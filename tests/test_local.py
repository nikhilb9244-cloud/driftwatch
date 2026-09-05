"""The local-analysis path: the network guard, the OEM reader, the manoeuvre record, the ephemeris benchmark against a
truth built from the set's own path, and the command end to end with nothing leaving the machine."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime

import httpx
import numpy as np
import pandas as pd
import pytest
from synthetic import satrec_from_kepler

from driftwatch import cli, local
from driftwatch.orbit.propagator import propagate_satrecs
from driftwatch.storm import precise


def test_no_network_refuses_every_client_and_restores_them():
    send, asend, urlopen = httpx.Client.send, httpx.AsyncClient.send, urllib.request.urlopen
    with local.no_network():
        with pytest.raises(local.NetworkRefused, match="refused"):
            httpx.Client().get("http://127.0.0.1:9/nothing")
        with pytest.raises(local.NetworkRefused):
            urllib.request.urlopen("http://127.0.0.1:9/nothing")
    assert (httpx.Client.send, httpx.AsyncClient.send, urllib.request.urlopen) == (send, asend, urlopen)


OEM = """CCSDS_OEM_VERS = 2.0
CREATION_DATE = 2024-05-08T00:00:00
ORIGINATOR = TEST OPERATOR
META_START
OBJECT_NAME = DESIGNED-1
OBJECT_ID = 2024-001A
CENTER_NAME = EARTH
REF_FRAME = TEME
TIME_SYSTEM = UTC
START_TIME = 2024-05-06T12:00:00.000
STOP_TIME = 2024-05-06T12:00:20.000
META_STOP
COMMENT two states, then a gap
2024-05-06T12:00:00.000 6838.0 0.0 0.0 0.0 7.6 0.0
2024-05-06T12:00:10.000 6837.9 76.0 0.0 -0.08 7.6 0.0 0.0 0.0 0.0
META_START
OBJECT_NAME = DESIGNED-1
OBJECT_ID = 2024-001A
CENTER_NAME = EARTH
REF_FRAME = TEME
TIME_SYSTEM = GPS
START_TIME = 2024-05-06T13:00:00.000
STOP_TIME = 2024-05-06T13:00:10.000
META_STOP
2024-05-06T13:00:00.000 6838.0 0.0 0.0 0.0 7.6 0.0
COVARIANCE_START
EPOCH = 2024-05-06T13:00:00.000
COV_REF_FRAME = RTN
1.0
COVARIANCE_STOP
"""


def test_parse_oem_reads_segments_states_time_systems_and_skips_covariance():
    segments = local.parse_oem(OEM, source="test.oem")
    assert [s.time_system for s in segments] == ["UTC", "GPS"] and segments[0].object_name == "DESIGNED-1"
    assert len(segments[0].states) == 2 and len(segments[1].states) == 1
    assert segments[0].states["vy_kms"].iloc[0] == 7.6 and segments[0].comments == ["two states, then a gap"]
    orbit = local.oem_to_precise_orbit(segments, norad_id=90001)
    assert orbit.frame == "TEME" and orbit.files == ["test.oem"] and len(orbit.table) == 3
    # The GPS-time segment moved 18 s earlier when read as UTC.
    assert orbit.table["t"].iloc[-1] == pd.Timestamp("2024-05-06T12:59:42")
    with pytest.raises(ValueError, match="unsupported ephemeris frame"):
        local.oem_to_precise_orbit(
            [local.OemSegment("x", "", "EARTH", "MARSIAU", "UTC", None, None, segments[0].states)], norad_id=1
        )
    with pytest.raises(ValueError, match="different frames"):
        local.oem_to_precise_orbit(
            segments + [local.OemSegment("x", "", "EARTH", "ITRF2020", "UTC", None, None, segments[0].states)],
            norad_id=1,
        )
    with pytest.raises(ValueError, match="no OEM segment"):
        local.parse_oem("CCSDS_OEM_VERS = 2.0\n")


def test_manoeuvre_records_need_start_and_end_columns(tmp_path):
    path = tmp_path / "burns.csv"
    path.write_text("Start,End,note\n2024-05-05T18:00:00Z,2024-05-05T18:02:00Z,orbit raise\n", encoding="utf-8")
    assert local.load_manoeuvre_records(path) == [
        (pd.Timestamp("2024-05-05T18:00:00"), pd.Timestamp("2024-05-05T18:02:00"))
    ]
    bad = tmp_path / "bad.csv"
    bad.write_text("when,what\n2024-05-05T18:00:00Z,x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="start"):
        local.load_manoeuvre_records(bad)


def designed_object(epoch: datetime):
    sat = satrec_from_kepler(90001, epoch, 6838.0, 0.001, np.radians(87.4), 0.3, 0.1, 0.2, bstar=1e-5)
    record = {
        "NORAD_CAT_ID": 90001,
        "OBJECT_NAME": "DESIGNED-1",
        "OBJECT_ID": "2024-001A",
        "EPOCH": epoch.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "MEAN_MOTION": sat.no_kozai * 1440.0 / (2 * np.pi),
        "ECCENTRICITY": sat.ecco,
        "INCLINATION": np.degrees(sat.inclo),
        "RA_OF_ASC_NODE": np.degrees(sat.nodeo),
        "ARG_OF_PERICENTER": np.degrees(sat.argpo),
        "MEAN_ANOMALY": np.degrees(sat.mo),
        "BSTAR": sat.bstar,
        "MEAN_MOTION_DOT": 0.0,
        "MEAN_MOTION_DDOT": 0.0,
        "EPHEMERIS_TYPE": 0,
        "CLASSIFICATION_TYPE": "U",
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 1,
    }
    return sat, record


def oem_from_sgp4(sat, epoch: datetime, hours: float, step_s: float = 60.0) -> str:
    grid = pd.to_datetime(epoch) + pd.to_timedelta(np.arange(0, hours * 3600 + step_s, step_s), unit="s")
    state = propagate_satrecs([sat], np.array([90001]), grid.to_numpy(dtype="datetime64[us]"))
    lines = [
        "CCSDS_OEM_VERS = 2.0",
        "CREATION_DATE = 2024-05-08T00:00:00",
        "ORIGINATOR = TEST OPERATOR",
        "META_START",
        "OBJECT_NAME = DESIGNED-1",
        "OBJECT_ID = 2024-001A",
        "CENTER_NAME = EARTH",
        "REF_FRAME = TEME",
        "TIME_SYSTEM = UTC",
        f"START_TIME = {grid[0].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}",
        f"STOP_TIME = {grid[-1].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}",
        "META_STOP",
    ]
    for t, r, v in zip(grid, state.r_teme[0], state.v_teme[0], strict=True):
        lines.append(
            f"{t.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]} {r[0]:.6f} {r[1]:.6f} {r[2]:.6f} "
            f"{v[0]:.9f} {v[1]:.9f} {v[2]:.9f}"
        )
    return "\n".join(lines) + "\n"


def test_the_command_runs_an_ephemeris_through_the_benchmark_with_nothing_leaving_the_machine(tmp_path, monkeypatch):
    """One designed set, its own SGP4 path as the operator's ephemeris, a burn record outside the arc."""
    epoch = datetime(2024, 5, 6, 12, 0, 0)
    sat, record = designed_object(epoch)
    (tmp_path / "eph.oem").write_text(oem_from_sgp4(sat, epoch, 30.0), encoding="utf-8")
    (tmp_path / "sets.json").write_text(json.dumps([record]), encoding="utf-8")
    (tmp_path / "burns.csv").write_text("start,end\n2024-05-03T00:00:00Z,2024-05-03T00:02:00Z\n", encoding="utf-8")
    out = tmp_path / "out"
    # Any fetch the command tried would be refused; make sure the guard is what runs, not a cache miss.
    monkeypatch.setattr(httpx.Client, "send", lambda *a, **k: pytest.fail("a request escaped the guard"))
    code = cli.main(
        [
            "local",
            "--out",
            str(out),
            "--ephemeris",
            str(tmp_path / "eph.oem"),
            "--norad",
            "90001",
            "--sets",
            str(tmp_path / "sets.json"),
            "--manoeuvres",
            str(tmp_path / "burns.csv"),
            "--leads",
            "6,24",
        ]
    )
    assert code == 0
    report = json.loads((out / "local_analysis.json").read_text(encoding="utf-8"))
    eph = report["ephemeris"]
    assert eph["frame"] == "TEME" and eph["n_trial_sets"] == 1 and eph["manoeuvre_record"].endswith("burns.csv")
    window = eph["summary"]["windows"]["ephemeris"]
    assert window["manoeuvres"]["source"] == ["operator-record"] and window["n_excluded_manoeuvre"] == 0
    assert set(window["by_lead_h"]) == {"6", "24"}
    assert window["by_lead_h"]["24"]["in_track"]["max_km"] < 0.01, "the truth is the set's own path"
    trials = pd.read_parquet(out / "ephemeris_trials.parquet")
    assert len(trials) == 2 and (trials["manoeuvre_source"] == "operator-record").all()
    text = (out / "local_analysis.md").read_text(encoding="utf-8")
    assert "Nothing left this machine" in text and "operator-record" in text
    assert {s["source"] for s in report["sources"]} >= {"Operator ephemeris", "Public element sets", "Manoeuvre record"}

    # A burn inside the arc before the set excludes every lead, and the report says so rather than printing numbers.
    (tmp_path / "burns.csv").write_text("start,end\n2024-05-06T00:00:00Z,2024-05-06T00:02:00Z\n", encoding="utf-8")
    out2 = tmp_path / "out2"
    assert (
        cli.main(
            [
                "local",
                "--out",
                str(out2),
                "--ephemeris",
                str(tmp_path / "eph.oem"),
                "--norad",
                "90001",
                "--sets",
                str(tmp_path / "sets.json"),
                "--manoeuvres",
                str(tmp_path / "burns.csv"),
                "--leads",
                "6,24",
            ]
        )
        == 0
    )
    report2 = json.loads((out2 / "local_analysis.json").read_text(encoding="utf-8"))
    w2 = report2["ephemeris"]["summary"]["windows"]["ephemeris"]
    assert w2["n_excluded_manoeuvre"] == 2 and w2["by_lead_h"] == {}

    # Nothing to do, and an ephemeris without an id, are refused before anything runs.
    assert cli.main(["local", "--out", str(tmp_path / "x")]) == 2
    assert cli.main(["local", "--out", str(tmp_path / "x"), "--ephemeris", str(tmp_path / "eph.oem")]) == 2


def test_ephemeris_benchmark_refuses_an_ephemeris_shorter_than_the_shortest_lead():
    epoch = datetime(2024, 5, 6, 12, 0, 0)
    sat, record = designed_object(epoch)
    segments = local.parse_oem(oem_from_sgp4(sat, epoch, 2.0), source="short.oem")
    orbit = local.oem_to_precise_orbit(segments, norad_id=90001)
    from driftwatch.catalogue import history

    sets = history.frame_from_records([record], source="local")
    with pytest.raises(ValueError, match="shorter than the shortest lead"):
        local.ephemeris_benchmark(90001, sets, orbit, leads_hours=(6.0,))
    assert precise.frame_kind("itrf2014") == "ITRF" and precise.frame_kind("EME2000") == "J2000"
