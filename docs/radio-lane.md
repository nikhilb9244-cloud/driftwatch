# Radio geometry, measured beams and limited catalogue metadata

The radio lane contains a component-error diagnostic, illustrative catalogue passages and a
paired topocentric comparison using measured MeerKAT beams. The former claim that small orbital
cross-track errors establish a seven-day beam-crossing horizon is withdrawn. The former claim
that S-band position prediction is impossible at every element age is also withdrawn. Neither
follows from the stored trials.

The [component table](radio-horizon.md), [declared-emission table](radio-emissions.md),
[April illustration](radio/quiet-2024-04.md), [May visibility counts](radio/storm-2024-05.md) and
their JSON exports remain reproducible. They estimate geometry and declared frequency overlap;
they contain no received-power, occupancy or sensitivity-loss measurement.

## What the component table establishes

The original table computes `arctan2(abs(C), h)` and `arctan2(abs(I), h)`, where C and I are
orbital cross-track and in-track residuals and h is mean altitude from the element set. It
compares each component separately with one third of an analytic beam FWHM, then reports the
last consecutive sampled lead at which at least 95% of rows pass. The sample p95 uses linear
interpolation. This is an arbitrary component criterion, not a predictive coverage guarantee.
The JSON also gives the sensitivity to choosing half the FWHM, for every band and frequency.
The corrected primary S4 scalar columns use measured widths at 3062.5 and 3499.1455078125 MHz;
the analytic 3500 MHz calculation is now only an explicitly historical comparison. For the
measured columns, the narrower diametric half-power cut through the sampled beam peak defines
the scalar width, with cuts every 0.5° in orientation. The wider-cut sensitivity is also recorded.
These are declared width conventions; actual crossing classification uses the complete pattern.

Mean altitude is a representative range. It is not the actual slant range, the orbital C axis
is not generally normal to the apparent sky track, and I does not solely change timing. The
radial component and observer rotation also matter. Even a purely phase-shifted circular orbit
with exactly zero C residual can miss a fixed celestial beam when the observer rotates.
Dividing I by circular orbital speed gives an orbital phase-time scale, not a beam-entry-time
error. A point very near a beam edge can change classification under an arbitrarily small error.

For the original 400–600 km rows, the chosen analytic 3.5 GHz FWHM/3 criterion fails at six
hours, the earliest sampled lead, in all four windows. That is the defensible statement; ages
below six hours were not measured, and the result does not cover every S-band frequency or
every beam-width criterion. The 600–750 km August table ends at 120 h with four rows. Its missing
144 h and 168 h rows are not threshold failures. Schema 2 records data exhaustion separately
from the first failed sampled lead.

## Measured beam and full-vector comparison

The correction uses de Villiers' published MeerKAT holography products, with actual array-average
Jones channels at 816, 1284, 1711.1640625, 2187.5, 3062.5 and 3499.1455078125 MHz. The last two
sample S4 above 3 GHz; there is no measurement at exactly 3500 MHz in the selected cube. The
published models represent 60° elevation and 15°C, averaged over 2020–2022 for UHF/L and
2021–2022 for S band. Application at other elevations and to a particular antenna or date is
an explicit instrument-model approximation. [SARAO data release](https://doi.org/10.48479/wdb0-h061).

The implementation reads four complex Jones planes, computes the unpolarised Stokes-I response
`0.5 * (|HH|² + |HV|² + |VH|² + |VV|²)`, and normalises it to its peak. Bilinear interpolation
evaluates its half-power contour. Squint and ellipticity remain in the measured pattern; no
lambda/D width replaces a missing measured product. The supplied Y axis is flipped onto upward
sky coordinates as the release's orientation note specifies. Horizontal and vertical axes are
recomputed from the boresight's instantaneous azimuth and elevation, so the measured mount-frame
pattern rotates appropriately relative to a fixed celestial pointing. [Orientation note](https://archive-gw-1.kat.ac.za/public/repository/10.48479/wdb0-h061/beam_orientation_diagram.pdf).

Both complete orbit vectors are transformed from TEME to ITRS at every sample with the same
Earth-orientation information, then the observer is subtracted. A fixed ICRS boresight is
transformed to the same local frame; no atmospheric refraction is applied. The algorithm finds
each curve's closest approach, response maximum and half-power entry/exit roots. It evaluates
nominal near misses as well as nominal entrants, and records false crossings, missed crossings,
timing residuals, full instantaneous angular error and search-boundary censoring. The code is
in `radio/site.py` and `radio/crossings.py`; the bounded case runner is `radio/track_benchmark.py`.

The corrective experiment uses the four existing 2024 windows only. At each stored trial lead,
the nominal satellite must be 15–85° above MeerKAT's horizon. Constructed fixed celestial
pointings sample the nominal centre and both sides of the measured half-power boundary,
including exterior near misses. Each pair is searched for ±180 s. The full interval and its
two halves separate geometric disagreement from timing across an observation boundary. The
same orbit curves serve all beams and pointings. Missing reference coverage, propagation errors
and nominal visibility exclusions are counted. This is conditional on nominal visibility: it
does not count truth-visible objects whose nominal prediction is below the eligibility cutoff.
These pointings are a constructed experiment, not an archived observing schedule or measured
satellite detections. Results belong to this selected reference-mission population and design.
All four windows were visible during this correction. The inherited `held-out` identifier means
the October window; it does not make the corrective radio comparison a new untouched holdout.

The [completed comparison](radio/track-benchmark-v2.md) has 112 eligible trials from 94
element-set/window combinations and 12 missions; 10,198 rows fail the nominal visibility gate.
Across the full ±180 s interval, its 6,048 constructed cases contain 687 false crossings and 53
missed crossings. Exact boundary pointings account for 642 and two respectively. The separately
reported seven-offset stratum, excluding the prespecified ±1 offsets, has 45 false crossings
among 2,016 predicted entries and 51 missed crossings among 2,022 reference entries. These
descriptive rates depend on the constructed pointing distribution. The linked report retains
all boundary cases, conditional timing denominators, per-channel results and observation-edge
effects; it does not infer a population accuracy guarantee.

## The public-record illustration

GCN 36362 reports an S4 observation of EP240414a on 23 April 2024. The demonstrator assumes the
counterpart coordinates from GCN 36105 because the actual phase centre is absent; calibrator
scans and slew boundaries are unknown. Its stored circular-aperture calculation predicts two
debris passages. It does not observe those fragments or validate crossing accuracy.
[Observation record](https://gcn.nasa.gov/circulars/36362), [counterpart position](https://gcn.nasa.gov/circulars/36105).

The historical model selects the latest archived element epoch before an observation cutoff.
It does not reconstruct when that element set became publicly available. Therefore it is an
epoch-filtered reconstruction, not a catalogue proven to have been available to an observer at
the time. Constellation counts include retired catalogued objects and say nothing about which
ones transmitted. The May report has no public pointing record and reports visibility counts.

The archive client reads public observation metadata through SARAO's documented GraphQL API,
using `SARAO_ARCHIVE_TOKEN`, and keeps its exports in ignored `data/archive/`. The original run
had no token and did not query an archived schedule. [Archive help](https://archive.sarao.ac.za/help).

## Proposed SatChecker-shaped metadata

The export is a proposal, not an accepted IAU CPS schema. SatChecker already returns element
epoch and position time, supports source selection and optional orbital data, and documents
source-dependent position errors. Element age is therefore a convenient derived field, not a
new independent accuracy measurement. [FOV API](https://satchecker.readthedocs.io/en/latest/fov.html),
[accuracy notes](https://satchecker.readthedocs.io/en/latest/notes.html).

Schema 2 adds three structured objects:

| Object | Meaning and required limits |
| --- | --- |
| `orbit_quality` | Element-epoch age, calibration applicability and an optional conditional reference-population component estimate. Identity must be one of the reference missions, scope must explicitly establish the manoeuvre-excluded public-GP analysis, and age must be 6–168 h. An eligible estimate names its method version, reference-row hash, window/lead and trial, mission and element-set counts. Other objects get `unsupported` and a null estimate. Altitude overlap alone does not calibrate a satellite. Publication age is unknown. |
| `radio_band` | Declared emission-frequency overlap with a receiver, accompanied by source, direction and dates. It is not the beam frequency, actual transmission, received power or an interference flag. Operational validity dates stay null when unknown. The FCC direct-to-cell order's 26 November 2024 publication is recorded as later evidence, not proof of April/May operation or South African authorisation. |
| `candidate_discontinuity` | A heuristic element change bracketed by element epochs, plus a mark using a later archived set when available. Neither a physical manoeuvre nor a catalogue fit arc is known from this alone. Unknown evidence stays null; false does not establish absence of a manoeuvre. The retrospective mark has no demonstrated publication-time availability. |

The former `crossing_horizon`, `position_horizon` and `fit_arc_spanned_manoeuvre` export fields
are removed. The last field mistook an assumed 24-hour exclusion interval for a known fit arc.
Whether IAU CPS would accept these narrower objects is for its maintainers to decide; the
repository has no institutional endorsement or upstream acceptance record.

## Reproduction

```bash
uv run driftwatch radio horizon
uv run driftwatch radio emissions
uv run driftwatch radio archive quiet-2024-04
uv run driftwatch radio period quiet-2024-04 --observations data/archive/sarao/quiet-2024-04.csv
```

`radio horizon` retains its command name for compatibility but writes component diagnostics.
Historical `radio period` output remains an analytic circular-aperture illustration. Corrected
track comparisons require the explicitly selected measured products. The beam source has a
CC BY-NC 4.0 licence; its cached data are third-party inputs, separate from the repository's MIT
code licence. Source URLs, measurement conditions, array/channel choices and byte hashes are
stored beside each cached slice.
