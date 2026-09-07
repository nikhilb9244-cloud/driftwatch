"""Running the reference expansion: every mission through the benchmark, the laser checks, and the page.

One mission-window is one call of :func:`run_mission_window`: the truth is loaded, the element
sets fitted from history that ends where the window's sets begin (the same rule and the same
functions as the Swarm benchmark), one trial per element set is scored against the truth in the
satellite's radial, in-track, cross-track frame, and, where the mission has a retroreflector, the
laser-ranging normal points of the window are compared with the truth (how the two references
disagree) and with each element set's propagation (a one-dimensional range residual by lead).
The tables are then by altitude band and window, and by mission and window.

Held out means held out: the covariance and the coefficient used on a window are fitted from the
history before it, for every mission, and no threshold in this module was chosen by looking at
October or August.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.catalogue import history
from driftwatch.drag import density as dn
from driftwatch.orbit.propagator import build_satrecs
from driftwatch.storm import precise, reference, slr
from driftwatch.storm.precise import BenchmarkWindow, PreciseOrbit, ThrusterRecord
from driftwatch.storm.reference import Mission

log = logging.getLogger(__name__)

WGS72_MU_KM3_S2 = 398600.8
EARTH_RADIUS_KM = 6378.137
# A normal point counts against a set while the set is inside the benchmark's leads, with an hour's slack.
SLR_MAX_LEAD_H = max(precise.LEADS_HOURS) + 1.0
# Laser points are plentiful for some missions; the SGP4 comparison keeps at most this many per set and lead bin.
SLR_MAX_POINTS_PER_SET_BIN = 40


def mean_altitude_km(mean_motion_rev_day: np.ndarray) -> np.ndarray:
    n = np.asarray(mean_motion_rev_day, dtype=float) * 2.0 * np.pi / 86400.0
    return (WGS72_MU_KM3_S2 / n**2) ** (1.0 / 3.0) - EARTH_RADIUS_KM


def load_sets(missions: list[Mission], windows: list[BenchmarkWindow]) -> pd.DataFrame:
    """Every stored element set for the missions from the earliest covariance history to the latest truth."""
    start = min(w.sets_from for w in windows) - timedelta(days=precise.COVARIANCE_HISTORY_DAYS + 1)
    end = max(w.truth_to for w in windows)
    sets = history.load_history(norad_ids=[m.norad_id for m in missions], start=start, end=end, include_snapshots=False)
    if len(sets):
        sets = sets.assign(category="payload")
    return sets


@dataclass
class MissionWindowRun:
    mission: Mission
    window: BenchmarkWindow
    orbit: PreciseOrbit | None
    record: ThrusterRecord | None
    n_trial_sets: int
    trials: pd.DataFrame | None
    orbit_vs_slr: dict[str, Any] | None
    sgp4_vs_slr: pd.DataFrame | None
    notes: list[str] = field(default_factory=list)


def _sgp4_residuals_by_lead(
    mission: Mission,
    window: BenchmarkWindow,
    inputs: precise.SatelliteInputs,
    points: pd.DataFrame,
    stations: slr.Stations,
    excluded: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> pd.DataFrame:
    """Each trial set propagated to the normal points inside its leads: the range residual, with the lead bin."""
    rows: list[pd.DataFrame] = []
    if not len(points):
        return pd.DataFrame()
    t_all = points["t"].dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    leads = np.asarray(precise.LEADS_HOURS, dtype=float)
    for _, row in inputs.trial_sets.iterrows():
        epoch = pd.Timestamp(row["epoch"])
        epoch = epoch.tz_convert(None) if epoch.tzinfo else epoch
        age_h = (t_all - np.datetime64(epoch.to_datetime64(), "us")) / np.timedelta64(1, "h")
        inside = (age_h > 0.0) & (age_h <= SLR_MAX_LEAD_H)
        if not inside.any():
            continue
        sub = points[inside].reset_index(drop=True)
        bins = leads[np.minimum(np.searchsorted(leads, age_h[inside], side="left"), len(leads) - 1)]
        sub = sub.assign(lead_h=age_h[inside], lead_bin_h=bins)
        # A burn between the set's tracking arc and the point takes the point out, as it takes a trial out.
        arc = epoch - pd.Timedelta(hours=precise.MANOEUVRE_ARC_HOURS)
        keep = np.array(
            [not precise._overlaps(excluded, arc, pd.Timestamp(t).tz_convert(None)) for t in sub["t"]], dtype=bool
        )
        sub = sub[keep]
        if not len(sub):
            continue
        # Thin dense passes so one satellite-day does not outweigh the rest of the bin.
        rng = np.random.default_rng(0)
        keep_idx: list[int] = []
        for _, g in sub.groupby("lead_bin_h"):
            idx = g.index.to_numpy()
            if len(idx) > SLR_MAX_POINTS_PER_SET_BIN:
                idx = rng.choice(idx, SLR_MAX_POINTS_PER_SET_BIN, replace=False)
            keep_idx.extend(int(i) for i in idx)
        sub = sub.loc[sorted(keep_idx)]
        satrec = build_satrecs(row.to_frame().T.reset_index(drop=True))[0]
        res = slr.range_residuals(sub, slr.sgp4_position_fn(satrec), stations)
        if not len(res):
            continue
        res = res.assign(mission=mission.key, window=window.name, set_epoch=epoch)
        rows.append(
            res[
                [
                    "mission",
                    "window",
                    "set_epoch",
                    "station",
                    "t",
                    "lead_h",
                    "lead_bin_h",
                    "elevation_deg",
                    "residual_m",
                ]
            ]
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def run_mission_window(
    mission: Mission,
    window: BenchmarkWindow,
    sets: pd.DataFrame,
    grid: dn.WeatherGrid | None,
    *,
    stations: slr.Stations | None,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    with_slr: bool = True,
) -> MissionWindowRun:
    day_from = (window.sets_from - timedelta(days=1)).date()
    day_to = window.truth_to.date()
    notes: list[str] = []
    orbit, record = reference.load_truth(mission, day_from, day_to, cache_dir=cache_dir, offline=offline)
    if orbit is not None and not len(orbit.table):
        notes.append("no truth states in the window")
        orbit = None
    inputs = precise.fit_inputs(
        mission.norad_id, sets, window, grid, label=mission.key, category="payload", altitude_band="leo"
    )
    n_sets = len(inputs.trial_sets)
    log.info(
        "%s, %s window: %d trial sets, covariance %s from %d sets, coefficient %s, truth %s",
        mission.name,
        window.name,
        n_sets,
        inputs.covariance_source,
        inputs.covariance_history[2],
        None if inputs.coefficient is None else f"{float(inputs.coefficient['b_m2_kg']):.4f} m2/kg",
        "none" if orbit is None else f"{len(orbit.table)} states, {len(orbit.days_missing)} day(s) missing",
    )
    trials = None
    if orbit is not None and n_sets:
        label = {reference.MANOEUVRES_ESA: "esa-record", reference.MANOEUVRES_GRACEFO: "thr1b-record"}.get(
            mission.manoeuvres, "esa-record"
        )
        trials = precise.satellite_trials(inputs, orbit, window, grid, record=record, record_label=label)
        alt = mean_altitude_km(inputs.trial_sets["mean_motion"].to_numpy(dtype=float))
        by_epoch = dict(zip(pd.to_datetime(inputs.trial_sets["epoch"], utc=True).dt.tz_convert(None), alt, strict=True))
        trials["altitude_km"] = [by_epoch.get(pd.Timestamp(e), np.nan) for e in trials["set_epoch"]]
        trials["mission"] = mission.key
        trials["altitude_band"] = reference.altitude_band_label(float(np.nanmedian(alt)))
    elif orbit is None:
        notes.append("no reconstructed orbit: laser ranging only")
    orbit_vs_slr = None
    sgp4_vs_slr = None
    if with_slr and mission.slr and stations is not None:
        points, have, missing = slr.load_normal_points(
            mission.slr, day_from, day_to, cache_dir=cache_dir, offline=offline
        )
        notes.append(f"{len(points)} normal points on {len(have)} day(s), {len(missing)} day(s) without a file")
        if orbit is not None and len(points):

            def orbit_fn(times: np.ndarray, _orbit: PreciseOrbit = orbit) -> np.ndarray:
                return _orbit.states_teme(np.asarray(times, dtype="datetime64[us]"))[0]

            res = slr.range_residuals(points, orbit_fn, stations)
            orbit_vs_slr = {**slr.residual_summary(res), "dropped": res.attrs.get("dropped", {})}
        if len(points) and n_sets:
            if record is not None:
                excluded = list(record.intervals)
            else:
                excluded = precise.manoeuvre_intervals_from_sets(inputs.sets)
                if orbit is not None:
                    excluded += precise.manoeuvre_intervals_from_orbit(orbit)
            sgp4_vs_slr = _sgp4_residuals_by_lead(mission, window, inputs, points, stations, excluded)
    return MissionWindowRun(mission, window, orbit, record, n_sets, trials, orbit_vs_slr, sgp4_vs_slr, notes)


# --------------------------------------------------------------------------------------
# Summaries


def _q(x: np.ndarray, q: float) -> float | None:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.quantile(x, q)) if x.size else None


def _horizon(by_lead: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"last_lead_h_within": None, "first_lead_h_beyond": None, "quantile_km_there": None}
    for lead in sorted(by_lead, key=float):
        p = by_lead[lead]["in_track"]["p95_km"]
        if p is None:
            continue
        if p <= precise.HORIZON_TOLERANCE_KM and out["first_lead_h_beyond"] is None:
            out["last_lead_h_within"] = float(lead)
        elif out["first_lead_h_beyond"] is None:
            out["first_lead_h_beyond"] = float(lead)
            out["quantile_km_there"] = p
    return out


def summarise_group(frame: pd.DataFrame) -> dict[str, Any]:
    """The Swarm benchmark's per-window summary on any set of trials, plus which missions and sets are in it."""
    usable = frame[~frame["gap"] & ~frame["manoeuvre"] & (frame["sgp4_error"] == 0)]
    by_lead: dict[str, dict[str, Any]] = {}
    for lead, g in usable.groupby("lead_h", sort=True):
        entry: dict[str, Any] = {
            "n": int(len(g)),
            "n_sets": int(g["set_epoch"].nunique()),
            "n_missions": int(g["mission"].nunique()) if "mission" in g else 1,
        }
        for c in ("radial", "in_track", "cross"):
            a = g[f"{c}_km"].abs().to_numpy()
            entry[c] = {
                "median_km": _q(a, 0.5),
                "p68_km": _q(a, 0.68),
                "p95_km": _q(a, 0.95),
                "inside_1_sigma": float(g[f"{c}_inside_1s"].mean()) if len(g) else None,
                "inside_2_sigma": float(g[f"{c}_inside_2s"].mean()) if len(g) else None,
            }
        with_term = g.dropna(subset=["storm_shift_km"])
        raw = with_term["in_track_km"].abs().to_numpy()
        corrected = with_term["in_track_corrected_km"].abs().to_numpy()
        entry["storm_term"] = {
            "n": int(len(with_term)),
            "median_abs_raw_km": _q(raw, 0.5),
            "median_abs_corrected_km": _q(corrected, 0.5),
            "improvement": (1.0 - _q(corrected, 0.5) / _q(raw, 0.5)) if len(with_term) and _q(raw, 0.5) else None,
            "share_of_trials_improved": float((corrected < raw).mean()) if len(with_term) else None,
        }
        by_lead[f"{lead:g}"] = entry
    return {
        "n_sets": int(frame["set_epoch"].nunique()),
        "n_missions": int(frame["mission"].nunique()) if "mission" in frame else 1,
        "missions": sorted(frame["mission"].unique()) if "mission" in frame else [],
        "n_trial_leads": int(len(frame)),
        "n_excluded_gap": int(frame["gap"].sum()),
        "n_excluded_manoeuvre": int((frame["manoeuvre"] & ~frame["gap"]).sum()),
        "altitude_km": {"min": _q(frame["altitude_km"], 0.0), "max": _q(frame["altitude_km"], 1.0)}
        if "altitude_km" in frame
        else None,
        "by_lead_h": by_lead,
        "horizon": _horizon(by_lead),
    }


def summarise_trials(trials: pd.DataFrame) -> dict[str, Any]:
    """By altitude band and window, and by mission and window."""
    out: dict[str, Any] = {"by_band": {}, "by_mission": {}}
    for band, bf in trials.groupby("altitude_band", sort=False):
        out["by_band"][band] = {w: summarise_group(wf) for w, wf in bf.groupby("window", sort=False)}
    for mission, mf in trials.groupby("mission", sort=False):
        out["by_mission"][mission] = {w: summarise_group(wf) for w, wf in mf.groupby("window", sort=False)}
    return out


def summarise_sgp4_vs_slr(frame: pd.DataFrame, missions: dict[str, Mission]) -> dict[str, Any]:
    """By altitude band (from the mission's nominal altitude), window and lead bin: the absolute range residual, km."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    if not len(frame):
        return out
    band = frame["mission"].map(lambda k: reference.altitude_band_label(missions[k].altitude_km))
    frame = frame.assign(altitude_band=band)
    for (b, w), g in frame.groupby(["altitude_band", "window"], sort=False):
        entry: dict[str, Any] = {"missions": sorted(g["mission"].unique()), "n_sets": int(g["set_epoch"].nunique())}
        for lead, gl in g.groupby("lead_bin_h", sort=True):
            a = np.abs(gl["residual_m"].to_numpy(dtype=float)) / 1000.0
            entry[f"{lead:g}"] = {
                "n": int(len(gl)),
                "n_sets": int(gl["set_epoch"].nunique()),
                "median_km": _q(a, 0.5),
                "p95_km": _q(a, 0.95),
            }
        out.setdefault(str(b), {})[str(w)] = entry
    return out


def summarise_sgp4_vs_slr_by_mission(frame: pd.DataFrame) -> dict[str, Any]:
    """By mission, window and lead bin: the absolute range residual of the element set against the laser, km."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    if not len(frame):
        return out
    for (m, w), g in frame.groupby(["mission", "window"], sort=False):
        entry: dict[str, Any] = {"n_sets": int(g["set_epoch"].nunique()), "n_stations": int(g["station"].nunique())}
        for lead, gl in g.groupby("lead_bin_h", sort=True):
            a = np.abs(gl["residual_m"].to_numpy(dtype=float)) / 1000.0
            entry[f"{lead:g}"] = {
                "n": int(len(gl)),
                "n_sets": int(gl["set_epoch"].nunique()),
                "median_km": _q(a, 0.5),
                "p95_km": _q(a, 0.95),
            }
        out.setdefault(str(m), {})[str(w)] = entry
    return out


def rebuild_summary(
    summary: dict[str, Any],
    trials: pd.DataFrame,
    sgp4_vs_slr: pd.DataFrame,
    missions: list[Mission],
    windows: list[BenchmarkWindow],
) -> dict[str, Any]:
    """The parts of a stored summary that derive from the per-trial files, recomputed from them."""
    mission_map = {m.key: m for m in missions}
    out = dict(summary)
    out["results"] = summarise_trials(trials) if len(trials) else {"by_band": {}, "by_mission": {}}
    out["sgp4_vs_slr"] = summarise_sgp4_vs_slr(sgp4_vs_slr, mission_map)
    out["sgp4_vs_slr_by_mission"] = summarise_sgp4_vs_slr_by_mission(sgp4_vs_slr)
    out["population"] = population_statement(missions, windows, trials)
    return out


# --------------------------------------------------------------------------------------
# The run


@dataclass
class ReferenceResult:
    trials: pd.DataFrame
    sgp4_vs_slr: pd.DataFrame
    runs: list[MissionWindowRun]
    summary: dict[str, Any]
    built_at: datetime


def run_reference(
    missions: list[Mission],
    windows: list[BenchmarkWindow],
    *,
    grid: dn.WeatherGrid | None,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    with_slr: bool = True,
) -> ReferenceResult:
    now = datetime.now(UTC)
    sets = load_sets(missions, windows)
    if not len(sets):
        raise RuntimeError("no element sets in the history store for the missions asked for")
    stations = slr.load_stations(cache_dir=cache_dir, offline=offline) if with_slr else None
    runs: list[MissionWindowRun] = []
    for mission in missions:
        for window in windows:
            try:
                run = run_mission_window(
                    mission,
                    window,
                    sets,
                    grid,
                    stations=stations,
                    cache_dir=cache_dir,
                    offline=offline,
                    with_slr=with_slr,
                )
            except Exception as exc:  # one mission's failure must not take the table down; it is reported
                log.exception("%s, %s window failed: %s", mission.name, window.name, exc)
                run = MissionWindowRun(mission, window, None, None, 0, None, None, None, [f"failed: {exc}"])
            runs.append(run)
    trial_frames = [r.trials for r in runs if r.trials is not None and len(r.trials)]
    trials = pd.concat(trial_frames, ignore_index=True) if trial_frames else pd.DataFrame()
    slr_frames = [r.sgp4_vs_slr for r in runs if r.sgp4_vs_slr is not None and len(r.sgp4_vs_slr)]
    sgp4_vs_slr = pd.concat(slr_frames, ignore_index=True) if slr_frames else pd.DataFrame()
    mission_map = {m.key: m for m in missions}
    summary: dict[str, Any] = {
        "trial": "one element set; one residual per lead bin",
        "windows": {w.name: w.as_dict() for w in windows},
        "missions": {
            m.key: {
                "name": m.name,
                "norad_id": m.norad_id,
                "altitude_km_nominal": m.altitude_km,
                "altitude_band": reference.altitude_band_label(m.altitude_km),
                "truth": m.truth,
                "truth_source": reference.truth_source(m),
                "manoeuvres": reference.manoeuvre_source(m),
                "slr": m.slr,
                "note": m.note,
            }
            for m in missions
        },
        "not_covered": dict(reference.NOT_COVERED),
        "coverage": {
            m.key: {
                w.name: {
                    "n_trial_sets": r.n_trial_sets,
                    "truth_states": 0 if r.orbit is None else int(len(r.orbit.table)),
                    "truth_days_missing": [] if r.orbit is None else [d.isoformat() for d in r.orbit.days_missing],
                    "truth_files": 0 if r.orbit is None else len(r.orbit.files),
                    "manoeuvres_recorded": None
                    if r.record is None
                    else [[a.isoformat(), b.isoformat()] for a, b in r.record.intervals],
                    "orbit_vs_slr": r.orbit_vs_slr,
                    "notes": r.notes,
                }
                for w in windows
                for r in runs
                if r.mission.key == m.key and r.window.name == w.name
            }
            for m in missions
        },
        "results": summarise_trials(trials) if len(trials) else {"by_band": {}, "by_mission": {}},
        "sgp4_vs_slr": summarise_sgp4_vs_slr(sgp4_vs_slr, mission_map),
        "sgp4_vs_slr_by_mission": summarise_sgp4_vs_slr_by_mission(sgp4_vs_slr),
        "population": population_statement(missions, windows, trials),
    }
    return ReferenceResult(trials, sgp4_vs_slr, runs, summary, now)


def population_statement(missions: list[Mission], windows: list[BenchmarkWindow], trials: pd.DataFrame) -> str:
    """The sentence every downstream page may claim, computed from what was actually scored."""
    if not len(trials):
        return "No trials were scored."
    usable = trials[~trials["gap"] & ~trials["manoeuvre"] & (trials["sgp4_error"] == 0)]
    names = {m.key: m.name for m in missions}
    parts = []
    for band, bf in usable.groupby("altitude_band", sort=False):
        ms = sorted({names[k] for k in bf["mission"].unique()})
        parts.append(
            f"{band}: {', '.join(ms)} ({bf['set_epoch'].nunique()} element sets, {bf['altitude_km'].min():.0f} to "
            f"{bf['altitude_km'].max():.0f} km)"
        )
    return (
        "The measured population is "
        + "; ".join(parts)
        + f"; {len(windows)} windows of one week of element sets each; near-circular, free-flying between manoeuvres, "
        "with manoeuvre arcs excluded from a published record where one exists and from detection otherwise. "
        "Nothing here is measured for debris, for eccentric orbits, for station-kept constellations, for objects "
        "the network tracks less often, or above 1,340 km."
    )


# --------------------------------------------------------------------------------------
# The page


def _lead(h: float) -> str:
    return f"{h:g} h" if h < 48 else f"{h / 24:g} d"


def _horizon_text(h: dict[str, Any]) -> str:
    within, beyond = h.get("last_lead_h_within"), h.get("first_lead_h_beyond")
    if within is None and beyond is None:
        return "-"
    if beyond is None:
        return f"{_lead(within)} (every lead measured)"
    if within is None:
        return f"under {_lead(beyond)} ({h['quantile_km_there']:.0f} km there)"
    return f"{_lead(within)} ({h['quantile_km_there']:.0f} km at {_lead(beyond)})"


def to_markdown(result: ReferenceResult, windows: list[BenchmarkWindow], missions: list[Mission]) -> str:
    s = result.summary
    order = [w.name for w in windows]
    bands = [b for _, _, b in reference.ALTITUDE_BANDS if b in s["results"]["by_band"]]
    lines = [
        "# Calibration against reference orbits: the population beyond Swarm",
        "",
        "Every number here is computed from the per-trial file beside `reference_benchmark.json`. The method is the "
        "Swarm benchmark's (`docs/calibration-benchmark.md`): every public element set issued in a window is one "
        "trial, propagated with SGP4 to leads from six hours to seven days and measured against the mission's "
        "reconstructed orbit in the satellite's radial, in-track, cross-track frame; the covariance and the ballistic "
        "coefficient on a window are fitted from history that ends where the window's sets begin. Two windows are held "
        "out from every tuning, October 2024 as before and August 2024 added here. Laser ranging is the second, "
        "independent truth where a mission carries a retroreflector: it is compared with the reconstructed orbit "
        "first, so that the disagreement between the two references is on the page before either is compared with "
        "an element set.",
        "",
        f"**Population.** {s['population']}",
        "",
        "## Windows",
        "",
        "| Window | Role | Element sets issued | Truth needed to | Disturbed interval | Note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for w in windows:
        d = f"{w.disturbed[0]:%Y-%m-%d %H:%M} to {w.disturbed[1]:%Y-%m-%d %H:%M}" if w.disturbed else "none"
        lines.append(
            f"| {w.name} | {w.role} | {w.sets_from:%Y-%m-%d} to {w.sets_to:%Y-%m-%d} | {w.truth_to:%Y-%m-%d} "
            f"| {d} | {w.note} |"
        )
    lines += [
        "",
        "## Missions and their truth",
        "",
        "| Mission | NORAD | Band | Reconstructed orbit | Manoeuvres | Laser ranging | Sets per window ("
        + ", ".join(order)
        + ") | Truth coverage |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for m in missions:
        cov = s["coverage"][m.key]
        n_sets = ", ".join(str(cov[w]["n_trial_sets"]) for w in order)
        gaps = []
        for w in order:
            c = cov[w]
            if c["truth_states"] == 0:
                gaps.append(f"{w}: none")
            elif c["truth_days_missing"]:
                gaps.append(f"{w}: {len(c['truth_days_missing'])} day(s) missing")
        coverage = "; ".join(gaps) if gaps else "complete"
        truth = {
            reference.TRUTH_SWARM: "ESA Swarm SP3 (TU Delft)",
            reference.TRUTH_GRACEFO: "JPL GNV1B via GFZ ISDC",
            reference.TRUTH_CNES: "CNES POE via IDS",
            reference.TRUTH_S1: "Copernicus POEORB via ESA STEP",
            reference.TRUTH_NONE: "none anonymous",
        }[m.truth]
        man = {
            reference.MANOEUVRES_ESA: "ESA thruster record",
            reference.MANOEUVRES_GRACEFO: "THR1B thruster record",
            reference.MANOEUVRES_DETECTION: "detection",
        }[m.manoeuvres]
        lines.append(
            f"| {m.name} | {m.norad_id} | {reference.altitude_band_label(m.altitude_km)} | {truth} | {man} | "
            f"{m.slr or 'none'} | {n_sets} | {coverage} |"
        )
    lines += ["", "**Asked for and not obtainable without an account, said rather than substituted.**", ""]
    for k, v in s["not_covered"].items():
        lines.append(f"- **{k}.** {v}")
    lines += [
        "",
        "## The horizon by altitude band and window",
        "",
        f"Task: in-track residual within {precise.HORIZON_TOLERANCE_KM:g} km, the screening box's half-width, at the "
        f"{precise.HORIZON_QUANTILE:.0%} of trials; the last lead within it, with the 95th percentile at the first "
        "lead beyond it in brackets.",
        "",
        "| Altitude band | Missions | " + " | ".join(order) + " |",
        "| --- | --- | " + " | ".join("---" for _ in order) + " |",
    ]
    names = {m.key: m.name for m in missions}
    for b in bands:
        by_w = s["results"]["by_band"][b]
        ms = sorted({names.get(k, k) for w in by_w.values() for k in w["missions"]})
        cells = [_horizon_text(by_w[w]["horizon"]) if w in by_w else "-" for w in order]
        lines.append(f"| {b} | {', '.join(ms)} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "### The in-track residual by band, window and lead",
        "",
        "Median and 95th percentile of the absolute in-track residual, km, with the number of trials; per band and "
        "window.",
        "",
    ]
    for b in bands:
        by_w = s["results"]["by_band"][b]
        lines += [
            f"**{b}.**",
            "",
            "| Lead | " + " | ".join(f"{w}: n, median, p95" for w in order) + " |",
            "| ---: | " + " | ".join("---" for _ in order) + " |",
        ]
        leads = sorted({float(k) for w in by_w.values() for k in w["by_lead_h"]})
        for lead in leads:
            cells = []
            for w in order:
                e = by_w.get(w, {}).get("by_lead_h", {}).get(f"{lead:g}")
                if e is None:
                    cells.append("-")
                else:
                    cells.append(f"{e['n']}, {e['in_track']['median_km']:.2f}, {e['in_track']['p95_km']:.1f}")
            lines.append(f"| {_lead(lead)} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += [
        "### Coverage of the empirical covariance, and the storm term, by band",
        "",
        "The share of in-track residuals inside two sigma of the covariance the screening would have carried (95 per "
        "cent claimed), and the storm term's change to the median absolute in-track residual, at one, three and seven "
        "days; a positive improvement means the term brought the prediction closer to the truth. The term needs a "
        "ballistic coefficient fitted from the object's own decay, which is not measurable at the higher altitudes, so "
        "those cells are empty.",
        "",
        "| Band | Window | 2σ at 24 h / 72 h / 168 h | Storm term at 24 h / 72 h / 168 h |",
        "| --- | --- | --- | --- |",
    ]
    for b in bands:
        for w in order:
            e = s["results"]["by_band"][b].get(w)
            if e is None:
                continue
            cov_cells, term_cells = [], []
            for lead in ("24", "72", "168"):
                x = e["by_lead_h"].get(lead)
                if x is None:
                    cov_cells.append("-")
                    term_cells.append("-")
                    continue
                cov_cells.append(f"{x['in_track']['inside_2_sigma']:.0%}")
                t = x["storm_term"]
                term_cells.append(f"{t['improvement']:+.0%}" if t["n"] and t["improvement"] is not None else "-")
            lines.append(f"| {b} | {w} | {' / '.join(cov_cells)} | {' / '.join(term_cells)} |")
    lines += [
        "",
        "## The horizon by mission and window",
        "",
        "| Mission | Band | " + " | ".join(order) + " |",
        "| --- | --- | " + " | ".join("---" for _ in order) + " |",
    ]
    for m in missions:
        by_w = s["results"]["by_mission"].get(m.key)
        if not by_w:
            continue
        cells = [
            _horizon_text(by_w[w]["horizon"]) + f" ({by_w[w]['n_sets']} sets)" if w in by_w else "-" for w in order
        ]
        lines.append(f"| {m.name} | {reference.altitude_band_label(m.altitude_km)} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Laser ranging: how the two references disagree",
        "",
        "Observed minus predicted one-way range of the reconstructed orbit against every ILRS normal point of the "
        "window above 20 degrees of elevation, metres: the median, the RMS and the 95th percentile of the absolute "
        "residual, with the number of points and stations. Marini-Murray troposphere from the station's own "
        "meteorology; station coordinates SLRF2020 with the ILRS site eccentricities; the retroreflector's offset from "
        "the centre of mass is not applied, so the figures bound the disagreement at the metre level and do not "
        "validate either product at its own centimetre level.",
        "",
        "| Mission | Window | n | Stations | Median (m) | RMS (m) | p95 of |residual| (m) |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in missions:
        for w in order:
            o = s["coverage"][m.key][w]["orbit_vs_slr"]
            if not o or not o.get("n"):
                continue
            lines.append(
                f"| {m.name} | {w} | {o['n']} | {o['n_stations']} | {o['median_m']:+.2f} | {o['rms_m']:.2f} "
                f"| {o['p95_abs_m']:.2f} |"
            )
    lines += [
        "",
        "### The element set against the laser, by band, window and lead",
        "",
        "The same range residual for each element set's SGP4 propagation to the normal points inside its leads, km, "
        "absolute, median and 95th percentile with the number of points and sets. A range residual is one projection "
        "of the position error, so it is smaller than the in-track residual it accompanies; for the missions without a "
        "reconstructed orbit it is the only truth.",
        "",
        "| Band | Window | Missions | 6 h | 24 h | 72 h | 168 h |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for b, by_w in s["sgp4_vs_slr"].items():
        for w in order:
            e = by_w.get(w)
            if e is None:
                continue
            cells = []
            for lead in ("6", "24", "72", "168"):
                x = e.get(lead)
                cells.append(
                    "-" if x is None else f"{x['median_km']:.2f} / {x['p95_km']:.1f} ({x['n']}, {x['n_sets']})"
                )
            ms = ", ".join(names.get(k, k) for k in e["missions"])
            lines.append(f"| {b} | {w} | {ms} | " + " | ".join(cells) + " |")
    laser_only = [m for m in missions if m.truth == reference.TRUTH_NONE and m.slr]
    by_mission = s.get("sgp4_vs_slr_by_mission", {})
    if laser_only and by_mission:
        lines += [
            "",
            "### The missions whose only truth is the laser",
            "",
            "The same range residual per mission and window for the missions with no reconstructed orbit on an "
            "anonymous server: this is all that is measured for them, and the per-mission rows for every other "
            "mission are in the JSON beside this page.",
            "",
            "| Mission | Window | Sets, stations | 6 h | 24 h | 72 h | 168 h |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for m in laser_only:
            for w in order:
                e = by_mission.get(m.key, {}).get(w)
                if e is None:
                    continue
                cells = []
                for lead in ("6", "24", "72", "168"):
                    x = e.get(lead)
                    cells.append("-" if x is None else f"{x['median_km']:.2f} / {x['p95_km']:.1f} ({x['n']})")
                lines.append(f"| {m.name} | {w} | {e['n_sets']}, {e['n_stations']} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Sources, with origin and derivation",
        "",
    ]
    for src in reference.mission_sources_record(missions, result.built_at):
        if "items" in src:
            lines.append(f"- **{src['source']}.** " + " ".join(f"{k}: {v}." for k, v in src["items"].items()))
        else:
            lines.append(
                f"- **{src['source']}.** Retrieved {src['retrieved_at'][:10]}. Missions: {', '.join(src['missions'])}."
            )
    lines += [
        f"- **Laser ranging.** {slr.EDC_SOURCE}; {slr.SLRF2020_SOURCE}; {slr.ECCENTRICITY_SOURCE}. Derivation: one-way "
        "range as the mean of the up and down legs with the light time iterated in TEME; Marini-Murray troposphere; "
        "elevation cut 20 degrees; no centre-of-mass correction.",
        "- **Public element sets.** Space-Track gp_history through driftwatch's history backfill, each set propagated "
        f"with sgp4 to leads {list(precise.LEADS_HOURS)} hours from its epoch; covariance from the "
        f"{precise.COVARIANCE_HISTORY_DAYS} days before each window, coefficient from the "
        f"{precise.COEFFICIENT_HISTORY_DAYS}.",
        "",
        "## What this does not show",
        "",
        "- One week of sets per window and per mission; a mission's horizon rests on a few dozen sets.",
        "- No published manoeuvre record was found on an anonymous server for the CNES, Copernicus and laser-only "
        "missions, so detection decides their exclusions; a burn the detector misses lengthens a residual, and a storm "
        "the detector reads as a burn removes a trial. Both directions are possible and neither is measured here.",
        "- The laser comparison bounds the reconstructed orbits at the metre level only, for the reasons above.",
        "- Jason-3 and Sentinel-6A fly at 1,336 km, just above the 1,300 km asked for; they are the top of the range.",
        "",
        f"_Last updated {result.built_at:%d %B %Y}._",
    ]
    return "\n".join(lines) + "\n"
