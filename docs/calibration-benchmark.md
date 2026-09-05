# Calibration against precise orbits: Swarm A, B and C

Written by `driftwatch validate swarm` on 2026-09-05. Every number here is computed from the per-trial file beside `swarm_benchmark.json`; the reasoning and the caveats are in `docs/methods.md`, "Uncertainty and probability", and on the findings page.

**A trial is one element set.** For every public element set issued in a window, the set is propagated with SGP4 to each lead and compared with ESA's precise science orbit at that instant, in the satellite's radial, in-track, cross-track frame; one residual per set per lead, never one per timestamp, because the residuals along one set's propagation are not independent. `n` at a lead is the number of sets whose propagation had truth there, converged, and spanned no manoeuvre (from ESA's thruster record where it was read; the project's own detection otherwise).

## Windows

| Window | Role | Element sets issued | Truth needed to | Disturbed interval | Note |
| --- | --- | --- | --- | --- | --- |
| quiet | control | 2024-04-20 to 2024-04-27 | 2024-05-04 | none | the quiet control before the May 2024 storm; Kp at or under 4 over 25 to 28 April |
| storm | storm | 2024-05-06 to 2024-05-13 | 2024-05-20 | 2024-05-10 12:00 to 2024-05-13 00:00 | the May 2024 Gannon storm; sets issued from four days before the onset to its end |
| held-out | held-out | 2024-10-06 to 2024-10-13 | 2024-10-20 | 2024-10-10 12:00 to 2024-10-12 00:00 | the 10 to 11 October 2024 storm (Kp 9-), held out from every tuning; nothing was chosen by looking at it |

The held-out window was held out: the covariance and the coefficient used on it are fitted from the history before it, exactly as on the other two, and no threshold in this module was chosen by looking at its result.

## quiet (control)

57 element sets (A: 19, B: 19, C: 19), 570 set-lead pairs; excluded 0 for a truth gap, 0 for a manoeuvre, 0 for an SGP4 error. Covariance source: empirical; coefficient source: history.

Manoeuvres: exclusion by `esa-record`; 0 set-lead pairs excluded (0 sets at some lead, 0 at every lead); the project's own detection flagged 0 -- record and detection agree on 0 excluded and 570 kept; record only 0, detection only 0.

### The residual distribution, absolute, km

| Lead | n | in-track median | in-track p68 | in-track p95 | in-track max | radial median | radial p95 | cross median | cross p95 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 57 | 0.32 | 0.60 | 1.42 | 1.6 | 0.053 | 0.116 | 0.196 | 0.399 |
| 12 h | 57 | 0.51 | 0.84 | 1.69 | 1.8 | 0.043 | 0.185 | 0.179 | 0.251 |
| 24 h | 57 | 0.54 | 0.80 | 1.54 | 2.3 | 0.069 | 0.143 | 0.198 | 0.286 |
| 36 h | 57 | 1.15 | 1.85 | 3.20 | 4.3 | 0.109 | 0.326 | 0.093 | 0.291 |
| 48 h | 57 | 1.57 | 2.25 | 4.92 | 6.6 | 0.195 | 0.351 | 0.140 | 0.254 |
| 72 h | 57 | 3.17 | 4.34 | 8.95 | 12.0 | 0.361 | 0.570 | 0.075 | 0.226 |
| 96 h | 57 | 6.89 | 8.55 | 12.89 | 26.7 | 0.084 | 0.205 | 0.217 | 0.412 |
| 120 h | 57 | 9.91 | 13.97 | 22.95 | 44.2 | 0.620 | 0.765 | 0.131 | 0.256 |
| 144 h | 57 | 14.36 | 22.88 | 39.66 | 67.7 | 0.556 | 0.923 | 0.148 | 0.497 |
| 168 h | 57 | 24.05 | 38.47 | 62.12 | 99.5 | 0.572 | 0.965 | 0.219 | 0.345 |

### Coverage of the empirical covariance

The fraction of residuals inside one and two sigma of the covariance the screening would have carried for the set, per component, against the 68 and 95 per cent a Gaussian claims.

| Lead | n | in-track sigma (median) | inside 1σ | inside 2σ | radial 1σ | radial 2σ | cross 1σ | cross 2σ |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 57 | 0.29 km | 49% | 75% | 72% | 96% | 4% | 4% |
| 12 h | 57 | 0.29 km | 37% | 60% | 63% | 86% | 0% | 2% |
| 24 h | 57 | 1.01 km | 82% | 98% | 93% | 100% | 2% | 7% |
| 36 h | 57 | 2.27 km | 84% | 100% | 70% | 100% | 32% | 44% |
| 48 h | 57 | 4.04 km | 93% | 100% | 75% | 100% | 11% | 23% |
| 72 h | 57 | 9.08 km | 95% | 100% | 61% | 100% | 47% | 74% |
| 96 h | 57 | 15.30 km | 96% | 100% | 100% | 100% | 25% | 44% |
| 120 h | 57 | 21.87 km | 91% | 98% | 88% | 100% | 40% | 86% |
| 144 h | 57 | 29.27 km | 84% | 98% | 95% | 100% | 44% | 74% |
| 168 h | 57 | 37.46 km | 70% | 96% | 96% | 100% | 28% | 70% |

### The storm term with the observed ap

The in-track residual with SGP4 alone against the residual after the storm term's shift, driven by the observed ap and the pre-window coefficient, is subtracted; a positive improvement means the term brought the prediction closer to the truth.

| Lead | n | median \|residual\| raw | median \|residual\| corrected | median \|shift\| | improvement | trials improved |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 57 | 0.32 km | 0.32 km | 0.02 km | -1% | 61% |
| 12 h | 57 | 0.51 km | 0.45 km | 0.10 km | +12% | 39% |
| 24 h | 57 | 0.54 km | 0.59 km | 0.43 km | -10% | 46% |
| 36 h | 57 | 1.15 km | 1.85 km | 1.01 km | -61% | 35% |
| 48 h | 57 | 1.57 km | 3.08 km | 2.05 km | -96% | 37% |
| 72 h | 57 | 3.17 km | 6.04 km | 5.36 km | -91% | 28% |
| 96 h | 57 | 6.89 km | 8.42 km | 10.33 km | -22% | 37% |
| 120 h | 57 | 9.91 km | 12.22 km | 17.81 km | -23% | 37% |
| 144 h | 57 | 14.36 km | 15.60 km | 28.32 km | -9% | 46% |
| 168 h | 57 | 24.05 km | 17.14 km | 41.64 km | +29% | 54% |

### The horizon

Task: in-track residual within 25 km, the screening box's half-width, at the 95% of trials. The residual stays inside the tolerance through **120 hours** of lead and is beyond it at **144 hours** (39.7 km at the 95th percentile).

## storm (storm)

54 element sets (A: 18, B: 19, C: 17), 540 set-lead pairs; excluded 0 for a truth gap, 0 for a manoeuvre, 0 for an SGP4 error. Covariance source: empirical; coefficient source: history.

Manoeuvres: exclusion by `esa-record`; 0 set-lead pairs excluded (0 sets at some lead, 0 at every lead); the project's own detection flagged 0 -- record and detection agree on 0 excluded and 540 kept; record only 0, detection only 0.

### The residual distribution, absolute, km

| Lead | n | in-track median | in-track p68 | in-track p95 | in-track max | radial median | radial p95 | cross median | cross p95 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 54 | 0.50 | 0.68 | 1.23 | 1.6 | 0.069 | 0.129 | 0.212 | 0.416 |
| 12 h | 54 | 0.37 | 0.59 | 0.94 | 1.3 | 0.048 | 0.132 | 0.164 | 0.239 |
| 24 h | 54 | 0.82 | 1.42 | 3.70 | 3.9 | 0.059 | 0.147 | 0.221 | 0.295 |
| 36 h | 54 | 0.70 | 1.39 | 9.89 | 12.3 | 0.085 | 0.224 | 0.105 | 0.369 |
| 48 h | 54 | 2.20 | 5.07 | 15.87 | 20.6 | 0.210 | 0.455 | 0.157 | 0.230 |
| 72 h | 54 | 7.22 | 19.52 | 35.73 | 39.1 | 0.347 | 0.665 | 0.059 | 0.230 |
| 96 h | 54 | 19.86 | 32.97 | 64.15 | 73.2 | 0.086 | 0.618 | 0.211 | 0.370 |
| 120 h | 54 | 37.37 | 52.21 | 100.29 | 111.9 | 0.628 | 0.987 | 0.094 | 0.233 |
| 144 h | 54 | 57.54 | 69.30 | 146.21 | 157.8 | 0.538 | 2.402 | 0.077 | 0.290 |
| 168 h | 54 | 74.56 | 89.25 | 197.49 | 214.3 | 0.475 | 3.517 | 0.221 | 0.350 |

### Coverage of the empirical covariance

The fraction of residuals inside one and two sigma of the covariance the screening would have carried for the set, per component, against the 68 and 95 per cent a Gaussian claims.

| Lead | n | in-track sigma (median) | inside 1σ | inside 2σ | radial 1σ | radial 2σ | cross 1σ | cross 2σ |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 54 | 0.34 km | 33% | 67% | 37% | 93% | 0% | 2% |
| 12 h | 54 | 0.34 km | 44% | 76% | 63% | 93% | 2% | 6% |
| 24 h | 54 | 1.19 km | 67% | 80% | 91% | 100% | 4% | 4% |
| 36 h | 54 | 2.54 km | 76% | 76% | 89% | 100% | 22% | 37% |
| 48 h | 54 | 4.52 km | 67% | 76% | 61% | 100% | 11% | 22% |
| 72 h | 54 | 10.17 km | 52% | 65% | 70% | 100% | 54% | 89% |
| 96 h | 54 | 18.08 km | 44% | 65% | 96% | 100% | 15% | 33% |
| 120 h | 54 | 28.24 km | 33% | 67% | 83% | 96% | 63% | 94% |
| 144 h | 54 | 39.77 km | 35% | 67% | 85% | 89% | 80% | 93% |
| 168 h | 54 | 52.90 km | 35% | 80% | 89% | 89% | 28% | 85% |

### The storm term with the observed ap

The in-track residual with SGP4 alone against the residual after the storm term's shift, driven by the observed ap and the pre-window coefficient, is subtracted; a positive improvement means the term brought the prediction closer to the truth.

| Lead | n | median \|residual\| raw | median \|residual\| corrected | median \|shift\| | improvement | trials improved |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 54 | 0.50 km | 0.53 km | 0.06 km | -8% | 46% |
| 12 h | 54 | 0.37 km | 0.61 km | 0.22 km | -64% | 44% |
| 24 h | 54 | 0.82 km | 1.39 km | 0.98 km | -68% | 24% |
| 36 h | 54 | 0.70 km | 2.70 km | 2.52 km | -287% | 24% |
| 48 h | 54 | 2.20 km | 4.25 km | 4.81 km | -93% | 37% |
| 72 h | 54 | 7.22 km | 8.81 km | 13.38 km | -22% | 48% |
| 96 h | 54 | 19.86 km | 15.86 km | 32.53 km | +20% | 54% |
| 120 h | 54 | 37.37 km | 21.68 km | 54.75 km | +42% | 69% |
| 144 h | 54 | 57.54 km | 29.70 km | 84.37 km | +48% | 74% |
| 168 h | 54 | 74.56 km | 43.66 km | 114.60 km | +41% | 76% |

### The horizon

Task: in-track residual within 25 km, the screening box's half-width, at the 95% of trials. The residual stays inside the tolerance through **48 hours** of lead and is beyond it at **72 hours** (35.7 km at the 95th percentile).

## held-out (held-out)

61 element sets (A: 21, B: 19, C: 21), 610 set-lead pairs; excluded 0 for a truth gap, 36 for a manoeuvre, 0 for an SGP4 error. Covariance source: empirical; coefficient source: history.

Manoeuvres: exclusion by `esa-record`; 36 set-lead pairs excluded (15 sets at some lead, 0 at every lead); the project's own detection flagged 211 -- record and detection agree on 36 excluded and 399 kept; record only 0, detection only 175.

### The residual distribution, absolute, km

| Lead | n | in-track median | in-track p68 | in-track p95 | in-track max | radial median | radial p95 | cross median | cross p95 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 61 | 0.85 | 1.09 | 2.06 | 3.4 | 0.060 | 0.191 | 0.104 | 0.274 |
| 12 h | 61 | 0.91 | 1.39 | 6.02 | 8.8 | 0.148 | 0.258 | 0.152 | 0.315 |
| 24 h | 61 | 1.77 | 3.66 | 18.28 | 27.5 | 0.115 | 0.251 | 0.153 | 0.307 |
| 36 h | 61 | 4.22 | 8.58 | 37.54 | 57.4 | 0.283 | 0.554 | 0.150 | 0.260 |
| 48 h | 61 | 6.95 | 15.87 | 64.38 | 98.9 | 0.168 | 0.666 | 0.168 | 0.266 |
| 72 h | 61 | 15.14 | 35.58 | 141.53 | 219.7 | 0.430 | 2.584 | 0.073 | 0.218 |
| 96 h | 58 | 19.69 | 64.72 | 239.51 | 388.3 | 0.512 | 4.188 | 0.184 | 0.324 |
| 120 h | 54 | 27.07 | 61.57 | 265.92 | 598.8 | 0.587 | 6.235 | 0.156 | 0.383 |
| 144 h | 50 | 38.75 | 104.41 | 432.73 | 863.1 | 0.915 | 16.979 | 0.062 | 0.234 |
| 168 h | 46 | 49.06 | 99.85 | 651.92 | 1168.8 | 0.934 | 31.579 | 0.190 | 0.334 |

### Coverage of the empirical covariance

The fraction of residuals inside one and two sigma of the covariance the screening would have carried for the set, per component, against the 68 and 95 per cent a Gaussian claims.

| Lead | n | in-track sigma (median) | inside 1σ | inside 2σ | radial 1σ | radial 2σ | cross 1σ | cross 2σ |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 61 | 0.56 km | 31% | 75% | 48% | 84% | 3% | 11% |
| 12 h | 61 | 0.56 km | 33% | 62% | 21% | 33% | 5% | 10% |
| 24 h | 61 | 2.08 km | 51% | 69% | 62% | 95% | 11% | 18% |
| 36 h | 61 | 4.45 km | 49% | 62% | 33% | 79% | 18% | 26% |
| 48 h | 61 | 7.25 km | 48% | 67% | 84% | 93% | 20% | 25% |
| 72 h | 61 | 14.45 km | 44% | 66% | 70% | 85% | 39% | 64% |
| 96 h | 58 | 23.56 km | 55% | 64% | 74% | 93% | 12% | 29% |
| 120 h | 54 | 34.43 km | 63% | 69% | 70% | 72% | 35% | 48% |
| 144 h | 50 | 46.94 km | 62% | 68% | 66% | 72% | 58% | 82% |
| 168 h | 46 | 61.00 km | 61% | 70% | 72% | 72% | 24% | 59% |

### The storm term with the observed ap

The in-track residual with SGP4 alone against the residual after the storm term's shift, driven by the observed ap and the pre-window coefficient, is subtracted; a positive improvement means the term brought the prediction closer to the truth.

| Lead | n | median \|residual\| raw | median \|residual\| corrected | median \|shift\| | improvement | trials improved |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 61 | 0.85 km | 0.82 km | 0.07 km | +5% | 49% |
| 12 h | 61 | 0.91 km | 0.73 km | 0.27 km | +20% | 74% |
| 24 h | 61 | 1.77 km | 1.56 km | 1.26 km | +12% | 64% |
| 36 h | 61 | 4.22 km | 2.67 km | 2.88 km | +37% | 67% |
| 48 h | 61 | 6.95 km | 4.92 km | 6.05 km | +29% | 77% |
| 72 h | 61 | 15.14 km | 8.56 km | 15.73 km | +43% | 72% |
| 96 h | 58 | 19.69 km | 14.62 km | 27.26 km | +26% | 69% |
| 120 h | 54 | 27.07 km | 24.57 km | 37.68 km | +9% | 61% |
| 144 h | 50 | 38.75 km | 40.00 km | 54.05 km | -3% | 58% |
| 168 h | 46 | 49.06 km | 55.14 km | 60.10 km | -12% | 54% |

### The horizon

Task: in-track residual within 25 km, the screening box's half-width, at the 95% of trials. The residual stays inside the tolerance through **24 hours** of lead and is beyond it at **36 hours** (37.5 km at the 95th percentile).

## Sources, with origin and derivation

- **ESA Swarm precise science orbits.** https://swarm-diss.eo.esa.int/#swarm/Level2daily/Entire_mission_data/POD/RD/Sat_x — product SW_OPER_SP3xCOM_2_, reduced-dynamic, centre of mass, IGS20 (ITRF2020) frame, ten-second states with velocities, produced by TU Delft (SPC_DUT); SP3-d files, one a day, in zips with an Earth Explorer header. Retrieved 2026-09-05. Derivation: epochs converted from the files' GPS time to UTC (19 s to TAI, then astropy's leap-second table; 18 s in 2024); positions interpolated in the Earth-fixed frame by cubic Hermite on the product's own velocities, rotated to TEME with astropy (IERS Earth-orientation tables as bundled or cached by astropy); the inertial velocity for the RIC frame is the central difference of the rotated positions five seconds either side.
  - Swarm A (quiet): 16 daily files, SW_OPER_SP3ACOM_2__20240418T235942_20240419T235942_0203.ZIP to SW_OPER_SP3ACOM_2__20240503T235942_20240504T235942_0203.ZIP; no days missing.
  - Swarm B (quiet): 16 daily files, SW_OPER_SP3BCOM_2__20240418T235942_20240419T235942_0203.ZIP to SW_OPER_SP3BCOM_2__20240503T235942_20240504T235942_0203.ZIP; no days missing.
  - Swarm C (quiet): 16 daily files, SW_OPER_SP3CCOM_2__20240418T235942_20240419T235942_0203.ZIP to SW_OPER_SP3CCOM_2__20240503T235942_20240504T235942_0203.ZIP; no days missing.
  - Swarm A (storm): 16 daily files, SW_OPER_SP3ACOM_2__20240504T235942_20240505T235942_0203.ZIP to SW_OPER_SP3ACOM_2__20240519T235942_20240520T235942_0203.ZIP; no days missing.
  - Swarm B (storm): 16 daily files, SW_OPER_SP3BCOM_2__20240504T235942_20240505T235942_0203.ZIP to SW_OPER_SP3BCOM_2__20240519T235942_20240520T235942_0203.ZIP; no days missing.
  - Swarm C (storm): 16 daily files, SW_OPER_SP3CCOM_2__20240504T235942_20240505T235942_0203.ZIP to SW_OPER_SP3CCOM_2__20240519T235942_20240520T235942_0203.ZIP; no days missing.
  - Swarm A (held-out): 16 daily files, SW_OPER_SP3ACOM_2__20241004T235942_20241005T235942_0203.ZIP to SW_OPER_SP3ACOM_2__20241019T235942_20241020T235942_0203.ZIP; no days missing.
  - Swarm B (held-out): 16 daily files, SW_OPER_SP3BCOM_2__20241004T235942_20241005T235942_0203.ZIP to SW_OPER_SP3BCOM_2__20241019T235942_20241020T235942_0203.ZIP; no days missing.
  - Swarm C (held-out): 16 daily files, SW_OPER_SP3CCOM_2__20241004T235942_20241005T235942_0203.ZIP to SW_OPER_SP3CCOM_2__20241019T235942_20241020T235942_0203.ZIP; no days missing.
- **Public element sets.** Space-Track gp_history for NORAD 39452 (Swarm A), 39451 (Swarm B), 39453 (Swarm C), through driftwatch's history backfill (data/cache/spacetrack/gp_history, data/history). Retrieved 2026-09-05. Derivation: each set propagated with sgp4 2.27 (WGS72, mode i) to leads [6.0, 12.0, 24.0, 36.0, 48.0, 72.0, 96.0, 120.0, 144.0, 168.0] hours from its own epoch; the empirical covariance fitted per satellite from the 45 days of sets before each window (driftwatch.risk.covariance, the model the screening uses); the ballistic coefficient fitted from the 36 days before each window (driftwatch.drag.ballistic).
- **Observed geomagnetic activity.** CelesTrak SW-All.csv (observed ap and Kp, F10.7), through driftwatch.weather; nothing forecast enters the benchmark. Retrieved 2026-09-05. Derivation: the storm term (driftwatch.storm.term.object_shift via driftwatch.storm.validation.predicted_shifts) driven by NRLMSIS 2.1 with the observed ap over each trial's lead, from the trial set's own epoch, with the pre-window coefficient.
- **Manoeuvre intervals.** ESA Swarm Level 1b spacecraft dynamics, SW_OPER_SC_xDYN_1B (Level 1b spacecraft dynamics, daily CDF; swarm/Level1b/Entire_mission_data/SC_xDYN), retrieved from https://swarm-diss.eo.esa.int/: per-second on-times of the twelve thrusters (dt_thr) and the nominal force of the orbit-control thrusters that fired (f_thr); each day's header Maneuver_Information ids are kept beside it. Retrieved 2026-09-05. Derivation: an orbit manoeuvre is a run of seconds with non-zero orbit-control force, merged across gaps under 600 s; a trial is excluded when one falls between 24 h before its element set's epoch and the lead's time; thruster on-time with no orbit-control force is attitude control, counted and not excluded. Cross-check, deciding nothing: the project's own detection -- a step in the orbit-mean semi-major axis of the precise orbit beyond 20 m and 6 robust sigmas between consecutive orbits, and driftwatch.drag.ballistic.manoeuvre_intervals on the element sets.
  - Swarm A (quiet): 16 daily files, SW_OPER_SC_ADYN_1B_20240419T000000_20240419T235959_0601.CDF.ZIP to SW_OPER_SC_ADYN_1B_20240504T000000_20240504T235959_0601.CDF.ZIP; no days missing; 0 orbit manoeuvre(s): none; 0 s of orbit-control thrust; 105 attitude pulses.
  - Swarm B (quiet): 16 daily files, SW_OPER_SC_BDYN_1B_20240419T000000_20240419T235959_0601.CDF.ZIP to SW_OPER_SC_BDYN_1B_20240504T000000_20240504T235959_0601.CDF.ZIP; no days missing; 0 orbit manoeuvre(s): none; 0 s of orbit-control thrust; 105 attitude pulses.
  - Swarm C (quiet): 16 daily files, SW_OPER_SC_CDYN_1B_20240419T000000_20240419T235959_0601.CDF.ZIP to SW_OPER_SC_CDYN_1B_20240504T000000_20240504T235959_0601.CDF.ZIP; no days missing; 0 orbit manoeuvre(s): none; 0 s of orbit-control thrust; 133 attitude pulses.
  - Swarm A (storm): 16 daily files, SW_OPER_SC_ADYN_1B_20240505T000000_20240505T235959_0601.CDF.ZIP to SW_OPER_SC_ADYN_1B_20240520T000000_20240520T235959_0601.CDF.ZIP; no days missing; 0 orbit manoeuvre(s): none; 0 s of orbit-control thrust; 121 attitude pulses.
  - Swarm B (storm): 16 daily files, SW_OPER_SC_BDYN_1B_20240505T000000_20240505T235959_0601.CDF.ZIP to SW_OPER_SC_BDYN_1B_20240520T000000_20240520T235959_0601.CDF.ZIP; no days missing; 0 orbit manoeuvre(s): none; 0 s of orbit-control thrust; 61 attitude pulses.
  - Swarm C (storm): 16 daily files, SW_OPER_SC_CDYN_1B_20240505T000000_20240505T235959_0601.CDF.ZIP to SW_OPER_SC_CDYN_1B_20240520T000000_20240520T235959_0601.CDF.ZIP; no days missing; 0 orbit manoeuvre(s): none; 0 s of orbit-control thrust; 124 attitude pulses.
  - Swarm A (held-out): 16 daily files, SW_OPER_SC_ADYN_1B_20241005T000000_20241005T235959_0601.CDF.ZIP to SW_OPER_SC_ADYN_1B_20241020T000000_20241020T235959_0601.CDF.ZIP; no days missing; 2 orbit manoeuvre(s): 2024-10-15T21:07 to 2024-10-15T21:08; 2024-10-15T21:54 to 2024-10-15T21:54; 198 s of orbit-control thrust; 98 attitude pulses.
  - Swarm B (held-out): 16 daily files, SW_OPER_SC_BDYN_1B_20241005T000000_20241005T235959_0601.CDF.ZIP to SW_OPER_SC_BDYN_1B_20241020T000000_20241020T235959_0601.CDF.ZIP; no days missing; 1 orbit manoeuvre(s): 2024-10-17T22:58 to 2024-10-17T23:23; 260.4 s of orbit-control thrust; 89 attitude pulses.
  - Swarm C (held-out): 16 daily files, SW_OPER_SC_CDYN_1B_20241005T000000_20241005T235959_0601.CDF.ZIP to SW_OPER_SC_CDYN_1B_20241020T000000_20241020T235959_0601.CDF.ZIP; no days missing; 0 orbit manoeuvre(s): none; 0 s of orbit-control thrust; 106 attitude pulses.
- **Not used, noted for later.** Swarm thermospheric density from POD and accelerometer, SW_OPER_DNSxPOD_2_ (TU Delft thermospheric density from POD; swarm/Level2daily/Entire_mission_data/DNS): would separate the atmosphere's error from the object's response in the storm-term comparison; not part of this week
- **Software.** driftwatch (this repository), sgp4 2.27, astropy 8.0.1, numpy 2.5.2, pandas 3.0.5

