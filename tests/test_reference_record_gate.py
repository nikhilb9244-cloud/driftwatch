"""A missing source must not be interpreted as a published no-burn interval."""

from types import SimpleNamespace

import pandas as pd
import pytest

from driftwatch.storm import reference, reference_run


def test_detector_crosscheck_reports_each_missed_record_and_unmatched_detection():
    def span(start, end):
        return pd.Timestamp(start), pd.Timestamp(end)

    records = [span("2024-05-01T01:00", "2024-05-01T01:01"), span("2024-05-02T01:00", "2024-05-02T01:01")]
    detections = [span("2024-05-01T00:30", "2024-05-01T01:30"), span("2024-05-03T01:00", "2024-05-03T01:01")]
    result = reference_run.detector_crosscheck(records, detections)
    assert result["record_count"] == 2
    assert result["matched_record_count"] == 1
    assert result["misses"] == [[t.isoformat() for t in records[1]]]
    assert result["unmatched_detections"] == [[t.isoformat() for t in detections[1]]]
    assert reference_run.detector_crosscheck([], [])["record_count"] == 0
    assert reference_run.detector_crosscheck(None, [])["record_count"] is None


@pytest.mark.parametrize("authoritative,missing", [(False, []), (True, ["2024-05-01"])])
def test_reference_stops_before_fitting_when_record_coverage_is_unavailable(monkeypatch, authoritative, missing):
    record = SimpleNamespace(authoritative=authoritative, days_missing=missing, issues=["source unavailable"])
    monkeypatch.setattr(reference, "load_truth", lambda *a, **kw: (None, record))
    with pytest.raises(RuntimeError, match="published manoeuvre coverage unavailable"):
        reference_run.run_mission_window(
            reference.MISSIONS["jason-3"], reference.WINDOWS[0], pd.DataFrame(), None, stations=None, with_slr=False
        )
