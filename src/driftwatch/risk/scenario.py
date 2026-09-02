"""Covariance and probability over stored events, once per scenario.

The design rule for Phase 3: geometry and probability are separate. Stages A to C run
once per snapshot and write the events with both objects' TEME states at the time of
closest approach. A scenario (``quiet`` here; ``storm`` and ``replay:<name>`` in Phase
3) reruns only this module over those stored events with its own covariance model, and
writes one row per event carrying the scenario, the run id, the snapshot and the model
version. Nothing here propagates an orbit.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import __version__
from driftwatch.fleet import Fleet
from driftwatch.orbit.time import stamp
from driftwatch.risk.covariance import CovarianceModel, ObjectRef
from driftwatch.risk.manoeuvre import manoeuvre_prior
from driftwatch.risk.pc import (
    encounter_plane,
    flags,
    max_pc_sweep,
    pc_alfano,
    pc_chan,
    pc_foster,
    rotate_ric_to_teme,
)
from driftwatch.screening.ric import ric_basis
from driftwatch.screening.stages import STATE_COLUMNS

log = logging.getLogger(__name__)

# Hard-body radius for secondaries: the circumscribing sphere of a typical member of the
# category in metres, and whether a published radar cross-section should replace it.
# The RCS-derived radius, sqrt(RCS / pi), is the equivalent sphere of the radar return; it
# understates bodies much larger than the radar wavelength (a Starlink returns a few
# square metres from a 10 m envelope), so categories with a known envelope keep it.
# Starlink: V1.5 spans about 11 m, V2 Mini about 30 m with both arrays; 10 m is between.
# OneWeb and the other constellations: 1 m buses with 3 to 5 m arrays. Payload: a wide
# class; 3 m is a small bus with panels. Rocket body: half the length of a typical upper
# stage. Debris: fragments are mostly well under a metre. Unknown: analyst objects.
SECONDARY_HBR_M: dict[str, tuple[float, bool]] = {
    "station": (30.0, False),
    "starlink": (10.0, False),
    "oneweb": (3.0, False),
    "constellation": (3.0, False),
    "payload": (3.0, True),
    "rocket_body": (5.0, True),
    "debris": (0.5, True),
    "unknown": (1.0, True),
}
RCS_RADIUS_MIN_M = 0.1
RCS_RADIUS_MAX_M = 20.0


def hard_body_radius_m(category: str, rcs_m2: float | None, fleet_radius_m: float | None = None) -> tuple[float, str]:
    """The hard-body radius for one object and where it came from: ``fleet``, ``rcs`` or ``category``."""
    if fleet_radius_m is not None:
        return float(fleet_radius_m), "fleet"
    default, prefer_rcs = SECONDARY_HBR_M.get(str(category), SECONDARY_HBR_M["unknown"])
    if prefer_rcs and rcs_m2 is not None and np.isfinite(rcs_m2) and rcs_m2 > 0:
        return float(np.clip(np.sqrt(rcs_m2 / np.pi), RCS_RADIUS_MIN_M, RCS_RADIUS_MAX_M)), "rcs"
    return default, "category"


OBJECT_COLUMNS: tuple[str, ...] = (
    "norad_id",
    "name",
    "category",
    "altitude_band",
    "is_primary",
    "epoch",
    "ephemeris",
    "source",
    "in_active_group",
    "rcs_m2",
    "hbr_m",
    "hbr_source",
    "manoeuvre_prior",
    "manoeuvre_level",
    "n_history_sets",
    "n_jumps",
    "jump_epochs",
    "last_jump",
    "cov_source",
)


def objects_from_snapshot(norad_ids: list[int], snapshot: pd.DataFrame, fleet: Fleet) -> pd.DataFrame:
    """The per-object table for a run: identity, element set used, hard-body radius, manoeuvre prior.

    ``norad_ids`` are the objects that take part in any event plus the fleet. The
    history-derived columns (``manoeuvre_level``, jumps, ``cov_source``) are filled by
    :func:`apply_history` once the covariance has been fitted; until then the level is
    the prior.
    """
    by_id = snapshot.drop_duplicates("norad_id").set_index("norad_id")
    ids = sorted({int(i) for i in norad_ids})
    ephemeris = by_id["ephemeris"] if "ephemeris" in by_id.columns else pd.Series("gp", index=by_id.index)
    rows: list[dict[str, Any]] = []
    for norad_id in ids:
        cat = by_id.loc[norad_id]
        member = fleet[norad_id] if norad_id in fleet else None
        groups = cat["groups"]
        active = "active" in (list(groups) if groups is not None else [])
        rcs = float(cat["rcs_m2"]) if pd.notna(cat["rcs_m2"]) else None
        hbr, hbr_source = hard_body_radius_m(
            str(cat["category"]), rcs, member.hard_body_radius_m if member is not None else None
        )
        prior = manoeuvre_prior(str(cat["category"]), active, member.manoeuvres if member is not None else None)
        rows.append(
            {
                "norad_id": norad_id,
                "name": member.name if member is not None else str(cat["name"]),
                "category": str(cat["category"]),
                "altitude_band": str(cat["altitude_band"]),
                "is_primary": member is not None,
                "epoch": pd.Timestamp(cat["epoch"]),
                "ephemeris": str(ephemeris.get(norad_id, "gp")),
                "source": str(cat["source"]),
                "in_active_group": active,
                "rcs_m2": rcs if rcs is not None else np.nan,
                "hbr_m": hbr,
                "hbr_source": hbr_source,
                "manoeuvre_prior": prior,
                "manoeuvre_level": prior,
                "n_history_sets": 0,
                "n_jumps": 0,
                "jump_epochs": [],
                "last_jump": pd.NaT,
                "cov_source": None,
            }
        )
    df = pd.DataFrame(rows, columns=OBJECT_COLUMNS)
    df["epoch"] = pd.to_datetime(df["epoch"], utc=True)
    df["last_jump"] = pd.to_datetime(df["last_jump"], utc=True)
    return df


def apply_history(objects: pd.DataFrame, fit: Any) -> pd.DataFrame:
    """Fill the history-derived columns from a :class:`~driftwatch.risk.covariance.CovarianceFit`."""
    from driftwatch.risk.manoeuvre import promote

    out = objects.copy()
    table = fit.table[fit.table["kind"] == "object"].set_index("norad_id")
    levels, n_sets, n_jumps, epochs, last, sources = [], [], [], [], [], []
    for row in out.itertuples():
        det = fit.jumps.get(int(row.norad_id))
        n_j = det.n_jumps if det is not None else 0
        levels.append(promote(str(row.manoeuvre_prior), n_j))
        n_jumps.append(n_j)
        epochs.append([pd.Timestamp(t) for t in det.jump_epochs] if det is not None else [])
        last.append(max(det.jump_epochs) if det is not None and det.jump_epochs else pd.NaT)
        if int(row.norad_id) in table.index:
            n_sets.append(int(np.nan_to_num(table.loc[int(row.norad_id), "n_sets"])))
            sources.append(table.loc[int(row.norad_id), "source"])
        else:
            n_sets.append(0)
            sources.append(fit.model.growth_for(ObjectRef(int(row.norad_id), row.category, row.altitude_band))[1])
    out["manoeuvre_level"] = levels
    out["n_history_sets"] = n_sets
    out["n_jumps"] = n_jumps
    out["jump_epochs"] = epochs
    out["last_jump"] = pd.to_datetime(pd.Series(last, index=out.index), utc=True)
    out["cov_source"] = sources
    return out


RISK_COLUMNS: tuple[str, ...] = (
    "run_id",
    "snapshot",
    "model_version",
    "scenario",
    "event_id",
    "sigma_r_primary_km",
    "sigma_i_primary_km",
    "sigma_c_primary_km",
    "sigma_r_secondary_km",
    "sigma_i_secondary_km",
    "sigma_c_secondary_km",
    "cov_source_primary",
    "cov_source_secondary",
    "hbr_m",
    "enc_cov_xx_km2",
    "enc_cov_xy_km2",
    "enc_cov_yy_km2",
    "pc",
    "pc_alfano",
    "pc_chan",
    "pc_max",
    "pc_max_scale",
    "flag",
    "computed_at",
)
__all__ = ["OBJECT_COLUMNS", "RISK_COLUMNS", "STATE_COLUMNS", "apply_history", "objects_from_snapshot", "run_risk"]


def new_run_id(now: datetime | None = None) -> str:
    """A run id: the UTC stamp of the run plus a short random suffix."""
    return f"{stamp(now or datetime.now(UTC))}-{secrets.token_hex(2)}"


def model_version_string(model: CovarianceModel) -> str:
    """``<driftwatch version>+<model version>``, the ``model_version`` column."""
    return f"{__version__}+{model.version}"


def _covariances(
    model: CovarianceModel, objects: pd.DataFrame, norad_ids: np.ndarray, at: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Per-event RIC covariances ``(n, 3, 3)`` and source labels, one model call per distinct object."""
    by_id = objects.set_index("norad_id")
    cov = np.full((len(norad_ids), 3, 3), np.nan)
    source = np.empty(len(norad_ids), dtype=object)
    for norad_id in np.unique(norad_ids):
        idx = np.nonzero(norad_ids == norad_id)[0]
        row = by_id.loc[int(norad_id)]
        ref = ObjectRef(int(norad_id), str(row["category"]), str(row["altitude_band"]))
        result = model.covariance_ric(ref, row["epoch"].to_pydatetime(), at[idx])
        cov[idx] = result.cov_km2
        source[idx] = result.source
    return cov, source


def run_risk(
    events: pd.DataFrame,
    objects: pd.DataFrame,
    model: CovarianceModel,
    *,
    scenario: str,
    run_id: str,
    snapshot: str,
    sweep: bool = True,
    now: datetime | None = None,
) -> pd.DataFrame:
    """Covariance, probability of collision, maximum probability and flags for every stored event.

    ``events`` carries the geometry and both TEME states at the time of closest approach
    (see ``docs/data-schema.md``); ``objects`` the element-set epochs, categories, bands
    and hard-body radii. The combined covariance is the sum of the two objects'
    covariances rotated from their own RIC frames into TEME, projected onto the
    encounter plane. Returns one row per event in ``RISK_COLUMNS`` order.
    """
    now = now or datetime.now(UTC)
    n = len(events)
    if n == 0:
        return pd.DataFrame(columns=list(RISK_COLUMNS))
    p = events["primary_norad_id"].to_numpy(dtype=np.int64)
    s = events["secondary_norad_id"].to_numpy(dtype=np.int64)
    tca = pd.to_datetime(events["tca"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    r_p = events[["p_x_km", "p_y_km", "p_z_km"]].to_numpy(dtype=float)
    v_p = events[["p_vx_kms", "p_vy_kms", "p_vz_kms"]].to_numpy(dtype=float)
    r_s = events[["s_x_km", "s_y_km", "s_z_km"]].to_numpy(dtype=float)
    v_s = events[["s_vx_kms", "s_vy_kms", "s_vz_kms"]].to_numpy(dtype=float)
    dr = r_s - r_p
    dv = v_s - v_p

    cov_p, src_p = _covariances(model, objects, p, tca)
    cov_s, src_s = _covariances(model, objects, s, tca)
    combined = rotate_ric_to_teme(ric_basis(r_p, v_p), cov_p) + rotate_ric_to_teme(ric_basis(r_s, v_s), cov_s)
    plane = encounter_plane(dr, dv, combined)

    hbr = objects.set_index("norad_id")["hbr_m"]
    hbr_m = hbr.reindex(p).to_numpy(dtype=float) + hbr.reindex(s).to_numpy(dtype=float)
    radius_km = hbr_m / 1000.0
    pc = pc_foster(plane.miss_km, plane.cov_km2, radius_km)
    pc_a = pc_alfano(plane.miss_km, plane.cov_km2, radius_km)
    pc_c = pc_chan(plane.miss_km, plane.cov_km2, radius_km)
    if sweep:
        pc_max, scale, _ = max_pc_sweep(plane.miss_km, plane.cov_km2, radius_km)
    else:
        pc_max = np.full(n, np.nan)
        scale = np.full(n, np.nan)

    sig = np.sqrt(np.stack([cov_p[:, 0, 0], cov_p[:, 1, 1], cov_p[:, 2, 2]], axis=1))
    sig_s = np.sqrt(np.stack([cov_s[:, 0, 0], cov_s[:, 1, 1], cov_s[:, 2, 2]], axis=1))
    out = pd.DataFrame(
        {
            "run_id": run_id,
            "snapshot": snapshot,
            "model_version": model_version_string(model),
            "scenario": scenario,
            "event_id": events["event_id"].to_numpy(),
            "sigma_r_primary_km": sig[:, 0],
            "sigma_i_primary_km": sig[:, 1],
            "sigma_c_primary_km": sig[:, 2],
            "sigma_r_secondary_km": sig_s[:, 0],
            "sigma_i_secondary_km": sig_s[:, 1],
            "sigma_c_secondary_km": sig_s[:, 2],
            "cov_source_primary": src_p.astype(str),
            "cov_source_secondary": src_s.astype(str),
            "hbr_m": hbr_m,
            "enc_cov_xx_km2": plane.cov_km2[:, 0, 0],
            "enc_cov_xy_km2": plane.cov_km2[:, 0, 1],
            "enc_cov_yy_km2": plane.cov_km2[:, 1, 1],
            "pc": pc,
            "pc_alfano": pc_a,
            "pc_chan": pc_c,
            "pc_max": pc_max,
            "pc_max_scale": scale,
            "flag": flags(pc).astype(str),
            "computed_at": pd.Timestamp(now).tz_convert("UTC"),
        }
    )[list(RISK_COLUMNS)]
    with np.errstate(invalid="ignore", divide="ignore"):
        disagreement = np.abs(pc_a / pc - 1.0)
    meaningful = np.isfinite(disagreement) & (pc > 1e-12)
    log.info(
        "Risk (%s): %d events; %d red, %d yellow; max pc %.2e; "
        "Foster/Alfano disagreement max %.2e over %d events with pc > 1e-12",
        scenario,
        n,
        int((out["flag"] == "red").sum()),
        int((out["flag"] == "yellow").sum()),
        float(np.nanmax(pc)) if n else float("nan"),
        float(disagreement[meaningful].max()) if meaningful.any() else 0.0,
        int(meaningful.sum()),
    )
    return out
