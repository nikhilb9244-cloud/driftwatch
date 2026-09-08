# Public element sets against reconstructed orbits: a record-controlled reference benchmark

Nikhil Bhana · Cape Town, South Africa

ORCID: 0009-0003-2220-627X · nikhilb9244@gmail.com

This version, v2, supersedes v1 at doi [10.5281/zenodo.22656992](https://doi.org/10.5281/zenodo.22656992). It corrects manoeuvre exclusions, horizon criteria and covariance coordinates, and adds the completed calendar replay and topocentric comparison while retaining the learned-propagator negative findings.

Evidence object: [benchmark-v2.json](assets/benchmark-v2.json), SHA-256 `76c463a7a6e9728425f846aea7cc1fc44cbf0b316be9fdf4726a148505b7ba48`.

## Abstract

Public element-set errors vary sharply with altitude, disturbance and mission. For spacecraft at 460–507 km, last-pass/first-fail brackets are 120/144 hours in April 2024 control, 48/72 in May 2024, 48/72 in August 2024 held out and 24/36 in October 2024 held out. Whole-set deletion leaves these brackets unchanged; spacecraft deletion preserves all except the August 2024 held out bracket. Bands above 850 km pass through the longest tested lead, with mission-dependent fragility. Consistency covariance fails to cover storm residuals and Sentinel-6A even in the control. The September replay gives mean absolute prediction error 4.284 km against 17.254 km for zero prediction; 11 of 13 events improve, with SWOT and one Sentinel-3A event as the exceptions. Constructed topocentric crossings agree in 98.0% of cases away from the deliberate boundary offsets and 52.1% at them. Both learned-propagator checkpoints are rejected. These results describe inspected populations, not transferable operating guarantees.

## Population and comparison method

Building on [Flohrer, Krag and Klinkrad (2008)](https://amostech.com/TechnicalPapers/2008/Orbital_Debris/Flohrer.pdf), who estimated covariance from element-set consistency, this work measures component coverage against reconstructed orbits with covariance and residuals expressed in the same basis. Extending [Mason's (2013)](https://arxiv.org/abs/1304.0842) NASA Ames comparison of element sets with reference ephemerides, it reports mission-specific storm and control comparisons, recorded-manoeuvre exclusions and deletion-sensitive horizon brackets. Alongside [Parker and Linares (2024)](https://doi.org/10.2514/1.A36164), who examined catalogue decay and geomagnetic forecast performance during the Gannon storm, it measures propagation residuals against reconstructed orbits without interpreting observed storm conditions as issued forecasts. Following [Acciarini, Baydin and Izzo (2025)](https://doi.org/10.1016/j.actaastro.2024.10.063), who introduced differentiable and learned SGP4 propagation, it records paired negative findings for the local checkpoints and public-data recipe rather than claiming to reproduce their experiment.

We compare public SGP4 element sets with reconstructed reference orbits for 15 spacecraft in 5 altitude bands. The sample spans 460–1,338 km and contains 1,249 raw element sets. Of these, 1,193 contribute a usable comparison at some lead, yielding 10,310 set/lead pairs. Each pair compares propagation from an element-set epoch with the reference state at the same time. These are epoch-based reconstructions; state epochs do not establish historical publication or availability.

The windows are April 2024 control, May 2024, August 2024 held out and October 2024 held out. All have been inspected. The retained “held out” names describe their historical roles; the corrected comparisons are descriptive, and none of these windows remains an untouched evaluation population. The supplement records the exact epoch selections and mission composition at each lead.

Published manoeuvre records govern exclusions where integrated. A recorded burn from 24 hours before the element-set epoch through the comparison time excludes that pair. This span is an analysis rule, not a measured catalogue fitting arc. Missing record coverage is not evidence of no burn. Orbit and element-set detectors provide cross-checks on recorded missions and explicitly identified exclusions elsewhere. The IDS registry does not independently establish exhaustive reporting of every firing.

The reference products come from the ESA Swarm, JPL/GFZ GRACE-FO, CNES/SSALTO and Sentinel precise-orbit archives cited in the supplement. GRACE-FO adds another mission, producer and thruster record, although these and Swarm remain related GNSS-derived references. Laser ranging supplies a different measurement on sampled passes. Agreement in range helps check conventions and reference points; it does not measure the complete spatial tail distribution. Debris, eccentric orbits and unmeasured catalogue objects are outside this population.

## Residual horizons

A lead passes when at least 95% of finite, usable absolute in-track residuals lie within 25 km. The bracket joins the last passing bin to the first failing bin; it does not locate a continuous transition between them. Passing through the longest tested lead, 168 hours, is right censoring. Missing observations end the supported interval separately from a measured threshold failure. Empirical counts determine the primary result; linear and inverted-CDF quantiles remain alongside them in the supplement.

| Band | Window | Primary observed endpoints | Remove one spacecraft | Remove one set |
| --- | --- | --- | --- | --- |
| 400-600 km | April 2024 control | 120 h pass / 144 h fail | 120 h pass / 144 h fail | 0/95 deletions change a reported criterion |
| 400-600 km | May 2024 | 48 h pass / 72 h fail | 48 h pass / 72 h fail | 0/91 deletions change a reported criterion |
| 400-600 km | October 2024 held out | 24 h pass / 36 h fail | 24 h pass / 36 h fail | 0/100 deletions change a reported criterion |
| 400-600 km | August 2024 held out | 48 h pass / 72 h fail | 36 h pass / 48 h fail; 48 h pass / 72 h fail | 0/93 deletions change a reported criterion |
| 600-750 km | April 2024 control | 120 h pass / 144 h fail | 120 h pass / 144 h fail; passes through the longest tested lead (168 h) | 3/45 deletions change a reported criterion |
| 600-750 km | May 2024 | passes through the longest tested lead (168 h) | 120 h last pass; unavailable at 144 h; passes through the longest tested lead (168 h) | 0/41 deletions change a reported criterion |
| 600-750 km | October 2024 held out | 96 h pass / 120 h fail | 96 h pass / 120 h fail; passes through the longest tested lead (168 h) | 1/42 deletions change a reported criterion |
| 600-750 km | August 2024 held out | 120 h last pass; unavailable at 144 h | 120 h last pass; unavailable at 144 h | 0/39 deletions change a reported criterion |
| 750-850 km | April 2024 control | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/57 deletions change a reported criterion |
| 750-850 km | May 2024 | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/65 deletions change a reported criterion |
| 750-850 km | October 2024 held out | 120 h pass / 144 h fail | 48 h pass / 72 h fail; passes through the longest tested lead (168 h) | 2/51 deletions change a reported criterion |
| 750-850 km | August 2024 held out | passes through the longest tested lead (168 h) | 144 h last pass; unavailable at 168 h; passes through the longest tested lead (168 h) | 0/60 deletions change a reported criterion |
| 850-1000 km | April 2024 control | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/78 deletions change a reported criterion |
| 850-1000 km | May 2024 | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/77 deletions change a reported criterion |
| 850-1000 km | October 2024 held out | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/60 deletions change a reported criterion |
| 850-1000 km | August 2024 held out | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/65 deletions change a reported criterion |
| 1000-1400 km | April 2024 control | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/37 deletions change a reported criterion |
| 1000-1400 km | May 2024 | passes through the longest tested lead (168 h) | 144 h pass / 168 h fail; passes through the longest tested lead (168 h) | 19/30 deletions change a reported criterion |
| 1000-1400 km | October 2024 held out | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/32 deletions change a reported criterion |
| 1000-1400 km | August 2024 held out | passes through the longest tested lead (168 h) | passes through the longest tested lead (168 h) | 0/35 deletions change a reported criterion |

The low-altitude brackets survive deletion of any whole element set. Removing a spacecraft preserves the April 2024 control, May 2024 and October 2024 held out brackets; in August 2024 held out it can move the bracket earlier. The intermediate bands are more sensitive to who remains in the sample. In May 2024, the 600-750 km band passes through the longest tested lead with only 12 CryoSat-2 sets remaining. In August 2024 held out, its next lead has no usable observations. Above 850 km, the pooled bands pass through the longest tested lead, but the highest band in May 2024 can fail there after a spacecraft deletion.

Successive fits share tracking data; leads reuse trajectories; missions share orbit producers and storm conditions. The deletion checks describe fragility under those dependencies. They are not confidence intervals, and the selected disturbed windows cannot supply a sampling distribution for future storms.

## September calendar replay

The pre-registered endpoint was signed in-track error 96 hours after the first post-manoeuvre element-set epoch. The locally frozen protocol yielded 13 complete recorded-burn predictor/endpoints, with mean absolute prediction error 4.284 km against 17.254 km for the zero-prediction baseline. The energy predictor beat that baseline in 11 of 13 events; SWOT and one Sentinel-3A event did not.

The failures matter. GRACE-FO D has a calibrated burn fraction of -2.397 and a 28.35 km prediction error. It still improves on its 55.20 km zero-baseline error, but that large residual limits the diagnostic. SWOT's event on 2024-09-13 has the wrong sign: the prediction is +2.232 km and the observed residual is -0.525 km. Its 2.757 km prediction error exceeds the 0.525 km baseline. The other baseline failure is Sentinel-3A on 2024-09-18, with a 1.037 km prediction error against 0.708 km for the zero baseline.

Calibration uses only earlier clean sets. Every published in-month burn remains in the inventory, including events with an intervening burn. The predeclared subset without another recorded burn has 12 complete endpoints. The mean prediction error stays below the zero baseline in all 7 spacecraft deletions.

The event inventory is not an independent sample. Its 13 rows share 12 distinct endpoints. Closely spaced Sentinel-3B burns overlap the fixed energy plateaus; the no-later-burn subset does not isolate the earlier plateau. An intermediate calibrated fraction therefore does not establish mixed catalogue fitting for an isolated manoeuvre.

The protocol and separate author attestation preceded experiment access locally; this is not externally timestamped preregistration. Earlier public-element and weather history and overlapping orbit products already existed. This replay is a retrospective physical diagnostic, not a prediction shown to have been available at element-set publication. September will not be reused as a hold-out for any new recipe. The [status page](protocols/september-2024-execution-status.md) and [complete event tables](locked-benchmark-v2-tables.md) retain chronology, exclusions, unresolved classifications and source-retention limits.

## Component covariance and reference checks

Consistency covariance measures disagreement between catalogue solutions. It can miss shared error or include independent fit noise, so it bounds absolute accuracy in neither direction. We transport the predicted-state RIC covariance into each residual's truth RIC basis before extracting component sigmas. Component intervals are distinct from joint spatial ellipsoid coverage; this paper reports the former.

| Population | Window | Lead h | Component | Inside 2σ |
| --- | --- | --- | --- | --- |
| 400-600 km | April 2024 control | 24 | radial | 95/95 (100.0%) |
| 400-600 km | April 2024 control | 24 | in_track | 93/95 (97.9%) |
| 400-600 km | April 2024 control | 24 | cross | 5/95 (5.3%) |
| Jason-3 | April 2024 control | 24 | radial | 14/19 (73.7%) |
| Jason-3 | April 2024 control | 24 | in_track | 19/19 (100.0%) |
| Jason-3 | April 2024 control | 24 | cross | 15/19 (78.9%) |
| Sentinel-6A | April 2024 control | 24 | radial | 15/18 (83.3%) |
| Sentinel-6A | April 2024 control | 24 | in_track | 0/18 (0.0%) |
| Sentinel-6A | April 2024 control | 24 | cross | 16/18 (88.9%) |

The table illustrates why coverage must be stated by component and mission. In-track intervals fail during storms, while even the control can fail in another component. At the same nominal high altitude, Jason-3 passes the 2σ in-track check for 19/19 sets while Sentinel-6A fails completely, 0/18; the latter's fitted median sigma is 0.038 km, about a tenth of its 0.288 km median residual, with no cause established by this comparison.

The storm term is outside this paper's scope; its coefficient support, residuals and shift diagnostics remain in [the benchmark tables](benchmark-v2-tables.md) and [storm-term analysis](storm-validation.md).

## Topocentric crossing agreement

An orbital-component angle is not a sky-track displacement, and dividing in-track error by orbital speed is not a beam-crossing time error. We instead compare complete topocentric trajectories with a rotating observer and fixed celestial pointings against the measured MeerKAT beams. The cases are constructed pointings on previously inspected windows. They do not represent an observing schedule or detected interference.

Of 10,310 source-filtered rows, 112 have qualifying nominal visibility and complete curves. These yield 18,144 beam/pointing/observation cases from 94 element sets on 12 spacecraft. Nominal eligibility excludes reference-visible events whose predictions fail the gate. Repeated beams, offsets and intervals do not create independent trajectories.

For the full observation interval, the other declared offsets agree in 4,608/4,704 cases, with 45/2,016 false predicted crossings and 51/2,022 missed reference crossings. At the deliberately exact half-power boundary, agreement falls to 700/1,344. This construction-based split is a sensitivity check, separate from numerical near-boundary diagnostics.

| Element-set age h | Pointings | Agreement / all cases | False / predicted crossings | Missed / reference crossings | Closest times n | Median absolute Δt s | Linear p95 absolute Δt s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | Exact boundary offsets | 30/60 (50.0%) | 30/60 | 0/30 | 60 | 0.0652545 | 0.161698 |
| 6 | Other declared offsets | 210/210 (100.0%) | 0/90 | 0/90 | 210 | 0.0652724 | 0.161719 |
| 12 | Exact boundary offsets | 228/420 (54.3%) | 191/419 | 1/229 | 420 | 0.0596551 | 0.221621 |
| 12 | Other declared offsets | 1470/1470 (100.0%) | 0/630 | 0/630 | 1470 | 0.0596575 | 0.22162 |
| 24 | Exact boundary offsets | 106/204 (52.0%) | 98/204 | 0/106 | 204 | 0.058273 | 1.60689 |
| 24 | Other declared offsets | 691/714 (96.8%) | 11/306 | 12/307 | 714 | 0.0583181 | 1.60688 |
| 36 | Exact boundary offsets | 6/12 (50.0%) | 6/12 | 0/6 | 12 | 0.0541513 | 0.0544004 |
| 36 | Other declared offsets | 42/42 (100.0%) | 0/18 | 0/18 | 42 | 0.0540956 | 0.0544217 |
| 48 | Exact boundary offsets | 164/324 (50.6%) | 160/324 | 0/164 | 324 | 0.0225135 | 0.800852 |
| 48 | Other declared offsets | 1109/1134 (97.8%) | 11/486 | 14/489 | 1134 | 0.0225488 | 0.800856 |
| 72 | Exact boundary offsets | 29/60 (48.3%) | 30/59 | 1/30 | 60 | 0.0809106 | 4.8007 |
| 72 | Other declared offsets | 198/210 (94.3%) | 6/90 | 6/90 | 210 | 0.0809555 | 4.80074 |
| 96 | Exact boundary offsets | 0/0 (unavailable) | 0/0 | 0/0 | 0 | unavailable | unavailable |
| 96 | Other declared offsets | 0/0 (unavailable) | 0/0 | 0/0 | 0 | unavailable | unavailable |
| 120 | Exact boundary offsets | 40/72 (55.6%) | 32/72 | 0/40 | 72 | 0.946547 | 3.68884 |
| 120 | Other declared offsets | 229/252 (90.9%) | 11/108 | 12/109 | 252 | 0.947119 | 3.68884 |
| 144 | Exact boundary offsets | 43/84 (51.2%) | 41/84 | 0/43 | 84 | 0.181079 | 12.5503 |
| 144 | Other declared offsets | 281/294 (95.6%) | 6/126 | 7/127 | 294 | 0.181252 | 12.5504 |
| 168 | Exact boundary offsets | 54/108 (50.0%) | 54/108 | 0/54 | 108 | 0.0770706 | 0.623042 |
| 168 | Other declared offsets | 378/378 (100.0%) | 0/162 | 0/162 | 378 | 0.0771282 | 0.622893 |

Each populated age bin has a different spacecraft composition, so these agreements do not establish an increase in agreement with element-set age.

Age bins are measured from element-set epoch, not publication. Agreement includes both crossing and non-crossing cases. Closest-time errors use all finite uncensored paired closest times, including false and missed crossings; entry and exit errors in the supplement require suitable crossings on both tracks. The table therefore keeps classification denominators beside timing errors. Receiver response, received power, coherence and real monitoring outcomes remain unmeasured. The measured beam data are CC BY-NC 4.0 and are used for research only.

## Rejected learned propagators

The 2 local learned-propagator checkpoints lower the pooled paired median in 0/40 model/window/lead cells and lower the interpolated tail in 3/40. Both are rejected by the stored adoption rule. Some individual spacecraft improve while tails worsen. These are negative findings for the stated checkpoints, population and recipe, not a rejection of learned propagation as a field.

This is a local adaptation of the published dSGP4 method. Checkpoints were selected by the fixed training objective and checked again after reload. The evaluation windows were already inspected before correction; their historical names do not make this rerun confirmatory. Training traces, paired denominators, recipes and checkpoint identities remain in [the supplement](benchmark-v2-tables.md#revised-learned-propagator-evaluation).

## Corrections and reproducibility

The covariance-basis correction dated 2026-09-08 changes coverage counts in 39/2400 original benchmark cells and 10/570 September secondary cells. All affected coverage counts are radial. Residuals, exclusions, in-track coverage counts and horizons are unchanged. [Every cell's change](covariance-basis-correction.md) is retained alongside the earlier manoeuvre-record and statistical corrections. The frozen September outputs remain intact; the supplement identifies the later covariance amendment.

The earlier post-manoeuvre classifications describe calibrated energy compatibility, not the catalogue's unobserved fitting procedure. Their thresholds were author-reported as chosen before execution, but the first commit containing them also contained results. The later dated classifier freeze cannot establish earlier preregistration. State epoch spacing does not establish publication cadence.

The evidence object binds input files, method definitions, source hashes and completed-result metadata. Prose is authored in a Markdown template; only figures and tables are substituted from evidence. Tests reject unbound figures or stale rendered text. [Rebuild instructions](publication-rebuild.md) specify the retained inputs and checks. The [complete tables](benchmark-v2-tables.md) hold hashes, checkpoints, timestamps and detailed references; the [archived earlier paper](archive/paper-2026-09-v1.md) preserves the superseded record.

Independent checks exposed clock, frame, fitting-window and station-reference-point errors that internally consistent calculations had missed. Those checks support the stated comparisons. They do not establish independent orbit determination, calibrated operational collision probabilities, warning completeness or a general radio operating horizon. Short-lead timing applications also require the open Cartesian dynamical validation recorded in the [roadmap](../ROADMAP.md).

## Assurance appendix

| Boundary | Fault | Independent check |
| --- | --- | --- |
| Declared time system to comparison epoch | GPS orbit epochs were read as UTC. | Read the orbit header independently and compare lead-dependent residuals after conversion. |
| Provider states to propagation frame | SpaceX inertial states were interpreted in the catalogue frame; the header identified only the covariance frame. | Compare transformed states with CelesTrak's fit to the same source file, and check the rotation with a second library. |
| Sampled position to instantaneous velocity | A finite-difference chord biased the energy-derived semi-major axis. | Reproduce the bias on an orbit with known velocity and calibrate against earlier clean reference arcs. |
| Station ground marker to telescope reference point | Separately published laser-station eccentricities were omitted. | Compare residuals by station and elevation, using ILRS offsets independently of the orbit reader. |
| Configured fit window to actual inputs | A live covariance fit included stored sets outside its labelled window. | Count and bound the input epochs themselves, then compare the refitted result with the earlier fit. |
| Process exit status to completed validation | The density-model library could terminate the interpreter before the test runner finished while returning success. | Require a completed test report and compare its count with fresh collection and the retained test inventory. |

The [convention notes](frames-and-time.md), [frame comparison](ephemeris-frame.md), [archived fault record](archive/paper-2026-09-v1.md#7-the-format-and-provenance-faults-as-a-class) and [test-count guard](../scripts/check_test_count.py) retain the supporting checks. The covariance-basis amendment is recorded separately in the corrections section above.

## Acknowledgements

The work uses public element sets from the US Space Force through Space-Track.org and CelesTrak, with thanks to T. S. Kelso; ESA and TU Delft's Swarm orbit and spacecraft-dynamics products; JPL and GFZ's GRACE-FO orbit and thruster products; Copernicus and ESA STEP reconstructed orbits; CNES/SSALTO orbit products and event records distributed through IDS and IGN; and ILRS laser-ranging normal points, station coordinates and eccentricities through the EUROLAS Data Center. The wider repository also uses SpaceX's published predictions, CelesTrak and NOAA SWPC space-weather indices, ESA Kelvins reference inputs, ESA dSGP4 and the US Naval Research Laboratory's atmospheric model. The radio lane used publicly documented MeerKAT receiver and site parameters and one public observation record from the GCN circular cited below. SARAO supplied nothing and has not been consulted. Public measured beam products are attributed separately and retain their research-only use under the stated licence.

## Data and code availability

The [driftwatch repository](https://github.com/nikhilb9244-cloud/driftwatch) provides the code, evidence object, recorded tables and reproduction instructions. Release [paper-2026-09-v2](https://github.com/nikhilb9244-cloud/driftwatch/releases/tag/paper-2026-09-v2) freezes the paper and supporting repository state; the Zenodo version DOI is [10.5281/zenodo.22661809](https://doi.org/10.5281/zenodo.22661809). Code is distributed under the [MIT licence](https://github.com/nikhilb9244-cloud/driftwatch/blob/paper-2026-09-v2/LICENSE). Third-party inputs retain their source terms, and the code licence does not relicense them. Raw SpaceX ephemerides and ESA Kelvins inputs are not redistributed. Product identifiers, retained-file hashes, access limits and reconstruction commands are recorded in the [data-source record](data-sources.md), [complete tables](benchmark-v2-tables.md) and [rebuild instructions](publication-rebuild.md). Citation metadata is in [CITATION.cff](../CITATION.cff).

<!-- BEGIN AVAILABILITY CORRECTION -->
Availability correction - 2026-09-08. Release paper-2026-09-v2.1 supplies 24 project-generated files omitted from paper-2026-09-v2, together with the derived artefacts required for reconstruction and their hashes. The evidence object and affected supporting artefacts were scrubbed to remove local paths, account and machine identifiers, and execution traces; embedded third-party records were replaced by source identifiers and content hashes to avoid redistributing those records. The evidence object's SHA-256 changed from `f19c24451e65d8e0baf6b803f379380aab72146e5ef73687b818397bcb5609e5` to `76c463a7a6e9728425f846aea7cc1fc44cbf0b316be9fdf4726a148505b7ba48`; the [correction ledger](assets/publication-assets-v2.1.json) records the original and replacement hashes for each supporting file. Provider inputs must be obtained from their sources and verified against the recorded hashes, following the [exact-snapshot recovery instructions](publication-rebuild.md). Every published table and substituted figure is unchanged; the invariant comparison reports 0 differences. The correction's version DOI is [pending assignment](#availability-correction).
<!-- END AVAILABILITY CORRECTION -->

## References

- Flohrer, T., Krag, H. and Klinkrad, H. (2008). [Assessment and Categorization of TLE Orbit Errors for the US SSN Catalogue](https://amostech.com/TechnicalPapers/2008/Orbital_Debris/Flohrer.pdf). Advanced Maui Optical and Space Surveillance Technologies Conference.
- Mason, J. (2013, arXiv posting). [Development of a MATLAB/STK TLE Accuracy Assessment Tool, in support of the NASA Ames Space Traffic Management Project](https://arxiv.org/abs/1304.0842). International Space University MSc report.
- Parker, W. E. and Linares, R. (2024). [Satellite Drag Analysis During the May 2024 Gannon Geomagnetic Storm](https://doi.org/10.2514/1.A36164). Journal of Spacecraft and Rockets, 61(5), 1412-1416.
- Acciarini, G., Baydin, A. G. and Izzo, D. (2025). [Closing the Gap Between SGP4 and High-Precision Propagation via Differentiable Programming](https://doi.org/10.1016/j.actaastro.2024.10.063). Acta Astronautica, 226. [Author manuscript and experimental design](https://arxiv.org/html/2402.04830v5#S4.SS2); [ESA dSGP4 implementation](https://github.com/esa/dSGP4).
- Vallado, D. A., Crawford, P., Hujsak, R. and Kelso, T. S. (2006). [Vallado et al., Revisiting Spacetrack Report #3 (AIAA 2006-6753)](https://celestrak.org/publications/AIAA/2006-6753/). Reference implementation and verification cases.
- US Space Force. [Space-Track documentation and data terms](https://www.space-track.org/documentation). CelesTrak. [General perturbations data formats and distribution](https://celestrak.org/NORAD/documentation/gp-data-formats.php).
- ESA and TU Delft. [Swarm dissemination service](https://swarm-diss.eo.esa.int/). Reconstructed orbit and spacecraft-dynamics products.
- JPL and GFZ. [GRACE-FO orbit and thruster products](https://isdc-data.gfz.de/grace-fo/Level-1B/JPL/INSTRUMENT/RL04/). GNSS-derived reference states and firing records.
- CNES/SSALTO, IDS and IGN. [IDS data and products](https://ids-doris.org/data-products/section-content-dataproducts.html) and [reported system events](https://ids-doris.org/user-corner/table-of-all-events.html). Precise orbit products and published manoeuvre intervals.
- Copernicus and ESA. [SentiWiki altimetry processing and manoeuvre histories](https://sentiwiki.copernicus.eu/web/altimetry-processing) and [STEP precise-orbit archive](https://step.esa.int/auxdata/orbits/Sentinel-1/POEORB/S1A/).
- ILRS and EUROLAS Data Center. [Laser-ranging normal-point archive](https://edc.dgfi.tum.de/pub/slr/data/npt_crd_v2/) and [station coordinates and eccentricities](https://ilrs.gsfc.nasa.gov/network/site_information/index.html).
- de Villiers, M. S. (2023). [MeerKAT Holography Measurements in the UHF, L, and S bands](https://arxiv.org/abs/2301.06752). [Measured primary-beam data release](https://doi.org/10.48479/wdb0-h061) and [beam-orientation convention](https://archive-gw-1.kat.ac.za/public/repository/10.48479/wdb0-h061/beam_orientation_diagram.pdf).
- SARAO. [Public MeerKAT specifications](https://skaafrica.atlassian.net/wiki/spaces/ESDKB/pages/277315585/MeerKAT+specifications). Receiver bands and site parameters.
- Bright, J. and collaborators. [GCN circular 36362](https://gcn.nasa.gov/circulars/36362). The public MeerKAT observation record; [counterpart-position circular](https://gcn.nasa.gov/circulars/36105).
- SpaceX. [Satellite-operator information and published ephemerides](https://www.starlink.com/satellite-operators). ESA. [Kelvins collision-avoidance challenge](https://kelvins.esa.int/collision-avoidance-challenge/). Reference inputs for the wider repository's independent checks.
- CelesTrak. [Space-weather data](https://celestrak.org/SpaceData/). NOAA SWPC. [Public space-weather services](https://services.swpc.noaa.gov/). US Naval Research Laboratory. [NRLMSIS model](https://map.nrl.navy.mil/map/pub/nrl/NRLMSIS/NRLMSIS2.0/). Inputs and model used by the separately reported storm analysis.
