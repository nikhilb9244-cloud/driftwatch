"""Reproduce the risk column of ESA's Kelvins Collision Avoidance Challenge from its own inputs.

The dataset (Uriot et al., "Spacecraft collision avoidance challenge: design and
results of a machine learning competition", Astrodynamics 2021; data from
https://kelvins.esa.int/collision-avoidance-challenge/) holds one row per conjunction
data message: the chaser's position and velocity relative to the target in the target's
RTN frame, the standard deviations and correlations of both objects' position
covariances in their own RTN frames, and ESA's computed ``risk`` as log10 of the
probability of collision (floored at -30), with, for many rows, ``max_risk_estimate``
and ``max_risk_scaling`` from the covariance scale sweep. The hard-body radius ESA used
is not given, so it is treated as a fit parameter here.

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
DEFAULT_RADII_M: np.ndarray = np.arange(1.0, 50.01, 0.5)


def find_dataset(kelvins_dir: Path = config.KELVINS_DIR) -> Path | None:
    """The first CSV that looks like the challenge data under ``kelvins_dir``, or None."""
    if not kelvins_dir.exists():
        return None
    for name in ("train_data.csv", "test_data.csv"):
        if (kelvins_dir / name).exists():
            return kelvins_dir / name
    csvs = sorted(kelvins_dir.glob("*.csv"))
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


def reproduce(df: pd.DataFrame, hbr_m: float, *, plane: EncounterPlane | None = None) -> np.ndarray:
    """log10 of our probability for every row at hard-body radius ``hbr_m`` (Foster), floored like ESA's column."""
    plane = plane or encounter(df)
    pc = pc_foster(plane.miss_km, plane.cov_km2, hbr_m / 1000.0)
    with np.errstate(divide="ignore"):
        return np.maximum(np.log10(np.where(pc > 0, pc, 0.0)), RISK_FLOOR)


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
    return {"overall": stats(res), "by_risk_bin": by_bin}


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


def to_markdown(fit: HbrFit, dataset: Path, extra: dict[str, Any] | None = None) -> str:
    """The reproduction as a short markdown section for the docs."""
    lines = [
        f"Dataset: `{dataset.name}`, {fit.n_tail} rows in the tail (risk >= {TAIL_RISK:g}).",
        f"Best hard-body radius: **{fit.hbr_m:.1f} m** (median absolute residual "
        f"{fit.report['overall']['median']:+.3f} in log10; {fit.report['overall']['within_factor_two']:.0%} "
        "within a factor of two).",
        "",
        "| Risk bin | n | median | p05 | p95 | within x2 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, st in fit.report["by_risk_bin"].items():
        if st.get("n", 0) == 0:
            lines.append(f"| {name} | 0 | | | | |")
        else:
            lines.append(
                f"| {name} | {st['n']} | {st['median']:+.2f} | {st['p05']:+.2f} | {st['p95']:+.2f} | "
                f"{st['within_factor_two']:.0%} |"
            )
    if extra:
        lines.append("")
        lines.append("Maximum-risk check: " + ", ".join(f"{k} = {v}" for k, v in extra.items()))
    return "\n".join(lines)
