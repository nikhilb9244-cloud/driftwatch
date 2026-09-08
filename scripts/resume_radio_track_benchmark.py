"""Preserve an interrupted radio attempt and continue its unscored exact identities.

The original attempt failed solely while writing its progress JSON after a fully
completed target. This script checks all completed cases, prepares the disjoint
remainder, and later composes both attempts without changing scoring settings.
It reads result records and the four-window trial identities, never orbit sources.
"""

import argparse
import hashlib
import itertools
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from driftwatch.radio import track_benchmark as benchmark

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / "data/radio/track_benchmark_v2"
REST = ROOT / "data/radio/track_benchmark_v2_remaining"
FINAL = ROOT / "data/radio/track_benchmark_v2_complete"
KEY = ["mission", "window", "set_epoch", "lead_h"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name, directory=FIRST):
    return json.loads((directory / name).read_text())


def read_lines(path):
    with path.open(encoding="utf-8") as stream:
        return pd.DataFrame([json.loads(line) for line in stream])


def normalised(frame):
    out = frame.copy()
    out["set_epoch"] = pd.to_datetime(out.set_epoch, utc=True)
    return out


def verify_cases(cases, completed, protocol):
    assert set(cases.trial_id) == set(completed.loc[completed.eligible, "trial_id"])
    expected = set(
        itertools.product(
            protocol["beams"],
            protocol["configuration"]["normal_boundary_fractions"],
            protocol["observation_intervals_s"],
        )
    )
    assert len(expected) == 162
    for _, group in cases.groupby("trial_id"):
        actual = set(zip(group.beam_key, group.offset_fraction, group.observation, strict=True))
        assert len(group) == 162 and actual == expected


def prepare():
    progress = read("radio_track_progress.json")
    assert progress["status"] == "failed" and progress["error_type"] == "OSError"
    assert "radio_track_progress.json" in progress["error"]
    completed = read_lines(FIRST / "radio_track_eligibility.jsonl")
    cases = read_lines(FIRST / "radio_track_cases.jsonl")
    assert len(completed) == progress["completed_trials"]
    assert not completed.duplicated(KEY).any()
    assert len(cases) == int(completed.eligible.sum()) * 162 == progress["scored_cases"]
    assert cases.groupby("trial_id").size().eq(162).all()
    assert set(cases.trial_id) == set(completed.loc[completed.eligible, "trial_id"])
    source = ROOT / "data/radio/benchmark_trials.csv"
    protocol = read("radio_track_protocol.json")
    verify_cases(cases, completed, protocol)
    assert digest(source) == protocol["input_csv_sha256"]
    all_trials = benchmark.load_trial_identities(source)
    joined = all_trials.merge(normalised(completed)[KEY], on=KEY, how="left", indicator=True, validate="one_to_one")
    remaining = joined.loc[joined._merge.eq("left_only"), list(benchmark.IDENTITY_COLUMNS)]
    assert len(remaining) + len(completed) == len(all_trials)
    target = ROOT / "data/radio/track_benchmark_remaining_trials.csv"
    if target.exists():
        raise FileExistsError(target)
    remaining.to_csv(target, index=False)
    benchmark._write_json(
        target.with_suffix(".json"),
        {
            "reason": "Continue after Windows OSError22 writing progress; completed scores preserved unchanged",
            "created_at": datetime.now(UTC).isoformat(),
            "source_csv_sha256": digest(source),
            "first_protocol_sha256": digest(FIRST / "radio_track_protocol.json"),
            "first_progress_sha256": digest(FIRST / "radio_track_progress.json"),
            "completed_eligibility_sha256": digest(FIRST / "radio_track_eligibility.jsonl"),
            "completed_cases_sha256": digest(FIRST / "radio_track_cases.jsonl"),
            "remaining_csv_sha256": digest(target),
            "n_completed": len(completed),
            "n_remaining": len(remaining),
            "scoring_settings_changed": False,
        },
    )
    print(
        f"Prepared {len(remaining)} remaining identities; retained {len(completed)} completed targets "
        f"and {len(cases)} cases"
    )


def assemble():
    assert read("radio_track_progress.json", REST)["status"] == "complete"
    first_protocol, second_protocol = read("radio_track_protocol.json"), read("radio_track_protocol.json", REST)
    assert first_protocol["configuration"] == second_protocol["configuration"]
    assert first_protocol["beams"] == second_protocol["beams"]
    assert first_protocol["observation_intervals_s"] == second_protocol["observation_intervals_s"]
    admission = pd.concat([read_lines(p / "radio_track_eligibility.jsonl") for p in (FIRST, REST)], ignore_index=True)
    assert len(admission) == first_protocol["n_input_trials"] == 10310
    assert not normalised(admission).duplicated(KEY).any()
    all_trials = benchmark.load_trial_identities(ROOT / "data/radio/benchmark_trials.csv")
    joined = all_trials.merge(normalised(admission)[KEY], on=KEY, how="outer", indicator=True, validate="one_to_one")
    assert joined._merge.eq("both").all()
    raw = pd.concat([read_lines(p / "radio_track_cases.jsonl") for p in (FIRST, REST)], ignore_index=True)
    assert len(raw) == int(admission.eligible.sum()) * 162
    assert raw.groupby("trial_id").size().eq(162).all()
    assert set(raw.trial_id) == set(admission.loc[admission.eligible, "trial_id"])
    verify_cases(raw, admission, first_protocol)
    flat = raw.drop(columns=["normal_xy", "prediction_intervals", "reference_intervals"])
    FINAL.mkdir(exist_ok=False)
    (FINAL / "curves").mkdir()
    for directory in (FIRST, REST):
        for path in (directory / "curves").glob("*.npz"):
            target = FINAL / "curves" / path.name
            assert not target.exists()
            shutil.copy2(path, target)
    for row in flat[["curve_file", "curve_sha256"]].drop_duplicates().itertuples(index=False):
        assert digest(FINAL / row.curve_file) == row.curve_sha256
    for name in ("radio_track_cases.jsonl", "radio_track_eligibility.jsonl"):
        with (FINAL / name).open("wb") as output:
            for directory in (FIRST, REST):
                with (directory / name).open("rb") as source:
                    shutil.copyfileobj(source, output)
    flat.to_csv(FINAL / "radio_track_cases.csv", index=False)
    admission.to_csv(FINAL / "radio_track_eligibility.csv", index=False)
    protocol = {
        **first_protocol,
        "composition_created_at": datetime.now(UTC).isoformat(),
        "composition": [
            {
                "directory": str(p.relative_to(ROOT)),
                "protocol_sha256": digest(p / "radio_track_protocol.json"),
                "progress_sha256": digest(p / "radio_track_progress.json"),
                "cases_sha256": digest(p / "radio_track_cases.jsonl"),
                "eligibility_sha256": digest(p / "radio_track_eligibility.jsonl"),
            }
            for p in (FIRST, REST)
        ],
        "composition_rule": (
            "Disjoint union of every completed target from the interrupted attempt and every "
            "remaining target; unchanged scoring settings, no completed case discarded"
        ),
        "composition_script_sha256": digest(Path(__file__)),
        "interpretation": (
            "All four evaluation windows were previously inspected; copied legacy window notes "
            "do not establish an untouched v2 test"
        ),
    }
    benchmark._write_json(FINAL / "radio_track_protocol.json", protocol)
    summary = {
        "schema_version": 1,
        "protocol": "radio_track_protocol.json",
        "n_input_trials": len(admission),
        "n_eligible_trials": int(admission.eligible.sum()),
        "n_cases": len(flat),
        "eligibility_counts": admission.reason.value_counts().to_dict(),
        "eligibility_by_window_mission_lead": admission.groupby(["window", "mission", "lead_h", "reason"])
        .size()
        .rename("n")
        .reset_index()
        .to_dict("records"),
        "by_beam_window_lead_observation": benchmark.summarise_cases(flat),
        "by_beam_window_lead_observation_offset": benchmark.summarise_cases(flat, by_offset=True),
        "interpretation": protocol["interpretation"],
        "execution_fragments": protocol["composition"],
    }
    benchmark._write_json(FINAL / "radio_track_summary.json", summary)
    truth_sources = {**read("radio_track_truth_sources.json"), **read("radio_track_truth_sources.json", REST)}
    benchmark._write_json(FINAL / "radio_track_truth_sources.json", truth_sources)
    benchmark._write_json(
        FINAL / "radio_track_progress.json",
        {
            "status": "complete",
            "completed_trials": len(admission),
            "total_trials": len(admission),
            "scored_cases": len(flat),
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    print(json.dumps({k: summary[k] for k in ("n_input_trials", "n_eligible_trials", "n_cases")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "assemble"])
    args = parser.parse_args()
    {"prepare": prepare, "assemble": assemble}[args.mode]()
