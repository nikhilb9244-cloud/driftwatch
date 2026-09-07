"""ESA's dSGP4 and its ML-dSGP4 hybrid on the benchmark's trials.

dsgp4 (Acciarini, Baydin and Izzo, "Closing the gap between SGP4 and high-precision propagation via
differentiable programming", Acta Astronautica 226, 2025, 694-701; github.com/esa/dSGP4) is SGP4
written in PyTorch, so that a propagation is differentiable and can be run in batches. Its hybrid,
ML-dSGP4, wraps the propagator in two small networks: one perturbs the six mean elements before
the propagation, the other perturbs the propagated state after it, each by a bounded (tanh)
fraction, and the two are trained against a higher-precision reference. The published training
used an operator's predictions in a quiet week: the paper fits the hybrid to SpaceX's published
Starlink ephemerides, which are the operator's own propagation, over about a week without a
storm. Nothing published says what the hybrid does through a geomagnetic storm, so the storm
result here is new.

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
trials. The recommendation rule is fixed before the numbers are seen: adopt the hybrid only if it
improves the held-out storms.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

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
    "The published hybrid was trained on an operator's predictions in a quiet week: SpaceX's published Starlink "
    "ephemerides, the operator's own propagation, over about a week without a storm. The storm result here is new."
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
        out.append(TrialSet(str(r.mission), str(r.window), epoch, omm_from_row(row), orbit))
    return out


def truth_at(
    orbit: PreciseOrbit, epoch: pd.Timestamp, tsince_min: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    at = (
        np.datetime64(epoch.to_datetime64(), "us")
        + (np.asarray(tsince_min, dtype=float) * 60e6).astype("timedelta64[us]")
    ).astype("datetime64[us]")
    return orbit.states_teme(at)


def training_samples(
    items: Iterable[TrialSet], *, step_min: float = SAMPLE_STEP_MIN, horizon_min: float = HORIZON_MIN
) -> tuple[list[Any], np.ndarray, np.ndarray]:
    """``(omms, tsince_min, true_states)``: one row per hour of truth for every training set."""
    omms: list[Any] = []
    tsince: list[float] = []
    states: list[np.ndarray] = []
    grid = np.arange(step_min, horizon_min + 1e-9, step_min)
    for item in items:
        r, v, ok = truth_at(item.orbit, item.epoch, grid)
        for k in np.flatnonzero(ok):
            omms.append(item.omm)
            tsince.append(float(grid[k]))
            states.append(np.concatenate([r[k], v[k]]))
    return omms, np.asarray(tsince, dtype=float), np.asarray(states, dtype=float).reshape(-1, 6)


# --------------------------------------------------------------------------------------
# The models


def new_hybrid(hidden_size: int = 35, *, zero_start: bool = True, seed: int = 0):
    """An ML-dSGP4 model; with ``zero_start`` its two corrections begin at zero, so it starts as SGP4."""
    import dsgp4

    torch = _torch()
    torch.manual_seed(seed)
    model = dsgp4.mldsgp4(hidden_size=hidden_size)
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
) -> TrainingRecord:
    """Adam on the mean squared error of the normalised state; the record carries the loss per epoch."""
    torch = _torch()
    rng = np.random.default_rng(seed)
    n = len(omms)
    target = np.concatenate([states[:, :3] / model.normalization_R, states[:, 3:] / model.normalization_V], axis=1)
    target_t = torch.tensor(target, dtype=torch.float64)
    ts_all = torch.tensor(tsince_min, dtype=torch.float64)
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    # The corrections start at zero and the needed ones are small, so the rate falls through the run
    # (cosine, to a hundredth of its start) and the epoch with the lowest training loss is kept; the
    # held-out windows play no part in either.
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimiser, T_max=max(epochs, 1), eta_min=learning_rate / 100)
    losses: list[float] = []
    # The zero start is itself a candidate: it is scored first and restored if nothing beats it.
    model.eval()
    with torch.no_grad():
        initial = 0.0
        for k in range(0, n, batch_size):
            batch = omms[k : k + batch_size]
            x = (
                model(batch, ts_all[k : k + batch_size])
                if len(batch) > 1
                else model(batch[0], ts_all[k : k + batch_size])
            )
            initial += float(torch.mean((x - target_t[k : k + batch_size]) ** 2)) * len(batch)
        initial /= max(n, 1)
    best = (initial, {k: v.detach().clone() for k, v in model.state_dict().items()})
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
        losses.append(total / max(n, 1))
        scheduler.step()
        if losses[-1] < best[0]:
            best = (losses[-1], {k: v.detach().clone() for k, v in model.state_dict().items()})
        log.info("ML-dSGP4 epoch %d/%d: loss %.3e (%.0f s)", epoch + 1, epochs, losses[-1], time.time() - t0)
    kept_zero = bool(losses) and min(losses) >= initial
    if best[1] is not None:
        model.load_state_dict(best[1])
    model.eval()
    n_sets = len({id(o) for o in omms})
    return TrainingRecord(n, n_sets, epochs, batch_size, learning_rate, losses, time.time() - t0, initial, kept_zero)


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
    term = usable.dropna(subset=["storm_shift_km"])[
        ["mission", "window", "set_epoch", "lead_h", "radial_km", "cross_km"]
    ].copy()
    term["in_track_km"] = usable.dropna(subset=["storm_shift_km"])["in_track_corrected_km"].to_numpy()
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
                "in_track_median_km": float(np.median(np.abs(gm["in_track_km"]))),
                "in_track_p95_km": float(np.quantile(np.abs(gm["in_track_km"]), 0.95)),
                "radial_median_km": float(np.median(np.abs(gm["radial_km"]))),
                "cross_median_km": float(np.median(np.abs(gm["cross_km"]))),
            }
        out.setdefault(str(window), {})[f"{float(lead):g}"] = entry
    return out


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
    """The rule, applied: adopt only if the held-out storms improve at most leads, and say what happened."""
    verdict: dict[str, Any] = {"method": method, "rule": "adopt only if the held-out storms improve"}
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
    verdict["adopt"] = bool(held) and all(h["leads_improved"] > h["leads"] / 2 and h["median_change"] > 0 for h in held)
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
            f"start, {t['losses'][0]:.2e} after the first epoch, {min(t['losses']):.2e} at the best, "
            f"{t['seconds']:.0f} s"
            + (" (no epoch beat the zero start, which was kept)" if t.get("kept_zero_start") else "")
            for name, t in record["training"].items()
        )
        + ".",
        "",
        "## The in-track residual by window and lead, per method",
        "",
        "Median absolute in-track residual, km, against the reconstructed orbit, on the same sets for every method; "
        "n is the number of trials. Quiet and May are the hybrids' training windows; October and August are held out.",
        "",
    ]
    for window, by_lead in s.items():
        role = "training" if window in TRAINING_WINDOWS else "held out"
        lines += [
            f"### {window} ({role})",
            "",
            "| Lead | n | " + " | ".join(methods) + " |",
            "| ---: | ---: | " + " | ".join("---:" for _ in methods) + " |",
        ]
        for lead in sorted(by_lead, key=float):
            e = by_lead[lead]
            n = max((v["n"] for v in e.values()), default=0)
            cells = [f"{e[m]['in_track_median_km']:.2f}" if m in e else "-" for m in methods]
            lines.append(f"| {_lead(float(lead))} | {n} | " + " | ".join(cells) + " |")
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
