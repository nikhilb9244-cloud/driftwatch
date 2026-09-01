"""Frame conversions against skyfield.

Skyfield is an independent implementation of the TEME -> ITRS rotation (GMST from UT1
plus polar motion) with its own IERS tables. Two comparisons are made:

* Against skyfield's rotation fed with astropy's Earth-orientation values. This must
  agree to millimetres and pins down matrix conventions and signs.
* Against skyfield's full pipeline with its default timescale, which carries UT1-UTC but
  no polar-motion table. The residual must then be explained by polar motion alone.

The GMST-only shortcut used in the browser is measured against the full conversion and
its error must be explained by the UT1-UTC offset (which scales with orbital radius) and
polar motion, so the approximation is characterised rather than guessed.
"""

from __future__ import annotations

from datetime import timedelta

import astropy.units as u
import numpy as np
import pytest
from astropy.time import Time
from astropy.utils.iers import earth_orientation_table
from sgp4.api import Satrec
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.framelib import itrs
from skyfield.sgp4lib import TEME_to_ITRF

from driftwatch.orbit.frames import EARTH_ROTATION_RATE, itrs_to_geodetic, teme_to_ecef_gmst_only, teme_to_itrs
from driftwatch.orbit.propagator import propagate_satrecs
from driftwatch.orbit.time import datetime64_to_datetime, to_datetime64

# Catalogue numbers from SGP4-VER.TLE spanning LEO, Molniya, GPS and geosynchronous.
SAMPLE_IDS = (6251, 8195, 28129, 23599, 25954)


@pytest.fixture(scope="module")
def ts():
    return load.timescale()


def _sample(verification_tles):
    by_id = {Satrec.twoline2rv(t.line1, t.line2).satnum: t for t in verification_tles}
    return [by_id[i] for i in SAMPLE_IDS if i in by_id]


def _epoch(sat: Satrec):
    us = int(round((sat.jdsatepoch + sat.jdsatepochF - 2440587.5) * 86400e6))
    return datetime64_to_datetime(np.datetime64(us, "us"))


def _eop(t):
    """UT1-UTC (s) and polar motion (rad) from astropy's IERS table at UTC ``t``."""
    at = Time(t, scale="utc")
    pmx, pmy = earth_orientation_table.get().pm_xy(at)
    return at, float(at.delta_ut1_utc), pmx.to_value(u.rad), pmy.to_value(u.rad)


def test_rotation_matches_skyfield_given_same_earth_orientation(verification_tles):
    worst = 0.0
    for tle in _sample(verification_tles):
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        for hours in (0.0, 1.5, 7.25, 23.0):
            t = _epoch(sat) + timedelta(hours=hours)
            state = propagate_satrecs([sat], np.array([sat.satnum]), to_datetime64([t]))
            assert state.error[0, 0] == 0
            r_teme, v_teme, _ = state.at_index(0)
            r_ours, v_ours = teme_to_itrs(r_teme, v_teme, t)
            at, _, xp, yp = _eop(t)
            # skyfield's helper wants velocity per day (its angular-rate term is per day).
            r_ref, v_ref_day = TEME_to_ITRF(at.ut1.jd1, r_teme[0], v_teme[0] * 86400.0, xp, yp, at.ut1.jd2)
            v_ref = v_ref_day / 86400.0
            worst = max(worst, float(np.max(np.abs(r_ours[0] - r_ref))))
            assert np.max(np.abs(v_ours[0] - v_ref)) < 1e-7  # km/s, i.e. 0.1 mm/s
    print(f"\nTEME->ITRS vs skyfield rotation (same EOP): max |dr| = {worst * 1e6:.3f} mm")
    assert worst < 1e-6  # 1 mm


def test_full_pipeline_residual_vs_skyfield_is_polar_motion(verification_tles, ts):
    assert ts.polar_motion_table is None, "skyfield's default timescale is expected to omit polar motion"
    worst_unexplained = -1.0
    for tle in _sample(verification_tles):
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        sky = EarthSatellite(tle.line1, tle.line2, ts=ts)
        for hours in (0.0, 7.25):
            t = _epoch(sat) + timedelta(hours=hours)
            state = propagate_satrecs([sat], np.array([sat.satnum]), to_datetime64([t]))
            r_teme, v_teme, _ = state.at_index(0)
            r_ours, _ = teme_to_itrs(r_teme, v_teme, t)
            r_ref, _ = sky.at(ts.from_datetime(t)).frame_xyz_and_velocity(itrs)
            residual = float(np.linalg.norm(r_ours[0] - r_ref.km))
            _, _, xp, yp = _eop(t)
            polar_bound = np.hypot(xp, yp) * float(np.linalg.norm(r_teme[0]))
            worst_unexplained = max(worst_unexplained, residual - polar_bound)
            assert residual < polar_bound + 0.002, (sat.satnum, residual, polar_bound)
    print(f"\nFull pipeline vs skyfield: residual beyond the polar-motion bound = {worst_unexplained * 1e3:.2f} m")


def test_gmst_only_error_is_explained_by_dut1_and_polar_motion(verification_tles):
    """The browser skips DUT1 and polar motion; the error must be exactly that and nothing else."""
    rows = []
    for tle in _sample(verification_tles):
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        t = _epoch(sat) + timedelta(hours=3)
        state = propagate_satrecs([sat], np.array([sat.satnum]), to_datetime64([t]))
        r_teme, v_teme, _ = state.at_index(0)
        r_full, v_full = teme_to_itrs(r_teme, v_teme, t)
        r_approx, v_approx = teme_to_ecef_gmst_only(r_teme, v_teme, t)
        residual = float(np.linalg.norm(r_full - r_approx))
        _, dut1, xp, yp = _eop(t)
        r_axis = float(np.hypot(r_teme[0, 0], r_teme[0, 1]))
        dut1_term = abs(dut1) * EARTH_ROTATION_RATE * r_axis
        polar_term = np.hypot(xp, yp) * float(np.linalg.norm(r_teme[0]))
        rows.append((sat.satnum, np.linalg.norm(r_teme[0]), residual, dut1_term, polar_term))
        assert residual < dut1_term + polar_term + 0.002
        assert residual > 0.5 * dut1_term  # a missing rotation would show up as a far larger residual
        # Both include the omega x r term, so velocities agree to the same rotation error.
        assert np.max(np.abs(v_full - v_approx)) < 1e-3
    print("\nGMST-only vs full ITRS (km): satnum, |r|, residual, DUT1 term, polar term")
    for row in rows:
        print(f"  {row[0]:6d} {row[1]:9.0f} {row[2]:8.4f} {row[3]:8.4f} {row[4]:8.4f}")


def test_geodetic_matches_skyfield_subpoint(verification_tles, ts):
    for tle in _sample(verification_tles):
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        sky = EarthSatellite(tle.line1, tle.line2, ts=ts)
        t = _epoch(sat) + timedelta(minutes=40)
        state = propagate_satrecs([sat], np.array([sat.satnum]), to_datetime64([t]))
        r_teme, v_teme, _ = state.at_index(0)
        r_itrs, _ = teme_to_itrs(r_teme, v_teme, t)
        lat, lon, height = itrs_to_geodetic(r_itrs)
        pos = sky.at(ts.from_datetime(t))
        sub = wgs84.subpoint_of(pos)
        assert abs(lat[0] - sub.latitude.degrees) < 1e-3
        dlon = (lon[0] - sub.longitude.degrees + 180) % 360 - 180
        assert abs(dlon) < 1e-3
        assert abs(height[0] - wgs84.height_of(pos).km) < 0.1


def test_nan_rows_pass_through():
    r = np.array([[7000.0, 0.0, 0.0], [np.nan, np.nan, np.nan]])
    v = np.array([[0.0, 7.5, 0.0], [np.nan, np.nan, np.nan]])
    r_out, v_out = teme_to_itrs(r, v, "2024-05-10T12:00:00Z")
    assert np.isfinite(r_out[0]).all() and np.isnan(r_out[1]).all()
    lat, lon, h = itrs_to_geodetic(r_out)
    assert np.isfinite(lat[0]) and np.isnan(lat[1])
