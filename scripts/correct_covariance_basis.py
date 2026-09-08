"""Amend stored component coverage without refitting covariance or changing residuals.

The original model has diagonal predicted-RIC covariance. Reconstruct both
bases from the original states, check the saved residuals, then transport that
matrix into truth RIC. Frozen September outputs are never overwritten.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs
from driftwatch.screening.ric import ric_basis, to_ric, transport_covariance
from driftwatch.storm import benchmark_statistics, precise, reference, reference_run

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/validation/covariance-basis-correction-2026-09-08"
SIGMAS = ["sigma_r_km", "sigma_i_km", "sigma_c_km"]
COMPONENTS = ["radial", "in_track", "cross"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")


def retain_noncomponent_results(original, corrected):
    """Retain storm-term diagnostics and legacy fields unaffected by this amendment."""
    for scope in ("by_band", "by_mission"):
        for name, windows in corrected[scope].items():
            for window, group in windows.items():
                old = original[scope][name][window]
                group["by_lead_h"] = {
                    lead: {**old["by_lead_h"][lead], **cell} for lead, cell in group["by_lead_h"].items()
                }
                windows[window] = {**old, **group}
    return corrected


def amend(label, original, sets, orbit_loader):
    old = pd.read_parquet(original)
    new = old.copy()
    sets = sets.copy()
    sets["_epoch"] = pd.to_datetime(sets.epoch, utc=True).dt.tz_convert(None)
    sources = np.full((len(old), 3, 3), np.nan)
    targets = sources.copy()
    max_difference = 0.0
    for (mission, window), frame in old.groupby(["mission", "window"]):
        orbit = orbit_loader(mission, window)
        assert orbit is not None
        for epoch, group in frame.groupby("set_epoch"):
            one = sets[sets.norad_id.eq(group.norad_id.iloc[0]) & sets._epoch.eq(epoch)]
            assert len(one) == 1, (mission, epoch, len(one))
            at = group.t.to_numpy(dtype="datetime64[us]")
            state = propagate_satrecs(build_satrecs(one), one.norad_id.to_numpy(), at)
            r, v, covered = orbit.states_teme(at)
            assert np.array_equal(~group.gap.to_numpy(), covered)
            assert np.array_equal(group.sgp4_error, state.error[0])
            source = ric_basis(state.r_teme[0], state.v_teme[0])
            target = ric_basis(r, v)
            residual = to_ric(target, r - state.r_teme[0])
            saved = group[[f"{c}_km" for c in COMPONENTS]].to_numpy()
            valid = covered & group.sgp4_error.eq(0).to_numpy()
            if valid.any():
                difference = float(np.max(np.abs(residual[valid] - saved[valid])))
                max_difference = max(max_difference, difference)
                np.testing.assert_allclose(residual[valid], saved[valid], rtol=0, atol=1e-7)
            covariance = np.zeros((len(group), 3, 3))
            covariance[:, np.arange(3), np.arange(3)] = group[SIGMAS].to_numpy() ** 2
            transported = transport_covariance(covariance, source, target)
            new.loc[group.index, SIGMAS] = np.sqrt(np.diagonal(transported, axis1=-2, axis2=-1))
            sources[group.index], targets[group.index] = source, target
        print(f"{label}: {mission}/{window} transported", flush=True)
    for component, sigma in zip(COMPONENTS, SIGMAS, strict=True):
        for multiple in (1, 2):
            new[f"{component}_inside_{multiple}s"] = new[f"{component}_km"].abs() <= multiple * new[sigma]
    changed_columns = SIGMAS + [f"{c}_inside_{s}s" for c in COMPONENTS for s in (1, 2)]
    pd.testing.assert_frame_equal(old.drop(columns=changed_columns), new.drop(columns=changed_columns))
    new.to_parquet(OUT / f"{label}-trials.parquet", index=False)
    np.savez_compressed(OUT / f"{label}-bases.npz", source=sources, target=targets)
    print(f"{label}: summarising coverage and deletion sensitivities", flush=True)
    before = benchmark_statistics.summarise_trials(old, include_sensitivities=False)
    after = benchmark_statistics.summarise_trials(new)
    rows = []
    for scope in ("by_band", "by_mission"):
        for name, windows in after[scope].items():
            for window, group in windows.items():
                old_group = before[scope][name][window]
                assert group["horizons_by_criterion"] == old_group["horizons_by_criterion"]
                for lead, cell in group["by_lead_h"].items():
                    for component, value in cell["components"].items():
                        previous = old_group["by_lead_h"][lead]["components"][component]
                        a, b = previous["coverage"], value["coverage"]
                        rows.append(
                            {
                                "scope": scope,
                                "name": name,
                                "window": window,
                                "lead_h": lead,
                                "component": component,
                                "old": previous,
                                "new": value,
                                "coverage_changed": any(a[k] != b[k] for k in a if k != "median_sigma_km"),
                            }
                        )
    return {
        "input": {"path": original.relative_to(ROOT).as_posix(), "sha256": digest(original)},
        "max_reconstructed_residual_difference_km": max_difference,
        "n_cells": len(rows),
        "n_coverage_cells_changed": sum(r["coverage_changed"] for r in rows),
        "horizons_unchanged": True,
        "results": after,
        "cells": rows,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Copies are write-once: rerunning always begins with the pre-correction bytes.
    for name, source in (
        ("reference-original.parquet", ROOT / "data/validation/reference_benchmark.parquet"),
        ("reference-original.json", ROOT / "data/validation/reference_benchmark.json"),
        ("benchmark-v2-original.json", ROOT / "docs/assets/benchmark-v2.json"),
    ):
        if not (OUT / name).exists():
            shutil.copyfile(source, OUT / name)
    missions = list(reference.MISSIONS.values())
    sets = reference_run.load_sets(missions, list(reference.WINDOWS))
    windows = {w.name: w for w in reference.WINDOWS}

    def orbit(mission, window):
        w = windows[window]
        return reference.load_truth(
            reference.MISSIONS[mission],
            (w.sets_from - timedelta(days=1)).date(),
            w.truth_to.date(),
            offline=True,
            records=False,
        )[0]

    result = {
        "method_version": "truth-ric-covariance-v1",
        "corrected_at": datetime.now(UTC).isoformat(),
        "formula": "Q = B_truth B_predicted.T; C_truth = Q C_predicted Q.T",
        "scope": "Component sigmas and coverage only; saved residuals, masks and horizons unchanged",
    }
    result["reference"] = amend("reference", OUT / "reference-original.parquet", sets, orbit)
    raw = json.loads((OUT / "reference-original.json").read_text())
    retain_noncomponent_results(raw["summary"]["results"], result["reference"]["results"])
    locked = ROOT / "data/validation/locked-september-2024"
    gp = json.loads((locked / "gp-input-manifest.json").read_text())

    def locked_orbit(mission, window):
        manifest = json.loads((locked / f"{mission}-inputs-manifest.json").read_text())
        for key in ("metadata", "orbit_table"):
            assert digest(locked / manifest[key]) == manifest["files"][manifest[key]]
        meta = json.loads((locked / manifest["metadata"]).read_text())["orbit"]
        return precise.PreciseOrbit(
            meta["letter"],
            meta["norad_id"],
            pd.read_parquet(locked / manifest["orbit_table"]),
            [date.fromisoformat(d) for d in meta["days_missing"]],
            meta["files"],
            meta["frame"],
        )

    result["september"] = amend(
        "september", locked / "locked_trials.parquet", pd.read_parquet(locked / gp["table"]), locked_orbit
    )
    write_json(OUT / "correction.json", result)
    post_burn = raw["summary"]["results"]["post_burn"]
    raw["summary"]["results"] = {**result["reference"]["results"], "post_burn": post_burn}
    raw["covariance_basis_correction"] = {
        "path": (OUT / "correction.json").relative_to(ROOT).as_posix(),
        "sha256": digest(OUT / "correction.json"),
    }
    write_json(ROOT / "data/validation/reference_benchmark.json", raw)
    shutil.copyfile(OUT / "reference-trials.parquet", ROOT / "data/validation/reference_benchmark.parquet")
    print(
        json.dumps(
            {
                k: {n: v for n, v in result[k].items() if n not in {"results", "cells"}}
                for k in ("reference", "september")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
