"""Bounded, paired radio track benchmark on the four existing reference windows.

This module performs no work at import. A caller must explicitly run the benchmark
after the corrected input is ready. All candidates are constructed pointings, not
an observing schedule or detections. No September experiment data are selected.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from astropy.utils import iers
from scipy.optimize import brentq

from driftwatch import config as paths
from driftwatch.orbit.propagator import build_satrecs
from driftwatch.orbit.time import julian_dates
from driftwatch.radio import crossings, site
from driftwatch.storm import reference

ALLOWED_WINDOWS = frozenset({"quiet", "storm", "august", "held-out"})
IDENTITY_COLUMNS = ("mission", "norad_id", "window", "set_epoch", "lead_h", "t")
BEAM_FILES = (
    "meerkat_U_816.000000MHz.npz",
    "meerkat_L_1284.000000MHz.npz",
    "meerkat_L_1712.000000MHz.npz",
    "meerkat_S0_2187.500000MHz.npz",
    "meerkat_S4_3062.500000MHz.npz",
    "meerkat_S4_3500.000000MHz.npz",
)


@dataclass(frozen=True)
class TrackBenchmarkConfig:
    half_span_s: int = 180
    step_s: float = 1.0
    min_nominal_elevation_deg: float = 15.0
    max_nominal_elevation_deg: float = 85.0
    normal_boundary_fractions: tuple[float, ...] = (0.0, 0.95, -0.95, 1.0, -1.0, 1.05, -1.05, 1.5, -1.5)
    root_tolerance_s: float = 0.001


DEFAULT_CONFIG = TrackBenchmarkConfig()


def validate_trials(trials: pd.DataFrame) -> pd.DataFrame:
    """Validate labels AND actual epochs before any orbit/history access."""
    if not set(trials.window) <= ALLOWED_WINDOWS:
        raise ValueError("Only the four existing reference windows are permitted")
    frame = trials.loc[:, list(IDENTITY_COLUMNS)].copy()
    frame["set_epoch"] = pd.to_datetime(frame.set_epoch, utc=True)
    frame["t"] = pd.to_datetime(frame.t, utc=True)
    if frame.empty or frame.isna().any().any():
        raise ValueError("The radio input must contain complete trial identities")
    windows = {w.name: w for w in reference.WINDOWS}
    for name, group in frame.groupby("window"):
        window = windows[name]
        if not ((group.set_epoch >= window.sets_from) & (group.set_epoch < window.sets_to)).all():
            raise ValueError(f"Trial epochs lie outside the declared {name} window")
    if not frame.lead_h.isin(reference.precise.LEADS_HOURS).all():
        raise ValueError("Unexpected reference lead")
    delta = (frame.t - frame.set_epoch).dt.total_seconds() - frame.lead_h * 3600.0
    if not np.all(np.abs(delta) <= 1e-5):
        raise ValueError("Trial target does not equal element epoch plus declared lead")
    for mission, group in frame.groupby("mission"):
        if mission not in reference.MISSIONS or not (group.norad_id == reference.MISSIONS[mission].norad_id).all():
            raise ValueError("Trial mission/NORAD identity is inconsistent")
    if frame.duplicated(["mission", "window", "set_epoch", "lead_h"]).any():
        raise ValueError("Duplicate radio trial identity")
    return frame.sort_values(["mission", "window", "set_epoch", "lead_h"]).reset_index(drop=True)


def load_trial_identities(path: Path) -> pd.DataFrame:
    """Read window labels first, then identities only; residual values are not read."""
    labels = pd.read_csv(path, usecols=["window"])
    if not set(labels.window) <= ALLOWED_WINDOWS:
        raise ValueError("Only the four existing reference windows are permitted")
    return validate_trials(pd.read_csv(path, usecols=list(IDENTITY_COLUMNS)))


def _history_filters(trials: pd.DataFrame) -> list[list[tuple]]:
    # Disjunction of narrow windows, never one April--October bounding interval.
    return [
        [
            ("epoch", ">=", group.set_epoch.min().to_pydatetime()),
            ("epoch", "<=", group.set_epoch.max().to_pydatetime()),
            ("norad_id", "in", sorted(map(int, group.norad_id.unique()))),
        ]
        for _, group in trials.groupby("window", sort=True)
    ]


def load_selected_elements(trials: pd.DataFrame, history_dir: Path) -> pd.DataFrame:
    """Push down disjoint window filters, then exact-join every requested epoch."""
    trials = validate_trials(trials)
    history_dir = Path(history_dir).resolve()
    wanted = trials[["norad_id", "set_epoch"]].drop_duplicates().rename(columns={"set_epoch": "epoch"})
    filters = _history_filters(trials)
    index = pq.read_table(
        history_dir / "index.parquet", columns=["norad_id", "epoch", "file"], filters=filters
    ).to_pandas()
    index["epoch"] = pd.to_datetime(index.epoch, utc=True)
    selected = wanted.merge(index, on=["norad_id", "epoch"], how="left", validate="one_to_one")
    if selected.file.isna().any():
        raise ValueError("Missing exact element set in the stored history index")
    frames = []
    for filename, group in selected.groupby("file"):
        path = (history_dir / filename).resolve()
        if not path.is_relative_to(history_dir):
            raise ValueError("History index file lies outside its declared directory")
        part = pq.read_table(path, filters=filters).to_pandas()
        part["epoch"] = pd.to_datetime(part.epoch, utc=True)
        frames.append(
            group[["norad_id", "epoch"]].merge(part, on=["norad_id", "epoch"], how="left", validate="one_to_one")
        )
    result = pd.concat(frames, ignore_index=True).sort_values(["norad_id", "epoch"]).reset_index(drop=True)
    if len(result) != len(wanted) or result.mean_motion.isna().any():
        raise ValueError("An indexed exact element set is absent from its history file")
    return result


def _mount_axes(centre: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    az = np.arctan2(centre[0], centre[1])
    alt = np.arctan2(centre[2], np.hypot(centre[0], centre[1]))
    return np.array([np.cos(az), -np.sin(az), 0]), np.array(
        [-np.sin(alt) * np.sin(az), -np.sin(alt) * np.cos(az), np.cos(alt)]
    )


def displaced_boresight(centre: np.ndarray, normal_xy: np.ndarray, angle_deg: float) -> np.ndarray:
    right, up = _mount_axes(centre)
    angle = np.deg2rad(angle_deg)
    return np.cos(angle) * centre + np.sin(angle) * (normal_xy[0] * right + normal_xy[1] * up)


def signed_half_power_radius(centre: np.ndarray, normal_xy: np.ndarray, beam, sign: int) -> float:
    """First outward half-power boundary, preserving sign, squint and beam axes."""
    if sign not in {-1, 1}:
        raise ValueError("Boundary sign must be -1 or +1")

    def objective(radius):
        bore = displaced_boresight(centre, normal_xy, sign * radius)
        return float(beam.power(*site.beam_offsets_deg(centre, bore))) - 0.5

    if objective(0.0) <= 0:
        raise ValueError("The nominal beam centre is outside the measured main lobe")
    # Fine scan finds the first boundary, rather than a later side-lobe contour.
    limit = min(15.0, float(np.max(np.abs(beam.margin_deg))) * 1.5)
    radii = np.linspace(0.0, limit, 1001)
    right, up = _mount_axes(centre)
    angle = np.deg2rad(sign * radii)
    candidates = np.cos(angle)[:, None] * centre + np.sin(angle)[:, None] * (normal_xy[0] * right + normal_xy[1] * up)
    values = beam.power(*site.beam_offsets_deg(centre, candidates)) - 0.5
    outside = np.flatnonzero(values <= 0)
    if len(outside):
        k = outside[0]
        return float(brentq(objective, radii[k - 1], radii[k], xtol=1e-10))
    raise ValueError("No measured half-power boundary within the declared beam field")


def pointing_family(
    prediction_enu: np.ndarray,
    times: np.ndarray,
    seconds: np.ndarray,
    beam,
    configuration: TrackBenchmarkConfig = DEFAULT_CONFIG,
) -> list[dict[str, Any]]:
    """Pointings normal to motion RELATIVE to the fixed celestial centre."""
    centre_index = int(np.flatnonzero(seconds == 0)[0])
    centre = prediction_enu[centre_index]
    alt = np.rad2deg(np.arctan2(centre[2], np.hypot(centre[0], centre[1])))
    az = np.rad2deg(np.arctan2(centre[0], centre[1]))
    ra, dec = site.sky_from_alt_az(site.MEERKAT, alt, az, times[centre_index : centre_index + 1])
    _, _, centre_curve = site.boresight(site.MEERKAT, float(ra[0]), float(dec[0]), times)
    x, y = site.beam_offsets_deg(prediction_enu, centre_curve)
    velocity = np.array([x[centre_index + 1] - x[centre_index - 1], y[centre_index + 1] - y[centre_index - 1]])
    if not np.isfinite(velocity).all() or np.linalg.norm(velocity) <= 1e-10:
        raise ValueError("Nominal apparent motion has no resolved normal direction")
    normal = np.array([-velocity[1], velocity[0]]) / np.linalg.norm(velocity)
    radii = {sign: signed_half_power_radius(centre, normal, beam, sign) for sign in (-1, 1)}
    family = []
    for fraction in configuration.normal_boundary_fractions:
        sign = 1 if fraction >= 0 else -1
        angle = fraction * radii[sign]
        candidate = displaced_boresight(centre, normal, angle)
        alt = np.rad2deg(np.arctan2(candidate[2], np.hypot(candidate[0], candidate[1])))
        az = np.rad2deg(np.arctan2(candidate[0], candidate[1]))
        ra, dec = site.sky_from_alt_az(site.MEERKAT, alt, az, times[centre_index : centre_index + 1])
        _, _, curve = site.boresight(site.MEERKAT, float(ra[0]), float(dec[0]), times)
        family.append(
            {
                "offset_fraction": fraction,
                "offset_deg": angle,
                "signed_boundary_radius_deg": sign * radii[sign],
                "normal_xy": normal.tolist(),
                "ra_deg": float(ra[0]),
                "dec_deg": float(dec[0]),
                "boresight_enu": curve,
            }
        )
    return family


def restrict_observation(
    comparison: crossings.TrackComparison, interval: tuple[float, float]
) -> crossings.TrackComparison:
    """Reuse full-span extrema/roots and clip only the observing interval."""
    if (
        interval[0] < comparison.observation_interval_s[0]
        or interval[1] > comparison.observation_interval_s[1]
        or interval[0] >= interval[1]
    ):
        raise ValueError("Observation interval must lie within the full comparison")

    def clipped(measure):
        pairs = [
            (max(i.entry_s, interval[0]), min(i.exit_s, interval[1]))
            for i in measure.intervals
            if min(i.exit_s, interval[1]) > max(i.entry_s, interval[0])
        ]

        def inside(t):
            return any(i.entry_s <= t <= i.exit_s for i in measure.intervals)

        return replace(
            measure,
            observation_crossed=bool(pairs),
            observation_entry_s=pairs[0][0] if pairs else None,
            observation_exit_s=pairs[-1][1] if pairs else None,
            observation_start_inside=inside(interval[0]),
            observation_end_inside=inside(interval[1]),
        )

    p, r = clipped(comparison.prediction), clipped(comparison.reference)
    false, missed = (
        p.observation_crossed and not r.observation_crossed,
        r.observation_crossed and not p.observation_crossed,
    )
    return replace(
        comparison,
        prediction=p,
        reference=r,
        observation_interval_s=interval,
        false_crossing=false,
        missed_crossing=missed,
        both_crossed=p.observation_crossed and r.observation_crossed,
        observation_edge_mismatch=bool((false or missed) and p.intervals and r.intervals),
    )


def flatten_case(
    identity: dict, pointing: dict, beam_key: str, observation: str, comparison: crossings.TrackComparison
) -> dict[str, Any]:
    record = comparison.record()
    result = {
        **identity,
        **{k: v for k, v in pointing.items() if k not in {"boresight_enu", "normal_xy"}},
        "beam_key": beam_key,
        "frequency_mhz": comparison.beam["frequency_mhz"],
        "observation": observation,
    }
    result.update(
        {k: v for k, v in record.items() if k not in {"prediction", "reference", "beam", "observation_interval_s"}}
    )
    result["true_negative"] = (
        not comparison.prediction.observation_crossed and not comparison.reference.observation_crossed
    )
    for prefix in ("prediction", "reference"):
        result.update({f"{prefix}_{k}": v for k, v in record[prefix].items() if k != "intervals"})
        intervals = record[prefix]["intervals"]
        result[f"{prefix}_n_intervals"] = len(intervals)
        result[f"{prefix}_entry_censored"] = any(i["entry_censored"] for i in intervals)
        result[f"{prefix}_exit_censored"] = any(i["exit_censored"] for i in intervals)
    return result


def summarise_cases(cases: pd.DataFrame, *, by_offset: bool = False) -> list[dict[str, Any]]:
    """Descriptive paired denominators; constructed pointings are correlated."""
    if cases.empty:
        return []
    group_cols = ["beam_key", "frequency_mhz", "window", "lead_h", "observation"]
    if by_offset:
        group_cols += ["offset_fraction"]
    output = []
    flags = ("false_crossing", "missed_crossing", "both_crossed", "true_negative", "observation_edge_mismatch")
    for key, group in cases.groupby(group_cols, dropna=False, sort=True):
        row = dict(zip(group_cols, key, strict=True))
        row.update(
            n_cases=len(group),
            n_missions=group.mission.nunique(),
            n_sets=len(group[["mission", "window", "set_epoch"]].drop_duplicates()),
            n_trials=group.trial_id.nunique(),
            mission_counts=group.mission.value_counts().sort_index().to_dict(),
        )
        for flag in flags:
            row[flag + "_n"] = int(group[flag].sum())
            row[flag + "_fraction"] = float(group[flag].mean())
        row["n_reference_crossed"] = int(group.reference_observation_crossed.sum())
        row["n_prediction_crossed"] = int(group.prediction_observation_crossed.sum())
        row["false_fraction_of_prediction_crossings"] = (
            row["false_crossing_n"] / row["n_prediction_crossed"] if row["n_prediction_crossed"] else None
        )
        row["missed_fraction_of_reference_crossings"] = (
            row["missed_crossing_n"] / row["n_reference_crossed"] if row["n_reference_crossed"] else None
        )
        for side in ("prediction", "reference"):
            for flag in (
                "closest_time_censored",
                "peak_time_censored",
                "entry_censored",
                "exit_censored",
                "tangential_contact",
                "observation_start_inside",
                "observation_end_inside",
            ):
                row[f"{side}_{flag}_n"] = int(group[f"{side}_{flag}"].sum())
        for metric in (
            "closest_time_error_s",
            "entry_time_error_s",
            "exit_time_error_s",
            "closest_separation_error_deg",
            "instantaneous_error_at_reference_closest_deg",
            "max_sampled_instantaneous_error_deg",
        ):
            selected = group
            if metric.startswith("closest_") or metric == "instantaneous_error_at_reference_closest_deg":
                selected = group.loc[~group.prediction_closest_time_censored & ~group.reference_closest_time_censored]
            if metric.startswith(("entry_", "exit_")):
                selected = group.loc[group.both_crossed]
            values = pd.to_numeric(selected[metric], errors="coerce").dropna()
            values = values[np.isfinite(values)]
            row[metric + "_n"] = len(values)
            row[metric + "_median"] = float(values.median()) if len(values) else None
            row[metric + "_abs_median"] = float(values.abs().median()) if len(values) else None
            row[metric + "_abs_q95_linear"] = (
                float(values.abs().quantile(0.95, interpolation="linear")) if len(values) else None
            )
        output.append(row)
    return output


def _write_json(path: Path, content: Any) -> None:
    """Replace atomically; tolerate transient Windows readers of progress files."""
    payload = json.dumps(content, indent=2, allow_nan=False, default=str) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    try:
        for attempt in range(10):
            try:
                os.replace(temporary, path)
                break
            except OSError as exc:
                if exc.errno not in {13, 22, 32} or attempt == 9:
                    raise
                time.sleep(0.05)
    finally:
        temporary.unlink(missing_ok=True)


def run_track_benchmark(
    trial_csv: Path,
    output_dir: Path,
    *,
    history_dir: Path = paths.HISTORY_DIR,
    beam_dir: Path = paths.CACHE_DIR / "radio",
    configuration: TrackBenchmarkConfig = DEFAULT_CONFIG,
    progress=None,
) -> dict[str, Any]:
    """Explicit entry point: no downloads, no new windows, all raw cases retained.

    The corrected source-filtered CSV is required. Caller is responsible for
    scheduling this run only after earlier reference corrections are complete.
    An existing output protocol is never overwritten; choose a new attempt path.
    """
    trials = load_trial_identities(Path(trial_csv))
    if configuration.half_span_s != 180 or configuration.step_s != 1.0:
        raise ValueError("The specified production grid is ±180 s at 1 s cadence")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if (output_dir / "radio_track_protocol.json").exists():
        raise FileExistsError("A radio attempt already exists; preserve it and choose a new output directory")
    beams = {Path(name).stem: site.MeasuredBeam.load(Path(beam_dir) / name) for name in BEAM_FILES}
    protocol = {
        "schema_version": 1,
        "specified_at": datetime.now(UTC).isoformat(),
        "configuration": asdict(configuration),
        "windows": [w.as_dict() for w in reference.WINDOWS],
        "input_csv": str(Path(trial_csv).resolve()),
        "input_csv_sha256": hashlib.sha256(Path(trial_csv).read_bytes()).hexdigest(),
        "trial_identities_sha256": hashlib.sha256(trials.to_csv(index=False).encode()).hexdigest(),
        "n_input_trials": len(trials),
        "site": asdict(site.MEERKAT),
        "beams": {key: beam.record() for key, beam in beams.items()},
        "source_sha256": {
            str(p.relative_to(paths.PROJECT_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((paths.PROJECT_ROOT / "src" / "driftwatch").rglob("*.py"))
        },
        "observation_intervals_s": {"full": [-180, 180], "ends_at_centre": [-180, 0], "starts_at_centre": [0, 180]},
        "candidate_rule": (
            "fixed ICRS centre and signed normal offsets, each sign scaled to its first measured half-power boundary"
        ),
        "normal_rule": "central difference relative to fixed ICRS centre in per-time mount beam axes",
        "population": (
            "constructed pointings at source-filtered benchmark targets; not an observing schedule or detections"
        ),
        "eligibility": (
            "nominal elevation at target 15 through 85 degrees; entire ±180 s curves finite "
            "with reference coverage and zero SGP4 codes"
        ),
        "geometry": (
            "complete TEME positions transformed with IERS UT1/polar motion, rotating WGS84 observer, "
            "fixed ICRS boresight; no refraction"
        ),
        "data_access": (
            "offline truth by individual mission/window; disjoint history predicates followed by exact epoch joins"
        ),
        "timing_summary": (
            "uncensored paired closest times; entry/exit only for both observation crossings "
            "and one uncensored full-span interval each"
        ),
        "uncertainty": "descriptive clustered cases; no independent-trial confidence or population guarantee",
    }
    _write_json(output_dir / "radio_track_protocol.json", protocol)
    elements = load_selected_elements(trials, history_dir)
    _write_json(
        output_dir / "radio_track_elements.json",
        {"n": len(elements), "selected_rows_sha256": hashlib.sha256(elements.to_csv(index=False).encode()).hexdigest()},
    )
    satrecs = {
        (int(row.norad_id), row.epoch): sat
        for row, sat in zip(elements.itertuples(index=False), build_satrecs(elements), strict=True)
    }
    seconds = np.arange(-180.0, 181.0)
    exclusions, flat_cases, truth_sources = [], [], {}
    curves_dir = output_dir / "curves"
    curves_dir.mkdir()
    completed = 0

    def report(status, **details):
        value = {
            "status": status,
            "completed_trials": completed,
            "total_trials": len(trials),
            "scored_cases": len(flat_cases),
            "updated_at": datetime.now(UTC).isoformat(),
            **details,
        }
        _write_json(output_dir / "radio_track_progress.json", value)
        if progress:
            progress(value)

    report("running")
    try:
        with (
            (output_dir / "radio_track_cases.jsonl").open("w", encoding="utf-8") as raw,
            (output_dir / "radio_track_eligibility.jsonl").open("w", encoding="utf-8") as eligibility,
            iers.conf.set_temp("auto_download", False),
        ):
            for (mission, window), group in trials.groupby(["mission", "window"], sort=True):
                start = (group.t.min() - pd.Timedelta(seconds=185)).date()
                end = (group.t.max() + pd.Timedelta(seconds=185)).date()
                orbit, _ = reference.load_truth(reference.MISSIONS[mission], start, end, offline=True, records=False)
                truth_sources[f"{mission}/{window}"] = {
                    "from": str(start),
                    "through": str(end),
                    "files": list(orbit.files) if orbit is not None else [],
                    "available": orbit is not None,
                }
                _write_json(output_dir / "radio_track_truth_sources.json", truth_sources)
                for row in group.itertuples(index=False):
                    identity = {k: getattr(row, k) for k in IDENTITY_COLUMNS}
                    identity.update(set_epoch=row.set_epoch.isoformat(), t=row.t.isoformat())
                    trial_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
                    identity["trial_id"] = trial_id
                    dates = row.t.to_datetime64().astype("datetime64[us]") + (seconds * 1e6).astype("timedelta64[us]")
                    jd, fr = julian_dates(dates)
                    error, predicted, _ = satrecs[(int(row.norad_id), row.set_epoch)].sgp4_array(jd, fr)
                    reason, nominal_el = None, None
                    if np.any(error != 0) or not np.isfinite(predicted).all():
                        reason = "invalid_nominal_sgp4_curve"
                    else:
                        nominal = site.look_from_teme(site.MEERKAT, predicted, dates)
                        nominal_el = float(nominal.elevation_deg[180])
                        if nominal_el < 0:
                            reason = "nominal_below_horizon"
                        elif nominal_el < configuration.min_nominal_elevation_deg:
                            reason = "nominal_below_15_degrees"
                        elif nominal_el > configuration.max_nominal_elevation_deg:
                            reason = "nominal_above_85_degrees"
                        elif orbit is None:
                            reason = "reference_unavailable"
                        else:
                            actual, _, covered = orbit.states_teme(dates)
                            if not np.all(covered) or not np.isfinite(actual).all():
                                reason = "reference_curve_gap_or_nonfinite"
                    admission = {
                        **identity,
                        "nominal_elevation_deg": nominal_el,
                        "eligible": reason is None,
                        "reason": reason or "eligible",
                    }
                    exclusions.append(admission)
                    eligibility.write(json.dumps(admission, allow_nan=False) + "\n")
                    eligibility.flush()
                    if reason is None:
                        truth = site.look_from_teme(site.MEERKAT, actual, dates)
                        curve_path = curves_dir / f"{trial_id}.npz"
                        np.savez_compressed(
                            curve_path,
                            seconds=seconds,
                            times=dates,
                            prediction_teme_km=predicted,
                            reference_teme_km=actual,
                            prediction_enu=nominal.enu,
                            reference_enu=truth.enu,
                            prediction_range_km=nominal.range_km,
                            reference_range_km=truth.range_km,
                        )
                        curve_hash = hashlib.sha256(curve_path.read_bytes()).hexdigest()
                        identity.update(
                            nominal_elevation_deg=nominal_el,
                            reference_elevation_deg=float(truth.elevation_deg[180]),
                            reference_min_elevation_deg=float(truth.elevation_deg.min()),
                            prediction_min_elevation_deg=float(nominal.elevation_deg.min()),
                            curve_file=str(curve_path.relative_to(output_dir)),
                            curve_sha256=curve_hash,
                        )
                        for beam_key, beam in beams.items():
                            family = pointing_family(nominal.enu, dates, seconds, beam, configuration)
                            for pointing in family:
                                bore = pointing["boresight_enu"]
                                full = crossings.compare_sky_tracks(
                                    crossings.SkyTrack(seconds, nominal.enu, bore),
                                    crossings.SkyTrack(seconds, truth.enu, bore),
                                    beam.power,
                                    beam_record=beam.record(),
                                    observation_interval_s=(-180, 180),
                                    time_tolerance_s=configuration.root_tolerance_s,
                                )
                                for observation, interval in protocol["observation_intervals_s"].items():
                                    result = (
                                        full if observation == "full" else restrict_observation(full, tuple(interval))
                                    )
                                    case = flatten_case(identity, pointing, beam_key, observation, result)
                                    flat_cases.append(case)
                                    raw.write(
                                        json.dumps(
                                            {
                                                **case,
                                                "normal_xy": pointing["normal_xy"],
                                                "prediction_intervals": asdict(result)["prediction"]["intervals"],
                                                "reference_intervals": asdict(result)["reference"]["intervals"],
                                            },
                                            allow_nan=False,
                                        )
                                        + "\n"
                                    )
                        raw.flush()
                    completed += 1
                    report("running", mission=mission, window=window)
        cases = pd.DataFrame(flat_cases)
        admitted = pd.DataFrame(exclusions)
        cases.to_csv(output_dir / "radio_track_cases.csv", index=False)
        admitted.to_csv(output_dir / "radio_track_eligibility.csv", index=False)
        summary = {
            "schema_version": 1,
            "protocol": "radio_track_protocol.json",
            "n_input_trials": len(trials),
            "n_eligible_trials": int(admitted.eligible.sum()),
            "n_cases": len(cases),
            "eligibility_counts": admitted.reason.value_counts().to_dict(),
            "eligibility_by_window_mission_lead": admitted.groupby(["window", "mission", "lead_h", "reason"])
            .size()
            .rename("n")
            .reset_index()
            .to_dict("records"),
            "by_beam_window_lead_observation": summarise_cases(cases),
            "by_beam_window_lead_observation_offset": summarise_cases(cases, by_offset=True),
        }
        _write_json(output_dir / "radio_track_summary.json", summary)
        report("complete")
        return summary
    except Exception as exc:
        report("failed", error_type=type(exc).__name__, error=str(exc))
        raise


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=Path, default=paths.DATA_DIR / "radio" / "benchmark_trials.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    last_group = None

    def progress(value):
        nonlocal last_group
        group = (value.get("mission"), value.get("window"))
        if group != last_group or value["completed_trials"] % 100 == 0 or value["status"] != "running":
            print(json.dumps(value), flush=True)
            last_group = group

    summary = run_track_benchmark(args.trials, args.output, progress=progress)
    print(json.dumps({key: summary[key] for key in ("n_input_trials", "n_eligible_trials", "n_cases")}), flush=True)


if __name__ == "__main__":
    main()
