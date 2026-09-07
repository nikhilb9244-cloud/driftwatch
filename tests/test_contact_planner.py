"""A schedule change must respect commitments and beat the declared baseline fairly."""

import itertools
from decimal import Decimal
from io import StringIO

import numpy as np
import pandas as pd
import pytest

from driftwatch.contact_planner import schedule_contacts
from driftwatch.workbench import analyse


def table(rows):
    """id, start minute, end minute, priority, current, protected."""
    epoch = pd.Timestamp("2024-05-10", tz="UTC")
    return pd.DataFrame(
        [
            dict(
                contact_id=identity,
                satellite="Training satellite",
                start=(epoch + pd.Timedelta(minutes=start)).isoformat(),
                end=(epoch + pd.Timedelta(minutes=end)).isoformat(),
                priority=priority,
                baseline=current,
                locked=protected,
            )
            for identity, start, end, priority, current, protected in rows
        ]
    ).to_csv(index=False)


def selected(result):
    return {c["contact_id"] for c in result["contacts"] if c["selected"]}


def test_compare_an_actual_schedule_and_keep_its_protected_contact():
    text = table(
        [
            ("long", 0, 20, 10, True, False),
            ("short-a", 0, 8, 6, False, False),
            ("short-b", 9, 18, 6, False, False),
            ("committed", 21, 30, 4, True, True),
        ]
    )
    result = analyse("plan", {"contacts": {"name": "requests.csv", "text": text}})
    assert selected(result) == {"short-a", "short-b", "committed"}
    assert result["protected_count"] == 1
    comparison = result["comparison"]
    assert comparison["status"] == "improved"
    assert comparison["baseline_priority"] == 14
    assert comparison["priority_delta"] == 2
    assert comparison["removed_ids"] == ["long"]
    assert comparison["retained_ids"] == ["committed"]
    assert comparison["baseline_minutes"] == 29
    assert comparison["proposed_minutes"] == 26
    assert result["sources"][0]["sha256"]
    assert result["request_sha256"]


def test_protected_lower_priority_is_never_silently_removed():
    result = schedule_contacts(
        table(
            [
                ("protected", 0, 20, 1, True, True),
                ("tempting", 0, 8, 100, False, False),
                ("after", 21, 30, 2, True, False),
            ]
        )
    )
    assert selected(result) == {"protected", "after"}
    assert result["comparison"]["status"] == "unchanged"
    assert result["comparison"]["priority_delta"] == 0
    assert next(c for c in result["contacts"] if c["contact_id"] == "tempting")["conflicts_with"] == ["protected"]


def test_equal_priority_preserves_current_schedule_including_decimal_ties():
    result = schedule_contacts(
        table(
            [
                ("current", 0, 20, 0.3, True, False),
                ("a", 0, 8, 0.1, False, False),
                ("b", 9, 18, 0.2, False, False),
            ]
        )
    )
    assert selected(result) == {"current"}
    assert result["comparison"]["added_ids"] == []
    assert result["comparison"]["removed_ids"] == []


def test_infeasible_baseline_is_reported_without_a_false_improvement():
    result = schedule_contacts(
        table(
            [
                ("overlap-a", 0, 20, 10, True, False),
                ("overlap-b", 1, 8, 20, True, False),
                ("new-commitment", 21, 30, 1, False, True),
            ]
        )
    )
    comparison = result["comparison"]
    assert comparison["status"] == "repair_required"
    assert comparison["feasible"] is False
    assert comparison["priority_delta"] is None
    assert len(comparison["issues"]) == 2
    assert "new-commitment" in selected(result)


def test_turnaround_applies_on_both_sides_of_commitments_and_at_boundaries():
    rows = [
        ("before", 0, 8, 2, False, False),
        ("protected", 9, 18, 1, True, True),
        ("after", 19, 30, 2, False, False),
    ]
    assert selected(schedule_contacts(table(rows), turnaround_s=60)) == {"before", "protected", "after"}
    assert selected(schedule_contacts(table(rows), turnaround_s=61)) == {"protected"}
    rows[0] = ("before", 0, 8, 2, True, True)
    with pytest.raises(ValueError, match="Protected contacts before and protected conflict"):
        schedule_contacts(table(rows), turnaround_s=61)


@pytest.mark.parametrize("value", ["maybe", "booked", "2", "nan"])
def test_ambiguous_flags_are_refused(value):
    with pytest.raises(ValueError, match="true/false"):
        schedule_contacts(table([("a", 0, 8, 2, value, False)]))


def test_optional_mapped_columns_are_explicit_and_five_column_files_still_work():
    frame = pd.read_csv(StringIO(table([("a", 0, 8, 2, True, True)])))
    frame = frame.rename(columns={"baseline": "already_booked", "locked": "must_keep"})
    mapping = {key: key for key in ("contact_id", "satellite", "start", "end", "priority")}
    result = schedule_contacts(
        frame.to_csv(index=False, sep=";"),
        delimiter=";",
        mapping={
            **mapping,
            "baseline": "already_booked",
            "locked": "must_keep",
        },
    )
    assert result["comparison"]["status"] == "unchanged"
    assert result["protected_count"] == 1
    with pytest.raises(ValueError, match="distinct existing columns"):
        schedule_contacts(frame.to_csv(index=False), mapping={**mapping, "baseline": "priority"})
    result = schedule_contacts(frame[list(mapping)].to_csv(index=False))
    assert result["comparison"]["status"] == "baseline_required"
    assert result["comparison"]["priority_delta"] is None


def test_committed_scheduler_matches_exhaustive_priority_then_minimum_changes():
    rng = np.random.default_rng(270)
    for _ in range(24):
        starts = rng.integers(0, 90, 8)
        ends = starts + rng.integers(1, 20, 8)
        weights = rng.integers(1, 8, 8)
        baseline = rng.integers(0, 2, 8).astype(bool)
        locked = np.zeros(8, dtype=bool)
        locked[0] = True
        rows = [
            (str(i), int(starts[i]), int(ends[i]), int(weights[i]), bool(baseline[i]), bool(locked[i]))
            for i in range(8)
        ]
        result = schedule_contacts(table(rows))
        alternatives = []
        for mask in itertools.product([False, True], repeat=8):
            if not mask[0]:
                continue
            order = sorted([i for i in range(8) if mask[i]], key=lambda i: starts[i])
            if all(ends[a] + 1 <= starts[b] for a, b in zip(order, order[1:], strict=False)):
                alternatives.append(
                    (sum(int(weights[i]) for i in order), -sum(mask[i] != baseline[i] for i in range(8)))
                )
        ids = selected(result)
        actual = (Decimal(str(result["priority_total"])), -sum((str(i) in ids) != baseline[i] for i in range(8)))
        assert actual == max(alternatives)
