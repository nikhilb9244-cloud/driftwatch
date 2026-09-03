"""The warning-stability index: one narrow row per encounter per run, kept across runs.

**What it answers.** How a warning evolved. An operator's question before trusting a screening
service is not "what does it say today" but "what did it say yesterday, and the day before, and
did the flag it raised at three days survive to one". A daily pipeline is the only thing that can
answer that, and only if it keeps something. `docs/pipeline.md` records why every run is archived
for it; this file is the read path, so that following one pair does not mean downloading a month
of 4.8 MB run archives and opening them one by one.

**The hard part is identity, and it is why this cannot be a join on ``event_id``.** An event id is
``<snapshot stamp>:<primary>:<secondary>:<tca to the minute>``. The snapshot stamp changes daily
by construction and the time of closest approach itself moves by seconds to minutes as both
orbits are refitted, so **the same physical encounter has a different id in every run** and a join
on it finds nothing. A series is therefore assembled on

* the **object pair**, which is stable, and
* the **time of closest approach within a tolerance**
  (:data:`driftwatch.config.STABILITY_TCA_TOLERANCE_S`, ten minutes),

which is the same greedy nearest-time match the Step 1 comparison used, and delicate in the same
one place: a pair with repeated close passes. Successive passes of a pair are typically half an
orbit apart -- about 46 minutes in low Earth orbit -- so ten minutes separates them cleanly, and
every matched row carries the ``dt_tca_s`` it was matched on so that the tolerance can be checked
against what the runs actually do rather than defended from this docstring.

**What is in it, and what is deliberately not.**

* **Every event, not the flagged ones.** Measured over two runs of the demo fleet, flagged events
  have miss distances from 0.53 km to 28.3 km -- the whole screening volume. The flag is decided
  by the covariance, not by the miss, so there is no miss-distance cut that admits the warnings
  and drops the rest, and an event admitted only once it flags has no history to compare against
  on the day it flags. That is the whole failure this file exists to avoid.
* **The scenarios that are statements about the actual window**
  (:data:`driftwatch.config.STABILITY_SCENARIOS`: ``quiet`` and ``forecast``). ``storm-g3`` and
  its siblings are what-ifs -- their run-to-run movement is a property of the scenario definition,
  not of a warning -- and they double the index for a question the archive can still answer.
* **No ``event_id``.** The index carries the snapshot, the pair and the tca, which is exactly what
  an event id is made of, so it can be reconstructed to go back to the archive; storing it costs
  15 % of the file to repeat that.
* **No analysis.** Survival rates, false-alarm rates and lead-time curves are not computed here
  and there is no viewer panel. This is the storage and the read path only.

**Where it lives.** ``data/stability/<fleet>/<run_id>.parquet``, on the ``pipeline-store`` branch
with the other accumulating state -- **not** in the release-asset archive, because the point is to
read a year of it without downloading a year of runs. One immutable file per run rather than one
growing file rewritten daily: git stores every version of a rewritten file in full, so a monthly
file rewritten each day costs an order of magnitude more history than the same bytes written once.
Measured on the 2026-09-03 demo run: **330 KB a run** for two scenarios over 6,224 events, against
8.6 MB a day for the run and its snapshot -- 4 % of the archive it saves you from reading.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import __version__, config
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.orbit.time import parse_utc, stamp

log = logging.getLogger(__name__)

# One row per (series, run, scenario). Identity first, then the run it was seen in, then the
# geometry, then the score. Types are chosen for the file rather than for the arithmetic: the
# index is read whole and often, and a float32 miss distance is a millimetre at 25 km.
COLUMNS: tuple[str, ...] = (
    "series_id",
    "fleet",
    "primary_norad_id",
    "secondary_norad_id",
    "run_id",
    "run_start",
    "snapshot",
    "snapshot_fetched_at",
    "obs_index",
    "scenario",
    "tca",
    "lead_s",
    "dt_tca_s",
    "miss_km",
    "pc",
    "pc_max",
    "flag",
    "scoreable",
    "unscoreable_reason",
    "slow_encounter",
    "storm_validity",
    "cov_source_primary",
    "cov_source_secondary",
    "primary_trajectory",
    "secondary_trajectory",
)

# Columns the matcher needs out of an earlier run's file. Reading five columns rather than
# twenty-five is the difference between opening ten files and opening ten megabytes.
_MATCH_COLUMNS: tuple[str, ...] = ("series_id", "primary_norad_id", "secondary_norad_id", "run_start", "tca")


def series_id(primary: int, secondary: int, first_tca: datetime | pd.Timestamp) -> str:
    """``55053-61705-20260904T1018Z``: the pair and the time of closest approach *when first seen*.

    Anchored to the first sighting and never recomputed, so the id of a series does not move when
    its time of closest approach does -- which is the whole reason a series exists.
    """
    t = pd.Timestamp(first_tca).tz_convert("UTC") if pd.Timestamp(first_tca).tzinfo else pd.Timestamp(first_tca)
    return f"{int(primary)}-{int(secondary)}-{t.strftime('%Y%m%dT%H%MZ')}"


@dataclass(frozen=True)
class AppendResult:
    """What one run added to the index, for the run record and the console."""

    fleet: str
    run_id: str
    path: str
    n_events: int
    n_rows: int
    scenarios: list[str] = field(default_factory=list)
    n_new: int = 0
    n_continued: int = 0
    n_not_seen: int = 0
    n_candidates: int = 0
    dt_tca_s: dict[str, float] | None = None
    tolerance_s: float = 0.0
    bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_scenarios(run: RunDirectory, wanted: list[str] | None) -> list[str]:
    """The stored scenarios this index wants, in the order the run stored them."""
    stored = run.scenarios()
    ask = list(wanted) if wanted else list(config.STABILITY_SCENARIOS)
    keep = [s for s in stored if s in ask]
    missing = [s for s in ask if s not in stored]
    if missing:
        log.info("Stability: %s not scored in this run; indexing %s", ", ".join(missing), ", ".join(keep) or "nothing")
    return keep


def _match(new: pd.DataFrame, previous: pd.DataFrame, tolerance_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Greedy nearest-time match of this run's events to open series, one to one.

    Returns, per row of ``new``: the matched series id (or ``None``), the previous observation
    index, and the seconds the time of closest approach moved. Candidates are only ever the same
    object pair inside the tolerance, so there are few of them and the greedy loop is cheap.
    """
    n = len(new)
    matched = np.full(n, None, dtype=object)
    prev_index = np.full(n, -1, dtype=np.int64)
    dt = np.full(n, np.nan, dtype=np.float64)
    if previous.empty or n == 0:
        return matched, prev_index, dt

    cand = new.reset_index(names="_row").merge(
        previous, on=["primary_norad_id", "secondary_norad_id"], suffixes=("", "_prev")
    )
    if cand.empty:
        return matched, prev_index, dt
    cand["_dt"] = (cand["tca"] - cand["tca_prev"]).dt.total_seconds()
    cand = cand[cand["_dt"].abs() <= tolerance_s]
    # Nearest first, so that when two events of one pair both fall inside the tolerance of one
    # series the closer of them takes it and the other starts its own.
    cand = cand.reindex(cand["_dt"].abs().sort_values(kind="stable").index)

    used_rows: set[int] = set()
    used_series: set[str] = set()
    for row, sid, obs, delta in zip(
        cand["_row"].to_numpy(),
        cand["series_id"].to_numpy(),
        cand["obs_index"].to_numpy(),
        cand["_dt"].to_numpy(),
        strict=True,
    ):
        if int(row) in used_rows or sid in used_series:
            continue
        used_rows.add(int(row))
        used_series.add(sid)
        matched[int(row)] = sid
        prev_index[int(row)] = int(obs)
        dt[int(row)] = float(delta)
    return matched, prev_index, dt


class StabilityIndex:
    """The per-fleet index under ``data/stability``. One file per run; nothing is rewritten."""

    def __init__(self, path: Path | None = None) -> None:
        self.root = Path(path or config.STABILITY_DIR)

    def fleet_dir(self, fleet: str) -> Path:
        return self.root / fleet

    def files(self, fleet: str) -> list[Path]:
        """Every stored run's file for this fleet, oldest first (the run id sorts by time)."""
        return sorted(self.fleet_dir(fleet).glob("*.parquet"))

    def latest_observations(
        self, fleet: str, *, exclude_run_id: str | None = None, limit: int | None = None
    ) -> pd.DataFrame:
        """One row per open series: the most recent observation of it, for the matcher.

        Only the last :data:`driftwatch.config.STABILITY_LOOKBACK_RUNS` files are read. A series
        can only be matched by an event inside this run's window, and the window is a week, so a
        series last seen more than a lookback of daily runs ago is closed by construction.
        """
        files = self.files(fleet)
        if exclude_run_id:
            files = [p for p in files if p.stem != exclude_run_id]
        files = files[-(limit or config.STABILITY_LOOKBACK_RUNS) :]
        frames = []
        for path in files:
            try:
                frame = pq.read_table(path, columns=list(_MATCH_COLUMNS + ("obs_index",))).to_pandas()
            except (OSError, pa.ArrowInvalid, KeyError) as exc:  # pragma: no cover - corrupt file
                log.warning("Stability: cannot read %s (%s); it is skipped for matching", path, exc)
                continue
            frames.append(frame)
        if not frames:
            return pd.DataFrame(columns=[*_MATCH_COLUMNS, "obs_index"])
        rows = pd.concat(frames, ignore_index=True)
        rows["tca"] = pd.to_datetime(rows["tca"], utc=True)
        rows["run_start"] = pd.to_datetime(rows["run_start"], utc=True)
        rows = rows.sort_values(["series_id", "run_start"]).drop_duplicates("series_id", keep="last")
        return rows.reset_index(drop=True)

    def append_run(
        self,
        run: RunDirectory,
        *,
        scenarios: list[str] | None = None,
        tolerance_s: float | None = None,
        dry_run: bool = False,
    ) -> AppendResult:
        """Index one scored run: match its events to open series and write this run's file."""
        info = run.read_run()
        fleet = str(info.get("fleet_name") or "fleet")
        run_id = str(info.get("run_id") or run.name)
        start = parse_utc(str(info["start"]))
        tolerance = float(tolerance_s if tolerance_s is not None else config.STABILITY_TCA_TOLERANCE_S)
        names = _read_scenarios(run, scenarios)
        if not names:
            raise StabilityError(f"{run.name}: none of {scenarios or list(config.STABILITY_SCENARIOS)} is scored here")

        events = run.read_events()
        base = events[["event_id", "primary_norad_id", "secondary_norad_id", "tca", "miss_km"]].copy()
        # A run screened before Phase 4 Step 1 has no trajectory columns. It is still a real
        # observation of the same encounters, and refusing to index it would put a hole in exactly
        # the series that span the change. The columns become nulls, which is what they mean.
        for column in ("primary_trajectory", "secondary_trajectory"):
            base[column] = (
                events[column].astype("string")
                if column in events
                else pd.Series(pd.NA, index=events.index, dtype="string")
            )
        base = base.sort_values(["primary_norad_id", "secondary_norad_id", "tca"]).reset_index(drop=True)

        previous = self.latest_observations(fleet, exclude_run_id=run_id)
        matched, prev_index, dt = _match(base, previous, tolerance)
        first_tca = base["tca"].to_numpy()
        ids = np.array(
            [
                sid
                if sid is not None
                else series_id(
                    int(p),
                    int(s),
                    pd.Timestamp(t).tz_localize("UTC") if pd.Timestamp(t).tzinfo is None else pd.Timestamp(t),
                )
                for sid, p, s, t in zip(
                    matched,
                    base["primary_norad_id"].to_numpy(),
                    base["secondary_norad_id"].to_numpy(),
                    first_tca,
                    strict=True,
                )
            ],
            dtype=object,
        )
        base["series_id"] = pd.Series(ids, dtype="string")
        base["obs_index"] = (prev_index + 1).astype("int16")
        base["dt_tca_s"] = dt.astype("float32")

        seen = set(base.loc[base["obs_index"] > 0, "series_id"].tolist())
        open_in_window = previous[
            (previous["tca"] >= start - pd.Timedelta(seconds=tolerance))
            & (previous["tca"] <= parse_utc(str(info["end"])) + pd.Timedelta(seconds=tolerance))
        ]
        n_not_seen = int((~open_in_window["series_id"].isin(seen)).sum())

        snapshot_name = str(info.get("snapshot") or "")
        fetched_at = _snapshot_fetched_at(snapshot_name)
        rows = pd.concat(
            [self._rows(run, base, name, fleet, run_id, start, snapshot_name, fetched_at) for name in names]
        )
        rows = rows.sort_values(["primary_norad_id", "secondary_norad_id", "tca", "scenario"]).reset_index(drop=True)

        path = self.fleet_dir(fleet) / f"{run_id}.parquet"
        finite = dt[np.isfinite(dt)]
        result = AppendResult(
            fleet=fleet,
            run_id=run_id,
            path=str(path),
            n_events=len(base),
            n_rows=len(rows),
            scenarios=names,
            n_new=int((base["obs_index"] == 0).sum()),
            n_continued=int((base["obs_index"] > 0).sum()),
            n_not_seen=n_not_seen,
            n_candidates=int(len(previous)),
            dt_tca_s=(
                {
                    "median_abs": round(float(np.median(np.abs(finite))), 1),
                    "p95_abs": round(float(np.percentile(np.abs(finite), 95)), 1),
                    "max_abs": round(float(np.max(np.abs(finite))), 1),
                }
                if finite.size
                else None
            ),
            tolerance_s=tolerance,
        )
        if dry_run:
            return result

        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(rows, preserve_index=False)
        table = table.replace_schema_metadata(
            {
                **(table.schema.metadata or {}),
                b"driftwatch_version": __version__.encode(),
                b"driftwatch_run_id": run_id.encode(),
                b"driftwatch_fleet": fleet.encode(),
                b"driftwatch_snapshot": snapshot_name.encode(),
                b"driftwatch_tca_tolerance_s": str(tolerance).encode(),
            }
        )
        pq.write_table(table, path, compression="zstd")
        result = AppendResult(**{**result.to_dict(), "bytes": path.stat().st_size})
        log.info(
            "Stability: %d rows (%d events x %d scenarios) -> %s (%.0f KB); %d new series, %d continued, "
            "%d open series not seen this run",
            result.n_rows,
            result.n_events,
            len(names),
            path,
            result.bytes / 1024.0,
            result.n_new,
            result.n_continued,
            result.n_not_seen,
        )
        return result

    def _rows(
        self,
        run: RunDirectory,
        base: pd.DataFrame,
        scenario: str,
        fleet: str,
        run_id: str,
        start: datetime,
        snapshot_name: str,
        fetched_at: pd.Timestamp,
    ) -> pd.DataFrame:
        """One scenario's rows: the run's geometry with that scenario's score joined on."""
        risk = run.read_risk(scenario)
        cols = [
            c
            for c in (
                "event_id",
                "pc",
                "pc_max",
                "flag",
                "scoreable",
                "unscoreable_reason",
                "slow_encounter",
                "storm_validity",
                "cov_source_primary",
                "cov_source_secondary",
            )
            if c in risk.columns
        ]
        joined = base.merge(risk[cols], on="event_id", how="left")
        out = pd.DataFrame(
            {
                "series_id": joined["series_id"].astype("string"),
                "fleet": pd.Series([fleet] * len(joined), dtype="string"),
                "primary_norad_id": joined["primary_norad_id"].astype("int32"),
                "secondary_norad_id": joined["secondary_norad_id"].astype("int32"),
                "run_id": pd.Series([run_id] * len(joined), dtype="string"),
                "run_start": pd.Series([pd.Timestamp(start)] * len(joined), dtype="datetime64[us, UTC]"),
                "snapshot": pd.Series([snapshot_name] * len(joined), dtype="string"),
                "snapshot_fetched_at": pd.Series([fetched_at] * len(joined), dtype="datetime64[us, UTC]"),
                "obs_index": joined["obs_index"].astype("int16"),
                "scenario": pd.Series([scenario] * len(joined), dtype="string"),
                "tca": joined["tca"].astype("datetime64[us, UTC]"),
                "lead_s": ((joined["tca"] - pd.Timestamp(start)).dt.total_seconds()).astype("int32"),
                "dt_tca_s": joined["dt_tca_s"].astype("float32"),
                "miss_km": joined["miss_km"].astype("float32"),
            }
        )
        for name, dtype in (("pc", "float32"), ("pc_max", "float32")):
            out[name] = joined[name].astype(dtype) if name in joined else np.float32(np.nan)
        for name in ("flag", "unscoreable_reason", "storm_validity", "cov_source_primary", "cov_source_secondary"):
            missing = pd.Series([pd.NA] * len(joined), dtype="string")
            out[name] = joined[name].astype("string") if name in joined else missing
        for name in ("scoreable", "slow_encounter"):
            missing = pd.Series([pd.NA] * len(joined), dtype="boolean")
            out[name] = joined[name].astype("boolean") if name in joined else missing
        for name in ("primary_trajectory", "secondary_trajectory"):
            out[name] = joined[name].astype("string")
        out["snapshot_fetched_at"] = out["snapshot_fetched_at"].astype("datetime64[us, UTC]")
        return out[list(COLUMNS)]

    # the read path ---------------------------------------------------------------------

    def read(
        self,
        fleet: str,
        *,
        series: str | None = None,
        pair: tuple[int, int] | None = None,
        scenario: str | None = None,
    ) -> pd.DataFrame:
        """The history of one series, one pair, or the whole index, oldest run first.

        This is the read path the index exists for: following one warning across a month of runs
        costs the index's files, not the month of 4.8 MB run archives they were derived from.
        """
        files = self.files(fleet)
        if not files:
            return pd.DataFrame(columns=list(COLUMNS))
        # Pushed into the read rather than applied after it. The rows are written sorted by pair,
        # so parquet's own row-group statistics skip most of a file for a pair query, and a year
        # of files stays a cheap read rather than a year of frames concatenated and thrown away.
        filters: list[tuple[str, str, Any]] = []
        if series:
            filters.append(("series_id", "==", series))
        if pair:
            filters.append(("primary_norad_id", "==", int(pair[0])))
            filters.append(("secondary_norad_id", "==", int(pair[1])))
        if scenario:
            filters.append(("scenario", "==", scenario))
        frames = []
        for path in files:
            frame = pq.read_table(path, filters=filters or None).to_pandas()
            if len(frame):
                frames.append(frame)
        if not frames:
            return pd.DataFrame(columns=list(COLUMNS))
        rows = pd.concat(frames, ignore_index=True)
        for column in ("run_start", "tca", "snapshot_fetched_at"):
            rows[column] = pd.to_datetime(rows[column], utc=True)
        return rows.sort_values(["series_id", "scenario", "run_start"]).reset_index(drop=True)

    def summary(self, fleet: str) -> dict[str, Any]:
        """What the index holds for this fleet, without reading the rows."""
        files = self.files(fleet)
        total = sum(p.stat().st_size for p in files)
        return {
            "fleet": fleet,
            "path": str(self.fleet_dir(fleet)),
            "n_runs": len(files),
            "bytes": total,
            "first_run": files[0].stem if files else None,
            "last_run": files[-1].stem if files else None,
        }


class StabilityError(RuntimeError):
    """A run cannot be indexed."""


def _snapshot_fetched_at(name: str) -> pd.Timestamp:
    """The snapshot's own fetch time, or NaT if it cannot be resolved from here.

    Read from the snapshot rather than from its file name, the same rule ``check-run`` follows,
    so that a renamed file cannot put a false age in the index. The pipeline runs ``check-run``
    before this, so an unresolvable snapshot has already failed the run; indexing does not fail
    a second time for it.
    """
    from driftwatch.cli import snapshot_file  # circular at import time: the CLI imports this module

    if not name:
        return pd.NaT
    try:
        from driftwatch.catalogue import snapshot as snapshot_mod

        return pd.Timestamp(snapshot_mod.snapshot_fetched_at(snapshot_file(name)))
    except (FileNotFoundError, OSError, KeyError, ValueError) as exc:
        log.warning("Stability: snapshot %r cannot be read for its fetch time (%s)", name, exc)
        return pd.NaT


def format_series(rows: pd.DataFrame) -> str:
    """One series as a table, newest run last: the lead time, the miss, the probability, the flag."""
    if rows.empty:
        return "No observations."
    out = []
    for sid, group in rows.groupby("series_id", sort=True):
        for scenario, series in group.groupby("scenario", sort=True):
            head = series.iloc[0]
            out.append(
                f"{sid}  {int(head['primary_norad_id'])} vs {int(head['secondary_norad_id'])}  "
                f"scenario {scenario}  {len(series)} runs"
            )
            out.append(f"{'run':>24}  {'lead':>8}  {'tca':>17}  {'dtca s':>8}  {'miss km':>9}  {'pc':>10}  flag")
            for row in series.itertuples():
                lead = f"{row.lead_s / 86400.0:.2f} d"
                pc = "-" if pd.isna(row.pc) else f"{row.pc:.3e}"
                dt = "-" if pd.isna(row.dt_tca_s) else f"{row.dt_tca_s:+.0f}"
                out.append(
                    f"{row.run_id:>24}  {lead:>8}  {stamp(pd.Timestamp(row.tca).to_pydatetime()):>17}  "
                    f"{dt:>8}  {row.miss_km:9.3f}  {pc:>10}  {row.flag or '-'}"
                )
            out.append("")
    return "\n".join(out)
