# Claims, populations and qualifications

These statements distinguish measured results, model assumptions and absent evidence.
Negative findings and withdrawn interpretations remain part of the evidence.

| Claim needing a population or caveat | Bounded statement |
| --- | --- |
| Five/two/one-day operating horizon | Last sampled leads before the 95th-percentile along-track error exceeds 25 km for Swarm A/B/C in the stated quiet, May and October windows. No interpolated crossing or validated horizon for another spacecraft. |
| Three spacecraft near 460 km; one storm per window | Swarm spans approximately 460 and 506 km. October includes two disturbed intervals. Three related spacecraft are not three independent orbit classes. |
| A storm correction always hurts inside three days | May worsens at 12–72 hours; October improves at 6–120 hours; quiet worsens at 1–6 days. Universal short-lead conclusions were too broad. |
| 0.20 km residual describes the operator prediction over 72 hours | Nineteen matched files reached 82.9 km median disagreement at 60–72 hours. Seventeen pairs have qualified lineage. These are differences from predictions, not realised-orbit errors or constellation-wide estimates. |
| All positions come from public element sets | Published operator states, reconstructed references and supplied orbit products are also inputs. The software performs no independent orbit determination. |
| Independent truth establishes exact position | ESA reduced-dynamic orbits are an independent reconstructed reference with their own errors. The earlier GPS/UTC error created about 137 km of along-track offset. |
| Robust flags mean accurate or actionable warnings | Robust labels the covariance region. Every probability remains indicative; neither a small dilution-region probability nor no flag establishes safety. Region and confidence precede colour. |
| 446 red events describe independent urgent encounters | In the 7 September quiet run, 445/446 red events are in dilution at low confidence. Across red and yellow, 594/597 flagged events (99.5%) are in dilution. Repeated events collapse to 14 flagged pairs: 12/14 (85.7%) in dilution and two robust. Counts require population, window and scenario. |
| Offline means recorded-input replay | Offline cache reuse does not identify historical inputs. Explicit `screen --offline --replay` uses recorded supplemental parquet, configuration, objects and covariance. Missing inputs fail. Quiet element-set-only replay does not prove served-state or storm replay. |
| Attached-filter counts imply machine-dependent screening | Rounded station copies create minima; identical copies can have none. Identical 5 September inputs reproduce ten excluded pairs and 444 dropped candidates. |
| Swarm A and ISS share 0.544/32.845 km medians at 1,440 samples | Those figures apply only to Swarm A on 13 May 2024. ISS has three predicted passes on 11 May, acquisition deltas of 1.06–1.33 seconds and nine plotted first-pass samples. There is no independent ISS reference or receiver log. The duplicate attribution was a reporting slip. |
| Quiet consistency is an accuracy bound | Successive fits share observations and assumptions. The Swarm comparison over-covers at 1–5 days in quiet and under-covers in storms. Agreement bounds accuracy in neither direction. |
| Kelvins validates the screener | It checks probability arithmetic on provided geometry and covariance. It does not measure catalogue completeness, warning recall, local covariance calibration or operational utility. |
| No stated licence permits unrestricted republication | Public access grants no redistribution right. Operator ephemerides and raw Kelvins data remain analysis-only under the project's publication policy. Provider terms govern third-party data. |
| Browser checks or synthetic examples establish usability | Synthetic fixtures test specified behaviour. No real CDM pair, request week or receiver log establishes operational performance. Second-PC installation, real-handset and assistive-technology evaluation remain incomplete. |
| A local network guard proves isolation | It disables supported clients during analysis. It does not secure a compromised PC, extensions or modified code and is not an operating-system sandbox. |
| Schedule priority gain means revenue or reliability gain | Priorities are supplied preference points. Optimisation assumes visibility and feasibility, one antenna and fixed turnaround. No real request week or accepted operational baseline has been measured. |
| Named prospects imply participation or willingness to pay | Workflows are described by engineering role. No organisation has adopted the tool or agreed to be identified as a prospect; no willingness-to-pay result is claimed. |
| The radio horizon is seven days | Two horizons, not one. The crossing horizon, governed by the cross-track error, holds for the benchmark's full seven days in every window at every MeerKAT receiver for three Swarm-class satellites at zenith range, and answers only whether an object crossed the beam; the position horizon, governed by the along-track error, answers where an object is at an instant and is 24, 12 and 6 hours at the L-band centre in the quiet, May and October windows and under six hours at the top of S band in every window. Neither is measured for any other orbit class or for a station-kept object. |
| Beam-crossing lists quantify interference | Product two is geometry from public element sets: closest approach, time, element-set age, the benchmark's angular uncertainty and the two horizon labels. No received power, occupancy fraction or sensitivity loss is computed anywhere in the radio lane. |
| Constellation counts are counts of transmitters | Membership is by catalogue name and orbit and includes retired satellites; the catalogue carries no transmit status. Emissions are declarations from filings, some made after the observations, not measurements; the direct-to-cell L-band range is recorded as declared and subject to each administration, and no licence in South Africa is asserted or predicted. |
| The retrospective covers the archive | One public observation record was found (GCN 36362, 23 April 2024, S-band) and none for 10 to 12 May 2024; the SARAO archive search needs an account and was not queried. The storm-week report carries only the product that needs no pointing. |

## Withdrawn claims retained as corrections

The attached-hardware probability headline, operator-controlled mean displacement,
common-mode-cancellation explanation, unbounded covariance fit, pooled correlation and
overbroad short-lead claim remain in [findings.md](findings.md), [storm-term.md](storm-term.md),
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
