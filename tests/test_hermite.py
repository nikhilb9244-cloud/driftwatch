"""The Hermite interpolant: exactness, the measured error, and the refusal to extrapolate.

The interpolant is the thing that lets Stage C refine on an operator's published states
instead of on an SGP4 fit to them, so what it costs has to be known rather than assumed. The
tests below check the two ends of that: it is exact on the polynomials it is built from, and
on a real orbit its error at held-out grid points matches the analytic bound
``a (omega h)^4 / 384`` -- which is what makes the 120-second stored grid defensible against
the 200 m fit residual it replaces.
"""

from __future__ import annotations

import numpy as np
import pytest

from driftwatch.ephemeris.hermite import HermiteSpline

MU_KM3_S2 = 398600.4418


def circular(t_s: np.ndarray, radius_km: float = 6871.0) -> tuple[np.ndarray, np.ndarray]:
    """A circular orbit and its exact derivative, sampled at ``t_s``."""
    omega = np.sqrt(MU_KM3_S2 / radius_km**3)
    angle = omega * np.asarray(t_s, dtype=float)
    u = np.array([1.0, 0.0, 0.0])
    w = np.array([0.0, np.cos(np.radians(53.0)), np.sin(np.radians(53.0))])
    r = radius_km * (np.cos(angle)[:, None] * u + np.sin(angle)[:, None] * w)
    v = radius_km * omega * (-np.sin(angle)[:, None] * u + np.cos(angle)[:, None] * w)
    return r, v


def test_it_passes_through_every_node_with_the_right_slope():
    t = np.array([0.0, 60.0, 120.0, 180.0])
    r, v = circular(t)
    spline = HermiteSpline(t, r, v)
    got_r, got_v = spline(t)
    np.testing.assert_allclose(got_r, r, atol=1e-12)
    np.testing.assert_allclose(got_v, v, atol=1e-12)


def test_it_is_exact_on_a_cubic_because_that_is_what_it_is():
    """A cubic Hermite reproduces any cubic exactly -- position and velocity both."""
    t = np.linspace(0.0, 300.0, 6)
    coefficients = np.array([[1.0, -2.0, 0.5], [3.0, 0.25, -1.0], [-0.5, 1.5, 2.0], [7.0, -3.0, 0.125]])
    r = sum(coefficients[k] * (t**k)[:, None] for k in range(4))
    v = sum(k * coefficients[k] * (t ** (k - 1))[:, None] for k in range(1, 4))
    spline = HermiteSpline(t, np.asarray(r), np.asarray(v))
    query = np.array([13.0, 77.0, 199.5, 288.0])
    expected_r = sum(coefficients[k] * (query**k)[:, None] for k in range(4))
    expected_v = sum(k * coefficients[k] * (query ** (k - 1))[:, None] for k in range(1, 4))
    got_r, got_v = spline(query)
    np.testing.assert_allclose(got_r, expected_r, rtol=1e-10)
    np.testing.assert_allclose(got_v, expected_v, rtol=1e-10)


@pytest.mark.parametrize("step_s", [60.0, 120.0, 300.0])
def test_the_held_out_error_follows_the_quartic_bound(step_s):
    """Hold out every other point of a 60-second orbit and measure: the bound is ``a (w h)^4 / 384``."""
    radius_km = 6871.0
    omega = np.sqrt(MU_KM3_S2 / radius_km**3)
    fine = np.arange(0, 6 * 3600, 60.0)
    r_fine, v_fine = circular(fine, radius_km)

    stride = int(step_s // 60)
    kept = np.arange(0, len(fine), stride)
    held = np.setdiff1d(np.arange(len(fine)), kept)
    held = held[(held >= kept[0]) & (held <= kept[-1])]
    spline = HermiteSpline(fine[kept], r_fine[kept], v_fine[kept])
    if not len(held):  # stride 1 holds nothing out; the nodes are exact and that is the point
        np.testing.assert_allclose(spline(fine[kept])[0], r_fine[kept], atol=1e-12)
        return

    error_km = np.linalg.norm(spline(fine[held])[0] - r_fine[held], axis=1)
    bound_km = radius_km * (omega * step_s) ** 4 / 384.0
    # Within a factor of two of the analytic bound, either way: the bound is a worst case over
    # the interval and the held-out points sit at its midpoints, where the error is largest.
    assert 0.5 * bound_km < np.median(error_km) < 2.0 * bound_km
    # And the number that matters: at the shipped grid it is small against the 0.2 km fit
    # residual removing it is meant to buy.
    if step_s <= 120.0:
        assert error_km.max() < 0.02


def test_it_returns_nan_outside_the_table_rather_than_extrapolating():
    """Past the end of a published ephemeris there is no information, and none is invented."""
    t = np.arange(0.0, 600.0, 60.0)
    r, v = circular(t)
    spline = HermiteSpline(t, r, v)
    query = np.array([-1.0, 0.0, 300.0, 540.0, 541.0])
    got_r, got_v = spline(query)
    assert np.isnan(got_r[0]).all() and np.isnan(got_v[0]).all()
    assert np.isnan(got_r[4]).all()
    assert np.isfinite(got_r[1:4]).all()
    np.testing.assert_array_equal(spline.covers(query), [False, True, True, True, False])
    assert spline.span_s == (0.0, 540.0)


def test_a_grid_that_is_not_a_grid_is_refused():
    t = np.array([0.0, 60.0, 60.0, 120.0])
    r, v = circular(t)
    with pytest.raises(ValueError, match="strictly increasing"):
        HermiteSpline(t, r, v)
    with pytest.raises(ValueError, match="at least two"):
        HermiteSpline(t[:1], r[:1], v[:1])
    with pytest.raises(ValueError, match="expected"):
        HermiteSpline(t, r[:2], v)


def test_an_uneven_grid_is_interpolated_on_its_own_spacing():
    """The stored grid is even inside a segment but a segment's last interval need not be."""
    t = np.array([0.0, 120.0, 240.0, 300.0])  # the last interval is half the others
    r, v = circular(t)
    spline = HermiteSpline(t, r, v)
    query = np.array([270.0])
    truth_r, _ = circular(query)
    assert np.linalg.norm(spline(query)[0][0] - truth_r[0]) < 1e-3
