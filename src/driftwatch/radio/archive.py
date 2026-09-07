"""The SARAO archive's documented API, used for observation metadata and for nothing else.

The route, as the archive documents it (archive.sarao.ac.za/help, read September 2026). "You can
interact with the MeerKAT Archive programmatically using our GraphQL API. Visit /graphql in your
browser to explore the schema and run queries interactively using the built-in GraphQL
Playground." The interface's own metadata download is that API: selecting rows and clicking
"DOWNLOAD METADATA" hands out ``export_meerkat_archive.py``, a published script that pages the
``observations`` query 25 records at a time and is offered as "a reference implementation to
extend for specific use cases". Authentication is "script-based authentication through the OAuth2
PKCE flow": a browser login (``login.py``) that issues an access token and a refresh token, and
"Refresh tokens are valid for 30 days, and are rotated on successful logins". "Public datasets are
available to all logged-in users." The page also says "This API is experimental and may be subject
to change."

What this module does with that. It reads one token from the environment, ``SARAO_ARCHIVE_TOKEN``
(a refresh token from the archive's login step, exchanged here for an access token, or an access
token used as it is), keeps it in memory, and never writes it to disk, to a log or to the cache;
its ``repr`` is masked. There is no documented password grant, so a username and password in the
environment are not used: the archive's login is a browser step, and the token it issues is what
the environment carries. Every request carries a descriptive User-Agent, requests are at least
``MIN_INTERVAL_S`` apart, pages are the published script's 25 records, and the query asks only for
observation metadata -- capture block, proposal, start, duration, band, frequency range, targets,
pointings and the public flag -- never a product, an RDB link or a data token. A record is kept only
when the archive marks it ``Public`` and its start is more than ``PROPRIETARY_MONTHS`` months
before the export; everything else is excluded and counted.

The terms of use of the archive site (archive.sarao.ac.za/terms-of-use) grant permission "to
display, copy, distribute, and download the materials on this website for personal, non-commercial
use only, provided you do not modify the materials and that you retain all copyright and other
proprietary notices contained in the materials". The export therefore carries the archive's own
identifiers and a ``source`` column naming the record, and the observation list is a derived
metadata table, not a copy of any data product. Publications using MeerKAT data carry the
acknowledgement statement the archive asks for; a crossing list is not such a publication, and the
statement is recorded in ``docs/radio-lane.md`` beside the route in case one follows.
"""

from __future__ import annotations

import csv
import logging
import os
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from driftwatch import config
from driftwatch.radio.observations import parse_angle
from driftwatch.radio.site import RECEIVERS

log = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive.sarao.ac.za"
GRAPHQL_PATH = "/graphql"
REFRESH_PATH = "/_auth/pkce-cli-refresh"
HELP_URL = f"{ARCHIVE_URL}/help"
TERMS_URL = f"{ARCHIVE_URL}/terms-of-use"
TOKEN_ENV = "SARAO_ARCHIVE_TOKEN"
USER_ENV = "SARAO_ARCHIVE_USER"
PASS_ENV = "SARAO_ARCHIVE_PASS"
# The published script's page size, and a floor between requests it does not set; the help page
# states no rate limit, so this is the polite default rather than a documented one.
PAGE_SIZE = 25
MIN_INTERVAL_S = 2.0
# "Open Time proposals typically have a proprietary period of 12 months after the last observation
# has been obtained" (the help page); the archive's own Public flag decides, this is the second check.
PROPRIETARY_MONTHS = 12
USER_AGENT = config.USER_AGENT.rstrip(")") + "; MeerKAT archive observation metadata, read-only, paced)"

ROUTE = (
    "The archive documents a GraphQL API (archive.sarao.ac.za/graphql) with a published export script that "
    "pages the observations query 25 records at a time, authenticated by an OAuth2 PKCE browser login that "
    "issues an access token and a 30-day refresh token; public datasets are available to logged-in users. "
    "This export uses that API with the token from the environment, asks for observation metadata only, and "
    "keeps a record only when the archive marks it public and its start is past the proprietary period."
)

# The fields asked for, every one an observation's metadata (from the Observation type of the
# schema the API publishes). Nothing here is a product, a link or a token.
OBSERVATION_FIELDS: tuple[str, ...] = (
    "id",
    "CaptureBlockId",
    "ProposalId",
    "StartTime",
    "Duration",
    "band",
    "MinFreq",
    "MaxFreq",
    "Targets",
    "TargetsString",
    "KatpointTargets",
    "DecRa",
    "IntegrationTime",
    "Public",
    "Description",
    "Observer",
    "NumFreqChannels",
    "ProductTypeName",
    "Instrument",
)

QUERY = (
    "query ($limit: Int, $cursor: String, $search: String, $filters: [SolrFilterInput!]) {\n"
    "  observations(limit: $limit, cursor: $cursor, search: $search, filters: $filters) {\n"
    "    pageInfo { totalCount endCursor hasNextPage }\n"
    "    records { " + " ".join(OBSERVATION_FIELDS) + " }\n"
    "  }\n"
    "}"
)


class ArchiveError(Exception):
    """The archive refused or could not be reached."""


class ArchiveAuthError(ArchiveError):
    """No usable token, or the archive rejected the one it was given."""


@dataclass(frozen=True, repr=False)
class Token:
    """One archive token. ``repr`` and ``str`` mask it so it never lands in a log or a traceback."""

    value: str

    def __repr__(self) -> str:
        return "Token(***)"

    __str__ = __repr__


def token_from_env(environ: Mapping[str, str] = os.environ) -> Token:
    """Read ``SARAO_ARCHIVE_TOKEN``; refuse, naming the variable, when it is unset.

    A username and password (``SARAO_ARCHIVE_USER``, ``SARAO_ARCHIVE_PASS``) are not a route this
    module can use, because the archive's documented login is a browser step; the message says
    so when they are set and the token is not.
    """
    token = environ.get(TOKEN_ENV, "").strip()
    if token:
        return Token(token)
    hint = ""
    if environ.get(USER_ENV) or environ.get(PASS_ENV):
        hint = (
            f" ({USER_ENV}/{PASS_ENV} are set, but the archive documents no password login for scripts: run its "
            "login.py once in a browser and put the refresh token it issues in the environment)"
        )
    raise ArchiveAuthError(
        f"set {TOKEN_ENV} in the environment (a refresh or access token from the archive's login step, never in "
        f"a file in the repository) to read the MeerKAT archive{hint}"
    )


class Throttle:
    """At least ``min_interval_s`` between requests; ``clock`` and ``sleep`` are injectable for tests."""

    def __init__(
        self,
        min_interval_s: float = MIN_INTERVAL_S,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval_s = float(min_interval_s)
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> float:
        """Block until the interval has passed since the last request, record this one, return the seconds slept."""
        now = self._clock()
        slept = 0.0
        if self._last is not None:
            delay = self.min_interval_s - (now - self._last)
            if delay > 0:
                self._sleep(delay)
                slept = delay
                now = self._clock()
        self._last = now
        return slept


def _iso_z(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class ArchiveClient:
    """The documented GraphQL route, paced, with the token held in memory only."""

    def __init__(
        self,
        token: Token,
        *,
        base_url: str = ARCHIVE_URL,
        client: httpx.Client | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=60.0)
        self._throttle = throttle or Throttle()
        self._access = token.value
        self._refresh = token.value
        self.n_requests = 0
        self.refreshed = False
        self.rotated_refresh_token: Token | None = None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ArchiveClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access}",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def refresh(self) -> None:
        """Exchange the refresh token for an access token at the documented refresh endpoint.

        The response may carry a rotated refresh token; it is kept in memory as
        ``rotated_refresh_token`` and nowhere else, so the caller can tell the operator that the
        environment's value has been superseded without this module ever writing it down.
        """
        self._throttle.wait()
        self.n_requests += 1
        r = self._client.post(
            self.base_url + REFRESH_PATH,
            json={"refresh_token": self._refresh},
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        )
        if r.status_code != 200:
            raise ArchiveAuthError(
                f"the archive did not accept the token from {TOKEN_ENV} as a refresh token (HTTP {r.status_code}); "
                "refresh tokens are valid for 30 days from the archive's login step"
            )
        body = r.json()
        access = body.get("access_token")
        if not access:
            raise ArchiveAuthError("the refresh response carried no access token")
        self._access = str(access)
        new_refresh = body.get("refresh_token")
        if new_refresh and new_refresh != self._refresh:
            self.rotated_refresh_token = Token(str(new_refresh))
            self._refresh = str(new_refresh)
        self.refreshed = True
        log.info("Archive: access token obtained from the refresh endpoint")

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """One paced GraphQL request; a 401 on the first try is answered by a refresh and one retry."""
        for attempt in range(2):
            self._throttle.wait()
            self.n_requests += 1
            r = self._client.post(
                self.base_url + GRAPHQL_PATH, json={"query": query, "variables": variables}, headers=self._headers()
            )
            if r.status_code == 401 and attempt == 0 and not self.refreshed:
                log.info("Archive: the token was not accepted as an access token; trying it as a refresh token")
                self.refresh()
                continue
            if r.status_code == 401:
                raise ArchiveAuthError(
                    f"the archive rejected the token (HTTP 401) even after a refresh; check {TOKEN_ENV}"
                )
            if r.status_code != 200:
                raise ArchiveError(f"the archive answered HTTP {r.status_code} to a GraphQL request")
            body = r.json()
            if body.get("errors"):
                messages = "; ".join(str(e.get("message", e)) for e in body["errors"])
                if "unauth" in messages.lower() or "forbidden" in messages.lower() or "login" in messages.lower():
                    if attempt == 0 and not self.refreshed:
                        self.refresh()
                        continue
                    raise ArchiveAuthError(f"the archive refused the query: {messages}")
                raise ArchiveError(f"the archive returned errors: {messages}")
            return body.get("data") or {}
        raise ArchiveError("unreachable")

    def observations(
        self,
        start: datetime,
        end: datetime,
        *,
        search: str = "*",
        page_size: int = PAGE_SIZE,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:
        """Every observation record the archive lists with a start inside ``[start, end)``, paged.

        The filter is the published script's ``dateRange`` on whole days; the records come back
        as the schema's fields and are not interpreted here.
        """
        filters = [{"field": "dateRange", "value": [_iso_z(start), _iso_z(end)]}]
        records: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            limit = page_size if max_records is None else max(1, min(page_size, max_records - len(records)))
            data = self.graphql(QUERY, {"limit": limit, "cursor": cursor, "search": search, "filters": filters})
            page = (data.get("observations") or {}).get("records") or []
            info = (data.get("observations") or {}).get("pageInfo") or {}
            records.extend(page)
            log.info(
                "Archive: %d record(s) on this page, %d so far, %s in total",
                len(page),
                len(records),
                info.get("totalCount", "?"),
            )
            if not page or not info.get("hasNextPage") or (max_records is not None and len(records) >= max_records):
                break
            cursor = info.get("endCursor")
            if not cursor:
                break
        return records


# --------------------------------------------------------------------------------------
# Records to observations


@dataclass(frozen=True)
class ArchivePointing:
    """One pointing of one capture block: what the observation CSV needs, plus what qualifies it."""

    capture_block_id: str
    proposal_id: str
    start: datetime
    duration_s: float
    band: str
    centre_mhz: float | None
    target: str
    ra_deg: float
    dec_deg: float
    integration_s: float | None
    n_targets: int
    public: bool
    description: str
    observer: str

    @property
    def observation_id(self) -> str:
        return f"sarao-{self.capture_block_id}-{_slug(self.target)}"


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9+-]+", "-", text.strip()).strip("-")[:40] or "target"


_SPECIAL_TAGS = ("azel", "gal", "tle", "special", "xephem")


def parse_katpoint_target(text: str) -> tuple[str, float, float] | None:
    """``(name, ra_deg, dec_deg)`` from a katpoint target description, or None when it is not a radec target.

    The description is ``names, tags, longitude, latitude[, flux model]`` with ``|`` between
    alternative names; only targets tagged ``radec`` carry a fixed sky position, so the Sun, an
    azimuth-elevation pointing or a TLE target returns None.
    """
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) < 4:
        return None
    names, tags = parts[0], parts[1].lower().split()
    if "radec" not in tags or any(t in tags for t in _SPECIAL_TAGS):
        return None
    name = names.split("|")[0].strip() or "target"
    ra_text, dec_text = parts[2], parts[3]
    try:
        ra = parse_angle(ra_text, hours=":" in ra_text or "h" in ra_text.lower())
        dec = parse_angle(dec_text, hours=False)
    except ValueError:
        return None
    return name, ra, dec


def parse_decra(text: str) -> tuple[float, float] | None:
    """``(ra_deg, dec_deg)`` from the archive's ``DecRa`` string, declination first, degrees or sexagesimal."""
    pieces = [p for p in re.split(r"[,\s]+", str(text).strip()) if p]
    if len(pieces) != 2:
        return None
    try:
        dec = parse_angle(pieces[0], hours=False)
        ra = parse_angle(pieces[1], hours=":" in pieces[1])
    except ValueError:
        return None
    return ra, dec


def parse_start(value: Any) -> datetime | None:
    """A UTC datetime from the archive's ``StartTime``: ISO 8601 text, or seconds since the Unix epoch."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return datetime.fromtimestamp(float(text), tz=UTC)
    try:
        t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t.astimezone(UTC)


def freq_mhz(value: Any) -> float | None:
    """A frequency in MHz from a number that may be in Hz (the archive's convention) or MHz."""
    if value is None or value == "":
        return None
    f = float(value)
    return f / 1e6 if f > 1e5 else f


def receiver_for(band: Any, lo_mhz: float | None, hi_mhz: float | None) -> str | None:
    """The receiver name the observation CSV uses, from the archive's band label or its frequency range."""
    label = str(band or "").strip().upper().replace("-BAND", "").replace(" BAND", "").replace("BAND", "").strip()
    if label in RECEIVERS:
        return label
    if label == "S":
        label = ""
    if lo_mhz is not None and hi_mhz is not None:
        centre = 0.5 * (lo_mhz + hi_mhz)
        best = None
        for name, rx in RECEIVERS.items():
            if rx.lo_mhz - 5.0 <= lo_mhz and hi_mhz <= rx.hi_mhz + 5.0:
                score = abs(centre - rx.centre_mhz)
                if best is None or score < best[0]:
                    best = (score, name)
        if best is not None:
            return best[1]
    return None


def is_past_proprietary(start: datetime, public: bool | None, *, today: datetime) -> tuple[bool, str]:
    """Both checks: the archive's own Public flag, and a start more than the proprietary period before today."""
    if public is not True:
        return False, "not marked public by the archive" if public is False else "public status not stated"
    if start > today - timedelta(days=int(PROPRIETARY_MONTHS * 30.44)):
        return False, f"started within the last {PROPRIETARY_MONTHS} months"
    return True, "public, and past the proprietary period"


def pointings_from_record(record: Mapping[str, Any]) -> tuple[list[ArchivePointing], str | None]:
    """The pointings one record carries, and the reason when it carries none usable."""
    start = parse_start(record.get("StartTime"))
    if start is None:
        return [], "no start time"
    duration = record.get("Duration")
    if duration is None or duration == "":
        return [], "no duration"
    duration_s = float(duration)
    lo, hi = freq_mhz(record.get("MinFreq")), freq_mhz(record.get("MaxFreq"))
    band = receiver_for(record.get("band"), lo, hi)
    if band is None:
        return [], f"band {record.get('band')!r} with {lo}-{hi} MHz matches no receiver"
    centre = 0.5 * (lo + hi) if lo is not None and hi is not None else None
    public = record.get("Public")
    katpoint = record.get("KatpointTargets") or []
    names = record.get("Targets") or []
    integration = record.get("IntegrationTime") or []
    decra = record.get("DecRa") or []
    targets: list[tuple[str, float, float, float | None]] = []
    if katpoint:
        for k, text in enumerate(katpoint):
            parsed = parse_katpoint_target(text)
            if parsed is None:
                continue
            name, ra, dec = parsed
            secs = float(integration[k]) if k < len(integration) and integration[k] is not None else None
            targets.append((name, ra, dec, secs))
    elif decra:
        for k, text in enumerate(decra):
            parsed = parse_decra(text)
            if parsed is None:
                continue
            ra, dec = parsed
            name = str(names[k]) if k < len(names) else f"target {k + 1}"
            secs = float(integration[k]) if k < len(integration) and integration[k] is not None else None
            targets.append((name, ra, dec, secs))
    if not targets:
        return [], "no target with a sky position"
    out = [
        ArchivePointing(
            capture_block_id=str(record.get("CaptureBlockId") or record.get("id") or ""),
            proposal_id=str(record.get("ProposalId") or ""),
            start=start,
            duration_s=duration_s,
            band=band,
            centre_mhz=centre,
            target=name,
            ra_deg=ra,
            dec_deg=dec,
            integration_s=secs,
            n_targets=len(targets),
            public=bool(public) if public is not None else False,
            description=str(record.get("Description") or ""),
            observer=str(record.get("Observer") or ""),
        )
        for name, ra, dec, secs in targets
    ]
    return out, None


@dataclass
class Export:
    pointings: list[ArchivePointing]
    n_records: int
    excluded: dict[str, int]
    exported_at: datetime


def select_pointings(
    records: Iterable[Mapping[str, Any]],
    *,
    bands: Iterable[str] = ("UHF", "L"),
    today: datetime | None = None,
    first_day: datetime | None = None,
    last_day: datetime | None = None,
) -> Export:
    """Keep the pointings of records in the wanted bands that are public and past the proprietary period.

    ``first_day`` and ``last_day`` (UTC midnights, the end exclusive) bound the start time as a
    second check on the server-side date filter; a record outside them is counted, not kept.
    """
    today = today or datetime.now(UTC)
    wanted = {b.strip().upper() for b in bands}
    kept: list[ArchivePointing] = []
    excluded: dict[str, int] = {}
    n = 0
    for record in records:
        n += 1
        pointings, reason = pointings_from_record(record)
        if reason is not None:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        first = pointings[0]
        if first.band not in wanted:
            key = f"band {first.band} not asked for"
            excluded[key] = excluded.get(key, 0) + 1
            continue
        if (first_day is not None and first.start < first_day) or (last_day is not None and first.start >= last_day):
            excluded["start outside the period"] = excluded.get("start outside the period", 0) + 1
            continue
        ok, why = is_past_proprietary(first.start, record.get("Public"), today=today)
        if not ok:
            excluded[why] = excluded.get(why, 0) + 1
            continue
        kept.extend(pointings)
    kept.sort(key=lambda p: (p.start, p.capture_block_id))  # stable: a block keeps the archive order of its targets
    return Export(kept, n, excluded, today)


CSV_COLUMNS = (
    "observation_id",
    "target",
    "ra",
    "dec",
    "start_utc",
    "duration_s",
    "band",
    "centre_mhz",
    "source",
    "note",
)


# The export directory is outside the repository (``data/archive/`` is ignored): the archive's terms permit
# personal, non-commercial copies and forbid mirroring, so the metadata table stays local and the pages
# cite the archive's identifiers rather than reproduce its records.
EXPORT_DIR = config.DATA_DIR / "archive" / "sarao"


def source_text(p: ArchivePointing, exported_at: datetime) -> str:
    """The citation a page carries for the record: the archive and its identifiers, nothing copied from it."""
    return (
        f"SARAO MeerKAT archive ({ARCHIVE_URL}), capture block {p.capture_block_id}, proposal "
        f"{p.proposal_id or 'not stated'}; metadata read through the archive's documented GraphQL API on "
        f"{exported_at:%Y-%m-%d}; marked public by the archive"
    )


def note_text(p: ArchivePointing) -> str:
    """What the pointing needs said about it; the archive's own descriptive text is not reproduced."""
    secs = "not stated" if p.integration_s is None else f"{p.integration_s:.0f} s"
    return (
        f"Target {p.target}, one of {p.n_targets} with a sky position in this capture block, integration {secs} of "
        f"the block's {p.duration_s:.0f} s; scan boundaries are not in the archive's metadata, so the whole block is "
        "searched and a crossing during another target's scan or a slew is counted with the rest."
    )


def _fmt_time(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_observation_csv(
    export: Export, path: Path, *, keep_other_sources: bool = True, base: Path | None = None
) -> Path:
    """Write the observation CSV: the archive's pointings, and any rows from other sources kept.

    Rows whose ``observation_id`` starts with ``sarao-`` are replaced by this export; rows from other
    sources (a published circular, say) are kept above them, read from ``base`` (the repository's
    public-record CSV) and from ``path`` itself when it already exists.
    """
    path = Path(path)
    kept: list[dict[str, str]] = []
    seen: set[str] = set()
    sources = [p for p in (base, path if keep_other_sources else None) if p is not None and Path(p).exists()]
    for src in sources:
        with Path(src).open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                oid = row.get("observation_id", "")
                if oid.startswith("sarao-") or oid in seen:
                    continue
                if any((v or "").strip() for v in row.values()):
                    seen.add(oid)
                    kept.append({c: row.get(c, "") or "" for c in CSV_COLUMNS})
    rows = [
        {
            "observation_id": p.observation_id,
            "target": p.target,
            "ra": f"{p.ra_deg:.6f}",
            "dec": f"{p.dec_deg:+.6f}",
            "start_utc": _fmt_time(p.start),
            "duration_s": f"{p.duration_s:.0f}",
            "band": p.band,
            "centre_mhz": "" if p.centre_mhz is None else f"{p.centre_mhz:.3f}",
            "source": source_text(p, export.exported_at),
            "note": note_text(p),
        }
        for p in export.pointings
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in kept + rows:
            writer.writerow(row)
    return path


def observation_sources_sentence(export: Export, period_label: str) -> str:
    """The sentence the period report opens its observation section with."""
    blocks = sorted({p.capture_block_id for p in export.pointings})
    excluded = "; ".join(f"{v} {k}" for k, v in sorted(export.excluded.items()))
    return (
        f"Observation records for {period_label}: {len(blocks)} capture block(s) with {len(export.pointings)} "
        f"pointing(s), read from the SARAO MeerKAT archive through its documented GraphQL API on "
        f"{export.exported_at:%Y-%m-%d}, kept only where the archive marks the observation public and its start is "
        f"more than {PROPRIETARY_MONTHS} months before the export; of {export.n_records} record(s) the archive "
        f"listed for the period, excluded: {excluded or 'none'}."
    )
