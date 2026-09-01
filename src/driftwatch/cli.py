"""Command-line interface: ``driftwatch fetch``, ``propagate``, ``snapshots``, ``history`` and ``fleet``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import __version__, config
from driftwatch.catalogue import celestrak, history, satcat, snapshot, spacetrack
from driftwatch.export.viewer import export_viewer_bundle
from driftwatch.fleet import FleetError, load_fleet, resolve_fleet
from driftwatch.orbit import frames, propagator
from driftwatch.orbit.time import parse_utc, stamp

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
    """Fetch Space-Track gp_history for a list of NORAD ids and write a history parquet."""
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
        history.history_path(now, config.HISTORY_DIR),
        metadata={"norad_ids": ",".join(map(str, ids)), "start": start.isoformat(), "end": end.isoformat()},
    )
    summary = history.history_summary(df)
    log.info("History: %s", summary)
    missing = sorted(set(ids) - set(df["norad_id"].tolist()))
    if missing:
        log.warning("No element sets in range for %d ids: %s", len(missing), missing[:20])
    print(path)
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
    hist.add_argument("--ids", required=True, help="comma-separated NORAD ids, e.g. 25544,39634")
    hist.add_argument("--start", required=True, help="first epoch day (UTC), YYYY-MM-DD")
    hist.add_argument("--end", required=True, help="last epoch day inclusive (UTC), YYYY-MM-DD")
    hist.add_argument("--offline", action="store_true", help="use only cached gp_history responses")
    hist.set_defaults(func=cmd_history)

    fleet = sub.add_parser("fleet", help="validate a fleet YAML file and show its members in the latest snapshot")
    fleet.add_argument("fleet", help="fleet file, e.g. fleets/demo.yaml")
    fleet.add_argument("--snapshot", help="snapshot parquet path (default: latest)")
    fleet.set_defaults(func=cmd_fleet)
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
