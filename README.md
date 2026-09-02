# driftwatch

Conjunction screening for low Earth orbit that shows how geomagnetic storms change
collision risk. A storm heats the upper atmosphere, drag rises, predicted positions
drift along-track, and screening built on the public catalogue quietly gets worse at
the moment it matters most. driftwatch will screen a chosen fleet against the whole
catalogue and show how miss distances and probabilities move under quiet and stormy
conditions, live and in replay of past storms.

**Status: Phase 2 of 5 complete** (conjunction screening: Space-Track merged in, the demo
fleet defined, three-stage screening, an empirical covariance and a probability of
collision on every event, a weekly report and a conjunctions panel in the viewer). Phase 1
(catalogue and globe) is complete. Phase 3 adds the storm layer. See `ROADMAP.md` for the
full plan, `docs/phase1-plan.md` for what Phase 1 built and why, and `docs/phase2-plan.md`
for the Phase 2 plan and every decision taken along the way.

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
  histories, the history index and batched backfill, and the scenario mechanism end to
  end.

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
uv run driftwatch report latest           # weekly report + the viewer's conjunctions bundle
cd web && npm install && npm run dev      # open the printed URL
```

`uv run driftwatch snapshots` lists what has been fetched. `--offline` on `fetch`
rebuilds the snapshot from cache without touching the network; `--spacetrack off` skips
Space-Track and `--spacetrack on` fails without it (the default uses it when the
credentials or a cache are present). `uv run driftwatch history --ids 25544,39634
--start 2024-05-01 --end 2024-05-20` pulls every element set for those objects from
Space-Track's `gp_history` into `data/history/`; `screen` does the same for the fleet
and its surviving secondaries by itself (`--history off` skips it, `--history on` insists
on it). Run `uv run pytest` for the tests (the first run downloads IERS Earth-orientation
data for astropy, about 3 MB).

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
  risk/                 covariance model and fit, manoeuvre flag, probability of collision, scenarios, Kelvins
  export/               viewer bundle, conjunction run directory, weekly report
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

## Licence

MIT. See `LICENSE`.
