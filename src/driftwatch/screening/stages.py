"""Three-stage conjunction screening of a fleet against the catalogue.

Fleet against catalogue, never all against all: with ``P`` primaries and ``N`` catalogue
objects there are ``P x N`` pairs, and the three stages of Hoots, Crawford and Roehrich
(1984) throw pairs away as cheaply as possible before anything expensive is done.

**Stage A, geometry.** Two orbits cannot come within ``D`` of each other unless their
altitude shells overlap to within ``D``: the higher of the two perigees must be no more
than ``D`` above the lower of the two apogees. Apogee and perigee are read from the mean
elements, which differ from the osculating orbit by a few km, and the pad ``D`` (default
50 km) covers that, a week of drag decay, and the screening radius itself. Objects with
a mean perigee below 120 km are dropped as decaying: SGP4 is unreliable that low and the
object will be gone within days. Element sets older than five days are kept but flagged
stale.

**Stage B, coarse time stepping.** Every surviving pair's separation is sampled on a
common time grid with the vectorised SGP4 path. The step and the detection threshold
are chosen together so that no approach inside the screening radius ``R`` can fall
between samples: the separation ``d(t)`` cannot change faster than the relative speed,
``|d'(t)| <= |v_rel|``, so any minimum below ``R`` lies within half a step of a sample
where ``d <= R + v_max h / 2``. ``v_max`` is bounded per pair by the sum of the two
perigee speeds (``docs/screening.md`` has the derivation and the numbers). A candidate
is any consecutive pair of samples where the range rate changes sign from approaching
to receding while either sample is below the threshold; a sampled local minimum with no
sign change beside it is kept as a fallback candidate.

**Stage C, refinement.** For each candidate the time of closest approach is the root of
the range rate, ``f(t) = dr . dv`` (the derivative of ``d^2/2``), found by a bracketed
root finder with SGP4 evaluated at each trial time. Fallback candidates are minimised
directly. The result is the time of closest approach, the miss distance, the relative
speed and the miss vector in the primary's radial, in-track, cross-track frame.

Everything is in TEME. Nothing here knows about uncertainty; Step 3 adds covariance and
probability on top of the geometry this module produces.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sgp4.api import Satrec, SatrecArray

from driftwatch.fleet import Fleet
from driftwatch.orbit.propagator import WGS72_EARTH_RADIUS_KM, WGS72_MU_KM3_S2, build_satrecs
from driftwatch.orbit.time import julian_date, julian_dates, parse_utc
from driftwatch.screening.ric import ric_basis, to_ric

log = logging.getLogger(__name__)

# Categories whose members are known to manoeuvre: operated constellations and crewed
# stations. A heuristic, and a warning rather than a model: an active payload outside these
# categories may also manoeuvre, and nothing here predicts a burn.
MANOEUVRING_CATEGORIES: frozenset[str] = frozenset({"starlink", "oneweb", "constellation", "station"})

EVENT_COLUMNS: tuple[str, ...] = (
    "primary_norad_id",
    "primary_name",
    "primary_category",
    "secondary_norad_id",
    "secondary_name",
    "secondary_category",
    "tca",
    "miss_km",
    "rel_speed_kms",
    "miss_r_km",
    "miss_i_km",
    "miss_c_km",
    "in_box",
    "within_watch_radius",
    "stale_primary",
    "stale_secondary",
    "manoeuvrable_primary",
    "manoeuvrable_secondary",
    "secondary_ephemeris",
    "refine_method",
)


class ScreeningError(RuntimeError):
    """The screening cannot run as asked: a primary is missing from the snapshot or decaying."""


@dataclass(frozen=True)
class ScreeningConfig:
    """Everything configurable about a screening run. Defaults are the Phase 2 prompt's."""

    days: float = 7.0
    pad_km: float = 50.0
    decay_perigee_km: float = 120.0
    stale_days: float = 5.0
    step_s: float = 30.0
    box_ric_km: tuple[float, float, float] = (2.0, 25.0, 25.0)
    watch_radius_km: float = 25.0
    # Multiplies the per-pair bound on relative speed. SGP4 orbits are not exactly Keplerian,
    # so the perigee speed from mean elements is not an exact bound on the osculating speed.
    speed_margin: float = 1.02
    # Stage C stops when the bracket on the time of closest approach is narrower than this.
    time_tolerance_s: float = 1e-5
    # Stage B propagates in time chunks sized so the position and velocity arrays fit this.
    memory_budget_mb: float = 256.0

    @property
    def screening_radius_km(self) -> float:
        """The sphere that encloses both the box and the watch radius: what Stage B must not miss."""
        return max(float(self.watch_radius_km), float(np.linalg.norm(self.box_ric_km)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "days": self.days,
            "pad_km": self.pad_km,
            "decay_perigee_km": self.decay_perigee_km,
            "stale_days": self.stale_days,
            "step_s": self.step_s,
            "box_ric_km": list(self.box_ric_km),
            "watch_radius_km": self.watch_radius_km,
            "speed_margin": self.speed_margin,
            "time_tolerance_s": self.time_tolerance_s,
            "screening_radius_km": self.screening_radius_km,
        }


def perigee_speed_kms(perigee_km: np.ndarray, semi_major_axis_km: np.ndarray) -> np.ndarray:
    """Two-body speed at perigee from mean elements (vis-viva): the fastest point of the orbit.

    ``v^2 = mu (2 / r_p - 1 / a)``. The sum of two objects' perigee speeds bounds their
    relative speed at any time, since ``|v_s - v_p| <= |v_s| + |v_p|``.
    """
    r_p = np.asarray(perigee_km, dtype=float) + WGS72_EARTH_RADIUS_KM
    a = np.asarray(semi_major_axis_km, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        v2 = WGS72_MU_KM3_S2 * (2.0 / r_p - 1.0 / a)
        return np.sqrt(np.where(v2 > 0, v2, np.nan))


# --------------------------------------------------------------------------------------
# Stage A


@dataclass
class StageAResult:
    """Surviving pairs and per-object flags."""

    pairs: pd.DataFrame  # primary_norad_id, secondary_norad_id, speed_bound_kms
    objects: pd.DataFrame  # norad_id, epoch_age_days, stale, decaying, v_perigee_kms (every snapshot object)
    dropped_decaying: list[int]
    pairs_per_primary: dict[int, int]

    @property
    def secondary_ids(self) -> np.ndarray:
        return np.unique(self.pairs["secondary_norad_id"].to_numpy())


def stage_a(
    snapshot: pd.DataFrame, primaries: Sequence[int], config: ScreeningConfig, *, start: datetime
) -> StageAResult:
    """Apogee/perigee overlap filter with a pad; drop decaying objects; flag stale element sets.

    Uses only ``perigee_km``, ``apogee_km``, ``semi_major_axis_km`` and ``epoch``. The
    ``category`` and ``altitude_band`` labels play no part, by design (see
    ``docs/phase2-plan.md``), and a test permutes them to prove it.
    """
    ids = snapshot["norad_id"].to_numpy(dtype=np.int64)
    perigee = snapshot["perigee_km"].to_numpy(dtype=float)
    apogee = snapshot["apogee_km"].to_numpy(dtype=float)
    sma = snapshot["semi_major_axis_km"].to_numpy(dtype=float)
    epoch = pd.to_datetime(snapshot["epoch"], utc=True)
    start_ts = pd.Timestamp(parse_utc(start))
    age_days = ((start_ts - epoch).dt.total_seconds() / 86400.0).to_numpy()

    decaying = perigee < config.decay_perigee_km
    stale = age_days > config.stale_days
    v_peri = perigee_speed_kms(perigee, sma)
    objects = pd.DataFrame(
        {
            "norad_id": ids,
            "epoch_age_days": age_days,
            "stale": stale,
            "decaying": decaying,
            "v_perigee_kms": v_peri,
        }
    )

    row_of = {int(n): k for k, n in enumerate(ids)}
    frames = []
    per_primary: dict[int, int] = {}
    for p in primaries:
        p = int(p)
        if p not in row_of:
            raise ScreeningError(f"primary {p} is not in the snapshot")
        k = row_of[p]
        if decaying[k] or not np.isfinite(perigee[k]):
            raise ScreeningError(
                f"primary {p} has a mean perigee of {perigee[k]:.0f} km, below the {config.decay_perigee_km:.0f} km cut"
            )
        higher_perigee = np.maximum(perigee[k], perigee)
        lower_apogee = np.minimum(apogee[k], apogee)
        with np.errstate(invalid="ignore"):
            keep = (higher_perigee - lower_apogee <= config.pad_km) & ~decaying & (ids != p)
        keep &= np.isfinite(perigee) & np.isfinite(apogee)
        idx = np.nonzero(keep)[0]
        per_primary[p] = int(len(idx))
        frames.append(
            pd.DataFrame(
                {
                    "primary_norad_id": p,
                    "secondary_norad_id": ids[idx],
                    "speed_bound_kms": config.speed_margin * (v_peri[k] + v_peri[idx]),
                }
            )
        )
    pairs = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(
            {"primary_norad_id": pd.Series(dtype=np.int64), "secondary_norad_id": pd.Series(dtype=np.int64)}
        )
    )
    dropped = sorted(int(n) for n in ids[decaying])
    log.info(
        "Stage A: %d pairs over %d primaries (%s); %d objects dropped as decaying; %d element sets stale",
        len(pairs),
        len(per_primary),
        ", ".join(f"{p}: {n}" for p, n in per_primary.items()),
        len(dropped),
        int(stale.sum()),
    )
    return StageAResult(pairs, objects, dropped, per_primary)


# --------------------------------------------------------------------------------------
# Propagation helpers shared by Stages B and C


@dataclass
class Propagable:
    """SGP4 records for the objects a run needs (primaries plus Stage A survivors), in a fixed order."""

    norad_id: np.ndarray
    satrecs: list[Satrec]
    row: dict[int, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.row = {int(n): k for k, n in enumerate(self.norad_id)}

    @classmethod
    def from_snapshot(cls, snapshot: pd.DataFrame, ids: Sequence[int]) -> Propagable:
        wanted = np.asarray(sorted({int(i) for i in ids}), dtype=np.int64)
        sub = snapshot.drop_duplicates("norad_id").set_index("norad_id").loc[wanted].reset_index()
        return cls(wanted, build_satrecs(sub))


def _time_grid(start: datetime, config: ScreeningConfig) -> np.ndarray:
    """Sample times as ``datetime64[us]``: the window plus one step of padding either side.

    The padding gives every in-window sample a neighbour on both sides, so a minimum right
    at the start or end of the window can still be bracketed.
    """
    step_us = int(round(config.step_s * 1e6))
    n_in = int(np.ceil(config.days * 86400.0 / config.step_s)) + 1
    start64 = np.datetime64(parse_utc(start).replace(tzinfo=None), "us")
    k = np.arange(-1, n_in + 1, dtype=np.int64)
    return start64 + (k * step_us).astype("timedelta64[us]")


# --------------------------------------------------------------------------------------
# Stage B


@dataclass
class StageBResult:
    """Candidate brackets for Stage C, plus what it cost."""

    candidates: pd.DataFrame  # primary_norad_id, secondary_norad_id, t_lo, t_hi, d_sample_km, method
    times: np.ndarray  # the sample grid, datetime64[us]
    n_objects: int
    n_propagations: int


def stage_b(
    prop: Propagable, stage_a_result: StageAResult, config: ScreeningConfig, *, start: datetime
) -> StageBResult:
    """Coarse time stepping of relative distance with SatrecArray; returns brackets for Stage C.

    The per-pair threshold is ``R + v_bound h / 2`` with ``R`` the screening radius,
    ``v_bound`` the pair's speed bound from Stage A and ``h`` the step. A candidate is a
    sample interval where the range rate ``f = dr . dv`` goes from negative to
    non-negative while either end is under the threshold (``method="root"``), or a
    sampled local minimum under the threshold with no sign change beside it
    (``method="minimum"``).
    """
    times = _time_grid(start, config)
    jd, fr = julian_dates(times)
    n_t = len(times)
    n_obj = len(prop.satrecs)
    array = SatrecArray(prop.satrecs)
    radius = config.screening_radius_km
    half_step = 0.5 * config.step_s

    groups = []
    for p, sub in stage_a_result.pairs.groupby("primary_norad_id", sort=False):
        idx = np.fromiter((prop.row[int(s)] for s in sub["secondary_norad_id"]), dtype=np.int64, count=len(sub))
        threshold = radius + sub["speed_bound_kms"].to_numpy(dtype=float) * half_step
        groups.append((int(p), prop.row[int(p)], idx, threshold, sub["secondary_norad_id"].to_numpy(dtype=np.int64)))

    # Two (n_obj, chunk, 3) float64 arrays per chunk.
    chunk = max(8, int(config.memory_budget_mb * 1e6 // (n_obj * 48)))
    out: dict[str, list[np.ndarray]] = {k: [] for k in ("primary", "secondary", "j", "d_sample", "root")}
    n_prop = 0
    s = 0
    while s < n_t - 1:
        e = min(s + chunk, n_t - 1)  # sign changes for intervals (j, j+1), j in [s, e)
        lo, hi = max(s - 1, 0), min(e + 2, n_t)  # evaluate samples lo..hi-1 so j-1 and j+1 exist
        err, r, v = array.sgp4(jd[lo:hi], fr[lo:hi])
        n_prop += n_obj * (hi - lo)
        bad = err != 0
        if bad.any():
            r[bad] = np.nan
            v[bad] = np.nan
        j_sc = np.arange(s, e)
        c_sc = j_sc - lo
        j_lm = np.arange(max(s, 1), min(e, n_t - 1))
        c_lm = j_lm - lo
        for p, p_row, idx, threshold, sec_ids in groups:
            dr = r[idx] - r[p_row][None, :, :]
            dv = v[idx] - v[p_row][None, :, :]
            d = np.sqrt(np.einsum("kmi,kmi->km", dr, dr))
            f = np.einsum("kmi,kmi->km", dr, dv)
            below = d <= threshold[:, None]
            with np.errstate(invalid="ignore"):
                sign_change = (f[:, :-1] < 0) & (f[:, 1:] >= 0)
            hit = sign_change[:, c_sc] & (below[:, c_sc] | below[:, c_sc + 1])
            rows, cols = np.nonzero(hit)
            if len(rows):
                out["primary"].append(np.full(len(rows), p, dtype=np.int64))
                out["secondary"].append(sec_ids[rows])
                out["j"].append(j_sc[cols])
                out["d_sample"].append(np.minimum(d[rows, c_sc[cols]], d[rows, c_sc[cols] + 1]))
                out["root"].append(np.ones(len(rows), dtype=bool))
            if len(c_lm):
                with np.errstate(invalid="ignore"):
                    local_min = (
                        below[:, c_lm]
                        & (d[:, c_lm - 1] >= d[:, c_lm])
                        & (d[:, c_lm] < d[:, c_lm + 1])
                        & ~(sign_change[:, c_lm - 1] | sign_change[:, c_lm])
                    )
                rows, cols = np.nonzero(local_min)
                if len(rows):
                    out["primary"].append(np.full(len(rows), p, dtype=np.int64))
                    out["secondary"].append(sec_ids[rows])
                    out["j"].append(j_lm[cols])
                    out["d_sample"].append(d[rows, c_lm[cols]])
                    out["root"].append(np.zeros(len(rows), dtype=bool))
        s = e

    if out["primary"]:
        primary = np.concatenate(out["primary"])
        secondary = np.concatenate(out["secondary"])
        j = np.concatenate(out["j"])
        d_sample = np.concatenate(out["d_sample"])
        root = np.concatenate(out["root"])
    else:
        primary = secondary = j = np.zeros(0, dtype=np.int64)
        d_sample = np.zeros(0)
        root = np.zeros(0, dtype=bool)
    t_lo = np.where(root, times[j], times[np.maximum(j - 1, 0)])
    t_hi = times[np.minimum(j + 1, n_t - 1)]
    candidates = pd.DataFrame(
        {
            "primary_norad_id": primary,
            "secondary_norad_id": secondary,
            "t_lo": t_lo,
            "t_hi": t_hi,
            "d_sample_km": d_sample,
            "method": np.where(root, "root", "minimum"),
        }
    )
    log.info(
        "Stage B: %d samples x %d objects = %d propagations; %d candidates (%d sign changes, %d sampled minima)",
        n_t,
        n_obj,
        n_prop,
        len(candidates),
        int(root.sum()),
        int((~root).sum()),
    )
    return StageBResult(candidates, times, n_obj, n_prop)


# --------------------------------------------------------------------------------------
# Stage C


class PairEvaluator:
    """SGP4 states of candidate pairs at per-candidate times.

    Times are seconds from a reference instant, held as ``(jd0, fr0)``; the sgp4 library
    accepts a day fraction outside [0, 1), and a float64 offset of a week keeps
    nanosecond precision. Each primary is evaluated once per call with ``sgp4_array``
    over all of its candidates; each secondary with a scalar call.
    """

    def __init__(self, satrecs: list[Satrec], p_rows: Sequence[int], s_rows: Sequence[int], jd0: float, fr0: float):
        self.satrecs = satrecs
        self.s_rows = np.asarray(s_rows, dtype=np.int64)
        self.jd0 = float(jd0)
        self.fr0 = float(fr0)
        groups: dict[int, list[int]] = {}
        for k, row in enumerate(p_rows):
            groups.setdefault(int(row), []).append(k)
        self.groups = {row: np.asarray(ks, dtype=np.int64) for row, ks in groups.items()}
        self.n = len(p_rows)

    def states(self, t_s: np.ndarray, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """``(r_p, v_p, r_s, v_s)`` in km and km/s, ``(m, 3)`` each, for candidates ``idx`` at times ``t_s``."""
        idx = np.asarray(idx, dtype=np.int64)
        t_s = np.asarray(t_s, dtype=float)
        m = len(idx)
        fr = self.fr0 + t_s / 86400.0
        r_p = np.full((m, 3), np.nan)
        v_p = np.full((m, 3), np.nan)
        r_s = np.full((m, 3), np.nan)
        v_s = np.full((m, 3), np.nan)
        where = np.full(self.n, -1, dtype=np.int64)
        where[idx] = np.arange(m)
        for row, ks in self.groups.items():
            sel = where[ks]
            sel = sel[sel >= 0]
            if len(sel) == 0:
                continue
            err, rr, vv = self.satrecs[row].sgp4_array(np.full(len(sel), self.jd0), fr[sel])
            ok = err == 0
            r_p[sel[ok]] = rr[ok]
            v_p[sel[ok]] = vv[ok]
        jd0 = self.jd0
        satrecs = self.satrecs
        s_rows = self.s_rows
        for i in range(m):
            err, rr, vv = satrecs[s_rows[idx[i]]].sgp4(jd0, fr[i])
            if err == 0:
                r_s[i] = rr
                v_s[i] = vv
        return r_p, v_p, r_s, v_s

    def range_rate(self, t_s: np.ndarray, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """``f = dr . dv`` and ``|dv|^2`` (the scale that turns ``f`` into a time error)."""
        r_p, v_p, r_s, v_s = self.states(t_s, idx)
        dr = r_s - r_p
        dv = v_s - v_p
        return np.einsum("ki,ki->k", dr, dv), np.einsum("ki,ki->k", dv, dv)

    def distance(self, t_s: np.ndarray, idx: np.ndarray) -> np.ndarray:
        r_p, _, r_s, _ = self.states(t_s, idx)
        return np.linalg.norm(r_s - r_p, axis=1)


def vector_root(
    func: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]],
    a: np.ndarray,
    b: np.ndarray,
    fa: np.ndarray,
    fb: np.ndarray,
    *,
    tol: float,
    max_iter: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Roots of many bracketed functions at once: ``f(a) < 0 <= f(b)`` for each candidate.

    ``func(t, idx)`` returns ``(f, scale)`` for candidates ``idx`` at times ``t``; a
    candidate stops when its bracket is narrower than ``tol`` or ``|f| <= tol * scale``.
    Regula falsi with the Illinois modification (halve the retained endpoint's value when
    the same endpoint is kept twice running) plus Dekker's safeguard (bisect whenever the
    bracket has not halved over two iterations), so convergence is superlinear on smooth
    functions and never worse than twice bisection. Returns ``(t, converged)``; a
    candidate whose function returns NaN is abandoned with ``converged=False``.
    """
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    fa = np.array(fa, dtype=float)
    fb = np.array(fb, dtype=float)
    n = len(a)
    t = 0.5 * (a + b)
    valid = np.isfinite(a) & np.isfinite(b) & np.isfinite(fa) & np.isfinite(fb) & (fa < 0) & (fb >= 0) & (b >= a)
    converged = valid & ((b - a) <= tol)
    dead = ~valid
    last_side = np.zeros(n, dtype=np.int8)
    w_prev = b - a
    w_prev2 = b - a
    for _ in range(max_iter):
        idx = np.nonzero(~(converged | dead))[0]
        if len(idx) == 0:
            break
        aa, bb, faa, fbb = a[idx], b[idx], fa[idx], fb[idx]
        w = bb - aa
        with np.errstate(divide="ignore", invalid="ignore"):
            c = bb - fbb * (bb - aa) / (fbb - faa)
        force = ~np.isfinite(c) | (c <= aa) | (c >= bb) | (w > 0.5 * w_prev2[idx])
        c = np.where(force, 0.5 * (aa + bb), c)
        fc, scale = func(c, idx)
        fc = np.asarray(fc, dtype=float)
        scale = np.asarray(scale, dtype=float)
        bad = ~np.isfinite(fc)
        move_a = (fc < 0) & ~bad
        move_b = ~(fc < 0) & ~bad
        same_a = move_a & (last_side[idx] == 1)
        same_b = move_b & (last_side[idx] == -1)
        a[idx[move_a]] = c[move_a]
        fa[idx[move_a]] = fc[move_a]
        b[idx[move_b]] = c[move_b]
        fb[idx[move_b]] = fc[move_b]
        fb[idx[same_a & ~force]] *= 0.5
        fa[idx[same_b & ~force]] *= 0.5
        last_side[idx[move_a]] = 1
        last_side[idx[move_b]] = -1
        t[idx] = c
        dead[idx[bad]] = True
        with np.errstate(invalid="ignore"):
            done = ~bad & (((b[idx] - a[idx]) <= tol) | (np.abs(fc) <= tol * scale))
        converged[idx[done]] = True
        w_prev2[idx] = w_prev[idx]
        w_prev[idx] = b[idx] - a[idx]
    return t, converged


def vector_minimum(
    func: Callable[[np.ndarray, np.ndarray], np.ndarray],
    a: np.ndarray,
    b: np.ndarray,
    *,
    tol: float,
    max_iter: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Golden-section minimisation of many unimodal functions on ``[a, b]`` at once.

    ``func(t, idx)`` returns the values for candidates ``idx`` at times ``t``. Returns
    ``(t, converged)``; the bracket shrinks by 0.618 per evaluation, so a 60 s bracket
    reaches 1 ms in about 23 evaluations.
    """
    g = (np.sqrt(5.0) - 1.0) / 2.0
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    n = len(a)
    idx_all = np.arange(n)
    c = b - g * (b - a)
    d = a + g * (b - a)
    fc = np.asarray(func(c, idx_all), dtype=float) if n else np.zeros(0)
    fd = np.asarray(func(d, idx_all), dtype=float) if n else np.zeros(0)
    dead = ~(np.isfinite(fc) & np.isfinite(fd) & np.isfinite(a) & np.isfinite(b))
    for _ in range(max_iter):
        idx = np.nonzero(~dead & ((b - a) > tol))[0]
        if len(idx) == 0:
            break
        left = fc[idx] < fd[idx]
        li, ri = idx[left], idx[~left]
        b[li] = d[li]
        d[li] = c[li]
        fd[li] = fc[li]
        c[li] = b[li] - g * (b[li] - a[li])
        a[ri] = c[ri]
        c[ri] = d[ri]
        fc[ri] = fd[ri]
        d[ri] = a[ri] + g * (b[ri] - a[ri])
        new_t = np.concatenate([c[li], d[ri]])
        new_idx = np.concatenate([li, ri])
        vals = np.asarray(func(new_t, new_idx), dtype=float)
        fc[li] = vals[: len(li)]
        fd[ri] = vals[len(li) :]
        dead[new_idx[~np.isfinite(vals)]] = True
    t = np.where(fc < fd, c, d)
    return t, ~dead & ((b - a) <= tol)


@dataclass
class StageCResult:
    """Refined events (geometry only) and counts."""

    events: pd.DataFrame
    n_candidates: int
    n_root: int
    n_minimum: int
    n_unconverged: int


def stage_c(
    prop: Propagable, stage_b_result: StageBResult, config: ScreeningConfig, *, start: datetime, end: datetime
) -> StageCResult:
    """Refine every Stage B candidate to the time of closest approach and the miss geometry."""
    cand = stage_b_result.candidates
    n = len(cand)
    start_dt = parse_utc(start)
    start64 = np.datetime64(start_dt.replace(tzinfo=None), "us")
    window_s = (parse_utc(end) - start_dt).total_seconds()
    jd0, fr0 = julian_date(start_dt)
    empty = pd.DataFrame({c: pd.Series(dtype=t) for c, t in _GEOMETRY_DTYPES.items()})
    if n == 0:
        return StageCResult(empty, 0, 0, 0, 0)

    p_rows = [prop.row[int(p)] for p in cand["primary_norad_id"]]
    s_rows = [prop.row[int(s)] for s in cand["secondary_norad_id"]]
    ev = PairEvaluator(prop.satrecs, p_rows, s_rows, jd0, fr0)
    t_lo = (cand["t_lo"].to_numpy(dtype="datetime64[us]") - start64) / np.timedelta64(1, "s")
    t_hi = (cand["t_hi"].to_numpy(dtype="datetime64[us]") - start64) / np.timedelta64(1, "s")
    idx_all = np.arange(n)

    # Re-evaluate the bracket ends with the scalar path (bit-for-bit it can differ from the
    # array path in the last place), and send anything not properly bracketed to the minimiser.
    f_lo, _ = ev.range_rate(t_lo, idx_all)
    f_hi, _ = ev.range_rate(t_hi, idx_all)
    use_root = (cand["method"].to_numpy() == "root") & (f_lo < 0) & (f_hi >= 0)
    t = np.full(n, np.nan)
    ok = np.zeros(n, dtype=bool)
    root_idx = np.nonzero(use_root)[0]
    if len(root_idx):

        def f_root(tt: np.ndarray, sub: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            return ev.range_rate(tt, root_idx[sub])

        tr, cr = vector_root(
            f_root, t_lo[root_idx], t_hi[root_idx], f_lo[root_idx], f_hi[root_idx], tol=config.time_tolerance_s
        )
        t[root_idx] = tr
        ok[root_idx] = cr
    min_idx = np.nonzero(~use_root)[0]
    if len(min_idx):

        def f_min(tt: np.ndarray, sub: np.ndarray) -> np.ndarray:
            return ev.distance(tt, min_idx[sub])

        tm, cm = vector_minimum(f_min, t_lo[min_idx], t_hi[min_idx], tol=max(config.time_tolerance_s, 1e-3))
        t[min_idx] = tm
        ok[min_idx] = cm

    r_p, v_p, r_s, v_s = ev.states(np.where(np.isfinite(t), t, 0.0), idx_all)
    dr = r_s - r_p
    dv = v_s - v_p
    miss = np.linalg.norm(dr, axis=1)
    speed = np.linalg.norm(dv, axis=1)
    ric = to_ric(ric_basis(r_p, v_p), dr)
    box = np.asarray(config.box_ric_km, dtype=float)
    with np.errstate(invalid="ignore"):
        in_box = (np.abs(ric) <= box).all(axis=1)
        within = miss <= config.watch_radius_km
        keep = ok & np.isfinite(miss) & (in_box | within) & (t >= 0.0) & (t <= window_s)

    tca = start64 + np.round(np.where(np.isfinite(t), t, 0.0) * 1e6).astype("timedelta64[us]")
    events = pd.DataFrame(
        {
            "primary_norad_id": cand["primary_norad_id"].to_numpy(dtype=np.int64),
            "secondary_norad_id": cand["secondary_norad_id"].to_numpy(dtype=np.int64),
            "tca": tca,
            "miss_km": miss,
            "rel_speed_kms": speed,
            "miss_r_km": ric[:, 0],
            "miss_i_km": ric[:, 1],
            "miss_c_km": ric[:, 2],
            "in_box": in_box,
            "within_watch_radius": within,
            "refine_method": np.where(use_root, "root", "minimum"),
        }
    )[keep]
    # Two candidates can converge on the same minimum (a sign change and a neighbouring
    # sampled minimum, or two sign changes around a shallow root): keep one per second.
    key = events["tca"].to_numpy(dtype="datetime64[s]")
    events = events.assign(_key=key).sort_values(["primary_norad_id", "secondary_norad_id", "miss_km"])
    events = events.drop_duplicates(["primary_norad_id", "secondary_norad_id", "_key"]).drop(columns="_key")
    events = events.sort_values(["primary_norad_id", "tca"]).reset_index(drop=True)
    n_unconverged = int((~ok).sum())
    log.info(
        "Stage C: %d candidates refined (%d by root, %d by minimisation, %d did not converge); %d events "
        "within %.1f km or the %s km box",
        n,
        int(use_root.sum()),
        int((~use_root).sum()),
        n_unconverged,
        len(events),
        config.watch_radius_km,
        "x".join(f"{2 * x:g}" for x in config.box_ric_km),
    )
    return StageCResult(events, n, int(use_root.sum()), int((~use_root).sum()), n_unconverged)


_GEOMETRY_DTYPES: dict[str, Any] = {
    "primary_norad_id": np.int64,
    "secondary_norad_id": np.int64,
    "tca": "datetime64[us]",
    "miss_km": float,
    "rel_speed_kms": float,
    "miss_r_km": float,
    "miss_i_km": float,
    "miss_c_km": float,
    "in_box": bool,
    "within_watch_radius": bool,
    "refine_method": str,
}


# --------------------------------------------------------------------------------------
# The whole run


@dataclass
class ScreeningResult:
    """Everything a screening run produced: the events, the stage results and the timings."""

    events: pd.DataFrame
    start: datetime
    end: datetime
    config: ScreeningConfig
    stage_a: StageAResult
    stage_b: StageBResult
    stage_c: StageCResult
    timings_s: dict[str, float]

    def summary(self) -> dict[str, Any]:
        ev = self.events
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "pairs": int(len(self.stage_a.pairs)),
            "pairs_per_primary": self.stage_a.pairs_per_primary,
            "objects_propagated": self.stage_b.n_objects,
            "propagations": self.stage_b.n_propagations,
            "candidates": self.stage_c.n_candidates,
            "events": int(len(ev)),
            "events_in_box": int(ev["in_box"].sum()) if len(ev) else 0,
            "events_within_watch": int(ev["within_watch_radius"].sum()) if len(ev) else 0,
            "timings_s": {k: round(v, 2) for k, v in self.timings_s.items()},
        }


def default_start(snapshot: pd.DataFrame) -> datetime:
    """The screening start a snapshot implies: its fetch time, floored to the minute."""
    fetched = pd.to_datetime(snapshot["fetched_at"], utc=True).max().to_pydatetime()
    return fetched.replace(second=0, microsecond=0)


def screen_fleet(
    snapshot: pd.DataFrame,
    fleet: Fleet,
    *,
    config: ScreeningConfig | None = None,
    start: datetime | str | None = None,
) -> ScreeningResult:
    """Screen every fleet member against the snapshot over the window; the Step 2 entry point.

    ``snapshot`` may carry an ``ephemeris`` column from
    :func:`driftwatch.screening.supplemental.apply_supplemental`; otherwise every
    secondary is marked ``"gp"``. Raises :class:`ScreeningError` when a member is missing
    from the snapshot or sits below the decay cut: refusing beats silently dropping a
    primary.
    """
    config = config or ScreeningConfig()
    start_dt = parse_utc(start) if start is not None else default_start(snapshot)
    end_dt = start_dt + timedelta(days=config.days)
    timings: dict[str, float] = {}
    log.info(
        "Screening fleet %r (%d primaries) from %s for %g days",
        fleet.name,
        len(fleet),
        start_dt.isoformat(),
        config.days,
    )

    t0 = time.perf_counter()
    a = stage_a(snapshot, fleet.norad_ids, config, start=start_dt)
    timings["stage_a"] = time.perf_counter() - t0

    t1 = time.perf_counter()
    prop = Propagable.from_snapshot(snapshot, list(a.secondary_ids) + list(fleet.norad_ids))
    b = stage_b(prop, a, config, start=start_dt)
    timings["stage_b"] = time.perf_counter() - t1

    t2 = time.perf_counter()
    c = stage_c(prop, b, config, start=start_dt, end=end_dt)
    timings["stage_c"] = time.perf_counter() - t2

    events = annotate_events(c.events, snapshot, fleet, a)
    timings["total"] = time.perf_counter() - t0
    log.info(
        "Timings: Stage A %.1f s, Stage B %.1f s, Stage C %.1f s, total %.1f s",
        timings["stage_a"],
        timings["stage_b"],
        timings["stage_c"],
        timings["total"],
    )
    return ScreeningResult(events, start_dt, end_dt, config, a, b, c, timings)


def annotate_events(
    events: pd.DataFrame, snapshot: pd.DataFrame, fleet: Fleet, stage_a_result: StageAResult
) -> pd.DataFrame:
    """Add names, categories and the flags to Stage C's geometry, in ``EVENT_COLUMNS`` order."""
    by_id = snapshot.drop_duplicates("norad_id").set_index("norad_id")
    flags = stage_a_result.objects.set_index("norad_id")
    p = events["primary_norad_id"].to_numpy()
    s = events["secondary_norad_id"].to_numpy()
    ephemeris = by_id["ephemeris"] if "ephemeris" in by_id.columns else pd.Series("gp", index=by_id.index)
    fleet_flags = {m.norad_id: m.manoeuvres for m in fleet}
    fleet_names = {m.norad_id: m.name for m in fleet}
    sec_category = by_id["category"].reindex(s).to_numpy()
    out = events.copy()
    out["primary_name"] = [fleet_names.get(int(n), by_id["name"].get(n, "")) for n in p]
    out["primary_category"] = by_id["category"].reindex(p).to_numpy()
    out["secondary_name"] = by_id["name"].reindex(s).to_numpy()
    out["secondary_category"] = sec_category
    out["stale_primary"] = flags["stale"].reindex(p).to_numpy(dtype=bool)
    out["stale_secondary"] = flags["stale"].reindex(s).to_numpy(dtype=bool)
    out["manoeuvrable_primary"] = [bool(fleet_flags[int(n)]) for n in p]
    out["manoeuvrable_secondary"] = [
        bool(fleet_flags[int(n)]) if int(n) in fleet_flags else (str(cat) in MANOEUVRING_CATEGORIES)
        for n, cat in zip(s, sec_category, strict=True)
    ]
    out["secondary_ephemeris"] = ephemeris.reindex(s).fillna("gp").to_numpy()
    out["tca"] = pd.to_datetime(out["tca"], utc=True)
    return out[list(EVENT_COLUMNS)].reset_index(drop=True)
