"""The weekly report and the viewer's conjunction bundle (Phase 2, Step 4).

Both are built from a run directory and both collapse repeated encounters. A fleet
member and a co-orbital secondary can meet every orbit: on the first live run one
Starlink satellite came back 130 times in a week, and a list of 130 near-identical rows
buries the twenty pairs a reader should look at. So the report and the viewer show one
row per pair, with the number of events, the closest miss, the highest probability and
the first time of closest approach, and the individual events underneath on demand. The
parquet and the JSON keep every event, as decided at the Step 2 review.

A pair also gets a cumulative probability, one minus the product of the complements over
its events. It is an upper bound rather than a probability: the events of one pair are
repeated passes of the same two objects propagated from the same two element sets, so
their errors are strongly correlated and the true combined probability is lower. It is
reported because a reader comparing a pair that comes back 130 times with a pair seen
once needs some measure of the difference, and it is labelled as not independent
wherever it appears.

The viewer bundle carries the encounter geometry and, for the events a reader can open,
the two objects' tracks for ten minutes either side of the time of closest approach,
sampled in Python from the same element sets the screening used (the catalogue snapshot
plus the stored supplemental version the run recorded). The browser draws those numbers;
it never computes a screening result.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import __version__, config
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.orbit.propagator import build_satrecs
from driftwatch.orbit.time import julian_dates
from driftwatch.risk.pc import RED_PC, SLOW_ENCOUNTER_KMS, YELLOW_PC

log = logging.getLogger(__name__)

BUNDLE_VERSION = 1
# The track drawn either side of the time of closest approach, and its sampling.
TRACK_HALF_WINDOW_S = 600.0
TRACK_STEP_S = 20.0
TRACK_SAMPLES = int(2 * TRACK_HALF_WINDOW_S / TRACK_STEP_S) + 1
# How many events the viewer bundle carries tracks for: every flagged event, then the
# highest probability first until the cap. 300 events is about 440 kB of float32.
MAX_TRACKED_EVENTS = 300
# The panel lists every pair, but carries the individual events only for the pairs a reader
# can act on: every flagged pair, every pair with an event inside the notification box, and
# the highest-probability pairs up to this many. The parquet keeps all of them.
MAX_DETAIL_PAIRS = 250
TOP_N = 20

PAIR_COLUMNS: tuple[str, ...] = (
    "scenario",
    "primary_norad_id",
    "primary_name",
    "secondary_norad_id",
    "secondary_name",
    "secondary_category",
    "n_events",
    "first_tca",
    "closest_km",
    "closest_tca",
    "max_pc",
    "max_pc_tca",
    "miss_at_max_pc_km",
    "pc_cumulative",
    "max_pc_max",
    "pc_max_scale_at_max_pc",
    "region",
    "flag",
    "confidence",
    "storm_validity",
    "n_in_box",
    "manoeuvre_secondary",
    "secondary_ephemeris",
    "cov_source_secondary",
    "hbr_m",
)

_FLAG_ORDER = {"none": 0, "yellow": 1, "red": 2}


def cumulative_pc(pc: np.ndarray) -> float:
    """``1 - prod(1 - pc)`` over a pair's events: an upper bound, since the events are not independent."""
    p = np.asarray(pc, dtype=float)
    p = p[np.isfinite(p)]
    if not len(p):
        return float("nan")
    return float(1.0 - np.prod(1.0 - np.clip(p, 0.0, 1.0)))


def normalise(conjunctions: pd.DataFrame) -> pd.DataFrame:
    """Fill the columns a run scored before they existed, so an older run still reports.

    ``region`` and ``confidence`` were added after the first live run; they are derived
    from ``pc_max_scale`` where it is present and left unknown where it is not.
    """
    df = conjunctions.copy()
    if "region" not in df.columns:
        from driftwatch.risk.pc import regions

        df["region"] = regions(pd.to_numeric(df.get("pc_max_scale"), errors="coerce").to_numpy())
    if "confidence" not in df.columns:
        from driftwatch.risk.pc import confidences

        df["confidence"] = confidences(df["region"].to_numpy())
    if "slow_encounter" not in df.columns and "rel_speed_kms" in df.columns:
        from driftwatch.risk.pc import slow_encounters

        df["slow_encounter"] = slow_encounters(pd.to_numeric(df["rel_speed_kms"], errors="coerce").to_numpy())
    # The miss under the scenario in force: `miss_km` is what the two element sets predicted,
    # and a storm scenario moved both objects before computing its probability. Quoting the
    # pre-storm miss beside a post-storm probability puts two answers to different questions on
    # one row, so everything that summarises a scenario reads this column and everything that
    # describes the geometry goes on reading `miss_km`. Under `quiet` they are the same number.
    geometry = pd.to_numeric(df["miss_km"], errors="coerce")
    shifted = pd.to_numeric(df["miss_shifted_km"], errors="coerce") if "miss_shifted_km" in df.columns else geometry
    df["miss_scenario_km"] = shifted.fillna(geometry)
    return df


def collapse_pairs(conjunctions: pd.DataFrame) -> pd.DataFrame:
    """One row per (scenario, primary, secondary): the count, the closest miss, the highest probability, the first TCA.

    The flag, region and confidence of a pair are those of its highest-probability event,
    which is the event the pair is judged on.
    """
    if conjunctions.empty:
        return pd.DataFrame(columns=list(PAIR_COLUMNS))
    df = normalise(conjunctions)
    df["tca"] = pd.to_datetime(df["tca"], utc=True)
    df["pc"] = pd.to_numeric(df["pc"], errors="coerce")
    rows: list[dict[str, Any]] = []
    for (scenario, primary, secondary), group in df.groupby(
        ["scenario", "primary_norad_id", "secondary_norad_id"], dropna=False, sort=False
    ):
        group = group.sort_values("tca")
        worst = group.loc[group["pc"].idxmax()] if group["pc"].notna().any() else group.iloc[0]
        closest = group.loc[group["miss_scenario_km"].idxmin()]
        rows.append(
            {
                "scenario": scenario,
                "primary_norad_id": int(primary),
                "primary_name": group["primary_name"].iloc[0],
                "secondary_norad_id": int(secondary),
                "secondary_name": group["secondary_name"].iloc[0],
                "secondary_category": group["secondary_category"].iloc[0],
                "n_events": int(len(group)),
                "first_tca": group["tca"].iloc[0],
                "closest_km": float(closest["miss_scenario_km"]),
                "closest_tca": closest["tca"],
                "max_pc": float(worst["pc"]) if pd.notna(worst["pc"]) else float("nan"),
                "max_pc_tca": worst["tca"],
                "miss_at_max_pc_km": float(worst["miss_scenario_km"]),
                "pc_cumulative": cumulative_pc(group["pc"].to_numpy()),
                "max_pc_max": float(pd.to_numeric(group["pc_max"], errors="coerce").max()),
                "pc_max_scale_at_max_pc": float(worst["pc_max_scale"]) if pd.notna(worst["pc_max_scale"]) else np.nan,
                "region": worst.get("region", "unknown"),
                "flag": worst.get("flag", "none"),
                "confidence": worst.get("confidence", "low"),
                # A pair is only as validated as the event it is judged on, for the same reason
                # an event is only as validated as its weaker object.
                "storm_validity": worst.get("storm_validity", "none"),
                "n_in_box": int(group["in_box"].sum()),
                "manoeuvre_secondary": group["manoeuvre_secondary"].iloc[0],
                "secondary_ephemeris": group["secondary_ephemeris"].iloc[0],
                "cov_source_secondary": group["cov_source_secondary"].iloc[0],
                "hbr_m": float(pd.to_numeric(group["hbr_m"], errors="coerce").iloc[0]),
            }
        )
    out = pd.DataFrame(rows, columns=list(PAIR_COLUMNS))
    return out.sort_values("max_pc", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# Tracks


@dataclass
class Tracks:
    """Sampled TEME positions around each event's time of closest approach."""

    event_ids: list[str]
    positions: np.ndarray  # (n_events, 2, TRACK_SAMPLES, 3) float32, km, primary then secondary
    step_s: float = TRACK_STEP_S
    samples: int = TRACK_SAMPLES
    half_window_s: float = TRACK_HALF_WINDOW_S

    def to_bytes(self) -> bytes:
        return np.ascontiguousarray(self.positions, dtype="<f4").tobytes()


def sample_tracks(events: pd.DataFrame, elements: pd.DataFrame) -> Tracks:
    """Propagate both objects of each event over ten minutes either side of the time of closest approach.

    ``elements`` is the element-set table the run screened from (the snapshot with the
    supplemental sets already substituted), indexed by NORAD id. Positions come back in
    TEME, the frame SGP4 works in and the one the viewer's own propagator uses, so the
    browser applies the same GMST rotation to these as to everything else it draws.
    """
    ids = sorted({int(i) for i in events["primary_norad_id"]} | {int(i) for i in events["secondary_norad_id"]})
    rows = elements.drop_duplicates("norad_id").set_index("norad_id")
    missing = [i for i in ids if i not in rows.index]
    if missing:
        raise KeyError(f"no element set for {len(missing)} object(s) in the events, first few {missing[:5]}")
    satrecs = dict(zip(ids, build_satrecs(rows.loc[ids].reset_index()), strict=True))

    offsets = (np.arange(TRACK_SAMPLES) - (TRACK_SAMPLES - 1) // 2) * TRACK_STEP_S
    tca = pd.to_datetime(events["tca"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    out = np.full((len(events), 2, TRACK_SAMPLES, 3), np.nan, dtype=np.float32)
    for k in range(len(events)):
        times = tca[k] + (offsets * 1e6).astype("timedelta64[us]")
        jd, fr = julian_dates(times)
        for side, column in enumerate(("primary_norad_id", "secondary_norad_id")):
            sat = satrecs[int(events[column].iloc[k])]
            err, r, _ = sat.sgp4_array(jd, fr)
            r = np.asarray(r, dtype=float)
            r[np.asarray(err) != 0] = np.nan
            out[k, side] = r.astype(np.float32)
    return Tracks([str(e) for e in events["event_id"]], out)


# The two flag values that mean "somebody should look at this". `unscoreable` is a third value
# and is deliberately not one of them: an event whose storm term ran outside the linear theory
# has no probability at all, so it can be neither flagged nor cleared, and counting it as flagged
# would put a pair with no number into a table of pairs ranked by their numbers.
ACTIONABLE_FLAGS: tuple[str, ...] = ("red", "yellow")


def is_flagged(flag: pd.Series) -> pd.Series:
    """Whether each row carries a flag a reader is meant to act on."""
    return flag.isin(ACTIONABLE_FLAGS)


def events_for_tracks(rows: pd.DataFrame, limit: int = MAX_TRACKED_EVENTS) -> pd.DataFrame:
    """The events the viewer carries tracks for: every flagged one, then the rest by probability."""
    if rows.empty:
        return rows
    ranked = rows.assign(
        _flagged=is_flagged(rows["flag"]).astype(int),
        _pc=pd.to_numeric(rows["pc"], errors="coerce").fillna(-1.0),
    ).sort_values(["_flagged", "_pc"], ascending=False)
    return ranked.head(limit).drop(columns=["_flagged", "_pc"]).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# The viewer bundle


def detail_pairs(pairs: pd.DataFrame, limit: int = MAX_DETAIL_PAIRS) -> pd.DataFrame:
    """The pairs the viewer carries individual events for: flagged, in the box, or highest probability."""
    if pairs.empty:
        return pairs
    keep = is_flagged(pairs["flag"]) | (pairs["n_in_box"] > 0)
    ranked = pairs.sort_values("max_pc", ascending=False)
    top = ranked.head(limit).index
    return pairs[keep | pairs.index.isin(top)]


def _clean(value: Any) -> Any:
    """JSON-safe: numpy scalars to Python, NaN and NaT to None, timestamps to ISO 8601."""
    if isinstance(value, pd.Timestamp):
        return value.tz_convert("UTC").isoformat().replace("+00:00", "Z") if value.tzinfo else value.isoformat()
    if value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, np.ndarray):
        return [_clean(v) for v in value]
    return value


# Probabilities span forty orders of magnitude, so they are rounded to significant figures
# rather than decimal places: four is far more than the covariance behind them can justify
# and keeps the bundle small.
_SIGNIFICANT: frozenset[str] = frozenset(
    {"pc", "pc_alfano", "pc_chan", "pc_max", "pc_max_scale", "pc_cumulative", "max_pc", "max_pc_max"}
)


def _significant(value: float, digits: int = 4) -> float:
    if value == 0.0 or not np.isfinite(value):
        return value
    return float(f"%.{digits}g" % value)


def _records(df: pd.DataFrame, columns: list[str], *, round_map: dict[str, int] | None = None) -> list[dict[str, Any]]:
    out = []
    for row in df[columns].to_dict("records"):
        cleaned = {}
        for key, value in row.items():
            value = _clean(value)
            if isinstance(value, float):
                if key in _SIGNIFICANT:
                    value = _significant(value)
                elif round_map and key in round_map:
                    value = round(value, round_map[key])
            cleaned[key] = value
        out.append(cleaned)
    return out


EVENT_JSON_COLUMNS: list[str] = [
    "event_id",
    "primary_norad_id",
    "secondary_norad_id",
    "tca",
    "miss_km",
    "rel_speed_kms",
    "miss_r_km",
    "miss_i_km",
    "miss_c_km",
    "in_box",
    "hbr_m",
    "sigma_i_primary_km",
    "sigma_i_secondary_km",
    "cov_source_secondary",
    "enc_cov_xx_km2",
    "enc_cov_xy_km2",
    "enc_cov_yy_km2",
    "pc",
    # Step 3's storm columns, carried at Step 5 so the panel can say what moved a number rather
    # than only that it moved. Present and inert under `quiet`, which is what makes the storm
    # control a re-render rather than a different code path.
    "pc_shift_only",
    "pc_variance_only",
    "miss_shifted_km",
    "relative_shift_km",
    "storm_source_primary",
    "storm_source_secondary",
    "storm_validity",
    "scoreable",
    "unscoreable_reason",
    "pc_max",
    "pc_max_scale",
    "region",
    "flag",
    "confidence",
]
PAIR_JSON_COLUMNS: list[str] = [
    "primary_norad_id",
    "primary_name",
    "secondary_norad_id",
    "secondary_name",
    "secondary_category",
    "n_events",
    "n_in_box",
    "first_tca",
    "closest_km",
    "max_pc",
    "miss_at_max_pc_km",
    "pc_cumulative",
    "max_pc_max",
    "region",
    "flag",
    "confidence",
    "storm_validity",
    "manoeuvre_secondary",
    "secondary_ephemeris",
    "cov_source_secondary",
    "hbr_m",
]
_ROUND = {
    "miss_km": 4,
    "rel_speed_kms": 4,
    "miss_r_km": 4,
    "miss_i_km": 4,
    "miss_c_km": 4,
    "closest_km": 4,
    "miss_at_max_pc_km": 4,
    "hbr_m": 2,
    "sigma_r_primary_km": 4,
    "sigma_i_primary_km": 4,
    "sigma_c_primary_km": 4,
    "sigma_r_secondary_km": 4,
    "sigma_i_secondary_km": 4,
    "sigma_c_secondary_km": 4,
    "enc_cov_xx_km2": 8,
    "enc_cov_xy_km2": 8,
    "enc_cov_yy_km2": 8,
    "miss_shifted_km": 4,
    "relative_shift_km": 4,
}


def build_bundle(
    run: RunDirectory,
    elements: pd.DataFrame,
    *,
    scenario: str | None = None,
    limit_tracks: int = MAX_TRACKED_EVENTS,
) -> tuple[dict[str, Any], Tracks]:
    """The viewer's conjunctions JSON and the track binary for one scenario of a run."""
    from driftwatch.export import storm as storm_export

    info = run.read_run()
    joined = run.read_conjunctions()
    scenarios = sorted(str(s) for s in joined["scenario"].dropna().unique())
    scenario = scenario or (scenarios[0] if scenarios else "quiet")
    rows = normalise(joined[joined["scenario"] == scenario])
    rows["tca"] = pd.to_datetime(rows["tca"], utc=True)
    # Kept before `rows` is narrowed to the detail set below, because the storm summary and the
    # unscoreable list are statements about the whole scenario. Computed over the detail subset
    # they disagreed with `scenarios.json` -- 2,052 events against 5,704 -- and the disagreement
    # showed up as numbers changing when the overlay landed rather than when the reader did
    # anything, which is the one failure mode a lazily fetched overlay must not have.
    all_rows = rows
    pairs = collapse_pairs(rows)

    detailed = detail_pairs(pairs)
    keys = set(zip(detailed["primary_norad_id"], detailed["secondary_norad_id"], strict=True))
    in_detail = [
        (int(p), int(s)) in keys for p, s in zip(rows["primary_norad_id"], rows["secondary_norad_id"], strict=True)
    ]
    detail_rows = rows[np.asarray(in_detail)]

    tracked = events_for_tracks(detail_rows, limit_tracks)
    tracks = sample_tracks(tracked, elements) if len(tracked) else Tracks([], np.zeros((0, 2, TRACK_SAMPLES, 3), "f4"))
    track_index = {event_id: k for k, event_id in enumerate(tracks.event_ids)}

    rows = detail_rows.sort_values(["primary_norad_id", "tca"]).reset_index(drop=True)
    event_records = _records(rows, EVENT_JSON_COLUMNS, round_map=_ROUND)
    for record in event_records:
        record["track"] = track_index.get(str(record["event_id"]))
    index_of = {str(e["event_id"]): k for k, e in enumerate(event_records)}

    pair_records = _records(pairs, PAIR_JSON_COLUMNS, round_map=_ROUND)
    for record, (_, pair) in zip(pair_records, pairs.iterrows(), strict=True):
        ids = rows.loc[
            (rows["primary_norad_id"] == pair["primary_norad_id"])
            & (rows["secondary_norad_id"] == pair["secondary_norad_id"]),
            "event_id",
        ]
        record["events"] = [index_of[str(i)] for i in ids if str(i) in index_of]

    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "generator": f"driftwatch {__version__}",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "run_id": info.get("run_id"),
        "snapshot": info.get("snapshot"),
        "fleet": info.get("fleet_name") or info.get("fleet"),
        "model_version": info.get("covariance", {}).get("model_version"),
        "scenario": scenario,
        "scenarios": scenarios,
        "window": {"start": info.get("start"), "end": info.get("end")},
        "supplemental": info.get("supplemental"),
        "screening": info.get("config"),
        "thresholds": {"red": RED_PC, "yellow": YELLOW_PC},
        # Storm mode fetches `scenarios.json` lazily and switches between these without
        # re-fetching anything here. `quiet` is the Phase 2 baseline every other one is read
        # against, so the viewer offers it as the comparison whichever scenario is in force.
        "storm": {
            "overlays": "scenarios.json",
            "baseline": "quiet",
            "scored": scenarios,
            "summary": storm_export.scenario_summary(all_rows),
            "unscoreable": storm_export.unscoreable_rows(all_rows),
        },
        "n_events": len(event_records),
        "n_events_total": int(len(joined[joined["scenario"] == scenario])),
        "n_pairs": len(pair_records),
        "n_pairs_detailed": int(len(detailed)),
        "pairs": pair_records,
        "events": event_records,
        "tracks": {
            "path": "conjunction-tracks.bin",
            "dtype": "float32le",
            "frame": "teme",
            "units": "km",
            "n_events": len(tracks.event_ids),
            "objects_per_event": 2,
            "samples": tracks.samples,
            "step_s": tracks.step_s,
            "half_window_s": tracks.half_window_s,
            "order": "event, object (primary then secondary), sample, xyz",
        },
        "caveats": [
            "Every number here comes from Python: the browser draws them and computes no screening result.",
            "Under a storm scenario the miss shown is the shifted miss, which is what that scenario's "
            "probability was computed from; the geometry's own miss is what the two element sets predicted "
            "before the storm term moved them, and the two answer different questions.",
            "storm_validity says how far Step 4's May 2024 validation reaches an event: validated when both "
            "objects have a ballistic coefficient fitted from their own decay, indicative otherwise. The "
            "storm term is predictive at a correlation of 0.88 for the first group and has no demonstrated "
            "skill for the second. Nothing is weighted or withheld by the label and every aggregate is "
            "reported both ways.",
            "The storm displaces the two objects of a pair nearly independently, not in common: the relative "
            "shift is a median 1.91 times the mean of the two absolute shifts, out of a possible 2. That a "
            "storm lowers most probabilities is measured; it happens because a displacement of tens of "
            "kilometres applied to a miss of a few separates more pairs than it creates.",
            "A pair's cumulative probability is one minus the product of the complements over its events. "
            "The events are repeated passes of the same two objects propagated from the same two element "
            "sets, so they are not independent and the true combined probability is lower.",
            "A flag in the dilution region is reported at low confidence: the probability there is held up "
            "by the size of the covariance rather than by the geometry, and is not actionable. It means the "
            "data cannot support a judgement either way, not that better data would clear the flag.",
            "Every pair is listed. Individual events are carried for the flagged pairs, the pairs with an "
            "event inside the notification box, and the highest-probability pairs; the parquet in the run "
            "directory holds every event of every pair.",
        ],
    }
    return bundle, tracks


def write_bundle(bundle: dict[str, Any], tracks: Tracks, out_dir: Path | None = None) -> dict[str, Path]:
    """Write ``conjunctions.json`` and ``conjunction-tracks.bin`` into the viewer's data directory."""
    out_dir = Path(out_dir or config.VIEWER_DATA_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "conjunctions.json"
    bin_path = out_dir / str(bundle["tracks"]["path"])
    json_path.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    bin_path.write_bytes(tracks.to_bytes())
    log.info(
        "Viewer conjunctions: %d events (%d with tracks) over %d pairs, %.1f kB JSON + %.1f kB tracks",
        bundle["n_events"],
        bundle["tracks"]["n_events"],
        bundle["n_pairs"],
        json_path.stat().st_size / 1024,
        bin_path.stat().st_size / 1024,
    )
    return {"json": json_path, "tracks": bin_path}


# --------------------------------------------------------------------------------------
# The weekly report


def _fmt_pc(value: float) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    return f"{value:.2e}"


def _fmt_flag(flag: str, confidence: str, region: str) -> str:
    if flag == "none":
        return "—"
    if flag == "unscoreable":
        return "**unscoreable**"
    if confidence == "low":
        return f"**{flag}** (low confidence, {region})"
    return f"**{flag}**"


def _verdicts(flagged: pd.DataFrame) -> list[str]:
    """One plain sentence per flagged pair saying which region it is in and what that means.

    The Phase 3 Step 0 review asked for this: the tables carry `region` and `confidence`
    in every row, but a reader should not have to decode a column to learn whether the
    week's red is a real geometry or an artefact of the uncertainty.
    """
    if not len(flagged):
        return ["## The flags, plainly", "", "No pair is flagged this week.", ""]
    lines = [
        "## The flags, plainly",
        "",
        "Every flagged pair, with the region of the event that raised the flag. **Robust** means the "
        "maximum of the probability over covariance scale factors sits at or above the covariance in "
        "hand, so the number is set by the geometry: worth a second look. **Dilution** means it sits "
        "below, so the probability is held up by the size of the uncertainty rather than by the "
        "geometry. A dilution flag is not actionable, and it is not a statement that the pair is safe "
        "either: at that lead time the catalogue cannot tell whether the two objects come close.",
        "",
    ]
    for _, p in flagged.sort_values("max_pc", ascending=False).iterrows():
        scale = p["pc_max_scale_at_max_pc"]
        scale_txt = f"{scale:.2f}×" if np.isfinite(scale) else "an unknown scale"
        verdict = {
            "robust": f"**robust** (maximum at {scale_txt} the covariance)",
            "dilution": f"**dilution**, not robust (maximum at {scale_txt} the covariance)",
        }.get(str(p["region"]), "**unclassified**: the covariance-scale sweep did not run")
        miss = p.get("miss_at_max_pc_km", p["closest_km"])
        lines.append(
            f"- **{p['primary_name']} versus {p['secondary_name']} ({int(p['secondary_norad_id'])})**: "
            f"{p['flag']} at `pc` {_fmt_pc(p['max_pc'])}, at a miss of {float(miss):.3f} km on "
            f"{pd.Timestamp(p['max_pc_tca']).strftime('%Y-%m-%d %H:%M')} UTC. {verdict}."
        )
    lines.append("")
    return lines


def _pair_rows(pairs: pd.DataFrame) -> list[str]:
    lines = [
        "| Primary | Secondary | Events | First TCA | Closest (km) | Highest Pc | Cumulative Pc | Max Pc | Flag |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, p in pairs.iterrows():
        lines.append(
            f"| {p['primary_name']} | {p['secondary_name']} ({int(p['secondary_norad_id'])}) "
            f"| {int(p['n_events'])} | {pd.Timestamp(p['first_tca']).strftime('%Y-%m-%d %H:%M')} "
            f"| {p['closest_km']:.3f} | {_fmt_pc(p['max_pc'])} | {_fmt_pc(p['pc_cumulative'])} "
            f"| {_fmt_pc(p['max_pc_max'])} | {_fmt_flag(p['flag'], p['confidence'], p['region'])} |"
        )
    return lines


def _event_details(rows: pd.DataFrame, pairs: pd.DataFrame, limit: int = 10) -> list[str]:
    """One collapsible block per pair listing its individual events (the "expand on demand" of the review)."""
    lines: list[str] = []
    for _, p in pairs.iterrows():
        events = rows[
            (rows["primary_norad_id"] == p["primary_norad_id"])
            & (rows["secondary_norad_id"] == p["secondary_norad_id"])
        ].sort_values("tca")
        shown = events.head(limit)
        more = len(events) - len(shown)
        lines.append("")
        lines.append(
            f"<details><summary>{p['primary_name']} vs {p['secondary_name']} "
            f"({int(p['n_events'])} events, closest {p['closest_km']:.3f} km)</summary>"
        )
        lines.append("")
        # The pre-storm miss is only worth a column when the storm term actually moved something;
        # under `quiet` it would be the same number twice.
        moved = bool((pd.to_numeric(events.get("relative_shift_km"), errors="coerce").fillna(0) > 0).any())
        miss_head = "Miss (km) | Before the storm (km)" if moved else "Miss (km)"
        miss_align = "---: | ---:" if moved else "---:"
        lines.append(f"| TCA | {miss_head} | Rel. speed (km/s) | R, I, C (km) | Pc | Max Pc (scale) | Region |")
        lines.append(f"| --- | {miss_align} | ---: | --- | ---: | ---: | --- |")
        for _, e in shown.iterrows():
            ric = f"{e['miss_r_km']:+.2f}, {e['miss_i_km']:+.2f}, {e['miss_c_km']:+.2f}"
            scale = f"{e['pc_max_scale']:.2f}" if np.isfinite(e["pc_max_scale"]) else "—"
            miss = f"{e['miss_scenario_km']:.3f}" + (f" | {e['miss_km']:.3f}" if moved else "")
            lines.append(
                f"| {pd.Timestamp(e['tca']).strftime('%Y-%m-%d %H:%M:%S')} | {miss} "
                f"| {e['rel_speed_kms']:.2f} | {ric} | {_fmt_pc(e['pc'])} | {_fmt_pc(e['pc_max'])} ({scale}) "
                f"| {e['region']} |"
            )
        if more > 0:
            lines.append(f"| … {more} more events |{' |' * (6 if moved else 5)} |")
        lines.append("")
        lines.append("</details>")
    return lines


def _validity_summary_rows(rows: pd.DataFrame) -> list[str]:
    """Two summary lines counting the events the storm-term validation does and does not reach."""
    if "storm_validity" not in rows.columns:
        return []
    counts = rows["storm_validity"].astype(str).value_counts()
    if not counts.drop(labels=["none"], errors="ignore").sum():
        return []
    return [
        f"| Events with the storm term validated (both coefficients measured) | {int(counts.get('validated', 0))} |",
        f"| Events with the storm term indicative only | {int(counts.get('indicative', 0))} |",
    ]


def _storm_rows(rows: pd.DataFrame, label: str) -> pd.DataFrame:
    """The subset of ``rows`` carrying one ``storm_validity`` label, or everything for ``combined``."""
    if label == "combined" or "storm_validity" not in rows.columns:
        return rows
    return rows[rows["storm_validity"].astype(str) == label]


def _storm_figures(rows: pd.DataFrame) -> dict[str, Any]:
    """What the storm term did to one population of events: shift size, direction, flags."""
    scoreable = rows[rows["flag"] != "unscoreable"] if "flag" in rows.columns else rows
    relative = pd.to_numeric(scoreable.get("relative_shift_km"), errors="coerce").to_numpy(dtype=float)
    moved = np.isfinite(relative) & (relative > 0)
    pc = pd.to_numeric(scoreable.get("pc"), errors="coerce").to_numpy(dtype=float)
    variance_only = pd.to_numeric(scoreable.get("pc_variance_only"), errors="coerce").to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(variance_only > 0, pc / variance_only, np.nan)
    comparable = np.isfinite(ratio) & (variance_only > 1e-12)
    return {
        "n_events": int(len(rows)),
        "n_unscoreable": int((rows["flag"] == "unscoreable").sum()) if "flag" in rows.columns else 0,
        "n_moved": int(moved.sum()),
        "median_relative_km": float(np.median(relative[moved])) if moved.any() else float("nan"),
        "p90_relative_km": float(np.quantile(relative[moved], 0.9)) if moved.any() else float("nan"),
        "n_comparable": int(comparable.sum()),
        "median_ratio": float(np.nanmedian(ratio[comparable])) if comparable.any() else float("nan"),
        "n_lowered": int(np.nansum(ratio[comparable] < 1.0)),
        "n_raised": int(np.nansum(ratio[comparable] > 1.0)),
        "n_red": int((rows["flag"] == "red").sum()) if "flag" in rows.columns else 0,
        "n_yellow": int((rows["flag"] == "yellow").sum()) if "flag" in rows.columns else 0,
    }


def _fmt_num(value: float, digits: int = 2) -> str:
    return "—" if value is None or not np.isfinite(value) else f"{value:.{digits}f}"


def storm_section(rows: pd.DataFrame, scenario: str) -> list[str]:
    """What the scenario's storm term did, reported over the validated and indicative events.

    Empty for a scenario with no storm layer. The order is fixed -- validated, indicative,
    combined -- and the combined column is never the only one, because Step 4 measured the term
    against the May 2024 record and found it predictive at r = 0.88 only where **both** objects
    have a ballistic coefficient fitted from their own decay. A median taken over a population
    that is mostly indicative reads as a measurement and is not one.
    """
    if "relative_shift_km" not in rows.columns or not len(rows):
        return []
    if not np.any(pd.to_numeric(rows["relative_shift_km"], errors="coerce").to_numpy(dtype=float) > 0):
        return []
    labels = ["validated", "indicative", "combined"]
    figures = {label: _storm_figures(_storm_rows(rows, label)) for label in labels}
    labels = [label for label in labels if figures[label]["n_events"]]

    header = " | ".join(f"{label} ({figures[label]['n_events']})" for label in labels)
    lines = [
        f"## What the `{scenario}` storm term did",
        "",
        "**Every figure here is given both ways.** `validated` means **both** objects of the event "
        "have a ballistic coefficient fitted from their own decay history; `indicative` means at "
        "least one rests on a B\\* inversion, a population stand-in, or no coefficient at all. Step 4 "
        "measured the storm term against the May 2024 record and found it predictive at a "
        "correlation of **0.88** for objects with a measured coefficient and of **no demonstrated "
        "skill** otherwise, so the split is the difference between a measurement and an "
        "extrapolation. Nothing is weighted, widened or withheld by the label — the numbers are "
        "identical either way, and the label says how far the validation reaches.",
        "",
        f"| | {header} |",
        "| --- | " + " | ".join(["---:"] * len(labels)) + " |",
    ]

    def row(name: str, key: str, fmt) -> str:
        return f"| {name} | " + " | ".join(fmt(figures[label][key]) for label in labels) + " |"

    lines += [
        row("Events moved by the shift", "n_moved", lambda v: f"{v:,}"),
        row("Median relative shift (km)", "median_relative_km", lambda v: _fmt_num(v, 2)),
        row("p90 relative shift (km)", "p90_relative_km", lambda v: _fmt_num(v, 1)),
        row("Median `pc` / `pc_variance_only`", "median_ratio", lambda v: _fmt_num(v, 3)),
        row("Events the shift lowered", "n_lowered", lambda v: f"{v:,}"),
        row("Events the shift raised", "n_raised", lambda v: f"{v:,}"),
        row("Flagged red", "n_red", lambda v: f"{v:,}"),
        row("Flagged yellow", "n_yellow", lambda v: f"{v:,}"),
        row("Not scored (outside the linear theory)", "n_unscoreable", lambda v: f"{v:,}"),
        "",
        "**How to read the ratio.** `pc` is the scenario's probability with both effects — the "
        "objects moved and the covariance widened. `pc_variance_only` is the same covariance with "
        "the objects left where their element sets put them. A median below one says the "
        "displacement is *protective* on most events, which is the counter-intuitive result the "
        "phase turns on and which `driftwatch storm-check` attacks rather than asserts.",
        "",
        "**The reason is not a cancellation between the two objects.** The relative displacement "
        "that reaches the miss is a median 1.91 times the mean of the two objects' own "
        "displacements, out of a maximum of 2: the two are nearly independent, because a "
        "conjunction is a crossing — a median 120° between the two in-track directions. What "
        "lowers most probabilities is simply that a displacement of tens of kilometres applied to "
        "a miss of a few separates more pairs than it creates. (Corrected 2026-09-03; Step 3 "
        "attributed the same result to common-mode cancellation and `docs/storm-term.md` carries "
        "the measurement that withdrew it.)",
        "",
    ]
    return lines


def weekly_report(run: RunDirectory, *, scenario: str | None = None, top_n: int = TOP_N) -> str:
    """The weekly markdown report for one scenario of a run."""
    info = run.read_run()
    joined = run.read_conjunctions()
    scenarios = sorted(str(s) for s in joined["scenario"].dropna().unique())
    scenario = scenario or (scenarios[0] if scenarios else "quiet")
    rows = normalise(joined[joined["scenario"] == scenario])
    rows["tca"] = pd.to_datetime(rows["tca"], utc=True)
    pairs = collapse_pairs(rows)
    cov = info.get("covariance", {})

    start = pd.Timestamp(info.get("start")).strftime("%Y-%m-%d %H:%M")
    end = pd.Timestamp(info.get("end")).strftime("%Y-%m-%d %H:%M")
    flagged = pairs[is_flagged(pairs["flag"])]
    n_unscoreable = int((rows["flag"] == "unscoreable").sum())
    actionable = flagged[flagged["confidence"] == "standard"]
    low = flagged[flagged["confidence"] == "low"]

    lines = [
        f"# Conjunction report: {info.get('fleet_name', 'fleet')}, {start} to {end} UTC",
        "",
        f"Run `{info.get('run_id')}` over snapshot `{info.get('snapshot')}`, scenario `{scenario}`, "
        f"covariance `{cov.get('model_version', '')}`.",
        "",
        "## What this is",
        "",
        "Every close approach between a fleet member and a catalogue object over the window, with a "
        "probability of collision built on an uncertainty estimated from how much each object's own "
        "element sets disagree. Repeated encounters of the same pair are collapsed to one row; the "
        "individual events are underneath each pair and in full in the parquet and JSON.",
        "",
        "## Summary",
        "",
        "| | |",
        "| --- | ---: |",
        f"| Events | {len(rows)} |",
        f"| Distinct pairs | {len(pairs)} |",
        f"| Events inside the notification box | {int(rows['in_box'].sum())} |",
        f"| Pairs flagged red | {int((pairs['flag'] == 'red').sum())} |",
        f"| Pairs flagged yellow | {int((pairs['flag'] == 'yellow').sum())} |",
        f"| Flagged pairs in the dilution region (low confidence) | {len(low)} |",
        f"| Flagged pairs in the robust region | {len(actionable)} |",
        f"| Events not scored (the storm term left its own derivation) | {n_unscoreable} |",
        *_validity_summary_rows(rows),
        f"| Closest approach | {rows['miss_scenario_km'].min():.3f} km |",
        f"| Highest probability | {_fmt_pc(rows['pc'].max())} |",
        "",
    ]
    lines += _verdicts(flagged)

    if len(actionable):
        lines += [
            "## Flagged, robust region",
            "",
            "These are the pairs where the geometry, not the size of the "
            "covariance, drives the number. They are the ones worth a second look.",
            "",
        ]
        lines += _pair_rows(actionable)
        lines += _event_details(rows, actionable)
        lines.append("")
    else:
        lines += [
            "## Flagged, robust region",
            "",
            "None. Every flag this week sits in the dilution region, where the probability is held up by the "
            "size of the covariance rather than by the geometry; see below.",
            "",
        ]

    if len(low):
        lines += [
            "## Flagged, dilution region (low confidence, not actionable)",
            "",
            "The maximum of the probability over covariance scale factors lies below the covariance actually "
            "used, so shrinking the uncertainty at the same miss would raise the probability. A flag here says "
            "the trajectories are uncertain, not that the objects are likely to collide, and it must not be "
            "acted on. It is equally not a statement that they are safe: the data cannot support a judgement "
            "either way. Better tracking would shrink the covariance and move the nominal miss at the same "
            "time, by a distance of the order of the uncertainty removed and in a direction nothing here can "
            "predict, so no claim is made about which way these would go.",
            "",
        ]
        lines += _pair_rows(low)
        lines += _event_details(rows, low)
        lines.append("")

    lines += storm_section(rows, scenario)

    top_pc = pairs.head(top_n)
    lines += [f"## Top {len(top_pc)} pairs by probability", ""]
    lines += _pair_rows(top_pc)
    lines.append("")

    top_miss = pairs.sort_values("closest_km").head(top_n)
    lines += [f"## Top {len(top_miss)} pairs by closest approach", ""]
    lines += _pair_rows(top_miss)
    lines.append("")

    per_primary = rows.groupby("primary_name").agg(
        events=("miss_km", "size"),
        pairs=("secondary_norad_id", "nunique"),
        in_box=("in_box", "sum"),
        closest_km=("miss_km", "min"),
        max_pc=("pc", "max"),
    )
    lines += [
        "## By fleet member",
        "",
        "| Member | Events | Distinct secondaries | In box | Closest (km) | Highest Pc |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in per_primary.iterrows():
        lines.append(
            f"| {name} | {int(r['events'])} | {int(r['pairs'])} | {int(r['in_box'])} "
            f"| {r['closest_km']:.3f} | {_fmt_pc(r['max_pc'])} |"
        )
    lines.append("")

    counts = rows["cov_source_secondary"].str.split(":").str[0].value_counts()
    sources = ", ".join(f"{n} {name}" for name, n in counts.items())
    supplemental = info.get("supplemental") or []
    lines += [
        "## How to read this",
        "",
        "- **The probability is not a forecast.** The covariance comes from how much each object's own "
        "element sets disagree after propagation, which is a floor on the error and not a measure of it "
        f"(`docs/screening.md`). Secondaries here: {sources}.",
        "- **Maximum probability and its scale.** `Max Pc` is the largest probability over covariance scale "
        "factors from 0.1 to 10, with the miss held fixed. Where its scale is above one the covariance is "
        "smaller than the miss and a larger uncertainty would raise the probability; where it is below one "
        "the event is in the dilution region and the flag is not actionable. The sweep is arithmetic on the "
        "numbers in hand, not a forecast of what a better orbit would give.",
        "- **Cumulative probability is an upper bound.** The events of a pair are repeated passes of the same "
        "two objects from the same two element sets, so they are not independent.",
        "- **The miss quoted is the one under this scenario.** Under `quiet` it is what the two element sets "
        "predicted. Under a storm scenario the term has moved both objects along track first, and this is the "
        "miss its probability was computed from; the per-event tables carry the pre-storm miss beside it, and "
        "the difference between the two is the storm's whole effect on the geometry.",
        "- **Manoeuvres are not predicted.** An object marked `known` or `observed` can move at any time, and "
        "no element set here knows about a burn that has not happened yet.",
    ]
    spacex_rows = int(rows["cov_source_secondary"].astype(str).str.startswith("spacex").sum())
    if spacex_rows:
        lines.append(
            f"- **{spacex_rows} events use SpaceX's own published covariance** for the Starlink secondary, "
            "inside the 72-hour horizon of the operator's ephemeris. It is much tighter than an estimate from "
            "element-set consistency, and it answers a different question: it is the uncertainty *within* one "
            "published plan, not the uncertainty *of the plan being revised*. One term is added to it: the "
            "0.2 km published residual of CelesTrak's SGP4 fit to that same ephemeris, in quadrature, because "
            "that fit is the trajectory being propagated here while their covariance describes the ephemeris. "
            "Past the horizon the covariance changes hands mid-window and `Cov source` says so."
        )
    slow = rows[rows["slow_encounter"]] if "slow_encounter" in rows.columns else rows.iloc[:0]
    if len(slow):
        flagged_slow = int(is_flagged(slow["flag"]).sum())
        lines.append(
            f"- **{len(slow)} of these events are slow encounters**, below "
            f"{SLOW_ENCOUNTER_KMS:g} km/s relative (slowest {slow['rel_speed_kms'].min():.3f} km/s), and "
            f"{flagged_slow or 'none'} of them {'is' if flagged_slow == 1 else 'are'} flagged. Their "
            "probability is a **known underestimate**: the two-dimensional method assumes the pair passes in "
            "a straight line at constant velocity, and a co-orbital pair does not. The flag rests on that "
            "assumption, not on a measured error — the ESA Kelvins reproduction agrees with the operational "
            "risk column on slow rows as closely as on fast ones, which cannot clear the method, because both "
            "tools compute the same two-dimensional integral and a bias they share is invisible to the "
            "comparison. Nothing here corrects for it; a three-dimensional integration would."
        )
    if supplemental:
        used = ", ".join(f"{s['name']} version {s['version']} ({s['n_applied']} objects)" for s in supplemental)
        lines.append(
            f"- **Operator ephemerides.** {used}. Those objects were screened on the operator's published "
            "trajectory rather than on tracking data, and their uncertainty comes from the consistency of "
            "successive supplemental versions."
        )
    sources = "Element sets from CelesTrak and Space-Track"
    if spacex_rows:
        sources += "; Starlink ephemerides published by SpaceX, used for analysis"
    lines += [
        "",
        f"Generated by driftwatch {__version__}. {sources}; "
        "see `docs/data-sources.md` for the attribution each requires.",
        "",
    ]
    return "\n".join(lines)


def write_report(run: RunDirectory, *, scenario: str | None = None, top_n: int = TOP_N) -> Path:
    """Write ``report.md`` into the run directory."""
    text = weekly_report(run, scenario=scenario, top_n=top_n)
    path = run.path / "report.md"
    path.write_text(text, encoding="utf-8")
    log.info("Wrote %s (%.1f kB)", path, path.stat().st_size / 1024)
    return path
