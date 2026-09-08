"""Runner guards and constructed geometries, without loading benchmark orbits."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from astropy.utils import iers

from driftwatch.radio import crossings, site
from driftwatch.radio import track_benchmark as benchmark


class EllipticalBeam:
    margin_deg = np.linspace(-5, 5, 101)
    frequency_mhz = 1234.5

    def power(self, x, y):
        return np.exp(-np.log(2) * ((np.asarray(x) + 0.15) ** 2 / 0.8**2 + np.asarray(y) ** 2 / 1.4**2))

    def record(self):
        return {"frequency_mhz": self.frequency_mhz, "kind": "synthetic test beam"}


def trial():
    return pd.DataFrame(
        [
            {
                "mission": "swarm-a",
                "norad_id": benchmark.reference.MISSIONS["swarm-a"].norad_id,
                "window": "quiet",
                "set_epoch": "2024-04-20T00:00:00Z",
                "lead_h": 6,
                "t": "2024-04-20T06:00:00Z",
            }
        ]
    )


def curve(times, impact=0.0, delay=0.0):
    centre = site.enu_from_alt_az(45, 0)
    right, up = np.array([1, 0, 0]), np.array([0, -np.sqrt(0.5), np.sqrt(0.5)])
    directions = centre + np.tan(np.deg2rad((times - delay) * 0.1))[:, None] * right
    directions += np.tan(np.deg2rad(impact)) * up
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    return crossings.SkyTrack(times, directions, np.tile(centre, (len(times), 1)))


def comparison(p, r, interval=None):
    return crossings.compare_sky_tracks(
        p, r, EllipticalBeam().power, beam_record=EllipticalBeam().record(), observation_interval_s=interval
    )


def test_csv_guard_rejects_unknown_window_before_reading_other_columns(monkeypatch, tmp_path):
    calls = []

    def reader(path, *, usecols):
        calls.append(usecols)
        return pd.DataFrame({"window": ["september"]})

    monkeypatch.setattr(pd, "read_csv", reader)
    with pytest.raises(ValueError, match="four existing"):
        benchmark.load_trial_identities(tmp_path / "unopened.csv")
    assert calls == [["window"]]


def test_progress_write_is_atomic_and_retries_transient_windows_reader(tmp_path, monkeypatch):
    target = tmp_path / "progress.json"
    target.write_text('{"status":"previous"}')
    real_replace, calls = benchmark.os.replace, []

    def replace(source, destination):
        calls.append(1)
        if len(calls) == 1:
            assert json.loads(target.read_text())["status"] == "previous"
            raise OSError(22, "transient Windows reader")
        return real_replace(source, destination)

    monkeypatch.setattr(benchmark.os, "replace", replace)
    monkeypatch.setattr(benchmark.time, "sleep", lambda seconds: None)
    benchmark._write_json(target, {"status": "running"})
    assert json.loads(target.read_text()) == {"status": "running"}
    assert len(calls) == 2 and list(tmp_path.iterdir()) == [target]


def test_mislabeled_september_epoch_and_target_are_rejected_before_history_read(monkeypatch, tmp_path):
    data = trial()
    data["set_epoch"], data["t"] = "2024-09-20T00:00:00Z", "2024-09-20T06:00:00Z"

    def forbidden(*args, **kwargs):
        raise AssertionError("No Parquet file may be opened")

    monkeypatch.setattr(benchmark.pq, "read_table", forbidden)
    with pytest.raises(ValueError, match="outside"):
        benchmark.load_selected_elements(data, tmp_path)
    data = trial()
    data["t"] = "2024-04-21T06:00:00Z"
    with pytest.raises(ValueError, match="target"):
        benchmark.validate_trials(data)


def test_history_loader_uses_disjoint_filters_and_exact_joins(tmp_path, monkeypatch):
    data = pd.concat([trial(), trial()], ignore_index=True)
    data.loc[1, ["window", "set_epoch", "t"]] = ["held-out", "2024-10-06T00:00:00Z", "2024-10-06T06:00:00Z"]
    data = benchmark.validate_trials(data)
    index = data[["norad_id", "set_epoch"]].rename(columns={"set_epoch": "epoch"})
    index["file"] = "selected.parquet"
    index.to_parquet(tmp_path / "index.parquet")
    elements = index.drop(columns="file").assign(mean_motion=15.0)
    extra = elements.iloc[[0]].copy()
    extra["epoch"] = pd.Timestamp("2024-09-10", tz="UTC")
    pd.concat([elements, extra]).to_parquet(tmp_path / "selected.parquet")
    real_read, calls = benchmark.pq.read_table, []

    def read(path, **kwargs):
        calls.append(kwargs)
        return real_read(path, **kwargs)

    monkeypatch.setattr(benchmark.pq, "read_table", read)
    loaded = benchmark.load_selected_elements(data, tmp_path)
    assert len(loaded) == 2 and not (loaded.epoch.dt.month == 9).any()
    assert len(calls) == 2
    assert all(len(call["filters"]) == 2 for call in calls)
    assert all(a[0][2].month == a[1][2].month for call in calls for a in call["filters"])


def test_measured_boundary_is_signed_and_preserves_squint_and_ellipse():
    centre, normal, beam = site.enu_from_alt_az(45, 20), np.array([1.0, 0.0]), EllipticalBeam()
    radii = {sign: benchmark.signed_half_power_radius(centre, normal, beam, sign) for sign in (-1, 1)}
    assert radii[1] != pytest.approx(radii[-1], abs=0.1)
    for sign, radius in radii.items():
        bore = benchmark.displaced_boresight(centre, normal, sign * radius)
        assert beam.power(*site.beam_offsets_deg(centre, bore)) == pytest.approx(0.5, abs=1e-8)
        inner = benchmark.displaced_boresight(centre, normal, sign * radius * 0.95)
        outer = benchmark.displaced_boresight(centre, normal, sign * radius * 1.05)
        assert beam.power(*site.beam_offsets_deg(centre, inner)) > 0.5
        assert beam.power(*site.beam_offsets_deg(centre, outer)) < 0.5


def test_pointing_normal_subtracts_fixed_celestial_boresight_motion():
    seconds = np.arange(-5.0, 6.0)
    times = np.datetime64("2024-04-20T06:00:00", "us") + seconds.astype("timedelta64[s]")
    with iers.conf.set_temp("auto_download", False):
        ra, dec = site.sky_from_alt_az(site.MEERKAT, 45, 20, times[5:6])
        _, _, fixed = site.boresight(site.MEERKAT, float(ra[0]), float(dec[0]), times)
        # A tiny horizontal motion, dominated by Earth rotation in raw ENU.
        predicted = np.array(
            [
                benchmark.displaced_boresight(c, np.array([1.0, 0.0]), t * 0.0001)
                for c, t in zip(fixed, seconds, strict=True)
            ]
        )
        family = benchmark.pointing_family(predicted, times, seconds, EllipticalBeam())
        for pointing in family:
            assert abs(pointing["normal_xy"][0]) < 0.001
            assert pointing["normal_xy"][1] > 0.999
            _, _, rebuilt = site.boresight(site.MEERKAT, pointing["ra_deg"], pointing["dec_deg"], times)
            assert np.allclose(rebuilt, pointing["boresight_enu"], atol=1e-12)
        assert len(family) == 9


def test_observation_clipping_matches_independent_edge_measurement():
    t = np.arange(-40.0, 61.0)
    p, r = curve(t, delay=25), curve(t)
    full = comparison(p, r)
    expected = comparison(p, r, (-15, 10))
    clipped = benchmark.restrict_observation(full, (-15, 10))
    assert clipped.record() == expected.record()
    assert clipped.missed_crossing and clipped.observation_edge_mismatch
    assert full.both_crossed


def test_case_summary_keeps_all_four_outcomes_clusters_and_censored_denominators():
    t = np.arange(-30.0, 31.0)
    pairs = [
        (curve(t), curve(t, impact=2)),
        (curve(t, impact=2), curve(t)),
        (curve(t), curve(t)),
        (curve(t, impact=2), curve(t, impact=3)),
    ]
    rows = []
    for k, (p, r) in enumerate(pairs):
        identity = {"mission": "synthetic", "window": "quiet", "set_epoch": "epoch", "lead_h": 24, "trial_id": "one"}
        rows.append(benchmark.flatten_case(identity, {"offset_fraction": k}, "beam", "full", comparison(p, r)))
    result = benchmark.summarise_cases(pd.DataFrame(rows))[0]
    assert result["n_cases"] == 4 and result["n_sets"] == result["n_trials"] == result["n_missions"] == 1
    assert [result[f + "_n"] for f in ("false_crossing", "missed_crossing", "both_crossed", "true_negative")] == [1] * 4
    assert result["false_fraction_of_prediction_crossings"] == 0.5
    assert result["missed_fraction_of_reference_crossings"] == 0.5
    assert result["entry_time_error_s_n"] == result["exit_time_error_s_n"] == 1


def test_synthetic_runner_writes_protocol_raw_curves_cases_and_denominators(tmp_path, monkeypatch):
    source = tmp_path / "trials.csv"
    trial().to_csv(source, index=False)
    monkeypatch.setattr(benchmark, "BEAM_FILES", ("synthetic.npz",))
    monkeypatch.setattr(site.MeasuredBeam, "load", lambda path: EllipticalBeam())
    elements = benchmark.validate_trials(trial())[["norad_id", "set_epoch"]].rename(columns={"set_epoch": "epoch"})
    monkeypatch.setattr(benchmark, "load_selected_elements", lambda *args: elements)
    t = np.arange(-180.0, 181.0)
    nominal, truth = curve(t), curve(t, impact=2)
    sat = SimpleNamespace(sgp4_array=lambda jd, fr: (np.zeros(len(t)), nominal.sightline_enu, nominal.sightline_enu))
    monkeypatch.setattr(benchmark, "build_satrecs", lambda frame: [sat])
    orbit = SimpleNamespace(
        files=["synthetic"],
        states_teme=lambda times: (truth.sightline_enu, truth.sightline_enu, np.ones(len(t), dtype=bool)),
    )
    calls = []

    def load_truth(*args, **kwargs):
        assert (tmp_path / "out" / "radio_track_protocol.json").exists()
        calls.append((args, kwargs))
        return orbit, None

    monkeypatch.setattr(benchmark.reference, "load_truth", load_truth)
    monkeypatch.setattr(
        site,
        "look_from_teme",
        lambda _, pos, dates: site.Look(np.full(len(t), 1000), np.full(len(t), 45), np.zeros(len(t)), pos),
    )
    monkeypatch.setattr(
        benchmark,
        "pointing_family",
        lambda *args: [
            {
                "offset_fraction": 0.0,
                "offset_deg": 0.0,
                "signed_boundary_radius_deg": 1.0,
                "normal_xy": [0.0, 1.0],
                "ra_deg": 0.0,
                "dec_deg": 0.0,
                "boresight_enu": nominal.boresight_enu,
            }
        ],
    )
    summary = benchmark.run_track_benchmark(source, tmp_path / "out")
    assert summary["n_input_trials"] == summary["n_eligible_trials"] == 1
    assert summary["n_cases"] == 3
    assert len(calls) == 1 and calls[0][1] == {"offline": True, "records": False}
    cases = pd.read_csv(tmp_path / "out" / "radio_track_cases.csv")
    assert cases.false_crossing.all() and len(list((tmp_path / "out" / "curves").glob("*.npz"))) == 1
    assert len((tmp_path / "out" / "radio_track_cases.jsonl").read_text().splitlines()) == 3
    assert json.loads((tmp_path / "out" / "radio_track_progress.json").read_text())["status"] == "complete"
    with pytest.raises(FileExistsError):
        benchmark.run_track_benchmark(source, tmp_path / "out")
