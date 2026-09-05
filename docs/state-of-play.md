# State of play

Written 2026-09-05, after the close-out's two fixes and its verification. It supersedes the earlier
2026-09-05 versions and, like them, records **where things stand and what is unresolved** without
restating the reasoning, which lives in the pages it points at. A snapshot; where it disagrees with a
plan or a methods page, the page wins. **Nothing else is built until a user supplies a case.**

## Reading order for a fresh session

1. `README.md`, the **findings and corrections** page at the top. It opens with the horizon, ahead
   of any probability: five days quiet, two days in the May 2024 storm, one day in the October 2024
   storm, at the screening box's 25 km in-track half-width and the 95th percentile of trials. Item 2
   now carries three corrections of one class, the frame, the clock and the fit's window, each a
   constant offset between two conventions that no self-comparison could see. Item 6 is the
   calibration against ESA's precise orbits and carries the explanation of the under-coverage in the
   order the evidence supports, and the two decisions the benchmark leaves open.
2. `docs/calibration-benchmark.md` — the page `driftwatch validate swarm` writes: three windows,
   four things by lead bin, every source with its origin and derivation.
3. `ROADMAP.md`, "Plan change, 2026-09-05" and the paragraph added after it — Phase 4 stops at the
   pipeline; the benchmark and the local path are the one bounded experiment and the one optional
   path added after the second review; the parked items have their premises rewritten, not deleted.
4. `docs/local-analysis.md` — `driftwatch local`: an operator's own ephemerides, messages and records
   through the provenance check, the CDM matcher and the same benchmark, with the network refused.
5. `docs/writeup-notes.md` — additive; the last two entries are the second review and the benchmark.
6. `docs/methods.md`, "Uncertainty and probability" — what the covariance is, and what one
   calibration found about it; `docs/screening.md`, "History for the fit" — what the fit reads,
   corrected.
7. `docs/storm-validation.md` and `docs/storm-term.md` — the storm term, its May 2024 validation
   against later element sets, and the pointer to the same term measured against a truth.
8. `docs/pipeline.md`, `docs/cdm-matching.md`, `docs/phase4-plan.md` — the pipeline, the matcher and
   the working record, unchanged since the benchmark.

## What the close-out did (2026-09-05)

Two passes. The first recorded and set defaults; the second fixed two things and looked.

| Item | What was done | Where |
| --- | --- | --- |
| **The fit reads only its window** | A live run's covariance fit passed no epoch bounds to the history load and read every stored element set for its objects, labelling the result with the 45-day backfill window; only a historical replay was bounded. Now every fit is bounded to `[window start, run start]`, `fit_covariance` refuses rows outside the window it is labelled with, and two tests pin it (one on the guard, one on `fit_from_history` with a store holding rows from other years). | `src/driftwatch/cli.py`, `fit_from_history`; `src/driftwatch/catalogue/history.py`, `window_bounds`; `src/driftwatch/risk/covariance.py`; `tests/test_covariance.py` |
| **The 3 September run refitted** | On a copy, with the bound in place, the original kept beside it. What the unbounded fit had read outside its window: 615,648 of 2,714,544 sets, of which 513,838 were April and May 2024 for 13,440 of 22,646 objects (the storm validation's store), 8,387 were 2022 (the Starlink validation's), and 93,423 were 19 and 20 July 2026 (the earlier run's backfill days). The delta is in README item 2 and below. | `data/conjunctions/step3-bounded/demo_20260903T160600Z` (gitignored) against `step2-attached/` |
| **Provenance defect recorded** | On the findings page beside the frame and the time offset, as the third of one class. | `README.md` item 2; `docs/screening.md`, "History for the fit" |
| **Hypothesis restated** | In the order the check supports: quiet history cannot describe storm error (primary); the detector reading a storm as a burn (secondary, only when a storm falls inside the fit window, two of seventeen its measured size). | `README.md` item 6; open item 3 here |
| **Viewer verified in a browser** | A regenerated bundle from the 3 September run, `npm run dev`, headless Chromium through Playwright, at 1500 by 1000: quiet is the scenario in force on load and again after a reload; the horizon is the first line of the conjunctions panel; under G5 the one-sentence calibration sits under the scenario control and inside the storm block's first fold, the full note heads the storm summary above its table, the sentence heads the list, and the full note is in the event detail; none of it appears under quiet; no console errors. Screenshots were looked at. | `web/src/scenarios.ts`, `storm.ts`, `conjunctions.ts`, `main.ts`, `style.css` |
| Quiet is the default (first pass) | `driftwatch report` and the viewer's bundle default to `quiet` wherever it was scored; the live viewer switches to `quiet` once the overlays land unless a scenario was carried across; a replay keeps its own. One test pins the default. | `src/driftwatch/export/report.py`, `default_scenario` |
| The horizon is the headline (first pass) | The report opens with "The horizon" before its summary; the findings page before item 1; the viewer's conjunctions panel before its counts. | `HORIZON_HEADLINE` in `report.py` and `scenarios.ts` |
| GPS-to-UTC recorded (first pass) | Beside the frame finding: a constant 137 km at every lead, invisible to every internal check, exposed only by the independent truth. | `README.md` item 2 |

**The refit's delta, in numbers** (the original 3 September fit against the bounded one, same
events, same everything else). Covariance: 610,130 sets left the fit; 222 objects moved from their
own fit to a pool (empirical 22,261 to 22,039; pooled 385 to 607); the in-track one-day sigma changed
on 21,644 of 22,039 fitted objects, median −5 per cent, tenth percentile −49 per cent, ninetieth
+10; the fleet members' own in-track sigma fell by a median 47 per cent, because their 2024 rows
were from solar maximum; the pools moved by −47 to +18 per cent, most of them down. Under `quiet`:
21 flagged events became 12 (11 lost, 2 gained; one red became two), the region changed on 285 of
6,224 events (244 robust to dilution, 41 the other way), and the ratio of the probability after to
before has a median of 0.98, a fifth percentile of 0.15 and a ninety-fifth of 2.5.
Under the storm scenarios the same: `forecast` 20 flagged events became 12 (10 lost, 2 gained), `storm-g4` 18 became 11 (9 lost, 2 gained), `storm-g5` 18 became 12 (9 lost, 3 gained), the region changing on 277 to 286 events in each, and the median of the probability ratio 0.99 with a fifth percentile of 0.13 to 0.16 and a ninety-fifth of 2.5; the fleet members in-track sigma at the encounter fell by a median 26, 20 and 17 per cent under the three, less than under `quiet` because the storm variance term is added on top and is the same in both fits. The benchmark is unaffected: its fits bound their own history to the weeks
before each window, and the guard holds on them.

Three things the verification found and this session did not fix, because they are outside the
two fixes asked for:

- **The conjunction list's name column collapses to one character per line** on the pairs whose
  flag chip is long (`dilution · low confidence · red`) beside an `operator-controlled` chip: the
  numbers column is `white-space: nowrap` and takes the row's width. Pre-existing, visible under
  `quiet` too, in every screenshot. A one-line stylesheet change; not made.
- The storm block is capped and scrolls, so under a storm scenario the summary table is below its
  first fold; its floor was raised from 190 to 250 px so the control, the scenario's line and the
  calibration sentence sit above the fold. The list loses 60 px at a 1000 px viewport.
- The bundle in `web/public/data` is regenerated from the **original** 3 September run, not the
  bounded refit, because the refit lives in a copy; the pipeline's next run, when it completes, is
  bounded by construction.

Verification of the code: `ruff`, the full test suite, and the viewer's `tsc --noEmit` pass; the
Playwright script is in the session's scratchpad, not the repository.

## Where things stand

| Item | State | Where |
| --- | --- | --- |
| **Calibration benchmark** | **Run and published.** Swarm A, B and C against ESA's `SW_OPER_SP3xCOM_2_` precise orbits; 57, 54 and 61 element sets in the quiet (20 to 27 April 2024), May 2024 storm and held-out October 2024 windows; one trial per set; manoeuvres from ESA's `SW_OPER_SC_xDYN_1B` thruster record. Its own covariance fits were always bounded, so the provenance defect did not reach it. | `README.md` item 6; `docs/calibration-benchmark.md`; `src/driftwatch/storm/precise.py` |
| **The covariance fit** | **Bounded to its window, with a guard and tests** (this close-out). The stored 3 September run's fit is the unbounded one; the bounded refit is in a gitignored copy. No pipeline run has been made with the bound. | `src/driftwatch/cli.py`; `docs/screening.md` |
| **Local-analysis path** | **Built and tested**, not yet used by anyone. | `docs/local-analysis.md`; `src/driftwatch/local.py` |
| Defaults | **Quiet everywhere; storm scenarios explicit and annotated**, now seen in a browser. | table above |
| Second review's corrections | Committed. | `docs/writeup-notes.md`, "The second review" |
| Parked items | Premises rewritten, dated 2026-09-05. | `ROADMAP.md`, parked items |
| Precondition check | Unchanged: `VERCEL_TOKEN` is still not set; only the account holder can create it. The pipeline's deploy step fails by name until it is. | `docs/pipeline.md`, "Hosting" |
| The daily pipeline | Unchanged: built, fired once on its own (2026-09-04), **no run has completed end to end**. | `docs/pipeline.md` |
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

`main`, two close-out commits on top of the four the benchmark session made. Not pushed by this
session unless the log says otherwise; **nothing was pushed before the browser verification**, as
asked.

Local state that is **not** in the repository, all gitignored deliberately:
`data/cache/swarm/` (150 precise-orbit zips and 150 thruster-record zips, about 600 MB, plus the
server listings), `data/validation/swarm_benchmark.{json,parquet}`, the 2022 and 2024 element-set
history in `data/history/` (the Starlink 2022 and Gannon validations' rows and the Swarm rows: half
a million rows that the unbounded fit read and the bounded one refuses), the bounded refit
`data/conjunctions/step3-bounded/`, and everything the earlier state-of-play listed
(`data/conjunctions/step*`, `data/spacex/`, `data/cache/`, `data/ballistic/`, `data/validation/`,
`.vercel/`).

## What has never happened

- **No pipeline run has completed end to end**, and **no deploy from CI** on either host; the deploy
  is blocked on `VERCEL_TOKEN`. Unchanged. **No pipeline run has been made with the bounded fit.**
- **No real Conjunction Data Message has been matched**, and **nobody has run `driftwatch local`**
  on real files. Both are built and tested against designed inputs only.
- **No second object class has been calibrated.** The benchmark covers three well-tracked
  satellites at 460 to 506 km.

## The first scheduled run, and why it failed (2026-09-05)

Run 6, the first run the schedule started rather than a dispatch, failed in `driftwatch screen` at
`spacex.load_trajectory` with `the time grid must be strictly increasing`. Diagnosed from the
runner's logs rather than guessed: run 5 (dispatched 09:25 UTC) and run 6 (10:35 UTC) fetched the
same 300 SpaceX files, all created at about 01:25, into the state store the Actions cache carries
between runs; the newest-version rule kept both copies because they tie on `created`, and every
epoch appeared twice. Run 4 had run with SpaceX off, so run 5 saw one copy and passed. Fixed the
same day: a tie on `created` goes to the later fetch, the loader sorts and de-duplicates each
segment's grid and splits it with a logged reason where one epoch carries two states, and
`tests/test_spacex.py` feeds it two overlapping versions and a duplicated timestamp
(`docs/spacex-ephemerides.md`, "The store holds one copy of one version per satellite").

## Open items

1. **The quiet-condition baseline** (decision open; nothing changed). The storm term's excess is not
   zero without a storm, and the benchmark shows it makes the residual worse from one to six days
   in a quiet week and twice the actual drift at seven. The `forecast` scenario applies the term
   whenever it has a coefficient. **The baseline needs a diagnosis, not a zeroing**: the excess is
   the difference between the model's quiet density and the density the set's own `B*` implies, and
   the same difference is inside the four-day-and-beyond result that helps, so zeroing the mean shift
   below some ap would remove a symptom whose cause stays in the term. Whether the quiet excess is
   the model, the coefficient or the integration is what to find out first, against this
   measurement, and the decision recorded rather than tuned.
2. **A storm-conditional covariance scale** (decision open; nothing changed). The covariance
   under-covers in a storm by the numbers in item 6 and the screening carries it unchanged. Any scale
   is a calibration on one orbit class and two storms; **it must be fitted on May 2024 and validated
   on October 2024**, held out as the benchmark held it, or it is a tuning on the number it is meant
   to predict. Not made.
3. **Why the covariance under-covers in a storm**, in the order the evidence supports (restated
   2026-09-05). **Primary:** a covariance fitted from the consistency of quiet history cannot describe
   storm-time error; nothing in how quiet fits disagree with each other says how far a storm will
   move the object, and the benchmark's own fits, bounded to the weeks before each window, under-cover
   in both storms. **Secondary, with a measured size:** the fit excludes pairs that span a detected
   manoeuvre, the detector reads an unexplained change in semi-major axis as a burn, and a storm's
   drag is such a change, so where a storm falls inside the fit window the detector can discard the
   storm-time intervals and calibrate the fit on the quiet days either side (it read the 11 October
   storm as a burn on Swarm A and C). It matters only when a storm falls inside the window: the
   3 September run's window held no interval at Kp 6 or above, so none of its 17,033 in-window
   exclusions coincide with one; in the May 2024 rows the unbounded fit had read, 155 of 4,617
   exclusions coincide with Kp 6 or above, 145 of them on Starlinks, and **2 of the 17 free-flying
   objects whose stored history spans the 10 to 13 May storm, both debris, had the storm interval
   excluded as a burn**. Two of seventeen, on one storm, is its size. Nothing in the detector was
   changed. The counts are reproducible from `objects.parquet`, `data/history/` and CelesTrak's
   `SW-All.csv`; the script is not in the repository.
4. **The conjunction list's name column collapses** on rows with a long flag chip (found by the
   browser verification; pre-existing; not fixed). See the list above.
5. **The held-out window holds two storms** (7 to 8 October, then 10 to 11), and the sets issued
   between them over-predict the decay for the quiet days that followed; the `B*`-across-a-storm
   explanation is an inference. Swarm's TU Delft density products (`SW_OPER_DNSxPOD_2_`) would
   separate the atmosphere's error from the object's response and are the next thing to read.
6. **Generalisation.** Whether the ratio of actual error to consistency found here holds for debris,
   for higher orbits, or for objects the network tracks less often is not measured; laser-ranging
   objects and other GNSS-carrying missions with public precise orbits are the way to extend it.
7. Everything the earlier state-of-play listed and this session did not touch: the attached-object
   filter's runner reading (settled in `docs/pipeline.md`, "Reproducibility"), the deploy and the
   archive never having run on a runner, the `spacex-ephemeris+sgp4-fit` covariance path never
   exercised by real data, the storm's effect on how often an operator's plan is revised, and the
   NRLMSIS storm bias recorded and not applied.

## The runner and the ceiling

Unchanged from the earlier state-of-play: the ceiling in `docs/pipeline.md` is left as written until
a second completed run confirms the first, and the positioning it implies is unchanged — a
university group, a single-spacecraft mission, a small national operator — which is who the CDM
matcher and the local path are for.

## What happens next

Nothing, until a user supplies a case: an operator's files through `driftwatch local`, or a real
Conjunction Data Message through the matcher. The two decisions above are made against that case
and the benchmark, and recorded, not tuned.
