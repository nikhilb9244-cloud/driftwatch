# Pipeline, retention and reproducibility

The daily GitHub Actions pipeline fetches a catalogue, screens the configured fleet, scores quiet
and the configured storm scenarios, builds a static bundle and publishes it through Vercel.
The schedule is 06:20 UTC; GitHub scheduling latency means the start time is not guaranteed.
The production alias is [driftwatch-coral.vercel.app](https://driftwatch-coral.vercel.app/).
Hosting is static: no fetch, screening or private analysis runs at the hosting edge.

## Failure rules

A failed fetch, scoring step, provenance check or bundle audit prevents publication. The prior
deployment remains available and its age remains relevant; success is not inferred from a cached
response. `check-run` rejects snapshots more than six hours old before deployment. It reads
`fetched_at` from the snapshot, not the filename. A missing recorded snapshot, a supplemental file
misrecorded as a snapshot, or absent scored output fails the check. A missing supplemental version
warns at publication and fails an exact replay. `check-bundle` rejects credentials, prohibited
data, retired synthetic demonstration identities and oversize files.

The GitHub job serialises pipeline runs and does not cancel a run during publication. A failure
after deployment but before archival can still leave a published result without a complete
archive. Archive retention and a successful deploy are separate facts.

## Recorded replay and the production gate

`REPRODUCED_RUN` in `.github/workflows/pipeline.yml` names `demo_20260905T000400Z`. An empty value
downgrades production to preview. The gate is retained: its evidence requires the same recorded
inputs to reproduce the runner's events on another machine.

The corrected replay mode uses `cli.elements_for_run` with strict supplemental-file checks:

```powershell
uv run driftwatch screen --offline --replay <archive-run-directory> --out-dir <new-output-directory>
uv run python scripts/compare_replay.py <archive-run-directory> <replayed-run-directory>
```

The snapshot and the exact supplemental parquet named in `run.json` must exist in the directories
under `DRIFTWATCH_DATA_DIR`. The fleet, radii and manoeuvre priors come from `objects.parquet`;
screening parameters and window come from `run.json`; quiet scoring uses `covariance.parquet`.
No current fleet file, response cache or history refit enters this path. The output directory
must be new and separate. Missing inputs or unsupported covariance layers fail explicitly.

The mode supports **quiet, element-set-only archives**. A run that used published operator
states is refused because those states are not retained in the public archive. Storm scenarios
also require their recorded forcing and ballistic inputs and are outside this replay mode.
Matching an element-set-only run does not establish reproducibility for an unretained served-state run.

**Correction:** earlier `screen --offline` replay attempts used the mutable CelesTrak response
cache. One such attempt produced 6,330 events instead of 5,766: only 4,120 supplemental sets
applied instead of 10,723. The corrected recorded-input replay reproduces 5,766 events and all
event flags. The quiet result has **16 robust-region flags** and **17 dilution-region flags out
of 33 (51.5%)**, with low confidence on every dilution flag. Robust does not certify accuracy.

The attached filter's differing counts arose from differing ISS element sets. Rounded copies
produced tiny relative oscillations and candidate minima; identical copies produced zero range
rate and no candidates. Both cases could exclude the same ten attached pairs. With identical
5 September inputs, both machines exclude ten pairs and drop 444 candidates. The discrepancy
does not require weakening or removing the filter.

## Storage and limits

| State | Storage and limit |
| --- | --- |
| Snapshots, history, supplemental versions, weather issues and ballistic coefficients | `pipeline-store` branch; accumulating inputs, subject to the documented retention policies. Supplemental thinning can remove a run's exact input and then strict replay fails. |
| CelesTrak/Space-Track response cache | Actions cache; ephemeral and evictable. Cache loss can cost a refetch and does not establish historical reproducibility. |
| Operator ephemeris covariance and state stores | Git-ignored Actions cache; analysis-only, never the public bundle or durable run archive. Expired state files are pruned after a week; summaries do not reconstruct their trajectories. |
| Completed runs | Monthly GitHub release assets, retained for warning-stability analysis; geometry, object table, covariance, per-scenario risk and provenance. These outputs alone do not contain all source data. |
| Warning-stability index | Small per-run files on the store branch, recording quiet and forecast series. Other scenario history still requires the archive. |

Git deletion does not reclaim old blobs. Store-branch compaction replaces history with its retained
tip; it cannot restore inputs already pruned. Release assets avoid adding every run to Git history,
but are not an unlimited-storage guarantee. Actions cache eviction, release access, provider
availability, repository quotas and credentials remain external dependencies.

The observed runtime and storage measurements concern the six-object demo fleet; they do not
establish a tenfold-fleet throughput guarantee. The explicit history-fit time budget does not
bound network backfill, screening, all diagnostic propagation, archive uploads or total job time.
The 48-hour browser window is separate from the seven-day screening window. A successful pipeline
does not validate the probabilities or establish operational warning completeness.

_Last updated 7 September 2026._
