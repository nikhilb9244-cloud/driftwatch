"""The run directory: what a screening run writes under ``data/conjunctions/<fleet>_<start>/``.

Geometry and probability are kept apart (the Phase 3 design rule). One directory per
run holds:

``run.json``               the snapshot, the fleet, the configuration, the summary and the timings;
``events.parquet``         Stages A to C: one row per event with the geometry and both TEME states at TCA;
``objects.parquet``        one row per object in any event plus the fleet: element set used, hard-body
                           radius, manoeuvre level, history counts, covariance source;
``covariance.parquet``     the fitted covariance model (per object, per pool, defaults);
``risk_<scenario>.parquet`` one row per event for that scenario: sigmas, sources, probabilities, flags;
``conjunctions.parquet``   the joined export decided at the Step 0 review: one row per event per
                           scenario with every column, rebuilt from the files above.

A scenario rerun writes its ``risk_*`` file and rebuilds the join; it never touches the
events. Step 4 adds the JSON and the markdown report beside these.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import __version__, config
from driftwatch.orbit.time import stamp

log = logging.getLogger(__name__)

EXPORT_COLUMNS: tuple[str, ...] = (
    "run_id",
    "snapshot",
    "model_version",
    "scenario",
    "event_id",
    "primary_norad_id",
    "primary_name",
    "primary_category",
    "secondary_norad_id",
    "secondary_name",
    "secondary_category",
    "tca",
    "miss_km",
    "rel_speed_kms",
    "miss_r_km",
    "miss_i_km",
    "miss_c_km",
    "in_box",
    "within_watch_radius",
    "sigma_r_primary_km",
    "sigma_i_primary_km",
    "sigma_c_primary_km",
    "sigma_r_secondary_km",
    "sigma_i_secondary_km",
    "sigma_c_secondary_km",
    "cov_source_primary",
    "cov_source_secondary",
    "hbr_m",
    "pc",
    "pc_alfano",
    "pc_chan",
    "pc_max",
    "pc_max_scale",
    "region",
    "flag",
    "confidence",
    "slow_encounter",
    "stale_primary",
    "stale_secondary",
    "manoeuvre_primary",
    "manoeuvre_secondary",
    "secondary_ephemeris",
    "refine_method",
    "enc_cov_xx_km2",
    "enc_cov_xy_km2",
    "enc_cov_yy_km2",
)


def scenario_file_name(scenario: str) -> str:
    """``risk_quiet.parquet``; a ``replay:may2024`` scenario becomes ``risk_replay-may2024.parquet``."""
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in scenario)
    return f"risk_{safe}.parquet"


def _write(df: pd.DataFrame, path: Path, metadata: Mapping[str, str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    meta = {b"driftwatch_version": __version__.encode()}
    for key, value in (metadata or {}).items():
        meta[key.encode()] = value.encode()
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **meta})
    pq.write_table(table, path, compression="zstd")
    return path


def _read(path: Path) -> pd.DataFrame:
    return pq.read_table(path).to_pandas()


class RunDirectory:
    """Paths and read/write helpers for one run under ``data/conjunctions``."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @classmethod
    def for_run(cls, fleet_name: str, start: datetime, out_dir: Path | None = None) -> RunDirectory:
        return cls(Path(out_dir or config.CONJUNCTION_DIR) / f"{fleet_name}_{stamp(start)}")

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def run_json(self) -> Path:
        return self.path / "run.json"

    @property
    def events_path(self) -> Path:
        return self.path / "events.parquet"

    @property
    def objects_path(self) -> Path:
        return self.path / "objects.parquet"

    @property
    def covariance_path(self) -> Path:
        return self.path / "covariance.parquet"

    @property
    def conjunctions_path(self) -> Path:
        return self.path / "conjunctions.parquet"

    def risk_path(self, scenario: str) -> Path:
        return self.path / scenario_file_name(scenario)

    def scenarios(self) -> list[str]:
        """Scenario names of the risk files present, read from each file's metadata."""
        out = []
        for p in sorted(self.path.glob("risk_*.parquet")):
            meta = pq.read_metadata(p).metadata or {}
            out.append(meta.get(b"driftwatch_scenario", b"").decode() or p.stem[len("risk_") :])
        return out

    # run.json ---------------------------------------------------------------------

    def write_run(self, info: Mapping[str, Any]) -> Path:
        self.path.mkdir(parents=True, exist_ok=True)
        payload = {"driftwatch_version": __version__, "written_at": datetime.now(UTC).isoformat(), **info}
        self.run_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return self.run_json

    def read_run(self) -> dict[str, Any]:
        return json.loads(self.run_json.read_text(encoding="utf-8"))

    def update_run(self, **fields: Any) -> dict[str, Any]:
        info = self.read_run() if self.run_json.exists() else {}
        info.update(fields)
        self.write_run(info)
        return info

    # tables ------------------------------------------------------------------------

    def write_events(self, events: pd.DataFrame, *, snapshot: str, metadata: Mapping[str, str] | None = None) -> Path:
        return _write(events, self.events_path, {"driftwatch_snapshot": snapshot, **(metadata or {})})

    def read_events(self) -> pd.DataFrame:
        df = _read(self.events_path)
        df["tca"] = pd.to_datetime(df["tca"], utc=True)
        return df

    def write_objects(self, objects: pd.DataFrame) -> Path:
        return _write(objects, self.objects_path)

    def read_objects(self) -> pd.DataFrame:
        df = _read(self.objects_path)
        df["epoch"] = pd.to_datetime(df["epoch"], utc=True)
        df["last_jump"] = pd.to_datetime(df["last_jump"], utc=True)
        # Parquet stores the list of jump epochs in UTC; pandas hands them back as naive datetime64 values.
        df["jump_epochs"] = df["jump_epochs"].map(
            lambda v: [pd.Timestamp(t).tz_localize("UTC") for t in (v if v is not None else [])]
        )
        return df

    def write_covariance(self, table: pd.DataFrame, *, metadata: Mapping[str, str] | None = None) -> Path:
        return _write(table, self.covariance_path, metadata)

    def read_covariance(self) -> pd.DataFrame:
        return _read(self.covariance_path)

    @property
    def ballistic_path(self) -> Path:
        return self.path / "ballistic.parquet"

    def write_ballistic(self, table: pd.DataFrame, *, metadata: Mapping[str, str] | None = None) -> Path:
        """The ballistic coefficient per object (Phase 3 Step 2), fitted once and reused per scenario."""
        return _write(table, self.ballistic_path, metadata)

    def read_ballistic(self) -> pd.DataFrame:
        return _read(self.ballistic_path)

    def write_risk(self, rows: pd.DataFrame, scenario: str) -> Path:
        return _write(rows, self.risk_path(scenario), {"driftwatch_scenario": scenario})

    def read_risk(self, scenario: str) -> pd.DataFrame:
        df = _read(self.risk_path(scenario))
        df["computed_at"] = pd.to_datetime(df["computed_at"], utc=True)
        return df

    # the join ----------------------------------------------------------------------

    def rebuild_conjunctions(self) -> pd.DataFrame:
        """Join events, objects and every risk file into ``conjunctions.parquet`` (one row per event per scenario)."""
        events = self.read_events()
        objects = self.read_objects()
        risks = [self.read_risk(s) for s in self.scenarios()]
        joined = join_conjunctions(events, objects, risks)
        _write(joined, self.conjunctions_path)
        log.info("Wrote %d rows (%d scenarios) to %s", len(joined), len(risks), self.conjunctions_path)
        return joined

    def read_conjunctions(self) -> pd.DataFrame:
        df = _read(self.conjunctions_path)
        df["tca"] = pd.to_datetime(df["tca"], utc=True)
        return df


def join_conjunctions(events: pd.DataFrame, objects: pd.DataFrame, risks: list[pd.DataFrame]) -> pd.DataFrame:
    """The export decided at the Step 0 review: events joined with the manoeuvre levels and each scenario's risk rows.

    With no risk files the geometry rows are returned with the risk columns empty and
    ``scenario`` null, so a geometry-only run still exports.
    """
    levels = objects.set_index("norad_id")["manoeuvre_level"]
    base = events.copy()
    base["manoeuvre_primary"] = levels.reindex(base["primary_norad_id"]).fillna("none").to_numpy()
    base["manoeuvre_secondary"] = levels.reindex(base["secondary_norad_id"]).fillna("none").to_numpy()
    if risks:
        risk = pd.concat(risks, ignore_index=True)
        joined = risk.merge(base, on="event_id", how="left", validate="many_to_one")
    else:
        joined = base.copy()
    for col in EXPORT_COLUMNS:
        if col not in joined.columns:
            joined[col] = None
    joined = joined[list(EXPORT_COLUMNS)]
    sort_cols = ["scenario", "primary_norad_id", "tca"] if risks else ["primary_norad_id", "tca"]
    return joined.sort_values(sort_cols).reset_index(drop=True)
