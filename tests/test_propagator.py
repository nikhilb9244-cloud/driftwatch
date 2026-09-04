from datetime import UTC, timedelta

import numpy as np
import pandas as pd
from sgp4.api import Satrec

from driftwatch.catalogue.snapshot import records_to_frame
from driftwatch.orbit.propagator import (
    WGS72_EARTH_RADIUS_KM,
    build_satrecs,
    mean_orbit_geometry,
    propagate_satrecs,
    satrec_from_elements,
)
from driftwatch.orbit.time import datetime64_to_datetime, to_datetime64


def test_omm_initialisation_matches_tle_initialisation(verification_tles, omm_records):
    """Elements that went TLE -> OMM -> our sgp4init must propagate like the TLE itself."""
    by_id = {Satrec.twoline2rv(t.line1, t.line2).satnum: t for t in verification_tles}
    frame = records_to_frame(omm_records)
    ours = build_satrecs(frame)
    worst = 0.0
    for sat_ours, norad in zip(ours, frame["norad_id"], strict=True):
        tle = by_id[int(norad)]
        sat_ref = Satrec.twoline2rv(tle.line1, tle.line2)
        epoch = datetime64_to_datetime(
            np.datetime64(pd.Timestamp(frame.loc[frame["norad_id"] == norad, "epoch"].iloc[0]).tz_convert(None), "us")
        )
        times = to_datetime64([epoch + timedelta(minutes=m) for m in (0, 30, 360, 1440)])
        a = propagate_satrecs([sat_ours], np.array([norad]), times)
        b = propagate_satrecs([sat_ref], np.array([norad]), times)
        ok = (a.error[0] == 0) & (b.error[0] == 0)
        assert (a.error[0] == b.error[0]).all()
        if ok.any():
            worst = max(worst, float(np.max(np.abs(a.r_teme[0][ok] - b.r_teme[0][ok]))))
    # The OMM epoch carries microseconds where a TLE epoch has ~0.9 ms resolution, so the
    # exporter's round trip is exact to well under a metre.
    assert worst < 1e-4


def test_mean_orbit_geometry_is_sensible():
    """An ISS-like element set should show a ~420 km near-circular orbit."""
    from datetime import datetime

    sat = satrec_from_elements(
        norad_id=25544,
        epoch=datetime(2026, 9, 1, tzinfo=UTC),
        mean_motion=15.49,
        eccentricity=0.0005,
        inclination_deg=51.64,
        raan_deg=100.0,
        arg_perigee_deg=90.0,
        mean_anomaly_deg=270.0,
        bstar=2.2e-4,
    )
    geom = mean_orbit_geometry([sat])
    assert 6700 < geom["semi_major_axis_km"][0] < 6820
    assert 380 < geom["perigee_km"][0] < 450
    assert 380 < geom["apogee_km"][0] < 450
    assert abs(sat.radiusearthkm - WGS72_EARTH_RADIUS_KM) < 1e-9


def test_invalid_elements_give_error_code_and_nan():
    from datetime import datetime

    sat = satrec_from_elements(
        norad_id=1,
        epoch=datetime(2026, 9, 1, tzinfo=UTC),
        mean_motion=15.0,
        eccentricity=1.2,  # hyperbolic: not an orbit SGP4 can handle
        inclination_deg=50.0,
        raan_deg=0.0,
        arg_perigee_deg=0.0,
        mean_anomaly_deg=0.0,
        bstar=0.0,
    )
    state = propagate_satrecs([sat], np.array([1]), to_datetime64(["2026-09-01T01:00:00Z"]))
    assert state.error[0, 0] != 0
    assert np.isnan(state.r_teme).all()


def test_a_placeholder_id_past_the_alpha5_range_still_propagates():
    """CelesTrak's supplemental sets carry nine-digit placeholder ids for uncatalogued Starlinks.

    The sgp4 library refuses a satellite number over 339,999 outright, and one such id stopped
    every scheduled supplemental fit on 2026-09-04. The number is identity only, so it is
    initialised as zero and the state is the same as for any other id.
    """
    from datetime import datetime

    elements = dict(
        epoch=datetime(2026, 9, 3, tzinfo=UTC),
        mean_motion=15.05,
        eccentricity=0.0002,
        inclination_deg=53.0,
        raan_deg=10.0,
        arg_perigee_deg=20.0,
        mean_anomaly_deg=30.0,
        bstar=1e-4,
    )
    placeholder = satrec_from_elements(799_501_567, **elements)
    ordinary = satrec_from_elements(64_712, **elements)
    assert placeholder.satnum == 0 and ordinary.satnum == 64_712
    at = to_datetime64(["2026-09-03T06:00:00Z"])
    a = propagate_satrecs([placeholder], np.array([799_501_567]), at)
    b = propagate_satrecs([ordinary], np.array([64_712]), at)
    assert a.error[0, 0] == 0
    np.testing.assert_allclose(a.r_teme, b.r_teme)
