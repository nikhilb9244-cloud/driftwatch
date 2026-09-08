# dSGP4 and ML-dSGP4 on the benchmark's trials

Acciarini, G., Baydin, A. G., Izzo, D. (2025), Closing the gap between SGP4 and high-precision propagation via differentiable programming, Acta Astronautica 226, 694-701; software github.com/esa/dSGP4. dsgp4 1.3.0, torch 2.14.0+cpu.

The published experiment used SpaceX numerical predictions for 1,519 Starlink satellites over three days, 18-21 February 2023, at 60-second cadence. The paper does not classify this period as quiet. It used 30 epochs, learning rate 0.003, a TLE-level training/validation/test split and validation-selected models. This experiment is a local adaptation: 40 epochs, initial learning rate 0.001, a cosine schedule, zero initial corrections and selection by the complete fixed training objective on the stated reference-orbit benchmark. Source: https://arxiv.org/html/2402.04830v5#S4.SS2.

**What was done.** 1193 usable trial sets, trained on April 2024 control and May 2024 with the same authoritative burn intervals as evaluation, truth coverage and zero SGP4 error at each hourly target. A single frozen recipe was evaluated on pooled and spacecraft-specific paired residuals.

**Training.** ML-dSGP4 (Swarm): 18648 samples from 111 sets, 40 epochs of 4096 at learning rate 0.001, loss 6.80e-06 at the zero start, 6.92e-06 after the first epoch, 6.66e-06 at the retained model, 30 s; ML-dSGP4 (all missions): 89258 samples from 616 sets, 40 epochs of 4096 at learning rate 0.001, loss 1.75e-06 at the zero start, 1.77e-06 after the first epoch, 1.65e-06 at the retained model, 148 s.
Checkpoint selection uses the objective re-evaluated over the complete fixed training sample after each epoch. Changing-model minibatch losses are stored separately. Checkpoint hashes, reload checks and per-spacecraft paired comparison counts accompany the JSON/CSV artifacts.

## The in-track residual by window and lead, per method

Cells give median absolute in-track residual in km (number of trials). April 2024 control and May 2024 are training windows. October 2024 held out and August 2024 held out are excluded from optimizer training, but their earlier results have already been inspected. This corrected rerun is not a newly uninspected validation experiment. Method changes in the paired-comparison CSV use exactly shared set/lead rows.

### August 2024 held out (previously inspected evaluation)

| Lead | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 0.50 (292) | 0.50 (292) | 0.50 (292) | 11.59 (292) | 3.10 (292) | 0.59 (111) |
| 12 h | 0.40 (288) | 0.40 (288) | 0.42 (288) | 11.52 (288) | 2.74 (288) | 0.64 (111) |
| 24 h | 0.45 (280) | 0.45 (280) | 0.47 (280) | 14.16 (280) | 2.92 (280) | 0.81 (111) |
| 36 h | 0.60 (271) | 0.60 (271) | 0.61 (271) | 18.00 (271) | 2.44 (271) | 2.05 (111) |
| 2 d | 0.72 (261) | 0.72 (261) | 0.78 (261) | 19.62 (261) | 2.63 (261) | 3.56 (111) |
| 3 d | 1.49 (244) | 1.49 (244) | 1.51 (244) | 24.06 (244) | 3.17 (244) | 8.07 (111) |
| 4 d | 2.02 (227) | 2.02 (227) | 2.06 (227) | 35.83 (227) | 4.09 (227) | 13.78 (111) |
| 5 d | 3.04 (206) | 3.04 (206) | 3.06 (206) | 43.06 (206) | 4.28 (206) | 22.07 (111) |
| 6 d | 3.99 (193) | 3.99 (193) | 3.84 (193) | 45.39 (193) | 4.86 (193) | 34.83 (111) |
| 7 d | 5.88 (185) | 5.88 (185) | 5.79 (185) | 46.90 (185) | 7.41 (185) | 46.34 (111) |

### October 2024 held out (previously inspected evaluation)

| Lead | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 0.58 (285) | 0.58 (285) | 0.58 (285) | 14.92 (285) | 3.68 (285) | 0.75 (134) |
| 12 h | 0.54 (282) | 0.54 (282) | 0.54 (282) | 15.59 (282) | 3.55 (282) | 0.66 (134) |
| 24 h | 0.64 (276) | 0.64 (276) | 0.67 (276) | 15.19 (276) | 4.10 (276) | 0.84 (131) |
| 36 h | 0.93 (269) | 0.93 (269) | 0.92 (269) | 16.61 (269) | 4.47 (269) | 1.63 (130) |
| 2 d | 1.34 (261) | 1.34 (261) | 1.34 (261) | 24.24 (261) | 4.39 (261) | 2.34 (128) |
| 3 d | 2.64 (246) | 2.64 (246) | 2.65 (246) | 37.63 (246) | 6.30 (246) | 5.92 (124) |
| 4 d | 4.11 (226) | 4.11 (226) | 4.01 (226) | 62.73 (226) | 7.96 (226) | 13.30 (116) |
| 5 d | 5.56 (209) | 5.56 (209) | 5.68 (209) | 81.94 (209) | 8.96 (209) | 19.95 (112) |
| 6 d | 7.12 (191) | 7.12 (191) | 6.92 (191) | 83.63 (191) | 11.07 (191) | 29.07 (108) |
| 7 d | 11.09 (173) | 11.09 (173) | 10.97 (173) | 89.75 (173) | 12.95 (173) | 38.83 (104) |

### April 2024 control (training)

| Lead | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 0.46 (312) | 0.46 (312) | 0.46 (312) | 6.97 (312) | 1.24 (312) | 0.53 (114) |
| 12 h | 0.42 (311) | 0.42 (311) | 0.43 (311) | 7.60 (311) | 1.19 (311) | 0.54 (114) |
| 24 h | 0.42 (306) | 0.42 (306) | 0.42 (306) | 7.57 (306) | 1.04 (306) | 0.58 (114) |
| 36 h | 0.56 (301) | 0.56 (301) | 0.56 (301) | 7.54 (301) | 1.22 (301) | 1.69 (114) |
| 2 d | 0.58 (297) | 0.58 (297) | 0.58 (297) | 8.34 (297) | 1.14 (297) | 2.46 (114) |
| 3 d | 0.71 (288) | 0.71 (288) | 0.73 (288) | 10.16 (288) | 1.17 (288) | 5.30 (114) |
| 4 d | 1.05 (279) | 1.05 (279) | 1.02 (279) | 15.64 (279) | 1.16 (279) | 7.31 (114) |
| 5 d | 1.15 (275) | 1.15 (275) | 1.14 (275) | 23.51 (275) | 1.20 (275) | 11.17 (114) |
| 6 d | 1.22 (274) | 1.22 (274) | 1.30 (274) | 37.64 (274) | 1.39 (274) | 15.01 (114) |
| 7 d | 2.05 (273) | 2.05 (273) | 2.14 (273) | 45.99 (273) | 1.91 (273) | 17.11 (114) |

### May 2024 (training)

| Lead | sgp4 (library, WGS72) | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 0.48 (304) | 0.48 (304) | 0.48 (304) | 12.80 (304) | 1.47 (304) | 0.56 (134) |
| 12 h | 0.44 (297) | 0.44 (297) | 0.44 (297) | 13.60 (297) | 1.53 (297) | 0.58 (132) |
| 24 h | 0.50 (287) | 0.50 (287) | 0.51 (287) | 15.18 (287) | 1.53 (287) | 1.05 (130) |
| 36 h | 0.57 (279) | 0.57 (279) | 0.56 (279) | 16.32 (279) | 1.57 (279) | 1.61 (129) |
| 2 d | 0.68 (273) | 0.68 (273) | 0.67 (273) | 16.50 (273) | 1.65 (273) | 2.79 (129) |
| 3 d | 1.16 (255) | 1.16 (255) | 1.22 (255) | 17.58 (255) | 1.67 (255) | 5.60 (126) |
| 4 d | 2.77 (235) | 2.77 (235) | 2.74 (235) | 25.35 (235) | 2.43 (235) | 10.12 (124) |
| 5 d | 3.77 (217) | 3.77 (217) | 3.76 (217) | 28.17 (217) | 3.29 (217) | 14.63 (122) |
| 6 d | 6.43 (199) | 6.43 (199) | 6.55 (199) | 41.13 (199) | 5.79 (199) | 18.35 (119) |
| 7 d | 7.35 (183) | 7.35 (183) | 7.47 (183) | 44.61 (183) | 6.56 (183) | 26.33 (116) |

## Change against plain SGP4

Each method's change to the median absolute in-track residual, relative to the sgp4 library; positive is better.

| Window | Lead | dsgp4 (WGS72) | dsgp4 (WGS-84) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) | sgp4 + storm term (observed ap) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| august | 6 h | -0% | -0% | -2222% | -522% | +6% |
| august | 12 h | +0% | -4% | -2758% | -580% | -2% |
| august | 24 h | +0% | -4% | -3041% | -549% | -29% |
| august | 36 h | -0% | -2% | -2905% | -307% | -29% |
| august | 2 d | -0% | -8% | -2611% | -263% | -62% |
| august | 3 d | +0% | -2% | -1519% | -113% | -6% |
| august | 4 d | +0% | -2% | -1670% | -102% | -2% |
| august | 5 d | +0% | -1% | -1317% | -41% | +9% |
| august | 6 d | +0% | +4% | -1038% | -22% | +7% |
| august | 7 d | -0% | +1% | -698% | -26% | +7% |
| held-out | 6 h | -0% | +1% | -2460% | -532% | -1% |
| held-out | 12 h | +0% | -1% | -2813% | -562% | +5% |
| held-out | 24 h | -0% | -4% | -2260% | -537% | +29% |
| held-out | 36 h | -0% | +1% | -1677% | -378% | +32% |
| held-out | 2 d | +0% | +0% | -1703% | -226% | +53% |
| held-out | 3 d | +0% | -0% | -1326% | -139% | +39% |
| held-out | 4 d | +0% | +2% | -1428% | -94% | +17% |
| held-out | 5 d | -0% | -2% | -1374% | -61% | +1% |
| held-out | 6 d | +0% | +3% | -1075% | -55% | -1% |
| held-out | 7 d | -0% | +1% | -709% | -17% | +10% |
| quiet | 6 h | -0% | -0% | -1419% | -170% | +1% |
| quiet | 12 h | -0% | -3% | -1723% | -185% | -0% |
| quiet | 24 h | +0% | +0% | -1715% | -150% | -54% |
| quiet | 36 h | -0% | +0% | -1253% | -119% | -92% |
| quiet | 2 d | +0% | +0% | -1341% | -97% | -143% |
| quiet | 3 d | -0% | -3% | -1338% | -66% | -150% |
| quiet | 4 d | +0% | +4% | -1383% | -10% | -133% |
| quiet | 5 d | +0% | +0% | -1951% | -5% | -109% |
| quiet | 6 d | -0% | -7% | -2984% | -14% | -98% |
| quiet | 7 d | +0% | -5% | -2146% | +7% | -30% |
| storm | 6 h | +0% | +1% | -2550% | -203% | -4% |
| storm | 12 h | +0% | +1% | -2967% | -246% | -19% |
| storm | 24 h | +0% | -2% | -2946% | -206% | -55% |
| storm | 36 h | +0% | +1% | -2770% | -175% | -118% |
| storm | 2 d | +0% | +2% | -2337% | -144% | -108% |
| storm | 3 d | -0% | -5% | -1417% | -44% | -80% |
| storm | 4 d | -0% | +1% | -815% | +12% | -27% |
| storm | 5 d | +0% | +0% | -647% | +13% | -39% |
| storm | 6 d | -0% | -2% | -540% | +10% | +16% |
| storm | 7 d | +0% | -2% | -507% | +11% | +9% |

## The recommendation

- **ML-dSGP4 (Swarm)**: rejected under the historical checkpoint rule on inspected windows. October 2024 held out: 0 of 10 leads improved, median change -1553%, worst -2813%; August 2024 held out: 0 of 10 leads improved, median change -1946%, worst -3041%.
- **ML-dSGP4 (all missions)**: rejected under the historical checkpoint rule on inspected windows. October 2024 held out: 0 of 10 leads improved, median change -182%, worst -562%; August 2024 held out: 0 of 10 leads improved, median change -188%, worst -580%.

## Retained checkpoints

The initial model and every candidate checkpoint are evaluated on the same eligible training targets. The saved checkpoint is reloaded and evaluated once more; its SHA-256 identifies the bytes.

| Model | Samples kept / candidate | Burn targets excluded | Selected epoch | Reloaded objective | SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| ML-dSGP4 (Swarm) | 18648 / 18648 | 0 | 40 | 6.662583e-06 | d064ce7bc0870b2d547324ab67ec8d09032eb5d56dbd16a68f6b3cb5d867fa97 |
| ML-dSGP4 (all missions) | 89258 / 103488 | 14230 | 40 | 1.653824e-06 | fe7de0d5567882ada2c9f2e53e17aa5d8d107d5c4a644359584d9439033c4cd6 |

## Spacecraft results at one and seven days

Fixed display leads: 24 and 168 hours, median absolute in-track km (n), with every available spacecraft shown. All leads and exact paired denominators are in `dsgp4_paired_comparisons.csv`; these correlated spacecraft/lead cells are descriptive, not independent tests.

| Spacecraft | Window | Lead | sgp4 (library, WGS72) | ML-dSGP4 (Swarm) | ML-dSGP4 (all missions) |
| --- | --- | ---: | ---: | ---: | ---: |
| cryosat-2 | held-out | 24 h | 1.04 (12) | 16.02 (12) | 0.98 (12) |
| cryosat-2 | held-out | 7 d | 14.34 (6) | 4.53 (6) | 13.11 (6) |
| cryosat-2 | august | 24 h | 0.77 (13) | 5.62 (13) | 2.42 (13) |
| gracefo-c | held-out | 24 h | 1.22 (19) | 29.72 (19) | 9.89 (19) |
| gracefo-c | held-out | 7 d | 49.22 (19) | 149.02 (19) | 49.18 (19) |
| gracefo-c | august | 24 h | 0.47 (18) | 55.24 (18) | 4.44 (18) |
| gracefo-c | august | 7 d | 51.40 (18) | 38.46 (18) | 46.93 (18) |
| gracefo-d | held-out | 24 h | 1.21 (20) | 29.53 (20) | 7.90 (20) |
| gracefo-d | held-out | 7 d | 45.13 (20) | 147.54 (20) | 49.86 (20) |
| gracefo-d | august | 24 h | 0.46 (18) | 55.12 (18) | 4.41 (18) |
| gracefo-d | august | 7 d | 52.18 (18) | 39.23 (18) | 47.01 (18) |
| hy-2c | held-out | 24 h | 0.41 (26) | 84.17 (26) | 2.41 (26) |
| hy-2c | held-out | 7 d | 1.47 (12) | 85.32 (12) | 3.82 (12) |
| hy-2c | august | 24 h | 0.29 (25) | 45.81 (25) | 0.87 (25) |
| hy-2c | august | 7 d | 1.12 (22) | 45.98 (22) | 0.53 (22) |
| hy-2d | held-out | 24 h | 0.30 (14) | 52.31 (14) | 1.17 (14) |
| hy-2d | held-out | 7 d | 2.80 (2) | 53.82 (2) | 1.26 (2) |
| hy-2d | august | 24 h | 0.59 (23) | 75.62 (23) | 0.42 (23) |
| jason-3 | held-out | 24 h | 0.41 (17) | 108.54 (17) | 2.28 (17) |
| jason-3 | held-out | 7 d | 0.88 (17) | 109.13 (17) | 1.70 (17) |
| jason-3 | august | 24 h | 0.25 (17) | 61.73 (17) | 4.18 (17) |
| jason-3 | august | 7 d | 0.42 (17) | 62.99 (17) | 3.28 (17) |
| saral | held-out | 24 h | 0.42 (17) | 93.74 (17) | 7.71 (17) |
| saral | held-out | 7 d | 3.13 (17) | 95.19 (17) | 10.78 (17) |
| saral | august | 24 h | 0.42 (18) | 12.00 (18) | 2.16 (18) |
| saral | august | 7 d | 4.69 (18) | 8.02 (18) | 6.56 (18) |
| sentinel-1a | held-out | 24 h | 0.84 (27) | 1.87 (27) | 3.82 (27) |
| sentinel-1a | held-out | 7 d | 14.67 (2) | 10.41 (2) | 17.70 (2) |
| sentinel-1a | august | 24 h | 0.81 (21) | 0.96 (21) | 4.26 (21) |
| sentinel-3a | held-out | 24 h | 0.91 (22) | 9.02 (22) | 8.17 (22) |
| sentinel-3a | held-out | 7 d | 2.61 (12) | 9.64 (12) | 8.55 (12) |
| sentinel-3a | august | 24 h | 0.61 (24) | 2.78 (24) | 2.54 (24) |
| sentinel-3b | held-out | 24 h | 0.56 (11) | 10.52 (11) | 8.23 (11) |
| sentinel-3b | held-out | 7 d | 2.36 (4) | 11.34 (4) | 10.13 (4) |
| sentinel-3b | august | 24 h | 0.51 (11) | 0.61 (11) | 2.35 (11) |
| sentinel-6a | held-out | 24 h | 0.28 (15) | 111.05 (15) | 1.04 (15) |
| sentinel-6a | held-out | 7 d | 0.66 (15) | 111.21 (15) | 0.46 (15) |
| sentinel-6a | august | 24 h | 0.33 (18) | 62.83 (18) | 3.35 (18) |
| sentinel-6a | august | 7 d | 0.36 (18) | 63.26 (18) | 2.94 (18) |
| swarm-a | held-out | 24 h | 2.00 (21) | 3.66 (21) | 7.92 (21) |
| swarm-a | held-out | 7 d | 48.74 (10) | 50.79 (10) | 52.61 (10) |
| swarm-a | august | 24 h | 0.74 (19) | 7.53 (19) | 4.46 (19) |
| swarm-a | august | 7 d | 95.32 (19) | 88.28 (19) | 90.52 (19) |
| swarm-b | held-out | 24 h | 1.72 (19) | 1.94 (19) | 1.64 (19) |
| swarm-b | held-out | 7 d | 29.80 (15) | 29.78 (15) | 29.99 (15) |
| swarm-b | august | 24 h | 0.64 (19) | 2.40 (19) | 0.70 (19) |
| swarm-b | august | 7 d | 60.13 (19) | 58.69 (19) | 59.79 (19) |
| swarm-c | held-out | 24 h | 1.77 (21) | 3.95 (21) | 7.88 (21) |
| swarm-c | held-out | 7 d | 61.97 (21) | 57.33 (21) | 68.14 (21) |
| swarm-c | august | 24 h | 0.84 (19) | 7.47 (19) | 4.27 (19) |
| swarm-c | august | 7 d | 92.71 (19) | 85.61 (19) | 88.09 (19) |
| swot | held-out | 24 h | 0.41 (15) | 7.81 (15) | 5.02 (15) |
| swot | held-out | 7 d | 1.85 (1) | 7.11 (1) | 7.74 (1) |
| swot | august | 24 h | 0.34 (17) | 19.85 (17) | 3.27 (17) |
| swot | august | 7 d | 1.83 (17) | 19.40 (17) | 2.61 (17) |

## What this does not show

- The hybrids are trained on one week of quiet sets and one storm week, on the missions listed, with one architecture and one training recipe; a different recipe could do better or worse, and none is tuned on the held-out windows.
- The dsgp4 baseline with WGS72 constants is the check that the two implementations agree; the hybrid uses the library's WGS-84 constants inside, as published, and the WGS-84 baseline shows that difference alone.
- A method that lowers the median can raise the tail; the 95th percentiles are in the JSON beside this page.

_Last updated 08 September 2026._
