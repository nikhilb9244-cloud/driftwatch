"""Covariance and probability over stored events, once per scenario.

The design rule for Phase 3: geometry and probability are separate. Stages A to C run
once per snapshot and write the events with both objects' TEME states at the time of
closest approach. A scenario reruns only this module over those stored events with its own
covariance model, and writes one row per event carrying the scenario, the run id, the
snapshot, the supplemental version and the model version. Nothing here propagates an orbit.

**Step 3 adds a mean shift.** A scenario may now say that an object is not where its element
set puts it, by returning an in-track displacement beside the covariance (see
:class:`~driftwatch.risk.covariance.RicCovariance`). The two objects' displacements are
rotated into TEME and applied to the stored positions, which moves the relative position and
therefore the miss; the uncertainty of each displacement is already in the in-track element of
its covariance by the time it arrives here.

Applying the shift at the *stored* time of closest approach rather than searching for a new
one is exact for what the probability depends on, not an approximation. The encounter plane is
perpendicular to the relative velocity, and the component of a shift along that direction is
precisely the part that moves the time of closest approach rather than the miss at it; the
projection removes it. What survives the projection is what changes the answer.

**Three probabilities, side by side.** A scenario does two things at once and they pull in
opposite directions often enough that one number hides both, so every row carries all three:

``pc``
    Both effects. The objects are moved by the scenario's mean shift and the covariance carries
    the shift's uncertainty. The primary number.
``pc_shift_only``
    The objects are moved, but scored against the covariance the run would have had without the
    storm layer. What the displacement alone does to the geometry.
``pc_variance_only``
    The covariance is the scenario's, but the objects are left where their element sets put
    them. What the added uncertainty alone does.

Under a model with no storm layer the three are the same array and the quiet scenario is
unchanged from Phase 2.

**And some events carry none of them.** The storm term is derived under a small-perturbation
linearisation. An object whose in-track displacement has run past
:data:`driftwatch.config.STORM_MAX_SHIFT_REVOLUTIONS` of its orbit's circumference is outside
it, and a probability computed from such a position would be arithmetic without a claim behind
it. Those events are reported **unscoreable**: NaN in every probability column, ``unscoreable``
as the region and the flag, the reason on the row, and excluded from every aggregate. Nothing
is dropped -- the event, its geometry, its covariance and its shift all stay -- but no number
is offered that a reader could act on. See :func:`unscoreable_events`.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import __version__, config
from driftwatch.catalogue.classify import rcs_class
from driftwatch.fleet import Fleet
from driftwatch.orbit.time import stamp
from driftwatch.risk.covariance import CovarianceModel, ObjectRef
from driftwatch.risk.manoeuvre import manoeuvre_prior
from driftwatch.risk.pc import (
    SLOW_ENCOUNTER_KMS,
    confidences,
    encounter_plane,
    flags,
    max_pc_sweep,
    pc_alfano,
    pc_chan,
    pc_foster,
    regions,
    rotate_ric_to_teme,
    slow_encounters,
)
from driftwatch.screening.ric import ric_basis
from driftwatch.screening.stages import STATE_COLUMNS
from driftwatch.storm.term import event_validities

log = logging.getLogger(__name__)

# Hard-body radius for secondaries: the circumscribing sphere of a typical member of the
# category in metres, and whether the objects in it have a known envelope at all.
# Starlink: V1.5 spans about 11 m, V2 Mini about 30 m with both arrays; 10 m is between.
# OneWeb and the other constellations: 1 m buses with 3 to 5 m arrays. Payload: a wide
# class; 3 m is a small bus with panels. Rocket body: half the length of a typical upper
# stage. Debris: fragments are mostly well under a metre. Unknown: analyst objects.
# The four categories flagged True are the ones whose members have no known envelope; they
# are the ones SPAN_RADIUS_M below serves, and the ones the radar cross-section was used for.
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

# The radius of a typical object of each type and radar cross-section class, in metres,
# derived from ESA's Kelvins collision-avoidance data by
# :func:`driftwatch.risk.kelvins.chaser_radius_table` (2026-09-02, 162,634 rows; re-derive it
# with ``driftwatch kelvins``). Half the median chaser span of the cell, because ESA's own
# risk column is reproduced by the combined radius ``(t_span + c_span) / 2`` with no fitted
# parameter at all. Cells with fewer than a hundred rows take the object type's overall
# median instead.
#
# Why this replaced ``sqrt(RCS / pi)``. That formula gives the radius of the disc that would
# return the same radar echo, which is not the size of the object: it understates anything
# much larger than the radar wavelength and anything with a low-return geometry. Tested
# against these same rows at the Phase 3 Step 0 review it needed a free multiplier of nearly
# five and still did no better than one radius for everything, while ESA's spans reproduced
# their risk column exactly. The cross-section survives here only as a *class* -- small,
# medium, large -- which is the part of it that does carry size information.
#
# Read these as a population median, not a measurement of any one object. Most cells come out
# at exactly 1.0 m because ESA defaults an unpublished span to 2.0 m; that default is a
# screening convention, deliberately generous for an object whose size nobody knows, and
# adopting it is what makes these probabilities comparable with ESA's. It raises the
# probability of a conjunction with a small fragment by two orders of magnitude against the
# radar-cross-section formula. ``docs/kelvins-reproduction.md`` carries the derivation.
SPAN_RADIUS_M: dict[tuple[str, str], float] = {
    ("debris", "small"): 1.00,
    ("debris", "medium"): 1.00,
    ("debris", "large"): 1.25,
    ("debris", "unknown"): 1.00,
    ("payload", "small"): 1.00,
    ("payload", "medium"): 1.00,
    ("payload", "large"): 4.55,
    ("payload", "unknown"): 1.50,
    ("rocket_body", "small"): 1.50,
    ("rocket_body", "medium"): 1.50,
    ("rocket_body", "large"): 1.90,
    ("rocket_body", "unknown"): 1.50,
    ("unknown", "small"): 1.00,
    ("unknown", "medium"): 1.00,
    ("unknown", "large"): 1.00,
    ("unknown", "unknown"): 1.00,
}


def span_radius_m(category: str, rcs_m2: float | None) -> float | None:
    """The looked-up radius for a category with no known envelope, or None for a category that has one."""
    return SPAN_RADIUS_M.get((str(category), rcs_class(rcs_m2)))


def hard_body_radius_m(category: str, rcs_m2: float | None, fleet_radius_m: float | None = None) -> tuple[float, str]:
    """The hard-body radius for one object and where it came from.

    The fleet file's own value wins outright. Otherwise the object gets the largest of what
    the remaining rules say, because every one of them is a lower bound on a size nobody has
    published: the category default, the radar cross-section's equivalent radius, and the
    population median span of the object's type and cross-section class
    (:data:`SPAN_RADIUS_M`). The label says which won: ``fleet``, ``category``, ``rcs`` or
    ``span``.
    """
    if fleet_radius_m is not None:
        return float(fleet_radius_m), "fleet"
    default, unknown_envelope = SECONDARY_HBR_M.get(str(category), SECONDARY_HBR_M["unknown"])
    radius, source = default, "category"
    if unknown_envelope:
        if rcs_m2 is not None and np.isfinite(rcs_m2) and rcs_m2 > 0:
            from_rcs = float(np.clip(np.sqrt(rcs_m2 / np.pi), RCS_RADIUS_MIN_M, RCS_RADIUS_MAX_M))
            if from_rcs > radius:
                radius, source = from_rcs, "rcs"
        from_span = span_radius_m(category, rcs_m2)
        if from_span is not None and from_span > radius:
            radius, source = float(from_span), "span"
    return radius, source


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


def refresh_hard_body_radii(objects: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Recompute ``hbr_m`` and ``hbr_source`` for a stored run from the current rules.

    The radius is a model parameter, not a measurement of the run, so rescoring stored events
    has to use the rules the code holds now rather than the ones it held when the events were
    screened; otherwise a change to :data:`SPAN_RADIUS_M` would never reach a stored run.
    Rows whose radius came from the fleet file are left alone -- that is the operator's own
    number, and the fleet file is not part of the stored run. Returns the objects and a
    summary of what moved, for the log.
    """
    out = objects.copy()
    if not len(out):
        return out, {"n_changed": 0}
    before = pd.to_numeric(out["hbr_m"], errors="coerce").to_numpy(dtype=float)
    radii, sources = [], []
    for row in out.itertuples():
        if str(row.hbr_source) == "fleet":
            radii.append(float(row.hbr_m))
            sources.append("fleet")
            continue
        rcs = float(row.rcs_m2) if pd.notna(row.rcs_m2) else None
        radius, source = hard_body_radius_m(str(row.category), rcs)
        radii.append(radius)
        sources.append(source)
    out["hbr_m"] = radii
    out["hbr_source"] = sources
    after = np.asarray(radii, dtype=float)
    changed = ~np.isclose(before, after, rtol=1e-9, atol=1e-12)
    summary: dict[str, Any] = {
        "n_objects": int(len(out)),
        "n_changed": int(changed.sum()),
        "by_source": out["hbr_source"].value_counts().to_dict(),
    }
    if changed.any():
        summary["median_ratio"] = round(float(np.median(after[changed] / np.maximum(before[changed], 1e-9))), 3)
    return out, summary


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
    "supplemental_version",
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
    "pc_shift_only",
    "pc_variance_only",
    "pc_alfano",
    "pc_chan",
    "pc_max",
    "pc_max_scale",
    "miss_shifted_km",
    "shift_i_primary_km",
    "shift_i_secondary_km",
    "relative_shift_km",
    "sigma_shift_i_primary_km",
    "sigma_shift_i_secondary_km",
    "storm_source_primary",
    "storm_source_secondary",
    "storm_validity",
    "region",
    "flag",
    "confidence",
    "scoreable",
    "unscoreable_reason",
    "slow_encounter",
    "computed_at",
)
__all__ = [
    "OBJECT_COLUMNS",
    "RISK_COLUMNS",
    "STATE_COLUMNS",
    "apply_history",
    "objects_from_snapshot",
    "refresh_hard_body_radii",
    "run_risk",
]


def new_run_id(now: datetime | None = None) -> str:
    """A run id: the UTC stamp of the run plus a short random suffix."""
    return f"{stamp(now or datetime.now(UTC))}-{secrets.token_hex(2)}"


def model_version_string(model: CovarianceModel) -> str:
    """``<driftwatch version>+<model version>``, the ``model_version`` column."""
    return f"{__version__}+{model.version}"


def _covariances(
    model: CovarianceModel, objects: pd.DataFrame, norad_ids: np.ndarray, at: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-event RIC covariances ``(n, 3, 3)``, source labels and mean shifts ``(n, 3)`` in km.

    One model call per distinct object, whatever the model is. A model that returns no shift
    -- every Phase 2 one -- contributes zeros, so the arithmetic downstream is the same and
    the quiet scenario comes out bit for bit as it did.
    """
    by_id = objects.set_index("norad_id")
    cov = np.full((len(norad_ids), 3, 3), np.nan)
    shift = np.zeros((len(norad_ids), 3))
    source = np.empty(len(norad_ids), dtype=object)
    for norad_id in np.unique(norad_ids):
        idx = np.nonzero(norad_ids == norad_id)[0]
        row = by_id.loc[int(norad_id)]
        ref = ObjectRef(int(norad_id), str(row["category"]), str(row["altitude_band"]))
        result = model.covariance_ric(ref, row["epoch"].to_pydatetime(), at[idx])
        cov[idx] = result.cov_km2
        source[idx] = result.source
        if result.mean_shift_ric_km is not None:
            shift[idx] = np.asarray(result.mean_shift_ric_km, dtype=float)
    return cov, source, shift


def _storm_label(source: np.ndarray) -> np.ndarray:
    """The ``storm:<b source>`` part of a covariance source label, or ``none``."""
    return np.array([str(s).split("+storm:")[-1] if "+storm:" in str(s) else "none" for s in source], dtype=object)


def unscoreable_events(model: CovarianceModel, primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    """One reason string per event, empty where the event can be scored.

    An event is unscoreable when either object's storm term has run outside the linear theory
    it was derived under -- an in-track displacement past
    :data:`driftwatch.config.STORM_MAX_SHIFT_REVOLUTIONS` of the orbit's circumference. Past
    that the term is no longer a small correction to a known position, and a probability
    computed from it would be a number with no claim behind it. So none is reported: the row
    keeps its geometry, its covariance and its reason, and carries NaN where the probabilities
    would have been.

    Models with no storm layer -- every Phase 2 one, and ``quiet`` -- return no reasons at all,
    which is what keeps them unchanged.
    """
    shifts = getattr(model, "shifts", None)
    reasons = np.full(len(primary), "", dtype=object)
    if not shifts:
        return reasons
    per_object = {int(k): v.unscoreable_reason() for k, v in shifts.items() if not v.scoreable}
    if not per_object:
        return reasons
    for index, (p, s) in enumerate(zip(primary, secondary, strict=True)):
        parts = [per_object[int(o)] for o in (p, s) if int(o) in per_object]
        if parts:
            reasons[index] = "; ".join(parts)
    return reasons


def run_risk(
    events: pd.DataFrame,
    objects: pd.DataFrame,
    model: CovarianceModel,
    *,
    scenario: str,
    run_id: str,
    snapshot: str,
    supplemental_version: str = "",
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

    cov_p, src_p, shift_p = _covariances(model, objects, p, tca)
    cov_s, src_s, shift_s = _covariances(model, objects, s, tca)
    basis_p = ric_basis(r_p, v_p)
    basis_s = ric_basis(r_s, v_s)
    combined = rotate_ric_to_teme(basis_p, cov_p) + rotate_ric_to_teme(basis_s, cov_s)
    # The scenario's mean shifts, out of each object's own RIC frame and into TEME. The basis
    # rows are the R, I and C unit vectors, so the transpose takes RIC components to TEME.
    dr_shift = np.einsum("nji,nj->ni", basis_s, shift_s) - np.einsum("nji,nj->ni", basis_p, shift_p)
    dr_shift = np.nan_to_num(dr_shift, nan=0.0)
    shifted = bool(np.any(dr_shift))
    # What the covariance would have been without the storm layer. It serves two purposes: the
    # report can say how much in-track sigma the scenario added rather than only what it is
    # now, and it is the covariance the *shift-only* probability is computed against.
    base = getattr(model, "base", None) if hasattr(model, "shifts") else None
    if base is not None:
        cov_p_base, _, _ = _covariances(base, objects, p, tca)
        cov_s_base, _, _ = _covariances(base, objects, s, tca)
        combined_base = rotate_ric_to_teme(basis_p, cov_p_base) + rotate_ric_to_teme(basis_s, cov_s_base)
    else:
        cov_p_base, cov_s_base, combined_base = cov_p, cov_s, combined

    # Three probabilities, so a reader never has to take on trust which half of a scenario did
    # the work: the shift moves the objects and the variance widens the ellipse, and they pull
    # in opposite directions often enough that the combined number alone hides both.
    #   pc                 both: the objects moved and the covariance grew.  The primary number.
    #   pc_shift_only      the objects moved, the covariance is the one the run would have had.
    #   pc_variance_only   the covariance grew, the objects are where their element sets put them.
    plane = encounter_plane(dr + dr_shift, dv, combined)
    plane_shift_only = encounter_plane(dr + dr_shift, dv, combined_base) if base is not None else plane
    plane_unshifted = encounter_plane(dr, dv, combined) if shifted else plane

    hbr = objects.set_index("norad_id")["hbr_m"]
    hbr_m = hbr.reindex(p).to_numpy(dtype=float) + hbr.reindex(s).to_numpy(dtype=float)
    radius_km = hbr_m / 1000.0
    pc = pc_foster(plane.miss_km, plane.cov_km2, radius_km)
    pc_shift_only = (
        pc if plane_shift_only is plane else pc_foster(plane_shift_only.miss_km, plane_shift_only.cov_km2, radius_km)
    )
    pc_variance_only = (
        pc if plane_unshifted is plane else pc_foster(plane_unshifted.miss_km, plane_unshifted.cov_km2, radius_km)
    )
    pc_a = pc_alfano(plane.miss_km, plane.cov_km2, radius_km)
    pc_c = pc_chan(plane.miss_km, plane.cov_km2, radius_km)
    if sweep:
        pc_max, scale, _ = max_pc_sweep(plane.miss_km, plane.cov_km2, radius_km)
    else:
        pc_max = np.full(n, np.nan)
        scale = np.full(n, np.nan)

    sig = np.sqrt(np.stack([cov_p[:, 0, 0], cov_p[:, 1, 1], cov_p[:, 2, 2]], axis=1))
    sig_s = np.sqrt(np.stack([cov_s[:, 0, 0], cov_s[:, 1, 1], cov_s[:, 2, 2]], axis=1))
    region = regions(scale)
    flag = flags(pc)
    slow = slow_encounters(np.linalg.norm(dv, axis=1))

    # Events whose storm term ran outside the linear theory carry no probability at all. The
    # geometry, the covariance, the shift and the reason stay on the row; every probability
    # column goes to NaN and the flag says `unscoreable`, so nothing downstream can sum, rank
    # or threshold them by accident. Under quiet there are none and nothing below runs.
    # How far Step 4's validation reaches, per event, from the weaker of the two coefficient
    # sources. Not a weighting and not a filter: the numbers are identical either way, and the
    # label is what every aggregate downstream is split on. See `storm.term.event_validity`.
    storm_p, storm_s = _storm_label(src_p), _storm_label(src_s)

    reason = unscoreable_events(model, p, s)
    unscoreable = reason != ""
    if unscoreable.any():
        # `np.where` rather than assignment: several of these are the *same array* when a
        # scenario applies no shift, and masking in place would reach further than intended.
        pc, pc_shift_only, pc_variance_only, pc_a, pc_c, pc_max, scale = (
            np.where(unscoreable, np.nan, values)
            for values in (pc, pc_shift_only, pc_variance_only, pc_a, pc_c, pc_max, scale)
        )
        region = np.where(unscoreable, "unscoreable", region).astype(object)
        flag = np.where(unscoreable, "unscoreable", flag).astype(object)
    out = pd.DataFrame(
        {
            "run_id": run_id,
            "snapshot": snapshot,
            "model_version": model_version_string(model),
            "supplemental_version": supplemental_version,
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
            "pc_shift_only": pc_shift_only,
            "pc_variance_only": pc_variance_only,
            "pc_alfano": pc_a,
            "pc_chan": pc_c,
            "pc_max": pc_max,
            "pc_max_scale": scale,
            "miss_shifted_km": plane.miss_km[:, 0],
            "shift_i_primary_km": shift_p[:, 1],
            "shift_i_secondary_km": shift_s[:, 1],
            "relative_shift_km": np.linalg.norm(dr_shift, axis=1),
            "sigma_shift_i_primary_km": np.sqrt(np.maximum(cov_p[:, 1, 1] - cov_p_base[:, 1, 1], 0.0)),
            "sigma_shift_i_secondary_km": np.sqrt(np.maximum(cov_s[:, 1, 1] - cov_s_base[:, 1, 1], 0.0)),
            "storm_source_primary": storm_p,
            "storm_source_secondary": storm_s,
            "storm_validity": event_validities(storm_p, storm_s).astype(str),
            "region": region.astype(str),
            "flag": flag.astype(str),
            "confidence": np.where(unscoreable, "none", confidences(region)).astype(str),
            "scoreable": ~unscoreable,
            "unscoreable_reason": reason.astype(str),
            "slow_encounter": slow,
            "computed_at": pd.Timestamp(now).tz_convert("UTC"),
        }
    )[list(RISK_COLUMNS)]
    with np.errstate(invalid="ignore", divide="ignore"):
        disagreement = np.abs(pc_a / pc - 1.0)
    meaningful = np.isfinite(disagreement) & (pc > 1e-12)
    flagged = out["flag"].isin(("red", "yellow"))
    if unscoreable.any():
        log.warning(
            "Unscoreable (%s): %d of %d events involve an object whose in-track shift ran past "
            "%g of its orbit's circumference; they carry no probability and are excluded from "
            "every aggregate below. %d distinct objects, %d events. First reason: %s",
            scenario,
            int(unscoreable.sum()),
            n,
            config.STORM_MAX_SHIFT_REVOLUTIONS,
            len({int(o) for o in np.concatenate([p[unscoreable], s[unscoreable]])}),
            int(unscoreable.sum()),
            reason[unscoreable][0],
        )
    log.info(
        "Risk (%s): %d events scored of %d; %d red, %d yellow (%d of the %d flagged are in the "
        "dilution region, reported at low confidence); max pc %.2e; "
        "Foster/Alfano disagreement max %.2e over %d events with pc > 1e-12",
        scenario,
        int((~unscoreable).sum()),
        n,
        int((out["flag"] == "red").sum()),
        int((out["flag"] == "yellow").sum()),
        int((flagged & (out["region"] == "dilution")).sum()),
        int(flagged.sum()),
        float(np.nanmax(pc)) if np.isfinite(pc).any() else float("nan"),
        float(disagreement[meaningful].max()) if meaningful.any() else 0.0,
        int(meaningful.sum()),
    )
    relative = out["relative_shift_km"].to_numpy(dtype=float)
    if np.any(relative > 0):
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = np.where(pc_variance_only > 0, pc / pc_variance_only, np.nan)
            absolute = 0.5 * (np.abs(shift_p[:, 1]) + np.abs(shift_s[:, 1]))
            cancellation = np.where(absolute > 0, relative / absolute, np.nan)
        interesting = np.isfinite(ratio) & (pc_variance_only > 1e-12) & ~unscoreable
        moved = (relative > 0) & ~unscoreable
    if np.any(relative > 0) and moved.any():
        log.info(
            "Storm term (%s): the in-track shift moves %d of %d scoreable events by a median %.3f km "
            "relative against a median %.3f km absolute, a relative-to-absolute ratio of %.3f; "
            "pc/pc_variance_only over the %d events above 1e-12 runs %.2f to %.2f",
            scenario,
            int(moved.sum()),
            int((~unscoreable).sum()),
            float(np.median(relative[moved])),
            float(np.median(absolute[moved])),
            float(np.nanmedian(cancellation[moved])),
            int(interesting.sum()),
            float(np.nanmin(ratio[interesting])) if interesting.any() else float("nan"),
            float(np.nanmax(ratio[interesting])) if interesting.any() else float("nan"),
        )
    if slow.any():
        log.info(
            "Slow encounters (%s): %d of %d events are below %g km/s relative, %d of them flagged; "
            "their probability is a known underestimate of the two-dimensional method",
            scenario,
            int(slow.sum()),
            n,
            SLOW_ENCOUNTER_KMS,
            int((slow & flagged.to_numpy()).sum()),
        )
    return out
