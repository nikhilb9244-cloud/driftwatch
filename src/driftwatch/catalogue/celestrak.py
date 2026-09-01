"""Polite client for CelesTrak general perturbations (GP) element sets.

CelesTrak publishes the public catalogue as OMM (Orbit Mean-elements Message) records,
one query per predefined group. Their usage rules are simple: identify yourself, and do
not fetch a group more often than every two hours. This module enforces both. Every
download is written to an on-disk cache with a sidecar metadata file, and a cache entry
younger than the minimum interval is returned without touching the network.

The raw JSON is kept verbatim so that a snapshot can always be rebuilt from cache.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from driftwatch import config

log = logging.getLogger(__name__)


class CelesTrakError(RuntimeError):
    """Raised when CelesTrak returns something other than a GP record list."""


@dataclass(frozen=True)
class GroupFetch:
    """Outcome of fetching one CelesTrak group."""

    group: str
    path: Path
    fetched_at: datetime
    from_cache: bool
    n_objects: int


def gp_cache_dir(cache_dir: Path = config.CACHE_DIR) -> Path:
    """Directory holding the cached GP JSON for each group."""
    return cache_dir / "celestrak" / "gp"


def _json_path(group: str, cache_dir: Path) -> Path:
    return gp_cache_dir(cache_dir) / f"{group}.json"


def _meta_path(json_path: Path) -> Path:
    return json_path.with_name(json_path.stem + ".meta.json")


def read_meta(group: str, cache_dir: Path = config.CACHE_DIR) -> dict[str, Any] | None:
    """Return the cache metadata for ``group`` or ``None`` when nothing is cached."""
    json_path = _json_path(group, cache_dir)
    meta_path = _meta_path(json_path)
    if not (json_path.exists() and meta_path.exists()):
        return None
    with meta_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def make_client(timeout: float = config.HTTP_TIMEOUT_S) -> httpx.Client:
    """An HTTP client with the descriptive User-Agent CelesTrak asks for."""
    return httpx.Client(
        headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"},
        timeout=timeout,
        follow_redirects=True,
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def download_group(group: str, client: httpx.Client) -> list[dict[str, Any]]:
    """Download one group as a list of OMM records. One request, no retries in a loop.

    CelesTrak answers unknown or empty groups with a plain-text message and HTTP 200,
    so the body is checked before it is parsed.
    """
    log.info("Downloading CelesTrak group %r", group)
    response = client.get(config.CELESTRAK_GP_URL, params={"GROUP": group, "FORMAT": "json"})
    response.raise_for_status()
    text = response.text
    if not text.lstrip().startswith("["):
        raise CelesTrakError(f"CelesTrak returned no GP data for group {group!r}: {text[:120]!r}")
    records = json.loads(text)
    if not isinstance(records, list):
        raise CelesTrakError(f"Unexpected JSON shape for group {group!r}")
    return records


def fetch_group(
    group: str,
    *,
    cache_dir: Path = config.CACHE_DIR,
    min_interval: timedelta = config.MIN_GROUP_FETCH_INTERVAL,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> GroupFetch:
    """Return cached GP data for ``group``, downloading only when the cache is stale.

    Parameters
    ----------
    group:
        A CelesTrak group name such as ``"active"`` or ``"starlink"``.
    min_interval:
        Minimum age of the cache before a new download is attempted. Values below the
        CelesTrak floor of two hours are raised to it.
    offline:
        Never touch the network; raise if nothing is cached.
    """
    min_interval = max(min_interval, config.MIN_GROUP_FETCH_INTERVAL)
    now = now or datetime.now(UTC)
    json_path = _json_path(group, cache_dir)
    meta = read_meta(group, cache_dir)

    if meta is not None:
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
        age = now - fetched_at
        if offline or age < min_interval:
            log.info("Using cached %r (age %s)", group, _fmt_age(age))
            return GroupFetch(group, json_path, fetched_at, True, int(meta["n_objects"]))

    if offline:
        raise FileNotFoundError(f"No cached data for group {group!r} and offline=True")

    own_client = client is None
    client = client or make_client()
    try:
        try:
            records = download_group(group, client)
        except (httpx.HTTPError, CelesTrakError) as exc:
            if meta is not None:
                fetched_at = datetime.fromisoformat(meta["fetched_at"])
                log.warning("Fetch of %r failed (%s); keeping stale cache from %s", group, exc, fetched_at)
                return GroupFetch(group, json_path, fetched_at, True, int(meta["n_objects"]))
            raise
    finally:
        if own_client:
            client.close()

    fetched_at = now
    _atomic_write_text(json_path, json.dumps(records, separators=(",", ":")))
    _atomic_write_text(
        _meta_path(json_path),
        json.dumps(
            {
                "group": group,
                "url": config.CELESTRAK_GP_URL,
                "fetched_at": fetched_at.isoformat(),
                "n_objects": len(records),
                "user_agent": config.USER_AGENT,
            },
            indent=2,
        ),
    )
    log.info("Cached %d records for %r", len(records), group)
    return GroupFetch(group, json_path, fetched_at, False, len(records))


def fetch_groups(
    groups: tuple[str, ...] | list[str] = config.DEFAULT_GROUPS,
    *,
    cache_dir: Path = config.CACHE_DIR,
    min_interval: timedelta = config.MIN_GROUP_FETCH_INTERVAL,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> list[GroupFetch]:
    """Fetch several groups with one shared HTTP client. See :func:`fetch_group`."""
    own_client = client is None and not offline
    client = client if client is not None else (make_client() if not offline else None)
    try:
        return [
            fetch_group(
                group,
                cache_dir=cache_dir,
                min_interval=min_interval,
                client=client,
                now=now,
                offline=offline,
            )
            for group in groups
        ]
    finally:
        if own_client and client is not None:
            client.close()


def load_group_records(group: str, cache_dir: Path = config.CACHE_DIR) -> list[dict[str, Any]]:
    """Read the cached OMM records for ``group`` from disk."""
    with _json_path(group, cache_dir).open(encoding="utf-8") as fh:
        return json.load(fh)


def _fmt_age(age: timedelta) -> str:
    total = int(age.total_seconds())
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    return f"{hours}h{minutes:02d}m"
