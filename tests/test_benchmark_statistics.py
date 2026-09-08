"""Statistical failure cases: interpolation, missing leads, mixtures and clustered deletions."""

import json

import numpy as np
import pandas as pd
import pytest

from driftwatch.storm import benchmark_statistics as stats


def trials(values, leads=(6.0,), missions=None):
    rows = []
    for index, value in enumerate(values):
        for lead in leads:
            rows.append(
                {
                    "mission": missions[index] if missions else "one",
                    "window": "synthetic",
                    "altitude_band": "test-band",
                    "set_epoch": pd.Timestamp("2000-01-01") + pd.Timedelta(hours=index),
                    "lead_h": lead,
                    "in_track_km": value,
                    "radial_km": value,
                    "cross_km": value,
                    "sigma_i_km": 1.0,
                    "sigma_r_km": 1.0,
                    "sigma_c_km": 1.0,
                    "gap": False,
                    "manoeuvre": False,
                    "sgp4_error": 0,
                }
            )
    return pd.DataFrame(rows)


def test_interpolated_quantile_can_pass_when_less_than_95_percent_of_trials_pass():
    result = stats.summarise_group(trials([0.0] * 17 + [38.0]), leads_hours=[6])
    lead = result["by_lead_h"]["6"]
    assert lead["exceedance_count"] == 1
    assert lead["inside_tolerance_fraction"] == pytest.approx(17 / 18)
    assert lead["components"]["in_track"]["quantile_abs_km"] == pytest.approx({"linear": 5.7, "inverted_cdf": 38})
    assert result["horizon"]["termination"] == "threshold_failure"
    assert result["horizon"]["last_lead_h_within"] is None
    assert result["horizons_by_criterion"]["linear_quantile"]["termination"] == "longest_tested_lead"
    assert result["horizons_by_criterion"]["inverted_cdf_quantile"]["termination"] == "threshold_failure"


def test_tolerance_equality_is_inside_and_exactly_95_percent_passes():
    result = stats.summarise_group(trials([25.0] * 19 + [26.0]), leads_hours=[6])
    assert result["by_lead_h"]["6"]["inside_tolerance_count"] == 19
    assert result["horizon"]["termination"] == "longest_tested_lead"


def test_missing_or_excluded_leads_are_censored_instead_of_failures_or_seven_day_success():
    frame = trials([1, 2], leads=[6, 12, 24])
    frame.loc[frame["lead_h"].eq(12), "manoeuvre"] = True
    result = stats.summarise_group(frame, leads_hours=[6, 12, 24])
    assert result["horizon"]["termination"] == "coverage_censored"
    assert result["horizon"]["last_lead_h_within"] == 6
    assert result["horizon"]["first_lead_h_beyond"] is None
    assert result["horizon"]["last_observed_lead_h"] == 24
    assert result["by_lead_h"]["12"]["n"] == 0
    assert result["by_lead_h"]["12"]["n_total"] == 2
    assert result["by_lead_h"]["12"]["mission_counts_total"] == {"one": 2}
    tail = stats.summarise_group(frame[frame["lead_h"].eq(6)], leads_hours=[6, 12])
    assert tail["horizon"]["termination"] == "coverage_censored"
    empty = stats.summarise_group(frame.iloc[:0], leads_hours=[6, 12])
    assert empty["horizon"]["last_observed_lead_h"] is None


def test_failure_bracket_stops_at_first_failure_even_if_later_residuals_recover():
    frame = trials([1], leads=[6, 12, 24])
    frame.loc[frame["lead_h"].eq(12), "in_track_km"] = 30
    result = stats.summarise_group(frame, leads_hours=[6, 12, 24])
    assert result["horizon"]["last_lead_h_within"] == 6
    assert result["horizon"]["first_lead_h_beyond"] == 12
    assert result["horizon"]["termination"] == "threshold_failure"


def test_disaggregated_coverage_exposes_a_pooled_mixture_and_ignores_stale_flags():
    frame = trials([0.21] * 19 + [0.29] * 18, missions=["jason"] * 19 + ["sentinel"] * 18)
    frame.loc[frame["mission"].eq("jason"), "sigma_i_km"] = 0.26
    frame.loc[frame["mission"].eq("sentinel"), "sigma_i_km"] = 0.038
    frame["sigma_c_km"] = 0.01
    frame["in_track_inside_2s"] = True  # Recompute from residual and sigma, not a saved convenience flag.
    summary = stats.summarise_trials(frame, leads_hours=[6], include_sensitivities=False)
    pooled = summary["by_band"]["test-band"]["synthetic"]["by_lead_h"]["6"]
    assert pooled["components"]["in_track"]["coverage"]["inside_2_sigma_count"] == 19
    assert pooled["components"]["cross"]["coverage"]["inside_2_sigma_count"] == 0
    for mission, expected in (("jason", 1.0), ("sentinel", 0.0)):
        cell = summary["by_mission"][mission]["synthetic"]["by_lead_h"]["6"]
        assert cell["components"]["in_track"]["coverage"]["inside_2_sigma_fraction"] == expected


def test_deletion_removes_whole_set_trajectory_and_preserves_grid_when_a_mission_disappears():
    frame = trials([1, 40], leads=[6, 12], missions=["a", "b"])
    frame.loc[frame["lead_h"].eq(6), "in_track_km"] = 1
    result = stats.summarise_group(frame, leads_hours=[6, 12])
    sensitivity = result["sensitivities"]
    assert sensitivity["leave_one_set_out"]["n_deletions"] == 2
    change = next(c for c in sensitivity["leave_one_set_out"]["changes"] if c["deleted_set"]["mission"] == "b")
    assert change["horizons_by_criterion"]["empirical_coverage"]["last_lead_h_within"] == 12
    frame.loc[frame["mission"].eq("a") & frame["lead_h"].eq(12), "gap"] = True
    result = stats.summarise_group(frame, leads_hours=[6, 12])
    horizon = result["sensitivities"]["leave_one_spacecraft_out"]["b"]["empirical_coverage"]
    assert horizon["termination"] == "coverage_censored"
    assert horizon["last_lead_h_within"] == 6


def test_invalid_residual_and_sigma_pairs_keep_explicit_denominators_and_json_is_finite():
    frame = trials([0.0, 1.0, np.nan, 3.0])
    frame["sigma_i_km"] = [0.0, np.nan, 1.0, -1.0]
    result = stats.summarise_group(frame, leads_hours=[6])
    lead = result["by_lead_h"]["6"]
    assert lead["n_usable"] == 4 and lead["n"] == 3
    coverage = lead["components"]["in_track"]["coverage"]
    assert coverage["n"] == 1 and coverage["n_invalid_pairs"] == 3
    assert coverage["n_zero_sigma"] == 1 and coverage["inside_2_sigma_count"] == 1
    json.dumps(result, allow_nan=False)


def test_duplicate_set_leads_and_unplanned_leads_are_rejected():
    frame = trials([1])
    with pytest.raises(ValueError, match="one row"):
        stats.summarise_group(pd.concat([frame, frame]), leads_hours=[6])
    with pytest.raises(ValueError, match="planned"):
        stats.summarise_group(frame, leads_hours=[12])


def test_component_coverage_deletions_preserve_sets_and_component_specific_denominators():
    frame = trials([1, 4, 4], leads=[6, 12], missions=["a", "a", "b"])
    frame.loc[frame["mission"].eq("b") & frame["lead_h"].eq(12), "gap"] = True
    frame.loc[frame["mission"].eq("b"), "sigma_r_km"] = np.nan
    result = stats.summarise_group(frame, leads_hours=[6, 12])
    cells = result["sensitivities"]["component_coverage"]["by_lead_h"]
    early = cells["6"]["in_track"]
    assert early["baseline"] == {"n": 3, "inside_2_sigma_count": 1, "inside_2_sigma_fraction": 1 / 3}
    assert early["leave_one_spacecraft_out"]["a"] == {
        "n": 1,
        "inside_2_sigma_count": 0,
        "inside_2_sigma_fraction": 0,
    }
    assert early["leave_one_spacecraft_out"]["b"]["inside_2_sigma_fraction"] == 0.5
    assert early["leave_one_set_out"] == {
        "n_deletions": 3,
        "n_defined": 3,
        "n_undefined": 0,
        "n_fraction_changed": 3,
        "min_fraction": 0,
        "max_fraction": 0.5,
        "min_n": 2,
        "max_n": 2,
    }
    later = cells["12"]["in_track"]["leave_one_set_out"]
    assert later == {
        "n_deletions": 3,
        "n_defined": 3,
        "n_undefined": 0,
        "n_fraction_changed": 2,
        "min_fraction": 0,
        "max_fraction": 1,
        "min_n": 1,
        "max_n": 2,
    }
    radial = cells["6"]["radial"]
    assert radial["leave_one_spacecraft_out"]["a"]["inside_2_sigma_fraction"] is None
    assert radial["leave_one_set_out"]["max_n"] == 2
    assert radial["leave_one_set_out"]["n_fraction_changed"] == 2
    coverage = result["by_lead_h"]["6"]["components"]["radial"]["coverage"]
    assert coverage["mission_counts"] == {"a": 2}
    assert result["by_lead_h"]["6"]["components"]["radial"]["mission_counts"] == {"a": 2, "b": 1}


def test_component_coverage_deletions_report_undefined_and_zero_sigma_pairs():
    frame = trials([0, 3], leads=[6, 12], missions=["a", "b"])
    frame["sigma_i_km"] = [0, 0, -1, -1]
    result = stats.summarise_group(frame, leads_hours=[6, 12, 24])
    cells = result["sensitivities"]["component_coverage"]["by_lead_h"]
    one_pair = cells["6"]["in_track"]
    assert one_pair["baseline"]["inside_2_sigma_fraction"] == 1
    assert one_pair["leave_one_set_out"] == {
        "n_deletions": 2,
        "n_defined": 1,
        "n_undefined": 1,
        "n_fraction_changed": 0,
        "min_fraction": 1,
        "max_fraction": 1,
        "min_n": 0,
        "max_n": 1,
    }
    assert one_pair["leave_one_spacecraft_out"]["a"]["inside_2_sigma_fraction"] is None
    empty = cells["24"]["in_track"]["leave_one_set_out"]
    assert empty["n_deletions"] == empty["n_undefined"] == 2
    assert empty["min_fraction"] is None and empty["max_fraction"] is None
    json.dumps(result, allow_nan=False)
