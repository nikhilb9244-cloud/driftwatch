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

Measured on the development machine on 2026-09-03, over the demo fleet's six primaries against a
22,646-object catalogue for a seven-day window. GitHub's runners are slower than this machine on
single-threaded NumPy, so the right planning figure is 1.3 to 1.8 times each number.

| Step | Cost | What sets it |
| --- | ---: | --- |
| CelesTrak groups + SATCAT + Space-Track merge | ~1 min | download, cached at CelesTrak's two-hour floor |
| SpaceX ephemerides, 300 objects | **26 min** | download, 2 MB a file; parsing is 0.17 s a file |
| Screening, Stages A to C | 4 min | Stage B: 20,161 samples x 22,646 objects |
| History backfill + covariance fit | 6 to 7 min | Space-Track `gp_history`, then the consistency fit |
| `risk` for `quiet` | ~6 s | arithmetic over stored events |
| `risk` for a storm scenario | **~16 min each** | two density tracks per object, from its own epoch to the window end |
| `storm-check`, `report`, viewer export | ~1 min | |
| `npm run build`, `check-bundle`, deploy | ~1.5 min | |

Four scenarios beyond `quiet` (`forecast`, `storm-g3`, `storm-g4`, `storm-g5`) is **64 minutes of
scoring**, and the total is about 105 minutes on this machine, so **two and a half to three hours
on a runner**. Against the six-hour job limit that fits with room; against the courtesy owed to
CelesTrak and Space-Track it is one polite pass a day over each.

**The three levers, spent in this order.** The prompt's instruction was to measure before
optimising, so these are recorded with what they are worth and only the first is applied yet.

1. **The persistent ballistic-coefficient cache** (`data/ballistic/`, `drag/store.py`). A
   coefficient costs about a hundred NRLMSIS evaluations and is the same answer next week; the
   store is keyed by NORAD id **and by the span of history it used**, and refits only when the
   history has grown by more than a week, the fit is older than its limit, or the NRLMSIS version
   or acceptance rules changed. It is **396 KB** and it is the single biggest lever on the storm
   scenarios, so it is the one piece of state that must never be lost. Applied: it lives on the
   store branch, not in a cache that can be evicted.
2. **`--storm-step-s` coarsening**, whose cost was measured at 0.65 % on a history fit against a
   5 % statistical uncertainty. Not applied yet. It is the lever to reach for if the runner turns
   out slower than the 1.8x planning figure.
3. **Geometry once, scoring per scenario.** Already true and worth stating because it is why the
   budget is 4 minutes of screening and not 4 per scenario: `driftwatch screen` writes
   `events.parquet` once, and each `driftwatch risk <run> --scenario X` rescores those rows
   without touching SGP4. Every event carries both objects' TEME states at closest approach
   precisely so that this is possible.

**Why the SpaceX fetch needs the previous day's run.** `driftwatch spacex` chooses which Starlink
secondaries to request by ranking a run's events by closest approach, so it needs a run before it
can choose. In steady state the pipeline uses **yesterday's run** for that ranking: the Starlink
objects that come near a fixed fleet do not change much in a day, and it saves a whole screening
pass. On the first run there is no yesterday, so the pipeline screens once with `--no-spacex` to
seed the ranking and then screens again for real. That first run therefore costs about four
minutes more than every run after it.

## Where the state lives, and why each piece lives there

The split is by **character**, not by convenience. Three homes, and the reason for three is that
these are three different kinds of thing.

| State | Size | Character | Home |
| --- | ---: | --- | --- |
| `data/supplemental/` | 0.74 MB a version | Accumulating and **irreplaceable**: CelesTrak serves one version and overwrites it. The whole value of the store is that it eventually spans days rather than hours. | Orphan branch `supplemental-store` |
| `data/ballistic/` | 396 KB | Accumulating, expensive to rebuild, self-invalidating. Lever 1 above. | Orphan branch `pipeline-store` |
| `data/snapshots/` | 3.8 MB a day | Accumulating and irreplaceable: the catalogue as it stood. Needed to rebuild any stored run. | Orphan branch `pipeline-store` |
| `data/weather/` | 1.2 MB | Small, accumulating, rebuildable from NOAA but cheap to keep. | Orphan branch `pipeline-store` |
| Run directories | **4.8 MB a run** | Accumulating and irreplaceable, and required in full by the retention rule below. | **GitHub release assets** |
| `data/cache/` | 1.5 GB | Ephemeral and rebuildable. It exists to honour CelesTrak's two-hour floor, so it only has to remember two hours. | Actions cache |
| `data/spacex/` | 39 MB | Ephemeral by construction: the files are valid for 72 hours and are refetched. | Actions cache |
| `data/history/` | 191 MB | Rebuildable from Space-Track, but slowly and under a rate limit. Losing it costs a backfill, not data. | Actions cache |

**Why an orphan branch and not the Actions cache, for the first four.** The Actions cache evicts
after seven days without a hit and has no durability guarantee. The supplemental store's entire
purpose is to accumulate for months; the ballistic store is the biggest lever on the run time.
Neither can be allowed to evaporate. `docs/phase4-plan.md` has the isolation test that proved the
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

### The schema warning stability will need. No analysis is built.

Reported now because the storage decision cannot be made retrospectively, and deliberately not
implemented: there is no command for it, no viewer panel and no table.

**The hard part is identity across runs.** An `event_id` is
`<snapshot stamp>:<primary>:<secondary>:<tca to the minute>`, so **the same physical encounter has
a different id in every run** -- the snapshot stamp changes daily by construction, and the time of
closest approach itself moves by seconds to minutes as the orbits are refitted. Joining on
`event_id` would find nothing. The series has to be assembled on:

- **the object pair**, `(primary_norad_id, secondary_norad_id)`, which is stable; and
- **the time of closest approach within a tolerance**, because that is the only thing that
  distinguishes two encounters of the same pair. Successive passes of a pair are typically half
  an orbit apart -- about 46 minutes in low Earth orbit -- while a TCA moves by far less than that
  between runs, so a tolerance of a few minutes separates them cleanly. The Step 1 comparison
  used a greedy nearest-time match inside ten minutes and it is the same problem; the one place
  it is delicate is a pair with repeated close passes in a short span, which is exactly the
  near-co-orbital geometry the attached-object filter also had to reason about.

A future analysis therefore needs, **per run and per event**: `run_id`, the run's `start` (which
gives the lead time as `tca - start`), the snapshot's `fetched_at`, the pair, `tca`, `miss_km`,
`pc`, `pc_max`, `flag`, `storm_validity`, `cov_source_primary`, `cov_source_secondary`,
`primary_trajectory` and `secondary_trajectory`. Every one of those is already written by the
existing `risk_<scenario>.parquet` and `events.parquet`, so **no schema change is needed** -- the
analysis is a join over what the archive already holds. What it must not have to do is open all
365 run directories to find the series for one pair, so a later phase should write a per-run
**stability slice**: one narrow parquet of exactly the columns above, a few hundred kilobytes
rather than 4.8 MB, appended to a single index. That file does not exist yet and is not being
created; recording its columns is the deliverable.

**Cost, stated so the retention decision is arguable.** 8.6 MB a day is 3.1 GB a year at the demo
fleet's size. A fleet ten times larger multiplies the run directory but not the snapshot, so it is
closer to 50 MB a day and 18 GB a year, which is past what release assets should be asked to hold
and is the point at which R2 or another object store becomes the answer rather than the
alternative. That threshold is worth writing down now: **the archive as designed is good to about
a tenfold growth in fleet size and no further.**

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
