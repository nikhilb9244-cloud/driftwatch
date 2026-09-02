"""The history store keeps one row per (object, epoch) across gp_history pulls and snapshots; the index
finds the files that hold an object; the backfill batches, skips what is covered and never re-requests."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
from test_spacetrack import FakeSpaceTrack, spacetrack_records

from driftwatch.catalogue import history, spacetrack
from driftwatch.catalogue.snapshot import build_snapshot, snapshot_path, write_snapshot


def _stringify(records):
    return [{k: str(v) for k, v in r.items()} for r in records]


def _unique(omm_records):
    return list({r["NORAD_CAT_ID"]: r for r in omm_records}.values())


def test_frame_from_records_dedupes_same_epoch(omm_records):
    records = _stringify(_unique(omm_records)[:4])
    reissued = dict(records[0], ELEMENT_SET_NO="999")
    newer = dict(records[0], EPOCH="2030-01-01T00:00:00.000000")
    df = history.frame_from_records(records + [reissued, newer], fetched_at=datetime(2026, 9, 1, tzinfo=UTC))
    assert list(df.columns) == list(history.HISTORY_COLUMNS)
    assert len(df) == 5
    first = df[df["norad_id"] == int(records[0]["NORAD_CAT_ID"])]
    assert len(first) == 2 and int(first.iloc[0]["element_set_no"]) == 999 and first.iloc[1]["epoch"].year == 2030
    assert (df["source"] == "spacetrack").all()
    assert str(df["epoch"].dtype) == "datetime64[us, UTC]"
    assert history.frame_from_records([]).empty


def test_write_read_and_load_with_snapshots(omm_records, tmp_path):
    hist_dir, snap_dir = tmp_path / "history", tmp_path / "snapshots"
    records = _unique(omm_records)
    ids = [r["NORAD_CAT_ID"] for r in records]
    t = datetime(2026, 9, 1, 12, tzinfo=UTC)

    df = history.frame_from_records(_stringify(records[:3]), fetched_at=t)
    path = history.write_history(df, history.history_path(t, hist_dir), metadata={"norad_ids": "test"})
    assert path.name == "gph_20260901T120000Z.parquet"
    back = history.read_history(path)
    pd.testing.assert_frame_equal(back, df, check_dtype=False)

    # A snapshot with the same three objects one day later plus a fourth object.
    snap = build_snapshot({"active": records[:4]}, None, fetched_at=t)
    snap["epoch"] = snap["epoch"] + pd.Timedelta(days=1)
    write_snapshot(snap, snapshot_path(t, snap_dir))

    both = history.load_history(history_dir=hist_dir, snapshot_dir=snap_dir)
    assert len(both) == 7 and both["norad_id"].is_monotonic_increasing
    assert set(both["source"]) == {"spacetrack", "celestrak"}
    only_history = history.load_history(history_dir=hist_dir, snapshot_dir=snap_dir, include_snapshots=False)
    assert len(only_history) == 3

    one = history.load_history(norad_ids=ids[:1], history_dir=hist_dir, snapshot_dir=snap_dir)
    assert len(one) == 2 and one["epoch"].is_monotonic_increasing
    later = history.load_history(
        norad_ids=ids[:1], start=one["epoch"].iloc[1], history_dir=hist_dir, snapshot_dir=snap_dir
    )
    assert len(later) == 1 and later.iloc[0]["source"] == "celestrak"
    earlier = history.load_history(
        norad_ids=ids[:1], end=one["epoch"].iloc[0], history_dir=hist_dir, snapshot_dir=snap_dir
    )
    assert len(earlier) == 1 and earlier.iloc[0]["source"] == "spacetrack"

    summary = history.history_summary(both)
    assert summary["n_objects"] == 4 and summary["n_records"] == 7
    assert summary["sets_per_object"] == {"min": 1, "median": 2.0, "max": 2}
    assert history.history_summary(history.load_history(history_dir=tmp_path / "x", snapshot_dir=tmp_path / "y")) == {
        "n_records": 0,
        "n_objects": 0,
    }


def test_index_is_maintained_rebuilt_and_used_to_open_only_the_right_files(omm_records, tmp_path, monkeypatch):
    hist_dir, none = tmp_path / "history", tmp_path / "none"
    records = _stringify(_unique(omm_records))
    ids = [int(r["NORAD_CAT_ID"]) for r in records]
    t = datetime(2026, 9, 1, 12, tzinfo=UTC)

    def frame(rows):
        return history.frame_from_records(rows, fetched_at=t)

    f1 = history.write_history(frame(records[:3]), history.history_path(t, hist_dir))
    f2 = history.write_history(frame(records[3:5]), history.history_path(t + timedelta(hours=1), hist_dir))
    index = history.load_index(hist_dir)
    assert len(index) == 5 and sorted(index["file"].unique()) == [f1.name, f2.name]
    assert list(index.columns) == ["norad_id", "epoch", "file"] and str(index["epoch"].dtype) == "datetime64[us, UTC]"

    opened = []
    real = history.read_history
    monkeypatch.setattr(history, "read_history", lambda p, **kw: (opened.append(p), real(p, **kw))[1])
    one = history.load_history(norad_ids=[ids[4]], history_dir=hist_dir, snapshot_dir=none)
    assert len(one) == 1 and opened == [f2]
    opened.clear()
    both = history.load_history(norad_ids=[ids[0], ids[4]], history_dir=hist_dir, snapshot_dir=none)
    assert len(both) == 2 and opened == [f1, f2]
    assert history.load_history(norad_ids=[424242], history_dir=hist_dir, snapshot_dir=none).empty

    # A file written without updating the index makes it stale; a lookup notices and rebuilds.
    f3 = history.write_history(
        frame(records[5:6]), history.history_path(t + timedelta(hours=2), hist_dir), update=False
    )
    assert len(history.load_index(hist_dir, rebuild=False)) == 5
    assert len(history.load_index(hist_dir)) == 6
    history.index_path(hist_dir).unlink()
    rebuilt = history.load_index(hist_dir)
    assert len(rebuilt) == 6 and f3.name in set(rebuilt["file"])
    assert history.load_index(tmp_path / "empty").empty


def test_backfill_batches_skips_covered_ids_and_asks_only_for_missing_days(omm_records, tmp_path):
    server = FakeSpaceTrack(spacetrack_records(omm_records[:8]))
    ids = sorted(int(r["NORAD_CAT_ID"]) for r in server.records[:5])
    hist_dir = tmp_path / "history"
    end = datetime(2026, 9, 1, 15, tzinfo=UTC)
    assert history.backfill_window(end, 3) == (date(2026, 8, 30), date(2026, 9, 1))
    with server.client() as client:
        kw = dict(cache_dir=tmp_path, history_dir=hist_dir, client=client, now=end)
        first = history.backfill(ids, end=end, days=3, **kw)
        again = history.backfill(ids, end=end, days=3, **kw)
        later = history.backfill(ids, end=end + timedelta(days=2), days=5, **kw)
        more = history.backfill(ids + [server.records[6]["NORAD_CAT_ID"]], end=end, days=3, **kw)
    assert (first.start, first.end, first.n_requested, first.n_already_covered) == (
        date(2026, 8, 30),
        date(2026, 9, 1),
        5,
        0,
    )
    assert first.n_requests == 1 and first.n_cached_requests == 0 and first.n_records == 5 and first.path is not None
    paths = server.query_paths()
    assert "/EPOCH/2026-08-30--2026-09-02/" in paths[0] and "/predicates/" in paths[0]
    assert again.n_requests == 0 and again.n_already_covered == 5 and again.path is None
    # Same window start, two more days: only the two missing days are requested.
    assert later.n_requests == 1 and "/EPOCH/2026-09-02--2026-09-04/" in paths[1]
    # A new id joins: only it is requested, over the whole window.
    assert more.n_requests == 1 and more.n_already_covered == 5 and more.n_fetched_ids == 1
    assert paths[2].split("/NORAD_CAT_ID/")[1].split("/")[0] == str(server.records[6]["NORAD_CAT_ID"])
    assert len(paths) == 3

    # Three pulls in the same second are three files, not one overwritten twice.
    assert len(history.list_history(hist_dir)) == 3
    index = history.load_index(hist_dir)
    assert sorted(index["file"].unique()) == sorted(p.name for p in history.list_history(hist_dir))
    stored = history.load_history(norad_ids=ids, history_dir=hist_dir, snapshot_dir=tmp_path / "none")
    assert stored["norad_id"].tolist() == ids  # one epoch per object in the fake data, de-duplicated across files
    coverage = spacetrack.history_coverage(tmp_path)
    assert spacetrack.covered_ids(coverage, ids, date(2026, 8, 30), date(2026, 9, 1)) == set(ids)
    groups = history._needed_ranges(coverage, ids, date(2026, 8, 30), date(2026, 9, 3))
    assert groups == {}  # fully covered after the third pull
    groups = history._needed_ranges(coverage, ids, date(2026, 8, 30), date(2026, 9, 5))
    assert groups == {(date(2026, 9, 4), date(2026, 9, 5)): ids}
    offline = history.backfill(ids, end=end, days=3, cache_dir=tmp_path, history_dir=hist_dir, offline=True, now=end)
    assert offline.n_requests == 0


def test_history_updates_are_incremental_after_the_first_backfill(omm_records, tmp_path):
    """The backfill is a one-off: later runs ask only for the days after each object's newest stored set."""
    server = FakeSpaceTrack(spacetrack_records(omm_records[:8]))
    ids = sorted(int(r["NORAD_CAT_ID"]) for r in server.records[:4])
    hist_dir = tmp_path / "history"
    end = datetime(2026, 9, 1, 15, tzinfo=UTC)

    with server.client() as client:
        kw = dict(cache_dir=tmp_path, history_dir=hist_dir, client=client)
        first = history.backfill(ids, end=end, days=10, now=end, **kw)
        assert first.n_requests == 1 and first.n_records == 4
        stored = history.stored_through(ids, hist_dir)
        assert set(stored) == set(ids)
        newest = history.load_history(norad_ids=ids, history_dir=hist_dir, snapshot_dir=tmp_path / "none")
        for norad_id, day in stored.items():
            assert day == newest.loc[newest["norad_id"] == norad_id, "epoch"].max().date()

        # A day later: the window start moves back ten days, but the store already holds those
        # element sets, so only the new day is requested.
        later = end + timedelta(days=1)
        update = history.backfill(ids, end=later, days=10, now=later, **kw)
    paths = server.query_paths()
    assert update.n_requests == 1 and len(paths) == 2
    first_start, first_end = paths[0].split("/EPOCH/")[1].split("/")[0].split("--")
    second_start, second_end = paths[1].split("/EPOCH/")[1].split("/")[0].split("--")
    assert (first_start, first_end) == ("2026-08-23", "2026-09-02")  # ten days, the whole window
    assert second_start > first_start and second_end == "2026-09-03"  # only what the store lacks
    assert (later.date() - date.fromisoformat(second_start)).days <= 30


def test_needed_ranges_starts_from_the_newest_stored_set_per_object():
    coverage = pd.DataFrame({"norad_id": pd.Series(dtype="int64"), "start": [], "end": []})
    ids = [1, 2, 3]
    stored = {1: date(2026, 8, 30), 2: date(2026, 9, 3)}
    groups = history._needed_ranges(coverage, ids, date(2026, 8, 20), date(2026, 9, 2), stored)
    # Object 1 needs the days from its newest set; object 2 is already past the window end and is
    # skipped; object 3 has nothing stored and needs the whole window.
    assert groups == {(date(2026, 8, 30), date(2026, 9, 2)): [1], (date(2026, 8, 20), date(2026, 9, 2)): [3]}
    assert history._needed_ranges(coverage, ids, date(2026, 8, 20), date(2026, 9, 2), {}) == {
        (date(2026, 8, 20), date(2026, 9, 2)): [1, 2, 3]
    }
    assert history.stored_through([1, 2], tmp_history_dir := Path("data/history-does-not-exist")) == {}
    assert not tmp_history_dir.exists()
