"""The period report and the machine-readable export.

The export follows the shape of the IAU CPS SatChecker field-of-view response
(``GET /fov/satellite-passes/``, synchronous form, documented at
satchecker.readthedocs.io): a list holding one object with ``data.satellites`` keyed by
``"NAME (NORAD)"``, each with ``name``, ``norad_id`` and ``positions`` carrying ``altitude``,
``angle``, ``azimuth``, ``date_time``, ``dec``, ``julian_date``, ``ra``, ``tle_epoch`` and
``range_km``, plus ``total_position_results`` and ``total_satellites``, ``source`` and
``version``. Two fields are added to every position, ``cross_track_uncertainty_deg`` and
``horizon``, which is the whole of what this lane would offer upstream; everything else
driftwatch adds sits under its own keys beside ``data`` and can be ignored by a SatChecker reader.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from driftwatch import __version__
from driftwatch.radio import emissions
from driftwatch.radio import horizon as horizon_mod
from driftwatch.radio.crossings import (
    CATALOGUE_MAX_AGE_DAYS,
    ELEVATION_CUTOFF_DEG,
    MEASURED_POPULATION,
    Crossing,
    ObservationResult,
    Period,
)
from driftwatch.radio.site import MEERKAT, RECEIVERS, Site, beam_fwhm_deg

ADDED_FIELDS = ("cross_track_uncertainty_deg", "horizon")
SATCHECKER_FORMAT = (
    "IAU CPS SatChecker /fov/satellite-passes/ synchronous response "
    "(satchecker.readthedocs.io, Field of View endpoints)"
)
EXPORT_SOURCE = (
    "driftwatch radio lane, on public element sets; response shape after the IAU CPS SatChecker field-of-view endpoint"
)
EXPORT_LIMITS = [
    "Positions come from public element sets propagated with SGP4; no tracking, no orbit determination.",
    "cross_track_uncertainty_deg is the 95th percentile of the calibration benchmark's cross-track residual at "
    "the element set's age, projected on the sky at the crossing's range; it applies only where horizon is "
    "inside or outside, and is null where the object is outside the benchmark's population.",
    "Nothing here is a received power, an occupancy fraction or a sensitivity loss.",
]


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat().replace("+00:00", "Z")


def satchecker_export(
    result: ObservationResult, site: Site, period: Period, elevation_deg: float
) -> list[dict[str, Any]]:
    """One observation's crossings in the SatChecker field-of-view shape, with the two added fields."""
    obs = result.observation
    satellites: dict[str, Any] = {}
    n_positions = 0
    for c in result.crossings:
        key = f"{c.name} ({c.norad_id})"
        entry = satellites.setdefault(key, {"name": c.name, "norad_id": c.norad_id, "positions": []})
        for s in c.samples:
            entry["positions"].append(
                {
                    "altitude": s.elevation_deg,
                    "angle": s.separation_deg,
                    "azimuth": s.azimuth_deg,
                    "date_time": s.time_utc,
                    "dec": s.dec_deg,
                    "julian_date": s.julian_date,
                    "ra": s.ra_deg,
                    "tle_epoch": c.set_epoch_utc,
                    "range_km": s.range_km,
                    "cross_track_uncertainty_deg": c.cross_track_uncertainty_deg,
                    "horizon": c.horizon,
                }
            )
            n_positions += 1
    return [
        {
            "data": {
                "satellites": satellites,
                "total_position_results": n_positions,
                "total_satellites": len(satellites),
            },
            "source": EXPORT_SOURCE,
            "version": __version__,
            "format": SATCHECKER_FORMAT,
            "added_fields": list(ADDED_FIELDS),
            "fov": {
                "ra_deg": obs.ra_deg,
                "dec_deg": obs.dec_deg,
                "radius_deg": obs.fwhm_deg / 2.0,
                "radius_is": "half of the primary beam's half-power width at the observation's centre frequency",
                "start_time_utc": _iso(obs.start),
                "duration_s": obs.duration_s,
            },
            "observation": obs.record(),
            "site": site_record(site),
            "catalogue": {
                "as_of": result.catalogue_at,
                "n_objects": result.n_catalogue,
                "max_set_age_days": CATALOGUE_MAX_AGE_DAYS,
            },
            "period": {"name": period.name, "label": period.label, "benchmark_window": period.benchmark_window},
            "in_view_elevation_cutoff_deg": elevation_deg,
            "constellations_in_view": [c.__dict__ for c in result.counts],
            "crossings": [c.record(with_samples=False) for c in result.crossings],
            "limits": list(EXPORT_LIMITS),
        }
    ]


def write_export(payload: Any, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, default=_default) + "\n", encoding="utf-8")
    return path


def _default(o: Any) -> Any:
    if isinstance(o, (pd.Timestamp, datetime)):
        return _iso(o) if isinstance(o, datetime) else o.isoformat()
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(f"cannot serialise {type(o).__name__}")


def site_record(site: Site = MEERKAT) -> dict[str, Any]:
    return {
        "name": site.name,
        "latitude_deg": site.latitude_deg,
        "longitude_deg": site.longitude_deg,
        "height_m": site.height_m,
        "dish_diameter_m": site.dish_diameter_m,
        "source": site.source,
    }


# --------------------------------------------------------------------------------------
# The period report


def _counts_table(counts: Iterable[Any]) -> list[str]:
    lines = [
        "| Constellation | Catalogued members | Above the cutoff at some time | Up at once, mean | Up at once, peak "
        "| Emission in this band |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for c in counts:
        lines.append(
            f"| {c.constellation} | {c.n_catalogued} | {c.n_above} | {c.mean_simultaneous:.1f} "
            f"| {c.max_simultaneous} | {c.status}: {c.detail} |"
        )
    return lines


def _crossings_table(crossings: list[Crossing]) -> list[str]:
    if not crossings:
        return ["No catalogued object's predicted track passed inside the half-power radius during this observation."]
    lines = [
        "| Object | Type | Closest approach (UTC) | Angle from boresight | Elevation | Range | Set age "
        "| Cross-track uncertainty (p95) | Along-track shift (p95) | Trials inside beam/3 | Horizon "
        "| Emission in this band |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    kinds = {"DEB": "debris", "R/B": "rocket body", "PAY": "payload"}
    for c in crossings:
        kind = c.constellation or kinds.get(c.object_type, c.object_type)
        frac = "-" if c.fraction_inside is None else f"{100 * c.fraction_inside:.0f}%"
        unc = "-" if c.cross_track_uncertainty_deg is None else f"{60 * c.cross_track_uncertainty_deg:.1f}'"
        shift = "-" if c.along_track_shift_s is None else f"{c.along_track_shift_s:.1f} s"
        horizon = c.horizon if c.population == "measured" else f"no measured horizon ({c.population_reason})"
        partial = " (in progress at the edge)" if c.partial else ""
        when = c.t_ca_utc[:19].replace("T", " ") + partial
        lines.append(
            f"| {c.name} ({c.norad_id}) | {kind} | {when} | {60 * c.separation_deg:.1f}' | {c.elevation_deg:.1f} deg "
            f"| {c.range_km:.0f} km | {c.set_age_days:.2f} d | {unc} | {shift} | {frac} | {horizon} "
            f"| {c.emission_status}: {c.emission_detail} |"
        )
    return lines


def _observation_section(r: ObservationResult, elevation_deg: float) -> list[str]:
    o = r.observation
    radius_arcmin = 60 * o.fwhm_deg / 2
    declared = emissions.declared_in_band(o.receiver)
    names = sorted({e.constellation for e in declared})
    declared_line = (
        f"Declared emitters inside the {o.receiver.name} band: "
        + (", ".join(names) if names else "none in the emission table")
        + "; "
        + "; ".join(f"{e.constellation} {e.signal} {e.lo_mhz:g}-{e.hi_mhz:g} MHz" for e in declared)
        + "."
    )
    return [
        f"### {o.observation_id}: {o.target}",
        "",
        f"Pointing {o.ra_deg:.5f}, {o.dec_deg:+.5f} (J2000); {_iso(o.start)} for {o.duration_s:.0f} s; "
        f"receiver {o.receiver.name} ({o.receiver.lo_mhz:g}-{o.receiver.hi_mhz:g} MHz digitised), centre frequency "
        f"{o.centre_mhz:g} MHz, half-power width {o.fwhm_deg:.2f} deg, so the beam radius used is "
        f"{radius_arcmin:.1f} arcmin. Record: {o.source}." + (f" {o.note}" if o.note else ""),
        "",
        f"Catalogue as of {r.catalogue_at}: {r.n_catalogue:,} objects.",
        "",
        f"**Product one: in the sky above {elevation_deg:g} degrees during the observation, by constellation.**",
        "",
        *_counts_table(r.counts),
        "",
        f"**Product two: tracks inside the half-power radius ({radius_arcmin:.1f} arcmin).**",
        "",
        *_crossings_table(r.crossings),
        "",
        declared_line,
        "",
    ]


NO_RECORD = (
    "No archived observation with a public record was found for this period. The SARAO archive search, which "
    "carries the pointing, start, duration and band of every released observation, needs a SARAO account "
    "(skaafrica.atlassian.net, ESDKB page 302546945), and no published circular or paper read for this work "
    "gives a MeerKAT observation inside these days. Product two therefore has nothing to run on here; product "
    "one is computed below for the whole period, hour by hour, because it needs no pointing. "
    "`driftwatch radio period` runs both products the moment an observation list is exported from the archive."
)

LIMITS = [
    "- No received power, occupancy fraction or sensitivity loss: those need a measurement at the site, and the "
    "statistics of satellite interference have been modelled elsewhere.",
    "- Constellation counts include retired members still catalogued; the catalogue does not say who is transmitting.",
    "- The measured horizon is three non-manoeuvring satellites at 460 to 506 km in three windows; a station-kept "
    "constellation satellite at the same altitude carries the label by altitude, not by a measurement of its "
    "own error.",
    "- Where the archive's phase centre is not public, the target position stands in for it and the report says "
    "so per observation.",
    "- Scan boundaries inside an observation are not public; a crossing is reported against the whole "
    "observation, so a crossing during a calibrator scan or a slew is counted with the rest.",
]


def period_report(
    period: Period,
    site: Site,
    results: list[ObservationResult],
    hourly_summary: dict[str, pd.DataFrame],
    provenance: dict[str, Any],
    horizon_table: pd.DataFrame,
    elevation_deg: float = ELEVATION_CUTOFF_DEG,
    observation_sources: str = "",
) -> str:
    """The short report for one period: the two products per observation, the weekly aggregate, the horizon rows."""
    lines = [
        f"# Satellite crossings over the Karoo: {period.label}",
        "",
        f"Retrospective for {period.label} ({period.why}), at the {site.name} ({site.latitude_deg:.4f}, "
        f"{site.longitude_deg:.4f}, {site.height_m:.0f} m; {site.dish_diameter_m:g} m dish). Positions are public "
        "element sets propagated with SGP4, each object's newest set at or before the moment in question and none "
        f"later, no older than {CATALOGUE_MAX_AGE_DAYS:g} days. Element-set error is read from the calibration "
        f"benchmark's *{period.benchmark_window}* window (`docs/radio-horizon.md`). Nothing here is a received "
        "power, an occupancy fraction or a sensitivity loss.",
        "",
        f"**Population and limits.** {provenance['n_sets']:,} element sets for {provenance['n_objects']:,} objects "
        f"with epochs from {provenance['epoch_min'][:10]} to {provenance['epoch_max'][:10]}, from Space-Track's "
        "gp_history. Constellation membership is by catalogue name (GLONASS by owner and orbit) and includes "
        "retired members, because the catalogue does not carry transmit status. Emissions are declarations from "
        "public filings, dated in `docs/radio-emissions.md`; a declaration made after these observations "
        "(Starlink direct-to-cell, November 2024) is still listed, as a capability, and says so. The measured "
        f"horizon applies only to {MEASURED_POPULATION}; every other object carries *no measured horizon* and the "
        "reason.",
        "",
        "## Observations",
        "",
    ]
    if observation_sources:
        lines += [observation_sources, ""]
    if not results:
        lines += [NO_RECORD, ""]
    for r in results:
        lines += _observation_section(r, elevation_deg)
    lines += [
        "## The sky over the whole period, hour by hour (product one without a pointing)",
        "",
        "For every hour of the period, the catalogue as it stood at that hour, sampled every minute: how many "
        f"members of each constellation were above {elevation_deg:g} degrees at once, averaged over the period, "
        "and at the peak minute. This is the aggregate a sidelobe sees whatever the dish points at, and it needs "
        "no schedule.",
    ]
    for rx_name, summary in hourly_summary.items():
        rx = RECEIVERS[rx_name]
        lines += [
            "",
            f"### {rx.name} band ({rx.lo_mhz:g}-{rx.hi_mhz:g} MHz), beam {beam_fwhm_deg(rx.centre_mhz):.2f} deg "
            f"at {rx.centre_mhz:g} MHz",
            "",
        ]
        if summary.empty:
            lines.append("No constellation member in the catalogue.")
            continue
        lines += [
            "| Constellation | Catalogued members | Up at once, period mean | Up at once, peak "
            "| Emission in this band |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
        for _, s in summary.iterrows():
            lines.append(
                f"| {s['constellation']} | {int(s['n_catalogued'])} | {s['mean_simultaneous']:.1f} "
                f"| {int(s['max_simultaneous'])} | {s['status']}: {s['detail']} |"
            )
    lines += ["", f"## The radio horizon for this period's window ({period.benchmark_window})", ""]
    w = horizon_table[horizon_table["window"] == period.benchmark_window]
    cols = [c for c in horizon_mod.table_columns() if c.receiver in ("UHF", "L", "S0")]
    if w.empty:
        lines.append("No benchmark trials for this window.")
    else:
        lines += [
            "| Lead | n | cross-track p95 (overhead) | along-track p95 (overhead) | along-track shift p95 | "
            + " | ".join(f"{c.label}, cross / along" for c in cols)
            + " |",
            "| ---: | ---: | ---: | ---: | ---: | " + " | ".join("---:" for _ in cols) + " |",
        ]
        for _, r in w.iterrows():
            lead = f"{r['lead_h']:g} h" if r["lead_h"] < 48 else f"{r['lead_h'] / 24:g} d"
            lines.append(
                f"| {lead} | {int(r['n'])} | {r['cross_p95_arcmin']:.1f}' | {r['along_p95_arcmin']:.1f}' "
                f"| {r['along_shift_p95_s']:.2f} s | "
                + " | ".join(f"{100 * r[c.key]:.0f}% / {100 * r[c.along_key]:.0f}%" for c in cols)
                + " |"
            )
        lines += [
            "",
            "Fractions are the share of benchmark trials whose angular error, with the satellite overhead, is under "
            "a third of the beam width, cross-track then along-track; the full table with every receiver is "
            "`docs/radio-horizon.md`.",
        ]
    lines += ["", "## What this does not show", "", *LIMITS, "", f"_Last updated {datetime.now(UTC):%d %B %Y}._"]
    return "\n".join(lines).rstrip() + "\n"


def emissions_page() -> str:
    """The emission table page, with its population statement."""
    bands = "; ".join(f"{r.name} {r.lo_mhz:g}-{r.hi_mhz:g} MHz" for r in RECEIVERS.values())
    lines = [
        "# Declared satellite emissions by band, against the MeerKAT receivers",
        "",
        "Each row is a frequency range a regulator has authorised or an interface control document publishes for a "
        "constellation, with its direction and where it was read. *Declared* means a transmitter may operate there; "
        "it does not say that a given catalogued object is transmitting, how strongly, or that nothing else is "
        "emitted. A band a satellite receives in is listed with its direction and is not an emission. Where a "
        "per-object capability cannot be established from public data, the note says so. The absence of a "
        "published measurement is recorded as *unknown*, not as absence.",
        "",
        "**Population and limits.** The constellations SARAO's own interference list names as space-based sources "
        "at the site (GPS, GLONASS, Galileo, Iridium, Inmarsat, Globalstar), the other GNSS (BeiDou, NavIC, QZSS), "
        "and the two large low-orbit constellations (Starlink, OneWeb). Nothing is listed for any other operator; "
        f"a row's absence is a statement about this table. Receiver bands are the digitised ranges from SARAO's "
        f"specifications: {bands}. SARAO states there are no satellite-based transmitters in the UHF band, and "
        "this table agrees: no declared space-to-Earth range below 1088 MHz was found in the filings read.",
        "",
        emissions.to_markdown(),
        "",
        f"Cross-check: [{emissions.SARAO_RFI[0]}]({emissions.SARAO_RFI[1]}).",
        "",
        f"_Last updated {datetime.now(UTC):%d %B %Y}._",
    ]
    return "\n".join(lines) + "\n"
