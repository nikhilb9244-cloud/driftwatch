"""Local analysis: an operator's own ephemerides, messages and records, on the operator's own machine.

The public demonstration is reproducible from public sources and stays that way: the daily
pipeline, the validation cases and the Swarm calibration read nothing that is not public. This
module is the optional other path. An operator who will not upload a Conjunction Data Message
or an ephemeris to anybody -- which is most of them -- can run the same three instruments over
their own files without a byte leaving the machine:

1. the **provenance check** on a stored run (``driftwatch check-run``'s logic): is the run's
   recorded snapshot real, how old is it, are its supplemental versions still stored;
2. the **CDM matcher** (``driftwatch cdm match``): which of the operator's warnings public data
   found, at what miss and probability against theirs, and which public-data flags they never
   received;
3. the **calibration against the operator's ephemeris**, the Swarm benchmark's machinery with
   the operator's own orbit as the truth (``driftwatch.storm.precise``): for every public
   element set issued while the ephemeris runs, the residual by lead in the satellite's RIC
   frame, the coverage of the covariance the screening would have carried, the storm term's
   effect if the weather is cached, and the horizon for the screening box. The operator's own
   manoeuvre record, if supplied, decides the exclusion; the project's detection is reported
   beside it.

**Nothing leaves the machine.** ``no_network`` makes every outbound HTTP request fail by name
for the duration of the command: httpx (every fetch this project makes), urllib (astropy's
IERS and leap-second downloads) and astropy's own auto-download switch. The element sets come
from the local history store or from a file the operator supplies; the weather from the
cached CelesTrak file, or the storm term is skipped and the report says so. Nothing is written
anywhere but the output directory.

The ephemeris format is the CCSDS Orbit Ephemeris Message (502.0-B-2) in KVN: a header, one or
more segments each with ``META_START`` / ``META_STOP`` and state lines ``epoch x y z vx vy vz``
in km and km/s. Frames accepted: ITRF (any realisation), TEME, and J2000/EME2000; time systems
UTC, TAI and GPS. Anything else is refused by name rather than guessed. The manoeuvre record is
a CSV with ``start`` and ``end`` columns of UTC times, one interval a row, whatever else it
carries.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch.cdm.parse import parse_epoch
from driftwatch.storm import precise

log = logging.getLogger(__name__)

__all__ = [
    "NetworkRefused",
    "OemSegment",
    "ephemeris_benchmark",
    "load_manoeuvre_records",
    "load_oem",
    "no_network",
    "oem_to_precise_orbit",
    "parse_oem",
    "to_markdown",
]


# --------------------------------------------------------------------------------------
# The guard


class NetworkRefused(RuntimeError):
    """Raised by any outbound request attempted inside :func:`no_network`."""


@contextmanager
def no_network() -> Iterator[None]:
    """Make every outbound HTTP request fail by name for the duration of the block.

    Belt and braces rather than a promise: the project's fetches all go through httpx, so
    ``Client.send`` and ``AsyncClient.send`` are replaced; astropy fetches IERS tables and leap
    seconds through urllib, so ``urlopen`` is replaced and astropy's auto-download is switched
    off; everything is restored on exit, whatever happened inside.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        target = ""
        for a in args:
            if isinstance(a, httpx.Request):
                target = str(a.url)
            elif isinstance(a, str | urllib.request.Request):
                target = a if isinstance(a, str) else a.full_url
        raise NetworkRefused(f"local analysis: an outbound request was attempted and refused ({target or 'unknown'})")

    saved = (httpx.Client.send, httpx.AsyncClient.send, urllib.request.urlopen)
    httpx.Client.send = refuse  # type: ignore[method-assign]
    httpx.AsyncClient.send = refuse  # type: ignore[method-assign]
    urllib.request.urlopen = refuse  # type: ignore[assignment]
    auto = None
    try:
        from astropy.utils import iers

        auto = iers.conf.auto_download
        iers.conf.auto_download = False
    except Exception:  # pragma: no cover - astropy is a dependency, but the guard must not depend on it
        iers = None  # type: ignore[assignment]
    try:
        yield
    finally:
        httpx.Client.send, httpx.AsyncClient.send, urllib.request.urlopen = saved  # type: ignore[method-assign,assignment]
        if auto is not None:
            iers.conf.auto_download = auto


# --------------------------------------------------------------------------------------
# The ephemeris


@dataclass
class OemSegment:
    """One segment of an Orbit Ephemeris Message: its metadata and its states, km and km/s."""

    object_name: str
    object_id: str
    center_name: str
    ref_frame: str
    time_system: str
    start_time: pd.Timestamp | None
    stop_time: pd.Timestamp | None
    states: pd.DataFrame
    source: str = ""
    comments: list[str] = field(default_factory=list)


_KV = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$")


def parse_oem(text: str, *, source: str = "") -> list[OemSegment]:
    """An OEM in KVN, as a list of segments; the covariance blocks, if any, are skipped.

    The header (``CCSDS_OEM_VERS``, ``CREATION_DATE``, ``ORIGINATOR``) is read past; each
    ``META_START`` to ``META_STOP`` block names the object, the centre, the frame and the time
    system; every data line after it with seven or ten numbers is a state (acceleration, when
    given, is dropped). A ``COVARIANCE_START`` block ends the segment's states.
    """
    segments: list[OemSegment] = []
    meta: dict[str, str] | None = None
    rows: list[tuple[Any, ...]] = []
    comments: list[str] = []
    in_meta = False
    in_cov = False

    def close() -> None:
        nonlocal meta, rows, comments
        if meta is None:
            return
        frame = pd.DataFrame(rows, columns=["t", "x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"])
        segments.append(
            OemSegment(
                object_name=meta.get("OBJECT_NAME", ""),
                object_id=meta.get("OBJECT_ID", ""),
                center_name=meta.get("CENTER_NAME", ""),
                ref_frame=meta.get("REF_FRAME", ""),
                time_system=meta.get("TIME_SYSTEM", "UTC"),
                start_time=parse_epoch(meta["START_TIME"]) if meta.get("START_TIME") else None,
                stop_time=parse_epoch(meta["STOP_TIME"]) if meta.get("STOP_TIME") else None,
                states=frame,
                source=source,
                comments=comments,
            )
        )
        meta, rows, comments = None, [], []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        upper = line.upper()
        if upper == "META_START":
            close()
            meta, in_meta, in_cov = {}, True, False
            continue
        if upper == "META_STOP":
            in_meta = False
            continue
        if upper == "COVARIANCE_START":
            in_cov = True
            continue
        if upper == "COVARIANCE_STOP":
            in_cov = False
            continue
        if upper.startswith("COMMENT"):
            comments.append(line[7:].strip())
            continue
        if in_meta and meta is not None:
            m = _KV.match(line)
            if m:
                meta[m.group(1)] = m.group(2)
            continue
        if in_cov or meta is None:
            continue
        parts = line.split()
        if len(parts) in (7, 10):
            try:
                values = [float(v) for v in parts[1:7]]
            except ValueError:
                continue
            rows.append((parse_epoch(parts[0]).tz_convert(None), *values))
    close()
    if not segments:
        raise ValueError(f"no OEM segment found{f' in {source}' if source else ''}")
    return segments


def load_oem(path: Path | str) -> list[OemSegment]:
    """Every segment of every OEM file at ``path`` (a file, or a directory of ``*.oem``, ``*.txt``, ``*.kvn``)."""
    p = Path(path)
    files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.suffix.lower() in (".oem", ".txt", ".kvn"))
    if not files:
        raise FileNotFoundError(f"no OEM files under {p}")
    out: list[OemSegment] = []
    for f in files:
        out.extend(parse_oem(f.read_text(encoding="utf-8", errors="replace"), source=f.name))
    return out


def oem_to_precise_orbit(
    segments: list[OemSegment], *, norad_id: int, label: str | None = None
) -> precise.PreciseOrbit:
    """The segments as one truth the benchmark can compare against: one frame, epochs in UTC, gaps kept.

    Segments must share a frame the rotation supports (:func:`driftwatch.storm.precise.frame_kind`);
    each segment's time system is converted with the SP3 reader's own conversion (UTC, TAI, GPS).
    A gap between segments stays a gap: nothing is interpolated across it.
    """
    frames = {s.ref_frame.strip().upper() for s in segments}
    if len(frames) != 1:
        raise ValueError(f"the OEM segments are in different frames: {sorted(frames)}")
    frame = next(iter(frames))
    precise.frame_kind(frame)  # refuses an unsupported frame by name
    tables = []
    for seg in segments:
        t = seg.states.copy()
        if len(t):
            t["t"] = precise.sp3_epochs_to_utc(t["t"], seg.time_system)
        tables.append(t)
    table = (
        pd.concat(tables, ignore_index=True).sort_values("t").drop_duplicates("t").reset_index(drop=True)
        if tables
        else pd.DataFrame(columns=["t", "x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"])
    )
    table["t"] = pd.to_datetime(table["t"]).astype("datetime64[us]")
    files = sorted({s.source for s in segments if s.source})
    return precise.PreciseOrbit(label or str(norad_id), int(norad_id), table, [], files, frame=frame)


# --------------------------------------------------------------------------------------
# The operator's records


def load_manoeuvre_records(path: Path | str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Manoeuvre intervals from a CSV with ``start`` and ``end`` columns of UTC times (case-insensitive)."""
    frame = pd.read_csv(path)
    columns = {c.lower().strip(): c for c in frame.columns}
    if "start" not in columns or "end" not in columns:
        raise ValueError(f"{path}: the manoeuvre record needs 'start' and 'end' columns; it has {list(frame.columns)}")
    out = []
    for start, end in zip(frame[columns["start"]], frame[columns["end"]], strict=True):
        lo, hi = parse_epoch(start).tz_convert(None), parse_epoch(end).tz_convert(None)
        if hi < lo:
            raise ValueError(f"{path}: manoeuvre interval ends before it starts ({start} to {end})")
        out.append((lo, hi))
    return sorted(out)


# --------------------------------------------------------------------------------------
# The benchmark against the operator's ephemeris


@dataclass
class EphemerisBenchmark:
    window: precise.BenchmarkWindow
    inputs: precise.SatelliteInputs
    trials: pd.DataFrame
    summary: dict[str, Any]


def ephemeris_benchmark(
    norad_id: int,
    sets: pd.DataFrame,
    orbit: precise.PreciseOrbit,
    *,
    label: str | None = None,
    leads_hours: tuple[float, ...] = precise.LEADS_HOURS,
    published: list[tuple[pd.Timestamp, pd.Timestamp]] | None = None,
    grid: Any = None,
    category: str = "payload",
    altitude_band: str = "leo",
    tolerance_km: float = precise.HORIZON_TOLERANCE_KM,
) -> EphemerisBenchmark:
    """The Swarm benchmark's four outputs with the operator's ephemeris as the truth.

    The trials are the public element sets issued while the ephemeris runs and at least the
    shortest lead before it ends; the covariance and the coefficient are fitted from the local
    history before the first of them, exactly as for Swarm.
    """
    span = orbit.span
    if span is None:
        raise ValueError("the ephemeris holds no states")
    first, last = span
    sets_to = last - pd.Timedelta(hours=min(leads_hours))
    if sets_to <= first:
        raise ValueError(f"the ephemeris ({first} to {last}) is shorter than the shortest lead")
    window = precise.BenchmarkWindow(
        "ephemeris",
        "operator",
        first.tz_localize("UTC").to_pydatetime(),
        sets_to.tz_localize("UTC").to_pydatetime(),
        None,
        f"the operator's ephemeris {'; '.join(orbit.files) or '(unnamed)'} as the truth",
    )
    inputs = precise.fit_inputs(
        norad_id, sets, window, grid, label=label or str(norad_id), category=category, altitude_band=altitude_band
    )
    if not len(inputs.trial_sets):
        raise ValueError(f"no public element set for {norad_id} is held locally inside {first} to {sets_to}")
    trials = precise.satellite_trials(inputs, orbit, window, grid, leads_hours=leads_hours, published=published)
    summary = precise.summarise(trials, tolerance_km=tolerance_km)
    return EphemerisBenchmark(window, inputs, trials, summary)


# --------------------------------------------------------------------------------------
# The report


def to_markdown(report: dict[str, Any]) -> str:
    """The local analysis as a page: what was checked, what was matched, what the ephemeris showed."""
    lines = [
        "# Local analysis",
        "",
        f"Written by `driftwatch local` on {report['built_at'][:19]}Z. Nothing left this machine: every outbound "
        "request was refused for the duration of the command (`driftwatch.local.no_network`).",
        "",
    ]
    check = report.get("provenance")
    if check:
        lines += ["## Provenance of the run", ""]
        lines.append(
            f"Run `{check['run']}`: snapshot `{check.get('snapshot')}`"
            + (
                f", fetched {check['snapshot_fetched_at'][:19]}Z ({check['snapshot_age_hours']:.1f} h before this "
                "analysis)."
                if check.get("snapshot_fetched_at")
                else "."
            )
        )
        for w in check.get("warnings", []):
            lines.append(f"- warning: {w}")
        for p in check.get("problems", []):
            lines.append(f"- **problem: {p}**")
        lines.append("- ok" if check.get("ok") else "- **the run's recorded provenance does not check out**")
        lines.append("")
    match = report.get("cdm")
    if match:
        s = match["summary"]
        lines += ["## Conjunction Data Messages against the run", ""]
        lines.append(
            f"{s.get('n_messages', 0)} messages, {s.get('n_conjunctions', 0)} distinct conjunctions; matched "
            f"{s.get('n_matched', 0)} messages ({s.get('n_conjunctions_matched', 0)} conjunctions) within "
            f"{s.get('tolerance_s', 0):g} s of a public-data event; {s.get('n_unmatched', 0)} operator warnings "
            f"public data did not find; {s.get('n_unwarned_flags', 0)} public-data flags on the operator's objects "
            "that no message mentions."
        )
        for key in ("miss_ratio", "log10_pc_ratio", "dt_tca_s"):
            if key in s and isinstance(s[key], dict):
                lines.append(f"- {key}: {json.dumps(s[key])}")
        lines.append("")
    eph = report.get("ephemeris")
    if eph:
        lines += ["## The public element sets against the operator's ephemeris", ""]
        lines.append(
            f"Object {eph['norad_id']} ({eph['label']}); ephemeris in {eph['frame']} from {eph['span'][0][:19]} to "
            f"{eph['span'][1][:19]}; {eph['n_states']} states in {eph['n_files']} file(s). A trial is one public "
            "element set; one residual per lead."
        )
        lines.append("")
        w = eph["summary"]["windows"]["ephemeris"]
        lines.append(
            f"{w['n_sets']} element sets, {w['n_trial_leads']} set-lead pairs; excluded {w['n_excluded_gap']} for an "
            f"ephemeris gap, {w['n_excluded_manoeuvre']} for a manoeuvre, {w['n_excluded_sgp4_error']} for an SGP4 "
            f"error. Covariance source: {', '.join(w['covariance_sources'])}; coefficient source: "
            f"{', '.join(w['b_sources'])}."
        )
        lines.append("")
        lines.append(precise._manoeuvre_sentence(w.get("manoeuvres") or {}))
        lines.append("")
        lines += [
            "| Lead | n | in-track median | in-track p95 | inside 1σ | inside 2σ | radial median | cross median | "
            "storm term |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for lead, e in w["by_lead_h"].items():
            i, r, c, st = e["in_track"], e["radial"], e["cross"], e["storm_term"]
            term = (
                f"{st['median_abs_raw_km']:.2f} → {st['median_abs_corrected_km']:.2f} km ({st['improvement']:+.0%})"
                if st["n"] and st["improvement"] is not None
                else "not run"
            )
            lines.append(
                f"| {float(lead):g} h | {e['n']} | {i['median_km']:.2f} km | {i['p95_km']:.2f} km | "
                f"{i['inside_1_sigma']:.0%} | {i['inside_2_sigma']:.0%} | {r['median_km']:.3f} km | "
                f"{c['median_km']:.3f} km | {term} |"
            )
        h = w["horizon"]
        lines.append("")
        lines.append(
            f"Horizon. Task: {h['task']}. "
            + (
                f"Inside the tolerance through {h['last_lead_h_within']:g} h; beyond it at "
                f"{h['first_lead_h_beyond']:g} h."
                if h["last_lead_h_within"] is not None and h["first_lead_h_beyond"] is not None
                else f"Inside the tolerance at every lead measured, through {h['last_lead_h_within']:g} h."
                if h["last_lead_h_within"] is not None
                else f"Beyond the tolerance at the shortest lead measured, {h['first_lead_h_beyond']:g} h."
                if h["first_lead_h_beyond"] is not None
                else "No usable trial."
            )
        )
        lines.append("")
    lines += ["## Sources", ""]
    for s in report.get("sources", []):
        lines.append(f"- **{s['source']}.** {s['origin']}")
    lines.append("")
    return "\n".join(lines)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, pd.Timestamp | datetime):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value


def write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    """``local_analysis.json`` and ``local_analysis.md`` under ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "local_analysis.json"
    md_path = out_dir / "local_analysis.md"
    json_path.write_text(json.dumps(_json_ready(report), indent=2, default=str), encoding="utf-8")
    md_path.write_text(to_markdown(report) + "\n", encoding="utf-8")
    return json_path, md_path
