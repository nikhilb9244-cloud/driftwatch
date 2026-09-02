"""The ballistic coefficient: how hard a given density pushes on a given object.

``B = C_D A / m`` in m^2/kg, the one number that turns a density into a deceleration. On a
near-circular orbit it sets the decay rate directly:

    da/dt = -B rho sqrt(mu a)

on a circular orbit, and in general

    da/dt = -(B a^2 / mu) rho |v_rel| (v_rel . v)

which is what is actually fitted here, because an eccentric orbit does its drag at perigee
where both the density and the speed are highest, and ``v_rel`` is the velocity relative to a
co-rotating atmosphere. This is the whole of Step 3's storm term once the density is known. A
compact dense body
sits near 0.002 m^2/kg, a spent upper stage near 0.01, a Starlink with its panel edge-on
around 0.01 to 0.02, and a light fragment or a deployed sail reaches a few tenths.

**Three sources, and they are not equally good.** The label ``source`` on every row says
which was used, and it is carried through to Step 3.

*Fitted from the object's own decay* (``source='history'``). Take the element sets over the
last :data:`driftwatch.config.BALLISTIC_FIT_DAYS` days, read the mean semi-major axis off
each, and ask what B makes NRLMSIS reproduce the drop that actually happened:

    B = -mu sum(da_i) / sum(a_i^2 integral_i(rho |v_rel| (v_rel . v) dt))

summed over the intervals that survive, which is a total-decay estimator: element-set noise
averages out over the window instead of being fitted interval by interval.

Three things are excluded rather than fitted around. **Manoeuvre intervals**, found by the
same detector the covariance fit uses (``risk/manoeuvre.py``): a station-keeping burn raises
the orbit and would come back as a negative drag. **Outlier element sets**, likewise. And
**intervals longer than a fortnight**, where a burn could hide inside a net decay. What is
left is fitted over windows that carry the **observed** ap of those days, so the storm days
in the window are modelled as storms rather than averaged into a quiet mean.

*From the element set's own B\\** (``source='bstar'``). B* is not a physical ballistic
coefficient: it is a fit parameter for SGP4's own atmosphere model, and it absorbs whatever
the fit could not otherwise explain. It is routinely negative -- STARLINK-6053 carried
-2.98e-5 on 2026-09-02, which as a physical coefficient would mean an object that
accelerates as it flies through air. The textbook conversion ``B = 2 B*/rho0`` with
``rho0 = 2.461e-5`` kg/m^2/ER is quoted in ``config`` and **not used**: measured against the
decay SGP4 itself produces it is wrong by three orders of magnitude, and the factor is not
even constant -- two objects 45 km apart in altitude imply reference densities differing
sevenfold. So the fallback asks the self-consistent question instead: propagate the element
set with its own B* for :data:`driftwatch.config.BSTAR_DECAY_DAYS` days, measure the
orbit-averaged decay SGP4 produces, and invert that through NRLMSIS. Altitude-aware, no
magic constant, and it inherits exactly as much noise as B* has -- which is the point of the
label.

*The run's own typical value* (``source='typical'``). Where neither works -- no usable
history and a B* that implies no decay or an implausible one -- the object takes the median
of the coefficients this run actually fitted, for its own category where there are enough of
them. Sentinel-1A is the case that forced this: at 693 km its decay over 45 days is 24 m,
inside the element-set scatter, and its B* implies 3.3 m^2/kg, which is not a satellite. The
alternative was B = 0, which asserts that a storm does nothing to it -- nearly true at 800 km,
plainly false at 500, and the wrong kind of wrong for a risk model. The label says it is a
stand-in.

**The density model's bias folds into the fitted coefficient, and partly cancels.** If
NRLMSIS is systematically low by 20 per cent over the fit window, the fit returns a B that is
20 per cent high, because only the product ``B rho`` is observable from a decay. When the
same model then drives the scenarios, the product comes back right and the error cancels --
for the *quiet* case. It does not cancel for the storm response: a model that gets the quiet
density wrong by a constant factor and the storm *ratio* right will give the right answer,
but a model whose storm ratio is wrong is not corrected by anything here. This is why the
fitted coefficient is preferred over B* and why the same model must drive both the fit and
the scenarios.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from sgp4.api import SatrecArray

from driftwatch import config
from driftwatch.drag import density as dn
from driftwatch.orbit.propagator import WGS72_EARTH_RADIUS_KM, build_satrecs
from driftwatch.orbit.time import julian_date, julian_dates
from driftwatch.risk.manoeuvre import detect_jumps

log = logging.getLogger(__name__)

MU_M3_S2 = dn.MU_M3_S2
MU_KM3_S2 = 398600.4418
DAY_S = 86400.0

COEFFICIENT_COLUMNS: tuple[str, ...] = (
    "norad_id",
    "category",
    "b_m2_kg",
    "source",
    "n_sets",
    "span_days",
    "decay_m",
    "rho_mean_kg_m3",
    "n_intervals",
    "n_manoeuvre_excluded",
    "note",
)


@dataclass(frozen=True)
class Coefficient:
    """One object's ballistic coefficient and everything needed to distrust it."""

    norad_id: int
    b_m2_kg: float
    source: str  # 'history', 'bstar' or 'none'
    n_sets: int = 0
    span_days: float = 0.0
    decay_m: float = 0.0
    rho_mean_kg_m3: float = float("nan")
    n_intervals: int = 0
    n_manoeuvre_excluded: int = 0
    note: str = ""

    def as_row(self) -> dict[str, Any]:
        return asdict(self)


def coefficient_from_decay(decay_m: float, drag_integral: float, a_m: float) -> float:
    """Invert ``da = -(B a^2 / mu) * integral(rho |v_rel| (v_rel . v) dt)`` for B.

    ``decay_m`` is positive for a falling orbit and ``drag_integral`` comes from
    :func:`driftwatch.drag.density.drag_integral` over the same span. The general form, not
    the circular one: for an eccentric orbit the drag is concentrated at perigee and a mean
    density times ``sqrt(mu a)`` understates the integral badly. Returns NaN where the inputs
    cannot support an answer.
    """
    if not (np.isfinite(decay_m) and np.isfinite(drag_integral) and np.isfinite(a_m)):
        return float("nan")
    if drag_integral <= 0 or a_m <= 0:
        return float("nan")
    return float(decay_m * MU_M3_S2 / (a_m**2 * drag_integral))


def _plausible(b: float) -> bool:
    return bool(np.isfinite(b) and config.BALLISTIC_MIN_M2_KG <= b <= config.BALLISTIC_MAX_M2_KG)


# --------------------------------------------------------------------------------------
# Fitted from the object's own decay


def _osculating_a_km(r: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Osculating semi-major axis (km) from a state, for the manoeuvre detector's inputs."""
    rn = np.linalg.norm(r, axis=-1)
    vn = np.linalg.norm(v, axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 1.0 / (2.0 / rn - vn**2 / MU_KM3_S2)


def manoeuvre_intervals(sets: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """``(jump, bad_set)`` for consecutive intervals of one object's element sets.

    The same detector and the same three propagations the covariance fit uses, so a burn
    excluded there is excluded here. A fit over an interval containing a station-keeping
    burn would read the raise as negative drag and return a nonsense coefficient.
    """
    n = len(sets)
    if n < 2:
        return np.zeros(0, dtype=bool), np.zeros(n, dtype=bool)
    t64 = pd.to_datetime(sets["epoch"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    jd, fr = julian_dates(t64)
    err, r, v = SatrecArray(build_satrecs(sets)).sgp4(jd, fr)
    err0, r0, v0 = SatrecArray(build_satrecs(sets.assign(bstar=0.0))).sgp4(jd[1:], fr[1:])
    k = np.arange(n - 1)
    a_fit = _osculating_a_km(r[k + 1, k + 1], v[k + 1, k + 1])
    a_prop = _osculating_a_km(r[k, k + 1], v[k, k + 1])
    a_free = _osculating_a_km(r0[k, k], v0[k, k])
    good = (err[k + 1, k + 1] == 0) & (err[k, k + 1] == 0) & (err0[k, k] == 0)
    a_fit = np.where(good, a_fit, np.nan)
    dt_days = (t64[1:] - t64[:-1]) / np.timedelta64(86_400_000_000, "us")
    return detect_jumps(a_fit, a_prop, a_free, dt_days)


def fit_from_history(
    sets: pd.DataFrame,
    table: pd.DataFrame,
    *,
    step_s: float | None = None,
    max_interval_days: float = 14.0,
) -> Coefficient:
    """Fit B from one object's element sets, excluding manoeuvres. See the module docstring."""
    sets = sets.sort_values("epoch").drop_duplicates("epoch", keep="last").reset_index(drop=True)
    norad_id = int(sets["norad_id"].iloc[0]) if len(sets) else -1
    if len(sets) < config.BALLISTIC_MIN_SETS:
        return Coefficient(norad_id, float("nan"), "none", len(sets), note="too few element sets")

    epochs = pd.to_datetime(sets["epoch"], utc=True)
    span_days = float((epochs.iloc[-1] - epochs.iloc[0]).total_seconds() / DAY_S)
    a_m = mean_sma_m(sets)
    jump, bad_set = manoeuvre_intervals(sets)
    dt_s = np.diff(epochs.to_numpy(dtype="datetime64[s]")).astype(float)

    keep = (~jump) & (~bad_set[:-1]) & (~bad_set[1:]) & (dt_s > 0) & (dt_s <= max_interval_days * DAY_S)
    keep &= np.isfinite(a_m[:-1]) & np.isfinite(a_m[1:])
    n_excluded = int(jump.sum())
    if not keep.any():
        return Coefficient(
            norad_id,
            float("nan"),
            "none",
            len(sets),
            span_days,
            n_manoeuvre_excluded=n_excluded,
            note="no clean interval",
        )

    total_decay = 0.0
    total_integral = 0.0
    rho_weighted = 0.0
    seconds = 0.0
    a_weighted = 0.0
    for k in np.nonzero(keep)[0]:
        row = sets.iloc[k]
        t0 = epochs.iloc[k].to_pydatetime()
        t1 = epochs.iloc[k + 1].to_pydatetime()
        track = dn.density_along_orbit(row, table, t0, t1, step_s=step_s)
        integral = dn.drag_integral(track)
        if not np.isfinite(integral["integral"]) or integral["integral"] <= 0:
            continue
        a_mid = 0.5 * (a_m[k] + a_m[k + 1])
        total_decay += float(a_m[k] - a_m[k + 1])
        # Each interval contributes its own (a^2 integral); summing them and dividing the
        # summed decay by the sum is the total-decay estimator with each interval weighted
        # by how much drag it actually carried.
        total_integral += a_mid**2 * integral["integral"]
        rho_weighted += integral["rho_mean"] * float(dt_s[k])
        a_weighted += a_mid * float(dt_s[k])
        seconds += float(dt_s[k])

    rho_mean = rho_weighted / seconds if seconds > 0 else float("nan")
    if total_integral <= 0:
        return Coefficient(
            norad_id,
            float("nan"),
            "none",
            len(sets),
            span_days,
            total_decay,
            rho_mean,
            int(keep.sum()),
            n_excluded,
            "no usable density over the window",
        )
    b = total_decay * MU_M3_S2 / total_integral
    note = ""
    source = "history"
    if seconds < config.BALLISTIC_MIN_SPAN_DAYS * DAY_S:
        source, note = "none", f"clean span {seconds / DAY_S:.1f} d is under the minimum"
    elif abs(total_decay) < config.BALLISTIC_MIN_DECAY_M:
        source, note = "none", f"decay {total_decay:.0f} m is inside the element-set scatter"
    elif not _plausible(b):
        source, note = "none", f"fitted B {b:.3g} m^2/kg is outside the plausible range"
    return Coefficient(
        norad_id,
        b if source == "history" else float("nan"),
        source,
        len(sets),
        span_days,
        total_decay,
        rho_mean,
        int(keep.sum()),
        n_excluded,
        note,
    )


# --------------------------------------------------------------------------------------
# From the element set's own B*


def mean_sma_m(sets: pd.DataFrame) -> np.ndarray:
    """Brouwer mean semi-major axis in metres, one per element set, from SGP4's own initialisation.

    The mean element, not an osculating one. An instantaneous semi-major axis carries a
    short-period oscillation of kilometres at low Earth orbit and a long-period one that over
    ten days looks exactly like a trend, either of which swamps the tens or hundreds of metres
    a week of drag actually removes. SGP4 recovers the mean value when it initialises a
    record, and reports it at any propagation time as ``satrec.am``, so both routes here read
    the same quantity and their difference is drag and nothing else.
    """
    if not len(sets):
        return np.zeros(0)
    return np.array([sat.a for sat in build_satrecs(sets)]) * WGS72_EARTH_RADIUS_KM * 1000.0


def bstar_decay_m(element_row: pd.Series, days: float) -> tuple[float, float]:
    """``(drop in mean semi-major axis over ``days``, mean semi-major axis)``, both in metres.

    What SGP4 itself does with this element set's own drag term, read off its mean elements
    at the two ends. On 2026-09-02 that is 26 m a day for the ISS, 1.1 m for Sentinel-1A at
    691 km and 0.5 m for NOAA-20 at 824 km, which are the right sizes; a negative B* gives a
    negative decay, which is the honest signal that the term is not physical for that object.
    """
    satrec = build_satrecs(element_row.to_frame().T)[0]
    t0 = pd.Timestamp(element_row["epoch"]).to_pydatetime()
    values = []
    for offset in (0.0, days):
        jd, fr = julian_date(t0 + timedelta(days=float(offset)))
        error, _, _ = satrec.sgp4(jd, fr)
        values.append(satrec.am * WGS72_EARTH_RADIUS_KM * 1000.0 if error == 0 else np.nan)
    if not np.isfinite(values).all():
        return float("nan"), float("nan")
    return float(values[0] - values[1]), float(np.mean(values))


def from_bstar(
    element_row: pd.Series,
    table: pd.DataFrame,
    *,
    days: float | None = None,
    step_s: float | None = None,
) -> Coefficient:
    """The physical B implied by the decay this element set's own B* produces.

    No conversion constant: propagate with SGP4, measure the orbit-averaged drop, and invert
    it through the same density model everything else uses. See the module docstring for why
    the textbook constant is quoted and not used.
    """
    days = config.BSTAR_DECAY_DAYS if days is None else days
    norad_id = int(element_row["norad_id"])
    t0 = pd.Timestamp(element_row["epoch"]).to_pydatetime()
    t1 = t0 + timedelta(days=days)
    decay, a_mean = bstar_decay_m(element_row, days)
    track = dn.density_along_orbit(element_row, table, t0, t1, step_s=step_s)
    integral = dn.drag_integral(track)
    rho = integral["rho_mean"]
    b = coefficient_from_decay(decay, integral["integral"], a_mean)
    if not _plausible(b):
        note = "B* implies no decay" if np.isfinite(b) and b <= 0 else f"B* implies B {b:.3g} m^2/kg"
        return Coefficient(norad_id, float("nan"), "none", 1, days, decay, rho, 1, 0, note)
    return Coefficient(norad_id, b, "bstar", 1, days, decay, rho, 1, 0, "from the element set's own drag term")


def typical_coefficient(fitted: pd.DataFrame, category: str) -> tuple[float, str]:
    """A stand-in B for an object whose own decay says nothing and whose B* is not physical.

    The median of the coefficients actually fitted in this run, for the same category where
    there are enough of them and across all of them otherwise. It is a **measured** typical
    value rather than a textbook one, and it is labelled ``typical`` in every output so that
    nothing built on it can be mistaken for a measurement of that object.

    Without it these objects would carry B = 0, which says a storm does nothing to them. That
    is nearly true at 800 km and plainly false at 500, and it is the wrong kind of wrong: a
    silent zero in a risk model. :data:`driftwatch.config.BALLISTIC_TYPICAL_M2_KG` stands in
    when a run has no fits at all to take a median from.
    """
    good = fitted[(fitted["source"] == "history") & fitted["b_m2_kg"].notna()] if len(fitted) else fitted
    if len(good) and "category" in good.columns:
        same = good[good["category"] == category]
        if len(same) >= config.BALLISTIC_TYPICAL_MIN_OBJECTS:
            return float(same["b_m2_kg"].median()), f"median of {len(same)} fitted {category} objects"
    if len(good) >= config.BALLISTIC_TYPICAL_MIN_OBJECTS:
        return float(good["b_m2_kg"].median()), f"median of {len(good)} fitted objects in this run"
    return float(config.BALLISTIC_TYPICAL_M2_KG), "the configured typical value; this run fitted too few objects"


# --------------------------------------------------------------------------------------
# Both, for a set of objects


def coefficients(
    elements: pd.DataFrame,
    table: pd.DataFrame,
    history: pd.DataFrame | None = None,
    *,
    step_s: float | None = None,
    fit_days: float | None = None,
) -> pd.DataFrame:
    """A coefficient per object: fitted from history where it can be, from B* where it cannot.

    ``elements`` is one row per object (a snapshot slice); ``history`` is every element set
    available for them, from ``catalogue/history.py``. The label says which route each took,
    and the diagnostics say why.
    """
    fit_days = config.BALLISTIC_FIT_DAYS if fit_days is None else fit_days
    rows: list[dict[str, Any]] = []
    by_id: dict[int, pd.DataFrame] = {}
    if history is not None and len(history):
        cutoff = pd.to_datetime(elements["epoch"], utc=True).max() - pd.Timedelta(days=fit_days)
        recent = history[pd.to_datetime(history["epoch"], utc=True) >= cutoff]
        by_id = {int(k): v for k, v in recent.groupby("norad_id")}

    categories = {int(r["norad_id"]): str(r.get("category", "unknown")) for _, r in elements.iterrows()}
    for _, row in elements.iterrows():
        norad_id = int(row["norad_id"])
        fitted = None
        sets = by_id.get(norad_id)
        if sets is not None and len(sets) >= config.BALLISTIC_MIN_SETS:
            fitted = fit_from_history(sets, table, step_s=step_s)
        if fitted is not None and fitted.source == "history":
            rows.append(fitted.as_row())
            continue
        fallback = from_bstar(row, table, step_s=step_s)
        if fitted is not None and fitted.note:
            fallback = Coefficient(**{**fallback.as_row(), "note": f"{fallback.note}; history rejected: {fitted.note}"})
        rows.append(fallback.as_row())

    out = pd.DataFrame(rows)
    if not len(out):
        return pd.DataFrame(columns=list(COEFFICIENT_COLUMNS))
    out["norad_id"] = out["norad_id"].astype("int64")
    out["category"] = out["norad_id"].map(categories).astype("string")
    # Anything neither route could answer takes the run's own typical value, labelled.
    unresolved = out["source"] == "none"
    if unresolved.any():
        for idx in out.index[unresolved]:
            b_typical, why = typical_coefficient(out, str(out.at[idx, "category"]))
            out.at[idx, "b_m2_kg"] = b_typical
            out.at[idx, "source"] = "typical"
            out.at[idx, "note"] = f"{out.at[idx, 'note']}; stood in with {why}".lstrip("; ")
    return out[list(COEFFICIENT_COLUMNS)]


def summary(frame: pd.DataFrame) -> dict[str, Any]:
    """What a set of coefficients looks like, for the log and the run record."""
    if not len(frame):
        return {"n": 0}
    good = frame[frame["source"] != "none"]
    return {
        "n": int(len(frame)),
        "by_source": {str(k): int(v) for k, v in frame["source"].value_counts().items()},
        "b_m2_kg": {
            "median": round(float(good["b_m2_kg"].median()), 6) if len(good) else None,
            "p10": round(float(good["b_m2_kg"].quantile(0.1)), 6) if len(good) else None,
            "p90": round(float(good["b_m2_kg"].quantile(0.9)), 6) if len(good) else None,
        },
        "n_manoeuvre_excluded": int(frame["n_manoeuvre_excluded"].sum()),
    }
