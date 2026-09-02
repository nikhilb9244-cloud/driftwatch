"""The storm term: the derivation, its sign, the scenarios and what they do to a probability.

Nothing here touches the network. The closed form is checked against a numerical integration
of the same physics done independently, the sign against a case where the answer is obvious
from first principles, and the covariance protocol's new field against the Phase 2 models,
which must go on returning exactly what they returned.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import satrec_from_kepler
from test_drag import element_row, weather
from test_screening import PRIMARY_EPOCH, PRIMARY_ID, START, fleet_of, primary_satrec, snapshot_from

from driftwatch import config
from driftwatch.risk.covariance import DEFAULT_GROWTH, EmpiricalCovariance, ObjectRef, RicCovariance
from driftwatch.risk.scenario import objects_from_snapshot
from driftwatch.screening import ScreeningConfig, screen_fleet
from driftwatch.storm import scenarios as sc
from driftwatch.storm import term
from driftwatch.weather import table as wt

T0 = datetime(2026, 9, 1, tzinfo=UTC)
MU = 3.986004418e14


@pytest.fixture(scope="module")
def designed_conjunction():
    """One designed conjunction screened by Stages A to C, as ``test_scenario`` builds it.

    Built here rather than imported so the two modules do not share a fixture by import,
    which pytest allows and every linter reads as a redefinition.
    """
    from synthetic import make_conjunction

    primary = primary_satrec()
    t_star = START + timedelta(hours=2, minutes=7)
    secondary, design = make_conjunction(
        primary, t_star, miss_km=0.4, crossing_angle_deg=90.0, miss_direction_deg=30.0, norad_id=90020
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90020: (secondary, "SECONDARY", t_star)})
    fleet = fleet_of((PRIMARY_ID, "Primary", True))
    result = screen_fleet(snap, fleet, config=ScreeningConfig(days=0.2), start=START)
    objects = objects_from_snapshot([PRIMARY_ID, 90020], snap, fleet)
    return result.events, objects


# --------------------------------------------------------------------------------------
# The derivation


def test_the_closed_form_matches_a_numerical_integration_of_the_same_orbit():
    """``s = (3/4) B drho v^2 t^2`` against an independent integration, to well under a per cent.

    The verification the prompt asks for. :func:`term.integrate_test_orbit` integrates the
    decay and the along-track angle directly, with a step density change and no appeal to the
    closed form; the two are then differenced. The agreement is best where the orbit barely
    decays and worst at 300 km over a week, where the orbit has dropped far enough that the
    "constant v" the closed form assumes is no longer quite constant -- which is the
    approximation being measured, and it is a quarter of a per cent.
    """
    for altitude_km, rho, tolerance in ((300.0, 2.6e-11, 0.005), (400.0, 4.3e-12, 0.002), (550.0, 4.0e-13, 0.001)):
        for days in (1.0, 3.0, 7.0):
            got = term.integrate_test_orbit(
                b_m2_kg=0.01,
                rho_kg_m3=rho,
                delta_rho_kg_m3=rho,
                altitude_km=altitude_km,
                days=days,
                step_s=30.0,
            )
            assert abs(got["relative_error"]) < tolerance, f"{altitude_km} km over {days} d: {got}"
            assert got["numerical_m"] > 0


def test_more_drag_puts_the_object_ahead_of_its_element_set_not_behind():
    """The sign. Easy to get backwards, so it is pinned from first principles twice.

    A density excess is extra drag, the orbit sinks, and a lower orbit has a higher mean
    motion: the object arrives early. So the in-track displacement is **positive**, meaning
    ahead. The numerical integration is asked the same question independently -- it reports a
    perturbed orbit whose semi-major axis is smaller and whose along-track angle is larger.
    """
    assert term.in_track_shift_m(0.01, 1e-12, 7660.0, 86400.0) > 0
    assert term.in_track_shift_m(0.01, -1e-12, 7660.0, 86400.0) < 0
    assert term.in_track_shift_m(0.01, 0.0, 7660.0, 86400.0) == 0.0

    got = term.integrate_test_orbit(
        b_m2_kg=0.01, rho_kg_m3=4e-12, delta_rho_kg_m3=4e-12, altitude_km=400.0, days=2.0, step_s=30.0
    )
    assert got["numerical_m"] > 0, "the perturbed orbit must be ahead, not behind"
    assert got["decay_m"] > 0, "and lower"


def test_the_displacement_grows_with_the_square_of_time_and_linearly_in_everything_else():
    """The scalings the derivation claims, each varied one at a time."""
    base = term.in_track_shift_m(0.01, 1e-12, 7660.0, 86400.0)
    assert term.in_track_shift_m(0.01, 1e-12, 7660.0, 2 * 86400.0) == pytest.approx(4 * base)
    assert term.in_track_shift_m(0.02, 1e-12, 7660.0, 86400.0) == pytest.approx(2 * base)
    assert term.in_track_shift_m(0.01, 3e-12, 7660.0, 86400.0) == pytest.approx(3 * base)
    assert term.in_track_shift_m(0.01, 1e-12, 2 * 7660.0, 86400.0) == pytest.approx(4 * base)


def test_an_excess_early_in_the_window_displaces_far_more_than_the_same_excess_late():
    """Why the scenarios use the weighted integral and not the closed form on a window mean.

    Equation (4) weights the excess by the time *remaining*, so the same three-hour storm at
    the start of a week-long window and at the end of it are not the same scenario at all.
    Both profiles here carry an identical total excess; only when it arrives differs.
    """
    seconds = np.arange(0.0, 7 * 86400.0 + 1, 3600.0)
    power = np.full(len(seconds), 7660.0**3)
    early = np.where(seconds < 86400.0, 1e-12, 0.0)
    late = np.where(seconds > 6 * 86400.0, 1e-12, 0.0)
    assert early.sum() == pytest.approx(late.sum(), rel=0.02)

    a_m = (6378.137 + 400.0) * 1000.0
    s_early = term.shift_from_profile(seconds, early, power, b_m2_kg=0.01, a_m=a_m)[-1]
    s_late = term.shift_from_profile(seconds, late, power, b_m2_kg=0.01, a_m=a_m)[-1]
    assert s_early > 10 * s_late, f"early {s_early:.0f} m against late {s_late:.0f} m"

    # And a constant excess reproduces the closed form, which is what makes (4) a generalisation
    # of (5) rather than a different model.
    flat = np.full(len(seconds), 1e-12)
    weighted = term.shift_from_profile(seconds, flat, power, b_m2_kg=0.01, a_m=a_m)[-1]
    closed = term.in_track_shift_m(0.01, 1e-12, np.sqrt(MU / a_m), seconds[-1])
    assert weighted == pytest.approx(closed, rel=0.01)


# --------------------------------------------------------------------------------------
# The protocol extension


class Isotropic:
    """A Phase 2 style model: a covariance, no shift, exactly as before."""

    version = "isotropic/1"

    def __init__(self, sigma_km: float = 1.0) -> None:
        self.sigma_km = sigma_km

    def growth_for(self, obj: ObjectRef):
        return DEFAULT_GROWTH["leo"], "default:leo"

    def covariance_ric(self, obj: ObjectRef, epoch, at) -> RicCovariance:
        cov = np.zeros((len(at), 3, 3))
        cov[:, [0, 1, 2], [0, 1, 2]] = self.sigma_km**2
        return RicCovariance(cov, "isotropic")


def test_a_phase_2_model_returns_no_shift_at_all():
    """The protocol extension is additive: every Phase 2 model says 'the element set is right'.

    This is what keeps the quiet scenario bit for bit unchanged. A default of ``None`` rather
    than a zero vector is deliberate -- 'no opinion' and 'zero' are the same number here but
    not the same statement, and a model that has an opinion has to say so.
    """
    at = np.array(["2026-09-02T00:00:00"], dtype="datetime64[us]")
    empirical = EmpiricalCovariance().covariance_ric(ObjectRef(1, "debris", "leo"), T0, at)
    assert empirical.mean_shift_ric_km is None
    assert Isotropic().covariance_ric(ObjectRef(1, "debris", "leo"), T0, at).mean_shift_ric_km is None


def test_the_storm_layer_adds_a_shift_in_track_and_a_variance_in_track_and_nothing_else():
    """What ``StormCovariance`` is allowed to touch: the I element, and the new field."""
    at = np.array(["2026-09-02T00:00:00", "2026-09-04T00:00:00"], dtype="datetime64[us]")
    series = term.ShiftSeries(
        norad_id=7,
        seconds=np.array([0.0, 10 * 86400.0]),
        shift_m=np.array([0.0, 20_000.0]),
        sigma_m=np.array([0.0, 4_000.0]),
        rho_scenario_kg_m3=4e-12,
        rho_implied_kg_m3=3e-12,
        b_m2_kg=0.01,
        b_source="history",
    )
    base = Isotropic(1.0)
    layered = sc.StormCovariance(base, {7: series}, scenario="storm-g5")
    ref = ObjectRef(7, "payload", "leo")
    before = base.covariance_ric(ref, T0, at)
    after = layered.covariance_ric(ref, T0, at)

    # Radial and cross-track are untouched; in-track grows by the shift's own variance.
    assert after.cov_km2[:, 0, 0] == pytest.approx(before.cov_km2[:, 0, 0])
    assert after.cov_km2[:, 2, 2] == pytest.approx(before.cov_km2[:, 2, 2])
    assert (after.cov_km2[:, 1, 1] > before.cov_km2[:, 1, 1]).all()
    sigma_added = np.sqrt(after.cov_km2[:, 1, 1] - before.cov_km2[:, 1, 1])
    assert sigma_added == pytest.approx(np.interp([1.0, 3.0], [0.0, 10.0], [0.0, 4.0]), rel=1e-6)

    # The shift is in-track only, and it is the series interpolated at the propagation time.
    assert after.mean_shift_ric_km.shape == (2, 3)
    assert (after.mean_shift_ric_km[:, [0, 2]] == 0).all()
    assert after.mean_shift_ric_km[:, 1] == pytest.approx(np.interp([1.0, 3.0], [0.0, 10.0], [0.0, 20.0]), rel=1e-6)
    assert "storm:history" in after.source

    # An object the scenario has no coefficient for is not moved, and says so rather than
    # silently reading as "no storm".
    other = layered.covariance_ric(ObjectRef(8, "payload", "leo"), T0, at)
    assert other.mean_shift_ric_km is None and other.source.endswith("storm:none")


def test_a_scenario_with_no_storm_layer_is_the_phase_2_answer_exactly(designed_conjunction):
    """The regression assertion: a Phase 2 model through the extended ``run_risk`` is unchanged.

    Checked on the real run as well -- rescoring the stored ``risk_quiet.parquet`` after Step 3
    reproduces every shared column identically, NaN for NaN, over all 5,704 events. This pins
    the same property at the unit level so it cannot quietly stop being true: no shift, no
    added variance, and ``pc_variance_only`` equal to ``pc`` to the bit, because the two are the
    same calculation when nothing moved.
    """
    from driftwatch.risk.scenario import run_risk

    events, objects = designed_conjunction
    risk = run_risk(events, objects, Isotropic(0.4), scenario="quiet", run_id="r", snapshot="s", sweep=False)
    for column in (
        "shift_i_primary_km",
        "shift_i_secondary_km",
        "sigma_shift_i_primary_km",
        "sigma_shift_i_secondary_km",
    ):
        assert (risk[column] == 0).all(), column
    assert set(risk["storm_source_primary"]) == {"none"}
    np.testing.assert_array_equal(risk["pc"].to_numpy(), risk["pc_variance_only"].to_numpy())
    np.testing.assert_allclose(risk["miss_shifted_km"], events["miss_km"], rtol=1e-9)


def test_the_shift_moves_the_miss_and_the_probability_and_reports_both_numbers(designed_conjunction):
    """End to end through ``run_risk``: the shift changes the miss, and the comparison is kept.

    The Phase 2 designed conjunction, with the secondary displaced along its own track.
    Because the encounter plane is perpendicular to the relative velocity, only the part of
    the shift across that direction can change the miss -- which is exactly the design claim,
    so the test uses a crossing geometry where it will show.
    """
    from driftwatch.risk.scenario import run_risk

    events, objects = designed_conjunction
    quiet = run_risk(events, objects, Isotropic(0.5), scenario="quiet", run_id="r", snapshot="s", sweep=False)

    secondary = int(events["secondary_norad_id"].iloc[0])
    # The secondary's element set is epoched at the conjunction itself, and a shift is zero at
    # its own epoch by definition -- that is what "the element set is right about where it is"
    # means. So the series brackets the epoch, which is the real case: an object screened seven
    # days out has seven days of displacement by the time of closest approach.
    series = term.ShiftSeries(
        norad_id=secondary,
        seconds=np.array([-86400.0, 86400.0]),
        shift_m=np.array([2_000.0, 8_000.0]),
        sigma_m=np.array([400.0, 1_600.0]),
        rho_scenario_kg_m3=5e-12,
        rho_implied_kg_m3=3e-12,
        b_m2_kg=0.02,
        b_source="history",
    )
    stormy = run_risk(
        events,
        objects,
        sc.StormCovariance(Isotropic(0.5), {secondary: series}, scenario="storm-g5"),
        scenario="storm-g5",
        run_id="r",
        snapshot="s",
        sweep=False,
    )
    assert (stormy["shift_i_secondary_km"] != 0).any()
    assert (stormy["shift_i_primary_km"] == 0).all()
    assert not np.allclose(stormy["miss_shifted_km"], quiet["miss_shifted_km"])
    # Both numbers are reported: with the shift and with the variance alone.
    assert "pc_variance_only" in stormy.columns
    assert not np.allclose(stormy["pc"], stormy["pc_variance_only"])
    # The variance-only probability uses the same widened covariance, so it is not the quiet one.
    assert (stormy["sigma_i_secondary_km"] > quiet["sigma_i_secondary_km"]).any()
    assert (stormy["sigma_shift_i_secondary_km"] > 0).any()
    assert set(stormy["storm_source_secondary"]) == {"history"}
    assert (stormy["supplemental_version"] == "").all()


# --------------------------------------------------------------------------------------
# The scenarios


def test_the_scenario_names_are_strict_where_a_typo_would_be_invisible():
    """A near miss of a storm scenario is an error; an operator's own label is not.

    ``storm-g6`` running quietly and reporting quiet numbers under a stormy name is the one
    failure mode here that a reader of the output could not detect, so it is refused.
    """
    for name in ("quiet", "forecast", "storm-g3", "storm-g4", "storm-g5", "replay:2024-05-09"):
        assert sc.validate(name) == name
        assert sc.is_known(name)
    for name in ("storm", "storm-g6", "forcast", "replayed"):
        with pytest.raises(ValueError, match="unknown scenario"):
            sc.validate(name)
    # An unrelated label is a plain rescore and is allowed through unlabelled by the storm code.
    assert sc.validate("scaled9") == "scaled9"
    assert not sc.is_known("scaled9")


def test_quiet_carries_no_weather_and_therefore_no_storm_term():
    """The regression baseline: quiet is the Phase 2 model and applies nothing."""
    scenario = sc.build_scenario("quiet", start=T0, end=T0 + timedelta(days=7), sources=wt.WeatherSources())
    assert scenario.table is None and not scenario.applies_storm_term
    assert sc.shifts_for_objects(scenario, pd.DataFrame(), pd.DataFrame(), end=T0) == {}


def test_a_synthetic_storm_keeps_the_shape_of_may_2024_and_only_replaces_its_own_intervals():
    """Scaled on the Kp axis, dropped in at the stated offset, and the rest of the table left alone."""
    observed = weather(datetime(2024, 5, 8, tzinfo=UTC), 6.0, kp=2.0)
    observed = observed.copy()
    # A designed "May 2024": quiet, then a sharp rise to Kp 9, then a recovery.
    shape = np.array([2, 3, 5, 7, 9, 9, 8, 7, 6, 5, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3], dtype=float)
    at = pd.to_datetime(observed["t"], utc=True)
    start = pd.Timestamp("2024-05-10T00:00:00Z")
    inside = (at >= start) & (at < start + pd.Timedelta(days=3))
    observed.loc[inside, "kp"] = shape[: int(inside.sum())]
    observed.loc[inside, "ap"] = wt.kp_to_ap(shape[: int(inside.sum())])

    template = sc.storm_template(observed)
    assert len(template) == 24 and float(np.nanmax(template)) == pytest.approx(9.0)
    g4 = sc.scaled_profile(template, 8.0)
    assert float(np.nanmax(g4)) == pytest.approx(8.0)
    # Scaled on the Kp axis, so the shape survives: the ratio between any two intervals is kept.
    assert g4[3] / g4[0] == pytest.approx(template[3] / template[0])

    window = weather(T0, 8.0, kp=1.0)
    stormy, summary = sc.insert_storm(window, g4, start=T0 + timedelta(days=1), name="g4")
    assert summary["n_intervals"] == 24 and summary["peak_kp"] == pytest.approx(8.0)
    designed = stormy["skill"] == "designed"
    assert int(designed.sum()) == 24
    # Everything outside the storm keeps the provenance it came with. This is the whole reason
    # the insertion takes a mask: a scenario that relabelled the observed record as synthetic
    # would be lying about most of its own table.
    assert set(stormy.loc[~designed, "provenance"]) == {"observed"}
    assert (stormy.loc[~designed, "kp"] == window.loc[~designed, "kp"]).all()
    assert float(stormy.loc[designed, "ap"].max()) > float(window["ap"].max())
    # And a designed interval never claims to be more certain than a forecast of it would be.
    assert (stormy.loc[designed, "ap_sigma"] > 0).all()


def test_raising_ap_by_its_own_sigma_is_how_the_index_uncertainty_is_measured():
    """The ap term of the variance has no closed form, so it is evaluated. Check the perturbation."""
    table = weather(T0, 4.0, kp=3.0)
    table["ap_sigma"] = 7.0
    raised = sc.raise_ap_by_sigma(table)
    assert np.allclose(raised["ap"] - table["ap"], 7.0)
    assert (raised["kp"] > table["kp"]).all()
    # The daily average follows the three-hourly values, or NRLMSIS would be given an
    # inconsistent pair.
    assert raised["ap_daily"].iloc[0] == pytest.approx(raised["ap"].iloc[:8].mean())


def test_an_object_with_no_coefficient_is_not_moved_and_the_label_says_so(monkeypatch):
    """'We do not know' and 'nothing happens' are the same number and must not be the same label."""
    from driftwatch.drag import density as dn

    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), 4e-12))
    sat = satrec_from_kepler(90001, T0, 6778.137, 0.0, 0.0, 0.0, 0.0, 0.0, bstar=1e-4)
    row = pd.Series(element_row(sat, T0, norad_id=90001))
    table = weather(T0 - timedelta(days=4), 12.0)

    without = term.object_shift(row, None, table, T0 + timedelta(days=3))
    assert len(without.shift_m) == 0 and without.note == "no ballistic coefficient"

    coefficient = pd.Series({"b_m2_kg": 0.01, "b_sigma_m2_kg": 0.0005, "source": "history"})
    with_one = term.object_shift(row, coefficient, table, T0 + timedelta(days=3))
    assert len(with_one.shift_m) > 0
    assert np.isfinite(with_one.rho_implied_kg_m3)
    # The uncertainty is never zero: the density model's own storm-response error is always in it.
    assert with_one.sigma_m[-1] > 0
    assert with_one.sigma_m[-1] >= abs(with_one.shift_m[-1]) * config.DENSITY_STORM_RATIO_SIGMA_REL * 0.5


# --------------------------------------------------------------------------------------
# The Step 3 review corrections


def test_an_extrapolated_object_makes_its_events_unscoreable_rather_than_wrong(designed_conjunction):
    """Past a quarter of a revolution of shift the term is outside its own derivation.

    The review's instruction, and the reason for it: a probability computed from a position
    the linear theory cannot support is arithmetic with no claim behind it. So it is not
    reported at all. What must survive is everything that is still true -- the geometry, the
    covariance, the shift itself and a reason a reader can act on.
    """
    from driftwatch.risk.scenario import run_risk

    events, objects = designed_conjunction
    secondary = int(events["secondary_norad_id"].iloc[0])
    a_m = 6_778_137.0
    past = 2.0 * np.pi * a_m * (config.STORM_MAX_SHIFT_REVOLUTIONS + 0.5)
    series = term.ShiftSeries(
        norad_id=secondary,
        seconds=np.array([-86400.0, 86400.0]),
        shift_m=np.array([0.0, past]),
        sigma_m=np.array([0.0, past / 10.0]),
        rho_scenario_kg_m3=5e-12,
        rho_implied_kg_m3=3e-12,
        b_m2_kg=0.5,
        b_source="history",
        shift_revolutions=config.STORM_MAX_SHIFT_REVOLUTIONS + 0.5,
        valid=False,
    )
    assert not series.scoreable
    out = run_risk(
        events,
        objects,
        sc.StormCovariance(Isotropic(0.5), {secondary: series}, scenario="storm-g5"),
        scenario="storm-g5",
        run_id="r",
        snapshot="s",
        sweep=True,
    )
    assert (~out["scoreable"]).all()
    for column in ("pc", "pc_shift_only", "pc_variance_only", "pc_alfano", "pc_chan", "pc_max", "pc_max_scale"):
        assert out[column].isna().all(), column
    assert (out["region"] == "unscoreable").all()
    assert (out["flag"] == "unscoreable").all()
    assert (out["confidence"] == "none").all()
    # The reason names the object and the size of the violation, so it can be acted on.
    reason = out["unscoreable_reason"].iloc[0]
    assert str(secondary) in reason and "circumference" in reason
    # And nothing about the event has been thrown away.
    assert (out["shift_i_secondary_km"] != 0).any()
    assert out["sigma_i_secondary_km"].notna().all()


def test_the_shift_and_the_variance_are_reported_separately_as_well_as_together(designed_conjunction):
    """Three probabilities on every row, because the two effects pull in opposite directions.

    A storm both moves the objects and widens the ellipse. The combined number alone cannot
    say which did the work, and on this project the answer -- that the shift usually *lowers*
    the probability -- is the headline, so it has to be visible per event rather than argued.
    """
    from driftwatch.risk.scenario import run_risk

    events, objects = designed_conjunction
    secondary = int(events["secondary_norad_id"].iloc[0])
    series = term.ShiftSeries(
        norad_id=secondary,
        seconds=np.array([-86400.0, 86400.0]),
        shift_m=np.array([2_000.0, 8_000.0]),
        sigma_m=np.array([400.0, 1_600.0]),
        rho_scenario_kg_m3=5e-12,
        rho_implied_kg_m3=3e-12,
        b_m2_kg=0.02,
        b_source="history",
    )
    base = Isotropic(0.5)
    out = run_risk(
        events,
        objects,
        sc.StormCovariance(base, {secondary: series}, scenario="storm-g5"),
        scenario="storm-g5",
        run_id="r",
        snapshot="s",
        sweep=False,
    )
    quiet = run_risk(events, objects, base, scenario="quiet", run_id="r", snapshot="s", sweep=False)

    # Shift only: the objects moved, scored against the covariance the run would have had. So
    # it differs from quiet only through the geometry, and from `pc` only through the spread.
    assert not np.allclose(out["pc_shift_only"], quiet["pc"])
    assert not np.allclose(out["pc_shift_only"], out["pc"])
    assert not np.allclose(out["pc_variance_only"], out["pc"])
    # Variance only leaves the objects where their element sets put them, so its miss is quiet's.
    assert (out["relative_shift_km"] > 0).any()
    # And a model with no storm layer gives one number three times over, which is what keeps
    # the Phase 2 quiet scenario unchanged.
    assert np.allclose(quiet["pc"], quiet["pc_shift_only"], equal_nan=True)
    assert np.allclose(quiet["pc"], quiet["pc_variance_only"], equal_nan=True)
    assert (quiet["relative_shift_km"] == 0).all()
    assert quiet["scoreable"].all()


def test_a_weather_table_that_does_not_reach_the_oldest_epoch_fails_loudly():
    """The one failure here that looks like a result: a silently understated storm term.

    Every shift is integrated from its own object's epoch and NRLMSIS wants its ap history
    behind that. A table built over the screening window alone is short by however stale the
    oldest element set is, and what comes back is not an error but a smaller number. So the
    short table is refused rather than used.
    """
    from driftwatch.drag import density as dn

    epoch = T0 - timedelta(days=5)
    short = weather(T0, 8.0)
    with pytest.raises(sc.WeatherTableTooShort, match="silently understated"):
        sc.check_table_reaches(short, epoch, scenario="storm-g5")

    # Long enough once the epoch and NRLMSIS's own lead are both allowed for.
    long_enough = weather(epoch - dn.WEATHER_LEAD - timedelta(hours=3), 16.0)
    sc.check_table_reaches(long_enough, epoch, scenario="storm-g5")

    # And the check is wired into the path that would otherwise understate: a run whose
    # elements reach back past the table cannot compute shifts at all.
    scenario = sc.Scenario("storm-g5", short, sc.raise_ap_by_sigma(short))
    elements = pd.DataFrame({"norad_id": [90001], "epoch": [pd.Timestamp(epoch)]})
    with pytest.raises(sc.WeatherTableTooShort):
        sc.shifts_for_objects(scenario, elements, pd.DataFrame(), end=T0 + timedelta(days=2))
