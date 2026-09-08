# Corrected measured-beam comparison

These are descriptive results from constructed fixed celestial pointings at MeerKAT. They do not validate an observing schedule, satellite detections or a transferable crossing horizon. April 2024 control, May 2024, August 2024 held out and October 2024 held out were all inspected during correction; the inherited held-out labels are historical metadata.

## Population and fixed design

The corrected reference CSV contains 10,310 manoeuvre-excluded rows. Only 112 (1.09%) have nominal elevation 15–85° at the target time and complete finite reference/predicted curves for ±180 s. There are 9,829 nominal-below-horizon exclusions and 369 further rows below 15°. No other exclusion reason occurred. Truth-visible objects whose nominal prediction fails this gate are outside the comparison.

The eligible population comprises 94 element-set/window combinations from 12 missions: gracefo-c, gracefo-d, hy-2c, hy-2d, jason-3, saral, sentinel-1a, sentinel-3a, sentinel-3b, sentinel-6a, swarm-a, swarm-b. It contains no eligible CryoSat-2, SWOT or Swarm-C case. Each trial supplies six measured beam channels, nine fixed pointing offsets and three observation intervals, giving 18,144 cases. The many cases sharing an orbit curve are dependent; counts and sample quantiles below are not independent-trial confidence bounds.

The offsets are 0, ±0.95, ±1, ±1.05 and ±1.5 times the first measured half-power boundary along each signed normal to the nominal central track. Thus the design explicitly includes nominal entrants, boundary pointings and exterior near misses. The boresight is fixed in ICRS, and the full-vector topocentric prediction and reference retain observer rotation. The measured mount-frame pattern rotates relative to the celestial pointing. All six channels use peak-normalised unpolarised Stokes I derived from the Jones planes. See the [method and source limits](../radio-lane.md).

## Full ±180 s interval

A false crossing means a predicted half-power entry without a reference entry; a missed crossing means the reverse. Their rate denominators are predicted and reference crossings respectively. Both and neither complete the four-way classification.

| Pointing stratum | Cases | False / predicted crossings | Missed / reference crossings | Both | Neither |
| --- | ---: | ---: | ---: | ---: | ---: |
| All nine offsets | 6,048 | 687 / 3,358 (20.46%) | 53 / 2,724 (1.95%) | 2,671 | 2,637 |
| Seven offsets excluding exactly ±1 | 4,704 | 45 / 2,016 (2.23%) | 51 / 2,022 (2.52%) | 1,971 | 2,637 |
| Exactly ±1 only | 1,344 | 642 / 1,342 (47.84%) | 2 / 702 (0.28%) | 700 | 0 |

The seven-offset row is a prespecified design stratum, not a removal based on observed error. The exact-boundary pointings are retained in the primary all-offset result. Small normal shifts can change classification at a boundary; the pattern peak can also move along a curved track. Only 3 nominal peaks and 0 reference peaks have an absolute peak-minus-half-power margin at most 1e-8. Consequently the much larger boundary-stratum disagreement cannot all be described as numerical roundoff. Frozen classifications and raw margins are preserved.

The seven-offset sensitivity resolves the dependence on measured channel. Each row has 784 cases from the same 112 trials; pooling these rows does not create more independent spacecraft.

| Actual measured frequency (MHz) | False / predicted crossings | Missed / reference crossings | Both | Entry absolute error p95 (s) | Exit absolute error p95 (s) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 816.000000 | 3 / 336 (0.89%) | 3 / 336 (0.89%) | 333 | 1.073 | 1.050 |
| 1284.000000 | 5 / 336 (1.49%) | 5 / 336 (1.49%) | 331 | 1.059 | 1.040 |
| 1711.164062 | 5 / 336 (1.49%) | 8 / 339 (2.36%) | 331 | 1.091 | 1.032 |
| 2187.500000 | 8 / 336 (2.38%) | 8 / 336 (2.38%) | 328 | 1.052 | 1.039 |
| 3062.500000 | 11 / 336 (3.27%) | 12 / 337 (3.56%) | 325 | 1.034 | 1.013 |
| 3499.145508 | 13 / 336 (3.87%) | 15 / 338 (4.44%) | 323 | 1.043 | 1.031 |

Entry and exit timing in this table use only the paired **both-crossed** cases named in that row, with one uncensored full-span interval on each curve. They exclude false and missed crossings by definition and are not an unconditional timing guarantee. Quantiles use linear interpolation.

## Timing, angular error and observation boundaries

| Full-interval timing stratum | Paired closest times | Closest absolute error p95 (s) | Paired entries/exits | Entry absolute error p95 (s) | Exit absolute error p95 (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| All offsets | 6,048 | 1.392 | 2,671 | 1.103 | 1.192 |
| Excluding exactly ±1 | 4,704 | 1.392 | 1,971 | 1.053 | 1.049 |

Across all offsets, the largest absolute closest-time residual is 12.553 s; paired entry and exit maxima are 12.682 and 13.984 s. No closest approach, response peak or entry/exit was censored by the ±180 s search span. That observation does not establish completeness outside the span.

The full instantaneous line-of-sight separation at each reference closest time has sample p95 21.885 arcmin and maximum 210.967 arcmin (n=6,048). The per-case maximum over the sampled ±180 s curve has p95 46.882 arcmin. These are full angular separations, distinct from the earlier orbital-C/mean-altitude diagnostic. They do not establish range-rate, Doppler, coherence or received power accuracy.

Fixed half-intervals show what changes when a real observation has a start or end near the passage. An edge mismatch is a false/missed observation crossing for which both curves have a full-span entry; it isolates the effect of clipping the interval.

| Observation interval (s) | Cases | False | Missed | Both | Neither | Edge mismatches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| −180 to 0 | 6,048 | 567 | 257 | 2,152 | 3,072 | 449 |
| 0 to +180 | 6,048 | 429 | 397 | 2,226 | 2,996 | 411 |

The input cadence is 1 s, with interpolation and refined half-power roots (1 ms root tolerance). Focused synthetic tests include grazing contacts and a finer-cadence comparison. There was no finer-cadence rerun of these empirical cases, so root tolerance alone must not be read as millisecond physical accuracy. The beam product represents the published array average at 60° elevation and 15°C; applying it across the selected elevations is an instrument-model approximation.

## Artefacts and separate scalar sensitivity

The pre-run [protocol](../../data/radio/track_benchmark_v2_complete/radio_track_protocol.json), [grouped summary](../../data/radio/track_benchmark_v2_complete/radio_track_summary.json), [diagnostics](../../data/radio/track_benchmark_v2_complete/radio_track_diagnostics.json), [case rows](../../data/radio/track_benchmark_v2_complete/radio_track_cases.csv) and [eligibility rows](../../data/radio/track_benchmark_v2_complete/radio_track_eligibility.csv) retain the population, pointing rule, source hashes, conditional timing counts and exclusions. One execution stopped on a progress-file write error after 6,598 targets; a disjoint continuation processed the remaining 3,712 targets. The composed protocol identifies both unchanged fragments. Independent checks reproduced every grouped classification count and verified all 112 raw curve hashes; no completed case was discarded.

The [component diagnostic](../radio-horizon.md) remains a separate calculation. Its above-3-GHz primary widths are measured narrowest diametric half-power cuts: 33.446725 arcmin at 3062.5 MHz and 26.421109 arcmin at 3499.1455078125 MHz. The JSON includes the widest-cut sensitivity and half-FWHM component criterion across all bands. The historical analytic 3500 MHz result is labelled separately. Neither scalar convention supplies a crossing probability.
