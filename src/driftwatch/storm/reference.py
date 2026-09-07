"""Reference orbits beyond Swarm: every public reconstructed orbit obtainable without an account, and the missions
that were asked for but are not.

The calibration benchmark (``precise.py``) compared public element sets with ESA's precise orbits
for three Swarm satellites at 460 to 506 km. This module extends it to the other missions whose
reconstructed orbits a public server hands out anonymously, keeps the same windows and the same
rule that nothing is tuned on the held-out ones, and adds a fourth, disturbed window. Each
mission's truth is read into the same :class:`~driftwatch.storm.precise.PreciseOrbit` and scored
by the same :func:`~driftwatch.storm.precise.satellite_trials`, one trial per element set.

The products, all read on 7 September 2026:

* **CNES/SSALTO precise orbit ephemerides for the DORIS satellites**, through the International
  DORIS Service's data centre at IGN (``ftp://doris.ign.fr/pub/doris/products/orbits/ssa/``,
  anonymous FTP): SP3 files of about ten days, ITRF, TAI, one-minute states with velocities, the
  POE-F and POE-G standards -- Jason-3, Sentinel-3A, Sentinel-3B, Sentinel-6A, CryoSat-2, SARAL,
  HY-2C, HY-2D and SWOT.
* **Copernicus precise orbit ephemerides for Sentinel-1A**, mirrored anonymously by ESA's STEP
  auxiliary-data server (``step.esa.int/auxdata/orbits/Sentinel-1/POEORB/S1A/``): Earth Explorer
  XML, Earth-fixed, UTC, ten-second states with velocities, one file a day covering 26 hours.
* **GRACE-FO Level-1B navigation (GNV1B) from JPL, release 04**, served anonymously by GFZ's
  ISDC (``isdc-data.gfz.de/grace-fo/Level-1B/JPL/INSTRUMENT/RL04/``) in daily archives that also
  carry the thruster record (THR1B), which separates the two orbit-control thrusters from the
  twelve attitude-control ones and is the published manoeuvre record used here, as ESA's is for
  Swarm.
* **ESA's Swarm products**, as before.
* **ILRS laser-ranging normal points** from the EUROLAS Data Center for every mission with a
  retroreflector, as an independent second truth (``slr.py``).

Asked for and not obtainable without an account, said rather than substituted: see
:data:`NOT_COVERED`.

Manoeuvres. Where a mission publishes a thruster record that a public server carries (Swarm,
GRACE-FO) it decides the exclusion, and the project's own detection is a cross-check. For the
CNES, Copernicus and SLR-only missions no public manoeuvre record was found on an anonymous
server, so the detection decides -- a step in the orbit-mean semi-major axis of the precise orbit,
and the jump detector on the element sets -- and every table says so.
"""

from __future__ import annotations

import ftplib
import io
import json
import logging
import re
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.orbit.time import parse_utc
from driftwatch.storm import precise
from driftwatch.storm.precise import BenchmarkWindow, PreciseOrbit, ThrusterRecord

log = logging.getLogger(__name__)

TRUTH_CNES = "ids-cnes-poe"
TRUTH_S1 = "esa-step-poeorb"
TRUTH_GRACEFO = "gfz-jpl-gnv1b"
TRUTH_SWARM = "esa-swarm-sp3"
TRUTH_NONE = "none"

MANOEUVRES_ESA = "esa-record"
MANOEUVRES_GRACEFO = "gracefo-thr1b"
MANOEUVRES_DETECTION = "detection"


@dataclass(frozen=True)
class Mission:
    """One spacecraft in the reference expansion: where its truth comes from, and what qualifies it."""

    key: str
    name: str
    norad_id: int
    altitude_km: float  # nominal mean altitude in 2024, for the band label; the trials carry the measured one
    truth: str
    truth_code: str
    slr: str | None
    manoeuvres: str
    note: str = ""


MISSIONS: dict[str, Mission] = {
    "swarm-a": Mission("swarm-a", "Swarm A", 39452, 462.0, TRUTH_SWARM, "A", "swarma", MANOEUVRES_ESA),
    "swarm-b": Mission("swarm-b", "Swarm B", 39451, 503.0, TRUTH_SWARM, "B", "swarmb", MANOEUVRES_ESA),
    "swarm-c": Mission("swarm-c", "Swarm C", 39453, 462.0, TRUTH_SWARM, "C", "swarmc", MANOEUVRES_ESA),
    "gracefo-c": Mission(
        "gracefo-c", "GRACE-FO 1 (C)", 43476, 490.0, TRUTH_GRACEFO, "C", "gracefo1", MANOEUVRES_GRACEFO
    ),
    "gracefo-d": Mission(
        "gracefo-d", "GRACE-FO 2 (D)", 43477, 490.0, TRUTH_GRACEFO, "D", "gracefo2", MANOEUVRES_GRACEFO
    ),
    "sentinel-1a": Mission("sentinel-1a", "Sentinel-1A", 39634, 693.0, TRUTH_S1, "S1A", None, MANOEUVRES_DETECTION),
    "cryosat-2": Mission("cryosat-2", "CryoSat-2", 36508, 717.0, TRUTH_CNES, "cs2", "cryosat2", MANOEUVRES_DETECTION),
    "saral": Mission("saral", "SARAL", 39086, 781.0, TRUTH_CNES, "srl", "saral", MANOEUVRES_DETECTION),
    "sentinel-3a": Mission(
        "sentinel-3a", "Sentinel-3A", 41335, 814.0, TRUTH_CNES, "s3a", "sentinel3a", MANOEUVRES_DETECTION
    ),
    "sentinel-3b": Mission(
        "sentinel-3b", "Sentinel-3B", 43437, 814.0, TRUTH_CNES, "s3b", "sentinel3b", MANOEUVRES_DETECTION
    ),
    "swot": Mission("swot", "SWOT", 54754, 891.0, TRUTH_CNES, "swo", "swot", MANOEUVRES_DETECTION),
    "hy-2c": Mission("hy-2c", "HY-2C", 46469, 957.0, TRUTH_CNES, "h2c", "hy2c", MANOEUVRES_DETECTION),
    "hy-2d": Mission("hy-2d", "HY-2D", 48621, 957.0, TRUTH_CNES, "h2d", "hy2d", MANOEUVRES_DETECTION),
    "jason-3": Mission(
        "jason-3",
        "Jason-3",
        41240,
        1336.0,
        TRUTH_CNES,
        "ja3",
        "jason3",
        MANOEUVRES_DETECTION,
        "at 1,336 km, just above the 1,300 km asked for; kept as the top of the range",
    ),
    "sentinel-6a": Mission(
        "sentinel-6a",
        "Sentinel-6A",
        46984,
        1336.0,
        TRUTH_CNES,
        "s6a",
        "sentinel6a",
        MANOEUVRES_DETECTION,
        "Jason-3's orbit; the same note",
    ),
    # Laser ranging only: no reconstructed orbit on an anonymous server for 2024.
    "terrasar-x": Mission(
        "terrasar-x",
        "TerraSAR-X",
        31698,
        514.0,
        TRUTH_NONE,
        "",
        "terrasarx",
        MANOEUVRES_DETECTION,
        "GFZ's ISDC serves TerraSAR-X rapid science orbits anonymously only through 2020; laser ranging is the truth",
    ),
    "tandem-x": Mission(
        "tandem-x",
        "TanDEM-X",
        36605,
        514.0,
        TRUTH_NONE,
        "",
        "tandemx",
        MANOEUVRES_DETECTION,
        "as TerraSAR-X",
    ),
    "icesat-2": Mission(
        "icesat-2",
        "ICESat-2",
        43613,
        496.0,
        TRUTH_NONE,
        "",
        "icesat2",
        MANOEUVRES_DETECTION,
        "the precise orbit is inside the ATL03 product at NSIDC behind an Earthdata login; laser ranging is the truth",
    ),
}

NOT_COVERED: dict[str, str] = {
    "Sentinel-2A and Sentinel-2B": "the Copernicus precise orbit products are served through the Copernicus Data "
    "Space Ecosystem, which needs a registered account; no anonymous mirror carries Sentinel-2 orbits, and "
    "Sentinel-2 carries no laser retroreflector, so there is no truth for it here",
    "ICESat-2 (reconstructed orbit)": "the precise orbit determination product is distributed inside ATL03 at NSIDC "
    "behind an Earthdata login; the laser-ranging normal points are public and are the truth used",
    "TerraSAR-X and TanDEM-X (reconstructed orbit)": "GFZ's ISDC serves the rapid science orbits anonymously for 2010 "
    "to 2020 and nothing for 2024; the laser-ranging normal points are public and are the truth used",
    "GOCE": "the precise science orbits (SST_PSO_2, 2009 to 2013) are behind ESA's EO-SSO login on the GOCE online "
    "dissemination service; not obtainable anonymously, so not substituted",
    "CHAMP": "GFZ's ISDC serves the 2000 to 2010 rapid science orbits anonymously and Space-Track's element-set "
    "history reaches back to 2000, so a CHAMP benchmark is possible on CHAMP's own storm windows; it is not part "
    "of this fortnight and is recorded as a candidate",
}

# Altitude bands for the horizon table. The lower edge of the first is the benchmark's own.
ALTITUDE_BANDS: tuple[tuple[float, float, str], ...] = (
    (400.0, 600.0, "400-600 km"),
    (600.0, 750.0, "600-750 km"),
    (750.0, 850.0, "750-850 km"),
    (850.0, 1000.0, "850-1000 km"),
    (1000.0, 1400.0, "1000-1400 km"),
)


def altitude_band_label(altitude_km: float) -> str:
    for lo, hi, label in ALTITUDE_BANDS:
        if lo <= altitude_km < hi:
            return label
    return "outside the bands"


# The fourth window. Kp reached 8- on 12 August 2024 (ap 207 in the 12:00 to 15:00 interval); the
# sets issued from four days before the onset to three after are the trials, held out like October.
AUGUST = BenchmarkWindow(
    "august",
    "held-out",
    parse_utc("2024-08-08T00:00:00Z"),
    parse_utc("2024-08-15T00:00:00Z"),
    (parse_utc("2024-08-12T00:00:00Z"), parse_utc("2024-08-13T12:00:00Z")),
    "the 12 August 2024 storm (Kp 8-), the further disturbed window of the reference expansion; held out like "
    "October, nothing was chosen by looking at it",
)
WINDOWS: tuple[BenchmarkWindow, ...] = (*precise.WINDOWS, AUGUST)


class _Borrowed:
    """A context manager around a client that belongs to the caller: yields it and never closes it."""

    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def __enter__(self) -> httpx.Client:
        return self.client

    def __exit__(self, *exc: object) -> None:
        return None


def _client(client: httpx.Client | None) -> httpx.Client | _Borrowed:
    if client is not None:
        return _Borrowed(client)
    return httpx.Client(timeout=300.0, headers={"User-Agent": config.USER_AGENT}, follow_redirects=True)


def _days(start: date, end: date) -> list[date]:
    out = []
    day = start
    while day <= end:
        out.append(day)
        day += timedelta(days=1)
    return out


def _days_missing(table: pd.DataFrame, start: date, end: date) -> list[date]:
    """Days in ``[start, end]`` with no sample in the table."""
    if not len(table):
        return _days(start, end)
    have = set(pd.to_datetime(table["t"]).dt.date.unique())
    return [d for d in _days(start, end) if d not in have]


# --------------------------------------------------------------------------------------
# CNES precise orbit ephemerides through the IDS data centre (anonymous FTP)

IDS_FTP_HOST = "doris.ign.fr"
IDS_FTP_DIR = "/pub/doris/products/orbits/ssa"
IDS_SOURCE = (
    "CNES/SSALTO precise orbit ephemerides (POE-F and POE-G standards) for the DORIS satellites, from the "
    "International DORIS Service data centre at IGN, ftp://doris.ign.fr/pub/doris/products/orbits/ssa/ "
    "(anonymous FTP): SP3, ITRF, TAI, one-minute states with velocities, files of about ten days"
)
_IDS_NAME = re.compile(
    r"^ssa(?P<sat>[a-z0-9]{3})(?P<vv>\d{2})\.b(?P<b>\d{5})\.e(?P<e>\d{5})\.(?P<flag>[A-Z_]{3})\.sp3\.(?P<n>\d{3})\.Z$"
)


def _yyddd(text: str) -> date:
    y = int(text[:2])
    y += 2000 if y < 80 else 1900
    return date(y, 1, 1) + timedelta(days=int(text[2:]) - 1)


def ids_listing(
    sat: str, *, cache_dir: Path = config.CACHE_DIR, offline: bool = False, ftp: ftplib.FTP | None = None
) -> list[str]:
    """The file names in the satellite's IDS orbit folder, cached for a day."""
    path = Path(cache_dir) / "ids" / sat / "listing.json"
    if path.exists() and (
        offline or (datetime.now(UTC) - datetime.fromtimestamp(path.stat().st_mtime, UTC)) < timedelta(days=1)
    ):
        return json.loads(path.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError(f"no cached IDS listing for {sat} at {path}")
    own = ftp is None
    ftp = ftp or _ids_connect()
    try:
        names = [n.rsplit("/", 1)[-1] for n in ftp.nlst(f"{IDS_FTP_DIR}/{sat}")]
    finally:
        if own:
            ftp.quit()
    names = sorted(n for n in names if _IDS_NAME.match(n))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(names), encoding="utf-8")
    return names


def _ids_connect() -> ftplib.FTP:
    ftp = ftplib.FTP(IDS_FTP_HOST, timeout=120)
    ftp.login(user="anonymous", passwd="driftwatch-reference-benchmark@example.invalid")
    return ftp


def ids_files_for(names: list[str], start: date, end: date) -> list[str]:
    """The files whose span overlaps ``[start, end]``, one per span, the highest version and issue of each."""
    best: dict[tuple[date, date], tuple[int, int, str]] = {}
    for n in names:
        m = _IDS_NAME.match(n)
        if m is None:
            continue
        b, e = _yyddd(m.group("b")), _yyddd(m.group("e"))
        if e < start or b > end:
            continue
        rank = (int(m.group("vv")), int(m.group("n")))
        if (b, e) not in best or rank > best[(b, e)][:2]:
            best[(b, e)] = (*rank, n)
    return [best[k][2] for k in sorted(best)]


def fetch_ids_file(
    sat: str, name: str, *, cache_dir: Path = config.CACHE_DIR, offline: bool = False, ftp: ftplib.FTP | None = None
) -> Path | None:
    dest = Path(cache_dir) / "ids" / sat / name
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    if offline:
        return None
    own = ftp is None
    ftp = ftp or _ids_connect()
    try:
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {IDS_FTP_DIR}/{sat}/{name}", buf.write)
    finally:
        if own:
            ftp.quit()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(buf.getvalue())
    log.info("Fetched %s (%d bytes)", name, len(buf.getvalue()))
    return dest


def read_ids_sp3(path: Path) -> pd.DataFrame:
    """One ``.Z`` (LZW) SP3 file as a table in UTC; the file's own TAI epochs are converted."""
    import unlzw3

    text = unlzw3.unlzw(Path(path).read_bytes()).decode("ascii", "replace")
    return precise.parse_sp3(text)


def load_ids_orbit(
    mission: Mission, start: date, end: date, *, cache_dir: Path = config.CACHE_DIR, offline: bool = False
) -> PreciseOrbit:
    """The CNES precise orbit for a DORIS mission over ``[start, end]``, files joined, later files winning overlaps."""
    names = ids_listing(mission.truth_code, cache_dir=cache_dir, offline=offline)
    wanted = ids_files_for(names, start, end)
    frames: list[pd.DataFrame] = []
    files: list[str] = []
    ftp = None if offline else _ids_connect()
    try:
        for name in wanted:
            path = fetch_ids_file(mission.truth_code, name, cache_dir=cache_dir, offline=offline, ftp=ftp)
            if path is None:
                continue
            frames.append(read_ids_sp3(path))
            files.append(name)
    finally:
        if ftp is not None:
            ftp.quit()
    lo = pd.Timestamp(datetime(start.year, start.month, start.day))
    hi = pd.Timestamp(datetime(end.year, end.month, end.day)) + pd.Timedelta(days=1)
    table = (
        pd.concat(frames, ignore_index=True).sort_values("t").drop_duplicates("t", keep="last").reset_index(drop=True)
        if frames
        else precise.parse_sp3("")
    )
    table = table[(table["t"] >= lo) & (table["t"] < hi)].reset_index(drop=True)
    missing = _days_missing(table, start, end)
    if missing:
        log.warning("%s: no CNES orbit for %d day(s): %s", mission.name, len(missing), [d.isoformat() for d in missing])
    return PreciseOrbit(mission.truth_code, mission.norad_id, table, missing, files, frame="ITRF")


# --------------------------------------------------------------------------------------
# Sentinel-1A precise orbit ephemerides (ESA STEP mirror, anonymous HTTPS)

S1_BASE_URL = "https://step.esa.int/auxdata/orbits/Sentinel-1/POEORB/S1A/"
S1_SOURCE = (
    "Copernicus Sentinel-1A precise orbit ephemerides (AUX_POEORB, produced by the Copernicus POD service), mirrored "
    "at https://step.esa.int/auxdata/orbits/Sentinel-1/POEORB/S1A/ (anonymous HTTPS): Earth Explorer XML, "
    "Earth-fixed, UTC, ten-second states with velocities, one 26-hour file a day"
)
_S1_NAME = re.compile(r"S1A_OPER_AUX_POEORB_OPOD_(\d{8}T\d{6})_V(\d{8})T(\d{6})_(\d{8}T\d{6})\.EOF\.zip")
_OSV = re.compile(
    r"<OSV>.*?<UTC>UTC=([^<]+)</UTC>.*?<X unit=\"m\">([^<]+)</X>\s*<Y unit=\"m\">([^<]+)</Y>"
    r"\s*<Z unit=\"m\">([^<]+)</Z>\s*<VX unit=\"m/s\">([^<]+)</VX>\s*<VY unit=\"m/s\">([^<]+)</VY>"
    r"\s*<VZ unit=\"m/s\">([^<]+)</VZ>.*?</OSV>",
    re.S,
)


def s1_listing(
    year: int,
    month: int,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> list[str]:
    path = Path(cache_dir) / "sentinel1" / f"listing_{year:04d}{month:02d}.json"
    if path.exists() and (
        offline or (datetime.now(UTC) - datetime.fromtimestamp(path.stat().st_mtime, UTC)) < timedelta(days=1)
    ):
        return json.loads(path.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError(f"no cached Sentinel-1 listing at {path}")
    with _client(client) as c:
        r = c.get(f"{S1_BASE_URL}{year:04d}/{month:02d}/")
        r.raise_for_status()
    names = sorted(set(re.findall(r'href="(S1A_OPER_AUX_POEORB[^"]+\.EOF\.zip)"', r.text)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(names), encoding="utf-8")
    return names


def s1_file_for_day(names: list[str], day: date) -> str | None:
    """The newest file whose validity starts the evening before ``day``.

    Each file covers 22:59:42 the day before to 00:59:42 the day after.
    """
    stamp = (day - timedelta(days=1)).strftime("%Y%m%d")
    hits = [(m.group(1), n) for n in names if (m := _S1_NAME.match(n)) and m.group(2) == stamp]
    return max(hits)[1] if hits else None


def parse_eof(text: str) -> pd.DataFrame:
    """The orbit state vectors of an Earth Explorer POEORB file: UTC, km and km/s, Earth-fixed."""
    rows = [
        (
            pd.Timestamp(t.strip()),
            float(x) / 1000.0,
            float(y) / 1000.0,
            float(z) / 1000.0,
            float(vx) / 1000.0,
            float(vy) / 1000.0,
            float(vz) / 1000.0,
        )
        for t, x, y, z, vx, vy, vz in _OSV.findall(text)
    ]
    frame = pd.DataFrame(rows, columns=["t", "x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"])
    frame["t"] = pd.to_datetime(frame["t"]).astype("datetime64[us]")
    return frame.sort_values("t").drop_duplicates("t").reset_index(drop=True)


def load_s1_orbit(
    mission: Mission,
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> PreciseOrbit:
    frames: list[pd.DataFrame] = []
    files: list[str] = []
    missing: list[date] = []
    folder = Path(cache_dir) / "sentinel1"
    with _client(client) as c:
        for day in _days(start, end):
            try:
                names = s1_listing(day.year, day.month, cache_dir=cache_dir, offline=offline, client=c)
            except FileNotFoundError:
                names = []
            name = s1_file_for_day(names, day)
            if name is None and not offline:
                # The file for the first of a month sits in the previous month's folder by validity.
                prev = day - timedelta(days=1)
                names = s1_listing(prev.year, prev.month, cache_dir=cache_dir, offline=offline, client=c)
                name = s1_file_for_day(names, day)
            if name is None:
                missing.append(day)
                continue
            dest = folder / name
            if not dest.exists():
                if offline:
                    missing.append(day)
                    continue
                m = _S1_NAME.match(name)
                sub = f"{m.group(2)[:4]}/{m.group(2)[4:6]}/" if m else ""
                r = c.get(f"{S1_BASE_URL}{sub}{name}")
                if r.status_code == 404 and m:
                    nxt = datetime.strptime(m.group(2), "%Y%m%d") + timedelta(days=1)
                    r = c.get(f"{S1_BASE_URL}{nxt:%Y/%m/}{name}")
                r.raise_for_status()
                folder.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                log.info("Fetched %s (%d bytes)", name, len(r.content))
            with zipfile.ZipFile(dest) as z:
                inner = next(n for n in z.namelist() if n.upper().endswith(".EOF"))
                frames.append(parse_eof(z.read(inner).decode("utf-8", "replace")))
            files.append(name)
    table = (
        pd.concat(frames, ignore_index=True).sort_values("t").drop_duplicates("t", keep="last").reset_index(drop=True)
        if frames
        else precise.parse_sp3("")
    )
    if missing:
        log.warning("Sentinel-1A: no orbit file for %d day(s): %s", len(missing), [d.isoformat() for d in missing])
    return PreciseOrbit(mission.truth_code, mission.norad_id, table, missing, files, frame="ITRF")


# --------------------------------------------------------------------------------------
# GRACE-FO Level-1B navigation and thruster records (GFZ ISDC, anonymous HTTPS)

GFZ_BASE_URL = "https://isdc-data.gfz.de/grace-fo/Level-1B/JPL/INSTRUMENT/RL04/"
GRACEFO_SOURCE = (
    "GRACE-FO Level-1B release 04 from JPL, served by GFZ's ISDC at "
    "https://isdc-data.gfz.de/grace-fo/Level-1B/JPL/INSTRUMENT/RL04/ (anonymous HTTPS), daily archives: GNV1B "
    "(navigation: reduced-dynamic orbit, Earth-fixed ITRF, one-second states with velocities, GPS time) and THR1B "
    "(thruster activation: on-times of the twelve attitude-control and the two orbit-control thrusters)"
)
GPS_EPOCH_2000 = pd.Timestamp("2000-01-01T12:00:00")
GNV_STEP_S = 10


def _gps_seconds_to_utc(seconds: pd.Series) -> pd.Series:
    """GPS seconds past 2000-01-01 12:00:00 GPS as UTC, through the leap-second table."""
    gps = pd.Series(
        (GPS_EPOCH_2000 + pd.to_timedelta(seconds.to_numpy(dtype=float), unit="s")).astype("datetime64[us]")
    )
    return precise.sp3_epochs_to_utc(gps, "GPS")


def parse_gnv1b(text: str, *, step_s: int = GNV_STEP_S) -> pd.DataFrame:
    """A GNV1B text product as a table in UTC, km and km/s, one state every ``step_s`` seconds."""
    body = text.split("# End of YAML header", 1)[-1]
    rows = []
    for line in body.splitlines():
        f = line.split()
        if len(f) < 12 or not f[0].isdigit():
            continue
        s = int(f[0])
        if s % step_s:
            continue
        rows.append((s, float(f[3]), float(f[4]), float(f[5]), float(f[9]), float(f[10]), float(f[11])))
    frame = pd.DataFrame(rows, columns=["gps_s", "x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"])
    for c in ("x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"):
        frame[c] = frame[c] / 1000.0
    frame["t"] = _gps_seconds_to_utc(frame["gps_s"]) if len(frame) else pd.Series(dtype="datetime64[us]")
    return frame[["t", "x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms"]].sort_values("t").reset_index(drop=True)


def parse_thr1b(text: str) -> pd.DataFrame:
    """A THR1B text product: per record, the UTC time tag and the on-times (ms) of the orbit-control and attitude
    thrusters."""
    body = text.split("# End of YAML header", 1)[-1]
    rows = []
    for line in body.splitlines():
        f = line.split()
        if len(f) < 32 or not f[0].isdigit():
            continue
        seconds = int(f[0]) + int(f[1]) / 1e6
        attitude = sum(float(v) for v in f[18:30])
        rows.append((seconds, float(f[30]), float(f[31]), attitude))
    frame = pd.DataFrame(rows, columns=["gps_s", "orbit_1_ms", "orbit_2_ms", "attitude_ms"])
    frame["t"] = _gps_seconds_to_utc(frame["gps_s"]) if len(frame) else pd.Series(dtype="datetime64[us]")
    return frame[["t", "orbit_1_ms", "orbit_2_ms", "attitude_ms"]].sort_values("t").reset_index(drop=True)


def gracefo_day_files(
    day: date, *, cache_dir: Path = config.CACHE_DIR, offline: bool = False, client: httpx.Client | None = None
) -> dict[str, Path]:
    """The parsed GNV1B and THR1B tables for both satellites on one day, as cached parquet files.

    The daily archive is 144 MB; it is fetched once, the four small products are parsed into
    parquet, and the archive is deleted. Keys are ``GNV1B_C``, ``GNV1B_D``, ``THR1B_C``, ``THR1B_D``.
    """
    folder = Path(cache_dir) / "gracefo"
    keys = {
        f"{kind}_{sat}": folder / f"{kind}_{day:%Y-%m-%d}_{sat}.parquet" for kind in ("GNV1B", "THR1B") for sat in "CD"
    }
    marker = folder / f"gracefo_1B_{day:%Y-%m-%d}.missing"
    if all(p.exists() for p in keys.values()):
        return keys
    if marker.exists() or offline:
        return {k: p for k, p in keys.items() if p.exists()}
    name = f"gracefo_1B_{day:%Y-%m-%d}_RL04.ascii.noLRI.tgz"
    url = f"{GFZ_BASE_URL}{day.year}/{name}"
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / name
    with _client(client) as c:
        with c.stream("GET", url) as r:
            if r.status_code == 404:
                marker.write_text("", encoding="utf-8")
                return {}
            r.raise_for_status()
            with archive.open("wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
    log.info("Fetched %s (%d bytes)", name, archive.stat().st_size)
    try:
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                base = member.name.rsplit("/", 1)[-1]
                m = re.match(r"(GNV1B|THR1B)_(\d{4}-\d{2}-\d{2})_([CD])_04\.txt$", base)
                if not m:
                    continue
                text = tar.extractfile(member).read().decode("ascii", "replace")
                table = parse_gnv1b(text) if m.group(1) == "GNV1B" else parse_thr1b(text)
                table.to_parquet(keys[f"{m.group(1)}_{m.group(3)}"], index=False)
    finally:
        archive.unlink(missing_ok=True)
    return {k: p for k, p in keys.items() if p.exists()}


def load_gracefo_orbit(
    mission: Mission,
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> tuple[PreciseOrbit, ThrusterRecord]:
    """The GNV1B orbit and the THR1B manoeuvre record for one GRACE-FO satellite over ``[start, end]``."""
    frames: list[pd.DataFrame] = []
    thr: list[pd.DataFrame] = []
    files: list[str] = []
    missing: list[date] = []
    with _client(client) as c:
        for day in _days(start, end):
            paths = gracefo_day_files(day, cache_dir=cache_dir, offline=offline, client=c)
            gnv = paths.get(f"GNV1B_{mission.truth_code}")
            if gnv is None:
                missing.append(day)
                continue
            frames.append(pd.read_parquet(gnv))
            files.append(gnv.name)
            t = paths.get(f"THR1B_{mission.truth_code}")
            if t is not None:
                thr.append(pd.read_parquet(t))
    table = (
        pd.concat(frames, ignore_index=True).sort_values("t").drop_duplicates("t", keep="last").reset_index(drop=True)
        if frames
        else precise.parse_sp3("")
    )
    if missing:
        log.warning("%s: no GNV1B for %d day(s): %s", mission.name, len(missing), [d.isoformat() for d in missing])
    orbit = PreciseOrbit(mission.truth_code, mission.norad_id, table, missing, files, frame="ITRF")
    thrusters = (
        pd.concat(thr, ignore_index=True)
        if thr
        else pd.DataFrame(columns=["t", "orbit_1_ms", "orbit_2_ms", "attitude_ms"])
    )
    record = gracefo_thruster_record(mission, thrusters, missing, files)
    return orbit, record


def gracefo_thruster_record(
    mission: Mission, thrusters: pd.DataFrame, missing: list[date], files: list[str]
) -> ThrusterRecord:
    """Orbit manoeuvres from THR1B: records with orbit-control on-time, merged across gaps under ``THRUST_GAP_S``."""
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    pulses = 0
    thrust_s = 0.0
    if len(thrusters):
        t = pd.to_datetime(thrusters["t"]).to_numpy(dtype="datetime64[us]")
        orbit_ms = thrusters["orbit_1_ms"].to_numpy(dtype=float) + thrusters["orbit_2_ms"].to_numpy(dtype=float)
        firing = orbit_ms > 0
        thrust_s = float(orbit_ms[firing].sum() / 1000.0)
        pulses = int((thrusters["attitude_ms"].to_numpy(dtype=float) > 0).sum())
        raw = [
            (pd.Timestamp(t[k]), pd.Timestamp(t[k]) + pd.Timedelta(milliseconds=float(orbit_ms[k])))
            for k in np.flatnonzero(firing)
        ]
        for lo, hi in raw:
            if intervals and (lo - intervals[-1][1]).total_seconds() <= precise.THRUST_GAP_S:
                intervals[-1] = (intervals[-1][0], max(intervals[-1][1], hi))
            else:
                intervals.append((lo, hi))
    return ThrusterRecord(mission.truth_code, mission.norad_id, intervals, list(missing), list(files), pulses, thrust_s)


# --------------------------------------------------------------------------------------
# Every mission through one door


def load_truth(
    mission: Mission,
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
) -> tuple[PreciseOrbit | None, ThrusterRecord | None]:
    """The mission's reconstructed orbit over ``[start, end]`` and its published thruster record, where each exists."""
    if mission.truth == TRUTH_SWARM:
        orbit = precise.load_precise_orbit(mission.truth_code, start, end, cache_dir=cache_dir, offline=offline)
        record = precise.load_thruster_record(mission.truth_code, start, end, cache_dir=cache_dir, offline=offline)
        return orbit, record
    if mission.truth == TRUTH_GRACEFO:
        return load_gracefo_orbit(mission, start, end, cache_dir=cache_dir, offline=offline)
    if mission.truth == TRUTH_CNES:
        return load_ids_orbit(mission, start, end, cache_dir=cache_dir, offline=offline), None
    if mission.truth == TRUTH_S1:
        return load_s1_orbit(mission, start, end, cache_dir=cache_dir, offline=offline), None
    return None, None


def truth_source(mission: Mission) -> str:
    return {
        TRUTH_SWARM: "ESA Swarm precise science orbits (SW_OPER_SP3xCOM_2_, TU Delft reduced-dynamic)",
        TRUTH_GRACEFO: GRACEFO_SOURCE,
        TRUTH_CNES: IDS_SOURCE,
        TRUTH_S1: S1_SOURCE,
        TRUTH_NONE: "no reconstructed orbit on an anonymous server; laser ranging only",
    }[mission.truth]


def manoeuvre_source(mission: Mission) -> str:
    return {
        MANOEUVRES_ESA: "ESA's thruster record (SW_OPER_SC_xDYN_1B) decides; detection is a cross-check",
        MANOEUVRES_GRACEFO: "the THR1B thruster record decides (orbit-control thruster on-time); detection is a "
        "cross-check",
        MANOEUVRES_DETECTION: "no public manoeuvre record on an anonymous server: detection decides (a step in the "
        "orbit-mean semi-major axis of the precise orbit, and the jump detector on the element sets)",
    }[mission.manoeuvres]


def mission_sources_record(missions: list[Mission], retrieved_at: datetime) -> list[dict[str, Any]]:
    """The sources block of the page: one entry per distinct product, plus what was not covered."""
    seen: dict[str, dict[str, Any]] = {}
    for m in missions:
        key = m.truth
        entry = seen.setdefault(
            key,
            {"source": truth_source(m), "retrieved_at": retrieved_at.isoformat(), "missions": []},
        )
        entry["missions"].append(f"{m.name} (NORAD {m.norad_id})")
    out = list(seen.values())
    out.append(
        {
            "source": "Asked for and not obtainable without an account; said, not substituted",
            "items": dict(NOT_COVERED),
        }
    )
    return out
