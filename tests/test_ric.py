"""The RIC frame: axes where expected, right-handed, orthonormal, and relative vectors project correctly."""

import numpy as np

from driftwatch.screening.ric import relative_ric, ric_basis, to_ric


def test_circular_equatorial_orbit_axes():
    r = np.array([[7000.0, 0.0, 0.0]])
    v = np.array([[0.0, 7.5, 0.0]])
    basis = ric_basis(r, v)[0]
    np.testing.assert_allclose(basis[0], [1, 0, 0], atol=1e-15)  # radial: along r
    np.testing.assert_allclose(basis[1], [0, 1, 0], atol=1e-15)  # in-track: along v for a circular orbit
    np.testing.assert_allclose(basis[2], [0, 0, 1], atol=1e-15)  # cross-track: along r x v


def test_orthonormal_and_right_handed_for_random_states():
    rng = np.random.default_rng(1)
    r = rng.normal(size=(50, 3)) * 7000.0
    v = rng.normal(size=(50, 3)) * 7.0
    basis = ric_basis(r, v)
    gram = np.einsum("nij,nkj->nik", basis, basis)
    np.testing.assert_allclose(gram, np.broadcast_to(np.eye(3), gram.shape), atol=1e-12)
    np.testing.assert_allclose(np.cross(basis[:, 0], basis[:, 1]), basis[:, 2], atol=1e-12)
    # C is along the angular momentum, so r and v both lie in the R-I plane.
    np.testing.assert_allclose(np.einsum("ni,ni->n", basis[:, 2], v), 0.0, atol=1e-9)


def test_in_track_is_velocity_direction_only_when_circular():
    r = np.array([[7000.0, 0.0, 0.0]])
    v = np.array([[1.0, 7.5, 0.0]])  # a radial velocity component: eccentric orbit
    basis = ric_basis(r, v)[0]
    v_ric = to_ric(basis[None], v)[0]
    assert v_ric[0] > 0 and v_ric[1] > 0 and abs(v_ric[2]) < 1e-12


def test_relative_ric_of_an_in_track_offset():
    r = np.array([[0.0, 7000.0, 0.0]])
    v = np.array([[-7.5, 0.0, 0.0]])
    other = r + 1.0 * v / np.linalg.norm(v)  # 1 km ahead along the velocity
    ric = relative_ric(r, v, other)[0]
    np.testing.assert_allclose(ric, [0.0, 1.0, 0.0], atol=1e-12)


def test_degenerate_state_gives_nan_not_an_exception():
    basis = ric_basis(np.zeros((1, 3)), np.ones((1, 3)))
    assert np.isnan(basis).all()
