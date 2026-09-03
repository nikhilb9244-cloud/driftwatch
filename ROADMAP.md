# driftwatch roadmap

Working name, rename freely. This file is written to live in the repository so the coding agent can read it at the start of every phase.

## The idea

A geomagnetic storm heats the upper atmosphere, density rises, drag on every low Earth orbit object increases, and predicted positions drift, mostly along the direction of travel. Conjunction screening built on the public catalogue quietly gets worse at the moment it matters most. driftwatch screens conjunctions for a chosen fleet against the whole catalogue, then shows how miss distances and collision probabilities change under quiet and stormy conditions, both live and in replay of past storms. The end product is a public site, an open repository, a validated write-up and a portfolio piece aimed at the space situational awareness industry.

## What you need before you start

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
- ESA's Kelvins Collision Avoidance Challenge dataset, around 160,000 anonymised real conjunction messages, for checking your probability calculations against how operators score risk.
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

Write. A short paper or a long blog post covering the problem, the method, the two validation storms, and what the tool gets right and wrong. Publish it and send it to a few people at SANSA, the SKA Observatory, a university satellite group and two space situational awareness companies, asking for criticism rather than praise.

Milestone. Site live, repository public, write-up published, five pieces of outside feedback received.

Parked for this phase (added 2026-09-02 at the Phase 2 Step 1 review; not to be built before Phase 4):

- ~~**Stage C should interpolate the SpaceX ephemeris states directly for served events, so the trajectory and the covariance share a source.**~~ **Built, Phase 4 Step 1, 2026-09-03** — and it was a bigger item than this entry supposed. The 0.2 km figure is CelesTrak's fit residual over the arc the fit was made on, not over the file: measured on nineteen matched files, the propagated element set sits a median 0.30 km from the published ephemeris inside 12 hours but **2.8 km at 12 to 24, 28 km at 36 to 48 and 83 km at 60 to 72**, almost all in-track. Three consequences. The Phase 2 patch was the right shape at a hundredth of the right size at the far end of the horizon. Serving SpaceX's 3.8 km control box on a trajectory 83 km out **understated** the uncertainty on the events furthest ahead. And "a decision about what Stage B screens on" had only one defensible answer: Stage B screens on the published states too, because no pad covers 83 km. The states are stored on a 120-second grid (measured interpolation error: median 5.7 m, maximum 6.8 m), rotated out of the files' MEME/J2000 frame into TEME (44 km if you get that wrong), and split at every discontinuity — every file carries one at exactly 48 hours. The fit residual now applies per event rather than globally. See `docs/phase4-plan.md` and `docs/spacex-ephemerides.md`.
- A live impacts panel in the viewer driven by NOAA's R (radio blackout), S (solar radiation storm) and G (geomagnetic storm) scales, read from the SWPC JSON feeds that Phase 3 already pulls for Kp, so a visitor sees the current and forecast scale levels next to the conjunction list.
- An overlay for the May 2024 storm replay showing Starlink round-trip times from public RIPE Atlas probes on Starlink connections, plotted against the Kp bar, so the replay shows what the storm did to a user-facing service alongside what it did to the orbits.

Parked for this phase (added 2026-09-02 at the Phase 3 Step 2 review; not to be built before Phase 4):

- **A commandability column on every event: the interval between the fleet member's last ground contact and the time of closest approach.** A probability is only actionable if somebody can act on it, and for a small operator with one or two ground stations the binding constraint is often not the number but whether there is a pass between now and the encounter. It needs ground station coordinates in the fleet YAML (latitude, longitude, altitude, and a minimum elevation), a pass predictor over the screening window, and a column giving the hours from the last usable pass to the TCA — with the honest note that a pass is an opportunity to command, not a guarantee of one.
- **Manoeuvre burden: the count of events crossing an operator's action threshold under each storm scenario, against quiet.** The single number an operator recognises. Phase 3 already produces every input — the scenarios, the per-event probabilities and the flags — so this is a summary over the risk tables rather than new physics, and it turns "the probabilities moved" into "you would have had to plan four burns instead of one". Report it per fleet member and per scenario, and say plainly that the threshold is the operator's to choose.
- **Lifetime loss per storm, for every low object, from the density model.** The same ballistic coefficient and density track that Step 3 already computes, integrated to a re-entry rather than to a time of closest approach: how many days of remaining life a G3, G4 or G5 costs an object at 300, 400 and 500 km. It is the most legible consequence of a storm for a general reader, it needs no new data, and it is a natural figure for the Phase 4 write-up. Watch the same limit Step 3 hit — the linear theory does not survive a decay this large, so this one has to integrate rather than extrapolate.
- **Illuminated satellites over southern African sites, per night, with growth over years.** Two related counts: satellites above a chosen elevation at Sutherland (the South African Astronomical Observatory) that are sunlit while the sky at the site is in astronomical twilight or darker, and satellites above the horizon at the SKA core site in the Karoo. Both are a shadow-geometry calculation on the propagated catalogue and nothing more, and both answer a question the astronomy community here is actively arguing about. Run over several years of historical snapshots it gives the growth curve, which is the part that is hard to dispute.
- **A Hermanus magnetic field rate-of-change panel, from INTERMAGNET, with a threshold.** SANSA's Hermanus observatory is an INTERMAGNET station, so the one-minute magnetogram is public. dB/dt is the quantity that drives geomagnetically induced currents, and a panel showing it against a stated threshold puts a local, ground-level measurement beside the orbital story — the same storm, seen from the other end. Check INTERMAGNET's attribution and licensing conditions before anything is redistributed; the data are free but conditioned.
- **A Starlink latency and loss overlay for the May 2024 replay, from RIPE Atlas probes.** This overlaps the item above from the Phase 2 Step 1 review and supersedes its framing: it belongs in the **write-up as context**, not in the pipeline. What a storm did to a consumer internet service is the most relatable evidence there is that the orbits moved, but it is a different measurement with different provenance, and wiring it into the conjunction pipeline would blur what the tool is claiming to compute. Pull it once, plot it against the Kp bar in the paper, cite the probe ids.

## Phase 5. Money probes (ongoing)

Goal. Find out what, if anything, someone will pay for.

Do. Offer free screening reports to five small operators or university teams and ask what they would need before relying on it. Sketch a constellation risk index and show it to one insurer or investor. Look at South African and African grant routes, since independent tracking and analysis capacity on the continent is thin. Apply for roles or contracts at space situational awareness companies with the repository as the centrepiece.

Milestone. A clear answer on whether to keep building a product or to treat it as a portfolio piece and take the job.

## Validation cases

- The May 10 to 12, 2024 Gannon storm, the largest in two decades, poorly forecast even a day out, with heavy drag and mass Starlink manoeuvres.
- The February 3 to 4, 2022 Starlink loss to a minor storm at insertion altitude.
- The October to November 2003 Halloween storms, if Space-Track history allows, for the catalogue before the megaconstellations.
- The ESA Kelvins dataset for probability behaviour.

## Risks

- Public element sets are coarse. Position errors of hundreds of metres to kilometres mean absolute probabilities are indicative, not operational. Say so everywhere, and lean on relative changes and rankings, which is where the storm story lives anyway.
- Density models are uncertain by tens of percent even in quiet conditions. Treat NRLMSIS as a baseline and report its uncertainty rather than hiding it.
- CelesTrak and Space-Track have usage rules. Cache, rate limit, and check the terms before redistributing raw data. Derived products are yours.
- Scope creep toward a tracking company. You do not own sensors. Stay on the analysis layer.
- Browser performance with 30,000 points. Use typed arrays and instanced points, not one mesh per object.

## Definition of done

A stranger can open the site, pick a fleet, see this week's closest approaches on a globe, flip a switch to see what a G4 storm forecast does to them, scrub through May 2024 to watch it happen, read how it was calculated, and download the numbers. The repository has tests, the write-up has two validated storms, and at least one person who does this for a living has told you what is wrong with it.
