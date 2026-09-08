"""Loopback-only analysis workspace. No external service, database, or uploaded file store.

Run ``python -m driftwatch.workbench`` after building ``web``. All file contents arrive
as bounded JSON strings; no API accepts filesystem paths. Requests run serially because
the existing no_network guard changes process-global HTTP methods.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import mimetypes
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize_scalar

from driftwatch import availability
from driftwatch.catalogue.history import frame_from_records
from driftwatch.cdm import parse as cdm_parse
from driftwatch.contact_planner import schedule_contacts
from driftwatch.imports import decode_orbit
from driftwatch.local import manoeuvre_table, no_network, oem_to_precise_orbit, parse_oem
from driftwatch.orbit.frames import teme_positions_to_geodetic
from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs
from driftwatch.storm.precise import frame_kind

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[2]
MAX_FILE = 12_000_000
MAX_REQUEST = 40_000_000
REFERENCE_KINDS = {"prediction", "reconstructed", "navigation"}


def finite(value: Any, name: str, low: float, high: float) -> float:
    try:
        n = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a number.") from None
    if not np.isfinite(n) or not low <= n <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}.")
    return n


def upload(body: dict, key: str, required: bool = True) -> tuple[str, str] | None:
    item = body.get(key)
    if item is None and not required:
        return None
    if not isinstance(item, dict) or not isinstance(item.get("text"), str):
        raise ValueError(f"Choose a {key} file.")
    text = item["text"].lstrip("\ufeff")
    if not text.strip() or len(text.encode("utf-8")) > MAX_FILE:
        raise ValueError(f"{key} must contain text and be no larger than 12 MB.")
    name = str(item.get("name", key)).replace("\\", "/").rsplit("/", 1)[-1][:160]
    return name, text


def source(name: str, text: str, role: str) -> dict:
    raw = text.encode("utf-8")
    return {"name": name, "role": role, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def stamp(t: Any) -> pd.Timestamp:
    value = pd.Timestamp(t)
    if pd.isna(value):
        raise ValueError("Supply a valid UTC date and time.")
    return value.tz_convert("UTC").tz_localize(None) if value.tzinfo else value


def iso(t: Any) -> str:
    return stamp(t).isoformat() + "Z"


def earth_trace(r: np.ndarray, times: np.ndarray, label: str, colour: str) -> dict:
    """Earth-fixed track, capped to its first 100 minutes for readability."""
    use = np.flatnonzero(times <= times[0] + np.timedelta64(100, "m"))
    use = use[:: max(1, int(np.ceil(len(use) / 240)))]
    lat, lon, height = teme_positions_to_geodetic(r[use], times[use])
    return {"label": label, "colour": colour, "points": np.column_stack((lat, lon, height)).tolist()}


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


@dataclass
class Trajectory:
    states: Callable
    start: pd.Timestamp | None
    end: pd.Timestamp | None
    metadata: dict
    identity: str


def trajectory(
    file: tuple[str, str], norad: int, at: pd.Timestamp | None = None, options: dict | None = None
) -> Trajectory:
    name, text = file
    options = options or {}
    selection_kind = options.get("selection_kind", availability.EPOCH_RECONSTRUCTION)
    decision_at = options.get("as_of", at)
    if selection_kind not in {availability.EPOCH_RECONSTRUCTION, availability.CAUSAL_REPLAY}:
        raise ValueError("Unknown availability selection kind")
    if selection_kind == availability.CAUSAL_REPLAY and pd.isna(availability.utc(decision_at)):
        raise ValueError("Causal replay requires a decision time")
    decoded = decode_orbit(text, options)
    if decoded.records is not None:
        records = decoded.records
        if at is None:
            raise ValueError(
                "A reference needs sampled states (OEM or mapped state CSV), not mean elements. "
                "Predictions also need a start time."
            )
        annotated = [
            {
                **r,
                "_driftwatch_published_at": options.get("published_at"),
                "_driftwatch_retrieved_at": options.get("retrieved_at"),
            }
            for r in records
        ]
        rows = frame_from_records(annotated, source="local-upload", preserve_versions=True)
        rows = rows[(rows.norad_id == norad) & (rows.epoch <= at.tz_localize("UTC"))]
        rows = availability.select(rows, as_of=decision_at, selection_kind=selection_kind)
        if not len(rows):
            raise ValueError(
                f"No OMM record for {norad} has an epoch at or before the start. "
                "Later state epochs and unavailable versions are refused under the declared selection rule."
            )
        selected = rows.sort_values(
            ["epoch", "provider_created_at", "retrieved_at"], na_position="first", kind="stable"
        ).iloc[-1:]
        sat = build_satrecs(selected)[0]
        epoch = stamp(selected.epoch.iloc[0])

        def states(times):
            result = propagate_satrecs([sat], np.array([norad]), np.asarray(times, dtype="datetime64[us]"))
            return result.r_teme[0], result.v_teme[0], result.error[0] == 0

        object_id = str(selected.object_id.iloc[0]) if pd.notna(selected.object_id.iloc[0]) else ""
        return Trajectory(
            states,
            None,
            None,
            {
                "name": name,
                "format": decoded.format,
                "import_warnings": decoded.warnings,
                "frame": "TEME",
                "time_system": "UTC",
                "epoch": iso(epoch),
                "state_epoch": iso(epoch),
                "provider_created_at": None
                if pd.isna(selected.provider_created_at.iloc[0])
                else iso(selected.provider_created_at.iloc[0]),
                "published_at": None if pd.isna(selected.published_at.iloc[0]) else iso(selected.published_at.iloc[0]),
                "retrieved_at": None if pd.isna(selected.retrieved_at.iloc[0]) else iso(selected.retrieved_at.iloc[0]),
                "imported_at": iso(datetime.now(UTC)),
                "selection_kind": selection_kind,
                "availability_as_of": iso(decision_at) if selection_kind == availability.CAUSAL_REPLAY else None,
                "age_at_start_h": (at - epoch).total_seconds() / 3600,
                "note": selection_kind + ": one fixed fit with latest eligible state epoch at/before start. "
                "Provider creation is not publication; unknown acquisition times stay unknown.",
            },
            object_id,
        )
    text = decoded.oem
    segments = parse_oem(
        text, source=name, published_at=options.get("published_at"), retrieved_at=options.get("retrieved_at")
    )
    if selection_kind == availability.CAUSAL_REPLAY:
        segments = [
            segment
            for segment in segments
            if availability.available(pd.DataFrame([segment.temporal_metadata()]), decision_at).iloc[0]
        ]
        if not segments:
            raise ValueError("No sampled orbit product was available by the causal decision time")
    identities = {s.object_id.strip() for s in segments}
    if len(identities) != 1 or not next(iter(identities)):
        raise ValueError("Every OEM segment must declare the same non-empty OBJECT_ID.")
    for segment in segments:
        if segment.center_name.strip().upper() != "EARTH":
            raise ValueError("OEM CENTER_NAME must explicitly be EARTH.")
        if segment.time_system.upper() not in {"UTC", "TAI", "GPS"}:
            raise ValueError(f"Unsupported time system {segment.time_system!r}; use UTC, TAI or GPS.")
        frame_kind(segment.ref_frame)
        if len(segment.states) < 2 or not np.isfinite(segment.states.iloc[:, 1:].to_numpy()).all():
            raise ValueError("Each OEM segment needs at least two finite position and velocity states in km and km/s.")
        times = segment.states.t.to_numpy(dtype="datetime64[us]")
        if np.any(np.diff(times) <= np.timedelta64(0, "us")):
            raise ValueError("OEM state times must increase within each segment; duplicates are refused.")
    # The generic parser historically defaulted a missing TIME_SYSTEM to UTC. Refuse
    # that ambiguity at the user-facing boundary, including a missing value in just one segment.
    import re

    blocks = re.findall(r"META_START(.*?)META_STOP", text, flags=re.S | re.I)
    if len(blocks) != len(segments) or any(not re.search(r"(?m)^\s*TIME_SYSTEM\s*=\s*\S+", b) for b in blocks):
        raise ValueError("Every OEM segment must explicitly declare TIME_SYSTEM; it cannot be guessed.")
    for segment, block in zip(segments, blocks, strict=True):
        metadata = dict(re.findall(r"(?m)^\s*([A-Z_]+)\s*=\s*([^\r\n]+)", block))
        # OEM producers can provide extra interpolation states outside a declared
        # usable interval. Conservatively restrict the supported interpolation to it.
        starts = [stamp(metadata[k]) for k in ("START_TIME", "USEABLE_START_TIME") if k in metadata]
        ends = [stamp(metadata[k]) for k in ("STOP_TIME", "USEABLE_STOP_TIME") if k in metadata]
        if starts:
            segment.states = segment.states[segment.states.t >= max(starts)].copy()
        if ends:
            segment.states = segment.states[segment.states.t <= min(ends)].copy()
        if len(segment.states) < 2:
            raise ValueError("The declared OEM usable interval contains fewer than two states.")
    orbit = oem_to_precise_orbit(segments, norad_id=norad)
    if not orbit.span:
        raise ValueError("This OEM contains no usable time span.")
    return Trajectory(
        orbit.states_teme,
        *orbit.span,
        {
            "name": name,
            "format": decoded.format,
            "import_warnings": decoded.warnings,
            "frame": orbit.frame,
            "time_system": ", ".join(sorted({s.time_system for s in segments})),
            "segments": len(segments),
            "object_id": next(iter(identities)),
            "source_time_metadata": [s.temporal_metadata() for s in segments],
            "selection_kind": selection_kind,
            "availability_as_of": iso(decision_at) if selection_kind == availability.CAUSAL_REPLAY else None,
            "state_epoch_start_utc": iso(orbit.span[0]),
            "state_epoch_end_utc": iso(orbit.span[1]),
            "note": "Covariance blocks are not used. States outside declared usable times are excluded. "
            "Frame conversion uses the project's documented "
            "J2000 approximation where applicable.",
        },
        next(iter(identities)),
    )


def compare(body: dict) -> dict:
    ref_file, pred_file = upload(body, "reference"), upload(body, "prediction")
    candidate_file = upload(body, "candidate", False)
    norad = int(finite(body.get("norad"), "Catalogue number", 1, 999999999))
    kind = body.get("reference_kind")
    if kind not in REFERENCE_KINDS:
        raise ValueError("Declare whether the reference is a prediction, reconstructed orbit or navigation solution.")
    ref = trajectory(ref_file, norad, options=body.get("reference_import"))
    pred = trajectory(pred_file, norad, ref.start, body.get("prediction_import"))
    candidate = trajectory(candidate_file, norad, ref.start, body.get("candidate_import")) if candidate_file else None
    sources = [source(*ref_file, "reference"), source(*pred_file, "prediction")]
    members = [ref, pred] + ([candidate] if candidate else [])
    for member in members[1:]:
        if member.identity and member.identity != ref.identity:
            raise ValueError("The files name different OBJECT_ID values. Select products for the same spacecraft.")
    start = max(t.start for t in members if t.start is not None)
    end = min(t.end for t in members if t.end is not None)
    if (end - start).total_seconds() < 60:
        raise ValueError("The products need at least one minute of overlapping coverage.")
    step = max(60, int(np.ceil((end - start).total_seconds() / 4000)))
    times = pd.date_range(start + pd.Timedelta(seconds=5), end - pd.Timedelta(seconds=5), freq=f"{step}s").to_numpy(
        dtype="datetime64[us]"
    )
    rr, rv, covered = ref.states(times)
    pr, _, pok = pred.states(times)
    good = covered & pok
    cr = None
    if candidate:
        cr, _, cok = candidate.states(times)
        good &= cok
        sources.append(source(*candidate_file, "candidate"))
    burns = upload(body, "manoeuvres", False)
    excluded_burns = np.zeros(len(times), dtype=bool)
    burn_metadata = []
    if burns:
        table = manoeuvre_table(
            pd.read_csv(io.StringIO(burns[1])),
            as_of=pred.metadata.get("availability_as_of"),
            selection_kind=pred.metadata["selection_kind"],
        )
        burn_metadata = availability.metadata(table, epoch_column="start")
        for _, row in table.iterrows():
            lo, hi = stamp(row.start), stamp(row.end)
            if hi < lo:
                raise ValueError("A manoeuvre interval ends before it starts.")
            excluded_burns |= (times >= lo.to_datetime64()) & (times <= hi.to_datetime64())
        sources.append(source(*burns, "manoeuvre intervals"))
    n_missing = int((~good).sum())
    good &= ~excluded_burns
    good &= np.isfinite(rr).all(axis=1) & np.isfinite(rv).all(axis=1)
    if not good.any():
        raise ValueError("There are no common usable samples after gap and manoeuvre exclusions.")
    rr, rv, pr = rr[good], rv[good], pr[good]
    radial = rr / np.linalg.norm(rr, axis=1)[:, None]
    cross = np.cross(rr, rv)
    if np.any(np.linalg.norm(cross, axis=1) < 1e-9):
        raise ValueError("Reference position and velocity cannot define an orbit frame.")
    cross /= np.linalg.norm(cross, axis=1)[:, None]
    intrack = np.cross(cross, radial)
    delta = pr - rr
    distance = np.linalg.norm(delta, axis=1)
    components = np.column_stack([np.sum(delta * b, axis=1) for b in (radial, intrack, cross)])
    candidate_distance = np.linalg.norm(cr[good] - rr, axis=1) if cr is not None else None
    tolerance = finite(body.get("tolerance_km", 1), "Tolerance in km", 0.001, 100000)
    samples = []
    for i, t in enumerate(times[good]):
        samples.append(
            {
                "time": iso(t),
                "elapsed_h": (stamp(t) - start).total_seconds() / 3600,
                "distance_km": distance[i],
                "radial_km": components[i, 0],
                "in_track_km": components[i, 1],
                "cross_track_km": components[i, 2],
                "candidate_km": candidate_distance[i] if candidate_distance is not None else None,
            }
        )
    summary = {
        "n": len(samples),
        "sample_step_s": step,
        "n_missing": n_missing,
        "n_manoeuvre": int(excluded_burns.sum()),
        "median_km": np.median(distance),
        "p95_km": np.quantile(distance, 0.95),
        "max_km": distance.max(),
        "within_tolerance_fraction": np.mean(distance <= tolerance),
        "tolerance_km": tolerance,
    }
    summary["earth_tracks"] = [
        earth_trace(rr, times[good], "Reference", "#d4ef8d"),
        earth_trace(pr, times[good], "Prediction", "#68b6ee"),
    ]
    if candidate_distance is not None:
        summary["earth_tracks"].append(earth_trace(cr[good], times[good], "Candidate", "#edb45e"))
        summary.update(
            candidate_median_km=np.median(candidate_distance),
            candidate_p95_km=np.quantile(candidate_distance, 0.95),
            candidate_fraction_better=np.mean(candidate_distance < distance),
        )
    return {
        "kind": "orbit-comparison",
        "reference_kind": kind,
        "reference_is_independent": "declared by user, not verified",
        "start": iso(start),
        "end": iso(end),
        "metadata": [m.metadata for m in members],
        "manoeuvre_time_metadata": burn_metadata,
        "summary": summary,
        "samples": samples,
        "sources": sources,
        "limitations": [
            "Prediction-to-prediction agreement is consistency, not accuracy."
            if kind == "prediction"
            else "Reference quality and independence are declared, not established by this comparison.",
            "Samples along one trajectory are correlated. Counts are not independent forecast trials.",
            "No collision probability or manoeuvre recommendation is computed.",
            "Manoeuvre exclusions cover only the recorded interval; later residuals can still reflect the burn.",
            "OEM interpolation never crosses metadata boundaries. "
            "The five-second margin supports reference velocity conversion.",
        ],
    }


def elevation(
    r_teme: np.ndarray, times: np.ndarray, lat: float, lon: float, height_m: float
) -> tuple[np.ndarray, np.ndarray]:
    """WGS84 station, GMST-only Earth rotation. UTC approximates UT1; no refraction."""
    import erfa
    from astropy.time import Time

    jd = Time(times, format="datetime64", scale="utc")
    angle = erfa.gmst82(jd.jd1, jd.jd2)
    c, s = np.cos(angle), np.sin(angle)
    xyz = np.column_stack((c * r_teme[:, 0] + s * r_teme[:, 1], -s * r_teme[:, 0] + c * r_teme[:, 1], r_teme[:, 2]))
    phi, lam = np.radians([lat, lon])
    n = 6378.137 / np.sqrt(1 - 6.69437999014e-3 * np.sin(phi) ** 2)
    height = height_m / 1000
    station = np.array(
        [
            (n + height) * np.cos(phi) * np.cos(lam),
            (n + height) * np.cos(phi) * np.sin(lam),
            (n * (1 - 6.69437999014e-3) + height) * np.sin(phi),
        ]
    )
    d = xyz - station
    east = -np.sin(lam) * d[:, 0] + np.cos(lam) * d[:, 1]
    north = -np.sin(phi) * np.cos(lam) * d[:, 0] - np.sin(phi) * np.sin(lam) * d[:, 1] + np.cos(phi) * d[:, 2]
    up = np.cos(phi) * np.cos(lam) * d[:, 0] + np.cos(phi) * np.sin(lam) * d[:, 1] + np.sin(phi) * d[:, 2]
    return np.degrees(np.arctan2(up, np.hypot(east, north))), np.degrees(np.arctan2(east, north)) % 360


def contact_passes(
    orbit: Trajectory, start: pd.Timestamp, hours: float, station: dict, mask: float
) -> tuple[list, list]:
    offsets = np.arange(0, hours * 3600 + 1, 20.0)

    def at(values):
        times = (start + pd.to_timedelta(np.atleast_1d(values), unit="s")).to_numpy(dtype="datetime64[us]")
        r, _, ok = orbit.states(times)
        el, az = elevation(r, times, **station)
        el[~ok] = np.nan
        return el, az

    el, az = at(offsets)
    active = np.isfinite(el) & (el >= mask)
    starts = np.flatnonzero(active & ~np.r_[False, active[:-1]])
    stops = np.flatnonzero(active & ~np.r_[active[1:], False])
    passes = []
    for a, b in zip(starts, stops, strict=True):
        partial = (
            a == 0
            or b == len(offsets) - 1
            or not np.isfinite(el[max(a - 1, 0)])
            or not np.isfinite(el[min(b + 1, len(el) - 1)])
        )

        def crossing(v):
            return float(at([v])[0][0] - mask)

        lo = brentq(crossing, offsets[a - 1], offsets[a], xtol=0.05) if a > 0 and np.isfinite(el[a - 1]) else offsets[a]
        hi = (
            brentq(crossing, offsets[b], offsets[b + 1], xtol=0.05)
            if b + 1 < len(offsets) and np.isfinite(el[b + 1])
            else offsets[b]
        )
        peak = minimize_scalar(lambda v: -float(at([v])[0][0]), bounds=(lo, hi), method="bounded") if hi > lo else None
        peak_s = float(peak.x) if peak else lo
        peak_el = float(at([peak_s])[0][0])
        passes.append(
            {
                "aos": iso(start + pd.Timedelta(seconds=lo)),
                "los": iso(start + pd.Timedelta(seconds=hi)),
                "duration_s": hi - lo,
                "peak_elevation_deg": peak_el,
                "peak_time": iso(start + pd.Timedelta(seconds=peak_s)),
                "partial": bool(partial),
                "lock_time": None,
                "lock_delay_s": None,
            }
        )
    # Only the first detected pass is plotted at full 20-second sampling resolution.
    points = []
    if passes:
        p = passes[0]
        lo = (stamp(p["aos"]) - start).total_seconds() - 60
        hi = (stamp(p["los"]) - start).total_seconds() + 60
        indices = (offsets >= lo) & (offsets <= hi)
        points = [
            {
                "time": iso(start + pd.Timedelta(seconds=t)),
                "minutes_from_aos": (t - (stamp(p["aos"]) - start).total_seconds()) / 60,
                "elevation_deg": e,
                "azimuth_deg": a,
            }
            for t, e, a in zip(offsets[indices], el[indices], az[indices], strict=True)
        ]
    return passes, points


def contacts(body: dict) -> dict:
    file = upload(body, "prediction")
    start = stamp(body.get("start"))
    hours = finite(body.get("hours", 24), "Window in hours", 1, 48)
    norad = int(finite(body.get("norad"), "Catalogue number", 1, 999999999))
    station = {
        "lat": finite(body.get("latitude"), "Latitude", -90, 90),
        "lon": finite(body.get("longitude"), "Longitude", -180, 180),
        "height_m": finite(body.get("height_m", 0), "Station height in metres", -500, 9000),
    }
    mask = finite(body.get("mask_deg", 10), "Elevation mask", 0, 89)
    orbit = trajectory(file, norad, start, body.get("prediction_import"))
    passes, points = contact_passes(orbit, start, hours, station, mask)
    trace_start = stamp(passes[0]["aos"]) - pd.Timedelta(minutes=10) if passes else start
    trace_times = pd.date_range(trace_start, periods=101, freq="60s").to_numpy(dtype="datetime64[us]")
    trace_r, _, trace_ok = orbit.states(trace_times)
    orbit.metadata["earth_tracks"] = (
        [earth_trace(trace_r[trace_ok], trace_times[trace_ok], "Prediction track", "#d4ef8d")] if trace_ok.any() else []
    )
    sources = [source(*file, "orbit prediction")]
    log = upload(body, "log", False)
    unmatched = []
    if log:
        table = pd.read_csv(io.StringIO(log[1]))
        if "lock_time" not in table:
            raise ValueError("Acquisition CSV needs a lock_time column of UTC times.")
        if len(table) > 10000:
            raise ValueError("Use at most 10,000 acquisition rows.")
        for value in table.lock_time:
            t = stamp(value)
            candidates = [
                p
                for p in passes
                if stamp(p["aos"]) - pd.Timedelta(minutes=2) <= t <= stamp(p["los"]) + pd.Timedelta(minutes=2)
            ]
            # Multiple possible matches are kept unresolved rather than forced.
            if len(candidates) == 1 and candidates[0]["lock_time"] is None:
                p = candidates[0]
                p["lock_time"], p["lock_delay_s"] = iso(t), (t - stamp(p["aos"])).total_seconds()
            else:
                unmatched.append(iso(t))
        sources.append(source(*log, "receiver lock log"))
    alternative = upload(body, "candidate", False)
    alternatives = []
    if alternative:
        other = trajectory(alternative, norad, start, body.get("candidate_import"))
        if other.identity and orbit.identity and other.identity != orbit.identity:
            raise ValueError("The two orbit files name different spacecraft.")
        alternatives, _ = contact_passes(other, start, hours, station, mask)
        used = set()
        for p in passes:
            matches = [
                (i, q)
                for i, q in enumerate(alternatives)
                if abs((stamp(q["aos"]) - stamp(p["aos"])).total_seconds()) <= 600
            ]
            p["alternative_aos_delta_s"] = None
            if len(matches) == 1 and matches[0][0] not in used and not p["partial"] and not matches[0][1]["partial"]:
                i, q = matches[0]
                used.add(i)
                p["alternative_aos_delta_s"] = (stamp(q["aos"]) - stamp(p["aos"])).total_seconds()
        sources.append(source(*alternative, "alternative orbit prediction"))
    return {
        "kind": "ground-contacts",
        "norad": norad,
        "start": iso(start),
        "hours": hours,
        "station": station,
        "mask_deg": mask,
        "metadata": orbit.metadata,
        "passes": passes,
        "first_pass_samples": points,
        "alternative_passes": alternatives,
        "unmatched_lock_times": unmatched,
        "sources": sources,
        "limitations": [
            "Ground-contact experiment, not an antenna command schedule. "
            "Confirm station coordinates and mask with the operator.",
            "20-second search grid with refined crossings; very short or grazing passes can be missed. "
            "No no-miss guarantee is claimed.",
            "GMST-only rotation uses UTC for UT1, ignores polar motion and atmospheric refraction. "
            "Suitable for exploratory timing comparisons, not precision pointing.",
            "Late receiver lock can result from pointing, clock, link budget or hardware. "
            "It is not a measurement of orbital error.",
            "Log rows match to one pass inside its interval plus two minutes; "
            "ambiguous and duplicate matches remain unresolved.",
            "A pass cut by the time window or an ephemeris gap is marked partial.",
        ],
    }


def cdms(body: dict) -> dict:
    files = [upload(body, "first"), upload(body, "second")]
    messages = []
    for name, text in files:
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise ValueError("XML document type declarations and entities are not accepted.")
        m = (
            cdm_parse.parse_xml(text, source=name)
            if text.lstrip().startswith("<")
            else cdm_parse.parse_kvn(text, source=name)
        )
        # The parser preserves declared units; never silently display km as metres.
        for key, unit in m.units.items():
            expected = "m/s" if key.startswith("RELATIVE_VELOCITY_") or key == "RELATIVE_SPEED" else "m"
            if (
                key.startswith("RELATIVE_POSITION_")
                or key.startswith("RELATIVE_VELOCITY_")
                or key in {"MISS_DISTANCE", "RELATIVE_SPEED"}
            ) and unit != expected:
                raise ValueError(f"Unsupported {key} unit {unit!r}; this comparison expects {expected}.")
        for obj in (m.object1, m.object2):
            for key in cdm_parse.COVARIANCE_KEYS:
                if key in obj.units and obj.units[key] not in {"m**2", "m^2", "m2"}:
                    raise ValueError(f"Unsupported covariance unit {obj.units[key]!r}; expected square metres.")
        if len(m.pair) != 2 or not m.object1.designator or not m.object2.designator:
            raise ValueError("Both messages must name two different object designators.")
        messages.append(m)
    a, b = messages
    dt = (b.tca - a.tca).total_seconds()
    tolerance = finite(body.get("tolerance_s", 600), "TCA matching tolerance in seconds", 0, 3600)
    same = a.pair == b.pair and abs(dt) <= tolerance
    checks = []
    for m in messages:
        for obj in (m.object1, m.object2):
            covariance = obj.covariance_rtn_m2
            state = "not supplied"
            if covariance is not None:
                state = (
                    "positive semidefinite"
                    if np.isfinite(covariance).all() and np.linalg.eigvalsh(covariance).min() >= -1e-8
                    else "invalid covariance: non-finite or negative eigenvalue"
                )
            checks.append(
                {
                    "file": m.source,
                    "object": obj.designator,
                    "frame": obj.raw.get("REF_FRAME", "not declared"),
                    "covariance": state,
                }
            )
        if np.isfinite(m.collision_probability) and not 0 <= m.collision_probability <= 1:
            raise ValueError("A collision probability is outside 0 to 1.")
    return {
        "kind": "cdm-reconciliation",
        "same_case": same,
        "tca_delta_s": dt,
        "tolerance_s": tolerance,
        "messages": [m.summary() for m in messages],
        "checks": checks,
        "sources": [source(*f, role) for f, role in zip(files, ("first CDM", "second CDM"), strict=True)],
        "limitations": [
            "A case match uses the unordered object pair and the selected closest-approach time tolerance. "
            "It does not establish equal orbit inputs.",
            "Message quantities use CCSDS standard units. "
            "This is a consistency review, not full CCSDS schema validation.",
            "Probability changes can result from different covariance, hard-body radius or prediction age. "
            "They do not prove one service wrong.",
            "Only the 3×3 position covariance is checked for positive semidefiniteness; "
            "covariance calibration and collision probability are not recomputed.",
        ],
    }


def model_trials(body: dict) -> dict:
    file = upload(body, "trials")
    frame = pd.read_csv(io.StringIO(file[1]))
    required = {"trial_id", "satellite", "window", "lead_h", "baseline_km", "candidate_km"}
    if not required.issubset(frame) or not 1 <= len(frame) <= 100000:
        raise ValueError(
            "Trial CSV needs 1–100,000 rows and trial_id,satellite,window,lead_h,baseline_km,candidate_km columns."
        )
    kind = body.get("reference_kind")
    forcing = body.get("forcing")
    if kind not in REFERENCE_KINDS or forcing not in {"observed", "forecast"}:
        raise ValueError("Declare the reference type and whether weather forcing was observed or forecast.")
    for col in ("lead_h", "baseline_km", "candidate_km"):
        frame[col] = pd.to_numeric(frame[col], errors="raise")
        if not np.isfinite(frame[col]).all():
            raise ValueError("Trial leads and residuals must be finite numbers.")
    if (frame.lead_h < 0).any() or (frame.lead_h > 8760).any():
        raise ValueError("Trial lead must be between 0 and 8,760 hours.")
    for col in ("trial_id", "satellite", "window"):
        if frame[col].isna().any():
            raise ValueError(f"Every trial needs {col}.")
        frame[col] = frame[col].astype(str)
    if frame.duplicated(["trial_id", "satellite", "lead_h"]).any():
        raise ValueError(
            "A satellite/trial/lead occurs more than once, possibly in both fit and holdout windows. "
            "Deduplicate or assign independent trial IDs."
        )
    if frame.window.nunique() > 20 or frame.lead_h.nunique() > 1000:
        raise ValueError("Use at most 20 windows and 1,000 distinct leads.")
    if forcing == "forecast":
        if not {"issued_at", "valid_at"}.issubset(frame):
            raise ValueError("Forecast trials also need issued_at and valid_at UTC columns.")
        issued = pd.to_datetime(frame.issued_at, utc=True, errors="raise")
        valid = pd.to_datetime(frame.valid_at, utc=True, errors="raise")
        lead = (valid - issued).dt.total_seconds() / 3600
        if (
            issued.isna().any()
            or valid.isna().any()
            or (lead < 0).any()
            or (np.abs(lead - frame.lead_h) > 1 / 60).any()
        ):
            raise ValueError("Forecast issue time must precede validity and agree with lead_h within one minute.")
    if "sigma_km" in frame:
        frame["sigma_km"] = pd.to_numeric(frame.sigma_km, errors="raise")
        if not np.isfinite(frame.sigma_km).all() or (frame.sigma_km <= 0).any():
            raise ValueError("Supplied sigma_km values must be finite and positive.")
    windows = {}
    for name, group in frame.groupby("window", sort=False):
        leads = {}
        for h, g in group.groupby("lead_h", sort=True):
            raw, candidate = g.baseline_km.abs(), g.candidate_km.abs()
            raw_m, candidate_m = float(raw.median()), float(candidate.median())
            leads[f"{h:g}"] = {
                "n": len(g),
                "in_track": {
                    "median_km": raw_m,
                    "p95_km": float(raw.quantile(0.95)),
                    "inside_2_sigma": float((raw <= 2 * g.sigma_km).mean()) if "sigma_km" in g else None,
                },
                "storm_term": {
                    "n": len(g),
                    "median_abs_raw_km": raw_m,
                    "median_abs_corrected_km": candidate_m,
                    "improvement": 1 - candidate_m / raw_m if raw_m else None,
                    "share_of_trials_improved": float((candidate < raw).mean()),
                },
            }
        windows[name] = {
            "role": str(name),
            "n_sets": len(group[["trial_id", "satellite"]].drop_duplicates()),
            "n_trial_leads": len(group),
            "n_excluded_gap": 0,
            "n_excluded_manoeuvre": 0,
            "n_excluded_sgp4_error": 0,
            "by_lead_h": leads,
        }
    return {
        "kind": "model-evaluation",
        "reference_kind": kind,
        "forcing": "Recorded forecast issue times supplied; provenance and availability at issuance remain unverified."
        if forcing == "forecast"
        else "Observed weather supplied; this is a hindcast, not a forecast-skill test.",
        "summary": {"windows": windows},
        "sources": [source(*file, "paired model residuals")],
        "limitations": [
            "Residuals and reference type are supplied by the analyst. "
            "This tool checks structure, timing and aggregation, not the underlying orbit determination.",
            "Each row is one paired trial at one lead. Correlated trials do not establish independent sample size.",
            "A holdout label is a declaration, not proof of separation from tuning. "
            "A zero baseline median leaves relative improvement undefined.",
            "No manoeuvre or data-gap exclusions are inferred from this CSV. "
            "Supply a curated trial table and keep its exclusion record.",
        ],
    }


def plan(body: dict) -> dict:
    file = upload(body, "contacts")
    result = schedule_contacts(
        file[1],
        turnaround_s=body.get("turnaround_s", 60),
        mapping=body.get("mapping"),
        delimiter=body.get("delimiter", ","),
    )
    result["sources"] = [source(*file, "candidate contacts")]
    return result


def inspect_orbit(body: dict) -> dict:
    file = upload(body, "file")
    options = body.get("options")
    decoded = decode_orbit(file[1], options)
    result = {
        "kind": "inspect",
        "format": decoded.format,
        "warnings": decoded.warnings or [],
        "sources": [source(*file, "inspection")],
        "schema_validation": "Supported fields checked; not a full CCSDS schema validation.",
    }
    if decoded.records is not None:
        rows = decoded.records
        result.update(
            frame="TEME",
            time_system="UTC",
            records=len(rows),
            objects=[
                {"norad": n, "name": next(r.get("OBJECT_NAME", "") for r in rows if r["NORAD_CAT_ID"] == n)}
                for n in sorted({r["NORAD_CAT_ID"] for r in rows})
            ],
            start=min(iso(r["EPOCH"]) for r in rows),
            end=max(iso(r["EPOCH"]) for r in rows),
            coverage_label="Element epochs, not a validity window",
        )
    else:
        orbit = trajectory(file, 1, options=options)
        result.update(
            orbit.metadata,
            start=iso(orbit.start),
            end=iso(orbit.end),
            objects=[],
            coverage_label="Sampled state coverage; segment gaps are excluded",
        )
    return result


def analyse(kind: str, body: dict) -> dict:
    if not isinstance(body, dict):
        raise ValueError("The request must be a JSON object.")
    handlers = {
        "compare": compare,
        "contacts": contacts,
        "cdms": cdms,
        "model": model_trials,
        "inspect": inspect_orbit,
        "plan": plan,
    }
    if kind not in handlers:
        raise ValueError("Unknown analysis tool.")
    with no_network():
        result = handlers[kind](body)
    result.update(
        schema_version=1,
        software_version=VERSION,
        built_at=datetime.now(UTC).isoformat(),
        processing="local process; supported outbound HTTP clients disabled during analysis",
    )
    # Inputs and parameters fingerprint the result. A hash proves file identity, not origin.
    result["request_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return clean(result)


def make_server(directory: Path, port: int = 8765) -> HTTPServer:
    directory = directory.resolve()
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Do not put private filenames or results in the terminal.

        def allowed(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            return self.headers.get("Host") == expected and self.headers.get("Sec-Fetch-Site") != "cross-site"

        def respond(self, status, value, mime="application/json"):
            data = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header(
                "Content-Type",
                mime
                + (
                    "; charset=utf-8"
                    if mime in ("application/json", "text/html", "text/css", "text/javascript")
                    else ""
                ),
            )
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; worker-src 'self' blob:; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.allowed():
                self.respond(403, {"error": "Use the 127.0.0.1 address shown by the local workspace."})
                return
            path = unquote(urlsplit(self.path).path)
            if path == "/api/health":
                self.respond(200, {"service": "driftwatch-local", "version": VERSION, "token": token})
                return
            dest = (directory / (path.lstrip("/") or "index.html")).resolve()
            if (
                not dest.is_relative_to(directory)
                or any(part.startswith(".") for part in dest.relative_to(directory).parts)
                or not dest.is_file()
            ):
                self.respond(404, {"error": "File not found."})
                return
            mime = (
                {".js": "text/javascript", ".wasm": "application/wasm"}.get(dest.suffix)
                or mimetypes.guess_type(dest.name)[0]
                or "application/octet-stream"
            )
            self.respond(200, dest.read_bytes(), mime)

        def do_POST(self):
            if (
                not self.allowed()
                or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}"
                or not secrets.compare_digest(self.headers.get("X-Driftwatch-Token", ""), token)
            ):
                self.respond(403, {"error": "This request must come from this local workspace."})
                return
            if self.headers.get("Content-Type") != "application/json":
                self.respond(415, {"error": "Use a JSON request."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_REQUEST:
                    self.respond(413, {"error": "Request must be between 1 byte and 40 MB."})
                    return
                self.connection.settimeout(30)
                body = json.loads(self.rfile.read(length))
                kind = urlsplit(self.path).path.removeprefix("/api/")
                self.respond(200, analyse(kind, body))
            except (ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
                self.respond(400, {"error": str(exc)[:500]})
            except Exception:
                self.respond(
                    500,
                    {
                        "error": "The analysis could not finish. "
                        "Check the file format and coverage; no result has been saved."
                    },
                )

    return HTTPServer(("127.0.0.1", port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--web", type=Path, default=ROOT / "web" / "dist")
    args = parser.parse_args(argv)
    if not (args.web / "index.html").is_file():
        parser.error("Build the interface first: cd web, then npm ci and npm run build.")
    server = make_server(args.web, args.port)
    print(f"driftwatch local workspace: http://127.0.0.1:{server.server_port}", flush=True)
    print("Files are analysed in memory. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
