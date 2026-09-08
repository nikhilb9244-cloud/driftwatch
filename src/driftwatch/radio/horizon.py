"""Orbital-component angular scales from the stored reference residuals.

The original crossing/position horizon interpretation is withdrawn. arctan2(|C|,h)
and arctan2(|I|,h) are separate component diagnostics at a representative mean-altitude
range. Neither is a full sky-position error, a sky-track displacement, nor a beam
entry or timing guarantee. Actual comparison must propagate both complete orbits
past a rotating observer and minimise their separation from a stated boresight.

The analytic beam scale is retained solely for reproducibility of the historical
component table. Measured Jones patterns are required by the corrected comparison.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from driftwatch import config
from driftwatch.catalogue import history
from driftwatch.orbit.propagator import build_satrecs, mean_orbit_geometry
from driftwatch.radio import site as site_mod
from driftwatch.radio.site import RECEIVERS, Receiver, angular_error_deg, beam_fwhm_deg
from driftwatch.storm import reference

REFERENCE_PARQUET = config.DATA_DIR / "validation" / "reference_benchmark.parquet"
SWARM_PARQUET = config.DATA_DIR / "validation" / "swarm_benchmark.parquet"
TRIALS_CSV = config.DATA_DIR / "radio" / "benchmark_trials.csv"
MEASURED_PROVENANCE_JSON = config.DATA_DIR / "radio" / "measured-beam-provenance.json"

WINDOW_LABELS: dict[str, str] = {
    "quiet": "quiet week, 20 to 27 April 2024",
    "storm": "May 2024 storm, element epochs 6 to 13 May",
    "held-out": "October 2024 storm, element epochs 6 to 13 October (held out)",
    "august": "August 2024 storm, element epochs 8 to 15 August (held out)",
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
    ("S4", RECEIVERS["S4"].centre_mhz),
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
    beam_model: str = "historical analytic L-band relation or labelled extrapolation"
    beam_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.receiver}@{self.freq_mhz:.12g}"

    @property
    def cross_track_key(self) -> str:
        """The cross-track component fraction below the stated beam-width fraction."""
        return f"cross_track:{self.key}"

    @property
    def in_track_key(self) -> str:
        """The in-track component fraction below the stated beam-width fraction."""
        return f"in_track:{self.key}"

    @property
    def label(self) -> str:
        return f"{self.receiver} {self.freq_mhz:.9g} MHz"


def table_columns(frequencies: Iterable[tuple[str, float]] = TABLE_FREQUENCIES) -> list[Column]:
    """Declared scalar widths, requiring measured Jones-derived widths above 3 GHz."""
    return [receiver_column(RECEIVERS[name], float(f)) for name, f in frequencies]


def receiver_column(rx: Receiver, freq_mhz: float | None = None) -> Column:
    f = float(freq_mhz) if freq_mhz is not None else rx.centre_mhz
    if f > 3000:
        records = json.loads(MEASURED_PROVENANCE_JSON.read_text(encoding="utf-8"))["beams"]
        selected = next(
            (r for r in records if min(abs(r["requested_frequency_mhz"] - f), abs(r["frequency_mhz"] - f)) < 1e-6), None
        )
        if selected is None or "derived_half_power_widths" not in selected:
            raise ValueError(f"no recorded measured Jones width for {f:g} MHz; an analytic fallback is not permitted")
        widths = selected["derived_half_power_widths"]
        return Column(
            rx.name,
            float(selected["frequency_mhz"]),
            widths["minimum_diametric_width_deg"],
            "measured Jones half-power contour: minimum sampled diametric width through its sampled peak",
            {
                "doi": selected["doi"],
                "source_url": selected["source_url"],
                "requested_frequency_mhz": f,
                "cache_sha256": selected["cache_sha256"],
                "measurement_conditions": selected["measurement_conditions"],
                **widths,
            },
        )
    return Column(rx.name, f, beam_fwhm_deg(f))


def measured_half_power_widths(beam: site_mod.MeasuredBeam, *, angle_step_deg: float = 0.5) -> dict[str, Any]:
    """Widths of actual measured 0.5-power cuts, without fitting a circular or elliptical model.

    Sample diametric cuts in the source's angular coordinate plane through the
    highest measured pixel, over orientations [0,180). Both first half-power roots
    are found along each cut. Their sum defines its width. This is a declared
    scalar convention, not a substitute for the two-dimensional crossing test.
    """
    if not 0 < angle_step_deg <= 5:
        raise ValueError("orientation step must be in (0, 5] degrees")
    iy, ix = np.unravel_index(np.argmax(beam.power_yx), beam.power_yx.shape)
    peak_x, peak_y = float(beam.margin_deg[ix]), -float(beam.margin_deg[iy])
    radii = np.linspace(0, 2 * float(np.max(np.abs(beam.margin_deg))), 1025)
    angles = np.arange(0, 180, angle_step_deg)
    widths = []
    for angle in angles:
        direction = np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
        roots = []
        for sign in (-1, 1):
            x, y = np.array([peak_x, peak_y])[:, None] + sign * direction[:, None] * radii
            response = beam.power(x, y) - 0.5
            outside = np.flatnonzero(response <= 0)
            if not len(outside) or outside[0] == 0:
                raise ValueError("measured half-power contour is incomplete around the sampled peak")
            k = int(outside[0])
            roots.append(
                brentq(
                    lambda radius, sign=sign, direction=direction: (
                        float(beam.power(peak_x + sign * direction[0] * radius, peak_y + sign * direction[1] * radius))
                        - 0.5
                    ),
                    radii[k - 1],
                    radii[k],
                    xtol=1e-10,
                )
            )
        widths.append(sum(roots))
    return {
        "method_version": "measured_jones_peak_diametric_cuts_v1",
        "response": "unpolarised Stokes I = 0.5 sum |Jones|^2, normalised to sampled image peak",
        "peak_horizontal_deg": peak_x,
        "peak_vertical_deg": peak_y,
        "orientation_step_deg": angle_step_deg,
        "orientation_count": len(angles),
        "minimum_diametric_width_deg": float(np.min(widths)),
        "maximum_diametric_width_deg": float(np.max(widths)),
        "minimum_width_orientation_deg": float(angles[int(np.argmin(widths))]),
        "maximum_width_orientation_deg": float(angles[int(np.argmax(widths))]),
        "coordinate_convention": "straight cuts in measured horizontal/vertical angular plane through the sampled peak",
    }


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
    """Add component angles at mean-altitude range and the orbital phase-time scale |I|/v."""
    out = trials.copy()
    out["cross_deg"] = angular_error_deg(out["cross_km"], out["altitude_km"])
    out["along_deg"] = angular_error_deg(out["in_track_km"], out["altitude_km"])
    out["along_shift_s"] = np.abs(out["in_track_km"].to_numpy()) / out["speed_km_s"].to_numpy()
    return out


def _p(x: pd.Series, q: float) -> float:
    return float(np.quantile(x.to_numpy(dtype=float), q)) if len(x) else float("nan")


def horizon_table(
    trials: pd.DataFrame, columns: Iterable[Column] | None = None, *, beam_fraction: float = BEAM_FRACTION
) -> pd.DataFrame:
    """One row per band, window and lead: the angular residual distribution and, per column, the cross-track and
    along-track fractions inside a third of the beam (separate component tests)."""
    if not 0 < beam_fraction <= 1:
        raise ValueError("beam_fraction must be in (0, 1]")
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
                    limit = beam_fraction * c.fwhm_deg
                    row[c.cross_track_key] = float(np.mean(cross < limit)) if len(g) else float("nan")
                    row[c.in_track_key] = float(np.mean(along < limit)) if len(g) else float("nan")
                rows.append(row)
    return pd.DataFrame(rows)


COMPONENTS = ("cross_track", "in_track")


def _select(table: pd.DataFrame, band: str | None) -> pd.DataFrame:
    if band is None:
        return table
    return table[table["band"] == band]


def threshold_hours(
    table: pd.DataFrame,
    column: Column,
    *,
    which: str = "cross_track",
    coverage: float = COVERAGE,
    band: str | None = None,
) -> dict[str, float | None]:
    """Last consecutively passing sampled lead for one component and altitude band.

    This returns no continuous-time validity claim. Use threshold_status to distinguish
    failure from exhausted observations. No result is inferred below the first lead.
    """
    if which not in COMPONENTS:
        raise ValueError(f"which must be one of {COMPONENTS}, not {which!r}")
    t = _select(table, band)
    if "band" in t and t["band"].nunique() > 1:
        raise ValueError("the table holds several altitude bands; say which")
    key = column.cross_track_key if which == "cross_track" else column.in_track_key
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


def cross_track_threshold_hours(
    table: pd.DataFrame, column: Column, *, coverage: float = COVERAGE, band: str | None = None
) -> dict[str, float | None]:
    """Last consecutively passing sampled cross-track component lead."""
    return threshold_hours(table, column, which="cross_track", coverage=coverage, band=band)


def in_track_threshold_hours(
    table: pd.DataFrame, column: Column, *, coverage: float = COVERAGE, band: str | None = None
) -> dict[str, float | None]:
    """Last consecutively passing sampled in-track component lead."""
    return threshold_hours(table, column, which="in_track", coverage=coverage, band=band)


def component_thresholds(
    table: pd.DataFrame, columns: Iterable[Column] | None = None
) -> dict[str, dict[str, dict[str, dict[str, float | None]]]]:
    """``{"cross_track": {band: {column key: {window: hours}}}, "in_track": {...}}`` for every band and column."""
    cols = list(columns) if columns is not None else table_columns()
    return {
        which: {b: {c.key: threshold_hours(table, c, which=which, band=b) for c in cols} for b in bands_present(table)}
        for which in COMPONENTS
    }


def format_lead(h: float | None) -> str:
    """Format a measured lead; None means no sampled lead passed, not an inferred cutoff."""
    if h is None:
        return "no sampled lead passed"
    return f"{h:g} h" if h < 48 else f"{h / 24:g} d"


_fmt_lead = format_lead


def _fraction_block(table: pd.DataFrame, band: str, window: str, cols: list[Column], which: str) -> list[str]:
    what = "along-track" if which == "in_track" else "cross-track"
    lines = [
        f"| Lead | n | {what} median | {what} p95 | " + " | ".join(c.label for c in cols) + " |",
        "| ---: | ---: | ---: | ---: | " + " | ".join("---:" for _ in cols) + " |",
    ]
    prefix = "along" if which == "in_track" else "cross"
    rows = table[(table["band"] == band) & (table["window"] == window)]
    for _, r in rows.iterrows():
        cells = [
            _fmt_lead(float(r["lead_h"])),
            str(int(r["n"])),
            f"{r[f'{prefix}_median_arcmin']:.1f}'",
            f"{r[f'{prefix}_p95_arcmin']:.1f}'",
        ] + [f"{100 * r[c.in_track_key if which == 'in_track' else c.cross_track_key]:.0f}%" for c in cols]
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


def threshold_status(
    table: pd.DataFrame,
    column: Column,
    *,
    which: str = "cross_track",
    coverage: float = COVERAGE,
    band: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Report failure separately from exhaustion of the available sampled leads."""
    passed = threshold_hours(table, column, which=which, coverage=coverage, band=band)
    t = _select(table, band)
    key = column.cross_track_key if which == "cross_track" else column.in_track_key
    result = {}
    for window, last in passed.items():
        w = t[t["window"] == window].sort_values("lead_h")
        failed = w[w[key] < coverage]
        first_failed = float(failed.iloc[0]["lead_h"]) if len(failed) else None
        result[window] = {
            "passed_through_sampled_h": last,
            "first_failed_sampled_h": first_failed,
            "first_available_h": float(w.iloc[0]["lead_h"]),
            "last_available_h": float(w.iloc[-1]["lead_h"]),
            "n_last_available": int(w.iloc[-1]["n"]),
            "end_reason": "threshold_failure" if first_failed is not None else "data_exhausted",
            "below_first_lead": "unmeasured",
        }
    return result


def horizon_statements(
    table: pd.DataFrame, columns: Iterable[Column] | None = None, band: str | None = None
) -> list[str]:
    """Narrow component-diagnostic statements, with no beam classification inference."""
    cols = list(columns) if columns is not None else table_columns()
    t = _select(table, band)
    if t.empty or not cols:
        return []
    out = [
        f"At {band or 'this band'}, the largest stored cross-track component p95 is "
        f"{t['cross_p95_arcmin'].max():.3f} arcmin at mean-altitude range. This is not a sky-track-normal error.",
        "No beam-entry or beam-timing accuracy follows from this component table. Ages below the first "
        "sampled lead are unmeasured; an exhausted window is not a threshold failure.",
    ]
    for c in cols:
        status = threshold_status(t, c, which="in_track")
        out.append(
            c.label
            + ", in-track component threshold: "
            + "; ".join(
                f"{WINDOW_SHORT[w]}: {format_lead(x['passed_through_sampled_h'])}, "
                + (
                    f"first failed sample {format_lead(x['first_failed_sampled_h'])}"
                    if x["first_failed_sampled_h"] is not None
                    else f"data exhausted at {format_lead(x['last_available_h'])} (n={x['n_last_available']})"
                )
                for w, x in status.items()
            )
            + "."
        )
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
    """The reproducible component diagnostic, explicitly withdrawing its old interpretation."""
    cols = list(columns) if columns is not None else table_columns()
    lines = [
        "# Orbital-component angular-error thresholds",
        "",
        "**Correction.** The former crossing-horizon and position-horizon interpretations are withdrawn. "
        "An orbital cross-track residual does not determine whether a moving sky track enters a fixed beam. "
        "The radial and in-track residuals, observer rotation, range, pointing and distance from the beam edge "
        "all affect the answer. The stored component arithmetic below does not validate beam crossing or timing.",
        "",
        "These rows transform the stored RIC residuals using arctan2(|C|, mean altitude) and "
        "arctan2(|I|, mean altitude), in degrees. They are representative component scales, not an upper "
        "bound on complete topocentric error. |I| divided by the circular orbital speed is an orbital phase-time "
        "scale, not the error in beam-entry time. The p95 is NumPy's linearly interpolated sample quantile.",
        "",
        "The threshold diagnostic requires at least 95% of stored rows to be strictly below one third of the "
        "stated scalar beam width. That arbitrary fraction is distinct from a "
        "half-power crossing boundary, depends on the chosen fraction and does not supply a calibrated "
        "95% predictive probability. Repeated leads from an element set are dependent.",
        "",
        "Above 3 GHz the primary scalar width is the minimum diametric width of the measured half-power "
        "contour through the sampled image peak. Cuts are sampled every 0.5 degree in orientation and both "
        "first half-power roots are refined. This declared convention retains the measured frequency dependence "
        "and has no wavelength-scaling fallback. Actual channel frequencies, source hashes and the maximum "
        "diametric-width sensitivity are in the JSON. The full track comparison uses the complete 2D pattern, "
        "not this scalar width. [Published MeerKAT Jones patterns](https://doi.org/10.48479/wdb0-h061).",
        "",
        "Below 3 GHz this component diagnostic retains the historical 57.5 arcmin × 1500/frequency_MHz "
        "L-band relation and its labelled UHF/S0 extrapolations. The full topocentric comparison uses measured "
        "patterns in all six channels. The former analytic 3500 MHz calculation is retained only as an "
        "explicit historical comparison in the JSON. See [radio lane](radio-lane.md).",
        "",
        "## Stored population",
        "",
        f"Source: `{source or TRIALS_CSV.as_posix()}`. The table covers the four named 2024 windows only. "
        "Element epochs are not publication timestamps. These results describe the qualified reference "
        "missions and analysed manoeuvre exclusions; altitude overlap alone does not justify transfer to "
        "debris, constellation spacecraft or other missions.",
        "",
        *population_table_lines(trials),
        "",
        "## Stated scalar beam widths",
        "",
        "| Receiver / actual frequency | Scalar width (arcmin) | Component threshold width/3 (arcmin) | Width source |",
        "| --- | ---: | ---: | --- |",
    ]
    lines += [
        f"| {c.label} | {60 * c.fwhm_deg:.3f} | {60 * BEAM_FRACTION * c.fwhm_deg:.3f} | {c.beam_model} |" for c in cols
    ]
    for band in bands_present(table):
        lines += ["", f"## {band}", "", *_compact_block(table, band, windows_present(table)), ""]
        lines += [x + "\n" for x in horizon_statements(table, cols, band)]
        lines += [
            "| Component / receiver | Window | Last consecutive passing sampled lead "
            "| First failed sample | Last available / n | End reason |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for which in COMPONENTS:
            for c in cols:
                for window, st in threshold_status(table, c, which=which, band=band).items():
                    failed = format_lead(st["first_failed_sampled_h"]) if st["first_failed_sampled_h"] else "-"
                    lines.append(
                        f"| {which} / {c.label} | {WINDOW_SHORT[window]} | "
                        f"{format_lead(st['passed_through_sampled_h'])} | "
                        f"{failed} | "
                        f"{format_lead(st['last_available_h'])} / {st['n_last_available']} | {st['end_reason']} |"
                    )
    lines += [
        "",
        "A missing later row is not a failed row. In particular, the 600–750 km August sample "
        "ends at 120 h with four rows; it does not establish a crossing failure after five days. "
        "No stored row tests ages below six hours, so failure at six hours cannot establish impossibility "
        "at every element age. No actual satellite detections or observing schedule were used in this "
        "component table.",
        "",
    ]
    return "\n".join(lines)


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
    widest = [
        replace(c, fwhm_deg=c.beam_metadata["maximum_diametric_width_deg"]) if c.beam_metadata else c for c in cols
    ]
    historical = [Column(name, f, beam_fwhm_deg(f)) for name, f in TABLE_FREQUENCIES]
    return {
        "schema_version": 2,
        "built_at": datetime.now(UTC).isoformat(),
        "source_trials": source,
        "site": dict(MEERKAT_RECORD),
        "interpretation": "Orbital-component diagnostics only; former beam crossing/position accuracy claims withdrawn",
        "crossing_classification_calibrated": False,
        "beam": {
            "model": "measured minimum diametric half-power width above 3 GHz; labelled historical scale below",
            "fwhm_arcmin_at_1500_mhz": site_mod.BEAM_FWHM_ARCMIN_AT_1500_MHZ,
            "k_lambda_over_d": site_mod.beam_fwhm_lambda_over_d(),
            "source": site_mod.BEAM_SOURCE,
            "measured_comparison_source": site_mod.MEASURED_BEAM_DOI,
        },
        "geometry": "arctan2(abs(orbital component), mean altitude); "
        "not a full topocentric error or sky-track displacement",
        "coverage": COVERAGE,
        "beam_fraction": BEAM_FRACTION,
        "quantile_method": "linear sample interpolation; threshold coverage is the strict empirical fraction",
        "columns": [
            {
                "receiver": c.receiver,
                "freq_mhz": c.freq_mhz,
                "fwhm_deg": c.fwhm_deg,
                "beam_model": c.beam_model,
                "beam_metadata": c.beam_metadata,
                "key": c.key,
                "cross_track_key": c.cross_track_key,
                "in_track_key": c.in_track_key,
            }
            for c in cols
        ],
        "windows": {w: WINDOW_LABELS[w] for w in windows_present(table)},
        "bands": bands_present(table),
        "population": band_populations(trials) if trials is not None else None,
        "rows": json.loads(table.to_json(orient="records")),
        "definitions": {
            "cross_track_threshold": "Last passing consecutive sampled orbital-C lead; no beam-entry guarantee",
            "in_track_threshold": "Last passing consecutive sampled orbital-I lead; no sky-position guarantee",
            "phase_time": "abs(in_track_km)/circular_orbit_speed_km_s; not a beam timing residual",
        },
        "component_thresholds_hours": component_thresholds(table, cols),
        "component_criterion_sensitivity": {
            "interpretation": "Changing the arbitrary scalar-component threshold; "
            "not changing a measured beam crossing boundary",
            "beam_fraction": 0.5,
            "component_thresholds_hours": component_thresholds(horizon_table(trials, cols, beam_fraction=0.5), cols)
            if trials is not None
            else None,
        },
        "maximum_measured_width_sensitivity": {
            "interpretation": "Use maximum rather than minimum measured diametric width above 3 GHz",
            "beam_fraction": BEAM_FRACTION,
            "widths_deg": {c.key: c.fwhm_deg for c in widest},
            "component_thresholds_hours": component_thresholds(horizon_table(trials, widest), widest)
            if trials is not None
            else None,
        },
        "historical_analytic_comparison": {
            "interpretation": "Historical wavelength-scaled widths at nominal frequencies, including 3500 MHz; "
            "not the current measured S4 scalar result",
            "widths_deg": {c.key: c.fwhm_deg for c in historical},
            "component_thresholds_hours": component_thresholds(horizon_table(trials, historical), historical)
            if trials is not None
            else None,
        },
        "threshold_status": {
            which: {
                b: {c.key: threshold_status(table, c, which=which, band=b) for c in cols} for b in bands_present(table)
            }
            for which in COMPONENTS
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
class ComponentDiagnostic:
    """Projected component scales for a qualified reference mission; no crossing guarantee."""

    window: str
    lead_h: float
    n_trials: int
    cross_p95_deg: float
    along_p95_deg: float
    along_shift_p95_s: float
    cross_track_fraction_inside: float  # the cross-track component threshold test at this age and geometry
    in_track_fraction_inside: float  # the in-track component threshold test
    band: str | None = None


def component_diagnostic(
    trials: pd.DataFrame,
    window: str,
    age_hours: float,
    range_km: float,
    projection_cross: float,
    projection_along: float,
    fwhm_deg: float,
    band: str | None = None,
) -> ComponentDiagnostic | None:
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
    return ComponentDiagnostic(
        window=window,
        lead_h=lead,
        n_trials=int(len(g)),
        cross_p95_deg=float(np.quantile(cross, 0.95)),
        along_p95_deg=float(np.quantile(along, 0.95)),
        along_shift_p95_s=float(np.quantile(shift, 0.95)),
        cross_track_fraction_inside=float(np.mean(cross < limit)),
        in_track_fraction_inside=float(np.mean(along < limit)),
        band=band,
    )
