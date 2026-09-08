"""ESA's dSGP4 and its ML-dSGP4 hybrid on the benchmark's trials.

dsgp4 (Acciarini, Baydin and Izzo, "Closing the gap between SGP4 and high-precision propagation via
differentiable programming", Acta Astronautica 226, 2025, 694-701; github.com/esa/dSGP4) is SGP4
written in PyTorch, so that a propagation is differentiable and can be run in batches. Its hybrid,
ML-dSGP4, wraps the propagator in two small networks: one perturbs the six mean elements before
the propagation, the other perturbs the propagated state after it, each by a bounded (tanh)
fraction, and the two are trained against a higher-precision reference. The published experiment
used SpaceX numerical predictions for 1,519 Starlink satellites over three days, 18-21 February
2023. The paper does not classify this period as quiet. The experiment here is a local adaptation:
40 epochs, initial learning rate 0.001 and selection by the fixed training objective, evaluated
on the stated benchmark windows. See https://arxiv.org/html/2402.04830v5#S4.SS2.

What is done here. The trial sets of the two tuning-visible windows, the quiet week and the May
2024 storm, are the training set; the hybrid never sees a set, or a truth state, from October or
August 2024. For every training set the reconstructed orbit is sampled every hour from the set's
epoch to seven days, which gives (set, time since epoch, true state) triples; the networks are
trained by Adam on the mean squared error of the position and velocity in the library's normalised
units. The corrections start at zero, so the untrained hybrid is exactly SGP4: the library's random
initialisation starts hundreds of kilometres away and the first epochs would be spent finding SGP4
again. Two hybrids are trained, one on Swarm alone (the population the benchmark began with) and
one on every mission with a reconstructed orbit. Every trial set of every window is then scored at
the benchmark's leads, in the truth's radial, in-track, cross-track frame, by: the sgp4 library
(plain SGP4, WGS72, the benchmark's own numbers); dsgp4 as a baseline with WGS72 constants, which
must agree with the library to metres; dsgp4 with its default WGS-84 constants, which the hybrid
uses inside; the two hybrids; and the project's storm term with the observed ap, read from the
trials. The stored recommendation rule is retained for these two checkpoints. All four windows
have already been inspected; a rerun does not make October or August a new hold-out,
and this rule is not an adoption protocol for a new recipe.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch.orbit.propagator import build_satrecs
from driftwatch.orbit.time import julian_dates
from driftwatch.screening.ric import ric_basis, to_ric
from driftwatch.storm import precise
from driftwatch.storm.precise import PreciseOrbit

log = logging.getLogger(__name__)

TRAINING_WINDOWS = ("quiet", "storm")
HELD_OUT_WINDOWS = ("held-out", "august")
SAMPLE_STEP_MIN = 60.0
HORIZON_MIN = float(max(precise.LEADS_HOURS)) * 60.0
CITATION = (
    "Acciarini, G., Baydin, A. G., Izzo, D. (2025), Closing the gap between SGP4 and high-precision propagation via "
    "differentiable programming, Acta Astronautica 226, 694-701; software github.com/esa/dSGP4"
)
PUBLISHED_TRAINING = (
    "The published experiment used SpaceX numerical predictions for 1,519 Starlink satellites over three days, "
    "18-21 February 2023, at 60-second cadence. The paper does not classify this period as quiet. It used "
    "30 epochs, learning rate 0.003, a TLE-level training/validation/test split and validation-selected models. "
    "This experiment is a local adaptation: 40 epochs, initial learning rate 0.001, a cosine schedule, "
    "zero initial corrections and selection by the complete fixed training objective on the stated "
    "reference-orbit benchmark. Source: https://arxiv.org/html/2402.04830v5#S4.SS2."
)


def _torch():
    import torch

    return torch


def omm_from_row(row: pd.Series | dict[str, Any]):
    """A dsgp4 OMM object from one element-set row of the history store (degrees, revolutions per day)."""
    from dsgp4.omm import OMM

    epoch = pd.Timestamp(row["epoch"])
    epoch = epoch.tz_convert(None) if epoch.tzinfo else epoch

    def get(key: str, default: Any = None) -> Any:
        value = row.get(key, default) if hasattr(row, "get") else default
        return default if value is None or (isinstance(value, float) and np.isnan(value)) else value

    fields = {
        "OBJECT_NAME": str(get("name", "") or "UNKNOWN"),
        "OBJECT_ID": str(get("object_id", "") or "UNKNOWN"),
        "EPOCH": epoch.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "MEAN_MOTION": float(row["mean_motion"]),
        "ECCENTRICITY": float(row["eccentricity"]),
        "INCLINATION": float(row["inclination_deg"]),
        "RA_OF_ASC_NODE": float(row["raan_deg"]),
        "ARG_OF_PERICENTER": float(row["arg_perigee_deg"]),
        "MEAN_ANOMALY": float(row["mean_anomaly_deg"]),
        "EPHEMERIS_TYPE": 0,
        "CLASSIFICATION_TYPE": "U",
        "NORAD_CAT_ID": int(row["norad_id"]),
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 0,
        "BSTAR": float(get("bstar", 0.0) or 0.0),
        "MEAN_MOTION_DOT": float(get("mean_motion_dot", 0.0) or 0.0),
        "MEAN_MOTION_DDOT": float(get("mean_motion_ddot", 0.0) or 0.0),
    }
    return OMM(fields)


# --------------------------------------------------------------------------------------
# Samples: sets, times since epoch, true states


@dataclass
class TrialSet:
    """One element set with its truth orbit: the OMM object, the epoch, the mission and window it belongs to."""

    mission: str
    window: str
    epoch: pd.Timestamp
    omm: Any
    orbit: PreciseOrbit
    sgp4_record: Any
    element_sha256: str


def trial_sets(trials: pd.DataFrame, sets: pd.DataFrame, orbits: dict[tuple[str, str], PreciseOrbit]) -> list[TrialSet]:
    """The distinct (mission, window, set) triples of the benchmark's usable trials, with their OMM and truth orbit."""
    usable = trials[~trials["gap"] & ~trials["manoeuvre"] & (trials["sgp4_error"] == 0)]
    keys = usable[["mission", "window", "norad_id", "set_epoch"]].drop_duplicates()
    by_epoch: dict[tuple[int, pd.Timestamp], pd.Series] = {}
    epochs = pd.to_datetime(sets["epoch"], utc=True).dt.tz_convert(None)
    for (nid, ep), row in zip(
        zip(sets["norad_id"].astype(int), epochs, strict=True), sets.to_dict("records"), strict=True
    ):
        by_epoch[(int(nid), pd.Timestamp(ep))] = pd.Series(row)
    out: list[TrialSet] = []
    for r in keys.itertuples(index=False):
        orbit = orbits.get((r.mission, r.window))
        if orbit is None:
            continue
        epoch = pd.Timestamp(r.set_epoch)
        epoch = epoch.tz_convert(None) if epoch.tzinfo else epoch
        row = by_epoch.get((int(r.norad_id), epoch))
        if row is None:
            continue
        element_sha = hashlib.sha256(json.dumps(row.to_dict(), sort_keys=True, default=str).encode()).hexdigest()
        out.append(
            TrialSet(
                str(r.mission),
                str(r.window),
                epoch,
                omm_from_row(row),
                orbit,
                build_satrecs(pd.DataFrame([row]))[0],
                element_sha,
            )
        )
    return out


def truth_at(
    orbit: PreciseOrbit, epoch: pd.Timestamp, tsince_min: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    at = (
        np.datetime64(epoch.to_datetime64(), "us")
        + (np.asarray(tsince_min, dtype=float) * 60e6).astype("timedelta64[us]")
    ).astype("datetime64[us]")
    return orbit.states_teme(at)


@dataclass(frozen=True)
class TrainingExclusions:
    """The evaluation's authoritative intervals, including an explicitly empty record."""

    source: str
    intervals: tuple[tuple[pd.Timestamp, pd.Timestamp], ...]
    arc_hours: float = precise.MANOEUVRE_ARC_HOURS


def training_exclusions_from_benchmark(
    trials: pd.DataFrame, coverage: Mapping[str, Any]
) -> dict[tuple[str, str], TrainingExclusions]:
    """Resolve and cross-check exclusions on training windows only.

    Missing record metadata is an error, never an empty burn list. Published
    records take precedence; detection uses both orbit and element-set intervals,
    exactly as ``precise.satellite_trials`` does. Held-out results play no role.
    """
    out = {}
    training = trials[trials["window"].isin(TRAINING_WINDOWS)]
    for (mission, window), group in training.groupby(["mission", "window"], sort=True):
        sources = group["manoeuvre_source"].dropna().unique()
        if len(sources) != 1 or group["manoeuvre_source"].isna().any():
            raise ValueError(f"Ambiguous manoeuvre source for {mission}/{window}")
        source = str(sources[0])
        entry = coverage.get(str(mission), {}).get(str(window))
        if entry is None:
            raise ValueError(f"Missing exclusion metadata for {mission}/{window}")
        if source in (
            "esa-record",
            "thr1b-record",
            "operator-record",
            "ids-ssalto-record",
            "sentiwiki-sentinel3-record",
        ):
            provenance = entry.get("manoeuvre_record_provenance")
            if source in ("ids-ssalto-record", "sentiwiki-sentinel3-record") and provenance is None:
                raise ValueError(f"Missing authoritative record provenance for {mission}/{window}")
            if provenance is not None and (
                provenance.get("days_missing")
                or provenance.get("authoritative") is False
                or provenance.get("coverage_status")
                not in ("published_event_registry", "published_history", "daily-products-complete")
            ):
                raise ValueError(f"Incomplete authoritative record for {mission}/{window}")
            raw = entry.get("manoeuvres_recorded")
            if raw is None:
                raise ValueError(f"Missing authoritative manoeuvre record for {mission}/{window}")
        elif source == "detected":
            if any(entry.get(k) is None for k in ("manoeuvres_detected_orbit", "manoeuvres_detected_sets")):
                raise ValueError(f"Missing detection intervals for {mission}/{window}")
            raw = entry["manoeuvres_detected_orbit"] + entry["manoeuvres_detected_sets"]
        else:
            raise ValueError(f"Unknown manoeuvre source: {source}")
        intervals = tuple((precise._naive(a), precise._naive(b)) for a, b in raw)
        if any(a > b for a, b in intervals):
            raise ValueError(f"Reversed manoeuvre interval for {mission}/{window}")
        policy = TrainingExclusions(source, intervals)
        for row in group.itertuples(index=False):
            epoch = precise._naive(row.set_epoch)
            excluded = precise._overlaps(
                list(intervals), epoch - pd.Timedelta(hours=policy.arc_hours), epoch + pd.Timedelta(hours=row.lead_h)
            )
            if pd.isna(row.manoeuvre) or excluded != bool(row.manoeuvre):
                raise ValueError(f"Training/evaluation exclusion mismatch for {mission}/{window}/{epoch}")
        out[(str(mission), str(window))] = policy
    return out


@dataclass
class TrainingSamples:
    omms: list[Any]
    tsince_min: np.ndarray
    states: np.ndarray
    manifest: pd.DataFrame
    sha256: str


def prepare_training_samples(
    items: Iterable[TrialSet],
    *,
    exclusions: Mapping[tuple[str, str], TrainingExclusions],
    step_min: float = SAMPLE_STEP_MIN,
    horizon_min: float = HORIZON_MIN,
) -> TrainingSamples:
    """Sample only eligible hourly targets, retaining an audit row for every target.

    Eligibility requires reconstructed truth coverage, finite truth and SGP4
    states, zero WGS72 SGP4 error, and no authoritative burn between epoch minus
    24 hours and the target. Non-training windows fail before truth is accessed.
    """
    items = list(items)
    if any(item.window not in TRAINING_WINDOWS for item in items):
        raise ValueError("Training samples may use quiet and storm windows only")
    if not np.isfinite(step_min) or not np.isfinite(horizon_min) or step_min <= 0 or horizon_min < step_min:
        raise ValueError("Training grid must have a finite positive step and horizon >= step")
    for item in items:
        if (item.mission, item.window) not in exclusions:
            raise ValueError(f"No training exclusion policy for {item.mission}/{item.window}")
    omms: list[Any] = []
    tsince: list[float] = []
    states: list[np.ndarray] = []
    audit = []
    grid = np.arange(step_min, horizon_min + 1e-9, step_min)
    for item in items:
        policy = exclusions[(item.mission, item.window)]
        if policy.arc_hours != precise.MANOEUVRE_ARC_HOURS:
            raise ValueError("Training and benchmark pre-epoch exclusion arcs must match")
        r, v, ok = truth_at(item.orbit, item.epoch, grid)
        at = (item.epoch + pd.to_timedelta(grid, unit="min")).to_numpy(dtype="datetime64[us]")
        jd, fraction = julian_dates(at)
        errors, predicted_r, predicted_v = item.sgp4_record.sgp4_array(jd, fraction)
        finite = np.isfinite(r).all(axis=1) & np.isfinite(v).all(axis=1)
        finite &= np.isfinite(predicted_r).all(axis=1) & np.isfinite(predicted_v).all(axis=1)
        for k, lead in enumerate(grid):
            burn = precise._overlaps(
                list(policy.intervals), item.epoch - pd.Timedelta(hours=policy.arc_hours), pd.Timestamp(at[k])
            )
            usable = bool(ok[k] and finite[k] and errors[k] == 0 and not burn)
            audit.append(
                {
                    "mission": item.mission,
                    "window": item.window,
                    "set_epoch": item.epoch.isoformat(),
                    "lead_min": float(lead),
                    "truth_covered": bool(ok[k]),
                    "finite_states": bool(finite[k]),
                    "sgp4_error": int(errors[k]),
                    "manoeuvre": burn,
                    "manoeuvre_source": policy.source,
                    "usable": usable,
                    "element_sha256": item.element_sha256,
                }
            )
            if usable:
                omms.append(item.omm)
                tsince.append(float(lead))
                states.append(np.concatenate([r[k], v[k]]))
    times = np.asarray(tsince, dtype=float)
    targets = np.asarray(states, dtype=float).reshape(-1, 6)
    manifest = pd.DataFrame(audit)
    digest = hashlib.sha256(manifest.to_csv(index=False, lineterminator="\n").encode())
    digest.update(times.astype("<f8").tobytes())
    digest.update(targets.astype("<f8").tobytes())
    return TrainingSamples(omms, times, targets, manifest, digest.hexdigest())


def training_samples(
    items: Iterable[TrialSet],
    *,
    exclusions: Mapping[tuple[str, str], TrainingExclusions],
    step_min: float = SAMPLE_STEP_MIN,
    horizon_min: float = HORIZON_MIN,
) -> tuple[list[Any], np.ndarray, np.ndarray]:
    """Compatibility tuple interface; the explicit exclusion policy is mandatory."""
    samples = prepare_training_samples(items, exclusions=exclusions, step_min=step_min, horizon_min=horizon_min)
    return samples.omms, samples.tsince_min, samples.states


# --------------------------------------------------------------------------------------
# The models


def new_hybrid(hidden_size: int = 35, *, zero_start: bool = True, seed: int = 0):
    """An ML-dSGP4 model; with ``zero_start`` its two corrections begin at zero, so it starts as SGP4."""
    import dsgp4

    torch = _torch()
    torch.manual_seed(seed)
    model = dsgp4.mldsgp4(hidden_size=hidden_size).to(dtype=torch.float64)
    if zero_start:
        with torch.no_grad():
            model.fc3.weight.zero_()
            model.fc3.bias.zero_()
            model.fc6.weight.zero_()
            model.fc6.bias.zero_()
    return model


def hybrid_states(model, omms: list[Any], tsince_min: np.ndarray, *, batch_size: int = 4096) -> np.ndarray:
    """Positions and velocities, km and km/s in TEME, from a hybrid for a list of sets and times."""
    torch = _torch()
    out = []
    model.eval()
    with torch.no_grad():
        for k in range(0, len(omms), batch_size):
            batch = omms[k : k + batch_size]
            ts = torch.tensor(tsince_min[k : k + batch_size], dtype=torch.float64)
            x = model(batch, ts) if len(batch) > 1 else model(batch[0], ts)
            r = x[:, :3] * model.normalization_R
            v = x[:, 3:] * model.normalization_V
            out.append(torch.cat([r, v], dim=1).numpy())
    return np.concatenate(out, axis=0) if out else np.zeros((0, 6))


def dsgp4_states(
    omms: list[Any], tsince_min: np.ndarray, *, gravity: str = "wgs-72", batch_size: int = 4096
) -> np.ndarray:
    """dsgp4 itself, no correction, with the named gravity constants."""
    import dsgp4

    torch = _torch()
    out = []
    for k in range(0, len(omms), batch_size):
        batch = omms[k : k + batch_size]
        ts = torch.tensor(tsince_min[k : k + batch_size], dtype=torch.float64)
        _, tles = dsgp4.initialize_tle(list(batch), gravity_constant_name=gravity)
        with torch.no_grad():
            states = dsgp4.propagate_batch(tles, ts)
        out.append(states.reshape(-1, 6).numpy())
    return np.concatenate(out, axis=0) if out else np.zeros((0, 6))


@dataclass
class TrainingRecord:
    n_samples: int
    n_sets: int
    epochs: int
    batch_size: int
    learning_rate: float
    losses: list[float]
    seconds: float
    initial_loss: float = float("nan")  # the loss at the zero start, before any step
    kept_zero_start: bool = False  # true when no epoch beat the zero start and it was restored
    online_losses: list[float] = field(default_factory=list)
    selected_epoch: int = 0
    selected_loss: float | None = None
    seed: int = 0
    sample_sha256: str | None = None
    checkpoint_path: str | None = None
    checkpoint_sha256: str | None = None
    checkpoint_reloaded_loss: float | None = None


def fixed_objective(model, omms: list[Any], tsince_min: np.ndarray, states: np.ndarray, *, batch_size: int = 4096):
    """Evaluate one fixed model on every supplied sample, weighted by sample count."""
    torch = _torch()
    if not omms or batch_size < 1 or len(omms) != len(tsince_min) or states.shape != (len(omms), 6):
        raise ValueError("Objective requires a nonempty aligned sample and positive batch size")
    target = np.concatenate([states[:, :3] / model.normalization_R, states[:, 3:] / model.normalization_V], axis=1)
    if not np.isfinite(target).all() or not np.isfinite(tsince_min).all():
        raise ValueError("Training sample must contain finite states and times")
    previous_mode = model.training
    model.eval()
    total = 0.0
    with torch.no_grad():
        for k in range(0, len(omms), batch_size):
            batch = omms[k : k + batch_size]
            times = torch.tensor(tsince_min[k : k + batch_size], dtype=torch.float64)
            truth = torch.tensor(target[k : k + batch_size], dtype=torch.float64)
            x = model(batch, times) if len(batch) > 1 else model(batch[0], times)
            total += float(torch.mean((x - truth) ** 2)) * len(batch)
    model.train(previous_mode)
    value = total / len(omms)
    if not np.isfinite(value):
        raise ValueError("Model objective is nonfinite")
    return value


def train_hybrid(
    model,
    omms: list[Any],
    tsince_min: np.ndarray,
    states: np.ndarray,
    *,
    epochs: int = 30,
    batch_size: int = 4096,
    learning_rate: float = 1e-3,
    seed: int = 0,
    sample_sha256: str | None = None,
    checkpoint_path: Path | None = None,
) -> TrainingRecord:
    """Adam with fixed-sample end-of-epoch selection and verified checkpoint persistence.

    ``losses`` contains full fixed-model objectives after each epoch; the old
    changing-model minibatch averages survive separately as ``online_losses``.
    The initial checkpoint remains a candidate. No validation/held-out input is
    accepted by this function.
    """
    torch = _torch()
    if epochs < 0 or batch_size < 1 or not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("Invalid training epochs, batch size or learning rate")
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    n = len(omms)
    initial = fixed_objective(model, omms, tsince_min, states, batch_size=batch_size)
    target = np.concatenate([states[:, :3] / model.normalization_R, states[:, 3:] / model.normalization_V], axis=1)
    target_t = torch.tensor(target, dtype=torch.float64)
    ts_all = torch.tensor(tsince_min, dtype=torch.float64)
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    # The corrections start at zero and the needed ones are small, so the rate falls through the run
    # (cosine, to a hundredth of its start) and the epoch with the lowest training loss is kept; the
    # held-out windows play no part in either.
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimiser, T_max=max(epochs, 1), eta_min=learning_rate / 100)
    losses: list[float] = []
    online_losses: list[float] = []
    # The zero start is itself a candidate: it is scored first and restored if nothing beats it.
    best = (initial, {k: v.detach().clone() for k, v in model.state_dict().items()})
    selected_epoch = 0
    t0 = time.time()
    model.train()
    for epoch in range(epochs):
        order = rng.permutation(n)
        total = 0.0
        for k in range(0, n, batch_size):
            idx = order[k : k + batch_size]
            batch = [omms[i] for i in idx]
            x = model(batch, ts_all[idx]) if len(batch) > 1 else model(batch[0], ts_all[idx])
            loss = torch.mean((x - target_t[idx]) ** 2)
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            total += loss.item() * len(idx)
        online_losses.append(total / n)
        losses.append(fixed_objective(model, omms, tsince_min, states, batch_size=batch_size))
        scheduler.step()
        if losses[-1] < best[0]:
            best = (losses[-1], {k: v.detach().clone() for k, v in model.state_dict().items()})
            selected_epoch = epoch + 1
        log.info("ML-dSGP4 epoch %d/%d: loss %.3e (%.0f s)", epoch + 1, epochs, losses[-1], time.time() - t0)
    kept_zero = selected_epoch == 0
    if best[1] is not None:
        model.load_state_dict(best[1])
    model.eval()
    n_sets = len({id(o) for o in omms})
    selected_loss = fixed_objective(model, omms, tsince_min, states, batch_size=batch_size)
    record = TrainingRecord(
        n,
        n_sets,
        epochs,
        batch_size,
        learning_rate,
        losses,
        time.time() - t0,
        initial,
        kept_zero,
        online_losses=online_losses,
        selected_epoch=selected_epoch,
        selected_loss=selected_loss,
        seed=seed,
        sample_sha256=sample_sha256,
    )
    if checkpoint_path is not None:
        checkpoint_path = Path(checkpoint_path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": model.state_dict(),
                "normalization_R": model.normalization_R,
                "normalization_V": model.normalization_V,
                "training_record": asdict(record),
            },
            checkpoint_path,
        )
        record.checkpoint_path = str(checkpoint_path.resolve())
        record.checkpoint_sha256 = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
        # Reload the persisted bytes, then recompute the objective on the same fixed sample.
        saved = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model.load_state_dict(saved["state_dict"])
        record.checkpoint_reloaded_loss = fixed_objective(model, omms, tsince_min, states, batch_size=batch_size)
        if not np.isclose(record.checkpoint_reloaded_loss, selected_loss, rtol=1e-12, atol=0):
            raise RuntimeError("Persisted checkpoint objective does not match the selected model")
    return record


# --------------------------------------------------------------------------------------
# Evaluation


def usable_pairs(trials: pd.DataFrame) -> set[tuple[str, str, pd.Timestamp, float]]:
    """The (mission, window, set epoch, lead) pairs the benchmark scored: truth present, converged, no manoeuvre."""
    usable = trials[~trials["gap"] & ~trials["manoeuvre"] & (trials["sgp4_error"] == 0)]
    ep = pd.to_datetime(usable["set_epoch"])
    ep = ep.dt.tz_convert(None) if getattr(ep.dt, "tz", None) is not None else ep
    return {
        (str(m), str(w), pd.Timestamp(e), float(lead))
        for m, w, e, lead in zip(usable["mission"], usable["window"], ep, usable["lead_h"], strict=True)
    }


def residuals_at_leads(
    items: list[TrialSet],
    predict,
    *,
    leads_hours: tuple[float, ...] = precise.LEADS_HOURS,
    method: str = "",
    keep: set[tuple[str, str, pd.Timestamp, float]] | None = None,
) -> pd.DataFrame:
    """RIC residuals (truth minus prediction) at the benchmark's leads for every set, for one predictor.

    ``predict(omms, tsince_min)`` returns ``(n, 6)`` states in TEME. With ``keep`` (from
    :func:`usable_pairs`) only the set-lead pairs the benchmark itself scored are kept, so every
    method is compared on one population: a lead the benchmark excluded for a manoeuvre or a gap
    is excluded here too.
    """
    leads = np.asarray(leads_hours, dtype=float) * 60.0
    omms = [item.omm for item in items for _ in leads]
    tsince = np.tile(leads, len(items))
    states = predict(omms, tsince)
    rows: list[dict[str, Any]] = []
    for j, item in enumerate(items):
        r_true, v_true, ok = truth_at(item.orbit, item.epoch, leads)
        pred = states[j * len(leads) : (j + 1) * len(leads)]
        good = ok & np.isfinite(pred).all(axis=1)
        if not good.any():
            continue
        basis = ric_basis(r_true[good], v_true[good])
        delta = to_ric(basis, r_true[good] - pred[good, :3])
        for k, lead in zip(np.flatnonzero(good), leads[good], strict=True):
            m = int(np.flatnonzero(np.flatnonzero(good) == k)[0])
            if keep is not None and (item.mission, item.window, item.epoch, float(lead / 60.0)) not in keep:
                continue
            rows.append(
                {
                    "mission": item.mission,
                    "window": item.window,
                    "set_epoch": item.epoch,
                    "lead_h": float(lead / 60.0),
                    "method": method,
                    "radial_km": float(delta[m, 0]),
                    "in_track_km": float(delta[m, 1]),
                    "cross_km": float(delta[m, 2]),
                }
            )
    return pd.DataFrame(rows)


def storm_term_residuals(trials: pd.DataFrame, items: list[TrialSet]) -> pd.DataFrame:
    """The benchmark's own in-track residual with the storm term applied, on the same sets, as a method."""
    keys = {(i.mission, i.window, i.epoch) for i in items}
    usable = trials[~trials["gap"] & ~trials["manoeuvre"] & (trials["sgp4_error"] == 0)].copy()
    ep = pd.to_datetime(usable["set_epoch"])
    ep = ep.dt.tz_convert(None) if getattr(ep.dt, "tz", None) is not None else ep
    usable["set_epoch"] = ep
    mask = [(m, w, e) in keys for m, w, e in zip(usable["mission"], usable["window"], usable["set_epoch"], strict=True)]
    usable = usable[np.asarray(mask, dtype=bool)]
    plain = usable[["mission", "window", "set_epoch", "lead_h", "radial_km", "in_track_km", "cross_km"]].assign(
        method="sgp4 (library, WGS72)"
    )
    supported = usable[usable["b_source"].eq("history")] if "b_source" in usable else usable.iloc[:0]
    supported = supported.dropna(subset=["storm_shift_km", "in_track_corrected_km"])
    term = supported[["mission", "window", "set_epoch", "lead_h", "radial_km", "cross_km"]].copy()
    term["in_track_km"] = supported["in_track_corrected_km"].to_numpy()
    term["method"] = "sgp4 + storm term (observed ap)"
    return pd.concat([plain, term], ignore_index=True)


def summarise(residuals: pd.DataFrame) -> dict[str, Any]:
    """Per window and lead, per method: the median absolute in-track, radial and cross-track residual and n."""
    out: dict[str, Any] = {}
    for (window, lead), g in residuals.groupby(["window", "lead_h"], sort=True):
        entry: dict[str, Any] = {}
        for method, gm in g.groupby("method", sort=False):
            entry[str(method)] = {
                "n": int(len(gm)),
                "n_missions": int(gm["mission"].nunique()),
                "mission_counts": {str(m): int(n) for m, n in gm.groupby("mission").size().items()},
                "in_track_median_km": float(np.median(np.abs(gm["in_track_km"]))),
                "in_track_p95_km": float(np.quantile(np.abs(gm["in_track_km"]), 0.95)),
                "radial_median_km": float(np.median(np.abs(gm["radial_km"]))),
                "cross_median_km": float(np.median(np.abs(gm["cross_km"]))),
            }
        out.setdefault(str(window), {})[f"{float(lead):g}"] = entry
    return out


def summarise_by_mission(residuals: pd.DataFrame) -> dict[str, Any]:
    """The same cells as the pooled summary, without mixing spacecraft."""
    return {str(m): summarise(group) for m, group in residuals.groupby("mission", sort=True)}


def paired_comparison_cells(residuals: pd.DataFrame, plain: str = "sgp4 (library, WGS72)") -> pd.DataFrame:
    """Pooled and spacecraft medians on each method's exact matched trial pairs.

    Source counts expose any unequal method coverage. Each comparison's raw and
    corrected medians use the same rows, and neither ten leads nor spacecraft
    cells are labelled independent experiments.
    """
    keys = ["mission", "window", "set_epoch", "lead_h"]
    if residuals.duplicated(keys + ["method"]).any():
        raise ValueError("Duplicate method/set/lead residuals")
    base = residuals[residuals["method"].eq(plain)]
    rows = []
    for method, candidate in residuals[residuals["method"].ne(plain)].groupby("method", sort=True):
        paired = base.merge(candidate, on=keys, suffixes=("_plain", "_method"), validate="one_to_one")
        valid = np.isfinite(paired[["in_track_km_plain", "in_track_km_method"]].to_numpy(dtype=float)).all(axis=1)
        paired = paired[valid]
        for (window, lead), group in paired.groupby(["window", "lead_h"], sort=True):
            scopes = [("pooled", None, group), *[("spacecraft", str(m), g) for m, g in group.groupby("mission")]]
            for scope, mission, cell in scopes:
                raw = cell["in_track_km_plain"].abs().to_numpy()
                adjusted = cell["in_track_km_method"].abs().to_numpy()
                raw_median, adjusted_median = float(np.median(raw)), float(np.median(adjusted))
                source_mask = base["window"].eq(window) & base["lead_h"].eq(lead)
                method_mask = candidate["window"].eq(window) & candidate["lead_h"].eq(lead)
                if mission is not None:
                    source_mask &= base["mission"].eq(mission)
                    method_mask &= candidate["mission"].eq(mission)
                rows.append(
                    {
                        "scope": scope,
                        "mission": mission,
                        "window": str(window),
                        "lead_h": float(lead),
                        "method": str(method),
                        "n_paired": len(cell),
                        "n_plain_source": int(source_mask.sum()),
                        "n_method_source": int(method_mask.sum()),
                        "n_missions": int(cell["mission"].nunique()),
                        "plain_median_abs_in_track_km": raw_median,
                        "method_median_abs_in_track_km": adjusted_median,
                        "plain_p95_abs_in_track_km": float(np.quantile(raw, 0.95, method="linear")),
                        "method_p95_abs_in_track_km": float(np.quantile(adjusted, 0.95, method="linear")),
                        "median_improvement": 1 - adjusted_median / raw_median if raw_median else None,
                        "trials_improved_count": int((adjusted < raw).sum()),
                        "trials_improved_fraction": float((adjusted < raw).mean()),
                    }
                )
    return pd.DataFrame(rows)


def improvement_over_plain(summary: dict[str, Any], plain: str = "sgp4 (library, WGS72)") -> dict[str, Any]:
    """Per window and lead: each method's change to the median absolute in-track residual against plain SGP4."""
    out: dict[str, Any] = {}
    for window, by_lead in summary.items():
        for lead, methods in by_lead.items():
            base = methods.get(plain, {}).get("in_track_median_km")
            if not base:
                continue
            for method, e in methods.items():
                if method == plain:
                    continue
                out.setdefault(window, {}).setdefault(lead, {})[method] = 1.0 - e["in_track_median_km"] / base
    return out


def recommendation(improvement: dict[str, Any], method: str) -> dict[str, Any]:
    """Apply the historical checkpoint rule on inspected evaluation windows; not a new adoption gate."""
    verdict: dict[str, Any] = {
        "method": method,
        "rule": "historical checkpoint rule: improve the inspected evaluation windows; not a new adoption gate",
    }
    for window in HELD_OUT_WINDOWS:
        by_lead = improvement.get(window, {})
        changes = [v[method] for v in by_lead.values() if method in v]
        if not changes:
            verdict[window] = None
            continue
        verdict[window] = {
            "leads_improved": int(sum(c > 0 for c in changes)),
            "leads": len(changes),
            "median_change": float(np.median(changes)),
            "worst": float(min(changes)),
            "best": float(max(changes)),
        }
    held = [verdict[w] for w in HELD_OUT_WINDOWS if verdict.get(w)]
    verdict["adopt"] = len(held) == len(HELD_OUT_WINDOWS) and all(
        h["leads_improved"] > h["leads"] / 2 and h["median_change"] > 0 for h in held
    )
    return verdict


# --------------------------------------------------------------------------------------
# The page


def _lead(h: float) -> str:
    return f"{h:g} h" if h < 48 else f"{h / 24:g} d"


def to_markdown(record: dict[str, Any], built_at: datetime) -> str:
    s = record["summary"]
    methods = record["methods"]
    lines = [
        "# dSGP4 and ML-dSGP4 on the benchmark's trials",
        "",
        f"{CITATION}. dsgp4 {record['dsgp4_version']}, torch {record['torch_version']}.",
        "",
        PUBLISHED_TRAINING,
        "",
        "**What was done.** " + record["what_was_done"],
        "",
        "**Training.** "
        + "; ".join(
            f"{name}: {t['n_samples']} samples from {t['n_sets']} sets, {t['epochs']} epochs of {t['batch_size']} "
            f"at learning rate {t['learning_rate']:g}, loss {t.get('initial_loss', float('nan')):.2e} at the zero "
            f"start, {t['losses'][0]:.2e} after the first epoch, "
            f"{t.get('selected_loss', min(t['losses'])):.2e} at the retained model, "
            f"{t['seconds']:.0f} s"
            + (" (no epoch beat the zero start, which was kept)" if t.get("kept_zero_start") else "")
            for name, t in record["training"].items()
        )
        + ".",
        (
            "Checkpoint selection uses the objective re-evaluated over the complete fixed training sample after "
            "each epoch. Changing-model minibatch losses are stored separately. Checkpoint hashes, reload checks "
            "and per-spacecraft paired comparison counts accompany the JSON/CSV artifacts."
            if all("selected_loss" in t for t in record["training"].values())
            else "Legacy training records contain changing-model minibatch losses, not fixed-checkpoint objectives."
        ),
        "",
        "## The in-track residual by window and lead, per method",
        "",
        "Cells give median absolute in-track residual in km (number of trials). Quiet and May are training "
        "windows. October and August are excluded from optimizer training, but their earlier results have already "
        "been inspected. This corrected rerun is not a newly uninspected validation experiment. Method changes "
        "in the paired-comparison CSV use exactly shared set/lead rows.",
        "",
    ]
    for window, by_lead in s.items():
        role = "training" if window in TRAINING_WINDOWS else "previously inspected evaluation"
        lines += [
            f"### {window} ({role})",
            "",
            "| Lead | " + " | ".join(methods) + " |",
            "| ---: | " + " | ".join("---:" for _ in methods) + " |",
        ]
        for lead in sorted(by_lead, key=float):
            e = by_lead[lead]
            cells = [f"{e[m]['in_track_median_km']:.2f} ({e[m]['n']})" if m in e else "-" for m in methods]
            lines.append(f"| {_lead(float(lead))} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += [
        "## Change against plain SGP4",
        "",
        "Each method's change to the median absolute in-track residual, relative to the sgp4 library; positive is "
        "better.",
        "",
        "| Window | Lead | " + " | ".join(m for m in methods if m != record["plain"]) + " |",
        "| --- | ---: | " + " | ".join("---:" for m in methods if m != record["plain"]) + " |",
    ]
    for window, by_lead in record["improvement"].items():
        for lead in sorted(by_lead, key=float):
            e = by_lead[lead]
            cells = [f"{e[m]:+.0%}" if m in e else "-" for m in methods if m != record["plain"]]
            lines.append(f"| {window} | {_lead(float(lead))} | " + " | ".join(cells) + " |")
    lines += ["", "## The recommendation", ""]
    for v in record["recommendations"]:
        held = "; ".join(
            f"{w}: {v[w]['leads_improved']} of {v[w]['leads']} leads improved, median change "
            f"{v[w]['median_change']:+.0%}, worst {v[w]['worst']:+.0%}"
            for w in HELD_OUT_WINDOWS
            if v.get(w)
        )
        verdict = "adopt" if v["adopt"] else "do not adopt"
        lines.append(f"- **{v['method']}**: {verdict} ({v['rule']}). Held out: {held or 'no held-out result'}.")
    if all("selected_loss" in t for t in record["training"].values()):
        lines += [
            "",
            "## Retained checkpoints",
            "",
            "The initial model and every candidate checkpoint are evaluated on the same eligible training "
            "targets. The saved checkpoint is reloaded and evaluated once more; its SHA-256 identifies the bytes.",
            "",
            "| Model | Samples kept / candidate | Burn targets excluded | Selected epoch | "
            "Reloaded objective | SHA-256 |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
        for name, t in record["training"].items():
            reloaded = t.get("checkpoint_reloaded_loss")
            lines.append(
                f"| {name} | {t['n_samples']} / {t.get('candidate_targets', '-')} | "
                f"{t.get('excluded_burn_targets', '-')} | {t['selected_epoch']} | "
                f"{f'{reloaded:.6e}' if reloaded is not None else '-'} | {t.get('checkpoint_sha256') or '-'} |"
            )
    if record.get("summary_by_mission"):
        chosen = [record["plain"], *record["training"]]
        lines += [
            "",
            "## Spacecraft results at one and seven days",
            "",
            "Fixed display leads: 24 and 168 hours, median absolute in-track km (n), with every available "
            "spacecraft shown. All leads and exact paired denominators are in `dsgp4_paired_comparisons.csv`; "
            "these correlated spacecraft/lead cells are descriptive, not independent tests.",
            "",
            "| Spacecraft | Window | Lead | " + " | ".join(chosen) + " |",
            "| --- | --- | ---: | " + " | ".join("---:" for _ in chosen) + " |",
        ]
        for mission, windows in record["summary_by_mission"].items():
            for window in HELD_OUT_WINDOWS:
                for lead in ("24", "168"):
                    cell = windows.get(window, {}).get(lead)
                    if not cell:
                        continue
                    cells = [
                        f"{cell[m]['in_track_median_km']:.2f} ({cell[m]['n']})" if m in cell else "-" for m in chosen
                    ]
                    lines.append(f"| {mission} | {window} | {_lead(float(lead))} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## What this does not show",
        "",
        "- The hybrids are trained on one week of quiet sets and one storm week, on the missions listed, with one "
        "architecture and one training recipe; a different recipe could do better or worse, and none is tuned on the "
        "held-out windows.",
        "- The dsgp4 baseline with WGS72 constants is the check that the two implementations agree; the hybrid uses "
        "the library's WGS-84 constants inside, as published, and the WGS-84 baseline shows that difference alone.",
        "- A method that lowers the median can raise the tail; the 95th percentiles are in the JSON beside this page.",
        "",
        f"_Last updated {built_at:%d %B %Y}._",
    ]
    return "\n".join(lines) + "\n"
