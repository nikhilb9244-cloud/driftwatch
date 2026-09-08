"""Callable corrected ML benchmark runner; no fetching or implicit new windows.

Call only after the correction protocol is frozen and the caller authorises the
benchmark rerun. The supplied inputs must be the existing four-window benchmark.
This module does not load orbit files or select a new evaluation period.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from driftwatch.storm import dsgp4_eval
from driftwatch.storm.precise import PreciseOrbit


@dataclass(frozen=True)
class TrainingConfig:
    """A single specified recipe, without a hyperparameter search."""

    seed: int = 0
    hidden_size: int = 35
    epochs: int = 40
    batch_size: int = 4096
    learning_rate: float = 1e-3
    sample_step_min: float = 60.0
    horizon_min: float = 10080.0
    cpu_threads: int = 1
    deterministic_algorithms: bool = True


DEFAULT_TRAINING_CONFIG = TrainingConfig()


def run_corrected_evaluation(
    trials: pd.DataFrame,
    sets: pd.DataFrame,
    orbits: dict[tuple[str, str], PreciseOrbit],
    coverage: dict[str, Any],
    output_dir: Path,
    *,
    config: TrainingConfig = DEFAULT_TRAINING_CONFIG,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Train on masked quiet/May targets and evaluate the existing four windows.

    Inputs/orbits are supplied explicitly by the caller. The protocol file is
    written before propagation or training. Per-target inclusion manifests,
    hashed/reloaded model checkpoints, paired pooled/spacecraft comparisons and
    full residuals are retained beside the evaluation JSON.
    """
    allowed = {*dsgp4_eval.TRAINING_WINDOWS, *dsgp4_eval.HELD_OUT_WINDOWS}
    if not set(trials["window"].unique()) <= allowed or any(window not in allowed for _, window in orbits):
        raise ValueError("The corrected ML rerun accepts only the existing quiet/May/October/August windows")
    if config.hidden_size < 1 or config.cpu_threads < 1 or config.epochs < 1:
        raise ValueError("Invalid fixed model configuration")
    policies = dsgp4_eval.training_exclusions_from_benchmark(trials, coverage)
    import dsgp4
    import torch

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    protocol = {
        "specified_at": now.isoformat(),
        "configuration": asdict(config),
        "training_windows": list(dsgp4_eval.TRAINING_WINDOWS),
        "evaluation_windows": sorted(allowed),
        "precision": "float64",
        "zero_initialisation": True,
        "optimizer": "Adam; cosine learning rate to initial/100",
        "checkpoint_selection": "minimum fixed-sample end-of-epoch objective, including initial model",
        "trial_dataframe_sha256": hashlib.sha256(trials.to_csv(index=False, lineterminator="\n").encode()).hexdigest(),
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__), Path(dsgp4_eval.__file__))
        },
        "exclusions": {
            f"{mission}/{window}": {
                "source": p.source,
                "arc_hours": p.arc_hours,
                "intervals": [[a.isoformat(), b.isoformat()] for a, b in p.intervals],
            }
            for (mission, window), p in policies.items()
        },
        "versions": {"dsgp4": getattr(dsgp4, "__version__", "unknown"), "torch": torch.__version__},
    }
    (output_dir / "dsgp4_protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    torch.set_num_threads(config.cpu_threads)
    torch.use_deterministic_algorithms(config.deterministic_algorithms)
    items = dsgp4_eval.trial_sets(trials, sets, orbits)
    expected = {(m, w, e) for m, w, e, _ in dsgp4_eval.usable_pairs(trials)}
    present = {(i.mission, i.window, i.epoch) for i in items}
    if expected != present:
        raise ValueError(
            f"Missing element sets or reconstructed orbits for {len(expected - present)} usable trial sets"
        )
    training = [item for item in items if item.window in dsgp4_eval.TRAINING_WINDOWS]
    populations = {
        "ML-dSGP4 (Swarm)": [item for item in training if item.mission.startswith("swarm")],
        "ML-dSGP4 (all missions)": training,
    }
    keep = dsgp4_eval.usable_pairs(trials)
    frames = [dsgp4_eval.storm_term_residuals(trials, items)]
    for gravity, label in (("wgs-72", "dsgp4 (WGS72)"), ("wgs-84", "dsgp4 (WGS-84)")):
        frames.append(
            dsgp4_eval.residuals_at_leads(
                items,
                lambda o, t, g=gravity: dsgp4_eval.dsgp4_states(o, t, gravity=g),
                method=label,
                keep=keep,
            )
        )
    records = {}
    for name, population in populations.items():
        if not population:
            continue
        samples = dsgp4_eval.prepare_training_samples(
            population,
            exclusions=policies,
            step_min=config.sample_step_min,
            horizon_min=config.horizon_min,
        )
        stem = "swarm" if name == "ML-dSGP4 (Swarm)" else "all_missions"
        samples.manifest.to_csv(output_dir / f"dsgp4_training_{stem}.csv", index=False)
        model = dsgp4_eval.new_hybrid(config.hidden_size, seed=config.seed)
        record = dsgp4_eval.train_hybrid(
            model,
            samples.omms,
            samples.tsince_min,
            samples.states,
            epochs=config.epochs,
            batch_size=config.batch_size,
            learning_rate=config.learning_rate,
            seed=config.seed,
            sample_sha256=samples.sha256,
            checkpoint_path=output_dir / f"dsgp4_{stem}.pt",
        )
        records[name] = {
            **asdict(record),
            "candidate_targets": len(samples.manifest),
            "excluded_burn_targets": int(samples.manifest["manoeuvre"].sum()),
            "excluded_truth_targets": int((~samples.manifest["truth_covered"]).sum()),
            "excluded_sgp4_error_targets": int(samples.manifest["sgp4_error"].ne(0).sum()),
            "excluded_nonfinite_targets": int((~samples.manifest["finite_states"]).sum()),
        }
        frames.append(
            dsgp4_eval.residuals_at_leads(
                items,
                lambda o, t, m=model: dsgp4_eval.hybrid_states(m, o, t),
                method=name,
                keep=keep,
            )
        )
    residuals = pd.concat(frames, ignore_index=True)
    comparisons = dsgp4_eval.paired_comparison_cells(residuals)
    improvement = {}
    for row in comparisons[comparisons["scope"].eq("pooled")].itertuples(index=False):
        if pd.notna(row.median_improvement):
            improvement.setdefault(row.window, {}).setdefault(f"{row.lead_h:g}", {})[row.method] = (
                row.median_improvement
            )
    plain = "sgp4 (library, WGS72)"
    methods = [plain, "dsgp4 (WGS72)", "dsgp4 (WGS-84)", *records, "sgp4 + storm term (observed ap)"]
    result = {
        "built_at": now.isoformat(),
        "dsgp4_version": protocol["versions"]["dsgp4"],
        "torch_version": protocol["versions"]["torch"],
        "citation": dsgp4_eval.CITATION,
        "published_training": dsgp4_eval.PUBLISHED_TRAINING,
        "what_was_done": (
            f"{len(items)} usable trial sets, trained on the quiet and May windows with the same authoritative "
            "burn intervals as evaluation, truth coverage and zero SGP4 error at each hourly target. "
            "A single frozen recipe was evaluated on pooled and spacecraft-specific paired residuals."
        ),
        "protocol": protocol,
        "training_windows": list(dsgp4_eval.TRAINING_WINDOWS),
        "held_out_windows": list(dsgp4_eval.HELD_OUT_WINDOWS),
        "missions": sorted({i.mission for i in items}),
        "training": records,
        "plain": plain,
        "methods": [m for m in methods if m in set(residuals["method"])],
        "summary": dsgp4_eval.summarise(residuals),
        "summary_by_mission": dsgp4_eval.summarise_by_mission(residuals),
        "improvement": improvement,
        "improvement_estimand": "change in pooled median absolute in-track error on each method's paired set",
        "recommendations": [dsgp4_eval.recommendation(improvement, name) for name in records],
    }
    residuals.to_parquet(output_dir / "dsgp4_residuals.parquet", index=False)
    comparisons.to_csv(output_dir / "dsgp4_paired_comparisons.csv", index=False)
    (output_dir / "dsgp4_evaluation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result, residuals
