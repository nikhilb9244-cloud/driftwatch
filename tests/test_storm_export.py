"""The Step 5 exports: the per-scenario overlay and the replay timeline.

What is worth pinning here is not the arithmetic -- that is Steps 3 and 4 -- but the promises the
viewer relies on and could not detect being broken:

* the overlay's columns are **parallel** to the base bundle's arrays, so the browser indexes
  rather than joins, and a scenario that lost an event would silently shift every row after it;
* the miss under a scenario is the **shifted** one, in the overlay and in the base bundle alike,
  so a number does not change when the overlay lands;
* an **unscoreable** event carries null rather than a small number;
* every aggregate is present **both ways**, with the combined figure never alone;
* the replay timeline's density ratio has a denominator that actually reaches the quiet window,
  which is the one failure that comes back as a plausible-looking NaN rather than an error.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from driftwatch import config
from driftwatch.export import storm as storm_export
from driftwatch.export.report import normalise

T0 = datetime(2024, 5, 9, tzinfo=UTC)


def conjunction_rows(scenario: str, *, n: int = 4, unscoreable_last: bool = False) -> pd.DataFrame:
    """A joined-conjunctions frame of the shape the exporter consumes."""
    rows = pd.DataFrame(
        {
            "event_id": [f"e{i}" for i in range(n)],
            "scenario": scenario,
            "primary_norad_id": [100] * n,
            "secondary_norad_id": [200, 200, 300, 300][:n],
            "tca": pd.to_datetime([T0 + timedelta(hours=i) for i in range(n)], utc=True),
            "miss_km": np.linspace(5.0, 8.0, n),
            "miss_shifted_km": np.linspace(2.0, 3.5, n),
            "rel_speed_kms": np.full(n, 13.0),
            "pc": np.logspace(-9, -5, n),
            "pc_shift_only": np.logspace(-10, -6, n),
            "pc_variance_only": np.logspace(-8, -4, n),
            "pc_max": np.logspace(-8, -4, n),
            "pc_max_scale": np.full(n, 1.4),
            "relative_shift_km": np.full(n, 22.0),
            "shift_i_primary_km": np.full(n, 9.0),
            "shift_i_secondary_km": np.full(n, -11.0),
            "sigma_i_primary_km": np.full(n, 1.5),
            "sigma_i_secondary_km": np.full(n, 2.5),
            "enc_cov_xx_km2": np.full(n, 4.0),
            "enc_cov_xy_km2": np.full(n, 0.5),
            "enc_cov_yy_km2": np.full(n, 0.25),
            "storm_source_primary": ["history"] * n,
            "storm_source_secondary": ["history", "bstar", "history", "typical"][:n],
            "storm_validity": ["validated", "indicative", "validated", "indicative"][:n],
            "region": ["robust"] * n,
            "flag": ["yellow", "none", "none", "none"][:n],
            "confidence": ["standard"] * n,
            "scoreable": [True] * n,
            "unscoreable_reason": [""] * n,
            "in_box": [True] * n,
            "primary_name": ["PRIMARY"] * n,
            "secondary_name": ["SECONDARY-A", "SECONDARY-A", "SECONDARY-B", "SECONDARY-B"][:n],
        }
    )
    if unscoreable_last:
        rows.loc[n - 1, ["pc", "pc_shift_only", "pc_variance_only", "pc_max", "pc_max_scale"]] = np.nan
        rows.loc[n - 1, "flag"] = "unscoreable"
        rows.loc[n - 1, "region"] = "unscoreable"
        rows.loc[n - 1, "confidence"] = "none"
        rows.loc[n - 1, "scoreable"] = False
        rows.loc[n - 1, "unscoreable_reason"] = "300: in-track shift 0.4 of the orbit's circumference"
    return normalise(rows)


# --------------------------------------------------------------------------------------
# The overlay


def test_the_event_columns_stay_parallel_to_the_bundles_own_order():
    """The browser indexes; it does not join. A reordered or short column would misattribute rows."""
    rows = conjunction_rows("storm-g5")
    ids = ["e3", "e0", "e2", "e1"]  # deliberately not the frame's order
    overlay = storm_export.event_overlay(rows, ids)
    for name in (*storm_export.EVENT_NUMBERS, "scoreable"):
        assert len(overlay[name]) == len(ids), name
    for name in storm_export.EVENT_LABELS:
        assert len(overlay[name]["i"]) == len(ids), name
    # e3's shifted miss is the largest in the frame and must land in position 0.
    assert overlay["miss_shifted_km"][0] == pytest.approx(3.5)
    assert overlay["miss_shifted_km"][1] == pytest.approx(2.0)

    # An event the scenario has no row for is nulls, not a dropped column.
    missing = storm_export.event_overlay(rows, ["e0", "nope"])
    assert missing["pc"][1] is None
    assert missing["scoreable"][1] is True


def test_a_label_column_is_dictionary_encoded_and_round_trips():
    """A third of the overlay was repeated short strings. Encoded, they are a rounding error."""
    rows = conjunction_rows("storm-g5")
    overlay = storm_export.event_overlay(rows, [f"e{i}" for i in range(4)])
    validity = overlay["storm_validity"]
    assert sorted(validity["v"]) == ["indicative", "validated"]
    decoded = [validity["v"][i] for i in validity["i"]]
    assert decoded == ["validated", "indicative", "validated", "indicative"]


def test_the_pair_rollup_uses_the_shifted_miss_and_the_worst_event_under_this_scenario():
    """The miss beside a scenario's probability is the one that probability was computed from."""
    rows = conjunction_rows("storm-g5")
    overlay = storm_export.pair_overlay(rows, [(100, 200), (100, 300)])
    # Pair (100, 200) covers e0 and e1: shifted misses 2.0 and 2.5, geometry 5.0 and 6.0.
    assert overlay["closest_km"][0] == pytest.approx(2.0)
    assert overlay["miss_at_max_pc_km"][0] == pytest.approx(2.5), "the worst event's, not the closest"
    assert overlay["n_scoreable"] == [2, 2]

    # A pair the scenario has no rows for is absent rather than wrong.
    empty = storm_export.pair_overlay(rows, [(999, 888)])
    assert empty["max_pc"] == [None] and empty["n_scoreable"] == [0]


def test_an_unscoreable_event_carries_null_and_its_reason_rather_than_a_small_number():
    """Null, not zero: the storm term left its derivation and there is no probability to give."""
    rows = conjunction_rows("storm-g5", unscoreable_last=True)
    overlay = storm_export.event_overlay(rows, [f"e{i}" for i in range(4)])
    assert overlay["pc"][3] is None
    assert overlay["pc_max"][3] is None
    assert overlay["scoreable"][3] is False
    reason = overlay["unscoreable_reason"]
    assert "circumference" in reason["v"][reason["i"][3]]

    listed = storm_export.unscoreable_rows(rows)
    assert len(listed) == 1 and listed[0]["event_id"] == "e3"
    assert "circumference" in listed[0]["reason"]
    # And it is out of the pair's probability without being out of the pair.
    pairs = storm_export.pair_overlay(rows, [(100, 300)])
    assert pairs["n_scoreable"] == [1]


def test_the_summary_is_given_both_ways_with_combined_last_and_never_alone():
    """A median over a mostly-indicative population reads as a measurement and is not one."""
    rows = conjunction_rows("storm-g5")
    summary = storm_export.scenario_summary(rows)
    assert list(summary) == ["validated", "indicative", "combined"]
    assert summary["validated"]["n_events"] == 2
    assert summary["indicative"]["n_events"] == 2
    assert summary["combined"]["n_events"] == 4
    assert summary["combined"]["n_moved"] == 4

    # A population with one label still reports combined, so a caller can rely on the key.
    one = storm_export.scenario_summary(rows.assign(storm_validity="indicative"))
    assert list(one) == ["indicative", "combined"]


# --------------------------------------------------------------------------------------
# The replay timeline


def weather_frame(start: datetime, hours: int, kp: float) -> pd.DataFrame:
    """A three-hourly weather table of the shape the density model wants."""
    t = pd.date_range(pd.Timestamp(start), periods=hours // 3, freq="3h", tz="UTC")
    ap = 4.0 if kp < 5 else 200.0
    return pd.DataFrame(
        {
            "t": t,
            "kp": kp,
            "ap": ap,
            "ap_daily": ap,
            "ap_sigma": 2.0,
            "f107": 170.0,
            "f107a": 165.0,
            "provenance": "observed",
            "skill": "observed",
        }
    )


def test_the_kp_series_is_the_window_and_carries_its_provenance():
    table = weather_frame(T0 - timedelta(days=3), 24 * 12, 5.0)
    series = storm_export.kp_series(table, T0, T0 + timedelta(days=1))
    assert len(series) == 9  # inclusive of both ends on a three-hour grid
    assert set(series["provenance"]) == {"observed"}
    assert series["t"].is_monotonic_increasing


def test_a_baseline_that_does_not_reach_the_quiet_window_is_refused_rather_than_returning_nan():
    """The one failure here that comes back looking like a result.

    The density ratio's denominator is three weeks earlier than its numerator. A table built over
    the replay window alone does not contain it, `quiet_density_profile` returns NaN for every
    sample, and every ratio in the viewer becomes null with nothing to say why. That is how this
    was found, so it is an exception now.
    """
    table = weather_frame(T0 - timedelta(days=3), 24 * 12, 5.0)
    with pytest.raises(ValueError, match="quiet control window"):
        storm_export.density_ratio_series(table, [T0], baseline=table)


def test_the_replay_window_comes_from_the_scenario_name():
    start, end = storm_export.replay_window("replay:2024-05-09", 7.0)
    assert start == T0
    assert (end - start).days == 7
    with pytest.raises(ValueError, match="does not name a date"):
        storm_export.replay_window("replay", 7.0)


def test_the_written_bundles_are_json_the_viewer_can_read(tmp_path):
    """No NaN, no infinity: JSON has neither, and a viewer that meets one stops rendering."""
    rows = conjunction_rows("storm-g5", unscoreable_last=True)
    overlay = {
        "overlay_version": storm_export.OVERLAY_VERSION,
        "n_events": 4,
        "n_pairs": 2,
        "scenarios": {
            "storm-g5": {
                "events": storm_export.event_overlay(rows, [f"e{i}" for i in range(4)]),
                "pairs": storm_export.pair_overlay(rows, [(100, 200), (100, 300)]),
                "summary": storm_export.scenario_summary(rows),
                "unscoreable": storm_export.unscoreable_rows(rows),
                "n_events_total": 4,
            }
        },
    }
    path = storm_export.write_overlays(overlay, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text
    assert json.loads(text)["scenarios"]["storm-g5"]["events"]["pc"][3] is None


def test_the_quiet_denominator_is_the_one_step_4_measured_against():
    """A viewer ratio meaning something different from the validated one would be a quiet trap."""
    assert config.GANNON_QUIET_WINDOW == ("2024-04-25T00:00:00Z", "2024-04-28T00:00:00Z")
    assert storm_export.REPLAY_ALTITUDES_KM == (400.0, 500.0)
