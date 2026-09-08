"""Absent, unavailable and corrupt release artefacts must be distinguished."""

import hashlib
import io
import json
import sys
import urllib.error
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publication_assets as assets  # noqa: E402


@pytest.fixture
def release(tmp_path):
    relative = "data/validation/example.json"
    raw = b'{"derived_residual": 0.125}\n'
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(relative, raw)
    bundle = stream.getvalue()
    sha = lambda value: hashlib.sha256(value).hexdigest()  # noqa: E731
    data = {
        "repository_id": 1,
        "release_tag": "test-release",
        "bundle": {"name": "sha256-" + sha(bundle) + ".zip", "sha256": sha(bundle), "bytes": len(bundle)},
        "files": [{"path": relative, "sha256": sha(raw), "original_sha256": "a" * 64, "bytes": len(raw)}],
        "tracked_bindings": [],
        "required_for_tests": [relative],
    }
    destination = tmp_path / assets.MANIFEST
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(data))
    return tmp_path, relative, raw, bundle, data


def test_missing_input_downloads_and_verifies_archive_and_member(release, monkeypatch):
    root, relative, raw, bundle, data = release
    calls = []
    monkeypatch.setenv("DRIFTWATCH_ASSET_MIRROR", "https://example.invalid/artefacts")

    def download(url, **kwargs):
        calls.append(url)
        return io.BytesIO(bundle)

    monkeypatch.setattr(assets, "_request", download)
    assert not (root / "data").exists()
    assert assets.require_asset(relative, root=root).read_bytes() == raw
    assert calls == ["https://example.invalid/artefacts/" + data["bundle"]["name"]]
    assert assets.require_asset(relative, root=root).read_bytes() == raw
    assert len(calls) == 1


def test_unavailable_release_names_missing_input_and_hash(release, monkeypatch):
    root, relative, _, _, data = release

    def absent(*args, **kwargs):
        raise urllib.error.URLError("unavailable")

    monkeypatch.setattr(assets, "_bundle_url", absent)
    with pytest.raises(FileNotFoundError) as caught:
        assets.require_asset(relative, root=root)
    assert relative in str(caught.value)
    assert data["files"][0]["sha256"] in str(caught.value)
    assert data["bundle"]["name"] in str(caught.value)


def test_corrupt_download_is_never_installed(release, monkeypatch):
    root, relative, _, _, _ = release
    monkeypatch.setattr(assets, "_bundle_url", lambda _: ("https://example.invalid/corrupt", False))
    monkeypatch.setattr(assets, "_request", lambda *args, **kwargs: io.BytesIO(b"corrupt"))
    with pytest.raises(FileNotFoundError, match="Missing publication asset"):
        assets.require_asset(relative, root=root)
    assert not (root / relative).exists()
    assert list((root / ".cache/publication").iterdir()) == []


def test_existing_wrong_bytes_fail_without_network(release, monkeypatch):
    root, relative, _, _, _ = release
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"unverified local result")
    monkeypatch.setattr(
        assets, "_request", lambda *args, **kwargs: pytest.fail("must not fetch over an existing mismatch")
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        assets.require_asset(relative, root=root)


def test_only_disclosed_original_bindings_resolve(release):
    root, relative, _, _, data = release
    assert assets.effective_hash(relative, "a" * 64, root=root) == data["files"][0]["sha256"]
    with pytest.raises(ValueError, match="Undeclared"):
        assets.effective_hash(relative, "b" * 64, root=root)


@pytest.mark.parametrize("path", ["../escape", "/escape", "data/../../escape", "data\\escape"])
def test_manifest_cannot_escape_checkout(tmp_path, path):
    with pytest.raises(ValueError, match="Unsafe"):
        assets.safe_path(tmp_path, path)
