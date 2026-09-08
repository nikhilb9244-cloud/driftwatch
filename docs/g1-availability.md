# G1 availability contract — 2026-09-08

The late-publication acceptance gate passes for supplied element-set, catalogue-membership
and manoeuvre provenance. This maintenance changes input selection and metadata; the
published v2 evidence, tables and paper figures remain frozen.

| Field | Meaning | Unknown handling |
| --- | --- | --- |
| `state_epoch` / `epoch` | Instant represented by an element set or state | Never used as publication time |
| `effective_at`, `start` / `end` | Membership or manoeuvre event time | Kept separate from the record's availability |
| `provider_created_at` | Provider's product creation time | Null if absent; never substitutes for publication |
| `published_at` | Known publication time for the specific product or record | Null when unestablished |
| `retrieved_at` | Actual acquisition from the provider | Null when unrecorded; cache import does not refresh it |
| `reconstructed_at`, `imported_at`, `reviewed_at` | Local processing times | Never used to establish earlier availability |

`fetched_at` remains a compatibility alias for actual retrieval. Schema-1 epoch snapshots
that put the historical target in this field are read with unknown retrieval; the target is
retained only as `epoch_selection_as_of`. Schema-2 snapshots keep their recorded retrieval
times. Schema 3 also stores the causal cutoff and selected membership provenance.

An **epoch-based reconstruction** selects on state or event time and says that availability
is not established. A **causal replay** requires known publication at or before its decision
time. When publication is unknown, an actual retrieval by that time is sufficient evidence
of availability. A known late publication always excludes the record. Creation, file mtime,
local import and the reconstruction target do not fill missing availability.

Selection applies before choosing among revisions with the same state epoch. New history
imports preserve those revisions and their cache retrieval times; older discarded revisions
cannot be recovered. Catalogue replay additionally requires explicit membership events,
with `norad_id`, `effective_at`, boolean `present`, the three availability fields and supplied
source identifiers/hashes. Current SATCAT and group labels are not historical evidence.

Use `driftwatch snapshot-as-of --selection causal --date <UTC instant> --ids <ids>
--membership-history <provenance.json>` with the provenance format written by
`driftwatch.availability.write_records(..., epoch_column="effective_at")`. Existing causal
output is not silently reused for different evidence; reopen its Parquet file or explicitly
rebuild with `--force`. The default remains an epoch reconstruction. Local fixed-object
comparison options and their narrower scope are documented in [local analysis](local-analysis.md).

The [acceptance suite](../tests/test_availability.py) checks:

- A late revision is included only by epoch reconstruction; replay keeps the earlier eligible
  revision, and reopening preserves all time fields and membership source provenance.
- A late membership addition or removal changes the epoch reconstruction, while the causal
  membership is the last state supported by evidence at the decision time.
- A manoeuvre before the decision but published later is excluded from causal record selection;
  event times, source hash and unknown retrieval survive reopening.
- Creation does not replace unknown publication/retrieval, including an exact cutoff and
  conflicting known late publication. Missing membership fails explicitly.
- Cache reads and both fetch/history commands retain original retrieval times; local uploads
  and source-review summaries do not invent them.

These are acceptance checks of selection and persistence, not proof that a supplied timestamp
is authentic, that an external catalogue is complete, or that an orbit is accurate. The existing
reference residuals and derived manoeuvre diagnostics remain retrospective. No weather
forecast availability, candidate rediscovery, short-window dynamics or new recipe is added.

Validation on 8 September completed all 786 collected tests with no failures or skips,
including the 17 G1 cases and all 10 publication contracts. The independent completion
guard passed. The publication invariant check reported zero differences across 52 tables,
107 scalar substitutions and the paper body outside its authorised availability correction.
