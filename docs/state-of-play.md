# State of play

Written 2026-09-03 (22:44 UTC), at the end of the session that built Phase 4 Steps 1 and 2, so
that the next session can pick the work up without re-reading the phase plans end to end. It
records **where things stand and what is unresolved**. It does not restate the reasoning behind
any decision — that is in the plan files, and this page points at them.

This file is a snapshot and will go stale. Where it disagrees with a phase plan, the phase plan
wins.

## Reading order for a fresh session

1. `docs/phase4-prompt.md` — the specification for the phase. Steps 1 to 7, with acceptance
   criteria at the end.
2. `docs/phase4-plan.md` — the working record: decisions before the code, results after it, a
   review section per step, wrong turnings left beside their corrections.
3. `docs/pipeline.md` — the daily run: runtime budget, where each piece of state lives, the
   retention rule, the failure model.
4. `docs/writeup-notes.md` — the findings Step 7 has to name, with their numbers. Additive;
   nothing is deleted from it.
5. `ROADMAP.md` — the phase structure, the parked items, the capability targets and the
   successor projects.

For the physics and its limits: `docs/methods.md` (every approximation, with the largest one
named), `docs/screening.md`, `docs/density-and-drag.md`, `docs/storm-term.md`,
`docs/storm-validation.md`. For the data: `docs/data-sources.md`, `docs/data-schema.md`,
`docs/spacex-ephemerides.md`. For the front end: `docs/design-brief.md`.

## Where Phase 4 stands, step by step

| Step | State | Where |
| --- | --- | --- |
| Precondition check | **Run twice.** Remote and `.gitignore` pass. The four Actions secrets are **still unverified** — `gh` here is authenticated as an account with `pull` only, so listing secret names returns 403. That is "could not verify", not "absent". | `phase4-plan.md` §"Prompt additions", both check tables |
| **1. Stage C on the published states** | **Built and reviewed.** Stages B and C both screen SpaceX's published states; the fit residual applies per event; states on a 120 s grid, rotated MEME/J2000 → TEME, split at every discontinuity. Four review items closed. | `phase4-plan.md` §Step 1 and §"Step 1 review"; `docs/spacex-ephemerides.md` |
| **2. The daily pipeline** | **Built, never completed.** `.github/workflows/pipeline.yml` plus `docs/pipeline.md`. One real runner attempt, which failed — see below. | `phase4-plan.md` §Step 2 |
| Warning-stability read path | **Built** after the Step 2 review (`src/driftwatch/stability.py`, `driftwatch stability`, `tests/test_stability.py`). The **analysis is not built**, and is not meant to be yet. | `phase4-plan.md` §"The read path warning stability needed"; `pipeline.md` §"The index warning stability reads" |
| **2A. Office of Space Commerce validation** | **Read, nothing fetched.** The user's guide is read in full, the terms confirmed, the structure and the decomposition question worked out, the three-round plan written. No byte of the 20.73 GB has been downloaded. | `phase4-plan.md` §"Step 2A preparation" |
| 3. The public landing page | **Not started.** | `phase4-prompt.md` §Step 3 |
| 4. CSV and JSON export per fleet | **Not started.** | `phase4-prompt.md` §Step 4 |
| 5. Visual pass, mobile layout, paint budget | **Not started.** Note that Phase 3 Step 5 already built the scenario control, the Δ-against-quiet column, the unscoreable section, the encounter plane's shift arrow and the replay scrubber **to this spec, and they are not to be rebuilt**. | `phase4-prompt.md` §Step 5; `docs/design-brief.md` |
| 6. Two of the six parked items | **Not started.** Order fixed and argued: **commandability first, manoeuvre burden second**. The other four are parked again with the reasoning attached. | `phase4-prompt.md` §Step 6; `ROADMAP.md` Phase 4 |
| 7. The write-up | **Not started.** Five entries already accumulated. | `docs/writeup-notes.md` |

## What is committed

`main`, tree clean, pushed. Three branches on the remote: `main`, `pipeline-store` and
`supplemental-store` — both stores now exist and both bootstrap themselves, which was not true
this morning.

Local state that is **not** in the repository, and that a fresh clone will not have:
`data/conjunctions/step1-baseline`, `step1-served` and `step2-attached` (the three runs every
Step 1 and Step 2 number in the plan came from), `data/spacex/` (300 ephemerides,
undistributable), `data/history/`, `data/cache/`, `data/ballistic/`. All are gitignored
deliberately; `check-bundle` exists to keep the SpaceX files out of anything published.

## What has never happened

- **No pipeline run has ever completed.** See the attempt below.
- **No deploy from CI.** The site has only ever been published by hand with
  `scripts/deploy-pages.ps1` (Cloudflare Pages project `driftwatch`; branch `main` is
  production, any other branch name gets its own preview URL).
- **No release archive and no stability file has ever been written by a runner.** Both steps run
  after the deploy, and no run has reached the deploy.
- **The four Actions secrets have never been confirmed to exist** by anything but the operator's
  word.

## The first real runner attempt, and what it cost

`workflow_dispatch`, 2026-09-03 19:10 UTC, run `33794896936`. **Failed at "Score every scenario"
after 29m36s**, which is exactly the failure the runtime-budget exercise predicted the same
evening: the workflow never ran `driftwatch ballistic`, and every scenario but `quiet` refuses
without a ballistic coefficient per object. **The step is now in the workflow and pushed, and has
not been re-run.** The next scheduled run — 06:20 UTC daily — is the first test of the fix.

The steps that did run are the first runner numbers this project has, and they are worth putting
beside `pipeline.md`'s planning table, which was measured locally and multiplied by 1.3 to 1.8:

| Step | Local (`pipeline.md`) | Planned on a runner | **Observed** |
| --- | ---: | ---: | ---: |
| `fetch` + `weather` | ~1 min | ~1 min | **17 s** |
| Seed screen (first run only) | ~4 min extra | — | **13 m 33 s** |
| `spacex latest`, 300 ephemerides | 26 min | ~26 min | **5 m 00 s** |
| `screen` + history/fit + `risk quiet` | 10.1 min | 13 to 18 min | **10 m 23 s** |
| `check-run` | — | — | **1 s** |

Two things follow, and they point in opposite directions. **The ephemeris fetch is five times
faster from a runner than from this machine** — 5 minutes against 26 — which softens the term
`pipeline.md` calls the second ceiling and makes the 300-object cap look generous rather than
binding. And **the CPU-bound screening came in at local speed, not 1.3 to 1.8 times it**, which
would make the fleet-size ceiling below conservative. Neither conclusion is safe yet: **the
scenarios are 67 of the local 113 minutes and they have never run on a runner at all.** The
budget in `pipeline.md` stands until a run completes; these figures are recorded here rather than
folded into it.

## Open items, from the last three reviews

Numbered so a review can dispose of them individually. Items 1 and 2 are new in this file and
have not been through a review yet.

1. **The attached-object filter dropped nothing on the runner, and 2,170 candidates locally.**
   *Unexplained, and it should be settled before the site is ever published from CI.* Same code,
   same ten pairs found, opposite outcomes:

   | | Local, Windows (`step2-attached`) | Runner, Linux (`33794896936`) |
   | --- | ---: | ---: |
   | `attached_pairs_excluded` | 10 | 10 |
   | `attached_candidates_dropped` | **2,170** | **0** |
   | Candidates into Stage C | 171,359 | 170,752 |
   | Events | 6,224 | 5,903 |

   The runner's log says it plainly: `Stage B: 10 pair(s) held attached or co-orbiting and
   excluded, dropping 0 candidate(s)`, naming the same ten NORAD ids. There are two readings and
   they have very different consequences. Either the pair match in `stages.py` (a
   `pd.MultiIndex.isin` over the two id columns, around line 719) silently fails on that
   platform — in which case **the ISS's own docked hardware is back in the published table**,
   which is the fault the front page caught once already — or Stage B genuinely bracketed no
   candidates for those pairs on that snapshot, in which case the filter had nothing to do and
   only the counter alarms. The runner's event count (5,903, *below* the local **filtered** 6,224)
   is weak evidence for the second reading, but the two windows start three hours apart, so it
   settles nothing.

   **The query that settles it**: dispatch or wait for a run that reaches the archive, then look
   in its `events.parquet` for any pair `(25544, 25575)` — ISS against Unity. Any row at all is
   the first reading. Note also that `tests/test_screening.py:932` asserts
   `summary["attached_candidates_dropped"] == result.stage_b.n_attached_candidates`, which
   compares the field to its own source and so can never fail; no test asserts a non-zero drop.

2. **Everything after `check-run` is untested on a runner.** The four scenarios, `storm-check`,
   the export, the npm build, `check-bundle`, the Pages deploy, `stability`, the release upload
   and the store push have all run only on this machine. The scenarios are also where the whole
   runtime risk sits.

3. **The Actions secrets are unverified** (precondition check, both runs). Needs a `gh` session
   with admin on the repository, or a look at the web interface. Until then the Pages deploy and
   the Space-Track fetch in CI are taken on trust.

4. **No warning-stability analysis, deliberately** (Step 2 review). The index and the read path
   exist; survival rates, false-alarm rates, lead-time curves and a viewer panel do not, and
   nothing should be concluded from a pipeline that has not run for a week. The two runs indexed
   so far are **not** evidence about stability — Step 1 changed what the Starlink secondaries are
   screened on in between — and the write-up must not use them as such.

5. **The `spacex-ephemeris+sgp4-fit` covariance path has never been produced by real data**
   (Step 1 review, item 3). Correct, tested end to end in `tests/test_spacex.py`, and still
   unexercised by any run: on the 2026-09-03 run every unserved event on the sixteen mixed
   objects fell past the covariance horizon too. It belongs in the limitations as a sentence.

6. **Three questions the Phase 3 Step 5 review left standing**, all now Step 5's business:
   whether `scenarios.json` should be split per scenario (1.25 MB for three, ~2 MB for five, paid
   all at once by a reader on a phone); whether the storm summary's two populations should stay a
   table at 360 px or lead with the validated figure and subordinate the indicative one; and the
   Sun imagery budget, now 121 kB of inline thumbnails plus 360 kB per full frame. The fourth —
   the replay being a page reload — was answered and built.

## The OSC dataset structure question

Nothing has been fetched. The question the step turns on, and its answer, so it need not be
re-derived: **the dataset decomposes by file but not by test.** It is one OCM per object (per
candidate), so members can be selected by name — but a `.tar.gz` has no index, so extracting a
subset still means streaming the whole 20.73 GB once. That makes it a transfer cost paid once and
a storage cost never paid. The binding constraint is the guide's **ALL vs ALL** requirement:
all-vs-all over a catalogue that size is ~3.4 × 10⁸ pairs, of order **a week** of Stage B on this
machine, so a subset is not a saving — it is the difference between a step that exists and one
that does not.

The subset that keeps both directions of the claim exact is a **closed** one: choose S, screen
all-vs-all within S, and compare against the key restricted to pairs with both objects in S.
Because the key is itself all-vs-all, its restriction to S is the exact truth for S — nothing is
missed by construction and nothing is falsely called extra. Build S as (1) every synthetic
object, the ~600 ids in the 90006–90190, 95000–95407, 99000–99008 and 99996–99999 ranges, which
are the stressing cases driftwatch has never been tested on; (2) every TLE-derived object the key
pairs with one of those, so each edge case keeps its real background; (3) a documented random
sample of the rest.

Three rounds, and **Round 0 needs no tarball at all**: the answer key carries both objects' J2000
state at TCA and both UVW covariances, so feeding driftwatch's encounter-plane construction those
exact inputs tests the scoring path against a government reference from a 200 MB file — and
like-for-like, because the key's `prob` is Alfano (2004) and `pc_alfano` already sits beside the
default. Do that first; if it disagrees, nothing downstream is worth downloading.

Two things not to get wrong. **driftwatch's `box_ric_km = (2, 25, 25)` is exactly the SFSH
near-Earth volume** (both are half-widths), and the spherical key is reachable today by setting
the watch radius to 10 km and the box to zero. And the headline claim is about **screening** —
which events are found, where TCA is placed, what the miss distance is — because the guide says
outright that direct Pc comparison requires the same Pc method and is not a key metric of the
dataset. Full detail, including the five rules driftwatch does not implement and the file-size
disagreement to check on download, is in `phase4-plan.md` §"Step 2A preparation".
`docs/writeup-notes.md` carries why this is a stronger claim than Kelvins, and the three caveats
that have to travel with it.

## The warning-stability index

One narrow file per run, `data/stability/<fleet>/<run_id>.parquet`, on the `pipeline-store`
branch rather than in the release archive. Written by `driftwatch stability <run>` after the
deploy and before the archive; read with `driftwatch stability --pair A,B` or `--series <id>`.

The thing to carry forward is **why identity is hard**, because it decided the schema: an
`event_id` is `<snapshot stamp>:<primary>:<secondary>:<tca to the minute>`, and the snapshot stamp
changes daily by construction while TCA itself moves as the orbits are refitted, so **joining on
`event_id` finds nothing**. A series is assembled instead on the object pair plus TCA within a
ten-minute tolerance, greedily, nearest first, one event to one series. Measured over two real
runs 43 hours apart: 1,756 series continued, TCA moved a median 0.3 s, 4.5 s at the 95th
percentile and 20.8 s at most — thirty times inside the tolerance, and a hundred times clear of
the ~46-minute gap between successive passes of one pair. Every row carries its own `dt_tca_s`,
so the tolerance stays checkable from the files rather than from that table.

Two decisions that will look wrong until the reasoning is read. **Every event is indexed, not the
flagged ones**: flagged events span 0.53 to 28.3 km, the whole screening volume, because the flag
is decided by the covariance and not by the miss, so there is no cut that admits the warnings —
and an event first indexed on the day it flags has no history behind it, which is the failure the
index exists to prevent. What is cut is scenarios instead: `quiet` and `forecast` only. And **one
immutable file per run, not one file rewritten**: git keeps every version of a rewritten file in
full, so a monthly file rewritten daily costs about fifteen times its own size in branch history.
330 KB a run for two scenarios, 27 bytes a row; a year is ~120 MB against the 3.1 GB of archives
it saves downloading. A test pins the byte budget, because a column added without thinking is a
year of files.

## The scoring ceiling, and who this can serve

The binding constraint on the daily pipeline is the **four storm scenarios**, and what they scale
with is not the number of primaries but the number of **distinct objects appearing in an event** —
two density tracks each, per scenario. Measured at **0.34 s per object per scenario**, with only
a 6 % spread across all four, so no scenario is materially cheaper than another.

| | |
| --- | --- |
| Fixed cost on a runner | ~51 to 60 min |
| Left for scoring under the six-hour job limit | ~5.0 to 5.2 h |
| Objects in events that buys | **7,300 to 10,500** |
| At this fleet's mean of 490 objects a primary | **15 to 21 primaries** |
| If every primary were EOS SAT-1-like (1,587 objects) | **5 or 6** |
| If every primary were ISS-like (81 objects) | **90 to 130** |

Two measurements make that arithmetic legitimate rather than a guess: primaries barely share
secondaries (overlap factor **1.01**, so objects-in-events is linear in fleet size), and a primary
is not a unit — the six range from 81 distinct secondaries to 1,587, a twentyfold spread, and
EOS SAT-1 alone is 4,222 of the run's 6,224 events.

**What it implies about who this can serve.** Fifteen to twenty-one satellites is a university
group, a single-spacecraft mission, a small national operator, an SME with a handful of birds —
which is precisely the audience Step 7 is written for and the one Phase 5 goes looking for. It is
**not** a constellation operator and not an SSA provider screening a catalogue: at 5 or 6
primaries for a fleet crossing the Starlink shells, even a twenty-satellite constellation in a
busy orbit does not fit in a day. So the honest positioning is that the pipeline serves the
operator who has nobody doing this for them, and stops well short of the operator who could pay
most for it. That is worth stating on the landing page rather than discovering in Phase 5.

Two caveats keep it from being a hard limit. **Storage and runtime are different ceilings** and
give out at different points: the archive is good to a tenfold fleet, the runtime to about two
and a half to three and a half times the demo fleet — so runtime fails first, by a factor of
three, and the two should not be quoted as one number. And **the first lever is structural, not
numerical**: the scenarios are independent by construction and the six-hour limit is per job, so
fanning them into four parallel jobs turns 67 minutes of scoring into 17 and moves the ceiling
out by roughly four, into the region where the ephemeris fetch binds instead — and nothing is
approximated to buy it. The cost is passing the run directory between jobs as an artifact and
rejoining the risk files before the export. `pipeline.md` §"The levers, in the order they should
be spent" has the other three. Note finally that the observed runner figures above may make this
whole ceiling conservative; that cannot be claimed until the scenarios have run on a runner once.
