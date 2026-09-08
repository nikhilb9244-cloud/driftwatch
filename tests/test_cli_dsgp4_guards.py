"""ML entry-point guards must run before residual values or orbit data are read."""

from types import SimpleNamespace

import pandas as pd
import pytest

from driftwatch import cli
from driftwatch.radio.track_benchmark import IDENTITY_COLUMNS
from driftwatch.storm import reference


def prepare(tmp_path):
    (tmp_path / "reference_benchmark.parquet").touch()
    (tmp_path / "reference_benchmark.json").touch()
    return SimpleNamespace(out=str(tmp_path))


def test_unknown_window_stops_before_full_parquet_read(tmp_path, monkeypatch):
    calls = []

    def read(path, *, columns):
        calls.append(columns)
        return pd.DataFrame({"window": ["september"]})

    monkeypatch.setattr(pd, "read_parquet", read)
    assert cli.cmd_validate_dsgp4(prepare(tmp_path)) == 2
    assert calls == [["window"]]


def test_mislabeled_epoch_stops_before_any_residual_column(tmp_path, monkeypatch):
    calls = []

    def read(path, *, columns):
        calls.append(columns)
        if columns == ["window"]:
            return pd.DataFrame({"window": ["quiet"]})
        assert columns == list(IDENTITY_COLUMNS)
        return pd.DataFrame(
            [
                {
                    "mission": "swarm-a",
                    "norad_id": reference.MISSIONS["swarm-a"].norad_id,
                    "window": "quiet",
                    "set_epoch": "2024-09-01T00:00:00Z",
                    "lead_h": 6.0,
                    "t": "2024-09-01T06:00:00Z",
                }
            ]
        )

    monkeypatch.setattr(pd, "read_parquet", read)
    with pytest.raises(ValueError, match="outside"):
        cli.cmd_validate_dsgp4(prepare(tmp_path))
    assert calls == [["window"], list(IDENTITY_COLUMNS)]
