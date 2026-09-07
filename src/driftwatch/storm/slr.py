"""Satellite laser ranging as a second, independent truth: normal points, stations, and a range model.

The ILRS network measures the round-trip time of flight of laser pulses to retroreflectors on
satellites; a *normal point* is the average of the returns in a short bin (a few seconds for a low
satellite), with centimetre precision. The EUROLAS Data Center (EDC, DGFI-TUM) serves the normal
points in the Consolidated Laser Ranging Data format, version 2 (CRD v2), one file per satellite
and day, anonymously; the ILRS publishes the station coordinates (SLRF2020, the ILRS extension of
the ITRF2020, positions at 2015.0 with velocities) as a SINEX file. Both are read here.

What is computed. For an orbit -- a precise science orbit, or an SGP4 propagation of a public
element set -- the *predicted* one-way range to a station is the mean of the up and down legs,
with the light time iterated so that the satellite is taken at the bounce time and the station
at its transmit and receive times, in an inertial frame (TEME). The *observed* one-way range is
half the round-trip time of flight times the speed of light, less the tropospheric delay. The
residual, observed minus predicted, is what the table reports.

Two things are not corrected and are stated wherever the residual is. The tropospheric delay is
the Marini-Murray model (Marini & Murray 1973), the ILRS standard until 2006, from the pressure,
temperature and humidity the station recorded with the pass; it is accurate to a few centimetres
above 20 degrees of elevation and the residuals are restricted to that. The retroreflector's
offset from the satellite's centre of mass, which the precise orbits refer to, is not applied:
it is of order a metre or less and mission-specific, so the orbit-versus-laser residuals here are a
bound at the metre level, three orders of magnitude below the element-set residuals they are
placed beside, and not a validation of the orbit products at their own centimetre level.

Physics note. Light time matters at this level: a satellite at 1,000 km moves about 7 m during
the round trip, and the Earth-fixed station moves about 3 m; both are inside the iteration. The
Sagnac term that a purely Earth-fixed computation would miss is a metre or more, which is why the
legs are computed in an inertial frame.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.orbit.frames import itrs_to_geodetic, itrs_to_teme

log = logging.getLogger(__name__)

C_KM_S = 299792.458
EDC_NPT_URL = "https://edc.dgfi.tum.de/pub/slr/data/npt_crd_v2/"
EDC_SOURCE = (
    "EUROLAS Data Center (EDC, DGFI-TUM), ILRS normal points in CRD v2, one file per satellite and day "
    "(edc.dgfi.tum.de/pub/slr/data/npt_crd_v2), anonymous HTTPS"
)
SLRF2020_URL = "https://ilrs.gsfc.nasa.gov/docs/2025/SLRF2020_POS+VEL_2025.02.05.snx"
# The station coordinates refer to the ground marker; the offset from the marker to the telescope's
# optical reference point is the site eccentricity, kept by the ILRS in a separate SINEX file. It is
# up to a few metres at a trailer-mounted station (Yarragadee: 3.18 m up) and zero at most fixed ones.
ECCENTRICITY_URL = "https://ilrs.gsfc.nasa.gov/docs/2026/slrecc.260527.ILRS.xyz.snx"
ECCENTRICITY_SOURCE = (
    "ILRS site eccentricities, marker to optical reference point in XYZ (slrecc.260527.ILRS.xyz.snx, "
    "ilrs.gsfc.nasa.gov/docs/2026), SINEX"
)
SLRF2020_SOURCE = (
    "ILRS SLRF2020 positions and velocities, the ILRS extension of ITRF2020 (SLRF2020_POS+VEL_2025.02.05.snx, "
    "ilrs.gsfc.nasa.gov/docs/2025), SINEX"
)
MIN_ELEVATION_DEG = 20.0
# Epoch event codes in a CRD normal-point record: which instant the timestamp is.
EVENT_RECEIVE, EVENT_BOUNCE, EVENT_TRANSMIT = 0, 1, 2


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
    return httpx.Client(timeout=120.0, headers={"User-Agent": config.USER_AGENT}, follow_redirects=True)


# --------------------------------------------------------------------------------------
# Normal points


def fetch_normal_points_day(
    satellite: str,
    day: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> Path | None:
    """The CRD v2 normal-point file for one satellite-day, from the cache or EDC; None when there is none.

    A day the server has no file for is remembered by an empty ``.missing`` marker, so it is not
    asked for again.
    """
    folder = Path(cache_dir) / "slr" / "npt" / satellite
    name = f"{satellite}_{day:%Y%m%d}.np2"
    dest = folder / name
    marker = folder / (name + ".missing")
    if dest.exists():
        return dest
    if marker.exists() or offline:
        return None
    url = f"{EDC_NPT_URL}{satellite}/{day.year}/{name}"
    with _client(client) as c:
        r = c.get(url)
    folder.mkdir(parents=True, exist_ok=True)
    if r.status_code == 404:
        marker.write_text("", encoding="utf-8")
        return None
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def _sod_to_time(day: date, seconds: float, previous: float | None) -> tuple[datetime, float]:
    """A seconds-of-day timestamp as a UTC datetime; a value smaller than the previous one has crossed midnight."""
    if previous is not None and seconds + 43200.0 < previous:
        day = day + timedelta(days=1)
    return datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(seconds=float(seconds)), seconds


def parse_crd(text: str) -> pd.DataFrame:
    """Normal points from a CRD (v1 or v2) file: one row per record 11, with its session's context.

    Columns: ``station`` (CDP pad id), ``station_name``, ``target``, ``norad_id``, ``t`` (UTC, the
    instant the epoch event names), ``epoch_event`` (0 receive, 1 bounce, 2 transmit), ``tof_s``
    (round-trip time of flight for two-way ranging), ``two_way`` (from the h4 range-type field),
    ``wavelength_nm``, ``pressure_mbar``, ``temperature_k``, ``humidity_pct`` (the nearest
    meteorological record of the session), ``n_raw``, ``rms_ps``, ``window_s``.
    """
    rows: list[dict[str, Any]] = []
    station = station_name = target = ""
    norad = 0
    session_day: date | None = None
    two_way = True
    wavelength = np.nan
    met: list[tuple[float, float, float, float]] = []
    previous: float | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = line[:2].lower()
        f = line.split()
        if key == "h2":
            station_name = f[1]
            station = f[2]
        elif key == "h3":
            target = f[1]
            norad = int(f[4]) if len(f) > 4 and f[4].lstrip("-").isdigit() else 0
        elif key == "h4":
            session_day = date(int(f[2]), int(f[3]), int(f[4]))
            met = []
            previous = None
            # After the two date-times: release, tropospheric, centre-of-mass, amplitude, station delay,
            # spacecraft delay, range type, quality.
            tail = f[14:]
            two_way = len(tail) < 7 or tail[6] in ("2", "4")
        elif key == "c0":
            try:
                wavelength = float(f[2])
            except (IndexError, ValueError):
                wavelength = np.nan
        elif key == "20" and session_day is not None:
            try:
                met.append((float(f[1]), float(f[2]), float(f[3]), float(f[4])))
            except (IndexError, ValueError):
                continue
        elif key == "11" and session_day is not None:
            try:
                sod, tof = float(f[1]), float(f[2])
                event = int(f[4])
                window = float(f[5])
                n_raw = int(float(f[6]))
                rms = float(f[7])
            except (IndexError, ValueError):
                continue
            t, previous = _sod_to_time(session_day, sod, previous)
            p = t_k = rh = np.nan
            if met:
                nearest = min(met, key=lambda m: abs(m[0] - sod))
                p, t_k, rh = nearest[1], nearest[2], nearest[3]
            rows.append(
                {
                    "station": station,
                    "station_name": station_name,
                    "target": target,
                    "norad_id": norad,
                    "t": t,
                    "epoch_event": event,
                    "tof_s": tof,
                    "two_way": two_way,
                    "wavelength_nm": wavelength,
                    "pressure_mbar": p,
                    "temperature_k": t_k,
                    "humidity_pct": rh,
                    "n_raw": n_raw,
                    "rms_ps": rms,
                    "window_s": window,
                }
            )
    frame = pd.DataFrame(
        rows,
        columns=[
            "station",
            "station_name",
            "target",
            "norad_id",
            "t",
            "epoch_event",
            "tof_s",
            "two_way",
            "wavelength_nm",
            "pressure_mbar",
            "temperature_k",
            "humidity_pct",
            "n_raw",
            "rms_ps",
            "window_s",
        ],
    )
    if len(frame):
        frame["t"] = pd.to_datetime(frame["t"], utc=True)
    return frame


def load_normal_points(
    satellite: str,
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> tuple[pd.DataFrame, list[date], list[date]]:
    """Every normal point for ``satellite`` from ``start`` to ``end`` inclusive.

    Returns ``(points, days with a file, days without)``.
    """
    frames: list[pd.DataFrame] = []
    have: list[date] = []
    missing: list[date] = []
    day = start
    with _client(client) as c:
        while day <= end:
            path = fetch_normal_points_day(satellite, day, cache_dir=cache_dir, offline=offline, client=c)
            if path is None:
                missing.append(day)
            else:
                have.append(day)
                frames.append(parse_crd(path.read_text(encoding="ascii", errors="replace")))
            day += timedelta(days=1)
    points = pd.concat(frames, ignore_index=True) if frames else parse_crd("")
    if len(points):
        points = points.sort_values("t").reset_index(drop=True)
    return points, have, missing


# --------------------------------------------------------------------------------------
# Stations


@dataclass(frozen=True)
class StationSolution:
    code: str
    soln: str
    start: datetime | None
    end: datetime | None
    ref_epoch: datetime
    position_m: np.ndarray  # ITRF2020 at the reference epoch
    velocity_m_yr: np.ndarray

    def position_km(self, at: datetime) -> np.ndarray:
        years = (at - self.ref_epoch).total_seconds() / (365.25 * 86400.0)
        return (self.position_m + self.velocity_m_yr * years) / 1000.0


def _sinex_epoch(text: str) -> datetime | None:
    """``yy:ddd:sssss`` as a UTC datetime; ``00:000:00000`` is open-ended and returns None."""
    yy, ddd, sssss = text.split(":")
    if int(yy) == 0 and int(ddd) == 0:
        return None
    year = int(yy) + (2000 if int(yy) < 50 else 1900)
    return datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=int(ddd) - 1, seconds=int(sssss))


def fetch_station_file(
    *, cache_dir: Path = config.CACHE_DIR, offline: bool = False, client: httpx.Client | None = None
) -> Path:
    dest = Path(cache_dir) / "slr" / SLRF2020_URL.rsplit("/", 1)[-1]
    if dest.exists():
        return dest
    if offline:
        raise FileNotFoundError(f"no cached station file at {dest}")
    with _client(client) as c:
        r = c.get(SLRF2020_URL)
        r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


def parse_sinex_stations(text: str) -> dict[str, list[StationSolution]]:
    """Station positions and velocities by CDP code from a SINEX file's SOLUTION/EPOCHS and SOLUTION/ESTIMATE blocks."""
    epochs: dict[tuple[str, str], tuple[datetime | None, datetime | None]] = {}
    estimates: dict[tuple[str, str], dict[str, tuple[datetime, float]]] = {}
    block = ""
    for raw in text.splitlines():
        if raw.startswith("+"):
            block = raw[1:].strip()
            continue
        if raw.startswith("-"):
            block = ""
            continue
        if raw.startswith("*") or not raw.strip():
            continue
        f = raw.split()
        if block == "SOLUTION/EPOCHS" and len(f) >= 7:
            epochs[(f[0], f[2])] = (_sinex_epoch(f[4]), _sinex_epoch(f[5]))
        elif block == "SOLUTION/ESTIMATE" and len(f) >= 9:
            kind, code, soln, ref = f[1], f[2], f[4], f[5]
            ref_epoch = _sinex_epoch(ref)
            if ref_epoch is None:
                continue
            estimates.setdefault((code, soln), {})[kind] = (ref_epoch, float(f[8].replace("D", "E")))
    out: dict[str, list[StationSolution]] = {}
    for (code, soln), values in estimates.items():
        if not all(k in values for k in ("STAX", "STAY", "STAZ")):
            continue
        ref_epoch = values["STAX"][0]
        pos = np.array([values["STAX"][1], values["STAY"][1], values["STAZ"][1]])
        vel = np.array([values.get(k, (ref_epoch, 0.0))[1] for k in ("VELX", "VELY", "VELZ")])
        start, end = epochs.get((code, soln), (None, None))
        out.setdefault(code, []).append(StationSolution(code, soln, start, end, ref_epoch, pos, vel))
    for code in out:
        out[code].sort(key=lambda s: s.start or datetime(1900, 1, 1, tzinfo=UTC))
    return out


@dataclass(frozen=True)
class Eccentricity:
    code: str
    start: datetime | None
    end: datetime | None
    xyz_m: np.ndarray


def fetch_eccentricity_file(
    *, cache_dir: Path = config.CACHE_DIR, offline: bool = False, client: httpx.Client | None = None
) -> Path:
    dest = Path(cache_dir) / "slr" / ECCENTRICITY_URL.rsplit("/", 1)[-1]
    if dest.exists():
        return dest
    if offline:
        raise FileNotFoundError(f"no cached eccentricity file at {dest}")
    with _client(client) as c:
        r = c.get(ECCENTRICITY_URL)
        r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


def parse_sinex_eccentricities(text: str) -> dict[str, list[Eccentricity]]:
    """Marker-to-instrument offsets by station code from the SITE/ECCENTRICITY block (XYZ rows only)."""
    out: dict[str, list[Eccentricity]] = {}
    block = ""
    for raw in text.splitlines():
        if raw.startswith("+"):
            block = raw[1:].strip()
            continue
        if raw.startswith("-"):
            block = ""
            continue
        if block != "SITE/ECCENTRICITY" or raw.startswith("*") or not raw.strip():
            continue
        f = raw.split()
        m = re.search(r"\b(XYZ|UNE)\b(.*)$", raw)
        if len(f) < 7 or m is None or m.group(1) != "XYZ":
            continue
        # The values are fixed-width and run together when one is hundreds of metres.
        values = re.findall(r"-?\d+\.\d+", m.group(2))[:3]
        if len(values) < 3:
            continue
        out.setdefault(f[0], []).append(
            Eccentricity(f[0], _sinex_epoch(f[4]), _sinex_epoch(f[5]), np.array([float(v) for v in values]))
        )
    return out


@dataclass
class Stations:
    """The coordinate solutions and the eccentricities together: a station's optical reference point at a time."""

    solutions: Mapping[str, list[StationSolution]]
    eccentricities: Mapping[str, list[Eccentricity]]

    def eccentricity_m(self, code: str, at: datetime) -> np.ndarray | None:
        rows = self.eccentricities.get(code)
        if not rows:
            return None
        for e in rows:
            if (e.start is None or e.start <= at) and (e.end is None or at <= e.end):
                return e.xyz_m
        return rows[-1].xyz_m

    def position_km(self, code: str, at: datetime) -> np.ndarray | None:
        """Marker position plus eccentricity, km, ITRF; None for a station not in the coordinate file."""
        solution = station_at(self.solutions, code, at)
        if solution is None:
            return None
        ecc = self.eccentricity_m(code, at)
        return solution.position_km(at) + (ecc / 1000.0 if ecc is not None else 0.0)


def load_stations(*, cache_dir: Path = config.CACHE_DIR, offline: bool = False) -> Stations:
    """SLRF2020 solutions and the ILRS eccentricities, fetched once and cached."""
    solutions = parse_sinex_stations(
        fetch_station_file(cache_dir=cache_dir, offline=offline).read_text(encoding="ascii", errors="replace")
    )
    ecc = parse_sinex_eccentricities(
        fetch_eccentricity_file(cache_dir=cache_dir, offline=offline).read_text(encoding="ascii", errors="replace")
    )
    return Stations(solutions, ecc)


def station_at(solutions: Mapping[str, list[StationSolution]], code: str, at: datetime) -> StationSolution | None:
    """The solution valid at ``at`` for a station code, or the last one when none brackets it."""
    candidates = solutions.get(code)
    if not candidates:
        return None
    for s in candidates:
        if (s.start is None or s.start <= at) and (s.end is None or at <= s.end):
            return s
    return candidates[-1]


# --------------------------------------------------------------------------------------
# The troposphere and the range model


def marini_murray_m(
    elevation_deg: np.ndarray,
    pressure_mbar: np.ndarray,
    temperature_k: np.ndarray,
    humidity_pct: np.ndarray,
    latitude_deg: float,
    height_km: float,
    wavelength_um: float,
) -> np.ndarray:
    """One-way tropospheric range correction in metres, Marini & Murray (1973).

    Inputs are the station's surface pressure (mbar), temperature (K) and relative humidity (%),
    its geodetic latitude and height, and the laser wavelength in micrometres.
    """
    e = np.radians(np.asarray(elevation_deg, dtype=float))
    p = np.asarray(pressure_mbar, dtype=float)
    t = np.asarray(temperature_k, dtype=float)
    rh = np.asarray(humidity_pct, dtype=float)
    tc = t - 273.15
    e_h2o = rh / 100.0 * 6.11 * 10.0 ** (7.5 * tc / (237.3 + tc))
    lam = float(wavelength_um)
    f_lam = 0.9650 + 0.0164 / lam**2 + 0.000228 / lam**4
    phi = np.radians(latitude_deg)
    f_phi = 1.0 - 0.0026 * np.cos(2.0 * phi) - 0.00031 * height_km
    k = 1.163 - 0.00968 * np.cos(2.0 * phi) - 0.00104 * t + 0.00001435 * p
    a = 0.002357 * p + 0.000141 * e_h2o
    b = 1.084e-8 * p * t * k + 4.734e-8 * (p**2 / t) * (2.0 / (3.0 - 1.0 / k))
    s = np.sin(e)
    return (f_lam / f_phi) * (a + b) / (s + (b / (a + b)) / (s + 0.01))


def station_teme_km(position_itrf_km: np.ndarray, times: np.ndarray) -> np.ndarray:
    """An Earth-fixed station position, rotated into TEME at each of ``times`` (datetime64)."""
    n = np.asarray(times, dtype="datetime64[us]").size
    r = np.repeat(np.asarray(position_itrf_km, dtype=float)[None, :], n, axis=0)
    v = np.zeros_like(r)
    return itrs_to_teme(r, v, times)[0]


PositionFn = Callable[[np.ndarray], np.ndarray]
"""Inertial (TEME) positions in km, shape ``(n, 3)``, at ``datetime64[us]`` times; NaN where unavailable."""


@dataclass
class RangeResult:
    """Per normal point: the predicted one-way range, the observed geometric one-way range, and the geometry."""

    predicted_km: np.ndarray
    observed_km: np.ndarray
    elevation_deg: np.ndarray
    tropo_m: np.ndarray
    t_bounce: np.ndarray

    @property
    def residual_m(self) -> np.ndarray:
        return (self.observed_km - self.predicted_km) * 1000.0


def predicted_ranges(
    points: pd.DataFrame,
    position_teme: PositionFn,
    station_itrf_km: np.ndarray,
    *,
    iterations: int = 2,
) -> RangeResult:
    """The light-time-iterated one-way range for each normal point in ``points`` from one station.

    ``points`` are one station's records; ``station_itrf_km`` its ITRF position (the drift over a
    pass is negligible). The bounce time is solved from the epoch event: transmit, bounce or
    receive. Elevation is the satellite's elevation at the bounce time from the station's
    geocentric vertical, which is within a fifth of a degree of the geodetic one.
    """
    t0 = points["t"].to_numpy(dtype="datetime64[us]")
    tof = points["tof_s"].to_numpy(dtype=float)
    event = points["epoch_event"].to_numpy(dtype=int)
    two_way = points["two_way"].to_numpy(dtype=bool)
    one_way_s = np.where(two_way, tof / 2.0, tof)
    us = np.timedelta64(1, "us")

    def shifted(base: np.ndarray, seconds: np.ndarray) -> np.ndarray:
        return base + (seconds * 1e6).astype("timedelta64[us]")

    # First guess: everything at the timestamp, then iterate the legs.
    up = one_way_s * C_KM_S
    down = one_way_s * C_KM_S
    t_b = np.where(
        event == EVENT_BOUNCE,
        t0,
        np.where(event == EVENT_TRANSMIT, shifted(t0, up / C_KM_S), shifted(t0, -down / C_KM_S)),
    )
    for _ in range(iterations):
        t_tx = shifted(t_b, -up / C_KM_S)
        t_rx = shifted(t_b, down / C_KM_S)
        r_sat = position_teme(t_b)
        r_tx = station_teme_km(station_itrf_km, t_tx)
        r_rx = station_teme_km(station_itrf_km, t_rx)
        up = np.linalg.norm(r_sat - r_tx, axis=1)
        down = np.linalg.norm(r_rx - r_sat, axis=1)
        t_b = np.where(
            event == EVENT_BOUNCE,
            t0,
            np.where(event == EVENT_TRANSMIT, shifted(t0, up / C_KM_S), shifted(t0, -down / C_KM_S)),
        )
    _ = us
    r_sat = position_teme(t_b)
    r_b = station_teme_km(station_itrf_km, t_b)
    los = r_sat - r_b
    up_vec = r_b / np.linalg.norm(r_b, axis=1, keepdims=True)
    with np.errstate(invalid="ignore"):
        elevation = np.degrees(np.arcsin(np.sum(los * up_vec, axis=1) / np.linalg.norm(los, axis=1)))
    lat, _, height_km = itrs_to_geodetic(np.asarray(station_itrf_km, dtype=float)[None, :])
    wavelength_um = points["wavelength_nm"].to_numpy(dtype=float) / 1000.0
    tropo = np.full(len(points), np.nan)
    met_ok = points[["pressure_mbar", "temperature_k", "humidity_pct"]].notna().all(axis=1).to_numpy()
    if met_ok.any():
        lam = float(np.nanmedian(wavelength_um[met_ok])) if np.isfinite(wavelength_um[met_ok]).any() else 0.532
        tropo[met_ok] = marini_murray_m(
            elevation[met_ok],
            points["pressure_mbar"].to_numpy(dtype=float)[met_ok],
            points["temperature_k"].to_numpy(dtype=float)[met_ok],
            points["humidity_pct"].to_numpy(dtype=float)[met_ok],
            float(lat[0]),
            float(height_km[0]),
            lam,
        )
    observed = one_way_s * C_KM_S - tropo / 1000.0
    predicted = 0.5 * (up + down)
    return RangeResult(predicted, observed, elevation, tropo, t_b)


def range_residuals(
    points: pd.DataFrame,
    position_teme: PositionFn,
    stations: Stations | Mapping[str, list[StationSolution]],
    *,
    min_elevation_deg: float = MIN_ELEVATION_DEG,
) -> pd.DataFrame:
    """Observed-minus-predicted one-way range per normal point, station by station, above the elevation cut.

    Rows whose station is not in the coordinate file, whose orbit is unavailable at the bounce
    time, or whose elevation is below the cut are dropped and counted in ``attrs["dropped"]``.
    """
    out: list[pd.DataFrame] = []
    dropped = {
        "unknown station": 0,
        "no orbit at the bounce time": 0,
        "below the elevation cut": 0,
        "no meteorology": 0,
    }
    for code, group in points.groupby("station", sort=False):
        group = group.reset_index(drop=True)
        mid = group["t"].iloc[len(group) // 2].to_pydatetime()
        if isinstance(stations, Stations):
            position = stations.position_km(str(code), mid)
        else:
            solution = station_at(stations, str(code), mid)
            position = None if solution is None else solution.position_km(mid)
        if position is None:
            dropped["unknown station"] += len(group)
            continue
        result = predicted_ranges(group, position_teme, position)
        frame = group.copy()
        frame["predicted_km"] = result.predicted_km
        frame["observed_km"] = result.observed_km
        frame["elevation_deg"] = result.elevation_deg
        frame["tropo_m"] = result.tropo_m
        frame["residual_m"] = result.residual_m
        frame["t_bounce"] = pd.to_datetime(result.t_bounce, utc=True)
        ok = np.isfinite(frame["predicted_km"].to_numpy())
        dropped["no orbit at the bounce time"] += int((~ok).sum())
        frame = frame[ok]
        met = np.isfinite(frame["tropo_m"].to_numpy())
        dropped["no meteorology"] += int((~met).sum())
        frame = frame[met]
        high = frame["elevation_deg"].to_numpy() >= min_elevation_deg
        dropped["below the elevation cut"] += int((~high).sum())
        out.append(frame[high])
    result = pd.concat(out, ignore_index=True) if out else points.iloc[0:0].copy()
    result.attrs["dropped"] = dropped
    return result


def residual_summary(residuals: pd.DataFrame) -> dict[str, Any]:
    """n, stations, median, RMS and 95th percentile of the absolute residual, in metres."""
    r = residuals["residual_m"].to_numpy(dtype=float) if len(residuals) else np.array([])
    if not r.size:
        return {"n": 0, "n_stations": 0, "median_m": None, "median_abs_m": None, "rms_m": None, "p95_abs_m": None}
    return {
        "n": int(r.size),
        "n_stations": int(residuals["station"].nunique()),
        "median_m": float(np.median(r)),
        "median_abs_m": float(np.median(np.abs(r))),
        "rms_m": float(np.sqrt(np.mean(r**2))),
        "p95_abs_m": float(np.quantile(np.abs(r), 0.95)),
    }


def sgp4_position_fn(satrec) -> PositionFn:
    """A :data:`PositionFn` for one element set: SGP4 in TEME at the requested times."""
    from driftwatch.orbit.propagator import propagate_satrecs

    def fn(times: np.ndarray) -> np.ndarray:
        t64 = np.asarray(times, dtype="datetime64[us]")
        if not t64.size:
            return np.zeros((0, 3))
        state = propagate_satrecs([satrec], np.array([0]), t64)
        r = state.r_teme[0].astype(float)
        r[state.error[0] != 0] = np.nan
        return r

    return fn
