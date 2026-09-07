# driftwatch

[![ci](https://github.com/nikhilb9244-cloud/driftwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/nikhilb9244-cloud/driftwatch/actions/workflows/ci.yml)
[![licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
[![benchmark: swarm-benchmark-2026-09](https://img.shields.io/badge/benchmark-swarm--benchmark--2026--09-informational)](https://github.com/nikhilb9244-cloud/driftwatch/releases/tag/swarm-benchmark-2026-09)

driftwatch screens a satellite fleet against the public orbital catalogue, estimates collision
probability from an uncertainty model fitted to how successive element sets for the same object
disagree, and adds a storm term that displaces objects and widens their covariance under a
geomagnetic scenario.

## The horizon

Against ESA's reduced-dynamic precise science orbits for **Swarm A, B and C** — three
sun-synchronous satellites at approximately 460 and 506 km, the only population this has been measured on — a public
element set keeps the satellite inside the 25 km in-track half-width of the screening box, at the
95th percentile of trials, for **five days in a quiet week** (20–27 April 2024), **two days in the
May 2024 Gannon storm** (6–13 May) and **one day in a held-out October 2024 storm** (6–13 October).
Those three windows are the whole of the evidence. A probability computed from an element set
propagated past its horizon is arithmetic on a position the set no longer predicts, so the quiet
scenario is the default everywhere and a storm scenario is an explicit choice. The measured
tolerance for three Swarm-class satellites does not establish an operating horizon for any other
spacecraft. Detail: [docs/calibration-benchmark.md](docs/calibration-benchmark.md).

## Provenance findings

Each was measured, and each is stated with the correction it forced.

1. **A public SGP4 fit drifts from the operator's own ephemeris by two orders of magnitude more
   than its published fit residual.** CelesTrak's supplemental Starlink sets carry a residual near
   0.20 km; measured against the published states on nineteen matched files (2026-09-03), the
   median separation runs from 0.30 km under 12 hours to **82.9 km at 60–72 hours**, almost all
   along track. Qualified: one lead bin of six, nineteen satellites, one date, against the
   operator's published *prediction* rather than the realised orbit.

2. **A frame or clock error can survive internally consistent calculations.** SpaceX's published states are MEME (J2000), 0.36 degrees from TEME by
   2026: on six satellites' files (2026-09-03), compared at the ephemeris start with the fit to
   the same file, they sit a median **36.2 km** away read as TEME and a median 0.356 km when
   rotated. The same class of error in the time system put ESA's Swarm orbits **137 km** along
   track when their GPS epochs were read as UTC. The independent comparison exposed an error that the existing internal checks had missed.

3. **A covariance fit labelled with one window had read outside it.** The 3 September 2026 run's
   fit, labelled 21 July to 3 September, had read 2,714,544 element sets of which **615,648 lay
   before the window**, most from the 2024 solar maximum. Refitted under the bound, the in-track
   one-day sigma changed on 21,644 of 22,039 objects (median −5 per cent) and the flagged events
   under `quiet` went from 21 to 12.

## Scope and limits

- **Absolute probabilities are indicative, not operational.** They combine a predicted separation,
  assumed object sizes and an uncertainty estimate, and each can change the answer.
- **The uncertainty model measures consistency, not accuracy.** It is fitted from how an object's
  successive element sets disagree; those sets share observations and assumptions, so their
  agreement bounds the true error in neither direction. The Swarm A/B/C comparison across the three stated windows found it over-covering from one to five days in a quiet week and under-covering at
  every lead in a storm.
- **There is no independent orbit determination.** Positions come from public element sets, published operator predictions or supplied orbit products,
  no sensor, and no tracking of any kind in this project.
- **The storm term has demonstrated skill for one population, at one end of the window, on one
  storm**, and its effect depends on the period: it helps at longer leads in October's sample and
  hurts May's 12–72 hour sample and the quiet 1–6 day sample.
- **A flag is reported with its region and confidence before its colour.** A red in the dilution
  region is a statement about the size of the covariance, not about the encounter.
- **No operator has used this tool**, and no organisation has adopted it or agreed to be named in
  connection with it. Nothing here has been exercised against operational practice.
- The conjunction-message reconciler and the contact planner ship no example and **have not been
  exercised on real data**.

## Archived screening result

**Robust region, standard confidence: 16 flagged events. Dilution region, low confidence:
17 of 33 flags (51.5%).** These counts belong to the quiet scenario of the archived
`demo_20260905T000400Z` run: 5,766 events across six fleet objects over 5–12 September 2026.
The robust flags comprise one red and 15 yellow; the dilution flags are 17 yellow.
Robust describes a covariance region; it does not certify position accuracy or authorise a manoeuvre.
The [catalogue](https://driftwatch-coral.vercel.app/catalogue.html) labels its own run and scenario.

## Software and examples

The [analysis workspace](https://driftwatch-coral.vercel.app/) compares orbit products, evaluates
the historical Swarm benchmark and predicts ground contacts. The public site serves recorded
examples. The local engine processes supplied files in memory on the same computer.

The Swarm A orbit example compares two Space-Track element sets with an ESA reconstructed orbit:
median differences **0.544 km and 32.845 km**, over **1,440 samples** on 13 May 2024. The ISS
example is a separate contact calculation: **three predicted passes** on 11 May 2024, with
acquisition differences of **1.06–1.33 seconds** between two element sets. It has nine plot samples
around the first pass, not 1,440 orbit-reference trials. Assigning the Swarm figures to the ISS
was a reporting error; the shipped inputs and computed outputs are distinct.

Neither example establishes general refresh-policy performance. The ISS example has no measured
receiver log or independent orbit reference. The surveyed station marker does not establish
antenna availability. [Workspace limits and provenance](docs/workspace.md).

## Installation and recorded replay

Python 3.12+, uv and Node.js are required for the local workspace:

```powershell
uv sync
cd web
npm ci
npm run build
cd ..
uv run python -m driftwatch.workbench
```

The workspace serves at `http://127.0.0.1:8765`. Installation requires internet access;
analysis uses an application network guard, not operating-system isolation. It provides no
protection against a compromised computer, extensions or modified code. No operational service
guarantee, account system, telemetry or hardware control is provided.

An archived element-set-only screening replays with its recorded snapshot, supplemental parquet,
fleet object table, configuration and covariance. The recorded snapshot and supplemental files
must be available under `DRIFTWATCH_DATA_DIR`; the response cache and history store are not inputs.

```powershell
uv run driftwatch screen --offline --replay <archive-run-directory> --out-dir <new-output-directory>
uv run python scripts/compare_replay.py <archive-run-directory> <replayed-run-directory>
```

Replay currently supports the archived **quiet** scenario and refuses runs that used unretained
operator states. It does not refit the historical covariance or reproduce storm forcing.
Missing supplemental versions fail; a different cached response cannot substitute for them.
The production gate remains in place. [Pipeline and retention limits](docs/pipeline.md).

## Methods, sources and citation

- [Findings and corrections](docs/findings.md): the bounded measurements and withdrawn claims.
- [Calibration benchmark](docs/calibration-benchmark.md): all three windows, populations and lead bins.
- [Radio lane](docs/radio-lane.md): the benchmark's residuals as angles on the sky for a 13.5 m dish over the
  Karoo, the [radio horizon](docs/radio-horizon.md) by receiver, the [declared-emission table](docs/radio-emissions.md),
  and two retrospective period reports on the catalogue as it stood. Geometry only; no received power anywhere.
- [Methods and approximations](docs/methods.md), [screening](docs/screening.md), [frames and time](docs/frames-and-time.md).
- [Data sources and redistribution](docs/data-sources.md): attribution and analysis-only inputs.
- [Input formats](docs/input-formats.md), [commands](docs/commands.md), [remaining validation](ROADMAP.md).
- [Claims audit](docs/claims-audit.md): scope corrections and unresolved evidence.

The [tagged Swarm benchmark](https://github.com/nikhilb9244-cloud/driftwatch/releases/tag/swarm-benchmark-2026-09)
contains the frozen measurements. [CITATION.cff](CITATION.cff) supplies citation metadata.
Source code is [MIT licensed](LICENSE); the code licence grants no rights over third-party data.

_Last updated 7 September 2026._
