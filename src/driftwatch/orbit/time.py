"""Time handling: UTC parsing and Julian dates in the split form SGP4 expects.

SGP4 works in minutes since the element set epoch. The sgp4 library takes the target
time as a Julian date split into a whole part ``jd`` (ending in .5, so it is a midnight)
and a fraction ``fr`` in [0, 1), because a single float64 Julian date only resolves to
about 10 microseconds and the split keeps full precision. The scale is UTC throughout:
TLE epochs are UTC and SGP4 only ever uses time differences.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

UNIX_EPOCH_JD = 2440587.5  # Julian date of 1970-01-01T00:00:00 UTC
US_PER_DAY = 86_400_000_000
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def parse_utc(value: str | datetime) -> datetime:
    """Parse an ISO 8601 string (``Z`` or offset) or normalise a datetime to aware UTC.

    Naive inputs are taken to be UTC, since nothing in this project is ever local time.
    """
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.strip()
        if text.endswith("Z") or text.endswith("z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def unix_microseconds(t: datetime) -> int:
    """Integer microseconds since the Unix epoch, exact for aware datetimes."""
    delta = parse_utc(t) - _UNIX_EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def julian_date(t: datetime) -> tuple[float, float]:
    """Return ``(jd, fr)`` for a UTC datetime, matching ``sgp4.api.jday``.

    ``jd`` is the Julian date of the preceding midnight (a value ending in .5) and ``fr``
    the fraction of the day since then.
    """
    us = unix_microseconds(t)
    days, rem = divmod(us, US_PER_DAY)
    return UNIX_EPOCH_JD + days, rem / US_PER_DAY


def julian_dates(times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised :func:`julian_date` for a ``datetime64`` array of any unit."""
    us = np.asarray(times, dtype="datetime64[us]").astype("int64")
    days, rem = np.divmod(us, US_PER_DAY)
    return UNIX_EPOCH_JD + days.astype(np.float64), rem.astype(np.float64) / US_PER_DAY


def to_datetime64(times) -> np.ndarray:
    """Coerce datetimes, ISO strings or datetime64 values to a ``datetime64[us]`` array."""
    if isinstance(times, (str, datetime)):
        times = [times]
    out = []
    for item in times:
        if isinstance(item, np.datetime64):
            out.append(item.astype("datetime64[us]"))
        else:
            dt = parse_utc(item).replace(tzinfo=None)
            out.append(np.datetime64(dt, "us"))
    return np.array(out, dtype="datetime64[us]")


def stamp(t: datetime) -> str:
    """Compact UTC stamp used in file names, e.g. ``20260901T120000Z``."""
    return parse_utc(t).strftime("%Y%m%dT%H%M%SZ")


def datetime64_to_datetime(value: np.datetime64) -> datetime:
    """Convert a ``datetime64`` to an aware UTC datetime with microsecond precision."""
    us = int(np.datetime64(value, "us").astype("int64"))
    return _UNIX_EPOCH + timedelta(microseconds=us)
