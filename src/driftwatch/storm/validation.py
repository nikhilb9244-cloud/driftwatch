"""Step 4: does the storm term predict what the May 2024 storm actually did?

Everything before this step is internally consistent and unvalidated. The closed form was
checked against a numerical integration of *itself*, the density model against published
tables, the coefficients against the objects' own decay -- and a chain of correct steps can
still add up to a wrong answer if the density model's storm response is wrong, which is the
one term Phase 3 carries as a prior rather than a measurement.

So this module puts the whole chain against the record, twice, and in the order that makes a
failure interpretable.

## 1. Did the atmosphere do what the model says? (:func:`decay_rates`, :func:`density_ratios`)

The cleanest measurement available from public element sets, because it needs no ballistic
coefficient at all. For one object, ``da/dt = -B rho sqrt(mu a)``. Take that over a quiet
window and over the storm and divide: **B cancels**, ``sqrt(mu a)`` cancels to the per cent
the altitude moved, and what is left is the ratio of the densities the object actually flew
through. NRLMSIS, driven by the observed ap for the same days at the same altitudes, predicts
that ratio independently. The two are compared per object and against altitude.

This is why the mean-motion route is first: it tests the atmosphere alone. If it fails,
nothing downstream can be believed; if it passes, a failure downstream is in the ballistic
coefficients or in the linearisation rather than in the weather.

## 2. Did it move the objects where we say it did? (:func:`in_track_errors`)

The test that matters for screening, and it is a *forecast* test, run the way an operator
would have run it. Take each object's last element set issued **before** the storm, propagate
it with SGP4 through 10 to 13 May, and compare against the element sets issued during those
days. The along-track component of that disagreement is the error a screening run made on
those days -- the thing driftwatch exists to predict.

Two disciplines make it a test rather than a demonstration:

* **Nothing after the pivot is used to make the prediction.** The predicted shift is computed
  from the pre-storm element set, its own pre-storm ballistic coefficient and the observed ap.
  An element set issued on 12 May already contains the storm's effect; propagating one would
  "predict" the drag it was fitted to.
* **A quiet control window with the same lead times.** SGP4 accumulates along-track error
  without any storm at all, from the fit noise and from ordinary mismodelled drag, and it does
  so quadratically too. Without the control, that error would be read as the storm's. The
  storm's contribution is what the storm window has *beyond* the control at the same lead.

The residual is ``observed - predicted``, and it is reported as a distribution against lead
time and altitude rather than as one number, because a term that is right on average and
wrong at 400 km is not right.

## What the truth is here, and what it is not

The later element set is not truth. It is another fit, with its own error of hundreds of
metres to kilometres (``docs/screening.md``). What is measured is the disagreement between
two fits, which is a **floor** on the propagation error rather than a measurement of it. Over
a storm the disagreement runs to tens of kilometres, so the floor is far below the signal and
the comparison is meaningful; in the quiet control it is not far below, and the control's
numbers are reported as an upper bound on what SGP4 alone contributes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from driftwatch.drag import ballistic as bal
from driftwatch.drag import density as dn
from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs
from driftwatch.screening.ric import ric_basis, to_ric
from driftwatch.storm import term

log = logging.getLogger(__name__)

DAY_S = 86400.0
MU_M3_S2 = dn.MU_M3_S2


@dataclass(frozen=True)
class Window:
    """A named span of days, and whether it is meant to be quiet or stormy."""

    name: str
    start: datetime
    end: datetime

    @property
    def days(self) -> float:
        return (self.end - self.start).total_seconds() / DAY_S

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "start": self.start.isoformat(), "end": self.end.isoformat()}


# --------------------------------------------------------------------------------------
# 1. The density enhancement, from the objects themselves


def decay_rate(sets: pd.DataFrame, window: Window) -> dict[str, Any]:
    """``da/dt`` in metres per second over ``window`` for one object, with the burns taken out.

    A straight line through the mean semi-major axis against time, not an endpoint difference:
    over a three-day window with six or eight element sets the endpoints are the two noisiest
    numbers available and a fit uses all of them. The slope's own standard error comes from the
    residuals, which is what decides later whether an object's ratio means anything.

    Intervals the manoeuvre detector flags are dropped, and an object left with fewer than
    three usable sets returns NaN rather than a slope through two points.
    """
    epochs = pd.to_datetime(sets["epoch"], utc=True)
    inside = (epochs >= pd.Timestamp(window.start)) & (epochs <= pd.Timestamp(window.end))
    chosen = sets[inside].sort_values("epoch").drop_duplicates("epoch", keep="last").reset_index(drop=True)
    out: dict[str, Any] = {"window": window.name, "n_sets": int(len(chosen))}
    if len(chosen) < 3:
        return {**out, "da_dt_m_s": np.nan, "sigma_m_s": np.nan, "a_mean_m": np.nan, "note": "fewer than three sets"}

    a_m = bal.mean_sma_m(chosen)
    jump, bad = bal.manoeuvre_intervals(chosen)
    # A jump between k and k+1 taints both sets for a straight-line fit, so both are dropped.
    keep = ~bad
    keep[:-1] &= ~jump
    keep[1:] &= ~jump
    keep &= np.isfinite(a_m)
    out["n_manoeuvre_excluded"] = int(jump.sum())
    if keep.sum() < 3:
        return {**out, "da_dt_m_s": np.nan, "sigma_m_s": np.nan, "a_mean_m": np.nan, "note": "manoeuvring"}

    seconds = (pd.to_datetime(chosen["epoch"], utc=True) - pd.Timestamp(window.start)).dt.total_seconds().to_numpy()
    x, y = seconds[keep], a_m[keep]
    slope, intercept = np.polyfit(x, y, 1)
    residual = y - (slope * x + intercept)
    dof = max(len(x) - 2, 1)
    sigma_slope = float(np.sqrt(np.sum(residual**2) / dof / max(np.sum((x - x.mean()) ** 2), 1e-9)))
    return {
        **out,
        "da_dt_m_s": float(slope),
        "sigma_m_s": sigma_slope,
        "a_mean_m": float(np.mean(y)),
        "altitude_km": float(np.mean(y)) / 1000.0 - dn.EARTH_RADIUS_KM,
        "scatter_m": float(np.sqrt(np.mean(residual**2))),
        "note": "",
    }


def decay_rates(history: pd.DataFrame, windows: list[Window]) -> pd.DataFrame:
    """:func:`decay_rate` for every object over every window, one row per object and window."""
    rows = []
    for norad_id, sets in history.groupby("norad_id"):
        for window in windows:
            rows.append({"norad_id": int(norad_id), **decay_rate(sets, window)})
    return pd.DataFrame(rows)


def observed_density_ratio(rates: pd.DataFrame, storm: str, quiet: str, *, min_snr: float = 3.0) -> pd.DataFrame:
    """The storm-to-quiet density ratio each object measured, from its own two decay rates.

    ``B`` and the object's size and mass cancel; the residual dependence on the semi-major
    axis between the two windows is ``sqrt(a_storm / a_quiet)``, which is applied rather than
    assumed away even though it is a few parts in ten thousand.

    An object whose quiet decay is not significant against its own scatter has no denominator
    worth dividing by and is dropped, which is what ``min_snr`` is for: the ratio of two noisy
    small numbers is the classic way to manufacture a spectacular and meaningless enhancement.
    """
    wide = rates.pivot(index="norad_id", columns="window")
    storm_rate = -wide[("da_dt_m_s", storm)]
    quiet_rate = -wide[("da_dt_m_s", quiet)]
    storm_sigma = wide[("sigma_m_s", storm)]
    quiet_sigma = wide[("sigma_m_s", quiet)]
    a_storm = wide[("a_mean_m", storm)]
    a_quiet = wide[("a_mean_m", quiet)]
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = (storm_rate / quiet_rate) * np.sqrt(a_quiet / a_storm)
        snr = quiet_rate / quiet_sigma
        # Independent relative errors added in quadrature.
        relative = np.sqrt((storm_sigma / storm_rate) ** 2 + (quiet_sigma / quiet_rate) ** 2)
    out = pd.DataFrame(
        {
            "norad_id": wide.index,
            "altitude_km": (a_quiet.to_numpy() / 1000.0 - dn.EARTH_RADIUS_KM),
            "quiet_decay_m_s": quiet_rate.to_numpy(),
            "storm_decay_m_s": storm_rate.to_numpy(),
            "observed_ratio": ratio.to_numpy(),
            "ratio_sigma": (ratio * relative).to_numpy(),
            "quiet_snr": snr.to_numpy(),
        }
    ).reset_index(drop=True)
    out["usable"] = np.isfinite(out["observed_ratio"]) & (out["quiet_snr"] >= min_snr) & (out["quiet_decay_m_s"] > 0)
    return out


def modelled_density_ratio(
    elements: pd.DataFrame,
    table: pd.DataFrame | dn.WeatherGrid,
    storm: Window,
    quiet: Window,
    *,
    step_scale: float = 4.0,
) -> pd.DataFrame:
    """What NRLMSIS says the same ratio should be, along each object's own orbit.

    Along the orbit rather than at a fixed altitude and latitude, because the enhancement is
    not uniform: it is largest at high latitude where the energy goes in, and an object at 53
    degrees inclination samples a different part of it than one in a polar orbit. The
    drag-weighted mean is used -- the same weighting the coefficient fit uses -- so the ratio
    is of the quantity that actually moves the orbit.
    """
    grid = dn.weather_grid(table)
    rows = []
    for row in elements.to_dict("records"):
        series = pd.Series(row)
        values: dict[str, float] = {}
        mean_rho: dict[str, float] = {}
        for window in (quiet, storm):
            step = dn.sample_step_s(float(series["mean_motion"]), float(series.get("eccentricity", 0.0))) * step_scale
            track = dn.density_along_orbit(series, grid, window.start, window.end, step_s=step)
            integral = dn.drag_integral(track)
            # Per unit time, so windows of different lengths compare. The quantity is the drag
            # integral rather than a mean density because that is what a decay measures: the
            # observed side of this comparison is a ratio of `da/dt`, and `da/dt` is
            # proportional to `rho |v_rel| (v_rel . v)`, not to `rho`. On a near-circular orbit
            # the two agree to a fraction of a per cent; on an eccentric one they do not.
            values[window.name] = float(integral["integral"]) / max(window.days * DAY_S, 1e-9)
            mean_rho[window.name] = float(integral["rho_mean"])
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = values[storm.name] / values[quiet.name] if values[quiet.name] else np.nan
        rows.append(
            {
                "norad_id": int(series["norad_id"]),
                "rho_quiet": mean_rho[quiet.name],
                "rho_storm": mean_rho[storm.name],
                "drag_quiet": values[quiet.name],
                "drag_storm": values[storm.name],
                "modelled_ratio": float(ratio),
            }
        )
    return pd.DataFrame(rows)


def density_ratios(observed: pd.DataFrame, modelled: pd.DataFrame) -> pd.DataFrame:
    """Join the two and take the difference the whole comparison rests on."""
    out = observed.merge(modelled, on="norad_id", how="inner")
    with np.errstate(invalid="ignore", divide="ignore"):
        out["ratio_of_ratios"] = out["observed_ratio"] / out["modelled_ratio"]
    return out


# --------------------------------------------------------------------------------------
# 2. The in-track error of a pre-storm element set


def _states(sets: pd.DataFrame, at: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """SGP4 states for one element set at many times, as ``(r, v, error)`` with shape ``(m, 3)``."""
    satrecs = build_satrecs(sets)
    state = propagate_satrecs(satrecs, sets["norad_id"].to_numpy(), at)
    return state.r_teme[0], state.v_teme[0], state.error[0]


def in_track_errors(sets: pd.DataFrame, pivot: datetime, window: Window) -> pd.DataFrame:
    """How far along track the last pre-``pivot`` element set is from every set issued in ``window``.

    One row per later element set: the lead time from the pivot set's epoch, and the along-track
    component of the disagreement, in kilometres, measured in the **later** set's own RIC frame
    because that is the frame the later state defines.

    **The sign is the storm term's.** ``observed_shift_km`` is *later minus propagated*: how far
    ahead the object turned out to be of where the old element set put it. More drag than the
    old set knew about lowers the orbit, a lower orbit is faster, and the object arrives ahead
    -- so a storm makes this positive, exactly as :func:`driftwatch.storm.term.in_track_shift_m`
    is positive. The two can therefore be subtracted directly, which is what
    :func:`residuals` does.
    """
    sets = sets.sort_values("epoch").drop_duplicates("epoch", keep="last").reset_index(drop=True)
    epochs = pd.to_datetime(sets["epoch"], utc=True)
    before = sets[epochs <= pd.Timestamp(pivot)]
    if not len(before):
        return pd.DataFrame()
    old = before.iloc[[-1]].reset_index(drop=True)
    old_epoch = pd.Timestamp(old["epoch"].iloc[0])

    inside = (
        (epochs > pd.Timestamp(pivot)) & (epochs >= pd.Timestamp(window.start)) & (epochs <= pd.Timestamp(window.end))
    )
    later = sets[inside].reset_index(drop=True)
    if not len(later):
        return pd.DataFrame()

    at = pd.to_datetime(later["epoch"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    r_old, _, error_old = _states(old, at)
    # Each later set evaluated at its own epoch: one propagation of zero length per set.
    r_new = np.full_like(r_old, np.nan)
    v_new = np.full_like(r_old, np.nan)
    error_new = np.zeros(len(later), dtype=int)
    for k in range(len(later)):
        r_k, v_k, e_k = _states(later.iloc[[k]].reset_index(drop=True), at[k : k + 1])
        r_new[k], v_new[k], error_new[k] = r_k[0], v_k[0], int(e_k[0])

    basis = ric_basis(r_new, v_new)
    delta = to_ric(basis, r_new - r_old)
    lead_s = (pd.to_datetime(later["epoch"], utc=True) - old_epoch).dt.total_seconds().to_numpy()
    # Did the object burn between the pivot set and each later one? A satellite that raised or
    # lowered its orbit inside the comparison has an along-track error that is its operator's,
    # not the atmosphere's, and on a population dominated by Starlink that is most of the
    # variance. The flag travels on the row so the summary can report both populations rather
    # than a filtered one; it is *not* dropped here, because "how wrong was the screening run"
    # is a fair question that includes the burns.
    spanning = sets[(epochs >= old_epoch) & (epochs <= pd.Timestamp(later["epoch"].iloc[-1]))]
    burned_by: dict[pd.Timestamp, bool] = {}
    if len(spanning) >= 2:
        jump, _ = bal.manoeuvre_intervals(spanning.reset_index(drop=True))
        spanning_epochs = pd.to_datetime(spanning["epoch"], utc=True).to_numpy()
        seen = False
        for k, when in enumerate(spanning_epochs[1:]):
            seen = seen or bool(jump[k])
            burned_by[pd.Timestamp(when)] = seen
    manoeuvred = [bool(burned_by.get(pd.Timestamp(t), False)) for t in pd.to_datetime(later["epoch"], utc=True)]
    return pd.DataFrame(
        {
            "norad_id": int(sets["norad_id"].iloc[0]),
            "pivot_epoch": old_epoch,
            "epoch": pd.to_datetime(later["epoch"], utc=True),
            "lead_days": lead_s / DAY_S,
            "radial_km": delta[:, 0],
            "observed_shift_km": delta[:, 1],
            "cross_km": delta[:, 2],
            "manoeuvred": manoeuvred,
            "sgp4_error": np.maximum(error_old, error_new),
        }
    )


def predicted_shifts(
    sets: pd.DataFrame,
    coefficient: pd.Series | None,
    table: pd.DataFrame | dn.WeatherGrid,
    pivot: datetime,
    at: pd.Series,
    *,
    step_scale: float = 4.0,
) -> pd.DataFrame:
    """The storm term's own prediction for the same object at the same times.

    Driven by the pre-``pivot`` element set and the **observed** ap, so nothing after the pivot
    reaches the prediction. Returns the shift and its sigma in kilometres at each of ``at``.
    """
    epochs = pd.to_datetime(sets["epoch"], utc=True)
    before = sets[epochs <= pd.Timestamp(pivot)].sort_values("epoch")
    if not len(before) or not len(at):
        return pd.DataFrame()
    row = before.iloc[-1]
    end = pd.Timestamp(at.max()).to_pydatetime()
    step = dn.sample_step_s(float(row["mean_motion"]), float(row.get("eccentricity", 0.0))) * step_scale
    series = term.object_shift(row, coefficient, table, end, step_s=step)
    if not len(series.seconds):
        return pd.DataFrame()
    seconds = term.times_since_epoch_s(pd.Timestamp(row["epoch"]).to_pydatetime(), at.to_numpy())
    shift, sigma = series.at(seconds)
    return pd.DataFrame(
        {
            "norad_id": int(row["norad_id"]),
            "epoch": at.to_numpy(),
            "predicted_shift_km": shift / 1000.0,
            "predicted_sigma_km": sigma / 1000.0,
            "b_m2_kg": series.b_m2_kg,
            "b_source": series.b_source,
            "scoreable": series.scoreable,
        }
    )


def residuals(observed: pd.DataFrame, predicted: pd.DataFrame, control: pd.DataFrame | None = None) -> pd.DataFrame:
    """``observed - predicted`` per element set, with the quiet control subtracted where there is one.

    The control is matched on **lead time**, not on epoch: what it measures is how much
    along-track error SGP4 accumulates by itself over that many days for that object, and that
    is a function of the lead. Where an object has a control at a comparable lead its median is
    removed from the observed shift before the residual is taken; where it has none the raw
    number is kept and ``control_km`` is NaN, so a reader can separate the two populations.
    """
    out = observed.merge(predicted, on=["norad_id", "epoch"], how="inner")
    out["control_km"] = np.nan
    if control is not None and len(control):
        # One number per object and lead-time day, which is as fine as the control can support.
        control = control.copy()
        control["lead_bin"] = np.round(control["lead_days"]).astype(int)
        by_bin = control.groupby(["norad_id", "lead_bin"])["observed_shift_km"].median()
        bins = np.round(out["lead_days"]).astype(int)
        keys = pd.MultiIndex.from_arrays([out["norad_id"], bins])
        out["control_km"] = by_bin.reindex(keys).to_numpy()
    out["corrected_shift_km"] = out["observed_shift_km"] - np.nan_to_num(out["control_km"], nan=0.0)
    out["residual_km"] = out["corrected_shift_km"] - out["predicted_shift_km"]
    with np.errstate(invalid="ignore", divide="ignore"):
        out["residual_sigmas"] = out["residual_km"] / out["predicted_sigma_km"]
        out["ratio"] = out["corrected_shift_km"] / out["predicted_shift_km"]
    return out


def slope_through_origin(predicted: pd.Series, observed: pd.Series) -> float | None:
    """``sum(p o) / sum(p^2)``: how much of the predicted shift the record actually shows.

    The headline number, and deliberately not the median of the per-event ratios. A ratio whose
    denominator is a fraction of a kilometre is unbounded noise, and a population of them has a
    median that says more about how many small predictions there are than about whether the
    large ones came true. A least-squares slope through the origin weights each event by the
    size of the thing being predicted, which is what "does the term have the right magnitude"
    means. Through the origin because a term that predicts nothing must predict zero.
    """
    p = np.asarray(predicted, dtype=float)
    o = np.asarray(observed, dtype=float)
    ok = np.isfinite(p) & np.isfinite(o)
    denominator = float(np.sum(p[ok] ** 2))
    if ok.sum() < 3 or denominator <= 0:
        return None
    return round(float(np.sum(p[ok] * o[ok]) / denominator), 3)


def robust_slope(predicted: pd.Series, observed: pd.Series, *, fraction: float = 0.5) -> float | None:
    """The median of ``observed / predicted`` over the events with the largest predictions.

    :func:`slope_through_origin` is the right estimator when the errors are well behaved and the
    wrong one when they are not: it is a least-squares fit, so a single object with a 1,200 km
    residual moves it further than four hundred well-behaved ones. On the May 2024 population
    that happens -- a handful of low objects under active control swing the least-squares slope
    from 1.3 to -0.08 -- so the two are reported side by side and a disagreement between them is
    read as "the tail is doing the work", which is a fact about the data rather than a defect in
    either number.

    The restriction to the largest ``fraction`` of ``|predicted|`` is what makes a median of
    ratios meaningful at all: a ratio whose denominator is a hundred metres is noise with a
    number attached, and including it would measure how many small predictions there are.
    """
    p = np.asarray(predicted, dtype=float)
    o = np.asarray(observed, dtype=float)
    ok = np.isfinite(p) & np.isfinite(o) & (p != 0)
    p, o = p[ok], o[ok]
    if len(p) < 6:
        return None
    cut = float(np.quantile(np.abs(p), 1.0 - fraction))
    big = np.abs(p) >= cut
    if big.sum() < 3:
        return None
    return round(float(np.median(o[big] / p[big])), 3)


def correlation(predicted: pd.Series, observed: pd.Series) -> float | None:
    """Pearson correlation of the two, which says whether the term is tracking anything at all.

    Distinct from the slope and worth both: a term with the wrong constant but the right shape
    has a high correlation and a slope away from one, and is fixable; a term with a slope near
    one and no correlation is right on average and useless per event.
    """
    p = np.asarray(predicted, dtype=float)
    o = np.asarray(observed, dtype=float)
    ok = np.isfinite(p) & np.isfinite(o)
    if ok.sum() < 6 or np.std(p[ok]) == 0 or np.std(o[ok]) == 0:
        return None
    return round(float(np.corrcoef(p[ok], o[ok])[0, 1]), 3)


def sign_agreement(predicted: pd.Series, observed: pd.Series) -> float | None:
    """The fraction of comparisons whose observed shift has the sign the term predicted.

    The bluntest per-event statistic and the one least moved by a tail: a term with no skill at
    a lead sits at one half here whatever its least-squares slope says, because the slope and
    the correlation are carried by the handful of largest events. Reported beside them because
    on the May 2024 record the three disagree inside two days of lead and agree beyond it, and
    that disagreement is the finding.
    """
    p = np.asarray(predicted, dtype=float)
    o = np.asarray(observed, dtype=float)
    ok = np.isfinite(p) & np.isfinite(o) & (p != 0) & (o != 0)
    if ok.sum() < 3:
        return None
    return round(float(np.mean(np.sign(p[ok]) == np.sign(o[ok]))), 3)


def lead_time_table(frame: pd.DataFrame, *, min_rows: int = 5) -> dict[int, dict[str, Any]]:
    """One row per whole day of lead: the statistics of the comparisons at that lead.

    Whole days rather than finer bins because the element sets arrive when the catalogue issues
    them, so a half-day bin at one day holds a couple of dozen comparisons. ``median_abs_residual_km``
    is added beside the slope pair and the correlation because it is the number an operator would
    actually feel: how far from the prediction the object typically turned out to be.
    """
    out: dict[int, dict[str, Any]] = {}
    if not len(frame):
        return out
    for lead, group in frame.groupby(np.round(frame["lead_days"]).astype(int)):
        if len(group) < min_rows:
            continue
        out[int(lead)] = {
            "n": int(len(group)),
            "n_objects": int(group["norad_id"].nunique()),
            "median_observed_km": round(float(group["corrected_shift_km"].median()), 3),
            "median_predicted_km": round(float(group["predicted_shift_km"].median()), 3),
            "median_abs_residual_km": round(float(group["residual_km"].abs().median()), 3),
            "p84_abs_residual_km": round(float(group["residual_km"].abs().quantile(0.84)), 3),
            "slope": slope_through_origin(group["predicted_shift_km"], group["corrected_shift_km"]),
            "slope_robust": robust_slope(group["predicted_shift_km"], group["corrected_shift_km"]),
            "correlation": correlation(group["predicted_shift_km"], group["corrected_shift_km"]),
            "sign_agreement": sign_agreement(group["predicted_shift_km"], group["corrected_shift_km"]),
        }
    return out


def residual_summary(frame: pd.DataFrame, *, by_altitude: pd.Series | None = None) -> dict[str, Any]:
    """The distribution the review asks for, and its dependence on lead time and altitude."""
    if not len(frame):
        return {"n": 0}
    usable = frame[np.isfinite(frame["residual_km"]) & frame.get("scoreable", True)]
    if not len(usable):
        return {"n": 0, "note": "nothing scoreable"}
    quiet_flying = usable[~usable["manoeuvred"].astype(bool)] if "manoeuvred" in usable else usable

    def stats(f: pd.DataFrame) -> dict[str, Any]:
        return {
            "n": int(len(f)),
            "median_observed_km": round(float(f["corrected_shift_km"].median()), 3),
            "median_predicted_km": round(float(f["predicted_shift_km"].median()), 3),
            "median_residual_km": round(float(f["residual_km"].median()), 3),
            "p16_residual_km": round(float(f["residual_km"].quantile(0.16)), 3),
            "p84_residual_km": round(float(f["residual_km"].quantile(0.84)), 3),
            "slope": slope_through_origin(f["predicted_shift_km"], f["corrected_shift_km"]),
            "slope_robust": robust_slope(f["predicted_shift_km"], f["corrected_shift_km"]),
            "correlation": correlation(f["predicted_shift_km"], f["corrected_shift_km"]),
            "sign_agreement": sign_agreement(f["predicted_shift_km"], f["corrected_shift_km"]),
            "median_ratio": round(float(f["ratio"].median()), 3),
            "median_residual_sigmas": round(float(f["residual_sigmas"].median()), 3),
        }

    out: dict[str, Any] = {**stats(usable), "n_objects": int(usable["norad_id"].nunique())}
    # The population the term is actually a claim about, in two narrowings, each stated rather
    # than applied silently. First: objects the atmosphere alone was moving, with the burns out.
    out["free_flying"] = {
        **stats(quiet_flying),
        "n_objects": int(quiet_flying["norad_id"].nunique()),
        "n_excluded_for_manoeuvring": int(len(usable) - len(quiet_flying)),
    }
    # Second, and this is the headline: of those, the ones whose ballistic coefficient was
    # *measured* from their own decay history. The term is the product of a coefficient and a
    # density excess, so an object standing in with the run's population median has no
    # coefficient in it to test and a B* inversion has a number that is not a coefficient. This
    # is a narrowing of the population, not of the residual: nothing is trimmed inside it.
    measured = quiet_flying[quiet_flying["b_source"] == "history"] if "b_source" in quiet_flying else quiet_flying
    out["free_flying_measured_coefficient"] = {
        **stats(measured),
        "n_objects": int(measured["norad_id"].nunique()),
        "definition": "no manoeuvre between the pivot and the comparison, and B fitted from the object's own decay",
        # The lead-time structure of the skill, on the population the term is a claim about
        # (added 2026-09-05). The headline correlation is a population figure; where in the
        # window it comes from is the operational question, and the answer is not uniform.
        "by_lead_day": lead_time_table(measured),
    }
    usable = quiet_flying if len(quiet_flying) >= 30 else usable
    out["by_lead_day"] = {
        int(k): stats(g) for k, g in usable.groupby(np.round(usable["lead_days"]).astype(int)) if len(g) >= 5
    }
    out["by_b_source"] = {str(k): stats(g) for k, g in usable.groupby("b_source") if len(g) >= 5}
    if by_altitude is not None:
        altitude = by_altitude.reindex(usable["norad_id"]).to_numpy(dtype=float)
        bands = pd.cut(altitude, bins=[0, 350, 450, 550, 650, 800, 2000])
        out["by_altitude_km"] = {str(k): stats(g) for k, g in usable.groupby(bands, observed=True) if len(g) >= 5}
    return out


# --------------------------------------------------------------------------------------
# The February 2022 launch


def decay_history(sets: pd.DataFrame) -> pd.DataFrame:
    """Mean semi-major axis and perigee against time for one object, for the decay plots and tables."""
    sets = sets.sort_values("epoch").drop_duplicates("epoch", keep="last").reset_index(drop=True)
    if not len(sets):
        return pd.DataFrame()
    a_m = bal.mean_sma_m(sets)
    mean_motion = pd.to_numeric(sets["mean_motion"], errors="coerce").to_numpy(dtype=float)
    ecc = pd.to_numeric(sets["eccentricity"], errors="coerce").to_numpy(dtype=float)
    return pd.DataFrame(
        {
            "norad_id": sets["norad_id"].astype("int64").to_numpy(),
            "name": sets["name"].astype(str).to_numpy() if "name" in sets else "",
            "epoch": pd.to_datetime(sets["epoch"], utc=True),
            "mean_motion": mean_motion,
            "a_km": a_m / 1000.0,
            "altitude_km": a_m / 1000.0 - dn.EARTH_RADIUS_KM,
            "perigee_km": [bal.perigee_altitude_km(n, e) for n, e in zip(mean_motion, ecc, strict=True)],
        }
    )


def lifetime_from_decay(track: pd.DataFrame) -> dict[str, Any]:
    """How fast one object came down, and where it ended: the February 2022 question in one row."""
    if len(track) < 2:
        return {"n_sets": int(len(track)), "note": "too few element sets"}
    span_days = float((track["epoch"].iloc[-1] - track["epoch"].iloc[0]).total_seconds() / DAY_S)
    drop_km = float(track["a_km"].iloc[0] - track["a_km"].iloc[-1])
    return {
        "norad_id": int(track["norad_id"].iloc[0]),
        "name": str(track["name"].iloc[0]),
        "n_sets": int(len(track)),
        "first_epoch": track["epoch"].iloc[0].isoformat(),
        "last_epoch": track["epoch"].iloc[-1].isoformat(),
        "span_days": round(span_days, 2),
        "first_altitude_km": round(float(track["altitude_km"].iloc[0]), 1),
        "last_altitude_km": round(float(track["altitude_km"].iloc[-1]), 1),
        "drop_km": round(drop_km, 1),
        "mean_rate_km_day": round(drop_km / span_days, 3) if span_days > 0 else None,
    }


def storm_ratio_at(table: pd.DataFrame, altitude_km: float, at: datetime, *, quiet_at: datetime) -> dict[str, Any]:
    """The density at one altitude on a storm day against a quiet day, straight from the model.

    Used for the February 2022 question, which is narrower than the May 2024 one: not "does the
    model get the enhancement right" but "does the model show *any* elevated drag at 210 km for
    a G1". A G1 is a small storm, and 210 km is low enough that the density is dominated by the
    solar cycle and the diurnal bulge rather than by the geomagnetic term.
    """
    grid = dn.weather_grid(table)
    out = {}
    for label, when in (("storm", at), ("quiet", quiet_at)):
        times = [when + timedelta(hours=h) for h in range(0, 24, 3)]
        inputs = dn.msis_inputs(times, grid)
        rho = dn.density(times, np.zeros(len(times)), np.zeros(len(times)), np.full(len(times), altitude_km), inputs)
        out[label] = float(np.nanmean(rho))
    ratio = out["storm"] / out["quiet"] if out["quiet"] else float("nan")
    return {"altitude_km": altitude_km, **out, "ratio": round(float(ratio), 4)}


def coefficient_for(coefficients: pd.DataFrame, norad_id: int) -> pd.Series | None:
    """One object's row of a coefficient table, or None."""
    if not len(coefficients):
        return None
    hit = coefficients[coefficients["norad_id"] == int(norad_id)]
    return hit.iloc[0] if len(hit) else None


__all__ = [
    "Window",
    "coefficient_for",
    "decay_history",
    "decay_rate",
    "decay_rates",
    "density_ratios",
    "in_track_errors",
    "lead_time_table",
    "lifetime_from_decay",
    "modelled_density_ratio",
    "observed_density_ratio",
    "predicted_shifts",
    "correlation",
    "residual_summary",
    "robust_slope",
    "sign_agreement",
    "slope_through_origin",
    "residuals",
    "storm_ratio_at",
]
