# Orbital-component angular-error thresholds

**Correction.** The former crossing-horizon and position-horizon interpretations are withdrawn. An orbital cross-track residual does not determine whether a moving sky track enters a fixed beam. The radial and in-track residuals, observer rotation, range, pointing and distance from the beam edge all affect the answer. The stored component arithmetic below does not validate beam crossing or timing.

These rows transform the stored RIC residuals using arctan2(|C|, mean altitude) and arctan2(|I|, mean altitude), in degrees. They are representative component scales, not an upper bound on complete topocentric error. |I| divided by the circular orbital speed is an orbital phase-time scale, not the error in beam-entry time. The p95 is NumPy's linearly interpolated sample quantile.

The threshold diagnostic requires at least 95% of stored rows to be strictly below one third of the stated scalar beam width. That arbitrary fraction is distinct from a half-power crossing boundary, depends on the chosen fraction and does not supply a calibrated 95% predictive probability. Repeated leads from an element set are dependent.

Above 3 GHz the primary scalar width is the minimum diametric width of the measured half-power contour through the sampled image peak. Cuts are sampled every 0.5 degree in orientation and both first half-power roots are refined. This declared convention retains the measured frequency dependence and has no wavelength-scaling fallback. Actual channel frequencies, source hashes and the maximum diametric-width sensitivity are in the JSON. The full track comparison uses the complete 2D pattern, not this scalar width. [Published MeerKAT Jones patterns](https://doi.org/10.48479/wdb0-h061).

Below 3 GHz this component diagnostic retains the historical 57.5 arcmin × 1500/frequency_MHz L-band relation and its labelled UHF/S0 extrapolations. The full topocentric comparison uses measured patterns in all six channels. The former analytic 3500 MHz calculation is retained only as an explicit historical comparison in the JSON. See [radio lane](radio-lane.md).

## Stored population

Source: `data/radio/benchmark_trials.csv`. The table covers the four named 2024 windows only. Element epochs are not publication timestamps. These results describe the qualified reference missions and analysed manoeuvre exclusions; altitude overlap alone does not justify transfer to debris, constellation spacecraft or other missions.

| Altitude band | Spacecraft | Mean altitude of the sets | Sets, quiet | Sets, May 2024 | Sets, October 2024 | Sets, August 2024 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 400-600 km | GRACE-FO 1 (C), GRACE-FO 2 (D), Swarm A, Swarm B, Swarm C | 460 to 507 km | 95 | 91 | 100 | 93 |
| 600-750 km | CryoSat-2, Sentinel-1A | 696 to 719 km | 45 | 41 | 42 | 39 |
| 750-850 km | SARAL, Sentinel-3A, Sentinel-3B | 783 to 803 km | 57 | 65 | 51 | 60 |
| 850-1000 km | HY-2C, HY-2D, SWOT | 893 to 952 km | 78 | 77 | 60 | 65 |
| 1000-1400 km | Jason-3, Sentinel-6A | 1338 to 1338 km | 37 | 30 | 32 | 35 |

## Stated scalar beam widths

| Receiver / actual frequency | Scalar width (arcmin) | Component threshold width/3 (arcmin) | Width source |
| --- | ---: | ---: | --- |
| UHF 816 MHz | 105.699 | 35.233 | historical analytic L-band relation or labelled extrapolation |
| L 1284 MHz | 67.173 | 22.391 | historical analytic L-band relation or labelled extrapolation |
| L 1712 MHz | 50.380 | 16.793 | historical analytic L-band relation or labelled extrapolation |
| S0 2187.5 MHz | 39.429 | 13.143 | historical analytic L-band relation or labelled extrapolation |
| S4 3062.5 MHz | 33.447 | 11.149 | measured Jones half-power contour: minimum sampled diametric width through its sampled peak |
| S4 3499.14551 MHz | 26.421 | 8.807 | measured Jones half-power contour: minimum sampled diametric width through its sampled peak |

## 400-600 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 95, 2.7', 9.7', 0.18 s | 91, 3.0', 9.9', 0.18 s | 100, 2.0', 16.9', 0.31 s | 93, 2.9', 9.6', 0.17 s |
| 12 h | 95, 1.8', 11.7', 0.22 s | 91, 1.7', 9.3', 0.17 s | 100, 2.3', 45.0', 0.79 s | 93, 1.8', 14.6', 0.26 s |
| 24 h | 95, 2.1', 11.3', 0.20 s | 91, 2.1', 26.0', 0.47 s | 100, 2.3', 129.9', 2.34 s | 93, 2.3', 34.6', 0.64 s |
| 36 h | 95, 2.7', 22.6', 0.41 s | 91, 2.7', 65.4', 1.18 s | 100, 1.9', 246.8', 4.46 s | 93, 2.2', 68.2', 1.27 s |
| 2 d | 95, 1.7', 32.6', 0.59 s | 91, 1.6', 105.6', 1.94 s | 100, 1.9', 399.4', 7.23 s | 93, 1.8', 121.9', 2.27 s |
| 3 d | 95, 1.6', 55.4', 1.00 s | 88, 1.6', 250.5', 4.55 s | 100, 2.7', 827.0', 15.20 s | 93, 2.1', 270.5', 5.05 s |
| 4 d | 95, 2.8', 89.2', 1.63 s | 86, 2.7', 425.0', 8.21 s | 97, 2.4', 1383.5', 26.37 s | 93, 2.1', 486.2', 9.11 s |
| 5 d | 95, 1.7', 161.2', 2.96 s | 84, 1.5', 675.3', 13.01 s | 93, 2.5', 1678.6', 32.63 s | 93, 2.5', 754.5', 14.28 s |
| 6 d | 95, 3.2', 257.4', 4.80 s | 81, 2.2', 965.5', 18.39 s | 89, 3.4', 2342.7', 50.15 s | 93, 2.6', 1086.9', 20.68 s |
| 7 d | 95, 2.4', 422.0', 7.66 s | 78, 2.5', 1279.3', 25.08 s | 85, 2.4', 2957.9', 72.17 s | 93, 2.5', 1474.3', 28.86 s |

At 400-600 km, the largest stored cross-track component p95 is 3.394 arcmin at mean-altitude range. This is not a sky-track-normal error.

No beam-entry or beam-timing accuracy follows from this component table. Ages below the first sampled lead are unmeasured; an exhausted window is not a threshold failure.

UHF 816 MHz, in-track component threshold: quiet: 2 d, first failed sample 3 d; May 2024: 24 h, first failed sample 36 h; October 2024: 6 h, first failed sample 12 h; August 2024: 12 h, first failed sample 24 h.

L 1284 MHz, in-track component threshold: quiet: 24 h, first failed sample 36 h; May 2024: 12 h, first failed sample 24 h; October 2024: 6 h, first failed sample 12 h; August 2024: 12 h, first failed sample 24 h.

L 1712 MHz, in-track component threshold: quiet: 24 h, first failed sample 36 h; May 2024: 12 h, first failed sample 24 h; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 12 h, first failed sample 24 h.

S0 2187.5 MHz, in-track component threshold: quiet: 24 h, first failed sample 36 h; May 2024: 12 h, first failed sample 24 h; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 6 h, first failed sample 12 h.

S4 3062.5 MHz, in-track component threshold: quiet: 6 h, first failed sample 12 h; May 2024: 12 h, first failed sample 24 h; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 6 h, first failed sample 12 h.

S4 3499.14551 MHz, in-track component threshold: quiet: no sampled lead passed, first failed sample 6 h; May 2024: no sampled lead passed, first failed sample 6 h; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: no sampled lead passed, first failed sample 6 h.

| Component / receiver | Window | Last consecutive passing sampled lead | First failed sample | Last available / n | End reason |
| --- | --- | --- | --- | --- | --- |
| cross_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 95 | data_exhausted |
| cross_track / UHF 816 MHz | May 2024 | 7 d | - | 7 d / 78 | data_exhausted |
| cross_track / UHF 816 MHz | October 2024 | 7 d | - | 7 d / 85 | data_exhausted |
| cross_track / UHF 816 MHz | August 2024 | 7 d | - | 7 d / 93 | data_exhausted |
| cross_track / L 1284 MHz | quiet | 7 d | - | 7 d / 95 | data_exhausted |
| cross_track / L 1284 MHz | May 2024 | 7 d | - | 7 d / 78 | data_exhausted |
| cross_track / L 1284 MHz | October 2024 | 7 d | - | 7 d / 85 | data_exhausted |
| cross_track / L 1284 MHz | August 2024 | 7 d | - | 7 d / 93 | data_exhausted |
| cross_track / L 1712 MHz | quiet | 7 d | - | 7 d / 95 | data_exhausted |
| cross_track / L 1712 MHz | May 2024 | 7 d | - | 7 d / 78 | data_exhausted |
| cross_track / L 1712 MHz | October 2024 | 7 d | - | 7 d / 85 | data_exhausted |
| cross_track / L 1712 MHz | August 2024 | 7 d | - | 7 d / 93 | data_exhausted |
| cross_track / S0 2187.5 MHz | quiet | 7 d | - | 7 d / 95 | data_exhausted |
| cross_track / S0 2187.5 MHz | May 2024 | 7 d | - | 7 d / 78 | data_exhausted |
| cross_track / S0 2187.5 MHz | October 2024 | 7 d | - | 7 d / 85 | data_exhausted |
| cross_track / S0 2187.5 MHz | August 2024 | 7 d | - | 7 d / 93 | data_exhausted |
| cross_track / S4 3062.5 MHz | quiet | 7 d | - | 7 d / 95 | data_exhausted |
| cross_track / S4 3062.5 MHz | May 2024 | 7 d | - | 7 d / 78 | data_exhausted |
| cross_track / S4 3062.5 MHz | October 2024 | 7 d | - | 7 d / 85 | data_exhausted |
| cross_track / S4 3062.5 MHz | August 2024 | 7 d | - | 7 d / 93 | data_exhausted |
| cross_track / S4 3499.14551 MHz | quiet | 7 d | - | 7 d / 95 | data_exhausted |
| cross_track / S4 3499.14551 MHz | May 2024 | 7 d | - | 7 d / 78 | data_exhausted |
| cross_track / S4 3499.14551 MHz | October 2024 | 7 d | - | 7 d / 85 | data_exhausted |
| cross_track / S4 3499.14551 MHz | August 2024 | 7 d | - | 7 d / 93 | data_exhausted |
| in_track / UHF 816 MHz | quiet | 2 d | 3 d | 7 d / 95 | threshold_failure |
| in_track / UHF 816 MHz | May 2024 | 24 h | 36 h | 7 d / 78 | threshold_failure |
| in_track / UHF 816 MHz | October 2024 | 6 h | 12 h | 7 d / 85 | threshold_failure |
| in_track / UHF 816 MHz | August 2024 | 12 h | 24 h | 7 d / 93 | threshold_failure |
| in_track / L 1284 MHz | quiet | 24 h | 36 h | 7 d / 95 | threshold_failure |
| in_track / L 1284 MHz | May 2024 | 12 h | 24 h | 7 d / 78 | threshold_failure |
| in_track / L 1284 MHz | October 2024 | 6 h | 12 h | 7 d / 85 | threshold_failure |
| in_track / L 1284 MHz | August 2024 | 12 h | 24 h | 7 d / 93 | threshold_failure |
| in_track / L 1712 MHz | quiet | 24 h | 36 h | 7 d / 95 | threshold_failure |
| in_track / L 1712 MHz | May 2024 | 12 h | 24 h | 7 d / 78 | threshold_failure |
| in_track / L 1712 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 85 | threshold_failure |
| in_track / L 1712 MHz | August 2024 | 12 h | 24 h | 7 d / 93 | threshold_failure |
| in_track / S0 2187.5 MHz | quiet | 24 h | 36 h | 7 d / 95 | threshold_failure |
| in_track / S0 2187.5 MHz | May 2024 | 12 h | 24 h | 7 d / 78 | threshold_failure |
| in_track / S0 2187.5 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 85 | threshold_failure |
| in_track / S0 2187.5 MHz | August 2024 | 6 h | 12 h | 7 d / 93 | threshold_failure |
| in_track / S4 3062.5 MHz | quiet | 6 h | 12 h | 7 d / 95 | threshold_failure |
| in_track / S4 3062.5 MHz | May 2024 | 12 h | 24 h | 7 d / 78 | threshold_failure |
| in_track / S4 3062.5 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 85 | threshold_failure |
| in_track / S4 3062.5 MHz | August 2024 | 6 h | 12 h | 7 d / 93 | threshold_failure |
| in_track / S4 3499.14551 MHz | quiet | no sampled lead passed | 6 h | 7 d / 95 | threshold_failure |
| in_track / S4 3499.14551 MHz | May 2024 | no sampled lead passed | 6 h | 7 d / 78 | threshold_failure |
| in_track / S4 3499.14551 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 85 | threshold_failure |
| in_track / S4 3499.14551 MHz | August 2024 | no sampled lead passed | 6 h | 7 d / 93 | threshold_failure |

## 600-750 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 45, 1.6', 5.8', 0.16 s | 41, 1.4', 5.7', 0.15 s | 42, 1.4', 11.4', 0.31 s | 39, 1.2', 7.1', 0.20 s |
| 12 h | 45, 1.6', 6.1', 0.16 s | 39, 1.5', 6.5', 0.18 s | 41, 1.4', 22.1', 0.59 s | 37, 1.1', 9.4', 0.26 s |
| 24 h | 44, 1.2', 15.9', 0.43 s | 34, 1.3', 9.2', 0.25 s | 39, 1.0', 33.1', 0.89 s | 34, 1.0', 11.4', 0.31 s |
| 36 h | 42, 1.5', 24.6', 0.66 s | 32, 1.3', 9.9', 0.27 s | 37, 1.5', 47.4', 1.28 s | 29, 1.1', 19.0', 0.51 s |
| 2 d | 41, 1.8', 37.8', 1.02 s | 29, 1.6', 13.7', 0.37 s | 33, 1.3', 49.4', 1.33 s | 25, 1.2', 30.4', 0.82 s |
| 3 d | 38, 2.1', 56.2', 1.52 s | 24, 1.9', 12.0', 0.34 s | 27, 1.6', 54.6', 1.48 s | 19, 1.6', 36.2', 0.98 s |
| 4 d | 36, 1.3', 83.2', 2.24 s | 20, 1.5', 18.2', 0.51 s | 22, 1.4', 56.0', 1.51 s | 12, 1.0', 43.1', 1.16 s |
| 5 d | 35, 1.5', 103.4', 2.79 s | 15, 1.3', 33.8', 0.94 s | 18, 1.4', 104.6', 2.82 s | 4, 0.4', 34.8', 0.94 s |
| 6 d | 35, 1.8', 129.1', 3.48 s | 12, 1.6', 40.8', 1.14 s | 13, 1.9', 79.2', 2.18 s | - |
| 7 d | 35, 2.3', 158.2', 4.27 s | 12, 1.2', 64.1', 1.79 s | 8, 1.8', 103.9', 2.90 s | - |

At 600-750 km, the largest stored cross-track component p95 is 2.281 arcmin at mean-altitude range. This is not a sky-track-normal error.

No beam-entry or beam-timing accuracy follows from this component table. Ages below the first sampled lead are unmeasured; an exhausted window is not a threshold failure.

UHF 816 MHz, in-track component threshold: quiet: 36 h, first failed sample 2 d; May 2024: 5 d, first failed sample 6 d; October 2024: 24 h, first failed sample 36 h; August 2024: 2 d, first failed sample 3 d.

L 1284 MHz, in-track component threshold: quiet: 24 h, first failed sample 36 h; May 2024: 4 d, first failed sample 5 d; October 2024: 12 h, first failed sample 24 h; August 2024: 36 h, first failed sample 2 d.

L 1712 MHz, in-track component threshold: quiet: 24 h, first failed sample 36 h; May 2024: 3 d, first failed sample 4 d; October 2024: 6 h, first failed sample 12 h; August 2024: 24 h, first failed sample 36 h.

S0 2187.5 MHz, in-track component threshold: quiet: 12 h, first failed sample 24 h; May 2024: 36 h, first failed sample 2 d; October 2024: 6 h, first failed sample 12 h; August 2024: 24 h, first failed sample 36 h.

S4 3062.5 MHz, in-track component threshold: quiet: 12 h, first failed sample 24 h; May 2024: 36 h, first failed sample 2 d; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 12 h, first failed sample 24 h.

S4 3499.14551 MHz, in-track component threshold: quiet: 12 h, first failed sample 24 h; May 2024: 12 h, first failed sample 24 h; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 6 h, first failed sample 12 h.

| Component / receiver | Window | Last consecutive passing sampled lead | First failed sample | Last available / n | End reason |
| --- | --- | --- | --- | --- | --- |
| cross_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / UHF 816 MHz | May 2024 | 7 d | - | 7 d / 12 | data_exhausted |
| cross_track / UHF 816 MHz | October 2024 | 7 d | - | 7 d / 8 | data_exhausted |
| cross_track / UHF 816 MHz | August 2024 | 5 d | - | 5 d / 4 | data_exhausted |
| cross_track / L 1284 MHz | quiet | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / L 1284 MHz | May 2024 | 7 d | - | 7 d / 12 | data_exhausted |
| cross_track / L 1284 MHz | October 2024 | 7 d | - | 7 d / 8 | data_exhausted |
| cross_track / L 1284 MHz | August 2024 | 5 d | - | 5 d / 4 | data_exhausted |
| cross_track / L 1712 MHz | quiet | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / L 1712 MHz | May 2024 | 7 d | - | 7 d / 12 | data_exhausted |
| cross_track / L 1712 MHz | October 2024 | 7 d | - | 7 d / 8 | data_exhausted |
| cross_track / L 1712 MHz | August 2024 | 5 d | - | 5 d / 4 | data_exhausted |
| cross_track / S0 2187.5 MHz | quiet | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / S0 2187.5 MHz | May 2024 | 7 d | - | 7 d / 12 | data_exhausted |
| cross_track / S0 2187.5 MHz | October 2024 | 7 d | - | 7 d / 8 | data_exhausted |
| cross_track / S0 2187.5 MHz | August 2024 | 5 d | - | 5 d / 4 | data_exhausted |
| cross_track / S4 3062.5 MHz | quiet | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / S4 3062.5 MHz | May 2024 | 7 d | - | 7 d / 12 | data_exhausted |
| cross_track / S4 3062.5 MHz | October 2024 | 7 d | - | 7 d / 8 | data_exhausted |
| cross_track / S4 3062.5 MHz | August 2024 | 5 d | - | 5 d / 4 | data_exhausted |
| cross_track / S4 3499.14551 MHz | quiet | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / S4 3499.14551 MHz | May 2024 | 7 d | - | 7 d / 12 | data_exhausted |
| cross_track / S4 3499.14551 MHz | October 2024 | 7 d | - | 7 d / 8 | data_exhausted |
| cross_track / S4 3499.14551 MHz | August 2024 | 5 d | - | 5 d / 4 | data_exhausted |
| in_track / UHF 816 MHz | quiet | 36 h | 2 d | 7 d / 35 | threshold_failure |
| in_track / UHF 816 MHz | May 2024 | 5 d | 6 d | 7 d / 12 | threshold_failure |
| in_track / UHF 816 MHz | October 2024 | 24 h | 36 h | 7 d / 8 | threshold_failure |
| in_track / UHF 816 MHz | August 2024 | 2 d | 3 d | 5 d / 4 | threshold_failure |
| in_track / L 1284 MHz | quiet | 24 h | 36 h | 7 d / 35 | threshold_failure |
| in_track / L 1284 MHz | May 2024 | 4 d | 5 d | 7 d / 12 | threshold_failure |
| in_track / L 1284 MHz | October 2024 | 12 h | 24 h | 7 d / 8 | threshold_failure |
| in_track / L 1284 MHz | August 2024 | 36 h | 2 d | 5 d / 4 | threshold_failure |
| in_track / L 1712 MHz | quiet | 24 h | 36 h | 7 d / 35 | threshold_failure |
| in_track / L 1712 MHz | May 2024 | 3 d | 4 d | 7 d / 12 | threshold_failure |
| in_track / L 1712 MHz | October 2024 | 6 h | 12 h | 7 d / 8 | threshold_failure |
| in_track / L 1712 MHz | August 2024 | 24 h | 36 h | 5 d / 4 | threshold_failure |
| in_track / S0 2187.5 MHz | quiet | 12 h | 24 h | 7 d / 35 | threshold_failure |
| in_track / S0 2187.5 MHz | May 2024 | 36 h | 2 d | 7 d / 12 | threshold_failure |
| in_track / S0 2187.5 MHz | October 2024 | 6 h | 12 h | 7 d / 8 | threshold_failure |
| in_track / S0 2187.5 MHz | August 2024 | 24 h | 36 h | 5 d / 4 | threshold_failure |
| in_track / S4 3062.5 MHz | quiet | 12 h | 24 h | 7 d / 35 | threshold_failure |
| in_track / S4 3062.5 MHz | May 2024 | 36 h | 2 d | 7 d / 12 | threshold_failure |
| in_track / S4 3062.5 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 8 | threshold_failure |
| in_track / S4 3062.5 MHz | August 2024 | 12 h | 24 h | 5 d / 4 | threshold_failure |
| in_track / S4 3499.14551 MHz | quiet | 12 h | 24 h | 7 d / 35 | threshold_failure |
| in_track / S4 3499.14551 MHz | May 2024 | 12 h | 24 h | 7 d / 12 | threshold_failure |
| in_track / S4 3499.14551 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 8 | threshold_failure |
| in_track / S4 3499.14551 MHz | August 2024 | 6 h | 12 h | 5 d / 4 | threshold_failure |

## 750-850 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 57, 0.6', 4.7', 0.15 s | 65, 0.9', 4.7', 0.14 s | 51, 0.9', 19.8', 0.62 s | 60, 0.9', 6.9', 0.22 s |
| 12 h | 56, 1.2', 3.3', 0.10 s | 63, 1.2', 6.2', 0.19 s | 50, 1.1', 23.3', 0.73 s | 58, 1.4', 7.6', 0.23 s |
| 24 h | 52, 1.3', 4.2', 0.13 s | 61, 1.3', 7.0', 0.22 s | 50, 1.1', 28.4', 0.89 s | 53, 1.2', 6.3', 0.20 s |
| 36 h | 49, 0.8', 5.0', 0.16 s | 58, 0.9', 6.4', 0.20 s | 48, 0.8', 38.9', 1.22 s | 50, 0.9', 8.0', 0.25 s |
| 2 d | 46, 1.4', 6.4', 0.19 s | 56, 1.1', 9.8', 0.30 s | 47, 1.4', 37.3', 1.17 s | 46, 1.1', 7.9', 0.24 s |
| 3 d | 40, 1.5', 8.1', 0.25 s | 53, 1.4', 16.9', 0.53 s | 45, 1.2', 30.4', 0.95 s | 40, 1.1', 14.5', 0.45 s |
| 4 d | 33, 1.5', 13.0', 0.41 s | 46, 1.8', 24.8', 0.78 s | 43, 1.4', 46.6', 1.46 s | 34, 1.3', 20.9', 0.65 s |
| 5 d | 30, 1.5', 20.4', 0.64 s | 40, 1.1', 35.1', 1.10 s | 41, 1.9', 66.2', 2.08 s | 25, 1.4', 27.9', 0.85 s |
| 6 d | 29, 1.7', 19.0', 0.59 s | 33, 1.8', 48.8', 1.53 s | 38, 1.0', 133.9', 4.16 s | 19, 0.6', 40.5', 1.24 s |
| 7 d | 29, 1.3', 27.4', 0.85 s | 25, 1.3', 40.8', 1.27 s | 33, 2.3', 74.1', 2.29 s | 18, 1.7', 56.4', 1.72 s |

At 750-850 km, the largest stored cross-track component p95 is 2.274 arcmin at mean-altitude range. This is not a sky-track-normal error.

No beam-entry or beam-timing accuracy follows from this component table. Ages below the first sampled lead are unmeasured; an exhausted window is not a threshold failure.

UHF 816 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=29); May 2024: 5 d, first failed sample 6 d; October 2024: 24 h, first failed sample 36 h; August 2024: 5 d, first failed sample 6 d.

L 1284 MHz, in-track component threshold: quiet: 6 d, first failed sample 7 d; May 2024: 3 d, first failed sample 4 d; October 2024: 6 h, first failed sample 12 h; August 2024: 3 d, first failed sample 4 d.

L 1712 MHz, in-track component threshold: quiet: 4 d, first failed sample 5 d; May 2024: 2 d, first failed sample 3 d; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 3 d, first failed sample 4 d.

S0 2187.5 MHz, in-track component threshold: quiet: 3 d, first failed sample 4 d; May 2024: 2 d, first failed sample 3 d; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 2 d, first failed sample 3 d.

S4 3062.5 MHz, in-track component threshold: quiet: 3 d, first failed sample 4 d; May 2024: 2 d, first failed sample 3 d; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 2 d, first failed sample 3 d.

S4 3499.14551 MHz, in-track component threshold: quiet: 3 d, first failed sample 4 d; May 2024: 36 h, first failed sample 2 d; October 2024: no sampled lead passed, first failed sample 6 h; August 2024: 2 d, first failed sample 3 d.

| Component / receiver | Window | Last consecutive passing sampled lead | First failed sample | Last available / n | End reason |
| --- | --- | --- | --- | --- | --- |
| cross_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 29 | data_exhausted |
| cross_track / UHF 816 MHz | May 2024 | 7 d | - | 7 d / 25 | data_exhausted |
| cross_track / UHF 816 MHz | October 2024 | 7 d | - | 7 d / 33 | data_exhausted |
| cross_track / UHF 816 MHz | August 2024 | 7 d | - | 7 d / 18 | data_exhausted |
| cross_track / L 1284 MHz | quiet | 7 d | - | 7 d / 29 | data_exhausted |
| cross_track / L 1284 MHz | May 2024 | 7 d | - | 7 d / 25 | data_exhausted |
| cross_track / L 1284 MHz | October 2024 | 7 d | - | 7 d / 33 | data_exhausted |
| cross_track / L 1284 MHz | August 2024 | 7 d | - | 7 d / 18 | data_exhausted |
| cross_track / L 1712 MHz | quiet | 7 d | - | 7 d / 29 | data_exhausted |
| cross_track / L 1712 MHz | May 2024 | 7 d | - | 7 d / 25 | data_exhausted |
| cross_track / L 1712 MHz | October 2024 | 7 d | - | 7 d / 33 | data_exhausted |
| cross_track / L 1712 MHz | August 2024 | 7 d | - | 7 d / 18 | data_exhausted |
| cross_track / S0 2187.5 MHz | quiet | 7 d | - | 7 d / 29 | data_exhausted |
| cross_track / S0 2187.5 MHz | May 2024 | 7 d | - | 7 d / 25 | data_exhausted |
| cross_track / S0 2187.5 MHz | October 2024 | 7 d | - | 7 d / 33 | data_exhausted |
| cross_track / S0 2187.5 MHz | August 2024 | 7 d | - | 7 d / 18 | data_exhausted |
| cross_track / S4 3062.5 MHz | quiet | 7 d | - | 7 d / 29 | data_exhausted |
| cross_track / S4 3062.5 MHz | May 2024 | 7 d | - | 7 d / 25 | data_exhausted |
| cross_track / S4 3062.5 MHz | October 2024 | 7 d | - | 7 d / 33 | data_exhausted |
| cross_track / S4 3062.5 MHz | August 2024 | 7 d | - | 7 d / 18 | data_exhausted |
| cross_track / S4 3499.14551 MHz | quiet | 7 d | - | 7 d / 29 | data_exhausted |
| cross_track / S4 3499.14551 MHz | May 2024 | 7 d | - | 7 d / 25 | data_exhausted |
| cross_track / S4 3499.14551 MHz | October 2024 | 7 d | - | 7 d / 33 | data_exhausted |
| cross_track / S4 3499.14551 MHz | August 2024 | 7 d | - | 7 d / 18 | data_exhausted |
| in_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 29 | data_exhausted |
| in_track / UHF 816 MHz | May 2024 | 5 d | 6 d | 7 d / 25 | threshold_failure |
| in_track / UHF 816 MHz | October 2024 | 24 h | 36 h | 7 d / 33 | threshold_failure |
| in_track / UHF 816 MHz | August 2024 | 5 d | 6 d | 7 d / 18 | threshold_failure |
| in_track / L 1284 MHz | quiet | 6 d | 7 d | 7 d / 29 | threshold_failure |
| in_track / L 1284 MHz | May 2024 | 3 d | 4 d | 7 d / 25 | threshold_failure |
| in_track / L 1284 MHz | October 2024 | 6 h | 12 h | 7 d / 33 | threshold_failure |
| in_track / L 1284 MHz | August 2024 | 3 d | 4 d | 7 d / 18 | threshold_failure |
| in_track / L 1712 MHz | quiet | 4 d | 5 d | 7 d / 29 | threshold_failure |
| in_track / L 1712 MHz | May 2024 | 2 d | 3 d | 7 d / 25 | threshold_failure |
| in_track / L 1712 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 33 | threshold_failure |
| in_track / L 1712 MHz | August 2024 | 3 d | 4 d | 7 d / 18 | threshold_failure |
| in_track / S0 2187.5 MHz | quiet | 3 d | 4 d | 7 d / 29 | threshold_failure |
| in_track / S0 2187.5 MHz | May 2024 | 2 d | 3 d | 7 d / 25 | threshold_failure |
| in_track / S0 2187.5 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 33 | threshold_failure |
| in_track / S0 2187.5 MHz | August 2024 | 2 d | 3 d | 7 d / 18 | threshold_failure |
| in_track / S4 3062.5 MHz | quiet | 3 d | 4 d | 7 d / 29 | threshold_failure |
| in_track / S4 3062.5 MHz | May 2024 | 2 d | 3 d | 7 d / 25 | threshold_failure |
| in_track / S4 3062.5 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 33 | threshold_failure |
| in_track / S4 3062.5 MHz | August 2024 | 2 d | 3 d | 7 d / 18 | threshold_failure |
| in_track / S4 3499.14551 MHz | quiet | 3 d | 4 d | 7 d / 29 | threshold_failure |
| in_track / S4 3499.14551 MHz | May 2024 | 36 h | 2 d | 7 d / 25 | threshold_failure |
| in_track / S4 3499.14551 MHz | October 2024 | no sampled lead passed | 6 h | 7 d / 33 | threshold_failure |
| in_track / S4 3499.14551 MHz | August 2024 | 2 d | 3 d | 7 d / 18 | threshold_failure |

## 850-1000 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 78, 0.9', 3.4', 0.12 s | 77, 0.9', 3.3', 0.12 s | 60, 0.7', 4.3', 0.16 s | 65, 0.6', 3.6', 0.13 s |
| 12 h | 78, 0.7', 2.9', 0.11 s | 75, 0.7', 4.1', 0.14 s | 59, 0.7', 5.0', 0.19 s | 65, 0.7', 3.9', 0.14 s |
| 24 h | 78, 0.9', 3.2', 0.11 s | 73, 1.1', 3.0', 0.11 s | 55, 1.1', 8.1', 0.30 s | 65, 0.9', 3.6', 0.13 s |
| 36 h | 78, 1.2', 3.1', 0.11 s | 72, 1.3', 3.9', 0.14 s | 52, 1.3', 11.6', 0.44 s | 64, 1.2', 4.9', 0.18 s |
| 2 d | 78, 1.4', 3.3', 0.11 s | 72, 1.4', 3.2', 0.12 s | 49, 1.5', 11.4', 0.42 s | 62, 1.3', 4.7', 0.17 s |
| 3 d | 78, 1.5', 3.7', 0.13 s | 67, 1.8', 5.6', 0.21 s | 42, 1.7', 20.6', 0.77 s | 57, 1.4', 4.9', 0.18 s |
| 4 d | 78, 1.2', 4.8', 0.18 s | 63, 1.8', 10.3', 0.37 s | 32, 1.2', 16.2', 0.61 s | 53, 1.2', 6.9', 0.26 s |
| 5 d | 78, 2.5', 4.8', 0.18 s | 58, 2.3', 14.2', 0.53 s | 25, 1.8', 29.1', 1.09 s | 49, 2.2', 8.7', 0.33 s |
| 6 d | 78, 2.8', 4.0', 0.15 s | 53, 3.0', 15.9', 0.59 s | 19, 2.8', 11.5', 0.43 s | 46, 2.5', 11.5', 0.42 s |
| 7 d | 77, 2.4', 7.1', 0.26 s | 48, 2.4', 18.0', 0.66 s | 15, 2.0', 26.0', 0.98 s | 39, 1.6', 16.6', 0.62 s |

At 850-1000 km, the largest stored cross-track component p95 is 3.033 arcmin at mean-altitude range. This is not a sky-track-normal error.

No beam-entry or beam-timing accuracy follows from this component table. Ages below the first sampled lead are unmeasured; an exhausted window is not a threshold failure.

UHF 816 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=77); May 2024: 7 d, data exhausted at 7 d (n=48); October 2024: 5 d, first failed sample 6 d; August 2024: 7 d, data exhausted at 7 d (n=39).

L 1284 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=77); May 2024: 7 d, data exhausted at 7 d (n=48); October 2024: 3 d, first failed sample 4 d; August 2024: 7 d, data exhausted at 7 d (n=39).

L 1712 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=77); May 2024: 6 d, first failed sample 7 d; October 2024: 2 d, first failed sample 3 d; August 2024: 6 d, first failed sample 7 d.

S0 2187.5 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=77); May 2024: 4 d, first failed sample 5 d; October 2024: 36 h, first failed sample 2 d; August 2024: 6 d, first failed sample 7 d.

S4 3062.5 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=77); May 2024: 4 d, first failed sample 5 d; October 2024: 24 h, first failed sample 36 h; August 2024: 5 d, first failed sample 6 d.

S4 3499.14551 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=77); May 2024: 3 d, first failed sample 4 d; October 2024: 12 h, first failed sample 24 h; August 2024: 4 d, first failed sample 5 d.

| Component / receiver | Window | Last consecutive passing sampled lead | First failed sample | Last available / n | End reason |
| --- | --- | --- | --- | --- | --- |
| cross_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| cross_track / UHF 816 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| cross_track / UHF 816 MHz | October 2024 | 7 d | - | 7 d / 15 | data_exhausted |
| cross_track / UHF 816 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| cross_track / L 1284 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| cross_track / L 1284 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| cross_track / L 1284 MHz | October 2024 | 7 d | - | 7 d / 15 | data_exhausted |
| cross_track / L 1284 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| cross_track / L 1712 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| cross_track / L 1712 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| cross_track / L 1712 MHz | October 2024 | 7 d | - | 7 d / 15 | data_exhausted |
| cross_track / L 1712 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| cross_track / S0 2187.5 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| cross_track / S0 2187.5 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| cross_track / S0 2187.5 MHz | October 2024 | 7 d | - | 7 d / 15 | data_exhausted |
| cross_track / S0 2187.5 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| cross_track / S4 3062.5 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| cross_track / S4 3062.5 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| cross_track / S4 3062.5 MHz | October 2024 | 7 d | - | 7 d / 15 | data_exhausted |
| cross_track / S4 3062.5 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| cross_track / S4 3499.14551 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| cross_track / S4 3499.14551 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| cross_track / S4 3499.14551 MHz | October 2024 | 7 d | - | 7 d / 15 | data_exhausted |
| cross_track / S4 3499.14551 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| in_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| in_track / UHF 816 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| in_track / UHF 816 MHz | October 2024 | 5 d | 6 d | 7 d / 15 | threshold_failure |
| in_track / UHF 816 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| in_track / L 1284 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| in_track / L 1284 MHz | May 2024 | 7 d | - | 7 d / 48 | data_exhausted |
| in_track / L 1284 MHz | October 2024 | 3 d | 4 d | 7 d / 15 | threshold_failure |
| in_track / L 1284 MHz | August 2024 | 7 d | - | 7 d / 39 | data_exhausted |
| in_track / L 1712 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| in_track / L 1712 MHz | May 2024 | 6 d | 7 d | 7 d / 48 | threshold_failure |
| in_track / L 1712 MHz | October 2024 | 2 d | 3 d | 7 d / 15 | threshold_failure |
| in_track / L 1712 MHz | August 2024 | 6 d | 7 d | 7 d / 39 | threshold_failure |
| in_track / S0 2187.5 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| in_track / S0 2187.5 MHz | May 2024 | 4 d | 5 d | 7 d / 48 | threshold_failure |
| in_track / S0 2187.5 MHz | October 2024 | 36 h | 2 d | 7 d / 15 | threshold_failure |
| in_track / S0 2187.5 MHz | August 2024 | 6 d | 7 d | 7 d / 39 | threshold_failure |
| in_track / S4 3062.5 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| in_track / S4 3062.5 MHz | May 2024 | 4 d | 5 d | 7 d / 48 | threshold_failure |
| in_track / S4 3062.5 MHz | October 2024 | 24 h | 36 h | 7 d / 15 | threshold_failure |
| in_track / S4 3062.5 MHz | August 2024 | 5 d | 6 d | 7 d / 39 | threshold_failure |
| in_track / S4 3499.14551 MHz | quiet | 7 d | - | 7 d / 77 | data_exhausted |
| in_track / S4 3499.14551 MHz | May 2024 | 3 d | 4 d | 7 d / 48 | threshold_failure |
| in_track / S4 3499.14551 MHz | October 2024 | 12 h | 24 h | 7 d / 15 | threshold_failure |
| in_track / S4 3499.14551 MHz | August 2024 | 4 d | 5 d | 7 d / 39 | threshold_failure |

## 1000-1400 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 37, 0.7', 1.6', 0.09 s | 30, 1.1', 1.8', 0.10 s | 32, 0.6', 1.6', 0.09 s | 35, 0.8', 2.2', 0.12 s |
| 12 h | 37, 0.6', 1.7', 0.09 s | 29, 0.4', 2.1', 0.11 s | 32, 0.5', 2.1', 0.11 s | 35, 0.7', 1.5', 0.08 s |
| 24 h | 37, 0.5', 1.2', 0.07 s | 28, 0.8', 3.1', 0.17 s | 32, 0.6', 1.6', 0.09 s | 35, 0.6', 1.3', 0.07 s |
| 36 h | 37, 0.6', 2.3', 0.12 s | 26, 0.9', 6.2', 0.34 s | 32, 0.9', 2.7', 0.14 s | 35, 0.9', 1.8', 0.10 s |
| 2 d | 37, 0.6', 1.3', 0.07 s | 25, 1.1', 8.3', 0.45 s | 32, 0.8', 1.7', 0.09 s | 35, 0.7', 1.4', 0.08 s |
| 3 d | 37, 1.2', 1.8', 0.10 s | 23, 1.0', 16.4', 0.89 s | 32, 0.8', 1.8', 0.10 s | 35, 0.8', 1.9', 0.10 s |
| 4 d | 37, 0.6', 2.3', 0.13 s | 20, 1.1', 26.3', 1.42 s | 32, 0.6', 2.7', 0.15 s | 35, 0.9', 2.4', 0.13 s |
| 5 d | 37, 1.5', 2.0', 0.11 s | 20, 1.7', 35.2', 1.91 s | 32, 1.3', 2.7', 0.14 s | 35, 1.2', 1.9', 0.10 s |
| 6 d | 37, 1.5', 2.6', 0.14 s | 20, 0.8', 43.7', 2.37 s | 32, 1.2', 3.2', 0.17 s | 35, 1.2', 3.0', 0.16 s |
| 7 d | 37, 1.2', 2.9', 0.16 s | 20, 1.6', 54.8', 2.97 s | 32, 1.2', 3.6', 0.19 s | 35, 1.2', 3.3', 0.18 s |

At 1000-1400 km, the largest stored cross-track component p95 is 1.677 arcmin at mean-altitude range. This is not a sky-track-normal error.

No beam-entry or beam-timing accuracy follows from this component table. Ages below the first sampled lead are unmeasured; an exhausted window is not a threshold failure.

UHF 816 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=37); May 2024: 5 d, first failed sample 6 d; October 2024: 7 d, data exhausted at 7 d (n=32); August 2024: 7 d, data exhausted at 7 d (n=35).

L 1284 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=37); May 2024: 3 d, first failed sample 4 d; October 2024: 7 d, data exhausted at 7 d (n=32); August 2024: 7 d, data exhausted at 7 d (n=35).

L 1712 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=37); May 2024: 2 d, first failed sample 3 d; October 2024: 7 d, data exhausted at 7 d (n=32); August 2024: 7 d, data exhausted at 7 d (n=35).

S0 2187.5 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=37); May 2024: 2 d, first failed sample 3 d; October 2024: 7 d, data exhausted at 7 d (n=32); August 2024: 7 d, data exhausted at 7 d (n=35).

S4 3062.5 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=37); May 2024: 2 d, first failed sample 3 d; October 2024: 7 d, data exhausted at 7 d (n=32); August 2024: 7 d, data exhausted at 7 d (n=35).

S4 3499.14551 MHz, in-track component threshold: quiet: 7 d, data exhausted at 7 d (n=37); May 2024: 36 h, first failed sample 2 d; October 2024: 7 d, data exhausted at 7 d (n=32); August 2024: 7 d, data exhausted at 7 d (n=35).

| Component / receiver | Window | Last consecutive passing sampled lead | First failed sample | Last available / n | End reason |
| --- | --- | --- | --- | --- | --- |
| cross_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| cross_track / UHF 816 MHz | May 2024 | 7 d | - | 7 d / 20 | data_exhausted |
| cross_track / UHF 816 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| cross_track / UHF 816 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / L 1284 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| cross_track / L 1284 MHz | May 2024 | 7 d | - | 7 d / 20 | data_exhausted |
| cross_track / L 1284 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| cross_track / L 1284 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / L 1712 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| cross_track / L 1712 MHz | May 2024 | 7 d | - | 7 d / 20 | data_exhausted |
| cross_track / L 1712 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| cross_track / L 1712 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / S0 2187.5 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| cross_track / S0 2187.5 MHz | May 2024 | 7 d | - | 7 d / 20 | data_exhausted |
| cross_track / S0 2187.5 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| cross_track / S0 2187.5 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / S4 3062.5 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| cross_track / S4 3062.5 MHz | May 2024 | 7 d | - | 7 d / 20 | data_exhausted |
| cross_track / S4 3062.5 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| cross_track / S4 3062.5 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| cross_track / S4 3499.14551 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| cross_track / S4 3499.14551 MHz | May 2024 | 7 d | - | 7 d / 20 | data_exhausted |
| cross_track / S4 3499.14551 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| cross_track / S4 3499.14551 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| in_track / UHF 816 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| in_track / UHF 816 MHz | May 2024 | 5 d | 6 d | 7 d / 20 | threshold_failure |
| in_track / UHF 816 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| in_track / UHF 816 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| in_track / L 1284 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| in_track / L 1284 MHz | May 2024 | 3 d | 4 d | 7 d / 20 | threshold_failure |
| in_track / L 1284 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| in_track / L 1284 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| in_track / L 1712 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| in_track / L 1712 MHz | May 2024 | 2 d | 3 d | 7 d / 20 | threshold_failure |
| in_track / L 1712 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| in_track / L 1712 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| in_track / S0 2187.5 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| in_track / S0 2187.5 MHz | May 2024 | 2 d | 3 d | 7 d / 20 | threshold_failure |
| in_track / S0 2187.5 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| in_track / S0 2187.5 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| in_track / S4 3062.5 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| in_track / S4 3062.5 MHz | May 2024 | 2 d | 3 d | 7 d / 20 | threshold_failure |
| in_track / S4 3062.5 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| in_track / S4 3062.5 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |
| in_track / S4 3499.14551 MHz | quiet | 7 d | - | 7 d / 37 | data_exhausted |
| in_track / S4 3499.14551 MHz | May 2024 | 36 h | 2 d | 7 d / 20 | threshold_failure |
| in_track / S4 3499.14551 MHz | October 2024 | 7 d | - | 7 d / 32 | data_exhausted |
| in_track / S4 3499.14551 MHz | August 2024 | 7 d | - | 7 d / 35 | data_exhausted |

A missing later row is not a failed row. In particular, the 600–750 km August sample ends at 120 h with four rows; it does not establish a crossing failure after five days. No stored row tests ages below six hours, so failure at six hours cannot establish impossibility at every element age. No actual satellite detections or observing schedule were used in this component table.
