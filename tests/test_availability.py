"""G1 acceptance: late products, catalogue membership and manoeuvre records cannot leak into causal replay."""

import json
from datetime import UTC, date, datetime

import pandas as pd
import pytest

from driftwatch import availability as a
from driftwatch import cli, config, local, workbench
from driftwatch.catalogue import celestrak, history, snapshot, spacetrack
from driftwatch.storm import manoeuvre_records as mr
from driftwatch.storm import precise, reference

DECISION = datetime(2024, 5, 9, tzinfo=UTC)


def member(norad, **overrides):
    return {
        "norad_id": norad,
        "effective_at": "2024-05-07T00:00:00Z",
        "present": True,
        "provider_created_at": "2024-05-07T01:00:00Z",
        "published_at": "2024-05-07T02:00:00Z",
        "retrieved_at": "2026-09-08T00:00:00Z",
        "source_identifier": "fixture:membership",
        "source_sha256": "a" * 64,
        **overrides,
    }


def stored_versions(omm_records):
    base = {
        **omm_records[0],
        "EPOCH": "2024-05-08T00:00:00Z",
        "CREATION_DATE": "2024-05-08T01:00:00Z",
        "_driftwatch_published_at": "2024-05-08T02:00:00Z",
        "_driftwatch_retrieved_at": "2026-09-07T12:00:00Z",
    }
    revised = {
        **base,
        "MEAN_ANOMALY": (float(base["MEAN_ANOMALY"]) + 1) % 360,
        "CREATION_DATE": "2024-05-08T03:00:00Z",
        "_driftwatch_published_at": "2024-05-10T00:00:00Z",
        "_driftwatch_retrieved_at": "2026-09-08T12:00:00Z",
    }
    return history.frame_from_records([base, revised], preserve_versions=True)


def test_late_revision_is_filtered_before_version_selection_and_survives_reopening(omm_records, tmp_path):
    versions = stored_versions(omm_records)
    history.write_history(versions, tmp_path / "gph_case.parquet")
    restored = history.load_history(history_dir=tmp_path, include_snapshots=False, preserve_versions=True)
    assert len(restored) == 2
    norad = int(versions.norad_id.iloc[0])
    membership = pd.DataFrame([member(norad)])
    epoch = snapshot.snapshot_as_of(restored, None, as_of=DECISION, membership=membership)
    causal = snapshot.snapshot_as_of(
        restored, None, as_of=DECISION, membership=membership, selection_kind=a.CAUSAL_REPLAY
    )
    assert epoch.mean_anomaly_deg.iloc[0] == versions.mean_anomaly_deg.iloc[1]
    assert causal.mean_anomaly_deg.iloc[0] == versions.mean_anomaly_deg.iloc[0]
    assert epoch.selection_kind.iloc[0] == a.EPOCH_RECONSTRUCTION
    assert causal.selection_kind.iloc[0] == a.CAUSAL_REPLAY
    assert epoch.state_epoch.iloc[0] < pd.Timestamp(DECISION) < epoch.published_at.iloc[0]
    reopened = snapshot.read_snapshot(snapshot.write_snapshot(causal, tmp_path / "gp_causal_case.parquet"))
    for field in ("state_epoch", *a.TIME_FIELDS, "fetched_at", "availability_as_of", "membership_provenance"):
        pd.testing.assert_series_equal(reopened[field], causal[field], check_dtype=False)
    assert json.loads(reopened.membership_provenance.iloc[0])["source_sha256"] == "a" * 64
    assert reopened.retrieved_at.iloc[0] != pd.Timestamp(DECISION)


@pytest.mark.parametrize("late_present", [True, False])
def test_late_catalogue_addition_or_removal_changes_only_epoch_reconstruction(omm_records, late_present):
    sets = stored_versions(omm_records).iloc[:1]
    norad = int(sets.norad_id.iloc[0])
    events = pd.DataFrame(
        [
            member(norad, present=not late_present),
            member(
                norad, effective_at="2024-05-08T00:00:00Z", present=late_present, published_at="2024-05-10T00:00:00Z"
            ),
        ]
    )
    epoch = a.membership_at(events, as_of=DECISION, selection_kind=a.EPOCH_RECONSTRUCTION)
    causal = a.membership_at(events, as_of=DECISION, selection_kind=a.CAUSAL_REPLAY)
    assert bool(len(epoch)) == late_present
    assert bool(len(causal)) != late_present
    if late_present:
        with pytest.raises(ValueError, match="at or before"):
            snapshot.snapshot_as_of(sets, None, as_of=DECISION, membership=events, selection_kind=a.CAUSAL_REPLAY)
    else:
        out = snapshot.snapshot_as_of(sets, None, as_of=DECISION, membership=events, selection_kind=a.CAUSAL_REPLAY)
        assert len(out) == 1 and out.owner.isna().all() and list(out.groups.iloc[0]) == []


def test_causal_catalogue_requires_membership_evidence(omm_records):
    with pytest.raises(ValueError, match="membership history"):
        snapshot.snapshot_as_of(stored_versions(omm_records), None, as_of=DECISION, selection_kind=a.CAUSAL_REPLAY)


@pytest.mark.parametrize(
    "publication,retrieval,expected",
    [
        (None, None, False),
        (None, "2024-05-08T00:00:00Z", True),
        (None, "2026-09-08T00:00:00Z", False),
        ("2024-05-09T00:00:00Z", None, True),
        ("2024-05-10T00:00:00Z", "2024-05-08T00:00:00Z", False),
    ],
)
def test_creation_never_substitutes_for_publication_or_retrieval(publication, retrieval, expected):
    frame = pd.DataFrame(
        [
            {
                "epoch": "2024-05-01T00:00:00Z",
                "provider_created_at": "2024-05-01T01:00:00Z",
                "published_at": publication,
                "retrieved_at": retrieval,
            }
        ]
    )
    assert bool(a.available(frame, DECISION).iloc[0]) is expected


def test_late_manoeuvre_record_is_excluded_causally_and_provenance_reopens(tmp_path):
    frame = pd.DataFrame(
        [
            {
                "start": "2024-05-08T12:00:00Z",
                "end": "2024-05-08T12:02:00Z",
                "provider_created_at": "2024-05-08T13:00:00Z",
                "published_at": "2024-05-10T00:00:00Z",
                "retrieved_at": None,
                "source_identifier": "fixture:manoeuvre",
                "source_sha256": "b" * 64,
            }
        ]
    )
    epoch = local.manoeuvre_table(frame)
    causal = local.manoeuvre_table(frame, as_of=DECISION, selection_kind=a.CAUSAL_REPLAY)
    assert len(epoch) == 1 and len(causal) == 0
    path = tmp_path / "events.json"
    a.write_records(epoch, path, epoch_column="start")
    reopened = a.read_records(path)
    assert a.metadata(reopened, epoch_column="start") == a.metadata(epoch, epoch_column="start")
    assert reopened.retrieved_at.isna().all()
    assert len(local.manoeuvre_table(reopened, as_of=DECISION, selection_kind=a.CAUSAL_REPLAY)) == 0


def test_provider_manoeuvre_snapshot_requires_known_availability_and_keeps_unknowns(tmp_path):
    meta = mr.cache_snapshot("ids-ssalto", b"a source record", mr.IDS_URL, cache_dir=tmp_path)
    assert all(meta[k] is None for k in a.TIME_FIELDS)
    assert "raw_path" not in meta
    record = mr.PublishedManoeuvreRecord(
        "x",
        1,
        [(pd.Timestamp("2024-05-08"), pd.Timestamp("2024-05-08"))],
        [],
        [],
        0,
        0,
        provenance=[{**meta, "published_at": "2024-05-10T00:00:00Z"}],
    )
    with pytest.raises(ValueError, match="unavailable"):
        record.for_causal_replay(DECISION)
    assert record.selection_kind == a.EPOCH_RECONSTRUCTION and len(record.intervals) == 1
    opened = record.for_causal_replay(datetime(2024, 5, 11, tzinfo=UTC))
    assert opened.as_metadata()["selection_kind"] == a.CAUSAL_REPLAY
    assert opened.provenance[0]["retrieved_at"] is None


def test_cached_gp_history_preserves_actual_retrieval_instead_of_import_time(omm_records, tmp_path):
    ids = [int(omm_records[0]["NORAD_CAT_ID"])]
    start, end = date(2024, 5, 1), date(2024, 5, 2)
    query_end = date(2024, 5, 3)
    fetched = datetime(2024, 5, 3, 12, tzinfo=UTC)
    folder = spacetrack.history_cache_dir(tmp_path)
    spacetrack._write_history_cache(folder, ids, start, end, query_end, omm_records[:1], fetched, None)
    records = spacetrack.fetch_gp_history(
        ids, start, end, cache_dir=tmp_path, offline=True, now=datetime(2026, 9, 8, tzinfo=UTC), with_provenance=True
    )
    frame = history.frame_from_records(records)
    assert frame.retrieved_at.iloc[0] == pd.Timestamp(fetched)
    assert frame.fetched_at.iloc[0] == pd.Timestamp(fetched)
    assert frame.published_at.isna().all()


def test_cached_gp_without_retrieval_metadata_preserves_unknown(omm_records, tmp_path):
    ids = [int(omm_records[0]["NORAD_CAT_ID"])]
    folder = spacetrack.history_cache_dir(tmp_path)
    folder.mkdir(parents=True)
    key = spacetrack.history_request_key(ids, date(2024, 5, 1), date(2024, 5, 3))
    (folder / (key + ".json")).write_text(json.dumps(omm_records[:1]), encoding="utf-8")
    records = spacetrack.fetch_gp_history(
        ids, date(2024, 5, 1), date(2024, 5, 2), cache_dir=tmp_path, offline=True, with_provenance=True
    )
    assert history.frame_from_records(records).retrieved_at.isna().all()


def test_fetch_command_keeps_each_cached_group_retrieval_time(omm_records, tmp_path, monkeypatch):
    dates = [datetime(2024, 5, 1, tzinfo=UTC), datetime(2024, 5, 2, tzinfo=UTC)]
    groups = ["first", "second"]
    results = [
        celestrak.GroupFetch(g, tmp_path / (g + ".json"), t, True, 1) for g, t in zip(groups, dates, strict=True)
    ]
    monkeypatch.setattr(celestrak, "fetch_groups", lambda *args, **kwargs: results)
    monkeypatch.setattr(celestrak, "load_group_records", lambda g, *args: [omm_records[groups.index(g)]])
    monkeypatch.setattr(config, "SNAPSHOT_DIR", tmp_path)
    assert cli.main(["fetch", "--groups", "first,second", "--no-satcat", "--spacetrack", "off", "--offline"]) == 0
    frame = snapshot.read_snapshot(snapshot.latest_snapshot(tmp_path)).set_index("norad_id")
    for record, retrieved in zip(omm_records[:2], dates, strict=True):
        row = frame.loc[int(record["NORAD_CAT_ID"])]
        assert row.retrieved_at == pd.Timestamp(retrieved) == row.fetched_at
        assert row.reconstructed_at > row.retrieved_at and pd.isna(row.published_at)


def test_history_command_preserves_cached_retrieval_and_reissued_versions(omm_records, tmp_path, monkeypatch):
    ids = [int(omm_records[0]["NORAD_CAT_ID"])]
    records = [omm_records[0], {**omm_records[0], "MEAN_ANOMALY": 7.0}]
    retrieved = datetime(2024, 5, 3, tzinfo=UTC)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(config, "HISTORY_DIR", tmp_path / "history")
    spacetrack._write_history_cache(
        spacetrack.history_cache_dir(config.CACHE_DIR),
        ids,
        date(2024, 5, 1),
        date(2024, 5, 2),
        date(2024, 5, 3),
        records,
        retrieved,
        None,
    )
    assert cli.main(["history", "--ids", str(ids[0]), "--start", "2024-05-01", "--end", "2024-05-02", "--offline"]) == 0
    frame = history.load_history(history_dir=config.HISTORY_DIR, include_snapshots=False, preserve_versions=True)
    assert len(frame) == 2 and (frame.retrieved_at == pd.Timestamp(retrieved)).all()
    assert frame.published_at.isna().all()


def test_local_prediction_refuses_late_publication_and_preserves_declared_times(omm_records):
    record = {**omm_records[0], "EPOCH": "2024-05-08T00:00:00Z", "CREATION_DATE": "2024-05-08T01:00:00Z"}
    file = ("orbit.json", json.dumps([record]))
    options = {"published_at": "2024-05-10T00:00:00Z", "retrieved_at": None}
    epoch = workbench.trajectory(file, int(record["NORAD_CAT_ID"]), pd.Timestamp("2024-05-09"), options)
    assert epoch.metadata["published_at"] == options["published_at"]
    assert epoch.metadata["retrieved_at"] is None
    with pytest.raises(ValueError, match="unavailable versions"):
        workbench.trajectory(
            file,
            int(record["NORAD_CAT_ID"]),
            pd.Timestamp("2024-05-09"),
            {**options, "selection_kind": a.CAUSAL_REPLAY},
        )


def test_source_summary_review_time_is_not_reported_as_provider_retrieval():
    now = datetime(2026, 9, 8, tzinfo=UTC)
    blocks = precise.sources_record({}, reviewed_at=now)
    blocks += reference.mission_sources_record([reference.MISSIONS["swarm-a"]], now)
    reviewed = [b for b in blocks if "reviewed_at" in b]
    assert reviewed
    assert all(b["reviewed_at"] == now.isoformat() and b["retrieved_at"] is None for b in reviewed)
