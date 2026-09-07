# ruff: noqa: E501  (sample product lines are quoted as the products write them)
"""The reference expansion: the product readers, the mission registry and its windows, the laser-ranging records and
stations, the troposphere model, and the light-time range model on a constructed geometry."""

from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest

from driftwatch.storm import precise, reference, reference_run, slr

# --------------------------------------------------------------------------------------
# Missions and windows


def test_every_mission_has_a_truth_or_a_laser_target_and_the_bands_cover_them():
    for m in reference.MISSIONS.values():
        assert m.truth != reference.TRUTH_NONE or m.slr, m.key
        assert reference.altitude_band_label(m.altitude_km) != "outside the bands", m.key
    assert reference.altitude_band_label(462.0) == "400-600 km"
    assert reference.altitude_band_label(1336.0) == "1000-1400 km"
    assert reference.altitude_band_label(2000.0) == "outside the bands"
    assert {"Sentinel-2A and Sentinel-2B", "GOCE", "CHAMP"} <= set(reference.NOT_COVERED)


def test_the_fourth_window_is_disturbed_held_out_and_after_the_tuning_windows():
    names = [w.name for w in reference.WINDOWS]
    assert names == ["quiet", "storm", "held-out", "august"]
    august = reference.AUGUST
    assert august.role == "held-out" and august.disturbed is not None
    assert august.sets_from < august.disturbed[0] < august.sets_to
    for w in precise.WINDOWS[:2]:
        assert w.truth_to < august.sets_from, "nothing the tuning-visible windows see is in August"


# --------------------------------------------------------------------------------------
# Product readers


def test_ids_file_names_are_read_and_the_newest_version_of_each_span_is_chosen():
    names = [
        "ssaja320.b24103.e24113.DG_.sp3.001.Z",
        "ssaja320.b24113.e24122.DG_.sp3.001.Z",
        "ssaja330.b24113.e24122.DG_.sp3.001.Z",
        "ssaja320.b24122.e24132.DG_.sp3.001.Z",
        "ssaja320.b24271.e24281.DG_.sp3.001.Z",
        "MD5SUMS",
    ]
    assert reference._yyddd("24113") == date(2024, 4, 22)
    chosen = reference.ids_files_for(names, date(2024, 4, 19), date(2024, 5, 4))
    assert chosen == [
        "ssaja320.b24103.e24113.DG_.sp3.001.Z",
        "ssaja330.b24113.e24122.DG_.sp3.001.Z",
        "ssaja320.b24122.e24132.DG_.sp3.001.Z",
    ]


def test_sentinel_1_orbit_file_is_the_one_starting_the_evening_before_and_parses():
    names = [
        "S1A_OPER_AUX_POEORB_OPOD_20240511T070733_V20240420T225942_20240422T005942.EOF.zip",
        "S1A_OPER_AUX_POEORB_OPOD_20240512T070747_V20240421T225942_20240423T005942.EOF.zip",
        "S1A_OPER_AUX_POEORB_OPOD_20240513T070000_V20240421T225942_20240423T005942.EOF.zip",
    ]
    assert reference.s1_file_for_day(names, date(2024, 4, 22)) == names[2], "the newest generation wins"
    assert reference.s1_file_for_day(names, date(2024, 4, 25)) is None
    xml = (
        '<Earth_Explorer_File><Data_Block><List_of_OSVs count="2"><OSV><TAI>TAI=2024-04-01T23:00:19.000000</TAI>'
        "<UTC>UTC=2024-04-01T22:59:42.000000</UTC><UT1>UT1=2024-04-01T22:59:41.986027</UT1>"
        '<Absolute_Orbit>+53246</Absolute_Orbit><X unit="m">1950200.216160</X><Y unit="m">-4143460.384445</Y>'
        '<Z unit="m">-5401629.615817</Z><VX unit="m/s">579.550068</VX><VY unit="m/s">-5889.842297</VY>'
        '<VZ unit="m/s">4730.338429</VZ><Quality>NOMINAL</Quality></OSV>'
        "<OSV><TAI>TAI=2024-04-01T23:00:29.000000</TAI><UTC>UTC=2024-04-01T22:59:52.000000</UTC>"
        "<UT1>UT1=2024-04-01T22:59:51.986027</UT1><Absolute_Orbit>+53246</Absolute_Orbit>"
        '<X unit="m">1955993.0</X><Y unit="m">-4202355.0</Y><Z unit="m">-5354282.0</Z>'
        '<VX unit="m/s">579.0</VX><VY unit="m/s">-5889.0</VY><VZ unit="m/s">4730.0</VZ><Quality>NOMINAL</Quality></OSV>'
        "</List_of_OSVs></Data_Block></Earth_Explorer_File>"
    )
    frame = reference.parse_eof(xml)
    assert len(frame) == 2 and frame["t"].iloc[0] == pd.Timestamp("2024-04-01T22:59:42")
    assert frame["x_km"].iloc[0] == pytest.approx(1950.200216160) and frame["vz_kms"].iloc[0] == pytest.approx(
        4.730338429
    )


GNV = """header:
  dimensions:
    num_records: 3
# End of YAML header
766843200 C E 91176.42831043818 218728.3222403865 -6854587.689530753 0.0005 0.0006 0.0010 -1130.978005769431 7518.720900251436 228.4225250577528 1.2e-06 1.9e-06 2.0e-06  00000000
766843201 C E 90045.94311766274 226246.9903230498 -6854355.044759914 0.0005 0.0006 0.0010 -1129.992141675325 7518.613707901231 236.866971931798 1.2e-06 1.9e-06 2.0e-06  00000000
766843210 C E 80000.0 290000.0 -6850000.0 0.0005 0.0006 0.0010 -1120.0 7517.0 300.0 1.2e-06 1.9e-06 2.0e-06  00000000
"""

THR = """header:
# End of YAML header
766843613 91576 G C   337832 8003 192713 6528 173083 125474 337470 7833 192700 6465 172973 125015 0 0 600 0 0 0 0 0 600 0 0 0 0 0 0 0 116914655 0 0 0 0 0 0 0 0 0 0 0 29162000 0   00001100
766865895 91235 G C   337833 8003 192713 6528 173083 125474 337471 7833 192700 6465 172973 125015 0 0 600 0 0 0 0 0 600 0 0 0 0 0 0 0 116916055 0 0 0 0 0 0 0 0 0 0 0 29162000 0   00001100
766894096 590803 G C   337834 8003 192713 6528 173083 125474 337472 7833 192700 6465 172973 125015 0 0 0 0 0 0 0 0 0 0 0 0 0 0 12000 3000 116917255 0 0 0 0 0 0 0 0 0 0 0 29162000 0   00001100
"""


def test_gracefo_navigation_and_thruster_products_are_read_in_utc():
    """GPS seconds past 2000-01-01 12:00:00 GPS: 766843200 is 2024-04-20 00:00:00 GPS, which is 23:59:42 UTC the day before."""
    gnv = reference.parse_gnv1b(GNV, step_s=10)
    assert len(gnv) == 2, "only the samples on the ten-second grid are kept"
    assert gnv["t"].iloc[0] == pd.Timestamp("2024-04-19T23:59:42")
    assert gnv["x_km"].iloc[0] == pytest.approx(91.17642831043818) and gnv["vy_kms"].iloc[0] == pytest.approx(
        7.518720900251436
    )
    thr = reference.parse_thr1b(THR)
    assert len(thr) == 3 and thr["orbit_1_ms"].tolist() == [0.0, 0.0, 12000.0] and thr["orbit_2_ms"].iloc[2] == 3000.0
    assert thr["attitude_ms"].iloc[0] == 1200.0
    mission = reference.MISSIONS["gracefo-c"]
    record = reference.gracefo_thruster_record(mission, thr, [], ["GNV1B_2024-04-20_C.parquet"])
    assert record.n_attitude_pulses == 2 and record.orbit_thrust_s == pytest.approx(15.0)
    assert len(record.intervals) == 1 and (record.intervals[0][1] - record.intervals[0][0]) == pd.Timedelta(seconds=15)


# --------------------------------------------------------------------------------------
# Laser ranging: records, stations, the troposphere and the range model

CRD = """h1 CRD  2 2024  4 21  2
h2 YARL       7090  5 13 3       ILRS
h3 sentinel3a  1601101 8010    41335 0 1 1
h4  1 2024  4 21  1 10 29 2024  4 21  1 15 44  0 0 0 0 1 0 2 0
c0 0  532.000 new la1 mcp ti1 swm    met cac
20  4229.501  989.30 297.50  25. 0
11  4229.500587400000     0.010463482347 new 2   15.0      2    3.0   0.000  -2.000 na          1.33 0 na
20  4241.401  989.30 297.50  25. 0
11  4241.400597700000     0.010265876739 new 2   15.0     16   27.0  -0.215  -0.526 na         10.67 0 na
h8
h1 CRD  2 2024  4 21  2
h2 GRZL       7839  1  1 4       ILRS
h3 sentinel3a  1601101 8010    41335 0 1 1
h4  1 2024  4 21 23 59 50 2024  4 22  0  4  0  0 0 0 0 1 0 2 0
c0 0  532.000 std la1
11 86395.000000000000     0.012000000000 std 2   15.0     10    5.0   0.000   0.000 na          2.00 0 na
11     5.000000000000     0.011000000000 std 2   15.0     10    5.0   0.000   0.000 na          2.00 0 na
h8
"""


def test_crd_normal_points_carry_their_session_and_cross_midnight():
    points = slr.parse_crd(CRD)
    assert len(points) == 4
    assert points["station"].tolist() == ["7090", "7090", "7839", "7839"]
    assert points["norad_id"].iloc[0] == 41335 and points["two_way"].all() and (points["epoch_event"] == 2).all()
    expected = pd.Timestamp("2024-04-21T01:10:29.5005874", tz="UTC")
    assert abs((points["t"].iloc[0] - expected).total_seconds()) < 2e-6, "microsecond timestamps"
    assert points["pressure_mbar"].iloc[1] == 989.3 and points["temperature_k"].iloc[1] == 297.5
    assert np.isnan(points["pressure_mbar"].iloc[2]), "Graz's session in the sample carries no meteorology"
    assert points["t"].iloc[3] == pd.Timestamp("2024-04-22T00:00:05", tz="UTC"), "seconds of day wrap at midnight"


SINEX = """%=SNX 2.02 DGF 25:036:43200 DGF 79:329:00000 25:036:43200 C 01368 2 S
+SOLUTION/EPOCHS
 7090  A    1 L 79:329:00000 14:079:86399 96:284:00000
 7090  A    2 L 14:080:00000 00:000:00000 19:181:00000
-SOLUTION/EPOCHS
+SOLUTION/ESTIMATE
     1 STAX   7090  A    1 15:001:00000 m    2 -.238900777005032E+07 0.69543E-03
     2 STAY   7090  A    1 15:001:00000 m    2 0.504332948581405E+07 0.59590E-03
     3 STAZ   7090  A    1 15:001:00000 m    2 -.307852397088064E+07 0.69866E-03
     4 VELX   7090  A    1 15:001:00000 m/y  2 -.468239683104311E-01 0.52896E-04
     5 VELY   7090  A    1 15:001:00000 m/y  2 0.797007645988301E-02 0.45572E-04
     6 VELZ   7090  A    1 15:001:00000 m/y  2 0.509599889854529E-01 0.59966E-04
     7 STAX   7090  A    2 15:001:00000 m    2 -.238900777100000E+07 0.69543E-03
     8 STAY   7090  A    2 15:001:00000 m    2 0.504332948600000E+07 0.59590E-03
     9 STAZ   7090  A    2 15:001:00000 m    2 -.307852397100000E+07 0.69866E-03
    10 VELX   7090  A    2 15:001:00000 m/y  2 -.468239683104311E-01 0.52896E-04
    11 VELY   7090  A    2 15:001:00000 m/y  2 0.797007645988301E-02 0.45572E-04
    12 VELZ   7090  A    2 15:001:00000 m/y  2 0.509599889854529E-01 0.59966E-04
-SOLUTION/ESTIMATE
"""

ECC = """%=SNX 2.02 GSC 26:036:12000 DGF 68:041:00000 00:000:00000 L 00558 0 X
+SITE/ECCENTRICITY
 7090  A    1 L 10:196:00000 14:079:86399 XYZ   1.5620  -3.2960   1.8940        70900513
 7090  A    1 L 14:080:00000 00:000:00000 XYZ   1.5623  -3.2967   1.8951        70900513
 7839  A    1 L 88:214:00000 00:000:00000 XYZ   0.0000   0.0000   0.0000        78393402
 1234  A    1 L 00:001:00000 00:000:00000 XYZ 601.1170-470.9420  12.0000        12340001
 9999  A    1 L 00:001:00000 00:000:00000 UNE   3.0000   0.0000   0.0000        99990001
-SITE/ECCENTRICITY
"""


def test_station_solutions_and_eccentricities_give_the_optical_reference_point_at_a_date():
    solutions = slr.parse_sinex_stations(SINEX)
    assert list(solutions) == ["7090"] and len(solutions["7090"]) == 2
    at = datetime(2024, 4, 21, tzinfo=UTC)
    s = slr.station_at(solutions, "7090", at)
    assert s is not None and s.soln == "2", "the solution valid in 2024 is the second"
    early = slr.station_at(solutions, "7090", datetime(2000, 1, 1, tzinfo=UTC))
    assert early is not None and early.soln == "1"
    # Nine years of velocity: about 0.42 m in x from 2015.0 to 2024.3.
    years = (at - s.ref_epoch).total_seconds() / (365.25 * 86400)
    assert s.position_km(at)[0] * 1000 == pytest.approx(-2389007.771 + (-0.0468239683 * years), abs=1e-3)
    ecc = slr.parse_sinex_eccentricities(ECC)
    assert set(ecc) == {"7090", "7839", "1234"}, "UNE rows are not read; XYZ ones are"
    assert ecc["1234"][0].xyz_m.tolist() == [601.117, -470.942, 12.0], "values that run together are still three"
    stations = slr.Stations(solutions, ecc)
    assert stations.eccentricity_m("7090", at).tolist() == [1.5623, -3.2967, 1.8951]
    assert np.allclose(stations.position_km("7090", at), s.position_km(at) + np.array([1.5623, -3.2967, 1.8951]) / 1000)
    assert stations.position_km("0000", at) is None


def test_marini_murray_zenith_delay_is_about_two_and_a_half_metres_at_sea_level():
    zenith = slr.marini_murray_m(90.0, 1013.25, 288.15, 50.0, 30.0, 0.0, 0.532)
    assert 2.3 < float(zenith) < 2.6
    low = slr.marini_murray_m(20.0, 1013.25, 288.15, 50.0, 30.0, 0.0, 0.532)
    assert 2.6 < float(low) / float(zenith) < 3.1, "roughly 1/sin(e) at 20 degrees"
    high_site = slr.marini_murray_m(90.0, 700.0, 280.0, 30.0, 30.0, 3.0, 0.532)
    assert float(high_site) < float(zenith)


def test_the_range_model_recovers_a_satellite_placed_a_thousand_kilometres_overhead():
    """A station on the equator and a satellite 1,000 km above it in the Earth-fixed frame; the light-time
    iteration must return a one-way range of 1,000 km to centimetres, and the elevation 90 degrees."""
    station_itrf = np.array([6378.137, 0.0, 0.0])
    t0 = np.array(["2024-04-21T12:00:00"], dtype="datetime64[us]")
    sat_itrf = np.array([[7378.137, 0.0, 0.0]])

    def fn(times: np.ndarray) -> np.ndarray:
        n = np.asarray(times, dtype="datetime64[us]").size
        r = np.repeat(sat_itrf, n, axis=0)
        return slr.itrs_to_teme(r, np.zeros_like(r), times)[0]

    points = pd.DataFrame(
        {
            "t": pd.to_datetime(t0, utc=True),
            "tof_s": [2.0 * 1000.0 / slr.C_KM_S],
            "epoch_event": [2],
            "two_way": [True],
            "wavelength_nm": [532.0],
            "pressure_mbar": [1013.25],
            "temperature_k": [288.15],
            "humidity_pct": [50.0],
        }
    )
    result = slr.predicted_ranges(points, fn, station_itrf)
    assert result.predicted_km[0] == pytest.approx(1000.0, abs=0.02)
    assert result.elevation_deg[0] == pytest.approx(90.0, abs=0.2)
    assert 2.3 < result.tropo_m[0] < 2.6
    # Observed geometric range is c*tof/2 less the troposphere, so the residual is minus the troposphere here.
    assert result.residual_m[0] == pytest.approx(-result.tropo_m[0], abs=20.0)


def test_mean_altitude_from_mean_motion_and_the_summary_shape():
    assert reference_run.mean_altitude_km(np.array([15.3])) == pytest.approx(462.0, abs=15.0)
    assert reference_run.mean_altitude_km(np.array([12.8])) == pytest.approx(1336.0, abs=25.0)
    rows = []
    for k, lead in enumerate((6.0, 24.0, 72.0)):
        for s in range(3):
            rows.append(
                {
                    "mission": "jason-3",
                    "window": "quiet",
                    "set_epoch": pd.Timestamp("2024-04-20") + pd.Timedelta(hours=s),
                    "lead_h": lead,
                    "gap": False,
                    "manoeuvre": s == 2 and lead == 72.0,
                    "sgp4_error": 0,
                    "radial_km": 0.1,
                    "in_track_km": (k + 1) * 3.0 * (1 + s),
                    "cross_km": 0.2,
                    "radial_inside_1s": True,
                    "radial_inside_2s": True,
                    "in_track_inside_1s": True,
                    "in_track_inside_2s": True,
                    "cross_inside_1s": True,
                    "cross_inside_2s": True,
                    "storm_shift_km": np.nan,
                    "in_track_corrected_km": np.nan,
                    "altitude_km": 1336.0,
                    "altitude_band": "1000-1400 km",
                }
            )
    trials = pd.DataFrame(rows)
    summary = reference_run.summarise_trials(trials)
    band = summary["by_band"]["1000-1400 km"]["quiet"]
    assert band["n_sets"] == 3 and band["missions"] == ["jason-3"]
    assert band["by_lead_h"]["72"]["n"] == 2, "the manoeuvre trial is out"
    assert band["horizon"]["last_lead_h_within"] == 72.0 and band["horizon"]["first_lead_h_beyond"] is None
    assert "jason-3" in summary["by_mission"]
    statement = reference_run.population_statement([reference.MISSIONS["jason-3"]], list(reference.WINDOWS), trials)
    assert "1000-1400 km: Jason-3 (3 element sets" in statement and "4 windows" in statement
