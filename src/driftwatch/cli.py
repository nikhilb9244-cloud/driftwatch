"""Command-line interface: fetch, propagate, snapshots, history, fleet, screen, risk and kelvins."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import __version__, config
from driftwatch.catalogue import celestrak, history, satcat, snapshot, spacetrack
from driftwatch.ephemeris import spacex
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.export.report import build_bundle, write_bundle, write_report
from driftwatch.export.viewer import export_viewer_bundle
from driftwatch.fleet import Fleet, FleetError, load_fleet, resolve_fleet
from driftwatch.orbit import frames, propagator
from driftwatch.orbit.time import parse_utc, stamp
from driftwatch.risk import kelvins as kelvins_mod
from driftwatch.risk.covariance import (
    CovarianceFit,
    CovarianceModel,
    EmpiricalCovariance,
    ObjectRef,
    ScaledCovariance,
    SupplementalCovariance,
    fit_covariance,
    fit_supplemental_covariance,
    label_cov_sources,
    sigma_table,
)
from driftwatch.risk.scenario import (
    apply_history,
    model_version_string,
    new_run_id,
    objects_from_snapshot,
    refresh_hard_body_radii,
    run_risk,
)
from driftwatch.screening import ScreeningConfig, ScreeningError, ScreeningResult, screen_fleet
from driftwatch.screening import supplemental as supplemental_mod
from driftwatch.weather import celestrak_sw, helioviewer, swpc
from driftwatch.weather import table as weather_table

log = logging.getLogger("driftwatch")


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch (or reuse cached) groups and SATCAT, then write a snapshot."""
    groups = tuple(g.strip() for g in args.groups.split(",") if g.strip()) if args.groups else config.DEFAULT_GROUPS
    now = datetime.now(UTC)
    results = celestrak.fetch_groups(groups, cache_dir=config.CACHE_DIR, now=now, offline=args.offline)
    for res in results:
        log.info("%-22s %6d objects  %s", res.group, res.n_objects, "cache" if res.from_cache else "downloaded")

    satcat_df = None
    if not args.no_satcat:
        try:
            satcat_df = satcat.load_satcat(
                satcat.fetch_satcat(cache_dir=config.CACHE_DIR, now=now, offline=args.offline)
            )
        except FileNotFoundError as exc:
            log.warning("SATCAT unavailable (%s); object types will be UNK", exc)

    extra_sources: dict[str, list] = {}
    if args.spacetrack != "off":
        try:
            st = spacetrack.fetch_gp_catalogue(cache_dir=config.CACHE_DIR, now=now, offline=args.offline)
        except (spacetrack.SpaceTrackAuthError, FileNotFoundError) as exc:
            if args.spacetrack == "on":
                log.error("Space-Track required (--spacetrack on) but unavailable: %s", exc)
                return 2
            log.warning("Space-Track skipped (%s); the snapshot is CelesTrak only", exc)
        else:
            log.info("%-22s %6d objects  %s", "spacetrack gp", st.n_objects, "cache" if st.from_cache else "downloaded")
            extra_sources["spacetrack"] = spacetrack.load_gp_records(config.CACHE_DIR)

    records = {res.group: celestrak.load_group_records(res.group, config.CACHE_DIR) for res in results}
    df = snapshot.build_snapshot(records, satcat_df, fetched_at=now, extra_sources=extra_sources)
    path = snapshot.write_snapshot(df, snapshot.snapshot_path(now, config.SNAPSHOT_DIR), groups=groups)
    summary = snapshot.snapshot_summary(df)
    log.info("Snapshot %s: %d objects", path.name, summary["n_objects"])
    log.info("By category: %s", summary["by_category"])
    log.info("By band: %s", summary["by_band"])
    log.info("By source: %s", summary["by_source"])
    if extra_sources:
        in_celestrak = df["groups"].map(len) > 0
        added = df[~in_celestrak]
        log.info(
            "Space-Track adds %d objects in no CelesTrak group; by category %s; by band %s",
            len(added),
            {k: int(v) for k, v in added["category"].value_counts().sort_index().items()},
            {k: int(v) for k, v in added["altitude_band"].value_counts().sort_index().items()},
        )
        fresher = int(((df["source"] == "spacetrack") & in_celestrak).sum())
        log.info("%d objects also in CelesTrak took a fresher Space-Track element set", fresher)
    log.info(
        "Element-set age (days): median %.2f, p90 %.2f, max %.1f",
        summary["epoch_age_days"]["median"],
        summary["epoch_age_days"]["p90"],
        summary["epoch_age_days"]["max"],
    )
    print(path)
    return 0


def _state_frame(df: pd.DataFrame, state: propagator.PropagatedState, at: datetime) -> pd.DataFrame:
    r_teme, v_teme, error = state.at_index(0)
    r_itrs, v_itrs = frames.teme_to_itrs(r_teme, v_teme, at)
    lat, lon, height = frames.itrs_to_geodetic(r_itrs)
    out = pd.DataFrame(
        {
            "norad_id": df["norad_id"].to_numpy(),
            "name": df["name"].to_numpy(),
            "category": df["category"].to_numpy(),
            "t": pd.Timestamp(at),
            "x_teme_km": r_teme[:, 0],
            "y_teme_km": r_teme[:, 1],
            "z_teme_km": r_teme[:, 2],
            "vx_teme_kms": v_teme[:, 0],
            "vy_teme_kms": v_teme[:, 1],
            "vz_teme_kms": v_teme[:, 2],
            "x_itrs_km": r_itrs[:, 0],
            "y_itrs_km": r_itrs[:, 1],
            "z_itrs_km": r_itrs[:, 2],
            "vx_itrs_kms": v_itrs[:, 0],
            "vy_itrs_kms": v_itrs[:, 1],
            "vz_itrs_kms": v_itrs[:, 2],
            "lat_deg": lat,
            "lon_deg": lon,
            "height_km": height,
            "sgp4_error": error,
        }
    )
    return out


def cmd_propagate(args: argparse.Namespace) -> int:
    """Propagate the latest (or given) snapshot to ``--at`` and export the viewer bundle."""
    at = parse_utc(args.at)
    path = Path(args.snapshot) if args.snapshot else snapshot.latest_snapshot(config.SNAPSHOT_DIR)
    df = snapshot.read_snapshot(path)
    log.info("Propagating %d objects from %s to %s", len(df), path.name, at.isoformat())

    state = propagator.propagate_snapshot(df, [at])
    summary = propagator.error_summary(state.error)
    log.info("SGP4 status: %s", summary)

    state_df = _state_frame(df, state, at)
    out_path = config.PROPAGATED_DIR / f"state_{stamp(at)}.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(state_df, preserve_index=False)
    table = table.replace_schema_metadata(
        {
            **(table.schema.metadata or {}),
            b"driftwatch_snapshot": path.name.encode(),
            b"driftwatch_version": __version__.encode(),
        }
    )
    pq.write_table(table, out_path, compression="zstd")
    ok = state_df["sgp4_error"] == 0
    log.info(
        "Wrote %s; height range %.0f to %.0f km over %d valid objects",
        out_path,
        float(np.nanmin(state_df.loc[ok, "height_km"])),
        float(np.nanmax(state_df.loc[ok, "height_km"])),
        int(ok.sum()),
    )

    if not args.no_export:
        export_dir = Path(args.export_dir) if args.export_dir else config.VIEWER_DATA_DIR
        manifest = export_viewer_bundle(df, state, out_dir=export_dir, snapshot_name=path.name)
        log.info("Viewer manifest: %d objects, reference %s", manifest["n_objects"], manifest["reference_time"])
    print(out_path)
    return 0


def cmd_snapshots(args: argparse.Namespace) -> int:
    """List snapshots with object counts."""
    paths = snapshot.list_snapshots(config.SNAPSHOT_DIR)
    if not paths:
        print(f"No snapshots in {config.SNAPSHOT_DIR}")
        return 0
    for p in paths:
        meta = pq.read_metadata(p)
        print(f"{p.name}  {meta.num_rows:>7d} objects")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Fetch Space-Track gp_history for a list of NORAD ids and write a history parquet; or rebuild the index."""
    if args.rebuild_index:
        index = history.rebuild_index(config.HISTORY_DIR)
        print(f"{history.index_path(config.HISTORY_DIR)}: {len(index)} element sets in {index['file'].nunique()} files")
        return 0
    if not (args.ids and args.start and args.end):
        log.error("history needs --ids, --start and --end (or --rebuild-index)")
        return 2
    ids = sorted({int(x) for x in args.ids.split(",") if x.strip()})
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    now = datetime.now(UTC)
    try:
        records = spacetrack.fetch_gp_history(
            ids, start, end, cache_dir=config.CACHE_DIR, now=now, offline=args.offline
        )
    except (spacetrack.SpaceTrackAuthError, FileNotFoundError) as exc:
        log.error("Cannot fetch history: %s", exc)
        return 2
    df = history.frame_from_records(records, fetched_at=now)
    path = history.write_history(
        df,
        history.unique_history_path(now, config.HISTORY_DIR),
        metadata={"norad_ids": ",".join(map(str, ids)), "start": start.isoformat(), "end": end.isoformat()},
    )
    summary = history.history_summary(df)
    log.info("History: %s", summary)
    missing = sorted(set(ids) - set(df["norad_id"].tolist()))
    if missing:
        log.warning("No element sets in range for %d ids: %s", len(missing), missing[:20])
    print(path)
    return 0


def cmd_supplemental(args: argparse.Namespace) -> int:
    """Keep the supplemental store: fetch a version, thin the old ones, and refit the covariance across it.

    This is what the scheduled task runs (see ``.github/workflows/supplemental.yml`` and
    ``scripts/register-supplemental-task.ps1``). The supplemental covariance can only stop
    being an extrapolation once the store holds versions days apart, and CelesTrak keeps
    one version and overwrites it, so the versions have to be collected as they appear.
    """
    now = datetime.now(UTC)
    names = [n.strip() for n in (args.files or ",".join(config.SUPPLEMENTAL_FILES)).split(",") if n.strip()]
    for name in names:
        if not args.no_fetch:
            try:
                res = supplemental_mod.fetch_supplemental(name, now=now, offline=args.offline)
            except (httpx.HTTPError, celestrak.CelesTrakError, FileNotFoundError) as exc:
                log.error("Cannot fetch supplemental %s: %s", name, exc)
                return 2
            log.info(
                "%-22s %6d records  %s",
                f"supplemental {name}",
                res.n_objects,
                "cache" if res.from_cache else "downloaded",
            )
            records = supplemental_mod.load_supplemental_records(name, config.CACHE_DIR)
            path, written = supplemental_mod.store_supplemental(records, name=name, fetched_at=res.fetched_at)
            log.info(
                "Supplemental %s version %s: %s (%d records)",
                name,
                supplemental_mod.version_of(path),
                "stored" if written else "already stored",
                len(records),
            )
        if not args.no_prune:
            supplemental_mod.prune_supplemental(name, now=now, dry_run=args.dry_run)
        status = supplemental_mod.store_status(name)
        log.info("Supplemental store: %s", status)
        print(
            f"{name}: {status['n_versions']} versions, {status['first']} to {status['last']} "
            f"({status['span_days']} days, {status['megabytes']} MB)"
        )
        if args.fit:
            history_df = supplemental_mod.load_supplemental_history(name)
            ids = sorted({int(i) for i in history_df["norad_id"].unique()}) if len(history_df) else []
            fit = fit_supplemental_covariance(EmpiricalCovariance(), history_df, ids)
            if fit.bins is not None and len(fit.bins):
                print(fit.bins.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
            print(f"growth: {fit.summary.get('growth')}")
            horizon = fit.summary.get("horizon_days")
            print(
                f"exponent fitted: {fit.summary.get('exponent_fitted')} "
                f"(amplitude from the {fit.summary.get('amplitude_from')}); "
                f"valid to {horizon if horizon is not None else 'the whole window'}"
                f"{' days' if horizon is not None else ''}, beyond that the base model serves"
            )
    return 0


def cmd_fleet(args: argparse.Namespace) -> int:
    """Validate a fleet file and show each member as the latest (or given) snapshot knows it."""
    try:
        fleet = load_fleet(args.fleet)
    except FleetError as exc:
        log.error("%s", exc)
        return 2
    try:
        path = Path(args.snapshot) if args.snapshot else snapshot.latest_snapshot(config.SNAPSHOT_DIR)
    except FileNotFoundError as exc:
        log.warning("%s; showing the fleet file only", exc)
        for m in fleet:
            print(f"{m.norad_id:>9d}  {m.name:<28s} r={m.hard_body_radius_m:g} m  manoeuvres={m.manoeuvres}")
        return 0
    df = snapshot.read_snapshot(path)
    now = datetime.now(UTC)
    resolved = resolve_fleet(fleet, df, now=now)
    print(f"Fleet {fleet.name!r} ({len(fleet)} members) against {path.name}")
    shown = resolved.assign(
        hbr_m=resolved["hard_body_radius_m"],
        age_d=resolved["epoch_age_days"].round(2),
        active=resolved["in_active_group"],
    )[
        [
            "norad_id",
            "name",
            "role",
            "hbr_m",
            "manoeuvres",
            "in_catalogue",
            "active",
            "category",
            "altitude_band",
            "perigee_km",
            "apogee_km",
            "inclination_deg",
            "age_d",
            "source",
        ]
    ]
    with pd.option_context("display.width", 200, "display.max_columns", 30, "display.precision", 2):
        print(shown.to_string(index=False))
    missing = resolved.loc[~resolved["in_catalogue"], "norad_id"].tolist()
    if missing:
        log.error("%d fleet member(s) are not in the snapshot: %s", len(missing), missing)
        return 1
    stale = resolved.loc[resolved["epoch_age_days"] > 5.0, "norad_id"].tolist()
    if stale:
        log.warning("Element sets older than five days for %s", stale)
    inactive = resolved.loc[~resolved["in_active_group"], "norad_id"].tolist()
    if inactive:
        log.warning("Not in CelesTrak's active group: %s", inactive)
    return 0


# --------------------------------------------------------------------------------------
# History backfill and the covariance fit, shared by ``screen`` and ``risk --refit``


class HistoryUnavailable(RuntimeError):
    """The backfill was required (``--history on``) and could not run."""


def history_source_available(cache_dir: Path) -> bool:
    """Whether a backfill can be attempted: Space-Track credentials in the environment or a history cache."""
    has_creds = bool(os.environ.get(config.SPACETRACK_USER_ENV)) and bool(os.environ.get(config.SPACETRACK_PASS_ENV))
    return has_creds or spacetrack.history_cache_dir(cache_dir).exists()


def fit_from_history(
    objects: pd.DataFrame,
    *,
    end: datetime,
    days: int,
    mode: str,
    offline: bool,
    now: datetime,
    cache_dir: Path | None = None,
    history_dir: Path | None = None,
    snapshot_dir: Path | None = None,
) -> tuple[CovarianceFit, history.BackfillResult | None]:
    """Backfill ``days`` of history for ``objects`` (``norad_id``, ``category``, ``altitude_band``) and fit the model.

    ``mode`` is ``auto`` (backfill when credentials or a cache exist, warn and carry on
    otherwise), ``on`` (raise :class:`HistoryUnavailable` if the backfill fails) or
    ``off`` (fit from whatever the history store and the snapshots already hold). The
    directories default to the configured ones at call time.
    """
    cache_dir = cache_dir or config.CACHE_DIR
    history_dir = history_dir or config.HISTORY_DIR
    snapshot_dir = snapshot_dir or config.SNAPSHOT_DIR
    ids = [int(i) for i in objects["norad_id"]]
    result = None
    if mode == "on" or (mode == "auto" and history_source_available(cache_dir)):
        try:
            result = history.backfill(
                ids, end=end, days=days, cache_dir=cache_dir, history_dir=history_dir, now=now, offline=offline
            )
        except (spacetrack.SpaceTrackAuthError, spacetrack.SpaceTrackError, FileNotFoundError, httpx.HTTPError) as exc:
            if mode == "on":
                raise HistoryUnavailable(f"history backfill required (--history on) but failed: {exc}") from exc
            log.warning("History backfill skipped (%s); fitting from the stored history only", exc)
    elif mode == "auto":
        log.info("No Space-Track credentials or history cache; fitting from the stored history only")
    window = history.backfill_window(end, days)
    hist = history.load_history(norad_ids=ids, history_dir=history_dir, snapshot_dir=snapshot_dir)
    log.info(
        "History for the fit: %d element sets for %d of %d objects", len(hist), hist["norad_id"].nunique(), len(ids)
    )
    fit = fit_covariance(hist, objects, now=now, window=window)
    return fit, result


def supplemental_history(norad_ids: Sequence[int], names: Sequence[str] = config.SUPPLEMENTAL_FILES) -> pd.DataFrame:
    """Every stored supplemental version's sets for ``norad_ids``, across the configured files."""
    frames = [supplemental_mod.load_supplemental_history(name, norad_ids=norad_ids) for name in names]
    frames = [f for f in frames if len(f)]
    if not frames:
        return supplemental_mod.load_supplemental_history(names[0], norad_ids=norad_ids)
    return pd.concat(frames, ignore_index=True)


def elements_for_run(info: dict[str, Any]) -> pd.DataFrame:
    """Rebuild the element sets a stored run screened from: its snapshot plus the supplemental versions it used.

    This is what makes a run reproducible from what it records. The catalogue snapshot is
    immutable and the supplemental versions are stored per fetch, so the table this
    returns is the one the screening propagated, whatever CelesTrak is serving now.
    """
    df = snapshot.read_snapshot(Path(config.SNAPSHOT_DIR) / str(info["snapshot"]))
    df["ephemeris"] = "gp"
    for entry in info.get("supplemental") or []:
        path = Path(config.SUPPLEMENTAL_DIR) / str(entry["file"])
        if not path.exists():
            log.warning("Supplemental version %s is not stored; tracks fall back to the GP element sets", entry["file"])
            continue
        sup = supplemental_mod.read_supplemental(path)
        df, match = supplemental_mod.apply_supplemental_frame(
            df, sup, name=str(entry["name"]), version=str(entry["version"])
        )
        if match.n_applied != entry.get("n_applied"):
            log.warning(
                "Supplemental %s version %s applied to %d objects now against %s at the time of the run",
                entry["name"],
                entry["version"],
                match.n_applied,
                entry.get("n_applied"),
            )
    return df


def write_outputs(run_dir: RunDirectory, elements: pd.DataFrame, *, scenario: str, export: bool, show: int) -> None:
    """The Step 4 outputs: the weekly markdown report, and the viewer's JSON and track binary."""
    path = write_report(run_dir, scenario=scenario)
    log.info("Report: %s", path)
    if export:
        bundle, tracks = build_bundle(run_dir, elements, scenario=scenario)
        write_bundle(bundle, tracks)


def survivor_labels(df: pd.DataFrame, fleet: Fleet, result: ScreeningResult) -> pd.DataFrame:
    """``norad_id``, ``category``, ``altitude_band`` for the fleet and every Stage A survivor."""
    ids = sorted({int(i) for i in fleet.norad_ids} | {int(i) for i in result.stage_a.secondary_ids})
    by_id = df.drop_duplicates("norad_id").set_index("norad_id")
    labels = by_id.loc[ids, ["category", "altitude_band"]].reset_index()
    labels["norad_id"] = labels["norad_id"].astype("int64")
    return labels


def print_risk_summary(joined: pd.DataFrame, scenario: str, show: int) -> None:
    """The top events by probability and a per-primary table for one scenario of a run."""
    rows = joined[joined["scenario"] == scenario]
    if rows.empty:
        print(f"No events to score for scenario {scenario!r}.")
        return
    cols = [
        "primary_name",
        "secondary_norad_id",
        "secondary_name",
        "secondary_category",
        "tca",
        "miss_km",
        "rel_speed_kms",
        "pc",
        "pc_max",
        "pc_max_scale",
        "flag",
        "cov_source_secondary",
        "manoeuvre_secondary",
    ]
    top = rows.sort_values("pc", ascending=False).head(show)
    print(f"Top {len(top)} of {len(rows)} events by probability, scenario {scenario!r}")
    with pd.option_context("display.width", 240, "display.max_columns", 30, "display.precision", 3):
        print(top[cols].to_string(index=False, float_format=lambda x: f"{x:.3g}"))
    per_primary = rows.groupby("primary_name").agg(
        events=("miss_km", "size"),
        in_box=("in_box", "sum"),
        closest_km=("miss_km", "min"),
        red=("flag", lambda f: int((f == "red").sum())),
        yellow=("flag", lambda f: int((f == "yellow").sum())),
        max_pc=("pc", "max"),
        max_pc_max=("pc_max", "max"),
    )
    with pd.option_context("display.width", 240, "display.precision", 3):
        print(per_primary.to_string(float_format=lambda x: f"{x:.3g}"))


def print_fleet_sigmas(model: CovarianceModel, objects: pd.DataFrame) -> None:
    """Standard deviations at 1, 3 and 7 days for the fleet members under ``model``."""
    if not isinstance(model, EmpiricalCovariance):
        return
    members = objects[objects["is_primary"]]
    refs = [ObjectRef(int(r.norad_id), str(r.category), str(r.altitude_band)) for r in members.itertuples()]
    table = sigma_table(model, refs).merge(members[["norad_id", "name"]], on="norad_id")
    cols = ["name", "source"] + [c for c in table.columns if c.startswith("sigma_")]
    print("Fleet covariance (km, RIC standard deviations at 1, 3 and 7 days of propagation)")
    with pd.option_context("display.width", 240, "display.max_columns", 30):
        print(table[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))


def cmd_screen(args: argparse.Namespace) -> int:
    """Screen a fleet against the latest (or given) snapshot, fit the covariance, score the quiet scenario."""
    try:
        fleet = load_fleet(args.fleet)
    except FleetError as exc:
        log.error("%s", exc)
        return 2
    try:
        path = Path(args.snapshot) if args.snapshot else snapshot.latest_snapshot(config.SNAPSHOT_DIR)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    df = snapshot.read_snapshot(path)
    now = datetime.now(UTC)
    resolved = resolve_fleet(fleet, df, now=now)
    missing = resolved.loc[~resolved["in_catalogue"], "norad_id"].tolist()
    if missing:
        log.error("Refusing to screen: %d fleet member(s) are not in %s: %s", len(missing), path.name, missing)
        return 1

    df["ephemeris"] = "gp"
    supplemental_used: list[dict[str, Any]] = []
    if not args.no_supplemental:
        for name in config.SUPPLEMENTAL_FILES:
            try:
                res = supplemental_mod.fetch_supplemental(
                    name, cache_dir=config.CACHE_DIR, now=now, offline=args.offline
                )
            except (httpx.HTTPError, celestrak.CelesTrakError, FileNotFoundError) as exc:
                log.warning(
                    "Supplemental %s unavailable (%s); Starlink secondaries use their GP element sets", name, exc
                )
                continue
            log.info(
                "%-22s %6d records  %s",
                f"supplemental {name}",
                res.n_objects,
                "cache" if res.from_cache else "downloaded",
            )
            records = supplemental_mod.load_supplemental_records(name, config.CACHE_DIR)
            # Store the version before it is used: the cache keeps one version and overwrites it,
            # so without this a run cannot be reproduced from what it records.
            path, written = supplemental_mod.store_supplemental(records, name=name, fetched_at=res.fetched_at)
            version = supplemental_mod.version_of(path)
            log.info("Supplemental %s version %s (%s)", name, version, "stored" if written else "already stored")
            df, match = supplemental_mod.apply_supplemental(df, records, name=name, version=version)
            supplemental_used.append(
                {
                    "name": name,
                    "version": version,
                    "file": path.name,
                    "n_records": match.n_records,
                    "n_applied": match.n_applied,
                    "epoch_lag_days_median": round(float(match.epoch_lag_days_median), 3),
                }
            )

    cfg = ScreeningConfig(days=args.days, step_s=args.step, pad_km=args.pad, watch_radius_km=args.watch_radius)
    try:
        result = screen_fleet(df, fleet, config=cfg, start=args.start)
    except ScreeningError as exc:
        log.error("%s", exc)
        return 1
    summary = result.summary()
    log.info("Summary: %s", json.dumps(summary))

    # Geometry first: the events are written before anything about uncertainty is known.
    out_dir = Path(args.out_dir) if args.out_dir else config.CONJUNCTION_DIR
    run_dir = RunDirectory.for_run(fleet.name, result.start, out_dir)
    run_id = new_run_id(now)
    run_dir.write_events(
        result.events,
        snapshot=path.name,
        metadata={
            "driftwatch_run_id": run_id,
            "driftwatch_fleet": str(fleet.path or fleet.name),
            "driftwatch_screening_config": json.dumps(cfg.to_dict()),
            "driftwatch_screening_summary": json.dumps(summary),
            "driftwatch_supplemental": json.dumps(supplemental_used),
        },
    )
    log.info("Wrote %d events to %s", len(result.events), run_dir.events_path)
    timings = dict(result.timings_s)

    # Then the history, the covariance fit and the quiet scenario.
    t0 = time.perf_counter()
    labels = survivor_labels(df, fleet, result)
    rc = 0
    try:
        fit, backfill = fit_from_history(
            labels, end=result.start, days=args.history_days, mode=args.history, offline=args.offline, now=now
        )
    except HistoryUnavailable as exc:
        log.error(
            "%s. Scoring with the stored history only; run `driftwatch risk %s --refit --history on` "
            "to redo the history and the fit without rescreening",
            exc,
            run_dir.path,
        )
        fit, backfill = fit_from_history(
            labels, end=result.start, days=args.history_days, mode="off", offline=True, now=now
        )
        rc = 2
    model: CovarianceModel = fit.model
    ev = result.events
    involved = sorted({int(i) for i in ev["primary_norad_id"]} | {int(i) for i in ev["secondary_norad_id"]})
    objects = apply_history(objects_from_snapshot(involved + fleet.norad_ids, df, fleet), fit)
    table = fit.table
    supplemental_fit = None
    sup_ids = [int(i) for i in objects.loc[objects["ephemeris"] == "supplemental", "norad_id"]]
    if sup_ids:
        sup_history = supplemental_history(sup_ids)
        supplemental_fit = fit_supplemental_covariance(model, sup_history, sup_ids)
        model = supplemental_fit.model
        table = pd.concat([fit.table, supplemental_fit.table], ignore_index=True)
        objects = label_cov_sources(objects, model)
    timings["history_and_fit"] = time.perf_counter() - t0
    run_dir.write_covariance(
        table,
        metadata={"driftwatch_model_version": model_version_string(model), "driftwatch_run_id": run_id},
    )
    run_dir.write_objects(objects)

    t1 = time.perf_counter()
    risk = run_risk(
        ev, objects, model, scenario=args.scenario, run_id=run_id, snapshot=path.name, sweep=not args.no_sweep, now=now
    )
    run_dir.write_risk(risk, args.scenario)
    timings["risk"] = time.perf_counter() - t1
    timings["total"] = time.perf_counter() - t0 + result.timings_s["total"]
    run_dir.write_run(
        {
            "run_id": run_id,
            "snapshot": path.name,
            "fleet": str(fleet.path or fleet.name),
            "fleet_name": fleet.name,
            "start": result.start.isoformat(),
            "end": result.end.isoformat(),
            "config": cfg.to_dict(),
            "summary": summary,
            "timings_s": {k: round(v, 2) for k, v in timings.items()},
            "history": {
                "mode": args.history if rc == 0 else "off",
                "days": args.history_days,
                "backfill": asdict(backfill) if backfill is not None else None,
                "backfill_failed": rc != 0,
            },
            "supplemental": supplemental_used,
            "supplemental_covariance": supplemental_fit.summary if supplemental_fit is not None else None,
            "covariance": {
                **fit.summary,
                "model_version": model_version_string(model),
                "window": list(fit.model.window or ()),
            },
            "scenarios": [args.scenario],
            "risk_runs": [risk_run_record(risk, args.scenario, model, now)],
        }
    )
    joined = run_dir.rebuild_conjunctions()
    log.info(
        "Timings: screening %.1f s, history and fit %.1f s, risk %.1f s, total %.1f s",
        result.timings_s["total"],
        timings["history_and_fit"],
        timings["risk"],
        timings["total"],
    )
    write_outputs(run_dir, df, scenario=args.scenario, export=not args.no_viewer, show=args.show)
    print_fleet_sigmas(model, objects)
    print_risk_summary(joined, args.scenario, args.show)
    print(run_dir.path)
    return rc


def layer_spacex_ephemerides(model: CovarianceModel, objects: pd.DataFrame, info: dict[str, Any]) -> CovarianceModel:
    """Serve the Starlink objects a stored SpaceX ephemeris covers from SpaceX's own covariance.

    Everything else, and every time past a file's 72-hour horizon, stays with ``model``: the
    ephemeris is the operator's plan for the next three days and says nothing about day four.
    """
    ids = [int(i) for i in objects.loc[objects["category"] == "starlink", "norad_id"]]
    if not ids:
        return model
    table = spacex.load_store(ids)
    if not len(table):
        return model
    layered = spacex.SpacexEphemerisCovariance(model, table)
    info["spacex_covariance"] = {
        "n_objects": len(layered.series),
        "n_starlink_in_run": len(ids),
        "window": [str(table["ephemeris_start"].min()), str(table["ephemeris_stop"].max())],
        "source": "spacex-ephemeris",
    }
    log.info("SpaceX ephemeris covariance: %s", info["spacex_covariance"])
    return layered


def risk_run_record(risk: pd.DataFrame, scenario: str, model: CovarianceModel, now: datetime) -> dict[str, Any]:
    """What ``run.json`` keeps about one scoring: when, which model, how many flags."""
    return {
        "scenario": scenario,
        "computed_at": now.isoformat(),
        "model_version": model_version_string(model),
        "n_events": int(len(risk)),
        "n_red": int((risk["flag"] == "red").sum()) if len(risk) else 0,
        "n_yellow": int((risk["flag"] == "yellow").sum()) if len(risk) else 0,
        "max_pc": float(risk["pc"].max()) if len(risk) else None,
    }


def resolve_run(arg: str, out_dir: Path | None = None) -> RunDirectory:
    """A run directory from a path, a directory name under ``data/conjunctions`` or ``latest``."""
    out_dir = Path(out_dir or config.CONJUNCTION_DIR)
    if arg == "latest":
        runs = sorted(p for p in Path(out_dir).glob("*_*Z") if p.is_dir() and (p / "run.json").exists())
        if not runs:
            raise FileNotFoundError(f"no runs under {out_dir}")
        return RunDirectory(runs[-1])
    path = Path(arg)
    if not path.is_dir():
        path = Path(out_dir) / arg
    if not (path / "run.json").exists():
        raise FileNotFoundError(f"{path} is not a run directory (no run.json)")
    return RunDirectory(path)


def cmd_risk(args: argparse.Namespace) -> int:
    """Rescore the stored events of a run for one scenario: covariance and probability only, no rescreening."""
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    info = run_dir.read_run()
    now = datetime.now(UTC)
    events = run_dir.read_events()
    objects = run_dir.read_objects()
    log.info("Run %s: %d stored events from %s", run_dir.name, len(events), info["snapshot"])
    # The hard-body radius is a model parameter, so a rescore uses the rules the code holds
    # now rather than the ones the screening ran under.
    objects, hbr_summary = refresh_hard_body_radii(objects)
    if hbr_summary["n_changed"]:
        log.info("Hard-body radii rebaselined: %s", hbr_summary)
        info["hard_body_radii"] = hbr_summary

    model: CovarianceModel
    if args.refit:
        table = run_dir.read_covariance()
        labels = table.loc[table["kind"] == "object", ["norad_id", "category", "altitude_band"]].reset_index(drop=True)
        labels["norad_id"] = labels["norad_id"].astype("int64")
        try:
            fit, backfill = fit_from_history(
                labels,
                end=parse_utc(info["start"]),
                days=args.history_days,
                mode=args.history,
                offline=args.offline,
                now=now,
            )
        except HistoryUnavailable as exc:
            log.error("%s", exc)
            return 2
        model = fit.model
        objects = apply_history(objects, fit)
        table = fit.table
        sup_ids = [int(i) for i in objects.loc[objects["ephemeris"] == "supplemental", "norad_id"]]
        if sup_ids:
            supplemental_fit = fit_supplemental_covariance(model, supplemental_history(sup_ids), sup_ids)
            model = supplemental_fit.model
            table = pd.concat([fit.table, supplemental_fit.table], ignore_index=True)
            info["supplemental_covariance"] = supplemental_fit.summary
        objects = label_cov_sources(objects, model)
        run_dir.write_objects(objects)
        run_dir.write_covariance(
            table,
            metadata={"driftwatch_model_version": model_version_string(model), "driftwatch_run_id": info["run_id"]},
        )
        info["covariance"] = {
            **fit.summary,
            "model_version": model_version_string(model),
            "window": list(fit.model.window or ()),
        }
        info["history"] = {
            "mode": args.history,
            "days": args.history_days,
            "backfill": asdict(backfill) if backfill is not None else None,
        }
    else:
        table = run_dir.read_covariance()
        model = EmpiricalCovariance.from_frame(table)
        if (table["kind"] == "supplemental").any():
            model = SupplementalCovariance.from_frame(model, table)
    if hbr_summary["n_changed"] and not args.refit:
        run_dir.write_objects(objects)
    if not args.no_spacex:
        model = layer_spacex_ephemerides(model, objects, info)
    if args.scale != 1.0:
        model = ScaledCovariance(model, args.scale)

    risk = run_risk(
        events,
        objects,
        model,
        scenario=args.scenario,
        run_id=info["run_id"],
        snapshot=info["snapshot"],
        sweep=not args.no_sweep,
        now=now,
    )
    run_dir.write_risk(risk, args.scenario)
    runs = [r for r in info.get("risk_runs", []) if r.get("scenario") != args.scenario]
    runs.append(risk_run_record(risk, args.scenario, model, now))
    info["risk_runs"] = runs
    info["scenarios"] = run_dir.scenarios()
    run_dir.write_run(info)
    joined = run_dir.rebuild_conjunctions()
    try:
        write_outputs(
            run_dir, elements_for_run(info), scenario=args.scenario, export=not args.no_viewer, show=args.show
        )
    except FileNotFoundError as exc:
        log.warning("Cannot rebuild the run's element sets (%s); the report and viewer bundle were not written", exc)
    print_fleet_sigmas(model, objects)
    print_risk_summary(joined, args.scenario, args.show)
    print(run_dir.risk_path(args.scenario))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Rewrite the weekly report and the viewer bundle for a stored run."""
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    info = run_dir.read_run()
    scenarios = run_dir.scenarios()
    scenario = args.scenario or (scenarios[0] if scenarios else "quiet")
    if scenarios and scenario not in scenarios:
        log.error("Run %s has no scenario %r; it has %s", run_dir.name, scenario, scenarios)
        return 2
    write_outputs(run_dir, elements_for_run(info), scenario=scenario, export=not args.no_viewer, show=0)
    print(run_dir.path / "report.md")
    return 0


def weather_sources(
    *, now: datetime, offline: bool, as_of: datetime | None = None
) -> tuple[weather_table.WeatherSources, dict[str, Any]]:
    """The parsed space weather feeds and a summary of where each came from.

    ``as_of`` picks the newest SWPC version issued at or before that time instead of the
    newest stored, which is what makes rescoring a stored run reproducible: a run made last
    Tuesday rescores against last Tuesday's forecast.
    """
    used: dict[str, Any] = {}
    rows = None
    try:
        path = celestrak_sw.fetch_sw_all(now=now, offline=offline)
        rows = celestrak_sw.load_sw_all(path)
        used["celestrak"] = celestrak_sw.summary(rows)
    except (httpx.HTTPError, FileNotFoundError, ValueError) as exc:
        log.warning("CelesTrak space weather unavailable (%s)", exc)

    parsed: dict[str, tuple[pd.DataFrame, datetime] | None] = {}
    for product in ("kp-forecast", "outlook-27day"):
        path = swpc.stored_before(product, as_of) if as_of is not None else swpc.latest_version(product)
        if path is None:
            parsed[product] = None
            continue
        meta = swpc.read_meta(path)
        issued = datetime.fromisoformat(meta["issued_at"]) if meta.get("issued_at") else now
        parsed[product] = (swpc.load(product, path), issued)
        used[product] = {"file": path.name, "issued_at": issued.isoformat(), "from": meta.get("issued_from")}

    sources = weather_table.WeatherSources(
        celestrak=rows,
        kp_forecast=parsed["kp-forecast"][0] if parsed["kp-forecast"] else None,
        kp_forecast_issued=parsed["kp-forecast"][1] if parsed["kp-forecast"] else None,
        outlook=parsed["outlook-27day"][0] if parsed["outlook-27day"] else None,
        outlook_issued=parsed["outlook-27day"][1] if parsed["outlook-27day"] else None,
    )
    return sources, used


def cmd_weather(args: argparse.Namespace) -> int:
    """Fetch the space weather feeds, build the three-hourly table for a window and report it."""
    now = datetime.now(UTC)
    if not args.no_fetch:
        try:
            celestrak_sw.fetch_sw_all(now=now, offline=args.offline)
        except (httpx.HTTPError, FileNotFoundError) as exc:
            log.warning("CelesTrak space weather unavailable (%s)", exc)
        fetched = swpc.fetch_all(now=now, offline=args.offline)
        for product, res in fetched.items():
            log.info(
                "%-16s issued %s (%s)%s",
                product,
                res.issued_at.isoformat(timespec="minutes"),
                res.issued_from,
                " [stored]" if res.from_cache else "",
            )

    start = parse_utc(args.start) if args.start else now
    end = parse_utc(args.end) if args.end else start + timedelta(days=args.days)
    sources, used = weather_sources(now=now, offline=True)
    table = weather_table.weather_table(start, end, sources)
    summary = weather_table.table_summary(table)
    log.info("Space weather table: %s", summary)

    print(f"Space weather, {start.isoformat(timespec='minutes')} to {end.isoformat(timespec='minutes')}")
    with pd.option_context("display.width", 200, "display.max_rows", args.show):
        shown = (
            table if len(table) <= args.show else pd.concat([table.head(args.show // 2), table.tail(args.show // 2)])
        )
        print(shown.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print()
    print("provenance:", summary["by_provenance"])
    print("sources:   ", {k: v for k, v in summary["by_source"].items()})
    if summary["forecast_issued"]:
        print("forecasts issued:", ", ".join(summary["forecast_issued"]))
    if summary["n_missing"]:
        print(f"WARNING: {summary['n_missing']} intervals have no source at all")

    if not args.no_solar_wind:
        try:
            wind = swpc.load("solar-wind")
            print("solar wind:", swpc.solar_wind_summary(wind))
        except (FileNotFoundError, KeyError) as exc:
            log.info("No stored solar wind (%s)", exc)

    if args.images:
        frames = helioviewer.fetch_frames(start, end, per_day=args.frames_per_day, offline=args.offline)
        if frames:
            print()
            print(helioviewer.frames_table(frames).to_string(index=False))

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        table.to_parquet(out, index=False)
        print(out)
    return 0


def cmd_spacex(args: argparse.Namespace) -> int:
    """Fetch SpaceX's own ephemeris covariance for a run's Starlink secondaries and store it.

    One request per satellite, bounded to the objects the run's events actually involve, and
    only the thinned position covariance is kept. The raw files are never stored or
    redistributed (see ``docs/spacex-ephemerides.md``).
    """
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    info = run_dir.read_run()
    events = run_dir.read_events()
    objects = run_dir.read_objects()
    ids = args.ids and [int(i) for i in args.ids.split(",") if i.strip()]
    if not ids:
        ids = spacex.select_objects(events, objects, limit=args.limit)
    if not ids:
        log.error("Run %s has no Starlink secondaries to fetch ephemerides for", run_dir.name)
        return 2
    log.info("Fetching SpaceX ephemerides for %d of the run's Starlink secondaries", len(ids))

    now = datetime.now(UTC)
    try:
        table, summary = spacex.fetch_ephemerides(ids, now=now, offline=args.offline, limit=args.limit)
    except (httpx.HTTPError, FileNotFoundError) as exc:
        log.error("Cannot fetch SpaceX ephemerides: %s", exc)
        return 2
    if not len(table):
        log.error("No SpaceX ephemerides were retrieved")
        return 2
    path = spacex.write_store(table, spacex.store_path(now))
    summary["file"] = path.name

    # The cross-check: their covariance against ours, at matched leads. Two different
    # quantities, kept side by side rather than merged (see ephemeris/spacex.py).
    covariance_table = run_dir.read_covariance()
    base = EmpiricalCovariance.from_frame(covariance_table)
    model: CovarianceModel = base
    if (covariance_table["kind"] == "supplemental").any():
        model = SupplementalCovariance.from_frame(base, covariance_table)
    comparison = spacex.cross_check(table, model)
    if len(comparison):
        print(comparison.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
        summary["cross_check"] = comparison.to_dict("records")
    info["spacex"] = summary
    run_dir.write_run(info)
    print(path)
    return 0


def cmd_kelvins(args: argparse.Namespace) -> int:
    """Reproduce the risk column of ESA's Kelvins dataset and report the fitted hard-body radius and residuals."""
    data = Path(args.data) if args.data else kelvins_mod.find_dataset()
    if data is None or not data.exists():
        log.error(
            "Kelvins dataset not found under %s. Download train_data.csv from "
            "https://kelvins.esa.int/collision-avoidance-challenge/data/ (registration required) "
            "and place it there, or pass --data.",
            config.KELVINS_DIR,
        )
        return 2
    df = kelvins_mod.load_kelvins(data)
    log.info("Loaded %d rows from %s", len(df), data)
    fit = kelvins_mod.fit_hbr(df)
    extra = kelvins_mod.compare_max_risk(df, fit.hbr_m)
    tail = df[(df["risk"] >= kelvins_mod.TAIL_RISK) & (df["risk"] > kelvins_mod.RISK_FLOOR)].reset_index(drop=True)
    primary = kelvins_mod.reproduce_tail(df, source="span")
    if primary is not None:
        log.info(
            "Kelvins with the span radius: %d rows, %s",
            primary.n,
            {k: round(v, 4) for k, v in primary.report["tight_tail"].items() if isinstance(v, float)},
        )
    proxies = [p for p in (kelvins_mod.test_size_proxy(tail, s) for s in ("span", "rcs")) if p is not None]
    for proxy in proxies:
        log.info("Kelvins size proxy: %s", proxy)
    # The lookup driftwatch screens with, re-derived from these rows so the constant in
    # risk/scenario.py can be checked against its source rather than trusted.
    radii = kelvins_mod.chaser_radius_table(df)
    log.info("Kelvins radius lookup:\n%s", radii.to_string(index=False))
    stale = kelvins_mod.compare_span_radius_lookup(radii)
    if stale:
        log.warning("SPAN_RADIUS_M no longer matches the data: %s", stale)

    out = Path(args.out) if args.out else None
    plot_name = None
    if out is not None:
        plot_name = out.with_suffix(".svg").name
        risk = tail["risk"].to_numpy(dtype=float)
        svg = kelvins_mod.residual_plot_svg(
            primary.risk if primary is not None else risk,
            primary.residuals if primary is not None else fit.residuals,
            compare=(risk, fit.residuals) if primary is not None else None,
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        (out.parent / plot_name).write_text(svg, encoding="utf-8")
        log.info("Wrote %s", out.parent / plot_name)
    text = kelvins_mod.to_markdown(fit, data, extra, primary=primary, proxies=proxies, radii=radii, plot_path=plot_name)
    print(text)
    if out is not None:
        out.write_text(text + "\n", encoding="utf-8")
        log.info("Wrote %s", out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """The argparse parser for the ``driftwatch`` command."""
    parser = argparse.ArgumentParser(
        prog="driftwatch", description="LEO conjunction screening under geomagnetic storms."
    )
    parser.add_argument("--version", action="version", version=f"driftwatch {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="download CelesTrak groups (cached, at most every 2 h) and write a snapshot")
    fetch.add_argument(
        "--groups", help=f"comma-separated CelesTrak group names (default: {','.join(config.DEFAULT_GROUPS)})"
    )
    fetch.add_argument(
        "--offline", action="store_true", help="rebuild the snapshot from cache without any network access"
    )
    fetch.add_argument("--no-satcat", action="store_true", help="skip the SATCAT join (object types become UNK)")
    fetch.add_argument(
        "--spacetrack",
        choices=("auto", "on", "off"),
        default="auto",
        help=(
            "merge the Space-Track gp catalogue (cached, at most every 2 h and 4 times a day): "
            "auto uses it when SPACETRACK_USER and SPACETRACK_PASS are set or a cache exists, "
            "on fails without it, off skips it (default: auto)"
        ),
    )
    fetch.set_defaults(func=cmd_fetch)

    prop = sub.add_parser("propagate", help="propagate the latest snapshot to a time and export the viewer bundle")
    prop.add_argument("--at", required=True, help="UTC time, ISO 8601, e.g. 2026-09-01T12:00:00Z")
    prop.add_argument("--snapshot", help="snapshot parquet path (default: latest)")
    prop.add_argument("--no-export", action="store_true", help="skip writing the viewer bundle")
    prop.add_argument("--export-dir", help="viewer bundle directory (default: web/public/data)")
    prop.set_defaults(func=cmd_propagate)

    snaps = sub.add_parser("snapshots", help="list stored snapshots")
    snaps.set_defaults(func=cmd_snapshots)

    hist = sub.add_parser(
        "history", help="fetch Space-Track gp_history for NORAD ids over a date range into data/history/"
    )
    hist.add_argument("--ids", help="comma-separated NORAD ids, e.g. 25544,39634")
    hist.add_argument("--start", help="first epoch day (UTC), YYYY-MM-DD")
    hist.add_argument("--end", help="last epoch day inclusive (UTC), YYYY-MM-DD")
    hist.add_argument("--offline", action="store_true", help="use only cached gp_history responses")
    hist.add_argument(
        "--rebuild-index", action="store_true", help="rebuild data/history/index.parquet from the history files"
    )
    hist.set_defaults(func=cmd_history)

    fleet = sub.add_parser("fleet", help="validate a fleet YAML file and show its members in the latest snapshot")
    fleet.add_argument("fleet", help="fleet file, e.g. fleets/demo.yaml")
    fleet.add_argument("--snapshot", help="snapshot parquet path (default: latest)")
    fleet.set_defaults(func=cmd_fleet)

    def add_risk_options(p: argparse.ArgumentParser, *, scenario_default: str) -> None:
        p.add_argument("--scenario", default=scenario_default, help=f"scenario label (default: {scenario_default})")
        p.add_argument(
            "--history",
            choices=("auto", "on", "off"),
            default="auto",
            help=(
                "backfill Space-Track gp_history for the fleet and the Stage A survivors before the covariance fit: "
                "auto when credentials or a cache exist, on fails without it, off fits from stored history only "
                "(default: auto)"
            ),
        )
        p.add_argument(
            "--history-days",
            type=int,
            default=config.HISTORY_BACKFILL_DAYS,
            help=f"days of history before the window start to backfill (default: {config.HISTORY_BACKFILL_DAYS})",
        )
        p.add_argument("--no-sweep", action="store_true", help="skip the covariance-scale sweep for pc_max")
        p.add_argument(
            "--no-viewer", action="store_true", help="write the markdown report but not the viewer's JSON and tracks"
        )
        p.add_argument("--show", type=int, default=20, help="events to print, highest probability first (default: 20)")

    screen = sub.add_parser(
        "screen", help="screen a fleet against the latest snapshot, fit the covariance and write data/conjunctions/"
    )
    screen.add_argument("--fleet", required=True, help="fleet file, e.g. fleets/demo.yaml")
    screen.add_argument("--snapshot", help="snapshot parquet path (default: latest)")
    screen.add_argument("--days", type=float, default=7.0, help="window length in days from the start (default: 7)")
    screen.add_argument("--start", help="window start, UTC ISO 8601 (default: the snapshot's fetch time)")
    screen.add_argument("--step", type=float, default=30.0, help="Stage B step in seconds (default: 30)")
    screen.add_argument("--pad", type=float, default=50.0, help="Stage A apogee/perigee pad in km (default: 50)")
    screen.add_argument("--watch-radius", type=float, default=25.0, help="watch radius in km (default: 25)")
    screen.add_argument(
        "--no-supplemental", action="store_true", help="do not use CelesTrak's supplemental Starlink sets"
    )
    screen.add_argument("--offline", action="store_true", help="use only cached supplemental and history data")
    screen.add_argument("--out-dir", help="output directory (default: data/conjunctions)")
    add_risk_options(screen, scenario_default="quiet")
    screen.set_defaults(func=cmd_screen)

    risk = sub.add_parser(
        "risk", help="rescore a stored run's events for a scenario (covariance and probability only, no rescreening)"
    )
    risk.add_argument("run", help="run directory, its name under data/conjunctions, or 'latest'")
    risk.add_argument("--refit", action="store_true", help="refit the covariance from history before scoring")
    risk.add_argument(
        "--scale", type=float, default=1.0, help="multiply every covariance by this factor (a stand-in scenario knob)"
    )
    risk.add_argument("--offline", action="store_true", help="use only cached history data when refitting")
    risk.add_argument(
        "--no-spacex",
        action="store_true",
        help="ignore any stored SpaceX ephemeris covariance (see `driftwatch spacex`)",
    )
    add_risk_options(risk, scenario_default="quiet")
    risk.set_defaults(func=cmd_risk)

    report = sub.add_parser("report", help="rewrite a stored run's markdown report and the viewer's conjunction bundle")
    report.add_argument("run", help="run directory, its name under data/conjunctions, or 'latest'")
    report.add_argument("--scenario", help="scenario to report (default: the first stored)")
    report.add_argument("--no-viewer", action="store_true", help="write the report only")
    report.set_defaults(func=cmd_report)

    sup = sub.add_parser(
        "supplemental",
        help="fetch and store a supplemental version, thin the old ones, and optionally refit across the store",
    )
    sup.add_argument("--files", help=f"comma-separated file names (default: {','.join(config.SUPPLEMENTAL_FILES)})")
    sup.add_argument("--no-fetch", action="store_true", help="do not fetch; report (and prune) the store as it is")
    sup.add_argument("--no-prune", action="store_true", help="keep every stored version, however old")
    sup.add_argument("--dry-run", action="store_true", help="report what pruning would remove without removing it")
    sup.add_argument("--fit", action="store_true", help="refit the supplemental covariance over the whole store")
    sup.add_argument("--offline", action="store_true", help="use only the cached supplemental response")
    sup.set_defaults(func=cmd_supplemental)

    wx = sub.add_parser(
        "weather",
        help="fetch the space weather feeds and build the three-hourly table with its provenance",
    )
    wx.add_argument("--start", help="window start, ISO 8601 UTC (default: now)")
    wx.add_argument("--end", help="window end, ISO 8601 UTC (default: --days after the start)")
    wx.add_argument("--days", type=float, default=7.0, help="window length in days when --end is not given")
    wx.add_argument("--no-fetch", action="store_true", help="use the stored feeds; do not refresh any of them")
    wx.add_argument("--offline", action="store_true", help="use only what is already cached or stored")
    wx.add_argument("--no-solar-wind", action="store_true", help="skip the solar wind summary")
    wx.add_argument("--images", action="store_true", help="fetch Sun imagery for the window as well")
    wx.add_argument(
        "--frames-per-day",
        type=int,
        default=config.HELIOVIEWER_FRAMES_PER_DAY,
        help=f"Sun frames a day with --images (default {config.HELIOVIEWER_FRAMES_PER_DAY})",
    )
    wx.add_argument("--show", type=int, default=24, help="rows of the table to print (default 24)")
    wx.add_argument("--out", help="write the table to this parquet file as well")
    wx.set_defaults(func=cmd_weather)

    spx = sub.add_parser(
        "spacex",
        help="fetch SpaceX's own ephemeris covariance for a run's Starlink secondaries (analysis only)",
    )
    spx.add_argument("run", nargs="?", default="latest", help="run directory, its name, or 'latest'")
    spx.add_argument(
        "--limit",
        type=int,
        default=config.SPACEX_MAX_OBJECTS,
        help=f"most satellites to request, closest approach first (default {config.SPACEX_MAX_OBJECTS})",
    )
    spx.add_argument("--ids", help="comma-separated NORAD ids to fetch instead of choosing from the run")
    spx.add_argument("--offline", action="store_true", help="use the cached manifest only (cannot fetch files)")
    spx.set_defaults(func=cmd_spacex)

    kelvins = sub.add_parser("kelvins", help="reproduce ESA's Kelvins risk column and report the fitted radius")
    kelvins.add_argument("--data", help=f"the challenge CSV (default: the first CSV under {config.KELVINS_DIR})")
    kelvins.add_argument("--out", help="write the markdown report here as well as printing it")
    kelvins.set_defaults(func=cmd_kelvins)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    # httpx/httpcore debug logs would print request lines; keep them quiet even with -v so the
    # Space-Track login request never shows up in a log.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
