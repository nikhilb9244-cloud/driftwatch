"""Running the reference expansion: every mission through the benchmark, the laser checks, and the page.

One mission-window is one call of :func:`run_mission_window`: the truth is loaded, the element
sets fitted from history that ends where the window's sets begin (the same rule and the same
functions as the Swarm benchmark), one trial per element set is scored against the truth in the
satellite's radial, in-track, cross-track frame, and, where the mission has a retroreflector, the
laser-ranging normal points of the window are compared with the truth (how the two references
disagree) and with each element set's propagation (a one-dimensional range residual by lead).
The tables are then by altitude band and window, and by mission and window.

All four windows have been inspected. Historical held-out names do not establish
untouched evaluation populations. Covariance and coefficient fits use history
before the trial epochs in each window; epoch selection is not publication evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from driftwatch import config
from driftwatch.catalogue import history
from driftwatch.drag import density as dn
from driftwatch.orbit.propagator import build_satrecs
from driftwatch.storm import benchmark_statistics, precise, reference, slr
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
    # What the two detectors found, recorded whether or not a record decided the exclusions.
    manoeuvres_detected_orbit: list[tuple[pd.Timestamp, pd.Timestamp]] = field(default_factory=list)
    manoeuvres_detected_sets: list[tuple[pd.Timestamp, pd.Timestamp]] = field(default_factory=list)
    # The first sets after each burn, classified by how much of the burn their semi-major axis contains.
    post_burn_fits: list[dict[str, Any]] = field(default_factory=list)


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
    if record is not None and (not getattr(record, "authoritative", True) or record.days_missing):
        raise RuntimeError(
            f"published manoeuvre coverage unavailable for {mission.key}: "
            f"{getattr(record, 'issues', record.days_missing)}"
        )
    if orbit is not None and not len(orbit.table):
        notes.append("no truth states in the window")
        orbit = None
    inputs = precise.fit_inputs(
        mission.norad_id, sets, window, grid, label=mission.key, category="payload", altitude_band="leo"
    )
    n_sets = len(inputs.trial_sets)
    # Both detectors once per mission-window, kept with the result: they decide the exclusions where
    # no record exists, and the post-burn table needs the intervals back.
    detected_orbit = precise.manoeuvre_intervals_from_orbit(orbit) if orbit is not None else []
    detected_sets = precise.manoeuvre_intervals_from_sets(inputs.sets) if len(inputs.sets) else []
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
    fits: list[dict[str, Any]] = []
    if orbit is not None and n_sets:
        label = getattr(record, "source_id", None) or {
            reference.MANOEUVRES_ESA: "esa-record",
            reference.MANOEUVRES_GRACEFO: "thr1b-record",
        }.get(mission.manoeuvres, "published-record")
        trials = precise.satellite_trials(
            inputs, orbit, window, grid, record=record, record_label=label, detected=detected_orbit + detected_sets
        )
        alt = mean_altitude_km(inputs.trial_sets["mean_motion"].to_numpy(dtype=float))
        by_epoch = dict(zip(pd.to_datetime(inputs.trial_sets["epoch"], utc=True).dt.tz_convert(None), alt, strict=True))
        trials["altitude_km"] = [by_epoch.get(pd.Timestamp(e), np.nan) for e in trials["set_epoch"]]
        trials["mission"] = mission.key
        trials["altitude_band"] = reference.altitude_band_label(float(np.nanmedian(alt)))
        burns = list(record.intervals) if record is not None else detected_orbit
        fits = precise.post_burn_fits(inputs.trial_sets, orbit, burns)
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
            excluded = list(record.intervals) if record is not None else detected_sets + detected_orbit
            sgp4_vs_slr = _sgp4_residuals_by_lead(mission, window, inputs, points, stations, excluded)
    return MissionWindowRun(
        mission,
        window,
        orbit,
        record,
        n_sets,
        trials,
        orbit_vs_slr,
        sgp4_vs_slr,
        notes,
        detected_orbit,
        detected_sets,
        fits,
    )


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


def _legacy_summarise_group(frame: pd.DataFrame) -> dict[str, Any]:
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


def summarise_group(frame: pd.DataFrame, *, include_sensitivities: bool = True) -> dict[str, Any]:
    """Auditable denominators and brackets, with aliases for existing consumers."""
    out = benchmark_statistics.summarise_group(
        frame,
        leads_hours=precise.LEADS_HOURS,
        tolerance_km=precise.HORIZON_TOLERANCE_KM,
        include_sensitivities=include_sensitivities,
    )
    legacy = _legacy_summarise_group(frame)
    for key in ("n_missions", "n_excluded_gap", "n_excluded_manoeuvre", "altitude_km"):
        out[key] = legacy[key]
    out["n_sets"] = out["n_sets_total"]
    for lead, cell in out["by_lead_h"].items():
        g = frame[(frame["lead_h"] == float(lead)) & ~frame["gap"] & ~frame["manoeuvre"] & (frame["sgp4_error"] == 0)]
        for component, component_result in cell["components"].items():
            cov = component_result["coverage"] or {}
            cell[component] = {
                "median_km": component_result["median_abs_km"],
                "p68_km": _q(g[f"{component}_km"].abs().to_numpy(), 0.68),
                "p95_km": component_result["quantile_abs_km"]["linear"],
                "inside_1_sigma": cov.get("inside_1_sigma_fraction"),
                "inside_2_sigma": cov.get("inside_2_sigma_fraction"),
            }
        sources = g["b_source"].value_counts().to_dict() if "b_source" in g else {}
        supported = g[g["b_source"].eq("history")] if "b_source" in g else g.iloc[:0]
        supported = supported.dropna(subset=["storm_shift_km", "in_track_corrected_km"])
        raw = supported["in_track_km"].abs().to_numpy()
        corrected = supported["in_track_corrected_km"].abs().to_numpy()
        raw_median, corrected_median = _q(raw, 0.5), _q(corrected, 0.5)
        cell["storm_term"] = {
            "status": "supported_history_coefficient" if len(supported) else "unsupported",
            "coefficient_source_counts": sources,
            "n": len(supported),
            "n_unsupported": len(g) - len(supported),
            "median_abs_raw_km": raw_median,
            "median_abs_corrected_km": corrected_median,
            "median_abs_shift_km": _q(supported["storm_shift_km"].abs().to_numpy(), 0.5),
            "improvement": 1 - corrected_median / raw_median if raw_median else None,
            "share_of_trials_improved": float((corrected < raw).mean()) if len(supported) else None,
        }
    return out


def summarise_trials(trials: pd.DataFrame) -> dict[str, Any]:
    """By altitude band and window, and by mission and window."""
    out: dict[str, Any] = {"by_band": {}, "by_mission": {}}
    for band, bf in trials.groupby("altitude_band", sort=False):
        out["by_band"][band] = {w: summarise_group(wf) for w, wf in bf.groupby("window", sort=False)}
    for mission, mf in trials.groupby("mission", sort=False):
        out["by_mission"][mission] = {
            w: summarise_group(wf, include_sensitivities=False) for w, wf in mf.groupby("window", sort=False)
        }
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


# --------------------------------------------------------------------------------------
# The first element sets after a burn

# The leads at which the first sets after a burn are tabulated, and how many sets after each burn.
POST_BURN_LEADS_H: tuple[float, ...] = (24.0, 72.0, 96.0, 168.0)
POST_BURN_SETS = 3


def _naive(ts: Any) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    return t.tz_convert(None) if t.tzinfo else t


def detector_crosscheck(
    recorded: list[tuple[pd.Timestamp, pd.Timestamp]] | None,
    detected: list[tuple[pd.Timestamp, pd.Timestamp]],
) -> dict[str, Any]:
    """Event-level overlap with published intervals; absence from a registry is not proof of no burn."""
    if recorded is None:
        return {"reference_available": False, "record_count": None, "misses": None, "unmatched_detections": None}
    misses = [(a, b) for a, b in recorded if not precise._overlaps(detected, _naive(a), _naive(b))]
    unmatched = [(a, b) for a, b in detected if not precise._overlaps(recorded, _naive(a), _naive(b))]
    return {
        "reference_available": True,
        "record_count": len(recorded),
        "matched_record_count": len(recorded) - len(misses),
        "misses": [[a.isoformat(), b.isoformat()] for a, b in misses],
        "unmatched_detections": [[a.isoformat(), b.isoformat()] for a, b in unmatched],
        "matching_rule": "closed-interval overlap; detector intervals retain their timing uncertainty",
        "limitation": "published registry completeness is not established by an empty interval list",
    }


def record_provenance(record: ThrusterRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        **(record.as_metadata() if hasattr(record, "as_metadata") else {}),
        "source_id": getattr(record, "source_id", "spacecraft-thruster-product"),
        "files": record.files,
        "days_missing": [d.isoformat() for d in record.days_missing],
        "sources": getattr(record, "provenance", []),
        "coverage_status": getattr(record, "coverage_status", "daily-products-complete"),
        "issues": getattr(record, "issues", []),
    }


def burn_intervals(entry: dict[str, Any]) -> tuple[list[tuple[pd.Timestamp, pd.Timestamp]], str]:
    """The burns a mission-window's exclusion rests on: the published record's where one exists, otherwise the
    orbit-step detector's on the reconstructed orbit. The set-jump detector's intervals are not burns by
    themselves (a storm produces them too) and are not read as burns here."""
    recorded = entry.get("manoeuvres_recorded")
    if recorded is not None:
        return [(_naive(a), _naive(b)) for a, b in recorded], "record"
    return [(_naive(a), _naive(b)) for a, b in entry.get("manoeuvres_detected_orbit") or []], "orbit-step"


def _spearman(x: Any, y: Any) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 4:
        return {"n": int(m.sum()), "rho": None, "p": None}
    rho, p = stats.spearmanr(x[m], y[m])
    return {"n": int(m.sum()), "rho": float(rho), "p": float(p)}


def summarise_post_burn(trials: pd.DataFrame, coverage: dict[str, Any], windows: dict[str, Any]) -> dict[str, Any]:
    """Every burn inside a window's set span with a set issued after it, and what the first sets after it did.

    Per burn: the mission's cadence in the window (the median gap between consecutive trial-set
    epochs), then for the first ``POST_BURN_SETS`` sets issued after the burn the delay from the
    burn and the absolute in-track residual at ``POST_BURN_LEADS_H``, beside the median of the
    window's usable trials at the same leads for scale. The delay is measured from the burn
    interval's midpoint, so for a detected burn it carries the detector's resolution of about an
    orbit either side. A pair whose own arc, from its epoch to the lead, reaches a later burn is
    left blank. The rank correlations of the first set's residual with the cadence and with the
    delay are given per burn and per spacecraft (means over each spacecraft's burns), because one
    spacecraft's burns are not independent of one another.
    """
    leads = POST_BURN_LEADS_H
    empty = {
        "leads_h": list(leads),
        "sets_after": POST_BURN_SETS,
        "burns": [],
        "burns_without_a_set_after": [],
        "burns_after_the_span": [],
        "rank_correlation": {},
    }
    if not len(trials):
        return empty
    t = trials.assign(set_epoch=pd.to_datetime(trials["set_epoch"]), t=pd.to_datetime(trials["t"]))
    burns: list[dict[str, Any]] = []
    without: list[dict[str, Any]] = []
    after_span: list[dict[str, Any]] = []
    for mission, by_w in coverage.items():
        for wname, entry in by_w.items():
            w = windows.get(wname)
            if w is None:
                continue
            sets_from, sets_to = _naive(w["sets_from"]), _naive(w["sets_to"])
            intervals, source = burn_intervals(entry)
            detected_sets = [(_naive(a), _naive(b)) for a, b in entry.get("manoeuvres_detected_sets") or []]
            g = t[(t["mission"] == mission) & (t["window"] == wname)]
            epochs = np.array(sorted(g["set_epoch"].unique()), dtype="datetime64[us]")
            for lo, hi in intervals:
                head = {
                    "mission": mission,
                    "window": wname,
                    "source": source,
                    "burn_from": lo.isoformat(),
                    "burn_to": hi.isoformat(),
                }
                if lo >= sets_to:
                    after_span.append(head)
                    continue
                if hi < sets_from:
                    continue
                after = [pd.Timestamp(e) for e in epochs if pd.Timestamp(e) > hi]
                if not after or len(epochs) < 2:
                    without.append(head)
                    continue
                mid = lo + (hi - lo) / 2
                fit = next(
                    (
                        f
                        for f in entry.get("post_burn_fits") or []
                        if _naive(f["burn_from"]) == lo and _naive(f["burn_to"]) == hi
                    ),
                    None,
                )
                usable = g[~g["gap"] & ~g["manoeuvre"] & (g["sgp4_error"] == 0)]
                clear = {
                    f"{ld:g}": _q(usable[usable["lead_h"] == ld]["in_track_km"].abs().to_numpy(), 0.5) for ld in leads
                }
                later_intervals = intervals if source == "record" else intervals + detected_sets
                later = [(a, b) for a, b in later_intervals if a > mid]
                rows = []
                for k, epoch in enumerate(after[:POST_BURN_SETS], start=1):
                    sub = g[g["set_epoch"] == epoch]
                    residual: dict[str, float | None] = {}
                    signed: dict[str, float | None] = {}
                    for ld in leads:
                        r = sub[sub["lead_h"] == ld]
                        value = None
                        signed_value = None
                        if len(r):
                            r0 = r.iloc[0]
                            reaches_later = any(a <= r0["t"] and b >= epoch for a, b in later)
                            clean = not bool(r0["gap"]) and int(r0["sgp4_error"]) == 0
                            if not reaches_later and clean and np.isfinite(r0["in_track_km"]):
                                value = float(abs(r0["in_track_km"]))
                                signed_value = float(r0["in_track_km"])
                        residual[f"{ld:g}"] = value
                        signed[f"{ld:g}"] = signed_value
                    fit_set = None
                    if fit is not None:
                        fit_set = next((s for s in fit["sets_after"] if _naive(s["epoch"]) == epoch), None)
                    rows.append(
                        {
                            "k": k,
                            "epoch": epoch.isoformat(),
                            "delay_h": float((epoch - mid).total_seconds() / 3600.0),
                            "in_track_km": residual,
                            "in_track_signed_km": signed,
                            "a_error_m": None if fit_set is None else fit_set["a_error_m"],
                            "fraction": None if fit_set is None else fit_set["fraction"],
                            "class": None if fit_set is None else fit_set["class"],
                            "predicted_in_track_km": {} if fit_set is None else fit_set["predicted_in_track_km"],
                        }
                    )
                burns.append(
                    {
                        **head,
                        "burn_mid": mid.isoformat(),
                        "cadence_h": float(np.median(np.diff(epochs) / np.timedelta64(1, "h"))),
                        "n_sets": int(len(epochs)),
                        "n_sets_after": len(after),
                        "clear_median_km": clear,
                        "delta_a_m": None if fit is None else fit["delta_a_m"],
                        "offset_m": None if fit is None else fit["offset_m"],
                        "sigma_m": None if fit is None else fit["sigma_m"],
                        "n_clean_sets": None if fit is None else fit["n_clean_sets"],
                        "sets_after": rows,
                    }
                )
    corr: dict[str, Any] = {}
    if burns:
        keys = [f"{ld:g}" for ld in leads]
        cadence = np.array([b["cadence_h"] for b in burns])
        delay = np.array([b["sets_after"][0]["delay_h"] for b in burns])
        first = {
            key: np.array(
                [
                    np.nan if b["sets_after"][0]["in_track_km"][key] is None else b["sets_after"][0]["in_track_km"][key]
                    for b in burns
                ]
            )
            for key in keys
        }
        frame = pd.DataFrame({"mission": [b["mission"] for b in burns], "cadence": cadence, "delay": delay, **first})
        means = frame.groupby("mission").mean(numeric_only=True)
        corr = {
            "per_burn": {
                "n": len(burns),
                "cadence": {k: _spearman(cadence, first[k]) for k in keys},
                "delay": {k: _spearman(delay, first[k]) for k in keys},
            },
            "per_spacecraft": {
                "n": int(len(means)),
                "cadence": {k: _spearman(means["cadence"], means[k]) for k in keys},
                "delay": {k: _spearman(means["delay"], means[k]) for k in keys},
            },
        }
    return {
        **empty,
        "burns": burns,
        "burns_without_a_set_after": without,
        "burns_after_the_span": after_span,
        "rank_correlation": corr,
    }


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
    out["results"]["post_burn"] = summarise_post_burn(trials, out.get("coverage", {}), out.get("windows", {}))
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
        "execution": {
            "requested_mission_windows": len(missions) * len(windows),
            "failed_mission_windows": [
                {"mission": r.mission.key, "window": r.window.name, "notes": r.notes}
                for r in runs
                if any(note.startswith("failed:") for note in r.notes)
            ],
        },
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
                    "manoeuvre_record_provenance": record_provenance(r.record),
                    "orbit_detector_crosscheck": detector_crosscheck(
                        None if r.record is None else r.record.intervals, r.manoeuvres_detected_orbit
                    ),
                    "element_detector_crosscheck": detector_crosscheck(
                        None if r.record is None else r.record.intervals, r.manoeuvres_detected_sets
                    ),
                    "manoeuvres_detected_orbit": [
                        [a.isoformat(), b.isoformat()] for a, b in r.manoeuvres_detected_orbit
                    ],
                    "manoeuvres_detected_sets": [[a.isoformat(), b.isoformat()] for a, b in r.manoeuvres_detected_sets],
                    "post_burn_fits": r.post_burn_fits,
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
    summary["results"]["post_burn"] = summarise_post_burn(trials, summary["coverage"], summary["windows"])
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
        + f"; {len(windows)} windows with epoch bounds stated in the result; "
        "near-circular, free-flying between manoeuvres, "
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
    passed = "none" if within is None else _lead(within)
    if beyond is not None:
        return f"last passing {passed}; first failing {_lead(beyond)}"
    if h.get("termination") == "longest_tested_lead":
        return "passes through the longest tested lead"
    return f"last passing {passed}; no measured failure; coverage censored"


# The methodology correction of 7 September 2026 stays on the page, with the two tables as they stood before it.
CORRECTION_2026_09_07 = [
    "",
    "## Methodology correction, 7 September 2026: one manoeuvre-exclusion rule on both paths",
    "",
    "Manoeuvre arcs are excluded on two paths. Where a published thruster record exists (Swarm, GRACE-FO), the "
    "record path has from the first run dropped every set-lead pair with a burn between 24 hours before the "
    "set's epoch, the tracking arc the set was fitted from, and the lead's time. Where no record exists (the "
    "CNES, Copernicus and laser-only missions) detection decides, and until 7 September 2026 the detection path "
    "dropped only the pairs whose propagation arc, from the epoch to the lead, crossed a detected burn: a set "
    "fitted across a burn in the 24 hours before its epoch was kept. The record path's rule was extended to the "
    "detection path without change, the same 24-hour arc (`precise.MANOEUVRE_ARC_HOURS`) on both, and the "
    "benchmark was rerun with nothing else altered.",
    "",
    "The extension was applied after the results on the held-out windows had been seen: Sentinel-3B's October "
    "figure, 3 d against Sentinel-3A's 7 d in the same orbit, is what exposed the difference between the two "
    "paths. The rule and its arc were fixed on the record path before any held-out result existed and were not "
    "tuned, but the decision to apply them to the detection path was taken with the October and August results "
    "in view, and the held-out figures in the two bands the rule moved carry that qualification.",
    "",
    "It moved two figures in the band table: the 750-850 km October horizon up, from 3 d (26 km at 4 d) to 5 d "
    "(31 km at 6 d), and the 600-750 km August horizon down, from 6 d to 5 d, every lead measured in both. The "
    "400-600 km row, the five spacecraft with a published record, is unchanged in every window: 5 d, 2 d, 24 h, "
    "2 d. Per mission it moved Sentinel-3B from 4 d, 7 d, 3 d, 4 d to 7 d, 7 d, 7 d, 5 d, Sentinel-3A in "
    "October from 7 d to 5 d, Sentinel-1A in May from 6 d to 5 d, CryoSat-2 in August from 6 d to 5 d, and SWOT "
    "in October from 5 d to 7 d; the usable element sets went from 1,228 to 1,201. Both tables as they stood "
    "before the correction are kept below, as rendered on 7 September 2026 from the run of that day under the "
    "earlier detection rule; the two tables above are the corrected ones.",
    "",
    "**The horizon by altitude band and window, before the correction.**",
    "",
    "| Altitude band | Missions | quiet | storm | held-out | august |",
    "| --- | --- | --- | --- | --- | --- |",
    "| 400-600 km | GRACE-FO 1 (C), GRACE-FO 2 (D), Swarm A, Swarm B, Swarm C | 5 d (37 km at 6 d) "
    "| 2 d (35 km at 3 d) | 24 h (34 km at 36 h) | 2 d (38 km at 3 d) |",
    "| 600-750 km | CryoSat-2, Sentinel-1A | 5 d (26 km at 6 d) | 5 d (27 km at 6 d) | 7 d (every lead measured) "
    "| 6 d (every lead measured) |",
    "| 750-850 km | SARAL, Sentinel-3A, Sentinel-3B | 7 d (every lead measured) | 7 d (every lead measured) "
    "| 3 d (26 km at 4 d) | 7 d (every lead measured) |",
    "| 850-1000 km | HY-2C, HY-2D, SWOT | 7 d (every lead measured) | 7 d (every lead measured) "
    "| 7 d (every lead measured) | 7 d (every lead measured) |",
    "| 1000-1400 km | Jason-3, Sentinel-6A | 7 d (every lead measured) | 7 d (every lead measured) "
    "| 7 d (every lead measured) | 7 d (every lead measured) |",
    "",
    "**The horizon by mission and window, before the correction.**",
    "",
    "| Mission | Band | quiet | storm | held-out | august |",
    "| --- | --- | --- | --- | --- | --- |",
    "| Swarm A | 400-600 km | 5 d (42 km at 6 d) (19 sets) | 2 d (36 km at 3 d) (18 sets) "
    "| 24 h (38 km at 36 h) (21 sets) | 36 h (29 km at 2 d) (19 sets) |",
    "| Swarm B | 400-600 km | 5 d (38 km at 6 d) (19 sets) | 2 d (33 km at 3 d) (19 sets) "
    "| 2 d (51 km at 3 d) (19 sets) | 3 d (42 km at 4 d) (19 sets) |",
    "| Swarm C | 400-600 km | 5 d (39 km at 6 d) (19 sets) | 2 d (37 km at 3 d) (17 sets) "
    "| 24 h (38 km at 36 h) (21 sets) | 36 h (26 km at 2 d) (19 sets) |",
    "| GRACE-FO 1 (C) | 400-600 km | 6 d (34 km at 7 d) (19 sets) | 2 d (25 km at 3 d) (18 sets) "
    "| 36 h (39 km at 2 d) (19 sets) | 2 d (34 km at 3 d) (18 sets) |",
    "| GRACE-FO 2 (D) | 400-600 km | 6 d (32 km at 7 d) (19 sets) | 3 d (25 km at 4 d) (19 sets) "
    "| 24 h (26 km at 36 h) (20 sets) | 2 d (34 km at 3 d) (18 sets) |",
    "| Sentinel-1A | 600-750 km | 5 d (27 km at 6 d) (31 sets) | 6 d (every lead measured) (33 sets) "
    "| 4 d (27 km at 5 d) (27 sets) | 5 d (every lead measured) (26 sets) |",
    "| CryoSat-2 | 600-750 km | 7 d (every lead measured) (18 sets) | 5 d (27 km at 6 d) (18 sets) "
    "| 7 d (every lead measured) (17 sets) | 6 d (every lead measured) (18 sets) |",
    "| SARAL | 750-850 km | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (19 sets) "
    "| 4 d (25 km at 5 d) (17 sets) | 7 d (every lead measured) (18 sets) |",
    "| Sentinel-3A | 750-850 km | 7 d (every lead measured) (29 sets) | 7 d (every lead measured) (30 sets) "
    "| 7 d (every lead measured) (27 sets) | 5 d (every lead measured) (32 sets) |",
    "| Sentinel-3B | 750-850 km | 4 d (27 km at 5 d) (15 sets) | 7 d (every lead measured) (19 sets) "
    "| 3 d (27 km at 4 d) (13 sets) | 4 d (31 km at 5 d) (17 sets) |",
    "| SWOT | 850-1000 km | 7 d (every lead measured) (21 sets) | 7 d (every lead measured) (19 sets) "
    "| 5 d (25 km at 6 d) (20 sets) | 7 d (every lead measured) (17 sets) |",
    "| HY-2C | 850-1000 km | 7 d (every lead measured) (30 sets) | 7 d (every lead measured) (34 sets) "
    "| 7 d (every lead measured) (26 sets) | 7 d (every lead measured) (25 sets) |",
    "| HY-2D | 850-1000 km | 7 d (every lead measured) (27 sets) | 7 d (every lead measured) (29 sets) "
    "| 7 d (every lead measured) (19 sets) | 6 d (every lead measured) (23 sets) |",
    "| Jason-3 | 1000-1400 km | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (18 sets) "
    "| 7 d (every lead measured) (17 sets) | 7 d (every lead measured) (17 sets) |",
    "| Sentinel-6A | 1000-1400 km | 7 d (every lead measured) (18 sets) | 7 d (every lead measured) (15 sets) "
    "| 7 d (every lead measured) (15 sets) | 7 d (every lead measured) (18 sets) |",
]


def _ordinal(k: int) -> str:
    return {1: "First", 2: "Second", 3: "Third"}.get(k, f"{k}th")


def _corr_cell(c: dict[str, Any] | None) -> str:
    if not c or c.get("rho") is None:
        return f"- (n {c['n']})" if c else "-"
    return f"{c['rho']:+.2f} (n {c['n']}, p {c['p']:.3f})"


def _post_burn_fit_lines(burns: list[dict[str, Any]], names: dict[str, str], keys: list[str]) -> list[str]:
    """The first set after each burn, classified by how much of the burn its semi-major axis contains."""
    if not any(b.get("delta_a_m") is not None for b in burns):
        return []
    lead_a, lead_b = ("24", "96") if "24" in keys and "96" in keys else (keys[0], keys[-1])
    lines = [
        "",
        "### What the first set after each burn contains",
        "",
        "Each set's semi-major axis is put in the reconstructed orbit's convention (SGP4 over one revolution "
        "centred on its epoch, the osculating value averaged as the detector averages the orbit's), the constant "
        "between the two conventions, most of it the ten-second finite-difference velocity the orbit reader carries, "
        "is calibrated on the window's clean sets (their median residual against the orbit, with the scatter as "
        "1.4826 times the median absolute deviation), and the set's error is measured "
        "against the orbit at its own epoch, not the plateau after the burn, because a decaying orbit has moved on "
        "by then. The fraction of the burn a set contains is one plus that error over the burn: at or under "
        f"{precise.POST_BURN_FRACTION_PRE:g} the energy is compatible with retaining the pre-manoeuvre orbit despite "
        f"the later epoch; at or over {precise.POST_BURN_FRACTION_POST:g} it is compatible with post-manoeuvre energy; "
        "between these thresholds the fraction is mixed. These classes do not identify the catalogue's "
        "fitting procedure. A "
        f"burn under {precise.POST_BURN_RESOLVE_SIGMAS:g} scatters is unresolved. The drift the error predicts, "
        "three halves of the mean motion times the error times the lead, is beside the observed residual, signed as "
        "the benchmark signs it (positive when the satellite is ahead of the set). The thresholds are an "
        "author-reported pre-execution choice; the first commit carrying them also carried results. "
        "Epoch spacing is not publication cadence.",
        "",
        "| Mission | Window | Burn (m) | Clean sets: n, offset, scatter (m) | First set after: delay, error at its "
        f"epoch (m), fraction, class | Observed / predicted at {_lead(float(lead_a))} (km) "
        f"| Observed / predicted at {_lead(float(lead_b))} (km) |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for b in burns:
        if b.get("delta_a_m") is None:
            continue
        first = b["sets_after"][0]
        err = "-" if first.get("a_error_m") is None else f"{first['a_error_m']:+.0f}"
        frac = "-" if first.get("fraction") is None else f"{first['fraction']:.2f}"
        cells = []
        for key in (lead_a, lead_b):
            obs = (first.get("in_track_signed_km") or first["in_track_km"]).get(key)
            pred = (first.get("predicted_in_track_km") or {}).get(key)
            o = "-" if obs is None else f"{obs:+.1f}"
            p = "-" if pred is None else f"{pred:+.1f}"
            cells.append(f"{o} / {p}")
        lines.append(
            f"| {names.get(b['mission'], b['mission'])} | {b['window']} | {b['delta_a_m']:+.0f} "
            f"| {b['n_clean_sets']}, {b['offset_m']:+.0f}, {b['sigma_m']:.1f} "
            f"| {first['delay_h']:.1f} h, {err}, {frac}, {first.get('class') or '-'} | " + " | ".join(cells) + " |"
        )
    # The observed residual is signed here; the tables above carry its absolute value.
    lines.append("")
    lines.append(
        "The observed residuals in this table are signed; the tables above carry their absolute values. The second "
        "and third sets after each burn are classified in the JSON beside this page."
    )
    return lines


def _post_burn_section(post: dict[str, Any], names: dict[str, str]) -> list[str]:
    """The first element sets after a burn, against the cadence of the mission's sets and the delay after the burn."""
    leads = [float(x) for x in post.get("leads_h", [])]
    keys = [f"{ld:g}" for ld in leads]
    heads = " / ".join(_lead(ld) for ld in leads)
    n_after = int(post.get("sets_after", POST_BURN_SETS))
    lines = [
        "",
        "## The first element sets after a burn, against cadence and delay",
        "",
        "Every burn that fell inside a window's set span with a set issued after it, from the published record "
        "where one exists and otherwise from the orbit-step detector on the reconstructed orbit, which places a "
        "burn to about an orbit either side: the cadence of the mission's sets in the window (the median gap "
        f"between consecutive epochs) and, for the first {n_after} sets issued after the burn, the delay from the "
        f"burn and the absolute in-track residual at {heads}, km, beside the median of the window's usable trials "
        "at the same leads for scale. A pair whose own arc reaches a later burn is blank. The set-jump detector's "
        "intervals are not read as burns here: a storm produces them too.",
        "",
    ]
    burns = post.get("burns") or []
    if not burns:
        lines.append("No burn fell inside a window's set span with a set issued after it.")
        return lines
    lines += [
        "| Mission | Window | Burn (UTC), how found | Sets, cadence | "
        + " | ".join(f"{_ordinal(k)} set after: delay; residual at {heads}" for k in range(1, n_after + 1))
        + f" | Usable-trial median at {heads} |",
        "| --- | --- | --- | --- | " + " | ".join("---" for _ in range(n_after)) + " | --- |",
    ]

    def fmt(v: float | None) -> str:
        return "-" if v is None else f"{v:.1f}"

    for b in burns:
        mid = pd.Timestamp(b["burn_mid"])
        cells = []
        for k in range(1, n_after + 1):
            row = next((r for r in b["sets_after"] if r["k"] == k), None)
            if row is None:
                cells.append("-")
            else:
                cells.append(f"{row['delay_h']:.1f} h; " + " / ".join(fmt(row["in_track_km"].get(key)) for key in keys))
        clear = " / ".join(fmt(b["clear_median_km"].get(key)) for key in keys)
        lines.append(
            f"| {names.get(b['mission'], b['mission'])} | {b['window']} | {mid:%Y-%m-%d %H:%M}, {b['source']} "
            f"| {b['n_sets']}, {b['cadence_h']:.1f} h | " + " | ".join(cells) + f" | {clear} |"
        )
    corr = post.get("rank_correlation") or {}
    if corr:
        pb, ps = corr["per_burn"], corr["per_spacecraft"]
        lines += [
            "",
            "Spearman rank correlation of the first set's residual with the cadence and with the delay after the "
            f"burn, per burn ({pb['n']}) and per spacecraft, the means over each one's burns ({ps['n']}):",
            "",
            "| Lead | Per burn, cadence | Per burn, delay | Per spacecraft, cadence | Per spacecraft, delay |",
            "| --- | --- | --- | --- | --- |",
        ]
        for ld, key in zip(leads, keys, strict=True):
            lines.append(
                f"| {_lead(ld)} | {_corr_cell(pb['cadence'].get(key))} | {_corr_cell(pb['delay'].get(key))} "
                f"| {_corr_cell(ps['cadence'].get(key))} | {_corr_cell(ps['delay'].get(key))} |"
            )

    def burn_list(items: list[dict[str, Any]]) -> str:
        return "; ".join(
            f"{names.get(i['mission'], i['mission'])}, {i['window']} "
            f"({pd.Timestamp(i['burn_from']):%Y-%m-%d %H:%M} to {pd.Timestamp(i['burn_to']):%H:%M}, {i['source']})"
            for i in items
        )

    lines += _post_burn_fit_lines(burns, names, keys)
    without = post.get("burns_without_a_set_after") or []
    after_span = post.get("burns_after_the_span") or []
    if without:
        lines += [
            "",
            "Burns inside a span with no set issued after them before the span's end: " + burn_list(without) + ".",
        ]
    if after_span:
        lines += [
            "",
            "Burns after a span's last set, inside the truth period, which take out only the leads of earlier sets: "
            + burn_list(after_span)
            + ".",
        ]
    return lines


def to_markdown(
    result: ReferenceResult,
    windows: list[BenchmarkWindow],
    missions: list[Mission],
    rendered_at: datetime | None = None,
) -> str:
    """Render the stored corrected summary without historical hardcoded claims."""
    import json

    summary = result.summary
    names = {mission.key: mission.name for mission in missions}

    def number(value, *, percent=False):
        if value is None:
            return "unavailable"
        return f"{value:.1%}" if percent else f"{value:.4g}"

    def table(headers, rows):
        def clean(value):
            return str(value).replace("|", "/").replace("\n", " ")

        return "\n".join(
            [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join("---" for _ in headers) + " |",
                *("| " + " | ".join(clean(value) for value in row) + " |" for row in rows),
            ]
        )

    horizon_rows, lead_rows = [], []
    definition = None
    for scope in ("by_band", "by_mission"):
        for population, by_window in summary["results"][scope].items():
            for window, group in by_window.items():
                if "definition" not in group:
                    raise ValueError("Re-summarise stored trials with the corrected statistics before rendering")
                definition = group["definition"]
                sensitivity = group.get("sensitivities", {})
                spacecraft = sensitivity.get("leave_one_spacecraft_out", {})
                deletion = (
                    "; ".join(
                        f"omit {names.get(mission, mission)}: {_horizon_text(value['empirical_coverage'])}"
                        for mission, value in spacecraft.items()
                    )
                    or "not computed for this scope"
                )
                sets = sensitivity.get("leave_one_set_out", {})
                horizon_rows.append(
                    [
                        scope,
                        names.get(population, population),
                        window,
                        group["n_sets_total"],
                        group["n_sets_usable"],
                        _horizon_text(group["horizon"]),
                        _horizon_text(group["horizons_by_criterion"]["linear_quantile"]),
                        deletion,
                        f"{sets.get('n_changed', 'unavailable')}/{sets.get('n_deletions', 'unavailable')}",
                    ]
                )
                for lead, cell in group["by_lead_h"].items():
                    component = cell["components"]["in_track"]
                    components = []
                    for name, value in cell["components"].items():
                        coverage = value["coverage"]
                        if coverage is None:
                            components.append(f"{name}: sigma unavailable")
                            continue
                        components.append(
                            f"{name}: median |error| {number(value['median_abs_km'])} km; "
                            f"median sigma {number(coverage['median_sigma_km'])} km; "
                            f"inside 1sigma {coverage['inside_1_sigma_count']}/{coverage['n']}; "
                            f"inside 2sigma {coverage['inside_2_sigma_count']}/{coverage['n']}; "
                            f"invalid {coverage['n_invalid_pairs']}"
                        )
                    term = cell.get("storm_term", {})
                    lead_rows.append(
                        [
                            scope,
                            names.get(population, population),
                            window,
                            lead,
                            cell["n_total"],
                            cell["n"],
                            "; ".join(
                                f"{names.get(mission, mission)}: {count}"
                                for mission, count in cell["mission_counts"].items()
                            )
                            or "none",
                            f"{cell['exceedance_count']}/{cell['n']} "
                            f"({number(cell['exceedance_fraction'], percent=True)})",
                            number(component["median_abs_km"]),
                            number(component["quantile_abs_km"]["linear"]),
                            number(component["quantile_abs_km"]["inverted_cdf"]),
                            "; ".join(components),
                            term.get("status", "not reported"),
                        ]
                    )
    lines = [
        "# Record-controlled reference benchmark",
        "",
        "This CLI page is generated from the corrected stored reference summary. The publication, "
        "archived comparisons and full component deletion sensitivities are generated by "
        "`scripts/render_paper_v2.py` in [the canonical publication](paper.md).",
        "",
        "An element-set epoch selects each trial; epoch spacing is not publication cadence. "
        "Published manoeuvre records govern exclusions where available, including authoritative empty "
        "interval lists. Missing record coverage is explicit. Detector intervals remain the labelled "
        "fallback for other missions and auxiliary checks for recorded missions.",
        "",
    ]
    if definition:
        lines += [
            f"Primary criterion: at least {number(definition['quantile'], percent=True)} of finite usable "
            f"absolute in-track errors within {number(definition['tolerance_km'])} km, on the planned lead grid "
            f"{definition['leads_hours']} hours. Linear and inverted-CDF quantiles are reported separately. "
            "Missing coverage censors the supported interval; a threshold failure is a different termination. "
            "Deletion results are descriptive stability checks, not confidence intervals. These previously "
            "examined windows are an exploratory corrected benchmark.",
            "",
        ]
    lines += [
        "## Horizons, counts and deletion checks",
        "",
        table(
            [
                "Scope",
                "Population",
                "Window",
                "All sets",
                "Usable sets at any lead",
                "Primary empirical endpoints",
                "Linear-quantile endpoints",
                "Remove one spacecraft",
                "Set deletions changing a criterion / tested",
            ],
            horizon_rows,
        ),
        "",
        "## Every planned lead and component",
        "",
        table(
            [
                "Scope",
                "Population",
                "Window",
                "Lead h",
                "All pairs",
                "Finite usable n",
                "Mission composition",
                "Exceedances / n",
                "Median |I| km",
                "Linear quantile km",
                "Inverted-CDF quantile km",
                "Component residuals and sigma coverage",
                "Storm-term support",
            ],
            lead_rows,
        ),
        "",
        "## Exclusion sources and coverage",
        "",
    ]
    rows = []
    for mission, by_window in summary.get("coverage", {}).items():
        for window, coverage in by_window.items():
            record = coverage.get("manoeuvre_record_provenance")
            recorded = coverage.get("manoeuvres_recorded")
            rows.append(
                [
                    names.get(mission, mission),
                    window,
                    "detector fallback" if record is None else record.get("source_id", "published record"),
                    "not integrated" if record is None else record.get("coverage_status"),
                    "unavailable" if recorded is None else len(recorded),
                    json.dumps(record, sort_keys=True) if record else "no published-record metadata",
                    json.dumps(coverage.get("orbit_detector_crosscheck"), sort_keys=True),
                ]
            )
    lines += [
        table(
            [
                "Mission",
                "Window",
                "Authority",
                "Coverage",
                "Loaded published intervals",
                "Provenance",
                "Orbit detector check",
            ],
            rows,
        ),
        "",
        "Published registries do not independently prove exhaustive firing reports. Loaded record products "
        "include date padding, so unmatched intervals must be classified by their overlap with actual scored "
        "arcs; detector differencing also needs surrounding states. The canonical supplement reports those "
        "individual scopes and mask effects. Swarm and GRACE-FO provide different mission/producer checks "
        "within a GNSS-derived reference family. Sampled laser ranges constrain range error on observed passes "
        "and do not establish a complete three-dimensional tail distribution. No operational reliability "
        "probability or unobserved catalogue-processing mechanism is inferred here.",
        "",
        _last_updated(result.built_at, rendered_at),
        "",
    ]
    return "\n".join(lines)


def _last_updated(built_at: datetime, rendered_at: datetime | None) -> str:
    if rendered_at is None or rendered_at.date() == built_at.date():
        return f"_Last updated {built_at:%d %B %Y}._"
    return f"_Last updated {rendered_at:%d %B %Y}, from the run of {built_at:%d %B %Y}._"
