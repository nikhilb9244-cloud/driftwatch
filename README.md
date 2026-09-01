# driftwatch

Conjunction screening for low Earth orbit that shows how geomagnetic storms change
collision risk. A storm heats the upper atmosphere, drag rises, predicted positions
drift along-track, and screening built on the public catalogue quietly gets worse at
the moment it matters most. driftwatch will screen a chosen fleet against the whole
catalogue and show how miss distances and probabilities move under quiet and stormy
conditions, live and in replay of past storms.

**Status: Phase 2 of 5 in progress** (conjunction screening; Space-Track merged in and
the demo fleet defined, screening next). Phase 1 (catalogue and globe) is complete. See
`ROADMAP.md` for the full plan, `docs/phase1-plan.md` for what Phase 1 built and why, and
`docs/phase2-plan.md` for the Phase 2 plan and the decisions taken so far.

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
  snapshot knows it. The demo fleet is the ISS, Sentinel-1A, two university cubesats and
  the two active South African objects.
- Tests cover the official SGP4 verification cases, frame conversions against skyfield,
  a real ISS pass over Durban, the cache rules, the snapshot schema, the export, the
  Space-Track client and the fleet files.

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
cd web && npm install && npm run dev      # open the printed URL
```

`uv run driftwatch snapshots` lists what has been fetched. `--offline` on `fetch`
rebuilds the snapshot from cache without touching the network; `--spacetrack off` skips
Space-Track and `--spacetrack on` fails without it (the default uses it when the
credentials or a cache are present). `uv run driftwatch history --ids 25544,39634
--start 2024-05-01 --end 2024-05-20` pulls every element set for those objects from
Space-Track's `gp_history` into `data/history/`. Run `uv run pytest` for the tests (the
first run downloads IERS Earth-orientation data for astropy, about 3 MB).

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
  export/               viewer bundle
fleets/                 YAML fleet definitions (the primaries to screen)
tests/                  pytest
docs/                   physics background, frames and time, data schema, methods, data sources, plans
web/                    Vite + TypeScript + globe.gl + satellite.js viewer
data/                   cache, snapshots, history, propagated states (git-ignored)
```

## Docs

- `docs/tle-and-sgp4.md`: what a TLE is, mean versus osculating elements, what SGP4
  does, and the accuracy limits of the public catalogue.
- `docs/frames-and-time.md`: TEME, ITRS, GMST, UT1 and polar motion, and the measured
  cost of the browser's shortcut.
- `docs/data-schema.md`: every column in the snapshot, state and viewer files.
- `docs/methods.md`: the running list of approximations.
- `docs/data-sources.md`: each data provider's terms, the Space-Track redistribution
  clause as checked, and the citation format.
- `docs/phase2-plan.md`: the Phase 2 plan, the review decisions and the demo fleet.

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

## Licence

MIT. See `LICENSE`.
