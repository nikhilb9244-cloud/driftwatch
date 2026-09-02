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
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

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


def gp_history_request(
    norad_ids: Iterable[int], start: date, end: date, *, predicates: Sequence[str] | None = None
) -> str:
    """Query path for every element set of ``norad_ids`` with an epoch in ``[start, end)`` (dates, UTC).

    Space-Track's range operator ``a--b`` on a date column compares against midnight, so
    ``end`` is exclusive at 00:00 of that day; callers pass the day after the last day wanted.
    ``predicates`` restricts the returned fields (Space-Track's ``predicates`` operator).
    """
    ids = ",".join(str(int(i)) for i in sorted(set(norad_ids)))
    if not ids:
        raise ValueError("no NORAD ids")
    fields = f"/predicates/{','.join(predicates)}" if predicates else ""
    return (
        f"/class/gp_history/NORAD_CAT_ID/{ids}/EPOCH/{start:%Y-%m-%d}--{end:%Y-%m-%d}"
        f"/orderby/EPOCH%20asc{fields}/format/json"
    )


def chunk_ids_by_url(
    norad_ids: Iterable[int],
    start: date,
    end: date,
    *,
    url_budget: int = config.SPACETRACK_HISTORY_URL_BUDGET,
    predicates: Sequence[str] | None = config.SPACETRACK_HISTORY_PREDICATES,
) -> list[list[int]]:
    """Split sorted ids into consecutive chunks whose request URL stays within ``url_budget`` characters.

    The decision at the Step 0 review: as many ids per request as fit a URL of about
    8,000 characters, sorted so that a repeated run with the same ids builds the same
    chunks and hits the same cached requests.
    """
    ids = sorted({int(i) for i in norad_ids})
    if not ids:
        return []
    base = len(config.SPACETRACK_QUERY_URL) + len(gp_history_request([ids[0]], start, end, predicates=predicates))
    base -= len(str(ids[0]))
    chunks: list[list[int]] = []
    current: list[int] = []
    length = base
    for i in ids:
        extra = len(str(i)) + (1 if current else 0)
        if current and length + extra > url_budget:
            chunks.append(current)
            current, length = [], base
            extra = len(str(i))
        current.append(i)
        length += extra
    if current:
        chunks.append(current)
    return chunks


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

    def gp_history(
        self, norad_ids: Iterable[int], start: date, end: date, *, predicates: Sequence[str] | None = None
    ) -> list[dict[str, Any]]:
        """Every element set for ``norad_ids`` with an epoch in ``[start, end)``; see :func:`gp_history_request`."""
        return self.query(gp_history_request(norad_ids, start, end, predicates=predicates))


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


# A chunk that Space-Track cannot serve in one go (URL too long, a timeout, a 5xx on a
# large response) is halved and retried, down to this many ids; below it the error stands.
HISTORY_MIN_SPLIT_IDS = 8


def _query_history_chunk(
    client: SpaceTrackClient, ids: list[int], start: date, query_end: date, predicates: Sequence[str] | None
) -> tuple[list[dict[str, Any]], list[list[int]]]:
    """One gp_history request with fallbacks for a request that is too big.

    A 413 or 414 (the URL was too long for Space-Track after all), or a 403 on a chunk of
    more than one id (Space-Track's front end answers a generic 403 to a URL over about
    4 KB, measured 2026-09-02), splits the chunk in two and fetches the halves; so does a
    timeout or a 5xx on a chunk of more than :data:`HISTORY_MIN_SPLIT_IDS` ids. A 400
    with ``predicates`` set retries for the full records. Returns the records and the
    list of id chunks actually requested, so the caller caches each request under its
    own key.
    """

    def split(reason: str) -> tuple[list[dict[str, Any]], list[list[int]]]:
        half = len(ids) // 2
        log.warning("Space-Track could not serve a %d-id gp_history request (%s); splitting", len(ids), reason)
        left, left_chunks = _query_history_chunk(client, ids[:half], start, query_end, predicates)
        right, right_chunks = _query_history_chunk(client, ids[half:], start, query_end, predicates)
        return left + right, left_chunks + right_chunks

    try:
        return client.gp_history(ids, start, query_end, predicates=predicates), [ids]
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in (403, 413, 414) and len(ids) > 1:
            return split(f"HTTP {status}")
        if predicates and status == 400:
            log.warning("Space-Track rejected the predicates operator (HTTP %d); requesting full records", status)
            return client.gp_history(ids, start, query_end), [ids]
        if status >= 500 and len(ids) > HISTORY_MIN_SPLIT_IDS:
            return split(f"HTTP {status}")
        raise
    except httpx.TimeoutException as exc:
        if len(ids) > HISTORY_MIN_SPLIT_IDS:
            return split(f"timeout: {exc.__class__.__name__}")
        raise


def fetch_gp_history(
    norad_ids: Iterable[int],
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    chunk_size: int = config.SPACETRACK_HISTORY_CHUNK,
    url_budget: int | None = None,
    predicates: Sequence[str] | None = None,
    client: SpaceTrackClient | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> list[dict[str, Any]]:
    """Every element set for ``norad_ids`` with an epoch on the days ``start`` to ``end`` inclusive.

    The ids are sorted and split into chunks: of ``chunk_size`` ids, or, when ``url_budget``
    is given, of as many ids as fit a request URL that long (the Step 3 backfill). Each
    chunk is one request, cached permanently under :func:`history_request_key`.
    Space-Track's guidance for ``gp_history`` is "once per lifetime", so a cached chunk
    is never re-requested. ``predicates`` limits the fields Space-Track returns.
    """
    ids = sorted({int(i) for i in norad_ids})
    if not ids:
        return []
    if end < start:
        raise ValueError("end is before start")
    query_end = end + timedelta(days=1)  # the range operator is exclusive at midnight of ``end``
    now = now or datetime.now(UTC)
    out_dir = history_cache_dir(cache_dir)
    if url_budget is not None:
        chunks = chunk_ids_by_url(ids, start, query_end, url_budget=url_budget, predicates=predicates)
    else:
        chunks = _chunks(ids, chunk_size)

    records: list[dict[str, Any]] = []
    own_client = client is None
    try:
        for chunk in chunks:
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
                client = SpaceTrackClient(timeout=config.SPACETRACK_HISTORY_TIMEOUT_S)
            log.info("Fetching gp_history for %d ids, %s to %s", len(chunk), start, end)
            chunk_records, requested = _query_history_chunk(client, chunk, start, query_end, predicates)
            if requested != [chunk]:
                # The chunk was split; cache each part under its own key so a repeat finds them.
                for part in requested:
                    part_ids = set(part)
                    part_records = [r for r in chunk_records if int(r["NORAD_CAT_ID"]) in part_ids]
                    _write_history_cache(out_dir, part, start, end, query_end, part_records, now, predicates)
            else:
                _write_history_cache(out_dir, chunk, start, end, query_end, chunk_records, now, predicates)
            records.extend(chunk_records)
    finally:
        if own_client and client is not None:
            client.close()
    return records


def _write_history_cache(
    out_dir: Path,
    ids: list[int],
    start: date,
    end: date,
    query_end: date,
    records: list[dict[str, Any]],
    now: datetime,
    predicates: Sequence[str] | None,
) -> None:
    key = history_request_key(ids, start, query_end)
    path = out_dir / f"{key}.json"
    _atomic_write_text(path, json.dumps(records, separators=(",", ":")))
    _atomic_write_text(
        _meta_path(path),
        json.dumps(
            {
                "norad_ids": ids,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "query": gp_history_request(ids, start, query_end, predicates=predicates),
                "fetched_at": now.isoformat(),
                "n_records": len(records),
            },
            indent=2,
        ),
    )


def history_coverage(cache_dir: Path = config.CACHE_DIR) -> pd.DataFrame:
    """Which (NORAD id, day range) combinations have already been requested from gp_history.

    Read from the request metadata in the cache: one row per id per request with the
    inclusive ``start`` and ``end`` days. The backfill uses it to skip ids whose window
    is already covered, honouring Space-Track's "once per lifetime" guidance even when
    the chunking changes between runs.
    """
    rows: list[tuple[int, date, date]] = []
    out_dir = history_cache_dir(cache_dir)
    if out_dir.exists():
        for meta_path in sorted(out_dir.glob("*.meta.json")):
            with meta_path.open(encoding="utf-8") as fh:
                meta = json.load(fh)
            start = date.fromisoformat(meta["start"])
            end = date.fromisoformat(meta["end"])
            rows.extend((int(i), start, end) for i in meta["norad_ids"])
    if not rows:
        return pd.DataFrame({"norad_id": pd.Series(dtype="int64"), "start": [], "end": []})
    df = pd.DataFrame(rows, columns=["norad_id", "start", "end"])
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    return df


def covered_ids(coverage: pd.DataFrame, norad_ids: Iterable[int], start: date, end: date) -> set[int]:
    """The ids among ``norad_ids`` that some single cached request already covers for all of ``[start, end]``."""
    wanted = {int(i) for i in norad_ids}
    if coverage.empty or not wanted:
        return set()
    sub = coverage[coverage["norad_id"].isin(wanted)]
    ok = sub[(sub["start"] <= pd.Timestamp(start)) & (sub["end"] >= pd.Timestamp(end))]
    return {int(i) for i in ok["norad_id"].unique()}
