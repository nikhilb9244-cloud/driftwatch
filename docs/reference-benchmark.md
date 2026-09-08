# Calibration against reference orbits: the population beyond Swarm

Every number here is computed from the per-trial file beside `reference_benchmark.json`. The method is the Swarm benchmark's (`docs/calibration-benchmark.md`): every public element set issued in a window is one trial, propagated with SGP4 to leads from six hours to seven days and measured against the mission's reconstructed orbit in the satellite's radial, in-track, cross-track frame; the covariance and the ballistic coefficient on a window are fitted from history that ends where the window's sets begin. Two windows are held out from every tuning, October 2024 as before and August 2024 added here. Laser ranging is the second, independent truth where a mission carries a retroreflector: it is compared with the reconstructed orbit first, so that the disagreement between the two references is on the page before either is compared with an element set.

**Population.** The measured population is 400-600 km: GRACE-FO 1 (C), GRACE-FO 2 (D), Swarm A, Swarm B, Swarm C (379 element sets, 460 to 507 km); 600-750 km: CryoSat-2, Sentinel-1A (169 element sets, 696 to 719 km); 750-850 km: SARAL, Sentinel-3A, Sentinel-3B (236 element sets, 783 to 803 km); 850-1000 km: HY-2C, HY-2D, SWOT (280 element sets, 893 to 952 km); 1000-1400 km: Jason-3, Sentinel-6A (137 element sets, 1338 to 1338 km); 4 windows of one week of element sets each; near-circular, free-flying between manoeuvres, with manoeuvre arcs excluded from a published record where one exists and from detection otherwise. Nothing here is measured for debris, for eccentric orbits, for station-kept constellations, for objects the network tracks less often, or above 1,340 km.

## Windows

| Window | Role | Element sets issued | Truth needed to | Disturbed interval | Note |
| --- | --- | --- | --- | --- | --- |
| quiet | control | 2024-04-20 to 2024-04-27 | 2024-05-04 | none | the quiet control before the May 2024 storm; Kp at or under 4 over 25 to 28 April |
| storm | storm | 2024-05-06 to 2024-05-13 | 2024-05-20 | 2024-05-10 12:00 to 2024-05-13 00:00 | the May 2024 Gannon storm; sets issued from four days before the onset to its end |
| held-out | held-out | 2024-10-06 to 2024-10-13 | 2024-10-20 | 2024-10-10 12:00 to 2024-10-12 00:00 | the 10 to 11 October 2024 storm (Kp 9-), held out from every tuning; nothing was chosen by looking at it |
| august | held-out | 2024-08-08 to 2024-08-15 | 2024-08-22 | 2024-08-12 00:00 to 2024-08-13 12:00 | the 12 August 2024 storm (Kp 8-), the further disturbed window of the reference expansion; held out like October, nothing was chosen by looking at it |

## Missions and their truth

| Mission | NORAD | Band | Reconstructed orbit | Manoeuvres | Laser ranging | Sets per window (quiet, storm, held-out, august) | Truth coverage |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Swarm A | 39452 | 400-600 km | ESA Swarm SP3 (TU Delft) | ESA thruster record | swarma | 19, 18, 21, 19 | complete |
| Swarm B | 39451 | 400-600 km | ESA Swarm SP3 (TU Delft) | ESA thruster record | swarmb | 19, 19, 19, 19 | complete |
| Swarm C | 39453 | 400-600 km | ESA Swarm SP3 (TU Delft) | ESA thruster record | swarmc | 19, 17, 21, 19 | complete |
| GRACE-FO 1 (C) | 43476 | 400-600 km | JPL GNV1B via GFZ ISDC | THR1B thruster record | gracefo1 | 19, 18, 19, 18 | complete |
| GRACE-FO 2 (D) | 43477 | 400-600 km | JPL GNV1B via GFZ ISDC | THR1B thruster record | gracefo2 | 19, 19, 20, 18 | complete |
| Sentinel-1A | 39634 | 600-750 km | Copernicus POEORB via ESA STEP | detection | none | 31, 33, 27, 26 | complete |
| CryoSat-2 | 36508 | 600-750 km | CNES POE via IDS | detection | cryosat2 | 18, 18, 17, 18 | complete |
| SARAL | 39086 | 750-850 km | CNES POE via IDS | detection | saral | 19, 19, 17, 18 | complete |
| Sentinel-3A | 41335 | 750-850 km | CNES POE via IDS | detection | sentinel3a | 29, 30, 27, 32 | complete |
| Sentinel-3B | 43437 | 750-850 km | CNES POE via IDS | detection | sentinel3b | 15, 19, 13, 17 | complete |
| SWOT | 54754 | 850-1000 km | CNES POE via IDS | detection | swot | 21, 19, 20, 17 | complete |
| HY-2C | 46469 | 850-1000 km | CNES POE via IDS | detection | hy2c | 30, 34, 26, 25 | complete |
| HY-2D | 48621 | 850-1000 km | CNES POE via IDS | detection | hy2d | 27, 29, 19, 23 | complete |
| Jason-3 | 41240 | 1000-1400 km | CNES POE via IDS | detection | jason3 | 19, 18, 17, 17 | complete |
| Sentinel-6A | 46984 | 1000-1400 km | CNES POE via IDS | detection | sentinel6a | 18, 15, 15, 18 | complete |
| TerraSAR-X | 31698 | 400-600 km | none anonymous | detection | terrasarx | 8, 5, 9, 6 | quiet: none; storm: none; held-out: none; august: none |
| TanDEM-X | 36605 | 400-600 km | none anonymous | detection | tandemx | 8, 5, 9, 6 | quiet: none; storm: none; held-out: none; august: none |
| ICESat-2 | 43613 | 400-600 km | none anonymous | detection | icesat2 | 17, 18, 20, 21 | quiet: none; storm: none; held-out: none; august: none |

**Asked for and not obtainable without an account, said rather than substituted.**

- **Sentinel-2A and Sentinel-2B.** the Copernicus precise orbit products are served through the Copernicus Data Space Ecosystem, which needs a registered account; no anonymous mirror carries Sentinel-2 orbits, and Sentinel-2 carries no laser retroreflector, so there is no truth for it here
- **ICESat-2 (reconstructed orbit).** the precise orbit determination product is distributed inside ATL03 at NSIDC behind an Earthdata login; the laser-ranging normal points are public and are the truth used
- **TerraSAR-X and TanDEM-X (reconstructed orbit).** GFZ's ISDC serves the rapid science orbits anonymously for 2010 to 2020 and nothing for 2024; the laser-ranging normal points are public and are the truth used
- **GOCE.** the precise science orbits (SST_PSO_2, 2009 to 2013) are behind ESA's EO-SSO login on the GOCE online dissemination service; not obtainable anonymously, so not substituted
- **CHAMP.** GFZ's ISDC serves the 2000 to 2010 rapid science orbits anonymously and Space-Track's element-set history reaches back to 2000, so a CHAMP benchmark is possible on CHAMP's own storm windows; it is not part of this fortnight and is recorded as a candidate

## The horizon by altitude band and window

Task: in-track residual within 25 km, the screening box's half-width, at the 95% of trials; the last lead within it, with the 95th percentile at the first lead beyond it in brackets.

| Altitude band | Missions | quiet | storm | held-out | august |
| --- | --- | --- | --- | --- | --- |
| 400-600 km | GRACE-FO 1 (C), GRACE-FO 2 (D), Swarm A, Swarm B, Swarm C | 5 d (37 km at 6 d) | 2 d (35 km at 3 d) | 24 h (34 km at 36 h) | 2 d (38 km at 3 d) |
| 600-750 km | CryoSat-2, Sentinel-1A | 5 d (26 km at 6 d) | 5 d (27 km at 6 d) | 7 d (every lead measured) | 5 d (every lead measured) |
| 750-850 km | SARAL, Sentinel-3A, Sentinel-3B | 7 d (every lead measured) | 7 d (every lead measured) | 5 d (31 km at 6 d) | 7 d (every lead measured) |
| 850-1000 km | HY-2C, HY-2D, SWOT | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) |
| 1000-1400 km | Jason-3, Sentinel-6A | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) |

### The in-track residual by band, window and lead

Median and 95th percentile of the absolute in-track residual, km, with the number of trials; per band and window.

**400-600 km.**

| Lead | quiet: n, median, p95 | storm: n, median, p95 | held-out: n, median, p95 | august: n, median, p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 95, 0.52, 1.4 | 91, 0.66, 1.4 | 100, 0.82, 2.3 | 93, 0.63, 1.3 |
| 12 h | 95, 0.63, 1.7 | 91, 0.59, 1.3 | 100, 0.90, 6.0 | 93, 0.63, 2.0 |
| 24 h | 95, 0.37, 1.5 | 91, 0.88, 3.6 | 100, 1.56, 17.9 | 93, 0.67, 4.9 |
| 36 h | 95, 1.01, 3.1 | 91, 0.95, 9.0 | 100, 3.88, 34.0 | 93, 1.66, 9.7 |
| 2 d | 95, 1.31, 4.5 | 91, 2.11, 14.8 | 100, 6.34, 55.2 | 93, 4.29, 17.3 |
| 3 d | 95, 2.51, 7.6 | 88, 8.46, 34.7 | 100, 13.19, 115.9 | 93, 10.41, 38.4 |
| 4 d | 95, 4.38, 12.4 | 86, 17.84, 62.6 | 97, 18.48, 201.2 | 93, 19.30, 69.4 |
| 5 d | 95, 8.23, 22.5 | 84, 28.46, 99.1 | 93, 25.24, 249.0 | 93, 31.58, 108.8 |
| 6 d | 95, 11.01, 36.5 | 81, 43.74, 140.3 | 89, 34.78, 382.7 | 93, 45.55, 157.6 |
| 7 d | 95, 18.56, 58.4 | 78, 55.40, 191.3 | 85, 49.22, 550.6 | 93, 57.03, 220.0 |

**600-750 km.**

| Lead | quiet: n, median, p95 | storm: n, median, p95 | held-out: n, median, p95 | august: n, median, p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 45, 0.48, 1.2 | 44, 0.63, 1.1 | 41, 0.68, 2.3 | 39, 0.64, 1.5 |
| 12 h | 45, 0.48, 1.2 | 43, 0.56, 1.7 | 40, 0.47, 4.5 | 37, 0.40, 2.0 |
| 24 h | 43, 0.74, 3.2 | 40, 0.60, 2.4 | 39, 0.91, 6.7 | 34, 0.79, 2.3 |
| 36 h | 42, 0.64, 5.0 | 38, 0.70, 5.2 | 36, 1.55, 9.6 | 29, 0.91, 3.9 |
| 2 d | 41, 0.80, 7.6 | 35, 1.12, 8.5 | 33, 1.32, 10.0 | 25, 0.95, 6.2 |
| 3 d | 37, 1.30, 11.4 | 30, 1.55, 13.4 | 27, 3.35, 11.1 | 19, 3.02, 7.3 |
| 4 d | 35, 3.01, 16.9 | 26, 2.02, 19.5 | 22, 4.63, 11.3 | 12, 7.36, 8.7 |
| 5 d | 35, 3.76, 20.9 | 21, 4.65, 22.1 | 18, 8.18, 21.2 | 4, 6.73, 7.1 |
| 6 d | 35, 6.41, 26.1 | 18, 6.66, 26.6 | 13, 10.82, 16.3 | - |
| 7 d | 35, 9.93, 32.0 | 18, 10.88, 27.4 | 8, 14.67, 21.8 | - |

**750-850 km.**

| Lead | quiet: n, median, p95 | storm: n, median, p95 | held-out: n, median, p95 | august: n, median, p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 57, 0.68, 1.1 | 68, 0.71, 1.5 | 51, 0.85, 4.6 | 60, 0.55, 1.6 |
| 12 h | 54, 0.23, 0.8 | 68, 0.36, 1.4 | 50, 0.38, 5.4 | 58, 0.37, 1.7 |
| 24 h | 52, 0.57, 1.0 | 68, 0.49, 2.1 | 50, 0.58, 6.6 | 53, 0.58, 1.5 |
| 36 h | 47, 0.42, 1.2 | 68, 0.58, 2.6 | 48, 0.61, 9.1 | 50, 0.35, 1.8 |
| 2 d | 46, 0.69, 1.5 | 68, 0.91, 4.0 | 46, 0.72, 5.0 | 46, 0.69, 1.8 |
| 3 d | 40, 0.77, 1.9 | 66, 2.11, 6.0 | 45, 1.39, 7.1 | 39, 1.12, 3.4 |
| 4 d | 33, 0.76, 3.0 | 59, 3.37, 7.0 | 43, 1.85, 10.9 | 32, 1.40, 4.9 |
| 5 d | 30, 1.11, 4.8 | 53, 5.48, 8.3 | 41, 2.45, 15.5 | 25, 2.74, 6.4 |
| 6 d | 29, 1.36, 4.4 | 46, 6.40, 10.9 | 38, 2.33, 31.0 | 18, 3.86, 9.3 |
| 7 d | 29, 1.81, 6.3 | 38, 6.10, 9.5 | 33, 2.74, 17.1 | 18, 4.69, 12.9 |

**850-1000 km.**

| Lead | quiet: n, median, p95 | storm: n, median, p95 | held-out: n, median, p95 | august: n, median, p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 78, 0.45, 0.9 | 77, 0.30, 0.9 | 60, 0.33, 1.2 | 65, 0.44, 0.9 |
| 12 h | 78, 0.38, 0.8 | 75, 0.35, 1.1 | 57, 0.37, 1.4 | 65, 0.39, 1.0 |
| 24 h | 78, 0.39, 0.8 | 73, 0.38, 0.8 | 55, 0.36, 2.2 | 65, 0.36, 1.0 |
| 36 h | 78, 0.35, 0.8 | 72, 0.27, 1.0 | 51, 0.53, 3.2 | 64, 0.43, 1.3 |
| 2 d | 78, 0.39, 0.8 | 72, 0.31, 0.9 | 48, 0.53, 3.2 | 62, 0.36, 1.3 |
| 3 d | 78, 0.48, 1.0 | 67, 0.44, 1.5 | 41, 0.66, 5.9 | 57, 0.34, 1.4 |
| 4 d | 78, 0.63, 1.3 | 63, 1.14, 2.7 | 33, 0.85, 4.2 | 53, 0.78, 1.9 |
| 5 d | 78, 0.67, 1.3 | 58, 1.80, 3.9 | 30, 1.38, 7.4 | 49, 1.33, 2.4 |
| 6 d | 78, 0.44, 1.1 | 53, 2.19, 4.4 | 29, 1.28, 11.1 | 46, 1.33, 3.1 |
| 7 d | 78, 0.94, 2.0 | 48, 3.00, 4.9 | 29, 3.53, 15.1 | 39, 1.31, 4.6 |

**1000-1400 km.**

| Lead | quiet: n, median, p95 | storm: n, median, p95 | held-out: n, median, p95 | august: n, median, p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 37, 0.16, 0.6 | 33, 0.20, 1.0 | 32, 0.19, 0.6 | 35, 0.32, 0.9 |
| 12 h | 37, 0.43, 0.7 | 33, 0.35, 1.0 | 32, 0.55, 0.8 | 35, 0.35, 0.6 |
| 24 h | 37, 0.27, 0.5 | 33, 0.45, 1.7 | 32, 0.32, 0.6 | 35, 0.27, 0.5 |
| 36 h | 37, 0.53, 0.9 | 33, 0.64, 2.6 | 32, 0.61, 1.0 | 35, 0.45, 0.7 |
| 2 d | 37, 0.21, 0.5 | 33, 0.56, 3.4 | 32, 0.30, 0.7 | 35, 0.17, 0.5 |
| 3 d | 37, 0.33, 0.7 | 33, 0.68, 5.3 | 32, 0.25, 0.7 | 35, 0.27, 0.7 |
| 4 d | 37, 0.38, 0.9 | 33, 0.84, 7.2 | 32, 0.57, 1.0 | 35, 0.40, 0.9 |
| 5 d | 37, 0.32, 0.8 | 33, 2.33, 9.3 | 32, 0.26, 1.0 | 35, 0.30, 0.7 |
| 6 d | 37, 0.34, 1.0 | 33, 3.19, 11.6 | 32, 0.61, 1.2 | 35, 0.34, 1.2 |
| 7 d | 37, 0.54, 1.1 | 33, 4.35, 14.1 | 32, 0.80, 1.4 | 35, 0.39, 1.3 |

### Coverage of the empirical covariance, and the storm term, by band

The share of in-track residuals inside two sigma of the covariance the screening would have carried (95 per cent claimed), and the storm term's change to the median absolute in-track residual, at one, three and seven days; a positive improvement means the term brought the prediction closer to the truth. The term needs a ballistic coefficient fitted from the object's own decay, which is not measurable at the higher altitudes, so those cells are empty.

| Band | Window | 2σ at 24 h / 72 h / 168 h | Storm term at 24 h / 72 h / 168 h |
| --- | --- | --- | --- |
| 400-600 km | quiet | 98% / 100% / 98% | -56% / -137% / -5% |
| 400-600 km | storm | 84% / 68% / 83% | -57% / +14% / +35% |
| 400-600 km | held-out | 71% / 65% / 67% | +14% / +41% / +7% |
| 400-600 km | august | 81% / 51% / 33% | -32% / +14% / +12% |
| 600-750 km | quiet | 100% / 95% / 89% | +10% / +7% / -97% |
| 600-750 km | storm | 95% / 97% / 100% | +6% / +2% / -14% |
| 600-750 km | held-out | 85% / 93% / 100% | +7% / -63% / +92% |
| 600-750 km | august | 82% / 95% / - | +1% / -16% / - |
| 750-850 km | quiet | 88% / 100% / 93% | +7% / -18% / +42% |
| 750-850 km | storm | 90% / 94% / 74% | +8% / +30% / +22% |
| 750-850 km | held-out | 80% / 89% / 76% | +3% / +28% / -86% |
| 750-850 km | august | 72% / 72% / 39% | +1% / -18% / +24% |
| 850-1000 km | quiet | 100% / 100% / 100% | -1% / +17% / -14% |
| 850-1000 km | storm | 85% / 100% / 100% | -1% / -4% / +56% |
| 850-1000 km | held-out | 67% / 93% / 90% | +8% / +28% / -13% |
| 850-1000 km | august | 69% / 100% / 100% | -7% / -62% / -55% |
| 1000-1400 km | quiet | 51% / 59% / 73% | +1% / +5% / -138% |
| 1000-1400 km | storm | 6% / 27% / 45% | +0% / -6% / +73% |
| 1000-1400 km | held-out | 81% / 100% / 100% | -3% / +3% / +31% |
| 1000-1400 km | august | 9% / 46% / 51% | -0% / +14% / -23% |

## The horizon by mission and window

| Mission | Band | quiet | storm | held-out | august |
| --- | --- | --- | --- | --- | --- |
| Swarm A | 400-600 km | 5 d (42 km at 6 d) (19 sets) | 2 d (36 km at 3 d) (18 sets) | 24 h (38 km at 36 h) (21 sets) | 36 h (29 km at 2 d) (19 sets) |
| Swarm B | 400-600 km | 5 d (38 km at 6 d) (19 sets) | 2 d (33 km at 3 d) (19 sets) | 2 d (51 km at 3 d) (19 sets) | 3 d (42 km at 4 d) (19 sets) |
| Swarm C | 400-600 km | 5 d (39 km at 6 d) (19 sets) | 2 d (37 km at 3 d) (17 sets) | 24 h (38 km at 36 h) (21 sets) | 36 h (26 km at 2 d) (19 sets) |
| GRACE-FO 1 (C) | 400-600 km | 6 d (34 km at 7 d) (19 sets) | 2 d (25 km at 3 d) (18 sets) | 36 h (39 km at 2 d) (19 sets) | 2 d (34 km at 3 d) (18 sets) |
| GRACE-FO 2 (D) | 400-600 km | 6 d (32 km at 7 d) (19 sets) | 3 d (25 km at 4 d) (19 sets) | 24 h (26 km at 36 h) (20 sets) | 2 d (34 km at 3 d) (18 sets) |
| Sentinel-1A | 600-750 km | 5 d (27 km at 6 d) (31 sets) | 5 d (every lead measured) (33 sets) | 4 d (27 km at 5 d) (27 sets) | 5 d (every lead measured) (26 sets) |
| CryoSat-2 | 600-750 km | 7 d (every lead measured) (18 sets) | 5 d (27 km at 6 d) (18 sets) | 7 d (every lead measured) (17 sets) | 5 d (every lead measured) (18 sets) |
| SARAL | 750-850 km | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (19 sets) | 4 d (25 km at 5 d) (17 sets) | 7 d (every lead measured) (18 sets) |
| Sentinel-3A | 750-850 km | 7 d (every lead measured) (29 sets) | 7 d (every lead measured) (30 sets) | 5 d (37 km at 6 d) (27 sets) | 5 d (every lead measured) (32 sets) |
| Sentinel-3B | 750-850 km | 7 d (every lead measured) (15 sets) | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (13 sets) | 5 d (every lead measured) (17 sets) |
| SWOT | 850-1000 km | 7 d (every lead measured) (21 sets) | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (20 sets) | 7 d (every lead measured) (17 sets) |
| HY-2C | 850-1000 km | 7 d (every lead measured) (30 sets) | 7 d (every lead measured) (34 sets) | 7 d (every lead measured) (26 sets) | 7 d (every lead measured) (25 sets) |
| HY-2D | 850-1000 km | 7 d (every lead measured) (27 sets) | 7 d (every lead measured) (29 sets) | 7 d (every lead measured) (19 sets) | 6 d (every lead measured) (23 sets) |
| Jason-3 | 1000-1400 km | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (18 sets) | 7 d (every lead measured) (17 sets) | 7 d (every lead measured) (17 sets) |
| Sentinel-6A | 1000-1400 km | 7 d (every lead measured) (18 sets) | 7 d (every lead measured) (15 sets) | 7 d (every lead measured) (15 sets) | 7 d (every lead measured) (18 sets) |

## Methodology correction, 7 September 2026: one manoeuvre-exclusion rule on both paths

Manoeuvre arcs are excluded on two paths. Where a published thruster record exists (Swarm, GRACE-FO), the record path has from the first run dropped every set-lead pair with a burn between 24 hours before the set's epoch, the tracking arc the set was fitted from, and the lead's time. Where no record exists (the CNES, Copernicus and laser-only missions) detection decides, and until 7 September 2026 the detection path dropped only the pairs whose propagation arc, from the epoch to the lead, crossed a detected burn: a set fitted across a burn in the 24 hours before its epoch was kept. The record path's rule was extended to the detection path without change, the same 24-hour arc (`precise.MANOEUVRE_ARC_HOURS`) on both, and the benchmark was rerun with nothing else altered.

The extension was applied after the results on the held-out windows had been seen: Sentinel-3B's October figure, 3 d against Sentinel-3A's 7 d in the same orbit, is what exposed the difference between the two paths. The rule and its arc were fixed on the record path before any held-out result existed and were not tuned, but the decision to apply them to the detection path was taken with the October and August results in view, and the held-out figures in the two bands the rule moved carry that qualification.

It moved two figures in the band table: the 750-850 km October horizon up, from 3 d (26 km at 4 d) to 5 d (31 km at 6 d), and the 600-750 km August horizon down, from 6 d to 5 d, every lead measured in both. The 400-600 km row, the five spacecraft with a published record, is unchanged in every window: 5 d, 2 d, 24 h, 2 d. Per mission it moved Sentinel-3B from 4 d, 7 d, 3 d, 4 d to 7 d, 7 d, 7 d, 5 d, Sentinel-3A in October from 7 d to 5 d, Sentinel-1A in May from 6 d to 5 d, CryoSat-2 in August from 6 d to 5 d, and SWOT in October from 5 d to 7 d; the usable element sets went from 1,228 to 1,201. Both tables as they stood before the correction are kept below, as rendered on 7 September 2026 from the run of that day under the earlier detection rule; the two tables above are the corrected ones.

**The horizon by altitude band and window, before the correction.**

| Altitude band | Missions | quiet | storm | held-out | august |
| --- | --- | --- | --- | --- | --- |
| 400-600 km | GRACE-FO 1 (C), GRACE-FO 2 (D), Swarm A, Swarm B, Swarm C | 5 d (37 km at 6 d) | 2 d (35 km at 3 d) | 24 h (34 km at 36 h) | 2 d (38 km at 3 d) |
| 600-750 km | CryoSat-2, Sentinel-1A | 5 d (26 km at 6 d) | 5 d (27 km at 6 d) | 7 d (every lead measured) | 6 d (every lead measured) |
| 750-850 km | SARAL, Sentinel-3A, Sentinel-3B | 7 d (every lead measured) | 7 d (every lead measured) | 3 d (26 km at 4 d) | 7 d (every lead measured) |
| 850-1000 km | HY-2C, HY-2D, SWOT | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) |
| 1000-1400 km | Jason-3, Sentinel-6A | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) | 7 d (every lead measured) |

**The horizon by mission and window, before the correction.**

| Mission | Band | quiet | storm | held-out | august |
| --- | --- | --- | --- | --- | --- |
| Swarm A | 400-600 km | 5 d (42 km at 6 d) (19 sets) | 2 d (36 km at 3 d) (18 sets) | 24 h (38 km at 36 h) (21 sets) | 36 h (29 km at 2 d) (19 sets) |
| Swarm B | 400-600 km | 5 d (38 km at 6 d) (19 sets) | 2 d (33 km at 3 d) (19 sets) | 2 d (51 km at 3 d) (19 sets) | 3 d (42 km at 4 d) (19 sets) |
| Swarm C | 400-600 km | 5 d (39 km at 6 d) (19 sets) | 2 d (37 km at 3 d) (17 sets) | 24 h (38 km at 36 h) (21 sets) | 36 h (26 km at 2 d) (19 sets) |
| GRACE-FO 1 (C) | 400-600 km | 6 d (34 km at 7 d) (19 sets) | 2 d (25 km at 3 d) (18 sets) | 36 h (39 km at 2 d) (19 sets) | 2 d (34 km at 3 d) (18 sets) |
| GRACE-FO 2 (D) | 400-600 km | 6 d (32 km at 7 d) (19 sets) | 3 d (25 km at 4 d) (19 sets) | 24 h (26 km at 36 h) (20 sets) | 2 d (34 km at 3 d) (18 sets) |
| Sentinel-1A | 600-750 km | 5 d (27 km at 6 d) (31 sets) | 6 d (every lead measured) (33 sets) | 4 d (27 km at 5 d) (27 sets) | 5 d (every lead measured) (26 sets) |
| CryoSat-2 | 600-750 km | 7 d (every lead measured) (18 sets) | 5 d (27 km at 6 d) (18 sets) | 7 d (every lead measured) (17 sets) | 6 d (every lead measured) (18 sets) |
| SARAL | 750-850 km | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (19 sets) | 4 d (25 km at 5 d) (17 sets) | 7 d (every lead measured) (18 sets) |
| Sentinel-3A | 750-850 km | 7 d (every lead measured) (29 sets) | 7 d (every lead measured) (30 sets) | 7 d (every lead measured) (27 sets) | 5 d (every lead measured) (32 sets) |
| Sentinel-3B | 750-850 km | 4 d (27 km at 5 d) (15 sets) | 7 d (every lead measured) (19 sets) | 3 d (27 km at 4 d) (13 sets) | 4 d (31 km at 5 d) (17 sets) |
| SWOT | 850-1000 km | 7 d (every lead measured) (21 sets) | 7 d (every lead measured) (19 sets) | 5 d (25 km at 6 d) (20 sets) | 7 d (every lead measured) (17 sets) |
| HY-2C | 850-1000 km | 7 d (every lead measured) (30 sets) | 7 d (every lead measured) (34 sets) | 7 d (every lead measured) (26 sets) | 7 d (every lead measured) (25 sets) |
| HY-2D | 850-1000 km | 7 d (every lead measured) (27 sets) | 7 d (every lead measured) (29 sets) | 7 d (every lead measured) (19 sets) | 6 d (every lead measured) (23 sets) |
| Jason-3 | 1000-1400 km | 7 d (every lead measured) (19 sets) | 7 d (every lead measured) (18 sets) | 7 d (every lead measured) (17 sets) | 7 d (every lead measured) (17 sets) |
| Sentinel-6A | 1000-1400 km | 7 d (every lead measured) (18 sets) | 7 d (every lead measured) (15 sets) | 7 d (every lead measured) (15 sets) | 7 d (every lead measured) (18 sets) |

## The first element sets after a burn, against cadence and delay

Every burn that fell inside a window's set span with a set issued after it, from the published record where one exists and otherwise from the orbit-step detector on the reconstructed orbit, which places a burn to about an orbit either side: the cadence of the mission's sets in the window (the median gap between consecutive epochs) and, for the first 3 sets issued after the burn, the delay from the burn and the absolute in-track residual at 24 h / 3 d / 4 d / 7 d, km, beside the median of the window's usable trials at the same leads for scale. A pair whose own arc reaches a later burn is blank. The set-jump detector's intervals are not read as burns here: a storm produces them too.

| Mission | Window | Burn (UTC), how found | Sets, cadence | First set after: delay; residual at 24 h / 3 d / 4 d / 7 d | Second set after: delay; residual at 24 h / 3 d / 4 d / 7 d | Third set after: delay; residual at 24 h / 3 d / 4 d / 7 d | Usable-trial median at 24 h / 3 d / 4 d / 7 d |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sentinel-1A | storm | 2024-05-07 21:55, orbit-step | 33, 6.6 h | 6.2 h; 1.5 / 3.2 / 4.2 / - | 14.5 h; 0.0 / 0.4 / 0.6 / - | 16.1 h; 0.8 / 0.4 / 1.1 / - | 0.9 / 1.0 / 0.9 / - |
| CryoSat-2 | quiet | 2024-04-24 15:35, orbit-step | 18, 8.3 h | 5.4 h; 0.7 / 2.7 / 4.6 / 10.0 | 7.0 h; 1.2 / 3.2 / 5.3 / 10.4 | 21.9 h; 0.4 / 0.0 / 0.6 / 2.3 | 0.4 / 0.6 / 0.8 / 1.7 |
| CryoSat-2 | held-out | 2024-10-09 03:47, orbit-step | 17, 8.3 h | 9.6 h; 0.6 / 2.3 / 2.3 / 4.4 | 16.2 h; 0.2 / 3.4 / 4.9 / 12.6 | 34.4 h; 1.3 / 6.2 / 8.3 / 21.4 | 1.0 / 3.7 / 5.0 / 14.3 |
| CryoSat-2 | august | 2024-08-08 17:15, orbit-step | 18, 8.3 h | 18.6 h; 0.7 / 1.9 / 2.3 / - | 20.2 h; 1.2 / 2.4 / 2.9 / - | 28.5 h; 0.4 / 0.5 / 1.1 / - | 0.8 / 1.9 / 3.0 / - |
| Sentinel-3A | quiet | 2024-04-24 09:00, orbit-step | 29, 6.7 h | 18.5 h; 0.3 / 0.8 / 0.2 / 1.6 | 26.9 h; 0.4 / 0.8 / 0.5 / 1.2 | 28.6 h; 0.6 / 1.5 / 0.8 / 0.6 | 0.6 / 1.5 / 1.2 / 1.6 |
| Sentinel-3A | held-out | 2024-10-06 07:43, orbit-step | 27, 6.7 h | 11.7 h; 0.9 / 0.1 / 0.1 / 2.1 | 13.4 h; 0.8 / 0.3 / 0.2 / 2.0 | 20.2 h; 0.4 / 1.2 / 1.1 / 3.0 | 0.9 / 1.5 / 2.2 / 2.6 |
| Sentinel-3B | quiet | 2024-04-25 07:52, orbit-step | 15, 10.1 h | 6.8 h; 7.0 / 18.6 / 25.3 / 44.9 | 20.2 h; 0.9 / 4.1 / 5.1 / 11.5 | 30.3 h; 0.1 / 1.1 / 2.8 / 6.8 | 0.7 / 1.1 / 2.8 / 7.0 |
| Sentinel-3B | held-out | 2024-10-10 06:55, orbit-step | 13, 12.6 h | 3.4 h; 9.0 / 24.6 / 32.8 / 60.9 | 27.0 h; 0.2 / 0.2 / 0.8 / 3.1 | 35.4 h; 1.2 / 1.4 / 2.0 / 4.9 | 0.6 / 0.4 / 0.8 / 2.4 |
| Sentinel-3B | august | 2024-08-13 13:51, orbit-step | 17, 10.9 h | 8.3 h; 9.6 / 22.4 / 30.1 / - | 15.1 h; 0.4 / 1.2 / 1.0 / - | 20.1 h; 0.2 / 0.7 / 0.6 / - | 0.5 / 0.5 / 0.9 / - |
| SWOT | held-out | 2024-10-11 14:18, orbit-step | 20, 8.6 h | 2.4 h; 5.8 / 14.9 / 19.3 / 32.4 | 23.0 h; 0.1 / 0.6 / 0.7 / 1.7 | 29.8 h; 0.4 / 0.8 / 0.8 / 1.8 | 0.4 / 0.9 / 0.7 / 1.8 |
| HY-2D | storm | 2024-05-07 06:30, orbit-step | 29, 6.9 h | 13.8 h; 0.5 / 0.4 / 0.2 / 2.4 | 15.5 h; 0.6 / 0.8 / 0.0 / 2.8 | 22.5 h; 0.1 / 0.4 / 1.7 / 3.7 | 0.5 / 0.7 / 1.4 / 3.7 |
| HY-2D | held-out | 2024-10-10 01:56, orbit-step | 19, 6.9 h | 58.6 h; 0.1 / 0.4 / 0.4 / 2.1 | 67.3 h; 0.4 / 0.6 / 0.4 / 3.5 | - | 0.3 / 0.4 / 0.4 / 2.8 |

Spearman rank correlation of the first set's residual with the cadence and with the delay after the burn, per burn (12) and per spacecraft, the means over each one's burns (6):

| Lead | Per burn, cadence | Per burn, delay | Per spacecraft, cadence | Per spacecraft, delay |
| --- | --- | --- | --- | --- |
| 24 h | +0.67 (n 12, p 0.017) | -0.69 (n 12, p 0.014) | +0.60 (n 6, p 0.208) | -0.94 (n 6, p 0.005) |
| 3 d | +0.73 (n 12, p 0.007) | -0.76 (n 12, p 0.004) | +0.60 (n 6, p 0.208) | -0.94 (n 6, p 0.005) |
| 4 d | +0.78 (n 12, p 0.003) | -0.71 (n 12, p 0.010) | +0.66 (n 6, p 0.156) | -0.89 (n 6, p 0.019) |
| 7 d | +0.97 (n 9, p 0.000) | -0.88 (n 9, p 0.002) | +1.00 (n 5, p 0.000) | -0.80 (n 5, p 0.104) |

### What the first set after each burn contains

Each set's semi-major axis is put in the reconstructed orbit's convention (SGP4 over one revolution centred on its epoch, the osculating value averaged as the detector averages the orbit's), the constant between the two conventions, most of it the ten-second finite-difference velocity the orbit reader carries, is calibrated on the window's clean sets (their median residual against the orbit, with the scatter as 1.4826 times the median absolute deviation), and the set's error is measured against the orbit at its own epoch, not the plateau after the burn, because a decaying orbit has moved on by then. The fraction of the burn a set contains is one plus that error over the burn: at or under 0.25 the set is a pre-burn fit with its epoch advanced past the burn, at or over 0.75 it contains the burn, between the two it was fitted across it; a burn under 3 scatters is unresolved. The drift the error predicts, three halves of the mean motion times the error times the lead, is beside the observed residual, signed as the benchmark signs it (positive when the satellite is ahead of the set). The thresholds were fixed before any set was classified.

| Mission | Window | Burn (m) | Clean sets: n, offset, scatter (m) | First set after: delay, error at its epoch (m), fraction, class | Observed / predicted at 24 h (km) | Observed / predicted at 4 d (km) |
| --- | --- | ---: | --- | --- | --- | --- |
| Sentinel-1A | storm | +9 | 27, +74, 5.1 | 6.2 h, -11, -0.22, unresolved | -1.5 / -1.5 | -4.2 / -6.1 |
| CryoSat-2 | quiet | +71 | 14, +73, 1.8 | 5.4 h, -6, 0.92, post-burn | -0.7 / -0.8 | -4.6 / -3.3 |
| CryoSat-2 | held-out | +86 | 15, +72, 6.4 | 9.6 h, +5, 1.06, post-burn | +0.6 / +0.7 | +2.3 / +3.0 |
| CryoSat-2 | august | +45 | 14, +74, 5.3 | 18.6 h, -7, 0.85, post-burn | +0.7 / -0.9 | +2.3 / -3.7 |
| Sentinel-3A | quiet | +66 | 27, +74, 4.3 | 18.5 h, +1, 1.02, post-burn | +0.3 / +0.2 | +0.2 / +0.8 |
| Sentinel-3A | held-out | +75 | 22, +71, 2.7 | 11.7 h, -2, 0.98, post-burn | -0.9 / -0.2 | -0.1 / -0.9 |
| Sentinel-3B | quiet | +41 | 12, +70, 2.5 | 6.8 h, -38, 0.06, pre-burn re-epoched | -7.0 / -5.2 | -25.3 / -20.7 |
| Sentinel-3B | held-out | +65 | 12, +70, 4.3 | 3.4 h, -63, 0.04, pre-burn re-epoched | -9.0 / -8.5 | -32.8 / -33.9 |
| Sentinel-3B | august | +53 | 13, +70, 3.4 | 8.3 h, -47, 0.12, pre-burn re-epoched | -9.6 / -6.3 | -30.1 / -25.3 |
| SWOT | held-out | +30 | 17, +71, 6.2 | 2.4 h, -32, -0.07, pre-burn re-epoched | -5.8 / -4.3 | -19.3 / -17.1 |
| HY-2D | storm | +34 | 24, +71, 1.9 | 13.8 h, -5, 0.86, post-burn | -0.5 / -0.6 | +0.2 / -2.6 |
| HY-2D | held-out | +95 | 18, +73, 1.9 | 58.6 h, -0, 1.00, post-burn | +0.1 / -0.0 | -0.4 / -0.1 |

The observed residuals in this table are signed; the tables above carry their absolute values. The second and third sets after each burn are classified in the JSON beside this page.

Burns inside a span with no set issued after them before the span's end: Sentinel-1A, august (2024-08-13 19:47 to 23:39, orbit-step); Sentinel-3A, august (2024-08-14 11:47 to 18:42, orbit-step).

Burns after a span's last set, inside the truth period, which take out only the leads of earlier sets: Swarm A, held-out (2024-10-15 21:07 to 21:08, record); Swarm A, held-out (2024-10-15 21:54 to 21:54, record); Swarm B, held-out (2024-10-17 22:58 to 23:23, record); GRACE-FO 2 (D), storm (2024-05-15 06:11 to 06:14, record); Sentinel-1A, storm (2024-05-14 19:47 to 23:49, orbit-step); Sentinel-1A, storm (2024-05-16 12:32 to 15:49, orbit-step); Sentinel-1A, storm (2024-05-16 19:08 to 22:42, orbit-step); Sentinel-1A, held-out (2024-10-13 20:00 to 01:10, orbit-step); CryoSat-2, august (2024-08-15 15:55 to 19:43, orbit-step); Sentinel-3A, storm (2024-05-16 06:00 to 09:39, orbit-step); Sentinel-3A, held-out (2024-10-17 06:14 to 09:50, orbit-step); Sentinel-3B, storm (2024-05-15 05:16 to 09:52, orbit-step); Sentinel-3B, august (2024-08-20 06:57 to 11:20, orbit-step); HY-2C, storm (2024-05-15 00:13 to 03:45, orbit-step); HY-2C, august (2024-08-20 10:39 to 14:26, orbit-step); HY-2D, august (2024-08-15 06:09 to 10:37, orbit-step).

## Laser ranging: how the two references disagree

Observed minus predicted one-way range of the reconstructed orbit against every ILRS normal point of the window above 20 degrees of elevation, metres: the median, the RMS and the 95th percentile of the absolute residual, with the number of points and stations. Marini-Murray troposphere from the station's own meteorology; station coordinates SLRF2020 with the ILRS site eccentricities; the retroreflector's offset from the centre of mass is not applied, so the figures bound the disagreement at the metre level and do not validate either product at its own centimetre level.

| Mission | Window | n | Stations | Median (m) | RMS (m) | p95 of |residual| (m) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Swarm A | quiet | 636 | 16 | -0.24 | 0.44 | 0.76 |
| Swarm A | storm | 472 | 6 | -0.13 | 0.42 | 0.73 |
| Swarm A | held-out | 323 | 10 | -0.58 | 0.87 | 0.78 |
| Swarm A | august | 556 | 16 | -0.19 | 0.41 | 0.71 |
| Swarm B | quiet | 1892 | 20 | -0.24 | 0.45 | 0.77 |
| Swarm B | storm | 1576 | 21 | -0.27 | 6.25 | 0.77 |
| Swarm B | held-out | 778 | 12 | -0.35 | 0.47 | 0.78 |
| Swarm B | august | 1108 | 19 | -0.40 | 0.51 | 0.82 |
| Swarm C | quiet | 750 | 16 | -0.20 | 0.42 | 0.74 |
| Swarm C | storm | 428 | 6 | -0.21 | 0.38 | 0.69 |
| Swarm C | held-out | 253 | 7 | -0.34 | 0.46 | 0.74 |
| Swarm C | august | 637 | 15 | -0.13 | 0.39 | 0.70 |
| GRACE-FO 1 (C) | quiet | 869 | 13 | -0.23 | 0.40 | 0.65 |
| GRACE-FO 1 (C) | storm | 685 | 14 | -0.33 | 0.42 | 0.65 |
| GRACE-FO 1 (C) | held-out | 529 | 15 | -0.28 | 0.81 | 0.67 |
| GRACE-FO 1 (C) | august | 1181 | 24 | -0.20 | 0.39 | 0.67 |
| GRACE-FO 2 (D) | quiet | 722 | 9 | -0.35 | 0.43 | 0.71 |
| GRACE-FO 2 (D) | storm | 557 | 10 | -0.25 | 0.39 | 0.67 |
| GRACE-FO 2 (D) | held-out | 411 | 10 | -0.16 | 0.39 | 0.69 |
| GRACE-FO 2 (D) | august | 1162 | 20 | -0.38 | 2.17 | 0.73 |
| CryoSat-2 | quiet | 1708 | 21 | -0.30 | 1.89 | 0.92 |
| CryoSat-2 | storm | 1398 | 24 | -0.35 | 0.57 | 0.98 |
| CryoSat-2 | held-out | 1316 | 24 | -0.04 | 0.56 | 0.91 |
| CryoSat-2 | august | 1965 | 28 | -0.31 | 17.90 | 0.95 |
| SARAL | quiet | 1507 | 20 | -0.32 | 0.35 | 0.58 |
| SARAL | storm | 1518 | 20 | -0.28 | 0.33 | 0.56 |
| SARAL | held-out | 1255 | 21 | -0.30 | 0.49 | 0.57 |
| SARAL | august | 1037 | 20 | -0.28 | 0.32 | 0.54 |
| Sentinel-3A | quiet | 1652 | 14 | -0.45 | 0.57 | 0.96 |
| Sentinel-3A | storm | 1531 | 15 | -0.46 | 0.56 | 0.95 |
| Sentinel-3A | held-out | 947 | 12 | -0.45 | 0.55 | 0.92 |
| Sentinel-3A | august | 1524 | 14 | -0.38 | 0.52 | 0.92 |
| Sentinel-3B | quiet | 1854 | 14 | -0.47 | 21.70 | 0.96 |
| Sentinel-3B | storm | 1594 | 15 | -0.53 | 0.60 | 0.98 |
| Sentinel-3B | held-out | 877 | 12 | -0.50 | 0.85 | 0.91 |
| Sentinel-3B | august | 1825 | 14 | -0.42 | 0.54 | 0.93 |
| SWOT | quiet | 2422 | 21 | -2.08 | 2.13 | 2.79 |
| SWOT | storm | 2051 | 18 | -2.12 | 2.13 | 2.77 |
| SWOT | held-out | 1581 | 19 | -2.03 | 2.07 | 2.70 |
| SWOT | august | 2228 | 21 | -1.99 | 2.03 | 2.69 |
| HY-2C | quiet | 1604 | 24 | -0.78 | 0.91 | 1.46 |
| HY-2C | storm | 1139 | 18 | -0.81 | 0.90 | 1.42 |
| HY-2C | held-out | 1284 | 19 | -0.47 | 38.42 | 1.37 |
| HY-2C | august | 1448 | 24 | -0.75 | 0.88 | 1.43 |
| HY-2D | quiet | 2008 | 23 | -0.58 | 0.81 | 1.38 |
| HY-2D | storm | 1779 | 24 | -0.68 | 1.40 | 1.41 |
| HY-2D | held-out | 944 | 20 | -0.64 | 0.93 | 1.47 |
| HY-2D | august | 1832 | 23 | -0.51 | 0.80 | 1.42 |
| Jason-3 | quiet | 4154 | 20 | -0.44 | 0.54 | 0.91 |
| Jason-3 | storm | 4304 | 23 | -0.44 | 0.55 | 0.92 |
| Jason-3 | held-out | 4529 | 25 | -0.46 | 3.08 | 0.91 |
| Jason-3 | august | 4780 | 28 | -0.46 | 0.55 | 0.91 |
| Sentinel-6A | quiet | 4561 | 21 | -0.41 | 0.47 | 0.76 |
| Sentinel-6A | storm | 3643 | 20 | -0.40 | 0.46 | 0.74 |
| Sentinel-6A | held-out | 3612 | 23 | -0.44 | 0.85 | 0.76 |
| Sentinel-6A | august | 4523 | 23 | -0.42 | 0.48 | 0.76 |

### The element set against the laser, by band, window and lead

The same range residual for each element set's SGP4 propagation to the normal points inside its leads, km, absolute, median and 95th percentile with the number of points and sets. A range residual is one projection of the position error, so it is smaller than the in-track residual it accompanies; for the missions without a reconstructed orbit it is the only truth.

| Band | Window | Missions | 6 h | 24 h | 72 h | 168 h |
| --- | --- | --- | --- | --- | --- | --- |
| 400-600 km | quiet | GRACE-FO 1 (C), GRACE-FO 2 (D), ICESat-2, Swarm A, Swarm B, Swarm C, TanDEM-X, TerraSAR-X | 0.25 / 0.9 (1279, 67) | 0.39 / 2.0 (2052, 95) | 1.02 / 9.7 (3021, 108) | 6.86 / 59.5 (3213, 106) |
| 400-600 km | storm | GRACE-FO 1 (C), GRACE-FO 2 (D), ICESat-2, Swarm A, Swarm B, Swarm C, TanDEM-X, TerraSAR-X | 0.24 / 0.9 (1201, 59) | 0.31 / 1.1 (1718, 74) | 1.15 / 11.4 (2104, 81) | 20.13 / 79.7 (1758, 75) |
| 400-600 km | held-out | GRACE-FO 1 (C), GRACE-FO 2 (D), ICESat-2, Swarm A, Swarm B, Swarm C, TanDEM-X, TerraSAR-X | 0.34 / 1.0 (733, 46) | 0.39 / 2.2 (1228, 74) | 4.09 / 35.7 (1799, 93) | 15.30 / 181.3 (1402, 82) |
| 400-600 km | august | GRACE-FO 1 (C), GRACE-FO 2 (D), ICESat-2, Swarm A, Swarm B, Swarm C, TanDEM-X, TerraSAR-X | 0.24 / 0.7 (1561, 67) | 0.34 / 2.8 (1812, 74) | 2.08 / 17.3 (2719, 95) | 20.20 / 84.2 (2234, 88) |
| 600-750 km | quiet | CryoSat-2 | 0.25 / 0.6 (307, 12) | 0.22 / 0.7 (367, 13) | 0.28 / 0.8 (268, 9) | 1.01 / 4.2 (115, 4) |
| 600-750 km | storm | CryoSat-2 | 0.23 / 0.6 (321, 16) | 0.26 / 2.1 (420, 15) | 0.51 / 7.8 (539, 18) | 3.69 / 18.8 (565, 18) |
| 600-750 km | held-out | CryoSat-2 | 0.17 / 0.9 (277, 12) | 0.21 / 0.9 (288, 12) | 0.69 / 3.8 (202, 7) | 5.32 / 12.4 (184, 6) |
| 600-750 km | august | CryoSat-2 | 0.20 / 0.9 (402, 14) | 0.23 / 1.0 (406, 12) | 0.44 / 2.3 (328, 10) | - |
| 750-850 km | quiet | SARAL, Sentinel-3A, Sentinel-3B | 0.21 / 0.7 (1061, 48) | 0.24 / 0.7 (1559, 53) | 0.22 / 1.1 (1479, 44) | 0.52 / 3.3 (952, 29) |
| 750-850 km | storm | SARAL, Sentinel-3A, Sentinel-3B | 0.31 / 0.8 (1209, 53) | 0.26 / 1.0 (1777, 63) | 0.49 / 3.3 (1895, 67) | 2.50 / 7.5 (1213, 45) |
| 750-850 km | held-out | SARAL, Sentinel-3A, Sentinel-3B | 0.30 / 3.5 (643, 39) | 0.20 / 2.1 (1050, 45) | 0.53 / 5.1 (1334, 46) | 1.28 / 14.0 (964, 37) |
| 750-850 km | august | SARAL, Sentinel-3A, Sentinel-3B | 0.31 / 0.9 (1066, 50) | 0.27 / 0.8 (1230, 51) | 0.25 / 1.2 (1233, 44) | 1.02 / 4.2 (528, 18) |
| 850-1000 km | quiet | HY-2C, HY-2D, SWOT | 0.22 / 0.6 (1504, 69) | 0.23 / 0.6 (2315, 78) | 0.24 / 0.7 (2607, 78) | 0.34 / 1.0 (2471, 78) |
| 850-1000 km | storm | HY-2C, HY-2D, SWOT | 0.22 / 0.7 (1649, 69) | 0.21 / 0.7 (2070, 71) | 0.24 / 0.8 (2179, 69) | 1.04 / 3.3 (1474, 50) |
| 850-1000 km | held-out | HY-2C, HY-2D, SWOT | 0.17 / 0.9 (1133, 55) | 0.17 / 0.8 (1603, 57) | 0.26 / 1.3 (1400, 47) | 0.83 / 7.6 (867, 29) |
| 850-1000 km | august | HY-2C, HY-2D, SWOT | 0.23 / 0.7 (1655, 62) | 0.21 / 0.6 (1913, 64) | 0.27 / 0.9 (1975, 61) | 0.57 / 2.0 (1427, 46) |
| 1000-1400 km | quiet | Jason-3, Sentinel-6A | 0.16 / 0.5 (1105, 36) | 0.16 / 0.5 (1206, 37) | 0.22 / 0.5 (1294, 37) | 0.29 / 0.7 (1234, 37) |
| 1000-1400 km | storm | Jason-3, Sentinel-6A | 0.18 / 0.6 (1014, 32) | 0.21 / 0.7 (1109, 33) | 0.30 / 1.8 (1048, 33) | 0.62 / 4.7 (917, 33) |
| 1000-1400 km | held-out | Jason-3, Sentinel-6A | 0.12 / 0.4 (1013, 31) | 0.13 / 0.5 (873, 31) | 0.19 / 0.5 (990, 32) | 0.29 / 0.9 (978, 32) |
| 1000-1400 km | august | Jason-3, Sentinel-6A | 0.17 / 0.5 (1121, 34) | 0.19 / 0.5 (1127, 35) | 0.21 / 0.5 (1145, 35) | 0.33 / 0.8 (1172, 35) |

### The missions whose only truth is the laser

The same range residual per mission and window for the missions with no reconstructed orbit on an anonymous server: this is all that is measured for them, and the per-mission rows for every other mission are in the JSON beside this page.

| Mission | Window | Sets, stations | 6 h | 24 h | 72 h | 168 h |
| --- | --- | --- | --- | --- | --- | --- |
| TerraSAR-X | quiet | 8, 11 | 0.24 / 1.5 (51) | 1.50 / 2.9 (122) | 9.11 / 22.2 (227) | 44.24 / 102.2 (228) |
| TerraSAR-X | storm | 3, 7 | 0.78 / 1.4 (64) | 0.44 / 1.1 (63) | 1.73 / 6.1 (40) | - |
| TerraSAR-X | held-out | 2, 5 | 0.37 / 0.7 (32) | 3.86 / 6.4 (13) | - | - |
| TerraSAR-X | august | 4, 3 | 0.42 / 0.6 (18) | 2.31 / 6.7 (46) | 4.67 / 13.4 (31) | - |
| TanDEM-X | quiet | 8, 14 | 0.57 / 1.0 (55) | 0.64 / 3.5 (175) | 5.65 / 13.6 (202) | 48.84 / 91.4 (204) |
| TanDEM-X | storm | 3, 7 | 0.59 / 1.0 (54) | 0.15 / 0.8 (69) | 1.58 / 2.1 (20) | - |
| TanDEM-X | held-out | 6, 4 | 0.01 / 0.1 (22) | 0.59 / 1.3 (31) | 12.00 / 29.8 (84) | - |
| TanDEM-X | august | 4, 4 | - | 3.79 / 5.8 (51) | - | - |
| ICESat-2 | quiet | 11, 6 | 0.35 / 0.9 (91) | 0.74 / 1.9 (204) | 1.07 / 3.2 (176) | - |
| ICESat-2 | storm | 6, 3 | 0.36 / 0.9 (82) | 0.41 / 0.9 (47) | - | - |
| ICESat-2 | held-out | 13, 5 | 0.16 / 0.9 (80) | 0.30 / 2.2 (259) | 1.93 / 18.2 (235) | - |
| ICESat-2 | august | 6, 2 | 1.04 / 1.1 (28) | 4.15 / 4.4 (12) | - | - |

## Sources, with origin and derivation

- **ESA Swarm precise science orbits (SW_OPER_SP3xCOM_2_, TU Delft reduced-dynamic).** Retrieved 2026-09-07. Missions: Swarm A (NORAD 39452), Swarm B (NORAD 39451), Swarm C (NORAD 39453).
- **GRACE-FO Level-1B release 04 from JPL, served by GFZ's ISDC at https://isdc-data.gfz.de/grace-fo/Level-1B/JPL/INSTRUMENT/RL04/ (anonymous HTTPS), daily archives: GNV1B (navigation: reduced-dynamic orbit, Earth-fixed ITRF, one-second states with velocities, GPS time) and THR1B (thruster activation: on-times of the twelve attitude-control and the two orbit-control thrusters).** Retrieved 2026-09-07. Missions: GRACE-FO 1 (C) (NORAD 43476), GRACE-FO 2 (D) (NORAD 43477).
- **Copernicus Sentinel-1A precise orbit ephemerides (AUX_POEORB, produced by the Copernicus POD service), mirrored at https://step.esa.int/auxdata/orbits/Sentinel-1/POEORB/S1A/ (anonymous HTTPS): Earth Explorer XML, Earth-fixed, UTC, ten-second states with velocities, one 26-hour file a day.** Retrieved 2026-09-07. Missions: Sentinel-1A (NORAD 39634).
- **CNES/SSALTO precise orbit ephemerides (POE-F and POE-G standards) for the DORIS satellites, from the International DORIS Service data centre at IGN, ftp://doris.ign.fr/pub/doris/products/orbits/ssa/ (anonymous FTP): SP3, ITRF, TAI, one-minute states with velocities, files of about ten days.** Retrieved 2026-09-07. Missions: CryoSat-2 (NORAD 36508), SARAL (NORAD 39086), Sentinel-3A (NORAD 41335), Sentinel-3B (NORAD 43437), SWOT (NORAD 54754), HY-2C (NORAD 46469), HY-2D (NORAD 48621), Jason-3 (NORAD 41240), Sentinel-6A (NORAD 46984).
- **no reconstructed orbit on an anonymous server; laser ranging only.** Retrieved 2026-09-07. Missions: TerraSAR-X (NORAD 31698), TanDEM-X (NORAD 36605), ICESat-2 (NORAD 43613).
- **Asked for and not obtainable without an account; said, not substituted.** Sentinel-2A and Sentinel-2B: the Copernicus precise orbit products are served through the Copernicus Data Space Ecosystem, which needs a registered account; no anonymous mirror carries Sentinel-2 orbits, and Sentinel-2 carries no laser retroreflector, so there is no truth for it here. ICESat-2 (reconstructed orbit): the precise orbit determination product is distributed inside ATL03 at NSIDC behind an Earthdata login; the laser-ranging normal points are public and are the truth used. TerraSAR-X and TanDEM-X (reconstructed orbit): GFZ's ISDC serves the rapid science orbits anonymously for 2010 to 2020 and nothing for 2024; the laser-ranging normal points are public and are the truth used. GOCE: the precise science orbits (SST_PSO_2, 2009 to 2013) are behind ESA's EO-SSO login on the GOCE online dissemination service; not obtainable anonymously, so not substituted. CHAMP: GFZ's ISDC serves the 2000 to 2010 rapid science orbits anonymously and Space-Track's element-set history reaches back to 2000, so a CHAMP benchmark is possible on CHAMP's own storm windows; it is not part of this fortnight and is recorded as a candidate.
- **Laser ranging.** EUROLAS Data Center (EDC, DGFI-TUM), ILRS normal points in CRD v2, one file per satellite and day (edc.dgfi.tum.de/pub/slr/data/npt_crd_v2), anonymous HTTPS; ILRS SLRF2020 positions and velocities, the ILRS extension of ITRF2020 (SLRF2020_POS+VEL_2025.02.05.snx, ilrs.gsfc.nasa.gov/docs/2025), SINEX; ILRS site eccentricities, marker to optical reference point in XYZ (slrecc.260527.ILRS.xyz.snx, ilrs.gsfc.nasa.gov/docs/2026), SINEX. Derivation: one-way range as the mean of the up and down legs with the light time iterated in TEME; Marini-Murray troposphere; elevation cut 20 degrees; no centre-of-mass correction.
- **Public element sets.** Space-Track gp_history through driftwatch's history backfill, each set propagated with sgp4 to leads [6.0, 12.0, 24.0, 36.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0] hours from its epoch; covariance from the 45 days before each window, coefficient from the 36.

## What this does not show

- One week of sets per window and per mission; a mission's horizon rests on a few dozen sets.
- No published manoeuvre record was found on an anonymous server for the CNES, Copernicus and laser-only missions, so detection decides their exclusions; a burn the detector misses lengthens a residual, and a storm the detector reads as a burn removes a trial. Both directions are possible and neither is measured here.
- The laser comparison bounds the reconstructed orbits at the metre level only, for the reasons above.
- Jason-3 and Sentinel-6A fly at 1,336 km, just above the 1,300 km asked for; they are the top of the range.

_Last updated 07 September 2026._
