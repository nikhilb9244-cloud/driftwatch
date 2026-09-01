"""Supplemental Starlink sets: fetched under the CelesTrak rules, matched by NORAD id, substituted with care."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import numpy as np
import pandas as pd
import pytest

from driftwatch import config
from driftwatch.catalogue.snapshot import build_snapshot
from driftwatch.screening import supplemental
from driftwatch.screening.supplemental import apply_supplemental, fetch_supplemental, supplemental_frame


class FakeSupplemental:
    def __init__(self, records):
        self.records = records
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.params.get("FILE") != "starlink":
            return httpx.Response(200, text="No GP data found")
        return httpx.Response(200, text=json.dumps(self.records))

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler), headers={"User-Agent": config.USER_AGENT})


def test_fetch_uses_the_supplemental_endpoint_and_the_cache(omm_records, tmp_path):
    server = FakeSupplemental(omm_records[:4])
    t0 = datetime(2026, 9, 2, 0, tzinfo=UTC)
    with server.client() as client:
        first = fetch_supplemental("starlink", cache_dir=tmp_path, client=client, now=t0)
        again = fetch_supplemental("starlink", cache_dir=tmp_path, client=client, now=t0 + timedelta(hours=1))
        later = fetch_supplemental("starlink", cache_dir=tmp_path, client=client, now=t0 + timedelta(hours=3))
    assert not first.from_cache and again.from_cache and not later.from_cache
    assert len(server.requests) == 2
    url = server.requests[0].url
    assert url.path.endswith("/supplemental/sup-gp.php")
    assert url.params["FILE"] == "starlink" and url.params["FORMAT"] == "json"
    assert first.path == supplemental.supplemental_cache_path("starlink", tmp_path)
    assert len(supplemental.load_supplemental_records("starlink", tmp_path)) == 4


def test_offline_requires_cache(tmp_path):
    with pytest.raises(FileNotFoundError):
        fetch_supplemental("starlink", cache_dir=tmp_path, offline=True)


def test_supplemental_frame_tolerates_missing_bookkeeping_fields(omm_records):
    rec = dict(omm_records[0])
    for key in ("OBJECT_ID", "ELEMENT_SET_NO", "REV_AT_EPOCH", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT"):
        rec.pop(key)
    frame = supplemental_frame([rec])
    assert len(frame) == 1 and frame["element_set_no"].iloc[0] == 0
    with pytest.raises(ValueError, match="lack fields"):
        supplemental_frame([{"NORAD_CAT_ID": 1}])


def _shift(record: dict, *, days: float, mean_motion_delta: float = 0.0, norad_id: int | None = None) -> dict:
    out = dict(record)
    epoch = datetime.fromisoformat(record["EPOCH"]) + timedelta(days=days)
    out["EPOCH"] = epoch.strftime("%Y-%m-%dT%H:%M:%S.%f")
    out["MEAN_MOTION"] = record["MEAN_MOTION"] + mean_motion_delta
    if norad_id is not None:
        out["NORAD_CAT_ID"] = norad_id
    return out


def test_apply_substitutes_matching_fresh_records_only(omm_records):
    fetched_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    snap = build_snapshot({"starlink": omm_records[:6]}, None, fetched_at=fetched_at)
    ids = [int(x) for x in snap["norad_id"]]
    records = [
        _shift(omm_records[0], days=0.5, mean_motion_delta=0.01),  # fresher: applied
        _shift(omm_records[1], days=-0.5, mean_motion_delta=0.01),  # half a day older: still applied
        _shift(omm_records[2], days=-3.0, mean_motion_delta=0.01),  # too old: ignored
        _shift(omm_records[3], days=0.0, norad_id=100_001),  # placeholder id: skipped
        _shift(omm_records[4], days=0.0, norad_id=99_999),  # a real id the snapshot does not hold: skipped
    ]
    out, match = apply_supplemental(snap, records)
    assert (match.n_records, match.n_placeholder, match.n_unmatched, match.n_too_old, match.n_applied) == (
        5,
        1,
        1,
        1,
        2,
    )
    assert list(out.columns) == [*snap.columns, "ephemeris"]
    assert out["ephemeris"].tolist() == ["supplemental", "supplemental", "gp", "gp", "gp", "gp"]
    assert out["element_set_no"].dtype == snap["element_set_no"].dtype
    for k in (0, 1):
        assert out["mean_motion"].iloc[k] == pytest.approx(snap["mean_motion"].iloc[k] + 0.01)
        assert out["epoch"].iloc[k] != snap["epoch"].iloc[k]
        # A higher mean motion is a lower orbit: the derived geometry follows the new elements.
        assert out["semi_major_axis_km"].iloc[k] < snap["semi_major_axis_km"].iloc[k]
        assert out["period_min"].iloc[k] == pytest.approx(1440.0 / out["mean_motion"].iloc[k])
    for k in (2, 3, 4, 5):
        assert out["mean_motion"].iloc[k] == snap["mean_motion"].iloc[k]
    assert out["norad_id"].tolist() == ids
    assert "name" in out.columns and (out["name"] == snap["name"]).all()
    # The input is untouched.
    assert "ephemeris" not in snap.columns
    assert np.isfinite(match.epoch_lag_days_median)


def test_apply_with_nothing_matching_is_a_no_op(omm_records):
    snap = build_snapshot({"starlink": omm_records[:3]}, None, fetched_at=datetime(2026, 9, 1, tzinfo=UTC))
    out, match = apply_supplemental(snap, [_shift(omm_records[0], days=0.0, norad_id=100_500)])
    assert match.n_applied == 0 and match.n_placeholder == 1
    assert (out["ephemeris"] == "gp").all()
    out2, match2 = apply_supplemental(snap, [])
    assert match2.n_records == 0 and (out2["ephemeris"] == "gp").all()
    pd.testing.assert_frame_equal(out2.drop(columns="ephemeris"), snap)
