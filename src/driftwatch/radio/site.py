"""MeerKAT geometry and explicitly sourced measured beam slices.

The historical Mauch L-band analytic width remains solely to reproduce the old
component diagnostic and circular illustrative catalogue passages. It must not be
silently extrapolated as the measured S-band pattern. Corrected paired comparisons
require a MeasuredBeam and use full TEME-to-ITRS positions at every sample with a
rotating observer. The older UTC/GMST PEF helper remains for historical illustrations.
Both paths use geometric directions without atmospheric refraction.
"""

from __future__ import annotations

import hashlib
import io
import json
import struct
import warnings
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import astropy.units as u
import erfa
import httpx
import numpy as np
from astropy.coordinates import ICRS, ITRS, TEME, AltAz, CartesianRepresentation, EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers
from scipy.interpolate import RegularGridInterpolator

from driftwatch import config
from driftwatch.orbit.time import julian_dates, to_datetime64

WGS84_A_KM = 6378.137
WGS84_E2 = 6.69437999014e-3
EARTH_RADIUS_KM = 6378.137

# Mauch et al. 2020, equation 4: 57.5 arcmin at 1.5 GHz, scaling as 1/frequency.
BEAM_FWHM_ARCMIN_AT_1500_MHZ = 57.5
BEAM_REFERENCE_MHZ = 1500.0
BEAM_SOURCE = (
    "Mauch et al. 2020, ApJ 888, 61, section 2.2, equation 4 (circularised L-band half-power width "
    "57.5 arcmin at 1.5 GHz, scaling as 1/frequency); applied to UHF and S by the lambda/D scaling "
    "de Villiers 2023, AJ 165, 78 reports over most of each band"
)

# The analytic width above remains available to reproduce the original component
# tables. Corrected track comparisons require a MeasuredBeam explicitly; they never
# silently replace a missing measured beam with the wavelength approximation.
MEASURED_BEAM_URL = "https://archive-gw-1.kat.ac.za/public/repository/10.48479/wdb0-h061"
MEASURED_BEAM_DOI = "https://doi.org/10.48479/wdb0-h061"
MEASURED_BEAM_CACHE = config.CACHE_DIR / "radio"
BEAM_LICENCE = "CC BY-NC 4.0; third-party data, not the repository's MIT code licence"


class _RemoteZip(io.RawIOBase):
    """Seekable HTTP range reader; prevents downloading a 35 GB beam cube by accident."""

    def __init__(self, url: str, client: httpx.Client):
        self.url, self.client, self.pos = url, client, 0
        head = client.head(url)
        head.raise_for_status()
        self.length = int(head.headers["content-length"])
        self.last_modified = head.headers.get("last-modified")
        self.ranges: list[dict[str, Any]] = []

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = offset if whence == 0 else (self.pos + offset if whence == 1 else self.length + offset)
        if self.pos < 0:
            raise ValueError("negative remote-file offset")
        return self.pos

    def read(self, size: int = -1) -> bytes:
        size = min(self.length - self.pos, size if size >= 0 else self.length)
        if size <= 0:
            return b""
        if size > 2_000_000:
            raise ValueError("beam extraction refuses a range above 2 MB")
        start, end = self.pos, self.pos + size - 1
        response = self.client.get(self.url, headers={"Range": f"bytes={start}-{end}"})
        response.raise_for_status()
        expected = f"bytes {start}-{end}/{self.length}"
        if response.status_code != 206 or response.headers.get("content-range") != expected:
            raise ValueError("beam server did not honour the exact byte range")
        data = response.content
        if len(data) != size:
            raise ValueError("truncated measured-beam range")
        self.pos += size
        self.ranges.append({"start": start, "end": end, "sha256": hashlib.sha256(data).hexdigest()})
        return data


def _npy_member(remote: _RemoteZip, archive: zipfile.ZipFile, name: str) -> tuple[int, tuple[int, ...], np.dtype]:
    """Byte offset and declared shape/dtype of an uncompressed NumPy member."""
    info = archive.getinfo(name)
    if info.compress_type != zipfile.ZIP_STORED:
        raise ValueError("selective beam extraction requires ZIP_STORED members")
    remote.seek(info.header_offset)
    header = remote.read(30)
    if header[:4] != b"PK\x03\x04":
        raise ValueError("invalid measured-beam ZIP member header")
    name_length, extra_length = struct.unpack_from("<HH", header, 26)
    offset = info.header_offset + 30 + name_length + extra_length
    remote.seek(offset)
    prefix = io.BytesIO(remote.read(min(1024, info.file_size)))
    version = np.lib.format.read_magic(prefix)
    if version == (1, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(prefix)
    elif version == (2, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_2_0(prefix)
    else:
        raise ValueError(f"unsupported NumPy beam header {version}")
    if fortran or dtype.hasobject:
        raise ValueError("beam extraction requires numeric C-order arrays")
    return offset + prefix.tell(), shape, dtype


def cache_measured_beam(band: str, requested_frequency_mhz: float, *, directory: Path = MEASURED_BEAM_CACHE) -> Path:
    """Cache an array-average Jones slice and its measured ellipse metrics.

    Only selected byte ranges are fetched. The requested frequency selects the
    nearest measured channel (less than one channel away); the actual frequency,
    original source headers, byte hashes and local file hash are retained. The
    published edge is 3499.1455 MHz, not a measurement at exactly 3500 MHz.
    """
    band = band.upper()
    if band not in {"U", "L", "S0", "S4"}:
        raise ValueError("measured beam band must be U, L, S0 or S4")
    directory = Path(directory)
    target = directory / f"meerkat_{band}_{requested_frequency_mhz:.6f}MHz.npz"
    provenance_path = target.with_suffix(".json")
    if target.exists() and provenance_path.exists():
        MeasuredBeam.load(target)  # validate the existing cache before reusing it
        return target
    source = f"{MEASURED_BEAM_URL}/data/MeerKAT_{band}_band_primary_beam.npz"
    metric_source = source.replace(".npz", "_metrics.npz")
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        remote = _RemoteZip(source, client)
        archive = zipfile.ZipFile(remote)
        small: dict[str, np.ndarray] = {}
        for name in ("freq_MHz", "margin_deg", "antnames", "pols"):
            with archive.open(f"{name}.npy") as member:
                small[name] = np.load(io.BytesIO(member.read()), allow_pickle=False)
        frequencies, axis = small["freq_MHz"], small["margin_deg"]
        channel = int(np.argmin(abs(frequencies - requested_frequency_mhz)))
        spacing = float(np.median(np.diff(frequencies)))
        if abs(float(frequencies[channel]) - requested_frequency_mhz) > spacing * 1.001:
            raise ValueError("requested frequency lies outside the measured channels")
        names = [x.decode() for x in small["antnames"]]
        antenna = names.index("array_average")
        pols = [x.decode() for x in small["pols"]]
        if pols != ["HH", "HV", "VH", "VV"]:
            raise ValueError("unexpected Jones polarization order")
        offset, shape, dtype = _npy_member(remote, archive, "beam.npy")
        expected = (4, len(names), len(frequencies), len(axis), len(axis))
        if shape != expected:
            raise ValueError(f"unexpected measured beam shape: {shape}")
        size = len(axis) ** 2 * dtype.itemsize
        planes = []
        for pol in range(4):
            start = offset + ((pol * len(names) + antenna) * len(frequencies) + channel) * size
            remote.seek(start)
            planes.append(np.frombuffer(remote.read(size), dtype=dtype).reshape(len(axis), len(axis)))
        metrics_remote = _RemoteZip(metric_source, client)
        metrics_zip = zipfile.ZipFile(metrics_remote)
        metrics: dict[str, float] = {}
        for name in ("Imajor", "Iminor", "Iangle", "Ix0", "Iy0"):
            start, metric_shape, metric_dtype = _npy_member(metrics_remote, metrics_zip, f"{name}.npy")
            if metric_shape != (len(names), len(frequencies)):
                raise ValueError("measured beam metric dimensions differ from the cube")
            metrics_remote.seek(start + (antenna * len(frequencies) + channel) * metric_dtype.itemsize)
            metrics[name] = float(np.frombuffer(metrics_remote.read(metric_dtype.itemsize), dtype=metric_dtype)[0])
        provenance = {
            "schema_version": 1,
            "doi": MEASURED_BEAM_DOI,
            "source_url": source,
            "source_bytes": remote.length,
            "source_last_modified": remote.last_modified,
            "source_shape": list(shape),
            "source_dtype": str(dtype),
            "source_byte_ranges": remote.ranges,
            "metric_source_url": metric_source,
            "metric_source_byte_ranges": metrics_remote.ranges,
            "requested_frequency_mhz": float(requested_frequency_mhz),
            "frequency_mhz": float(frequencies[channel]),
            "channel_index": channel,
            "channel_spacing_mhz": spacing,
            "antenna_index": antenna,
            "antenna": "array_average",
            "polarizations": pols,
            "measured_metrics": metrics,
            "orientation_source": f"{MEASURED_BEAM_URL}/beam_orientation_diagram.pdf",
            "orientation": "source axes Y,X; supplied pattern flips vertically onto upward sky coordinates",
            "measurement_conditions": "60 degree elevation, 15 Celsius; 2020-2022 average (S: 2021-2022)",
            "licence": BEAM_LICENCE,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(target, jones=np.stack(planes), margin_deg=axis)
    provenance["cache_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return target


@dataclass
class MeasuredBeam:
    """Measured Stokes-I response to an unpolarized source, relative to beam peak.

    The raw Jones sum retains measured shape and squint. A peak normalization only
    sets the half-power contour; it is not a received flux or interference estimate.
    Source coordinates are horizontal X and downward Y. Public sky evaluation takes
    horizontal right/increasing azimuth and vertical up/increasing elevation.
    """

    margin_deg: np.ndarray
    jones: np.ndarray
    provenance: dict[str, Any]
    _interpolator: RegularGridInterpolator = field(init=False, repr=False)
    power_yx: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        axis = np.asarray(self.margin_deg, dtype=float)
        jones = np.asarray(self.jones)
        if axis.ndim != 1 or len(axis) < 3 or not np.all(np.diff(axis) > 0):
            raise ValueError("measured beam angular coordinates must increase strictly")
        if jones.shape != (4, len(axis), len(axis)) or not np.isfinite(jones).all():
            raise ValueError("measured Jones slice is incomplete or malformed")
        power = 0.5 * np.sum(np.abs(jones.astype(np.complex128)) ** 2, axis=0)
        peak = float(np.max(power))
        if not np.isfinite(peak) or peak <= 0:
            raise ValueError("measured beam has no finite positive peak")
        self.margin_deg = axis
        self.power_yx = power / peak
        self._interpolator = RegularGridInterpolator((axis, axis), self.power_yx, bounds_error=False, fill_value=0.0)

    @classmethod
    def load(cls, path: Path) -> MeasuredBeam:
        path = Path(path)
        provenance = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        if hashlib.sha256(path.read_bytes()).hexdigest() != provenance["cache_sha256"]:
            raise ValueError("measured beam cache hash does not match its provenance")
        with np.load(path, allow_pickle=False) as data:
            return cls(data["margin_deg"].copy(), data["jones"].copy(), provenance)

    @property
    def frequency_mhz(self) -> float:
        return float(self.provenance["frequency_mhz"])

    def power(self, horizontal_deg, vertical_deg) -> np.ndarray:
        x, y = np.broadcast_arrays(horizontal_deg, vertical_deg)
        points = np.stack([-y, x], axis=-1)  # published orientation: flip vertically
        return np.asarray(self._interpolator(points), dtype=float).reshape(x.shape)

    def record(self) -> dict[str, Any]:
        return {**self.provenance, "response": "measured unpolarized Stokes I, normalized to peak", "half_power": 0.5}


@dataclass(frozen=True)
class Site:
    """A place on the WGS84 ellipsoid with a dish of one diameter."""

    name: str
    latitude_deg: float
    longitude_deg: float
    height_m: float
    dish_diameter_m: float
    source: str

    def ecef_km(self) -> np.ndarray:
        """The site's WGS84 Cartesian position in km."""
        phi, lam = np.radians([self.latitude_deg, self.longitude_deg])
        n = WGS84_A_KM / np.sqrt(1.0 - WGS84_E2 * np.sin(phi) ** 2)
        h = self.height_m / 1000.0
        return np.array(
            [
                (n + h) * np.cos(phi) * np.cos(lam),
                (n + h) * np.cos(phi) * np.sin(lam),
                (n * (1.0 - WGS84_E2) + h) * np.sin(phi),
            ]
        )

    def enu_basis(self) -> np.ndarray:
        """Rows are the east, north and up unit vectors in the Earth-fixed frame."""
        phi, lam = np.radians([self.latitude_deg, self.longitude_deg])
        east = np.array([-np.sin(lam), np.cos(lam), 0.0])
        north = np.array([-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)])
        up = np.array([np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)])
        return np.stack([east, north, up])

    def location(self) -> EarthLocation:
        return EarthLocation.from_geodetic(
            lon=self.longitude_deg * u.deg, lat=self.latitude_deg * u.deg, height=self.height_m * u.m
        )


# The array phase centre from SARAO's MeerKAT specifications page:
# 30° 42' 39.8" S, 21° 26' 38.0" E, 1086.6 m.
MEERKAT = Site(
    name="MeerKAT array phase centre",
    latitude_deg=-(30.0 + 42.0 / 60.0 + 39.8 / 3600.0),
    longitude_deg=21.0 + 26.0 / 60.0 + 38.0 / 3600.0,
    height_m=1086.6,
    dish_diameter_m=13.5,
    source="SARAO, MeerKAT specifications (skaafrica.atlassian.net, ESDKB page 277315585): "
    "array phase centre 30d42m39.8s S, 21d26m38.0s E, 1086.6 m; dish 13.5 m nominal",
)


@dataclass(frozen=True)
class Receiver:
    """One MeerKAT receiver: the digitised range the correlator sees, and the feed's design range."""

    name: str
    lo_mhz: float
    hi_mhz: float
    feed_lo_mhz: float | None
    feed_hi_mhz: float | None

    @property
    def centre_mhz(self) -> float:
        return 0.5 * (self.lo_mhz + self.hi_mhz)

    def overlaps(self, lo_mhz: float, hi_mhz: float) -> bool:
        """Whether ``[lo, hi]`` MHz falls at all inside the digitised band."""
        return lo_mhz < self.hi_mhz and hi_mhz > self.lo_mhz


# SARAO's specifications page: UHF 580-1015 MHz (544-1088 digitised), L 900-1670 (856-1712
# digitised), S-band in five 875 MHz sub-bands S0 to S4.
RECEIVERS: dict[str, Receiver] = {
    "UHF": Receiver("UHF", 544.0, 1088.0, 580.0, 1015.0),
    "L": Receiver("L", 856.0, 1712.0, 900.0, 1670.0),
    "S0": Receiver("S0", 1750.0, 2625.0, None, None),
    "S1": Receiver("S1", 1968.0, 2843.0, None, None),
    "S2": Receiver("S2", 2187.0, 3062.0, None, None),
    "S3": Receiver("S3", 2406.0, 3281.0, None, None),
    "S4": Receiver("S4", 2625.0, 3500.0, None, None),
}
RECEIVER_SOURCE = "SARAO, MeerKAT specifications (skaafrica.atlassian.net, ESDKB page 277315585)"


def receiver(name: str) -> Receiver:
    key = name.strip().upper()
    if key in ("S", "S-BAND"):
        key = "S0"
    if key not in RECEIVERS:
        raise KeyError(f"unknown receiver {name!r}; choose one of {', '.join(RECEIVERS)}")
    return RECEIVERS[key]


def beam_fwhm_deg(freq_mhz: float) -> float:
    """Half-power width of the primary beam in degrees at ``freq_mhz`` (see the module note)."""
    return (BEAM_FWHM_ARCMIN_AT_1500_MHZ / 60.0) * (BEAM_REFERENCE_MHZ / float(freq_mhz))


def beam_fwhm_lambda_over_d(dish_diameter_m: float = MEERKAT.dish_diameter_m) -> float:
    """The constant ``k`` in ``FWHM = k λ/D`` that the measured relation implies for this dish."""
    wavelength = 299792458.0 / (BEAM_REFERENCE_MHZ * 1e6)
    return np.radians(BEAM_FWHM_ARCMIN_AT_1500_MHZ / 60.0) / (wavelength / dish_diameter_m)


def angular_error_deg(residual_km, range_km) -> np.ndarray:
    """A position residual perpendicular to the line of sight, as an angle at the site."""
    return np.degrees(np.arctan2(np.abs(np.asarray(residual_km, dtype=float)), np.asarray(range_km, dtype=float)))


# --------------------------------------------------------------------------------------
# Earth rotation and the topocentric frame


def gmst_rad(times) -> np.ndarray:
    """Greenwich mean sidereal time (IAU 1982) at UTC ``times``, taking UTC for UT1."""
    jd, fr = julian_dates(to_datetime64(times))
    return np.asarray(erfa.gmst82(jd, fr), dtype=float)


def teme_to_pef(r_teme: np.ndarray, times) -> np.ndarray:
    """Rotate TEME vectors ``(..., m, 3)`` into the Earth-fixed frame at the ``m`` times."""
    theta = gmst_rad(times)
    c, s = np.cos(theta), np.sin(theta)
    r = np.asarray(r_teme, dtype=float)
    out = np.empty_like(r)
    out[..., 0] = c * r[..., 0] + s * r[..., 1]
    out[..., 1] = -s * r[..., 0] + c * r[..., 1]
    out[..., 2] = r[..., 2]
    return out


def pef_to_teme(r_pef: np.ndarray, times) -> np.ndarray:
    """The inverse of :func:`teme_to_pef`."""
    theta = gmst_rad(times)
    c, s = np.cos(theta), np.sin(theta)
    r = np.asarray(r_pef, dtype=float)
    out = np.empty_like(r)
    out[..., 0] = c * r[..., 0] - s * r[..., 1]
    out[..., 1] = s * r[..., 0] + c * r[..., 1]
    out[..., 2] = r[..., 2]
    return out


@dataclass
class Look:
    """Where an Earth-fixed position is seen from the site: range, elevation, azimuth, and the ENU direction."""

    range_km: np.ndarray
    elevation_deg: np.ndarray
    azimuth_deg: np.ndarray
    enu: np.ndarray


def look_from(site: Site, r_pef: np.ndarray) -> Look:
    """Topocentric range, elevation, azimuth and unit direction for Earth-fixed positions ``(..., 3)``."""
    d = np.asarray(r_pef, dtype=float) - site.ecef_km()
    enu = d @ site.enu_basis().T
    rng = np.linalg.norm(enu, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        unit = enu / rng[..., None]
    el = np.degrees(np.arctan2(enu[..., 2], np.hypot(enu[..., 0], enu[..., 1])))
    az = np.degrees(np.arctan2(enu[..., 0], enu[..., 1])) % 360.0
    return Look(rng, el, az, unit)


def look_from_teme(site: Site, positions_km: np.ndarray, times) -> Look:
    """Full-vector topocentric directions, with IERS UT1 and polar motion.

    One TEME state per UTC time. Both the prediction and reconstructed orbit must
    use this same transform. This subtracts the observer at every time; an orbital
    phase delay is consequently not assumed to preserve the apparent sky track.
    No orbit data are fetched here. IERS auto-download is disabled for repeatability.
    """
    positions = np.asarray(positions_km, dtype=float)
    dates = to_datetime64(times).astype("datetime64[us]")
    if positions.shape != (len(dates), 3) or not np.isfinite(positions).all():
        raise ValueError("one finite three-dimensional TEME position is required per time")
    time = Time(dates, scale="utc")
    with iers.conf.set_temp("auto_download", False):
        states = TEME(CartesianRepresentation(positions.T * u.km), obstime=time)
        fixed = states.transform_to(ITRS(obstime=time)).cartesian.xyz.to_value(u.km).T
    return look_from(site, fixed)


def beam_offsets_deg(sightline_enu: np.ndarray, boresight_enu: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Signed beam-frame offsets: right/increasing azimuth and up/increasing elevation.

    Unlike separate R/I/C magnitudes, these retain all components of the actual
    line-of-sight displacement and their signs. At zenith the mounting azimuth is
    singular; track benchmarks should declare and enforce an elevation ceiling.
    """
    sight = np.asarray(sightline_enu, dtype=float)
    bore = np.asarray(boresight_enu, dtype=float)
    azimuth = np.arctan2(bore[..., 0], bore[..., 1])
    altitude = np.arctan2(bore[..., 2], np.hypot(bore[..., 0], bore[..., 1]))
    right = np.stack([np.cos(azimuth), -np.sin(azimuth), np.zeros_like(azimuth)], axis=-1)
    up = np.stack([-np.sin(altitude) * np.sin(azimuth), -np.sin(altitude) * np.cos(azimuth), np.cos(altitude)], axis=-1)
    depth = np.sum(sight * bore, axis=-1)
    x = np.degrees(np.arctan2(np.sum(sight * right, axis=-1), depth))
    y = np.degrees(np.arctan2(np.sum(sight * up, axis=-1), depth))
    return x, y


def enu_from_alt_az(alt_deg, az_deg) -> np.ndarray:
    """Unit vectors in the east-north-up frame from altitude and azimuth (north through east)."""
    alt = np.radians(np.asarray(alt_deg, dtype=float))
    az = np.radians(np.asarray(az_deg, dtype=float))
    return np.stack([np.cos(alt) * np.sin(az), np.cos(alt) * np.cos(az), np.sin(alt)], axis=-1)


def boresight(site: Site, ra_deg: float, dec_deg: float, times) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Altitude, azimuth (degrees) and ENU unit vectors of a J2000 direction at UTC ``times``, no refraction."""
    t = Time(to_datetime64(times), scale="utc")
    frame = AltAz(obstime=t, location=site.location(), pressure=0.0 * u.bar)
    with iers.conf.set_temp("iers_degraded_accuracy", "warn"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        altaz = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs").transform_to(frame)
    alt = np.atleast_1d(altaz.alt.to_value(u.deg))
    az = np.atleast_1d(altaz.az.to_value(u.deg))
    return alt, az, enu_from_alt_az(alt, az)


def sky_from_alt_az(site: Site, alt_deg, az_deg, times) -> tuple[np.ndarray, np.ndarray]:
    """J2000 right ascension and declination (degrees) of topocentric directions, no refraction."""
    t = Time(to_datetime64(times), scale="utc")
    frame = AltAz(
        alt=np.atleast_1d(alt_deg) * u.deg,
        az=np.atleast_1d(az_deg) * u.deg,
        obstime=t,
        location=site.location(),
        pressure=0.0 * u.bar,
    )
    with iers.conf.set_temp("iers_degraded_accuracy", "warn"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        icrs = SkyCoord(frame).transform_to(ICRS())
    return np.atleast_1d(icrs.ra.to_value(u.deg)), np.atleast_1d(icrs.dec.to_value(u.deg))


def separation_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Angle between unit vectors, stable near zero (chord rather than dot product)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    chord = np.linalg.norm(a - b, axis=-1)
    return np.degrees(2.0 * np.arcsin(np.clip(chord / 2.0, 0.0, 1.0)))


def sky_projection(unit: np.ndarray, line_of_sight: np.ndarray) -> np.ndarray:
    """How much of a unit direction lies across the line of sight: ``|u - (u.l) l|``, from 0 along it to 1 across."""
    unit = np.asarray(unit, dtype=float)
    los = np.asarray(line_of_sight, dtype=float)
    along = np.sum(unit * los, axis=-1, keepdims=True)
    return np.linalg.norm(unit - along * los, axis=-1)
