"""The empirical covariance and the manoeuvre detector.

The power-law fit recovers designed error growth (a period error grows linearly in-track,
a timing error is a flat floor); thin history falls back to the pool and then to the
defaults with the right source labels; a burn is detected and the pairs across it are
kept out of the fit; a reversed jump is an outlier element set, not two burns; the model
satisfies the protocol Phase 3 will implement.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import history_records, raised_copy

from driftwatch.catalogue import history
from driftwatch.orbit.propagator import WGS72_MU_KM3_S2, satrec_from_elements
from driftwatch.risk.covariance import (
    DEFAULT_GROWTH,
    CovarianceModel,
    EmpiricalCovariance,
    ObjectRef,
    PowerLawGrowth,
    ScaledCovariance,
    SupplementalCovariance,
    analyse_object,
    fit_covariance,
    fit_supplemental_covariance,
    label_cov_sources,
    median_growth,
    sigma_table,
    sufficient_stats,
)
from driftwatch.risk.manoeuvre import detect_jumps, manoeuvre_prior, promote
from driftwatch.screening import supplemental as sup_mod

T0 = datetime(2026, 7, 20, tzinfo=UTC)
BASE_ID = 90100
MEAN_MOTION_REV_DAY = 15.2


def base_orbit(norad_id: int = BASE_ID, epoch: datetime = T0, bstar: float = 1e-4):
    """A sun-synchronous-ish orbit at about 500 km with some drag."""
    return satrec_from_elements(norad_id, epoch, MEAN_MOTION_REV_DAY, 0.001, 97.4, 200.0, 80.0, 10.0, bstar)


def semi_major_axis_km() -> float:
    n = MEAN_MOTION_REV_DAY * 2.0 * np.pi / 86400.0
    return float((WGS72_MU_KM3_S2 / n**2) ** (1.0 / 3.0))


def epochs_every(hours: float, days: float, start: datetime = T0) -> list[datetime]:
    return [start + timedelta(hours=float(h)) for h in np.arange(0.0, days * 24.0 + 1e-9, hours)]


def history_frame(records: list[dict]) -> pd.DataFrame:
    stringified = [{k: str(v) for k, v in r.items()} for r in records]
    return history.frame_from_records(stringified, fetched_at=T0 + timedelta(days=60))


# --------------------------------------------------------------------------------------
# The fit


def test_profile_likelihood_recovers_a_designed_power_law():
    rng = np.random.default_rng(0)
    dt = rng.uniform(0.5, 7.0, 600)
    s1 = np.array([0.05, 0.8, 0.03])
    p = np.array([0.3, 1.2, 0.0])
    residuals = rng.normal(size=(600, 3)) * (s1[None, :] * dt[:, None] ** p[None, :])
    growth = sufficient_stats(dt, residuals).fit()
    assert growth is not None
    np.testing.assert_allclose(growth.exponent, p, atol=0.1)
    np.testing.assert_allclose(growth.sigma_1d_km, s1, rtol=0.15)
    # Pooling by addition: the stats of two halves add to the stats of the whole.
    a = sufficient_stats(dt[:300], residuals[:300])
    a.add(sufficient_stats(dt[300:], residuals[300:]))
    whole = sufficient_stats(dt, residuals)
    np.testing.assert_allclose(a.s, whole.s)
    assert a.n == whole.n and a.log_dt_sum == pytest.approx(whole.log_dt_sum)
    assert sufficient_stats(np.zeros(0), np.zeros((0, 3))).fit() is None


def test_period_noise_grows_linearly_in_track_and_timing_noise_is_a_flat_floor():
    """The two textbook shapes of element-set error, recovered through SGP4 and the RIC differencing."""
    rng = np.random.default_rng(1)
    base = base_orbit()
    epochs = epochs_every(12.0, 30.0)
    a_km = semi_major_axis_km()

    sigma_n_rel = 1e-6
    drift = history_frame(history_records(BASE_ID, lambda t: base, epochs, rng, sigma_n_rel=sigma_n_rel))
    fit = analyse_object(drift)
    assert fit.enough_history and fit.n_sets == len(epochs) and fit.jumps.n_jumps == 0
    growth = fit.growth
    assert growth is not None
    n_rad_s = MEAN_MOTION_REV_DAY * 2.0 * np.pi / 86400.0
    expected_s1 = a_km * sigma_n_rel * n_rad_s * 86400.0  # in-track drift per day from a period error
    assert abs(growth.exponent[1] - 1.0) <= 0.1
    assert abs(growth.sigma_1d_km[1] / expected_s1 - 1.0) < 0.3
    assert growth.sigma_1d_km[0] < 0.05 and growth.sigma_1d_km[2] < 0.05  # radial and cross-track stay small

    # Timing noise on a drag-free orbit. With drag on, SGP4 is not invariant under re-initialisation: a set
    # fitted at a later epoch with the same B* drifts in-track by about 0.07 km per day at B* = 1e-4 (measured),
    # which would masquerade as growth here; with B* = 0 the mean-element inversion is exact.
    sigma_m = 1.5e-5
    dragless = base_orbit(bstar=0.0)
    flat = history_frame(history_records(BASE_ID, lambda t: dragless, epochs, rng, sigma_m_rad=sigma_m, bstar=0.0))
    fit2 = analyse_object(flat)
    growth2 = fit2.growth
    assert growth2 is not None
    assert growth2.exponent[1] <= 0.15
    expected_floor = a_km * sigma_m * np.sqrt(2.0)  # the difference of two independent timing errors
    assert abs(growth2.sigma_1d_km[1] / expected_floor - 1.0) < 0.3


def test_a_burn_is_detected_and_pairs_across_it_are_kept_out_of_the_fit():
    rng = np.random.default_rng(2)
    base = base_orbit()
    epochs = epochs_every(12.0, 30.0)
    t_burn = T0 + timedelta(days=15, hours=3)
    after = raised_copy(base, t_burn, 1.0)

    def truth(t: datetime):
        return base if t < t_burn else after

    burned = history_frame(history_records(BASE_ID, truth, epochs, rng, sigma_n_rel=1e-6))
    clean = history_frame(history_records(BASE_ID, lambda t: base, epochs, rng, sigma_n_rel=1e-6))
    fit = analyse_object(burned, max_pairs=100_000)
    ref = analyse_object(clean, max_pairs=100_000)
    first_after = next(t for t in epochs if t >= t_burn)
    assert fit.jumps.n_jumps == 1 and fit.jumps.jump_epochs == [first_after]
    assert abs(fit.jumps.jump_delta_a_km[0] - 1.0) < 0.1
    assert fit.jumps.bad_set_epochs == []
    assert ref.jumps.n_jumps == 0
    assert fit.n_pairs < ref.n_pairs  # every pair that spans the burn is gone
    assert fit.growth is not None and ref.growth is not None
    assert 0.6 < fit.growth.sigma_1d_km[1] / ref.growth.sigma_1d_km[1] < 1.5  # the burn did not leak into the fit
    assert abs(fit.growth.exponent[1] - 1.0) <= 0.15


def test_a_reversed_jump_is_one_bad_element_set_not_two_burns():
    rng = np.random.default_rng(3)
    base = base_orbit()
    epochs = epochs_every(12.0, 20.0)
    odd = epochs[17]
    outlier = raised_copy(base, odd, 1.0)
    frame = history_frame(
        history_records(BASE_ID, lambda t: outlier if t == odd else base, epochs, rng, sigma_n_rel=1e-6)
    )
    clean = history_frame(history_records(BASE_ID, lambda t: base, epochs, np.random.default_rng(3), sigma_n_rel=1e-6))
    fit = analyse_object(frame)
    ref = analyse_object(clean)
    assert fit.jumps.n_jumps == 0
    assert fit.jumps.bad_set_epochs == [odd]
    assert fit.growth is not None and ref.growth is not None
    assert 0.8 < fit.growth.sigma_1d_km[1] / ref.growth.sigma_1d_km[1] < 1.25  # the outlier is not in the residuals


def test_detect_jumps_thresholds_raise_lower_reversal_gap_and_nan():
    # Intervals: a raise above the floor and half the drag change; a raise below it; a lowering within twice
    # the drag change (a storm, not a burn); a lowering beyond it; a long gap; a NaN.
    da_drag = np.array([-0.3, -0.3, -0.3, -0.3, -0.3, -0.3])
    a_free = np.zeros(6)
    a_prop = a_free + da_drag
    unexplained = np.array([0.2, 0.12, -0.5, -0.8, 5.0, np.nan])
    a_fit = a_prop + unexplained
    dt = np.array([0.5, 0.5, 0.5, 0.5, 12.0, 0.5])
    jump, bad = detect_jumps(a_fit, a_prop, a_free, dt)
    assert jump.tolist() == [True, False, False, True, False, False]
    assert not bad.any() and len(bad) == 7
    # A raise followed by an equal fall is one bad set between them.
    jump, bad = detect_jumps(np.array([1.0, -1.0, 0.0]) - 0.3, np.array([-0.3] * 3), np.zeros(3), np.full(3, 0.5))
    assert jump.tolist() == [False, False, False] and bad.tolist() == [False, True, False, False]
    empty_jump, empty_bad = detect_jumps(np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0))
    assert len(empty_jump) == 0 and empty_bad.tolist() == [False]


def test_manoeuvre_prior_is_three_valued_and_only_possible_can_be_promoted():
    assert manoeuvre_prior("starlink", False) == "known"
    assert manoeuvre_prior("station", True) == "known"
    assert manoeuvre_prior("payload", True) == "possible"
    assert manoeuvre_prior("payload", False) == "none"
    assert manoeuvre_prior("debris", True) == "none"
    assert manoeuvre_prior("rocket_body", True) == "none"
    assert manoeuvre_prior("debris", True, fleet_flag=True) == "known"
    assert manoeuvre_prior("starlink", True, fleet_flag=False) == "none"
    assert promote("possible", 2) == "observed"
    assert promote("possible", 0) == "possible"
    assert promote("known", 3) == "known" and promote("none", 3) == "none"


# --------------------------------------------------------------------------------------
# The model: labels, fallbacks, persistence, protocol


def test_fit_covariance_labels_empirical_pooled_and_default_and_round_trips():
    rng = np.random.default_rng(4)
    base = base_orbit()
    rich = history_records(BASE_ID, lambda t: base, epochs_every(12.0, 30.0), rng, sigma_n_rel=1e-6)
    thin_ids = list(range(90201, 90213))
    thin = []
    for k, norad_id in enumerate(thin_ids):
        epochs = epochs_every(48.0, 6.0, start=T0 + timedelta(days=k))
        thin.extend(history_records(norad_id, lambda t: base, epochs, rng, sigma_n_rel=2e-6, name=f"THIN {k}"))
    single = history_records(90301, lambda t: base, [T0 + timedelta(days=3)], rng)
    hist = history_frame(rich + thin + single)
    objects = pd.DataFrame(
        {
            "norad_id": [BASE_ID, *thin_ids, 90300, 90301],
            "category": ["payload"] * 13 + ["debris", "payload"],
            "altitude_band": ["leo"] * 14 + ["meo"],
        }
    )
    fit = fit_covariance(hist, objects, now=T0 + timedelta(days=60))
    model = fit.model
    table = fit.table
    by_id = table[table["kind"] == "object"].set_index("norad_id")
    assert by_id.loc[BASE_ID, "source"] == "empirical"
    assert (by_id.loc[thin_ids, "source"] == "pooled:payload/leo").all()
    assert by_id.loc[90300, "source"] == "default:leo" and by_id.loc[90301, "source"] == "default:meo"
    assert fit.summary["by_source"] == {"empirical": 1, "pooled": 12, "default": 2}
    assert fit.summary["n_pools"] == 1 and fit.summary["n_objects"] == 15
    pool = table[table["kind"] == "pool"].iloc[0]
    # Every object's residuals join its pool, the one with its own fit included; with a single fitted
    # member the pool is the fit to the pooled residuals.
    assert pool["n_objects"] == 13 and pool["n_fitted"] == 1 and pool["n_pairs"] >= 30
    assert abs(pool["p_i"] - 1.0) <= 0.2
    assert set(table["kind"]) == {"object", "pool", "default"}

    # The covariance at absolute times: diagonal, floored at half a day, labelled.
    ref = ObjectRef(BASE_ID, "payload", "leo")
    epoch = T0 + timedelta(days=10)
    at = np.asarray(
        [np.datetime64(t.replace(tzinfo=None), "us") for t in (epoch + timedelta(hours=1), epoch + timedelta(days=3))]
    )
    cov = model.covariance_ric(ref, epoch, at)
    assert cov.source == "empirical" and cov.cov_km2.shape == (2, 3, 3)
    growth = model.objects[BASE_ID]
    expected = growth.sigma_km(np.array([0.5, 3.0])) ** 2  # one hour is floored to half a day
    np.testing.assert_allclose(cov.cov_km2[:, [0, 1, 2], [0, 1, 2]], expected)
    off_diagonal = cov.cov_km2.copy()
    off_diagonal[:, [0, 1, 2], [0, 1, 2]] = 0.0
    assert not off_diagonal.any()
    assert model.covariance_ric(ObjectRef(90300, "debris", "leo"), epoch, at).source == "default:leo"
    assert model.covariance_ric(ObjectRef(90301, "payload", "meo"), epoch, at).source == "default:meo"
    assert model.covariance_ric(ObjectRef(1, "payload", "leo"), epoch, at).source == "pooled:payload/leo"
    assert model.covariance_ric(ObjectRef(1, "payload", "mars"), epoch, at).source == "default:other"

    # Persistence: the table rebuilds the same model.
    back = EmpiricalCovariance.from_frame(model.to_frame())
    for obj in (ref, ObjectRef(90201, "payload", "leo"), ObjectRef(90300, "debris", "leo"), ObjectRef(2, "x", "geo")):
        g1, s1 = model.growth_for(obj)
        g2, s2 = back.growth_for(obj)
        assert s1 == s2 and g1 == g2
    sig = sigma_table(model, [ref, ObjectRef(90300, "debris", "leo")])
    assert list(sig.columns[:2]) == ["norad_id", "source"] and "sigma_i_7d_km" in sig.columns
    assert sig["source"].tolist() == ["empirical", "default:leo"]


def test_a_pool_with_enough_fitted_members_is_their_median_fit():
    """Five or more fitted members: the pool is the component-wise median of their power laws, so one member
    with enormous residuals (a manoeuvring satellite the detector missed) cannot dominate it."""
    rng = np.random.default_rng(5)
    base = base_orbit()
    epochs = epochs_every(12.0, 24.0)
    ids = list(range(90401, 90407))
    records = []
    for k, norad_id in enumerate(ids):
        noise = 1e-6 * (0.5, 0.8, 1.0, 1.5, 2.0, 40.0)[k]  # the last one is wild
        records.extend(history_records(norad_id, lambda t: base, epochs, rng, sigma_n_rel=noise, name=f"M {k}"))
    records.extend(history_records(90500, lambda t: base, epochs[:3], rng, sigma_n_rel=1e-6, name="THIN"))
    hist = history_frame(records)
    objects = pd.DataFrame({"norad_id": [*ids, 90500], "category": ["payload"] * 7, "altitude_band": ["leo"] * 7})
    fit = fit_covariance(hist, objects, now=T0 + timedelta(days=60))
    table = fit.table
    members = table[(table["kind"] == "object") & (table["source"] == "empirical")]
    assert len(members) == 6
    pool = table[table["kind"] == "pool"].iloc[0]
    assert pool["n_fitted"] == 6 and pool["source"] == "pooled:payload/leo"
    expected = median_growth(PowerLawGrowth.from_row(r) for _, r in members.iterrows())
    assert PowerLawGrowth.from_row(pool) == expected
    assert pool["sigma_i_1d_km"] < 0.25 * members["sigma_i_1d_km"].max()  # the wild member did not win
    thin = table[(table["kind"] == "object") & (table["norad_id"] == 90500)].iloc[0]
    assert thin["source"] == "pooled:payload/leo"
    assert fit.model.growth_for(ObjectRef(90500, "payload", "leo"))[0] == expected


def test_models_satisfy_the_protocol_and_scaling_wraps_a_base_model():
    model = EmpiricalCovariance()
    assert isinstance(model, CovarianceModel)
    assert model.version == "empirical-powerlaw/1"
    scaled = ScaledCovariance(model, 4.0)
    assert isinstance(scaled, CovarianceModel) and scaled.version == "empirical-powerlaw/1*scaled/4"
    ref = ObjectRef(1, "payload", "leo")
    epoch = datetime(2026, 9, 1, tzinfo=UTC)
    at = np.array(["2026-09-03T00:00:00"], dtype="datetime64[us]")
    base = model.covariance_ric(ref, epoch, at)
    out = scaled.covariance_ric(ref, epoch, at)
    np.testing.assert_allclose(out.cov_km2, 4.0 * base.cov_km2)
    assert out.source == "scaled:4:default:leo" and base.source == "default:leo"
    np.testing.assert_allclose(base.cov_km2[0, 1, 1], DEFAULT_GROWTH["leo"].sigma_km(np.array([2.0]))[0, 1] ** 2)
    with pytest.raises(ValueError):
        ScaledCovariance(model, 0.0)
    assert PowerLawGrowth.from_row(DEFAULT_GROWTH["leo"].as_dict()) == DEFAULT_GROWTH["leo"]


# --------------------------------------------------------------------------------------
# The supplemental layer: objects screened on an operator ephemeris get their own uncertainty


def supplemental_history_frame(records: list[dict], fetched_at: datetime, rms_km: float = 0.2) -> pd.DataFrame:
    """The stored-version shape: element columns plus the published RMS and the fetch time."""
    df = history_frame(records)[list(sup_mod.SUPPLEMENTAL_ELEMENT_COLUMNS)].copy()
    df["rms_km"] = rms_km
    df["fetched_at"] = pd.Timestamp(fetched_at)
    return df


def test_supplemental_covariance_is_fitted_from_successive_versions_not_from_gp_history():
    """Two stored versions per object, published hours apart, give the growth of the operator's plan."""
    rng = np.random.default_rng(11)
    # A drag-free truth, so the only difference between the two versions is the designed revision:
    # with drag on, a set refitted at a later epoch also carries SGP4's own re-initialisation drift.
    base = base_orbit(bstar=0.0)
    ids = list(range(90601, 90901))
    v1_epochs = {i: T0 + timedelta(hours=float(rng.uniform(0, 12))) for i in ids}
    gaps = {i: float(rng.uniform(0.2, 3.0)) for i in ids}  # days between the two published epochs
    sigma_per_day = 0.4  # km of in-track drift per day of separation, by construction
    v1, v2 = [], []
    for i in ids:
        v1.extend(history_records(i, lambda t: base, [v1_epochs[i]], rng, bstar=0.0, name=f"SUP {i}"))
        later = v1_epochs[i] + timedelta(days=gaps[i])
        # Version two is the same trajectory at the later epoch, displaced in-track by an amount
        # proportional to the gap: a revision of the plan that grows with how long ago it was published.
        shift = sigma_per_day * gaps[i] * rng.normal()
        record = history_records(i, lambda t: base, [later], rng, bstar=0.0, name=f"SUP {i}")[0]
        record["MEAN_ANOMALY"] = (record["MEAN_ANOMALY"] + np.degrees(shift / semi_major_axis_km())) % 360.0
        v2.append(record)
    history = pd.concat(
        [supplemental_history_frame(v1, T0), supplemental_history_frame(v2, T0 + timedelta(hours=8))],
        ignore_index=True,
    )

    fit = fit_supplemental_covariance(EmpiricalCovariance(), history, ids)
    assert fit.summary["n_versions"] == 2
    assert fit.summary["n_objects_with_pairs"] == len(ids)
    assert fit.summary["n_pairs"] == len(ids)
    assert fit.summary["exponent_fitted"] is True  # the gaps span more than a factor of three
    assert fit.summary["by_source"] == {"supplemental:consistency": len(ids)}
    growth = fit.summary["growth"]
    assert abs(growth["p_i"] - 1.0) <= 0.35  # a drift proportional to the gap
    assert 0.5 * sigma_per_day < growth["sigma_i_1d_km"] < 2.0 * sigma_per_day

    model = fit.model
    ref = ObjectRef(ids[0], "starlink", "leo")
    epoch = T0 + timedelta(days=1)
    at = np.array([np.datetime64((epoch + timedelta(days=3)).replace(tzinfo=None), "us")])
    cov = model.covariance_ric(ref, epoch, at)
    assert cov.source == "supplemental:consistency"
    sigma_i = float(np.sqrt(cov.cov_km2[0, 1, 1]))
    assert 0.6 < sigma_i < 3.0  # about three days of drift, not the GP history's tens of kilometres
    other = model.covariance_ric(ObjectRef(4242, "debris", "leo"), epoch, at)
    assert other.source == "default:leo"  # anything outside the supplemental set falls through
    assert isinstance(model, CovarianceModel)


def test_supplemental_covariance_without_a_second_version_is_the_published_rms():
    """One stored version cannot show any growth, so the floor stands alone and says so."""
    rng = np.random.default_rng(12)
    base = base_orbit(bstar=0.0)
    ids = [90701, 90702]
    records = []
    for i in ids:
        records.extend(history_records(i, lambda t: base, [T0], rng, bstar=0.0, name=f"SUP {i}"))
    history = supplemental_history_frame(records, T0, rms_km=0.25)
    fit = fit_supplemental_covariance(EmpiricalCovariance(), history, ids)
    assert fit.summary["n_pairs"] == 0 and fit.summary["growth"] is None
    assert fit.summary["by_source"] == {"supplemental:rms": 2}
    at = np.array([np.datetime64((T0 + timedelta(days=5)).replace(tzinfo=None), "us")])
    cov = fit.model.covariance_ric(ObjectRef(ids[0], "starlink", "leo"), T0, at)
    assert cov.source == "supplemental:rms"
    sigma = np.sqrt(np.diag(cov.cov_km2[0]))
    np.testing.assert_allclose(sigma, 0.25 / np.sqrt(3.0), rtol=1e-9)  # isotropic, flat, the RMS alone


def test_the_supplemental_fit_keeps_pairs_that_span_a_burn():
    """A supplemental set already contains the planned burn, so a jump between versions is the error."""
    rng = np.random.default_rng(13)
    base = base_orbit()
    epochs = epochs_every(12.0, 10.0)
    t_burn = T0 + timedelta(days=5)
    after = raised_copy(base, t_burn, 1.0)
    frame = history_frame(
        history_records(BASE_ID, lambda t: base if t < t_burn else after, epochs, rng, sigma_n_rel=1e-7)
    )
    with_exclusion = analyse_object(frame)
    without = analyse_object(frame, exclude_jumps=False)
    assert with_exclusion.jumps.n_jumps == 1
    assert without.n_pairs > with_exclusion.n_pairs
    assert without.growth is not None and with_exclusion.growth is not None
    assert without.growth.sigma_1d_km[1] > with_exclusion.growth.sigma_1d_km[1]


def test_the_supplemental_table_round_trips_through_the_covariance_file():
    rng = np.random.default_rng(14)
    base = base_orbit(bstar=0.0)
    ids = [90801, 90802]
    records = []
    for k, i in enumerate(ids):
        for hours in (0.0, 18.0):
            records.extend(
                history_records(i, lambda t: base, [T0 + timedelta(hours=hours)], rng, bstar=0.0, name=f"S{k}")
            )
    history = supplemental_history_frame(records, T0, rms_km=0.3)
    fit = fit_supplemental_covariance(EmpiricalCovariance(), history, ids)
    table = fit.model.to_frame()
    assert set(table.loc[table["kind"] == "supplemental", "norad_id"]) == set(ids)
    rebuilt = SupplementalCovariance.from_frame(EmpiricalCovariance(), table)
    at = np.array([np.datetime64((T0 + timedelta(days=2)).replace(tzinfo=None), "us")])
    for i in ids:
        ref = ObjectRef(i, "starlink", "leo")
        before = fit.model.covariance_ric(ref, T0, at)
        after = rebuilt.covariance_ric(ref, T0, at)
        np.testing.assert_allclose(after.cov_km2, before.cov_km2, rtol=1e-9)
        assert after.source == before.source


def test_label_cov_sources_uses_the_model_that_will_serve_each_object():
    objects = pd.DataFrame(
        {"norad_id": [90901, 90902], "category": ["starlink", "debris"], "altitude_band": ["leo", "leo"]}
    )
    history = supplemental_history_frame(
        history_records(90901, lambda t: base_orbit(bstar=0.0), [T0], np.random.default_rng(0), bstar=0.0),
        T0,
        rms_km=0.1,
    )
    model = fit_supplemental_covariance(EmpiricalCovariance(), history, [90901]).model
    labelled = label_cov_sources(objects, model)
    assert labelled["cov_source"].tolist() == ["supplemental:rms", "default:leo"]
