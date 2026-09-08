"""Published manoeuvres: independent time conventions, absent sources and offline replay."""

import hashlib
import json
from datetime import UTC, date, datetime

import httpx
import pandas as pd
import pytest

from driftwatch.storm import manoeuvre_records as mr
from driftwatch.storm import reference


def ids_row(start, mission, event, source="SSALTO"):
    return "<tr>" + "".join(f"<td>{v}</td>" for v in [start, "system", mission, event, source]) + "</tr>"


def ids_fixture(*events):
    return (
        "<table>"
        + "".join(
            [
                ids_row("2023/01/01 00:00:37", "CRYOSAT-2", "[on board] routine status"),
                *events,
                ids_row("2025/01/01 00:00:37", "CRYOSAT-2", "[on board] routine status"),
            ]
        )
        + "</table>"
    )


MAY_EVENT = ids_row(
    "2024/05/07 12:10:54",
    "CRYOSAT-2",
    "[on board] Orbit Maintenance Maneuver (end : 2024/05/07 12:13:48 TAI), all data available",
)
HISTORY = """2025/01/01-12:00:00.000 269
2023/01/01-09:00:00.000     0.00000000D+00-0.51116378D-06 0.24540891D-07    1
2023/01/01-09:01:00.000     0.00000000D+00-0.51116378D-06 0.24540891D-07    0
2024/10/10-06:59:28.250    -0.65563725D-07 0.51116378D-06 0.24540891D-07    1
2024/10/10-07:00:31.750    -0.65563725D-07 0.51116378D-06 0.24540891D-07    0
"""


def test_ids_tai_to_utc_recovers_recorded_burn_and_handles_leap_offset():
    text = ids_fixture(MAY_EVENT)
    parsed = mr.parse_ids_events(text)
    assert parsed.intervals["cryosat-2"] == [(pd.Timestamp("2024-05-07T12:10:17"), pd.Timestamp("2024-05-07T12:13:11"))]
    # A fixed subtraction of 37 seconds would be wrong before January 2017.
    assert mr._utc("2016-12-31T23:59:50", "TAI") == pd.Timestamp("2016-12-31T23:59:14")
    assert mr._utc("2017-01-01T00:00:50", "TAI") == pd.Timestamp("2017-01-01T00:00:13")


def test_sentinel_utc_fractional_times_agree_with_independent_ids_seconds():
    parsed = mr.parse_sentinel3_history(HISTORY, "sentinel-3b")
    start, end = parsed.intervals["sentinel-3b"][-1]
    ids = mr.parse_ids_events(
        ids_fixture(
            ids_row("2024/10/10 07:00:05", "SENTINEL-3B", "Orbit Maintenance Maneuver (end: 2024/10/10 07:01:09 TAI)")
        )
    ).intervals["sentinel-3b"][0]
    assert abs((start - ids[0]).total_seconds()) == 0.25
    assert abs((end - ids[1]).total_seconds()) == 0.25
    assert start == pd.Timestamp("2024-10-10T06:59:28.250")
    assert parsed.bounds["sentinel-3b"][1] == pd.Timestamp("2025-01-01T12:00:00")
    with pytest.raises(ValueError, match="spacecraft ID"):
        mr.parse_sentinel3_history(HISTORY, "sentinel-3a")


def test_missing_or_unrecognised_catalogue_is_never_no_burn_data(tmp_path):
    def no_network(request):
        pytest.fail("an offline record request performed network I/O")

    with httpx.Client(transport=httpx.MockTransport(no_network)) as client:
        record = mr.load_record(
            "cryosat-2", 36508, date(2024, 5, 6), date(2024, 5, 8), cache_dir=tmp_path, offline=True, client=client
        )
    assert not record.authoritative and record.coverage_status == "unavailable"
    assert len(record.days_missing) == 3 and record.intervals == []
    with pytest.raises(ValueError, match="valid IDS catalogue"):
        mr.parse_ids_events("<html>please sign in</html>")


def test_authoritative_empty_list_is_preserved_and_missing_mission_is_distinct(tmp_path):
    mr.cache_snapshot("ids-ssalto", ids_fixture(MAY_EVENT).encode(), mr.IDS_URL, cache_dir=tmp_path)
    empty = mr.load_record("cryosat-2", 36508, date(2024, 4, 20), date(2024, 4, 27), cache_dir=tmp_path, offline=True)
    absent = mr.load_record("saral", 39086, date(2024, 4, 20), date(2024, 4, 27), cache_dir=tmp_path, offline=True)
    assert empty.authoritative and empty.intervals == [] and empty.days_missing == []
    assert empty.coverage_status == "published_event_registry"
    assert not absent.authoritative and len(absent.days_missing) == 8
    assert "no dated entries" in absent.issues[-1]


def test_cached_source_checksum_and_actual_retrieval_time_are_verified(tmp_path):
    payload = ids_fixture(MAY_EVENT).encode()
    fetched = datetime(2026, 9, 8, 10, 0, tzinfo=UTC)
    meta = mr.cache_snapshot("ids-ssalto", payload, mr.IDS_URL, cache_dir=tmp_path, retrieved_at=fetched)
    assert meta["sha256"] == hashlib.sha256(payload).hexdigest()
    record = mr.load_record("cryosat-2", 36508, date(2024, 5, 6), date(2024, 5, 8), cache_dir=tmp_path, offline=True)
    assert record.authoritative and len(record.intervals) == 1
    assert record.provenance[0]["retrieved_at"] == fetched.isoformat()
    assert record.provenance[0]["source_time_system"] == "TAI"
    raw = tmp_path / "manoeuvre-records" / meta["raw_file"]
    raw.write_bytes(b"corrupted")
    corrupted = mr.load_record("cryosat-2", 36508, date(2024, 5, 6), date(2024, 5, 8), cache_dir=tmp_path, offline=True)
    assert not corrupted.authoritative and "SHA256" in corrupted.issues[-1]


def test_malformed_record_inside_request_invalidates_coverage_without_hiding_valid_events(tmp_path):
    malformed = ids_row("2024/05/08 00:00:37", "CRYOSAT-2", "Orbit Maintenance Maneuver (end: 2024/05:08 00:01:37 TAI)")
    mr.cache_snapshot("ids-ssalto", ids_fixture(MAY_EVENT, malformed).encode(), mr.IDS_URL, cache_dir=tmp_path)
    record = mr.load_record("cryosat-2", 36508, date(2024, 5, 6), date(2024, 5, 9), cache_dir=tmp_path, offline=True)
    assert record.coverage_status == "malformed_records" and not record.authoritative
    assert len(record.intervals) == 1 and len(record.days_missing) == 4
    older = mr.load_record("cryosat-2", 36508, date(2024, 4, 20), date(2024, 4, 27), cache_dir=tmp_path, offline=True)
    assert older.authoritative


def test_outside_published_temporal_span_is_explicitly_incomplete(tmp_path):
    mr.cache_snapshot("sentiwiki-s3b", HISTORY.encode(), "https://example.org/s3b.man", cache_dir=tmp_path)
    record = mr.load_record("sentinel-3b", 43437, date(2025, 2, 1), date(2025, 2, 2), cache_dir=tmp_path, offline=True)
    assert record.coverage_status == "out_of_range" and not record.authoritative
    assert record.days_missing == [date(2025, 2, 1), date(2025, 2, 2)]


def test_unclosed_sentinel_burn_cannot_be_a_clean_interval(tmp_path):
    text = HISTORY.rsplit("\n", 2)[0] + "\n"
    mr.cache_snapshot("sentiwiki-s3b", text.encode(), "https://example.org/s3b.man", cache_dir=tmp_path)
    record = mr.load_record(
        "sentinel-3b", 43437, date(2024, 10, 10), date(2024, 10, 11), cache_dir=tmp_path, offline=True
    )
    assert not record.authoritative and record.coverage_status == "malformed_records"
    assert any("unclosed" in issue for issue in record.issues)


def test_online_sentinel_link_resolution_then_offline_raw_replay(tmp_path):
    page = '<a href="/__attachments/new/s3b.man?version=2">Sentinel-3B Manoeuvre History file</a>'
    calls = []

    def fetch(request):
        calls.append(str(request.url))
        return httpx.Response(200, text=page if str(request.url) == mr.SENTINEL3_INDEX_URL else HISTORY)

    with httpx.Client(transport=httpx.MockTransport(fetch)) as client:
        record = mr.load_record(
            "sentinel-3b", 43437, date(2024, 10, 10), date(2024, 10, 11), cache_dir=tmp_path, client=client
        )
    assert record.authoritative and len(calls) == 2
    assert calls[1] == "https://sentiwiki.copernicus.eu/__attachments/new/s3b.man?version=2"
    assert len(record.provenance) == 2
    offline = mr.load_record(
        "sentinel-3b", 43437, date(2024, 10, 10), date(2024, 10, 11), cache_dir=tmp_path, offline=True
    )
    assert offline.authoritative and offline.intervals == record.intervals
    assert offline.as_metadata()["interval_time_system"] == "UTC"


def test_nine_cnes_missions_use_records_and_orbit_only_loading_can_skip_them(monkeypatch):
    cnes = [m for m in reference.MISSIONS.values() if m.truth == reference.TRUTH_CNES]
    assert len(cnes) == 9
    assert all(m.manoeuvres in {reference.MANOEUVRES_IDS, reference.MANOEUVRES_SENTINEL3} for m in cnes)
    marker = object()
    monkeypatch.setattr(reference, "load_ids_orbit", lambda *args, **kwargs: marker)
    expected = mr.PublishedManoeuvreRecord(
        "swot", 54754, [], [], [], 0, 0.0, coverage_status="published_event_registry"
    )
    calls = []

    def load(*args, **kwargs):
        calls.append(args)
        return expected

    monkeypatch.setattr(mr, "load_record", load)
    args = (reference.MISSIONS["swot"], date(2024, 4, 20), date(2024, 4, 27))
    assert reference.load_truth(*args, offline=True) == (marker, expected)
    assert reference.load_truth(*args, offline=True, records=False) == (marker, None)
    assert len(calls) == 1
    assert json.dumps(expected.as_metadata())
