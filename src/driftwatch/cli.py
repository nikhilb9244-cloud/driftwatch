"""Command-line interface: fetch, propagate, snapshots, history, fleet, screen, risk and kelvins."""

from __future__ import annotations

import argparse
import cProfile
import functools
import io
import json
import logging
import os
import pstats
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import __version__, config
from driftwatch import stability as stability_mod
from driftwatch.catalogue import celestrak, history, satcat, snapshot, spacetrack
from driftwatch.cdm import kelvins as cdm_kelvins
from driftwatch.cdm import match as cdm_match
from driftwatch.cdm import parse as cdm_parse
from driftwatch.drag import ballistic as ballistic_mod
from driftwatch.drag import density as density_mod
from driftwatch.drag.store import CoefficientStore
from driftwatch.ephemeris import spacex
from driftwatch.export import storm as storm_export
from driftwatch.export.audit import audit_bundle
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.export.report import build_bundle, default_scenario, write_bundle, write_report
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
from driftwatch.stability import StabilityIndex
from driftwatch.storm import diagnostics, validation
from driftwatch.storm import scenarios as storm_scenarios
from driftwatch.storm import term as storm_term
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


def select_historical_objects(
    args: argparse.Namespace, as_of: datetime, satcat_frame: pd.DataFrame | None
) -> tuple[list[int], dict[str, Any]]:
    """Which objects a historical snapshot should cover, and why each rule kept them.

    Four ways in, and they compose: explicit ids, a launch's international designator prefix,
    a fleet file, and an altitude range read off the *current* catalogue. The altitude range
    is what keeps a history pull bounded -- a few hundred objects rather than the catalogue --
    and it has a bias worth stating plainly: it selects on where an object is **now**, so
    anything that has decayed since the date is missing from it. That matters most for exactly
    the storm being validated, because a storm's most affected objects are the ones that came
    down. The launch and id routes exist to reach those, through SATCAT, which keeps decayed
    objects and their decay dates.
    """
    ids: set[int] = set()
    why: dict[str, Any] = {}
    if args.ids:
        named = {int(x) for x in args.ids.split(",") if x.strip()}
        ids |= named
        why["ids"] = len(named)
    if args.fleet:
        members = {int(m.norad_id) for m in load_fleet(Path(args.fleet)).members}
        ids |= members
        why["fleet"] = len(members)
    if args.launch:
        prefixes = tuple(x.strip() for x in args.launch.split(",") if x.strip())
        raw = pd.read_csv(satcat.satcat_path(config.CACHE_DIR), usecols=["OBJECT_ID", "NORAD_CAT_ID"])
        matched = raw[raw["OBJECT_ID"].astype(str).str.startswith(prefixes)]
        ids |= {int(i) for i in matched["NORAD_CAT_ID"]}
        why["launch"] = {"prefixes": list(prefixes), "n": int(len(matched))}
    if args.min_perigee_km is not None or args.max_perigee_km is not None:
        current = snapshot.read_snapshot(snapshot.latest_snapshot(config.SNAPSHOT_DIR))
        perigee = pd.to_numeric(current["perigee_km"], errors="coerce")
        keep = pd.Series(True, index=current.index)
        if args.min_perigee_km is not None:
            keep &= perigee >= float(args.min_perigee_km)
        if args.max_perigee_km is not None:
            keep &= perigee <= float(args.max_perigee_km)
        if args.category:
            wanted = {c.strip() for c in args.category.split(",") if c.strip()}
            keep &= current["category"].astype(str).isin(wanted)
        band = current.loc[keep, "norad_id"]
        if args.sample and len(band) > args.sample:
            # Spread over the range rather than taken at random, so the sample covers the
            # altitudes and does not clump wherever the catalogue is densest.
            order = current.loc[keep].sort_values("perigee_km")
            band = order.iloc[:: max(len(order) // int(args.sample), 1)]["norad_id"].head(int(args.sample))
        ids |= {int(i) for i in band}
        why["altitude"] = {
            "min_perigee_km": args.min_perigee_km,
            "max_perigee_km": args.max_perigee_km,
            "category": args.category,
            "n_in_range": int(keep.sum()),
            "n_sampled": int(len(band)),
            "read_from": "the current catalogue, so objects that have decayed since are absent",
        }
    # Objects that had not launched, or had already re-entered, cannot be in a snapshot of that day.
    if satcat_frame is not None and ids:
        meta = satcat_frame.reindex(sorted(ids))
        day = as_of.date()
        launched = meta["launch_date"].isna() | (meta["launch_date"] <= day)
        alive = meta["decay_date"].isna() | (meta["decay_date"] > day)
        dropped = sorted({int(i) for i in meta.index[~(launched & alive)]})
        if dropped:
            why["not_in_orbit_on_the_day"] = len(dropped)
            ids -= set(dropped)
    return sorted(ids), why


def cmd_snapshot_as_of(args: argparse.Namespace) -> int:
    """Rebuild the catalogue as it stood on a past date, from gp_history. Cached permanently."""
    as_of = parse_utc(args.date)
    path = snapshot.as_of_path(as_of, config.AS_OF_SNAPSHOT_DIR)
    if path.exists() and not args.force:
        df = snapshot.read_snapshot(path)
        log.info("Using the cached historical snapshot %s: %d objects", path.name, len(df))
        print(path)
        return 0
    now = datetime.now(UTC)
    try:
        satcat_path = satcat.fetch_satcat(cache_dir=config.CACHE_DIR, now=now, offline=args.offline)
        satcat_frame = satcat.load_satcat(satcat_path)
    except (httpx.HTTPError, FileNotFoundError) as exc:
        log.warning("No SATCAT (%s); the snapshot will carry no object type or radar cross-section", exc)
        satcat_frame = None

    ids, why = select_historical_objects(args, as_of, satcat_frame)
    if not ids:
        log.error("no objects selected; pass --ids, --launch, --fleet or an altitude range")
        return 2
    log.info("Historical snapshot for %s: %d objects selected (%s)", as_of.date(), len(ids), why)

    # The pull has to reach back far enough that every object has a set *before* the date.
    end = as_of + timedelta(days=1)
    days = int(args.days)
    try:
        result = history.backfill(
            ids,
            end=end,
            days=days,
            cache_dir=config.CACHE_DIR,
            history_dir=config.HISTORY_DIR,
            offline=args.offline,
            # The window is in the past, so "already held through today" says nothing about it.
            use_stored=False,
        )
        log.info("History: %s", result)
    except (spacetrack.SpaceTrackAuthError, FileNotFoundError) as exc:
        log.error("Cannot fetch history: %s", exc)
        return 2

    sets = history.load_history(norad_ids=ids, start=as_of - timedelta(days=days), end=end)
    if not len(sets):
        log.error("no element sets stored for those objects in the %d days to %s", days, as_of.date())
        return 2
    current_groups: dict[int, list[str]] = {}
    try:
        latest = snapshot.read_snapshot(snapshot.latest_snapshot(config.SNAPSHOT_DIR))
        current_groups = {int(r.norad_id): list(r.groups) for r in latest.itertuples() if r.groups is not None}
    except FileNotFoundError:
        pass
    try:
        df = snapshot.snapshot_as_of(
            sets, satcat_frame, as_of=as_of, groups=current_groups, max_age_days=args.max_age_days
        )
    except ValueError as exc:
        log.error("%s", exc)
        return 2

    path.parent.mkdir(parents=True, exist_ok=True)
    table = snapshot.to_arrow(
        df,
        extra_metadata={
            "driftwatch_as_of": as_of.isoformat(),
            "driftwatch_selection": json.dumps(why),
            "driftwatch_max_age_days": str(args.max_age_days),
            "driftwatch_built_at": now.isoformat(),
        },
    )
    pq.write_table(table, path, compression="zstd")
    ages = (pd.Timestamp(as_of) - pd.to_datetime(df["epoch"], utc=True)).dt.total_seconds() / 86400.0
    log.info(
        "Historical snapshot %s: %d of %d objects, element-set age median %.2f d, p90 %.2f d, max %.2f d",
        path.name,
        len(df),
        len(ids),
        float(ages.median()),
        float(ages.quantile(0.9)),
        float(ages.max()),
    )
    print(f"{len(df)} objects as of {as_of.isoformat()}")
    print("by category:", df["category"].value_counts().to_dict())
    print(
        f"perigee km: min {df['perigee_km'].min():.0f}, median {df['perigee_km'].median():.0f}, "
        f"max {df['perigee_km'].max():.0f}"
    )
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
    # A window that ended well before now is a historical run (Phase 3 Step 4's replay), and two
    # things that are right for a live run are wrong for it. The backfill's "already held
    # through the newest stored set" shortcut is a true statement about an object with a 2026
    # element set that says nothing about 2024, so it is turned off; and the fit must be given
    # only the element sets from around that window, or it is fitted to today's behaviour and
    # merely labelled with the historical window.
    historical = end < now - timedelta(days=int(days))
    if mode == "on" or (mode == "auto" and history_source_available(cache_dir)):
        try:
            result = history.backfill(
                ids,
                end=end,
                days=days,
                cache_dir=cache_dir,
                history_dir=history_dir,
                now=now,
                offline=offline,
                use_stored=not historical,
            )
        except (spacetrack.SpaceTrackAuthError, spacetrack.SpaceTrackError, FileNotFoundError, httpx.HTTPError) as exc:
            if mode == "on":
                raise HistoryUnavailable(f"history backfill required (--history on) but failed: {exc}") from exc
            log.warning("History backfill skipped (%s); fitting from the stored history only", exc)
    elif mode == "auto":
        log.info("No Space-Track credentials or history cache; fitting from the stored history only")
    window = history.backfill_window(end, days)
    # Every fit reads only its recorded window, live or historical (2026-09-05). Before this a
    # live run passed no epoch bounds, so the fit read every stored row for its objects: the
    # 3 September 2026 run's fit took the May 2024 sets the storm validation had stored for
    # 1,794 of its 2,944 objects while its covariance block said 21 July to 3 September.
    # `fit_covariance` refuses rows outside the window it is labelled with, so the label is
    # true by construction; the end bound is the run's start rather than the last day's end,
    # so a historical run reads nothing issued after the moment it replays.
    window_start, _ = history.window_bounds(window)
    hist = history.load_history(
        norad_ids=ids, history_dir=history_dir, snapshot_dir=snapshot_dir, start=window_start, end=end
    )
    log.info(
        "History for the fit: %d element sets for %d of %d objects, bounded to %s to %s%s",
        len(hist),
        hist["norad_id"].nunique(),
        len(ids),
        window[0],
        window[1],
        " (a historical run)" if historical else "",
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


def snapshot_file(name: str) -> Path:
    """The stored snapshot of that name, live or historical.

    A run records its snapshot by file name. Historical snapshots live in their own directory
    (:data:`driftwatch.config.AS_OF_SNAPSHOT_DIR`) so that they cannot become "the latest
    snapshot" for the pipeline, which means a run built from one has to be told where to look.
    """
    live = Path(config.SNAPSHOT_DIR) / name
    if live.exists():
        return live
    historical = Path(config.AS_OF_SNAPSHOT_DIR) / name
    if historical.exists():
        return historical
    raise FileNotFoundError(f"snapshot {name!r} is in neither {config.SNAPSHOT_DIR} nor {config.AS_OF_SNAPSHOT_DIR}")


@dataclass(frozen=True)
class RunCheck:
    """The result of checking one run's provenance and freshness."""

    problems: list[str]
    warnings: list[str]
    snapshot: Path | None
    fetched_at: datetime | None
    age_hours: float | None

    @property
    def ok(self) -> bool:
        return not self.problems


def check_run(
    run_dir: RunDirectory,
    *,
    max_snapshot_age_hours: float | None = None,
    now: datetime | None = None,
) -> RunCheck:
    """Is this run's recorded provenance true, and is its snapshot fresh enough to publish?

    Added at the Phase 4 Step 2 review, because the failure it guards against had already
    happened once and nothing noticed. A run records its snapshot by file name; ``cmd_screen``
    shadowed the variable holding that name with the stored supplemental file's, so two runs
    recorded a supplemental element-set file as their snapshot. `driftwatch report` could not
    rebuild them, every exported row carried a false provenance, and the whole test suite was
    green -- because no test, and no code path outside `elements_for_run`, ever looked the
    recorded name up.

    Step 2's failure model rests on this name twice over: it computes the snapshot age from it
    and refuses to publish past a limit, and the console shows that age. A name that resolves
    to the wrong file, or to nothing, has to be a loud failure rather than a silent one.

    Problems fail; warnings do not. Two runs of the same snapshot minutes apart are ordinary,
    so a start time that disagrees with the snapshot's fetch time is a warning; a snapshot that
    is not a snapshot is a problem.
    """
    now = now or datetime.now(UTC)
    problems: list[str] = []
    warnings: list[str] = []
    try:
        info = run_dir.read_run()
    except (OSError, json.JSONDecodeError) as exc:
        return RunCheck([f"{run_dir.name}: run.json cannot be read ({exc})"], [], None, None, None)

    name = info.get("snapshot")
    if not name:
        return RunCheck([f"{run_dir.name}: run.json records no snapshot"], warnings, None, None, None)

    path: Path | None = None
    try:
        path = snapshot_file(str(name))
    except FileNotFoundError as exc:
        problems.append(f"{run_dir.name}: {exc}")

    fetched_at: datetime | None = None
    age_hours: float | None = None
    if path is not None:
        problem = snapshot.snapshot_problem(path)
        if problem:
            problems.append(f"{run_dir.name}: recorded snapshot {name!r} is not a catalogue snapshot -- {problem}")
        else:
            fetched_at = snapshot.snapshot_fetched_at(path)
            age_hours = (now - fetched_at).total_seconds() / 3600.0
            # The screening window starts at the snapshot's fetch time floored to the minute
            # (`default_start`), so more than a minute of disagreement means the run was screened
            # from a different snapshot than the one it names.
            start = info.get("start")
            if start:
                drift_s = abs((parse_utc(start) - fetched_at).total_seconds())
                if drift_s > 60.0:
                    warnings.append(
                        f"{run_dir.name}: start {start} is {drift_s / 60.0:.1f} min from the snapshot's "
                        f"fetch time {fetched_at.isoformat()}; --start was given, "
                        "or the snapshot is not the one screened"
                    )
            if max_snapshot_age_hours is not None and age_hours > float(max_snapshot_age_hours):
                problems.append(
                    f"{run_dir.name}: snapshot {path.name} was fetched {age_hours:.1f} h ago, "
                    f"past the {float(max_snapshot_age_hours):g} h limit -- EXPIRED, do not publish"
                )

    for entry in info.get("supplemental") or []:
        supplemental_path = Path(config.SUPPLEMENTAL_DIR) / str(entry.get("file", ""))
        if not supplemental_path.exists():
            warnings.append(
                f"{run_dir.name}: supplemental version {entry.get('file')!r} is no longer stored, "
                "so this run cannot be rebuilt exactly"
            )

    for required in (run_dir.events_path, run_dir.objects_path):
        if not required.exists():
            problems.append(f"{run_dir.name}: {required.name} is missing")
    if not run_dir.scenarios():
        problems.append(f"{run_dir.name}: no risk_<scenario>.parquet, so nothing has been scored")

    return RunCheck(problems, warnings, path, fetched_at, age_hours)


def cmd_check_run(args: argparse.Namespace) -> int:
    """Check a run's provenance and its snapshot's age; the pipeline's gate before it publishes."""
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    result = check_run(run_dir, max_snapshot_age_hours=args.max_snapshot_age_hours)
    for warning in result.warnings:
        log.warning("%s", warning)
    for problem in result.problems:
        log.error("%s", problem)
    if result.fetched_at is not None:
        log.info(
            "Snapshot %s fetched %s (%.1f h ago)",
            result.snapshot.name if result.snapshot else "?",
            result.fetched_at.isoformat(),
            result.age_hours or 0.0,
        )
    if result.problems:
        log.error("%s: %d problem(s); refusing to pass this run", run_dir.name, len(result.problems))
        return 1
    print(
        json.dumps(
            {
                "run": run_dir.name,
                "snapshot": result.snapshot.name if result.snapshot else None,
                "snapshot_fetched_at": result.fetched_at.isoformat() if result.fetched_at else None,
                "snapshot_age_hours": round(result.age_hours, 3) if result.age_hours is not None else None,
                "warnings": result.warnings,
                "ok": True,
            }
        )
    )
    return 0


def cmd_stability(args: argparse.Namespace) -> int:
    """Append a scored run to the warning-stability index, or read one series back out of it.

    Two modes in one command because they are two ends of one file. The pipeline calls the first
    after it publishes; a person asking "did this warning hold up" calls the second, and never
    has to download a run archive to get an answer.
    """
    index = StabilityIndex(Path(args.store) if args.store else None)
    if args.series or args.pair:
        pair = None
        if args.pair:
            try:
                a, b = (int(x) for x in str(args.pair).replace(",", " ").split())
            except ValueError:
                log.error("--pair wants two NORAD ids, e.g. --pair 55053,61705")
                return 2
            pair = (a, b)
        rows = index.read(args.fleet, series=args.series, pair=pair, scenario=args.scenario)
        if rows.empty:
            log.error("Nothing in the index for %s", args.series or f"{pair[0]} vs {pair[1]}" if pair else args.fleet)
            return 1
        print(stability_mod.format_series(rows))
        return 0

    try:
        run_dir = resolve_run(args.run or "latest")
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    try:
        result = index.append_run(
            run_dir,
            scenarios=[s.strip() for s in args.scenario.split(",")] if args.scenario else None,
            tolerance_s=args.tolerance_s,
            dry_run=args.dry_run,
        )
    except stability_mod.StabilityError as exc:
        log.error("%s", exc)
        return 1
    if not args.dry_run:
        # The run records what it contributed, so an archived run says whether it is in the index
        # and on what tolerance -- the same rule every other step here follows.
        run_dir.update_run(stability=result.to_dict())
    print(json.dumps(result.to_dict()))
    return 0


def elements_for_run(info: dict[str, Any]) -> pd.DataFrame:
    """Rebuild the element sets a stored run screened from: its snapshot plus the supplemental versions it used.

    This is what makes a run reproducible from what it records. The catalogue snapshot is
    immutable and the supplemental versions are stored per fetch, so the table this
    returns is the one the screening propagated, whatever CelesTrak is serving now.
    """
    df = snapshot.read_snapshot(snapshot_file(str(info["snapshot"])))
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


def write_outputs(
    run_dir: RunDirectory,
    elements: pd.DataFrame,
    *,
    scenario: str,
    export: bool,
    show: int,
    out_dir: Path | None = None,
) -> None:
    """The weekly markdown report, the viewer's JSON and track binary, and the scenario overlays.

    The overlays are a separate file rather than more of the bundle because storm mode has to
    switch between five scenarios without re-fetching the geometry, the names or the tracks --
    none of which a scenario changes. The viewer fetches it after first paint, so the critical
    path is the size it was before storm mode existed.
    """
    path = write_report(run_dir, scenario=scenario)
    log.info("Report: %s", path)
    if export:
        bundle, tracks = build_bundle(run_dir, elements, scenario=scenario)
        target = Path(out_dir) if out_dir else config.VIEWER_DATA_DIR
        write_bundle(bundle, tracks, target)
        storm_export.write_overlays(storm_export.build_overlays(run_dir, bundle), target)


def survivor_labels(df: pd.DataFrame, fleet: Fleet, result: ScreeningResult) -> pd.DataFrame:
    """``norad_id``, ``category``, ``altitude_band`` for the fleet and every Stage A survivor."""
    ids = sorted({int(i) for i in fleet.norad_ids} | {int(i) for i in result.stage_a.secondary_ids})
    by_id = df.drop_duplicates("norad_id").set_index("norad_id")
    labels = by_id.loc[ids, ["category", "altitude_band"]].reset_index()
    labels["norad_id"] = labels["norad_id"].astype("int64")
    return labels


def print_scenario_comparison(run_dir: RunDirectory, scenario: str, show: int) -> None:
    """What the scenario did to the quiet numbers, event by event, for the events it moved most.

    The comparison the prompt asks for: the probability under shift plus variance is the
    primary number, the probability under variance alone is beside it, and the quiet run --
    when one is stored -- is the baseline both are read against.
    """
    if scenario == config.SCENARIO_QUIET or config.SCENARIO_QUIET not in run_dir.scenarios():
        return
    quiet = run_dir.read_risk(config.SCENARIO_QUIET).set_index("event_id")
    now = run_dir.read_risk(scenario).set_index("event_id")
    joined = now.join(quiet[["pc"]].rename(columns={"pc": "pc_quiet"}), how="inner")
    moved = joined[(joined["pc"] > 1e-9) | (joined["pc_quiet"] > 1e-9)].copy()
    if not len(moved):
        print(f"\nNo event under '{scenario}' or 'quiet' reaches a probability of 1e-9; nothing to compare.")
        return
    with np.errstate(divide="ignore", invalid="ignore"):
        moved["ratio"] = moved["pc"] / moved["pc_quiet"].replace(0.0, np.nan)
    moved["shift_km"] = moved["shift_i_secondary_km"] - moved["shift_i_primary_km"]
    columns = ["pc_quiet", "pc", "pc_variance_only", "ratio", "shift_km", "miss_shifted_km", "flag"]
    print(f"\n'{scenario}' against 'quiet', the {show} events it moves most (probability, km):")
    shown = moved.reindex(moved["ratio"].abs().sort_values(ascending=False).index).head(show)
    print(shown[columns].to_string(float_format=lambda x: f"{x:.3g}"))
    print(
        f"  shift plus variance is `pc`; variance alone is `pc_variance_only`. "
        f"Median pc/pc_variance_only over these: {float(np.nanmedian(moved['pc'] / moved['pc_variance_only'])):.3f}"
    )


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
            # so without this a run cannot be reproduced from what it records. Its own variable,
            # never `path`: `path` is the catalogue snapshot and is what the run records as its
            # snapshot, and shadowing it here made two Step 1 runs record the supplemental file
            # name instead -- which `snapshot_file` then cannot find, so `elements_for_run`
            # could not rebuild them and Step 2 could not have computed a snapshot age.
            stored_path, written = supplemental_mod.store_supplemental(records, name=name, fetched_at=res.fetched_at)
            version = supplemental_mod.version_of(stored_path)
            log.info("Supplemental %s version %s (%s)", name, version, "stored" if written else "already stored")
            df, match = supplemental_mod.apply_supplemental(df, records, name=name, version=version)
            supplemental_used.append(
                {
                    "name": name,
                    "version": version,
                    "file": stored_path.name,
                    "n_records": match.n_records,
                    "n_applied": match.n_applied,
                    "epoch_lag_days_median": round(float(match.epoch_lag_days_median), 3),
                }
            )

    cfg = ScreeningConfig(
        days=args.days,
        step_s=args.step,
        pad_km=args.pad,
        watch_radius_km=args.watch_radius,
        attached_km=args.attached_km,
        attached_fraction=args.attached_fraction,
        exclude_attached=not args.keep_attached,
    )
    # The operator's own published states, where the store holds them, in place of the SGP4
    # fit to them -- in Stage B as well as Stage C, because the two trajectories are tens of
    # kilometres apart at the far end of the ephemeris horizon (docs/spacex-ephemerides.md).
    trajectory = None
    if not args.no_spacex:
        trajectory = spacex.load_trajectory(sorted(set(df["norad_id"].astype(int))))
        if len(trajectory):
            log.info("Screening on published states where they reach: %s", trajectory.summary())
        else:
            log.info("No stored SpaceX states; screening on element sets alone (run `driftwatch spacex`)")
    try:
        result = screen_fleet(df, fleet, config=cfg, start=args.start, ephemeris=trajectory)
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
        ev,
        objects,
        model,
        scenario=args.scenario,
        run_id=run_id,
        snapshot=path.name,
        supplemental_version=supplemental_version_string({"supplemental": supplemental_used}),
        sweep=not args.no_sweep,
        now=now,
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
            "attached_excluded": attached_record(result, df, fleet),
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
    # Immediately, on the run just written: the provenance a run records is trusted by every
    # later step and by the pipeline's staleness gate, and it went wrong silently once.
    provenance = check_run(run_dir)
    for warning in provenance.warnings:
        log.warning("%s", warning)
    if provenance.problems:
        for problem in provenance.problems:
            log.error("%s", problem)
        log.error("The run was written but its recorded provenance is wrong; treat it as unpublishable")
        rc = 1

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


def attached_record(result: ScreeningResult, elements: pd.DataFrame, fleet: Fleet) -> dict[str, Any]:
    """What the attached/co-orbiting filter excluded, named, for ``run.json`` and the report.

    Named here rather than in the screening because Stage B works on norad ids and the names
    live in the snapshot. Ten rows at most in practice, so it goes in ``run.json`` beside the
    rest of the run's provenance rather than into a parquet of its own.
    """
    cfg = result.config
    table = result.stage_b.attached
    names = elements.drop_duplicates("norad_id").set_index("norad_id")["name"]
    fleet_names = {m.norad_id: m.name for m in fleet}
    rows = [
        {
            "primary_norad_id": int(r.primary_norad_id),
            "primary_name": fleet_names.get(int(r.primary_norad_id), str(names.get(r.primary_norad_id, ""))),
            "secondary_norad_id": int(r.secondary_norad_id),
            "secondary_name": str(names.get(r.secondary_norad_id, "")),
            "samples": int(r.samples),
            "fraction_below": round(float(r.fraction_below), 6),
            "d_min_m": round(float(r.d_min_km) * 1000.0, 3),
            "d_mean_m": round(float(r.d_mean_km) * 1000.0, 3),
            "d_max_m": round(float(r.d_max_km) * 1000.0, 3),
        }
        for r in table.itertuples()
    ]
    return {
        "enabled": bool(cfg.exclude_attached),
        "rule": (
            f"separation at or under {cfg.attached_km:g} km for at least "
            f"{cfg.attached_fraction:.0%} of the sampled window"
        ),
        "attached_km": cfg.attached_km,
        "attached_fraction": cfg.attached_fraction,
        "n_pairs": len(rows),
        "n_candidates_dropped": int(result.stage_b.n_attached_candidates),
        "pairs": rows,
    }


def layer_spacex_ephemerides(
    model: CovarianceModel,
    objects: pd.DataFrame,
    info: dict[str, Any],
    events: pd.DataFrame | None = None,
) -> CovarianceModel:
    """Serve the Starlink objects a stored SpaceX ephemeris covers from SpaceX's own covariance.

    Everything else, and every time past a file's 72-hour horizon, stays with ``model``: the
    ephemeris is the operator's plan for the next three days and says nothing about day four.

    Their covariance carries CelesTrak's SGP4 fit residual in quadrature **only on the events
    whose geometry still comes from that fit**. Which those are is read from the events table
    the screening wrote, not recomputed here; see ``ephemeris/spacex.py``.
    """
    ids = [int(i) for i in objects.loc[objects["category"] == "starlink", "norad_id"]]
    if not ids:
        return model
    table = spacex.load_store(ids)
    if not len(table):
        return model
    served = spacex.interpolated_times_from_events(events) if events is not None else {}
    layered = spacex.SpacexEphemerisCovariance(model, table, interpolated_times=served)
    info["spacex_covariance"] = {
        "n_objects": len(layered.series),
        "n_starlink_in_run": len(ids),
        "window": [str(table["ephemeris_start"].min()), str(table["ephemeris_stop"].max())],
        "source": "spacex-ephemeris",
        "sgp4_fit_residual": layered.fit_rms_summary(),
    }
    log.info("SpaceX ephemeris covariance: %s", info["spacex_covariance"])
    return layered


def supplemental_version_string(info: dict[str, Any]) -> str:
    """``starlink:20260902T064855Z`` and so on: which supplemental versions the run screened on.

    Carried on every risk row because two runs against the same catalogue snapshot but
    different supplemental versions are different runs -- the sets change several times a day
    and CelesTrak keeps only the current one.
    """
    entries = info.get("supplemental") or []
    return ",".join(f"{e.get('name')}:{e.get('version')}" for e in entries if isinstance(e, dict))


def layer_storm_term(
    model: CovarianceModel,
    run_dir: RunDirectory,
    objects: pd.DataFrame,
    info: dict[str, Any],
    *,
    scenario_name: str,
    offline: bool,
    now: datetime,
    step_s: float | None = None,
    offset_days: float | None = None,
) -> tuple[CovarianceModel, storm_scenarios.Scenario]:
    """Build the named scenario's weather, compute the storm term, and wrap ``model`` in it.

    The quiet scenario returns ``model`` untouched, which is what makes it the Phase 2
    regression baseline. Anything else needs the run's ballistic coefficients; without them
    the scenario would move nothing, so the absence is an error rather than a quiet zero.
    """
    if not storm_scenarios.is_known(scenario_name) or scenario_name == config.SCENARIO_QUIET:
        scenario = storm_scenarios.build_scenario(
            scenario_name,
            start=parse_utc(info["start"]),
            end=parse_utc(info["end"]),
            sources=weather_table.WeatherSources(),
            now=now,
        )
        log.info("Scenario %s: %s", scenario.name, scenario.description)
        return model, scenario
    if not run_dir.ballistic_path.exists():
        raise FileNotFoundError(
            f"scenario {scenario_name!r} needs a ballistic coefficient per object and "
            f"{run_dir.ballistic_path} does not exist; run `driftwatch ballistic {run_dir.name}` first"
        )
    coefficients = run_dir.read_ballistic()
    elements = elements_for_run(info)
    elements = elements[elements["norad_id"].isin(objects["norad_id"])].reset_index(drop=True)
    # The table has to reach behind the *oldest element set*, not the window start: every shift
    # is integrated from its own object's epoch.
    scenario = storm_scenarios.build_scenario(
        scenario_name,
        start=parse_utc(info["start"]),
        end=parse_utc(info["end"]),
        sources=weather_sources(now=now, offline=offline)[0],
        now=now,
        offset_days=offset_days,
        earliest_epoch=pd.to_datetime(elements["epoch"], utc=True).min().to_pydatetime(),
    )
    log.info("Scenario %s: %s", scenario.name, scenario.description)
    # Operator-controlled objects (2026-09-05): no mean shift for any of them, and no density
    # track at all for the ones on an operator's trajectory, where the excess is undefined.
    controlled = storm_scenarios.controlled_objects(objects)
    skip = {norad_id for norad_id, reason in controlled.items() if storm_scenarios.skips_storm_term(reason)}
    shifts = storm_scenarios.shifts_for_objects(
        scenario, elements, coefficients, end=parse_utc(info["end"]), step_s=step_s, skip=skip
    )
    summary = storm_term.shift_summary(shifts, controlled)
    log.info("Storm term: %s", summary)
    info.setdefault("storm", {})[scenario.name] = {
        "description": scenario.description,
        **scenario.provenance,
        "shifts": summary,
    }
    layered = storm_scenarios.StormCovariance(model, shifts, scenario=scenario.name, controlled=controlled)
    return layered, scenario


def _flag_counts(risk: pd.DataFrame) -> dict[str, Any]:
    """Events, flags and the largest probability over whatever subset is handed in."""
    return {
        "n_events": int(len(risk)),
        "n_red": int((risk["flag"] == "red").sum()) if len(risk) else 0,
        "n_yellow": int((risk["flag"] == "yellow").sum()) if len(risk) else 0,
        "n_unscoreable": int((risk["flag"] == "unscoreable").sum()) if len(risk) else 0,
        "max_pc": float(risk["pc"].max()) if len(risk) else None,
    }


def risk_run_record(risk: pd.DataFrame, scenario: str, model: CovarianceModel, now: datetime) -> dict[str, Any]:
    """What ``run.json`` keeps about one scoring: when, which model, how many flags.

    The flag counts are kept **both ways** as well as combined -- over the events whose two
    objects both have a ballistic coefficient measured from their own decay, and over the rest.
    Step 4 found the storm term predictive only for the first group, so a red count that does not
    say which population it came from is not a number anybody should read. See
    :func:`driftwatch.storm.term.event_validity`.
    """
    validity = risk["storm_validity"].astype(str) if len(risk) and "storm_validity" in risk.columns else None
    return {
        "scenario": scenario,
        "computed_at": now.isoformat(),
        "model_version": model_version_string(model),
        **_flag_counts(risk),
        "by_storm_validity": {
            label: _flag_counts(risk[validity == label])
            for label in (
                storm_term.VALIDATED,
                storm_term.INDICATIVE,
                storm_term.OPERATOR_CONTROLLED,
                storm_term.NO_STORM_TERM,
            )
            if validity is not None and bool((validity == label).any())
        },
        "max_pc_variance_only": float(risk["pc_variance_only"].max()) if len(risk) else None,
        "max_abs_shift_km": float(
            np.nanmax(np.abs(risk[["shift_i_primary_km", "shift_i_secondary_km"]].to_numpy(dtype=float)))
        )
        if len(risk)
        else None,
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
        model = layer_spacex_ephemerides(model, objects, info, events)
    if args.scale != 1.0:
        model = ScaledCovariance(model, args.scale)
    try:
        model, _scenario = layer_storm_term(
            model,
            run_dir,
            objects,
            info,
            scenario_name=args.scenario,
            offline=args.offline,
            now=now,
            step_s=args.storm_step_s,
            offset_days=args.storm_offset_days,
        )
    except (ValueError, FileNotFoundError) as exc:
        log.error("%s", exc)
        return 2

    risk = run_risk(
        events,
        objects,
        model,
        scenario=args.scenario,
        run_id=info["run_id"],
        snapshot=info["snapshot"],
        supplemental_version=supplemental_version_string(info),
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
    print_scenario_comparison(run_dir, args.scenario, min(args.show, 12))
    print(run_dir.risk_path(args.scenario))
    return 0


def _print_table(title: str, table: dict[str, Any] | list[dict[str, Any]]) -> None:
    """A dict-of-dicts or list-of-dicts as an aligned block, without pulling in a table library."""
    rows = (
        [{"": str(k), **{ck: cv for ck, cv in v.items()}} for k, v in table.items()]
        if isinstance(table, dict)
        else list(table)
    )
    print(f"\n{title}")
    if not rows:
        print("  (nothing)")
        return
    columns = list(rows[0])
    widths = {c: max(len(str(c)), *(len(f"{r.get(c, '')}") for r in rows)) for c in columns}
    print("  " + "  ".join(str(c).rjust(widths[c]) for c in columns))
    for row in rows:
        print("  " + "  ".join(f"{row.get(c, '')}".rjust(widths[c]) for c in columns))


def cmd_storm_check(args: argparse.Namespace) -> int:
    """Attack the storm result and report what cannot be scored. See storm/diagnostics.py."""
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    info = run_dir.read_run()
    events = run_dir.read_events()
    objects = run_dir.read_objects()
    coefficients = run_dir.read_ballistic() if run_dir.ballistic_path.exists() else pd.DataFrame()
    try:
        altitudes = diagnostics.mean_altitudes_km(elements_for_run(info))
    except FileNotFoundError as exc:
        log.warning(
            "Cannot rebuild the run's element sets (%s); splitting on the altitude at closest "
            "approach instead, which a conjunction makes nearly the same for both objects",
            exc,
        )
        altitudes = None
    stored = [s for s in run_dir.scenarios() if s != config.SCENARIO_QUIET]
    names = [args.scenario] if args.scenario else stored
    if not names:
        log.error(
            "run %s has no scored scenario but quiet; run `driftwatch risk %s --scenario storm-g5` first",
            run_dir.name,
            run_dir.name,
        )
        return 2

    checks: dict[str, Any] = info.get("storm_check", {})
    for name in names:
        if not run_dir.risk_path(name).exists():
            log.error("run %s has no stored risk table for scenario %r", run_dir.name, name)
            return 2
        risk = run_dir.read_risk(name)
        frame = diagnostics.cancellation_frame(risk, events, coefficients, altitudes)
        cancel = diagnostics.cancellation(frame, min_events=args.min_events)
        effects = diagnostics.effect_split(frame)
        bad = diagnostics.unscoreable_objects(risk, events, objects, coefficients)
        bad_summary = diagnostics.unscoreable_summary(bad)

        print(
            f"\n=== {name} on {run_dir.name}: {cancel.get('n_events', 0)} scoreable events with both objects "
            f"free-flying ({cancel.get('n_excluded_operator_controlled', 0)} with an operator-controlled side "
            "left out: one displacement is zero by rule there, so the ratio would be 2 by construction) ==="
        )
        if cancel.get("n_events"):
            print(
                f"\nOverall: relative shift {cancel['overall']['median_relative_km']} km against an absolute "
                f"{cancel['overall']['median_absolute_km']} km, a ratio of {cancel['overall']['median_ratio']} "
                f"(p90 {cancel['overall']['p90_ratio']}). Rank correlation of the ratio with the altitude "
                f"difference: {cancel['spearman_ratio_vs_altitude_difference']}"
            )
            # Validated first, combined last, and never the combined figure on its own: the
            # term is measured only where both objects have a coefficient fitted from their own
            # decay. Same numbers either way; the label says how far the validation reaches.
            print(
                "\nStorm-term validity. `validated` means BOTH objects have a ballistic coefficient"
                "\nmeasured from their own decay, which is the only population Step 4's May 2024 test"
                "\nreaches (the right sign on about nine in ten at three to four days of lead, no skill"
                "\ninside two, no demonstrated skill otherwise). Nothing is weighted or"
                "\nwithheld by the label; it says how far the validation goes, not how large the shift is."
                "\nAn operator-controlled object is given no mean shift, so an event with one such side is"
                "\njudged on its free-flying side alone (2026-09-05)."
            )
            _print_table("", cancel["by_storm_validity"])
            _print_table("By ballistic coefficient source pair", cancel["by_b_source_pair"])
            _print_table("By whether the two sources are the same", cancel["by_shared_source"])
            print(
                f"\nBy the difference in *orbital* altitude (their median difference at the encounter "
                f"itself is only {cancel['median_tca_altitude_difference_km']} km -- a conjunction is a "
                f"near-coincidence in position, so that axis has no range):"
            )
            _print_table("", cancel["by_altitude_difference"])
            for label, table in cancel.get("by_altitude_difference_per_validity", {}).items():
                if label == "combined":
                    continue  # the table immediately above is the combined one
                spearman = cancel.get("spearman_per_validity", {}).get(label)
                _print_table(f"  ... {label} only (rank correlation {spearman})", table)
            if "by_storm_validity" in effects:
                for label, split in effects["by_storm_validity"].items():
                    _print_table(
                        f"Probability: combined, shift only, variance only -- {label} ({split['n_events']} events)",
                        split["bands"],
                    )
            else:
                _print_table("Probability: combined, shift only, variance only", effects["bands"])
        print(f"\nUnscoreable: {bad_summary.get('n_objects', 0)} objects over {bad_summary.get('n_events', 0)} events")
        if len(bad):
            print(bad.head(args.show).to_string(index=False))
            print(f"  by category: {bad_summary.get('by_category')}")
            print(f"  by coefficient source: {bad_summary.get('by_b_source')}")
            print(f"  by altitude band: {bad_summary.get('by_alt_band')}")
        checks[name] = {"cancellation": cancel, "effects": effects, "unscoreable": bad_summary}

    info["storm_check"] = checks
    run_dir.write_run(info)
    print(f"\n{run_dir.run_json}")
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
    scenario = args.scenario or default_scenario(scenarios)
    if scenarios and scenario not in scenarios:
        log.error("Run %s has no scenario %r; it has %s", run_dir.name, scenario, scenarios)
        return 2
    write_outputs(
        run_dir,
        elements_for_run(info),
        scenario=scenario,
        export=not args.no_viewer,
        show=0,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    print(run_dir.path / "report.md")
    return 0


def cmd_replay_bundle(args: argparse.Namespace) -> int:
    """The Step 5 replay timeline: the Kp bar, the density ratios and the Sun frames on one grid.

    Writes ``storm.json`` beside the replay run's own conjunctions bundle. It does **not** write
    the catalogue export or the conjunctions: those are `driftwatch propagate --export-dir` and
    `driftwatch report --out-dir` over the historical snapshot, because they are the same two
    exports the live viewer uses and duplicating them here would be a second code path that
    could drift from the first.
    """
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    info = run_dir.read_run()
    stored = run_dir.scenarios()
    scenario = args.scenario or next((s for s in stored if storm_scenarios.is_replay(s)), None)
    if scenario is None:
        log.error(
            "run %s has no replay scenario; score one with `driftwatch risk %s --scenario replay:<YYYY-MM-DD>`",
            run_dir.name,
            run_dir.name,
        )
        return 2
    days = (parse_utc(info["end"]) - parse_utc(info["start"])).total_seconds() / 86400.0
    start, end = storm_export.replay_window(scenario, days)
    now = datetime.now(UTC)

    frames = storm_export.replay_frames(start, end, offline=args.offline)
    if not frames and not args.offline:
        log.warning("Helioviewer returned no frames for %s to %s; the timeline will have no Sun", start, end)
    elif not frames:
        log.warning(
            "No cached Sun frames for %s to %s. Run without --offline to fetch them, "
            "a few per day as `docs/data-sources.md` describes",
            start.date(),
            end.date(),
        )

    sources, provenance = weather_sources(now=now, offline=args.offline, as_of=None)
    table_start, table_end = density_mod.weather_window(start, end)
    table = weather_table.weather_table(table_start, table_end, sources, now=now)
    # A second table over the quiet control window, because the density ratio's denominator is
    # three weeks earlier than its numerator and one table cannot hold both without spanning the
    # storm it is supposed to be a baseline for.
    quiet_start, quiet_end = (parse_utc(s) for s in config.GANNON_QUIET_WINDOW)
    baseline_start, baseline_end = density_mod.weather_window(quiet_start, quiet_end)
    baseline_table = weather_table.weather_table(baseline_start, baseline_end, sources, now=now)
    out_dir = Path(args.out_dir) if args.out_dir else config.VIEWER_DATA_DIR / "replay"
    bundle = storm_export.build_storm_bundle(
        scenario=scenario,
        start=start,
        end=end,
        table=table,
        frames=frames,
        out_dir=out_dir,
        baseline_table=baseline_table,
        run_id=info.get("run_id"),
        snapshot=info.get("snapshot"),
    )
    bundle["weather_provenance"] = provenance
    path = storm_export.write_storm_bundle(bundle, out_dir)
    peak = max((k for k in bundle["kp"]["kp"] if k is not None), default=None)
    print(
        f"{path}\n"
        f"  {len(bundle['kp']['t'])} three-hour intervals, peak Kp {peak}, "
        f"{len(bundle['sun']['frames'])} Sun frames "
        f"({bundle['sun']['total_bytes'] / 1024 / 1024:.1f} MiB)"
    )
    for altitude in storm_export.REPLAY_ALTITUDES_KM:
        ratios = [r for r in bundle["density"][f"ratio_{int(altitude)}km"] if r is not None]
        if ratios:
            print(f"  density ratio at {int(altitude)} km: {min(ratios):.2f} to {max(ratios):.2f} over the window")
    print(
        "  the ratio's denominator is the quiet control window "
        f"{bundle['density']['quiet_window'][0][:10]} to {bundle['density']['quiet_window'][1][:10]}, "
        "the same one Step 4 measured the enhancement against"
    )
    return 0


def cmd_check_bundle(args: argparse.Namespace) -> int:
    """Check what is about to be published: no redistributed files, no credentials, nothing oversized.

    Run before every deploy (``scripts/deploy-pages.ps1`` does it for you). The rules and the
    reasoning are in ``driftwatch/export/audit.py``; the short version is that SpaceX's
    ephemerides are analysis-only and Space-Track's credentials live in the environment, and
    neither may reach a CDN.
    """
    directory = Path(args.dir) if args.dir else config.VIEWER_DATA_DIR
    findings, summary = audit_bundle(directory, max_file_bytes=args.max_file_mib * 1024 * 1024)
    print(f"{summary['n_files']} files, {summary.get('total_mib', 0)} MiB total, in {directory}")
    for entry in summary.get("largest", []):
        print(f"  {entry['mib']:8.2f} MiB  {entry['path']}")
    if summary.get("headroom_mib") is not None:
        print(
            f"largest file is {summary['largest'][0]['mib']} MiB against the "
            f"{summary['limit_mib']} MiB per-file ceiling "
            f"({summary['headroom_mib']} MiB of headroom)"
        )
    for finding in findings:
        print(finding)
    if summary.get("n_errors"):
        log.error("%d problems would be published; not fit to deploy", summary["n_errors"])
        return 1
    print("OK: nothing redistributed, no credentials, every file inside the limit")
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
        if not args.no_roll:
            rolled = swpc.roll_solar_wind(now=now)
            if rolled["n_rolled"]:
                print(
                    f"rolled {rolled['n_rolled']} minute-cadence solar wind files older than "
                    f"{config.SOLAR_WIND_MINUTE_DAYS} days into hourly means "
                    f"({rolled['kilobytes_freed']} kB freed, archive now {rolled['archive_rows']} hours)"
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
    print("skill:     ", summary["by_skill"])
    print("sources:   ", {k: v for k, v in summary["by_source"].items()})
    print(
        f"ap sigma:   {summary['ap_sigma']['min']} to {summary['ap_sigma']['max']} nT "
        f"(climatological spread {summary['ap_sigma']['climatological']} nT, "
        f"{summary['ap_sigma']['climatological_from']}, over the last {config.AP_CLIMATOLOGY_DAYS} days)"
    )
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


def weather_for_density(now: datetime, start: datetime, end: datetime, *, offline: bool) -> pd.DataFrame:
    """A space weather table covering the window plus the history NRLMSIS needs behind it."""
    table_start, table_end = density_mod.weather_window(start, end)
    sources, used = weather_sources(now=now, offline=offline)
    table = weather_table.weather_table(table_start, table_end, sources, now=now)
    summary = weather_table.table_summary(table)
    log.info("Space weather for the density model: %s", {k: summary[k] for k in ("range", "by_skill", "n_missing")})
    if summary["n_missing"]:
        log.warning("%d intervals have no space weather at all; density there will be NaN", summary["n_missing"])
    table.attrs["sources_used"] = used
    return table


def historical_history(ids: list[int], *, end: datetime, days: int, offline: bool) -> pd.DataFrame:
    """Pull and load ``gp_history`` for a window in the past, then read it back for those ids.

    ``use_stored=False``: an object with a 2026 element set is "held through 2026", which says
    nothing at all about 2024 and would skip the pull entirely. See
    :func:`driftwatch.catalogue.history.backfill`.
    """
    result = history.backfill(
        ids,
        end=end,
        days=days,
        cache_dir=config.CACHE_DIR,
        history_dir=config.HISTORY_DIR,
        offline=offline,
        use_stored=False,
    )
    log.info(
        "History: %d requests, %d cached, %d element sets",
        result.n_requests,
        result.n_cached_requests,
        result.n_records,
    )
    sets = history.load_history(norad_ids=ids, start=end - timedelta(days=days + 1), end=end, include_snapshots=False)
    log.info(
        "Loaded %d element sets for %d of %d objects over %s to %s",
        len(sets),
        sets["norad_id"].nunique() if len(sets) else 0,
        len(ids),
        (end - timedelta(days=days)).date(),
        end.date(),
    )
    return sets


def gannon_coefficients(pre_storm: pd.DataFrame, sets: pd.DataFrame, grid: Any, pivot: datetime) -> pd.DataFrame:
    """Ballistic coefficients fitted from **pre-storm** history only.

    The discipline the whole test rests on. A coefficient fitted over a window that includes the
    storm has absorbed the storm's own drag, and using it to predict that storm would be fitting
    the answer. So the history is cut at the pivot and the fit is given nothing else.
    """
    before = sets[pd.to_datetime(sets["epoch"], utc=True) <= pd.Timestamp(pivot)]
    log.info("Fitting pre-storm ballistic coefficients from %d element sets", len(before))
    frame = ballistic_mod.coefficients(
        pre_storm,
        grid,
        before,
        fit_days=config.BALLISTIC_FIT_DAYS,
        budget_s=0,
        store=None,
        step_scale=config.BALLISTIC_FIT_STEP_SCALE,
        now=pivot,
    )
    log.info("Pre-storm coefficients: %s", ballistic_mod.summary(frame))
    return frame


def gannon_selection(args: argparse.Namespace, pivot: datetime, now: datetime) -> tuple[list[int], pd.DataFrame, int]:
    """The objects to measure, spread over the altitude range, and the size of what is missing.

    Taken from today's catalogue, which is the bias worth stating before any number is read:
    every object that has decayed since May 2024 is absent, and a storm's most affected objects
    are precisely the ones that came down. SATCAT knows how many those are, so the count is
    reported rather than left as a caveat.
    """
    current = snapshot.read_snapshot(snapshot.latest_snapshot(config.SNAPSHOT_DIR))
    perigee = pd.to_numeric(current["perigee_km"], errors="coerce")
    band = current[(perigee >= args.min_perigee_km) & (perigee <= args.max_perigee_km)]
    if args.category:
        band = band[band["category"].astype(str).isin({c.strip() for c in args.category.split(",")})]
    order = band.sort_values("perigee_km")
    step = max(len(order) // max(int(args.sample), 1), 1)
    chosen = order.iloc[::step].head(int(args.sample))
    ids = sorted({int(i) for i in chosen["norad_id"]})

    satcat_frame = satcat.load_satcat(satcat.fetch_satcat(cache_dir=config.CACHE_DIR, now=now, offline=True))
    gone = satcat_frame[
        satcat_frame["decay_date"].notna()
        & (satcat_frame["decay_date"] > pivot.date())
        & (satcat_frame["launch_date"] <= pivot.date())
    ]
    log.info(
        "Selected %d objects with perigee %g to %g km, spread over the range, from today's catalogue. "
        "SATCAT records %d objects that were in orbit on %s and have decayed since; none of them can "
        "be in this selection, so it is survivorship-biased against the objects a storm affects most.",
        len(ids),
        args.min_perigee_km,
        args.max_perigee_km,
        len(gone),
        pivot.date(),
    )
    return ids, current, int(len(gone))


def cmd_validate_gannon(args: argparse.Namespace) -> int:
    """The May 2024 storm: the density enhancement first, then the in-track error it caused."""
    now = datetime.now(UTC)
    storm = validation.Window("storm", *(parse_utc(t) for t in config.GANNON_STORM_WINDOW))
    quiet = validation.Window("quiet", *(parse_utc(t) for t in config.GANNON_QUIET_WINDOW))
    pivot = parse_utc(config.GANNON_PIVOT)
    quiet_pivot = parse_utc(config.GANNON_QUIET_PIVOT)
    end = parse_utc(config.GANNON_HISTORY_END)

    ids, current, n_gone = gannon_selection(args, pivot, now)
    sets = historical_history(ids, end=end, days=int(args.days), offline=args.offline)
    if not len(sets):
        log.error("no element sets came back for the window; nothing to validate against")
        return 2
    sets = sets.merge(current[["norad_id", "category"]], on="norad_id", how="left")
    sets["category"] = sets["category"].astype("string").fillna("unknown")

    table = weather_for_density(now, parse_utc("2024-04-01T00:00:00Z"), end, offline=args.offline)
    grid = density_mod.weather_grid(table)
    pre_storm = (
        sets[pd.to_datetime(sets["epoch"], utc=True) <= pd.Timestamp(pivot)]
        .sort_values("epoch")
        .drop_duplicates("norad_id", keep="last")
        .reset_index(drop=True)
    )

    # 1. The density enhancement, from the objects' own mean motion. No coefficient needed.
    rates = validation.decay_rates(sets, [quiet, storm])
    observed = validation.observed_density_ratio(rates, "storm", "quiet", min_snr=args.min_snr)
    usable = observed[observed["usable"]]
    modelled = validation.modelled_density_ratio(
        pre_storm[pre_storm["norad_id"].isin(usable["norad_id"])], grid, storm, quiet
    )
    ratios = validation.density_ratios(usable, modelled)
    print(f"\n=== May 2024, the density enhancement: {len(ratios)} objects with two usable decay rates ===")
    print(f"   of {observed['norad_id'].nunique()} with rates at all, from {sets['norad_id'].nunique()} pulled")
    if len(ratios):
        for label, column in (("observed", "observed_ratio"), ("NRLMSIS", "modelled_ratio")):
            print(
                f"{label:>9} storm/quiet: median {ratios[column].median():.2f}, "
                f"p10 {ratios[column].quantile(0.1):.2f}, p90 {ratios[column].quantile(0.9):.2f}"
            )
        print(f"observed / modelled: median {ratios['ratio_of_ratios'].median():.3f}")
        bands = pd.cut(ratios["altitude_km"], bins=[0, 350, 450, 550, 650, 800, 2000])
        by_band = ratios.groupby(bands, observed=True).agg(
            n=("norad_id", "size"),
            observed=("observed_ratio", "median"),
            modelled=("modelled_ratio", "median"),
            ratio=("ratio_of_ratios", "median"),
        )
        print("\nby altitude:")
        print(by_band.round(3).to_string())

    # 2. The in-track error of the pre-storm element sets, against a quiet control at the same lead.
    coefficients = gannon_coefficients(pre_storm, sets, grid, pivot)
    observed_shifts, control_shifts, predicted = [], [], []
    for norad_id, object_sets in sets.groupby("norad_id"):
        storm_rows = validation.in_track_errors(object_sets, pivot, storm)
        control_rows = validation.in_track_errors(object_sets, quiet_pivot, quiet)
        if len(storm_rows):
            observed_shifts.append(storm_rows)
            coefficient = validation.coefficient_for(coefficients, int(norad_id))
            predicted.append(validation.predicted_shifts(object_sets, coefficient, grid, pivot, storm_rows["epoch"]))
        if len(control_rows):
            control_shifts.append(control_rows)
    if not observed_shifts:
        log.error("no object had both a pre-storm element set and a set issued during the storm")
        return 2

    observed_frame = pd.concat(observed_shifts, ignore_index=True)
    control_frame = pd.concat(control_shifts, ignore_index=True) if control_shifts else pd.DataFrame()
    predicted_frame = pd.concat([p for p in predicted if len(p)], ignore_index=True)
    residual = validation.residuals(observed_frame, predicted_frame, control_frame)
    altitude = observed.set_index("norad_id")["altitude_km"]
    summary = validation.residual_summary(residual, by_altitude=altitude)

    print(f"\n=== May 2024, the in-track error of pre-storm element sets: {len(residual)} comparisons ===")
    print(
        f"pivot {pivot.date()}, storm window {storm.start.date()} to {storm.end.date()}; "
        f"control pivot {quiet_pivot.date()}, control window {quiet.start.date()} to {quiet.end.date()}"
    )
    if len(control_frame):
        print(
            f"control: SGP4 alone drifts a median {control_frame['observed_shift_km'].abs().median():.3f} km "
            f"in track over {control_frame['lead_days'].median():.1f} days, p90 "
            f"{control_frame['observed_shift_km'].abs().quantile(0.9):.3f} km"
        )
    keys = ("n", "n_objects", "median_observed_km", "median_predicted_km", "median_residual_km", "slope")
    for key in keys:
        print(f"  {key}: {summary.get(key)}")
    for label, key in (
        ("free-flying", "free_flying"),
        ("free-flying, coefficient measured", "free_flying_measured_coefficient"),
    ):
        block = summary.get(key, {})
        if block:
            print(
                f"  {label} ({block.get('n')} comparisons over {block.get('n_objects')} objects): "
                f"observed {block.get('median_observed_km')} km against a predicted "
                f"{block.get('median_predicted_km')} km; slope {block.get('slope')}, "
                f"robust slope {block.get('slope_robust')}, correlation {block.get('correlation')}"
            )
    for title, key in (
        ("by lead time (days)", "by_lead_day"),
        ("by altitude", "by_altitude_km"),
        ("by ballistic coefficient source", "by_b_source"),
    ):
        if summary.get(key):
            _print_table(title, {str(k): v for k, v in summary[key].items()})

    out = Path(args.out or config.DATA_DIR / "validation")
    out.mkdir(parents=True, exist_ok=True)
    if len(ratios):
        ratios.to_parquet(out / "gannon_density_ratios.parquet", index=False)
    residual.to_parquet(out / "gannon_in_track.parquet", index=False)
    if len(control_frame):
        control_frame.to_parquet(out / "gannon_control.parquet", index=False)
    record = {
        "built_at": now.isoformat(),
        "windows": {"storm": storm.as_dict(), "quiet": quiet.as_dict()},
        "pivots": {"storm": pivot.isoformat(), "quiet": quiet_pivot.isoformat()},
        "selection": {
            "n_requested": len(ids),
            "n_with_history": int(sets["norad_id"].nunique()),
            "min_perigee_km": args.min_perigee_km,
            "max_perigee_km": args.max_perigee_km,
            "n_in_orbit_then_and_decayed_since": n_gone,
        },
        "coefficients": ballistic_mod.summary(coefficients),
        "density_enhancement": {
            "n_objects": int(len(ratios)),
            "observed_median": round(float(ratios["observed_ratio"].median()), 4) if len(ratios) else None,
            "modelled_median": round(float(ratios["modelled_ratio"].median()), 4) if len(ratios) else None,
            "observed_over_modelled_median": round(float(ratios["ratio_of_ratios"].median()), 4)
            if len(ratios)
            else None,
        },
        "in_track": summary,
        "control": {
            "n": int(len(control_frame)),
            "median_abs_km": round(float(control_frame["observed_shift_km"].abs().median()), 4)
            if len(control_frame)
            else None,
        },
    }
    (out / "gannon.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    print(f"\n{out / 'gannon.json'}")
    return 0


def cmd_validate_swarm(args: argparse.Namespace) -> int:
    """Calibrate public element sets against ESA's precise orbits for Swarm A, B and C; see ``storm/precise.py``."""
    from driftwatch.storm import precise

    now = datetime.now(UTC)
    wanted = [w for w in precise.WINDOWS if args.window in ("all", w.name)]
    if not wanted:
        log.error("no such window %r; choose all, quiet, storm or held-out", args.window)
        return 2
    ids = sorted(precise.SWARM.values())

    # Category and altitude band, for the covariance model's pools and defaults, from the latest snapshot
    # where there is one; Swarm is a payload in low Earth orbit either way.
    labels: dict[int, tuple[str, str]] = {i: ("payload", "leo") for i in ids}
    try:
        current = snapshot.read_snapshot(snapshot.latest_snapshot(config.SNAPSHOT_DIR))
        for row in current[current["norad_id"].isin(ids)].itertuples():
            labels[int(row.norad_id)] = (str(row.category), str(row.altitude_band))
    except FileNotFoundError:
        pass

    # Every element set from the covariance history before the earliest window to the last truth.
    frames = []
    for window in wanted:
        start = window.sets_from - timedelta(days=precise.COVARIANCE_HISTORY_DAYS + 1)
        frames.append(
            historical_history(ids, end=window.truth_to, days=(window.truth_to - start).days, offline=args.offline)
        )
    sets = pd.concat(frames, ignore_index=True).drop_duplicates(["norad_id", "epoch"]) if frames else pd.DataFrame()
    if not len(sets):
        log.error("no element sets came back for Swarm; nothing to calibrate")
        return 2
    sets = sets.merge(
        pd.DataFrame({"norad_id": ids, "category": [labels[i][0] for i in ids]}), on="norad_id", how="left"
    )

    # The observed space weather over the whole span, for the storm term. Nothing forecast.
    grid = None
    weather_used = None
    if not args.no_storm_term:
        table = weather_for_density(
            now,
            min(w.sets_from for w in wanted) - timedelta(days=precise.COEFFICIENT_HISTORY_DAYS + 3),
            max(w.truth_to for w in wanted),
            offline=args.offline,
        )
        grid = density_mod.weather_grid(table)
        weather_used = table.attrs.get("sources_used")

    trials: list[pd.DataFrame] = []
    orbits: dict[str, precise.PreciseOrbit] = {}
    records: dict[str, precise.ThrusterRecord | None] = {}
    for window in wanted:
        for letter, norad_id in precise.SWARM.items():
            key = f"{letter} ({window.name})"
            day_from = (window.sets_from - timedelta(days=1)).date()
            orbit = precise.load_precise_orbit(letter, day_from, window.truth_to.date(), offline=args.offline)
            orbits[key] = orbit
            # ESA's published thruster record decides the manoeuvre exclusion; the project's own
            # detection is computed beside it as a cross-check. Without the record, detection decides.
            record: precise.ThrusterRecord | None = None
            if not args.no_esa_record:
                try:
                    record = precise.load_thruster_record(
                        letter, day_from, window.truth_to.date(), offline=args.offline
                    )
                except (OSError, httpx.HTTPError, ImportError, ValueError) as exc:
                    log.warning(
                        "Swarm %s, %s window: ESA's thruster record is unavailable (%s); manoeuvres will be "
                        "detected instead",
                        letter,
                        window.name,
                        exc,
                    )
            records[key] = record
            category, band = labels[norad_id]
            inputs = precise.fit_inputs(
                norad_id, sets, window, grid, label=letter, category=category, altitude_band=band
            )
            log.info(
                "Swarm %s, %s window: %d trial sets, covariance %s from %d sets (%s to %s), coefficient %s",
                letter,
                window.name,
                len(inputs.trial_sets),
                inputs.covariance_source,
                inputs.covariance_history[2],
                inputs.covariance_history[0],
                inputs.covariance_history[1],
                None
                if inputs.coefficient is None
                else f"{float(inputs.coefficient['b_m2_kg']):.4f} m2/kg ({inputs.coefficient.get('source')})",
            )
            if not len(inputs.trial_sets):
                continue
            trials.append(precise.satellite_trials(inputs, orbit, window, grid, record=record))
    if not trials:
        log.error("no trials: no element set fell inside any window")
        return 2
    frame = pd.concat(trials, ignore_index=True)
    summary = precise.summarise(frame)
    sources = precise.sources_record(orbits, retrieved_at=now, weather_sources=weather_used, records=records)

    out = Path(args.out or config.DATA_DIR / "validation")
    out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out / "swarm_benchmark.parquet", index=False)
    record = {
        "built_at": now.isoformat(),
        "windows": {w.name: w.as_dict() for w in wanted},
        "leads_hours": list(precise.LEADS_HOURS),
        "summary": summary,
        "sources": sources,
    }
    (out / "swarm_benchmark.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    text = precise.to_markdown(summary, sources, {w.name: w for w in wanted}, built_at=now)
    if args.page:
        page = Path(args.page)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(text + "\n", encoding="utf-8")
        log.info("Wrote %s", page)
    for name, w in summary["windows"].items():
        h = w["horizon"]
        print(
            f"\n=== {name} ({w['role']}): {w['n_sets']} sets; horizon within {h['last_lead_h_within']} h, beyond at "
            f"{h['first_lead_h_beyond']} h"
        )
        for lead, e in w["by_lead_h"].items():
            i, s = e["in_track"], e["storm_term"]
            print(
                f"  {float(lead):5g} h  n={e['n']:3d}  in-track median {i['median_km']:7.2f} p95 {i['p95_km']:8.2f} "
                f"km  "
                f"inside 1s {i['inside_1_sigma']:.0%} 2s {i['inside_2_sigma']:.0%}  storm term: "
                + (
                    f"{s['median_abs_raw_km']:.2f} -> {s['median_abs_corrected_km']:.2f} km ({s['improvement']:+.0%})"
                    if s["n"] and s["improvement"] is not None
                    else "n/a"
                )
            )
    print(f"\n{out / 'swarm_benchmark.json'}")
    return 0


def cmd_local(args: argparse.Namespace) -> int:
    """An operator's own files through the provenance check, the CDM matcher and the ephemeris benchmark, offline.

    Every outbound request is refused for the duration (``driftwatch.local.no_network``), so the
    messages, the ephemeris and the records never leave the machine; what is read comes from the
    operator's files, the local run and history stores, and the cached space weather. See
    ``docs/local-analysis.md``.
    """
    from driftwatch import local as local_mod
    from driftwatch.storm import precise

    now = datetime.now(UTC)
    out = Path(args.out)
    if not any([args.run, args.cdm, args.ephemeris]):
        log.error("nothing to do: give --run, --cdm (with --run), or --ephemeris with --norad")
        return 2
    if args.cdm and not args.run:
        log.error("--cdm needs --run: the messages are matched to a stored run")
        return 2
    if args.ephemeris and args.norad is None:
        log.error("--ephemeris needs --norad: which public catalogue object the ephemeris describes")
        return 2
    report: dict[str, Any] = {
        "built_at": now.isoformat(),
        "network": "every outbound request refused for the duration (driftwatch.local.no_network)",
        "sources": [],
    }
    with local_mod.no_network():
        try:
            if args.run:
                run_dir = resolve_run(args.run)
                result = check_run(run_dir, max_snapshot_age_hours=args.max_snapshot_age_hours, now=now)
                for warning in result.warnings:
                    log.warning("%s", warning)
                for problem in result.problems:
                    log.error("%s", problem)
                report["provenance"] = {
                    "run": run_dir.name,
                    "path": str(run_dir.path),
                    "snapshot": result.snapshot.name if result.snapshot else None,
                    "snapshot_fetched_at": result.fetched_at.isoformat() if result.fetched_at else None,
                    "snapshot_age_hours": round(result.age_hours, 3) if result.age_hours is not None else None,
                    "warnings": result.warnings,
                    "problems": result.problems,
                    "ok": result.ok,
                }
                report["sources"].append(
                    {
                        "source": "Stored run",
                        "origin": f"{run_dir.path} (run.json, events, objects and risk tables written by driftwatch on "
                        f"this machine); snapshot {result.snapshot.name if result.snapshot else 'unresolved'}",
                    }
                )
                if args.cdm:
                    messages = cdm_parse.load_cdms(Path(args.cdm))
                    if not messages:
                        log.error("no messages under %s", args.cdm)
                        return 2
                    match = cdm_match.match_cdms(
                        messages, run_dir.read_conjunctions(), tolerance_s=args.tolerance_s, scenario=args.scenario
                    )
                    print("\n".join(cdm_match.report_lines(match)))
                    report["cdm"] = {
                        "summary": match.summary,
                        "matches": json.loads(match.matches.to_json(orient="records", date_format="iso"))
                        if len(match.matches)
                        else [],
                        "unmatched_cdms": json.loads(match.unmatched_cdms.to_json(orient="records", date_format="iso"))
                        if len(match.unmatched_cdms)
                        else [],
                        "unwarned_flags": json.loads(match.unwarned_flags.to_json(orient="records", date_format="iso"))
                        if len(match.unwarned_flags)
                        else [],
                    }
                    report["sources"].append(
                        {
                            "source": "Conjunction Data Messages",
                            "origin": f"{len(messages)} message(s) under {args.cdm}, the operator's own, read on this "
                            "machine and copied nowhere",
                        }
                    )
            if args.ephemeris:
                segments = local_mod.load_oem(args.ephemeris)
                label = args.label or segments[0].object_name or str(args.norad)
                orbit = local_mod.oem_to_precise_orbit(segments, norad_id=int(args.norad), label=label)
                span = orbit.span
                if span is None:
                    log.error("the ephemeris holds no states")
                    return 2
                if args.sets:
                    records = json.loads(Path(args.sets).read_text(encoding="utf-8"))
                    sets = history.frame_from_records(records, source="local", fetched_at=now)
                    sets_origin = f"{len(sets)} OMM records from {args.sets}"
                else:
                    sets = history.load_history(
                        norad_ids=[int(args.norad)],
                        start=(span[0] - pd.Timedelta(days=precise.COVARIANCE_HISTORY_DAYS + 15)).tz_localize("UTC"),
                        end=span[1].tz_localize("UTC"),
                    )
                    sets_origin = f"{len(sets)} element sets from the local history store ({config.HISTORY_DIR})"
                if not len(sets):
                    log.error(
                        "no element sets for %s are held locally; pass --sets <OMM JSON>, or fetch history beforehand "
                        "with `driftwatch history` (which needs the network, and is not this command)",
                        args.norad,
                    )
                    return 2
                sets = sets.assign(category=sets.get("category", "payload"))
                published = local_mod.load_manoeuvre_records(args.manoeuvres) if args.manoeuvres else None
                grid = None
                weather_origin = "not used: --storm-term not given"
                if args.storm_term:
                    try:
                        table = weather_for_density(
                            now,
                            (span[0] - pd.Timedelta(days=precise.COEFFICIENT_HISTORY_DAYS + 3)).to_pydatetime(),
                            span[1].to_pydatetime(),
                            offline=True,
                        )
                        grid = density_mod.weather_grid(table)
                        weather_origin = f"cached observed record: {table.attrs.get('sources_used')}"
                    except (FileNotFoundError, ValueError, KeyError) as exc:
                        log.warning("Storm term skipped: no cached space weather (%s)", exc)
                        weather_origin = f"not available offline ({exc}); the storm term was skipped"
                leads = tuple(float(x) for x in str(args.leads).split(","))
                bench = local_mod.ephemeris_benchmark(
                    int(args.norad),
                    sets,
                    orbit,
                    label=label,
                    leads_hours=leads,
                    published=published,
                    grid=grid,
                    tolerance_km=args.tolerance_km,
                )
                out.mkdir(parents=True, exist_ok=True)
                bench.trials.to_parquet(out / "ephemeris_trials.parquet", index=False)
                coefficient = bench.inputs.coefficient
                report["ephemeris"] = {
                    "norad_id": int(args.norad),
                    "label": label,
                    "frame": orbit.frame,
                    "time_systems": sorted({seg.time_system for seg in segments}),
                    "span": [span[0].isoformat(), span[1].isoformat()],
                    "n_states": int(len(orbit.table)),
                    "n_files": len(orbit.files),
                    "files": orbit.files,
                    "window": bench.window.as_dict(),
                    "n_trial_sets": int(len(bench.inputs.trial_sets)),
                    "covariance_source": bench.inputs.covariance_source,
                    "covariance_history": [str(v) for v in bench.inputs.covariance_history],
                    "coefficient": None
                    if coefficient is None
                    else {"b_m2_kg": float(coefficient["b_m2_kg"]), "source": str(coefficient.get("source"))},
                    "manoeuvre_record": args.manoeuvres,
                    "leads_hours": list(leads),
                    "summary": bench.summary,
                }
                report["sources"] += [
                    {
                        "source": "Operator ephemeris",
                        "origin": f"{args.ephemeris} ({len(segments)} segment(s), frame {orbit.frame}, time system "
                        f"{', '.join(sorted({seg.time_system for seg in segments}))}), read on this machine and copied "
                        "nowhere; interpolated by cubic Hermite on its own velocities and rotated to TEME with astropy",
                    },
                    {"source": "Public element sets", "origin": sets_origin},
                    {
                        "source": "Manoeuvre record",
                        "origin": f"the operator's own, {args.manoeuvres}: decides the exclusion; the project's "
                        "detection is reported beside it"
                        if args.manoeuvres
                        else "none supplied: the project's own detection decides the exclusion",
                    },
                    {"source": "Space weather", "origin": weather_origin},
                ]
        except local_mod.NetworkRefused as exc:
            log.error("%s", exc)
            return 3
        except (FileNotFoundError, ValueError) as exc:
            log.error("%s", exc)
            return 2
    json_path, md_path = local_mod.write_report(report, out)
    print(md_path.read_text(encoding="utf-8"))
    print(json_path)
    return 0


def starlink_2022_control(args: argparse.Namespace, end: datetime) -> tuple[pd.DataFrame, list[int]]:
    """Starlinks already on station near 500 km through the same days, as the control group.

    The prompt asks for one and it earns its place: without it the fall at 210 km could be read
    as "the storm was large" rather than "the storm was large *down there*". These are payloads
    from the earlier shells, launched well before the window so they were done raising, and they
    are filtered on the perigee their own 2022 element sets show rather than on where they are
    today.
    """
    raw = pd.read_csv(
        satcat.satcat_path(config.CACHE_DIR),
        usecols=["OBJECT_NAME", "OBJECT_ID", "NORAD_CAT_ID", "OBJECT_TYPE", "LAUNCH_DATE", "DECAY_DATE"],
    )
    earlier = raw[
        raw["OBJECT_NAME"].astype(str).str.startswith("STARLINK")
        & (raw["OBJECT_TYPE"] == "PAY")
        & (pd.to_datetime(raw["LAUNCH_DATE"], errors="coerce") < pd.Timestamp("2021-12-01"))
    ]
    # Spread over the whole pre-2022 population rather than taken from the front of it: the
    # lowest catalogue numbers are the v0.9 demonstration batch, most of which was deorbited
    # long before this window, and a control drawn from them comes back nearly empty.
    pool = sorted({int(i) for i in earlier["NORAD_CAT_ID"]})
    wanted = max(int(args.control_sample) * 6, 1)
    candidates = pool[:: max(len(pool) // wanted, 1)][:wanted]
    if not candidates:
        return pd.DataFrame(), []
    sets = historical_history(candidates, end=end, days=int(config.STARLINK_2022_HISTORY_DAYS), offline=args.offline)
    if not len(sets):
        return pd.DataFrame(), []
    perigee = pd.Series(
        [
            ballistic_mod.perigee_altitude_km(float(m), float(e))
            for m, e in zip(sets["mean_motion"], sets["eccentricity"], strict=True)
        ],
        index=sets.index,
    )
    half = float(args.control_band_km)
    band = (perigee >= config.STARLINK_2022_CONTROL_KM - half) & (perigee <= config.STARLINK_2022_CONTROL_KM + half)
    keep = sets.loc[band, "norad_id"].value_counts()
    ids = [int(i) for i in keep[keep >= 5].index][: int(args.control_sample)]
    return sets[sets["norad_id"].isin(ids)].reset_index(drop=True), ids


def cmd_validate_starlink_2022(args: argparse.Namespace) -> int:
    """The February 2022 loss: what the public catalogue saw, and whether the model shows the drag.

    A narrower question than May 2024 and a harder one. The storm was a G1 -- the smallest
    named level -- and the altitude was about 210 km, low enough that the density is set mostly
    by the solar cycle and the diurnal bulge rather than by the geomagnetic term. So the test
    is not "is the enhancement the right size" but "does the model show elevated drag there at
    all", and the answer is reported either way without adjusting anything.
    """
    now = datetime.now(UTC)
    end = parse_utc(config.STARLINK_2022_HISTORY_END)
    storm_day = parse_utc(config.STARLINK_2022_STORM_DAY)
    quiet_day = parse_utc(config.STARLINK_2022_QUIET_DAY)

    raw = pd.read_csv(
        satcat.satcat_path(config.CACHE_DIR),
        usecols=["OBJECT_NAME", "OBJECT_ID", "NORAD_CAT_ID", "OBJECT_TYPE", "LAUNCH_DATE", "DECAY_DATE"],
    )
    launch = raw[raw["OBJECT_ID"].astype(str).str.startswith(config.STARLINK_2022_LAUNCH)].copy()
    launch["decayed"] = launch["DECAY_DATE"].notna()
    ids = sorted({int(i) for i in launch["NORAD_CAT_ID"]})

    # What the public catalogue actually holds about this launch, which is the first finding.
    payloads = launch[launch["OBJECT_TYPE"] == "PAY"]
    print("\n=== February 2022, what the catalogue saw ===")
    print(
        f"SpaceX launched 49 satellites on 3 February 2022. CelesTrak's SATCAT carries "
        f"{len(launch)} objects under {config.STARLINK_2022_LAUNCH}: {len(payloads)} payloads and "
        f"{len(launch) - len(payloads)} pieces of debris. "
        f"{int(payloads['decayed'].sum())} of the payloads have a decay date."
    )
    print(launch.sort_values("NORAD_CAT_ID").to_string(index=False))

    sets = historical_history(ids, end=end, days=int(config.STARLINK_2022_HISTORY_DAYS), offline=args.offline)
    if not len(sets):
        log.error("no element sets came back for the launch")
        return 2
    names = launch.set_index("NORAD_CAT_ID")["OBJECT_NAME"].to_dict()
    decay_dates = launch.set_index("NORAD_CAT_ID")["DECAY_DATE"].to_dict()

    tracks, rows = [], []
    for norad_id, object_sets in sets.groupby("norad_id"):
        track = validation.decay_history(object_sets)
        if not len(track):
            continue
        track["name"] = names.get(int(norad_id), "")
        tracks.append(track)
        rows.append(
            {
                **validation.lifetime_from_decay(track),
                "name": names.get(int(norad_id), ""),
                "decay_date": decay_dates.get(int(norad_id)),
            }
        )
    decay = pd.DataFrame(rows).sort_values("norad_id")
    print("\n=== The decay at insertion altitude, from the element sets themselves ===")
    columns = [
        "norad_id",
        "name",
        "n_sets",
        "span_days",
        "first_altitude_km",
        "last_altitude_km",
        "drop_km",
        "mean_rate_km_day",
        "decay_date",
    ]
    print(decay[[c for c in columns if c in decay.columns]].to_string(index=False))
    brief = decay[decay["span_days"] < 1.0]
    if len(brief):
        print(
            f"  {len(brief)} of these have under a day of element sets before they were lost, so their "
            "rate column is element-set scatter rather than a decay rate and two of them come out "
            "rising. The altitudes are still real; the rates are not."
        )

    # Does the model show elevated drag at the insertion altitude for that G1?
    table = weather_for_density(now, quiet_day - timedelta(days=5), end, offline=args.offline)
    print(f"\n=== Does NRLMSIS show elevated drag at {config.STARLINK_2022_INSERTION_KM:g} km for the G1? ===")
    ratios = []
    for altitude in (config.STARLINK_2022_INSERTION_KM, 300.0, 400.0, config.STARLINK_2022_CONTROL_KM):
        value = validation.storm_ratio_at(table, altitude, storm_day, quiet_at=quiet_day)
        ratios.append(value)
        print(
            f"  {altitude:5.0f} km: {storm_day.date()} {value['storm']:.3e} against "
            f"{quiet_day.date()} {value['quiet']:.3e}, ratio {value['ratio']:.3f}"
        )
    kp = weather_table.weather_table(
        *density_mod.weather_window(quiet_day - timedelta(days=2), end),
        weather_sources(now=now, offline=args.offline)[0],
        now=now,
    )
    inside = pd.to_datetime(kp["t"], utc=True).between(
        pd.Timestamp(storm_day) - pd.Timedelta(days=1), pd.Timestamp(storm_day) + pd.Timedelta(days=2)
    )
    print(
        f"  observed Kp over {storm_day.date()} +/- a day: max {kp.loc[inside, 'kp'].max():.2f}, "
        f"ap max {kp.loc[inside, 'ap'].max():.0f}"
    )

    # The control group: the same days, the same model, 500 km instead of 210.
    control, control_ids = starlink_2022_control(args, end)
    control_rows = []
    for _, object_sets in control.groupby("norad_id"):
        track = validation.decay_history(object_sets)
        if len(track):
            control_rows.append(validation.lifetime_from_decay(track))
    control_decay = pd.DataFrame(control_rows)
    print(f"\n=== The control group at {config.STARLINK_2022_CONTROL_KM:g} km, same days ===")
    if len(control_decay):
        print(
            f"{len(control_decay)} Starlinks launched before December 2021 and flying within "
            f"{args.control_band_km:g} km of "
            f"{config.STARLINK_2022_CONTROL_KM:g} km: median fall "
            f"{control_decay['drop_km'].median():.2f} km over "
            f"{control_decay['span_days'].median():.1f} days, "
            f"{control_decay['mean_rate_km_day'].median():.3f} km/day. The insertion group's survivors were "
            f"climbing and its losses fell at tens of km a day."
        )
    else:
        print("  no control objects came back with enough element sets in the window")

    out = Path(args.out or config.DATA_DIR / "validation")
    out.mkdir(parents=True, exist_ok=True)
    if tracks:
        pd.concat(tracks, ignore_index=True).to_parquet(out / "starlink2022_tracks.parquet", index=False)
    decay.to_parquet(out / "starlink2022_decay.parquet", index=False)
    record = {
        "built_at": now.isoformat(),
        "catalogue": {
            "launch": config.STARLINK_2022_LAUNCH,
            "n_launched": 49,
            "n_catalogued": int(len(launch)),
            "n_payloads_catalogued": int(len(payloads)),
            "n_payloads_with_decay_date": int(payloads["decayed"].sum()),
            "n_with_element_sets": int(sets["norad_id"].nunique()),
        },
        "decay": decay.to_dict(orient="records"),
        "control": {
            "target_km": config.STARLINK_2022_CONTROL_KM,
            "n_objects": int(len(control_decay)),
            "norad_ids": control_ids,
            "median_drop_km": round(float(control_decay["drop_km"].median()), 3) if len(control_decay) else None,
            "median_rate_km_day": round(float(control_decay["mean_rate_km_day"].median()), 4)
            if len(control_decay)
            else None,
        },
        "density_ratios": ratios,
        "observed_kp_max": round(float(kp.loc[inside, "kp"].max()), 2),
        "observed_ap_max": round(float(kp.loc[inside, "ap"].max()), 1),
    }
    (out / "starlink2022.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    print(f"\n{out / 'starlink2022.json'}")
    return 0


def cmd_density(args: argparse.Namespace) -> int:
    """The density sanity checks: quiet profile, storm ratios, and the sampling-step convergence."""
    now = parse_utc(args.at) if args.at else datetime.now(UTC)
    table = weather_for_density(now, now, now + timedelta(days=1), offline=args.offline)

    profile = density_mod.quiet_density_profile(table, at=now)
    print(f"NRLMSIS {config.MSIS_VERSION} at {now.isoformat(timespec='minutes')}, averaged over 24 local times")
    print(
        f"drivers: F10.7 (previous day) {profile.attrs['f107']:.1f}, 81-day centred "
        f"{profile.attrs['f107a']:.1f}, daily Ap {profile.attrs['ap_daily']:.1f}"
    )
    shown = profile.copy()
    for column in ("rho_mean_kg_m3", "rho_min_kg_m3", "rho_max_kg_m3"):
        shown[column] = shown[column].map(lambda x: f"{x:.3e}")
    shown["day_night_ratio"] = shown["day_night_ratio"].round(2)
    print(shown.to_string(index=False))

    for kp, name in ((7.0, "G3"), (9.0, "G5")):
        ratio = density_mod.storm_ratio(table, kp, at=now)
        print(f"\n{name} storm (Kp {kp:g}, ap {weather_table.kp_to_ap(np.array([kp]))[0]:.0f}), applied for 24 h:")
        out = ratio.copy()
        for column in ("rho_quiet_kg_m3", "rho_storm_kg_m3"):
            out[column] = out[column].map(lambda x: f"{x:.3e}")
        out["ratio"] = out["ratio"].round(2)
        print(out.to_string(index=False))

    if args.convergence:
        print("\nSampling-step convergence (one day, against a 10 s step):")
        objects = snapshot.read_snapshot(snapshot.latest_snapshot(config.SNAPSHOT_DIR))
        leo = objects[(objects["perigee_km"] > 200) & (objects["perigee_km"] < 700)]
        rows = []
        for lo, hi in ((0.0, 0.002), (0.002, 0.01), (0.01, 0.05), (0.05, 0.15), (0.15, 0.4), (0.4, 0.8)):
            band = leo[(leo["eccentricity"] >= lo) & (leo["eccentricity"] < hi)]
            if not len(band):
                continue
            row = band.sort_values("perigee_km").iloc[len(band) // 2]
            step = density_mod.sample_step_s(float(row["mean_motion"]), float(row["eccentricity"]))
            end = now + timedelta(days=1)
            rule = density_mod.mean_density(density_mod.density_along_orbit(row, table, now, end, step_s=step))
            fixed = density_mod.mean_density(density_mod.density_along_orbit(row, table, now, end, step_s=600.0))
            fine = density_mod.mean_density(density_mod.density_along_orbit(row, table, now, end, step_s=10.0))
            rows.append(
                {
                    "norad_id": int(row["norad_id"]),
                    "name": str(row["name"])[:22],
                    "e": round(float(row["eccentricity"]), 4),
                    "perigee_km": round(float(row["perigee_km"]), 1),
                    "step_s": round(step, 1),
                    "rule_err_pct": round(100.0 * (rule["rho_mean"] / fine["rho_mean"] - 1.0), 2),
                    "fixed600_err_pct": round(100.0 * (fixed["rho_mean"] / fine["rho_mean"] - 1.0), 2),
                }
            )
        print(pd.DataFrame(rows).to_string(index=False))
    return 0


def rank_by_probability(run_dir: RunDirectory, elements: pd.DataFrame) -> pd.DataFrame:
    """The objects that appear in the run's events, in descending order of their worst probability.

    The Step 2 review's instruction: do not fit the catalogue. An object that appears in no
    event has no conjunction to score and no coefficient is needed for it; among those that
    do, the fit budget should be spent where it changes an answer, which is the top of the
    probability list. Ties, and a run with no scored scenario yet, fall back to the closest
    approach the object takes part in -- the only ordering the geometry alone supports.
    """
    events = run_dir.read_events()
    in_events = set(int(i) for i in events["primary_norad_id"]) | set(int(i) for i in events["secondary_norad_id"])
    worst_pc: dict[int, float] = {}
    scenarios = run_dir.scenarios()
    if scenarios:
        risk = run_dir.read_risk(scenarios[0])
        pc = risk.set_index("event_id")["pc"].reindex(events["event_id"]).to_numpy(dtype=float)
        for column in ("primary_norad_id", "secondary_norad_id"):
            for norad_id, value in zip(events[column].to_numpy(dtype=np.int64), pc, strict=True):
                if np.isfinite(value):
                    worst_pc[int(norad_id)] = max(worst_pc.get(int(norad_id), 0.0), float(value))
    closest: dict[int, float] = {}
    miss = events["miss_km"].to_numpy(dtype=float)
    for column in ("primary_norad_id", "secondary_norad_id"):
        for norad_id, value in zip(events[column].to_numpy(dtype=np.int64), miss, strict=True):
            closest[int(norad_id)] = min(closest.get(int(norad_id), np.inf), float(value))

    ranked = elements[elements["norad_id"].isin(in_events)].copy()
    ids = ranked["norad_id"].astype(int)
    ranked["_pc"] = [worst_pc.get(int(i), 0.0) for i in ids]
    ranked["_miss"] = [closest.get(int(i), np.inf) for i in ids]
    ranked = ranked.sort_values(["_pc", "_miss"], ascending=[False, True]).drop(columns=["_pc", "_miss"])
    dropped = len(elements) - len(ranked)
    if dropped:
        log.info(
            "%d of the run's %d objects appear in no event and are not fitted; %d ranked by %s",
            dropped,
            len(elements),
            len(ranked),
            f"probability under '{scenarios[0]}'" if scenarios else "miss distance (no scenario scored yet)",
        )
    return ranked.reset_index(drop=True)


def cmd_ballistic(args: argparse.Namespace) -> int:
    """Fit a ballistic coefficient for the objects of a run that appear in events, worst first."""
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    info = run_dir.read_run()
    now = datetime.now(UTC)
    objects = run_dir.read_objects()
    elements = elements_for_run(info)
    elements = elements[elements["norad_id"].isin(objects["norad_id"])].reset_index(drop=True)
    if not args.all:
        elements = rank_by_probability(run_dir, elements)
    if args.limit:
        elements = elements.head(args.limit)
    log.info("Fitting ballistic coefficients for %d objects", len(elements))

    start = parse_utc(info["start"]) - timedelta(days=args.fit_days)
    # The B* fallback propagates each element set forward from its own epoch, so the table has
    # to reach past the run window by that much as well.
    latest_epoch = pd.to_datetime(elements["epoch"], utc=True).max().to_pydatetime()
    end = max(parse_utc(info["end"]), latest_epoch + timedelta(days=config.BSTAR_DECAY_DAYS + 1))
    table = weather_for_density(now, start, end, offline=args.offline)
    hist = None
    if not args.no_history:
        # Bounded at both ends. The upper bound is what makes this work on a historical run: the
        # store also holds today's element sets for most of these objects, and a fit given both
        # would measure 2026's decay and label it 2024's. For a live run the bound is a no-op,
        # because the newest set in the store *is* the run's.
        hist = history.load_history(norad_ids=[int(i) for i in elements["norad_id"]], start=start, end=latest_epoch)
        log.info(
            "History: %d element sets for %d objects, %s to %s",
            len(hist),
            hist["norad_id"].nunique() if len(hist) else 0,
            start.date(),
            latest_epoch.date(),
        )
    store = None if args.no_cache else CoefficientStore().load()

    def progress(done: int, total: int) -> None:
        log.info("  %d/%d objects, %.0f s elapsed", done, total, time.perf_counter() - t_start)

    t_start = time.perf_counter()
    fit = functools.partial(
        ballistic_mod.coefficients,
        elements,
        table,
        hist,
        fit_days=args.fit_days,
        step_s=args.step_s,
        budget_s=args.budget_s,
        store=store,
        step_scale=args.step_scale,
        now=now,
        progress=progress,
    )
    if args.profile:
        profiler = cProfile.Profile()
        profiler.enable()
        frame = fit()
        profiler.disable()
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).sort_stats("tottime").print_stats(15)
        print(stream.getvalue())
    else:
        frame = fit()
    if store is not None:
        store.save()

    run_dir.write_ballistic(
        frame, metadata={"driftwatch_run_id": info["run_id"], "driftwatch_msis": str(config.MSIS_VERSION)}
    )
    summary = ballistic_mod.summary(frame)
    info["ballistic"] = {
        **summary,
        "n_objects_in_run": int(len(objects)),
        "fit_days": args.fit_days,
        "step_scale": args.step_scale,
        "fitted_at": now.isoformat(),
        "msis_version": config.MSIS_VERSION,
        "cache": store.summary(now=now) if store is not None else None,
    }
    if len(frame) < len(objects):
        log.info(
            "%d of the run's %d objects have a coefficient; the rest appear in no event, so no scenario asks for one",
            len(frame),
            len(objects),
        )
    run_dir.write_run(info)
    log.info("Ballistic coefficients: %s", summary)

    print(f"{len(frame)} objects in {time.perf_counter() - t_start:.0f} s")
    print("by source:", summary["by_source"])
    print("budget:   ", summary.get("budget"))
    print("B (m^2/kg): p10 {p10}, median {median}, p90 {p90}".format(**summary["b_m2_kg"]))
    print("relative sigma: median {median}, p90 {p90}".format(**summary["relative_sigma"]))
    shown = frame.sort_values("b_m2_kg", ascending=False).head(args.show)
    columns = ["norad_id", "category", "alt_band", "b_m2_kg", "b_sigma_m2_kg", "source", "n_sets", "decay_snr"]
    print(shown[columns].to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print(run_dir.ballistic_path)
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
        table, states, summary = spacex.fetch_ephemerides(ids, now=now, offline=args.offline, limit=args.limit)
    except (httpx.HTTPError, FileNotFoundError) as exc:
        log.error("Cannot fetch SpaceX ephemerides: %s", exc)
        return 2
    if not len(table):
        log.error("No SpaceX ephemerides were retrieved")
        return 2
    # The frame check, before anything is written. It is here rather than only in the tests
    # because the failure it guards against is a change at the source: the file header does not
    # name the state frame at all, so a change to the convention would otherwise be silent, and
    # states in the wrong frame are smooth, interpolate cleanly and land 44 km from the truth.
    # See docs/ephemeris-frame.md.
    frame_check = {"verdict": "not checked: no stored supplemental element sets to check against"}
    if len(states):
        elements = supplemental_mod.load_supplemental_history("starlink")
        if len(elements):
            elements = elements.sort_values("epoch").drop_duplicates("norad_id", keep="last")
            frame_check = spacex.check_state_frame(states, elements)
        summary["frame_check"] = frame_check
        log.info("SpaceX state frame check: %s", frame_check)
        if frame_check.get("passed") is False:
            log.error("%s", frame_check["verdict"])
            log.error("Refusing to store states that fail the frame check; nothing was written.")
            info["spacex_frame_check"] = frame_check
            run_dir.write_run(info)
            return 1
        if "passed" not in frame_check:
            log.warning("The state frame could not be checked (%s)", frame_check["verdict"])

    path = spacex.write_store(table, spacex.store_path(now))
    summary["file"] = path.name
    if len(states):
        state_path = spacex.write_state_store(states, spacex.state_store_path(now))
        summary["state_file"] = state_path.name
        log.info("SpaceX states: %s", summary["states"])
        s = summary["states"]
        print(
            f"states: {s['kept']} of {s['of']} kept for {s['objects']} satellites; "
            f"interpolation error median {s['interp_err_median_m']:.2f} m, worst {s['interp_err_worst_m']:.2f} m; "
            f"{s['objects_with_a_break']} objects carry a break, at {s['break_hours']} h"
        )

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
    # The span convention was recovered from these rows, so it is confirmed on rows it never
    # saw: the training events halved, and the challenge's own test file where it sits beside
    # the training one.
    held_out: list[dict[str, Any]] = []
    if primary is not None:
        test_path = kelvins_mod.find_test_dataset(data)
        test = kelvins_mod.load_kelvins(test_path) if test_path is not None else None
        try:
            held_out = kelvins_mod.held_out_checks(df, test)
        except ValueError as exc:
            log.warning("Kelvins held-out check skipped: %s", exc)
        for check in held_out:
            log.info("Kelvins held out: %s", check)

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
    text = kelvins_mod.to_markdown(
        fit, data, extra, primary=primary, proxies=proxies, radii=radii, plot_path=plot_name, held_out=held_out
    )
    print(text)
    if out is not None:
        out.write_text(text + "\n", encoding="utf-8")
        log.info("Wrote %s", out)
    return 0


def cmd_cdm(args: argparse.Namespace) -> int:
    """Conjunction Data Messages: parse them, match them to a run, or build test messages from Kelvins rows.

    ``parse`` prints each message's summary. ``match`` joins a directory of messages to a stored
    run on the object pair and the time of closest approach and reports which operator warnings
    public data found, at what miss and probability, and which public-data flags the operator
    never received; ``--out`` writes the three tables and the summary as JSON beside the run.
    ``from-kelvins`` writes ESA's anonymised challenge rows out as KVN messages with synthetic
    identities, which is the test input the parser and the matcher were built against.
    """
    if args.cdm_command == "parse":
        messages = []
        for item in args.paths:
            messages.extend(cdm_parse.load_cdms(Path(item)))
        for cdm in messages:
            print(json.dumps(cdm.summary(), default=str))
        print(f"{len(messages)} message(s)")
        return 0
    if args.cdm_command == "from-kelvins":
        path = Path(args.csv) if args.csv else kelvins_mod.find_dataset()
        if path is None or not Path(path).exists():
            log.error("no Kelvins CSV: pass one, or place train_data.csv under %s", config.KELVINS_DIR)
            return 2
        frame = pd.read_csv(path, nrows=args.limit)
        reference = parse_utc(args.reference_epoch) if args.reference_epoch else cdm_kelvins.DEFAULT_REFERENCE_EPOCH
        messages = cdm_kelvins.kelvins_to_cdms(frame, reference_epoch=reference)
        paths = cdm_kelvins.write_cdms(messages, Path(args.out_dir))
        events = cdm_kelvins.kelvins_events(frame, reference_epoch=reference)
        events_path = Path(args.out_dir) / "kelvins_events.parquet"
        events.to_parquet(events_path, index=False)
        print(f"{len(paths)} messages under {args.out_dir}, {len(events)} distinct conjunctions in {events_path}")
        print("Object designators and times are synthetic and deterministic; every other field is the row's own.")
        return 0
    # match
    try:
        run_dir = resolve_run(args.run)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2
    messages = cdm_parse.load_cdms(Path(args.cdm))
    if not messages:
        log.error("no messages under %s", args.cdm)
        return 2
    joined = run_dir.read_conjunctions()
    result = cdm_match.match_cdms(messages, joined, tolerance_s=args.tolerance_s, scenario=args.scenario)
    print("\n".join(cdm_match.report_lines(result)))
    if len(result.matches):
        columns = [
            "message_id",
            "object1",
            "object2",
            "cdm_tca",
            "dt_tca_s",
            "cdm_miss_km",
            "event_miss_shifted_km",
            "cdm_pc",
            "event_pc",
            "event_region",
            "event_confidence",
            "event_flag",
        ]
        print("\nMatched (first rows):")
        print(
            result.matches[[c for c in columns if c in result.matches.columns]].head(args.show).to_string(index=False)
        )
    if len(result.unmatched_cdms):
        print("\nOperator warnings public data did not find:")
        cols = [
            c
            for c in ("message_id", "object1", "object2", "cdm_tca", "cdm_miss_km", "cdm_pc", "reason")
            if c in result.unmatched_cdms
        ]
        print(result.unmatched_cdms[cols].head(args.show).to_string(index=False))
    if len(result.unwarned_flags):
        print("\nPublic-data flags the operator never received (region and confidence first):")
        cols = [
            c
            for c in (
                "region",
                "confidence",
                "flag",
                "primary_norad_id",
                "secondary_norad_id",
                "tca",
                "miss_km",
                "pc",
                "event_id",
            )
            if c in result.unwarned_flags
        ]
        print(result.unwarned_flags[cols].head(args.show).to_string(index=False))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": result.summary,
            "matches": json.loads(result.matches.to_json(orient="records", date_format="iso"))
            if len(result.matches)
            else [],
            "unmatched_cdms": json.loads(result.unmatched_cdms.to_json(orient="records", date_format="iso"))
            if len(result.unmatched_cdms)
            else [],
            "unwarned_flags": json.loads(result.unwarned_flags.to_json(orient="records", date_format="iso"))
            if len(result.unwarned_flags)
            else [],
        }
        out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        print(f"\n{out}")
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
        p.add_argument(
            "--scenario",
            default=scenario_default,
            help=(
                "quiet (the Phase 2 baseline, no storm layer), forecast, storm-g3, storm-g4, storm-g5, "
                f"or replay:<YYYY-MM-DD> (default: {scenario_default})"
            ),
        )
        p.add_argument(
            "--storm-offset-days",
            type=float,
            default=config.STORM_OFFSET_DAYS,
            help=(
                f"days into the window at which a synthetic storm begins (default {config.STORM_OFFSET_DAYS:g}); "
                "the displacement grows with the square of the time left, so this matters"
            ),
        )
        p.add_argument(
            "--storm-step-s",
            type=float,
            help="sampling step for the storm term's density track (default: the per-object rule)",
        )
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
    screen.add_argument(
        "--no-spacex",
        action="store_true",
        help="ignore SpaceX's published ephemerides: their states when screening, their covariance when scoring",
    )
    screen.add_argument(
        "--keep-attached",
        action="store_true",
        help="keep attached and co-orbiting objects (docked vehicles, station modules) instead of excluding them",
    )
    screen.add_argument(
        "--attached-km",
        type=float,
        default=1.0,
        help="a pair never further apart than this for --attached-fraction of the window is one cluster (default: 1)",
    )
    screen.add_argument(
        "--attached-fraction",
        type=float,
        default=0.99,
        help="how much of the window a pair must stay within --attached-km to be excluded (default: 0.99)",
    )
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
        help="ignore SpaceX's published ephemerides: their states when screening, their covariance when scoring",
    )
    add_risk_options(risk, scenario_default="quiet")
    risk.set_defaults(func=cmd_risk)

    check_storm = sub.add_parser(
        "storm-check",
        help="attack the storm result: split the shift cancellation by coefficient source and altitude "
        "difference, put the three probabilities side by side, and name the unscoreable objects",
    )
    check_storm.add_argument("run", help="run directory, its name under data/conjunctions, or 'latest'")
    check_storm.add_argument("--scenario", help="scenario to check (default: every stored one but quiet)")
    check_storm.add_argument(
        "--min-events", type=int, default=20, help="smallest coefficient-source group to report (default: 20)"
    )
    check_storm.add_argument("--show", type=int, default=25, help="unscoreable objects to print (default: 25)")
    check_storm.set_defaults(func=cmd_storm_check)

    replay = sub.add_parser(
        "replay-bundle",
        help="write the viewer's replay timeline (Kp, density ratios, Sun frames) for a replay-scored run",
    )
    replay.add_argument("run", help="run directory, its name under data/conjunctions, or 'latest'")
    replay.add_argument("--scenario", help="replay scenario name (default: the run's first replay:<date>)")
    replay.add_argument("--out-dir", help="output directory (default: web/public/data/replay)")
    replay.add_argument(
        "--offline", action="store_true", help="use only cached weather and cached Sun frames; fetch nothing"
    )
    replay.set_defaults(func=cmd_replay_bundle)

    report = sub.add_parser("report", help="rewrite a stored run's markdown report and the viewer's conjunction bundle")
    report.add_argument("run", help="run directory, its name under data/conjunctions, or 'latest'")
    report.add_argument(
        "--scenario", help="scenario to report (default: quiet where it was scored, else the first stored)"
    )
    report.add_argument("--no-viewer", action="store_true", help="write the report only")
    report.add_argument(
        "--out-dir",
        help=(
            "viewer bundle directory (default: web/public/data). A replay run goes in its own "
            "subdirectory, e.g. web/public/data/replay, because replay is a mode with its own "
            "catalogue export and its own times"
        ),
    )
    report.set_defaults(func=cmd_report)

    check_run = sub.add_parser(
        "check-run",
        help="check a run's recorded provenance and its snapshot's age; the pipeline's gate before deploy",
    )
    check_run.add_argument("run", help="run directory, its name under data/conjunctions, or 'latest'")
    check_run.add_argument(
        "--max-snapshot-age-hours",
        type=float,
        default=None,
        help="fail if the run's snapshot was fetched longer ago than this (default: no limit)",
    )
    check_run.set_defaults(func=cmd_check_run)

    stability = sub.add_parser(
        "stability",
        help="append a scored run to the warning-stability index, or read one encounter's history back",
    )
    stability.add_argument("run", nargs="?", help="run directory, its name, or 'latest' (default) -- the append mode")
    stability.add_argument("--series", help="read mode: one series id, e.g. 55053-61705-20260904T1018Z")
    stability.add_argument("--pair", help="read mode: two NORAD ids, e.g. 55053,61705")
    stability.add_argument("--fleet", default="demo", help="fleet whose index to read (read mode only; default: demo)")
    stability.add_argument(
        "--scenario",
        help=(
            "comma-separated scenarios to index, or one to read "
            f"(default: {', '.join(config.STABILITY_SCENARIOS)}, whichever the run scored)"
        ),
    )
    stability.add_argument(
        "--tolerance-s",
        type=float,
        default=None,
        help=(
            "how far a time of closest approach may move between runs and still be the same "
            f"encounter (default {config.STABILITY_TCA_TOLERANCE_S:g} s)"
        ),
    )
    stability.add_argument("--store", help=f"index directory (default {config.STABILITY_DIR})")
    stability.add_argument("--dry-run", action="store_true", help="match and report, but write nothing")
    stability.set_defaults(func=cmd_stability)

    check = sub.add_parser(
        "check-bundle",
        help="check the viewer bundle before publishing it: redistribution, credentials and file sizes",
    )
    check.add_argument("--dir", help=f"directory to check (default {config.VIEWER_DATA_DIR})")
    check.add_argument(
        "--max-file-mib",
        type=float,
        default=25.0,
        help="largest single file allowed, in MiB (default 25, the per-file ceiling kept from Cloudflare Pages)",
    )
    check.set_defaults(func=cmd_check_bundle)

    validate = sub.add_parser(
        "validate",
        help="Phase 3 Step 4: measure the storm term against the May 2024 and February 2022 records",
    )
    validate.add_argument("case", choices=("gannon", "starlink-2022", "swarm"), help="which validation case to run")
    validate.add_argument("--window", default="all", help="swarm: all, quiet, storm or held-out (default: all)")
    validate.add_argument(
        "--page",
        default="docs/calibration-benchmark.md",
        help="swarm: write the benchmark page here (default: docs/calibration-benchmark.md; empty to skip)",
    )
    validate.add_argument("--no-storm-term", action="store_true", help="swarm: skip the storm-term comparison")
    validate.add_argument(
        "--no-esa-record",
        action="store_true",
        help="swarm: do not read ESA's thruster record (SC_xDYN_1B); detect manoeuvres instead",
    )
    validate.add_argument("--sample", type=int, default=300, help="objects to measure (gannon; default 300)")
    validate.add_argument("--min-perigee-km", type=float, default=250.0, help="lower edge of the altitude range")
    validate.add_argument("--max-perigee-km", type=float, default=750.0, help="upper edge of the altitude range")
    validate.add_argument("--category", help="comma-separated categories to keep")
    validate.add_argument(
        "--days", type=int, default=config.GANNON_HISTORY_DAYS, help="days of history to pull before the end date"
    )
    validate.add_argument(
        "--min-snr",
        type=float,
        default=3.0,
        help="smallest quiet-window decay, in units of its own scatter, worth taking a ratio of (default 3)",
    )
    validate.add_argument(
        "--control-band-km",
        type=float,
        default=40.0,
        help="half-width of the control group's perigee band around 500 km (default 40)",
    )
    validate.add_argument(
        "--control-sample",
        type=int,
        default=40,
        help="control objects near 500 km for the 2022 case (default 40)",
    )
    validate.add_argument("--out", help=f"output directory (default {config.DATA_DIR / 'validation'})")
    validate.add_argument("--offline", action="store_true", help="use only cached history and space weather")
    validate.set_defaults(
        func=lambda a: {
            "gannon": cmd_validate_gannon,
            "starlink-2022": cmd_validate_starlink_2022,
            "swarm": cmd_validate_swarm,
        }[a.case](a)
    )

    asof = sub.add_parser(
        "snapshot-as-of",
        help="rebuild the catalogue as it stood on a past date from gp_history, and cache it permanently",
    )
    asof.add_argument("--date", required=True, help="the date to reconstruct, ISO 8601 UTC")
    asof.add_argument("--ids", help="comma-separated NORAD ids")
    asof.add_argument("--launch", help="comma-separated international designator prefixes, e.g. 2022-010")
    asof.add_argument("--fleet", help="fleet file whose members to include")
    asof.add_argument("--min-perigee-km", type=float, help="lower edge of the altitude range to sample")
    asof.add_argument("--max-perigee-km", type=float, help="upper edge of the altitude range to sample")
    asof.add_argument("--category", help="comma-separated categories to keep within the altitude range")
    asof.add_argument("--sample", type=int, default=400, help="objects to take from the altitude range (default 400)")
    asof.add_argument("--days", type=int, default=30, help="days of history to pull before the date (default 30)")
    asof.add_argument(
        "--max-age-days",
        type=float,
        default=7.0,
        help="drop objects whose newest set by then is staler than this (default 7)",
    )
    asof.add_argument("--force", action="store_true", help="rebuild even if the cached file exists")
    asof.add_argument("--offline", action="store_true", help="use only cached history and SATCAT")
    asof.set_defaults(func=cmd_snapshot_as_of)

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
    wx.add_argument(
        "--no-roll",
        action="store_true",
        help=(
            "do not roll minute-cadence solar wind older than "
            f"{config.SOLAR_WIND_MINUTE_DAYS} days into the hourly archive"
        ),
    )
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

    dens = sub.add_parser(
        "density",
        help="NRLMSIS sanity checks: quiet density by altitude, the storm ratios and the sampling step",
    )
    dens.add_argument("--at", help="UTC time to evaluate, ISO 8601 (default: now)")
    dens.add_argument("--offline", action="store_true", help="use only stored space weather")
    dens.add_argument(
        "--convergence",
        action="store_true",
        help="also measure the sampling step against a 10 s reference across eccentricities (slow)",
    )
    dens.set_defaults(func=cmd_density)

    bal = sub.add_parser(
        "ballistic",
        help="fit a ballistic coefficient per object of a run, from its own decay or from B*",
    )
    bal.add_argument("run", nargs="?", default="latest", help="run directory, its name, or 'latest'")
    bal.add_argument("--limit", type=int, help="fit at most this many objects, worst probability first")
    bal.add_argument(
        "--all",
        action="store_true",
        help="cover every object of the run, not only those that appear in an event",
    )
    bal.add_argument(
        "--fit-days",
        type=float,
        default=config.BALLISTIC_FIT_DAYS,
        help=f"days of element-set history to fit over (default {config.BALLISTIC_FIT_DAYS:g})",
    )
    bal.add_argument("--no-history", action="store_true", help="skip the decay fit and use B* for everything")
    bal.add_argument("--no-cache", action="store_true", help="ignore the stored coefficients and refit everything")
    bal.add_argument(
        "--budget-s",
        type=float,
        default=config.BALLISTIC_FIT_BUDGET_S,
        help=(
            f"wall-clock allowance for the history fits in seconds (default "
            f"{config.BALLISTIC_FIT_BUDGET_S:g}); 0 for no limit. What it does not reach falls back to B*"
        ),
    )
    bal.add_argument(
        "--step-scale",
        type=float,
        default=config.BALLISTIC_FIT_STEP_SCALE,
        help=(
            f"coarsen the sampling step by this factor for the fit alone (default "
            f"{config.BALLISTIC_FIT_STEP_SCALE:g}; see docs/density-and-drag.md)"
        ),
    )
    bal.add_argument(
        "--step-s",
        type=float,
        help="sampling step along the orbit in seconds (default: the per-object rule; overrides --step-scale)",
    )
    bal.add_argument("--profile", action="store_true", help="report where the fit spends its time")
    bal.add_argument("--offline", action="store_true", help="use only stored space weather")
    bal.add_argument("--show", type=int, default=15, help="rows to print (default 15)")
    bal.set_defaults(func=cmd_ballistic)

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

    cdm = sub.add_parser(
        "cdm",
        help="CCSDS Conjunction Data Messages: parse, match to a run, or build test messages from Kelvins rows",
    )
    cdm_sub = cdm.add_subparsers(dest="cdm_command", required=True)
    cdm_parse_p = cdm_sub.add_parser("parse", help="print a summary of every message in the given files or directories")
    cdm_parse_p.add_argument("paths", nargs="+", help="KVN or XML files, or directories of them")
    cdm_match_p = cdm_sub.add_parser(
        "match",
        help="match messages to a stored run's events on the object pair and the time of closest approach",
    )
    cdm_match_p.add_argument("run", nargs="?", default="latest", help="run directory, its name, or 'latest'")
    cdm_match_p.add_argument("--cdm", required=True, help="a message file or a directory of them")
    cdm_match_p.add_argument("--scenario", help="which scored scenario to compare against (default quiet)")
    cdm_match_p.add_argument(
        "--tolerance-s",
        type=float,
        default=cdm_match.DEFAULT_TOLERANCE_S,
        help=f"TCA tolerance for a match in seconds (default {cdm_match.DEFAULT_TOLERANCE_S:g})",
    )
    cdm_match_p.add_argument("--out", help="write the tables and the summary as JSON here")
    cdm_match_p.add_argument("--show", type=int, default=20, help="rows to print per table (default 20)")
    cdm_from = cdm_sub.add_parser(
        "from-kelvins",
        help="write ESA's anonymised Kelvins rows out as KVN messages with synthetic identities, as test input",
    )
    cdm_from.add_argument("--csv", help=f"the challenge CSV (default: the first CSV under {config.KELVINS_DIR})")
    cdm_from.add_argument("--out-dir", required=True, help="directory to write the messages into")
    cdm_from.add_argument("--limit", type=int, default=200, help="rows to convert (default 200)")
    cdm_from.add_argument("--reference-epoch", help="the synthetic week starts here (default 2024-05-09T00:00:00Z)")
    cdm.set_defaults(func=cmd_cdm)

    local = sub.add_parser(
        "local",
        help="an operator's own ephemerides, messages and records through the provenance check, the CDM matcher "
        "and the ephemeris benchmark, with every outbound request refused",
    )
    local.add_argument(
        "--out", required=True, help="directory for local_analysis.json, local_analysis.md and the trials"
    )
    local.add_argument("--run", help="a stored run: directory, name under data/conjunctions, or 'latest'")
    local.add_argument("--max-snapshot-age-hours", type=float, help="fail the provenance check past this age")
    local.add_argument("--cdm", help="the operator's messages (a file or a directory); needs --run")
    local.add_argument("--scenario", help="which scored scenario the messages are matched against (default quiet)")
    local.add_argument(
        "--tolerance-s",
        type=float,
        default=cdm_match.DEFAULT_TOLERANCE_S,
        help=f"TCA tolerance for a match in seconds (default {cdm_match.DEFAULT_TOLERANCE_S:g})",
    )
    local.add_argument("--ephemeris", help="the operator's CCSDS OEM (KVN) file, or a directory of them")
    local.add_argument("--norad", type=int, help="the public catalogue id the ephemeris describes")
    local.add_argument("--label", help="a name for the object in the report (default: the OEM's OBJECT_NAME)")
    local.add_argument(
        "--sets", help="the object's element sets as OMM JSON (CelesTrak/Space-Track form); default: the local history"
    )
    local.add_argument(
        "--manoeuvres", help="the operator's manoeuvre record: a CSV with start,end columns of UTC times"
    )
    local.add_argument(
        "--leads", default="6,12,24,36,48,72,96,120,144,168", help="lead times in hours (default 6 h to 7 days)"
    )
    local.add_argument("--tolerance-km", type=float, default=25.0, help="the horizon's in-track tolerance (default 25)")
    local.add_argument(
        "--storm-term",
        action="store_true",
        help="apply the storm term with the cached observed ap; skipped, and said so, when no weather is cached",
    )
    local.set_defaults(func=cmd_local)
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
