"""Descriptive benchmark statistics with explicit denominators and censoring.

This module only summarises the supplied rows; it fetches and propagates nothing.
The primary horizon requires at least ``quantile`` of the empirical residuals to
be within the tolerance. NumPy's linear and inverted-CDF quantiles are reported
separately, including the horizon each convention would produce. None of the
deletion sensitivities is a confidence interval: trials share spacecraft,
tracking information and storm conditions.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_LEADS_HOURS = (6.0, 12.0, 24.0, 36.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0)
COMPONENTS = {"radial": "sigma_r_km", "in_track": "sigma_i_km", "cross": "sigma_c_km"}
CRITERIA = ("empirical_coverage", "linear_quantile", "inverted_cdf_quantile")


def _prepare(trials: pd.DataFrame, leads_hours: Iterable[float]) -> tuple[pd.DataFrame, tuple[float, ...]]:
    required = {"mission", "set_epoch", "lead_h", "in_track_km"}
    missing = required - set(trials.columns)
    if missing:
        raise ValueError(f"Missing benchmark columns: {', '.join(sorted(missing))}")
    leads = tuple(sorted(set(float(h) for h in leads_hours)))
    if not leads or not all(np.isfinite(h) and h > 0 for h in leads):
        raise ValueError("leads_hours must contain finite positive planned leads")
    frame = trials.copy()
    if frame[["mission", "set_epoch", "lead_h"]].isna().any().any():
        raise ValueError("Mission, set epoch and lead must be present on every trial")
    if not frame["lead_h"].isin(leads).all():
        raise ValueError("Trial leads must be included in the planned leads_hours grid")
    if frame.duplicated(_set_columns(frame) + ["lead_h"]).any():
        raise ValueError("Expected one row per mission/window/set epoch/lead")
    keep = pd.Series(True, index=frame.index)
    for flag in ("gap", "manoeuvre"):
        if flag in frame:
            keep &= ~frame[flag].fillna(True).astype(bool)
    if "sgp4_error" in frame:
        keep &= frame["sgp4_error"].eq(0)
    frame["_benchmark_usable"] = keep
    return frame, leads


def _set_columns(frame: pd.DataFrame) -> list[str]:
    return ["mission", *(["window"] if "window" in frame else []), "set_epoch"]


def _counts(frame: pd.DataFrame) -> dict[str, int]:
    return {str(m): int(n) for m, n in frame.groupby("mission", sort=True).size().items()}


def _quantile(values: np.ndarray, quantile: float, method: str) -> float | None:
    return float(np.quantile(values, quantile, method=method)) if len(values) else None


def _component(frame: pd.DataFrame, component: str, quantile: float) -> dict[str, Any]:
    residual = frame[f"{component}_km"].to_numpy(dtype=float)
    finite = np.isfinite(residual)
    absolute = np.abs(residual[finite])
    out: dict[str, Any] = {
        "n_residuals": int(finite.sum()),
        "mission_counts": _counts(frame.loc[finite]),
        "n_nonfinite_residuals": int((~finite).sum()),
        "median_abs_km": _quantile(absolute, 0.5, "linear"),
        "quantile_abs_km": {
            "linear": _quantile(absolute, quantile, "linear"),
            "inverted_cdf": _quantile(absolute, quantile, "inverted_cdf"),
        },
    }
    sigma_column = COMPONENTS[component]
    if sigma_column not in frame:
        out["coverage"] = None
        return out
    sigma = frame[sigma_column].to_numpy(dtype=float)
    valid = finite & np.isfinite(sigma) & (sigma >= 0)
    n = int(valid.sum())
    coverage: dict[str, Any] = {
        "n": n,
        "mission_counts": _counts(frame.loc[valid]),
        "n_invalid_pairs": int(len(frame) - n),
        "n_zero_sigma": int((valid & (sigma == 0)).sum()),
        "median_sigma_km": _quantile(sigma[valid], 0.5, "linear"),
    }
    for multiple in (1, 2):
        count = int((np.abs(residual[valid]) <= multiple * sigma[valid]).sum())
        coverage[f"inside_{multiple}_sigma_count"] = count
        coverage[f"inside_{multiple}_sigma_fraction"] = count / n if n else None
    out["coverage"] = coverage
    return out


def _lead_statistics(frame: pd.DataFrame, leads: tuple[float, ...], tolerance: float, quantile: float) -> dict:
    out = {}
    for lead in leads:
        total = frame[frame["lead_h"].eq(lead)]
        usable = total[total["_benchmark_usable"]]
        finite = usable[np.isfinite(usable["in_track_km"].to_numpy(dtype=float))]
        n = len(finite)
        exceedances = int(finite["in_track_km"].abs().gt(tolerance).sum())
        components = {c: _component(usable, c, quantile) for c in COMPONENTS if f"{c}_km" in usable.columns}
        out[f"{lead:g}"] = {
            "n_total": len(total),
            "n_usable": len(usable),
            "n_excluded": len(total) - len(usable),
            "n": n,
            "n_sets": len(finite[_set_columns(finite)].drop_duplicates()),
            "n_missions": int(finite["mission"].nunique()),
            "mission_counts": _counts(finite),
            "mission_counts_total": _counts(total),
            "exceedance_count": exceedances,
            "exceedance_fraction": exceedances / n if n else None,
            "inside_tolerance_count": n - exceedances,
            "inside_tolerance_fraction": (n - exceedances) / n if n else None,
            "components": components,
        }
    return out


def _horizons(by_lead: dict, leads: tuple[float, ...], tolerance: float, quantile: float) -> dict:
    observed = [lead for lead in leads if by_lead[f"{lead:g}"]["n"]]
    missing = [lead for lead in leads if not by_lead[f"{lead:g}"]["n"]]
    results = {}
    for criterion in CRITERIA:
        last = None
        first_bad = None
        stopped_at = None
        termination = "longest_tested_lead"
        for lead in leads:
            entry = by_lead[f"{lead:g}"]
            if not entry["n"]:
                termination, stopped_at = "coverage_censored", lead
                break
            if criterion == "empirical_coverage":
                # Integer comparison through the fraction avoids rounding displayed percentages.
                passed = entry["inside_tolerance_count"] >= quantile * entry["n"]
            else:
                method = "linear" if criterion == "linear_quantile" else "inverted_cdf"
                passed = entry["components"]["in_track"]["quantile_abs_km"][method] <= tolerance
            if not passed:
                termination, first_bad, stopped_at = "threshold_failure", lead, lead
                break
            last = lead
        results[criterion] = {
            "criterion": criterion,
            "last_lead_h_within": last,
            "first_lead_h_beyond": first_bad,
            "termination": termination,
            "stopped_at_lead_h": stopped_at,
            "last_observed_lead_h": max(observed) if observed else None,
            "longest_tested_lead_h": max(leads),
            "missing_leads_h": missing,
            "bracket_is_confidence_interval": False,
        }
    return results


def _horizons_only(frame: pd.DataFrame, leads: tuple[float, ...], tolerance: float, quantile: float) -> dict:
    """Small per-lead records for deletion sensitivity, without covariance recomputation."""
    by_lead = {}
    usable = frame[frame["_benchmark_usable"]]
    for lead in leads:
        values = usable.loc[usable["lead_h"].eq(lead), "in_track_km"].to_numpy(dtype=float)
        values = np.abs(values[np.isfinite(values)])
        by_lead[f"{lead:g}"] = {
            "n": len(values),
            "inside_tolerance_count": int((values <= tolerance).sum()),
            "components": {
                "in_track": {
                    "quantile_abs_km": {
                        method: _quantile(values, quantile, method) for method in ("linear", "inverted_cdf")
                    }
                }
            },
        }
    return _horizons(by_lead, leads, tolerance, quantile)


def _coverage_sensitivity(frame: pd.DataFrame, leads: tuple) -> dict:
    """Delete whole spacecraft or sets; summarise 2-sigma coverage without resampling.

    The deletion population is all sets with an unmasked trial in this group.
    A set contributes at most one row at a lead, so subtracting its valid pair
    gives the same result as deleting its entire trajectory before scoring.
    Deletions of sets absent at a lead are retained as unchanged results.
    """
    usable = frame[frame["_benchmark_usable"]]
    missions = sorted(str(m) for m in usable["mission"].unique())
    keys = _set_columns(frame)
    n_sets = len(usable[keys].drop_duplicates())
    out = {}
    for lead in leads:
        rows = usable[usable["lead_h"].eq(lead)]
        cells = {}
        for component, sigma_column in COMPONENTS.items():
            if f"{component}_km" not in rows or sigma_column not in rows:
                continue
            residual = rows[f"{component}_km"].to_numpy(dtype=float)
            sigma = rows[sigma_column].to_numpy(dtype=float)
            valid = np.isfinite(residual) & np.isfinite(sigma) & (sigma >= 0)
            valid_rows = rows.loc[valid]
            inside = np.abs(residual[valid]) <= 2 * sigma[valid]
            n, count = len(valid_rows), int(inside.sum())
            fraction = count / n if n else None
            spacecraft = {}
            for mission in missions:
                deleted = valid_rows["mission"].eq(mission).to_numpy()
                remaining_n = n - int(deleted.sum())
                remaining_count = count - int(inside[deleted].sum())
                spacecraft[mission] = {
                    "n": remaining_n,
                    "inside_2_sigma_count": remaining_count,
                    "inside_2_sigma_fraction": remaining_count / remaining_n if remaining_n else None,
                }
            # Repeated entries represent distinct whole-set deletions; weights
            # preserve the count without storing every identical outcome.
            outcomes = []
            if n_sets > n:
                outcomes.append((n, count, n_sets - n))
            if n:
                if count:
                    outcomes.append((n - 1, count - 1, count))
                if count < n:
                    outcomes.append((n - 1, count, n - count))
            defined = [(c / denominator, weight) for denominator, c, weight in outcomes if denominator]
            values = [value for value, _ in defined]
            cells[component] = {
                "baseline": {"n": n, "inside_2_sigma_count": count, "inside_2_sigma_fraction": fraction},
                "leave_one_spacecraft_out": spacecraft,
                "leave_one_set_out": {
                    "n_deletions": n_sets,
                    "n_defined": sum(weight for _, weight in defined),
                    "n_undefined": sum(weight for denominator, _, weight in outcomes if not denominator),
                    "n_fraction_changed": sum(
                        weight
                        for value, weight in defined
                        if fraction is None or not np.isclose(value, fraction, rtol=1e-12, atol=1e-12)
                    ),
                    "min_fraction": min(values) if values else None,
                    "max_fraction": max(values) if values else None,
                    "min_n": min((denominator for denominator, _, _ in outcomes), default=None),
                    "max_n": max((denominator for denominator, _, _ in outcomes), default=None),
                },
            }
        out[f"{lead:g}"] = cells
    return {
        "interpretation": "Descriptive deletion sensitivity of valid residual/sigma pairs; not confidence intervals",
        "deletion_population": "All spacecraft and whole sets with at least one unmasked trial in this group",
        "sigma_multiple": 2,
        "by_lead_h": out,
    }


def _sensitivity(frame: pd.DataFrame, baseline: dict, leads: tuple, tolerance: float, quantile: float) -> dict:
    usable = frame[frame["_benchmark_usable"] & np.isfinite(frame["in_track_km"].to_numpy(dtype=float))]
    spacecraft = {}
    for mission in sorted(usable["mission"].unique()):
        spacecraft[str(mission)] = _horizons_only(frame[frame["mission"].ne(mission)], leads, tolerance, quantile)
    changes = []
    keys = _set_columns(frame)
    unique_sets = usable[keys].drop_duplicates()
    for values in unique_sets.itertuples(index=False, name=None):
        deleted = pd.Series(True, index=frame.index)
        for key, value in zip(keys, values, strict=True):
            deleted &= frame[key].eq(value)
        horizons = _horizons_only(frame[~deleted], leads, tolerance, quantile)
        if horizons != baseline:
            changes.append(
                {
                    "deleted_set": {key: str(value) for key, value in zip(keys, values, strict=True)},
                    "horizons_by_criterion": horizons,
                }
            )
    return {
        "interpretation": "Descriptive deletion sensitivity; not confidence intervals or independent trials",
        "leave_one_spacecraft_out": spacecraft,
        "leave_one_set_out": {"n_deletions": len(unique_sets), "n_changed": len(changes), "changes": changes},
        "component_coverage": _coverage_sensitivity(frame, leads),
    }


def summarise_group(
    trials: pd.DataFrame,
    *,
    leads_hours: Iterable[float] = DEFAULT_LEADS_HOURS,
    tolerance_km: float = 25.0,
    quantile: float = 0.95,
    include_sensitivities: bool = True,
) -> dict[str, Any]:
    """Summarise one population on its *planned* lead grid, including empty leads.

    Optional ``gap``, ``manoeuvre`` and ``sgp4_error`` columns apply the benchmark's
    exclusion rule; missing flag columns mean the caller supplied filtered rows.
    Missing residuals and invalid sigma pairs have separate denominators. A gap
    in observed leads terminates the supported contiguous horizon even when a
    later lead is observed. Supply the original planned grid after any deletion
    or filtering, otherwise censoring cannot be distinguished from test length.
    """
    if not np.isfinite(tolerance_km) or tolerance_km < 0:
        raise ValueError("tolerance_km must be finite and nonnegative")
    if not 0 < quantile <= 1:
        raise ValueError("quantile must be in (0, 1]")
    frame, leads = _prepare(trials, leads_hours)
    by_lead = _lead_statistics(frame, leads, tolerance_km, quantile)
    horizons = _horizons(by_lead, leads, tolerance_km, quantile)
    usable = frame[frame["_benchmark_usable"]]
    finite = usable[np.isfinite(usable["in_track_km"].to_numpy(dtype=float))]
    out = {
        "definition": {
            "tolerance_km": float(tolerance_km),
            "quantile": float(quantile),
            "primary_criterion": "empirical_coverage",
            "primary_rule": "inside_tolerance_count >= quantile * n_finite_usable_residuals",
            "quantile_methods": ["linear", "inverted_cdf"],
            "exceedance_rule": "absolute in-track residual > tolerance_km; equality is inside",
            "leads_hours": list(leads),
            "uncertainty": "Descriptive only; correlated trials do not supply independent binomial observations",
        },
        "n_trial_leads": len(frame),
        "n_usable_trial_leads": len(usable),
        "n_sets_total": len(frame[_set_columns(frame)].drop_duplicates()),
        "n_sets_usable": len(finite[_set_columns(finite)].drop_duplicates()),
        "missions": sorted(str(m) for m in finite["mission"].unique()),
        "by_lead_h": by_lead,
        "horizon": horizons["empirical_coverage"],
        "horizons_by_criterion": horizons,
    }
    if include_sensitivities:
        out["sensitivities"] = _sensitivity(frame, horizons, leads, tolerance_km, quantile)
    return out


def summarise_trials(trials: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
    """Summarise each band/window and each mission/window without pooling windows.

    Keyword arguments are those of :func:`summarise_group`. Mission summaries
    omit deletion sensitivities; band summaries include them by default.
    """
    missing = {"altitude_band", "window"} - set(trials.columns)
    if missing:
        raise ValueError(f"Missing grouping columns: {', '.join(sorted(missing))}")
    out: dict[str, Any] = {"by_band": {}, "by_mission": {}}
    for band, frame in trials.groupby("altitude_band", sort=True):
        out["by_band"][str(band)] = {
            str(window): summarise_group(group, **kwargs) for window, group in frame.groupby("window", sort=True)
        }
    mission_kwargs = {**kwargs, "include_sensitivities": False}
    for mission, frame in trials.groupby("mission", sort=True):
        out["by_mission"][str(mission)] = {
            str(window): summarise_group(group, **mission_kwargs)
            for window, group in frame.groupby("window", sort=True)
        }
    return out
