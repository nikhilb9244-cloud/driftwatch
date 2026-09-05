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

import logging
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

    # The same version fetched again is one copy, not two: the tie on `created` goes to the later fetch.
    spacex.write_store(new, spacex.store_path(datetime(2026, 9, 2, 10, tzinfo=UTC), tmp_path))
    assert len(spacex.load_store(out_dir=tmp_path)) == len(new)


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


def stored_states(*, start: datetime = T0, **kwargs) -> pd.DataFrame:
    """One satellite's stored state history, as a fetch of the version created at ``start`` writes it."""
    states = parsed_states(start=start, **kwargs)
    states.insert(0, "norad_id", NORAD_ID)
    states.insert(1, "name", "STARLINK-37618")
    states.insert(2, "created", pd.Timestamp(start))
    states.insert(3, "ephemeris_start", pd.Timestamp(start))
    states.insert(4, "ephemeris_stop", pd.Timestamp(start + timedelta(hours=72)))
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
    assert np.sqrt(result.cov_km2[1, 1, 1]) == pytest.approx(np.hypot(0.05, model.fit_rms_share[1] * model.fit_rms_km))
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


def test_the_same_version_fetched_twice_is_one_copy_and_a_newer_version_replaces_the_overlap(tmp_path):
    """Pipeline run 6, 2026-09-05. Run 5 fetched at 09:33 UTC and run 6 at 10:48 UTC, inside one
    refresh window, so both held the files created at 01:25; the store the Actions cache carried
    between them had both copies, the newest-version rule kept both because they tie on
    ``created``, every epoch of every segment appeared twice, and the Hermite interpolant refused
    the grid. The tie goes to the later fetch, and a newer version replaces the older one where
    they overlap rather than joining it.
    """
    first = stored_states(hours=4.0)
    spacex.write_state_store(first, spacex.state_store_path(datetime(2026, 9, 5, 9, 33, tzinfo=UTC), tmp_path))
    spacex.write_state_store(first, spacex.state_store_path(datetime(2026, 9, 5, 10, 48, tzinfo=UTC), tmp_path))

    once = spacex.load_state_store(out_dir=tmp_path)
    assert len(once) == len(first)
    assert not once.duplicated(["norad_id", "segment", "t"]).any()
    trajectory = spacex.load_trajectory(out_dir=tmp_path)
    assert len(trajectory.segments[NORAD_ID]) == 1
    # The store did the work; the loader had nothing to repair and says nothing.
    assert trajectory.repairs["objects"] == 0
    assert "repairs" not in trajectory.summary()
    early = np.array([np.datetime64((T0 + timedelta(hours=1)).replace(tzinfo=None), "us")])
    assert trajectory.covers(NORAD_ID, early).all()

    # A newer version starting two hours in overlaps the first for two hours. It replaces it,
    # overlap and all: the rows left are exactly its own, and in the overlap it is the one that serves.
    newer = stored_states(hours=4.0, start=T0 + timedelta(hours=2))
    spacex.write_state_store(newer, spacex.state_store_path(datetime(2026, 9, 5, 12, 0, tzinfo=UTC), tmp_path))
    latest = spacex.load_state_store(out_dir=tmp_path)
    assert len(latest) == len(newer)
    assert set(latest["created"]) == {pd.Timestamp(T0 + timedelta(hours=2))}
    assert not latest.duplicated(["norad_id", "segment", "t"]).any()
    replaced = spacex.load_trajectory(out_dir=tmp_path)
    overlap = np.array([np.datetime64((T0 + timedelta(hours=3)).replace(tzinfo=None), "us")])
    r_store, _v, covered = replaced.states(NORAD_ID, overlap)
    r_newer, _v, _c = spacex.EphemerisTrajectory(newer).states(NORAD_ID, overlap)
    r_first, _v, _c = spacex.EphemerisTrajectory(first).states(NORAD_ID, overlap)
    assert covered.all()
    np.testing.assert_allclose(r_store, r_newer)
    assert np.linalg.norm(r_store - r_first) > 1.0
    # The older version's hours the newer does not reach went with it: a revised plan is replaced, not spliced.
    assert not replaced.covers(NORAD_ID, early).any()


def test_the_loader_drops_a_repeated_epoch_and_splits_where_one_epoch_carries_two_states(caplog):
    """The store should make this a no-op; the loader refuses to fall over if it does not."""
    states = stored_states(hours=4.0)
    epochs = states["t"].to_numpy(dtype="datetime64[us]")

    # The same row twice, and the table shuffled so the sort is exercised too: one copy is kept.
    doubled = pd.concat([states, states.iloc[[10]]], ignore_index=True).sample(frac=1.0, random_state=1)
    trajectory = spacex.EphemerisTrajectory(doubled)
    assert len(trajectory.segments[NORAD_ID]) == 1
    lo, hi, spline = trajectory.segments[NORAD_ID][0]
    assert (lo, hi) == (epochs[0], epochs[-1])
    assert spline.t_s.size == len(states)
    assert trajectory.repairs == {"objects": 1, "repeated_epochs_dropped": 1, "segments_split": 0}
    assert trajectory.summary()["repairs"] == trajectory.repairs

    # The same epoch with a different state is a disagreement between two trajectories, and no
    # interpolant spans it: the segment is split there, and the log says where and why.
    conflict = states.iloc[[20]].copy()
    conflict["x_km"] += 1.0
    with caplog.at_level(logging.WARNING, logger="driftwatch.ephemeris.spacex"):
        trajectory = spacex.EphemerisTrajectory(pd.concat([states, conflict], ignore_index=True))
    assert len(trajectory.segments[NORAD_ID]) == 2
    (lo1, hi1, _s1), (lo2, hi2, _s2) = trajectory.segments[NORAD_ID]
    assert (lo1, hi1) == (epochs[0], epochs[20])
    assert (lo2, hi2) == (epochs[20], epochs[-1])
    assert trajectory.repairs == {"objects": 1, "repeated_epochs_dropped": 0, "segments_split": 1}
    assert f"SpaceX states for {NORAD_ID}, segment 0: two different states share the epoch" in caplog.text
    assert str(epochs[20]) in caplog.text
    either_side = epochs[20] + np.array([-30, 30]).astype("timedelta64[s]")
    _r, _v, covered = trajectory.states(NORAD_ID, either_side)
    assert covered.all()


def test_the_state_store_is_pruned_a_week_after_validity_and_each_fetch_leaves_its_summary(tmp_path, caplog):
    """The store lives in the Actions cache and is restored and saved whole on every run, so a
    fetch's states go once its ephemerides have been invalid for seven days. What stays is a
    summary of which satellite had which version, so the history is still readable without them.
    """
    old = stored_states(hours=4.0)  # created at T0, its header says valid until T0 + 72 h
    old_path = spacex.write_state_store(old, spacex.state_store_path(T0, tmp_path))
    fresh = stored_states(hours=4.0, start=T0 + timedelta(days=9))
    fresh_path = spacex.write_state_store(fresh, spacex.state_store_path(T0 + timedelta(days=9), tmp_path))
    validity_end = T0 + timedelta(hours=72)

    # A day short of the grace: nothing goes.
    result = spacex.prune_state_store(tmp_path, now=validity_end + timedelta(days=6))
    assert (result["removed"], result["kept"]) == ([], 2)
    assert [p.name for p in spacex.list_state_store(tmp_path)] == [old_path.name, fresh_path.name]
    assert spacex.load_state_summaries(tmp_path) == []

    # An hour past it: the old file goes, its summary stays, the fresh file is untouched, and the
    # log says what went.
    now = validity_end + timedelta(days=7, hours=1)
    with caplog.at_level(logging.INFO, logger="driftwatch.ephemeris.spacex"):
        result = spacex.prune_state_store(tmp_path, now=now)
    assert (result["removed"], result["kept"]) == ([old_path.name], 1)
    assert result["bytes_freed"] > 0 and result["after_days"] == 7.0
    assert [p.name for p in spacex.list_state_store(tmp_path)] == [fresh_path.name]
    assert f"Pruned {old_path.name}" in caplog.text
    (summary,) = spacex.load_state_summaries(tmp_path)
    assert summary["file"] == old_path.name
    assert summary["fetched_at"] == "20260902T092342Z"
    assert (summary["rows"], summary["satellites"], summary["segments"]) == (len(old), 1, 1)
    assert summary["valid_from"] == pd.Timestamp(T0).isoformat()
    assert summary["valid_until"] == pd.Timestamp(validity_end).isoformat()
    assert summary["pruned_at"] == pd.Timestamp(now).isoformat()
    (version,) = summary["versions"]
    assert (version["norad_id"], version["name"]) == (NORAD_ID, "STARLINK-37618")
    assert version["created"] == pd.Timestamp(T0).isoformat()
    assert version["ephemeris_stop"] == pd.Timestamp(validity_end).isoformat()
    assert (version["rows"], version["segments"], version["n_breaks"]) == (len(old), 1, 0)

    # Pruning again removes nothing and writes no second summary; the loader still serves what is left.
    assert spacex.prune_state_store(tmp_path, now=now)["removed"] == []
    assert len(spacex.load_state_summaries(tmp_path)) == 1
    assert spacex.load_trajectory(out_dir=tmp_path).norad_ids == [NORAD_ID]

    # A file whose header carried no `ephemeris_stop` is judged by its last stored epoch instead:
    # this one's header would have kept it for three more days, its last state is an hour past the grace.
    headless_start = now - timedelta(days=7, hours=5)
    headless = stored_states(hours=4.0, start=headless_start)
    headless["ephemeris_stop"] = pd.NaT
    headless_path = spacex.write_state_store(headless, spacex.state_store_path(headless_start, tmp_path))
    assert spacex.prune_state_store(tmp_path, now=now)["removed"] == [headless_path.name]
    last_epoch = pd.Timestamp(headless_start + timedelta(hours=4)).isoformat()
    assert spacex.load_state_summaries(tmp_path)[-1]["valid_until"] == last_epoch


def test_the_frame_check_passes_on_matching_states_and_fails_on_a_rotation_error():
    """The guard that runs on every fetch, in both directions.

    The failure this exists for is silent: states in the wrong frame are smooth, interpolate
    cleanly and produce plausible conjunctions in the wrong place. So the check is a comparison
    against an independent trajectory -- CelesTrak's SGP4 fit to the same file -- and its two
    plausible outcomes are hundreds of metres (the published fit residual) or tens of kilometres
    (a frame error). Nothing sits between them, which is why a 5 km threshold is not a
    judgement call. See docs/ephemeris-frame.md.
    """
    from driftwatch.orbit.propagator import satrec_from_elements
    from driftwatch.orbit.time import julian_dates

    epoch = T0 - timedelta(hours=1)
    elements = pd.DataFrame(
        {
            "norad_id": [NORAD_ID],
            "epoch": [pd.Timestamp(epoch)],
            "mean_motion": [15.06],
            "eccentricity": [0.0002],
            "inclination_deg": [53.05],
            "raan_deg": [130.0],
            "arg_perigee_deg": [80.0],
            "mean_anomaly_deg": [200.0],
            "bstar": [3.5e-4],
            "mean_motion_dot": [0.0],
            "mean_motion_ddot": [0.0],
        }
    )
    satrec = satrec_from_elements(NORAD_ID, epoch, 15.06, 0.0002, 53.05, 130.0, 80.0, 200.0, 3.5e-4)
    times = np.array(
        [np.datetime64((T0 + timedelta(seconds=120 * k)).replace(tzinfo=None), "us") for k in range(60)],
        dtype="datetime64[us]",
    )
    jd, fr = julian_dates(times)
    err, r, _v = satrec.sgp4_array(jd, fr)
    assert (err == 0).all()
    states = pd.DataFrame(
        {
            "norad_id": NORAD_ID,
            "t": times,
            "x_km": r[:, 0],
            "y_km": r[:, 1],
            "z_km": r[:, 2],
        }
    )

    good = spacex.check_state_frame(states, elements)
    assert good["passed"] is True
    assert good["median_km"] < 0.001
    assert "pass" in good["verdict"]

    # A frame error is a rotation about the pole, so it displaces without changing the radius.
    # 44 km is what MEME-read-as-TEME costs at this altitude in 2026.
    angle = np.radians(0.365)
    rotated = states.copy()
    x, y = states["x_km"].to_numpy(), states["y_km"].to_numpy()
    rotated["x_km"] = x * np.cos(angle) - y * np.sin(angle)
    rotated["y_km"] = x * np.sin(angle) + y * np.cos(angle)
    bad = spacex.check_state_frame(rotated, elements)
    assert bad["passed"] is False
    assert bad["median_km"] > 20.0
    assert "FAIL" in bad["verdict"] and "docs/ephemeris-frame.md" in bad["verdict"]

    # With nothing to check against, the check says so rather than passing by default.
    empty = spacex.check_state_frame(states, elements.iloc[:0])
    assert "passed" not in empty
    assert "not checked" in empty["verdict"]


# --------------------------------------------------------------------------------------
# The mixed case: their covariance present, the trajectory still the SGP4 fit


def inclined_copy(base, norad_id: int, *, d_inclination_deg: float):
    """The same orbit with the plane tilted, so the two objects meet twice an orbit all week.

    Both keep the same period and the same argument of latitude, so their separation is
    ``2 r sin(di/2) |sin u|``: it goes to nothing at the two nodes and out to ``r di`` between
    them, once every half orbit. That gives events spread evenly across the window without
    designing each one, which is what this test needs -- events on both sides of the hour the
    stored states run out.
    """
    from test_screening import PRIMARY_EPOCH

    from driftwatch.orbit.propagator import satrec_from_elements

    return satrec_from_elements(
        norad_id,
        PRIMARY_EPOCH,
        base.no_kozai * 1440.0 / (2.0 * np.pi),
        base.ecco,
        np.degrees(base.inclo) + d_inclination_deg,
        np.degrees(base.nodeo),
        np.degrees(base.argpo),
        np.degrees(base.mo),
        base.bstar,
    )


def test_one_object_carries_the_fit_residual_on_some_events_and_not_others_end_to_end():
    """Their covariance present, the trajectory still CelesTrak's fit: the partial residual path.

    Added at the Step 1 review, because production has not produced this case and might not
    for a while. Measured on the 2026-09-03 demo run **no event took it**: 646 events were
    served by the published states, 16 objects had events both ways, and every unserved event
    on those objects fell past the covariance's own horizon too, so it went to the base model
    with ``supplemental:beyond-horizon`` rather than to ``spacex-ephemeris+sgp4-fit``. The path
    is real -- an ephemeris covers 72 hours while its stored states can stop earlier, and 299
    of 300 real files carry a seam at 47.98 hours whose interior has SpaceX's covariance and
    CelesTrak's trajectory -- but waiting for a run to produce it is not a test.

    So: one Starlink secondary meeting the primary twice an orbit for a day, with states stored
    for the first twelve hours only and covariance stored across the whole twenty-four. The
    chain runs for real -- the screening writes ``secondary_trajectory``,
    ``interpolated_times_from_events`` reads it back, the model decides per event, ``run_risk``
    labels the row -- and the events of the *same object* must come out with two different
    covariances and two different labels.
    """
    from test_screening import PRIMARY_ID, START, ephemeris_table, fleet_of, primary_satrec, snapshot_from

    from driftwatch.ephemeris.spacex import EphemerisTrajectory
    from driftwatch.risk.scenario import objects_from_snapshot, run_risk
    from driftwatch.screening import ScreeningConfig, screen_fleet

    primary = primary_satrec()
    secondary = inclined_copy(primary, NORAD_ID, d_inclination_deg=0.25)
    snapshot = snapshot_from(
        {
            PRIMARY_ID: (primary, "PRIMARY", START - timedelta(hours=6)),
            NORAD_ID: (secondary, "STARLINK-37618", START - timedelta(hours=6)),
        }
    )
    snapshot.loc[snapshot["norad_id"] == NORAD_ID, "category"] = "starlink"
    fleet = fleet_of((PRIMARY_ID, "PRIMARY", True))

    # Twelve hours of published states against a twenty-four hour window, displaced by a known
    # 0.5 km so that the two trajectories are genuinely different objects to screen on.
    trajectory = EphemerisTrajectory(
        ephemeris_table(secondary, NORAD_ID, start=START, hours=12.0, offset_km=np.array([0.0, 0.0, 0.5]))
    )
    result = screen_fleet(
        snapshot, fleet, config=ScreeningConfig(days=1.0, step_s=30.0), start=START, ephemeris=trajectory
    )
    assert set(result.events["secondary_trajectory"]) == {"spacex-ephemeris", "sgp4"}, (
        "the run has to produce both, or the test is checking nothing"
    )

    # Their covariance across the whole window, so every event is inside it whatever served the
    # trajectory. This is exactly the situation the per-event residual exists for.
    covariance = stored_frame(sigma_i_km=0.05, start=START, hours=24.0)
    served = spacex.interpolated_times_from_events(result.events)
    assert set(served) == {NORAD_ID}
    model = spacex.SpacexEphemerisCovariance(EmpiricalCovariance(), covariance, interpolated_times=served)

    objects = objects_from_snapshot([PRIMARY_ID, NORAD_ID], snapshot, fleet)
    risk = run_risk(
        result.events, objects, model, scenario="quiet", run_id="test", snapshot="test.parquet", sweep=False
    )
    counts = risk["cov_source_secondary"].value_counts()
    assert set(counts.index) == {"spacex-ephemeris", "spacex-ephemeris+sgp4-fit"}
    assert counts["spacex-ephemeris"] > 0 and counts["spacex-ephemeris+sgp4-fit"] > 0

    # The label follows the trajectory event by event, not object by object.
    joined = risk[["event_id", "cov_source_secondary"]].merge(
        result.events[["event_id", "tca", "secondary_trajectory"]], on="event_id"
    )
    expected = np.where(
        joined["secondary_trajectory"] == "spacex-ephemeris", "spacex-ephemeris", "spacex-ephemeris+sgp4-fit"
    )
    assert list(joined["cov_source_secondary"]) == list(expected)
    summary = model.fit_rms_summary()
    assert summary["served_with_fit_term"] > 0 and summary["served_without_fit_term"] > 0

    # And the difference is exactly the quadrature term, on the same object, hours apart.
    at = pd.to_datetime(joined["tca"], utc=True).dt.tz_convert(None).to_numpy(dtype="datetime64[us]")
    cov = model.covariance_ric(ObjectRef(NORAD_ID, "starlink", "leo"), START, at)
    interpolated = np.asarray(cov.source) == "spacex-ephemeris"
    sigma_i = np.sqrt(cov.cov_km2[:, 1, 1])
    assert sigma_i[interpolated] == pytest.approx(0.05)
    assert sigma_i[~interpolated] == pytest.approx(np.hypot(0.05, model.fit_rms_share[1] * model.fit_rms_km))
