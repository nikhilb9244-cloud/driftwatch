"""The CDM parser and matcher, built against the Kelvins rows as test input.

Three promises are pinned. The parser reads both forms of the standard and a message written back
out reads back equal, so nothing is lost between an operator's file and the report. The Kelvins
adapter turns the challenge rows into messages whose every non-synthetic field is the row's own,
and matching those messages against events built from the same rows recovers them exactly -- by
construction, which is what makes it a test of the plumbing and not of anything else. And the
matcher separates the three things the report is for: the warnings public data found, the
warnings it missed, and the public-data flags no warning mentions.

The real challenge file, when it is present under ``data/external/kelvins/``, is run through the
same path; that test is skipped with a clear message when the download has not been made.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_kelvins import SKIP_MESSAGE, synthetic_frame

from driftwatch.cdm import kelvins as cdm_kelvins
from driftwatch.cdm import match as cdm_match
from driftwatch.cdm import parse as cdm_parse
from driftwatch.risk import kelvins as risk_kelvins

#: The example message from CCSDS 508.0-B-1, abridged to the keys the standard marks obligatory
#: plus the covariance and a state vector, in the KVN form.
SAMPLE_KVN = """\
CCSDS_CDM_VERS = 1.0
COMMENT This is a sample CDM in the KVN form.
CREATION_DATE = 2010-03-12T22:31:12.000
ORIGINATOR = JSPOC
MESSAGE_FOR = SATELLITE A
MESSAGE_ID = 201113719185
TCA = 2010-03-13T22:37:52.618
MISS_DISTANCE = 715 [m]
RELATIVE_SPEED = 14762 [m/s]
RELATIVE_POSITION_R = 27.4 [m]
RELATIVE_POSITION_T = -70.2 [m]
RELATIVE_POSITION_N = 711.8 [m]
RELATIVE_VELOCITY_R = -7.2 [m/s]
RELATIVE_VELOCITY_T = -14692.0 [m/s]
RELATIVE_VELOCITY_N = -1437.2 [m/s]
START_SCREEN_PERIOD = 2010-03-12T18:29:32.212
STOP_SCREEN_PERIOD = 2010-03-15T18:29:32.212
COLLISION_PROBABILITY = 4.835E-05
COLLISION_PROBABILITY_METHOD = FOSTER-1992
OBJECT = OBJECT1
OBJECT_DESIGNATOR = 12345
CATALOG_NAME = SATCAT
OBJECT_NAME = SATELLITE A
INTERNATIONAL_DESIGNATOR = 1997-030E
OBJECT_TYPE = PAYLOAD
EPHEMERIS_NAME = EPHEMERIS SATELLITE A
COVARIANCE_METHOD = CALCULATED
MANEUVERABLE = YES
REF_FRAME = EME2000
X = 2570.097065 [km]
Y = 2244.654904 [km]
Z = 6281.497978 [km]
X_DOT = 4.418769571 [km/s]
Y_DOT = 4.833547743 [km/s]
Z_DOT = -3.526774282 [km/s]
CR_R = 4.142E+01 [m**2]
CT_R = -8.579E+00 [m**2]
CT_T = 2.533E+03 [m**2]
CN_R = -2.313E+01 [m**2]
CN_T = 1.336E+01 [m**2]
CN_N = 7.098E+01 [m**2]
OBJECT = OBJECT2
OBJECT_DESIGNATOR = 30337
CATALOG_NAME = SATCAT
OBJECT_NAME = FENGYUN 1C DEB
INTERNATIONAL_DESIGNATOR = 1999-025AA
OBJECT_TYPE = DEBRIS
EPHEMERIS_NAME = NONE
COVARIANCE_METHOD = CALCULATED
MANEUVERABLE = NO
REF_FRAME = EME2000
X = 2569.540800 [km]
Y = 2245.093614 [km]
Z = 6281.599946 [km]
X_DOT = -2.888612500 [km/s]
Y_DOT = -6.007247516 [km/s]
Z_DOT = 3.328770172 [km/s]
CR_R = 1.337E+03 [m**2]
CT_R = -4.806E+04 [m**2]
CT_T = 2.492E+06 [m**2]
CN_R = -3.298E+01 [m**2]
CN_T = -7.5888E+02 [m**2]
CN_N = 7.105E+01 [m**2]
"""

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<cdm xmlns="urn:ccsds:schema:cdmxml" id="CCSDS_CDM_VERS" version="1.0">
  <header>
    <COMMENT>The same message in the XML form.</COMMENT>
    <CREATION_DATE>2010-03-12T22:31:12.000</CREATION_DATE>
    <ORIGINATOR>JSPOC</ORIGINATOR>
    <MESSAGE_FOR>SATELLITE A</MESSAGE_FOR>
    <MESSAGE_ID>201113719185</MESSAGE_ID>
  </header>
  <body>
    <relativeMetadataData>
      <TCA>2010-03-13T22:37:52.618</TCA>
      <MISS_DISTANCE units="m">715</MISS_DISTANCE>
      <RELATIVE_SPEED units="m/s">14762</RELATIVE_SPEED>
      <relativeStateVector>
        <RELATIVE_POSITION_R units="m">27.4</RELATIVE_POSITION_R>
        <RELATIVE_POSITION_T units="m">-70.2</RELATIVE_POSITION_T>
        <RELATIVE_POSITION_N units="m">711.8</RELATIVE_POSITION_N>
        <RELATIVE_VELOCITY_R units="m/s">-7.2</RELATIVE_VELOCITY_R>
        <RELATIVE_VELOCITY_T units="m/s">-14692.0</RELATIVE_VELOCITY_T>
        <RELATIVE_VELOCITY_N units="m/s">-1437.2</RELATIVE_VELOCITY_N>
      </relativeStateVector>
      <COLLISION_PROBABILITY>4.835E-05</COLLISION_PROBABILITY>
      <COLLISION_PROBABILITY_METHOD>FOSTER-1992</COLLISION_PROBABILITY_METHOD>
    </relativeMetadataData>
    <segment>
      <metadata>
        <OBJECT>OBJECT1</OBJECT>
        <OBJECT_DESIGNATOR>12345</OBJECT_DESIGNATOR>
        <OBJECT_NAME>SATELLITE A</OBJECT_NAME>
        <OBJECT_TYPE>PAYLOAD</OBJECT_TYPE>
        <MANEUVERABLE>YES</MANEUVERABLE>
      </metadata>
      <data>
        <covarianceMatrix>
          <CR_R units="m**2">4.142E+01</CR_R>
          <CT_R units="m**2">-8.579E+00</CT_R>
          <CT_T units="m**2">2.533E+03</CT_T>
          <CN_R units="m**2">-2.313E+01</CN_R>
          <CN_T units="m**2">1.336E+01</CN_T>
          <CN_N units="m**2">7.098E+01</CN_N>
        </covarianceMatrix>
      </data>
    </segment>
    <segment>
      <metadata>
        <OBJECT>OBJECT2</OBJECT>
        <OBJECT_DESIGNATOR>30337</OBJECT_DESIGNATOR>
        <OBJECT_NAME>FENGYUN 1C DEB</OBJECT_NAME>
        <OBJECT_TYPE>DEBRIS</OBJECT_TYPE>
      </metadata>
      <data>
        <covarianceMatrix>
          <CR_R units="m**2">1.337E+03</CR_R>
          <CT_R units="m**2">-4.806E+04</CT_R>
          <CT_T units="m**2">2.492E+06</CT_T>
          <CN_R units="m**2">-3.298E+01</CN_R>
          <CN_T units="m**2">-7.5888E+02</CN_T>
          <CN_N units="m**2">7.105E+01</CN_N>
        </covarianceMatrix>
      </data>
    </segment>
  </body>
</cdm>
"""


# --------------------------------------------------------------------------------------
# The parser


def test_the_kvn_sample_reads_into_the_typed_fields():
    cdm = cdm_parse.parse_kvn(SAMPLE_KVN, source="sample.kvn")
    assert cdm.version == "1.0" and cdm.originator == "JSPOC" and cdm.message_id == "201113719185"
    assert cdm.tca == pd.Timestamp("2010-03-13T22:37:52.618", tz="UTC")
    assert cdm.creation_date == pd.Timestamp("2010-03-12T22:31:12", tz="UTC")
    assert cdm.miss_distance_m == 715.0 and cdm.relative_speed_ms == 14762.0
    np.testing.assert_allclose(cdm.relative_position_rtn_m, [27.4, -70.2, 711.8])
    assert cdm.collision_probability == pytest.approx(4.835e-5)
    assert cdm.collision_probability_method == "FOSTER-1992"
    assert cdm.screen_period is not None and cdm.screen_period[1] > cdm.screen_period[0]
    assert cdm.object1.designator == "12345" and cdm.object2.designator == "30337"
    assert cdm.object1.name == "SATELLITE A" and cdm.object2.object_type == "DEBRIS"
    assert cdm.object1.maneuverable == "YES"
    assert cdm.pair == frozenset({"12345", "30337"})
    assert cdm.units["MISS_DISTANCE"] == "m" and cdm.object1.units["CR_R"] == "m**2"
    assert cdm.comments == ["This is a sample CDM in the KVN form."]
    # The covariance is the symmetric matrix the six lower-triangle terms describe.
    cov = cdm.object2.covariance_rtn_m2
    assert cov.shape == (3, 3) and cov[0, 1] == cov[1, 0] == pytest.approx(-4.806e4)
    np.testing.assert_allclose(cdm.object2.sigma_rtn_m, np.sqrt([1.337e3, 2.492e6, 7.105e1]))
    state = cdm.object1.state_km
    assert state is not None and state[0] == pytest.approx(2570.097065)
    assert cdm.summary()["object2_name"] == "FENGYUN 1C DEB"


def test_the_xml_form_reads_to_the_same_encounter_and_the_same_objects():
    """Element names are the KVN keys; the two segments are the two objects; units are attributes."""
    kvn = cdm_parse.parse_kvn(SAMPLE_KVN)
    xml = cdm_parse.parse(SAMPLE_XML, source="sample.xml")
    assert xml.form == "xml" and xml.version == "1.0"
    assert xml.tca == kvn.tca and xml.miss_distance_m == kvn.miss_distance_m
    assert xml.collision_probability == pytest.approx(kvn.collision_probability)
    assert xml.pair == kvn.pair
    np.testing.assert_allclose(xml.object2.covariance_rtn_m2, kvn.object2.covariance_rtn_m2)
    assert xml.object1.units["CR_R"] == "m**2" and xml.units["MISS_DISTANCE"] == "m"
    assert xml.comments == ["The same message in the XML form."]
    # The XML sample carries no state vector, and says so rather than inventing one.
    assert xml.object1.state_km is None


def test_a_message_written_out_reads_back_equal():
    cdm = cdm_parse.parse_kvn(SAMPLE_KVN)
    text = cdm_parse.to_kvn(cdm)
    again = cdm_parse.parse_kvn(text)
    assert again.raw == cdm.raw and again.units == cdm.units and again.comments == cdm.comments
    assert again.object1.raw == cdm.object1.raw and again.object2.raw == cdm.object2.raw
    assert again.object2.units == cdm.object2.units


def test_epochs_in_both_calendar_and_day_of_year_forms_and_designators_normalise():
    assert cdm_parse.parse_epoch("2024-131T12:00:00") == pd.Timestamp("2024-05-10T12:00:00", tz="UTC")
    assert cdm_parse.parse_epoch("2024-05-10T12:00:00Z") == pd.Timestamp("2024-05-10T12:00:00", tz="UTC")
    assert cdm_parse.format_epoch(pd.Timestamp("2024-05-10T12:00:00.250", tz="UTC")) == "2024-05-10T12:00:00.250"
    assert cdm_parse.normalise_designator("00025544") == "25544"
    assert cdm_parse.normalise_designator(25544.0) == "25544"
    assert cdm_parse.normalise_designator(" 2019-029AB ") == "2019-029AB"
    assert cdm_parse.normalise_designator(None) == ""


def test_a_file_without_a_tca_is_refused_and_a_directory_is_read_whole(tmp_path):
    with pytest.raises(ValueError, match="no TCA"):
        cdm_parse.parse_kvn("CCSDS_CDM_VERS = 1.0\nORIGINATOR = X\n")
    with pytest.raises(ValueError, match="OBJECT1 or OBJECT2"):
        cdm_parse.parse_kvn("TCA = 2024-05-10T00:00:00\nOBJECT = OBJECT3\n")
    (tmp_path / "a.kvn").write_text(SAMPLE_KVN, encoding="utf-8")
    (tmp_path / "b.xml").write_text(SAMPLE_XML, encoding="utf-8")
    (tmp_path / "notes.md").write_text("not a message", encoding="utf-8")
    loaded = cdm_parse.load_cdms(tmp_path)
    assert [c.form for c in loaded] == ["kvn", "xml"]
    assert cdm_parse.load_cdms(tmp_path / "a.kvn")[0].source.endswith("a.kvn")


# --------------------------------------------------------------------------------------
# The Kelvins adapter


def kelvins_rows() -> pd.DataFrame:
    """The challenge-layout frame from the Kelvins tests, with the columns the adapter also reads."""
    df = synthetic_frame(sigma_m=120.0, hbr_m=10.0)
    n = len(df)
    df["mission_id"] = [3, 3, 3, 7, 7, 7, 7, 11, 11, 11, 11, 11][:n]
    df["miss_distance"] = np.linalg.norm(
        df[["relative_position_r", "relative_position_t", "relative_position_n"]].to_numpy(dtype=float), axis=1
    )
    df["relative_speed"] = np.linalg.norm(
        df[["relative_velocity_r", "relative_velocity_t", "relative_velocity_n"]].to_numpy(dtype=float), axis=1
    )
    df["c_object_type"] = ["DEBRIS", "PAYLOAD", "ROCKET BODY", "UNKNOWN"] * (n // 4)
    df["t_actual_od_span"] = 5.5
    df["t_obs_used"] = 579.0
    df["t_time_lastob_start"] = 1.0
    df["c_cd_area_over_mass"] = 0.0129
    return df


def test_a_kelvins_row_becomes_a_message_whose_numbers_are_the_row_s_own():
    rows = kelvins_rows()
    row = rows.iloc[0]
    cdm = cdm_kelvins.kelvins_row_to_cdm(row)
    assert cdm.miss_distance_m == pytest.approx(float(row["miss_distance"]))
    np.testing.assert_allclose(
        cdm.relative_position_rtn_m,
        row[["relative_position_r", "relative_position_t", "relative_position_n"]].to_numpy(dtype=float),
    )
    assert cdm.collision_probability == pytest.approx(10.0 ** float(row["risk"]))
    assert cdm.object1.designator == str(cdm_kelvins.MISSION_BASE + 3)
    assert cdm.object2.designator == str(cdm_kelvins.EVENT_BASE + int(row["event_id"]))
    assert cdm.object2.object_type == "DEBRIS" and cdm.object1.object_type == "PAYLOAD"
    assert cdm.object1.raw["ACTUAL_OD_SPAN"] == 5.5 and cdm.object1.units["ACTUAL_OD_SPAN"] == "d"
    assert cdm.object2.raw["CD_AREA_OVER_MASS"] == pytest.approx(0.0129)
    # The covariance is the sigmas and correlations of the row, as ESA's risk column uses them.
    expected = risk_kelvins._covariance_from_sigmas(rows.iloc[[0]], "t")[0] * 1e6
    np.testing.assert_allclose(cdm.object1.covariance_rtn_m2, expected)
    # The creation date is `time_to_tca` days before the synthetic TCA, and the message says the
    # identities are synthetic.
    assert (cdm.tca - cdm.creation_date).total_seconds() == pytest.approx(float(row["time_to_tca"]) * 86400.0, abs=1)
    assert "synthetic" in cdm.comments[0]
    # And it is a message: it writes out and reads back.
    again = cdm_parse.parse_kvn(cdm_parse.to_kvn(cdm))
    assert again.tca == cdm.tca and again.object2.raw == cdm.object2.raw


def test_the_synthetic_tca_is_deterministic_and_spread_over_a_week():
    tcas = [cdm_kelvins.synthetic_tca(k) for k in range(50)]
    assert tcas == [cdm_kelvins.synthetic_tca(k) for k in range(50)]
    span = (max(tcas) - min(tcas)).total_seconds() / 86400.0
    assert 6.0 <= span <= 7.0
    assert len(set(tcas)) == 50


def test_kelvins_events_are_one_row_per_conjunction_with_the_last_message_s_numbers():
    rows = kelvins_rows()
    # Two messages about event 0: an early one and a late one; the events table keeps the late one.
    early = rows.iloc[[0]].copy()
    early["time_to_tca"] = 5.0
    early["miss_distance"] = early["miss_distance"] * 3
    frame = pd.concat([rows, early], ignore_index=True)
    events = cdm_kelvins.kelvins_events(frame)
    assert len(events) == len(rows)
    first = events[events["secondary_norad_id"] == cdm_kelvins.EVENT_BASE].iloc[0]
    assert first["miss_km"] == pytest.approx(float(rows.iloc[0]["miss_distance"]) / 1000.0)
    assert set(events["flag"]) <= {"red", "yellow", "none"}
    assert str(events["tca"].dtype).endswith("UTC]")


# --------------------------------------------------------------------------------------
# The matcher


def test_matching_messages_to_events_built_from_the_same_rows_recovers_them_and_reports_the_rest(tmp_path):
    rows = kelvins_rows()
    early = rows.copy()
    early["time_to_tca"] = early["time_to_tca"] + 3.0
    messages = cdm_kelvins.kelvins_to_cdms(pd.concat([rows, early], ignore_index=True))
    events = cdm_kelvins.kelvins_events(rows)
    n = len(events)

    # Perturb: one event's TCA moved 90 s (inside the tolerance), one moved 40 minutes (outside),
    # one dropped altogether, and one extra flagged event of the operator's that no message
    # mentions.
    events = events.copy()
    events.loc[0, "tca"] = events.loc[0, "tca"] + pd.Timedelta(seconds=90)
    events.loc[1, "tca"] = events.loc[1, "tca"] + pd.Timedelta(minutes=40)
    # A flagged event moved past the tolerance would itself count as a flag the operator never
    # received -- correctly, since forty minutes is a different pass. Unflag it so the count below
    # isolates the one deliberately added.
    events.loc[1, "flag"] = "none"
    dropped_event = int(events.loc[2, "secondary_norad_id"])
    events = events.drop(index=2)
    extra = events.iloc[[3]].copy()
    extra["event_id"] = "extra"
    extra["secondary_norad_id"] = 777_777
    extra["tca"] = events["tca"].min() + pd.Timedelta(hours=6)
    extra["pc"] = 3e-5
    extra["flag"] = "yellow"
    events = pd.concat([events, extra], ignore_index=True)

    result = cdm_match.match_cdms(messages, events, tolerance_s=600.0)
    s = result.summary
    assert s["n_cdms"] == 2 * n and s["n_operator_conjunctions"] == n
    # Two conjunctions lost: the one that moved past the tolerance and the one dropped.
    assert s["n_conjunctions_found_by_public_data"] == n - 2
    assert s["n_conjunctions_public_data_missed"] == 2 and s["n_cdms_unmatched"] == 4
    reasons = set(result.unmatched_cdms["reason"])
    assert any("past the tolerance" in r for r in reasons) and "pair not in the run" in reasons
    assert dropped_event in {int(o) for o in result.unmatched_cdms["object2"]}
    # The moved-inside event matched with its offset recorded; everything else at zero.
    moved = result.matches[result.matches["object2"] == str(cdm_kelvins.EVENT_BASE + int(rows.loc[0, "event_id"]))]
    assert (moved["dt_tca_s"].round(1) == 90.0).all()
    assert s["dt_tca_s"]["max_abs"] == 90.0
    # Built from the same rows, the misses and the probabilities agree by construction.
    assert s["miss_ratio_event_over_cdm"]["median"] == pytest.approx(1.0)
    assert s["log10_pc_ratio_event_over_cdm"]["median"] == pytest.approx(0.0, abs=1e-9)
    # The operator's flagged event that no message mentions is the third output.
    assert s["n_public_flags_operator_never_received"] == 1
    assert result.unwarned_flags["event_id"].tolist() == ["extra"]
    # And the whole thing round-trips through files on disk.
    paths = cdm_kelvins.write_cdms(messages[:5], tmp_path / "cdms")
    assert len(paths) == 5 and all(p.suffix == ".kvn" for p in paths)
    loaded = cdm_parse.load_cdms(tmp_path / "cdms")
    assert [c.message_id for c in loaded] == sorted(c.message_id for c in messages[:5])
    text = "\n".join(cdm_match.report_lines(result))
    assert "found" in text and "never received: 1" in text


def test_the_matcher_picks_a_scenario_and_tolerates_a_frame_with_no_flags():
    rows = kelvins_rows()
    messages = cdm_kelvins.kelvins_to_cdms(rows)
    events = cdm_kelvins.kelvins_events(rows)
    stormy = events.copy()
    stormy["scenario"] = "storm-g5"
    stormy["pc"] = stormy["pc"] * 0.5
    both = pd.concat([events, stormy], ignore_index=True)
    quiet = cdm_match.match_cdms(messages, both)
    assert quiet.summary["scenario"] == "quiet"
    storm = cdm_match.match_cdms(messages, both, scenario="storm-g5")
    assert storm.summary["scenario"] == "storm-g5"
    assert storm.summary["log10_pc_ratio_event_over_cdm"]["median"] == pytest.approx(np.log10(0.5), abs=1e-3)
    bare = events.drop(columns=["flag", "region", "confidence", "pc", "storm_validity"])
    result = cdm_match.match_cdms(messages, bare)
    assert result.summary["n_cdms_matched"] == len(messages)
    assert result.summary["n_public_flags_operator_never_received"] == 0
    empty = cdm_match.match_cdms([], events)
    assert empty.summary["n_cdms"] == 0 and empty.matches.empty and empty.unwarned_flags.empty


def test_the_real_kelvins_rows_go_through_the_whole_path_when_present():
    path = risk_kelvins.find_dataset()
    if path is None or not Path(path).exists():
        pytest.skip(SKIP_MESSAGE)
    frame = pd.read_csv(path, nrows=400)
    messages = cdm_kelvins.kelvins_to_cdms(frame)
    assert len(messages) == len(frame)
    events = cdm_kelvins.kelvins_events(frame)
    result = cdm_match.match_cdms(messages, events)
    assert result.summary["n_cdms_matched"] == len(messages)
    assert result.summary["n_conjunctions_public_data_missed"] == 0
    # Every message writes and reads back, including the ones at the probability floor.
    for cdm in messages[:20]:
        again = cdm_parse.parse_kvn(cdm_parse.to_kvn(cdm))
        assert again.tca == cdm.tca and again.pair == cdm.pair


def test_default_reference_epoch_is_the_gannon_window():
    assert cdm_kelvins.DEFAULT_REFERENCE_EPOCH == datetime(2024, 5, 9, tzinfo=UTC)
    assert cdm_kelvins.synthetic_tca(0) - pd.Timestamp(cdm_kelvins.DEFAULT_REFERENCE_EPOCH) < timedelta(days=1)
