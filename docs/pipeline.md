# The daily pipeline

`.github/workflows/pipeline.yml`. Fetches, screens, scores every scenario, rebuilds the bundle
and deploys, once a day, with nobody in the loop. This page is the design: what the run costs,
where its state lives, how it fails, and what it keeps.

## Every fetch is inside Actions, and this is not a preference

CelesTrak firewalls by IP, and **Cloudflare Worker egress addresses are shared between
tenants**. A Worker's fetches can therefore start returning HTTP 522 on every source while the
same URLs answer instantly from anywhere else, because another tenant on the same egress address
earned the block. `docs/design-brief.md` records where this was read and how the project that hit
it worked around it. A Worker or a Pages deployment may **serve** the bundle. It must never
fetch. Nothing in this pipeline runs outside a GitHub-hosted runner except the upload at the end.

## The runtime budget

Timed on the development machine on 2026-09-03, over the demo fleet's six primaries against a
22,646-object catalogue for a seven-day window, at the settings the workflow uses. These are
**steady-state** figures: the first run also screens once with `--no-spacex` to seed the ephemeris
ranking, which costs about four minutes more, once.

The planning factor for a GitHub runner is **1.3 to 1.8 times** each number -- but only for the
steps that are arithmetic. The two fetches are not: they are bounded by somebody else's server and
by the network, and a runner is at least as good at those as this machine is. Multiplying them by
the CPU factor would invent half an hour of budget that does not exist.

| Step | Local | Bound by | On a runner |
| --- | ---: | --- | ---: |
| `fetch` + `weather`: CelesTrak groups, SATCAT, the Space-Track merge and the weather tables | ~1 min | download, cached at CelesTrak's two-hour floor | ~1 min |
| **`spacex latest`: 300 ephemerides** | **26 min** | **download**: 300 files of 2 MB, one request at a time, 5.2 s each. Parsing is 0.17 s a file, so this is entirely network | **~26 min** |
| `screen`, Stages A to C | 4.1 min | CPU: 20,161 samples x 22,646 objects, propagated **once** for all primaries | 5 to 7 min |
| `screen`, history backfill + covariance fit | 6.0 min | CPU over every Stage A survivor, not over the fleet | 8 to 11 min |
| `risk quiet` | 2 s | arithmetic over stored events | ~4 s |
| `ballistic` | **5.0 min** | CPU, and self-limiting: `BALLISTIC_FIT_BUDGET_S` is 240 s and what it does not reach falls back to B* | 6 to 9 min |
| **`risk` for a scenario, x4** | **16.7 min each, 67 min** | CPU: two density tracks per **object in an event**, from its own epoch to the window end | 88 to 122 min |
| `storm-check`, `propagate`, `report` | ~1 min | CPU | 1.5 to 2 min |
| `stability` | 3 s | one narrow file per run | ~5 s |
| `npm ci`, `npm run build`, `check-bundle` | ~1.5 min | node | ~2 min |
| deploy, archive upload, store push | ~1 min | upload | ~1 min |

**The total is about 1 h 53 m locally and 2 h 18 m to 3 h 0 m on a runner, against the six-hour
job limit** -- 38 to 50 % of it, with three to three and two-thirds hours spare. `timeout-minutes`
is set to 330, under the ceiling, so a hung step fails rather than being killed by GitHub.

**Where it goes, which is the number that matters for growth.** Of the local 113 minutes, **67 are
the four scenarios** and **26 are the ephemeris download**. Everything else together is 20
minutes. The two big terms grow in completely different ways, and neither grows with the fleet in
the way one would guess.

### At what fleet size it stops fitting

The scenarios are the binding constraint, and what they scale with is **not the number of
primaries** but the number of **distinct objects that appear in an event** -- two density tracks
each, per scenario. All four scenarios were timed on the 2026-09-03 run's 2,944 objects --
`storm-g4` 970 s, `forecast` 1,012 s, `storm-g5` 1,031 s -- against 990 s over 2,993 objects on
the 2026-09-01 run. That is a 6 % spread end to end: **0.34 s per object per scenario**, and no
scenario materially cheaper than another, which is the assumption the fan-out lever rests on.

Two measurements decide how that translates into fleet size:

- **The primaries barely share secondaries.** Summing each primary's distinct secondaries gives
  2,967 against 2,938 distinct overall -- an overlap factor of **1.01**. For a fleet of different
  orbits, objects-in-events is **linear** in fleet size.
- **A primary is not a unit.** The six range from **81** distinct secondaries (the ISS, at 400 km
  in a sparse shell) to **1,587** (EOS SAT-1, at ~500 km crossing the Starlink shells) -- a
  twentyfold spread, with a mean of 490. EOS SAT-1 alone is 4,222 of the run's 6,224 events.

So the ceiling is properly stated in objects, and only then in satellites:

| | |
| --- | --- |
| Fixed cost on a runner (fetches, screening, covariance, ballistic, export, deploy) | ~51 to 60 min |
| Left for scoring under the 6 h limit | ~5.0 to 5.2 h |
| At 0.34 s per object per scenario, four scenarios, x1.3 to x1.8 | **7,300 to 10,500 objects in events** |
| At this fleet's mean of 490 objects a primary | **15 to 21 primaries** |
| If every primary were EOS SAT-1-like (1,587 objects) | **5 or 6 primaries** |
| If every primary were ISS-like (81 objects) | **90 to 130 primaries** |

**The pipeline as written is good to about two and a half to three and a half times the demo
fleet, not to the tenfold the archive is designed for.** Those are two different limits and it is
worth keeping them apart: the *storage* survives a tenfold fleet, the *runtime* does not.

**And there is a second ceiling, which arrives first if the fleet is Starlink-facing.** The
ephemeris fetch is capped at `SPACEX_MAX_OBJECTS = 300` today, which is why it is a flat 26
minutes. A fleet ten times larger that wanted the same served-trajectory coverage would need ten
times the ephemerides: at the measured 5.2 s a file that is **4.3 hours of downloading**, which
breaks the six-hour job on its own, whatever the arithmetic costs. The cap is a runtime decision as
much as a politeness one, and it currently hides that.

### The levers, in the order they should be spent

1. **Fan the scenarios out into parallel jobs.** The six-hour limit is **per job**, and the
   scenarios are already independent by construction -- `driftwatch screen` writes `events.parquet`
   once and each `driftwatch risk <run> --scenario X` rescores those rows without touching SGP4.
   Four scenarios in four jobs turns 67 minutes of scoring into 17 and moves the fleet ceiling out
   by roughly a factor of four, to the region where the ephemeris fetch becomes the constraint
   instead. The cost is that the run directory has to be passed between jobs as an artifact and the
   risk files rejoined before the export. **This is the lever to reach for first**, and it is
   structural rather than numerical: nothing is approximated to buy it.
2. **The persistent ballistic-coefficient cache** (`data/ballistic/`, `drag/store.py`), already
   applied and already earning: this run fitted 534 objects, read **1,720 from the store** and left
   671 to the B* fallback when the 240 s budget ran out. That last number is the visible price of
   the bound -- those objects score `indicative` rather than `validated` in `storm_validity` -- and
   it is the reason the store lives on the branch where it cannot be evicted.
3. **`--storm-step-s` coarsening**, measured at 0.65 % on a history fit against a 5 % statistical
   uncertainty. Still not applied. It is the lever for a runner that turns out slower than the 1.8x
   figure, and it is cheaper in accuracy than dropping a scenario.
4. **Concurrency on the ephemeris fetch** is available and deliberately not taken: 300 serial
   requests with no delay between them is a choice about what is owed to `api.starlink.com`, and
   changing it is a politeness decision, not a performance one.

**Why the SpaceX fetch needs the previous day's run.** `driftwatch spacex` chooses which Starlink
secondaries to request by ranking a run's events by closest approach, so it needs a run before it
can choose. In steady state the pipeline uses **yesterday's run** for that ranking: the Starlink
objects that come near a fixed fleet do not change much in a day, and it saves a whole screening
pass. On the first run there is no yesterday, so the pipeline screens once with `--no-spacex` to
seed the ranking and then screens again for real.

**A step that was missing, found by timing them.** Every scenario but `quiet` refuses to run
without a ballistic coefficient per object, and the workflow never ran `driftwatch ballistic`. The
first scheduled run would have published a bundle and then failed at `risk --scenario forecast`,
every day. The step is now in, before `Score every scenario`; `docs/phase4-plan.md` has the note.

## Where the state lives, and why each piece lives there

The split is by **character**, not by convenience. Three homes, and the reason for three is that
these are three different kinds of thing.

| State | Size | Character | Home |
| --- | ---: | --- | --- |
| `data/supplemental/` | 0.74 MB a version | Accumulating and **irreplaceable**: CelesTrak serves one version and overwrites it. The whole value of the store is that it eventually spans days rather than hours. | Orphan branch `supplemental-store` |
| `data/ballistic/` | 396 KB | Accumulating, expensive to rebuild, self-invalidating. Lever 1 above. | Orphan branch `pipeline-store` |
| `data/snapshots/` | 3.8 MB a day | Accumulating and irreplaceable: the catalogue as it stood. Needed to rebuild any stored run. | Orphan branch `pipeline-store` |
| `data/weather/` | 1.2 MB | Small, accumulating, rebuildable from NOAA but cheap to keep. | Orphan branch `pipeline-store` |
| `data/stability/` | **0.33 MB a run** | Accumulating and derived, but derived from something that will not be re-read: the point of it is to answer a question about a year of runs without opening a year of runs. | Orphan branch `pipeline-store` |
| Run directories | **4.8 MB a run** | Accumulating and irreplaceable, and required in full by the retention rule below. | **GitHub release assets** |
| `data/cache/` | 1.5 GB | Ephemeral and rebuildable. It exists to honour CelesTrak's two-hour floor, so it only has to remember two hours. | Actions cache |
| `data/spacex/` | 39 MB | Ephemeral by construction: the files are valid for 72 hours and are refetched. | Actions cache |
| `data/history/` | 191 MB | Rebuildable from Space-Track, but slowly and under a rate limit. Losing it costs a backfill, not data. | Actions cache |

**Why an orphan branch and not the Actions cache, for the five above the line.** The Actions cache
evicts after seven days without a hit and has no durability guarantee. The supplemental store's
entire purpose is to accumulate for months; the ballistic store is the biggest lever on the run
time; the stability index is a series that a gap ruins. None can be allowed to evaporate. `docs/phase4-plan.md` has the isolation test that proved the
branch pattern, including the two ways it went wrong first.

**Why the branch cannot hold the run archive, which is the finding that decided it.** A run
directory is 4.8 MB and a snapshot is 3.8 MB, so retaining every daily run is **8.6 MB a day,
about 3.1 GB a year**. Git stores each of these already-compressed parquet files as a full blob
that deltas against nothing -- measured: three supplemental versions cost 2.19 MB of `.git` for
2.22 MB of files -- and deleting a file reclaims nothing from the history. Compaction bounds the
history to the tip, but the tip *is* 3.1 GB after a year, which is past what GitHub asks a
repository to stay under. **Release assets are not stored in git**: they do not count against the
repository, each may be up to 2 GB, and there is no limit on how many a release carries. One
release per month, one compressed run per day as an asset on it, is 145 MB a month in objects
that never touch a clone.

The alternative considered and not taken was **Cloudflare R2**, which would also work and which
the project already has an account for. It was not taken because it needs a bucket, a token
scope this project's Cloudflare token does not currently have, and a second place to look for
data -- against a release asset, which needs `gh release upload` and nothing else.

## Retention: every run, and why it cannot be decided later

**Every daily run is kept.** Not a rolling window. The reason is **warning stability**: how a
particular event's miss distance and probability evolve run by run as its time of closest
approach approaches, and how often a flag raised at a long lead survives to a short one. That is
the question an operator asks about a screening service before trusting it, it is the one thing a
daily pipeline can answer that no single run can, and **it is unrecoverable** -- a run that was
not kept cannot be reconstructed, because the catalogue it screened is gone from CelesTrak and
the supplemental sets it used were overwritten within hours.

`driftwatch report` can rebuild any archived run, which is what makes the archive worth keeping
rather than merely large: the run's `snapshot` and its `supplemental` versions are recorded in
`run.json`, `elements_for_run` reassembles exactly the element sets it screened, and
`driftwatch check-run` now refuses a run whose recorded provenance does not resolve.

### The index warning stability reads. Still no analysis.

`data/stability/<fleet>/<run_id>.parquet`, written by `driftwatch stability <run>` after the
deploy and before the archive, and read back with `driftwatch stability --pair A,B` or
`--series <id>`. `docs/data-schema.md` has the columns. What is deliberately still absent is the
**analysis**: survival rates, false-alarm rates, lead-time curves, a viewer panel. This is the
storage and the read path, and nothing is being concluded from a pipeline that has not yet run for
a week.

**The hard part is identity, and it decided the schema.** An `event_id` is
`<snapshot stamp>:<primary>:<secondary>:<tca to the minute>`, so **the same physical encounter has
a different id in every run** -- the snapshot stamp changes daily by construction, and the time of
closest approach itself moves as the orbits are refitted. Joining on `event_id` finds nothing. A
series is assembled instead on

- **the object pair**, `(primary_norad_id, secondary_norad_id)`, which is stable; and
- **the time of closest approach within a tolerance**, greedily, nearest first, one event to one
  series, because that is the only thing that distinguishes two encounters of the same pair.

The tolerance is ten minutes, and it is now measured rather than argued. Indexing two real runs
whose windows start 43 hours apart continued 1,756 series, and the matched time of closest
approach moved by a **median 0.3 s, 4.5 s at the 95th percentile and 20.8 s at most** -- thirty
times inside the tolerance, and a hundred times inside the ~46-minute half-orbit gap between
successive passes of one pair. Every row carries the `dt_tca_s` it was matched on, so the
tolerance stays checkable from the files instead of from the note that set it.

**Every event is indexed, not the flagged ones.** Over the same runs, flagged events have miss
distances from **0.53 km to 28.3 km** -- the whole screening volume, because the flag is decided by
the covariance and not by the miss. There is no miss-distance cut that admits the warnings, and an
event first indexed on the day it flags has no history to be read against, which is the failure
the index exists to prevent. What is cut instead is scenarios: `quiet` and `forecast`, the two that
are statements about the actual window. `storm-g3` and its siblings are what-ifs whose run-to-run
movement is a property of the scenario definition, and the run archive still answers for them.

**A disappearance is counted, not invented.** An encounter reported yesterday and absent today is
the signal, so the run's `stability` record carries `n_not_seen`; no row is written for it, because
the file is what that run saw.

**What it costs, and the point of the file.** 231 KB for one scenario over 6,224 events and
**330 KB for two** -- 27 bytes a row, the second scenario compressing against the first's identity
columns -- against 8.6 MB a day for the run and its snapshot. One
immutable file per run rather than one file rewritten daily -- git stores every version of a
rewritten file in full, so a monthly file rewritten each day would cost roughly fifteen times its
own size in history. A year of the index is about **120 MB**, which is read in one shallow clone of
the store branch; a year of the archives it replaces is 3.1 GB of downloads. At a tenfold fleet the
index is 3.3 MB a day and 1.2 GB a year -- which the runtime budget says the pipeline could not
reach anyway.

**Cost of the archive, stated so the retention decision is arguable.** 8.6 MB a day is 3.1 GB a
year at the demo fleet's size. A fleet ten times larger multiplies the run directory but not the
snapshot, so it is closer to 50 MB a day and 18 GB a year, which is past what release assets should
be asked to hold and is the point at which R2 or another object store becomes the answer rather
than the alternative. That threshold is worth writing down now: **the archive as designed is good
to about a tenfold growth in fleet size and no further** -- and note that this is *not* the
binding limit. The runtime budget above stops fitting a six-hour job at about two and a half to
three and a half times the demo fleet, so the runtime gives out first by a factor of three. The
two are worth keeping apart: they are fixed by different things and relieved by different levers.

## How it fails

The rule is that **a failure never publishes**. Every check is a step that exits non-zero, and a
failed step stops the job before the deploy step, so the previously deployed site stands
unchanged rather than being replaced by something built on bad input.

| Check | Where | What it catches |
| --- | --- | --- |
| Fetch failure | `driftwatch fetch` | CelesTrak or Space-Track unreachable. The job fails; nothing is published. |
| **Frame residual** | `driftwatch spacex` | The published states' frame changing at the source. It propagates the matching supplemental element set over the first three hours of every fetched ephemeris and compares **before writing anything**; hundreds of metres is the published fit residual, tens of kilometres is a frame error, and the threshold sits at 5 km, an order of magnitude clear of both. A failure refuses to write the store and exits non-zero. |
| **Provenance and snapshot age** | `driftwatch check-run --max-snapshot-age-hours` | A run whose recorded snapshot does not resolve, is not a snapshot, or is older than the limit. The age is read from the snapshot's own `fetched_at` column, not from its file name, so a rename cannot fake freshness. |
| **The export** | `driftwatch check-bundle --dir web/dist` | A redistributed SpaceX file, the literal value of any credential, or a file over Cloudflare Pages' 25 MiB limit. Runs over `dist/` rather than the source bundle, because `dist/` is what is uploaded. |

`concurrency: {group: pipeline, cancel-in-progress: false}` allows one run at a time and **never
cancels a run mid-deploy**, which is the case that would leave a half-uploaded bundle live.

**Three steps run after the deploy** -- the stability index, the archive upload and the store push
-- and all three are hard failures, which means a red run whose site is nonetheless fine. That is
the right way round: a failure there costs an unindexed and unarchived run, and neither can be
reconstructed later, so it must be loud. It cannot cost a bad publish, because publishing is
already done.
