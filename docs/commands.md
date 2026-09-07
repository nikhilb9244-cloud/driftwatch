# Commands and deployment

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
  step and threshold derived so that no minimum inside the screening volume is lost while the
  trajectory is continuous with a bounded derivative — where a published ephemeris makes it
  jump the threshold is re-derived, those candidates are refined by a hundred-point scan that
  places the time of closest approach to about a hundredth of a step rather than by
  root-finding, and a break in the very first or very last interval of a published file cannot
  be detected at all (`docs/screening.md`) — and
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
  of a possible 2 over the 981 events of the 3 September 2026 run with both objects free-flying,
  so the two displacements are nearly independent on that population.
  What it could not find was that the result itself rested on displacing operator-controlled
  objects; an external review did (2026-09-05), and the ratio is now taken over free-flying
  pairs only. See `docs/storm-term.md`.
- Every aggregate the tool prints is reported **twice**: over the events whose two objects both
  have a ballistic coefficient measured from their own decay (`validated`), and over the rest
  (`indicative`). Step 4 measured the storm term against May 2024 and found its sign right on
  about nine comparisons in ten at three to four days of lead with a measured coefficient, no
  skill inside two days, and no demonstrated skill without a measured coefficient, so the split
  is the difference between a measurement and an extrapolation. `storm_validity` is on every row.
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
  the data: with the combined radius taken as `(t_span + c_span) / 2`, the 162,634-row
  training set is reproduced to a median residual of 0.07 % with 87 % of the high-risk tail
  within a factor of two. The convention was recovered from those rows, so it is confirmed on
  held-out splits (each half of the events against the other, and the training file against
  the challenge's test file) before being called unfitted. It validates the probability
  arithmetic on ESA's inputs and does not calibrate driftwatch's covariance
  (`docs/kelvins-reproduction.md`).
- `driftwatch cdm match <run> --cdm <dir>` reads an operator's Conjunction Data Messages
  (CCSDS 508.0-B-1, KVN or XML), matches them to a stored run's events on the object pair and
  a ten-minute TCA tolerance, and reports which operator-warned conjunctions public data found
  and at what miss and probability, which it missed, and which public-data flags the operator
  never received. Built against the Kelvins rows as test input, which `driftwatch cdm
  from-kelvins` writes out as messages with synthetic identities (`docs/cdm-matching.md`).
- `driftwatch validate swarm` is the calibration benchmark against precise orbits: every public
  element set issued for Swarm A, B and C in three windows (a quiet control, the May 2024 storm,
  and an October 2024 storm held out from every tuning) propagated with SGP4 to leads from six
  hours to seven days and measured against ESA's precise science orbit in the satellite's own RIC
  frame, one trial per element set. It reports the residual distribution, the coverage of the
  empirical covariance against the 68 and 95 per cent it claims, the storm term's effect with
  the observed ap, and the horizon for the screening box, and reads ESA's thruster record for the
  manoeuvre exclusion (`docs/calibration-benchmark.md`, item 6 above).
- `driftwatch validate reference` extends the calibration to every mission with a public reconstructed
  orbit on an anonymous server (the DORIS satellites through the IDS data centre, Sentinel-1A through ESA's
  STEP mirror, GRACE-FO through GFZ's ISDC, Swarm as before) and, for every mission with a retroreflector,
  compares ILRS laser-ranging normal points with the reconstructed orbit and with each element set's
  propagation; four windows, August 2024 added and held out like October; the horizon by altitude band
  and window, the population statement, and what was not obtainable (`docs/reference-benchmark.md`).
  `--missions` picks keys, `--no-slr` skips the laser comparison, `--offline` reads the cache only.
- `driftwatch validate dsgp4` runs ESA's dSGP4 and its ML-dSGP4 hybrid on the reference benchmark's trials
  (`uv sync --extra dsgp4` installs them): the hybrid is trained on the quiet and May windows only, scored
  on all four against plain SGP4 and the storm term, and adopted only if the held-out storms improve
  (`docs/dsgp4-evaluation.md`).
- `driftwatch radio horizon`, `driftwatch radio emissions` and `driftwatch radio period <name>` are
  the radio lane (`docs/radio-lane.md`): the calibration benchmark's residuals as angles on the sky
  for the 13.5 m MeerKAT dish, by receiver and lead (`docs/radio-horizon.md`); the declared
  satellite emissions by band from public filings (`docs/radio-emissions.md`); and, for a period,
  the two products on the catalogue as it stood at each observation start -- constellation members
  above ten degrees, counted, and every object whose track passes inside the half-power radius,
  with its closest approach, element-set age, cross-track angular uncertainty, the two horizon labels,
  and the time since the last detected manoeuvre with whether the set's likely fit arc spanned it --
  written as a report under `docs/radio/` and an export in the IAU CPS SatChecker field-of-view
  shape under `data/radio/`. Observations come from a CSV; `driftwatch radio archive <name>` writes
  one under `data/archive/sarao/` (ignored by the repository) from the SARAO archive's documented
  GraphQL API with the token in `SARAO_ARCHIVE_TOKEN` (read-only, paced, metadata only, public
  records past the proprietary period only, identifiers cited rather than records reproduced); the history
  for the period must be in `data/history/`. Geometry only: no received power, occupancy or
  sensitivity loss is computed.
- `driftwatch local` runs an operator's own files through the provenance check, the CDM matcher
  and the same benchmark with the operator's ephemeris as the truth, with every outbound request
  refused for the duration by an application-level guard over the clients this project fetches
  through — `httpx.Client.send`, `httpx.AsyncClient.send` and `urllib.request.urlopen` replaced
  and astropy's auto-download switched off, each restored on exit, any request inside the block
  raising `NetworkRefused` and exiting with code 3. It is an application guard, not OS-level
  isolation: it bounds what driftwatch itself sends, not what the machine can send. So the
  operator's files stay on the operator's machine and the public demonstration stays reproducible
  from public sources alone (`docs/local-analysis.md`).

(Same pass, README.md:758, which repeats the unbounded framing: replace "and the guard that keeps
them on the operator's machine." with "and the application-level guard — not OS-level isolation —
that refuses driftwatch's own outbound requests for the duration.")
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
export SPACETRACK_USER=user@example.org   # optional: Space-Track login for the full catalogue
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
on it). Astropy may download IERS Earth-orientation data on first use; offline installation requires that data to be available locally.

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
   `-Scenario` choose which stored run and scenario to show. The bundle names every fleet member.
   A rule that hid them behind their catalogue number ran from 5 to 7 September 2026 and was
   withdrawn: the catalogue number is public and `objects.json` ships the name against it, so the
   rule withheld nothing while making the page harder to read. What limits how a flag may be read
   is that every one of them leads with its region and confidence, which is unchanged.
   `docs/writeup-notes.md` records the reasoning both ways.
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



_Last updated 7 September 2026._
