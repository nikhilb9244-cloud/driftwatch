# driftwatch

Conjunction screening for low Earth orbit that shows how geomagnetic storms change
collision risk. A storm heats the upper atmosphere, drag rises, predicted positions
drift along-track, and screening built on the public catalogue quietly gets worse at
the moment it matters most. driftwatch will screen a chosen fleet against the whole
catalogue and show how miss distances and probabilities move under quiet and stormy
conditions, live and in replay of past storms.

**Status: Phase 3 of 5 built** (the storm layer: space weather ingested with provenance,
NRLMSIS density along every orbit, a ballistic coefficient per object, the in-track storm
term derived and verified against a numerical integration, five scenarios rescoring stored
events, validation against the May 2024 Gannon storm and the February 2022 Starlink loss,
and a storm mode and May 2024 replay in the viewer). Phases 1 and 2 are complete. Phase 4 is
the visual pass and the operator console. See `ROADMAP.md` for the full plan,
`docs/phase3-plan.md` for the Phase 3 plan and every decision taken along the way, and
`docs/design-brief.md` for what Phase 4 will look like.

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
  explanation** the headline result had been given. A storm still lowers the probability on most
  events, but not through any cancellation between the two objects — the ratio is 1.91 out of a
  possible 2, so the two displacements are nearly independent. See `docs/storm-term.md`.
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

Cloudflare Pages, by direct upload. There is no CI and nothing scheduled: the automated
daily pipeline is Phase 4. One script does the four steps.

```powershell
pwsh -File scripts/deploy-pages.ps1 -DryRun        # export, build, check; stop before uploading
pwsh -File scripts/deploy-pages.ps1                # deploy to the `preview` branch
pwsh -File scripts/deploy-pages.ps1 -Branch main   # deploy to production
```

1. **Export a fresh bundle.** `driftwatch propagate --at <now>` writes the catalogue side
   (`manifest.json`, `objects.json`, `elements.bin`, `reference.bin`) and
   `driftwatch report latest` the conjunctions side (`conjunctions.json`,
   `conjunction-tracks.bin`). Neither rescreens. `-SkipExport` deploys what is already in
   `web/public/data`, `-Run` and `-Scenario` choose which stored run and scenario to show.
2. **Build.** `npm --prefix web run build`, which copies `public/` into `dist/`.
3. **Check what is about to be published**, over `dist/` rather than the source bundle,
   because the build is what ships:

   ```bash
   uv run driftwatch check-bundle --dir web/dist
   ```

   It refuses to continue if any file is a raw SpaceX ephemeris or a copy of the derived
   covariance store (analysis only, never redistributed — `docs/spacex-ephemerides.md`), if
   anything matches a credential pattern or the literal value of `SPACETRACK_USER`,
   `SPACETRACK_PASS` or `CLOUDFLARE_API_TOKEN` in the environment, or if any file is over
   Cloudflare Pages' 25 MiB limit. The rules are in `src/driftwatch/export/audit.py` and the
   tests in `tests/test_audit.py`.
4. **Upload.** `npx wrangler pages deploy web/dist --project-name driftwatch --branch <branch>`.
   Pages treats the project's production branch by name and gives every other branch its own
   preview URL, which is why the branch is an explicit argument rather than a flag.

Authentication is wrangler's: run `npx wrangler login` once, or set `CLOUDFLARE_API_TOKEN`
and `CLOUDFLARE_ACCOUNT_ID` in the environment. The first deploy creates the project if the
account has none by that name.

**Current sizes** (2 September 2026): 26 files, 22.9 MiB total, the largest being the 8.2 MiB
JavaScript source map, then `elements.bin` at 2.7 MiB and `conjunctions.json` at 2.6 MiB. Well
inside the 25 MiB per-file limit, so nothing is split or compressed; Pages serves gzip and
brotli itself, and `conjunctions.json` is 544 kB compressed. The source map is published
deliberately — the source is open, and it makes a bug report from a stranger legible.

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
scripts/                deploy to Cloudflare Pages, register the supplemental fetch task
fleets/                 YAML fleet definitions (the primaries to screen)
tests/                  pytest
docs/                   physics background, frames and time, data schema, methods, data sources, plans
web/                    Vite + TypeScript + globe.gl + satellite.js viewer
data/                   cache, snapshots, history, supplemental and SpaceX ephemeris versions,
                        conjunction runs (git-ignored)
```

## Docs

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
- `docs/data-sources.md`: each data provider's terms, the Space-Track redistribution
  clause as checked, and the citation format.
- `docs/spacex-ephemerides.md`: whether SpaceX's published Starlink ephemerides may be
  used and how, what their covariance actually is, and the plan for them.
- `docs/space-weather.md`: Kp and ap and why the table carries both, the feeds and their
  terms, how the sources are layered, and what is deliberately not filled in.
- `docs/density-and-drag.md`: NRLMSIS and how it is driven, the sampling step and its
  convergence, the ballistic coefficient and why B* is not one.
- `docs/phase2-plan.md`: the Phase 2 plan, the review decisions and the demo fleet.
- `docs/phase3-plan.md`: the Phase 3 plan and its review decisions.

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
