"""CelesTrak supplemental element sets: operator ephemerides fitted to SGP4.

Starlink satellites manoeuvre constantly: orbit raising after launch, station keeping,
collision avoidance and deorbit burns. A standard element set is a fit to tracking data
from the past, so it knows nothing about a burn planned for tomorrow, and a screening
against it is a screening against where the satellite would go if it stopped manoeuvring.
SpaceX publishes its own ephemerides, which include planned manoeuvres, and CelesTrak fits
SGP4 element sets to them (its "supplemental" GP data) so that ordinary SGP4 tooling can
use them.

The fit is not perfect and the ephemeris is a prediction. CelesTrak publishes the RMS of
each fit in the ``RMS`` field of every record: a median of 0.20 km, a 90th percentile of
0.27 km and a worst case of 10.8 km when read on 2026-09-02. Step 3 uses that as the floor
under a supplemental object's covariance. So a supplemental set is better than the GP set
for a Starlink secondary, and is still not the truth; the output records which set was
used (``secondary_ephemeris`` in the events).

This module fetches the file with the same cache and two-hour floor as the GP groups,
matches its records to a snapshot by NORAD id, and returns a copy of the snapshot with
the matched objects' elements replaced and an ``ephemeris`` column that says which set
each object carries. Records for satellites not yet in the public catalogue carry
placeholder ids above 100000 and match nothing; they are counted and skipped.

Every fetch is also written to ``data/supplemental/<name>_<stamp>.parquet``, one file per
version, keeping the published RMS of each fit. Two things need that. A run is only
reproducible if the supplemental sets it used are still on disk: CelesTrak's cache holds
one version and overwrites it, and the sets change several times a day, so two runs
against the same catalogue snapshot but different supplemental versions give different
events (see ``docs/phase2-plan.md``). And the covariance of an object screened on a
supplemental set has to come from the consistency of successive supplemental sets, not
from its GP history, which measures its manoeuvring rather than its tracking.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import config
from driftwatch.catalogue.celestrak import GroupFetch, fetch_cached
from driftwatch.catalogue.snapshot import OMM_FIELDS, SNAPSHOT_SCHEMA, records_to_frame
from driftwatch.orbit.propagator import build_satrecs, mean_orbit_geometry
from driftwatch.orbit.time import parse_utc, stamp

log = logging.getLogger(__name__)

# The element-set columns a supplemental record replaces. Everything else in the snapshot
# (name, SATCAT metadata, category, groups, source) stays.
ELEMENT_COLUMNS: tuple[str, ...] = (
    "epoch",
    "mean_motion",
    "eccentricity",
    "inclination_deg",
    "raan_deg",
    "arg_perigee_deg",
    "mean_anomaly_deg",
    "bstar",
    "mean_motion_dot",
    "mean_motion_ddot",
    "element_set_no",
    "rev_at_epoch",
)
# CelesTrak gives satellites that are not yet in the public catalogue placeholder ids.
PLACEHOLDER_ID_FLOOR = 100_000

# The element-set columns of the snapshot schema that a stored supplemental version keeps,
# plus CelesTrak's published RMS of the fit to the operator ephemeris (km) and the fetch time.
SUPPLEMENTAL_ELEMENT_COLUMNS: tuple[str, ...] = tuple(OMM_FIELDS.values())
SUPPLEMENTAL_COLUMNS: tuple[str, ...] = (*SUPPLEMENTAL_ELEMENT_COLUMNS, "rms_km", "fetched_at")
SUPPLEMENTAL_SCHEMA = pa.schema(
    [
        *(SNAPSHOT_SCHEMA.field(name) for name in SUPPLEMENTAL_ELEMENT_COLUMNS),
        pa.field("rms_km", pa.float64()),
        pa.field("fetched_at", pa.timestamp("us", tz="UTC")),
    ]
)

# Fields the supplemental JSON may omit, with the value used when it does.
_OPTIONAL_FIELDS: dict[str, Any] = {
    "OBJECT_ID": "",
    "EPHEMERIS_TYPE": 0,
    "CLASSIFICATION_TYPE": "U",
    "ELEMENT_SET_NO": 0,
    "REV_AT_EPOCH": 0,
    "MEAN_MOTION_DOT": 0.0,
    "MEAN_MOTION_DDOT": 0.0,
}


def supplemental_cache_path(name: str, cache_dir: Path = config.CACHE_DIR) -> Path:
    """Cached JSON for one supplemental file, e.g. ``.../celestrak/supplemental/starlink.json``."""
    return cache_dir / "celestrak" / "supplemental" / f"{name}.json"


def fetch_supplemental(
    name: str = "starlink",
    *,
    cache_dir: Path = config.CACHE_DIR,
    min_interval: timedelta = config.MIN_GROUP_FETCH_INTERVAL,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> GroupFetch:
    """Fetch (or reuse cached) supplemental element sets for ``name`` under the CelesTrak rules."""
    return fetch_cached(
        f"supplemental/{name}",
        url=config.CELESTRAK_SUPPLEMENTAL_URL,
        params={"FILE": name, "FORMAT": "json"},
        json_path=supplemental_cache_path(name, cache_dir),
        min_interval=min_interval,
        client=client,
        now=now,
        offline=offline,
    )


def load_supplemental_records(name: str = "starlink", cache_dir: Path = config.CACHE_DIR) -> list[dict[str, Any]]:
    """Read the cached supplemental OMM records from disk."""
    with supplemental_cache_path(name, cache_dir).open(encoding="utf-8") as fh:
        return json.load(fh)


def supplemental_frame(records: Sequence[dict[str, Any]]) -> pd.DataFrame:
    """Supplemental OMM records as a typed frame with snapshot column names, newest epoch per id."""
    filled = [{**_OPTIONAL_FIELDS, **rec} for rec in records]
    if filled:
        missing = [f for f in OMM_FIELDS if f not in filled[0]]
        if missing:
            raise ValueError(f"supplemental records lack fields: {missing}")
    df = records_to_frame(filled)
    if df.empty:
        return df
    return df.sort_values(["norad_id", "epoch"]).drop_duplicates("norad_id", keep="last").reset_index(drop=True)


def supplemental_path(name: str, fetched_at: datetime, out_dir: Path = config.SUPPLEMENTAL_DIR) -> Path:
    """``data/supplemental/<name>_<YYYYMMDDTHHMMSSZ>.parquet``: one file per fetched version."""
    return Path(out_dir) / f"{name}_{stamp(fetched_at)}.parquet"


def version_of(path: Path) -> str:
    """The version stamp in a stored supplemental file name, e.g. ``20260902T064855Z``."""
    return path.stem.split("_")[-1]


def records_with_rms(records: Sequence[dict[str, Any]], *, fetched_at: datetime) -> pd.DataFrame:
    """Supplemental records as a stored version: element columns, the published RMS, the fetch time."""
    df = supplemental_frame(records)
    if df.empty:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in SUPPLEMENTAL_COLUMNS})
    rms = {int(r["NORAD_CAT_ID"]): r.get("RMS") for r in records}
    df = df[list(SUPPLEMENTAL_ELEMENT_COLUMNS)].copy()
    df["rms_km"] = [float(rms[i]) if rms.get(i) not in (None, "") else np.nan for i in df["norad_id"]]
    df["fetched_at"] = pd.Timestamp(parse_utc(fetched_at))
    return df


def write_supplemental(df: pd.DataFrame, path: Path, *, metadata: dict[str, str] | None = None) -> Path:
    """Write one supplemental version to parquet, sorted by object."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df.sort_values("norad_id").reset_index(drop=True)
    table = pa.Table.from_pandas(df[list(SUPPLEMENTAL_COLUMNS)], schema=SUPPLEMENTAL_SCHEMA, preserve_index=False)
    meta = {k.encode(): v.encode() for k, v in (metadata or {}).items()}
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **meta})
    pq.write_table(table, path, compression="zstd")
    log.info("Stored %d supplemental sets as %s", len(df), path.name)
    return path


def store_supplemental(
    records: Sequence[dict[str, Any]],
    *,
    name: str = "starlink",
    fetched_at: datetime,
    out_dir: Path = config.SUPPLEMENTAL_DIR,
) -> tuple[Path, bool]:
    """Store one fetched version if it is not already on disk; returns the path and whether it was written."""
    path = supplemental_path(name, fetched_at, out_dir)
    if path.exists():
        return path, False
    df = records_with_rms(records, fetched_at=fetched_at)
    if df.empty:
        return path, False
    write_supplemental(df, path, metadata={"driftwatch_supplemental": name})
    return path, True


def list_supplemental(name: str = "starlink", out_dir: Path = config.SUPPLEMENTAL_DIR) -> list[Path]:
    """Stored versions of one supplemental file, oldest first."""
    out_dir = Path(out_dir)
    if not out_dir.exists():
        return []
    return sorted(out_dir.glob(f"{name}_*.parquet"))


def read_supplemental(path: Path) -> pd.DataFrame:
    """Read one stored supplemental version."""
    df = pq.read_table(path).to_pandas()
    df["epoch"] = pd.to_datetime(df["epoch"], utc=True)
    return df


def load_supplemental_history(
    name: str = "starlink",
    *,
    norad_ids: Sequence[int] | None = None,
    out_dir: Path = config.SUPPLEMENTAL_DIR,
) -> pd.DataFrame:
    """Every stored supplemental set for ``norad_ids``, one row per (NORAD id, epoch), oldest first.

    Successive versions repeat a set whose epoch has not changed; those collapse to one row,
    so an object only has several rows once CelesTrak has actually refitted it.
    """
    frames = []
    ids = {int(i) for i in norad_ids} if norad_ids is not None else None
    for path in list_supplemental(name, out_dir):
        df = read_supplemental(path)
        frames.append(df[df["norad_id"].isin(ids)] if ids is not None else df)
    if not frames:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in SUPPLEMENTAL_COLUMNS})
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(["norad_id", "epoch", "fetched_at"]).drop_duplicates(["norad_id", "epoch"], keep="last")
    return out.reset_index(drop=True)


def supplemental_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Counts for the log: versions, objects, sets per object, the published RMS."""
    if df.empty:
        return {"n_records": 0, "n_objects": 0}
    per_object = df.groupby("norad_id")["epoch"].size()
    rms = df["rms_km"].dropna()
    return {
        "n_records": int(len(df)),
        "n_objects": int(df["norad_id"].nunique()),
        "sets_per_object": {
            "min": int(per_object.min()),
            "median": float(per_object.median()),
            "max": int(per_object.max()),
        },
        "rms_km": {
            "median": round(float(rms.median()), 4) if len(rms) else None,
            "p90": round(float(rms.quantile(0.9)), 4) if len(rms) else None,
            "max": round(float(rms.max()), 4) if len(rms) else None,
        },
    }


@dataclass(frozen=True)
class SupplementalMatch:
    """What happened when a supplemental file was applied to a snapshot."""

    name: str
    n_records: int
    n_placeholder: int  # ids >= 100000: not yet catalogued, cannot match
    n_unmatched: int  # real ids the snapshot does not hold
    n_too_old: int  # older than the GP set by more than the allowed lag
    n_applied: int
    epoch_lag_days_median: float  # supplemental epoch minus GP epoch, over the applied rows
    version: str = ""  # the stored version's stamp, when the records came from one
    applied_ids: tuple[int, ...] = ()  # the objects whose elements were replaced


def apply_supplemental(
    snapshot: pd.DataFrame,
    records: Sequence[dict[str, Any]],
    *,
    name: str = "starlink",
    max_lag_days: float = config.SUPPLEMENTAL_MAX_LAG_DAYS,
    version: str = "",
) -> tuple[pd.DataFrame, SupplementalMatch]:
    """Substitute supplemental elements from raw records; see :func:`apply_supplemental_frame`."""
    return apply_supplemental_frame(
        snapshot, supplemental_frame(records), name=name, max_lag_days=max_lag_days, version=version
    )


def apply_supplemental_frame(
    snapshot: pd.DataFrame,
    sup: pd.DataFrame,
    *,
    name: str = "starlink",
    max_lag_days: float = config.SUPPLEMENTAL_MAX_LAG_DAYS,
    version: str = "",
) -> tuple[pd.DataFrame, SupplementalMatch]:
    """Return a copy of ``snapshot`` with supplemental elements substituted where they match.

    The copy gains an ``ephemeris`` column: ``"gp"`` for untouched rows and
    ``"supplemental"`` for rows whose element set came from ``records``. A supplemental
    set older than the GP set by more than ``max_lag_days`` is ignored (CelesTrak has
    stopped updating it, so the GP set is the better guess). Mean-element apogee,
    perigee, semi-major axis and period are recomputed for the substituted rows so that
    Stage A sees the manoeuvred orbit.
    """
    out = snapshot.copy()
    if "ephemeris" not in out.columns:
        out["ephemeris"] = "gp"
    sup = sup.sort_values(["norad_id", "epoch"]).drop_duplicates("norad_id", keep="last").reset_index(drop=True)
    n_records = int(len(sup))
    if n_records == 0:
        match = SupplementalMatch(name, 0, 0, 0, 0, 0, float("nan"), version)
        log.info("Supplemental %s: no records", name)
        return out, match

    placeholder = (sup["norad_id"] >= PLACEHOLDER_ID_FLOOR).to_numpy()
    n_placeholder = int(placeholder.sum())
    sup = sup[~placeholder]

    position = pd.Series(np.arange(len(out)), index=out["norad_id"].to_numpy())
    position = position[~position.index.duplicated()]
    present = sup["norad_id"].isin(position.index).to_numpy()
    n_unmatched = int((~present).sum())
    sup = sup[present]

    if sup.empty:
        match = SupplementalMatch(name, n_records, n_placeholder, n_unmatched, 0, 0, float("nan"), version)
        log.info(
            "Supplemental %s: nothing applied (%d placeholder ids, %d not in snapshot)",
            name,
            n_placeholder,
            n_unmatched,
        )
        return out, match

    rows = position.loc[sup["norad_id"].to_numpy()].to_numpy()
    gp_epoch = pd.to_datetime(out["epoch"].iloc[rows], utc=True).to_numpy()
    sup_epoch = pd.to_datetime(sup["epoch"], utc=True).to_numpy()
    lag_days = (sup_epoch - gp_epoch) / np.timedelta64(1, "D")
    fresh = lag_days >= -max_lag_days
    n_too_old = int((~fresh).sum())
    rows = rows[fresh]
    sup = sup[fresh]

    if len(rows):
        index = out.index[rows]
        for col in ELEMENT_COLUMNS:
            # Keep the snapshot's dtypes (int32 bookkeeping columns, microsecond epochs):
            # pandas refuses to write a wider dtype into a narrower column.
            out.loc[index, col] = sup[col].astype(out[col].dtype).to_numpy()
        out.loc[index, "ephemeris"] = "supplemental"
        geometry = mean_orbit_geometry(build_satrecs(out.loc[index]))
        out.loc[index, "semi_major_axis_km"] = geometry["semi_major_axis_km"].to_numpy()
        out.loc[index, "apogee_km"] = geometry["apogee_km"].to_numpy()
        out.loc[index, "perigee_km"] = geometry["perigee_km"].to_numpy()
        out.loc[index, "period_min"] = 1440.0 / out.loc[index, "mean_motion"].to_numpy()
    match = SupplementalMatch(
        name,
        n_records,
        n_placeholder,
        n_unmatched,
        n_too_old,
        int(len(rows)),
        float(np.median(lag_days[fresh])) if len(rows) else float("nan"),
        version,
        tuple(int(i) for i in out.loc[out.index[rows], "norad_id"]) if len(rows) else (),
    )
    log.info(
        "Supplemental %s: %d records, %d applied, %d placeholder ids, %d not in snapshot, %d too old; "
        "median epoch lag %+.2f days",
        name,
        n_records,
        match.n_applied,
        n_placeholder,
        n_unmatched,
        n_too_old,
        match.epoch_lag_days_median,
    )
    return out, match
