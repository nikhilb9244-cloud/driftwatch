"""Build one canonical evidence object, then render the v2 reference publication.

This reads stored results only. It never fetches or propagates or selects a new
evaluation window. Pending analyses must be supplied explicitly on the command
line; their absence cannot silently preserve a v1 claim.
"""
# ruff: noqa: E501  (Markdown paragraphs are kept as intact publication source.)

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import publication_text

from driftwatch.radio import site as radio_site
from driftwatch.storm import benchmark_statistics as statistics
from driftwatch.storm import manoeuvre_records, precise, reference, slr

ROOT = Path(__file__).resolve().parents[1]


def bibliography() -> dict:
    return {
        "sgp4": {
            "title": "Vallado et al., Revisiting Spacetrack Report #3 (AIAA 2006-6753)",
            "url": "https://celestrak.org/publications/AIAA/2006-6753/",
            "purpose": "SGP4 reference code, conventions and validation cases",
        },
        "swarm": {
            "title": "ESA Swarm dissemination service",
            "url": precise.SWARM_DISS_URL,
            "purpose": "Swarm reconstructed orbit and thruster products",
        },
        "gracefo": {
            "title": "JPL GRACE-FO Level-1B products, GFZ distribution",
            "url": reference.GFZ_BASE_URL,
            "purpose": "GRACE-FO GNV1B reconstructed orbits and THR1B records",
        },
        "ids_orbits": {
            "title": "IDS data and products",
            "url": "https://ids-doris.org/data-products/section-content-dataproducts.html",
            "purpose": "CNES/SSALTO precise orbit products and distribution",
        },
        "ids_events": {
            "title": "IDS table of system events reported by SSALTO",
            "url": manoeuvre_records.IDS_URL,
            "purpose": "Published manoeuvre intervals and declared source time systems",
        },
        "sentinel3": {
            "title": "SentiWiki altimetry processing and manoeuvre histories",
            "url": manoeuvre_records.SENTINEL3_INDEX_URL,
            "purpose": "Sentinel-3 manoeuvre histories with UTC timestamps",
        },
        "sentinel1": {
            "title": "ESA Sentinel-1A precise orbit auxiliary products",
            "url": reference.S1_BASE_URL,
            "purpose": "Sentinel-1A reconstructed orbits",
        },
        "slr": {
            "title": "EUROLAS Data Center normal-point archive",
            "url": slr.EDC_NPT_URL,
            "purpose": "Sampled laser-range observations",
        },
        "dsgp4": {
            "title": "Acciarini, Baydin and Izzo, Closing the gap between SGP4 and high-precision propagation via differentiable programming",
            "url": "https://doi.org/10.1016/j.actaastro.2024.10.063",
            "purpose": "Differentiable propagator and hybrid model reference",
        },
        "dsgp4_code": {
            "title": "ESA dSGP4 source and documentation",
            "url": "https://github.com/esa/dSGP4",
            "purpose": "Upstream implementation; local experiment is separately specified",
        },
        "dsgp4_manuscript": {
            "title": "Acciarini, Baydin and Izzo, author manuscript: experimental design",
            "url": "https://arxiv.org/html/2402.04830v5#S4.SS2",
            "purpose": "Published training data and recipe; the local benchmark is an adaptation",
        },
        "meerkat_paper": {
            "title": "de Villiers, MeerKAT Holography Measurements in the UHF, L, and S bands",
            "url": "https://arxiv.org/abs/2301.06752",
            "purpose": "Frequency-dependent measured primary-beam response",
        },
        "meerkat_data": {
            "title": "MeerKAT measured primary-beam data release",
            "url": radio_site.MEASURED_BEAM_DOI,
            "purpose": "Measured Jones patterns; third-party data licence retained",
        },
        "satchecker": {
            "title": "SatChecker field-of-view API documentation",
            "url": "https://satchecker.readthedocs.io/en/latest/fov.html",
            "purpose": "Context for the proposed metadata shape; no upstream acceptance is claimed",
        },
        "satchecker_accuracy": {
            "title": "SatChecker accuracy and usage notes",
            "url": "https://satchecker.readthedocs.io/en/latest/notes.html",
            "purpose": "Source-dependent limitations of satellite position estimates",
        },
    }


def cite(data: dict, key: str) -> str:
    source = data["bibliography"][key]
    return f"[{source['title']}]({source['url']})"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_evidence(path: Path) -> dict:
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path).astype(object)
        return {"rows": frame.where(pd.notna(frame), None).to_dict("records")}
    return read_json(path)


def provenance(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def locked_access_evidence(path: Path, protocol_evidence: dict) -> dict:
    """Read the immutable first-access/attestation metadata without reading outcomes."""
    digest = protocol_evidence["input"]["sha256"]
    access = read_json(path)
    if access["protocol_sha256"] != digest:
        raise ValueError("Locked first-access marker refers to another protocol")
    source_binding = hashlib.sha256(
        json.dumps(protocol_evidence["result"]["source_hashes"], sort_keys=True).encode()
    ).hexdigest()
    if access["source_manifest_sha256"] != source_binding:
        raise ValueError("Locked first access refers to another source manifest")
    evidence = {"access": {"status": "supplied", "input": provenance(path), "result": access}}
    attestation = access["attestation"]
    attestation_path = Path(attestation["path"]).resolve()
    if not attestation_path.is_relative_to(ROOT):
        raise ValueError("Locked attestation must have a preserved workspace copy")
    if provenance(attestation_path)["sha256"] != attestation["sha256"]:
        raise ValueError("Locked author attestation hash differs")
    if read_json(attestation_path) != attestation["record"] or attestation["record"]["protocol_sha256"] != digest:
        raise ValueError("Locked author attestation does not bind the frozen protocol")
    if attestation["record"]["statement"] != protocol_evidence["result"]["required_attestation_statement"]:
        raise ValueError("Locked author attestation does not contain the required statement")
    if datetime.fromisoformat(attestation["record"]["attested_at"]) > datetime.fromisoformat(access["started_at"]):
        raise ValueError("Locked author attestation postdates first experiment access")
    binding = hashlib.sha256(json.dumps(attestation, sort_keys=True).encode()).hexdigest()
    if access["attestation_sha256"] != binding:
        raise ValueError("Locked author attestation differs from its first-access binding")
    evidence["attestation"] = {
        "status": "supplied",
        "input": provenance(attestation_path),
        "result": attestation["record"],
    }
    return evidence


def locked_completion_evidence(path: Path, result: dict, protocol_evidence: dict) -> dict:
    """Accept a locked result only after its final, hash-bound inventory exists."""
    directory = path.parent.resolve()
    protocol = protocol_evidence["result"]
    digest = protocol_evidence["input"]["sha256"]
    if result["protocol_sha256"] != digest or result["protocol"] != protocol:
        raise ValueError("Locked result differs from the frozen scientific protocol")
    if not result.get("completed_at") or set(result["coverage"]) != set(protocol["missions"]):
        raise ValueError("Locked result does not contain every frozen mission")
    evidence = locked_access_evidence(directory / "first-data-access.json", protocol_evidence)
    source = directory / "completion-manifest.json"
    completion = read_json(source)
    access = evidence["access"]["result"]
    for key in ("protocol_sha256", "source_manifest_sha256", "attestation_sha256"):
        if completion[key] != access[key]:
            raise ValueError(f"Locked completion and first access disagree: {key}")
    evidence["completion"] = {"status": "supplied", "input": provenance(source), "result": completion}
    if not {"locked_trials.parquet", path.name} <= set(completion["files"]):
        raise ValueError("Locked completion manifest omits aggregate files")
    for relative, expected in completion["files"].items():
        source = (directory / relative).resolve()
        if not source.is_relative_to(directory) or provenance(source)["sha256"] != expected:
            raise ValueError(f"Locked completion file fails its hash: {relative}")
    mission_hashes = result["mission_completion_sha256"]
    if set(mission_hashes) != set(protocol["missions"]) or completion["mission_completion_sha256"] != mission_hashes:
        raise ValueError("Locked completion manifest does not identify every frozen mission")
    for mission, expected in mission_hashes.items():
        source = directory / f"{mission}-completion.json"
        if provenance(source)["sha256"] != expected:
            raise ValueError(f"Locked mission completion hash differs: {mission}")
    if result["first_data_access"] != access:
        raise ValueError("Locked result and first-access marker disagree")
    trials = pd.read_parquet(directory / "locked_trials.parquet")
    validate_summary_counts(trials, result["secondary"])
    if len(result["events"]) != result["primary"]["all_recorded_burns"]["n_events"]:
        raise ValueError("Locked primary count differs from its event inventory")
    for mission, coverage in result["coverage"].items():
        events = [event for event in result["events"] if event["mission"] == mission]
        if coverage["n_recorded_burns"] != len(events):
            raise ValueError(f"Locked coverage count differs from its event inventory: {mission}")
    for mission in ("gracefo-c", "gracefo-d"):
        if mission not in protocol["missions"]:
            continue
        source = directory / "supporting-evidence" / mission / "thruster-products-manifest.json"
        support = read_json(source)
        for key in ("protocol_sha256", "source_manifest_sha256", "attestation_sha256"):
            if support[key] != access[key]:
                raise ValueError(f"GRACE supporting manifest binding differs: {mission}/{key}")
        if support["mission"] != mission or support["gp_manifest_sha256"] != result["gp_manifest_sha256"]:
            raise ValueError(f"GRACE supporting manifest identifies another mission or GP input: {mission}")
        if (
            support["normal_input_manifest_sha256"]
            != provenance(directory / f"{mission}-inputs-manifest.json")["sha256"]
        ):
            raise ValueError(f"GRACE supporting manifest identifies another frozen input snapshot: {mission}")
        if support["original_first_access_sha256"] != evidence["access"]["input"]["sha256"]:
            raise ValueError(f"GRACE supporting manifest identifies another first access: {mission}")
        if support["n_products"] != len(support["products"]) or support["n_products"] != len(support["files"]):
            raise ValueError(f"GRACE supporting product inventory differs: {mission}")
        total_bytes = 0
        for relative, expected in support["files"].items():
            product = (directory / relative).resolve()
            if not product.is_relative_to(directory) or provenance(product)["sha256"] != expected:
                raise ValueError(f"GRACE supporting product fails its hash: {relative}")
            total_bytes += product.stat().st_size
        if total_bytes != support["total_bytes"]:
            raise ValueError(f"GRACE supporting byte inventory differs: {mission}")
        evidence[f"thrusters_{mission.replace('-', '_')}"] = {
            "status": "supplied",
            "input": provenance(source),
            "result": support,
        }
    return evidence


def locked_publication_diagnostics(result: dict) -> dict:
    events = result["events"]
    endpoint_groups = {}
    class_counts = {}
    for event in events:
        class_counts[event["class"]] = class_counts.get(event["class"], 0) + 1
        if event.get("epoch") is not None and event.get("target") is not None:
            key = (event["mission"], event["epoch"], event["target"])
            endpoint_groups.setdefault(key, []).append(event["event_id"])
    complete = [
        event
        for event in events
        if event.get("predicted_in_track_km") is not None and event.get("signed_in_track_km") is not None
    ]
    largest = (
        max(complete, key=lambda event: abs(event["signed_in_track_km"] - event["predicted_in_track_km"]))
        if complete
        else None
    )
    deletions = result["primary"]["leave_one_spacecraft_out"]
    plateau = pd.Timedelta(hours=result["protocol"]["plateau_hours"])
    plateau_overlaps = []
    for event in events:
        start, end = pd.Timestamp(event["burn_from"]), pd.Timestamp(event["burn_to"])
        neighbours = [
            other for other in events if other["mission"] == event["mission"] and other["event_id"] != event["event_id"]
        ]
        before = [
            other["event_id"]
            for other in neighbours
            if pd.Timestamp(other["burn_to"]) >= start - plateau and pd.Timestamp(other["burn_from"]) <= start
        ]
        after = [
            other["event_id"]
            for other in neighbours
            if pd.Timestamp(other["burn_to"]) >= end and pd.Timestamp(other["burn_from"]) <= end + plateau
        ]
        if before or after:
            plateau_overlaps.append(
                {
                    "event_id": event["event_id"],
                    "pre_plateau_events": before,
                    "post_plateau_events": after,
                    "class": event["class"],
                    "fraction": event["fraction"],
                    "retained_in_no_additional_burn_subset": not event["later_burns"],
                }
            )
    return {
        "n_protocol_missions": len(result["protocol"]["missions"]),
        "n_secondary_raw_pairs": sum(
            cell["n_total"]
            for windows in result["secondary"]["by_mission"].values()
            for group in windows.values()
            for cell in group["by_lead_h"].values()
        ),
        "n_secondary_usable_pairs": sum(
            cell["n"]
            for windows in result["secondary"]["by_mission"].values()
            for group in windows.values()
            for cell in group["by_lead_h"].values()
        ),
        "n_event_spacecraft": len({event["mission"] for event in events}),
        "n_unique_post_event_endpoints": len(endpoint_groups),
        "shared_endpoint_groups": [
            {"mission": key[0], "epoch": key[1], "target": key[2], "event_ids": value}
            for key, value in endpoint_groups.items()
            if len(value) > 1
        ],
        "class_counts": class_counts,
        "plateau_overlap_scope": "Other recorded in-month burns overlapping the fixed pre/post-event plateaus",
        "plateau_overlaps": plateau_overlaps,
        "orbit_detector_misses": sum(event["orbit_detector_missed"] for event in events),
        "element_detector_misses": sum(event["element_detector_missed"] for event in events),
        "n_spacecraft_deletions": len(deletions),
        "n_spacecraft_deletions_lower_prediction_mae": sum(
            value.get("mean_absolute_error_prediction_km", float("inf"))
            < value.get("mean_absolute_error_zero_km", float("inf"))
            for value in deletions.values()
        ),
        "largest_abs_prediction_error": None
        if largest is None
        else {
            "selection": "Largest absolute prediction error among complete endpoints, selected after scoring",
            "event_id": largest["event_id"],
            "mission": largest["mission"],
            "fraction": largest["fraction"],
            "class": largest["class"],
            "absolute_prediction_error_km": abs(largest["signed_in_track_km"] - largest["predicted_in_track_km"]),
        },
        "retention_note": (
            "Parsed GRACE-FO GNV1B and THR1B products are retained and hashed. The existing loader deleted the "
            "large daily transport archives after parsing, so neither original raw GRACE transport archives nor "
            "raw text products were retained. This is a source-retention limitation relative to the frozen protocol's "
            "raw-source preservation requirement. "
            "The separate supporting THR manifests repair the omission of thruster filenames from the frozen normal "
            "record.files inventory; they do not repair the absence of raw archives. The frozen input manifests, "
            "event intervals, scientific rules and results remain unchanged."
        ),
    }


def groups(results: dict):
    for scope in ("by_band", "by_mission"):
        for name, windows in results[scope].items():
            for window, value in windows.items():
                yield scope, name, window, value


def endpoint(horizon: dict) -> tuple:
    return (horizon.get("last_lead_h_within"), horizon.get("first_lead_h_beyond"), horizon.get("termination"))


def changed_number(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a != b
    return not np.isclose(a, b, rtol=1e-12, atol=1e-12)


def correction_data(old: dict, current: dict, published: dict, old_trials: pd.DataFrame, trials: pd.DataFrame) -> dict:
    horizon_rows, component_rows = [], []
    for scope, name, window, group in groups(current):
        previous = old.get(scope, {}).get(name, {}).get(window)
        if previous is None:
            continue
        original = published.get(scope, {}).get(name, {}).get(window, {}).get("horizon", {})
        old_linear = previous["horizons_by_criterion"]["linear_quantile"]
        new_linear = group["horizons_by_criterion"]["linear_quantile"]
        primary = group["horizon"]
        record_change = endpoint(old_linear) != endpoint(new_linear)
        criterion_change = endpoint(new_linear) != endpoint(primary)
        original_change = original.get("last_lead_h_within") != primary.get("last_lead_h_within") or original.get(
            "first_lead_h_beyond"
        ) != primary.get("first_lead_h_beyond")
        horizon_rows.append(
            {
                "scope": scope,
                "name": name,
                "window": window,
                "published_v1": original,
                "v1_recomputed_linear": old_linear,
                "corrected_linear": new_linear,
                "corrected_primary": primary,
                "source_or_residual_change": record_change,
                "criterion_change": criterion_change,
                "published_endpoint_change": original_change,
                "old_n_by_lead": {k: v["n"] for k, v in previous["by_lead_h"].items()},
                "new_n_by_lead": {k: v["n"] for k, v in group["by_lead_h"].items()},
            }
        )
        for lead, entry in group["by_lead_h"].items():
            old_entry = previous["by_lead_h"].get(lead, {})
            for component, cell in entry["components"].items():
                old_cell = old_entry.get("components", {}).get(component)
                if old_cell is None:
                    continue
                cov, old_cov = cell["coverage"], old_cell["coverage"]
                fields = (
                    "n",
                    "inside_1_sigma_count",
                    "inside_2_sigma_count",
                    "inside_1_sigma_fraction",
                    "inside_2_sigma_fraction",
                    "median_sigma_km",
                )
                changes = {
                    key: {"old": old_cov.get(key), "new": cov.get(key)}
                    for key in fields
                    if changed_number(old_cov.get(key), cov.get(key))
                }
                for key in ("median_abs_km",):
                    if changed_number(old_cell[key], cell[key]):
                        changes[key] = {"old": old_cell[key], "new": cell[key]}
                for method in ("linear", "inverted_cdf"):
                    a, b = old_cell["quantile_abs_km"][method], cell["quantile_abs_km"][method]
                    if changed_number(a, b):
                        changes[f"quantile_{method}_km"] = {"old": a, "new": b}
                if changes:
                    component_rows.append(
                        {
                            "scope": scope,
                            "name": name,
                            "window": window,
                            "lead_h": float(lead),
                            "component": component,
                            "old": old_cell,
                            "new": cell,
                            "changed_fields": changes,
                        }
                    )
    keys = ["mission", "window", "set_epoch", "lead_h"]
    joined = old_trials.merge(trials, on=keys, suffixes=("_old", "_new"), how="outer", indicator=True)
    matched = joined[joined._merge.eq("both")]
    old_ok = (
        ~matched.gap_old.astype(bool)
        & ~matched.manoeuvre_old.astype(bool)
        & matched.sgp4_error_old.eq(0)
        & np.isfinite(matched.in_track_km_old)
    )
    new_ok = (
        ~matched.gap_new.astype(bool)
        & ~matched.manoeuvre_new.astype(bool)
        & matched.sgp4_error_new.eq(0)
        & np.isfinite(matched.in_track_km_new)
    )
    old_masks = matched.loc[old_ok & ~new_ok, keys]
    restored = matched.loc[~old_ok & new_ok, keys]
    return {
        "interpretation": "Frozen v1 and corrected trials, identical statistical code; published v1 linear endpoints "
        "are retained separately from recomputed linear and corrected empirical-coverage endpoints.",
        "newly_excluded_pairs": len(old_masks),
        "restored_pairs": len(restored),
        "unmatched_old_pairs": int(joined._merge.eq("left_only").sum()),
        "unmatched_new_pairs": int(joined._merge.eq("right_only").sum()),
        "newly_excluded_by_mission_window": old_masks.groupby(["mission", "window"])
        .size()
        .rename("n")
        .reset_index()
        .to_dict("records"),
        "restored_by_mission_window": restored.groupby(["mission", "window"])
        .size()
        .rename("n")
        .reset_index()
        .to_dict("records"),
        "horizons": horizon_rows,
        "components": component_rows,
    }


def discrepancy_diagnostics(trials: pd.DataFrame, results: dict, windows: dict) -> dict:
    """Named audit questions, computed from the corrected raw population."""
    usable = trials[~trials.gap & ~trials.manoeuvre & trials.sgp4_error.eq(0)]
    storm_windows = [name for name, value in windows.items() if value.get("disturbed")]
    band_min = trials.groupby("altitude_band").altitude_km.min().to_dict()
    above = [band for band, low in band_min.items() if low >= 600]
    low_band = str(trials.loc[trials.mission.eq("swarm-a"), "altitude_band"].iloc[0])
    high_band = str(trials.loc[trials.mission.eq("jason-3"), "altitude_band"].iloc[0])

    def range_cells(lead: int, bands: list, selected_windows: list) -> dict:
        cells = []
        for band in bands:
            for window in selected_windows:
                coverage = results["by_band"][band][window]["by_lead_h"][str(lead)]["components"]["in_track"][
                    "coverage"
                ]
                cells.append({"band": band, "window": window, "lead_h": lead, **coverage})
        defined = [cell for cell in cells if cell["inside_2_sigma_fraction"] is not None]
        return {
            "cells": cells,
            "n_defined_cells": len(defined),
            "minimum": min(defined, key=lambda cell: cell["inside_2_sigma_fraction"]) if defined else None,
            "maximum": max(defined, key=lambda cell: cell["inside_2_sigma_fraction"]) if defined else None,
        }

    swarm = usable[usable.mission.str.startswith("swarm-") & usable.window.eq("storm") & usable.lead_h.eq(168)]

    def storm_scope(frame: pd.DataFrame) -> dict:
        raw = frame.in_track_km.to_numpy(dtype=float)
        shift = frame.storm_shift_km.to_numpy(dtype=float)
        raw, shift = raw[np.isfinite(raw)], shift[np.isfinite(shift)]
        return {
            "n_pairs": len(frame),
            "mission_counts": {str(k): int(v) for k, v in frame.mission.value_counts().sort_index().items()},
            "coefficient_source_counts": {str(k): int(v) for k, v in frame.b_source.value_counts(dropna=False).items()},
            "n_finite_raw": len(raw),
            "n_finite_shift": len(shift),
            "median_abs_in_track_km": float(np.median(np.abs(raw))) if len(raw) else None,
            "median_abs_storm_shift_km": float(np.median(np.abs(shift))) if len(shift) else None,
        }

    supported = swarm[swarm.b_source.eq("history") & np.isfinite(swarm.in_track_km) & np.isfinite(swarm.storm_shift_km)]
    high_status = [
        {"scope": scope, "population": name, "window": window, "lead_h": lead, **cell["storm_term"]}
        for scope, name, window, group in groups(results)
        if (scope == "by_band" and name == high_band) or (scope == "by_mission" and name in {"jason-3", "sentinel-6a"})
        for lead, cell in group["by_lead_h"].items()
    ]
    return {
        "selection": {
            "above_altitude_km": 600,
            "early_lead_h": 6,
            "day_lead_h": 24,
            "swarm_long_lead_h": 168,
            "storm_windows": storm_windows,
            "above_bands": above,
            "low_band": low_band,
            "high_band": high_band,
            "supported_coefficient_source": "history",
            "swarm_window": "storm",
            "control_window": "quiet",
        },
        "above_600_storm_day_in_track_2sigma": range_cells(24, above, storm_windows),
        "early_all_band_window_in_track_2sigma": range_cells(6, list(results["by_band"]), list(windows)),
        "swarm_may_long_lead": {"all_usable": storm_scope(swarm), "supported_history_only": storm_scope(supported)},
        "high_missions_quiet_day": {
            mission: results["by_mission"][mission]["quiet"]["by_lead_h"]["24"]["components"]
            for mission in ("jason-3", "sentinel-6a")
        },
        "low_band_quiet_day": results["by_band"][low_band]["quiet"]["by_lead_h"]["24"]["components"],
        "high_altitude_storm_term_status": high_status,
    }


def validate_summary_counts(trials: pd.DataFrame, results: dict) -> None:
    for scope, name, window, group in groups(results):
        field = "altitude_band" if scope == "by_band" else "mission"
        population = trials[trials[field].eq(name) & trials.window.eq(window)]
        for lead, entry in group["by_lead_h"].items():
            rows = population[population.lead_h.eq(float(lead))]
            usable = rows[~rows.gap & ~rows.manoeuvre & rows.sgp4_error.eq(0)]
            finite = usable[np.isfinite(usable.in_track_km)]
            expected = (
                len(rows),
                len(usable),
                len(finite),
                int(finite.in_track_km.abs().gt(group["definition"]["tolerance_km"]).sum()),
            )
            actual = tuple(entry[k] for k in ("n_total", "n_usable", "n", "exceedance_count"))
            if actual != expected:
                raise ValueError(f"Summary/trial mismatch at {scope}/{name}/{window}/{lead}: {actual} != {expected}")


def detector_diagnostics(summary: dict, old_trials: pd.DataFrame, trials: pd.DataFrame) -> dict:
    rows = []
    span_h = precise.MANOEUVRE_ARC_HOURS
    for mission, windows in summary["coverage"].items():
        for window, coverage in windows.items():
            check = coverage.get("orbit_detector_crosscheck") or {}
            if not check.get("reference_available"):
                continue
            definition = summary["windows"][window]
            start, end, truth_end = [
                pd.to_datetime(definition[key], utc=True) for key in ("sets_from", "sets_to", "truth_to")
            ]
            old = old_trials[old_trials.mission.eq(mission) & old_trials.window.eq(window)]
            new = trials[trials.mission.eq(mission) & trials.window.eq(window)]
            old_ok = ~old.gap & ~old.manoeuvre & old.sgp4_error.eq(0) & np.isfinite(old.in_track_km)
            new_ok_keys = set(
                map(
                    tuple,
                    new.loc[~new.gap & ~new.manoeuvre & new.sgp4_error.eq(0), ["set_epoch", "lead_h"]].itertuples(
                        index=False, name=None
                    ),
                )
            )
            left = pd.to_datetime(old.set_epoch, utc=True) - pd.Timedelta(hours=span_h)
            right = pd.to_datetime(old.set_epoch, utc=True) + pd.to_timedelta(old.lead_h, unit="h")
            for burn_start, burn_end in check.get("misses") or []:
                a, b = pd.to_datetime(burn_start, utc=True), pd.to_datetime(burn_end, utc=True)
                if b < start - pd.Timedelta(hours=span_h) or a > truth_end:
                    scope = "outside scored comparison/exclusion span"
                elif a < start:
                    scope = "pre-epoch exclusion span"
                elif a < end:
                    scope = "trial epoch-selection span"
                else:
                    scope = "propagation extension"
                overlap = (left <= b) & (right >= a)
                affected = old.loc[overlap & old_ok, ["set_epoch", "lead_h"]]
                newly_excluded = sum(
                    tuple(pair) not in new_ok_keys for pair in affected.itertuples(index=False, name=None)
                )
                rows.append(
                    {
                        "mission": mission,
                        "window": window,
                        "burn_from": burn_start,
                        "burn_to": burn_end,
                        "scope": scope,
                        "raw_trial_arc_overlaps": int(overlap.sum()),
                        "old_usable_arc_overlaps": len(affected),
                        "newly_excluded_arc_overlaps": newly_excluded,
                        "source": (coverage.get("manoeuvre_record_provenance") or {}).get("source_id"),
                        "detector_edge_caveat": "Orbit averaging and differencing require surrounding states; loaded-product padding is not an equally supported detection interval",
                    }
                )
    return {
        "missed_published_intervals": rows,
        "scope_counts": {
            scope: sum(row["scope"] == scope for row in rows) for scope in sorted({row["scope"] for row in rows})
        },
        "interpretation": "Unmatched published intervals over loaded record products, not a count of newly missed in-window burns; interval effects can overlap and must not be summed as unique trials",
    }


def build(args) -> dict:
    summary_file, trial_file = ROOT / args.summary, ROOT / args.trials
    archived_summary = ROOT / "data/validation/v1/reference_benchmark.json"
    archived_trials = ROOT / "data/validation/v1/reference_benchmark.parquet"
    raw = read_json(summary_file)
    summary = raw["summary"]
    trials = pd.read_parquet(trial_file)
    failed = summary.get("execution", {}).get("failed_mission_windows", [])
    if failed:
        raise ValueError(f"Refusing to publish an incomplete run: {failed}")
    current = summary["results"]
    for scope, name, window, group in groups(current):
        if "definition" not in group or "components" not in next(iter(group["by_lead_h"].values())):
            raise ValueError("Corrected results must be re-summarised with benchmark_statistics before rendering")
        if scope == "by_band" and "sensitivities" not in group:
            raise ValueError(f"Missing deletion sensitivities: {name}/{window}")
        if scope == "by_band" and "component_coverage" not in group["sensitivities"]:
            raise ValueError(f"Missing component coverage sensitivities: {name}/{window}")
    validate_summary_counts(trials, current)
    definition = next(iter(next(iter(current["by_band"].values())).values()))["definition"]
    old_trials = pd.read_parquet(archived_trials)
    old_raw = read_json(archived_summary)["summary"]
    old = statistics.summarise_trials(
        old_trials,
        leads_hours=definition["leads_hours"],
        tolerance_km=definition["tolerance_km"],
        quantile=definition["quantile"],
        include_sensitivities=False,
    )
    usable = trials[~trials.gap & ~trials.manoeuvre & trials.sgp4_error.eq(0) & np.isfinite(trials.in_track_km)]
    set_keys = ["mission", "window", "set_epoch"]
    population = {
        "missions": sorted(trials.mission.unique()),
        "n_missions": int(trials.mission.nunique()),
        "n_windows": int(trials.window.nunique()),
        "n_bands": int(trials.altitude_band.nunique()),
        "n_raw_sets": len(trials[set_keys].drop_duplicates()),
        "n_usable_sets_any_lead": len(usable[set_keys].drop_duplicates()),
        "n_raw_pairs": len(trials),
        "n_usable_pairs": len(usable),
        "minimum_altitude_km": float(trials.altitude_km.min()),
        "maximum_altitude_km": float(trials.altitude_km.max()),
    }
    sources = [provenance(p) for p in [summary_file, trial_file, archived_summary, archived_trials]]
    source_code = [
        ROOT / "src/driftwatch/storm/benchmark_statistics.py",
        ROOT / "src/driftwatch/storm/reference_run.py",
        ROOT / "src/driftwatch/storm/precise.py",
        ROOT / "src/driftwatch/screening/ric.py",
        ROOT / "scripts/correct_covariance_basis.py",
        ROOT / "src/driftwatch/storm/manoeuvre_records.py",
        Path(__file__),
    ]
    protocols = {}
    for name in ("locked_protocol", "classifier_protocol", "protocol_audit"):
        path = ROOT / getattr(args, name)
        protocols[name] = {"input": provenance(path), "result": read_json(path)}
    freeze_audit = protocols["protocol_audit"]["result"]
    if freeze_audit["status"] != "passed":
        raise ValueError("Frozen scientific protocol audit did not pass")
    if freeze_audit["protocol_sha256"] != protocols["locked_protocol"]["input"]["sha256"]:
        raise ValueError("Frozen protocol audit identifies different scientific protocol bytes")
    classifier = protocols["classifier_protocol"]["result"]
    for field, expected in (
        ("fraction_pre_max", precise.POST_BURN_FRACTION_PRE),
        ("fraction_post_min", precise.POST_BURN_FRACTION_POST),
        ("resolve_sigmas_min", precise.POST_BURN_RESOLVE_SIGMAS),
    ):
        if classifier[field] != expected:
            raise ValueError(f"Frozen classifier differs from executed configuration: {field}")
    extras = {}
    for name in ("dsgp4", "dsgp4_paired", "dsgp4_audit", "radio", "radio_tracks", "locked"):
        filename = getattr(args, name)
        if filename:
            path = ROOT / filename
            if name == "locked" and not (path.parent / "completion-manifest.json").is_file():
                raise ValueError("A final locked completion manifest is required before reading experiment results")
            extras[name] = {"status": "supplied", "input": provenance(path), "result": read_evidence(path)}
        else:
            extras[name] = {
                "status": "pending",
                "reason": "Required author attestation has not been supplied; no locked-experiment result is reported"
                if name == "locked"
                else "No revised result supplied to this publication build",
            }
    if extras["dsgp4"]["status"] == "supplied":
        extras["dsgp4"]["reported_quantile"] = {"probability": 0.95, "method": "linear"}
        extras["dsgp4"]["objective_definition"] = (
            "The fixed training objective is the mean squared error of normalised TEME position and velocity "
            "over the fixed eligible training targets. It is dimensionless, rather than an error measured in kilometres."
        )
        if extras["dsgp4_paired"]["status"] != "supplied":
            raise ValueError("A revised ML result requires --dsgp4-pairs with its paired-comparison CSV")
        for model, fit in extras["dsgp4"]["result"]["training"].items():
            if not fit.get("checkpoint_sha256") or not fit.get("sample_sha256"):
                raise ValueError(f"ML fit {model} lacks checkpoint/sample hashes")
            if not np.isclose(fit["selected_loss"], fit["checkpoint_reloaded_loss"], rtol=1e-12, atol=0):
                raise ValueError(f"ML fit {model} reload objective differs from selection")
        if extras["dsgp4_audit"]["status"] == "supplied" and extras["dsgp4_audit"]["result"]["status"] != "passed":
            raise ValueError("ML independent correction audit did not pass")
    if extras["radio_tracks"]["status"] == "supplied":
        extras["radio_tracks"]["reported_quantile"] = {"probability": 0.95, "method": "linear"}
        directory = (ROOT / args.radio_tracks).parent
        for name in ("protocol", "progress", "diagnostics"):
            path = directory / f"radio_track_{name}.json"
            extras[f"radio_tracks_{name}"] = {
                "status": "supplied",
                "input": provenance(path),
                "result": read_json(path),
            }
        progress = extras["radio_tracks_progress"]["result"]
        if progress["status"] != "complete" or progress["completed_trials"] != progress["total_trials"]:
            raise ValueError("Radio track summary lacks a complete execution inventory")
        diagnostics = extras["radio_tracks_diagnostics"]["result"]
        for name in ("n_input_trials", "n_eligible_trials"):
            if diagnostics[name] != extras["radio_tracks"]["result"][name]:
                raise ValueError(f"Radio diagnostic inventory mismatch: {name}")
        if not diagnostics["all_curve_hashes_verified"]:
            raise ValueError("Radio curve hash audit is incomplete")
    if extras["locked"]["status"] == "supplied":
        locked_evidence = locked_completion_evidence(
            ROOT / args.locked, extras["locked"]["result"], protocols["locked_protocol"]
        )
        extras.update({f"locked_{name}": value for name, value in locked_evidence.items()})
        extras["locked"]["publication_diagnostics"] = locked_publication_diagnostics(extras["locked"]["result"])
        audit_path = ROOT / args.locked_audit
        audit = read_json(audit_path)
        if not audit["passed"] or audit["issues"]:
            raise ValueError("Locked independent audit did not pass")
        if audit["protocol_sha256"] != protocols["locked_protocol"]["input"]["sha256"]:
            raise ValueError("Locked independent audit identifies another protocol")
        if audit["completion_manifest_sha256"] != extras["locked_completion"]["input"]["sha256"]:
            raise ValueError("Locked independent audit identifies another completion manifest")
        if audit["verified_aggregate_files"] != extras["locked_completion"]["result"]["files"]:
            raise ValueError("Locked independent audit identifies different aggregate output bytes")
        extras["locked_audit"] = {"status": "supplied", "input": provenance(audit_path), "result": audit}
        provenance_path = ROOT / args.locked_provenance_audit
        provenance_audit = read_json(provenance_path)
        if (
            provenance_audit["status"] != "pass"
            or provenance_audit["bindings"]["protocol_sha256"] != audit["protocol_sha256"]
        ):
            raise ValueError("Locked provenance audit failed or identifies another protocol")
        if provenance_audit["first_data_access_sha256"] != extras["locked_access"]["input"]["sha256"]:
            raise ValueError("Locked provenance audit identifies another first-access marker")
        extras["locked_provenance_audit"] = {
            "status": "supplied",
            "input": provenance(provenance_path),
            "result": provenance_audit,
        }
    elif args.locked_access:
        locked_evidence = locked_access_evidence(ROOT / args.locked_access, protocols["locked_protocol"])
        extras.update({f"locked_{name}": value for name, value in locked_evidence.items()})
        extras["locked"]["reason"] = (
            "Author attestation is recorded and execution has begun; no completed result is supplied"
        )
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    basis_path = ROOT / "data/validation/covariance-basis-correction-2026-09-08/correction.json"
    basis_correction = read_json(basis_path)
    if current["by_band"] != basis_correction["reference"]["results"]["by_band"]:
        raise ValueError("Reference results differ from the covariance-basis amendment")
    sources.append(provenance(basis_path))
    if extras["locked"]["status"] == "supplied":
        if (
            extras["locked"]["result"]["secondary"]["by_band"].keys()
            != basis_correction["september"]["results"]["by_band"].keys()
        ):
            raise ValueError("September amendment population differs")
        # The frozen completion and audits above bind the original bytes. Only
        # this explicitly labelled publication view receives the later amendment.
        extras["locked"]["result"]["secondary"] = basis_correction["september"]["results"]
        extras["locked"]["secondary_amendment"] = provenance(basis_path)
    archive_display = ROOT / "docs/archive/paper-2026-09-v1.md"
    archive_original = ROOT / "docs/archive/paper-2026-09-v1.original.md"
    archive_body = (archive_original if archive_original.exists() else archive_display).read_bytes()
    tagged_body = subprocess.check_output(["git", "show", "paper-2026-09-v1:docs/paper.md"], cwd=ROOT)
    data = {
        "schema_version": "benchmark-publication-v2",
        "built_at": datetime.now(UTC).isoformat(),
        "benchmark_built_at": raw["built_at"],
        "revision": revision,
        "inputs": sources,
        "source_code": [provenance(p) for p in source_code],
        "bibliography": bibliography(),
        "protocols": protocols,
        "archive": {
            "tag": "paper-2026-09-v1",
            "tag_paper_sha256": hashlib.sha256(tagged_body).hexdigest(),
            "display_paper": archive_display.relative_to(ROOT).as_posix(),
            "preserved_local_body": archive_original.relative_to(ROOT).as_posix(),
            "preserved_local_body_sha256": hashlib.sha256(archive_body).hexdigest(),
            "local_body_matches_tag": archive_body == tagged_body,
        },
        "definition": {
            **definition,
            "propagator": "SGP4",
            "covariance_multiples": [1, 2],
            "pre_epoch_manoeuvre_arc_h": precise.MANOEUVRE_ARC_HOURS,
            "post_burn_fraction_pre": precise.POST_BURN_FRACTION_PRE,
            "post_burn_fraction_post": precise.POST_BURN_FRACTION_POST,
            "post_burn_resolve_scatters": precise.POST_BURN_RESOLVE_SIGMAS,
            "post_burn_display_classes": {
                "pre-burn re-epoched": "pre-manoeuvre-energy compatible",
                "post-burn": "post-manoeuvre-energy compatible",
                "mixed": "intermediate energy fraction",
                "unresolved": "unresolved",
            },
        },
        "population": population,
        "missions": summary["missions"],
        "windows": summary["windows"],
        "coverage": summary["coverage"],
        "not_covered": summary.get("not_covered", {}),
        "execution": summary.get("execution", {}),
        "reference_checks": {
            "sgp4_vs_slr_by_band": summary.get("sgp4_vs_slr", {}),
            "sgp4_vs_slr_by_mission": summary.get("sgp4_vs_slr_by_mission", {}),
            "interpretation": "Range-only checks on sampled passes; pooled normal points are correlated, and these legacy range quantiles use linear interpolation",
        },
        "results": current,
        "corrections": correction_data(old, current, old_raw["results"], old_trials, trials),
        "covariance_basis_correction": basis_correction,
        "discrepancy_diagnostics": discrepancy_diagnostics(trials, current, summary["windows"]),
        "detector_diagnostics": detector_diagnostics(summary, old_trials, trials),
        "extras": extras,
        "assurance_cases": [
            {
                "boundary": "Reference frame",
                "observed_fault": "The frame declared by the product filename was misread, producing a comparison in the wrong frame.",
                "check": "Compare independently interpreted published states in their declared frame.",
            },
            {
                "boundary": "Time system",
                "observed_fault": "GPS timestamps were treated as UTC, shifting the comparison epoch.",
                "check": "Convert declared source time scales and compare against independently timed observations.",
            },
            {
                "boundary": "Fit input provenance",
                "observed_fault": "The covariance fit used inputs from the wrong year despite the intended interval in the request.",
                "check": "Check the actual rows fitted against the requested object and time interval.",
            },
            {
                "boundary": "Station reference point",
                "observed_fault": "The ground-marker position was used in place of the telescope reference point.",
                "check": "Apply published station eccentricities and inspect residuals by station.",
            },
            {
                "boundary": "Velocity convention",
                "observed_fault": "Finite-difference chord velocity was interpreted as a physical force or orbital-energy discrepancy.",
                "check": "Compare the derivative against a known-velocity orbit and clean reference arcs.",
            },
            {
                "boundary": "Test completion",
                "observed_fault": "A Fortran STOP returned a successful process status while terminating the test run early.",
                "check": "Compare completed tests with independently collected test inventory.",
            },
        ],
    }
    return publication_text.enrich(data, trials)


def num(value, digits=2) -> str:
    return "—" if value is None else f"{value:,.{digits}f}"


def pct(value) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def significant(value) -> str:
    return "—" if value is None else f"{value:.6g}"


def horizon_text(h: dict) -> str:
    last, fail, status = endpoint(h)
    if status == "coverage_censored":
        return f"{num(last, 0)} h last pass; unavailable at {num(h.get('stopped_at_lead_h'), 0)} h"
    if fail is not None:
        return f"{num(last, 0)} h pass / {num(fail, 0)} h fail" if last is not None else f"fails at {num(fail, 0)} h"
    if status is None:
        return f"{num(last, 0)} h last pass; legacy censoring unspecified"
    return f"passes through the longest tested lead ({num(last, 0)} h)" if last is not None else "unavailable"


def table(headers, rows) -> str:
    def cell(value):
        return str(value).replace("|", "/").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def composition(c: dict, names: dict) -> str:
    return "; ".join(f"{names.get(m, m)}: {n}" for m, n in c.items()) or "none"


def sensitivity_text(group: dict) -> tuple[str, str]:
    sensitivity = group.get("sensitivities")
    if not sensitivity:
        return "not applicable", "not computed"
    spacecraft = sensitivity["leave_one_spacecraft_out"]
    outcomes = sorted({horizon_text(v["empirical_coverage"]) for v in spacecraft.values()})
    sets = sensitivity["leave_one_set_out"]
    return "; ".join(outcomes), f"{sets['n_changed']}/{sets['n_deletions']} deletions change a reported criterion"


def coverage_deletion_text(group: dict, lead: str, component: str, names: dict) -> tuple[str, str]:
    cell = (
        group.get("sensitivities", {}).get("component_coverage", {}).get("by_lead_h", {}).get(lead, {}).get(component)
    )
    if cell is None:
        return "not computed for mission-only cells", "not computed for mission-only cells"
    missions = "; ".join(
        f"omit {names.get(mission, mission)}: {value['inside_2_sigma_count']}/{value['n']} ({pct(value['inside_2_sigma_fraction'])})"
        for mission, value in cell["leave_one_spacecraft_out"].items()
    )
    sets = cell["leave_one_set_out"]
    deletion = (
        f"{pct(sets['min_fraction'])}–{pct(sets['max_fraction'])}; n {sets['min_n']}–{sets['max_n']}; "
        f"{sets['n_fraction_changed']}/{sets['n_deletions']} fraction changes; {sets['n_undefined']} undefined"
    )
    return missions, deletion


def endpoint_exceedance(group: dict, key: str) -> str:
    lead = group["horizon"][key]
    if lead is None:
        if key == "first_lead_h_beyond" and group["horizon"]["termination"] == "coverage_censored":
            lead = group["horizon"]["stopped_at_lead_h"]
        else:
            return "no measured endpoint"
    cell = group["by_lead_h"][f"{lead:g}"]
    if cell["n"] == 0:
        return f"{lead:g} h: n=0; 0/0; fraction unavailable (coverage censored)"
    return f"{lead:g} h: {cell['exceedance_count']}/{cell['n']} ({pct(cell['exceedance_fraction'])})"


def headline_table(data: dict) -> str:
    rows = []
    endpoints = []
    names = {key: value["name"] for key, value in data["missions"].items()}
    for band, windows in sorted(data["results"]["by_band"].items(), key=lambda item: int(item[0].split("-")[0])):
        for window in data["windows"]:
            if window not in windows:
                continue
            group = windows[window]
            loo, los = sensitivity_text(group)
            horizon = group["horizon"]
            rows.append([band, window, horizon_text(horizon), loo, los])
            selected = [
                ("last pass", horizon["last_lead_h_within"]),
                ("first fail", horizon["first_lead_h_beyond"]),
            ]
            if horizon["termination"] == "coverage_censored":
                selected.append(("coverage censored", horizon["stopped_at_lead_h"]))
            for label, lead in selected:
                if lead is None:
                    continue
                cell = group["by_lead_h"][f"{lead:g}"]
                endpoints.append(
                    [
                        band,
                        window,
                        label,
                        f"{lead:g}",
                        cell["n"],
                        f"{cell['exceedance_count']}/{cell['n']}",
                        pct(cell["exceedance_fraction"]) if cell["n"] else "unavailable",
                        composition(cell["mission_counts"], names),
                    ]
                )
    return "\n\n".join(
        [
            table(["Band", "Window", "Primary observed endpoints", "Remove one spacecraft", "Remove one set"], rows),
            "Endpoint evidence uses the usable population at the indicated lead. An unavailable fraction at n=0 "
            "is a coverage limit, not an observed failure. For a row that passes through the longest tested lead, "
            "the last-pass evidence refers to that lead; there is no observed failing endpoint.",
            table(
                [
                    "Band",
                    "Window",
                    "Endpoint",
                    "Lead h",
                    "Usable n",
                    "Exceedances / n",
                    "Exceedance share",
                    "Usable spacecraft composition",
                ],
                endpoints,
            ),
        ]
    )


def detailed_tables(data: dict, *, secondary_only: bool = False) -> str:
    names = {k: v["name"] for k, v in data["missions"].items()}
    text = [
        "# Reference benchmark: complete tables",
        "",
        "Generated from [benchmark-v2.json](assets/benchmark-v2.json). Each count refers to the stated mission/window/lead. "
        "Passing and failing endpoints, deletion sensitivities and tested limits are descriptive; none is a confidence interval.",
        "",
        "## Horizons and deletion sensitivity",
        "",
        headline_table(data),
        "",
        "## Every band, window and planned lead",
        "",
    ]
    rows = []
    for band, windows in data["results"]["by_band"].items():
        for window, group in windows.items():
            for lead, e in group["by_lead_h"].items():
                component = e["components"]["in_track"]
                rows.append(
                    [
                        band,
                        window,
                        lead,
                        e["n_total"],
                        e["n"],
                        e["exceedance_count"],
                        pct(e["exceedance_fraction"]),
                        num(component["median_abs_km"]),
                        num(component["quantile_abs_km"]["linear"]),
                        num(component["quantile_abs_km"]["inverted_cdf"]),
                        composition(e["mission_counts"], names),
                        group["horizon"]["termination"],
                    ]
                )
    text += [
        table(
            [
                "Band",
                "Window",
                "Lead h",
                "All pairs",
                "Usable n",
                "Exceedances",
                "Exceedance share",
                "Median km",
                "Linear quantile km",
                "Inverted-CDF quantile km",
                "Mission composition",
                "Horizon termination",
            ],
            rows,
        ),
        "",
        "## Mission horizons and censoring",
        "",
    ]
    rows = []
    for mission, windows in data["results"]["by_mission"].items():
        for window, group in windows.items():
            rows.append(
                [
                    names[mission],
                    window,
                    horizon_text(group["horizon"]),
                    horizon_text(group["horizons_by_criterion"]["linear_quantile"]),
                    endpoint_exceedance(group, "last_lead_h_within"),
                    endpoint_exceedance(group, "first_lead_h_beyond"),
                    "; ".join(f"{k} h: {v['n']}" for k, v in group["by_lead_h"].items()),
                ]
            )
    text += [
        table(
            [
                "Mission",
                "Window",
                "Primary empirical-coverage endpoints",
                "Linear-quantile endpoints",
                "Last pass exceedances",
                "First fail exceedances",
                "n at every planned lead",
            ],
            rows,
        ),
        "",
        "## Component residuals and covariance coverage",
        "",
    ]
    rows = []
    for scope, name, window, group in groups(data["results"]):
        # Include all missions, so the high-altitude pair is separately inspectable.
        for lead, entry in group["by_lead_h"].items():
            for component, cell in entry["components"].items():
                c = cell["coverage"]
                loo, los = coverage_deletion_text(group, lead, component, names)
                rows.append(
                    [
                        scope,
                        names.get(name, name),
                        window,
                        lead,
                        component,
                        c["n"],
                        num(cell["median_abs_km"]),
                        num(c["median_sigma_km"]),
                        f"{c['inside_1_sigma_count']}/{c['n']} ({pct(c['inside_1_sigma_fraction'])})",
                        f"{c['inside_2_sigma_count']}/{c['n']} ({pct(c['inside_2_sigma_fraction'])})",
                        c["n_invalid_pairs"],
                        composition(c["mission_counts"], names),
                        loo,
                        los,
                    ]
                )
    text += [
        table(
            [
                "Scope",
                "Population",
                "Window",
                "Lead h",
                "Component",
                "n",
                "Median error km",
                "Median sigma km",
                "Inside one sigma",
                "Inside two sigma",
                "Invalid pairs",
                "Valid pair mission composition",
                "Two-sigma coverage, remove one spacecraft",
                "Two-sigma coverage, remove one whole set (descriptive range)",
            ],
            rows,
        ),
        "",
    ]
    if secondary_only:
        return "\n".join(text)
    text += ["## Published records and detector checks", ""]
    rows = []
    for mission, windows in data["coverage"].items():
        for window, coverage in windows.items():
            record = coverage.get("manoeuvre_record_provenance")
            check = coverage.get("orbit_detector_crosscheck") or {}
            rows.append(
                [
                    names.get(mission, mission),
                    window,
                    "detection" if record is None else record.get("source_id", record.get("source", "record")),
                    "not integrated" if record is None else record.get("coverage_status", "published record"),
                    "not available"
                    if coverage.get("manoeuvres_recorded") is None
                    else coverage.get("manoeuvres_recorded_count", len(coverage["manoeuvres_recorded"])),
                    json.dumps(check, ensure_ascii=False),
                ]
            )
    text += [
        table(["Mission", "Window", "Authority", "Coverage", "Published intervals", "Orbit detector comparison"], rows),
        "",
        "### Unmatched published intervals: time scope and mask effect",
        "",
        data.get("detector_diagnostics", {}).get(
            "interpretation", "No detector comparison was supplied for this population."
        ),
        "",
        "The orbit detector needs surrounding states for averaging and differencing. Records in loaded-product padding "
        "or near its edges do not establish the same detection opportunity as an interior event.",
        "",
        table(
            [
                "Mission",
                "Window",
                "Burn start UTC",
                "Burn end UTC",
                "Time scope",
                "All raw arcs overlapping",
                "Old usable arcs overlapping",
                "Newly excluded arcs overlapping",
            ],
            [
                [
                    names.get(row["mission"], row["mission"]),
                    row["window"],
                    row["burn_from"],
                    row["burn_to"],
                    row["scope"],
                    row["raw_trial_arc_overlaps"],
                    row["old_usable_arc_overlaps"],
                    row["newly_excluded_arc_overlaps"],
                ]
                for row in data.get("detector_diagnostics", {}).get("missed_published_intervals", [])
            ],
        ),
        "",
        "### Published record source manifests",
        "",
    ]
    source_rows = {}
    for windows in data["coverage"].values():
        for coverage in windows.values():
            record = coverage.get("manoeuvre_record_provenance") or {}
            for source in record.get("sources", record.get("provenance", [])):
                source_rows[json.dumps(source, sort_keys=True)] = source
    text += [
        table(
            ["Source", "URL", "Retrieved UTC", "Declared time system", "SHA-256"],
            [
                [
                    source.get("source", source.get("source_id", "published record")),
                    source.get("url"),
                    source.get("retrieved_at"),
                    source.get("time_system", source.get("source_time_system")),
                    source.get("sha256"),
                ]
                for source in source_rows.values()
            ],
        ),
        "",
        "## Post-manoeuvre energy measurements",
        "",
        "Delay from burn end is recomputed from the stored UTC interval and element-set epoch. The original stored delay "
        "is retained separately because older summaries measured it from the interval midpoint. Neither is a publication delay. "
        "The displayed energy classes do not identify unobserved catalogue processing.",
        "",
    ]
    rows = []
    post = data["results"].get("post_burn", {})
    labels = data["definition"]["post_burn_display_classes"]
    for burn in post.get("burns", []):
        for fitted in burn["sets_after"]:
            epoch = pd.to_datetime(fitted["epoch"], utc=True)
            end = pd.to_datetime(burn["burn_to"], utc=True)
            comparisons = []
            for lead, observed in fitted.get("in_track_signed_km", {}).items():
                predicted = fitted.get("predicted_in_track_km", {}).get(lead)
                comparisons.append(f"{lead} h: {num(observed)} / {num(predicted)}")
            rows.append(
                [
                    names[burn["mission"]],
                    burn["window"],
                    burn["burn_from"],
                    burn["burn_to"],
                    fitted["epoch"],
                    num((epoch - end).total_seconds() / 3600),
                    num(fitted.get("delay_h")),
                    num(burn.get("delta_a_m")),
                    num(burn.get("sigma_m")),
                    num(fitted.get("a_error_m")),
                    num(fitted.get("fraction"), 3),
                    labels.get(fitted.get("class"), fitted.get("class") or "unavailable"),
                    "; ".join(comparisons),
                ]
            )
    text += [
        table(
            [
                "Mission",
                "Window",
                "Burn start UTC",
                "Burn end UTC",
                "Set epoch UTC",
                "Delay from end h",
                "Stored delay h",
                "Burn delta-a m",
                "Clean scatter m",
                "Calibrated semi-major-axis error m",
                "Burn fraction",
                "Energy compatibility",
                "Observed / predicted in-track km",
            ],
            rows,
        ),
        "",
        "## Changed horizon figures",
        "",
    ]
    rows = []
    for change in data["corrections"]["horizons"]:
        if not (
            change["source_or_residual_change"] or change["criterion_change"] or change["published_endpoint_change"]
        ):
            continue
        rows.append(
            [
                change["scope"],
                names.get(change["name"], change["name"]),
                change["window"],
                horizon_text(change["published_v1"]),
                horizon_text(change["v1_recomputed_linear"]),
                horizon_text(change["corrected_linear"]),
                horizon_text(change["corrected_primary"]),
                "; ".join(
                    f"{k} h: {change['old_n_by_lead'].get(k, 0)} → {v}" for k, v in change["new_n_by_lead"].items()
                ),
            ]
        )
    text += [
        table(
            [
                "Scope",
                "Population",
                "Window",
                "Published v1",
                "V1 re-scored linear",
                "Corrected linear",
                "Corrected primary",
                "Old → new n",
            ],
            rows,
        ),
        "",
        "## Every changed component statistic",
        "",
        "The full precision values and all changed fields are also in [the correction CSV](assets/benchmark-v2-component-corrections.csv).",
        "",
    ]
    rows = []
    for change in data["corrections"]["components"]:
        a, b = change["old"]["coverage"], change["new"]["coverage"]
        rows.append(
            [
                change["scope"],
                names.get(change["name"], change["name"]),
                change["window"],
                num(change["lead_h"], 0),
                change["component"],
                f"{a['n']} → {b['n']}",
                f"{pct(a['inside_1_sigma_fraction'])} → {pct(b['inside_1_sigma_fraction'])}",
                f"{pct(a['inside_2_sigma_fraction'])} → {pct(b['inside_2_sigma_fraction'])}",
                "; ".join(change["changed_fields"]),
            ]
        )
    text += [
        table(
            [
                "Scope",
                "Population",
                "Window",
                "Lead h",
                "Component",
                "Old → new n",
                "One-sigma coverage",
                "Two-sigma coverage",
                "Changed fields",
            ],
            rows,
        ),
        "",
    ]
    text += [
        "## Sampled laser-ranging checks",
        "",
        data["reference_checks"]["interpretation"],
        "",
        "Orbit-reference range residuals are in metres; propagated element-set range residuals below are in kilometres. "
        "Station and normal-point counts are not counts of independent orbital errors.",
        "",
    ]
    rows = []
    for mission, windows in data["coverage"].items():
        for window, coverage in windows.items():
            c = coverage.get("orbit_vs_slr") or {}
            rows.append(
                [
                    names.get(mission, mission),
                    window,
                    c.get("n", 0),
                    c.get("n_stations", 0),
                    num(c.get("median_abs_m")),
                    num(c.get("rms_m")),
                    num(c.get("p95_abs_m")),
                    json.dumps(c.get("dropped", {}), sort_keys=True),
                ]
            )
    text += [
        table(
            [
                "Mission",
                "Window",
                "Normal points",
                "Stations",
                "Median absolute m",
                "RMS m",
                "Linear p95 m",
                "Dropped observations",
            ],
            rows,
        ),
        "",
    ]
    rows = []
    for mission, windows in data["reference_checks"]["sgp4_vs_slr_by_mission"].items():
        for window, group in windows.items():
            for lead, c in group.items():
                if not isinstance(c, dict) or "n" not in c:
                    continue
                rows.append(
                    [
                        names.get(mission, mission),
                        window,
                        lead,
                        c["n"],
                        c["n_sets"],
                        group.get("n_stations"),
                        num(c.get("median_km")),
                        num(c.get("p95_km")),
                    ]
                )
    text += [
        table(
            [
                "Mission",
                "Window",
                "Lead h bin",
                "Normal-point comparisons",
                "Sets",
                "Stations in window",
                "Median absolute km",
                "Linear p95 km",
            ],
            rows,
        ),
        "",
    ]
    if data["extras"]["dsgp4"]["status"] == "supplied":
        text += ["## Revised learned-propagator evaluation", "", ml_sections(data, detailed=True), ""]
    if data["extras"]["locked"]["status"] == "supplied":
        text += ["## Locked calendar-month replay", "", locked_sections(data, detailed=True), ""]
    return "\n".join(text)


def ml_sections(data: dict, *, detailed: bool = False) -> str:
    result = data["extras"]["dsgp4"]["result"]
    paired = data["extras"]["dsgp4_paired"]["result"]["rows"]
    config = result["protocol"]["configuration"]
    evaluated = [
        row
        for row in paired
        if row["scope"] == "pooled"
        and row["method"] in result["training"]
        and row["window"] in result["held_out_windows"]
    ]
    improved_median = sum(row["median_improvement"] is not None and row["median_improvement"] > 0 for row in evaluated)
    improved_tail = sum(row["method_p95_abs_in_track_km"] < row["plain_p95_abs_in_track_km"] for row in evaluated)
    text = [
        f"The tested local hybrids lower the paired pooled median in {improved_median}/{len(evaluated)} "
        f"model/window/lead evaluation cells and lower the interpolated tail in {improved_tail}/{len(evaluated)}. "
        "These cells share spacecraft and storm windows and are not independent experiments.",
        "",
        f"Upstream method: {cite(data, 'dsgp4')}; implementation: {cite(data, 'dsgp4_code')}.",
        "",
        "This is a local adaptation with its own reference population, recipe and training-objective checkpoint "
        f"selection; it is not a reproduction of the published experiment. Published design: {cite(data, 'dsgp4_manuscript')}.",
        "",
        f"The revised learned-propagator evaluation trains on {', '.join(data['publication']['windows'][w] for w in result['training_windows'])}, using the "
        "same published-record exclusion authority as evaluation at each hourly target. The selected checkpoint "
        "minimises the objective evaluated over the same complete training sample after each epoch, including the "
        "initial model; the saved checkpoint is reloaded and its objective checked. The changing-model minibatch "
        "average is retained only as an optimisation trace. Exclusion counts below may overlap.",
        "",
        data["extras"]["dsgp4"]["objective_definition"],
        "",
        f"Frozen recipe: `{json.dumps(config, sort_keys=True)}`.",
        "",
    ]
    training_rows = []
    for model, fit in result["training"].items():
        training_rows.append(
            [
                model,
                f"{fit['n_samples']}/{fit['candidate_targets']}",
                fit["n_sets"],
                fit["excluded_burn_targets"],
                fit["excluded_truth_targets"],
                fit["excluded_sgp4_error_targets"],
                fit.get("excluded_nonfinite_targets"),
                fit["selected_epoch"],
                significant(fit["initial_loss"]),
                significant(fit["selected_loss"]),
                significant(fit["checkpoint_reloaded_loss"]),
                fit["checkpoint_sha256"],
                fit["sample_sha256"],
            ]
        )
    text += [
        table(
            [
                "Model",
                "Eligible / candidate targets",
                "Sets",
                "Burn-excluded targets",
                "Truth gaps",
                "SGP4 failures",
                "Nonfinite states",
                "Selected epoch",
                "Initial fixed objective",
                "Selected fixed objective",
                "Reloaded objective",
                "Checkpoint SHA-256",
                "Training-sample SHA-256",
            ],
            training_rows,
        ),
        "",
    ]
    text += [
        "Relative reduction is one minus the method median divided by the plain-propagator median; "
        "negative values therefore mean larger median error.",
        "",
    ]
    audit = data["extras"].get("dsgp4_audit", {})
    if audit.get("status") == "supplied":
        evidence = audit["result"]
        text += [
            f"Independent correction-audit status: {evidence['status']}. Its paired comparison inventory contains "
            f"{evidence['paired_cells_by_scope']['pooled']} pooled cells and "
            f"{evidence['paired_cells_by_scope']['spacecraft']} spacecraft cells. "
            f"The reported tails use the {pct(data['extras']['dsgp4']['reported_quantile']['probability'])} "
            "quantile with linear interpolation.",
            "",
        ]
    summary_rows = []
    for method in result["training"]:
        for window in result["held_out_windows"]:
            cells = [
                row
                for row in paired
                if row["scope"] == "pooled" and row["method"] == method and row["window"] == window
            ]
            changes = [row["median_improvement"] for row in cells if row["median_improvement"] is not None]
            tails_better = sum(row["method_p95_abs_in_track_km"] < row["plain_p95_abs_in_track_km"] for row in cells)
            spacecraft = [
                row
                for row in paired
                if row["scope"] == "spacecraft" and row["method"] == method and row["window"] == window
            ]
            median_better = [
                row for row in spacecraft if row["median_improvement"] is not None and row["median_improvement"] > 0
            ]
            spacecraft_tail_better = sum(
                row["method_p95_abs_in_track_km"] < row["plain_p95_abs_in_track_km"] for row in spacecraft
            )
            tradeoffs = sum(
                row["method_p95_abs_in_track_km"] > row["plain_p95_abs_in_track_km"] for row in median_better
            )
            summary_rows.append(
                [
                    method,
                    window,
                    len(cells),
                    sum(value > 0 for value in changes),
                    tails_better,
                    pct(float(np.median(changes))) if changes else "unavailable",
                    pct(min(changes)) if changes else "unavailable",
                    pct(max(changes)) if changes else "unavailable",
                    "; ".join(f"{row['lead_h']:g} h: {row['n_paired']}" for row in cells),
                    f"{len(median_better)}/{len(spacecraft)}",
                    f"{spacecraft_tail_better}/{len(spacecraft)}",
                    f"{tradeoffs}/{len(median_better)}",
                ]
            )
    text += [
        table(
            [
                "Model",
                "Evaluation window",
                "Paired lead cells",
                "Leads with lower paired median",
                "Leads with lower linear tail",
                "Median relative reduction across lead cells",
                "Worst change",
                "Best change",
                "Paired n at every lead",
                "Spacecraft/lead cells with lower median",
                "Spacecraft/lead cells with lower tail",
                "Median improves but tail worsens / median improvements",
            ],
            summary_rows,
        ),
        "",
        "The comparison unit is the same set/lead pair for each method and its plain-propagator baseline. "
        "Individual spacecraft can improve even when the pooled median worsens; some median improvements accompany "
        "larger tails. These windows were "
        "already examined before the methodological correction, so this rerun is exploratory and does not establish "
        "performance of learned propagation outside the stated model, population and frozen recipe.",
        "",
    ]
    rejected = [row["method"] for row in result["recommendations"] if not row["adopt"]]
    if rejected:
        text += [
            "The stored pooled adoption rule rejects these fitted checkpoints: "
            + "; ".join(rejected)
            + ". This conclusion concerns the reported recipe and checkpoints, not all learned propagators or every spacecraft.",
            "",
        ]
    example_keys = {("hy-2c", "august", 168.0), ("cryosat-2", "held-out", 168.0), ("sentinel-6a", "august", 24.0)}
    examples = [
        row
        for row in paired
        if row["scope"] == "spacecraft"
        and row["method"] == "ML-dSGP4 (all missions)"
        and (row["mission"], row["window"], row["lead_h"]) in example_keys
    ]
    if examples:
        text += [
            "Illustrative spacecraft cases, selected retrospectively to show the different median/tail outcomes:",
            "",
            table(
                [
                    "Mission",
                    "Window",
                    "Lead h",
                    "Paired n",
                    "Plain median km",
                    "Learned median km",
                    "Plain linear tail km",
                    "Learned linear tail km",
                ],
                [
                    [
                        row["mission"],
                        row["window"],
                        row["lead_h"],
                        row["n_paired"],
                        num(row["plain_median_abs_in_track_km"], 3),
                        num(row["method_median_abs_in_track_km"], 3),
                        num(row["plain_p95_abs_in_track_km"], 3),
                        num(row["method_p95_abs_in_track_km"], 3),
                    ]
                    for row in examples
                ],
            ),
            "",
        ]
    if detailed:
        text += [
            "### Paired comparisons at every lead",
            "",
            table(
                [
                    "Scope",
                    "Mission",
                    "Window",
                    "Lead h",
                    "Method",
                    "Paired n",
                    "Plain source n",
                    "Method source n",
                    "Missions",
                    "Plain median km",
                    "Method median km",
                    "Plain linear tail km",
                    "Method linear tail km",
                    "Relative reduction of paired median",
                    "Individual pairs improved",
                ],
                [
                    [
                        row["scope"],
                        row["mission"],
                        row["window"],
                        row["lead_h"],
                        row["method"],
                        row["n_paired"],
                        row["n_plain_source"],
                        row["n_method_source"],
                        row["n_missions"],
                        num(row["plain_median_abs_in_track_km"]),
                        num(row["method_median_abs_in_track_km"]),
                        num(row["plain_p95_abs_in_track_km"]),
                        num(row["method_p95_abs_in_track_km"]),
                        pct(row["median_improvement"]),
                        f"{row['trials_improved_count']}/{row['n_paired']} ({pct(row['trials_improved_fraction'])})",
                    ]
                    for row in paired
                ],
            ),
            "",
            "### Training objective traces",
            "",
        ]
        rows = []
        for model, fit in result["training"].items():
            rows.append([model, "initial", significant(fit["initial_loss"]), "not applicable"])
            for epoch, loss in enumerate(fit["losses"], 1):
                online = fit["online_losses"][epoch - 1] if epoch <= len(fit["online_losses"]) else None
                rows.append([model, epoch, significant(loss), significant(online)])
        text += [
            table(["Model", "Epoch", "Fixed-model complete-sample objective", "Changing-model minibatch trace"], rows),
            "",
        ]
    else:
        text.append(
            "All pooled and individual-spacecraft paired medians, tails, denominators and training traces are in [the complete tables](benchmark-v2-tables.md#revised-learned-propagator-evaluation)."
        )
    return "\n".join(text)


def locked_sections(data: dict, *, detailed: bool = False) -> str:
    result = data["extras"]["locked"]["result"]
    protocol, primary = result["protocol"], result["primary"]
    diagnostics = data["extras"]["locked"]["publication_diagnostics"]
    attestation = data["extras"]["locked_attestation"]
    statement = attestation["result"]
    attestation_link = Path(attestation["input"]["path"]).relative_to("docs").as_posix()
    protocol_link = Path(data["protocols"]["locked_protocol"]["input"]["path"]).relative_to("docs").as_posix()
    overlaps = diagnostics["plateau_overlaps"]
    plateau_prose = ""
    if overlaps:
        plateau_prose = (
            f"The fixed {protocol['plateau_hours']:g}-hour orbital-energy plateaus overlap other in-month recorded burns "
            f"for {len(overlaps)} event rows: "
            + "; ".join(
                f"{entry['event_id']} has earlier-plateau overlap with {', '.join(entry['pre_plateau_events']) or 'none'} "
                f"and later-plateau overlap with {', '.join(entry['post_plateau_events']) or 'none'}"
                for entry in overlaps
            )
            + ". The no-additional-burn subset still retains "
            + "; ".join(
                f"{entry['event_id']} ({entry['class']}, fraction {num(entry['fraction'], 3)})"
                for entry in overlaps
                if entry["retained_in_no_additional_burn_subset"]
            )
            + ". That subset excludes later burns, so it does not establish isolated pre-event plateaus. "
            "The mixed fraction here is not evidence of mixed catalogue fitting for an isolated burn; the frozen rows are retained."
        )
    groups_to_show = [
        ("All recorded burns", primary["all_recorded_burns"]),
        ("No intervening recorded burn", primary["without_intervening_recorded_burn"]),
        *((f"Spacecraft {name}", value) for name, value in primary["by_spacecraft"].items()),
        *((f"Omit spacecraft {name}", value) for name, value in primary["leave_one_spacecraft_out"].items()),
    ]
    if detailed:
        groups_to_show += [(f"Omit burn {name}", value) for name, value in primary["leave_one_burn_out"].items()]
    rows = [
        [
            label,
            f"{value['n_complete']}/{value['n_events']}",
            value["n_unavailable"],
            num(value.get("slope")),
            num(value.get("intercept_km")),
            num(value.get("slope_through_origin")),
            num(value.get("pearson_r")),
            num(value.get("spearman_rho")),
            num(value.get("mean_absolute_error_prediction_km")),
            num(value.get("mean_absolute_error_zero_km")),
            num(value.get("median_absolute_error_prediction_km")),
            num(value.get("median_signed_prediction_error_km")),
            f"{value.get('sign_agreement_count', 0)}/{value['n_complete']} ({pct(value.get('sign_agreement_fraction'))})",
            value.get("zero_predictor_or_endpoint_count", 0),
        ]
        for label, value in groups_to_show
    ]
    text = [
        f"The calendar replay uses epochs from {protocol['sets_from']} to {protocol['sets_to']}, with a "
        f"{protocol['primary_lead_hours']}-hour signed in-track endpoint after the first post-manoeuvre element-set "
        f"epoch. Its [scientific protocol]({protocol_link}) was frozen at {protocol['frozen_at']} "
        f"(SHA-256 `{result['protocol_sha256']}`). "
        f"The separately bound [author attestation]({attestation_link}) by {statement['author']} at "
        f"{statement['attested_at']} states “{statement['statement']}”. First experiment access was "
        f"{result['first_data_access']['started_at']}; execution completed at {result['completed_at']}. "
        "The frozen protocol's earlier pending-attestation status is historical; its bytes were preserved. "
        "Every published in-month burn remains in the event "
        "inventory, including unavailable endpoints and intervening manoeuvres. Energy calibration uses only prior "
        "clean sets. The zero-prediction error supplies an explicit baseline for the energy-based prediction. "
        "This is a retrospective physical diagnostic with a separately assessed endpoint, not an operational "
        "prediction available at element-set publication time. The attestation and local audit qualify prior "
        "exposure; September public-element/weather history and overlapping orbit products already existed.",
        "",
        "The [current execution-status note](protocols/september-2024-execution-status.md) links the preserved "
        "freeze, separate attestation, first-access marker and verified completion manifest.",
        "",
        f"The primary inventory contains {primary['all_recorded_burns']['n_events']} recorded burns on "
        f"{diagnostics['n_event_spacecraft']} event-bearing spacecraft among {diagnostics['n_protocol_missions']} "
        f"protocol missions, with {primary['all_recorded_burns']['n_complete']} complete predictor/endpoints and "
        f"{primary['all_recorded_burns']['n_unavailable']} unavailable. The predeclared subset with no additional "
        f"recorded burn has {primary['without_intervening_recorded_burn']['n_complete']}/"
        f"{primary['without_intervening_recorded_burn']['n_events']} complete events and "
        f"{primary['without_intervening_recorded_burn']['n_unavailable']} unavailable. The primary prediction MAE "
        f"is {num(primary['all_recorded_burns'].get('mean_absolute_error_prediction_km'), 3)} km against "
        f"{num(primary['all_recorded_burns'].get('mean_absolute_error_zero_km'), 3)} km for the zero-prediction baseline. "
        f"The prediction MAE is lower than that baseline in {diagnostics['n_spacecraft_deletions_lower_prediction_mae']}/"
        f"{diagnostics['n_spacecraft_deletions']} spacecraft deletions. These are descriptive checks of this "
        "calibrated energy-error diagnostic on the stated event population.",
        "",
        f"The {primary['all_recorded_burns']['n_events']} event rows contain "
        f"{diagnostics['n_unique_post_event_endpoints']} unique spacecraft/first-after-set/target combinations. "
        + (
            "Shared endpoints: "
            + "; ".join(
                f"{data['missions'][group['mission']]['name']}, set {group['epoch']}, target {group['target']}: "
                + ", ".join(group["event_ids"])
                for group in diagnostics["shared_endpoint_groups"]
            )
            + ". Both recorded burns remain in the frozen population. "
            if diagnostics["shared_endpoint_groups"]
            else ""
        )
        + "Repeated endpoints, spacecraft and conditions prevent treating the event count as an independent sample size.",
        "",
        plateau_prose,
        "",
        table(
            [
                "Population / deletion",
                "Complete / recorded burns",
                "Unavailable",
                "Slope",
                "Intercept km",
                "Origin slope",
                "Pearson r",
                "Spearman rho",
                "Prediction MAE km",
                "Zero-prediction MAE km",
                "Prediction median absolute error km",
                "Median signed prediction error km",
                "Sign agreements",
                "Zero predictor or endpoint",
            ],
            rows,
        ),
        "",
        primary["interpretation"],
        "",
        "; ".join(result["limitations"]),
        "",
    ]
    largest = diagnostics["largest_abs_prediction_error"]
    if largest is not None:
        text += [
            f"Energy-compatibility labels are {composition(diagnostics['class_counts'], {})}. Fractions remain "
            "unclipped. As a descriptive example selected after scoring for the largest absolute prediction error, "
            f"{data['missions'][largest['mission']]['name']} has fraction {num(largest['fraction'], 3)} and "
            f"prediction error {num(largest['absolute_prediction_error_km'], 3)} km while labelled "
            f"{largest['class']}. Compatibility is not proof of an exact retained-energy state or catalogue fitting provenance.",
            "",
        ]
    coverage_rows = []
    for mission in protocol["missions"]:
        coverage = result["coverage"][mission]
        own = [event for event in result["events"] if event["mission"] == mission]
        record = coverage["record"]
        complete = primary["by_spacecraft"].get(mission, {}).get("n_complete", 0)
        coverage_rows.append(
            [
                data["missions"][mission]["name"],
                record.get("source_id", "published record"),
                record.get("coverage_status", "published record"),
                len(coverage["orbit_days_missing"]),
                len(record.get("days_missing", [])),
                coverage["n_recorded_burns"],
                complete,
                len(own) - complete,
                coverage["orbit_detector_misses"],
                coverage["element_detector_misses"],
            ]
        )
    text += [
        f"The orbit detector lacks an overlapping interval for {diagnostics['orbit_detector_misses']}/"
        f"{primary['all_recorded_burns']['n_events']} published events; the element detector does so for "
        f"{diagnostics['element_detector_misses']}/{primary['all_recorded_burns']['n_events']}. "
        "Published-event and source coverage includes spacecraft with zero recorded in-month burns. Detector misses "
        "mean no detector interval overlaps the recorded interval; they do not remove events. An empty registry "
        "does not establish complete physical reporting, and detector timing/averaging limits remain relevant.",
        "",
        table(
            [
                "Spacecraft",
                "Record source",
                "Record coverage status",
                "Missing orbit days",
                "Missing record days",
                "Recorded burns",
                "Complete predictor/endpoints",
                "Unavailable",
                "Orbit detector misses",
                "Element detector misses",
            ],
            coverage_rows,
        ),
        "",
        diagnostics["retention_note"],
        "",
        f"The independent numerical audit passed {data['extras']['locked_audit']['result']['n_checks']:,} checks "
        f"with {len(data['extras']['locked_audit']['result']['issues'])} discrepancies. The separately hashed "
        "provenance audit verifies local chronology and retained file identities. These are locally dated, hash-bound "
        "records with author attestation, not an externally timestamped preregistration.",
        "",
        f"The secondary propagation population has {diagnostics['n_secondary_usable_pairs']:,} usable finite pairs "
        f"among {diagnostics['n_secondary_raw_pairs']:,} raw set/lead pairs. Its mission/band horizons and component "
        "coverage use the same frozen criterion and descriptive deletion checks as the corrected earlier benchmark. "
        "The displayed secondary component sigmas and coverage include the later truth-RIC covariance amendment, "
        "documented cell by cell in [the dated correction](covariance-basis-correction.md). The earlier independent "
        "numerical audit applies to the preserved original result bytes; the amendment is separately checked by "
        "Cartesian covariance transport. Original primary outcomes and frozen files are unchanged.",
        "",
    ]
    if detailed:
        support_rows = []
        for key, value in data["extras"].items():
            if not key.startswith("locked_thrusters_"):
                continue
            manifest = value["result"]
            dates = [product["date"] for product in manifest["products"]]
            support_rows.append(
                [
                    data["missions"][manifest["mission"]]["name"],
                    f"{min(dates)} to {max(dates)}",
                    manifest["n_products"],
                    manifest["total_bytes"],
                    f"[Supporting manifest]({posixpath.relpath(value['input']['path'], 'docs')})",
                    value["input"]["sha256"],
                    manifest["filename_limitation"],
                    manifest["retention_convention"],
                ]
            )
        text += [
            "### Supplemental GRACE thruster provenance",
            "",
            table(
                [
                    "Mission",
                    "Product dates",
                    "Parsed THR products",
                    "Bytes",
                    "Manifest",
                    "Manifest SHA-256",
                    "Filename inventory limitation",
                    "Retention convention",
                ],
                support_rows,
            ),
            "",
        ]
        event_rows = []
        for event in result["events"]:
            event_rows.append(
                [
                    event["event_id"],
                    event["mission"],
                    event["burn_from"],
                    event["burn_to"],
                    event["epoch"],
                    num(event.get("epoch_delay_after_burn_end_hours")),
                    event["n_clean_sets"],
                    num(event["calibration_offset_m"]),
                    num(event["calibration_scatter_m"]),
                    num(event["delta_a_m"]),
                    num(event["a_error_m"]),
                    num(event["fraction"]),
                    event["class"],
                    significant(event["missing_specific_energy_km2_s2"]),
                    num(event["predicted_in_track_km"]),
                    num(event["signed_in_track_km"]),
                    event.get("target"),
                    len(event["later_burns"]),
                    "; ".join(f"{start} to {end}" for start, end in event["later_burns"]) or "none",
                    event["orbit_detector_missed"],
                    event["element_detector_missed"],
                    "; ".join(event["unavailable_reasons"]),
                ]
            )
        text += [
            "### Every recorded burn",
            "",
            table(
                [
                    "Event",
                    "Mission",
                    "Burn start UTC",
                    "Burn end UTC",
                    "First post-event epoch",
                    "Delay from end h",
                    "Prior clean sets",
                    "Calibration offset m",
                    "Calibration scatter m",
                    "Burn delta-a m",
                    "Calibrated semi-major-axis error m",
                    "Burn fraction",
                    "Energy compatibility",
                    "Missing specific energy km²/s²",
                    "Predicted in-track km",
                    "Observed signed in-track km",
                    "Target UTC",
                    "Intervening recorded burns",
                    "Intervening intervals UTC",
                    "Orbit detector missed",
                    "Element detector missed",
                    "Unavailable reasons",
                ],
                event_rows,
            ),
            "",
        ]
    text.append(
        "Secondary horizons, component coverage and deletion checks for every population/lead are in [the locked replay tables](locked-benchmark-v2-tables.md)."
    )
    return "\n".join(text)


def radio_sections(data: dict, *, detailed: bool = False) -> str:
    text = []
    scalar = data["extras"]["radio"]
    if scalar["status"] == "supplied":
        record = scalar["result"]
        text += [
            record["interpretation"] + ". " + record["geometry"] + ". " + record["definitions"]["phase_time"] + ".",
            "An orbital-component threshold failure at the first sampled age leaves fresher ages unmeasured. "
            "It does not establish a beam-crossing failure, a whole receiver-band limit or the impossibility of a radio observation.",
            "",
        ]
        columns = record["columns"]
        text += [
            table(
                ["Frequency column", "Actual MHz", "Primary width deg", "Maximum measured width deg", "Width model"],
                [
                    [
                        column["key"],
                        column["freq_mhz"],
                        significant(column["fwhm_deg"]),
                        significant(column.get("beam_metadata", {}).get("maximum_diametric_width_deg")),
                        column.get("beam_model"),
                    ]
                    for column in columns
                ],
            ),
            "",
            f"The primary scalar criterion uses a width fraction of {significant(record['beam_fraction'])} and "
            f"an empirical inside fraction of {pct(record['coverage'])}. The alternate criterion and maximum-width "
            "choices are descriptive sensitivities; the nominal analytic comparison is explicitly historical.",
            "",
        ]
        if detailed:
            rows = []
            for component, bands in record["threshold_status"].items():
                for band, columns in bands.items():
                    for column, windows in columns.items():
                        for window, value in windows.items():
                            end = (
                                f"passes through the longest tested lead ({value['last_available_h']:g} h)"
                                if value["end_reason"] == "data_exhausted"
                                else f"first failed sample {value['first_failed_sampled_h']:g} h"
                            )
                            rows.append(
                                [
                                    component,
                                    band,
                                    column,
                                    window,
                                    num(value["passed_through_sampled_h"]),
                                    end,
                                    value["n_last_available"],
                                    value["below_first_lead"],
                                ]
                            )
            text += [
                table(
                    [
                        "Component",
                        "Band",
                        "Frequency/scale column",
                        "Window",
                        "Last passing sample h",
                        "Termination",
                        "n at last available sample",
                        "Earlier ages",
                    ],
                    rows,
                ),
                "",
            ]
            variants = []
            for key in (
                "component_criterion_sensitivity",
                "maximum_measured_width_sensitivity",
                "historical_analytic_comparison",
            ):
                variant = record.get(key) or {}
                for component, bands in (variant.get("component_thresholds_hours") or {}).items():
                    for band, by_column in bands.items():
                        for column, by_window in by_column.items():
                            for window, last in by_window.items():
                                observed = [
                                    row["lead_h"]
                                    for row in record["rows"]
                                    if row["window"] == window and row.get("altitude_band", row.get("band")) == band
                                ]
                                label = (
                                    "no sampled lead passed"
                                    if last is None
                                    else (
                                        f"passes through the longest tested lead ({last:g} h)"
                                        if observed and last == max(observed)
                                        else f"last passing sample {last:g} h"
                                    )
                                )
                                variants.append(
                                    [key, component, band, column, window, label, variant["interpretation"]]
                                )
            text += [
                "### Scalar criterion and beam-width sensitivities",
                "",
                table(
                    [
                        "Variant",
                        "Component",
                        "Band",
                        "Frequency column",
                        "Window",
                        "Reported endpoint",
                        "Interpretation",
                    ],
                    variants,
                ),
                "",
            ]
    tracks = data["extras"]["radio_tracks"]
    if tracks["status"] != "supplied":
        text.append("Full measured-beam topocentric track results are pending.")
        return "\n\n".join(text)
    result = tracks["result"]
    protocol = data["extras"]["radio_tracks_protocol"]["result"]
    diagnostics = data["extras"]["radio_tracks_diagnostics"]["result"]
    cells = result["by_beam_window_lead_observation"]
    text += [
        f"Beam source: {cite(data, 'meerkat_paper')}; data: {cite(data, 'meerkat_data')}.",
        "",
        f"The topocentric comparison admits {result['n_eligible_trials']}/{result['n_input_trials']} source-filtered "
        f"set/lead trials and constructs {result['n_cases']} beam/pointing/observation cases. "
        f"Those eligible curves come from {diagnostics['n_sets']} element sets on {diagnostics['n_missions']} spacecraft. "
        f"Eligibility: {protocol['eligibility']}. Geometry: {protocol['geometry']}. "
        f"Pointings: {protocol['candidate_rule']}. These are previously inspected evaluation windows and constructed "
        "pointings, not an untouched test population or an observing schedule. The source frequencies below are "
        "the actual measured frequency slices. Cases sharing a trajectory are correlated.",
        "",
        f"Eligibility inventory: {composition(result['eligibility_counts'], {})}.",
        "",
    ]
    strata = [("All declared offsets", row) for row in diagnostics["by_observation"]]
    strata += [("Other declared offsets", row) for row in diagnostics["by_observation_without_exact_boundary_offsets"]]
    boundary = [row for row in diagnostics["full_by_offset"] if abs(row["offset_fraction"]) == 1]
    if boundary:
        combined = {
            key: sum(row[key] for row in boundary)
            for key in (
                "n_cases",
                "false_crossing",
                "missed_crossing",
                "both_crossed",
                "true_negative",
                "observation_edge_mismatch",
            )
        }
        combined["observation"] = "full"
        strata.append(("Declared boundary-stress offsets", combined))
    stress_offsets = ", ".join(significant(row["offset_fraction"]) for row in boundary)
    text += [
        f"The declared offsets at {stress_offsets} half-power radii are deliberate boundary stress cases. "
        "Their classification counts remain in the full inventory and are shown separately from the other declared "
        "offsets. Removing these exact-radius constructions is a descriptive sensitivity, not a new test population. "
        "The numerical near-threshold diagnostic is separate from this construction-based split.",
        "",
        table(
            [
                "Pointing stratum",
                "Observation interval",
                "All cases",
                "False crossings",
                "Missed crossings",
                "Both cross",
                "Neither crosses",
                "False / predicted crossings",
                "Missed / reference crossings",
                "Observation-edge mismatches",
            ],
            [
                [
                    label,
                    row["observation"],
                    row["n_cases"],
                    row["false_crossing"],
                    row["missed_crossing"],
                    row["both_crossed"],
                    row["true_negative"],
                    f"{row['false_crossing']}/{row['false_crossing'] + row['both_crossed']} ({pct(row['false_crossing'] / (row['false_crossing'] + row['both_crossed'])) if row['false_crossing'] + row['both_crossed'] else 'undefined'})",
                    f"{row['missed_crossing']}/{row['missed_crossing'] + row['both_crossed']} ({pct(row['missed_crossing'] / (row['missed_crossing'] + row['both_crossed'])) if row['missed_crossing'] + row['both_crossed'] else 'undefined'})",
                    row["observation_edge_mismatch"],
                ]
                for label, row in strata
            ],
        ),
        "",
    ]
    full = next(row for row in diagnostics["by_observation"] if row["observation"] == "full")
    timing = full["closest_time_error_s"]
    radio_quantile = pct(tracks["reported_quantile"]["probability"])
    angle = full["instantaneous_error_at_reference_closest_deg"]
    text += [
        f"Across the full-span constructed cases, absolute closest-time error has median {significant(timing['median_abs'])} s, "
        f"interpolated {radio_quantile} quantile {significant(timing['q95_abs_linear'])} s and maximum {significant(timing['max_abs'])} s "
        f"(n={timing['n']}). Prediction/reference closest-time censoring counts are "
        f"{full['prediction_closest_time_censored']}/{full['reference_closest_time_censored']}. "
        f"Instantaneous line-of-sight separation at reference closest approach has absolute median "
        f"{significant(angle['median_abs'])} deg, interpolated {radio_quantile} quantile "
        f"{significant(angle['q95_abs_linear'])} deg and maximum {significant(angle['max_abs'])} deg (n={angle['n']}). "
        "These are repeated geometric comparisons on the eligible curves, not independent timing trials. "
        "Range-rate, interferometric coherence and received power have not been validated by this beam-geometry experiment.",
        "",
    ]
    beam_rows = []
    for beam in sorted({cell["beam_key"] for cell in cells}):
        selected = [cell for cell in cells if cell["beam_key"] == beam]
        totals = {
            field: sum(cell[field] for cell in selected)
            for field in (
                "n_cases",
                "false_crossing_n",
                "missed_crossing_n",
                "both_crossed_n",
                "true_negative_n",
                "observation_edge_mismatch_n",
                "n_reference_crossed",
                "n_prediction_crossed",
            )
        }
        beam_rows.append(
            [
                beam,
                selected[0]["frequency_mhz"],
                totals["n_cases"],
                totals["false_crossing_n"],
                totals["missed_crossing_n"],
                totals["both_crossed_n"],
                totals["true_negative_n"],
                totals["observation_edge_mismatch_n"],
                f"{totals['false_crossing_n']}/{totals['n_prediction_crossed']}",
                f"{totals['missed_crossing_n']}/{totals['n_reference_crossed']}",
            ]
        )
    text += [
        table(
            [
                "Measured beam",
                "Actual MHz",
                "Constructed cases",
                "False crossings",
                "Missed crossings",
                "Both cross",
                "Neither crosses",
                "Observation-edge mismatches",
                "False / predicted crossings",
                "Missed / reference crossings",
            ],
            beam_rows,
        ),
        "",
        protocol["timing_summary"] + ". " + protocol["uncertainty"] + ". "
        "No scalar component horizon is promoted to a general beam or observing guarantee.",
        "",
    ]
    if detailed:
        text += [
            diagnostics["boundary_diagnostic"],
            "",
            diagnostics["legacy_metadata"],
            "",
            "### Full-span offset stress counts",
            "",
            table(
                [
                    "Offset in boundary radii",
                    "Cases",
                    "False",
                    "Missed",
                    "Both",
                    "Neither",
                    "Any numerical near-boundary flag",
                ],
                [
                    [
                        row["offset_fraction"],
                        row["n_cases"],
                        row["false_crossing"],
                        row["missed_crossing"],
                        row["both_crossed"],
                        row["true_negative"],
                        row["any_near_boundary"],
                    ]
                    for row in diagnostics["full_by_offset"]
                ],
            ),
            "",
        ]
        for label, values in (
            ("Every beam/window/lead/observation", cells),
            ("Every signed pointing offset", result["by_beam_window_lead_observation_offset"]),
        ):
            text += [f"### {label}", ""]
            identity = ["beam_key", "frequency_mhz", "window", "lead_h", "observation"]
            if "offset" in label:
                identity += ["offset_fraction"]
            count_keys = [
                "n_cases",
                "n_missions",
                "n_sets",
                "n_trials",
                "false_crossing_n",
                "missed_crossing_n",
                "both_crossed_n",
                "true_negative_n",
                "observation_edge_mismatch_n",
                "n_reference_crossed",
                "n_prediction_crossed",
            ]
            text += [
                table(
                    identity + count_keys + ["mission_counts"],
                    [
                        [row.get(key) for key in identity + count_keys] + [composition(row["mission_counts"], {})]
                        for row in values
                    ],
                ),
                "",
            ]
            for suffix, title in (
                ("_abs_q95_linear", "Timing and angular errors"),
                ("_censored_n", "Censored timing counts"),
            ):
                if not values:
                    continue
                if suffix == "_abs_q95_linear":
                    metric_keys = [key for key in values[0] if key.endswith(suffix)]
                    expanded = [
                        key.removesuffix(suffix) + part
                        for key in metric_keys
                        for part in ("_n", "_median", "_abs_median", suffix)
                    ]
                else:
                    expanded = [
                        key for key in values[0] if key.endswith(suffix) or key.endswith(("_contact_n", "_inside_n"))
                    ]
                text += [
                    f"{title}: signed median, absolute median and interpolated tail each retain their own denominator where applicable.",
                    "",
                    table(
                        identity + expanded,
                        [
                            [row.get(key) for key in identity] + [significant(row.get(key)) for key in expanded]
                            for row in values
                        ],
                    ),
                    "",
                ]
    else:
        text.append(
            "Every window/lead/observation and signed-offset denominator, crossing count, censored-time count and angular/timing residual is in [the radio tables](radio-v2-tables.md)."
        )
    return "\n".join(text)


def pending_sections(data: dict) -> str:
    names = {"dsgp4": "Learned propagator", "radio": "Radio geometry", "locked": "Locked calendar-month replay"}
    paragraphs = []
    for key, title in names.items():
        extra = data["extras"][key]
        if key == "radio" and (extra["status"] == "supplied" or data["extras"]["radio_tracks"]["status"] == "supplied"):
            paragraphs.append(f"**{title}.**\n\n{radio_sections(data)}")
        elif extra["status"] == "pending":
            if key == "locked":
                if data["extras"].get("locked_access", {}).get("status") == "supplied":
                    access = data["extras"]["locked_access"]["result"]
                    statement = data["extras"]["locked_attestation"]["result"]
                    paragraphs.append(
                        f"**{title}: author attestation recorded; execution started, completed result pending.** "
                        f"The separate author attestation at {statement['attested_at']} is bound to the unchanged "
                        f"frozen protocol; first experiment access was {access['started_at']}. This publication "
                        "build includes execution metadata only and reports no September result. The "
                        "[current execution-status note](protocols/september-2024-execution-status.md) links the "
                        "historical freeze, attestation and first-access marker."
                    )
                    continue
                evidence = data["protocols"]["locked_protocol"]
                protocol = evidence["result"]
                protocol_path = Path(evidence["input"]["path"]).relative_to("docs").as_posix()
                prose_path = Path(protocol_path).with_suffix(".md").as_posix()
                audit = data["protocols"]["protocol_audit"]["result"]
                paragraphs.append(
                    f"**{title}: scientific protocol frozen; execution pending author attestation.** "
                    f"The [scientific protocol]({prose_path}) was frozen at {protocol['frozen_at']} "
                    f"for {len(protocol['missions'])} spacecraft under the calendar rule “{protocol['calendar_rule']}”. "
                    f"The [executable protocol]({protocol_path}) has SHA-256 `{evidence['input']['sha256']}`. "
                    f"The freeze audit verified {audit['source_files_verified']} source files and "
                    f"{audit['prior_corrected_inputs_verified']} earlier corrected input artefacts. "
                    f"{extra['reason']}. September reference residuals and post-burn outcomes have not been "
                    "accessed or scored for this experiment. Existing public-element/weather history and orbit-file "
                    "overlap are documented exposure limits; the month is not claimed to be unseen in every sense."
                )
            else:
                paragraphs.append(
                    f"**{title}: pending.** The earlier quantitative claim is not carried into this version."
                )
        elif key == "dsgp4":
            paragraphs.append(f"**{title}.**\n\n{ml_sections(data)}")
        elif key == "locked":
            paragraphs.append(f"**{title}.**\n\n{locked_sections(data)}")
        else:
            paragraphs.append(
                f"**{title}: revised artefact supplied.** Results and provenance are embedded in the canonical "
                f"evidence object under `extras.{key}`; source: `{extra['input']['path']}`."
            )
    return "\n\n".join(paragraphs)


def locked_execution_note(data: dict) -> str:
    """Current status is derived separately; never rewrite a frozen historical record."""
    document = "docs/protocols/september-2024-execution-status.md"

    def link(label: str, path: str) -> str:
        return f"[{label}]({posixpath.relpath(path, posixpath.dirname(document))})"

    frozen = data["protocols"]["locked_protocol"]
    protocol = frozen["result"]
    lines = [
        "# September calendar replay: current execution status",
        "",
        f"Local review artefact generated {data['built_at']} from "
        + link("the canonical publication object", "docs/assets/benchmark-v2.json")
        + ".",
        "",
        f"The scientific protocol was frozen at {protocol['frozen_at']} with SHA-256 `{frozen['input']['sha256']}`. "
        + link("Frozen scientific protocol JSON", frozen["input"]["path"])
        + "; "
        + link("unchanged historical method note", data["publication"]["frozen_protocol_markdown_path"])
        + ". Any pending-attestation or not-started wording in that snapshot describes the time of freezing.",
        "",
    ]
    extras = data["extras"]
    if extras.get("locked_access", {}).get("status") != "supplied":
        lines.append(
            "**Author attestation and experiment execution remain pending in this publication build. No September result is reported.**"
        )
        return "\n".join(lines)
    attestation = extras["locked_attestation"]
    statement = attestation["result"]
    access = extras["locked_access"]
    lines += [
        f"{statement['author']} supplied the separately bound author attestation at {statement['attested_at']}. "
        + link("Preserved attestation", attestation["input"]["path"])
        + f"; SHA-256 `{attestation['input']['sha256']}`.",
        "",
        "Author's recorded words: “" + statement.get("author_verbatim", statement["statement"]) + "”",
        "",
        statement.get("local_evidence", {}).get("finding", ""),
        "",
        statement.get("prior_exposure_qualification", ""),
        "",
        f"First experiment access was {access['result']['started_at']}. "
        + link("Immutable first-data-access marker", access["input"]["path"])
        + f"; SHA-256 `{access['input']['sha256']}`. The attestation precedes access and binds the same frozen scientific protocol.",
        "",
    ]
    if extras["locked"]["status"] == "supplied":
        result = extras["locked"]["result"]
        completion = extras["locked_completion"]
        lines += [
            f"**Execution completed at {result['completed_at']} for every frozen mission.** "
            + link("Final completion manifest", completion["input"]["path"])
            + f"; SHA-256 `{completion['input']['sha256']}`. The publication build verifies the aggregate output "
            "hashes, mission completion hashes, protocol/attestation binding and secondary trial denominators.",
            "",
            link("Completed results and every recorded event", "docs/locked-benchmark-v2-tables.md")
            + "; "
            + link("current paper v2", "docs/paper.md")
            + ". These are local review artefacts; no external publication is claimed.",
        ]
    else:
        lines.append(
            "**Execution has started; a verified completed result is not yet included in this publication build.** "
            "This note uses attestation/access metadata only. It does not inspect or report partial September residuals or post-burn outcomes."
        )
    return "\n".join(lines)


def diagnostic_text(data: dict) -> str:
    diagnostics = data["discrepancy_diagnostics"]
    selection = diagnostics["selection"]
    multiple = data["definition"]["covariance_multiples"][-1]

    def extrema_text(record: dict) -> str:
        if record["minimum"] is None:
            return "no defined coverage cells"
        a, b = record["minimum"], record["maximum"]
        return (
            f"{pct(a['inside_2_sigma_fraction'])} ({a['inside_2_sigma_count']}/{a['n']}, {a['band']}, {a['window']}) "
            f"to {pct(b['inside_2_sigma_fraction'])} ({b['inside_2_sigma_count']}/{b['n']}, {b['band']}, {b['window']})"
        )

    paragraphs = [
        f"At {selection['day_lead_h']} hours, observed in-track coverage within {multiple}σ above "
        f"{selection['above_altitude_km']} km ranges from {extrema_text(diagnostics['above_600_storm_day_in_track_2sigma'])} "
        f"across the disturbed windows ({', '.join(selection['storm_windows'])}). At {selection['early_lead_h']} hours "
        f"across all band/window cells it ranges from {extrema_text(diagnostics['early_all_band_window_in_track_2sigma'])}. "
        "These extrema describe the measured cells and do not estimate a population confidence interval."
    ]
    swarm = diagnostics["swarm_may_long_lead"]
    all_rows, supported = swarm["all_usable"], swarm["supported_history_only"]
    paragraphs.append(
        f"For all Swarm spacecraft in the May window at {selection['swarm_long_lead_h']} hours, the median absolute "
        f"in-track residual is {num(all_rows['median_abs_in_track_km'])} km (n={all_rows['n_finite_raw']}), and the "
        f"median absolute saved storm shift is {num(all_rows['median_abs_storm_shift_km'])} km "
        f"(n={all_rows['n_finite_shift']}). Restricting both measurements to the supported history-coefficient "
        f"subset gives {num(supported['median_abs_in_track_km'])} km and "
        f"{num(supported['median_abs_storm_shift_km'])} km, respectively (n={supported['n_pairs']}). "
        f"The all-usable coefficient sources are {composition(all_rows['coefficient_source_counts'], {})}. "
        "A shift magnitude is not an improvement estimate."
    )
    rows = []
    for component, cell in diagnostics["low_band_quiet_day"].items():
        c = cell["coverage"]
        rows.append(
            [
                selection["low_band"],
                selection["control_window"],
                selection["day_lead_h"],
                component,
                f"{c['inside_2_sigma_count']}/{c['n']} ({pct(c['inside_2_sigma_fraction'])})",
            ]
        )
    for mission, cells in diagnostics["high_missions_quiet_day"].items():
        for component, cell in cells.items():
            c = cell["coverage"]
            rows.append(
                [
                    data["missions"][mission]["name"],
                    selection["control_window"],
                    selection["day_lead_h"],
                    component,
                    f"{c['inside_2_sigma_count']}/{c['n']} ({pct(c['inside_2_sigma_fraction'])})",
                ]
            )
    paragraphs.append(table(["Population", "Window", "Lead h", "Component", f"Inside {multiple}σ"], rows))
    status = diagnostics["high_altitude_storm_term_status"]
    unsupported = sum(cell["status"] == "unsupported" for cell in status)
    sources = sorted({source for cell in status for source in cell["coefficient_source_counts"]})
    paragraphs.append(
        f"In the {selection['high_band']} band and its separate spacecraft summaries, {unsupported}/{len(status)} "
        "window/lead cells label the storm term unsupported; this status is explicit even when no trial is usable. "
        f"Stored coefficient labels present there are {', '.join(sources) or 'none'}. B-star fallback is not treated "
        "as a supported physical coefficient. The canonical object retains every status and source count."
    )
    return "\n\n".join(paragraphs)


def paper_tables(data: dict) -> dict[str, str]:
    return {
        "horizons": headline_table(data).split("\n\n")[0],
        "components": next(p for p in diagnostic_text(data).split("\n\n") if p.startswith("| Population")),
        "radio_age": publication_text.age_table(data, table),
    }


def render(data: dict) -> dict[str, str]:
    tables = {k: publication_text.display_windows(v, data) for k, v in paper_tables(data).items()}
    evidence_hash = hashlib.sha256((ROOT / "docs/assets/benchmark-v2.json").read_bytes()).hexdigest()
    template = (ROOT / "docs/paper.template.md").read_text(encoding="utf-8")
    paper = publication_text.render_template(template, data, tables, evidence_hash)
    publication_text.validate_numeric_prose(template, paper, data, tables, evidence_hash)
    metadata_rows = [[row["path"], row["sha256"]] for row in data["inputs"] + data["source_code"]]
    window_rows = [
        [data["publication"]["windows"][k], w["sets_from"], w["sets_to"]] for k, w in data["windows"].items()
    ]
    bibliography_rows = [[f"[{v['title']}]({v['url']})", v["purpose"]] for v in data["bibliography"].values()]
    supplement = detailed_tables(data) + "\n\n## Reproducibility and primary sources\n\n"
    supplement += table(["Window", "Epoch selection begins", "Epoch selection ends"], window_rows)
    supplement += "\n\n" + table(["Input or source", "SHA-256"], metadata_rows)
    supplement += "\n\n" + table(["Source", "Use in this work"], bibliography_rows)
    if "release_correction" in data:
        supplement += (
            "\n\nThe tables above preserve the published v2 measurements and original v2 provenance bindings. "
            "The dated v2.1 [correction ledger](assets/publication-assets-v2.1.json) records the distributable "
            "replacement hashes and release assets; original provenance hashes are not assertions that a "
            "scrubbed replacement has the same bytes. No table entry has changed."
        )
    output = {
        "docs/paper.md": paper,
        "docs/benchmark-v2-tables.md": publication_text.display_windows(supplement, data),
        "docs/protocols/september-2024-execution-status.md": locked_execution_note(data),
        "docs/protocols/2026-09-08-september-2024.md": locked_execution_note(data),
        "docs/radio-v2-tables.md": publication_text.display_windows(
            "# Revised radio geometry: complete tables\n\n"
            + radio_sections(data, detailed=True)
            + "\n\n## Crossing agreement and closest-time error by element-set age\n\n"
            + tables["radio_age"],
            data,
        ),
    }
    replay = data["extras"]["locked"]["result"]
    window = next(iter(next(iter(replay["secondary"]["by_band"].values()))))
    secondary = {
        **data,
        "results": replay["secondary"],
        "windows": {window: {"role": "retrospective calendar replay"}},
        "coverage": {},
        "detector_diagnostics": {},
        "corrections": {"horizons": [], "components": []},
        "reference_checks": {
            "interpretation": "No sampled laser-ranging comparison is part of this replay.",
            "sgp4_vs_slr_by_mission": {},
        },
        "extras": {key: {"status": "pending"} for key in data["extras"]},
    }
    output["docs/locked-benchmark-v2-tables.md"] = (
        "# Locked calendar replay: complete evidence\n\n"
        + locked_sections(data, detailed=True)
        + "\n\n"
        + detailed_tables(secondary, secondary_only=True).replace(
            "# Reference benchmark: complete tables", "## Secondary reference tables", 1
        )
    )
    return output


def basis_correction_outputs(data: dict) -> dict[str, str]:
    amendment = data["covariance_basis_correction"]
    rows, csv_rows = [], []
    for population in ("reference", "september"):
        for cell in amendment[population]["cells"]:
            a, b = cell["old"]["coverage"], cell["new"]["coverage"]
            row = {"population": population, **{k: cell[k] for k in ("scope", "name", "window", "lead_h", "component")}}
            for field in (
                "n",
                "median_sigma_km",
                "inside_1_sigma_count",
                "inside_1_sigma_fraction",
                "inside_2_sigma_count",
                "inside_2_sigma_fraction",
            ):
                row[f"old_{field}"], row[f"new_{field}"] = a[field], b[field]
            for multiple in (1, 2):
                field = f"inside_{multiple}_sigma_fraction"
                row[f"change_{multiple}_sigma_pp"] = (
                    None if a[field] is None or b[field] is None else 100 * (b[field] - a[field])
                )
            csv_rows.append(row)
            rows.append(
                [
                    population,
                    cell["scope"],
                    cell["name"],
                    data["publication"]["windows"].get(cell["window"], cell["window"]),
                    cell["lead_h"],
                    cell["component"],
                    f"{a['n']} → {b['n']}",
                    f"{a['inside_1_sigma_count']} → {b['inside_1_sigma_count']}",
                    f"{pct(a['inside_1_sigma_fraction'])} → {pct(b['inside_1_sigma_fraction'])}",
                    num(row["change_1_sigma_pp"], 6),
                    f"{a['inside_2_sigma_count']} → {b['inside_2_sigma_count']}",
                    f"{pct(a['inside_2_sigma_fraction'])} → {pct(b['inside_2_sigma_fraction'])}",
                    num(row["change_2_sigma_pp"], 6),
                ]
            )
    title = "# Covariance basis correction — " + amendment["corrected_at"][:10]
    note = (
        "Covariance is transported from predicted-state RIC into each residual's truth RIC basis before component scoring. "
        "Every cell is shown, including unchanged cells; differences are percentage points. Residuals, exclusions and horizons are unchanged. "
        "The September secondary tables use a dated amendment; the original frozen files, primary endpoint and audits remain preserved. "
        "Full precision sigma medians, counts and fractions are in [the CSV](assets/benchmark-v2-basis-corrections.csv)."
    )
    body = table(
        [
            "Population",
            "Scope",
            "Group",
            "Window",
            "Lead h",
            "Component",
            "Old → new n",
            "Inside 1σ count",
            "Inside 1σ share",
            "Change pp",
            "Inside 2σ count",
            "Inside 2σ share",
            "Change pp",
        ],
        rows,
    )
    return {
        "docs/covariance-basis-correction.md": title + "\n\n" + note + "\n\n" + body,
        "docs/assets/benchmark-v2-basis-corrections.csv": pd.DataFrame(csv_rows).to_csv(
            index=False, lineterminator="\n"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="data/validation/reference_benchmark.json")
    parser.add_argument("--trials", default="data/validation/reference_benchmark.parquet")
    for name in ("dsgp4", "dsgp4_audit", "radio", "radio_tracks", "locked"):
        parser.add_argument(f"--{name.replace('_', '-')}")
    parser.add_argument("--dsgp4-pairs", "--dsgp4-paired", dest="dsgp4_paired")
    parser.add_argument("--locked-protocol", default="docs/protocols/2026-09-08-september-2024.json")
    parser.add_argument("--classifier-protocol", default="docs/protocols/2026-09-08-post-manoeuvre-classifier.json")
    parser.add_argument("--protocol-audit", default="output/referee/frozen_protocol_audit.json")
    parser.add_argument("--locked-audit", default="output/referee/locked_september_audit.json")
    parser.add_argument("--locked-provenance-audit", default="output/referee/locked_provenance_independent.json")
    parser.add_argument(
        "--locked-access", help="Read first-access/attestation metadata while a completed result is pending"
    )
    args = parser.parse_args()
    data = build(args)
    archive = ROOT / "docs/archive"
    archive.mkdir(parents=True, exist_ok=True)
    original = ROOT / data["archive"]["preserved_local_body"]
    display = ROOT / data["archive"]["display_paper"]
    if not original.exists():
        original.write_bytes(display.read_bytes())
    original_bytes = original.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != data["archive"]["preserved_local_body_sha256"]:
        raise ValueError("Preserved v1 body differs from its canonical hash")
    notice = (
        f"> **Historical paper v1 — notice added {data['built_at'][:10]}.** "
        "The current corrected results are in [paper v2](../paper.md). The historical body below contains "
        "superseded claims and is retained for the correction record. "
        f"[The exact local body before this notice]({original.name}) is preserved with SHA-256 "
        f"`{data['archive']['preserved_local_body_sha256']}`. The original Git tag remains unchanged; its paper blob "
        f"has SHA-256 `{data['archive']['tag_paper_sha256']}`.\n\n---\n\n"
    )
    display.write_bytes(notice.encode("utf-8") + original_bytes)
    for basename in ("findings", "reference-benchmark", "calibration-benchmark"):
        target = archive / f"{basename}-paper-2026-09-v1.md"
        if not target.exists():
            frozen = subprocess.check_output(["git", "show", f"paper-2026-09-v1:docs/{basename}.md"], cwd=ROOT)
            target.write_bytes(frozen)
    (archive / "README.md").write_text(
        "# Historical paper v1\n\nThe display paper has a dated correction notice and retains its historical body. "
        "The exact local body before that notice is [preserved separately](paper-2026-09-v1.original.md); "
        "the local-body and original Git-tag blob hashes are recorded in the canonical evidence object. "
        "The companion benchmark pages are preserved from the `paper-2026-09-v1` Git tag. "
        "These are historical artefacts, not current results. "
        "Read the [revised paper v2](../paper.md) and [complete corrected tables](../benchmark-v2-tables.md) for current results. "
        "Current publication pages "
        "are rendered by `scripts/render_paper_v2.py` from `docs/assets/benchmark-v2.json`; the corresponding "
        "original derived trials and summaries are under `data/validation/v1`.\n",
        encoding="utf-8",
    )
    assets = ROOT / "docs/assets"
    assets.mkdir(parents=True, exist_ok=True)
    canonical = assets / "benchmark-v2.json"
    canonical.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    # Rendering reads the saved object, so every page shares exactly that object.
    data = read_json(canonical)
    correction_rows = []
    for change in data["corrections"]["components"]:
        for field, values in change["changed_fields"].items():
            correction_rows.append(
                {
                    **{k: change[k] for k in ("scope", "name", "window", "lead_h", "component")},
                    "field": field,
                    **values,
                    "old_n": change["old"]["coverage"]["n"],
                    "new_n": change["new"]["coverage"]["n"],
                }
            )
    pd.DataFrame(correction_rows).to_csv(assets / "benchmark-v2-component-corrections.csv", index=False)
    for name, text in {**render(data), **basis_correction_outputs(data)}.items():
        (ROOT / name).write_text(text.strip() + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "canonical": str(canonical),
                "population": data["population"],
                "pending": [k for k, v in data["extras"].items() if v["status"] == "pending"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
