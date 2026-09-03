"""Cubic Hermite interpolation of a tabulated position and velocity history.

Why Hermite and not Lagrange. An ephemeris file gives position *and* velocity at every
grid point, and velocity is the derivative of the quantity being interpolated. A cubic
Hermite interpolant uses both, matching value and slope at each end of an interval, and
its error on a smooth function is ``h^4 |f''''| / 384``. A Lagrange fit through positions
alone throws the velocities away and needs a much higher order -- and therefore a much
wider stencil, which is worse near the ends of the file -- to reach the same accuracy.

The error, for an orbit. Take the worst case, a circular low Earth orbit as a sinusoid of
amplitude ``a = 6,900 km`` and angular rate ``omega = 1.1e-3 rad/s``: ``|f''''| = a
omega^4``, so the bound is ``a (omega h)^4 / 384``. At a 60-second grid that is 0.3 m, at
120 seconds 5 m, at 300 seconds 210 m. The last is the same size as the thing this whole
exercise exists to remove, which is why the stored grid is fine rather than coarse; the
measured error against held-out grid points is in ``docs/spacex-ephemerides.md``.

The interpolant is ``C^1`` -- it matches velocity at the nodes -- but not ``C^2``, so
acceleration jumps across a node. Nothing here differentiates twice: Stage C wants
position and velocity, and the range-rate root finder wants a continuous ``dr . dv``,
which this gives.
"""

from __future__ import annotations

import numpy as np

__all__ = ["HermiteSpline"]


class HermiteSpline:
    """Position and velocity at any time inside a tabulated state history.

    ``t_s`` is seconds from an arbitrary origin, strictly increasing; ``r`` and ``v`` are
    ``(n, 3)`` in km and km/s. The grid does not have to be uniform. Query times outside
    ``[t_s[0], t_s[-1]]`` return NaN rather than extrapolating: past the end of a published
    ephemeris there is no information, and a silent extrapolation is exactly the kind of
    thing that turns into a number nobody can trace.
    """

    def __init__(self, t_s: np.ndarray, r_km: np.ndarray, v_kms: np.ndarray) -> None:
        t = np.asarray(t_s, dtype=float)
        r = np.asarray(r_km, dtype=float)
        v = np.asarray(v_kms, dtype=float)
        if t.ndim != 1 or r.shape != (t.size, 3) or v.shape != (t.size, 3):
            raise ValueError(f"expected t (n,), r (n, 3), v (n, 3); got {t.shape}, {r.shape}, {v.shape}")
        if t.size < 2:
            raise ValueError("a Hermite interpolant needs at least two grid points")
        if not np.all(np.diff(t) > 0):
            raise ValueError("the time grid must be strictly increasing")
        self.t_s = t
        self.r_km = r
        self.v_kms = v

    @property
    def span_s(self) -> tuple[float, float]:
        return float(self.t_s[0]), float(self.t_s[-1])

    def covers(self, t_s: np.ndarray) -> np.ndarray:
        """Which query times lie inside the tabulated span."""
        t = np.asarray(t_s, dtype=float)
        return np.isfinite(t) & (t >= self.t_s[0]) & (t <= self.t_s[-1])

    def __call__(self, t_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """``(r, v)`` in km and km/s at the query times, NaN where the table does not reach."""
        t = np.atleast_1d(np.asarray(t_s, dtype=float))
        r_out = np.full((t.size, 3), np.nan)
        v_out = np.full((t.size, 3), np.nan)
        inside = self.covers(t)
        if not inside.any():
            return r_out, v_out

        tq = t[inside]
        # searchsorted with 'right' puts a query exactly on a node in the interval to its
        # left; clipping keeps the last node inside the final interval rather than past it.
        j = np.clip(np.searchsorted(self.t_s, tq, side="right") - 1, 0, self.t_s.size - 2)
        t0 = self.t_s[j]
        h = self.t_s[j + 1] - t0
        s = (tq - t0) / h
        s2 = s * s
        s3 = s2 * s
        # The Hermite basis on [0, 1], and its derivative with respect to s.
        h00 = 2 * s3 - 3 * s2 + 1
        h10 = s3 - 2 * s2 + s
        h01 = -2 * s3 + 3 * s2
        h11 = s3 - s2
        d00 = 6 * s2 - 6 * s
        d10 = 3 * s2 - 4 * s + 1
        d01 = -6 * s2 + 6 * s
        d11 = 3 * s2 - 2 * s

        r0, r1 = self.r_km[j], self.r_km[j + 1]
        v0, v1 = self.v_kms[j], self.v_kms[j + 1]
        hh = h[:, None]
        r_out[inside] = h00[:, None] * r0 + h10[:, None] * hh * v0 + h01[:, None] * r1 + h11[:, None] * hh * v1
        v_out[inside] = (d00[:, None] * r0 + d01[:, None] * r1) / hh + d10[:, None] * v0 + d11[:, None] * v1
        return r_out, v_out
