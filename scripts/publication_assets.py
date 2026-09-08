"""Restore hash-bound publication inputs from the correction release."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "docs/assets/publication-assets-v2.1.json"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def manifest(root=ROOT):
    return json.loads((root / MANIFEST).read_text(encoding="utf-8"))


def safe_path(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
        raise ValueError(f"Unsafe publication path: {relative}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Publication path escapes checkout: {relative}")
    return target


def effective_hash(relative, original_hash, *, root=ROOT):
    """Resolve a disclosed v2 original binding to its v2.1 distributable bytes."""
    data = manifest(root)
    entry = next((x for x in data["files"] + data["tracked_bindings"] if x["path"] == relative), None)
    if entry is None:
        return original_hash
    if original_hash not in {entry["original_sha256"], entry["sha256"]}:
        raise ValueError(f"Undeclared publication hash for {relative}: {original_hash}")
    return entry["sha256"]


def _request(url, *, api=False):
    headers = {
        "User-Agent": "driftwatch-publication-rebuild",
        "Accept": "application/octet-stream" if api else "application/json",
    }
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90)


def _bundle_url(data):
    bundle = data["bundle"]
    mirror = os.environ.get("DRIFTWATCH_ASSET_MIRROR")
    if mirror:
        return mirror.rstrip("/") + "/" + bundle["name"], False
    release_url = f"https://api.github.com/repositories/{data['repository_id']}/releases/tags/{data['release_tag']}"
    with _request(release_url) as response:
        release = json.load(response)
    asset = next((a for a in release["assets"] if a["name"] == bundle["name"]), None)
    if asset is None:
        raise FileNotFoundError(bundle["name"])
    return asset["browser_download_url"], False


def _bundle(data, root):
    entry = data["bundle"]
    cache = root / ".cache/publication"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / entry["name"]
    if target.exists():
        if sha256(target) != entry["sha256"]:
            raise ValueError(f"Publication archive hash mismatch: {entry['name']}")
        return target
    url, api = _bundle_url(data)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
            temporary = Path(stream.name)
            with _request(url, api=api) as response:
                shutil.copyfileobj(response, stream)
        if temporary.stat().st_size != entry["bytes"] or sha256(temporary) != entry["sha256"]:
            raise ValueError(f"Publication archive hash/size mismatch: {entry['name']}")
        temporary.replace(target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def require_asset(relative, *, root=ROOT):
    data = manifest(root)
    entry = next((x for x in data["files"] if x["path"] == relative), None)
    if entry is None:
        raise FileNotFoundError(f"Missing publication asset {relative}: no hash-bound release entry")
    target = safe_path(root, relative)
    if target.exists():
        if sha256(target) != entry["sha256"]:
            raise ValueError(f"Publication asset hash mismatch: {relative}; expected SHA-256 {entry['sha256']}")
        return target
    try:
        archive = _bundle(data, root)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zipped:
            member = zipped.getinfo(relative)
            if member.file_size != entry["bytes"]:
                raise ValueError(f"Publication member size mismatch: {relative}")
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                temporary = Path(stream.name)
                try:
                    with zipped.open(member) as source:
                        shutil.copyfileobj(source, stream)
                    stream.close()
                    if sha256(temporary) != entry["sha256"]:
                        raise ValueError(f"Publication member hash mismatch: {relative}")
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
    except (OSError, ValueError, KeyError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        raise FileNotFoundError(
            f"Missing publication asset {relative}; SHA-256 {entry['sha256']}; "
            f"release asset {data['bundle']['name']} on {data['release_tag']}: {type(exc).__name__}"
        ) from exc
    return target


def restore_required(*, root=ROOT, all_files=False):
    data = manifest(root)
    paths = [x["path"] for x in data["files"]] if all_files else data["required_for_tests"]
    for relative in paths:
        require_asset(relative, root=root)
    return paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="restore every released derived artefact")
    args = parser.parse_args()
    print(f"Verified {len(restore_required(all_files=args.all))} publication assets")
