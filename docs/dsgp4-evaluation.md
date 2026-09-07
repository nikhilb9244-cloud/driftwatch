# dSGP4 and ML-dSGP4 on the benchmark's trials

Acciarini, G., Baydin, A. G., Izzo, D. (2025), Closing the gap between SGP4 and high-precision propagation via differentiable programming, Acta Astronautica 226, 694-701; software github.com/esa/dSGP4. dsgp4 1.3.0, torch 2.14.0+cpu.

The published hybrid was trained on an operator's predictions in a quiet week: SpaceX's published Starlink ephemerides, the operator's own propagation, over about a week without a storm. The storm result here is new.

**What was done.** 1201 trial sets from 15 mission(s) over 4 windows; the hybrids trained on the 625 sets of the quiet and May windows only, with the reconstructed orbit sampled hourly to seven days, corrections starting at zero, hidden size 35; scored at the benchmark's leads in the truth's radial, in-track, cross-track frame against plain SGP4, dsgp4 with both gravity constants, and the storm term with the observed ap.

**Training.** ML-dSGP4 (Swarm): 18648 samples from 111 sets, 40 epochs of 4096 at learning rate 0.001, loss 6.80e-06 at the zero start, 7.24e-06 after the first epoch, 6.66e-06 at the best, 23 s; ML-dSGP4 (all missions): 105000 samples from 625 sets, 40 epochs of 4096 at learning rate 0.001, loss 1.84e-06 at the zero start, 2.05e-06 after the first epoch, 1.63e-06 at the best, 138 s.

## The in-track residual by window and lead, per method

Median absolute in-track residual, km, against the reconstructed orbit, on the same sets for every method; n is the number of trials. Quiet and May are the hybrids' training windows; October and August are held out.

### august (held out)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 292 | 0.50 | 0.50 | 0.50 | 11.59 | 7.14 | 0.50 |
| 12 h | 288 | 0.40 | 0.40 | 0.42 | 11.52 | 6.94 | 0.41 |
| 24 h | 280 | 0.45 | 0.45 | 0.47 | 14.16 | 6.99 | 0.52 |
| 36 h | 271 | 0.60 | 0.60 | 0.61 | 18.00 | 7.90 | 0.58 |
| 2 d | 261 | 0.72 | 0.72 | 0.78 | 19.62 | 8.39 | 0.82 |
| 3 d | 243 | 1.45 | 1.45 | 1.46 | 24.07 | 10.59 | 1.74 |
| 4 d | 225 | 2.00 | 2.00 | 2.03 | 36.30 | 15.28 | 2.98 |
| 5 d | 206 | 3.04 | 3.04 | 3.06 | 43.06 | 19.58 | 4.37 |
| 6 d | 192 | 3.83 | 3.83 | 3.80 | 45.41 | 22.90 | 5.83 |
| 7 d | 185 | 5.88 | 5.88 | 5.79 | 46.90 | 22.41 | 21.31 |

### held-out (held out)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 284 | 0.58 | 0.58 | 0.57 | 13.94 | 5.21 | 0.55 |
| 12 h | 279 | 0.54 | 0.54 | 0.54 | 13.02 | 4.56 | 0.53 |
| 24 h | 276 | 0.64 | 0.64 | 0.67 | 15.19 | 4.71 | 0.61 |
| 36 h | 267 | 0.93 | 0.93 | 0.92 | 16.61 | 6.11 | 0.88 |
| 2 d | 259 | 1.34 | 1.34 | 1.34 | 25.89 | 7.07 | 0.93 |
| 3 d | 245 | 2.68 | 2.68 | 2.66 | 38.19 | 8.98 | 2.05 |
| 4 d | 227 | 4.04 | 4.04 | 3.97 | 66.44 | 11.52 | 6.40 |
| 5 d | 214 | 5.18 | 5.18 | 5.07 | 82.50 | 13.01 | 7.26 |
| 6 d | 201 | 6.72 | 6.72 | 6.79 | 85.30 | 13.98 | 8.84 |
| 7 d | 187 | 11.20 | 11.20 | 11.06 | 91.78 | 15.69 | 11.27 |

### quiet (training)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 312 | 0.46 | 0.46 | 0.46 | 6.97 | 2.48 | 0.45 |
| 12 h | 309 | 0.42 | 0.42 | 0.43 | 7.60 | 2.58 | 0.41 |
| 24 h | 305 | 0.42 | 0.42 | 0.42 | 7.57 | 2.12 | 0.45 |
| 36 h | 299 | 0.56 | 0.56 | 0.56 | 7.55 | 2.02 | 0.63 |
| 2 d | 297 | 0.58 | 0.58 | 0.58 | 8.34 | 1.83 | 0.67 |
| 3 d | 287 | 0.71 | 0.71 | 0.73 | 10.34 | 1.59 | 0.87 |
| 4 d | 278 | 1.06 | 1.06 | 1.03 | 16.56 | 1.51 | 1.13 |
| 5 d | 275 | 1.15 | 1.15 | 1.14 | 23.51 | 1.64 | 1.50 |
| 6 d | 274 | 1.22 | 1.22 | 1.30 | 37.64 | 2.08 | 1.74 |
| 7 d | 274 | 2.04 | 2.04 | 2.13 | 45.98 | 2.91 | 1.84 |

### storm (training)

| Lead | n | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 313 | 0.48 | 0.48 | 0.47 | 12.53 | 2.36 | 0.48 |
| 12 h | 310 | 0.44 | 0.44 | 0.44 | 13.06 | 2.56 | 0.45 |
| 24 h | 305 | 0.51 | 0.51 | 0.52 | 14.03 | 2.10 | 0.60 |
| 36 h | 302 | 0.61 | 0.61 | 0.58 | 15.39 | 2.42 | 0.69 |
| 2 d | 299 | 0.75 | 0.75 | 0.74 | 15.59 | 2.03 | 0.84 |
| 3 d | 284 | 1.52 | 1.52 | 1.52 | 17.07 | 2.82 | 1.77 |
| 4 d | 267 | 3.25 | 3.25 | 3.24 | 23.30 | 3.56 | 3.14 |
| 5 d | 249 | 4.52 | 4.52 | 4.68 | 27.77 | 4.98 | 5.57 |
| 6 d | 231 | 6.43 | 6.43 | 6.50 | 30.72 | 5.79 | 6.49 |
| 7 d | 215 | 7.08 | 7.08 | 7.25 | 41.66 | 6.94 | 7.72 |

## Change against plain SGP4

Each method's change to the median absolute in-track residual, relative to the sgp4 library; positive is better.

| Window | Lead | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| august | 6 h | -0% | -0% | -2222% | -1331% | -1% |
| august | 12 h | +0% | -4% | -2758% | -1621% | -3% |
| august | 24 h | +0% | -4% | -3041% | -1452% | -15% |
| august | 36 h | -0% | -2% | -2905% | -1219% | +2% |
| august | 2 d | -0% | -8% | -2611% | -1059% | -14% |
| august | 3 d | -0% | -1% | -1565% | -632% | -21% |
| august | 4 d | -0% | -1% | -1711% | -662% | -49% |
| august | 5 d | +0% | -1% | -1317% | -544% | -44% |
| august | 6 d | +0% | +1% | -1087% | -498% | -52% |
| august | 7 d | -0% | +1% | -698% | -281% | -263% |
| held-out | 6 h | -0% | +2% | -2299% | -797% | +5% |
| held-out | 12 h | +0% | -1% | -2329% | -751% | +1% |
| held-out | 24 h | -0% | -4% | -2260% | -632% | +5% |
| held-out | 36 h | -0% | +1% | -1677% | -554% | +6% |
| held-out | 2 d | +0% | +0% | -1825% | -425% | +31% |
| held-out | 3 d | +0% | +1% | -1322% | -235% | +24% |
| held-out | 4 d | +0% | +2% | -1546% | -185% | -59% |
| held-out | 5 d | +0% | +2% | -1494% | -151% | -40% |
| held-out | 6 d | -0% | -1% | -1169% | -108% | -31% |
| held-out | 7 d | +0% | +1% | -720% | -40% | -1% |
| quiet | 6 h | -0% | -0% | -1419% | -442% | +2% |
| quiet | 12 h | -0% | -3% | -1721% | -519% | +3% |
| quiet | 24 h | +0% | +0% | -1707% | -407% | -8% |
| quiet | 36 h | +0% | +0% | -1255% | -262% | -13% |
| quiet | 2 d | +0% | +0% | -1341% | -216% | -15% |
| quiet | 3 d | -0% | -3% | -1360% | -125% | -23% |
| quiet | 4 d | +0% | +3% | -1461% | -43% | -7% |
| quiet | 5 d | +0% | +0% | -1951% | -43% | -31% |
| quiet | 6 d | -0% | -7% | -2984% | -71% | -43% |
| quiet | 7 d | +0% | -4% | -2150% | -42% | +10% |
| storm | 6 h | +0% | +2% | -2497% | -389% | -0% |
| storm | 12 h | +0% | +2% | -2835% | -476% | -1% |
| storm | 24 h | +0% | -3% | -2661% | -313% | -18% |
| storm | 36 h | +0% | +5% | -2435% | -299% | -14% |
| storm | 2 d | +0% | +1% | -1982% | -171% | -12% |
| storm | 3 d | +0% | +0% | -1021% | -85% | -16% |
| storm | 4 d | +0% | +0% | -617% | -9% | +3% |
| storm | 5 d | +0% | -4% | -515% | -10% | -23% |
| storm | 6 d | -0% | -1% | -378% | +10% | -1% |
| storm | 7 d | +0% | -2% | -489% | +2% | -9% |

## The recommendation

- **ML-dSGP4 (Swarm)**: do not adopt (adopt only if the held-out storms improve). Held out: held-out: 0 of 10 leads improved, median change -1612%, worst -2329%; august: 0 of 10 leads improved, median change -1967%, worst -3041%.
- **ML-dSGP4 (all missions)**: do not adopt (adopt only if the held-out storms improve). Held out: held-out: 0 of 10 leads improved, median change -330%, worst -797%; august: 0 of 10 leads improved, median change -860%, worst -1621%.

## What this does not show

- The hybrids are trained on one week of quiet sets and one storm week, on the missions listed, with one architecture and one training recipe; a different recipe could do better or worse, and none is tuned on the held-out windows.
- The dsgp4 baseline with WGS72 constants is the check that the two implementations agree; the hybrid uses the library's WGS-84 constants inside, as published, and the WGS-84 baseline shows that difference alone.
- A method that lowers the median can raise the tail; the 95th percentiles are in the JSON beside this page.

_Last updated 07 September 2026._
