# Claims, populations and qualifications

Current benchmark claims are bound by the [claims manifest](assets/claims-v2.json); the [dated covariance correction](covariance-basis-correction.md) records every affected and unchanged coverage cell. The statements below distinguish measured results, model assumptions and absent evidence.
Negative findings and withdrawn interpretations remain part of the evidence.

| Claim needing a population or caveat | Bounded statement |
| --- | --- |
| Operating horizon | The corrected reference tables give the last passing and first failing lead, or explicitly identify censoring, with counts, spacecraft composition, empirical exceedance and deletion sensitivities. No validated horizon transfers to another orbit class. See [v2](paper.md). |
| Three spacecraft near 460 km; one storm per window | Swarm spans approximately 460 and 506 km. October includes two disturbed intervals. The expansion has fifteen spacecraft with a reconstructed orbit in five bands from 460 to 1,338 km and three with laser ranging only. October and August 2024 carried historical held-out labels, but all four windows were inspected during this correction; they are not untouched v2 evaluation data. Related spacecraft in one orbit (Swarm A and C; Sentinel-3A and 3B; HY-2C and 2D; Jason-3 and Sentinel-6A) are not independent classes. |
| Laser ranging validates the reconstructed orbits | It bounds the disagreement between the two references at the metre level (median residual within 0.6 m for every mission but SWOT, whose constant 2 m is the uncorrected retroreflector offset); no centre-of-mass correction is applied, so nothing is validated at the centimetre level. |
| ML-dSGP4 improves prediction through a storm | The corrected eligible-target rerun is complete. Neither local checkpoint improves the pooled median at any of ten leads in October or August. Individual spacecraft are heterogeneous: the all-mission fit improves medians in 23/150 October and 43/142 August spacecraft/lead cells, often while worsening their p95. The result rejects these fitted checkpoints under the stated rule, not learned propagation generally; both evaluation windows were previously inspected. See [the corrected evaluation](dsgp4-evaluation.md) and its paired CSV. No external issue has been filed. |
| Every mission asked for is covered | Sentinel-2A and 2B, GOCE and CHAMP are not; ICESat-2, TerraSAR-X and TanDEM-X have laser ranging only, with three to thirteen sets in a storm window. The page names the account each missing product sits behind rather than substituting. |
| A storm correction always hurts inside three days | May worsens at 12–72 hours; October improves at 6–120 hours; quiet worsens at 1–6 days. Universal short-lead conclusions were too broad. |
| 0.20 km residual describes the operator prediction over 72 hours | Nineteen matched files reached 82.9 km median disagreement at 60–72 hours. Seventeen pairs have qualified lineage. These are differences from predictions, not realised-orbit errors or constellation-wide estimates. |
| All positions come from public element sets | Published operator states, reconstructed references and supplied orbit products are also inputs. The software performs no independent orbit determination. |
| Independent truth establishes exact position | ESA reduced-dynamic orbits are an independent reconstructed reference with their own errors. The earlier GPS/UTC error created about 137 km of along-track offset. |
| Robust flags mean accurate or actionable warnings | Robust labels the covariance region. Every probability remains indicative; neither a small dilution-region probability nor no flag establishes safety. Region and confidence precede colour. |
| 446 red events describe independent urgent encounters | In the 7 September quiet run, 445/446 red events are in dilution at low confidence. Across red and yellow, 594/597 flagged events (99.5%) are in dilution. Repeated events collapse to 14 flagged pairs: 12/14 (85.7%) in dilution and two robust. Counts require population, window and scenario. |
| Offline means recorded-input replay | Offline cache reuse does not identify historical inputs. Explicit `screen --offline --replay` uses recorded supplemental parquet, configuration, objects and covariance. Missing inputs fail. Quiet element-set-only replay does not prove served-state or storm replay. |
| Attached-filter counts imply machine-dependent screening | Rounded station copies create minima; identical copies can have none. Identical 5 September inputs reproduce ten excluded pairs and 444 dropped candidates. |
| Swarm A and ISS share 0.544/32.845 km medians at 1,440 samples | Those figures apply only to Swarm A on 13 May 2024. ISS has three predicted passes on 11 May, acquisition deltas of 1.06–1.33 seconds and nine plotted first-pass samples. There is no independent ISS reference or receiver log. The duplicate attribution was a reporting slip. |
| Quiet consistency is an accuracy bound | Component and spacecraft coverage differ. The benchmark measures reference residuals against consistency-derived intervals; it does not identify why catalogue fits agree with each other. See the generated calibration tables. |
| Kelvins validates the screener | It checks probability arithmetic on provided geometry and covariance. It does not measure catalogue completeness, warning recall, local covariance calibration or operational utility. |
| No stated licence permits unrestricted republication | Public access grants no redistribution right. Operator ephemerides and raw Kelvins data remain analysis-only under the project's publication policy. Provider terms govern third-party data. |
| Browser checks or synthetic examples establish usability | Synthetic fixtures test specified behaviour. No real CDM pair, request week or receiver log establishes operational performance. Second-PC installation, real-handset and assistive-technology evaluation remain incomplete. |
| A local network guard proves isolation | It disables supported clients during analysis. It does not secure a compromised PC, extensions or modified code and is not an operating-system sandbox. |
| Schedule priority gain means revenue or reliability gain | Priorities are supplied preference points. Optimisation assumes visibility and feasibility, one antenna and fixed turnaround. No real request week or accepted operational baseline has been measured. |
| Named prospects imply participation or willingness to pay | Workflows are described by engineering role. No organisation has adopted the tool or agreed to be identified as a prospect; no willingness-to-pay result is claimed. |
| The radio horizon is seven days | Withdrawn. The old quantity is an orbital cross-track angular-error threshold at an assumed range. It does not establish a beam crossing. The corrected topocentric comparison retains near misses, rotates the observer with Earth and minimises separation from a fixed celestial boresight. |
| Beam-crossing lists quantify interference | Geometric comparisons do not measure received power, occupancy or sensitivity loss. Reference-population uncertainty is optional and carries its version, count and applicability scope; excluded objects do not inherit measured labels. |
| Constellation counts are counts of transmitters | Membership is by catalogue name and orbit and includes retired satellites; the catalogue carries no transmit status. Emissions are declarations from filings, some made after the observations, not measurements; the direct-to-cell L-band range is recorded as declared and subject to each administration, and no licence in South Africa is asserted or predicted. |
| The retrospective covers the archive | One public observation record was found (GCN 36362, 23 April 2024, S-band) and none for 10 to 12 May 2024; the SARAO archive search needs an account and was not queried. The storm-week report carries only the product that needs no pointing. |

## Withdrawn claims retained as corrections

The attached-hardware probability headline, operator-controlled mean displacement,
common-mode-cancellation explanation, unbounded covariance fit, pooled correlation and
overbroad short-lead claim remain in the [archived findings](archive/findings-paper-2026-09-v1.md), [storm-term.md](storm-term.md),
[storm-validation.md](storm-validation.md) and [writeup-notes.md](writeup-notes.md).
Their correction does not validate the remaining model.

## Documentation boundary

Procedural verification, test counts, viewport checks, command transcripts, commit narration
and planning history are kept outside the repository.
Scientific dates identifying sample windows and source products remain with measurements.
Current pages carry one last-updated marker.

Commercial research and contact-pilot assessments are outside the repository; outreach
drafts remain in their existing private location. They are not sources for capability claims.
Data-provider and scientific-author citations remain because attribution is necessary;
they imply no adoption or endorsement.

_Last updated 7 September 2026._
