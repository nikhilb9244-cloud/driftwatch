"""The space weather table: one row per three-hour interval, and where every number came from.

This is what the density model reads. One row for each three-hour interval a window covers,
carrying the planetary index, the solar flux, and a provenance that says whether the row is
a measurement, a forecast or an invention.

**How the sources are layered**, best first, each filling only what the one above it leaves:

1. **CelesTrak observed** (``celestrak:observed``, which covers the file's ``OBS`` rows and
   the ``INT`` rows where the record was interpolated across a gap). The definitive
   three-hourly Kp and ap and the day's F10.7, back to 1957. Nothing beats a measurement.
2. **SWPC observed and estimated** (``swpc:kp-observed``, ``swpc:kp-estimated``). CelesTrak
   rebuilds its file once a day, so the last day or two before now sits in a gap where
   CelesTrak has only a prediction and SWPC already has the real index — estimated from the
   live magnetometer network for the most recent hours, definitive behind that. Both are
   measurements and both beat any forecast, so they are marked ``observed`` with a source
   that says which.
3. **SWPC's three-day Kp forecast** (``swpc:kp-forecast``). Finer and fresher than anything
   else for the next three days: SWPC reissues it several times a day, and every row carries
   the issue time of the forecast it came from.
4. **CelesTrak predicted** (``celestrak:predicted``), which carries three-hourly Kp and ap for
   about six weeks ahead, and predicted F10.7 for fifteen years.
5. **SWPC's 27-day outlook** (``swpc:outlook-27day``), a daily product: one planetary A index
   per day, spread flat across the day's eight intervals.

Layer 5 is a last resort and rarely reached, because layer 4 already covers six weeks. It is
kept because CelesTrak's predicted Kp is itself derived from SWPC's forecasts, so when the two
disagree it is worth being able to see both.

**Why the 27-day outlook's A index and not its largest Kp.** The outlook publishes a daily
planetary A index and the largest Kp expected that day. A daily maximum repeated across eight
intervals would say the whole day was as disturbed as its worst three hours, which for a
density model driven by the average is badly wrong in the direction that matters. The A index
is already a daily average, so spreading it flat is the honest reading of a daily number, and
``kp`` for those rows is the inverse of the standard ap-to-Kp table rather than the outlook's
own Kp.

**What is not filled.** Nothing. A row with no source anywhere comes back with NaN and
provenance ``missing``; the density model must decide what to do about a gap rather than
have a quiet zero substituted for it. A ``synthetic`` provenance appears only when Step 3
builds a storm scenario, through :func:`apply_synthetic`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

INTERVAL_HOURS = 3
# The standard Kp-to-ap table (Bartels): Kp runs 0, 0+, 1-, 1, 1+, ... 9 in thirds, and ap is
# the quasi-linear amplitude in nanotesla that each step corresponds to. Published in every
# geomagnetic-index reference; reproduced here so the conversion is visible rather than
# hidden in a dependency.
KP_STEPS: np.ndarray = np.round(np.arange(0, 28) / 3.0, 6)
AP_STEPS: np.ndarray = np.array(
    [0, 2, 3, 4, 5, 6, 7, 9, 12, 15, 18, 22, 27, 32, 39, 48, 56, 67, 80, 94, 111, 132, 154, 179, 207, 236, 300, 400],
    dtype=float,
)

TABLE_COLUMNS: tuple[str, ...] = (
    "t",
    "kp",
    "ap",
    "ap_daily",
    "f107",
    "f107_81",
    "f107_adj",
    "f107_adj_81",
    "provenance",
    "source",
    "issued_at",
)


def snap_kp(kp: np.ndarray) -> np.ndarray:
    """Kp to the nearest third, which is the only resolution the index has.

    SWPC serves it rounded to two decimals (0.67, 2.33) and CelesTrak as ten times the value
    (7, 23); snapping both to thirds keeps the column homogeneous and makes the ap lookup a
    table read rather than a nearest-neighbour search that happens to work.
    """
    kp = np.asarray(kp, dtype=float)
    return np.round(kp * 3.0) / 3.0


def kp_to_ap(kp: np.ndarray) -> np.ndarray:
    """The planetary amplitude for each Kp, by the standard table (nearest step)."""
    kp = np.asarray(kp, dtype=float)
    out = np.full(kp.shape, np.nan)
    good = np.isfinite(kp)
    if good.any():
        idx = np.abs(KP_STEPS[None, :] - np.clip(kp[good], 0.0, 9.0)[:, None]).argmin(axis=1)
        out[good] = AP_STEPS[idx]
    return out


def ap_to_kp(ap: np.ndarray) -> np.ndarray:
    """The inverse: the Kp whose tabulated ap is nearest, used where only a daily A index exists."""
    ap = np.asarray(ap, dtype=float)
    out = np.full(ap.shape, np.nan)
    good = np.isfinite(ap)
    if good.any():
        idx = np.abs(AP_STEPS[None, :] - np.clip(ap[good], 0.0, AP_STEPS[-1])[:, None]).argmin(axis=1)
        out[good] = KP_STEPS[idx]
    return out


def intervals(start: datetime, end: datetime) -> pd.DatetimeIndex:
    """Every three-hour interval start from the one containing ``start`` to the one containing ``end``."""
    lo = pd.Timestamp(start).tz_convert("UTC") if pd.Timestamp(start).tzinfo else pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end).tz_convert("UTC") if pd.Timestamp(end).tzinfo else pd.Timestamp(end, tz="UTC")
    lo = lo.floor(f"{INTERVAL_HOURS}h")
    hi = hi.floor(f"{INTERVAL_HOURS}h")
    return pd.date_range(lo, hi, freq=f"{INTERVAL_HOURS}h", tz="UTC")


@dataclass
class WeatherSources:
    """The parsed feeds the table is built from. Anything absent is simply not used."""

    celestrak: pd.DataFrame | None = None  # from weather.celestrak_sw.load_sw_all
    kp_forecast: pd.DataFrame | None = None  # from weather.swpc.parse_kp_forecast
    kp_forecast_issued: datetime | None = None
    outlook: pd.DataFrame | None = None  # from weather.swpc.parse_27day_outlook
    outlook_issued: datetime | None = None


def _fill(
    table: pd.DataFrame, values: pd.DataFrame, columns: tuple[str, ...], source: str, provenance: str, issued: Any
) -> pd.DataFrame:
    """Write ``columns`` from ``values`` (indexed by ``t``) into the rows of ``table`` still missing ``kp``."""
    missing = table["kp"].isna()
    if not missing.any():
        return table
    aligned = values.reindex(table.loc[missing, "t"].to_numpy())
    have = aligned["kp"].notna().to_numpy()
    if not have.any():
        return table
    idx = table.index[missing][have]
    for column in columns:
        if column in aligned.columns:
            table.loc[idx, column] = aligned[column].to_numpy()[have]
    table.loc[idx, "source"] = source
    table.loc[idx, "provenance"] = provenance
    if issued is not None:
        table.loc[idx, "issued_at"] = pd.Timestamp(issued)
    return table


def weather_table(start: datetime, end: datetime, sources: WeatherSources) -> pd.DataFrame:
    """One row per three-hour interval from ``start`` to ``end``, layered as the module docstring says."""
    grid = intervals(start, end)
    table = pd.DataFrame({"t": grid})
    for column in ("kp", "ap", "ap_daily", "f107", "f107_81", "f107_adj", "f107_adj_81"):
        table[column] = np.nan
    table["provenance"] = "missing"
    table["source"] = pd.NA
    table["issued_at"] = pd.Series(pd.NaT, index=table.index, dtype="datetime64[ns, UTC]")

    # F10.7 comes from CelesTrak whatever the Kp source is: it is the only feed that covers
    # the whole range, and the flux and the index are independent measurements anyway.
    celestrak = sources.celestrak
    if celestrak is not None and len(celestrak):
        c = celestrak.set_index("t")
        aligned = c.reindex(grid)
        table["f107"] = aligned["f107_obs"].to_numpy()
        table["f107_81"] = aligned["f107_obs_81"].to_numpy()
        table["f107_adj"] = aligned["f107_adj"].to_numpy()
        table["f107_adj_81"] = aligned["f107_adj_81"].to_numpy()

        observed = c[c["provenance"] == "observed"]
        table = _fill(table, observed, ("kp", "ap", "ap_daily"), "celestrak:observed", "observed", None)

    forecast = sources.kp_forecast
    if forecast is not None and len(forecast):
        # SWPC's own rows say whether each is observed, estimated from the live magnetometers,
        # or predicted. The first two are measurements and fill the day or two between
        # CelesTrak's last rebuild and now; only the third is a forecast.
        f = forecast.copy()
        f["kp"] = snap_kp(f["kp"].to_numpy())
        f["ap"] = kp_to_ap(f["kp"].to_numpy())
        for kind, source, provenance, issued in (
            ("observed", "swpc:kp-observed", "observed", None),
            ("estimated", "swpc:kp-estimated", "observed", None),
            ("predicted", "swpc:kp-forecast", "forecast", sources.kp_forecast_issued),
        ):
            rows = f[f["observed"] == kind]
            if len(rows):
                table = _fill(table, rows.set_index("t"), ("kp", "ap"), source, provenance, issued)

    if celestrak is not None and len(celestrak):
        predicted = celestrak.set_index("t")
        predicted = predicted[predicted["provenance"] == "forecast"]
        table = _fill(table, predicted, ("kp", "ap", "ap_daily"), "celestrak:predicted", "forecast", None)

    outlook = sources.outlook
    if outlook is not None and len(outlook):
        # A daily A index spread flat across the day's eight intervals; see the module docstring.
        daily = outlook.copy()
        daily["kp"] = ap_to_kp(daily["ap"].to_numpy())
        daily["ap_daily"] = daily["ap"]
        expanded = daily.loc[daily.index.repeat(8)].reset_index(drop=True)
        offsets = np.tile(np.arange(8) * INTERVAL_HOURS, len(daily))
        expanded["t"] = pd.to_datetime(expanded["date"]) + pd.to_timedelta(offsets, unit="h")
        expanded = expanded.set_index("t")
        table = _fill(
            table, expanded, ("kp", "ap", "ap_daily"), "swpc:outlook-27day", "forecast", sources.outlook_issued
        )

    # A day's average ap where no source supplied one: the mean of whatever the day has.
    day = table["t"].dt.floor("D")
    filled = table.groupby(day)["ap"].transform("mean")
    table["ap_daily"] = table["ap_daily"].fillna(filled)
    table["provenance"] = table["provenance"].astype("string")
    table["source"] = table["source"].astype("string")
    # Microseconds throughout, as everywhere else in the project's parquet files.
    for column in ("t", "issued_at"):
        table[column] = table[column].astype("datetime64[us, UTC]")
    return table[list(TABLE_COLUMNS)]


def apply_synthetic(table: pd.DataFrame, kp: np.ndarray, *, name: str) -> pd.DataFrame:
    """Replace the geomagnetic columns with a designed profile, marked ``synthetic``.

    Step 3's storm scenarios build their ap profile from the May 2024 sequence scaled to a
    target level. The solar flux is left alone: a geomagnetic storm does not change F10.7, and
    pretending otherwise would put two unrelated changes behind one scenario name.
    """
    out = table.copy()
    kp = np.asarray(kp, dtype=float)
    if len(kp) != len(out):
        raise ValueError(f"the synthetic profile has {len(kp)} intervals, the table has {len(out)}")
    out["kp"] = kp
    out["ap"] = kp_to_ap(kp)
    out["ap_daily"] = out.groupby(out["t"].dt.floor("D"))["ap"].transform("mean")
    out["provenance"] = "synthetic"
    out["source"] = f"synthetic:{name}"
    out["issued_at"] = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]")
    return out


def table_summary(table: pd.DataFrame) -> dict[str, Any]:
    """What a built table covers and where it came from, for the log, the report and run.json."""
    if not len(table):
        return {"n_intervals": 0}
    issued = table["issued_at"].dropna()
    return {
        "n_intervals": int(len(table)),
        "range": [str(table["t"].min()), str(table["t"].max())],
        "by_provenance": table.groupby("provenance", observed=True)["t"].size().to_dict(),
        "by_source": table.groupby("source", observed=True, dropna=False)["t"].size().to_dict(),
        "n_missing": int((table["provenance"] == "missing").sum()),
        "kp": {
            "max": float(np.nanmax(table["kp"])) if table["kp"].notna().any() else None,
            "mean": float(np.nanmean(table["kp"])) if table["kp"].notna().any() else None,
        },
        "ap": {
            "max": float(np.nanmax(table["ap"])) if table["ap"].notna().any() else None,
            "mean": float(np.nanmean(table["ap"])) if table["ap"].notna().any() else None,
        },
        "f107": {
            "first": float(table["f107"].iloc[0]) if table["f107"].notna().any() else None,
            "f107_81_first": float(table["f107_81"].iloc[0]) if table["f107_81"].notna().any() else None,
        },
        "forecast_issued": [str(v) for v in sorted(issued.unique())] if len(issued) else [],
    }


def build(
    start: datetime,
    end: datetime,
    *,
    celestrak_rows: pd.DataFrame | None = None,
    kp_forecast: tuple[pd.DataFrame, datetime] | None = None,
    outlook: tuple[pd.DataFrame, datetime] | None = None,
) -> pd.DataFrame:
    """Convenience wrapper over :func:`weather_table` for callers holding the parsed feeds."""
    sources = WeatherSources(
        celestrak=celestrak_rows,
        kp_forecast=kp_forecast[0] if kp_forecast else None,
        kp_forecast_issued=kp_forecast[1] if kp_forecast else None,
        outlook=outlook[0] if outlook else None,
        outlook_issued=outlook[1] if outlook else None,
    )
    table = weather_table(start, end, sources)
    log.info("Space weather table: %s", table_summary(table))
    return table


def now_utc() -> datetime:
    return datetime.now(UTC)
