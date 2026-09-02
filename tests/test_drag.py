"""Density and drag: the model inputs, the sampling step, and the ballistic coefficient.

Nothing here touches the network. NRLMSIS itself is a Fortran library shipped with pymsis, so
the density tests are real evaluations of the real model against published expectations; the
fit tests drive the real code with synthetic element sets whose decay was designed, so the
answer is known in advance.

The one that matters most is the ap vector. NRLMSIS takes a seven-element geomagnetic history
per sample, not a number, and getting it wrong produces a storm response that looks entirely
plausible and is not. It is checked here against a hand-built case.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import satrec_from_kepler

from driftwatch import config
from driftwatch.drag import ballistic as bal
from driftwatch.drag import density as dn
from driftwatch.orbit import frames
from driftwatch.weather import table as wt

T0 = datetime(2026, 9, 1, tzinfo=UTC)
MU = 3.986004418e14


def weather(start: datetime, days: float, *, kp: float = 2.0, f107: float = 100.0, ap_series=None) -> pd.DataFrame:
    """A three-hourly table with a flat index, or the given ap series, and no gaps."""
    grid = wt.intervals(start, start + timedelta(days=days))
    ap = wt.kp_to_ap(np.full(len(grid), kp)) if ap_series is None else np.asarray(ap_series, dtype=float)
    table = pd.DataFrame(
        {
            "t": grid,
            "kp": wt.ap_to_kp(ap),
            "ap": ap,
            "ap_sigma": 1.0,
            "ap_daily": ap,
            "f107": f107,
            "f107_81": f107 + 10.0,
            "f107_adj": f107 + 1.0,
            "f107_adj_81": f107 + 11.0,
            "provenance": "observed",
            "skill": "measured",
            "source": "test",
            "issued_at": pd.NaT,
        }
    )
    table["ap_daily"] = table.groupby(table["t"].dt.floor("D"))["ap"].transform("mean")
    return table


# --------------------------------------------------------------------------------------
# The model inputs


def test_the_ap_vector_is_the_seven_element_history_nrlmsis_expects():
    """Daily Ap, then now, 3, 6 and 9 hours back, then two eight-interval averages.

    Built against a table whose ap is the interval index, so every element of the answer is
    a different number and a transposition cannot pass by luck.
    """
    start = T0
    n = 40
    grid = wt.intervals(start, start + timedelta(hours=3 * (n - 1)))
    table = weather(start, 5.0)
    table = table.iloc[: len(grid)].copy()
    table["ap"] = np.arange(len(table), dtype=float)
    table["ap_daily"] = 1000.0  # distinguishable from every three-hourly value

    at = table["t"].iloc[30].to_pydatetime()
    vector = dn.ap_vector([at], table)[0]
    assert vector[0] == 1000.0  # the daily value, not one of the three-hourly ones
    assert list(vector[1:5]) == [30.0, 29.0, 28.0, 27.0]  # now, 3 h, 6 h, 9 h back
    assert vector[5] == pytest.approx(np.mean([26.0, 25.0, 24.0, 23.0, 22.0, 21.0, 20.0, 19.0]))  # 12-33 h
    assert vector[6] == pytest.approx(np.mean([18.0, 17.0, 16.0, 15.0, 14.0, 13.0, 12.0, 11.0]))  # 36-57 h

    # 57 hours of history is 19 intervals; anything shallower cannot be built and comes back
    # NaN rather than being padded with a quiet zero that would hide a storm.
    shallow = dn.ap_vector([table["t"].iloc[18].to_pydatetime()], table)[0]
    assert np.isnan(shallow).all()
    assert not np.isnan(dn.ap_vector([table["t"].iloc[19].to_pydatetime()], table)[0]).any()


def test_the_flux_is_the_previous_days_observed_value_with_the_centred_average():
    """What NRLMSIS was fitted with: yesterday's F10.7, and the 81-day average centred on today.

    The thermosphere responds to the extreme ultraviolet that arrived yesterday. Using
    today's value is a quiet few-per-cent error, so the rule is pinned here.
    """
    start = T0
    table = weather(start, 6.0)
    day = table["t"].dt.floor("D")
    # A different flux each day, so "which day" is visible in the answer.
    table["f107"] = 100.0 + (day - day.min()).dt.days * 10.0
    table["f107_81"] = 200.0 + (day - day.min()).dt.days * 10.0

    for hour in (0, 1, 12, 23):
        at = (start + timedelta(days=3, hours=hour)).replace(tzinfo=UTC)
        f107, f107a = dn.f107_inputs([at], table)
        assert f107[0] == pytest.approx(120.0)  # day 2, the day before this one
        assert f107a[0] == pytest.approx(230.0)  # day 3, centred on today
    # The adjusted flux is carried in the table but never fed to the model: the atmosphere
    # feels the flux that arrives, not the flux scaled to 1 AU.
    assert "f107_adj" in table.columns


def test_a_missing_driver_gives_no_density_rather_than_a_quiet_day():
    table = weather(T0, 5.0)
    table.loc[table.index[25], "ap"] = np.nan
    at = table["t"].iloc[30].to_pydatetime()
    inputs = dn.msis_inputs([at], table)
    assert inputs.n_incomplete == 1
    rho = dn.density([at], [0.0], [0.0], [400.0], inputs)
    assert np.isnan(rho[0])


# --------------------------------------------------------------------------------------
# The model itself


def test_quiet_density_is_within_the_published_range_and_falls_with_altitude():
    """The sanity check the prompt asks for: 300, 400, 500 and 600 km against published values.

    The bands are wide because the real spread is wide: density at 400 km runs from about
    5e-13 kg/m^3 at solar minimum to 8e-12 at solar maximum, and the published tables
    (US Standard Atmosphere 1976, CIRA) sit near the top of that. What is checked is that
    the model lands inside the physical range at each altitude, that it falls monotonically,
    and that the day-night contrast grows with height -- which it does because the diurnal
    bulge is a temperature effect and a hotter atmosphere is a taller one.
    """
    table = weather(T0, 6.0, kp=2.0, f107=150.0)
    at = T0 + timedelta(days=4)
    profile = dn.quiet_density_profile(table, at=at)
    bands = {300.0: (5e-12, 6e-11), 400.0: (3e-13, 1e-11), 500.0: (4e-14, 3e-12), 600.0: (5e-15, 1e-12)}
    for row in profile.itertuples():
        lo, hi = bands[row.altitude_km]
        assert lo < row.rho_mean_kg_m3 < hi, f"{row.altitude_km} km: {row.rho_mean_kg_m3:.3e}"
    assert (profile["rho_mean_kg_m3"].diff().dropna() < 0).all()
    assert (profile["day_night_ratio"].diff().dropna() > 0).all()


def test_a_storm_raises_the_density_and_raises_it_more_the_higher_you_are():
    """G5 above G3 above quiet, and the ratio grows with altitude, which is the physics.

    A geomagnetic storm heats the lower thermosphere; the atmosphere expands, and the density
    at a fixed height rises by more the further that height is above the heating.
    """
    table = weather(T0, 6.0, kp=1.0, f107=120.0)
    at = T0 + timedelta(days=4)
    g3 = dn.storm_ratio(table, 7.0, at=at)
    g5 = dn.storm_ratio(table, 9.0, at=at)
    assert (g3["ratio"] > 1.0).all()
    assert (g5["ratio"] > g3["ratio"]).all()
    assert g5["ratio"].iloc[-1] > g5["ratio"].iloc[0]
    # A G5 at 400 km is a factor of a few, not a factor of a hundred.
    assert 2.0 < float(g5.loc[g5["altitude_km"] == 400.0, "ratio"].iloc[0]) < 12.0


# --------------------------------------------------------------------------------------
# The sampling step


def test_the_step_tightens_for_eccentric_orbits_and_stays_inside_its_bounds():
    """A near-circular orbit is sampled by local time; an eccentric one by its perigee passage."""
    circular = dn.sample_step_s(15.5, 0.0001)
    assert circular == pytest.approx(86400.0 / 15.5 / config.DENSITY_SAMPLES_PER_ORBIT)
    assert dn.sample_step_s(15.5, 0.008) < circular
    assert dn.sample_step_s(15.5, 0.02) < dn.sample_step_s(15.5, 0.008)
    # Clamped at both ends whatever the rule says.
    assert dn.sample_step_s(15.5, 0.8) == config.DENSITY_MIN_STEP_S
    assert dn.sample_step_s(0.5, 0.0) == config.DENSITY_MAX_STEP_S


# --------------------------------------------------------------------------------------
# The ballistic coefficient


def circular_satrec(norad_id: int, altitude_km: float, epoch: datetime, *, bstar: float = 0.0):
    """An equatorial circular orbit. Equatorial because the J2 short-period variation in the
    semi-major axis goes as sin^2(i) cos(2u) and vanishes at zero inclination, which keeps a
    designed decay of a few hundred metres a day visible instead of buried under ten
    kilometres of periodic wobble."""
    a_km = 6378.137 + altitude_km
    return satrec_from_kepler(norad_id, epoch, a_km, 0.0, 0.0, 0.0, 0.0, 0.0, bstar=bstar)


def element_row(sat, epoch: datetime, norad_id: int = 90000, name: str = "DESIGNED") -> dict:
    return {
        "norad_id": norad_id,
        "name": name,
        "epoch": pd.Timestamp(epoch),
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


def bstar_for_decay(altitude_km: float, epoch: datetime, decay_m_per_day: float) -> float:
    """The B* whose own SGP4 decay matches a designed one, found by scaling a trial value.

    Element sets must carry a drag term consistent with the decay they show, or the manoeuvre
    detector will -- correctly -- read a steadily dropping orbit with no modelled drag as a
    string of de-orbit burns. SGP4's decay is very nearly linear in B*, so one trial and a
    scale is enough.
    """
    trial = 1e-4
    row = pd.Series(element_row(circular_satrec(90000, altitude_km, epoch, bstar=trial), epoch))
    measured, _ = bal.bstar_decay_m(row, 1.0)
    return float(trial * decay_m_per_day / measured)


def designed_sets(
    *,
    b_true: float,
    rho: float,
    altitude_km: float,
    days: int,
    raise_at: int | None = None,
    raise_m: float = 0.0,
    scatter_m: float = 0.0,
) -> pd.DataFrame:
    """One element set a day for an orbit decaying at exactly the rate ``b_true`` implies.

    With ``raise_at`` a burn of ``raise_m`` is inserted between that interval's two sets, so
    the manoeuvre detector has something real to find. With ``scatter_m`` each set is
    displaced by that much, alternating in sign: deterministic, so the test is not a coin
    toss, and never more than ``2 * scatter_m`` between neighbours, which keeps it under the
    manoeuvre detector's 100 m floor and so tests the acceptance rule rather than the
    detector.
    """
    a0 = 6378.137e3 + altitude_km * 1e3
    rate = b_true * rho * np.sqrt(MU * a0)  # m/s, the circular closed form
    bstar = bstar_for_decay(altitude_km, T0, rate * 86400.0)
    rows = []
    for k in range(days):
        epoch = T0 + timedelta(days=k)
        a_k = a0 - rate * (epoch - T0).total_seconds()
        if raise_at is not None and k > raise_at:
            a_k += raise_m
        a_k += scatter_m * (1.0 if k % 2 else -1.0)
        sat = circular_satrec(90000 + k, (a_k - 6378.137e3) / 1000.0, epoch, bstar=bstar)
        rows.append(element_row(sat, epoch))
    return pd.DataFrame(rows)


def test_the_decay_inversion_is_the_general_form_not_the_circular_one():
    """``da = -(B a^2 / mu) * integral(rho |v_rel| (v_rel . v) dt)``, checked by hand.

    For a circular orbit with a still atmosphere the integral is ``rho v^3 T`` with
    ``v = sqrt(mu/a)``, which collapses to ``da = -B rho sqrt(mu a) T``. Both forms are
    evaluated here and they agree, which is what makes the general one safe to use everywhere.
    """
    a = 6_778_137.0  # 400 km
    v = np.sqrt(MU / a)
    rho = 1e-12
    seconds = 86400.0
    b_true = 0.01
    integral = rho * v**3 * seconds
    decay = b_true * a**2 * integral / MU
    assert bal.coefficient_from_decay(decay, integral, a) == pytest.approx(b_true)
    # The circular form, written out, gives the same drop.
    assert decay == pytest.approx(b_true * rho * np.sqrt(MU * a) * seconds)
    # Nonsense in, NaN out rather than a confident wrong answer.
    assert np.isnan(bal.coefficient_from_decay(decay, 0.0, a))
    assert np.isnan(bal.coefficient_from_decay(np.nan, integral, a))


def test_the_fit_recovers_a_designed_ballistic_coefficient(monkeypatch):
    """Element sets built to decay by exactly what a known B would give, fitted back.

    The atmosphere is held still (no co-rotation) and its density constant, so the expected
    decay has a closed form and the test knows the answer without asking the code for it.
    """
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))

    b_true = 0.02
    sets = designed_sets(b_true=b_true, rho=rho, altitude_km=450.0, days=12)
    table = weather(T0 - timedelta(days=4), 20.0)
    fit = bal.fit_from_history(sets, table, step_s=300.0)
    assert fit.source == "history", fit.note
    assert fit.b_m2_kg == pytest.approx(b_true, rel=0.05)
    assert fit.n_intervals == 11
    assert fit.decay_m > config.BALLISTIC_MIN_DECAY_M


def test_a_burn_in_the_history_is_excluded_rather_than_read_as_negative_drag(monkeypatch):
    """A station-keeping raise inside the window must not be fitted as an atmosphere pushing back."""
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))

    b_true = 0.02
    burn_at = 6
    raise_m = 2000.0  # about seven days of decay, undone in one interval
    sets = designed_sets(b_true=b_true, rho=rho, altitude_km=450.0, days=12, raise_at=burn_at, raise_m=raise_m)
    table = weather(T0 - timedelta(days=4), 20.0)

    jump, _ = bal.manoeuvre_intervals(sets)
    assert jump[burn_at], "the detector should see a 2 km raise"

    fit = bal.fit_from_history(sets, table, step_s=300.0)
    assert fit.n_manoeuvre_excluded >= 1
    assert fit.b_m2_kg == pytest.approx(b_true, rel=0.1)
    # Without the exclusion the raise would cancel most of the decay and the coefficient would
    # come back far too small; this is what the exclusion is worth.
    a_m = bal.mean_sma_m(sets)
    assert (a_m[0] - a_m[-1]) < 0.5 * fit.decay_m

    # And the burn must not reappear as element-set scatter. The exclusion leaves two runs of
    # sets; a curve fitted across the gap between them would read the 2 km raise as noise,
    # inflate the decay's uncertainty by a kilometre and refuse the very fit the exclusion
    # made possible. Measured inside each run, these designed sets have no scatter at all.
    assert bal.runs_of_sets(np.array([True] * 6 + [False] + [True] * 4)) == [(0, 7), (7, 12)]
    assert fit.scatter_m < 1.0, f"the burn leaked into the scatter: {fit.scatter_m:.0f} m"
    assert fit.decay_snr > config.BALLISTIC_MIN_DECAY_SNR


def test_an_object_whose_decay_says_nothing_falls_back_and_says_so():
    """Too few sets, too small a decay, an implausible B: each is refused with its reason."""
    table = weather(T0 - timedelta(days=4), 20.0)
    epochs = [T0 + timedelta(days=k) for k in range(3)]
    sets = pd.DataFrame(
        [element_row(circular_satrec(90100 + k, 800.0, t), t, norad_id=90100, name="FEW") for k, t in enumerate(epochs)]
    )
    fit = bal.fit_from_history(sets, table)
    assert fit.source == "none" and "too few element sets" in fit.note

    # A zero B* implies no decay at all, which is not a physical coefficient either.
    coefficient = bal.from_bstar(sets.iloc[-1], table, days=5.0)
    assert coefficient.source == "none" and "no decay" in coefficient.note

    # And the run's own typical value stands in, labelled, rather than a silent zero.
    elements = sets.iloc[[-1]].assign(category="debris")
    frame = bal.coefficients(elements, table, history=None, store=None)
    assert list(frame["source"]) == ["typical"]
    assert frame["b_m2_kg"].iloc[0] == pytest.approx(config.BALLISTIC_TYPICAL_M2_KG)
    assert "stood in" in frame["note"].iloc[0]
    # Never silently certain: a stand-in carries at least a factor of two.
    assert frame["b_sigma_m2_kg"].iloc[0] >= config.BALLISTIC_SIGMA_REL_TYPICAL * frame["b_m2_kg"].iloc[0]
    assert frame["alt_band"].iloc[0] == "650-800"


# --------------------------------------------------------------------------------------
# What the Step 2 review asked for: the acceptance rule, the bands, the uncertainty, the cache


def test_a_fit_is_accepted_against_the_objects_own_scatter_not_a_fixed_number_of_metres(monkeypatch):
    """The same decay is a measurement on quiet elements and noise on scattered ones.

    The review's threshold: the drop in mean semi-major axis has to exceed the uncertainty
    the element-set scatter puts on it by about three. Both objects here decay by the same
    designed amount; they differ only in how much their element sets bounce, and that alone
    decides whether a coefficient comes back.
    """
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))
    table = weather(T0 - timedelta(days=4), 20.0)
    # 120 m of designed decay over eleven days. The alternating scatter displaces the two end
    # sets in opposite directions, so what is *measured* is 120 - 2*scatter: 70 m for the noisy
    # object and 116 m for the quiet one. Both clear the 20 m floor, and neither is anywhere
    # near a fixed threshold that could separate them -- only the scatter can.
    b_small = 0.02 * 120.0 / 2972.0

    noisy = bal.fit_from_history(
        designed_sets(b_true=b_small, rho=rho, altitude_km=450.0, days=12, scatter_m=25.0), table, step_s=300.0
    )
    assert noisy.source == "none"
    assert noisy.decay_snr < config.BALLISTIC_MIN_DECAY_SNR
    assert "times its own uncertainty" in noisy.note
    assert noisy.scatter_m == pytest.approx(25.0, rel=0.3)

    quiet = bal.fit_from_history(
        designed_sets(b_true=b_small, rho=rho, altitude_km=450.0, days=12, scatter_m=2.0), table, step_s=300.0
    )
    assert quiet.source == "history", quiet.note
    assert quiet.decay_snr > config.BALLISTIC_MIN_DECAY_SNR
    # The two decays are the same to within their own scatter; only the scatter differs.
    assert quiet.decay_m == pytest.approx(noisy.decay_m, abs=4 * 25.0)


def test_every_accepted_coefficient_carries_an_uncertainty_step_3_can_propagate(monkeypatch):
    """A fitted B gets the statistical error of its own decay; a B* and a stand-in get priors."""
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))
    table = weather(T0 - timedelta(days=4), 20.0)

    fit = bal.fit_from_history(
        designed_sets(b_true=0.02, rho=rho, altitude_km=450.0, days=12, scatter_m=20.0), table, step_s=300.0
    )
    assert fit.source == "history"
    # sigma/B is 1/snr, floored: a designed decay is never known better than the floor says.
    assert fit.b_sigma_m2_kg / fit.b_m2_kg == pytest.approx(
        max(1.0 / fit.decay_snr, config.BALLISTIC_SIGMA_REL_FLOOR), rel=1e-6
    )
    assert fit.b_sigma_m2_kg > 0

    row = pd.Series(element_row(circular_satrec(90500, 500.0, T0, bstar=1e-4), T0, norad_id=90500))
    from_bstar = bal.from_bstar(row, table, days=5.0, step_s=300.0)
    assert from_bstar.source == "bstar"
    assert from_bstar.b_sigma_m2_kg == pytest.approx(config.BALLISTIC_SIGMA_REL_BSTAR * from_bstar.b_m2_kg)


def test_the_typical_value_is_taken_by_category_and_drag_altitude_band():
    """The review's instruction: medians by category *and* altitude band, not category alone.

    Two bands of the same category with coefficients an order of magnitude apart. An object
    falling back in one of them must take its own band's median, because what its coefficient
    has in common with another object's is the density its decay was measured in.
    """
    low = [{"b_m2_kg": 0.01, "source": "history", "category": "debris", "alt_band": "450-550"}] * 6
    high = [{"b_m2_kg": 0.20, "source": "history", "category": "debris", "alt_band": "650-800"}] * 6
    fitted = pd.DataFrame(low + high)

    b_low, sigma_low, why_low = bal.typical_coefficient(fitted, "debris", "450-550")
    b_high, _, why_high = bal.typical_coefficient(fitted, "debris", "650-800")
    assert b_low == pytest.approx(0.01) and b_high == pytest.approx(0.20)
    assert "450-550" in why_low and "650-800" in why_high
    # Sigma is the spread of the pool, floored: an identical pool still carries a factor of two.
    assert sigma_low == pytest.approx(config.BALLISTIC_SIGMA_REL_TYPICAL * 0.01)

    # A band with too few fits falls back to the category, and says so.
    _, _, why_any = bal.typical_coefficient(fitted, "debris", "0-350")
    assert "any altitude" in why_any

    # And the bands themselves come from the element set, not from a column somebody may forget.
    assert bal.altitude_band(420.0) == "350-450"
    assert bal.altitude_band(693.0) == "650-800"
    assert bal.altitude_band(1500.0) == ">1200"
    assert bal.altitude_band(float("nan")) == "unknown"
    iss_like = pd.Series({"mean_motion": 15.5, "eccentricity": 0.0005})
    assert bal.band_for_row(iss_like) == "350-450"


def test_the_fit_budget_falls_back_rather_than_running_over(monkeypatch):
    """A run with no time to fit anything still answers, from B*, and says the budget stopped it."""
    monkeypatch.setattr(frames, "EARTH_ROTATION_RATE", 0.0)
    rho = 3e-12
    monkeypatch.setattr(dn, "density", lambda times, lat, lon, alt, inputs: np.full(len(np.asarray(alt)), rho))
    table = weather(T0 - timedelta(days=4), 20.0)
    sets = designed_sets(b_true=0.02, rho=rho, altitude_km=450.0, days=12)
    elements = sets.iloc[[-1]].assign(category="payload")
    history = sets.assign(norad_id=90000)

    generous = bal.coefficients(elements, table, history, step_s=300.0, budget_s=0.0, store=None)
    assert generous["source"].iloc[0] == "history"

    # A budget of a nanosecond is exhausted before the first object, so nothing is fitted.
    spent = bal.coefficients(elements, table, history, step_s=300.0, budget_s=1e-9, store=None)
    assert spent["source"].iloc[0] in ("bstar", "typical")
    assert "budget" in spent["note"].iloc[0]
    assert spent.attrs["budget"]["n_over_budget"] == 1


def test_a_fitted_coefficient_is_cached_and_refitted_only_when_it_should_be(tmp_path):
    """The cache keeps the history span it used, and the three things that invalidate it."""
    from driftwatch.drag.store import CoefficientStore

    store = CoefficientStore(tmp_path)
    now = datetime(2026, 9, 2, tzinfo=UTC)
    history_end = datetime(2026, 9, 1, tzinfo=UTC)
    row = bal.Coefficient(41335, 0.0087, "history", b_sigma_m2_kg=0.0004).as_row()
    store.put(row, history_start=datetime(2026, 7, 1, tzinfo=UTC), history_end=history_end, now=now)

    assert store.usable(41335, history_end=history_end, now=now)["b_m2_kg"] == pytest.approx(0.0087)
    # A day of new element sets is not worth refitting for; a fortnight is.
    assert store.usable(41335, history_end=history_end + timedelta(days=1), now=now) is not None
    assert store.usable(41335, history_end=history_end + timedelta(days=14), now=now) is None
    # Nor does a fit stand for ever.
    assert store.usable(41335, history_end=history_end, now=now + timedelta(days=90)) is None
    # And a fit made against another atmosphere is not a fit against this one: only the
    # product B*rho is observable from a decay.
    store.rows[41335]["msis_version"] = "0"
    assert store.usable(41335, history_end=history_end, now=now) is None
    store.rows[41335]["msis_version"] = str(config.MSIS_VERSION)
    # Nor is a fit accepted under different rules. Without this a change to what counts as a
    # good enough decay would reach new objects and leave the cached ones as they were.
    store.rows[41335]["rules_version"] = "0"
    assert store.usable(41335, history_end=history_end, now=now) is None
    store.rows[41335]["rules_version"] = str(config.BALLISTIC_RULES_VERSION)
    assert store.usable(41335, history_end=history_end, now=now) is not None

    # A rejection is cached too -- it cost the same hundred evaluations to find out.
    refused = bal.Coefficient(99999, float("nan"), "none", note="decay is inside the scatter").as_row()
    store.put(refused, history_start=None, history_end=history_end, now=now)
    store.save()
    reloaded = CoefficientStore(tmp_path).load()
    assert reloaded.usable(99999, history_end=history_end, now=now)["source"] == "none"
    assert reloaded.summary(now=now)["n"] == 2

    # A bstar or typical coefficient is a property of one element set or one run, not of the
    # object, so it is never stored.
    store.put(bal.Coefficient(1, 0.01, "bstar").as_row(), history_start=None, history_end=None, now=now)
    assert 1 not in store.rows


# --------------------------------------------------------------------------------------
# Against NRL's own published output


# Rows of NRL's reference output for NRLMSIS 2.1, distributed with the model and shipped with
# pymsis as `tests/msis2.1_test_ref_dp.txt`. Columns: (yyddd, seconds of day, altitude km,
# latitude, longitude, F10.7 81-day average, F10.7 previous day, Ap, total mass density in
# kg/m^3 -- the file publishes g/cm^3 and these are multiplied by 1000).
#
# All four have Ap = 4, which is the value at which NRLMSIS's daily-Ap mode and its
# storm-time seven-element mode agree; NRL's file was produced in the daily mode and
# driftwatch always drives the storm-time one, so these are the rows on which the two can be
# compared without confounding the model's own two answers. The rows at other Ap are used
# below to measure exactly how far apart those two modes are.
NRL_REFERENCE: tuple[tuple[str, float, float, float, float, float, float, float, float], ...] = (
    ("76138", 83955.0, 349.9, 4.2, -20.6, 72.4, 77.4, 4.0, 1.5860e-12),
    ("78279", 63960.0, 379.2, -8.1, 14.2, 156.5, 138.7, 4.0, 6.2060e-12),
    ("88156", 58563.0, 434.6, 3.0, -4.3, 129.9, 145.2, 3.0, 2.2890e-12),
    ("6257", 18301.0, 500.0, -47.6, 125.3, 77.6, 82.9, 4.0, 1.8790e-13),
)


def reference_case(iyd: str, sec: float, f107a: float, f107: float, ap: float):
    """``(sample time, weather table)`` reproducing one NRL reference row's drivers."""
    year = int(iyd[:-3])
    year += 1900 if year > 60 else 2000
    at = datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=int(iyd[-3:]) - 1, seconds=sec)
    # The table has to reach 57 hours behind the sample for the ap history and a day behind
    # for the previous day's flux; the drivers are flat, which is what a single reference row
    # states.
    table = weather(at - timedelta(days=5), 7.0, f107=f107)
    table["ap"] = ap
    table["ap_daily"] = ap
    table["kp"] = wt.ap_to_kp(np.full(len(table), ap))
    table["f107"] = f107
    table["f107_81"] = f107a
    return at, table


def test_the_density_matches_nrls_own_published_reference_output():
    """End-to-end against NRL's published NRLMSIS 2.1 reference rows: better than one per cent.

    The US Standard Atmosphere 1976 comparison in ``docs/density-and-drag.md`` measures the
    1976 profile's known bias as much as anything of ours. This measures our plumbing: the
    table lookup, the previous day's flux, the 81-day average, the seven-element ap vector,
    the units and the pymsis call, against numbers NRL published for this model at stated
    drivers. Anything wrong in the driving shows up here as tens of per cent.
    """
    for iyd, sec, alt, lat, lon, f107a, f107, ap, expected in NRL_REFERENCE:
        at, table = reference_case(iyd, sec, f107a, f107, ap)
        inputs = dn.msis_inputs([at], table)
        assert inputs.n_incomplete == 0
        rho = dn.density([at], [lat], [lon], [alt], inputs)[0]
        assert rho == pytest.approx(expected, rel=0.01), f"{iyd} at {alt} km: {rho:.4e} against {expected:.4e}"


def test_the_seven_element_ap_mode_is_the_one_that_answers_a_storm():
    """Why the reference rows above are the Ap = 4 ones, stated as a measurement.

    NRLMSIS has two geomagnetic modes and they are not the same model. The daily-Ap mode NRL's
    reference file was produced in and the storm-time mode ``density()`` always asks for agree
    at Ap = 4 -- the model's quiet baseline -- and diverge as the index rises, which is the
    whole reason the seven-element vector exists. If they agreed everywhere, building it would
    not matter.
    """
    at, table = reference_case("78279", 63960.0, 156.5, 138.7, 4.0)
    quiet = dn.density([at], [-8.1], [14.2], [379.2], dn.msis_inputs([at], table))[0]
    at_storm, stormy = reference_case("78279", 63960.0, 156.5, 138.7, 80.0)
    storm = dn.density([at_storm], [-8.1], [14.2], [379.2], dn.msis_inputs([at_storm], stormy))[0]
    assert storm > 1.3 * quiet, "a sustained Ap of 80 has to move the density"
