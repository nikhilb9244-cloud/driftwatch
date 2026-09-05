# State of play

Written 2026-09-05, at the close-out that followed the calibration benchmark. It supersedes the
earlier 2026-09-05 version and, like it, records **where things stand and what is unresolved**
without restating the reasoning, which lives in the pages it points at. A snapshot; where it
disagrees with a plan or a methods page, the page wins. **Nothing else is built until a user
supplies a case.**

## Reading order for a fresh session

1. `README.md`, the **findings and corrections** page at the top. It now opens with the horizon,
   ahead of any probability: five days quiet, two days in the May 2024 storm, one day in the
   October 2024 storm, at the screening box's 25 km in-track half-width and the 95th percentile of
   trials. Six items follow; item 6 is the calibration against ESA's precise orbits and carries the
   open hypothesis about the manoeuvre detector and the two decisions the benchmark leaves open.
2. `docs/calibration-benchmark.md` — the page `driftwatch validate swarm` writes: three windows,
   four things by lead bin, every source with its origin and derivation.
3. `ROADMAP.md`, "Plan change, 2026-09-05" and the paragraph added after it — Phase 4 stops at the
   pipeline; the benchmark and the local path are the one bounded experiment and the one optional
   path added after the second review; the parked items have their premises rewritten, not deleted.
4. `docs/local-analysis.md` — `driftwatch local`: an operator's own ephemerides, messages and records
   through the provenance check, the CDM matcher and the same benchmark, with the network refused.
5. `docs/writeup-notes.md` — additive; the last two entries are the second review and the benchmark.
6. `docs/methods.md`, "Uncertainty and probability" — what the covariance is, and what one
   calibration found about it.
7. `docs/storm-validation.md` and `docs/storm-term.md` — the storm term, its May 2024 validation
   against later element sets, and the pointer to the same term measured against a truth.
8. `docs/pipeline.md`, `docs/cdm-matching.md`, `docs/phase4-plan.md` — the pipeline, the matcher and
   the working record, unchanged since the benchmark.

## What the close-out did (2026-09-05)

Close-out only; no new development. Each item is on the findings page or in the code named.

| Item | What was done | Where |
| --- | --- | --- |
| **Quiet is the default** | `driftwatch report` and the viewer's bundle default to `quiet` wherever it was scored (they took the first scenario by name before, which was `forecast`). The live viewer switches to `quiet` once the overlays land unless a scenario was carried across; a replay keeps its own, because entering replay is the explicit choice. The pipeline already passed `--scenario quiet`. One test pins the default. | `src/driftwatch/export/report.py`, `default_scenario`; `src/driftwatch/cli.py`; `web/src/main.ts` |
| **Every storm number carries the calibration** | One plain-text note, quoted from the benchmark and not computed: the covariance under-covers in a storm (two sigma holds 65 to 80 and 62 to 75 per cent against 95), the storm term helps only from about four days and hurts inside three, hurts from one to six days in a quiet week (the quiet-week bias), and over-corrects at seven days (about 1.5 times the actual in May). It heads the report's storm section, sits in the bundle's caveats, and in the viewer is shown under the scenario control, above the storm summary table and in the event detail whenever the scenario is not `quiet`. | `STORM_CALIBRATION_NOTE` in `report.py` and `web/src/scenarios.ts`; `web/src/storm.ts`; `web/src/conjunctions.ts` |
| **The horizon is the headline** | The report opens with "The horizon" before its summary; the findings page opens with it before item 1. | `HORIZON_HEADLINE` in `report.py`; `README.md` |
| **GPS-to-UTC recorded as a correction** | Placed beside the frame finding (item 2) as the same class of error in the time system: a constant 137 km in-track offset at every lead, invisible to every internal check, exposed only by the independent truth. | `README.md` item 2 |
| **Manoeuvre-detector hypothesis recorded** | The number below; not acted on. | `README.md` item 6; open item 3 here |
| **Two open decisions recorded** | Quiet-condition baseline and storm-conditional covariance scale, as open, with the constraints on each. | `README.md` item 6; open items 1 and 2 here |

Verification: `ruff`, the report, storm-export and export tests, and the viewer's `tsc --noEmit`
pass; the 3 September run's report was regenerated under the default (it came out `quiet`, with the
horizon first) and under `storm-g5` (the calibration note heads the storm section), and left under
`quiet`. The viewer changes are type-checked only: **nobody has opened them in a browser**, and no
bundle was regenerated for `web/public/data`.

## Where things stand

| Item | State | Where |
| --- | --- | --- |
| **Calibration benchmark** | **Run and published.** Swarm A, B and C against ESA's `SW_OPER_SP3xCOM_2_` precise orbits; 57, 54 and 61 element sets in the quiet (20 to 27 April 2024), May 2024 storm and held-out October 2024 windows; one trial per set; manoeuvres from ESA's `SW_OPER_SC_xDYN_1B` thruster record (two in 150 satellite-days, both also found by the precise-orbit step detector). Results in `docs/calibration-benchmark.md` and README item 6; per-trial file `data/validation/swarm_benchmark.parquet` (gitignored). | `README.md` item 6; `docs/calibration-benchmark.md`; `src/driftwatch/storm/precise.py` |
| **Local-analysis path** | **Built and tested**, not yet used by anyone: `driftwatch local` runs a stored run's provenance check, the CDM matcher and the ephemeris benchmark over an operator's own files with every outbound request refused. | `docs/local-analysis.md`; `src/driftwatch/local.py`; `tests/test_local.py` |
| Defaults | **Quiet everywhere; storm scenarios explicit and annotated** (this close-out). | table above |
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

`main`, one commit for this close-out on top of the four the benchmark session made. Not pushed by
this session unless the log says otherwise.

Local state that is **not** in the repository, all gitignored deliberately:
`data/cache/swarm/` (150 precise-orbit zips and 150 thruster-record zips, about 600 MB, plus the
server listings), `data/validation/swarm_benchmark.{json,parquet}` (the benchmark's outputs; the
page in `docs/` is regenerated from them), the 2022 and 2024 element-set history in `data/history/`
(the Starlink 2022 and Gannon validations' rows and the Swarm rows; see open item 3 for what they
did to the 3 September fit), and everything the earlier state-of-play listed
(`data/conjunctions/step*`, `data/spacex/`, `data/cache/`, `data/ballistic/`, `data/validation/`,
`.vercel/`).

## What has never happened

- **No pipeline run has completed end to end**, and **no deploy from CI** on either host; the deploy
  is blocked on `VERCEL_TOKEN`. Unchanged.
- **No real Conjunction Data Message has been matched**, and **nobody has run `driftwatch local`**
  on real files. Both are built and tested against designed inputs only.
- **No second object class has been calibrated.** The benchmark covers three well-tracked
  satellites at 460 to 506 km.
- **Nobody has seen the quiet default or the calibration note in a browser.** Type-checked and
  reasoned about; not looked at.

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
3. **The manoeuvre-detector hypothesis** (recorded 2026-09-05; not acted on). The covariance is fitted
   from pairs of element sets that span no detected burn, and the detector reads an unexplained
   change in semi-major axis as a burn; the benchmark watched it read the 11 October storm as a burn
   on Swarm A and C. The hypothesis: the production fit has been excluding storm intervals and is
   therefore calibrated on quiet-biased history, which would explain part of the under-coverage in
   a storm. **Checked cheaply**, on the 3 September run's 2,944 objects in events, by the maximum
   observed Kp inside each excluded interval (the interval from the previous set's epoch to the jump
   epoch):
   - The fit's 45-day window, 21 July to 3 September 2026, had **no** three-hour interval at Kp 6 or
     above (maximum 5.7). **0 of the 17,033** excluded intervals inside the window coincide with one;
     1,148 coincide with Kp 5 or above.
   - The fit also read element sets from outside its window: **a live run passes no epoch bounds to
     the history load** (`fit_from_history` bounds only a historical run), so the 3 September fit read
     every stored row for its objects, including the May 2024 rows the Gannon validation had stored
     for 1,794 of the 2,944 and the 2022 rows the Starlink validation had stored for 9, while its
     covariance block labels the window 21 July to 3 September. Among those out-of-window rows, **155
     of 4,617** excluded intervals coincide with Kp 6 or above, on 127 objects: 145 on Starlinks
     (`known` manoeuvrers), 7 on payloads flagged `observed`, and **3 on debris, which does not
     manoeuvre**, two of them 10 to 11 May 2024 at Kp 9. Most of those 2024 rows end at the
     storm's onset (they came from the pre-storm snapshot pulls): only 40 of the 2,944 have stored
     history spanning 10 to 13 May, 17 of them free-flying, and **2 of those 17, both debris, had
     the storm interval excluded as a burn**.
   - The 1 September run, made before those rows were stored, has all 17,581 of its excluded
     intervals inside its window and 0 at Kp 6 or above.
   - Consistent with the hypothesis; not a test of it. The test is the coverage of a fit made with
     and without the storm intervals, against a truth. The out-of-window rows in a live fit are a
     second observation, recorded here and not fixed: the fit for six in ten of the objects in
     events was made on their 2026 window plus a fortnight of 2024 rows, storm-time for a few.
   The script is not in the repository; the counts are reproducible from `objects.parquet`,
   `data/history/` and CelesTrak's `SW-All.csv`.
4. **The held-out window holds two storms** (7 to 8 October, then 10 to 11), and the sets issued
   between them over-predict the decay for the quiet days that followed; the `B*`-across-a-storm
   explanation is an inference. Swarm's TU Delft density products (`SW_OPER_DNSxPOD_2_`) would
   separate the atmosphere's error from the object's response and are the next thing to read.
5. **Generalisation.** Whether the ratio of actual error to consistency found here holds for debris,
   for higher orbits, or for objects the network tracks less often is not measured; laser-ranging
   objects and other GNSS-carrying missions with public precise orbits are the way to extend it.
6. Everything the earlier state-of-play listed and this session did not touch: the attached-object
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
