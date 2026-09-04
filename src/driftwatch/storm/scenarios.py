"""The named scenarios, and the covariance model each of them hands to ``driftwatch risk``.

A scenario is a statement about the atmosphere over the screening window. It changes two
things and nothing else: **where** each object is at the stored time of closest approach, and
**how uncertain** that is. The geometry -- which pairs, at what time, with what relative
velocity -- was settled by Stages A to C and is not touched, exactly as Phase 2 designed.

## The five

``quiet``
    The Phase 2 model, untouched, with no storm layer at all. This is deliberate and it is the
    one scenario whose numbers must not move: it is the regression baseline the whole phase is
    read against, and every other scenario is a difference from it. It is also the honest
    reading of "observed conditions", because the empirical covariance underneath it was fitted
    on real element sets that flew through whatever weather actually happened.
``forecast``
    The space weather table as Step 1 layers it: observed where the record reaches, SWPC's
    three-day Kp forecast after that, the 27-day outlook beyond, each row carrying its own
    provenance, skill and issue time. This is the live operational scenario.
``storm-g3``, ``storm-g4``, ``storm-g5``
    The May 2024 sequence scaled to a target peak Kp and dropped into the window at a stated
    offset (:data:`driftwatch.config.STORM_OFFSET_DAYS`). Synthetic: the rows it replaces say
    so, and their skill is ``designed``.
``replay:<date>``
    The observed record of a historical window. Used for Step 4's May 2024 work.

## Why the storm profile is a real storm rather than a square wave

A flat Kp for three days is not what a storm looks like and would give the wrong answer for a
reason that matters: the displacement grows with the square of the time *remaining*, so when
the excess arrives inside the window is as important as how large it is. The May 2024 sequence
carries a sudden commencement, a main phase of about a day and a recovery of two, and scaling
its Kp to a target peak keeps that shape. Scaling Kp rather than ap is the right axis --
Kp is quasi-logarithmic, and scaling ap would turn a G4 into something with no counterpart in
the record.

## What a scenario returns

:func:`storm_model` wraps whatever covariance model the run would otherwise use --
empirical, plus the supplemental layer, plus SpaceX's ephemeris covariance -- and adds the
storm term for the objects it has a ballistic coefficient for. Everything else falls through
untouched, and the source label says which happened. An object with no coefficient gets no
shift, which is a statement that we do not know, not that there is none; the label carries
that distinction to the output.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.drag import density as dn
from driftwatch.orbit.time import parse_utc
from driftwatch.risk.covariance import CovarianceModel, ObjectRef, RicCovariance, relabel, source_array
from driftwatch.storm import term
from driftwatch.weather import table as weather_table

log = logging.getLogger(__name__)

SYNTHETIC_LEVELS: tuple[str, ...] = tuple(config.STORM_LEVEL_KP)
STATIC_SCENARIOS: tuple[str, ...] = (config.SCENARIO_QUIET, config.SCENARIO_FORECAST)
SCENARIO_NAMES: tuple[str, ...] = (*STATIC_SCENARIOS, *SYNTHETIC_LEVELS, config.SCENARIO_REPLAY_PREFIX)


def is_replay(name: str) -> bool:
    return str(name) == config.SCENARIO_REPLAY_PREFIX or str(name).startswith(f"{config.SCENARIO_REPLAY_PREFIX}:")


def replay_start(name: str) -> datetime | None:
    """The window start a ``replay:<date>`` scenario names, or ``None`` for a bare ``replay``."""
    if ":" not in str(name):
        return None
    return parse_utc(str(name).split(":", 1)[1])


def is_known(name: str) -> bool:
    """Whether ``name`` is one of the scenarios that carries a storm term."""
    return name in STATIC_SCENARIOS or name in SYNTHETIC_LEVELS or is_replay(name)


def validate(name: str) -> str:
    """The scenario name, or a ``ValueError`` for a near miss of a real one.

    A name that is not recognised at all is allowed through as a plain label -- that is what
    ``driftwatch risk --scale 2 --scenario doubled`` is, a rescore of the stored events under
    an operator's own name with no storm layer. What is *not* allowed is a name that looks
    like one of the storm scenarios and is not one, because ``storm-g6`` or ``forcast`` would
    otherwise run quietly and produce quiet numbers under a stormy label, which is the one
    failure here that a reader could not see.
    """
    if is_known(name):
        return name
    lowered = str(name).lower()
    if lowered.startswith(("storm", "replay", "forecast", "forcast", "quiet")):
        allowed = ", ".join([*STATIC_SCENARIOS, *SYNTHETIC_LEVELS, "replay:<YYYY-MM-DD>"])
        raise ValueError(f"unknown scenario {name!r}; expected one of {allowed}")
    return name


# --------------------------------------------------------------------------------------
# The synthetic profile


def storm_template(observed: pd.DataFrame | None, *, start: datetime | None = None, days: float | None = None):
    """The Kp sequence of the May 2024 storm, three-hourly, from the observed record.

    ``observed`` is CelesTrak's SW-All rows, which reach back to 1957, so this needs no
    network and no new feed. Returns the Kp values in order; an empty array when the record
    does not cover those days, which the caller reports rather than silently replacing with a
    square wave.
    """
    if observed is None or not len(observed):
        return np.zeros(0)
    start = start or parse_utc(config.STORM_TEMPLATE_START)
    days = config.STORM_TEMPLATE_DAYS if days is None else days
    t = pd.to_datetime(observed["t"], utc=True)
    window = observed[(t >= pd.Timestamp(start)) & (t < pd.Timestamp(start) + pd.Timedelta(days=days))]
    return pd.to_numeric(window.sort_values("t")["kp"], errors="coerce").to_numpy(dtype=float)


def scaled_profile(template: np.ndarray, target_kp: float) -> np.ndarray:
    """The template scaled so its peak is ``target_kp``, on the Kp axis and clipped to the index's range."""
    if not len(template):
        return template
    peak = float(np.nanmax(template))
    if not np.isfinite(peak) or peak <= 0:
        return template
    return np.clip(template * (target_kp / peak), 0.0, 9.0)


def insert_storm(
    table: pd.DataFrame,
    profile: np.ndarray,
    *,
    start: datetime,
    name: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Write ``profile`` into ``table`` from ``start``, leaving the rest of the table as it was.

    Only the intervals the storm covers become synthetic; the rows before and after keep the
    provenance, skill and issue time they came with, because they are still the observation or
    the forecast they were. A storm that runs off the end of the table is truncated and the
    summary says by how much.
    """
    t = pd.to_datetime(table["t"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[ns]")
    begin = pd.Timestamp(start)
    begin = begin.tz_convert(None) if begin.tzinfo is not None else begin
    first = int(np.searchsorted(t, begin.to_datetime64()))
    room = max(len(table) - first, 0)
    used = profile[:room]
    kp = pd.to_numeric(table["kp"], errors="coerce").to_numpy(dtype=float).copy()
    mask = np.zeros(len(table), dtype=bool)
    if len(used):
        kp[first : first + len(used)] = used
        mask[first : first + len(used)] = True
    out = weather_table.apply_synthetic(table, kp, name=name, mask=mask)
    summary = {
        "storm_start": pd.Timestamp(start).isoformat(),
        "n_intervals": int(mask.sum()),
        "n_truncated": int(len(profile) - len(used)),
        "peak_kp": round(float(np.nanmax(used)), 2) if len(used) else None,
        "peak_ap": round(float(weather_table.kp_to_ap(used).max()), 1) if len(used) else None,
    }
    return out, summary


# --------------------------------------------------------------------------------------
# A scenario


@dataclass(frozen=True)
class Scenario:
    """One named scenario: the weather it runs under, the same weather with ap raised, and why."""

    name: str
    table: pd.DataFrame | None
    perturbed_table: pd.DataFrame | None = None
    description: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def applies_storm_term(self) -> bool:
        return self.table is not None


def raise_ap_by_sigma(table: pd.DataFrame) -> pd.DataFrame:
    """The same table with every interval's ap raised by its own ``ap_sigma``.

    How the index's contribution to the storm term's uncertainty is measured: there is no
    closed form for the density's response to ap, so it is evaluated. ``ap_sigma`` is Step 1's
    column -- small where the index was measured, the unskilled part of the climatological
    spread where it was forecast beyond three days -- and raising rather than perturbing in
    both directions is enough, because what is wanted is a magnitude and the response is
    monotonic in ap.
    """
    out = table.copy()
    ap = pd.to_numeric(out["ap"], errors="coerce").to_numpy(dtype=float)
    sigma = pd.to_numeric(out["ap_sigma"], errors="coerce").to_numpy(dtype=float)
    raised = ap + np.nan_to_num(sigma, nan=0.0)
    out["ap"] = raised
    out["kp"] = weather_table.ap_to_kp(raised)
    out["ap_daily"] = out.groupby(out["t"].dt.floor("D"))["ap"].transform("mean")
    return out


def build_scenario(
    name: str,
    *,
    start: datetime,
    end: datetime,
    sources: weather_table.WeatherSources,
    now: datetime | None = None,
    offset_days: float | None = None,
    earliest_epoch: datetime | None = None,
) -> Scenario:
    """The weather a named scenario runs under, and the provenance of it.

    ``start`` and ``end`` are the screening window. ``earliest_epoch`` is the oldest element-set
    epoch the storm term will integrate from, which is what the table actually has to reach back
    to: the shift is measured from each object's *own* epoch, and a run screening on element sets
    up to five days stale needs those five days plus NRLMSIS's own 57 hours of history behind
    them. Without it the oldest objects' tracks come back part NaN and their shifts are silently
    understated -- which is how this was found.

    The quiet scenario carries no table at all, which is what makes it the Phase 2 model
    untouched.
    """
    validate(name)
    now = now or datetime.now(UTC)
    if name == config.SCENARIO_QUIET:
        return Scenario(
            name,
            None,
            description=(
                "the Phase 2 covariance untouched: no storm layer, no mean shift, the regression "
                "baseline every other scenario is read against"
            ),
        )
    if not is_known(name):
        return Scenario(name, None, description=f"a labelled rescore under the operator's own name {name!r}")

    window_start, window_end = start, end
    if is_replay(name):
        replay = replay_start(name)
        if replay is not None:
            window_start = replay
            window_end = replay + (end - start)
    reach_back = window_start
    if earliest_epoch is not None and earliest_epoch < reach_back:
        reach_back = earliest_epoch
    table_start, table_end = dn.weather_window(reach_back, window_end)
    table = weather_table.weather_table(table_start, table_end, sources, now=now)
    summary = weather_table.table_summary(table)
    provenance: dict[str, Any] = {
        "window": [window_start.isoformat(), window_end.isoformat()],
        "table": [table_start.isoformat(), table_end.isoformat()],
        "by_provenance": summary["by_provenance"],
        "by_skill": summary["by_skill"],
        "forecast_issued": summary["forecast_issued"],
        "n_missing": summary["n_missing"],
    }

    if name in SYNTHETIC_LEVELS:
        template = storm_template(sources.celestrak)
        if not len(template):
            raise ValueError(
                f"{name} needs the May 2024 record to build its profile from and the CelesTrak "
                "space weather file does not cover it; fetch it with `driftwatch weather`"
            )
        profile = scaled_profile(template, config.STORM_LEVEL_KP[name])
        offset = config.STORM_OFFSET_DAYS if offset_days is None else offset_days
        table, storm = insert_storm(
            table, profile, start=window_start + timedelta(days=offset), name=name.replace("storm-", "")
        )
        provenance["storm"] = {
            **storm,
            "template": f"{config.STORM_TEMPLATE_START} + {config.STORM_TEMPLATE_DAYS:g} d",
            "template_peak_kp": round(float(np.nanmax(template)), 2),
            "offset_days": offset,
        }
        description = (
            f"the May 2024 sequence scaled to Kp {config.STORM_LEVEL_KP[name]:g}, starting "
            f"{offset:g} days into the window"
        )
    elif is_replay(name):
        description = f"the observed record for {window_start.date()} to {window_end.date()}"
    else:
        description = "SWPC's three-day Kp forecast, the 27-day outlook beyond it, observed where the record reaches"

    return Scenario(name, table, raise_ap_by_sigma(table), description, provenance)


# --------------------------------------------------------------------------------------
# The covariance model a scenario hands to `risk`


#: Why an object's storm mean shift is zeroed, most specific first. The first two are about the
#: **trajectory**: the excess density is measured against SGP4's own atmosphere through the
#: element set's B*, and a trajectory that was never SGP4's -- the operator's published states,
#: or CelesTrak's fit to them -- carries the operator's drag model and planned burns, so there is
#: no excess to measure and nothing is added at all. The last two are about the **object**: a
#: station-kept or observed-manoeuvring satellite on a tracking-derived element set will burn
#: rather than drift, so the direction of its displacement is the operator's and the mean is
#: undefined, while the size of the storm's push is still a legitimate uncertainty and stays in
#: the in-track variance.
CONTROL_SERVED = "served"
CONTROL_OPERATOR_EPHEMERIS = "operator-ephemeris"
CONTROL_KNOWN = "known"
CONTROL_OBSERVED = "observed"
CONTROLLED_PREFIX = term.CONTROLLED_PREFIX
#: The covariance label the SpaceX layer writes where the event's geometry came from the
#: published states themselves (`ephemeris/spacex.py`); the trajectory is the operator's there.
SERVED_TRAJECTORY_LABEL = "spacex-ephemeris"


def controlled_objects(objects: pd.DataFrame) -> dict[int, str]:
    """NORAD id to the reason its storm mean shift is undefined, for every object it is.

    From the run's objects table: ``ephemeris == "supplemental"`` means the element set is
    CelesTrak's SGP4 fit to the operator's own ephemeris (:data:`CONTROL_OPERATOR_EPHEMERIS`);
    otherwise a ``manoeuvre_level`` of ``known`` or ``observed`` (`risk/manoeuvre.py`). Objects
    served from the published states at an event are recognised per time by
    :class:`StormCovariance` from the covariance label, since that is per event rather than per
    object. Everything else is free-flying and absent from the result.
    """
    out: dict[int, str] = {}
    if not len(objects):
        return out
    ephemeris = (
        objects["ephemeris"].astype(str) if "ephemeris" in objects.columns else pd.Series("gp", index=objects.index)
    )
    levels = objects["manoeuvre_level"].astype(str) if "manoeuvre_level" in objects.columns else None
    for position, norad_id in enumerate(objects["norad_id"].to_numpy()):
        if ephemeris.iloc[position] == "supplemental":
            out[int(norad_id)] = CONTROL_OPERATOR_EPHEMERIS
        elif levels is not None and levels.iloc[position] in (CONTROL_KNOWN, CONTROL_OBSERVED):
            out[int(norad_id)] = str(levels.iloc[position])
    return out


def skips_storm_term(reason: str) -> bool:
    """Whether a control reason drops the storm term entirely (mean **and** variance).

    True for the trajectory reasons: the excess over SGP4's atmosphere is undefined against a
    trajectory that never used it, so a variance derived from that excess is as undefined as
    the mean. False for the object reasons, where the excess is defined and only the response
    is the operator's.
    """
    return reason in (CONTROL_SERVED, CONTROL_OPERATOR_EPHEMERIS)


class StormCovariance:
    """A base model with an in-track mean shift and an in-track variance from the storm term.

    Everything the base model says is kept; the storm layer adds. The variance goes into the
    in-track element of the covariance, which is where an along-track displacement's
    uncertainty belongs, and the shift is returned beside it on the protocol's new field for
    :func:`driftwatch.risk.scenario.run_risk` to apply to the miss vector.

    **Operator-controlled objects get no mean shift** (corrected 2026-09-05). ``controlled``
    maps NORAD id to the reason (:func:`controlled_objects`); a served trajectory is recognised
    per time from the base label. For a trajectory reason nothing is added at all; for an object
    reason the in-track variance is kept and the mean is zero. The source label says which:
    ``...+storm:operator-controlled/<reason>``. Before this correction every object with a
    coefficient was displaced, which put a 30,000 km shift on Starlinks whose B* describes a
    thrusting plan rather than drag, and reported their events as outside the linear theory --
    the same category error seen from the other side. ``docs/storm-term.md``.
    """

    def __init__(
        self,
        base: CovarianceModel,
        shifts: Mapping[int, term.ShiftSeries],
        *,
        scenario: str,
        controlled: Mapping[int, str] | None = None,
    ) -> None:
        self.base = base
        self.shifts = dict(shifts)
        self.controlled: dict[int, str] = {int(k): str(v) for k, v in (controlled or {}).items()}
        self.scenario = str(scenario)
        # /2: operator-controlled objects carry no mean shift (2026-09-05). /1 displaced them.
        self.version = f"{base.version}+storm/{self.scenario}/2"

    def growth_for(self, obj: ObjectRef) -> tuple[Any, str]:
        return self.base.growth_for(obj)  # type: ignore[attr-defined]

    def applies_shift_to(self, norad_id: int) -> bool:
        """Whether this scenario moves the object at all; false for every operator-controlled one."""
        return int(norad_id) not in self.controlled

    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        inner = self.base.covariance_ric(obj, epoch, at)
        n = len(np.asarray(at))
        labels = source_array(inner.source, n)
        served = np.array([str(s) == SERVED_TRAJECTORY_LABEL for s in labels], dtype=bool)
        reason = self.controlled.get(int(obj.norad_id))
        series = self.shifts.get(int(obj.norad_id))
        has_series = series is not None and len(series.seconds) > 0
        if reason is None and not served.any():
            if not has_series:
                return RicCovariance(inner.cov_km2, relabel(inner.source, "{}+storm:none"), inner.mean_shift_ric_km)
            shift_m, sigma_m = series.at(term.times_since_epoch_s(epoch, at))
            cov = np.array(inner.cov_km2, dtype=float, copy=True)
            cov[:, 1, 1] += (sigma_m / 1000.0) ** 2
            mean = np.zeros((len(cov), 3))
            mean[:, 1] = shift_m / 1000.0
            if inner.mean_shift_ric_km is not None:
                mean = mean + np.asarray(inner.mean_shift_ric_km, dtype=float)
            label = series.b_source if series.valid else f"{series.b_source}!extrapolated"
            return RicCovariance(cov, relabel(inner.source, "{}+storm:" + label), mean)

        # Operator-controlled, for at least some of the times asked about. The mean is zero at
        # every one of them; the variance is kept only where the trajectory is SGP4's and the
        # object's reason is about its behaviour rather than about the trajectory.
        cov = np.array(inner.cov_km2, dtype=float, copy=True)
        per_time = np.empty(n, dtype=object)
        keep_variance = np.zeros(n, dtype=bool)
        for k in range(n):
            why = CONTROL_SERVED if served[k] else (reason or CONTROL_SERVED)
            per_time[k] = f"{CONTROLLED_PREFIX}/{why}"
            keep_variance[k] = not skips_storm_term(why)
        if has_series and keep_variance.any():
            _, sigma_m = series.at(term.times_since_epoch_s(epoch, at))
            cov[keep_variance, 1, 1] += (sigma_m[keep_variance] / 1000.0) ** 2
        mean = np.zeros((n, 3))
        if inner.mean_shift_ric_km is not None:
            mean = mean + np.asarray(inner.mean_shift_ric_km, dtype=float)
        source = np.array([f"{s}+storm:{why}" for s, why in zip(labels, per_time, strict=True)], dtype=object)
        return RicCovariance(cov, source, mean)

    def to_frame(self) -> pd.DataFrame:
        return self.base.to_frame() if hasattr(self.base, "to_frame") else pd.DataFrame()


class WeatherTableTooShort(ValueError):
    """The scenario's weather does not reach back to the oldest element set it has to integrate from."""


def check_table_reaches(table: pd.DataFrame, earliest_epoch: datetime, *, scenario: str = "") -> None:
    """Fail loudly when the weather table starts after the oldest element-set epoch needs it to.

    Every shift is integrated from its **own object's** epoch, and NRLMSIS wants
    :data:`driftwatch.drag.density.WEATHER_LEAD` of ap history behind the first sample. A table
    built over the screening window alone is short by however stale the oldest element set is,
    and the failure it produces is the quiet kind: the early part of those objects' density
    tracks comes back NaN, :func:`~driftwatch.storm.term.object_shift` zeroes the unusable
    samples, and the shift is *understated* with nothing on the row to say so.

    That is exactly how the reach-back was found during the first real run, and the reason this
    is an exception rather than a warning: a silently small storm term on the stalest element
    sets in the run is the one error here that looks like a result.
    """
    if table is None or not len(table):
        raise WeatherTableTooShort(f"scenario {scenario!r} has no weather table at all")
    first = pd.to_datetime(table["t"], utc=True).min()
    needed = pd.Timestamp(earliest_epoch)
    needed = needed.tz_localize("UTC") if needed.tzinfo is None else needed.tz_convert("UTC")
    needed = needed - dn.WEATHER_LEAD
    if first > needed:
        short_days = (first - needed).total_seconds() / 86400.0
        raise WeatherTableTooShort(
            f"the weather table for scenario {scenario!r} starts at {first.isoformat()}, which is "
            f"{short_days:.2f} days after the {needed.isoformat()} the oldest element-set epoch "
            f"({pd.Timestamp(earliest_epoch).isoformat()}) needs once NRLMSIS's "
            f"{dn.WEATHER_LEAD.total_seconds() / 3600:.0f} hours of ap history are allowed for; "
            "those objects' shifts would be silently understated. Pass `earliest_epoch` to "
            "`build_scenario`, or fetch more weather with `driftwatch weather`"
        )


def shifts_for_objects(
    scenario: Scenario,
    elements: pd.DataFrame,
    coefficients: pd.DataFrame,
    *,
    end: datetime,
    step_s: float | None = None,
    norad_ids: set[int] | None = None,
    skip: set[int] | None = None,
) -> dict[int, term.ShiftSeries]:
    """The storm term for every object of a run, keyed by NORAD id.

    One density track per object from its own element-set epoch to ``end``, not one per event:
    the shift is a function of time, and the events read it at their own times of closest
    approach.

    ``skip`` names the objects whose storm term is dropped entirely -- those on an operator's
    trajectory, for which the excess is undefined (:func:`skips_storm_term`) -- so no density
    track is computed for them. On the demo fleet that is six Starlinks in ten, and the density
    tracks are what the scenario step's runtime is made of.
    """
    if scenario.table is None:
        return {}
    if len(elements):
        check_table_reaches(scenario.table, pd.to_datetime(elements["epoch"], utc=True).min(), scenario=scenario.name)
    by_id = coefficients.set_index("norad_id") if len(coefficients) else pd.DataFrame()
    grid = dn.weather_grid(scenario.table)
    perturbed = dn.weather_grid(scenario.perturbed_table) if scenario.perturbed_table is not None else None
    out: dict[int, term.ShiftSeries] = {}
    n_without = 0
    skipped = {int(i) for i in (skip or ())}
    started = time.perf_counter()
    wanted = elements["norad_id"].astype(int) if norad_ids is None else elements["norad_id"].astype(int).isin(norad_ids)
    total = int(len(elements) if norad_ids is None else wanted.sum())
    n_skipped = int(elements["norad_id"].astype(int).isin(skipped).sum())
    log.info(
        "Storm term for %s: %d objects, two density tracks each; %d on an operator's trajectory get no term "
        "and no track",
        scenario.name,
        total - n_skipped,
        n_skipped,
    )
    for position, (_, row) in enumerate(elements.iterrows()):
        norad_id = int(row["norad_id"])
        if norad_ids is not None and norad_id not in norad_ids:
            continue
        if norad_id in skipped:
            continue
        coefficient = by_id.loc[norad_id] if norad_id in by_id.index else None
        if coefficient is None:
            n_without += 1
        out[norad_id] = term.object_shift(row, coefficient, grid, end, perturbed_table=perturbed, step_s=step_s)
        if position % 250 == 249:
            elapsed = time.perf_counter() - started
            log.info(
                "  %d/%d objects, %.0f s elapsed, about %.0f s left",
                position + 1,
                total,
                elapsed,
                elapsed * (total - position - 1) / max(position + 1, 1),
            )
    if n_without:
        log.warning(
            "%d of %d objects have no ballistic coefficient, so the scenario moves them not at all; "
            "run `driftwatch ballistic` first if that is not what you want",
            n_without,
            len(out),
        )
    return out
