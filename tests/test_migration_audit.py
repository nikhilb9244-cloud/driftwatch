"""The audit must expose failed and untested paths, and its table must match its record."""

import json
from pathlib import Path

from driftwatch import migration_audit

ROOT = Path(__file__).resolve().parents[1]


def test_six_axes_expose_optional_field_loss_and_unexercised_browser_paths():
    record = migration_audit.audit(ROOT / "docs/assets/cases/public-swarm-a.zip")
    statuses = {r["axis"]: r["status"] for r in record["rows"]}
    assert statuses == {
        "Object identity": "untested",
        "Time and availability": "passed",
        "Frame, centre and units": "passed",
        "Mean-element theory": "passed",
        "Optional and missing data": "failed",
        "Full adapter path": "untested",
    }
    optional = next(r for r in record["rows"] if r["axis"] == "Optional and missing data")
    assert all(c["status"] == "failed" for c in optional["checks"])
    assert optional["checks"][0]["observation"]["CLASSIFICATION_TYPE"] == "U"
    assert optional["checks"][1]["observation"]["retained_in_history"] is False
    assert record["customer_adapter"] == "unverified"


def test_rendered_matrix_and_second_machine_report_are_bound_to_the_public_case():
    record = json.loads((ROOT / "docs/assets/cases/migration-audit-2026-09-08.json").read_bytes())
    assert (ROOT / "docs/migration-audit-2026-09-08.md").read_text(encoding="utf-8") == migration_audit.render(record)
    asset = json.loads((ROOT / "docs/assets/cases/public-swarm-a.json").read_bytes())
    second = json.loads((ROOT / "docs/assets/cases/second-machine-2026-09-08.json").read_bytes())
    assert record["bundle_sha256"] == asset["sha256"]
    assert second["result"]["case_sha256"] == asset["case_sha256"]
    assert second["fresh_clone_without_data"] and second["source_and_lock_from_bundle"]
    assert second["result"]["reproduced"] and second["result"]["verification_os"] == "Linux"
