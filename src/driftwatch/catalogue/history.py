"""Element-set history: every element set we have seen for an object, from any source.

Two things in later steps need more than the latest element set per object:

* Step 3 estimates orbit uncertainty by propagating an older element set to a newer
  one's epoch and measuring the disagreement. That needs several element sets per
  object spread over days.
* Phase 3 replays past storms, which needs element sets from around those dates.

The snapshots already hold one element set per object per fetch. This module adds
``data/history/gph_<stamp>.parquet`` files written from Space-Track ``gp_history``
pulls, with the element columns of the snapshot schema plus ``source`` and
``fetched_at``, and :func:`load_history`, which concatenates history files and snapshots
and keeps one row per (NORAD id, epoch).

Physics note: an element set is a fit to tracking data over a few days, tagged with an
epoch. Two element sets for the same object with different epochs are two different
fits, and the difference between them after propagating one to the other's epoch is how
much the fits disagree, not how far either is from the truth. Step 3 documents why that
is a floor on the error rather than a measurement of it.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import config
from driftwatch.catalogue.snapshot import (
    OMM_FIELDS,
    SCHEMA_VERSION,
    SNAPSHOT_SCHEMA,
    list_snapshots,
    read_snapshot,
    records_to_frame,
)
from driftwatch.orbit.time import stamp

log = logging.getLogger(__name__)

HISTORY_COLUMNS: tuple[str, ...] = (*OMM_FIELDS.values(), "source", "fetched_at")
HISTORY_SCHEMA = pa.schema([SNAPSHOT_SCHEMA.field(name) for name in HISTORY_COLUMNS])


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


def write_history(df: pd.DataFrame, path: Path, *, metadata: Mapping[str, str] | None = None) -> Path:
    """Write a history frame to parquet with the schema version and any extra metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(_normalise(df), schema=HISTORY_SCHEMA, preserve_index=False)
    meta = {b"driftwatch_schema_version": str(SCHEMA_VERSION).encode()}
    for key, value in (metadata or {}).items():
        meta[key.encode()] = value.encode()
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **meta})
    pq.write_table(table, path, compression="zstd")
    log.info("Wrote %d element sets for %d objects to %s", len(df), df["norad_id"].nunique(), path)
    return path


def read_history(path: Path) -> pd.DataFrame:
    """Read one history file."""
    return _normalise(pq.read_table(path).to_pandas())


def list_history(history_dir: Path = config.HISTORY_DIR) -> list[Path]:
    """All history files, oldest first."""
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob("gph_*.parquet"))


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
    ``start`` and ``end`` filter on epoch (inclusive, UTC).
    """
    frames = [read_history(p) for p in list_history(history_dir)]
    if include_snapshots:
        frames.extend(_normalise(read_snapshot(p)) for p in list_snapshots(snapshot_dir))
    if not frames:
        return _empty_frame()
    df = pd.concat(frames, ignore_index=True)
    if norad_ids is not None:
        df = df[df["norad_id"].isin([int(i) for i in norad_ids])]
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
