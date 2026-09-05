"""The Step 4 outputs: collapsed pairs, the cumulative probability, the markdown report and the viewer bundle.

The dilution labelling is tested here as well as in the probability module, because its
purpose is what the report says: a flag in the dilution region must be reported at low
confidence and never presented as actionable.
"""

from __future__ import annotations

import json
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest
from synthetic import make_conjunction
from test_scenario import Isotropic
from test_screening import PRIMARY_EPOCH, PRIMARY_ID, START, fleet_of, primary_satrec, snapshot_from

from driftwatch import config
from driftwatch.catalogue.snapshot import write_snapshot
from driftwatch.cli import main
from driftwatch.export.conjunctions import RunDirectory
from driftwatch.export.report import (
    TRACK_SAMPLES,
    build_bundle,
    collapse_pairs,
    cumulative_pc,
    detail_pairs,
    sample_tracks,
    weekly_report,
    write_bundle,
    write_report,
)
from driftwatch.risk.scenario import objects_from_snapshot, run_risk
from driftwatch.screening import ScreeningConfig, screen_fleet

SECONDARY_ID = 90020


@pytest.fixture(scope="module")
def run(tmp_path_factory) -> tuple[RunDirectory, pd.DataFrame]:
    """A real run directory: one designed conjunction screened, scored and joined."""
    primary = primary_satrec()
    t_star = START + timedelta(hours=2, minutes=7)
    secondary, _ = make_conjunction(
        primary, t_star, miss_km=0.4, crossing_angle_deg=90.0, miss_direction_deg=30.0, norad_id=SECONDARY_ID
    )
    snap = snapshot_from(
        {PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), SECONDARY_ID: (secondary, "SECONDARY", t_star)}
    )
    fleet = fleet_of((PRIMARY_ID, "Primary", True))
    result = screen_fleet(snap, fleet, config=ScreeningConfig(days=0.3), start=START)
    objects = objects_from_snapshot([PRIMARY_ID, SECONDARY_ID], snap, fleet)
    path = tmp_path_factory.mktemp("runs")
    run_dir = RunDirectory.for_run("synthetic", START, path)
    run_dir.write_events(result.events, snapshot="gp_test.parquet")
    run_dir.write_objects(objects)
    run_dir.write_covariance(pd.DataFrame({"kind": [], "norad_id": []}))
    run_dir.write_risk(
        run_risk(result.events, objects, Isotropic(0.05), scenario="quiet", run_id="r-1", snapshot="gp_test.parquet"),
        "quiet",
    )
    run_dir.write_run(
        {
            "run_id": "r-1",
            "snapshot": "gp_test.parquet",
            "fleet_name": "synthetic",
            "start": START.isoformat(),
            "end": (START + timedelta(days=0.3)).isoformat(),
            "covariance": {"model_version": "test/1"},
            "supplemental": [{"name": "starlink", "version": "20260902T000000Z", "file": "x.parquet", "n_applied": 1}],
            "scenarios": ["quiet"],
        }
    )
    run_dir.rebuild_conjunctions()
    return run_dir, snap


# --------------------------------------------------------------------------------------
# Collapsing and the cumulative probability


def test_cumulative_probability_is_the_complement_product():
    assert cumulative_pc(np.array([0.1, 0.2])) == pytest.approx(1 - 0.9 * 0.8)
    assert cumulative_pc(np.array([1e-6] * 10)) == pytest.approx(1e-5, rel=1e-3)
    # It is never smaller than the largest single event, and never above one.
    p = np.array([1e-4, 5e-5, 2e-5])
    assert cumulative_pc(p) >= p.max()
    assert cumulative_pc(np.array([0.9, 0.9, 0.9])) < 1.0
    assert np.isnan(cumulative_pc(np.array([])))
    assert cumulative_pc(np.array([np.nan, 0.25])) == pytest.approx(0.25)


def synthetic_conjunctions() -> pd.DataFrame:
    base = {
        "scenario": "quiet",
        "primary_name": "Primary",
        "secondary_name": "Secondary",
        "secondary_category": "debris",
        "in_box": True,
        "pc_chan": 0.0,
        "manoeuvre_secondary": "none",
        "secondary_ephemeris": "gp",
        "cov_source_secondary": "empirical",
        "hbr_m": 20.0,
        "pc_max": 1e-4,
    }
    rows = [
        {
            **base,
            "primary_norad_id": 1,
            "secondary_norad_id": 2,
            "tca": "2026-09-03T08:00:00Z",
            "miss_km": 5.0,
            "pc": 1e-6,
            "pc_max_scale": 4.0,
            "region": "robust",
            "flag": "none",
            "confidence": "standard",
        },
        {
            **base,
            "primary_norad_id": 1,
            "secondary_norad_id": 2,
            "tca": "2026-09-03T09:34:00Z",
            "miss_km": 0.8,
            "pc": 2e-4,
            "pc_max_scale": 0.7,
            "region": "dilution",
            "flag": "red",
            "confidence": "low",
        },
        {
            **base,
            "primary_norad_id": 1,
            "secondary_norad_id": 2,
            "tca": "2026-09-03T11:08:00Z",
            "miss_km": 3.0,
            "pc": 5e-6,
            "pc_max_scale": 2.0,
            "region": "robust",
            "flag": "none",
            "confidence": "standard",
        },
        {
            **base,
            "primary_norad_id": 1,
            "secondary_norad_id": 3,
            "tca": "2026-09-04T02:00:00Z",
            "miss_km": 1.5,
            "pc": 3e-5,
            "pc_max_scale": 1.4,
            "region": "robust",
            "flag": "yellow",
            "confidence": "standard",
            "secondary_name": "Other",
            "in_box": False,
        },
    ]
    df = pd.DataFrame(rows)
    df["tca"] = pd.to_datetime(df["tca"], utc=True)
    return df


def test_collapse_pairs_keeps_the_count_the_closest_and_the_worst():
    pairs = collapse_pairs(synthetic_conjunctions())
    assert len(pairs) == 2
    first = pairs.iloc[0]  # sorted by the highest probability
    assert first["secondary_norad_id"] == 2
    assert first["n_events"] == 3 and first["n_in_box"] == 3
    assert first["closest_km"] == pytest.approx(0.8)
    assert first["max_pc"] == pytest.approx(2e-4)
    assert first["first_tca"] == pd.Timestamp("2026-09-03T08:00:00Z")
    assert first["pc_cumulative"] == pytest.approx(cumulative_pc(np.array([1e-6, 2e-4, 5e-6])))
    # The pair inherits the flag, region and confidence of the event it is judged on.
    assert (first["flag"], first["region"], first["confidence"]) == ("red", "dilution", "low")
    second = pairs.iloc[1]
    assert second["n_events"] == 1 and second["flag"] == "yellow" and second["confidence"] == "standard"
    assert collapse_pairs(pd.DataFrame()).empty


def test_detail_pairs_keeps_the_flagged_and_the_boxed_whatever_the_limit():
    pairs = collapse_pairs(synthetic_conjunctions())
    kept = detail_pairs(pairs, limit=0)
    assert len(kept) == 2  # one flagged red, one flagged yellow
    quiet = pairs.copy()
    quiet["flag"] = "none"
    quiet["n_in_box"] = 0
    assert len(detail_pairs(quiet, limit=1)) == 1
    assert len(detail_pairs(quiet, limit=99)) == 2


# --------------------------------------------------------------------------------------
# The report


def test_report_separates_the_dilution_flags_and_calls_them_not_actionable(run):
    run_dir, _ = run
    joined = run_dir.read_conjunctions()
    text = weekly_report(run_dir)
    assert "# Conjunction report" in text and "scenario `quiet`" in text
    assert "Flagged, robust region" in text
    assert "not independent" in text  # the cumulative-probability caveat
    assert f"| Events | {len(joined)} |" in text
    # Every flagged pair appears under a heading that matches its confidence.
    pairs = collapse_pairs(joined)
    low = pairs[(pairs["flag"] != "none") & (pairs["confidence"] == "low")]
    if len(low):
        assert "dilution region (low confidence, not actionable)" in text
        assert "must not be acted on" in text
        for name in low["secondary_name"]:
            assert name in text
    path = write_report(run_dir)
    assert path.name == "report.md" and path.read_text(encoding="utf-8") == text


def test_report_marks_a_dilution_red_as_low_confidence_everywhere_it_appears(tmp_path):
    """A red in the dilution region is never presented as a plain red."""
    rows = synthetic_conjunctions()
    pairs = collapse_pairs(rows)
    red = pairs[pairs["flag"] == "red"].iloc[0]
    assert red["confidence"] == "low"
    from driftwatch.export.report import _fmt_flag

    rendered = _fmt_flag(red["flag"], red["confidence"], red["region"])
    assert "low confidence" in rendered and "dilution" in rendered
    # The region and the confidence come first, the colour last (2026-09-05).
    assert rendered.index("dilution") < rendered.index("red")
    assert "not actionable" in rendered
    robust = _fmt_flag("red", "standard", "robust")
    assert robust.startswith("robust region") and robust.endswith("**red**")
    assert _fmt_flag("none", "standard", "robust") == "—"


def test_the_public_bundle_names_a_station_and_anonymises_every_other_primary(run):
    """A small operator's satellite is not named in a public warning until they have agreed."""
    from driftwatch.export.report import anonymise_primaries, public_primary_name

    assert public_primary_name("ISS (Zarya)", "station", 25544) == "ISS (Zarya)"
    assert public_primary_name("EOS SAT-1", "payload", 55053) == "payload 55053"
    assert public_primary_name("Some Body", "rocket_body", 9) == "rocket body 9"
    rows = pd.DataFrame(
        {
            "primary_name": ["ISS (Zarya)", "EOS SAT-1"],
            "primary_category": ["station", "payload"],
            "primary_norad_id": [25544, 55053],
            "secondary_name": ["A", "B"],
        }
    )
    out = anonymise_primaries(rows)
    assert out["primary_name"].tolist() == ["ISS (Zarya)", "payload 55053"]
    assert out["secondary_name"].tolist() == ["A", "B"], "catalogue names are the public record"
    assert rows["primary_name"].iloc[1] == "EOS SAT-1", "the input frame is not touched"

    run_dir, snap = run
    bundle, _ = build_bundle(run_dir, snap)
    for pair in bundle["pairs"]:
        assert pair["primary_name"] != "Primary"
        assert pair["primary_name"].endswith(str(pair["primary_norad_id"]))
    assert any("agreed to appear" in c for c in bundle["caveats"])
    # The run directory's own report keeps the name: it is the operator's report, not the page.
    assert "Primary" in weekly_report(run_dir)


# --------------------------------------------------------------------------------------
# The viewer bundle


def test_bundle_carries_pairs_events_and_tracks_that_match_the_stored_states(run, tmp_path):
    run_dir, snap = run
    bundle, tracks = build_bundle(run_dir, snap)
    assert bundle["bundle_version"] == 1 and bundle["scenario"] == "quiet"
    assert bundle["n_pairs"] == len(bundle["pairs"]) >= 1
    assert bundle["n_events_total"] == len(run_dir.read_conjunctions())
    assert bundle["thresholds"] == {"red": 1e-4, "yellow": 1e-5}
    assert any("not independent" in c for c in bundle["caveats"])
    assert any("dilution" in c for c in bundle["caveats"])
    assert bundle["supplemental"][0]["version"] == "20260902T000000Z"

    # Every pair's event indices resolve, and every event's track index is in range.
    for pair in bundle["pairs"]:
        for k in pair["events"]:
            assert 0 <= k < len(bundle["events"])
    for event in bundle["events"]:
        assert event["region"] in ("robust", "dilution", "unknown")
        assert event["confidence"] in ("low", "standard")
        if event["track"] is not None:
            assert 0 <= event["track"] < bundle["tracks"]["n_events"]

    # The tracks are TEME positions at 20 s spacing, and the middle sample of each is the
    # state Stage C stored for that event: the same elements propagated the same way.
    spec = bundle["tracks"]
    assert spec["frame"] == "teme" and spec["samples"] == TRACK_SAMPLES and spec["step_s"] == 20.0
    assert tracks.positions.shape == (spec["n_events"], 2, TRACK_SAMPLES, 3)
    events = run_dir.read_events().set_index("event_id")
    middle = (TRACK_SAMPLES - 1) // 2
    for k, event_id in enumerate(tracks.event_ids):
        row = events.loc[event_id]
        np.testing.assert_allclose(
            tracks.positions[k, 0, middle], [row["p_x_km"], row["p_y_km"], row["p_z_km"]], rtol=1e-4, atol=1e-3
        )
        np.testing.assert_allclose(
            tracks.positions[k, 1, middle], [row["s_x_km"], row["s_y_km"], row["s_z_km"]], rtol=1e-4, atol=1e-3
        )
    # The two objects are close at the middle sample and further away at the ends.
    if spec["n_events"]:
        sep = np.linalg.norm(tracks.positions[0, 0] - tracks.positions[0, 1], axis=1)
        assert sep[middle] < sep[0] and sep[middle] < sep[-1]

    paths = write_bundle(bundle, tracks, tmp_path)
    assert json.loads(paths["json"].read_text(encoding="utf-8"))["run_id"] == "r-1"
    assert paths["tracks"].stat().st_size == tracks.positions.size * 4


def test_bundle_json_is_finite_and_serialisable(run):
    run_dir, snap = run
    bundle, _ = build_bundle(run_dir, snap)
    text = json.dumps(bundle)  # NaN would serialise as the invalid literal NaN
    assert "NaN" not in text and "Infinity" not in text


def test_the_bundles_storm_summary_counts_the_whole_scenario_not_the_detailed_events(tmp_path, monkeypatch):
    """The base bundle and the lazily fetched overlay must agree, or numbers move on their own.

    `conjunctions.json` carries the events of the pairs a reader can act on -- 2,052 of 5,704 on
    the demo run -- while `scenarios.json` summarises every event of the scenario. When the
    summary in the bundle was computed over the narrowed set, the storm figures changed the
    moment the overlay landed, with no interaction in between. Both are statements about the
    whole scenario and both must count it.
    """
    from driftwatch.export import report as report_mod
    from driftwatch.export.storm import build_overlays

    primary = primary_satrec()
    members = {PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH)}
    for k in range(4):
        t_star = START + timedelta(hours=1, minutes=20 + 17 * k)
        secondary, _ = make_conjunction(
            primary,
            t_star,
            miss_km=0.4 + 0.3 * k,
            crossing_angle_deg=70.0 + 10.0 * k,
            miss_direction_deg=20.0 * k,
            norad_id=91000 + k,
        )
        members[91000 + k] = (secondary, f"SECONDARY-{k}", t_star)
    snap = snapshot_from(members)
    fleet = fleet_of((PRIMARY_ID, "Primary", True))
    result = screen_fleet(snap, fleet, config=ScreeningConfig(days=0.3), start=START)
    objects = objects_from_snapshot(sorted(members), snap, fleet)

    run_dir = RunDirectory.for_run("many", START, tmp_path)
    run_dir.write_events(result.events, snapshot="gp_test.parquet")
    run_dir.write_objects(objects)
    run_dir.write_covariance(pd.DataFrame({"kind": [], "norad_id": []}))
    run_dir.write_risk(
        run_risk(result.events, objects, Isotropic(0.05), scenario="quiet", run_id="r-2", snapshot="gp_test.parquet"),
        "quiet",
    )
    run_dir.write_run(
        {
            "run_id": "r-2",
            "snapshot": "gp_test.parquet",
            "fleet_name": "many",
            "start": START.isoformat(),
            "end": (START + timedelta(days=0.3)).isoformat(),
            "covariance": {"model_version": "test/1"},
            "scenarios": ["quiet"],
        }
    )
    run_dir.rebuild_conjunctions()

    # One detailed pair out of several, which is the situation the demo run is always in --
    # forced directly, because `detail_pairs` keeps every pair with an event inside the
    # notification box whatever the limit says, and all four of these are inside it.
    monkeypatch.setattr(report_mod, "detail_pairs", lambda pairs, limit=None: pairs.head(1))
    bundle, _ = build_bundle(run_dir, snap, scenario="quiet")
    assert bundle["n_pairs"] > bundle["n_pairs_detailed"], "the fixture must actually narrow"
    assert len(bundle["events"]) < bundle["n_events_total"]

    combined = bundle["storm"]["summary"]["combined"]["n_events"]
    assert combined == bundle["n_events_total"]
    overlays = build_overlays(run_dir, bundle)
    assert combined == overlays["scenarios"]["quiet"]["summary"]["combined"]["n_events"]
    assert len(bundle["storm"]["unscoreable"]) == len(overlays["scenarios"]["quiet"]["unscoreable"])


def test_the_overlay_columns_are_parallel_to_the_bundle_it_was_built_from(run):
    """The browser indexes into these by position; a length mismatch would misattribute rows."""
    from driftwatch.export.storm import build_overlays

    run_dir, snap = run
    bundle, _ = build_bundle(run_dir, snap, scenario="quiet")
    overlays = build_overlays(run_dir, bundle)
    assert overlays["n_events"] == len(bundle["events"])
    assert overlays["n_pairs"] == len(bundle["pairs"])
    events = overlays["scenarios"]["quiet"]["events"]
    assert len(events["pc"]) == len(bundle["events"])
    assert len(events["region"]["i"]) == len(bundle["events"])
    assert len(overlays["scenarios"]["quiet"]["pairs"]["max_pc"]) == len(bundle["pairs"])
    # And under a scenario with no storm layer the overlay agrees with the bundle event by event.
    for k, record in enumerate(bundle["events"]):
        assert events["pc"][k] == pytest.approx(record["pc"], rel=1e-6, abs=1e-30)


def test_sample_tracks_refuses_an_object_it_has_no_elements_for(run):
    run_dir, snap = run
    events = run_dir.read_events().head(1)
    with pytest.raises(KeyError, match="no element set"):
        sample_tracks(events, snap[snap["norad_id"] == PRIMARY_ID])


def test_the_report_command_rebuilds_a_stored_run_from_what_it_recorded(run, tmp_path, monkeypatch):
    """`driftwatch report` reconstructs the run's element sets from its snapshot and the stored
    supplemental versions, not from whatever the cache holds now: that is what makes a run reproducible."""
    run_dir, snap = run
    snapshot_dir = tmp_path / "snapshots"
    viewer_dir = tmp_path / "viewer"
    snapshot_dir.mkdir()
    write_snapshot(snap, snapshot_dir / "gp_20260901T120000Z.parquet")
    monkeypatch.setattr(config, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(config, "VIEWER_DATA_DIR", viewer_dir)
    monkeypatch.setattr(config, "SUPPLEMENTAL_DIR", tmp_path / "supplemental")
    monkeypatch.setattr(config, "CONJUNCTION_DIR", run_dir.path.parent)
    info = run_dir.read_run()
    info["snapshot"] = "gp_20260901T120000Z.parquet"
    info["supplemental"] = []
    run_dir.write_run(info)

    assert main(["report", str(run_dir.path)]) == 0
    assert (run_dir.path / "report.md").exists()
    bundle = json.loads((viewer_dir / "conjunctions.json").read_text(encoding="utf-8"))
    assert bundle["run_id"] == "r-1" and bundle["n_events_total"] == len(run_dir.read_conjunctions())
    assert (viewer_dir / "conjunction-tracks.bin").stat().st_size > 0
    # "latest" resolves under the configured output directory, and an unknown scenario is refused.
    assert main(["report", "latest"]) == 0
    assert main(["report", str(run_dir.path), "--scenario", "storm"]) == 2


def test_the_default_scenario_is_quiet_wherever_it_was_scored():
    """A storm scenario is chosen explicitly (2026-09-05); a reader never meets a storm number first."""
    from driftwatch.export.report import default_scenario

    assert default_scenario(["forecast", "quiet", "storm-g4", "storm-g5"]) == "quiet"
    assert default_scenario([]) == "quiet"
    assert default_scenario(["storm-g5", "replay:2024-05-09"]) == "replay:2024-05-09"
