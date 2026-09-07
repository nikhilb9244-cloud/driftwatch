"""The site, its receivers and its beam, and the geometry from an orbit to an angle on the sky.

Physics note. A dish of diameter ``D`` observing at wavelength ``λ`` has a main beam whose
half-power width is close to ``λ/D`` radians times a constant of order one that depends on how
the dish is illuminated. MeerKAT's L-band beam was measured: Mauch et al. (2020, ApJ 888, 61,
section 2.2, equation 4) give the circularised half-power width as
``θ_b = 57.5' × (ν / 1.5 GHz)^-1``, which for a 13.5 m dish is ``1.13 λ/D``. The holography
paper (de Villiers, 2023, AJ 165, 78) finds the width proportional to ``λ/D`` over most of each
band, so the same relation is applied to the UHF and S receivers. That is an extrapolation from
a measurement in one band, and it is labelled as such wherever it is used.

Frames. Satellite positions come from SGP4 in TEME. They are rotated into the Earth-fixed
pseudo-body-fixed frame with the Greenwich mean sidereal time of the epoch, taking UTC for UT1
and ignoring polar motion, which together are under a hundredth of a degree in 2024, against a
beam whose half-power radius is half a degree or more. The boresight is a J2000 (ICRS) position
turned into altitude and azimuth by astropy, which handles precession, nutation and aberration;
the two directions are compared in the site's east-north-up frame. No refraction is applied to
either, so both are geometric directions.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import astropy.units as u
import erfa
import numpy as np
from astropy.coordinates import ICRS, AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers

from driftwatch.orbit.time import julian_dates, to_datetime64

WGS84_A_KM = 6378.137
WGS84_E2 = 6.69437999014e-3
EARTH_RADIUS_KM = 6378.137

# Mauch et al. 2020, equation 4: 57.5 arcmin at 1.5 GHz, scaling as 1/frequency.
BEAM_FWHM_ARCMIN_AT_1500_MHZ = 57.5
BEAM_REFERENCE_MHZ = 1500.0
BEAM_SOURCE = (
    "Mauch et al. 2020, ApJ 888, 61, section 2.2, equation 4 (circularised L-band half-power width "
    "57.5 arcmin at 1.5 GHz, scaling as 1/frequency); applied to UHF and S by the lambda/D scaling "
    "de Villiers 2023, AJ 165, 78 reports over most of each band"
)


@dataclass(frozen=True)
class Site:
    """A place on the WGS84 ellipsoid with a dish of one diameter."""

    name: str
    latitude_deg: float
    longitude_deg: float
    height_m: float
    dish_diameter_m: float
    source: str

    def ecef_km(self) -> np.ndarray:
        """The site's WGS84 Cartesian position in km."""
        phi, lam = np.radians([self.latitude_deg, self.longitude_deg])
        n = WGS84_A_KM / np.sqrt(1.0 - WGS84_E2 * np.sin(phi) ** 2)
        h = self.height_m / 1000.0
        return np.array(
            [
                (n + h) * np.cos(phi) * np.cos(lam),
                (n + h) * np.cos(phi) * np.sin(lam),
                (n * (1.0 - WGS84_E2) + h) * np.sin(phi),
            ]
        )

    def enu_basis(self) -> np.ndarray:
        """Rows are the east, north and up unit vectors in the Earth-fixed frame."""
        phi, lam = np.radians([self.latitude_deg, self.longitude_deg])
        east = np.array([-np.sin(lam), np.cos(lam), 0.0])
        north = np.array([-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)])
        up = np.array([np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)])
        return np.stack([east, north, up])

    def location(self) -> EarthLocation:
        return EarthLocation.from_geodetic(
            lon=self.longitude_deg * u.deg, lat=self.latitude_deg * u.deg, height=self.height_m * u.m
        )


# The array phase centre from SARAO's MeerKAT specifications page:
# 30° 42' 39.8" S, 21° 26' 38.0" E, 1086.6 m.
MEERKAT = Site(
    name="MeerKAT array phase centre",
    latitude_deg=-(30.0 + 42.0 / 60.0 + 39.8 / 3600.0),
    longitude_deg=21.0 + 26.0 / 60.0 + 38.0 / 3600.0,
    height_m=1086.6,
    dish_diameter_m=13.5,
    source="SARAO, MeerKAT specifications (skaafrica.atlassian.net, ESDKB page 277315585): "
    "array phase centre 30d42m39.8s S, 21d26m38.0s E, 1086.6 m; dish 13.5 m nominal",
)


@dataclass(frozen=True)
class Receiver:
    """One MeerKAT receiver: the digitised range the correlator sees, and the feed's design range."""

    name: str
    lo_mhz: float
    hi_mhz: float
    feed_lo_mhz: float | None
    feed_hi_mhz: float | None

    @property
    def centre_mhz(self) -> float:
        return 0.5 * (self.lo_mhz + self.hi_mhz)

    def overlaps(self, lo_mhz: float, hi_mhz: float) -> bool:
        """Whether ``[lo, hi]`` MHz falls at all inside the digitised band."""
        return lo_mhz < self.hi_mhz and hi_mhz > self.lo_mhz


# SARAO's specifications page: UHF 580-1015 MHz (544-1088 digitised), L 900-1670 (856-1712
# digitised), S-band in five 875 MHz sub-bands S0 to S4.
RECEIVERS: dict[str, Receiver] = {
    "UHF": Receiver("UHF", 544.0, 1088.0, 580.0, 1015.0),
    "L": Receiver("L", 856.0, 1712.0, 900.0, 1670.0),
    "S0": Receiver("S0", 1750.0, 2625.0, None, None),
    "S1": Receiver("S1", 1968.0, 2843.0, None, None),
    "S2": Receiver("S2", 2187.0, 3062.0, None, None),
    "S3": Receiver("S3", 2406.0, 3281.0, None, None),
    "S4": Receiver("S4", 2625.0, 3500.0, None, None),
}
RECEIVER_SOURCE = "SARAO, MeerKAT specifications (skaafrica.atlassian.net, ESDKB page 277315585)"


def receiver(name: str) -> Receiver:
    key = name.strip().upper()
    if key in ("S", "S-BAND"):
        key = "S0"
    if key not in RECEIVERS:
        raise KeyError(f"unknown receiver {name!r}; choose one of {', '.join(RECEIVERS)}")
    return RECEIVERS[key]


def beam_fwhm_deg(freq_mhz: float) -> float:
    """Half-power width of the primary beam in degrees at ``freq_mhz`` (see the module note)."""
    return (BEAM_FWHM_ARCMIN_AT_1500_MHZ / 60.0) * (BEAM_REFERENCE_MHZ / float(freq_mhz))


def beam_fwhm_lambda_over_d(dish_diameter_m: float = MEERKAT.dish_diameter_m) -> float:
    """The constant ``k`` in ``FWHM = k λ/D`` that the measured relation implies for this dish."""
    wavelength = 299792458.0 / (BEAM_REFERENCE_MHZ * 1e6)
    return np.radians(BEAM_FWHM_ARCMIN_AT_1500_MHZ / 60.0) / (wavelength / dish_diameter_m)


def angular_error_deg(residual_km, range_km) -> np.ndarray:
    """A position residual perpendicular to the line of sight, as an angle at the site."""
    return np.degrees(np.arctan2(np.abs(np.asarray(residual_km, dtype=float)), np.asarray(range_km, dtype=float)))


# --------------------------------------------------------------------------------------
# Earth rotation and the topocentric frame


def gmst_rad(times) -> np.ndarray:
    """Greenwich mean sidereal time (IAU 1982) at UTC ``times``, taking UTC for UT1."""
    jd, fr = julian_dates(to_datetime64(times))
    return np.asarray(erfa.gmst82(jd, fr), dtype=float)


def teme_to_pef(r_teme: np.ndarray, times) -> np.ndarray:
    """Rotate TEME vectors ``(..., m, 3)`` into the Earth-fixed frame at the ``m`` times."""
    theta = gmst_rad(times)
    c, s = np.cos(theta), np.sin(theta)
    r = np.asarray(r_teme, dtype=float)
    out = np.empty_like(r)
    out[..., 0] = c * r[..., 0] + s * r[..., 1]
    out[..., 1] = -s * r[..., 0] + c * r[..., 1]
    out[..., 2] = r[..., 2]
    return out


def pef_to_teme(r_pef: np.ndarray, times) -> np.ndarray:
    """The inverse of :func:`teme_to_pef`."""
    theta = gmst_rad(times)
    c, s = np.cos(theta), np.sin(theta)
    r = np.asarray(r_pef, dtype=float)
    out = np.empty_like(r)
    out[..., 0] = c * r[..., 0] - s * r[..., 1]
    out[..., 1] = s * r[..., 0] + c * r[..., 1]
    out[..., 2] = r[..., 2]
    return out


@dataclass
class Look:
    """Where an Earth-fixed position is seen from the site: range, elevation, azimuth, and the ENU direction."""

    range_km: np.ndarray
    elevation_deg: np.ndarray
    azimuth_deg: np.ndarray
    enu: np.ndarray


def look_from(site: Site, r_pef: np.ndarray) -> Look:
    """Topocentric range, elevation, azimuth and unit direction for Earth-fixed positions ``(..., 3)``."""
    d = np.asarray(r_pef, dtype=float) - site.ecef_km()
    enu = d @ site.enu_basis().T
    rng = np.linalg.norm(enu, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        unit = enu / rng[..., None]
    el = np.degrees(np.arctan2(enu[..., 2], np.hypot(enu[..., 0], enu[..., 1])))
    az = np.degrees(np.arctan2(enu[..., 0], enu[..., 1])) % 360.0
    return Look(rng, el, az, unit)


def enu_from_alt_az(alt_deg, az_deg) -> np.ndarray:
    """Unit vectors in the east-north-up frame from altitude and azimuth (north through east)."""
    alt = np.radians(np.asarray(alt_deg, dtype=float))
    az = np.radians(np.asarray(az_deg, dtype=float))
    return np.stack([np.cos(alt) * np.sin(az), np.cos(alt) * np.cos(az), np.sin(alt)], axis=-1)


def boresight(site: Site, ra_deg: float, dec_deg: float, times) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Altitude, azimuth (degrees) and ENU unit vectors of a J2000 direction at UTC ``times``, no refraction."""
    t = Time(to_datetime64(times), scale="utc")
    frame = AltAz(obstime=t, location=site.location(), pressure=0.0 * u.bar)
    with iers.conf.set_temp("iers_degraded_accuracy", "warn"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        altaz = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs").transform_to(frame)
    alt = np.atleast_1d(altaz.alt.to_value(u.deg))
    az = np.atleast_1d(altaz.az.to_value(u.deg))
    return alt, az, enu_from_alt_az(alt, az)


def sky_from_alt_az(site: Site, alt_deg, az_deg, times) -> tuple[np.ndarray, np.ndarray]:
    """J2000 right ascension and declination (degrees) of topocentric directions, no refraction."""
    t = Time(to_datetime64(times), scale="utc")
    frame = AltAz(
        alt=np.atleast_1d(alt_deg) * u.deg,
        az=np.atleast_1d(az_deg) * u.deg,
        obstime=t,
        location=site.location(),
        pressure=0.0 * u.bar,
    )
    with iers.conf.set_temp("iers_degraded_accuracy", "warn"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        icrs = SkyCoord(frame).transform_to(ICRS())
    return np.atleast_1d(icrs.ra.to_value(u.deg)), np.atleast_1d(icrs.dec.to_value(u.deg))


def separation_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Angle between unit vectors, stable near zero (chord rather than dot product)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    chord = np.linalg.norm(a - b, axis=-1)
    return np.degrees(2.0 * np.arcsin(np.clip(chord / 2.0, 0.0, 1.0)))


def sky_projection(unit: np.ndarray, line_of_sight: np.ndarray) -> np.ndarray:
    """How much of a unit direction lies across the line of sight: ``|u - (u.l) l|``, from 0 along it to 1 across."""
    unit = np.asarray(unit, dtype=float)
    los = np.asarray(line_of_sight, dtype=float)
    along = np.sum(unit * los, axis=-1, keepdims=True)
    return np.linalg.norm(unit - along * los, axis=-1)
