"""Identity across runs, which is the only hard part of the warning-stability index.

An ``event_id`` carries the snapshot stamp and the time of closest approach to the minute, so the
same physical encounter has a different id in every run and a join on it finds nothing. The index
assembles a series on the object pair plus the time of closest approach within a tolerance, and
everything that can go wrong with that is here: a tca that moves, two passes of one pair close
enough together to be confused, two events competing for one series, and a run that simply stops
reporting an encounter it reported yesterday -- which is not an error but the signal the whole
index exists to record.

The frames are built by hand rather than screened. The subject is the matcher, and it needs times
of closest approach placed to the second.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from driftwatch import config
from driftwatch.cli import main
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.stability import COLUMNS, StabilityError, StabilityIndex, format_series, series_id

START = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
PRIMARY = 55053
SECONDARY = 61705
# Half an orbit in low Earth orbit: the gap between successive close passes of one pair, and the
# distance the ten-minute tolerance has to stay clear of.
HALF_ORBIT = timedelta(minutes=46)


def events_frame(rows: list[tuple[int, int, datetime, float]]) -> pd.DataFrame:
    """The columns of ``events.parquet`` the index reads, and nothing else."""
    return pd.DataFrame(
        {
            "event_id": [f"snap:{p}:{s}:{t:%Y%m%dT%H%MZ}" for p, s, t, _ in rows],
            "primary_norad_id": [p for p, _, _, _ in rows],
            "secondary_norad_id": [s for _, s, _, _ in rows],
            "tca": pd.to_datetime([t for _, _, t, _ in rows], utc=True),
            "miss_km": [m for _, _, _, m in rows],
            "primary_trajectory": ["sgp4"] * len(rows),
            "secondary_trajectory": ["spacex-ephemeris"] * len(rows),
        }
    )


def risk_frame(events: pd.DataFrame, *, pc: float = 1e-6, flag: str = "none") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": events["event_id"],
            "pc": pc,
            "pc_max": pc * 2,
            "flag": flag,
            "scoreable": True,
            "unscoreable_reason": None,
            "slow_encounter": False,
            "cov_source_primary": "empirical",
            "cov_source_secondary": "spacex-ephemeris",
            "computed_at": pd.Timestamp(START),
        }
    )


def make_run(
    root,
    run_id: str,
    start: datetime,
    rows: list[tuple[int, int, datetime, float]],
    *,
    fleet: str = "synthetic",
    days: float = 7.0,
    trajectories: bool = True,
    **risk_kwargs,
) -> RunDirectory:
    """A run directory with just enough in it to be indexed."""
    events = events_frame(rows)
    if not trajectories:
        events = events.drop(columns=["primary_trajectory", "secondary_trajectory"])
    run_dir = RunDirectory(root / run_id)
    run_dir.write_events(events, snapshot="gp_test.parquet")
    run_dir.write_risk(risk_frame(events, **risk_kwargs), "quiet")
    run_dir.write_run(
        {
            "run_id": run_id,
            "snapshot": "gp_test.parquet",
            "fleet_name": fleet,
            "start": start.isoformat(),
            "end": (start + timedelta(days=days)).isoformat(),
            "scenarios": ["quiet"],
        }
    )
    return run_dir


@pytest.fixture
def index(tmp_path) -> StabilityIndex:
    return StabilityIndex(tmp_path / "stability")


# --------------------------------------------------------------------------------------
# Identity


def test_a_moving_tca_is_still_one_series(index, tmp_path):
    """The tca moves between runs as both orbits are refitted. That is the same encounter."""
    tca = START + timedelta(days=2)
    first = index.append_run(make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0)]))
    second = index.append_run(
        make_run(tmp_path, "run-2", START + timedelta(days=1), [(PRIMARY, SECONDARY, tca + timedelta(seconds=90), 3.1)])
    )
    assert (first.n_new, first.n_continued) == (1, 0)
    assert (second.n_new, second.n_continued) == (0, 1)

    rows = index.read("synthetic")
    assert rows["series_id"].nunique() == 1
    # The id is anchored to the first sighting and does not follow the tca.
    assert rows["series_id"].iloc[0] == series_id(PRIMARY, SECONDARY, tca)
    assert list(rows["obs_index"]) == [0, 1]
    assert rows["dt_tca_s"].iloc[1] == pytest.approx(90.0)
    assert pd.isna(rows["dt_tca_s"].iloc[0])
    # The lead time is what an analysis reads the series by, and it shortens.
    assert list(rows["lead_s"]) == [2 * 86400, 86400 + 90]


def test_past_the_tolerance_it_is_a_different_encounter(index, tmp_path):
    tca = START + timedelta(days=2)
    index.append_run(make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0)]))
    result = index.append_run(
        make_run(tmp_path, "run-2", START, [(PRIMARY, SECONDARY, tca + timedelta(seconds=601), 4.0)])
    )
    assert (result.n_new, result.n_continued) == (1, 0)
    assert index.read("synthetic")["series_id"].nunique() == 2


def test_repeated_passes_of_one_pair_stay_apart(index, tmp_path):
    """The delicate case: a pair that comes round again half an orbit later, in both runs."""
    tca = START + timedelta(days=2)
    passes = [(PRIMARY, SECONDARY, tca, 4.0), (PRIMARY, SECONDARY, tca + HALF_ORBIT, 9.0)]
    index.append_run(make_run(tmp_path, "run-1", START, passes))
    moved = [(p, s, t + timedelta(seconds=20), m) for p, s, t, m in passes]
    result = index.append_run(make_run(tmp_path, "run-2", START + timedelta(days=1), moved))

    assert (result.n_new, result.n_continued) == (0, 2)
    rows = index.read("synthetic")
    assert rows["series_id"].nunique() == 2
    # Each pass continued its own series, not its neighbour's: every match moved 20 s, not 46 min.
    assert set(rows["dt_tca_s"].dropna().round(0)) == {20.0}
    for _, group in rows.groupby("series_id"):
        assert list(group["obs_index"]) == [0, 1]


def test_two_events_cannot_take_the_same_series(index, tmp_path):
    """Greedy and one to one: the nearer event continues the series, the other starts its own."""
    tca = START + timedelta(days=2)
    index.append_run(make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0)]))
    result = index.append_run(
        make_run(
            tmp_path,
            "run-2",
            START,
            [
                (PRIMARY, SECONDARY, tca + timedelta(seconds=400), 6.0),
                (PRIMARY, SECONDARY, tca + timedelta(seconds=30), 4.2),
            ],
        )
    )
    assert (result.n_new, result.n_continued) == (1, 1)
    rows = index.read("synthetic")
    continued = rows[rows["obs_index"] == 1]
    assert len(continued) == 1
    assert continued["dt_tca_s"].iloc[0] == pytest.approx(30.0)


def test_a_disappearance_is_counted_not_invented(index, tmp_path):
    """An encounter reported yesterday and not today is the signal, so it is counted -- and only counted.

    No row is written for it: the file is what the run saw. The count says a series inside this
    run's window went unreported, which is where an analysis starts looking.
    """
    tca = START + timedelta(days=2)
    index.append_run(make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0), (PRIMARY, 12345, tca, 8.0)]))
    result = index.append_run(make_run(tmp_path, "run-2", START, [(PRIMARY, SECONDARY, tca, 4.0)]))
    assert result.n_not_seen == 1
    assert len(index.read("synthetic", pair=(PRIMARY, 12345))) == 1


def test_reindexing_a_run_does_not_match_it_to_itself(index, tmp_path):
    """Running the step twice is a rerun, not a second observation."""
    tca = START + timedelta(days=2)
    run = make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0)])
    index.append_run(run)
    again = index.append_run(run)
    assert (again.n_new, again.n_continued) == (1, 0)
    assert len(index.files("synthetic")) == 1
    assert len(index.read("synthetic")) == 1


# --------------------------------------------------------------------------------------
# The file


def test_the_file_holds_the_agreed_columns_and_no_event_id(index, tmp_path):
    tca = START + timedelta(days=1)
    result = index.append_run(make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0)], flag="red"))
    rows = index.read("synthetic")
    assert list(rows.columns) == list(COLUMNS)
    # Deliberate: the snapshot, the pair and the tca are what an event id is made of.
    assert "event_id" not in rows.columns
    assert rows["snapshot"].iloc[0] == "gp_test.parquet"
    assert rows["flag"].iloc[0] == "red"
    assert rows["fleet"].iloc[0] == "synthetic"
    assert result.path.endswith("run-1.parquet")


def test_a_run_from_before_the_trajectory_columns_is_still_indexed(index, tmp_path):
    """Phase 4 Step 1 added those columns. Older runs are observations of the same encounters."""
    tca = START + timedelta(days=1)
    index.append_run(make_run(tmp_path, "run-0", START, [(PRIMARY, SECONDARY, tca, 4.0)], trajectories=False))
    rows = index.read("synthetic")
    assert rows["primary_trajectory"].isna().all()
    assert rows["miss_km"].iloc[0] == pytest.approx(4.0)


def test_a_scenario_the_run_did_not_score_is_refused(index, tmp_path):
    run = make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, START + timedelta(days=1), 4.0)])
    with pytest.raises(StabilityError):
        index.append_run(run, scenarios=["storm-g5"])


def test_a_row_stays_narrow(index, tmp_path):
    """The reason it can live on the store branch rather than in the release-asset archive.

    Measured on the 2026-09-03 demo run: 38 bytes a row, 231 KB for 6,224 events. Sixty bytes is
    the budget, and a column added without thinking about the year of files behind it breaks this
    before it breaks the branch.
    """
    tca = START + timedelta(days=1)
    rows = [(PRIMARY, 60000 + i, tca + timedelta(seconds=97 * i), 1.0 + i % 20) for i in range(2000)]
    result = index.append_run(make_run(tmp_path, "run-1", START, rows))
    assert result.n_rows == 2000
    assert result.bytes / result.n_rows < 60.0


# --------------------------------------------------------------------------------------
# The read path


def test_reading_one_pair_gives_its_history_oldest_first(index, tmp_path):
    tca = START + timedelta(days=3)
    index.append_run(make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 16.4)], pc=1e-5, flag="yellow"))
    index.append_run(
        make_run(
            tmp_path,
            "run-2",
            START + timedelta(days=1),
            [(PRIMARY, SECONDARY, tca + timedelta(seconds=4), 23.0)],
            pc=1e-25,
        )
    )
    rows = index.read("synthetic", pair=(PRIMARY, SECONDARY))
    assert list(rows["run_id"]) == ["run-1", "run-2"]
    assert list(rows["flag"]) == ["yellow", "none"]
    # A yellow flag at a three-day lead that is gone at two: the question the index exists for.
    assert rows["lead_s"].is_monotonic_decreasing
    text = format_series(rows)
    assert "run-1" in text and "run-2" in text and "2 runs" in text
    assert index.read("synthetic", series=rows["series_id"].iloc[0]).equals(rows)
    assert index.read("synthetic", pair=(PRIMARY, 99999)).empty


def test_the_summary_counts_the_runs_without_reading_them(index, tmp_path):
    tca = START + timedelta(days=1)
    index.append_run(make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0)]))
    index.append_run(make_run(tmp_path, "run-2", START, [(PRIMARY, SECONDARY, tca, 4.0)]))
    summary = index.summary("synthetic")
    assert summary["n_runs"] == 2
    assert summary["first_run"] == "run-1" and summary["last_run"] == "run-2"
    assert summary["bytes"] > 0
    assert index.summary("other")["n_runs"] == 0


def test_the_command_appends_then_reads_back(tmp_path, capsys, monkeypatch):
    """The two ends of the file, through the CLI the pipeline calls."""
    monkeypatch.setattr(config, "CONJUNCTION_DIR", tmp_path)
    store = tmp_path / "stability"
    tca = START + timedelta(days=2)
    make_run(tmp_path, "run-1", START, [(PRIMARY, SECONDARY, tca, 4.0)], flag="red")
    assert main(["stability", str(tmp_path / "run-1"), "--store", str(store)]) == 0
    capsys.readouterr()

    assert main(["stability", "--pair", f"{PRIMARY},{SECONDARY}", "--fleet", "synthetic", "--store", str(store)]) == 0
    out = capsys.readouterr().out
    assert series_id(PRIMARY, SECONDARY, tca) in out
    assert "red" in out
    # The run records what it contributed, so an archived run says whether it is in the index.
    assert RunDirectory(tmp_path / "run-1").read_run()["stability"]["n_rows"] == 1

    assert main(["stability", "--pair", "1,2", "--fleet", "synthetic", "--store", str(store)]) == 1
