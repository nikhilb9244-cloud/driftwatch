"""The calibration against precise orbits: the SP3 reader, the interpolation and its gaps, the residual's sign,
one trial per element set, the coverage arithmetic, the horizon rule, the manoeuvre detector, and the promise
that the held-out window is held out."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import satrec_from_kepler

from driftwatch.orbit.propagator import WGS72_MU_KM3_S2, propagate_satrecs
from driftwatch.risk.covariance import EmpiricalCovariance
from driftwatch.screening.ric import ric_basis, to_ric
from driftwatch.storm import precise

SP3 = """#dV2024  5 10  0  0  0.00000000       3 U+u   IGS20 FIT TUD
## 2313 432000.00000000    10.00000000 60440 0.0000000000000
+    1   L47  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
/* Created by: test
*  2024 05 10 00 00 00.00000000
PL47 -2208.1501534  6455.7666060   624.5215918 999999.999999
VL47  3630.8826499 -6212.8450706 75883.2399948 999999.999999
*  2024 05 10 00 00 10.00000000
PL47     0.0000000     0.0000000     0.0000000 999999.999999
VL47     0.0000000     0.0000000     0.0000000 999999.999999
*  2024 05 10 00 00 20.00000000
PL47 -2200.3630051  6441.7353817   776.1200171 999999.999999
VL47  4155.1700585 -7818.0720385 75708.8941386 999999.999999
EOF
"""


def test_parse_sp3_reads_km_and_dm_per_second_and_drops_the_absent_epoch():
    frame = precise.parse_sp3(SP3)
    assert len(frame) == 2, "the all-zero position is SP3's absent value and must stay a gap"
    assert frame["t"].iloc[0] == pd.Timestamp("2024-05-10T00:00:00") and frame["t"].iloc[1] == pd.Timestamp(
        "2024-05-10T00:00:20"
    )
    assert frame["x_km"].iloc[0] == pytest.approx(-2208.1501534)
    assert frame["vz_kms"].iloc[0] == pytest.approx(7.58832399948)  # decimetres per second in the file
    assert np.linalg.norm(frame[["vx_kms", "vy_kms", "vz_kms"]].iloc[0]) == pytest.approx(7.62, abs=0.05)


def test_sp3_epochs_in_gps_time_are_moved_to_utc():
    """ESA's files are in GPS time, 18 s ahead of UTC in 2024: read as UTC, the truth sits 137 km ahead.

    The first run of the benchmark showed exactly that at every lead. A file whose ``%c`` line
    says GPS is shifted through the leap-second table; a file with no ``%c`` line is taken as UTC.
    """
    gps = SP3.replace(
        "/* Created by: test", "%c M  cc GPS ccc cccc cccc cccc cccc ccccc ccccc ccccc ccccc\n/* Created by: test"
    )
    frame = precise.parse_sp3(gps)
    assert frame.attrs["time_system"] == "GPS"
    assert frame["t"].iloc[0] == pd.Timestamp("2024-05-09T23:59:42")
    assert precise.parse_sp3(SP3).attrs["time_system"] == "UTC"
    utc = pd.Series(pd.to_datetime(["2024-05-10T00:00:00"]).astype("datetime64[us]"))
    assert precise.sp3_epochs_to_utc(utc, "TAI").iloc[0] == pd.Timestamp("2024-05-09T23:59:23")
    with pytest.raises(ValueError, match="time system"):
        precise.sp3_epochs_to_utc(utc, "GLO")


def test_pod_file_for_day_takes_the_file_ending_that_day_at_its_newest_version():
    listing = [
        {"name": "SW_OPER_SP3ACOM_2__20240509T235942_20240510T235942_0201.ZIP", "path": "p1", "size": 1},
        {"name": "SW_OPER_SP3ACOM_2__20240509T235942_20240510T235942_0203.ZIP", "path": "p2", "size": 2},
        {"name": "SW_OPER_SP3ACOM_2__20240510T235942_20240511T235942_0203.ZIP", "path": "p3", "size": 3},
    ]
    assert precise.pod_file_for_day(listing, date(2024, 5, 10))["path"] == "p2"
    assert precise.pod_file_for_day(listing, date(2024, 5, 11))["path"] == "p3"
    assert precise.pod_file_for_day(listing, date(2024, 5, 12)) is None


def circular_table(
    t0: pd.Timestamp,
    n: int,
    step_s: float = 10.0,
    *,
    a_km: float = 6838.0,
    jump_at: int | None = None,
    jump_km: float = 0.0,
) -> pd.DataFrame:
    """A circular orbit tabulated like an SP3 file (treated as inertial by the tests that patch the rotation out)."""
    omega = np.sqrt(WGS72_MU_KM3_S2 / a_km**3)
    k = np.arange(n)
    a = np.full(n, a_km)
    if jump_at is not None:
        a[jump_at:] += jump_km
    theta = omega * k * step_s
    inc = np.radians(87.4)
    r = np.stack([a * np.cos(theta), a * np.sin(theta) * np.cos(inc), a * np.sin(theta) * np.sin(inc)], axis=1)
    speed = np.sqrt(WGS72_MU_KM3_S2 / a)
    v = np.stack(
        [-speed * np.sin(theta), speed * np.cos(theta) * np.cos(inc), speed * np.cos(theta) * np.sin(inc)], axis=1
    )
    t = (t0 + pd.to_timedelta(k * step_s, unit="s")).astype("datetime64[us]")
    return pd.DataFrame(
        {
            "t": t,
            "x_km": r[:, 0],
            "y_km": r[:, 1],
            "z_km": r[:, 2],
            "vx_kms": v[:, 0],
            "vy_kms": v[:, 1],
            "vz_kms": v[:, 2],
        }
    )


def test_the_precise_orbit_interpolates_to_centimetres_and_keeps_a_gap_a_gap(monkeypatch):
    t0 = pd.Timestamp("2024-05-10T00:00:00")
    table = circular_table(t0, 400)
    # A gap of a minute in the product: the segment breaks and nothing is interpolated across it.
    table = table[
        (table["t"] < t0 + pd.Timedelta(minutes=20)) | (table["t"] >= t0 + pd.Timedelta(minutes=21))
    ].reset_index(drop=True)
    orbit = precise.PreciseOrbit("A", 39452, table, [], ["synthetic"])
    assert len(orbit.segments) == 2
    at = np.array(
        [t0 + pd.Timedelta(seconds=125), t0 + pd.Timedelta(seconds=20 * 60 + 30), t0 + pd.Timedelta(minutes=30)],
        dtype="datetime64[us]",
    )
    r, v, covered = orbit.states_itrs(at)
    assert covered.tolist() == [True, False, True]
    truth = circular_table(t0, 2, step_s=125.0).iloc[1]  # the same orbit, 125 s on
    assert np.linalg.norm(r[0] - truth[["x_km", "y_km", "z_km"]].to_numpy(dtype=float)) < 1e-4  # under a decimetre
    assert np.isnan(r[1]).all()

    # With the rotation patched to the identity, the inertial velocity from differenced positions is the orbital one.
    monkeypatch.setattr(precise, "itrs_to_teme", lambda r, v, t: (r, v))
    r_t, v_t, ok = orbit.states_teme(at[[0, 2]])
    assert ok.all()
    assert np.linalg.norm(v_t[0]) == pytest.approx(np.sqrt(WGS72_MU_KM3_S2 / 6838.0), rel=1e-4)
    assert abs(float(r_t[0] @ v_t[0])) < 0.05  # circular: radial velocity is zero


def test_the_in_track_residual_is_positive_when_the_satellite_is_ahead_of_the_set():
    """The storm term's sign: truth minus prediction along the truth's velocity."""
    r_true = np.array([[6838.0, 0.0, 0.0]])
    v_true = np.array([[0.0, 7.6, 0.0]])
    r_sgp4 = r_true - np.array([[0.0, 1.0, 0.0]])  # the set put the satellite a kilometre behind
    delta = to_ric(ric_basis(r_true, v_true), r_true - r_sgp4)
    assert delta[0, 1] == pytest.approx(1.0) and abs(delta[0, 0]) < 1e-9 and abs(delta[0, 2]) < 1e-9


def designed_trials() -> pd.DataFrame:
    rows = []
    epochs = [
        pd.Timestamp("2024-05-06T01:00:00"),
        pd.Timestamp("2024-05-06T13:00:00"),
        pd.Timestamp("2024-05-07T01:00:00"),
    ]
    in_track = {6.0: [0.3, -0.4, 0.5], 24.0: [4.0, -6.0, 5.0], 72.0: [20.0, 40.0, -30.0]}
    for k, epoch in enumerate(epochs):
        for lead in (6.0, 24.0, 72.0):
            rows.append(
                {
                    "satellite": "A",
                    "norad_id": 39452,
                    "window": "storm",
                    "role": "storm",
                    "set_epoch": epoch,
                    "lead_h": lead,
                    "t": epoch + pd.Timedelta(hours=lead),
                    "gap": False,
                    "sgp4_error": 0,
                    "manoeuvre": False,
                    "through_disturbed": lead == 72.0,
                    "radial_km": 0.05 * (k + 1),
                    "in_track_km": in_track[lead][k],
                    "cross_km": 0.02,
                    "distance_km": abs(in_track[lead][k]),
                    "sigma_r_km": 0.1,
                    "sigma_i_km": 1.0 * lead / 6.0,
                    "sigma_c_km": 0.05,
                    "covariance_source": "empirical",
                    "storm_shift_km": 0.5 * in_track[lead][k],
                    "b_source": "history",
                }
            )
    frame = pd.DataFrame(rows)
    # One gap and one manoeuvre row, to be counted and excluded.
    gap = frame.iloc[[0]].copy()
    gap["set_epoch"] = pd.Timestamp("2024-05-08T01:00:00")
    gap["gap"] = True
    gap["in_track_km"] = np.nan
    burn = frame.iloc[[1]].copy()
    burn["set_epoch"] = pd.Timestamp("2024-05-08T13:00:00")
    burn["manoeuvre"] = True
    burn["in_track_km"] = 500.0
    frame = pd.concat([frame, gap, burn], ignore_index=True)
    frame["in_track_corrected_km"] = frame["in_track_km"] - frame["storm_shift_km"]
    for c, s in (("radial", "sigma_r_km"), ("in_track", "sigma_i_km"), ("cross", "sigma_c_km")):
        frame[f"{c}_inside_1s"] = frame[f"{c}_km"].abs() <= frame[s]
        frame[f"{c}_inside_2s"] = frame[f"{c}_km"].abs() <= 2.0 * frame[s]
    return frame


def test_summarise_counts_one_trial_per_set_excludes_gaps_and_burns_and_states_the_horizon():
    summary = precise.summarise(designed_trials())
    w = summary["windows"]["storm"]
    assert summary["trial"].startswith("one element set")
    assert w["n_sets"] == 5 and w["n_excluded_gap"] == 1 and w["n_excluded_manoeuvre"] == 1
    six = w["by_lead_h"]["6"]
    assert six["n"] == 3 and six["n_sets"] == 3, "three sets, three trials at this lead; the gap and the burn are out"
    assert six["in_track"]["median_km"] == pytest.approx(0.4)
    assert six["in_track"]["inside_1_sigma"] == pytest.approx(
        1.0
    )  # sigma is 1 km at 6 h and every residual is under it
    day = w["by_lead_h"]["24"]
    assert day["in_track"]["inside_1_sigma"] == pytest.approx(1 / 3)  # sigma 4 km: 4.0 inside, 6 and 5 outside
    assert day["in_track"]["inside_2_sigma"] == pytest.approx(1.0)
    # The storm term halves every residual by design, so the improvement is 50 % and every trial improves.
    assert (
        day["storm_term"]["improvement"] == pytest.approx(0.5) and day["storm_term"]["share_of_trials_improved"] == 1.0
    )
    # The horizon: the 95th percentile is within 25 km at 24 h and beyond it at 72 h.
    assert w["horizon"]["last_lead_h_within"] == 24.0 and w["horizon"]["first_lead_h_beyond"] == 72.0
    assert w["horizon"]["quantile_km_there"] > 25.0
    assert w["by_lead_h"]["72"]["through_disturbed"]["n"] == 3


def test_the_manoeuvre_detector_flags_a_step_in_the_orbit_mean_semi_major_axis(monkeypatch):
    monkeypatch.setattr(precise, "itrs_to_teme", lambda r, v, t: (r, v))
    t0 = pd.Timestamp("2024-05-10T00:00:00")
    n = 8640  # a day at ten seconds
    quiet = precise.PreciseOrbit("A", 39452, circular_table(t0, n), [], ["synthetic"])
    assert precise.manoeuvre_intervals_from_orbit(quiet) == []
    burned = precise.PreciseOrbit("A", 39452, circular_table(t0, n, jump_at=n // 2, jump_km=0.1), [], ["synthetic"])
    intervals = precise.manoeuvre_intervals_from_orbit(burned)
    assert len(intervals) == 1
    lo, hi = intervals[0]
    assert lo <= t0 + pd.Timedelta(hours=12) <= hi
    assert hi - lo < pd.Timedelta(hours=8)  # the detector's resolution is a couple of orbits either side


def test_the_held_out_window_is_held_out_and_the_windows_do_not_overlap():
    names = [w.name for w in precise.WINDOWS]
    assert names == ["quiet", "storm", "held-out"]
    held = precise.WINDOWS[-1]
    assert held.role == "held-out"
    for w in precise.WINDOWS[:-1]:
        assert w.truth_to < held.sets_from, "nothing the held-out window sees is seen by the tuning-visible windows"
    quiet, storm = precise.WINDOWS[0], precise.WINDOWS[1]
    assert quiet.truth_to <= storm.sets_from + timedelta(days=1)
    assert storm.disturbed is not None and storm.sets_from < storm.disturbed[0] < storm.sets_to
    # The tuning that exists is fitted from history that ends where each window's sets begin.
    assert precise.COVARIANCE_HISTORY_DAYS > 0 and precise.COEFFICIENT_HISTORY_DAYS > 0


def test_thruster_intervals_separate_orbit_control_thrust_from_attitude_pulses():
    """A run of orbit-control force is a manoeuvre; thruster on-time with no such force is an attitude pulse."""
    t0 = pd.Timestamp("2024-05-10T00:00:00")
    n = 3600 * 3
    t = (t0 + pd.to_timedelta(np.arange(n), unit="s")).astype("datetime64[us]")
    on = np.zeros(n)
    force = np.zeros(n)
    # Two attitude bursts of a few seconds, an hour apart.
    on[600:606] = 0.8
    on[4200:4205] = 0.8
    # One orbit manoeuvre: 40 s of orbit-control thrust with a 20 s pause in it.
    on[7200:7220] = 1.0
    on[7240:7260] = 1.0
    force[7200:7220] = 100.0
    force[7240:7260] = 100.0
    frame = pd.DataFrame({"t": t, "on_time_s": on, "force_mn": force})
    intervals, pulses, thrust_s = precise.thruster_intervals(frame)
    assert pulses == 2 and thrust_s == pytest.approx(40.0)
    assert intervals == [(pd.Timestamp(t[7200]), pd.Timestamp(t[7259]))]
    assert precise.thruster_intervals(frame.iloc[0:0]) == ([], 0, 0.0)
    assert (
        precise.dyn_file_for_day(
            [
                {"name": "SW_OPER_SC_ADYN_1B_20240510T000000_20240510T235959_0601.CDF.ZIP", "path": "a", "size": 1},
                {"name": "SW_OPER_SC_ADYN_1B_20240510T000000_20240510T235959_0602.CDF.ZIP", "path": "b", "size": 1},
            ],
            date(2024, 5, 10),
        )["path"]
        == "b"
    )


def test_an_unknown_ephemeris_frame_is_refused_by_name():
    r = np.array([[6838.0, 0.0, 0.0]])
    v = np.array([[0.0, 7.6, 0.0]])
    t = np.array(["2024-05-10T00:00:00"], dtype="datetime64[us]")
    assert np.allclose(precise._rotate_to_teme("TEME", r, v, t), r)
    with pytest.raises(ValueError, match="unsupported ephemeris frame"):
        precise._rotate_to_teme("MARS", r, v, t)


def test_a_trial_against_a_truth_built_from_its_own_set_has_no_residual_and_the_record_excludes_it():
    """End to end on one element set: the truth is SGP4's own path tabulated in TEME, so the residual is the
    interpolation error; then a published manoeuvre inside the arc before the epoch excludes every lead while the
    detection, which sees no step in the orbit, flags none -- and the cross-check records the disagreement."""
    from datetime import datetime

    epoch = datetime(2024, 5, 6, 12, 0, 0)
    sat = satrec_from_kepler(90001, epoch, 6838.0, 0.001, np.radians(87.4), 0.3, 0.1, 0.2, bstar=1e-5)
    row = {
        "norad_id": 90001,
        "name": "DESIGNED",
        "epoch": pd.Timestamp(epoch, tz="UTC"),
        "mean_motion": sat.no_kozai * 1440.0 / (2 * np.pi),
        "eccentricity": sat.ecco,
        "inclination_deg": np.degrees(sat.inclo),
        "raan_deg": np.degrees(sat.nodeo),
        "arg_perigee_deg": np.degrees(sat.argpo),
        "mean_anomaly_deg": np.degrees(sat.mo),
        "bstar": sat.bstar,
        "mean_motion_dot": 0.0,
        "mean_motion_ddot": 0.0,
    }
    sets = pd.DataFrame([row])
    # The truth: the same set propagated every ten seconds over the trial's leads, in TEME.
    leads = (6.0, 24.0)
    grid = pd.to_datetime(epoch) + pd.to_timedelta(np.arange(0, 25 * 3600, 10), unit="s")
    state = propagate_satrecs([sat], np.array([90001]), grid.to_numpy(dtype="datetime64[us]"))
    table = pd.DataFrame(
        {
            "t": grid.astype("datetime64[us]"),
            "x_km": state.r_teme[0][:, 0],
            "y_km": state.r_teme[0][:, 1],
            "z_km": state.r_teme[0][:, 2],
            "vx_kms": state.v_teme[0][:, 0],
            "vy_kms": state.v_teme[0][:, 1],
            "vz_kms": state.v_teme[0][:, 2],
        }
    )
    orbit = precise.PreciseOrbit("X", 90001, table, [], ["synthetic"], frame="TEME")
    window = precise.BenchmarkWindow(
        "designed",
        "control",
        precise.parse_utc("2024-05-06T00:00:00Z"),
        precise.parse_utc("2024-05-07T00:00:00Z"),
        None,
        "",
    )
    inputs = precise.SatelliteInputs(
        "X", 90001, sets, sets, EmpiricalCovariance(), "default:leo", None, "payload", "leo"
    )
    trials = precise.satellite_trials(inputs, orbit, window, None, leads_hours=leads)
    assert len(trials) == 2 and trials["manoeuvre_source"].eq("detected").all()
    assert not trials["gap"].any() and not trials["manoeuvre"].any()
    assert trials["distance_km"].abs().max() < 0.01, "the truth is the set's own path; only interpolation remains"
    assert trials["sigma_i_km"].gt(0).all() and trials["in_track_inside_2s"].all()
    assert trials["storm_shift_km"].isna().all() and trials["b_source"].eq("none").all()

    # A published burn eighteen hours before the epoch is inside the tracking arc the set was fitted from.
    burn = [(pd.Timestamp(epoch) - pd.Timedelta(hours=18), pd.Timestamp(epoch) - pd.Timedelta(hours=17, minutes=58))]
    with_record = precise.satellite_trials(inputs, orbit, window, None, leads_hours=leads, published=burn)
    assert with_record["manoeuvre"].all() and with_record["manoeuvre_source"].eq("operator-record").all()
    assert not with_record["manoeuvre_detected"].any()
    summary = precise.summarise(with_record)["windows"]["designed"]
    assert summary["manoeuvres"]["source"] == ["operator-record"]
    assert summary["manoeuvres"]["n_sets_excluded_all_leads"] == 1
    assert summary["manoeuvres"]["cross_check"] == {"both": 0, "record_only": 2, "detection_only": 0, "neither": 0}
    assert summary["by_lead_h"] == {}, "every trial is excluded, so nothing is summarised"

    # The same burn two days before the epoch is outside the arc and excludes nothing.
    old_burn = [
        (
            pd.Timestamp(epoch) - pd.Timedelta(days=2),
            pd.Timestamp(epoch) - pd.Timedelta(days=2) + pd.Timedelta(minutes=2),
        )
    ]
    assert not precise.satellite_trials(inputs, orbit, window, None, leads_hours=leads, published=old_burn)[
        "manoeuvre"
    ].any()
