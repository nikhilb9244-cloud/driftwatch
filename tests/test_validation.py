"""Step 4's measurements: the decay-rate ratio, the in-track error and how they are summarised.

Nothing here touches the network or Space-Track. Every case is built from element sets whose
decay was designed, so the answer is known before the code is asked, and the two things that
would quietly invalidate the whole step -- a sign the wrong way round and a pivot that peeks at
the future -- are pinned rather than assumed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from test_drag import MU, circular_satrec, designed_sets, element_row, weather

from driftwatch.drag import density as dn
from driftwatch.orbit import frames
from driftwatch.storm import validation as val

T0 = datetime(2026, 9, 1, tzinfo=UTC)


def _windows(days: float = 6.0) -> tuple[val.Window, val.Window]:
    quiet = val.Window("quiet", T0, T0 + timedelta(days=days / 2))
    storm = val.Window("storm", T0 + timedelta(days=days / 2), T0 + timedelta(days=days))
    return quiet, storm


# --------------------------------------------------------------------------------------
# The decay rate, and the ratio that needs no coefficient


def test_the_decay_rate_is_a_fit_through_the_window_not_an_endpoint_difference(monkeypatch):
    """A designed decay, recovered as a slope, with the scatter kept out of the answer.

    Element sets are displaced alternately either side of the true curve, which is what real
    ones do. An endpoint estimator would take those two displacements straight into the answer;
    a straight line through all of them does not.
    """
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))
    b_true = 0.02
    sets = designed_sets(b_true=b_true, rho=rho, altitude_km=450.0, days=10, scatter_m=30.0)

    a0 = 6378.137e3 + 450e3
    expected = -b_true * rho * np.sqrt(MU * a0)  # m/s, the circular closed form
    rate = val.decay_rate(sets, val.Window("w", T0, T0 + timedelta(days=9)))

    assert rate["da_dt_m_s"] == pytest.approx(expected, rel=0.05)
    assert rate["sigma_m_s"] > 0
    assert rate["n_sets"] >= 9
    # Fewer than three sets is not a slope, and says so rather than returning one.
    short = val.decay_rate(sets, val.Window("w", T0, T0 + timedelta(days=1)))
    assert np.isnan(short["da_dt_m_s"]) and "three" in short["note"]


def test_the_observed_density_ratio_recovers_a_designed_one_with_the_coefficient_cancelled():
    """Two decay rates, one object, and `B` never enters. That is the point of the measurement.

    Built at the level of the rate table rather than from element sets, because what is being
    tested is the cancellation and the altitude correction, not the fit that produced the rates.
    """
    a = 6378.137e3 + 500e3
    rates = pd.DataFrame(
        [
            {"norad_id": 1, "window": "quiet", "da_dt_m_s": -1.0e-3, "sigma_m_s": 1e-5, "a_mean_m": a},
            {"norad_id": 1, "window": "storm", "da_dt_m_s": -2.5e-3, "sigma_m_s": 2e-5, "a_mean_m": a - 2000.0},
            # An object whose quiet decay is inside its own noise has no denominator worth using.
            {"norad_id": 2, "window": "quiet", "da_dt_m_s": -1.0e-6, "sigma_m_s": 1e-5, "a_mean_m": a},
            {"norad_id": 2, "window": "storm", "da_dt_m_s": -9.0e-3, "sigma_m_s": 2e-5, "a_mean_m": a},
        ]
    )
    out = val.observed_density_ratio(rates, "storm", "quiet", min_snr=3.0).set_index("norad_id")

    assert out.loc[1, "observed_ratio"] == pytest.approx(2.5, rel=1e-3)
    assert bool(out.loc[1, "usable"])
    assert out.loc[1, "ratio_sigma"] > 0
    # The noisy one is dropped rather than reported as a ninefold enhancement.
    assert not bool(out.loc[2, "usable"])
    assert out.loc[2, "observed_ratio"] > 1000


# --------------------------------------------------------------------------------------
# The in-track error, and the sign that decides whether any of it means anything


def test_an_object_ahead_of_its_element_set_comes_out_positive(monkeypatch):
    """The sign the whole comparison rests on, matched to the storm term's.

    More drag than the old element set knew about lowers the orbit, a lower orbit is faster, and
    the object arrives **ahead** of where the old set put it. So ``observed_shift_km`` -- later
    minus propagated, in track -- must be **positive** for an object that is ahead, which is the
    same sign :func:`driftwatch.storm.term.in_track_shift_m` returns for a positive density
    excess. Get this backwards and every residual in Step 4 is twice the signal.

    Constructed by putting the later element sets a known number of degrees ahead in mean
    anomaly, one and two whole orbits after the pivot, so the two-body phase returns to where it
    started and what is left in the comparison is the offset that was put there. This tests the
    frame and the sign, which is what can silently be wrong; the physics of the displacement is
    tested against a numerical integration in ``test_storm.py``.
    """
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    sat = circular_satrec(90600, 500.0, T0, bstar=0.0)
    pivot = element_row(sat, T0, norad_id=90600)
    period_min = 1440.0 / pivot["mean_motion"]

    rows = [pivot]
    for k, ahead_deg in ((1, 5.0), (2, 10.0)):
        later = dict(pivot)
        later["epoch"] = pd.Timestamp(T0 + timedelta(minutes=period_min * k))
        later["mean_anomaly_deg"] = (pivot["mean_anomaly_deg"] + ahead_deg) % 360.0
        rows.append(later)
    sets = pd.DataFrame(rows)

    out = val.in_track_errors(sets, T0, val.Window("w", T0, T0 + timedelta(days=1)))
    assert len(out) == 2
    assert (out["sgp4_error"] == 0).all()
    assert (out["observed_shift_km"] > 0).all(), out[["lead_days", "observed_shift_km"]]
    # Twice the offset, twice the displacement, and the size is the arc the angle subtends.
    ordered = out.sort_values("lead_days")
    assert ordered["observed_shift_km"].iloc[1] > ordered["observed_shift_km"].iloc[0]
    radius_km = (MU / (pivot["mean_motion"] * 2 * np.pi / 86400.0) ** 2) ** (1 / 3) / 1000.0
    # Within a quarter, not exactly: SGP4 advances the mean anomaly with secular J2 terms, so
    # 1440/mean_motion minutes is not quite one anomalistic revolution and about half a degree
    # of the five is the phase not having come all the way back. The size is what is being
    # checked -- hundreds of kilometres, not thousands or tens -- along with the sign.
    assert ordered["observed_shift_km"].iloc[0] == pytest.approx(np.radians(5.0) * radius_km, rel=0.25)
    # A pure along-track offset puts nothing worth reading in the other two components.
    assert (ordered["cross_km"].abs() < 1.0).all()


def test_the_pivot_never_uses_an_element_set_from_after_the_date(monkeypatch):
    """A set issued during the storm already contains it; using one would be fitting the answer."""
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))
    sets = designed_sets(b_true=0.02, rho=rho, altitude_km=450.0, days=8)
    pivot = T0 + timedelta(days=3, hours=1)

    out = val.in_track_errors(sets, pivot, val.Window("storm", T0 + timedelta(days=3), T0 + timedelta(days=8)))
    assert len(out)
    assert (out["pivot_epoch"] <= pd.Timestamp(pivot)).all()
    assert (out["epoch"] > out["pivot_epoch"]).all()
    # The pivot is the newest set at or before it, not the oldest available.
    assert out["pivot_epoch"].iloc[0] == pd.Timestamp(T0 + timedelta(days=3))
    # And with no set before the pivot at all there is nothing to compare, not a silent zero.
    assert val.in_track_errors(sets, T0 - timedelta(days=1), val.Window("s", T0, T0 + timedelta(days=8))).empty


def test_a_burn_inside_the_comparison_is_flagged_rather_than_read_as_drag(monkeypatch):
    """A satellite that raised its orbit has an along-track error that is its operator's."""
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))
    sets = designed_sets(b_true=0.02, rho=rho, altitude_km=450.0, days=10, raise_at=4, raise_m=3000.0)

    out = val.in_track_errors(sets, T0 + timedelta(hours=1), val.Window("w", T0, T0 + timedelta(days=10)))
    assert len(out) >= 6
    early = out[out["lead_days"] < 4.5]
    late = out[out["lead_days"] > 5.5]
    assert not early["manoeuvred"].any()
    assert late["manoeuvred"].all()


# --------------------------------------------------------------------------------------
# Summarising it


def test_the_slope_estimators_answer_different_questions_and_both_are_reported():
    """Least squares is pulled by one bad object; the robust one is not. That gap is the finding."""
    predicted = pd.Series([1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 0.2])
    observed = predicted * 0.6
    assert val.slope_through_origin(predicted, observed) == pytest.approx(0.6, rel=1e-6)
    assert val.robust_slope(predicted, observed) == pytest.approx(0.6, rel=1e-6)
    assert val.correlation(predicted, observed) == pytest.approx(1.0, rel=1e-6)

    # One object under active control: a large predicted shift and an along-track error that is
    # not the atmosphere's. Least squares weights it by the square of that large prediction.
    spoiled = observed.copy()
    spoiled.iloc[5] = -900.0
    assert val.slope_through_origin(predicted, spoiled) < 0.0
    # The robust estimator sees it as one ratio among the large-prediction half and takes the
    # median, so it survives. The gap between the two is the finding, not a defect in either.
    assert val.robust_slope(predicted, spoiled) == pytest.approx(0.6, rel=1e-6)


def test_the_control_is_subtracted_at_the_matching_lead_time():
    """SGP4 drifts along track with no storm at all; without the control that is read as the storm."""
    epochs = pd.to_datetime([T0 + timedelta(days=d) for d in (1, 2, 3)], utc=True)
    observed = pd.DataFrame(
        {
            "norad_id": 7,
            "epoch": epochs,
            "lead_days": [1.0, 2.0, 3.0],
            "observed_shift_km": [3.0, 8.0, 18.0],
            "manoeuvred": False,
        }
    )
    predicted = pd.DataFrame(
        {
            "norad_id": 7,
            "epoch": epochs,
            "predicted_shift_km": [2.0, 6.0, 15.0],
            "predicted_sigma_km": [1.0, 2.0, 4.0],
            "b_m2_kg": 0.02,
            "b_source": "history",
            "scoreable": True,
        }
    )
    control = pd.DataFrame(
        {
            "norad_id": 7,
            "lead_days": [0.9, 1.1, 2.0],
            "observed_shift_km": [1.0, 3.0, 4.0],  # median 2.0 at lead 1, 4.0 at lead 2
        }
    )
    out = val.residuals(observed, predicted, control)
    assert list(out["control_km"]) == [2.0, 4.0, pytest.approx(np.nan, nan_ok=True)]
    assert list(out["corrected_shift_km"]) == [1.0, 4.0, 18.0]
    assert list(out["residual_km"]) == [-1.0, -2.0, 3.0]

    summary = val.residual_summary(out)
    assert summary["n"] == 3
    assert summary["free_flying"]["n"] == 3
    assert summary["free_flying_measured_coefficient"]["n"] == 3
    assert summary["slope"] is not None
    # The lead-time structure travels with the measured population (2026-09-05), with the sign
    # agreement beside the slope pair: three rows here, so no day reaches the five-row floor.
    assert summary["free_flying_measured_coefficient"]["by_lead_day"] == {}
    assert summary["sign_agreement"] == 1.0
    table = val.lead_time_table(pd.concat([out] * 3, ignore_index=True), min_rows=3)
    assert set(table) == {1, 2, 3}
    assert table[3]["n"] == 3 and table[3]["median_abs_residual_km"] == 3.0 and table[3]["sign_agreement"] == 1.0


def test_sign_agreement_is_blind_to_the_tail_that_carries_the_slope():
    """Inside two days of lead the slope and the correlation are carried by a few large events.

    The sign agreement is the statistic that says so: a population whose typical comparison has
    the wrong sign sits below one half here however well its largest events fit.
    """
    predicted = pd.Series([1.0, 1.0, 1.0, 1.0, 40.0, 60.0])
    observed = pd.Series([-0.5, -0.4, -0.6, -0.3, 38.0, 61.0])
    assert val.correlation(predicted, observed) > 0.99
    assert val.sign_agreement(predicted, observed) == pytest.approx(2 / 6, abs=1e-3)
    assert val.sign_agreement(pd.Series([1.0, 2.0]), pd.Series([1.0, 2.0])) is None


def test_a_short_lived_object_gets_altitudes_but_not_a_decay_rate(monkeypatch):
    """February 2022: five of the lost Starlinks had under a day of element sets before they were gone."""
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    epochs = [T0 + timedelta(hours=h) for h in (0, 6, 14)]
    rows = [
        element_row(circular_satrec(90500, 230.0 - k * 5.0, t, bstar=5e-3), t, norad_id=90500)
        for k, t in enumerate(epochs)
    ]
    sets = pd.DataFrame(rows)
    sets["name"] = "STARLINK A"

    track = val.decay_history(sets)
    assert len(track) == 3
    assert track["altitude_km"].iloc[0] > track["altitude_km"].iloc[-1]
    life = val.lifetime_from_decay(track)
    assert life["span_days"] < 1.0
    assert life["drop_km"] > 0
    # A rate over well under a day is element-set scatter with a number attached; the caller says
    # so, and what this pins is that the span it would be computed over is reported beside it.
    assert life["mean_rate_km_day"] == pytest.approx(life["drop_km"] / life["span_days"], rel=0.02)
    assert life["span_days"] > 0


def test_the_storm_ratio_at_one_altitude_is_a_plain_model_evaluation():
    """The February 2022 question: does the model show anything at 210 km for a small storm?"""
    table = weather(T0 - timedelta(days=4), 12.0, kp=2.0)
    stormy = table.copy()
    inside = stormy["t"] >= pd.Timestamp(T0 + timedelta(days=2))
    stormy.loc[inside, "ap"] = 56.0
    stormy["ap_daily"] = stormy.groupby(stormy["t"].dt.floor("D"))["ap"].transform("mean")

    out = val.storm_ratio_at(stormy, 210.0, T0 + timedelta(days=3), quiet_at=T0)
    assert out["altitude_km"] == 210.0
    assert out["storm"] > out["quiet"] > 0
    # A G1 at 210 km is a small effect and the test says so: tens of per cent, not a factor.
    assert 1.0 < out["ratio"] < 1.6
    # And higher up the same storm does more, which is the physics.
    higher = val.storm_ratio_at(stormy, 500.0, T0 + timedelta(days=3), quiet_at=T0)
    assert higher["ratio"] > out["ratio"]
