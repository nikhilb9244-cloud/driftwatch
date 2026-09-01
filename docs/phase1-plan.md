# Phase 1 plan: catalogue and globe

This is the plan the kickoff prompt asked for, kept in the repository so it can be
reviewed and revised. Decisions that affect later phases are listed at the end with
the reasoning, and with the alternative that was not taken.

## What Phase 1 delivers

1. `uv run driftwatch fetch` downloads the CelesTrak groups, caches every download,
   joins the SATCAT object-type table, and writes one dated parquet snapshot.
2. `uv run driftwatch propagate --at 2026-09-01T12:00:00Z` propagates every object in
   the latest snapshot with SGP4, converts TEME to ITRS (Earth-fixed) and geodetic
   coordinates, writes a parquet state file, and exports the viewer bundle.
3. `web/` is a static Vite site: a globe.gl globe, one `THREE.Points` object holding
   every satellite, a 48-hour time slider centred on the reference time, filters for
   category and altitude band, and hover details.
4. Tests against the sgp4 verification cases and against skyfield, plus docs.

## Module layout

```
src/driftwatch/
  __init__.py
  cli.py                  argparse entry point: fetch, propagate, snapshots
  config.py               paths, URLs, User-Agent, cache intervals, group list
  catalogue/
    celestrak.py          polite GP fetcher with an on-disk cache (2 h minimum interval)
    satcat.py             SATCAT download (24 h cache) for object type, RCS, owner
    classify.py           category and altitude-band rules
    snapshot.py           merge groups -> schema -> parquet; list/load snapshots
  orbit/
    time.py               UTC parsing and Julian date splitting
    propagator.py         Satrec construction from the snapshot, vectorised SGP4
    frames.py             TEME -> ITRS (astropy) and ITRS -> geodetic; GMST-only variant
  export/
    viewer.py             writes the viewer bundle into web/public/data/
tests/                    pytest
docs/                     tle-and-sgp4.md, frames-and-time.md, data-schema.md, methods.md
web/                      Vite + TypeScript + globe.gl + satellite.js viewer
data/                     cache/, snapshots/, propagated/ (git-ignored)
```

## Data flow

```
CelesTrak gp.php (JSON, one request per group)   CelesTrak satcat.csv
            |                                          |
     data/cache/celestrak/gp/<group>.json      data/cache/celestrak/satcat.csv
            |                                          |
            +------------------ merge, dedupe, classify -+
                                     |
                    data/snapshots/gp_<UTC stamp>.parquet
                                     |
                       SGP4 (sgp4.SatrecArray, WGS72)
                                     |
             data/propagated/state_<UTC stamp>.parquet  (TEME + ITRS + geodetic)
                                     |
             web/public/data/{manifest.json, objects.json, elements.bin, reference.bin}
                                     |
                         browser: satellite.js SGP4 -> globe
```

## Storage schema

See `docs/data-schema.md` for the column list. The important choices:

- One parquet file per fetch, named by the UTC fetch time. Every fetch is kept. Later
  phases estimate per-object covariance from consecutive element sets, so snapshots are
  the raw material and are never overwritten.
- The snapshot keeps the OMM mean elements exactly as CelesTrak publishes them, plus
  derived columns (period, mean semi-major axis, apogee, perigee) that are marked as
  mean-element quantities, plus SATCAT metadata and the classification.
- A `source` column ("celestrak") and a `groups` list column, so a Space-Track source can
  be added with the same schema when the full catalogue and history are needed.
- Propagated state files carry both frames and the SGP4 error code per object rather
  than dropping failed objects.

## Decisions taken (and why)

### 1. The time slider runs SGP4 in the browser

The viewer needs positions for around 30,000 objects at any time in a 48-hour window.
Exporting a trajectory table is not viable: at a one-minute cadence that is about a
gigabyte of float32, and at a coarser cadence linear interpolation cuts visible chords
through the orbit (a 10-minute gap on a 90-minute orbit dips 400 km). So the browser
carries the elements and runs the same SGP4 algorithm as the Python side, using
satellite.js, which is a port of the same Vallado reference implementation as the
Python sgp4 library and is checked against the same verification cases. satellite.js 7
ships a WebAssembly bulk propagator, which we run in a Web Worker.

The Python side remains the source of truth for analysis. To keep the two honest, the
export includes Python's TEME state at the reference time, and the viewer computes and
displays the maximum disagreement between the two implementations at that time.

Alternative not taken: two-body plus J2 secular propagation in the browser from an
exported osculating state. Cheaper, but it drifts by tens of kilometres per hour from
SGP4 and would have needed its own caveats.

### 2. Earth-fixed frame: ITRS via astropy, with a stated GMST-only approximation in the browser

The Python side converts TEME to ITRS with astropy, which applies the Greenwich mean
sidereal time rotation and polar motion using IERS Earth orientation data (downloaded
automatically; for dates beyond the table astropy extrapolates and warns). Tests compare
against skyfield. The browser uses the GMST rotation only, which differs from ITRS by
polar motion, about 10 to 20 m at the surface, invisible on a globe and documented.

### 3. Categories and altitude bands are rule-based and approximate

Category comes from SATCAT object type (payload, rocket body, debris) with overrides
from group membership (stations) and name prefixes (Starlink, OneWeb and a short list of
other constellations). Altitude bands use mean-element apogee and perigee: LEO if
apogee < 2000 km, GEO if both within 200 km of 35,786 km, HEO if eccentricity > 0.25,
MEO between LEO and GEO, other for the rest.

### 4. Coverage: CelesTrak groups now, Space-Track for the full catalogue later

CelesTrak has no whole-catalogue query. Fetching active, stations, starlink, oneweb,
last-30-days and the four large debris clouds gives roughly 16,000 to 18,000 objects.
The remaining rocket bodies and untracked-in-groups debris that make up the roughly
30,000-object public catalogue are only available from Space-Track, which needs
credentials. The fetcher, schema and viewer are written so that a Space-Track source
slots in without changes elsewhere.

### 5. SGP4 constants and mode

WGS72 gravity constants and the "improved" operations mode, which is what the sgp4
library defaults to and what the public TLEs are generated against. This is also what
satellite.js uses, so both sides agree.

## Review points

The kickoff asked for a pause after each of fetch, store, propagate, export and viewer.
Each step is a separate commit with its own tests, so the history can be reviewed in
that order.
