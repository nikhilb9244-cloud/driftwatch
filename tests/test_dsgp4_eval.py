"""The dSGP4 evaluation: our element sets become dsgp4 objects that propagate like the sgp4 library, the hybrid starts
as SGP4 and learns a constant offset, and the summaries and the adoption rule do what they say."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("dsgp4")
pytest.importorskip("torch")

from driftwatch.orbit.propagator import build_satrecs, propagate_satrecs  # noqa: E402
from driftwatch.storm import dsgp4_eval, precise  # noqa: E402

ROW = {
    "norad_id": 39452,
    "name": "SWARM A",
    "object_id": "2013-067B",
    "epoch": pd.Timestamp("2024-04-20T14:16:04.793952", tz="UTC"),
    "mean_motion": 15.31453865,
    "eccentricity": 0.0002337,
    "inclination_deg": 87.3466,
    "raan_deg": 343.8225,
    "arg_perigee_deg": 81.5466,
    "mean_anomaly_deg": 278.6049,
    "bstar": 0.00042182,
    "mean_motion_dot": 0.00012844,
    "mean_motion_ddot": 0.0,
}


def test_an_element_set_becomes_a_dsgp4_object_that_propagates_like_the_library():
    omm = dsgp4_eval.omm_from_row(pd.Series(ROW))
    tsince = np.array([60.0, 1440.0, 10080.0])
    states = dsgp4_eval.dsgp4_states([omm] * 3, tsince, gravity="wgs-72")
    sat = build_satrecs(pd.DataFrame([ROW]))
    epoch = ROW["epoch"].tz_convert(None)
    times = (epoch + pd.to_timedelta(tsince, unit="min")).to_numpy(dtype="datetime64[us]")
    ref = propagate_satrecs(sat, np.array([39452]), times)
    for k in range(3):
        assert np.linalg.norm(states[k, :3] - ref.r_teme[0][k]) < 0.005, (
            "dsgp4 with WGS72 agrees with the library to metres"
        )
    wgs84 = dsgp4_eval.dsgp4_states([omm] * 3, tsince, gravity="wgs-84")
    assert 0.01 < np.linalg.norm(wgs84[2, :3] - ref.r_teme[0][2]) < 1.0, "the constants differ by decametres at a week"


def test_the_zero_started_hybrid_is_sgp4_and_learns_a_constant_offset():
    omm = dsgp4_eval.omm_from_row(pd.Series(ROW))
    model = dsgp4_eval.new_hybrid(hidden_size=8)
    tsince = np.linspace(60.0, 10080.0, 12)
    before = dsgp4_eval.hybrid_states(model, [omm] * 12, tsince)
    base = dsgp4_eval.dsgp4_states([omm] * 12, tsince, gravity="wgs-84")
    assert np.allclose(before, base, atol=1e-6), "zero corrections: the hybrid starts exactly at dsgp4"
    # A truth that is dsgp4 plus a constant 2 km along x: the output network can learn it.
    truth = base.copy()
    truth[:, 0] += 2.0
    record = dsgp4_eval.train_hybrid(model, [omm] * 12, tsince, truth, epochs=200, batch_size=12, learning_rate=1e-3)
    assert record.n_samples == 12 and len(record.losses) == 200
    assert record.losses[-1] < record.losses[0] * 0.5, "the loss fell"
    after = dsgp4_eval.hybrid_states(model, [omm] * 12, tsince)
    assert np.median(np.abs(after[:, 0] - truth[:, 0])) < 1.5, "most of the 2 km offset is learnt"


def _orbit_from_set(row: dict) -> precise.PreciseOrbit:
    """The set's own SGP4 path tabulated in TEME, so the residual against it is the interpolation error."""
    sat = build_satrecs(pd.DataFrame([row]))
    epoch = row["epoch"].tz_convert(None)
    grid = (epoch + pd.to_timedelta(np.arange(0, 7 * 86400 + 660, 60), unit="s")).to_numpy(dtype="datetime64[us]")
    state = propagate_satrecs(sat, np.array([row["norad_id"]]), grid)
    table = pd.DataFrame(
        {
            "t": grid,
            "x_km": state.r_teme[0][:, 0],
            "y_km": state.r_teme[0][:, 1],
            "z_km": state.r_teme[0][:, 2],
            "vx_kms": state.v_teme[0][:, 0],
            "vy_kms": state.v_teme[0][:, 1],
            "vz_kms": state.v_teme[0][:, 2],
        }
    )
    return precise.PreciseOrbit("A", 39452, table, [], ["synthetic"], frame="TEME")


def test_trial_sets_and_residuals_at_leads_follow_the_benchmark_frame():
    orbit = _orbit_from_set(ROW)
    trials = pd.DataFrame(
        [
            {
                "mission": "swarm-a",
                "window": "quiet",
                "norad_id": 39452,
                "set_epoch": ROW["epoch"].tz_convert(None),
                "lead_h": lead,
                "gap": False,
                "manoeuvre": False,
                "sgp4_error": 0,
                "radial_km": 0.0,
                "in_track_km": 0.1 * k,
                "cross_km": 0.0,
                "storm_shift_km": 0.05 * k,
                "in_track_corrected_km": 0.05 * k,
            }
            for k, lead in enumerate(precise.LEADS_HOURS)
        ]
    )
    sets = pd.DataFrame([ROW])
    items = dsgp4_eval.trial_sets(trials, sets, {("swarm-a", "quiet"): orbit})
    assert len(items) == 1 and items[0].mission == "swarm-a"
    omms, tsince, states = dsgp4_eval.training_samples(items, step_min=720.0)
    assert len(omms) in (13, 14) and states.shape[1] == 6 and tsince[0] == 720.0, (
        "the last hour sits at the table's edge"
    )
    res = dsgp4_eval.residuals_at_leads(items, lambda o, t: dsgp4_eval.dsgp4_states(o, t, gravity="wgs-72"), method="d")
    assert len(res) == len(precise.LEADS_HOURS)
    assert res["in_track_km"].abs().max() < 0.01, "the truth is the set's own path; dsgp4 with WGS72 reproduces it"
    both = dsgp4_eval.storm_term_residuals(trials, items)
    assert set(both["method"]) == {"sgp4 (library, WGS72)", "sgp4 + storm term (observed ap)"}
    summary = dsgp4_eval.summarise(pd.concat([res, both], ignore_index=True))
    assert summary["quiet"]["24"]["d"]["n"] == 1
    improvement = dsgp4_eval.improvement_over_plain(summary)
    assert improvement["quiet"]["24"]["sgp4 + storm term (observed ap)"] == pytest.approx(0.5)


def test_the_adoption_rule_needs_the_held_out_storms_to_improve():
    improvement = {
        "quiet": {"6": {"m": 0.5}},
        "held-out": {"6": {"m": 0.1}, "24": {"m": 0.2}, "72": {"m": -0.05}},
        "august": {"6": {"m": 0.3}, "24": {"m": 0.1}},
    }
    verdict = dsgp4_eval.recommendation(improvement, "m")
    assert verdict["adopt"] and verdict["held-out"]["leads_improved"] == 2 and verdict["august"]["leads"] == 2
    worse = {"held-out": {"6": {"m": -0.1}, "24": {"m": 0.2}, "72": {"m": -0.3}}, "august": {"6": {"m": 0.3}}}
    assert not dsgp4_eval.recommendation(worse, "m")["adopt"]
    assert not dsgp4_eval.recommendation({"quiet": {"6": {"m": 0.9}}}, "m")["adopt"], "no held-out result, no adoption"
    page = dsgp4_eval.to_markdown(
        {
            "dsgp4_version": "1.3.0",
            "torch_version": "x",
            "what_was_done": "test",
            "training": {
                "m": {
                    "n_samples": 1,
                    "n_sets": 1,
                    "epochs": 1,
                    "batch_size": 1,
                    "learning_rate": 1e-3,
                    "losses": [1.0, 0.5],
                    "seconds": 1.0,
                }
            },
            "summary": {
                "held-out": {
                    "6": {
                        "sgp4 (library, WGS72)": {"n": 1, "in_track_median_km": 1.0},
                        "m": {"n": 1, "in_track_median_km": 0.9},
                    }
                }
            },
            "methods": ["sgp4 (library, WGS72)", "m"],
            "plain": "sgp4 (library, WGS72)",
            "improvement": {"held-out": {"6": {"m": 0.1}}},
            "recommendations": [verdict],
        },
        datetime(2026, 9, 7, tzinfo=UTC),
    )
    assert "operator's predictions in a quiet week" in page and "adopt only if the held-out storms improve" in page
