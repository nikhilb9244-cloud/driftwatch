"""CelesTrak SATCAT: the satellite catalogue metadata table.

GP element sets say where an object is but not what it is. SATCAT carries the object
type (payload, rocket body, debris, unknown), the owner, launch date and a radar
cross-section estimate. It changes slowly, so it is cached for a day.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd

from driftwatch import config
from driftwatch.catalogue.celestrak import make_client

log = logging.getLogger(__name__)

SATCAT_COLUMNS = {
    "NORAD_CAT_ID": "norad_id",
    "OBJECT_TYPE": "object_type",
    "OPS_STATUS_CODE": "ops_status",
    "OWNER": "owner",
    "LAUNCH_DATE": "launch_date",
    "DECAY_DATE": "decay_date",
    "RCS": "rcs_m2",
}


def satcat_path(cache_dir: Path = config.CACHE_DIR) -> Path:
    """Location of the cached SATCAT CSV."""
    return cache_dir / "celestrak" / "satcat.csv"


def _meta_path(path: Path) -> Path:
    return path.with_name("satcat.meta.json")


def fetch_satcat(
    *,
    cache_dir: Path = config.CACHE_DIR,
    max_age: timedelta = config.SATCAT_MAX_AGE,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> Path:
    """Return the path of a SATCAT CSV no older than ``max_age``, downloading if needed."""
    now = now or datetime.now(UTC)
    path = satcat_path(cache_dir)
    meta_path = _meta_path(path)
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
        if offline or now - fetched_at < max_age:
            log.info("Using cached SATCAT from %s", fetched_at.isoformat(timespec="minutes"))
            return path
    if offline:
        raise FileNotFoundError("No cached SATCAT and offline=True")

    own_client = client is None
    client = client or make_client()
    try:
        log.info("Downloading SATCAT")
        try:
            response = client.get(config.CELESTRAK_SATCAT_URL, headers={"Accept": "*/*"})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            if path.exists():
                log.warning("SATCAT download failed (%s); keeping stale copy", exc)
                return path
            raise
    finally:
        if own_client:
            client.close()

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(response.content)
    os.replace(tmp, path)
    meta_path.write_text(
        json.dumps({"url": config.CELESTRAK_SATCAT_URL, "fetched_at": now.isoformat()}, indent=2),
        encoding="utf-8",
    )
    return path


def load_satcat(path: Path) -> pd.DataFrame:
    """Load SATCAT as a frame indexed by NORAD id with normalised column names.

    ``object_type`` is one of ``PAY``, ``R/B``, ``DEB`` or ``UNK``; ``rcs_m2`` is NaN
    when CelesTrak does not publish a value.
    """
    df = pd.read_csv(
        path,
        usecols=list(SATCAT_COLUMNS),
        dtype={"NORAD_CAT_ID": "int64", "OBJECT_TYPE": "string", "OPS_STATUS_CODE": "string", "OWNER": "string"},
    )
    df = df.rename(columns=SATCAT_COLUMNS)
    df["rcs_m2"] = pd.to_numeric(df["rcs_m2"], errors="coerce")
    df["launch_date"] = pd.to_datetime(df["launch_date"], errors="coerce").dt.date
    df["decay_date"] = pd.to_datetime(df["decay_date"], errors="coerce").dt.date
    df["object_type"] = df["object_type"].fillna("UNK")
    df = df.drop_duplicates("norad_id", keep="last").set_index("norad_id")
    return df
