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

**Every layer says how much it can be trusted.** ``provenance`` says whether a row is a
measurement or a forecast; ``skill`` says what kind of forecast, because "forecast" covers
both SWPC's three-day Kp, which has real skill over climatology, and a 27-day recurrence
outlook, which is skilful only for a coronal hole coming round again and is blind to the
coronal mass ejection that causes the storms this project cares about. The five values are
``measured``, ``provisional`` (a measurement not yet definitive), ``forecast``,
``recurrence`` and ``designed`` (a synthetic scenario, which is not a prediction at all);
``none`` marks a gap. :data:`SKILL_BY_SOURCE` maps each layer to its own.

**And how uncertain the index is.** ``ap_sigma`` is the standard deviation of the interval's
ap, which is what Step 3's variance term consumes. A measurement is uncertain only by the
resolution of the index; a forecast is uncertain by the part of the climatological spread
its skill does not remove, ``sigma_clim * sqrt(1 - r^2)``, so beyond three days, where the
correlation is taken to be zero, it widens to the climatological spread itself. The spread
is measured from the observed record rather than assumed. See :func:`ap_uncertainty`.

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

from driftwatch import config

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
    "ap_sigma",
    "ap_daily",
    "f107",
    "f107_81",
    "f107_adj",
    "f107_adj_81",
    "provenance",
    "skill",
    "source",
    "issued_at",
)

# What each layer's numbers are worth. `measured` and `provisional` are observations, the
# second not yet definitive; `forecast` is a forecast with demonstrated skill over
# climatology; `recurrence` is a 27-day recurrence climatology, which anticipates a coronal
# hole coming round again and nothing else -- in particular no coronal mass ejection, which is
# what causes the storms this project exists for. CelesTrak's own six-week prediction is
# derived from SWPC's outlooks, so it is recurrence too however far ahead it is read.
SKILL_BY_SOURCE: dict[str, str] = {
    "celestrak:observed": "measured",
    "swpc:kp-observed": "measured",
    "swpc:kp-estimated": "provisional",
    "swpc:kp-forecast": "forecast",
    "celestrak:predicted": "recurrence",
    "swpc:outlook-27day": "recurrence",
}
SKILLS: tuple[str, ...] = ("measured", "provisional", "forecast", "recurrence", "designed", "none")


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


def ap_step_width(ap: np.ndarray) -> np.ndarray:
    """The width of the Bartels step each ap sits on: the resolution of the index there.

    The table is quasi-logarithmic -- the step from ap 2 to 3 is 1 nT, the step from 300 to
    400 is 100 -- so the resolution of a quiet interval and of a severe one are different
    numbers, and a single "ap is known to +/- x" would be wrong at one end or the other.
    """
    ap = np.asarray(ap, dtype=float)
    out = np.full(ap.shape, np.nan)
    good = np.isfinite(ap)
    if not good.any():
        return out
    idx = np.abs(AP_STEPS[None, :] - np.clip(ap[good], 0.0, AP_STEPS[-1])[:, None]).argmin(axis=1)
    lo = AP_STEPS[np.maximum(idx - 1, 0)]
    hi = AP_STEPS[np.minimum(idx + 1, len(AP_STEPS) - 1)]
    # The mean gap to the neighbours on either side, which at the ends of the table is the
    # one gap there is.
    out[good] = (hi - lo) / 2.0
    return out


def climatological_ap_sigma(
    observed: pd.DataFrame | None, *, before: datetime, days: int | None = None
) -> tuple[float, str]:
    """The spread of three-hourly ap over the ``days`` before ``before``, from the observed record.

    This is what "no forecast skill" is worth: past three days the honest statement about a
    given three-hour interval is that its ap is drawn from the recent climatology. Measured
    rather than assumed, because it depends strongly on where in the solar cycle we are.

    It is a **standard deviation of a strongly skewed distribution**: most intervals are quiet
    and the variance is carried by a few storm days, so this number is several times a typical
    interval's ap. That is the point. A symmetric sigma around a quiet forecast will imply
    negative ap at one standard deviation, which is why Step 3 must use it as a variance on
    the density and not as an interval on the index.
    """
    days = config.AP_CLIMATOLOGY_DAYS if days is None else days
    if observed is not None and len(observed):
        window = observed[
            (observed["t"] > pd.Timestamp(before) - pd.Timedelta(days=days)) & (observed["t"] <= pd.Timestamp(before))
        ]
        values = pd.to_numeric(window["ap"], errors="coerce").dropna()
        if len(values) >= 8:
            return float(values.std(ddof=1)), f"measured over {len(values)} observed intervals"
    log.info("No observed ap in the %d days before %s; using the climatology fallback", days, before)
    return float(config.AP_CLIMATOLOGY_FALLBACK_NT), "fallback (no observed record)"


def forecast_correlation(lead_days: np.ndarray) -> np.ndarray:
    """The prior correlation of a geomagnetic forecast against what happens, by lead time.

    Interpolated between :data:`driftwatch.config.AP_FORECAST_CORRELATION_BY_LEAD_DAY` and
    zero past the last breakpoint, which is three days. A prior of the right order for SWPC's
    three-day Kp forecast, not a measured skill score; May 2024 was far worse than this.
    """
    leads = np.asarray(lead_days, dtype=float)
    xp = np.array([x for x, _ in config.AP_FORECAST_CORRELATION_BY_LEAD_DAY], dtype=float)
    fp = np.array([y for _, y in config.AP_FORECAST_CORRELATION_BY_LEAD_DAY], dtype=float)
    out = np.interp(np.clip(leads, 0.0, None), xp, fp, left=fp[0], right=0.0)
    return np.where(leads > xp[-1], 0.0, out)


def ap_uncertainty(table: pd.DataFrame, *, now: datetime, climatology_sigma: float) -> np.ndarray:
    """The standard deviation of each row's ap, in nT. What Step 3's variance term consumes.

    Three regimes, by what the row is:

    - **A measurement** is uncertain only by the resolution of the index, half a Bartels step.
      SWPC's *estimated* Kp is a measurement that has not been made definitive yet and is
      revised by about a step, so it carries the full step.
    - **A forecast** is uncertain by the part of the climatological spread its skill does not
      remove, ``sigma_clim * sqrt(1 - r^2)``, with ``r`` from :func:`forecast_correlation`.
      At a lead past three days ``r`` is zero and this is the climatological spread itself --
      which is the answer to "what do we know about the ap eleven days from now": nothing that
      the last year's distribution does not already say. It is floored at a fraction of the
      forecast value, because an ap of 100 nT is not known to the same absolute precision as
      an ap of 5.
    - **A gap** has no ap and no uncertainty; NaN stays NaN.

    The lead time is measured from the **issue time of the forecast** where the row has one,
    because that is when the information stopped arriving, and from ``now`` where it does not.
    """
    ap = pd.to_numeric(table["ap"], errors="coerce").to_numpy(dtype=float)
    quantum = ap_step_width(ap)
    provenance = table["provenance"].astype(str).to_numpy()
    source = table["source"].astype(str).to_numpy()

    issued = pd.to_datetime(table["issued_at"], utc=True)
    reference = issued.fillna(pd.Timestamp(now))
    lead_days = (pd.to_datetime(table["t"], utc=True) - reference).dt.total_seconds().to_numpy() / 86400.0
    r = forecast_correlation(np.maximum(lead_days, 0.0))

    out = np.full(len(table), np.nan)
    observed = provenance == "observed"
    out[observed] = quantum[observed] / 2.0
    provisional = source == "swpc:kp-estimated"
    out[provisional] = quantum[provisional]

    ahead = np.isin(provenance, ("forecast", "synthetic"))
    unskilled = climatology_sigma * np.sqrt(np.clip(1.0 - r**2, 0.0, 1.0))
    out[ahead] = np.maximum(
        np.maximum(unskilled[ahead], config.AP_FORECAST_RELATIVE_FLOOR * ap[ahead]), quantum[ahead] / 2.0
    )
    out[~np.isfinite(ap)] = np.nan
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


def weather_table(
    start: datetime, end: datetime, sources: WeatherSources, *, now: datetime | None = None
) -> pd.DataFrame:
    """One row per three-hour interval from ``start`` to ``end``, layered as the module docstring says.

    ``now`` is when the table is being built, which is what a forecast row's lead time is
    measured from when it carries no issue time of its own. It defaults to the window start,
    which is what a live run wants; a rescore of a stored run passes the run's own time so the
    uncertainties come out as they were on the day.
    """
    now = now or start
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
    table["skill"] = table["source"].map(SKILL_BY_SOURCE).fillna("none").astype("string")

    # The uncertainty of the index, measured against the observed record where there is one.
    observed_record = None
    if celestrak is not None and len(celestrak):
        observed_record = celestrak[celestrak["provenance"] == "observed"]
    sigma_clim, how = climatological_ap_sigma(observed_record, before=now)
    table["ap_sigma"] = ap_uncertainty(table, now=now, climatology_sigma=sigma_clim)
    table.attrs["climatological_ap_sigma_nt"] = sigma_clim
    table.attrs["climatological_ap_sigma_from"] = how
    # Microseconds throughout, as everywhere else in the project's parquet files.
    for column in ("t", "issued_at"):
        table[column] = table[column].astype("datetime64[us, UTC]")
    return table[list(TABLE_COLUMNS)]


def apply_synthetic(table: pd.DataFrame, kp: np.ndarray, *, name: str, mask: np.ndarray | None = None) -> pd.DataFrame:
    """Replace the geomagnetic columns with a designed profile, marked ``synthetic``.

    Step 3's storm scenarios build their ap profile from the May 2024 sequence scaled to a
    target level. The solar flux is left alone: a geomagnetic storm does not change F10.7, and
    pretending otherwise would put two unrelated changes behind one scenario name.

    ``mask`` says which intervals the scenario actually designed. A storm occupies a few days
    of a window that is mostly observation or forecast, and relabelling the whole table
    ``synthetic`` would be a false statement about the rows the storm never touched -- their
    provenance, their skill, their issue time and their uncertainty are all still what the feed
    said. Omitted, the whole table is treated as designed, which is what a caller replacing
    every interval means.
    """
    out = table.copy()
    kp = np.asarray(kp, dtype=float)
    if len(kp) != len(out):
        raise ValueError(f"the synthetic profile has {len(kp)} intervals, the table has {len(out)}")
    designed = np.ones(len(out), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    if len(designed) != len(out):
        raise ValueError(f"the mask has {len(designed)} intervals, the table has {len(out)}")
    where = out.index[designed]
    out.loc[where, "kp"] = kp[designed]
    out.loc[where, "ap"] = kp_to_ap(kp[designed])
    # The daily average is recomputed over the whole table, because a day the storm entered
    # partway through has a different average whether or not every one of its intervals moved.
    out["ap_daily"] = out.groupby(out["t"].dt.floor("D"))["ap"].transform("mean")
    out.loc[where, "provenance"] = "synthetic"
    out.loc[where, "skill"] = "designed"
    out.loc[where, "source"] = f"synthetic:{name}"
    out.loc[where, "issued_at"] = pd.NaT
    # A scenario states its ap rather than predicting it, so there is no forecast error to
    # carry. What is left is that the scenario itself is a supposition of that magnitude, so
    # the uncertainty stays at the climatological spread the table was built with -- the
    # widest of its forecast sigmas, which is what a lead past three days already gives.
    # Step 3 may override it per scenario; it must not read zero variance off a storm.
    spread = float(np.nanmax(table["ap_sigma"])) if "ap_sigma" in table.columns else np.nan
    if not np.isfinite(spread):
        spread = float(config.AP_CLIMATOLOGY_FALLBACK_NT)
    ap = out["ap"].to_numpy(dtype=float)
    out.loc[where, "ap_sigma"] = np.maximum(spread, config.AP_FORECAST_RELATIVE_FLOOR * ap[designed])
    return out[list(TABLE_COLUMNS)]


def table_summary(table: pd.DataFrame) -> dict[str, Any]:
    """What a built table covers and where it came from, for the log, the report and run.json."""
    if not len(table):
        return {"n_intervals": 0}
    issued = table["issued_at"].dropna()
    return {
        "n_intervals": int(len(table)),
        "range": [str(table["t"].min()), str(table["t"].max())],
        "by_provenance": table.groupby("provenance", observed=True)["t"].size().to_dict(),
        "by_skill": table.groupby("skill", observed=True)["t"].size().to_dict() if "skill" in table.columns else {},
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
        "ap_sigma": {
            "min": round(float(np.nanmin(table["ap_sigma"])), 3) if table["ap_sigma"].notna().any() else None,
            "max": round(float(np.nanmax(table["ap_sigma"])), 3) if table["ap_sigma"].notna().any() else None,
            "climatological": round(float(table.attrs.get("climatological_ap_sigma_nt", np.nan)), 3),
            "climatological_from": table.attrs.get("climatological_ap_sigma_from"),
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
    now: datetime | None = None,
) -> pd.DataFrame:
    """Convenience wrapper over :func:`weather_table` for callers holding the parsed feeds."""
    sources = WeatherSources(
        celestrak=celestrak_rows,
        kp_forecast=kp_forecast[0] if kp_forecast else None,
        kp_forecast_issued=kp_forecast[1] if kp_forecast else None,
        outlook=outlook[0] if outlook else None,
        outlook_issued=outlook[1] if outlook else None,
    )
    table = weather_table(start, end, sources, now=now)
    log.info("Space weather table: %s", table_summary(table))
    return table


def now_utc() -> datetime:
    return datetime.now(UTC)
