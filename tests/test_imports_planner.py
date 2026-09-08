"""Import equivalence, ambiguous conventions and scheduling decisions."""

import itertools
import json
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
import pytest
from sgp4.exporter import export_tle
from workspace_fixtures import RECORD  # noqa: E402
from workspace_fixtures import text as fixture_text

from driftwatch import local, workbench
from driftwatch.catalogue.history import frame_from_records
from driftwatch.contact_planner import schedule_contacts
from driftwatch.imports import CONVENTIONS, STATE_KEYS, decode_orbit
from driftwatch.orbit.propagator import build_satrecs


def record():
    return {**RECORD, **CONVENTIONS}


def test_omm_encodings_preserve_the_same_trajectory_and_long_catalogue_id():
    row = record()
    row["NORAD_CAT_ID"] = 123456789
    data = [
        json.dumps([row]),
        "CCSDS_OMM_VERS = 2.0\n" + "\n".join(f"{k} = {v}" for k, v in row.items()),
        '<ndm xmlns="urn:ccsds:test"><omm><body><segment><metadata>'
        + "".join(f"<{k}>{escape(str(v))}</{k}>" for k, v in row.items())
        + "</metadata></segment></body></omm></ndm>",
        pd.DataFrame([row]).to_csv(index=False),
    ]
    times = np.array(["2024-05-10T01:00:00", "2024-05-10T04:00:00"], dtype="datetime64[us]")
    states = [
        workbench.trajectory(("test", text), 123456789, pd.Timestamp("2024-05-10")).states(times)[0] for text in data
    ]
    for result in states[1:]:
        np.testing.assert_allclose(result, states[0], atol=1e-8)
    inspected = workbench.analyse("inspect", {"file": {"name": "renamed.anything", "text": data[-1]}})
    assert inspected["objects"][0]["norad"] == 123456789


def xml_oem(text):
    segment = local.parse_oem(text)[0]
    fields = {
        "OBJECT_ID": segment.object_id,
        "CENTER_NAME": "EARTH",
        "REF_FRAME": segment.ref_frame,
        "TIME_SYSTEM": segment.time_system,
    }
    states = []
    for row in segment.states.itertuples(index=False, name=None):
        values = [row[0].isoformat(), *row[1:]]
        states.append(
            "<stateVector>"
            + "".join(f"<{k}>{v}</{k}>" for k, v in zip(STATE_KEYS, values, strict=True))
            + "</stateVector>"
        )
    return (
        '<oem version="2.0"><body><segment><metadata>'
        + "".join(f"<{k}>{v}</{k}>" for k, v in fields.items())
        + "</metadata><data>"
        + "".join(states)
        + "</data></segment></body></oem>"
    )


def test_local_xml_keeps_provider_creation_separate_from_unknown_availability():
    text = xml_oem(fixture_text("reference.oem")).replace(
        "<body>",
        "<header><CREATION_DATE>2024-06-01T00:00:00Z</CREATION_DATE>"
        "<ORIGINATOR>Example provider</ORIGINATOR></header><body>",
        1,
    )
    orbit = workbench.trajectory(("reference.xml", text), 90001)
    metadata = orbit.metadata["source_time_metadata"][0]
    assert metadata["provider_created_at"].startswith("2024-06-01")
    assert metadata["originator"] == "Example provider"
    assert metadata["published_at"] is None and metadata["retrieved_at"] is None
    row = {**record(), "CREATION_DATE": "2024-05-11T00:00:00Z"}
    imported = frame_from_records([row], source="local-upload")
    assert imported.provider_created_at.iloc[0] == pd.Timestamp("2024-05-11T00:00:00Z")
    assert imported.fetched_at.isna().all() and imported.retrieved_at.isna().all()


def test_oem_xml_and_mapped_metre_csv_match_kvn_without_unit_guessing():
    text = fixture_text("reference.oem")
    orbit = workbench.trajectory(("reference.oem", text), 90001)
    states = local.parse_oem(text)[0].states.copy()
    states.iloc[:, 1:] *= 1000
    csv = states.to_csv(index=False, sep=";")
    # Explicit ISO times avoid spreadsheet locale ambiguity.
    states["t"] = states.t.map(lambda t: t.isoformat())
    csv = states.to_csv(index=False, sep=";")
    options = {
        "format": "state-csv",
        "delimiter": ";",
        "columns": dict(zip(STATE_KEYS, states.columns, strict=True)),
        "frame": "TEME",
        "time_system": "UTC",
        "position_unit": "m",
        "velocity_unit": "m/s",
        "object_id": "2024-001A",
    }
    others = [
        workbench.trajectory(("reference.xml", xml_oem(text)), 90001),
        workbench.trajectory(("state.csv", csv), 90001, options=options),
    ]
    times = np.array(["2024-05-10T01:00:00", "2024-05-10T02:10:00"], dtype="datetime64[us]")
    for other in others:
        np.testing.assert_allclose(other.states(times)[0], orbit.states(times)[0], atol=1e-8)
    options.pop("time_system")
    with pytest.raises(ValueError, match="time system"):
        decode_orbit(csv, options)


def test_tle_checksum_and_conventions_are_enforced():
    sat = build_satrecs(frame_from_records([record()], source="test"))[0]
    sat.intldesg = "24001A"
    line1, line2 = export_tle(sat)
    decoded = decode_orbit("0 Example satellite\n" + line1 + "\n" + line2)
    assert decoded.records[0]["NORAD_CAT_ID"] == 90001
    broken = line1[:-1] + str((int(line1[-1]) + 1) % 10)
    with pytest.raises(ValueError, match="checksum"):
        decode_orbit(broken + "\n" + line2)
    row = record()
    row["MEAN_ELEMENT_THEORY"] = "DSST"
    with pytest.raises(ValueError, match="SGP4"):
        decode_orbit(json.dumps([row]))


def test_malformed_oem_rows_and_xml_units_are_not_silently_skipped():
    text = fixture_text("reference.oem")
    with pytest.raises(ValueError, match="state rows"):
        decode_orbit(text + "2024-05-11T12:00:00 1 2 broken\n")
    xml = xml_oem(text).replace("<X>", '<X units="m">')
    with pytest.raises(ValueError, match="supported message unit"):
        decode_orbit(xml)
    with pytest.raises(ValueError, match="DTDs"):
        decode_orbit('<!DOCTYPE oem [<!ENTITY x "bad">]><oem/>')
    with pytest.raises(ValueError, match="Duplicate catalogue"):
        decode_orbit(json.dumps([record(), record()]))


def test_scheduler_beats_priority_greedy_and_handles_exact_turnaround():
    text = (
        "contact_id,satellite,start,end,priority\n"
        "A,One,2024-05-10T09:00:00Z,2024-05-10T09:20:00Z,10\n"
        "B,Two,2024-05-10T09:00:00Z,2024-05-10T09:08:00Z,6\n"
        "C,Three,2024-05-10T09:09:00Z,2024-05-10T09:18:00Z,6\n"
    )
    result = schedule_contacts(text, turnaround_s=60)
    assert result["priority_total"] == 12
    assert {c["contact_id"] for c in result["contacts"] if c["selected"]} == {"B", "C"}
    assert next(c for c in result["contacts"] if c["contact_id"] == "A")["conflicts_with"] == ["B", "C"]
    assert schedule_contacts(text, turnaround_s=61)["priority_total"] == 10


def test_scheduler_matches_exhaustive_feasible_subsets_with_variable_columns():
    rng = np.random.default_rng(71)
    for _ in range(12):
        starts = rng.integers(0, 90, 8)
        ends = starts + rng.integers(1, 20, 8)
        weights = rng.integers(1, 20, 8)
        rows = [
            {
                "id": str(i),
                "craft": "Test",
                "a": (pd.Timestamp("2024-05-10", tz="UTC") + pd.Timedelta(minutes=int(a))).isoformat(),
                "b": (pd.Timestamp("2024-05-10", tz="UTC") + pd.Timedelta(minutes=int(b))).isoformat(),
                "score": int(w),
            }
            for i, (a, b, w) in enumerate(zip(starts, ends, weights, strict=True))
        ]
        result = schedule_contacts(
            pd.DataFrame(rows).to_csv(index=False, sep=";"),
            turnaround_s=60,
            delimiter=";",
            mapping=dict(
                zip(
                    ["contact_id", "satellite", "start", "end", "priority"],
                    ["id", "craft", "a", "b", "score"],
                    strict=True,
                )
            ),
        )
        best = 0
        for mask in itertools.product([False, True], repeat=8):
            selected = sorted([i for i in range(8) if mask[i]], key=lambda i: starts[i])
            if all(ends[a] + 1 <= starts[b] for a, b in zip(selected, selected[1:], strict=False)):
                best = max(best, sum(weights[i] for i in selected))
        assert result["priority_total"] == best


def test_scheduler_refuses_ambiguous_time_and_multiple_antennas():
    text = (
        "contact_id,satellite,start,end,priority,resource\n"
        "a,x,2024-05-10T09:00:00Z,2024-05-10T09:08:00Z,1,A\n"
        "b,x,2024-05-10T09:00:00Z,2024-05-10T09:08:00Z,1,B\n"
    )
    with pytest.raises(ValueError, match="one antenna"):
        schedule_contacts(text)
    with pytest.raises(ValueError, match="offset"):
        schedule_contacts(text.replace(",B", ",A").replace("Z,", ","))


def test_oem_usable_times_constrain_the_comparison_and_keep_gaps():
    text = fixture_text("reference.oem").replace(
        "META_STOP", "USEABLE_START_TIME = 2024-05-10T01:00:00\nUSEABLE_STOP_TIME = 2024-05-10T02:00:00\nMETA_STOP"
    )
    orbit = workbench.trajectory(("reference.oem", text), 90001)
    assert orbit.start == pd.Timestamp("2024-05-10T01:00:00")
    assert orbit.end == pd.Timestamp("2024-05-10T02:00:00")
