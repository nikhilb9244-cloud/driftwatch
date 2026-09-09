# driftwatch working roadmap — 9 September 2026

Keep driftwatch open source as a maintained research reference and a bounded comparison tool.
Maintain the published record and existing scheduled work. Throughflow Systems has one active
service hypothesis: a bounded orbit-data or adapter acceptance review for a real engineering
decision. The next milestone is an external person using the existing work and challenging its
interpretation. Feature counts, test totals and another internally selected dataset do not meet it.

This review carries the settled documentation reconciliation onto development revision
`3e5a64c0fd3f772e622fd4fb402bc1b176a5e125`. The
[maintenance record and current evidence references](docs/state-of-play.md) establish the
completion scopes below. Earlier roadmaps remain in Git; published results, existing archives
and correction history remain unchanged.

## Completed work and maintained operations

| Area | Recorded status | Scope and next action |
| --- | --- | --- |
| Publication v2.1 | Complete; published at [10.5281/zenodo.22665947](https://doi.org/10.5281/zenodo.22665947). The retained deposit verification confirms the v2 notice links to the correction. | The completeness/provenance correction changes no v2 result. The retained comparison reports zero differences across 52 tables, 107 scalar substitutions and the paper body outside the authorised availability addition/hash correction. Preserve both evidence hashes in the existing correction record. [P1] |
| Public-tag reproduction | Fresh-clone reproduction at `paper-2026-09-v2.1`: 730 passed, 5 skipped, including all 10 publication contracts. | This verifies the recorded publication-reproduction contract, not a rerun of every upstream scientific calculation. Keep it separate from later local tests. [P2] |
| G1 implementation | Complete for tested selection and persistence: 17 G1 checks passed; the later local suite completed 786 tests with no failures or skips. | Late publication is excluded before causal revision selection; state/event, creation, publication and retrieval times and unknowns survive reopening. Supplied provenance is not authenticated by these checks. Missing historical publication/membership records and discarded revisions remain missing; the historical benchmark remains an epoch-based reconstruction. [G1] |
| Daily/supplemental collection and watchdog | Installed and audited through 8 September, 20:15:45 UTC. The 5 September daily failure was repaired; scheduled daily runs on 6–8 September succeeded. The watchdog uses a 36-hour freshness threshold. | Preserve this verified recovery. Daily delays and ten supplemental intervals without a recorded start remain documented; delayed versus dropped triggers are unresolved. Later success, cadence and data completeness need actual run evidence, separately, on a requested operations check. [S1] |
| Monthly reference comparison | Protocol-first job installed; first scheduled observational run due 12 September 2026 at 04:43 UTC. No monthly scientific result is recorded yet. | Inspect the actual run and outputs after it is due. Preserve the frozen v2 method and installed rule selecting the newest qualifying completed month before residual inspection. Job success alone is not a usable benchmark. [M1] |
| Public case bundle | The existing public case reproduced its decision on a fresh Linux runner from the bundle's source and lock. | This is automated second-machine reproduction. An independent person reopening a suitable case and customer acceptance remain separate, unmet conditions. [A1] |

Evidence identifiers above and below resolve in the [state-of-play evidence register](docs/state-of-play.md#evidence-used-for-this-reconciliation).
No experiment, workflow dispatch, schedule change or evidence regeneration is part of this reconciliation.

## One bounded orbit-data or adapter review

The offer is a reopenable acceptance record for the behaviour an engineering team agrees it needs.
Agree the technical owner, decision, permitted inputs and use, baseline, exact customer adapter
stages, time/frame/unit conventions, required information preservation, comparison epochs,
exclusions and scientific tolerance. Record replay tolerance separately. Establish whether the
inputs represent the same underlying orbit solution before attributing differences to migration.

The existing internal profile compares one element set per input, matching catalogue and
international identifiers, Earth-centred TEME, UTC, km and km/s, SGP4, WGS72 and improved operation
mode. Its public TLE and OMM inputs encode the same stored mean elements; neither is an independent
physical reference. Comparing them through driftwatch does not accept an unexercised customer path.
An independent second person must be able to reopen an agreed case and reproduce its decision.

The retained migration matrix has **three passed, one failed and two untested axes**. [A1]

| Compatibility axis | Internal audit status | Limit that remains visible |
| --- | --- | --- |
| Object identity | Untested as a complete axis | Import, history and inspection-API checks passed for the public case and declared identifier variants; browser identity display and export joins were not exercised. |
| Time and availability | Passed for recorded checks | State epoch and creation are distinct; supplied retrieval and unknown availability survive storage. G1 adds tested causal selection, without creating historical provenance. |
| Frame, centre and units | Passed for recorded checks | The exercised unsupported declarations are refused. Other conventions do not acquire support by implication. |
| Mean-element theory | Passed for recorded checks | The same stored mean elements agree through the declared SGP4 paths within the public criterion; this does not establish orbit accuracy. |
| Optional and missing data | Failed | Missing fields acquire invented defaults; decoded covariance metadata and matrix are lost in history without explicit refusal. Covariance preservation was not accepted. |
| Full adapter path | Untested | CLI reopening passed; full browser, save/open and export round trips were not exercised. |

Every customer adapter remains unverified until its actual agreed path is exercised. Before an
affected case, refuse an unsupported path, explicitly narrow the scope, or separately agree a
necessary bounded fix. Do not repair failed axes just to make the offer appear complete.

Honour the initial comparison already offered at no cost: one suitable bounded case using existing
capabilities, after permissions, scope and acceptance criteria are agreed. It includes no custom
development or ongoing free work. New paid work needs a separately agreed scope, acceptance
criterion and funded next step. No price, delivery promise, buyer or authorised budget is assumed.
AI may assist investigation and coding; the useful outcome is a better-supported customer decision.

## Weather investigation closed

The NOAA ISD–GHCNh investigation is complete as a bounded exploratory diagnostic. Preserve the
original unassessable run, the dated interpretation addendum and the revised zero-difference run
as three separate records. The revised design followed inspection; it is not an untouched
validation and does not replace the original outcome. [N1, N2, N3]

Both runs used the same six retained files, KATL, KDEN and KSEA, the half-open UTC interval
`[2024-01-01T00:00:00Z, 2024-01-08T00:00:00Z)`, routine FM15 records, air temperature and dew-point
temperature. The endpoint is the observation-weighted mean of `D = temperature − dew point`.
The selected interval contains 798 ISD and 774 GHCNh raw records.

| Station | Original native eligible, ISD / GHCNh | Original common pairs | Revised native eligible, ISD / GHCNh | Revised common pairs |
| --- | ---: | ---: | ---: | ---: |
| KATL | 0 / 0 | 0 | 168 / 168 | 168 |
| KDEN | 0 / 0 | 0 | 168 / 168 | 168 |
| KSEA | 8 / 0 | 0 | 168 / 168 | 168 |
| Total | 8 / 0 | 0 | 504 / 504 | 504 |

The original frozen interpretation excluded documented-good nonblank GHCNh quality flags and
merged ISD provenance. Its primary comparison is unassessable at every station. Its 774 secondary
pairs per variable have identical decoded values, but include excluded records and do not establish
an eligible combined common set. The empty primary result is not a measured zero difference.

The revised rules admit source-defined good GHCNh quality labels and documented ISD merges for a
supplied-record calculation. At every station all selected common-set values, native/common means,
native mean difference, value component, population component and algebraic closure agree exactly,
with all differences/components zero. There are no eligible unmatched or ambiguous records.
Independent raw-record processing reconstructed the 504 common pairs and exercised nonmissing
calculations; fresh-directory replay reproduced 17 deterministic files byte for byte. [N3]

These results apply only to these files and rules. The 496 eligible merged ISD records retain
unresolved field origins and false provenance coherence, separately from calculation eligibility.
Whether integrated GHCNh checks ran or passed remains unknown. Different native populations,
nonzero components and absent ambiguity conditions were not validated by this sample. Both runs'
secondary tables retain 24 ISD-only summary records with missing selected fields; their precise
upstream omission from GHCNh remains unresolved. No general collection equivalence, measurement
accuracy, NOAA data defect, customer demand or unmet practitioner need was established.

Network enforcement was application-level only; the attempted Sandbox execution did not establish
operating-system isolation. Preserve that limitation. Retain the detailed packages locally; do not
bulk-copy data, scripts or generated evidence into publication assets. No further weather stations,
periods, variables, adapters, models, service or scheduled ingestion are active. A specific external
workflow and separately approved scope would be needed to reopen weather. A public methods note
is optional only if it serves an identified conversation and receives separate review; no weather
product, new paper, DOI or website is planned.

## Work through early October

Use the existing private correspondence and its latest confirmed sending status. Do not restart
introductions or count a draft as sent. The private record preserves the initial no-cost commitment,
existing technical threads and any unresolved sending evidence; contact identities and correspondence
are not copied into this public plan. Keep research feasibility and observation-data access requests
distinct from a paid review. A recent unanswered message does not establish lack of demand.

Seek one external technical owner, real decision and permitted case, and one independent reader
who can reopen suitable existing material. A demo build is not a prerequisite. Record the problem,
current method, unresolved consequence, case permissions, owner, acceptance criterion, budget owner
and next agreed action privately; keep unknowns unknown. There is no mass outreach campaign.

| Period | Bounded planning action | Evidence of progress |
| --- | --- | --- |
| 9–11 September | Reconcile planning, close weather and preserve its records; carry forward the existing correspondence state. | Consistent roadmap and state of play; no new research task. |
| 9–18 September | Continue already selected external approaches only where appropriate and separately reviewed. | An actual technical discussion, case-reopening response or accurate record of no reply. This edit sends or prepares no message. |
| From 12 September, after the scheduled run is due | Inspect the existing monthly run, predeclared month selection, inputs and scientific outputs. | A usable result or explicit failed/unassessable status. Preserve the protocol; do not dispatch early or choose a month after seeing residuals. |
| 19 September–2 October | Agree a real case if one emerges; use the existing-workflow free case or separately funded scope. | Named decision and owner, actual inputs or agreed access, acceptance criterion, and funding recorded separately. |
| Early October; 5 October 2026 proposed for adoption | Apply the external continuation gate. | Written decision based on a real case and a funded next step, not an expanded feature backlog. |

The early-October gate remains in force. **Monday 5 October 2026 is a proposed review date**, not
an earlier agreement or a newly scheduled job. The dates above are work checkpoints, not forecasts
of replies, and a useful response can be handled when it arrives.

A funded next step means an agreed bounded engagement with an identified payer and authorised
budget or equivalent concrete funding commitment. General interest, an independent reproduction,
a free pilot or a maintainer contribution does not by itself meet the commercial gate.

| Position at the gate | Effort decision |
| --- | --- |
| Real case and funded next step | Continue only the agreed review or implementation; preserve the public reference and scope. |
| Technical usefulness without funding | Record usefulness separately, pause speculative commercial development and maintain the reference within a deliberate effort limit. Use the work in employment, subcontracting or explicitly supported research discussions. |
| Agreed free case underway without funded continuation | Honour its bounded existing-workflow scope; do not expand it or count the commercial gate as met. |
| No external case | Stop discretionary product/research expansion and direct effort to externally defined paid opportunities. Preserve published artefacts and corrections; review unattended-job costs separately without silently disabling services. |

Do not extend this gate because internal work was completed. Later external evidence can justify
a newly bounded decision, recorded as such.

## Permitted maintenance and parked work

Development can address a demonstrated failure of existing supported behaviour or reproduction,
one small contribution whose use and scope a maintainer or engineer confirms, or an agreed customer
case. Name the failure/decision and smallest correction. A positive reply alone does not authorise
implementation. Any new commercial implementation requires an approved bounded scope, acceptance
criterion and funded next step. Keep supplied customer material private unless its owner approves
sharing. Existing public work stays available under its current terms; no licensing redesign begins.

G2 candidate rediscovery/full perturbed scenarios and G7 short-window Cartesian validation remain
open and parked. Current storm output is sensitivity analysis on a baseline event set, without
warning-completeness or short-lead control/timing claims. Their original questions and acceptance
descriptions remain in the retained 8 September roadmap; recording them does not activate them.

The Johlander density replication, WAM-IPE forecast comparison, new covariance, manoeuvre,
ballistic-coefficient, differential-drag and learned-propagator recipes remain parked. GNSS,
Earth-observation and additional weather applications are discovery topics only. A general
scientific-data or AI-assisted acceptance platform remains a hypothesis, with no framework,
generic adapter, AI interface, MCP server, browser redesign or new repository authorised.

Radio remains dependent on a partner, permitted beam use and suitable observation/monitoring
evidence. Measured beams are CC BY-NC 4.0 and used for research only; constructed pointing agreement
does not establish interference detection, recovered observing time or an operational schedule.

## Standing evidence rules and current claims

Every claim retains its population, method, reference and limitation. Preserve original results
and dated corrections. All four orbital windows have been inspected; their historical tuning and
held-out labels do not create untouched evaluations for new recipes. September remains a
retrospective physical diagnostic and will not be reused as a hold-out. Forecast skill requires
archived issue-time evidence; observed-weather hindcasts do not establish it.

Use real records for any later external case; do not manufacture observations or absent test
conditions. Independent processing does not automatically provide an independent physical
reference or human acceptance. Test totals and hashes support a record; they do not establish
scientific validity, demand or confidentiality. No broader network-isolation claim follows from
an application guard.

The generated block below is preserved exactly from the claims-bound roadmap at `3e5a64c`,
using that retained source rather than numbers retyped from the proposal. The claims manifest,
evidence objects, paper, frozen protocols, original results and published corrections remain fixed.
No publication, message, commit, push or implementation follows from recording this plan.

## Current results from the claims manifest

<!-- BEGIN CLAIMS:results -->
15 spacecraft in 5 altitude bands across 4 inspected windows; 1,249 raw element sets, 1,193 usable at some lead and 10,310 usable set/lead pairs. These are epoch-based reconstructions; historical publication availability is not established.

Consistency covariance bounds absolute accuracy in neither direction. Component coverage varies by mission, window and lead; storm residuals and Sentinel-6A in April 2024 control expose undercoverage. Storm output is a sensitivity analysis on the baseline event set; candidate discovery is not repeated.

Both local learned-propagator checkpoints remain negative findings: 0/40 pooled paired medians improve; 3/40 tails improve. The stored adoption rule rejects both checkpoints.

September retrospective physical diagnostic: prediction MAE 4.284 km versus 17.254 km for zero prediction. 11/13 events beat zero; SWOT and one Sentinel-3A event do not. September will not be reused as a hold-out for any new recipe.

Other declared offsets: crossing agreement 4608/4704 (98.0%); false crossings 45/2016; missed crossings 51/2022. Constructed pointings on inspected windows; measured beams are CC BY-NC and used for research only.

Exact boundary offsets: crossing agreement 700/1344 (52.1%); false crossings 642/1342; missed crossings 2/702. Constructed pointings on inspected windows; measured beams are CC BY-NC and used for research only.
<!-- END CLAIMS:results -->
