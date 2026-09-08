# Decisions recorded for review — 2026-09-08

This replaces the previous feature plan with the strategy report's five decisions. The offers and experiments below are recorded, not built or launched. The current repository is a research benchmark and local comparison tool. It has no customer acceptance, operational warning-completeness evidence or independent orbit determination.

## 1. Repair and maintain the evidence contract

The dated covariance-basis correction, reader-edited paper, current September status and shared public-claims record are implemented for review. The [claims manifest](docs/assets/claims-v2.json) binds each published claim to its result hash, method, population, denominator, reference type, censoring and permitted wording. [Every component-coverage change](docs/covariance-basis-correction.md) remains inspectable. Joint covariance calibration, reference dependence and causal availability remain separate unresolved questions.

All four windows have been inspected: April 2024 control, May 2024, August 2024 held out and October 2024 held out. The latter names retain their historical roles only. No new recipe may fit on one of these windows and claim another as an untouched adoption test. September's locally frozen protocol is a retrospective physical diagnostic and will not be reused as a hold-out for any new recipe. Any new recipe needs a prospectively frozen population, endpoint, baseline and decision rule before its outcomes are inspected.

## 2. Offer an orbit-product and adapter acceptance review

The proposed paid offer is a bounded review of an orbit product and its software adapter against a customer-agreed acceptance criterion. Agree the integration decision, responsible owner, reference conventions, input rights, baseline workflow, exclusions and tolerance before work starts. Report accepted and failed cases with their practical consequences; passing a parser is not a standards or operational certification.

The deliverable is a reopenable case bundle: supplied files and rights record, hashes, time/frame/unit/origin conventions, selected adapters, exact software environment, baseline and candidate outputs, signed differences, acceptance result and limitations. Acceptance requires a second person to open the bundle on a second machine and reproduce the decision without relying on the author's session. [Portable CLI bundles and a public second-machine reproduction](docs/case-bundles.md) are implemented. An independent person reopening a rights-cleared customer case remains open; the public criterion is not customer acceptance. No price, customer agreement, delivery date or outreach is implied by recording this offer.

## 3. Use a TLE-to-OMM migration audit as the entry offer

The entry offer checks whether a customer's existing TLE path and proposed OMM path preserve the same intended orbit and downstream behaviour. The explicit compatibility matrix below defines the planned review. Every row is **unverified for a customer adapter** until a supplied case is exercised; this is not a claim of general OMM conformance.

| Compatibility axis | TLE path to record | OMM path to record | Acceptance evidence required |
| --- | --- | --- | --- |
| Object identity | Legacy catalogue field, Alpha-5 handling, joins | Numeric/extended identifiers, designators, joins | Identity survives import, storage, browser display and export without truncation or collision |
| Time and availability | State epoch and separately known acquisition history | EPOCH, TIME_SYSTEM, CREATION_DATE and separate publication/retrieval times | Same declared instant; unknown availability stays unknown; epoch is not publication |
| Frame, centre and units | SGP4/TEME conventions and implicit units | REF_FRAME, CENTER_NAME and declared units | Supported conversions agree; unsupported combinations fail explicitly |
| Mean-element theory | SGP4 constants, drag fields and conventions | MEAN_ELEMENT_THEORY, constants and drag conventions | Matched supported settings reproduce the baseline within the agreed tolerance |
| Optional and missing data | Absent metadata and fixed-width limits | Optional metadata, covariance and missing fields | No invented values; covariance basis and units remain attached to the matrix |
| Full adapter path | Parser through propagation and downstream joins | Parser through propagation and downstream joins | Round-trip fields and signed state differences remain reproducible through storage, browser and export |

A review must distinguish format compatibility, numerical propagation agreement and product accuracy. An adapter audit establishes only the criteria actually tested. The second-person reopenable-bundle test from decision two also applies here.

The [8 September audit of driftwatch's own paths](docs/migration-audit-2026-09-08.md) records every axis as passed, failed or untested. Optional-field defaults and covariance loss are failed checks; browser display/export and the complete browser round trip remain untested. These results do not verify a customer's adapter.

## 4. Advance one bounded scientific experiment at a time

The two learned-propagator checkpoints remain negative findings under their stored rule. They are not candidates for deployment or evidence that a new training recipe will work.

The density lane begins with a bounded replication of [Johlander and colleagues (2026), *Thermospheric mass density derived in near real time from space debris*](https://doi.org/10.1051/swsc/2026005). Freeze a limited population, time span, reference, preprocessing, availability cutoff and scoring rule before running it. First reproduce the published estimator within declared replication limits; then compare against persistence, the uncorrected model and [WAM-IPE issued forecasts](https://www.spaceweather.gov/products/wam-ipe) at matched lead times using only information available by each issue time. Observed-weather hindcasts must be distinguished from issued forecasts. Record estimator latency, data gaps, manoeuvre treatment and ballistic-coefficient/density identifiability. No new density or forecast-skill claim is permitted before this baseline comparison succeeds on a newly frozen evaluation population. The replication and comparison are open, not implemented.

New covariance scaling, manoeuvre classification, ballistic-coefficient regression and differential-drag recipes have no adoption decision from the inspected windows. Any timing or short-lead application also depends on the open Cartesian dynamical gate below.

## 5. Keep radio research dependent on a partner and the beam licence

The radio branch remains research and partner-dependent. The measured beam data are CC BY-NC 4.0 and used for research only; a commercial offer using them is gated on a licence permitting the intended use or a suitable replacement. Constructed pointings on inspected windows do not demonstrate recovered observing time, interference detection or an operational observing schedule.

A partner pilot would need rights-cleared beam information, actual schedules, acquisition/monitoring records and coordination logs; an agreed baseline and useful decision; and explicit instrument response, cadence and boundary checks. No partner, data access or commercial permission is presumed. Do not build a radio product or send an outreach letter on the strength of the geometric benchmark alone.

## Open acceptance tests from the report

### G1 — Causal availability and late publication (open)

Construct a record whose state epoch precedes a decision time but whose known publication is later. An explicitly epoch-based reconstruction may include it and must say so; a causal replay at the decision time must exclude it. Provider creation time, known publication time, actual retrieval time and state epoch must remain distinct, and unknown values must remain unknown. Reopening the result must preserve those fields and the original acquisition provenance. Repeat the test for historical catalogue membership and a manoeuvre record published after the event. The implemented epoch-selection labelling and time separation do not yet establish a publication-aware causal replay or historical membership reconstruction.

### G2 — Full scenario with candidate rediscovery (open)

The current output is a **sensitivity analysis on the baseline event set**. It rescores stored encounters and cannot discover pairs that a perturbed trajectory brings into the gate.

For a full-scenario acceptance test, construct a pair outside the baseline candidate gate that enters it under the perturbation. The perturbed run must rediscover that pair, recompute closest approach, relative velocity and covariance at the new event, and account for both appearing and disappearing encounters. Compare against an independent dense-trajectory search, including slow encounters, gate seams and multiple local minima. An Office of Space Commerce dataset comparison remains open when suitable data are obtained; synthetic checks alone do not establish catalogue warning recall. Until this test passes, no output may be described as a full perturbed scenario or a complete warning set.

### G7 — Short-window Cartesian dynamical validation (open)

Start controlled Cartesian integrations from the same initial state and perturb each force separately. Over 1–180 minutes and separately over multiple orbital periods, compare the integrated relative position and velocity with the linear relative-motion and secular approximations. Retain signed component errors and zero crossings, including their times; do not score only unsigned maxima or orbit-averaged displacement. Fix tolerances and the force cases before evaluation. Passing this test for the relevant regime gates any timing, short-lead control or differential-drag application. Failure over short windows does not by itself invalidate a separately supported multi-day mean displacement result.

## Current results from the claims manifest

<!-- BEGIN CLAIMS:results -->
15 spacecraft in 5 altitude bands across 4 inspected windows; 1,249 raw element sets, 1,193 usable at some lead and 10,310 usable set/lead pairs. These are epoch-based reconstructions; historical publication availability is not established.

Consistency covariance bounds absolute accuracy in neither direction. Component coverage varies by mission, window and lead; storm residuals and Sentinel-6A in April 2024 control expose undercoverage. Storm output is a sensitivity analysis on the baseline event set; candidate discovery is not repeated.

Both local learned-propagator checkpoints remain negative findings: 0/40 pooled paired medians improve; 3/40 tails improve. The stored adoption rule rejects both checkpoints.

September retrospective physical diagnostic: prediction MAE 4.284 km versus 17.254 km for zero prediction. 11/13 events beat zero; SWOT and one Sentinel-3A event do not. September will not be reused as a hold-out for any new recipe.

Other declared offsets: crossing agreement 4608/4704 (98.0%); false crossings 45/2016; missed crossings 51/2022. Constructed pointings on inspected windows; measured beams are CC BY-NC and used for research only.

Exact boundary offsets: crossing agreement 700/1344 (52.1%); false crossings 642/1342; missed crossings 2/702. Constructed pointings on inspected windows; measured beams are CC BY-NC and used for research only.
<!-- END CLAIMS:results -->

## Review and release gates

The rewritten [paper](docs/paper.md), dated correction and public claim wording stop here for the author's review. Nothing is deposited before the author has read the rewritten paper. No outreach letter goes out before the README matches v2; matching it does not itself authorise sending a letter. No deployment, deposit, new scientific recipe or outreach is part of these recorded decisions.
