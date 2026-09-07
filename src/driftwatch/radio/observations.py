"""Archived observations: what the demonstrator runs on, and where each record came from.

An observation is a pointing, a start, a duration and a receiver, and nothing more is needed
from the archive. The SARAO archive search returns, per source, the source name and
coordinates, the on-source duration, the band, the observed date and the proposal, but only to a
logged-in SARAO account (skaafrica.atlassian.net, ESDKB page 302546945: "You will need a SARAO
account in order to use the MeerKAT archive search"). This module therefore reads a plain CSV
with the columns below, which is what an archive export reduces to, and every row carries a
``source`` column saying where the record was read, so that a record from a published circular
and a record from an archive export are told apart in the report.

CSV columns: ``observation_id, target, ra, dec, start_utc, duration_s, band, centre_mhz, source, note``.
``ra`` is degrees or ``HH:MM:SS.s``; ``dec`` is degrees or ``+DD:MM:SS.s``; ``start_utc`` is ISO 8601;
``band`` is one of the receiver names; ``centre_mhz`` may be blank for the band centre.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from driftwatch.orbit.time import parse_utc
from driftwatch.radio.site import Receiver, beam_fwhm_deg, receiver

_SEXAGESIMAL = re.compile(r"^\s*([+-]?)\s*(\d{1,3})[:\s h]\s*(\d{1,2})[:\s m]\s*(\d{1,2}(?:\.\d*)?)\s*s?\s*$")


def parse_angle(text: str, *, hours: bool) -> float:
    """Degrees from decimal degrees or a sexagesimal string, in hours of right ascension when ``hours``."""
    s = str(text).strip()
    try:
        return float(s)
    except ValueError:
        pass
    m = _SEXAGESIMAL.match(s)
    if m is None:
        raise ValueError(f"cannot read the angle {text!r}")
    sign = -1.0 if m.group(1) == "-" else 1.0
    value = float(m.group(2)) + float(m.group(3)) / 60.0 + float(m.group(4)) / 3600.0
    return sign * value * (15.0 if hours else 1.0)


@dataclass(frozen=True)
class Observation:
    observation_id: str
    target: str
    ra_deg: float
    dec_deg: float
    start: datetime
    duration_s: float
    receiver: Receiver
    centre_mhz: float
    source: str
    note: str = ""

    @property
    def end(self) -> datetime:
        return self.start + timedelta(seconds=self.duration_s)

    @property
    def fwhm_deg(self) -> float:
        return beam_fwhm_deg(self.centre_mhz)

    def record(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "target": self.target,
            "ra_deg": self.ra_deg,
            "dec_deg": self.dec_deg,
            "start_utc": self.start.isoformat().replace("+00:00", "Z"),
            "end_utc": self.end.isoformat().replace("+00:00", "Z"),
            "duration_s": self.duration_s,
            "band": self.receiver.name,
            "centre_mhz": self.centre_mhz,
            "beam_fwhm_deg": self.fwhm_deg,
            "source": self.source,
            "note": self.note,
        }


REQUIRED = ("observation_id", "target", "ra", "dec", "start_utc", "duration_s", "band", "source")


def read_observations(path: Path) -> list[Observation]:
    """Read the observation CSV; refuse a row that is missing a required field."""
    out: list[Observation] = []
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {', '.join(missing)}")
        for k, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            for c in REQUIRED:
                if not (row.get(c) or "").strip():
                    raise ValueError(f"{path} line {k}: {c!r} is empty")
            rx = receiver(row["band"])
            centre = row.get("centre_mhz") or ""
            out.append(
                Observation(
                    observation_id=row["observation_id"].strip(),
                    target=row["target"].strip(),
                    ra_deg=parse_angle(row["ra"], hours=":" in row["ra"] or "h" in row["ra"].lower()),
                    dec_deg=parse_angle(row["dec"], hours=False),
                    start=parse_utc(row["start_utc"].strip()),
                    duration_s=float(row["duration_s"]),
                    receiver=rx,
                    centre_mhz=float(centre) if centre.strip() else rx.centre_mhz,
                    source=row["source"].strip(),
                    note=(row.get("note") or "").strip(),
                )
            )
    return out
