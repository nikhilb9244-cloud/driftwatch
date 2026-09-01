"""Space-Track.org: the full public catalogue and element-set history.

CelesTrak's groups cover the operational population and a few debris clouds, about
19,000 objects. The dominant secondaries in conjunction screening are the rest: old
rocket bodies and the debris that belongs to no group, which only Space-Track's ``gp``
class holds, roughly 30,000 objects in all. Space-Track needs a free account and has
stricter rules than CelesTrak (documentation read 2026-09-01). This module enforces them:

* Fewer than 30 requests per minute and 300 per hour. :class:`RateLimiter` is a
  sliding window set below both.
* The catalogue at most once an hour by their rule. Here the cache has a two-hour floor
  and a cap of four pulls per rolling day, because the daily pipeline needs one.
* ``gp_history`` "once per lifetime": every history request is cached for ever under
  its (NORAD ids, date range) key and never asked for twice.
* Credentials come from ``SPACETRACK_USER`` and ``SPACETRACK_PASS``. They are sent only
  in the login POST body and are never written to cache metadata or logs.

Redistribution: the user agreement grants blanket approval to redistribute basic SSA
data (TLEs and OMMs, SATCAT, decay data) with citation; the text is quoted in
``docs/phase2-plan.md``. Conjunction Data Messages are excluded from that approval and
are never fetched by driftwatch.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from driftwatch import config

log = logging.getLogger(__name__)


class SpaceTrackError(RuntimeError):
    """Space-Track answered with something other than the requested records."""


class SpaceTrackAuthError(SpaceTrackError):
    """Credentials are missing or were rejected."""


@dataclass(frozen=True, repr=False)
class Credentials:
    """A Space-Track login. ``repr`` and ``str`` mask both fields so they never leak into a log or traceback."""

    user: str
    password: str

    def __repr__(self) -> str:
        return "Credentials(user=***, password=***)"

    __str__ = __repr__


def credentials_from_env(environ: Mapping[str, str] = os.environ) -> Credentials:
    """Read ``SPACETRACK_USER`` and ``SPACETRACK_PASS``; raise :class:`SpaceTrackAuthError` if either is unset."""
    user = environ.get(config.SPACETRACK_USER_ENV, "").strip()
    password = environ.get(config.SPACETRACK_PASS_ENV, "")
    if not user or not password:
        raise SpaceTrackAuthError(
            f"set {config.SPACETRACK_USER_ENV} and {config.SPACETRACK_PASS_ENV} in the environment "
            "(never in a file in the repository) to use Space-Track"
        )
    return Credentials(user, password)


class RateLimiter:
    """Sliding-window limiter: at most ``per_minute`` calls in any 60 s and ``per_hour`` in any 3600 s.

    ``clock`` and ``sleep`` are injectable so the tests can run it without waiting.
    """

    def __init__(
        self,
        per_minute: int = config.SPACETRACK_MAX_PER_MINUTE,
        per_hour: int = config.SPACETRACK_MAX_PER_HOUR,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._clock = clock
        self._sleep = sleep
        self._times: deque[float] = deque()

    def wait(self) -> float:
        """Block until one more request is allowed, record it, and return the seconds slept."""
        slept = 0.0
        while True:
            now = self._clock()
            while self._times and now - self._times[0] >= 3600.0:
                self._times.popleft()
            in_minute = [t for t in self._times if now - t < 60.0]
            delay = 0.0
            if len(self._times) >= self.per_hour:
                delay = 3600.0 - (now - self._times[0])
            elif len(in_minute) >= self.per_minute:
                delay = 60.0 - (now - in_minute[0])
            if delay <= 0.0:
                self._times.append(now)
                return slept
            delay += 0.01
            log.info("Space-Track rate limit: waiting %.1f s", delay)
            self._sleep(delay)
            slept += delay


def gp_catalogue_request(max_epoch_age_days: int = config.SPACETRACK_GP_MAX_EPOCH_AGE_DAYS) -> str:
    """Query path for the current catalogue: not decayed, epoch inside the last ``max_epoch_age_days``."""
    return (
        f"/class/gp/decay_date/null-val/epoch/%3Enow-{int(max_epoch_age_days)}/orderby/norad_cat_id%20asc/format/json"
    )


def gp_history_request(norad_ids: Iterable[int], start: date, end: date) -> str:
    """Query path for every element set of ``norad_ids`` with an epoch in ``[start, end)`` (dates, UTC).

    Space-Track's range operator ``a--b`` on a date column compares against midnight, so
    ``end`` is exclusive at 00:00 of that day; callers pass the day after the last day wanted.
    """
    ids = ",".join(str(int(i)) for i in sorted(set(norad_ids)))
    if not ids:
        raise ValueError("no NORAD ids")
    return (
        f"/class/gp_history/NORAD_CAT_ID/{ids}/EPOCH/{start:%Y-%m-%d}--{end:%Y-%m-%d}/orderby/EPOCH%20asc/format/json"
    )


class SpaceTrackClient:
    """A logged-in, rate-limited HTTP session against Space-Track's REST API.

    Logs in lazily on the first query, once, and re-logs in if the session cookie has
    expired. Use as a context manager so the session is logged out and closed.
    """

    def __init__(
        self,
        credentials: Credentials | None = None,
        *,
        timeout: float = config.HTTP_TIMEOUT_S,
        limiter: RateLimiter | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._credentials = credentials
        self._limiter = limiter or RateLimiter()
        self._http = httpx.Client(
            headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )
        self._logged_in = False

    def __enter__(self) -> SpaceTrackClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        """Log out (best effort) and close the HTTP client."""
        if self._logged_in:
            try:
                self._limiter.wait()
                self._http.get(config.SPACETRACK_LOGOUT_URL)
            except httpx.HTTPError:
                pass
            self._logged_in = False
        self._http.close()

    def login(self) -> None:
        """POST the credentials. Space-Track answers a bad login with HTTP 200 and ``{"Login":"Failed"}``."""
        creds = self._credentials or credentials_from_env()
        self._credentials = creds
        self._limiter.wait()
        log.info("Logging in to Space-Track")
        response = self._http.post(
            config.SPACETRACK_LOGIN_URL, data={"identity": creds.user, "password": creds.password}
        )
        if response.status_code != 200 or "Failed" in response.text:
            raise SpaceTrackAuthError(
                f"Space-Track rejected the login (HTTP {response.status_code}); "
                f"check {config.SPACETRACK_USER_ENV} and {config.SPACETRACK_PASS_ENV}"
            )
        self._logged_in = True

    def query(self, request: str) -> list[dict[str, Any]]:
        """Run one ``basicspacedata`` query and return the JSON record list.

        ``request`` is the path after ``/basicspacedata/query`` (see
        :func:`gp_catalogue_request`). One retry after a fresh login on 401/403.
        """
        if not self._logged_in:
            self.login()
        url = config.SPACETRACK_QUERY_URL + request
        response = self._get(url)
        if response.status_code in (401, 403):
            log.info("Space-Track session expired; logging in again")
            self._logged_in = False
            self.login()
            response = self._get(url)
        response.raise_for_status()
        try:
            records = response.json()
        except ValueError as exc:
            raise SpaceTrackError(f"Space-Track returned non-JSON for {request}: {response.text[:120]!r}") from exc
        if not isinstance(records, list):
            raise SpaceTrackError(f"Unexpected JSON shape for {request}: {str(records)[:120]!r}")
        return records

    def _get(self, url: str) -> httpx.Response:
        self._limiter.wait()
        log.debug("Space-Track GET %s", url)
        return self._http.get(url)

    def gp_catalogue(self, max_epoch_age_days: int = config.SPACETRACK_GP_MAX_EPOCH_AGE_DAYS) -> list[dict[str, Any]]:
        """The current catalogue as OMM-style records (field values are strings, as Space-Track sends them)."""
        return self.query(gp_catalogue_request(max_epoch_age_days))

    def gp_history(self, norad_ids: Iterable[int], start: date, end: date) -> list[dict[str, Any]]:
        """Every element set for ``norad_ids`` with an epoch in ``[start, end)``; see :func:`gp_history_request`."""
        return self.query(gp_history_request(norad_ids, start, end))


# --- catalogue cache -----------------------------------------------------------------


@dataclass(frozen=True)
class SpaceTrackFetch:
    """Outcome of :func:`fetch_gp_catalogue`."""

    path: Path
    fetched_at: datetime
    from_cache: bool
    n_objects: int


def spacetrack_cache_dir(cache_dir: Path = config.CACHE_DIR) -> Path:
    """Directory holding the raw Space-Track downloads."""
    return cache_dir / "spacetrack"


def gp_path(cache_dir: Path = config.CACHE_DIR) -> Path:
    """Cached catalogue JSON."""
    return spacetrack_cache_dir(cache_dir) / "gp.json"


def _meta_path(json_path: Path) -> Path:
    return json_path.with_name(json_path.stem + ".meta.json")


def read_gp_meta(cache_dir: Path = config.CACHE_DIR) -> dict[str, Any] | None:
    """Cache metadata for the catalogue, or ``None`` when nothing is cached."""
    path = gp_path(cache_dir)
    meta_path = _meta_path(path)
    if not (path.exists() and meta_path.exists()):
        return None
    with meta_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _fmt_age(age: timedelta) -> str:
    total = int(age.total_seconds())
    hours, rem = divmod(total, 3600)
    return f"{hours}h{rem // 60:02d}m"


def fetch_gp_catalogue(
    *,
    cache_dir: Path = config.CACHE_DIR,
    min_interval: timedelta = config.MIN_SPACETRACK_GP_INTERVAL,
    max_pulls_per_day: int = config.MAX_SPACETRACK_GP_PULLS_PER_DAY,
    max_epoch_age_days: int = config.SPACETRACK_GP_MAX_EPOCH_AGE_DAYS,
    client: SpaceTrackClient | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> SpaceTrackFetch:
    """Return the cached catalogue, downloading only when the cache rules allow it.

    Rules, in order: a cache younger than ``min_interval`` (floor two hours) is reused;
    a cache is reused when ``max_pulls_per_day`` downloads already happened in the last
    24 hours; ``offline`` never touches the network; a failed download keeps the stale
    cache, except for a rejected login, which is raised so the operator finds out.
    """
    min_interval = max(min_interval, config.MIN_SPACETRACK_GP_INTERVAL)
    now = now or datetime.now(UTC)
    path = gp_path(cache_dir)
    meta = read_gp_meta(cache_dir)
    pulls: list[datetime] = []

    if meta is not None:
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
        age = now - fetched_at
        pulls = [p for p in (datetime.fromisoformat(s) for s in meta.get("pulls", [])) if now - p < timedelta(days=1)]
        cached = SpaceTrackFetch(path, fetched_at, True, int(meta["n_objects"]))
        if offline or age < min_interval:
            log.info("Using cached Space-Track catalogue (age %s)", _fmt_age(age))
            return cached
        if len(pulls) >= max_pulls_per_day:
            log.warning(
                "Space-Track catalogue already pulled %d times in the last day; using cache (age %s)",
                len(pulls),
                _fmt_age(age),
            )
            return cached

    if offline:
        raise FileNotFoundError("No cached Space-Track catalogue and offline=True")

    own_client = client is None
    client = client or SpaceTrackClient()
    try:
        try:
            records = client.gp_catalogue(max_epoch_age_days)
        except SpaceTrackAuthError:
            raise
        except (httpx.HTTPError, SpaceTrackError) as exc:
            if meta is not None:
                fetched_at = datetime.fromisoformat(meta["fetched_at"])
                log.warning("Space-Track fetch failed (%s); keeping stale cache from %s", exc, fetched_at)
                return SpaceTrackFetch(path, fetched_at, True, int(meta["n_objects"]))
            raise
    finally:
        if own_client:
            client.close()

    _atomic_write_text(path, json.dumps(records, separators=(",", ":")))
    _atomic_write_text(
        _meta_path(path),
        json.dumps(
            {
                "url": config.SPACETRACK_QUERY_URL + gp_catalogue_request(max_epoch_age_days),
                "fetched_at": now.isoformat(),
                "n_objects": len(records),
                "max_epoch_age_days": max_epoch_age_days,
                "pulls": [p.isoformat() for p in [*pulls, now]],
                "user_agent": config.USER_AGENT,
            },
            indent=2,
        ),
    )
    log.info("Cached %d Space-Track records", len(records))
    return SpaceTrackFetch(path, now, False, len(records))


def load_gp_records(cache_dir: Path = config.CACHE_DIR) -> list[dict[str, Any]]:
    """Read the cached catalogue records from disk."""
    with gp_path(cache_dir).open(encoding="utf-8") as fh:
        return json.load(fh)


# --- history cache -------------------------------------------------------------------


def history_cache_dir(cache_dir: Path = config.CACHE_DIR) -> Path:
    """Directory holding one JSON file per gp_history request."""
    return spacetrack_cache_dir(cache_dir) / "gp_history"


def history_request_key(norad_ids: Iterable[int], start: date, end: date) -> str:
    """Stable file stem for one gp_history request: date range, id count and a digest of the ids."""
    ids = sorted({int(i) for i in norad_ids})
    digest = hashlib.sha1(f"{ids}|{start:%Y-%m-%d}|{end:%Y-%m-%d}".encode()).hexdigest()[:16]
    return f"{start:%Y%m%d}_{end:%Y%m%d}_{len(ids)}ids_{digest}"


def _chunks(items: list[int], size: int) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def fetch_gp_history(
    norad_ids: Iterable[int],
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    chunk_size: int = config.SPACETRACK_HISTORY_CHUNK,
    client: SpaceTrackClient | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> list[dict[str, Any]]:
    """Every element set for ``norad_ids`` with an epoch on the days ``start`` to ``end`` inclusive.

    The ids are sorted and split into chunks of ``chunk_size``; each chunk is one request,
    cached permanently under :func:`history_request_key`. Space-Track's guidance for
    ``gp_history`` is "once per lifetime", so a cached chunk is never re-requested.
    """
    ids = sorted({int(i) for i in norad_ids})
    if not ids:
        return []
    if end < start:
        raise ValueError("end is before start")
    query_end = end + timedelta(days=1)  # the range operator is exclusive at midnight of ``end``
    now = now or datetime.now(UTC)
    out_dir = history_cache_dir(cache_dir)

    records: list[dict[str, Any]] = []
    own_client = client is None
    try:
        for chunk in _chunks(ids, chunk_size):
            key = history_request_key(chunk, start, query_end)
            path = out_dir / f"{key}.json"
            if path.exists():
                log.info("Using cached gp_history %s", key)
                with path.open(encoding="utf-8") as fh:
                    records.extend(json.load(fh))
                continue
            if offline:
                raise FileNotFoundError(f"No cached gp_history for {key} and offline=True")
            if client is None:
                client = SpaceTrackClient()
            log.info("Fetching gp_history for %d ids, %s to %s", len(chunk), start, end)
            chunk_records = client.gp_history(chunk, start, query_end)
            _atomic_write_text(path, json.dumps(chunk_records, separators=(",", ":")))
            _atomic_write_text(
                _meta_path(path),
                json.dumps(
                    {
                        "norad_ids": chunk,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "query": gp_history_request(chunk, start, query_end),
                        "fetched_at": now.isoformat(),
                        "n_records": len(chunk_records),
                    },
                    indent=2,
                ),
            )
            records.extend(chunk_records)
    finally:
        if own_client and client is not None:
            client.close()
    return records
