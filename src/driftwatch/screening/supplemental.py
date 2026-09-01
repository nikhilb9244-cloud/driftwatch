"""CelesTrak supplemental element sets: operator ephemerides fitted to SGP4.

Starlink satellites manoeuvre constantly: orbit raising after launch, station keeping,
collision avoidance and deorbit burns. A standard element set is a fit to tracking data
from the past, so it knows nothing about a burn planned for tomorrow, and a screening
against it is a screening against where the satellite would go if it stopped manoeuvring.
SpaceX publishes its own ephemerides, which include planned manoeuvres, and CelesTrak fits
SGP4 element sets to them (its "supplemental" GP data) so that ordinary SGP4 tooling can
use them.

The fit is not perfect and the ephemeris is a prediction. CelesTrak publishes the RMS of
each fit (``starlink.rms.txt``): 0.1 to 5 km per satellite when read on 2026-09-02. So a
supplemental set is better than the GP set for a Starlink secondary, and is still not the
truth; the output records which set was used (``secondary_ephemeris`` in the events).

This module fetches the file with the same cache and two-hour floor as the GP groups,
matches its records to a snapshot by NORAD id, and returns a copy of the snapshot with
the matched objects' elements replaced and an ``ephemeris`` column that says which set
each object carries. Records for satellites not yet in the public catalogue carry
placeholder ids above 100000 and match nothing; they are counted and skipped.
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

from driftwatch import config
from driftwatch.catalogue.celestrak import GroupFetch, fetch_cached
from driftwatch.catalogue.snapshot import OMM_FIELDS, records_to_frame
from driftwatch.orbit.propagator import build_satrecs, mean_orbit_geometry

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


def apply_supplemental(
    snapshot: pd.DataFrame,
    records: Sequence[dict[str, Any]],
    *,
    name: str = "starlink",
    max_lag_days: float = config.SUPPLEMENTAL_MAX_LAG_DAYS,
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
    sup = supplemental_frame(records)
    n_records = int(len(sup))
    if n_records == 0:
        match = SupplementalMatch(name, 0, 0, 0, 0, 0, float("nan"))
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
        match = SupplementalMatch(name, n_records, n_placeholder, n_unmatched, 0, 0, float("nan"))
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
