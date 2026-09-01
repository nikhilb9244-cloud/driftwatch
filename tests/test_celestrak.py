"""The fetcher must be polite: cache everything, never re-fetch within two hours, keep stale data on failure."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from driftwatch import config
from driftwatch.catalogue import celestrak


class FakeCelesTrak:
    def __init__(self, records):
        self.records = records
        self.requests: list[httpx.Request] = []
        self.fail = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail:
            return httpx.Response(503, text="Service Unavailable")
        group = request.url.params.get("GROUP")
        if group == "nonsense":
            return httpx.Response(200, text="No GP data found")
        return httpx.Response(200, text=json.dumps(self.records))

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler), headers={"User-Agent": config.USER_AGENT})


@pytest.fixture
def server(omm_records):
    return FakeCelesTrak(omm_records[:5])


def test_user_agent_is_descriptive():
    assert config.USER_AGENT.startswith("driftwatch/")
    assert "conjunction" in config.USER_AGENT


def test_fetch_caches_and_respects_two_hour_floor(server, tmp_path):
    t0 = datetime(2026, 9, 1, 12, tzinfo=UTC)
    with server.client() as client:
        first = celestrak.fetch_group("active", cache_dir=tmp_path, client=client, now=t0)
        again = celestrak.fetch_group("active", cache_dir=tmp_path, client=client, now=t0 + timedelta(minutes=119))
        # Asking for a shorter interval must not get below the floor.
        still = celestrak.fetch_group(
            "active", cache_dir=tmp_path, client=client, now=t0 + timedelta(minutes=119), min_interval=timedelta(0)
        )
        later = celestrak.fetch_group(
            "active", cache_dir=tmp_path, client=client, now=t0 + timedelta(hours=2, minutes=1)
        )
    assert not first.from_cache and first.n_objects == 5
    assert again.from_cache and still.from_cache
    assert not later.from_cache
    assert len(server.requests) == 2
    assert server.requests[0].headers["User-Agent"].startswith("driftwatch/")
    assert server.requests[0].url.params["FORMAT"] == "json"
    assert celestrak.load_group_records("active", tmp_path)[0]["NORAD_CAT_ID"] == server.records[0]["NORAD_CAT_ID"]


def test_unknown_group_is_an_error(server, tmp_path):
    with server.client() as client, pytest.raises(celestrak.CelesTrakError):
        celestrak.fetch_group("nonsense", cache_dir=tmp_path, client=client)


def test_stale_cache_survives_outage(server, tmp_path):
    t0 = datetime(2026, 9, 1, 12, tzinfo=UTC)
    with server.client() as client:
        celestrak.fetch_group("active", cache_dir=tmp_path, client=client, now=t0)
        server.fail = True
        result = celestrak.fetch_group("active", cache_dir=tmp_path, client=client, now=t0 + timedelta(days=1))
    assert result.from_cache and result.fetched_at == t0


def test_offline_requires_cache(tmp_path):
    with pytest.raises(FileNotFoundError):
        celestrak.fetch_group("active", cache_dir=tmp_path, offline=True)


def test_fetch_groups_shares_client(server, tmp_path):
    with server.client() as client:
        results = celestrak.fetch_groups(["active", "stations"], cache_dir=tmp_path, client=client)
    assert [r.group for r in results] == ["active", "stations"]
    assert len(server.requests) == 2
    meta = celestrak.read_meta("stations", tmp_path)
    assert meta["n_objects"] == 5 and "fetched_at" in meta
