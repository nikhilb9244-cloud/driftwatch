"""Resolve published method bindings against their immutable source archive."""

import hashlib
import json
import zipfile
from pathlib import Path


def published_source(path, expected, *, root):
    root = Path(root)
    record = json.loads((root / "docs/assets/benchmark-v2-method.json").read_bytes())
    archive = root / record["archive"]
    if not archive.exists():
        raise FileNotFoundError(f"Missing published method asset: {record['archive']}")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError("Published method archive hash mismatch")
    if record["files"].get(path) != expected:
        raise ValueError(f"Published method binding differs: {path}")
    with zipfile.ZipFile(archive) as stored:
        raw = stored.read(path)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Published method source hash mismatch: {path}")
    return raw
