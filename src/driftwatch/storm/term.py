"""The in-track displacement an unmodelled density excess produces, and its uncertainty.

## The derivation

Drag removes energy, the orbit sinks, and a lower orbit is a *faster* one. That last step is
what makes a storm a screening problem rather than an altimetry one: the object does not
mostly move down, it moves **forward**, and it keeps moving further forward for as long as the
error is uncorrected.

For a near-circular orbit of semi-major axis ``a`` under a density ``rho``:

    da/dt = -B rho sqrt(mu a)                                                (1)

with ``B = C_D A / m``. The mean motion is ``n = sqrt(mu / a^3)``, so ``dn/da = -(3/2) n/a``
and

    dn/dt = -(3/2) (n/a) da/dt = (3/2) n B rho v,     v = sqrt(mu/a)          (2)

A *constant* excess ``drho`` over the density the element set already knows about therefore
adds a constant mean-motion drift, and the along-track angle it accumulates is the double
integral of it. Writing the angular displacement as the once-integrated drift,

    dtheta(t) = integral_0^t (t - tau) (dn/dt)(tau) dtau                      (3)

and multiplying by ``a`` to get a distance, with ``a n = v``:

    s(t) = (3/2) B v^2 integral_0^t (t - tau) drho(tau) dtau                  (4)

which for a constant excess collapses to the closed form the prompt asks for:

    **s(t) = (3/4) B drho v^2 t^2**                                           (5)

Quadratic in time, linear in the ballistic coefficient, linear in the density excess, and
quadratic in the orbital speed. :func:`in_track_shift_m` is (5); :func:`shift_from_profile` is
(4), which is what the scenarios actually use, because a storm is not a constant: an excess on
the first day of a seven-day window displaces the object far more than the same excess on the
last, and (5) applied to a window-mean excess cannot express that.

**The sign.** A positive excess means more drag than the element set assumed, so the object is
**ahead** of where its element set says it will be, in the +I (in-track) direction. This is
the one sign in the whole phase that is easy to get backwards -- "more drag" reads like
"slower" -- and it is pinned by a test.

**Verified numerically.** :func:`integrate_test_orbit` integrates (1) and ``dtheta/dt = n(a)``
directly for a perturbed and an unperturbed orbit and differences the along-track angles.
Against the closed form for a step density change it agrees to well under one per cent over a
week; ``docs/storm-term.md`` carries the table.

## The general form used on a real orbit

An eccentric orbit does its drag at perigee, and the code everywhere else integrates
``rho |v_rel| (v_rel . v)`` rather than assuming ``rho v^3``. Carrying that through (2) with
``P(t) = |v_rel| (v_rel . v)`` gives

    s(t) = (3/2) (n a^2 B / mu) integral_0^t (t - tau) drho(tau) P(tau) dtau  (6)

which reduces to (4) exactly when ``P = v^3``, and which is what :func:`shift_from_profile`
evaluates. The near-circular assumption has not gone away -- (2) linearises the relation
between the energy loss and the mean motion, which is a near-circular statement -- so the term
is reported for near-circular orbits and flagged as an approximation for eccentric ones.
``docs/methods.md`` carries it in the approximations list.

## The excess, and where it is measured from

``drho`` is not the density. It is the density the scenario says there is, **minus the density
the object's own element set is already flying through**. An element set carries a B\\* that
SGP4 turns into a decay; given the object's physical ``B`` from Step 2, that decay implies an
effective density, and :func:`driftwatch.drag.ballistic.density_from_decay` inverts it. The
difference is what the element set does not know, which is the only part that displaces
anything.

That is also why the quiet scenario is not this term evaluated under observed conditions but
the Phase 2 model untouched: see :mod:`driftwatch.storm.scenarios`.

## The uncertainty

Three sources, and they do not combine the way one might first write down.

* **The coefficient.** ``sigma_B`` from Step 2, carried on every row with its source label.
  Contributes ``(sigma_B / B) * s``.
* **The density model.** NRLMSIS's own uncertainty is tens of per cent, but the *common* part
  of it cancels for an object whose ``B`` was fitted through the same model: only the product
  ``B rho`` is observable from a decay, so a model low by 20 per cent gives a ``B`` high by 20
  per cent and a product that is right. What does not cancel is the model's error in the storm
  *response*, which has no baseline to divide out against. So the term carried here is
  :data:`driftwatch.config.DENSITY_STORM_RATIO_SIGMA_REL` for a fitted coefficient, and that
  in quadrature with :data:`driftwatch.config.DENSITY_ABSOLUTE_SIGMA_REL` for a ``bstar`` or
  ``typical`` one, where the cancellation argument does not apply. It is applied **coherently
  in time** -- a model bias is not a new random number every three hours -- which means it
  passes through the same weighted integral (6) rather than being added in quadrature across
  samples.
* **The index.** The ``ap_sigma`` column from Step 1 says how uncertain each interval's ap is:
  small for a measurement, the unskilled part of the climatological spread for a forecast
  beyond three days. This one has no closed form, because the density's response to ap is what
  NRLMSIS says it is, so it is evaluated: the density is recomputed with ap raised by its own
  sigma and the difference in the resulting shift is the term.

The three are combined in quadrature, and the result is the standard deviation of the in-track
mean shift. It is added to the **in-track variance** of that object's covariance, and the
shift itself is returned beside the covariance for the scenario to apply to the miss vector.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.drag import ballistic as bal
from driftwatch.drag import density as dn
from driftwatch.orbit.time import to_datetime64

log = logging.getLogger(__name__)

MU_M3_S2 = dn.MU_M3_S2
DAY_S = 86400.0

# --------------------------------------------------------------------------------------
# How far Step 4's validation reaches: the label on every event.

#: The one ballistic coefficient source Step 4 measured the term against, and the only one it
#: found predictive. A `history` coefficient is fitted from the object's own decay.
MEASURED_B_SOURCE = "history"
#: Both objects measured. The only case the May 2024 validation covers.
VALIDATED = "validated"
#: Either object resting on a B* inversion, a population stand-in, or no coefficient at all.
INDICATIVE = "indicative"
#: No storm layer applied at all: `quiet`, and any plain labelled rescore.
NO_STORM_TERM = "none"


def coefficient_source(label: Any) -> str:
    """The bare coefficient source from a ``storm_source_*`` label.

    The label a scenario writes can carry the ``!extrapolated`` marker
    (:meth:`ShiftSeries.summary`), which says the implied decay was large -- a separate
    statement from where the coefficient came from. Strip it.
    """
    return str(label).split("!", 1)[0].strip() or NO_STORM_TERM


def event_validity(primary: Any, secondary: Any) -> str:
    """``validated``, ``indicative`` or ``none`` for one event, from its two coefficient sources.

    **The weaker of the two decides**, because a relative shift is the difference of two
    displacements and the worse-known one bounds what can be said about it. Step 4 measured the
    term against the May 2024 record and found it predictive at r = 0.88 for objects with a
    coefficient fitted from their own decay, and of **no demonstrated skill** for objects
    carrying a B\\* inversion (regression slope -1.39) or a population stand-in. So two measured
    sides is ``validated`` and everything else is ``indicative``.

    ``indicative`` is not a smaller number and nothing downstream downweights it: the sigma such
    an object carries is the one :func:`object_shift` derived, unchanged. The label says the
    validation does not reach the event. ``docs/methods.md``, "Storm-term validity".
    """
    a, b = coefficient_source(primary), coefficient_source(secondary)
    if a == NO_STORM_TERM and b == NO_STORM_TERM:
        return NO_STORM_TERM
    return VALIDATED if a == MEASURED_B_SOURCE and b == MEASURED_B_SOURCE else INDICATIVE


def event_validities(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    """:func:`event_validity` over two arrays of labels, as an object array."""
    return np.array(
        [event_validity(a, b) for a, b in zip(np.asarray(primary), np.asarray(secondary), strict=True)],
        dtype=object,
    )


# --------------------------------------------------------------------------------------
# The closed form and its verification


def in_track_shift_m(b_m2_kg, delta_rho_kg_m3, speed_ms, dt_s):
    """``s = (3/4) B drho v^2 t^2``: equation (5), the constant-excess closed form.

    Positive for a positive excess, meaning the object is **ahead** of where its element set
    puts it, because the extra drag lowered the orbit and a lower orbit is faster. Arrays
    broadcast.
    """
    b = np.asarray(b_m2_kg, dtype=float)
    drho = np.asarray(delta_rho_kg_m3, dtype=float)
    v = np.asarray(speed_ms, dtype=float)
    t = np.asarray(dt_s, dtype=float)
    return 0.75 * b * drho * v**2 * t**2


def mean_motion_drift_rad_s2(b_m2_kg, delta_rho_kg_m3, speed_ms, a_m):
    """``dn/dt = (3/2) n B drho v``: equation (2), for the docs and the numerical check."""
    a = np.asarray(a_m, dtype=float)
    n = np.sqrt(MU_M3_S2 / a**3)
    return 1.5 * n * np.asarray(b_m2_kg, dtype=float) * np.asarray(delta_rho_kg_m3, dtype=float) * speed_ms


def integrate_test_orbit(
    *,
    b_m2_kg: float,
    rho_kg_m3: float,
    delta_rho_kg_m3: float,
    altitude_km: float,
    days: float,
    step_s: float = 60.0,
) -> dict[str, Any]:
    """Integrate a circular orbit under drag twice and difference the along-track angles.

    The verification the prompt asks for: a test orbit with a **step** density change, done
    numerically from equation (1) and ``dtheta/dt = n(a)`` with no appeal to the closed form,
    and compared with :func:`in_track_shift_m`. Fourth-order Runge-Kutta on the two-state
    system ``(a, theta)``; the step is small against the timescale over which ``a`` changes by
    anything, so the integration error is orders below the thing being measured.

    Returns the numerical and closed-form displacements and the relative difference.
    """
    a0 = (dn.EARTH_RADIUS_KM + altitude_km) * 1000.0
    total_s = days * DAY_S

    def derivative(state: np.ndarray, rho: float) -> np.ndarray:
        a = state[0]
        return np.array([-b_m2_kg * rho * np.sqrt(MU_M3_S2 * a), np.sqrt(MU_M3_S2 / a**3)])

    def run(rho: float) -> np.ndarray:
        state = np.array([a0, 0.0])
        t = 0.0
        while t < total_s:
            h = min(step_s, total_s - t)
            k1 = derivative(state, rho)
            k2 = derivative(state + 0.5 * h * k1, rho)
            k3 = derivative(state + 0.5 * h * k2, rho)
            k4 = derivative(state + h * k3, rho)
            state = state + (h / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
            t += h
        return state

    base = run(rho_kg_m3)
    perturbed = run(rho_kg_m3 + delta_rho_kg_m3)
    # The along-track difference at the same instant, measured on the unperturbed radius: this
    # is the in-track component of the separation, which is what the covariance frame wants.
    numerical = float(a0 * (perturbed[1] - base[1]))
    closed = float(in_track_shift_m(b_m2_kg, delta_rho_kg_m3, np.sqrt(MU_M3_S2 / a0), total_s))
    return {
        "numerical_m": numerical,
        "closed_form_m": closed,
        "relative_error": float(closed / numerical - 1.0) if numerical else float("nan"),
        "decay_m": float(a0 - perturbed[0]),
        "days": days,
        "altitude_km": altitude_km,
    }


# --------------------------------------------------------------------------------------
# On a real orbit, under a real scenario


@dataclass(frozen=True)
class ShiftSeries:
    """One object's in-track shift and its uncertainty, as a function of time from the epoch.

    ``seconds`` are measured from the element set's epoch and are the sample times of the
    density track; ``shift_m`` and ``sigma_m`` are the cumulative quantities at each of them,
    so a scenario reads a value at any time of closest approach by interpolating. Interpolating
    rather than re-integrating is exact enough: the shift is a smooth quadratic-ish function of
    time sampled every few minutes.
    """

    norad_id: int
    seconds: np.ndarray
    shift_m: np.ndarray
    sigma_m: np.ndarray
    rho_scenario_kg_m3: float
    rho_implied_kg_m3: float
    b_m2_kg: float
    b_source: str
    note: str = ""
    decay_fraction: float = 0.0  # the scenario's implied decay over the span, as a fraction of a
    shift_revolutions: float = 0.0  # the displacement at the end, in orbit circumferences
    valid: bool = True  # whether the linearisation still holds at all; see `validity`

    @property
    def scoreable(self) -> bool:
        """Whether a probability may be reported for an event this object takes part in.

        The cut set at the Step 3 review, and it is the *displacement* one alone: past
        :data:`driftwatch.config.STORM_MAX_SHIFT_REVOLUTIONS` of the orbit's circumference the
        term has stopped being a small perturbation of a known position and has become a
        statement about where in its orbit the object is, which nothing here can support. An
        event with such an object is reported with its reason and no number.

        ``valid`` is the wider test -- this one *and* the decay fraction -- and it stays the
        label on the covariance source, so the reader of a scored event can still see that its
        implied decay was large without the event being withdrawn.
        """
        limit = config.STORM_MAX_SHIFT_REVOLUTIONS
        return bool(np.isfinite(self.shift_revolutions) and self.shift_revolutions <= limit)

    def unscoreable_reason(self) -> str:
        """Why this object cannot be scored, or ``""`` when it can."""
        if self.scoreable:
            return ""
        if not np.isfinite(self.shift_revolutions):
            return f"{self.norad_id}: the storm term did not evaluate"
        return (
            f"{self.norad_id}: in-track shift {self.shift_revolutions:.3g} of the orbit's "
            f"circumference, past the {config.STORM_MAX_SHIFT_REVOLUTIONS:g} the linear theory allows"
        )

    def at(self, dt_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """``(shift, sigma)`` in metres at the given seconds since the epoch, clamped to the track."""
        t = np.asarray(dt_s, dtype=float)
        if not len(self.seconds):
            return np.zeros(len(t)), np.zeros(len(t))
        inside = np.clip(t, self.seconds[0], self.seconds[-1])
        return np.interp(inside, self.seconds, self.shift_m), np.interp(inside, self.seconds, self.sigma_m)

    def summary(self) -> dict[str, Any]:
        return {
            "norad_id": self.norad_id,
            "valid": self.valid,
            "scoreable": self.scoreable,
            "decay_fraction": float(f"{self.decay_fraction:.3g}"),
            "shift_revolutions": round(self.shift_revolutions, 3),
            "b_m2_kg": round(self.b_m2_kg, 6),
            "b_source": self.b_source,
            "rho_scenario": f"{self.rho_scenario_kg_m3:.3e}",
            "rho_implied": f"{self.rho_implied_kg_m3:.3e}",
            "shift_end_km": round(float(self.shift_m[-1]) / 1000.0, 3) if len(self.shift_m) else None,
            "sigma_end_km": round(float(self.sigma_m[-1]) / 1000.0, 3) if len(self.sigma_m) else None,
        }


def _weighted_integral(seconds: np.ndarray, integrand: np.ndarray) -> np.ndarray:
    """``W(t) = integral_0^t (t - tau) f(tau) dtau`` at every sample time, cumulatively.

    Expanded as ``t * J1(t) - J2(t)`` with ``J1 = integral f`` and ``J2 = integral tau f``, so
    two cumulative trapezoids give the whole series in one pass instead of one integral per
    output time. The ``(t - tau)`` weight is what makes an excess early in the window count for
    more than the same excess late in it, which is the difference between equation (4) and
    equation (5) applied to a mean.
    """
    f = np.nan_to_num(np.asarray(integrand, dtype=float), nan=0.0)
    j1 = np.concatenate([[0.0], np.cumsum(np.diff(seconds) * 0.5 * (f[1:] + f[:-1]))])
    weighted = seconds * f
    j2 = np.concatenate([[0.0], np.cumsum(np.diff(seconds) * 0.5 * (weighted[1:] + weighted[:-1]))])
    return seconds * j1 - j2


def _implied_density(element_row: pd.Series, track: pd.DataFrame, b_m2_kg: float, span_s: float) -> float:
    """The constant density the element set's own B\\* decay implies, given ``B``.

    SGP4's atmosphere is not NRLMSIS and does not vary along the orbit the way it does, so what
    is recovered is one effective number over the span: the density that, with this object's
    physical ``B``, reproduces the decay SGP4 itself produces from the element set's own drag
    term. That is exactly the density the element set is already flying through, and the
    scenario's excess is measured from it.
    """
    days = max(span_s / DAY_S, 1e-6)
    decay_m, a_mean = bal.bstar_decay_m(element_row, days)
    power = pd.to_numeric(track["drag_power_m3_s3"], errors="coerce").to_numpy(dtype=float)
    seconds = _track_seconds(track)
    ok = np.isfinite(power)
    if ok.sum() < 2:
        return float("nan")
    unit_integral = float(np.trapezoid(power[ok], seconds[ok]))
    return bal.density_from_decay(decay_m, unit_integral, a_mean, b_m2_kg)


def _track_seconds(track: pd.DataFrame) -> np.ndarray:
    t = pd.to_datetime(track["t"]).to_numpy(dtype="datetime64[ns]")
    if not len(t):
        return np.zeros(0)
    return (t - t[0]) / np.timedelta64(1, "s")


def shift_from_profile(
    seconds: np.ndarray,
    delta_rho: np.ndarray,
    drag_power: np.ndarray,
    *,
    b_m2_kg: float,
    a_m: float,
) -> np.ndarray:
    """Equation (6): the in-track shift at every sample time, in metres.

    ``delta_rho`` is the excess at each sample and ``drag_power`` is ``|v_rel| (v_rel . v)``
    from the same track, so an eccentric orbit's perigee weighting is carried rather than
    assumed away.
    """
    if not np.isfinite(a_m) or a_m <= 0 or not np.isfinite(b_m2_kg):
        return np.zeros(len(seconds))
    n = np.sqrt(MU_M3_S2 / a_m**3)
    return 1.5 * (n * a_m**2 * b_m2_kg / MU_M3_S2) * _weighted_integral(seconds, delta_rho * drag_power)


def object_shift(
    element_row: pd.Series,
    coefficient: pd.Series | None,
    table: pd.DataFrame,
    end: datetime,
    *,
    perturbed_table: pd.DataFrame | None = None,
    step_s: float | None = None,
) -> ShiftSeries:
    """The whole storm term for one object, from its element-set epoch to ``end``.

    ``coefficient`` is that object's row of ``ballistic.parquet``; ``table`` is the scenario's
    space weather and ``perturbed_table`` the same table with ap raised by its own sigma, which
    is how the index's contribution to the uncertainty is measured. An object with no
    coefficient gets a zero shift and a zero sigma, and says so in ``note`` -- the storm term is
    additive, so "unknown" and "nothing" have to be told apart by the label rather than by the
    number.
    """
    norad_id = int(element_row["norad_id"])
    epoch = pd.Timestamp(element_row["epoch"]).to_pydatetime()
    empty = ShiftSeries(norad_id, np.zeros(0), np.zeros(0), np.zeros(0), np.nan, np.nan, np.nan, "none")
    if coefficient is None or not np.isfinite(float(coefficient.get("b_m2_kg", np.nan))):
        return ShiftSeries(**{**empty.__dict__, "note": "no ballistic coefficient"})
    b = float(coefficient["b_m2_kg"])
    b_source = str(coefficient.get("source", "unknown"))
    b_sigma = float(coefficient.get("b_sigma_m2_kg", np.nan))
    if not np.isfinite(b_sigma):
        b_sigma = abs(b) * config.BALLISTIC_SIGMA_REL_TYPICAL

    track = dn.density_along_orbit(element_row, table, epoch, end, step_s=step_s)
    seconds = _track_seconds(track)
    rho = pd.to_numeric(track["rho_kg_m3"], errors="coerce").to_numpy(dtype=float)
    power = pd.to_numeric(track["drag_power_m3_s3"], errors="coerce").to_numpy(dtype=float)
    usable = np.isfinite(rho) & np.isfinite(power)
    if usable.sum() < 2 or not len(seconds):
        blank = {**empty.__dict__, "b_m2_kg": b, "b_source": b_source, "note": "no density along the orbit"}
        return ShiftSeries(**blank)
    rho = np.where(usable, rho, 0.0)
    power = np.where(usable, power, 0.0)

    a_m = float(np.mean(bal.mean_sma_m(element_row.to_frame().T)))
    span_s = float(seconds[-1])
    rho_implied = _implied_density(element_row, track, b, span_s)
    if not np.isfinite(rho_implied):
        rho_implied = 0.0
    excess = rho - rho_implied
    shift = shift_from_profile(seconds, excess, power, b_m2_kg=b, a_m=a_m)

    # The uncertainty, three terms, in quadrature. Each is a *displacement*, so each passes
    # through the same weighted integral rather than being scaled off the total.
    relative = config.DENSITY_STORM_RATIO_SIGMA_REL
    if b_source != "history":
        relative = float(np.hypot(relative, config.DENSITY_ABSOLUTE_SIGMA_REL))
    from_model = shift_from_profile(seconds, relative * rho, power, b_m2_kg=b, a_m=a_m)
    from_b = shift * (b_sigma / abs(b)) if b else np.zeros_like(shift)
    from_ap = np.zeros_like(shift)
    if perturbed_table is not None:
        raised = dn.density_along_orbit(element_row, perturbed_table, epoch, end, step_s=step_s)
        rho_up = pd.to_numeric(raised["rho_kg_m3"], errors="coerce").to_numpy(dtype=float)
        if len(rho_up) == len(rho):
            rho_up = np.where(np.isfinite(rho_up), rho_up, rho)
            from_ap = shift_from_profile(seconds, rho_up - rho, power, b_m2_kg=b, a_m=a_m)
    sigma = np.sqrt(from_model**2 + from_b**2 + from_ap**2)

    drag_weight = np.trapezoid(power, seconds)
    rho_scenario = float(np.trapezoid(rho * power, seconds) / drag_weight) if drag_weight > 0 else float("nan")
    # How far the scenario says the orbit actually falls over the span, which is what decides
    # whether the small-perturbation derivation still applies to it.
    decay_m = (b * a_m**2 / MU_M3_S2) * float(np.trapezoid(rho * power, seconds))
    fraction, revolutions, ok = validity(decay_m, float(shift[-1]) if len(shift) else 0.0, a_m)
    notes = []
    if not usable.all():
        notes.append(f"{int(usable.sum())} of {len(seconds)} samples usable")
    if not ok:
        notes.append(f"outside the linear theory: {fraction:.2g} of a in decay, {revolutions:.2g} revolutions of shift")
    return ShiftSeries(
        norad_id=norad_id,
        seconds=seconds,
        shift_m=shift,
        sigma_m=sigma,
        rho_scenario_kg_m3=rho_scenario,
        rho_implied_kg_m3=rho_implied,
        b_m2_kg=b,
        b_source=b_source,
        note="; ".join(notes),
        decay_fraction=fraction,
        shift_revolutions=revolutions,
        valid=ok,
    )


def validity(decay_m: float, shift_m: float, a_m: float) -> tuple[float, float, bool]:
    """``(decay fraction, shift in revolutions, whether the linearisation still holds)``.

    Equation (2) linearises the relation between the energy loss and the mean motion at a fixed
    semi-major axis, and equations (4) and (6) then integrate that drift twice with ``v`` held
    constant. Both are small-perturbation statements. They are checked here rather than assumed,
    because the same arithmetic that gives the ISS a few hundred kilometres under a G5 gives a
    high area-to-mass fragment at 300 km a hundred thousand -- which is a faithful evaluation of
    a formula outside its domain, and would be read as a prediction if nothing said otherwise.

    An object that fails this has not been dropped: it keeps its number, and the flag travels
    with it to the output so a reader can see that its probability rests on an extrapolation.
    """
    if not (np.isfinite(a_m) and a_m > 0):
        return float("nan"), float("nan"), False
    fraction = abs(float(decay_m)) / a_m if np.isfinite(decay_m) else float("nan")
    revolutions = abs(float(shift_m)) / (2.0 * np.pi * a_m) if np.isfinite(shift_m) else float("nan")
    ok = bool(
        np.isfinite(fraction)
        and np.isfinite(revolutions)
        and fraction <= config.STORM_MAX_DECAY_FRACTION
        and revolutions <= config.STORM_MAX_SHIFT_REVOLUTIONS
    )
    return fraction, revolutions, ok


def shift_summary(series: dict[int, ShiftSeries]) -> dict[str, Any]:
    """What a set of shifts amounts to, for the log and the run record."""
    ends = [float(s.shift_m[-1]) / 1000.0 for s in series.values() if len(s.shift_m)]
    sigmas = [float(s.sigma_m[-1]) / 1000.0 for s in series.values() if len(s.sigma_m)]
    if not ends:
        return {"n_objects": len(series), "n_with_shift": 0}
    absolute = np.abs(ends)
    return {
        "n_objects": len(series),
        "n_with_shift": len(ends),
        "n_without_coefficient": sum(1 for s in series.values() if not len(s.shift_m)),
        "shift_km": {
            "median_abs": round(float(np.median(absolute)), 3),
            "p90_abs": round(float(np.quantile(absolute, 0.9)), 3),
            "max_abs": round(float(absolute.max()), 3),
            "n_ahead": int(np.sum(np.asarray(ends) > 0)),
            "n_behind": int(np.sum(np.asarray(ends) < 0)),
        },
        "sigma_km": {
            "median": round(float(np.median(sigmas)), 3),
            "p90": round(float(np.quantile(sigmas, 0.9)), 3),
        },
        "by_b_source": {
            str(k): int(v) for k, v in pd.Series([s.b_source for s in series.values()]).value_counts().items()
        },
        "n_outside_linear_theory": int(sum(1 for s in series.values() if len(s.shift_m) and not s.valid)),
        "n_unscoreable": int(sum(1 for s in series.values() if len(s.shift_m) and not s.scoreable)),
        "n_decay_only": int(sum(1 for s in series.values() if len(s.shift_m) and s.scoreable and not s.valid)),
    }


def times_since_epoch_s(epoch: datetime, at: np.ndarray) -> np.ndarray:
    """Seconds from an element-set epoch to each of the absolute times ``at``."""
    at64 = to_datetime64(at).astype("datetime64[us]")
    epoch_ts = pd.Timestamp(epoch)
    epoch_ts = epoch_ts.tz_convert(None) if epoch_ts.tzinfo else epoch_ts
    return (at64 - np.datetime64(epoch_ts.to_datetime64(), "us")) / np.timedelta64(1, "s")
