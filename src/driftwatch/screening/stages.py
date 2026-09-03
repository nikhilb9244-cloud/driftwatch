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

Where an operator's published states are used instead of the element set, both the shell
and the speed bound are **widened to whatever those states actually reach**, because both
have to bound the trajectory the later stages screen on rather than a different one.
Measured over 300 Starlink files on 2026-09-03, the published trajectory leaves the
mean-element shell by a median 7.6 km and by up to 32.6 km for a satellite raising its
orbit. The pad's slack over the 35.4 km screening radius is only 14.6 km, so the excursion
is not something the pad absorbs; using the trajectory's own reach removes the question
rather than padding it.

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
root finder with the trajectory evaluated at each trial time. Fallback candidates are
minimised directly. The result is the time of closest approach, the miss distance, the
relative speed and the miss vector in the primary's radial, in-track, cross-track frame.

**The served trajectory (Phase 4 Step 1).** Where an operator has published states for an
object -- SpaceX's Starlink ephemerides, ``ephemeris/spacex.py`` -- those states are
interpolated and used in place of SGP4, in **both** Stage B and Stage C. Both, not just
Stage C, because the two trajectories are not close: measured on 2026-09-03 the SGP4 fit
sits a median 0.30 km from the ephemeris inside 12 hours but 28 km at 36 to 48 hours and
83 km at 60 to 72. Screening on one and refining on the other would choose pairs by a
trajectory tens of kilometres from the one they are then scored on, and no pad this side
of absurdity covers that.

That leaves the switch itself. An object's published states cover part of the window and
not the rest, and they are split at every discontinuity in the file, so the served
trajectory has a small number of instants -- at most three per object per run: the start
of coverage, the 48-hour seam, the 72-hour horizon -- where it jumps. Stage B's no-miss
argument rests on ``|d'(t)| <= |v_rel|``, which a jump breaks. Every sample interval
holding a jump is therefore marked, and on a marked interval the detection threshold is
**doubled**, from ``R + v h / 2`` to ``R + v h``, because only one of the two endpoint
samples lies on each side of the jump and a one-sided bound needs the whole step rather
than half of it. A candidate on a marked interval is refined by scanning the interval
rather than by root finding, since a discontinuous function has neither a bracketed root
nor a unimodal minimum, and the event carries ``refine_method="scan"`` so it can be
counted. ``docs/screening.md`` re-derives the guarantee with the jump in it.

Everything is in TEME. Nothing here knows about uncertainty: Step 3 adds covariance and
probability on top of the geometry this module produces, and to keep the two apart every
event carries both objects' TEME states at the time of closest approach, so the risk
step never propagates an orbit and a scenario can be rescored without rescreening.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from sgp4.api import Satrec, SatrecArray

from driftwatch.fleet import Fleet
from driftwatch.orbit.propagator import WGS72_EARTH_RADIUS_KM, WGS72_MU_KM3_S2, build_satrecs
from driftwatch.orbit.time import julian_date, julian_dates, parse_utc, stamp
from driftwatch.risk.manoeuvre import manoeuvre_prior
from driftwatch.screening.ric import ric_basis, to_ric

if TYPE_CHECKING:  # a type-only import: importing it for real would close a cycle
    # through risk.covariance, which reaches back into this package for the RIC basis.
    from driftwatch.ephemeris.spacex import EphemerisTrajectory

log = logging.getLogger(__name__)

# Both objects' TEME states at the time of closest approach: position in km, velocity in km/s.
STATE_COLUMNS: tuple[str, ...] = tuple(
    f"{who}_{comp}" for who in ("p", "s") for comp in ("x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms")
)

EVENT_COLUMNS: tuple[str, ...] = (
    "event_id",
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
    "manoeuvre_primary",
    "manoeuvre_secondary",
    "secondary_ephemeris",
    "primary_trajectory",
    "secondary_trajectory",
    "refine_method",
    *STATE_COLUMNS,
)

# What produced an object's state at the time of closest approach: its element set through
# SGP4, or the operator's own published ephemeris interpolated (Phase 4 Step 1).
TRAJECTORY_SGP4 = "sgp4"
TRAJECTORY_EPHEMERIS = "spacex-ephemeris"
# How finely a candidate spanning a trajectory jump is scanned, as a fraction of the step.
SCAN_SUBDIVISIONS = 100


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
    snapshot: pd.DataFrame,
    primaries: Sequence[int],
    config: ScreeningConfig,
    *,
    start: datetime,
    reach: Mapping[int, tuple[float, float, float]] | None = None,
) -> StageAResult:
    """Apogee/perigee overlap filter with a pad; drop decaying objects; flag stale element sets.

    Uses only ``perigee_km``, ``apogee_km``, ``semi_major_axis_km`` and ``epoch``. The
    ``category`` and ``altitude_band`` labels play no part, by design (see
    ``docs/phase2-plan.md``), and a test permutes them to prove it.

    ``reach`` describes the published states that will actually serve an object:
    ``{norad id: (lowest km, highest km, fastest km/s)}``, from
    :meth:`driftwatch.ephemeris.spacex.EphemerisTrajectory.reach`. Both of Stage A's tests are
    widened by it and neither is ever narrowed -- the union with the mean-element values is
    taken -- because outside the ephemeris's coverage the element set still serves and has to
    be bounded too.
    """
    ids = snapshot["norad_id"].to_numpy(dtype=np.int64)
    # Copies, not views: the widening below writes into them, and a frame column can hand back
    # read-only memory.
    perigee = np.array(snapshot["perigee_km"], dtype=float)
    apogee = np.array(snapshot["apogee_km"], dtype=float)
    sma = snapshot["semi_major_axis_km"].to_numpy(dtype=float)
    n_widened = 0
    published_speed: dict[int, float] = {}
    if reach:
        row_for = {int(n): k for k, n in enumerate(ids)}
        for norad_id, (low, high, fastest) in reach.items():
            k = row_for.get(int(norad_id))
            if k is None or not (np.isfinite(low) and np.isfinite(high)):
                continue
            if low < perigee[k] or high > apogee[k]:
                n_widened += 1
            perigee[k] = min(perigee[k], float(low))
            apogee[k] = max(apogee[k], float(high))
            if np.isfinite(fastest):
                published_speed[k] = float(fastest)
    epoch = pd.to_datetime(snapshot["epoch"], utc=True)
    start_ts = pd.Timestamp(parse_utc(start))
    age_days = ((start_ts - epoch).dt.total_seconds() / 86400.0).to_numpy()

    decaying = perigee < config.decay_perigee_km
    stale = age_days > config.stale_days
    # The speed bound comes from the mean elements, and from the published states where there
    # are any: the largest speed those states actually show is an exact bound over the span
    # they cover, while the vis-viva value covers the rest of the window. The larger wins.
    v_peri = perigee_speed_kms(snapshot["perigee_km"].to_numpy(dtype=float), sma)
    for k, fastest in published_speed.items():
        if not np.isfinite(v_peri[k]) or fastest > v_peri[k]:
            v_peri[k] = fastest
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
        "Stage A: %d pairs over %d primaries (%s); %d objects dropped as decaying; %d element sets stale; "
        "%d shells widened to the published trajectory's own reach",
        len(pairs),
        len(per_primary),
        ", ".join(f"{p}: {n}" for p, n in per_primary.items()),
        len(dropped),
        int(stale.sum()),
        n_widened,
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
# The served trajectory


class ServedTrajectory:
    """SGP4, with an operator's published states substituted wherever they reach.

    Holds, for the objects a run propagates, which rows of a :class:`Propagable` have
    published states and where those states cover the sample grid. Everything the two stages
    have to agree about lives here, so that "which trajectory served this object at this
    time" has exactly one answer in a run.
    """

    def __init__(self, prop: Propagable, ephemeris: EphemerisTrajectory | None, times: np.ndarray) -> None:
        self.ephemeris = ephemeris
        self.times = times
        self.rows: dict[int, int] = {}  # prop row -> norad id
        self.served: dict[int, np.ndarray] = {}  # prop row -> covered, per sample
        self.jumps: dict[int, np.ndarray] = {}  # prop row -> the trajectory jumps inside interval j
        if ephemeris is None or not len(ephemeris):
            return
        for row, norad_id in enumerate(prop.norad_id):
            if int(norad_id) not in ephemeris:
                continue
            covered = ephemeris.covers(int(norad_id), times)
            if not covered.any():
                continue
            self.rows[row] = int(norad_id)
            self.served[row] = covered
            self.jumps[row] = covered[:-1] != covered[1:]

    def __bool__(self) -> bool:
        return bool(self.rows)

    def substitute(self, times: np.ndarray, r: np.ndarray, v: np.ndarray, offset: int) -> None:
        """Overwrite ``r`` and ``v`` in place for every row an ephemeris covers.

        ``r`` and ``v`` are ``(n_obj, n_chunk, 3)`` over ``times``, which begin at sample
        ``offset`` of the run's grid.
        """
        for row, norad_id in self.rows.items():
            covered = self.served[row][offset : offset + len(times)]
            if not covered.any():
                continue
            r_e, v_e, ok = self.ephemeris.states(norad_id, times[covered])  # type: ignore[union-attr]
            sel = np.nonzero(covered)[0][ok]
            r[row, sel] = r_e[ok]
            v[row, sel] = v_e[ok]

    def states_at(self, norad_id: int, at: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The published states at arbitrary times, and which of them the ephemeris reached."""
        if self.ephemeris is None:
            n = np.asarray(at).size
            return np.full((n, 3), np.nan), np.full((n, 3), np.nan), np.zeros(n, dtype=bool)
        return self.ephemeris.states(int(norad_id), at)

    def jump_intervals(self, row: int) -> np.ndarray | None:
        """Which sample intervals hold a jump for this row, or ``None`` where it has no ephemeris."""
        return self.jumps.get(row)

    def label(self, norad_id: int, at: np.ndarray) -> np.ndarray:
        """``sgp4`` or ``spacex-ephemeris`` per requested time, for the events table."""
        at64 = np.asarray(at, dtype="datetime64[us]")
        if self.ephemeris is None or int(norad_id) not in self.ephemeris:
            return np.full(at64.shape, TRAJECTORY_SGP4, dtype=object)
        covered = self.ephemeris.covers(int(norad_id), at64)
        return np.where(covered, TRAJECTORY_EPHEMERIS, TRAJECTORY_SGP4).astype(object)

    def summary(self) -> dict[str, Any]:
        if not self.rows:
            return {"objects": 0}
        served = np.array([int(c.sum()) for c in self.served.values()])
        return {
            "objects": len(self.rows),
            "samples_served": int(served.sum()),
            "samples_per_object_median": float(np.median(served)),
            "jump_intervals": int(sum(int(d.sum()) for d in self.jumps.values())),
        }


def pair_jumps(served: ServedTrajectory, p_row: int, s_rows: np.ndarray, intervals: np.ndarray) -> np.ndarray:
    """Which ``(secondary, interval)`` cells hold a jump in either object's served trajectory."""
    out = np.zeros((len(s_rows), len(intervals)), dtype=bool)
    if not served or not len(intervals):
        return out
    primary = served.jump_intervals(int(p_row))
    if primary is not None:
        out |= primary[intervals][None, :]
    for k, row in enumerate(s_rows):
        secondary = served.jump_intervals(int(row))
        if secondary is not None:
            out[k] |= secondary[intervals]
    return out


# --------------------------------------------------------------------------------------
# Stage B


@dataclass
class StageBResult:
    """Candidate brackets for Stage C, plus what it cost."""

    candidates: pd.DataFrame  # primary_norad_id, secondary_norad_id, t_lo, t_hi, d_sample_km, method
    times: np.ndarray  # the sample grid, datetime64[us]
    n_objects: int
    n_propagations: int
    served: ServedTrajectory | None = None


def stage_b(
    prop: Propagable,
    stage_a_result: StageAResult,
    config: ScreeningConfig,
    *,
    start: datetime,
    ephemeris: EphemerisTrajectory | None = None,
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
    served = ServedTrajectory(prop, ephemeris, times)
    if served:
        log.info("Stage B: served trajectory: %s", served.summary())

    groups = []
    for p, sub in stage_a_result.pairs.groupby("primary_norad_id", sort=False):
        idx = np.fromiter((prop.row[int(s)] for s in sub["secondary_norad_id"]), dtype=np.int64, count=len(sub))
        threshold = radius + sub["speed_bound_kms"].to_numpy(dtype=float) * half_step
        groups.append((int(p), prop.row[int(p)], idx, threshold, sub["secondary_norad_id"].to_numpy(dtype=np.int64)))

    # Two (n_obj, chunk, 3) float64 arrays per chunk.
    chunk = max(8, int(config.memory_budget_mb * 1e6 // (n_obj * 48)))
    out: dict[str, list[np.ndarray]] = {k: [] for k in ("primary", "secondary", "j", "d_sample", "root", "jump")}
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
        served.substitute(times[lo:hi], r, v, lo)
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
            # Twice the reach, for the intervals where only one endpoint is on the near side
            # of a trajectory jump: threshold is R + v h / 2, and this is R + v h.
            wide = d <= (2.0 * threshold - radius)[:, None]
            jump_sc = pair_jumps(served, p_row, idx, j_sc)
            with np.errstate(invalid="ignore"):
                sign_change = (f[:, :-1] < 0) & (f[:, 1:] >= 0)
            hit = sign_change[:, c_sc] & (below[:, c_sc] | below[:, c_sc + 1]) & ~jump_sc
            rows, cols = np.nonzero(hit)
            if len(rows):
                out["primary"].append(np.full(len(rows), p, dtype=np.int64))
                out["secondary"].append(sec_ids[rows])
                out["j"].append(j_sc[cols])
                out["d_sample"].append(np.minimum(d[rows, c_sc[cols]], d[rows, c_sc[cols] + 1]))
                out["root"].append(np.ones(len(rows), dtype=bool))
                out["jump"].append(np.zeros(len(rows), dtype=bool))
            if jump_sc.any():
                rows, cols = np.nonzero(jump_sc & (wide[:, c_sc] | wide[:, c_sc + 1]))
                if len(rows):
                    out["primary"].append(np.full(len(rows), p, dtype=np.int64))
                    out["secondary"].append(sec_ids[rows])
                    out["j"].append(j_sc[cols])
                    out["d_sample"].append(np.minimum(d[rows, c_sc[cols]], d[rows, c_sc[cols] + 1]))
                    out["root"].append(np.zeros(len(rows), dtype=bool))
                    out["jump"].append(np.ones(len(rows), dtype=bool))
            if len(c_lm):
                # A sampled minimum is bracketed by the two intervals either side of it, so it
                # is only usable when neither of them holds a jump.
                safe = ~(pair_jumps(served, p_row, idx, j_lm - 1) | pair_jumps(served, p_row, idx, j_lm))
                with np.errstate(invalid="ignore"):
                    local_min = (
                        below[:, c_lm]
                        & (d[:, c_lm - 1] >= d[:, c_lm])
                        & (d[:, c_lm] < d[:, c_lm + 1])
                        & ~(sign_change[:, c_lm - 1] | sign_change[:, c_lm])
                    )
                rows, cols = np.nonzero(local_min & safe)
                if len(rows):
                    out["primary"].append(np.full(len(rows), p, dtype=np.int64))
                    out["secondary"].append(sec_ids[rows])
                    out["j"].append(j_lm[cols])
                    out["d_sample"].append(d[rows, c_lm[cols]])
                    out["root"].append(np.zeros(len(rows), dtype=bool))
                    out["jump"].append(np.zeros(len(rows), dtype=bool))
        s = e

    if out["primary"]:
        primary = np.concatenate(out["primary"])
        secondary = np.concatenate(out["secondary"])
        j = np.concatenate(out["j"])
        d_sample = np.concatenate(out["d_sample"])
        root = np.concatenate(out["root"])
        jump = np.concatenate(out["jump"])
    else:
        primary = secondary = j = np.zeros(0, dtype=np.int64)
        d_sample = np.zeros(0)
        root = jump = np.zeros(0, dtype=bool)
    t_lo = np.where(root | jump, times[j], times[np.maximum(j - 1, 0)])
    t_hi = times[np.minimum(j + 1, n_t - 1)]
    candidates = pd.DataFrame(
        {
            "primary_norad_id": primary,
            "secondary_norad_id": secondary,
            "t_lo": t_lo,
            "t_hi": t_hi,
            "d_sample_km": d_sample,
            "method": np.where(jump, "scan", np.where(root, "root", "minimum")),
        }
    )
    log.info(
        "Stage B: %d samples x %d objects = %d propagations; %d candidates "
        "(%d sign changes, %d sampled minima, %d across a trajectory jump)",
        n_t,
        n_obj,
        n_prop,
        len(candidates),
        int(root.sum()),
        int((~root & ~jump).sum()),
        int(jump.sum()),
    )
    return StageBResult(candidates, times, n_obj, n_prop, served)


# --------------------------------------------------------------------------------------
# Stage C


class PairEvaluator:
    """States of candidate pairs at per-candidate times: SGP4, or the published ephemeris.

    Times are seconds from a reference instant, held as ``(jd0, fr0)``; the sgp4 library
    accepts a day fraction outside [0, 1), and a float64 offset of a week keeps
    nanosecond precision. Each primary is evaluated once per call with ``sgp4_array``
    over all of its candidates; each secondary with a scalar call.

    Where a :class:`ServedTrajectory` covers an object at a trial time, the interpolated
    published state replaces the SGP4 one -- the same substitution Stage B made, by the same
    rule, so that a pair chosen on one trajectory is refined on it too.
    """

    def __init__(
        self,
        satrecs: list[Satrec],
        p_rows: Sequence[int],
        s_rows: Sequence[int],
        jd0: float,
        fr0: float,
        *,
        served: ServedTrajectory | None = None,
        start64: np.datetime64 | None = None,
        norad_of_row: Mapping[int, int] | None = None,
    ):
        self.satrecs = satrecs
        self.p_rows = np.asarray(p_rows, dtype=np.int64)
        self.s_rows = np.asarray(s_rows, dtype=np.int64)
        self.jd0 = float(jd0)
        self.fr0 = float(fr0)
        self.served = served if (served is not None and served) else None
        self.start64 = start64
        self.norad_of_row = dict(norad_of_row or {})
        groups: dict[int, list[int]] = {}
        for k, row in enumerate(p_rows):
            groups.setdefault(int(row), []).append(k)
        self.groups = {row: np.asarray(ks, dtype=np.int64) for row, ks in groups.items()}
        self.n = len(p_rows)

    def _substitute(self, t_s: np.ndarray, rows: np.ndarray, r: np.ndarray, v: np.ndarray) -> None:
        """Replace SGP4 states with interpolated published ones wherever the ephemeris reaches."""
        if self.served is None or self.start64 is None:
            return
        at = self.start64 + np.round(np.asarray(t_s, dtype=float) * 1e6).astype("timedelta64[us]")
        for row in np.unique(rows):
            norad_id = self.norad_of_row.get(int(row))
            if norad_id is None or int(row) not in self.served.rows:
                continue
            which = np.nonzero(rows == row)[0]
            r_e, v_e, ok = self.served.states_at(norad_id, at[which])
            if not ok.any():
                continue
            r[which[ok]] = r_e[ok]
            v[which[ok]] = v_e[ok]

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
        if self.served is not None:
            self._substitute(t_s, self.p_rows[idx], r_p, v_p)
            self._substitute(t_s, s_rows[idx], r_s, v_s)
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


def vector_scan(
    func: Callable[[np.ndarray, np.ndarray], np.ndarray],
    a: np.ndarray,
    b: np.ndarray,
    *,
    subdivisions: int = SCAN_SUBDIVISIONS,
) -> tuple[np.ndarray, np.ndarray]:
    """The smallest sampled value of many functions on ``[a, b]``, on a fixed sub-grid.

    For the brackets that straddle a jump in the served trajectory. A root finder needs a
    sign change it can trust and a golden-section search needs unimodality; across a
    discontinuity there is neither, so the interval is simply scanned. With the default
    hundred subdivisions of a 30-second step the time of closest approach is placed to 0.3 s,
    which is coarse against the microsecond tolerance the root finder reaches and entirely
    adequate for the handful of candidates that land on one of an object's three jump
    instants in a run. Returns ``(t, converged)``; converged is false where every sample
    was NaN.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = len(a)
    if n == 0:
        return np.zeros(0), np.zeros(0, dtype=bool)
    idx = np.arange(n)
    best_t = np.full(n, np.nan)
    best_d = np.full(n, np.inf)
    for s in np.linspace(0.0, 1.0, int(subdivisions) + 1):
        t = a + s * (b - a)
        d = np.asarray(func(t, idx), dtype=float)
        better = np.isfinite(d) & (d < best_d)
        best_d[better] = d[better]
        best_t[better] = t[better]
    return np.where(np.isfinite(best_t), best_t, 0.5 * (a + b)), np.isfinite(best_t)


@dataclass
class StageCResult:
    """Refined events (geometry only) and counts."""

    events: pd.DataFrame
    n_candidates: int
    n_root: int
    n_minimum: int
    n_unconverged: int
    n_scan: int = 0


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
    ev = PairEvaluator(
        prop.satrecs,
        p_rows,
        s_rows,
        jd0,
        fr0,
        served=stage_b_result.served,
        start64=start64,
        norad_of_row={row: int(n) for n, row in prop.row.items()},
    )
    t_lo = (cand["t_lo"].to_numpy(dtype="datetime64[us]") - start64) / np.timedelta64(1, "s")
    t_hi = (cand["t_hi"].to_numpy(dtype="datetime64[us]") - start64) / np.timedelta64(1, "s")
    idx_all = np.arange(n)

    # Re-evaluate the bracket ends with the scalar path (bit-for-bit it can differ from the
    # array path in the last place), and send anything not properly bracketed to the minimiser.
    f_lo, _ = ev.range_rate(t_lo, idx_all)
    f_hi, _ = ev.range_rate(t_hi, idx_all)
    method = cand["method"].to_numpy()
    use_scan = method == "scan"
    use_root = (method == "root") & (f_lo < 0) & (f_hi >= 0) & ~use_scan
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
    min_idx = np.nonzero(~use_root & ~use_scan)[0]
    if len(min_idx):

        def f_min(tt: np.ndarray, sub: np.ndarray) -> np.ndarray:
            return ev.distance(tt, min_idx[sub])

        tm, cm = vector_minimum(f_min, t_lo[min_idx], t_hi[min_idx], tol=max(config.time_tolerance_s, 1e-3))
        t[min_idx] = tm
        ok[min_idx] = cm
    scan_idx = np.nonzero(use_scan)[0]
    if len(scan_idx):

        def f_scan(tt: np.ndarray, sub: np.ndarray) -> np.ndarray:
            return ev.distance(tt, scan_idx[sub])

        ts, cs = vector_scan(f_scan, t_lo[scan_idx], t_hi[scan_idx])
        t[scan_idx] = ts
        ok[scan_idx] = cs

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
            "refine_method": np.where(use_scan, "scan", np.where(use_root, "root", "minimum")),
            **state_columns(r_p, v_p, r_s, v_s),
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
        "Stage C: %d candidates refined (%d by root, %d by minimisation, %d by scanning a jump, "
        "%d did not converge); %d events within %.1f km or the %s km box",
        n,
        int(use_root.sum()),
        int((~use_root & ~use_scan).sum()),
        int(use_scan.sum()),
        n_unconverged,
        len(events),
        config.watch_radius_km,
        "x".join(f"{2 * x:g}" for x in config.box_ric_km),
    )
    return StageCResult(
        events, n, int(use_root.sum()), int((~use_root & ~use_scan).sum()), n_unconverged, int(use_scan.sum())
    )


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
    **{name: float for name in STATE_COLUMNS},
}


def state_columns(r_p: np.ndarray, v_p: np.ndarray, r_s: np.ndarray, v_s: np.ndarray) -> dict[str, np.ndarray]:
    """The :data:`STATE_COLUMNS` arrays from ``(n, 3)`` positions and velocities of both objects."""
    stacked = np.hstack([r_p, v_p, r_s, v_s])
    return {name: stacked[:, k] for k, name in enumerate(STATE_COLUMNS)}


def event_ids(primary: np.ndarray, secondary: np.ndarray, tca: np.ndarray, snapshot_stamp: str) -> np.ndarray:
    """Stable event identities: ``<snapshot stamp>:<primary>:<secondary>:<TCA to the minute>``.

    The Step 0 review's rule, so that the same event carries the same id in every
    scenario and across reruns of the same snapshot. Two distinct minima of one pair
    inside one minute (a shallow double approach) get ``#2``, ``#3`` suffixes in time order.
    """
    minutes = pd.to_datetime(pd.Series(tca), utc=True).dt.strftime("%Y%m%dT%H%MZ").to_numpy()
    ids = pd.Series(
        [f"{snapshot_stamp}:{int(p)}:{int(s)}:{m}" for p, s, m in zip(primary, secondary, minutes, strict=True)],
        dtype=object,
    )
    repeat = ids.groupby(ids).cumcount().to_numpy()
    suffixed = [f"{i}#{k + 1}" if k > 0 else i for i, k in zip(ids, repeat, strict=True)]
    return np.asarray(suffixed, dtype=object)


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
            "scanned_across_a_jump": self.stage_c.n_scan,
            "served_trajectory": self.stage_b.served.summary() if self.stage_b.served is not None else {"objects": 0},
            "events": int(len(ev)),
            "events_on_published_states": (
                int((ev["secondary_trajectory"] == TRAJECTORY_EPHEMERIS).sum()) if len(ev) else 0
            ),
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
    ephemeris: EphemerisTrajectory | None = None,
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
    reach = ephemeris.reach() if ephemeris is not None else None
    a = stage_a(snapshot, fleet.norad_ids, config, start=start_dt, reach=reach)
    timings["stage_a"] = time.perf_counter() - t0

    t1 = time.perf_counter()
    prop = Propagable.from_snapshot(snapshot, list(a.secondary_ids) + list(fleet.norad_ids))
    b = stage_b(prop, a, config, start=start_dt, ephemeris=ephemeris)
    timings["stage_b"] = time.perf_counter() - t1

    t2 = time.perf_counter()
    c = stage_c(prop, b, config, start=start_dt, end=end_dt)
    timings["stage_c"] = time.perf_counter() - t2

    events = annotate_events(c.events, snapshot, fleet, a, b.served)
    timings["total"] = time.perf_counter() - t0
    log.info(
        "Timings: Stage A %.1f s, Stage B %.1f s, Stage C %.1f s, total %.1f s",
        timings["stage_a"],
        timings["stage_b"],
        timings["stage_c"],
        timings["total"],
    )
    return ScreeningResult(events, start_dt, end_dt, config, a, b, c, timings)


def in_active_group(snapshot: pd.DataFrame) -> pd.Series:
    """Whether each snapshot row is in CelesTrak's ``active`` group (the manoeuvre prior's second rule)."""
    return snapshot["groups"].map(lambda g: "active" in (list(g) if g is not None else [])).astype(bool)


def annotate_events(
    events: pd.DataFrame,
    snapshot: pd.DataFrame,
    fleet: Fleet,
    stage_a_result: StageAResult,
    served: ServedTrajectory | None = None,
) -> pd.DataFrame:
    """Add the event id, names, categories and the flags to Stage C's geometry, in ``EVENT_COLUMNS`` order.

    The manoeuvre columns carry the prior level of :func:`driftwatch.risk.manoeuvre.manoeuvre_prior`
    (``known``, ``possible`` or ``none``); Step 3's history check can promote ``possible``
    to ``observed`` in the objects table and the joined export.
    """
    by_id = snapshot.drop_duplicates("norad_id").set_index("norad_id")
    flags = stage_a_result.objects.set_index("norad_id")
    p = events["primary_norad_id"].to_numpy()
    s = events["secondary_norad_id"].to_numpy()
    ephemeris = by_id["ephemeris"] if "ephemeris" in by_id.columns else pd.Series("gp", index=by_id.index)
    active = in_active_group(by_id)
    fleet_flags = {m.norad_id: m.manoeuvres for m in fleet}
    fleet_names = {m.norad_id: m.name for m in fleet}
    pri_category = by_id["category"].reindex(p).to_numpy()
    sec_category = by_id["category"].reindex(s).to_numpy()
    snapshot_stamp = stamp(pd.to_datetime(snapshot["fetched_at"], utc=True).max().to_pydatetime())
    out = events.copy()
    out["event_id"] = event_ids(p, s, events["tca"].to_numpy(), snapshot_stamp)
    out["primary_name"] = [fleet_names.get(int(n), by_id["name"].get(n, "")) for n in p]
    out["primary_category"] = pri_category
    out["secondary_name"] = by_id["name"].reindex(s).to_numpy()
    out["secondary_category"] = sec_category
    out["stale_primary"] = flags["stale"].reindex(p).to_numpy(dtype=bool)
    out["stale_secondary"] = flags["stale"].reindex(s).to_numpy(dtype=bool)
    out["manoeuvre_primary"] = [
        manoeuvre_prior(str(cat), bool(active.get(n, False)), fleet_flags.get(int(n)))
        for n, cat in zip(p, pri_category, strict=True)
    ]
    out["manoeuvre_secondary"] = [
        manoeuvre_prior(str(cat), bool(active.get(n, False)), fleet_flags.get(int(n)))
        for n, cat in zip(s, sec_category, strict=True)
    ]
    out["secondary_ephemeris"] = ephemeris.reindex(s).fillna("gp").to_numpy()
    tca64 = events["tca"].to_numpy(dtype="datetime64[us]")
    out["primary_trajectory"] = _trajectory_labels(served, p, tca64)
    out["secondary_trajectory"] = _trajectory_labels(served, s, tca64)
    out["tca"] = pd.to_datetime(out["tca"], utc=True)
    return out[list(EVENT_COLUMNS)].reset_index(drop=True)


def _trajectory_labels(served: ServedTrajectory | None, norad_ids: np.ndarray, tca: np.ndarray) -> np.ndarray:
    """Which trajectory produced each event's state for these objects at their own TCA."""
    out = np.full(len(norad_ids), TRAJECTORY_SGP4, dtype=object)
    if served is None or not served:
        return out
    for norad_id in np.unique(norad_ids):
        which = np.nonzero(norad_ids == norad_id)[0]
        out[which] = served.label(int(norad_id), tca[which])
    return out
