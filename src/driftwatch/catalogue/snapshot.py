"""Dated catalogue snapshots in parquet.

A snapshot is the merged, de-duplicated content of every fetched CelesTrak group at one
moment, with SATCAT metadata and classification joined on, stored under
``data/snapshots/gp_<UTC stamp>.parquet``. Every fetch keeps its own file: later phases
estimate per-object orbit uncertainty from how consecutive element sets disagree, so the
history is the point, not a by-product.

The column list is documented in ``docs/data-schema.md`` and enforced by
:data:`SNAPSHOT_SCHEMA`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import config
from driftwatch.catalogue.classify import altitude_bands, categorise_frame
from driftwatch.orbit.propagator import build_satrecs, mean_orbit_geometry
from driftwatch.orbit.time import stamp

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

# OMM field -> snapshot column, for the fields taken verbatim from CelesTrak.
OMM_FIELDS: dict[str, str] = {
    "NORAD_CAT_ID": "norad_id",
    "OBJECT_NAME": "name",
    "OBJECT_ID": "object_id",
    "EPOCH": "epoch",
    "MEAN_MOTION": "mean_motion",
    "ECCENTRICITY": "eccentricity",
    "INCLINATION": "inclination_deg",
    "RA_OF_ASC_NODE": "raan_deg",
    "ARG_OF_PERICENTER": "arg_perigee_deg",
    "MEAN_ANOMALY": "mean_anomaly_deg",
    "BSTAR": "bstar",
    "MEAN_MOTION_DOT": "mean_motion_dot",
    "MEAN_MOTION_DDOT": "mean_motion_ddot",
    "EPHEMERIS_TYPE": "ephemeris_type",
    "CLASSIFICATION_TYPE": "classification",
    "ELEMENT_SET_NO": "element_set_no",
    "REV_AT_EPOCH": "rev_at_epoch",
}

SNAPSHOT_SCHEMA = pa.schema(
    [
        pa.field("norad_id", pa.int32()),
        pa.field("name", pa.string()),
        pa.field("object_id", pa.string()),
        pa.field("epoch", pa.timestamp("us", tz="UTC")),
        pa.field("mean_motion", pa.float64()),
        pa.field("eccentricity", pa.float64()),
        pa.field("inclination_deg", pa.float64()),
        pa.field("raan_deg", pa.float64()),
        pa.field("arg_perigee_deg", pa.float64()),
        pa.field("mean_anomaly_deg", pa.float64()),
        pa.field("bstar", pa.float64()),
        pa.field("mean_motion_dot", pa.float64()),
        pa.field("mean_motion_ddot", pa.float64()),
        pa.field("ephemeris_type", pa.int8()),
        pa.field("classification", pa.string()),
        pa.field("element_set_no", pa.int32()),
        pa.field("rev_at_epoch", pa.int32()),
        pa.field("period_min", pa.float64()),
        pa.field("semi_major_axis_km", pa.float64()),
        pa.field("apogee_km", pa.float64()),
        pa.field("perigee_km", pa.float64()),
        pa.field("object_type", pa.string()),
        pa.field("category", pa.string()),
        pa.field("altitude_band", pa.string()),
        pa.field("rcs_m2", pa.float64()),
        pa.field("owner", pa.string()),
        pa.field("launch_date", pa.date32()),
        pa.field("groups", pa.list_(pa.string())),
        pa.field("source", pa.string()),
        pa.field("fetched_at", pa.timestamp("us", tz="UTC")),
    ]
)


def records_to_frame(records: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """Turn raw OMM dictionaries into a typed frame with snapshot column names."""
    if not records:
        return pd.DataFrame({col: pd.Series(dtype="object") for col in OMM_FIELDS.values()})
    df = pd.DataFrame.from_records(list(records))
    missing = [f for f in OMM_FIELDS if f not in df.columns]
    if missing:
        raise ValueError(f"OMM records lack fields: {missing}")
    df = df[list(OMM_FIELDS)].rename(columns=OMM_FIELDS)
    df["norad_id"] = df["norad_id"].astype("int64")
    df["epoch"] = pd.to_datetime(df["epoch"], utc=True, format="ISO8601")
    for col in (
        "mean_motion",
        "eccentricity",
        "inclination_deg",
        "raan_deg",
        "arg_perigee_deg",
        "mean_anomaly_deg",
        "bstar",
        "mean_motion_dot",
        "mean_motion_ddot",
    ):
        df[col] = pd.to_numeric(df[col]).astype("float64")
    df["ephemeris_type"] = pd.to_numeric(df["ephemeris_type"]).fillna(0).astype("int64")
    df["element_set_no"] = pd.to_numeric(df["element_set_no"]).fillna(0).astype("int64")
    df["rev_at_epoch"] = pd.to_numeric(df["rev_at_epoch"]).fillna(0).astype("int64")
    df["name"] = df["name"].astype("string").str.strip()
    df["object_id"] = df["object_id"].astype("string")
    df["classification"] = df["classification"].astype("string")
    return df


def build_snapshot(
    records_by_group: Mapping[str, Sequence[Mapping[str, Any]]],
    satcat: pd.DataFrame | None,
    *,
    fetched_at: datetime,
    source: str = "celestrak",
    extra_sources: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> pd.DataFrame:
    """Merge OMM records from CelesTrak groups and any other sources into one classified snapshot.

    ``records_by_group`` holds the CelesTrak groups (labelled ``source``); ``extra_sources``
    maps another source name, ``"spacetrack"``, to its records. Every object is kept once
    with its newest epoch, and ``source`` records where that element set came from. At
    equal epoch the CelesTrak record wins the tie: CelesTrak redistributes Space-Track's
    data, so equal epochs are the same element set and the tie only decides the label.
    ``groups`` lists the CelesTrak groups an object appeared in and is empty for objects
    that only another source holds.
    """
    frames = []
    for group, records in records_by_group.items():
        frame = records_to_frame(records)
        if frame.empty:
            continue
        frame["group"] = group
        frame["source"] = source
        frame["_tiebreak"] = 1
        frames.append(frame)
    for name, records in (extra_sources or {}).items():
        frame = records_to_frame(records)
        if frame.empty:
            continue
        frame["group"] = None
        frame["source"] = name
        frame["_tiebreak"] = 0
        frames.append(frame)
    if not frames:
        raise ValueError("No records to merge")
    df = pd.concat(frames, ignore_index=True)

    in_group = df["group"].notna()
    groups = df[in_group].groupby("norad_id")["group"].agg(lambda g: sorted(set(g)))
    df = df.sort_values(["norad_id", "epoch", "_tiebreak"]).drop_duplicates("norad_id", keep="last")
    df = df.drop(columns=["group", "_tiebreak"]).set_index("norad_id")
    df["groups"] = [g if isinstance(g, list) else [] for g in groups.reindex(df.index)]
    df = df.reset_index()

    return enrich(df, satcat, fetched_at=fetched_at)


def enrich(df: pd.DataFrame, satcat: pd.DataFrame | None, *, fetched_at: datetime) -> pd.DataFrame:
    """Join SATCAT metadata, derive the orbit geometry and classify, into the snapshot schema.

    Split out of :func:`build_snapshot` so a snapshot can also be built from stored element
    sets rather than from live records -- see :func:`snapshot_as_of`, which is how a
    historical storm window is reconstructed. Everything from here down is a function of one
    element set per object plus static metadata, so both routes share it exactly.
    """
    df = df.copy()
    if satcat is not None:
        meta = satcat[~satcat.index.duplicated(keep="last")].reindex(df["norad_id"].to_numpy())
        df["object_type"] = meta["object_type"].fillna("UNK").astype("string").to_numpy()
        df["rcs_m2"] = meta["rcs_m2"].to_numpy(dtype="float64", na_value=np.nan)
        df["owner"] = meta["owner"].astype("string").to_numpy()
        df["launch_date"] = meta["launch_date"].to_numpy()
    else:
        df["object_type"] = pd.array(["UNK"] * len(df), dtype="string")
        df["rcs_m2"] = np.nan
        df["owner"] = pd.array([pd.NA] * len(df), dtype="string")
        df["launch_date"] = pd.array([None] * len(df), dtype="object")

    geometry = mean_orbit_geometry(build_satrecs(df))
    df["period_min"] = 1440.0 / df["mean_motion"].to_numpy()
    df["semi_major_axis_km"] = geometry["semi_major_axis_km"].to_numpy()
    df["apogee_km"] = geometry["apogee_km"].to_numpy()
    df["perigee_km"] = geometry["perigee_km"].to_numpy()

    df["category"] = categorise_frame(df)
    df["altitude_band"] = pd.array(
        altitude_bands(df["perigee_km"].to_numpy(), df["apogee_km"].to_numpy(), df["eccentricity"].to_numpy()),
        dtype="string",
    )
    df["fetched_at"] = (
        pd.Timestamp(fetched_at).tz_convert("UTC")
        if pd.Timestamp(fetched_at).tzinfo
        else pd.Timestamp(fetched_at, tz="UTC")
    )
    df = df[[f.name for f in SNAPSHOT_SCHEMA]].sort_values("norad_id").reset_index(drop=True)
    return df


def snapshot_as_of(
    sets: pd.DataFrame,
    satcat: pd.DataFrame | None,
    *,
    as_of: datetime,
    groups: Mapping[int, Sequence[str]] | None = None,
    max_age_days: float | None = None,
) -> pd.DataFrame:
    """The catalogue as it stood on ``as_of``: each object's newest element set at or before it.

    ``sets`` is a history frame (``catalogue/history.py``) -- every element set we hold for the
    objects in question -- and this picks one per object exactly the way an operator screening
    on that day would have: the newest fit published by then, and nothing later. Using a set
    from *after* the date is the failure mode this exists to prevent, and it is the one that
    would quietly make a storm validation come out right: an element set issued on 12 May
    already contains the storm's effect, so propagating it would "predict" the drag it was
    fitted to.

    ``max_age_days`` drops objects whose newest set by then is staler than that, which is how
    an object that stopped being tracked long before the date is kept out of the snapshot
    rather than carried in on a fit nobody would have used. ``groups`` supplies the CelesTrak
    group membership, which history does not carry: pass the current snapshot's, understanding
    that group membership is being read from today rather than from then.
    """
    if not len(sets):
        raise ValueError("no element sets to build a snapshot from")
    at = pd.Timestamp(as_of)
    at = at.tz_localize("UTC") if at.tzinfo is None else at.tz_convert("UTC")
    epochs = pd.to_datetime(sets["epoch"], utc=True)
    before = sets[epochs <= at].copy()
    if not len(before):
        raise ValueError(f"no element set in the history is at or before {at.isoformat()}")
    before["epoch"] = pd.to_datetime(before["epoch"], utc=True)
    latest = before.sort_values(["norad_id", "epoch"]).drop_duplicates("norad_id", keep="last")
    if max_age_days is not None:
        age_days = (at - latest["epoch"]).dt.total_seconds() / 86400.0
        latest = latest[age_days <= float(max_age_days)]
    if not len(latest):
        raise ValueError(f"no element set within {max_age_days} days of {at.isoformat()}")
    latest = latest.reset_index(drop=True)
    latest["norad_id"] = latest["norad_id"].astype("int64")
    lookup = {int(k): list(v) for k, v in (groups or {}).items()}
    latest["groups"] = [lookup.get(int(i), []) for i in latest["norad_id"]]
    if "source" not in latest.columns:
        latest["source"] = "gp_history"
    return enrich(latest, satcat, fetched_at=at)


def as_of_path(as_of: datetime, snapshot_dir: Path = config.AS_OF_SNAPSHOT_DIR) -> Path:
    """Where a historical snapshot lives. Named by the date it reconstructs, not by when it was built.

    Cached permanently: the input is ``gp_history``, which does not change, so the file is a
    pure function of the date and the object list and rebuilding it is waste.

    In :data:`driftwatch.config.AS_OF_SNAPSHOT_DIR`, deliberately not beside the live snapshots.
    :func:`list_snapshots` globs one directory for ``gp_*.parquet`` and takes the last by name,
    and ``gp_asof_2022...`` sorts after ``gp_20260901...`` because a letter beats a digit -- so
    a reconstruction of an old day would silently become "the latest snapshot" for the screener,
    the coefficient fit and the history loader alike. It is also a different kind of file: a
    live snapshot is what the catalogue said at a fetch, this is what it said on a chosen date,
    rebuilt afterwards from history.
    """
    return Path(snapshot_dir) / f"gp_asof_{stamp(as_of)}.parquet"


def to_arrow(df: pd.DataFrame, extra_metadata: Mapping[str, str] | None = None) -> pa.Table:
    """Convert a snapshot frame to an Arrow table with the canonical schema and metadata."""
    table = pa.Table.from_pandas(df, schema=SNAPSHOT_SCHEMA, preserve_index=False)
    metadata = {b"driftwatch_schema_version": str(SCHEMA_VERSION).encode()}
    for key, value in (extra_metadata or {}).items():
        metadata[key.encode()] = value.encode()
    return table.replace_schema_metadata({**(table.schema.metadata or {}), **metadata})


def snapshot_path(fetched_at: datetime, snapshot_dir: Path = config.SNAPSHOT_DIR) -> Path:
    """File name for a snapshot fetched at ``fetched_at``."""
    return snapshot_dir / f"gp_{stamp(fetched_at)}.parquet"


def write_snapshot(df: pd.DataFrame, path: Path, *, groups: Sequence[str] = ()) -> Path:
    """Write a snapshot frame to parquet with schema metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = to_arrow(df, {"groups": json.dumps(list(groups))})
    pq.write_table(table, path, compression="zstd")
    log.info("Wrote %d objects to %s", len(df), path)
    return path


def read_snapshot(path: Path) -> pd.DataFrame:
    """Read a snapshot parquet file back into a frame."""
    table = pq.read_table(path)
    version = (table.schema.metadata or {}).get(b"driftwatch_schema_version", b"?").decode()
    if version != str(SCHEMA_VERSION):
        log.warning("Snapshot %s has schema version %s, expected %s", path.name, version, SCHEMA_VERSION)
    return table.to_pandas(date_as_object=True)


def list_snapshots(snapshot_dir: Path = config.SNAPSHOT_DIR) -> list[Path]:
    """All snapshot files, oldest first."""
    if not snapshot_dir.exists():
        return []
    return sorted(snapshot_dir.glob("gp_*.parquet"))


def latest_snapshot(snapshot_dir: Path = config.SNAPSHOT_DIR) -> Path:
    """The newest snapshot file, or raise ``FileNotFoundError``."""
    paths = list_snapshots(snapshot_dir)
    if not paths:
        raise FileNotFoundError(f"No snapshots in {snapshot_dir}; run `driftwatch fetch` first")
    return paths[-1]


def snapshot_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Counts by category and altitude band plus the epoch age spread, for logs and docs."""
    now = pd.Timestamp(datetime.now(UTC))
    age_days = (now - pd.to_datetime(df["epoch"], utc=True)).dt.total_seconds() / 86400.0
    return {
        "n_objects": int(len(df)),
        "by_category": {k: int(v) for k, v in df["category"].value_counts().sort_index().items()},
        "by_band": {k: int(v) for k, v in df["altitude_band"].value_counts().sort_index().items()},
        "by_source": {k: int(v) for k, v in df["source"].value_counts().sort_index().items()},
        "epoch_age_days": {
            "median": float(age_days.median()),
            "p90": float(age_days.quantile(0.9)),
            "max": float(age_days.max()),
        },
    }
