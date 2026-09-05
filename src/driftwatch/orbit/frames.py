"""Reference-frame conversions: TEME to an Earth-fixed frame, and to geodetic coordinates.

Why this exists. SGP4 outputs positions in TEME, "True Equator, Mean Equinox": an
inertial frame whose z-axis is the true (nutated) pole of date but whose x-axis is the
*mean* equinox of date, an awkward mixture that exists only because the original
Air Force software worked that way. To put an object over a point on the map we need an
Earth-fixed frame that rotates with the ground: ITRS, the International Terrestrial
Reference System, of which WGS84 is a realisation for practical purposes.

Going from TEME to ITRS takes two rotations:

1. About the z-axis by the Greenwich Mean Sidereal Time (GMST), which is how far the
   Earth has turned. GMST is a function of UT1, the time scale tied to Earth's rotation,
   which differs from UTC by up to 0.9 s (published by the IERS as DUT1). Ignoring DUT1
   rotates everything about the pole by up to 0.9 s of Earth rotation: about 400 m at
   the surface or in LEO, and up to 3 km at geostationary radius, since the error
   scales with distance from the axis.
2. Polar motion, the wobble of the rotation axis relative to the crust, a few tenths of
   an arcsecond: about 10 m in LEO, 60 m at geostationary radius.

The full conversion here uses astropy, which fetches IERS Earth orientation data for both
corrections. The GMST-only variant reproduces what the browser does with satellite.js
(UTC in place of UT1, no polar motion) so that the difference can be measured and stated.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime

import astropy.units as u
import erfa
import numpy as np
import pandas as pd
from astropy.coordinates import ITRS, TEME, CartesianDifferential, CartesianRepresentation, EarthLocation
from astropy.time import Time
from astropy.utils import iers
from skyfield.api import load as skyfield_load
from skyfield.sgp4lib import TEME as SkyfieldTEME

from driftwatch.orbit.time import julian_date, julian_dates, parse_utc, to_datetime64

log = logging.getLogger(__name__)

# Earth's rotation rate used for the rotating-frame velocity term (rad/s), IERS 2010.
EARTH_ROTATION_RATE = 7.292115e-5


def _astropy_time(t: datetime) -> Time:
    return Time(parse_utc(t), scale="utc")


def teme_to_itrs(r_teme: np.ndarray, v_teme: np.ndarray, t: datetime) -> tuple[np.ndarray, np.ndarray]:
    """Rotate TEME position and velocity into ITRS at UTC time ``t``.

    ``r_teme`` and ``v_teme`` are ``(n, 3)`` arrays in km and km/s. Returns ITRS position
    (km) and velocity (km/s) with the same shape. The velocity is the velocity relative to
    the rotating Earth, i.e. it includes the omega-cross-r term. Rows containing NaN are
    passed through as NaN.

    Uses IERS data for UT1-UTC and polar motion. If the requested time lies beyond the
    available table, astropy extrapolates and a warning is logged once; the error this
    introduces is at the tens-of-metres level.
    """
    r_teme = np.asarray(r_teme, dtype=float)
    v_teme = np.asarray(v_teme, dtype=float)
    time = _astropy_time(t)
    ok = np.isfinite(r_teme).all(axis=1) & np.isfinite(v_teme).all(axis=1)
    r_out = np.full_like(r_teme, np.nan)
    v_out = np.full_like(v_teme, np.nan)
    if not ok.any():
        return r_out, v_out
    with iers.conf.set_temp("iers_degraded_accuracy", "warn"), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        teme = TEME(
            CartesianRepresentation(
                r_teme[ok].T * u.km,
                differentials=CartesianDifferential(v_teme[ok].T * u.km / u.s),
            ),
            obstime=time,
        )
        itrs = teme.transform_to(ITRS(obstime=time))
    for w in caught:
        log.warning("astropy: %s", str(w.message).splitlines()[0])
    r_out[ok] = itrs.cartesian.xyz.to_value(u.km).T
    v_out[ok] = itrs.velocity.d_xyz.to_value(u.km / u.s).T
    return r_out, v_out


def itrs_to_teme(r_itrs: np.ndarray, v_itrs: np.ndarray, times) -> tuple[np.ndarray, np.ndarray]:
    """Rotate ITRS positions and velocities into TEME, one UTC time per row.

    The inverse of :func:`teme_to_itrs` for a batch of times: ``r_itrs`` and ``v_itrs`` are
    ``(n, 3)`` in km and km/s and ``times`` has one entry per row. Rows containing NaN are
    passed through as NaN. Added for the calibration against precise orbits
    (``driftwatch.storm.precise``), whose truth is published in the ITRF; that module takes
    the inertial velocity it needs from the rotated positions rather than from the rotated
    velocity, so nothing there depends on how astropy treats the frame's rotation rate.
    """
    r_itrs = np.asarray(r_itrs, dtype=float)
    v_itrs = np.asarray(v_itrs, dtype=float)
    t64 = to_datetime64(times).astype("datetime64[us]")
    ok = np.isfinite(r_itrs).all(axis=1) & np.isfinite(v_itrs).all(axis=1)
    r_out = np.full_like(r_itrs, np.nan)
    v_out = np.full_like(v_itrs, np.nan)
    if not ok.any():
        return r_out, v_out
    time = Time(t64[ok], scale="utc")
    with iers.conf.set_temp("iers_degraded_accuracy", "warn"), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        itrs = ITRS(
            CartesianRepresentation(
                r_itrs[ok].T * u.km,
                differentials=CartesianDifferential(v_itrs[ok].T * u.km / u.s),
            ),
            obstime=time,
        )
        teme = itrs.transform_to(TEME(obstime=time))
    for w in caught:
        log.warning("astropy: %s", str(w.message).splitlines()[0])
    r_out[ok] = teme.cartesian.xyz.to_value(u.km).T
    v_out[ok] = teme.velocity.d_xyz.to_value(u.km / u.s).T
    return r_out, v_out


_TIMESCALE = None


def _timescale():
    """Skyfield's timescale, built once. It reads no files: the built-in leap-second table serves."""
    global _TIMESCALE
    if _TIMESCALE is None:
        _TIMESCALE = skyfield_load.timescale()
    return _TIMESCALE


def j2000_to_teme(r_km: np.ndarray, v_kms: np.ndarray, times) -> tuple[np.ndarray, np.ndarray]:
    """Rotate mean-equator mean-equinox J2000 states into TEME, one time per row.

    Why this exists. SpaceX publishes its Starlink ephemerides in the frame its file names
    declare, ``MEME`` -- mean equator and mean equinox -- and the rest of this project is in
    TEME, because that is what SGP4 produces. The two differ by precession and nutation
    accumulated since J2000, which by 2026 is about 0.36 degrees: **roughly 44 km at low
    Earth orbit radius**. Reading the published states as TEME is not a small error, it is
    two hundred times the fit residual this conversion exists to remove, and
    ``docs/spacex-ephemerides.md`` records how that was measured rather than assumed.

    MEME J2000 and the ICRF differ by the frame bias, about 23 milliarcseconds, which is
    0.8 m at this radius -- below every other error in the chain and ignored here, as it is
    everywhere else in the project.

    The rotation is skyfield's, not astropy's, and that is the reverse of Phase 1, where
    astropy converted and skyfield checked. The reason is cost, not preference: a fetch
    converts a few hundred thousand states and astropy's frame machinery takes about 1.7 s
    per 4,321-state file against skyfield's 0.13 s. ``tests/test_frames.py`` pins the two
    against each other -- they agree to under a millimetre in position -- so the check that
    justified astropy in Phase 1 still runs, only as a test rather than in the pipeline.

    One difference is real and stated rather than hidden: skyfield rotates the velocity with
    the same matrix as the position, so it omits the frame's own rotation rate, worth about
    0.12 mm/s. That term matters to nothing here -- it is a part in 10^8 of a relative speed,
    and over a 60-second interpolation interval it moves a position by 7 mm.
    """
    r = np.asarray(r_km, dtype=float)
    v = np.asarray(v_kms, dtype=float)
    if r.shape != v.shape or r.ndim != 2 or r.shape[1] != 3:
        raise ValueError(f"expected (n, 3) position and velocity, got {r.shape} and {v.shape}")
    times64 = to_datetime64(times)
    if len(times64) != len(r):
        raise ValueError(f"got {len(r)} states and {len(times64)} times")
    when = _timescale().from_datetimes(list(pd.to_datetime(times64, utc=True).to_pydatetime()))
    rot = SkyfieldTEME.rotation_at(when)  # (3, 3, n), ICRF -> TEME
    if rot.ndim == 2:  # a single time comes back as (3, 3)
        rot = rot[:, :, None]
    return np.einsum("ijk,kj->ki", rot, r), np.einsum("ijk,kj->ki", rot, v)


def teme_to_ecef_gmst_only(r_teme: np.ndarray, v_teme: np.ndarray, t: datetime) -> tuple[np.ndarray, np.ndarray]:
    """The approximate conversion used in the browser: GMST rotation with UTC as UT1.

    This is a pseudo-Earth-fixed frame (Vallado's PEF): no polar motion, and the
    sidereal angle is evaluated at UTC rather than UT1. Used to quantify the viewer's
    error against :func:`teme_to_itrs`; not for analysis.
    """
    r_teme = np.asarray(r_teme, dtype=float)
    v_teme = np.asarray(v_teme, dtype=float)
    jd, fr = julian_date(t)
    theta = float(erfa.gmst82(jd, fr))  # IAU 1982 GMST, the expression SGP4 tooling uses
    c, s = np.cos(theta), np.sin(theta)
    rot = np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])
    r_pef = r_teme @ rot.T
    omega = np.array([0.0, 0.0, EARTH_ROTATION_RATE])
    v_pef = v_teme @ rot.T - np.cross(omega, r_pef)
    return r_pef, v_pef


def teme_positions_to_geodetic(r_teme: np.ndarray, times) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Geodetic latitude, longitude (deg) and altitude (km) for one position per time.

    A GMST-only rotation, vectorised over times, and then the WGS84 conversion. Unlike
    :func:`teme_to_itrs` this skips polar motion and treats UTC as UT1. Measured against the
    full transform on the ISS on 2026-09-02 that costs 12 m in latitude, 0.9 m in longitude and
    1 cm in height -- nothing for a thermosphere model whose own uncertainty is tens of per
    cent, and it is the difference between one vectorised rotation and an
    astropy frame transform per sample time -- millions of them, for a run's worth of orbits.
    Use :func:`teme_to_itrs` for anything where the position itself is the answer.
    """
    r_teme = np.asarray(r_teme, dtype=float)
    times64 = to_datetime64(times)
    jd, fr = julian_dates(times64)
    theta = np.asarray(erfa.gmst82(jd, fr), dtype=float)
    c, s = np.cos(theta), np.sin(theta)
    # The rotation about z, applied per row: [x cos + y sin, -x sin + y cos, z].
    x, y, z = r_teme[:, 0], r_teme[:, 1], r_teme[:, 2]
    r_ecef = np.stack([x * c + y * s, -x * s + y * c, z], axis=1)
    return itrs_to_geodetic(r_ecef)


def itrs_to_geodetic(r_itrs: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """WGS84 geodetic latitude, longitude (degrees) and height (km) from ITRS positions.

    Height is above the WGS84 ellipsoid, which is what "altitude" means everywhere in
    this project. It differs from height above the mean sphere by up to about 21 km at
    the poles, because the Earth is flattened.
    """
    r_itrs = np.asarray(r_itrs, dtype=float)
    ok = np.isfinite(r_itrs).all(axis=1)
    lat = np.full(r_itrs.shape[0], np.nan)
    lon = np.full(r_itrs.shape[0], np.nan)
    height = np.full(r_itrs.shape[0], np.nan)
    if ok.any():
        loc = EarthLocation.from_geocentric(r_itrs[ok, 0] * u.km, r_itrs[ok, 1] * u.km, r_itrs[ok, 2] * u.km)
        geo = loc.to_geodetic("WGS84")
        lat[ok] = geo.lat.to_value(u.deg)
        lon[ok] = geo.lon.to_value(u.deg)
        height[ok] = geo.height.to_value(u.km)
    return lat, lon, height
