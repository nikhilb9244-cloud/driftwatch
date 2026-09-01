"""Fleet definitions: the primaries that Phase 2 screens against the whole catalogue.

A fleet is a short YAML file under ``fleets/`` listing objects by NORAD id with a display
name, a hard-body radius in metres with a note on where it came from, and a flag for
whether the object manoeuvres. The file is the place to argue for each number; this
module only checks that the argument was made and turns the file into typed objects.

Physics note on the radius. The hard-body radius is the radius of the smallest sphere
that encloses the whole spacecraft with its appendages deployed, the "circumscribing 3D
sphere" of NASA's guidance (Mashiku and Hejduk, *Recommended Methods for Setting Mission
Conjunction Analysis Hard Body Radii*, AAS 19-702, 2019). Step 3 integrates a Gaussian
over a disc whose radius is the *combined* hard-body radius, the primary's plus the
secondary's, so the values here scale the probability of collision directly. A sphere is
a conservative stand-in for an attitude-dependent shape: for anything long and flat, most
approach directions see much less than the sphere's cross-section. Every entry records
the dimensions its radius was built from so the choice can be revisited.

The manoeuvre flag is a warning, not a model. SGP4 cannot predict a burn, so every pair
that involves a manoeuvring object is flagged in the output (Step 2) and nothing here
tries to guess when the next burn is.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

log = logging.getLogger(__name__)

FLEET_SCHEMA_VERSION = 1

FLEET_KEYS: frozenset[str] = frozenset({"schema_version", "name", "description", "members"})
MEMBER_KEYS: frozenset[str] = frozenset(
    {"norad_id", "name", "hard_body_radius_m", "radius_source", "manoeuvres", "role", "notes"}
)
REQUIRED_MEMBER_KEYS: frozenset[str] = frozenset(
    {"norad_id", "name", "hard_body_radius_m", "radius_source", "manoeuvres"}
)
# Nothing in orbit is a kilometre across; a radius above this is a units mistake
# (millimetres, or a diameter in centimetres), not a spacecraft.
MAX_HARD_BODY_RADIUS_M = 1000.0


class FleetError(ValueError):
    """A fleet file is malformed or fails validation. The message names the member and the key."""


@dataclass(frozen=True)
class FleetMember:
    """One primary: identity, hard-body radius with its provenance, and the manoeuvre flag."""

    norad_id: int
    name: str
    hard_body_radius_m: float
    radius_source: str
    manoeuvres: bool
    role: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Fleet:
    """A validated fleet: unique NORAD ids, positive radii, every radius justified."""

    name: str
    description: str
    members: tuple[FleetMember, ...]
    path: Path | None = None
    _by_id: dict[int, FleetMember] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_id", {m.norad_id: m for m in self.members})

    def __len__(self) -> int:
        return len(self.members)

    def __iter__(self) -> Iterator[FleetMember]:
        return iter(self.members)

    def __contains__(self, norad_id: object) -> bool:
        return norad_id in self._by_id

    def __getitem__(self, norad_id: int) -> FleetMember:
        try:
            return self._by_id[int(norad_id)]
        except KeyError:
            raise KeyError(f"NORAD id {norad_id} is not in fleet {self.name!r}") from None

    @property
    def norad_ids(self) -> list[int]:
        """NORAD ids in file order."""
        return [m.norad_id for m in self.members]

    def hard_body_radii_m(self) -> dict[int, float]:
        """NORAD id to hard-body radius in metres, for the probability step."""
        return {m.norad_id: m.hard_body_radius_m for m in self.members}


def _check_keys(mapping: Mapping[str, Any], allowed: frozenset[str], required: frozenset[str], where: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise FleetError(f"{where}: unknown key(s) {unknown}; allowed keys are {sorted(allowed)}")
    missing = sorted(required - set(mapping))
    if missing:
        raise FleetError(f"{where}: missing required key(s) {missing}")


def _member_from_mapping(raw: Any, index: int) -> FleetMember:
    where = f"members[{index}]"
    if not isinstance(raw, Mapping):
        raise FleetError(f"{where}: expected a mapping, got {type(raw).__name__}")
    _check_keys(raw, MEMBER_KEYS, REQUIRED_MEMBER_KEYS, where)
    where = f"{where} ({raw.get('name', '?')})"

    norad_id = raw["norad_id"]
    if isinstance(norad_id, bool) or not isinstance(norad_id, int) or norad_id <= 0:
        raise FleetError(f"{where}: norad_id must be a positive integer, got {norad_id!r}")

    name = raw["name"]
    if not isinstance(name, str) or not name.strip():
        raise FleetError(f"{where}: name must be a non-empty string")

    radius = raw["hard_body_radius_m"]
    if isinstance(radius, bool) or not isinstance(radius, int | float):
        raise FleetError(f"{where}: hard_body_radius_m must be a number in metres, got {radius!r}")
    radius = float(radius)
    if not (0.0 < radius <= MAX_HARD_BODY_RADIUS_M):
        raise FleetError(
            f"{where}: hard_body_radius_m must be in (0, {MAX_HARD_BODY_RADIUS_M:.0f}] metres, got {radius}"
        )

    source = raw["radius_source"]
    if not isinstance(source, str) or len(source.split()) < 5:
        raise FleetError(f"{where}: radius_source must say where the radius came from (a sentence, not a word)")

    manoeuvres = raw["manoeuvres"]
    if not isinstance(manoeuvres, bool):
        raise FleetError(f"{where}: manoeuvres must be true or false, got {manoeuvres!r}")

    role = raw.get("role")
    if role is not None and (not isinstance(role, str) or not role.strip()):
        raise FleetError(f"{where}: role must be a non-empty string when given")
    notes = raw.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise FleetError(f"{where}: notes must be a string when given")

    return FleetMember(
        norad_id=norad_id,
        name=name.strip(),
        hard_body_radius_m=radius,
        radius_source=" ".join(source.split()),
        manoeuvres=manoeuvres,
        role=role.strip() if role else None,
        notes=" ".join(notes.split()) if notes else None,
    )


def fleet_from_mapping(data: Any, *, path: Path | None = None) -> Fleet:
    """Validate a parsed YAML document and build a :class:`Fleet`; raise :class:`FleetError` otherwise."""
    where = str(path) if path else "fleet"
    if not isinstance(data, Mapping):
        raise FleetError(f"{where}: the document must be a mapping with a `members` list")
    _check_keys(data, FLEET_KEYS, frozenset({"schema_version", "name", "members"}), where)
    if data["schema_version"] != FLEET_SCHEMA_VERSION:
        raise FleetError(f"{where}: schema_version {data['schema_version']!r} is not {FLEET_SCHEMA_VERSION}")
    name = data["name"]
    if not isinstance(name, str) or not name.strip():
        raise FleetError(f"{where}: name must be a non-empty string")
    description = data.get("description") or ""
    if not isinstance(description, str):
        raise FleetError(f"{where}: description must be a string")
    raw_members = data["members"]
    if not isinstance(raw_members, list) or not raw_members:
        raise FleetError(f"{where}: members must be a non-empty list")

    members = tuple(_member_from_mapping(raw, k) for k, raw in enumerate(raw_members))
    seen: dict[int, str] = {}
    for m in members:
        if m.norad_id in seen:
            raise FleetError(f"{where}: NORAD id {m.norad_id} appears twice ({seen[m.norad_id]!r} and {m.name!r})")
        seen[m.norad_id] = m.name
    return Fleet(name=name.strip(), description=" ".join(description.split()), members=members, path=path)


def load_fleet(path: Path | str) -> Fleet:
    """Read and validate a fleet YAML file."""
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise FleetError(f"{path}: not valid YAML: {exc}") from exc
    fleet = fleet_from_mapping(data, path=path)
    log.info("Loaded fleet %r: %d members from %s", fleet.name, len(fleet), path)
    return fleet


RESOLVED_COLUMNS: tuple[str, ...] = (
    "norad_id",
    "name",
    "role",
    "hard_body_radius_m",
    "manoeuvres",
    "in_catalogue",
    "catalogue_name",
    "object_type",
    "owner",
    "category",
    "altitude_band",
    "perigee_km",
    "apogee_km",
    "inclination_deg",
    "epoch",
    "epoch_age_days",
    "source",
    "in_active_group",
)


def resolve_fleet(fleet: Fleet, snapshot: pd.DataFrame, *, now: datetime | None = None) -> pd.DataFrame:
    """Join the fleet to a catalogue snapshot, one row per member in file order.

    ``in_catalogue`` is False (and the catalogue columns are null) for a member the
    snapshot does not hold, which is what Step 2 checks before screening: a primary with
    no element set cannot be screened, and silently skipping it would be worse than
    stopping. ``epoch_age_days`` is measured at ``now`` (default: the current time).
    """
    now_ts = pd.Timestamp(now or datetime.now(UTC))
    now_ts = now_ts.tz_convert("UTC") if now_ts.tzinfo else now_ts.tz_localize("UTC")
    by_id = snapshot.drop_duplicates("norad_id").set_index("norad_id")
    rows: list[dict[str, Any]] = []
    for m in fleet.members:
        row: dict[str, Any] = {
            "norad_id": m.norad_id,
            "name": m.name,
            "role": m.role,
            "hard_body_radius_m": m.hard_body_radius_m,
            "manoeuvres": m.manoeuvres,
            "in_catalogue": m.norad_id in by_id.index,
        }
        if row["in_catalogue"]:
            cat = by_id.loc[m.norad_id]
            epoch = pd.Timestamp(cat["epoch"])
            epoch = epoch.tz_convert("UTC") if epoch.tzinfo else epoch.tz_localize("UTC")
            groups = cat["groups"]
            row.update(
                {
                    "catalogue_name": cat["name"],
                    "object_type": cat["object_type"],
                    "owner": cat["owner"],
                    "category": cat["category"],
                    "altitude_band": cat["altitude_band"],
                    "perigee_km": float(cat["perigee_km"]),
                    "apogee_km": float(cat["apogee_km"]),
                    "inclination_deg": float(cat["inclination_deg"]),
                    "epoch": epoch,
                    "epoch_age_days": (now_ts - epoch).total_seconds() / 86400.0,
                    "source": cat["source"],
                    "in_active_group": "active" in (list(groups) if groups is not None else []),
                }
            )
        rows.append(row)
    df = pd.DataFrame(rows)
    for col in RESOLVED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[list(RESOLVED_COLUMNS)]
    df["in_active_group"] = df["in_active_group"].fillna(False).astype(bool)
    return df
