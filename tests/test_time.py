from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from sgp4.api import jday

from driftwatch.orbit.time import (
    datetime64_to_datetime,
    julian_date,
    julian_dates,
    parse_utc,
    stamp,
    to_datetime64,
    unix_microseconds,
)


@pytest.mark.parametrize(
    "text",
    ["2026-09-01T12:00:00Z", "2026-09-01T12:00:00+00:00", "2026-09-01T14:00:00+02:00", "2026-09-01 12:00:00"],
)
def test_parse_utc_normalises(text):
    dt = parse_utc(text)
    assert dt.tzinfo == UTC
    assert dt == datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)


def test_julian_date_matches_sgp4_jday():
    cases = [
        datetime(1970, 1, 1, tzinfo=UTC),
        datetime(2000, 1, 1, 12, tzinfo=UTC),
        datetime(2024, 5, 10, 17, 3, 27, 123456, tzinfo=UTC),
        datetime(2026, 9, 1, 23, 59, 59, 999999, tzinfo=UTC),
    ]
    for dt in cases:
        jd, fr = julian_date(dt)
        ref_jd, ref_fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
        assert jd == ref_jd
        assert abs(fr - ref_fr) < 1e-12
        assert jd % 1.0 == 0.5  # whole part ends at a midnight


def test_julian_dates_vectorised_matches_scalar():
    dts = [datetime(2026, 9, 1, tzinfo=UTC) + timedelta(minutes=17 * k, microseconds=k) for k in range(50)]
    jd, fr = julian_dates(to_datetime64(dts))
    for k, dt in enumerate(dts):
        sjd, sfr = julian_date(dt)
        assert jd[k] == sjd
        assert abs(fr[k] - sfr) < 1e-12


def test_unix_microseconds_is_exact():
    dt = datetime(2026, 9, 1, 12, 0, 0, 1, tzinfo=UTC)
    assert unix_microseconds(dt) == 1788264000000001


def test_datetime64_roundtrip():
    dt = datetime(2024, 5, 10, 17, 3, 27, 123456, tzinfo=UTC)
    arr = to_datetime64([dt])
    assert arr.dtype == np.dtype("datetime64[us]")
    assert datetime64_to_datetime(arr[0]) == dt


def test_stamp():
    assert stamp("2026-09-01T12:00:00Z") == "20260901T120000Z"
