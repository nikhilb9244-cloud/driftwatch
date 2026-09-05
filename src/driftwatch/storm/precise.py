"""Calibration against precise orbits: Swarm A, B and C against ESA's precise science orbits.

Everything driftwatch says about the accuracy of a public element set rests on the
*consistency* of successive sets, which bounds the accuracy in neither direction
(``docs/methods.md``, "Uncertainty and probability"). This module is the one place a public
element set is compared with an independent truth. ESA's Swarm satellites carry GPS receivers
and ESA publishes a reduced-dynamic precise science orbit for each of them (product
``SW_OPER_SP3xCOM_2_``, ten-second states in the ITRF, centre of mass), so for every public
element set issued in a window the propagated SGP4 position can be measured against where the
satellite actually was, in the satellite's own radial, in-track, cross-track frame, at leads
from six hours to seven days.

Four things are reported by lead bin, and each element set is **one trial** -- one residual
per lead -- never one trial per timestamp, because the residuals along one set's propagation
are not independent of each other:

1. the residual distribution (median, 68th and 95th percentiles of the absolute residual per
   component);
2. the fraction of residuals inside the empirical covariance's one and two sigma, against the
   68 and 95 per cent a Gaussian claims, per component;
3. whether applying the storm term with the *observed* ap reduces the in-track residual over the
   untreated SGP4 baseline, and by how much;
4. the lead beyond which the residual exceeds a tolerance for a named task -- here the in-track
   half-width of the screening box, 25 km -- so the output reads as a horizon.

Three windows: the May 2024 storm, a quiet control before it, and one further disturbed
interval (10 to 11 October 2024) that is **held out from every tuning**. Nothing in this module
takes a parameter from the held-out window: the covariance and the ballistic coefficient used
on each window are fitted from history that ends where that window's element sets begin, and
no threshold anywhere was chosen by looking at the October result.

Manoeuvres. ESA's thruster record for these satellites is the Level 1b spacecraft-dynamics
product (``SW_OPER_SC_xDYN_1B``, a daily CDF: per-second on-times for the twelve cold-gas
thrusters and the nominal force of the orbit-control thrusters that fired). It is read here. An
orbit manoeuvre is a run of seconds with orbit-control thrust, merged across gaps shorter than
``THRUST_GAP_S``; the attitude-control pulses the same record carries (thruster on-time with no
orbit-control force, several a day) are counted and are not manoeuvres. A trial is excluded when a
manoeuvre falls between ``MANOEUVRE_ARC_HOURS`` before its element set's epoch -- the tracking
arc the set was fitted from -- and the lead it is scored at. The project's own detection (a step
in the orbit-mean semi-major axis of the precise orbit; the jump detector on the element sets)
is still computed and reported beside the record as a cross-check, and decides nothing when the
record is present.

Data gaps are flagged explicitly: a day with no precise-orbit file, and a trial lead the precise
orbit does not reach, are counted and excluded rather than interpolated across.

Sources, recorded with the result: ESA Swarm precise science orbits (TU Delft reduced-dynamic,
IGS20 frame, ten-second sampling, retrieved from ``swarm-diss.eo.esa.int``); ESA Swarm Level 1b
spacecraft dynamics (``SW_OPER_SC_xDYN_1B``, the same server) for the manoeuvre intervals;
Space-Track ``gp_history`` for the three NORAD ids; CelesTrak's ``SW-All.csv`` for the observed ap; the
``sgp4`` library for the propagation; astropy for the ITRS-to-TEME rotation. Swarm's TU Delft
thermospheric density products (``SW_OPER_DNSxPOD_2_``, on the same server) could later separate
the atmosphere's error from the object's response and are not part of this week.
"""

from __future__ import annotations

import gc
import json
import logging
import re
import tempfile
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.drag import ballistic as ballistic_mod
from driftwatch.drag import density as dn
from driftwatch.ephemeris.hermite import HermiteSpline
from driftwatch.orbit.frames import itrs_to_teme, j2000_to_teme
from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs
from driftwatch.orbit.time import parse_utc
from driftwatch.risk.covariance import EmpiricalCovariance, ObjectRef, fit_covariance, osculating_semi_major_axis_km
from driftwatch.screening.ric import ric_basis, to_ric
from driftwatch.storm import validation

log = logging.getLogger(__name__)

# Swarm's NORAD ids: 2013-067A is Swarm B, 2013-067B Swarm A, 2013-067C Swarm C.
SWARM: dict[str, int] = {"A": 39452, "B": 39451, "C": 39453}
SWARM_DISS_URL = "https://swarm-diss.eo.esa.int/"
SWARM_POD_DIR = "swarm/Level2daily/Entire_mission_data/POD/RD/Sat_{letter}"
SWARM_DYN_DIR = "swarm/Level1b/Entire_mission_data/SC_xDYN/Sat_{letter}"
SWARM_DYN_PRODUCT = (
    "SW_OPER_SC_xDYN_1B (Level 1b spacecraft dynamics, daily CDF; swarm/Level1b/Entire_mission_data/SC_xDYN)"
)
# The published record. Seconds of orbit-control thrust closer together than this are one
# manoeuvre. A trial is excluded when a manoeuvre falls between this many hours before its
# element set's epoch -- the tracking arc the set was fitted from, which a burn corrupts as
# surely as a burn inside the propagation does -- and the lead it is scored at.
THRUST_GAP_S = 600.0
MANOEUVRE_ARC_HOURS = 24.0
SWARM_DENSITY_PRODUCT = (
    "SW_OPER_DNSxPOD_2_ (TU Delft thermospheric density from POD; swarm/Level2daily/Entire_mission_data/DNS)"
)

LEADS_HOURS: tuple[float, ...] = (6.0, 12.0, 24.0, 36.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0)
COVARIANCE_HISTORY_DAYS = 45
COEFFICIENT_HISTORY_DAYS = 36
# The named task the horizon is stated for: keeping the object inside the in-track half-width of
# the screening box driftwatch searches (2 x 25 x 25 km), at the 95th percentile of trials.
HORIZON_TOLERANCE_KM = 25.0
HORIZON_QUANTILE = 0.95
# A step in the orbit-mean semi-major axis between consecutive orbits larger than this, and than
# six times the robust scatter of the steps, is a manoeuvre. Storm-time decay at 460 km is a few
# metres an orbit; a Swarm orbit-maintenance burn is tens of metres in one.
MANOEUVRE_STEP_M = 20.0
MANOEUVRE_STEP_MAD_FACTOR = 6.0
# Consecutive samples further apart than this, or than three times the table's own median step, start a
# new interpolation segment: 30 s for ESA's ten-second product, three steps for a coarser ephemeris.
GAP_S = 30.0


@dataclass(frozen=True)
class BenchmarkWindow:
    """Element sets issued in ``[sets_from, sets_to)`` are the trials; the truth must reach ``truth_to``."""

    name: str
    role: str  # "control", "storm" or "held-out"
    sets_from: datetime
    sets_to: datetime
    disturbed: tuple[datetime, datetime] | None
    note: str

    @property
    def truth_to(self) -> datetime:
        return self.sets_to + timedelta(hours=max(LEADS_HOURS)) + timedelta(hours=1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "sets_from": self.sets_from.isoformat(),
            "sets_to": self.sets_to.isoformat(),
            "truth_to": self.truth_to.isoformat(),
            "disturbed": [t.isoformat() for t in self.disturbed] if self.disturbed else None,
            "note": self.note,
        }


WINDOWS: tuple[BenchmarkWindow, ...] = (
    BenchmarkWindow(
        "quiet",
        "control",
        parse_utc("2024-04-20T00:00:00Z"),
        parse_utc("2024-04-27T00:00:00Z"),
        None,
        "the quiet control before the May 2024 storm; Kp at or under 4 over 25 to 28 April",
    ),
    BenchmarkWindow(
        "storm",
        "storm",
        parse_utc("2024-05-06T00:00:00Z"),
        parse_utc("2024-05-13T00:00:00Z"),
        (parse_utc("2024-05-10T12:00:00Z"), parse_utc("2024-05-13T00:00:00Z")),
        "the May 2024 Gannon storm; sets issued from four days before the onset to its end",
    ),
    BenchmarkWindow(
        "held-out",
        "held-out",
        parse_utc("2024-10-06T00:00:00Z"),
        parse_utc("2024-10-13T00:00:00Z"),
        (parse_utc("2024-10-10T12:00:00Z"), parse_utc("2024-10-12T00:00:00Z")),
        "the 10 to 11 October 2024 storm (Kp 9-), held out from every tuning; nothing was chosen by looking at it",
    ),
)


# --------------------------------------------------------------------------------------
# The precise orbits: listing, fetching, parsing, interpolating


def _client(client: httpx.Client | None) -> httpx.Client:
    return client or httpx.Client(timeout=120.0, headers={"User-Agent": config.USER_AGENT}, follow_redirects=True)


def _server_listing(
    folder: str, path: Path, *, offline: bool, client: httpx.Client | None, page: int = 3000
) -> list[dict[str, Any]]:
    """The server's listing of one folder, paged, and cached at ``path`` for a day."""
    if path.exists() and (
        offline or (datetime.now(UTC) - datetime.fromtimestamp(path.stat().st_mtime, UTC)) < timedelta(days=1)
    ):
        return json.loads(path.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError(f"no cached Swarm listing for {folder} at {path}")
    results: list[dict[str, Any]] = []
    with _client(client) as c:
        pos = 0
        while True:
            params = {"do": "list", "maxfiles": str(page), "pos": str(pos), "file": folder}
            r = c.get(SWARM_DISS_URL, params=params)
            r.raise_for_status()
            batch = r.json().get("results", [])
            results.extend(batch)
            if len(batch) < page:
                break
            pos += page
    listing = [{"name": e["name"], "path": e["path"], "size": int(e["size"])} for e in results if not e.get("is_dir")]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(listing), encoding="utf-8")
    return listing


def _fetch_entry(entry: dict[str, Any], dest_dir: Path, *, offline: bool, client: httpx.Client | None) -> Path | None:
    """One listed file, from the cache or the server; None when offline and not cached."""
    dest = dest_dir / entry["name"]
    if dest.exists() and dest.stat().st_size == entry["size"]:
        return dest
    if offline:
        return None
    url = SWARM_DISS_URL + "?do=download&file=" + urllib.parse.quote(entry["path"], safe="")
    with _client(client) as c:
        r = c.get(url)
        r.raise_for_status()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
    log.info("Fetched %s (%d bytes)", entry["name"], len(r.content))
    return dest


def list_pod_files(
    letter: str, *, cache_dir: Path = config.CACHE_DIR, offline: bool = False, client: httpx.Client | None = None
) -> list[dict[str, Any]]:
    """The server's listing of the reduced-dynamic precise orbit files for one satellite, cached."""
    path = cache_dir / "swarm" / f"listing_{letter}.json"
    return _server_listing(SWARM_POD_DIR.format(letter=letter), path, offline=offline, client=client)


_NAME = re.compile(r"_2__(\d{8})T\d{6}_(\d{8})T\d{6}_(\d{4})\.ZIP$", re.IGNORECASE)


def pod_file_for_day(listing: list[dict[str, Any]], day: date) -> dict[str, Any] | None:
    """The file whose validity ends on ``day`` (each covers 23:59:42 the day before to 23:59:42 that day)."""
    stamp = day.strftime("%Y%m%d")
    hits = [e for e in listing if (m := _NAME.search(e["name"])) and m.group(2) == stamp]
    if not hits:
        return None
    return max(hits, key=lambda e: _NAME.search(e["name"]).group(3))  # type: ignore[union-attr]


def fetch_pod_day(
    letter: str,
    day: date,
    *,
    listing: list[dict[str, Any]],
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> Path | None:
    """The zipped precise orbit for one satellite-day, from the cache or the server; None is a data gap."""
    entry = pod_file_for_day(listing, day)
    if entry is None:
        return None
    return _fetch_entry(entry, cache_dir / "swarm", offline=offline, client=client)


def sp3_epochs_to_utc(epochs: pd.Series, time_system: str) -> pd.Series:
    """SP3 epochs, written in the file's time system, as UTC.

    ESA's Swarm files are in GPS time (``%c M  cc GPS``), which runs 19 s behind TAI and, in
    2024, 18 s ahead of UTC. Read as UTC, every truth state would be the satellite 18 s -- 137 km
    along track -- later than the time it is compared at, which is what the first run of this
    benchmark showed at every lead. GPS and TAI are converted through astropy's leap-second
    table; UTC passes through; anything else is refused by name.
    """
    system = (time_system or "UTC").strip().upper()
    if system == "UTC":
        return epochs
    from astropy.time import Time, TimeDelta

    t64 = pd.to_datetime(epochs).to_numpy(dtype="datetime64[us]")
    if system == "GPS":
        tai = Time(t64, format="datetime64", scale="tai") + TimeDelta(19.0, format="sec")
    elif system == "TAI":
        tai = Time(t64, format="datetime64", scale="tai")
    else:
        raise ValueError(f"SP3 time system {time_system!r} is not UTC, GPS or TAI")
    return pd.Series(np.asarray(tai.utc.datetime64, dtype="datetime64[us]"), index=epochs.index)


def parse_sp3(text: str) -> pd.DataFrame:
    """SP3-c/d position and velocity records: times in UTC, km and km/s in the file's Earth-fixed frame.

    Velocities in SP3 are decimetres per second. An epoch whose position record is the SP3 "bad
    or absent" value (all zeros) is dropped, so a gap in the product stays a gap here. The time
    system is read from the first ``%c`` line (columns 10 to 12) and the epochs are converted to
    UTC by :func:`sp3_epochs_to_utc`; a file with no ``%c`` line is taken as UTC.
    """
    rows: list[tuple[Any, ...]] = []
    epoch: pd.Timestamp | None = None
    pos: tuple[float, float, float] | None = None
    time_system = ""
    for line in text.splitlines():
        if line.startswith("%c") and not time_system:
            time_system = line[9:12].strip() or "UTC"
        elif line.startswith("*"):
            if epoch is not None and pos is not None:
                rows.append((epoch, *pos, np.nan, np.nan, np.nan))
            f = line[1:].split()
            sec = float(f[5])
            epoch = pd.Timestamp(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4])) + pd.Timedelta(seconds=sec)
            pos = None
        elif line.startswith("P") and epoch is not None:
            x, y, z = (float(line[4:18]), float(line[18:32]), float(line[32:46]))
            pos = None if (x == 0.0 and y == 0.0 and z == 0.0) else (x, y, z)
        elif line.startswith("V") and epoch is not None and pos is not None:
            vx, vy, vz = (float(line[4:18]) * 1e-4, float(line[18:32]) * 1e-4, float(line[32:46]) * 1e-4)
            rows.append((epoch, *pos, vx, vy, vz))
            pos = None
        elif line.startswith("EOF"):
            break
    if epoch is not None and pos is not None:
        rows.append((epoch, *pos, np.nan, np.nan, np.nan))
    frame = pd.DataFrame(rows, columns=["t", "x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"])
    frame["t"] = pd.to_datetime(frame["t"]).astype("datetime64[us]")
    if len(frame):
        frame["t"] = sp3_epochs_to_utc(frame["t"], time_system)
    frame = frame.sort_values("t").drop_duplicates("t").reset_index(drop=True)
    frame.attrs["time_system"] = time_system or "UTC"
    return frame


def read_pod_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".sp3"))
        return parse_sp3(z.read(name).decode("ascii", "replace"))


def frame_kind(frame: str) -> str:
    """``"ITRF"``, ``"TEME"`` or ``"J2000"`` for a frame name the rotation supports; anything else is refused."""
    key = str(frame).upper().replace("-", "").replace("_", "").replace(" ", "")
    if key.startswith("ITRF") or key in ("ITRS", "ECEF", "EFG"):
        return "ITRF"
    if key == "TEME":
        return "TEME"
    if key in ("J2000", "EME2000", "ICRF", "GCRF", "MEME"):
        return "J2000"
    raise ValueError(f"unsupported ephemeris frame {frame!r}: ITRF, TEME, or J2000/EME2000 only")


def _rotate_to_teme(frame: str, r: np.ndarray, v: np.ndarray, times: np.ndarray) -> np.ndarray:
    """Positions in TEME from positions tabulated in ``frame``: ITRF, TEME, or J2000/EME2000."""
    kind = frame_kind(frame)
    if kind == "ITRF":
        return itrs_to_teme(r, v, times)[0]
    if kind == "TEME":
        return np.asarray(r, dtype=float)
    return j2000_to_teme(r, v, times)[0]


@dataclass
class PreciseOrbit:
    """One satellite's precise orbit over a span: tabulated states, interpolable, with the gaps kept.

    Positions are interpolated in the table's own frame with the product's own velocities
    (cubic Hermite on the ten-second grid; the error is centimetres), then rotated into TEME.
    The inertial velocity a RIC frame needs is taken from the rotated positions five seconds
    either side rather than from the rotated velocity, which for an Earth-fixed table is the
    velocity relative to the rotating Earth and would need the omega-cross-r term put back.
    ``frame`` names the table's frame: ITRF for ESA's product; TEME or J2000/EME2000 for an
    operator's own ephemeris on the local path.
    """

    letter: str
    norad_id: int
    table: pd.DataFrame
    days_missing: list[date]
    files: list[str]
    frame: str = "ITRF"
    segments: list[tuple[np.datetime64, np.datetime64, HermiteSpline]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not len(self.table):
            return
        t = self.table["t"].to_numpy(dtype="datetime64[us]")
        steps = np.diff(t) / np.timedelta64(1, "s")
        gap_s = max(GAP_S, 3.0 * float(np.median(steps))) if steps.size else GAP_S
        gaps = steps > gap_s
        starts = np.concatenate([[0], np.nonzero(gaps)[0] + 1])
        ends = np.concatenate([np.nonzero(gaps)[0] + 1, [len(t)]])
        r = self.table[["x_km", "y_km", "z_km"]].to_numpy(dtype=float)
        v = self.table[["vx_kms", "vy_kms", "vz_kms"]].to_numpy(dtype=float)
        for s, e in zip(starts, ends, strict=True):
            if e - s < 2 or not np.isfinite(v[s:e]).all():
                continue
            seconds = (t[s:e] - t[s]) / np.timedelta64(1, "s")
            self.segments.append((t[s], t[e - 1], HermiteSpline(seconds.astype(float), r[s:e], v[s:e])))

    @property
    def span(self) -> tuple[pd.Timestamp, pd.Timestamp] | None:
        if not len(self.table):
            return None
        return pd.Timestamp(self.table["t"].iloc[0]), pd.Timestamp(self.table["t"].iloc[-1])

    def states_itrs(self, at: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Earth-fixed ``(r, v, covered)`` at the times; NaN where no segment reaches."""
        at64 = np.asarray(at, dtype="datetime64[us]")
        n = at64.size
        r_out = np.full((n, 3), np.nan)
        v_out = np.full((n, 3), np.nan)
        covered = np.zeros(n, dtype=bool)
        for lo, hi, spline in self.segments:
            inside = (at64 >= lo) & (at64 <= hi) & ~covered
            if not inside.any():
                continue
            r, v = spline(((at64[inside] - lo) / np.timedelta64(1, "s")).astype(float))
            r_out[inside] = r
            v_out[inside] = v
            covered |= inside
        return r_out, v_out, covered

    def states_teme(self, at: np.ndarray, *, half_step_s: float = 5.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Inertial ``(r, v, covered)`` in TEME, km and km/s, at the times."""
        at64 = np.asarray(at, dtype="datetime64[us]")
        offsets = np.array([-half_step_s, 0.0, half_step_s]) * np.timedelta64(1_000_000, "us")
        stacked = (at64[:, None] + offsets[None, :].astype("timedelta64[us]")).ravel()
        r_itrs, v_itrs, covered = self.states_itrs(stacked)
        ok = covered.reshape(-1, 3).all(axis=1)
        r_teme = np.full((at64.size, 3), np.nan)
        v_teme = np.full((at64.size, 3), np.nan)
        if not ok.any():
            return r_teme, v_teme, ok
        idx = np.repeat(ok, 3)
        r_rot = _rotate_to_teme(self.frame, r_itrs[idx], v_itrs[idx], stacked[idx]).reshape(-1, 3, 3)
        r_teme[ok] = r_rot[:, 1, :]
        v_teme[ok] = (r_rot[:, 2, :] - r_rot[:, 0, :]) / (2.0 * half_step_s)
        return r_teme, v_teme, ok


def load_precise_orbit(
    letter: str,
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> PreciseOrbit:
    """Every day from ``start`` to ``end`` inclusive, with the days that have no file recorded as gaps."""
    listing = list_pod_files(letter, cache_dir=cache_dir, offline=offline, client=client)
    frames: list[pd.DataFrame] = []
    missing: list[date] = []
    files: list[str] = []
    day = start
    while day <= end:
        path = fetch_pod_day(letter, day, listing=listing, cache_dir=cache_dir, offline=offline, client=client)
        if path is None:
            missing.append(day)
        else:
            frames.append(read_pod_zip(path))
            files.append(path.name)
        day += timedelta(days=1)
    table = (
        pd.concat(frames, ignore_index=True).sort_values("t").drop_duplicates("t").reset_index(drop=True)
        if frames
        else pd.DataFrame(columns=["t", "x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"])
    )
    if missing:
        log.warning(
            "Swarm %s: no precise orbit file for %d day(s): %s", letter, len(missing), [d.isoformat() for d in missing]
        )
    return PreciseOrbit(letter, SWARM[letter], table, missing, files)


# --------------------------------------------------------------------------------------
# ESA's published thruster record: the Level 1b spacecraft-dynamics product


@dataclass
class ThrusterRecord:
    """One satellite's orbit-manoeuvre intervals over a span, read from ``SW_OPER_SC_xDYN_1B``.

    ``intervals`` are the runs of orbit-control thrust (the product's ``f_thr``, the nominal
    force of the orbit-control thrusters that fired, non-zero), merged across gaps shorter than
    ``THRUST_GAP_S``; ``n_attitude_pulses`` counts the bursts of thruster on-time with no
    orbit-control force, which are attitude control and are not manoeuvres;
    ``header_manoeuvre_ids`` is what each day's header lists under ``Maneuver_Information``,
    kept for the record and not used.
    """

    letter: str
    norad_id: int
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]]
    days_missing: list[date]
    files: list[str]
    n_attitude_pulses: int
    orbit_thrust_s: float
    header_manoeuvre_ids: dict[str, list[str]] = field(default_factory=dict)


_DYN_NAME = re.compile(r"_1B_(\d{8})T\d{6}_(\d{8})T\d{6}_(\d{4})\.CDF\.ZIP$", re.IGNORECASE)


def list_dyn_files(
    letter: str, *, cache_dir: Path = config.CACHE_DIR, offline: bool = False, client: httpx.Client | None = None
) -> list[dict[str, Any]]:
    """The server's listing of the spacecraft-dynamics files for one satellite, cached."""
    path = cache_dir / "swarm" / "SC_xDYN" / f"listing_{letter}.json"
    return _server_listing(SWARM_DYN_DIR.format(letter=letter), path, offline=offline, client=client)


def dyn_file_for_day(listing: list[dict[str, Any]], day: date) -> dict[str, Any] | None:
    """The file for ``day`` (each covers 00:00:00 to 23:59:59 of one day) at its newest version."""
    stamp = day.strftime("%Y%m%d")
    hits = [e for e in listing if (m := _DYN_NAME.search(e["name"])) and m.group(1) == stamp]
    if not hits:
        return None
    return max(hits, key=lambda e: _DYN_NAME.search(e["name"]).group(3))  # type: ignore[union-attr]


def fetch_dyn_day(
    letter: str,
    day: date,
    *,
    listing: list[dict[str, Any]],
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> Path | None:
    """The zipped dynamics file for one satellite-day, from the cache or the server; None is a gap."""
    entry = dyn_file_for_day(listing, day)
    if entry is None:
        return None
    return _fetch_entry(entry, cache_dir / "swarm" / "SC_xDYN", offline=offline, client=client)


def read_dyn_zip(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Per-second thruster on-time and orbit-control force from one daily file, and the header's manoeuvre ids.

    The zip holds the CDF, an XML header and a quality report. The CDF is read with cdflib from
    a temporary extraction; ``dt_thr`` (on-time per thruster, twelve columns, seconds) is summed
    across thrusters and ``f_thr`` (nominal force of the activated orbit-control thrusters, mN,
    three components) is reduced to its magnitude.
    """
    import cdflib

    with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        cdf_name = next(n for n in z.namelist() if n.lower().endswith(".cdf"))
        hdr_name = next((n for n in z.namelist() if n.lower().endswith(".hdr")), None)
        ids: list[str] = []
        if hdr_name:
            header = z.read(hdr_name).decode("utf-8", "replace")
            ids = re.findall(r"<Maneuver_Id>\s*([^<\s]+)\s*</Maneuver_Id>", header)
        extracted = Path(z.extract(cdf_name, tmp))
        cdf = cdflib.CDF(extracted)
        t = np.asarray(cdflib.cdfepoch.to_datetime(cdf.varget("Timestamp")))
        on = np.atleast_2d(np.asarray(cdf.varget("dt_thr"), dtype=float))
        force = np.atleast_2d(np.asarray(cdf.varget("f_thr"), dtype=float))
        # cdflib keeps the file open for as long as the object lives, and Windows will not remove
        # an open file: drop the object before the temporary directory goes.
        del cdf
        gc.collect()
    frame = pd.DataFrame(
        {
            "t": pd.to_datetime(np.asarray(t)).astype("datetime64[us]"),
            "on_time_s": on.sum(axis=1),
            "force_mn": np.linalg.norm(force, axis=1),
        }
    )
    return frame.sort_values("t").reset_index(drop=True), ids


def _group_seconds(times: np.ndarray, gap_s: float) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Runs of timestamps separated by less than ``gap_s``, as (first, last) pairs."""
    if not times.size:
        return []
    times = np.sort(np.asarray(times, dtype="datetime64[us]"))
    breaks = np.nonzero(np.diff(times) / np.timedelta64(1, "s") > gap_s)[0]
    starts = np.concatenate([[0], breaks + 1])
    ends = np.concatenate([breaks, [times.size - 1]])
    return [(pd.Timestamp(times[a]), pd.Timestamp(times[b])) for a, b in zip(starts, ends, strict=True)]


def thruster_intervals(
    frame: pd.DataFrame, *, gap_s: float = THRUST_GAP_S
) -> tuple[list[tuple[pd.Timestamp, pd.Timestamp]], int, float]:
    """``(orbit manoeuvre intervals, attitude pulse count, seconds of orbit-control thrust)`` from the table."""
    if not len(frame):
        return [], 0, 0.0
    t = frame["t"].to_numpy(dtype="datetime64[us]")
    orbit = frame["force_mn"].to_numpy(dtype=float) > 0.0
    any_on = frame["on_time_s"].to_numpy(dtype=float) > 0.0
    intervals = _group_seconds(t[orbit], gap_s)
    pulses = _group_seconds(t[any_on & ~orbit], gap_s)
    return intervals, len(pulses), float(np.nansum(frame["on_time_s"].to_numpy(dtype=float)[orbit]))


def load_thruster_record(
    letter: str,
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> ThrusterRecord:
    """ESA's thruster record for every day from ``start`` to ``end`` inclusive; a day with no file is a gap."""
    listing = list_dyn_files(letter, cache_dir=cache_dir, offline=offline, client=client)
    frames: list[pd.DataFrame] = []
    missing: list[date] = []
    files: list[str] = []
    ids: dict[str, list[str]] = {}
    day = start
    while day <= end:
        path = fetch_dyn_day(letter, day, listing=listing, cache_dir=cache_dir, offline=offline, client=client)
        if path is None:
            missing.append(day)
        else:
            frame, day_ids = read_dyn_zip(path)
            frames.append(frame)
            files.append(path.name)
            ids[day.isoformat()] = day_ids
        day += timedelta(days=1)
    table = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["t", "on_time_s", "force_mn"])
    intervals, pulses, thrust_s = thruster_intervals(table)
    if missing:
        log.warning(
            "Swarm %s: no thruster record for %d day(s): %s", letter, len(missing), [d.isoformat() for d in missing]
        )
    log.info(
        "Swarm %s thruster record %s to %s: %d orbit manoeuvre(s), %.1f s of orbit-control thrust, %d attitude pulses",
        letter,
        start.isoformat(),
        end.isoformat(),
        len(intervals),
        thrust_s,
        pulses,
    )
    return ThrusterRecord(letter, SWARM.get(letter, 0), intervals, missing, files, pulses, thrust_s, ids)


# --------------------------------------------------------------------------------------
# Manoeuvres, detected from the precise orbit


def manoeuvre_intervals_from_orbit(
    orbit: PreciseOrbit, *, step_m: float = MANOEUVRE_STEP_M, mad_factor: float = MANOEUVRE_STEP_MAD_FACTOR
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Intervals in which the orbit-mean semi-major axis stepped by more than drag can move it in an orbit.

    The osculating semi-major axis is computed every minute from the inertial state, averaged
    over one orbital period, and differenced one period apart; a difference beyond ``step_m``
    and beyond ``mad_factor`` times the robust scatter of the differences marks a burn, and the
    interval returned spans about two orbits either side of it, which is the resolution the
    orbit-mean differencing has; a trial whose propagation touches it is excluded, conservatively.
    """
    if not len(orbit.table):
        return []
    t = orbit.table["t"].to_numpy(dtype="datetime64[us]")[::6]  # every minute
    r, v, ok = orbit.states_teme(t)
    if ok.sum() < 300:
        return []
    a_km = np.full(t.size, np.nan)
    a_km[ok] = osculating_semi_major_axis_km(r[ok], v[ok])
    period_min = int(round(2.0 * np.pi * np.sqrt(np.nanmedian(a_km) ** 3 / 398600.4418) / 60.0))
    series = pd.Series(a_km)
    # Full windows only: a partial window at the table's edge does not cancel the J2 short-period term
    # in the osculating semi-major axis, and reads as a step of hundreds of metres.
    mean_a = series.rolling(period_min, center=True, min_periods=period_min).mean().to_numpy()
    step = (mean_a[period_min:] - mean_a[:-period_min]) * 1000.0
    finite = np.isfinite(step)
    if finite.sum() < 10:
        return []
    mad = 1.4826 * np.nanmedian(np.abs(step[finite] - np.nanmedian(step[finite])))
    threshold = max(step_m, mad_factor * mad)
    flagged = np.zeros(t.size, dtype=bool)
    hits = np.nonzero(finite & (np.abs(step - np.nanmedian(step[finite])) > threshold))[0]
    for k in hits:
        lo, hi = max(k - period_min // 2, 0), min(k + period_min + period_min // 2, t.size - 1)
        flagged[lo : hi + 1] = True
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    if not flagged.any():
        return intervals
    edges = np.diff(np.concatenate([[0], flagged.astype(int), [0]]))
    for s, e in zip(np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0], strict=True):
        intervals.append((pd.Timestamp(t[s]), pd.Timestamp(t[e - 1])))
    return intervals


def manoeuvre_intervals_from_sets(sets: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """The project's own jump detector on the element sets, as intervals between the sets either side of a burn."""
    sets = sets.sort_values("epoch").drop_duplicates("epoch", keep="last").reset_index(drop=True)
    if len(sets) < 2:
        return []
    jump, _ = ballistic_mod.manoeuvre_intervals(sets)
    epochs = pd.to_datetime(sets["epoch"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    return [(pd.Timestamp(epochs[k]), pd.Timestamp(epochs[k + 1])) for k in np.nonzero(jump)[0]]


def _overlaps(intervals: list[tuple[pd.Timestamp, pd.Timestamp]], start: pd.Timestamp, end: pd.Timestamp) -> bool:
    return any(lo <= end and hi >= start for lo, hi in intervals)


# --------------------------------------------------------------------------------------
# The trials


@dataclass
class SatelliteInputs:
    """Everything one satellite needs for one window, fitted from history that ends where the window begins."""

    label: str
    norad_id: int
    sets: pd.DataFrame  # every element set held, for the manoeuvre detector and the storm term
    trial_sets: pd.DataFrame  # the sets issued inside the window: one trial each
    covariance: EmpiricalCovariance
    covariance_source: str
    coefficient: pd.Series | None
    category: str
    altitude_band: str
    covariance_history: tuple[pd.Timestamp | None, pd.Timestamp | None, int] = (None, None, 0)


def fit_inputs(
    norad_id: int,
    sets: pd.DataFrame,
    window: BenchmarkWindow,
    grid: dn.WeatherGrid | None,
    *,
    label: str | None = None,
    category: str = "payload",
    altitude_band: str = "leo",
) -> SatelliteInputs:
    """Fit the covariance and the ballistic coefficient from history before the window, and pick the trials.

    The covariance is fitted from the ``COVARIANCE_HISTORY_DAYS`` of sets before the window's
    first trial set and from nothing earlier or later -- the span the screening's daily fit uses --
    and the coefficient from the ``COEFFICIENT_HISTORY_DAYS`` before it. Both stop where the
    trials begin, so on the held-out window neither has seen anything of it.
    """
    norad_id = int(norad_id)
    label = label or str(norad_id)
    own = sets[sets["norad_id"] == norad_id].sort_values("epoch").drop_duplicates("epoch", keep="last")
    epochs = pd.to_datetime(own["epoch"], utc=True)
    start_ts = pd.Timestamp(window.sets_from)
    before = own[epochs < start_ts].reset_index(drop=True)
    trials = own[(epochs >= start_ts) & (epochs < pd.Timestamp(window.sets_to))].reset_index(drop=True)
    cov_from = start_ts - pd.Timedelta(days=COVARIANCE_HISTORY_DAYS)
    cov_history = before[pd.to_datetime(before["epoch"], utc=True) >= cov_from].reset_index(drop=True)
    objects = pd.DataFrame({"norad_id": [norad_id], "category": [category], "altitude_band": [altitude_band]})
    fit = fit_covariance(cov_history, objects, now=window.sets_from, window=(cov_from.date(), start_ts.date()))
    _, source = fit.model.growth_for(ObjectRef(norad_id, category, altitude_band))
    coefficient: pd.Series | None = None
    if grid is not None and len(before):
        frame = ballistic_mod.coefficients(
            before.iloc[[-1]].reset_index(drop=True),
            grid,
            before,
            fit_days=COEFFICIENT_HISTORY_DAYS,
            budget_s=0,
            store=None,
            step_scale=config.BALLISTIC_FIT_STEP_SCALE,
            now=window.sets_from,
        )
        coefficient = validation.coefficient_for(frame, norad_id)
    span: tuple[pd.Timestamp | None, pd.Timestamp | None, int] = (None, None, 0)
    if len(cov_history):
        span = (
            pd.Timestamp(cov_history["epoch"].iloc[0]),
            pd.Timestamp(cov_history["epoch"].iloc[-1]),
            len(cov_history),
        )
    return SatelliteInputs(
        label,
        norad_id,
        own.reset_index(drop=True),
        trials,
        fit.model,
        source,
        coefficient,
        category,
        altitude_band,
        span,
    )


def _naive(ts: Any) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    return t.tz_convert(None) if t.tzinfo else t


def satellite_trials(
    inputs: SatelliteInputs,
    orbit: PreciseOrbit,
    window: BenchmarkWindow,
    grid: dn.WeatherGrid | None,
    *,
    leads_hours: tuple[float, ...] = LEADS_HOURS,
    record: ThrusterRecord | None = None,
    published: list[tuple[Any, Any]] | None = None,
    arc_hours: float = MANOEUVRE_ARC_HOURS,
) -> pd.DataFrame:
    """One row per element set per lead: the residual against the precise orbit and everything that qualifies it.

    ``in_track_km`` is truth minus SGP4 along the truth's velocity, so it is positive when the
    satellite is ahead of where the set put it -- the storm term's own sign -- and the corrected
    residual is ``in_track_km - storm_shift_km``.

    Manoeuvres. With a published record (``record``, ESA's product; or ``published``, intervals
    from an operator's own file) a trial is excluded when a manoeuvre falls between ``arc_hours``
    before its set's epoch and the lead's time. The project's own detection is computed either
    way and kept in ``manoeuvre_detected`` as a cross-check; without a record it is what
    excludes. ``manoeuvre_source`` says which on every row.
    """
    detected = manoeuvre_intervals_from_orbit(orbit) + manoeuvre_intervals_from_sets(inputs.sets)
    if record is not None:
        published_intervals: list[tuple[pd.Timestamp, pd.Timestamp]] | None = list(record.intervals)
        source = "esa-record"
    elif published is not None:
        published_intervals = [(_naive(lo), _naive(hi)) for lo, hi in published]
        source = "operator-record"
    else:
        published_intervals = None
        source = "detected"
    arc = pd.Timedelta(hours=arc_hours)
    disturbed = tuple(_naive(t) for t in window.disturbed) if window.disturbed else None
    leads = np.asarray(leads_hours, dtype=float)
    rows: list[dict[str, Any]] = []
    ref = ObjectRef(inputs.norad_id, inputs.category, inputs.altitude_band)
    for _, row in inputs.trial_sets.iterrows():
        one = row.to_frame().T.reset_index(drop=True)
        epoch = _naive(row["epoch"])
        at = (np.datetime64(epoch.to_datetime64(), "us") + (leads * 3600.0 * 1e6).astype("timedelta64[us]")).astype(
            "datetime64[us]"
        )
        satrecs = build_satrecs(one)
        state = propagate_satrecs(satrecs, one["norad_id"].to_numpy(), at)
        r_sgp4 = state.r_teme[0]
        err = state.error[0]
        r_true, v_true, covered = orbit.states_teme(at)
        sigma = np.sqrt(np.einsum("nii->ni", inputs.covariance.covariance_ric(ref, epoch.to_pydatetime(), at).cov_km2))
        shift = np.full(leads.size, np.nan)
        b_source = "none"
        if grid is not None and inputs.coefficient is not None:
            # The storm term's own path (the May 2024 validation's), with tz-aware times as it expects.
            at_utc = pd.Series(pd.DatetimeIndex(at).tz_localize("UTC"))
            predicted = validation.predicted_shifts(
                inputs.sets, inputs.coefficient, grid, epoch.tz_localize("UTC").to_pydatetime(), at_utc
            )
            if len(predicted):
                shift = predicted["predicted_shift_km"].to_numpy(dtype=float)
                b_source = str(predicted["b_source"].iloc[0])
        basis = ric_basis(np.where(covered[:, None], r_true, 1.0), np.where(covered[:, None], v_true, 1.0))
        delta = to_ric(basis, r_true - r_sgp4)
        for k, lead in enumerate(leads):
            t_k = pd.Timestamp(at[k])
            usable = bool(covered[k]) and int(err[k]) == 0
            through = bool(disturbed and epoch < disturbed[1] and t_k > disturbed[0])
            det = _overlaps(detected, epoch, t_k)
            pub = _overlaps(published_intervals, epoch - arc, t_k) if published_intervals is not None else None
            rows.append(
                {
                    "satellite": inputs.label,
                    "norad_id": inputs.norad_id,
                    "window": window.name,
                    "role": window.role,
                    "set_epoch": epoch,
                    "lead_h": float(lead),
                    "t": t_k,
                    "gap": not bool(covered[k]),
                    "sgp4_error": int(err[k]),
                    "manoeuvre": bool(pub) if pub is not None else det,
                    "manoeuvre_detected": det,
                    "manoeuvre_published": pub,
                    "manoeuvre_source": source,
                    "through_disturbed": through,
                    "radial_km": float(delta[k, 0]) if usable else np.nan,
                    "in_track_km": float(delta[k, 1]) if usable else np.nan,
                    "cross_km": float(delta[k, 2]) if usable else np.nan,
                    "distance_km": float(np.linalg.norm(r_true[k] - r_sgp4[k])) if usable else np.nan,
                    "sigma_r_km": float(sigma[k, 0]),
                    "sigma_i_km": float(sigma[k, 1]),
                    "sigma_c_km": float(sigma[k, 2]),
                    "covariance_source": inputs.covariance_source,
                    "storm_shift_km": float(shift[k]),
                    "b_source": b_source,
                }
            )
    frame = pd.DataFrame(rows)
    frame["in_track_corrected_km"] = frame["in_track_km"] - frame["storm_shift_km"]
    for c, sig in (("radial", "sigma_r_km"), ("in_track", "sigma_i_km"), ("cross", "sigma_c_km")):
        frame[f"{c}_inside_1s"] = frame[f"{c}_km"].abs() <= frame[sig]
        frame[f"{c}_inside_2s"] = frame[f"{c}_km"].abs() <= 2.0 * frame[sig]
    return frame


# --------------------------------------------------------------------------------------
# The four things, by lead bin


def _q(x: pd.Series, q: float) -> float | None:
    x = x.dropna()
    return float(np.quantile(x, q)) if len(x) else None


def _manoeuvre_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """How the exclusion was decided, how much it removed, and how the detection compares with the record."""
    live = frame[~frame["gap"]]
    excluded = live["manoeuvre"].astype(bool)
    out: dict[str, Any] = {
        "source": sorted(set(frame["manoeuvre_source"])) if "manoeuvre_source" in frame else ["detected"],
        "n_set_leads_excluded": int(excluded.sum()),
        "n_sets_excluded_any_lead": int(live.loc[excluded, "set_epoch"].nunique()),
        "n_sets_excluded_all_leads": int(live.groupby("set_epoch")["manoeuvre"].all().sum()) if len(live) else 0,
    }
    if "manoeuvre_detected" in frame:
        detected = live["manoeuvre_detected"].astype(bool)
        out["n_set_leads_detected"] = int(detected.sum())
        if "manoeuvre_published" in frame and live["manoeuvre_published"].notna().any():
            published = live["manoeuvre_published"].fillna(False).astype(bool)
            out["cross_check"] = {
                "both": int((published & detected).sum()),
                "record_only": int((published & ~detected).sum()),
                "detection_only": int((~published & detected).sum()),
                "neither": int((~published & ~detected).sum()),
            }
    return out


def summarise(
    trials: pd.DataFrame, *, tolerance_km: float = HORIZON_TOLERANCE_KM, quantile: float = HORIZON_QUANTILE
) -> dict[str, Any]:
    """The report's numbers: per window and lead, the distribution, the coverage, the storm term and the horizon.

    A trial is one element set; ``n`` at a lead is the number of sets whose propagation to that
    lead had truth, converged and spanned no manoeuvre. Trials excluded for a gap or a manoeuvre
    are counted beside the ones used.
    """
    out: dict[str, Any] = {"trial": "one element set; one residual per lead bin", "windows": {}}
    for window, frame in trials.groupby("window", sort=False):
        usable = frame[~frame["gap"] & ~frame["manoeuvre"] & (frame["sgp4_error"] == 0)]
        by_lead: dict[str, dict[str, Any]] = {}
        horizon: dict[str, Any] = {
            "task": f"in-track residual within {tolerance_km:g} km, the screening box's half-width, at the "
            f"{quantile:.0%} of trials",
            "tolerance_km": tolerance_km,
            "quantile": quantile,
            "last_lead_h_within": None,
            "first_lead_h_beyond": None,
        }
        for lead, g in usable.groupby("lead_h", sort=True):
            n = int(len(g))
            entry: dict[str, Any] = {
                "n": n,
                "n_sets": int(g["set_epoch"].nunique()),
                "n_satellites": int(g["satellite"].nunique()),
            }
            for c in ("radial", "in_track", "cross"):
                a = g[f"{c}_km"].abs()
                entry[c] = {
                    "median_km": _q(a, 0.5),
                    "p68_km": _q(a, 0.68),
                    "p95_km": _q(a, 0.95),
                    "max_km": float(a.max()) if n else None,
                    "median_signed_km": _q(g[f"{c}_km"], 0.5),
                    "inside_1_sigma": float(g[f"{c}_inside_1s"].mean()) if n else None,
                    "inside_2_sigma": float(g[f"{c}_inside_2s"].mean()) if n else None,
                    "median_sigma_km": _q(
                        g[{"radial": "sigma_r_km", "in_track": "sigma_i_km", "cross": "sigma_c_km"}[c]], 0.5
                    ),
                }
            with_term = g.dropna(subset=["storm_shift_km"])
            raw = with_term["in_track_km"].abs()
            corrected = with_term["in_track_corrected_km"].abs()
            entry["storm_term"] = {
                "n": int(len(with_term)),
                "median_abs_raw_km": _q(raw, 0.5),
                "median_abs_corrected_km": _q(corrected, 0.5),
                "median_abs_shift_km": _q(with_term["storm_shift_km"].abs(), 0.5),
                "improvement": (1.0 - _q(corrected, 0.5) / _q(raw, 0.5)) if len(with_term) and _q(raw, 0.5) else None,
                "share_of_trials_improved": float((corrected < raw).mean()) if len(with_term) else None,
            }
            through = g[g["through_disturbed"]]
            if len(through):
                a = through["in_track_km"].abs()
                entry["through_disturbed"] = {
                    "n": int(len(through)),
                    "in_track_median_km": _q(a, 0.5),
                    "in_track_p95_km": _q(a, 0.95),
                }
            by_lead[f"{lead:g}"] = entry
            p = entry["in_track"]["p95_km"] if quantile == 0.95 else _q(g["in_track_km"].abs(), quantile)
            if p is not None and p <= tolerance_km:
                horizon["last_lead_h_within"] = float(lead)
            elif p is not None and horizon["first_lead_h_beyond"] is None:
                horizon["first_lead_h_beyond"] = float(lead)
                horizon["quantile_km_there"] = p
        out["windows"][window] = {
            "role": str(frame["role"].iloc[0]),
            "n_sets": int(frame["set_epoch"].nunique()),
            "n_sets_by_satellite": {k: int(v) for k, v in frame.groupby("satellite")["set_epoch"].nunique().items()},
            "n_trial_leads": int(len(frame)),
            "n_excluded_gap": int(frame["gap"].sum()),
            "n_excluded_manoeuvre": int((frame["manoeuvre"] & ~frame["gap"]).sum()),
            "n_excluded_sgp4_error": int(((frame["sgp4_error"] != 0) & ~frame["gap"] & ~frame["manoeuvre"]).sum()),
            "manoeuvres": _manoeuvre_summary(frame),
            "covariance_sources": sorted(set(frame["covariance_source"])),
            "b_sources": sorted(set(frame["b_source"])),
            "by_lead_h": by_lead,
            "horizon": horizon,
        }
    return out


# --------------------------------------------------------------------------------------
# The record of sources


def _manoeuvre_source(records: dict[str, ThrusterRecord | None] | None, retrieved_at: datetime) -> dict[str, Any]:
    detection = (
        "the project's own detection -- a step in the orbit-mean semi-major axis of the precise orbit beyond "
        f"{MANOEUVRE_STEP_M:g} m and {MANOEUVRE_STEP_MAD_FACTOR:g} robust sigmas between consecutive orbits, and "
        "driftwatch.drag.ballistic.manoeuvre_intervals on the element sets"
    )
    have = {k: r for k, r in (records or {}).items() if r is not None}
    if not have:
        return {
            "source": "Manoeuvre intervals",
            "origin": f"NOT ESA's published record: {detection}. ESA's thruster record for these days is the "
            f"{SWARM_DYN_PRODUCT}, which was not available to this run",
            "retrieved_at": retrieved_at.isoformat(),
        }
    return {
        "source": "Manoeuvre intervals",
        "origin": f"ESA Swarm Level 1b spacecraft dynamics, {SWARM_DYN_PRODUCT}, retrieved from {SWARM_DISS_URL}: "
        "per-second on-times of the twelve thrusters (dt_thr) and the nominal force of the orbit-control "
        "thrusters that fired (f_thr); each day's header Maneuver_Information ids are kept beside it",
        "retrieved_at": retrieved_at.isoformat(),
        "derivation": "an orbit manoeuvre is a run of seconds with non-zero orbit-control force, merged across gaps "
        f"under {THRUST_GAP_S:g} s; a trial is excluded when one falls between {MANOEUVRE_ARC_HOURS:g} h before its "
        "element set's epoch and the lead's time; thruster on-time with no orbit-control force is attitude control, "
        f"counted and not excluded. Cross-check, deciding nothing: {detection}",
        "files": {
            k: {
                "n": len(r.files),
                "first": r.files[0] if r.files else None,
                "last": r.files[-1] if r.files else None,
                "days_missing": [d.isoformat() for d in r.days_missing],
                "n_manoeuvres": len(r.intervals),
                "manoeuvres": [[lo.isoformat(), hi.isoformat()] for lo, hi in r.intervals],
                "orbit_thrust_s": round(r.orbit_thrust_s, 2),
                "n_attitude_pulses": r.n_attitude_pulses,
                "header_manoeuvre_ids": sorted({i for ids in r.header_manoeuvre_ids.values() for i in ids}),
            }
            for k, r in have.items()
        },
        "missing_for": [k for k, r in (records or {}).items() if r is None],
    }


def sources_record(
    orbits: dict[str, PreciseOrbit],
    *,
    retrieved_at: datetime,
    weather_sources: Any = None,
    records: dict[str, ThrusterRecord | None] | None = None,
) -> list[dict[str, Any]]:
    import astropy
    import sgp4

    return [
        {
            "source": "ESA Swarm precise science orbits",
            "origin": f"{SWARM_DISS_URL}#{SWARM_POD_DIR.format(letter='x')} — product SW_OPER_SP3xCOM_2_, "
            f"reduced-dynamic, centre of mass, IGS20 (ITRF2020) frame, ten-second states with velocities, produced by "
            f"TU Delft (SPC_DUT); SP3-d files, one a day, in zips with an Earth Explorer header",
            "retrieved_at": retrieved_at.isoformat(),
            "files": {
                k: {
                    "n": len(o.files),
                    "first": o.files[0] if o.files else None,
                    "last": o.files[-1] if o.files else None,
                    "days_missing": [d.isoformat() for d in o.days_missing],
                }
                for k, o in orbits.items()
            },
            "derivation": "epochs converted from the files' GPS time to UTC (19 s to TAI, then astropy's "
            "leap-second table; 18 s in 2024); positions interpolated in the Earth-fixed frame by cubic Hermite on "
            "the product's own velocities, rotated to TEME with astropy (IERS Earth-orientation tables as bundled "
            "or cached by astropy); the inertial velocity for the RIC frame is the central difference of the "
            "rotated positions five seconds either side",
        },
        {
            "source": "Public element sets",
            "origin": "Space-Track gp_history for NORAD 39452 (Swarm A), 39451 (Swarm B), 39453 (Swarm C), through "
            "driftwatch's history backfill (data/cache/spacetrack/gp_history, data/history)",
            "retrieved_at": retrieved_at.isoformat(),
            "derivation": f"each set propagated with sgp4 {sgp4.__version__} (WGS72, mode i) to leads "
            f"{list(LEADS_HOURS)} hours from its own epoch; the empirical covariance fitted per satellite from the "
            f"{COVARIANCE_HISTORY_DAYS} days of sets before each window (driftwatch.risk.covariance, the model the "
            f"screening uses); the ballistic coefficient fitted from the {COEFFICIENT_HISTORY_DAYS} days before each "
            f"window (driftwatch.drag.ballistic)",
        },
        {
            "source": "Observed geomagnetic activity",
            "origin": "CelesTrak SW-All.csv (observed ap and Kp, F10.7), through driftwatch.weather; nothing forecast "
            "enters the benchmark",
            "retrieved_at": retrieved_at.isoformat(),
            "derivation": "the storm term (driftwatch.storm.term.object_shift via "
            "driftwatch.storm.validation.predicted_shifts) driven by NRLMSIS 2.1 with the observed ap over each "
            "trial's lead, from the trial set's own epoch, with the pre-window coefficient",
            "weather_sources": weather_sources,
        },
        _manoeuvre_source(records, retrieved_at),
        {
            "source": "Not used, noted for later",
            "origin": f"Swarm thermospheric density from POD and accelerometer, {SWARM_DENSITY_PRODUCT}: would "
            f"separate the atmosphere's error from the object's response in the storm-term comparison; not part of "
            f"this week",
        },
        {
            "source": "Software",
            "origin": f"driftwatch (this repository), sgp4 {sgp4.__version__}, astropy {astropy.__version__}, numpy "
            f"{np.__version__}, pandas {pd.__version__}",
        },
    ]


# --------------------------------------------------------------------------------------
# The page


def _manoeuvre_sentence(m: dict[str, Any]) -> str:
    source = ", ".join(m.get("source", ["detected"]))
    text = (
        f"Manoeuvres: exclusion by `{source}`; {m.get('n_set_leads_excluded', 0)} set-lead pairs excluded "
        f"({m.get('n_sets_excluded_any_lead', 0)} sets at some lead, {m.get('n_sets_excluded_all_leads', 0)} at "
        "every lead)"
    )
    if "n_set_leads_detected" in m:
        text += f"; the project's own detection flagged {m['n_set_leads_detected']}"
    cc = m.get("cross_check")
    if cc:
        text += (
            f" -- record and detection agree on {cc['both']} excluded and {cc['neither']} kept; record only "
            f"{cc['record_only']}, detection only {cc['detection_only']}"
        )
    return text + "."


def to_markdown(
    summary: dict[str, Any], sources: list[dict[str, Any]], windows: dict[str, BenchmarkWindow], *, built_at: datetime
) -> str:
    """The benchmark as a markdown page for the docs, numbers from ``summary`` and nothing else."""
    lines = [
        "# Calibration against precise orbits: Swarm A, B and C",
        "",
        f"Written by `driftwatch validate swarm` on {built_at.date().isoformat()}. Every number here is computed "
        "from the per-trial file beside `swarm_benchmark.json`; the reasoning and the caveats are in "
        '`docs/methods.md`, "Uncertainty and probability", and on the findings page.',
        "",
        "**A trial is one element set.** For every public element set issued in a window, the set is propagated "
        "with SGP4 to each lead and compared with ESA's precise science orbit at that instant, in the "
        "satellite's radial, in-track, cross-track frame; one residual per set per lead, never one per "
        "timestamp, because the residuals along one set's propagation are not independent. `n` at a lead is "
        "the number of sets whose propagation had truth there, converged, and spanned no manoeuvre (from ESA's "
        "thruster record where it was read; the project's own detection otherwise).",
        "",
        "## Windows",
        "",
        "| Window | Role | Element sets issued | Truth needed to | Disturbed interval | Note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, w in windows.items():
        d = f"{w.disturbed[0]:%Y-%m-%d %H:%M} to {w.disturbed[1]:%Y-%m-%d %H:%M}" if w.disturbed else "none"
        lines.append(
            f"| {name} | {w.role} | {w.sets_from:%Y-%m-%d} to {w.sets_to:%Y-%m-%d} | {w.truth_to:%Y-%m-%d} | {d} | "
            f"{w.note} |"
        )
    lines += [
        "",
        "The held-out window was held out: the covariance and the coefficient used on it are fitted from the "
        "history before it, exactly as on the other two, and no threshold in this module was chosen by "
        "looking at its result.",
        "",
    ]
    for name, w in summary["windows"].items():
        lines += [
            f"## {name} ({w['role']})",
            "",
            f"{w['n_sets']} element sets ({', '.join(f'{k}: {v}' for k, v in w['n_sets_by_satellite'].items())}), "
            f"{w['n_trial_leads']} set-lead pairs; excluded {w['n_excluded_gap']} for a truth gap, "
            f"{w['n_excluded_manoeuvre']} for a manoeuvre, {w['n_excluded_sgp4_error']} for an SGP4 error. "
            f"Covariance source: {', '.join(w['covariance_sources'])}; coefficient source: "
            f"{', '.join(w['b_sources'])}.",
            "",
            _manoeuvre_sentence(w.get("manoeuvres") or {}),
            "",
            "### The residual distribution, absolute, km",
            "",
            "| Lead | n | in-track median | in-track p68 | in-track p95 | in-track max | radial median | radial p95 | "
            "cross median | cross p95 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for lead, e in w["by_lead_h"].items():
            i, r, c = e["in_track"], e["radial"], e["cross"]
            lines.append(
                f"| {float(lead):g} h | {e['n']} | {i['median_km']:.2f} | {i['p68_km']:.2f} | {i['p95_km']:.2f} | "
                f"{i['max_km']:.1f} "
                f"| {r['median_km']:.3f} | {r['p95_km']:.3f} | {c['median_km']:.3f} | {c['p95_km']:.3f} |"
            )
        lines += [
            "",
            "### Coverage of the empirical covariance",
            "",
            "The fraction of residuals inside one and two sigma of the covariance the screening would have "
            "carried for the set, per component, against the 68 and 95 per cent a Gaussian claims.",
            "",
            "| Lead | n | in-track sigma (median) | inside 1σ | inside 2σ | radial 1σ | radial 2σ | cross 1σ | cross "
            "2σ |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for lead, e in w["by_lead_h"].items():
            i, r, c = e["in_track"], e["radial"], e["cross"]
            lines.append(
                f"| {float(lead):g} h | {e['n']} | {i['median_sigma_km']:.2f} km | {i['inside_1_sigma']:.0%} | "
                f"{i['inside_2_sigma']:.0%} "
                f"| {r['inside_1_sigma']:.0%} | {r['inside_2_sigma']:.0%} | {c['inside_1_sigma']:.0%} | "
                f"{c['inside_2_sigma']:.0%} |"
            )
        lines += [
            "",
            "### The storm term with the observed ap",
            "",
            "The in-track residual with SGP4 alone against the residual after the storm term's shift, driven "
            "by the observed ap and the pre-window coefficient, is subtracted; a positive improvement means "
            "the term brought the prediction closer to the truth.",
            "",
            "| Lead | n | median \\|residual\\| raw | median \\|residual\\| corrected | median \\|shift\\| | "
            "improvement | trials improved |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for lead, e in w["by_lead_h"].items():
            s = e["storm_term"]
            if not s["n"]:
                lines.append(f"| {float(lead):g} h | 0 | | | | | |")
                continue
            imp = f"{s['improvement']:+.0%}" if s["improvement"] is not None else "—"
            lines.append(
                f"| {float(lead):g} h | {s['n']} | {s['median_abs_raw_km']:.2f} km | "
                f"{s['median_abs_corrected_km']:.2f} km "
                f"| {s['median_abs_shift_km']:.2f} km | {imp} | {s['share_of_trials_improved']:.0%} |"
            )
        h = w["horizon"]
        lines += [
            "",
            "### The horizon",
            "",
            f"Task: {h['task']}. ",
        ]
        if h["last_lead_h_within"] is not None and h["first_lead_h_beyond"] is not None:
            lines[-1] += (
                f"The residual stays inside the tolerance through **{h['last_lead_h_within']:g} hours** of lead and is "
                f"beyond it at **{h['first_lead_h_beyond']:g} hours** ({h['quantile_km_there']:.1f} km at the 95th "
                f"percentile)."
            )
        elif h["last_lead_h_within"] is not None:
            lines[-1] += (
                f"The residual stays inside the tolerance at every lead measured, through {h['last_lead_h_within']:g} "
                f"hours."
            )
        elif h["first_lead_h_beyond"] is not None:
            lines[-1] += (
                f"The residual is beyond the tolerance at the shortest lead measured, {h['first_lead_h_beyond']:g} "
                f"hours ({h['quantile_km_there']:.1f} km)."
            )
        lines.append("")
    lines += ["## Sources, with origin and derivation", ""]
    for s in sources:
        lines.append(f"- **{s['source']}.** {s['origin']}")
        if s.get("retrieved_at"):
            lines[-1] = lines[-1].rstrip(".") + f". Retrieved {s['retrieved_at'][:10]}."
        if s.get("derivation"):
            lines[-1] += f" Derivation: {s['derivation']}."
        if s.get("files"):
            for k, f in s["files"].items():
                gaps = f"; days missing: {', '.join(f['days_missing'])}" if f["days_missing"] else "; no days missing"
                extra = ""
                if "n_manoeuvres" in f:
                    burns = "; ".join(f"{lo[:16]} to {hi[:16]}" for lo, hi in f["manoeuvres"]) or "none"
                    extra = (
                        f"; {f['n_manoeuvres']} orbit manoeuvre(s): {burns}; {f['orbit_thrust_s']:g} s of "
                        f"orbit-control thrust; {f['n_attitude_pulses']} attitude pulses"
                    )
                lines.append(f"  - Swarm {k}: {f['n']} daily files, {f['first']} to {f['last']}{gaps}{extra}.")
        if s.get("missing_for"):
            lines.append(f"  - No record for: {', '.join(s['missing_for'])} (detection decided there).")
    lines.append("")
    return "\n".join(lines)
