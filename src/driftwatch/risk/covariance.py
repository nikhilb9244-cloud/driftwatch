"""Orbit uncertainty from element-set consistency: the covariance model and its fit.

The public catalogue carries no covariance, so it has to be estimated. The only handle
we have is consistency: for an object with several element sets, propagate an older set
to a newer set's epoch and measure the disagreement in the newer set's radial, in-track,
cross-track frame. Do that for every pair of sets between half a day and seven days
apart and the scatter of the disagreement, as a function of the propagation time, is a
model of how fast the position error grows.

Why that is a floor, not a measure. Every element set is a fit to the same tracking
network with the same force model, so two sets share whatever error the network and the
model have in common (a biased drag model during a storm, a sparse tracking geometry)
and the difference between them cannot see it. Consistency measures the part of the
error that changes from fit to fit. The true error is at least that large and
sometimes much larger; the probabilities built on it are indicative, not operational.

The model. Per object and per RIC component, the standard deviation of the
disagreement is fitted as a power law in the propagation time, ``sigma(dt) = s1 dt^p``
(``dt`` in days, ``s1`` in km at one day), by maximum likelihood for zero-mean Gaussian
residuals. Two parameters per component keep the fit stable on thin history; the
in-track exponent is expected near or above one (drag errors accumulate as position
errors grow with time squared while timing errors grow linearly), radial and cross-track
near zero (set by the fit noise, growing slowly). Objects with too little history fall
back to a pooled model for their category and altitude band: the component-wise median
of the fits of the objects in the pool that have one (a typical member, robust to the
few objects whose residuals are enormous), or, when fewer than five members are fitted,
a fit of the same form to the pool's residuals added together; and if even that is
empty, to a default prior per band taken from the published assessments of TLE
accuracy. Every covariance reports which was used.

Objects screened on a supplemental set are a special case. Their GP history measures
how much the satellite manoeuvred between fits, not how well it is tracked, so it says
nothing about the set actually used. :func:`fit_supplemental_covariance` fits those
objects from the consistency of successive stored supplemental versions instead, with
CelesTrak's published fit residual as a floor, and :class:`SupplementalCovariance`
wraps a base model to serve them.

The covariance is diagonal in the object's own RIC frame in Phase 2. Phase 3 will wrap
this model and add a storm term to the in-track variance, which is why the interface
returns a full matrix per time and a source label rather than three numbers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd
from sgp4.api import SatrecArray

from driftwatch.orbit.propagator import WGS72_MU_KM3_S2, build_satrecs
from driftwatch.orbit.time import julian_dates
from driftwatch.risk.manoeuvre import JumpDetection, detect_jumps
from driftwatch.screening.ric import ric_basis, to_ric

log = logging.getLogger(__name__)

# The range of propagation times the fit uses and the floor below which the model does
# not extrapolate: the fit noise at zero propagation time is not zero.
DT_MIN_DAYS = 0.5
DT_MAX_DAYS = 7.0
DT_FLOOR_DAYS = 0.5
# What counts as enough history for an object's own fit; below this the pooled fit is used.
MIN_SETS_EMPIRICAL = 5
MIN_PAIRS_EMPIRICAL = 10
MIN_DT_SPAN_RATIO = 3.0
# A pool is the median of its members' own fits when at least this many members have one;
# below that, a joint fit of the members' residuals with at least this many pairs.
MIN_FITTED_POOLED = 5
MIN_PAIRS_POOLED = 30
# Supplemental versions are published several times a day, so their consistency pairs are
# hours apart rather than days; the fit window and the floor move down to match.
SUPPLEMENTAL_DT_MIN_DAYS = 0.02
SUPPLEMENTAL_DT_FLOOR_DAYS = 0.05
# A power law fitted over a narrow range of propagation times cannot determine its own
# exponent; below this span ratio the exponent is fixed at :data:`SUPPLEMENTAL_DEFAULT_P`
# and only the scale is fitted. One is the shape of a plan revised at a steady rate.
SUPPLEMENTAL_MIN_SPAN_RATIO = 3.0
SUPPLEMENTAL_DEFAULT_P = 1.0
# Pairs per object are capped (random subsample) so that objects with several element sets
# a day do not dominate the pooled fit and the residual arrays stay small.
MAX_PAIRS_PER_OBJECT = 600
# The exponent grid for the profile likelihood.
P_GRID: np.ndarray = np.round(np.arange(0.0, 2.5001, 0.05), 2)
RIC = ("r", "i", "c")


@dataclass(frozen=True)
class ObjectRef:
    """Identity of an object as the covariance model sees it (the Step 0 review's interface)."""

    norad_id: int
    category: str  # snapshot category
    altitude_band: str  # snapshot altitude band


@dataclass(frozen=True)
class RicCovariance:
    """Position covariance in the object's own RIC frame at each requested time, and where it came from."""

    cov_km2: np.ndarray  # (n, 3, 3)
    source: str  # 'empirical', 'pooled:<category>/<band>', 'default:<band>', 'storm:<model>'


@runtime_checkable
class CovarianceModel(Protocol):
    """Any covariance model the screener can be handed (Phase 3 adds a storm one)."""

    version: str

    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        """Covariance of ``obj`` at the absolute UTC times ``at`` (datetime64[us]), given that
        its state was propagated from the element set with epoch ``epoch``."""
        ...


@dataclass(frozen=True)
class PowerLawGrowth:
    """``sigma_k(dt) = s1_k * dt^p_k`` per RIC component, ``dt`` in days clamped below at the floor."""

    sigma_1d_km: tuple[float, float, float]
    exponent: tuple[float, float, float]

    def sigma_km(self, dt_days: np.ndarray, *, dt_floor_days: float = DT_FLOOR_DAYS) -> np.ndarray:
        """Standard deviations ``(n, 3)`` in km at propagation times ``dt_days`` (any sign; the magnitude is used)."""
        dt = np.maximum(np.abs(np.asarray(dt_days, dtype=float)), dt_floor_days)
        s1 = np.asarray(self.sigma_1d_km, dtype=float)
        p = np.asarray(self.exponent, dtype=float)
        return s1[None, :] * dt[:, None] ** p[None, :]

    def covariance_km2(self, dt_days: np.ndarray, *, dt_floor_days: float = DT_FLOOR_DAYS) -> np.ndarray:
        """Diagonal RIC covariance ``(n, 3, 3)`` in km^2."""
        sigma = self.sigma_km(dt_days, dt_floor_days=dt_floor_days)
        out = np.zeros((len(sigma), 3, 3))
        out[:, [0, 1, 2], [0, 1, 2]] = sigma**2
        return out

    def as_dict(self) -> dict[str, float]:
        return {
            **{f"sigma_{k}_1d_km": float(s) for k, s in zip(RIC, self.sigma_1d_km, strict=True)},
            **{f"p_{k}": float(p) for k, p in zip(RIC, self.exponent, strict=True)},
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> PowerLawGrowth:
        return cls(
            tuple(float(row[f"sigma_{k}_1d_km"]) for k in RIC),  # type: ignore[arg-type]
            tuple(float(row[f"p_{k}"]) for k in RIC),  # type: ignore[arg-type]
        )


# Default priors per altitude band, used only when neither the object nor its pool has
# history. Magnitudes follow the published assessments of TLE accuracy (Flohrer, Krag and
# Klinkrad, "Assessment and categorisation of TLE orbit errors for the US SSN catalogue",
# 2008; Vallado and Cefola, "Two-line element sets: practice and use", 2012): in LEO the
# epoch error is a few hundred metres, in-track dominant, and the in-track error grows by
# about a kilometre a day. The exponents are the shape the empirical fits show. These
# numbers are a prior, not a measurement, and are labelled ``default:<band>``.
DEFAULT_GROWTH: dict[str, PowerLawGrowth] = {
    "leo": PowerLawGrowth((0.2, 1.0, 0.15), (0.3, 1.0, 0.3)),
    "meo": PowerLawGrowth((0.3, 0.8, 0.3), (0.3, 0.7, 0.3)),
    "geo": PowerLawGrowth((0.5, 1.5, 0.5), (0.3, 0.7, 0.3)),
    "heo": PowerLawGrowth((1.0, 3.0, 0.5), (0.5, 1.0, 0.5)),
    "other": PowerLawGrowth((1.0, 3.0, 0.5), (0.5, 1.0, 0.5)),
}


# --------------------------------------------------------------------------------------
# The fit: sufficient statistics of a power-law Gaussian model


@dataclass
class SufficientStats:
    """What the profile likelihood of the power law needs, so objects can be pooled by addition.

    For residuals ``d_k`` at propagation times ``dt_k`` and the model
    ``d_k ~ N(0, (s dt_k^p)^2)``, the likelihood maximised over ``s`` at fixed ``p`` is
    ``s^2 = S_p / N`` with ``S_p = sum d_k^2 / dt_k^(2p)``, and the profile log-likelihood
    is ``-(N/2) log(S_p / N) - p sum(log dt_k)`` up to a constant. ``s`` holds ``S_p`` for
    every ``p`` on :data:`P_GRID` and every RIC component.
    """

    s: np.ndarray = field(default_factory=lambda: np.zeros((len(P_GRID), 3)))
    log_dt_sum: float = 0.0
    n: int = 0
    dt_min: float = np.inf
    dt_max: float = 0.0

    def add(self, other: SufficientStats) -> None:
        self.s = self.s + other.s
        self.log_dt_sum += other.log_dt_sum
        self.n += other.n
        self.dt_min = min(self.dt_min, other.dt_min)
        self.dt_max = max(self.dt_max, other.dt_max)

    @property
    def span_ratio(self) -> float:
        """Longest propagation time over shortest: how much of a power law the residuals can see."""
        return float(self.dt_max / self.dt_min) if self.n and self.dt_min > 0 else 1.0

    def fit(self, *, fixed_p: float | None = None) -> PowerLawGrowth | None:
        """The maximum-likelihood power law, or None with no residuals.

        With ``fixed_p`` the exponent is not fitted (the residuals span too narrow a range
        of propagation times to determine one) and only the scale is maximised.
        """
        if self.n == 0:
            return None
        s = np.maximum(self.s, 1e-30)
        if fixed_p is not None:
            k = int(np.argmin(np.abs(P_GRID - fixed_p)))
            sigma1 = np.sqrt(s[k] / self.n)
            return PowerLawGrowth(tuple(float(x) for x in sigma1), (float(P_GRID[k]),) * 3)  # type: ignore[arg-type]
        ll = -0.5 * self.n * np.log(s / self.n) - P_GRID[:, None] * self.log_dt_sum
        best = np.argmax(ll, axis=0)
        sigma1 = np.sqrt(s[best, [0, 1, 2]] / self.n)
        return PowerLawGrowth(tuple(float(x) for x in sigma1), tuple(float(P_GRID[b]) for b in best))  # type: ignore[arg-type]


def median_growth(fits: Iterable[PowerLawGrowth]) -> PowerLawGrowth:
    """The component-wise median of several power laws: the parameters of a typical member of a pool."""
    fits = list(fits)
    s = np.median([f.sigma_1d_km for f in fits], axis=0)
    p = np.median([f.exponent for f in fits], axis=0)
    return PowerLawGrowth(tuple(float(x) for x in s), tuple(float(x) for x in p))  # type: ignore[arg-type]


def sufficient_stats(dt_days: np.ndarray, ric_km: np.ndarray) -> SufficientStats:
    """Sufficient statistics for residuals ``ric_km`` ``(n, 3)`` at propagation times ``dt_days`` ``(n,)``."""
    dt = np.asarray(dt_days, dtype=float)
    d2 = np.asarray(ric_km, dtype=float) ** 2
    if len(dt) == 0:
        return SufficientStats()
    weights = np.exp(-2.0 * P_GRID[:, None] * np.log(dt)[None, :])  # dt^(-2p), (n_p, n)
    return SufficientStats(weights @ d2, float(np.sum(np.log(dt))), int(len(dt)), float(dt.min()), float(dt.max()))


# --------------------------------------------------------------------------------------
# One object's history: propagation matrix, jump detection, consistency residuals


def osculating_semi_major_axis_km(r_km: np.ndarray, v_kms: np.ndarray) -> np.ndarray:
    """``a = 1 / (2 / |r| - v^2 / mu)`` from states ``(..., 3)``; the vis-viva inversion."""
    rn = np.linalg.norm(r_km, axis=-1)
    v2 = np.einsum("...i,...i->...", v_kms, v_kms)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 1.0 / (2.0 / rn - v2 / WGS72_MU_KM3_S2)


@dataclass
class ObjectHistoryFit:
    """The outcome of :func:`analyse_object` for one object."""

    norad_id: int
    n_sets: int
    n_pairs: int
    dt_min_days: float
    dt_max_days: float
    stats: SufficientStats
    jumps: JumpDetection
    growth: PowerLawGrowth | None  # the object's own fit, or None when the history is too thin

    @property
    def enough_history(self) -> bool:
        return self.growth is not None


def analyse_object(
    sets: pd.DataFrame,
    *,
    dt_min: float = DT_MIN_DAYS,
    dt_max: float = DT_MAX_DAYS,
    max_pairs: int = MAX_PAIRS_PER_OBJECT,
    rng: np.random.Generator | None = None,
    min_sets: int = MIN_SETS_EMPIRICAL,
    min_pairs: int = MIN_PAIRS_EMPIRICAL,
    min_span_ratio: float = MIN_DT_SPAN_RATIO,
    exclude_jumps: bool = True,
) -> ObjectHistoryFit:
    """Detect manoeuvres and measure consistency residuals for one object's element sets.

    ``sets`` holds one object's history rows (snapshot element columns), any order.
    Every set is propagated to every other set's epoch in one vectorised call; the
    jump detector reads consecutive intervals off that matrix (plus a drag-free
    propagation), and the residual pairs are every ``(older, newer)`` pair with a
    propagation time inside ``[dt_min, dt_max]`` days that spans no detected burn and
    involves no outlier set, subsampled to ``max_pairs``.

    ``exclude_jumps=False`` keeps the pairs that span a detected burn. Supplemental sets
    are fitted to an ephemeris that already contains the planned manoeuvres, so a jump
    between two of them is a revision of the plan, which is the error being measured
    rather than something to drop.
    """
    rng = rng or np.random.default_rng(0)
    sets = sets.sort_values("epoch").drop_duplicates("epoch", keep="last").reset_index(drop=True)
    n = len(sets)
    norad_id = int(sets["norad_id"].iloc[0]) if n else -1
    epochs = pd.to_datetime(sets["epoch"], utc=True)
    jumps = JumpDetection(n_intervals=max(n - 1, 0))
    if n < 2:
        return ObjectHistoryFit(norad_id, n, 0, np.nan, np.nan, SufficientStats(), jumps, None)

    t64 = epochs.dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    jd, fr = julian_dates(t64)
    err, r, v = SatrecArray(build_satrecs(sets)).sgp4(jd, fr)  # r[i, j]: set i at the epoch of set j
    ok = err == 0
    day = np.timedelta64(86_400_000_000, "us")
    k = np.arange(n - 1)

    # Manoeuvre detection on consecutive intervals.
    err0, r0, v0 = SatrecArray(build_satrecs(sets.assign(bstar=0.0))).sgp4(jd[1:], fr[1:])
    a_fit = osculating_semi_major_axis_km(r[k + 1, k + 1], v[k + 1, k + 1])
    a_prop = osculating_semi_major_axis_km(r[k, k + 1], v[k, k + 1])
    a_free = osculating_semi_major_axis_km(r0[k, k], v0[k, k])
    good = ok[k + 1, k + 1] & ok[k, k + 1] & (err0[k, k] == 0)
    a_fit = np.where(good, a_fit, np.nan)
    dt_consecutive = (t64[1:] - t64[:-1]) / day
    jump, bad_set = detect_jumps(a_fit, a_prop, a_free, dt_consecutive)
    py_epochs = [t.to_pydatetime() for t in epochs]
    jumps.jump_epochs = [py_epochs[m + 1] for m in np.nonzero(jump)[0]]
    jumps.jump_delta_a_km = [float(a_fit[m] - a_prop[m]) for m in np.nonzero(jump)[0]]
    jumps.bad_set_epochs = [py_epochs[m] for m in np.nonzero(bad_set)[0]]

    # Consistency residuals over pairs that span no burn.
    i, j = np.triu_indices(n, 1)
    dt = (t64[j] - t64[i]) / day
    spans_burn = np.concatenate([[0], np.cumsum(jump)])
    keep = (dt >= dt_min) & (dt <= dt_max) & ok[i, j] & ok[j, j]
    if exclude_jumps:
        keep &= ~bad_set[i] & ~bad_set[j]
        keep &= (spans_burn[j] - spans_burn[i]) == 0
    i, j, dt = i[keep], j[keep], dt[keep]
    if len(i) > max_pairs:
        pick = np.sort(rng.choice(len(i), max_pairs, replace=False))
        i, j, dt = i[pick], j[pick], dt[pick]
    if len(i) == 0:
        return ObjectHistoryFit(norad_id, n, 0, np.nan, np.nan, SufficientStats(), jumps, None)
    basis = ric_basis(r[j, j], v[j, j])
    ric = to_ric(basis, r[i, j] - r[j, j])
    stats = sufficient_stats(dt, ric)
    enough = n >= min_sets and len(i) >= min_pairs and dt.max() >= min_span_ratio * dt.min()
    growth = stats.fit() if enough else None
    return ObjectHistoryFit(norad_id, n, int(len(i)), float(dt.min()), float(dt.max()), stats, jumps, growth)


# --------------------------------------------------------------------------------------
# The model


class EmpiricalCovariance:
    """Per-object power laws with pooled and default fallbacks; the Phase 2 covariance model."""

    version = "empirical-powerlaw/1"

    def __init__(
        self,
        objects: Mapping[int, PowerLawGrowth] | None = None,
        pools: Mapping[tuple[str, str], PowerLawGrowth] | None = None,
        defaults: Mapping[str, PowerLawGrowth] | None = None,
        *,
        dt_floor_days: float = DT_FLOOR_DAYS,
        fitted_at: datetime | None = None,
        window: tuple[date, date] | None = None,
        table: pd.DataFrame | None = None,
    ) -> None:
        self.objects = dict(objects or {})
        self.pools = dict(pools or {})
        self.defaults = dict(defaults or DEFAULT_GROWTH)
        self.dt_floor_days = float(dt_floor_days)
        self.fitted_at = fitted_at
        self.window = window
        self.table = table

    def growth_for(self, obj: ObjectRef) -> tuple[PowerLawGrowth, str]:
        """The power law used for ``obj`` and its source label."""
        own = self.objects.get(int(obj.norad_id))
        if own is not None:
            return own, "empirical"
        pool = self.pools.get((str(obj.category), str(obj.altitude_band)))
        if pool is not None:
            return pool, f"pooled:{obj.category}/{obj.altitude_band}"
        band = str(obj.altitude_band) if str(obj.altitude_band) in self.defaults else "other"
        return self.defaults[band], f"default:{band}"

    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        """Diagonal RIC covariance at the times ``at``, from the propagation time since ``epoch``."""
        at64 = np.asarray(at, dtype="datetime64[us]")
        epoch_ts = pd.Timestamp(epoch)
        epoch_ts = epoch_ts.tz_convert(None) if epoch_ts.tzinfo else epoch_ts
        dt_days = (at64 - np.datetime64(epoch_ts.to_datetime64(), "us")) / np.timedelta64(86_400_000_000, "us")
        growth, source = self.growth_for(obj)
        return RicCovariance(growth.covariance_km2(dt_days, dt_floor_days=self.dt_floor_days), source)

    # Persistence ------------------------------------------------------------------

    def to_frame(self) -> pd.DataFrame:
        """The model as a table: one row per object fit, per pool and per default (see ``docs/data-schema.md``)."""
        if self.table is not None:
            return self.table
        rows: list[dict[str, Any]] = []
        for norad_id, growth in self.objects.items():
            rows.append({"kind": "object", "norad_id": norad_id, "source": "empirical", **growth.as_dict()})
        for (category, band), growth in self.pools.items():
            rows.append(
                {
                    "kind": "pool",
                    "category": category,
                    "altitude_band": band,
                    "source": f"pooled:{category}/{band}",
                    **growth.as_dict(),
                }
            )
        for band, growth in self.defaults.items():
            rows.append({"kind": "default", "altitude_band": band, "source": f"default:{band}", **growth.as_dict()})
        return pd.DataFrame(rows, columns=COVARIANCE_TABLE_COLUMNS)

    @classmethod
    def from_frame(cls, df: pd.DataFrame, **kwargs: Any) -> EmpiricalCovariance:
        """Rebuild a model from :meth:`to_frame` output (only rows with a fit are used)."""
        objects: dict[int, PowerLawGrowth] = {}
        pools: dict[tuple[str, str], PowerLawGrowth] = {}
        defaults: dict[str, PowerLawGrowth] = {}
        fitted = df[df["sigma_i_1d_km"].notna()]
        for _, row in fitted.iterrows():
            growth = PowerLawGrowth.from_row(row)
            if row["kind"] == "object" and row["source"] == "empirical":
                objects[int(row["norad_id"])] = growth
            elif row["kind"] == "pool":
                pools[(str(row["category"]), str(row["altitude_band"]))] = growth
            elif row["kind"] == "default":
                defaults[str(row["altitude_band"])] = growth
        return cls(objects, pools, defaults or None, table=df, **kwargs)


@dataclass(frozen=True)
class FlooredGrowth:
    """A power law over a floor: ``sigma_k(dt)^2 = (share_k * floor)^2 + (s_k dt^p_k)^2``.

    The floor is CelesTrak's published RMS of the fit of a supplemental element set to
    the operator ephemeris: the disagreement between the set and the trajectory it was
    fitted to, which no amount of consistency between versions can see. ``share`` splits
    that scalar across the RIC components; it is the shape of the fitted growth, or an
    equal split when there is no growth to take a shape from.
    """

    growth: PowerLawGrowth
    floor_km: float
    share: tuple[float, float, float]

    def sigma_km(self, dt_days: np.ndarray, *, dt_floor_days: float = SUPPLEMENTAL_DT_FLOOR_DAYS) -> np.ndarray:
        grown = self.growth.sigma_km(dt_days, dt_floor_days=dt_floor_days)
        floor = np.asarray(self.share, dtype=float)[None, :] * self.floor_km
        return np.sqrt(grown**2 + floor**2)

    def covariance_km2(self, dt_days: np.ndarray, *, dt_floor_days: float = SUPPLEMENTAL_DT_FLOOR_DAYS) -> np.ndarray:
        sigma = self.sigma_km(dt_days, dt_floor_days=dt_floor_days)
        out = np.zeros((len(sigma), 3, 3))
        out[:, [0, 1, 2], [0, 1, 2]] = sigma**2
        return out

    def as_dict(self) -> dict[str, float]:
        return {**self.growth.as_dict(), "rms_km": float(self.floor_km)}


class SupplementalCovariance:
    """A base model with the supplemental-set objects served from their own fit.

    An object screened on a supplemental set is propagated from a fit to the operator's
    published ephemeris, so its uncertainty is the uncertainty of that ephemeris, not of
    the GP element sets the catalogue holds for it. Only the objects in ``models`` are
    treated this way; everything else falls through to ``base``.
    """

    def __init__(
        self,
        base: CovarianceModel,
        models: Mapping[int, FlooredGrowth] | None = None,
        sources: Mapping[int, str] | None = None,
        *,
        dt_floor_days: float = SUPPLEMENTAL_DT_FLOOR_DAYS,
        table: pd.DataFrame | None = None,
    ) -> None:
        self.base = base
        self.models = dict(models or {})
        self.sources = dict(sources or {})
        self.supplemental_dt_floor_days = float(dt_floor_days)
        self.table = table
        self.version = f"{base.version}+supplemental/1"

    @property
    def dt_floor_days(self) -> float:
        return getattr(self.base, "dt_floor_days", DT_FLOOR_DAYS)

    def growth_for(self, obj: ObjectRef) -> tuple[Any, str]:
        """The growth used for ``obj`` and its source label, supplemental objects first."""
        model = self.models.get(int(obj.norad_id))
        if model is not None:
            return model, self.sources.get(int(obj.norad_id), "supplemental")
        return self.base.growth_for(obj)  # type: ignore[attr-defined]

    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        model = self.models.get(int(obj.norad_id))
        if model is None:
            return self.base.covariance_ric(obj, epoch, at)
        at64 = np.asarray(at, dtype="datetime64[us]")
        epoch_ts = pd.Timestamp(epoch)
        epoch_ts = epoch_ts.tz_convert(None) if epoch_ts.tzinfo else epoch_ts
        dt_days = (at64 - np.datetime64(epoch_ts.to_datetime64(), "us")) / np.timedelta64(86_400_000_000, "us")
        cov = model.covariance_km2(dt_days, dt_floor_days=self.supplemental_dt_floor_days)
        return RicCovariance(cov, self.sources.get(int(obj.norad_id), "supplemental"))

    def to_frame(self) -> pd.DataFrame:
        """The base model's table with the supplemental rows appended."""
        base_table = self.base.to_frame() if hasattr(self.base, "to_frame") else pd.DataFrame()
        if self.table is None:
            return base_table
        return pd.concat([base_table, self.table], ignore_index=True)

    @classmethod
    def from_frame(cls, base: CovarianceModel, df: pd.DataFrame, **kwargs: Any) -> SupplementalCovariance:
        """Rebuild the supplemental layer from the rows of :meth:`to_frame` with ``kind == 'supplemental'``."""
        rows = df[(df["kind"] == "supplemental") & df["sigma_i_1d_km"].notna()]
        models: dict[int, FlooredGrowth] = {}
        sources: dict[int, str] = {}
        for _, row in rows.iterrows():
            norad_id = int(row["norad_id"])
            share = _share_from(PowerLawGrowth.from_row(row))
            models[norad_id] = FlooredGrowth(PowerLawGrowth.from_row(row), float(row.get("rms_km") or 0.0), share)
            sources[norad_id] = str(row["source"])
        return cls(base, models, sources, table=rows.reset_index(drop=True), **kwargs)


def _share_from(growth: PowerLawGrowth) -> tuple[float, float, float]:
    """Split a scalar floor across R, I and C in the proportions of a growth law at one day."""
    s = np.asarray(growth.sigma_1d_km, dtype=float)
    total = float(np.linalg.norm(s))
    if not np.isfinite(total) or total <= 0:
        return (1.0 / np.sqrt(3.0),) * 3  # type: ignore[return-value]
    return tuple(float(x) for x in s / total)  # type: ignore[return-value]


class ScaledCovariance:
    """A base model with every covariance multiplied by a factor: the simplest possible scenario wrapper.

    Not a physical model. It exists so that a second scenario can be scored over stored
    events today (``driftwatch risk --scale 2``) through the same interface Phase 3's
    storm model will use, and so that the scenario mechanism can be tested. The source
    label is prefixed ``scaled:<factor>:`` and the version string records the factor.
    """

    def __init__(self, base: CovarianceModel, factor: float) -> None:
        if not factor > 0:
            raise ValueError(f"the covariance scale factor must be positive, got {factor}")
        self.base = base
        self.factor = float(factor)
        self.version = f"{base.version}*scaled/{self.factor:g}"

    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        inner = self.base.covariance_ric(obj, epoch, at)
        return RicCovariance(inner.cov_km2 * self.factor, f"scaled:{self.factor:g}:{inner.source}")


COVARIANCE_TABLE_COLUMNS: tuple[str, ...] = (
    "kind",
    "norad_id",
    "category",
    "altitude_band",
    "source",
    "n_objects",
    "n_fitted",
    "n_sets",
    "n_pairs",
    "dt_min_days",
    "dt_max_days",
    "sigma_r_1d_km",
    "p_r",
    "sigma_i_1d_km",
    "p_i",
    "sigma_c_1d_km",
    "p_c",
    "n_jumps",
    "n_bad_sets",
    "rms_km",
)


@dataclass
class CovarianceFit:
    """A fitted model, its table, the per-object jump detections and a summary for the log."""

    model: EmpiricalCovariance
    table: pd.DataFrame
    jumps: dict[int, JumpDetection]
    summary: dict[str, Any]


def fit_covariance(
    history: pd.DataFrame,
    objects: pd.DataFrame,
    *,
    dt_min: float = DT_MIN_DAYS,
    dt_max: float = DT_MAX_DAYS,
    max_pairs: int = MAX_PAIRS_PER_OBJECT,
    seed: int = 0,
    now: datetime | None = None,
    window: tuple[date, date] | None = None,
) -> CovarianceFit:
    """Fit the empirical model for ``objects`` (``norad_id``, ``category``, ``altitude_band``) from ``history``.

    Every object in ``objects`` is analysed with :func:`analyse_object`; those with enough
    history get their own power law, and every object's residuals and fit join its
    (category, band) pool. A pool's power law is the component-wise median of its
    members' fits when at least :data:`MIN_FITTED_POOLED` members have one, otherwise a
    fit to the pooled residuals when they hold at least :data:`MIN_PAIRS_POOLED` pairs.
    The returned table has one row per object (fitted or not), per pool and per default.
    """
    rng = np.random.default_rng(seed)
    now = now or datetime.now(UTC)
    labels = objects.drop_duplicates("norad_id").set_index("norad_id")
    wanted = [int(i) for i in labels.index]
    hist = history[history["norad_id"].isin(wanted)]
    by_object = {int(k): g for k, g in hist.groupby("norad_id", sort=False)}

    fits: dict[int, PowerLawGrowth] = {}
    pool_stats: dict[tuple[str, str], SufficientStats] = {}
    pool_members: dict[tuple[str, str], int] = {}
    pool_fits: dict[tuple[str, str], list[PowerLawGrowth]] = {}
    jumps: dict[int, JumpDetection] = {}
    rows: list[dict[str, Any]] = []
    for norad_id in wanted:
        category = str(labels.loc[norad_id, "category"])
        band = str(labels.loc[norad_id, "altitude_band"])
        sets = by_object.get(norad_id)
        if sets is None or len(sets) < 2:
            n_sets = 0 if sets is None else len(sets)
            jumps[norad_id] = JumpDetection()
            rows.append(
                {"kind": "object", "norad_id": norad_id, "category": category, "altitude_band": band, "n_sets": n_sets}
            )
            continue
        fit = analyse_object(sets, dt_min=dt_min, dt_max=dt_max, max_pairs=max_pairs, rng=rng)
        jumps[norad_id] = fit.jumps
        if fit.n_pairs:
            key = (category, band)
            pool_stats.setdefault(key, SufficientStats()).add(fit.stats)
            pool_members[key] = pool_members.get(key, 0) + 1
        row: dict[str, Any] = {
            "kind": "object",
            "norad_id": norad_id,
            "category": category,
            "altitude_band": band,
            "n_sets": fit.n_sets,
            "n_pairs": fit.n_pairs,
            "dt_min_days": fit.dt_min_days,
            "dt_max_days": fit.dt_max_days,
            "n_jumps": fit.jumps.n_jumps,
            "n_bad_sets": len(fit.jumps.bad_set_epochs),
        }
        if fit.growth is not None:
            fits[norad_id] = fit.growth
            pool_fits.setdefault((category, band), []).append(fit.growth)
            row.update(source="empirical", **fit.growth.as_dict())
        rows.append(row)

    pools: dict[tuple[str, str], PowerLawGrowth] = {}
    for key, stats in sorted(pool_stats.items()):
        fitted = pool_fits.get(key, [])
        if len(fitted) >= MIN_FITTED_POOLED:
            growth: PowerLawGrowth | None = median_growth(fitted)
        else:
            growth = stats.fit() if stats.n >= MIN_PAIRS_POOLED else None
        row = {
            "kind": "pool",
            "category": key[0],
            "altitude_band": key[1],
            "n_objects": pool_members[key],
            "n_fitted": len(fitted),
            "n_pairs": stats.n,
            "dt_min_days": stats.dt_min,
            "dt_max_days": stats.dt_max,
        }
        if growth is not None:
            pools[key] = growth
            row.update(source=f"pooled:{key[0]}/{key[1]}", **growth.as_dict())
        rows.append(row)
    for band, growth in DEFAULT_GROWTH.items():
        rows.append({"kind": "default", "altitude_band": band, "source": f"default:{band}", **growth.as_dict()})

    table = pd.DataFrame(rows, columns=COVARIANCE_TABLE_COLUMNS)
    # Label every object row with the source the model will actually use for it.
    model = EmpiricalCovariance(fits, pools, fitted_at=now, window=window)
    obj_rows = table["kind"] == "object"
    table.loc[obj_rows, "source"] = [
        model.growth_for(ObjectRef(int(r.norad_id), str(r.category), str(r.altitude_band)))[1]
        for r in table[obj_rows].itertuples()
    ]
    model.table = table
    sources = table.loc[obj_rows, "source"].str.split(":").str[0].value_counts().to_dict()
    summary = {
        "n_objects": int(obj_rows.sum()),
        "n_with_history": int((table.loc[obj_rows, "n_sets"].fillna(0) >= 2).sum()),
        "by_source": {str(k): int(v) for k, v in sources.items()},
        "n_pools": len(pools),
        "n_objects_with_jumps": int((table.loc[obj_rows, "n_jumps"].fillna(0) > 0).sum()),
        "n_jumps": int(table.loc[obj_rows, "n_jumps"].fillna(0).sum()),
        "n_bad_sets": int(table.loc[obj_rows, "n_bad_sets"].fillna(0).sum()),
    }
    log.info("Covariance fit: %s", summary)
    return CovarianceFit(model, table, jumps, summary)


@dataclass
class SupplementalFit:
    """A fitted supplemental layer, its table and a summary for the log."""

    model: SupplementalCovariance
    table: pd.DataFrame
    summary: dict[str, Any]


def fit_supplemental_covariance(
    base: CovarianceModel,
    history: pd.DataFrame,
    norad_ids: Iterable[int],
    *,
    dt_min: float = SUPPLEMENTAL_DT_MIN_DAYS,
    dt_max: float = DT_MAX_DAYS,
    seed: int = 0,
    default_p: float = SUPPLEMENTAL_DEFAULT_P,
) -> SupplementalFit:
    """Fit the objects in ``norad_ids`` from the consistency of successive supplemental versions.

    ``history`` is the stored supplemental history (see
    :func:`driftwatch.screening.supplemental.load_supplemental_history`): the element
    columns of the snapshot plus the published ``rms_km``. Every object with two or more
    stored sets contributes its residuals to one pool, since no object has enough
    versions of its own yet; the pool's power law is fitted with a free exponent when the
    propagation times span a factor of :data:`SUPPLEMENTAL_MIN_SPAN_RATIO`, and with the
    exponent fixed at ``default_p`` when they do not. Every object then gets that growth
    over its own published RMS as a floor. Objects with no stored history at all get the
    floor alone, which is a lower bound and is labelled so.

    Pairs that span a detected manoeuvre are kept here, unlike the GP fit: a supplemental
    set is fitted to an ephemeris that already contains the planned burns, so the
    difference between two versions is the revision of the plan, which is the error being
    measured.
    """
    rng = np.random.default_rng(seed)
    ids = sorted({int(i) for i in norad_ids})
    hist = history[history["norad_id"].isin(ids)] if len(history) else history
    rms_by_id: dict[int, float] = {}
    if len(hist):
        for norad_id, group in hist.groupby("norad_id"):
            values = group["rms_km"].dropna()
            if len(values):
                rms_by_id[int(norad_id)] = float(values.iloc[-1])
    median_rms = float(np.median(list(rms_by_id.values()))) if rms_by_id else 0.0

    stats = SufficientStats()
    n_objects_with_pairs = 0
    by_object = {int(k): g for k, g in hist.groupby("norad_id", sort=False)} if len(hist) else {}
    for norad_id in ids:
        sets = by_object.get(norad_id)
        if sets is None or len(sets) < 2:
            continue
        fit = analyse_object(sets, dt_min=dt_min, dt_max=dt_max, rng=rng, exclude_jumps=False)
        if fit.n_pairs:
            stats.add(fit.stats)
            n_objects_with_pairs += 1

    span = stats.span_ratio
    fixed_p = None if span >= SUPPLEMENTAL_MIN_SPAN_RATIO else default_p
    growth = stats.fit(fixed_p=fixed_p) if stats.n >= MIN_PAIRS_POOLED else None
    share = _share_from(growth) if growth is not None else (1.0 / np.sqrt(3.0),) * 3
    zero = PowerLawGrowth((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))

    models: dict[int, FlooredGrowth] = {}
    sources: dict[int, str] = {}
    rows: list[dict[str, Any]] = []
    for norad_id in ids:
        floor = rms_by_id.get(norad_id, median_rms)
        if growth is not None:
            models[norad_id] = FlooredGrowth(growth, floor, share)  # type: ignore[arg-type]
            label = "supplemental:consistency" if fixed_p is None else f"supplemental:consistency-p{default_p:g}"
        else:
            models[norad_id] = FlooredGrowth(zero, floor, share)  # type: ignore[arg-type]
            label = "supplemental:rms"
        sources[norad_id] = label
        rows.append(
            {
                "kind": "supplemental",
                "norad_id": norad_id,
                "source": label,
                "n_sets": len(by_object.get(norad_id, [])),
                **models[norad_id].as_dict(),
            }
        )

    table = pd.DataFrame(rows, columns=COVARIANCE_TABLE_COLUMNS)
    model = SupplementalCovariance(base, models, sources, table=table)
    summary = {
        "n_objects": len(ids),
        "n_versions": int(hist["fetched_at"].nunique()) if len(hist) else 0,
        "n_objects_with_pairs": n_objects_with_pairs,
        "n_pairs": int(stats.n),
        "dt_days": [round(float(stats.dt_min), 3), round(float(stats.dt_max), 3)] if stats.n else None,
        "span_ratio": round(span, 2) if stats.n else None,
        "exponent_fitted": fixed_p is None,
        "growth": growth.as_dict() if growth is not None else None,
        "rms_km_median": round(median_rms, 4),
        "by_source": {k: sum(1 for v in sources.values() if v == k) for k in sorted(set(sources.values()))},
    }
    log.info("Supplemental covariance: %s", summary)
    return SupplementalFit(model, table, summary)


def label_cov_sources(objects: pd.DataFrame, model: CovarianceModel) -> pd.DataFrame:
    """Set each object's ``cov_source`` from the model that will actually serve it."""
    out = objects.copy()
    out["cov_source"] = [
        model.growth_for(ObjectRef(int(r.norad_id), str(r.category), str(r.altitude_band)))[1]  # type: ignore[attr-defined]
        for r in out.itertuples()
    ]
    return out


def sigma_table(
    model: EmpiricalCovariance, refs: Iterable[ObjectRef], dt_days: Iterable[float] = (1.0, 3.0, 7.0)
) -> pd.DataFrame:
    """Standard deviations at a few propagation times for a list of objects, for logs and the report."""
    rows = []
    dts = np.asarray(list(dt_days), dtype=float)
    for ref in refs:
        growth, source = model.growth_for(ref)
        sigma = growth.sigma_km(dts, dt_floor_days=model.dt_floor_days)
        row: dict[str, Any] = {"norad_id": ref.norad_id, "source": source}
        for dt, s in zip(dts, sigma, strict=True):
            for k, val in zip(RIC, s, strict=True):
                row[f"sigma_{k}_{dt:g}d_km"] = float(val)
        rows.append(row)
    return pd.DataFrame(rows)
