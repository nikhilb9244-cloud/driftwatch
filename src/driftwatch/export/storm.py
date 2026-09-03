"""What the viewer needs for storm mode and for the May 2024 replay (Phase 3, Step 5).

Two exports, and they are separate on purpose.

## `scenarios.json`: the same events under every scenario

The conjunctions bundle carries one scenario. Storm mode has to switch between five without
re-fetching the geometry, the names, the tracks or the encounter-plane covariances that do not
depend on the scenario at all -- so this file carries **only what a scenario changes**, in
columns parallel to the base bundle's ``events`` and ``pairs`` arrays. The browser indexes into
them; it joins nothing and computes no screening result, exactly as in Phase 2.

It is **fetched lazily**, after the first paint, and never on the critical path. The base
bundle is unchanged in size, so Phase 1's performance and the console's paint budget
(`docs/design-brief.md` §8) are untouched by storm mode existing.

**The miss under a scenario is `miss_shifted_km`, not the event's `miss_km`.** The geometry's
miss is what the two element sets predicted; the scenario moved the objects, and the number the
probability was computed from is the shifted one. Showing the geometry's miss beside a storm
probability would be showing two answers to different questions side by side, so the overlay
carries the shifted miss and the viewer's Miss column reads from it.

**Every aggregate in the summary is given both ways**, over the events whose two objects both
have a ballistic coefficient measured from their own decay and over the rest. Step 4 measured
the storm term against the May 2024 record and found it predictive at r = 0.88 for the first
group and of no demonstrated skill for the second, and the split turns out to matter: on the
demo run the median ``pc / pc_variance_only`` is 0.16 over the validated events and 0.89 over
the indicative ones. A single combined figure averages a large real effect with a near-absent
unmeasured one, weighted by the coverage of the coefficient fit rather than by physics. See
`docs/methods.md`, "Storm-term validity".

## `storm.json`: the replay timeline

The Kp bar, the density ratio at 400 and 500 km, and the index of Sun frames, on one three-hour
grid so that scrubbing moves all three together. Written into the replay bundle's own directory
beside a historical catalogue export and that run's own conjunctions, because replay is a
*mode*: the times become historical, the positions come from the historical snapshot, and none
of it should load until a reader asks for it.

**The density ratio's denominator is the Gannon quiet control window** (`config`), which is the
same denominator Step 4's measurement used. A ratio in the viewer that meant something different
from the ratio in the validation document would be the worst kind of small inconsistency.
"""

from __future__ import annotations

import base64
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import __version__, config
from driftwatch.drag import density as dn
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.export.report import cumulative_pc, normalise
from driftwatch.storm import term
from driftwatch.weather import helioviewer

log = logging.getLogger(__name__)

OVERLAY_VERSION = 1
STORM_VERSION = 1
#: The altitudes the replay timeline reports a density ratio at, as the Step 5 prompt asks.
REPLAY_ALTITUDES_KM: tuple[float, ...] = (400.0, 500.0)

#: Per-event columns a scenario changes. Rounded like the base bundle: probabilities to four
#: significant figures, distances to four decimals.
EVENT_NUMBERS: tuple[str, ...] = (
    "pc",
    "pc_shift_only",
    "pc_variance_only",
    "pc_max",
    "pc_max_scale",
    "miss_shifted_km",
    "relative_shift_km",
    "shift_i_primary_km",
    "shift_i_secondary_km",
    "sigma_i_primary_km",
    "sigma_i_secondary_km",
    "enc_cov_xx_km2",
    "enc_cov_xy_km2",
    "enc_cov_yy_km2",
)
EVENT_LABELS: tuple[str, ...] = (
    "region",
    "flag",
    "confidence",
    "storm_validity",
    "storm_source_primary",
    "storm_source_secondary",
    "unscoreable_reason",
)
# Four significant figures rather than fixed decimals for everything that spans orders of
# magnitude. A probability runs from 1e-80 to 1, and an encounter-plane variance from 1e-8 to
# 1e3 km^2; eight decimal places on the second wrote sixteen characters to express three, and
# four significant figures is already far more than the covariance behind it can justify.
_SIGNIFICANT = {
    "pc",
    "pc_shift_only",
    "pc_variance_only",
    "pc_max",
    "enc_cov_xx_km2",
    "enc_cov_xy_km2",
    "enc_cov_yy_km2",
    "sigma_i_primary_km",
    "sigma_i_secondary_km",
}
_DECIMALS = {
    "pc_max_scale": 3,
    "miss_shifted_km": 4,
    "relative_shift_km": 4,
    "shift_i_primary_km": 4,
    "shift_i_secondary_km": 4,
}


def _number(value: Any, column: str) -> float | None:
    """One overlay number, rounded, with every non-finite value going to ``null``.

    ``null`` rather than ``NaN`` because JSON has no NaN and because an unscoreable event's
    probability genuinely is absent rather than zero -- the viewer renders it as an em dash and
    refuses to sort on it.
    """
    x = float(value) if value is not None else float("nan")
    if not np.isfinite(x):
        return None
    if column in _SIGNIFICANT:
        return 0.0 if x == 0.0 else float(f"{x:.4g}")
    return round(x, _DECIMALS.get(column, 4))


def _column(rows: pd.DataFrame, name: str) -> list[Any]:
    if name not in rows.columns:
        return [None] * len(rows)
    return [_number(v, name) for v in pd.to_numeric(rows[name], errors="coerce").to_numpy(dtype=float)]


def _encode(values: list[str]) -> dict[str, Any]:
    """Dictionary-encode a list of repeated short strings. See :func:`_labels`."""
    distinct: list[str] = []
    index: dict[str, int] = {}
    codes = []
    for value in values:
        code = index.get(value)
        if code is None:
            code = index[value] = len(distinct)
            distinct.append(value)
        codes.append(code)
    return {"v": distinct, "i": codes}


def _labels(rows: pd.DataFrame, name: str) -> dict[str, Any]:
    """A label column, dictionary-encoded: ``{"v": [...distinct values...], "i": [...codes...]}``.

    Every one of these columns is drawn from a handful of values repeated thousands of times --
    three regions, four flags, three validities, four coefficient sources, and one unscoreable
    reason per affected object. Written out as strings they were a third of the overlay; encoded
    they are a rounding error, and the browser reads them with a single index. The viewer's
    ``decode()`` is four lines.
    """
    values = [""] * len(rows) if name not in rows.columns else [("" if pd.isna(v) else str(v)) for v in rows[name]]
    return _encode(values)


# --------------------------------------------------------------------------------------
# The per-scenario overlay


def event_overlay(rows: pd.DataFrame, event_ids: list[str]) -> dict[str, Any]:
    """One scenario's per-event columns, reindexed onto the base bundle's event order.

    An event the scenario has no row for -- which should not happen, since every scenario
    rescores the same stored events -- comes back as nulls rather than being dropped, so the
    arrays stay parallel and the browser can index without checking lengths.
    """
    indexed = rows.set_index("event_id").reindex(event_ids)
    out: dict[str, Any] = {name: _column(indexed, name) for name in EVENT_NUMBERS}
    out |= {name: _labels(indexed, name) for name in EVENT_LABELS}
    scoreable = indexed.get("scoreable")
    out["scoreable"] = (
        [True] * len(event_ids) if scoreable is None else [bool(v) if pd.notna(v) else True for v in scoreable]
    )
    return out


def pair_overlay(rows: pd.DataFrame, keys: list[tuple[int, int]]) -> dict[str, Any]:
    """One scenario's per-pair rollup, reindexed onto the base bundle's pair order.

    Recollapsed here rather than reused from :func:`driftwatch.export.report.collapse_pairs`
    for one reason: the pair's miss has to be the **shifted** one under a storm scenario, and
    the flag, region and confidence have to come from the event that is worst *under this
    scenario*, which is not always the same event. A pair whose every event is unscoreable has
    no probability and says so.
    """
    grouped = rows.groupby(["primary_norad_id", "secondary_norad_id"], sort=False)
    frames: dict[tuple[int, int], pd.DataFrame] = {
        (int(p), int(s)): group
        for (p, s), group in grouped  # noqa: B905
    }
    max_pc: list[float | None] = []
    closest: list[float | None] = []
    cumulative: list[float | None] = []
    max_pc_max: list[float | None] = []
    region: list[str] = []
    flag: list[str] = []
    confidence: list[str] = []
    validity: list[str] = []
    n_scoreable: list[int] = []
    miss_at_max: list[float | None] = []
    for key in keys:
        group = frames.get(key)
        if group is None or not len(group):
            max_pc.append(None)
            closest.append(None)
            cumulative.append(None)
            max_pc_max.append(None)
            miss_at_max.append(None)
            region.append("unknown")
            flag.append("none")
            confidence.append("none")
            validity.append(term.NO_STORM_TERM)
            n_scoreable.append(0)
            continue
        pc = pd.to_numeric(group["pc"], errors="coerce")
        miss = pd.to_numeric(group["miss_scenario_km"], errors="coerce")
        usable = pc.notna()
        worst = group.loc[pc.idxmax()] if usable.any() else group.iloc[0]
        max_pc.append(_number(pc.max(), "pc") if usable.any() else None)
        closest.append(_number(miss.min(), "miss_shifted_km"))
        cumulative.append(_number(cumulative_pc(pc.to_numpy(dtype=float)), "pc") if usable.any() else None)
        max_pc_max.append(_number(pd.to_numeric(group["pc_max"], errors="coerce").max(), "pc"))
        miss_at_max.append(_number(miss.loc[worst.name] if usable.any() else miss.min(), "miss_shifted_km"))
        region.append(str(worst.get("region", "unknown")))
        flag.append(str(worst.get("flag", "none")))
        confidence.append(str(worst.get("confidence", "none")))
        # A pair is only as validated as its worst-scored event, for the same reason an event is
        # only as validated as its weaker object: the number on the row is the one being judged.
        validity.append(str(worst.get("storm_validity", term.NO_STORM_TERM)))
        n_scoreable.append(int(usable.sum()))
    return {
        "max_pc": max_pc,
        "closest_km": closest,
        "miss_at_max_pc_km": miss_at_max,
        "pc_cumulative": cumulative,
        "max_pc_max": max_pc_max,
        "region": _encode(region),
        "flag": _encode(flag),
        "confidence": _encode(confidence),
        "storm_validity": _encode(validity),
        "n_scoreable": n_scoreable,
    }


def scenario_summary(rows: pd.DataFrame) -> dict[str, Any]:
    """The aggregate figures the storm panel shows, over both populations and combined.

    Combined is last and is never alone. See the module docstring for why the split is not
    decoration: on the demo run the two populations disagree by a factor of five on the one
    number this phase is about.
    """
    labels = [term.VALIDATED, term.INDICATIVE]
    groups: list[tuple[str, pd.DataFrame]] = []
    if "storm_validity" in rows.columns:
        for label in labels:
            subset = rows[rows["storm_validity"].astype(str) == label]
            if len(subset):
                groups.append((label, subset))
    groups.append(("combined", rows))

    def figures(frame: pd.DataFrame) -> dict[str, Any]:
        scoreable = frame[frame["flag"] != "unscoreable"] if "flag" in frame.columns else frame
        relative = pd.to_numeric(scoreable.get("relative_shift_km"), errors="coerce").to_numpy(dtype=float)
        moved = np.isfinite(relative) & (relative > 0)
        pc = pd.to_numeric(scoreable.get("pc"), errors="coerce").to_numpy(dtype=float)
        variance = pd.to_numeric(scoreable.get("pc_variance_only"), errors="coerce").to_numpy(dtype=float)
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = np.where(variance > 0, pc / variance, np.nan)
        comparable = np.isfinite(ratio) & (variance > 1e-12)
        return {
            "n_events": int(len(frame)),
            "n_moved": int(moved.sum()),
            "median_relative_shift_km": round(float(np.median(relative[moved])), 3) if moved.any() else None,
            "p90_relative_shift_km": round(float(np.quantile(relative[moved], 0.9)), 3) if moved.any() else None,
            "median_pc_over_variance_only": round(float(np.nanmedian(ratio[comparable])), 4)
            if comparable.any()
            else None,
            "n_lowered_by_shift": int(np.nansum(ratio[comparable] < 1.0)),
            "n_raised_by_shift": int(np.nansum(ratio[comparable] > 1.0)),
            "n_red": int((frame["flag"] == "red").sum()) if "flag" in frame.columns else 0,
            "n_yellow": int((frame["flag"] == "yellow").sum()) if "flag" in frame.columns else 0,
            "n_unscoreable": int((frame["flag"] == "unscoreable").sum()) if "flag" in frame.columns else 0,
        }

    return {label: figures(frame) for label, frame in groups}


def unscoreable_rows(rows: pd.DataFrame) -> list[dict[str, Any]]:
    """The events this scenario refused to score, for the queue's own section below it.

    They cannot be ranked by a number they do not have, and a blank in a probability column
    would read as "safe" (`docs/design-brief.md` §5), so they are listed separately with the
    reason and everything except a probability.
    """
    if "flag" not in rows.columns:
        return []
    bad = rows[rows["flag"] == "unscoreable"]
    if not len(bad):
        return []
    out = []
    for _, row in bad.sort_values("tca").iterrows():
        out.append(
            {
                "event_id": str(row["event_id"]),
                "primary_name": str(row.get("primary_name", "")),
                "secondary_name": str(row.get("secondary_name", "")),
                "secondary_norad_id": int(row["secondary_norad_id"]),
                "tca": pd.Timestamp(row["tca"]).isoformat().replace("+00:00", "Z"),
                "miss_km": _number(row.get("miss_km"), "miss_shifted_km"),
                "reason": str(row.get("unscoreable_reason", "")),
            }
        )
    return out


def build_overlays(run: RunDirectory, bundle: dict[str, Any]) -> dict[str, Any]:
    """Every stored scenario's overlay, parallel to ``bundle``'s events and pairs.

    ``bundle`` is the base conjunctions bundle, which fixes the order the arrays are in.
    """
    joined = run.read_conjunctions()
    event_ids = [str(e["event_id"]) for e in bundle["events"]]
    keys = [(int(p["primary_norad_id"]), int(p["secondary_norad_id"])) for p in bundle["pairs"]]
    stored = sorted(str(s) for s in joined["scenario"].dropna().unique())
    scenarios: dict[str, Any] = {}
    for name in stored:
        rows = normalise(joined[joined["scenario"] == name]).copy()
        rows["tca"] = pd.to_datetime(rows["tca"], utc=True)
        detail = rows[rows["event_id"].isin(set(event_ids))]
        scenarios[name] = {
            "events": event_overlay(detail, event_ids),
            "pairs": pair_overlay(rows, keys),
            "summary": scenario_summary(rows),
            "unscoreable": unscoreable_rows(rows),
            "n_events_total": int(len(rows)),
        }
    info = run.read_run()
    return {
        "overlay_version": OVERLAY_VERSION,
        "generator": f"driftwatch {__version__}",
        "run_id": info.get("run_id"),
        "n_events": len(event_ids),
        "n_pairs": len(keys),
        "scenarios": scenarios,
        "descriptions": {
            name: (info.get("risk", {}) or {}).get(name, {}).get("description", "")
            if isinstance(info.get("risk"), dict)
            else ""
            for name in stored
        },
        "notes": [
            "Only what a scenario changes is here; the geometry, the names and the tracks are in "
            "conjunctions.json and do not depend on the scenario.",
            "Columns are parallel to conjunctions.json's events and pairs arrays, in the same order. "
            "A label column is dictionary-encoded as {v: [distinct values], i: [codes]}; a numeric "
            "column is a plain array with null where the value is absent.",
            "The miss under a scenario is the shifted miss, not the geometry's: the scenario moved "
            "the objects, and the shifted miss is what its probability was computed from.",
            "storm_validity is validated when both objects have a ballistic coefficient fitted from "
            "their own decay and indicative otherwise. The storm term is predictive at r = 0.88 for "
            "the first group and has no demonstrated skill for the second, so every aggregate is "
            "given both ways. Nothing is weighted or withheld by the label.",
            "An unscoreable event carries null in every probability: its in-track displacement left "
            "the linear theory the term was derived under. It is not a small probability.",
        ],
    }


# --------------------------------------------------------------------------------------
# The replay timeline


def kp_series(table: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
    """The three-hourly Kp, ap and provenance over the replay window."""
    t = pd.to_datetime(table["t"], utc=True)
    inside = (t >= pd.Timestamp(start)) & (t <= pd.Timestamp(end))
    out = table.loc[inside, ["t", "kp", "ap", "provenance"]].copy()
    return out.sort_values("t").reset_index(drop=True)


def density_ratio_series(
    table: pd.DataFrame,
    times: list[datetime],
    *,
    baseline: pd.DataFrame | None = None,
    altitudes_km: tuple[float, ...] = REPLAY_ALTITUDES_KM,
) -> pd.DataFrame:
    """Density at each altitude through the window, over its quiet-window value at the same altitude.

    Both numerator and denominator are averaged over 24 local solar times, because the day-night
    contrast at these altitudes is a factor of two and a single longitude would make the ratio a
    coin toss. The denominator is the **Gannon quiet control window**, which is the denominator
    Step 4's measured enhancement used (`docs/storm-validation.md` §1); a viewer ratio meaning
    something different from the validated one would be a needless inconsistency.
    """
    quiet_start, quiet_end = (pd.Timestamp(s) for s in config.GANNON_QUIET_WINDOW)
    reference = baseline if baseline is not None else table
    covered = pd.to_datetime(reference["t"], utc=True)
    if covered.min() > quiet_start or covered.max() < quiet_end:
        raise ValueError(
            f"the baseline weather table runs {covered.min().isoformat()} to {covered.max().isoformat()}, "
            f"which does not cover the quiet control window {quiet_start.isoformat()} to "
            f"{quiet_end.isoformat()}. Every ratio would come back NaN. Pass a table that reaches it."
        )
    quiet_times = pd.date_range(quiet_start, quiet_end, freq="6h", inclusive="left")
    quiet = {
        alt: float(
            np.nanmedian(
                [
                    dn.quiet_density_profile(reference, at=t.to_pydatetime(), altitudes_km=(alt,))[
                        "rho_mean_kg_m3"
                    ].iloc[0]
                    for t in quiet_times
                ]
            )
        )
        for alt in altitudes_km
    }
    rows = []
    for t in times:
        profile = dn.quiet_density_profile(table, at=t, altitudes_km=altitudes_km)
        row: dict[str, Any] = {"t": pd.Timestamp(t)}
        for alt in altitudes_km:
            rho = float(profile.loc[profile["altitude_km"] == alt, "rho_mean_kg_m3"].iloc[0])
            row[f"rho_{int(alt)}km"] = rho
            row[f"ratio_{int(alt)}km"] = rho / quiet[alt] if quiet[alt] > 0 else float("nan")
        rows.append(row)
    out = pd.DataFrame(rows)
    out.attrs["quiet"] = {f"{int(a)}km": quiet[a] for a in altitudes_km}
    out.attrs["quiet_window"] = list(config.GANNON_QUIET_WINDOW)
    return out


def copy_sun_frames(frames: list[helioviewer.SunFrame], out_dir: Path) -> list[dict[str, Any]]:
    """Copy the cached Helioviewer PNGs into the replay bundle and index them.

    Each frame records the time it was **asked for** and the time the image actually is, because
    Helioviewer returns the nearest image it holds and that can be hours away during a data gap.
    A replay that silently showed yesterday's Sun would be worse than showing none, so the lag is
    carried to the viewer and rendered.

    **The thumbnail travels inline and the full image does not.** A 64 px disc is about 3 kB, so
    all of them together are a fraction of the timeline JSON and every scrub position has a
    picture the instant the file parses. The 360 kB full frames stay as files and are fetched as
    the playhead approaches them. ``eager`` marks the handful worth requesting before the reader
    scrubs anywhere -- see :func:`eager_frames`.
    """
    sun_dir = out_dir / "sun"
    sun_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for frame in frames:
        if not frame.path.exists():
            continue
        target = sun_dir / frame.path.name
        shutil.copyfile(frame.path, target)
        thumb = None
        if frame.thumb is not None and frame.thumb.exists():
            thumb = "data:image/png;base64," + base64.b64encode(frame.thumb.read_bytes()).decode("ascii")
        index.append(
            {
                "requested": frame.requested.isoformat().replace("+00:00", "Z"),
                "actual": frame.actual.isoformat().replace("+00:00", "Z") if frame.actual else None,
                "lag_minutes": round(frame.lag.total_seconds() / 60.0, 1) if frame.lag is not None else None,
                "path": f"sun/{frame.path.name}",
                "bytes": target.stat().st_size,
                "thumb": thumb,
                "eager": False,
            }
        )
    return index


def eager_frames(index: list[dict[str, Any]], kp: pd.DataFrame, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Mark the few full-resolution frames the viewer should fetch before the reader scrubs.

    Three, by default, and they are chosen rather than taken in order: the **first**, because it
    is what the replay opens on; the frame nearest the **peak Kp**, because it is where a reader
    scrubbing to "the storm" lands and it is the picture the whole replay is about; and the
    **last**, so the far end of the scrubber is not the one position that always waits. Everything
    else arrives over its thumbnail as the playhead approaches it.
    """
    limit = config.HELIOVIEWER_EAGER_FRAMES if limit is None else limit
    if not index or limit <= 0:
        return index
    times = [pd.Timestamp(f["actual"] or f["requested"]) for f in index]
    wanted = {0, len(index) - 1}
    values = pd.to_numeric(kp["kp"], errors="coerce") if len(kp) else pd.Series(dtype=float)
    if values.notna().any():
        peak = pd.Timestamp(kp.loc[values.idxmax(), "t"])
        wanted.add(int(np.argmin([abs((t - peak).total_seconds()) for t in times])))
    for i in sorted(wanted)[:limit]:
        index[i]["eager"] = True
    return index


def build_storm_bundle(
    *,
    scenario: str,
    start: datetime,
    end: datetime,
    table: pd.DataFrame,
    frames: list[helioviewer.SunFrame],
    out_dir: Path,
    baseline_table: pd.DataFrame | None = None,
    run_id: str | None = None,
    snapshot: str | None = None,
) -> dict[str, Any]:
    """The replay timeline: the Kp bar, the density ratios and the Sun frames on one grid.

    ``baseline_table`` must cover the quiet control window, which a table built over the replay
    window does not: they are three weeks apart. Without it every ratio comes back NaN, which is
    how this was found.
    """
    kp = kp_series(table, start, end)
    times = [t.to_pydatetime() for t in pd.to_datetime(kp["t"], utc=True)]
    ratios = density_ratio_series(table, times, baseline=baseline_table)
    sun = eager_frames(copy_sun_frames(frames, out_dir), kp)
    return {
        "storm_version": STORM_VERSION,
        "generator": f"driftwatch {__version__}",
        "scenario": scenario,
        "run_id": run_id,
        "snapshot": snapshot,
        "window": {
            "start": start.isoformat().replace("+00:00", "Z"),
            "end": end.isoformat().replace("+00:00", "Z"),
        },
        "kp": {
            "t": [pd.Timestamp(t).isoformat().replace("+00:00", "Z") for t in kp["t"]],
            "kp": [round(float(v), 3) if np.isfinite(v) else None for v in kp["kp"]],
            "ap": [round(float(v), 2) if np.isfinite(v) else None for v in kp["ap"]],
            "provenance": [str(v) for v in kp["provenance"]],
        },
        "density": {
            "altitudes_km": list(REPLAY_ALTITUDES_KM),
            "t": [pd.Timestamp(t).isoformat().replace("+00:00", "Z") for t in ratios["t"]],
            **{
                f"ratio_{int(a)}km": [
                    round(float(v), 4) if np.isfinite(v) else None for v in ratios[f"ratio_{int(a)}km"]
                ]
                for a in REPLAY_ALTITUDES_KM
            },
            "quiet_baseline_kg_m3": {k: f"{v:.4e}" for k, v in ratios.attrs["quiet"].items()},
            "quiet_window": ratios.attrs["quiet_window"],
        },
        "sun": {
            "layers": config.HELIOVIEWER_LAYERS,
            "citation": config.HELIOVIEWER_CITATION,
            "frames": sun,
            "total_bytes": sum(int(f["bytes"]) for f in sun),
            "thumb_px": config.HELIOVIEWER_THUMB_PX,
            "n_eager": sum(1 for f in sun if f["eager"]),
            "n_with_thumb": sum(1 for f in sun if f["thumb"]),
        },
        "notes": [
            "Kp and ap are the observed record from CelesTrak's SW-All file; provenance says so per row.",
            "The density ratio is NRLMSIS at that altitude, averaged over 24 local solar times, divided "
            "by the same average over the quiet control window the Step 4 validation used. NRLMSIS "
            "over-predicted the measured enhancement of this storm by about 22 per cent and nothing "
            "here is corrected for that; see docs/storm-validation.md.",
            "A Sun frame is the nearest image Helioviewer holds to the time asked for. The lag is on "
            "every frame and the viewer shows it, because a stale image with no label would be worse "
            "than none.",
            "Each frame carries a 64 px thumbnail inline as a data URI and its full 512 px image as a "
            "file. The viewer draws the thumbnail at once and fetches the full image as the playhead "
            "approaches; the three marked `eager` are requested up front.",
        ],
    }


def write_storm_bundle(bundle: dict[str, Any], out_dir: Path) -> Path:
    path = Path(out_dir) / "storm.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    log.info(
        "Replay timeline: %d Kp intervals, %d Sun frames (%.1f MiB as files, %d eager, %d with an "
        "inline thumbnail), %.1f kB JSON -> %s",
        len(bundle["kp"]["t"]),
        len(bundle["sun"]["frames"]),
        bundle["sun"]["total_bytes"] / 1024 / 1024,
        bundle["sun"]["n_eager"],
        bundle["sun"]["n_with_thumb"],
        path.stat().st_size / 1024,
        path,
    )
    return path


def write_overlays(overlays: dict[str, Any], out_dir: Path) -> Path:
    path = Path(out_dir) / "scenarios.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overlays, separators=(",", ":")), encoding="utf-8")
    log.info(
        "Scenario overlays: %d scenarios over %d events and %d pairs, %.1f kB -> %s",
        len(overlays["scenarios"]),
        overlays["n_events"],
        overlays["n_pairs"],
        path.stat().st_size / 1024,
        path,
    )
    return path


def replay_frames(start: datetime, end: datetime, *, offline: bool = True) -> list[helioviewer.SunFrame]:
    """The cached Sun frames over the window, fetching none unless ``offline`` is False."""
    return helioviewer.fetch_frames(start, end, offline=offline)


def replay_window(scenario: str, days: float) -> tuple[datetime, datetime]:
    """The window a ``replay:<date>`` scenario names, and its end ``days`` later."""
    from driftwatch.storm.scenarios import replay_start

    start = replay_start(scenario)
    if start is None:
        raise ValueError(f"{scenario!r} does not name a date; use replay:<YYYY-MM-DD>")
    return start, start + timedelta(days=days)
