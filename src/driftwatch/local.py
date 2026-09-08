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
   the operator's own orbit as a declared reference (``driftwatch.storm.precise``): for every public
   element set selected by state epoch while the ephemeris runs, the residual by lead in the satellite's RIC
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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch import availability
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
    provider_created_at: pd.Timestamp | None = None
    published_at: pd.Timestamp | None = None
    retrieved_at: pd.Timestamp | None = None
    imported_at: pd.Timestamp | None = None
    originator: str | None = None

    def temporal_metadata(self) -> dict[str, Any]:
        def iso(value):
            return None if value is None or pd.isna(value) else pd.Timestamp(value).isoformat()

        return {
            "source": self.source,
            "state_epoch_start": iso(self.states.t.min()) if len(self.states) else None,
            "state_epoch_end": iso(self.states.t.max()) if len(self.states) else None,
            "state_time_system": self.time_system,
            "provider_created_at": iso(self.provider_created_at),
            "published_at": iso(self.published_at),
            "retrieved_at": iso(self.retrieved_at),
            "imported_at": iso(self.imported_at),
            "originator": self.originator,
        }


_KV = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$")


def parse_oem(
    text: str, *, source: str = "", published_at: datetime | None = None, retrieved_at: datetime | None = None
) -> list[OemSegment]:
    """An OEM in KVN, as a list of segments; the covariance blocks, if any, are skipped.

    Header creation time and originator are preserved separately from publication,
    retrieval and local import time. Unknown publication/retrieval stay unknown. Each
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
    header: dict[str, str] = {}
    imported_at = pd.Timestamp(datetime.now(UTC))

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
                provider_created_at=parse_epoch(header["CREATION_DATE"]) if header.get("CREATION_DATE") else None,
                published_at=parse_epoch(str(published_at)) if published_at is not None else None,
                retrieved_at=parse_epoch(str(retrieved_at)) if retrieved_at is not None else None,
                imported_at=imported_at,
                originator=header.get("ORIGINATOR"),
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
            match = _KV.match(line)
            if not in_cov and match and match[1] in {"CREATION_DATE", "ORIGINATOR"}:
                header[match[1]] = match[2]
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
    """The segments as one reference the benchmark can compare against: one frame, epochs in UTC, gaps kept.

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
    orbit = precise.PreciseOrbit(label or str(norad_id), int(norad_id), table, [], files, frame=frame)
    # An OEM metadata boundary is a discontinuity even when its timestamps are close.
    # Build each segment separately so Hermite interpolation never bridges that seam.
    orbit.segments.clear()
    orbit.table.attrs["source_time_metadata"] = [s.temporal_metadata() for s in segments]
    previous_end = None
    for t in sorted(tables, key=lambda x: x["t"].iloc[0] if len(x) else pd.Timestamp.max):
        if not len(t):
            continue
        if previous_end is not None and t["t"].iloc[0] <= previous_end:
            raise ValueError("OEM segments overlap; choose non-overlapping versions before comparing")
        previous_end = t["t"].iloc[-1]
        part = precise.PreciseOrbit(label or str(norad_id), int(norad_id), t, [], files, frame=frame)
        orbit.segments.extend(part.segments)
    return orbit


# --------------------------------------------------------------------------------------
# The operator's records


def manoeuvre_table(frame: pd.DataFrame, *, as_of=None, selection_kind=availability.EPOCH_RECONSTRUCTION):
    """Keep event time distinct from creation/publication/retrieval and filter before exclusion."""
    frame = frame.rename(columns={c: c.lower().strip() for c in frame.columns}).copy()
    if not {"start", "end"} <= set(frame):
        raise ValueError("Manoeuvre CSV needs start,end UTC columns")
    for key in ("start", "end"):
        frame[key] = pd.to_datetime(frame[key], utc=True, format="mixed")
    if frame[["start", "end"]].isna().any().any() or (frame.end < frame.start).any():
        raise ValueError("A manoeuvre interval ends before it starts or has an unknown event time")
    return availability.select(
        frame, as_of=as_of, selection_kind=selection_kind, epoch_column="start", restrict_epoch=False
    )


def load_manoeuvre_records(
    path: Path | str, *, as_of=None, selection_kind=availability.EPOCH_RECONSTRUCTION
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """UTC CSV intervals under an explicit reconstruction or causal-availability rule."""
    frame = manoeuvre_table(pd.read_csv(path), as_of=as_of, selection_kind=selection_kind)
    return [(row.start.tz_convert(None), row.end.tz_convert(None)) for row in frame.sort_values("start").itertuples()]


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
    reference_kind: str = "prediction",
    selection_kind: str = availability.EPOCH_RECONSTRUCTION,
    decision_at: datetime | None = None,
) -> EphemerisBenchmark:
    """The Swarm benchmark's four outputs with the operator's declared reference ephemeris.

    The trials are selected by state epoch while the ephemeris runs and at least the
    shortest lead before it ends; the covariance and the coefficient are fitted from the local
    history before the first of them, exactly as for Swarm.
    """
    if reference_kind not in {"prediction", "reconstructed", "navigation"}:
        raise ValueError("reference_kind must be prediction, reconstructed or navigation")
    if selection_kind == availability.CAUSAL_REPLAY:
        if grid is not None:
            raise ValueError("Causal weather availability is not established for this local comparison")
        sets = availability.select(sets, as_of=decision_at, selection_kind=selection_kind)
        sets = sets.sort_values(
            ["norad_id", "epoch", "provider_created_at", "retrieved_at"], na_position="first", kind="stable"
        ).drop_duplicates(["norad_id", "epoch"], keep="last")
    elif selection_kind != availability.EPOCH_RECONSTRUCTION:
        raise ValueError("Unknown availability selection kind")
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
        f"the operator's ephemeris {'; '.join(orbit.files) or '(unnamed)'} as a declared {reference_kind} reference",
    )
    inputs = precise.fit_inputs(
        norad_id, sets, window, grid, label=label or str(norad_id), category=category, altitude_band=altitude_band
    )
    if not len(inputs.trial_sets):
        raise ValueError(f"no public element set for {norad_id} is held locally inside {first} to {sets_to}")
    trials = precise.satellite_trials(inputs, orbit, window, grid, leads_hours=leads_hours, published=published)
    summary = precise.summarise(trials, tolerance_km=tolerance_km)
    summary["selection_kind"] = selection_kind
    summary["availability_as_of"] = None if decision_at is None else availability.utc(decision_at).isoformat()
    summary["source_time_metadata"] = orbit.table.attrs.get("source_time_metadata", [])
    summary["element_set_time_metadata"] = [
        {
            "norad_id": int(row.norad_id),
            "state_epoch": pd.Timestamp(row.epoch).isoformat(),
            **{
                key: None if pd.isna(getattr(row, key, None)) else pd.Timestamp(getattr(row, key)).isoformat()
                for key in ("provider_created_at", "published_at", "retrieved_at")
            },
        }
        for row in inputs.trial_sets.itertuples()
    ]
    summary["availability_claim"] = selection_kind == availability.CAUSAL_REPLAY
    summary["availability_scope"] = (
        "Prediction element sets for the fixed supplied object; reference may be reconstructed later"
    )
    return EphemerisBenchmark(window, inputs, trials, summary)


# --------------------------------------------------------------------------------------
# The report


def to_markdown(report: dict[str, Any]) -> str:
    """The local analysis as a page: what was checked, what was matched, what the ephemeris showed."""
    lines = [
        "# Local analysis",
        "",
        f"Written by `driftwatch local` on {report['built_at'][:19]}Z. The project's supported HTTP clients "
        "and astropy downloads were disabled during analysis (`driftwatch.local.no_network`). "
        "This application guard is not OS-level network isolation.",
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
        lines.append(
            f"Declared reference: {eph.get('reference_kind', 'unspecified')}. "
            "Agreement with a prediction is consistency, not realised accuracy. "
            "The reference's independence and quality must be established separately."
        )
        lines.append("")
        w = eph["summary"]["windows"]["ephemeris"]
        if eph["summary"].get("selection_kind") == availability.CAUSAL_REPLAY:
            lines.append(
                "Causal replay of prediction inputs at " + eph["summary"]["availability_as_of"] + ": "
                "publication or actual retrieval evidence is required. The reference may be reconstructed later."
            )
        else:
            lines.append(
                "Epoch-based reconstruction: sets are selected by state epoch; "
                "publication-time availability is not established."
            )
        for metadata in eph["summary"].get("source_time_metadata", []):
            lines.append("Source times (unknown fields remain null): " + json.dumps(metadata))
        lines.append("Element-set state and availability times are retained separately in the analysis JSON.")
        lines.append("")
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
