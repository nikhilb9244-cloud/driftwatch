"""The ballistic coefficient: how hard a given density pushes on a given object.

``B = C_D A / m`` in m^2/kg, the one number that turns a density into a deceleration. On a
near-circular orbit it sets the decay rate directly:

    da/dt = -B rho sqrt(mu a)

on a circular orbit, and in general

    da/dt = -(B a^2 / mu) rho |v_rel| (v_rel . v)

which is what is actually fitted here, because an eccentric orbit does its drag at perigee
where both the density and the speed are highest, and ``v_rel`` is the velocity relative to a
co-rotating atmosphere. This is the whole of Step 3's storm term once the density is known. A
compact dense body sits near 0.002 m^2/kg, a spent upper stage near 0.01, a Starlink with its
panel edge-on around 0.01 to 0.02, and a light fragment or a deployed sail reaches a few
tenths.

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

**And when it is refused outright.** A fit assumes the intervals around an excluded burn are
free flight. An object that is manoeuvring in more than
:data:`driftwatch.config.BALLISTIC_MAX_MANOEUVRE_FRACTION` of its intervals is under continuous
control, and a continuous low thrust is a *ramp* rather than a jump, which a jump detector
cannot see and a drag fit therefore reads as atmosphere. The Starlinks being deorbited are the
case: 48 km of decay in 45 days at 400 km, which inverts to B near 1 m^2/kg, an area-to-mass a
satellite does not have. The rule is on the exclusions rather than on the coefficient because
the genuinely high coefficients -- the debris fragments at 0.5 to 0.8, thin plate and
insulation from the big fragmentation clouds -- have no exclusions at all and have to survive.
It is a proxy and it is set from the measured break in the population; ``config`` carries the
measurement and names the case it still lets through.

**When a fit is accepted.** Not on a fixed decay threshold, which cannot know whether fifty
metres is a measurement or a wobble, but on the object's own element-set scatter. Excluding
the manoeuvre intervals leaves contiguous *runs* of element sets; a quadratic is fitted
through the mean semi-major axis inside each run and the pooled root-mean-square residual is
the scatter -- what one element set disagrees with its neighbours by, for this object, over
this window. Inside each run and never across the gap between two, because a run ends where a
burn was excluded and a curve fitted across the exclusion reads the burn itself as noise.
The decay estimator telescopes to endpoint differences within a run, so its own uncertainty is
``scatter * sqrt(2 * runs)``, and the fit is accepted only when the measured decay exceeds
that by :data:`driftwatch.config.BALLISTIC_MIN_DECAY_SNR`. Quiet elements earn a fit from a
smaller decay than noisy ones, which is the right way round and is not something a constant in
metres can express.

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
of the coefficients this run actually fitted, **for its own category and drag altitude band**.
Sentinel-1A is the case that forced this: at 693 km its decay over 45 days is 24 m, inside the
element-set scatter, and its B* implies 3.3 m^2/kg, which is not a satellite. The alternative
was B = 0, which asserts that a storm does nothing to it -- nearly true at 800 km, plainly
false at 500, and the wrong kind of wrong for a risk model. The label says it is a stand-in.

The bands are :data:`driftwatch.config.BALLISTIC_ALTITUDE_BAND_EDGES_KM` and they are drag
bands, not the screener's: what one object's coefficient has in common with another's is the
regime the decay was measured in, and between 400 and 800 km the density falls by three orders
of magnitude. ``leo`` is one band to the screener and six here.

**Every coefficient carries an uncertainty**, so the Step 3 variance term has something to
propagate. For a fitted one it is the statistical uncertainty of its own decay measurement,
``sigma_B / B = 1 / snr``, floored at :data:`driftwatch.config.BALLISTIC_SIGMA_REL_FLOOR`.
It is deliberately *not* the density model's uncertainty: that is a separate term in Step 3,
and it partly cancels there (below) in a way that adding it here would double-count. A B*
inversion and a typical stand-in have no repeat measurement to take a scatter from and carry
priors instead, stated in ``config`` and labelled by ``source``.

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
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sgp4.api import SatrecArray

from driftwatch import config
from driftwatch.drag import density as dn
from driftwatch.drag.store import CoefficientStore
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
    "alt_band",
    "b_m2_kg",
    "b_sigma_m2_kg",
    "source",
    "n_sets",
    "span_days",
    "clean_span_days",
    "decay_m",
    "scatter_m",
    "decay_sigma_m",
    "decay_snr",
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
    source: str  # 'history', 'bstar', 'typical' or 'none'
    b_sigma_m2_kg: float = float("nan")
    n_sets: int = 0
    span_days: float = 0.0
    clean_span_days: float = 0.0
    decay_m: float = 0.0
    scatter_m: float = float("nan")
    decay_sigma_m: float = float("nan")
    decay_snr: float = float("nan")
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


def density_from_decay(decay_m: float, unit_integral: float, a_m: float, b_m2_kg: float) -> float:
    """The mean density a measured decay implies, given B: the same relation solved the other way.

    ``unit_integral`` is ``integral(|v_rel| (v_rel . v) dt)`` over the span -- the drag
    integral with the density taken out, which is pure geometry. Step 3 uses this to ask what
    density an element set's own drag term is effectively assuming, so that a scenario's
    density can be differenced against it.
    """
    if not (np.isfinite(decay_m) and np.isfinite(unit_integral) and np.isfinite(a_m) and np.isfinite(b_m2_kg)):
        return float("nan")
    if unit_integral <= 0 or a_m <= 0 or b_m2_kg <= 0:
        return float("nan")
    return float(decay_m * MU_M3_S2 / (b_m2_kg * a_m**2 * unit_integral))


def _plausible(b: float) -> bool:
    return bool(np.isfinite(b) and config.BALLISTIC_MIN_M2_KG <= b <= config.BALLISTIC_MAX_M2_KG)


def perigee_altitude_km(mean_motion: float, eccentricity: float) -> float:
    """Perigee altitude from the mean motion and eccentricity of an element set, in km."""
    n_rad_s = 2.0 * np.pi * float(mean_motion) / DAY_S
    if not np.isfinite(n_rad_s) or n_rad_s <= 0:
        return float("nan")
    a_km = (MU_M3_S2 / n_rad_s**2) ** (1.0 / 3.0) / 1000.0
    return float(a_km * (1.0 - max(float(eccentricity), 0.0)) - dn.EARTH_RADIUS_KM)


def altitude_band(perigee_km: float) -> str:
    """The drag altitude band a perigee falls in, as a label like ``450-550``.

    Not the screener's band. Two objects share a band here if their decay was measured in
    something like the same density, which is what makes one object's coefficient worth
    standing in for another's; the screener's ``leo`` spans three orders of magnitude in
    density and tells you nothing of the kind.
    """
    if not np.isfinite(perigee_km):
        return "unknown"
    edges = config.BALLISTIC_ALTITUDE_BAND_EDGES_KM
    if perigee_km < edges[0]:
        return f"<{edges[0]:g}"
    for lo, hi in zip(edges[:-1], edges[1:], strict=False):
        if lo <= perigee_km < hi:
            return f"{lo:g}-{hi:g}"
    return f">{edges[-1]:g}"


def band_for_row(row: pd.Series) -> str:
    """The drag altitude band of one element set."""
    return altitude_band(perigee_altitude_km(float(row["mean_motion"]), float(row.get("eccentricity", 0.0))))


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


def runs_of_sets(keep: np.ndarray) -> list[tuple[int, int]]:
    """The contiguous runs of element sets the kept intervals join up, as half-open ``[start, stop)``.

    The total-decay estimator sums ``a[k] - a[k+1]`` over kept intervals, which telescopes
    within a run to the difference of its two endpoints. So the number of independent
    element-set errors entering the total is twice the number of runs, not twice the number
    of intervals -- a distinction worth several sigma on an object with clean history -- and
    the scatter has to be measured inside a run rather than across the gap between two.
    """
    if not len(keep) or not keep.any():
        return []
    edges = np.diff(np.concatenate([[False], keep, [False]]).astype(np.int8))
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1)
    return [(int(a), int(b) + 1) for a, b in zip(starts, stops, strict=True)]


def element_set_scatter_m(seconds: np.ndarray, a_m: np.ndarray, runs: list[tuple[int, int]]) -> float:
    """How much one element set's mean semi-major axis disagrees with its neighbours', in metres.

    The pooled root-mean-square residual of a low-order polynomial fitted **inside each run**
    of element sets, never across the gap between two. That distinction is the whole of it: a
    run ends where a manoeuvre was excluded, and a curve fitted across the exclusion would
    read the burn itself -- kilometres of it -- as element-set noise and refuse a fit that the
    exclusion had just made possible.

    A quadratic rather than a line, because a decaying orbit's semi-major axis is curved over
    six weeks and a line's residual would count the curvature as noise; nothing higher,
    because three parameters is already most of what a short run can support without fitting
    the noise itself. Runs too short for a residual are dropped, and a linear fit is tried
    across the ``>= 3`` runs only if no run is long enough for a quadratic. Returns NaN when
    nothing can be measured at all.
    """
    for degree in (2, 1):
        squares = 0.0
        dof = 0
        for start, stop in runs:
            index = np.arange(start, stop)
            ok = index[np.isfinite(a_m[index]) & np.isfinite(seconds[index])]
            if len(ok) < degree + 2:  # a curve through its own number of points has no residual
                continue
            t = seconds[ok]
            t = (t - t.mean()) / max(t.std(), 1.0)  # conditioning; the residual is unaffected
            residual = a_m[ok] - np.polyval(np.polyfit(t, a_m[ok], degree), t)
            squares += float(np.sum(residual**2))
            dof += len(ok) - degree - 1
        if dof > 0:
            return float(np.sqrt(squares / dof))
    return float("nan")


def fit_from_history(
    sets: pd.DataFrame,
    table: pd.DataFrame | dn.WeatherGrid,
    *,
    step_s: float | None = None,
    step_scale: float = 1.0,
    max_interval_days: float = 14.0,
) -> Coefficient:
    """Fit B from one object's element sets, excluding manoeuvres. See the module docstring."""
    sets = sets.sort_values("epoch").drop_duplicates("epoch", keep="last").reset_index(drop=True)
    norad_id = int(sets["norad_id"].iloc[0]) if len(sets) else -1
    if len(sets) < config.BALLISTIC_MIN_SETS:
        return Coefficient(norad_id, float("nan"), "none", n_sets=len(sets), note="too few element sets")

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
            n_sets=len(sets),
            span_days=span_days,
            n_manoeuvre_excluded=n_excluded,
            note="no clean interval",
        )

    if step_s is None:
        row0 = sets.iloc[0]
        step_s = dn.sample_step_s(float(row0["mean_motion"]), float(row0.get("eccentricity", 0.0))) * step_scale

    total_decay = 0.0
    total_integral = 0.0
    rho_weighted = 0.0
    seconds = 0.0
    for k in np.nonzero(keep)[0]:
        row = sets.iloc[k]
        t0 = epochs.iloc[k].to_pydatetime()
        t1 = epochs.iloc[k + 1].to_pydatetime()
        track = dn.density_along_orbit(row, table, t0, t1, step_s=step_s)
        integral = dn.drag_integral(track)
        if not np.isfinite(integral["integral"]) or integral["integral"] <= 0:
            keep[k] = False
            continue
        a_mid = 0.5 * (a_m[k] + a_m[k + 1])
        total_decay += float(a_m[k] - a_m[k + 1])
        # Each interval contributes its own (a^2 integral); summing them and dividing the
        # summed decay by the sum is the total-decay estimator with each interval weighted
        # by how much drag it actually carried.
        total_integral += a_mid**2 * integral["integral"]
        rho_weighted += integral["rho_mean"] * float(dt_s[k])
        seconds += float(dt_s[k])

    rho_mean = rho_weighted / seconds if seconds > 0 else float("nan")
    elapsed = (epochs - epochs.iloc[0]).dt.total_seconds().to_numpy(dtype=float)
    set_runs = runs_of_sets(keep)
    scatter = element_set_scatter_m(elapsed, a_m, set_runs)
    runs = len(set_runs)
    decay_sigma = float(scatter * np.sqrt(2.0 * runs)) if np.isfinite(scatter) and runs else float("nan")
    with np.errstate(divide="ignore", invalid="ignore"):
        snr = float(total_decay / decay_sigma) if np.isfinite(decay_sigma) and decay_sigma > 0 else float("nan")
    clean_span_days = seconds / DAY_S

    def refused(note: str) -> Coefficient:
        return Coefficient(
            norad_id,
            float("nan"),
            "none",
            n_sets=len(sets),
            span_days=span_days,
            clean_span_days=clean_span_days,
            decay_m=total_decay,
            scatter_m=scatter,
            decay_sigma_m=decay_sigma,
            decay_snr=snr,
            rho_mean_kg_m3=rho_mean,
            n_intervals=int(keep.sum()),
            n_manoeuvre_excluded=n_excluded,
            note=note,
        )

    if total_integral <= 0:
        return refused("no usable density over the window")
    b = total_decay * MU_M3_S2 / total_integral
    if clean_span_days < config.BALLISTIC_MIN_SPAN_DAYS:
        return refused(f"clean span {clean_span_days:.1f} d is under the {config.BALLISTIC_MIN_SPAN_DAYS:g} d minimum")
    if abs(total_decay) < config.BALLISTIC_MIN_DECAY_M:
        return refused(f"decay {total_decay:.0f} m is under the {config.BALLISTIC_MIN_DECAY_M:g} m floor")
    if not np.isfinite(snr):
        return refused("the element-set scatter cannot be measured over the clean intervals")
    excluded_fraction = n_excluded / max(len(sets) - 1, 1)
    if excluded_fraction > config.BALLISTIC_MAX_MANOEUVRE_FRACTION:
        return refused(
            f"{excluded_fraction:.0%} of the intervals are manoeuvres, over the "
            f"{config.BALLISTIC_MAX_MANOEUVRE_FRACTION:.0%} allowed; this object is under continuous "
            "control and its decay is not drag"
        )
    if snr < config.BALLISTIC_MIN_DECAY_SNR:
        return refused(
            f"decay {total_decay:.0f} m is {snr:.1f} times its own uncertainty "
            f"({decay_sigma:.0f} m from a scatter of {scatter:.0f} m), under the "
            f"{config.BALLISTIC_MIN_DECAY_SNR:g} required"
        )
    if not _plausible(b):
        return refused(f"fitted B {b:.3g} m^2/kg is outside the plausible range")

    sigma = abs(b) * max(1.0 / snr, config.BALLISTIC_SIGMA_REL_FLOOR)
    return Coefficient(
        norad_id,
        b,
        "history",
        b_sigma_m2_kg=sigma,
        n_sets=len(sets),
        span_days=span_days,
        clean_span_days=clean_span_days,
        decay_m=total_decay,
        scatter_m=scatter,
        decay_sigma_m=decay_sigma,
        decay_snr=snr,
        rho_mean_kg_m3=rho_mean,
        n_intervals=int(keep.sum()),
        n_manoeuvre_excluded=n_excluded,
        note=f"{runs} clean run{'s' if runs != 1 else ''} of element sets",
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
    table: pd.DataFrame | dn.WeatherGrid,
    *,
    days: float | None = None,
    step_s: float | None = None,
    step_scale: float = 1.0,
) -> Coefficient:
    """The physical B implied by the decay this element set's own B* produces.

    No conversion constant: propagate with SGP4, measure the orbit-averaged drop, and invert
    it through the same density model everything else uses. See the module docstring for why
    the textbook constant is quoted and not used.

    ``step_scale`` coarsens the sampling the same way the history fit's does and for the same
    reason: what is wanted is the ten-day *integral* of the density, and the local-time swing
    the fine step resolves is averaged out of it within the first orbit. This is not a detail
    of taste -- when the fit budget stops the history fits, every remaining object of a run
    comes through here, and at the full step that is the slowest thing in the command.
    """
    days = config.BSTAR_DECAY_DAYS if days is None else days
    norad_id = int(element_row["norad_id"])
    t0 = pd.Timestamp(element_row["epoch"]).to_pydatetime()
    t1 = t0 + timedelta(days=days)
    if step_s is None and step_scale != 1.0:
        step_s = dn.sample_step_s(float(element_row["mean_motion"]), float(element_row.get("eccentricity", 0.0)))
        step_s *= step_scale
    decay, a_mean = bstar_decay_m(element_row, days)
    track = dn.density_along_orbit(element_row, table, t0, t1, step_s=step_s)
    integral = dn.drag_integral(track)
    rho = integral["rho_mean"]
    b = coefficient_from_decay(decay, integral["integral"], a_mean)
    if not _plausible(b):
        note = "B* implies no decay" if np.isfinite(b) and b <= 0 else f"B* implies B {b:.3g} m^2/kg"
        return Coefficient(
            norad_id,
            float("nan"),
            "none",
            n_sets=1,
            span_days=days,
            decay_m=decay,
            rho_mean_kg_m3=rho,
            n_intervals=1,
            note=note,
        )
    return Coefficient(
        norad_id,
        b,
        "bstar",
        b_sigma_m2_kg=abs(b) * config.BALLISTIC_SIGMA_REL_BSTAR,
        n_sets=1,
        span_days=days,
        decay_m=decay,
        rho_mean_kg_m3=rho,
        n_intervals=1,
        note="from the element set's own drag term",
    )


def typical_coefficient(fitted: pd.DataFrame, category: str, band: str) -> tuple[float, float, str]:
    """``(B, sigma_B, why)``: a stand-in for an object whose decay says nothing and whose B* is not physical.

    The median of the coefficients actually fitted in this run, narrowed as far as the
    population allows: category and drag altitude band first, then category, then everything
    fitted. It is a **measured** typical value rather than a textbook one, and it is labelled
    ``typical`` in every output so that nothing built on it can be mistaken for a measurement
    of that object.

    Its uncertainty is the spread of the pool it came from -- ``1.4826 * MAD``, the robust
    equivalent of a standard deviation -- floored at
    :data:`driftwatch.config.BALLISTIC_SIGMA_REL_TYPICAL` of the value, because a population
    median is not a measurement of this object however tight the population is.

    Without any of this these objects would carry B = 0, which says a storm does nothing to
    them. That is nearly true at 800 km and plainly false at 500, and it is the wrong kind of
    wrong: a silent zero in a risk model.
    """
    good = fitted[(fitted["source"] == "history") & fitted["b_m2_kg"].notna()] if len(fitted) else fitted

    def spread(pool: pd.DataFrame, value: float) -> float:
        values = pool["b_m2_kg"].to_numpy(dtype=float)
        mad = float(np.median(np.abs(values - value))) if len(values) else float("nan")
        robust = 1.4826 * mad if np.isfinite(mad) else 0.0
        return float(max(robust, config.BALLISTIC_SIGMA_REL_TYPICAL * abs(value)))

    if len(good) and {"category", "alt_band"} <= set(good.columns):
        here = good[(good["category"] == category) & (good["alt_band"] == band)]
        if len(here) >= config.BALLISTIC_TYPICAL_MIN_OBJECTS:
            value = float(here["b_m2_kg"].median())
            return value, spread(here, value), f"median of {len(here)} fitted {category} objects at {band} km"
    if len(good) and "category" in good.columns:
        same = good[good["category"] == category]
        if len(same) >= config.BALLISTIC_TYPICAL_MIN_OBJECTS:
            value = float(same["b_m2_kg"].median())
            return value, spread(same, value), f"median of {len(same)} fitted {category} objects at any altitude"
    if len(good) >= config.BALLISTIC_TYPICAL_MIN_OBJECTS:
        value = float(good["b_m2_kg"].median())
        return value, spread(good, value), f"median of {len(good)} fitted objects in this run"
    value = float(config.BALLISTIC_TYPICAL_M2_KG)
    return value, config.BALLISTIC_SIGMA_REL_TYPICAL * value, "the configured typical value; this run fitted too few"


# --------------------------------------------------------------------------------------
# All three, for a set of objects


@dataclass
class FitBudget:
    """A wall-clock allowance for the history fits, and what it managed to cover.

    The fit is the expensive half of Step 2 -- about a hundred NRLMSIS evaluations an object
    -- and the run's object list is in descending order of probability, so spending the
    allowance from the top and falling back for the rest buys the accuracy where it changes
    an answer. Everything the budget does not reach is labelled ``bstar`` or ``typical`` like
    any other fallback, so nothing downstream has to know the budget existed.
    """

    seconds: float
    started_at: float = 0.0
    n_fitted: int = 0
    n_cached: int = 0
    n_skipped: int = 0

    def start(self) -> FitBudget:
        self.started_at = time.perf_counter()
        return self

    @property
    def elapsed_s(self) -> float:
        return time.perf_counter() - self.started_at if self.started_at else 0.0

    @property
    def exhausted(self) -> bool:
        return self.seconds > 0 and self.elapsed_s >= self.seconds

    def as_dict(self) -> dict[str, Any]:
        return {
            "budget_s": self.seconds,
            "elapsed_s": round(self.elapsed_s, 1),
            "n_fitted": self.n_fitted,
            "n_from_cache": self.n_cached,
            "n_over_budget": self.n_skipped,
        }


def coefficients(
    elements: pd.DataFrame,
    table: pd.DataFrame | dn.WeatherGrid,
    history: pd.DataFrame | None = None,
    *,
    step_s: float | None = None,
    fit_days: float | None = None,
    budget_s: float | None = None,
    store: CoefficientStore | None = None,
    step_scale: float | None = None,
    now: datetime | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    """A coefficient per object: fitted from history where it can be, from B* or a median where it cannot.

    ``elements`` is one row per object **in the order they should be fitted** -- the caller
    ranks them, and ``driftwatch ballistic`` ranks them by probability. ``history`` is every
    element set available for them, from ``catalogue/history.py``. The label says which route
    each took and the diagnostics say why.
    """
    fit_days = config.BALLISTIC_FIT_DAYS if fit_days is None else fit_days
    step_scale = config.BALLISTIC_FIT_STEP_SCALE if step_scale is None else step_scale
    now = now or datetime.now(UTC)
    budget = FitBudget(config.BALLISTIC_FIT_BUDGET_S if budget_s is None else budget_s).start()
    # One conversion of the weather table for the whole run rather than one per interval.
    grid = dn.weather_grid(table)

    by_id: dict[int, pd.DataFrame] = {}
    if history is not None and len(history):
        cutoff = pd.to_datetime(elements["epoch"], utc=True).max() - pd.Timedelta(days=fit_days)
        recent = history[pd.to_datetime(history["epoch"], utc=True) >= cutoff]
        by_id = {int(k): v for k, v in recent.groupby("norad_id")}

    rows: list[dict[str, Any]] = []
    meta: list[tuple[str, str]] = []
    total = len(elements)
    for position, (_, row) in enumerate(elements.iterrows()):
        norad_id = int(row["norad_id"])
        category = str(row.get("category", "unknown"))
        band = band_for_row(row)
        sets = by_id.get(norad_id)
        history_end = pd.to_datetime(sets["epoch"], utc=True).max() if sets is not None and len(sets) else None
        history_start = pd.to_datetime(sets["epoch"], utc=True).min() if sets is not None and len(sets) else None

        fitted: Coefficient | None = None
        over_budget = False
        cached = store.usable(norad_id, history_end=history_end, now=now) if store is not None else None
        if cached is not None:
            fitted = Coefficient(**{k: v for k, v in cached.items() if k in Coefficient.__dataclass_fields__})
            budget.n_cached += 1
        elif sets is not None and len(sets) >= config.BALLISTIC_MIN_SETS:
            if budget.exhausted:
                over_budget = True
                budget.n_skipped += 1
            else:
                fitted = fit_from_history(sets, grid, step_s=step_s, step_scale=step_scale)
                budget.n_fitted += 1
                if store is not None:
                    store.put(fitted.as_row(), history_start=history_start, history_end=history_end, now=now)

        if fitted is not None and fitted.source == "history":
            rows.append(fitted.as_row())
        else:
            fallback = from_bstar(row, grid, step_s=step_s, step_scale=step_scale)
            extra = f"history: {fitted.note}" if fitted is not None and fitted.note else ""
            if over_budget:
                extra = "the history fit did not fit inside the run's budget"
            if extra:
                fallback = Coefficient(**{**fallback.as_row(), "note": f"{fallback.note}; {extra}".lstrip("; ")})
            rows.append(fallback.as_row())
        meta.append((category, band))
        if progress is not None and (position % 100 == 99 or position == total - 1):
            progress(position + 1, total)

    out = pd.DataFrame(rows)
    if not len(out):
        return pd.DataFrame(columns=list(COEFFICIENT_COLUMNS))
    out["norad_id"] = out["norad_id"].astype("int64")
    out["category"] = pd.Series([c for c, _ in meta], index=out.index, dtype="string")
    out["alt_band"] = pd.Series([b for _, b in meta], index=out.index, dtype="string")
    # Anything neither route could answer takes the run's own typical value, labelled.
    unresolved = out["source"] == "none"
    if unresolved.any():
        for idx in out.index[unresolved]:
            b_typical, sigma, why = typical_coefficient(out, str(out.at[idx, "category"]), str(out.at[idx, "alt_band"]))
            out.at[idx, "b_m2_kg"] = b_typical
            out.at[idx, "b_sigma_m2_kg"] = sigma
            out.at[idx, "source"] = "typical"
            out.at[idx, "note"] = f"{out.at[idx, 'note']}; stood in with {why}".lstrip("; ")
    out.attrs["budget"] = budget.as_dict()
    return out[list(COEFFICIENT_COLUMNS)]


def summary(frame: pd.DataFrame) -> dict[str, Any]:
    """What a set of coefficients looks like, for the log and the run record."""
    if not len(frame):
        return {"n": 0}
    good = frame[frame["b_m2_kg"].notna()]
    fits = frame[frame["source"] == "history"]
    with np.errstate(divide="ignore", invalid="ignore"):
        relative = (good["b_sigma_m2_kg"] / good["b_m2_kg"].abs()).replace([np.inf, -np.inf], np.nan)
    out: dict[str, Any] = {
        "n": int(len(frame)),
        "by_source": {str(k): int(v) for k, v in frame["source"].value_counts().items()},
        "b_m2_kg": {
            "median": round(float(good["b_m2_kg"].median()), 6) if len(good) else None,
            "p10": round(float(good["b_m2_kg"].quantile(0.1)), 6) if len(good) else None,
            "p90": round(float(good["b_m2_kg"].quantile(0.9)), 6) if len(good) else None,
        },
        "relative_sigma": {
            "median": round(float(relative.median()), 3) if relative.notna().any() else None,
            "p90": round(float(relative.quantile(0.9)), 3) if relative.notna().any() else None,
        },
        "n_manoeuvre_excluded": int(frame["n_manoeuvre_excluded"].sum()),
    }
    if len(fits) and fits["decay_snr"].notna().any():
        out["decay_snr"] = {
            "median": round(float(fits["decay_snr"].median()), 1),
            "min": round(float(fits["decay_snr"].min()), 1),
        }
    if "budget" in frame.attrs:
        out["budget"] = frame.attrs["budget"]
    return out
