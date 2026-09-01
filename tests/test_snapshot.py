from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

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


def test_build_snapshot_merges_second_source(omm_records, tmp_path):
    records = list({r["NORAD_CAT_ID"]: r for r in omm_records}.values())
    ids = [r["NORAD_CAT_ID"] for r in records]

    def spacetrack(r, epoch=None):
        rec = {k: str(v) for k, v in r.items()}
        if epoch:
            rec["EPOCH"] = epoch
        return rec

    extra = [
        spacetrack(records[0], "2000-01-01T00:00:00.000000"),  # older: CelesTrak wins
        spacetrack(records[1]),  # equal epoch: CelesTrak wins the tie
        spacetrack(records[2], "2030-01-01T00:00:00.000000"),  # newer: Space-Track wins, groups kept
        *[spacetrack(r) for r in records[6:9]],  # only Space-Track holds these
    ]
    fetched_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    df = build_snapshot({"active": records[:6]}, None, fetched_at=fetched_at, extra_sources={"spacetrack": extra})

    assert len(df) == 9 and df["norad_id"].is_unique
    assert list(df.columns) == [f.name for f in SNAPSHOT_SCHEMA]
    by_id = df.set_index("norad_id")
    assert by_id.loc[ids[0], "source"] == "celestrak" and by_id.loc[ids[0], "groups"] == ["active"]
    assert by_id.loc[ids[1], "source"] == "celestrak"
    assert by_id.loc[ids[2], "source"] == "spacetrack" and by_id.loc[ids[2], "groups"] == ["active"]
    assert pd.Timestamp(by_id.loc[ids[2], "epoch"]).year == 2030
    for i in ids[6:9]:
        assert by_id.loc[i, "source"] == "spacetrack" and by_id.loc[i, "groups"] == []
    assert snapshot_summary(df)["by_source"] == {"celestrak": 5, "spacetrack": 4}

    back = read_snapshot(write_snapshot(df, snapshot_path(fetched_at, tmp_path)))
    assert back["source"].tolist() == df["source"].tolist()
    assert [list(g) for g in back["groups"]] == [list(g) for g in df["groups"]]

    # Nothing but empty groups is an error; an empty extra source is ignored.
    with pytest.raises(ValueError):
        build_snapshot({"active": []}, None, fetched_at=fetched_at)
    assert (
        len(build_snapshot({"active": records[:2]}, None, fetched_at=fetched_at, extra_sources={"spacetrack": []})) == 2
    )


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
