"""Refuse a CI run whose pytest session did not execute every test it collected.

pytest can exit 0 after running only part of the suite. The NRLMSIS Fortran behind pymsis holds
the path to its parameter file in a 128-character buffer; installed under a longer path it prints
``MSIS parameter set ... not found. Stopping.`` and stops the interpreter, and a plain Fortran
``STOP`` exits with status 0 (SWxTREC/pymsis#80). A shell or a CI step then reads the truncated
run as green: on 2026-09-07 that was about 66 of 594 tests. Nothing in pytest's own exit status
can see it, because pytest never gets to write one.

This script closes that gap from the outside. It reads the JUnit report the run was asked to write
(pytest writes it at the end of the session, so a run that stopped early leaves no report at all),
collects the suite again to count what should have run, and refuses unless the two agree and both
are at or above a floor. The floor is the number of tests the suite held when it was last raised;
lower it deliberately, in the same commit that removes tests.

Usage::

    uv run pytest -q --junitxml=pytest-report.xml
    uv run python scripts/check_test_count.py pytest-report.xml [--min N]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# The workflow-health suite on 2026-09-08. Raise it when tests are added; lower it only
# with the tests it counts.
EXPECTED_MINIMUM = 746


def reported_tests(report: Path) -> tuple[int, int]:
    """(test cases, errors) summed over every ``<testsuite>`` in a JUnit report."""
    root = ET.parse(report).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(s.get("tests", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    return tests, errors


def collected_tests() -> int:
    """How many tests pytest collects for the suite, from its own summary line."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"(\d+) tests? collected", proc.stdout + proc.stderr)
    if match is None:
        sys.stderr.write(proc.stdout[-2000:] + proc.stderr[-2000:])
        raise SystemExit("could not read the collected test count from pytest --collect-only")
    return int(match.group(1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="the JUnit XML pytest wrote with --junitxml")
    parser.add_argument("--min", type=int, default=EXPECTED_MINIMUM, help=f"floor (default {EXPECTED_MINIMUM})")
    args = parser.parse_args(argv)

    if not args.report.exists():
        print(f"FAIL: {args.report} was not written; the pytest session did not reach its end", file=sys.stderr)
        return 1
    ran, errors = reported_tests(args.report)
    collected = collected_tests()
    problems = []
    if ran != collected:
        problems.append(f"{ran} test cases reported against {collected} collected")
    if collected < args.min:
        problems.append(f"{collected} tests collected, below the floor of {args.min}")
    if errors:
        problems.append(f"{errors} collection or setup error(s) in the report")
    if problems:
        print("FAIL: " + "; ".join(problems), file=sys.stderr)
        return 1
    print(f"OK: {ran} tests ran, {collected} collected, floor {args.min}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
