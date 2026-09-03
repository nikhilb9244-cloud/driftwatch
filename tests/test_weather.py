"""Space weather ingestion: the file formats, the index conversions and the layering.

Nothing here touches the network. The feeds are small and their formats are fixed, so the
tests read synthetic copies of each; what they are really checking is the part that is easy
to get quietly wrong — Kp arriving in three different encodings, the Bartels ap table, which
source wins where, and that a gap stays a gap instead of becoming a quiet day.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from driftwatch import config
from driftwatch.weather import celestrak_sw as csw
from driftwatch.weather import helioviewer, swpc
from driftwatch.weather import table as wt

T0 = datetime(2026, 9, 1, tzinfo=UTC)


# --------------------------------------------------------------------------------------
# The indices themselves


def test_kp_and_ap_convert_by_the_bartels_table_in_both_directions():
    """Kp is an index on a quasi-logarithmic scale; ap is the amplitude it stands for.

    Averaging Kp is meaningless and averaging ap is not, which is why the density model wants
    ap and why the conversion has to be the published table rather than a formula.
    """
    # The anchors everyone quotes: quiet, the G1 threshold, and the top of the scale.
    assert wt.kp_to_ap(np.array([0.0]))[0] == 0
    assert wt.kp_to_ap(np.array([4.0]))[0] == 27
    assert wt.kp_to_ap(np.array([5.0]))[0] == 48  # G1
    assert wt.kp_to_ap(np.array([7.0]))[0] == 132  # G3
    assert wt.kp_to_ap(np.array([9.0]))[0] == 400  # the Gannon storm's peak three hours
    # Every tabulated step round-trips.
    np.testing.assert_allclose(wt.ap_to_kp(wt.kp_to_ap(wt.KP_STEPS)), wt.KP_STEPS, atol=1e-9)
    # It is not a linear scale: two units of Kp is a factor of five in ap, not a doubling.
    assert wt.kp_to_ap(np.array([7.0]))[0] / wt.kp_to_ap(np.array([5.0]))[0] == pytest.approx(2.75)
    assert np.isnan(wt.kp_to_ap(np.array([np.nan]))[0])
    assert np.isnan(wt.ap_to_kp(np.array([np.nan]))[0])


def test_kp_snaps_to_thirds_whichever_encoding_it_arrives_in():
    """CelesTrak sends ten times the value, SWPC sends two decimals, the index has 28 steps."""
    np.testing.assert_allclose(csw._to_kp(np.array([0, 7, 13, 43, 90])), [0.0, 2 / 3, 4 / 3, 13 / 3, 9.0], atol=1e-9)
    np.testing.assert_allclose(wt.snap_kp(np.array([0.33, 0.67, 2.33, 8.67])), [1 / 3, 2 / 3, 7 / 3, 26 / 3], atol=1e-9)


# --------------------------------------------------------------------------------------
# CelesTrak's SW-All.csv


SW_HEADER = (
    "DATE,BSRN,ND,KP1,KP2,KP3,KP4,KP5,KP6,KP7,KP8,KP_SUM,AP1,AP2,AP3,AP4,AP5,AP6,AP7,AP8,AP_AVG,CP,C9,ISN,"
    "F10.7_OBS,F10.7_ADJ,F10.7_DATA_TYPE,F10.7_OBS_CENTER81,F10.7_OBS_LAST81,F10.7_ADJ_CENTER81,F10.7_ADJ_LAST81"
)


def sw_row(date: str, kp10: list[int] | None, ap: list[int] | None, f107: float, data_type: str) -> str:
    kp_s = ",".join(str(k) for k in kp10) if kp10 else ",,,,,,,,"[:15]
    ap_s = ",".join(str(a) for a in ap) if ap else ",,,,,,,,"[:15]
    kp_sum = sum(kp10) if kp10 else ""
    ap_avg = round(sum(ap) / len(ap)) if ap else ""
    return (
        f"{date},2600,10,{kp_s},{kp_sum},{ap_s},{ap_avg},0.5,3,50,"
        f"{f107},{f107 + 1.5},{data_type},{f107 - 5},{f107 - 6},{f107 - 3},{f107 - 4}"
    )


def sw_csv(tmp_path):
    lines = [
        SW_HEADER,
        sw_row("2026-08-31", [7, 7, 13, 13, 20, 20, 27, 27], [3, 3, 5, 5, 7, 7, 12, 12], 100.0, "OBS"),
        sw_row("2026-09-01", [13, 13, 13, 13, 13, 13, 13, 13], [5, 5, 5, 5, 5, 5, 5, 5], 101.0, "OBS"),
        sw_row("2026-09-02", [17, 17, 17, 17, 17, 17, 17, 17], [6, 6, 6, 6, 6, 6, 6, 6], 102.0, "PRD"),
    ]
    path = tmp_path / "SW-All.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_sw_all_becomes_eight_intervals_a_day_with_the_right_times_and_provenance(tmp_path):
    rows = csw.load_sw_all(sw_csv(tmp_path))
    assert len(rows) == 24
    day = rows[rows["t"].dt.date == datetime(2026, 8, 31).date()]
    assert list(day["t"].dt.hour) == [0, 3, 6, 9, 12, 15, 18, 21]
    # 7, 13, 20 and 27 in the file are Kp 0+, 1+, 2 and 2+, which are 2/3, 4/3, 2 and 8/3.
    np.testing.assert_allclose(day["kp"].to_numpy(), [2 / 3, 2 / 3, 4 / 3, 4 / 3, 2.0, 2.0, 8 / 3, 8 / 3], atol=1e-9)
    np.testing.assert_allclose(day["ap"].to_numpy(), [3, 3, 5, 5, 7, 7, 12, 12])
    # The day's own average, and the flux repeated across its eight rows.
    assert set(day["ap_daily"]) == {round(sum([3, 3, 5, 5, 7, 7, 12, 12]) / 8)}
    assert set(day["f107_obs"]) == {100.0}
    # A predicted day is a forecast even though the file looks identical.
    assert set(rows[rows["data_type"] == "OBS"]["provenance"]) == {"observed"}
    assert set(rows[rows["data_type"] == "PRD"]["provenance"]) == {"forecast"}


def test_a_file_that_is_not_sw_all_is_refused(tmp_path):
    path = tmp_path / "wrong.csv"
    path.write_text("DATE,SOMETHING\n2026-09-01,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SW-All"):
        csw.load_sw_all(path)


# --------------------------------------------------------------------------------------
# SWPC


def test_the_issue_time_is_read_from_the_product_where_it_has_one():
    text = ":Product: 27-day Space Weather Outlook Table 27DO.txt\n:Issued: 2026 Aug 31 0155 UTC\n#\n"
    assert swpc.parse_issued(text) == datetime(2026, 8, 31, 1, 55, tzinfo=UTC)
    assert swpc.parse_issued("no issue line here") is None


def test_the_kp_forecast_keeps_the_observed_estimated_predicted_distinction():
    text = json.dumps(
        [
            {"time_tag": "2026-09-01T00:00:00", "kp": 1.33, "observed": "observed", "noaa_scale": None},
            {"time_tag": "2026-09-01T03:00:00", "kp": 2.33, "observed": "estimated", "noaa_scale": None},
            {"time_tag": "2026-09-01T06:00:00", "kp": 5.67, "observed": "predicted", "noaa_scale": "G2"},
        ]
    )
    frame = swpc.parse_kp_forecast(text)
    assert list(frame["observed"]) == ["observed", "estimated", "predicted"]
    assert frame["t"].dt.tz is not None
    assert frame["kp"].iloc[2] == pytest.approx(5.67)


def test_the_27_day_outlook_is_read_from_its_fixed_width_table():
    text = (
        ":Issued: 2026 Aug 31 0155 UTC\n"
        "#   UTC      Radio Flux   Planetary   Largest\n"
        "#  Date       10.7 cm      A Index    Kp Index\n"
        "2026 Aug 31     110          12          3\n"
        "2026 Sep 01     105           5          2\n"
    )
    frame = swpc.parse_27day_outlook(text)
    assert len(frame) == 2
    assert list(frame["f107"]) == [110.0, 105.0]
    assert list(frame["ap"]) == [12.0, 5.0]
    assert list(frame["kp_max"]) == [3.0, 2.0]
    assert frame["date"].iloc[0] == pd.Timestamp("2026-08-31", tz="UTC")


def test_the_solar_wind_arrives_as_an_array_of_arrays_with_its_header_in_the_first_row():
    text = json.dumps(
        [
            ["time_tag", "speed", "density", "temperature", "bx", "by", "bz", "bt", "vx", "vy", "vz", "propagated"],
            ["2026-09-01T00:00:00Z", 367.9, 4.86, 70103.0, 2.95, -3.72, 1.91, 5.23, -365.9, -17.1, -35.1, "x"],
            ["2026-09-01T00:01:00Z", 370.0, 5.0, 71000.0, 3.0, -3.0, -8.0, 9.0, -369.0, -17.0, -35.0, "x"],
        ]
    )
    frame = swpc.parse_solar_wind(text)
    assert list(frame.columns) == list(swpc.SOLAR_WIND_COLUMNS)
    assert frame["speed_kms"].iloc[0] == pytest.approx(367.9)
    summary = swpc.solar_wind_summary(frame)
    # Southward Bz is what couples the wind into the magnetosphere, so the minimum is reported.
    assert summary["bz_nt_min"] == pytest.approx(-8.0)
    assert summary["speed_kms"]["max"] == pytest.approx(370.0)


def solar_wind_file(directory, issued: str, start: datetime, minutes: int, bz) -> None:
    """One stored minute-cadence version, with its sidecar, as `fetch_product` writes it."""
    header = ["time_tag", "speed", "density", "temperature", "bx", "by", "bz", "bt"]
    rows = [
        [(start + timedelta(minutes=m)).strftime("%Y-%m-%dT%H:%M:%SZ"), 400.0 + m, 5.0, 7e4, 1.0, 1.0, bz(m), 5.0]
        for m in range(minutes)
    ]
    path = directory / f"solar-wind_{issued}.json"
    path.write_text(json.dumps([header, *rows]), encoding="utf-8")
    stamp = f"{issued[:4]}-{issued[4:6]}-{issued[6:8]}T{issued[9:11]}:{issued[11:13]}:00+00:00"
    (directory / f"solar-wind_{issued}.json.meta.json").write_text(
        json.dumps({"product": "solar-wind", "issued_at": stamp}), encoding="utf-8"
    )


def test_solar_wind_older_than_a_week_is_rolled_to_hourly_means_keeping_the_extremes(tmp_path):
    """The feed repeats a week of minutes on every fetch, so the store would grow for nothing.

    What must survive the roll is the shape of a storm. An hourly *mean* of Bz averages away
    exactly the southward excursions that drive one, so the archive keeps the minimum and the
    maximum beside the mean.
    """
    directory = tmp_path / "swpc"
    directory.mkdir(parents=True)
    now = datetime(2026, 9, 20, tzinfo=UTC)
    # One version from a fortnight ago (rolled) and one from yesterday (kept at one minute).
    solar_wind_file(directory, "20260906T000000Z", datetime(2026, 9, 5, 22, tzinfo=UTC), 120, lambda m: -20.0 + m / 3)
    solar_wind_file(directory, "20260919T000000Z", datetime(2026, 9, 18, 22, tzinfo=UTC), 120, lambda m: 1.0)

    rolled = swpc.roll_solar_wind(out_dir=tmp_path, now=now, keep_days=7)
    assert rolled["n_rolled"] == 1 and rolled["kilobytes_freed"] > 0
    assert not (directory / "solar-wind_20260906T000000Z.json").exists()
    assert not (directory / "solar-wind_20260906T000000Z.json.meta.json").exists()
    assert (directory / "solar-wind_20260919T000000Z.json").exists()  # inside the week, untouched

    archive = swpc.load_solar_wind_archive(tmp_path)
    assert list(archive["n"]) == [60, 60]
    assert archive["speed_kms"].iloc[0] == pytest.approx(400.0 + 29.5)
    assert archive["speed_kms_max"].iloc[0] == pytest.approx(459.0)
    # The first hour swings from -20 to -0.3 nT: the mean hides how southward it went.
    assert archive["bz_nt"].iloc[0] == pytest.approx(-20.0 + 29.5 / 3)
    assert archive["bz_nt_min"].iloc[0] == pytest.approx(-20.0)
    assert archive["bz_nt_max"].iloc[0] == pytest.approx(-20.0 + 59 / 3)
    # The rolled file is recorded rather than silently dropped.
    meta = json.loads((directory / "solar-wind-hourly.parquet.meta.json").read_text(encoding="utf-8"))
    assert [r["file"] for r in meta["rolled"]] == ["solar-wind_20260906T000000Z.json"]

    # Rolling again is a no-op, and an overlapping version does not duplicate an hour.
    assert swpc.roll_solar_wind(out_dir=tmp_path, now=now, keep_days=7)["n_rolled"] == 0
    solar_wind_file(directory, "20260907T000000Z", datetime(2026, 9, 5, 22, tzinfo=UTC), 30, lambda m: 1.0)
    swpc.roll_solar_wind(out_dir=tmp_path, now=now, keep_days=7)
    again = swpc.load_solar_wind_archive(tmp_path)
    assert len(again) == 2 and again["t"].is_unique
    # The hour built from more minutes is the better summary of it, so the 60-minute row stays.
    assert again["n"].iloc[0] == 60


def test_a_stored_version_is_chosen_by_the_time_it_was_issued_not_by_the_time_it_was_fetched(tmp_path):
    """Rescoring a run made last Tuesday has to use last Tuesday's forecast."""
    directory = tmp_path / "swpc"
    directory.mkdir(parents=True)
    for issued in ("20260901T000000Z", "20260902T000000Z", "20260903T000000Z"):
        path = directory / f"kp-forecast_{issued}.json"
        path.write_text("[]", encoding="utf-8")
        path.with_suffix(".json.meta.json").write_text(
            json.dumps({"issued_at": f"{issued[:4]}-{issued[4:6]}-{issued[6:8]}T00:00:00+00:00"}), encoding="utf-8"
        )
    assert len(swpc.list_versions("kp-forecast", tmp_path)) == 3  # and not the sidecars
    chosen = swpc.stored_before("kp-forecast", datetime(2026, 9, 2, 12, tzinfo=UTC), tmp_path)
    assert chosen is not None and chosen.name == "kp-forecast_20260902T000000Z.json"
    assert swpc.stored_before("kp-forecast", datetime(2026, 8, 1, tzinfo=UTC), tmp_path) is None


# --------------------------------------------------------------------------------------
# The table


def celestrak_rows(days: list[tuple[str, float, str]]) -> pd.DataFrame:
    """Eight intervals a day at a constant Kp, with the given provenance."""
    frames = []
    for date, kp, data_type in days:
        t = pd.date_range(pd.Timestamp(date, tz="UTC"), periods=8, freq="3h")
        frames.append(
            pd.DataFrame(
                {
                    "t": t,
                    "kp": kp,
                    "ap": wt.kp_to_ap(np.full(8, kp)),
                    "ap_daily": wt.kp_to_ap(np.array([kp]))[0],
                    "f107_obs": 100.0,
                    "f107_adj": 101.0,
                    "f107_obs_81": 110.0,
                    "f107_adj_81": 111.0,
                    "data_type": data_type,
                    "provenance": csw.DATA_TYPES[data_type],
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_the_table_layers_observation_over_forecast_and_says_which_it_used():
    """Three days: one observed, one where SWPC has the measurement and CelesTrak only a guess, one forecast."""
    celestrak = celestrak_rows([("2026-09-01", 2.0, "OBS"), ("2026-09-02", 1.0, "PRD"), ("2026-09-03", 1.0, "PRD")])
    forecast = pd.DataFrame(
        {
            "t": pd.date_range(pd.Timestamp("2026-09-02", tz="UTC"), periods=16, freq="3h"),
            "kp": [4.0] * 8 + [6.0] * 8,
            "observed": ["observed"] * 4 + ["estimated"] * 4 + ["predicted"] * 8,
            "noaa_scale": None,
        }
    )
    issued = datetime(2026, 9, 2, 12, 30, tzinfo=UTC)
    table = wt.build(
        datetime(2026, 9, 1, tzinfo=UTC),
        datetime(2026, 9, 3, 21, tzinfo=UTC),
        celestrak_rows=celestrak,
        kp_forecast=(forecast, issued),
    )
    assert len(table) == 24
    by_source = table.groupby("source", observed=True)["t"].size().to_dict()
    assert by_source == {
        "celestrak:observed": 8,
        "swpc:kp-observed": 4,
        "swpc:kp-estimated": 4,
        "swpc:kp-forecast": 8,
    }
    # CelesTrak's own prediction for 2 September never gets used: SWPC has the real thing.
    assert set(table[table["t"].dt.day == 2]["provenance"]) == {"observed"}
    assert set(table[table["t"].dt.day == 3]["provenance"]) == {"forecast"}
    # Only the forecast rows carry an issue time, and it is the forecast's, not the fetch's.
    assert set(table.loc[table["provenance"] == "forecast", "issued_at"]) == {pd.Timestamp(issued)}
    assert table.loc[table["provenance"] == "observed", "issued_at"].isna().all()
    # ap comes from the Bartels table, so a Kp 6 forecast is ap 80, not 6.
    assert set(table[table["source"] == "swpc:kp-forecast"]["ap"]) == {80.0}


def test_a_gap_with_no_source_stays_a_gap():
    """A quiet zero substituted for a missing index would be a silent, dangerous invention."""
    celestrak = celestrak_rows([("2026-09-01", 2.0, "OBS")])
    table = wt.build(datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 9, 2, 21, tzinfo=UTC), celestrak_rows=celestrak)
    missing = table[table["provenance"] == "missing"]
    assert len(missing) == 8
    assert missing["kp"].isna().all() and missing["ap"].isna().all()
    assert wt.table_summary(table)["n_missing"] == 8


def test_the_27_day_outlook_spreads_its_daily_a_index_flat_rather_than_its_largest_kp():
    """A daily maximum repeated eight times would say the whole day was as bad as its worst hours."""
    outlook = pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-09-01", tz="UTC")],
            "f107": [110.0],
            "ap": [48.0],  # a disturbed day on average
            "kp_max": [7.0],  # but only its worst three hours reached G3
        }
    )
    issued = datetime(2026, 8, 31, 1, 55, tzinfo=UTC)
    table = wt.build(datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 9, 1, 21, tzinfo=UTC), outlook=(outlook, issued))
    assert set(table["source"]) == {"swpc:outlook-27day"}
    assert set(table["ap"]) == {48.0}
    # Kp is the inverse of the A index, so 5 (the G1 threshold), not the day's largest of 7.
    assert set(table["kp"]) == {5.0}
    assert set(table["issued_at"]) == {pd.Timestamp(issued)}


def test_a_synthetic_profile_is_labelled_as_one_and_leaves_the_solar_flux_alone():
    """A geomagnetic scenario changes the index, not the Sun's radio output."""
    celestrak = celestrak_rows([("2026-09-01", 2.0, "OBS")])
    table = wt.build(datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 9, 1, 21, tzinfo=UTC), celestrak_rows=celestrak)
    storm = wt.apply_synthetic(table, np.array([2.0, 3.0, 5.0, 7.0, 9.0, 8.0, 6.0, 4.0]), name="storm-g5")
    assert set(storm["provenance"]) == {"synthetic"}
    assert set(storm["source"]) == {"synthetic:storm-g5"}
    assert storm["ap"].max() == 400.0  # Kp 9
    np.testing.assert_allclose(storm["f107"], table["f107"])
    assert storm["issued_at"].isna().all()
    # A scenario states its ap rather than forecasting it, so its skill is `designed`; the
    # uncertainty stays at the climatological spread so Step 3 cannot read zero variance off
    # a storm it was told to suppose.
    assert set(storm["skill"]) == {"designed"}
    assert (storm["ap_sigma"] > 0).all()
    assert storm["ap_sigma"].max() >= table["ap_sigma"].max()
    assert list(storm.columns) == list(wt.TABLE_COLUMNS)
    # The day's average ap is recomputed from the profile rather than left at the quiet value.
    assert storm["ap_daily"].iloc[0] > table["ap_daily"].iloc[0]
    with pytest.raises(ValueError, match="intervals"):
        wt.apply_synthetic(table, np.array([1.0, 2.0]), name="too-short")


def test_every_layer_carries_a_skill_and_the_skill_is_not_the_provenance():
    """`forecast` covers both a skilful three-day Kp and a 27-day recurrence guess."""
    celestrak = celestrak_rows(
        [("2026-09-01", 2.0, "OBS"), ("2026-09-02", 1.0, "PRD"), ("2026-09-03", 1.0, "PRD"), ("2026-09-04", 1.0, "PRD")]
    )
    forecast = pd.DataFrame(
        {
            "t": pd.date_range(pd.Timestamp("2026-09-02", tz="UTC"), periods=16, freq="3h"),
            "kp": [2.0] * 16,
            "observed": ["observed"] * 4 + ["estimated"] * 4 + ["predicted"] * 8,
            "noaa_scale": None,
        }
    )
    table = wt.build(
        datetime(2026, 9, 1, tzinfo=UTC),
        datetime(2026, 9, 4, 21, tzinfo=UTC),
        celestrak_rows=celestrak,
        kp_forecast=(forecast, datetime(2026, 9, 2, 12, 30, tzinfo=UTC)),
    )
    by_skill = table.groupby("skill", observed=True)["t"].size().to_dict()
    # SWPC's forecast runs out after 3 September; CelesTrak's own prediction covers the 4th.
    # `measured` is both CelesTrak's observed day and SWPC's definitive rows: two sources, one skill.
    assert by_skill == {"measured": 12, "provisional": 4, "forecast": 8, "recurrence": 8}
    # Provenance cannot make this distinction: three of these four skills are one provenance.
    assert set(table.loc[table["skill"] == "recurrence", "provenance"]) == {"forecast"}
    assert set(table.loc[table["skill"].isin(["measured", "provisional"]), "provenance"]) == {"observed"}
    assert set(table["skill"]) <= set(wt.SKILLS)


def test_the_ap_uncertainty_widens_to_the_climatological_spread_past_three_days():
    """A measurement is uncertain by the resolution of the index; a forecast by its lack of skill.

    Past three days the correlation prior is zero, which is the honest statement about a
    three-hour interval eleven days out: it is drawn from the recent climatology and nothing
    narrower is known. Step 3's variance term reads this column.
    """
    now = datetime(2026, 9, 1, tzinfo=UTC)
    # A year of quiet observed record with one storm in it, so the spread is measurable.
    days = [((now - timedelta(days=d)).strftime("%Y-%m-%d"), 1.0, "OBS") for d in range(365, 0, -1)]
    days += [(now.strftime("%Y-%m-%d"), 1.0, "OBS")]
    celestrak = celestrak_rows(days)
    celestrak.loc[celestrak["t"].dt.strftime("%Y-%m-%d") == "2026-05-11", ["kp", "ap"]] = [8.0, 236.0]
    predicted = celestrak_rows([((now + timedelta(days=d)).strftime("%Y-%m-%d"), 1.0, "PRD") for d in range(1, 12)])
    both = pd.concat([celestrak, predicted], ignore_index=True)

    table = wt.build(now, now + timedelta(days=11), celestrak_rows=both, now=now)
    sigma_clim, how = wt.climatological_ap_sigma(both[both["provenance"] == "observed"], before=now)
    assert "measured" in how and sigma_clim > 10.0

    lead = (table["t"] - pd.Timestamp(now)).dt.total_seconds() / 86400.0
    observed = table["provenance"] == "observed"
    # The observed rows sit at ap 4 nT, whose neighbouring Bartels steps are 3 and 5, so the
    # index resolves it to 1 nT and half of that is the measurement's whole uncertainty.
    assert table.loc[observed, "ap_sigma"].max() == pytest.approx(0.5)
    # Inside three days the forecast knows something; past them it does not.
    inside = table[(~observed) & (lead > 0.5) & (lead < 2.5)]
    past = table[lead > 3.5]
    assert (inside["ap_sigma"] < sigma_clim).all()
    assert past["ap_sigma"].to_numpy() == pytest.approx(sigma_clim)
    # And it is monotonic in lead time over the forecast rows, as a widening uncertainty must be.
    forecast_rows = table[~observed].sort_values("t")
    assert (forecast_rows["ap_sigma"].diff().dropna() >= -1e-9).all()
    # A gap has no ap and therefore no uncertainty; nothing invents one.
    gap = wt.build(now + timedelta(days=30), now + timedelta(days=31), celestrak_rows=both, now=now)
    assert gap["ap_sigma"].isna().all() and set(gap["skill"]) == {"none"}


def test_a_forecast_storm_carries_an_uncertainty_proportional_to_the_storm():
    """An ap of 200 nT is not known to the same absolute precision as an ap of 5."""
    now = datetime(2026, 9, 1, tzinfo=UTC)
    quiet = celestrak_rows([((now - timedelta(days=d)).strftime("%Y-%m-%d"), 1.0, "OBS") for d in range(30, 0, -1)])
    forecast = pd.DataFrame(
        {
            "t": pd.date_range(pd.Timestamp(now), periods=8, freq="3h"),
            "kp": [8.0] * 8,
            "observed": ["predicted"] * 8,
            "noaa_scale": None,
        }
    )
    table = wt.build(now, now + timedelta(hours=21), celestrak_rows=quiet, kp_forecast=(forecast, now), now=now)
    assert set(table["ap"]) == {207.0}  # Kp 8 on the Bartels table
    # Half the forecast value, which beats the climatological term at this level.
    assert table["ap_sigma"].to_numpy() == pytest.approx(207.0 * 0.5)


def test_the_interval_grid_covers_the_window_at_three_hour_steps():
    grid = wt.intervals(datetime(2026, 9, 1, 20, 48, tzinfo=UTC), datetime(2026, 9, 2, 4, 0, tzinfo=UTC))
    assert list(grid) == [
        pd.Timestamp("2026-09-01 18:00", tz="UTC"),
        pd.Timestamp("2026-09-01 21:00", tz="UTC"),
        pd.Timestamp("2026-09-02 00:00", tz="UTC"),
        pd.Timestamp("2026-09-02 03:00", tz="UTC"),
    ]


# --------------------------------------------------------------------------------------
# Helioviewer


def test_sun_frames_are_spaced_evenly_and_a_few_a_day():
    times = helioviewer.frame_times(T0, T0 + timedelta(days=1), per_day=4)
    assert times == [T0 + timedelta(hours=6 * i) for i in range(5)]
    assert helioviewer.frame_times(T0, T0, per_day=4) == []
    assert helioviewer.frame_times(T0, T0 + timedelta(days=1), per_day=0) == []


def test_a_thumbnails_size_is_part_of_its_cache_name(tmp_path):
    """Otherwise changing the size goes on serving the old one for ever.

    Found the hard way at the Step 5 review: `HELIOVIEWER_THUMB_PX` was changed from 64 to 32,
    the bundle was rebuilt, and `storm.json` came out exactly the same size because every
    thumbnail was still the cached 64 px one. A config value that cannot change anything is
    worse than no config value.
    """
    full = helioviewer.image_path(T0, tmp_path)
    small = helioviewer.image_path(T0, tmp_path, thumb=True, thumb_px=32)
    large = helioviewer.image_path(T0, tmp_path, thumb=True, thumb_px=64)
    assert full != small != large and full != large
    assert "thumb32" in small.name and "thumb64" in large.name
    assert "thumb" not in full.name
    # And the default follows the config rather than being frozen at whatever it once was.
    assert helioviewer.image_path(T0, tmp_path, thumb=True) == helioviewer.image_path(
        T0, tmp_path, thumb=True, thumb_px=config.HELIOVIEWER_THUMB_PX
    )
