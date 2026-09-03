"""Screening: Stage A rules and label independence, the Stage B no-miss guarantee against
brute force, Stage C precision on synthetic conjunctions, the root finder, the flags and
the ``screen`` command."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from sgp4.api import Satrec, SatrecArray
from synthetic import make_conjunction, omm_record, random_leo, state_at

from driftwatch.catalogue.snapshot import build_snapshot
from driftwatch.fleet import fleet_from_mapping
from driftwatch.orbit.propagator import satrec_from_elements
from driftwatch.orbit.time import julian_date, julian_dates
from driftwatch.screening import EVENT_COLUMNS, ScreeningConfig, ScreeningError, screen_fleet
from driftwatch.screening.stages import (
    STATE_COLUMNS,
    Propagable,
    annotate_events,
    default_start,
    event_ids,
    stage_a,
    stage_b,
    stage_c,
    vector_minimum,
    vector_root,
)

START = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
PRIMARY_ID = 25544
PRIMARY_EPOCH = START - timedelta(hours=6)


def primary_satrec(epoch: datetime = PRIMARY_EPOCH) -> Satrec:
    """An ISS-like primary: 51.6 degrees, about 420 km, slightly eccentric."""
    return satrec_from_elements(PRIMARY_ID, epoch, 15.49, 0.0007, 51.64, 100.0, 90.0, 270.0, 2.2e-4)


def snapshot_from(objects: dict[int, tuple[Satrec, str, datetime]], fetched_at: datetime = START) -> pd.DataFrame:
    records = [omm_record(sat, name, epoch) for sat, name, epoch in objects.values()]
    return build_snapshot({"test": records}, None, fetched_at=fetched_at)


def fleet_of(*members: tuple[int, str, bool]):
    return fleet_from_mapping(
        {
            "schema_version": 1,
            "name": "synthetic",
            "members": [
                {
                    "norad_id": norad_id,
                    "name": name,
                    "hard_body_radius_m": 10.0,
                    "radius_source": "A round number for a synthetic test object.",
                    "manoeuvres": manoeuvres,
                }
                for norad_id, name, manoeuvres in members
            ],
        }
    )


# --------------------------------------------------------------------------------------
# Stage C precision on designed conjunctions


@pytest.mark.parametrize(
    "miss_km, crossing_deg, direction_deg, speed_ratio",
    [
        (3.0, 60.0, 30.0, 1.0),
        (0.5, 90.0, 0.0, 1.003),
        (20.0, 10.0, 90.0, 0.998),
        (24.0, 170.0, 200.0, 1.0),
    ],
)
def test_designed_conjunction_recovered_to_a_second_and_a_metre(miss_km, crossing_deg, direction_deg, speed_ratio):
    primary = primary_satrec()
    t_star = START + timedelta(hours=5, minutes=37, seconds=12, microseconds=500_000)
    secondary, design = make_conjunction(
        primary,
        t_star,
        miss_km=miss_km,
        crossing_angle_deg=crossing_deg,
        miss_direction_deg=direction_deg,
        norad_id=90001,
        speed_ratio=speed_ratio,
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90001: (secondary, "SECONDARY", t_star)})
    result = screen_fleet(snap, fleet_of((PRIMARY_ID, "Primary", True)), config=ScreeningConfig(days=0.5), start=START)
    ev = result.events
    assert list(ev.columns) == list(EVENT_COLUMNS)
    hits = ev[ev["secondary_norad_id"] == 90001]
    assert len(hits) >= 1
    # Equal-speed pairs meet again every orbit; take the designed pass.
    dt = (hits["tca"] - pd.Timestamp(t_star)).dt.total_seconds().abs()
    hit = hits.loc[dt.idxmin()]
    assert abs((hit["tca"] - pd.Timestamp(t_star)).total_seconds()) < 1.0
    assert abs((hit["tca"] - pd.Timestamp(t_star)).total_seconds()) < 0.05, "expected millisecond agreement"
    assert abs(hit["miss_km"] - design["miss_km"]) < 1e-3
    assert abs(hit["rel_speed_kms"] - design["rel_speed_kms"]) < 1e-3
    for comp in ("miss_r_km", "miss_i_km", "miss_c_km"):
        assert abs(hit[comp] - design[comp]) < 1e-3, comp
    assert hit["refine_method"] == "root"
    assert hit["manoeuvre_primary"] == "known" and bool(hit["stale_primary"]) is False
    assert hit["secondary_ephemeris"] == "gp"
    assert result.timings_s["total"] > 0


@pytest.mark.parametrize(
    "miss_km, direction_deg, expect_in_box, expect_within",
    [
        (2.5, 0.0, False, True),  # radial miss beyond the 2 km box half-width, inside the 25 km sphere
        (18.0 * np.sqrt(2.0), 90.0, True, False),  # (0, 18, 18): inside the box, outside the sphere
        (1.0, 45.0, True, True),
    ],
)
def test_box_and_watch_radius_are_judged_separately(miss_km, direction_deg, expect_in_box, expect_within):
    primary = primary_satrec()
    t_star = START + timedelta(hours=2, minutes=3, seconds=4)
    secondary, design = make_conjunction(
        primary, t_star, miss_km=miss_km, crossing_angle_deg=90.0, miss_direction_deg=direction_deg, norad_id=90002
    )
    box = np.array(ScreeningConfig().box_ric_km)
    ric = np.array([design["miss_r_km"], design["miss_i_km"], design["miss_c_km"]])
    assert (np.abs(ric) <= box).all() == expect_in_box and (miss_km <= 25.0) == expect_within
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90002: (secondary, "SECONDARY", t_star)})
    result = screen_fleet(snap, fleet_of((PRIMARY_ID, "Primary", True)), config=ScreeningConfig(days=0.2), start=START)
    hits = result.events[result.events["secondary_norad_id"] == 90002]
    dt = (hits["tca"] - pd.Timestamp(t_star)).dt.total_seconds().abs()
    hit = hits.loc[dt.idxmin()]
    assert bool(hit["in_box"]) is expect_in_box
    assert bool(hit["within_watch_radius"]) is expect_within


# --------------------------------------------------------------------------------------
# Stage B against brute force


def _refine_scalar(sat_p: Satrec, sat_s: Satrec, t_lo: float, t_hi: float) -> tuple[float, float]:
    """Golden-section minimum of the separation, seconds from START, with scalar SGP4 calls only."""
    jd0, fr0 = julian_date(START)

    def d(t: float) -> float:
        _, r1, _ = sat_p.sgp4(jd0, fr0 + t / 86400.0)
        _, r2, _ = sat_s.sgp4(jd0, fr0 + t / 86400.0)
        return float(np.linalg.norm(np.subtract(r2, r1)))

    g = (np.sqrt(5.0) - 1.0) / 2.0
    a, b = t_lo, t_hi
    c, e = b - g * (b - a), a + g * (b - a)
    fc, fe = d(c), d(e)
    for _ in range(60):
        if fc < fe:
            b, e, fe = e, c, fc
            c = b - g * (b - a)
            fc = d(c)
        else:
            a, c, fc = c, e, fe
            e = a + g * (b - a)
            fe = d(e)
    t = c if fc < fe else e
    return t, d(t)


@pytest.fixture(scope="module")
def catalogue():
    """A primary, eight designed conjunctions and forty random LEO objects, with brute-force truth.

    Truth is every local minimum of the separation on a one-second grid over one day,
    refined by a scalar golden section, for every Stage A survivor.
    """
    rng = np.random.default_rng(7)
    primary = primary_satrec()
    objects: dict[int, tuple[Satrec, str, datetime]] = {PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH)}
    designed: dict[int, datetime] = {}
    for k in range(8):
        t_star = START + timedelta(seconds=float(rng.uniform(600.0, 86400.0 - 600.0)))
        sat, _ = make_conjunction(
            primary,
            t_star,
            miss_km=float(rng.uniform(0.1, 30.0)),
            crossing_angle_deg=float(rng.uniform(5.0, 175.0)),
            miss_direction_deg=float(rng.uniform(0.0, 360.0)),
            norad_id=90000 + k,
            speed_ratio=float(rng.uniform(0.99, 1.01)),
        )
        objects[90000 + k] = (sat, f"DESIGNED-{k}", t_star)
        designed[90000 + k] = t_star
    for k in range(40):
        objects[91000 + k] = (random_leo(rng, 91000 + k, START), f"RANDOM-{k}", START)
    snap = snapshot_from(objects)
    config = ScreeningConfig(days=1.0, step_s=30.0)
    a = stage_a(snap, [PRIMARY_ID], config, start=START)
    assert set(designed) <= set(a.secondary_ids.tolist())
    prop = Propagable.from_snapshot(snap, [*a.secondary_ids.tolist(), PRIMARY_ID])

    times = np.datetime64(START.replace(tzinfo=None), "us") + np.arange(0, 86401, dtype=np.int64).astype(
        "timedelta64[s]"
    )
    jd, fr = julian_dates(times)
    err, r, _ = SatrecArray(prop.satrecs).sgp4(jd, fr)
    assert (err == 0).all()
    p_row = prop.row[PRIMARY_ID]
    radius = config.screening_radius_km
    truth = []  # (secondary id, t_true seconds from START, d_true km)
    for sec in a.secondary_ids.tolist():
        row = prop.row[int(sec)]
        d = np.linalg.norm(r[row] - r[p_row], axis=1)
        local = (d[1:-1] <= d[:-2]) & (d[1:-1] < d[2:]) & (d[1:-1] <= radius + 10.0)
        for j in np.nonzero(local)[0] + 1:
            t_true, d_true = _refine_scalar(prop.satrecs[p_row], prop.satrecs[row], float(j - 1), float(j + 1))
            if d_true <= radius:
                truth.append((int(sec), t_true, d_true))
    assert len(truth) >= 8
    found_designed = {
        sec for sec, t, _ in truth if sec in designed and abs(t - (designed[sec] - START).total_seconds()) < 1.0
    }
    assert found_designed == set(designed)
    return {"snapshot": snap, "stage_a": a, "prop": prop, "truth": truth, "radius": radius}


def _misses(candidates: pd.DataFrame, truth: list[tuple[int, float, float]], radius: float) -> list[tuple]:
    """True minima inside ``radius`` that no Stage B bracket contains."""
    start64 = np.datetime64(START.replace(tzinfo=None), "us")
    lo = (candidates["t_lo"].to_numpy(dtype="datetime64[us]") - start64) / np.timedelta64(1, "s")
    hi = (candidates["t_hi"].to_numpy(dtype="datetime64[us]") - start64) / np.timedelta64(1, "s")
    sec = candidates["secondary_norad_id"].to_numpy()
    missed = []
    for s, t, d in truth:
        if d <= radius and not ((sec == s) & (lo <= t) & (t <= hi)).any():
            missed.append((s, t, d))
    return missed


def test_stage_b_brackets_every_brute_force_minimum_and_stage_c_matches_it(catalogue):
    config = ScreeningConfig(days=1.0, step_s=30.0)
    b = stage_b(catalogue["prop"], catalogue["stage_a"], config, start=START)
    assert _misses(b.candidates, catalogue["truth"], catalogue["radius"]) == []
    c = stage_c(catalogue["prop"], b, config, start=START, end=START + timedelta(days=1))
    assert c.n_unconverged == 0
    ev = c.events
    start64 = np.datetime64(START.replace(tzinfo=None), "us")
    t_ev = (ev["tca"].to_numpy(dtype="datetime64[us]") - start64) / np.timedelta64(1, "s")
    for sec, t_true, d_true in catalogue["truth"]:
        if d_true > config.watch_radius_km:
            continue  # may be outside both the sphere and the box; not an event by definition
        mask = (ev["secondary_norad_id"].to_numpy() == sec) & (np.abs(t_ev - t_true) < 0.01)
        assert mask.sum() == 1, (sec, t_true, d_true)
        assert abs(float(ev.loc[mask, "miss_km"].iloc[0]) - d_true) < 1e-3
    # And nothing invented: every event is a true minimum.
    for _, row in ev.iterrows():
        t = (row["tca"].to_datetime64() - start64) / np.timedelta64(1, "s")
        assert any(s == row["secondary_norad_id"] and abs(t - tt) < 0.01 for s, tt, _ in catalogue["truth"])


def test_the_guarantee_holds_at_a_coarser_step_and_fails_without_the_speed_term(catalogue):
    coarse = ScreeningConfig(days=1.0, step_s=120.0)
    b = stage_b(catalogue["prop"], catalogue["stage_a"], coarse, start=START)
    assert _misses(b.candidates, catalogue["truth"], catalogue["radius"]) == []
    # Threshold = R alone (no v_max h / 2 term): fast crossings fall between samples. The
    # speed bound is attached to the pairs by Stage A, so Stage A is rebuilt with the margin at zero.
    naive = ScreeningConfig(days=1.0, step_s=120.0, speed_margin=0.0)
    a_naive = stage_a(catalogue["snapshot"], [PRIMARY_ID], naive, start=START)
    assert (a_naive.pairs["speed_bound_kms"] == 0.0).all()
    b_naive = stage_b(catalogue["prop"], a_naive, naive, start=START)
    missed = _misses(b_naive.candidates, catalogue["truth"], catalogue["radius"])
    assert len(missed) > 0
    assert len(b_naive.candidates) < len(b.candidates)


# --------------------------------------------------------------------------------------
# Stage A


def _geometry_frame(rows: list[tuple[int, float, float, datetime]]) -> pd.DataFrame:
    """A minimal snapshot-like frame: (norad_id, perigee_km, apogee_km, epoch)."""
    ids, peri, apo, epochs = zip(*rows, strict=True)
    peri = np.array(peri, dtype=float)
    apo = np.array(apo, dtype=float)
    return pd.DataFrame(
        {
            "norad_id": np.array(ids, dtype=np.int64),
            "perigee_km": peri,
            "apogee_km": apo,
            "semi_major_axis_km": 6378.135 + 0.5 * (peri + apo),
            "epoch": pd.to_datetime(list(epochs), utc=True),
            "category": "payload",
            "altitude_band": "leo",
        }
    )


def test_stage_a_pad_decay_cut_stale_flag_and_self_exclusion():
    fresh = START - timedelta(days=1)
    frame = _geometry_frame(
        [
            (1, 400.0, 420.0, fresh),  # primary
            (2, 380.0, 440.0, fresh),  # overlaps
            (3, 470.0, 480.0, fresh),  # perigee exactly 50 km above the primary's apogee: kept
            (4, 470.1, 480.0, fresh),  # just beyond the pad: dropped
            (5, 300.0, 350.0, fresh),  # apogee exactly 50 km below the primary's perigee: kept
            (6, 300.0, 349.9, fresh),  # just beyond: dropped
            (7, 100.0, 900.0, fresh),  # overlaps but decaying: dropped and listed
            (8, 410.0, 415.0, START - timedelta(days=6)),  # stale: kept and flagged
            (9, 410.0, 415.0, START - timedelta(days=4)),  # not stale
            (10, 700.0, 710.0, fresh),  # second primary, no overlap with the first
        ]
    )
    a = stage_a(frame, [1, 10], ScreeningConfig(), start=START)
    pairs = a.pairs
    first = pairs.loc[pairs["primary_norad_id"] == 1, "secondary_norad_id"].tolist()
    assert first == [2, 3, 5, 8, 9]  # 10 sits 280 km higher: no overlap
    second = pairs.loc[pairs["primary_norad_id"] == 10, "secondary_norad_id"].tolist()
    assert second == []  # nothing within 50 km of the 700-710 km shell except the primary itself
    assert a.pairs_per_primary == {1: 5, 10: 0}
    assert a.dropped_decaying == [7]
    flags = a.objects.set_index("norad_id")
    assert bool(flags.loc[8, "stale"]) and not bool(flags.loc[9, "stale"]) and not bool(flags.loc[1, "stale"])
    assert flags.loc[8, "epoch_age_days"] == pytest.approx(6.0)
    # The speed bound is the sum of the two perigee speeds with the margin: about 15.6 km/s in LEO.
    bound = pairs.loc[(pairs["primary_norad_id"] == 1) & (pairs["secondary_norad_id"] == 2), "speed_bound_kms"].iloc[0]
    assert 15.3 < bound < 16.2
    with pytest.raises(ScreeningError, match="not in the snapshot"):
        stage_a(frame, [999], ScreeningConfig(), start=START)
    with pytest.raises(ScreeningError, match="below the 120 km cut"):
        stage_a(frame, [7], ScreeningConfig(), start=START)


def test_stage_a_ignores_category_and_band_labels(omm_records):
    snap = build_snapshot({"active": omm_records}, None, fetched_at=START)
    leo = snap[(snap["perigee_km"] > 150) & (snap["apogee_km"] < 2000)]
    primaries = [int(x) for x in leo["norad_id"].iloc[:2]]
    a = stage_a(snap, primaries, ScreeningConfig(), start=START)
    assert len(a.pairs) > 0

    rng = np.random.default_rng(3)
    shuffled = snap.copy()
    shuffled["category"] = rng.permutation(snap["category"].to_numpy())
    shuffled["altitude_band"] = rng.permutation(snap["altitude_band"].to_numpy())
    relabelled = snap.assign(category="unknown", altitude_band="other")
    minimal = snap[["norad_id", "perigee_km", "apogee_km", "semi_major_axis_km", "epoch"]]
    for variant in (shuffled, relabelled, minimal):
        b = stage_a(variant, primaries, ScreeningConfig(), start=START)
        pd.testing.assert_frame_equal(a.pairs, b.pairs)
        assert a.dropped_decaying == b.dropped_decaying
        assert a.objects["stale"].tolist() == b.objects["stale"].tolist()


# --------------------------------------------------------------------------------------
# The root finder and the minimiser


def test_vector_root_converges_superlinearly_and_reports_failures():
    roots = np.array([0.3, 12.5, 59.999, 30.0, 45.0])
    scales = np.array([1.0, 1e3, 1e-2, 5.0, 2.0])
    calls = {"n": 0}

    def f(t, idx):
        calls["n"] += 1
        slope = scales[idx] * (1.0 + 0.3 * np.cos(t))
        out = (t - roots[idx]) * slope
        out = np.where(idx == 4, np.nan, out)  # candidate 4: propagation failure
        return out, slope

    a = np.zeros(5)
    b = np.full(5, 60.0)
    fa, _ = f(a, np.arange(5))
    fb, _ = f(b, np.arange(5))
    fa[4], fb[4] = -1.0, 1.0
    t, ok = vector_root(f, a, b, fa, fb, tol=1e-6)
    assert ok.tolist() == [True, True, True, True, False]
    np.testing.assert_allclose(t[:4], roots[:4], atol=2e-6)
    assert calls["n"] <= 16, f"{calls['n']} evaluations; bisection alone would need 26"
    # An improper bracket (no sign change) is refused rather than guessed at.
    _, ok2 = vector_root(f, np.array([0.0]), np.array([60.0]), np.array([1.0]), np.array([2.0]), tol=1e-6)
    assert not ok2[0]


def test_vector_minimum_finds_each_minimum():
    centres = np.array([0.5, 17.25, 59.0])

    def g(t, idx):
        return (t - centres[idx]) ** 2 + 1.0

    t, ok = vector_minimum(g, np.zeros(3), np.full(3, 60.0), tol=1e-4)
    assert ok.all()
    np.testing.assert_allclose(t, centres, atol=2e-4)


def test_minimisation_fallback_agrees_with_the_root_path():
    """A Stage B 'minimum' candidate (a two-step bracket with no sign change) refines to the same answer."""
    primary = primary_satrec()
    t_star = START + timedelta(minutes=50, seconds=7)
    secondary, design = make_conjunction(
        primary, t_star, miss_km=4.0, crossing_angle_deg=45.0, miss_direction_deg=10.0, norad_id=90003
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90003: (secondary, "SECONDARY", t_star)})
    prop = Propagable.from_snapshot(snap, [PRIMARY_ID, 90003])
    config = ScreeningConfig(days=0.1)
    t64 = np.datetime64(t_star.replace(tzinfo=None), "us")
    for method in ("root", "minimum"):
        candidates = pd.DataFrame(
            {
                "primary_norad_id": [PRIMARY_ID],
                "secondary_norad_id": [90003],
                "t_lo": [t64 - np.timedelta64(30, "s")],
                "t_hi": [t64 + np.timedelta64(30, "s")],
                "d_sample_km": [100.0],
                "method": [method],
            }
        )
        from driftwatch.screening.stages import StageBResult

        c = stage_c(
            prop, StageBResult(candidates, np.array([t64]), 2, 0), config, start=START, end=START + timedelta(days=1)
        )
        assert len(c.events) == 1
        ev = c.events.iloc[0]
        assert ev["refine_method"] == method
        assert abs((pd.Timestamp(ev["tca"]) - pd.Timestamp(t_star.replace(tzinfo=None))).total_seconds()) < 0.01
        assert abs(ev["miss_km"] - design["miss_km"]) < 1e-3


# --------------------------------------------------------------------------------------
# Flags and annotation


def test_annotate_events_sets_names_flags_and_ephemeris():
    rng = np.random.default_rng(0)
    objects = {
        PRIMARY_ID: (primary_satrec(START - timedelta(days=6)), "PRIMARY", START - timedelta(days=6)),
        90010: (random_leo(rng, 90010, START), "STARLINK-90010", START),
        90011: (random_leo(rng, 90011, START - timedelta(days=7)), "OLD DEBRIS", START - timedelta(days=7)),
        90012: (random_leo(rng, 90012, START), "FLEET MATE", START),
    }
    snap = snapshot_from(objects)
    snap["ephemeris"] = ["gp", "supplemental", "gp", "gp"]
    fleet = fleet_of((PRIMARY_ID, "Primary", True), (90012, "Fleet mate", False))
    a = stage_a(snap.assign(perigee_km=400.0, apogee_km=420.0), [PRIMARY_ID, 90012], ScreeningConfig(), start=START)
    geometry = pd.DataFrame(
        {
            "primary_norad_id": [PRIMARY_ID] * 3,
            "secondary_norad_id": [90010, 90011, 90012],
            "tca": np.datetime64(START.replace(tzinfo=None), "us") + np.arange(3) * np.timedelta64(1, "h"),
            "miss_km": [1.0, 2.0, 3.0],
            "rel_speed_kms": [10.0, 11.0, 12.0],
            "miss_r_km": [0.1, 0.2, 0.3],
            "miss_i_km": [0.5, 0.6, 0.7],
            "miss_c_km": [0.8, 0.9, 1.0],
            "in_box": [True, True, False],
            "within_watch_radius": [True, True, True],
            "refine_method": ["root", "root", "minimum"],
            **{name: np.zeros(3) for name in STATE_COLUMNS},
        }
    )
    ev = annotate_events(geometry, snap, fleet, a)
    assert list(ev.columns) == list(EVENT_COLUMNS)
    assert ev["event_id"].tolist() == [
        f"20260901T120000Z:{PRIMARY_ID}:{s}:20260901T{12 + k:02d}00Z" for k, s in enumerate((90010, 90011, 90012))
    ]
    assert ev["primary_name"].tolist() == ["Primary"] * 3
    assert ev["secondary_name"].tolist() == ["STARLINK-90010", "OLD DEBRIS", "FLEET MATE"]
    assert ev["secondary_category"].tolist() == ["starlink", "unknown", "unknown"]
    assert ev["stale_primary"].tolist() == [True] * 3
    assert ev["stale_secondary"].tolist() == [False, True, False]
    assert ev["manoeuvre_primary"].tolist() == ["known"] * 3  # the fleet file says it manoeuvres
    # Starlink by category; an object outside the active group is "none"; a fleet mate takes its own flag.
    assert ev["manoeuvre_secondary"].tolist() == ["known", "none", "none"]
    assert ev["secondary_ephemeris"].tolist() == ["supplemental", "gp", "gp"]
    assert str(ev["tca"].dtype).endswith("UTC]")


def test_screen_fleet_refuses_a_missing_primary():
    snap = snapshot_from({PRIMARY_ID: (primary_satrec(), "PRIMARY", PRIMARY_EPOCH)})
    with pytest.raises(ScreeningError, match="not in the snapshot"):
        screen_fleet(snap, fleet_of((1, "Ghost", False)), config=ScreeningConfig(days=0.1), start=START)


def test_default_start_is_the_fetch_time_to_the_minute():
    snap = snapshot_from(
        {PRIMARY_ID: (primary_satrec(), "PRIMARY", PRIMARY_EPOCH)}, fetched_at=START + timedelta(seconds=41)
    )
    assert default_start(snap) == START


def test_event_ids_are_stable_and_disambiguate_the_same_minute():
    tca = np.array(["2026-09-03T08:57:12.5", "2026-09-03T08:57:40.0", "2026-09-03T08:58:00"], dtype="datetime64[us]")
    ids = event_ids(np.array([1, 1, 1]), np.array([2, 2, 2]), tca, "20260901T204841Z")
    assert ids.tolist() == [
        "20260901T204841Z:1:2:20260903T0857Z",
        "20260901T204841Z:1:2:20260903T0857Z#2",
        "20260901T204841Z:1:2:20260903T0858Z",
    ]
    again = event_ids(np.array([1, 1, 1]), np.array([2, 2, 2]), tca, "20260901T204841Z")
    assert ids.tolist() == again.tolist()


def test_state_at_helper_matches_the_library():
    sat = primary_satrec()
    r, v = state_at(sat, START)
    jd, fr = julian_date(START)
    _, r2, v2 = sat.sgp4(jd, fr)
    np.testing.assert_allclose(r, r2)
    np.testing.assert_allclose(v, v2)


# --------------------------------------------------------------------------------------
# The served trajectory (Phase 4 Step 1)


def ephemeris_table(
    sat: Satrec,
    norad_id: int,
    *,
    start: datetime,
    hours: float,
    offset_km: np.ndarray,
    step_s: float = 120.0,
    segments: int = 1,
) -> pd.DataFrame:
    """A stored state history for ``sat``, displaced by ``offset_km``, in the store's schema.

    A constant displacement is not a Keplerian orbit, but it is a smooth trajectory, which is
    all the interpolant needs -- and it is the cleanest way to make the published states and
    the SGP4 fit disagree by a known amount, which is the situation Step 1 exists for. With
    ``segments=2`` the history is split in the middle, leaving an uncovered gap the way a real
    file's 48-hour seam does.
    """
    end_s = hours * 3600.0
    offsets = [k * step_s for k in range(int(end_s // step_s) + 1)]
    if offsets[-1] < end_s:  # the history ends where it ends, not at the last whole step
        offsets.append(end_s)
    times = np.array([start + timedelta(seconds=o) for o in offsets])
    n = len(times)
    rows = []
    for t in times:
        r, v = state_at(sat, t)
        rows.append((r + offset_km, v))
    half = n // 2
    return pd.DataFrame(
        {
            "norad_id": norad_id,
            "name": f"OBJ-{norad_id}",
            "created": pd.Timestamp(start),
            "ephemeris_start": pd.Timestamp(start),
            "ephemeris_stop": pd.Timestamp(times[-1]),
            "state_frame": "MEME",
            "segment": [0 if (segments == 1 or k < half) else 1 for k in range(n)],
            "t": [np.datetime64(t.replace(tzinfo=None), "us") for t in times],
            "x_km": [r[0] for r, _ in rows],
            "y_km": [r[1] for r, _ in rows],
            "z_km": [r[2] for r, _ in rows],
            "vx_kms": [v[0] for _, v in rows],
            "vy_kms": [v[1] for _, v in rows],
            "vz_kms": [v[2] for _, v in rows],
            "interp_err_median_m": 0.0,
            "interp_err_p99_m": 0.0,
            "interp_err_max_m": 0.0,
            "n_breaks": segments - 1,
        }
    )


def test_screening_on_published_states_finds_an_event_the_element_set_hides():
    """The point of Step 1, as a test: the two trajectories are far enough apart to change the answer.

    The secondary's element set passes the primary at 60 km, well outside the 35.4 km screening
    radius, so on element sets alone there is no event at all. Its published states put it 1 km
    away. That is not a contrived margin -- measured on real files the two trajectories sit a
    median 83 km apart at the far end of the 72-hour horizon -- and it is why Stage B screens on
    the published states rather than screening on one trajectory and refining on another.
    """
    from driftwatch.ephemeris.spacex import EphemerisTrajectory

    primary = primary_satrec()
    t_star = START + timedelta(hours=3, minutes=17, seconds=5)
    secondary, design = make_conjunction(
        primary, t_star, miss_km=60.0, crossing_angle_deg=75.0, miss_direction_deg=30.0, norad_id=90101
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90101: (secondary, "SECONDARY", t_star)})
    fleet = fleet_of((PRIMARY_ID, "Primary", True))
    config = ScreeningConfig(days=0.5)

    # The miss vector is perpendicular to the relative velocity, so shrinking it along its own
    # direction moves the miss without moving the time of closest approach.
    r_p, v_p = state_at(primary, t_star)
    r_s, _v_s = state_at(secondary, t_star)
    delta = r_s - r_p
    offset = -delta * (1.0 - 1.0 / 60.0)

    plain = screen_fleet(snap, fleet, config=config, start=START)
    assert (plain.events["secondary_norad_id"] == 90101).sum() == 0

    trajectory = EphemerisTrajectory(ephemeris_table(secondary, 90101, start=START, hours=12.0, offset_km=offset))
    served = screen_fleet(snap, fleet, config=config, start=START, ephemeris=trajectory)
    hits = served.events[served.events["secondary_norad_id"] == 90101]
    assert len(hits) >= 1
    hit = hits.loc[(hits["tca"] - pd.Timestamp(t_star)).dt.total_seconds().abs().idxmin()]

    assert abs((hit["tca"] - pd.Timestamp(t_star)).total_seconds()) < 1.0
    assert hit["miss_km"] == pytest.approx(1.0, abs=0.01)
    assert hit["secondary_trajectory"] == "spacex-ephemeris"
    assert hit["primary_trajectory"] == "sgp4"
    assert hit["refine_method"] == "root"
    # The stored state is the published one, not the element set's: that is what the risk step
    # will score, and what says the covariance and the trajectory now share a source.
    stored = np.array([hit["s_x_km"], hit["s_y_km"], hit["s_z_km"]])
    # To the interpolation error of the 120-second grid, which is metres, and 59 km from where
    # the element set puts the same object at the same instant.
    assert np.linalg.norm(stored - (r_s + offset)) < 0.02
    assert np.linalg.norm(stored - r_s) == pytest.approx(59.0, abs=0.05)
    assert served.summary()["events_on_published_states"] >= 1


def test_an_approach_at_the_edge_of_the_published_states_is_still_found_and_flagged():
    """Where the served trajectory jumps, the threshold doubles and the interval is scanned.

    The published states stop part way through the window, so the trajectory steps by 59 km at
    that instant. The sampling argument is one-sided there, so Stage B widens its reach to a
    whole step instead of half of one, and Stage C scans rather than root-finding, because a
    discontinuous separation has neither a bracketed root nor a unimodal minimum.
    """
    from driftwatch.ephemeris.spacex import EphemerisTrajectory

    primary = primary_satrec()
    # The published states stop 15 s after a Stage B sample, so the jump falls strictly inside
    # the interval [10800 s, 10830 s], and the encounter is placed inside it on the covered side.
    horizon_s = 3 * 3600 + 15.0
    t_star = START + timedelta(seconds=3 * 3600 + 10.0)
    secondary, _design = make_conjunction(
        primary, t_star, miss_km=60.0, crossing_angle_deg=75.0, miss_direction_deg=30.0, norad_id=90102
    )
    snap = snapshot_from({PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90102: (secondary, "SECONDARY", t_star)})
    r_p, _ = state_at(primary, t_star)
    r_s, _ = state_at(secondary, t_star)
    offset = -(r_s - r_p) * (1.0 - 1.0 / 60.0)

    trajectory = EphemerisTrajectory(
        ephemeris_table(secondary, 90102, start=START, hours=horizon_s / 3600.0, offset_km=offset)
    )
    result = screen_fleet(
        snap,
        fleet_of((PRIMARY_ID, "Primary", True)),
        config=ScreeningConfig(days=0.5),
        start=START,
        ephemeris=trajectory,
    )
    hits = result.events[result.events["secondary_norad_id"] == 90102]
    assert len(hits) >= 1, "an approach at the horizon must not be lost to the jump"
    assert (hits["refine_method"] == "scan").any()
    assert result.stage_c.n_scan >= 1
    assert result.summary()["scanned_across_a_jump"] >= 1


def test_a_break_in_the_stored_history_is_a_gap_the_base_propagator_fills():
    """Between two segments nothing is interpolated, and the element set serves instead."""
    from driftwatch.ephemeris.spacex import EphemerisTrajectory

    primary = primary_satrec()
    trajectory = EphemerisTrajectory(
        ephemeris_table(primary, PRIMARY_ID, start=START, hours=4.0, offset_km=np.zeros(3), segments=2)
    )
    at = np.array(
        [
            np.datetime64((START + timedelta(hours=1)).replace(tzinfo=None), "us"),
            np.datetime64((START + timedelta(hours=1, minutes=58, seconds=30)).replace(tzinfo=None), "us"),
            np.datetime64((START + timedelta(hours=3)).replace(tzinfo=None), "us"),
        ]
    )
    covered = trajectory.covers(PRIMARY_ID, at)
    assert covered[0] and covered[2]
    assert not covered[1], "the gap between two segments is not covered by either"


def _served_separation(primary: Satrec, secondary: Satrec, trajectory, norad_id: int, t_s: np.ndarray) -> np.ndarray:
    """The separation Stage B is supposed to be sampling: SGP4, with the ephemeris where it reaches.

    Built here from the parts rather than from the screening code, so that the test is a check
    on the screening rather than a restatement of it.
    """
    jd0, fr0 = julian_date(START)
    jd = np.full(len(t_s), jd0)
    fr = fr0 + t_s / 86400.0
    _e1, r_p, _v_p = SatrecArray([primary]).sgp4(jd, fr)
    _e2, r_s, _v_s = SatrecArray([secondary]).sgp4(jd, fr)
    r_p, r_s = r_p[0], r_s[0]
    at = np.array(
        [np.datetime64((START + timedelta(seconds=float(t))).replace(tzinfo=None), "us") for t in t_s],
        dtype="datetime64[us]",
    )
    r_e, _v_e, covered = trajectory.states(norad_id, at)
    r_s = np.where(covered[:, None], r_e, r_s)
    return np.linalg.norm(r_s - r_p, axis=1)


def test_stage_b_still_misses_nothing_when_the_trajectory_is_the_published_one():
    """The Phase 2 guarantee, re-run against the trajectory Phase 4 Step 1 actually screens on.

    The published states cover the first two thirds of the window and stop, so the served
    trajectory jumps by several kilometres part way through — which is precisely the case the
    doubled threshold and the scan refinement exist for. Brute force samples the same served
    separation at one second and refines every local minimum; every minimum inside the
    screening radius has to fall inside a Stage B bracket.
    """
    from driftwatch.ephemeris.spacex import EphemerisTrajectory

    primary = primary_satrec()
    config = ScreeningConfig(days=0.25)
    window_s = config.days * 86400.0
    designs = [
        (90201, timedelta(hours=1, minutes=7), 4.0, 40.0),
        (90202, timedelta(hours=3, minutes=41), 12.0, 110.0),
        (90203, timedelta(hours=5, minutes=2), 22.0, 70.0),
    ]
    objects = {PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH)}
    secondaries = {}
    for norad_id, offset, miss_km, crossing in designs:
        t_star = START + offset
        sat, _design = make_conjunction(
            primary, t_star, miss_km=miss_km, crossing_angle_deg=crossing, miss_direction_deg=25.0, norad_id=norad_id
        )
        objects[norad_id] = (sat, f"SEC-{norad_id}", t_star)
        secondaries[norad_id] = sat
    snap = snapshot_from(objects)

    # Published states over the first two thirds of the window, displaced by 6 km, so the
    # served trajectory differs from the element set and then stops differing, abruptly.
    coverage_hours = 2.0 * config.days * 24.0 / 3.0
    tables = [
        ephemeris_table(
            sat,
            norad_id,
            start=START,
            hours=coverage_hours,
            offset_km=np.array([3.0, -4.0, 2.6]),
        )
        for norad_id, sat in secondaries.items()
    ]
    trajectory = EphemerisTrajectory(pd.concat(tables, ignore_index=True))

    result = screen_fleet(
        snap, fleet_of((PRIMARY_ID, "Primary", True)), config=config, start=START, ephemeris=trajectory
    )
    candidates = result.stage_b.candidates
    radius = config.screening_radius_km

    t_grid = np.arange(0.0, window_s + 1.0, 1.0)
    n_checked = 0
    for norad_id, sat in secondaries.items():
        d = _served_separation(primary, sat, trajectory, norad_id, t_grid)
        interior = np.nonzero((d[1:-1] <= d[:-2]) & (d[1:-1] < d[2:]) & (d[1:-1] <= radius))[0] + 1
        brackets = candidates[candidates["secondary_norad_id"] == norad_id]
        lo = (
            brackets["t_lo"].to_numpy(dtype="datetime64[us]") - np.datetime64(START.replace(tzinfo=None), "us")
        ) / np.timedelta64(1, "s")
        hi = (
            brackets["t_hi"].to_numpy(dtype="datetime64[us]") - np.datetime64(START.replace(tzinfo=None), "us")
        ) / np.timedelta64(1, "s")
        for k in interior:
            t_min = t_grid[k]
            n_checked += 1
            # The one-second grid can place the minimum a second either side of the truth, so
            # the bracket has to be allowed that much slack at its ends.
            assert ((lo - 1.0 <= t_min) & (t_min <= hi + 1.0)).any(), (
                f"secondary {norad_id}: a minimum of {d[k]:.3f} km at t={t_min:.0f} s is in no Stage B bracket"
            )
    assert n_checked >= len(designs), "the brute force found nothing to check"
    # And the jump was seen: the served trajectory stops part way through the window.
    assert result.stage_b.served is not None and len(result.stage_b.served.rows) == len(secondaries)
    assert result.stage_b.served.summary()["jump_intervals"] >= len(secondaries)


def test_stage_a_widens_a_shell_to_what_the_published_states_actually_reach():
    """The shell test has to bound the trajectory the later stages screen on, not a different one.

    Measured over 300 Starlink files on 2026-09-03, the published trajectory leaves the
    mean-element shell by a median 7.6 km and by up to 32.6 km for a satellite raising its
    orbit, against 14.6 km of pad left over the 35.4 km screening radius. So the excursion is
    not something the pad absorbs, and Stage A takes the union of the two ranges instead of
    assuming it fits.
    """
    primary = primary_satrec()  # about 420 km
    # A secondary whose mean shell sits far enough above the primary's to be dropped: at
    # 14.05 rev/day it is near 780 km, and the pad is 50 km.
    secondary = satrec_from_elements(90301, PRIMARY_EPOCH, 14.35, 0.0005, 53.0, 120.0, 90.0, 200.0, 1e-4)
    snap = snapshot_from(
        {PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH), 90301: (secondary, "SECONDARY", PRIMARY_EPOCH)}
    )
    config = ScreeningConfig(days=0.5)
    row = snap.loc[snap["norad_id"] == 90301].iloc[0]
    primary_row = snap.loc[snap["norad_id"] == PRIMARY_ID].iloc[0]
    gap = float(row["perigee_km"]) - float(primary_row["apogee_km"])
    assert gap > config.pad_km, "the test needs a pair the mean-element shells drop"

    plain = stage_a(snap, [PRIMARY_ID], config, start=START)
    assert 90301 not in set(plain.pairs["secondary_norad_id"])
    mean_speed = float(plain.objects.loc[plain.objects["norad_id"] == 90301, "v_perigee_kms"].iloc[0])

    # Published states that dip to within the pad of the primary's apogee: now it must survive.
    low = float(primary_row["apogee_km"]) + 0.5 * config.pad_km
    widened = stage_a(snap, [PRIMARY_ID], config, start=START, reach={90301: (low, float(row["apogee_km"]), 7.0)})
    assert 90301 in set(widened.pairs["secondary_norad_id"])

    # The speed bound is the larger of the two: 7.0 km/s from the states is slower than the
    # element set's own perigee speed here, so the element set's wins and nothing is loosened.
    assert 7.0 < mean_speed
    assert widened.objects.loc[widened.objects["norad_id"] == 90301, "v_perigee_kms"].iloc[0] == pytest.approx(
        mean_speed
    )
    # And a faster published state raises it, because the bound has to hold on what is screened.
    faster = stage_a(
        snap, [PRIMARY_ID], config, start=START, reach={90301: (low, float(row["apogee_km"]), mean_speed + 1.0)}
    )
    assert faster.objects.loc[faster.objects["norad_id"] == 90301, "v_perigee_kms"].iloc[0] == pytest.approx(
        mean_speed + 1.0
    )

    # And it only ever widens: a shell inside the element set's changes nothing.
    narrow = stage_a(
        snap,
        [PRIMARY_ID],
        config,
        start=START,
        reach={90301: (float(row["perigee_km"]) + 10.0, float(row["apogee_km"]) - 10.0, 1.0)},
    )
    assert list(narrow.pairs["secondary_norad_id"]) == list(plain.pairs["secondary_norad_id"])


def test_the_trajectory_reports_the_shell_its_states_reach():
    from driftwatch.ephemeris.spacex import EphemerisTrajectory
    from driftwatch.orbit.propagator import WGS72_EARTH_RADIUS_KM

    primary = primary_satrec()
    table = ephemeris_table(primary, PRIMARY_ID, start=START, hours=3.0, offset_km=np.zeros(3))
    reach = EphemerisTrajectory(table).reach()
    assert set(reach) == {PRIMARY_ID}
    low, high, fastest = reach[PRIMARY_ID]
    radii = np.linalg.norm(table[["x_km", "y_km", "z_km"]].to_numpy(), axis=1) - WGS72_EARTH_RADIUS_KM
    speeds = np.linalg.norm(table[["vx_kms", "vy_kms", "vz_kms"]].to_numpy(), axis=1)
    assert low == pytest.approx(radii.min())
    assert high == pytest.approx(radii.max())
    assert fastest == pytest.approx(speeds.max())
    assert high > low


# --------------------------------------------------------------------------------------
# Attached and co-orbiting objects


def docked_satrec(primary: Satrec, norad_id: int, *, along_track_km: float, epoch: datetime = PRIMARY_EPOCH) -> Satrec:
    """A second catalogue object holding station a fixed distance along track from the primary.

    What a docked visiting vehicle looks like in the catalogue: the same orbit to every
    significant figure, offset by a fraction of the along-track spacing that separate element
    sets for the same physical stack disagree by. The mean motion is copied exactly, so the
    offset neither grows nor closes -- which is the whole point.
    """
    r, _ = state_at(primary, epoch)
    radius_km = float(np.linalg.norm(r))
    d_mean_anomaly_deg = np.degrees(along_track_km / radius_km)
    return satrec_from_elements(
        norad_id,
        epoch,
        primary.no_kozai * 1440.0 / (2.0 * np.pi),
        primary.ecco,
        np.degrees(primary.inclo),
        np.degrees(primary.nodeo),
        np.degrees(primary.argpo),
        np.degrees(primary.mo) + d_mean_anomaly_deg,
        primary.bstar,
    )


def test_a_docked_object_is_excluded_structurally_and_a_real_conjunction_is_not():
    """The filter takes out the pair that never comes apart and leaves everything else alone.

    Three secondaries: one holding station 200 m along track (a docked vehicle), one making a
    designed fast conjunction, and one making a designed *slow* one at a 3 degree crossing.
    The slow encounter is the discrimination that matters. A rule on relative speed would take
    it out along with the docked object; the rule on sustained separation must not, because the
    slow encounters are the events `docs/methods.md` records as the largest error this project
    cannot size, and hiding them would be the worst possible way to tidy the table.
    """
    primary = primary_satrec()
    t_star = START + timedelta(hours=30)
    fast, _ = make_conjunction(
        primary, t_star, miss_km=1.5, crossing_angle_deg=70.0, miss_direction_deg=20.0, norad_id=90001
    )
    slow, slow_design = make_conjunction(
        primary,
        t_star + timedelta(hours=12),
        miss_km=2.0,
        crossing_angle_deg=3.0,
        miss_direction_deg=0.0,
        norad_id=90002,
    )
    docked = docked_satrec(primary, 90003, along_track_km=0.2)
    objects = {
        PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH),
        90001: (fast, "FAST", t_star),
        90002: (slow, "SLOW", t_star + timedelta(hours=12)),
        90003: (docked, "DOCKED VEHICLE", PRIMARY_EPOCH),
    }
    snapshot = snapshot_from(objects)
    fleet = fleet_of((PRIMARY_ID, "PRIMARY", True))
    config = ScreeningConfig(days=3.0, step_s=60.0)

    result = screen_fleet(snapshot, fleet, config=config, start=START)
    attached = result.stage_b.attached
    assert list(attached["secondary_norad_id"]) == [90003]
    row = attached.iloc[0]
    # It never comes apart, and the numbers the report quotes say so.
    assert row["d_max_km"] < config.attached_km
    assert row["fraction_below"] == 1.0
    assert row["d_min_km"] == pytest.approx(0.2, abs=0.05)
    assert result.stage_b.n_attached_candidates > 0
    assert set(result.events["secondary_norad_id"]) == {90001, 90002}
    # The slow encounter survives -- it approaches more than once, being nearly co-orbital --
    # and it really is slow: a twentieth of the fast one's relative speed.
    kept_slow = result.events[result.events["secondary_norad_id"] == 90002]
    designed = kept_slow.loc[kept_slow["miss_km"].idxmin()]
    assert float(designed["miss_km"]) == pytest.approx(slow_design["miss_km"], abs=0.02)
    assert float(designed["rel_speed_kms"]) == pytest.approx(slow_design["rel_speed_kms"], rel=0.02)
    assert slow_design["rel_speed_kms"] < 0.5

    summary = result.summary()
    assert summary["attached_pairs_excluded"] == 1
    assert summary["attached_candidates_dropped"] == result.stage_b.n_attached_candidates


def test_keep_attached_restores_the_docked_events_unchanged():
    """The exclusion is reversible by a flag, and reversing it changes nothing else.

    The events of every other pair have to be bit-for-bit what they were: the filter drops
    candidates and must not perturb the refinement of the ones it keeps.
    """
    primary = primary_satrec()
    t_star = START + timedelta(hours=30)
    fast, _ = make_conjunction(
        primary, t_star, miss_km=1.5, crossing_angle_deg=70.0, miss_direction_deg=20.0, norad_id=90001
    )
    docked = docked_satrec(primary, 90003, along_track_km=0.2)
    snapshot = snapshot_from(
        {
            PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH),
            90001: (fast, "FAST", t_star),
            90003: (docked, "DOCKED VEHICLE", PRIMARY_EPOCH),
        }
    )
    fleet = fleet_of((PRIMARY_ID, "PRIMARY", True))

    filtered = screen_fleet(snapshot, fleet, config=ScreeningConfig(days=3.0, step_s=60.0), start=START)
    kept = screen_fleet(
        snapshot,
        fleet,
        config=ScreeningConfig(days=3.0, step_s=60.0, exclude_attached=False),
        start=START,
    )
    assert not len(kept.stage_b.attached)
    assert kept.stage_b.n_attached_candidates == 0
    assert kept.summary()["attached_pairs_excluded"] == 0

    docked_events = kept.events[kept.events["secondary_norad_id"] == 90003]
    assert len(docked_events) > 10  # about one an orbit over three days
    assert float(docked_events["miss_km"].max()) < 1.0
    assert len(kept.events) == len(filtered.events) + len(docked_events)

    columns = ["secondary_norad_id", "tca", "miss_km", "rel_speed_kms"]
    other = kept.events[kept.events["secondary_norad_id"] != 90003].reset_index(drop=True)
    pd.testing.assert_frame_equal(other[columns], filtered.events[columns].reset_index(drop=True))


def test_a_pair_that_comes_apart_for_part_of_the_window_is_kept():
    """The rule is sustained separation, not the closest approach: one tight pass is not attachment.

    A designed conjunction whose miss is a hundred metres -- closer than the docked vehicle
    ever is -- must survive, because the two objects are a thousand kilometres apart for the
    rest of the window. Nothing here keys on how small the miss gets.
    """
    primary = primary_satrec()
    close, _ = make_conjunction(
        primary,
        START + timedelta(hours=20),
        miss_km=0.1,
        crossing_angle_deg=45.0,
        miss_direction_deg=0.0,
        norad_id=90004,
    )
    snapshot = snapshot_from(
        {
            PRIMARY_ID: (primary, "PRIMARY", PRIMARY_EPOCH),
            90004: (close, "VERY CLOSE PASS", START + timedelta(hours=20)),
        }
    )
    result = screen_fleet(
        snapshot, fleet_of((PRIMARY_ID, "PRIMARY", True)), config=ScreeningConfig(days=2.0, step_s=60.0), start=START
    )
    assert not len(result.stage_b.attached)
    assert float(result.events["miss_km"].min()) == pytest.approx(0.1, abs=0.01)
