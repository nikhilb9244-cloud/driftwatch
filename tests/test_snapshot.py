from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from driftwatch.catalogue.snapshot import (
    SNAPSHOT_SCHEMA,
    build_snapshot,
    latest_snapshot,
    list_snapshots,
    read_snapshot,
    records_to_frame,
    snapshot_path,
    snapshot_summary,
    write_snapshot,
)


def _fake_satcat(ids):
    rows = []
    for k, norad in enumerate(ids):
        rows.append(
            {
                "norad_id": norad,
                "object_type": ["PAY", "R/B", "DEB"][k % 3],
                "ops_status": "+",
                "owner": "US",
                "launch_date": date(2000, 1, 1),
                "decay_date": None,
                "rcs_m2": float(k),
            }
        )
    return pd.DataFrame(rows).set_index("norad_id")


def test_records_to_frame_types(omm_records):
    frame = records_to_frame(omm_records)
    assert str(frame["epoch"].dtype).startswith("datetime64[") and frame["epoch"].dt.tz is not None
    assert frame["mean_motion"].dtype == np.float64
    assert frame["norad_id"].dtype == np.int64
    assert len(frame) == len(omm_records)


def test_build_snapshot_dedupes_and_joins(omm_records, tmp_path):
    ids = sorted({r["NORAD_CAT_ID"] for r in omm_records})
    half = len(omm_records) // 2
    # Overlapping groups: the second group repeats a few objects with an older epoch.
    older = []
    for r in omm_records[:3]:
        r2 = dict(r)
        r2["EPOCH"] = "2000-01-01T00:00:00.000000"
        older.append(r2)
    groups = {"active": omm_records[:half], "other": omm_records[half:] + older}
    fetched_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    df = build_snapshot(groups, _fake_satcat(ids), fetched_at=fetched_at)

    assert list(df.columns) == [f.name for f in SNAPSHOT_SCHEMA]
    assert df["norad_id"].is_unique and len(df) == len(ids)
    dup = df[df["norad_id"] == omm_records[0]["NORAD_CAT_ID"]].iloc[0]
    assert dup["groups"] == ["active", "other"]
    assert pd.Timestamp(dup["epoch"]) == pd.Timestamp(omm_records[0]["EPOCH"], tz="UTC")  # newest epoch wins
    assert set(df["category"]) <= {
        "payload",
        "rocket_body",
        "debris",
        "unknown",
        "constellation",
        "starlink",
        "oneweb",
        "station",
    }
    assert (df["object_type"].isin(["PAY", "R/B", "DEB"])).all()
    assert np.isfinite(df["perigee_km"]).all()
    assert (df["apogee_km"] >= df["perigee_km"] - 1e-6).all()
    assert set(df["altitude_band"]) <= {"leo", "meo", "geo", "heo", "other"}

    path = write_snapshot(df, snapshot_path(fetched_at, tmp_path), groups=list(groups))
    assert path.name == "gp_20260901T120000Z.parquet"
    meta = pq.read_metadata(path).metadata
    assert meta[b"driftwatch_schema_version"] == b"1"
    back = read_snapshot(path)
    assert len(back) == len(df)
    assert list(back.columns) == list(df.columns)
    pd.testing.assert_series_equal(back["mean_motion"], df["mean_motion"], check_names=False)
    assert back["launch_date"].iloc[0] == date(2000, 1, 1)

    summary = snapshot_summary(back)
    assert summary["n_objects"] == len(df)


def test_build_snapshot_without_satcat(omm_records):
    df = build_snapshot({"active": omm_records}, None, fetched_at=datetime.now(UTC))
    assert (df["object_type"] == "UNK").all()
    assert df["rcs_m2"].isna().all()


def test_latest_snapshot_orders_by_stamp(omm_records, tmp_path):
    df = build_snapshot({"active": omm_records}, None, fetched_at=datetime.now(UTC))
    for stamp_dt in (datetime(2026, 9, 2, tzinfo=UTC), datetime(2026, 9, 1, tzinfo=UTC)):
        write_snapshot(df, snapshot_path(stamp_dt, tmp_path))
    assert [p.name for p in list_snapshots(tmp_path)] == ["gp_20260901T000000Z.parquet", "gp_20260902T000000Z.parquet"]
    assert latest_snapshot(tmp_path).name == "gp_20260902T000000Z.parquet"
