"""The radio horizon: the calibration benchmark's residuals as angles on the sky, by lead and window.

The calibration benchmark (``storm/precise.py``, ``docs/calibration-benchmark.md``) measured, for
every public element set issued in three windows, how far SGP4 put Swarm A, B and C from ESA's
precise orbit at leads from six hours to seven days, in the satellite's radial, in-track,
cross-track frame. Its horizon was stated in kilometres along track, because a screening box is
a box. A dish's beam is an angle, and the two components matter differently: an along-track
error moves the satellite along its path, so it changes *when* a crossing happens; a cross-track
error moves the path sideways, so it decides *whether* the crossing happens at all.

This module converts each trial's residual into the angle it would subtend from the site, and
computes, for each lead bin and window, the fraction of trials whose cross-track angular error is
under a third of the beam's half-power width for each receiver. That table is the radio horizon.
The same fraction is computed for the along-track angular error beside it, because for this
population the cross-track fraction is one at every lead and the along-track error is the number
that moves; the along-track figure is also given as a time shift at the orbital speed.

The conversion is at zenith range. A residual perpendicular to the line of sight subtends
``residual / range``; the range from the site is smallest, and the angle largest, when the
satellite is overhead, where the range is the altitude and both the in-track and cross-track
directions lie across the line of sight. Every angle here is therefore the largest the residual
could subtend from the site; lower in the sky the same residual subtends less, by the ratio of
the altitude to the range and by the projection of the direction onto the sky. The per-crossing
numbers in ``crossings.py`` use the actual geometry; the table uses the bound, and says so.

The altitude of each trial is the mean altitude the element set implies (its Brouwer mean
semi-major axis less the equatorial radius), which is within a few kilometres of the truth and
enters the angle at the one per cent level.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.catalogue import history
from driftwatch.orbit.propagator import build_satrecs, mean_orbit_geometry
from driftwatch.radio import site as site_mod
from driftwatch.radio.site import RECEIVERS, Receiver, angular_error_deg, beam_fwhm_deg

TRIALS_PARQUET = config.DATA_DIR / "validation" / "swarm_benchmark.parquet"
TRIALS_CSV = config.DATA_DIR / "radio" / "swarm_trials.csv"

WINDOW_LABELS: dict[str, str] = {
    "quiet": "quiet week, 20 to 27 April 2024",
    "storm": "May 2024 storm, sets issued 6 to 13 May",
    "held-out": "October 2024 storm, sets issued 6 to 13 October (held out)",
}
WINDOW_SHORT: dict[str, str] = {"quiet": "quiet", "storm": "May 2024", "held-out": "October 2024"}
WINDOW_ORDER = ("quiet", "storm", "held-out")

# The fraction of trials the horizon asks for, the benchmark's own 95th-percentile rule as a
# coverage, and the fraction of the beam width the angular error is held to.
COVERAGE = 0.95
BEAM_FRACTION = 1.0 / 3.0

# The columns the table is computed for: each receiver at its band centre, and the L and S
# receivers at the top of their bands as well, where the beam is narrowest and the test strictest.
TABLE_FREQUENCIES: tuple[tuple[str, float], ...] = (
    ("UHF", RECEIVERS["UHF"].centre_mhz),
    ("L", RECEIVERS["L"].centre_mhz),
    ("L", RECEIVERS["L"].hi_mhz),
    ("S0", RECEIVERS["S0"].centre_mhz),
    ("S4", RECEIVERS["S4"].hi_mhz),
)

TRIAL_COLUMNS = [
    "satellite",
    "norad_id",
    "window",
    "set_epoch",
    "lead_h",
    "t",
    "radial_km",
    "in_track_km",
    "cross_km",
    "altitude_km",
    "speed_km_s",
]

# WGS72 gravitational parameter, km^3/s^2, the constant SGP4 uses.
_MU_KM3_S2 = 398600.8


@dataclass(frozen=True)
class Column:
    receiver: str
    freq_mhz: float
    fwhm_deg: float

    @property
    def key(self) -> str:
        return f"{self.receiver}@{self.freq_mhz:g}"

    @property
    def along_key(self) -> str:
        return f"along:{self.key}"

    @property
    def label(self) -> str:
        return f"{self.receiver} {self.freq_mhz:g} MHz"


def table_columns(frequencies: Iterable[tuple[str, float]] = TABLE_FREQUENCIES) -> list[Column]:
    return [Column(name, float(f), beam_fwhm_deg(f)) for name, f in frequencies]


def receiver_column(rx: Receiver, freq_mhz: float | None = None) -> Column:
    f = float(freq_mhz) if freq_mhz is not None else rx.centre_mhz
    return Column(rx.name, f, beam_fwhm_deg(f))


# --------------------------------------------------------------------------------------
# Loading the trials and attaching the geometry


def usable(trials: pd.DataFrame) -> pd.DataFrame:
    """The trials the benchmark scored: truth present, SGP4 converged, no manoeuvre in the arc."""
    keep = trials["cross_km"].notna() & trials["in_track_km"].notna()
    if "manoeuvre" in trials.columns:
        keep &= ~trials["manoeuvre"].fillna(False).astype(bool)
    if "gap" in trials.columns:
        keep &= ~trials["gap"].fillna(False).astype(bool)
    if "sgp4_error" in trials.columns:
        keep &= trials["sgp4_error"].fillna(0).astype(int) == 0
    return trials[keep].reset_index(drop=True)


def attach_altitude(trials: pd.DataFrame, history_dir: Path = config.HISTORY_DIR) -> pd.DataFrame:
    """Add ``altitude_km`` and ``speed_km_s`` per trial from the element set the trial propagated.

    The set is looked up in the history store by NORAD id and epoch; its mean semi-major axis
    gives the altitude, and the circular speed at that radius the along-track speed. A trial
    whose set is not in the store takes the median of its satellite's other sets in the window;
    if there is none, the function refuses rather than invent a number.
    """
    out = trials.copy()
    ids = sorted({int(i) for i in out["norad_id"]})
    epochs = pd.to_datetime(out["set_epoch"])
    if epochs.dt.tz is None:
        epochs = epochs.dt.tz_localize("UTC")
    start = epochs.min().to_pydatetime() - timedelta(days=1)
    end = epochs.max().to_pydatetime() + timedelta(days=1)
    sets = history.load_history(norad_ids=ids, start=start, end=end, history_dir=history_dir)
    if sets.empty:
        raise FileNotFoundError("no element sets in the history store for the benchmark's satellites")
    geometry = mean_orbit_geometry(build_satrecs(sets))
    sets = sets.assign(
        altitude_km=geometry["semi_major_axis_km"].to_numpy() - site_mod.EARTH_RADIUS_KM,
        _epoch_us=pd.to_datetime(sets["epoch"], utc=True).astype("int64") // 1000,
    )
    out["_epoch_us"] = epochs.astype("int64") // 1000
    lookup = sets.set_index(["norad_id", "_epoch_us"])["altitude_km"]
    idx = pd.MultiIndex.from_arrays([out["norad_id"].astype("int64"), out["_epoch_us"]])
    out["altitude_km"] = lookup.reindex(idx).to_numpy()
    missing = out["altitude_km"].isna()
    if missing.any():
        fill = out[~missing].groupby(["norad_id", "window"])["altitude_km"].median()
        for i in np.flatnonzero(missing.to_numpy()):
            k = (int(out.at[i, "norad_id"]), out.at[i, "window"])
            if k not in fill.index:
                raise ValueError(f"no altitude for trial {k} at {out.at[i, 'set_epoch']}: set not in the history store")
            out.at[i, "altitude_km"] = float(fill.loc[k])
    out["speed_km_s"] = np.sqrt(_MU_KM3_S2 / (out["altitude_km"] + site_mod.EARTH_RADIUS_KM))
    return out.drop(columns=["_epoch_us"])


def load_trials(
    parquet: Path = TRIALS_PARQUET, csv: Path = TRIALS_CSV, history_dir: Path = config.HISTORY_DIR
) -> tuple[pd.DataFrame, str]:
    """The usable trials with altitude attached, from the benchmark's parquet or the exported CSV.

    Returns the frame and where it came from. The parquet is the benchmark's own per-trial file
    (``driftwatch validate swarm``), local and not in the repository; the CSV is the copy this
    module exports beside its table so the table can be recomputed from the repository alone.
    """
    if Path(parquet).exists():
        trials = usable(pd.read_parquet(parquet))
        trials = attach_altitude(trials, history_dir=history_dir)
        return trials[TRIAL_COLUMNS].reset_index(drop=True), repo_relative(parquet)
    if Path(csv).exists():
        trials = pd.read_csv(csv, parse_dates=["set_epoch", "t"])
        return trials[TRIAL_COLUMNS].reset_index(drop=True), repo_relative(csv)
    raise FileNotFoundError(f"neither {parquet} nor {csv} exists; run `driftwatch validate swarm` first")


def repo_relative(path: Path) -> str:
    """A path as it is named on the pages: relative to the repository where it lies inside it."""
    try:
        return Path(path).resolve().relative_to(config.PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def export_trials(trials: pd.DataFrame, path: Path = TRIALS_CSV) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    trials[TRIAL_COLUMNS].to_csv(path, index=False, date_format="%Y-%m-%dT%H:%M:%S.%fZ")
    return path


# --------------------------------------------------------------------------------------
# Angles and the table


def with_angles(trials: pd.DataFrame) -> pd.DataFrame:
    """Add the zenith-range angular errors, ``cross_deg`` and ``along_deg``, and the along-track time shift."""
    out = trials.copy()
    out["cross_deg"] = angular_error_deg(out["cross_km"], out["altitude_km"])
    out["along_deg"] = angular_error_deg(out["in_track_km"], out["altitude_km"])
    out["along_shift_s"] = np.abs(out["in_track_km"].to_numpy()) / out["speed_km_s"].to_numpy()
    return out


def _p(x: pd.Series, q: float) -> float:
    return float(np.quantile(x.to_numpy(dtype=float), q)) if len(x) else float("nan")


def horizon_table(trials: pd.DataFrame, columns: Iterable[Column] | None = None) -> pd.DataFrame:
    """One row per window and lead: the angular residual distribution and the in-beam fractions per column."""
    cols = list(columns) if columns is not None else table_columns()
    t = with_angles(trials)
    rows: list[dict[str, Any]] = []
    for window in WINDOW_ORDER:
        w = t[t["window"] == window]
        for lead in sorted(w["lead_h"].unique()):
            g = w[w["lead_h"] == lead]
            row: dict[str, Any] = {
                "window": window,
                "lead_h": float(lead),
                "n": int(len(g)),
                "cross_median_arcmin": 60.0 * _p(g["cross_deg"], 0.5),
                "cross_p95_arcmin": 60.0 * _p(g["cross_deg"], 0.95),
                "along_median_arcmin": 60.0 * _p(g["along_deg"], 0.5),
                "along_p95_arcmin": 60.0 * _p(g["along_deg"], 0.95),
                "along_shift_median_s": _p(g["along_shift_s"], 0.5),
                "along_shift_p95_s": _p(g["along_shift_s"], 0.95),
            }
            cross = g["cross_deg"].to_numpy()
            along = g["along_deg"].to_numpy()
            for c in cols:
                limit = BEAM_FRACTION * c.fwhm_deg
                row[c.key] = float(np.mean(cross < limit)) if len(g) else float("nan")
                row[c.along_key] = float(np.mean(along < limit)) if len(g) else float("nan")
            rows.append(row)
    return pd.DataFrame(rows)


def horizon_hours(
    table: pd.DataFrame, column: Column, *, along: bool = False, coverage: float = COVERAGE
) -> dict[str, float | None]:
    """Per window, the longest lead through which every lead bin keeps the coverage; None if the first fails."""
    key = column.along_key if along else column.key
    out: dict[str, float | None] = {}
    for window in WINDOW_ORDER:
        w = table[table["window"] == window].sort_values("lead_h")
        last: float | None = None
        for _, r in w.iterrows():
            if r[key] >= coverage:
                last = float(r["lead_h"])
            else:
                break
        out[window] = last
    return out


def _fmt_lead(h: float | None) -> str:
    if h is None:
        return "under 6 h"
    return f"{h:g} h" if h < 48 else f"{h / 24:g} d"


def _fraction_block(table: pd.DataFrame, window: str, cols: list[Column], along: bool) -> list[str]:
    what = "along-track" if along else "cross-track"
    lines = [
        f"| Lead | n | {what} median | {what} p95 | " + " | ".join(c.label for c in cols) + " |",
        "| ---: | ---: | ---: | ---: | " + " | ".join("---:" for _ in cols) + " |",
    ]
    prefix = "along" if along else "cross"
    for _, r in table[table["window"] == window].iterrows():
        cells = [
            _fmt_lead(float(r["lead_h"])),
            str(int(r["n"])),
            f"{r[f'{prefix}_median_arcmin']:.1f}'",
            f"{r[f'{prefix}_p95_arcmin']:.1f}'",
        ] + [f"{100 * r[c.along_key if along else c.key]:.0f}%" for c in cols]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def to_markdown(
    table: pd.DataFrame, trials: pd.DataFrame, columns: Iterable[Column] | None = None, source: str = ""
) -> str:
    """The radio horizon page: population, beam widths, the table per window, and the horizon per receiver."""
    cols = list(columns) if columns is not None else table_columns()
    n_sets = trials.groupby("window")["set_epoch"].nunique()
    alt = trials.groupby("satellite")["altitude_km"].agg(["min", "max"])
    k = site_mod.beam_fwhm_lambda_over_d()
    sets_by_window = ", ".join(f"{int(n_sets.get(w, 0))} sets in the {WINDOW_SHORT[w]} window" for w in WINDOW_ORDER)
    altitudes = ", ".join(f"Swarm {s} at {r['min']:.0f} to {r['max']:.0f} km" for s, r in alt.iterrows())
    csv_rel = TRIALS_CSV.relative_to(config.PROJECT_ROOT).as_posix()
    lines = [
        "# The radio horizon: the benchmark's residuals as angles on the sky",
        "",
        "The calibration benchmark measured how far a public element set puts Swarm A, B and C from ESA's precise "
        "orbit at leads from six hours to seven days, in the satellite's radial, in-track, cross-track frame "
        "(`docs/calibration-benchmark.md`). Here each residual is the angle it subtends from the MeerKAT array "
        "centre with the satellite overhead: the residual divided by the altitude, which is the largest angle "
        "the residual can subtend from the site. Lower in the sky the same residual subtends less, by the ratio "
        "of altitude to range and by the projection onto the sky; the per-crossing figures in the period reports "
        "use the actual geometry. Cross-track error decides whether a beam crossing happens; along-track error "
        "shifts when it happens, and is given as a time shift at the orbital speed as well as an angle.",
        "",
        f"**Population and limits.** Three sun-synchronous satellites, {altitudes}; {sets_by_window}; one trial per "
        "element set per lead, manoeuvre arcs excluded from ESA's thruster record. A measured horizon is attached "
        "only to objects between 400 and 600 km; every other object carries *no measured horizon* and the reason. "
        "Nothing here describes a station-kept object's error through a burn. The beam width is measured at L-band "
        "and scaled by wavelength to UHF and S (below).",
        "",
        "## The beam",
        "",
        f"Half-power width from {site_mod.BEAM_SOURCE}: FWHM = {site_mod.BEAM_FWHM_ARCMIN_AT_1500_MHZ:g} arcmin x "
        f"(1500 MHz / f), which is {k:.2f} lambda/D for the 13.5 m dish. The threshold in the tables is a third of "
        "the width at the stated frequency.",
        "",
        "| Receiver | Digitised band (MHz) | FWHM at band centre | FWHM at band top "
        "| A third of the width, centre / top |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in dict.fromkeys(c.receiver for c in cols):
        r = RECEIVERS[name]
        fc, ft = beam_fwhm_deg(r.centre_mhz), beam_fwhm_deg(r.hi_mhz)
        lines.append(
            f"| {name} | {r.lo_mhz:g}-{r.hi_mhz:g} | {fc:.2f} deg ({60 * fc:.0f}') at {r.centre_mhz:g} MHz "
            f"| {ft:.2f} deg ({60 * ft:.0f}') at {r.hi_mhz:g} MHz | {60 * fc / 3:.0f}' / {60 * ft / 3:.0f}' |"
        )
    lines += [
        "",
        "## The table",
        "",
        "For each window and lead: the number of trials, the angular error overhead at the median and the 95th "
        "percentile (arcmin), and the fraction of trials whose angular error is under a third of the beam width, "
        "per receiver and frequency. The first block of each window is the cross-track error, which decides "
        "whether a crossing happens; the second is the along-track error, which decides when, and whose time "
        "shift at the orbital speed is in the last table.",
    ]
    for window in WINDOW_ORDER:
        if table[table["window"] == window].empty:
            continue
        lines += ["", f"### {WINDOW_LABELS[window]}", "", "Cross-track:", ""]
        lines += _fraction_block(table, window, cols, along=False)
        lines += ["", "Along-track:", ""]
        lines += _fraction_block(table, window, cols, along=True)
    lines += [
        "",
        "### The along-track error as a time shift",
        "",
        "The along-track residual divided by the orbital speed: how early or late the satellite is at a crossing, "
        "whatever the range.",
        "",
        "| Lead | " + " | ".join(f"{WINDOW_SHORT[w]} median / p95" for w in WINDOW_ORDER) + " |",
        "| ---: | " + " | ".join("---:" for _ in WINDOW_ORDER) + " |",
    ]
    for lead in sorted(table["lead_h"].unique()):
        cells = []
        for w in WINDOW_ORDER:
            r = table[(table["window"] == w) & (table["lead_h"] == lead)]
            if len(r):
                cells.append(f"{r['along_shift_median_s'].iloc[0]:.2f} s / {r['along_shift_p95_s'].iloc[0]:.2f} s")
            else:
                cells.append("-")
        lines.append(f"| {_fmt_lead(float(lead))} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## The horizon",
        "",
        f"The longest lead through which at least {100 * COVERAGE:.0f} per cent of trials keep their angular error "
        "under a third of the beam width, every shorter lead bin included. *Under 6 h* means the first lead bin "
        "already fails the coverage; *7 d* means no lead in the benchmark failed it.",
        "",
        "| Receiver, frequency | Error | " + " | ".join(WINDOW_SHORT[w] for w in WINDOW_ORDER) + " |",
        "| --- | --- | " + " | ".join("---" for _ in WINDOW_ORDER) + " |",
    ]
    for c in cols:
        for along in (False, True):
            h = horizon_hours(table, c, along=along)
            lines.append(
                f"| {c.label} (FWHM {c.fwhm_deg:.2f} deg) | {'along-track' if along else 'cross-track'} | "
                + " | ".join(_fmt_lead(h[w]) for w in WINDOW_ORDER)
                + " |"
            )
    lines += [
        "",
        "## What this does not show",
        "",
        "- The angles are for the satellite overhead, the worst case; a crossing at 30 degrees of elevation "
        "sees a residual at roughly twice the range and half the angle.",
        "- Three satellites in one orbit class, three windows, one week of sets each. Nothing here is measured "
        "for debris, for the GNSS or mobile-satellite orbits, for station-kept constellations, or for objects "
        "the network tracks less often, and every such object is labelled *no measured horizon* in the reports.",
        "- The beam width is a measurement at L-band scaled by wavelength; the holography paper reports the "
        "width proportional to lambda/D over most of each band, with departures at the top of each band.",
        "- The cross-track residual stays under half a kilometre at every lead in every window, so on this "
        "population the cross-track fraction is one everywhere and the along-track error is the number that "
        "moves. Whether a crossing predicted days ahead happens inside a given observation is an along-track "
        "question, of timing, before it is a cross-track question, of geometry.",
        "",
        f"Source of the trials: `{source}`; the usable trials are exported beside this page as `{csv_rel}` so the "
        "table recomputes from the repository.",
        "",
        f"_Last updated {datetime.now(UTC):%d %B %Y}._",
    ]
    return "\n".join(lines).rstrip() + "\n"


MEERKAT_RECORD: Mapping[str, Any] = {
    "name": site_mod.MEERKAT.name,
    "latitude_deg": site_mod.MEERKAT.latitude_deg,
    "longitude_deg": site_mod.MEERKAT.longitude_deg,
    "height_m": site_mod.MEERKAT.height_m,
    "dish_diameter_m": site_mod.MEERKAT.dish_diameter_m,
    "source": site_mod.MEERKAT.source,
}


def to_json(table: pd.DataFrame, columns: Iterable[Column] | None = None, source: str = "") -> dict[str, Any]:
    cols = list(columns) if columns is not None else table_columns()
    return {
        "built_at": datetime.now(UTC).isoformat(),
        "source_trials": source,
        "site": dict(MEERKAT_RECORD),
        "beam": {
            "fwhm_arcmin_at_1500_mhz": site_mod.BEAM_FWHM_ARCMIN_AT_1500_MHZ,
            "k_lambda_over_d": site_mod.beam_fwhm_lambda_over_d(),
            "source": site_mod.BEAM_SOURCE,
        },
        "geometry": "zenith range: residual / altitude, the largest angle the residual subtends from the site",
        "coverage": COVERAGE,
        "beam_fraction": BEAM_FRACTION,
        "columns": [
            {
                "receiver": c.receiver,
                "freq_mhz": c.freq_mhz,
                "fwhm_deg": c.fwhm_deg,
                "key": c.key,
                "along_key": c.along_key,
            }
            for c in cols
        ],
        "windows": {w: WINDOW_LABELS[w] for w in WINDOW_ORDER},
        "rows": json.loads(table.to_json(orient="records")),
        "horizon_hours": {
            "cross_track": {c.key: horizon_hours(table, c) for c in cols},
            "along_track": {c.key: horizon_hours(table, c, along=True) for c in cols},
        },
    }


# --------------------------------------------------------------------------------------
# Per-crossing use of the same trials


def lead_bin_hours(age_hours: float, leads: Iterable[float]) -> float | None:
    """The smallest benchmark lead at or beyond an element-set age, or None past the longest lead."""
    ls = np.asarray(sorted({float(x) for x in leads}))
    k = int(np.searchsorted(ls, float(age_hours), side="left"))
    return float(ls[k]) if k < len(ls) else None


@dataclass(frozen=True)
class CrossingUncertainty:
    """What the benchmark says about one crossing's geometry, at its element-set age and window."""

    window: str
    lead_h: float
    n_trials: int
    cross_p95_deg: float
    along_p95_deg: float
    along_shift_p95_s: float
    fraction_inside: float
    fraction_inside_along: float


def crossing_uncertainty(
    trials: pd.DataFrame,
    window: str,
    age_hours: float,
    range_km: float,
    projection_cross: float,
    projection_along: float,
    fwhm_deg: float,
) -> CrossingUncertainty | None:
    """Project the window's trials at the age's lead bin onto the crossing's line of sight.

    ``projection_cross`` and ``projection_along`` are the sky-projection factors of the object's
    cross-track and in-track unit vectors at closest approach (1 across the line of sight, 0
    along it), so the angle each trial's residual would subtend is ``residual x factor / range``.
    """
    lead = lead_bin_hours(age_hours, trials["lead_h"].unique())
    if lead is None:
        return None
    g = trials[(trials["window"] == window) & (trials["lead_h"] == lead)]
    if g.empty:
        return None
    cross = angular_error_deg(g["cross_km"].to_numpy() * projection_cross, range_km)
    along = angular_error_deg(g["in_track_km"].to_numpy() * projection_along, range_km)
    shift = np.abs(g["in_track_km"].to_numpy()) / g["speed_km_s"].to_numpy()
    limit = BEAM_FRACTION * fwhm_deg
    return CrossingUncertainty(
        window=window,
        lead_h=lead,
        n_trials=int(len(g)),
        cross_p95_deg=float(np.quantile(cross, 0.95)),
        along_p95_deg=float(np.quantile(along, 0.95)),
        along_shift_p95_s=float(np.quantile(shift, 0.95)),
        fraction_inside=float(np.mean(cross < limit)),
        fraction_inside_along=float(np.mean(along < limit)),
    )
