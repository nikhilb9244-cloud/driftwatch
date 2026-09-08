"""Predicted-passage reports and the proposed SatChecker-shaped metadata export.

Schema 2 withdraws the former crossing/position accuracy labels. Epoch-age and
calibration applicability, declared emission-band evidence and candidate element
discontinuities are separate metadata objects. They are not accepted upstream
fields or operational accuracy, transmitter-state or manoeuvre guarantees.
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
from driftwatch.radio.crossings import (
    CATALOGUE_MAX_AGE_DAYS,
    ELEVATION_CUTOFF_DEG,
    FIT_ARC_HOURS,
    Crossing,
    ObservationResult,
    Period,
)
from driftwatch.radio.site import MEERKAT, RECEIVERS, Site, beam_fwhm_deg

ADDED_FIELDS = ("orbit_quality", "radio_band", "candidate_discontinuity")
POST_MANOEUVRE_CONSEQUENCE = (
    "The benchmark found first post-burn element epochs whose fitted orbit remained consistent with the "
    "pre-burn orbit. The catalogue does not expose the tracking or fit provenance needed to identify why. "
    "A later element discontinuity is retrospective evidence of a change, not confirmation of a manoeuvre "
    "or a known pre-burn fit. See the corrected post-burn analysis in docs/reference-benchmark.md."
)
POST_MANOEUVRE_DETECTOR = (
    "Candidate changes come from the element-set jump detector. Epoch order is not publication order. "
    "The interval endpoints are element epochs, the exclusion arc is an assumed 24-hour analysis rule, "
    "and no actual catalogue fit arc is known. next_set_shows_jump uses later archived elements; null "
    "means the evidence is absent. False does not establish that no manoeuvre occurred."
)
SATCHECKER_FORMAT = (
    "Proposed metadata in the IAU CPS SatChecker /fov/satellite-passes/ response shape; "
    "not an accepted upstream schema (https://satchecker.readthedocs.io/en/latest/fov.html)"
)
EXPORT_SOURCE = "driftwatch epoch-based reconstruction, latest archived element epoch before observation start"
EXPORT_LIMITS = [
    "These are modelled passages through the stated pointing; there is no measured satellite detection here.",
    "Schema 2 removes crossing_horizon and position_horizon: orbital component errors do not determine "
    "beam-entry or timing classification. A full-vector topocentric comparison is required.",
    "orbit_quality requires an eligible reference mission, explicit manoeuvre-excluded public-GP scope "
    "and measured age. Altitude overlap alone never supplies a calibrated uncertainty.",
    "Epoch-based reconstruction: epoch age is not publication age. "
    "Catalogue availability at observation start is not established.",
    "radio_band is declared emission-frequency evidence, not the beam frequency, actual transmission, "
    "received power or interference. Per-object capability and historical operation may be unknown.",
    "candidate_discontinuity is an element-change heuristic. The former fit_arc_spanned_manoeuvre "
    "field is withdrawn: the assumed exclusion arc is not a published fit arc.",
]


def radio_band_record(c: Crossing, obs) -> dict[str, Any]:
    evidence = [
        {
            "constellation": e.constellation,
            "signal": e.signal,
            "low_mhz": e.lo_mhz,
            "high_mhz": e.hi_mhz,
            "direction": e.direction,
            "source": e.source,
            "url": e.url,
            "note": e.note,
            "source_publication_date": "2024-11-26"
            if e.constellation == "Starlink" and "direct-to-cell" in e.signal
            else None,
            "operation_valid_from": None,
            "operation_valid_until": None,
            "historical_validity": "unknown; an order publication date is not local operational authorisation",
        }
        for e in emissions.EMISSIONS
        if e.constellation == c.constellation and e.emits and obs.receiver.overlaps(e.lo_mhz, e.hi_mhz)
    ]
    return {
        "receiver": obs.receiver.name,
        "receiver_range_mhz": [obs.receiver.lo_mhz, obs.receiver.hi_mhz],
        "declaration_status": c.emission_status,
        "detail": c.emission_detail,
        "evidence": evidence,
        "object_transmitting": None,
        "historical_operation_established": False,
        "interpretation": "declared frequency overlap only; unknown is not absence",
    }


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat().replace("+00:00", "Z")


def satchecker_export(
    result: ObservationResult, site: Site, period: Period, elevation_deg: float
) -> list[dict[str, Any]]:
    """One observation's crossings in the SatChecker field-of-view shape, with the added fields."""
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
                    "orbit_quality": dict(c.orbit_quality),
                    "radio_band": radio_band_record(c, obs),
                    "candidate_discontinuity": c.record(with_samples=False)["candidate_discontinuity"],
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
            "metadata_schema_version": 2,
            "format": SATCHECKER_FORMAT,
            "added_fields": list(ADDED_FIELDS),
            "post_manoeuvre": {
                "arc_hours": FIT_ARC_HOURS,
                "detector": POST_MANOEUVRE_DETECTOR,
                "measured_consequence": POST_MANOEUVRE_CONSEQUENCE,
            },
            "fov": {
                "ra_deg": obs.ra_deg,
                "dec_deg": obs.dec_deg,
                "radius_deg": obs.fwhm_deg / 2.0,
                "radius_is": "historical analytic circular FWHM/2 at the stated frequency; "
                "not a measured-beam validation",
                "start_time_utc": _iso(obs.start),
                "duration_s": obs.duration_s,
            },
            "observation": obs.record(),
            "site": site_record(site),
            "catalogue": {
                "epoch_cutoff": result.catalogue_at,
                "availability_as_of_known": False,
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
        return ["No catalogued object's predicted track entered the assumed circular aperture during this interval."]
    lines = [
        "| Object | Type | Predicted closest approach (UTC) | Angle | Elevation | Range | Element epoch age "
        "| Calibration applicability | Candidate element change | Declared emission evidence |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    kinds = {"DEB": "debris", "R/B": "rocket body", "PAY": "payload"}
    for c in crossings:
        kind = c.constellation or kinds.get(c.object_type, c.object_type)
        when = c.t_ca_utc[:19].replace("T", " ") + (" (interval edge)" if c.partial else "")
        candidate = c.manoeuvre_detection
        lines.append(
            f"| {c.name} ({c.norad_id}) | {kind} | {when} | {60 * c.separation_deg:.1f}' | "
            f"{c.elevation_deg:.1f} deg | {c.range_km:.0f} km | {c.set_age_days:.2f} d | "
            f"{c.population}: {c.population_reason} | {candidate} | {c.emission_status}: {c.emission_detail} |"
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
        f"{o.centre_mhz:g} MHz, historical analytic circular width {o.fwhm_deg:.2f} deg; illustrative aperture radius "
        f"{radius_arcmin:.1f} arcmin. Record: {o.source}." + (f" {o.note}" if o.note else ""),
        "",
        f"Archived element-epoch cutoff {r.catalogue_at}: {r.n_catalogue:,} objects. "
        "Publication-time availability is unknown.",
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
    "No archived observation with a public record was found for this period. The SARAO archive carries the "
    "pointing, start, duration and band of every released observation and documents a GraphQL API for reading "
    "them, which needs a logged-in account's token (`driftwatch radio archive`, `docs/radio-lane.md`); no such "
    "token was available to this run, and no published circular or paper read for this work gives a MeerKAT "
    "observation inside these days. Product two therefore has nothing to run on here; product one is computed "
    "below for the whole period, hour by hour, because it needs no pointing. `driftwatch radio period` runs both "
    "products the moment an observation list is exported from the archive."
)

LIMITS = ["- " + x for x in EXPORT_LIMITS] + [
    "- Where the archive phase centre is unavailable, a target position stands in for it. Scan boundaries, "
    "calibrator scans and slews are unknown, so the assumed pointing is not an actual schedule.",
    "- Historical circular-aperture passages are retained as illustrations. The measured-beam comparison "
    "uses constructed fixed celestial pointings, explicitly separate from this public-record example.",
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
    population: str = "",
) -> str:
    """The short report for one period: the two products per observation, the weekly aggregate, the horizon rows.

    ``population`` is the measured population as one sentence (``horizon.population_sentence``);
    left empty, the report points at the band table on the horizon page.
    """
    lines = [
        f"# Predicted satellite passages over the Karoo: {period.label}",
        "",
        f"Retrospective for {period.label} ({period.why}), at the {site.name} ({site.latitude_deg:.4f}, "
        f"{site.longitude_deg:.4f}, {site.height_m:.0f} m; {site.dish_diameter_m:g} m dish). Positions are public "
        "element sets propagated with SGP4, selected by latest archived epoch before the cutoff, "
        f"no older than {CATALOGUE_MAX_AGE_DAYS:g} days. Publication timestamps were not reconstructed. "
        "No beam classification accuracy has been calibrated by the component table. Nothing here is a received "
        "power, an occupancy fraction or a sensitivity loss.",
        "",
        f"**Population and limits.** {provenance['n_sets']:,} element sets for {provenance['n_objects']:,} objects "
        f"with epochs from {provenance['epoch_min'][:10]} to {provenance['epoch_max'][:10]}, from Space-Track's "
        "gp_history. Constellation membership is by catalogue name (GLONASS by owner and orbit) and includes "
        "retired members, because the catalogue does not carry transmit status. Emissions are declarations from "
        "public filings, dated in `docs/radio-emissions.md`; a declaration made after these observations "
        "(Starlink direct-to-cell, November 2024) is still listed as later declared capability, not demonstrated "
        "operation in April or May. Component diagnostics require an eligible reference mission, explicit "
        "manoeuvre-excluded scope and an age from 6 to 168 h; altitude alone does not establish eligibility. "
        + (population or "The reference population is listed in docs/radio-horizon.md.")
        + " No crossing or beam-timing guarantee is attached to these catalogue passages.",
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
        "For each hour, the latest archived element epoch before that hour, sampled every minute: how many "
        f"members of each constellation were above {elevation_deg:g} degrees at once, averaged over the period, "
        "and at the peak minute. This geometric visibility count has no sidelobe gain or power estimate and needs "
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
    lines += [
        "",
        f"## Reference component scales ({period.benchmark_window})",
        "",
        "These are orbital C and I scales at representative mean-altitude range. They do not predict "
        "beam-entry, closest-approach or boundary timing errors. See docs/radio-horizon.md for "
        "definitions, population and unavailable lead bins.",
        "",
    ]
    w = horizon_table[horizon_table["window"] == period.benchmark_window]
    if w.empty:
        lines.append("No benchmark trials for this window.")
    else:
        lines += [
            "| Band | Lead | n | Orbital C p95 | Orbital I p95 | Orbital phase-time p95 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for _, r in w.iterrows():
            lines.append(
                f"| {r['band']} | {r['lead_h']:g} h | {int(r['n'])} | {r['cross_p95_arcmin']:.2f}' | "
                f"{r['along_p95_arcmin']:.2f}' | {r['along_shift_p95_s']:.2f} s |"
            )
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
        *emissions.starlink_l_band_record(),
        "",
        f"_Last updated {datetime.now(UTC):%d %B %Y}._",
    ]
    return "\n".join(lines) + "\n"
