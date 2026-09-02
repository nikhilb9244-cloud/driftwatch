"""CelesTrak's ``SW-All.csv``: the space weather record, and the primary driver.

One row per UTC day from 1 October 1957 (the first day of the International Geophysical
Year, which is where the Kp record begins) to 2041. Each row carries the eight three-hourly
Kp values of the day and their eight ap values, the day's average ap, and the 10.7 cm solar
radio flux with its 81-day averages.

Three things about the file are worth knowing before reading it.

**Kp is published as an integer ten times its value.** ``KP1 = 43`` means Kp = 4.3, which is
the index written "4+" — Kp is quoted in thirds of a unit, so 4.3 is 4 and a third. The
loader divides by ten and rounds to the nearest third, so the values that come out are the
27 the index can actually take.

**F10.7 comes observed and adjusted, and NRLMSIS wants the observed one.** ``F10.7_OBS`` is
the flux measured at Earth; ``F10.7_ADJ`` is that value scaled to a fixed Sun-Earth distance
of 1 AU, which removes the annual 7 % swing from the eccentricity of Earth's orbit. The
adjusted number is the right one for studying the Sun and the wrong one for driving an
atmosphere model, because the atmosphere feels the flux that arrives. Both are loaded and
both are carried into the table; ``docs/space-weather.md`` records the choice.

**The 81-day average comes centred and trailing.** NRLMSIS wants the centred one, so that is
what the table carries; for a future date it is necessarily part prediction, and
``F10.7_DATA_TYPE`` says so.

That last column is the provenance for the whole row: ``OBS`` observed, ``INT`` interpolated
across a gap in the record, ``PRD`` a daily prediction (about six weeks ahead) and ``PRM`` a
monthly prediction (to 2041). Kp and ap stop entirely at the last observed day — CelesTrak
predicts the solar flux but not the geomagnetic index, which is why the table needs SWPC.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.catalogue.celestrak import make_client

log = logging.getLogger(__name__)

KP_COLUMNS: tuple[str, ...] = tuple(f"KP{i}" for i in range(1, 9))
AP_COLUMNS: tuple[str, ...] = tuple(f"AP{i}" for i in range(1, 9))
# What the file's F10.7_DATA_TYPE means, and how the table's provenance column reads it.
DATA_TYPES: dict[str, str] = {
    "OBS": "observed",
    "INT": "observed",  # interpolated across a gap in the record; still not a prediction
    "PRD": "forecast",  # daily prediction, about six weeks out
    "PRM": "forecast",  # monthly prediction, to 2041
}
# Kp is quoted in thirds of a unit: 0, 1/3, 2/3, 1, ... 9. The file stores ten times that.
KP_STEP = 1.0 / 3.0


def sw_path(cache_dir: Path = config.CACHE_DIR) -> Path:
    """Where the cached CSV lives."""
    return cache_dir / "weather" / "SW-All.csv"


def _meta_path(path: Path) -> Path:
    return path.with_suffix(".meta.json")


def fetch_sw_all(
    *,
    cache_dir: Path = config.CACHE_DIR,
    max_age: timedelta = config.CELESTRAK_SW_MAX_AGE,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> Path:
    """Return the path of an ``SW-All.csv`` no older than ``max_age``, downloading if needed.

    The file is three megabytes and is reissued once a day; a stale copy is kept and used if
    the download fails, because a day-old space weather record is far better than none.
    """
    now = now or datetime.now(UTC)
    path = sw_path(cache_dir)
    meta_path = _meta_path(path)
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
        if offline or now - fetched_at < max_age:
            log.info("Using cached SW-All.csv from %s", fetched_at.isoformat(timespec="minutes"))
            return path
    if offline:
        raise FileNotFoundError("No cached SW-All.csv and offline=True")

    own = client is None
    client = client or make_client()
    try:
        log.info("Downloading SW-All.csv")
        response = client.get(config.CELESTRAK_SW_URL, headers={"Accept": "*/*"})
        response.raise_for_status()
    except httpx.HTTPError as exc:
        if path.exists():
            log.warning("SW-All.csv download failed (%s); keeping the stale copy", exc)
            return path
        raise
    finally:
        if own:
            client.close()

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(response.content)
    os.replace(tmp, path)
    meta_path.write_text(
        json.dumps({"url": config.CELESTRAK_SW_URL, "fetched_at": now.isoformat(), "bytes": len(response.content)}),
        encoding="utf-8",
    )
    return path


def _to_kp(values: np.ndarray) -> np.ndarray:
    """Ten times Kp as the file stores it, back to Kp in thirds."""
    kp = np.asarray(values, dtype=float) / 10.0
    return np.round(kp / KP_STEP) * KP_STEP


DAILY_COLUMNS: tuple[str, ...] = (
    "date",
    "ap_daily",
    "f107_obs",
    "f107_adj",
    "f107_obs_81",
    "f107_adj_81",
    "data_type",
    "provenance",
)


def load_sw_all(path: Path) -> pd.DataFrame:
    """The file as two frames' worth of information in one: eight intervals a day, plus the daily columns.

    Returns one row per **three-hour interval** with ``t`` (the interval's start),
    ``kp``, ``ap``, and the day's ``ap_daily``, ``f107_*`` and provenance repeated across its
    eight rows. Rows past the last observed day keep their F10.7 and lose their Kp and ap,
    which is exactly what the file has: NaN there means "CelesTrak does not predict this",
    not "quiet".
    """
    raw = pd.read_csv(path)
    missing = [c for c in ("DATE", *KP_COLUMNS, *AP_COLUMNS, "F10.7_OBS") if c not in raw.columns]
    if missing:
        raise ValueError(f"{path} lacks the columns {missing}; is it CelesTrak's SW-All.csv?")
    duplicated = raw["DATE"].duplicated()
    if duplicated.any():
        # Never seen in the published file, but a repeated date would make the interval index
        # ambiguous and every lookup against it fail, so it is reported and the last kept.
        log.warning(
            "SW-All.csv has %d repeated dates (e.g. %s); keeping the last of each",
            int(duplicated.sum()),
            raw.loc[duplicated, "DATE"].iloc[0],
        )
        raw = raw.drop_duplicates("DATE", keep="last").reset_index(drop=True)
    date = pd.to_datetime(raw["DATE"]).to_numpy(dtype="datetime64[ns]")
    kp = _to_kp(raw[list(KP_COLUMNS)].to_numpy(dtype=float))
    ap = raw[list(AP_COLUMNS)].to_numpy(dtype=float)
    n = len(raw)
    hours = np.tile(np.arange(8) * 3, n)
    rows = pd.DataFrame(
        {
            "t": np.repeat(date, 8) + hours.astype("timedelta64[h]"),
            "kp": kp.reshape(-1),
            "ap": ap.reshape(-1),
            "ap_daily": np.repeat(raw["AP_AVG"].to_numpy(dtype=float), 8),
            "f107_obs": np.repeat(raw["F10.7_OBS"].to_numpy(dtype=float), 8),
            "f107_adj": np.repeat(raw["F10.7_ADJ"].to_numpy(dtype=float), 8),
            "f107_obs_81": np.repeat(raw["F10.7_OBS_CENTER81"].to_numpy(dtype=float), 8),
            "f107_adj_81": np.repeat(raw["F10.7_ADJ_CENTER81"].to_numpy(dtype=float), 8),
            "data_type": np.repeat(raw["F10.7_DATA_TYPE"].astype("string").to_numpy(), 8),
        }
    )
    rows["t"] = pd.to_datetime(rows["t"], utc=True)
    rows["provenance"] = rows["data_type"].map(DATA_TYPES).fillna("forecast").astype("string")
    return rows


def summary(rows: pd.DataFrame) -> dict[str, object]:
    """What the loaded record covers, for the log and the docs."""
    observed = rows[rows["kp"].notna()]
    return {
        "n_intervals": int(len(rows)),
        "range": [str(rows["t"].min()), str(rows["t"].max())],
        "kp_observed_to": str(observed["t"].max()) if len(observed) else None,
        "n_kp_observed": int(len(observed)),
        "by_data_type": rows.groupby("data_type", observed=True)["t"].size().to_dict(),
        "max_kp": float(observed["kp"].max()) if len(observed) else None,
        "max_ap": float(observed["ap"].max()) if len(observed) else None,
    }
