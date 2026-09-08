"""The dSGP4 evaluation: our element sets become dsgp4 objects that propagate like the sgp4 library, the hybrid starts
as SGP4 and learns a constant offset, and the summaries and the adoption rule do what they say."""

from __future__ import annotations

import hashlib
from dataclasses import replace
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
                "b_source": "history",
                "in_track_corrected_km": 0.05 * k,
            }
            for k, lead in enumerate(precise.LEADS_HOURS)
        ]
    )
    sets = pd.DataFrame([ROW])
    items = dsgp4_eval.trial_sets(trials, sets, {("swarm-a", "quiet"): orbit})
    assert len(items) == 1 and items[0].mission == "swarm-a"
    exclusions = {("swarm-a", "quiet"): dsgp4_eval.TrainingExclusions("synthetic-record", ())}
    omms, tsince, states = dsgp4_eval.training_samples(items, exclusions=exclusions, step_min=720.0)
    assert len(omms) in (13, 14) and states.shape[1] == 6 and tsince[0] == 720.0, (
        "the last hour sits at the table's edge"
    )
    res = dsgp4_eval.residuals_at_leads(items, lambda o, t: dsgp4_eval.dsgp4_states(o, t, gravity="wgs-72"), method="d")
    assert len(res) == len(precise.LEADS_HOURS)
    assert res["in_track_km"].abs().max() < 0.01, "the truth is the set's own path; dsgp4 with WGS72 reproduces it"
    both = dsgp4_eval.storm_term_residuals(trials, items)
    unsupported = dsgp4_eval.storm_term_residuals(trials.assign(b_source="bstar"), items)
    assert set(unsupported["method"]) == {"sgp4 (library, WGS72)"}, "B-star is not a supported storm correction"
    assert set(both["method"]) == {"sgp4 (library, WGS72)", "sgp4 + storm term (observed ap)"}
    summary = dsgp4_eval.summarise(pd.concat([res, both], ignore_index=True))
    assert summary["quiet"]["24"]["d"]["n"] == 1
    improvement = dsgp4_eval.improvement_over_plain(summary)
    assert improvement["quiet"]["24"]["sgp4 + storm term (observed ap)"] == pytest.approx(0.5)


def test_historical_checkpoint_rule_requires_both_inspected_evaluation_windows():
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
    assert not dsgp4_eval.recommendation({"august": {"6": {"m": 0.9}}}, "m")["adopt"], "both windows are required"
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
    assert "over three days" in page and "local adaptation" in page
    assert "historical checkpoint rule" in page and "not a new adoption gate" in page


def _training_item():
    orbit = _orbit_from_set(ROW)
    return dsgp4_eval.TrialSet(
        "swarm-a",
        "quiet",
        ROW["epoch"].tz_convert(None),
        dsgp4_eval.omm_from_row(ROW),
        orbit,
        build_satrecs(pd.DataFrame([ROW]))[0],
        "synthetic-elements",
    )


def test_hourly_training_excludes_post_burn_arcs_and_preepoch_burns():
    item = _training_item()
    burn = item.epoch + pd.Timedelta(minutes=90)
    policy = dsgp4_eval.TrainingExclusions("esa-record", ((burn, burn + pd.Timedelta(minutes=1)),))
    result = dsgp4_eval.prepare_training_samples(
        [item],
        exclusions={(item.mission, item.window): policy},
        horizon_min=240,
    )
    assert result.tsince_min.tolist() == [60.0]
    assert result.manifest["manoeuvre"].tolist() == [False, True, True, True]
    assert len(result.sha256) == 64
    earlier = item.epoch - pd.Timedelta(hours=23)
    policy = replace(policy, intervals=((earlier, earlier),))
    result = dsgp4_eval.prepare_training_samples(
        [item],
        exclusions={(item.mission, item.window): policy},
        horizon_min=120,
    )
    assert not len(result.omms) and result.states.shape == (0, 6)
    boundary = item.epoch - pd.Timedelta(hours=24)
    policy = replace(policy, intervals=((boundary, boundary),))
    result = dsgp4_eval.prepare_training_samples(
        [item],
        exclusions={(item.mission, item.window): policy},
        horizon_min=60,
    )
    assert result.manifest["manoeuvre"].all(), "the same inclusive 24-hour boundary as evaluation"


def test_training_requires_both_truth_coverage_and_zero_sgp4_error(monkeypatch):
    item = _training_item()

    class SyntheticErrors:
        def sgp4_array(self, jd, fraction):
            return np.array([0, 6, 0]), np.ones((3, 3)), np.ones((3, 3))

    item = replace(item, sgp4_record=SyntheticErrors())
    monkeypatch.setattr(
        dsgp4_eval, "truth_at", lambda *args: (np.ones((3, 3)), np.ones((3, 3)), np.array([True, True, False]))
    )
    result = dsgp4_eval.prepare_training_samples(
        [item],
        exclusions={(item.mission, item.window): dsgp4_eval.TrainingExclusions("esa-record", ())},
        horizon_min=180,
    )
    assert result.tsince_min.tolist() == [60.0]
    assert result.manifest["sgp4_error"].tolist() == [0, 6, 0]
    assert result.manifest["truth_covered"].tolist() == [True, True, False]


def test_held_out_samples_and_missing_policies_fail_before_truth_access(monkeypatch):
    item = _training_item()

    def no_truth(*args):
        pytest.fail("held-out truth must not be accessed for training")

    monkeypatch.setattr(dsgp4_eval, "truth_at", no_truth)
    with pytest.raises(ValueError, match="quiet and storm"):
        dsgp4_eval.prepare_training_samples([replace(item, window="held-out")], exclusions={})
    with pytest.raises(ValueError, match="No training exclusion"):
        dsgp4_eval.prepare_training_samples([item], exclusions={})


def test_authoritative_empty_records_are_distinct_from_missing_records_and_flags_are_crosschecked():
    frame = pd.DataFrame(
        [
            {
                "mission": "a",
                "window": "quiet",
                "manoeuvre_source": "ids-ssalto-record",
                "manoeuvre": False,
                "set_epoch": pd.Timestamp("2000-01-01"),
                "lead_h": 6.0,
            }
        ]
    )
    provenance = {"coverage_status": "published_event_registry", "days_missing": []}
    coverage = {"a": {"quiet": {"manoeuvres_recorded": [], "manoeuvre_record_provenance": provenance}}}
    policies = dsgp4_eval.training_exclusions_from_benchmark(frame, coverage)
    assert policies[("a", "quiet")].intervals == ()
    with pytest.raises(ValueError, match="Missing authoritative"):
        dsgp4_eval.training_exclusions_from_benchmark(
            frame,
            {
                "a": {
                    "quiet": {
                        "manoeuvres_recorded": None,
                        "manoeuvre_record_provenance": provenance,
                    }
                }
            },
        )
    with pytest.raises(ValueError, match="Incomplete authoritative"):
        dsgp4_eval.training_exclusions_from_benchmark(
            frame,
            {
                "a": {
                    "quiet": {
                        "manoeuvres_recorded": [],
                        "manoeuvre_record_provenance": {**provenance, "days_missing": ["2000-01-01"]},
                    }
                }
            },
        )
    coverage["a"]["quiet"]["manoeuvres_recorded"] = [["2000-01-01T02:00:00", "2000-01-01T02:01:00"]]
    with pytest.raises(ValueError, match="exclusion mismatch"):
        dsgp4_eval.training_exclusions_from_benchmark(frame, coverage)


def test_checkpoint_selection_and_persistence_use_a_fixed_model_objective(tmp_path):
    import torch

    class ToyModel(torch.nn.Module):
        normalization_R = 1.0
        normalization_V = 1.0

        def __init__(self):
            super().__init__()
            self.offset = torch.nn.Parameter(torch.tensor(0.0, dtype=torch.float64))

        def forward(self, objects, times):
            return self.offset.expand(len(times), 6)

    model = ToyModel()
    omms = [object()] * 5
    times, targets = np.arange(5, dtype=float), np.ones((5, 6))
    path = tmp_path / "checkpoint.pt"
    record = dsgp4_eval.train_hybrid(
        model,
        omms,
        times,
        targets,
        epochs=4,
        batch_size=3,
        learning_rate=0.1,
        checkpoint_path=path,
        sample_sha256="synthetic-sample",
    )
    actual = dsgp4_eval.fixed_objective(model, omms, times, targets, batch_size=2)
    assert record.selected_loss == pytest.approx(actual)
    assert record.selected_loss == pytest.approx(min([record.initial_loss, *record.losses]))
    assert record.selected_loss == pytest.approx(record.checkpoint_reloaded_loss)
    assert record.checkpoint_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert record.sample_sha256 == "synthetic-sample"
    assert record.online_losses != record.losses, "changing-model proxies are retained but do not select checkpoints"


def test_paired_comparisons_report_spacecraft_and_exact_shared_denominators():
    rows = []
    for mission, epoch, raw, corrected in (("a", "2000-01-01", 1, 2), ("b", "2000-01-02", 10, 5)):
        for method, value in (("sgp4 (library, WGS72)", raw), ("hybrid", corrected)):
            rows.append(
                {
                    "mission": mission,
                    "window": "held-out",
                    "set_epoch": pd.Timestamp(epoch),
                    "lead_h": 24.0,
                    "method": method,
                    "in_track_km": value,
                    "radial_km": 0.0,
                    "cross_km": 0.0,
                }
            )
    frame = pd.DataFrame(rows)
    result = dsgp4_eval.paired_comparison_cells(frame)
    assert result["n_paired"].tolist() == [2, 1, 1]
    assert result[result["scope"].eq("pooled")]["method_median_abs_in_track_km"].iloc[0] == 3.5
    assert dsgp4_eval.summarise_by_mission(frame)["a"]["held-out"]["24"]["hybrid"]["n"] == 1
    sparse = dsgp4_eval.paired_comparison_cells(frame.iloc[:-1])
    pooled = sparse[sparse["scope"].eq("pooled")].iloc[0]
    assert pooled.n_paired == 1 and pooled.n_plain_source == 2 and pooled.n_method_source == 1
    assert pooled.plain_median_abs_in_track_km == 1, "raw median is restricted to the same paired set"


def test_corrected_runner_rejects_a_new_window_before_access_or_output(tmp_path):
    from driftwatch.storm import dsgp4_run

    with pytest.raises(ValueError, match="existing quiet/May/October/August"):
        dsgp4_run.run_corrected_evaluation(
            pd.DataFrame({"window": ["new-uninspected-window"]}),
            pd.DataFrame(),
            {},
            {},
            tmp_path / "run",
        )
    assert not (tmp_path / "run").exists()
