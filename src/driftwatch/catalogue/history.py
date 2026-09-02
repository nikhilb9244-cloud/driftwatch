"""Element-set history: every element set we have seen for an object, from any source.

Two things in later steps need more than the latest element set per object:

* Step 3 estimates orbit uncertainty by propagating an older element set to a newer
  one's epoch and measuring the disagreement. That needs several element sets per
  object spread over days.
* Phase 3 replays past storms, which needs element sets from around those dates.

The snapshots already hold one element set per object per fetch. This module adds
``data/history/gph_<stamp>.parquet`` files written from Space-Track ``gp_history``
pulls, with the element columns of the snapshot schema plus ``source`` and
``fetched_at``; a consolidated index, ``data/history/index.parquet``, keyed by
(NORAD id, epoch) and recording which file holds each element set, so a lookup by
object opens only the files that hold it; :func:`load_history`, which concatenates
history files and snapshots and keeps one row per (NORAD id, epoch); and
:func:`backfill`, the Step 3 batched pull for a fleet and its Stage A survivors.

Physics note: an element set is a fit to tracking data over a few days, tagged with an
epoch. Two element sets for the same object with different epochs are two different
fits, and the difference between them after propagating one to the other's epoch is how
much the fits disagree, not how far either is from the truth. ``docs/screening.md``
explains why that is a floor on the error rather than a measurement of it.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import config
from driftwatch.catalogue import spacetrack
from driftwatch.catalogue.snapshot import (
    OMM_FIELDS,
    SCHEMA_VERSION,
    SNAPSHOT_SCHEMA,
    list_snapshots,
    read_snapshot,
    records_to_frame,
)
from driftwatch.orbit.time import parse_utc, stamp

log = logging.getLogger(__name__)

HISTORY_COLUMNS: tuple[str, ...] = (*OMM_FIELDS.values(), "source", "fetched_at")
HISTORY_SCHEMA = pa.schema([SNAPSHOT_SCHEMA.field(name) for name in HISTORY_COLUMNS])
INDEX_SCHEMA = pa.schema(
    [
        pa.field("norad_id", pa.int64()),
        pa.field("epoch", pa.timestamp("us", tz="UTC")),
        pa.field("file", pa.string()),
    ]
)
# Row groups small enough that a lookup of a few objects skips most of a large file.
HISTORY_ROW_GROUP = 50_000


def _empty_frame() -> pd.DataFrame:
    return HISTORY_SCHEMA.empty_table().to_pandas()


def _utc(t: datetime) -> pd.Timestamp:
    ts = pd.Timestamp(t)
    return ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Common dtypes so frames from different sources concatenate cleanly."""
    df = df.loc[:, list(HISTORY_COLUMNS)].copy()
    df["norad_id"] = df["norad_id"].astype("int64")
    df["epoch"] = pd.to_datetime(df["epoch"], utc=True).astype("datetime64[us, UTC]")
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True).astype("datetime64[us, UTC]")
    df["source"] = df["source"].astype("string")
    return df


def frame_from_records(
    records: Sequence[Mapping[str, Any]], *, source: str = "spacetrack", fetched_at: datetime | None = None
) -> pd.DataFrame:
    """Turn raw OMM records (Space-Track ``gp_history`` or ``gp``) into a history frame.

    Space-Track may return the same epoch twice for an object (re-issued element sets);
    the last one in ``records`` is kept.
    """
    if not records:
        return _empty_frame()
    df = records_to_frame(records)
    df["source"] = source
    df["fetched_at"] = pd.Timestamp(fetched_at or datetime.now(UTC)).tz_convert("UTC")
    df = _normalise(df)
    df = df.sort_values(["norad_id", "epoch"]).drop_duplicates(["norad_id", "epoch"], keep="last")
    return df.reset_index(drop=True)


def history_path(fetched_at: datetime, history_dir: Path = config.HISTORY_DIR) -> Path:
    """File name for a history pull made at ``fetched_at``."""
    return history_dir / f"gph_{stamp(fetched_at)}.parquet"


def write_history(
    df: pd.DataFrame, path: Path, *, metadata: Mapping[str, str] | None = None, update: bool = True
) -> Path:
    """Write a history frame to parquet with the schema version and any extra metadata.

    Rows are sorted by object and epoch and written in small row groups so that reads
    filtered on ``norad_id`` skip most of the file. The index is updated afterwards
    unless ``update`` is False.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df = _normalise(df).sort_values(["norad_id", "epoch"]).reset_index(drop=True)
    table = pa.Table.from_pandas(df, schema=HISTORY_SCHEMA, preserve_index=False)
    meta = {b"driftwatch_schema_version": str(SCHEMA_VERSION).encode()}
    for key, value in (metadata or {}).items():
        meta[key.encode()] = value.encode()
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **meta})
    pq.write_table(table, path, compression="zstd", row_group_size=HISTORY_ROW_GROUP)
    log.info("Wrote %d element sets for %d objects to %s", len(df), df["norad_id"].nunique(), path)
    if update:
        update_index(path, df, history_dir=path.parent)
    return path


def read_history(path: Path, *, norad_ids: Iterable[int] | None = None) -> pd.DataFrame:
    """Read one history file, optionally only the rows of ``norad_ids`` (row groups are skipped by statistics)."""
    filters = None
    if norad_ids is not None:
        filters = [("norad_id", "in", sorted({int(i) for i in norad_ids}))]
    return _normalise(pq.read_table(path, filters=filters).to_pandas())


def list_history(history_dir: Path = config.HISTORY_DIR) -> list[Path]:
    """All history files, oldest first."""
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob("gph_*.parquet"))


# --------------------------------------------------------------------------------------
# The index


def index_path(history_dir: Path = config.HISTORY_DIR) -> Path:
    """``data/history/index.parquet``: (norad_id, epoch) -> file name, for every history file."""
    return history_dir / "index.parquet"


def _index_rows(path: Path, df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "norad_id": df["norad_id"].astype("int64").to_numpy(),
            "epoch": pd.to_datetime(df["epoch"], utc=True).astype("datetime64[us, UTC]").to_numpy(),
            "file": path.name,
        }
    )


def _empty_index() -> pd.DataFrame:
    return INDEX_SCHEMA.empty_table().to_pandas()


def _write_index(index: pd.DataFrame, history_dir: Path) -> Path:
    path = index_path(history_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    index = index.sort_values(["norad_id", "epoch"]).drop_duplicates(["norad_id", "epoch"], keep="last")
    table = pa.Table.from_pandas(index.reset_index(drop=True), schema=INDEX_SCHEMA, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return path


def rebuild_index(history_dir: Path = config.HISTORY_DIR) -> pd.DataFrame:
    """Rebuild the index from the history files (it is derived data and can always be regenerated)."""
    frames = []
    for path in list_history(history_dir):
        cols = pq.read_table(path, columns=["norad_id", "epoch"]).to_pandas()
        frames.append(_index_rows(path, cols))
    index = pd.concat(frames, ignore_index=True) if frames else _empty_index()
    if history_dir.exists():
        _write_index(index, history_dir)
    log.info("Rebuilt history index: %d element sets in %d files", len(index), len(frames))
    return index


def update_index(path: Path, df: pd.DataFrame, *, history_dir: Path = config.HISTORY_DIR) -> pd.DataFrame:
    """Add one freshly written history file to the index (creating the index if needed)."""
    existing = load_index(history_dir, rebuild=False)
    index = pd.concat([existing, _index_rows(path, df)], ignore_index=True)
    _write_index(index, history_dir)
    return index


def load_index(history_dir: Path = config.HISTORY_DIR, *, rebuild: bool = True) -> pd.DataFrame:
    """The index; rebuilt from the files when it is missing or stale and ``rebuild`` is True."""
    path = index_path(history_dir)
    files = {p.name for p in list_history(history_dir)}
    if path.exists():
        index = pq.read_table(path).to_pandas()
        index["epoch"] = pd.to_datetime(index["epoch"], utc=True).astype("datetime64[us, UTC]")
        indexed = set(index["file"].unique())
        if not rebuild or indexed == files:
            return index
        log.info("History index out of date (%d files indexed, %d present)", len(indexed), len(files))
    elif not files or not rebuild:
        return _empty_index()
    return rebuild_index(history_dir)


def load_history(
    *,
    norad_ids: Iterable[int] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    history_dir: Path = config.HISTORY_DIR,
    snapshot_dir: Path = config.SNAPSHOT_DIR,
    include_snapshots: bool = True,
) -> pd.DataFrame:
    """Every element set we hold, one row per (NORAD id, epoch), sorted by object then epoch.

    History files and (by default) snapshots are concatenated; where the same epoch
    appears in several places the row read last wins, which is the newest snapshot.
    ``start`` and ``end`` filter on epoch (inclusive, UTC). With ``norad_ids`` the index
    picks the history files to open and each is read with a row-group filter.
    """
    ids = sorted({int(i) for i in norad_ids}) if norad_ids is not None else None
    if ids is not None:
        index = load_index(history_dir)
        hits = index[index["norad_id"].isin(ids)] if len(index) else index
        files = [history_dir / name for name in sorted(hits["file"].unique())]
        frames = [read_history(p, norad_ids=ids) for p in files if p.exists()]
    else:
        frames = [read_history(p) for p in list_history(history_dir)]
    if include_snapshots:
        for p in list_snapshots(snapshot_dir):
            snap = _normalise(read_snapshot(p))
            frames.append(snap[snap["norad_id"].isin(ids)] if ids is not None else snap)
    if not frames:
        return _empty_frame()
    df = pd.concat(frames, ignore_index=True)
    if start is not None:
        df = df[df["epoch"] >= _utc(start)]
    if end is not None:
        df = df[df["epoch"] <= _utc(end)]
    df = df.sort_values(["norad_id", "epoch"]).drop_duplicates(["norad_id", "epoch"], keep="last")
    return df.reset_index(drop=True)


def history_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Counts and spacing, for logs: objects, element sets, sets per object, epoch span."""
    if df.empty:
        return {"n_records": 0, "n_objects": 0}
    per_object = df.groupby("norad_id")["epoch"].agg(["count", "min", "max"])
    span_days = (per_object["max"] - per_object["min"]).dt.total_seconds() / 86400.0
    return {
        "n_records": int(len(df)),
        "n_objects": int(len(per_object)),
        "sets_per_object": {
            "min": int(per_object["count"].min()),
            "median": float(per_object["count"].median()),
            "max": int(per_object["count"].max()),
        },
        "span_days_median": float(span_days.median()),
        "epoch_min": per_object["min"].min().isoformat(),
        "epoch_max": per_object["max"].max().isoformat(),
    }


# --------------------------------------------------------------------------------------
# The Step 3 backfill


@dataclass(frozen=True)
class BackfillResult:
    """What a backfill did: the window, how many ids it was asked for, how many it fetched, and the file."""

    start: date
    end: date
    n_requested: int
    n_already_covered: int
    n_fetched_ids: int
    n_requests: int
    n_cached_requests: int
    n_records: int
    path: Path | None


def backfill_window(end: datetime, days: int = config.HISTORY_BACKFILL_DAYS) -> tuple[date, date]:
    """The whole-day window ``[end - (days - 1), end]`` ending on the day of ``end`` (UTC)."""
    end_day = parse_utc(end).date()
    return end_day - timedelta(days=int(days) - 1), end_day


def stored_through(norad_ids: Iterable[int], history_dir: Path = config.HISTORY_DIR) -> dict[int, date]:
    """The day of the newest stored element set for each of ``norad_ids``, from the index."""
    ids = {int(i) for i in norad_ids}
    index = load_index(history_dir, rebuild=False)
    if index.empty or not ids:
        return {}
    sub = index[index["norad_id"].isin(ids)]
    if sub.empty:
        return {}
    newest = sub.groupby("norad_id")["epoch"].max()
    return {int(k): v.date() for k, v in newest.items()}


def _needed_ranges(
    coverage: pd.DataFrame,
    ids: Sequence[int],
    start: date,
    end: date,
    stored: Mapping[int, date] | None = None,
) -> dict[tuple[date, date], list[int]]:
    """Group ids by the part of ``[start, end]`` that neither the store nor a cached request covers.

    ``stored`` gives the day of each object's newest stored element set: an object already
    held through that day only needs the days from it onwards, which is what makes a
    repeat run an update rather than another backfill. The day itself is asked for again
    because more sets can be published later the same day; the cached-request chain below
    then drops it when a previous request already covered it.

    For each id the cached requests that include it are walked in order of their start
    day: every request that touches the covered run so far (starts on or before the day
    after it) extends the run, and the id needs only the days after the run ends. A gap
    stops the walk, so coverage that begins after the gap does not count. Repeated daily
    runs therefore ask for one new day per id rather than the whole window again, and a
    window that starts before any coverage is fetched whole (conservative).
    """
    stored = stored or {}
    groups: dict[tuple[date, date], list[int]] = {}
    if coverage.empty:
        for i in ids:
            first = max(start, stored.get(int(i), start))
            if first <= end:
                groups.setdefault((first, end), []).append(int(i))
        return groups
    sub = coverage[coverage["norad_id"].isin(ids)]
    intervals = {
        int(i): sorted(zip(g["start"].dt.date, g["end"].dt.date, strict=True)) for i, g in sub.groupby("norad_id")
    }
    one_day = timedelta(days=1)
    for i in ids:
        cursor = max(start, stored.get(int(i), start))
        for s, e in intervals.get(int(i), []):
            if s > cursor:
                break
            if e >= cursor:
                cursor = e + one_day
        if cursor > end:
            continue
        groups.setdefault((cursor, end), []).append(int(i))
    return groups


def unique_history_path(fetched_at: datetime, history_dir: Path = config.HISTORY_DIR) -> Path:
    """:func:`history_path`, with a ``_2``, ``_3`` suffix when a file for that second already exists."""
    path = history_path(fetched_at, history_dir)
    k = 1
    while path.exists():
        k += 1
        path = history_dir / f"{history_path(fetched_at, history_dir).stem}_{k}.parquet"
    return path


def backfill(
    norad_ids: Iterable[int],
    *,
    end: datetime,
    days: int = config.HISTORY_BACKFILL_DAYS,
    cache_dir: Path = config.CACHE_DIR,
    history_dir: Path = config.HISTORY_DIR,
    url_budget: int = config.SPACETRACK_HISTORY_URL_BUDGET,
    predicates: Sequence[str] | None = config.SPACETRACK_HISTORY_PREDICATES,
    client: spacetrack.SpaceTrackClient | None = None,
    now: datetime | None = None,
    offline: bool = False,
    use_stored: bool = True,
) -> BackfillResult:
    """Pull gp_history for ``norad_ids`` over the ``days`` ending on the day of ``end``, in few large requests.

    An object that the store already holds is only asked for from its newest stored
    element set onwards, so the first call for a fleet is a backfill of the whole window
    and every later call is an update of the days since. Ids already covered by cached
    requests are skipped and partly covered ids ask only for the missing days; the rest
    are sorted and batched by URL length. Everything fetched is written to one history
    parquet and added to the index. With ``offline`` only cached requests are used and
    nothing new is asked for.

    ``use_stored=False`` turns off the newest-set shortcut, which is required whenever the
    window is in the **past**: "already held through 2026" is a true statement about an object
    that is also completely uninformative about 2024, and with the shortcut on such an object is
    skipped and the historical window comes back empty. The cached-request check still applies,
    so nothing is re-fetched twice. Phase 3 Step 4's historical snapshots are the caller.
    """
    ids = sorted({int(i) for i in norad_ids})
    start_day, end_day = backfill_window(end, days)
    now = now or datetime.now(UTC)
    coverage = spacetrack.history_coverage(cache_dir)
    stored = stored_through(ids, history_dir) if use_stored else {}
    groups = _needed_ranges(coverage, ids, start_day, end_day, stored)
    n_todo = sum(len(v) for v in groups.values())
    log.info(
        "History %s to %s: %d ids asked for, %d already held or covered, %d to fetch in %d date range(s) "
        "(%d ids already in the store)",
        start_day,
        end_day,
        len(ids),
        len(ids) - n_todo,
        n_todo,
        len(groups),
        len(stored),
    )
    if n_todo == 0:
        return BackfillResult(start_day, end_day, len(ids), len(ids), 0, 0, 0, 0, None)

    out_dir = spacetrack.history_cache_dir(cache_dir)
    n_requests = n_cached = 0
    records: list[dict[str, Any]] = []
    own_client = client is None
    try:
        for (g_start, g_end), g_ids in sorted(groups.items()):
            chunks = spacetrack.chunk_ids_by_url(
                g_ids, g_start, g_end + timedelta(days=1), url_budget=url_budget, predicates=predicates
            )
            for chunk in chunks:
                key = spacetrack.history_request_key(chunk, g_start, g_end + timedelta(days=1))
                if (out_dir / f"{key}.json").exists():
                    n_cached += 1
                else:
                    n_requests += 1
            if n_requests and offline:
                raise FileNotFoundError(f"{n_requests} gp_history request(s) are not cached and offline=True")
            if client is None and n_requests:
                client = spacetrack.SpaceTrackClient(timeout=config.SPACETRACK_HISTORY_TIMEOUT_S)
            records.extend(
                spacetrack.fetch_gp_history(
                    g_ids,
                    g_start,
                    g_end,
                    cache_dir=cache_dir,
                    url_budget=url_budget,
                    predicates=predicates,
                    client=client,
                    now=now,
                    offline=offline,
                )
            )
    finally:
        if own_client and client is not None:
            client.close()

    df = frame_from_records(records, fetched_at=now)
    path = None
    if len(df):
        path = write_history(
            df,
            unique_history_path(now, history_dir),
            metadata={
                "kind": "backfill",
                "start": start_day.isoformat(),
                "end": end_day.isoformat(),
                "n_ids_requested": str(n_todo),
            },
        )
    log.info(
        "Backfill: %d requests (%d served from cache), %d element sets for %d objects",
        n_requests,
        n_cached,
        len(df),
        df["norad_id"].nunique() if len(df) else 0,
    )
    return BackfillResult(start_day, end_day, len(ids), len(ids) - n_todo, n_todo, n_requests, n_cached, len(df), path)
