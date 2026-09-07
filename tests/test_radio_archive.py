"""The SARAO archive client: the token stays in memory and out of the logs, requests are paced and paged on the
documented route, and only public observations past the proprietary period reach the observation CSV."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import httpx
import pytest

from driftwatch.radio import archive, observations


def test_token_comes_from_the_environment_only_and_is_masked():
    with pytest.raises(archive.ArchiveAuthError, match="SARAO_ARCHIVE_TOKEN"):
        archive.token_from_env({})
    with pytest.raises(archive.ArchiveAuthError, match="no password login"):
        archive.token_from_env({"SARAO_ARCHIVE_USER": "someone", "SARAO_ARCHIVE_PASS": "secret"})
    token = archive.token_from_env({"SARAO_ARCHIVE_TOKEN": "  abc.def.ghi "})
    assert token.value == "abc.def.ghi"
    assert "abc" not in repr(token) and "abc" not in str(token) and "abc" not in f"{token}"


def test_throttle_keeps_requests_two_seconds_apart():
    clock = [100.0]
    slept: list[float] = []

    def sleep(s: float) -> None:
        slept.append(s)
        clock[0] += s

    t = archive.Throttle(2.0, clock=lambda: clock[0], sleep=sleep)
    assert t.wait() == 0.0
    clock[0] += 0.5
    assert t.wait() == pytest.approx(1.5) and slept == [pytest.approx(1.5)]
    clock[0] += 3.0
    assert t.wait() == 0.0


def _page(records: list[dict], *, has_next: bool, cursor: str | None) -> dict:
    return {
        "data": {
            "observations": {
                "pageInfo": {"totalCount": 3, "endCursor": cursor, "hasNextPage": has_next},
                "records": records,
            }
        }
    }


def _record(cbid: int, start: str, band: str = "L", public: bool = True, **extra) -> dict:
    base = {
        "id": str(cbid),
        "CaptureBlockId": cbid,
        "ProposalId": "SCI-20240101-AB-01",
        "StartTime": start,
        "Duration": 3600.0,
        "band": band,
        "MinFreq": 856000000.0,
        "MaxFreq": 1712000000.0,
        "Targets": ["J1939-6342", "AT2024gsa"],
        "TargetsString": ["J1939-6342", "AT2024gsa"],
        "KatpointTargets": [
            "J1939-6342 | PKS 1934-63, radec bfcal single_accumulation, 19:39:25.03, -63:42:45.6",
            "AT2024gsa, radec target, 12:46:01.67, -09:43:08.8",
        ],
        "DecRa": ["-63:42:45.6, 19:39:25.03", "-09:43:08.8, 12:46:01.67"],
        "IntegrationTime": [600, 2700],
        "Public": public,
        "Description": "a test block",
        "Observer": "someone",
        "NumFreqChannels": 4096,
        "ProductTypeName": "MeerKATTelescopeProduct",
        "Instrument": "meerkat",
    }
    base.update(extra)
    return base


def test_client_pages_the_documented_query_and_refreshes_a_rejected_token(caplog):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert "driftwatch" in request.headers["user-agent"] and "read-only" in request.headers["user-agent"]
        if request.url.path == "/_auth/pkce-cli-refresh":
            assert json.loads(request.content) == {"refresh_token": "refresh-secret"}
            return httpx.Response(200, json={"access_token": "access-secret", "refresh_token": "rotated-secret"})
        assert request.url.path == "/graphql"
        if request.headers["authorization"] != "Bearer access-secret":
            return httpx.Response(401, json={"error": "unauthorised"})
        body = json.loads(request.content)
        assert body["query"].startswith("query (") and "observations(" in body["query"]
        assert "rdb" not in body["query"] and "s3Token" not in body["query"]
        v = body["variables"]
        assert v["limit"] == 25 and v["filters"][0]["field"] == "dateRange"
        assert v["filters"][0]["value"] == ["2024-04-20T00:00:00.000Z", "2024-04-28T00:00:00.000Z"]
        if v["cursor"] is None:
            return httpx.Response(200, json=_page([_record(1, "2024-04-21T01:00:00Z")], has_next=True, cursor="c1"))
        assert v["cursor"] == "c1"
        return httpx.Response(200, json=_page([_record(2, "2024-04-22T01:00:00Z")], has_next=False, cursor=None))

    waits: list[float] = []
    throttle = archive.Throttle(2.0, clock=lambda: 0.0, sleep=waits.append)
    client = archive.ArchiveClient(
        archive.Token("refresh-secret"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        throttle=throttle,
    )
    with caplog.at_level(logging.INFO):
        records = client.observations(datetime(2024, 4, 20, tzinfo=UTC), datetime(2024, 4, 28, tzinfo=UTC))
    assert [r["CaptureBlockId"] for r in records] == [1, 2]
    # A 401 on the first try, then the refresh, then two pages: four paced requests.
    assert [r.url.path for r in seen] == ["/graphql", "/_auth/pkce-cli-refresh", "/graphql", "/graphql"]
    assert client.n_requests == 4 and len(waits) == 3 and client.refreshed
    assert client.rotated_refresh_token is not None and client.rotated_refresh_token.value == "rotated-secret"
    text = caplog.text
    assert "refresh-secret" not in text and "access-secret" not in text and "rotated-secret" not in text


def test_client_refuses_after_a_refresh_that_does_not_help():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/_auth/pkce-cli-refresh":
            return httpx.Response(400, json={"error": "expired"})
        return httpx.Response(401)

    client = archive.ArchiveClient(archive.Token("old"), client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(archive.ArchiveAuthError, match="refresh"):
        client.observations(datetime(2024, 4, 20, tzinfo=UTC), datetime(2024, 4, 28, tzinfo=UTC))


def test_katpoint_targets_are_parsed_and_special_targets_are_not():
    name, ra, dec = archive.parse_katpoint_target("AT2024gsa | EP240414a, radec target, 12:46:01.67, -09:43:08.8")
    assert name == "AT2024gsa"
    assert ra == pytest.approx(15 * (12 + 46 / 60 + 1.67 / 3600)) and dec == pytest.approx(-(9 + 43 / 60 + 8.8 / 3600))
    assert archive.parse_katpoint_target("Sun, special") is None
    assert archive.parse_katpoint_target("zenith, azel, 0.0, 90.0") is None
    assert archive.parse_katpoint_target("J1939-6342, radec, 294.854, -63.712") == ("J1939-6342", 294.854, -63.712)
    assert archive.parse_decra("-09:43:08.8, 12:46:01.67") == pytest.approx((191.50695833, -9.71911111), rel=1e-6)
    assert archive.parse_start("2024-04-23T20:19:25Z") == datetime(2024, 4, 23, 20, 19, 25, tzinfo=UTC)
    assert archive.parse_start(1713903565) == datetime(2024, 4, 23, 20, 19, 25, tzinfo=UTC)
    assert archive.freq_mhz(856000000.0) == 856.0 and archive.freq_mhz(1284.0) == 1284.0
    assert archive.receiver_for("L", None, None) == "L" and archive.receiver_for("UHF", None, None) == "UHF"
    assert archive.receiver_for("S", 2625.0, 3500.0) == "S4"
    assert archive.receiver_for("", 856.0, 1712.0) == "L" and archive.receiver_for("X", None, None) is None


def test_only_public_observations_past_the_proprietary_period_are_kept():
    today = datetime(2026, 9, 7, tzinfo=UTC)
    records = [
        _record(1, "2024-04-21T01:00:00Z"),
        _record(2, "2024-04-22T01:00:00Z", public=False),
        _record(3, "2024-04-23T01:00:00Z", band="S4", MinFreq=2625e6, MaxFreq=3500e6),
        _record(4, "2026-04-23T01:00:00Z"),
        _record(5, "2024-04-24T01:00:00Z", Public=None),
        _record(6, "2024-05-24T01:00:00Z"),
        {**_record(7, "2024-04-25T01:00:00Z"), "KatpointTargets": ["Sun, special"], "DecRa": []},
    ]
    export = archive.select_pointings(records, bands=("UHF", "L"), today=today)
    assert export.n_records == 7
    assert [p.capture_block_id for p in export.pointings] == ["1", "1", "6", "6"]
    assert [p.target for p in export.pointings][:2] == ["J1939-6342", "AT2024gsa"]
    assert export.pointings[1].integration_s == 2700 and export.pointings[1].n_targets == 2
    assert export.excluded == {
        "not marked public by the archive": 1,
        "band S4 not asked for": 1,
        "started within the last 12 months": 1,
        "public status not stated": 1,
        "no target with a sky position": 1,
    }
    bounded = archive.select_pointings(
        records[:1] + records[5:6],
        today=today,
        first_day=datetime(2024, 4, 20, tzinfo=UTC),
        last_day=datetime(2024, 4, 28, tzinfo=UTC),
    )
    assert [p.capture_block_id for p in bounded.pointings] == ["1", "1"]
    assert bounded.excluded == {"start outside the period": 1}
    ok, why = archive.is_past_proprietary(datetime(2025, 10, 1, tzinfo=UTC), True, today=today)
    assert not ok and "12 months" in why


def test_the_observation_csv_keeps_rows_from_other_sources_and_reads_back(tmp_path):
    path = tmp_path / "quiet-2024-04.csv"
    path.write_text(
        "observation_id,target,ra,dec,start_utc,duration_s,band,centre_mhz,source,note\n"
        "gcn-36362,one,191.507,-9.719,2024-04-23T20:19:25Z,3743,S4,,GCN 36362,\n"
        "sarao-9-old,stale,1,1,2024-04-23T20:19:25Z,1,L,,old export,\n",
        encoding="utf-8",
    )
    export = archive.select_pointings([_record(1, "2024-04-21T01:00:00Z")], today=datetime(2026, 9, 7, tzinfo=UTC))
    archive.write_observation_csv(export, path)
    got = observations.read_observations(path)
    assert [o.observation_id for o in got] == ["gcn-36362", "sarao-1-J1939-6342", "sarao-1-AT2024gsa"]
    assert got[1].receiver.name == "L" and got[1].centre_mhz == pytest.approx(1284.0)
    assert got[2].ra_deg == pytest.approx(191.50695833) and got[2].duration_s == 3600.0
    assert "capture block 1" in got[2].source and "documented GraphQL API" in got[2].source
    assert "whole block is searched" in got[2].note
    sentence = archive.observation_sources_sentence(export, "the quiet week")
    assert "1 capture block(s) with 2 pointing(s)" in sentence and "public" in sentence
