# State of play

Written 2026-09-05, at the end of the session that ran the calibration benchmark against precise
orbits, built the local-analysis path, and committed the second review's corrections with the
parked items' premises rewritten. It supersedes the earlier 2026-09-05 version and, like it,
records **where things stand and what is unresolved** without restating the reasoning, which lives
in the pages it points at. A snapshot; where it disagrees with a plan or a methods page, the page
wins.

## Reading order for a fresh session

1. `README.md`, the **findings and corrections** page at the top — six items now. Item 6 is the
   calibration against ESA's precise orbits for Swarm A, B and C: the first comparison of a public
   element set with an independent truth in this project, published whatever it showed.
2. `docs/calibration-benchmark.md` — the page `driftwatch validate swarm` writes: three windows,
   four things by lead bin, every source with its origin and derivation.
3. `ROADMAP.md`, "Plan change, 2026-09-05" and the paragraph added after it — Phase 4 stops at the
   pipeline; the benchmark and the local path are the one bounded experiment and the one optional
   path added after the second review; the parked items have their premises rewritten, not deleted.
4. `docs/local-analysis.md` — `driftwatch local`: an operator's own ephemerides, messages and records
   through the provenance check, the CDM matcher and the same benchmark, with the network refused.
5. `docs/writeup-notes.md` — additive; the last two entries are the second review and the benchmark.
6. `docs/methods.md`, "Uncertainty and probability" — what the covariance is, and now what one
   calibration found about it.
7. `docs/storm-validation.md` and `docs/storm-term.md` — the storm term, its May 2024 validation
   against later element sets, and the pointer to the same term measured against a truth.
8. `docs/pipeline.md`, `docs/cdm-matching.md`, `docs/phase4-plan.md` — the pipeline, the matcher and
   the working record, unchanged this session.

## Where things stand

| Item | State | Where |
| --- | --- | --- |
| **Calibration benchmark** | **Run and published.** Swarm A, B and C against ESA's `SW_OPER_SP3xCOM_2_` precise orbits; 57, 54 and 61 element sets in the quiet (20 to 27 April 2024), May 2024 storm and held-out October 2024 windows; one trial per set; manoeuvres from ESA's `SW_OPER_SC_xDYN_1B` thruster record (two in 150 satellite-days, both also found by the precise-orbit step detector). Results in `docs/calibration-benchmark.md` and README item 6; per-trial file `data/validation/swarm_benchmark.parquet` (gitignored). | `README.md` item 6; `docs/calibration-benchmark.md`; `src/driftwatch/storm/precise.py` |
| **Local-analysis path** | **Built and tested**, not yet used by anyone: `driftwatch local` runs a stored run's provenance check, the CDM matcher and the ephemeris benchmark over an operator's own files with every outbound request refused. OEM (KVN) reader for ITRF, TEME and J2000 frames and UTC, TAI and GPS time systems; manoeuvre records as CSV. | `docs/local-analysis.md`; `src/driftwatch/local.py`; `tests/test_local.py` |
| Second review's corrections | **Committed** (they were in the working tree, uncommitted, at the start of this session). | `docs/writeup-notes.md`, "The second review" |
| Parked items | **Premises rewritten**, dated 2026-09-05, per the instruction: investigation burden replaces manoeuvre burden; lifetime loss requires validated decay modelling; the Starlink latency record is a separate causal study, not an overlay; commandability needs an operator's contact and command constraints; Hermanus needs a grid engineer's action criterion. | `ROADMAP.md`, parked items |
| Precondition check | Unchanged: `VERCEL_TOKEN` is still not set; only the account holder can create it. The pipeline's deploy step fails by name until it is. | `docs/pipeline.md`, "Hosting" |
| The daily pipeline | Unchanged this session: built, fired once on its own (2026-09-04), **no run has completed end to end**. | `docs/pipeline.md` |
| Steps 3 to 7, OSC validation | Deferred indefinitely, unchanged. | `ROADMAP.md`, plan change |
| CDM parser and matcher | Built; **no real message has been matched**. The local path is the way one would be. | `docs/cdm-matching.md`, `docs/local-analysis.md` |

## What the benchmark found, in one paragraph

In-track median absolute residual at 6 h / 24 h / 72 h / 7 days: quiet 0.3 / 0.5 / 3.2 / 24 km, May
storm 0.5 / 0.8 / 7.2 / 75 km, October storm 0.9 / 1.8 / 15 / 49 km, with 95th percentiles of 62,
197 and 652 km at seven days. The empirical covariance over-covers in the quiet week from one to
five days (82 to 96 per cent inside one sigma) and under-covers inside twelve hours; in both storms
it under-covers at every lead (two sigma holds 65 to 80 and 62 to 75 per cent against the 95 it
claims). The storm term with the observed ap helps in May only from four days of lead (+20 to +48
per cent on the median) and hurts from twelve hours to three days; in October it helps from six
hours to five days and hurts at six and seven; in the quiet week it hurts from one to six days,
because its excess is not zero without a storm; at seven days in May its shift is about 1.5 times
the actual. The horizon for keeping the satellite inside the screening box's 25 km in-track
half-width at the 95th percentile: five days quiet, two days in May, one day in October.

## What is committed, and what is not

`main`, four commits this session (the second review and the roadmap rewrites; the benchmark
module, command, tests and the `cdflib` dependency; the result and its pages; the local path and
this page). Not pushed by this session unless the log says otherwise.

Local state that is **not** in the repository, all gitignored deliberately:
`data/cache/swarm/` (150 precise-orbit zips and 150 thruster-record zips, about 600 MB, plus the
server listings), `data/validation/swarm_benchmark.{json,parquet}` (the benchmark's outputs; the
page in `docs/` is regenerated from them), the 2024 Swarm element-set history in `data/history/`
(fetched by the previous session), and everything the earlier state-of-play listed
(`data/conjunctions/step*`, `data/spacex/`, `data/cache/`, `data/ballistic/`, `data/validation/`,
`.vercel/`).

## What has never happened

- **No pipeline run has completed end to end**, and **no deploy from CI** on either host; the deploy
  is blocked on `VERCEL_TOKEN`. Unchanged.
- **No real Conjunction Data Message has been matched**, and **nobody has run `driftwatch local`**
  on real files. Both are built and tested against designed inputs only.
- **No second object class has been calibrated.** The benchmark covers three well-tracked
  satellites at 460 to 506 km.

## Open items

1. **The storm term applies a non-zero mean shift in quiet conditions**, and the benchmark shows it
   makes the residual worse from one to six days in a quiet week (README item 6). The `forecast`
   scenario applies the term whenever it has a coefficient. Whether to zero the mean shift below
   some ap, or to subtract the quiet-time excess, is a decision about the model that should be made
   against this measurement and recorded, not tuned; nothing was changed this session.
2. **The covariance under-covers in a storm by the numbers in item 6**, and the screening carries
   it unchanged. The same applies: a storm-conditional scale would be a calibration on one orbit
   class and two storms, and it has not been made.
3. **The held-out window holds two storms** (7 to 8 October, then 10 to 11), and the sets issued
   between them over-predict the decay for the quiet days that followed; the `B*`-across-a-storm
   explanation is an inference. Swarm's TU Delft density products (`SW_OPER_DNSxPOD_2_`) would
   separate the atmosphere's error from the object's response and are the next thing to read.
4. **Generalisation.** Whether the ratio of actual error to consistency found here holds for debris,
   for higher orbits, or for objects the network tracks less often is not measured; laser-ranging
   objects and other GNSS-carrying missions with public precise orbits are the way to extend it.
5. Everything the earlier state-of-play listed and this session did not touch: the attached-object
   filter's runner reading (settled in `docs/pipeline.md`, "Reproducibility"), the deploy and the
   archive never having run on a runner, the `spacex-ephemeris+sgp4-fit` covariance path never
   exercised by real data, the storm's effect on how often an operator's plan is revised, and the
   NRLMSIS storm bias recorded and not applied.

## The runner and the ceiling

Unchanged from the earlier state-of-play: the ceiling in `docs/pipeline.md` is left as written until
a second completed run confirms the first, and the positioning it implies is unchanged — a
university group, a single-spacecraft mission, a small national operator — which is who the CDM
matcher and the local path are for.
