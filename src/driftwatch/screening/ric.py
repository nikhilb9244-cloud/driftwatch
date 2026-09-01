"""The primary's radial, in-track, cross-track (RIC) frame, and relative vectors in it.

Physics note. A conjunction is described in the frame of the object we care about rather
than in TEME, because that frame separates the parts of a miss that mean different things:

* **Radial (R)**: along the primary's position vector, outward from the Earth's centre.
  A radial miss is a difference in altitude, which the orbit's energy sets and drag
  slowly changes.
* **In-track (I)**: in the orbital plane, perpendicular to R, roughly along the velocity
  (exactly along it for a circular orbit). In-track is where timing errors appear: an
  object that is early or late on its orbit is displaced along I. Drag errors grow here,
  which is why Phase 3 adds its storm term to this component.
* **Cross-track (C)**: along the orbital angular momentum, normal to the orbital plane.
  A cross-track miss is a difference in orbital plane.

The set is right-handed, R x I = C. It is the frame the ESA Kelvins dataset calls RTN
(radial, transverse, normal) and Vallado calls RSW. The basis is built from the primary's
osculating position and velocity at the time of interest, so it is an instantaneous frame:
it rotates with the primary, once per orbit.
"""

from __future__ import annotations

import numpy as np


def ric_basis(r: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Unit vectors of the RIC frame for each state.

    ``r`` and ``v`` have shape ``(n, 3)`` in any consistent units. Returns ``(n, 3, 3)``
    where ``basis[k, 0]``, ``basis[k, 1]`` and ``basis[k, 2]`` are the R, I and C unit
    vectors of state ``k`` expressed in the input frame. Rows with a zero or non-finite
    position or angular momentum come back as NaN.
    """
    r = np.asarray(r, dtype=float)
    v = np.asarray(v, dtype=float)
    if r.ndim == 1:
        r = r[None, :]
        v = v[None, :]
    h = np.cross(r, v)
    with np.errstate(invalid="ignore", divide="ignore"):
        radial = r / np.linalg.norm(r, axis=1, keepdims=True)
        cross = h / np.linalg.norm(h, axis=1, keepdims=True)
    in_track = np.cross(cross, radial)
    return np.stack([radial, in_track, cross], axis=1)


def to_ric(basis: np.ndarray, vec: np.ndarray) -> np.ndarray:
    """Components of ``vec`` ``(n, 3)`` in the frames ``basis`` ``(n, 3, 3)``: ``(n, 3)`` as (R, I, C)."""
    return np.einsum("nij,nj->ni", basis, np.asarray(vec, dtype=float))


def relative_ric(r_primary: np.ndarray, v_primary: np.ndarray, r_other: np.ndarray) -> np.ndarray:
    """Position of ``r_other`` relative to the primary, in the primary's RIC frame, ``(n, 3)``."""
    basis = ric_basis(r_primary, v_primary)
    delta = np.asarray(r_other, dtype=float) - np.asarray(r_primary, dtype=float)
    if delta.ndim == 1:
        delta = delta[None, :]
    return to_ric(basis, delta)
