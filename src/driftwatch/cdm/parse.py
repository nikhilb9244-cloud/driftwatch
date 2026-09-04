"""Reading and writing CCSDS Conjunction Data Messages (CCSDS 508.0-B-1).

Two forms, one structure. A **KVN** message is ``KEY = value [unit]`` lines: a header, the
relative metadata and data (the time of closest approach, the miss vector, the probability),
then ``OBJECT = OBJECT1`` and ``OBJECT = OBJECT2`` introducing each object's metadata, orbit
determination parameters, state vector and covariance. The **XML** form carries the same keys as
element names inside ``header``, ``relativeMetadataData`` and two ``segment`` blocks, with units
as attributes. Both are read into :class:`ConjunctionDataMessage`, which keeps every key it saw
in ``raw`` so nothing the standard allows is lost by the fields this project happens to type.

What is typed is what the matcher and the report need: both designators, the time of closest
approach, the miss distance and its RTN components, the relative speed, the probability and its
method, and each object's RTN position covariance. Units follow the standard: metres and metres
per second for the relative quantities, kilometres and kilometres per second for the state
vectors, square metres for the covariance. They are converted to this project's kilometres at
the point of use, never in the stored message, so a parsed message reads back exactly as it was
written.

Comments (``COMMENT`` lines) are kept per section. Dates are ISO 8601 in either calendar or
day-of-year form and are read as UTC, which the standard fixes.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RELATIVE = "relative"
OBJECT1 = "OBJECT1"
OBJECT2 = "OBJECT2"

#: The six lower-triangle position covariance keys, in the order the standard lists them.
COVARIANCE_KEYS: tuple[str, ...] = ("CR_R", "CT_R", "CT_T", "CN_R", "CN_T", "CN_N")
STATE_KEYS: tuple[str, ...] = ("X", "Y", "Z", "X_DOT", "Y_DOT", "Z_DOT")

_LINE = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$")
_UNIT = re.compile(r"^(.*?)\s*\[([^\]]*)\]\s*$")
_DOY = re.compile(r"^(\d{4})-(\d{3})T(.*)$")


def _parse_value(text: str) -> tuple[Any, str | None]:
    """A KVN value into a number where it is one, with its unit split off."""
    unit = None
    m = _UNIT.match(text)
    if m:
        text, unit = m.group(1).strip(), m.group(2).strip()
    try:
        return float(text), unit
    except ValueError:
        return text, unit


def parse_epoch(text: Any) -> pd.Timestamp:
    """A CCSDS epoch string -- ``2024-05-10T12:34:56.789`` or ``2024-131T12:34:56`` -- as a UTC timestamp."""
    s = str(text).strip()
    if s.endswith("Z"):
        s = s[:-1]
    m = _DOY.match(s)
    if m:
        base = pd.Timestamp(year=int(m.group(1)), month=1, day=1) + pd.Timedelta(days=int(m.group(2)) - 1)
        return (base + pd.Timedelta(pd.Timestamp("1970-01-01T" + m.group(3)) - pd.Timestamp("1970-01-01"))).tz_localize(
            "UTC"
        )
    stamp = pd.Timestamp(s)
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


def format_epoch(stamp: pd.Timestamp) -> str:
    """The calendar form the standard prefers, to the millisecond, without a zone suffix."""
    t = pd.Timestamp(stamp)
    t = t.tz_convert("UTC") if t.tzinfo is not None else t.tz_localize("UTC")
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}"


def normalise_designator(value: Any) -> str:
    """An ``OBJECT_DESIGNATOR`` as a comparable string: ``"00025544"`` and ``25544.0`` both read ``25544``."""
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.0+)?", text):
        return str(int(float(text)))
    return text


@dataclass
class CdmObject:
    """One of the two objects: its identity, its state at TCA and its RTN position covariance."""

    role: str  # OBJECT1 or OBJECT2
    raw: dict[str, Any] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    comments: list[str] = field(default_factory=list)

    @property
    def designator(self) -> str:
        return normalise_designator(self.raw.get("OBJECT_DESIGNATOR"))

    @property
    def name(self) -> str:
        return str(self.raw.get("OBJECT_NAME", "") or "")

    @property
    def object_type(self) -> str:
        return str(self.raw.get("OBJECT_TYPE", "") or "")

    @property
    def maneuverable(self) -> str:
        return str(self.raw.get("MANEUVERABLE", "") or "")

    @property
    def state_km(self) -> np.ndarray | None:
        """``(x, y, z, xdot, ydot, zdot)`` in km and km/s, or None when the message carries no state."""
        if not all(k in self.raw for k in STATE_KEYS):
            return None
        return np.array([float(self.raw[k]) for k in STATE_KEYS], dtype=float)

    @property
    def covariance_rtn_m2(self) -> np.ndarray | None:
        """The 3 x 3 RTN position covariance in m^2, or None when any of the six terms is absent."""
        if not all(k in self.raw for k in COVARIANCE_KEYS):
            return None
        c = {k: float(self.raw[k]) for k in COVARIANCE_KEYS}
        return np.array(
            [
                [c["CR_R"], c["CT_R"], c["CN_R"]],
                [c["CT_R"], c["CT_T"], c["CN_T"]],
                [c["CN_R"], c["CN_T"], c["CN_N"]],
            ],
            dtype=float,
        )

    @property
    def sigma_rtn_m(self) -> np.ndarray | None:
        cov = self.covariance_rtn_m2
        return None if cov is None else np.sqrt(np.clip(np.diag(cov), 0.0, None))


@dataclass
class ConjunctionDataMessage:
    """One CDM, whichever form it arrived in. ``raw`` holds every relative-section key verbatim."""

    raw: dict[str, Any] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    comments: list[str] = field(default_factory=list)
    object1: CdmObject = field(default_factory=lambda: CdmObject(OBJECT1))
    object2: CdmObject = field(default_factory=lambda: CdmObject(OBJECT2))
    source: str = ""  # the file it came from, for the report
    form: str = "kvn"  # kvn or xml

    # Header -----------------------------------------------------------------------------
    @property
    def version(self) -> str:
        return str(self.raw.get("CCSDS_CDM_VERS", "") or "")

    @property
    def message_id(self) -> str:
        """The MESSAGE_ID as text: a purely numeric id reads back without a trailing ``.0``."""
        value = self.raw.get("MESSAGE_ID", "")
        if isinstance(value, float):
            return format_number(value)
        return str(value or "")

    @property
    def originator(self) -> str:
        return str(self.raw.get("ORIGINATOR", "") or "")

    @property
    def creation_date(self) -> pd.Timestamp | None:
        value = self.raw.get("CREATION_DATE")
        return parse_epoch(value) if value not in (None, "") else None

    # The encounter ------------------------------------------------------------------------
    @property
    def tca(self) -> pd.Timestamp:
        return parse_epoch(self.raw["TCA"])

    @property
    def miss_distance_m(self) -> float:
        return float(self.raw.get("MISS_DISTANCE", np.nan))

    @property
    def relative_speed_ms(self) -> float:
        return float(self.raw.get("RELATIVE_SPEED", np.nan))

    @property
    def relative_position_rtn_m(self) -> np.ndarray:
        return np.array([float(self.raw.get(f"RELATIVE_POSITION_{k}", np.nan)) for k in ("R", "T", "N")], dtype=float)

    @property
    def relative_velocity_rtn_ms(self) -> np.ndarray:
        return np.array([float(self.raw.get(f"RELATIVE_VELOCITY_{k}", np.nan)) for k in ("R", "T", "N")], dtype=float)

    @property
    def collision_probability(self) -> float:
        value = self.raw.get("COLLISION_PROBABILITY")
        return float(value) if value not in (None, "") else float("nan")

    @property
    def collision_probability_method(self) -> str:
        return str(self.raw.get("COLLISION_PROBABILITY_METHOD", "") or "")

    @property
    def screen_period(self) -> tuple[pd.Timestamp, pd.Timestamp] | None:
        start, stop = self.raw.get("START_SCREEN_PERIOD"), self.raw.get("STOP_SCREEN_PERIOD")
        if start in (None, "") or stop in (None, ""):
            return None
        return parse_epoch(start), parse_epoch(stop)

    @property
    def pair(self) -> frozenset[str]:
        """The two designators as an unordered pair, which is what an event is matched on."""
        return frozenset({self.object1.designator, self.object2.designator})

    def summary(self) -> dict[str, Any]:
        """The fields the report prints, JSON-friendly."""
        return {
            "message_id": self.message_id,
            "originator": self.originator,
            "creation_date": self.creation_date.isoformat() if self.creation_date is not None else None,
            "tca": self.tca.isoformat(),
            "object1": self.object1.designator,
            "object1_name": self.object1.name,
            "object2": self.object2.designator,
            "object2_name": self.object2.name,
            "miss_distance_m": self.miss_distance_m,
            "relative_speed_ms": self.relative_speed_ms,
            "collision_probability": self.collision_probability,
            "collision_probability_method": self.collision_probability_method,
            "source": self.source,
            "form": self.form,
        }


# --------------------------------------------------------------------------------------
# KVN


def parse_kvn(text: str, *, source: str = "") -> ConjunctionDataMessage:
    """Read a KVN message. Unknown keys are kept; malformed lines are collected as comments."""
    cdm = ConjunctionDataMessage(source=source, form="kvn")
    section = RELATIVE
    targets = {RELATIVE: cdm, OBJECT1: cdm.object1, OBJECT2: cdm.object2}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("COMMENT"):
            targets[section].comments.append(stripped[len("COMMENT") :].strip())
            continue
        m = _LINE.match(line)
        if not m:
            targets[section].comments.append(stripped)
            continue
        key, rest = m.group(1), m.group(2)
        value, unit = _parse_value(rest)
        if key == "OBJECT":
            role = str(value).strip().upper()
            if role not in (OBJECT1, OBJECT2):
                raise ValueError(f"OBJECT must be OBJECT1 or OBJECT2, got {value!r}")
            section = role
            targets[section].raw["OBJECT"] = role
            continue
        targets[section].raw[key] = value
        if unit:
            targets[section].units[key] = unit
    if "TCA" not in cdm.raw:
        raise ValueError(f"not a CDM: no TCA in {source or 'the text'}")
    return cdm


def to_kvn(cdm: ConjunctionDataMessage) -> str:
    """Write a message back out as KVN, header first, in the order the keys were read.

    Units are written where the message carries them. The result parses back to an equal
    ``raw`` on every section, which is what the round-trip test pins.
    """

    def lines(raw: dict[str, Any], units: dict[str, str], comments: list[str]) -> list[str]:
        out = [f"COMMENT {c}" for c in comments]
        for key, value in raw.items():
            if key == "OBJECT":
                continue
            if isinstance(value, float):
                text = format_number(value)
            else:
                text = str(value)
            unit = units.get(key)
            out.append(f"{key:<28} = {text}" + (f" [{unit}]" if unit else ""))
        return out

    body = lines(cdm.raw, cdm.units, cdm.comments)
    for obj in (cdm.object1, cdm.object2):
        body.append(f"{'OBJECT':<28} = {obj.role}")
        body.extend(lines(obj.raw, obj.units, obj.comments))
    return "\n".join(body) + "\n"


def format_number(value: float) -> str:
    """A float without trailing noise: integers as integers, otherwise up to 12 significant figures."""
    if not np.isfinite(value):
        return "NaN"
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.12g}"


# --------------------------------------------------------------------------------------
# XML


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_xml(text: str, *, source: str = "") -> ConjunctionDataMessage:
    """Read the XML form. Element names are the KVN keys; ``units`` attributes are the units.

    The two ``segment`` elements are the two objects, in document order, and each one's
    ``OBJECT`` element confirms which. Namespaces are ignored: the message is the same whether
    or not it declares the NDM schema.
    """
    root = ET.fromstring(text)
    cdm = ConjunctionDataMessage(source=source, form="xml")
    version = root.attrib.get("version")
    if version:
        cdm.raw["CCSDS_CDM_VERS"] = _parse_value(version)[0]
    segments: list[CdmObject] = []

    def visit(element: ET.Element, target: Any) -> None:
        for child in element:
            name = _local(child.tag)
            if name == "segment":
                obj = CdmObject(OBJECT1 if not segments else OBJECT2)
                segments.append(obj)
                visit(child, obj)
                continue
            if len(child):
                visit(child, target)
                continue
            value_text = (child.text or "").strip()
            if name == "COMMENT":
                target.comments.append(value_text)
                continue
            key = name.upper()
            value, _ = _parse_value(value_text)
            unit = child.attrib.get("units")
            if key == "OBJECT":
                target.raw["OBJECT"] = str(value).strip().upper()
                continue
            target.raw[key] = value
            if unit:
                target.units[key] = unit

    visit(root, cdm)
    for obj in segments:
        role = str(obj.raw.get("OBJECT", obj.role)).upper()
        if role == OBJECT1:
            cdm.object1 = CdmObject(OBJECT1, obj.raw, obj.units, obj.comments)
        elif role == OBJECT2:
            cdm.object2 = CdmObject(OBJECT2, obj.raw, obj.units, obj.comments)
        else:
            raise ValueError(f"segment OBJECT must be OBJECT1 or OBJECT2, got {role!r}")
    if "TCA" not in cdm.raw:
        raise ValueError(f"not a CDM: no TCA in {source or 'the text'}")
    return cdm


# --------------------------------------------------------------------------------------
# Either


def parse(text: str, *, source: str = "") -> ConjunctionDataMessage:
    """KVN or XML, decided by the first non-blank character."""
    head = text.lstrip()
    if head.startswith("<"):
        return parse_xml(text, source=source)
    return parse_kvn(text, source=source)


def load_cdms(path: Path | str) -> list[ConjunctionDataMessage]:
    """Every message in a file or, for a directory, in every ``*.cdm``, ``*.kvn``, ``*.txt`` and ``*.xml`` under it.

    Sorted by path so a report is reproducible. A file that is not a CDM raises with its name
    rather than being skipped: a silently ignored message is the failure mode this exists to
    prevent.
    """
    root = Path(path)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix.lower() in _SUFFIXES)
    out: list[ConjunctionDataMessage] = []
    for file in files:
        out.append(parse(file.read_text(encoding="utf-8", errors="replace"), source=str(file)))
    return out


_SUFFIXES = {".cdm", ".kvn", ".txt", ".xml"}
