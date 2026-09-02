"""SpaceX's published Starlink ephemerides: the operator's own covariance, used directly.

What they are. SpaceX publishes a predicted trajectory for every Starlink satellite, with a
covariance at every state, 72 hours ahead at a 60-second step, refreshed every eight hours.
They are the operator's own product rather than a tracking fit: they contain the manoeuvres
the satellite is *planned* to make, which no element set fitted to past observations can
know about. They are also the upstream source of the CelesTrak supplemental element sets
driftwatch already screens Starlink secondaries on -- CelesTrak fits an SGP4 element set to
each of these files -- so using their covariance is using the uncertainty of the trajectory
we are already propagating, instead of inferring one from how much successive fits to it
disagree.

Terms. They are served by SpaceX at ``api.starlink.com/public-files/ephemerides/``, without
an account and without a stated licence, for the express purpose of letting other operators
screen against Starlink. Space-Track stopped hosting them on 28 July 2025 and its user
agreement therefore does not govern them. **The rule adopted, and the one this module
enforces: analysis only.** Read them, compute with them, publish the results crediting
SpaceX; never republish the raw files or a repackaged copy of them. What is stored here is a
thinned covariance series, which is a derived product and is not redistributed either --
``data/spacex/`` is outside the repository. ``docs/spacex-ephemerides.md`` carries the full
finding and ``docs/data-sources.md`` the standing rule.

What their covariance is, and is not. It grows smoothly for about ten hours, which is a
propagated covariance, and then sits on round numbers -- exactly 100 m radial, 1,000 m
in-track, 10 m cross-track on the file measured for the Step 0 review -- until it steps to
another set of round numbers for the last twelve hours. Past ten hours it is a stated
envelope, plausibly the stationkeeping control box, not a fitted uncertainty. It is also
about eleven times tighter than driftwatch's own measurement of the version-to-version
revision at the same lead, and that is not a contradiction: theirs is the uncertainty
*within* one plan, ours is the uncertainty *of the plan being revised*. For screening a week
ahead the revision is the part that matters, which is why the supplemental-consistency fit
stays in place as a cross-check (:func:`cross_check`) rather than being replaced.

It is used **as published**. Nothing here inflates it, and one thing that arguably should is
recorded rather than done: the geometry driftwatch propagates comes from CelesTrak's SGP4
fit to this ephemeris, not from the ephemeris itself, and that fit disagrees with it by a
published RMS of about 0.2 km -- larger than SpaceX's own sigma inside the first several
hours. ``add_fit_rms_floor`` on :class:`SpacexEphemerisCovariance` applies that as a floor;
it is off by default because "use their covariance as published" was the instruction, and
the question is on the Step 0 review list.

The file format is the "Modified ITC" of the *Spaceflight Safety Handbook for Operators*:
three or four header lines, then one state per four lines -- an epoch and position and
velocity in km and km/s, then the 21 numbers of the lower triangle of the 6x6 covariance,
row-major, in the UVW (RTN, which is our RIC) frame. Only the position block is kept, and
only every :data:`driftwatch.config.SPACEX_COVARIANCE_STEP_S` seconds of it: the covariance
is smooth or piecewise constant, so a ten-minute grid holds it to a fraction of a percent
and turns a 2 MB file into a few tens of kilobytes.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.catalogue.celestrak import make_client
from driftwatch.orbit.time import stamp
from driftwatch.risk.covariance import CovarianceModel, ObjectRef, RicCovariance

log = logging.getLogger(__name__)

# MEME_<norad id>_STARLINK-<name>_<...>_UNCLASSIFIED.txt
MANIFEST_NAME_RE = re.compile(r"^MEME_(\d+)_(\S+?)_\d+_\w+_\d+_\w+\.txt$")
EPOCH_RE = re.compile(r"^\d{13}\.\d+$")
HEADER_KEYS: tuple[str, ...] = ("created", "ephemeris_start", "ephemeris_stop", "step_size", "ephemeris_source")
HEADER_KEY_ALTERNATION = "|".join(HEADER_KEYS)
COVARIANCE_COLUMNS: tuple[str, ...] = (
    "cov_rr_km2",
    "cov_ri_km2",
    "cov_ii_km2",
    "cov_rc_km2",
    "cov_ic_km2",
    "cov_cc_km2",
)
EPHEMERIS_COLUMNS: tuple[str, ...] = (
    "norad_id",
    "name",
    "created",
    "ephemeris_start",
    "ephemeris_stop",
    "ephemeris_source",
    "t",
    *COVARIANCE_COLUMNS,
)


# --------------------------------------------------------------------------------------
# The published files


@dataclass(frozen=True)
class ManifestEntry:
    """One line of the manifest: the file name and the NORAD id encoded in it."""

    file_name: str
    norad_id: int
    name: str


def parse_manifest(text: str) -> list[ManifestEntry]:
    """Every line of ``MANIFEST.txt`` that names a file we can attribute to a NORAD id."""
    entries: list[ManifestEntry] = []
    for line in text.splitlines():
        name = line.strip()
        match = MANIFEST_NAME_RE.match(name)
        if match:
            entries.append(ManifestEntry(name, int(match.group(1)), match.group(2)))
    return entries


def manifest_path(cache_dir: Path = config.CACHE_DIR) -> Path:
    return cache_dir / "spacex" / "MANIFEST.txt"


def fetch_manifest(
    *,
    cache_dir: Path = config.CACHE_DIR,
    max_age: timedelta = config.SPACEX_MANIFEST_MAX_AGE,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
) -> list[ManifestEntry]:
    """The manifest, from cache when it is younger than ``max_age``.

    The files are refreshed every eight hours, so a manifest a few hours old still names the
    current version of every satellite; the name does not change, only the contents behind it.
    """
    now = now or datetime.now(UTC)
    path = manifest_path(cache_dir)
    if path.exists():
        age = now - datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if offline or age < max_age:
            log.info("Using cached SpaceX manifest (%.1f h old)", age.total_seconds() / 3600.0)
            return parse_manifest(path.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError("No cached SpaceX ephemeris manifest and offline=True")
    own = client is None
    client = client or make_client()
    try:
        response = client.get(config.SPACEX_EPHEMERIS_URL + "MANIFEST.txt", headers={"Accept": "*/*"})
        response.raise_for_status()
    finally:
        if own:
            client.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(response.text, encoding="utf-8")
    os.replace(tmp, path)
    entries = parse_manifest(response.text)
    log.info("SpaceX ephemeris manifest: %d files", len(entries))
    return entries


def _parse_epoch(token: str) -> np.datetime64:
    """``YYYYDDDHHMMSS.sss`` (year, day of year, UTC time of day) as a microsecond datetime64."""
    year, doy = int(token[:4]), int(token[4:7])
    hour, minute = int(token[7:9]), int(token[9:11])
    second = float(token[11:])
    base = np.datetime64(f"{year:04d}-01-01", "us") + np.timedelta64(doy - 1, "D")
    return base + np.timedelta64(int(round((hour * 3600 + minute * 60 + second) * 1e6)), "us")


def parse_ephemeris(
    text: str, *, step_s: float = config.SPACEX_COVARIANCE_STEP_S
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """The thinned position covariance of one file, and its header.

    Returns a frame of ``t`` and the six independent entries of the RIC position covariance
    in km^2, sampled every ``step_s`` seconds, and a header dictionary. Only the states
    actually kept are parsed, which is what makes reading a few hundred 2 MB files bearable.
    """
    lines = text.splitlines()
    header: dict[str, Any] = {}
    start = 0
    for i, line in enumerate(lines[:8]):
        stripped = line.strip()
        if EPOCH_RE.match(stripped.split(" ", 1)[0] if stripped else ""):
            start = i
            break
        for key in HEADER_KEYS:
            # The lookahead has to name the keys: a value like "09:23:42 UTC" contains colons
            # of its own, and a generic \w+: lookahead would cut the timestamp at the hour.
            match = re.search(rf"{key}:\s*(.+?)(?=\s+(?:{HEADER_KEY_ALTERNATION}):|$)", stripped)
            if match:
                header[key] = match.group(1).strip()
        if stripped in ("UVW", "RTN", "ITRF", "EME2000"):
            header["frame"] = stripped
            start = i + 1
    if header.get("frame") not in (None, "UVW", "RTN"):
        raise ValueError(f"SpaceX ephemeris covariance is in {header['frame']!r}, not the RTN/UVW frame")

    body = lines[start:]
    n_states = len(body) // 4
    if n_states == 0:
        raise ValueError("no states in the ephemeris file")
    file_step_s = float(header.get("step_size") or 60.0)
    stride = max(1, int(round(float(step_s) / file_step_s)))
    # Always keep the last state so the stored series spans the file's full validity.
    indices = sorted({*range(0, n_states, stride), n_states - 1})
    times = np.empty(len(indices), dtype="datetime64[us]")
    cov = np.empty((len(indices), 6), dtype=float)
    for row, i in enumerate(indices):
        times[row] = _parse_epoch(body[4 * i].split()[0])
        # The 21 lower-triangle entries run over three lines; the position block is the first six.
        values = body[4 * i + 1].split()[:6]
        cov[row] = [float(v) for v in values]
    frame = pd.DataFrame(
        {
            "t": times,
            # Lower triangle, row-major: C00, C10, C11, C20, C21, C22 over (R, I, C).
            "cov_rr_km2": cov[:, 0],
            "cov_ri_km2": cov[:, 1],
            "cov_ii_km2": cov[:, 2],
            "cov_rc_km2": cov[:, 3],
            "cov_ic_km2": cov[:, 4],
            "cov_cc_km2": cov[:, 5],
        }
    )
    header["n_states"] = n_states
    header["n_kept"] = len(frame)
    return frame, header


def _header_time(value: str | None) -> pd.Timestamp:
    if not value:
        return pd.NaT
    return pd.to_datetime(value.replace(" UTC", ""), utc=True, errors="coerce")


def fetch_ephemerides(
    norad_ids: Iterable[int],
    *,
    cache_dir: Path = config.CACHE_DIR,
    client: httpx.Client | None = None,
    now: datetime | None = None,
    offline: bool = False,
    limit: int = config.SPACEX_MAX_OBJECTS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Download the ephemeris of each requested satellite and return their thinned covariances.

    One request per satellite, only for the satellites asked for, never a sweep of the
    constellation: at 2 MB a file the whole 11,000 would be 22 GB a version and there is no
    reason to pull a satellite no event involves. ``limit`` is a hard cap on the number of
    requests one call will make.
    """
    now = now or datetime.now(UTC)
    ids = sorted({int(i) for i in norad_ids})[: int(limit)]
    entries = {e.norad_id: e for e in fetch_manifest(cache_dir=cache_dir, client=client, now=now, offline=offline)}
    wanted = [entries[i] for i in ids if i in entries]
    missing = [i for i in ids if i not in entries]
    if offline:
        raise FileNotFoundError("SpaceX ephemerides are fetched per satellite; there is no offline path")

    own = client is None
    client = client or make_client()
    frames: list[pd.DataFrame] = []
    failures: list[int] = []
    try:
        for entry in wanted:
            try:
                response = client.get(config.SPACEX_EPHEMERIS_URL + entry.file_name, headers={"Accept": "*/*"})
                response.raise_for_status()
                frame, header = parse_ephemeris(response.text)
            except (httpx.HTTPError, ValueError) as exc:
                log.warning("SpaceX ephemeris for %d failed (%s)", entry.norad_id, exc)
                failures.append(entry.norad_id)
                continue
            frame.insert(0, "norad_id", entry.norad_id)
            frame.insert(1, "name", entry.name)
            frame.insert(2, "created", _header_time(header.get("created")))
            frame.insert(3, "ephemeris_start", _header_time(header.get("ephemeris_start")))
            frame.insert(4, "ephemeris_stop", _header_time(header.get("ephemeris_stop")))
            frame.insert(5, "ephemeris_source", str(header.get("ephemeris_source") or ""))
            frames.append(frame)
    finally:
        if own:
            client.close()

    table = (
        pd.concat(frames, ignore_index=True)[list(EPHEMERIS_COLUMNS)]
        if frames
        else pd.DataFrame(columns=list(EPHEMERIS_COLUMNS))
    )
    summary = {
        "requested": len(ids),
        "in_manifest": len(wanted),
        "fetched": int(table["norad_id"].nunique()) if len(table) else 0,
        "not_in_manifest": missing[:10],
        "n_not_in_manifest": len(missing),
        "failed": failures[:10],
        "n_failed": len(failures),
        "n_rows": int(len(table)),
        "created": sorted({str(t) for t in table["created"].dropna().unique()})[:3] if len(table) else [],
    }
    log.info("SpaceX ephemerides: %s", summary)
    return table, summary


# --------------------------------------------------------------------------------------
# The store


def store_path(fetched_at: datetime, out_dir: Path = config.SPACEX_DIR) -> Path:
    return Path(out_dir) / f"ephemerides_{stamp(fetched_at)}.parquet"


def write_store(table: pd.DataFrame, path: Path, *, metadata: dict[str, str] | None = None) -> Path:
    """Write one fetch's covariances. Derived data, not the raw files: see the module docstring."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = table.copy()
    out.attrs = {}
    tmp = path.with_suffix(".tmp")
    out.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    log.info("Wrote %s (%d rows, %d satellites)", path, len(out), out["norad_id"].nunique() if len(out) else 0)
    return path


def list_store(out_dir: Path = config.SPACEX_DIR) -> list[Path]:
    return sorted(Path(out_dir).glob("ephemerides_*.parquet"))


def load_store(
    norad_ids: Sequence[int] | None = None, out_dir: Path = config.SPACEX_DIR, *, latest_only: bool = True
) -> pd.DataFrame:
    """Every stored covariance series, or only the newest version of each satellite."""
    paths = list_store(out_dir)
    if not paths:
        return pd.DataFrame(columns=list(EPHEMERIS_COLUMNS))
    frames = []
    for path in paths:
        frame = pd.read_parquet(path)
        if norad_ids is not None:
            frame = frame[frame["norad_id"].isin([int(i) for i in norad_ids])]
        if len(frame):
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=list(EPHEMERIS_COLUMNS))
    table = pd.concat(frames, ignore_index=True)
    if latest_only and len(table):
        newest = table.groupby("norad_id")["created"].transform("max")
        table = table[table["created"] == newest]
    return table.sort_values(["norad_id", "t"]).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# The covariance model


class SpacexEphemerisCovariance:
    """A base model with Starlink objects served from SpaceX's own covariance where it reaches.

    The published covariance is a function of absolute time rather than of propagation time,
    so it is looked up at the time of closest approach directly and interpolated linearly
    between the stored samples. Outside a satellite's ``[ephemeris_start, ephemeris_stop]``,
    and for every satellite with no stored file, the base model serves and reports its own
    source, so a run whose window runs past the 72-hour horizon shows exactly where the
    covariance changed hands.

    Source labels: ``spacex-ephemeris`` when every requested time was covered,
    ``spacex-ephemeris+<what the base said>`` when only some were, and the base model's own
    label when none were.
    """

    def __init__(
        self,
        base: CovarianceModel,
        table: pd.DataFrame | None = None,
        *,
        add_fit_rms_floor: bool = False,
        fit_rms_km: float = 0.0,
    ) -> None:
        self.base = base
        self.table = table if table is not None else pd.DataFrame(columns=list(EPHEMERIS_COLUMNS))
        self.add_fit_rms_floor = bool(add_fit_rms_floor)
        self.fit_rms_km = float(fit_rms_km)
        self.series: dict[int, tuple[np.ndarray, np.ndarray, np.datetime64, np.datetime64]] = {}
        for norad_id, group in self.table.groupby("norad_id"):
            group = group.sort_values("t")
            times = pd.to_datetime(group["t"], utc=True).dt.tz_localize(None).to_numpy(dtype="datetime64[us]")
            cov = group[list(COVARIANCE_COLUMNS)].to_numpy(dtype=float)
            start = np.datetime64(pd.Timestamp(group["ephemeris_start"].iloc[0]).tz_localize(None), "us")
            stop = np.datetime64(pd.Timestamp(group["ephemeris_stop"].iloc[0]).tz_localize(None), "us")
            self.series[int(norad_id)] = (times, cov, start, stop)
        self.version = f"{base.version}+spacex-ephemeris/1"

    @property
    def dt_floor_days(self) -> float:
        return getattr(self.base, "dt_floor_days", 0.5)

    def growth_for(self, obj: ObjectRef) -> tuple[Any, str]:
        """The base model's growth. SpaceX's covariance is a table, not a power law, so it has none."""
        return self.base.growth_for(obj)  # type: ignore[attr-defined]

    def _matrices(self, norad_id: int, at64: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """The published covariance at ``at64`` and which of those times the file actually covers."""
        times, cov, start, stop = self.series[norad_id]
        covered = (at64 >= start) & (at64 <= stop) & (at64 >= times[0]) & (at64 <= times[-1])
        out = np.zeros((len(at64), 3, 3))
        if not covered.any():
            return out, covered
        x = (at64[covered] - times[0]) / np.timedelta64(1, "s")
        xp = (times - times[0]) / np.timedelta64(1, "s")
        entries = np.stack([np.interp(x, xp, cov[:, k]) for k in range(6)], axis=1)
        rr, ri, ii, rc, ic, cc = entries.T
        block = np.empty((len(rr), 3, 3))
        block[:, 0, 0], block[:, 1, 1], block[:, 2, 2] = rr, ii, cc
        block[:, 0, 1] = block[:, 1, 0] = ri
        block[:, 0, 2] = block[:, 2, 0] = rc
        block[:, 1, 2] = block[:, 2, 1] = ic
        if self.add_fit_rms_floor and self.fit_rms_km > 0:
            # The geometry comes from CelesTrak's SGP4 fit to this ephemeris, not from the
            # ephemeris; the fit's own residual is a floor under the covariance of what we
            # actually propagated. Off by default -- see the module docstring.
            floor = (self.fit_rms_km / np.sqrt(3.0)) ** 2
            block[:, [0, 1, 2], [0, 1, 2]] = np.maximum(block[:, [0, 1, 2], [0, 1, 2]], floor)
        out[covered] = block
        return out, covered

    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        at64 = np.asarray(at, dtype="datetime64[us]")
        if int(obj.norad_id) not in self.series:
            return self.base.covariance_ric(obj, epoch, at64)
        cov, covered = self._matrices(int(obj.norad_id), at64)
        if not covered.any():
            return self.base.covariance_ric(obj, epoch, at64)
        if covered.all():
            return RicCovariance(cov, "spacex-ephemeris")
        fallback = self.base.covariance_ric(obj, epoch, at64[~covered])
        cov[~covered] = fallback.cov_km2
        return RicCovariance(cov, f"spacex-ephemeris+{fallback.source}")

    def to_frame(self) -> pd.DataFrame:
        """The base model's table. The SpaceX covariance is a time series, stored separately."""
        return self.base.to_frame() if hasattr(self.base, "to_frame") else pd.DataFrame()


# --------------------------------------------------------------------------------------
# The cross-check


def cross_check(
    table: pd.DataFrame, model: CovarianceModel, *, leads_hours: Iterable[float] = (1.0, 3.0, 8.0, 24.0, 48.0, 72.0)
) -> pd.DataFrame:
    """SpaceX's published sigma against driftwatch's supplemental-consistency model, lead by lead.

    They are not the same quantity and the table is not a validation of either. SpaceX's
    number is the uncertainty *within* one published plan; the consistency fit measures how
    much the plan is *revised* between publications, which is the part a screening a week
    ahead lives or dies on. The ratio between them is roughly the size of that revision, and
    it is worth watching: if it ever fell to one, either the plans stopped being revised or
    the consistency fit stopped measuring the revision.
    """
    rows: list[dict[str, Any]] = []
    if not len(table):
        return pd.DataFrame(rows)
    norad_ids = sorted(table["norad_id"].unique())
    for lead_hours in leads_hours:
        sigmas: list[np.ndarray] = []
        for norad_id in norad_ids:
            group = table[table["norad_id"] == norad_id]
            start = pd.Timestamp(group["ephemeris_start"].iloc[0])
            want = np.array([np.datetime64((start + pd.Timedelta(hours=lead_hours)).tz_localize(None), "us")])
            times = pd.to_datetime(group["t"], utc=True).dt.tz_localize(None).to_numpy(dtype="datetime64[us]")
            if want[0] < times[0] or want[0] > times[-1]:
                continue
            x = (want - times[0]) / np.timedelta64(1, "s")
            xp = (times - times[0]) / np.timedelta64(1, "s")
            diag = [
                np.interp(x, xp, group[c].to_numpy(dtype=float))[0] for c in ("cov_rr_km2", "cov_ii_km2", "cov_cc_km2")
            ]
            sigmas.append(np.sqrt(np.maximum(np.asarray(diag), 0.0)))
        if not sigmas:
            continue
        spacex = np.median(np.stack(sigmas), axis=0)
        ref = ObjectRef(int(norad_ids[0]), "starlink", "leo")
        epoch = datetime(2026, 1, 1, tzinfo=UTC)
        at = np.array([np.datetime64((epoch + timedelta(hours=float(lead_hours))).replace(tzinfo=None), "us")])
        ours = np.sqrt(np.diag(model.covariance_ric(ref, epoch, at).cov_km2[0]))
        rows.append(
            {
                "lead_hours": float(lead_hours),
                "n_satellites": len(sigmas),
                "spacex_sigma_r_km": float(spacex[0]),
                "spacex_sigma_i_km": float(spacex[1]),
                "spacex_sigma_c_km": float(spacex[2]),
                "ours_sigma_r_km": float(ours[0]),
                "ours_sigma_i_km": float(ours[1]),
                "ours_sigma_c_km": float(ours[2]),
                "ratio_i": float(ours[1] / spacex[1]) if spacex[1] > 0 else float("nan"),
                "ours_source": model.covariance_ric(ref, epoch, at).source,
            }
        )
    return pd.DataFrame(rows)


def select_objects(events: pd.DataFrame, objects: pd.DataFrame, *, limit: int = config.SPACEX_MAX_OBJECTS) -> list[int]:
    """Which Starlink secondaries of a run are worth a request, closest approach first.

    At 2 MB a file the fetch has to be bounded, and the objects worth bounding it to are the
    ones whose events could be flagged. Ranking by the smallest miss any of the object's
    events has is the ordering available before the events are scored, and the covariance is
    what the scoring is waiting for.
    """
    if not len(events) or not len(objects):
        return []
    starlink = set(objects.loc[objects["category"] == "starlink", "norad_id"].astype(int))
    rows = events[events["secondary_norad_id"].isin(starlink)]
    if not len(rows):
        return []
    closest = rows.groupby("secondary_norad_id")["miss_km"].min().sort_values()
    return [int(i) for i in closest.index[: int(limit)]]
