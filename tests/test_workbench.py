"""Decision-relevant local workflows and their data/security boundaries."""

from __future__ import annotations

import copy
import http.client
import json
import threading

import numpy as np
import pandas as pd
import pytest

# Built here, not read out of web/public/examples/. The shipped examples became measured data
# on 2026-09-07; these stay constructed because a displacement the test chooses is the only way to
# assert that the engine measures the displacement it was given. See tests/workspace_fixtures.py.
from workspace_fixtures import RECORD, request  # noqa: E402

from driftwatch import local, workbench


def test_same_ephemeris_and_known_displacement_are_distinguished():
    body = request("orbit")
    result = workbench.analyse("compare", body)
    s = result["summary"]
    assert s["median_km"] > 2 and s["p95_km"] > 3
    assert s["candidate_median_km"] == pytest.approx(0.4 * s["median_km"], rel=1e-6)
    assert s["candidate_fraction_better"] == 1
    assert result["reference_kind"] == "prediction"
    assert len(result["sources"][0]["sha256"]) == 64
    body["prediction"] = body["reference"]
    same = workbench.analyse("compare", body)
    assert same["summary"]["max_km"] < 1e-9
    assert same["summary"]["within_tolerance_fraction"] == 1


@pytest.mark.parametrize(
    "replacement,match",
    [
        (("TIME_SYSTEM = UTC", "COMMENT missing time"), "TIME_SYSTEM"),
        (("REF_FRAME = TEME", "REF_FRAME = UNSUPPORTED"), "unsupported"),
        (("CENTER_NAME = EARTH", "CENTER_NAME = MARS"), "EARTH"),
        (("OBJECT_ID = 2024-001A", "OBJECT_ID = 2024-002B"), "different OBJECT_ID"),
    ],
)
def test_ambiguous_or_mismatched_products_are_refused(replacement, match):
    body = request("orbit")
    body["prediction"]["text"] = body["prediction"]["text"].replace(*replacement)
    with pytest.raises(ValueError, match=match):
        workbench.analyse("compare", body)


def test_future_omm_is_not_selected_and_manoeuvres_are_counted():
    body = request("orbit")
    record = dict(RECORD)
    record["EPOCH"] = "2025-01-01T00:00:00"
    body["prediction"] = {"name": "future.json", "text": json.dumps([record])}
    with pytest.raises(ValueError, match="Later state epochs"):
        workbench.analyse("compare", body)
    body = request("orbit")
    body["manoeuvres"] = {"name": "burns.csv", "text": "start,end\n2024-05-10T00:00:00Z,2024-05-10T01:00:00Z\n"}
    result = workbench.analyse("compare", body)
    assert result["summary"]["n_manoeuvre"] == 60
    assert all(p["time"] > "2024-05-10T01:00:00Z" for p in result["samples"])


def test_oem_metadata_seam_is_not_interpolated_across():
    text = request("orbit")["reference"]["text"]
    segment = local.parse_oem(text)[0]
    a, b = copy.deepcopy(segment), copy.deepcopy(segment)
    a.states = a.states.iloc[:5].copy()
    b.states = b.states.iloc[6:10].copy()
    # A two-minute seam is shorter than the old inferred gap limit.
    orbit = local.oem_to_precise_orbit([a, b], norad_id=90001)
    at = np.array(["2024-05-10T00:05:00"], dtype="datetime64[us]")
    assert not orbit.states_teme(at)[2][0]


def test_receiver_lock_is_reconciled_without_calling_it_orbit_error():
    result = workbench.analyse("contacts", request("contacts"))
    assert len(result["passes"]) >= 2
    assert [p["lock_delay_s"] for p in result["passes"][:2]] == pytest.approx([35, 35], abs=0.001)
    assert not result["unmatched_lock_times"]
    assert all(p["peak_elevation_deg"] >= 10 for p in result["passes"])
    assert any(p["alternative_aos_delta_s"] is not None for p in result["passes"])
    assert any("not a measurement" in t for t in result["limitations"])
    assert all(pd.Timestamp(p["los"]) > pd.Timestamp(p["aos"]) for p in result["passes"])


def test_a_tiny_oem_window_does_not_claim_full_pass_coverage():
    body = request("contacts")
    body["start"] = "2024-05-15T00:00:00Z"
    body["prediction"] = request("orbit")["reference"]
    body.pop("candidate")
    body.pop("log")
    result = workbench.analyse("contacts", body)
    assert result["passes"] == []


def test_messages_are_matched_on_pair_and_time_and_bad_covariance_is_visible():
    body = request("cdms")
    result = workbench.analyse("cdms", body)
    assert result["same_case"] and result["tca_delta_s"] == 30
    body["second"]["text"] = body["second"]["text"].replace("CT_T = 10000", "CT_T = -10000")
    result = workbench.analyse("cdms", body)
    assert any("invalid covariance" in c["covariance"] for c in result["checks"])
    body["tolerance_s"] = 5
    assert not workbench.analyse("cdms", body)["same_case"]


def test_model_evaluation_requires_paired_trials_and_forecast_issue_times():
    body = {
        "trials": {
            "name": "trials.csv",
            "text": "trial_id,satellite,window,lead_h,baseline_km,candidate_km\n"
            "a,X,holdout,24,-4,2\nb,X,holdout,24,8,-4\n",
        },
        "reference_kind": "reconstructed",
        "forcing": "observed",
    }
    result = workbench.analyse("model", body)
    row = result["summary"]["windows"]["holdout"]["by_lead_h"]["24"]
    assert row["in_track"]["median_km"] == 6
    assert row["storm_term"]["improvement"] == 0.5
    assert row["in_track"]["inside_2_sigma"] is None
    body["forcing"] = "forecast"
    with pytest.raises(ValueError, match="issued_at"):
        workbench.analyse("model", body)
    body["forcing"] = "observed"
    body["trials"]["text"] += "a,X,training,24,4,2\n"
    with pytest.raises(ValueError, match="more than once"):
        workbench.analyse("model", body)


def test_http_boundary_serves_only_public_build_and_rejects_foreign_origins(tmp_path):
    (tmp_path / "index.html").write_text("<html>Workspace</html>")
    (tmp_path / "data.json").write_text('{"sample": true}')
    server = workbench.make_server(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port

    def send(method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, data

    try:
        status, data = send("GET", "/api/health")
        assert status == 200
        token = json.loads(data)["token"]
        status, data = send("GET", "/data.json")
        assert status == 200 and json.loads(data)["sample"]
        assert send("GET", "/../pyproject.toml")[0] == 404
        assert send("GET", "/api/health", headers={"Host": "evil.example"})[0] == 403
        headers = {"Origin": "https://evil.example", "Content-Type": "application/json", "X-Driftwatch-Token": token}
        assert send("POST", "/api/cdms", json.dumps(request("cdms")), headers)[0] == 403
        headers["Origin"] = f"http://127.0.0.1:{port}"
        status, data = send("POST", "/api/cdms", json.dumps(request("cdms")), headers)
        assert status == 200 and json.loads(data)["same_case"]
        headers.pop("X-Driftwatch-Token")
        assert send("POST", "/api/cdms", "{}", headers)[0] == 403
        assert sorted(p.name for p in tmp_path.iterdir()) == ["data.json", "index.html"]
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
