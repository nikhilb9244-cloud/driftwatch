# Current benchmark findings

15 spacecraft in 5 altitude bands across 4 inspected windows; 1,249 raw element sets, 1,193 usable at some lead and 10,310 usable set/lead pairs. These are epoch-based reconstructions; historical publication availability is not established.

Consistency covariance bounds absolute accuracy in neither direction. Component coverage varies by mission, window and lead; storm residuals and Sentinel-6A in April 2024 control expose undercoverage. Storm output is a sensitivity analysis on the baseline event set; candidate discovery is not repeated.

Both local learned-propagator checkpoints remain negative findings: 0/40 pooled paired medians improve; 3/40 tails improve. The stored adoption rule rejects both checkpoints.

September retrospective physical diagnostic: prediction MAE 4.284 km versus 17.254 km for zero prediction. 11/13 events beat zero; SWOT and one Sentinel-3A event do not. September will not be reused as a hold-out for any new recipe.

Other declared offsets: crossing agreement 4608/4704 (98.0%); false crossings 45/2016; missed crossings 51/2022. Constructed pointings on inspected windows; measured beams are CC BY-NC and used for research only.

Exact boundary offsets: crossing agreement 700/1344 (52.1%); false crossings 642/1342; missed crossings 2/702. Constructed pointings on inspected windows; measured beams are CC BY-NC and used for research only.

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

The [claims manifest](assets/claims-v2.json) binds every result above to its population, denominator, reference, censoring state and permitted wording. [Paper](paper.md); [complete tables](benchmark-v2-tables.md); [dated covariance correction, every cell](covariance-basis-correction.md).
