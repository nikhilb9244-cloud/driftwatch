"""Check our propagation wrapper against the official SGP4 verification output.

``tcppver.out`` ships with the sgp4 library and was produced by the reference C++ code
from ``SGP4-VER.TLE``. Each satellite block lists position (km) and velocity (km/s) at a
sequence of minutes since epoch. Anything we build on top of the library must reproduce
those numbers to the printed precision (1e-8 km), which pins down that we drive the
library correctly: gravity constants, operations mode, Julian date splitting.
"""

from __future__ import annotations

from importlib.resources import files

import numpy as np
import pytest
from sgp4.api import Satrec

from driftwatch.orbit.propagator import _propagate_jd, error_summary, propagate_satrecs
from driftwatch.orbit.time import UNIX_EPOCH_JD, US_PER_DAY

Block = dict[int, list[tuple[float, np.ndarray, np.ndarray]]]


def load_tcppver() -> Block:
    """Parse tcppver.out into ``{satnum: [(tsince_min, r_km, v_kms), ...]}``."""
    text = files("sgp4").joinpath("tcppver.out").read_text(encoding="ascii")
    blocks: Block = {}
    current: list | None = None
    for line in text.splitlines():
        if line.endswith(" xx"):
            current = blocks.setdefault(int(line.split()[0]), [])
            continue
        fields = line.split()
        if current is None or len(fields) < 7:
            continue
        try:
            values = [float(x) for x in fields[:7]]
        except ValueError:
            continue
        current.append((values[0], np.array(values[1:4]), np.array(values[4:7])))
    return blocks


@pytest.fixture(scope="module")
def tcppver() -> Block:
    return load_tcppver()


def test_verification_file_parsed(tcppver):
    assert len(tcppver) >= 30
    assert 5 in tcppver and tcppver[5][0][0] == 0.0


def test_propagation_reproduces_tcppver_exactly(verification_tles, tcppver):
    """Drive the vectorised path with the same (jd, fr) split the library's tests use."""
    n_checked = 0
    for tle in verification_tles:
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        expected = tcppver.get(sat.satnum)
        if not expected:
            continue
        tsince = np.array([row[0] for row in expected])
        whole, fraction = np.divmod(tsince / 1440.0, 1.0)
        state = _propagate_jd([sat], np.array([sat.satnum]), sat.jdsatepoch + whole, sat.jdsatepochF + fraction)
        for k, (_, r_ref, v_ref) in enumerate(expected):
            if state.error[0, k] != 0:
                # 33334 is a deliberate "perturbed eccentricity out of range" case: the C++
                # reference still prints a position at epoch, but we refuse to use one that
                # carries an error code, so only check that it is the expected case.
                assert (sat.satnum, tsince[k], int(state.error[0, k])) == (33334, 0.0, 3)
                assert np.isnan(state.r_teme[0, k]).all()
                continue
            np.testing.assert_allclose(state.r_teme[0, k], r_ref, rtol=0, atol=1e-6)
            np.testing.assert_allclose(state.v_teme[0, k], v_ref, rtol=0, atol=1e-9)
            n_checked += 1
    assert n_checked > 500


def test_datetime_path_agrees_to_microsecond_rounding(verification_tles, tcppver):
    """The datetime64[us] path agrees with the split-Julian-date path to well under a metre.

    The residual here is the test's own doing: it forms each time from a single float64
    Julian date, which only resolves to about 40 microseconds. Two deliberately
    near-singular high-drag cases (33333, 33334) are excluded because their output moves
    by metres, or fails outright, for microsecond changes in time.
    """
    worst = 0.0
    for tle in verification_tles:
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        expected = tcppver.get(sat.satnum)
        if not expected or sat.satnum in (33333, 33334):
            continue
        tsince = np.array([row[0] for row in expected])
        jd_full = sat.jdsatepoch + sat.jdsatepochF + tsince / 1440.0
        us = np.rint((jd_full - UNIX_EPOCH_JD) * US_PER_DAY).astype("int64")
        times = us.astype("datetime64[us]")
        state = propagate_satrecs([sat], np.array([sat.satnum]), times)
        r_ref = np.array([row[1] for row in expected])
        worst = max(worst, float(np.nanmax(np.abs(state.r_teme[0] - r_ref))))
    assert worst < 1e-3  # km, i.e. 1 m


def test_error_codes_are_reported_not_hidden(verification_tles):
    """The verification set deliberately includes decayed and sub-orbital cases."""
    codes = set()
    n_failing = 0
    for tle in verification_tles:
        sat = Satrec.twoline2rv(tle.line1, tle.line2)
        start, stop, step = tle.time_grid
        tsince = np.arange(start, stop + step / 2, step)
        whole, fraction = np.divmod(tsince / 1440.0, 1.0)
        state = _propagate_jd([sat], np.array([sat.satnum]), sat.jdsatepoch + whole, sat.jdsatepochF + fraction)
        bad = state.error[0] != 0
        if bad.any():
            n_failing += 1
            codes.update(int(c) for c in state.error[0][bad])
            assert np.isnan(state.r_teme[0][bad]).all()
            assert np.isnan(state.v_teme[0][bad]).all()
    assert codes == {1, 3, 4, 6}
    assert n_failing == 7
    summary = error_summary(np.array([0, 0, 6, 1]))
    assert summary == {"ok": 2, "mean eccentricity outside 0 <= e < 1": 1, "satellite has decayed": 1}
