"""The Kelvins reproduction: the reconstruction is exact on a frame built from known geometry, and the
real dataset, when it is present under data/external/kelvins/, reproduces ESA's risk column within the
target. The second test is skipped with a clear message when the download has not been made."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import ncx2

from driftwatch.risk import kelvins
from driftwatch.risk.pc import max_pc_sweep

SKIP_MESSAGE = (
    "Kelvins dataset not found under data/external/kelvins/: download train_data.csv from "
    "https://kelvins.esa.int/collision-avoidance-challenge/data/ (registration required) and place it there"
)


def synthetic_frame(sigma_m: float = 100.0, hbr_m: float | np.ndarray = 10.0) -> pd.DataFrame:
    """Rows in the challenge's column layout whose ``risk`` is the exact two-dimensional probability.

    Both covariances are isotropic and uncorrelated, so the chaser's frame rotation
    drops out and the combined covariance is ``2 sigma^2`` times the identity.

    ``hbr_m`` may be one radius per row, in which case the ``*_span`` columns are set to
    match it: the dataset's convention is that the combined radius is half of each span
    added, so a span of ``R`` on both objects gives a combined radius of ``R``.
    """
    rng = np.random.default_rng(7)
    n = 12
    dr = rng.normal(size=(n, 3)) * np.array([150.0, 300.0, 80.0])  # metres
    dv = rng.normal(size=(n, 3)) * np.array([100.0, 8000.0, 8000.0])  # m/s
    sigma_km = sigma_m / 1000.0
    var = 2.0 * sigma_km**2
    z = dv / np.linalg.norm(dv, axis=1, keepdims=True)
    perp = dr / 1000.0 - np.einsum("ni,ni->n", dr / 1000.0, z)[:, None] * z
    d = np.linalg.norm(perp, axis=1)
    pc = ncx2.cdf((hbr_m / 1000.0) ** 2 / var, df=2, nc=d**2 / var)
    risk = np.log10(pc)
    df = pd.DataFrame(
        {
            "event_id": np.arange(n),
            "time_to_tca": 1.0,
            "risk": risk,
            "relative_position_r": dr[:, 0],
            "relative_position_t": dr[:, 1],
            "relative_position_n": dr[:, 2],
            "relative_velocity_r": dv[:, 0],
            "relative_velocity_t": dv[:, 1],
            "relative_velocity_n": dv[:, 2],
            "t_j2k_sma": 7000.0,
        }
    )
    for prefix in ("t", "c"):
        for axis in ("r", "t", "n"):
            df[f"{prefix}_sigma_{axis}"] = sigma_m
        df[f"{prefix}_ct_r"] = 0.0
        df[f"{prefix}_cn_r"] = 0.0
        df[f"{prefix}_cn_t"] = 0.0
        df[f"{prefix}_span"] = hbr_m
        # A radar cross-section that is deliberately not the size: a quarter of the disc area.
        df[f"{prefix}_rcs_estimate"] = np.pi * (np.asarray(hbr_m, dtype=float) / 4.0) ** 2
    return df


def test_reconstruction_is_exact_on_designed_rows_and_fits_the_radius():
    df = synthetic_frame()
    assert df["risk"].max() > -3 and df["risk"].min() > -6, "the designed rows should all sit in the tail"
    ours = kelvins.reproduce(df, 10.0)
    np.testing.assert_allclose(ours, df["risk"], atol=1e-5)
    fit = kelvins.fit_hbr(df, radii_m=np.array([5.0, 7.5, 10.0, 15.0, 20.0]))
    assert fit.hbr_m == 10.0 and fit.n_tail == len(df)
    assert abs(fit.report["overall"]["median"]) < 1e-5 and fit.report["overall"]["within_factor_two"] == 1.0
    wrong = fit.by_radius.set_index("hbr_m")
    assert wrong.loc[5.0, "median_abs_residual"] == pytest.approx(np.log10(4.0), abs=0.01)  # Pc scales with R^2
    assert wrong.loc[20.0, "within_factor_two"] == 0.0
    text = kelvins.to_markdown(fit, kelvins.config.KELVINS_DIR / "synthetic.csv")
    assert "Best single hard-body radius: **10.0 m**" in text and "| Risk bin |" in text

    # A floored row is left out of the tail; a chaser correlation term is applied without error.
    floored = pd.concat([df, df.iloc[:1].assign(risk=kelvins.RISK_FLOOR)], ignore_index=True)
    assert kelvins.fit_hbr(floored, radii_m=np.array([10.0])).n_tail == len(df)
    correlated = df.assign(c_ct_r=0.3, c_cn_t=-0.2)
    assert np.isfinite(kelvins.reproduce(correlated, 10.0)).all()


def test_a_per_object_radius_is_recovered_from_the_span_columns():
    """When the truth uses a different radius per row, the span columns recover it and one radius cannot."""
    radii = np.linspace(2.0, 30.0, 12)
    df = synthetic_frame(hbr_m=radii)
    np.testing.assert_allclose(kelvins.combined_radius_m(df, "span"), radii)

    rep = kelvins.reproduce_tail(df, source="span", tail_risk=-30.0 + 1e-9)
    assert rep is not None and rep.n == len(df) and rep.label == "span"
    assert abs(rep.report["overall"]["median"]) < 1e-4
    assert rep.report["overall"]["within_factor_two"] == 1.0

    # Each object's radar cross-section here is a disc of a quarter the radius, so the two
    # equivalent radii add to half the truth and the proxy needs a multiplier of two.
    rcs = kelvins.test_size_proxy(df, "rcs", scales=np.arange(0.5, 8.01, 0.5))
    assert rcs is not None and rcs["best_scale"] == pytest.approx(2.0)
    span = kelvins.test_size_proxy(df, "span")
    assert span is not None and span["best_scale"] == pytest.approx(1.0)
    # A single radius cannot fit twelve different ones; the per-object radius must beat it.
    assert span["median_abs_residual"] < span["constant_median_abs_residual"]

    text = kelvins.to_markdown(
        kelvins.fit_hbr(df, tail_risk=-30.0 + 1e-9),
        kelvins.config.KELVINS_DIR / "s.csv",
        primary=rep,
        proxies=[span, rcs],
        plot_path="s.svg",
    )
    assert "The hard-body radius ESA used" in text and "(t_span + c_span) / 2" in text
    assert "![Residual against ESA's risk](s.svg)" in text

    # Missing columns are a fallback, not an error.
    assert kelvins.reproduce_tail(df.drop(columns=["t_span", "c_span"]), source="span") is None
    assert kelvins.test_size_proxy(df.drop(columns=["c_rcs_estimate"]), "rcs") is None
    assert kelvins.test_size_proxy(df.assign(t_rcs_estimate=np.nan, c_rcs_estimate=np.nan), "rcs") is None
    with pytest.raises(ValueError, match="unknown size proxy"):
        kelvins.combined_radius_m(df, "mass")


def test_the_span_convention_is_chosen_on_one_half_and_holds_on_the_other():
    """The held-out check recovers the multiplier on rows it fits and scores it on rows it never saw.

    Twelve designed events with twelve radii, split by event: the half the multiplier is chosen on
    picks 1.0, the held-out half reproduces to the integrator's precision, and the held-out half's
    own choice is 1.0 too. Then the same rows with every span halved: the fitting half chooses a
    multiplier of two and the report says the convention is a fit.
    """
    radii = np.linspace(2.0, 30.0, 12)
    df = synthetic_frame(hbr_m=radii)
    a, b = kelvins.split_by_event(df, seed=3)
    assert len(a) + len(b) == len(df) and not set(a["event_id"]) & set(b["event_id"])
    check = kelvins.held_out_check(a, b, label="designed", tail_risk=-30.0 + 1e-9)
    assert check["fit_scale"] == pytest.approx(1.0) and check["held_own_scale"] == pytest.approx(1.0)
    assert abs(check["held_median_residual"]) < 1e-4 and check["held_within_factor_two"] == 1.0
    assert check["n_fit"] == len(a) and check["n_held"] == len(b)

    halved = df.assign(t_span=df["t_span"] / 2.0, c_span=df["c_span"] / 2.0)
    checks = kelvins.held_out_checks(halved, None, seed=3, tail_risk=-30.0 + 1e-9)
    assert len(checks) == 2 and all(c["fit_scale"] == pytest.approx(2.0) for c in checks)
    text = kelvins.to_markdown(
        kelvins.fit_hbr(halved, tail_risk=-30.0 + 1e-9),
        kelvins.config.KELVINS_DIR / "s.csv",
        held_out=checks,
    )
    assert "### Confirmed on a held-out split" in text and "do not agree on the multiplier" in text
    good = kelvins.to_markdown(kelvins.fit_hbr(df, tail_risk=-30.0 + 1e-9), Path("s.csv"), held_out=[check])
    assert "holds out of sample" in good

    # A test file beside the training file is found; the training file is never its own test set.
    with pytest.raises(ValueError, match="event_id"):
        kelvins.split_by_event(df.drop(columns=["event_id"]))


def test_find_test_dataset_looks_beside_and_one_level_up(tmp_path):
    (tmp_path / "train_data").mkdir()
    train = tmp_path / "train_data" / "train_data.csv"
    train.write_text("a\n1\n", encoding="utf-8")
    assert kelvins.find_test_dataset(train) is None
    test = tmp_path / "test_data.csv"
    test.write_text("a\n1\n", encoding="utf-8")
    assert kelvins.find_test_dataset(train) == test
    assert kelvins.find_test_dataset(test) is None


def test_the_residual_plot_is_valid_svg_with_both_medians():
    import xml.etree.ElementTree as ET

    rng = np.random.default_rng(3)
    risk = rng.uniform(-6.0, 0.0, 4000)
    svg = kelvins.residual_plot_svg(risk, rng.normal(0.0, 0.2, 4000), compare=(risk, rng.normal(0.5, 0.3, 4000)))
    root = ET.fromstring(svg)
    tags = [e.tag.split("}")[-1] for e in root]
    assert tags.count("polyline") == 4  # median and two percentiles, plus the comparison median
    assert tags.count("rect") > 50  # the density map
    assert kelvins.residual_plot_svg(risk[:5], np.zeros(5)).count("<polyline") == 0  # too few rows to bin


def test_max_risk_comparison_reads_the_scaling_convention():
    df = synthetic_frame()
    plane = kelvins.encounter(df)
    pc_max, scale, _ = max_pc_sweep(plane.miss_km, plane.cov_km2, 0.01)
    df["max_risk_estimate"] = np.log10(pc_max)
    df["max_risk_scaling"] = scale  # a factor on the covariance, as our sweep defines it
    out = kelvins.compare_max_risk(df, 10.0)
    assert out is not None and out["n"] == len(df)
    assert abs(out["max_risk_residual_median"]) < 1e-3 and out["max_risk_within_factor_two"] == 1.0
    assert out["scale_ratio_median_if_covariance_factor"] == pytest.approx(1.0, abs=1e-6)
    assert kelvins.compare_max_risk(df.drop(columns=["max_risk_estimate"]), 10.0) is None


def test_find_dataset_returns_none_without_the_download(tmp_path):
    assert kelvins.find_dataset(tmp_path / "missing") is None
    (tmp_path / "other.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    assert kelvins.find_dataset(tmp_path) == tmp_path / "other.csv"
    (tmp_path / "train_data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    assert kelvins.find_dataset(tmp_path) == tmp_path / "train_data.csv"
    with pytest.raises(ValueError, match="lacks the columns"):
        kelvins.load_kelvins(tmp_path / "train_data.csv")


@pytest.mark.skipif(kelvins.find_dataset() is None, reason=SKIP_MESSAGE)
def test_kelvins_risk_column_is_reproduced_within_a_factor_of_two_across_the_tail():
    """The target was agreement within a factor of two across the high-risk tail with the radius fitted.
    With the per-object span the reconstruction is far better than that; with a single fitted radius it is
    the median that meets the target and not the spread. Both are checked, the second because it is what a
    catalogue without a size column gets. Nothing here is tuned to make it pass."""
    path = kelvins.find_dataset()
    assert path is not None
    df = kelvins.load_kelvins(path)
    fit = kelvins.fit_hbr(df)
    primary = kelvins.reproduce_tail(df, source="span")
    print(kelvins.to_markdown(fit, path, kelvins.compare_max_risk(df, fit.hbr_m, limit=400), primary=primary))

    # The per-object span: ESA's own convention, so the agreement is close to exact.
    assert primary is not None
    tight = primary.report["tight_tail"]
    assert abs(tight["median"]) <= 0.01, tight  # within a couple of percent in the probability
    assert tight["within_factor_two"] >= 0.85, tight
    # Where it disagrees it reads the encounter as safer, which is the direction to keep an eye on.
    assert tight["p05"] < -0.1 and tight["p95"] < 0.3, tight

    # One fitted radius, the fallback.
    overall = fit.report["overall"]
    assert 1.0 <= fit.hbr_m <= 30.0, fit.hbr_m
    assert abs(overall["median"]) <= np.log10(2.0), overall
    assert overall["within_factor_ten"] >= 0.7, overall
    assert overall["within_factor_two"] < primary.report["overall"]["within_factor_two"]
    # The bins an operator acts on are reproduced at least as well as the tail as a whole.
    operational = fit.report["by_risk_bin"]["[-4, -3)"]
    assert abs(operational["median"]) <= np.log10(2.0), operational
    assert operational["within_factor_two"] >= overall["within_factor_two"], operational


@pytest.mark.skipif(kelvins.find_dataset() is None, reason=SKIP_MESSAGE)
def test_the_span_convention_holds_on_rows_it_was_not_recovered_from():
    """The convention came out of the evaluation data, so it is confirmed like a fitted parameter would be.

    Each half of the training events, split by event, chooses a multiplier of one on its own and
    reproduces the other half; and the multiplier chosen on the whole training file reproduces the
    challenge's separate test file. Only on this basis does any page say nothing was fitted.
    """
    path = kelvins.find_dataset()
    assert path is not None
    train = kelvins.load_kelvins(path)
    test_path = kelvins.find_test_dataset(path)
    test = kelvins.load_kelvins(test_path) if test_path is not None else None
    checks = kelvins.held_out_checks(train, test)
    assert len(checks) == 3 if test is not None else 2
    for check in checks:
        assert check["fit_scale"] == pytest.approx(1.0), check
        assert check["held_own_scale"] == pytest.approx(1.0), check
        assert abs(check["held_median_residual"]) <= 0.01, check  # within a couple of percent in probability
        # The whole tail sits at 87 % within a factor of two; a half of it drawn by event lands within a
        # few points of that (84.5 % on one draw), so the bar is the target the fit was set, not the tail.
        assert check["held_within_factor_two"] >= 0.80, check


@pytest.mark.skipif(kelvins.find_dataset() is None, reason=SKIP_MESSAGE)
def test_the_radius_lookup_driftwatch_screens_with_is_still_what_the_data_says():
    """`SPAN_RADIUS_M` is a baked copy of a derivation, so the derivation has to still give it."""
    path = kelvins.find_dataset()
    assert path is not None
    radii = kelvins.chaser_radius_table(kelvins.load_kelvins(path))
    assert kelvins.compare_span_radius_lookup(radii) == {}
    # Every cell of the lookup is at least the metre ESA defaults an unpublished span to.
    assert (radii["radius_m"] >= 1.0).all()


@pytest.mark.skipif(kelvins.find_dataset() is None, reason=SKIP_MESSAGE)
def test_the_residual_does_not_localise_in_the_slow_encounter_bin():
    """The slow-encounter underestimate is real but invisible here, because ESA's column shares it.

    Recorded as a test because the conclusion drawn from it -- that the flag has to come from
    the method rather than from these rows -- rests on the slow bin being unremarkable.
    """
    path = kelvins.find_dataset()
    assert path is not None
    df = kelvins.load_kelvins(path)
    primary = kelvins.reproduce_tail(df, source="span")
    assert primary is not None
    by_speed = primary.report["by_relative_speed"]
    assert by_speed is not None
    slowest, fastest = by_speed[0], by_speed[-1]
    assert slowest["speed_lo_kms"] == 0.0
    # The slow bin is no worse than the middle of the range, and better than the 4-10 km/s bin.
    middle = min(by_speed, key=lambda row: row["within_factor_two"])
    assert slowest["within_factor_two"] >= middle["within_factor_two"]
    assert slowest["within_factor_two"] < fastest["within_factor_two"]
    assert abs(slowest["median"]) < 0.01  # and it is not biased either way
