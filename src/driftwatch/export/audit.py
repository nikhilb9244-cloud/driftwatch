"""What may and may not leave this machine: the check that runs before a deploy.

The viewer bundle is the only thing driftwatch publishes, and two classes of mistake would
be irreversible once it is on a CDN.

**Redistribution.** SpaceX's Starlink ephemerides are served without a stated licence, for
the express purpose of letting other operators screen against Starlink, and the rule adopted
in ``docs/spacex-ephemerides.md`` is analysis only: compute with them, publish the results
crediting SpaceX, never republish the files or a repackaged copy of them. The derived
covariance store under ``data/spacex/`` is not redistributed either. Space-Track's element
sets *may* be redistributed with citation, and are, which is why the manifest carries the
attribution -- so this is not a blanket "no data" rule but a specific one, and it is checked
by name and by content rather than trusted to the exporter never changing.

**Credentials.** Space-Track's user and password live in the environment
(:data:`driftwatch.config.SPACETRACK_USER_ENV`, ``SPACETRACK_PASS_ENV``) and nothing writes
them anywhere. The strongest possible check is therefore also the simplest: take whatever
those variables hold right now and confirm the literal strings do not appear in any file
about to be published, alongside the usual patterns for keys and tokens.

The size limits -- 25 MiB a file and 20,000 files an upload -- were Cloudflare Pages' direct-upload
limits and are kept as this project's own ceiling now that the site is on Vercel (2026-09-05): a
bundle file that large is a design failure whichever CDN serves it, and hearing about it here is
better than hearing about it from an upload.

:func:`audit_bundle` returns findings rather than raising, and ``driftwatch check-bundle``
exits non-zero when any of them is an error. The deploy script runs it before it builds.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from driftwatch import config

log = logging.getLogger(__name__)

# Cloudflare Pages' direct-upload limits (docs read 2026-09-02): 25 MiB a file, 20,000 files.
# Kept as the project's own ceiling on Vercel.
PAGES_MAX_FILE_BYTES = 25 * 1024 * 1024
PAGES_MAX_FILES = 20_000

# Names that would mean a raw SpaceX file, or the derived covariance store, had been copied
# into the bundle. `MEME_<id>_STARLINK-...` is their own file naming; `ephemerides_<stamp>`
# is ours for the thinned covariance.
FORBIDDEN_NAMES: tuple[tuple[str, str], ...] = (
    (r"^MEME_\d+_", "a raw SpaceX ephemeris file"),
    (r"^ephemerides_\d{8}T\d{6}Z\.parquet$", "the derived SpaceX covariance store"),
    (r"^MANIFEST\.txt$", "SpaceX's own file manifest"),
)
# Content that would mean the same thing. The header of every published ephemeris carries
# these keys, so a copy pasted into a JSON blob would still be caught.
FORBIDDEN_CONTENT: tuple[tuple[str, str], ...] = (
    (r"api\.starlink\.com/public-files", "a link to the SpaceX file service"),
    (r"ephemeris_start\s+\d{13}", "the header of a published SpaceX ephemeris"),
    (r"created:\s*\d{13}\.\d+\s*\n\s*ephemeris_start", "a published SpaceX ephemeris"),
)
# These have to survive a minified JavaScript bundle and its source map, which are full of
# words like `token` and `secret` as ordinary identifiers. So every pattern here requires a
# **literal value**: a quoted string, a recognisable key shape, or a URL with credentials in
# it. `token = _ref2[0]` is a variable assignment and must not stop a deploy; a check that
# cries wolf on every build is a check that gets turned off.
SECRET_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
    (r"AKIA[0-9A-Z]{16}", "an AWS access key id"),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}", "a GitHub token"),
    (r"\bBearer\s+[A-Za-z0-9._\-]{16,}", "a bearer token"),
    (r"\bidentity=[^&\s\"']+&password=", "a Space-Track login query"),
    (r"https?://[^/\s:@\"']+:[^/\s@\"']+@", "a URL with a password in it"),
    (
        r"\b(?:password|passwd|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)\b"
        r"\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']",
        "a password, key or token literal",
    ),
)
# Text is scanned; these are read as bytes and skipped, since a float array cannot hold a
# credential in any form a regex would find and reading them costs seconds.
BINARY_SUFFIXES: frozenset[str] = frozenset({".bin", ".png", ".jpg", ".jpeg", ".webp", ".woff", ".woff2", ".parquet"})
# How much of a text file to scan. The bundles are megabytes of numbers; a credential that
# appeared only in the last kilobyte of objects.json would be a strange accident, but the
# files are small enough to read whole, so nothing is truncated. Kept as a named constant so
# the choice is visible if a future bundle is hundreds of megabytes.
SCAN_WHOLE_FILE = True


@dataclass(frozen=True)
class Finding:
    """One thing wrong with the bundle. ``error`` findings stop a deploy; warnings do not."""

    level: str  # 'error' or 'warning'
    path: str
    what: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.path}: {self.what}"


def _redactions(environ: Mapping[str, str]) -> list[tuple[str, str]]:
    """The literal credential values to search for, from the environment as it stands now.

    Short values are ignored: a one-character password would match every file and a false
    alarm that cries wolf is worse than no check.
    """
    out: list[tuple[str, str]] = []
    for name in (
        config.SPACETRACK_USER_ENV,
        config.SPACETRACK_PASS_ENV,
        "VERCEL_TOKEN",
        "CLOUDFLARE_API_TOKEN",
        "DRIFTWATCH_CONTACT",
    ):
        value = (environ.get(name) or "").strip()
        if len(value) >= 6:
            out.append((value, f"the value of ${name}"))
    return out


def scan_text(text: str, path: str, *, redactions: list[tuple[str, str]]) -> list[Finding]:
    """Every forbidden pattern, secret pattern and literal credential value in one file."""
    findings: list[Finding] = []
    for pattern, what in FORBIDDEN_CONTENT:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(Finding("error", path, f"contains {what} ({pattern})"))
    for pattern, what in SECRET_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            findings.append(Finding("error", path, f"looks like {what}: {match.group(0)[:40]!r}"))
    for value, what in redactions:
        if value in text:
            findings.append(Finding("error", path, f"contains {what}"))
    return findings


def audit_bundle(
    directory: Path, *, environ: Mapping[str, str] | None = None, max_file_bytes: int = PAGES_MAX_FILE_BYTES
) -> tuple[list[Finding], dict[str, Any]]:
    """Check every file under ``directory``: what it is, what it holds and how big it is.

    Returns the findings and a summary (file count, total bytes, the largest files) so the
    caller can report the size headroom whether or not anything was wrong.
    """
    directory = Path(directory)
    if not directory.exists():
        return [Finding("error", str(directory), "does not exist; nothing to publish")], {"n_files": 0}
    redactions = _redactions(environ if environ is not None else os.environ)
    findings: list[Finding] = []
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    sizes: list[tuple[int, str]] = []

    for path in files:
        rel = path.relative_to(directory).as_posix()
        size = path.stat().st_size
        sizes.append((size, rel))
        for pattern, what in FORBIDDEN_NAMES:
            if re.match(pattern, path.name):
                findings.append(Finding("error", rel, f"is {what}, which is never redistributed"))
        if size > max_file_bytes:
            findings.append(
                Finding(
                    "error",
                    rel,
                    f"is {size / 1024 / 1024:.1f} MiB, over the per-file ceiling of "
                    f"{max_file_bytes / 1024 / 1024:.0f} MiB (Cloudflare Pages' upload limit, kept on Vercel)",
                )
            )
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:  # pragma: no cover - unreadable file in a build directory
            findings.append(Finding("warning", rel, f"could not be read ({exc})"))
            continue
        findings.extend(scan_text(text, rel, redactions=redactions))

    if len(files) > PAGES_MAX_FILES:
        findings.append(
            Finding("error", str(directory), f"has {len(files)} files, over the Pages limit of {PAGES_MAX_FILES}")
        )
    sizes.sort(reverse=True)
    summary = {
        "directory": str(directory),
        "n_files": len(files),
        "total_mib": round(sum(s for s, _ in sizes) / 1024 / 1024, 2),
        "largest": [{"path": name, "mib": round(size / 1024 / 1024, 2)} for size, name in sizes[:5]],
        "limit_mib": round(max_file_bytes / 1024 / 1024, 1),
        "headroom_mib": round((max_file_bytes - sizes[0][0]) / 1024 / 1024, 2) if sizes else None,
        "n_errors": sum(1 for f in findings if f.level == "error"),
        "n_warnings": sum(1 for f in findings if f.level == "warning"),
    }
    return findings, summary
