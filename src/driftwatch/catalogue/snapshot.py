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
) -> pd.DataFrame:
    """Merge per-group OMM records into one classified snapshot frame.

    Objects present in several groups are kept once, with the newest epoch, and the
    ``groups`` column lists every group they appeared in.
    """
    frames = []
    for group, records in records_by_group.items():
        frame = records_to_frame(records)
        frame["group"] = group
        frames.append(frame)
    if not frames:
        raise ValueError("No groups to merge")
    df = pd.concat(frames, ignore_index=True)

    groups = df.groupby("norad_id")["group"].agg(lambda g: sorted(set(g)))
    df = df.sort_values(["norad_id", "epoch"]).drop_duplicates("norad_id", keep="last")
    df = df.drop(columns=["group"]).set_index("norad_id")
    df["groups"] = groups
    df = df.reset_index()

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
    df["source"] = source
    df["fetched_at"] = (
        pd.Timestamp(fetched_at).tz_convert("UTC")
        if pd.Timestamp(fetched_at).tzinfo
        else pd.Timestamp(fetched_at, tz="UTC")
    )
    df = df[[f.name for f in SNAPSHOT_SCHEMA]].sort_values("norad_id").reset_index(drop=True)
    return df


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
        "epoch_age_days": {
            "median": float(age_days.median()),
            "p90": float(age_days.quantile(0.9)),
            "max": float(age_days.max()),
        },
    }
