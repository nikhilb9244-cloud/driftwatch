# State of play

Written 2026-09-05 (late evening UTC), at the end of the session that took an external review's
corrections, changed the plan and moved the hosting. It supersedes the 2026-09-03 version and,
like it, records **where things stand and what is unresolved** without restating the reasoning,
which lives in the pages it points at. A snapshot; where it disagrees with a plan or a methods
page, the page wins.

## Reading order for a fresh session

1. `README.md`, the **findings and corrections** page at the top — the two-page statement of
   what this project has found and what it has had to take back, with dates.
2. `ROADMAP.md`, "Plan change, 2026-09-05" — Phase 4 now stops at the pipeline; Steps 3 to 7
   and the OSC validation are deferred indefinitely and replaced by two items, both built.
3. `docs/storm-term.md`, "Corrected 2026-09-05: operator-controlled objects" — the correctness
   error the review found, what it moved, and the 42 unscoreable Starlinks it explained.
4. `docs/storm-validation.md`, "By lead time" — where the storm term's skill actually lives.
5. `docs/writeup-notes.md` — additive; the EOS SAT-1 entry now leads with its region.
6. `docs/pipeline.md` — the daily run, the Vercel deploy, and the first scheduled run's numbers.
7. `docs/cdm-matching.md` — the CDM parser and matcher, and why the Kelvins rows are its test
   input and not a validation.
8. `docs/phase4-prompt.md` and `docs/phase4-plan.md` — the original specification and the working
   record, with the deferred steps still described.

## Where Phase 4 stands

| Item | State | Where |
| --- | --- | --- |
| Precondition check | **The four original Actions secrets are verified present** (`gh secret list`, 2026-09-05, from the repository-owning account); this closes the 2026-09-03 open item. Two of the three Vercel secrets, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`, were set by this session. **`VERCEL_TOKEN` is not set** and only the account holder can create it (Vercel dashboard, Account Settings, Tokens). Until it is, the pipeline's deploy-credentials check fails the run by name. | `docs/pipeline.md`, "Hosting" |
| **1. Stage C on the published states** | Built and reviewed, unchanged. | `phase4-plan.md` §Step 1 |
| **2. The daily pipeline** | **Built; the schedule has fired once on its own** (2026-09-04, run `33867306871`, 11:18 UTC): every step through `check-bundle` passed — the four scenarios on a runner for the first time, in 23 minutes — and the Cloudflare upload failed on the token's missing Pages permission. The deploy is now Vercel. **No run has yet completed end to end**, so no release archive, no stability file and no store commit has been written by a runner. | `docs/pipeline.md` |
| Warning-stability read path | Built; no analysis, deliberately. | `pipeline.md` §"The index warning stability reads" |
| **2A. Office of Space Commerce validation** | **Deferred indefinitely.** Read, nothing fetched. | `ROADMAP.md`, plan change; `phase4-plan.md` §"Step 2A preparation" |
| 3 to 7. Landing page, export, visual pass, parked items, write-up | **Deferred indefinitely**: they change nobody's decision while no operator uses the output. | `ROADMAP.md`, plan change |
| Replacement 1: findings and corrections page | **Built**, at the top of the README. | `README.md` |
| Replacement 2: CDM parser and matcher | **Built**: `src/driftwatch/cdm/`, `driftwatch cdm parse | match | from-kelvins`, tests against the Kelvins rows. No real message has been matched yet. | `docs/cdm-matching.md` |

## What changed on 2026-09-05

The external review found two correctness errors and a set of framing problems. All are fixed,
each with a dated note where the old claim stood rather than a silent rewrite.

- **The storm term displaced operator-controlled objects.** A SpaceX-served trajectory, or
  CelesTrak's supplemental fit to it, already carries the operator's drag model and burns, so the
  storm excess over SGP4's atmosphere is undefined for it; a station-kept primary will burn rather
  than drift. Those objects now get no mean shift (no term at all on an operator's trajectory; the
  in-track variance kept for a manoeuvring object on a tracking-derived set), are labelled
  `operator-controlled/<reason>`, and an event with one such side is judged on its free-flying
  side alone. The 36 to 42 "unscoreable" Starlinks of the earlier runs were this error seen from
  the other side: thrusting plans read as drag. Every scenario of the 2026-09-03 run was rescored:
  no event is unscoreable; `forecast` went from 0 red, 16 yellow, 71 unscoreable to 1 red, 19
  yellow, 0 (`storm-g4` 0/15/71 to 1/17/0, `storm-g5` 0/13/70 to 1/17/0), the one red being the
  EOS SAT-1 dilution flag; the relative-to-absolute ratio over the 981 events with both objects
  free-flying is 1.85 under every scenario; and **the Phase 3 headline — a storm lowers the
  probability on most events — is withdrawn as a finding of these runs**, because the lowering
  lived entirely in events with an operator-controlled side (median `pc / pc_variance_only` 0.67
  there against 0.98 on the both-free-flying events, before and after alike).
- **The EOS SAT-1 red is in the dilution region at low confidence** (maximum probability at 0.85
  times the covariance) and the write-up notes did not say so. Every mention now leads with the
  region and the confidence — the notes, the report, the viewer's chips, header and detail view.
  On the public page, fleet members other than stations are shown by category and NORAD id until
  their operator has agreed to appear.
- **The lead-time split.** On the free-flying measured-coefficient population the storm term's
  skill is concentrated at three to four days of lead and is near zero inside two (sign agreement
  39 and 41 per cent at one and two days against 91 and 96 at three and four). The table is on the
  validation page and `driftwatch validate gannon` now writes it.
- **Precedent.** Flohrer, Krag and Klinkrad (2008) and Parker and Linares (2024) are cited on the
  methods page with what this project does relative to each.
- **The supplemental workflow** had failed every three hours since 2026-09-04 on nine-digit
  placeholder NORAD ids in CelesTrak's supplemental file; the propagator now initialises an
  out-of-range id as zero. A day of supplemental versions was lost.
- **Hosting moved from Cloudflare Pages to Vercel.** The project did not exist when the session
  started and was created (team `nikolodeon-s-projects`, root directory `web`, framework Vite, no
  Git connection); `scripts/deploy-vercel.ps1` and the pipeline build with the Vercel CLI, run
  `check-bundle` over the prebuilt output, and deploy `--prebuilt`. The Cloudflare project and its
  URL are retired; `scripts/deploy-pages.ps1` stays, marked retired, until the first Vercel
  production deploy has succeeded.

## What is committed, and what is not

`main`, pushed. Three branches on the remote: `main`, `pipeline-store`, `supplemental-store`.

Local state that is **not** in the repository: `data/conjunctions/step1-baseline`, `step1-served`
and `step2-attached` (the 2026-09-03 runs; `step2-attached` is the one rescored on 2026-09-05 and
now carries `storm/<scenario>/2` in its model versions), `data/spacex/`, `data/history/`,
`data/cache/`, `data/ballistic/`, `data/validation/` (whose `gannon.json` predates the by-lead
table; the parquet beside it is what the table was computed from), and `.vercel/` (the project
link and the pulled environment). All gitignored deliberately.

## What has never happened

- **No pipeline run has completed end to end.** The 2026-09-04 run reached the deploy.
- **No deploy from CI**, on either host. The first Vercel deploy was a preview made by hand from
  this machine with `scripts/deploy-vercel.ps1` on 2026-09-05; its URL is in the session report
  and in `docs/pipeline.md` once the first production deploy follows it.
- **No release archive and no stability file written by a runner.**
- **No real Conjunction Data Message has been matched.** The matcher has run only against the
  Kelvins rows, where agreement is by construction.

## Open items

1. **The attached-object filter dropped nothing on the runner, and 2,170 candidates locally.**
   Still unexplained. The 2026-09-04 run reported the same ten pairs and, again, dropped no
   candidates — but it did not reach the archive, so the query that settles it (any `(25544,
   25575)` row in a runner's `events.parquet`) still cannot be made. Its event count was 5,903
   against the local filtered 6,224, which is the same weak evidence as before.
2. **The deploy, the stability index, the archive and the store push have never run on a
   runner.** Everything before them now has (2026-09-04). The deploy is blocked on `VERCEL_TOKEN`.
3. **The 22 per cent NRLMSIS storm bias, the validity split and the lead-time structure all rest
   on one storm.** A second storm in the observed record is the thing that would move any of them
   from a record to a calibration, and none of them is tuned.
4. **No warning-stability analysis, deliberately** — nothing should be concluded from a pipeline
   that has not run for a week, and it has not yet run for a day.
5. **The `spacex-ephemeris+sgp4-fit` covariance path has never been produced by real data.**
   Correct and tested; unexercised.
6. **The storm's effect on how often an operator's plan is revised is real and unmodelled.** An
   object on an operator's trajectory now gets no storm term at all, which is right for the mean
   and arguable for the variance: SpaceX revised plans constantly through May 2024. The
   supplemental store accumulates exactly the versions that would measure it, over a storm.
7. **`gannon.json` on disk predates the by-lead table.** Rerunning `driftwatch validate gannon`
   refreshes it; the sample is drawn from the latest snapshot, so the population may differ
   slightly from the 2026-09-02 one the docs quote.

## The runner and the ceiling

The 2026-09-04 run measured the scenarios at 0.12 s per object per scenario on a runner against
the 0.34 s measured locally, and the 2026-09-05 correction computes no density track for the 1,681
of 2,944 objects on an operator's trajectory. Both move the fleet ceiling in `docs/pipeline.md`
outward, by roughly a factor of three each; the ceiling is left as written there until a second
completed run confirms the first. The positioning it implies is unchanged: a university group, a
single-spacecraft mission, a small national operator — which is who the CDM matcher is for.
