"""Exercise the repository's bounded TLE/OMM paths and record all six review axes."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sgp4.exporter import export_tle

from driftwatch.case_bundle import encode, evaluate, read_case, sha
from driftwatch.catalogue.history import frame_from_records, read_history, write_history
from driftwatch.imports import decode_orbit
from driftwatch.orbit.propagator import build_satrecs
from driftwatch.workbench import inspect_orbit


def row(axis, checks):
    states = {c["status"] for c in checks}
    status = "failed" if "failed" in states else "untested" if "untested" in states else "passed"
    return {"axis": axis, "status": status, "checks": checks}


def check(name, passed, observation):
    return {"name": name, "status": "passed" if passed else "failed", "observation": observation}


def audit(bundle_path):
    _, entries = read_case(bundle_path)
    spec = json.loads(entries["case.json"])
    baseline = decode_orbit(entries[spec["inputs"]["baseline"]["path"]].decode()).records[0]
    candidate = decode_orbit(entries[spec["inputs"]["candidate"]["path"]].decode()).records[0]
    identity = []
    with tempfile.TemporaryDirectory(prefix="migration-audit-") as temporary:
        store = Path(temporary) / "history.parquet"
        for identifier, encoding in ((int(candidate["NORAD_CAT_ID"]), "json"), (100001, "tle"), (999999999, "json")):
            record = copy.deepcopy(candidate)
            record["NORAD_CAT_ID"] = identifier
            if encoding == "tle":
                sat = build_satrecs(frame_from_records([record]))[0]
                d = str(record["OBJECT_ID"])
                sat.intldesg = d[2:4] + d[5:]
                text = "\n".join(export_tle(sat))
            else:
                text = encode([record]).decode()
            decoded = decode_orbit(text).records
            frame = frame_from_records(decoded)
            write_history(frame, store, update=False)
            reopened = read_history(store)
            preview = inspect_orbit({"file": {"name": "case." + encoding, "text": text}})
            ids = [int(frame.norad_id.iloc[0]), int(reopened.norad_id.iloc[0]), preview["objects"][0]["norad"]]
            identity.append(
                check(
                    f"{encoding} identifier {identifier}: import, history and inspection API",
                    ids == [identifier] * 3,
                    {
                        "identifiers": ids,
                        "construction": "stored identity"
                        if identifier < 100000
                        else "identifier-only variant of the public case; not another observed spacecraft",
                    },
                )
            )
        identity.append(
            {
                "name": "Browser display and exported identity joins",
                "status": "untested",
                "observation": "Inspection API was exercised; browser display and export were not automated.",
            }
        )

        record = copy.deepcopy(candidate)
        record["CREATION_DATE"] = "2024-04-02T00:00:00Z"
        imported = decode_orbit(encode([record]).decode()).records
        frame = frame_from_records(imported, fetched_at=datetime(2026, 9, 8, tzinfo=UTC))
        write_history(frame, store, update=False)
        reopened = read_history(store)
        unknown = frame_from_records([copy.deepcopy(candidate)])
        times = [
            check(
                "State epoch and provider creation stay distinct",
                reopened.epoch.iloc[0] != reopened.provider_created_at.iloc[0]
                and reopened.provider_created_at.iloc[0] == pd.Timestamp(record["CREATION_DATE"]),
                {
                    "state_epoch": reopened.epoch.iloc[0].isoformat(),
                    "provider_created_at": reopened.provider_created_at.iloc[0].isoformat(),
                },
            ),
            check(
                "Actual supplied retrieval time survives history storage",
                reopened.retrieved_at.iloc[0] == pd.Timestamp("2026-09-08T00:00:00Z"),
                reopened.retrieved_at.iloc[0].isoformat(),
            ),
            check(
                "Unknown publication and acquisition remain unknown",
                unknown.published_at.isna().all() and unknown.retrieved_at.isna().all(),
                "Neither epoch nor local import time establishes publication or retrieval",
            ),
        ]

        conventions = []
        for key, value in (("REF_FRAME", "ITRF"), ("CENTER_NAME", "MARS"), ("TIME_SYSTEM", "TAI")):
            modified = {**candidate, key: value}
            try:
                decode_orbit(encode([modified]).decode())
                refused = False
            except ValueError:
                refused = True
            conventions.append(check(f"Unsupported {key} fails explicitly", refused, value))
        kvn = "CCSDS_OMM_VERS = 2.0\n" + "\n".join(f"{k} = {v}" for k, v in candidate.items())
        kvn = kvn.replace(
            f"MEAN_MOTION = {candidate['MEAN_MOTION']}", f"MEAN_MOTION = {candidate['MEAN_MOTION']} [rad/s]"
        )
        try:
            decode_orbit(kvn)
            refused = False
        except ValueError:
            refused = True
        conventions.append(check("Unsupported declared mean-motion units fail explicitly", refused, "rad/s refused"))
        numerical = evaluate(spec, entries)["acceptance"]
        theory = [
            check(
                "Same public elements through TLE and OMM preserve the declared SGP4 output",
                numerical["accepted"],
                numerical,
            )
        ]
        try:
            decode_orbit(encode([{**candidate, "MEAN_ELEMENT_THEORY": "DSST"}]).decode())
            refused = False
        except ValueError:
            refused = True
        theory.append(check("Unsupported mean-element theory is refused", refused, "DSST"))

        missing = {
            k: v for k, v in candidate.items() if k not in {"CLASSIFICATION_TYPE", "ELEMENT_SET_NO", "REV_AT_EPOCH"}
        }
        decoded = decode_orbit(encode([missing]).decode())
        imputed = {
            key: decoded.records[0].get(key) for key in ("CLASSIFICATION_TYPE", "ELEMENT_SET_NO", "REV_AT_EPOCH")
        }
        covariance = decode_orbit(encode([{**candidate, "COV_REF_FRAME": "RTN", "CX_X": 1.0}]).decode()).records
        persisted = frame_from_records(covariance)
        optional = [
            check("Missing optional values remain unknown", all(v is None for v in imputed.values()), imputed),
            check(
                "Supplied covariance metadata and matrix survive the history adapter",
                {"COV_REF_FRAME", "CX_X"} <= set(persisted.columns),
                {
                    "decoded": True,
                    "retained_in_history": "COV_REF_FRAME" in persisted.columns,
                    "explicit_rejection": False,
                },
            ),
        ]
    full = [
        check(
            "Legacy and OMM identity joins agree",
            int(baseline["NORAD_CAT_ID"]) == int(candidate["NORAD_CAT_ID"]),
            "Same public spacecraft and international designator",
        ),
        {
            "name": "Full browser, save/open and export round trip",
            "status": "untested",
            "observation": "CLI bundle reopening was independently verified; "
            "an end-to-end browser case workflow was not exercised.",
        },
    ]
    root = Path(__file__).resolve().parents[2]
    sources = ("imports.py", "catalogue/history.py", "catalogue/snapshot.py", "orbit/propagator.py", "workbench.py")
    return {
        "schema_version": "tle-omm-migration-audit-v1",
        "audited_at": datetime.now(UTC).isoformat(),
        "bundle_sha256": sha(bundle_path.read_bytes()),
        "population": "One stored Swarm A GP record and declared format/identity variants",
        "customer_adapter": "unverified",
        "source_sha256": {p: sha((root / "src/driftwatch" / p).read_bytes()) for p in sources},
        "rows": [
            row("Object identity", identity),
            row("Time and availability", times),
            row("Frame, centre and units", conventions),
            row("Mean-element theory", theory),
            row("Optional and missing data", optional),
            row("Full adapter path", full),
        ],
    }


def render(record):
    lines = [
        "# TLE-to-OMM audit of driftwatch's own paths",
        "",
        "Audit time: " + record["audited_at"],
        "",
        "One public history-store case and declared format/identity variants. Customer adapters remain unverified.",
        "",
        "| Axis | Status | Check | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for result in record["rows"]:
        for item in result["checks"]:
            evidence = item["observation"]
            if not isinstance(evidence, str):
                evidence = json.dumps(evidence)
            lines.append(f"| {result['axis']} ({result['status']}) | {item['status']} | {item['name']} | {evidence} |")
    lines += [
        "",
        "The optional-field and covariance failures are recorded defects, not repaired by this audit. "
        "The full browser round trip remains untested. No standards certification, product-accuracy result "
        "or customer acceptance follows from the passing rows.",
        "",
        "[Machine-readable record](assets/cases/migration-audit-2026-09-08.json); "
        "[second-machine bundle reproduction](assets/cases/second-machine-2026-09-08.json).",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("record", type=Path)
    parser.add_argument("table", type=Path)
    args = parser.parse_args()
    record = audit(args.bundle)
    args.record.write_bytes(encode(record))
    args.table.write_text(render(record), encoding="utf-8", newline="\n")
    print(encode({r["axis"]: r["status"] for r in record["rows"]}).decode())


if __name__ == "__main__":
    main()
