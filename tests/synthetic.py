"""Test scaffolding: synthetic orbits and conjunctions with known geometry.

The screening tests need pairs of SGP4 orbits that pass each other at a chosen time and
distance. Building one is a two-step problem: choose the secondary's osculating state at
the encounter (position and velocity in TEME), then find SGP4 *mean* elements that
reproduce that state, since SGP4 only accepts mean elements. The second step is a
fixed-point iteration: SGP4's mean-to-osculating map is the identity plus small
periodic terms (of order J2, about a part in a thousand), so correcting the mean
elements by the observed osculating error converges quickly, to well under a metre
in a handful of iterations.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
from sgp4.api import Satrec

from driftwatch.orbit.propagator import WGS72_MU_KM3_S2, satrec_from_elements
from driftwatch.orbit.time import julian_date
from driftwatch.screening.ric import ric_basis

MU = WGS72_MU_KM3_S2
TWO_PI = 2.0 * np.pi


def keplerian_from_state(r: np.ndarray, v: np.ndarray) -> tuple[float, float, float, float, float, float]:
    """Osculating ``(a, e, i, raan, argp, M)`` from a state in km and km/s; angles in radians."""
    r = np.asarray(r, dtype=float)
    v = np.asarray(v, dtype=float)
    rn = np.linalg.norm(r)
    vn = np.linalg.norm(v)
    h = np.cross(r, v)
    h_hat = h / np.linalg.norm(h)
    n = np.cross([0.0, 0.0, 1.0], h)
    e_vec = ((vn**2 - MU / rn) * r - np.dot(r, v) * v) / MU
    e = float(np.linalg.norm(e_vec))
    a = 1.0 / (2.0 / rn - vn**2 / MU)
    i = float(np.arccos(np.clip(h[2] / np.linalg.norm(h), -1.0, 1.0)))
    raan = float(np.arctan2(n[1], n[0]) % TWO_PI)
    argp = float(np.arctan2(np.dot(np.cross(n, e_vec), h_hat), np.dot(n, e_vec)) % TWO_PI)
    nu = float(np.arctan2(np.dot(np.cross(e_vec, r), h_hat), np.dot(e_vec, r)) % TWO_PI)
    big_e = 2.0 * np.arctan2(np.sqrt(1.0 - e) * np.sin(nu / 2.0), np.sqrt(1.0 + e) * np.cos(nu / 2.0))
    m = float((big_e - e * np.sin(big_e)) % TWO_PI)
    return float(a), e, i, raan, argp, m


def satrec_from_kepler(
    norad_id: int, epoch: datetime, a: float, e: float, i: float, raan: float, argp: float, m: float, bstar: float = 0.0
) -> Satrec:
    """Initialise SGP4 from Keplerian elements in km and radians, treating them as mean elements."""
    n_rev_day = np.sqrt(MU / a**3) * 86400.0 / TWO_PI
    return satrec_from_elements(
        norad_id, epoch, n_rev_day, e, np.degrees(i), np.degrees(raan), np.degrees(argp), np.degrees(m), bstar
    )


def state_at(sat: Satrec, t: datetime) -> tuple[np.ndarray, np.ndarray]:
    jd, fr = julian_date(t)
    err, r, v = sat.sgp4(jd, fr)
    if err:
        raise RuntimeError(f"sgp4 error {err}")
    return np.array(r), np.array(v)


def _pack(a: float, e: float, i: float, raan: float, argp: float, m: float) -> np.ndarray:
    # Equinoctial-style variables so near-circular orbits iterate stably.
    return np.array([a, e * np.cos(argp), e * np.sin(argp), i, raan, (argp + m) % TWO_PI])


def _unpack(x: np.ndarray) -> tuple[float, float, float, float, float, float]:
    a, k, h, i, raan, lam = x
    e = float(np.hypot(k, h))
    argp = float(np.arctan2(h, k) % TWO_PI)
    return float(a), e, float(i), float(raan % TWO_PI), argp, float((lam - argp) % TWO_PI)


def _wrap(delta: np.ndarray) -> np.ndarray:
    out = delta.copy()
    for k in (4, 5):
        out[k] = (out[k] + np.pi) % TWO_PI - np.pi
    return out


def mean_elements_for_state(
    r: np.ndarray, v: np.ndarray, epoch: datetime, norad_id: int, *, bstar: float = 0.0, iterations: int = 12
) -> tuple[Satrec, float]:
    """SGP4 mean elements at ``epoch`` whose propagation to ``epoch`` gives the osculating state.

    Returns the initialised record and the residual position error in km.
    """
    target = _pack(*keplerian_from_state(r, v))
    est = target.copy()
    sat = None
    residual = np.inf
    for _ in range(iterations):
        sat = satrec_from_kepler(norad_id, epoch, *_unpack(est), bstar)
        r1, v1 = state_at(sat, epoch)
        residual = float(np.linalg.norm(r1 - np.asarray(r)))
        got = _pack(*keplerian_from_state(r1, v1))
        est = est + _wrap(target - got)
    assert sat is not None
    return sat, residual


def rotate(vec: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues rotation of ``vec`` about the unit vector ``axis`` by ``angle`` radians."""
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    c, s = np.cos(angle), np.sin(angle)
    return vec * c + np.cross(axis, vec) * s + axis * np.dot(axis, vec) * (1.0 - c)


def make_conjunction(
    primary: Satrec,
    t_star: datetime,
    *,
    miss_km: float,
    crossing_angle_deg: float,
    miss_direction_deg: float,
    norad_id: int,
    speed_ratio: float = 1.0,
) -> tuple[Satrec, dict[str, float]]:
    """A secondary that passes the primary at ``t_star`` with the given miss geometry.

    The secondary's velocity is the primary's rotated about the radial axis by the
    crossing angle (and scaled by ``speed_ratio``), and the miss vector lies in the plane
    perpendicular to the relative velocity, at ``miss_direction_deg`` from the radial
    direction. Because the miss vector is perpendicular to the relative velocity, the
    designed instant is a stationary point of the separation, so the time of closest
    approach of the SGP4 trajectories is ``t_star`` to within the (tiny) effect of
    differential gravity over the encounter.

    Returns the secondary's record (epoch ``t_star``) and the design values: the miss
    distance, the relative speed and the miss vector's RIC components in the primary's
    frame at ``t_star``.
    """
    r_p, v_p = state_at(primary, t_star)
    basis = ric_basis(r_p, v_p)[0]
    radial = basis[0]
    v_s = rotate(v_p, radial, np.radians(crossing_angle_deg)) * speed_ratio
    dv = v_s - v_p
    d_hat = dv / np.linalg.norm(dv)
    u1 = radial - np.dot(radial, d_hat) * d_hat
    u1 /= np.linalg.norm(u1)
    u2 = np.cross(d_hat, u1)
    phi = np.radians(miss_direction_deg)
    delta = miss_km * (np.cos(phi) * u1 + np.sin(phi) * u2)
    r_s = r_p + delta
    sat, residual = mean_elements_for_state(r_s, v_s, t_star, norad_id)
    assert residual < 1e-6, residual
    ric = basis @ delta
    design = {
        "miss_km": float(miss_km),
        "rel_speed_kms": float(np.linalg.norm(dv)),
        "miss_r_km": float(ric[0]),
        "miss_i_km": float(ric[1]),
        "miss_c_km": float(ric[2]),
    }
    return sat, design


def omm_record(sat: Satrec, name: str, epoch: datetime) -> dict:
    """An OMM dictionary (CelesTrak JSON shape) for a record built with ``sgp4init``."""
    return {
        "OBJECT_NAME": name,
        "OBJECT_ID": f"2000-{sat.satnum % 1000:03d}A",
        "EPOCH": epoch.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "MEAN_MOTION": sat.no_kozai * 1440.0 / TWO_PI,
        "ECCENTRICITY": sat.ecco,
        "INCLINATION": np.degrees(sat.inclo),
        "RA_OF_ASC_NODE": np.degrees(sat.nodeo),
        "ARG_OF_PERICENTER": np.degrees(sat.argpo),
        "MEAN_ANOMALY": np.degrees(sat.mo),
        "EPHEMERIS_TYPE": 0,
        "CLASSIFICATION_TYPE": "U",
        "NORAD_CAT_ID": int(sat.satnum),
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 1,
        "BSTAR": sat.bstar,
        "MEAN_MOTION_DOT": 0.0,
        "MEAN_MOTION_DDOT": 0.0,
    }


def random_leo(rng: np.random.Generator, norad_id: int, epoch: datetime) -> Satrec:
    """A random low Earth orbit: 400 to 900 km, e < 0.02, any inclination and orientation."""
    a = 6378.135 + rng.uniform(400.0, 900.0)
    e = rng.uniform(0.0, 0.02)
    i = np.radians(rng.uniform(5.0, 110.0))
    raan, argp, m = rng.uniform(0.0, TWO_PI, size=3)
    return satrec_from_kepler(norad_id, epoch, a, e, i, raan, argp, m, bstar=1e-4)
