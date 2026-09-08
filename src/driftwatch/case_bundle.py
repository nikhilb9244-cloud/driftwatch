"""Portable, hash-checked orbit-adapter acceptance cases, evaluated without network access."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import stat
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

from driftwatch.catalogue.history import frame_from_records
from driftwatch.imports import decode_orbit
from driftwatch.local import no_network
from driftwatch.orbit.propagator import propagate_snapshot

SCHEMA = "orbit-adapter-case-v1"
MAX_BYTES = 100_000_000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")


def safe_name(name):
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or ":" in name
        or path.is_absolute()
        or name != path.as_posix()
        or any(p in {"..", "."} for p in path.parts)
    ):
        raise ValueError("Bundle member must be a portable relative path")
    return name


def validate_spec(spec):
    if spec.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported case schema")
    if set(spec["inputs"]) != {"baseline", "candidate"}:
        raise ValueError("This bounded case profile requires exactly a baseline and candidate")
    criterion = spec["acceptance_criterion"]
    if criterion["kind"] != "maximum-cartesian-state-difference":
        raise ValueError("Unsupported acceptance criterion")
    for key in ("position_km", "velocity_km_s", "reproduction_position_km", "reproduction_velocity_km_s"):
        value = criterion[key]
        if isinstance(value, bool) or not np.isfinite(value) or value <= 0:
            raise ValueError(f"Acceptance criterion requires a positive finite {key}")
    if not criterion["agreed_by_role"] or not criterion["decision_owner_role"]:
        raise ValueError("Record who owns and agreed the acceptance criterion")
    agreed = pd.Timestamp(criterion["recorded_at"])
    if pd.isna(agreed) or agreed.tzinfo is None or agreed > pd.Timestamp.now(tz="UTC"):
        raise ValueError("The criterion must have been recorded before evaluation")
    if spec["conventions"] != {
        "frame": "TEME",
        "centre": "EARTH",
        "time_system": "UTC",
        "position_unit": "km",
        "velocity_unit": "km/s",
        "theory": "SGP4",
        "constants": "WGS72",
        "operation_mode": "i",
        "difference_sign": "candidate minus baseline",
    }:
        raise ValueError("Unsupported or incomplete conventions")
    if not spec["limitations"] or not spec["epochs_utc"]:
        raise ValueError("Record evaluation epochs and limitations")
    times = pd.to_datetime(spec["epochs_utc"], utc=True)
    if times.hasnans or not times.is_monotonic_increasing or times.has_duplicates:
        raise ValueError("Evaluation epochs must be valid, increasing and unique")
    for role in ("baseline", "candidate"):
        item = spec["inputs"][role]
        safe_name(item["path"])
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError(f"Missing input hash: {role}")
        rights = item["rights"]
        if (
            rights.get("redistribution_permitted") is not True
            or not rights.get("basis")
            or not rights.get("attribution")
        ):
            raise ValueError(f"Explicit redistribution basis and attribution required: {role}")
        for field in ("state_epoch", "provider_created_at", "published_at", "retrieved_at"):
            if field not in item:
                raise ValueError(f"Missing temporal field (use null for unknown): {role}/{field}")
            if item[field] is not None:
                instant = pd.Timestamp(item[field])
                if pd.isna(instant) or instant.tzinfo is None:
                    raise ValueError(f"Use a timezone-bearing instant or null: {role}/{field}")


def evaluate(spec, supplied):
    """Return both states, signed differences and the declared decision; never fit a criterion."""
    validate_spec(spec)
    outputs = {}
    identities = []
    times = pd.to_datetime(spec["epochs_utc"], utc=True).tz_localize(None).to_numpy(dtype="datetime64[us]")
    with no_network():
        for role in ("baseline", "candidate"):
            item = spec["inputs"][role]
            raw = supplied[item["path"]]
            if sha(raw) != item["sha256"]:
                raise ValueError(f"Input hash mismatch: {item['path']}")
            decoded = decode_orbit(raw.decode("utf-8"))
            if decoded.records is None or len(decoded.records) != 1:
                raise ValueError("This bounded case profile requires one TLE or OMM element set per input")
            rows = frame_from_records(
                decoded.records, source=item["source_identifier"], fetched_at=item["retrieved_at"]
            )
            identity = (int(rows.norad_id.iloc[0]), str(rows.object_id.iloc[0]))
            identities.append(identity)
            if item["state_epoch"] is None or rows.epoch.iloc[0] != pd.Timestamp(item["state_epoch"]):
                raise ValueError(f"Declared state epoch differs from the input: {role}")
            states = propagate_snapshot(rows, times)
            if np.any(states.error) or not np.isfinite(states.r_teme).all() or not np.isfinite(states.v_teme).all():
                raise ValueError(f"Invalid propagation in {role}; no acceptance decision")
            outputs[role] = {
                "adapter": "driftwatch.imports.decode_orbit -> history frame -> SGP4",
                "format": decoded.format,
                "identity": list(identity),
                "warnings": decoded.warnings or [],
                "epochs_utc": spec["epochs_utc"],
                "r_teme_km": states.r_teme[0].tolist(),
                "v_teme_km_s": states.v_teme[0].tolist(),
            }
    if identities[0] != identities[1]:
        raise ValueError("Baseline and candidate identities differ")
    dr = np.asarray(outputs["candidate"]["r_teme_km"]) - np.asarray(outputs["baseline"]["r_teme_km"])
    dv = np.asarray(outputs["candidate"]["v_teme_km_s"]) - np.asarray(outputs["baseline"]["v_teme_km_s"])
    outputs["differences"] = {
        "sign": "candidate minus baseline",
        "epochs_utc": spec["epochs_utc"],
        "delta_r_teme_km": dr.tolist(),
        "delta_v_teme_km_s": dv.tolist(),
    }
    max_r, max_v = float(np.linalg.norm(dr, axis=1).max()), float(np.linalg.norm(dv, axis=1).max())
    c = spec["acceptance_criterion"]
    outputs["acceptance"] = {
        "accepted": max_r <= c["position_km"] and max_v <= c["velocity_km_s"],
        "max_position_difference_km": max_r,
        "max_velocity_difference_km_s": max_v,
        "criterion_sha256": sha(encode(c)),
        "limitations": spec["limitations"],
    }
    return outputs


def pack(spec_path, target, source_root):
    spec_raw = spec_path.read_bytes()
    spec = json.loads(spec_raw)
    validate_spec(spec)
    entries = {"case.json": spec_raw}
    for item in spec["inputs"].values():
        path = (spec_path.parent / safe_name(item["path"])).resolve()
        if not path.is_relative_to(spec_path.parent.resolve()):
            raise ValueError("Supplied file escapes the case directory")
        entries[item["path"]] = path.read_bytes()
    outputs = evaluate(spec, entries)
    entries.update({"outputs/" + role + ".json": encode(value) for role, value in outputs.items()})
    for name in ("pyproject.toml", "uv.lock"):
        entries[name] = (source_root / name).read_bytes()
    for path in sorted((source_root / "src/driftwatch").rglob("*")):
        if path.is_file() and path.suffix in {".py", ".json"}:
            entries[path.relative_to(source_root).as_posix()] = path.read_bytes()
    entries["environment.json"] = encode(
        {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "producer_os": platform.system(),
            "architecture": platform.machine(),
            "dependency_lock_sha256": sha(entries["uv.lock"]),
            "numerical_packages": {name: importlib.metadata.version(name) for name in ("sgp4", "numpy", "pandas")},
            "installation": "uv sync --frozen --no-dev --python " + platform.python_version(),
            "reopen": "uv run --frozen --no-dev python -m driftwatch.case_bundle verify .",
        }
    )
    inventory = {name: {"sha256": sha(raw), "bytes": len(raw)} for name, raw in sorted(entries.items())}
    entries["manifest.json"] = encode(
        {
            "schema_version": SCHEMA,
            "case_sha256": sha(spec_raw),
            "created_at": datetime.now(UTC).isoformat(),
            "files": inventory,
        }
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(entries.items()):
            archive.writestr(name, raw)
    return {
        "asset": target.name,
        "sha256": sha(target.read_bytes()),
        "bytes": target.stat().st_size,
        "case_sha256": sha(spec_raw),
        "accepted": outputs["acceptance"]["accepted"],
    }


def read_case(path):
    if path.is_dir():
        manifest = json.loads((path / "manifest.json").read_bytes())
        entries = {}
        for name in manifest["files"]:
            member = (path / safe_name(name)).resolve()
            if not member.is_relative_to(path.resolve()):
                raise ValueError("Bundle member escapes the case directory")
            entries[name] = member.read_bytes()
    else:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > 500 or sum(i.file_size for i in infos) > MAX_BYTES:
                raise ValueError("Bundle exceeds the bounded case size")
            names = [safe_name(i.filename) for i in infos]
            if len(names) != len(set(names)) or any(stat.S_ISLNK(i.external_attr >> 16) for i in infos):
                raise ValueError("Duplicate or symbolic-link bundle member")
            entries = {name: archive.read(name) for name in names}
        if "manifest.json" not in entries:
            raise ValueError("Bundle missing manifest.json")
        manifest = json.loads(entries.pop("manifest.json"))
    if manifest["schema_version"] != SCHEMA or set(entries) != set(manifest["files"]):
        raise ValueError("Bundle manifest does not describe every member")
    for name, expected in manifest["files"].items():
        raw = entries[name]
        if len(raw) != expected["bytes"] or sha(raw) != expected["sha256"]:
            raise ValueError(f"Bundle hash mismatch: {name}")
    if sha(entries["case.json"]) != manifest["case_sha256"]:
        raise ValueError("Case contract hash mismatch")
    return manifest, entries


def unpack(path, destination):
    manifest, entries = read_case(path)
    if destination.exists():
        raise ValueError("Unpack into a new directory")
    destination.mkdir(parents=True)
    for name, raw in {**entries, "manifest.json": encode(manifest)}.items():
        output = destination / safe_name(name)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)


def verify(path):
    manifest, entries = read_case(path)
    environment = json.loads(entries["environment.json"])
    if platform.python_version() != environment["python"]:
        raise ValueError("Use the Python version recorded in environment.json")
    for name, version in environment["numerical_packages"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f"Use the recorded numerical package version: {name}")
    source_root = Path(__file__).resolve().parents[2]
    for name, expected in manifest["files"].items():
        if name.startswith("src/") and sha((source_root / name).read_bytes()) != expected["sha256"]:
            raise ValueError("Use the source tree supplied inside this case bundle")
    spec = json.loads(entries["case.json"])
    actual = evaluate(spec, entries)
    c = spec["acceptance_criterion"]
    maxima = {}
    for role, keys in {
        "baseline": ("r_teme_km", "v_teme_km_s"),
        "candidate": ("r_teme_km", "v_teme_km_s"),
        "differences": ("delta_r_teme_km", "delta_v_teme_km_s"),
    }.items():
        expected = json.loads(entries[f"outputs/{role}.json"])
        if actual[role]["epochs_utc"] != expected["epochs_utc"]:
            raise ValueError("Reproduction epochs differ")
        for key, bound in zip(keys, (c["reproduction_position_km"], c["reproduction_velocity_km_s"]), strict=True):
            error = np.abs(np.asarray(actual[role][key]) - np.asarray(expected[key]))
            maxima[f"{role}/{key}"] = float(error.max())
            if not np.isfinite(error).all() or np.any(error > bound):
                raise ValueError(f"Reproduction exceeds the declared tolerance: {role}/{key}")
    expected = json.loads(entries["outputs/acceptance.json"])
    if actual["acceptance"]["accepted"] != expected["accepted"]:
        raise ValueError("Reproduced acceptance decision differs")
    return {
        "case_sha256": manifest["case_sha256"],
        "reproduced": True,
        "decision": actual["acceptance"],
        "maximum_component_reproduction_errors": maxima,
        "verification_os": platform.system(),
        "python": platform.python_version(),
        "external_data_used": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("pack")
    p.add_argument("spec", type=Path)
    p.add_argument("target", type=Path)
    p = commands.add_parser("unpack")
    p.add_argument("bundle", type=Path)
    p.add_argument("destination", type=Path)
    p = commands.add_parser("verify")
    p.add_argument("bundle", type=Path)
    p.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.command == "pack":
        result = pack(args.spec, args.target, Path(__file__).resolve().parents[2])
    elif args.command == "unpack":
        unpack(args.bundle, args.destination)
        result = {"unpacked": True}
    else:
        result = verify(args.bundle)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_bytes(encode(result))
    print(encode(result).decode(), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
