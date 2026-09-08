"""Predicted passages and paired topocentric track comparisons.

Historical catalogue displays select the latest archived element epoch before a
cutoff; publication-time availability is unknown. Their circular analytic beam
finder is a modelled-passage illustration, not an observed detection or accuracy
validation. Scalar component diagnostics require reference-mission identity,
calibration scope and measured age; they never establish crossing guarantees.

The corrected comparison API uses both complete orbit vectors, the rotating
observer, a fixed celestial boresight and an explicit measured beam response. It
evaluates nominal entrants and near misses and distinguishes timing across an
observation edge from beam-entry disagreement over the whole search interval.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq, minimize_scalar

from driftwatch import claims, config
from driftwatch.catalogue import history, snapshot
from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs
from driftwatch.orbit.time import julian_dates
from driftwatch.radio import emissions
from driftwatch.radio import horizon as horizon_mod
from driftwatch.radio import site as site_mod
from driftwatch.radio.horizon import ComponentDiagnostic
from driftwatch.radio.observations import Observation
from driftwatch.radio.site import Site, boresight, look_from, separation_deg, sky_projection, teme_to_pef
from driftwatch.screening.ric import ric_basis
from driftwatch.storm import precise

log = logging.getLogger(__name__)

# The population the reference benchmark measured: near-circular, free-flying spacecraft in the
# altitude bands of ``storm/reference.py``. An object is scored against its own band's trials;
# identity and scope are required in addition to an altitude band. The bands with trials are read from the
# trials themselves at run time; this tuple is the full set the benchmark defines.
MEASURED_BANDS: tuple[str, ...] = horizon_mod.BAND_ORDER
MEASURED_MAX_ECCENTRICITY = 0.02
MEASURED_MAX_AGE_DAYS = 7.0
MEASURED_MIN_AGE_DAYS = 6.0 / 24.0
REFERENCE_SCOPE = "public_gp_manoeuvre_excluded_reference_mission"
ELIGIBLE_MISSIONS = {
    m.norad_id: m.key for m in horizon_mod.reference.MISSIONS.values() if m.truth != horizon_mod.reference.TRUTH_NONE
}

# The elevation above which an object counts as in the sky for product one. MeerKAT observes
# above 15 degrees; a sidelobe has no such limit, and the local horizon is a degree or two.
ELEVATION_CUTOFF_DEG = 10.0
# Newest set at or before the observation, no older than this, or the object is not in the catalogue that day.
CATALOGUE_MAX_AGE_DAYS = 7.0
# An assumed exclusion interval used by the historical diagnostic. This is not a known fit arc,
# and a candidate element jump does not establish that an operator manoeuvre occurred.
FIT_ARC_HOURS = precise.MANOEUVRE_ARC_HOURS

COARSE_STEP_S = 10.0
FINE_STEP_S = 1.0
# The fastest a low object can move across the sky: orbital speed over the range. 7.9 km/s is
# the circular speed at the Earth's surface, an upper bound for any bound orbit's transverse speed.
MAX_TRANSVERSE_SPEED_KM_S = 7.9
CHUNK_OBJECTS = 4000


@dataclass
class SkyTrack:
    """A sampled complete topocentric direction curve and a fixed celestial pointing.

    Interpolation is only inside the supplied, gap-free time span. The directions
    must already include observer rotation at every sample; scalar R/I/C errors
    cannot construct this object. Cadence is retained for convergence checks.
    """

    seconds: np.ndarray
    sightline_enu: np.ndarray
    boresight_enu: np.ndarray
    _sight: CubicSpline = field(init=False, repr=False)
    _bore: CubicSpline = field(init=False, repr=False)

    def __post_init__(self) -> None:
        t = np.asarray(self.seconds, dtype=float)
        if t.ndim != 1 or len(t) < 4 or not np.isfinite(t).all() or not np.all(np.diff(t) > 0):
            raise ValueError("a sky track needs at least four increasing finite times")
        for values in (self.sightline_enu, self.boresight_enu):
            a = np.asarray(values, dtype=float)
            if a.shape != (len(t), 3) or not np.isfinite(a).all() or np.any(np.linalg.norm(a, axis=1) == 0):
                raise ValueError("a sky track needs finite three-dimensional directions at every time")
        self.seconds = t
        self._sight = CubicSpline(t, self.sightline_enu, axis=0, extrapolate=False)
        self._bore = CubicSpline(t, self.boresight_enu, axis=0, extrapolate=False)

    def directions(self, seconds) -> tuple[np.ndarray, np.ndarray]:
        t = np.asarray(seconds, dtype=float)
        if np.any((t < self.seconds[0]) | (t > self.seconds[-1])):
            raise ValueError("sky-track extrapolation is not permitted")
        sight, bore = self._sight(t), self._bore(t)
        return sight / np.linalg.norm(sight, axis=-1, keepdims=True), bore / np.linalg.norm(
            bore, axis=-1, keepdims=True
        )

    def separation(self, seconds) -> np.ndarray:
        return separation_deg(*self.directions(seconds))

    def power(self, seconds, response: Callable) -> np.ndarray:
        x, y = site_mod.beam_offsets_deg(*self.directions(seconds))
        return np.asarray(response(x, y), dtype=float)


@dataclass(frozen=True)
class BeamInterval:
    entry_s: float
    exit_s: float
    entry_censored: bool = False
    exit_censored: bool = False


@dataclass
class TrackMeasurement:
    closest_time_s: float
    closest_separation_deg: float
    peak_time_s: float
    peak_normalized_power: float
    intervals: list[BeamInterval]
    observation_crossed: bool
    observation_entry_s: float | None
    observation_exit_s: float | None
    observation_start_inside: bool
    observation_end_inside: bool
    input_max_step_s: float
    closest_time_censored: bool
    peak_time_censored: bool
    half_power_peak_margin: float
    tangential_contact: bool


@dataclass
class TrackComparison:
    prediction: TrackMeasurement
    reference: TrackMeasurement
    false_crossing: bool
    missed_crossing: bool
    both_crossed: bool
    observation_edge_mismatch: bool
    closest_time_error_s: float
    closest_separation_error_deg: float
    entry_time_error_s: float | None
    exit_time_error_s: float | None
    instantaneous_error_at_reference_closest_deg: float
    max_sampled_instantaneous_error_deg: float
    beam: dict[str, Any]
    observation_interval_s: tuple[float, float]

    def record(self) -> dict[str, Any]:
        return asdict(self)


def _measure_track(
    track: SkyTrack,
    response: Callable,
    observation_interval_s: tuple[float, float],
    *,
    time_tolerance_s: float,
) -> TrackMeasurement:
    """Find minima, beam peaks, and half-power entry/exit roots, including near misses."""
    t = track.seconds
    separation = track.separation(t)
    power = track.power(t, response)
    if not np.isfinite(power).all():
        raise ValueError("beam response contains unknown values on the supplied track")
    minima = np.flatnonzero(
        (separation <= np.r_[np.inf, separation[:-1]]) & (separation <= np.r_[separation[1:], np.inf])
    )
    maxima = np.flatnonzero((power >= np.r_[-np.inf, power[:-1]]) & (power >= np.r_[power[1:], -np.inf]) & (power > 0))
    angular_candidates = [float(t[0]), float(t[-1])]
    peak_candidates = [float(t[0]), float(t[-1])]
    for k in np.unique(np.r_[minima, maxima]):
        lo, hi = float(t[max(0, k - 1)]), float(t[min(len(t) - 1, k + 1)])
        if hi <= lo:
            continue
        angular = minimize_scalar(
            lambda s: float(track.separation(s)), bounds=(lo, hi), method="bounded", options={"xatol": time_tolerance_s}
        )
        peak = minimize_scalar(
            lambda s: -float(track.power(s, response)),
            bounds=(lo, hi),
            method="bounded",
            options={"xatol": time_tolerance_s},
        )
        angular_candidates.append(float(angular.x))
        peak_candidates.extend([float(peak.x), float(angular.x)])
    closest = min(angular_candidates, key=lambda s: float(track.separation(s)))
    peak_time = max(peak_candidates, key=lambda s: float(track.power(s, response)))
    # Inserting refined peaks catches brief crossings between the original samples.
    knots = np.unique(np.r_[t, angular_candidates, peak_candidates])
    values = track.power(knots, response) - 0.5
    roots: list[float] = []
    for left, right, a, b in zip(knots[:-1], knots[1:], values[:-1], values[1:], strict=True):
        if a == 0:
            roots.append(float(left))
        if a * b < 0:
            roots.append(
                float(brentq(lambda s: float(track.power(s, response)) - 0.5, left, right, xtol=time_tolerance_s))
            )
    if values[-1] == 0:
        roots.append(float(knots[-1]))
    edges = np.unique(np.r_[t[0], roots, t[-1]])
    intervals: list[BeamInterval] = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        if float(track.power((lo + hi) / 2.0, response)) >= 0.5:
            intervals.append(
                BeamInterval(
                    float(lo), float(hi), bool(lo == t[0] and power[0] >= 0.5), bool(hi == t[-1] and power[-1] >= 0.5)
                )
            )
    obs_lo, obs_hi = observation_interval_s
    clipped = [
        (max(i.entry_s, obs_lo), min(i.exit_s, obs_hi))
        for i in intervals
        if min(i.exit_s, obs_hi) > max(i.entry_s, obs_lo)
    ]
    return TrackMeasurement(
        closest_time_s=float(closest),
        closest_separation_deg=float(track.separation(closest)),
        peak_time_s=float(peak_time),
        peak_normalized_power=float(track.power(peak_time, response)),
        intervals=intervals,
        observation_crossed=bool(clipped),
        observation_entry_s=clipped[0][0] if clipped else None,
        observation_exit_s=clipped[-1][1] if clipped else None,
        observation_start_inside=bool(float(track.power(obs_lo, response)) >= 0.5),
        observation_end_inside=bool(float(track.power(obs_hi, response)) >= 0.5),
        input_max_step_s=float(np.max(np.diff(t))),
        closest_time_censored=bool(min(closest - t[0], t[-1] - closest) <= time_tolerance_s),
        peak_time_censored=bool(min(peak_time - t[0], t[-1] - peak_time) <= time_tolerance_s),
        half_power_peak_margin=float(track.power(peak_time, response)) - 0.5,
        tangential_contact=bool(not intervals and abs(float(track.power(peak_time, response)) - 0.5) < 1e-8),
    )


def compare_sky_tracks(
    prediction: SkyTrack,
    reference: SkyTrack,
    response: Callable,
    *,
    beam_record: dict[str, Any],
    observation_interval_s: tuple[float, float] | None = None,
    time_tolerance_s: float = 0.001,
) -> TrackComparison:
    """Paired crossing classification, timing and complete angular errors.

    Both curves are always evaluated, including predicted misses. Input curves
    must span the same times and identical pointing. A shorter observation inside
    the search interval distinguishes timing across an observation edge from a
    geometric miss. This function does not infer a population coverage guarantee.
    """
    if not np.array_equal(prediction.seconds, reference.seconds):
        raise ValueError("prediction and reference must use the same time samples")
    if not np.allclose(prediction.boresight_enu, reference.boresight_enu, atol=1e-12, rtol=0):
        raise ValueError("prediction and reference must use the same fixed celestial pointing")
    t = prediction.seconds
    interval = observation_interval_s or (float(t[0]), float(t[-1]))
    if interval[0] < t[0] or interval[1] > t[-1] or interval[0] >= interval[1]:
        raise ValueError("observation interval must lie inside the common search span")
    p = _measure_track(prediction, response, interval, time_tolerance_s=time_tolerance_s)
    r = _measure_track(reference, response, interval, time_tolerance_s=time_tolerance_s)
    false, missed = (
        p.observation_crossed and not r.observation_crossed,
        r.observation_crossed and not p.observation_crossed,
    )
    entry = exit_ = None
    if len(p.intervals) == len(r.intervals) == 1:
        pi, ri = p.intervals[0], r.intervals[0]
        if not pi.entry_censored and not ri.entry_censored:
            entry = pi.entry_s - ri.entry_s
        if not pi.exit_censored and not ri.exit_censored:
            exit_ = pi.exit_s - ri.exit_s
    pred_at, _ = prediction.directions(r.closest_time_s)
    ref_at, _ = reference.directions(r.closest_time_s)
    instant = separation_deg(prediction.directions(t)[0], reference.directions(t)[0])
    return TrackComparison(
        p,
        r,
        bool(false),
        bool(missed),
        p.observation_crossed and r.observation_crossed,
        bool((false or missed) and p.intervals and r.intervals),
        p.closest_time_s - r.closest_time_s,
        p.closest_separation_deg - r.closest_separation_deg,
        entry,
        exit_,
        float(separation_deg(pred_at, ref_at)),
        float(np.max(instant)),
        dict(beam_record),
        interval,
    )


def compare_orbit_tracks(
    times,
    prediction_teme_km: np.ndarray,
    reference_teme_km: np.ndarray,
    site: Site,
    ra_deg: float,
    dec_deg: float,
    beam: site_mod.MeasuredBeam,
    *,
    observation_interval_s: tuple[float, float] | None = None,
) -> TrackComparison:
    """The corrected end-to-end comparison, using a measured beam and full positions.

    Inputs are positions at explicit UTC times from SGP4 and the independently
    reconstructed orbit. No data fetching, orbit selection or scoring of stored
    trials occurs implicitly. Report actual element age and constructed-pointing
    provenance alongside each returned measurement in the benchmark runner.
    """
    dates = np.asarray(times, dtype="datetime64[us]")
    seconds = (dates - dates[0]) / np.timedelta64(1, "s")
    predicted = site_mod.look_from_teme(site, prediction_teme_km, dates)
    reconstructed = site_mod.look_from_teme(site, reference_teme_km, dates)
    with site_mod.iers.conf.set_temp("auto_download", False):
        _, _, bore = boresight(site, ra_deg, dec_deg, dates)
    return compare_sky_tracks(
        SkyTrack(seconds, predicted.enu, bore),
        SkyTrack(seconds, reconstructed.enu, bore),
        beam.power,
        beam_record=beam.record(),
        observation_interval_s=observation_interval_s,
    )


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
# The archived catalogue selected by element epoch


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
    """Epoch-based reconstruction at ``at``; membership and publication availability are not established."""
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
    """Product one over a whole period, hour by hour, using the archived element-epoch cutoff at each hour.

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
    cross_track_uncertainty_deg: float | None
    along_track_uncertainty_deg: float | None
    along_track_shift_s: float | None
    benchmark_window: str
    benchmark_lead_h: float | None
    benchmark_n_trials: int | None
    emission_status: str
    emission_detail: str
    manoeuvre_detected_between: list[str] | None = (
        None  # the two element epochs around the last candidate discontinuity
    )
    hours_since_manoeuvre: float | None = None  # time since the later element epoch, not since a known burn
    fit_arc_spanned_manoeuvre: bool | None = None  # the assumed exclusion interval before the epoch overlaps it
    manoeuvre_detection: str = "no detection"  # what was searched, and what it found
    next_set_shows_jump: bool | None = None  # retrospective: the set after this one shows a jump it may omit
    samples: list[Sample] = field(default_factory=list)
    orbit_quality: dict[str, Any] = field(default_factory=dict)

    def record(self, with_samples: bool = True) -> dict[str, Any]:
        d = asdict(self)
        d["component_error_diagnostics"] = {
            "cross_track_p95_deg": d.pop("cross_track_uncertainty_deg", None),
            "in_track_p95_deg": d.pop("along_track_uncertainty_deg", None),
            "orbital_phase_time_p95_s": d.pop("along_track_shift_s", None),
            "interpretation": "orbital-component scales only; not a crossing or beam-timing guarantee",
        }
        d["candidate_discontinuity"] = {
            "between_element_epochs": d.pop("manoeuvre_detected_between", None),
            "hours_since_later_element_epoch": d.pop("hours_since_manoeuvre", None),
            "overlaps_assumed_exclusion_arc": d.pop("fit_arc_spanned_manoeuvre", None),
            "next_set_shows_jump": d.pop("next_set_shows_jump", None),
            "evidence": d.pop("manoeuvre_detection", None),
            "fit_arc_known": False,
            "publication_time_known": False,
        }
        if not with_samples:
            d.pop("samples")
        return d


def population_label(
    mean_altitude_km: float,
    eccentricity: float,
    age_days: float,
    bands: Iterable[str] = MEASURED_BANDS,
    *,
    norad_id: int | None = None,
    object_type: str = "PAY",
    scope: str | None = None,
) -> tuple[str, str]:
    """Eligibility for reference-population component diagnostics, never generic altitude transfer.

    Identity, an explicitly qualified manoeuvre-excluded public-GP scope and a
    measured age are all required. Even an eligible mission has no calibrated
    beam-crossing guarantee from the scalar component table.
    """
    measured = list(bands)
    if not np.isfinite(mean_altitude_km) or not np.isfinite(eccentricity) or eccentricity < 0:
        return "unsupported", "altitude and non-negative eccentricity must be finite"
    band = horizon_mod.band_of(mean_altitude_km)
    if band is None or band not in measured:
        return (
            "unsupported",
            f"mean altitude {mean_altitude_km:.0f} km is outside the measured altitude bands "
            f"({', '.join(measured) or 'none'})",
        )
    if eccentricity > MEASURED_MAX_ECCENTRICITY:
        return (
            "unsupported",
            f"eccentricity {eccentricity:.3f} is beyond the near-circular benchmark population",
        )
    if age_days > MEASURED_MAX_AGE_DAYS:
        return (
            "unsupported",
            f"element set {age_days:.1f} days old, beyond the benchmark's {MEASURED_MAX_AGE_DAYS:.0f}-day range",
        )
    if age_days < MEASURED_MIN_AGE_DAYS or not np.isfinite(age_days):
        return "unsupported", "element age is outside the measured 6 to 168 hour range"
    if norad_id not in ELIGIBLE_MISSIONS or object_type != "PAY":
        return "unsupported", "object identity or class is outside the fifteen reference missions"
    if scope != REFERENCE_SCOPE:
        return "unsupported", "manoeuvre-excluded public-GP calibration scope is not established"
    return "reference_component_diagnostics", band


def _object_emission(object_type: str, constellation: str | None, rx: site_mod.Receiver) -> tuple[str, str]:
    if object_type in ("DEB", "R/B"):
        return "none expected", "debris or rocket body"
    return emissions.emission_status(constellation, rx)


class ManoeuvreContext(NamedTuple):
    """What the object's own element sets say about its last burn, for one crossing."""

    between: list[str] | None  # the two element epochs around the last candidate discontinuity
    hours_since: float | None  # time since the later element epoch, not since a known burn
    fit_arc_spanned: bool | None  # the assumed exclusion interval reaches the candidate epoch interval
    next_set_shows_jump: bool | None  # retrospective: the set after this one shows a jump this one may omit
    detection: str  # what was searched, and what it found


def last_manoeuvre(
    own_sets: pd.DataFrame | None, epoch: pd.Timestamp, t_ca: pd.Timestamp, *, arc_hours: float = FIT_ARC_HOURS
) -> ManoeuvreContext:
    """A candidate element discontinuity, plus a retrospective next-set mark.

    Endpoints are element epochs, not a known burn interval or publication times.
    ``hours_since`` counts from the later epoch. ``fit_arc_spanned`` is retained
    internally for compatibility but means overlap with an assumed exclusion
    interval, not knowledge of the catalogue's fit arc. A true next-set mark is
    evidence of an element change; false does not establish absence of a burn.
    ``epoch`` and ``t_ca`` are naive UTC.
    """
    if own_sets is None or not len(own_sets):
        return ManoeuvreContext(None, None, None, None, "no detection: no element-set history held")
    ordered = own_sets.assign(_e=pd.to_datetime(own_sets["epoch"], utc=True).dt.tz_convert(None))
    ordered = ordered.sort_values("_e").drop_duplicates("_e", keep="last")
    own = ordered[ordered["_e"] <= epoch]
    following = ordered[ordered["_e"] > epoch].head(2)
    if len(own) < 2:
        return ManoeuvreContext(
            None, None, None, None, "no detection: fewer than two element sets held at or before the epoch"
        )
    first, last = own["_e"].iloc[0], own["_e"].iloc[-1]
    searched = f"set-jump detector on {len(own)} sets from {first:%Y-%m-%d} to {last:%Y-%m-%d}"
    intervals = precise.manoeuvre_intervals_from_sets(own.drop(columns="_e"))
    next_shows: bool | None = None
    tail = "; no following set held"
    if len(following):
        later = precise.manoeuvre_intervals_from_sets(pd.concat([own, following]).drop(columns="_e"))
        next_shows = any(abs(lo - last) < pd.Timedelta(seconds=1) for lo, _ in later)
        tail = "; the following set shows a jump" if next_shows else "; the following set shows no jump"
    if not intervals:
        return ManoeuvreContext(None, None, False, next_shows, f"{searched}: none found{tail}")
    lo, hi = intervals[-1]
    spanned = bool(lo <= epoch and hi >= epoch - pd.Timedelta(hours=arc_hours))
    since_h = float((t_ca - hi).total_seconds() / 3600.0)
    between = [lo.isoformat() + "Z", hi.isoformat() + "Z"]
    return ManoeuvreContext(
        between, since_h, spanned, next_shows, f"{searched}: last found between {between[0]} and {between[1]}{tail}"
    )


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
    sets: pd.DataFrame | None = None,
) -> list[Crossing]:
    """Product two for one observation: every object whose track passes inside the half-power radius.

    ``sets`` is the element-set history the catalogue was built from; each crossing object's own sets at
    or before its epoch go to the manoeuvre detector. Without it the manoeuvre fields are null.
    """
    radius = obs.fwhm_deg / 2.0
    bands = tuple(horizon_mod.bands_present(trials))
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
            own = None if sets is None else sets[sets["norad_id"] == int(row["norad_id"])]
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
                    _describe(
                        row,
                        refiner,
                        t_ca_s,
                        closest,
                        partial,
                        obs,
                        trials,
                        period,
                        site,
                        float(fine_s[-1]),
                        bands,
                        own_sets=own,
                    )
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
    bands: tuple[str, ...] | None = None,
    own_sets: pd.DataFrame | None = None,
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
    measured_bands = bands if bands is not None else tuple(horizon_mod.bands_present(trials))
    scope = row.get("benchmark_scope")
    population, reason = population_label(
        mean_alt,
        ecc,
        age_days,
        measured_bands,
        norad_id=int(row["norad_id"]),
        object_type=str(row["object_type"]),
        scope=scope,
    )
    unc: ComponentDiagnostic | None = None
    if population == "reference_component_diagnostics":
        # The object's own band's trials, projected onto this crossing's line of sight.
        unc = horizon_mod.component_diagnostic(
            trials, period.benchmark_window, age_days * 24.0, range_km, g_c, g_i, obs.fwhm_deg, band=reason
        )
        if unc is None:
            population, reason = (
                "unsupported",
                f"element set {age_days:.1f} days old, beyond the benchmark's leads",
            )
    else:
        # The geometry is still reported against the matching window, for the reader's scale, but no label rests on it.
        unc = None
    ra, dec = site_mod.sky_from_alt_az(site, lk.elevation_deg, lk.azimuth_deg, np.array([t_ca]))
    samples = _in_beam_samples(refiner, site, t_ca_s, range_km, obs.fwhm_deg / 2.0, t_end_s)
    status, detail = _object_emission(str(row["object_type"]), row["constellation"], obs.receiver)
    context = last_manoeuvre(own_sets, epoch.tz_convert(None), t_ca_dt.tz_convert(None))
    estimate = None
    if unc is not None:
        group = trials[
            (trials["window"] == unc.window) & (trials["lead_h"] == unc.lead_h) & (trials["altitude_band"] == unc.band)
        ]
        estimate = {
            "method_version": "reference_orbital_component_projection_v2",
            "scope": REFERENCE_SCOPE,
            "window": unc.window,
            "lead_bin_h": unc.lead_h,
            "n_trials": unc.n_trials,
            "n_missions": int(group["mission"].nunique()),
            "n_element_sets": int(len(group[["norad_id", "set_epoch"]].drop_duplicates())),
            "reference_rows_sha256": hashlib.sha256(
                pd.util.hash_pandas_object(group, index=False).values.tobytes()
            ).hexdigest(),
            "cross_track_component_p95_deg": unc.cross_p95_deg,
            "in_track_component_p95_deg": unc.along_p95_deg,
            "orbital_phase_time_p95_s": unc.along_shift_p95_s,
            "interpretation": "conditional reference-population component estimates; "
            "no per-object sky-position, beam-entry or beam-timing coverage",
        }
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
        cross_track_uncertainty_deg=unc.cross_p95_deg if unc else None,
        along_track_uncertainty_deg=unc.along_p95_deg if unc else None,
        along_track_shift_s=unc.along_shift_p95_s if unc else None,
        benchmark_window=period.benchmark_window,
        benchmark_lead_h=unc.lead_h if unc else None,
        benchmark_n_trials=unc.n_trials if unc else None,
        emission_status=status,
        emission_detail=detail,
        manoeuvre_detected_between=context.between,
        hours_since_manoeuvre=context.hours_since,
        fit_arc_spanned_manoeuvre=context.fit_arc_spanned,
        manoeuvre_detection=context.detection,
        next_set_shows_jump=context.next_set_shows_jump,
        samples=samples,
        orbit_quality={
            "schema_version": 2,
            "status": "reference_component_diagnostics"
            if population == "reference_component_diagnostics"
            else "unsupported",
            "applicability_label": claims.wording(
                "applicability:eligible"
                if population == "reference_component_diagnostics"
                else "applicability:unsupported"
            ),
            "claim": claims.identity(
                "applicability:eligible"
                if population == "reference_component_diagnostics"
                else "applicability:unsupported"
            ),
            "mission": ELIGIBLE_MISSIONS.get(int(row["norad_id"])),
            "scope": scope if isinstance(scope, str) else None,
            "epoch_age_h": age_days * 24.0,
            "measured_age_range_h": [6.0, 168.0],
            "band": horizon_mod.band_of(mean_alt),
            "reason": reason,
            "crossing_classification_calibrated": False,
            "publication_age_h": None,
            "reference_population_estimate": estimate,
        },
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
        "%s: archived epoch cutoff %s holds %d objects (latest element epoch, no older than %g days)",
        obs.observation_id,
        obs.start.isoformat(),
        len(cat),
        CATALOGUE_MAX_AGE_DAYS,
    )
    counts = constellation_view(cat, site, obs.start, obs.duration_s, obs.receiver, elevation_deg=elevation_deg)
    crossings = beam_crossings(cat, site, obs, trials, period, sets=sets)
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
        "source": "Space-Track gp_history; latest archived element epoch before observation start, "
        "not reconstructed publication-time availability",
        "publication_time_availability_known": False,
    }


def in_beam_ids(crossings: Iterable[Crossing]) -> list[int]:
    return sorted({c.norad_id for c in crossings})
