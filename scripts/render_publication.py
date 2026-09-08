"""Render the corrected publication from its retained evidence, without rescoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import render_paper_v2

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads((ROOT / "docs/assets/benchmark-v2.json").read_text(encoding="utf-8"))
    outputs = {**render_paper_v2.render(data), **render_paper_v2.basis_correction_outputs(data)}
    for relative, text in outputs.items():
        expected = text.strip() + "\n"
        target = ROOT / relative
        if args.check:
            if target.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"Publication text differs: {relative}")
        else:
            target.write_text(expected, encoding="utf-8")
    print(f"{'Verified' if args.check else 'Rendered'} {len(outputs)} publication files")


if __name__ == "__main__":
    main()
