# dSGP4 and ML-dSGP4 on the benchmark's trials

Acciarini, G., Baydin, A. G., Izzo, D. (2025), Closing the gap between SGP4 and high-precision propagation via differentiable programming, Acta Astronautica 226, 694-701; software github.com/esa/dSGP4. dsgp4 1.3.0, torch 2.14.0+cpu.

The published hybrid was trained on an operator's predictions in a quiet week: SpaceX's published Starlink ephemerides, the operator's own propagation, over about a week without a storm. The storm result here is new.

**What was done.** 1228 trial sets from 15 mission(s) over 4 windows; the hybrids trained on the 639 sets of the quiet and May windows only, with the reconstructed orbit sampled hourly to seven days, corrections starting at zero, hidden size 35; scored at the benchmark's leads in the truth's radial, in-track, cross-track frame against plain SGP4, dsgp4 with both gravity constants, and the storm term with the observed ap.

**Training.** ML-dSGP4 (Swarm): 18648 samples from 111 sets, 40 epochs of 4096 at learning rate 0.001, loss 6.80e-06 at the zero start, 7.24e-06 after the first epoch, 6.66e-06 at the best, 22 s; ML-dSGP4 (all missions): 107352 samples from 639 sets, 40 epochs of 4096 at learning rate 0.001, loss 1.81e-06 at the zero start, 2.10e-06 after the first epoch, 1.61e-06 at the best, 141 s.

## The in-track residual by window and lead, per method

Median absolute in-track residual, km, against the reconstructed orbit, on the same sets for every method; n is the number of trials. Quiet and May are the hybrids' training windows; October and August are held out.

### august (held out)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 297 | 0.50 | 0.50 | 0.50 | 11.50 | 2.87 | 0.50 |
| 12 h | 293 | 0.40 | 0.40 | 0.42 | 11.06 | 2.38 | 0.42 |
| 24 h | 285 | 0.45 | 0.45 | 0.47 | 12.78 | 2.96 | 0.52 |
| 36 h | 276 | 0.60 | 0.60 | 0.61 | 16.32 | 3.32 | 0.59 |
| 2 d | 266 | 0.73 | 0.73 | 0.79 | 18.13 | 4.40 | 0.83 |
| 3 d | 248 | 1.49 | 1.49 | 1.51 | 23.46 | 8.29 | 1.95 |
| 4 d | 230 | 2.01 | 2.01 | 2.04 | 35.53 | 11.32 | 3.01 |
| 5 d | 211 | 3.06 | 3.06 | 3.22 | 39.60 | 13.46 | 4.75 |
| 6 d | 196 | 4.02 | 4.02 | 4.03 | 45.29 | 16.69 | 6.36 |
| 7 d | 185 | 5.88 | 5.88 | 5.79 | 46.90 | 20.88 | 21.31 |

### held-out (held out)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 292 | 0.58 | 0.58 | 0.57 | 12.78 | 6.93 | 0.55 |
| 12 h | 287 | 0.53 | 0.53 | 0.54 | 12.22 | 6.34 | 0.53 |
| 24 h | 284 | 0.65 | 0.65 | 0.67 | 14.89 | 6.32 | 0.61 |
| 36 h | 275 | 0.93 | 0.93 | 0.92 | 16.31 | 7.47 | 0.88 |
| 2 d | 267 | 1.34 | 1.34 | 1.34 | 23.54 | 7.03 | 0.93 |
| 3 d | 253 | 2.59 | 2.59 | 2.63 | 35.17 | 8.48 | 2.01 |
| 4 d | 235 | 3.93 | 3.93 | 3.87 | 50.06 | 11.23 | 6.00 |
| 5 d | 222 | 5.08 | 5.08 | 5.04 | 81.94 | 11.85 | 7.16 |
| 6 d | 209 | 6.59 | 6.59 | 6.66 | 83.63 | 13.60 | 8.15 |
| 7 d | 195 | 11.09 | 11.09 | 11.05 | 87.22 | 17.82 | 10.75 |

### quiet (training)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 318 | 0.46 | 0.46 | 0.47 | 6.87 | 2.28 | 0.46 |
| 12 h | 315 | 0.42 | 0.42 | 0.43 | 7.60 | 2.29 | 0.41 |
| 24 h | 311 | 0.43 | 0.43 | 0.42 | 7.57 | 1.72 | 0.45 |
| 36 h | 305 | 0.56 | 0.56 | 0.56 | 7.78 | 1.56 | 0.63 |
| 2 d | 303 | 0.58 | 0.58 | 0.58 | 8.34 | 1.64 | 0.67 |
| 3 d | 293 | 0.72 | 0.72 | 0.74 | 10.34 | 1.45 | 0.89 |
| 4 d | 284 | 1.07 | 1.07 | 1.06 | 14.23 | 1.35 | 1.13 |
| 5 d | 281 | 1.15 | 1.15 | 1.18 | 22.73 | 1.36 | 1.51 |
| 6 d | 280 | 1.34 | 1.34 | 1.41 | 34.97 | 2.01 | 1.78 |
| 7 d | 280 | 2.20 | 2.20 | 2.15 | 45.84 | 2.68 | 1.85 |

### storm (training)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 321 | 0.48 | 0.48 | 0.47 | 12.47 | 2.26 | 0.48 |
| 12 h | 318 | 0.44 | 0.44 | 0.44 | 12.87 | 2.38 | 0.45 |
| 24 h | 313 | 0.51 | 0.51 | 0.53 | 13.83 | 2.07 | 0.61 |
| 36 h | 310 | 0.61 | 0.61 | 0.58 | 15.10 | 2.46 | 0.69 |
| 2 d | 307 | 0.73 | 0.73 | 0.70 | 15.10 | 2.25 | 0.80 |
| 3 d | 292 | 1.49 | 1.49 | 1.50 | 16.89 | 2.60 | 1.76 |
| 4 d | 275 | 3.12 | 3.12 | 3.17 | 22.03 | 3.40 | 2.78 |
| 5 d | 257 | 4.35 | 4.35 | 4.31 | 26.27 | 4.62 | 5.37 |
| 6 d | 237 | 6.24 | 6.24 | 6.23 | 30.72 | 5.58 | 6.28 |
| 7 d | 218 | 6.94 | 6.94 | 7.06 | 44.00 | 6.33 | 7.47 |

## Change against plain SGP4

Each method's change to the median absolute in-track residual, relative to the sgp4 library; positive is better.

| Window | Lead | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| august | 6 h | -0% | -0% | -2211% | -476% | -1% |
| august | 12 h | -0% | -4% | -2638% | -490% | -3% |
| august | 24 h | +0% | -5% | -2735% | -556% | -15% |
| august | 36 h | -0% | -1% | -2613% | -452% | +2% |
| august | 2 d | -0% | -9% | -2400% | -507% | -14% |
| august | 3 d | +0% | -2% | -1478% | -458% | -31% |
| august | 4 d | -0% | -2% | -1664% | -462% | -49% |
| august | 5 d | +0% | -5% | -1195% | -340% | -55% |
| august | 6 d | +0% | -0% | -1027% | -316% | -58% |
| august | 7 d | -0% | +1% | -698% | -255% | -263% |
| held-out | 6 h | -0% | +2% | -2100% | -1093% | +5% |
| held-out | 12 h | -0% | -2% | -2212% | -1099% | +0% |
| held-out | 24 h | -0% | -5% | -2207% | -880% | +5% |
| held-out | 36 h | +0% | +1% | -1651% | -703% | +6% |
| held-out | 2 d | +0% | +0% | -1657% | -425% | +31% |
| held-out | 3 d | +0% | -2% | -1257% | -227% | +23% |
| held-out | 4 d | +0% | +2% | -1173% | -186% | -53% |
| held-out | 5 d | +0% | +1% | -1513% | -133% | -41% |
| held-out | 6 d | -0% | -1% | -1169% | -106% | -24% |
| held-out | 7 d | -0% | +0% | -687% | -61% | +3% |
| quiet | 6 h | -0% | -2% | -1395% | -397% | +1% |
| quiet | 12 h | -0% | -2% | -1714% | -447% | +2% |
| quiet | 24 h | +0% | +2% | -1678% | -304% | -7% |
| quiet | 36 h | +0% | -0% | -1294% | -180% | -13% |
| quiet | 2 d | -0% | -1% | -1338% | -182% | -16% |
| quiet | 3 d | -0% | -3% | -1331% | -100% | -24% |
| quiet | 4 d | +0% | +1% | -1232% | -26% | -6% |
| quiet | 5 d | +0% | -3% | -1881% | -18% | -32% |
| quiet | 6 d | -0% | -6% | -2515% | -50% | -33% |
| quiet | 7 d | +0% | +2% | -1987% | -22% | +16% |
| storm | 6 h | -0% | +2% | -2513% | -374% | -1% |
| storm | 12 h | +0% | +2% | -2793% | -434% | -1% |
| storm | 24 h | -0% | -3% | -2605% | -305% | -19% |
| storm | 36 h | +0% | +5% | -2388% | -306% | -14% |
| storm | 2 d | -0% | +4% | -1963% | -207% | -10% |
| storm | 3 d | +0% | -1% | -1035% | -75% | -18% |
| storm | 4 d | +0% | -2% | -606% | -9% | +11% |
| storm | 5 d | +0% | +1% | -503% | -6% | -23% |
| storm | 6 d | +0% | +0% | -392% | +11% | -1% |
| storm | 7 d | +0% | -2% | -534% | +9% | -8% |

## The recommendation

- **ML-dSGP4 (Swarm)**: do not adopt (adopt only if the held-out storms improve). Held out: held-out: 0 of 10 leads improved, median change -1582%, worst -2212%; august: 0 of 10 leads improved, median change -1937%, worst -2735%.
- **ML-dSGP4 (all missions)**: do not adopt (adopt only if the held-out storms improve). Held out: held-out: 0 of 10 leads improved, median change -326%, worst -1099%; august: 0 of 10 leads improved, median change -460%, worst -556%.

## What this does not show

- The hybrids are trained on one week of quiet sets and one storm week, on the missions listed, with one architecture and one training recipe; a different recipe could do better or worse, and none is tuned on the held-out windows.
- The dsgp4 baseline with WGS72 constants is the check that the two implementations agree; the hybrid uses the library's WGS-84 constants inside, as published, and the WGS-84 baseline shows that difference alone.
- A method that lowers the median can raise the tail; the 95th percentiles are in the JSON beside this page.

_Last updated 07 September 2026._
