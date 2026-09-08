"""Scalar evidence substitutions for human-authored Markdown; no prose generation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"\{\{([^{}]+)\}\}")
NUMBER = re.compile(r"(?<![\w])[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")


def enrich(data, trials):
    metadata_path = ROOT / "docs/publication-metadata.json"
    p = json.loads(metadata_path.read_text(encoding="utf-8"))
    frozen_markdown = ROOT / p["frozen_protocol_markdown_path"]
    assert (
        hashlib.sha256(frozen_markdown.read_bytes()).hexdigest()
        == data["protocols"]["locked_protocol"]["result"]["method_markdown"]["sha256"]
    )
    p["windows"] = p.pop("window_labels")
    low = trials[trials.altitude_band.eq("400-600 km")]
    p["low_altitude_min_km"] = float(low.altitude_km.min())
    p["low_altitude_max_km"] = float(low.altitude_km.max())
    p["high_band_boundary_km"] = min(
        int(k.split("-")[0]) for k in data["results"]["by_band"] if int(k.split("-")[0]) >= 850
    )
    p["low_horizons"] = {w: g["horizon"] for w, g in data["results"]["by_band"]["400-600 km"].items()}
    p["longest_lead_h"] = max(data["definition"]["leads_hours"])
    p["correction_date"] = data["covariance_basis_correction"]["corrected_at"][:10]
    p["sigma_multiple"] = max(data["definition"]["covariance_multiples"])
    p["calibration_lead_h"] = data["discrepancy_diagnostics"]["selection"]["day_lead_h"]
    events = data["extras"]["locked"]["result"]["events"]
    p["september_events"] = []
    for e in events:
        predicted, observed = e["predicted_in_track_km"], e["signed_in_track_km"]
        p["september_events"].append(
            {
                **e,
                "event_date": e["burn_from"][:10],
                "absolute_prediction_error_km": abs(predicted - observed),
                "absolute_zero_error_km": abs(observed),
                "beats_zero": abs(predicted - observed) < abs(observed),
            }
        )
    p["n_beats_zero"] = sum(e["beats_zero"] for e in p["september_events"])
    p["baseline_failures"] = [e for e in p["september_events"] if not e["beats_zero"]]
    p["gracefo_d"] = next(e for e in p["september_events"] if e["mission"] == "gracefo-d")
    p["swot"] = next(e for e in p["september_events"] if e["mission"] == "swot")
    p["sentinel3a_failure"] = next(e for e in p["baseline_failures"] if e["mission"] == "sentinel-3a")
    result = data["extras"]["dsgp4"]["result"]
    paired = data["extras"]["dsgp4_paired"]["result"]["rows"]
    evaluated = [
        r
        for r in paired
        if r["scope"] == "pooled" and r["method"] in result["training"] and r["window"] in result["held_out_windows"]
    ]
    p["learned"] = {
        "n_models": len(result["training"]),
        "n_cells": len(evaluated),
        "n_lower_median": sum(r["median_improvement"] is not None and r["median_improvement"] > 0 for r in evaluated),
        "n_lower_tail": sum(r["method_p95_abs_in_track_km"] < r["plain_p95_abs_in_track_km"] for r in evaluated),
    }
    cases_path = ROOT / "data/radio/track_benchmark_v2_complete/radio_track_cases.csv"
    cases = pd.read_csv(cases_path)
    assert len(cases) == data["extras"]["radio_tracks"]["result"]["n_cases"]
    full = cases[cases.observation.eq("full")]

    def radio_group(g):
        valid = g[~g.prediction_closest_time_censored & ~g.reference_closest_time_censored]
        times = valid.closest_time_error_s.to_numpy()
        times = np.abs(times[np.isfinite(times)])
        return {
            "n_cases": len(g),
            "n_trials": int(g.trial_id.nunique()),
            "agreement_count": int((g.both_crossed | g.true_negative).sum()),
            "agreement_fraction": float((g.both_crossed | g.true_negative).mean()) if len(g) else None,
            "false": int(g.false_crossing.sum()),
            "predicted": int(g.prediction_observation_crossed.sum()),
            "missed": int(g.missed_crossing.sum()),
            "reference": int(g.reference_observation_crossed.sum()),
            "n_closest": len(times),
            "median_abs_closest_s": float(np.median(times)) if len(times) else None,
            "q95_abs_closest_s": float(np.quantile(times, 0.95)) if len(times) else None,
        }

    p["radio_by_age"] = []
    strata = {
        "Other declared offsets": full[~full.offset_fraction.abs().eq(1)],
        "Exact boundary offsets": full[full.offset_fraction.abs().eq(1)],
    }
    p["radio_strata"] = {name: radio_group(g) for name, g in strata.items()}
    for name, group in strata.items():
        for lead in data["definition"]["leads_hours"]:
            g = group[group.lead_h.eq(lead)]
            p["radio_by_age"].append({"lead_h": float(lead), "stratum": name, **radio_group(g)})
    data["publication"] = p
    correction = ROOT / "data/validation/covariance-basis-correction-2026-09-08"
    audit_files = [
        correction / filename
        for filename in (
            "reference-original.parquet",
            "reference-trials.parquet",
            "reference-bases.npz",
            "september-trials.parquet",
            "september-bases.npz",
        )
    ]
    for path in (
        metadata_path,
        cases_path,
        frozen_markdown,
        ROOT / "docs/paper.template.md",
        Path(__file__),
        *audit_files,
    ):
        data["inputs"].append(
            {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
    return data


def resolve(data, path):
    value = data
    for key in path.split("/"):
        value = value[int(key)] if isinstance(value, list) else value[key]
    if isinstance(value, (dict, list)):
        raise ValueError(f"Prose substitutions must be scalars: {path}")
    return value


def scalar(data, token, evidence_hash):
    if token == "evidence_sha256":
        return evidence_hash
    path, *format_spec = token.split("|")
    value = resolve(data, path)
    if value is None:
        return "unavailable"
    return format(value, format_spec[0]) if format_spec else str(value)


def render_template(template, data, tables, evidence_hash):
    def substitute(match):
        token = match[1]
        return tables[token[6:]] if token.startswith("table:") else scalar(data, token, evidence_hash)

    return TOKEN.sub(substitute, template).strip() + "\n"


def validate_numeric_prose(template, rendered, data, tables, evidence_hash):
    # All figures in authored prose must be explicit evidence substitutions.
    literal = TOKEN.sub("", template)
    literal = re.sub(r"\]\([^)]*\)", "]", literal)
    if NUMBER.search(literal):
        raise ValueError(f"Literal figure lacks an evidence substitution: {NUMBER.search(literal)[0]}")
    expected = render_template(template, data, tables, evidence_hash)
    if rendered != expected:
        raise ValueError("Paper differs from its authored template and current evidence substitutions")
    # Resolve every scalar, including metadata identifiers; no free numeric allowlist.
    for match in TOKEN.finditer(template):
        if not match[1].startswith("table:"):
            scalar(data, match[1], evidence_hash)


def age_table(data, table):
    rows = []
    for r in sorted(data["publication"]["radio_by_age"], key=lambda r: (r["lead_h"], r["stratum"])):
        agreement = f"{r['agreement_fraction']:.1%}" if r["agreement_fraction"] is not None else "unavailable"
        median = "unavailable" if r["median_abs_closest_s"] is None else f"{r['median_abs_closest_s']:.6g}"
        tail = "unavailable" if r["q95_abs_closest_s"] is None else f"{r['q95_abs_closest_s']:.6g}"
        rows.append(
            [
                f"{r['lead_h']:g}",
                r["stratum"],
                f"{r['agreement_count']}/{r['n_cases']} ({agreement})",
                f"{r['false']}/{r['predicted']}",
                f"{r['missed']}/{r['reference']}",
                r["n_closest"],
                median,
                tail,
            ]
        )
    return table(
        [
            "Element-set age h",
            "Pointings",
            "Agreement / all cases",
            "False / predicted crossings",
            "Missed / reference crossings",
            "Closest times n",
            "Median absolute Δt s",
            "Linear p95 absolute Δt s",
        ],
        rows,
    )


def display_windows(text, data):
    for key, name in data["publication"]["windows"].items():
        text = re.sub(r"(?<=\| )" + re.escape(key) + r"(?= \|)", name, text)
    return text
