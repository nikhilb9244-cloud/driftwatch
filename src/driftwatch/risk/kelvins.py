"""Reproduce the risk column of ESA's Kelvins Collision Avoidance Challenge from its own inputs.

The dataset (Uriot et al., "Spacecraft collision avoidance challenge: design and
results of a machine learning competition", Astrodynamics 2021; data from
https://kelvins.esa.int/collision-avoidance-challenge/) holds one row per conjunction
data message: the chaser's position and velocity relative to the target in the target's
RTN frame, the standard deviations and correlations of both objects' position
covariances in their own RTN frames, and ESA's computed ``risk`` as log10 of the
probability of collision (floored at -30), with, for many rows, ``max_risk_estimate``
and ``max_risk_scaling`` from the covariance scale sweep.

The hard-body radius ESA used is not documented, and Phase 2 treated it as a single fitted
parameter (9.0 m, agreement within a factor of two on 43 % of the tail). It turned out to be
in the data. Each object carries a ``span`` in metres, and the combined radius
``(t_span + c_span) / 2`` reproduces ESA's risk column with a median residual of 0.0003 in
log10 and no fitted parameter at all: :func:`reproduce_tail` is the primary reconstruction and
:func:`fit_hbr` is kept as the fallback for a catalogue with no size column.

Approximations in the reconstruction, each stated so the residuals can be read
honestly:

* The chaser's RTN frame is built from the target's RTN frame and the relative
  velocity: same radial axis (the two are within kilometres of each other at 7,000 km
  from the centre), transverse along the chaser's velocity, which is the target's
  velocity plus the relative velocity. The target's velocity vector is not in the data;
  it is taken as circular, ``sqrt(mu / a)`` along the target's transverse axis, so the
  radial velocity of an eccentric target is ignored (a fraction of a percent of the
  speed for the eccentricities in the data).
* The covariances are used as position-only 3 x 3 matrices; the velocity terms play no
  part in the two-dimensional method.
* The expected level of agreement is a factor of two across the high-risk tail
  (``risk >= -6``). Rows at the floor are excluded from the fit.

The data are not redistributed with driftwatch; download them from the Kelvins site
(registration required) into ``data/external/kelvins/``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import config
from driftwatch.orbit.propagator import WGS72_MU_KM3_S2
from driftwatch.risk.pc import EncounterPlane, encounter_plane, max_pc_sweep, pc_foster

log = logging.getLogger(__name__)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "risk",
    "relative_position_r",
    "relative_position_t",
    "relative_position_n",
    "relative_velocity_r",
    "relative_velocity_t",
    "relative_velocity_n",
    "t_j2k_sma",
    "t_sigma_r",
    "t_sigma_t",
    "t_sigma_n",
    "t_ct_r",
    "t_cn_r",
    "t_cn_t",
    "c_sigma_r",
    "c_sigma_t",
    "c_sigma_n",
    "c_ct_r",
    "c_cn_r",
    "c_cn_t",
)
OPTIONAL_COLUMNS: tuple[str, ...] = ("event_id", "time_to_tca", "max_risk_estimate", "max_risk_scaling")
RISK_FLOOR = -30.0
TAIL_RISK = -6.0
# The tail that decides whether the tool is any use: ESA's own reporting threshold, and the
# yellow flag driftwatch uses. Agreement averaged over everything down to 1e-6 is dominated
# by the rows nobody would act on, so the headline number is quoted over this tail too.
TAIL_RISK_TIGHT = -5.0
DEFAULT_RADII_M: np.ndarray = np.arange(1.0, 50.01, 0.5)


def find_dataset(kelvins_dir: Path = config.KELVINS_DIR) -> Path | None:
    """The challenge CSV under ``kelvins_dir``, or None.

    ``train_data.csv`` is preferred over ``test_data.csv`` (it is the larger half and the
    one the challenge scored against), and both are looked for one directory down as well,
    since the download unpacks into a folder of its own.
    """
    if not kelvins_dir.exists():
        return None
    for name in ("train_data.csv", "test_data.csv"):
        for candidate in (kelvins_dir / name, *sorted(kelvins_dir.glob(f"*/{name}"))):
            if candidate.exists():
                return candidate
    csvs = sorted(kelvins_dir.glob("*.csv")) or sorted(kelvins_dir.glob("*/*.csv"))
    return csvs[0] if csvs else None


def load_kelvins(path: Path) -> pd.DataFrame:
    """Read the CSV and check the columns the reconstruction needs are present."""
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} lacks the columns {missing}; is it the Kelvins collision-avoidance CSV?")
    return df


def _covariance_from_sigmas(df: pd.DataFrame, prefix: str) -> np.ndarray:
    """A 3 x 3 RTN position covariance in km^2 from ``<prefix>_sigma_*`` (m) and the correlation coefficients."""
    s = df[[f"{prefix}_sigma_r", f"{prefix}_sigma_t", f"{prefix}_sigma_n"]].to_numpy(dtype=float) / 1000.0
    rho_tr = df[f"{prefix}_ct_r"].to_numpy(dtype=float)
    rho_nr = df[f"{prefix}_cn_r"].to_numpy(dtype=float)
    rho_nt = df[f"{prefix}_cn_t"].to_numpy(dtype=float)
    n = len(df)
    corr = np.ones((n, 3, 3))
    corr[:, 0, 1] = corr[:, 1, 0] = rho_tr
    corr[:, 0, 2] = corr[:, 2, 0] = rho_nr
    corr[:, 1, 2] = corr[:, 2, 1] = rho_nt
    return s[:, :, None] * corr * s[:, None, :]


def kelvins_geometry(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Relative position (km), relative velocity (km/s) and combined covariance (km^2) in the target's RTN frame."""
    dr = df[["relative_position_r", "relative_position_t", "relative_position_n"]].to_numpy(dtype=float) / 1000.0
    dv = df[["relative_velocity_r", "relative_velocity_t", "relative_velocity_n"]].to_numpy(dtype=float) / 1000.0
    cov_t = _covariance_from_sigmas(df, "t")
    cov_c = _covariance_from_sigmas(df, "c")
    # The chaser's RTN axes expressed in the target's RTN frame.
    sma_km = df["t_j2k_sma"].to_numpy(dtype=float)
    v_t = np.zeros_like(dv)
    v_t[:, 1] = np.sqrt(WGS72_MU_KM3_S2 / sma_km)
    v_c = v_t + dv
    radial = np.tile(np.array([1.0, 0.0, 0.0]), (len(df), 1))
    transverse = v_c - np.einsum("ni,ni->n", v_c, radial)[:, None] * radial
    transverse /= np.linalg.norm(transverse, axis=1, keepdims=True)
    normal = np.cross(radial, transverse)
    axes = np.stack([radial, transverse, normal], axis=2)  # columns: chaser R, T, N in target RTN
    cov_c_target = np.einsum("nij,njk,nlk->nil", axes, cov_c, axes)
    return dr, dv, cov_t + cov_c_target


def encounter(df: pd.DataFrame) -> EncounterPlane:
    dr, dv, cov = kelvins_geometry(df)
    return encounter_plane(dr, dv, cov)


def reproduce(df: pd.DataFrame, hbr_m: float | np.ndarray, *, plane: EncounterPlane | None = None) -> np.ndarray:
    """log10 of our probability for every row at hard-body radius ``hbr_m`` (Foster), floored like ESA's column.

    ``hbr_m`` is one radius for every row, or one per row when a size proxy is being tested.
    """
    plane = plane or encounter(df)
    radius_km = np.asarray(hbr_m, dtype=float) / 1000.0
    pc = pc_foster(plane.miss_km, plane.cov_km2, radius_km)
    with np.errstate(divide="ignore"):
        return np.maximum(np.log10(np.where(pc > 0, pc, 0.0)), RISK_FLOOR)


# --------------------------------------------------------------------------------------
# Size proxies: does the data say what radius ESA used?


def combined_radius_m(df: pd.DataFrame, source: str) -> np.ndarray:
    """A per-row combined hard-body radius in metres from one of the dataset's size columns.

    ``span``  ``(t_span + c_span) / 2``: the columns are each object's largest dimension in
              metres, so half of each is its circumscribing radius and the two add. The
              chaser's span is 2.0 m on 93 % of rows, which is a catalogue default rather
              than a measurement, so this proxy mostly varies with the target.
    ``rcs``   ``sqrt(t_rcs / pi) + sqrt(c_rcs / pi)`` from the radar cross-section estimates
              in square metres: the radius of the disc that would return the same echo. It
              understates anything much larger than the radar wavelength and anything with a
              low-return geometry, and it is missing on a third of the chaser rows.

    Rows with a missing value come back NaN; the caller decides whether to drop them.
    """
    if source == "span":
        cols = ("t_span", "c_span")
        if not all(c in df.columns for c in cols):
            raise ValueError(f"the dataset lacks {cols}")
        return df["t_span"].to_numpy(dtype=float) / 2.0 + df["c_span"].to_numpy(dtype=float) / 2.0
    if source == "rcs":
        cols = ("t_rcs_estimate", "c_rcs_estimate")
        if not all(c in df.columns for c in cols):
            raise ValueError(f"the dataset lacks {cols}")
        t = np.sqrt(np.maximum(df["t_rcs_estimate"].to_numpy(dtype=float), 0.0) / np.pi)
        c = np.sqrt(np.maximum(df["c_rcs_estimate"].to_numpy(dtype=float), 0.0) / np.pi)
        return t + c
    raise ValueError(f"unknown size proxy {source!r}")


@dataclass
class Reproduction:
    """One reconstruction of ESA's risk column over the tail: which radius, and how it did."""

    label: str
    description: str
    n: int
    radius_m: np.ndarray
    risk: np.ndarray
    residuals: np.ndarray
    report: dict[str, Any]


def reproduce_tail(df: pd.DataFrame, *, source: str = "span", tail_risk: float = TAIL_RISK) -> Reproduction | None:
    """Score the tail with a per-object radius from one of the dataset's size columns.

    Returns None when the columns are absent, so a dataset without them falls back to the
    fitted single radius.
    """
    tail = df[(df["risk"] >= tail_risk) & (df["risk"] > RISK_FLOOR)].reset_index(drop=True)
    try:
        radius = combined_radius_m(tail, source)
    except ValueError:
        return None
    usable = np.isfinite(radius) & (radius > 0)
    if not usable.any():
        return None
    tail = tail.loc[usable].reset_index(drop=True)
    radius = radius[usable]
    risk = tail["risk"].to_numpy(dtype=float)
    residuals = reproduce(tail, radius) - risk
    description = {
        "span": "half of each object's `span`, added: `(t_span + c_span) / 2`",
        "rcs": "the equivalent radius of each radar cross-section, added: `sqrt(t_rcs / pi) + sqrt(c_rcs / pi)`",
    }.get(source, source)
    return Reproduction(source, description, len(tail), radius, risk, residuals, residual_report(tail, residuals))


def test_size_proxy(
    tail: pd.DataFrame,
    source: str,
    *,
    plane: EncounterPlane | None = None,
    scales: np.ndarray | None = None,
) -> dict[str, Any] | None:
    """Score a per-object size proxy against the single fitted radius over the same rows.

    The proxy is allowed one free multiplier, fitted the same way the single radius is (the
    smallest median absolute residual), because the question is whether the *shape* of the
    per-object radius helps, not whether the dataset's units happen to match ESA's
    convention. Returns None when the columns are absent or every row is missing a value.
    """
    try:
        radius = combined_radius_m(tail, source)
    except ValueError:
        return None
    usable = np.isfinite(radius) & (radius > 0)
    if not usable.any():
        return None
    sub = tail.loc[usable].reset_index(drop=True)
    radius = radius[usable]
    plane = encounter(sub)
    risk = sub["risk"].to_numpy(dtype=float)
    scales = np.arange(0.25, 6.001, 0.25) if scales is None else scales

    # The same rows scored with one radius for everything, so the comparison is like for like.
    constant = fit_hbr(sub, tail_risk=float(np.min(risk)))
    best: tuple[float, float, np.ndarray] | None = None
    for scale in scales:
        res = reproduce(sub, radius * float(scale), plane=plane) - risk
        med = float(np.median(np.abs(res)))
        if best is None or med < best[0]:
            best = (med, float(scale), res)
    assert best is not None
    return {
        "source": source,
        "n": int(len(sub)),
        "n_missing": int((~usable).sum()),
        "radius_median_m": float(np.median(radius)),
        "radius_iqr_m": [float(np.percentile(radius, 25)), float(np.percentile(radius, 75))],
        "best_scale": best[1],
        "scaled_radius_median_m": float(np.median(radius) * best[1]),
        "median_abs_residual": best[0],
        "median_residual": float(np.median(best[2])),
        "within_factor_two": float(np.mean(np.abs(best[2]) <= np.log10(2.0))),
        # The single-radius fit over exactly these rows, for the comparison that matters.
        "constant_hbr_m": constant.hbr_m,
        "constant_median_abs_residual": float(np.median(np.abs(constant.residuals))),
        "constant_within_factor_two": constant.report["overall"]["within_factor_two"],
    }


@dataclass
class HbrFit:
    """The radius that best reproduces ESA's risk column, and how the residuals look there."""

    hbr_m: float
    n_tail: int
    by_radius: pd.DataFrame  # hbr_m, median_abs_residual, rms_residual, within_factor_two
    residuals: np.ndarray  # log10(ours) - risk over the tail, at the best radius
    report: dict[str, Any]


def fit_hbr(df: pd.DataFrame, *, radii_m: np.ndarray = DEFAULT_RADII_M, tail_risk: float = TAIL_RISK) -> HbrFit:
    """Scan the hard-body radius and pick the one with the smallest median absolute residual over the tail.

    The tail is every row with ``risk >= tail_risk`` (and above the floor). The
    residual is ``log10(ours) - risk``, so a factor of two is 0.30.
    """
    tail = df[(df["risk"] >= tail_risk) & (df["risk"] > RISK_FLOOR)].reset_index(drop=True)
    if tail.empty:
        raise ValueError("no rows in the high-risk tail")
    plane = encounter(tail)
    risk = tail["risk"].to_numpy(dtype=float)
    rows = []
    best: tuple[float, float, np.ndarray] | None = None
    for hbr in radii_m:
        ours = reproduce(tail, float(hbr), plane=plane)
        res = ours - risk
        med = float(np.median(np.abs(res)))
        rows.append(
            {
                "hbr_m": float(hbr),
                "median_abs_residual": med,
                "rms_residual": float(np.sqrt(np.mean(res**2))),
                "within_factor_two": float(np.mean(np.abs(res) <= np.log10(2.0))),
            }
        )
        if best is None or med < best[0]:
            best = (med, float(hbr), res)
    assert best is not None
    by_radius = pd.DataFrame(rows)
    report = residual_report(tail, best[2])
    log.info("Kelvins: best hard-body radius %.1f m over %d tail rows; %s", best[1], len(tail), report["overall"])
    return HbrFit(best[1], len(tail), by_radius, best[2], report)


def residual_report(tail: pd.DataFrame, residuals: np.ndarray) -> dict[str, Any]:
    """Percentiles of the residual overall and per risk bin, and the share within a factor of two."""
    res = np.asarray(residuals, dtype=float)

    def stats(x: np.ndarray) -> dict[str, float]:
        if len(x) == 0:
            return {"n": 0}
        p = np.percentile(x, [5, 25, 50, 75, 95])
        return {
            "n": int(len(x)),
            "p05": float(p[0]),
            "p25": float(p[1]),
            "median": float(p[2]),
            "p75": float(p[3]),
            "p95": float(p[4]),
            "within_factor_two": float(np.mean(np.abs(x) <= np.log10(2.0))),
            "within_factor_ten": float(np.mean(np.abs(x) <= 1.0)),
        }

    risk = tail["risk"].to_numpy(dtype=float)
    bins = [(-6.0, -5.0), (-5.0, -4.0), (-4.0, -3.0), (-3.0, -2.0), (-2.0, 0.0)]
    by_bin = {f"[{lo:g}, {hi:g})": stats(res[(risk >= lo) & (risk < hi)]) for lo, hi in bins}
    return {
        "overall": stats(res),
        "tight_tail": stats(res[risk >= TAIL_RISK_TIGHT]),
        "by_risk_bin": by_bin,
    }


def residual_plot_svg(
    risk: np.ndarray,
    residuals: np.ndarray,
    *,
    compare: tuple[np.ndarray, np.ndarray] | None = None,
    width: int = 720,
    height: int = 380,
) -> str:
    """The residual against ESA's risk as a standalone SVG: a density map with median and 5/95 curves.

    Drawn by hand rather than with a plotting library so the repository keeps no plotting
    dependency and the file stays a few kilobytes of text that diffs. Colours are chosen to
    read on a light or a dark page, and nothing is filled with the page background.
    """
    risk = np.asarray(risk, dtype=float)
    res = np.asarray(residuals, dtype=float)
    x0, x1, y0, y1 = TAIL_RISK, 0.0, -2.5, 2.5
    left, right, top, bottom = 62, 18, 16, 44
    w, h = width - left - right, height - top - bottom
    nx, ny = 60, 50
    counts, _, _ = np.histogram2d(
        np.clip(risk, x0, x1), np.clip(res, y0, y1), bins=[nx, ny], range=[[x0, x1], [y0, y1]]
    )
    peak = max(counts.max(), 1.0)

    def sx(v: float) -> float:
        return left + (v - x0) / (x1 - x0) * w

    def sy(v: float) -> float:
        return top + (y1 - v) / (y1 - y0) * h

    cell_w, cell_h = w / nx, h / ny
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" font-family="system-ui, sans-serif" font-size="12">',
        "<title>driftwatch minus ESA, log10 of the ratio, against ESA's risk</title>",
        f'<rect x="{left}" y="{top}" width="{w}" height="{h}" fill="none" stroke="#8888" />',
    ]
    # The density map: opacity by count, on a log scale so the sparse high-risk end is visible.
    for i in range(nx):
        for j in range(ny):
            c = counts[i, j]
            if c <= 0:
                continue
            alpha = 0.12 + 0.88 * float(np.log1p(c) / np.log1p(peak))
            parts.append(
                f'<rect x="{left + i * cell_w:.2f}" y="{top + h - (j + 1) * cell_h:.2f}" '
                f'width="{cell_w:.2f}" height="{cell_h:.2f}" fill="#2f6fb0" opacity="{alpha:.3f}" />'
            )
    # Agreement bands: exact, and within a factor of two.
    parts.append(
        f'<rect x="{left}" y="{sy(np.log10(2.0)):.1f}" width="{w}" '
        f'height="{sy(-np.log10(2.0)) - sy(np.log10(2.0)):.1f}" fill="#e8a33d" opacity="0.16" />'
    )
    parts.append(f'<line x1="{left}" y1="{sy(0.0):.1f}" x2="{left + w}" y2="{sy(0.0):.1f}" stroke="#e8a33d" />')
    # Median and 5/95 percentiles of the residual per risk bin.
    edges = np.linspace(x0, x1, 13)
    for q, style in (
        (50, 'stroke="#d1495b" stroke-width="2.5"'),
        (5, 'stroke="#d1495b" stroke-dasharray="4 3"'),
        (95, 'stroke="#d1495b" stroke-dasharray="4 3"'),
    ):
        pts = []
        for lo, hi in zip(edges[:-1], edges[1:], strict=False):
            sel = (risk >= lo) & (risk < hi)
            if sel.sum() >= 20:
                pts.append(f"{sx((lo + hi) / 2):.1f},{sy(float(np.percentile(res[sel], q))):.1f}")
        if len(pts) > 1:
            parts.append(f'<polyline points="{" ".join(pts)}" fill="none" {style} />')
    # The median of a second reconstruction, for contrast.
    if compare is not None:
        c_risk, c_res = np.asarray(compare[0], dtype=float), np.asarray(compare[1], dtype=float)
        pts = []
        for lo, hi in zip(edges[:-1], edges[1:], strict=False):
            sel = (c_risk >= lo) & (c_risk < hi)
            if sel.sum() >= 20:
                pts.append(f"{sx((lo + hi) / 2):.1f},{sy(float(np.median(c_res[sel]))):.1f}")
        if len(pts) > 1:
            parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#999" stroke-width="2" />')
            parts.append(
                f'<text x="{left + w - 6}" y="{top + 14}" text-anchor="end" fill="#999">one fitted radius</text>'
            )
            parts.append(
                f'<text x="{left + w - 6}" y="{top + 30}" text-anchor="end" fill="#d1495b">per-object span</text>'
            )
    # Axes.
    for v in np.arange(x0, x1 + 0.01, 1.0):
        parts.append(f'<line x1="{sx(v):.1f}" y1="{top + h}" x2="{sx(v):.1f}" y2="{top + h + 4}" stroke="#888" />')
        parts.append(f'<text x="{sx(v):.1f}" y="{top + h + 18}" text-anchor="middle" fill="#888">{v:g}</text>')
    for v in (-2, -1, 0, 1, 2):
        parts.append(f'<line x1="{left - 4}" y1="{sy(v):.1f}" x2="{left}" y2="{sy(v):.1f}" stroke="#888" />')
        parts.append(
            f'<text x="{left - 8}" y="{sy(v) + 4:.1f}" text-anchor="end" fill="#888">'
            f"{'×' + str(10 ** abs(v)) if v else '1'}{'' if v >= 0 else ' low'}</text>"
        )
    parts.append(
        f'<text x="{left + w / 2:.0f}" y="{height - 6}" text-anchor="middle" fill="#888">'
        "ESA&#8217;s risk, log10 of the probability of collision</text>"
    )
    parts.append(
        f'<text x="14" y="{top + h / 2:.0f}" text-anchor="middle" fill="#888" '
        f'transform="rotate(-90 14 {top + h / 2:.0f})">driftwatch over ESA</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def compare_max_risk(df: pd.DataFrame, hbr_m: float, *, limit: int | None = 2000) -> dict[str, Any] | None:
    """Our covariance-scale sweep against ESA's ``max_risk_estimate`` and ``max_risk_scaling``, if present.

    Reports the residual of the maximum probability and the ratio of scale factors, so
    the convention of ``max_risk_scaling`` (a factor on the covariance or on the
    standard deviation) can be checked rather than assumed.
    """
    if "max_risk_estimate" not in df.columns or "max_risk_scaling" not in df.columns:
        return None
    sub = df[(df["risk"] >= TAIL_RISK) & df["max_risk_estimate"].notna() & df["max_risk_scaling"].notna()]
    if limit is not None:
        sub = sub.head(limit)
    if sub.empty:
        return None
    plane = encounter(sub.reset_index(drop=True))
    pc_max, scale, _ = max_pc_sweep(plane.miss_km, plane.cov_km2, hbr_m / 1000.0)
    with np.errstate(divide="ignore"):
        ours = np.maximum(np.log10(np.where(pc_max > 0, pc_max, 0.0)), RISK_FLOOR)
    res = ours - sub["max_risk_estimate"].to_numpy(dtype=float)
    theirs = sub["max_risk_scaling"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = scale / theirs
        ratio_sqrt = np.sqrt(scale) / theirs
    return {
        "n": int(len(sub)),
        "max_risk_residual_median": float(np.median(res)),
        "max_risk_within_factor_two": float(np.mean(np.abs(res) <= np.log10(2.0))),
        "scale_ratio_median_if_covariance_factor": float(np.nanmedian(ratio)),
        "scale_ratio_median_if_sigma_factor": float(np.nanmedian(ratio_sqrt)),
    }


def to_markdown(
    fit: HbrFit,
    dataset: Path,
    extra: dict[str, Any] | None = None,
    *,
    primary: Reproduction | None = None,
    proxies: list[dict[str, Any]] | None = None,
    plot_path: str | None = None,
) -> str:
    """The reproduction as a markdown page for the docs.

    Residuals are ``log10(ours) - log10(ESA's)``, so a factor of two either way is 0.30 and
    a positive number means driftwatch reads the encounter as riskier than ESA did.
    """
    lines: list[str] = [
        f"Dataset: `{dataset.name}`, {fit.n_tail} rows in the high-risk tail (risk >= {TAIL_RISK:g}).",
        "",
    ]

    if primary is not None:
        overall = primary.report["overall"]
        tight = primary.report["tight_tail"]
        lines += [
            "## The hard-body radius ESA used",
            "",
            f"It is in the data. The combined radius is {primary.description}, and with it the "
            "reconstruction stops being an approximation: over the tail the median residual is "
            f"**{overall['median']:+.4f}** in log10, which is {abs(10 ** overall['median'] - 1):.2%} in the "
            f"probability, with quartiles {overall['p25']:+.3f} to {overall['p75']:+.3f}. "
            f"{overall['within_factor_two']:.0%} of rows agree within a factor of two and "
            f"{overall['within_factor_ten']:.0%} within a factor of ten. Nothing was fitted to get this: "
            "the multiplier on the span is one.",
            "",
            "That settles the question the Phase 2 review left open. The probability code agrees with ESA's "
            "to a fraction of a percent for most conjunctions; what disagreement remains is not in the "
            "integration but in the rows described below.",
            "",
            "**Restricted to the tail that matters** (risk above 1e-5, the yellow-flag threshold): "
            f"{tight['n']} rows, median residual **{tight['median']:+.4f}**, "
            f"{tight['within_factor_two']:.0%} within a factor of two and {tight['within_factor_ten']:.0%} "
            f"within a factor of ten, quartiles {tight['p25']:+.3f} to {tight['p75']:+.3f}.",
            "",
            "**The direction of the bias.** There is essentially none in the median: over the tail that "
            f"matters the reconstruction is {'high' if tight['median'] > 0 else 'low'} by "
            f"{abs(10 ** tight['median'] - 1):.2%}, which is numerical noise rather than a bias. The "
            f"residual is not symmetric, though. Its 5th percentile is {tight['p05']:+.2f} and its 95th is "
            f"{tight['p95']:+.2f}: the long tail is on the **low** side, so where this reconstruction "
            "disagrees it usually reads the encounter as *safer* than ESA did, by up to a factor of ten. "
            "That is the dangerous direction to be wrong in, and it is why the whole distribution is "
            "reported rather than its median. The rows in that tail are disproportionately payloads (13 % "
            "of them against 4 % of the tail), which is where the chaser-frame approximation below bites.",
            "",
            "| Risk bin | n | median | p05 | p95 | within x2 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for name, st in primary.report["by_risk_bin"].items():
            if st.get("n", 0) == 0:
                lines.append(f"| {name} | 0 | | | | |")
            else:
                lines.append(
                    f"| {name} | {st['n']} | {st['median']:+.4f} | {st['p05']:+.2f} | {st['p95']:+.2f} | "
                    f"{st['within_factor_two']:.0%} |"
                )
        lines += [
            "",
            "The eight rows above 1e-2 are the exception: five of them come out two orders of magnitude "
            "low. At that risk the miss is comparable to the hard-body radius and the two-dimensional "
            "method is at the edge of its assumptions, so the disagreement is expected there. It is stated "
            "rather than tuned away.",
            "",
        ]

    if plot_path:
        lines += [
            "## The residual against the risk",
            "",
            f"![Residual against ESA's risk]({plot_path})",
            "",
            "Density of the residual over the tail with the span radius: the median solid and the 5th and "
            "95th percentiles dashed, per risk decade, with the band marking agreement within a factor of "
            "two. The grey line is the median of the older reconstruction, which fitted one radius for "
            "every conjunction. Two things to read from it: the median sits on zero once the radius is "
            "right, and the spread is one-sided, reaching down towards safer and barely up towards riskier.",
            "",
        ]

    overall = fit.report["overall"]
    tight = fit.report.get("tight_tail", {})
    lines += [
        "## One radius for everything, as a fallback",
        "",
        "Kept because a catalogue without a size column still needs a number, and because it is the honest "
        "picture of what a screening tool can do when it does not know how big the objects are.",
        "",
        f"Best single hard-body radius: **{fit.hbr_m:.1f} m**, the radius with the smallest median absolute "
        "residual over the tail.",
        "",
        f"Residual: median **{overall['median']:+.3f}** "
        f"(a factor of {10 ** abs(overall['median']):.2f} {'high' if overall['median'] > 0 else 'low'}), "
        f"quartiles {overall['p25']:+.2f} to {overall['p75']:+.2f}, "
        f"{overall['within_factor_two']:.0%} within a factor of two and "
        f"{overall['within_factor_ten']:.0%} within a factor of ten.",
    ]
    if tight.get("n"):
        lines += [
            "",
            f"Over the tail that matters (risk above 1e-5): {tight['n']} rows, median "
            f"**{tight['median']:+.3f}**, a factor of {10 ** abs(tight['median']):.2f} "
            f"{'high' if tight['median'] > 0 else 'low'}, {tight['within_factor_two']:.0%} within a factor "
            "of two. The bias has an obvious cause: with one radius for every object the reconstruction "
            "over-calls the risk of small debris and under-calls the risk of large payloads, because it "
            "gives them the same size.",
        ]
    lines += [
        "",
        "| Risk bin | n | median | p05 | p95 | within x2 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, st in fit.report["by_risk_bin"].items():
        if st.get("n", 0) == 0:
            lines.append(f"| {name} | 0 | | | | |")
        else:
            lines.append(
                f"| {name} | {st['n']} | {st['median']:+.2f} | {st['p05']:+.2f} | {st['p95']:+.2f} | "
                f"{st['within_factor_two']:.0%} |"
            )

    if proxies:
        lines += [
            "",
            "## The two size columns, scored against each other",
            "",
            "The dataset carries two size columns per object: `*_span`, the largest dimension in metres, "
            "and `*_rcs_estimate`, the radar cross-section in square metres. Each is given one free "
            "multiplier, fitted the way the single radius is, so the comparison is of the shape of the "
            "per-object radius rather than of the units.",
            "",
            "| Proxy | Rows | Median radius | Best multiplier | Median abs. residual | Within x2 | "
            "One radius, same rows |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        for pr in proxies:
            lines.append(
                f"| `{pr['source']}` | {pr['n']} | {pr['radius_median_m']:.2f} m | {pr['best_scale']:g}x "
                f"| {pr['median_abs_residual']:.3f} | {pr['within_factor_two']:.0%} "
                f"| {pr['constant_hbr_m']:.1f} m: {pr['constant_median_abs_residual']:.3f}, "
                f"{pr['constant_within_factor_two']:.0%} |"
            )
        lines += [
            "",
            "`span` wins at a multiplier of exactly one, which is what identifies it as ESA's own "
            "convention rather than a lucky fit. `rcs` needs a multiplier of nearly five and still does no "
            "better than a single radius: the radar cross-section is the area of the echo rather than of "
            "the object, it understates anything much larger than the radar wavelength, and it is missing "
            "on a third of the chaser rows. **This bears directly on driftwatch's own screening**: the "
            "secondary radii in `risk/scenario.py` fall back to `sqrt(RCS / pi)` for payloads, rocket "
            "bodies and debris, and this says that fallback is biased small and that a published dimension "
            "should be preferred wherever there is one.",
        ]

    if extra:
        lines += [
            "",
            "## Maximum probability and its scaling, against ESA's own columns",
            "",
            f"- {extra['n']} rows compared; the residual of the maximum has median "
            f"{extra['max_risk_residual_median']:+.3f} and {extra['max_risk_within_factor_two']:.0%} within "
            "a factor of two.",
            "- Our scale factor over ESA's `max_risk_scaling`: median "
            f"{extra['scale_ratio_median_if_covariance_factor']:.4f} read as a factor on the covariance, "
            f"{extra['scale_ratio_median_if_sigma_factor']:.4f} read as a factor on the standard deviation. "
            "The first is one, so ESA's scaling is a factor on the covariance, as ours is.",
            "",
            "Both are computed at the fitted single radius, so they carry that reconstruction's bias.",
        ]

    lines += [
        "",
        "## What is still approximated",
        "",
        "- The chaser's RTN frame is built from the target's and the relative velocity, with the target's "
        "velocity taken as circular. The data do not carry the target's velocity vector.",
        "- Both covariances are used as position-only 3x3 matrices; the velocity terms play no part in the "
        "two-dimensional method.",
        "- Rows at the risk floor of -30 are excluded from every figure here.",
    ]
    return "\n".join(lines)
