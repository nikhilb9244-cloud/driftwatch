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

**The states are kept too, and they are the trajectory (Phase 4 Step 1).** Until Phase 4
the geometry driftwatch propagated for a Starlink secondary was CelesTrak's SGP4 *fit* to
this ephemeris while the covariance came from the ephemeris itself, and Phase 2 sized the
disagreement at CelesTrak's published fit residual -- a median 0.20 km -- and added it in
quadrature. That was right for the first several hours and badly wrong afterwards. Measured
on nineteen matched file-and-element-set pairs on 2026-09-03, the fit sits this far from the
ephemeris it was fitted to:

    lead      0-12 h   12-24 h   24-36 h   36-48 h   48-60 h   60-72 h
    median   0.30 km   2.77 km  11.50 km  28.31 km  51.79 km  82.94 km

almost all of it in-track, because an SGP4 element set cannot represent three days of a
trajectory that contains planned manoeuvres. The patch was a hundredth of the error at the
end of the horizon, and worse, layering SpaceX's own covariance on top of that trajectory
replaced a roughly honest 22.8 km in-track sigma from the supplemental-consistency fit with
a 3.8 km control box that describes a trajectory we were not propagating.

So the states are stored and interpolated, and the fit leaves the chain entirely for the
events they cover. What that requires, and what each piece costs, is measured rather than
assumed:

* **The frame.** The file names declare ``MEME``, mean equator and mean equinox of J2000;
  the header names only the covariance's frame, ``UVW``. MEME is not TEME -- by 2026
  precession and nutation separate them by 0.36 degrees, about 44 km at this radius -- so
  the states are rotated on the way in by :func:`driftwatch.orbit.frames.j2000_to_teme` and
  only TEME is ever stored. Read as TEME the states sit 36 km from the SGP4 fit of the same
  satellite; rotated, 0.36 km, which is the published fit residual. That is the check.
* **The grid.** Cubic Hermite on position and velocity, thinned to
  :data:`driftwatch.config.SPACEX_STATE_STEP_S`. The error at the file's own held-out states
  is a median 5.7 m and a maximum under 7 m, against the 200 m the exercise removes.
* **The breaks.** Every file measured jumps by a few hundred metres at exactly 48 hours
  after ``ephemeris_start`` -- a seam in the ``blend`` the header names, and a planned
  manoeuvre would look the same. :func:`detect_breaks` finds them and the history is stored
  in segments, so no interpolant spans one; in the 60-second gap between segments the base
  propagator serves, exactly as it does past the 72-hour horizon.

The fit residual therefore applies **per event, not per object**:

    sigma_k(t)^2  =  sigma_k^spacex(t)^2  +  (share_k * rms_fit)^2   [only where the fit served]

``fit_rms_km`` on :class:`SpacexEphemerisCovariance` carries that residual and defaults to
:data:`driftwatch.config.SPACEX_SGP4_FIT_RMS_KM`; ``0.0`` restores the as-published
behaviour. The scalar is split across R, I and C in the shape of the base model's own
measured floor, which is in-track dominated, because that is where an SGP4 fit to an
ephemeris misses. Which events had a fit in their chain is read from the screening's own
record -- the trajectory columns of the events table, via
:func:`interpolated_times_from_events` -- rather than recomputed from a store that is
refetched every eight hours.

The file format is the "Modified ITC" of the *Spaceflight Safety Handbook for Operators*:
three or four header lines, then one state per four lines -- an epoch and position and
velocity in km and km/s, then the 21 numbers of the lower triangle of the 6x6 covariance,
row-major, in the UVW (RTN, which is our RIC) frame. The covariance is read only every
:data:`driftwatch.config.SPACEX_COVARIANCE_STEP_S` seconds -- it is smooth or piecewise
constant, so a ten-minute grid holds it to a fraction of a percent -- while the states are
read in full, because the break detector needs the file's own resolution to see a seam at
all, and then thinned. A 2 MB file becomes a few tens of kilobytes of covariance and a few
hundred of states.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.catalogue.celestrak import make_client
from driftwatch.ephemeris.hermite import HermiteSpline
from driftwatch.orbit.frames import j2000_to_teme
from driftwatch.orbit.propagator import WGS72_EARTH_RADIUS_KM
from driftwatch.orbit.time import stamp
from driftwatch.risk.covariance import CovarianceModel, ObjectRef, RicCovariance, source_array

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
POSITION_VELOCITY_COLUMNS: tuple[str, ...] = ("x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms")
STATE_COLUMNS: tuple[str, ...] = (
    "norad_id",
    "name",
    "created",
    "ephemeris_start",
    "ephemeris_stop",
    "state_frame",
    "segment",
    "t",
    *POSITION_VELOCITY_COLUMNS,
    "interp_err_median_m",
    "interp_err_p99_m",
    "interp_err_max_m",
    "n_breaks",
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


def _read_header(lines: Sequence[str]) -> tuple[dict[str, Any], int]:
    """The header dictionary and the index of the first state line."""
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
    return header, start


def _parse_states(body: Sequence[str], n_states: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Every state line: times, position (km) and velocity (km/s) in the file's own frame."""
    times = np.empty(n_states, dtype="datetime64[us]")
    r = np.empty((n_states, 3))
    v = np.empty((n_states, 3))
    for i in range(n_states):
        tokens = body[4 * i].split()
        times[i] = _parse_epoch(tokens[0])
        r[i] = [float(x) for x in tokens[1:4]]
        v[i] = [float(x) for x in tokens[4:7]]
    return times, r, v


def node_consistency_error_km(t_s: np.ndarray, r_km: np.ndarray, v_kms: np.ndarray) -> np.ndarray:
    """For every interior node, how far a Hermite interpolant through its neighbours misses it.

    This is the held-out test applied to every node at once: node ``k`` is predicted from nodes
    ``k-1`` and ``k+1``, so the answer is the interpolation error over a span of two file
    steps. On a smooth arc it is the theoretical ``a (omega h)^4 / 384`` -- 5.7 m at the files'
    60-second step -- and where the trajectory is *not* smooth it is hundreds of metres, which
    is how :func:`detect_breaks` finds the seams.
    """
    n = len(t_s)
    if n < 3:
        return np.zeros(0)
    t0, t1 = t_s[:-2], t_s[2:]
    h = t1 - t0
    s = (t_s[1:-1] - t0) / h
    s2, s3 = s * s, s * s * s
    h00 = (2 * s3 - 3 * s2 + 1)[:, None]
    h10 = (s3 - 2 * s2 + s)[:, None] * h[:, None]
    h01 = (-2 * s3 + 3 * s2)[:, None]
    h11 = (s3 - s2)[:, None] * h[:, None]
    predicted = h00 * r_km[:-2] + h10 * v_kms[:-2] + h01 * r_km[2:] + h11 * v_kms[2:]
    return np.linalg.norm(predicted - r_km[1:-1], axis=1)


def detect_breaks(
    t_s: np.ndarray,
    r_km: np.ndarray,
    v_kms: np.ndarray,
    *,
    tolerance_km: float = config.SPACEX_BREAK_TOLERANCE_KM,
) -> tuple[np.ndarray, dict[str, float]]:
    """The file intervals a trajectory is not smooth across, and the error statistics behind it.

    Every 72-hour file measured carries a discontinuity of a few hundred metres at exactly 48
    hours after ``ephemeris_start`` -- a seam between two arcs of the ``blend`` the header
    names. A planned manoeuvre would look the same and is treated the same way: an interpolant
    must not span it.

    The test is :func:`node_consistency_error_km`. A node's error covers the two intervals
    either side of it, so a break in interval ``j`` shows up as the tests at nodes ``j`` and
    ``j+1`` both being large while their neighbours are small; that is the rule applied here,
    and it localises the break to one file interval rather than to a neighbourhood of three. A
    break in the very first or very last interval cannot be seen this way, because those have a
    node error on one side only; the limitation is stated rather than papered over.

    Returns the interval indices ``j`` -- the break lies between node ``j`` and node ``j+1`` --
    and the error statistics that found them.
    """
    error = node_consistency_error_km(t_s, r_km, v_kms)
    if not len(error):
        return np.zeros(0, dtype=np.int64), {"median_m": 0.0, "max_m": 0.0, "tolerance_m": 0.0}
    median = float(np.median(error))
    # Ten times the file's own median, or the configured floor, whichever is larger: the
    # smooth-arc error and the smallest break measured are three orders of magnitude apart, so
    # this is not a fine judgement. The relative half keeps it right if the step size changes.
    tolerance = max(float(tolerance_km), 10.0 * median)
    bad = error > tolerance  # bad[k - 1] is the test at node k
    # Interval j is a break when the tests at nodes j and j+1 are both bad, which in these
    # arrays is bad[j - 1] and bad[j].
    j = np.nonzero(bad[:-1] & bad[1:])[0] + 1
    stats = {"median_m": 1000.0 * median, "max_m": 1000.0 * float(error.max()), "tolerance_m": 1000.0 * tolerance}
    return j.astype(np.int64), stats


def thin_states(
    t_s: np.ndarray,
    r_km: np.ndarray,
    v_kms: np.ndarray,
    breaks: np.ndarray,
    *,
    step_s: float,
    file_step_s: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Which states to store, which segment each belongs to, and what the thinning costs.

    The grid is a plain stride taken separately inside each segment, so a break always falls
    between two stored nodes and never inside an interpolation interval. The first and last
    node of every segment are always kept, so the stored span is the file's span less the
    breaks themselves.

    The cost is measured rather than asserted: the interpolant built from the kept nodes is
    evaluated at every node it dropped and compared with the file's own value. That is the
    hold-out test the phase asks for, and it runs on every fetch rather than once in a
    notebook.
    """
    n = len(t_s)
    stride = max(1, int(round(float(step_s) / float(file_step_s))))
    starts = [0, *(int(j) + 1 for j in breaks)]
    ends = [*(int(j) for j in breaks), n - 1]
    keep: list[int] = []
    segment: list[int] = []
    dropped: list[int] = []
    for seg, (lo, hi) in enumerate(zip(starts, ends, strict=True)):
        nodes = sorted({*range(lo, hi + 1, stride), hi})
        keep.extend(nodes)
        segment.extend([seg] * len(nodes))
        dropped.extend(sorted(set(range(lo, hi + 1)) - set(nodes)))
    keep_idx = np.asarray(keep, dtype=np.int64)
    seg_idx = np.asarray(segment, dtype=np.int64)

    errors: list[np.ndarray] = []
    for seg in range(len(starts)):
        sel = keep_idx[seg_idx == seg]
        if len(sel) < 2:
            continue
        held = np.asarray([i for i in dropped if sel[0] <= i <= sel[-1]], dtype=np.int64)
        if not len(held):
            continue
        spline = HermiteSpline(t_s[sel], r_km[sel], v_kms[sel])
        predicted, _ = spline(t_s[held])
        errors.append(np.linalg.norm(predicted - r_km[held], axis=1))
    err = np.concatenate(errors) if errors else np.zeros(0)
    quality = {
        "n_states": int(n),
        "n_kept": int(len(keep_idx)),
        "n_held_out": int(len(err)),
        "n_segments": int(len(starts)),
        "interp_err_median_m": float(1000.0 * np.median(err)) if len(err) else 0.0,
        "interp_err_p99_m": float(1000.0 * np.quantile(err, 0.99)) if len(err) else 0.0,
        "interp_err_max_m": float(1000.0 * err.max()) if len(err) else 0.0,
    }
    return keep_idx, seg_idx, quality


def parse_ephemeris(
    text: str,
    *,
    step_s: float = config.SPACEX_COVARIANCE_STEP_S,
    state_step_s: float = config.SPACEX_STATE_STEP_S,
    break_tolerance_km: float = config.SPACEX_BREAK_TOLERANCE_KM,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """The thinned position covariance, the thinned TEME state history, and the header.

    Returns a covariance frame of ``t`` and the six independent entries of the RIC position
    covariance in km^2 sampled every ``step_s`` seconds; a state frame of ``t``, position and
    velocity **rotated into TEME** and thinned to ``state_step_s`` inside each smooth segment;
    and a header dictionary carrying the counts, the segment structure and the measured
    interpolation error.

    The states are read in full even though most are thrown away, because the break detector
    needs the file's own resolution to see a seam at all. The covariance is still read only
    where it is kept, which is what makes a few hundred 2 MB files bearable.
    """
    lines = text.splitlines()
    header, start = _read_header(lines)
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
        cov[row] = [float(value) for value in body[4 * i + 1].split()[:6]]
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

    state_times, r_file, v_file = _parse_states(body, n_states)
    # The file names declare MEME, not TEME, and at this radius the two are 44 km apart.
    r_teme, v_teme = j2000_to_teme(r_file, v_file, state_times)
    t_s = (state_times - state_times[0]) / np.timedelta64(1, "s")
    breaks, break_stats = detect_breaks(t_s, r_teme, v_teme, tolerance_km=break_tolerance_km)
    keep_idx, seg_idx, quality = thin_states(t_s, r_teme, v_teme, breaks, step_s=state_step_s, file_step_s=file_step_s)
    states = pd.DataFrame(
        {
            "state_frame": str(header.get("state_frame") or config.SPACEX_STATE_FRAME),
            "segment": seg_idx,
            "t": state_times[keep_idx],
            **{name: r_teme[keep_idx][:, k] for k, name in enumerate(POSITION_VELOCITY_COLUMNS[:3])},
            **{name: v_teme[keep_idx][:, k] for k, name in enumerate(POSITION_VELOCITY_COLUMNS[3:])},
            "interp_err_median_m": quality["interp_err_median_m"],
            "interp_err_p99_m": quality["interp_err_p99_m"],
            "interp_err_max_m": quality["interp_err_max_m"],
            "n_breaks": len(breaks),
        }
    )
    header["n_states"] = n_states
    header["n_kept"] = len(frame)
    header["breaks_hours"] = [round(float(t_s[int(j)] / 3600.0), 4) for j in breaks]
    header["break_stats"] = break_stats
    header["state_quality"] = quality
    return frame, states, header


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
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Download each requested satellite's ephemeris; return its covariance, its states and a summary.

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
    state_frames: list[pd.DataFrame] = []
    failures: list[int] = []
    quality: list[dict[str, Any]] = []
    try:
        for entry in wanted:
            try:
                response = client.get(config.SPACEX_EPHEMERIS_URL + entry.file_name, headers={"Accept": "*/*"})
                response.raise_for_status()
                frame, states, header = parse_ephemeris(response.text)
            except (httpx.HTTPError, ValueError) as exc:
                log.warning("SpaceX ephemeris for %d failed (%s)", entry.norad_id, exc)
                failures.append(entry.norad_id)
                continue
            created = _header_time(header.get("created"))
            start = _header_time(header.get("ephemeris_start"))
            stop = _header_time(header.get("ephemeris_stop"))
            frame.insert(0, "norad_id", entry.norad_id)
            frame.insert(1, "name", entry.name)
            frame.insert(2, "created", created)
            frame.insert(3, "ephemeris_start", start)
            frame.insert(4, "ephemeris_stop", stop)
            frame.insert(5, "ephemeris_source", str(header.get("ephemeris_source") or ""))
            frames.append(frame)
            states.insert(0, "norad_id", entry.norad_id)
            states.insert(1, "name", entry.name)
            states.insert(2, "created", created)
            states.insert(3, "ephemeris_start", start)
            states.insert(4, "ephemeris_stop", stop)
            state_frames.append(states)
            quality.append({"norad_id": entry.norad_id, **header["state_quality"], "breaks": header["breaks_hours"]})
    finally:
        if own:
            client.close()

    table = (
        pd.concat(frames, ignore_index=True)[list(EPHEMERIS_COLUMNS)]
        if frames
        else pd.DataFrame(columns=list(EPHEMERIS_COLUMNS))
    )
    state_table = (
        pd.concat(state_frames, ignore_index=True)[list(STATE_COLUMNS)]
        if state_frames
        else pd.DataFrame(columns=list(STATE_COLUMNS))
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
        "n_state_rows": int(len(state_table)),
        "created": sorted({str(t) for t in table["created"].dropna().unique()})[:3] if len(table) else [],
        "states": _state_summary(quality),
    }
    log.info("SpaceX ephemerides: %s", summary)
    return table, state_table, summary


def _state_summary(quality: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """What the stored state grid cost, over a whole fetch: the hold-out error and the breaks.

    Reported on every fetch rather than measured once, because it is the number that says
    whether interpolating the ephemeris was worth doing: it has to be small against the
    0.20 km fit residual it replaces, and if a file ever arrives on a coarser grid it will not
    be.
    """
    if not quality:
        return {"objects": 0}
    med = np.array([q["interp_err_median_m"] for q in quality], dtype=float)
    worst = np.array([q["interp_err_max_m"] for q in quality], dtype=float)
    breaks = [h for q in quality for h in q["breaks"]]
    return {
        "objects": len(quality),
        "kept": int(sum(q["n_kept"] for q in quality)),
        "of": int(sum(q["n_states"] for q in quality)),
        "held_out": int(sum(q["n_held_out"] for q in quality)),
        "interp_err_median_m": round(float(np.median(med)), 3),
        "interp_err_worst_m": round(float(worst.max()), 3),
        "objects_with_a_break": int(sum(1 for q in quality if q["breaks"])),
        "break_hours": sorted({round(h, 2) for h in breaks})[:5],
    }


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


def state_store_path(fetched_at: datetime, out_dir: Path = config.SPACEX_DIR) -> Path:
    return Path(out_dir) / f"states_{stamp(fetched_at)}.parquet"


def write_state_store(table: pd.DataFrame, path: Path) -> Path:
    """Write one fetch's TEME states. Derived data, not the raw files: see the module docstring."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = table.copy()
    out.attrs = {}
    tmp = path.with_suffix(".tmp")
    out.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    log.info("Wrote %s (%d rows, %d satellites)", path, len(out), out["norad_id"].nunique() if len(out) else 0)
    return path


def list_state_store(out_dir: Path = config.SPACEX_DIR) -> list[Path]:
    return sorted(Path(out_dir).glob("states_*.parquet"))


def load_state_store(
    norad_ids: Sequence[int] | None = None, out_dir: Path = config.SPACEX_DIR, *, latest_only: bool = True
) -> pd.DataFrame:
    """Every stored state history, or only the newest version of each satellite."""
    paths = list_state_store(out_dir)
    if not paths:
        return pd.DataFrame(columns=list(STATE_COLUMNS))
    frames = []
    for path in paths:
        frame = pd.read_parquet(path)
        if norad_ids is not None:
            frame = frame[frame["norad_id"].isin([int(i) for i in norad_ids])]
        if len(frame):
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=list(STATE_COLUMNS))
    table = pd.concat(frames, ignore_index=True)
    if latest_only and len(table):
        newest = table.groupby("norad_id")["created"].transform("max")
        table = table[table["created"] == newest]
    return table.sort_values(["norad_id", "t"]).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# The trajectory


class EphemerisTrajectory:
    """SpaceX's published states, interpolable in TEME: the trajectory Stage C refines on.

    Why this is worth the trouble. Before Phase 4 the geometry of a Starlink event came from
    CelesTrak's SGP4 fit to one of these files while the covariance came from the file itself,
    and Phase 2 sized the disagreement at CelesTrak's published fit residual, a median 0.20 km,
    and added it in quadrature. That was right about the first several hours and badly wrong
    afterwards: measured against nineteen matched files on 2026-09-03, the fit sits a median
    0.30 km from the ephemeris inside 12 hours, **2.8 km at 12 to 24 hours, 28 km at 36 to 48
    and 83 km at 60 to 72**, almost all of it in-track, because an SGP4 element set cannot
    represent three days of a trajectory containing planned manoeuvres. The patch was a
    hundredth of the error at the end of the horizon. Interpolating the published states
    removes it instead of sizing it.

    Coverage is per segment, not per file. A file is split wherever it is not smooth --
    every one measured has a seam at exactly 48 hours -- and no interpolant spans a break, so
    a query in the 60-second gap between two segments is uncovered and the base propagator
    serves it, exactly as one past the 72-hour horizon is.
    """

    def __init__(self, table: pd.DataFrame | None = None) -> None:
        self.table = table if table is not None else pd.DataFrame(columns=list(STATE_COLUMNS))
        self.segments: dict[int, list[tuple[np.datetime64, np.datetime64, HermiteSpline]]] = {}
        self.created: dict[int, pd.Timestamp] = {}
        if not len(self.table):
            return
        for norad_id, group in self.table.groupby("norad_id"):
            spans: list[tuple[np.datetime64, np.datetime64, HermiteSpline]] = []
            for _, part in group.groupby("segment"):
                part = part.sort_values("t")
                if len(part) < 2:
                    continue
                times = pd.to_datetime(part["t"], utc=True).dt.tz_localize(None).to_numpy(dtype="datetime64[us]")
                t_s = (times - times[0]) / np.timedelta64(1, "s")
                r = part[list(POSITION_VELOCITY_COLUMNS[:3])].to_numpy(dtype=float)
                v = part[list(POSITION_VELOCITY_COLUMNS[3:])].to_numpy(dtype=float)
                spans.append((times[0], times[-1], HermiteSpline(t_s, r, v)))
            if spans:
                self.segments[int(norad_id)] = spans
                self.created[int(norad_id)] = pd.Timestamp(group["created"].iloc[0])

    def __contains__(self, norad_id: int) -> bool:
        return int(norad_id) in self.segments

    def __len__(self) -> int:
        return len(self.segments)

    @property
    def norad_ids(self) -> list[int]:
        return sorted(self.segments)

    def covers(self, norad_id: int, at: np.ndarray) -> np.ndarray:
        """Which of the requested times fall inside a stored segment of this object."""
        at64 = np.asarray(at, dtype="datetime64[us]")
        covered = np.zeros(at64.shape, dtype=bool)
        for lo, hi, _ in self.segments.get(int(norad_id), []):
            covered |= (at64 >= lo) & (at64 <= hi)
        return covered

    def states(self, norad_id: int, at: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """``(r, v, covered)`` in TEME km and km/s; rows the ephemeris does not reach are NaN."""
        at64 = np.asarray(at, dtype="datetime64[us]")
        n = at64.size
        r_out = np.full((n, 3), np.nan)
        v_out = np.full((n, 3), np.nan)
        covered = np.zeros(n, dtype=bool)
        for lo, hi, spline in self.segments.get(int(norad_id), []):
            inside = (at64 >= lo) & (at64 <= hi) & ~covered
            if not inside.any():
                continue
            t_s = (at64[inside] - lo) / np.timedelta64(1, "s")
            r, v = spline(t_s.astype(float))
            r_out[inside] = r
            v_out[inside] = v
            covered |= inside
        return r_out, v_out, covered

    def reach(self) -> dict[int, tuple[float, float, float]]:
        """What each object's published states actually reach: lowest and highest altitude, top speed.

        Stage A's two tests both have to bound the trajectory the later stages screen on, and
        the mean elements do not. Measured over 300 files on 2026-09-03, these states leave the
        mean-element shell by a median 7.6 km and by up to 32.6 km for a satellite raising its
        orbit, against only 14.6 km of pad left over the 35.4 km screening radius -- so the
        excursion is not something the pad absorbs.

        The speed is the largest actually present in the states, which is an exact bound for the
        span they cover, rather than a vis-viva speed inferred from a perigee the object may
        never reach. Outside that span the element set serves and its own bound still applies,
        so Stage A takes the larger of the two.
        """
        if not len(self.table):
            return {}
        r = self.table[list(POSITION_VELOCITY_COLUMNS[:3])].to_numpy(dtype=float)
        v = self.table[list(POSITION_VELOCITY_COLUMNS[3:])].to_numpy(dtype=float)
        frame = pd.DataFrame(
            {
                "norad_id": self.table["norad_id"].to_numpy(),
                "altitude_km": np.linalg.norm(r, axis=1) - WGS72_EARTH_RADIUS_KM,
                "speed_kms": np.linalg.norm(v, axis=1),
            }
        )
        grouped = frame.groupby("norad_id")
        low, high, fast = grouped["altitude_km"].min(), grouped["altitude_km"].max(), grouped["speed_kms"].max()
        return {int(k): (float(low[k]), float(high[k]), float(fast[k])) for k in low.index}

    def summary(self) -> dict[str, Any]:
        if not len(self.table):
            return {"satellites": 0}
        by_object = self.table.groupby("norad_id").first()
        return {
            "satellites": int(len(self.segments)),
            "rows": int(len(self.table)),
            "segments": int(sum(len(s) for s in self.segments.values())),
            "state_frame": sorted(set(self.table["state_frame"].astype(str)))[:2],
            "interp_err_median_m": round(float(by_object["interp_err_median_m"].median()), 3),
            "interp_err_max_m": round(float(by_object["interp_err_max_m"].max()), 3),
            "n_breaks_total": int(by_object["n_breaks"].sum()),
        }


class FrameCheckError(RuntimeError):
    """The stored states do not sit where an independent trajectory says they should.

    Raised rather than warned about, and raised before anything is written, because the failure
    this guards against is silent: states in the wrong frame are smooth, interpolate cleanly and
    produce plausible conjunctions in the wrong place.
    """


def check_state_frame(
    states: pd.DataFrame,
    elements: pd.DataFrame,
    *,
    max_km: float = config.SPACEX_FRAME_CHECK_MAX_KM,
    lead_hours: float = config.SPACEX_FRAME_CHECK_LEAD_HOURS,
) -> dict[str, Any]:
    """Are the stored TEME states where an independent SGP4 fit to the same file puts them?

    ``elements`` is a frame of OMM columns -- CelesTrak's supplemental sets, which are fits to
    these very files and whose residual CelesTrak publishes. Propagating one to the first few
    hours of the ephemeris and comparing gives a number with only two plausible values: a few
    hundred metres, which is that published residual, or tens of kilometres, which is a frame
    error. See ``docs/ephemeris-frame.md``.

    Returns a summary. It does not raise; the caller decides what a failure means, and
    ``driftwatch spacex`` refuses to write the store.
    """
    from driftwatch.orbit.propagator import build_satrecs
    from driftwatch.orbit.time import julian_dates

    summary: dict[str, Any] = {"objects": 0, "median_km": None, "max_km_seen": None, "threshold_km": float(max_km)}
    if not len(states) or not len(elements):
        summary["verdict"] = "not checked: no states or no element sets to check them against"
        return summary

    by_id = elements.drop_duplicates("norad_id").set_index("norad_id")
    residuals: list[float] = []
    checked: list[int] = []
    for norad_id, group in states.groupby("norad_id"):
        norad_id = int(norad_id)
        # sgp4init refuses a satellite number above 339999; the supplemental file carries
        # placeholder ids for objects with no catalogue number, and they cannot be checked.
        if norad_id not in by_id.index or norad_id > 339999:
            continue
        group = group.sort_values("t")
        times = pd.to_datetime(group["t"], utc=True).dt.tz_localize(None).to_numpy(dtype="datetime64[us]")
        lead_s = (times - times[0]) / np.timedelta64(1, "s")
        window = lead_s <= lead_hours * 3600.0
        if not window.any():
            continue
        try:
            satrec = build_satrecs(by_id.loc[[norad_id]].reset_index())[0]
        except (ValueError, KeyError):
            continue
        jd, fr = julian_dates(times[window])
        err, r_sgp4, _v = satrec.sgp4_array(jd, fr)
        ok = err == 0
        if not ok.any():
            continue
        stored = group.loc[window, list(POSITION_VELOCITY_COLUMNS[:3])].to_numpy(dtype=float)
        residuals.append(float(np.median(np.linalg.norm(stored[ok] - r_sgp4[ok], axis=1))))
        checked.append(norad_id)

    if not residuals:
        summary["verdict"] = "not checked: no satellite had both stored states and a usable element set"
        return summary
    values = np.asarray(residuals)
    summary.update(
        {
            "objects": len(values),
            "median_km": round(float(np.median(values)), 4),
            "p90_km": round(float(np.quantile(values, 0.9)), 4),
            "max_km_seen": round(float(values.max()), 4),
            "passed": bool(np.median(values) <= float(max_km)),
        }
    )
    summary["verdict"] = (
        f"pass: the states sit a median {summary['median_km']} km from an independent SGP4 fit, "
        f"which is the published fit residual and not a frame error"
        if summary["passed"]
        else (
            f"FAIL: the states sit a median {summary['median_km']} km from an independent SGP4 fit, "
            f"over the {max_km:g} km threshold. A rotation error is about 44 km at this radius. "
            f"Check the frame the files declare (see docs/ephemeris-frame.md) before using them."
        )
    )
    return summary


def interpolated_times_from_events(events: pd.DataFrame) -> dict[int, np.ndarray]:
    """Per object, the event times whose geometry came from the published states.

    Read from the events table's ``primary_trajectory`` and ``secondary_trajectory`` columns,
    which are what Stage C actually did, rather than recomputed from whatever the store holds
    now. An events table written before Phase 4 Step 1 has neither column and yields nothing,
    which is correct: every one of its events was refined on the SGP4 fit.
    """
    out: dict[int, list[np.datetime64]] = {}
    if not len(events) or "secondary_trajectory" not in events.columns:
        return {}
    tca = pd.to_datetime(events["tca"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    for role in ("primary", "secondary"):
        column = f"{role}_trajectory"
        if column not in events.columns:
            continue
        served = events[column].astype(str).to_numpy() == "spacex-ephemeris"
        ids = events[f"{role}_norad_id"].to_numpy(dtype=np.int64)
        for norad_id in np.unique(ids[served]):
            out.setdefault(int(norad_id), []).extend(tca[served & (ids == norad_id)])
    return {k: np.unique(np.asarray(v, dtype="datetime64[us]")) for k, v in out.items()}


def load_trajectory(norad_ids: Sequence[int] | None = None, out_dir: Path = config.SPACEX_DIR) -> EphemerisTrajectory:
    """The newest stored state history of each requested satellite, ready to interpolate."""
    return EphemerisTrajectory(load_state_store(norad_ids, out_dir))


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

    ``fit_rms_km`` is the published residual of CelesTrak's SGP4 fit to these ephemerides,
    added in quadrature because that fit is the trajectory driftwatch actually propagates.
    See the module docstring; ``0.0`` gives the covariance exactly as SpaceX published it.
    """

    def __init__(
        self,
        base: CovarianceModel,
        table: pd.DataFrame | None = None,
        *,
        fit_rms_km: float | None = None,
        fit_rms_share: tuple[float, float, float] | None = None,
        interpolated_times: Mapping[int, np.ndarray] | None = None,
    ) -> None:
        self.base = base
        self.table = table if table is not None else pd.DataFrame(columns=list(EPHEMERIS_COLUMNS))
        self.interpolated_times = {
            int(k): np.asarray(v, dtype="datetime64[us]") for k, v in (interpolated_times or {}).items()
        }
        self.fit_rms_km = float(config.SPACEX_SGP4_FIT_RMS_KM if fit_rms_km is None else fit_rms_km)
        self.fit_rms_share = tuple(fit_rms_share) if fit_rms_share is not None else self._share_from_base()
        self.fit_variance_km2 = np.array([(s * self.fit_rms_km) ** 2 for s in self.fit_rms_share])
        self.n_with_fit = 0
        self.n_without_fit = 0
        self.series: dict[int, tuple[np.ndarray, np.ndarray, np.datetime64, np.datetime64]] = {}
        for norad_id, group in self.table.groupby("norad_id"):
            group = group.sort_values("t")
            times = pd.to_datetime(group["t"], utc=True).dt.tz_localize(None).to_numpy(dtype="datetime64[us]")
            cov = group[list(COVARIANCE_COLUMNS)].to_numpy(dtype=float)
            start = np.datetime64(pd.Timestamp(group["ephemeris_start"].iloc[0]).tz_localize(None), "us")
            stop = np.datetime64(pd.Timestamp(group["ephemeris_stop"].iloc[0]).tz_localize(None), "us")
            self.series[int(norad_id)] = (times, cov, start, stop)
        # Version 1 was as published, version 2 as published plus the SGP4 fit residual on
        # every served covariance, and version 3 -- this one -- carries that residual only on
        # the events whose geometry still comes from the fit. The residual stays in the string
        # because where it applies it still changes the covariance.
        self.version = f"{base.version}+spacex-ephemeris/3"
        if self.fit_rms_km > 0:
            self.version += f"+sgp4-fit-{self.fit_rms_km:g}km"
        if self.interpolated_times:
            self.version += f"+interp-{len(self.interpolated_times)}"

    def _share_from_base(self) -> tuple[float, float, float]:
        """How to split CelesTrak's scalar fit residual across R, I and C.

        The base model's own measured floor is the best answer available: it is the
        version-to-version disagreement of the same fits at essentially no lead, so its shape
        is the shape those fits miss in. Where the base has no floor to take a shape from --
        an empirical model, or a supplemental table written before the floors were split --
        the configured shape stands in.
        """
        models = getattr(self.base, "models", None)
        if isinstance(models, dict):
            floors = [
                np.asarray(m.floor_km, dtype=float) for m in models.values() if getattr(m, "floor_km", None) is not None
            ]
            if floors:
                pooled = np.median(np.stack(floors), axis=0)
                total = float(np.linalg.norm(pooled))
                if np.isfinite(total) and total > 0:
                    return (float(pooled[0] / total), float(pooled[1] / total), float(pooled[2] / total))
        return tuple(float(s) for s in config.SPACEX_FIT_RMS_SHARE)  # type: ignore[return-value]

    def fit_rms_summary(self) -> dict[str, Any]:
        """What the fit-residual term adds, per component, and how many times it applied."""
        return {
            "fit_rms_km": self.fit_rms_km,
            "share": [round(s, 4) for s in self.fit_rms_share],
            "sigma_km": {k: round(float(np.sqrt(v)), 4) for k, v in zip("ric", self.fit_variance_km2, strict=True)},
            "interpolated_objects": len(self.interpolated_times),
            "served_with_fit_term": self.n_with_fit,
            "served_without_fit_term": self.n_without_fit,
        }

    @property
    def dt_floor_days(self) -> float:
        return getattr(self.base, "dt_floor_days", 0.5)

    def growth_for(self, obj: ObjectRef) -> tuple[Any, str]:
        """The base model's growth. SpaceX's covariance is a table, not a power law, so it has none."""
        return self.base.growth_for(obj)  # type: ignore[attr-defined]

    def _matrices(self, norad_id: int, at64: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The published covariance, which times the file covers, and which carry the fit residual.

        The residual is the distance from the ephemeris to the trajectory driftwatch actually
        propagates, so it belongs on a time **only when those are two different things**. An
        event Stage C refined on the interpolated states has no fit in its chain and gets the
        covariance exactly as SpaceX published it; one past the horizon, inside a break, or on
        an object whose states were not stored still has a fit in its chain and still carries
        the residual. With nothing said about which events were interpolated, the model behaves
        as version 2 did and every served time carries the residual.

        Which events those are is read from the screening's own record -- the
        ``primary_trajectory`` and ``secondary_trajectory`` columns of the events table, via
        :func:`interpolated_times_from_events` -- and not recomputed from the store. The store
        is refetched every eight hours and a rescore weeks later would otherwise silently give
        an event a covariance that does not match the geometry it was scored on.
        """
        times, cov, start, stop = self.series[norad_id]
        covered = (at64 >= start) & (at64 <= stop) & (at64 >= times[0]) & (at64 <= times[-1])
        out = np.zeros((len(at64), 3, 3))
        served_times = self.interpolated_times.get(int(norad_id))
        interpolated = np.isin(at64, served_times) if served_times is not None else np.zeros(len(at64), dtype=bool)
        if not covered.any():
            return out, covered, interpolated
        x = (at64[covered] - times[0]) / np.timedelta64(1, "s")
        xp = (times - times[0]) / np.timedelta64(1, "s")
        entries = np.stack([np.interp(x, xp, cov[:, k]) for k in range(6)], axis=1)
        rr, ri, ii, rc, ic, cc = entries.T
        block = np.empty((len(rr), 3, 3))
        block[:, 0, 0], block[:, 1, 1], block[:, 2, 2] = rr, ii, cc
        block[:, 0, 1] = block[:, 1, 0] = ri
        block[:, 0, 2] = block[:, 2, 0] = rc
        block[:, 1, 2] = block[:, 2, 1] = ic
        if self.fit_rms_km > 0:
            # Their covariance describes the ephemeris; the fit residual is the distance from
            # it to what we propagate. Independent quantities, so the residual adds in
            # quadrature on the diagonal -- which keeps the matrix positive definite and
            # dilutes the published correlations, as an added error should.
            needs_fit = ~interpolated[covered]
            block[needs_fit] += np.diag(self.fit_variance_km2)[None, :, :]
            self.n_with_fit += int(needs_fit.sum())
            self.n_without_fit += int((~needs_fit).sum())
        out[covered] = block
        return out, covered, interpolated

    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        at64 = np.asarray(at, dtype="datetime64[us]")
        if int(obj.norad_id) not in self.series:
            return self.base.covariance_ric(obj, epoch, at64)
        cov, covered, interpolated = self._matrices(int(obj.norad_id), at64)
        if not covered.any():
            return self.base.covariance_ric(obj, epoch, at64)
        served = np.where(interpolated, "spacex-ephemeris", "spacex-ephemeris+sgp4-fit")
        if self.fit_rms_km <= 0:
            served = np.full(len(at64), "spacex-ephemeris", dtype=object)
        source = np.asarray(served, dtype=object)
        if not covered.all():
            fallback = self.base.covariance_ric(obj, epoch, at64[~covered])
            cov[~covered] = fallback.cov_km2
            source[~covered] = source_array(fallback.source, int((~covered).sum()))
        return RicCovariance(cov, source)

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
