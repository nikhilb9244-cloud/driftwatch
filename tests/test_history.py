"""The history store keeps one row per (object, epoch) across gp_history pulls and snapshots."""

from datetime import UTC, datetime

import pandas as pd

from driftwatch.catalogue import history
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
