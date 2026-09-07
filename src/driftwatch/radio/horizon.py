"""The radio horizon: the benchmark's residuals as angles on the sky, by altitude band, lead and window.

The calibration benchmark (``storm/precise.py``, ``docs/calibration-benchmark.md``) and its
reference expansion (``storm/reference_run.py``, ``docs/reference-benchmark.md``) measured, for
every public element set issued in four windows, how far SGP4 put a spacecraft from its
reconstructed orbit at leads from six hours to seven days, in the satellite's radial, in-track,
cross-track frame, for fifteen spacecraft in five altitude bands from 460 to 1,338 km. The
benchmark's horizon was stated in kilometres along track, because a screening box is a box. A
dish's beam is an angle, and the two components matter differently: an along-track error moves
the satellite along its path, so it changes *when* a crossing happens; a cross-track error moves
the path sideways, so it decides *whether* the crossing happens at all.

This module converts each trial's residual into the angle it would subtend from the site and
computes, for each altitude band, lead bin and window, two named quantities. The **crossing
horizon** is governed by the cross-track error: the longest lead through which at least 95 per
cent of trials keep their cross-track angular error under a third of the beam's half-power width,
per receiver. It answers whether an object crossed the beam during an observation, with the
crossing's time known to the along-track time shift tabulated beside it. The **position horizon**
is governed by the along-track error: the same coverage applied to the along-track angular error.
It answers where an object is at an instant to within a third of the beam. The population an
object is scored against is its own altitude band's; an object outside every measured band, or
eccentric, or on a set older than the benchmark's leads, carries *no measured horizon*.

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
from driftwatch.storm import reference

REFERENCE_PARQUET = config.DATA_DIR / "validation" / "reference_benchmark.parquet"
SWARM_PARQUET = config.DATA_DIR / "validation" / "swarm_benchmark.parquet"
TRIALS_CSV = config.DATA_DIR / "radio" / "benchmark_trials.csv"

WINDOW_LABELS: dict[str, str] = {
    "quiet": "quiet week, 20 to 27 April 2024",
    "storm": "May 2024 storm, sets issued 6 to 13 May",
    "held-out": "October 2024 storm, sets issued 6 to 13 October (held out)",
    "august": "August 2024 storm, sets issued 8 to 15 August (held out)",
}
WINDOW_SHORT: dict[str, str] = {
    "quiet": "quiet",
    "storm": "May 2024",
    "held-out": "October 2024",
    "august": "August 2024",
}
WINDOW_ORDER = ("quiet", "storm", "held-out", "august")
BAND_ORDER: tuple[str, ...] = tuple(label for _, _, label in reference.ALTITUDE_BANDS)
MISSION_NAMES: dict[str, str] = {k: m.name for k, m in reference.MISSIONS.items()}

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
    "mission",
    "satellite",
    "norad_id",
    "altitude_band",
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
    def crossing_key(self) -> str:
        """The table column for the crossing horizon's test: the cross-track fraction inside a third of the beam."""
        return f"crossing:{self.key}"

    @property
    def position_key(self) -> str:
        """The table column for the position horizon's test: the along-track fraction inside a third of the beam."""
        return f"position:{self.key}"

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


def _speed(trials: pd.DataFrame) -> pd.DataFrame:
    out = trials.copy()
    out["speed_km_s"] = np.sqrt(_MU_KM3_S2 / (out["altitude_km"].to_numpy(dtype=float) + site_mod.EARTH_RADIUS_KM))
    return out


def load_trials(
    reference_parquet: Path = REFERENCE_PARQUET,
    swarm_parquet: Path = SWARM_PARQUET,
    csv: Path = TRIALS_CSV,
    history_dir: Path = config.HISTORY_DIR,
) -> tuple[pd.DataFrame, str]:
    """The usable trials with altitude, speed and band attached, and where they came from.

    The reference benchmark's per-trial file (``driftwatch validate reference``) is preferred;
    the Swarm benchmark's file is the fallback, labelled by band; and the CSV exported beside the
    page is the copy that lets the table be recomputed from the repository alone.
    """
    if Path(reference_parquet).exists():
        trials = usable(pd.read_parquet(reference_parquet))
        trials = _speed(trials)
        return trials[TRIAL_COLUMNS].reset_index(drop=True), repo_relative(reference_parquet)
    if Path(swarm_parquet).exists():
        trials = usable(pd.read_parquet(swarm_parquet))
        trials = attach_altitude(trials, history_dir=history_dir)
        trials["mission"] = "swarm-" + trials["satellite"].astype(str).str.lower()
        trials["altitude_band"] = [reference.altitude_band_label(float(a)) for a in trials["altitude_km"]]
        return trials[TRIAL_COLUMNS].reset_index(drop=True), repo_relative(swarm_parquet)
    if Path(csv).exists():
        trials = pd.read_csv(csv, parse_dates=["set_epoch", "t"])
        return trials[TRIAL_COLUMNS].reset_index(drop=True), repo_relative(csv)
    raise FileNotFoundError(
        f"none of {reference_parquet}, {swarm_parquet} or {csv} exists; run `driftwatch validate reference` first"
    )


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


def windows_present(frame: pd.DataFrame) -> list[str]:
    """The benchmark windows the frame holds, in the fixed order."""
    have = set(frame["window"].unique()) if "window" in frame else set()
    return [w for w in WINDOW_ORDER if w in have]


def bands_present(frame: pd.DataFrame) -> list[str]:
    """The altitude bands the frame holds, lowest first: ``band`` in a horizon table, ``altitude_band`` in trials."""
    col = "band" if "band" in frame else "altitude_band"
    have = set(frame[col].unique()) if col in frame else set()
    return [b for b in BAND_ORDER if b in have]


def band_of(altitude_km: float) -> str | None:
    """The altitude band an object's mean altitude falls in, or None outside every band."""
    label = reference.altitude_band_label(float(altitude_km))
    return label if label in BAND_ORDER else None


def band_populations(trials: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Per band: the spacecraft, the sets per window and the altitude range, from the trials themselves."""
    out: dict[str, dict[str, Any]] = {}
    for band in bands_present(trials):
        b = trials[trials["altitude_band"] == band]
        names = sorted({MISSION_NAMES.get(str(m), str(m)) for m in b["mission"].unique()})
        out[band] = {
            "spacecraft": names,
            "n_sets": {w: int(b[b["window"] == w]["set_epoch"].nunique()) for w in windows_present(b)},
            "altitude_min_km": float(b["altitude_km"].min()),
            "altitude_max_km": float(b["altitude_km"].max()),
        }
    return out


def population_sentence(trials: pd.DataFrame) -> str:
    """The measured population as one sentence: every band, its spacecraft, its sets and its altitudes."""
    parts = []
    for band, p in band_populations(trials).items():
        sets = ", ".join(f"{n} {WINDOW_SHORT[w]}" for w, n in p["n_sets"].items())
        parts.append(
            f"{band} ({p['altitude_min_km']:.0f} to {p['altitude_max_km']:.0f} km): "
            f"{', '.join(p['spacecraft'])}; sets {sets}"
        )
    return "; ".join(parts) if parts else "no measured population"


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
    """One row per band, window and lead: the angular residual distribution and, per column, the cross-track and
    along-track fractions inside a third of the beam (the crossing and position horizons' tests)."""
    cols = list(columns) if columns is not None else table_columns()
    t = with_angles(trials)
    if "altitude_band" not in t:
        t["altitude_band"] = [reference.altitude_band_label(float(a)) for a in t["altitude_km"]]
    rows: list[dict[str, Any]] = []
    for band in bands_present(t):
        tb = t[t["altitude_band"] == band]
        for window in windows_present(tb):
            w = tb[tb["window"] == window]
            for lead in sorted(w["lead_h"].unique()):
                g = w[w["lead_h"] == lead]
                row: dict[str, Any] = {
                    "band": band,
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
                    row[c.crossing_key] = float(np.mean(cross < limit)) if len(g) else float("nan")
                    row[c.position_key] = float(np.mean(along < limit)) if len(g) else float("nan")
                rows.append(row)
    return pd.DataFrame(rows)


HORIZONS = ("crossing", "position")


def _select(table: pd.DataFrame, band: str | None) -> pd.DataFrame:
    if band is None:
        return table
    return table[table["band"] == band]


def horizon_hours(
    table: pd.DataFrame,
    column: Column,
    *,
    which: str = "crossing",
    coverage: float = COVERAGE,
    band: str | None = None,
) -> dict[str, float | None]:
    """Per window present, the longest lead through which every lead bin keeps the coverage; None if the first fails.

    ``which`` is ``"crossing"`` for the crossing horizon (the cross-track test: whether an object
    crossed the beam) or ``"position"`` for the position horizon (the along-track test: where the
    object is at an instant). ``band`` selects one altitude band; a table with a ``band`` column
    and no band asked for must hold one band only.
    """
    if which not in HORIZONS:
        raise ValueError(f"which must be one of {HORIZONS}, not {which!r}")
    t = _select(table, band)
    if "band" in t and t["band"].nunique() > 1:
        raise ValueError("the table holds several altitude bands; say which")
    key = column.crossing_key if which == "crossing" else column.position_key
    out: dict[str, float | None] = {}
    for window in windows_present(t):
        w = t[t["window"] == window].sort_values("lead_h")
        last: float | None = None
        for _, r in w.iterrows():
            if r[key] >= coverage:
                last = float(r["lead_h"])
            else:
                break
        out[window] = last
    return out


def crossing_horizon_hours(
    table: pd.DataFrame, column: Column, *, coverage: float = COVERAGE, band: str | None = None
) -> dict[str, float | None]:
    """The crossing horizon per window: the cross-track test (see :func:`horizon_hours`)."""
    return horizon_hours(table, column, which="crossing", coverage=coverage, band=band)


def position_horizon_hours(
    table: pd.DataFrame, column: Column, *, coverage: float = COVERAGE, band: str | None = None
) -> dict[str, float | None]:
    """The position horizon per window: the along-track test (see :func:`horizon_hours`)."""
    return horizon_hours(table, column, which="position", coverage=coverage, band=band)


def horizons(
    table: pd.DataFrame, columns: Iterable[Column] | None = None
) -> dict[str, dict[str, dict[str, dict[str, float | None]]]]:
    """``{"crossing": {band: {column key: {window: hours}}}, "position": {...}}`` for every band and column."""
    cols = list(columns) if columns is not None else table_columns()
    return {
        which: {b: {c.key: horizon_hours(table, c, which=which, band=b) for c in cols} for b in bands_present(table)}
        for which in HORIZONS
    }


def format_lead(h: float | None) -> str:
    """A horizon in hours as the pages print it: ``under 6 h`` when the first lead bin already fails."""
    if h is None:
        return "under 6 h"
    return f"{h:g} h" if h < 48 else f"{h / 24:g} d"


_fmt_lead = format_lead


def _fraction_block(table: pd.DataFrame, band: str, window: str, cols: list[Column], which: str) -> list[str]:
    what = "along-track" if which == "position" else "cross-track"
    lines = [
        f"| Lead | n | {what} median | {what} p95 | " + " | ".join(c.label for c in cols) + " |",
        "| ---: | ---: | ---: | ---: | " + " | ".join("---:" for _ in cols) + " |",
    ]
    prefix = "along" if which == "position" else "cross"
    rows = table[(table["band"] == band) & (table["window"] == window)]
    for _, r in rows.iterrows():
        cells = [
            _fmt_lead(float(r["lead_h"])),
            str(int(r["n"])),
            f"{r[f'{prefix}_median_arcmin']:.1f}'",
            f"{r[f'{prefix}_p95_arcmin']:.1f}'",
        ] + [f"{100 * r[c.position_key if which == 'position' else c.crossing_key]:.0f}%" for c in cols]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _compact_block(table: pd.DataFrame, band: str, windows: list[str]) -> list[str]:
    """Per lead, per window: the 95th-percentile cross-track and along-track angles overhead and the time shift."""
    lines = [
        "| Lead | " + " | ".join(f"{WINDOW_SHORT[w]}: n, cross p95, along p95, shift p95" for w in windows) + " |",
        "| ---: | " + " | ".join("---" for _ in windows) + " |",
    ]
    tb = table[table["band"] == band]
    for lead in sorted(tb["lead_h"].unique()):
        cells = []
        for w in windows:
            r = tb[(tb["window"] == w) & (tb["lead_h"] == lead)]
            if len(r):
                x = r.iloc[0]
                cells.append(
                    f"{int(x['n'])}, {x['cross_p95_arcmin']:.1f}', {x['along_p95_arcmin']:.1f}', "
                    f"{x['along_shift_p95_s']:.2f} s"
                )
            else:
                cells.append("-")
        lines.append(f"| {format_lead(float(lead))} | " + " | ".join(cells) + " |")
    return lines


def horizon_statements(
    table: pd.DataFrame, columns: Iterable[Column] | None = None, band: str | None = None
) -> list[str]:
    """The plain statements the two horizons support on one band's table, computed from it and nothing else."""
    cols = list(columns) if columns is not None else table_columns()
    t = _select(table, band)
    windows = windows_present(t)
    if not windows or not cols:
        return []
    longest = float(t["lead_h"].max())
    crossing = {c.key: horizon_hours(t, c, which="crossing") for c in cols}
    position = {c.key: horizon_hours(t, c, which="position") for c in cols}
    where = f" at {band}" if band else ""
    out: list[str] = []
    short = [
        f"{c.label} in the {WINDOW_SHORT[w]} window ({format_lead(crossing[c.key][w])})"
        for c in cols
        for w in windows
        if crossing[c.key][w] != longest
    ]
    if not short:
        out.append(
            f"**The crossing horizon{where} holds for the full {format_lead(longest)} in every window** for the "
            "measured population, at every receiver and frequency in the table: whether an object crossed the beam "
            "during an observation is answered through the benchmark's longest lead, and the time of the crossing "
            "is known to the along-track shift tabulated above."
        )
    else:
        out.append(
            f"**The crossing horizon{where}** falls short of the benchmark's longest lead for " + "; ".join(short) + "."
        )
    l_centre = next((c for c in cols if c.receiver == "L" and c.freq_mhz == RECEIVERS["L"].centre_mhz), None)
    if l_centre is not None:
        out.append(
            f"**The position horizon{where} at the L-band centre is "
            + ", ".join(f"{format_lead(position[l_centre.key][w])} in the {WINDOW_SHORT[w]} window" for w in windows)
            + "**: where an object is at an instant, to within a third of the beam, is answered only that far ahead."
        )
    s_cols = [c for c in cols if c.receiver.startswith("S")]
    if s_cols:
        top = max(s_cols, key=lambda c: c.freq_mhz)
        top_none = all(position[top.key][w] is None for w in windows)
        if top_none:
            lead_in = (
                f"**S-band position prediction from public element sets{where} is not possible at any element-set "
                f"age**: at the top of the band ({top.label}) the position horizon is {format_lead(None)} in every "
                "window, the benchmark's shortest lead"
            )
        else:
            lead_in = (
                f"**S-band position prediction from public element sets{where}** at the top of the band ({top.label}) "
                "holds "
                + ", ".join(f"{format_lead(position[top.key][w])} in the {WINDOW_SHORT[w]} window" for w in windows)
            )
        for c in s_cols:
            if c is top:
                continue
            lead_in += f"; at {c.label} the position horizon is " + ", ".join(
                f"{format_lead(position[c.key][w])} ({WINDOW_SHORT[w]})" for w in windows
            )
        out.append(lead_in + ".")
    return out


def population_table_lines(trials: pd.DataFrame) -> list[str]:
    """The population as a markdown table: band, spacecraft, altitude range, sets per window."""
    windows = windows_present(trials)
    lines = [
        "| Altitude band | Spacecraft | Mean altitude of the sets | "
        + " | ".join(f"Sets, {WINDOW_SHORT[w]}" for w in windows)
        + " |",
        "| --- | --- | --- | " + " | ".join("---:" for _ in windows) + " |",
    ]
    for band, p in band_populations(trials).items():
        lines.append(
            f"| {band} | {', '.join(p['spacecraft'])} | {p['altitude_min_km']:.0f} to {p['altitude_max_km']:.0f} km | "
            + " | ".join(str(p["n_sets"].get(w, 0)) for w in windows)
            + " |"
        )
    return lines


def to_markdown(
    table: pd.DataFrame, trials: pd.DataFrame, columns: Iterable[Column] | None = None, source: str = ""
) -> str:
    """The radio horizon page: population by band, beam widths, the tables, the two horizons per band and receiver."""
    cols = list(columns) if columns is not None else table_columns()
    windows = windows_present(table)
    bands = bands_present(table)
    k = site_mod.beam_fwhm_lambda_over_d()
    csv_rel = TRIALS_CSV.relative_to(config.PROJECT_ROOT).as_posix()
    lines = [
        "# The radio horizon: the benchmark's residuals as angles on the sky",
        "",
        "The reference benchmark measured how far a public element set puts a spacecraft from its reconstructed "
        "orbit at leads from six hours to seven days, in the satellite's radial, in-track, cross-track frame, for "
        "fifteen spacecraft in five altitude bands (`docs/reference-benchmark.md`, which extends "
        "`docs/calibration-benchmark.md`). Here each residual is the angle it subtends from the MeerKAT array "
        "centre with the satellite overhead: the residual divided by the altitude, which is the largest angle "
        "the residual can subtend from the site. Lower in the sky the same residual subtends less, by the ratio "
        "of altitude to range and by the projection onto the sky; the per-crossing figures in the period reports "
        "use the actual geometry.",
        "",
        "Two horizons are reported, and they answer different questions. The **crossing horizon** is governed by "
        "the cross-track error, which moves an object's path sideways: it is the longest lead through which the "
        "cross-track angular error stays under a third of the beam width for 95 per cent of trials, and it answers "
        "whether an object crossed the beam during an observation, with the crossing's time known to the "
        "along-track time shift tabulated below. The **position horizon** is governed by the along-track error, "
        "which moves the object along its path: the same coverage applied to the along-track angular error, and "
        "it answers where an object is at an instant to within a third of the beam. Both are computed per "
        "altitude band, and an object is scored against its own band's trials.",
        "",
        "## The measured population",
        "",
        "One trial per element set per lead; manoeuvre arcs excluded from a published thruster record (Swarm, "
        "GRACE-FO) and from detection on the reconstructed orbit otherwise; near-circular, free-flying between "
        "manoeuvres. A measured horizon is attached only to an object whose mean altitude falls in one of these "
        "bands, with an eccentricity under 0.02 and an element set no older than the benchmark's seven days; "
        "every other object carries *no measured horizon* and the reason. Nothing here describes a station-kept "
        "object's error through a burn, debris, or an eccentric orbit. The beam width is measured at L-band and "
        "scaled by wavelength to UHF and S (below).",
        "",
        *population_table_lines(trials),
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
        "## The two horizons, by band and receiver",
        "",
        f"Each is the longest lead through which at least {100 * COVERAGE:.0f} per cent of a band's trials keep the "
        "named angular error under a third of the beam width, every shorter lead bin included. *Under 6 h* means "
        "the first lead bin already fails the coverage; *7 d* means no lead in the benchmark failed it.",
        "",
        "- **Crossing horizon**, governed by the cross-track error: whether an object crossed the beam during an "
        "observation. The time of the crossing is known to the along-track shift in the tables below.",
        "- **Position horizon**, governed by the along-track error: where an object is at an instant, to within a "
        "third of the beam.",
        "",
        "| Band | Receiver, frequency | "
        + " | ".join(f"Crossing, {WINDOW_SHORT[w]}" for w in windows)
        + " | "
        + " | ".join(f"Position, {WINDOW_SHORT[w]}" for w in windows)
        + " |",
        "| --- | --- | " + " | ".join("---" for _ in range(2 * len(windows))) + " |",
    ]
    for band in bands:
        for c in cols:
            crossing = horizon_hours(table, c, which="crossing", band=band)
            position = horizon_hours(table, c, which="position", band=band)
            lines.append(
                f"| {band} | {c.label} (FWHM {c.fwhm_deg:.2f} deg) | "
                + " | ".join(format_lead(crossing.get(w)) if w in crossing else "-" for w in windows)
                + " | "
                + " | ".join(format_lead(position.get(w)) if w in position else "-" for w in windows)
                + " |"
            )
    for band in bands:
        for statement in horizon_statements(table, cols, band=band):
            lines += ["", statement]
    lines += [
        "",
        "## The tables",
        "",
        "For the lowest band, the band the lane began with, every window in full: the number of trials, the "
        "angular error overhead at the median and the 95th percentile (arcmin), and the fraction of trials whose "
        "angular error is under a third of the beam width per receiver and frequency; the first block is the "
        "cross-track error, the crossing horizon's test, the second the along-track error, the position horizon's "
        "test. For the other bands, the 95th percentiles and the along-track time shift per lead and window; their "
        "per-receiver fractions are in the JSON beside this page.",
    ]
    for band in bands:
        lines += ["", f"### {band}"]
        if band == bands[0]:
            for window in windows_present(table[table["band"] == band]):
                lines += ["", f"#### {WINDOW_LABELS[window]}", "", "Cross-track (the crossing horizon's test):", ""]
                lines += _fraction_block(table, band, window, cols, "crossing")
                lines += ["", "Along-track (the position horizon's test):", ""]
                lines += _fraction_block(table, band, window, cols, "position")
        else:
            lines += [""]
            lines += _compact_block(table, band, windows_present(table[table["band"] == band]))
    lines += [
        "",
        "### The along-track error as a time shift, lowest band",
        "",
        "The along-track residual divided by the orbital speed: how early or late the satellite is at a crossing, "
        "whatever the range. This is the timing figure the crossing horizon carries with it; the other bands' "
        "figures are in their tables above.",
        "",
        "| Lead | " + " | ".join(f"{WINDOW_SHORT[w]} median / p95" for w in windows) + " |",
        "| ---: | " + " | ".join("---:" for _ in windows) + " |",
    ]
    first = table[table["band"] == bands[0]] if bands else table
    for lead in sorted(first["lead_h"].unique()):
        cells = []
        for w in windows:
            r = first[(first["window"] == w) & (first["lead_h"] == lead)]
            if len(r):
                cells.append(f"{r['along_shift_median_s'].iloc[0]:.2f} s / {r['along_shift_p95_s'].iloc[0]:.2f} s")
            else:
                cells.append("-")
        lines.append(f"| {format_lead(float(lead))} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## What this does not show",
        "",
        "- The angles are for the satellite overhead, the worst case; a crossing at 30 degrees of elevation "
        "sees a residual at roughly twice the range and half the angle.",
        "- Fifteen spacecraft in five bands, four windows, one week of sets each. Nothing here is measured "
        "for debris, for the GNSS or mobile-satellite orbits, for station-kept constellations, for eccentric "
        "orbits, or for objects the network tracks less often, and every such object is labelled *no measured "
        "horizon* in the reports.",
        "- The beam width is a measurement at L-band scaled by wavelength; the holography paper reports the "
        "width proportional to lambda/D over most of each band, with departures at the top of each band.",
        "- In the lowest band the cross-track residual stays under half a kilometre at every lead in every "
        "window, so the crossing horizon is the benchmark's full seven days and the position horizon is the "
        "number that moves. Whether a crossing predicted days ahead happens inside a given observation is a "
        "position question, of timing, before it is a crossing question, of geometry.",
        "",
        f"Source of the trials: `{source}`; the usable trials are exported beside this page as `{csv_rel}` so the "
        "tables recompute from the repository.",
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


def to_json(
    table: pd.DataFrame, columns: Iterable[Column] | None = None, source: str = "", trials: pd.DataFrame | None = None
) -> dict[str, Any]:
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
                "crossing_key": c.crossing_key,
                "position_key": c.position_key,
            }
            for c in cols
        ],
        "windows": {w: WINDOW_LABELS[w] for w in windows_present(table)},
        "bands": bands_present(table),
        "population": band_populations(trials) if trials is not None else None,
        "rows": json.loads(table.to_json(orient="records")),
        "definitions": {
            "crossing_horizon": "governed by the cross-track error: the longest lead through which at least "
            "`coverage` of a band's trials keep their cross-track angular error under `beam_fraction` of the "
            "half-power width; whether an object crossed the beam during an observation, its time known to "
            "along_shift_p95_s",
            "position_horizon": "governed by the along-track error: the same coverage applied to the along-track "
            "angular error; where an object is at an instant to within `beam_fraction` of the beam",
        },
        "crossing_horizon_hours": horizons(table, cols)["crossing"],
        "position_horizon_hours": horizons(table, cols)["position"],
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
    """What the benchmark says about one crossing's geometry, at its element-set age, window and band."""

    window: str
    lead_h: float
    n_trials: int
    cross_p95_deg: float
    along_p95_deg: float
    along_shift_p95_s: float
    crossing_fraction_inside: float  # the crossing horizon's test at this age and geometry
    position_fraction_inside: float  # the position horizon's test
    band: str | None = None


def crossing_uncertainty(
    trials: pd.DataFrame,
    window: str,
    age_hours: float,
    range_km: float,
    projection_cross: float,
    projection_along: float,
    fwhm_deg: float,
    band: str | None = None,
) -> CrossingUncertainty | None:
    """Project the window's trials of one band at the age's lead bin onto the crossing's line of sight.

    ``projection_cross`` and ``projection_along`` are the sky-projection factors of the object's
    cross-track and in-track unit vectors at closest approach (1 across the line of sight, 0
    along it), so the angle each trial's residual would subtend is ``residual x factor / range``.
    """
    lead = lead_bin_hours(age_hours, trials["lead_h"].unique())
    if lead is None:
        return None
    g = trials[(trials["window"] == window) & (trials["lead_h"] == lead)]
    if band is not None and "altitude_band" in g:
        g = g[g["altitude_band"] == band]
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
        crossing_fraction_inside=float(np.mean(cross < limit)),
        position_fraction_inside=float(np.mean(along < limit)),
        band=band,
    )
