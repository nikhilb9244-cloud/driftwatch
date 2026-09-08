"""Acceptance arithmetic, tamper checks and portable bundle reopening."""

import copy
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from driftwatch import case_bundle as bundle
from driftwatch.imports import decode_orbit


@pytest.fixture
def case(verification_tles):
    tle = verification_tles[0]
    raw = (tle.line1[:69] + "\n" + tle.line2[:69] + "\n").encode()
    record = decode_orbit(raw.decode()).records[0]
    omm = bundle.encode([record])
    epoch = pd.Timestamp(record["EPOCH"])
    if epoch.tzinfo is None:
        epoch = epoch.tz_localize("UTC")
    inputs = {}
    for role, name, data in (("baseline", "baseline.tle", raw), ("candidate", "candidate.json", omm)):
        inputs[role] = {
            "path": "supplied/" + name,
            "sha256": bundle.sha(data),
            "source_identifier": "sgp4:verification-fixture",
            "rights": {"redistribution_permitted": True, "basis": "sgp4 MIT test fixture", "attribution": "sgp4"},
            "state_epoch": epoch.isoformat(),
            "provider_created_at": None,
            "published_at": None,
            "retrieved_at": None,
        }
    spec = {
        "schema_version": bundle.SCHEMA,
        "inputs": inputs,
        "conventions": {
            "frame": "TEME",
            "centre": "EARTH",
            "time_system": "UTC",
            "position_unit": "km",
            "velocity_unit": "km/s",
            "theory": "SGP4",
            "constants": "WGS72",
            "operation_mode": "i",
            "difference_sign": "candidate minus baseline",
        },
        "epochs_utc": [(epoch + pd.Timedelta(hours=h)).isoformat() for h in (6, 24, 72)],
        "acceptance_criterion": {
            "kind": "maximum-cartesian-state-difference",
            "position_km": 0.01,
            "velocity_km_s": 0.00001,
            "reproduction_position_km": 1e-8,
            "reproduction_velocity_km_s": 1e-11,
            "recorded_at": datetime.now(UTC).isoformat(),
            "agreed_by_role": "test author",
            "decision_owner_role": "test author",
        },
        "limitations": ["Constructed format check; no accuracy claim"],
    }
    return spec, {inputs["baseline"]["path"]: raw, inputs["candidate"]["path"]: omm}


def test_agreement_and_signed_difference_determine_acceptance(case):
    spec, supplied = case
    assert bundle.evaluate(spec, supplied)["acceptance"]["accepted"]
    record = json.loads(supplied["supplied/candidate.json"])[0]
    record["MEAN_ANOMALY"] += 0.1
    supplied["supplied/candidate.json"] = bundle.encode([record])
    spec["inputs"]["candidate"]["sha256"] = bundle.sha(supplied["supplied/candidate.json"])
    output = bundle.evaluate(spec, supplied)
    assert not output["acceptance"]["accepted"]
    assert output["acceptance"]["max_position_difference_km"] > 1
    np.testing.assert_allclose(
        output["differences"]["delta_r_teme_km"],
        np.asarray(output["candidate"]["r_teme_km"]) - np.asarray(output["baseline"]["r_teme_km"]),
    )


def test_input_tampering_and_identity_mismatch_fail(case):
    spec, supplied = case
    supplied["supplied/candidate.json"] += b" "
    with pytest.raises(ValueError, match="Input hash mismatch"):
        bundle.evaluate(spec, supplied)
    record = json.loads(supplied["supplied/candidate.json"])[0]
    record["NORAD_CAT_ID"] += 1
    supplied["supplied/candidate.json"] = bundle.encode([record])
    spec["inputs"]["candidate"]["sha256"] = bundle.sha(supplied["supplied/candidate.json"])
    with pytest.raises(ValueError, match="identities differ"):
        bundle.evaluate(spec, supplied)


@pytest.mark.parametrize("permission", [False, None])
def test_missing_redistribution_permission_prevents_packaging(case, permission):
    spec, _ = case
    spec["inputs"]["candidate"]["rights"]["redistribution_permitted"] = permission
    with pytest.raises(ValueError, match="redistribution"):
        bundle.validate_spec(spec)


def test_contract_cannot_be_recorded_after_evaluation(case):
    spec, _ = case
    spec["acceptance_criterion"]["recorded_at"] = "2999-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="before evaluation"):
        bundle.validate_spec(spec)


def test_unknown_temporal_values_remain_unknown_and_missing_keys_fail(case):
    spec, supplied = case
    before = copy.deepcopy(spec)
    bundle.evaluate(spec, supplied)
    assert spec == before
    del spec["inputs"]["baseline"]["published_at"]
    with pytest.raises(ValueError, match="use null for unknown"):
        bundle.validate_spec(spec)


@pytest.mark.parametrize("name", ["../outside", chr(67) + ":/outside", "folder\\outside"])
def test_archive_paths_cannot_escape_the_bundle(tmp_path, name):
    with pytest.raises(ValueError, match="relative path"):
        bundle.safe_name(name)
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, "bad")
    # The Windows ZIP writer can normalise a backslash before the reader sees it.
    with pytest.raises(ValueError, match="relative path|missing manifest"):
        bundle.read_case(path)


def test_pack_reopen_and_tampered_output_check(case, tmp_path):
    spec, supplied = case
    source = tmp_path / "case"
    source.mkdir()
    for name, raw in supplied.items():
        p = source / name
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(raw)
    (source / "case.json").write_bytes(bundle.encode(spec))
    archive = tmp_path / "case.zip"
    result = bundle.pack(source / "case.json", archive, Path(__file__).resolve().parents[1])
    assert bundle.sha(archive.read_bytes()) == result["sha256"]
    assert bundle.verify(archive)["reproduced"]
    unpacked = tmp_path / "reopened"
    bundle.unpack(archive, unpacked)
    assert bundle.verify(unpacked)["reproduced"]
    assert (unpacked / "uv.lock").exists() and (unpacked / "src/driftwatch/case_bundle.py").exists()
    path = unpacked / "outputs/differences.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch: outputs/differences.json"):
        bundle.verify(unpacked)


def test_public_case_asset_matches_its_committed_hash():
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root / "docs/assets/cases/public-swarm-a.json").read_bytes())
    path = root / record["path"]
    assert bundle.sha(path.read_bytes()) == record["sha256"]
    _, entries = bundle.read_case(path)
    spec = json.loads(entries["case.json"])
    assert spec["acceptance_criterion"]["customer_agreed"] is False
    assert all("spacetrack:gp_history" in item["source_identifier"] for item in spec["inputs"].values())
