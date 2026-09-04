"""What is the relative shift, really? The splits that attacked the headline result.

The headline result of Phase 3 was counter-intuitive and therefore had to be attacked before it
was published: **a storm lowers the probability on most events.** The explanation first attached
to it did not survive, and this module is what falsified it. The result itself did not survive
either, but not because of anything here: on 2026-09-05 an external review found that the storm
term was displacing operator-controlled objects (`docs/storm-term.md`, "Corrected 2026-09-05"),
and the lowering lived entirely in those events. This module now leaves events with an
operator-controlled side out of the ratio, where one displacement is zero by rule, and reports how
many it left out. The splits below could not have found that error, because they split along the
axes a *physical* cancellation would show on and not along the one a *category* error shows on.

.. note::

   **Corrected at the Step 4 review (2026-09-03).** This module was written to test a claim of
   *common-mode cancellation*: that a storm displaces both objects of a pair in the same
   direction by a similar amount, so that what reaches the miss vector is a *relative* shift far
   smaller than either absolute shift. The splits below excluded the artefact the review asked
   about and then refuted the claim itself. The measured relative-to-absolute ratio is **1.91**
   out of a possible 2 -- the two displacements are nearly independent, not a common mode --
   flat in both splits, with the two in-track shifts uncorrelated (r = 0.08) and the median
   angle between the two objects' in-track directions at the encounter **120°**. A screener
   finds crossing pairs, because a low relative speed is what stops two objects closing on each
   other.

   The result needs no cancellation to explain it: a displacement of tens of kilometres applied
   to a miss of a few separates more pairs than it creates, and the tighter the miss the more
   surely it does. ``cancellation_ratio`` keeps its name because it is the quantity the review
   asked for and the name is how the two runs already on disk are keyed; read it as the
   relative-to-absolute shift ratio, and read a value near 2 as the *absence* of cancellation.
   ``docs/storm-term.md`` carries the full account.

The claim was physical, and it had an obvious failure mode. Two objects can also come out with
similar shifts because they were handed **the same coefficient by the same rule** -- both
standing in with the run's `typical` median for their category and altitude band, say, or both
inverted from B\\* by the same code path. If the cancellation were an artefact of shared inputs
it would be strongest exactly where the inputs are shared and weakest where they are not, and it
would say nothing about the atmosphere.

So this module splits the ratio two ways and lets the split answer the question.

**By ballistic coefficient source.** A pair whose two coefficients were *measured
independently* -- both fitted from their own decay histories, ``history`` against ``history``
-- shares no input at all beyond the density model. If the ratio there is as small as it is for
a ``typical``-``typical`` pair, the cancellation is not coming from shared values.

**By the altitude difference between the two objects.** This is the physical prediction and the
sharper test. The shift goes as ``B drho v^2 t^2``, and the density falls by an order of
magnitude every 50 km or so of altitude, so two objects in the same shell see nearly the same
excess and two objects 100 km apart do not. If the cancellation is physical the ratio must
*rise* with the altitude difference; if it is an artefact of shared coefficients it has no
reason to depend on altitude at all. It did neither: the ratio is flat in altitude difference
(rank correlation -0.10) and flat across source pairs, which excludes the artefact and leaves
no cancellation to explain.

**Which altitude, and why it cannot be the one at the encounter.** The first version of this
split used each object's altitude at the stored time of closest approach, and it could not have
worked: a conjunction *is* a near-coincidence in position, so the two objects are at nearly the
same altitude at the moment they pass, by construction. On the May 2024 replay every pair came
out inside 30 km of each other and the split had no range to show a trend across. The
displacement is not accumulated at the encounter, though -- it is accumulated over the whole
window, along each object's own orbit -- so the axis that matters is the **mean altitude of the
two orbits**, which does have a range. The altitude at the encounter is kept as a column
because it is what a reader will assume is meant, and stating that it is not is cheaper than
being asked.

Both splits also report the relative and absolute shifts themselves, in kilometres, so the
ratio can be read against the sizes it came from.

## Every aggregate twice: validated and indicative

Step 4 measured the storm term against May 2024 and found it predictive at r = 0.88 for an
object whose ballistic coefficient was fitted from its own decay, and of no demonstrated skill
for one carrying a B\\* inversion or a population stand-in. An event needs **both** its objects
measured before the validation reaches it, so every event carries ``storm_validity``
(:func:`driftwatch.storm.term.event_validity`) and every table below is reported over the
``validated`` events, over the ``indicative`` ones, and over both together -- never over both
together alone. A median taken across a population that is mostly indicative reads as a
measurement and is not one.

## The other half: which of the two effects moves the number

A scenario does two things -- it moves the objects and it widens the ellipse -- and the run
carries all three probabilities on every row (see :mod:`driftwatch.risk.scenario`).
:func:`effect_split` puts them beside each other over probability bands, because the answer is
not the same at every size: the shift dominates where the miss is small against the shift, and
the variance is what is left everywhere else.

Unscoreable events -- those whose storm term ran outside the linear theory -- are excluded from
everything here, as they are from every other aggregate.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from driftwatch.storm import term

log = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6378.137

# The altitude-difference bins the cancellation is split over, in kilometres. The edges are
# density scale heights rather than round numbers: NRLMSIS's scale height in the drag regime
# runs from about 30 km at 300 km altitude to about 70 km at 700, so a pair separated by less
# than 10 km sees essentially one atmosphere, a pair separated by 100 km sees two.
ALTITUDE_DIFFERENCE_EDGES_KM: tuple[float, ...] = (0.0, 2.0, 10.0, 30.0, 100.0, 300.0, np.inf)

# The probability bands `effect_split` reports over. Below 1e-12 the three probabilities are
# all indistinguishable from zero and their ratios are numerical noise.
PC_BAND_EDGES: tuple[float, ...] = (1e-12, 1e-9, 1e-7, 1e-5, 1.0)


def _bin_labels(edges: tuple[float, ...], unit: str) -> list[str]:
    out = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        out.append(f"{lo:g} to {hi:g} {unit}" if np.isfinite(hi) else f"over {lo:g} {unit}")
    return out


def altitudes_at_tca_km(events: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Each object's altitude at the stored time of closest approach, from its own TEME state.

    The altitude that matters for the density excess is the one the object is at when the
    encounter happens, and the events table already carries both positions there, so this needs
    no propagation and no element set. Spherical Earth: the difference between the two
    altitudes is what is used, and the flattening term is common to both to within a few
    hundred metres at any one point of the orbit.
    """
    primary = np.linalg.norm(events[["p_x_km", "p_y_km", "p_z_km"]].to_numpy(dtype=float), axis=1)
    secondary = np.linalg.norm(events[["s_x_km", "s_y_km", "s_z_km"]].to_numpy(dtype=float), axis=1)
    return primary - EARTH_RADIUS_KM, secondary - EARTH_RADIUS_KM


def mean_altitudes_km(elements: pd.DataFrame) -> pd.Series:
    """Each object's mean orbital altitude, from its own element set: the axis the split needs.

    Brouwer mean semi-major axis through SGP4's own initialisation, minus the Earth's radius --
    a property of the orbit rather than of the encounter. See the module docstring for why the
    altitude at closest approach is the wrong one.
    """
    from driftwatch.drag import ballistic as bal

    if not len(elements):
        return pd.Series(dtype=float)
    a_m = bal.mean_sma_m(elements)
    return pd.Series(a_m / 1000.0 - EARTH_RADIUS_KM, index=elements["norad_id"].astype("int64").to_numpy())


def cancellation_frame(
    risk: pd.DataFrame,
    events: pd.DataFrame,
    coefficients: pd.DataFrame,
    altitudes: pd.Series | None = None,
) -> pd.DataFrame:
    """One row per scoreable event with its two shifts, their ratio, the source pair and the altitudes.

    ``relative_shift_km`` is the true relative displacement -- both objects' in-track shifts
    rotated out of their own RIC frames and differenced in TEME, which is what actually enters
    the miss vector -- and it is computed in :func:`driftwatch.risk.scenario.run_risk` rather
    than reconstructed here from the two in-track components, because those live in two
    different frames and their scalar difference is not a displacement.
    """
    joined = events.merge(risk, on="event_id", how="inner", suffixes=("", "_risk"))
    if "scoreable" in joined.columns:
        joined = joined[joined["scoreable"].astype(bool)]
    joined = joined[joined["relative_shift_km"].notna()]
    # An event with an operator-controlled side has one displacement zeroed by rule, so its
    # relative-to-absolute ratio is 2 by construction and says nothing about cancellation. Those
    # events are left out here and counted, rather than allowed to pull the ratio to the ceiling.
    n_controlled = 0
    if {"storm_source_primary", "storm_source_secondary"} <= set(joined.columns):
        controlled = joined["storm_source_primary"].map(term.is_operator_controlled) | joined[
            "storm_source_secondary"
        ].map(term.is_operator_controlled)
        n_controlled = int(controlled.sum())
        joined = joined[~controlled]
    joined = joined.reset_index(drop=True)
    if not len(joined):
        empty = pd.DataFrame()
        empty.attrs["n_excluded_operator_controlled"] = n_controlled
        return empty

    source = coefficients.set_index("norad_id")["source"].astype(str) if len(coefficients) else pd.Series(dtype=str)
    p = joined["primary_norad_id"].to_numpy(dtype=np.int64)
    s = joined["secondary_norad_id"].to_numpy(dtype=np.int64)
    alt_p, alt_s = altitudes_at_tca_km(joined)

    shift_p = np.abs(joined["shift_i_primary_km"].to_numpy(dtype=float))
    shift_s = np.abs(joined["shift_i_secondary_km"].to_numpy(dtype=float))
    absolute = 0.5 * (shift_p + shift_s)
    relative = joined["relative_shift_km"].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(absolute > 0, relative / absolute, np.nan)

    orbit_p, orbit_s = alt_p, alt_s
    if altitudes is not None and len(altitudes):
        orbit_p = altitudes.reindex(p).to_numpy(dtype=float)
        orbit_s = altitudes.reindex(s).to_numpy(dtype=float)
    source_p = source.reindex(p).fillna("unknown").to_numpy(dtype=object)
    source_s = source.reindex(s).fillna("unknown").to_numpy(dtype=object)
    # Prefer the label the run itself wrote; fall back to the coefficient table for a run
    # scored before `storm_validity` existed, so an old run still splits.
    validity = (
        joined["storm_validity"].astype(str).to_numpy(dtype=object)
        if "storm_validity" in joined.columns
        else term.event_validities(source_p, source_s)
    )
    # Unordered: a history-bstar pair and a bstar-history pair are the same experiment.
    pair = np.array(["+".join(sorted((str(a), str(b)))) for a, b in zip(source_p, source_s, strict=True)], dtype=object)

    difference = np.abs(orbit_p - orbit_s)
    out = pd.DataFrame(
        {
            "event_id": joined["event_id"].to_numpy(),
            "primary_norad_id": p,
            "secondary_norad_id": s,
            "b_source_primary": source_p,
            "b_source_secondary": source_s,
            "b_source_pair": pair,
            "storm_validity": validity,
            "shared_source": source_p == source_s,
            "altitude_primary_km": orbit_p,
            "altitude_secondary_km": orbit_s,
            "tca_altitude_difference_km": np.abs(alt_p - alt_s),
            "altitude_difference_km": difference,
            "altitude_difference_band": pd.cut(
                difference,
                bins=list(ALTITUDE_DIFFERENCE_EDGES_KM),
                labels=_bin_labels(ALTITUDE_DIFFERENCE_EDGES_KM, "km"),
                include_lowest=True,
            ),
            "abs_shift_primary_km": shift_p,
            "abs_shift_secondary_km": shift_s,
            "abs_shift_mean_km": absolute,
            "relative_shift_km": relative,
            "cancellation_ratio": ratio,
            "pc": joined["pc"].to_numpy(dtype=float),
            "pc_shift_only": joined["pc_shift_only"].to_numpy(dtype=float),
            "pc_variance_only": joined["pc_variance_only"].to_numpy(dtype=float),
        }
    )
    out.attrs["n_excluded_operator_controlled"] = n_controlled
    return out


def _group(frame: pd.DataFrame, by: str, *, min_events: int = 1) -> pd.DataFrame:
    """Median ratio and median shifts per group, with the count, ordered by the group key."""
    grouped = frame.groupby(by, observed=True, dropna=False)
    out = pd.DataFrame(
        {
            "n_events": grouped.size(),
            "median_relative_km": grouped["relative_shift_km"].median(),
            "median_absolute_km": grouped["abs_shift_mean_km"].median(),
            "median_ratio": grouped["cancellation_ratio"].median(),
            "p90_ratio": grouped["cancellation_ratio"].quantile(0.9),
        }
    )
    return out[out["n_events"] >= min_events].round(4)


def _overall(frame: pd.DataFrame) -> dict[str, Any]:
    """The headline four numbers over whatever subset is handed in."""
    return {
        "n_events": int(len(frame)),
        "median_relative_km": round(float(frame["relative_shift_km"].median()), 4),
        "median_absolute_km": round(float(frame["abs_shift_mean_km"].median()), 4),
        "median_ratio": round(float(frame["cancellation_ratio"].median()), 4),
        "p90_ratio": round(float(frame["cancellation_ratio"].quantile(0.9)), 4),
    }


def split_by_validity(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """``{"validated": ..., "indicative": ..., "combined": ...}``, in that order.

    The ordering is deliberate and every caller keeps it: the measured population is read first
    and the combined figure last, so a reader never meets a median over a mostly-indicative
    population before meeting the one the validation actually covers. Groups with no events are
    absent rather than present and empty.
    """
    out: dict[str, pd.DataFrame] = {}
    if "storm_validity" in frame.columns:
        for label in (term.VALIDATED, term.INDICATIVE, term.OPERATOR_CONTROLLED):
            subset = frame[frame["storm_validity"].astype(str) == label]
            if len(subset):
                out[label] = subset
    out["combined"] = frame
    return out


def cancellation(frame: pd.DataFrame, *, min_events: int = 20) -> dict[str, Any]:
    """The two splits, plus the overall figure, as plain tables ready for the docs and run.json.

    Reported **three ways**: over the events whose two objects both have a measured ballistic
    coefficient, over the rest, and over both together. See the module docstring.
    """
    excluded = int(frame.attrs.get("n_excluded_operator_controlled", 0)) if hasattr(frame, "attrs") else 0
    if not len(frame):
        return {"n_events": 0, "n_excluded_operator_controlled": excluded}
    groups = split_by_validity(frame)
    return {
        "n_events": int(len(frame)),
        "n_excluded_operator_controlled": excluded,
        "overall": {k: v for k, v in _overall(frame).items() if k != "n_events"},
        "by_storm_validity": {label: _overall(subset) for label, subset in groups.items()},
        "by_b_source_pair": _group(frame, "b_source_pair", min_events=min_events).to_dict(orient="index"),
        "by_shared_source": _group(frame, "shared_source").to_dict(orient="index"),
        "by_altitude_difference": _group(frame, "altitude_difference_band").to_dict(orient="index"),
        "by_altitude_difference_per_validity": {
            label: _group(subset, "altitude_difference_band").to_dict(orient="index")
            for label, subset in groups.items()
        },
        "spearman_ratio_vs_altitude_difference": _spearman(
            frame["altitude_difference_km"].to_numpy(dtype=float),
            frame["cancellation_ratio"].to_numpy(dtype=float),
        ),
        "spearman_per_validity": {
            label: _spearman(
                subset["altitude_difference_km"].to_numpy(dtype=float),
                subset["cancellation_ratio"].to_numpy(dtype=float),
            )
            for label, subset in groups.items()
        },
        "median_tca_altitude_difference_km": round(float(frame["tca_altitude_difference_km"].median()), 3)
        if "tca_altitude_difference_km" in frame
        else None,
    }


def _spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    """Rank correlation, the one number that says whether the altitude split has a trend in it.

    Rank rather than linear because the ratio is bounded below by zero and the altitude
    difference is heavily skewed, so a Pearson coefficient would be reporting the tail.
    """
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:
        return None
    rx = pd.Series(x[ok]).rank().to_numpy()
    ry = pd.Series(y[ok]).rank().to_numpy()
    if rx.std() == 0 or ry.std() == 0:
        return None
    return round(float(np.corrcoef(rx, ry)[0, 1]), 4)


def effect_split(frame: pd.DataFrame) -> dict[str, Any]:
    """Combined, shift-only and variance-only probability side by side, over probability bands.

    Banded on ``pc_variance_only`` -- the scenario's covariance with the objects left where their
    element sets put them -- because that is the closest thing to a size the event had *before*
    the shift moved it, and banding on the combined number would sort the events by the very
    effect being measured.

    ``bands`` is the combined table and ``by_storm_validity`` the same table computed separately
    over the validated and indicative events, because which of the two effects moves the number
    is exactly the kind of claim that must not be read off a population the validation does not
    reach.
    """
    if not len(frame):
        return {"n_events": 0}
    out = {"n_events": int(len(frame)), "bands": _bands(frame)}
    groups = split_by_validity(frame)
    if len(groups) > 1:
        out["by_storm_validity"] = {
            label: {"n_events": int(len(subset)), "bands": _bands(subset)} for label, subset in groups.items()
        }
    return out


def _bands(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """One row per probability band: the three probabilities and how many the shift moved each way."""
    rows: list[dict[str, Any]] = []
    baseline = frame["pc_variance_only"].to_numpy(dtype=float)
    for lo, hi in zip(PC_BAND_EDGES[:-1], PC_BAND_EDGES[1:], strict=True):
        inside = np.isfinite(baseline) & (baseline >= lo) & (baseline < hi)
        if not inside.any():
            continue
        band = frame[inside]
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = band["pc"].to_numpy(dtype=float) / band["pc_variance_only"].to_numpy(dtype=float)
        rows.append(
            {
                "band": f"{lo:g} to {hi:g}",
                "n_events": int(inside.sum()),
                "median_pc": f"{float(band['pc'].median()):.3e}",
                "median_pc_shift_only": f"{float(band['pc_shift_only'].median()):.3e}",
                "median_pc_variance_only": f"{float(band['pc_variance_only'].median()):.3e}",
                "median_pc_over_variance_only": round(float(np.nanmedian(ratio)), 4),
                "n_lowered_by_shift": int(np.nansum(ratio < 1.0)),
                "n_raised_by_shift": int(np.nansum(ratio > 1.0)),
            }
        )
    return rows


def unscoreable_objects(
    risk: pd.DataFrame,
    events: pd.DataFrame,
    objects: pd.DataFrame,
    coefficients: pd.DataFrame,
) -> pd.DataFrame:
    """The objects that made events unscoreable, with enough about each to say what they are.

    The review asked for this by name: a count of objects outside the linear theory is not a
    finding until somebody can say whether they are a physical class or a bug.
    """
    if "scoreable" not in risk.columns:
        return pd.DataFrame()
    bad = risk[~risk["scoreable"].astype(bool)]
    if not len(bad):
        return pd.DataFrame()
    joined = events.merge(bad[["event_id", "unscoreable_reason"]], on="event_id", how="inner")
    alt_p, alt_s = altitudes_at_tca_km(joined)
    named: dict[int, float] = {}
    for column, altitude in (("primary_norad_id", alt_p), ("secondary_norad_id", alt_s)):
        for norad_id, value in zip(joined[column].to_numpy(dtype=np.int64), altitude, strict=True):
            named.setdefault(int(norad_id), float(value))

    # Only the objects actually named in a reason: an event is unscoreable because of one of its
    # two objects, and the other is an innocent bystander.
    reasons: dict[int, str] = {}
    for text in joined["unscoreable_reason"].astype(str):
        for part in text.split("; "):
            if ":" in part:
                reasons[int(part.split(":", 1)[0])] = part.split(":", 1)[1].strip()

    obj = objects.set_index("norad_id") if len(objects) else pd.DataFrame()
    coef = coefficients.set_index("norad_id") if len(coefficients) else pd.DataFrame()
    rows = []
    for norad_id, reason in sorted(reasons.items()):
        row: dict[str, Any] = {"norad_id": norad_id, "reason": reason}
        if norad_id in obj.index:
            row |= {
                "name": str(obj.loc[norad_id, "name"]),
                "category": str(obj.loc[norad_id, "category"]),
                "rcs_m2": float(obj.loc[norad_id, "rcs_m2"]) if pd.notna(obj.loc[norad_id, "rcs_m2"]) else np.nan,
            }
        if norad_id in coef.index:
            row |= {
                "b_m2_kg": float(coef.loc[norad_id, "b_m2_kg"]),
                "b_source": str(coef.loc[norad_id, "source"]),
                "alt_band": str(coef.loc[norad_id, "alt_band"]),
            }
        row["altitude_at_tca_km"] = round(named.get(norad_id, float("nan")), 1)
        row["n_events"] = int(
            ((joined["primary_norad_id"] == norad_id) | (joined["secondary_norad_id"] == norad_id)).sum()
        )
        rows.append(row)
    return pd.DataFrame(rows)


def unscoreable_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """What the unscoreable objects have in common, which is the part that says whether it is physical."""
    if not len(frame):
        return {"n_objects": 0}
    out: dict[str, Any] = {
        "n_objects": int(len(frame)),
        "n_events": int(frame["n_events"].sum()),
        "by_category": {str(k): int(v) for k, v in frame.get("category", pd.Series(dtype=str)).value_counts().items()},
        "by_b_source": {str(k): int(v) for k, v in frame.get("b_source", pd.Series(dtype=str)).value_counts().items()},
        "by_alt_band": {str(k): int(v) for k, v in frame.get("alt_band", pd.Series(dtype=str)).value_counts().items()},
    }
    if "b_m2_kg" in frame:
        out["b_m2_kg"] = {
            "median": round(float(frame["b_m2_kg"].median()), 4),
            "max": round(float(frame["b_m2_kg"].max()), 4),
        }
    if "altitude_at_tca_km" in frame:
        out["altitude_km"] = {
            "min": round(float(frame["altitude_at_tca_km"].min()), 1),
            "median": round(float(frame["altitude_at_tca_km"].median()), 1),
            "max": round(float(frame["altitude_at_tca_km"].max()), 1),
        }
    return out
