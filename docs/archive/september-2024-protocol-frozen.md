# Frozen September 2024 energy-error and propagation protocol

**Scientific protocol frozen 2026-09-08T10:42:57.285144+00:00. Experiment not started.** The required author attestation about previous residual inspection remains pending. Its absence blocks all experiment access; it is a separate fact bound to this protocol hash, not permission to change the scientific rules.

Executable settings and full source hashes: [2026-09-08-september-2024.json](2026-09-08-september-2024.json). Classifier freeze: [2026-09-08-post-manoeuvre-classifier.json](2026-09-08-post-manoeuvre-classifier.json).

## Question and scope

For each published manoeuvre in a fixed calendar month, does the orbital-energy error in the first subsequent public element set account for the signed in-track error 96 hours after that set's epoch? The predictor is calculated from the reconstructed orbit around the set epoch and a baseline estimated strictly before the manoeuvre. The 96-hour reference endpoint is not used to fit that baseline, choose the set, classify the manoeuvre, or adjust the predictor.

This is a test of a retrospective physical diagnostic against an initially uninspected endpoint, subject to author attestation. It is not an operational forecast: the reconstructed orbit around the set epoch would not generally be available at the element set's publication time. A class described as compatible with pre-manoeuvre energy does not identify the observations used in the catalogue fit, prove re-epoching by the producer, or establish publication latency.

The corrected April, May, August and October results must be completed first. No September outcome may be used to settle a pending correction, tune a covariance scale, select an ML recipe, change a radio definition or choose this experiment's thresholds.

## Calendar selection and prior-exposure qualification

Use **2024-09-01 00:00:00 UTC through 2024-10-01 00:00:00 UTC, end exclusive**. September is selected by the calendar rule: the first complete calendar month between the existing August and October benchmark windows. It is not selected by a newly inspected residual, manoeuvre outcome, error maximum or storm-strength comparison. Published manoeuvres whose start lies inside this interval form the primary event population.

The local readiness audit found no recorded September 2024 reconstructed-orbit residual evaluation in the inspected repository, result inventories, available Git metadata or relevant development logs. The inspected result files identify only April, May, August and October windows. This is evidence about the inspected local records, not proof of what has never been calculated or seen. Deleted files, other machines, external notebooks, undocumented calculations and human recollection are outside that audit.

September public element sets and observed weather already fall inside the history used for the earlier October covariance and coefficient fits. Several cached IDS orbit products also span late September into October as product overlap. Therefore September must not be described as unseen in every sense, or as a period for which no orbit data was ever downloaded. The relevant qualification is whether September reference residuals and post-burn outcomes were inspected.

**Author attestation is required before data access.** Scientific choices may be frozen while the attestation is pending. The author must explicitly attest that September reference residuals and post-burn outcomes have never been inspected. The executable guard requires the recorded statement `September reference residuals and post-burn outcomes never inspected`, author identity, the actual attestation time and the SHA-256 of the exact frozen scientific protocol. Elapsed time and absence of a file do not supply that attestation. If the author reports prior inspection, this experiment cannot be labeled newly uninspected under this protocol.

## Fixed population and authoritative manoeuvre records

The population is the following fourteen spacecraft, selected from the existing reference population because each has both an accessible reconstructed orbit and a published manoeuvre record:

| Spacecraft | Repository key | Governing manoeuvre source |
| --- | --- | --- |
| Swarm A | swarm-a | ESA spacecraft thruster product |
| Swarm B | swarm-b | ESA spacecraft thruster product |
| Swarm C | swarm-c | ESA spacecraft thruster product |
| GRACE-FO 1 (C) | gracefo-c | JPL THR1B product via GFZ |
| GRACE-FO 2 (D) | gracefo-d | JPL THR1B product via GFZ |
| CryoSat-2 | cryosat-2 | IDS/SSALTO published manoeuvre registry |
| SARAL | saral | IDS/SSALTO published manoeuvre registry |
| Sentinel-3A | sentinel-3a | SentiWiki Sentinel-3 manoeuvre history |
| Sentinel-3B | sentinel-3b | SentiWiki Sentinel-3 manoeuvre history |
| SWOT | swot | IDS/SSALTO published manoeuvre registry |
| HY-2C | hy-2c | IDS/SSALTO published manoeuvre registry |
| HY-2D | hy-2d | IDS/SSALTO published manoeuvre registry |
| Jason-3 | jason-3 | IDS/SSALTO published manoeuvre registry |
| Sentinel-6A | sentinel-6a | IDS/SSALTO published manoeuvre registry |

Sentinel-1A is omitted before access because the project has not obtained a governing published manoeuvre record for it. Missions with laser ranging alone are not substituted. A mission is not selected or removed because of how many burns, usable sets, successful predictions or extreme errors it turns out to have. Missions with zero published burns remain in the coverage inventory with zero events; no event-level association is estimable for them.

Published records govern event inclusion and burn flags. The orbit-step and element-set-step detectors are measured as cross-checks; a detector miss does not remove a published event or replace the record. Preserve raw source files, source URLs, retrieval times, source time systems, parsing version and SHA-256 hashes. IDS/SSALTO TAI and SentiWiki UTC conventions must follow the corrected parsers; all analysis intervals are normalized to UTC. An authoritative empty event list is distinct from unavailable, malformed or out-of-range coverage. An incomplete published record or absent reconstructed orbit stops the experiment rather than silently dropping the affected mission. An empty registry does not prove physical completeness of the publisher's list.

## Fixed time windows and choice of element set

For each event with interval `[burn_start, burn_end]`, choose the element set with the earliest epoch **strictly after `burn_end`**, without inspecting its residual, predicted error, energy class or reference endpoint. Deduplicate identical epochs by the existing deterministic last-record rule. The search extends through **2024-10-08 01:00:00 UTC**, the existing seven-day reference extension plus one hour after the month ends. No later set may replace an unavailable or poorly performing first set.

The primary propagation target is exactly **96 hours after the chosen set's epoch**, not 96 hours after burn start, burn end, file retrieval or element-set publication. Preserve both the set's propagation age and its epoch delay from burn end. Epoch time is not publication time.

Reference products are requested with fixed padding: from 24 August, supporting the earliest event's prior calibration and orbit averaging, through 12 October, supporting the maximum first-set search endpoint plus 96 hours. The legacy history loader may read earlier GP sets for the secondary covariance fit, but only the event-specific seven-day baseline below enters the primary calibration.

Every additional published burn after the event's end and through its 96-hour target is flagged, including burns completed before the selected set's epoch. The event remains in the primary population. Preserve both detector overlap indicators and the full list of additional burns.

## Prior calibration and fixed orbit-averaging convention

For each burn, use clean sets from the **seven days preceding that burn**, with at least **three** eligible sets required to calibrate the predictor. A calibration set must have finite reconstructed and SGP4 mean semi-major axes, satisfy `set_epoch + one_nominal_revolution < burn_start`, and have no published manoeuvre overlapping the inclusive interval from 24 hours before its epoch through one nominal revolution after it. No same-burn or later endpoint contributes to the baseline. With fewer than three clean sets, retain the event and report its predictor unavailable; do not enlarge the lookback or borrow a fitted baseline from its later residual.

Use the same centered, one-revolution averaging convention for reconstructed and SGP4 semi-major axes. Fix the revolution length before September state access from the mission registry's nominal altitude:

`period_minutes = round(2*pi*sqrt((6378.137 km + nominal_altitude_km)^3 / mu) / 60)`

where `mu = 398600.4418 km^3/s^2`. The corresponding registry values are:

| Spacecraft | Nominal altitude, km | Frozen nominal period, min |
| --- | ---: | ---: |
| Swarm A and C | 462 | 94 |
| Swarm B | 503 | 95 |
| GRACE-FO 1 and 2 | 490 | 94 |
| CryoSat-2 | 717 | 99 |
| SARAL | 781 | 100 |
| Sentinel-3A and 3B | 814 | 101 |
| SWOT | 891 | 103 |
| HY-2C and 2D | 957 | 104 |
| Jason-3 and Sentinel-6A | 1336 | 112 |

These are registry inputs, not altitudes or periods estimated from September outcomes. The source manifest freezes their definitions. The semi-major-axis conversion uses the stated `mu`; public element-set propagation itself uses the benchmark's WGS72 SGP4 implementation. The calibration absorbs the existing mean-orbit convention offset; it does not retune propagation constants.

Let `a_set` and `a_truth` be the averaged semi-major axes at each clean set epoch. Define the baseline offset `b` as the median of `a_set - a_truth`, and its scatter `s` as `1.4826 * median(abs((a_set - a_truth) - b))`. At the first post-event set epoch, set `a_corrected = a_set - b` and `delta_a_error = a_corrected - a_truth`.

Interpolation of the reconstructed mean at an epoch requires two adjacent finite mean values bracketing that epoch, separated by no more than **90 seconds**. Missing mean values are not bridged across a reference gap. Full orbit-averaging windows are required. Missing or nonfinite epoch information leaves the predictor unavailable while preserving the event and, when possible, its measured endpoint.

## Primary predictor, endpoint and sign

Retain the signed specific-energy difference:

`missing_specific_energy = mu/2 * (1/a_corrected - 1/a_truth)`

in km²/s². This is `epsilon_truth - epsilon_corrected_set`, where specific orbital energy is `epsilon = -mu/(2*a)`. Its name does not imply that it must be positive.

The fixed first-order prediction is:

`predicted_in_track_km = 1.5 * sqrt(mu/a_truth^3) * delta_a_error * (96*3600)`.

The measured endpoint is the **truth-minus-SGP4** position residual at 96 hours, projected into the reconstructed orbit's radial/in-track/cross-track basis. The in-track sign in the predictor and endpoint is therefore the same. A positive `delta_a_error` predicts a positive truth-minus-SGP4 along-track residual under this approximation. Do not reverse signs, fit a multiplicative factor or subtract an endpoint-derived intercept after inspection.

A valid measured endpoint requires reference coverage, finite reconstructed position and velocity, finite SGP4 position and zero SGP4 error. Failures remain explicit unavailable endpoint fields, with a reason. The predictor's usefulness is assessed against that measured endpoint, not against a later public element set treated as truth.

## Energy-fraction classes, fixed independently of the primary score

Estimate the event's semi-major-axis change `delta_a_burn` as the median orbit-mean semi-major axis in the **three hours after burn end** minus the median in the **three hours before burn start**. Preserve its value and any missing-data limitation. These post-event plateau measurements are retrospective diagnostics and are not the primary endpoint or the prior calibration baseline.

When the required quantities are finite and `delta_a_burn` is nonzero, define the untruncated fraction:

`fraction = 1 + delta_a_error/delta_a_burn`.

Only assign a resolved class if `abs(delta_a_burn) >= 3*s`. The author-specified thresholds to freeze before execution are:

- `fraction <= 0.25`: **pre-manoeuvre-energy compatible**;
- `fraction >= 0.75`: **post-manoeuvre-energy compatible**;
- between 0.25 and 0.75: **mixed**;
- insufficient calibration, missing/nonfinite fraction, zero measured burn change or an unresolved change: **unresolved**.

Store fractions outside [0,1] without clipping. The classes are compatibility descriptions, not diagnoses of the producer's internal fitting process. An unresolved class does not remove a finite calibrated predictor/endpoint pair from the primary numerical score.

## Primary reporting and predefined diagnostics

The event list includes **all recorded in-month burns**, including detector misses, poorly predicted events, additional burns, insufficient calibration, missing first sets and unavailable outcomes. Report the total event count, finite calibrated predictor/endpoint pair count and unavailable count, with event-level reasons. Numerical prediction metrics necessarily use the finite calibrated pairs; the full denominator and missingness inventory remain beside them.

The principal numerical comparison is the mean absolute 96-hour prediction error `mean(abs(endpoint - prediction))` against the zero-prediction baseline `mean(abs(endpoint))`, on exactly the same pairs. Also report median absolute prediction error, median signed prediction error, sign-agreement count and fraction, the number with a zero predictor or zero endpoint, and the slope through the origin. Sign agreement uses the recorded signed values and `sign(0)=0`; the zero count makes this convention visible.

Report Pearson correlation, ordinary least-squares slope and intercept, and Spearman correlation only when there are at least two finite pairs and both variables vary. These are descriptive association diagnostics, not a fitted correction to be reapplied to the predictions. A favorable correlation without lower prediction error is not evidence of calibrated prediction. There is no independent-trial significance claim, binomial confidence interval, operational acceptance threshold or permission to substitute whichever metric happens to look best.

The primary paired score includes finite calibrated events **even when additional burns occur**. Separately report the predefined diagnostic subset with no additional recorded burn between the original event and its endpoint. Do not promote that subset to the primary result after seeing its score. Report per-spacecraft results, leave-one-spacecraft-out summaries and leave-one-burn-out summaries. These deletions measure fragility; repeated burns and spacecraft share conditions and are not independent replicates or confidence intervals.

## Secondary propagation and covariance summaries

For all element sets with epochs in the September calendar interval, generate the existing lead grid: 6, 12, 24, 36, 48, 72, 96, 120, 144 and 168 hours. In this secondary free-flight benchmark, exclude a set/lead pair when a published manoeuvre overlaps the inclusive interval from 24 hours before set epoch to the target, or when reference coverage or propagation validity fails. This exclusion does not apply to the primary post-manoeuvre event population.

Use the corrected summary definitions already completed on the four legacy windows. Publish per-lead usable/total counts, spacecraft composition, actual counts and fractions exceeding the 25 km in-track tolerance, explicit linear and nearest-rank quantiles, and the primary empirical-coverage criterion requiring at least 95% of finite usable trials inside tolerance. Keep threshold failure, missing-coverage censoring and the longest tested lead distinct. Report per-component covariance coverage and per-spacecraft disaggregation, with the existing deletion sensitivities. Do not fit a new covariance scale or modify a model using this period. No storm-term or ML model is trained on this experiment's outcomes.

## Freeze, execution guards and audit trail

Before any new September reference-state/residual access, all of the following must be complete:

1. Public manoeuvre records and their time-system corrections govern the revised legacy benchmark.
2. The corrected legacy reference, covariance, radio and ML results are complete and recorded, including hourly ML exclusion masks and verified checkpoint objectives.
3. A dated JSON protocol and matching Markdown freeze the interval, all fourteen missions, every numerical rule above, runtime/dependency versions and the source manifest without using September outcomes. `frozen_at` records that actual freeze. Hash every project Python source under `src/driftwatch`, including the scorer and its dependencies; retain the environment lockfile/runtime information alongside it. This scientific freeze may precede author attestation.
4. The frozen protocol's `author_attestation_path` identifies a separate JSON file, resolved relative to the protocol directory unless absolute. Before access, that file must contain `statement` with the exact required sentence, nonempty `author`, an actual timezone-aware `attested_at`, and `protocol_sha256` matching the frozen JSON bytes. Missing, future-dated, malformed or mismatched attestation fails the gate. The scientific protocol is not edited to add the later attestation.
5. The executable checks the bound attestation, actual freeze field, exact required source-file inventory and every source hash before creating an access marker or loading experiment data.

Execution creates `first-data-access.json`, recording the original start time, protocol and source-manifest hashes and bound attestation, before loading new inputs. The first marker is immutable. A pre-existing marker requires an explicit `resume=True`; a resume must match the original protocol, every scientific source hash and attestation hash. It is a continuation of the original access, not a fresh uninspected experiment.

Freeze the complete selected GP table to a hashed snapshot before any mission scoring. For each mission, persist and hash the reconstructed state table, exact manoeuvre intervals and their metadata, and copies of the named cached source files before scoring. Even the initial calculation reads its verified persisted snapshots. An interrupted mission with committed inputs retries from those same snapshots and the fixed GP table. Input acquisition interrupted before a snapshot commit may be retried under the same source-selection rules; uncommitted inputs and outputs remain identifiable in the failed attempt and cannot be used as completed results.

Each mission completion requires separately persisted trial, event and coverage files, all included in a completion hash manifest bound to the protocol, GP and mission-input manifests. Verify every existing input and completion before loading another mission. Skip a mission only when all required files and hashes match; changed inputs, missing files, altered outputs or a changed protocol reject the resume. Rebuild combined summaries only from verified mission completions, preserving all fourteen missions and every recorded event. The final completion manifest hashes both aggregate files and every mission completion.

Each attempt records its start, stage, completed or skipped missions, completion or failure time and failure reason. Preserve failed/partial attempts and their outputs; a failure is not permission to alter the period, remove a mission or silently start again with different code. Any necessary scientific correction after access requires a dated disclosed deviation, and its confirmatory status must be reassessed before proceeding. Metadata writes use atomic replacement and bounded retry for transient file-access failures.

Retain immutable source and parsed-input snapshots and their provenance, the frozen protocol, bound author attestation, actual code hashes, per-mission trial files, every event row, source-coverage and detector-miss counts, combined secondary trials, primary and sensitivity summaries, and the final completion record. Report the completed result regardless of whether the physical predictor helps. Protocol freeze alone does not authorise data access; all execution gates above must pass.
