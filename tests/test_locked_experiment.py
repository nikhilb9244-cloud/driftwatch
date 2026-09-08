"""Synthetic guards before the locked experiment touches its reference data."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from driftwatch.storm import locked_experiment as locked
from driftwatch.storm import precise


@pytest.fixture
def resumable_fixture(tmp_path, monkeypatch):
    """Two toy missions; no real GP, record or orbit file can be loaded."""
    source = tmp_path / "src/driftwatch/synthetic.py"
    source.parent.mkdir(parents=True)
    source.write_text("# synthetic frozen source\n")
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(locked.config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(locked.config, "CACHE_DIR", cache)
    missions = [locked.reference.MISSIONS[k] for k in ("swarm-a", "swarm-b")]
    gp = pd.DataFrame(
        {
            "norad_id": [m.norad_id for m in missions],
            "epoch": pd.to_datetime(["2024-09-01", "2024-09-01"], utc=True),
            "mean_motion": [15.0, 15.0],
        }
    )
    calls = {"gp": 0, "truth": [], "score": []}
    fail = {"second": True}

    def load_sets(*args, **kwargs):
        calls["gp"] += 1
        return gp.copy()

    def load_truth(mission, *args, **kwargs):
        calls["truth"].append(mission.key)
        files = [f"{mission.key}-synthetic-orbit.txt", f"{mission.key}-synthetic-record.txt"]
        for name in files:
            (cache / name).write_text("synthetic frozen source file\n")
        table = pd.DataFrame(
            {
                "t": pd.date_range("2024-09-01", periods=4, freq="min"),
                "x_km": 7000.0,
                "y_km": [0.0, 420.0, 840.0, 1260.0],
                "z_km": 0.0,
                "vx_kms": 0.0,
                "vy_kms": 7.0,
                "vz_kms": 0.0,
            }
        )
        orbit = precise.PreciseOrbit("toy", mission.norad_id, table, [], files[:1])
        record = precise.ThrusterRecord("toy", mission.norad_id, [], [], files[1:], 0, 0.0)
        return orbit, record

    def score(mission, orbit, record, own_sets, window, protocol):
        calls["score"].append(mission.key)
        assert len(own_sets) == 1 and len(orbit.table) == 4 and record.authoritative
        if mission.key == "swarm-b" and fail["second"]:
            raise OSError("synthetic interruption after persisted inputs")
        return (
            pd.DataFrame({"mission": [mission.key], "example": [1.0]}),
            [
                {
                    "event_id": mission.key,
                    "mission": mission.key,
                    "later_burns": [],
                    "predicted_in_track_km": 1.0,
                    "signed_in_track_km": 2.0,
                }
            ],
            {"n_recorded_burns": 1},
        )

    monkeypatch.setattr(locked.reference_run, "load_sets", load_sets)
    monkeypatch.setattr(locked.reference, "load_truth", load_truth)
    monkeypatch.setattr(locked, "_score_mission", score)
    monkeypatch.setattr(locked.reference_run, "summarise_trials", lambda frame: {"n": len(frame)})
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "author_attestation_path": "attestation.json",
                "frozen_at": "synthetic freeze",
                "source_hashes": {"src/driftwatch/synthetic.py": locked.sha256(source)},
                "missions": [m.key for m in missions],
                "sets_from": "2024-09-01T00:00:00+00:00",
                "sets_to": "2024-10-01T00:00:00+00:00",
                "calendar_rule": "synthetic test",
                "calibration_lookback_days": 7,
                "primary_lead_hours": 96,
            }
        )
    )
    attestation = tmp_path / "attestation.json"
    attestation.write_text(
        json.dumps(
            {
                "statement": locked.ATTESTATION,
                "author": "synthetic test author",
                "attested_at": "2024-01-01T00:00:00+00:00",
                "protocol_sha256": locked.sha256(protocol),
            }
        )
    )
    return SimpleNamespace(
        protocol=protocol,
        attestation=attestation,
        out=tmp_path / "output",
        source=source,
        cache=cache,
        calls=calls,
        fail=fail,
    )


def test_interrupted_mission_resumes_exact_inputs_and_skips_verified_completion(resumable_fixture):
    fixture = resumable_fixture
    with pytest.raises(OSError, match="synthetic interruption"):
        locked.execute(fixture.protocol, fixture.out, offline=True)
    marker = (fixture.out / "first-data-access.json").read_bytes()
    completed_a = locked.sha256(fixture.out / "swarm-a-completion.json")
    assert (fixture.out / "swarm-b-inputs-manifest.json").exists()
    assert not (fixture.out / "swarm-b-completion.json").exists()
    # A changed mutable cache must not change already frozen mission inputs.
    for path in fixture.cache.iterdir():
        path.write_text("mutable cache changed after input snapshot\n")
    fixture.fail["second"] = False
    result = locked.execute(fixture.protocol, fixture.out, offline=True, resume=True)
    assert fixture.calls == {"gp": 1, "truth": ["swarm-a", "swarm-b"], "score": ["swarm-a", "swarm-b", "swarm-b"]}
    assert (fixture.out / "first-data-access.json").read_bytes() == marker
    assert locked.sha256(fixture.out / "swarm-a-completion.json") == completed_a
    assert len(result["events"]) == 2 and result["secondary"]["n"] == 2
    attempts = [json.loads(p.read_text()) for p in (fixture.out / "attempts").glob("*.json")]
    assert sorted(a["status"] for a in attempts) == ["complete", "failed"]
    resumed = next(a for a in attempts if a["resume"])
    assert resumed["skipped_verified_missions"] == ["swarm-a"]
    assert locked.execute(fixture.protocol, fixture.out, offline=True, resume=True) == result
    assert fixture.calls["score"] == ["swarm-a", "swarm-b", "swarm-b"]
    with pytest.raises(RuntimeError, match="explicit resume"):
        locked.execute(fixture.protocol, fixture.out, offline=True)


@pytest.mark.parametrize("target", ["gp", "input", "output", "source", "attestation", "output_manifest"])
def test_resume_rejects_tampered_inputs_outputs_sources_or_attestation(resumable_fixture, target):
    fixture = resumable_fixture
    with pytest.raises(OSError):
        locked.execute(fixture.protocol, fixture.out, offline=True)
    if target == "output_manifest":
        path = fixture.out / "swarm-a-completion.json"
        value = json.loads(path.read_text())
        del value["files"][value["coverage"]]
        path.write_text(json.dumps(value))
        path = None
    elif target == "source":
        path = fixture.source
    elif target == "attestation":
        value = json.loads(fixture.attestation.read_text())
        value["author"] = "a different synthetic author"
        fixture.attestation.write_text(json.dumps(value))
        path = None
    else:
        manifest_name = {
            "gp": "gp-input-manifest.json",
            "input": "swarm-b-inputs-manifest.json",
            "output": "swarm-a-completion.json",
        }[target]
        manifest = json.loads((fixture.out / manifest_name).read_text())
        path = fixture.out / next(iter(manifest["files"]))
    if path is not None:
        path.write_bytes(path.read_bytes() + b"changed")
    fixture.fail["second"] = False
    with pytest.raises(RuntimeError, match="hash mismatch|Frozen code differs|attestation differs|omits"):
        locked.execute(fixture.protocol, fixture.out, offline=True, resume=True)
    assert fixture.calls["gp"] == 1 and fixture.calls["truth"] == ["swarm-a", "swarm-b"]
    assert fixture.calls["score"] == ["swarm-a", "swarm-b"]


@pytest.mark.parametrize("change", ["missing", "protocol_hash", "author", "date", "legacy_embedded"])
def test_external_attestation_gate_precedes_all_data_access(resumable_fixture, change):
    fixture = resumable_fixture
    value = json.loads(fixture.attestation.read_text())
    if change == "legacy_embedded":
        protocol = json.loads(fixture.protocol.read_text())
        del protocol["author_attestation_path"]
        protocol["author_attestation"] = locked.ATTESTATION
        fixture.protocol.write_text(json.dumps(protocol))
    elif change == "missing":
        fixture.attestation.unlink()
    else:
        key, replacement = {
            "protocol_hash": ("protocol_sha256", "incorrect"),
            "author": ("author", ""),
            "date": ("attested_at", "not a timestamp"),
        }[change]
        value[key] = replacement
        fixture.attestation.write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="attestation"):
        locked.execute(fixture.protocol, fixture.out, offline=True)
    assert fixture.calls == {"gp": 0, "truth": [], "score": []}
    assert not fixture.out.exists()


def test_resume_rejects_changed_protocol_even_with_a_new_matching_attestation(resumable_fixture):
    fixture = resumable_fixture
    with pytest.raises(OSError):
        locked.execute(fixture.protocol, fixture.out, offline=True)
    value = json.loads(fixture.protocol.read_text())
    value["primary_lead_hours"] = 24
    fixture.protocol.write_text(json.dumps(value))
    attestation = json.loads(fixture.attestation.read_text())
    attestation["protocol_sha256"] = locked.sha256(fixture.protocol)
    fixture.attestation.write_text(json.dumps(attestation))
    with pytest.raises(RuntimeError, match="Resume protocol"):
        locked.execute(fixture.protocol, fixture.out, offline=True, resume=True)
    assert fixture.calls["score"] == ["swarm-a", "swarm-b"]


def test_data_access_requires_attestation_and_frozen_hashes(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("data loaded before the protocol guard")

    monkeypatch.setattr(locked.reference, "load_truth", forbidden)
    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps({"author_attestation": "unconfirmed"}))
    with pytest.raises(RuntimeError, match="attestation"):
        locked.execute(protocol, tmp_path / "output")
    protocol.write_text(
        json.dumps(
            {
                "author_attestation_path": "attestation.json",
                "frozen_at": "a date",
                "source_hashes": {str(protocol): "wrong"},
            }
        )
    )
    (tmp_path / "attestation.json").write_text(
        json.dumps(
            {
                "statement": locked.ATTESTATION,
                "author": "synthetic test author",
                "attested_at": "2024-01-01T00:00:00+00:00",
                "protocol_sha256": locked.sha256(protocol),
            }
        )
    )
    with pytest.raises(RuntimeError, match="Frozen source manifest"):
        locked.execute(protocol, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_final_completion_must_verify_both_aggregate_files(resumable_fixture):
    fixture = resumable_fixture
    fixture.fail["second"] = False
    locked.execute(fixture.protocol, fixture.out, offline=True)
    manifest_path = fixture.out / "completion-manifest.json"
    value = json.loads(manifest_path.read_text())
    del value["files"]["locked_experiment.json"]
    manifest_path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="omits required aggregate"):
        locked.execute(fixture.protocol, fixture.out, offline=True, resume=True)
    assert fixture.calls["score"] == ["swarm-a", "swarm-b"]


def test_endpoint_keeps_unavailable_burns_and_spacecraft_deletions():
    rows = [
        {
            "event_id": str(k),
            "mission": "a" if k < 2 else "b",
            "later_burns": [],
            "predicted_in_track_km": x,
            "signed_in_track_km": y,
        }
        for k, (x, y) in enumerate([(1.0, 2.0), (2.0, 4.0), (None, 9.0)])
    ]
    result = locked.endpoint_report(rows)
    assert result["all_recorded_burns"]["n_events"] == 3
    assert result["all_recorded_burns"]["n_complete"] == 2
    assert result["all_recorded_burns"]["slope_through_origin"] == 2
    assert result["leave_one_spacecraft_out"]["a"]["n_complete"] == 0
    assert len(result["leave_one_burn_out"]) == 3


def test_energy_predictor_uses_only_prior_clean_sets_and_retains_endpoint(monkeypatch):
    times = pd.date_range("2024-08-24", "2024-10-12", freq="min").to_numpy(dtype="datetime64[us]")
    burn = pd.Timestamp("2024-09-02T00:00")
    mean_a = np.where(times < burn.to_datetime64(), 7000.0, 7000.06)
    monkeypatch.setattr(precise, "orbit_mean_semi_major_axis", lambda orbit, **kwargs: (times, mean_a, 100))
    monkeypatch.setattr(precise, "manoeuvre_intervals_from_orbit", lambda orbit: [])
    monkeypatch.setattr(precise, "manoeuvre_intervals_from_sets", lambda sets: [])
    monkeypatch.setattr(precise, "set_mean_semi_major_axis", lambda row, period: float(row["a"]))
    monkeypatch.setattr(locked, "build_satrecs", lambda one: [])
    monkeypatch.setattr(
        locked,
        "propagate_satrecs",
        lambda *args: SimpleNamespace(r_teme=np.array([[[7000.0, 10.0, 0.0]]]), error=np.array([[0]])),
    )
    orbit = SimpleNamespace(
        states_teme=lambda at: (np.array([[7000.0, 0.0, 0.0]]), np.array([[0.0, 7.0, 0.0]]), np.array([True]))
    )
    record = SimpleNamespace(intervals=[(burn, burn + pd.Timedelta(minutes=1))])
    epochs = pd.to_datetime(
        [
            "2024-08-29",
            "2024-08-30",
            "2024-08-31",
            "2024-09-02T04:00",
            "2024-09-04",
            "2024-09-05",
            "2024-09-06",
            "2024-09-07",
        ],
        utc=True,
        format="mixed",
    )
    sets = pd.DataFrame({"epoch": epochs, "norad_id": 1, "a": [7000.07] * 4 + [9000.0] * 4})
    window = precise.BenchmarkWindow(
        "test",
        "held-out",
        pd.Timestamp("2024-09-01", tz="UTC"),
        pd.Timestamp("2024-10-01", tz="UTC"),
        None,
        "synthetic",
    )
    protocol = {
        "calibration_lookback_days": 7,
        "exclusion_arc_hours": 24,
        "plateau_hours": 3,
        "primary_lead_hours": 96,
        "minimum_clean_sets": 3,
        "resolve_sigmas": 3,
        "fraction_pre": 0.25,
        "fraction_post": 0.75,
    }
    (event,) = locked.score_events(SimpleNamespace(key="test", altitude_km=622), orbit, record, sets, window, protocol)
    assert event["n_clean_sets"] == 3
    assert event["a_error_m"] == pytest.approx(-60.0, abs=1e-5)
    assert event["fraction"] == pytest.approx(0.0, abs=1e-7)
    assert event["predicted_in_track_km"] < 0
    assert event["signed_in_track_km"] == -10.0
    assert event["orbit_detector_missed"]
