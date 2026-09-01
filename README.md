# driftwatch

Conjunction screening for low Earth orbit that shows how geomagnetic storms change
collision risk. A storm heats the upper atmosphere, drag rises, predicted positions
drift along-track, and screening built on the public catalogue quietly gets worse at
the moment it matters most. driftwatch will screen a chosen fleet against the whole
catalogue and show how miss distances and probabilities move under quiet and stormy
conditions, live and in replay of past storms.

**Status: Phase 1 of 5** (catalogue and globe). See `ROADMAP.md` for the full plan and
`docs/phase1-plan.md` for what was built, and why, in this phase.

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
- Tests cover the official SGP4 verification cases, frame conversions against skyfield,
  a real ISS pass over Durban, the cache rules, the snapshot schema and the export.

## Quick start

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
uv sync                                   # Python environment
uv run driftwatch fetch                   # ~10 s; downloads ~20 MB, writes data/snapshots/gp_<stamp>.parquet
uv run driftwatch propagate --at 2026-09-01T12:00:00Z
                                          # ~3 s; writes data/propagated/state_<stamp>.parquet
                                          # and web/public/data/{manifest.json,objects.json,elements.bin,reference.bin}
cd web && npm install && npm run dev      # open the printed URL
```

`uv run driftwatch snapshots` lists what has been fetched. `--offline` on `fetch`
rebuilds the snapshot from cache without touching the network. Run `uv run pytest` for
the tests (the first run downloads IERS Earth-orientation data for astropy, about 3 MB).

## What you are looking at

Each point is one catalogued object at the time on the clock, coloured by category:
space stations, Starlink, OneWeb, other constellations, other payloads, rocket bodies,
debris, unknown. The slider spans 24 hours either side of the reference time. Hover for
name, altitude and position; click or search to pin an object.

Positions come from public two-line element sets propagated with SGP4. They are good to
hundreds of metres to a few kilometres near the element-set epoch and drift by kilometres
per day, more in a storm. The viewer's Earth-fixed frame ignores UT1 and polar motion,
which costs under a pixel. Everything approximate is listed in `docs/methods.md`.

Coverage in Phase 1 is the CelesTrak groups (operational payloads, stations, the
Starlink and OneWeb constellations, recent launches and the three largest debris clouds),
roughly 19,000 objects. The remaining rocket bodies and debris that make up the ~30,000
tracked public objects come from Space-Track in a later phase.

## Layout

```
src/driftwatch/         Python package (CLI: driftwatch)
  catalogue/            CelesTrak fetch, SATCAT, classification, parquet snapshots
  orbit/                time, SGP4 propagation, frame conversions
  export/               viewer bundle
tests/                  pytest
docs/                   physics background, frames and time, data schema, methods, plan
web/                    Vite + TypeScript + globe.gl + satellite.js viewer
data/                   cache, snapshots, propagated states (git-ignored)
```

## Docs

- `docs/tle-and-sgp4.md`: what a TLE is, mean versus osculating elements, what SGP4
  does, and the accuracy limits of the public catalogue.
- `docs/frames-and-time.md`: TEME, ITRS, GMST, UT1 and polar motion, and the measured
  cost of the browser's shortcut.
- `docs/data-schema.md`: every column in the snapshot, state and viewer files.
- `docs/methods.md`: the running list of approximations.

## Data sources and their rules

- [CelesTrak](https://celestrak.org) GP element sets and SATCAT. No account. Their rule
  is one fetch per group per two hours with a descriptive User-Agent; the fetcher
  enforces both and caches everything. Set `DRIFTWATCH_CONTACT` to add a contact
  address to the User-Agent.
- Space-Track (later phases) requires registration and has its own user agreement.

## Licence

MIT. See `LICENSE`.
