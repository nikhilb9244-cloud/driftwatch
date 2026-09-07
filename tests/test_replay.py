"""Replay an archived run without a response cache, current fleet or history store."""

from datetime import timedelta

import pandas as pd
import pytest
from synthetic import make_conjunction, omm_record
from test_screening import PRIMARY_EPOCH, PRIMARY_ID, START, fleet_of, primary_satrec, snapshot_from

from driftwatch import cli, config
from driftwatch.catalogue import snapshot
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.risk.covariance import EmpiricalCovariance
from driftwatch.risk.scenario import objects_from_snapshot, run_risk
from driftwatch.screening import ScreeningConfig, screen_fleet, supplemental


@pytest.fixture
def archive(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_DIR", tmp_path / "snapshots")
    monkeypatch.setattr(config, "AS_OF_SNAPSHOT_DIR", tmp_path / "snapshots/as-of")
    monkeypatch.setattr(config, "SUPPLEMENTAL_DIR", tmp_path / "supplemental")
    primary = primary_satrec()
    secondary, _ = make_conjunction(
        primary, START + timedelta(hours=2), miss_km=0.1, crossing_angle_deg=90, miss_direction_deg=30, norad_id=90020
    )
    secondary_epoch = START + timedelta(hours=2)
    snap = snapshot_from({PRIMARY_ID: (primary, "P", PRIMARY_EPOCH), 90020: (secondary, "S", secondary_epoch)})
    # The catalogue alone describes a different orbit. Only the recorded supplemental
    # version restores the conjunction; ignoring it cannot pass this test.
    snap.loc[snap.norad_id == 90020, "mean_anomaly_deg"] += 15
    name = "gp_20260901T120000Z.parquet"
    snapshot.write_snapshot(snap, config.SNAPSHOT_DIR / name)
    path, _ = supplemental.store_supplemental(
        [omm_record(secondary, "S", secondary_epoch)],
        name="starlink",
        fetched_at=START,
        out_dir=config.SUPPLEMENTAL_DIR,
    )
    entry = {"name": "starlink", "file": path.name, "version": supplemental.version_of(path), "n_applied": 1}
    elements, _ = supplemental.apply_supplemental_frame(
        snap, supplemental.read_supplemental(path), name="starlink", version=entry["version"]
    )
    fleet = fleet_of((PRIMARY_ID, "P", True))
    cfg = ScreeningConfig(days=0.15)
    result = screen_fleet(elements, fleet, config=cfg, start=START)
    model = EmpiricalCovariance()
    objects = objects_from_snapshot([PRIMARY_ID, 90020], elements, fleet)
    run = RunDirectory.for_run(fleet.name, START, tmp_path / "archive")
    run.write_events(result.events, snapshot=name)
    run.write_objects(objects)
    run.write_covariance(model.to_frame())
    run.write_risk(
        run_risk(result.events, objects, model, scenario="quiet", run_id="archived", snapshot=name, now=START), "quiet"
    )
    run.write_run(
        {
            "snapshot": name,
            "fleet_name": fleet.name,
            "run_id": "archived",
            "start": START.isoformat(),
            "end": result.end.isoformat(),
            "config": cfg.to_dict(),
            "summary": result.summary(),
            "supplemental": [entry],
        }
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Replay consulted a mutable cache, history, fleet or ephemeris store")

    for module, attr in [
        (supplemental, "fetch_supplemental"),
        (supplemental, "load_supplemental_records"),
        (cli, "fit_from_history"),
        (cli, "supplemental_history"),
        (cli, "load_fleet"),
        (cli.spacex, "load_trajectory"),
    ]:
        monkeypatch.setattr(module, attr, forbidden)
    return run


def test_screen_offline_replays_archive_events_and_flag_tally(archive, tmp_path):
    assert cli.main(["screen", "--offline", "--replay", str(archive.path), "--out-dir", str(tmp_path / "replay")]) == 0
    replay = RunDirectory(tmp_path / "replay" / archive.name)
    assert len(replay.read_events()) == len(archive.read_events()) > 0
    pd.testing.assert_frame_equal(replay.read_events(), archive.read_events())
    columns = ["region", "confidence", "flag"]
    pd.testing.assert_series_equal(
        replay.read_risk("quiet").groupby(columns).size(), archive.read_risk("quiet").groupby(columns).size()
    )
    assert replay.read_risk("quiet").flag.isin(["red", "yellow"]).any()
    assert replay.read_run()["supplemental"] == archive.read_run()["supplemental"]


@pytest.mark.parametrize("problem", ["missing", "count", "served", "overwrite"])
def test_replay_refuses_missing_or_changed_inputs(archive, tmp_path, problem):
    info = archive.read_run()
    out = tmp_path / "replay"
    if problem == "missing":
        (config.SUPPLEMENTAL_DIR / info["supplemental"][0]["file"]).unlink()
    elif problem == "count":
        info["supplemental"][0]["n_applied"] = 2
    elif problem == "served":
        info["summary"]["served_trajectory"] = {"objects": 1}
    else:
        out = archive.path.parent
    archive.write_run(info)
    assert cli.main(["screen", "--offline", "--replay", str(archive.path), "--out-dir", str(out)]) == 2
