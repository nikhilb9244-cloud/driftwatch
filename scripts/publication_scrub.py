"""Remove private provenance and embedded provider payloads without rescoring."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

WINDOWS_PATH = re.compile(r"(?i)(?<![a-z0-9_])[a-z]:[\\/][^\r\n<>\"`]*")
MACHINE = re.compile(r"(?i)\bDESKTOP-[A-Z0-9]+\b")
ASSISTANT = re.compile(r"(?i)\b(?:codex|chatgpt|openai|parent-created|the parent created)\b")
RAW_KEYS = frozenset(
    {"raw_record", "provider_record", "source_record", "raw_line", "source_line", "tle_line1", "tle_line2"}
)


def content_hash(value):
    """Hash a JSON value with a declared, deterministic encoding."""
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reference(identifier, value):
    return {"source_identifier": identifier, "content_sha256": content_hash(value)}


def scrub(value, *, workspace: Path, account_identifiers=(), location="", changes=None):
    """Retain computed results; replace source payloads with identities and hashes.

    Normalised UTC endpoints attached to computed residuals are derived results.
    Provider payloads, verbatim source descriptions and copied records are not.
    Acquisition dates, product identities, source URLs and original file hashes
    are our provenance metadata, and remain distinct from the provider payload.
    """
    if changes is None:
        changes = []

    def replaced(new, reason):
        if new != value:
            changes.append(
                {
                    "pointer": location,
                    "reason": reason,
                    "old_content_sha256": content_hash(value),
                    "new_content_sha256": content_hash(new),
                }
            )
        return new

    if isinstance(value, dict):
        if set(value) == {"source_identifier", "content_sha256"}:
            return value
        if {"NORAD_CAT_ID", "EPOCH"} <= value.keys() or {"line1", "line2"} <= value.keys():
            identifier = f"provider:gp/{value.get('NORAD_CAT_ID', 'record')}/{value.get('EPOCH', content_hash(value))}"
            return replaced(reference(identifier, value), "embedded provider element record")
        result = {}
        for key, item in value.items():
            pointer = location + "/" + key.replace("~", "~0").replace("/", "~1")
            if key in {"raw_path", "raw_file"}:
                changes.append(
                    {
                        "pointer": pointer,
                        "reason": "local provider snapshot location removed",
                        "old_content_sha256": content_hash(item),
                        "new_content_sha256": content_hash(None),
                    }
                )
                continue
            if key in RAW_KEYS or key == "measured_metrics" or (key == "site" and isinstance(item, dict)):
                source = (
                    "provider:meerkat-specifications"
                    if key == "site"
                    else str(value.get("source_url", value.get("source_id", "provider:record")))
                )
                result[key] = reference(source + "#" + key, item)
                changes.append(
                    {
                        "pointer": pointer,
                        "reason": "embedded third-party record replaced",
                        "old_content_sha256": content_hash(item),
                        "new_content_sha256": content_hash(result[key]),
                    }
                )
                continue
            if key == "manoeuvres_recorded" and isinstance(item, list):
                result["manoeuvres_recorded_count"] = len(item)
                source = (value.get("manoeuvre_record_provenance") or {}).get("source_id", "published-manoeuvre-record")
                result[key] = reference(source + "#normalised-interval-inventory", item)
                changes.append(
                    {
                        "pointer": pointer,
                        "reason": "embedded provider interval inventory replaced; derived count retained",
                        "old_content_sha256": content_hash(item),
                        "new_content_sha256": content_hash(result[key]),
                    }
                )
                continue
            if key == "email":
                result[key] = reference("docs/publication-metadata.json#/email", item)
                changes.append(
                    {
                        "pointer": pointer,
                        "reason": "author contact belongs in publication metadata",
                        "old_content_sha256": content_hash(item),
                        "new_content_sha256": content_hash(result[key]),
                    }
                )
                continue
            if key in {"author_verbatim", "recorded_from"}:
                result[key + "_reference"] = reference("author-attestation#" + key, item)
                changes.append(
                    {
                        "pointer": pointer,
                        "reason": "verbatim session provenance replaced",
                        "old_content_sha256": content_hash(item),
                        "new_content_sha256": content_hash(result[key + "_reference"]),
                    }
                )
                continue
            if key == "source" and isinstance(item, str) and "SARAO" in item:
                result[key] = reference("provider:meerkat-specifications", item)
                changes.append(
                    {
                        "pointer": pointer,
                        "reason": "verbatim provider description replaced",
                        "old_content_sha256": content_hash(item),
                        "new_content_sha256": content_hash(result[key]),
                    }
                )
                continue
            result[key] = scrub(
                item, workspace=workspace, account_identifiers=account_identifiers, location=pointer, changes=changes
            )
        return result
    if isinstance(value, list):
        return [
            scrub(
                v,
                workspace=workspace,
                account_identifiers=account_identifiers,
                location=location + f"/{i}",
                changes=changes,
            )
            for i, v in enumerate(value)
        ]
    if isinstance(value, str):
        normal = value.replace("\\", "/")
        prefix = workspace.resolve().as_posix().rstrip("/") + "/"
        if normal.lower().startswith(prefix.lower()):
            return replaced(normal[len(prefix) :], "workspace-relative path")
        if WINDOWS_PATH.search(value) or MACHINE.search(value) or re.search(r"(?i)(?:^|[\s`])/(?:Users|home)/", value):
            return replaced(
                "withheld-local-reference:sha256:" + content_hash(value), "private path or machine identifier removed"
            )
        if any(account and account.lower() in value.lower() for account in account_identifiers):
            return replaced(reference("publication-account-reference", value), "account identifier removed")
        if ASSISTANT.search(value):
            return replaced(
                "withheld-execution-reference:sha256:" + content_hash(value), "assistant execution trace removed"
            )
    return value
