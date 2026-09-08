"""Fail if a v2 table, existing scalar substitution or paper body changes."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import publication_text

ROOT = Path(__file__).resolve().parents[1]
BEGIN = "<!-- BEGIN AVAILABILITY CORRECTION -->"
END = "<!-- END AVAILABILITY CORRECTION -->"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def table_hashes(text):
    return [digest("\n".join(block.splitlines())) for block in re.findall(r"(?m)(?:^\|[^\n]*\n?)+", text)]


def check(root=ROOT):
    baseline = json.loads((root / "docs/assets/publication-invariants-v2.json").read_text(encoding="utf-8"))
    raw = (root / "docs/assets/benchmark-v2.json").read_bytes()
    evidence_hash = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    differences = []
    for name, expected in baseline["tables"].items():
        actual = table_hashes((root / name).read_text(encoding="utf-8"))
        if actual != expected:
            differences.extend(
                f"{name}: table {i + 1}"
                for i in range(max(len(expected), len(actual)))
                if (expected[i] if i < len(expected) else None) != (actual[i] if i < len(actual) else None)
            )
    for token, expected in baseline["substitutions"].items():
        if digest(publication_text.scalar(data, token, evidence_hash)) != expected:
            differences.append("substitution: " + token)
    paper = (root / "docs/paper.md").read_text(encoding="utf-8")
    if paper.count(BEGIN) != 1 or paper.count(END) != 1:
        differences.append("availability amendment markers")
    else:
        original_body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n\n", "", paper, flags=re.DOTALL)
        original_body = original_body.replace(evidence_hash, baseline["baseline_evidence_sha256"])
        if digest(original_body) != baseline["paper_sha256"]:
            differences.append("paper body outside the availability amendment and evidence line")
    return {
        "baseline_commit": baseline["baseline_commit"],
        "old_evidence_sha256": baseline["baseline_evidence_sha256"],
        "new_evidence_sha256": evidence_hash,
        "table_count": sum(map(len, baseline["tables"].values())),
        "scalar_substitution_count": len(baseline["substitutions"]),
        "diff_count": len(differences),
        "differences": differences,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check()
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(bool(result["diff_count"]))
