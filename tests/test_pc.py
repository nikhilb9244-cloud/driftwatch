"""Probability of collision: closed forms, the three integrators against each other and
against brute-force quadrature, the covariance-scale sweep, the encounter plane, the flags."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.integrate import dblquad
from scipy.stats import ncx2

from driftwatch.risk.pc import (
    confidences,
    encounter_plane,
    flags,
    max_pc_sweep,
    pc_alfano,
    pc_chan,
    pc_foster,
    principal_axes,
    regions,
    rotate_ric_to_teme,
)
from driftwatch.screening.ric import ric_basis

INTEGRATORS = (pc_foster, pc_alfano, pc_chan)


def isotropic(sigma: float, n: int = 1) -> np.ndarray:
    return np.tile(np.eye(2) * sigma**2, (n, 1, 1))


def rotated(sx: float, sy: float, angle_deg: float) -> np.ndarray:
    a = np.radians(angle_deg)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (rot @ np.diag([sx**2, sy**2]) @ rot.T)[None]


# --------------------------------------------------------------------------------------
# Closed forms


def test_zero_miss_isotropic_is_one_minus_exp():
    """Zero miss, isotropic sigma: Pc = 1 - exp(-R^2 / 2 sigma^2), the prompt's first check."""
    sigma = np.array([0.05, 0.1, 0.5, 2.0])
    radius = 0.02
    expected = 1.0 - np.exp(-(radius**2) / (2.0 * sigma**2))
    miss = np.zeros((4, 2))
    cov = np.stack([np.eye(2) * s**2 for s in sigma])
    for fn in INTEGRATORS:
        np.testing.assert_allclose(fn(miss, cov, radius), expected, rtol=1e-6)


@pytest.mark.parametrize("d_over_sigma", [0.0, 0.5, 1.0, 2.0, 3.0, 5.0])
@pytest.mark.parametrize("r_over_sigma", [0.01, 0.1, 0.5, 1.0])
@pytest.mark.parametrize("direction_deg", [0.0, 90.0, 210.0])
def test_offset_isotropic_matches_the_noncentral_chi_square(d_over_sigma, r_over_sigma, direction_deg):
    """An isotropic Gaussian's mass in a disc at distance d is a non-central chi-square with two degrees of freedom."""
    sigma = 0.3
    d = d_over_sigma * sigma
    radius = r_over_sigma * sigma
    expected = ncx2.cdf((radius / sigma) ** 2, df=2, nc=(d / sigma) ** 2)
    phi = np.radians(direction_deg)
    miss = np.array([[d * np.cos(phi), d * np.sin(phi)]])
    for fn in INTEGRATORS:
        np.testing.assert_allclose(fn(miss, isotropic(sigma), radius), [expected], rtol=2e-5, atol=1e-15)


# --------------------------------------------------------------------------------------
# Anisotropic: brute force, then the cross-check


def brute_force(miss: np.ndarray, cov: np.ndarray, radius: float) -> float:
    inv = np.linalg.inv(cov)
    norm = 1.0 / (2.0 * np.pi * np.sqrt(np.linalg.det(cov)))

    def pdf(y: float, x: float) -> float:
        d = np.array([x, y]) - miss
        return norm * np.exp(-0.5 * d @ inv @ d)

    value, _ = dblquad(
        pdf,
        -radius,
        radius,
        lambda x: -np.sqrt(radius**2 - x**2),
        lambda x: np.sqrt(radius**2 - x**2),
        epsabs=0,
        epsrel=1e-9,
    )
    return float(value)


@pytest.mark.parametrize(
    "sx, sy, angle, miss, radius",
    [
        (0.3, 0.05, 20.0, (0.1, 0.02), 0.03),
        (1.0, 0.1, 70.0, (0.2, 0.15), 0.08),
        (2.0, 0.2, 0.0, (1.0, 0.0), 0.05),
        (0.5, 0.5, 45.0, (0.0, 0.0), 0.4),
        (0.4, 0.02, 135.0, (0.05, 0.03), 0.02),
    ],
)
def test_foster_and_alfano_reproduce_brute_force_quadrature(sx, sy, angle, miss, radius):
    cov = rotated(sx, sy, angle)
    m = np.array([miss])
    expected = brute_force(m[0], cov[0], radius)
    np.testing.assert_allclose(pc_foster(m, cov, radius), [expected], rtol=1e-6)
    np.testing.assert_allclose(pc_alfano(m, cov, radius), [expected], rtol=1e-6)


@pytest.mark.parametrize("aspect", [1.0, 3.0, 10.0, 30.0, 100.0])
@pytest.mark.parametrize("angle_deg", [0.0, 30.0, 90.0])
@pytest.mark.parametrize(
    "d_over_smin, r_over_smin", [(0.0, 0.1), (1.0, 0.1), (3.0, 0.5), (2.0, 1.0), (6.0, 0.05), (0.3, 2.0)]
)
def test_foster_and_alfano_agree_within_one_percent(aspect, angle_deg, d_over_smin, r_over_smin):
    """The prompt's acceptance rule for the cross-check, over aspect ratios up to 100 and discs up to 2 sigma."""
    smin = 0.1
    cov = rotated(aspect * smin, smin, angle_deg)
    d = d_over_smin * smin
    miss = np.array([[d * np.cos(np.radians(40.0)), d * np.sin(np.radians(40.0))]])
    foster = pc_foster(miss, cov, r_over_smin * smin)[0]
    alfano = pc_alfano(miss, cov, r_over_smin * smin)[0]
    assert foster > 0 and alfano > 0
    assert abs(alfano / foster - 1.0) < 1e-2, (foster, alfano)


@pytest.mark.parametrize("aspect", [1.0, 3.0, 10.0, 30.0])
@pytest.mark.parametrize("d_over_smin", [0.0, 1.0, 3.0])
def test_chan_matches_where_the_disc_is_small_and_drifts_where_it_is_not(aspect, d_over_smin):
    """Chan's equal-area series is a third value: within one percent for a disc under a tenth of the smaller
    sigma, and visibly off (but the right order) when the disc is comparable to it."""
    smin = 0.1
    cov = rotated(aspect * smin, smin, 25.0)
    d = d_over_smin * smin
    miss = np.array([[d * np.cos(0.7), d * np.sin(0.7)]])
    small = 0.05 * smin
    ref = pc_foster(miss, cov, small)[0]
    assert abs(pc_chan(miss, cov, small)[0] / ref - 1.0) < 1e-2
    large = 1.5 * smin
    ref = pc_foster(miss, cov, large)[0]
    chan = pc_chan(miss, cov, large)[0]
    assert 0.3 < chan / ref < 3.0


def test_chan_far_out_underflows_to_zero_not_nan():
    miss = np.array([[100.0, 0.0]])
    out = pc_chan(miss, isotropic(0.1), 0.01)
    assert out[0] == 0.0
    assert np.isnan(pc_chan(miss, isotropic(np.nan), 0.01))[0]


# --------------------------------------------------------------------------------------
# The scale sweep and the flags


def test_scale_sweep_finds_the_dilution_maximum():
    """For a small disc and isotropic sigma_0, Pc(k) ~ (R^2 / 2 k sigma_0^2) exp(-d^2 / 2 k sigma_0^2), whose
    maximum over the scale factor k sits at k* = d^2 / (2 sigma_0^2)."""
    sigma0, d, radius = 0.1, 0.3, 0.005
    k_star = d**2 / (2.0 * sigma0**2)  # 4.5
    miss = np.array([[d, 0.0]])
    pc_max, scale, curve = max_pc_sweep(miss, isotropic(sigma0), radius)
    assert curve.shape == (1, 61)
    assert abs(scale[0] / k_star - 1.0) < 0.05
    expected = radius**2 / (2.0 * k_star * sigma0**2) * np.exp(-1.0)
    assert abs(pc_max[0] / expected - 1.0) < 0.02
    assert pc_max[0] >= pc_foster(miss, isotropic(sigma0), radius)[0]
    # The curve rises to the maximum and falls after it: dilution on the right, retreat on the left.
    idx = int(np.argmax(curve[0]))
    assert 0 < idx < 60 and np.all(np.diff(curve[0][:idx]) > 0) and np.all(np.diff(curve[0][idx:]) < 0)


def test_scale_sweep_when_the_uncertainty_is_already_too_large_or_too_small():
    d, radius = 0.3, 0.005
    miss = np.array([[d, 0.0]])
    # sigma_0 above d / sqrt(2): shrinking the covariance raises the probability.
    pc_max, scale, _ = max_pc_sweep(miss, isotropic(0.5), radius)
    assert scale[0] < 1.0 and abs(scale[0] / 0.18 - 1.0) < 0.06
    # sigma_0 so small that the maximum lies beyond the sweep: the edge is reported, nothing breaks.
    pc_max, scale, curve = max_pc_sweep(miss, isotropic(0.01), radius)
    assert scale[0] == pytest.approx(10.0) and pc_max[0] == pytest.approx(curve[0][-1], rel=1e-6)


def test_flags_use_the_iss_thresholds():
    pc = np.array([2e-4, 1e-4, 5e-5, 1e-5, 1e-6, np.nan])
    assert flags(pc).tolist() == ["red", "red", "yellow", "yellow", "none", "none"]


def test_region_is_dilution_below_a_scale_of_one_and_carries_the_confidence():
    scale = np.array([0.1, 0.5, 0.999, 1.0, 1.5, 10.0, np.nan])
    region = regions(scale)
    assert region.tolist() == ["dilution"] * 3 + ["robust"] * 3 + ["unknown"]
    assert confidences(region).tolist() == ["low"] * 3 + ["standard"] * 3 + ["low"]


def test_the_dilution_region_is_where_shrinking_the_covariance_would_raise_the_probability():
    """The label has to mean what it says, so check it against the curve rather than the number."""
    radius = 0.005
    for sigma, expected in ((0.5, "dilution"), (0.01, "robust")):
        miss = np.array([[0.3, 0.0]])
        cov = isotropic(sigma)
        pc_max, scale, _ = max_pc_sweep(miss, cov, radius)
        assert regions(scale)[0] == expected
        smaller = pc_foster(miss, cov * 0.5, radius)[0]
        here = pc_foster(miss, cov, radius)[0]
        assert (smaller > here) == (expected == "dilution")


# --------------------------------------------------------------------------------------
# Geometry


def test_encounter_plane_axes_are_orthonormal_and_perpendicular_to_the_relative_velocity():
    rng = np.random.default_rng(1)
    dr = rng.normal(size=(5, 3))
    dv = rng.normal(size=(5, 3)) * 7.0
    cov = rng.normal(size=(5, 3, 3))
    cov = cov @ np.transpose(cov, (0, 2, 1))
    plane = encounter_plane(dr, dv, cov)
    x, y = plane.axes_teme[:, 0], plane.axes_teme[:, 1]
    z = dv / np.linalg.norm(dv, axis=1, keepdims=True)
    np.testing.assert_allclose(np.einsum("ni,ni->n", x, z), 0.0, atol=1e-12)
    np.testing.assert_allclose(np.einsum("ni,ni->n", y, z), 0.0, atol=1e-12)
    np.testing.assert_allclose(np.einsum("ni,ni->n", x, y), 0.0, atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(x, axis=1), 1.0)
    perp = dr - np.einsum("ni,ni->n", dr, z)[:, None] * z
    np.testing.assert_allclose(plane.miss_km[:, 0], np.linalg.norm(perp, axis=1))
    np.testing.assert_allclose(plane.miss_km[:, 1], 0.0, atol=1e-12)
    expected = np.einsum("nai,nij,nbj->nab", plane.axes_teme, cov, plane.axes_teme)
    np.testing.assert_allclose(plane.cov_km2, expected)
    # A miss along the relative velocity projects to zero and still gets a finite plane.
    degenerate = encounter_plane(dv[:1] * 0.01, dv[:1], cov[:1])
    assert degenerate.miss_km[0, 0] == 0.0 and np.isfinite(degenerate.axes_teme).all()


def test_ric_covariance_rotates_to_teme_as_a_similarity_transform():
    r = np.array([[6800.0, 100.0, -50.0]])
    v = np.array([[0.1, 7.5, 0.3]])
    basis = ric_basis(r, v)
    cov_ric = np.diag([0.01, 1.0, 0.04])[None]
    cov_teme = rotate_ric_to_teme(basis, cov_ric)
    np.testing.assert_allclose(np.linalg.eigvalsh(cov_teme[0]), np.sort(np.diag(cov_ric[0])))
    back = np.einsum("nij,njk,nlk->nil", basis, cov_teme, basis)
    np.testing.assert_allclose(back, cov_ric, atol=1e-12)
    radial = basis[0, 0]
    assert radial @ cov_teme[0] @ radial == pytest.approx(0.01)


def test_principal_axes_diagonalise_the_covariance():
    cov = rotated(0.5, 0.1, 33.0)
    sx, sy, mx, my = principal_axes(cov, np.array([[0.2, 0.1]]))
    assert sorted([sx[0], sy[0]]) == pytest.approx([0.1, 0.5])
    assert mx[0] ** 2 + my[0] ** 2 == pytest.approx(0.2**2 + 0.1**2)
