"""End-to-end sanity check on a real ISS element set.

The element set below is the live CelesTrak record for the ISS fetched on
2026-09-01. Several things must hold if the pipeline is honest:

* SGP4 puts the station at 400 to 440 km altitude at 7.6 to 7.7 km/s, period 92 to 93 min.
* Our geodetic sub-satellite point matches skyfield's.
* When skyfield says the ISS culminates over Durban (the University of KwaZulu-Natal),
  our Earth-fixed position, turned into elevation above Durban's horizon, agrees with
  skyfield to a tenth of a degree. This checks the whole chain from elements to a place
  on the ground at a stated time.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest
from skyfield.api import EarthSatellite, load, wgs84

from driftwatch.catalogue.snapshot import records_to_frame
from driftwatch.orbit.frames import itrs_to_geodetic, teme_to_itrs
from driftwatch.orbit.propagator import build_satrecs, mean_orbit_geometry, propagate_satrecs
from driftwatch.orbit.time import parse_utc, to_datetime64

ISS_OMM = {
    "OBJECT_NAME": "ISS (ZARYA)",
    "OBJECT_ID": "1998-067A",
    "EPOCH": "2026-09-01T11:57:51.489504",
    "MEAN_MOTION": 15.48958602,
    "ECCENTRICITY": 0.00050553,
    "INCLINATION": 51.6312,
    "RA_OF_ASC_NODE": 282.3953,
    "ARG_OF_PERICENTER": 96.474,
    "MEAN_ANOMALY": 263.6825,
    "EPHEMERIS_TYPE": 0,
    "CLASSIFICATION_TYPE": "U",
    "NORAD_CAT_ID": 25544,
    "ELEMENT_SET_NO": 999,
    "REV_AT_EPOCH": 58358,
    "BSTAR": 7.9223149e-05,
    "MEAN_MOTION_DOT": 3.91e-05,
    "MEAN_MOTION_DDOT": 0,
}

# Howard College campus, University of KwaZulu-Natal, Durban.
DURBAN_LAT, DURBAN_LON, DURBAN_H_M = -29.867, 30.980, 150.0


@pytest.fixture(scope="module")
def iss():
    frame = records_to_frame([ISS_OMM])
    return frame, build_satrecs(frame)[0]


def test_iss_orbit_is_physically_sensible(iss):
    frame, sat = iss
    geom = mean_orbit_geometry([sat])
    assert 380 < geom["perigee_km"][0] < 450
    assert 380 < geom["apogee_km"][0] < 450
    assert 92.0 < 1440.0 / frame["mean_motion"][0] < 93.5

    epoch = parse_utc(ISS_OMM["EPOCH"])
    times = [epoch + timedelta(minutes=m) for m in range(0, 24 * 60, 7)]
    state = propagate_satrecs([sat], np.array([25544]), to_datetime64(times))
    assert (state.error == 0).all()
    r = state.r_teme[0]
    v = state.v_teme[0]
    radius = np.linalg.norm(r, axis=1)
    speed = np.linalg.norm(v, axis=1)
    assert np.all((radius > 6378 + 380) & (radius < 6378 + 450))
    assert np.all((speed > 7.6) & (speed < 7.7))


def test_iss_subpoint_matches_skyfield(iss):
    _, sat = iss
    ts = load.timescale()
    sky = EarthSatellite.from_satrec(sat, ts)
    epoch = parse_utc(ISS_OMM["EPOCH"])
    for minutes in (0, 45, 300, 1400):
        t = epoch + timedelta(minutes=minutes)
        state = propagate_satrecs([sat], np.array([25544]), to_datetime64([t]))
        r_teme, v_teme, _ = state.at_index(0)
        r_itrs, _ = teme_to_itrs(r_teme, v_teme, t)
        lat, lon, h = itrs_to_geodetic(r_itrs)
        pos = sky.at(ts.from_datetime(t))
        sub = wgs84.subpoint_of(pos)
        assert abs(lat[0] - sub.latitude.degrees) < 2e-3
        assert abs((lon[0] - sub.longitude.degrees + 180) % 360 - 180) < 2e-3
        assert abs(h[0] - wgs84.height_of(pos).km) < 0.05
        assert 380 < h[0] < 450


def _elevation_deg(r_itrs_km: np.ndarray) -> float:
    """Elevation of an Earth-fixed position above Durban's local horizon."""
    lat = np.deg2rad(DURBAN_LAT)
    lon = np.deg2rad(DURBAN_LON)
    a = 6378.137
    e2 = 1 / 298.257223563 * (2 - 1 / 298.257223563)
    n = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    h = DURBAN_H_M / 1000.0
    site = np.array(
        [
            (n + h) * np.cos(lat) * np.cos(lon),
            (n + h) * np.cos(lat) * np.sin(lon),
            (n * (1 - e2) + h) * np.sin(lat),
        ]
    )
    up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    los = r_itrs_km - site
    return float(np.rad2deg(np.arcsin(np.dot(los, up) / np.linalg.norm(los))))


def test_iss_passes_over_durban_when_skyfield_says_it_does(iss):
    _, sat = iss
    ts = load.timescale()
    sky = EarthSatellite.from_satrec(sat, ts)
    durban = wgs84.latlon(DURBAN_LAT, DURBAN_LON, elevation_m=DURBAN_H_M)
    epoch = parse_utc(ISS_OMM["EPOCH"])
    t0 = ts.from_datetime(epoch)
    t1 = ts.from_datetime(epoch + timedelta(hours=36))
    times, events = sky.find_events(durban, t0, t1, altitude_degrees=10.0)
    culminations = [t for t, e in zip(times, events, strict=True) if e == 1]
    assert culminations, "the ISS should culminate above 10 degrees over Durban within 36 hours"

    checked = 0
    for t_sky in culminations[:3]:
        t = t_sky.utc_datetime()
        alt_sky, _, _ = (sky - durban).at(t_sky).altaz()
        state = propagate_satrecs([sat], np.array([25544]), to_datetime64([t]))
        r_teme, v_teme, _ = state.at_index(0)
        r_itrs, _ = teme_to_itrs(r_teme, v_teme, t)
        elevation = _elevation_deg(r_itrs[0])
        assert elevation > 10.0
        assert abs(elevation - alt_sky.degrees) < 0.1, (t, elevation, alt_sky.degrees)
        # Ground range at culmination: for elevation e and height h the sub-satellite
        # point is within roughly h / tan(e) of the site.
        lat, lon, h = itrs_to_geodetic(r_itrs)
        ground_km = _great_circle_km(lat[0], lon[0], DURBAN_LAT, DURBAN_LON)
        assert ground_km < h[0] / np.tan(np.deg2rad(elevation)) * 1.2 + 50
        checked += 1
    assert checked >= 1


def _great_circle_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = np.deg2rad(lat1), np.deg2rad(lat2)
    dl = np.deg2rad(lon2 - lon1)
    c = np.arccos(np.clip(np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dl), -1, 1))
    return float(6371.0 * c)
