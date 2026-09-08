"""A stopped schedule must fail even when somebody dispatches a replacement."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_workflow_health import assess  # noqa: E402

NOW = datetime(2026, 9, 8, 20, tzinfo=UTC)
WORKFLOW = {"state": "active", "path": ".github/workflows/pipeline.yml"}


def run(age=1, **fields):
    return {
        "id": 1,
        "event": "schedule",
        "status": "completed",
        "conclusion": "success",
        "run_started_at": (NOW - timedelta(hours=age)).isoformat(),
        **fields,
    }


def test_recent_success_is_healthy():
    assert assess(WORKFLOW, [run()], now=NOW)["healthy"]


def test_recent_manual_dispatch_cannot_mask_a_stopped_schedule():
    result = assess(WORKFLOW, [run(40), run(1, id=2, event="workflow_dispatch")], now=NOW)
    assert not result["healthy"]
    assert result["last_scheduled_run_id"] == 1
    assert "no scheduled run started" in " ".join(result["problems"])


def test_queued_event_does_not_count_as_execution():
    assert not assess(WORKFLOW, [run(status="queued", conclusion=None)], now=NOW)["healthy"]


def test_recent_failure_is_reported_even_with_a_recent_success():
    result = assess(WORKFLOW, [run(2), run(1, id=2, conclusion="failure")], now=NOW)
    assert not result["healthy"]
    assert "latest completed scheduled run 2 concluded failure" in result["problems"]


def test_active_run_needs_a_successful_predecessor_within_the_limit():
    active = run(0.5, id=2, status="in_progress", conclusion=None)
    assert assess(WORKFLOW, [active, run(24)], now=NOW)["healthy"]
    assert not assess(WORKFLOW, [active, run(40)], now=NOW)["healthy"]


def test_age_boundary_is_inclusive():
    assert assess(WORKFLOW, [run(36)], now=NOW)["healthy"]
    assert not assess(WORKFLOW, [run(36 + 1 / 3600)], now=NOW)["healthy"]


@pytest.mark.parametrize("started", [None, "unknown", "2026-09-08T19:00:00", "2026-09-09T00:00:00Z"])
def test_unknown_naive_and_future_times_fail(started):
    assert not assess(WORKFLOW, [run(run_started_at=started)], now=NOW)["healthy"]


def test_disabled_workflow_fails_despite_a_recent_success():
    assert not assess({**WORKFLOW, "state": "disabled_inactivity"}, [run()], now=NOW)["healthy"]
