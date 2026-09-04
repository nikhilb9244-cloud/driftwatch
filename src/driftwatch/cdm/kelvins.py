"""ESA's Kelvins collision-avoidance rows as Conjunction Data Messages, and as the events to match them to.

The Kelvins challenge data (`docs/kelvins-reproduction.md`) are real operational CDMs with the
identities taken out: no designators, no absolute times, only ``time_to_tca`` and per-mission
``mission_id`` and per-conjunction ``event_id`` integers. Everything else a CDM carries is there
under a different name -- the miss, the RTN relative position and velocity, both covariances as
sigmas and correlations, the orbit-determination quality fields, the object type and the
operator's own probability as ``risk`` (log10). So a row can be written back out as a message
that is realistic in every field the matcher and the report read, and unreal only in the two
fields that were anonymised, which are given deterministic synthetic values and labelled as such.

That makes the rows a test input for the whole path -- parse, match, report -- against a
population of 160,000 real operational numbers, before a real operator has sent a real message.
It does not make them a validation of anything: the events the messages are matched against
here are built from the same rows, so agreement is by construction. What is exercised is the
plumbing, and what is measured is nothing.

**The synthetic identities.** A mission becomes ``OBJECT1 = 900000 + mission_id`` and a
conjunction becomes ``OBJECT2 = 800000 + event_id``, which are integers a NORAD id column will
hold and which no real object carries (the catalogue is under 100,000 and the Alpha-5 encoding
stops at 339,999). The time of closest approach is a fixed reference epoch plus a deterministic
offset spread over a week, keyed on the event id, and the creation date is that minus
``time_to_tca``. Every message carries a COMMENT saying so.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch.cdm.parse import ConjunctionDataMessage, format_epoch, to_kvn
from driftwatch.risk.pc import flags

#: Where the synthetic identities start. See the module docstring.
MISSION_BASE = 900_000
EVENT_BASE = 800_000
#: The default reference epoch: the first day of the Gannon storm window, so the synthetic week
#: sits where the rest of the project's replay material does.
DEFAULT_REFERENCE_EPOCH = datetime(2024, 5, 9, tzinfo=UTC)
#: Kelvins floors an unreported probability at log10 = -30; below this the message carries none.
RISK_FLOOR = -29.0

_OD_FIELDS: tuple[tuple[str, str, str | None, float], ...] = (
    # (Kelvins column suffix, CDM key, unit, scale)
    ("recommended_od_span", "RECOMMENDED_OD_SPAN", "d", 1.0),
    ("actual_od_span", "ACTUAL_OD_SPAN", "d", 1.0),
    ("obs_available", "OBS_AVAILABLE", None, 1.0),
    ("obs_used", "OBS_USED", None, 1.0),
    ("residuals_accepted", "RESIDUALS_ACCEPTED", "%", 1.0),
    ("weighted_rms", "WEIGHTED_RMS", None, 1.0),
    ("cd_area_over_mass", "CD_AREA_OVER_MASS", "m**2/kg", 1.0),
    ("cr_area_over_mass", "CR_AREA_OVER_MASS", "m**2/kg", 1.0),
    ("sedr", "SEDR", "W/kg", 1.0),
)

_OBJECT_TYPES = {"DEBRIS": "DEBRIS", "PAYLOAD": "PAYLOAD", "ROCKET BODY": "ROCKET BODY", "UNKNOWN": "UNKNOWN"}


def synthetic_tca(event_id: int, reference_epoch: datetime = DEFAULT_REFERENCE_EPOCH) -> pd.Timestamp:
    """A deterministic time of closest approach inside the week after the reference epoch.

    Spread by the event id so that conjunctions of one mission do not pile onto one instant:
    a whole number of days from ``event_id % 7`` and a fraction from a fixed multiplier, both
    reproducible from the id alone.
    """
    days = (int(event_id) % 7) + ((int(event_id) * 0.6180339887) % 1.0)
    return pd.Timestamp(reference_epoch) + pd.Timedelta(seconds=round(days * 86400.0))


def object1_designator(mission_id: int) -> int:
    return MISSION_BASE + int(mission_id)


def object2_designator(event_id: int) -> int:
    return EVENT_BASE + int(event_id)


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _covariance_terms(row: pd.Series, prefix: str) -> dict[str, float]:
    """The six CDM covariance terms in m^2 from Kelvins' sigmas (m) and correlation coefficients."""
    s_r, s_t, s_n = (float(row[f"{prefix}_sigma_{k}"]) for k in ("r", "t", "n"))
    rho_tr = float(row.get(f"{prefix}_ct_r", 0.0) or 0.0)
    rho_nr = float(row.get(f"{prefix}_cn_r", 0.0) or 0.0)
    rho_nt = float(row.get(f"{prefix}_cn_t", 0.0) or 0.0)
    return {
        "CR_R": s_r * s_r,
        "CT_R": rho_tr * s_t * s_r,
        "CT_T": s_t * s_t,
        "CN_R": rho_nr * s_n * s_r,
        "CN_T": rho_nt * s_n * s_t,
        "CN_N": s_n * s_n,
    }


def kelvins_row_to_cdm(
    row: pd.Series,
    *,
    reference_epoch: datetime = DEFAULT_REFERENCE_EPOCH,
    originator: str = "ESA KELVINS (ANONYMISED)",
) -> ConjunctionDataMessage:
    """One challenge row as a message. Every field the row has goes in; the two it lacks are synthetic."""
    event_id = int(row["event_id"])
    mission_id = int(row.get("mission_id", 0) or 0)
    tca = synthetic_tca(event_id, reference_epoch)
    time_to_tca = float(row.get("time_to_tca", 0.0) or 0.0)
    created = tca - pd.Timedelta(seconds=round(time_to_tca * 86400.0))
    cdm = ConjunctionDataMessage(form="kvn", source=f"kelvins:event={event_id}:t-{time_to_tca:.3f}d")
    cdm.comments.append(
        "Built from an anonymised row of ESA's Kelvins Collision Avoidance Challenge data. The object "
        "designators and every time in this message are synthetic and deterministic; the miss, the "
        "relative state, the covariances, the orbit-determination fields and the probability are the row's own."
    )
    cdm.raw.update(
        {
            "CCSDS_CDM_VERS": 1.0,
            "CREATION_DATE": format_epoch(created),
            "ORIGINATOR": originator,
            "MESSAGE_FOR": f"MISSION {mission_id}",
            "MESSAGE_ID": f"KELVINS-{event_id}-{int(round(time_to_tca * 1000)):06d}",
            "TCA": format_epoch(tca),
            "MISS_DISTANCE": float(row["miss_distance"]),
            "RELATIVE_SPEED": float(row["relative_speed"]) if _finite(row.get("relative_speed")) else np.nan,
            "RELATIVE_POSITION_R": float(row["relative_position_r"]),
            "RELATIVE_POSITION_T": float(row["relative_position_t"]),
            "RELATIVE_POSITION_N": float(row["relative_position_n"]),
            "RELATIVE_VELOCITY_R": float(row["relative_velocity_r"]),
            "RELATIVE_VELOCITY_T": float(row["relative_velocity_t"]),
            "RELATIVE_VELOCITY_N": float(row["relative_velocity_n"]),
        }
    )
    cdm.units.update(
        {
            "MISS_DISTANCE": "m",
            "RELATIVE_SPEED": "m/s",
            **{f"RELATIVE_POSITION_{k}": "m" for k in ("R", "T", "N")},
            **{f"RELATIVE_VELOCITY_{k}": "m/s" for k in ("R", "T", "N")},
        }
    )
    risk = float(row.get("risk", np.nan))
    if np.isfinite(risk) and risk > RISK_FLOOR:
        cdm.raw["COLLISION_PROBABILITY"] = float(10.0**risk)
        cdm.raw["COLLISION_PROBABILITY_METHOD"] = "FOSTER-1992"
    for obj, prefix, designator, object_type in (
        (cdm.object1, "t", object1_designator(mission_id), "PAYLOAD"),
        (
            cdm.object2,
            "c",
            object2_designator(event_id),
            _OBJECT_TYPES.get(str(row.get("c_object_type", "")).upper(), "UNKNOWN"),
        ),
    ):
        kind, number = ("MISSION", mission_id) if prefix == "t" else ("EVENT", event_id)
        obj.raw.update(
            {
                "OBJECT": obj.role,
                "OBJECT_DESIGNATOR": designator,
                "CATALOG_NAME": "KELVINS-SYNTHETIC",
                "OBJECT_NAME": f"KELVINS {kind} {number}",
                "INTERNATIONAL_DESIGNATOR": "UNKNOWN",
                "OBJECT_TYPE": object_type,
                "EPHEMERIS_NAME": "NONE",
                "COVARIANCE_METHOD": "CALCULATED",
                "MANEUVERABLE": "YES" if prefix == "t" else "N/A",
                "REF_FRAME": "EME2000",
            }
        )
        for suffix, key, unit, scale in _OD_FIELDS:
            value = row.get(f"{prefix}_{suffix}")
            if _finite(value):
                obj.raw[key] = float(value) * scale
                if unit:
                    obj.units[key] = unit
        for key, when in (("TIME_LASTOB_START", "lastob_start"), ("TIME_LASTOB_END", "lastob_end")):
            value = row.get(f"{prefix}_time_{when}")
            if _finite(value):
                obj.raw[key] = format_epoch(created - pd.Timedelta(seconds=round(float(value) * 86400.0)))
        if all(_finite(row.get(f"{prefix}_sigma_{k}")) for k in ("r", "t", "n")):
            obj.raw.update(_covariance_terms(row, prefix))
            obj.units.update({k: "m**2" for k in ("CR_R", "CT_R", "CT_T", "CN_R", "CN_T", "CN_N")})
    return cdm


def kelvins_to_cdms(
    frame: pd.DataFrame,
    *,
    reference_epoch: datetime = DEFAULT_REFERENCE_EPOCH,
    limit: int | None = None,
) -> list[ConjunctionDataMessage]:
    """Every row as a message, in the frame's order, optionally the first ``limit`` rows only."""
    rows = frame if limit is None else frame.head(int(limit))
    return [kelvins_row_to_cdm(row, reference_epoch=reference_epoch) for _, row in rows.iterrows()]


def kelvins_events(frame: pd.DataFrame, *, reference_epoch: datetime = DEFAULT_REFERENCE_EPOCH) -> pd.DataFrame:
    """The distinct conjunctions in the rows, shaped like driftwatch's joined conjunction rows.

    One row per ``event_id``, taken from the message closest to its time of closest approach
    (the operator's last word), with the columns the matcher and the report read. The
    probability is the row's own, and the flag is driftwatch's thresholds applied to it, so a
    matcher test can ask about flags without a screening run. Region and confidence are
    ``unknown`` and ``low``: nothing here ran a covariance sweep.
    """
    if not len(frame):
        return pd.DataFrame()
    last = frame.sort_values("time_to_tca").drop_duplicates("event_id", keep="first")
    pc = np.where(last["risk"] > RISK_FLOOR, 10.0 ** last["risk"].to_numpy(dtype=float), 0.0)
    out = pd.DataFrame(
        {
            "event_id": [f"kelvins:{int(e)}" for e in last["event_id"]],
            "scenario": "quiet",
            "primary_norad_id": [object1_designator(m) for m in last.get("mission_id", pd.Series(0, index=last.index))],
            "secondary_norad_id": [object2_designator(e) for e in last["event_id"]],
            "tca": [synthetic_tca(int(e), reference_epoch) for e in last["event_id"]],
            "miss_km": last["miss_distance"].to_numpy(dtype=float) / 1000.0,
            "miss_shifted_km": last["miss_distance"].to_numpy(dtype=float) / 1000.0,
            "rel_speed_kms": pd.to_numeric(last.get("relative_speed"), errors="coerce").to_numpy(dtype=float) / 1000.0,
            "pc": pc,
            "flag": flags(pc),
            "region": "unknown",
            "confidence": "low",
            "storm_validity": "none",
        }
    )
    out["tca"] = pd.to_datetime(out["tca"], utc=True)
    return out.reset_index(drop=True)


def write_cdms(cdms: list[ConjunctionDataMessage], out_dir: Path) -> list[Path]:
    """One ``.kvn`` file per message, named by its MESSAGE_ID."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for cdm in cdms:
        name = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in cdm.message_id or "cdm")
        path = out_dir / f"{name}.kvn"
        path.write_text(to_kvn(cdm), encoding="utf-8")
        paths.append(path)
    return paths


__all__ = [
    "DEFAULT_REFERENCE_EPOCH",
    "EVENT_BASE",
    "MISSION_BASE",
    "kelvins_events",
    "kelvins_row_to_cdm",
    "kelvins_to_cdms",
    "object1_designator",
    "object2_designator",
    "synthetic_tca",
    "write_cdms",
]
