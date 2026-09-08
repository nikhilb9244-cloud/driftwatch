"""Physical counterexamples and numerical checks for paired beam-track classification."""

import hashlib
import json

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import ITRS, TEME, CartesianRepresentation
from astropy.time import Time
from astropy.utils import iers

from driftwatch.radio import crossings, horizon, site


def gaussian(x, y):
    return np.exp(-np.log(2) * (np.asarray(x) ** 2 + np.asarray(y) ** 2))


def straight_track(times, *, impact=0.0, delay=0.0):
    """An independently specified tangent-plane passage; half-power radius is one degree."""
    t = np.asarray(times, dtype=float)
    bore = np.tile([0, np.cos(np.pi / 4), np.sin(np.pi / 4)], (len(t), 1))
    right, up = np.array([1, 0, 0]), np.array([0, -np.sin(np.pi / 4), np.cos(np.pi / 4)])
    x = np.tan(np.deg2rad((t - delay) * 0.1))
    y = np.tan(np.deg2rad(impact))
    sight = bore + x[:, None] * right + y * up
    return crossings.SkyTrack(t, sight, bore)


def compare(prediction, reference, **kwargs):
    return crossings.compare_sky_tracks(
        prediction, reference, gaussian, beam_record={"kind": "constructed test beam"}, **kwargs
    )


def test_near_misses_are_evaluated_in_both_directions():
    t = np.arange(-30.0, 31.0)
    inside, outside = straight_track(t, impact=0.99), straight_track(t, impact=1.01)
    false = compare(inside, outside)
    assert false.false_crossing and not false.missed_crossing
    assert false.prediction.peak_normalized_power > 0.5 > false.reference.peak_normalized_power
    missed = compare(outside, inside)
    assert missed.missed_crossing and not missed.false_crossing
    assert not missed.observation_edge_mismatch
    assert missed.reference.closest_separation_deg == pytest.approx(0.99, abs=1e-6)


def test_entry_exit_and_observation_edge_timing_are_separate_from_full_track_geometry():
    t = np.arange(-40.0, 61.0)
    result = compare(straight_track(t, delay=25), straight_track(t), observation_interval_s=(-15, 10))
    assert result.missed_crossing and result.observation_edge_mismatch
    assert result.closest_time_error_s == pytest.approx(25, abs=0.005)
    assert result.entry_time_error_s == pytest.approx(25, abs=0.005)
    assert result.exit_time_error_s == pytest.approx(25, abs=0.005)
    assert len(result.prediction.intervals) == len(result.reference.intervals) == 1
    full = compare(straight_track(t, delay=25), straight_track(t))
    assert full.both_crossed and not full.false_crossing and not full.missed_crossing


def test_interpolation_cadence_converges_for_a_short_grazing_passage():
    coarse = np.arange(-20.0, 21.0, 1.0)
    fine = np.arange(-20.0, 20.01, 0.25)
    a = compare(straight_track(coarse, impact=0.999, delay=0.43), straight_track(coarse, impact=0.995))
    b = compare(straight_track(fine, impact=0.999, delay=0.43), straight_track(fine, impact=0.995))
    assert a.both_crossed and b.both_crossed
    assert a.entry_time_error_s == pytest.approx(b.entry_time_error_s, abs=0.002)
    assert a.exit_time_error_s == pytest.approx(b.exit_time_error_s, abs=0.002)


def test_search_span_censors_boundary_intervals_and_refuses_extrapolation():
    t = np.arange(0.0, 21)
    result = compare(straight_track(t), straight_track(t, delay=1))
    assert result.prediction.intervals[0].entry_censored
    assert result.prediction.closest_time_censored
    assert result.entry_time_error_s is None
    with pytest.raises(ValueError, match="extrapolation"):
        straight_track(t).directions(-1)
    with pytest.raises(ValueError, match="observation interval"):
        compare(straight_track(t), straight_track(t), observation_interval_s=(-1, 10))


def test_pure_orbital_phase_delay_can_miss_a_fixed_beam_when_observer_rotates():
    # Analytic circular orbit in one plane; its residual has identically zero orbital C.
    # Compare in an inertial orthonormal basis: a circular response is rotation invariant.
    t = np.arange(-40.0, 100.1, 0.5)
    lat, radius, altitude = np.deg2rad(-30.7110556), 6378.137, 500.0
    up = np.array([np.cos(lat), 0, np.sin(lat)])
    north = np.array([-np.sin(lat), 0, np.cos(lat)])
    normal = np.cross(up, north)
    omega, mean_motion = 7.292115e-5, np.sqrt(398600.4418 / (radius + altitude) ** 3)

    def orbit(seconds):
        phase = mean_motion * seconds
        return (radius + altitude) * (np.cos(phase)[:, None] * up + np.sin(phase)[:, None] * north)

    observer = radius * np.column_stack(
        [np.cos(lat) * np.cos(omega * t), np.cos(lat) * np.sin(omega * t), np.full(len(t), np.sin(lat))]
    )
    basis = np.stack([normal, north, up])
    bore = np.tile(up @ basis.T, (len(t), 1))
    predicted, truth = orbit(t), orbit(t - 25)
    assert np.max(np.abs((predicted - truth) @ normal)) < 1e-10
    p = crossings.SkyTrack(t, (predicted - observer) @ basis.T, bore)
    r = crossings.SkyTrack(t, (truth - observer) @ basis.T, bore)
    result = compare(p, r)
    assert result.false_crossing and not result.observation_edge_mismatch
    assert 1.1 < result.reference.closest_separation_deg < 1.2


def test_full_teme_transform_preserves_all_components_and_subtracts_rotating_observer():
    times = np.array(["2024-04-23T20:40:00", "2024-04-23T20:41:00"], dtype="datetime64[us]")
    # Construct known ENU rays in ITRS, then independently transform to TEME.
    rays = np.array([[100, 200, 500], [-50, 150, 600]], dtype=float)
    fixed = site.MEERKAT.ecef_km() + rays @ site.MEERKAT.enu_basis()
    tm = Time(times, scale="utc")
    with iers.conf.set_temp("auto_download", False):
        teme = ITRS(CartesianRepresentation(fixed.T * u.km), obstime=tm).transform_to(TEME(obstime=tm))
    observed = site.look_from_teme(site.MEERKAT, teme.cartesian.xyz.to_value(u.km).T, times)
    assert np.allclose(observed.range_km, np.linalg.norm(rays, axis=1), atol=1e-8)
    assert np.allclose(observed.enu, rays / np.linalg.norm(rays, axis=1)[:, None], atol=1e-10)
    wrong_time = site.look_from_teme(site.MEERKAT, teme.cartesian.xyz.to_value(u.km).T, np.repeat(times[0], 2))
    assert site.separation_deg(observed.enu[1], wrong_time.enu[1]) > 1


def test_measured_jones_response_uses_cross_polarization_and_published_vertical_flip(tmp_path):
    axis = np.array([-1.0, 0.0, 1.0])
    jones = np.zeros((4, 3, 3), dtype=complex)
    jones[1, 0, 2] = 2  # pure cross-polar response at source Y=-1, X=+1
    beam = site.MeasuredBeam(axis, jones, {"frequency_mhz": 3499.1455078125})
    assert beam.power(1, 1) == 1 and beam.power(1, -1) == 0
    assert beam.power(0, 1) == 0 and beam.power(2, 1) == 0
    path = tmp_path / "beam.npz"
    np.savez(path, jones=jones, margin_deg=axis)
    path.with_suffix(".json").write_text(
        json.dumps({"frequency_mhz": 3499.1455078125, "cache_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    )
    assert site.MeasuredBeam.load(path).frequency_mhz == 3499.1455078125
    path.write_bytes(path.read_bytes() + b"altered")
    with pytest.raises(ValueError, match="hash"):
        site.MeasuredBeam.load(path)


def test_measured_diametric_width_recovers_rotated_elliptical_half_power_cuts():
    axis = np.linspace(-2, 2, 257)
    x, y = np.meshgrid(axis, -axis)
    theta = np.deg2rad(30)
    along = x * np.cos(theta) + y * np.sin(theta)
    across = -x * np.sin(theta) + y * np.cos(theta)
    voltage = np.exp(-2 * np.log(2) * ((along / 1.0) ** 2 + (across / 1.4) ** 2))
    jones = np.stack([voltage, voltage * 0, voltage * 0, voltage]).astype(complex)
    beam = site.MeasuredBeam(axis, jones, {"frequency_mhz": 3499.1455078125})
    widths = horizon.measured_half_power_widths(beam)
    assert widths["minimum_diametric_width_deg"] == pytest.approx(1.0, abs=0.0005)
    assert widths["maximum_diametric_width_deg"] == pytest.approx(1.4, abs=0.0005)
    assert widths["minimum_width_orientation_deg"] == pytest.approx(30, abs=0.5)
    assert widths["maximum_width_orientation_deg"] == pytest.approx(120, abs=0.5)


def test_primary_scalar_columns_above_3ghz_require_measured_width_and_actual_channel():
    columns = [c for c in horizon.table_columns() if c.freq_mhz > 3000]
    assert [c.freq_mhz for c in columns] == [3062.5, 3499.1455078125]
    for column in columns:
        assert column.beam_model.startswith("measured Jones")
        assert column.fwhm_deg == column.beam_metadata["minimum_diametric_width_deg"]
        assert column.fwhm_deg < column.beam_metadata["maximum_diametric_width_deg"]
        assert len(column.beam_metadata["cache_sha256"]) == 64
        assert not np.isclose(column.fwhm_deg, site.beam_fwhm_deg(column.freq_mhz), rtol=0.02)
    with pytest.raises(ValueError, match="fallback is not permitted"):
        horizon.receiver_column(site.RECEIVERS["S4"], 3400)
