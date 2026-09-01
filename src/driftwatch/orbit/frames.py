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
from astropy.coordinates import ITRS, TEME, CartesianDifferential, CartesianRepresentation, EarthLocation
from astropy.time import Time
from astropy.utils import iers

from driftwatch.orbit.time import julian_date, parse_utc

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
