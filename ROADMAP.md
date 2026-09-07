# driftwatch roadmap

## Active plan — 6 September 2026

**Objective: paid work or a viable product.** This plan supersedes the earlier decision to park UI work. The user explicitly requested a substantial visual rebuild, local PC input testing and implementation of the four pitches. The historical phases and dated corrections below remain as the record of how the project developed.

The product now opens on the existing interactive Earth, with reconstructed reference tracks and nearby decision charts. It is a case-analysis workspace. Whole-catalogue screening and the original viewer remain available, with their existing compute and accuracy ceilings.

### Implemented in this update

- Shared interactive Earth between the catalogue and a responsive visual workspace; plain-language summaries with expandable technical explanations and measurements.
- Real Swarm quiet/May/October comparison, real short reference tracks, selectable empirical distance tolerance and import of local benchmark results.
- Loopback-only Python service; browser file selection; bounded in-memory processing; input and request fingerprints; no cloud upload path for private orbit analysis.
- **Orbit-product review workflow**, for a flight-dynamics or ground-software engineer: OEM/OMM trajectory comparison, optional candidate model and manoeuvre intervals, true-scale tracks and export; two-CDM reconciliation with frame and position-covariance checks.
- **Ground-contact workflow**, for a station engineer testing an orbit-refresh policy: ground-contact timing from local orbit data and station parameters, optional alternative orbit, receiver-log matching and export. The contacts example uses genuine Space-Track element sets for the ISS (NORAD 25544) over IGS station HRAO00ZAF at Hartebeesthoek, South Africa (latitude -25.890, longitude 27.687, height 1414.744 m), from the published IGS station list (https://files.igs.org/pub/station/general/IGSNetwork.csv). That is a published geodetic marker, not a surveyed ground-station antenna and not a claim that the site is available.
- **Model-evaluation workflow**, for a researcher assessing a drag or storm correction: paired model-trial CSV evaluation, baseline/candidate results by window and lead, optional uncertainty coverage and issue-time checks for declared forecasts. Actual past forecast data still need to be supplied.
- **Evidence-quality workflow**, for an instructor teaching how far a claim may be taken: three public evidence-quality exercises, answer-key feedback, local text fingerprinting and review export. This is a training prototype, not an intelligence collection service.
- Downloadable real evidence only: the measured ESA Swarm A/B/C calibration benchmark and its reconstructed ESA tracks, which are the default orbit-comparison example, and two genuine Space-Track element sets for one catalogue object from the history store. No invented input is shipped, and the two tools with no real input ship no example at all.
- OEM interpolation no longer bridges metadata seams; the reported empirical horizon stops at the first sampled tolerance breach. The summary language now distinguishes May and October correction results.

Implementation detail and operating limits: [docs/workspace.md](docs/workspace.md).

### Visual, standards and scope update — 6 September 2026

The workspace now has a coherent deep-ink/lime/cyan visual system, a larger Earth-led comparison surface, sharp vector charts, selectable traces, keyboard rotation and bounded high-density rendering. It reports actual canvas resolution; the existing Earth source is 4096 × 2048. Scientific evidence remains expandable. Research and adoption tasks: [experience-design.md](docs/experience-design.md).

Browser verification now covers OEM and element-set comparison against the two genuine Swarm A element sets, the contacts view over the ISS element sets and the HRAO00ZAF coordinates, evidence feedback and visual controls. The CDM and planner views are checked only in their awaiting-input state, because neither has been exercised on real data. The usability pass added readable captions over bright Earth imagery, second-level contact timestamps and an export preview with a full-text manual-copy route for restrictive browsers. The full Python suite passed (577 tests), with final TypeScript and production-build checks after the interface fixes. A real user's second-PC trial remains the next adoption gate; in-app browser download completion has not been confirmed. Detailed evidence: [workspace verification](docs/workspace.md#verification-on-6-september-2026).

The catalogue page, which shares that Earth, was finished after the workspace. Rotating a phone from landscape to portrait had been carrying the landscape camera altitude into a portrait aspect and cropping Earth off both sides; the resize handler now re-fits, and a rotated viewport renders identically to a fresh load at that size. A hundred and sixty layout checks — forty viewports from 320 × 480 to 2560 × 1440, each plain, plain with a panel open, in replay, and in replay with a panel open — are now clear of overlap and horizontal overflow, with every visible control hit-tested at its own centre and the headline, zoom buttons, navigation and transport asserted present rather than merely un-overlapped. In landscape the navigation had sat over the wordmark and the zoom buttons behind the chart. The first fix for that was keyed on width and height alone and was worse in places: it caught portrait phones too, and at 360 × 640 the page lost its only heading and all three Earth buttons on a screen with 240 px of clear space. An overlap test cannot see a missing element, which is why the suite now checks presence and hit-testing; the rules are keyed on shape as well as size. Replay preserves the open panel, the selection, the position through the window and now the keyboard's place: the button used to disable itself while the catalogue loaded and drop focus to the top of the document. Below about 600 × 400 the headline, the zoom buttons and the weather chart are dropped because there is no arrangement that fits them; replay's transport still works there and nothing on screen says the chart is missing. Every measurement is headless Chromium at a set viewport; no real handset, orientation change, touch, assistive technology or second engine has been tried. Detail and the remaining limits: [experience-design.md](docs/experience-design.md#the-catalogue-viewer--6-september-2026).

The public bundle names every fleet member. An anonymisation rule ran from 5 to 7 September 2026 and was withdrawn: it replaced each primary with its catalogue number, which is public and resolves against `objects.json` in the same bundle, so it withheld nothing and cost the reader the label identifying the encounter. The safeguard that does constrain how a flag is read — region and confidence before colour — is unchanged. `docs/writeup-notes.md` records the reasoning in both directions.

Local input now recognises OEM KVN/XML, OMM KVN/XML, provider GP JSON/CSV and legacy TLE. Custom state tables have variable columns, delimiters, explicit units and clock/frame choices; inspection reveals recognised conventions and available objects. This is documented subset support, not full CCSDS certification. [input-formats.md](docs/input-formats.md).

The selected expansion is **one-antenna contact planning**: variable request-table mapping, positive user priorities, fixed turnaround, an exact whole-contact selection, a timeline and a reason for every exclusion. Complete predicted passes export into this table format. A station engineer can test whether a different contact allocation is worth adopting. Feasibility, radio readiness and actual slew constraints remain the operator's inputs. The planner has not been exercised against a real request week: no station has supplied a week of requests, an acceptance rule or an accepted schedule, so it has produced no measured comparison and ships no example. It needs a request table from the station: `contact_id,satellite,start,end,priority` in CSV or TSV, with optional `baseline` and `locked` flags.

Before adding more scheduling complexity, obtain one real request week, its constraints and its current accepted schedule. Demonstrate a changed decision before implementing multi-antenna planning, telemetry models, EO tasking or insurance scores. The [expansion decision](docs/commercial-research.md#expansion-decision-after-the-visual-and-input-rework) identifies the specific data and owner each deferred idea needs. Neither visual polish nor format breadth establishes willingness to pay.

### Resubmitted business brief: implemented schedule review

The user confirmed that no prospect has provided a case yet. The chosen addition makes the existing scheduling pitch falsifiable against a station's current procedure: optional mapped current-schedule flags, protected commitments, an exact preference optimum that minimises changes on ties, explicit baseline-conflict reporting and a comparison of counts, minutes and priority. Review exports include the request table, proposed contacts, all changes and source fingerprints. No bookings or antenna commands are sent.

The planner has not been exercised against a real request week: no station has supplied a week of requests, an acceptance rule or an accepted schedule, so it has produced no measured comparison and ships no example. The next task is to run the [bounded pilot](docs/contact-planning-pilot.md) against one real accepted schedule and have the station engineer assess its proposed changes. A “keep the current schedule” finding is an honest outcome. Do not add network scheduling or spacecraft health scores to avoid finding out whether the current product is useful.

Validation for this extension: 31 focused planner/import/API tests, including exhaustive constrained schedule comparisons and decimal ties; TypeScript/build checks; browser CSV imports for preserved/conflicting commitments; evidence/selected-contact export contents; and desktop/mobile layout checks. Stale reviews are cleared when inputs change. The original four-week commercial gate and stop conditions below still apply. [Re-evaluation of the full brief](docs/commercial-research.md#re-evaluation-of-the-resubmitted-brief--6-september-2026).

### Next four weeks: prove a transaction, then specialise

Planning envelope: 48–60 delivery hours over four weeks, a capacity assumption rather than a statement about the developer's available time. Do not run four parallel product roadmaps. Demonstrate all four workflows, then concentrate on the first organisation that supplies a real case and a funded next step.

| Week | Developer's work | Who must act differently | Exit evidence |
| --- | --- | --- | --- |
| 1 | Package this local workspace, run the two real examples on a second PC with a prospective user — the Swarm benchmark with its ESA tracks as the orbit comparison, and the ISS case over HRAO00ZAF — and collect one case-specific file-format requirement. The conjunction-message tool and the planner are shown as empty tools awaiting the prospect's own file. Arrange focused demonstrations; do not automate outreach. | A ground-software lead, a station engineer, a researcher or an instructor chooses one relevant case. | A named case owner, permitted input files, the decision to be tested and the current procedure. A compliment is not a pass. |
| 2 | Reproduce that user's baseline procedure; validate the delivered import with their real files and add at most one missing adapter or station constraint. Record reference independence, time/frame conventions, excluded samples and the user's tolerance. | The case owner verifies the input pairing and can reproduce the result without the developer interpreting every screen. | Side-by-side evidence from their actual case, including remaining unknowns and time spent with the old procedure. |
| 3 | Deliver a bounded evaluation with an engineering recommendation. Test an explicit fixed-fee scope with the budget owner; record rejection reasons. | Engineer accepts/fixes an adapter or tests an update policy; researcher restricts/rejects a model; instructor adopts/rejects an exercise. | A documented changed decision and either a purchase process, funded collaboration scope or concrete employment discussion. |
| 4 | Complete the accepted scope, measure support effort and demonstrate repeat use. Build only the packaging or integration that prevented adoption. | A second user or colleague repeats the workflow, or the first user brings a second case. | Payment/funded work plus evidence of recurrence. Otherwise narrow or stop feature development. |

### Expansion order

1. Add independent reconstructed/navigation references from a participating operator, with manoeuvre and provenance records. The flight-dynamics engineer can then distinguish real error from agreement between predictions.
2. Add archived forecasts with issue/version evidence. A researcher can then test forecast skill rather than retrospective forcing. The CSV timing check already exists; data provenance remains necessary.
3. Add real ground-station masks, clock/pointing status and receiver records. A station engineer can then investigate acquisition performance without blaming every late lock on the orbit.
4. Add one buyer-requested adapter and supported installation route. A maintained integration is a plausible paid service; speculative format breadth is not.

Defer more catalogue coverage, all-constellation daily scoring, new sensors, automatic manoeuvre advice, generic AI summaries, vessel monitoring, additional government dashboards, subscription billing and team accounts. Reopen only when a named buyer's decision requires them. The current daily screening ceiling is compatible with case-based evaluations.

### Product and commercial gates

- **Current:** research preview and locally runnable prototypes; no operator adoption and no validated willingness to pay.
- **Paid evaluation:** one case owner, real files, accepted decision criteria and an agreed scope. Start with the deliverable, not a blanket claim of “trusted SSA”.
- **Supported product:** two independent teams repeatedly use the same workflow, installations can be reproduced and support costs are known. Then consider signed packaging, saved projects and a supported integration API.
- **Subscription:** a budget owner confirms a recurring problem and pays for maintenance, integration or supported deployment. Do not manufacture a subscription simply because the UI looks commercial.
- **Stop:** after ten relevant conversations or four weeks without a real case and funded next step, publish the findings and use the work to obtain scientific-software/data-engineering work. Maintain corrections; pause expansion.

---

## Historical plan (retained)

Working name, rename freely. This file is written to live in the repository so the coding agent can read it at the start of every phase.

## The idea

A geomagnetic storm heats the upper atmosphere, density rises, drag on every low Earth orbit object increases, and predicted positions drift, mostly along the direction of travel. Conjunction screening built on the public catalogue quietly gets worse at the moment it matters most. driftwatch screens conjunctions for a chosen fleet against the whole catalogue, then shows how miss distances and collision probabilities change under quiet and stormy conditions, both live and in replay of past storms. The end product is a public site, an open repository, a validated write-up and a portfolio piece aimed at the space situational awareness industry.

## Prerequisites

### Accounts

- CelesTrak needs no account. It is the source for the live catalogue and for the daily space weather file used in drag models.
- Space-Track.org needs a free registration. You need it for historical element sets, which make the storm replays possible. Read the user agreement before republishing anything derived from its data.
- NOAA SWPC, NASA OMNIweb, INTERMAGNET and Helioviewer need no accounts.
- GitHub for the repository, GitHub Actions for scheduled runs, and GitHub Pages or Cloudflare Pages for hosting.

### Data sources

- CelesTrak GP data in JSON for the active catalogue, the Starlink, OneWeb and debris groups, and the supplemental Starlink ephemerides, which are more accurate than the standard elements.
- CelesTrak SW-All.csv for daily Kp, ap and F10.7 back to 1957 with forecast values appended.
- Space-Track gp_history for element sets around the validation storms.
- NOAA SWPC JSON feeds at services.swpc.noaa.gov for real-time solar wind, the planetary K index and the three-day Kp forecast.
- NASA OMNIweb for hourly and one-minute solar wind and geomagnetic indices, for analysis and any model training.
- ESA's Kelvins Collision Avoidance Challenge dataset, around 160,000 anonymised real conjunction messages, for checking probability calculations against how operators score risk.
- Helioviewer API for Sun imagery in the storm replay.

### Tools and libraries

Python 3.11 or newer with uv, sgp4, skyfield, astropy, numpy, pandas, scipy, pymsis for the NRLMSIS 2.x atmosphere, pyarrow for parquet, and pytest. For the front end, Vite with globe.gl, or CesiumJS if you want terrain and finer camera control. Plotly for analysis charts. GitHub Actions for scheduled runs.

### Background reading

- Vallado, Fundamentals of Astrodynamics and Applications, for SGP4, reference frames and covariance.
- The sgp4 library documentation and Spacetrack Report Number 3, the original description of the model.
- Alfano's and Chan's papers on probability of collision, and NASA CARA's public material on conjunction assessment.
- Parker and Linares, Satellite Drag Analysis During the May 2024 Gannon Geomagnetic Storm, which is a template for your validation.
- The NRLMSIS 2.0 paper for what the atmosphere model can and cannot do.

### Budget and time

Near zero in money. A domain name if you want one. Roughly fourteen weeks part-time, with the phases below sized for evenings and weekends.

## Phase 0. Setup (week 1)

Goal. A repository, a working environment and enough understanding to avoid fooling yourself.

Do. Register on Space-Track. Scaffold the project with uv. Read what a two-line element set is, what mean elements are, and why an SGP4 position is not a true position. Skim the probability of collision papers. Put this file and the kickoff prompt in the repository.

Done when. Tests run, the catalogue downloads, and you can explain why two element sets for the same object a day apart disagree by hundreds of metres.

## Phase 1. Catalogue and globe (weeks 1 to 3)

Goal. The whole public catalogue propagated and moving on a globe.

Build. Fetch and snapshot the catalogue daily. Propagate everything with SGP4 to any requested time, convert from TEME to an Earth-fixed frame, and export compact positions. A viewer with a time slider, categories, hover details and altitude bands.

Validate. SGP4 against the library's verification cases. Frame conversion against skyfield. A sanity check that the ISS passes over a known location at the right time.

Learn. Reference frames, epochs, and the difference between mean and osculating elements.

Milestone. A public link to a globe with around 30,000 objects moving.

## Phase 2. Conjunction screening (weeks 3 to 6)

Goal. A ranked conjunction list for a chosen fleet.

Build. Pick a fleet you can talk about publicly, for example the ISS, a Sentinel satellite and a couple of university cubesats. Screen in three stages. First a coarse filter on apogee and perigee overlap. Then a time-stepped relative distance over a seven-day window with a step small enough not to miss fast crossings, since relative speeds reach fourteen kilometres per second. Then refine the time of closest approach with a root finder on the relative range rate. Output miss distance, relative speed, the radial, in-track and cross-track components, and the time of closest approach.

Then uncertainty. The public catalogue carries no covariance, so estimate one empirically per object from consecutive element sets, or fall back to published category-level values, and be explicit that it is an estimate. Compute probability of collision with the two-dimensional Foster method using a combined hard-body radius, and add an Alfano or Chan implementation as a cross-check.

Validate. Run your probability code over the Kelvins dataset. You will not match their covariance, but the ranking of high-risk events and the way probability responds to miss distance and covariance should behave the same way. Reproduce a documented public close approach if you can find one.

Learn. Encounter geometry, covariance propagation, and why probability of collision can fall when uncertainty grows.

Milestone. A weekly report page for the fleet with the top twenty conjunctions shown on the globe.

## Phase 3. Storm layer (weeks 6 to 10)

Goal. Show what a storm does to the numbers.

Build. Pull Kp, ap and F10.7 history and the NOAA three-day forecast. Run NRLMSIS along each fleet orbit for quiet and forecast conditions to get density. Convert density to drag acceleration using a ballistic coefficient estimated from each object's own decay history. Propagate the resulting along-track position uncertainty over the screening window and add it to the covariance. Recompute miss distances and probabilities. Add a storm mode toggle, and a replay mode that steps through a historical storm with the Sun image, the Kp bar and the conjunction list all moving together.

Validate. The May 2024 Gannon storm first. Pull element sets for a few hundred low Earth orbit objects across the storm from Space-Track, measure the change in mean motion, infer the density enhancement, and compare it with what NRLMSIS gives you for the same Kp. Then the February 2022 Starlink loss, when 38 of 49 newly launched satellites at about 210 kilometres re-entered after a minor storm. If your model does not show elevated drag in both cases, find out why before going further.

Learn. Thermosphere basics, why forecasts of ap were poor even a day ahead in May 2024, and why density models are the weakest link in the whole chain.

Milestone. A side-by-side of the same conjunction list under quiet and storm assumptions, with the replay working.

## Phase 4. Ship it (weeks 10 to 14)

Goal. A public, automated, documented product.

Build. A daily GitHub Actions run that fetches, screens, computes and republishes. A landing page that explains the problem in plain language. CSV and JSON export for a fleet. Tests, a licence, a citation file, and a methods page that lists every approximation.

Write. A short paper or a long blog post covering the problem, the method, the two validation storms, and what the tool gets right and wrong. Publish it and send it to a few people at a national space agency, a large observatory, a university satellite group and two space situational awareness companies, asking for criticism rather than praise. Findings from the build that the write-up has to name, with their numbers attached, accumulate in `docs/writeup-notes.md` as they are produced, so Step 7 is not reconstructed from memory — the first entry is the EOS SAT-1 red flag that Step 1 produced.

Milestone. Site live, repository public, write-up published, five pieces of outside feedback received.

### Plan change, 2026-09-05: Phase 4 stops at the pipeline

An external review found two correctness errors (the storm term displacing operator-controlled
objects, and a dilution-region flag quoted as a plain red) and a set of framing problems. Both are
corrected (`docs/storm-term.md`, `docs/writeup-notes.md`). The plan changes as a result:

**Steps 3 to 7 of `docs/phase4-prompt.md` and the Step 2A Office of Space Commerce validation are
deferred indefinitely** — the landing page, the CSV and JSON export, the visual pass with the mobile
layout and its paint budget, manoeuvre burden and commandability, the write-up, and the 20 GB OSC
comparison. The reason is one sentence: **they change nobody's decision while no operator uses the
output.** A landing page explains a tool to people who are not yet asking; an export packages numbers
nobody is yet taking away; a paint budget is a property of a page nobody yet loads; a validation
against a government test set says how well the screening matches a reference, which matters only
once somebody relies on the screening. The pipeline, which fetches, screens, scores and publishes
every day and keeps every run, is the part that does something whether or not anybody is watching,
and it is what Phase 4 now ends at.

They are replaced by two items, and both are about the same thing — putting the project in front of
the one reader who can change what it does, an operator with real warnings:

1. **A findings-and-corrections page at the top of the README** (built 2026-09-05). Two pages: the
   drift curve between SpaceX's published states and CelesTrak's fit to them; the frame and the
   48-hour seam findings in the published files; the storm-term predictability split with its
   lead-time structure (skill at three to four days, near zero inside two); and the two falsified
   headlines — common-mode cancellation, and the EOS SAT-1 red — each with its dated correction. It
   is what a reviewer reads first, and it is the honest form of the write-up Step 7 would have been.
2. **A CCSDS CDM parser and matcher** (built 2026-09-05; `src/driftwatch/cdm/`, `driftwatch cdm`).
   Reads Conjunction Data Messages in both forms of the standard, matches them to driftwatch events
   on the object pair and a TCA tolerance, and reports which operator-warned events public data
   found and at what miss and probability, and which public-data flags the operator never received.
   Built against ESA's Kelvins rows as test input — real operational CDMs with the identities removed
   — so the path is exercised before a real message arrives. It is the instrument that turns the
   first operator conversation into a measurement, which is why it is built now rather than then.

Phase 5 is unchanged, and this is what it now begins with: a CDM from someone.

**Added 2026-09-05, after the second review: one bounded experiment and one optional path.** The
experiment is the calibration benchmark against precise orbits (`docs/calibration-benchmark.md`,
`driftwatch validate swarm`), capped at one working week: Swarm A, B and C against ESA's precise
science orbits, over the May 2024 storm with a quiet control before it and an October 2024 storm
held out from every tuning, one trial per public element set, four things reported by lead bin, and
the result published on the findings page whatever it showed (item 6 there). It is the first
comparison of a public element set with an independent truth in this project, which is the thing
the methods page had said nothing here had made. The optional path is `driftwatch local`
(`docs/local-analysis.md`): an operator's own ephemerides, messages and records through the CDM
matcher, the provenance check and the same benchmark, with the network refused for the duration, so
the public demonstration stays reproducible from public sources and the operator's data stays on
the operator's machine. The parked items below have their premises rewritten rather than deleted,
dated the same day.

Parked for this phase (added 2026-09-02 at the Phase 2 Step 1 review; not to be built before Phase 4):

- ~~**Stage C should interpolate the SpaceX ephemeris states directly for served events, so the trajectory and the covariance share a source.**~~ **Built, Phase 4 Step 1, 2026-09-03** — and it was a bigger item than this entry supposed. The 0.2 km figure is CelesTrak's fit residual over the arc the fit was made on, not over the file: measured on nineteen matched files, the propagated element set sits a median 0.30 km from the published ephemeris inside 12 hours but **2.8 km at 12 to 24, 28 km at 36 to 48 and 83 km at 60 to 72**, almost all in-track (one fetch, one date, against the published prediction rather than the realised orbit; the lineage of each pair was verified on 2026-09-05 and the drift is the same on the pairs that share a file as on those that do not, `docs/spacex-ephemerides.md`, "Lineage, checked"). Three consequences. The Phase 2 patch was the right shape at a hundredth of the right size at the far end of the horizon. Serving SpaceX's 3.8 km control box on a trajectory 83 km out **understated** the uncertainty on the events furthest ahead. And "a decision about what Stage B screens on" had only one defensible answer: Stage B screens on the published states too, because no pad covers 83 km. The states are stored on a 120-second grid (measured interpolation error: median 5.7 m, maximum 6.8 m), rotated out of the files' MEME/J2000 frame into TEME (44 km if you get that wrong), and split at every discontinuity — every file carries one at exactly 48 hours. The fit residual now applies per event rather than globally. See `docs/phase4-plan.md` and `docs/spacex-ephemerides.md`.
- A live impacts panel in the viewer driven by NOAA's R (radio blackout), S (solar radiation storm) and G (geomagnetic storm) scales, read from the SWPC JSON feeds that Phase 3 already pulls for Kp, so a visitor sees the current and forecast scale levels next to the conjunction list.
- ~~An overlay for the May 2024 storm replay showing Starlink round-trip times from public RIPE Atlas probes on Starlink connections, plotted against the Kp bar, so the replay shows what the storm did to a user-facing service alongside what it did to the orbits.~~ **Premise withdrawn 2026-09-05.** A latency or loss excursion coincident with a storm must not be described as showing that the orbits moved: network degradation during a storm has routing, ground-segment, ionospheric and demand explanations that have nothing to do with orbital displacement, and the replay would be asserting a cause it cannot test. Any use of the RIPE Atlas record is a separate causal study with its own controls, not an overlay on this one. Superseded by the entry below, whose premise is rewritten the same way.

Parked for this phase (added 2026-09-02 at the Phase 3 Step 2 review; not to be built before Phase 4):

- **A commandability column on every event — premise rewritten 2026-09-05.** ~~The interval between the fleet member's last ground contact and the time of closest approach, from a pass predictor over the fleet's ground stations, with the note that a pass is an opportunity to command, not a guarantee of one.~~ A visible pass is not an opportunity to command. Whether an operator can act before an encounter depends on its actual contact schedule, its command-uplink and planning constraints and its decision latency, none of which a pass predictor sees, and a column computed from station coordinates would assert a capability nobody has confirmed. The measurable form is a column filled from an operator's own contact and command records, supplied by that operator for its own fleet; the tool's part is to carry it beside the time of closest approach and say whose record it is. Not to be built from public data.
- **Investigation burden, replacing manoeuvre burden — premise rewritten 2026-09-05.** ~~The count of events crossing an operator's action threshold under each storm scenario, against quiet, reported per fleet member and per scenario as the number of burns an operator would have had to plan.~~ Withdrawn as stated: a threshold crossing is not a burn, and most crossings are investigated and dismissed, so a count of crossings measures nothing an operator recognises. The measurable quantity is investigation burden — how many events an operator's analysts would have had to look at under each scenario, and for how long — and it can only be measured with an operator, from their own records of what they investigated and what it cost. The scenario machinery already produces the candidate list under each scenario; the burden is theirs to count against it, and the threshold is theirs to choose.
- **Lifetime loss per storm, for every low object — premise rewritten 2026-09-05.** ~~The same ballistic coefficient and density track that Step 3 computes, integrated to a re-entry rather than to a time of closest approach: how many days of remaining life a G3, G4 or G5 costs an object at 300, 400 and 500 km; needs no new data.~~ It is not a cheap consequence of the density model. A remaining-life figure integrates the coefficient and the density over months, and the coefficient results say what that would rest on: a `B*`-derived coefficient has no predictive power for even a three-day shift, a `typical` stand-in is a population median, and a measured coefficient carries the density model's own storm bias (22 to 23 per cent on one storm), which cancels in the quiet decay and not in the storm response. Lifetime loss requires validated decay modelling — a coefficient and a density model checked against observed re-entries or against precise orbits over the integration span — and none of that exists here. To be built, if at all, after a calibration against precise orbits (`docs/calibration-benchmark.md`) has said how far the decay model can be trusted.
- **Illuminated satellites over southern African sites, per night, with growth over years.** Two related counts: satellites above a chosen elevation at Sutherland (the South African Astronomical Observatory) that are sunlit while the sky at the site is in astronomical twilight or darker, and satellites above the horizon at the SKA core site in the Karoo. Both are a shadow-geometry calculation on the propagated catalogue and nothing more, and both answer a question the astronomy community here is actively arguing about. Run over several years of historical snapshots it gives the growth curve, which is the part that is hard to dispute.
- **A Hermanus magnetic field rate-of-change panel, from INTERMAGNET — premise rewritten 2026-09-05.** ~~The Hermanus observatory is an INTERMAGNET station, so the one-minute magnetogram is public; dB/dt drives geomagnetically induced currents, and a panel showing it against a stated threshold puts a local ground-level measurement beside the orbital story.~~ A dB/dt threshold chosen by this project would be a number with no action behind it. What makes such a panel meaningful is a grid engineer with an action criterion — the rate of change at which their operator does something, for their transformers and their network — and that criterion has to come from them. Until one does, the panel is a picture of a storm and not an instrument. Check INTERMAGNET's attribution and licensing conditions before anything is redistributed; the data are free but conditioned.
- **A Starlink latency and loss record for May 2024, from RIPE Atlas probes — premise rewritten 2026-09-05.** ~~This overlaps the item above and supersedes its framing: it belongs in the write-up as context, not in the pipeline. What a storm did to a consumer internet service is the most relatable evidence there is that the orbits moved.~~ It is not evidence that the orbits moved, and must not be described as such: coincident network degradation has routing, ground-segment, ionospheric and demand explanations, and a plot against the Kp bar would invite a causal reading it cannot support. Any use of the RIPE Atlas record is a separate causal study — its own hypothesis, its own controls (non-Starlink probes over the same days, Starlink probes over quiet days), its own write-up — and if that study is ever done it is cited, not overlaid. Pull it once, if at all, for that study, and cite the probe ids.

## Phase 5. Money probes (ongoing)

Goal. Find out what, if anything, someone will pay for.

Do. Offer free screening reports to five small operators or university teams and ask what they would need before relying on it. Sketch a constellation risk index and show it to one insurer or investor. Look at South African and African grant routes: the continent has no comprehensive sovereign catalogue of its own, though it is not without sensors — a national space agency and DLR operate a debris-tracking telescope at Sutherland (corrected 2026-09-05; the earlier wording said independent tracking capacity was thin). Apply for roles or contracts at space situational awareness companies with the repository as the centrepiece.

Milestone. A clear answer on whether to keep building a product or to treat it as a portfolio piece and take the job.

## Successor projects (not to be built now)

Ideas large enough to be their own repository rather than a phase of this one. **Nothing here
starts before Phase 4 is published.** Recorded so they are not lost and not started early.

### Beyond Earth orbit: a cislunar and solar system companion

Extend the viewer outward from low Earth orbit to cislunar space and the solar system, plotting
**every human-made object beyond Earth orbit** — the deep space probes, the Lagrange point
observatories, the Mars and lunar orbiters, the derelict upper stages in heliocentric orbit, the
objects parked at the Earth–Moon Lagrange points. Ephemerides come from **NASA JPL Horizons**,
which is free, needs no account and serves state vectors for essentially every tracked body in
the solar system.

**A companion, not a phase.** It reuses driftwatch's rendering and time controls — the point
cloud, the frame budget, the scrubber, the replay machinery — and **shares no screening or
covariance code**. There are no conjunctions to screen out there, no element sets, no
consistency-derived covariance, and no storm term: the whole risk half of this project is
irrelevant to it. Sharing the viewer and nothing else is what makes it a separate repository
rather than a mode.

**What it actually needs, which is not what it looks like it needs.**

- **Nested coordinate systems.** Geocentric for Earth orbit, selenocentric for the lunar
  neighbourhood, barycentric for the solar system, with the transformations between them and a
  camera that knows which frame it is in. This is the real work, and it is the part that has
  nothing in common with anything driftwatch has built.
- **Logarithmic depth buffering.** A scene spanning from a 400 km orbit to Neptune is fourteen
  orders of magnitude, and an ordinary depth buffer collapses long before that.

**Explicitly out of scope for now: the observable-universe scale.** Stars, galaxies, large-scale
structure. It is a different problem again, and **Gaia Sky and OpenSpace already occupy that
ground** and do it far better than a side project would. The interesting, unoccupied gap is the
human-made objects between the Earth's surface and the outer planets, which is where this would
sit.

### Launch conjunction assessment

Screen a **nominal ascent trajectory** against the catalogue across a launch window and produce
what a launch operator actually wants: the **blocked intervals** inside the window, and the
objects responsible for each. It is the existing screening and probability code with **time as
the free variable** — instead of one trajectory over a week, it is the same trajectory offset by
every candidate lift-off time across the window, and the output is a set of intervals rather
than a set of events. Stages A to C, the covariance, the encounter plane and the flags all
carry over unchanged.

**Why it is distinctive here rather than a commodity, and it is the storm that makes it so.**
Blocked windows computed before a storm are **invalidated by catalogue displacement afterwards**:
the objects the analysis blocked around are not where the analysis put them, and a window cleared
on Monday is not cleared on Wednesday. That is the same in-track displacement driftwatch already
models — and the **storm-term validity split says how much of it is predictable**, object by
object. A launch conjunction assessment that reports which of its blocked intervals rest on
objects whose storm response is measured, and which rest on objects where it is not, is saying
something no existing tool says.

**The insertion case**, which is the sharp end: a vehicle **inserting at low altitude during a
storm** faces both elevated drag on its own initial orbit and a catalogue that has shifted
underneath it. That is the **February 2022 Starlink loss stated in prospective form** — the
validation case this project already reproduces, asked forwards instead of backwards.

**Explicitly out of scope: launch trajectory simulation itself.** Ascent flight dynamics —
staging, thrust profiles, aerodynamic loads, the trajectory's own construction — is a different
discipline and **RocketPy already serves it well**. This takes a nominal trajectory as input and
says nothing about how it was produced.

### Capability targets, not plans

Six things driftwatch cannot currently do, listed as capabilities to acquire rather than
features to build, because each one opens a class of work rather than a single deliverable.
**None of these begins before Phase 4 is published.**

The argument that connects them, and the reason they belong on this roadmap rather than
somebody else's: **solar radiation pressure above low Earth orbit is the same class of problem
as drag within it.** Both are a weakly known, non-gravitational force whose magnitude depends on
an object's area-to-mass ratio — the thing driftwatch already fits from an object's own decay —
and both are driven by the same solar activity. A project that has learned to say honestly which
objects its solar-driven perturbation model describes and which it does not is most of the way
to saying the same thing a hundred thousand kilometres further out.

1. **Numerical propagation, through Orekit or tudatpy.** The precondition for everything above
   geosynchronous orbit and everything beyond Earth orbit. SGP4 is an analytic theory fitted to
   a specific class of near-Earth orbit and it does not go where the next five items live.
   Nothing else on this list can start before this one.
2. **SPICE, through spiceypy.** NAIF's kernels are the standard for planetary ephemerides and
   for the frames that go with them, and they are the difference between guessing at a
   selenocentric frame and using the one everybody else uses.
3. **Orbit determination from observations.** The capability that would lift **the data ceiling
   this whole project currently sits under**. The dilution region, the empirical
   covariance fitted from element-set consistency, and the storm-term validity split are all
   consequences of taking somebody else's fitted orbits and inferring an uncertainty from how
   much they disagree. A real orbit determination produces a covariance from the fit itself,
   which is the single change that would move driftwatch from indicative toward operational.
4. **Ingestion of amateur optical and SatNOGS observations.** The motivation is the absence of a
   **comprehensive sovereign African catalogue** (corrected 2026-09-05: the earlier wording said
   the continent had no independent tracking, which is wrong — a national space agency and DLR operate a
   debris-tracking telescope at Sutherland): the large sensor networks are concentrated in the
   northern hemisphere and the Americas, a southern African longitude sees passes that few others
   measure, and what is measured here feeds no catalogue the region controls.
   This is the observational input that item 3 needs and the one place where being here rather
   than anywhere else is an advantage rather than a constraint.
5. **Cislunar conjunction screening.** An **unoccupied niche** — the traffic is growing, nobody
   publishes screening for it, and the three-body dynamics make it a genuinely different problem
   from the Earth-orbit case rather than the same one at a larger radius. Requires items 1 and 2.
6. **Near-Earth asteroid close approaches.** An adjacent public-interest application of the same
   propagation and close-approach machinery, against a population that is already public and
   already interesting to people who are not satellite operators.

## Validation cases

- The May 10 to 12, 2024 Gannon storm, the largest in two decades, poorly forecast even a day out, with heavy drag and mass Starlink manoeuvres.
- The February 3 to 4, 2022 Starlink loss to a minor storm at insertion altitude.
- The October to November 2003 Halloween storms, if Space-Track history allows, for the catalogue before the megaconstellations.
- The ESA Kelvins dataset for probability behaviour.

## Risks

- Public element sets are coarse. Position errors of hundreds of metres to kilometres mean absolute probabilities are indicative, not operational. Say so everywhere, and lean on relative changes and rankings, which is where the storm story lives anyway.
- Density models are uncertain by tens of percent even in quiet conditions. Treat NRLMSIS as a baseline and report its uncertainty rather than hiding it.
- CelesTrak and Space-Track have usage rules: cache, rate limit, and check the terms before redistributing raw data. Derived products are not covered by them.
- Scope creep toward a tracking company. You do not own sensors. Stay on the analysis layer.
- Browser performance with 30,000 points. Use typed arrays and instanced points, not one mesh per object.

## Definition of done

A stranger can open the site, pick a fleet, see this week's closest approaches on a globe, flip a switch to see what a G4 storm forecast does to them, scrub through May 2024 to watch it happen, read how it was calculated, and download the numbers. The repository has tests, the write-up has two validated storms, and at least one person who does this for a living has told you what is wrong with it.
