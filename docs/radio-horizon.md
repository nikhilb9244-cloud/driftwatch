# The radio horizon: the benchmark's residuals as angles on the sky

The calibration benchmark measured how far a public element set puts Swarm A, B and C from ESA's precise orbit at leads from six hours to seven days, in the satellite's radial, in-track, cross-track frame (`docs/calibration-benchmark.md`). Here each residual is the angle it subtends from the MeerKAT array centre with the satellite overhead: the residual divided by the altitude, which is the largest angle the residual can subtend from the site. Lower in the sky the same residual subtends less, by the ratio of altitude to range and by the projection onto the sky; the per-crossing figures in the period reports use the actual geometry. Cross-track error decides whether a beam crossing happens; along-track error shifts when it happens, and is given as a time shift at the orbital speed as well as an angle.

**Population and limits.** Three sun-synchronous satellites, Swarm A at 456 to 468 km, Swarm B at 496 to 503 km, Swarm C at 456 to 468 km; 57 sets in the quiet window, 54 sets in the May 2024 window, 61 sets in the October 2024 window; one trial per element set per lead, manoeuvre arcs excluded from ESA's thruster record. A measured horizon is attached only to objects between 400 and 600 km; every other object carries *no measured horizon* and the reason. Nothing here describes a station-kept object's error through a burn. The beam width is measured at L-band and scaled by wavelength to UHF and S (below).

## The beam

Half-power width from Mauch et al. 2020, ApJ 888, 61, section 2.2, equation 4 (circularised L-band half-power width 57.5 arcmin at 1.5 GHz, scaling as 1/frequency); applied to UHF and S by the lambda/D scaling de Villiers 2023, AJ 165, 78 reports over most of each band: FWHM = 57.5 arcmin x (1500 MHz / f), which is 1.13 lambda/D for the 13.5 m dish. The threshold in the tables is a third of the width at the stated frequency.

| Receiver | Digitised band (MHz) | FWHM at band centre | FWHM at band top | A third of the width, centre / top |
| --- | ---: | ---: | ---: | ---: |
| UHF | 544-1088 | 1.76 deg (106') at 816 MHz | 1.32 deg (79') at 1088 MHz | 35' / 26' |
| L | 856-1712 | 1.12 deg (67') at 1284 MHz | 0.84 deg (50') at 1712 MHz | 22' / 17' |
| S0 | 1750-2625 | 0.66 deg (39') at 2187.5 MHz | 0.55 deg (33') at 2625 MHz | 13' / 11' |
| S4 | 2625-3500 | 0.47 deg (28') at 3062.5 MHz | 0.41 deg (25') at 3500 MHz | 9' / 8' |

## The table

For each window and lead: the number of trials, the angular error overhead at the median and the 95th percentile (arcmin), and the fraction of trials whose angular error is under a third of the beam width, per receiver and frequency. The first block of each window is the cross-track error, which decides whether a crossing happens; the second is the along-track error, which decides when, and whose time shift at the orbital speed is in the last table.

### quiet week, 20 to 27 April 2024

Cross-track:

| Lead | n | cross-track median | cross-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 57 | 1.4' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 12 h | 57 | 1.3' | 1.8' | 100% | 100% | 100% | 100% | 100% |
| 24 h | 57 | 1.4' | 2.1' | 100% | 100% | 100% | 100% | 100% |
| 36 h | 57 | 0.6' | 2.1' | 100% | 100% | 100% | 100% | 100% |
| 2 d | 57 | 1.0' | 1.8' | 100% | 100% | 100% | 100% | 100% |
| 3 d | 57 | 0.5' | 1.6' | 100% | 100% | 100% | 100% | 100% |
| 4 d | 57 | 1.5' | 3.0' | 100% | 100% | 100% | 100% | 100% |
| 5 d | 57 | 0.9' | 1.9' | 100% | 100% | 100% | 100% | 100% |
| 6 d | 57 | 1.1' | 3.6' | 100% | 100% | 100% | 100% | 100% |
| 7 d | 57 | 1.6' | 2.5' | 100% | 100% | 100% | 100% | 100% |

Along-track:

| Lead | n | along-track median | along-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 57 | 2.4' | 9.8' | 100% | 100% | 100% | 100% | 91% |
| 12 h | 57 | 3.7' | 11.7' | 100% | 100% | 100% | 98% | 81% |
| 24 h | 57 | 3.7' | 11.3' | 100% | 100% | 100% | 96% | 84% |
| 36 h | 57 | 8.2' | 23.5' | 100% | 93% | 81% | 67% | 51% |
| 2 d | 57 | 11.5' | 36.1' | 93% | 81% | 68% | 56% | 40% |
| 3 d | 57 | 23.0' | 65.7' | 75% | 47% | 35% | 21% | 14% |
| 4 d | 57 | 50.0' | 94.6' | 37% | 26% | 16% | 12% | 5% |
| 5 d | 57 | 70.2' | 163.4' | 26% | 18% | 12% | 11% | 5% |
| 6 d | 57 | 99.3' | 286.4' | 21% | 9% | 9% | 7% | 4% |
| 7 d | 57 | 165.7' | 437.9' | 12% | 4% | 4% | 2% | 0% |

### May 2024 storm, sets issued 6 to 13 May

Cross-track:

| Lead | n | cross-track median | cross-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 54 | 1.5' | 3.1' | 100% | 100% | 100% | 100% | 100% |
| 12 h | 54 | 1.2' | 1.8' | 100% | 100% | 100% | 100% | 100% |
| 24 h | 54 | 1.6' | 2.2' | 100% | 100% | 100% | 100% | 100% |
| 36 h | 54 | 0.7' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 2 d | 54 | 1.1' | 1.6' | 100% | 100% | 100% | 100% | 100% |
| 3 d | 54 | 0.4' | 1.6' | 100% | 100% | 100% | 100% | 100% |
| 4 d | 54 | 1.6' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 5 d | 54 | 0.7' | 1.7' | 100% | 100% | 100% | 100% | 100% |
| 6 d | 54 | 0.6' | 2.1' | 100% | 100% | 100% | 100% | 100% |
| 7 d | 54 | 1.6' | 2.6' | 100% | 100% | 100% | 100% | 100% |

Along-track:

| Lead | n | along-track median | along-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 54 | 3.4' | 8.4' | 100% | 100% | 100% | 100% | 91% |
| 12 h | 54 | 2.6' | 6.7' | 100% | 100% | 100% | 100% | 98% |
| 24 h | 54 | 6.1' | 27.2' | 100% | 85% | 78% | 74% | 63% |
| 36 h | 54 | 5.1' | 70.8' | 76% | 76% | 76% | 74% | 61% |
| 2 d | 54 | 16.2' | 114.3' | 65% | 59% | 52% | 44% | 37% |
| 3 d | 54 | 51.0' | 262.4' | 39% | 30% | 30% | 22% | 11% |
| 4 d | 54 | 146.0' | 467.4' | 13% | 6% | 2% | 2% | 0% |
| 5 d | 54 | 264.2' | 701.9' | 13% | 11% | 7% | 6% | 4% |
| 6 d | 54 | 404.2' | 985.8' | 6% | 6% | 4% | 2% | 0% |
| 7 d | 54 | 526.0' | 1302.6' | 0% | 0% | 0% | 0% | 0% |

### October 2024 storm, sets issued 6 to 13 October (held out)

Cross-track:

| Lead | n | cross-track median | cross-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 61 | 0.7' | 2.0' | 100% | 100% | 100% | 100% | 100% |
| 12 h | 61 | 1.1' | 2.4' | 100% | 100% | 100% | 100% | 100% |
| 24 h | 61 | 1.2' | 2.3' | 100% | 100% | 100% | 100% | 100% |
| 36 h | 61 | 1.0' | 2.0' | 100% | 100% | 100% | 100% | 100% |
| 2 d | 61 | 1.2' | 2.0' | 100% | 100% | 100% | 100% | 100% |
| 3 d | 61 | 0.5' | 1.6' | 100% | 100% | 100% | 100% | 100% |
| 4 d | 58 | 1.3' | 2.4' | 100% | 100% | 100% | 100% | 100% |
| 5 d | 54 | 1.1' | 2.9' | 100% | 100% | 100% | 100% | 100% |
| 6 d | 50 | 0.4' | 1.8' | 100% | 100% | 100% | 100% | 100% |
| 7 d | 46 | 1.3' | 2.5' | 100% | 100% | 100% | 100% | 100% |

Along-track:

| Lead | n | along-track median | along-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 61 | 6.1' | 14.3' | 100% | 97% | 97% | 90% | 69% |
| 12 h | 61 | 6.7' | 45.3' | 93% | 84% | 80% | 79% | 64% |
| 24 h | 61 | 13.3' | 137.5' | 72% | 59% | 54% | 49% | 34% |
| 36 h | 61 | 29.3' | 281.8' | 56% | 36% | 31% | 23% | 13% |
| 2 d | 61 | 50.4' | 481.2' | 26% | 13% | 8% | 8% | 7% |
| 3 d | 61 | 107.5' | 1032.7' | 13% | 10% | 2% | 2% | 2% |
| 4 d | 58 | 148.1' | 1659.8' | 12% | 9% | 7% | 7% | 3% |
| 5 d | 54 | 203.3' | 1784.7' | 9% | 7% | 6% | 2% | 0% |
| 6 d | 50 | 284.6' | 2556.1' | 10% | 6% | 6% | 4% | 2% |
| 7 d | 46 | 367.8' | 3250.1' | 4% | 4% | 4% | 2% | 0% |

### The along-track error as a time shift

The along-track residual divided by the orbital speed: how early or late the satellite is at a crossing, whatever the range.

| Lead | quiet median / p95 | May 2024 median / p95 | October 2024 median / p95 |
| ---: | ---: | ---: | ---: |
| 6 h | 0.04 s / 0.19 s | 0.06 s / 0.16 s | 0.11 s / 0.27 s |
| 12 h | 0.07 s / 0.22 s | 0.05 s / 0.12 s | 0.12 s / 0.79 s |
| 24 h | 0.07 s / 0.20 s | 0.11 s / 0.48 s | 0.23 s / 2.39 s |
| 36 h | 0.15 s / 0.42 s | 0.09 s / 1.30 s | 0.55 s / 4.92 s |
| 2 d | 0.21 s / 0.65 s | 0.29 s / 2.08 s | 0.91 s / 8.43 s |
| 3 d | 0.42 s / 1.17 s | 0.95 s / 4.68 s | 1.99 s / 18.53 s |
| 4 d | 0.91 s / 1.69 s | 2.60 s / 8.42 s | 2.58 s / 31.36 s |
| 5 d | 1.30 s / 3.01 s | 4.90 s / 13.16 s | 3.54 s / 34.82 s |
| 6 d | 1.89 s / 5.20 s | 7.55 s / 19.21 s | 5.07 s / 56.66 s |
| 7 d | 3.15 s / 8.15 s | 9.80 s / 25.95 s | 6.42 s / 85.37 s |

## The horizon

The longest lead through which at least 95 per cent of trials keep their angular error under a third of the beam width, every shorter lead bin included. *Under 6 h* means the first lead bin already fails the coverage; *7 d* means no lead in the benchmark failed it.

| Receiver, frequency | Error | quiet | May 2024 | October 2024 |
| --- | --- | --- | --- | --- |
| UHF 816 MHz (FWHM 1.76 deg) | cross-track | 7 d | 7 d | 7 d |
| UHF 816 MHz (FWHM 1.76 deg) | along-track | 36 h | 24 h | 6 h |
| L 1284 MHz (FWHM 1.12 deg) | cross-track | 7 d | 7 d | 7 d |
| L 1284 MHz (FWHM 1.12 deg) | along-track | 24 h | 12 h | 6 h |
| L 1712 MHz (FWHM 0.84 deg) | cross-track | 7 d | 7 d | 7 d |
| L 1712 MHz (FWHM 0.84 deg) | along-track | 24 h | 12 h | 6 h |
| S0 2187.5 MHz (FWHM 0.66 deg) | cross-track | 7 d | 7 d | 7 d |
| S0 2187.5 MHz (FWHM 0.66 deg) | along-track | 24 h | 12 h | under 6 h |
| S4 3500 MHz (FWHM 0.41 deg) | cross-track | 7 d | 7 d | 7 d |
| S4 3500 MHz (FWHM 0.41 deg) | along-track | under 6 h | under 6 h | under 6 h |

## What this does not show

- The angles are for the satellite overhead, the worst case; a crossing at 30 degrees of elevation sees a residual at roughly twice the range and half the angle.
- Three satellites in one orbit class, three windows, one week of sets each. Nothing here is measured for debris, for the GNSS or mobile-satellite orbits, for station-kept constellations, or for objects the network tracks less often, and every such object is labelled *no measured horizon* in the reports.
- The beam width is a measurement at L-band scaled by wavelength; the holography paper reports the width proportional to lambda/D over most of each band, with departures at the top of each band.
- The cross-track residual stays under half a kilometre at every lead in every window, so on this population the cross-track fraction is one everywhere and the along-track error is the number that moves. Whether a crossing predicted days ahead happens inside a given observation is an along-track question, of timing, before it is a cross-track question, of geometry.

Source of the trials: `data/validation/swarm_benchmark.parquet`; the usable trials are exported beside this page as `data/radio/swarm_trials.csv` so the table recomputes from the repository.

_Last updated 07 September 2026._
