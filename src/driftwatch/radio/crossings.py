"""The two products for an observation, on the catalogue as it stood at the observation's start.

**Product one: what is in the sky.** Every catalogued object that belongs to a constellation
with a declared emission, counted by constellation, that rises above a chosen elevation at any
time during the observation, with how many are up at once. This is the aggregate that a
sidelobe sees: a GNSS satellite need not cross the beam to be received, and the number of them
above the horizon at once is the size of that problem. It is a count, not a power.

**Product two: what crosses the beam.** Every catalogued object whose predicted track passes
inside the primary beam's half-power radius, with its closest approach to the boresight, the
time, the element set's age at that time, the cross-track angular uncertainty the calibration
benchmark gives that age and geometry, and whether the crossing is inside or outside the
measured horizon. Objects outside the benchmark's population carry *no measured horizon* and
the reason.

Both are geometry from public element sets. Nothing here is a received power, an occupancy or
a sensitivity loss.

Method for product two. The whole catalogue is propagated on a ten-second grid over the
observation and every object that comes within reach of the beam -- its angle from the
boresight at some sample under the half-power radius plus what it could move between samples
at its range -- is propagated again on a one-second grid. Each local minimum of the angle on that
grid is refined by a bounded scalar minimisation of the continuous function (SGP4, Earth rotation,
the boresight interpolated between its one-second samples), and the crossing is reported if the
refined closest approach is inside the half-power radius. An angle that is already inside the
beam at the first or last sample is a crossing in progress at the observation's edge and is
labelled partial.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from driftwatch import config
from driftwatch.catalogue import history, snapshot
from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs
from driftwatch.orbit.time import julian_dates
from driftwatch.radio import emissions
from driftwatch.radio import horizon as horizon_mod
from driftwatch.radio import site as site_mod
from driftwatch.radio.horizon import COVERAGE, CrossingUncertainty
from driftwatch.radio.observations import Observation
from driftwatch.radio.site import Site, boresight, look_from, separation_deg, sky_projection, teme_to_pef
from driftwatch.screening.ric import ric_basis

log = logging.getLogger(__name__)

# The population the calibration benchmark measured: three near-circular satellites at 460 to
# 506 km. Objects outside this band carry no measured horizon.
MEASURED_ALTITUDE_KM = (400.0, 600.0)
MEASURED_MAX_ECCENTRICITY = 0.02
MEASURED_MAX_AGE_DAYS = 7.0
MEASURED_POPULATION = "Swarm A, B and C at 460 to 506 km, near-circular, not manoeuvring in the trials kept"

# The elevation above which an object counts as in the sky for product one. MeerKAT observes
# above 15 degrees; a sidelobe has no such limit, and the local horizon is a degree or two.
ELEVATION_CUTOFF_DEG = 10.0
# Newest set at or before the observation, no older than this, or the object is not in the catalogue that day.
CATALOGUE_MAX_AGE_DAYS = 7.0

COARSE_STEP_S = 10.0
FINE_STEP_S = 1.0
# The fastest a low object can move across the sky: orbital speed over the range. 7.9 km/s is
# the circular speed at the Earth's surface, an upper bound for any bound orbit's transverse speed.
MAX_TRANSVERSE_SPEED_KM_S = 7.9
CHUNK_OBJECTS = 4000


@dataclass(frozen=True)
class Period:
    """A retrospective period: which days, and which benchmark window its element-set error is read from."""

    name: str
    label: str
    first_day: date
    last_day: date
    benchmark_window: str
    why: str

    @property
    def start(self) -> datetime:
        return datetime(self.first_day.year, self.first_day.month, self.first_day.day, tzinfo=UTC)

    @property
    def end(self) -> datetime:
        return datetime(self.last_day.year, self.last_day.month, self.last_day.day, tzinfo=UTC) + timedelta(days=1)


PERIODS: dict[str, Period] = {
    "quiet-2024-04": Period(
        "quiet-2024-04",
        "quiet week, 20 to 27 April 2024",
        date(2024, 4, 20),
        date(2024, 4, 27),
        "quiet",
        "the calibration benchmark's quiet control week, Kp at or under 4 over 25 to 28 April",
    ),
    "storm-2024-05": Period(
        "storm-2024-05",
        "the May 2024 storm, 10 to 12 May",
        date(2024, 5, 10),
        date(2024, 5, 12),
        "storm",
        "the Gannon storm's main phase and first recovery, inside the benchmark's disturbed interval",
    ),
}


# --------------------------------------------------------------------------------------
# The catalogue as it stood


def load_sets(
    first_day: date, last_day: date, *, lead_days: int = 10, history_dir: Path = config.HISTORY_DIR
) -> pd.DataFrame:
    """Every stored element set with an epoch from ``lead_days`` before the first day to the end of the last."""
    start = datetime(first_day.year, first_day.month, first_day.day, tzinfo=UTC) - timedelta(days=lead_days)
    end = datetime(last_day.year, last_day.month, last_day.day, tzinfo=UTC) + timedelta(days=1)
    index = history.load_index(history_dir)
    if index.empty:
        raise FileNotFoundError(f"no history index under {history_dir}")
    epochs = pd.to_datetime(index["epoch"], utc=True)
    files = sorted(index.loc[(epochs >= start) & (epochs < end), "file"].unique())
    frames = []
    for name in files:
        df = history.read_history(Path(history_dir) / name)
        e = pd.to_datetime(df["epoch"], utc=True)
        frames.append(df[(e >= start) & (e < end)])
    if not frames:
        raise FileNotFoundError(f"no element sets between {start:%Y-%m-%d} and {end:%Y-%m-%d} in {history_dir}")
    sets = pd.concat(frames, ignore_index=True)
    sets["epoch"] = pd.to_datetime(sets["epoch"], utc=True)
    sets = sets.sort_values(["norad_id", "epoch"]).drop_duplicates(["norad_id", "epoch"], keep="last")
    log.info(
        "Element sets %s to %s: %d sets for %d objects from %d file(s)",
        start.date(),
        end.date(),
        len(sets),
        sets["norad_id"].nunique(),
        len(files),
    )
    return sets.reset_index(drop=True)


def catalogue_at(
    sets: pd.DataFrame, satcat_frame: pd.DataFrame | None, at: datetime, *, max_age_days: float = CATALOGUE_MAX_AGE_DAYS
) -> pd.DataFrame:
    """The catalogue at ``at``: each object's newest set at or before it, classified, with its constellation."""
    df = snapshot.snapshot_as_of(sets, satcat_frame, as_of=at, groups={}, max_age_days=max_age_days)
    df["mean_altitude_km"] = df["semi_major_axis_km"].to_numpy() - site_mod.EARTH_RADIUS_KM
    owners = df["owner"].astype(object).where(df["owner"].notna(), None)
    df["constellation"] = [
        emissions.constellation_of(n, o, t, a, i)
        for n, o, t, a, i in zip(
            df["name"].astype(str),
            owners,
            df["object_type"].astype(str),
            df["mean_altitude_km"],
            df["inclination_deg"],
            strict=True,
        )
    ]
    df["constellation"] = df["constellation"].astype(object)
    return df


# --------------------------------------------------------------------------------------
# Propagation helpers


def time_grid(start: datetime, duration_s: float, step_s: float) -> np.ndarray:
    """UTC ``datetime64[us]`` samples from ``start`` to ``start + duration``, the end included."""
    n = int(np.floor(duration_s / step_s)) + 1
    offsets = np.arange(n) * step_s
    if offsets[-1] < duration_s - 1e-9:
        offsets = np.append(offsets, duration_s)
    t0 = np.datetime64(start.astimezone(UTC).replace(tzinfo=None), "us")
    return t0 + (offsets * 1e6).astype("timedelta64[us]")


def _propagate_chunks(
    satrecs: list, ids: np.ndarray, times: np.ndarray, chunk: int = CHUNK_OBJECTS
) -> Iterator[tuple[slice, np.ndarray, np.ndarray]]:
    for k in range(0, len(satrecs), chunk):
        sl = slice(k, min(k + chunk, len(satrecs)))
        state = propagate_satrecs(satrecs[sl], ids[sl], times)
        yield sl, state.r_teme, state.v_teme


# --------------------------------------------------------------------------------------
# Product one


@dataclass
class ConstellationCount:
    constellation: str
    n_catalogued: int
    n_above: int
    mean_simultaneous: float
    max_simultaneous: int
    status: str
    detail: str


def constellation_view(
    catalogue: pd.DataFrame,
    site: Site,
    start: datetime,
    duration_s: float,
    rx: site_mod.Receiver,
    *,
    elevation_deg: float = ELEVATION_CUTOFF_DEG,
    step_s: float = 60.0,
) -> list[ConstellationCount]:
    """Constellation members above ``elevation_deg`` during the interval, sampled every ``step_s``."""
    members = catalogue[catalogue["constellation"].notna()].reset_index(drop=True)
    times = time_grid(start, duration_s, step_s)
    above = np.zeros((len(members), len(times)), dtype=bool)
    if len(members):
        satrecs = build_satrecs(members)
        for sl, r_teme, _ in _propagate_chunks(satrecs, members["norad_id"].to_numpy(), times):
            look = look_from(site, teme_to_pef(r_teme, times))
            above[sl] = np.nan_to_num(look.elevation_deg, nan=-90.0) >= elevation_deg
    out = []
    for name in emissions.CONSTELLATIONS:
        m = (members["constellation"] == name).to_numpy()
        if not m.any():
            continue
        block = above[m]
        simultaneous = block.sum(axis=0)
        status, detail = emissions.emission_status(name, rx)
        out.append(
            ConstellationCount(
                constellation=name,
                n_catalogued=int(m.sum()),
                n_above=int(block.any(axis=1).sum()),
                mean_simultaneous=float(simultaneous.mean()),
                max_simultaneous=int(simultaneous.max()),
                status=status,
                detail=detail,
            )
        )
    return out


def hourly_constellation_view(
    sets: pd.DataFrame,
    satcat_frame: pd.DataFrame | None,
    site: Site,
    period: Period,
    rx: site_mod.Receiver,
    *,
    elevation_deg: float = ELEVATION_CUTOFF_DEG,
    step_s: float = 60.0,
) -> pd.DataFrame:
    """Product one over a whole period, hour by hour, on the catalogue as it stood at each hour.

    Constellation membership is read once, from the catalogue at the period's start; a member
    launched inside the period is missed, which for these constellations is rare and is stated.
    """
    first = catalogue_at(sets, satcat_frame, period.start)
    member_ids = first.loc[first["constellation"].notna(), "norad_id"].astype("int64")
    member_sets = sets[sets["norad_id"].isin(member_ids)]
    rows: list[dict[str, Any]] = []
    hours = pd.date_range(period.start, period.end, freq="1h", inclusive="left")
    for h in hours:
        at = h.to_pydatetime()
        cat = catalogue_at(member_sets, satcat_frame, at)
        for c in constellation_view(cat, site, at, 3600.0 - step_s, rx, elevation_deg=elevation_deg, step_s=step_s):
            rows.append({"hour_utc": at.isoformat().replace("+00:00", "Z"), **asdict(c)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Product two


@dataclass
class Sample:
    time_utc: str
    julian_date: float
    elevation_deg: float
    azimuth_deg: float
    range_km: float
    separation_deg: float
    ra_deg: float
    dec_deg: float


@dataclass
class Crossing:
    norad_id: int
    name: str
    object_type: str
    category: str
    constellation: str | None
    mean_altitude_km: float
    eccentricity: float
    t_ca_utc: str
    separation_deg: float
    elevation_deg: float
    azimuth_deg: float
    range_km: float
    ra_deg: float
    dec_deg: float
    set_epoch_utc: str
    set_age_days: float
    partial: bool
    projection_cross: float
    projection_along: float
    population: str
    population_reason: str
    horizon: str
    fraction_inside: float | None
    cross_track_uncertainty_deg: float | None
    along_track_uncertainty_deg: float | None
    along_track_shift_s: float | None
    benchmark_window: str
    benchmark_lead_h: float | None
    benchmark_n_trials: int | None
    emission_status: str
    emission_detail: str
    samples: list[Sample] = field(default_factory=list)

    def record(self, with_samples: bool = True) -> dict[str, Any]:
        d = asdict(self)
        if not with_samples:
            d.pop("samples")
        return d


def population_label(mean_altitude_km: float, eccentricity: float, age_days: float) -> tuple[str, str]:
    """Whether the benchmark's measured horizon applies to an object, and why not when it does not."""
    lo, hi = MEASURED_ALTITUDE_KM
    if not (lo <= mean_altitude_km <= hi):
        return (
            "no measured horizon",
            f"mean altitude {mean_altitude_km:.0f} km is outside the {lo:.0f} to {hi:.0f} km benchmark population",
        )
    if eccentricity > MEASURED_MAX_ECCENTRICITY:
        return (
            "no measured horizon",
            f"eccentricity {eccentricity:.3f} is beyond the near-circular benchmark population",
        )
    if age_days > MEASURED_MAX_AGE_DAYS:
        return (
            "no measured horizon",
            f"element set {age_days:.1f} days old, beyond the benchmark's {MEASURED_MAX_AGE_DAYS:.0f}-day range",
        )
    return "measured", MEASURED_POPULATION


def _object_emission(object_type: str, constellation: str | None, rx: site_mod.Receiver) -> tuple[str, str]:
    if object_type in ("DEB", "R/B"):
        return "none expected", "debris or rocket body"
    return emissions.emission_status(constellation, rx)


class _Refiner:
    """The continuous angle from the boresight for one object, for the scalar minimiser."""

    def __init__(self, satrec, site: Site, t0: np.datetime64, bore_times_s: np.ndarray, bore_enu: np.ndarray):
        self.satrec = satrec
        self.site = site
        self.t0 = t0
        self.bore_times_s = bore_times_s
        self.bore_enu = bore_enu

    def boresight_at(self, t_s: float) -> np.ndarray:
        e = np.array([np.interp(t_s, self.bore_times_s, self.bore_enu[:, k]) for k in range(3)])
        return e / np.linalg.norm(e)

    def state(self, t_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        t = self.t0 + np.timedelta64(int(round(t_s * 1e6)), "us")
        jd, fr = julian_dates(np.array([t]))
        err, r, v = self.satrec.sgp4(float(jd[0]), float(fr[0]))
        if err:
            raise RuntimeError(f"sgp4 error {err}")
        r_teme = np.asarray(r, dtype=float)
        v_teme = np.asarray(v, dtype=float)
        r_pef = teme_to_pef(r_teme[None, :], np.array([t]))[0]
        v_rot = teme_to_pef(v_teme[None, :], np.array([t]))[0]
        return r_pef, v_rot, self.boresight_at(t_s), t

    def __call__(self, t_s: float) -> float:
        r_pef, _, bore, _ = self.state(t_s)
        return float(separation_deg(look_from(self.site, r_pef[None, :]).enu[0], bore))


def beam_crossings(
    catalogue: pd.DataFrame,
    site: Site,
    obs: Observation,
    trials: pd.DataFrame,
    period: Period,
    *,
    coarse_step_s: float = COARSE_STEP_S,
    fine_step_s: float = FINE_STEP_S,
) -> list[Crossing]:
    """Product two for one observation: every object whose track passes inside the half-power radius."""
    radius = obs.fwhm_deg / 2.0
    coarse = time_grid(obs.start, obs.duration_s, coarse_step_s)
    fine = time_grid(obs.start, obs.duration_s, fine_step_s)
    fine_s = (fine - fine[0]).astype("timedelta64[us]").astype("int64") / 1e6
    _, _, bore_coarse = boresight(site, obs.ra_deg, obs.dec_deg, coarse)
    bore_alt, bore_az, bore_fine = boresight(site, obs.ra_deg, obs.dec_deg, fine)
    if float(np.min(bore_alt)) < 0.0:
        log.warning(
            "%s: the boresight is below the horizon for part of the observation (min %.1f deg)",
            obs.observation_id,
            float(np.min(bore_alt)),
        )

    satrecs = build_satrecs(catalogue)
    ids = catalogue["norad_id"].to_numpy(dtype="int64")
    # Coarse pass: who could reach the beam between two samples.
    reach = np.zeros(len(satrecs), dtype=bool)
    for sl, r_teme, _ in _propagate_chunks(satrecs, ids, coarse):
        look = look_from(site, teme_to_pef(r_teme, coarse))
        sep = separation_deg(look.enu, bore_coarse[None, :, :])
        rng = np.nan_to_num(look.range_km, nan=np.inf)
        rate = np.degrees(MAX_TRANSVERSE_SPEED_KM_S / rng)  # deg/s at each sample
        margin = rate * (coarse_step_s / 2.0)
        ok = np.isfinite(sep) & (sep - margin <= radius)
        reach[sl] = ok.any(axis=1)
    cand = np.flatnonzero(reach)
    log.info(
        "%s: %d of %d objects could reach the beam between coarse samples", obs.observation_id, len(cand), len(satrecs)
    )

    t0 = fine[0]
    crossings: list[Crossing] = []
    cand_satrecs = [satrecs[i] for i in cand]
    for sl, r_teme, _ in _propagate_chunks(cand_satrecs, ids[cand], fine, chunk=500):
        look = look_from(site, teme_to_pef(r_teme, fine))
        sep = separation_deg(look.enu, bore_fine[None, :, :])
        rng = np.nan_to_num(look.range_km, nan=np.inf)
        margin = np.degrees(MAX_TRANSVERSE_SPEED_KM_S / rng) * (fine_step_s / 2.0)
        for j in range(sep.shape[0]):
            s = sep[j]
            if not np.isfinite(s).any():
                continue
            s_filled = np.where(np.isfinite(s), s, np.inf)
            left = np.r_[np.inf, s_filled[:-1]]
            right = np.r_[s_filled[1:], np.inf]
            minima = np.flatnonzero((s_filled <= left) & (s_filled <= right) & (s_filled - margin[j] <= radius))
            row = catalogue.iloc[int(cand[sl][j])]
            refiner = _Refiner(cand_satrecs[sl][j], site, t0, fine_s, bore_fine)
            for k in minima:
                lo = max(float(fine_s[k]) - 1.5 * fine_step_s, 0.0)
                hi = min(float(fine_s[k]) + 1.5 * fine_step_s, float(fine_s[-1]))
                if hi > lo:
                    res = minimize_scalar(refiner, bounds=(lo, hi), method="bounded", options={"xatol": 0.01})
                    t_ca_s, closest = float(res.x), float(res.fun)
                else:
                    t_ca_s, closest = float(fine_s[k]), float(s_filled[k])
                if closest > radius:
                    continue
                partial = bool(k == 0 or k == len(s_filled) - 1)
                crossings.append(
                    _describe(row, refiner, t_ca_s, closest, partial, obs, trials, period, site, float(fine_s[-1]))
                )
    crossings.sort(key=lambda c: c.t_ca_utc)
    log.info("%s: %d crossing(s) inside the %.2f deg half-power radius", obs.observation_id, len(crossings), radius)
    return crossings


SAMPLE_STEP_S = 0.1


def _in_beam_samples(
    refiner: _Refiner, site: Site, t_ca_s: float, range_km: float, radius: float, t_end_s: float
) -> list[Sample]:
    """The track through the beam, sampled every tenth of a second, for the export's position records.

    A low object crosses a half-degree beam in under a second, so the one-second search grid can
    hold no sample inside it; the window here is the time the object would need to cross the
    radius at the fastest transverse speed any bound orbit can have at its range, plus a second.
    """
    rate = np.degrees(MAX_TRANSVERSE_SPEED_KM_S / range_km)  # deg/s, an upper bound
    half = radius / max(rate, 1e-9) + 1.0
    ts = np.arange(max(0.0, t_ca_s - half), min(t_end_s, t_ca_s + half) + 1e-9, SAMPLE_STEP_S)
    kept: list[tuple[np.datetime64, float, float, float, float]] = []
    for t_s in ts:
        r_pef, _, bore, t = refiner.state(float(t_s))
        lk = look_from(site, r_pef[None, :])
        sep = float(separation_deg(lk.enu[0], bore))
        if sep <= radius:
            kept.append((t, float(lk.elevation_deg[0]), float(lk.azimuth_deg[0]), float(lk.range_km[0]), sep))
    if not kept:
        return []
    times = np.array([k[0] for k in kept], dtype="datetime64[us]")
    alts = np.array([k[1] for k in kept])
    azs = np.array([k[2] for k in kept])
    ras, decs = site_mod.sky_from_alt_az(site, alts, azs, times)
    jd, fr = julian_dates(times)
    return [
        Sample(
            time_utc=str(np.datetime_as_string(times[n], unit="ms")) + "Z",
            julian_date=float(jd[n] + fr[n]),
            elevation_deg=float(alts[n]),
            azimuth_deg=float(azs[n]),
            range_km=kept[n][3],
            separation_deg=kept[n][4],
            ra_deg=float(ras[n]),
            dec_deg=float(decs[n]),
        )
        for n in range(len(kept))
    ]


def _describe(
    row,
    refiner: _Refiner,
    t_ca_s: float,
    closest: float,
    partial: bool,
    obs: Observation,
    trials: pd.DataFrame,
    period: Period,
    site: Site,
    t_end_s: float,
) -> Crossing:
    r_pef, v_rot, _, t_ca = refiner.state(t_ca_s)
    lk = look_from(site, r_pef[None, :])
    range_km = float(lk.range_km[0])
    los = (r_pef - site.ecef_km()) / range_km
    basis = ric_basis(r_pef[None, :], v_rot[None, :])[0]
    g_r, g_i, g_c = (float(sky_projection(basis[k], los)) for k in range(3))
    t_ca_dt = pd.Timestamp(t_ca).tz_localize("UTC")
    epoch = pd.Timestamp(row["epoch"])
    epoch = epoch.tz_localize("UTC") if epoch.tzinfo is None else epoch.tz_convert("UTC")
    age_days = (t_ca_dt - epoch).total_seconds() / 86400.0
    mean_alt = float(row["mean_altitude_km"])
    ecc = float(row["eccentricity"])
    population, reason = population_label(mean_alt, ecc, age_days)
    unc: CrossingUncertainty | None = None
    horizon = "no measured horizon"
    if population == "measured":
        unc = horizon_mod.crossing_uncertainty(
            trials, period.benchmark_window, age_days * 24.0, range_km, g_c, g_i, obs.fwhm_deg
        )
        if unc is None:
            population, reason = (
                "no measured horizon",
                f"element set {age_days:.1f} days old, beyond the benchmark's leads",
            )
        else:
            horizon = "inside" if unc.fraction_inside >= COVERAGE else "outside"
    else:
        # The geometry is still reported against the matching window, for the reader's scale, but no label rests on it.
        unc = None
    ra, dec = site_mod.sky_from_alt_az(site, lk.elevation_deg, lk.azimuth_deg, np.array([t_ca]))
    samples = _in_beam_samples(refiner, site, t_ca_s, range_km, obs.fwhm_deg / 2.0, t_end_s)
    status, detail = _object_emission(str(row["object_type"]), row["constellation"], obs.receiver)
    return Crossing(
        norad_id=int(row["norad_id"]),
        name=str(row["name"]),
        object_type=str(row["object_type"]),
        category=str(row["category"]),
        constellation=row["constellation"] if isinstance(row["constellation"], str) else None,
        mean_altitude_km=mean_alt,
        eccentricity=ecc,
        t_ca_utc=t_ca_dt.isoformat().replace("+00:00", "Z"),
        separation_deg=closest,
        elevation_deg=float(lk.elevation_deg[0]),
        azimuth_deg=float(lk.azimuth_deg[0]),
        range_km=range_km,
        ra_deg=float(ra[0]),
        dec_deg=float(dec[0]),
        set_epoch_utc=epoch.isoformat().replace("+00:00", "Z"),
        set_age_days=age_days,
        partial=partial,
        projection_cross=g_c,
        projection_along=g_i,
        population=population,
        population_reason=reason,
        horizon=horizon,
        fraction_inside=unc.fraction_inside if unc else None,
        cross_track_uncertainty_deg=unc.cross_p95_deg if unc else None,
        along_track_uncertainty_deg=unc.along_p95_deg if unc else None,
        along_track_shift_s=unc.along_shift_p95_s if unc else None,
        benchmark_window=period.benchmark_window,
        benchmark_lead_h=unc.lead_h if unc else None,
        benchmark_n_trials=unc.n_trials if unc else None,
        emission_status=status,
        emission_detail=detail,
        samples=samples,
    )


# --------------------------------------------------------------------------------------
# Running a period


@dataclass
class ObservationResult:
    observation: Observation
    n_catalogue: int
    catalogue_at: str
    counts: list[ConstellationCount]
    crossings: list[Crossing]


def run_observation(
    sets: pd.DataFrame,
    satcat_frame: pd.DataFrame | None,
    site: Site,
    obs: Observation,
    trials: pd.DataFrame,
    period: Period,
    *,
    elevation_deg: float = ELEVATION_CUTOFF_DEG,
) -> ObservationResult:
    cat = catalogue_at(sets, satcat_frame, obs.start)
    log.info(
        "%s: catalogue as of %s holds %d objects (newest set at or before, no older than %g days)",
        obs.observation_id,
        obs.start.isoformat(),
        len(cat),
        CATALOGUE_MAX_AGE_DAYS,
    )
    counts = constellation_view(cat, site, obs.start, obs.duration_s, obs.receiver, elevation_deg=elevation_deg)
    crossings = beam_crossings(cat, site, obs, trials, period)
    return ObservationResult(obs, len(cat), obs.start.isoformat().replace("+00:00", "Z"), counts, crossings)


def summarise_hourly(hourly: pd.DataFrame) -> pd.DataFrame:
    """Per constellation over the period: catalogued members, and the mean and peak number up at once."""
    if hourly.empty:
        return hourly
    g = hourly.groupby("constellation", sort=False)
    out = pd.DataFrame(
        {
            "n_catalogued": g["n_catalogued"].max(),
            "mean_simultaneous": g["mean_simultaneous"].mean(),
            "max_simultaneous": g["max_simultaneous"].max(),
            "status": g["status"].first(),
            "detail": g["detail"].first(),
        }
    )
    order = [c for c in emissions.CONSTELLATIONS if c in out.index]
    return out.loc[order].reset_index()


def sets_provenance(sets: pd.DataFrame, history_dir: Path = config.HISTORY_DIR) -> dict[str, Any]:
    return {
        "n_sets": int(len(sets)),
        "n_objects": int(sets["norad_id"].nunique()),
        "epoch_min": pd.to_datetime(sets["epoch"], utc=True).min().isoformat(),
        "epoch_max": pd.to_datetime(sets["epoch"], utc=True).max().isoformat(),
        "history_dir": horizon_mod.repo_relative(history_dir),
        "source": "Space-Track gp_history through driftwatch's history store; each object's newest set at or before "
        "the observation start, none later",
    }


def in_beam_ids(crossings: Iterable[Crossing]) -> list[int]:
    return sorted({c.norad_id for c in crossings})
