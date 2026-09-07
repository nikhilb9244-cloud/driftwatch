"""The radio lane: the beam, the angular conversion, the emission table, the horizon arithmetic, the geometry
that puts a satellite on the boresight, and the crossing finder on a constructed pass."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from sgp4.api import Satrec
from synthetic import mean_elements_for_state, omm_record

from driftwatch.catalogue.snapshot import enrich, records_to_frame
from driftwatch.orbit.time import julian_date
from driftwatch.radio import crossings, emissions, horizon, observations, report
from driftwatch.radio import site as site_mod
from driftwatch.radio.site import MEERKAT, RECEIVERS

MU = 398600.8


# --------------------------------------------------------------------------------------
# The beam and the angle


def test_beam_width_is_mauch_at_1500_mhz_and_scales_with_wavelength():
    assert site_mod.beam_fwhm_deg(1500.0) == pytest.approx(57.5 / 60.0)
    assert site_mod.beam_fwhm_deg(750.0) == pytest.approx(2 * 57.5 / 60.0)
    assert site_mod.beam_fwhm_deg(RECEIVERS["L"].centre_mhz) == pytest.approx(1.12, abs=0.01)
    assert 1.10 < site_mod.beam_fwhm_lambda_over_d() < 1.16


def test_angular_error_is_residual_over_range_for_small_angles():
    assert site_mod.angular_error_deg(1.0, 500.0) == pytest.approx(np.degrees(1.0 / 500.0), rel=1e-5)
    assert site_mod.angular_error_deg(-0.5, 500.0) == site_mod.angular_error_deg(0.5, 500.0)


def test_meerkat_site_is_the_published_array_centre():
    assert MEERKAT.latitude_deg == pytest.approx(-30.7111, abs=1e-4)
    assert MEERKAT.longitude_deg == pytest.approx(21.4439, abs=1e-4)
    assert MEERKAT.height_m == 1086.6 and MEERKAT.dish_diameter_m == 13.5


# --------------------------------------------------------------------------------------
# The emission table


def test_declared_in_band_follows_the_receiver_and_the_direction():
    l_band = {e.constellation for e in emissions.declared_in_band(RECEIVERS["L"])}
    assert {"GPS", "GLONASS", "Galileo", "BeiDou", "NavIC", "QZSS", "Iridium", "Inmarsat"} <= l_band
    assert "Globalstar" not in l_band, "Globalstar's L-band service link is an uplink, not an emission"
    assert "OneWeb" not in l_band
    assert emissions.declared_in_band(RECEIVERS["UHF"]) == [], "no declared space-to-Earth range below 1088 MHz"
    s0 = {e.constellation for e in emissions.declared_in_band(RECEIVERS["S0"])}
    assert {"Globalstar", "NavIC", "Starlink"} <= s0


def test_emission_status_names_the_reason():
    assert emissions.emission_status("Globalstar", RECEIVERS["L"])[0] == "uplink only in band"
    assert emissions.emission_status("Starlink", RECEIVERS["UHF"])[0] == "unknown"
    assert emissions.emission_status("Iridium", RECEIVERS["L"])[0] == "declared in-band"
    assert emissions.emission_status("OneWeb", RECEIVERS["L"])[0] == "declared, out of band"
    assert emissions.emission_status(None, RECEIVERS["L"])[0] == "none declared"
    status, detail = emissions.emission_status("Starlink", RECEIVERS["L"])
    assert status == "declared in-band" and "1475-1518" in detail and "not established per object" in detail
    assert "subject to each administration" in detail


def test_constellation_of_reads_names_and_glonass_by_orbit():
    assert emissions.constellation_of("NAVSTAR 81 (USA 319)", "US", "PAY") == "GPS"
    assert emissions.constellation_of("GSAT0101 (GALILEO-PFM)", "ESA", "PAY") == "Galileo"
    assert emissions.constellation_of("GSAT 1", "IND", "PAY") is None, "an Indian communications satellite"
    assert emissions.constellation_of("COSMOS 2545", "CIS", "PAY", 19130.0, 64.8) == "GLONASS"
    assert emissions.constellation_of("COSMOS 2545", "CIS", "PAY", 800.0, 64.8) is None
    assert emissions.constellation_of("IRIDIUM 33 DEB", "US", "DEB") is None
    assert emissions.constellation_of("STARLINK-31000", "US", "PAY") == "Starlink"
    assert emissions.constellation_of("INMARSAT 2-F2 R/B(PAM-D)", "IM", "R/B") is None
    assert emissions.constellation_of("NVS-01", "IND", "PAY") == "NavIC"


def test_the_direct_to_cell_order_is_recorded_verbatim_and_labelled():
    o = emissions.STARLINK_DTC_ORDER
    assert "DA 24-1193" in o["reference"] and "26 November 2024" in o["reference"]
    assert o["paragraph_39"].startswith(
        "In particular, outside the United States, SpaceX is authorized to transmit in the 1475-1518"
    )
    assert "(outside the United States only)" in o["condition_ww"] and "1475-1518 MHz" in o["condition_ww"]
    assert "authorized by the relevant administrations" in o["paragraph_39_administrations"]
    assert o["status"] == "declared; subject to each administration"
    text = "\n".join(emissions.starlink_l_band_record())
    assert "as declared" in text and "South Africa" in text and "not\npredicted" not in text
    assert "is not predicted here" in emissions.STARLINK_L_BAND_NOTE
    row = next(e for e in emissions.EMISSIONS if e.constellation == "Starlink" and e.lo_mhz == 1475.0)
    assert row.status == emissions.DECLARED and row.note.startswith("declared and subject to each administration")
    assert "L" in row.receivers()


def test_every_emission_row_carries_a_source_and_a_status():
    for e in emissions.EMISSIONS:
        assert e.source and e.url.startswith("http")
        assert e.status in (emissions.DECLARED, emissions.UNKNOWN)
        assert e.lo_mhz < e.hi_mhz


# --------------------------------------------------------------------------------------
# The horizon arithmetic


def _trials(cross_km: float, in_track_km: float, altitude_km: float = 500.0, window: str = "quiet") -> pd.DataFrame:
    rows = []
    for lead in (6.0, 12.0, 24.0):
        for k in range(10):
            rows.append(
                {
                    "satellite": "A",
                    "norad_id": 39452,
                    "window": window,
                    "set_epoch": pd.Timestamp("2024-04-20T00:00:00"),
                    "lead_h": lead,
                    "t": pd.Timestamp("2024-04-20T06:00:00"),
                    "radial_km": 0.0,
                    "in_track_km": in_track_km * (1 + 0.01 * k),
                    "cross_km": cross_km * (-1) ** k,
                    "altitude_km": altitude_km,
                    "speed_km_s": 7.6,
                }
            )
    return pd.DataFrame(rows)


def test_horizon_table_fraction_is_one_when_cross_track_is_inside_a_third_of_the_beam():
    t = _trials(cross_km=0.1, in_track_km=1.0)
    table = horizon.horizon_table(t)
    col = horizon.receiver_column(RECEIVERS["L"])
    assert (table[col.crossing_key] == 1.0).all()
    assert horizon.horizon_hours(table, col) == {"quiet": 24.0, "storm": None, "held-out": None}
    assert horizon.crossing_horizon_hours(table, col) == horizon.horizon_hours(table, col, which="crossing")
    # 0.1 km at 500 km is 0.69 arcmin; the table carries the median and p95 in arcmin.
    assert table["cross_median_arcmin"].iloc[0] == pytest.approx(60 * np.degrees(0.1 / 500), rel=1e-3)


def test_horizon_table_fraction_is_zero_when_cross_track_exceeds_a_third_of_the_beam():
    t = _trials(cross_km=5.0, in_track_km=1.0)
    table = horizon.horizon_table(t)
    col = horizon.receiver_column(RECEIVERS["L"])
    assert (table[col.crossing_key] == 0.0).all() and horizon.horizon_hours(table, col)["quiet"] is None
    assert (table[col.position_key] == 1.0).all()
    assert horizon.position_horizon_hours(table, col)["quiet"] == 24.0
    with pytest.raises(ValueError, match="which"):
        horizon.horizon_hours(table, col, which="sideways")


def test_the_two_horizons_are_separate_quantities():
    """A small cross-track error with a large along-track one: the crossing happens, the position is unknown."""
    t = _trials(cross_km=0.1, in_track_km=30.0)  # 30 km at 500 km is 3.4 degrees, beyond a third of every beam
    table = horizon.horizon_table(t)
    col = horizon.receiver_column(RECEIVERS["L"])
    assert horizon.horizon_hours(table, col, which="crossing")["quiet"] == 24.0
    assert horizon.horizon_hours(table, col, which="position")["quiet"] is None
    both = horizon.horizons(table, [col])
    assert both["crossing"][col.key]["quiet"] == 24.0 and both["position"][col.key]["quiet"] is None
    u = horizon.crossing_uncertainty(t, "quiet", 3.0, 500.0, 1.0, 1.0, col.fwhm_deg)
    assert u is not None and u.crossing_fraction_inside == 1.0 and u.position_fraction_inside == 0.0
    payload = horizon.to_json(table, [col])
    assert payload["crossing_horizon_hours"][col.key]["quiet"] == 24.0
    assert payload["position_horizon_hours"][col.key]["quiet"] is None
    assert {"crossing_horizon", "position_horizon"} <= set(payload["definitions"])
    statements = horizon.horizon_statements(table, horizon.table_columns())
    assert any("crossing horizon holds for the full 24 h in every window" in s for s in statements)
    assert any("S-band position prediction from public element sets is not possible" in s for s in statements)
    assert horizon.format_lead(None) == "under 6 h" and horizon.format_lead(168.0) == "7 d"


def test_lead_bin_is_the_smallest_lead_at_or_beyond_the_age():
    leads = [6.0, 12.0, 24.0, 168.0]
    assert horizon.lead_bin_hours(0.5, leads) == 6.0
    assert horizon.lead_bin_hours(6.0, leads) == 6.0
    assert horizon.lead_bin_hours(6.1, leads) == 12.0
    assert horizon.lead_bin_hours(200.0, leads) is None


def test_crossing_uncertainty_projects_the_residual_onto_the_sky():
    t = _trials(cross_km=0.5, in_track_km=2.0)
    across = horizon.crossing_uncertainty(t, "quiet", 3.0, 1000.0, 1.0, 1.0, 1.12)
    along_los = horizon.crossing_uncertainty(t, "quiet", 3.0, 1000.0, 0.0, 0.0, 1.12)
    assert across is not None and along_los is not None
    assert across.lead_h == 6.0 and across.n_trials == 10
    assert across.cross_p95_deg == pytest.approx(np.degrees(0.5 / 1000.0), rel=1e-3)
    assert along_los.cross_p95_deg == 0.0 and along_los.crossing_fraction_inside == 1.0
    six_hours = t[t["lead_h"] == 6.0]
    assert across.along_shift_p95_s == pytest.approx(np.quantile(six_hours["in_track_km"], 0.95) / 7.6, rel=1e-3)
    assert horizon.crossing_uncertainty(t, "storm", 3.0, 1000.0, 1.0, 1.0, 1.12) is None


def test_population_label_states_the_reason():
    assert crossings.population_label(500.0, 0.001, 1.0) == ("measured", crossings.MEASURED_POPULATION)
    assert crossings.population_label(20000.0, 0.001, 1.0)[0] == "no measured horizon"
    assert "outside the 400 to 600 km" in crossings.population_label(800.0, 0.001, 1.0)[1]
    assert "eccentricity" in crossings.population_label(500.0, 0.1, 1.0)[1]
    assert "days old" in crossings.population_label(500.0, 0.001, 9.0)[1]


# --------------------------------------------------------------------------------------
# Geometry


def test_a_position_placed_on_the_boresight_is_seen_on_the_boresight():
    t = datetime(2024, 4, 23, 20, 40, tzinfo=UTC)
    times = np.array([np.datetime64(t.replace(tzinfo=None), "us")])
    alt, az, enu = site_mod.boresight(MEERKAT, 191.507, -9.719, times)
    assert alt[0] > 0
    # Put a point 900 km out along that direction, in the Earth-fixed frame, then send it through TEME and back.
    r_pef = MEERKAT.ecef_km() + 900.0 * (enu[0] @ MEERKAT.enu_basis())
    r_teme = site_mod.pef_to_teme(r_pef[None, :], times)
    back = site_mod.teme_to_pef(r_teme, times)
    look = site_mod.look_from(MEERKAT, back)
    assert site_mod.separation_deg(look.enu[0], enu[0]) < 1e-6
    assert look.range_km[0] == pytest.approx(900.0, abs=1e-6)
    assert look.elevation_deg[0] == pytest.approx(alt[0], abs=1e-6)
    ra, dec = site_mod.sky_from_alt_az(MEERKAT, look.elevation_deg, look.azimuth_deg, times)
    assert ra[0] == pytest.approx(191.507, abs=2e-3) and dec[0] == pytest.approx(-9.719, abs=2e-3)


def test_sky_projection_is_one_across_and_zero_along_the_line_of_sight():
    los = np.array([0.0, 0.0, 1.0])
    assert site_mod.sky_projection(np.array([1.0, 0.0, 0.0]), los) == pytest.approx(1.0)
    assert site_mod.sky_projection(los, los) == pytest.approx(0.0)
    assert site_mod.sky_projection(np.array([0.0, np.sqrt(0.5), np.sqrt(0.5)]), los) == pytest.approx(np.sqrt(0.5))


# --------------------------------------------------------------------------------------
# The crossing finder on a constructed pass


def _state(sat: Satrec, t: datetime) -> tuple[np.ndarray, np.ndarray]:
    jd, fr = julian_date(t)
    err, r, v = sat.sgp4(jd, fr)
    assert err == 0
    return np.array(r), np.array(v)


def _overhead_satrec(t: datetime, *, epoch: datetime | None = None, altitude_km: float = 500.0) -> Satrec:
    """A near-circular polar orbit over the site at ``t``, headed north, with its element set dated ``epoch``."""
    times = np.array([np.datetime64(t.replace(tzinfo=None), "us")])
    up = MEERKAT.ecef_km() / np.linalg.norm(MEERKAT.ecef_km())
    r_pef = (site_mod.EARTH_RADIUS_KM + altitude_km) * up
    north = np.array([0.0, 0.0, 1.0]) - np.dot(np.array([0.0, 0.0, 1.0]), up) * up
    north /= np.linalg.norm(north)
    r_teme = site_mod.pef_to_teme(r_pef[None, :], times)[0]
    v_teme = site_mod.pef_to_teme(north[None, :], times)[0] * np.sqrt(MU / np.linalg.norm(r_teme))
    sat, residual = mean_elements_for_state(r_teme, v_teme, t, 90001)
    assert residual < 0.5
    if epoch is None:
        return sat
    # Re-fit the same orbit at an earlier epoch, so the set carries an age at the crossing.
    earlier, residual = mean_elements_for_state(*_state(sat, epoch), epoch, 90001)
    assert residual < 0.5
    return earlier


def _catalogue_for(sat: Satrec, name: str, epoch: datetime, at: datetime) -> pd.DataFrame:
    df = records_to_frame([omm_record(sat, name, epoch)])
    df["source"] = "test"
    df["groups"] = [[]]
    cat = enrich(df, None, fetched_at=at)
    cat["mean_altitude_km"] = cat["semi_major_axis_km"] - site_mod.EARTH_RADIUS_KM
    cat["constellation"] = None
    cat["constellation"] = cat["constellation"].astype(object)
    return cat


def _pointing_at(sat: Satrec, t: datetime) -> tuple[float, float]:
    """Where SGP4 puts the satellite at ``t``, as J2000 right ascension and declination from the site."""
    times = np.array([np.datetime64(t.replace(tzinfo=None), "us")])
    r, _ = _state(sat, t)
    look = site_mod.look_from(MEERKAT, site_mod.teme_to_pef(r[None, :], times))
    ra, dec = site_mod.sky_from_alt_az(MEERKAT, look.elevation_deg, look.azimuth_deg, times)
    return float(ra[0]), float(dec[0])


def _observation(sat: Satrec, t: datetime, name: str, ra_dec: tuple[float, float] | None = None):
    ra, dec = ra_dec if ra_dec is not None else _pointing_at(sat, t)
    return observations.Observation(
        name, "constructed", ra, dec, t - timedelta(minutes=5), 600.0, RECEIVERS["L"], 1284.0, "test"
    )


def test_beam_crossings_finds_a_satellite_built_to_cross_the_boresight():
    t = datetime(2024, 4, 23, 20, 40, tzinfo=UTC)
    epoch = t - timedelta(hours=3)
    sat = _overhead_satrec(t, epoch=epoch)
    obs = _observation(sat, t, "test-pass")
    cat = _catalogue_for(sat, "TEST OBJECT", epoch, obs.start)
    trials = _trials(cross_km=0.2, in_track_km=1.0)
    found = crossings.beam_crossings(cat, MEERKAT, obs, trials, crossings.PERIODS["quiet-2024-04"])
    assert len(found) == 1
    c = found[0]
    assert c.separation_deg < 0.02
    t_ca = datetime.fromisoformat(c.t_ca_utc.replace("Z", "+00:00"))
    assert abs((t_ca - t).total_seconds()) < 2.0
    assert c.elevation_deg > 80.0 and 480.0 < c.range_km < 520.0
    assert c.population == "measured" and c.crossing_horizon == "inside" and c.position_horizon == "inside"
    assert c.crossing_fraction_inside == 1.0 and c.position_fraction_inside == 1.0
    assert 0.9 < c.projection_cross <= 1.0 and 0.9 < c.projection_along <= 1.0
    assert c.set_age_days == pytest.approx(3.0 / 24.0, abs=1e-3)
    assert c.benchmark_lead_h == 6.0 and c.benchmark_window == "quiet"
    assert c.emission_status == "none declared"
    assert c.samples and all(s.separation_deg <= obs.fwhm_deg / 2 for s in c.samples)
    assert min(s.separation_deg for s in c.samples) < 0.05
    counts = crossings.constellation_view(cat, MEERKAT, obs.start, obs.duration_s, obs.receiver)
    assert counts == [], "an object with no constellation is not in product one"


def test_beam_crossings_reports_nothing_when_the_dish_points_away():
    t = datetime(2024, 4, 23, 20, 40, tzinfo=UTC)
    sat = _overhead_satrec(t)
    obs = _observation(sat, t, "test-away", ra_dec=(10.0, -60.0))
    cat = _catalogue_for(sat, "TEST OBJECT", t, obs.start)
    assert crossings.beam_crossings(cat, MEERKAT, obs, _trials(0.2, 1.0), crossings.PERIODS["quiet-2024-04"]) == []


def test_an_object_outside_the_benchmark_population_carries_no_measured_horizon():
    t = datetime(2024, 4, 23, 20, 40, tzinfo=UTC)
    sat = _overhead_satrec(t, altitude_km=1000.0)
    obs = _observation(sat, t, "test-high")
    cat = _catalogue_for(sat, "HIGH OBJECT", t, obs.start)
    (c,) = crossings.beam_crossings(cat, MEERKAT, obs, _trials(0.2, 1.0), crossings.PERIODS["quiet-2024-04"])
    assert c.population == "no measured horizon" and "outside the 400 to 600 km" in c.population_reason
    assert c.crossing_horizon == "no measured horizon" and c.position_horizon == "no measured horizon"
    assert c.cross_track_uncertainty_deg is None and c.along_track_shift_s is None


# --------------------------------------------------------------------------------------
# Observations and the export


def test_observation_csv_reads_sexagesimal_and_degrees(tmp_path):
    path = tmp_path / "obs.csv"
    path.write_text(
        "observation_id,target,ra,dec,start_utc,duration_s,band,centre_mhz,source,note\n"
        "a,one,12:46:01.67,-09:43:08.8,2024-04-23T20:19:25Z,3743,S4,,GCN 36362,\n"
        "b,two,191.507,-9.719,2024-04-23T20:19:25Z,60,L,1284,a paper,note\n",
        encoding="utf-8",
    )
    got = observations.read_observations(path)
    assert [o.observation_id for o in got] == ["a", "b"]
    assert got[0].ra_deg == pytest.approx(15 * (12 + 46 / 60 + 1.67 / 3600))
    assert got[0].dec_deg == pytest.approx(-(9 + 43 / 60 + 8.8 / 3600))
    assert got[0].centre_mhz == RECEIVERS["S4"].centre_mhz and got[0].duration_s == 3743
    assert got[1].receiver.name == "L" and got[1].centre_mhz == 1284.0
    assert got[0].end - got[0].start == timedelta(seconds=3743)


def test_observation_csv_refuses_a_missing_column(tmp_path):
    path = tmp_path / "obs.csv"
    path.write_text("observation_id,target,ra,dec\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing column"):
        observations.read_observations(path)


def test_satchecker_export_has_the_documented_shape_and_the_two_added_fields():
    t = datetime(2024, 4, 23, 20, 40, tzinfo=UTC)
    epoch = t - timedelta(hours=3)
    sat = _overhead_satrec(t, epoch=epoch)
    obs = _observation(sat, t, "test-pass")
    cat = _catalogue_for(sat, "TEST OBJECT", epoch, obs.start)
    period = crossings.PERIODS["quiet-2024-04"]
    result = crossings.run_observation(cat, None, MEERKAT, obs, _trials(0.2, 1.0), period)
    payload = report.satchecker_export(result, MEERKAT, period, 10.0)
    assert isinstance(payload, list) and set(payload[0]) >= {"data", "source", "version"}
    data = payload[0]["data"]
    assert set(data) == {"satellites", "total_position_results", "total_satellites"}
    assert data["total_satellites"] == 1
    (entry,) = data["satellites"].values()
    assert set(entry) == {"name", "norad_id", "positions"}
    position = entry["positions"][0]
    documented = {"altitude", "angle", "azimuth", "date_time", "dec", "julian_date", "ra", "tle_epoch", "range_km"}
    assert set(position) == documented | set(report.ADDED_FIELDS)
    assert position["crossing_horizon"] == "inside" and position["cross_track_uncertainty_deg"] > 0
    assert position["position_horizon"] == "inside" and position["along_track_shift_s"] > 0
    assert "horizon" not in position, "the single horizon field is gone: the export carries the two named ones"
    assert data["total_position_results"] == len(entry["positions"])


def test_period_report_states_population_products_and_limits():
    period = crossings.PERIODS["storm-2024-05"]
    table = horizon.horizon_table(_trials(0.2, 1.0, window="storm"))
    text = report.period_report(
        period,
        MEERKAT,
        [],
        {"L": pd.DataFrame()},
        {"n_sets": 10, "n_objects": 5, "epoch_min": "2024-05-01T00:00:00", "epoch_max": "2024-05-12T00:00:00"},
        table,
    )
    assert "Population and limits" in text
    assert "No archived observation with a public record" in text
    assert "What this does not show" in text
    assert "received power" in text
