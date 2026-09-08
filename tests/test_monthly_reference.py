"""Protocol ordering, frozen rules and isolation of monthly claims from v2."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import monthly_reference as monthly

from driftwatch.storm import benchmark_statistics as statistics

NOW = datetime(2026, 9, 8, 20, tzinfo=UTC)


@pytest.mark.parametrize("commit,dirty", [("changed-commit", ""), (monthly.FROZEN_COMMIT, " M method.py")])
def test_scientific_checkout_drift_is_refused_before_import(tmp_path, monkeypatch, commit, dirty):
    responses = iter([commit, dirty])
    monkeypatch.setattr(monthly.subprocess, "check_output", lambda *a, **k: next(responses))
    with pytest.raises(ValueError, match="clean checkout"):
        monthly.bind_frozen_method(tmp_path)


def initialise(root):
    index = root / "docs/assets/claims-versions.json"
    monthly.write_new(index, {"versions": [{"version": "v2", "evidence_sha256": "frozen"}]})
    return index


def coverage(state="available"):
    return {m: {"state": state if m == "swarm-a" else "incomplete"} for m in monthly.POPULATION}


def test_completed_months_are_utc_half_open_and_cross_years_and_leap_days():
    start, end = next(monthly.completed_months(datetime(2024, 3, 1, tzinfo=UTC)))
    assert (end - start).days == 29
    assert next(monthly.completed_months(datetime(2026, 1, 1, tzinfo=UTC)))[0].isoformat().startswith("2025-12-01")


def test_every_availability_probe_has_a_prior_immutable_protocol(tmp_path):
    initialise(tmp_path)
    seen = []

    def probe(record):
        paths = list((tmp_path / "docs/assets/monthly").rglob("*-protocol.json"))
        assert any(json.loads(p.read_text(encoding="utf-8")) == record for p in paths)
        seen.append(record["month"])
        return coverage("incomplete" if len(seen) == 1 else "available")

    selected = monthly.prepare(tmp_path, tmp_path / "out", NOW, probe)
    record, selection = monthly.load_selection(tmp_path, selected)
    assert seen == ["2026-08", "2026-07"]
    assert selection["population"] == ["swarm-a"]
    assert record["endpoint"]["leads_hours"] == monthly.LEADS
    assert record["method_commit"] == monthly.FROZEN_COMMIT


def test_unknown_availability_is_not_treated_as_evidence_for_an_older_month(tmp_path):
    initialise(tmp_path)
    with pytest.raises(ValueError, match="unknown"):
        monthly.prepare(tmp_path, tmp_path / "out", NOW, lambda _: coverage("unknown"))
    assert len(list((tmp_path / "docs/assets/monthly").rglob("*-protocol.json"))) == 1


def test_missing_population_member_is_a_failure(tmp_path):
    initialise(tmp_path)
    with pytest.raises(ValueError, match="every named mission"):
        monthly.prepare(tmp_path, tmp_path / "out", NOW, lambda _: {})


def test_changed_protocol_prevents_all_residual_access(tmp_path):
    initialise(tmp_path)
    selected = monthly.prepare(tmp_path, tmp_path / "out", NOW, lambda _: coverage())
    path = next((tmp_path / "docs/assets/monthly").rglob("*-protocol.json"))
    path.write_text(path.read_text(encoding="utf-8").replace('"tolerance_km": 25.0', '"tolerance_km": 50.0'))

    def forbidden(*_):
        pytest.fail("Residuals were accessed before protocol verification")

    with pytest.raises(ValueError, match="Protocol changed"):
        monthly.execute(tmp_path, tmp_path / "out", selected, {}, scorer=forbidden)


def test_changed_population_prevents_residual_access(tmp_path):
    initialise(tmp_path)
    selected = monthly.prepare(tmp_path, tmp_path / "out", NOW, lambda _: coverage())
    path = tmp_path / selected["selection"]
    path.write_text(path.read_text(encoding="utf-8") + " ")
    with pytest.raises(ValueError, match="Population record changed"):
        monthly.load_selection(tmp_path, selected)


def test_new_month_uses_v2_statistics_and_appends_without_changing_v2(tmp_path):
    index = initialise(tmp_path)
    baseline = json.loads(index.read_text(encoding="utf-8"))["versions"][0]
    selected = monthly.prepare(tmp_path, tmp_path / "out", NOW, lambda _: coverage())

    def score(record, selection):
        rows = []
        for i in range(20):
            for lead in monthly.LEADS:
                rows.append(
                    {
                        "mission": "swarm-a",
                        "window": "2026-08",
                        "altitude_band": "400-600 km",
                        "set_epoch": pd.Timestamp("2026-08-01") + pd.Timedelta(hours=i),
                        "lead_h": lead,
                        "in_track_km": 24 if lead <= 48 or i < 18 else 30,
                        "radial_km": 1,
                        "cross_km": 2,
                        "sigma_i_km": 10,
                        "sigma_r_km": 1,
                        "sigma_c_km": 1,
                        "gap": False,
                        "manoeuvre": False,
                        "sgp4_error": 0,
                        "altitude_km": 470,
                    }
                )
        trials = pd.DataFrame(rows)
        return SimpleNamespace(
            trials=trials,
            built_at=NOW,
            summary={
                "results": statistics.summarise_trials(trials),
                "windows": {"2026-08": record["window"]},
                "missions": {"swarm-a": {"name": "Swarm A"}},
            },
        ), []

    data = monthly.execute(tmp_path, tmp_path / "out", selected, {"commit": monthly.FROZEN_COMMIT}, scorer=score)
    assert data["results"]["by_band"]["400-600 km"]["2026-08"]["horizon"]["last_lead_h_within"] == 48
    assert json.loads(index.read_text(encoding="utf-8"))["versions"][0] == baseline
    entry = json.loads(index.read_text(encoding="utf-8"))["versions"][-1]
    assert monthly.digest(tmp_path / entry["evidence_object"]) == entry["evidence_sha256"]
    claims = json.loads((tmp_path / entry["claims_manifest"]).read_text(encoding="utf-8"))
    assert (tmp_path / entry["tables"]).read_text(encoding="utf-8") == monthly.render_tables(data, claims)
    assert claims["claims"][0]["denominator"]["168"] == 20
    assert (
        monthly.prepare(tmp_path, tmp_path / "different", NOW, lambda _: pytest.fail("Duplicate run"))["status"]
        == "already_recorded"
    )
    with pytest.raises(ValueError, match="already exists"):
        monthly.append_version(index, entry)


def test_claims_version_index_hashes_and_monthly_rendered_text_are_current():
    root = Path(__file__).resolve().parents[1]
    index = json.loads((root / "docs/assets/claims-versions.json").read_text(encoding="utf-8"))
    assert index["versions"][0]["version"] == "v2"
    for entry in index["versions"]:
        for key in ("evidence_object", "claims_manifest"):
            hash_key = "evidence_sha256" if key == "evidence_object" else "claims_sha256"
            assert monthly.digest(root / entry[key]) == entry[hash_key]
        if entry["version"].startswith("monthly-"):
            data = json.loads((root / entry["evidence_object"]).read_text(encoding="utf-8"))
            claims = json.loads((root / entry["claims_manifest"]).read_text(encoding="utf-8"))
            assert claims == monthly.claims_for(data, entry["evidence_object"], entry["evidence_sha256"])
            assert (root / entry["tables"]).read_text(encoding="utf-8") == monthly.render_tables(data, claims)
            assert monthly.digest(root / entry["tables"]) == entry["tables_sha256"]
            assert monthly.digest(root / entry["protocol"]) == entry["protocol_sha256"]
