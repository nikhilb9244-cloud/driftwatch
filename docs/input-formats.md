# Supported input formats

Updated 7 September 2026. Recognition uses file content, not its extension. **Supported-field checks are not full CCSDS schema certification.**

| Input | Accepted path | Meaning and boundaries |
| --- | --- | --- |
| CCSDS OEM | KVN and XML, including namespaced XML | Sampled positions/velocities for one spacecraft; explicit Earth centre, object identity, frame and clock. Multiple non-overlapping segments; no interpolation across seams. Declared usable times restrict coverage. |
| CCSDS OMM | KVN and XML; multiple messages in an XML container | Earth / TEME / UTC / SGP4 only, conventional EPHEMERIS_TYPE 0. Latest element epoch at/before the requested start, fixed throughout the run. Epoch is not publication evidence. |
| Provider GP exports | JSON and CSV using OMM keywords | Common CelesTrak/Space-Track exports, not CCSDS JSON/CSV encodings. Missing Earth/TEME/UTC/SGP4 metadata uses the documented GP profile, reported as import warnings. Conflicting explicit conventions are refused. |
| Legacy TLE / 2LE / 3LE | Two 69-character lines, optional name line | Checksums, pair identity and field layout checked. Prefer OMM for modern catalogue IDs. Full OMM IDs are preserved beyond the SGP4 library's internal identifier range. |
| Custom state CSV/TSV | Seven distinct mapped columns | ISO time, three positions and three velocities. Explicit frame (TEME/J2000/ITRF), clock (UTC/GPS/TAI), position units (m/km), velocity units (m/s or km/s), and OBJECT_ID. Comma, semicolon or tab separators. |
| CCSDS CDM | KVN or XML in the conjunction-message tool | Pair/time reconciliation and position-covariance checks. Supplied relative units supported: m, m/s; covariance: m². Other declared units refused. No probability recomputation or covariance calibration. |
| Contact planner table | CSV/TSV, configurable mapping | Contact ID, satellite, start, end, positive priority. Optional mapped `baseline` and `locked` flags declare the current schedule and protected commitments. ISO times with Z or a UTC offset. One antenna, fixed turnaround, whole contacts. Optional `resource` column must contain one value. This is a driftwatch table profile, not a CCSDS booking-message standard. |

A comparison reference must contain sampled states (OEM or mapped states), not mean-element fits. The analyst separately declares whether those states are a prediction, reconstructed orbit or navigation solution.

OEM XML without explicit units uses standard km/km/s; conflicting units are refused. KVN follows the same standard. Accelerations and covariance blocks are not used. Existing frame-conversion approximations remain documented in [frames-and-time.md](frames-and-time.md). Unsupported clocks, theories and frames are not guessed.

For custom states, map exporter columns to EPOCH, X/Y/Z and X_DOT/Y_DOT/Z_DOT. Choose conventions from exporter documentation. Z means UTC and is refused with GPS/TAI. Metres are explicitly converted to kilometres. One spacecraft per file; missing manoeuvre/gap boundaries are not inferred. Split discontinuous products into OEM segments upstream.

Every file is checked again when analysis runs. Inspection reports format, frame, clock, coverage or element epochs, and available catalogue objects.

## Worked examples

Every shipped example is measured or published data, and names its object and source.

| Path | Example | Object and source |
| --- | --- | --- |
| Reference OEM, and the orbit comparison | `swarm-a-esa-orbit.oem` against `swarm-a-elements-2024-05-12.json` and `swarm-a-elements-2024-05-06.json` | Swarm A, NORAD 39452. Reference: ESA reduced-dynamic precise science orbit `SW_OPER_SP3ACOM_2_`. Predictions: two Space-Track `gp_history` element sets six days apart, from `data/history/gph_*.parquet`. |
| OMM / GP JSON, and ground contacts | `iss-elements-2024-05-10.json`, `iss-elements-2024-05-04.json` | ISS, NORAD 25544, two Space-Track `gp_history` element sets, over IGS station HRAO00ZAF (-25.890, 27.687, 1414.744 m) from `https://files.igs.org/pub/station/general/IGSNetwork.csv`. |
| Manoeuvre CSV | `swarm-a-esa-manoeuvres.csv` | ESA `SW_OPER_SC_xDYN_1B` thruster record for Swarm A. Empty over this window, because ESA recorded no orbit-control thrust in it. |
| Model benchmark JSON | `benchmark.json` | Swarm A, B and C against ESA precise orbits: the measured driftwatch calibration benchmark. |
| CCSDS CDM | none | No example ships. The tool needs two CDMs, KVN or XML, for the same conjunction, from the reader's own provider. **It has not been exercised on real conjunction messages.** |
| Contact planner table | none | No example ships. The tool needs one week of the station's own requests. **It has not been exercised against a real request week.** |
| Receiver log | none | No example ships. The tool needs a CSV with a `lock_time` column in UTC. **The match has not been run against a real receiver log.** | A fingerprint identifies processed UTF-8 text, not an authenticated publisher. Mappings and analysis parameters are included in the request fingerprint. Private file processing requires the loopback Python service; the static/Vite preview does not contain that engine.

Bounds: 12 MB/file, 40 MB/request, 10,000 OMM records, 100,000 table rows, 5,000 candidate contacts and a 31-day planning window. Duplicate object/epoch fits are refused so the user resolves ambiguous versions. OEM states must increase and be finite. XML DTDs/entities, malformed state rows, conflicting identities and unsupported declared units are refused.

## Schedule-review flags

`baseline` means the request is in the current accepted schedule. `locked` means it must appear in the proposed schedule. Recognised flag columns are used automatically; custom headings can be mapped. Choosing **Not supplied** explicitly omits a flag column. Values are case-insensitive `true/false`, `yes/no` or `1/0`; blank means false. Ambiguous values such as `booked` are refused. The seven mapped columns, when supplied, must be distinct.

Supply the whole candidate set, including unaccepted requests; otherwise the comparison cannot discover those alternatives. The current schedule is checked for overlaps including turnaround and for missing protected contacts. An infeasible current schedule is reported with the conflicts and receives no claimed priority gain. Two conflicting protected contacts stop planning; neither is silently dropped. Equal-priority feasible plans minimise the count of additions plus removals, then use a deterministic tie-break. Times, priorities and the flags remain declarations, not verified bookings.

Five-column tables remain supported, with the explicit result **Supply the current schedule to measure a gain**. Exporting proposed contacts saves selected rows only and preserves the original flags; it does not book them or relabel them as the accepted schedule. The request-table export includes every candidate and can be edited for another review. Spreadsheet-safe CSV prefixes text beginning with formula markers; JSON preserves the complete evidence values.

## Sources

CCSDS defines orbit messages and their KVN/XML encodings. This implementation supports useful fields and conventions, rather than every message type or optional field. [CCSDS Orbit Data Messages 502.0-B-3, corrected edition](https://ccsds.org/wp-content/uploads/gravity_forms/5-448e85c647331d9cbaf66c096458bdd5/2025/11/502x0b3e2.pdf).

CelesTrak documents OMM XML/KVN, GP JSON/CSV and omitted common conventions. [GP data formats](https://www.celestrak.org/NORAD/documentation/gp-data-formats.php). Its current catalogue explains migration away from the five-digit TLE limitation. [Current GP element sets](https://www.celestrak.org/NORAD/elements/index.php?FORMAT=xml).

_Last updated 7 September 2026._
