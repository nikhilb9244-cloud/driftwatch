"""Scenario scoring over stored events.

The closed form holds through the whole chain (Stage C geometry, RIC covariance rotated
into TEME, the encounter plane, Foster); a rescoring with another model changes the
probabilities and nothing else; the run directory round-trips and the joined export has
one row per event per scenario; hard-body radii and manoeuvre levels per object; the
``screen`` and ``risk`` commands end to end.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.stats import ncx2
from synthetic import make_conjunction
from test_screening import PRIMARY_EPOCH, PRIMARY_ID, START, fleet_of, primary_satrec, snapshot_from

from driftwatch import config
from driftwatch.catalogue import history
from driftwatch.catalogue.snapshot import write_snapshot
from driftwatch.cli import main
from driftwatch.export.conjunctions import EXPORT_COLUMNS, RunDirectory, join_conjunctions, scenario_file_name
from driftwatch.risk.covariance import EmpiricalCovariance, RicCovariance, fit_covariance
from driftwatch.risk.scenario import (
    OBJECT_COLUMNS,
    RISK_COLUMNS,
    apply_history,
    hard_body_radius_m,
    new_run_id,
    objects_from_snapshot,
    refresh_hard_body_radii,
    run_risk,
)
from driftwatch.screening import ScreeningConfig, screen_fleet


class Isotropic:
    """A covariance model for tests: the same isotropic sigma for every object at every time, and a call log."""

    version = "isotropic-test/1"

    def __init__(self, sigma_km: float) -> None:
        self.sigma_km = sigma_km
        self.calls: list[tuple[int, datetime, np.ndarray]] = []

    def covariance_ric(self, obj, epoch, at):
        at = np.asarray(at, dtype="datetime64[us]")
        self.calls.append((obj.norad_id, epoch, at))
        cov = np.zeros((len(at), 3, 3))
        cov[:, [0, 1, 2], [0, 1, 2]] = self.sigma_km**2
        return RicCovariance(cov, "test")


@pytest.fixture(scope="module")
def designed():
    """One designed conjunction screened by Stages A to C: the snapshot, the fleet, the events, the objects."""
    primary = primary_satrec()
    t_star = START + timedelta(hours=2, minutes=7)
    secondary, design = make_conjunction(
        primary, t_star, miss_km=0.4, crossing_angle_deg=90.0, miss_direction_deg=30.0, norad_id=90020
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90020: (secondary, "SECONDARY", t_star)})
    fleet = fleet_of((PRIMARY_ID, "Primary", True))
    result = screen_fleet(snap, fleet, config=ScreeningConfig(days=0.2), start=START)
    events = result.events
    assert len(events) >= 1
    objects = objects_from_snapshot([PRIMARY_ID, 90020], snap, fleet)
    return snap, fleet, events, objects, design, t_star


def closest(events: pd.DataFrame) -> int:
    return int(events["miss_km"].idxmin())


def test_run_risk_reproduces_the_closed_form_through_the_whole_chain(designed):
    snap, fleet, events, objects, design, t_star = designed
    model = Isotropic(0.2)
    risk = run_risk(events, objects, model, scenario="quiet", run_id="run-1", snapshot="gp_test.parquet")
    assert list(risk.columns) == list(RISK_COLUMNS)
    assert len(risk) == len(events) and risk["event_id"].tolist() == events["event_id"].tolist()
    k = closest(events)
    row = risk.iloc[k]
    d = float(events.loc[k, "miss_km"])
    assert abs(d - design["miss_km"]) < 1e-3
    radius = row["hbr_m"] / 1000.0
    assert row["hbr_m"] == pytest.approx(10.0 + 1.0)  # the fleet's 10 m plus the 1 m default for an unknown object
    var = 2.0 * 0.2**2  # both objects isotropic: the combined covariance is isotropic too
    expected = ncx2.cdf(radius**2 / var, df=2, nc=d**2 / var)
    assert row["pc"] == pytest.approx(expected, rel=1e-4)
    assert row["pc_alfano"] == pytest.approx(expected, rel=1e-4)
    assert row["pc_chan"] == pytest.approx(expected, rel=1e-4)
    assert row["pc_max"] >= row["pc"] and 0.1 <= row["pc_max_scale"] <= 10.0
    assert row["flag"] == ("red" if expected >= 1e-4 else "yellow" if expected >= 1e-5 else "none")
    assert (risk["cov_source_primary"] == "test").all() and (risk["cov_source_secondary"] == "test").all()
    for col in ("sigma_r_primary_km", "sigma_i_secondary_km", "sigma_c_primary_km"):
        np.testing.assert_allclose(risk[col], 0.2)
    assert row["enc_cov_xx_km2"] == pytest.approx(var) and row["enc_cov_xy_km2"] == pytest.approx(0.0, abs=1e-12)
    assert risk["run_id"].iloc[0] == "run-1" and risk["snapshot"].iloc[0] == "gp_test.parquet"
    assert risk["model_version"].iloc[0].endswith("+isotropic-test/1") and risk["scenario"].iloc[0] == "quiet"

    # The model was asked once per object, at the times of closest approach, with that object's own epoch.
    assert sorted(c[0] for c in model.calls) == [PRIMARY_ID, 90020]
    by_id = objects.set_index("norad_id")
    tca = pd.to_datetime(events["tca"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    for norad_id, epoch, at in model.calls:
        assert pd.Timestamp(epoch) == by_id.loc[norad_id, "epoch"]
        np.testing.assert_array_equal(np.sort(at), np.sort(tca))


def test_rescoring_changes_the_probabilities_and_not_the_geometry(designed):
    snap, fleet, events, objects, design, t_star = designed
    before = events.copy(deep=True)
    quiet = run_risk(events, objects, Isotropic(0.2), scenario="quiet", run_id="r", snapshot="s", sweep=False)
    storm = run_risk(events, objects, Isotropic(0.6), scenario="storm", run_id="r", snapshot="s", sweep=False)
    pd.testing.assert_frame_equal(events, before)
    assert quiet["event_id"].tolist() == storm["event_id"].tolist()
    assert not np.allclose(quiet["pc"], storm["pc"])
    assert storm["pc_max"].isna().all() and storm["scenario"].iloc[0] == "storm"
    assert run_risk(events.iloc[0:0], objects, Isotropic(0.2), scenario="x", run_id="r", snapshot="s").empty


def test_run_directory_round_trip_and_the_joined_export(designed, tmp_path):
    snap, fleet, events, objects, design, t_star = designed
    run_dir = RunDirectory.for_run("synthetic", START, tmp_path)
    assert run_dir.name == "synthetic_20260901T120000Z"
    run_dir.write_events(events, snapshot="gp_test.parquet", metadata={"driftwatch_run_id": "r"})
    labels = objects[["norad_id", "category", "altitude_band"]]
    fit = fit_covariance(history.load_history(history_dir=tmp_path / "none", snapshot_dir=tmp_path / "none"), labels)
    objects = apply_history(objects, fit)
    objects.at[objects.index[objects["norad_id"] == 90020][0], "jump_epochs"] = [pd.Timestamp(t_star)]
    objects.loc[objects["norad_id"] == 90020, "last_jump"] = pd.Timestamp(t_star)
    run_dir.write_objects(objects)
    run_dir.write_covariance(fit.table)
    run_dir.write_risk(run_risk(events, objects, fit.model, scenario="quiet", run_id="r", snapshot="s"), "quiet")
    run_dir.write_risk(
        run_risk(events, objects, Isotropic(0.5), scenario="replay:may2024", run_id="r", snapshot="s"),
        "replay:may2024",
    )
    assert scenario_file_name("replay:may2024") == "risk_replay-may2024.parquet"
    assert run_dir.scenarios() == ["quiet", "replay:may2024"]

    back_events = run_dir.read_events()
    pd.testing.assert_frame_equal(back_events, events, check_dtype=False)
    back_objects = run_dir.read_objects()
    assert list(back_objects.columns) == list(OBJECT_COLUMNS)
    sec = back_objects.set_index("norad_id").loc[90020]
    assert list(sec["jump_epochs"]) == [pd.Timestamp(t_star)] and sec["last_jump"] == pd.Timestamp(t_star)
    assert sec["cov_source"] == "default:leo" and sec["manoeuvre_level"] == "none"
    pri = back_objects.set_index("norad_id").loc[PRIMARY_ID]
    assert (
        pri["is_primary"]
        and pri["hbr_m"] == 10.0
        and pri["hbr_source"] == "fleet"
        and pri["manoeuvre_level"] == "known"
    )
    rebuilt = EmpiricalCovariance.from_frame(run_dir.read_covariance())
    assert rebuilt.growth_for(objects_ref(objects, 90020))[1] == "default:leo"

    joined = run_dir.rebuild_conjunctions()
    assert list(joined.columns) == list(EXPORT_COLUMNS)
    assert len(joined) == 2 * len(events)
    assert not joined.duplicated(["event_id", "scenario"]).any()
    assert set(joined["scenario"]) == {"quiet", "replay:may2024"}
    assert (joined["manoeuvre_primary"] == "known").all() and (joined["manoeuvre_secondary"] == "none").all()
    assert (joined["run_id"] == "r").all() and joined["pc"].notna().all()
    again = run_dir.read_conjunctions()
    assert len(again) == len(joined) and str(again["tca"].dtype).endswith("UTC]")
    # With no risk file at all the geometry still exports, with the risk columns empty.
    geometry_only = join_conjunctions(events, objects, [])
    assert list(geometry_only.columns) == list(EXPORT_COLUMNS) and geometry_only["pc"].isna().all()


def objects_ref(objects: pd.DataFrame, norad_id: int):
    from driftwatch.risk.covariance import ObjectRef

    row = objects.set_index("norad_id").loc[norad_id]
    return ObjectRef(norad_id, str(row["category"]), str(row["altitude_band"]))


def test_hard_body_radius_rules():
    """The largest of the rules wins, because each of them is a lower bound on an unpublished size."""
    assert hard_body_radius_m("debris", 0.5, 13.0) == (13.0, "fleet")  # the fleet file wins outright
    # A known envelope is not overruled by a population median.
    assert hard_body_radius_m("starlink", 2.0) == (10.0, "category")
    assert hard_body_radius_m("station", None) == (30.0, "category")
    # A small fragment: the radar echo says 0.4 m, ESA's catalogue convention says 1 m.
    assert hard_body_radius_m("debris", 0.5) == (1.0, "span")
    assert hard_body_radius_m("debris", float("nan")) == (1.0, "span")
    # A large payload: the median span of that class beats both the category default and the echo.
    assert hard_body_radius_m("payload", 12.0) == (4.55, "span")
    assert hard_body_radius_m("payload", 0.39) == (3.0, "category")
    # A cross-section large enough to beat the lookup is still used, and still clipped.
    assert hard_body_radius_m("payload", 5000.0) == (20.0, "rcs")
    r, source = hard_body_radius_m("debris", 5.0)
    assert source == "rcs" and r == pytest.approx(np.sqrt(5.0 / np.pi))
    assert hard_body_radius_m("rocket_body", 1e-6) == (5.0, "category")
    assert hard_body_radius_m("unknown", None) == (1.0, "category")
    assert hard_body_radius_m("never-heard-of-it", None) == (1.0, "category")


def test_hard_body_radii_are_rebaselined_over_a_stored_run(designed):
    """A stored run rescores with the radius rules the code holds now, not the ones it ran under."""
    _, _, _, objects, _, _ = designed
    stale = objects.copy()
    stale["hbr_m"] = 0.1
    stale["hbr_source"] = "rcs"
    stale.loc[stale["is_primary"], "hbr_m"] = 7.0
    stale.loc[stale["is_primary"], "hbr_source"] = "fleet"
    refreshed, summary = refresh_hard_body_radii(stale)
    assert summary["n_changed"] == int((~stale["is_primary"]).sum())
    # The fleet's own numbers are left alone; everything else comes back from the rules.
    assert (refreshed.loc[refreshed["is_primary"], "hbr_m"] == 7.0).all()
    assert (refreshed.loc[~refreshed["is_primary"], "hbr_m"] >= 0.5).all()
    assert (refreshed.loc[~refreshed["is_primary"], "hbr_source"] != "rcs").any()


def test_objects_table_priors_and_promotion(designed):
    snap, fleet, events, objects, design, t_star = designed
    snap = snap.copy()
    snap.loc[snap["norad_id"] == 90020, "category"] = "payload"
    snap.loc[snap["norad_id"] == 90020, "groups"] = pd.Series([["active"]] * len(snap), index=snap.index)
    objects = objects_from_snapshot([PRIMARY_ID, 90020], snap, fleet)
    by_id = objects.set_index("norad_id")
    assert by_id.loc[90020, "manoeuvre_prior"] == "possible" and by_id.loc[90020, "in_active_group"]
    assert by_id.loc[PRIMARY_ID, "manoeuvre_prior"] == "known" and by_id.loc[PRIMARY_ID, "name"] == "Primary"
    labels = objects[["norad_id", "category", "altitude_band"]]
    fit = fit_covariance(history.load_history(history_dir=snap_dir_none(), snapshot_dir=snap_dir_none()), labels)
    fit.jumps[90020].jump_epochs = [t_star]
    fit.jumps[90020].jump_delta_a_km = [0.7]
    promoted = apply_history(objects, fit).set_index("norad_id")
    assert promoted.loc[90020, "manoeuvre_level"] == "observed" and promoted.loc[90020, "n_jumps"] == 1
    assert promoted.loc[90020, "last_jump"] == pd.Timestamp(t_star)
    assert promoted.loc[PRIMARY_ID, "manoeuvre_level"] == "known"
    assert new_run_id(datetime(2026, 9, 1, tzinfo=UTC)).startswith("20260901T000000Z-")


def snap_dir_none():
    return config.PROJECT_ROOT / "does-not-exist"


def test_screen_and_risk_commands_end_to_end(designed, tmp_path, monkeypatch):
    snap, fleet, events, objects, design, t_star = designed
    data = tmp_path / "data"
    for name in ("cache", "history", "snapshots"):
        (data / name).mkdir(parents=True)
    out_dir = tmp_path / "out"
    monkeypatch.setattr(config, "CACHE_DIR", data / "cache")
    monkeypatch.setattr(config, "HISTORY_DIR", data / "history")
    monkeypatch.setattr(config, "SNAPSHOT_DIR", data / "snapshots")
    monkeypatch.setattr(config, "CONJUNCTION_DIR", out_dir)
    # Without this the run would write its bundle into the repository's own viewer data.
    monkeypatch.setattr(config, "VIEWER_DATA_DIR", data / "viewer")
    monkeypatch.delenv(config.SPACETRACK_USER_ENV, raising=False)
    monkeypatch.delenv(config.SPACETRACK_PASS_ENV, raising=False)
    snap_path = write_snapshot(snap, data / "snapshots" / "gp_20260901T120000Z.parquet")
    fleet_path = tmp_path / "fleet.yaml"
    fleet_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "cli",
                "members": [
                    {
                        "norad_id": PRIMARY_ID,
                        "name": "Primary",
                        "hard_body_radius_m": 10,
                        "radius_source": "A round number for a synthetic test object.",
                        "manoeuvres": False,
                    }
                ],
            }
        )
    )
    rc = main(
        [
            "screen",
            "--fleet",
            str(fleet_path),
            "--snapshot",
            str(snap_path),
            "--days",
            "0.2",
            "--start",
            "2026-09-01T12:00:00Z",
            "--no-supplemental",
            "--history",
            "off",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    run_path = out_dir / "cli_20260901T120000Z"
    for name in (
        "run.json",
        "events.parquet",
        "objects.parquet",
        "covariance.parquet",
        "risk_quiet.parquet",
        "report.md",
    ):
        assert (run_path / name).exists(), name
    assert (data / "viewer" / "conjunctions.json").exists()
    run_dir = RunDirectory(run_path)
    info = run_dir.read_run()
    assert info["snapshot"] == snap_path.name and info["scenarios"] == ["quiet"] and info["history"]["mode"] == "off"
    assert info["covariance"]["by_source"] == {"default": 2} and info["risk_runs"][0]["scenario"] == "quiet"
    joined = run_dir.read_conjunctions()
    assert (joined["scenario"] == "quiet").all() and joined["pc"].notna().all()
    assert abs(joined["miss_km"].min() - design["miss_km"]) < 1e-3
    assert (joined["cov_source_secondary"] == "default:leo").all() and (joined["manoeuvre_primary"] == "none").all()
    assert set(joined["model_version"]) == {f"{info['covariance']['model_version']}"}

    # A second scenario over the stored events: no rescreening, a new risk file, the join grows.
    events_mtime = (run_path / "events.parquet").stat().st_mtime_ns
    rc = main(["risk", str(run_path), "--scenario", "scaled9", "--scale", "9", "--history", "off"])
    assert rc == 0
    assert (run_path / "events.parquet").stat().st_mtime_ns == events_mtime
    assert (run_path / "risk_scaled9.parquet").exists()
    info = json.loads((run_path / "run.json").read_text(encoding="utf-8"))
    assert info["scenarios"] == ["quiet", "scaled9"] and [r["scenario"] for r in info["risk_runs"]] == [
        "quiet",
        "scaled9",
    ]
    joined = run_dir.read_conjunctions()
    assert set(joined["scenario"]) == {"quiet", "scaled9"} and len(joined) == 2 * len(run_dir.read_events())
    scaled = joined[joined["scenario"] == "scaled9"].set_index("event_id")
    quiet = joined[joined["scenario"] == "quiet"].set_index("event_id")
    assert (scaled["cov_source_secondary"] == "scaled:9:default:leo").all()
    np.testing.assert_allclose(scaled["sigma_i_primary_km"], 3.0 * quiet.loc[scaled.index, "sigma_i_primary_km"])
    assert not np.allclose(scaled["pc"], quiet.loc[scaled.index, "pc"])
    # "latest" resolves under the configured output directory; an empty one is an error, not a guess.
    assert main(["risk", "latest", "--scenario", "again", "--history", "off"]) == 0
    assert (run_path / "risk_again.parquet").exists() and run_dir.scenarios() == ["again", "quiet", "scaled9"]
    (tmp_path / "empty").mkdir()
    monkeypatch.setattr(config, "CONJUNCTION_DIR", tmp_path / "empty")
    assert main(["risk", "latest", "--scenario", "again", "--history", "off"]) == 2

    # A fleet member the snapshot does not hold is a refusal, not a silent skip.
    fleet_path.write_text(fleet_path.read_text().replace(str(PRIMARY_ID), "424242"))
    assert main(["screen", "--fleet", str(fleet_path), "--snapshot", str(snap_path), "--no-supplemental"]) == 1
