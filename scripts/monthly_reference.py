"""Protocol-first monthly reference comparisons using the immutable v2 method."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

FROZEN_COMMIT = "fedc1bc7f398edf6bbff4b8c066f95c8f2865cd9"
METHOD = "benchmark-v2/truth-ric-covariance-v1"
LEADS = [6, 12, 24, 36, 48, 72, 96, 120, 144, 168]
POPULATION = [
    "swarm-a",
    "swarm-b",
    "swarm-c",
    "gracefo-c",
    "gracefo-d",
    "sentinel-1a",
    "cryosat-2",
    "saral",
    "sentinel-3a",
    "sentinel-3b",
    "swot",
    "hy-2c",
    "hy-2d",
    "jason-3",
    "sentinel-6a",
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write_new(path, value):
    """Exclusive creation: reruns cannot silently change a protocol or result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def completed_months(now, limit=12):
    end = now.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(limit):
        start = (end - timedelta(days=1)).replace(day=1)
        yield start, end
        end = start


def protocol(now, start, end):
    return {
        "schema_version": "monthly-reference-protocol-v1",
        "written_at": now.isoformat(),
        "month": start.strftime("%Y-%m"),
        "method_version": METHOD,
        "method_commit": FROZEN_COMMIT,
        "candidate_population": POPULATION,
        "population_rule": "All named missions with reconstructed orbit coverage over the declared truth interval; "
        "availability is decided before residuals. Unknown provider availability is recorded separately.",
        "window": {
            "sets_from": start.isoformat(),
            "sets_to_exclusive": end.isoformat(),
            "truth_from": (start - timedelta(days=1)).isoformat(),
            "truth_to": (end + timedelta(hours=169)).isoformat(),
        },
        "endpoint": {
            "component": "absolute in-track residual",
            "quantile": 0.95,
            "tolerance_km": 25.0,
            "leads_hours": LEADS,
            "rule": "inside_tolerance_count >= 0.95 * n_finite_usable_residuals",
        },
        "rules": {
            "baseline": "unmodified SGP4; residual and transported covariance in truth RIC",
            "covariance_history_days": 45,
            "fit_cutoff": start.isoformat(),
            "exclusions": "Frozen v2 gaps, SGP4 errors, manoeuvre records and tracking-arc rules; "
            "missing manoeuvre coverage fails the run rather than becoming a no-burn history.",
            "summary": "Frozen empirical coverage, linear and inverted-CDF quantiles, complete planned lead grid, "
            "spacecraft and element-set deletion sensitivity; dependent trials remain descriptive.",
            "censoring": "First failure, missing coverage and passing through the longest tested lead are distinct.",
            "availability": "Epoch-based reconstruction; historical publication availability is not established.",
            "scope": "Reference comparison only; no storm term, radio, learned model, SLR or recipe adoption.",
            "selection": "Newest completed UTC calendar month with any eligible mission; search at most twelve "
            "months, fail if none. Never select on residuals or replace failed scoring cells.",
        },
    }


def prepare(root, out, now, probe):
    """Only probe coverage, never scores. A protocol exists before each probe."""
    run_stamp = now.strftime("%Y-%m-%dT%H%M%S%fZ")
    index_path = root / "docs/assets/claims-versions.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for start, end in completed_months(now):
        version = "monthly-" + start.strftime("%Y-%m")
        if any(v["version"] == version for v in index["versions"]):
            return {"status": "already_recorded", "version": version}
        folder = root / "docs/assets/monthly" / run_stamp
        path = folder / (version + "-protocol.json")
        record = protocol(now, start, end)
        write_new(path, record)
        coverage = probe(record)
        if set(coverage) != set(POPULATION):
            raise ValueError("Availability must account for every named mission")
        eligible = [m for m in POPULATION if coverage[m]["state"] == "available"]
        selection = {
            "protocol": path.relative_to(root).as_posix(),
            "protocol_sha256": digest(path),
            "coverage": coverage,
            "population": eligible,
            "version": version,
            "status": "ready" if eligible else "no_complete_orbit",
        }
        selection_path = folder / (version + "-population.json")
        write_new(selection_path, selection)
        if eligible:
            selected = {
                "status": "ready",
                "selection": selection_path.relative_to(root).as_posix(),
                "selection_sha256": digest(selection_path),
            }
            write_new(out / "selected.json", selected)
            return selected
        if any(v["state"] == "unknown" for v in coverage.values()):
            raise ValueError("Cannot establish the newest available month: provider availability is unknown")
    raise ValueError("No completed month has reconstructed coverage within the declared search bound")


def load_selection(root, selected):
    path = root / selected["selection"]
    if digest(path) != selected["selection_sha256"]:
        raise ValueError("Population record changed after preparation")
    selection = json.loads(path.read_text(encoding="utf-8"))
    protocol_path = root / selection["protocol"]
    if digest(protocol_path) != selection["protocol_sha256"]:
        raise ValueError("Protocol changed before residual access")
    record = json.loads(protocol_path.read_text(encoding="utf-8"))
    expected = protocol(
        datetime.fromisoformat(record["written_at"]),
        datetime.fromisoformat(record["window"]["sets_from"]),
        datetime.fromisoformat(record["window"]["sets_to_exclusive"]),
    )
    if record != expected or not selection["population"]:
        raise ValueError("Protocol differs from the frozen monthly rules")
    return record, selection


def bind_frozen_method(path):
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"], text=True
    )
    if actual != FROZEN_COMMIT or dirty:
        raise ValueError("Monthly comparison requires a clean checkout of the frozen method commit")
    sys.path.insert(0, str(path / "src"))
    from driftwatch.storm import precise

    if not Path(precise.__file__).resolve().is_relative_to(path.resolve()):
        raise ValueError("Imported method is not from the frozen checkout")
    return {"commit": actual, "dependency_lock_sha256": digest(path / "uv.lock")}


def make_window(record):
    from driftwatch.storm.precise import BenchmarkWindow

    w = record["window"]
    return BenchmarkWindow(
        record["month"],
        "rolling",
        datetime.fromisoformat(w["sets_from"]),
        datetime.fromisoformat(w["sets_to_exclusive"]),
        None,
        "Monthly epoch-based reconstruction under the frozen v2 method",
    )


def probe_orbits(record):
    from driftwatch import config
    from driftwatch.storm import reference

    w = record["window"]
    start, end = datetime.fromisoformat(w["truth_from"]), datetime.fromisoformat(w["truth_to"])
    coverage = {}
    for key in POPULATION:
        try:
            orbit, _ = reference.load_truth(
                reference.MISSIONS[key], start.date(), end.date(), cache_dir=config.CACHE_DIR, records=True
            )
            full = orbit is not None and len(orbit.table) and not orbit.days_missing
            if full:
                full = (
                    orbit.table.t.min().to_pydatetime().replace(tzinfo=UTC) <= start
                    and orbit.table.t.max().to_pydatetime().replace(tzinfo=UTC) >= end
                )
            coverage[key] = {
                "state": "available" if full else "incomplete",
                "n_states": 0 if orbit is None else len(orbit.table),
                "days_missing": [] if orbit is None else [d.isoformat() for d in orbit.days_missing],
            }
        except Exception as exc:
            # Provider exception messages can contain account or machine information.
            coverage[key] = {"state": "unknown", "error_type": type(exc).__name__}
        print(f"Orbit availability: {key}: {coverage[key]['state']}", flush=True)
    return coverage


def score(record, selection):
    from driftwatch import config
    from driftwatch.catalogue import history
    from driftwatch.storm import precise, reference, reference_run

    window = make_window(record)
    missions = [reference.MISSIONS[k] for k in selection["population"]]
    # Acquisition occurs after the protocol; actual retrieval time is used by backfill.
    history.backfill(
        [m.norad_id for m in missions],
        end=window.truth_to,
        days=(window.truth_to - window.sets_from).days + precise.COVARIANCE_HISTORY_DAYS + 2,
        use_stored=False,
        predicates=None,
    )
    result = reference_run.run_reference(missions, [window], grid=None, offline=True, with_slr=False)
    if result.summary["execution"]["failed_mission_windows"]:
        raise ValueError("Scoring failed for a declared mission; no monthly claim may be published")
    if not len(result.trials) or set(result.trials.mission) != set(selection["population"]):
        raise ValueError("A declared mission has no trial sets; no monthly claim may be published")
    inventory = [
        {
            "source_identifier": "provider-cache:" + p.relative_to(config.CACHE_DIR).as_posix(),
            "content_sha256": digest(p),
        }
        for p in sorted(config.CACHE_DIR.rglob("*"))
        if p.is_file()
    ]
    return result, inventory


def evidence_record(result, record, selection, sources, method):
    import numpy as np

    trials = result.trials
    usable = trials[~trials.gap & ~trials.manoeuvre & trials.sgp4_error.eq(0) & np.isfinite(trials.in_track_km)]
    keys = ["mission", "window", "set_epoch"]
    results = {k: result.summary["results"][k] for k in ("by_band", "by_mission")}
    definition = next(iter(next(iter(results["by_band"].values())).values()))["definition"]
    return {
        "schema_version": "benchmark-v2-reference-monthly-v1",
        "version": selection["version"],
        "built_at": result.built_at.isoformat(),
        "method_version": METHOD,
        "frozen_method": method,
        "protocol": {"path": selection["protocol"], "sha256": selection["protocol_sha256"]},
        "windows": result.summary["windows"],
        "missions": result.summary["missions"],
        "definition": definition,
        "population": {
            "missions": sorted(trials.mission.unique()),
            "n_missions": int(trials.mission.nunique()),
            "n_windows": 1,
            "n_bands": int(trials.altitude_band.nunique()),
            "n_raw_sets": len(trials[keys].drop_duplicates()),
            "n_usable_sets_any_lead": len(usable[keys].drop_duplicates()),
            "n_raw_pairs": len(trials),
            "n_usable_pairs": len(usable),
            "minimum_altitude_km": float(trials.altitude_km.min()),
            "maximum_altitude_km": float(trials.altitude_km.max()),
        },
        "availability": selection["coverage"],
        "reconstruction": record["rules"]["availability"],
        "results": results,
        "inputs": sources,
    }


def claims_for(data, evidence_path, evidence_hash):
    claims = []
    for band, windows in data["results"]["by_band"].items():
        for month, result in windows.items():
            h = result["horizon"]
            if h["termination"] == "longest_tested_lead":
                wording = f"passes through the longest tested lead ({h['longest_tested_lead_h']:g} h)"
            elif h["termination"] == "coverage_censored":
                wording = f"coverage censored at {h['stopped_at_lead_h']:g} h"
            elif h["last_lead_h_within"] is None:
                wording = f"fails at the first tested lead ({h['first_lead_h_beyond']:g} h)"
            else:
                wording = f"{h['last_lead_h_within']:g} h pass / {h['first_lead_h_beyond']:g} h fail"
            claims.append(
                {
                    "id": f"horizon:{band}:{month}",
                    "result_path": f"results/by_band/{band}/{month}",
                    "result_hash": value_hash(result),
                    "method_version": METHOD,
                    "population": {"missions": result["missions"], "band": band, "window": month},
                    "denominator": {lead: cell["n"] for lead, cell in result["by_lead_h"].items()},
                    "reference_type": "reconstructed orbit",
                    "censoring_state": h["termination"],
                    "permitted_wording": wording,
                }
            )
    return {
        "schema_version": "public-claims-v1",
        "version": data["version"],
        "method_version": METHOD,
        "evidence_object": evidence_path,
        "evidence_sha256": evidence_hash,
        "claims": claims,
    }


def render_tables(data, claims):
    lines = [
        "# Monthly reference comparison — " + data["version"],
        "",
        "Epoch-based reconstruction under the frozen v2 method. Trials are dependent; deletion checks are descriptive.",
        "",
        "| Band | Window | Observed endpoints |",
        "| --- | --- | --- |",
    ]
    for c in sorted(claims["claims"], key=lambda c: int(c["population"]["band"].split("-")[0])):
        lines.append(f"| {c['population']['band']} | {c['population']['window']} | {c['permitted_wording']} |")
    lines += [
        "",
        "## Component residuals and covariance coverage",
        "",
        "| Scope | Population | Window | Lead h | Component | Usable n | Median absolute km | "
        "p95 linear km | p95 inverted CDF km | Coverage n | Inside 1 sigma | Inside 2 sigma |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scope, populations in data["results"].items():
        for population, windows in populations.items():
            for window, group in windows.items():
                for lead, cell in group["by_lead_h"].items():
                    for component, value in cell["components"].items():
                        coverage = value["coverage"] or {}
                        row = [
                            scope,
                            population,
                            window,
                            lead,
                            component,
                            cell["n"],
                            value["median_abs_km"],
                            value["quantile_abs_km"]["linear"],
                            value["quantile_abs_km"]["inverted_cdf"],
                            coverage.get("n"),
                            coverage.get("inside_1_sigma_fraction"),
                            coverage.get("inside_2_sigma_fraction"),
                        ]
                        lines.append("| " + " | ".join("unavailable" if x is None else str(x) for x in row) + " |")
    lines += [
        "",
        "## Deletion sensitivity",
        "",
        "| Band | Window | Deleted spacecraft | Criterion | Last pass h | First fail h | Censoring |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for band, windows in data["results"]["by_band"].items():
        for window, group in windows.items():
            for mission, criteria in group["sensitivities"]["leave_one_spacecraft_out"].items():
                for criterion, h in criteria.items():
                    lines.append(
                        f"| {band} | {window} | {mission} | {criterion} | "
                        f"{h['last_lead_h_within']} | {h['first_lead_h_beyond']} | {h['termination']} |"
                    )
    lines += ["", "| Band | Window | Whole-set deletions | Changed brackets |", "| --- | --- | ---: | ---: |"]
    for band, windows in data["results"]["by_band"].items():
        for window, group in windows.items():
            s = group["sensitivities"]["leave_one_set_out"]
            lines.append(f"| {band} | {window} | {s['n_deletions']} | {s['n_changed']} |")
    lines += [
        "",
        "| Band | Window | Lead h | Component | Baseline n | Baseline 2 sigma | "
        "Set deletion min | Set deletion max | Undefined deletions |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for band, windows in data["results"]["by_band"].items():
        for window, group in windows.items():
            for lead, components in group["sensitivities"]["component_coverage"]["by_lead_h"].items():
                for component, values in components.items():
                    b, s = values["baseline"], values["leave_one_set_out"]
                    lines.append(
                        f"| {band} | {window} | {lead} | {component} | {b['n']} | "
                        f"{b['inside_2_sigma_fraction']} | {s['min_fraction']} | {s['max_fraction']} | "
                        f"{s['n_undefined']} |"
                    )
    lines += [
        "",
        "Each individual changed set and spacecraft component deletion is retained at full precision "
        "in the accompanying evidence object.",
    ]
    return "\n".join(lines) + "\n"


def append_version(index_path, entry):
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if any(v["version"] == entry["version"] for v in index["versions"]):
        raise ValueError("Claims version already exists; never overwrite a monthly or v2 record")
    index["versions"].append(entry)
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8", newline="\n")


def execute(root, out, selected, method, scorer=score):
    record, selection = load_selection(root, selected)  # Must precede every residual read.
    result, sources = scorer(record, selection)
    data = evidence_record(result, record, selection, sources, method)
    folder = root / "docs/assets/monthly" / selection["version"]
    evidence_path = folder / "evidence.json"
    out.mkdir(parents=True, exist_ok=True)
    trial_path = out / (selection["version"] + "-trials.parquet")
    result.trials.to_parquet(trial_path, index=False)
    data["derived_trials"] = {
        "asset": trial_path.name,
        "sha256": digest(trial_path),
        "actions_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    write_new(evidence_path, data)
    relative = evidence_path.relative_to(root).as_posix()
    claims = claims_for(data, relative, digest(evidence_path))
    claims_path = folder / "claims.json"
    write_new(claims_path, claims)
    tables_path = folder / "tables.md"
    with tables_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(render_tables(data, claims))
    append_version(
        root / "docs/assets/claims-versions.json",
        {
            "version": selection["version"],
            "method_version": METHOD,
            "evidence_object": relative,
            "evidence_sha256": digest(evidence_path),
            "claims_manifest": claims_path.relative_to(root).as_posix(),
            "claims_sha256": digest(claims_path),
            "tables": tables_path.relative_to(root).as_posix(),
            "tables_sha256": digest(tables_path),
            "protocol": selection["protocol"],
            "protocol_sha256": selection["protocol_sha256"],
        },
    )
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    parser.add_argument("--frozen-root", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("output/monthly"))
    args = parser.parse_args()
    method = bind_frozen_method(args.frozen_root.resolve())
    if args.phase == "prepare":
        selected = prepare(args.root, args.out, datetime.now(UTC), probe_orbits)
        print(json.dumps(selected))
    elif (args.out / "selected.json").exists():
        selected = json.loads((args.out / "selected.json").read_text())
        execute(args.root, args.out, selected, method)
    else:
        raise ValueError("Missing selected population; no residuals may be accessed")


if __name__ == "__main__":
    main()
