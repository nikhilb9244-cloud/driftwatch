"""Scoring for the dated, hash-locked September protocol; no fetch on import.

Execution requires an author attestation and the exact frozen source hashes.
Burns remain rows even when their predictor or endpoint cannot be measured.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from driftwatch import config
from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs
from driftwatch.screening.ric import ric_basis, to_ric
from driftwatch.storm import precise, reference, reference_run

log = logging.getLogger(__name__)
ATTESTATION = "September reference residuals and post-burn outcomes never inspected"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value: Any) -> None:
    """Atomic metadata commit, including bounded retry for Windows readers."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, indent=2, default=str, allow_nan=False)
        stream.write("\n")
        temporary = Path(stream.name)
    try:
        for attempt in range(10):
            try:
                os.replace(temporary, path)
                break
            except OSError as exc:
                if exc.errno not in {13, 22, 32} or attempt == 9:
                    raise
                time.sleep(0.05)
    finally:
        temporary.unlink(missing_ok=True)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _attestation(protocol: dict, protocol_path: Path) -> dict:
    if protocol.get("author_attestation_path"):
        path = Path(protocol["author_attestation_path"])
        if not path.is_absolute():
            path = protocol_path.parent / path
        if not path.is_file():
            raise RuntimeError("Author attestation file is required before data access")
        statement = _read(path)
        try:
            at = datetime.fromisoformat(statement["attested_at"])
            valid_date = at.tzinfo is not None and at <= datetime.now(UTC)
        except (KeyError, ValueError, TypeError):
            valid_date = False
        if (
            statement.get("statement") != ATTESTATION
            or not isinstance(statement.get("author"), str)
            or not statement["author"].strip()
            or not valid_date
            or statement.get("protocol_sha256") != sha256(protocol_path)
        ):
            raise RuntimeError("Author attestation must identify author/time and match the exact frozen protocol hash")
        return {"path": str(path.resolve()), "sha256": sha256(path), "record": statement}
    raise RuntimeError("External author attestation bound to the frozen protocol is required before data access")


def _manifest(path: Path, out: Path, expected: dict) -> dict:
    value = _read(path)
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise RuntimeError(f"Locked manifest differs in {key}: {path}")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeError(f"Locked manifest has no verified files: {path}")
    required = set()
    if path.name == "gp-input-manifest.json":
        required = {"table"}
    elif path.name.endswith("-inputs-manifest.json"):
        required = {"orbit_table", "metadata"}
    elif path.name.endswith("-completion.json"):
        required = {"trials", "events", "coverage"}
    elif path.name == "completion-manifest.json":
        if not {"locked_trials.parquet", "locked_experiment.json"} <= set(files):
            raise RuntimeError("Final completion manifest omits required aggregate files")
    for key in required:
        if value.get(key) not in files:
            raise RuntimeError(f"Locked manifest omits a required verified {key} file: {path}")
    for relative, digest in files.items():
        file = (out / relative).resolve()
        if not file.is_relative_to(out.resolve()) or not file.is_file() or sha256(file) != digest:
            raise RuntimeError(f"Locked input/output hash mismatch: {relative}")
    return value


def _commit(path: Path, out: Path, files: list[Path], **metadata) -> dict:
    value = {**metadata, "files": {p.relative_to(out).as_posix(): sha256(p) for p in files}}
    _json(path, value)
    return value


def _record_snapshot(record) -> dict:
    attributes = {
        "letter": record.letter,
        "norad_id": int(record.norad_id),
        "intervals": [[a.isoformat(), b.isoformat()] for a, b in record.intervals],
        "days_missing": [d.isoformat() for d in record.days_missing],
        "files": list(record.files),
        "authoritative": bool(getattr(record, "authoritative", True)),
    }
    for key in ("source_id", "coverage_status", "coverage_start", "coverage_end", "provenance", "issues"):
        if hasattr(record, key):
            attributes[key] = getattr(record, key)
    return {"attributes": attributes, "metadata": record.as_metadata() if hasattr(record, "as_metadata") else {}}


def _restore_record(value: dict):
    attributes = dict(value["attributes"])
    attributes["intervals"] = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in attributes["intervals"]]
    attributes["days_missing"] = [date.fromisoformat(d) for d in attributes["days_missing"]]
    return SimpleNamespace(**attributes, as_metadata=lambda: value["metadata"])


def _source_snapshots(names: list[str], destination: Path) -> tuple[list[Path], list[dict]]:
    """Copy only source files explicitly named by the selected mission loaders."""
    files, provenance = [], []
    for name in sorted(set(names)):
        direct = Path(name)
        candidates = [direct] if direct.is_file() else []
        if not candidates and (config.CACHE_DIR / name).is_file():
            candidates = [config.CACHE_DIR / name]
        if not candidates:
            candidates = sorted(config.CACHE_DIR.rglob(direct.name))
        if not candidates:
            raise RuntimeError(f"Named cached source is missing before snapshot: {name}")
        hashes = {sha256(p) for p in candidates}
        if len(hashes) != 1:
            raise RuntimeError(f"Ambiguous cached source versions: {name}")
        digest = next(iter(hashes))
        target = destination / f"source-{digest}"
        if not target.exists():
            shutil.copy2(candidates[0], target)
        if sha256(target) != digest:
            raise RuntimeError(f"Source snapshot changed during copy: {name}")
        files.append(target)
        provenance.append(
            {
                "declared_file": name,
                "original_path": str(candidates[0].resolve()),
                "snapshot": target.name,
                "sha256": digest,
            }
        )
    return files, provenance


def _mission_inputs(mission, window, protocol, out, attempt_id, binding, offline):
    manifest_path = out / f"{mission.key}-inputs-manifest.json"
    if manifest_path.exists():
        saved = _manifest(manifest_path, out, binding)
    else:
        folder = out / "inputs" / mission.key / attempt_id
        folder.mkdir(parents=True)
        orbit, record = reference.load_truth(
            mission,
            (window.sets_from - timedelta(days=protocol["calibration_lookback_days"] + 1)).date(),
            (window.truth_to + timedelta(hours=protocol["primary_lead_hours"])).date(),
            cache_dir=config.CACHE_DIR,
            offline=offline,
        )
        if record is None or not getattr(record, "authoritative", True) or record.days_missing:
            raise RuntimeError(f"{mission.key}: incomplete published record; experiment stops without dropping mission")
        if orbit is None or not len(orbit.table):
            raise RuntimeError(f"{mission.key}: no reference states; experiment stops without dropping mission")
        orbit_path, metadata_path = folder / "orbit.parquet", folder / "metadata.json"
        orbit.table.to_parquet(orbit_path, index=False)
        source_files, source_metadata = _source_snapshots([*orbit.files, *record.files], folder)
        _json(
            metadata_path,
            {
                "orbit": {
                    "letter": orbit.letter,
                    "norad_id": int(orbit.norad_id),
                    "frame": orbit.frame,
                    "days_missing": [d.isoformat() for d in orbit.days_missing],
                    "files": list(orbit.files),
                },
                "record": _record_snapshot(record),
                "cached_sources": source_metadata,
            },
        )
        saved = _commit(
            manifest_path,
            out,
            [orbit_path, metadata_path, *source_files],
            **binding,
            orbit_table=orbit_path.relative_to(out).as_posix(),
            metadata=metadata_path.relative_to(out).as_posix(),
        )
    # Even the initial attempt scores the persisted snapshots after hash checking.
    _manifest(manifest_path, out, binding)
    metadata = _read(out / saved["metadata"])
    values = metadata["orbit"]
    orbit = precise.PreciseOrbit(
        values["letter"],
        values["norad_id"],
        pd.read_parquet(out / saved["orbit_table"]),
        [date.fromisoformat(d) for d in values["days_missing"]],
        values["files"],
        values["frame"],
    )
    return orbit, _restore_record(metadata["record"]), sha256(manifest_path)


def association(events: list[dict]) -> dict:
    """Descriptive endpoint scores; no independent-trial p-value is asserted."""
    rows = [e for e in events if e.get("predicted_in_track_km") is not None and e.get("signed_in_track_km") is not None]
    x = np.array([e["predicted_in_track_km"] for e in rows], dtype=float)
    y = np.array([e["signed_in_track_km"] for e in rows], dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    x, y = x[finite], y[finite]
    out: dict[str, Any] = {"n_events": len(events), "n_complete": len(x), "n_unavailable": len(events) - len(x)}
    if not len(x):
        return out
    out.update(
        {
            "mean_absolute_error_prediction_km": float(np.mean(np.abs(y - x))),
            "mean_absolute_error_zero_km": float(np.mean(np.abs(y))),
            "median_absolute_error_prediction_km": float(np.median(np.abs(y - x))),
            "median_signed_prediction_error_km": float(np.median(y - x)),
            "sign_agreement_count": int((np.sign(x) == np.sign(y)).sum()),
            "sign_agreement_fraction": float(np.mean(np.sign(x) == np.sign(y))),
            "zero_predictor_or_endpoint_count": int(((x == 0) | (y == 0)).sum()),
            "slope_through_origin": float(x @ y / (x @ x)) if x @ x else None,
        }
    )
    if len(x) >= 2 and np.ptp(x) > 0 and np.ptp(y) > 0:
        regression = stats.linregress(x, y)
        out.update(
            {
                "pearson_r": float(regression.rvalue),
                "slope": float(regression.slope),
                "intercept_km": float(regression.intercept),
                "spearman_rho": float(stats.spearmanr(x, y).statistic),
            }
        )
    return out


def endpoint_report(events: list[dict]) -> dict:
    missions = sorted({e["mission"] for e in events})
    return {
        "all_recorded_burns": association(events),
        "without_intervening_recorded_burn": association([e for e in events if not e["later_burns"]]),
        "by_spacecraft": {m: association([e for e in events if e["mission"] == m]) for m in missions},
        "leave_one_spacecraft_out": {m: association([e for e in events if e["mission"] != m]) for m in missions},
        "leave_one_burn_out": {
            e["event_id"]: association([b for b in events if b["event_id"] != e["event_id"]]) for e in events
        },
        "interpretation": "Descriptive deletion sensitivity; repeated burns and spacecraft are correlated",
    }


def score_events(mission, orbit, record, sets: pd.DataFrame, window, protocol: dict) -> list[dict]:
    """Energy fraction and signed endpoint for every in-month recorded interval."""
    start, end = precise._naive(window.sets_from), precise._naive(window.sets_to)
    intervals = [(precise._naive(a), precise._naive(b)) for a, b in record.intervals]
    burns = [(a, b) for a, b in intervals if start <= a < end]
    orbit_detector = precise.manoeuvre_intervals_from_orbit(orbit)
    element_detector = precise.manoeuvre_intervals_from_sets(sets)
    period = int(round(2 * np.pi * np.sqrt((6378.137 + mission.altitude_km) ** 3 / 398600.4418) / 60))
    t, mean_a, period = precise.orbit_mean_semi_major_axis(orbit, period_min=period)
    rows = sets.sort_values("epoch").drop_duplicates("epoch", keep="last")
    rows = rows[
        rows["epoch"].between(window.sets_from - timedelta(days=protocol["calibration_lookback_days"]), window.truth_to)
    ]
    epochs = [precise._naive(e) for e in rows["epoch"]]
    a_sets = [precise.set_mean_semi_major_axis(row, period) if period else np.nan for _, row in rows.iterrows()]

    def epoch_mean(e):
        k = int(np.searchsorted(t, e.to_datetime64()))
        if not 0 < k < len(t):
            return np.nan
        if not np.isfinite(mean_a[k - 1 : k + 1]).all() or t[k] - t[k - 1] > np.timedelta64(90, "s"):
            return np.nan
        return precise._mean_a_at(t[k - 1 : k + 1], mean_a[k - 1 : k + 1], e)

    a_truth = [epoch_mean(e) for e in epochs]
    arc = pd.Timedelta(hours=protocol["exclusion_arc_hours"])
    plateau = pd.Timedelta(hours=protocol["plateau_hours"])
    revolution = pd.Timedelta(minutes=period)
    lead = protocol["primary_lead_hours"]

    def plateau_value(lo, hi):
        values = mean_a[(t >= lo.to_datetime64()) & (t <= hi.to_datetime64())]
        return float(np.nanmedian(values)) if np.isfinite(values).any() else np.nan

    events = []
    for lo, hi in burns:
        event = {
            "event_id": f"{mission.key}/{lo.isoformat()}",
            "mission": mission.key,
            "burn_from": lo.isoformat(),
            "burn_to": hi.isoformat(),
            "orbit_detector_missed": not precise._overlaps(orbit_detector, lo, hi),
            "element_detector_missed": not precise._overlaps(element_detector, lo, hi),
            "epoch": None,
            "fraction": None,
            "a_error_m": None,
            "missing_specific_energy_km2_s2": None,
            "predicted_in_track_km": None,
            "signed_in_track_km": None,
            "class": "unresolved",
            "later_burns": [],
            "unavailable_reasons": [],
        }
        clean = [
            s - o
            for e, s, o in zip(epochs, a_sets, a_truth, strict=True)
            if lo - pd.Timedelta(days=protocol["calibration_lookback_days"]) <= e
            and e + revolution < lo
            and np.isfinite(s)
            and np.isfinite(o)
            and not precise._overlaps(intervals, e - arc, e + revolution)
        ]
        offset = float(np.median(clean)) if clean else np.nan
        scatter = float(1.4826 * np.median(np.abs(np.asarray(clean) - offset))) if clean else np.nan
        event.update(
            {
                "n_clean_sets": len(clean),
                "calibration_offset_m": offset * 1000 if clean else None,
                "calibration_scatter_m": scatter * 1000 if clean else None,
            }
        )
        da = plateau_value(hi, hi + plateau) - plateau_value(lo - plateau, lo) if len(t) else np.nan
        event["delta_a_m"] = float(da * 1000) if np.isfinite(da) else None
        after = [k for k, e in enumerate(epochs) if e > hi]
        if not after:
            event["unavailable_reasons"].append("no set epoch after burn within the fixed search interval")
            events.append(event)
            continue
        k = after[0]
        epoch, s, o = epochs[k], a_sets[k], a_truth[k]
        target = epoch + pd.Timedelta(hours=lead)
        event.update(
            {
                "epoch": epoch.isoformat(),
                "propagation_age_hours": lead,
                "epoch_delay_after_burn_end_hours": (epoch - hi).total_seconds() / 3600,
                "target": target.isoformat(),
                "later_burns": [[a.isoformat(), b.isoformat()] for a, b in intervals if a > hi and a <= target],
            }
        )
        if len(clean) >= protocol["minimum_clean_sets"] and np.isfinite(s) and np.isfinite(o):
            error = s - offset - o
            fraction = 1 + error / da if np.isfinite(da) and da != 0 else np.nan
            event.update(
                {
                    "a_error_m": float(error * 1000),
                    "missing_specific_energy_km2_s2": float(398600.4418 / 2 * (1 / (s - offset) - 1 / o)),
                    "predicted_in_track_km": float(1.5 * np.sqrt(398600.4418 / o**3) * error * lead * 3600),
                    "fraction": float(fraction) if np.isfinite(fraction) else None,
                }
            )
            if np.isfinite(fraction) and abs(da) >= protocol["resolve_sigmas"] * scatter:
                event["class"] = (
                    "pre-manoeuvre-energy compatible"
                    if fraction <= protocol["fraction_pre"]
                    else "post-manoeuvre-energy compatible"
                    if fraction >= protocol["fraction_post"]
                    else "mixed"
                )
        else:
            event["unavailable_reasons"].append("insufficient prior clean calibration or missing epoch state")
        one = rows.iloc[[k]].reset_index(drop=True)
        at = np.array([target.to_datetime64()], dtype="datetime64[us]")
        state = propagate_satrecs(build_satrecs(one), one["norad_id"].to_numpy(), at)
        rt, vt, covered = orbit.states_teme(at)
        if (
            covered[0]
            and state.error[0, 0] == 0
            and np.isfinite(rt).all()
            and np.isfinite(vt).all()
            and np.isfinite(state.r_teme[0]).all()
        ):
            event["signed_in_track_km"] = float(to_ric(ric_basis(rt, vt), rt - state.r_teme[0])[0, 1])
        else:
            event["unavailable_reasons"].append("four-day reference gap or SGP4 error")
        events.append(event)
    return events


def _score_mission(mission, orbit, record, own_sets, window, protocol):
    """Unchanged numerical calculation, separated from resumable persistence."""
    inputs = precise.fit_inputs(
        mission.norad_id, own_sets, window, None, label=mission.key, category="payload", altitude_band="leo"
    )
    detected_orbit = precise.manoeuvre_intervals_from_orbit(orbit)
    detected_sets = precise.manoeuvre_intervals_from_sets(inputs.sets)
    trial = precise.satellite_trials(
        inputs,
        orbit,
        window,
        None,
        record=record,
        record_label=getattr(record, "source_id", mission.manoeuvres),
        detected=detected_orbit + detected_sets,
    )
    alt = reference_run.mean_altitude_km(inputs.trial_sets["mean_motion"].to_numpy(dtype=float))
    altitude_lookup = dict(zip([precise._naive(e) for e in inputs.trial_sets["epoch"]], alt, strict=True))
    trial["altitude_km"] = trial["set_epoch"].map(altitude_lookup)
    trial["mission"] = mission.key
    trial["altitude_band"] = reference.altitude_band_label(float(np.nanmedian(alt)))
    mission_events = score_events(mission, orbit, record, own_sets, window, protocol)
    coverage = {
        "orbit_days_missing": [d.isoformat() for d in orbit.days_missing],
        "orbit_files": orbit.files,
        "record": reference_run.record_provenance(record),
        "n_recorded_burns": len(mission_events),
        "orbit_detector_misses": sum(e["orbit_detector_missed"] for e in mission_events),
        "element_detector_misses": sum(e["element_detector_missed"] for e in mission_events),
    }
    return trial, mission_events, coverage


def execute(protocol_path: Path, out: Path, *, offline: bool = False, resume: bool = False) -> dict:
    """Run or explicitly resume the identical protocol from verified snapshots.

    Nothing is fetched on a verified completed mission or on a retry after its
    input snapshot commit. Uncommitted input/output attempts remain on disk.
    """
    protocol_path, out = Path(protocol_path).resolve(), Path(out).resolve()
    protocol = _read(protocol_path)
    attestation = _attestation(protocol, protocol_path)
    if not protocol.get("frozen_at"):
        raise RuntimeError("Protocol is not frozen")
    root = config.PROJECT_ROOT
    required_sources = {p.relative_to(root).as_posix() for p in (root / "src/driftwatch").rglob("*.py")}
    if not required_sources or set(protocol["source_hashes"]) != required_sources:
        raise RuntimeError("Frozen source manifest must cover every project Python source file")
    for filename, digest in protocol["source_hashes"].items():
        if sha256(root / filename) != digest:
            raise RuntimeError(f"Frozen code differs: {filename}; no data accessed")
    binding = {
        "protocol_sha256": sha256(protocol_path),
        "source_manifest_sha256": hashlib.sha256(
            json.dumps(protocol["source_hashes"], sort_keys=True).encode()
        ).hexdigest(),
        "attestation_sha256": hashlib.sha256(json.dumps(attestation, sort_keys=True).encode()).hexdigest(),
    }
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "first-data-access.json"
    if marker.exists():
        if not resume:
            raise RuntimeError("Locked execution already started; explicit resume=True is required")
        first = _read(marker)
        if any(first.get(k) != v for k, v in binding.items()):
            raise RuntimeError("Resume protocol, source or attestation differs from original first data access")
    else:
        if resume:
            raise RuntimeError("Cannot resume without an original first-data-access marker")
        first = {"started_at": datetime.now(UTC).isoformat(), **binding, "attestation": attestation}
        with marker.open("x", encoding="utf-8") as stream:
            json.dump(first, stream, indent=2)
    attempt_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:12]
    attempts = out / "attempts"
    attempts.mkdir(exist_ok=True)
    attempt_path = attempts / f"{attempt_id}.json"
    attempt = {
        "attempt_id": attempt_id,
        "started_at": datetime.now(UTC).isoformat(),
        "resume": resume,
        **binding,
        "first_data_access_sha256": sha256(marker),
        "status": "running",
        "stage": "gp_snapshot",
        "skipped_verified_missions": [],
        "completed_missions": [],
    }
    _json(attempt_path, attempt)
    try:
        window = precise.BenchmarkWindow(
            "september-locked",
            "held-out",
            datetime.fromisoformat(protocol["sets_from"]),
            datetime.fromisoformat(protocol["sets_to"]),
            None,
            protocol["calendar_rule"],
        )
        missions = [reference.MISSIONS[k] for k in protocol["missions"]]
        gp_manifest = out / "gp-input-manifest.json"
        if gp_manifest.exists():
            saved_gp = _manifest(gp_manifest, out, binding)
        else:
            folder = out / "inputs" / "gp" / attempt_id
            folder.mkdir(parents=True)
            all_sets = reference_run.load_sets(missions, [window])
            gp_path = folder / "gp.parquet"
            all_sets.to_parquet(gp_path, index=False)
            saved_gp = _commit(
                gp_manifest,
                out,
                [gp_path],
                **binding,
                table=gp_path.relative_to(out).as_posix(),
                n_rows=len(all_sets),
                captured_at=datetime.now(UTC).isoformat(),
            )
        _manifest(gp_manifest, out, binding)
        all_sets = pd.read_parquet(out / saved_gp["table"])
        binding = {**binding, "gp_manifest_sha256": sha256(gp_manifest)}
        # Verify ALL existing inputs/completions before fetching another mission.
        completed = {}
        for mission in missions:
            expected = {**binding, "mission": mission.key}
            input_manifest = out / f"{mission.key}-inputs-manifest.json"
            if input_manifest.exists():
                _manifest(input_manifest, out, expected)
            completion = out / f"{mission.key}-completion.json"
            if completion.exists():
                if not input_manifest.exists():
                    raise RuntimeError(f"Missing input manifest for completed mission {mission.key}")
                completed[mission.key] = _manifest(
                    completion, out, {**expected, "inputs_manifest_sha256": sha256(input_manifest)}
                )
        final_manifest = out / "completion-manifest.json"
        if final_manifest.exists():
            if len(completed) != len(missions):
                raise RuntimeError("Final completion does not contain every protocol mission")
            _manifest(
                final_manifest,
                out,
                {
                    **binding,
                    "mission_completion_sha256": {m.key: sha256(out / f"{m.key}-completion.json") for m in missions},
                },
            )
            result = _read(out / "locked_experiment.json")
            attempt.update(
                status="complete",
                stage="verified_complete",
                completed_at=datetime.now(UTC).isoformat(),
                skipped_verified_missions=[m.key for m in missions],
            )
            _json(attempt_path, attempt)
            return result
        frames, events, coverage = [], [], {}
        for mission in missions:
            attempt.update(stage="mission", mission=mission.key)
            _json(attempt_path, attempt)
            expected = {**binding, "mission": mission.key}
            if mission.key in completed:
                saved = completed[mission.key]
                attempt["skipped_verified_missions"].append(mission.key)
            else:
                log.info("Locked mission %s", mission.key)
                orbit, record, input_hash = _mission_inputs(
                    mission, window, protocol, out, attempt_id, expected, offline
                )
                own_sets = all_sets[all_sets["norad_id"].eq(mission.norad_id)]
                trial, mission_events, mission_coverage = _score_mission(
                    mission, orbit, record, own_sets, window, protocol
                )
                folder = out / "mission-results" / mission.key / attempt_id
                folder.mkdir(parents=True)
                trial_path, event_path, coverage_path = (
                    folder / "trials.parquet",
                    folder / "events.json",
                    folder / "coverage.json",
                )
                trial.to_parquet(trial_path, index=False)
                _json(event_path, mission_events)
                _json(coverage_path, mission_coverage)
                saved = _commit(
                    out / f"{mission.key}-completion.json",
                    out,
                    [trial_path, event_path, coverage_path],
                    **expected,
                    inputs_manifest_sha256=input_hash,
                    trials=trial_path.relative_to(out).as_posix(),
                    events=event_path.relative_to(out).as_posix(),
                    coverage=coverage_path.relative_to(out).as_posix(),
                    completed_at=datetime.now(UTC).isoformat(),
                )
                attempt["completed_missions"].append(mission.key)
            frames.append(pd.read_parquet(out / saved["trials"]))
            events.extend(_read(out / saved["events"]))
            coverage[mission.key] = _read(out / saved["coverage"])
            _json(attempt_path, attempt)
        attempt.update(stage="aggregation")
        _json(attempt_path, attempt)
        trials = pd.concat(frames, ignore_index=True)
        trials.to_parquet(out / "locked_trials.parquet", index=False)
        result = {
            "protocol": protocol,
            "protocol_sha256": sha256(protocol_path),
            "first_data_access": first,
            "gp_manifest_sha256": sha256(gp_manifest),
            "completed_at": datetime.now(UTC).isoformat(),
            "events": events,
            "coverage": coverage,
            "primary": endpoint_report(events),
            "secondary": reference_run.summarise_trials(trials),
            "mission_completion_sha256": {m.key: sha256(out / f"{m.key}-completion.json") for m in missions},
            "limitations": [
                "Epoch age is not publication age",
                "September GP and weather informed earlier October fits",
                "All recorded burns retained, including intervening burns and unavailable outcomes",
                "Registry completeness is not proved by empty event lists",
            ],
        }
        _json(out / "locked_experiment.json", result)
        _commit(
            final_manifest,
            out,
            [out / "locked_trials.parquet", out / "locked_experiment.json"],
            **binding,
            mission_completion_sha256=result["mission_completion_sha256"],
        )
        attempt.update(status="complete", stage="complete", completed_at=datetime.now(UTC).isoformat())
        _json(attempt_path, attempt)
        return result
    except BaseException as exc:
        attempt.update(
            status="failed", failed_at=datetime.now(UTC).isoformat(), error_type=type(exc).__name__, error=str(exc)
        )
        _json(attempt_path, attempt)
        raise
