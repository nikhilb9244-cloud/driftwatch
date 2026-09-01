"""Fleet files: validation rules, the demo fleet's composition, and the join to a snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml

from driftwatch.catalogue.snapshot import build_snapshot
from driftwatch.fleet import (
    FLEET_SCHEMA_VERSION,
    Fleet,
    FleetError,
    fleet_from_mapping,
    load_fleet,
    resolve_fleet,
)

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "fleets" / "demo.yaml"


def _member(**overrides) -> dict:
    base = {
        "norad_id": 25544,
        "name": "ISS (Zarya)",
        "hard_body_radius_m": 70,
        "radius_source": "Half the diagonal of the 109 x 73 x 20 m envelope, rounded up.",
        "manoeuvres": True,
    }
    base.update(overrides)
    return base


def _doc(*members: dict, **overrides) -> dict:
    doc = {"schema_version": FLEET_SCHEMA_VERSION, "name": "test", "members": list(members) or [_member()]}
    doc.update(overrides)
    return doc


def test_minimal_fleet_round_trip(tmp_path):
    path = tmp_path / "f.yaml"
    path.write_text(yaml.safe_dump(_doc(_member(), _member(norad_id=39634, name="Sentinel-1A", role="sentinel"))))
    fleet = load_fleet(path)
    assert isinstance(fleet, Fleet)
    assert fleet.norad_ids == [25544, 39634]
    assert fleet[39634].role == "sentinel" and fleet[25544].role is None
    assert 25544 in fleet and 1 not in fleet
    assert fleet.hard_body_radii_m() == {25544: 70.0, 39634: 70.0}
    assert fleet.path == path
    with pytest.raises(KeyError):
        fleet[1]


@pytest.mark.parametrize(
    "bad, message",
    [
        ({"norad_id": -1}, "positive integer"),
        ({"norad_id": "25544"}, "positive integer"),
        ({"norad_id": True}, "positive integer"),
        ({"name": ""}, "non-empty"),
        ({"hard_body_radius_m": 0}, "metres"),
        ({"hard_body_radius_m": -5}, "metres"),
        ({"hard_body_radius_m": 5000}, "metres"),
        ({"hard_body_radius_m": "70 m"}, "number"),
        ({"radius_source": "guess"}, "where the radius came from"),
        ({"manoeuvres": "yes"}, "true or false"),
        ({"manoeuvres": 1}, "true or false"),
        ({"manouevres": True}, "unknown key"),
        ({"role": ""}, "role"),
    ],
)
def test_member_validation(bad, message):
    member = _member(**bad)  # a misspelt key sits beside the real one and is rejected as unknown
    with pytest.raises(FleetError, match=message):
        fleet_from_mapping(_doc(member))


def test_member_missing_required_key():
    member = _member()
    del member["radius_source"]
    with pytest.raises(FleetError, match="missing required key.*radius_source"):
        fleet_from_mapping(_doc(member))


def test_document_validation():
    with pytest.raises(FleetError, match="mapping"):
        fleet_from_mapping([1, 2])
    with pytest.raises(FleetError, match="schema_version"):
        fleet_from_mapping(_doc(schema_version=99))
    with pytest.raises(FleetError, match="non-empty list"):
        fleet_from_mapping(_doc(members=[]))
    with pytest.raises(FleetError, match="unknown key"):
        fleet_from_mapping(_doc(extra=1))
    with pytest.raises(FleetError, match="appears twice"):
        fleet_from_mapping(_doc(_member(), _member(name="ISS again")))


def test_invalid_yaml_is_a_fleet_error(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("members: [\n  - norad_id: 1\n")
    with pytest.raises(FleetError, match="not valid YAML"):
        load_fleet(path)


def test_demo_fleet_matches_the_prompt():
    """ISS, one Sentinel, two university cubesats, every active SAFR object; each radius justified."""
    fleet = load_fleet(DEMO)
    assert fleet.name == "demo"
    ids = fleet.norad_ids
    assert len(ids) == len(set(ids))
    assert 25544 in fleet and fleet[25544].manoeuvres is True
    sentinels = [m for m in fleet if m.name.upper().startswith("SENTINEL")]
    assert len(sentinels) == 1 and sentinels[0].manoeuvres is True
    cubesats = [m for m in fleet if m.role == "university_cubesat"]
    assert len(cubesats) >= 2
    assert all(m.manoeuvres is False for m in cubesats), "the demo cubesats have no propulsion"
    safr = [m for m in fleet if m.role == "safr"]
    assert {m.norad_id for m in safr} == {39417, 55053}, "active SAFR objects on the 2026-09-01 SATCAT"
    for m in fleet:
        assert 0 < m.hard_body_radius_m <= 100
        assert len(m.radius_source.split()) >= 10, f"{m.name}: justify the radius in the file"
    # The ISS is the largest thing in orbit; cubesats are the smallest members.
    assert fleet[25544].hard_body_radius_m == max(m.hard_body_radius_m for m in fleet)
    assert min(m.hard_body_radius_m for m in fleet) < 1.0


def test_resolve_fleet_against_snapshot(omm_records):
    fetched_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    snap = build_snapshot({"active": omm_records[:6], "stations": omm_records[:2]}, None, fetched_at=fetched_at)
    present = [int(x) for x in snap["norad_id"].iloc[:3]]
    absent = 999_999_999
    fleet = fleet_from_mapping(
        _doc(
            _member(norad_id=present[0], name="A", hard_body_radius_m=70, role="station"),
            _member(norad_id=absent, name="Ghost", hard_body_radius_m=0.5, manoeuvres=False),
            _member(norad_id=present[2], name="C", hard_body_radius_m=13),
        )
    )
    now = snap["epoch"].max() + pd.Timedelta(days=2)
    resolved = resolve_fleet(fleet, snap, now=now)
    assert resolved["norad_id"].tolist() == [present[0], absent, present[2]]
    assert resolved["in_catalogue"].tolist() == [True, False, True]
    assert resolved["hard_body_radius_m"].tolist() == [70.0, 0.5, 13.0]
    assert resolved["manoeuvres"].tolist() == [True, False, True]
    ok = resolved[resolved["in_catalogue"]]
    assert ok["catalogue_name"].tolist() == snap.set_index("norad_id").loc[[present[0], present[2]], "name"].tolist()
    assert (ok["epoch_age_days"] >= 2.0).all()
    assert ok["in_active_group"].all()
    ghost = resolved[~resolved["in_catalogue"]].iloc[0]
    assert pd.isna(ghost["catalogue_name"]) and pd.isna(ghost["perigee_km"])
    assert bool(ghost["in_active_group"]) is False
