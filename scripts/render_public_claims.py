"""Bind public benchmark claims to result slices and render their consumers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "docs/assets/benchmark-v2.json"
MANIFEST = ROOT / "docs/assets/claims-v2.json"


def sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def build_manifest(data, evidence_hash):
    claims = []
    labels = data["publication"]["windows"]
    names = {k: v["name"] for k, v in data["missions"].items()}
    component_counts = {
        mission: {
            window: {
                lead: {component: value["coverage"]["n"] for component, value in cell["components"].items()}
                for lead, cell in group["by_lead_h"].items()
            }
            for window, group in windows.items()
        }
        for mission, windows in data["results"]["by_mission"].items()
    }

    def add(key, path, result, population, denominator, censoring, text, reference="reconstructed orbit"):
        claims.append(
            {
                "id": key,
                "result_path": path,
                "result_hash": sha(result),
                "method_version": "benchmark-v2/truth-ric-covariance-v1",
                "population": population,
                "denominator": denominator,
                "reference_type": reference,
                "censoring_state": censoring,
                "permitted_wording": text,
                "review_state": "author review required; reopen on new evidence",
            }
        )

    pop = data["population"]
    add(
        "population",
        "population",
        pop,
        {"missions": pop["missions"], "windows": list(data["windows"])},
        {k: pop[k] for k in ("n_raw_sets", "n_usable_sets_any_lead", "n_usable_pairs")},
        "lead-dependent exclusions",
        f"{pop['n_missions']} spacecraft in {pop['n_bands']} altitude bands "
        f"across {pop['n_windows']} inspected windows; "
        f"{pop['n_raw_sets']:,} raw element sets, {pop['n_usable_sets_any_lead']:,} usable at some lead "
        f"and {pop['n_usable_pairs']:,} usable set/lead pairs. "
        "These are epoch-based reconstructions; historical publication availability is not established.",
    )
    definition = data["definition"]
    add(
        "horizon_criterion",
        "definition",
        definition,
        {"missions": pop["missions"], "windows": list(data["windows"])},
        {"unit": "finite usable residuals at each lead", "n_usable_set_lead_pairs": pop["n_usable_pairs"]},
        "failure, missing coverage and longest tested lead distinguished",
        f"A lead passes when at least {definition['quantile']:.0%} of finite usable absolute in-track residuals "
        f"are within {definition['tolerance_km']:g} km. Brackets are observed bins; passing through the longest "
        "tested lead is right censoring, not a guarantee beyond it.",
    )
    for band in sorted(data["results"]["by_band"], key=lambda b: int(b.split("-")[0])):
        for window in ("quiet", "storm", "august", "held-out"):
            g = data["results"]["by_band"][band][window]
            h = g["horizon"]
            last, first = h["last_lead_h_within"], h["first_lead_h_beyond"]
            if h["termination"] == "longest_tested_lead":
                text = f"passes through the longest tested lead ({h['longest_tested_lead_h']:g} h)"
            elif h["termination"] == "coverage_censored":
                text = (
                    f"{last:g} h last pass; unavailable at {h['stopped_at_lead_h']:g} h"
                    if last is not None
                    else f"unavailable at {h['stopped_at_lead_h']:g} h"
                )
            else:
                text = (
                    f"{last:g} h pass / {first:g} h fail"
                    if last is not None
                    else f"fails at first tested lead ({first:g} h)"
                )
            endpoint = (
                g["by_lead_h"][f"{last:g}"] if last is not None else g["by_lead_h"][f"{h['stopped_at_lead_h']:g}"]
            )
            composition = "; ".join(f"{names[m]}: {n}" for m, n in endpoint["mission_counts"].items()) or "none"
            add(
                f"horizon:{band}:{window}",
                f"results/by_band/{band}/{window}",
                g,
                {"band": band, "window": window, "window_label": labels[window], "missions": g["missions"]},
                {
                    "by_lead_h": {lead: c["n"] for lead, c in g["by_lead_h"].items()},
                    "last_pass_n": endpoint["n"],
                    "last_pass_composition": composition,
                },
                h["termination"],
                text,
            )
    overview = data["results"]["by_band"]["400-600 km"]
    low = [c for c in claims if c["id"].startswith("horizon:400-600 km:")]
    text = "; ".join(f"{c['population']['window_label']}: {c['permitted_wording']}" for c in low)
    add(
        "horizon_overview",
        "results/by_band/400-600 km",
        overview,
        {"missions": sorted({m for g in overview.values() for m in g["missions"]}), "band": "400-600 km"},
        {w: {h: c["n"] for h, c in g["by_lead_h"].items()} for w, g in overview.items()},
        "observed brackets; no transfer to demo fleet",
        "Measured low-altitude reference population — "
        + text
        + ". These descriptive brackets do not calibrate another object or an operational probability.",
    )
    diag = data["results"]["by_mission"]
    add(
        "consistency",
        "results/by_mission",
        diag,
        {"missions": pop["missions"], "windows": list(data["windows"])},
        {"unit": "valid residual/sigma pairs", "by_mission_window_lead_component": component_counts},
        "measured cells only",
        "Consistency covariance bounds absolute accuracy in neither direction. Component coverage varies by "
        "mission, window and lead; storm residuals and Sentinel-6A in April 2024 control expose undercoverage. "
        "Storm output is a sensitivity analysis on the baseline event set; candidate discovery is not repeated.",
    )
    learned = data["publication"]["learned"]
    add(
        "learned",
        "publication/learned",
        learned,
        {"models": list(data["extras"]["dsgp4"]["result"]["training"]), "windows": ["august", "held-out"]},
        {"model_window_lead_cells": learned["n_cells"]},
        "inspected evaluation population",
        "Both local learned-propagator checkpoints remain negative findings: "
        f"{learned['n_lower_median']}/{learned['n_cells']} pooled paired medians improve; "
        f"{learned['n_lower_tail']}/{learned['n_cells']} tails improve. "
        "The stored adoption rule rejects both checkpoints.",
    )
    events = data["publication"]["september_events"]
    primary = data["extras"]["locked"]["result"]["primary"]["all_recorded_burns"]
    add(
        "september",
        "publication/september_events",
        events,
        {"missions": sorted({e["mission"] for e in events}), "window": "september-locked"},
        {
            "recorded_burns": primary["n_events"],
            "complete": primary["n_complete"],
            "unavailable": primary["n_unavailable"],
        },
        "complete endpoints; dependent events",
        "September retrospective physical diagnostic: prediction MAE "
        f"{primary['mean_absolute_error_prediction_km']:.3f} km versus "
        f"{primary['mean_absolute_error_zero_km']:.3f} km for zero prediction. "
        f"{data['publication']['n_beats_zero']}/{primary['n_complete']} events beat zero; "
        "SWOT and one Sentinel-3A event do not. September will not be reused as a hold-out for any new recipe.",
    )
    for key, value in data["publication"]["radio_strata"].items():
        add(
            "radio:" + key,
            "publication/radio_strata/" + key,
            value,
            {"construction": key, "windows": list(data["windows"]), "observation": "full"},
            {k: value[k] for k in ("n_cases", "n_trials", "predicted", "reference", "n_closest")},
            "nominal visibility and finite full curves required",
            f"{key}: crossing agreement {value['agreement_count']}/{value['n_cases']} "
            f"({value['agreement_fraction']:.1%}); false crossings {value['false']}/{value['predicted']}; "
            f"missed crossings {value['missed']}/{value['reference']}. Constructed pointings on inspected windows; "
            "measured beams are CC BY-NC and used for research only.",
            "constructed topocentric comparison against reconstructed orbit",
        )
    for key, wording in {
        "applicability:eligible": (
            "Reference-mission component diagnostic for the stated window, lead and manoeuvre-excluded "
            "public-GP scope. No calibrated beam-crossing or operating guarantee."
        ),
        "applicability:unsupported": (
            "Unsupported: identity, reference coverage, measured age or manoeuvre-excluded scope is not "
            "established. Altitude overlap alone does not transfer calibration."
        ),
    }.items():
        add(
            key,
            "results",
            data["results"],
            {"missions": pop["missions"], "windows": list(data["windows"])},
            {"unit": "valid residual/sigma pairs", "by_mission_window_lead_component": component_counts},
            "only measured eligible cells",
            wording,
        )
    return {
        "schema_version": "public-claims-v1",
        "evidence_object": "docs/assets/benchmark-v2.json",
        "evidence_sha256": evidence_hash,
        "method_version": "benchmark-v2/truth-ric-covariance-v1",
        "claims": claims,
    }


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(map(str, row)) + " |" for row in rows),
        ]
    )


def render(manifest):
    claims = {c["id"]: c for c in manifest["claims"]}
    horizon = table(
        ["Band", "Window", "Observed endpoints", "Usable n at last pass", "Composition at last pass"],
        [
            [
                c["population"]["band"],
                c["population"]["window_label"],
                c["permitted_wording"],
                c["denominator"]["last_pass_n"],
                c["denominator"]["last_pass_composition"],
            ]
            for c in manifest["claims"]
            if c["id"].startswith("horizon:")
        ],
    )
    numbers = "\n\n".join(
        claims[k]["permitted_wording"]
        for k in (
            "population",
            "consistency",
            "learned",
            "september",
            "radio:Other declared offsets",
            "radio:Exact boundary offsets",
        )
    )
    section = (
        claims["population"]["permitted_wording"]
        + "\n\n"
        + claims["horizon_criterion"]["permitted_wording"]
        + "\n\n"
        + horizon
        + "\n\n"
        + claims["applicability:unsupported"]["permitted_wording"]
    )
    output = {}
    for name, marker, content in (("README.md", "horizons", section), ("ROADMAP.md", "results", numbers)):
        text = (ROOT / name).read_text(encoding="utf-8")
        pattern = rf"<!-- BEGIN CLAIMS:{marker} -->.*?<!-- END CLAIMS:{marker} -->"
        replacement = f"<!-- BEGIN CLAIMS:{marker} -->\n{content}\n<!-- END CLAIMS:{marker} -->"
        if not re.search(pattern, text, re.S):
            raise ValueError(f"Missing managed claims region in {name}")
        output[name] = re.sub(pattern, lambda _, replacement=replacement: replacement, text, flags=re.S)
    output["docs/findings.md"] = (
        "# Current benchmark findings\n\n"
        + numbers
        + "\n\n"
        + horizon
        + "\n\nThe [claims manifest](assets/claims-v2.json) binds every result above to its population, "
        "denominator, reference, censoring state and permitted wording. [Paper](paper.md); "
        "[complete tables](benchmark-v2-tables.md); "
        "[dated covariance correction, every cell](covariance-basis-correction.md).\n"
    )
    output["docs/reference-benchmark.md"] = (
        "# Reference benchmark\n\n"
        + section
        + "\n\n[Paper](paper.md) and [complete denominators, deletion checks and tables](benchmark-v2-tables.md).\n"
    )
    output["docs/calibration-benchmark.md"] = (
        "# Component calibration\n\n"
        + claims["consistency"]["permitted_wording"]
        + "\n\n"
        + claims["population"]["permitted_wording"]
        + "\n\n[Current component coverage](benchmark-v2-tables.md#component-residuals-and-covariance-coverage); "
        "[every covariance-basis change](covariance-basis-correction.md).\n"
    )
    output["docs/applicability.md"] = (
        "# Benchmark applicability\n\n"
        + "\n\n".join(claims[k]["permitted_wording"] for k in ("applicability:eligible", "applicability:unsupported"))
        + "\n\nEvidence: [claims manifest](assets/claims-v2.json).\n"
    )
    output["src/driftwatch/public_claims.json"] = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    output["web/src/claims.generated.ts"] = (
        "// Generated by scripts/render_public_claims.py; edit the evidence or manifest renderer.\n"
        "export const PUBLIC_CLAIMS = "
        + json.dumps(manifest, indent=2, allow_nan=False)
        + " as const;\n"
        + "\n".join(
            f"export const {constant} = "
            f"PUBLIC_CLAIMS.claims[{next(i for i, c in enumerate(manifest['claims']) if c['id'] == key)}]"
            ".permitted_wording;"
            for constant, key in (
                ("HORIZON_HEADLINE", "horizon_overview"),
                ("STORM_CALIBRATION_NOTE", "consistency"),
                ("STORM_CALIBRATION_SHORT", "consistency"),
                ("APPLICABILITY_ELIGIBLE", "applicability:eligible"),
                ("APPLICABILITY_UNSUPPORTED", "applicability:unsupported"),
            )
        )
        + "\n"
    )
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    manifest = build_manifest(data, hashlib.sha256(CANONICAL.read_bytes()).hexdigest())
    outputs = {"docs/assets/claims-v2.json": json.dumps(manifest, indent=2, allow_nan=False) + "\n", **render(manifest)}
    for name, text in outputs.items():
        if args.check:
            if (ROOT / name).read_text(encoding="utf-8") != text:
                raise ValueError(f"Stale public claims: {name}")
        else:
            (ROOT / name).write_text(text, encoding="utf-8")
    print(f"{'Verified' if args.check else 'Rendered'} {len(manifest['claims'])} claims across {len(outputs)} files")


if __name__ == "__main__":
    main()
