"""SpaceX's published ephemerides: the file format, the store, the states and the covariance.

The file format is read from a synthetic file rather than a downloaded one, because the
raw files are not redistributed (`docs/data-sources.md`) and so cannot live in the
repository. What matters and is checked here: the epoch format, the ordering of the 21
lower-triangle covariance entries, the thinning, and that the model hands back to the base
model outside the file's 72-hour validity with a label that says it did.

Phase 4 Step 1 adds the states. The synthetic file therefore carries a real circular orbit
rather than a fixed point, so that the frame rotation, the Hermite thinning and the break
detector have something to be right or wrong about.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from driftwatch import config
from driftwatch.ephemeris import spacex
from driftwatch.orbit.frames import j2000_to_teme
from driftwatch.risk.covariance import (
    DEFAULT_GROWTH,
    EmpiricalCovariance,
    FlooredGrowth,
    ObjectRef,
    PowerLawGrowth,
    SupplementalCovariance,
)

T0 = datetime(2026, 9, 2, 9, 23, 42, tzinfo=UTC)
NORAD_ID = 69228


MU_KM3_S2 = 398600.4418


def circular_states(
    n: int, step_s: float, *, radius_km: float = 6871.0, jump_km: float = 0.0, jump_at: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """A circular orbit sampled on a regular grid, optionally with a step change part way.

    Position and velocity are exact derivatives of each other, which is what a Hermite
    interpolant needs and what makes the measured interpolation error meaningful. ``jump_km``
    displaces everything from ``jump_at`` onwards, which is what the seam in a real file looks
    like: two smooth arcs that do not quite meet.
    """
    omega = np.sqrt(MU_KM3_S2 / radius_km**3)
    t = np.arange(n) * float(step_s)
    u = np.array([1.0, 0.0, 0.0])
    w = np.array([0.0, np.cos(np.radians(53.0)), np.sin(np.radians(53.0))])
    angle = omega * t
    r = radius_km * (np.cos(angle)[:, None] * u + np.sin(angle)[:, None] * w)
    v = radius_km * omega * (-np.sin(angle)[:, None] * u + np.cos(angle)[:, None] * w)
    if jump_km and jump_at is not None:
        r[jump_at:] += jump_km * np.array([0.0, 0.0, 1.0])
    return r, v


def synthetic_file(
    *,
    start: datetime = T0,
    hours: float = 72.0,
    step_s: float = 60.0,
    sigma_r_km: float = 0.1,
    sigma_i_km: float = 1.0,
    sigma_c_km: float = 0.01,
    jump_km: float = 0.0,
    jump_at: int | None = None,
) -> str:
    """One ephemeris in the published format: four header lines, then four lines per state.

    The covariance is constant so the expected value at any time is known exactly; the 21
    numbers are the lower triangle of the 6x6, row-major, so the position block is the first
    six and its diagonal sits at offsets 0, 2 and 5. The states are a circular orbit in the
    file's own MEME frame.
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
    r, v = circular_states(n, step_s, jump_km=jump_km, jump_at=jump_at)
    for i in range(n):
        t = start + timedelta(seconds=i * step_s)
        stamp = f"{t.year:04d}{t.timetuple().tm_yday:03d}{t.hour:02d}{t.minute:02d}{t.second:02d}.000"
        state = " ".join(f"{x:.10f}" for x in (*r[i], *v[i]))
        lines.append(f"{stamp} {state}")
        for row in range(3):
            lines.append(" ".join(f"{value:.10e}" for value in lower[7 * row : 7 * row + 7]))
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
    frame, _states, header = spacex.parse_ephemeris(text, step_s=600.0)

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
    frame, _states, header = spacex.parse_ephemeris(synthetic_file(**kwargs), step_s=600.0)
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
    # fit_rms_km=0.0 isolates the hand-over: what the published numbers are, and where the
    # base model takes over. The fit residual the default carries is the test below.
    model = spacex.SpacexEphemerisCovariance(base, stored_frame(sigma_i_km=1.0), fit_rms_km=0.0)
    ref = ObjectRef(NORAD_ID, "starlink", "leo")
    epoch = T0 - timedelta(hours=2)

    def at(hours: float) -> np.ndarray:
        return np.array([np.datetime64((T0 + timedelta(hours=hours)).replace(tzinfo=None), "us")])

    inside = model.covariance_ric(ref, epoch, at(24.0))
    assert list(inside.source) == ["spacex-ephemeris"]
    np.testing.assert_allclose(np.sqrt(np.diag(inside.cov_km2[0])), [0.1, 1.0, 0.01], rtol=1e-9)

    # Past the 72-hour horizon the base model serves and reports its own label, so the report
    # can say which of the three models covered each event.
    outside = model.covariance_ric(ref, epoch, at(120.0))
    assert outside.source == "default:leo"
    np.testing.assert_allclose(outside.cov_km2, base.covariance_ric(ref, epoch, at(120.0)).cov_km2)
    assert outside.cov_km2[0, 1, 1] > inside.cov_km2[0, 1, 1]  # and it is much larger

    # One label per time, not one for the object: Phase 4 Step 1 needs to say which *events*
    # were served by the published covariance, because that is what decides whether the SGP4
    # fit residual belongs on them.
    mixed = model.covariance_ric(ref, epoch, np.concatenate([at(24.0), at(120.0)]))
    assert list(mixed.source) == ["spacex-ephemeris", "default:leo"]
    np.testing.assert_allclose(mixed.cov_km2[0], inside.cov_km2[0])
    np.testing.assert_allclose(mixed.cov_km2[1], outside.cov_km2[0])

    # An object with no stored file falls through untouched.
    other = ObjectRef(4242, "debris", "leo")
    assert model.covariance_ric(other, epoch, at(24.0)).source == "default:leo"
    assert "+spacex-ephemeris/3" in model.version


def test_the_sgp4_fit_residual_is_added_in_quadrature_by_default():
    """The covariance describes the ephemeris; we propagate CelesTrak's SGP4 fit to it.

    Those are two independent errors -- SpaceX's own uncertainty about where the satellite
    will be, and the distance between their ephemeris and the element set driftwatch
    actually propagates -- so the published residual of that fit adds in quadrature. Inside
    the first several hours it is the larger of the two, which is the whole point: used as
    published, the covariance is tighter than the gap between the two trajectories it sits
    between. `fit_rms_km=0.0` restores the as-published behaviour.
    """
    frame = stored_frame(sigma_i_km=0.05)
    ref = ObjectRef(NORAD_ID, "starlink", "leo")
    at = np.array([np.datetime64((T0 + timedelta(hours=4)).replace(tzinfo=None), "us")])

    published = spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), frame, fit_rms_km=0.0)
    assert np.sqrt(published.covariance_ric(ref, T0, at).cov_km2[0, 1, 1]) == pytest.approx(0.05)
    assert published.version.endswith("+spacex-ephemeris/3")

    model = spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), frame)
    assert model.fit_rms_km == config.SPACEX_SGP4_FIT_RMS_KM
    cov = model.covariance_ric(ref, T0, at).cov_km2[0]
    share = model.fit_rms_share
    for k in range(3):
        added = (share[k] * model.fit_rms_km) ** 2
        assert cov[k, k] == pytest.approx(published.covariance_ric(ref, T0, at).cov_km2[0, k, k] + added)
    # In-track dominated, because that is where an SGP4 fit to an ephemeris misses.
    assert share[1] > share[0] > share[2]
    assert np.sqrt(cov[1, 1]) == pytest.approx(np.hypot(0.05, share[1] * model.fit_rms_km))
    # Adding on the diagonal only cannot break positive definiteness.
    assert np.all(np.linalg.eigvalsh(cov) > 0)
    # And the model version says the residual is in there, so a stored row records it.
    assert "sgp4-fit-0.2km" in model.version


def test_the_fit_residual_is_split_in_the_shape_of_the_base_models_own_floor():
    """CelesTrak publishes one scalar. The base model's measured floor says what shape it has."""
    frame = stored_frame(sigma_i_km=0.05)
    base = SupplementalCovariance(
        EmpiricalCovariance(),
        {NORAD_ID: FlooredGrowth(PowerLawGrowth((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), (0.0, 1.0, 0.0), 0.2)},
        {NORAD_ID: "supplemental:rms"},
    )
    model = spacex.SpacexEphemerisCovariance(base, frame)
    # An entirely in-track floor puts the whole residual in-track and none of it elsewhere.
    assert model.fit_rms_share == pytest.approx((0.0, 1.0, 0.0))

    # With nothing to take a shape from, the configured shape stands in.
    assert spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), frame).fit_rms_share == pytest.approx(
        config.SPACEX_FIT_RMS_SHARE
    )


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


# --------------------------------------------------------------------------------------
# Phase 4 Step 1: the states, the frame, the breaks and the per-event fit residual


def parsed_states(**kwargs) -> pd.DataFrame:
    _cov, states, _header = spacex.parse_ephemeris(synthetic_file(**kwargs), step_s=600.0)
    return states


def test_the_states_are_rotated_out_of_the_files_meme_frame_into_teme():
    """MEME is not TEME, and at this radius the difference is tens of kilometres, not metres.

    The file names declare the frame; the header names only the covariance's. Reading the
    states as TEME would be a 44 km error in 2026 -- two hundred times the fit residual the
    whole exercise exists to remove -- so the rotation is checked against the published states
    it came from rather than assumed.
    """
    hours, step_s = 2.0, 60.0
    n = int(hours * 3600 / step_s) + 1
    r_file, v_file = circular_states(n, step_s)
    states = parsed_states(hours=hours, step_s=step_s)

    times = states["t"].to_numpy(dtype="datetime64[us]")
    kept = np.searchsorted(
        (np.arange(n) * step_s).astype(float), ((times - times[0]) / np.timedelta64(1, "s")).astype(float)
    )
    expected_r, expected_v = j2000_to_teme(r_file[kept], v_file[kept], times)
    np.testing.assert_allclose(states[["x_km", "y_km", "z_km"]].to_numpy(), expected_r, atol=1e-9)
    np.testing.assert_allclose(states[["vx_kms", "vy_kms", "vz_kms"]].to_numpy(), expected_v, atol=1e-12)
    assert set(states["state_frame"]) == {config.SPACEX_STATE_FRAME}
    # And the rotation is not the identity: if it were, the whole check would pass vacuously.
    assert np.linalg.norm(expected_r[0] - r_file[0]) > 10.0


def test_the_stored_grid_reproduces_the_files_own_states_to_metres():
    """The hold-out test, on the shipped grid: keep every other state and predict the rest."""
    states = parsed_states(hours=6.0, step_s=60.0)
    assert float(states["interp_err_median_m"].iloc[0]) < 10.0
    assert float(states["interp_err_max_m"].iloc[0]) < 20.0
    # Well under the 200 m fit residual it replaces, which is the point of the exercise.
    assert float(states["interp_err_max_m"].iloc[0]) < 0.1 * 1000.0 * config.SPACEX_SGP4_FIT_RMS_KM


def test_a_discontinuity_splits_the_stored_history_and_no_interpolant_spans_it():
    """Every real file has a seam at 48 hours; a manoeuvre would look the same and is treated so."""
    step_s, hours = 60.0, 4.0
    jump_at = 120  # two hours in
    clean = parsed_states(hours=hours, step_s=step_s)
    broken = parsed_states(hours=hours, step_s=step_s, jump_km=0.4, jump_at=jump_at)

    assert int(clean["n_breaks"].iloc[0]) == 0
    assert int(broken["n_breaks"].iloc[0]) == 1
    assert set(broken["segment"]) == {0, 1}

    # The two segments meet either side of the jump and never across it.
    first_end = broken.loc[broken["segment"] == 0, "t"].max()
    second_start = broken.loc[broken["segment"] == 1, "t"].min()
    gap_s = (second_start - first_end) / np.timedelta64(1, "s")
    assert gap_s == pytest.approx(step_s)

    # And segmenting keeps the measured error at the smooth-arc value rather than the jump's.
    assert float(broken["interp_err_max_m"].iloc[0]) < 20.0
    assert float(broken["interp_err_max_m"].iloc[0]) < 0.05 * 1000.0 * 0.4


def test_the_trajectory_interpolates_inside_a_segment_and_refuses_outside_it():
    trajectory = spacex.EphemerisTrajectory(stored_states(hours=4.0, jump_km=0.4, jump_at=120))
    assert NORAD_ID in trajectory
    assert 4242 not in trajectory

    inside = np.array([np.datetime64((T0 + timedelta(minutes=30)).replace(tzinfo=None), "us")])
    r, v, covered = trajectory.states(NORAD_ID, inside)
    assert covered.all()
    # A circular orbit: the interpolated radius and speed are the ones it was built from.
    assert np.linalg.norm(r[0]) == pytest.approx(6871.0, abs=0.05)
    assert np.linalg.norm(v[0]) == pytest.approx(np.sqrt(MU_KM3_S2 / 6871.0), abs=1e-4)

    # Past the end of the file there is nothing to interpolate, and nothing is invented.
    beyond = np.array([np.datetime64((T0 + timedelta(hours=9)).replace(tzinfo=None), "us")])
    _r, _v, out = trajectory.states(NORAD_ID, beyond)
    assert not out.any()

    # Inside the break the same is true: the gap is uncovered, not bridged. The jump sits
    # between file nodes 119 and 120, so the 60 seconds between them belong to no segment.
    gap = np.array([np.datetime64((T0 + timedelta(seconds=119 * 60 + 30)).replace(tzinfo=None), "us")])
    assert not trajectory.covers(NORAD_ID, gap).any()


def stored_states(**kwargs) -> pd.DataFrame:
    states = parsed_states(**kwargs)
    states.insert(0, "norad_id", NORAD_ID)
    states.insert(1, "name", "STARLINK-37618")
    states.insert(2, "created", pd.Timestamp(T0))
    states.insert(3, "ephemeris_start", pd.Timestamp(T0))
    states.insert(4, "ephemeris_stop", pd.Timestamp(T0 + timedelta(hours=72)))
    return states[list(spacex.STATE_COLUMNS)]


def test_the_fit_residual_goes_per_event_not_globally():
    """An event refined on the published states has no SGP4 fit in its chain; one past the
    horizon still does, and the two must not be given the same covariance.

    This is the Step 1 correction to Phase 2's patch. The residual was applied to every served
    covariance because the trajectory always came from the fit; now it applies only where it
    still does, and ``cov_source_secondary`` says which is which per event rather than per
    object.
    """
    frame = stored_frame(sigma_i_km=0.05)
    ref = ObjectRef(NORAD_ID, "starlink", "leo")

    def at(hours: float) -> np.datetime64:
        return np.datetime64((T0 + timedelta(hours=hours)).replace(tzinfo=None), "us")

    # What the screening recorded: this event's geometry came from the published states.
    events = pd.DataFrame(
        {
            "primary_norad_id": [4242, 4242],
            "secondary_norad_id": [NORAD_ID, NORAD_ID],
            "tca": pd.to_datetime([at(2.0), at(6.0)], utc=True),
            "primary_trajectory": ["sgp4", "sgp4"],
            "secondary_trajectory": ["spacex-ephemeris", "sgp4"],
        }
    )
    served = spacex.interpolated_times_from_events(events)
    assert list(served) == [NORAD_ID]
    model = spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), frame, interpolated_times=served)
    # Two hours in: interpolated, so the covariance is exactly as SpaceX published it.
    # Six hours in: past the stored states but inside the covariance's validity, so the
    # trajectory is still the SGP4 fit and the residual is still there.
    result = model.covariance_ric(ref, T0, np.array([at(2.0), at(6.0)]))
    assert list(result.source) == ["spacex-ephemeris", "spacex-ephemeris+sgp4-fit"]
    assert np.sqrt(result.cov_km2[0, 1, 1]) == pytest.approx(0.05)
    assert np.sqrt(result.cov_km2[1, 1, 1]) == pytest.approx(
        np.hypot(0.05, model.fit_rms_share[1] * model.fit_rms_km)
    )
    assert model.fit_rms_summary()["served_without_fit_term"] == 1
    assert model.fit_rms_summary()["served_with_fit_term"] == 1

    # Without a trajectory the model behaves exactly as version 2 did: every served time
    # carries the residual, because every one of them is still refined on the fit.
    plain = spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), frame)
    assert list(plain.covariance_ric(ref, T0, np.array([at(2.0)])).source) == ["spacex-ephemeris+sgp4-fit"]


def test_the_state_store_keeps_only_the_newest_version_of_each_satellite(tmp_path):
    old = stored_states(hours=4.0)
    new = stored_states(hours=4.0)
    new["created"] = pd.Timestamp(T0 + timedelta(hours=8))
    spacex.write_state_store(old, spacex.state_store_path(datetime(2026, 9, 2, 1, tzinfo=UTC), tmp_path))
    spacex.write_state_store(new, spacex.state_store_path(datetime(2026, 9, 2, 9, tzinfo=UTC), tmp_path))

    assert len(spacex.load_state_store(out_dir=tmp_path, latest_only=False)) == len(old) + len(new)
    latest = spacex.load_state_store(out_dir=tmp_path)
    assert len(latest) == len(new)
    assert set(latest["created"]) == {pd.Timestamp(T0 + timedelta(hours=8))}
    assert spacex.load_state_store([12345], out_dir=tmp_path).empty
