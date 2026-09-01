"""Space-Track rules: log in once, stay under the rate limits, cache with floors, never leak credentials."""

import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from driftwatch import config
from driftwatch.catalogue import spacetrack
from driftwatch.catalogue.spacetrack import (
    Credentials,
    RateLimiter,
    SpaceTrackAuthError,
    SpaceTrackClient,
    gp_catalogue_request,
    gp_history_request,
)

USER = "someone@example.org"
PASSWORD = "hunter2-not-for-disk"  # a test checks this string never lands in a file or a log
CREDS = Credentials(USER, PASSWORD)


def spacetrack_records(omm_records):
    """Space-Track sends every value as a string and adds catalogue fields CelesTrak's OMM lacks."""
    out = []
    for r in omm_records:
        rec = {k: str(v) for k, v in r.items()}
        rec.update(
            {
                "OBJECT_TYPE": "DEBRIS",
                "RCS_SIZE": "SMALL",
                "COUNTRY_CODE": "US",
                "DECAY_DATE": None,
                "GP_ID": rec["NORAD_CAT_ID"] + "01",
            }
        )
        out.append(rec)
    return out


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


class FakeSpaceTrack:
    """Enough of Space-Track to exercise the client: cookie login, 401 without it, gp and gp_history."""

    def __init__(self, records):
        self.records = records
        self.requests: list[httpx.Request] = []
        self.fail = False
        self.expire_session = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        request.read()
        url = str(request.url)
        if url == config.SPACETRACK_LOGIN_URL:
            form = dict(httpx.QueryParams(request.content.decode()))
            if form.get("identity") == USER and form.get("password") == PASSWORD:
                return httpx.Response(200, text='""', headers={"set-cookie": "chocolatechip=abc; Path=/"})
            return httpx.Response(200, json={"Login": "Failed"})
        if url == config.SPACETRACK_LOGOUT_URL:
            return httpx.Response(200, text='"Goodbye"')
        if "chocolatechip=abc" not in request.headers.get("cookie", "") or self.expire_session:
            self.expire_session = False
            return httpx.Response(401, text="Unauthorized")
        if self.fail:
            return httpx.Response(503, text="Service Unavailable")
        path = request.url.raw_path.decode()
        if "/class/gp/" in path:
            return httpx.Response(200, json=self.records)
        if "/class/gp_history/" in path:
            ids = {int(x) for x in path.split("/NORAD_CAT_ID/")[1].split("/")[0].split(",")}
            return httpx.Response(200, json=[r for r in self.records if int(r["NORAD_CAT_ID"]) in ids])
        return httpx.Response(404, text="no such class")

    def query_paths(self) -> list[str]:
        return [r.url.raw_path.decode() for r in self.requests if "/basicspacedata/" in str(r.url)]

    def client(self, credentials: Credentials = CREDS) -> SpaceTrackClient:
        clock = FakeClock()
        return SpaceTrackClient(
            credentials,
            transport=httpx.MockTransport(self.handler),
            limiter=RateLimiter(clock=clock, sleep=clock.sleep),
        )


@pytest.fixture
def server(omm_records):
    return FakeSpaceTrack(spacetrack_records(omm_records[:8]))


def test_credentials_are_masked_and_come_from_env():
    assert PASSWORD not in repr(CREDS) and PASSWORD not in str(CREDS) and USER not in repr(CREDS)
    with pytest.raises(SpaceTrackAuthError):
        spacetrack.credentials_from_env({})
    with pytest.raises(SpaceTrackAuthError):
        spacetrack.credentials_from_env({config.SPACETRACK_USER_ENV: USER})
    creds = spacetrack.credentials_from_env({config.SPACETRACK_USER_ENV: USER, config.SPACETRACK_PASS_ENV: PASSWORD})
    assert creds == CREDS


def test_request_builders():
    assert gp_catalogue_request() == (
        "/class/gp/decay_date/null-val/epoch/%3Enow-30/orderby/norad_cat_id%20asc/format/json"
    )
    assert gp_history_request([39634, 25544, 25544], date(2024, 5, 1), date(2024, 5, 21)) == (
        "/class/gp_history/NORAD_CAT_ID/25544,39634/EPOCH/2024-05-01--2024-05-21/orderby/EPOCH%20asc/format/json"
    )
    with pytest.raises(ValueError):
        gp_history_request([], date(2024, 5, 1), date(2024, 5, 2))


def test_login_once_then_query(server):
    with server.client() as client:
        first = client.gp_catalogue()
        second = client.gp_catalogue()
    assert len(first) == 8 and second == first
    urls = [str(r.url) for r in server.requests]
    assert urls[0] == config.SPACETRACK_LOGIN_URL and server.requests[0].method == "POST"
    assert urls[-1] == config.SPACETRACK_LOGOUT_URL
    assert urls.count(config.SPACETRACK_LOGIN_URL) == 1
    paths = server.query_paths()
    assert len(paths) == 2
    assert "/decay_date/null-val/" in paths[0] and "/epoch/%3Enow-30/" in paths[0] and "format/json" in paths[0]
    assert server.requests[1].headers["User-Agent"].startswith("driftwatch/")


def test_rejected_login_raises(server):
    with server.client(Credentials(USER, "wrong")) as client, pytest.raises(SpaceTrackAuthError):
        client.gp_catalogue()


def test_expired_session_logs_in_again(server):
    with server.client() as client:
        client.gp_catalogue()
        server.expire_session = True
        client.gp_catalogue()
    urls = [str(r.url) for r in server.requests]
    assert urls.count(config.SPACETRACK_LOGIN_URL) == 2


def test_rate_limiter_sleeps_at_both_windows():
    clock = FakeClock()
    limiter = RateLimiter(per_minute=3, per_hour=5, clock=clock, sleep=clock.sleep)
    assert [limiter.wait() for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.wait() == pytest.approx(60.0, abs=0.1)  # fourth call in the same minute
    assert limiter.wait() == 0.0
    assert limiter.wait() == pytest.approx(3540.0, abs=0.1)  # sixth call in the same hour


def test_catalogue_cache_floor_and_daily_cap(server, tmp_path, caplog):
    t0 = datetime(2026, 9, 1, tzinfo=UTC)
    with server.client() as client:
        kw = dict(cache_dir=tmp_path, client=client)
        first = spacetrack.fetch_gp_catalogue(now=t0, **kw)
        within_floor = spacetrack.fetch_gp_catalogue(now=t0 + timedelta(hours=1, minutes=59), **kw)
        floored = spacetrack.fetch_gp_catalogue(
            now=t0 + timedelta(hours=1, minutes=59), min_interval=timedelta(0), **kw
        )
        pulls = [spacetrack.fetch_gp_catalogue(now=t0 + timedelta(hours=h, minutes=1), **kw) for h in (2, 4, 6)]
        with caplog.at_level("WARNING"):
            capped = spacetrack.fetch_gp_catalogue(now=t0 + timedelta(hours=8, minutes=2), **kw)
        next_day = spacetrack.fetch_gp_catalogue(now=t0 + timedelta(hours=26), **kw)
    assert not first.from_cache and first.n_objects == 8 and first.fetched_at == t0
    assert within_floor.from_cache and floored.from_cache
    assert all(not p.from_cache for p in pulls)
    assert capped.from_cache and "already pulled 4 times" in caplog.text
    assert not next_day.from_cache
    assert len(server.query_paths()) == 5
    meta = spacetrack.read_gp_meta(tmp_path)
    assert meta["n_objects"] == 8 and len(meta["pulls"]) == 4  # pulls older than a day are dropped
    assert spacetrack.load_gp_records(tmp_path)[0]["NORAD_CAT_ID"] == server.records[0]["NORAD_CAT_ID"]


def test_outage_keeps_stale_cache_but_bad_login_does_not(server, tmp_path):
    t0 = datetime(2026, 9, 1, tzinfo=UTC)
    with server.client() as client:
        spacetrack.fetch_gp_catalogue(cache_dir=tmp_path, client=client, now=t0)
        server.fail = True
        stale = spacetrack.fetch_gp_catalogue(cache_dir=tmp_path, client=client, now=t0 + timedelta(hours=3))
        server.fail = False
    assert stale.from_cache and stale.fetched_at == t0
    with server.client(Credentials(USER, "wrong")) as bad, pytest.raises(SpaceTrackAuthError):
        spacetrack.fetch_gp_catalogue(cache_dir=tmp_path, client=bad, now=t0 + timedelta(hours=6))


def test_offline_uses_cache_or_fails(server, tmp_path):
    with pytest.raises(FileNotFoundError):
        spacetrack.fetch_gp_catalogue(cache_dir=tmp_path, offline=True)
    with server.client() as client:
        spacetrack.fetch_gp_catalogue(cache_dir=tmp_path, client=client, now=datetime(2026, 9, 1, tzinfo=UTC))
    result = spacetrack.fetch_gp_catalogue(cache_dir=tmp_path, offline=True, now=datetime(2027, 1, 1, tzinfo=UTC))
    assert result.from_cache


def test_history_is_chunked_and_cached_for_ever(server, tmp_path):
    ids = [int(r["NORAD_CAT_ID"]) for r in server.records[:5]]
    start, end = date(2024, 5, 1), date(2024, 5, 20)
    with server.client() as client:
        records = spacetrack.fetch_gp_history(ids, start, end, cache_dir=tmp_path, client=client, chunk_size=2)
        again = spacetrack.fetch_gp_history(ids, start, end, cache_dir=tmp_path, client=client, chunk_size=2)
    paths = server.query_paths()
    assert len(paths) == 3  # 5 ids in chunks of 2
    assert all("/EPOCH/2024-05-01--2024-05-21/" in p for p in paths)  # end day inclusive
    assert sorted(int(r["NORAD_CAT_ID"]) for r in records) == sorted(ids)
    assert again == records
    assert len([p for p in spacetrack.history_cache_dir(tmp_path).glob("*.json") if ".meta" not in p.name]) == 3
    assert spacetrack.fetch_gp_history(ids, start, end, cache_dir=tmp_path, chunk_size=2, offline=True) == records
    with pytest.raises(FileNotFoundError):
        spacetrack.fetch_gp_history(ids, start, date(2024, 6, 1), cache_dir=tmp_path, chunk_size=2, offline=True)
    with pytest.raises(ValueError):
        spacetrack.fetch_gp_history(ids, end, start, cache_dir=tmp_path)
    assert spacetrack.fetch_gp_history([], start, end, cache_dir=tmp_path) == []


def test_credentials_never_reach_disk_or_logs(server, tmp_path, caplog):
    t0 = datetime(2026, 9, 1, tzinfo=UTC)
    with caplog.at_level("DEBUG"), server.client() as client:
        spacetrack.fetch_gp_catalogue(cache_dir=tmp_path, client=client, now=t0)
        spacetrack.fetch_gp_history(
            [int(server.records[0]["NORAD_CAT_ID"])],
            date(2024, 5, 1),
            date(2024, 5, 2),
            cache_dir=tmp_path,
            client=client,
        )
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert PASSWORD not in text and USER not in text, path
        json.loads(text)  # every cache file is plain JSON
    assert PASSWORD not in caplog.text and USER not in caplog.text
