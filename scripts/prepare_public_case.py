"""Prepare a public TLE/OMM case from one stored basic GP record, before evaluating it."""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from sgp4.exporter import export_tle

from driftwatch.case_bundle import SCHEMA, encode, sha
from driftwatch.catalogue.history import read_history
from driftwatch.catalogue.snapshot import OMM_FIELDS
from driftwatch.imports import CONVENTIONS, decode_orbit
from driftwatch.orbit.propagator import build_satrecs


def prepare(history_path, destination):
    if destination.exists():
        raise ValueError("Prepare the case in a new directory")
    rows = read_history(history_path, norad_ids=[39452]).sort_values("epoch")
    rows = rows[rows.epoch.between("2024-04-01T00:00:00Z", "2024-04-30T23:59:59Z")]
    if not len(rows) or rows.iloc[0].source != "spacetrack":
        raise ValueError("The declared public Swarm A history record is absent")
    row = rows.iloc[0]
    record = {}
    for field, column in OMM_FIELDS.items():
        value = row[column]
        if isinstance(value, pd.Timestamp):
            value = value.isoformat()
        elif hasattr(value, "item"):
            value = value.item()
        record[field] = value
    record.update(CONVENTIONS)
    sat = build_satrecs(rows.iloc[:1])[0]
    designator = str(row.object_id)
    sat.intldesg = designator[2:4] + designator[5:]
    sat.classification = str(row.classification)
    sat.elnum = int(row.element_set_no)
    sat.revnum = int(row.rev_at_epoch)
    tle = (str(row["name"]) + "\n" + "\n".join(export_tle(sat)) + "\n").encode()
    candidate = encode([record])
    source_id = f"spacetrack:gp_history/NORAD_CAT_ID/39452/EPOCH/{row.epoch.isoformat()}"
    rights = {
        "redistribution_permitted": True,
        "basis": "Space-Track basic SSA redistribution permission conditioned on citation",
        "terms_url": "https://www.space-track.org/documentation#odr",
        "checked_on": datetime.now(UTC).date().isoformat(),
        "attribution": "Element sets from Space-Track.org (USSPACECOM / 18th Space Defense Squadron), "
        "redistributed with citation under the Space-Track user agreement.",
    }
    inputs = {}
    for role, name, raw in (("baseline", "baseline.tle", tle), ("candidate", "candidate.json", candidate)):
        decoded = decode_orbit(raw.decode())
        inputs[role] = {
            "path": "supplied/" + name,
            "sha256": sha(raw),
            "rights": rights,
            "source_identifier": source_id,
            "source_store_sha256": sha(history_path.read_bytes()),
            "derivation": "TLE re-encoding" if role == "baseline" else "OMM-keyword JSON from stored GP fields",
            "state_epoch": pd.Timestamp(decoded.records[0]["EPOCH"]).isoformat()
            + ("Z" if pd.Timestamp(decoded.records[0]["EPOCH"]).tzinfo is None else ""),
            "provider_created_at": None if pd.isna(row.provider_created_at) else row.provider_created_at.isoformat(),
            "published_at": None if pd.isna(row.published_at) else row.published_at.isoformat(),
            "retrieved_at": None if pd.isna(row.retrieved_at) else row.retrieved_at.isoformat(),
        }
    spec = {
        "schema_version": SCHEMA,
        "case_id": "public-swarm-a-tle-omm-2026-09-08",
        "inputs": inputs,
        "conventions": {
            "frame": "TEME",
            "centre": "EARTH",
            "time_system": "UTC",
            "position_unit": "km",
            "velocity_unit": "km/s",
            "theory": "SGP4",
            "constants": "WGS72",
            "operation_mode": "i",
            "difference_sign": "candidate minus baseline",
        },
        "epochs_utc": [(row.epoch.to_pydatetime() + timedelta(hours=h)).isoformat() for h in (6, 24, 48, 72, 168)],
        "acceptance_criterion": {
            "kind": "maximum-cartesian-state-difference",
            "position_km": 0.01,
            "velocity_km_s": 0.00001,
            "reproduction_position_km": 1e-8,
            "reproduction_velocity_km_s": 1e-11,
            "recorded_at": datetime.now(UTC).isoformat(),
            "agreed_by_role": "repository maintainer public demonstration criterion",
            "decision_owner_role": "repository maintainer",
            "customer_agreed": False,
        },
        "limitations": [
            "Public adapter demonstration; no customer has agreed or accepted this criterion.",
            "The baseline is a TLE encoding of the same stored mean elements; it is not independent truth.",
            "Agreement measures encoding and adapter behaviour, not orbit accuracy or operational suitability.",
            "Single mission and element epoch; no transfer to other adapters or unsupported conventions.",
            "No short-window dynamical validation or timing application is claimed.",
            "Unknown provider creation and publication times remain unknown.",
        ],
    }
    destination.mkdir(parents=True)
    (destination / "supplied").mkdir()
    (destination / inputs["baseline"]["path"]).write_bytes(tle)
    (destination / inputs["candidate"]["path"]).write_bytes(candidate)
    (destination / "case.json").write_bytes(encode(spec))
    return {
        "case_sha256": sha(encode(spec)),
        "criterion_sha256": sha(encode(spec["acceptance_criterion"])),
        "state_epoch": row.epoch.isoformat(),
        "residuals_evaluated": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(encode(prepare(args.history, args.destination)).decode())
