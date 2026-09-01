import json
from datetime import UTC, datetime

import numpy as np

from driftwatch.catalogue.snapshot import build_snapshot
from driftwatch.export.viewer import ELEMENTS_PER_OBJECT, REFERENCE_PER_OBJECT, export_viewer_bundle
from driftwatch.orbit.propagator import propagate_snapshot
from driftwatch.orbit.time import unix_microseconds


def test_bundle_roundtrip(omm_records, tmp_path):
    df = build_snapshot({"active": omm_records}, None, fetched_at=datetime.now(UTC))
    at = datetime(2006, 6, 25, 12, tzinfo=UTC)
    state = propagate_snapshot(df, [at])
    manifest = export_viewer_bundle(df, state, out_dir=tmp_path, snapshot_name="gp_test.parquet")

    n = len(df)
    assert manifest["n_objects"] == n
    assert manifest["reference_time"] == "2006-06-25T12:00:00.000000Z"
    assert (tmp_path / "manifest.json").exists()

    elements = np.frombuffer((tmp_path / "elements.bin").read_bytes(), dtype="<f8").reshape(n, ELEMENTS_PER_OBJECT)
    np.testing.assert_array_equal(elements[:, 0], df["norad_id"].to_numpy())
    np.testing.assert_allclose(elements[:, 2], df["mean_motion"].to_numpy())
    epoch0 = df["epoch"].iloc[0].to_pydatetime()
    assert abs(elements[0, 1] - unix_microseconds(epoch0) / 1000.0) < 1e-3

    reference = np.frombuffer((tmp_path / "reference.bin").read_bytes(), dtype="<f4").reshape(n, REFERENCE_PER_OBJECT)
    r, v, error = state.at_index(0)
    ok = error == 0
    np.testing.assert_allclose(reference[ok, :3], r[ok], rtol=1e-6)
    np.testing.assert_allclose(reference[ok, 3:], v[ok], rtol=1e-6)
    assert np.isnan(reference[~ok]).all()

    objects = json.loads((tmp_path / "objects.json").read_text())
    assert len(objects["name"]) == n
    assert objects["category"][0] < len(manifest["categories"])
    assert objects["sgp4_error"] == [int(e) for e in error]
