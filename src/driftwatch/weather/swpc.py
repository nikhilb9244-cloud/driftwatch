"""NOAA SWPC: what CelesTrak does not predict, and the context for what it does.

Four products, each cached with a floor and each stamped with the time it was **issued**
rather than the time it was fetched. A forecast is only reproducible if you know which
forecast it was, and SWPC reissues these several times a day.

``kp-forecast``
    ``noaa-planetary-k-index-forecast.json``: one row per three-hour interval, about a week
    of observed and estimated values and then three days predicted, each row saying which it
    is. This is the three-day Kp forecast.
``kp-realtime``
    ``planetary_k_index_1m.json``: the estimated planetary K index once a minute, from the
    ground magnetometer network, before the definitive index exists. Context rather than a
    driver: the density model wants the three-hourly index.
``outlook-27day``
    ``27-day-outlook.txt``: daily 10.7 cm flux, planetary A index and largest Kp, 27 days
    ahead. Text only — SWPC publishes no JSON for it.
``solar-wind``
    ``propagated-solar-wind.json``: speed, density, temperature and the interplanetary
    magnetic field at L1 propagated to the bow shock, a week of it at one-minute cadence.
    Both the "magnetic field" and the "plasma" the prompt asks for, in one series.

**Where the issue time comes from.** The text products carry their own ``:Issued:`` line and
that is used. The JSON products carry none, and their HTTP ``Last-Modified`` is the time the
file was last regenerated rather than the time the forecast was made — measured on
2026-09-02, ``Last-Modified`` was 36 seconds before the request. So for the Kp forecast the
three-day text product is fetched alongside the JSON purely for its ``:Issued:`` line: two
small requests at most every half hour, in exchange for knowing which forecast a stored run
used. For the observation feeds (the real-time index and the solar wind) the issue time is
the last observation in the series, which is the honest answer for a stream.

**Storage.** One file per issue under ``data/weather/swpc/``, named for the product and the
issue time and never overwritten, with a sidecar recording the URL, the fetch time, the
issue time and where the issue time came from. A stored run can then be rescored against the
forecast it actually used, months later, whatever SWPC is serving now.

**Except the solar wind, which is rolled.** That feed serves a week at one minute and every
fetch repeats the whole week, so the store would grow by a megabyte a fetch for data it
already holds. :func:`roll_solar_wind` keeps the minute cadence for
:data:`driftwatch.config.SOLAR_WIND_MINUTE_DAYS` days and summarises anything older into one
hourly archive -- with the Bz and speed extremes beside the means, because an hourly mean of
Bz averages away exactly the southward excursions that drive a storm. It is the only place
where raw data is deleted, and it is deliberately not done to the forecast products.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.catalogue.celestrak import make_client
from driftwatch.orbit.time import stamp

log = logging.getLogger(__name__)

PRODUCTS: dict[str, dict[str, Any]] = {
    "kp-forecast": {
        "url": config.SWPC_KP_FORECAST_URL,
        "suffix": ".json",
        "min_interval": config.SWPC_KP_MIN_INTERVAL,
        "kind": "forecast",
    },
    "kp-realtime": {
        "url": config.SWPC_KP_REALTIME_URL,
        "suffix": ".json",
        "min_interval": config.SWPC_KP_MIN_INTERVAL,
        "kind": "observation",
    },
    "outlook-27day": {
        "url": config.SWPC_27DAY_URL,
        "suffix": ".txt",
        "min_interval": config.SWPC_27DAY_MIN_INTERVAL,
        "kind": "forecast",
    },
    "solar-wind": {
        "url": config.SWPC_SOLAR_WIND_URL,
        "suffix": ".json",
        "min_interval": config.SWPC_SOLAR_WIND_MIN_INTERVAL,
        "kind": "observation",
    },
}
ISSUED_RE = re.compile(r"^:Issued:\s*(.+?)\s*$", re.MULTILINE)
# "2026 Aug 31 0155 UTC"
ISSUED_FORMAT = "%Y %b %d %H%M %Z"
# "2026 Aug 31     110          12          3"
OUTLOOK_ROW_RE = re.compile(r"^(\d{4})\s+(\w{3})\s+(\d{1,2})\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Fetched:
    """One stored version of one product: where it is, when it was issued and how we know."""

    product: str
    path: Path
    issued_at: datetime
    issued_from: str  # 'product' (its own :Issued: line), 'companion', 'last-observation' or 'fetch-time'
    fetched_at: datetime
    from_cache: bool


def product_dir(out_dir: Path = config.WEATHER_DIR) -> Path:
    return Path(out_dir) / "swpc"


def list_versions(product: str, out_dir: Path = config.WEATHER_DIR) -> list[Path]:
    """Every stored version of ``product``, oldest first."""
    suffix = PRODUCTS[product]["suffix"] if product in PRODUCTS else ".json"
    # The sidecars sit beside the versions and end in the same suffix, so they are excluded
    # by name rather than by glob: '*.json' happily matches 'x.json.meta.json'.
    return sorted(p for p in product_dir(out_dir).glob(f"{product}_*{suffix}") if not p.name.endswith(".meta.json"))


def latest_version(product: str, out_dir: Path = config.WEATHER_DIR) -> Path | None:
    versions = list_versions(product, out_dir)
    return versions[-1] if versions else None


def read_meta(path: Path) -> dict[str, Any]:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    return json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}


def parse_issued(text: str) -> datetime | None:
    """The ``:Issued:`` line of a SWPC text product, e.g. ``:Issued: 2026 Aug 31 0155 UTC``."""
    match = ISSUED_RE.search(text)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        return datetime.strptime(raw, ISSUED_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        try:  # some products omit the trailing zone
            return datetime.strptime(raw.removesuffix(" UTC").strip(), "%Y %b %d %H%M").replace(tzinfo=UTC)
        except ValueError:
            log.warning("Could not read a SWPC issue time from %r", raw)
            return None


def _last_observation(product: str, text: str) -> datetime | None:
    """The last ``time_tag`` in an observation feed, which is when it was current."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not data:
        return None
    if isinstance(data[0], list):  # array-of-arrays with a header row
        header = [str(c) for c in data[0]]
        if "time_tag" not in header:
            return None
        idx = header.index("time_tag")
        values = [row[idx] for row in data[1:] if len(row) > idx]
    else:
        values = [row.get("time_tag") for row in data if isinstance(row, dict)]
    stamps = pd.to_datetime(pd.Series([v for v in values if v]), utc=True, errors="coerce").dropna()
    return stamps.max().to_pydatetime() if len(stamps) else None


def fetch_product(
    product: str,
    *,
    out_dir: Path = config.WEATHER_DIR,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
    force: bool = False,
) -> Fetched:
    """Fetch one SWPC product unless a stored version is newer than its cache floor.

    A version whose issue time matches one already stored is not written again, so the store
    holds one file per issue rather than one per fetch.
    """
    if product not in PRODUCTS:
        raise ValueError(f"unknown SWPC product {product!r}; known: {sorted(PRODUCTS)}")
    spec = PRODUCTS[product]
    now = now or datetime.now(UTC)
    newest = latest_version(product, out_dir)

    if newest is not None:
        meta = read_meta(newest)
        fetched_at = datetime.fromisoformat(meta["fetched_at"]) if meta.get("fetched_at") else now
        if offline or (not force and now - fetched_at < spec["min_interval"]):
            log.info("Using stored SWPC %s issued %s", product, meta.get("issued_at"))
            return Fetched(
                product,
                newest,
                datetime.fromisoformat(meta["issued_at"]),
                str(meta.get("issued_from", "fetch-time")),
                fetched_at,
                True,
            )
    if offline:
        raise FileNotFoundError(f"No stored SWPC {product} and offline=True")

    own = client is None
    client = client or make_client()
    try:
        response = client.get(spec["url"], headers={"Accept": "*/*"})
        response.raise_for_status()
        text = response.text
        issued, issued_from = parse_issued(text), "product"
        if issued is None and spec["kind"] == "observation":
            issued, issued_from = _last_observation(product, text), "last-observation"
        if issued is None and product == "kp-forecast":
            # The JSON carries no issue line and Last-Modified is a regeneration time, so the
            # three-day text product is fetched alongside it purely for its :Issued: line.
            companion = client.get(config.SWPC_3DAY_URL, headers={"Accept": "*/*"})
            if companion.status_code == 200:
                issued, issued_from = parse_issued(companion.text), "companion"
        if issued is None:
            issued, issued_from = now, "fetch-time"
    finally:
        if own:
            client.close()

    path = product_dir(out_dir) / f"{product}_{stamp(issued)}{spec['suffix']}"
    if path.exists():
        log.info("SWPC %s issued %s is already stored", product, issued.isoformat(timespec="minutes"))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
        log.info("Stored SWPC %s issued %s (%d bytes)", product, issued.isoformat(timespec="minutes"), len(text))
    path.with_suffix(path.suffix + ".meta.json").write_text(
        json.dumps(
            {
                "product": product,
                "url": spec["url"],
                "issued_at": issued.isoformat(),
                "issued_from": issued_from,
                "fetched_at": now.isoformat(),
                "bytes": len(text),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return Fetched(product, path, issued, issued_from, now, False)


# --------------------------------------------------------------------------------------
# Parsers


def parse_kp_forecast(text: str) -> pd.DataFrame:
    """``t``, ``kp`` and ``observed`` (observed / estimated / predicted) per three-hour interval."""
    data = json.loads(text)
    frame = pd.DataFrame(data)
    if frame.empty:
        return pd.DataFrame(columns=["t", "kp", "observed", "noaa_scale"])
    frame = frame.rename(columns={"time_tag": "t"})
    frame["t"] = pd.to_datetime(frame["t"], utc=True)
    frame["kp"] = pd.to_numeric(frame["kp"], errors="coerce")
    frame["observed"] = frame["observed"].astype("string")
    if "noaa_scale" not in frame.columns:
        frame["noaa_scale"] = pd.NA
    return frame[["t", "kp", "observed", "noaa_scale"]].sort_values("t").reset_index(drop=True)


def parse_kp_realtime(text: str) -> pd.DataFrame:
    """``t``, ``kp`` (the estimated planetary index) once a minute."""
    frame = pd.DataFrame(json.loads(text))
    if frame.empty:
        return pd.DataFrame(columns=["t", "kp", "kp_index"])
    # The feed carries three things called Kp: the integer index, the estimated value, and a
    # string like "2M" that is the index with a quality letter. Keep the first two.
    frame = frame.drop(columns=[c for c in ("kp",) if c in frame.columns])
    frame = frame.rename(columns={"time_tag": "t", "estimated_kp": "kp"})
    frame["t"] = pd.to_datetime(frame["t"], utc=True)
    for column in ("kp", "kp_index"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame[[c for c in ("t", "kp", "kp_index") if c in frame.columns]].sort_values("t").reset_index(drop=True)


def parse_27day_outlook(text: str) -> pd.DataFrame:
    """``date``, ``f107``, ``ap`` and ``kp_max`` for each of the next 27 days.

    The outlook is a **daily** product: one flux, one planetary A index and one largest Kp per
    day. The table spreads the A index flat across the day's eight intervals rather than the
    largest Kp, because a daily maximum repeated eight times would badly overstate the day for
    a density model that wants the average. See :mod:`driftwatch.weather.table`.
    """
    rows = []
    for year, month, day, f107, ap, kp_max in OUTLOOK_ROW_RE.findall(text):
        try:
            date = datetime.strptime(f"{year} {month} {day}", "%Y %b %d").replace(tzinfo=UTC)
        except ValueError:
            continue
        rows.append({"date": date, "f107": float(f107), "ap": float(ap), "kp_max": float(kp_max)})
    frame = pd.DataFrame(rows, columns=["date", "f107", "ap", "kp_max"])
    if len(frame):
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.sort_values("date").reset_index(drop=True) if len(frame) else frame


SOLAR_WIND_COLUMNS: tuple[str, ...] = (
    "t",
    "speed_kms",
    "density_cm3",
    "temperature_k",
    "bx_nt",
    "by_nt",
    "bz_nt",
    "bt_nt",
)


def parse_solar_wind(text: str) -> pd.DataFrame:
    """The propagated L1 solar wind: speed, density, temperature and the magnetic field.

    SWPC serves this as an array of arrays with the column names in the first row.
    """
    data = json.loads(text)
    if not data or not isinstance(data[0], list):
        return pd.DataFrame(columns=list(SOLAR_WIND_COLUMNS))
    frame = pd.DataFrame(data[1:], columns=[str(c) for c in data[0]])
    frame = frame.rename(
        columns={
            "time_tag": "t",
            "speed": "speed_kms",
            "density": "density_cm3",
            "temperature": "temperature_k",
            "bx": "bx_nt",
            "by": "by_nt",
            "bz": "bz_nt",
            "bt": "bt_nt",
        }
    )
    frame["t"] = pd.to_datetime(frame["t"], utc=True, errors="coerce")
    for column in SOLAR_WIND_COLUMNS[1:]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    keep = [c for c in SOLAR_WIND_COLUMNS if c in frame.columns]
    return frame[keep].dropna(subset=["t"]).sort_values("t").reset_index(drop=True)


PARSERS = {
    "kp-forecast": parse_kp_forecast,
    "kp-realtime": parse_kp_realtime,
    "outlook-27day": parse_27day_outlook,
    "solar-wind": parse_solar_wind,
}


def load(product: str, path: Path | None = None, out_dir: Path = config.WEATHER_DIR) -> pd.DataFrame:
    """Parse a stored version of ``product`` (the newest, unless ``path`` names one)."""
    path = path or latest_version(product, out_dir)
    if path is None:
        raise FileNotFoundError(f"no stored SWPC {product} under {product_dir(out_dir)}")
    return PARSERS[product](path.read_text(encoding="utf-8"))


def solar_wind_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """Speed and southward field over the series: the two numbers that say whether a storm is coming."""
    if not len(frame):
        return {"n": 0}
    bz = frame["bz_nt"].to_numpy(dtype=float) if "bz_nt" in frame.columns else np.array([np.nan])
    speed = frame["speed_kms"].to_numpy(dtype=float) if "speed_kms" in frame.columns else np.array([np.nan])
    return {
        "n": int(len(frame)),
        "range": [str(frame["t"].min()), str(frame["t"].max())],
        "speed_kms": {"median": float(np.nanmedian(speed)), "max": float(np.nanmax(speed))},
        # Southward Bz is what lets the solar wind couple into the magnetosphere, so the
        # minimum matters and the maximum does not.
        "bz_nt_min": float(np.nanmin(bz)),
        "hours_bz_below_minus_5": round(float(np.nansum(bz < -5.0)) / 60.0, 2),
    }


# --------------------------------------------------------------------------------------
# Rolling the solar wind: one minute for a week, hourly for ever


SOLAR_WIND_ARCHIVE = "solar-wind-hourly.parquet"
HOURLY_COLUMNS: tuple[str, ...] = (
    "t",
    "n",
    "speed_kms",
    "speed_kms_max",
    "density_cm3",
    "temperature_k",
    "bx_nt",
    "by_nt",
    "bz_nt",
    "bz_nt_min",
    "bz_nt_max",
    "bt_nt",
)


def hourly_means(frame: pd.DataFrame) -> pd.DataFrame:
    """One row an hour: the means, and the extremes that a mean would destroy.

    A mean is the wrong summary for the interplanetary magnetic field. What couples the solar
    wind into the magnetosphere is a **southward** Bz, and an hour that swings from -15 to +15
    nT averages to zero while being the most geoeffective hour of the storm. So the archive
    carries ``bz_nt_min`` and ``bz_nt_max`` beside the mean, and the peak speed beside the mean
    speed. ``n`` is how many minutes went into the row, which is how a gap stays visible.
    """
    if not len(frame):
        return pd.DataFrame(columns=list(HOURLY_COLUMNS))
    f = frame.copy()
    f["t"] = pd.to_datetime(f["t"], utc=True)
    grouped = f.set_index("t").resample("1h")
    out = grouped.mean(numeric_only=True)
    out["n"] = grouped.size()
    if "bz_nt" in f.columns:
        out["bz_nt_min"] = grouped["bz_nt"].min()
        out["bz_nt_max"] = grouped["bz_nt"].max()
    if "speed_kms" in f.columns:
        out["speed_kms_max"] = grouped["speed_kms"].max()
    out = out[out["n"] > 0].reset_index()
    out["t"] = out["t"].astype("datetime64[us, UTC]")
    return out[[c for c in HOURLY_COLUMNS if c in out.columns]]


def archive_path(out_dir: Path = config.WEATHER_DIR) -> Path:
    return product_dir(out_dir) / SOLAR_WIND_ARCHIVE


def load_solar_wind_archive(out_dir: Path = config.WEATHER_DIR) -> pd.DataFrame:
    """The rolled hourly series, or an empty frame if nothing has been rolled yet."""
    path = archive_path(out_dir)
    if not path.exists():
        return pd.DataFrame(columns=list(HOURLY_COLUMNS))
    return pd.read_parquet(path)


def roll_solar_wind(
    *, out_dir: Path = config.WEATHER_DIR, now: datetime | None = None, keep_days: int | None = None
) -> dict[str, Any]:
    """Keep the minute cadence for a week and roll everything older into the hourly archive.

    The feed serves the last seven days at one minute and every fetch repeats the whole week,
    so the store grows by a megabyte a fetch for data it already holds. A version issued more
    than ``keep_days`` ago contains nothing newer than that, so it can be summarised to hourly
    means and dropped: the most recent version still carries every minute of the last week.

    This is the one place in the store where raw data is deleted rather than kept. It is the
    right trade for an observation stream used as replay context -- the hourly series keeps the
    shape of a storm, including its southward field extremes -- and it is deliberately not
    applied to the forecast products, whose whole point is that a stored run can be rescored
    against the forecast it actually used.
    """
    now = now or datetime.now(UTC)
    keep_days = config.SOLAR_WIND_MINUTE_DAYS if keep_days is None else keep_days
    cutoff = now - timedelta(days=keep_days)
    rolled: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    for path in list_versions("solar-wind", out_dir):
        meta = read_meta(path)
        issued = meta.get("issued_at")
        if not issued or datetime.fromisoformat(issued) > cutoff:
            continue
        try:
            frames.append(hourly_means(parse_solar_wind(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            log.warning("Cannot roll %s (%s); leaving it alone", path.name, exc)
            continue
        rolled.append({"file": path.name, "issued_at": issued, "bytes": path.stat().st_size})
        path.unlink()
        sidecar = Path(str(path) + ".meta.json")
        if sidecar.exists():
            sidecar.unlink()
    if not frames:
        return {"n_rolled": 0, "archive_rows": len(load_solar_wind_archive(out_dir))}

    combined = pd.concat([load_solar_wind_archive(out_dir), *frames], ignore_index=True)
    # Two versions overlap by up to a week, so the same hour arrives more than once. The row
    # built from more minutes is the better summary of that hour, so it wins.
    combined = combined.sort_values(["t", "n"]).drop_duplicates("t", keep="last").sort_values("t")
    path = archive_path(out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    combined.reset_index(drop=True).to_parquet(path, index=False)
    meta_path = Path(str(path) + ".meta.json")
    previous = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    history = [*previous.get("rolled", []), *rolled]
    meta_path.write_text(
        json.dumps(
            {
                "product": "solar-wind-hourly",
                "note": "Hourly means of the minute-cadence feed, with the Bz and speed extremes. The "
                "minute files listed here were summarised into this archive and deleted.",
                "keep_days": keep_days,
                "rows": int(len(combined)),
                "range": [str(combined["t"].min()), str(combined["t"].max())],
                "rolled": history,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    summary = {
        "n_rolled": len(rolled),
        "kilobytes_freed": round(sum(r["bytes"] for r in rolled) / 1024.0, 1),
        "archive_rows": int(len(combined)),
        "archive_range": [str(combined["t"].min()), str(combined["t"].max())],
    }
    log.info("Rolled the solar wind: %s", summary)
    return summary


def store_status(out_dir: Path = config.WEATHER_DIR) -> dict[str, Any]:
    """What the SWPC store holds, per product, for the log and the report."""
    out: dict[str, Any] = {}
    for product in PRODUCTS:
        versions = list_versions(product, out_dir)
        if not versions:
            out[product] = {"n_versions": 0}
            continue
        metas = [read_meta(v) for v in versions]
        issued = [m.get("issued_at") for m in metas if m.get("issued_at")]
        out[product] = {
            "n_versions": len(versions),
            "first_issued": min(issued) if issued else None,
            "last_issued": max(issued) if issued else None,
            "issued_from": sorted({str(m.get("issued_from")) for m in metas}),
            "kilobytes": round(sum(v.stat().st_size for v in versions) / 1024.0, 1),
        }
    archive = archive_path(out_dir)
    if archive.exists():
        rolled = load_solar_wind_archive(out_dir)
        out["solar-wind-hourly"] = {
            "n_rows": int(len(rolled)),
            "range": [str(rolled["t"].min()), str(rolled["t"].max())] if len(rolled) else None,
            "kilobytes": round(archive.stat().st_size / 1024.0, 1),
        }
    return out


def fetch_all(
    *,
    out_dir: Path = config.WEATHER_DIR,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
    products: tuple[str, ...] = tuple(PRODUCTS),
) -> dict[str, Fetched]:
    """Fetch every product, keeping going past one that fails."""
    now = now or datetime.now(UTC)
    own = client is None
    client = client or make_client()
    out: dict[str, Fetched] = {}
    try:
        for product in products:
            try:
                out[product] = fetch_product(product, out_dir=out_dir, client=client, now=now, offline=offline)
            except (httpx.HTTPError, FileNotFoundError, json.JSONDecodeError) as exc:
                log.warning("SWPC %s unavailable (%s)", product, exc)
    finally:
        if own:
            client.close()
    return out


def stored_before(product: str, when: datetime, out_dir: Path = config.WEATHER_DIR) -> Path | None:
    """The newest stored version of ``product`` issued at or before ``when``.

    This is what makes a stored run reproducible: rescoring a run made last Tuesday uses the
    forecast that existed last Tuesday, not the one SWPC is serving today.
    """
    best: tuple[datetime, Path] | None = None
    for path in list_versions(product, out_dir):
        meta = read_meta(path)
        issued = meta.get("issued_at")
        if not issued:
            continue
        issued_at = datetime.fromisoformat(issued)
        if issued_at <= when and (best is None or issued_at > best[0]):
            best = (issued_at, path)
    return best[1] if best else None


def timedelta_hours(td: timedelta) -> float:
    return td.total_seconds() / 3600.0
