"""Vectorised SGP4 propagation from snapshot mean elements.

Physics notes for the newcomer:

* A TLE or OMM record holds *mean* Keplerian elements: a smoothed orbit with the
  short-period wobbles from Earth's oblateness (J2) and other perturbations removed by
  the SGP4 theory itself. Feeding those elements to any propagator other than SGP4 gives
  a different, wrong orbit. This module therefore only ever hands them to the sgp4
  library, which is the reference C++ implementation of the theory.
* The output frame is TEME (True Equator, Mean Equinox), an inertial-ish frame peculiar
  to SGP4. See :mod:`driftwatch.orbit.frames` for getting into an Earth-fixed frame.
* Constants are WGS72, because that is what the catalogue's element sets are fitted
  against. Using WGS84 would not make positions more accurate; it would make them
  inconsistent with the elements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import pi

import numpy as np
import pandas as pd
from sgp4.api import WGS72, Satrec, SatrecArray

from driftwatch.orbit.time import UNIX_EPOCH_JD, US_PER_DAY, julian_date, julian_dates, to_datetime64

# radiusearthkm and mu for WGS72, as used by the sgp4 library. Used only to turn the
# library's mean semi-major axis (in Earth radii) into kilometres.
WGS72_EARTH_RADIUS_KM = 6378.135
WGS72_MU_KM3_S2 = 398600.8

# Days between the SGP4 epoch origin (1949 December 31 00:00 UT) and JD 0.
SGP4_EPOCH_ORIGIN_JD = 2433281.5

# rev/day -> rad/min, rev/day^2 -> rad/min^2, rev/day^3 -> rad/min^3
_REV_PER_DAY_TO_RAD_PER_MIN = 2.0 * pi / 1440.0
_REV_PER_DAY2_TO_RAD_PER_MIN2 = 2.0 * pi / (1440.0**2)
_REV_PER_DAY3_TO_RAD_PER_MIN3 = 2.0 * pi / (1440.0**3)

SGP4_ERRORS: dict[int, str] = {
    0: "ok",
    1: "mean eccentricity outside 0 <= e < 1",
    2: "mean motion less than zero",
    3: "perturbed eccentricity outside 0 <= e < 1",
    4: "semi-latus rectum less than zero",
    5: "epoch elements are sub-orbital",
    6: "satellite has decayed",
}


def satrec_from_elements(
    norad_id: int,
    epoch: datetime,
    mean_motion: float,
    eccentricity: float,
    inclination_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    bstar: float,
    mean_motion_dot: float = 0.0,
    mean_motion_ddot: float = 0.0,
    *,
    whichconst=WGS72,
    opsmode: str = "i",
) -> Satrec:
    """Initialise an sgp4 ``Satrec`` from OMM-style mean elements.

    Units follow the OMM/TLE conventions: mean motion in revolutions per day, angles in
    degrees, ``bstar`` in inverse Earth radii, and the mean-motion derivatives in the TLE
    convention (first derivative already divided by two, second by six, in rev/day^2 and
    rev/day^3). SGP4 ignores both derivatives; drag enters only through ``bstar``.
    """
    jd, fr = julian_date(epoch)
    sat = Satrec()
    sat.sgp4init(
        whichconst,
        opsmode,
        int(norad_id),
        (jd - SGP4_EPOCH_ORIGIN_JD) + fr,
        float(bstar),
        float(mean_motion_dot) * _REV_PER_DAY2_TO_RAD_PER_MIN2,
        float(mean_motion_ddot) * _REV_PER_DAY3_TO_RAD_PER_MIN3,
        float(eccentricity),
        np.deg2rad(float(arg_perigee_deg)),
        np.deg2rad(float(inclination_deg)),
        np.deg2rad(float(mean_anomaly_deg)),
        float(mean_motion) * _REV_PER_DAY_TO_RAD_PER_MIN,
        np.deg2rad(float(raan_deg)),
    )
    return sat


def build_satrecs(snapshot: pd.DataFrame) -> list[Satrec]:
    """Build one ``Satrec`` per row of a snapshot frame (see ``docs/data-schema.md``)."""
    epochs = pd.to_datetime(snapshot["epoch"], utc=True)
    cols = (
        snapshot["norad_id"].to_numpy(),
        epochs.dt.to_pydatetime(),
        snapshot["mean_motion"].to_numpy(),
        snapshot["eccentricity"].to_numpy(),
        snapshot["inclination_deg"].to_numpy(),
        snapshot["raan_deg"].to_numpy(),
        snapshot["arg_perigee_deg"].to_numpy(),
        snapshot["mean_anomaly_deg"].to_numpy(),
        snapshot["bstar"].to_numpy(),
        snapshot["mean_motion_dot"].to_numpy(),
        snapshot["mean_motion_ddot"].to_numpy(),
    )
    return [satrec_from_elements(*row) for row in zip(*cols, strict=True)]


def mean_orbit_geometry(satrecs: list[Satrec]) -> pd.DataFrame:
    """Mean semi-major axis, apogee and perigee (km) from initialised records.

    These are Brouwer mean values recovered by the sgp4 library at initialisation, not
    osculating values, so they can differ from the instantaneous orbit by several km.
    Good for filtering and altitude bands; not for anything precise.
    """
    a = np.array([s.a for s in satrecs]) * WGS72_EARTH_RADIUS_KM
    alta = np.array([s.alta for s in satrecs]) * WGS72_EARTH_RADIUS_KM
    altp = np.array([s.altp for s in satrecs]) * WGS72_EARTH_RADIUS_KM
    return pd.DataFrame({"semi_major_axis_km": a, "apogee_km": alta, "perigee_km": altp})


@dataclass
class PropagatedState:
    """SGP4 output for ``n`` objects at ``m`` times in the TEME frame.

    ``r_teme`` and ``v_teme`` have shape ``(n, m, 3)`` in km and km/s. ``error`` has
    shape ``(n, m)`` with the sgp4 error code (see :data:`SGP4_ERRORS`); positions for
    non-zero codes are NaN and must not be used.
    """

    norad_id: np.ndarray
    times: np.ndarray
    r_teme: np.ndarray
    v_teme: np.ndarray
    error: np.ndarray

    @property
    def single(self) -> bool:
        return self.times.shape[0] == 1

    def at_index(self, k: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """``(r, v, error)`` for time index ``k`` with shapes ``(n, 3)``, ``(n, 3)``, ``(n,)``."""
        return self.r_teme[:, k, :], self.v_teme[:, k, :], self.error[:, k]


def _propagate_jd(
    satrecs: list[Satrec], norad_id: np.ndarray, jd: np.ndarray, fr: np.ndarray, times64: np.ndarray | None = None
) -> PropagatedState:
    """Propagate to Julian dates given as ``(jd, fr)`` arrays; the datetime-free core.

    Kept separate so the verification test can drive it with exactly the same split
    Julian dates the library's own tests use.
    """
    jd = np.atleast_1d(np.asarray(jd, dtype=np.float64))
    fr = np.atleast_1d(np.asarray(fr, dtype=np.float64))
    if times64 is None:
        us = np.rint(((jd - UNIX_EPOCH_JD) + fr) * US_PER_DAY).astype("int64")
        times64 = us.astype("datetime64[us]")
    array = SatrecArray(satrecs)
    error, r, v = array.sgp4(jd, fr)
    error = error.astype(np.int8)
    bad = error != 0
    if bad.any():
        r = r.copy()
        v = v.copy()
        r[bad] = np.nan
        v[bad] = np.nan
    return PropagatedState(np.asarray(norad_id), times64, r, v, error)


def propagate_satrecs(satrecs: list[Satrec], norad_id: np.ndarray, times) -> PropagatedState:
    """Propagate initialised records to one or more UTC times using the vectorised C++ path."""
    times64 = to_datetime64(times)
    jd, fr = julian_dates(times64)
    return _propagate_jd(satrecs, norad_id, jd, fr, times64)


def propagate_snapshot(snapshot: pd.DataFrame, times) -> PropagatedState:
    """Build records from a snapshot and propagate them. See :func:`propagate_satrecs`."""
    satrecs = build_satrecs(snapshot)
    return propagate_satrecs(satrecs, snapshot["norad_id"].to_numpy(), times)


def error_summary(error: np.ndarray) -> dict[str, int]:
    """Count objects per SGP4 error message."""
    codes, counts = np.unique(np.asarray(error).ravel(), return_counts=True)
    return {SGP4_ERRORS.get(int(c), f"code {int(c)}"): int(n) for c, n in zip(codes, counts, strict=True)}
