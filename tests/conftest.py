"""Shared fixtures: the sgp4 library's verification element sets, as TLEs and OMM records."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

import pytest
from sgp4.api import Satrec
from sgp4.exporter import export_omm


@pytest.fixture(scope="session")
def publication_inputs():
    """Restore and verify release artefacts for tests of stored publication data."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "scripts"))
    from publication_assets import restore_required

    restore_required(root=root)


@dataclass(frozen=True)
class VerificationTLE:
    """One entry from SGP4-VER.TLE, whose line 2 carries start/stop/step minutes after column 69."""

    comment: str
    line1: str
    line2: str

    @property
    def satnum(self) -> int:
        return Satrec.twoline2rv(self.line1, self.line2).satnum

    @property
    def time_grid(self) -> tuple[float, float, float]:
        start, stop, step = (float(x) for x in self.line2[69:].split())
        return start, stop, step


def load_verification_tles() -> list[VerificationTLE]:
    """Parse SGP4-VER.TLE shipped inside the sgp4 package."""
    text = files("sgp4").joinpath("SGP4-VER.TLE").read_text(encoding="ascii")
    lines = text.splitlines()
    out: list[VerificationTLE] = []
    comment = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            comment = line.lstrip("# ").strip()
            i += 1
            continue
        if line.startswith("1 "):
            out.append(VerificationTLE(comment, line, lines[i + 1]))
            i += 2
            continue
        i += 1
    return out


@pytest.fixture(scope="session")
def verification_tles() -> list[VerificationTLE]:
    return load_verification_tles()


def omm_record(line1: str, line2: str, name: str) -> dict:
    """An OMM dictionary shaped like CelesTrak's JSON, built from a TLE via the sgp4 exporter."""
    sat = Satrec.twoline2rv(line1, line2)
    record = export_omm(sat, name)
    # CelesTrak serialises numbers as JSON numbers; the exporter gives strings for some fields.
    for key in (
        "MEAN_MOTION",
        "ECCENTRICITY",
        "INCLINATION",
        "RA_OF_ASC_NODE",
        "ARG_OF_PERICENTER",
        "MEAN_ANOMALY",
        "BSTAR",
        "MEAN_MOTION_DOT",
        "MEAN_MOTION_DDOT",
    ):
        record[key] = float(record[key])
    for key in ("NORAD_CAT_ID", "ELEMENT_SET_NO", "REV_AT_EPOCH", "EPHEMERIS_TYPE"):
        record[key] = int(record[key])
    return record


@pytest.fixture(scope="session")
def omm_records(verification_tles) -> list[dict]:
    """OMM records for the verification objects that propagate cleanly at their epoch."""
    out = []
    for tle in verification_tles:
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        e, _, _ = sat.sgp4_tsince(0.0)
        if e == 0 and sat.ecco < 1.0 and sat.intldesg.strip():
            out.append(omm_record(tle.line1, tle.line2, f"OBJECT {sat.satnum}"))
    return out


def pytest_sessionstart(session) -> None:
    """Refuse to start when pymsis sits under a path NRLMSIS cannot read.

    The Fortran holds the parameter-file path in a 128-character buffer; past that it prints
    "MSIS parameter set ... not found. Stopping." and stops the interpreter with exit status 0
    (SWxTREC/pymsis#80), so a suite that reached a density test would end early and read as
    green. Failing here, before any test runs, is the loud version of that. The CI job also
    compares the tests that ran against the tests collected (scripts/check_test_count.py).
    """
    from pathlib import Path

    import pymsis

    parm = Path(pymsis.__file__).resolve().parent / "msis21.parm"
    limit = 128
    if len(str(parm)) > limit:
        pytest.exit(
            f"pymsis is installed at a path of {len(str(parm))} characters, past the {limit} the NRLMSIS "
            "Fortran can read; the density tests would stop the interpreter silently. Install under a "
            "shorter path.",
            returncode=3,
        )
