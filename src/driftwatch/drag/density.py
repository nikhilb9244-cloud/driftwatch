"""NRLMSIS 2.1 along an orbit, driven by the space weather table.

The model. `pymsis` wraps NRLMSIS 2.1, the current version of the US Naval Research
Laboratory's empirical thermosphere model: an enormous fit to decades of satellite drag,
mass spectrometer and radar data, parameterised by date, position, solar flux and
geomagnetic activity. It is the standard baseline, and its own quoted uncertainty is **tens
of per cent even in quiet conditions**, worse in a storm and worse again in the days after
one. Nothing here improves on that; what this module does is drive it correctly and record
what went in.

**Driving it correctly is most of the work**, because the inputs are not the obvious ones:

* ``f107`` is the **previous day's observed** 10.7 cm flux, not the current day's. The
  thermosphere responds to the extreme ultraviolet that arrived yesterday, and the model was
  fitted that way; using today's value is a common and quiet error worth a few per cent.
* ``f107a`` is the **81-day centred** average, centred on the day in question, so for a
  forecast it needs the predicted flux of the following forty days. CelesTrak publishes
  exactly that, which is why the table carries it.
* Both are the **observed** flux, not the flux adjusted to 1 AU. The atmosphere feels what
  arrives at the Earth, and the Earth's distance from the Sun varies by 3.4 per cent over a
  year, so the adjustment is a real 7 per cent swing in the wrong direction.
* ``ap`` is a **seven-element vector per time**, not a number: the daily Ap, the three-hourly
  ap now and at 3, 6 and 9 hours ago, then the average of the eight intervals from 12 to 33
  hours ago and the eight from 36 to 57 hours ago. The thermosphere at a given moment
  remembers two and a half days of heating. Building this wrong is the single easiest way to
  get a storm response that looks plausible and is not, so :func:`ap_vector` is tested
  against a hand-built case. It is only used when the model is asked for it explicitly --
  ``geomagnetic_activity=-1`` -- which :func:`density` always does.

**The step along the orbit.** Density has to be sampled, and the choice trades cost against
the two things that make it vary: where the satellite is (latitude, and above all local
solar time, which swings the density by a factor of two over an orbit) and how high it is
(a factor of e per 50 km or so of scale height). For a near-circular orbit the altitude
barely moves and the local-time variation sets the step; for an eccentric one the altitude
dominates and the perigee passage carries nearly all of the drag. So the step is
:data:`SAMPLES_PER_ORBIT` per revolution, tightened for eccentric orbits in proportion to
how much of the orbit's altitude range a single step would cross, and clamped into
``[MIN_STEP_S, MAX_STEP_S]``. ``docs/density-and-drag.md`` carries the convergence
measurement that justifies the numbers rather than asserting them.

**The frame.** Sampling uses a GMST-only rotation from TEME to an Earth-fixed frame rather
than the full IERS transform. Measured on the ISS, ignoring UT1-UTC and polar motion misplaces
the sub-satellite point by 12 m in latitude and 0.9 m in longitude, which for a model whose own
uncertainty is tens of per cent is nothing, and it avoids an astropy frame transform per sample
time over millions of samples.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.orbit import frames, propagator
from driftwatch.orbit.time import to_datetime64

log = logging.getLogger(__name__)

try:  # pragma: no cover - exercised by every real call; the fallback is for a stripped env
    import pymsis
except ImportError:  # pragma: no cover
    pymsis = None  # type: ignore[assignment]

MU_M3_S2 = 3.986004418e14
EARTH_RADIUS_KM = 6378.137
INTERVAL_HOURS = 3
# NRLMSIS wants 57 hours of three-hourly ap history behind every sample, which is 19
# intervals. A table that does not reach back this far cannot drive the model, so the
# builders add this lead rather than silently filling with zeros.
AP_HISTORY_INTERVALS = 19
AP_HISTORY_HOURS = AP_HISTORY_INTERVALS * INTERVAL_HOURS
# Plus a day for the previous day's F10.7, and a margin so the lead lands on a whole
# interval whatever the sample time is.
WEATHER_LEAD = timedelta(hours=AP_HISTORY_HOURS + 24 + INTERVAL_HOURS)


def weather_window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """The span a weather table must cover to drive the model between ``start`` and ``end``."""
    return start - WEATHER_LEAD, end


# --------------------------------------------------------------------------------------
# The model inputs


@dataclass(frozen=True)
class MsisInputs:
    """The three driver arrays NRLMSIS wants, one row per sample time, and where they came from."""

    f107: np.ndarray  # previous day's observed 10.7 cm flux
    f107a: np.ndarray  # 81-day centred average, observed
    ap: np.ndarray  # (n, 7): daily Ap, then the history the model expects
    provenance: dict[str, int] = field(default_factory=dict)
    n_incomplete: int = 0

    def __len__(self) -> int:
        return len(self.f107)


def _grid(table: pd.DataFrame) -> tuple[np.datetime64, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The table as aligned arrays on its own three-hourly grid."""
    t = pd.to_datetime(table["t"], utc=True).dt.tz_localize(None).to_numpy(dtype="datetime64[s]")
    order = np.argsort(t)
    t = t[order]
    ap = pd.to_numeric(table["ap"], errors="coerce").to_numpy(dtype=float)[order]
    ap_daily = pd.to_numeric(table["ap_daily"], errors="coerce").to_numpy(dtype=float)[order]
    f107 = pd.to_numeric(table["f107"], errors="coerce").to_numpy(dtype=float)[order]
    f107_81 = pd.to_numeric(table["f107_81"], errors="coerce").to_numpy(dtype=float)[order]
    return t[0], t, ap, ap_daily, f107, f107_81


def _indices(times64: np.ndarray, t0: np.datetime64, n: int) -> np.ndarray:
    """Which three-hourly interval each time falls in, ``-1`` where it falls off the table."""
    seconds = (times64.astype("datetime64[s]") - t0) / np.timedelta64(1, "s")
    idx = np.floor(seconds / (INTERVAL_HOURS * 3600.0)).astype(np.int64)
    return np.where((idx >= 0) & (idx < n), idx, -1)


def ap_vector(times, table: pd.DataFrame) -> np.ndarray:
    """The seven-element ap input NRLMSIS 2.x expects, one row per time.

    ``[daily Ap, ap now, ap 3 h ago, ap 6 h ago, ap 9 h ago, mean of 12-33 h ago,
    mean of 36-57 h ago]``. The last two are eight three-hourly values each, which is why
    the table has to reach 57 hours behind the first sample; a time whose history is not
    covered comes back NaN rather than zero, because a quiet zero would turn a missing
    record into a calm day and hide a storm.
    """
    times64 = to_datetime64(times)
    t0, grid_t, ap, ap_daily, _, _ = _grid(table)
    idx = _indices(times64, t0, len(grid_t))
    out = np.full((len(times64), 7), np.nan)
    ok = idx >= AP_HISTORY_INTERVALS
    if not ok.any():
        return out
    here = idx[ok]
    out[ok, 0] = ap_daily[here]
    for k, lag in enumerate((0, 1, 2, 3), start=1):
        out[ok, k] = ap[here - lag]
    # Lags 4 to 11 are the intervals 12 to 33 hours back, 12 to 19 those 36 to 57 hours back.
    windows = np.stack([ap[here - lag] for lag in range(4, 12)], axis=1)
    out[ok, 5] = windows.mean(axis=1)
    windows = np.stack([ap[here - lag] for lag in range(12, 20)], axis=1)
    out[ok, 6] = windows.mean(axis=1)
    return out


def f107_inputs(times, table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """``(previous day's observed F10.7, 81-day centred average)`` for each time.

    The previous day's value is what NRLMSIS was fitted with: the thermosphere responds to
    yesterday's extreme ultraviolet. Subtracting exactly 24 hours always lands in the
    previous calendar day whatever the hour, and every interval of a day carries that day's
    flux, so the lookup is one index shift rather than a date join.
    """
    times64 = to_datetime64(times).astype("datetime64[s]")
    t0, grid_t, _, _, f107, f107_81 = _grid(table)
    n = len(grid_t)
    yesterday = _indices(times64 - np.timedelta64(24, "h"), t0, n)
    today = _indices(times64, t0, n)
    out_f107 = np.where(yesterday >= 0, f107[np.maximum(yesterday, 0)], np.nan)
    out_f107a = np.where(today >= 0, f107_81[np.maximum(today, 0)], np.nan)
    return out_f107, out_f107a


def msis_inputs(times, table: pd.DataFrame) -> MsisInputs:
    """Everything NRLMSIS needs for these times, plus a count of what the table could not cover."""
    ap = ap_vector(times, table)
    f107, f107a = f107_inputs(times, table)
    complete = np.isfinite(ap).all(axis=1) & np.isfinite(f107) & np.isfinite(f107a)
    times64 = to_datetime64(times)
    t0, grid_t, *_ = _grid(table)
    idx = _indices(times64, t0, len(grid_t))
    provenance: dict[str, int] = {}
    if "provenance" in table.columns and len(table):
        labels = table.sort_values("t")["provenance"].astype(str).to_numpy()
        used = labels[idx[idx >= 0]]
        provenance = {str(k): int(v) for k, v in zip(*np.unique(used, return_counts=True), strict=True)}
    n_incomplete = int((~complete).sum())
    if n_incomplete:
        log.warning(
            "%d of %d sample times have no complete NRLMSIS driver -- the table has to cover every sample "
            "and %d hours of history behind the earliest one; their density will be NaN",
            n_incomplete,
            len(complete),
            AP_HISTORY_HOURS,
        )
    return MsisInputs(f107=f107, f107a=f107a, ap=ap, provenance=provenance, n_incomplete=n_incomplete)


# --------------------------------------------------------------------------------------
# The model itself


def density(times, lat_deg, lon_deg, alt_km, inputs: MsisInputs) -> np.ndarray:
    """Total mass density in kg/m^3 at each (time, latitude, longitude, altitude).

    Satellite fly-through mode: the arrays are aligned, one output per input point, not a
    grid. ``geomagnetic_activity=-1`` is what makes NRLMSIS read the whole ap vector instead
    of the daily value alone, which is the entire point of building it.
    """
    if pymsis is None:  # pragma: no cover
        raise RuntimeError("pymsis is not installed; `uv sync` installs it")
    times64 = to_datetime64(times).astype("datetime64[ns]")
    lat = np.asarray(lat_deg, dtype=float)
    lon = np.asarray(lon_deg, dtype=float)
    alt = np.asarray(alt_km, dtype=float)
    if not (len(times64) == len(lat) == len(lon) == len(alt) == len(inputs)):
        raise ValueError("times, positions and drivers must be the same length (satellite fly-through mode)")
    if not len(times64):
        return np.zeros(0)
    # NRLMSIS is undefined below the ground and above the exosphere; NaN in, NaN out
    # everywhere else, which the callers count rather than hide.
    usable = np.isfinite(lat) & np.isfinite(lon) & np.isfinite(alt) & np.isfinite(inputs.f107)
    usable &= np.isfinite(inputs.f107a) & np.isfinite(inputs.ap).all(axis=1)
    out = np.full(len(times64), np.nan)
    if not usable.any():
        return out
    result = pymsis.calculate(
        times64[usable],
        lon[usable],
        lat[usable],
        alt[usable],
        inputs.f107[usable],
        inputs.f107a[usable],
        inputs.ap[usable],
        geomagnetic_activity=-1,
        version=config.MSIS_VERSION,
    )
    out[usable] = np.asarray(result)[..., 0]
    return out


# --------------------------------------------------------------------------------------
# Along an orbit


def sample_step_s(mean_motion: float, eccentricity: float) -> float:
    """The sampling step for one object, in seconds. See the module docstring for the reasoning.

    ``SAMPLES_PER_ORBIT`` samples a revolution, which resolves the local-time swing that
    dominates a near-circular orbit's density. An eccentric orbit is tightened in proportion
    to its altitude range measured in scale heights, because there the drag is concentrated
    in the perigee passage and a step that flies over it integrates the wrong thing.
    """
    period_s = 86400.0 / max(float(mean_motion), 1e-6)
    step = period_s / config.DENSITY_SAMPLES_PER_ORBIT
    e = max(float(eccentricity), 0.0)
    if e > config.DENSITY_ECCENTRICITY_THRESHOLD:
        # The radius swings by 2ae over an orbit; each scale height of that swing is a factor
        # of e in density, so the step shrinks by the number of scale heights involved.
        a_km = (MU_M3_S2 / (2 * np.pi * mean_motion / 86400.0) ** 2) ** (1 / 3) / 1000.0
        scale_heights = 2.0 * a_km * e / config.DENSITY_SCALE_HEIGHT_KM
        step /= max(1.0, scale_heights / config.DENSITY_SCALE_HEIGHTS_PER_STEP)
    return float(np.clip(step, config.DENSITY_MIN_STEP_S, config.DENSITY_MAX_STEP_S))


def orbit_track(element_row: pd.Series | pd.DataFrame, times) -> pd.DataFrame:
    """Sub-satellite position and the two speeds the drag integral needs, at each time.

    One object, many times. The Earth-fixed rotation is GMST-only: see the module docstring
    for what that costs and why it is worth it here.

    ``speed_ms`` is the inertial speed. ``drag_power_m3_s3`` is the quantity the energy loss
    is actually proportional to, ``|v_rel| (v_rel . v)``, where ``v_rel`` is the velocity
    relative to the **co-rotating** atmosphere. The atmosphere carries a satellite's own
    ground track along at up to 465 m/s, which is 6 per cent of an orbital speed and about 17
    per cent of its cube, so ignoring it would be a systematic overestimate of the drag on
    every prograde orbit and an underestimate on every retrograde one.
    """
    row = element_row.iloc[[0]] if isinstance(element_row, pd.DataFrame) else element_row.to_frame().T
    times64 = to_datetime64(times)
    state = propagator.propagate_snapshot(row, times64)
    r_teme = state.r_teme[0]
    v_teme = state.v_teme[0]
    error = state.error[0]
    lat, lon, alt = frames.teme_positions_to_geodetic(r_teme, times64)
    v_ms = v_teme * 1000.0
    omega = np.array([0.0, 0.0, frames.EARTH_ROTATION_RATE])
    v_rel = v_ms - np.cross(omega, r_teme * 1000.0)
    speed = np.linalg.norm(v_ms, axis=1)
    drag_power = np.linalg.norm(v_rel, axis=1) * np.einsum("ij,ij->i", v_rel, v_ms)
    bad = error != 0
    lat[bad] = lon[bad] = alt[bad] = np.nan
    speed[bad] = np.nan
    drag_power[bad] = np.nan
    return pd.DataFrame(
        {
            "t": times64,
            "lat_deg": lat,
            "lon_deg": lon,
            "alt_km": alt,
            "speed_ms": speed,
            "drag_power_m3_s3": drag_power,
        }
    )


def sample_times(start: datetime, end: datetime, step_s: float) -> np.ndarray:
    """Sample times from ``start`` to ``end`` inclusive of both ends, at most ``step_s`` apart."""
    span = (end - start).total_seconds()
    if span <= 0:
        return to_datetime64([start])
    n = int(np.ceil(span / step_s)) + 1
    offsets = np.linspace(0.0, span, n)
    base = np.datetime64(start.replace(tzinfo=None) if start.tzinfo else start, "us")
    return base + (offsets * 1e6).astype("timedelta64[us]")


def density_along_orbit(
    element_row: pd.Series | pd.DataFrame,
    table: pd.DataFrame,
    start: datetime,
    end: datetime,
    *,
    step_s: float | None = None,
) -> pd.DataFrame:
    """Density along one object's orbit from ``start`` to ``end`` under the given weather.

    Returns one row per sample: time, sub-satellite position, altitude, inertial speed and
    density. ``start`` is normally the element set's own epoch and ``end`` the time of
    closest approach, so the integral of this is the drag the element set did not know about.
    """
    row = element_row.iloc[0] if isinstance(element_row, pd.DataFrame) else element_row
    if step_s is None:
        step_s = sample_step_s(float(row["mean_motion"]), float(row.get("eccentricity", 0.0)))
    times = sample_times(start, end, step_s)
    track = orbit_track(element_row, times)
    inputs = msis_inputs(times, table)
    track["rho_kg_m3"] = density(times, track["lat_deg"], track["lon_deg"], track["alt_km"], inputs)
    track.attrs["step_s"] = float(step_s)
    track.attrs["n_incomplete_weather"] = inputs.n_incomplete
    track.attrs["weather_provenance"] = inputs.provenance
    return track


def drag_integral(track: pd.DataFrame) -> dict[str, float]:
    """``integral of rho |v_rel| (v_rel . v) dt`` over the track, and what went into it.

    This is the quantity a decay measures. Energy per unit mass is ``E = -mu / 2a``, and drag
    removes it at ``dE/dt = -B/2 rho |v_rel| (v_rel . v)``, so

        da/dt = -(B a^2 / mu) rho |v_rel| (v_rel . v)

    which for a circular orbit collapses to the familiar ``da/dt = -B rho sqrt(mu a)`` and for
    an eccentric one does not: there the drag is concentrated in the perigee passage, where
    both the density and the speed are highest, and using a circular formula with a mean
    density understates the integral by tens of per cent. ``rho_mean`` is reported beside it
    because it is the readable number, not because anything is fitted from it.

    Trapezoidal over the sample times, which is what the sampling step was chosen to support.
    A sample with no density (a propagation error, a gap in the weather) is dropped, and
    ``coverage`` says how much of the track survived.
    """
    rho = pd.to_numeric(track["rho_kg_m3"], errors="coerce").to_numpy(dtype=float)
    power = pd.to_numeric(track["drag_power_m3_s3"], errors="coerce").to_numpy(dtype=float)
    t = pd.to_datetime(track["t"]).to_numpy(dtype="datetime64[ns]")
    seconds = (t - t[0]) / np.timedelta64(1, "s") if len(t) else np.zeros(0)
    ok = np.isfinite(rho) & np.isfinite(power)
    out = {"integral": float("nan"), "rho_mean": float("nan"), "n": int(ok.sum()), "coverage": 0.0}
    if not len(t):
        return out
    out["coverage"] = float(ok.mean())
    if ok.sum() < 2:
        return out
    out["integral"] = float(np.trapezoid(rho[ok] * power[ok], seconds[ok]))
    out["rho_mean"] = float(np.mean(rho[ok]))
    out["seconds"] = float(seconds[ok][-1] - seconds[ok][0])
    return out


def mean_density(track: pd.DataFrame) -> dict[str, float]:
    """The plain time mean of the density along a track, and the drag-weighted one.

    The readable numbers, for the sanity checks and the reports. The fit uses
    :func:`drag_integral`, which is the quantity a decay actually measures.
    """
    rho = pd.to_numeric(track["rho_kg_m3"], errors="coerce").to_numpy(dtype=float)
    power = pd.to_numeric(track["drag_power_m3_s3"], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(rho) & np.isfinite(power)
    if not ok.any():
        return {"rho_mean": float("nan"), "rho_v3_mean": float("nan"), "n": 0, "coverage": 0.0}
    weights = power[ok]
    return {
        "rho_mean": float(np.mean(rho[ok])),
        "rho_v3_mean": float(np.sum(rho[ok] * weights) / np.sum(weights)),
        "n": int(ok.sum()),
        "coverage": float(ok.mean()),
    }


# --------------------------------------------------------------------------------------
# The sanity checks the prompt asks for


def quiet_density_profile(
    table: pd.DataFrame,
    *,
    at: datetime | None = None,
    altitudes_km: tuple[float, ...] = (300.0, 400.0, 500.0, 600.0),
    latitude_deg: float = 0.0,
) -> pd.DataFrame:
    """Density at the given altitudes under the table's own conditions, averaged over local time.

    Averaged over 24 local solar times, because the day-night contrast at these altitudes is
    a factor of two and a single longitude would be a coin toss rather than a check. The
    published values this is compared against in ``docs/density-and-drag.md`` are themselves
    global averages at moderate solar activity.
    """
    at = at or datetime.now(UTC)
    longitudes = np.arange(0.0, 360.0, 15.0)
    rows = []
    for alt in altitudes_km:
        times = np.repeat(to_datetime64([at]), len(longitudes))
        inputs = msis_inputs(times, table)
        rho = density(times, np.full(len(longitudes), latitude_deg), longitudes, np.full(len(longitudes), alt), inputs)
        rows.append(
            {
                "altitude_km": alt,
                "rho_mean_kg_m3": float(np.nanmean(rho)),
                "rho_min_kg_m3": float(np.nanmin(rho)),
                "rho_max_kg_m3": float(np.nanmax(rho)),
                "day_night_ratio": float(np.nanmax(rho) / np.nanmin(rho)) if np.nanmin(rho) > 0 else float("nan"),
            }
        )
    out = pd.DataFrame(rows)
    out.attrs["f107"] = float(np.nanmedian(inputs.f107))
    out.attrs["f107a"] = float(np.nanmedian(inputs.f107a))
    out.attrs["ap_daily"] = float(np.nanmedian(inputs.ap[:, 0]))
    out.attrs["at"] = at.isoformat()
    return out


def storm_ratio(
    table: pd.DataFrame,
    kp: float,
    *,
    at: datetime | None = None,
    altitudes_km: tuple[float, ...] = (300.0, 400.0, 500.0, 600.0),
    hours: float = 24.0,
) -> pd.DataFrame:
    """Density under a flat storm at ``kp`` divided by density under the table as it stands.

    The storm is applied for ``hours`` before the evaluation time as well as at it, because
    the thermosphere at a given moment is responding to two and a half days of heating and a
    storm switched on at the instant of evaluation would show almost nothing.
    """
    from driftwatch.weather.table import apply_synthetic

    at = at or datetime.now(UTC)
    quiet = quiet_density_profile(table, at=at, altitudes_km=altitudes_km)
    profile = table.copy()
    t = pd.to_datetime(profile["t"], utc=True)
    storm_kp = np.where(t >= pd.Timestamp(at) - pd.Timedelta(hours=hours), kp, np.nan)
    base_kp = pd.to_numeric(profile["kp"], errors="coerce").to_numpy(dtype=float)
    stormy = apply_synthetic(profile, np.where(np.isfinite(storm_kp), storm_kp, base_kp), name=f"flat-kp{kp:g}")
    storm = quiet_density_profile(stormy, at=at, altitudes_km=altitudes_km)
    out = quiet[["altitude_km"]].copy()
    out["rho_quiet_kg_m3"] = quiet["rho_mean_kg_m3"]
    out["rho_storm_kg_m3"] = storm["rho_mean_kg_m3"]
    out["ratio"] = storm["rho_mean_kg_m3"] / quiet["rho_mean_kg_m3"]
    out.attrs = {"kp": kp, "hours": hours, "at": at.isoformat(), "quiet_ap": quiet.attrs.get("ap_daily")}
    return out


def profile_summary(profile: pd.DataFrame) -> dict[str, Any]:
    """The quiet profile as a dict for the log and the run record."""
    return {
        "at": profile.attrs.get("at"),
        "f107": profile.attrs.get("f107"),
        "f107a": profile.attrs.get("f107a"),
        "ap_daily": profile.attrs.get("ap_daily"),
        "rho": {
            f"{int(row.altitude_km)}km": f"{row.rho_mean_kg_m3:.3e}"
            for row in profile.itertuples()  # noqa: B905
        },
    }
