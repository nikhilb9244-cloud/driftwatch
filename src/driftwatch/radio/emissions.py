"""Declared satellite emissions by band, from public regulatory filings, and who belongs to which constellation.

Every row is a *declaration*: a frequency range a regulator has authorised or an interface
control document has published for a constellation. A declaration says a transmitter may
operate there; it does not say that a given catalogued object is transmitting, or how strongly,
or that nothing else is emitted. Where a per-object capability cannot be established from public
data -- which Starlink units carry a direct-to-cell payload, for instance -- the table says so
rather than guessing. And the absence of a published measurement is recorded as *unknown*, not
as absence: no measurement of Starlink's unintended emission inside MeerKAT's bands has been
published, and the row says exactly that.

Directions matter. A band a satellite *receives* in (Earth-to-space) is not an emission from the
satellite; Globalstar's L-band service link is an uplink, so a Globalstar satellite crossing an
L-band beam is not a declared L-band emitter, whatever the band plan suggests at a glance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from driftwatch.radio.site import RECEIVERS, Receiver

SPACE_TO_EARTH = "space-to-Earth"
EARTH_TO_SPACE = "Earth-to-space"
BOTH = "both directions (time-division duplex)"

DECLARED = "declared"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Emission:
    """One declared frequency range for one constellation, with its direction and where it was read."""

    constellation: str
    signal: str
    lo_mhz: float
    hi_mhz: float
    direction: str
    status: str
    source: str
    url: str
    note: str = ""

    @property
    def emits(self) -> bool:
        """Whether the satellite transmits in this range (space-to-Earth or both)."""
        return self.direction in (SPACE_TO_EARTH, BOTH)

    def receivers(self) -> list[str]:
        """The MeerKAT receivers whose digitised band this range falls inside, if any."""
        return [name for name, r in RECEIVERS.items() if r.overlaps(self.lo_mhz, self.hi_mhz)]


_GPS = (
    "IS-GPS-200 (L1, L2) and IS-GPS-705 (L5), the GPS interface specifications",
    "https://www.gps.gov/technical/icwg/",
)
_GLO = (
    "GLONASS interface control documents (FDMA L1/L2; CDMA L3), Russian Space Systems",
    "https://glonass-iac.ru/en/documents/",
)
_GAL = (
    "Galileo Open Service Signal-in-Space ICD, issue 2.1 (November 2023), table of carrier frequencies and "
    "receiver reference bandwidths",
    "https://www.gsc-europa.eu/sites/default/files/sites/all/files/Galileo_OS_SIS_ICD_v2.1.pdf",
)
_BDS = (
    "BeiDou Navigation Satellite System Signal-in-Space ICDs (B1I, B1C, B2a, B2b, B3I)",
    "http://en.beidou.gov.cn/SYSTEMS/ICD/",
)
_NAV = (
    "NavIC Signal-in-Space ICD for the Standard Positioning Service (L5 and S bands) and for the L1 band, ISRO",
    "https://www.isro.gov.in/media_isro/pdf/SateliteNavigation/NavIC_SPS_ICD_L1_final.pdf",
)
_QZS = ("IS-QZSS-PNT, the QZSS interface specification", "https://qzss.go.jp/en/technical/ps-is-qzss/ps-is-qzss.html")
_IRI = (
    "FCC DA 16-875 (1 August 2016), Iridium Constellation LLC, second-generation constellation: service links "
    "authorised in 1617.775-1626.5 MHz, 1617.775-1618.725 MHz shared with Globalstar; the satellites are capable "
    "of the whole 1616-1626.5 MHz band",
    "https://docs.fcc.gov/public/attachments/DA-16-875A1.pdf",
)
_GLB = (
    "FCC DA 24-825 (16 August 2024), Globalstar Licensee LLC, replacement satellites: service links "
    "1610-1621.35 MHz (Earth-to-space) and 2483.5-2500 MHz (space-to-Earth)",
    "https://docs.fcc.gov/public/attachments/DA-24-825A1.pdf",
)
_INM = (
    "ITU Radio Regulations, Article 5: mobile-satellite service allocations 1525-1559 MHz (space-to-Earth) and "
    "1626.5-1660.5 MHz (Earth-to-space), the bands the Inmarsat L-band systems operate in; SARAO lists "
    "1526-1554 MHz as Inmarsat at the site",
    "https://www.itu.int/pub/R-REG-RR",
)
# The order, quoted. The reference is the document's own: an Order and Authorization of the Space
# Bureau, adopted and released on the same day; the wording is paragraph 39 of the discussion and
# condition ww of ordering paragraph 89, verbatim, with the sentences on the authority of other
# administrations from paragraphs 39 and 40. The range 1475-1518 MHz lies inside MeerKAT's L band.
STARLINK_DTC_ORDER: dict[str, str] = {
    "reference": "FCC DA 24-1193, Order and Authorization, Federal Communications Commission, Space Bureau, "
    "adopted and released 26 November 2024; In the Matter of Space Exploration Holdings, LLC, Application for "
    "Authority for Modification of the SpaceX NGSO Satellite System to Add a Direct to Cellular System, ICFS File "
    "Nos. SAT-MOD-20230207-00021 and SAT-AMD-20240322-00061, call sign S3069, with GN Docket No. 23-135",
    "url": "https://docs.fcc.gov/public/attachments/DA-24-1193A1.pdf",
    "paragraph_39": "In particular, outside the United States, SpaceX is authorized to transmit in the 1475-1518 "
    "MHz, 1805-1880 MHz, 1930-2000 MHz, 2110-2180 MHz, 2180-2200 MHz, 2345-2360 MHz, and 2620-2690 MHz "
    "(space-to-Earth) bands and to receive in the 1429-1470 MHz, 1710-1785 MHz, 1850-1920 MHz, 1920-1980 MHz, "
    "2000-2020 MHz, 2305-2320 MHz, and 2500-2570 MHz (Earth-to-space) bands.",
    "paragraph_39_administrations": "We also require that any direct-to-cell operations outside the United States "
    "be duly authorized by the relevant administrations and will be subject to the laws, regulations, and "
    "requirements applicable to such operations in the territories of the authorizing administrations.",
    "paragraph_40": "Furthermore, we emphasize that SpaceX, prior to initiation of communications with earth "
    "stations in a particular country, must inform the Commission that it has obtained all necessary "
    "authorizations from the relevant country and demonstrate that such operations will not cause harmful "
    "interference to operations in conformity with the ITU Radio Regulations before the initiation of service "
    "in that country.",
    "condition_ww": "SpaceX is authorized to operate in the MSS for the purpose of direct-to-cell operations "
    "within the 1429-2690 MHz band (space-to-Earth and Earth-to-space) in the following sub-bands bands: "
    "1475-1518 MHz, 1805-1880 MHz, 1930-2000 MHz, 2110-2180 MHz, 2180-2200 MHz, 2345-2360 MHz, and 2620-2690 "
    "MHz (space-to-Earth) (outside the United States only); and 1429-1470 MHz, 1710-1785 MHz, 1850-1920 MHz, "
    "1920-1980 MHz, 2000-2020 MHz, 2305-2320 MHz, and 2500-2570 MHz (Earth-to-space) (outside the United States "
    "only).",
    "condition_aaa": "When conducting SCS operations outside the United States in the 1429-2690 MHz band, "
    "SpaceX shall operate in accordance with the cooperative arrangements with local terrestrial providers to "
    "protect services allocated under Safety-of-Life, Radio Astronomy, Space Research, Radionavigation "
    "Satellite, Aeronautical Radionavigation, Earth-Exploration Satellite, and Space Operations.",
    "status": "declared; subject to each administration",
}
STARLINK_L_BAND_NOTE = (
    "The range 1475-1518 MHz lies inside the L-band receiver's digitised band, 856-1712 MHz, and inside its feed's "
    "design range, 900-1670 MHz. The declaration is a capability, not an operation over the site: the order "
    "authorises the transmission outside the United States only where the relevant administration has "
    "authorised it, and no public record read for this work shows such an authorisation in South Africa. If the "
    "downlink were licensed in South Africa, an intentional space-to-Earth transmission would sit inside the "
    "L-band receiver's band from satellites the period reports count at about 120 above ten degrees at once, so "
    "1475-1518 MHz would join the GNSS, Iridium and Inmarsat ranges the receiver already sees as declared "
    "in-band emitters, at a level no public measurement gives; whether such a licence will be granted is not "
    "predicted here."
)
_STL_DTC = (
    "FCC DA 24-1193 (Order and Authorization, Space Bureau, adopted and released 26 November 2024; ICFS File Nos. "
    "SAT-MOD-20230207-00021 and SAT-AMD-20240322-00061, call sign S3069; GN Docket No. 23-135), paragraph 39 and "
    "ordering paragraph 89 condition ww, SpaceX direct-to-cell: within the United States 1990-1995 MHz "
    "(space-to-Earth) and 1910-1915 MHz (Earth-to-space); outside the United States only, and subject to each "
    "administration, transmit in 1475-1518, 1805-1880, 1930-2000, 2110-2180, 2180-2200, 2345-2360 and "
    "2620-2690 MHz",
    "https://docs.fcc.gov/public/attachments/DA-24-1193A1.pdf",
)
_STL_KU = (
    "FCC 18-38 (29 March 2018), SpaceX NGSO system authorisation: Ku-band user downlinks 10.7-12.7 GHz",
    "https://docs.fcc.gov/public/attachments/FCC-18-38A1.pdf",
)
_OW_KU = (
    "FCC 17-77 (22 June 2017), WorldVu/OneWeb market access: Ku-band user downlinks 10.7-12.7 GHz",
    "https://docs.fcc.gov/public/attachments/FCC-17-77A1.pdf",
)
_STL_UEMR = (
    "No published measurement inside the MeerKAT bands. The published measurements of Starlink unintended "
    "emission are at LOFAR frequencies: Di Vruno et al. 2023, A&A 676, A75 (110-188 MHz) and Bassa et al. "
    "2024, A&A 689, L10 (10-88 and 110-188 MHz)",
    "https://doi.org/10.1051/0004-6361/202346374",
)
SARAO_RFI = (
    "SARAO, Radio Frequency Interference (skaafrica.atlassian.net, ESDKB page 305332225): the space-based "
    "sources it lists in the MeerKAT bands are GPS, GLONASS, Galileo, Iridium, Inmarsat and Globalstar, and it "
    "states there are no satellite-based transmitters in the UHF band",
    "https://skaafrica.atlassian.net/wiki/spaces/ESDKB/pages/305332225/Radio+Frequency+Interference+RFI",
)

_NOT_PER_OBJECT = "direct-to-cell capability is not established per object from public data"
_OUTSIDE_US = "declared and subject to each administration; " + _NOT_PER_OBJECT
_RECEIVES = "the satellite receives here; not an emission"


def _gnss(
    constellation: str, signal: str, centre: float, bandwidth: float, source: tuple[str, str], note: str = ""
) -> Emission:
    return Emission(
        constellation,
        signal,
        centre - bandwidth / 2,
        centre + bandwidth / 2,
        SPACE_TO_EARTH,
        DECLARED,
        source[0],
        source[1],
        note,
    )


def _row(
    constellation: str, signal: str, lo: float, hi: float, direction: str, source: tuple[str, str], note: str = ""
) -> Emission:
    return Emission(constellation, signal, lo, hi, direction, DECLARED, source[0], source[1], note)


def _dtc(lo: float, hi: float, note: str = _OUTSIDE_US) -> Emission:
    return _row(
        "Starlink", "direct-to-cell downlink, outside the United States", lo, hi, SPACE_TO_EARTH, _STL_DTC, note
    )


EMISSIONS: tuple[Emission, ...] = (
    # GNSS. Centre frequency and a 24 MHz extent for the wideband signals (the receiver reference
    # bandwidths in the ICDs are 20 to 41 MHz); SARAO's own list uses 20 MHz windows.
    _gnss("GPS", "L1 (C/A, P(Y), M, L1C)", 1575.42, 24.0, _GPS),
    _gnss("GPS", "L2 (P(Y), M, L2C)", 1227.60, 24.0, _GPS),
    _gnss("GPS", "L5", 1176.45, 24.0, _GPS),
    _row("GLONASS", "L1 FDMA (channels -7 to +6)", 1598.0625 - 5.0, 1605.375 + 5.0, SPACE_TO_EARTH, _GLO),
    _row("GLONASS", "L2 FDMA (channels -7 to +6)", 1242.9375 - 5.0, 1248.625 + 5.0, SPACE_TO_EARTH, _GLO),
    _gnss("GLONASS", "L3 CDMA", 1202.025, 20.46, _GLO),
    _gnss("Galileo", "E1", 1575.42, 24.552, _GAL),
    _gnss("Galileo", "E6", 1278.75, 40.92, _GAL),
    _gnss("Galileo", "E5 (E5a 1176.45, E5b 1207.14)", 1191.795, 51.15, _GAL),
    _gnss("BeiDou", "B1I", 1561.098, 4.092, _BDS),
    _gnss("BeiDou", "B1C", 1575.42, 32.736, _BDS),
    _gnss("BeiDou", "B2a", 1176.45, 20.46, _BDS),
    _gnss("BeiDou", "B2b", 1207.14, 20.46, _BDS),
    _gnss("BeiDou", "B3I", 1268.52, 20.46, _BDS),
    _gnss("NavIC", "L5", 1176.45, 24.0, _NAV, "1164.45-1188.45 MHz in the ICD"),
    _gnss("NavIC", "S", 2492.028, 16.5, _NAV, "2483.5-2500 MHz in the ICD; the S-band signal, unique to NavIC"),
    _gnss("NavIC", "L1", 1575.42, 24.0, _NAV, "NVS-01 onwards"),
    _gnss("QZSS", "L1", 1575.42, 24.0, _QZS),
    _gnss("QZSS", "L2", 1227.60, 24.0, _QZS),
    _gnss("QZSS", "L5", 1176.45, 24.0, _QZS),
    _gnss("QZSS", "L6", 1278.75, 40.92, _QZS),
    # Mobile-satellite systems.
    _row(
        "Iridium",
        "service links",
        1617.775,
        1626.5,
        BOTH,
        _IRI,
        "authorised range; the satellites can operate 1616-1626.5 MHz",
    ),
    _row("Globalstar", "service uplink", 1610.0, 1621.35, EARTH_TO_SPACE, _GLB, _RECEIVES),
    _row("Globalstar", "service downlink", 2483.5, 2500.0, SPACE_TO_EARTH, _GLB),
    _row(
        "Inmarsat",
        "L-band service downlink",
        1525.0,
        1559.0,
        SPACE_TO_EARTH,
        _INM,
        "allocation, not a per-satellite filing",
    ),
    _row("Inmarsat", "L-band service uplink", 1626.5, 1660.5, EARTH_TO_SPACE, _INM, _RECEIVES),
    # Starlink direct-to-cell, as authorised by the FCC; use outside the United States needs each
    # administration's authority, so a declared band is a capability, not an operation over the site.
    _row(
        "Starlink",
        "direct-to-cell downlink, United States (PCS G block)",
        1990.0,
        1995.0,
        SPACE_TO_EARTH,
        _STL_DTC,
        _NOT_PER_OBJECT,
    ),
    _row(
        "Starlink",
        "direct-to-cell uplink, United States (PCS G block)",
        1910.0,
        1915.0,
        EARTH_TO_SPACE,
        _STL_DTC,
        _RECEIVES,
    ),
    _dtc(1475.0, 1518.0),
    _dtc(1805.0, 1880.0),
    _dtc(1930.0, 2000.0),
    _dtc(2110.0, 2200.0, "2110-2180 and 2180-2200 MHz in the order; " + _OUTSIDE_US),
    _dtc(2345.0, 2360.0),
    _dtc(2620.0, 2690.0),
    _row(
        "Starlink",
        "Ku-band user downlink",
        10700.0,
        12700.0,
        SPACE_TO_EARTH,
        _STL_KU,
        "out of band for every MeerKAT receiver",
    ),
    Emission(
        "Starlink",
        "unintended emission inside 544-3500 MHz",
        544.0,
        3500.0,
        SPACE_TO_EARTH,
        UNKNOWN,
        _STL_UEMR[0],
        _STL_UEMR[1],
        "no published measurement inside the MeerKAT bands; treated as unknown, not as absent",
    ),
    _row(
        "OneWeb",
        "Ku-band user downlink",
        10700.0,
        12700.0,
        SPACE_TO_EARTH,
        _OW_KU,
        "out of band for every MeerKAT receiver",
    ),
)

CONSTELLATIONS: tuple[str, ...] = (
    "GPS",
    "GLONASS",
    "Galileo",
    "BeiDou",
    "NavIC",
    "QZSS",
    "Iridium",
    "Globalstar",
    "Inmarsat",
    "Starlink",
    "OneWeb",
)


def declared_in_band(receiver: Receiver) -> list[Emission]:
    """Declared *emissions* (space-to-Earth or both) that fall inside a receiver's digitised band."""
    return [e for e in EMISSIONS if e.status == DECLARED and e.emits and receiver.overlaps(e.lo_mhz, e.hi_mhz)]


def unknown_in_band(receiver: Receiver) -> list[Emission]:
    return [e for e in EMISSIONS if e.status == UNKNOWN and receiver.overlaps(e.lo_mhz, e.hi_mhz)]


def emission_status(constellation: str | None, receiver: Receiver) -> tuple[str, str]:
    """(status, detail) for a constellation against one receiver.

    ``declared in-band`` names the declared ranges inside the band, with their notes; ``declared,
    out of band`` says the constellation's declarations all fall elsewhere; ``uplink only in
    band`` says the only declared range inside the band is one the satellite receives in;
    ``unknown`` carries the unknown row's note; ``none declared`` is a payload with no row in this
    table, which is a statement about the table and not about the object.
    """
    if constellation is None:
        return "none declared", "no public filing read for this object"
    rows = [e for e in EMISSIONS if e.constellation == constellation]
    inside = [e for e in rows if receiver.overlaps(e.lo_mhz, e.hi_mhz)]
    declared_emits = [e for e in inside if e.status == DECLARED and e.emits]
    if declared_emits:
        parts = []
        for e in declared_emits:
            parts.append(f"{e.signal} {e.lo_mhz:g}-{e.hi_mhz:g} MHz" + (f" ({e.note})" if e.note else ""))
        unknown = [e for e in inside if e.status == UNKNOWN]
        if unknown:
            parts.append(f"{unknown[0].signal}: {unknown[0].note}")
        return "declared in-band", "; ".join(parts)
    unknown = [e for e in inside if e.status == UNKNOWN]
    if unknown:
        return "unknown", unknown[0].note
    uplinks = [e for e in inside if e.direction == EARTH_TO_SPACE]
    if uplinks:
        detail = "; ".join(f"{e.signal} {e.lo_mhz:g}-{e.hi_mhz:g} MHz (Earth-to-space)" for e in uplinks)
        return "uplink only in band", detail
    return "declared, out of band", "; ".join(f"{e.signal} {e.lo_mhz:g}-{e.hi_mhz:g} MHz" for e in rows)


_GALILEO = re.compile(r"^GSAT0\d{3}\b|GALILEO", re.IGNORECASE)


def constellation_of(
    name: str,
    owner: str | None,
    object_type: str | None,
    mean_altitude_km: float | None = None,
    inclination_deg: float | None = None,
) -> str | None:
    """Which constellation a catalogued object belongs to, by name and, for GLONASS, by orbit.

    The public catalogue names GPS, Galileo, BeiDou, NavIC, QZSS, Iridium, Globalstar, Inmarsat,
    Starlink and OneWeb satellites recognisably. GLONASS satellites are catalogued as ``COSMOS``
    with a number, so they are picked out by owner and orbit: a CIS payload near 19,100 km at
    64.8 degrees of inclination. Membership says the object is *of* the constellation as
    catalogued; it does not say the object is operating, which the catalogue does not carry, so
    retired members are counted with the active ones and every count says so.
    """
    if object_type is not None and object_type not in ("PAY", "UNK"):
        return None
    n = (name or "").upper()
    if "DEB" in n.split() or " DEB" in n:
        return None
    if n.startswith("STARLINK"):
        return "Starlink"
    if n.startswith("ONEWEB"):
        return "OneWeb"
    if "NAVSTAR" in n or n.startswith("GPS "):
        return "GPS"
    if _GALILEO.search(n):
        return "Galileo"
    if "BEIDOU" in n:
        return "BeiDou"
    if n.startswith("IRNSS") or n.startswith("NVS-"):
        return "NavIC"
    if n.startswith("QZS"):
        return "QZSS"
    if n.startswith("IRIDIUM"):
        return "Iridium"
    if n.startswith("GLOBALSTAR"):
        return "Globalstar"
    if n.startswith("INMARSAT") or n.startswith("ALPHASAT"):
        return "Inmarsat"
    if "GLONASS" in n:
        return "GLONASS"
    if (
        n.startswith("COSMOS")
        and (owner or "").upper() == "CIS"
        and mean_altitude_km is not None
        and inclination_deg is not None
        and 18500.0 <= float(mean_altitude_km) <= 19700.0
        and 63.0 <= float(inclination_deg) <= 66.5
    ):
        return "GLONASS"
    return None


def starlink_l_band_record() -> list[str]:
    """The direct-to-cell L-band authorisation as a page section: the order's reference and wording, quoted."""
    o = STARLINK_DTC_ORDER
    return [
        "## The direct-to-cell authorisation inside the L band, as declared",
        "",
        f"**Reference.** {o['reference']} ([the order]({o['url']})). **Status: {o['status']}.**",
        "",
        f'**Paragraph 39, verbatim.** "{o["paragraph_39"]}" And, on the authority of other administrations: '
        f'"{o["paragraph_39_administrations"]}"',
        "",
        f'**Paragraph 40, verbatim.** "{o["paragraph_40"]}"',
        "",
        f'**Ordering paragraph 89, condition ww, verbatim.** "{o["condition_ww"]}"',
        "",
        f'**Ordering paragraph 89, condition aaa, verbatim.** "{o["condition_aaa"]}"',
        "",
        f"**What it means for the L-band receiver.** {STARLINK_L_BAND_NOTE}",
    ]


def to_markdown() -> str:
    """The emission table as a markdown page, one row per declaration, with its source and receivers."""
    lines = [
        "| Constellation | Signal | Range (MHz) | Direction | Status | MeerKAT receivers | Source | Note |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for e in EMISSIONS:
        rx = ", ".join(e.receivers()) or "none (out of band)"
        lines.append(
            f"| {e.constellation} | {e.signal} | {e.lo_mhz:g}-{e.hi_mhz:g} | {e.direction} | {e.status} | {rx} "
            f"| [{e.source}]({e.url}) | {e.note} |"
        )
    return "\n".join(lines)


def rows() -> list[dict[str, object]]:
    """The table as plain records, for the JSON export."""
    return [
        {
            "constellation": e.constellation,
            "signal": e.signal,
            "lo_mhz": e.lo_mhz,
            "hi_mhz": e.hi_mhz,
            "direction": e.direction,
            "status": e.status,
            "receivers": e.receivers(),
            "source": e.source,
            "url": e.url,
            "note": e.note,
        }
        for e in EMISSIONS
    ]
