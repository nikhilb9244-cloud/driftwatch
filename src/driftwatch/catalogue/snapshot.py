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
import pyarrow.compute as pc
import pyarrow.parquet as pq

from driftwatch import availability, config
from driftwatch.catalogue.classify import altitude_bands, categorise_frame
from driftwatch.orbit.propagator import build_satrecs, mean_orbit_geometry
from driftwatch.orbit.time import stamp

log = logging.getLogger(__name__)

SCHEMA_VERSION = 3

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
        pa.field("state_epoch", pa.timestamp("us", tz="UTC")),
        pa.field("provider_created_at", pa.timestamp("us", tz="UTC")),
        pa.field("published_at", pa.timestamp("us", tz="UTC")),
        pa.field("retrieved_at", pa.timestamp("us", tz="UTC")),
        pa.field("reconstructed_at", pa.timestamp("us", tz="UTC")),
        pa.field("epoch_selection_as_of", pa.timestamp("us", tz="UTC")),
        pa.field("selection_kind", pa.string()),
        pa.field("availability_as_of", pa.timestamp("us", tz="UTC")),
        pa.field("membership_provenance", pa.string()),
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
    created = pd.to_datetime(df.get("CREATION_DATE", pd.Series(pd.NaT, index=df.index)), utc=True, format="ISO8601")
    provenance = {
        key: df.get("_driftwatch_" + key, pd.Series(pd.NaT, index=df.index)) for key in ("published_at", "retrieved_at")
    }
    df = df[list(OMM_FIELDS)].rename(columns=OMM_FIELDS)
    df["provider_created_at"] = created
    for key, values in provenance.items():
        df[key] = pd.to_datetime(values, utc=True, format="mixed")
    df["norad_id"] = df["norad_id"].astype("int64")
    df["epoch"] = pd.to_datetime(df["epoch"], utc=True, format="ISO8601")
    df["state_epoch"] = df["epoch"]
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
    fetched_at: datetime | None = None,
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
    that only another source holds. Per-record retrieval annotations survive merging;
    ``fetched_at`` is an optional actual acquisition time for a single shared fetch,
    never the time a cached file was imported or this snapshot was built.
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

    df["fetched_at"] = df["retrieved_at"]
    return enrich(df, satcat, fetched_at=fetched_at)


def enrich(df: pd.DataFrame, satcat: pd.DataFrame | None, *, fetched_at: datetime | None = None) -> pd.DataFrame:
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
    if fetched_at is not None:
        df["fetched_at"] = pd.to_datetime(fetched_at, utc=True)
        df["retrieved_at"] = df["fetched_at"]
    df = temporal_fields(df)
    df = df[[f.name for f in SNAPSHOT_SCHEMA]].sort_values("norad_id").reset_index(drop=True)
    return df


def temporal_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Keep state, creation, publication and acquisition distinct; absent dates stay unknown."""
    df = df.copy()
    df["state_epoch"] = pd.to_datetime(df["epoch"], utc=True)
    for name in (
        "fetched_at",
        "provider_created_at",
        "published_at",
        "retrieved_at",
        "reconstructed_at",
        "epoch_selection_as_of",
        "availability_as_of",
    ):
        if name not in df:
            df[name] = df.get("fetched_at", pd.NaT) if name == "retrieved_at" else pd.NaT
        df[name] = pd.to_datetime(df[name], utc=True)
    df["retrieved_at"] = df["retrieved_at"].fillna(df["fetched_at"])
    if "selection_kind" not in df:
        df["selection_kind"] = "retrieval snapshot"
    if "membership_provenance" not in df:
        df["membership_provenance"] = None
    return df


def snapshot_as_of(
    sets: pd.DataFrame,
    satcat: pd.DataFrame | None,
    *,
    as_of: datetime,
    groups: Mapping[int, Sequence[str]] | None = None,
    max_age_days: float | None = None,
    reconstructed_at: datetime | None = None,
    selection_kind: str = availability.EPOCH_RECONSTRUCTION,
    membership: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Epoch-based reconstruction: newest stored state epoch no later than ``as_of``.

    This does not establish which products were published or available at that
    historical time. A late-published fit with an early epoch may be selected.
    Provider creation is not publication. Actual input retrieval times survive;
    missing times remain unknown. Supplied SATCAT and group membership can be
    retrospective and do not establish historical membership. ``max_age_days``
    limits state-epoch age only. ``causal replay`` additionally requires publication
    or actual retrieval evidence before the cutoff and a supplied membership history.
    """
    if not len(sets):
        raise ValueError("no element sets to build a snapshot from")
    at = pd.Timestamp(as_of)
    at = at.tz_localize("UTC") if at.tzinfo is None else at.tz_convert("UTC")
    epochs = pd.to_datetime(sets["epoch"], utc=True)
    before = availability.select(sets.assign(epoch=epochs), as_of=at, selection_kind=selection_kind)
    membership_rows = None
    if selection_kind == availability.CAUSAL_REPLAY and membership is None:
        raise ValueError("Causal catalogue replay requires an explicit membership history")
    if membership is not None:
        membership_rows = availability.membership_at(membership, as_of=at, selection_kind=selection_kind)
        before = before[before.norad_id.isin(membership_rows.norad_id)]
    if not len(before):
        raise ValueError(f"no element set in the history is at or before {at.isoformat()}")
    before["epoch"] = pd.to_datetime(before["epoch"], utc=True)
    latest = before.sort_values(
        ["norad_id", "epoch", "provider_created_at", "retrieved_at"], na_position="first", kind="stable"
    ).drop_duplicates("norad_id", keep="last")
    if max_age_days is not None:
        age_days = (at - latest["epoch"]).dt.total_seconds() / 86400.0
        latest = latest[age_days <= float(max_age_days)]
    if not len(latest):
        raise ValueError(f"no element set within {max_age_days} days of {at.isoformat()}")
    latest = latest.reset_index(drop=True)
    latest["norad_id"] = latest["norad_id"].astype("int64")
    lookup = (
        {int(k): list(v) for k, v in (groups or {}).items()}
        if selection_kind == availability.EPOCH_RECONSTRUCTION
        else {}
    )
    latest["groups"] = [lookup.get(int(i), []) for i in latest["norad_id"]]
    if "source" not in latest.columns:
        latest["source"] = "gp_history"
    latest["selection_kind"] = selection_kind
    latest["epoch_selection_as_of"] = at
    latest["availability_as_of"] = at if selection_kind == availability.CAUSAL_REPLAY else pd.NaT
    provenance = (
        {}
        if membership_rows is None
        else {
            int(row["norad_id"]): json.dumps(row)
            for row in availability.metadata(membership_rows, epoch_column="effective_at")
        }
    )
    latest["membership_provenance"] = [provenance.get(int(n)) for n in latest.norad_id]
    latest["reconstructed_at"] = pd.to_datetime(reconstructed_at or datetime.now(UTC), utc=True)
    # Current SATCAT attributes cannot be attached as historical causal facts.
    return enrich(latest, satcat if selection_kind == availability.EPOCH_RECONSTRUCTION else None)


def as_of_path(as_of: datetime, snapshot_dir: Path = config.AS_OF_SNAPSHOT_DIR) -> Path:
    """Where a historical snapshot lives. Named by the date it reconstructs, not by when it was built.

    Stored for reuse. Later retrievals can include revisions or late publications,
    so an epoch-selected reconstruction can change when rebuilt.

    In :data:`driftwatch.config.AS_OF_SNAPSHOT_DIR`, deliberately not beside the live snapshots.
    :func:`list_snapshots` globs one directory for ``gp_*.parquet`` and takes the last by name,
    and ``gp_asof_2022...`` sorts after ``gp_20260901...`` because a letter beats a digit -- so
    a reconstruction of an old day would silently become "the latest snapshot" for the screener,
    the coefficient fit and the history loader alike. It is also a different kind of file: a
    live snapshot records a retrieval; this is an epoch-based reconstruction from
    later-held history, not proof of what was available on the chosen date.
    """
    return Path(snapshot_dir) / f"gp_asof_{stamp(as_of)}.parquet"


def to_arrow(df: pd.DataFrame, extra_metadata: Mapping[str, str] | None = None) -> pa.Table:
    """Convert a snapshot frame to an Arrow table with the canonical schema and metadata."""
    table = pa.Table.from_pandas(temporal_fields(df), schema=SNAPSHOT_SCHEMA, preserve_index=False)
    metadata = {b"driftwatch_schema_version": str(SCHEMA_VERSION).encode()}
    for key, value in (extra_metadata or {}).items():
        metadata[key.encode()] = value.encode()
    return table.replace_schema_metadata({**(table.schema.metadata or {}), **metadata})


def snapshot_path(fetched_at: datetime, snapshot_dir: Path = config.SNAPSHOT_DIR) -> Path:
    """Name a local build; the legacy argument name does not set the rows' retrieval time."""
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
    frame = table.to_pandas(date_as_object=True)
    metadata = table.schema.metadata or {}
    if version == "1" and (path.name.startswith("gp_asof_") or b"driftwatch_as_of" in metadata):
        # Legacy reconstructions wrote the target epoch into fetched_at. That
        # field cannot be recovered as an acquisition time from these bytes.
        cutoff = metadata.get(b"driftwatch_as_of")
        frame["epoch_selection_as_of"] = (
            pd.to_datetime(cutoff.decode(), utc=True) if cutoff else pd.to_datetime(frame["fetched_at"], utc=True)
        )
        built = metadata.get(b"driftwatch_built_at")
        frame["reconstructed_at"] = pd.to_datetime(built.decode(), utc=True) if built else pd.NaT
        frame["fetched_at"] = pd.NaT
        frame["retrieved_at"] = pd.NaT
        frame["selection_kind"] = "epoch-based reconstruction"
    return temporal_fields(frame)


def snapshot_problem(path: Path) -> str | None:
    """Why ``path`` is not a usable catalogue snapshot, or ``None`` if it is one.

    A run records its snapshot by file name and everything downstream trusts that name: the
    element sets a rescore propagates, the provenance on every exported row, and -- from Phase 4
    Step 2 -- the snapshot age the pipeline refuses to publish past. Nothing checked that the
    name was a snapshot at all, and in September 2026 a shadowed variable in ``cmd_screen``
    made two runs record a *supplemental element-set file* instead. Every test passed. The two
    file types share nineteen of their columns and both are parquet, so the check is on what
    only a snapshot has: the schema-version metadata that :func:`write_snapshot` stamps, the
    absence of the supplemental marker, and the columns a snapshot alone carries.
    """
    path = Path(path)
    if not path.exists():
        return f"{path} does not exist"
    if path.suffix != ".parquet":
        return f"{path.name} is not a parquet file"
    try:
        schema = pq.read_schema(path)
    except Exception as exc:  # noqa: BLE001 -- any unreadable file is the same answer here
        return f"{path.name} cannot be read as parquet ({exc})"
    metadata = {k.decode(): v.decode() for k, v in (schema.metadata or {}).items() if not k.startswith(b"pandas")}
    if "driftwatch_supplemental" in metadata:
        return (
            f"{path.name} is a supplemental element-set file "
            f"({metadata['driftwatch_supplemental']!r}), not a catalogue snapshot"
        )
    version = metadata.get("driftwatch_schema_version")
    if version is None:
        return f"{path.name} carries no driftwatch_schema_version, so it was not written as a snapshot"
    if version not in {"1", "2", str(SCHEMA_VERSION)}:
        return f"{path.name} has snapshot schema version {version}, expected {SCHEMA_VERSION}"
    required = SNAPSHOT_SCHEMA.names
    if version == "1":
        required = required[: required.index("state_epoch")]
    elif version == "2":
        required = required[: required.index("availability_as_of")]
    missing = [name for name in required if name not in schema.names]
    if missing:
        return f"{path.name} is missing snapshot columns: {', '.join(missing)}"
    return None


def snapshot_fetched_at(path: Path) -> datetime | None:
    """When the catalogue snapshot at ``path`` was fetched: the newest ``fetched_at`` in it.

    Read from the data rather than parsed out of the file name, so that a renamed or copied
    file cannot make a stale snapshot look fresh. The pipeline's staleness check runs on this.
    """
    table = pq.read_table(path, columns=["fetched_at"])
    metadata = table.schema.metadata or {}
    if metadata.get(b"driftwatch_schema_version") == b"1" and (
        path.name.startswith("gp_asof_") or b"driftwatch_as_of" in metadata
    ):
        return None  # The legacy field was a reconstruction cutoff, not a retrieval.
    value = pc.max(table["fetched_at"]).as_py()
    return pd.Timestamp(value).tz_convert("UTC").to_pydatetime() if value is not None else None


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
        "selection_kind": sorted(df.selection_kind.dropna().unique()) if "selection_kind" in df else ["unknown"],
        "by_category": {k: int(v) for k, v in df["category"].value_counts().sort_index().items()},
        "by_band": {k: int(v) for k, v in df["altitude_band"].value_counts().sort_index().items()},
        "by_source": {k: int(v) for k, v in df["source"].value_counts().sort_index().items()},
        "epoch_age_days": {
            "median": float(age_days.median()),
            "p90": float(age_days.quantile(0.9)),
            "max": float(age_days.max()),
        },
    }
