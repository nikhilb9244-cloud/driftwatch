"""SpaceX's published ephemerides: the file format, the store and the covariance model.

The file format is read from a synthetic file rather than a downloaded one, because the
raw files are not redistributed (`docs/data-sources.md`) and so cannot live in the
repository. What matters and is checked here: the epoch format, the ordering of the 21
lower-triangle covariance entries, the thinning, and that the model hands back to the base
model outside the file's 72-hour validity with a label that says it did.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from driftwatch.ephemeris import spacex
from driftwatch.risk.covariance import DEFAULT_GROWTH, EmpiricalCovariance, ObjectRef

T0 = datetime(2026, 9, 2, 9, 23, 42, tzinfo=UTC)
NORAD_ID = 69228


def synthetic_file(
    *,
    start: datetime = T0,
    hours: float = 72.0,
    step_s: float = 60.0,
    sigma_r_km: float = 0.1,
    sigma_i_km: float = 1.0,
    sigma_c_km: float = 0.01,
) -> str:
    """One ephemeris in the published format: four header lines, then four lines per state.

    The covariance is constant so the expected value at any time is known exactly; the 21
    numbers are the lower triangle of the 6x6, row-major, so the position block is the first
    six and its diagonal sits at offsets 0, 2 and 5.
    """
    stop = start + timedelta(hours=hours)
    lines = [
        f"created:{start.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"ephemeris_start:{start.strftime('%Y-%m-%d %H:%M:%S')} UTC "
        f"ephemeris_stop:{stop.strftime('%Y-%m-%d %H:%M:%S')} UTC step_size:{step_s:g}",
        "ephemeris_source:blend",
        "UVW",
    ]
    lower = [
        sigma_r_km**2,
        0.0,
        sigma_i_km**2,
        0.0,
        0.0,
        sigma_c_km**2,
        *([0.0] * 15),
    ]
    n = int(hours * 3600 / step_s) + 1
    for i in range(n):
        t = start + timedelta(seconds=i * step_s)
        stamp = f"{t.year:04d}{t.timetuple().tm_yday:03d}{t.hour:02d}{t.minute:02d}{t.second:02d}.000"
        lines.append(f"{stamp} 774.9 6585.0 1696.7 1.19 1.76 -7.33")
        for row in range(3):
            lines.append(" ".join(f"{v:.10e}" for v in lower[7 * row : 7 * row + 7]))
    return "\n".join(lines) + "\n"


def test_the_manifest_gives_a_norad_id_per_file():
    text = (
        "MEME_69228_STARLINK-37618_2450923_Operational_1472635440_UNCLASSIFIED.txt\n"
        "MEME_52355_STARLINK-3877_2451115_Operational_1472642160_UNCLASSIFIED.txt\n"
        "README.md\n"
        "\n"
    )
    entries = spacex.parse_manifest(text)
    assert [e.norad_id for e in entries] == [69228, 52355]
    assert entries[0].name == "STARLINK-37618"
    assert entries[0].file_name.endswith("UNCLASSIFIED.txt")


def test_the_ephemeris_parses_its_epochs_covariance_ordering_and_thins_to_the_requested_step():
    text = synthetic_file(hours=2.0, sigma_r_km=0.1, sigma_i_km=1.0, sigma_c_km=0.01)
    frame, header = spacex.parse_ephemeris(text, step_s=600.0)

    assert header["ephemeris_source"] == "blend"
    assert header["frame"] == "UVW"
    assert header["n_states"] == 121  # two hours at a minute, inclusive
    # Every ten minutes, and the last state kept whatever the stride lands on.
    assert len(frame) == 13
    assert pd.Timestamp(frame["t"].iloc[0]) == pd.Timestamp(T0).tz_localize(None)
    assert pd.Timestamp(frame["t"].iloc[-1]) == pd.Timestamp(T0 + timedelta(hours=2)).tz_localize(None)
    assert (np.diff(frame["t"].to_numpy()) / np.timedelta64(1, "s") == 600.0).all()

    # The 21 numbers are the lower triangle of the 6x6, so R, I and C are entries 0, 2 and 5.
    np.testing.assert_allclose(frame["cov_rr_km2"], 0.1**2)
    np.testing.assert_allclose(frame["cov_ii_km2"], 1.0**2)
    np.testing.assert_allclose(frame["cov_cc_km2"], 0.01**2)
    np.testing.assert_allclose(frame[["cov_ri_km2", "cov_rc_km2", "cov_ic_km2"]], 0.0)


def test_a_covariance_in_the_wrong_frame_is_refused():
    text = synthetic_file(hours=0.5).replace("UVW", "EME2000", 1)
    with pytest.raises(ValueError, match="EME2000"):
        spacex.parse_ephemeris(text)


def stored_frame(**kwargs) -> pd.DataFrame:
    frame, header = spacex.parse_ephemeris(synthetic_file(**kwargs), step_s=600.0)
    frame.insert(0, "norad_id", NORAD_ID)
    frame.insert(1, "name", "STARLINK-37618")
    frame.insert(2, "created", pd.Timestamp(T0))
    frame.insert(3, "ephemeris_start", pd.Timestamp(header["ephemeris_start"].replace(" UTC", ""), tz="UTC"))
    frame.insert(4, "ephemeris_stop", pd.Timestamp(header["ephemeris_stop"].replace(" UTC", ""), tz="UTC"))
    frame.insert(5, "ephemeris_source", "blend")
    return frame[list(spacex.EPHEMERIS_COLUMNS)]


def test_the_model_serves_spacex_inside_the_file_and_hands_back_outside_it():
    """Their covariance for the three days it covers, the base model for days four to seven."""
    base = EmpiricalCovariance()
    model = spacex.SpacexEphemerisCovariance(base, stored_frame(sigma_i_km=1.0))
    ref = ObjectRef(NORAD_ID, "starlink", "leo")
    epoch = T0 - timedelta(hours=2)

    def at(hours: float) -> np.ndarray:
        return np.array([np.datetime64((T0 + timedelta(hours=hours)).replace(tzinfo=None), "us")])

    inside = model.covariance_ric(ref, epoch, at(24.0))
    assert inside.source == "spacex-ephemeris"
    np.testing.assert_allclose(np.sqrt(np.diag(inside.cov_km2[0])), [0.1, 1.0, 0.01], rtol=1e-9)

    # Past the 72-hour horizon the base model serves and reports its own label, so the report
    # can say which of the three models covered each event.
    outside = model.covariance_ric(ref, epoch, at(120.0))
    assert outside.source == "default:leo"
    np.testing.assert_allclose(outside.cov_km2, base.covariance_ric(ref, epoch, at(120.0)).cov_km2)
    assert outside.cov_km2[0, 1, 1] > inside.cov_km2[0, 1, 1]  # and it is much larger

    mixed = model.covariance_ric(ref, epoch, np.concatenate([at(24.0), at(120.0)]))
    assert mixed.source == "spacex-ephemeris+default:leo"
    np.testing.assert_allclose(mixed.cov_km2[0], inside.cov_km2[0])
    np.testing.assert_allclose(mixed.cov_km2[1], outside.cov_km2[0])

    # An object with no stored file falls through untouched.
    other = ObjectRef(4242, "debris", "leo")
    assert model.covariance_ric(other, epoch, at(24.0)).source == "default:leo"
    assert model.version.endswith("+spacex-ephemeris/1")


def test_the_published_covariance_is_used_as_published_unless_the_fit_floor_is_asked_for():
    """The instruction was to use it as published; the fit-residual floor is an opt-in.

    The geometry driftwatch propagates comes from CelesTrak's SGP4 fit to this ephemeris,
    not from the ephemeris, and that fit's own residual is larger than SpaceX's sigma inside
    the first several hours. Applying it is a decision for the review, not a default.
    """
    frame = stored_frame(sigma_i_km=0.05)
    ref = ObjectRef(NORAD_ID, "starlink", "leo")
    at = np.array([np.datetime64((T0 + timedelta(hours=4)).replace(tzinfo=None), "us")])

    plain = spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), frame)
    assert np.sqrt(plain.covariance_ric(ref, T0, at).cov_km2[0, 1, 1]) == pytest.approx(0.05)

    floored = spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), frame, add_fit_rms_floor=True, fit_rms_km=0.2)
    assert np.sqrt(floored.covariance_ric(ref, T0, at).cov_km2[0, 1, 1]) == pytest.approx(0.2 / np.sqrt(3.0))


def test_the_store_keeps_only_the_newest_version_of_each_satellite(tmp_path):
    old = stored_frame(sigma_i_km=5.0)
    new = stored_frame(sigma_i_km=1.0)
    new["created"] = pd.Timestamp(T0 + timedelta(hours=8))
    spacex.write_store(old, spacex.store_path(datetime(2026, 9, 2, 1, tzinfo=UTC), tmp_path))
    spacex.write_store(new, spacex.store_path(datetime(2026, 9, 2, 9, tzinfo=UTC), tmp_path))

    both = spacex.load_store(out_dir=tmp_path, latest_only=False)
    latest = spacex.load_store(out_dir=tmp_path)
    assert len(both) == 2 * len(latest)
    np.testing.assert_allclose(latest["cov_ii_km2"], 1.0)
    assert spacex.load_store([12345], out_dir=tmp_path).empty


def test_only_the_starlink_secondaries_of_a_run_are_selected_closest_approach_first():
    objects = pd.DataFrame({"norad_id": [10, 11, 12, 13], "category": ["starlink", "starlink", "starlink", "debris"]})
    events = pd.DataFrame(
        {
            "secondary_norad_id": [10, 10, 11, 12, 13],
            "miss_km": [8.0, 3.0, 1.0, 20.0, 0.5],
        }
    )
    assert spacex.select_objects(events, objects) == [11, 10, 12]
    assert spacex.select_objects(events, objects, limit=2) == [11, 10]
    assert spacex.select_objects(events.iloc[4:], objects) == []


def test_the_cross_check_puts_their_number_beside_ours_without_merging_them():
    """Two different quantities: their uncertainty within one plan, ours of the plan being revised."""
    model = EmpiricalCovariance(defaults=DEFAULT_GROWTH)
    table = spacex.cross_check(stored_frame(sigma_i_km=1.0), model, leads_hours=(3.0, 24.0))
    assert list(table["lead_hours"]) == [3.0, 24.0]
    np.testing.assert_allclose(table["spacex_sigma_i_km"], 1.0)
    # The default LEO prior grows in-track at about a kilometre a day, so the ratio grows too.
    assert table["ratio_i"].iloc[1] > table["ratio_i"].iloc[0]
    assert (table["ours_source"] == "default:leo").all()
