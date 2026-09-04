# driftwatch

Conjunction screening for low Earth orbit that shows how geomagnetic storms change
collision risk. A storm heats the upper atmosphere, drag rises, predicted positions
drift along-track, and screening built on the public catalogue quietly gets worse at
the moment it matters most. driftwatch screens a chosen fleet against the whole
catalogue every day and shows how miss distances and probabilities move under quiet and
stormy conditions, live and in replay of past storms.

## Findings and corrections

What this project has found, and what it has had to take back, in the order a reviewer should
read them. Every number here is reproduced from a stored run or a stored measurement named in
the linked page, and every correction carries its date. Written 2026-09-05, after an external
review found two correctness errors and a set of framing problems; the plan changed as a result
(`ROADMAP.md`, "Plan change").

### 1. The public catalogue's fit to an operator's ephemeris drifts from it by kilometres inside a day

CelesTrak publishes SGP4 element sets fitted to SpaceX's own Starlink ephemerides, with a fit
residual of about 0.20 km. That residual is measured over the arc the fit was made on, not over
the 72-hour file. Measured directly on nineteen matched files (2026-09-03), the propagated element
set sits this far from the published states, almost all of it along track:

| Lead from the file's start | under 12 h | 12 to 24 h | 24 to 36 h | 36 to 48 h | 48 to 60 h | 60 to 72 h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Median distance | 0.30 km | 2.8 km | 11.5 km | 28.3 km | 51.8 km | 82.9 km |

Two consequences were recorded rather than tidied away. Phase 2 had patched the gap with the 0.20 km
residual in quadrature and measured that the patch moved no flag; that measurement was true of the
patch and not of the error, which is a hundred times larger at the far end. And serving SpaceX's
published covariance on top of a trajectory 83 km away understated the uncertainty on the events
furthest ahead. So Stage C now screens on the published states themselves where they exist
(`docs/methods.md`, "Where an operator publishes states, those are the trajectory";
`docs/spacex-ephemerides.md`).

### 2. The published files are in a different frame from the one the catalogue uses, and only the filename says so

SpaceX's states are in MEME (J2000). The file header names the covariance frame and never the
states'. MEME is 0.36 degrees from TEME by 2026, about **44 km** at low Earth orbit radius: read as
TEME the states sit 36.2 km from CelesTrak's fit to the same file, rotated into TEME they sit
0.356 km away, which is the published residual. Getting this wrong would have introduced a 44 km
error in the course of removing a 0.2 km one, silently. Every fetch re-runs the comparison and
refuses to write the store if it fails (`docs/ephemeris-frame.md`).

### 3. Every published file has a seam at exactly 48 hours

Ten of ten files, then nineteen of nineteen: the position steps by a few hundred metres at
exactly 48 hours after the file's start, and the published velocity there disagrees with the
central difference of the positions by 16 m/s. It is at the same lead in every file, so it is not
a manoeuvre; the header labels the product `blend`, and two arcs joined at a fixed offset with no
attempt to match derivatives is the likely explanation. An interpolant must not span it, and any
use of these files that assumes one smooth 72-hour arc is wrong by a few hundred metres for part
of it (`docs/methods.md`, screening; `docs/spacex-ephemerides.md`).

### 4. The storm term has demonstrated skill for one population, at one end of the window

The in-track displacement a storm produces was measured against the May 2024 Gannon storm as a
forecast test: each object's last pre-storm element set propagated through the storm and compared
with the sets issued during it, against a quiet control at the same lead times
(`docs/storm-validation.md`).

- **It is predictive only where the ballistic coefficient was measured from the object's own
  decay** (correlation 0.88 over 422 comparisons), and has **no demonstrated skill** for an object
  carrying a B\* inversion or a population stand-in (correlation −0.10 over the free-flying
  population as a whole; a B\* coefficient regresses at slope −1.39). Every event therefore carries
  `storm_validity`, and every aggregate is reported over the validated events, the indicative ones
  and both, never both alone.
- **The skill is concentrated at three to four days of lead and is near zero inside two**
  (recomputed 2026-09-05). On the validated population the observed sign agrees with the
  predicted one on 39 and 41 per cent of comparisons at one and two days, chance being 50, and on
  91 and 96 per cent at three and four; the robust slope is −0.15 and −0.04 inside two days
  against 0.63 and 0.71 beyond. The quiet-time propagation error is already 10 km at three days,
  and a predicted storm shift of 2 to 5 km at one or two days is inside it. A storm forecast one
  or two days out is an uncertainty on an event, not a correction to it.
- **NRLMSIS 2.1 over-predicts the storm's three-day density enhancement by about 22 per cent**
  over 450 to 2,000 km with no resolvable altitude dependence, in the opposite direction to the
  published accelerometer assessments, which measure a different quantity (the peak, at a point).
  Recorded and deliberately not applied; a test pins the untuned prior.
- **Corrected 2026-09-05: the term must not be applied to operator-controlled objects.** A
  trajectory that is the operator's — SpaceX's published states, or CelesTrak's fit to them —
  already carries the operator's drag model and planned burns, so the excess over SGP4's
  atmosphere is undefined for it, and a station-kept satellite will burn rather than drift.
  Before the correction every object with a coefficient was displaced, which put shifts of up to
  31,000 km on Starlinks whose supplemental B\* described a thrusting plan and reported their
  events as "outside the linear theory" — 42 objects on the 1 September run, 36 on the
  3 September one, every one a Starlink, and explained at the time as a physical population in
  the densest shell. That explanation was wrong: it was this category error seen from the other
  side. Such objects now get no mean shift, are labelled `operator-controlled`, and an event with
  one such side is judged on its free-flying side alone (`docs/storm-term.md`, "Corrected
  2026-09-05"). Rescored, the 3 September run has no unscoreable event; its `forecast` tally moved
  from 0 red, 16 yellow and 71 unscoreable to 1 red, 19 yellow and none, and the storm scenarios
  likewise, the one red being the dilution-region flag in item 5.

### 5. Two headlines were falsified, and both corrections are dated

**"A storm lowers the probability on most events, because the two objects are displaced alike."**
Falsified twice. The explanation, common-mode cancellation, went on 2026-09-03: the diagnostic
built to test it found the relative displacement that reaches the miss to be a median **1.91
times** the mean of the two objects' own displacements, out of a possible 2, flat across
coefficient sources and across the altitude difference between the two orbits, because a
conjunction is a crossing at a median 120° between the two in-track directions. The result itself
went on 2026-09-05: the lowering — a median `pc / pc_variance_only` of 0.16 to 0.40 on the
validated events — lived entirely in events with an operator-controlled side, displaced by the
category error in item 4. On the 981 events of the 3 September run with both objects free-flying,
whose displacements were legitimate and which the correction did not touch, the probability is
lowered on 55 and raised on 43 under a G5, at a median ratio of 0.98. What is measured now is
narrower: on this fleet the storm term moves a free-flying event's probability little either way
(median relative displacement 2 to 7 km against covariances of kilometres to tens of kilometres),
the two displacements of a free-flying pair are nearly independent (1.85 of 2), and no general
claim about the direction should be made until a fleet with low free-flying primaries has been
screened through a real storm (`docs/storm-term.md`, "Attacking the result" and "Corrected
2026-09-05").

**"Screening on the operator's own published states gives the demo fleet its one red flag."** The
flag exists — EOS SAT-1 (shown on the public page as `payload 55053`) against Starlink 61705,
2.780 km at a fifteen-hour lead, probability 1.076 × 10⁻⁴ against 6.19 × 10⁻⁶ on the catalogue's
fit — and the write-up quoted it as a red. Corrected 2026-09-05: it is **in the dilution region at
low confidence**, with its maximum probability over covariance scale factors at 0.85 times the
covariance in hand, so the number is held up by the size of the uncertainty rather than by the
geometry and is not an actionable warning. Every mention now leads with the region and the
confidence, in the notes, the report and the viewer. What survives is that the choice of
trajectory moved a dilution-region probability across the red threshold at a fifteen-hour lead,
which the term Phase 2 carried for that choice could not have done (`docs/writeup-notes.md`).

Everything above is indicative, not operational: the covariances come from the consistency of
public element sets, which is a floor on the error rather than a measurement of it, and the
probabilities are computed by the two-dimensional method, which is a known underestimate for slow
encounters. `docs/methods.md` lists every approximation, with the precedent this rests on
(Flohrer, Krag and Klinkrad, 2008; Parker and Linares, 2024) and what is done differently.

**Status: Phases 1 to 3 built; Phase 4 stops at the pipeline** (a daily GitHub Actions run that
fetches, screens, scores every scenario, publishes to Vercel and keeps every run). The landing
page, the export, the visual pass, the parked research items, the write-up and the Office of
Space Commerce validation are deferred indefinitely, because they change nobody's decision while
no operator uses the output; they are replaced by this page and by a Conjunction Data Message
parser and matcher (`docs/cdm-matching.md`), which is what turns the first operator conversation
into a measurement. `docs/state-of-play.md` is where a fresh session starts; `ROADMAP.md` has the
plan and the change to it.

What works today:

- `driftwatch fetch` downloads the CelesTrak catalogue groups politely (cached, at most
  one request per group every two hours), joins SATCAT object types, classifies every
  object and writes a dated parquet snapshot.
- `driftwatch propagate --at <time>` runs SGP4 over the whole snapshot, converts TEME to
  the Earth-fixed ITRS frame and to WGS84 latitude, longitude and height, writes a
  parquet state file, and exports a compact bundle for the viewer.
- The viewer renders every object on a globe as one GPU point cloud, runs SGP4 in a Web
  Worker (satellite.js, WebAssembly) so a 48-hour window can be scrubbed and played, filters
  by category and altitude band, and shows details on hover. It reports the disagreement
  between its own SGP4 and the Python reference state at the reference time.
- `driftwatch fleet fleets/demo.yaml` validates a fleet definition (NORAD ids, hard-body
  radii with their provenance, manoeuvre flags) and shows each member as the latest
  snapshot knows it. The demo fleet is the ISS, Sentinel-1C, two university cubesats and
  the two active South African objects.
- `driftwatch screen --fleet fleets/demo.yaml --days 7` screens the fleet against the
  whole catalogue in three stages (apogee/perigee overlap, coarse time stepping with a
  step and threshold chosen so nothing inside the screening volume can be missed, and
  root-finding on the range rate), using CelesTrak's supplemental Starlink sets for
  Starlink secondaries; then backfills 45 days of Space-Track element-set history for
  the fleet and every surviving secondary, fits each object's position uncertainty from
  the disagreement between its own element sets (with a pooled fallback per category and
  altitude band, and a labelled prior below that), checks the history for unexplained
  orbit raises, and computes the probability of collision on the encounter plane by
  Foster's integration with Alfano's form as a cross-check, the maximum probability over
  covariance scale factors, and red/yellow flags at the ISS thresholds. Everything goes
  into a run directory under `data/conjunctions/`: the geometry, the objects, the
  covariance model, one risk file per scenario and the joined export. The demo fleet's
  week takes about four minutes plus the history backfill on a laptop.
  Every event is labelled `robust` or `dilution` by where the maximum probability sits:
  a flag in the dilution region is reported at low confidence and never as actionable,
  because shrinking the covariance would raise it.
- `driftwatch risk <run> --scenario <name>` rescores a stored run's events with another
  covariance model without rescreening (today a scale factor; Phase 3's storm model
  uses the same interface), so a quiet row and a storm row for the same event sit side
  by side in the export.
- `driftwatch storm-check <run>` attacks the storm result rather than reporting it. It splits
  the relative-to-absolute shift ratio by ballistic coefficient source and by the altitude
  difference between their two orbits — the first says whether the pair's shifts are alike only
  because their coefficients came from the same rule, the second is the physical prediction,
  since the density falls by an order of magnitude every 50 km and two objects far apart in
  altitude cannot see the same excess — puts the combined, shift-only and variance-only
  probabilities side by side over probability
  bands, and names the objects whose storm term ran outside the linear theory. Those events carry
  no probability at all: `unscoreable`, with the reason on the row and excluded from every
  aggregate. It did its job twice: it excluded the artefact, and then it **falsified the
  explanation** the headline result had been given — the relative-to-absolute ratio is 1.85 out
  of a possible 2 over the free-flying pairs, so the two displacements are nearly independent.
  What it could not find was that the result itself rested on displacing operator-controlled
  objects; an external review did (2026-09-05), and the ratio is now taken over free-flying
  pairs only. See `docs/storm-term.md`.
- Every aggregate the tool prints is reported **twice**: over the events whose two objects both
  have a ballistic coefficient measured from their own decay (`validated`), and over the rest
  (`indicative`). Step 4 measured the storm term against May 2024 and found it predictive at
  r = 0.88 with a measured coefficient and of no demonstrated skill without one, so the split is
  the difference between a measurement and an extrapolation. `storm_validity` is on every row.
- `driftwatch snapshot-as-of --date <when>` rebuilds the catalogue as it stood on a past date
  from `gp_history`, taking each object's newest element set **at or before** that date and
  nothing later, bounded by an altitude range or a launch's international designator to keep the
  pull proportionate. Cached permanently under `data/snapshots/as-of/`.
- `driftwatch validate gannon` and `driftwatch validate starlink-2022` measure the storm term
  against the record. See below.
- `driftwatch stability <run>` adds a scored run to the warning-stability index -- one narrow
  file per run on the pipeline's store branch, holding each encounter's identity, miss distance
  and probability. `driftwatch stability --pair 55053,61705` reads one encounter's history back:
  how a warning moved run to run, without opening a month of run archives. The index is written;
  no analysis of it is.
- `driftwatch report <run>` writes the weekly markdown report and the viewer's
  conjunction bundle. Repeated encounters of one pair are collapsed to a single row with
  the event count, the closest miss, the highest probability and the first time of
  closest approach, expanding to the individual events on demand, with a cumulative
  probability per pair labelled as the upper bound it is.
- The viewer's conjunctions panel lists those pairs. Selecting an event jumps the clock
  to the time of closest approach, highlights both objects, draws ten minutes of each
  track either side and opens an inset of the encounter plane with the covariance
  ellipse, the hard-body disc, the miss vector and the probabilities. Every number is
  Python's; the browser computes no screening result.
- **Storm mode** switches the panel between `quiet`, `forecast` and the three synthetic storm
  levels. Every row then carries the miss and probability *under that scenario*, its region and
  confidence, whether the storm term is validated or indicative for it, and `Δ vs quiet` as a
  multiplier — on every row, not only the interesting ones, so the phase's result is learnt from
  the screen. The detail view adds the pre-storm miss, the relative displacement, the shift-only
  and variance-only probabilities, and the quiet ellipse behind the scenario's with an arrow
  between the two misses. Events the storm term cannot score sit in their own section below the
  queue with the reason, never in the queue with a blank. **The control changes numbers in the
  panel and nothing else** — the point cloud, the worker and the tracks are geometry and do not
  depend on the scenario, which is what keeps Phase 1's frame budget.
- **Replay mode** swaps the catalogue for the one that existed on 9 May 2024, that run's own
  screening under the observed record, and a timeline — **without leaving the page**. The Kp bar is
  the background of the scrubber, the density ratio at 400 and 500 km is drawn over it, the Sun in
  SDO/AIA 193 Å sits beside it, and all of them plus the objects read the one simulation clock, so
  scrubbing moves everything together by construction. The camera, the selected object, the
  filters, the playback speed and the position through the window all carry across; the scenario
  is remembered per mode, so leaving replay puts a G5 back. `?replay` still goes in the address
  bar, so a replay is a link and the Back button leaves it, and nothing of the replay bundle is
  fetched until somebody asks for it.
- `driftwatch replay-bundle <run>` writes that timeline: the observed Kp and ap with their
  provenance, the density ratios against the same quiet control window Step 4 measured the
  enhancement against, and a few Sun frames a day from Helioviewer with the lag between the time
  asked for and the image actually returned on each. Each frame is fetched at two sizes — the full
  512 px image as a file and a 32 px thumbnail inlined in the timeline — so the viewer has a
  placeholder everywhere on the scrubber and fetches the 360 kB frames only as the playhead
  reaches them.
- `driftwatch supplemental` fetches CelesTrak's operator-ephemeris element sets, stores
  the version, thins versions older than a fortnight to one a day, and with `--fit`
  refits the supplemental covariance across the whole store. It runs every three hours
  from a scheduled task, because that covariance is measured from the consistency of
  successive versions and CelesTrak keeps only the latest one.
- `driftwatch kelvins` reproduces the risk column of ESA's Kelvins Collision Avoidance
  Challenge data from its own inputs. The hard-body radius ESA used turns out to be in
  the data: with the combined radius taken as `(t_span + c_span) / 2` and nothing fitted,
  the 162,634-row training set is reproduced to a median residual of 0.07 % with 87 % of
  the high-risk tail within a factor of two (`docs/kelvins-reproduction.md`).
- `driftwatch cdm match <run> --cdm <dir>` reads an operator's Conjunction Data Messages
  (CCSDS 508.0-B-1, KVN or XML), matches them to a stored run's events on the object pair and
  a ten-minute TCA tolerance, and reports which operator-warned conjunctions public data found
  and at what miss and probability, which it missed, and which public-data flags the operator
  never received. Built against the Kelvins rows as test input, which `driftwatch cdm
  from-kelvins` writes out as messages with synthetic identities (`docs/cdm-matching.md`).
- Tests cover the official SGP4 verification cases, frame conversions against skyfield,
  a real ISS pass over Durban, the cache rules, the snapshot schema, the export, the
  Space-Track client, the fleet files, the screening (synthetic conjunctions with a
  designed time and miss distance recovered to a millisecond and a metre, and the coarse
  step checked against one-second brute force), the probability of collision (closed
  forms, brute-force quadrature, the three integrators against each other, the dilution
  maximum), the covariance fit and the manoeuvre detector on synthetic element-set
  histories, the history index and batched backfill, the scenario mechanism end to end, the
  storm term's closed form against an independent Runge-Kutta integration and its sign against a
  case where the answer is obvious, the refusal to score an event whose displacement has left
  the linear theory, the thrust ceiling on a satellite fitting above what its own geometry
  allows, the loud failure of a weather table that does not reach the oldest element-set epoch
  in a run, the historical snapshot builder's refusal to use an element set from after the date
  it reconstructs, Step 4's own measurements, the storm-term validity label and the promise that
  it changes no number, the storm-response prior's value (so the measured 22 per cent
  over-prediction cannot quietly become a calibration), and Step 5's exports: the scenario
  overlay's columns staying parallel to the bundle's own order, an unscoreable event carrying
  null rather than a small number, every aggregate present both ways, and the refusal to build a
  replay timeline whose density baseline does not reach the quiet control window.

## Quick start

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
uv sync                                   # Python environment
export SPACETRACK_USER=you@example.org    # optional: Space-Track login for the full catalogue
export SPACETRACK_PASS=...                #   (PowerShell: $env:SPACETRACK_USER = "..."). Never put these in a file.
uv run driftwatch fetch                   # ~30 s; CelesTrak groups + Space-Track gp, writes data/snapshots/gp_<stamp>.parquet
uv run driftwatch propagate --at 2026-09-01T12:00:00Z
                                          # ~3 s; writes data/propagated/state_<stamp>.parquet
                                          # and web/public/data/{manifest.json,objects.json,elements.bin,reference.bin}
uv run driftwatch fleet fleets/demo.yaml  # check the demo fleet against the snapshot
uv run driftwatch screen --fleet fleets/demo.yaml --days 7
                                          # ~4 min + the history backfill; writes data/conjunctions/demo_<stamp>/
uv run driftwatch risk latest --scenario test --scale 3
                                          # rescore the same events with every covariance tripled
uv run driftwatch spacex latest           # optional: SpaceX's own covariance for the run's Starlink
                                          #   secondaries, inside their 72-hour horizon
uv run driftwatch weather --days 7        # space weather for the window, with its provenance
uv run driftwatch density                 # NRLMSIS sanity check: quiet density and the storm ratios
uv run driftwatch ballistic latest        # a ballistic coefficient per object, from decay or B*
uv run driftwatch risk latest --scenario storm-g5
                                          # rescore under a synthetic G5 built from May 2024
uv run driftwatch storm-check latest      # attack the storm result; name what cannot be scored
uv run driftwatch stability latest        # index the run for warning stability (the pipeline does this daily)
uv run driftwatch stability --pair 55053,61705
                                          # read one encounter's history back across runs
uv run driftwatch validate gannon         # measure the term against the May 2024 storm

# The May 2024 replay the viewer's `?replay` mode reads.
uv run driftwatch propagate --snapshot data/snapshots/as-of/gp_asof_20240509T000000Z.parquet \
    --at 2024-05-09T00:00:00Z --export-dir web/public/data/replay
uv run driftwatch report demo-2024_20240509T000000Z --scenario replay:2024-05-09 \
    --out-dir web/public/data/replay
uv run driftwatch replay-bundle demo-2024_20240509T000000Z
uv run driftwatch report latest           # weekly report + the viewer's conjunctions bundle
cd web && npm install && npm run dev      # open the printed URL
```

To publish it, see [Deploying the viewer](#deploying-the-viewer).

`uv run driftwatch snapshots` lists what has been fetched. `--offline` on `fetch`
rebuilds the snapshot from cache without touching the network; `--spacetrack off` skips
Space-Track and `--spacetrack on` fails without it (the default uses it when the
credentials or a cache are present). `uv run driftwatch history --ids 25544,39634
--start 2024-05-01 --end 2024-05-20` pulls every element set for those objects from
Space-Track's `gp_history` into `data/history/`; `screen` does the same for the fleet
and its surviving secondaries by itself (`--history off` skips it, `--history on` insists
on it). Run `uv run pytest` for the tests (the first run downloads IERS Earth-orientation
data for astropy, about 3 MB).

## Deploying the viewer

Vercel, from 2026-09-05: team `nikolodeon-s-projects`, project `driftwatch`, root directory
`web`, framework Vite, with the GitHub repository **disconnected**, so nothing builds on a push.
Two things deploy and nothing else does: the daily pipeline (`.github/workflows/pipeline.yml`,
production) and the hand-run script below (a preview by default). Both build the same way and
check the same bytes. Every deployment sits behind Vercel Authentication until a custom domain is
attached or the protection is changed (`docs/pipeline.md`, "Hosting").

```powershell
pwsh -File scripts/deploy-vercel.ps1 -DryRun                    # export, build, check; stop before uploading
pwsh -File scripts/deploy-vercel.ps1 -Run <run> -Scenario quiet  # a preview deploy with its own URL
pwsh -File scripts/deploy-vercel.ps1 -Production -Run <run> -Scenario quiet
```

1. **Export a fresh bundle.** `driftwatch propagate --at <now>` writes the catalogue side
   (`manifest.json`, `objects.json`, `elements.bin`, `reference.bin`) and `driftwatch report`
   the conjunctions side (`conjunctions.json`, `scenarios.json`, `conjunction-tracks.bin`).
   Neither rescreens. `-SkipExport` deploys what is already in `web/public/data`; `-Run` and
   `-Scenario` choose which stored run and scenario to show. On the public page, fleet members
   other than stations appear by category and NORAD id, not by name, until their operator has
   agreed to appear.
2. **Build with the Vercel CLI.** `vercel pull` fetches the project settings and `vercel build`
   runs the Vite build locally into `.vercel/output/`. Building here and deploying prebuilt is
   what lets the next step check exactly the files that will be served.
3. **Check what is about to be published**, over the prebuilt output:

   ```bash
   uv run driftwatch check-bundle --dir .vercel/output
   ```

   It refuses to continue if any file is a raw SpaceX ephemeris or a copy of the derived
   covariance store (analysis only, never redistributed — `docs/spacex-ephemerides.md`), if
   anything matches a credential pattern or the literal value of `SPACETRACK_USER`,
   `SPACETRACK_PASS` or `VERCEL_TOKEN` in the environment, or if any file is over the 25 MiB
   per-file ceiling (Cloudflare Pages' upload limit, kept as the project's own). The rules are in
   `src/driftwatch/export/audit.py` and the tests in `tests/test_audit.py`.
4. **Upload.** `vercel deploy --prebuilt`, with `--prod` for production. Vercel builds nothing.

Authentication is the Vercel CLI's: `npx vercel login` once on a machine, or `VERCEL_TOKEN` with
`VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` in the environment, which is how the pipeline runs it.
The pipeline names a missing secret before it builds anything.

**Retired: Cloudflare Pages.** The project `driftwatch` and <https://driftwatch-2wg.pages.dev>
are retired; they last served the 2026-09-03 run under the uncorrected storm term.
`scripts/deploy-pages.ps1` stays, marked retired, until the first Vercel production deploy has
succeeded. `docs/pipeline.md` has the deploy design and why the host changed.

**Current sizes** (5 September 2026): the prebuilt output is 31 MiB in all, the largest files
`elements.bin` at 2.7 MiB and `conjunctions.json` at about 3 MiB, well inside the 25 MiB per-file
ceiling. Source maps are not published (`web/vite.config.ts`).

## What you are looking at

Each point is one catalogued object at the time on the clock, coloured by category:
space stations, Starlink, OneWeb, other constellations, other payloads, rocket bodies,
debris, unknown. The slider spans 24 hours either side of the reference time. Hover for
name, altitude and position; click or search to pin an object.

Positions come from public two-line element sets propagated with SGP4. They are good to
hundreds of metres to a few kilometres near the element-set epoch and drift by kilometres
per day, more in a storm. The viewer's Earth-fixed frame ignores UT1 and polar motion,
which costs under a pixel. Everything approximate is listed in `docs/methods.md`.

Coverage is the CelesTrak groups (operational payloads, stations, the Starlink and
OneWeb constellations, recent launches and the three largest debris clouds), roughly
19,000 objects, merged with Space-Track's full `gp` catalogue when a login is available,
which adds the older rocket bodies and the rest of the tracked debris. Each object keeps
its freshest element set and records which source it came from.

## Layout

```
src/driftwatch/         Python package (CLI: driftwatch)
  catalogue/            CelesTrak and Space-Track fetch, SATCAT, classification, parquet snapshots, history
  orbit/                time, SGP4 propagation, frame conversions
  screening/            three-stage conjunction screening, RIC frame, supplemental Starlink sets
  ephemeris/            operator-published ephemerides (SpaceX's Starlink covariance)
  weather/              space weather: CelesTrak SW-All, NOAA SWPC, the three-hourly table, Sun imagery
  drag/                 NRLMSIS density along an orbit, and the ballistic coefficient per object
  risk/                 covariance model and fit, manoeuvre flag, probability of collision, scenarios, Kelvins
  export/               viewer bundle, conjunction run directory, weekly report, pre-deploy audit
  cdm/                  CCSDS Conjunction Data Messages: parser, matcher, the Kelvins test adapter
scripts/                deploy to Vercel (deploy-vercel.ps1; deploy-pages.ps1 is retired), register the supplemental fetch task
fleets/                 YAML fleet definitions (the primaries to screen)
tests/                  pytest
docs/                   physics background, frames and time, data schema, methods, data sources, plans
web/                    Vite + TypeScript + globe.gl + satellite.js viewer
data/                   cache, snapshots, history, supplemental and SpaceX ephemeris versions,
                        conjunction runs (git-ignored)
```

## Docs

- `docs/state-of-play.md`: **start here to resume the work.** Where Phase 4 stands step by
  step, what is committed and what has never run, the open items, and the ceilings.
- `docs/tle-and-sgp4.md`: what a TLE is, mean versus osculating elements, what SGP4
  does, and the accuracy limits of the public catalogue.
- `docs/frames-and-time.md`: TEME, ITRS, GMST, UT1 and polar motion, and the measured
  cost of the browser's shortcut.
- `docs/data-schema.md`: every column in the snapshot, state, conjunction and viewer files.
- `docs/screening.md`: the three screening stages, the step-and-threshold derivation
  with its brute-force proof, what an event's numbers mean; then the covariance from
  element-set consistency and why it is a floor, the manoeuvre flag, the encounter
  plane, the three probability integrators, the dilution maximum and the flags.
- `docs/methods.md`: the running list of approximations.
- `docs/kelvins-reproduction.md`: the ESA Kelvins reproduction as the command writes it,
  with `docs/kelvins-reproduction.svg`, the residual against ESA's risk.
- `docs/cdm-matching.md`: the Conjunction Data Message parser and matcher, what the three
  outputs mean, and why the Kelvins rows are its test input and not a validation.
- `docs/data-sources.md`: each data provider's terms, the Space-Track redistribution
  clause as checked, and the citation format.
- `docs/spacex-ephemerides.md`: whether SpaceX's published Starlink ephemerides may be
  used and how, what their covariance actually is, and the plan for them.
- `docs/space-weather.md`: Kp and ap and why the table carries both, the feeds and their
  terms, how the sources are layered, and what is deliberately not filled in.
- `docs/density-and-drag.md`: NRLMSIS and how it is driven, the sampling step and its
  convergence, the ballistic coefficient and why B* is not one.
- `docs/pipeline.md`: the daily run — the runtime budget, where each piece of state lives
  and why, the retention rule and the failure model.
- `docs/phase2-plan.md`: the Phase 2 plan, the review decisions and the demo fleet.
- `docs/phase3-plan.md`: the Phase 3 plan and its review decisions.
- `docs/phase4-plan.md`: the Phase 4 plan and its review decisions, with
  `docs/writeup-notes.md` accumulating the findings the write-up has to name.

## Data sources and their rules

- [CelesTrak](https://celestrak.org) GP element sets and SATCAT. No account. Their rule
  is one fetch per group per two hours with a descriptive User-Agent; the fetcher
  enforces both and caches everything. Set `DRIFTWATCH_CONTACT` to add a contact
  address to the User-Agent.
- [Space-Track](https://www.space-track.org) `gp` catalogue and `gp_history`. Free
  registration. Credentials are read from `SPACETRACK_USER` and `SPACETRACK_PASS` and
  never written to disk or logs. The client stays under Space-Track's limits (fewer than
  30 requests a minute and 300 an hour), pulls the catalogue at most every two hours and
  four times a day, and never repeats a history request. Their user agreement grants
  blanket approval to redistribute basic SSA data (element sets, SATCAT and decay data)
  with citation, which the viewer bundle carries; conjunction messages and the emergency
  and advanced tiers are not covered and are never fetched. See `docs/data-sources.md`
  for the quoted text, the date it was checked and the citation format.

- [SpaceX Starlink ephemerides](https://api.starlink.com/public-files/ephemerides/). No
  account, no stated licence, published so that other operators can screen against
  Starlink. driftwatch uses their covariance for Starlink secondaries inside the 72-hour
  horizon of each file. Because no licence is stated the rule is **analysis only**: the
  raw files are never redistributed, only one satellite's file is fetched per satellite a
  run actually needs, and the store holds a thinned covariance series rather than the
  file. See `docs/spacex-ephemerides.md` and `docs/data-sources.md`.

- [NOAA SWPC](https://services.swpc.noaa.gov) space weather forecasts and the L1 solar
  wind, and [CelesTrak's `SW-All.csv`](https://celestrak.org/SpaceData/) for the observed
  record. Both public and free of account. Every forecast is stored under the time it was
  **issued**, so a stored run can be rescored against the forecast it actually used.
- [Helioviewer](https://helioviewer.org) for Sun imagery in the storm replay. Public API,
  credit given in `config.HELIOVIEWER_CITATION`; the images are NASA/SDO products.

## Licence

MIT. See `LICENSE`.
