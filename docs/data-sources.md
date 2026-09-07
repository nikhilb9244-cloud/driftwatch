# Data sources, attribution and redistribution

The MIT licence applies to driftwatch's code. It does not license third-party data or imply
endorsement by a provider. Source terms govern access and reuse. Public accessibility,
an HTTP success response or a content hash establishes neither permission nor scientific truth.

## CelesTrak

[CelesTrak GP documentation](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
describes orbital formats and retrieval guidance. The software consumes GP OMM JSON, SATCAT,
supplemental Starlink SGP4 fits and RMS records, plus `SW-All.csv` weather indices.
The fetcher uses a descriptive User-Agent and a two-hour minimum between group downloads;
`DRIFTWATCH_CONTACT` adds a contact address. Weather has a twelve-hour cache floor and
can fall back to an older copy, whose age remains relevant.

Credit: **Element sets and SATCAT from CelesTrak (celestrak.org), T.S. Kelso.** The bundle carries
this attribution. Supplemental RMS is a fit residual, not an uncertainty bound across the
operator file's full horizon. Versioned supplemental parquets provide recorded replay inputs;
the mutable response cache does not establish reproducibility.

## Space-Track

The client requests `gp` and `gp_history`, never CDM, emergency or advanced classes.
Credentials are read from `SPACETRACK_USER` and `SPACETRACK_PASS` and are not logged or written
by the client. Its limits are 20 requests per minute, 250 per hour, a two-hour catalogue floor
and four catalogue pulls per day. History responses are cached permanently rather than re-requested.

The [Space-Track documentation and user agreement](https://www.space-track.org/documentation)
restrict transfers generally and grant blanket redistribution permission for basic SSA data
with citation: TLE/OMM element sets, SATCAT, decay and re-entry data. Analysis also
requires citation. This exception does not cover conjunction messages or emergency and
advanced tiers. The agreement remains controlling.

Credit: **Element sets from Space-Track.org (USSPACECOM / 18th Space Defense Squadron),
redistributed with citation under the Space-Track user agreement.** The bundle and reports
carry this line; snapshots and history retain source fields. Element sets are model fits,
not independent orbit determinations by driftwatch.

## SpaceX operator predictions

[SpaceX satellite-operator information](https://www.starlink.com/satellite-operators) and its
public ephemeris service supply predicted Starlink states and covariance. No redistribution
licence is stated by the file service. The project uses these inputs for analysis only,
credits SpaceX, and does not redistribute raw files, repackaged trajectories or derived
covariance/state stores. The Space-Track agreement grants no rights over these files.

Fetches are limited to needed satellites and versions, with a default cap of 300 files.
The predicted horizon is 72 hours, with an eight-hour update cadence. Served covariance describes
uncertainty within a published plan; successive-plan disagreement measures something else.
Neither measures the realised orbit. The full constellation is not harvested.

States are MEME/J2000; `UVW` names the covariance frame, not the state frame.
The six-file start-epoch comparison produced median disagreement of 36.2 km when states were
misread as TEME and 0.356 km after rotation. Sub-kilometre agreement is consistent with the
intended frame, not independent accuracy validation. The nineteen-file propagation comparison
and seventeen lineage-qualified pairs are bounded samples, not fleet-wide error estimates.
[Frame limits](ephemeris-frame.md), [ephemeris method and corrections](spacex-ephemerides.md).

Credit: **Starlink ephemerides published by SpaceX, used for analysis; raw files are not redistributed.**
`check-bundle` rejects prohibited file formats, derived stores and service links in the
deployed bundle. It is a publication check, not a general legal or security certification.
Unretained inputs limit exact replay of served-state runs.

## ESA Swarm and Kelvins

[ESA Swarm data access](https://swarm-diss.eo.esa.int/) supplies reduced-dynamic precise science
orbits (`SW_OPER_SP3xCOM_2_`) and spacecraft dynamics (`SW_OPER_SC_xDYN_1B`). Access and use are
subject to ESA's data policy and specific terms. The benchmark retains source-product identifiers;
public examples contain attributed derived orbit samples and measurements. The code licence
does not govern ESA data. GPS epochs are converted to UTC. The dynamics record supplies
manoeuvre exclusions. Reconstructed orbits provide an independent reference for this comparison,
not perfect truth. Only Swarm A/B/C and the three specified windows have been calibrated.

The [ESA Kelvins collision-avoidance challenge](https://kelvins.esa.int/collision-avoidance-challenge/)
contains anonymised conjunction records. Raw challenge data remain under
`data/external/kelvins`, outside the public bundle; only derived radius and residual statistics
are published. Challenge terms govern the source; no broader redistribution right is claimed.
The earlier statement that the data had not been fetched was stale: the published reproduction
uses them. It checks probability arithmetic on supplied inputs, not screening recall or
driftwatch's covariance calibration. [Reproduction and limits](kelvins-reproduction.md).

## Weather, imagery and station geometry

NOAA SWPC supplies Kp forecasts, real-time K indices, the 27-day outlook and propagated L1 solar
wind through its [public services](https://services.swpc.noaa.gov/). The software stores issue
times, with cache floors of thirty minutes for Kp, six hours for the outlook and fifteen minutes
for solar wind. The bundle contains derived tables and analysis. Access requires no
account; attribution and provenance remain necessary. Government-produced data and third-party
material hosted alongside it are not assumed to have identical rights.

[Helioviewer](https://api.helioviewer.org/docs/v2/index.html) supplies SDO/AIA 193 Å images nearest
the requested time; gaps can make an image hours old. Actual image time and lag remain
visible. Credit follows the [SDO data rules](https://sdo.gsfc.nasa.gov/data/rules.php): NASA/SDO,
the AIA team and the Helioviewer Project. Imagery is context, not evidence of local satellite density.

The ISS contact example uses the [IGS station list](https://files.igs.org/pub/station/general/IGSNetwork.csv)
for HRAO00ZAF, a surveyed geodetic marker. Its coordinates establish neither an available tracking
antenna nor an operating agreement. Contact geometry has no measured receiver-log validation.
NASA OMNIweb is a possible future historical source, not an input to the current result.

## The radio lane: site, archive records and regulatory filings

The MeerKAT array phase centre, dish diameter and receiver bands come from SARAO's public
[MeerKAT specifications](https://skaafrica.atlassian.net/wiki/spaces/ESDKB/pages/277315585/MeerKAT+specifications),
and the space-based interference list from SARAO's
[Radio Frequency Interference](https://skaafrica.atlassian.net/wiki/spaces/ESDKB/pages/305332225/Radio+Frequency+Interference+RFI)
page. The primary beam width is Mauch et al. 2020 (ApJ 888, 61) scaled by wavelength as
de Villiers 2023 (AJ 165, 78) reports. These describe the instrument; they imply no use of, or
agreement with, the observatory.

Archived MeerKAT observations are read from public records, each row of an observation CSV naming
its source. The one record used is GCN Circular 36362 with the pointing from GCN Circular 36105.
The [SARAO archive](https://archive.sarao.ac.za/) holds every released observation's pointing,
start, duration and band after the proprietary period, but its search needs a SARAO account and
was not queried; no account was created.

Declared emissions are read from public regulatory filings and interface control documents, each
row of `docs/radio-emissions.md` carrying its source: the GPS, GLONASS, Galileo, BeiDou, NavIC and
QZSS interface specifications; FCC DA 16-875 (Iridium), DA 24-825 (Globalstar), DA 24-1193
(SpaceX direct-to-cell), FCC 18-38 and FCC 17-77 (Ku-band downlinks); the ITU Radio Regulations
for the Inmarsat L-band allocations. A declaration is a permission to transmit, not a measurement
of an emission, and the absence of a published measurement is recorded as unknown.

The element-set history for the two periods came from Space-Track's `gp_history` under the terms
above, one request per chunk of ids, cached and never repeated.

## Local supplied data

Local OEMs, OMMs, CDMs, state tables and receiver/request records are analysed in memory. They do
not enter the public bundle. Source labels are declarations; hashes identify processed text and
do not verify origin. The application network guard is not operating-system isolation, and the
software does not establish permission to use an externally supplied file.

_Last updated 7 September 2026._
