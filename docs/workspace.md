# Local visual workspace

The workspace keeps the existing interactive Earth and catalogue, adds real Swarm reference tracks and exposes four case-based tools. It is an engineering research preview. No organisation has adopted it, and no organisation is named in this repository as a prospective user.

## Start on this PC

From the repository root, install the locked project dependencies with `uv sync`. In `web`, run `npm ci` then `npm run build`. Return to the project root and run:

```powershell
uv run --offline python -m driftwatch.workbench
```

On Windows, `start-workspace.cmd` runs the same command after the build. Open **http://127.0.0.1:8765**. Leave the terminal running; Ctrl+C stops the server. Use `--port 8766` if the default is occupied. Node and uv are prerequisites; there is no standalone installer yet.

Initial dependency installation needs internet access. Analysis uses the chosen local files and installed frame-conversion resources, without fetching orbit or weather data. The public/static site serves two stored results — the Swarm A orbit comparison and the ISS contact prediction below — and runs benchmark JSON imports and the evidence exercises in the browser. The conjunction-message tool and the contact planner have no stored example; each needs the reader's own file through the local engine. Its orbit, CDM and contact file analyses require the local Python process. The public site does not ask users to upload private orbit files to Cloudflare.

## Inputs and results

Complete supported formats, variable column mapping and explicit conventions: [input-formats.md](input-formats.md). Design research and adoption tasks: [experience-design.md](experience-design.md).

| Tool | User inputs | Result and decision |
| --- | --- | --- |
| Compare orbits | Reference OEM KVN/XML or mapped states; prediction OEM/OMM/GP/TLE or mapped states; optional candidate model; catalogue number; reference kind; distance tolerance; optional `start,end` manoeuvre CSV | Paired position differences, radial/along/cross-track components, reference conventions, true-scale Earth-fixed tracks and source fingerprints. Engineer reviews the adapter, product version or tolerance. |
| Conjunction messages, inside Compare orbits | Two CCSDS CDMs in KVN or XML; time tolerance | Unordered-pair/time matching, message quantities and position-covariance semidefiniteness. Engineer reconciles input versions before interpreting a probability change. |
| Ground contacts | OEM or OMM; optional alternative orbit; station latitude/longitude/height; elevation mask; start and duration; optional `lock_time` CSV | Acquisition/loss times, peak elevation, paired alternative acquisition times and receiver-lock matches. Engineer tests an orbit-refresh policy; late lock is not treated as an orbit observation. |
| Storm models | Published real benchmark; own driftwatch benchmark JSON; or paired trial CSV with reference kind and forcing type | Lead-dependent differences, correction effect, uncertainty-band coverage when supplied and a user-selected empirical tolerance. Researcher accepts, restricts or rejects a model claim. |
| Evidence lab | One of three documented cases, an answer and review note; optional local text evidence file | Answer-key feedback and a downloadable review with the evidence fingerprint. Instructor assesses whether the claim exceeds its supporting data. |

The model CSV schema is `trial_id,satellite,window,lead_h,baseline_km,candidate_km`. Residuals are signed along-track differences in km against the same declared reference. `sigma_km` is optional and must be positive when supplied. With forecast forcing, `issued_at,valid_at` are required and must agree with `lead_h` within one minute. The tool refuses duplicate satellite/trial/lead rows, including duplicated rows split across tuning and holdout windows. A named holdout remains the analyst's declaration; independence from tuning is not verified.

Each OEM segment must name one object, Earth as its centre, a supported reference frame and a UTC/TAI/GPS clock. Positions and velocities use the CCSDS km/km/s convention. Different objects, missing conventions, non-finite states, unsupported frames and overlapping segments are refused. OEM covariance blocks are not used. The existing J2000/EME2000 approximation also handles the documented MEME/GCRF/ICRF aliases; consult [frames-and-time.md](frames-and-time.md) for the limits before precision use.

OMM XML/KVN and GP JSON/CSV are read through the existing SGP4 implementation. One fixed fit with the latest epoch at or before the comparison start is chosen for the selected object. No newer fit is silently substituted later. An epoch does not prove when a product was published. The user's catalogue-number association with an OEM is a declaration; object IDs are compared where supplied.

The orbit comparison uses at most about 4,000 samples, at least 60 seconds apart. Reference conversion needs positions five seconds either side, so segment edges are excluded. It never interpolates across OEM metadata boundaries. Manoeuvre exclusions cover the recorded interval only; later samples may still contain the burn's effect. The plotted Earth-fixed traces show up to 100 minutes, at actual altitude with no displacement exaggeration. Missing data are not orbital manoeuvres.

The contact search samples every 20 seconds and refines the elevation crossings. Short or grazing passes can be missed; this is not the catalogue screener's no-miss algorithm. WGS84 station geometry uses a GMST-only Earth rotation, UTC in place of UT1, no polar motion and no refraction. It is a timing experiment, not a command schedule or precision pointing system. A cut-off pass is marked partial. Receiver times match uniquely within a pass plus a two-minute margin. Duplicate or ambiguous matches remain unresolved. No receiver log ships and the match has never been run against a real one; it needs a CSV with a `lock_time` column in UTC. Alternative passes match uniquely within ten minutes and only when both are complete.

Save JSON for the evidence bundle, CSV for measurements or print the current result. Save/export actions open a preview with the filename and size, then offer a download, full-text copy or manual full-text selection. Long previews initially show 60,000 characters; downloads and copies include the entire report, and manual selection expands the preview to the complete text. If the browser blocks automatic clipboard access, the full text is selected for keyboard copying. A download request is not reported as a confirmed save. JSON includes the software version, parameters/request fingerprint, input text fingerprints and limitations. Files and results are not saved by the server. Results in the page are discarded on a tool switch or reload unless exported. Benchmark imports remain only in the current browser session; there is no automatic local storage.

## Examples and provenance

Every shipped example is measured or published data. `web/public/examples/benchmark.json` is the measured comparison of public element sets for Swarm A (39452), B (39451) and C (39453) against ESA's reduced-dynamic precise science orbits; `benchmark-tracks.json` holds short reconstructed ESA tracks for the corresponding dates. That benchmark and those tracks are the default orbit-comparison example. Rebuild every example from the existing offline cache with:

```powershell
uv run --offline python scripts/export_workspace_examples.py
```

Two further examples ship, and both name their object and their source.

**Orbit comparison — Swarm A (NORAD 39452, 2013-067B).** The reference is ESA's reduced-dynamic
precise science orbit (`SW_OPER_SP3ACOM_2_`) for 13 May 2024, packaged as an OEM in ITRF and UTC.
Against it run two genuine Space-Track `gp_history` element sets for the same satellite: one with
epoch 2024-05-12T20:57:24Z, three hours before the window, and one with epoch
2024-05-06T14:26:27Z, six days before it. Compared with the same measured orbit, the newer set has
a median position difference of 0.54 km and the older one 32.8 km. That gap is the real growth of
error with element-set age through the May 2024 storm — the quantity the horizon result reports —
and not a displacement anyone chose. ESA's own thruster record (`SW_OPER_SC_xDYN_1B`) supplies the
manoeuvre intervals; it records no orbit-control thrust in this window, so nothing is excluded.

**Ground contacts — ISS (NORAD 25544, 1998-067A).** Two genuine Space-Track element sets, epochs
2024-05-10T20:04:09Z and 2024-05-04T05:00:00Z, over IGS station **HRAO00ZAF** at the Hartebeesthoek
Radio Astronomy Observatory: latitude -25.890, longitude 27.687, height 1414.744 m, from the
published IGS station list (`https://files.igs.org/pub/station/general/IGSNetwork.csv`). That is a
surveyed geodetic marker, not a statement about which antenna is used or whether the site is
available. Over 11 May 2024 the two sets predict the same three passes and their acquisition times
differ by about a second, although at the first acquisition the two predicted positions are 9 km apart — which is a result
about this object over this day, not a general claim about refresh policy.

**Two tools ship no example.** The conjunction-message tool needs two CCSDS CDMs, KVN or XML,
describing the same conjunction, supplied by the reader from their own conjunction-assessment
provider; it has not been exercised on real conjunction messages. The contact planner needs a week
of real requests as CSV or TSV; it has not been exercised against a real request week. Neither
gets an invented substitute, because an invented input would show the software running rather than
working.

## Local boundary and present limits

The server binds only to 127.0.0.1, checks the Host and Origin, requires a per-process token for analysis, exposes no CORS permission, accepts no arbitrary filesystem paths and serves only the built public interface. Each input text is limited to 12 MB; the whole request to 40 MB. Analyses run serially. Static responses use a restrictive content policy; request/result contents are not logged or stored.

The existing `no_network` guard disables the HTTP clients used by driftwatch and astropy's automatic downloads during analysis. This is an application guard, not OS-level network isolation or a security certification. It does not protect against an already compromised PC, browser extensions or a modified program. Text fingerprints refer to UTF-8 text as processed, which can differ from raw file bytes after browser decoding or BOM removal; the evidence-lab fingerprint has the same text-normalisation scope. A hash identifies content, not its source or truth.

There is no account system, payment collection, multi-user deployment, background job queue, installation signing, telemetry, hardware control or operational service guarantee. Those belong behind a real adopter's requirements and a funded scope. Python handles confidential local analysis; the static viewer remains publicly deployable without embedding those inputs.

## Plan one antenna

Inside Ground contacts, choose **Plan one antenna**. Candidate contacts are supplied as contact_id,satellite,start,end,priority, or through an explicit column and separator mapping. ISO times require Z or a UTC offset. Priorities are positive user preferences. The engine selects whole contacts to maximise their summed priority, respecting a fixed turnaround, and reports exclusions. It assumes visibility and other feasibility checks have already been performed. Use complete predicted passes as a starting table through the visibility result's planning export; set priorities and combine requests for the one antenna before scheduling. The planner has not been exercised against a real request week: no station has supplied a week of requests, an acceptance rule or an accepted schedule, so it has produced no measured comparison and ships no example. It needs a request table from the station: CSV or TSV with `contact_id,satellite,start,end,priority`, optional `baseline` and `locked` flags, and ISO times carrying Z or a UTC offset. Priorities are preference points, not revenue or reliability. No commands are sent.

The schedule review also accepts `baseline` flags for already accepted requests and `locked` flags for protected commitments. It compares the proposed plan with the actual supplied baseline, reports additions/removals/retained contacts and shows contact minutes separately from priority. Protected contacts must stay; conflicting commitments cause an error. Equal-priority solutions minimise changes to the supplied schedule. An infeasible baseline is identified without an improvement claim. There is no inference that a missing baseline means an empty accepted schedule.

Any priority trade-off it proposes is shown with contact minutes beside it, so the engineer can challenge the objective rather than accept a single score. JSON, a comparison CSV, the editable request table and selected-only proposed contacts can all be exported. The operator still owns bookings and feasibility checks. Any pilot would need one real request week, its constraints and the schedule the station currently runs, none of which exists here.

_Last updated 7 September 2026._
