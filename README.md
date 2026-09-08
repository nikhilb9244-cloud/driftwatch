# driftwatch

[![ci](https://github.com/nikhilb9244-cloud/driftwatch/actions/workflows/ci.yml/badge.svg)](https://github.com/nikhilb9244-cloud/driftwatch/actions/workflows/ci.yml)
[![licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

driftwatch compares public and supplied orbit products and screens a baseline catalogue for close approaches. Storm outputs are a sensitivity analysis on the baseline event set. Candidate discovery is not repeated for perturbed trajectories.

## The horizon

<!-- BEGIN CLAIMS:horizons -->
15 spacecraft in 5 altitude bands across 4 inspected windows; 1,249 raw element sets, 1,193 usable at some lead and 10,310 usable set/lead pairs. These are epoch-based reconstructions; historical publication availability is not established.

A lead passes when at least 95% of finite usable absolute in-track residuals are within 25 km. Brackets are observed bins; passing through the longest tested lead is right censoring, not a guarantee beyond it.

| Band | Window | Observed endpoints | Usable n at last pass | Composition at last pass |
| --- | --- | --- | --- | --- |
| 400-600 km | April 2024 control | 120 h pass / 144 h fail | 95 | GRACE-FO 1 (C): 19; GRACE-FO 2 (D): 19; Swarm A: 19; Swarm B: 19; Swarm C: 19 |
| 400-600 km | May 2024 | 48 h pass / 72 h fail | 91 | GRACE-FO 1 (C): 18; GRACE-FO 2 (D): 19; Swarm A: 18; Swarm B: 19; Swarm C: 17 |
| 400-600 km | August 2024 held out | 48 h pass / 72 h fail | 93 | GRACE-FO 1 (C): 18; GRACE-FO 2 (D): 18; Swarm A: 19; Swarm B: 19; Swarm C: 19 |
| 400-600 km | October 2024 held out | 24 h pass / 36 h fail | 100 | GRACE-FO 1 (C): 19; GRACE-FO 2 (D): 20; Swarm A: 21; Swarm B: 19; Swarm C: 21 |
| 600-750 km | April 2024 control | 120 h pass / 144 h fail | 35 | CryoSat-2: 4; Sentinel-1A: 31 |
| 600-750 km | May 2024 | passes through the longest tested lead (168 h) | 12 | CryoSat-2: 12 |
| 600-750 km | August 2024 held out | 120 h last pass; unavailable at 144 h | 4 | CryoSat-2: 3; Sentinel-1A: 1 |
| 600-750 km | October 2024 held out | 96 h pass / 120 h fail | 22 | CryoSat-2: 6; Sentinel-1A: 16 |
| 750-850 km | April 2024 control | passes through the longest tested lead (168 h) | 29 | SARAL: 19; Sentinel-3A: 8; Sentinel-3B: 2 |
| 750-850 km | May 2024 | passes through the longest tested lead (168 h) | 25 | SARAL: 19; Sentinel-3B: 6 |
| 750-850 km | August 2024 held out | passes through the longest tested lead (168 h) | 18 | SARAL: 18 |
| 750-850 km | October 2024 held out | 120 h pass / 144 h fail | 41 | SARAL: 17; Sentinel-3A: 20; Sentinel-3B: 4 |
| 850-1000 km | April 2024 control | passes through the longest tested lead (168 h) | 77 | HY-2C: 30; HY-2D: 27; SWOT: 20 |
| 850-1000 km | May 2024 | passes through the longest tested lead (168 h) | 48 | HY-2C: 10; HY-2D: 19; SWOT: 19 |
| 850-1000 km | August 2024 held out | passes through the longest tested lead (168 h) | 39 | HY-2C: 22; SWOT: 17 |
| 850-1000 km | October 2024 held out | passes through the longest tested lead (168 h) | 15 | HY-2C: 12; HY-2D: 2; SWOT: 1 |
| 1000-1400 km | April 2024 control | passes through the longest tested lead (168 h) | 37 | Jason-3: 19; Sentinel-6A: 18 |
| 1000-1400 km | May 2024 | passes through the longest tested lead (168 h) | 20 | Jason-3: 5; Sentinel-6A: 15 |
| 1000-1400 km | August 2024 held out | passes through the longest tested lead (168 h) | 35 | Jason-3: 17; Sentinel-6A: 18 |
| 1000-1400 km | October 2024 held out | passes through the longest tested lead (168 h) | 32 | Jason-3: 17; Sentinel-6A: 15 |

Unsupported: identity, reference coverage, measured age or manoeuvre-excluded scope is not established. Altitude overlap alone does not transfer calibration.
<!-- END CLAIMS:horizons -->

Mission and whole-set deletion sensitivity, exclusions and every usable denominator are in the [v2 paper](docs/paper.md) and [complete tables](docs/benchmark-v2-tables.md). The [claims manifest](docs/assets/claims-v2.json) supplies this section and the application labels; [findings](docs/findings.md) includes covariance, radio, September and learned-propagator results.

## Scope and review

The software performs no independent orbit determination and supplies no calibrated operational collision probabilities. The measured population does not establish warning completeness or applicability to a new spacecraft. The local comparison workspace and recorded examples show software behaviour; receiver-log validation, real conjunction-message cases and operational adoption remain open.

Independent comparisons exposed clock, frame, covariance-fitting-window and station-reference-point errors. The [paper](docs/paper.md) records their implications and the [dated covariance correction](docs/covariance-basis-correction.md) records every moved cell. Epoch-selected histories are epoch-based reconstructions; their element epochs do not establish publication-time availability.

The [September status page](docs/protocols/september-2024-execution-status.md) is generated from its attestation, access and completion metadata. September is a retrospective physical diagnostic and will not be reused as a hold-out for another recipe. All earlier benchmark windows have also been inspected.

The [radio branch](docs/radio-lane.md) remains research and partner-dependent. Measured MeerKAT beams are CC BY-NC and used for research only; commercial use requires an appropriate rights-cleared data path.

The paper awaits author review. Nothing is deposited before that review, and no outreach letter is sent before the README matches the current evidence. The [roadmap](ROADMAP.md) records decisions and acceptance tests, not completed products or customer demand.

## Software and examples

The [public workspace](https://driftwatch-coral.vercel.app/) serves recorded examples. The local engine compares supplied products on the same computer. Orbit comparison and contact examples have distinct inputs and denominators; their [provenance and limits](docs/workspace.md) must accompany reuse. The archived catalogue is an illustrative screening output, not a current reference calibration.

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

- [Current paper](docs/paper.md), [findings](docs/findings.md), [reference benchmark](docs/reference-benchmark.md) and [component calibration](docs/calibration-benchmark.md).
- [Learned-propagator evaluation](docs/dsgp4-evaluation.md) and [radio geometry](docs/radio/track-benchmark-v2.md).
- [Methods](docs/methods.md), [frames and time](docs/frames-and-time.md), [input formats](docs/input-formats.md) and [commands](docs/commands.md).
- [Data sources and redistribution](docs/data-sources.md), [claims audit](docs/claims-audit.md) and [remaining acceptance tests](ROADMAP.md).

[CITATION.cff](CITATION.cff) supplies citation metadata. The [v1 archive](docs/archive/README.md) preserves superseded measurements. Source code is [MIT licensed](LICENSE); this grants no rights over third-party data.
