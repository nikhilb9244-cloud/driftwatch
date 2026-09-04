"""How far Step 4's validation reaches, per event, and the promise that nothing is tuned to it.

Two separate things are pinned here and they are easy to conflate. The first is the
``storm_validity`` label: which events the May 2024 measurement covers, taken from the weaker of
the two objects' ballistic coefficient sources. The second is that the label changes **nothing
else** -- not a probability, not a sigma, not a flag. It is a statement about the evidence, and a
label that quietly reweighted the numbers would be a calibration wearing a provenance badge.

The last test in the file pins the storm-response prior itself, because "nothing in the storm
term was tuned to any of it" is a claim the repository makes in three documents and a test is the
only thing that can keep it true.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from test_screening import PRIMARY_EPOCH, PRIMARY_ID, START, fleet_of, primary_satrec, snapshot_from
from test_storm import Isotropic

from driftwatch import config
from driftwatch.risk.scenario import RISK_COLUMNS, objects_from_snapshot, run_risk
from driftwatch.screening import ScreeningConfig, screen_fleet
from driftwatch.storm import diagnostics, term
from driftwatch.storm import scenarios as sc

T0 = datetime(2026, 9, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def designed_conjunction():
    """One designed conjunction screened by Stages A to C. See ``tests/test_storm.py``."""
    from synthetic import make_conjunction

    primary = primary_satrec()
    t_star = START + timedelta(hours=2, minutes=7)
    secondary, _ = make_conjunction(
        primary, t_star, miss_km=0.4, crossing_angle_deg=90.0, miss_direction_deg=30.0, norad_id=90020
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90020: (secondary, "SECONDARY", t_star)})
    fleet = fleet_of((PRIMARY_ID, "Primary", True))
    result = screen_fleet(snap, fleet, config=ScreeningConfig(days=0.2), start=START)
    objects = objects_from_snapshot([PRIMARY_ID, 90020], snap, fleet)
    return result.events, objects


def shift_series(norad_id: int, source: str) -> term.ShiftSeries:
    """A shift of a few kilometres over the window, attributed to ``source``."""
    return term.ShiftSeries(
        norad_id=norad_id,
        seconds=np.array([-86400.0, 86400.0]),
        shift_m=np.array([2_000.0, 8_000.0]),
        sigma_m=np.array([400.0, 1_600.0]),
        rho_scenario_kg_m3=5e-12,
        rho_implied_kg_m3=3e-12,
        b_m2_kg=0.02,
        b_source=source,
    )


# --------------------------------------------------------------------------------------
# The label itself


@pytest.mark.parametrize(
    ("primary", "secondary", "expected"),
    [
        ("history", "history", term.VALIDATED),
        ("history", "bstar", term.INDICATIVE),
        ("typical", "history", term.INDICATIVE),
        ("bstar", "typical", term.INDICATIVE),
        # A coefficient nobody has is weaker than a stand-in, not stronger.
        ("history", "none", term.INDICATIVE),
        # No storm layer at all on either side: `quiet`, and any plain labelled rescore.
        ("none", "none", term.NO_STORM_TERM),
        # An operator-controlled side is neutral (2026-09-05): its shift was zeroed, so the free
        # side's coefficient decides on its own.
        ("operator-controlled/known", "history", term.VALIDATED),
        ("operator-controlled/served", "typical", term.INDICATIVE),
        ("operator-controlled/operator-ephemeris", "none", term.INDICATIVE),
        # Both sides controlled: nothing was displaced, and the validation has nothing to reach.
        ("operator-controlled/known", "operator-controlled/served", term.OPERATOR_CONTROLLED),
    ],
)
def test_the_weaker_of_the_two_coefficient_sources_decides(primary, secondary, expected):
    """A relative shift is the difference of two displacements, so the worse-known one bounds it.

    Step 4 found the term predictive at r = 0.88 for an object whose coefficient was fitted from
    its own decay and of no demonstrated skill for one carrying a B* inversion, so an event is
    only validated when *both* sides were measured.
    """
    assert term.event_validity(primary, secondary) == expected
    assert term.event_validity(secondary, primary) == expected, "the rule is symmetric in the pair"


def test_the_extrapolation_marker_is_not_a_coefficient_source():
    """``history!extrapolated`` says the implied decay was large, not where the coefficient came from.

    Two different statements ride on the same label and conflating them would silently demote
    every object whose orbit the scenario says falls a long way -- which is a property of the
    storm, not of the evidence for the coefficient.
    """
    assert term.coefficient_source("history!extrapolated") == "history"
    assert term.event_validity("history!extrapolated", "history") == term.VALIDATED
    assert term.event_validity("bstar!extrapolated", "history") == term.INDICATIVE


def test_every_risk_row_carries_the_label_and_quiet_carries_none(designed_conjunction):
    """The column exists on every scenario, and says `none` where no storm term was applied."""
    events, objects = designed_conjunction
    secondary = int(events["secondary_norad_id"].iloc[0])
    base = Isotropic(0.5)

    quiet = run_risk(events, objects, base, scenario="quiet", run_id="r", snapshot="s", sweep=False)
    assert "storm_validity" in RISK_COLUMNS
    assert (quiet["storm_validity"] == term.NO_STORM_TERM).all()

    # One measured side and one object the scenario could not move: indicative, because the
    # unknown displacement is the weaker half of the difference that reaches the miss.
    model = sc.StormCovariance(base, {secondary: shift_series(secondary, "history")}, scenario="storm-g5")
    out = run_risk(events, objects, model, scenario="storm-g5", run_id="r", snapshot="s", sweep=False)
    assert (out["storm_validity"] == term.INDICATIVE).all()
    assert (out["storm_source_secondary"] == "history").all()
    assert (out["storm_source_primary"] == "none").all()

    # Both sides measured: validated.
    both = sc.StormCovariance(
        base,
        {secondary: shift_series(secondary, "history"), PRIMARY_ID: shift_series(PRIMARY_ID, "history")},
        scenario="storm-g5",
    )
    validated = run_risk(events, objects, both, scenario="storm-g5", run_id="r", snapshot="s", sweep=False)
    assert (validated["storm_validity"] == term.VALIDATED).all()


def test_the_label_changes_no_number_at_all(designed_conjunction):
    """`indicative` is an unmeasured number, not a smaller one.

    The same shift attributed to a measured coefficient and to a stand-in must produce identical
    probabilities, sigmas and flags. If it ever does not, the label has become a weighting and
    the documented promise that nothing is tuned to Step 4 is broken.
    """
    events, objects = designed_conjunction
    secondary = int(events["secondary_norad_id"].iloc[0])
    base = Isotropic(0.5)

    def score(source: str) -> pd.DataFrame:
        model = sc.StormCovariance(base, {secondary: shift_series(secondary, source)}, scenario="storm-g5")
        return run_risk(events, objects, model, scenario="storm-g5", run_id="r", snapshot="s", sweep=False)

    measured, stood_in = score("history"), score("typical")
    assert measured["storm_validity"].iloc[0] == stood_in["storm_validity"].iloc[0] == term.INDICATIVE
    for column in ("pc", "pc_shift_only", "pc_variance_only", "miss_shifted_km", "relative_shift_km"):
        assert np.allclose(measured[column], stood_in[column], equal_nan=True), column
    for column in ("sigma_i_primary_km", "sigma_i_secondary_km", "flag", "region", "confidence"):
        assert (measured[column] == stood_in[column]).all(), column


# --------------------------------------------------------------------------------------
# Every aggregate, both ways


def cancellation_frame_of(validities: list[str]) -> pd.DataFrame:
    """A minimal frame of the shape :func:`diagnostics.cancellation` consumes."""
    n = len(validities)
    return pd.DataFrame(
        {
            "storm_validity": validities,
            "b_source_pair": ["history+history"] * n,
            "shared_source": [True] * n,
            "altitude_difference_km": np.linspace(1.0, 200.0, n),
            "altitude_difference_band": pd.cut(
                np.linspace(1.0, 200.0, n),
                bins=list(diagnostics.ALTITUDE_DIFFERENCE_EDGES_KM),
                labels=diagnostics._bin_labels(diagnostics.ALTITUDE_DIFFERENCE_EDGES_KM, "km"),
                include_lowest=True,
            ),
            "abs_shift_mean_km": np.full(n, 10.0),
            "relative_shift_km": np.full(n, 19.0),
            "cancellation_ratio": np.full(n, 1.9),
            "tca_altitude_difference_km": np.full(n, 8.0),
            "pc": np.logspace(-11, -6, n),
            "pc_shift_only": np.logspace(-11, -6, n) * 0.5,
            "pc_variance_only": np.logspace(-11, -6, n) * 2.0,
        }
    )


def test_the_cancellation_tables_are_reported_over_both_populations():
    """Validated first, indicative second, combined last -- and combined is never the only one."""
    frame = cancellation_frame_of(["validated"] * 6 + ["indicative"] * 10)
    out = diagnostics.cancellation(frame, min_events=1)
    split = out["by_storm_validity"]
    assert list(split) == ["validated", "indicative", "combined"]
    assert split["validated"]["n_events"] == 6
    assert split["indicative"]["n_events"] == 10
    assert split["combined"]["n_events"] == 16
    assert set(out["by_altitude_difference_per_validity"]) == set(split)
    assert set(out["spearman_per_validity"]) == set(split)


def test_the_effect_split_is_reported_over_both_populations():
    """Which of the two effects moves the number must not be read off the unvalidated population."""
    frame = cancellation_frame_of(["validated"] * 8 + ["indicative"] * 8)
    out = diagnostics.effect_split(frame)
    assert out["bands"], "the combined table is still there"
    assert list(out["by_storm_validity"]) == ["validated", "indicative", "combined"]
    assert out["by_storm_validity"]["validated"]["n_events"] == 8


def test_a_population_with_one_label_reports_it_once_and_still_reports_combined():
    """No empty groups, and the combined figure is always present so a caller can rely on it."""
    out = diagnostics.cancellation(cancellation_frame_of(["indicative"] * 5), min_events=1)
    assert list(out["by_storm_validity"]) == ["indicative", "combined"]


def test_the_weekly_report_gives_every_storm_figure_both_ways():
    """The report is where a reader meets these numbers, so the split has to survive to it."""
    from driftwatch.export.report import storm_section

    rows = pd.DataFrame(
        {
            "storm_validity": ["validated"] * 3 + ["indicative"] * 4,
            "flag": ["none"] * 7,
            "relative_shift_km": [12.0, 30.0, 9.0, 44.0, 51.0, 7.0, 18.0],
            "pc": np.array([1e-7, 2e-8, 5e-9, 3e-7, 1e-6, 4e-9, 8e-8]),
            "pc_variance_only": np.array([2e-7, 3e-8, 6e-9, 9e-7, 2e-6, 5e-9, 1e-7]),
        }
    )
    text = "\n".join(storm_section(rows, "storm-g5"))
    assert "validated (3)" in text and "indicative (4)" in text and "combined (7)" in text
    assert text.index("validated (3)") < text.index("combined (7)"), "validated is read first"
    assert "no demonstrated skill" in text
    # And the corrected mechanism travels with the number rather than the old explanation.
    assert "common-mode cancellation" in text and "withdrew" in text
    assert "1.91" in text

    # A scenario that moved nothing gets no section at all rather than a table of dashes.
    assert storm_section(rows.assign(relative_shift_km=0.0), "quiet") == []


# --------------------------------------------------------------------------------------
# And the promise that nothing was tuned


def test_the_storm_response_prior_is_still_the_untuned_symmetric_thirty_per_cent():
    """Step 4 measured a 22 per cent over-prediction and the code was deliberately not changed.

    `docs/storm-validation.md`, `docs/methods.md` and the README all state that the measurement
    is recorded and not applied. One storm is not a population, and fitting a model to the data
    that measured it destroys the measurement. This test is what stops a later change turning
    the record into a calibration without somebody deciding to.
    """
    assert config.DENSITY_STORM_RATIO_SIGMA_REL == 0.30
    assert config.DENSITY_ABSOLUTE_SIGMA_REL == 0.15


# --------------------------------------------------------------------------------------
# Operator-controlled objects (the 2026-09-05 correction)


def unscoreable_series(norad_id: int, source: str = "typical") -> term.ShiftSeries:
    """A shift past the linear theory, the kind a thrusting Starlink's B* produced on the real runs."""
    a_m = 6_778_137.0
    past = 2.0 * np.pi * a_m * (config.STORM_MAX_SHIFT_REVOLUTIONS + 0.5)
    return term.ShiftSeries(
        norad_id=norad_id,
        seconds=np.array([-86400.0, 86400.0]),
        shift_m=np.array([0.0, past]),
        sigma_m=np.array([0.0, past / 10.0]),
        rho_scenario_kg_m3=5e-12,
        rho_implied_kg_m3=-3e-12,
        b_m2_kg=0.5,
        b_source=source,
        shift_revolutions=config.STORM_MAX_SHIFT_REVOLUTIONS + 0.5,
        valid=False,
    )


def test_an_operator_controlled_object_is_not_displaced_and_cannot_make_an_event_unscoreable(designed_conjunction):
    """The category error, seen from both sides at once.

    Before the correction a Starlink whose supplemental B* described a thrusting plan was given a
    displacement of tens of thousands of kilometres and its events were reported outside the
    linear theory. The displacement of a controlled object is not the atmosphere's to predict,
    so the mean is zero, the event is scored, and the label says why.
    """
    events, objects = designed_conjunction
    secondary = int(events["secondary_norad_id"].iloc[0])
    base = Isotropic(0.5)
    series = {secondary: unscoreable_series(secondary)}
    kwargs = dict(scenario="storm-g5", run_id="r", snapshot="s", sweep=False)

    free = run_risk(events, objects, sc.StormCovariance(base, series, scenario="storm-g5"), **kwargs)
    assert (~free["scoreable"]).all(), "uncontrolled, the same series is outside the linear theory"

    # A station-kept object on a tracking-derived element set: mean zero, variance kept.
    known = sc.StormCovariance(base, series, scenario="storm-g5", controlled={secondary: sc.CONTROL_KNOWN})
    out = run_risk(events, objects, known, **kwargs)
    assert out["scoreable"].all()
    assert (out["shift_i_secondary_km"] == 0).all() and (out["relative_shift_km"] == 0).all()
    assert (out["sigma_shift_i_secondary_km"] > 0).all(), "the size of the storm's push stays in the variance"
    assert (out["storm_source_secondary"] == "operator-controlled/known").all()
    assert (out["storm_validity"] == term.INDICATIVE).all(), "the free side has no coefficient"
    np.testing.assert_allclose(out["miss_shifted_km"], events["miss_km"], rtol=1e-9)
    assert out["model_version"].iloc[0].endswith("+storm/storm-g5/2")

    # An object on the operator's own trajectory: no term at all, so the probability is quiet's.
    plan = sc.StormCovariance(base, series, scenario="storm-g5", controlled={secondary: sc.CONTROL_OPERATOR_EPHEMERIS})
    out_plan = run_risk(events, objects, plan, **kwargs)
    quiet = run_risk(events, objects, base, scenario="quiet", run_id="r", snapshot="s", sweep=False)
    assert (out_plan["sigma_shift_i_secondary_km"] == 0).all()
    assert (out_plan["storm_source_secondary"] == "operator-controlled/operator-ephemeris").all()
    np.testing.assert_allclose(out_plan["pc"], quiet["pc"])

    # Both sides controlled: no displacement anywhere, and its own validity label.
    both = sc.StormCovariance(
        base,
        {**series, PRIMARY_ID: unscoreable_series(PRIMARY_ID, "history")},
        scenario="storm-g5",
        controlled={secondary: sc.CONTROL_KNOWN, PRIMARY_ID: sc.CONTROL_OBSERVED},
    )
    out_both = run_risk(events, objects, both, **kwargs)
    assert out_both["scoreable"].all()
    assert (out_both["storm_validity"] == term.OPERATOR_CONTROLLED).all()
    assert (out_both["storm_source_primary"] == "operator-controlled/observed").all()


class ServedBase:
    """A base model whose label says the trajectory was the operator's published states."""

    version = "served-test/1"

    def growth_for(self, obj):
        return None, sc.SERVED_TRAJECTORY_LABEL

    def covariance_ric(self, obj, epoch, at):
        cov = np.zeros((len(at), 3, 3))
        cov[:, [0, 1, 2], [0, 1, 2]] = 0.25
        return sc.RicCovariance(cov, sc.SERVED_TRAJECTORY_LABEL)


def test_a_served_trajectory_is_recognised_from_the_label_and_gets_no_term_at_all():
    """Served is per event, not per object, so it is read off the base model's label per time."""
    from driftwatch.risk.covariance import ObjectRef

    at = np.array(["2026-09-02T00:00:00", "2026-09-04T00:00:00"], dtype="datetime64[us]")
    layered = sc.StormCovariance(ServedBase(), {7: shift_series(7, "typical")}, scenario="storm-g5")
    out = layered.covariance_ric(ObjectRef(7, "starlink", "leo"), T0, at)
    np.testing.assert_allclose(out.cov_km2[:, 1, 1], 0.25)
    assert (out.mean_shift_ric_km == 0).all()
    assert list(out.source) == ["spacex-ephemeris+storm:operator-controlled/served"] * 2
    # `run_risk` strips the covariance prefix before the label reaches `storm_source_*`.
    storm_label = str(out.source[0]).split("+storm:")[-1]
    assert term.event_validity(storm_label, "history") == term.VALIDATED


def test_the_controlled_objects_are_read_from_the_objects_table(designed_conjunction):
    """Known and observed manoeuvre levels, and any supplemental element set, are controlled."""
    _, objects = designed_conjunction
    controlled = sc.controlled_objects(objects)
    # The fixture's primary is a fleet member flagged `manoeuvres: true`; the secondary is not
    # in the active group and so is `none`.
    assert controlled == {PRIMARY_ID: sc.CONTROL_KNOWN}
    with_plan = objects.copy()
    with_plan.loc[with_plan["norad_id"] != PRIMARY_ID, "ephemeris"] = "supplemental"
    secondary = int(with_plan.loc[with_plan["norad_id"] != PRIMARY_ID, "norad_id"].iloc[0])
    assert sc.controlled_objects(with_plan)[secondary] == sc.CONTROL_OPERATOR_EPHEMERIS
    assert sc.skips_storm_term(sc.CONTROL_OPERATOR_EPHEMERIS) and sc.skips_storm_term(sc.CONTROL_SERVED)
    assert not sc.skips_storm_term(sc.CONTROL_KNOWN) and not sc.skips_storm_term(sc.CONTROL_OBSERVED)
    assert sc.controlled_objects(objects.iloc[0:0]) == {}


def test_the_shift_summary_counts_controlled_objects_out_of_the_unscoreable_tally():
    """A displacement that is never applied cannot make anything unscoreable."""
    series = {1: unscoreable_series(1), 2: shift_series(2, "history")}
    plain = term.shift_summary(series)
    assert plain["n_unscoreable"] == 1 and plain["n_outside_linear_theory"] == 1
    controlled = term.shift_summary(series, {1: sc.CONTROL_KNOWN, 3: sc.CONTROL_OPERATOR_EPHEMERIS})
    assert controlled["n_unscoreable"] == 0 and controlled["n_outside_linear_theory"] == 0
    assert controlled["n_operator_controlled"] == 2
    assert controlled["by_control_reason"] == {sc.CONTROL_KNOWN: 1, sc.CONTROL_OPERATOR_EPHEMERIS: 1}
    assert controlled["n_objects"] == 3


def test_the_cancellation_split_leaves_out_events_with_a_controlled_side():
    """One displacement zeroed by rule makes the ratio 2 by construction; that is not a measurement."""
    frame = cancellation_frame_of(["validated"] * 6)
    frame.attrs["n_excluded_operator_controlled"] = 4
    out = diagnostics.cancellation(frame, min_events=1)
    assert out["n_excluded_operator_controlled"] == 4
    assert out["n_events"] == 6
    assert diagnostics.cancellation(pd.DataFrame())["n_excluded_operator_controlled"] == 0
    # And the split carries the third population when it is present.
    three = cancellation_frame_of(["validated"] * 4 + ["indicative"] * 4 + ["operator-controlled"] * 4)
    assert list(diagnostics.split_by_validity(three)) == ["validated", "indicative", "operator-controlled", "combined"]
