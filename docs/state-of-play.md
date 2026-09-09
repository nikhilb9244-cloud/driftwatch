# State of play — 9 September 2026

The current plan is to maintain driftwatch as an open-source research reference and bounded
comparison tool, preserve its published correction history and existing scheduled work, and
prioritise a real external orbit-data or adapter acceptance case through Throughflow Systems.
The [roadmap](../ROADMAP.md) is the governing plan. Weather is closed as an exploratory diagnostic;
the general scientific-data platform and other speculative lanes are parked.

## Review base and retained evidence

The review base is development revision `3e5a64c0fd3f772e622fd4fb402bc1b176a5e125`, verified
against the live `origin/main` tip on 9 September 2026. It is also the evidence revision for the
published v2.1 correction and four completed maintenance items. Their implementation and evidence
are present in this worktree; the completion scopes below use those records and the retained
9 September NOAA reports. No post-audit workflow-health check or scientific rerun was performed.

Earlier roadmaps remain in Git at their original revisions. Existing archives, the private
development log and correction history remain unchanged in this review. The diff changes only
this state-of-play document and the roadmap.

## Recorded outcomes and remaining limits

| Area | Completion evidence | Limit or next action |
| --- | --- | --- |
| v2.1 completeness/provenance correction | Complete and published at [10.5281/zenodo.22665947](https://doi.org/10.5281/zenodo.22665947). Retained deposit verification confirms the v2 correction link. The invariant comparison has zero differences across 52 tables and 107 scalar substitutions; the authorised paper-body comparison also passed. [P1, P2] | Preserve the original and corrected evidence hashes in the dated correction record. No v2 result was rescored and no new evidence regeneration is authorised. |
| Public-tag reproduction | Fresh clone and new environment at `paper-2026-09-v2.1`: 730 passed, 5 skipped; all 10 publication contracts passed. [P2] | Publication reproduction has a defined scope; it is not every upstream calculation rerun or customer acceptance. |
| G1 availability maintenance | Complete for tested provenance selection and persistence; 17 G1 checks passed within the later local 786-test suite, with no failures or skips. [G1] | Separate state/event, creation, publication and retrieval times; reject known late publication before selecting revisions. Unknowns remain unknown. Neither missing historical publication/membership evidence nor discarded revisions were recovered; historical benchmark claims remain epoch-based reconstructions. |
| Scheduled collection and watchdog | Audited through 8 September, 20:15:45 UTC. Duplicate SpaceX epochs caused the 5 September daily failure; retained evidence identifies repair `8c216fb` and successful scheduled daily runs on 6–8 September. A 36-hour freshness watchdog is installed. [S1] | Daily scheduling delays and ten supplemental intervals without a start remain recorded; delayed versus dropped triggers are unresolved. No 36-hour gap was present at that cutoff. Subsequent execution success, cadence and input completeness require separate actual evidence. |
| Monthly reference comparison | Installed with the frozen v2 method at `fedc1bc7f398edf6bbff4b8c066f95c8f2865cd9`; first scheduled observational run due 12 September 2026, 04:43 UTC. [M1] | No completed monthly scientific result yet. Inspect the due run, protocol, month selection, available inputs and outputs. Keep failed/unassessable results visible. |
| Public case bundle | The public criterion reproduced on a fresh Linux runner using only the bundle's source, dependency lock and inputs. [A1] | Automated second-machine reproduction is not an independent person's acceptance or an independent physical reference. No customer adapter was accepted. |
| Internal migration matrix | Three passed, one failed and two untested axes. [A1] | Failed: invented optional-field defaults and covariance loss in history without refusal. Untested: complete object identity through browser display/export, and full browser/save/open/export round trips. Passing CLI checks do not resolve them; the [roadmap matrix](../ROADMAP.md#one-bounded-orbit-data-or-adapter-review) retains each axis. |
| External case and funding | No reviewed completion record establishes a customer acceptance decision or funded next step. | Continue the existing private technical threads; establish a real decision, permitted case, responsible owner and acceptance criterion. Record funding separately from technical interest. |

The installed monthly protocol checks completed UTC months in reverse order from the immediately
preceding month and selects the newest with qualifying reconstructed-orbit coverage for at least
one v2 mission, within a twelve-month search bound. It records the candidate protocol before
availability checks and the eligible population before scoring. Failed provider requests remain
unknown availability; residuals cannot justify dropping missions or substituting months. This
existing rule is more specific than the proposal's warning against changing months: preserve the
rule, and do not choose a month ad hoc or run the job early. [M1]

## NOAA closure and preserved chronology

The original run, interpretation addendum and revised exploratory run are retained separately,
without copying their data or generated evidence into tracked publication assets. [N1, N2, N3]
Both runs concern six files, KATL/KDEN/KSEA, routine FM15 observations in
`[2024-01-01T00:00:00Z, 2024-01-08T00:00:00Z)`, temperature, dew point and the observation-weighted
mean of their difference. The selected interval has 798 ISD and 774 GHCNh raw records.

The original frozen gates left native eligible ISD/GHCNh counts of 0/0 at KATL, 0/0 at KDEN and
8/0 at KSEA, with no common eligible pairs: all primary comparisons remain **unassessable**.
The blank-only GHCNh quality interpretation excluded documented-good flags; the ISD gate also
excluded merged provenance. The identical values in 774 secondary pairs per variable do not turn
the empty primary comparison into a zero-difference result.

The revised source-aware quality and supplied-record merge rules produce 168 eligible records
per source and 168 common pairs at each station, 504 common pairs in total, with no eligible
unmatched or ambiguous records. Selected values and native/common means agree exactly; the native
mean difference, value component, population component and closure are zero at every station.
Independent raw-record processing exercised the nonmissing calculations and reconstructed the
common population; 17 deterministic files replayed byte for byte. This design followed inspection
and remains **exploratory**, not an untouched validation or replacement for the original result.

The 496 eligible merged ISD records still have unresolved field origins; whether integrated GHCNh
checks ran or passed remains unestablished. Different native populations, nonzero migration
components and absent ambiguity conditions were not validated. The 24 ISD-only secondary summary
records have missing selected fields; the precise upstream reason for their omission remains open.
Enforced network restriction was application-only; operating-system isolation was not established.
There is no general equivalence, measurement-accuracy, data-defect or customer-demand claim.

The selected question is closed. No further weather experiments, sample expansion, adapters,
product, service or scheduled ingestion are active. Reopening requires an identified external
workflow and separately approved scope. The [roadmap](../ROADMAP.md#weather-investigation-closed)
carries the station populations and limits.

## Next decisions and effort limit

Maintain the published reference, supported reproduction paths and existing jobs. Inspect the
monthly benchmark after its 12 September run is due; installation or a green job alone cannot
establish a usable result. Do not add a monitoring system or a new scientific recipe.

Prioritise existing external technical conversations and one independent person reopening an
existing suitable case. Honour the initial no-cost commitment for one bounded existing-workflow
comparison after permissions, scope and criteria are agreed; it promises no free custom
development. A new paid implementation needs an approved scope, acceptance criterion and funded
next step. Keep correspondence, customer inputs and case permissions private.

The early-October continuation gate remains **a real case and a funded next step**. **5 October
2026 is proposed for adoption**, with no retained evidence of prior agreement to that exact date.
At the gate, continue only agreed funded work; otherwise pause speculative commercial development
and keep reference maintenance within a deliberate effort limit. Honour any already agreed free
case without expanding it. Technical usefulness, a free case, a maintainer contribution and
independent reproduction remain distinct from funding. Do not extend the gate because of internal
progress or silently disable existing jobs.

G2, G7, the Johlander/WAM-IPE lane, new covariance/manoeuvre/ballistic-coefficient/differential-drag/
learned-propagator recipes, radio product work and general scientific-data/AI platform development
remain parked. Radio research still needs a partner, suitable evidence and permitted beam use.
No implementation or additional outreach is authorised by this reconciliation.

## Evidence used for this reconciliation

Repository paths in this table refer to files present at the review base
`3e5a64c0fd3f772e622fd4fb402bc1b176a5e125`. Locally retained execution reports remain outside
the review worktree. Their names and hashes identify the evidence without implying a public
download link; private correspondence and retained evidence packages are not included.

| ID | Retained evidence |
| --- | --- |
| P1 | `docs/publication-rebuild.md`, `docs/assets/publication-correction-v2.1.json` and `docs/assets/publication-invariant-check-v2.1.json`. The correction preserves old evidence SHA-256 `f19c24451e65d8e0baf6b803f379380aab72146e5ef73687b818397bcb5609e5` and corrected SHA-256 `76c463a7a6e9728425f846aea7cc1fc44cbf0b316be9fdf4726a148505b7ba48`; the claims manifest binds the corrected object. |
| P2 | Retained 8 September `clean-clone-public-run.json` (SHA-256 `9ba15b1e3ccaecd48d53f690aa844806e7aad41fbfa41f24b967637a2f26ce2b`), its public-tag `full-suite.xml` (SHA-256 `3fa8319659f79456c428e0ba9279f7265afcbbbe543d2f56a952b3b5d9e43306`) and `published-verification.json` (SHA-256 `3b6340c435ffa3d5386992082d5823006ca39aef19f10988c93225dd4cab33dd`). The first two record 735 completed tests including 5 skips; the third records the DOI and v2 correction notice. |
| G1 | `docs/g1-availability.md`, `tests/test_availability.py` and retained 8 September `g1-pytest.xml` (SHA-256 `dac96534d833a98270a6f733060a95051dd7413e013359fc45f8d0ae4b84e4b7`): 786 completed, no failures/errors/skips, including 17 G1 cases and 10 publication contracts. |
| S1 | `docs/maintenance-2026-09-08.md`, `docs/assets/maintenance-2026-09-08.json` and `.github/workflows/workflow-health.yml`; scope ends at the recorded audit cutoff. |
| M1 | `docs/monthly-reference.md`, `.github/workflows/monthly-reference.yml`, `scripts/monthly_reference.py` and `docs/assets/claims-versions.json`; protocol-first installed rule, frozen scientific revision and separate append-only monthly results. |
| A1 | `docs/case-bundles.md`, `docs/migration-audit-2026-09-08.md`, `docs/assets/cases/migration-audit-2026-09-08.json` and `docs/assets/cases/second-machine-2026-09-08.json`. |
| N1 | Original NOAA ISD–GHCNh bounded diagnostic `findings.md`, completed 9 September (SHA-256 `ebd02218f91815daaac032e37ae8aeaa69ad6a2625a08113b8cc030d98bd9f77`); original primary result unassessable. |
| N2 | `noaa-migration-2026-09-09-interpretation-addendum.md` (SHA-256 `e4b6d3b3ce13ec697810cf6709831043abc239e80102fc2ed986a3c50d582e33`); dated proposed source-specific eligibility correction, retained separately from both runs. |
| N3 | Revised NOAA exploratory diagnostic `findings.md`, completed 9 September (SHA-256 `c8b444c26120be6e06cc156429fa2b54e9cca03a7c58702a518a11effcbeac1f`); revised populations, exact zero differences, independent checks, replay and network limitations. |

## Recorded limits and unresolved facts

The retained successful daily runs on 6–8 September establish recovery after the 5 September
failure; later health and data completeness are unchecked. Supplemental delayed versus dropped
triggers remain unresolved. The monthly job's predeclared reverse-month availability search
remains controlling.

Sending status and permissions remain in the existing private correspondence record; unverified
status stays unknown. The exact 5 October date remains proposed, and neither an accepted customer
case nor funding is inferred.
