"""A run's recorded snapshot has to be a snapshot, and it has to be fresh enough to publish.

Written at the Phase 4 Step 2 review, against a failure that had already happened. ``cmd_screen``
shadowed the variable holding the catalogue snapshot's path with the stored supplemental file's,
so two runs recorded a supplemental element-set file as their snapshot. ``driftwatch report``
could not rebuild them and every exported row carried a false provenance -- and the whole test
suite stayed green, because nothing outside ``elements_for_run`` ever looked the recorded name up.

Step 2's failure model rests on that name twice: the pipeline computes the snapshot's age from it
and refuses to publish past a limit, and the console shows that age. So the check has to fail on
a name that resolves to nothing, on a name that resolves to the wrong *kind* of file, and on a
snapshot that is simply too old.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from synthetic import make_conjunction
from test_scenario import Isotropic
from test_screening import PRIMARY_EPOCH, PRIMARY_ID, START, fleet_of, primary_satrec, snapshot_from

from driftwatch import config
from driftwatch.catalogue import snapshot as snapshot_mod
from driftwatch.cli import check_run
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.risk.scenario import objects_from_snapshot, run_risk
from driftwatch.screening import ScreeningConfig, screen_fleet
from driftwatch.screening.supplemental import SUPPLEMENTAL_COLUMNS, write_supplemental

SECONDARY_ID = 90020


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A snapshot directory, a supplemental directory and one scored run, all under tmp_path."""
    snapshots = tmp_path / "snapshots"
    supplemental = tmp_path / "supplemental"
    snapshots.mkdir()
    supplemental.mkdir()
    monkeypatch.setattr(config, "SNAPSHOT_DIR", snapshots)
    monkeypatch.setattr(config, "AS_OF_SNAPSHOT_DIR", snapshots / "as-of")
    monkeypatch.setattr(config, "SUPPLEMENTAL_DIR", supplemental)
    monkeypatch.setattr(config, "CONJUNCTION_DIR", tmp_path / "conjunctions")

    primary = primary_satrec()
    secondary, _ = make_conjunction(
        primary,
        START + timedelta(hours=2, minutes=7),
        miss_km=0.4,
        crossing_angle_deg=90.0,
        miss_direction_deg=30.0,
        norad_id=SECONDARY_ID,
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "P", PRIMARY_EPOCH), SECONDARY_ID: (secondary, "S", START)})
    name = "gp_" + START.strftime("%Y%m%dT%H%M%SZ") + ".parquet"
    snapshot_mod.write_snapshot(snap, snapshots / name)

    fleet = fleet_of((PRIMARY_ID, "Primary", True))
    result = screen_fleet(snap, fleet, config=ScreeningConfig(days=0.3), start=START)
    objects = objects_from_snapshot([PRIMARY_ID, SECONDARY_ID], snap, fleet)

    run_dir = RunDirectory.for_run("synthetic", START, tmp_path / "conjunctions")
    run_dir.write_events(result.events, snapshot=name)
    run_dir.write_objects(objects)
    run_dir.write_covariance(pd.DataFrame({"kind": [], "norad_id": []}))
    run_dir.write_risk(
        run_risk(result.events, objects, Isotropic(0.05), scenario="quiet", run_id="r-1", snapshot=name),
        "quiet",
    )
    run_dir.write_run(
        {
            "run_id": "r-1",
            "snapshot": name,
            "fleet_name": "synthetic",
            "start": START.isoformat(),
            "end": (START + timedelta(days=0.3)).isoformat(),
            "scenarios": ["quiet"],
        }
    )
    return run_dir, snapshots, supplemental, name


def set_snapshot(run_dir: RunDirectory, name: str) -> None:
    info = json.loads(run_dir.run_json.read_text(encoding="utf-8"))
    info["snapshot"] = name
    run_dir.run_json.write_text(json.dumps(info), encoding="utf-8")


def empty_supplemental() -> pd.DataFrame:
    """An empty frame in the supplemental schema, typed so pyarrow will write it."""
    from driftwatch.screening.supplemental import SUPPLEMENTAL_SCHEMA

    return pd.DataFrame(
        {name: pd.Series(dtype=SUPPLEMENTAL_SCHEMA.field(name).type.to_pandas_dtype()) for name in SUPPLEMENTAL_COLUMNS}
    )


def test_a_sound_run_passes_and_reports_its_snapshots_age(store):
    run_dir, _snapshots, _supplemental, name = store
    result = check_run(run_dir, now=START + timedelta(hours=5))
    assert result.ok, result.problems
    assert result.snapshot is not None and result.snapshot.name == name
    assert result.age_hours == pytest.approx(5.0, abs=0.02)


def test_the_shadowed_variable_bug_is_caught_both_ways(store):
    """The exact failure that shipped: a supplemental file recorded as the run's snapshot.

    Two forms. The name does not resolve at all, which is what happened in production; and the
    name *does* resolve, because somebody put such a file in the snapshot directory. The second
    is the harder case and the reason the check reads the parquet's own metadata rather than
    trusting the path: the two file types share nineteen columns, so a column check alone would
    let it through.
    """
    run_dir, snapshots, supplemental, _name = store
    supplemental_name = "starlink_20260901T120000Z.parquet"
    # The same metadata `store_supplemental` writes, which is what marks the file's kind.
    marker = {"driftwatch_supplemental": "starlink"}
    write_supplemental(empty_supplemental(), supplemental / supplemental_name, metadata=marker)

    set_snapshot(run_dir, supplemental_name)
    unresolved = check_run(run_dir)
    assert not unresolved.ok
    assert any("is in neither" in p for p in unresolved.problems)

    write_supplemental(empty_supplemental(), snapshots / supplemental_name, metadata=marker)
    resolved = check_run(run_dir)
    assert not resolved.ok
    assert any("is a supplemental element-set file" in p for p in resolved.problems)
    assert any("not a catalogue snapshot" in p for p in resolved.problems)


def test_a_stale_snapshot_is_a_problem_only_past_the_limit(store):
    """Step 2's gate: refuse to publish past a set age, and pass under it."""
    run_dir, _snapshots, _supplemental, _name = store
    old = START + timedelta(hours=30)
    assert check_run(run_dir, max_snapshot_age_hours=48, now=old).ok
    expired = check_run(run_dir, max_snapshot_age_hours=24, now=old)
    assert not expired.ok
    assert any("EXPIRED" in p for p in expired.problems)
    assert expired.age_hours == pytest.approx(30.0, abs=0.02)
    # With no limit given the age is reported and nothing fails on it.
    assert check_run(run_dir, now=old).ok


def test_a_missing_snapshot_is_a_problem(store):
    run_dir, _snapshots, _supplemental, _name = store
    set_snapshot(run_dir, "gp_20990101T000000Z.parquet")
    result = check_run(run_dir)
    assert not result.ok
    assert result.fetched_at is None


def test_an_unscored_run_is_a_problem(store):
    run_dir, _snapshots, _supplemental, _name = store
    run_dir.risk_path("quiet").unlink()
    result = check_run(run_dir)
    assert not result.ok
    assert any("nothing has been scored" in p for p in result.problems)


def test_an_unstored_supplemental_version_warns_but_does_not_fail(store):
    """A run that cannot be rebuilt *exactly* is still publishable; it is not a false provenance."""
    run_dir, _snapshots, _supplemental, _name = store
    info = json.loads(run_dir.run_json.read_text(encoding="utf-8"))
    info["supplemental"] = [{"name": "starlink", "version": "20260902T000000Z", "file": "gone.parquet"}]
    run_dir.run_json.write_text(json.dumps(info), encoding="utf-8")
    result = check_run(run_dir)
    assert result.ok
    assert any("no longer stored" in w for w in result.warnings)


def test_snapshot_problem_names_what_is_wrong_with_a_file(tmp_path):
    assert snapshot_mod.snapshot_problem(tmp_path / "nothing.parquet") is not None
    text = tmp_path / "notes.txt"
    text.write_text("not parquet", encoding="utf-8")
    assert "not a parquet file" in (snapshot_mod.snapshot_problem(text) or "")
    broken = tmp_path / "broken.parquet"
    broken.write_bytes(b"PAR1 nonsense")
    assert "cannot be read as parquet" in (snapshot_mod.snapshot_problem(broken) or "")


def test_the_age_comes_from_the_data_so_a_rename_cannot_fake_freshness(store):
    """``snapshot_fetched_at`` reads the column, not the stamp in the file name."""
    run_dir, snapshots, _supplemental, name = store
    truth = snapshot_mod.snapshot_fetched_at(snapshots / name)
    renamed = snapshots / "gp_20990101T000000Z.parquet"
    (snapshots / name).rename(renamed)
    assert snapshot_mod.snapshot_fetched_at(renamed) == truth

    set_snapshot(run_dir, renamed.name)
    result = check_run(run_dir, now=datetime(2099, 1, 1, 12, tzinfo=UTC))
    assert result.fetched_at == truth
    assert result.age_hours is not None and result.age_hours > 100000
