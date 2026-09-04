"""The check that runs before anything is published.

Two mistakes would be irreversible once the bundle is on a CDN: republishing SpaceX's
ephemerides, which are analysis-only, and shipping a credential. Both are cheap to test and
neither is the sort of thing to find out about afterwards. The third case here is the one
that decides whether the check survives contact with reality: a minified JavaScript bundle
is full of the words `token` and `secret`, and a check that fails on every build is a check
that gets turned off.
"""

from __future__ import annotations

import json

from driftwatch.export.audit import audit_bundle


def write(directory, name: str, text: str) -> None:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_a_clean_bundle_passes_and_reports_its_size_headroom(tmp_path):
    write(tmp_path, "index.html", "<!doctype html><title>driftwatch</title>")
    write(tmp_path, "data/manifest.json", json.dumps({"generator": "driftwatch 0.1.0", "n_objects": 32361}))
    (tmp_path / "data/elements.bin").write_bytes(b"\x00" * 2048)

    findings, summary = audit_bundle(tmp_path, environ={})
    assert findings == []
    assert summary["n_files"] == 3
    assert summary["largest"][0]["path"] == "data/elements.bin"
    assert summary["headroom_mib"] > 24.0


def test_a_raw_spacex_file_in_the_bundle_stops_the_deploy(tmp_path):
    """Analysis only: their files are never republished, and neither is our derived store."""
    write(tmp_path, "data/MEME_37618_STARLINK-1234_1234567_Operational_1234567_UNCLASSIFIED.txt", "whatever")
    write(tmp_path, "data/ephemerides_20260902T132832Z.parquet", "not really a parquet")
    write(tmp_path, "data/notes.json", json.dumps({"see": "https://api.starlink.com/public-files/ephemerides/"}))

    findings, summary = audit_bundle(tmp_path, environ={})
    assert summary["n_errors"] == 3
    assert any("raw SpaceX ephemeris" in f.what for f in findings)
    assert any("derived SpaceX covariance store" in f.what for f in findings)
    assert any("file service" in f.what for f in findings)


def test_a_credential_anywhere_in_the_bundle_stops_the_deploy(tmp_path):
    """The strongest check available: the literal value the environment holds right now."""
    write(tmp_path, "data/manifest.json", json.dumps({"fetched_by": "sw0rdf1sh-secret-value"}))
    write(tmp_path, "assets/app.js", 'const u = "https://alice:hunter2pass@space-track.org/basicspacedata";')

    findings, summary = audit_bundle(
        tmp_path, environ={"SPACETRACK_USER": "nikhil", "SPACETRACK_PASS": "sw0rdf1sh-secret-value"}
    )
    assert summary["n_errors"] == 2
    assert any("$SPACETRACK_PASS" in f.what for f in findings)
    assert any("password in it" in f.what for f in findings)
    # A short value is not searched for: matching "abc" everywhere would be worse than useless.
    clean, summary = audit_bundle(tmp_path, environ={"SPACETRACK_PASS": "abc"})
    assert not any("SPACETRACK_PASS" in f.what for f in clean)


def test_the_minified_bundle_does_not_cry_wolf(tmp_path):
    """`token = _ref2[0]` is a variable, not a secret, and it appears in real builds."""
    write(
        tmp_path,
        "assets/index-CwEHRVzs.js.map",
        'var token = _ref2[0], secret = x.secret; const password = opts.password; "authToken" in o;',
    )
    findings, summary = audit_bundle(tmp_path, environ={})
    assert findings == [] and summary["n_errors"] == 0

    # But a literal still fails, in the same file.
    write(tmp_path, "assets/index-CwEHRVzs.js.map", 'const o = {api_key: "9f8e7d6c5b4a3210ffff"};')
    findings, _ = audit_bundle(tmp_path, environ={})
    assert len(findings) == 1 and "key or token literal" in findings[0].what


def test_a_file_over_the_pages_limit_stops_the_deploy(tmp_path):
    """The 25 MiB per-file ceiling came from Cloudflare Pages and is kept on Vercel as the project's own."""
    (tmp_path / "big.bin").write_bytes(b"\x00" * 4096)
    findings, summary = audit_bundle(tmp_path, environ={}, max_file_bytes=2048)
    assert summary["n_errors"] == 1
    assert "over the per-file ceiling" in findings[0].what


def test_the_deploy_token_s_literal_value_is_searched_for(tmp_path):
    """The token the pipeline deploys with is in the environment precisely so this can look for it."""
    write(tmp_path, "assets/app.js", "const t = 'vcl_0123456789abcdefXYZ';")
    findings, _ = audit_bundle(tmp_path, environ={"VERCEL_TOKEN": "vcl_0123456789abcdefXYZ"})
    assert len(findings) == 1 and "the value of $VERCEL_TOKEN" in findings[0].what


def test_a_missing_directory_is_an_error_not_a_pass(tmp_path):
    findings, summary = audit_bundle(tmp_path / "nothing-here", environ={})
    assert summary["n_files"] == 0
    assert len(findings) == 1 and "does not exist" in findings[0].what
