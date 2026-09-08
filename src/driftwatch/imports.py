"""Bounded adapters for orbit exchange formats; not a full CCSDS schema validator."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from math import isfinite
from xml.etree import ElementTree as ET

import pandas as pd
from sgp4.api import Satrec
from sgp4.earth_gravity import wgs72
from sgp4.exporter import export_omm
from sgp4.io import twoline2rv as validate_tle
from sgp4.io import verify_checksum

CONVENTIONS = {"CENTER_NAME": "EARTH", "REF_FRAME": "TEME", "TIME_SYSTEM": "UTC", "MEAN_ELEMENT_THEORY": "SGP4"}
STATE_KEYS = ("EPOCH", "X", "Y", "Z", "X_DOT", "Y_DOT", "Z_DOT")
UNITS = {
    "X": "km",
    "Y": "km",
    "Z": "km",
    "X_DOT": "km/s",
    "Y_DOT": "km/s",
    "Z_DOT": "km/s",
    "MEAN_MOTION": "rev/day",
    "ECCENTRICITY": "1",
    "INCLINATION": "deg",
    "RA_OF_ASC_NODE": "deg",
    "ARG_OF_PERICENTER": "deg",
    "MEAN_ANOMALY": "deg",
    "BSTAR": "1/ER",
    "MEAN_MOTION_DOT": "rev/day**2",
    "MEAN_MOTION_DDOT": "rev/day**3",
}


@dataclass
class OrbitInput:
    format: str
    oem: str | None = None
    records: list | None = None
    warnings: list | None = None


def scalar(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} needs a finite number.") from None
    if not isfinite(result):
        raise ValueError(f"{name} needs a finite number.")
    return result


def tabular(text: str, delimiter: str = ",") -> tuple[list[str], list[dict]]:
    if delimiter not in {",", ";", "\t"}:
        raise ValueError("Choose comma, semicolon or tab as the delimiter.")
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    columns = reader.fieldnames or []
    if not columns or len(columns) > 100 or len(set(columns)) != len(columns):
        raise ValueError("A table needs 1–100 unique column headings.")
    rows = []
    for row in reader:
        if len(rows) >= 100000:
            raise ValueError("Use at most 100,000 table rows.")
        if None in row or any(v is None for v in row.values()):
            raise ValueError("A table row has a different number of cells from its headings.")
        rows.append(row)
    if not rows:
        raise ValueError("The table contains no data rows.")
    return columns, rows


def xml_root(text):
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("XML DTDs and entities are not accepted.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed XML: {exc}") from None
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    return root


def leaves(element):
    values = {}
    for e in element.iter():
        if len(e) or e.tag in {"COMMENT", "comment"}:
            continue
        if e.tag in values:
            raise ValueError(f"Duplicate {e.tag} in a message block.")
        unit = e.attrib.get("units")
        if unit and e.tag in UNITS and unit != UNITS[e.tag]:
            raise ValueError(f"{e.tag} declares {unit}; the supported message unit is {UNITS[e.tag]}.")
        values[e.tag] = (e.text or "").strip()
    return values


def oem_xml(root):
    messages = list(root.iter("oem"))
    if len(messages) != 1:
        raise ValueError("Upload one OEM message at a time.")
    lines = ["CCSDS_OEM_VERS = 2.0"]
    header = messages[0].find("header")
    if header is not None:
        for key, value in leaves(header).items():
            if key in {"CREATION_DATE", "ORIGINATOR"}:
                if "\n" in value or "\r" in value:
                    raise ValueError("OEM header values must occupy one line.")
                lines.append(f"{key} = {value}")
    segments = list(messages[0].iter("segment"))
    if not segments:
        raise ValueError("OEM XML has no segments.")
    for segment in segments:
        meta = segment.find("metadata")
        if meta is None:
            raise ValueError("Each OEM segment needs metadata.")
        values = leaves(meta)
        if any("\n" in value or "\r" in value for value in values.values()):
            raise ValueError("OEM metadata values must occupy one line.")
        lines.extend(["META_START", *(f"{k} = {v}" for k, v in values.items()), "META_STOP"])
        vectors = list(segment.iter("stateVector"))
        for vector in vectors:
            v = leaves(vector)
            if not all(k in v for k in STATE_KEYS):
                raise ValueError("OEM stateVector needs EPOCH, X/Y/Z and X_DOT/Y_DOT/Z_DOT.")
            lines.append(" ".join(v[k] for k in STATE_KEYS))
    return "\n".join(lines)


def validate_records(records, standard):
    if not isinstance(records, list) or not 1 <= len(records) <= 10000:
        raise ValueError("Supply 1–10,000 OMM records.")
    defaults_used = set()
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Each OMM record must be an object.")
        for key, expected in CONVENTIONS.items():
            if not row.get(key) and not standard:
                defaults_used.add(key)
                row[key] = expected
            if str(row.get(key, "")).upper() != expected:
                raise ValueError(f"OMM {key} must be {expected}; this engine supports Earth SGP4 fits only.")
        for key in (
            "NORAD_CAT_ID",
            "EPOCH",
            "MEAN_MOTION",
            "ECCENTRICITY",
            "INCLINATION",
            "RA_OF_ASC_NODE",
            "ARG_OF_PERICENTER",
            "MEAN_ANOMALY",
            "BSTAR",
        ):
            if key not in row or row[key] in (None, ""):
                raise ValueError(f"OMM is missing {key}.")
        n = scalar(row["NORAD_CAT_ID"], "NORAD_CAT_ID")
        if not n.is_integer() or not 1 <= n <= 999999999:
            raise ValueError("NORAD_CAT_ID must be an integer from 1 to 999999999.")
        row["NORAD_CAT_ID"] = int(n)
        epoch = pd.Timestamp(row["EPOCH"])
        if pd.isna(epoch):
            raise ValueError("OMM EPOCH is not a valid time.")
        epoch = epoch.tz_localize("UTC") if epoch.tzinfo is None else epoch.tz_convert("UTC")
        key = (int(n), epoch.isoformat())
        if key in seen:
            raise ValueError("Duplicate catalogue number and epoch. Resolve the orbit version explicitly.")
        seen.add(key)
        for name in UNITS:
            if name in row and row[name] not in (None, ""):
                row[name] = scalar(row[name], name)
        if not 0 < row["MEAN_MOTION"] <= 30 or not 0 <= row["ECCENTRICITY"] < 1 or not 0 <= row["INCLINATION"] <= 180:
            raise ValueError("OMM mean motion, eccentricity or inclination is outside the supported physical range.")
        for name in ("RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY"):
            if not 0 <= row[name] <= 360:
                raise ValueError(f"{name} must be in degrees between 0 and 360.")
        if scalar(row.get("EPHEMERIS_TYPE", 0) or 0, "EPHEMERIS_TYPE") != 0:
            raise ValueError("Only conventional SGP4 EPHEMERIS_TYPE 0 is supported.")
        for name, default in {
            "OBJECT_NAME": "",
            "OBJECT_ID": "",
            "MEAN_MOTION_DOT": 0,
            "MEAN_MOTION_DDOT": 0,
            "EPHEMERIS_TYPE": 0,
            "CLASSIFICATION_TYPE": "U",
            "ELEMENT_SET_NO": 0,
            "REV_AT_EPOCH": 0,
        }.items():
            if row.get(name) in (None, ""):
                row[name] = default
    return (
        ["GP export defaults applied: " + ", ".join(f"{k}={CONVENTIONS[k]}" for k in sorted(defaults_used))]
        if defaults_used
        else []
    )


def mapped_states(text, options):
    columns, rows = tabular(text, options.get("delimiter", ","))
    mapping = options.get("columns", {})
    selected = [mapping.get(k) for k in STATE_KEYS]
    if any(c not in columns for c in selected) or len(set(selected)) != 7:
        raise ValueError("Map seven distinct columns: time, X/Y/Z and VX/VY/VZ.")
    frame, clock = options.get("frame"), options.get("time_system")
    identity = str(options.get("object_id", "")).strip()
    if frame not in {"TEME", "J2000", "ITRF"} or clock not in {"UTC", "GPS", "TAI"}:
        raise ValueError("Mapped states require an explicit supported frame and time system.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", identity):
        raise ValueError("Supply one OBJECT_ID (letters, digits, dot, underscore or hyphen).")
    punit, vunit = options.get("position_unit"), options.get("velocity_unit")
    if punit not in {"km", "m"} or vunit not in {"km/s", "m/s"}:
        raise ValueError("Choose explicit position and velocity units.")
    lines = [
        "CCSDS_OEM_VERS = 2.0",
        "META_START",
        f"OBJECT_ID = {identity}",
        "CENTER_NAME = EARTH",
        f"REF_FRAME = {frame}",
        f"TIME_SYSTEM = {clock}",
        "META_STOP",
    ]
    for row in rows:
        time = str(row[selected[0]]).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", time):
            raise ValueError("State times must be ISO 8601 YYYY-MM-DDTHH:MM:SS[.fraction], optionally Z for UTC.")
        if time.endswith("Z") and clock != "UTC":
            raise ValueError("Z means UTC; remove it for a declared GPS or TAI clock.")
        numbers = [
            scalar(row[c], c) * (0.001 if (punit == "m" if i < 3 else vunit == "m/s") else 1)
            for i, c in enumerate(selected[1:])
        ]
        lines.append(time + " " + " ".join(format(n, ".16g") for n in numbers))
    return "\n".join(lines)


def validate_oem_lines(text: str) -> None:
    in_meta = False
    in_data = False
    in_covariance = False
    keys = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("COMMENT"):
            continue
        if line == "META_START":
            in_meta, in_data, keys = True, False, set()
        elif line == "META_STOP":
            in_meta, in_data = False, True
        elif line == "COVARIANCE_START":
            in_covariance = True
        elif line == "COVARIANCE_STOP":
            in_covariance = False
        elif in_meta:
            if "=" not in line:
                raise ValueError("Malformed OEM metadata line.")
            key = line.split("=", 1)[0].strip()
            if key in keys:
                raise ValueError(f"Duplicate OEM metadata field {key}.")
            keys.add(key)
        elif in_data and not in_covariance:
            parts = line.split()
            if len(parts) not in {7, 10}:
                raise ValueError("OEM state rows need a time and six state values (plus three optional accelerations).")
            for number in parts[1:]:
                scalar(number, "OEM state")
    if in_meta or in_covariance:
        raise ValueError("OEM metadata or covariance block is not closed.")


def decode_orbit(text: str, options: dict | None = None) -> OrbitInput:
    text = text.lstrip("\ufeff").strip()
    options = options or {}
    if not isinstance(options, dict):
        raise ValueError("Import options must be an object.")
    if options.get("format") == "state-csv":
        return OrbitInput(
            "Mapped state table",
            oem=mapped_states(text, options),
            warnings=["Frame, clock, units and identity are user declarations. CSV is not a CCSDS encoding."],
        )
    records = None
    standard = False
    if text.startswith("<"):
        root = xml_root(text)
        if list(root.iter("oem")):
            if any(list(root.iter(kind)) for kind in ("omm", "opm", "ocm")):
                raise ValueError("Split mixed navigation-message containers into separate orbit files.")
            return OrbitInput("OEM XML", oem=oem_xml(root), warnings=[])
        messages = list(root.iter("omm"))
        if not messages:
            raise ValueError("Expected OEM or OMM XML. CDMs belong in the conjunction-message tool.")
        records = [leaves(message) for message in messages]
        format_name, standard = "OMM XML", True
    elif re.search(r"(?m)^CCSDS_OEM_VERS\s*=", text):
        validate_oem_lines(text)
        return OrbitInput("OEM KVN", oem=text, warnings=[])
    elif re.search(r"(?m)^CCSDS_OMM_VERS\s*=", text):
        records = []
        for block in re.split(r"(?m)^CCSDS_OMM_VERS\s*=.*$", text)[1:]:
            row = {}
            for line in block.splitlines():
                if "=" not in line or line.strip().startswith("COMMENT"):
                    continue
                key, value = (s.strip() for s in line.split("=", 1))
                unit = re.search(r"\s*\[([^]]+)\]\s*$", value)
                if unit:
                    if key in UNITS and unit[1] != UNITS[key]:
                        raise ValueError(f"{key} has unsupported units {unit[1]}.")
                    value = value[: unit.start()].strip()
                if key in row:
                    raise ValueError(f"Duplicate OMM field {key}.")
                row[key] = value
            records.append(row)
        format_name, standard = "OMM KVN", True
    elif text.startswith(("[", "{")):
        records = json.loads(text)
        if isinstance(records, dict):
            records = [records]
        format_name = "GP JSON (OMM keywords)"
    elif re.search(r"(?m)^1 .{60,}$", text):
        lines = text.splitlines()
        records = []
        label = ""
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line.startswith("1 "):
                if line.startswith("2 "):
                    raise ValueError("TLE line 2 has no preceding line 1.")
                label = line.removeprefix("0 ").strip()
                i += 1
                continue
            if i + 1 >= len(lines):
                raise ValueError("TLE line 1 needs its matching line 2.")
            second = lines[i + 1].rstrip()
            if (
                len(line) != 69
                or len(second) != 69
                or not second.startswith("2 ")
                or line[2:7] != second[2:7]
                or not line[-1].isdigit()
                or not second[-1].isdigit()
            ):
                raise ValueError("TLEs require matching, 69-character lines with checksums.")
            verify_checksum(line, second)
            validate_tle(line, second, wgs72)
            sat = Satrec.twoline2rv(line, second)
            missing_identity = not sat.intldesg.strip()
            if missing_identity:
                sat.intldesg = "00000A"  # exporter requires a designator; do not report this placeholder.
            record = export_omm(sat, label)
            if missing_identity:
                record["OBJECT_ID"] = ""
            records.append(record)
            i += 2
            label = ""
        format_name = "TLE / 3LE (legacy)"
    else:
        columns, records = tabular(text, options.get("delimiter", ","))
        if "MEAN_MOTION" not in columns or "NORAD_CAT_ID" not in columns:
            raise ValueError(
                "Unrecognised orbit table. Choose Custom state CSV and map its columns, frame, clock and units."
            )
        format_name = "GP CSV (OMM keywords)"
    warnings = validate_records(records, standard)
    if format_name.startswith("TLE"):
        warnings.append("Legacy TLE identity range is limited. Prefer OMM for modern catalogue numbers.")
    return OrbitInput(format_name, records=records, warnings=warnings)
