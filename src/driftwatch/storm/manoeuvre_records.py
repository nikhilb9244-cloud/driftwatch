"""Published manoeuvre histories used independently of orbit-step detection.

The IDS chronology is a published event registry, not a completeness guarantee.
Within its dated, mission-specific span the listed events are the exclusion
authority, including a genuinely empty list. An unavailable, unparseable or
out-of-range source is explicitly non-authoritative, never an empty no-burn
record. Sentinel-3 uses the mission's more precise SentiWiki history instead.

Raw snapshots are immutable and content-addressed. Their metadata retains URL,
retrieval time, SHA256 and source time system. No orbit or element-set residual
is read by this module. IDS SSALTO manoeuvre times are TAI; Sentinel-3 NAPEOS
history times are UTC. Neither is an element-set publication timestamp.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import pandas as pd
from astropy.time import Time

from driftwatch import config
from driftwatch.storm.precise import ThrusterRecord

IDS_URL = "https://ids-doris.org/user-corner/table-of-all-events.html"
SENTINEL3_INDEX_URL = "https://sentiwiki.copernicus.eu/web/altimetry-processing"
IDS_SOURCE_ID = "ids-ssalto-record"
SENTINEL3_SOURCE_ID = "sentiwiki-sentinel3-record"
PARSER_VERSION = 1
MISSION_ALIASES = {
    "CRYOSAT-2": "cryosat-2",
    "SARAL": "saral",
    "SENTINEL-3A": "sentinel-3a",
    "SENTINEL-3B": "sentinel-3b",
    "SWOT": "swot",
    "HY-2C": "hy-2c",
    "HY-2D": "hy-2d",
    "JASON-3": "jason-3",
    "SENTINEL-6A": "sentinel-6a",
}
SENTINEL3_IDS = {"sentinel-3a": 268, "sentinel-3b": 269}
SOURCE_SPECS = {
    "ids-ssalto": (".html", "TAI"),
    "sentiwiki-index": (".html", "not applicable"),
    "sentiwiki-s3a": (".man", "UTC"),
    "sentiwiki-s3b": (".man", "UTC"),
}


@dataclass
class PublishedManoeuvreRecord(ThrusterRecord):
    """A ThrusterRecord with explicit source availability and coverage semantics.

    ``authoritative`` means the chosen published list governs exclusions. It does
    not claim that an event registry proves every firing has been reported.
    Callers must stop or mark affected trials unavailable when this is false.
    """

    source_id: str = ""
    coverage_status: str = "unavailable"
    coverage_start: str | None = None
    coverage_end: str | None = None
    provenance: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def authoritative(self) -> bool:
        return self.coverage_status in ("published_event_registry", "published_history") and not self.days_missing

    def as_metadata(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "authoritative": self.authoritative,
            "coverage_status": self.coverage_status,
            "coverage_start": self.coverage_start,
            "coverage_end": self.coverage_end,
            "provenance": self.provenance,
            "issues": self.issues,
            "parser_version": PARSER_VERSION,
            "interval_time_system": "UTC",
        }


@dataclass
class ParsedHistory:
    intervals: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = field(default_factory=dict)
    bounds: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = field(default_factory=dict)
    # Date hints allow a malformed historic row to invalidate its own span
    # without silently discarding it or invalidating unrelated years.
    issues: list[tuple[str, date | None, str]] = field(default_factory=list)


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def _utc(value: str, scale: str) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if scale == "UTC":
        return stamp
    return pd.Timestamp(Time(stamp.to_datetime64(), format="datetime64", scale=scale.lower()).utc.datetime64)


def _date_hint(value: str) -> date | None:
    try:
        return pd.Timestamp(value[:10]).date()
    except ValueError:
        return None


def parse_ids_events(text: str) -> ParsedHistory:
    """Read SSALTO onboard manoeuvres; retain malformed relevant rows as issues.

    Bounds use dated SSALTO system entries for each mission, independently of
    whether an entry is a manoeuvre. Known empty mission intervals consequently
    remain distinct from an absent mission or a missing catalogue.
    """
    parser = _TableParser()
    parser.feed(text)
    result = ParsedHistory()
    dated: dict[str, list[pd.Timestamp]] = {}
    for number, row in enumerate(parser.rows, 1):
        if len(row) != 5 or row[1].lower() != "system" or row[4].upper() != "SSALTO":
            continue
        mission = MISSION_ALIASES.get(row[2].upper())
        if mission is None:
            continue
        description = row[3]
        manoeuvre = bool(re.search(r"man(?:eu|oeu)ver|manoeuvre", description, re.IGNORECASE))
        try:
            # One historic attitude-slew entry explicitly supplies UTC start
            # and end times. Do not interpret those as TAI merely by source.
            utc_slew = re.search(
                r"on (\d{2}/\d{2}/\d{4}) from (\d{2}:\d{2}:\d{2}) UTC to (\d{2}:\d{2}:\d{2}) UTC",
                description,
            )
            if utc_slew:
                day = pd.to_datetime(utc_slew[1], format="%d/%m/%Y").strftime("%Y-%m-%d")
                start = _utc(f"{day} {utc_slew[2]}", "UTC")
                end = _utc(f"{day} {utc_slew[3]}", "UTC")
            else:
                start = _utc(row[0], "TAI")
                end_match = re.search(
                    r"end\s*:\s*(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+TAI",
                    description,
                    re.IGNORECASE,
                )
                if manoeuvre and end_match is None:
                    raise ValueError("manoeuvre has no valid, explicitly TAI end timestamp")
                end = _utc(end_match[1], "TAI") if end_match else start
            dated.setdefault(mission, []).append(start)
            if manoeuvre:
                if end < start:
                    raise ValueError("manoeuvre ends before it starts")
                result.intervals.setdefault(mission, []).append((start, end))
        except (ValueError, TypeError) as exc:
            result.issues.append((mission, _date_hint(row[0]), f"IDS row {number}: {exc}; {' | '.join(row)}"))
    for mission, times in dated.items():
        result.bounds[mission] = (min(times), max(times))
        result.intervals[mission] = sorted(set(result.intervals.get(mission, [])))
    if not result.bounds:
        raise ValueError("no dated SSALTO entries for benchmark missions; not a valid IDS catalogue")
    return result


def parse_sentinel3_history(text: str, mission: str) -> ParsedHistory:
    """Parse the NAPEOS UTC start/end pairs; check satellite identity and pairing.

    The first line is update epoch and ESOC spacecraft ID, not a record count.
    Coverage ends at that update epoch; subsequent planned entries cannot turn
    a request for newer realised manoeuvres into a complete historical record.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if mission not in SENTINEL3_IDS or not lines:
        raise ValueError("missing Sentinel-3 history or unknown spacecraft")
    header = lines[0].split()
    if len(header) != 2 or int(header[1]) != SENTINEL3_IDS[mission]:
        raise ValueError("Sentinel-3 history header has the wrong spacecraft ID")
    updated = pd.to_datetime(header[0], format="%Y/%m/%d-%H:%M:%S.%f")
    result = ParsedHistory(intervals={mission: []})
    opened: pd.Timestamp | None = None
    times: list[pd.Timestamp] = []
    for number, line in enumerate(lines[1:], 2):
        try:
            when = pd.to_datetime(line[:23], format="%Y/%m/%d-%H:%M:%S.%f")
            body = line[23:]
            # Adjacent signed Fortran D exponents need no intervening space.
            fields = re.findall(r"[+-]?\d+\.\d+[DdEe][+-]\d+", body)
            if len(fields) != 3:
                raise ValueError("expected three acceleration components")
            flag = int(body.split()[-1])
            if times and when < times[-1]:
                raise ValueError("history records are not in timestamp order")
            times.append(when)
            if flag > 0:
                if opened is not None:
                    raise ValueError("start without an intervening end")
                opened = when
            elif flag == 0:
                if opened is None or when < opened:
                    raise ValueError("end without a valid preceding start")
                result.intervals[mission].append((opened, when))
                opened = None
            else:
                raise ValueError("negative start/end flag")
        except (ValueError, TypeError) as exc:
            result.issues.append((mission, _date_hint(line), f"history line {number}: {exc}; {line}"))
    if opened is not None:
        result.issues.append((mission, opened.date(), "history has an unclosed manoeuvre start"))
    if not times:
        raise ValueError("Sentinel-3 history contains no dated manoeuvre rows")
    result.bounds[mission] = (min(times), updated)
    return result


def cache_snapshot(
    source: str,
    payload: bytes,
    url: str,
    *,
    cache_dir: Path = config.CACHE_DIR,
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    """Cache a downloaded raw source, also usable for importing an audited snapshot."""
    suffix, time_system = SOURCE_SPECS[source]
    folder = cache_dir / "manoeuvre-records"
    folder.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(payload).hexdigest()
    raw = folder / f"{source}-{sha}{suffix}"
    if not raw.exists():
        raw.write_bytes(payload)
    metadata = {
        "source": source,
        "url": url,
        "retrieved_at": (retrieved_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        "sha256": sha,
        "bytes": len(payload),
        "raw_path": str(raw.resolve()),
        "raw_file": raw.name,
        "source_time_system": time_system,
    }
    pointer = folder / f"{source}.json"
    temporary = pointer.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    temporary.replace(pointer)
    return metadata


def _cached(source: str, cache_dir: Path) -> tuple[str, dict[str, Any]]:
    folder = cache_dir / "manoeuvre-records"
    metadata = json.loads((folder / f"{source}.json").read_text(encoding="utf-8"))
    # Use a basename below this cache, never an arbitrary absolute path from JSON.
    name = metadata["raw_file"]
    if Path(name).name != name:
        raise ValueError("invalid raw snapshot filename")
    raw = folder / name
    payload = raw.read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
        raise ValueError(f"cached {source} snapshot failed SHA256 verification")
    if metadata.get("source") != source or metadata.get("source_time_system") != SOURCE_SPECS[source][1]:
        raise ValueError("snapshot source identity or time system differs from its parser")
    metadata["raw_path"] = str(raw.resolve())
    return payload.decode("utf-8-sig"), metadata


def _source(
    source: str, url: str | None, cache_dir: Path, offline: bool, client: httpx.Client, refresh: bool
) -> tuple[str, dict[str, Any]]:
    if not refresh or offline:
        try:
            return _cached(source, cache_dir)
        except (OSError, ValueError, KeyError) as exc:
            if offline:
                raise ValueError(f"{source} unavailable offline: {exc}") from exc
    if url is None:
        raise ValueError(f"no published URL resolved for {source}")
    response = client.get(url)
    response.raise_for_status()
    metadata = cache_snapshot(source, response.content, str(response.url), cache_dir=cache_dir)
    return response.content.decode("utf-8-sig"), metadata


class _HistoryLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.label: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.label = []

    def handle_data(self, data: str) -> None:
        if self.href:
            self.label.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href:
            self.links.append((" ".join("".join(self.label).split()), self.href))
            self.href = None


def sentinel3_history_url(text: str, mission: str) -> str:
    parser = _HistoryLinks()
    parser.feed(text)
    wanted = f"{mission} Manoeuvre History file".lower()
    for label, href in parser.links:
        if label.lower() == wanted:
            return urljoin(SENTINEL3_INDEX_URL, href)
    raise ValueError(f"SentiWiki page has no manoeuvre-history link for {mission}")


def load_record(
    mission: str,
    norad_id: int,
    start: date,
    end: date,
    *,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
    refresh: bool = False,
) -> PublishedManoeuvreRecord:
    """Load the chosen published authority, retaining missing coverage explicitly."""
    if mission not in MISSION_ALIASES.values():
        raise ValueError(f"no published manoeuvre source configured for {mission}")
    if end < start:
        raise ValueError("record end precedes start")
    days = [start + timedelta(days=k) for k in range((end - start).days + 1)]
    source_id = SENTINEL3_SOURCE_ID if mission in SENTINEL3_IDS else IDS_SOURCE_ID
    record = PublishedManoeuvreRecord(mission, norad_id, [], days, [], 0, 0.0, source_id=source_id)
    own_client = client is None
    c = client or httpx.Client(follow_redirects=True, timeout=60.0)
    try:
        if mission in SENTINEL3_IDS:
            source = f"sentiwiki-s3{mission[-1]}"
            try:
                text, metadata = _cached(source, cache_dir) if not refresh or offline else (None, None)
            except (OSError, ValueError, KeyError):
                text, metadata = None, None
            if text is None:
                page, page_meta = _source("sentiwiki-index", SENTINEL3_INDEX_URL, cache_dir, offline, c, refresh)
                record.provenance.append(page_meta)
                url = sentinel3_history_url(page, mission)
                text, metadata = _source(source, url, cache_dir, offline, c, refresh)
            record.provenance.append(metadata)
            parsed = parse_sentinel3_history(text, mission)
            status = "published_history"
        else:
            text, metadata = _source("ids-ssalto", IDS_URL, cache_dir, offline, c, refresh)
            record.provenance.append(metadata)
            parsed = parse_ids_events(text)
            status = "published_event_registry"
            record.issues.append(
                "The IDS chronology lists published SSALTO events; its temporal span is known, "
                "but exhaustive reporting of every firing is not independently established."
            )
        record.files = [p["raw_path"] for p in record.provenance]
        if mission not in parsed.bounds:
            raise ValueError(f"source contains no dated entries for {mission}")
        lo, hi = parsed.bounds[mission]
        record.coverage_start, record.coverage_end = lo.isoformat(), hi.isoformat()
        record.days_missing = [
            day for day in days if pd.Timestamp(day) < lo or pd.Timestamp(day) + pd.Timedelta(days=1) > hi
        ]
        relevant_issues = [
            message
            for key, day, message in parsed.issues
            if key == mission and (mission in SENTINEL3_IDS or day is None or start <= day <= end)
        ]
        record.issues.extend(relevant_issues)
        query_start, query_end = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
        record.intervals = [(a, b) for a, b in parsed.intervals.get(mission, []) if a < query_end and b >= query_start]
        record.orbit_thrust_s = float(sum((b - a).total_seconds() for a, b in record.intervals))
        if relevant_issues:
            record.coverage_status = "malformed_records"
            record.days_missing = days
        elif record.days_missing:
            record.coverage_status = "out_of_range"
            record.issues.append("Requested dates extend outside the published source's dated span.")
        else:
            record.coverage_status = status
    except (OSError, ValueError, KeyError, httpx.HTTPError) as exc:
        record.coverage_status = "unavailable"
        record.days_missing = days
        record.issues.append(str(exc))
    finally:
        if own_client:
            c.close()
    return record
