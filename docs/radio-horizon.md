# The radio horizon: the benchmark's residuals as angles on the sky

The reference benchmark measured how far a public element set puts a spacecraft from its reconstructed orbit at leads from six hours to seven days, in the satellite's radial, in-track, cross-track frame, for fifteen spacecraft in five altitude bands (`docs/reference-benchmark.md`, which extends `docs/calibration-benchmark.md`). Here each residual is the angle it subtends from the MeerKAT array centre with the satellite overhead: the residual divided by the altitude, which is the largest angle the residual can subtend from the site. Lower in the sky the same residual subtends less, by the ratio of altitude to range and by the projection onto the sky; the per-crossing figures in the period reports use the actual geometry.

Two horizons are reported, and they answer different questions. The **crossing horizon** is governed by the cross-track error, which moves an object's path sideways: it is the longest lead through which the cross-track angular error stays under a third of the beam width for 95 per cent of trials, and it answers whether an object crossed the beam during an observation, with the crossing's time known to the along-track time shift tabulated below. The **position horizon** is governed by the along-track error, which moves the object along its path: the same coverage applied to the along-track angular error, and it answers where an object is at an instant to within a third of the beam. Both are computed per altitude band, and an object is scored against its own band's trials.

## The measured population

One trial per element set per lead; manoeuvre arcs excluded from a published thruster record (Swarm, GRACE-FO) and from detection on the reconstructed orbit otherwise; near-circular, free-flying between manoeuvres. A measured horizon is attached only to an object whose mean altitude falls in one of these bands, with an eccentricity under 0.02 and an element set no older than the benchmark's seven days; every other object carries *no measured horizon* and the reason. Nothing here describes a station-kept object's error through a burn, debris, or an eccentric orbit. The beam width is measured at L-band and scaled by wavelength to UHF and S (below).

| Altitude band | Spacecraft | Mean altitude of the sets | Sets, quiet | Sets, May 2024 | Sets, October 2024 | Sets, August 2024 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 400-600 km | GRACE-FO 1 (C), GRACE-FO 2 (D), Swarm A, Swarm B, Swarm C | 460 to 507 km | 95 | 91 | 100 | 93 |
| 600-750 km | CryoSat-2, Sentinel-1A | 696 to 719 km | 45 | 44 | 41 | 39 |
| 750-850 km | SARAL, Sentinel-3A, Sentinel-3B | 783 to 803 km | 57 | 68 | 51 | 60 |
| 850-1000 km | HY-2C, HY-2D, SWOT | 893 to 952 km | 78 | 77 | 60 | 65 |
| 1000-1400 km | Jason-3, Sentinel-6A | 1338 to 1338 km | 37 | 33 | 32 | 35 |

## The beam

Half-power width from Mauch et al. 2020, ApJ 888, 61, section 2.2, equation 4 (circularised L-band half-power width 57.5 arcmin at 1.5 GHz, scaling as 1/frequency); applied to UHF and S by the lambda/D scaling de Villiers 2023, AJ 165, 78 reports over most of each band: FWHM = 57.5 arcmin x (1500 MHz / f), which is 1.13 lambda/D for the 13.5 m dish. The threshold in the tables is a third of the width at the stated frequency.

| Receiver | Digitised band (MHz) | FWHM at band centre | FWHM at band top | A third of the width, centre / top |
| --- | ---: | ---: | ---: | ---: |
| UHF | 544-1088 | 1.76 deg (106') at 816 MHz | 1.32 deg (79') at 1088 MHz | 35' / 26' |
| L | 856-1712 | 1.12 deg (67') at 1284 MHz | 0.84 deg (50') at 1712 MHz | 22' / 17' |
| S0 | 1750-2625 | 0.66 deg (39') at 2187.5 MHz | 0.55 deg (33') at 2625 MHz | 13' / 11' |
| S4 | 2625-3500 | 0.47 deg (28') at 3062.5 MHz | 0.41 deg (25') at 3500 MHz | 9' / 8' |

## The two horizons, by band and receiver

Each is the longest lead through which at least 95 per cent of a band's trials keep the named angular error under a third of the beam width, every shorter lead bin included. *Under 6 h* means the first lead bin already fails the coverage; *7 d* means no lead in the benchmark failed it.

- **Crossing horizon**, governed by the cross-track error: whether an object crossed the beam during an observation. The time of the crossing is known to the along-track shift in the tables below.
- **Position horizon**, governed by the along-track error: where an object is at an instant, to within a third of the beam.

| Band | Receiver, frequency | Crossing, quiet | Crossing, May 2024 | Crossing, October 2024 | Crossing, August 2024 | Position, quiet | Position, May 2024 | Position, October 2024 | Position, August 2024 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 400-600 km | UHF 816 MHz (FWHM 1.76 deg) | 7 d | 7 d | 7 d | 7 d | 2 d | 24 h | 6 h | 12 h |
| 400-600 km | L 1284 MHz (FWHM 1.12 deg) | 7 d | 7 d | 7 d | 7 d | 24 h | 12 h | 6 h | 12 h |
| 400-600 km | L 1712 MHz (FWHM 0.84 deg) | 7 d | 7 d | 7 d | 7 d | 24 h | 12 h | under 6 h | 12 h |
| 400-600 km | S0 2187.5 MHz (FWHM 0.66 deg) | 7 d | 7 d | 7 d | 7 d | 24 h | 12 h | under 6 h | 6 h |
| 400-600 km | S4 3500 MHz (FWHM 0.41 deg) | 7 d | 7 d | 7 d | 7 d | under 6 h | under 6 h | under 6 h | under 6 h |
| 600-750 km | UHF 816 MHz (FWHM 1.76 deg) | 7 d | 7 d | 7 d | 5 d | 36 h | 36 h | 24 h | 2 d |
| 600-750 km | L 1284 MHz (FWHM 1.12 deg) | 7 d | 7 d | 7 d | 5 d | 24 h | 24 h | 12 h | 36 h |
| 600-750 km | L 1712 MHz (FWHM 0.84 deg) | 7 d | 7 d | 7 d | 5 d | 24 h | 24 h | 6 h | 24 h |
| 600-750 km | S0 2187.5 MHz (FWHM 0.66 deg) | 7 d | 7 d | 7 d | 5 d | 12 h | 24 h | 6 h | 24 h |
| 600-750 km | S4 3500 MHz (FWHM 0.41 deg) | 7 d | 7 d | 7 d | 5 d | 12 h | 12 h | under 6 h | under 6 h |
| 750-850 km | UHF 816 MHz (FWHM 1.76 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 4 d | 24 h | 5 d |
| 750-850 km | L 1284 MHz (FWHM 1.12 deg) | 7 d | 7 d | 7 d | 7 d | 6 d | 2 d | 6 h | 3 d |
| 750-850 km | L 1712 MHz (FWHM 0.84 deg) | 7 d | 7 d | 7 d | 7 d | 4 d | 36 h | under 6 h | 3 d |
| 750-850 km | S0 2187.5 MHz (FWHM 0.66 deg) | 7 d | 7 d | 7 d | 7 d | 3 d | 36 h | under 6 h | 2 d |
| 750-850 km | S4 3500 MHz (FWHM 0.41 deg) | 7 d | 7 d | 7 d | 7 d | 3 d | 12 h | under 6 h | 2 d |
| 850-1000 km | UHF 816 MHz (FWHM 1.76 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 7 d | 5 d | 7 d |
| 850-1000 km | L 1284 MHz (FWHM 1.12 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 7 d | 3 d | 7 d |
| 850-1000 km | L 1712 MHz (FWHM 0.84 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 6 d | 2 d | 6 d |
| 850-1000 km | S0 2187.5 MHz (FWHM 0.66 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 4 d | 36 h | 6 d |
| 850-1000 km | S4 3500 MHz (FWHM 0.41 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 3 d | 12 h | 4 d |
| 1000-1400 km | UHF 816 MHz (FWHM 1.76 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 5 d | 7 d | 7 d |
| 1000-1400 km | L 1284 MHz (FWHM 1.12 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 3 d | 7 d | 7 d |
| 1000-1400 km | L 1712 MHz (FWHM 0.84 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 2 d | 7 d | 7 d |
| 1000-1400 km | S0 2187.5 MHz (FWHM 0.66 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 2 d | 7 d | 7 d |
| 1000-1400 km | S4 3500 MHz (FWHM 0.41 deg) | 7 d | 7 d | 7 d | 7 d | 7 d | 36 h | 7 d | 7 d |

**The crossing horizon at 400-600 km holds for the full 7 d in every window** for the measured population, at every receiver and frequency in the table: whether an object crossed the beam during an observation is answered through the benchmark's longest lead, and the time of the crossing is known to the along-track shift tabulated above.

**The position horizon at 400-600 km at the L-band centre is 24 h in the quiet window, 12 h in the May 2024 window, 6 h in the October 2024 window, 12 h in the August 2024 window**: where an object is at an instant, to within a third of the beam, is answered only that far ahead.

**S-band position prediction from public element sets at 400-600 km is not possible at any element-set age**: at the top of the band (S4 3500 MHz) the position horizon is under 6 h in every window, the benchmark's shortest lead; at S0 2187.5 MHz the position horizon is 24 h (quiet), 12 h (May 2024), under 6 h (October 2024), 6 h (August 2024).

**The crossing horizon at 600-750 km** falls short of the benchmark's longest lead for UHF 816 MHz in the August 2024 window (5 d); L 1284 MHz in the August 2024 window (5 d); L 1712 MHz in the August 2024 window (5 d); S0 2187.5 MHz in the August 2024 window (5 d); S4 3500 MHz in the August 2024 window (5 d).

**The position horizon at 600-750 km at the L-band centre is 24 h in the quiet window, 24 h in the May 2024 window, 12 h in the October 2024 window, 36 h in the August 2024 window**: where an object is at an instant, to within a third of the beam, is answered only that far ahead.

**S-band position prediction from public element sets at 600-750 km** at the top of the band (S4 3500 MHz) holds 12 h in the quiet window, 12 h in the May 2024 window, under 6 h in the October 2024 window, under 6 h in the August 2024 window; at S0 2187.5 MHz the position horizon is 12 h (quiet), 24 h (May 2024), 6 h (October 2024), 24 h (August 2024).

**The crossing horizon at 750-850 km holds for the full 7 d in every window** for the measured population, at every receiver and frequency in the table: whether an object crossed the beam during an observation is answered through the benchmark's longest lead, and the time of the crossing is known to the along-track shift tabulated above.

**The position horizon at 750-850 km at the L-band centre is 6 d in the quiet window, 2 d in the May 2024 window, 6 h in the October 2024 window, 3 d in the August 2024 window**: where an object is at an instant, to within a third of the beam, is answered only that far ahead.

**S-band position prediction from public element sets at 750-850 km** at the top of the band (S4 3500 MHz) holds 3 d in the quiet window, 12 h in the May 2024 window, under 6 h in the October 2024 window, 2 d in the August 2024 window; at S0 2187.5 MHz the position horizon is 3 d (quiet), 36 h (May 2024), under 6 h (October 2024), 2 d (August 2024).

**The crossing horizon at 850-1000 km holds for the full 7 d in every window** for the measured population, at every receiver and frequency in the table: whether an object crossed the beam during an observation is answered through the benchmark's longest lead, and the time of the crossing is known to the along-track shift tabulated above.

**The position horizon at 850-1000 km at the L-band centre is 7 d in the quiet window, 7 d in the May 2024 window, 3 d in the October 2024 window, 7 d in the August 2024 window**: where an object is at an instant, to within a third of the beam, is answered only that far ahead.

**S-band position prediction from public element sets at 850-1000 km** at the top of the band (S4 3500 MHz) holds 7 d in the quiet window, 3 d in the May 2024 window, 12 h in the October 2024 window, 4 d in the August 2024 window; at S0 2187.5 MHz the position horizon is 7 d (quiet), 4 d (May 2024), 36 h (October 2024), 6 d (August 2024).

**The crossing horizon at 1000-1400 km holds for the full 7 d in every window** for the measured population, at every receiver and frequency in the table: whether an object crossed the beam during an observation is answered through the benchmark's longest lead, and the time of the crossing is known to the along-track shift tabulated above.

**The position horizon at 1000-1400 km at the L-band centre is 7 d in the quiet window, 3 d in the May 2024 window, 7 d in the October 2024 window, 7 d in the August 2024 window**: where an object is at an instant, to within a third of the beam, is answered only that far ahead.

**S-band position prediction from public element sets at 1000-1400 km** at the top of the band (S4 3500 MHz) holds 7 d in the quiet window, 36 h in the May 2024 window, 7 d in the October 2024 window, 7 d in the August 2024 window; at S0 2187.5 MHz the position horizon is 7 d (quiet), 2 d (May 2024), 7 d (October 2024), 7 d (August 2024).

## The tables

For the lowest band, the band the lane began with, every window in full: the number of trials, the angular error overhead at the median and the 95th percentile (arcmin), and the fraction of trials whose angular error is under a third of the beam width per receiver and frequency; the first block is the cross-track error, the crossing horizon's test, the second the along-track error, the position horizon's test. For the other bands, the 95th percentiles and the along-track time shift per lead and window; their per-receiver fractions are in the JSON beside this page.

### 400-600 km

#### quiet week, 20 to 27 April 2024

Cross-track (the crossing horizon's test):

| Lead | n | cross-track median | cross-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 95 | 1.3' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 12 h | 95 | 1.1' | 1.8' | 100% | 100% | 100% | 100% | 100% |
| 24 h | 95 | 1.4' | 2.1' | 100% | 100% | 100% | 100% | 100% |
| 36 h | 95 | 0.8' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 2 d | 95 | 0.8' | 1.7' | 100% | 100% | 100% | 100% | 100% |
| 3 d | 95 | 0.5' | 1.6' | 100% | 100% | 100% | 100% | 100% |
| 4 d | 95 | 1.4' | 2.8' | 100% | 100% | 100% | 100% | 100% |
| 5 d | 95 | 0.8' | 1.7' | 100% | 100% | 100% | 100% | 100% |
| 6 d | 95 | 1.0' | 3.2' | 100% | 100% | 100% | 100% | 100% |
| 7 d | 95 | 1.1' | 2.4' | 100% | 100% | 100% | 100% | 100% |

Along-track (the position horizon's test):

| Lead | n | along-track median | along-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 95 | 3.6' | 9.7' | 100% | 100% | 100% | 100% | 93% |
| 12 h | 95 | 4.4' | 11.7' | 100% | 100% | 100% | 100% | 75% |
| 24 h | 95 | 2.7' | 11.3' | 100% | 100% | 100% | 98% | 88% |
| 36 h | 95 | 7.2' | 22.6' | 100% | 94% | 86% | 76% | 56% |
| 2 d | 95 | 9.2' | 32.6' | 96% | 86% | 77% | 62% | 49% |
| 3 d | 95 | 18.0' | 55.4' | 83% | 60% | 47% | 34% | 29% |
| 4 d | 95 | 31.3' | 89.2' | 54% | 39% | 29% | 24% | 11% |
| 5 d | 95 | 58.9' | 161.2' | 37% | 25% | 18% | 14% | 7% |
| 6 d | 95 | 80.3' | 257.4' | 27% | 17% | 12% | 9% | 7% |
| 7 d | 95 | 133.0' | 422.0' | 16% | 7% | 4% | 1% | 0% |

#### May 2024 storm, sets issued 6 to 13 May

Cross-track (the crossing horizon's test):

| Lead | n | cross-track median | cross-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 91 | 1.2' | 3.0' | 100% | 100% | 100% | 100% | 100% |
| 12 h | 91 | 1.0' | 1.7' | 100% | 100% | 100% | 100% | 100% |
| 24 h | 91 | 1.4' | 2.1' | 100% | 100% | 100% | 100% | 100% |
| 36 h | 91 | 0.7' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 2 d | 91 | 0.9' | 1.6' | 100% | 100% | 100% | 100% | 100% |
| 3 d | 88 | 0.4' | 1.6' | 100% | 100% | 100% | 100% | 100% |
| 4 d | 86 | 1.2' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 5 d | 84 | 0.6' | 1.5' | 100% | 100% | 100% | 100% | 100% |
| 6 d | 81 | 0.6' | 2.2' | 100% | 100% | 100% | 100% | 100% |
| 7 d | 78 | 1.3' | 2.5' | 100% | 100% | 100% | 100% | 100% |

Along-track (the position horizon's test):

| Lead | n | along-track median | along-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 91 | 4.7' | 9.9' | 100% | 100% | 100% | 100% | 88% |
| 12 h | 91 | 4.1' | 9.3' | 100% | 100% | 100% | 100% | 86% |
| 24 h | 91 | 6.4' | 26.0' | 99% | 90% | 86% | 80% | 60% |
| 36 h | 91 | 6.8' | 65.4' | 79% | 76% | 76% | 74% | 58% |
| 2 d | 91 | 15.2' | 105.6' | 68% | 62% | 56% | 43% | 31% |
| 3 d | 88 | 59.2' | 250.5' | 42% | 30% | 25% | 19% | 12% |
| 4 d | 86 | 130.2' | 425.0' | 14% | 3% | 1% | 1% | 0% |
| 5 d | 84 | 202.2' | 675.3' | 14% | 11% | 7% | 6% | 5% |
| 6 d | 81 | 298.8' | 965.5' | 5% | 5% | 2% | 1% | 0% |
| 7 d | 78 | 395.9' | 1279.3' | 3% | 1% | 1% | 1% | 1% |

#### October 2024 storm, sets issued 6 to 13 October (held out)

Cross-track (the crossing horizon's test):

| Lead | n | cross-track median | cross-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 100 | 0.9' | 2.0' | 100% | 100% | 100% | 100% | 100% |
| 12 h | 100 | 1.2' | 2.3' | 100% | 100% | 100% | 100% | 100% |
| 24 h | 100 | 1.3' | 2.3' | 100% | 100% | 100% | 100% | 100% |
| 36 h | 100 | 0.8' | 1.9' | 100% | 100% | 100% | 100% | 100% |
| 2 d | 100 | 0.8' | 1.9' | 100% | 100% | 100% | 100% | 100% |
| 3 d | 100 | 0.9' | 2.7' | 100% | 100% | 100% | 100% | 100% |
| 4 d | 97 | 1.2' | 2.4' | 100% | 100% | 100% | 100% | 100% |
| 5 d | 93 | 0.9' | 2.5' | 100% | 100% | 100% | 100% | 100% |
| 6 d | 89 | 0.8' | 3.4' | 100% | 100% | 100% | 100% | 100% |
| 7 d | 85 | 0.7' | 2.4' | 100% | 100% | 100% | 100% | 100% |

Along-track (the position horizon's test):

| Lead | n | along-track median | along-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 100 | 5.8' | 16.9' | 100% | 96% | 94% | 91% | 76% |
| 12 h | 100 | 6.6' | 45.0' | 92% | 86% | 80% | 79% | 65% |
| 24 h | 100 | 10.9' | 129.9' | 75% | 65% | 58% | 53% | 38% |
| 36 h | 100 | 28.6' | 246.8' | 61% | 41% | 36% | 29% | 16% |
| 2 d | 100 | 47.3' | 399.4' | 35% | 18% | 11% | 10% | 5% |
| 3 d | 100 | 95.4' | 827.0' | 15% | 11% | 4% | 3% | 2% |
| 4 d | 97 | 135.6' | 1383.5' | 13% | 8% | 7% | 6% | 4% |
| 5 d | 93 | 183.4' | 1678.6' | 15% | 9% | 5% | 3% | 1% |
| 6 d | 89 | 248.8' | 2342.7' | 15% | 12% | 10% | 9% | 6% |
| 7 d | 85 | 362.2' | 2957.9' | 2% | 2% | 2% | 1% | 0% |

#### August 2024 storm, sets issued 8 to 15 August (held out)

Cross-track (the crossing horizon's test):

| Lead | n | cross-track median | cross-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 93 | 1.1' | 2.9' | 100% | 100% | 100% | 100% | 100% |
| 12 h | 93 | 0.7' | 1.8' | 100% | 100% | 100% | 100% | 100% |
| 24 h | 93 | 1.2' | 2.3' | 100% | 100% | 100% | 100% | 100% |
| 36 h | 93 | 0.7' | 2.2' | 100% | 100% | 100% | 100% | 100% |
| 2 d | 93 | 1.0' | 1.8' | 100% | 100% | 100% | 100% | 100% |
| 3 d | 93 | 0.6' | 2.1' | 100% | 100% | 100% | 100% | 100% |
| 4 d | 93 | 1.1' | 2.1' | 100% | 100% | 100% | 100% | 100% |
| 5 d | 93 | 0.7' | 2.5' | 100% | 100% | 100% | 100% | 100% |
| 6 d | 93 | 0.9' | 2.6' | 100% | 100% | 100% | 100% | 100% |
| 7 d | 93 | 1.0' | 2.5' | 100% | 100% | 100% | 100% | 100% |

Along-track (the position horizon's test):

| Lead | n | along-track median | along-track p95 | UHF 816 MHz | L 1284 MHz | L 1712 MHz | S0 2187.5 MHz | S4 3500 MHz |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 h | 93 | 4.7' | 9.6' | 100% | 100% | 100% | 100% | 85% |
| 12 h | 93 | 4.7' | 14.6' | 100% | 100% | 97% | 92% | 72% |
| 24 h | 93 | 4.6' | 34.6' | 95% | 89% | 88% | 84% | 68% |
| 36 h | 93 | 12.0' | 68.2' | 84% | 61% | 57% | 52% | 33% |
| 2 d | 93 | 31.0' | 121.9' | 57% | 45% | 44% | 30% | 23% |
| 3 d | 93 | 72.4' | 270.5' | 30% | 17% | 9% | 9% | 5% |
| 4 d | 93 | 142.5' | 486.2' | 16% | 11% | 9% | 4% | 3% |
| 5 d | 93 | 229.0' | 754.5' | 11% | 6% | 2% | 2% | 0% |
| 6 d | 93 | 314.0' | 1086.9' | 11% | 5% | 3% | 2% | 1% |
| 7 d | 93 | 408.9' | 1474.3' | 8% | 5% | 4% | 4% | 4% |

### 600-750 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 45, 1.6', 5.8', 0.16 s | 44, 1.4', 5.7', 0.15 s | 41, 1.4', 11.5', 0.31 s | 39, 1.2', 7.1', 0.20 s |
| 12 h | 45, 1.6', 6.1', 0.16 s | 43, 1.5', 7.9', 0.22 s | 40, 1.4', 22.4', 0.60 s | 37, 1.1', 9.4', 0.26 s |
| 24 h | 43, 1.2', 16.0', 0.43 s | 40, 1.3', 11.6', 0.32 s | 39, 1.0', 33.1', 0.89 s | 34, 1.0', 11.4', 0.31 s |
| 36 h | 42, 1.5', 24.6', 0.66 s | 38, 1.3', 25.0', 0.70 s | 36, 1.4', 47.5', 1.28 s | 29, 1.1', 19.0', 0.51 s |
| 2 d | 41, 1.8', 37.8', 1.02 s | 35, 1.6', 40.8', 1.14 s | 33, 1.3', 49.4', 1.33 s | 25, 1.2', 30.4', 0.82 s |
| 3 d | 37, 2.1', 56.4', 1.52 s | 30, 1.8', 64.1', 1.79 s | 27, 1.6', 54.6', 1.48 s | 19, 1.6', 36.2', 0.98 s |
| 4 d | 35, 1.3', 83.5', 2.25 s | 26, 1.5', 93.2', 2.60 s | 22, 1.4', 56.0', 1.51 s | 12, 1.0', 43.1', 1.16 s |
| 5 d | 35, 1.5', 103.4', 2.79 s | 21, 1.2', 105.8', 2.96 s | 18, 1.4', 104.6', 2.82 s | 4, 0.4', 34.8', 0.94 s |
| 6 d | 35, 1.8', 129.1', 3.48 s | 18, 1.7', 126.9', 3.55 s | 13, 1.9', 79.2', 2.18 s | - |
| 7 d | 35, 2.3', 158.2', 4.27 s | 18, 1.3', 131.1', 3.66 s | 8, 1.8', 103.9', 2.90 s | - |

### 750-850 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 57, 0.6', 4.7', 0.15 s | 68, 0.9', 6.6', 0.21 s | 51, 0.9', 19.8', 0.62 s | 60, 0.9', 6.9', 0.22 s |
| 12 h | 54, 1.2', 3.3', 0.10 s | 68, 1.2', 6.3', 0.19 s | 50, 1.1', 23.3', 0.73 s | 58, 1.4', 7.6', 0.23 s |
| 24 h | 52, 1.3', 4.2', 0.13 s | 68, 1.3', 9.2', 0.29 s | 50, 1.1', 28.4', 0.89 s | 53, 1.2', 6.3', 0.20 s |
| 36 h | 47, 0.8', 5.1', 0.16 s | 68, 0.9', 11.0', 0.34 s | 48, 0.8', 38.9', 1.22 s | 50, 0.9', 8.0', 0.25 s |
| 2 d | 46, 1.4', 6.4', 0.19 s | 68, 1.1', 17.0', 0.53 s | 46, 1.4', 21.5', 0.67 s | 46, 1.1', 7.9', 0.24 s |
| 3 d | 40, 1.5', 8.1', 0.25 s | 66, 1.4', 25.7', 0.81 s | 45, 1.2', 30.4', 0.95 s | 39, 1.1', 14.5', 0.45 s |
| 4 d | 33, 1.5', 13.0', 0.41 s | 59, 1.8', 29.9', 0.94 s | 43, 1.4', 46.6', 1.46 s | 32, 1.3', 21.5', 0.66 s |
| 5 d | 30, 1.5', 20.4', 0.64 s | 53, 1.1', 35.7', 1.12 s | 41, 1.9', 66.2', 2.08 s | 25, 1.4', 27.9', 0.85 s |
| 6 d | 29, 1.7', 19.0', 0.59 s | 46, 2.1', 46.6', 1.46 s | 38, 1.0', 133.9', 4.16 s | 18, 0.7', 40.7', 1.24 s |
| 7 d | 29, 1.3', 27.4', 0.85 s | 38, 1.2', 41.2', 1.28 s | 33, 2.3', 74.1', 2.29 s | 18, 1.7', 56.4', 1.72 s |

### 850-1000 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 78, 0.9', 3.4', 0.12 s | 77, 0.9', 3.3', 0.12 s | 60, 0.7', 4.3', 0.16 s | 65, 0.6', 3.6', 0.13 s |
| 12 h | 78, 0.7', 2.9', 0.11 s | 75, 0.7', 4.1', 0.14 s | 57, 0.7', 5.1', 0.19 s | 65, 0.7', 3.9', 0.14 s |
| 24 h | 78, 0.9', 3.2', 0.11 s | 73, 1.1', 3.0', 0.11 s | 55, 1.1', 8.1', 0.30 s | 65, 0.9', 3.6', 0.13 s |
| 36 h | 78, 1.2', 3.1', 0.11 s | 72, 1.3', 3.9', 0.14 s | 51, 1.3', 11.6', 0.44 s | 64, 1.2', 4.9', 0.18 s |
| 2 d | 78, 1.4', 3.3', 0.11 s | 72, 1.4', 3.2', 0.12 s | 48, 1.5', 11.8', 0.44 s | 62, 1.3', 4.7', 0.17 s |
| 3 d | 78, 1.5', 3.7', 0.13 s | 67, 1.8', 5.6', 0.21 s | 41, 1.7', 21.3', 0.80 s | 57, 1.4', 4.9', 0.18 s |
| 4 d | 78, 1.2', 4.8', 0.18 s | 63, 1.8', 10.3', 0.37 s | 33, 1.2', 15.2', 0.57 s | 53, 1.2', 6.9', 0.26 s |
| 5 d | 78, 2.5', 4.8', 0.18 s | 58, 2.3', 14.2', 0.53 s | 30, 1.8', 26.8', 1.01 s | 49, 2.2', 8.7', 0.33 s |
| 6 d | 78, 2.8', 4.0', 0.15 s | 53, 3.0', 15.9', 0.59 s | 29, 2.9', 40.1', 1.51 s | 46, 2.5', 11.5', 0.42 s |
| 7 d | 78, 2.4', 7.0', 0.26 s | 48, 2.4', 18.0', 0.66 s | 29, 2.1', 54.6', 2.05 s | 39, 1.6', 16.6', 0.62 s |

### 1000-1400 km

| Lead | quiet: n, cross p95, along p95, shift p95 | May 2024: n, cross p95, along p95, shift p95 | October 2024: n, cross p95, along p95, shift p95 | August 2024: n, cross p95, along p95, shift p95 |
| ---: | --- | --- | --- | --- |
| 6 h | 37, 0.7', 1.6', 0.09 s | 33, 1.1', 2.5', 0.13 s | 32, 0.6', 1.6', 0.09 s | 35, 0.8', 2.2', 0.12 s |
| 12 h | 37, 0.6', 1.7', 0.09 s | 33, 0.4', 2.5', 0.13 s | 32, 0.5', 2.1', 0.11 s | 35, 0.7', 1.5', 0.08 s |
| 24 h | 37, 0.5', 1.2', 0.07 s | 33, 0.8', 4.4', 0.24 s | 32, 0.6', 1.6', 0.09 s | 35, 0.6', 1.3', 0.07 s |
| 36 h | 37, 0.6', 2.3', 0.12 s | 33, 1.2', 6.8', 0.37 s | 32, 0.9', 2.7', 0.14 s | 35, 0.9', 1.8', 0.10 s |
| 2 d | 37, 0.6', 1.3', 0.07 s | 33, 1.1', 8.6', 0.47 s | 32, 0.8', 1.7', 0.09 s | 35, 0.7', 1.4', 0.08 s |
| 3 d | 37, 1.2', 1.8', 0.10 s | 33, 1.0', 13.6', 0.74 s | 32, 0.8', 1.8', 0.10 s | 35, 0.8', 1.9', 0.10 s |
| 4 d | 37, 0.6', 2.3', 0.13 s | 33, 1.1', 18.4', 1.00 s | 32, 0.6', 2.7', 0.15 s | 35, 0.9', 2.4', 0.13 s |
| 5 d | 37, 1.5', 2.0', 0.11 s | 33, 1.7', 23.8', 1.29 s | 32, 1.3', 2.7', 0.14 s | 35, 1.2', 1.9', 0.10 s |
| 6 d | 37, 1.5', 2.6', 0.14 s | 33, 0.8', 29.8', 1.61 s | 32, 1.2', 3.2', 0.17 s | 35, 1.2', 3.0', 0.16 s |
| 7 d | 37, 1.2', 2.9', 0.16 s | 33, 1.6', 36.2', 1.96 s | 32, 1.2', 3.6', 0.19 s | 35, 1.2', 3.3', 0.18 s |

### The along-track error as a time shift, lowest band

The along-track residual divided by the orbital speed: how early or late the satellite is at a crossing, whatever the range. This is the timing figure the crossing horizon carries with it; the other bands' figures are in their tables above.

| Lead | quiet median / p95 | May 2024 median / p95 | October 2024 median / p95 | August 2024 median / p95 |
| ---: | ---: | ---: | ---: | ---: |
| 6 h | 0.07 s / 0.18 s | 0.09 s / 0.18 s | 0.11 s / 0.31 s | 0.08 s / 0.17 s |
| 12 h | 0.08 s / 0.22 s | 0.08 s / 0.17 s | 0.12 s / 0.79 s | 0.08 s / 0.26 s |
| 24 h | 0.05 s / 0.20 s | 0.12 s / 0.47 s | 0.20 s / 2.34 s | 0.09 s / 0.64 s |
| 36 h | 0.13 s / 0.41 s | 0.12 s / 1.18 s | 0.51 s / 4.46 s | 0.22 s / 1.27 s |
| 2 d | 0.17 s / 0.59 s | 0.28 s / 1.94 s | 0.83 s / 7.23 s | 0.56 s / 2.27 s |
| 3 d | 0.33 s / 1.00 s | 1.11 s / 4.55 s | 1.73 s / 15.20 s | 1.37 s / 5.05 s |
| 4 d | 0.57 s / 1.63 s | 2.34 s / 8.21 s | 2.42 s / 26.37 s | 2.53 s / 9.11 s |
| 5 d | 1.08 s / 2.96 s | 3.73 s / 13.01 s | 3.31 s / 32.63 s | 4.14 s / 14.28 s |
| 6 d | 1.44 s / 4.80 s | 5.74 s / 18.39 s | 4.56 s / 50.15 s | 5.97 s / 20.68 s |
| 7 d | 2.43 s / 7.66 s | 7.27 s / 25.08 s | 6.45 s / 72.17 s | 7.48 s / 28.86 s |

## What this does not show

- The angles are for the satellite overhead, the worst case; a crossing at 30 degrees of elevation sees a residual at roughly twice the range and half the angle.
- Fifteen spacecraft in five bands, four windows, one week of sets each. Nothing here is measured for debris, for the GNSS or mobile-satellite orbits, for station-kept constellations, for eccentric orbits, or for objects the network tracks less often, and every such object is labelled *no measured horizon* in the reports.
- The beam width is a measurement at L-band scaled by wavelength; the holography paper reports the width proportional to lambda/D over most of each band, with departures at the top of each band.
- In the lowest band the cross-track residual stays under half a kilometre at every lead in every window, so the crossing horizon is the benchmark's full seven days and the position horizon is the number that moves. Whether a crossing predicted days ahead happens inside a given observation is a position question, of timing, before it is a crossing question, of geometry.

Source of the trials: `data/validation/reference_benchmark.parquet`; the usable trials are exported beside this page as `data/radio/benchmark_trials.csv` so the tables recompute from the repository.

_Last updated 07 September 2026._
