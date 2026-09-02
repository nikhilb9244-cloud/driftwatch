"""Probability of collision on the encounter plane.

The two-dimensional method. Near the time of closest approach the relative motion of
two objects in LEO is a straight line at constant velocity (the encounter lasts a
fraction of a second; gravity bends the relative path by micrometres). Project the
combined position uncertainty, the sum of both objects' covariances, onto the plane
perpendicular to the relative velocity; the probability that the two spheres touch is
the probability mass of that two-dimensional Gaussian inside a disc whose radius is the
sum of the two hard-body radii, centred on the miss vector. Three ways to evaluate the
same integral are implemented:

* :func:`pc_foster`: Foster and Estes (1992), numerical integration of the Gaussian
  over the disc on a polar grid (Gauss-Legendre in radius, a uniform grid in angle,
  which is spectrally accurate for a periodic integrand). This is the reference value.
* :func:`pc_alfano`: Alfano (2005), the disc integral reduced to one dimension along a
  principal axis of the covariance, the other dimension done in closed form with error
  functions. With the substitution ``x = R sin(phi)`` the integrand is smooth and a few
  dozen Gauss-Legendre nodes give ten digits. Must agree with Foster within one percent.
* :func:`pc_chan`: Chan (2008), an analytical series after replacing the ellipse of
  equal probability by a circle of equal area. Exact for an isotropic covariance and
  very accurate when the disc is small against the uncertainty; it drifts when the
  disc radius is comparable to the smaller standard deviation. Reported as a third
  value so the reader can see where the approximation holds.

The scale sweep. Alfano's dilution: for a fixed miss, the probability is not monotonic
in the uncertainty. Shrink the covariance and the Gaussian pulls away from the disc;
inflate it and the mass spreads thin; the maximum sits at a standard deviation of the
order of the miss distance. :func:`max_pc_sweep` scales the combined covariance by
factors from 0.1 to 10 and reports the largest probability and the factor at which it
occurs. When the empirical covariance is a floor on the true error (see ``covariance``)
the maximum is the honest upper bound.

Where the straight-line assumption stops. It holds because the encounter is over in a
fraction of a second while the geometry turns over on an orbital period. Two objects in
nearly the same orbit -- two members of one constellation, a satellite and its own upper
stage -- pass each other at metres per second instead of kilometres, and then the passage
takes minutes and the relative path curves through it. :func:`slow_encounters` flags the
events below :data:`SLOW_ENCOUNTER_KMS`. Their probability is a known underestimate: the
pair lingers near the closest approach and can re-approach, so more of the uncertainty is in
play than one plane sees. Nothing here corrects it -- the fix is a three-dimensional
integration -- so the flag is carried through to the output and the report instead.

Note what a large in-track uncertainty is *not*. A seven-day-old element set can be hundreds
of kilometres uncertain along track, but that is mostly a timing error: the object is on the
same track, early or late. Projecting the covariance onto the plane perpendicular to the
relative velocity discards exactly that component, which is why the method survives a large
in-track sigma and fails on a low relative speed instead.

Flags follow NASA's practice for the ISS: red at a probability of 1e-4 or above, yellow
at 1e-5 (the level at which the ISS programme starts planning an avoidance manoeuvre).

The scale at which the maximum occurs classifies the event. Below one, the probability
would rise if the covariance shrank: the uncertainty is already past the peak, the
probability is being held up by the size of the covariance rather than by the geometry,
and no judgement about the encounter can rest on it. That is the dilution region, and a
flag raised there is reported with low confidence and is never actionable. At or above
one the probability is limited by the geometry rather than by the uncertainty, which is
the regime the thresholds were written for.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.special import erfc, gammainc, gammaln

RED_PC = 1e-4
YELLOW_PC = 1e-5
DEFAULT_SCALES: np.ndarray = np.logspace(-1.0, 1.0, 61)
TWO_PI = 2.0 * np.pi
# Below this relative speed the straight-line assumption is gone. At 0.1 km/s a pair takes
# 100 seconds to cross 10 km of separation, and in 100 seconds a low Earth orbit turns
# through about 6 degrees, so the relative path curves appreciably over the passage. At the
# 7 to 15 km/s of an ordinary crossing conjunction the same traverse takes about a second and
# the rotation is under a twentieth of a degree, which is why the method works at all. Slow
# encounters in low Earth orbit are almost always two members of one constellation, or a
# satellite and its own upper stage, in nearly the same orbit.
SLOW_ENCOUNTER_KMS = 0.1


def rotate_ric_to_teme(basis: np.ndarray, cov_ric: np.ndarray) -> np.ndarray:
    """``C_teme = B^T C_ric B`` for RIC bases ``basis`` ``(n, 3, 3)`` whose rows are the R, I, C unit vectors."""
    return np.einsum("nji,njk,nkl->nil", basis, cov_ric, basis)


@dataclass(frozen=True)
class EncounterPlane:
    """What the integrators need: the miss and the covariance in the plane perpendicular to the relative velocity.

    ``miss_km`` is ``(n, 2)`` and by construction ``(d, 0)``: the x axis of the plane points
    along the miss vector. ``axes_teme`` ``(n, 2, 3)`` holds the two plane axes in TEME so a
    viewer can draw the ellipse and the disc in the right orientation.
    """

    miss_km: np.ndarray
    cov_km2: np.ndarray
    axes_teme: np.ndarray


def encounter_plane(dr_km: np.ndarray, dv_kms: np.ndarray, cov_teme_km2: np.ndarray) -> EncounterPlane:
    """Project the relative position and the combined covariance onto the plane perpendicular to ``dv``."""
    dr = np.atleast_2d(np.asarray(dr_km, dtype=float))
    dv = np.atleast_2d(np.asarray(dv_kms, dtype=float))
    cov = np.asarray(cov_teme_km2, dtype=float).reshape(len(dr), 3, 3)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = dv / np.linalg.norm(dv, axis=1, keepdims=True)
        x = dr - np.einsum("ni,ni->n", dr, z)[:, None] * z
        nx = np.linalg.norm(x, axis=1)
        degenerate = ~(nx > 1e-9)
        if degenerate.any():
            # Zero miss: any direction perpendicular to the relative velocity will do.
            helper = np.zeros_like(z)
            helper[np.arange(len(z)), np.argmin(np.abs(z), axis=1)] = 1.0
            alt = helper - np.einsum("ni,ni->n", helper, z)[:, None] * z
            x = np.where(degenerate[:, None], alt, x)
            nx = np.where(degenerate, np.linalg.norm(alt, axis=1), nx)
        x = x / nx[:, None]
    y = np.cross(z, x)
    axes = np.stack([x, y], axis=1)
    cov2 = np.einsum("nai,nij,nbj->nab", axes, cov, axes)
    miss = np.zeros((len(dr), 2))
    miss[:, 0] = np.where(degenerate, 0.0, nx) if degenerate.any() else nx
    return EncounterPlane(miss, cov2, axes)


def principal_axes(cov2: np.ndarray, miss2: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Rotate into the covariance's principal axes: ``(sigma_x, sigma_y, miss_x, miss_y)``."""
    a = cov2[:, 0, 0]
    b = cov2[:, 0, 1]
    c = cov2[:, 1, 1]
    theta = 0.5 * np.arctan2(2.0 * b, a - c)
    ct, st = np.cos(theta), np.sin(theta)
    var_x = a * ct**2 + 2.0 * b * ct * st + c * st**2
    var_y = a * st**2 - 2.0 * b * ct * st + c * ct**2
    mx = ct * miss2[:, 0] + st * miss2[:, 1]
    my = -st * miss2[:, 0] + ct * miss2[:, 1]
    with np.errstate(invalid="ignore"):
        return np.sqrt(np.maximum(var_x, 0.0)), np.sqrt(np.maximum(var_y, 0.0)), mx, my


def _as_arrays(miss2, cov2, radius_km) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    miss2 = np.atleast_2d(np.asarray(miss2, dtype=float))
    cov2 = np.asarray(cov2, dtype=float).reshape(len(miss2), 2, 2)
    radius = np.broadcast_to(np.asarray(radius_km, dtype=float), (len(miss2),)).astype(float)
    return miss2, cov2, radius


def _resolution_ratio(radius: np.ndarray, sx: np.ndarray, sy: np.ndarray) -> float:
    """Disc radius over the smallest standard deviation, the number that sets the grid density."""
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = radius / np.minimum(sx, sy)
    ratio = ratio[np.isfinite(ratio)]
    return float(ratio.max()) if len(ratio) else 1.0


def pc_foster(
    miss2: np.ndarray,
    cov2: np.ndarray,
    radius_km: np.ndarray | float,
    *,
    n_r: int | None = None,
    n_theta: int | None = None,
    chunk: int = 512,
) -> np.ndarray:
    """Foster's polar-grid integration of the Gaussian over the disc, vectorised over events.

    The grid density follows the hardest case in each chunk (disc radius over the
    smallest standard deviation): at least 24 radial and 72 angular nodes, more when the
    disc is large against the uncertainty so that the peak is resolved. Explicit
    ``n_r`` and ``n_theta`` override that.
    """
    miss2, cov2, radius = _as_arrays(miss2, cov2, radius_km)
    n = len(miss2)
    out = np.full(n, np.nan)
    for s in range(0, n, chunk):
        sl = slice(s, min(s + chunk, n))
        m, c, R = miss2[sl], cov2[sl], radius[sl]
        sx, sy, _, _ = principal_axes(c, m)
        ratio = _resolution_ratio(R, sx, sy)
        nr = n_r or int(np.clip(np.ceil(6.0 * ratio), 24, 512))
        nt = n_theta or int(np.clip(np.ceil(20.0 * ratio), 72, 1024))
        x_gl, w_gl = leggauss(nr)
        r = 0.5 * R[:, None] * (x_gl[None, :] + 1.0)  # (m, nr)
        w_r = 0.5 * R[:, None] * w_gl[None, :] * r
        theta = TWO_PI * (np.arange(nt) + 0.5) / nt
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        X = r[:, :, None] * cos_t[None, None, :] - m[:, 0, None, None]
        Y = r[:, :, None] * sin_t[None, None, :] - m[:, 1, None, None]
        a, b, cc = c[:, 0, 0], c[:, 0, 1], c[:, 1, 1]
        det = a * cc - b * b
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            q = (cc[:, None, None] * X * X - 2.0 * b[:, None, None] * X * Y + a[:, None, None] * Y * Y) / det[
                :, None, None
            ]
            pdf = np.exp(-0.5 * q) / (TWO_PI * np.sqrt(det))[:, None, None]
            out[sl] = np.einsum("mi,mij->m", w_r, pdf) * (TWO_PI / nt)
    return out


def pc_alfano(
    miss2: np.ndarray,
    cov2: np.ndarray,
    radius_km: np.ndarray | float,
    *,
    n_nodes: int | None = None,
    chunk: int = 4096,
) -> np.ndarray:
    """Alfano's one-dimensional form: Gauss-Legendre along a principal axis, error functions across.

    In the principal axes of the covariance, with the substitution ``x = R sin(phi)``,
    the probability is the integral over ``phi`` of the chord length times the marginal
    density along ``x`` times the mass of the other marginal inside the chord. The
    across-chord mass is written with complementary error functions so that a miss far
    outside the disc does not cancel catastrophically.
    """
    miss2, cov2, radius = _as_arrays(miss2, cov2, radius_km)
    n = len(miss2)
    out = np.full(n, np.nan)
    for s in range(0, n, chunk):
        sl = slice(s, min(s + chunk, n))
        m, c, R = miss2[sl], cov2[sl], radius[sl]
        sx, sy, mx, my = principal_axes(c, m)
        ratio = _resolution_ratio(R, sx, sy)
        nn = n_nodes or int(np.clip(np.ceil(12.0 * ratio), 64, 2048))
        phi, w = leggauss(nn)
        phi = 0.5 * np.pi * phi
        w = 0.5 * np.pi * w
        x = R[:, None] * np.sin(phi)[None, :]
        chord = R[:, None] * np.cos(phi)[None, :]
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            pdf_x = np.exp(-0.5 * ((x - mx[:, None]) / sx[:, None]) ** 2) / (sx[:, None] * np.sqrt(TWO_PI))
            root2_sy = np.sqrt(2.0) * sy[:, None]
            mass_y = 0.5 * (
                erfc((np.abs(my)[:, None] - chord) / root2_sy) - erfc((np.abs(my)[:, None] + chord) / root2_sy)
            )
            out[sl] = np.einsum("j,mj->m", w, chord * pdf_x * mass_y)
    return out


def pc_chan(miss2: np.ndarray, cov2: np.ndarray, radius_km: np.ndarray | float, *, max_terms: int = 2000) -> np.ndarray:
    """Chan's equal-area series: ``sum_m Poisson(m; v/2) P(m + 1, u/2)``.

    ``u = R^2 / (sx sy)`` is the disc area over the ellipse area and ``v`` the Mahalanobis miss.

    ``P`` is the regularised lower incomplete gamma function, which is the bracketed
    partial exponential sum of Chan's formula. The series is summed to where the Poisson
    weights are negligible; a miss so far out that ``v / 2 > 700`` underflows to zero.
    """
    miss2, cov2, radius = _as_arrays(miss2, cov2, radius_km)
    sx, sy, mx, my = principal_axes(cov2, miss2)
    with np.errstate(invalid="ignore", divide="ignore"):
        u = radius**2 / (sx * sy)
        v = (mx / sx) ** 2 + (my / sy) ** 2
    lam = 0.5 * v
    x = 0.5 * u
    finite = np.isfinite(lam) & np.isfinite(x) & (lam <= 700.0)
    terms_needed = np.where(finite, np.ceil(lam + 10.0 * np.sqrt(lam + 1.0) + 10.0), 1.0)
    M = int(min(max_terms, terms_needed.max())) if len(terms_needed) else 1
    m = np.arange(M + 1, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_w = m[None, :] * np.log(np.where(lam > 0, lam, 1.0))[:, None] - lam[:, None] - gammaln(m + 1.0)[None, :]
        log_w = np.where((lam[:, None] == 0.0) & (m[None, :] > 0), -np.inf, log_w)
        w = np.exp(log_w)
    w = np.where(m[None, :] <= terms_needed[:, None], w, 0.0)
    partial = gammainc(m[None, :] + 1.0, np.where(finite, x, 0.0)[:, None])
    out = np.einsum("nm,nm->n", w, partial)
    return np.where(finite, out, np.where(np.isfinite(lam) & (lam > 700.0), 0.0, np.nan))


Integrator = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


def max_pc_sweep(
    miss2: np.ndarray,
    cov2: np.ndarray,
    radius_km: np.ndarray | float,
    *,
    scales: np.ndarray = DEFAULT_SCALES,
    integrator: Integrator = pc_alfano,
    final: Integrator | None = pc_foster,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The maximum probability over covariance scale factors, and the factor at which it occurs.

    The combined covariance is multiplied by each factor in ``scales`` (a log grid from
    0.1 to 10 by default) and the probability evaluated with ``integrator``; an interior
    maximum is refined by a parabola through its neighbours in log scale. ``final``, if
    given, re-evaluates the maximum (so the reported value comes from the same
    integrator as ``pc``). Returns ``(pc_max, scale_at_max, curve)`` with ``curve`` of
    shape ``(n, len(scales))``.
    """
    miss2, cov2, radius = _as_arrays(miss2, cov2, radius_km)
    scales = np.asarray(scales, dtype=float)
    curve = np.stack([integrator(miss2, cov2 * s, radius) for s in scales], axis=1)
    safe = np.where(np.isfinite(curve), curve, -np.inf)
    idx = np.argmax(safe, axis=1)
    log_s = np.log(scales)
    best_log = log_s[idx]
    interior = (idx > 0) & (idx < len(scales) - 1) & np.isfinite(curve[np.arange(len(idx)), idx])
    if interior.any():
        rows = np.nonzero(interior)[0]
        f_lo = curve[rows, idx[rows] - 1]
        f0 = curve[rows, idx[rows]]
        f_hi = curve[rows, idx[rows] + 1]
        denom = f_lo - 2.0 * f0 + f_hi
        with np.errstate(invalid="ignore", divide="ignore"):
            delta = np.where(denom < 0, 0.5 * (f_lo - f_hi) / denom, 0.0)
        h = log_s[idx[rows]] - log_s[idx[rows] - 1]
        best_log[rows] = log_s[idx[rows]] + np.clip(delta, -1.0, 1.0) * h
    scale_at_max = np.exp(best_log)
    evaluate = final or integrator
    pc_max = evaluate(miss2, cov2 * scale_at_max[:, None, None], radius)
    grid_max = curve[np.arange(len(idx)), idx]
    worse = ~(pc_max >= grid_max)
    if worse.any():
        # The refinement did not help (or the integrators differ slightly): keep the grid point.
        pc_max = np.where(worse, evaluate(miss2, cov2 * scales[idx][:, None, None], radius), pc_max)
        scale_at_max = np.where(worse, scales[idx], scale_at_max)
    return pc_max, scale_at_max, curve


def slow_encounters(rel_speed_kms: np.ndarray, *, threshold_kms: float = SLOW_ENCOUNTER_KMS) -> np.ndarray:
    """Which encounters are too slow for the straight-line assumption to hold.

    A true flag says the probability reported for that event is a **known underestimate**.
    The two-dimensional method projects the covariance onto one plane and integrates once,
    which is right only if the pair passes in a straight line at constant velocity. A slow
    pair does not: the relative path curves through the passage, the two can re-approach, and
    more of the uncertainty is in play than the single plane sees.

    It is a flag and not a correction. Nothing here rescales the probability; the fix is a
    three-dimensional integration over the encounter, and that is not in this phase.

    **It rests on the method's assumption and not on any measured error.** The reproduction
    of ESA's Kelvins risk column cannot size the underestimate, or even detect it: ESA's own
    column is computed the same way, so the residual binned by relative speed is flat at the
    slow end whatever the true bias is. Agreement between two tools that share an
    approximation is not evidence about the approximation
    (``docs/kelvins-reproduction.md``). The threshold is therefore set from the geometry --
    at 0.1 km/s a pair takes 100 s to cross 10 km, in which a low orbit turns through about
    six degrees against a twentieth of a degree at 13 km/s -- not from a measured residual.
    """
    speed = np.asarray(rel_speed_kms, dtype=float)
    with np.errstate(invalid="ignore"):
        return np.asarray(np.isfinite(speed) & (speed < float(threshold_kms)))


def flags(pc: np.ndarray, *, red: float = RED_PC, yellow: float = YELLOW_PC) -> np.ndarray:
    """``'red'`` at or above ``red``, ``'yellow'`` at or above ``yellow``, else ``'none'``; NaN is ``'none'``."""
    pc = np.asarray(pc, dtype=float)
    out = np.full(pc.shape, "none", dtype=object)
    with np.errstate(invalid="ignore"):
        out[pc >= yellow] = "yellow"
        out[pc >= red] = "red"
    return out


def regions(scale_at_max: np.ndarray) -> np.ndarray:
    """``'dilution'`` where the maximum probability lies below the current covariance, else ``'robust'``.

    ``'unknown'`` when the sweep did not run. A scale below one means shrinking the
    covariance would raise the probability: the event sits on the falling side of
    Alfano's curve, where a larger uncertainty gives a smaller number and the
    probability says more about the covariance than about the encounter.
    """
    scale = np.asarray(scale_at_max, dtype=float)
    out = np.full(scale.shape, "unknown", dtype=object)
    with np.errstate(invalid="ignore"):
        out[scale >= 1.0] = "robust"
        out[scale < 1.0] = "dilution"
    return out


def confidences(region: np.ndarray) -> np.ndarray:
    """``'standard'`` in the robust region, ``'low'`` everywhere else.

    A red or yellow flag with ``'low'`` confidence is a statement about the uncertainty,
    not about the encounter: it must be reported as such and never acted on.
    """
    region = np.asarray(region, dtype=object)
    return np.where(region == "robust", "standard", "low").astype(object)
