# Findings, limitations and corrections

Measurements below identify their populations and source products. Corrections preserve the earlier limitations and withdrawn interpretations.

**The measured horizon.** Against ESA's precise orbits for Swarm A, B and C, a public
element set keeps the satellite inside the 25 km in-track half-width of the screening box, at the
95th percentile of trials, for **five days** in a quiet week, **two days** in the May 2024 storm and
**one day** in the October 2024 storm (item 6; `docs/calibration-benchmark.md`). Every probability
on this page, in the report and in the viewer is read after that number, not before it: a
probability computed from a set propagated past its horizon is arithmetic on a position the set no
longer predicts. The quiet scenario is the default everywhere. A storm scenario is chosen
explicitly, and every storm number carries the benchmark's calibration beside it: the covariance
under-covers in a storm. **Correction:** correction performance depends on
the period: it hurts May's 12–72 hour sample but helps October's 6–120 hour sample, and hurts
the quiet 1–6 day sample. The earlier summary that it always hurts inside three days was too
broad. At seven days it over-corrects in May. The sampled Swarm tolerance results do not
establish universal operating horizons for other spacecraft.

### 1. The public catalogue's fit to an operator's ephemeris drifts from it by kilometres inside a day

CelesTrak publishes SGP4 element sets fitted to SpaceX's own Starlink ephemerides, with a fit
residual of about 0.20 km. That residual is measured over the arc the fit was made on, not over
the 72-hour file. Measured directly on nineteen matched files (2026-09-03), the propagated element
set sits this far from the published states, almost all of it along track:

| Lead from the file's start | under 12 h | 12 to 24 h | 24 to 36 h | 36 to 48 h | 48 to 60 h | 60 to 72 h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Median distance | 0.30 km | 2.8 km | 11.5 km | 28.3 km | 51.8 km | 82.9 km |

Two consequences were recorded rather than tidied away. Phase 2 had patched the gap with the 0.20 km
residual in quadrature and measured that the patch moved no flag; that measurement was true of the
patch and not of the error, which is a hundred times larger at the far end. And serving SpaceX's
published covariance on top of a trajectory 83 km away understated the uncertainty on the events
furthest ahead. So Stage C now screens on the published states themselves where they exist
(`docs/methods.md`, "Where an operator publishes states, those are the trajectory";
`docs/spacex-ephemerides.md`).

**Scope qualification.** The headline is one lead bin of a six-bin
table, measured on nineteen satellites on one date, against the operator's *published prediction*
rather than the realised orbit: a 72-hour file carries planned burns and the operator's drag model,
and whether the fit or the file is nearer where the satellite went cannot be told from it. The
lineage of each pair was then checked, because a set fitted to one file and compared with another
would be measuring the revision of the plan as well: a supplemental set's epoch is the start of the
file it was fitted to, and of the 300 stored pairs from the same day 17 share their file with the
states they are compared against, 105 were fitted to an earlier file and 178 to a later one. All
three give the same curve (the 17 verified pairs: 0.29, 2.8, 11.8, 27.6, 51.8 and 82.2 km by bin),
so the disagreement is not the plan changing between files. What stays open is why the fit drifts:
past 24 hours it runs ahead of the file on nine of the verified objects and behind on eight, which
planned manoeuvres inside the file would do and fit noise in the mean motion would do equally, and
only the next file's first states, the nearest thing to a realised trajectory SpaceX publishes,
could separate them (`docs/spacex-ephemerides.md`, "Lineage, checked").

### 2. The published files are in a different frame from the one the catalogue uses, and only the filename says so

SpaceX's states are in MEME (J2000). The file header names the covariance frame and never the
states'. MEME is 0.36 degrees from TEME by 2026, about **44 km** at low Earth orbit radius:
measured on six satellites' files (2026-09-03), with the states compared at the ephemeris start,
read as TEME the states sit a median 36.2 km from CelesTrak's fit to the same file, rotated into
TEME they sit a median 0.356 km away, which is the published residual. Getting this wrong would have introduced a 44 km
error in the course of removing a 0.2 km one, silently. Every fetch re-runs the comparison and
refuses to write the store if it fails (`docs/ephemeris-frame.md`).

**Corrected 2026-09-05: the same class of error, in the time system.** ESA's Swarm precise orbits
are written in GPS time, which the SP3 header declares and the benchmark's first reader did not
honour. Read as UTC, every truth state was the satellite 18 s further along its orbit, and the
benchmark's first run showed a constant **137 km** in-track offset at every lead (18 s at 7.6 km/s).
Nothing internal could have caught it: the element sets agreed with each other as well as ever,
the covariance fit was unchanged, every test passed, and the offset was the same size at six hours
as at seven days. Only the comparison with an independent truth made it visible, as a residual that
refused to grow with lead. The reader now converts GPS and TAI epochs through the leap-second table
and a test pins the 18 s (`docs/calibration-benchmark.md`, sources). The lesson is the frame's: a
constant offset between two conventions is invisible to every check that compares a source with
itself, and this project had no other kind of check until item 6.

**Corrected 2026-09-05: the covariance fit read outside the window it was labelled with.** A third
error of the same class, in provenance rather than in a frame or a clock. A live run's fit passed no
epoch bounds to the history load, so it read every stored element set for its objects, and its
covariance block then labelled the result with the 45-day backfill window. The 3 September run's
fit, labelled 21 July to 3 September 2026, had read 2,714,544 element sets, of which **615,648 lay
before the window**: 513,838 from April and May 2024, stored by the storm validation for 13,440 of
its 22,646 objects; 8,387 from 2022, stored by the Starlink validation; and 93,423 from 19 and
20 July 2026, the earlier run's backfill days. Only a historical replay had been bounded. Every
internal check passed, because a fit reads whatever it is given and the label was written from the
configuration rather than from the data. The fit now reads only its recorded window,
`fit_covariance` refuses rows outside the window it is labelled with, and a test fails if a fit
reads outside it. Refitted on the same run with the bound in place
(`data/conjunctions/step3-bounded/`, the original kept beside it): 610,130 sets left the fit, 222
objects moved from their own fit to a pool, the in-track one-day sigma changed on 21,644 of 22,039
fitted objects (median −5 per cent, tenth percentile −49 per cent), and the fleet members' own
in-track sigma fell by a median 47 per cent, because their 2024 rows were from solar maximum. Under
`quiet`, 21 flagged events became 12 (11 lost, 2 gained; one red became two), the region changed on
285 of 6,224 events, and the ratio of the probability after to before has a median of 0.98, a fifth
percentile of 0.15 and a ninety-fifth of 2.5. Under the storm scenarios the same: `forecast` 20 flagged events became 12 (10 lost, 2 gained), `storm-g4` 18 became 11 (9 lost, 2 gained), `storm-g5` 18 became 12 (9 lost, 3 gained), the region changing on 277 to 286 events in each, and the median of the probability ratio 0.99 with a fifth percentile of 0.13 to 0.16 and a ninety-fifth of 2.5; the fleet members in-track sigma at the encounter fell by a median 26, 20 and 17 per cent under the three, less than under `quiet` because the storm variance term is added on top and is the same in both fits. The benchmark is unaffected: its
fits bound their own history to the weeks before each window, and the guard holds on them.

**Corrected 2026-09-07: the laser stations' coordinates locate a marker on the ground, and the
telescope is not on it.** A fourth error of the same class, in the realisation of a reference
frame rather than in its name. The laser-ranging comparison of item 8 placed each station at its
SLRF2020 coordinates, and its first run showed residuals of **−1 to −3.5 m** at four stations,
Yarragadee, Greenbelt, Monument Peak and Hartebeesthoek, the NASA MOBLAS systems, on every
satellite in every window, growing with elevation, while the fixed European stations sat at zero.
SLRF2020 gives the position of a station's ground marker; the telescope's reference point is offset
from it, by 3.18 m upward at Yarragadee, and the offset is published separately, in the ILRS site
eccentricity file, which the first reader did not apply. A vertical offset shortens the range by
its projection on the line of sight, the height times the sine of the elevation, which is why the
residual grew with elevation and vanished at stations whose telescope stands on its marker. Nothing
internal could have caught it: the offset is the same for every satellite and every epoch, and per
mission it looked like a modest centre-of-mass correction. It was exposed by comparing the two
independent references per station rather than per mission, where the residual turned out to be a
property of the station and not of the orbit. The eccentricities are now read from the ILRS file
and applied to every station, a test pins Yarragadee's, and the per-mission medians of item 8 are
−0.1 to −0.6 m.

### 3. Every published file has a seam at exactly 48 hours

Ten of ten files, then nineteen of nineteen: the position steps by a few hundred metres at
exactly 48 hours after the file's start, and the published velocity there disagrees with the
central difference of the positions by 16 m/s. It is at the same lead in every file, so it is not
a manoeuvre; the header labels the product `blend`, and two arcs joined at a fixed offset with no
attempt to match derivatives is the likely explanation. An interpolant must not span it, and any
use of these files that assumes one smooth 72-hour arc is wrong by a few hundred metres for part
of it (`docs/methods.md`, screening; `docs/spacex-ephemerides.md`).

### 4. The storm term has demonstrated skill for one population, at one end of the window, on one storm

The in-track displacement a storm produces was measured against the May 2024 Gannon storm as a
forecast test: each object's last pre-storm element set propagated through the storm and compared
with the sets issued during it, against a quiet control at the same lead times
(`docs/storm-validation.md`).

- **It has skill only where the ballistic coefficient was measured from the object's own decay**,
  and **no demonstrated skill** for an object carrying a B\* inversion or a population stand-in (a
  B\* coefficient regresses at slope −1.39; the free-flying population as a whole is uncorrelated).
  Every event therefore carries `storm_validity`, and every aggregate is reported over the validated
  events, the indicative ones and both, never both alone. The correlation of 0.88 this bullet used
  to quote for the measured population is withdrawn as a headline (item 5, third claim): it was 0.64
  when the sample was redrawn on 2026-09-05, and no correlation is quoted.
- **The skill is concentrated at three to four days of lead and is near zero inside two**
  (recomputed 2026-09-05, and reproduced on a redrawn sample the same day). On the validated
  population the observed sign agrees with the predicted one on 39 and 41 per cent of comparisons
  at one and two days on the first draw and 38 and 33 on the second, chance being 50, and on 91 and
  96 per cent at three and four (88 and 97 on the second draw); the robust slope is −0.15 and −0.04
  inside two days against 0.63 and 0.71 beyond (−0.12 and −0.09 against 0.63 and 0.75). The
  quiet-time propagation error is already 8 to 10 km at three days, and a predicted storm shift of 2
  to 5 km at one or two days is inside it. A storm forecast one or two days out is an uncertainty on
  an event, not a correction to it.
- **NRLMSIS 2.1 over-predicts the storm's three-day density enhancement by 22 to 23 per cent** (the
  two draws) over 450 to 2,000 km with no resolvable altitude dependence, in the opposite direction to the
  published accelerometer assessments, which measure a different quantity (the peak, at a point).
  Recorded and deliberately not applied; a test pins the untuned prior.
- **Corrected 2026-09-05: the term must not be applied to operator-controlled objects.** A
  trajectory that is the operator's — SpaceX's published states, or CelesTrak's fit to them —
  already carries the operator's drag model and planned burns, so the excess over SGP4's
  atmosphere is undefined for it, and a station-kept satellite will burn rather than drift.
  Before the correction every object with a coefficient was displaced, which put shifts of up to
  31,000 km on Starlinks whose supplemental B\* described a thrusting plan and reported their
  events as "outside the linear theory" — 42 objects on the 1 September run, 36 on the
  3 September one, every one a Starlink, and explained at the time as a physical population in
  the densest shell. That explanation was wrong: it was this category error seen from the other
  side. Such objects now get no mean shift, are labelled `operator-controlled`, and an event with
  one such side is judged on its free-flying side alone (`docs/storm-term.md`, "Corrected
  2026-09-05"). Rescored, the 3 September run has no unscoreable event; its `forecast` tally moved
  from 0 red, 16 yellow and 71 unscoreable to 1 red, 19 yellow and none, and the storm scenarios
  likewise, the one red being the dilution-region flag in item 5.

### 5. Three withdrawn headlines

**"A storm lowers the probability on most events, because the two objects are displaced alike."**
Falsified twice. The explanation, common-mode cancellation, went on 2026-09-03: the diagnostic
built to test it found the relative displacement that reaches the miss to be a median **1.91
times** the mean of the two objects' own displacements, out of a possible 2, flat across
coefficient sources and across the altitude difference between the two orbits, because a
conjunction is a crossing at a median 120° between the two in-track directions. The result itself
went on 2026-09-05: the lowering — a median `pc / pc_variance_only` of 0.16 to 0.40 on the
validated events — lived entirely in events with an operator-controlled side, displaced by the
category error in item 4. On the 981 events of the 3 September run with both objects free-flying,
whose displacements were legitimate and which the correction did not touch, the probability is
lowered on 55 and raised on 43 under a G5, at a median ratio of 0.98. What is measured now is
narrower: on this fleet the storm term moves a free-flying event's probability little either way
(median relative displacement 2 to 7 km against covariances of kilometres to tens of kilometres),
the two displacements of a free-flying pair are nearly independent (1.85 of 2), and no general
claim about the direction should be made until a fleet with low free-flying primaries has been
screened through a real storm (`docs/storm-term.md`, "Attacking the result" and "Corrected
2026-09-05").

**"Screening on the operator's own published states gives the demo fleet its one red flag."** The
flag exists — EOS SAT-1 against Starlink 61705,
2.780 km at a fifteen-hour lead, probability 1.076 × 10⁻⁴ against 6.19 × 10⁻⁶ on the catalogue's
fit — and the write-up quoted it as a red. Corrected 2026-09-05: it is **in the dilution region at
low confidence**, with its maximum probability over covariance scale factors at 0.85 times the
covariance in hand, so the number is held up by the size of the uncertainty rather than by the
geometry and is not an actionable warning. Every mention now leads with the region and the
confidence, in the notes, the report and the viewer. What survives is that the choice of
trajectory moved a dilution-region probability across the red threshold at a fifteen-hour lead,
which the term Phase 2 carried for that choice could not have done (`docs/writeup-notes.md`).

**"The storm term is predictive at r = 0.88 where the coefficient is measured."** Withdrawn
2026-09-05 by the project's own rerun of the validation, made to write the lead-time table into
`gannon.json`. The sample is drawn from the latest snapshot, and the redraw shared four objects with
the 2 September draw: 101 measured-coefficient objects and 498 comparisons against 81 and 422, and
a correlation of 0.64 against 0.88. On the four shared objects the two runs agree to the third
decimal, so the code did not move; the statistic did, because a Pearson correlation on this
population is carried by its largest events (dropping the largest two per cent of predictions takes
0.88 to 0.68 and 0.64 to 0.55) and the two draws had different large events. What reproduced: the
robust slope (0.65, then 0.68), the sign agreement at three and four days (91 and 96 per cent, then
88 and 97), the absence of skill inside two days, the density over-prediction (22 per cent, then 23)
and the absence of skill without a measured coefficient. So `validated` on a row means what it
always meant, that both coefficients were measured, and the claim behind it is the bounded one
below, with no correlation in it (`docs/storm-validation.md`, "Redrawn 2026-09-05").

**What the storm work shows, bounded (2026-09-05).** On one storm, May 2024, for free-flying
objects whose ballistic coefficient was measured from their own decay, the storm term's predicted
in-track shift agrees in sign with the observed one on about nine comparisons in ten at three and
four days of lead (91 and 96 per cent on one draw of the sample, 88 and 97 on another), with a
robust slope of 0.63 to 0.75; inside two days the sign agreement is below chance and the robust
slope is zero or negative; without a measured coefficient there is no demonstrated skill at any
lead. NRLMSIS 2.1 over-predicts the storm's three-day density enhancement by 22 to 23 per cent on
the two draws, and nothing is tuned to it. No correlation is quoted, because the one that was moved
from 0.88 to 0.64 between draws. What none of this measures: the term's skill on a second storm, its
calibration against an independent truth (the later element sets are fits by the same network, so
the comparison bounds the error in neither direction), the direction in which a storm moves a
free-flying event's probability, or the covariance driftwatch puts around any event, which the
Kelvins reproduction does not calibrate either. The sample is drawn from today's catalogue, so the
3,891 objects that decayed since May 2024 are absent from it.

### 6. Against an independent reference, storm-period error exceeds consistency estimates; correction skill depends on period and lead 

The first comparison in this project of a public element set with something that is not another
fit by the same network. ESA's Swarm A, B and C carry GPS receivers and ESA publishes a
reduced-dynamic precise science orbit for each (`SW_OPER_SP3xCOM_2_`, ten-second states, centimetres),
so every public element set issued in a window can be propagated with SGP4 to leads from six hours
to seven days and measured against where the satellite actually was, in its own radial, in-track,
cross-track frame. Three windows: a quiet control (20 to 27 April 2024, Kp at or under 4), the May
2024 storm (sets issued 6 to 13 May), and the 10 to 11 October 2024 storm, **held out from every
tuning** — the covariance and the ballistic coefficient used on each window are fitted from the 45
and 36 days of history before it, and no threshold was chosen by looking at October. **One element
set is one trial**, one residual per lead, never one per timestamp. Swarm A and C fly at 460 to
470 km, B at 500 to 506 km; 57, 54 and 61 sets in the three windows. Manoeuvres are excluded from
ESA's own thruster record (`SW_OPER_SC_xDYN_1B`): two orbit manoeuvres in 150 satellite-days, Swarm A
on 15 October and Swarm B on 17 October, both of which the project's step detector on the precise
orbit found independently and nothing else; the element-set jump detector, left to itself, would
have read the 11 October storm as a burn on A and C and thrown away the storm-time trials
themselves. `docs/calibration-benchmark.md` has every number; `driftwatch validate swarm` rewrites it.

**The residual.** In-track, median absolute, at 6 h / 24 h / 72 h / 7 days: quiet **0.3 / 0.5 / 3.2 /
24 km**; May storm **0.5 / 0.8 / 7.2 / 75 km**; October storm **0.9 / 1.8 / 15 / 49 km**. The 95th
percentiles at 7 days are 62, 197 and 652 km. Radial and cross-track stay under a kilometre at every
lead in every window.

**The covariance's coverage.** The empirical covariance is fitted from the consistency of each
satellite's own element sets, and item 5 said that bounds the accuracy in neither direction. Now
measured: in the quiet week it **over-covers** from one to five days (82 to 96 per cent of residuals
inside one sigma against the 68 claimed; 98 to 100 inside two) and **under-covers** inside twelve
hours (37 to 49 inside one sigma, 60 to 75 inside two), where it sits on its half-day floor. In both
storms it under-covers at every lead: two sigma contains **65 to 80 per cent** of the May residuals
and **62 to 75 per cent** of the October ones against the 95 it claims, one sigma 33 to 76 and 31 to
63. A covariance fitted from quiet history does not grow with a storm, and nothing in the
consistency of pre-storm fits could have told it to.

**The storm term with the observed ap.** Applied to the untreated SGP4 residual, the term (the
in-track shift from the density excess over what the set's own drag term implies, driven by the
observed ap and a coefficient measured from the satellite's own decay) **reduces the May residual
only from four days of lead**: +20, +42, +48 and +41 per cent on the median at 4, 5, 6 and 7 days,
with 54 to 76 per cent of trials improved, and **increases it from 12 hours to three days** (−64,
−68, −287, −93 and −22 per cent at 12, 24, 36, 48 and 72 h). On the sets issued before the onset and
propagated across it, the 7-day median falls from 75 to 44 km and the 95th percentile from 197 to
57 km. Its magnitude is too large: at 7 days the median predicted shift is 100 km against an
actual 64. In the held-out October storm the term helps from six hours to five days (+5 to +43 per
cent) and hurts at six and seven days (−3, −12): the sets issued after the 7 to 8 October storm
over-predict the decay for the quiet days that followed (the satellite is *behind* the prediction
by 4 to 23 km at two to three days, consistent with a `B*` fitted across that storm), and the term
with the observed ap has the sign of that too. **In the quiet control it makes the residual worse
from one to six days** (−10 to −96 per cent): the excess it integrates is not zero without a
storm, because the density the set's `B*` implies is not the model's quiet density, and by seven
days its shift is twice the actual drift with the same sign. This is the lead-time split of item 4
measured against a truth: skill at three to four days and beyond, none inside two, and a bias in
quiet conditions that the element-set comparison could not see.

**The horizon, for a named task.** Keeping the satellite inside the in-track half-width of the
screening box driftwatch searches, 25 km, at the 95th percentile of trials: **five days** in the
quiet week (39.7 km at six), **two days** in the May storm (35.7 km at three), **one day** in the
October storm (37.5 km at 36 hours). An engineer screening on public element sets through a
storm has a day to two days of lead in which the coarse stage can be trusted to keep the object
inside its box, and the covariance carried beside it is too small by the numbers above.

**Why the covariance under-covers in a storm, in the order the evidence supports (2026-09-05).** The
primary explanation is the plain one: the covariance is fitted from the consistency of an object's
element sets over the weeks before the run, and a fit made on quiet history cannot describe
storm-time error, because nothing in how quiet fits disagree with each other says how far a storm
will move the object. The benchmark's own fits, bounded to the weeks before each window, are exactly
that, and they under-cover in both storms. A secondary mechanism exists and has a measured size. The
fit excludes pairs that span a detected manoeuvre, the detector reads an unexplained change in
semi-major axis as a burn, and a storm's drag is such a change; so where a storm falls inside the
fit window, the detector can throw the storm-time intervals away and calibrate the fit on the quiet
days either side. The benchmark watched it read the 11 October storm as a burn on Swarm A and C. It
matters only when a storm falls inside the window. The 3 September run's 45-day window held no
three-hour interval at Kp 6 or above (its maximum was 5.7), so none of the 17,033 intervals excluded
inside the window coincide with one. Where a storm did fall inside stored history, in the May 2024
rows the fit had read outside its window (the provenance defect in item 2), 155 of 4,617 excluded
intervals coincide with Kp 6 or above, 145 of them on Starlinks, which manoeuvre; and among the 17
free-flying objects whose stored history spans the 10 to 13 May storm, **2, both debris, had the
storm interval excluded as a burn**. Two of seventeen is the measured size of the secondary
mechanism, on one storm. Recorded; nothing in the detector was changed.

**What this does not show.** Three well-tracked satellites at two altitudes in one orbit class, one
week of sets per window; whether the ratio of actual error to consistency generalises to debris, to
higher orbits, or to objects the network tracks less often is not measured. Swarm's TU Delft density
products (`SW_OPER_DNSxPOD_2_`) could later separate the atmosphere's error from the object's
response in the storm-term result; they are not part of this week. And one construction lesson,
recorded because an independent truth is what made it visible: the benchmark's first run showed a
constant 137 km in-track offset at every lead, which was the precise-orbit files' GPS time read as
UTC, 18 s at 7.6 km/s; the reader now converts through the leap-second table and a test pins it.

**Two decisions the benchmark leaves open (2026-09-05).** Neither is made here. First, the
**quiet-condition baseline**: the storm term's excess is not zero without a storm, and it hurts from
one to six days in a quiet week. That wants a diagnosis before it is zeroed or subtracted, because
the excess is the difference between the model's quiet density and the density the set's `B*`
implies, and the same difference is inside the four-day-and-beyond result that helps; zeroing the
shift below some ap would remove a symptom whose cause is still in the term. Second, a
**storm-conditional covariance scale**: the under-coverage in a storm is by known factors on one
orbit class and two storms, and any scale must be fitted on May 2024 and validated on October 2024,
held out as the benchmark held it, or it is a tuning on the number it is meant to predict. Both are
in `ROADMAP.md`.

### 7. On the sky, the horizon is two quantities, and only one of them moves

The radio lane (`docs/radio-lane.md`) converts the benchmark's residuals into angles at the MeerKAT
array centre and tests them against a third of the primary beam's half-power width, per altitude
band of item 8, each object scored against its own band's trials. Two horizons result, and they
answer different questions. The **crossing horizon**, governed by the cross-track error, answers
whether an object crossed the beam during an observation: the cross-track residual stays under
3.4 arcmin at the 95th percentile at every lead in every window in every band, so it holds for the
benchmark's full seven days in every band and window at every receiver, with one exception (5 days
at 600 to 750 km in the August 2024 window), and the crossing's time is known to the along-track
shift (at 400 to 600 km, 0.2 s at the 95th percentile at six hours; 8, 25, 72 and 29 s at seven
days in the quiet, May, October and August windows). The **position horizon**, governed by the
along-track error, answers where an object is at an instant to within a third of the beam, and it
is the one a storm moves, and altitude lengthens: at the L-band centre **24, 12, 6 and 12 hours at
400 to 600 km** in the quiet, May, October and August windows; 24, 24, 12 and 36 hours at 600 to
750 km; 6 days, 2 days, 6 hours and 3 days at 750 to 850 km; 7, 7, 3 and 7 days at 850 to
1,000 km; 7, 3, 7 and 7 days at 1,338 km. **S-band position prediction from public element sets is
not possible at any element-set age at 400 to 600 km**: at the top of the band the position horizon
is under six hours, the benchmark's shortest lead, in every window. Higher it is possible: at the
top of S band, 12 hours in the quiet and May windows at 600 to 750 km, 3 days in the quiet week at
750 to 850 km, the full seven days in the quiet week at 850 to 1,000 km with 12 hours to 4 days in
the storms, and seven days in every window but May (36 hours) at 1,338 km. Both rest on the
population of item 8, the band table of `docs/radio-horizon.md`; every object outside it carries
*no measured horizon* for both.

### 8. Fifteen more spacecraft in five altitude bands: the storm's reach in the horizon ends near 700 km

The reference expansion (`docs/reference-benchmark.md`) extends item 6 from three Swarm satellites
to every mission whose reconstructed orbit an anonymous server hands out: GRACE-FO 1 and 2 (JPL
Level-1B navigation through GFZ's ISDC, with the THR1B thruster record as the published manoeuvre
record), Sentinel-1A (Copernicus precise orbits through ESA's STEP mirror), and the DORIS satellites
CryoSat-2, SARAL, Sentinel-3A and 3B, SWOT, HY-2C and 2D, Jason-3 and Sentinel-6A (CNES precise
orbits through the IDS data centre at IGN). ILRS laser-ranging normal points are a second,
independent truth for every mission with a retroreflector and the only truth for TerraSAR-X,
TanDEM-X and ICESat-2, whose 2024 orbits sit behind accounts. Sentinel-2, GOCE and CHAMP are not
covered, and the page says why rather than substituting. The same four windows for every mission,
with the 12 August 2024 storm (Kp 8-) added and held out like October; the same rule that the
covariance and the coefficient are fitted from history that ends where the window's sets begin.
1,201 element sets over fifteen spacecraft with a reconstructed orbit, 460 to 1,338 km.

**The horizon by altitude band** (25 km in-track at the 95th percentile of trials), quiet / May /
October / August:

| Band (mean altitude of the sets) | Spacecraft | quiet | May 2024 | October 2024 | August 2024 |
| --- | --- | --- | --- | --- | --- |
| 460 to 507 km | Swarm A, B, C; GRACE-FO 1, 2 | 5 d | 2 d | 24 h | 2 d |
| 696 to 719 km | Sentinel-1A, CryoSat-2 | 5 d | 5 d | 7 d | 5 d |
| 783 to 803 km | SARAL, Sentinel-3A, 3B | 7 d | 7 d | 5 d | 7 d |
| 893 to 952 km | SWOT, HY-2C, 2D | 7 d | 7 d | 7 d | 7 d |
| 1,338 km | Jason-3, Sentinel-6A | 7 d | 7 d | 7 d | 7 d |

GRACE-FO, at 490 km, agrees with Swarm window for window (6 d, 2 to 3 d, 24 to 36 h, 2 d), which
is the first reproduction of item 6 on a different spacecraft with a different producer's orbit and
a different published thruster record. At 700 km a storm no longer shortens the horizon below the
quiet week's five days; at 800 km and above the horizon is the benchmark's full seven days in every
window but one: October at 800 km is 5 d (31 km at 6 d), carried by SARAL (4 d) and Sentinel-3A
(5 d) while Sentinel-3B holds 7 d. The 7-day in-track median at 1,338 km is 0.4 to 0.8 km in three
windows and 4.4 km in May.

**Corrected 2026-09-07: the two manoeuvre-exclusion paths used different spans, and the detection
path was brought to the record path's.** In the first run of this expansion the October figure at
800 km was 3 d, carried by Sentinel-3B while Sentinel-3A, in the same orbit, held 7 d; 3B was also
the short mission in the quiet week (4 d) and in August (4 d). The two spacecraft are alike in every
element-set property compared: B-star of the same sign and size with no sign change in any window,
the same spread of epochs; they differ in cadence, a set every 6.7 hours for 3A against every 10 to
13 hours for 3B (27 against 13 sets in the October window). No thruster record is published for
either, so their manoeuvre exclusion rests on the reconstructed orbit's own step detector, which
finds one burn per spacecraft per window (two for 3A in October, two for 3B in August) and which the
element sets never show, the set-jump detector finding none. The cause was in the exclusion rule.
The record path (Swarm, GRACE-FO) had from the first run dropped every set with a burn in the 24
hours before its epoch, the tracking arc the set was fitted from, since such a set is wrong from its
epoch on; the detection path had not: it dropped only pairs whose propagation arc, from the epoch to
the lead, crossed the burn. Every short 3B window was carried by the one set issued a few hours
after that window's burn (10 October 10:20 UTC, an hour after a burn ending 09:25, +33 km at four
days; 25 April 14:38, +25 km; 13 August 22:11, +30 km), and with 7 to 10 usable sets per window one
such set is the 95th percentile. The record path's rule was extended to the detection path without
change, the same 24-hour arc (`precise.MANOEUVRE_ARC_HOURS`) on both, and the benchmark rerun with
nothing else altered. The extension was applied after the results on the held-out windows had been
seen: the rule and its arc were fixed on the record path before any held-out result existed and
were not tuned, but the decision to apply them to the detection path was taken with the October and
August results in view, and the held-out figures in the two bands it moved carry that
qualification. It moved the 750-850 km October horizon up, from 3 d to 5 d, and the 600-750 km
August horizon down, from 6 d to 5 d; the 460 to 507 km result, the five spacecraft with a published
record, is unchanged in every window. Per mission: Sentinel-3B from 4 d, 7 d, 3 d, 4 d to 7 d, 7 d,
7 d, 5 d; CryoSat-2 in August and Sentinel-1A in May from 6 d to 5 d; SWOT in October from 5 d to
7 d; Sentinel-3A in October from 7 d to 5 d, because the pairs the arc removes were well-behaved
ones and the set of 11 October 03:49, issued into the storm, now carries the 95th percentile on 25
sets; the usable sets from 1,228 to 1,201. The table above is the corrected one; the table as it
stood before the correction is kept here, and `docs/reference-benchmark.md` keeps both of its
tables beside the correction:

| Band (mean altitude of the sets) | Spacecraft | quiet | May 2024 | October 2024 | August 2024 |
| --- | --- | --- | --- | --- | --- |
| 460 to 507 km | Swarm A, B, C; GRACE-FO 1, 2 | 5 d | 2 d | 24 h | 2 d |
| 696 to 719 km | Sentinel-1A, CryoSat-2 | 5 d | 5 d | 7 d | 6 d |
| 783 to 803 km | SARAL, Sentinel-3A, 3B | 7 d | 7 d | 3 d | 7 d |
| 893 to 952 km | SWOT, HY-2C, 2D | 7 d | 7 d | 7 d | 7 d |
| 1,338 km | Jason-3, Sentinel-6A | 7 d | 7 d | 7 d | 7 d |

The October figures at 800 km for SARAL (4 d, 25 km at 5 d) and 3A are storm effects on 17 to 27
sets, not diagnosed further. Why 3B's first post-burn sets are wrong by tens of kilometres and 3A's,
after burns of the same kind, are not was recorded open at the time; the next paragraph tests the
one property the two were seen to differ in.

**The cadence hypothesis, tested 2026-09-08.** The candidate explanation was the cadence of the
element sets. Tested on every benchmark mission with a burn inside a window's set span and a set
issued after it (`docs/reference-benchmark.md`, "The first element sets after a burn"): twelve burns
on six spacecraft at 700 to 950 km, Sentinel-1A, CryoSat-2, Sentinel-3A, Sentinel-3B, SWOT and
HY-2D, in all four windows, each burn placed by the orbit-step detector on the reconstructed orbit
to about an orbit either side; the recorded burns of Swarm and GRACE-FO all fell after their
windows' sets, so no record mission is in the population. The measure is the first set issued after
each burn, its absolute in-track residual at fixed leads, against the mission's cadence in that
window, the median gap between consecutive sets. The rank correlation with cadence at four days is
+0.78 per burn (n = 12, p = 0.003), and it is Sentinel-3B: its three burns are the three sparsest
cadences (10 to 13 hours against 6.6 to 8.6) and the three largest residuals (25, 30 and 33 km).
Without them the correlation is +0.48 on nine burns (p = 0.19), and with the spacecraft as the unit,
means over each one's burns, +0.66 on six (p = 0.16). **Error does not scale with cadence on this
population; the association is one spacecraft.** What holds at every level is the delay between the
burn and the first set's epoch: −0.71 per burn (p = 0.010), −0.62 without 3B (p = 0.077), −0.89 per
spacecraft (p = 0.019). The seven first sets issued within ten hours of the burn are wrong at four
days by 2.3 to 33 km (19 to 33 on Sentinel-3B and SWOT, 2.3 to 4.6 on Sentinel-1A and CryoSat-2);
the five issued twelve hours or later by 0.1 to 2.3 km; at a day, 0.6 to 9.6 km against 0.1 to 0.9;
twelve burns on six spacecraft in four windows, a split re-measured whenever a window is added.
The second set after every burn is within 5.3 km at four days and the third within 8.3. The burn's
size does not order it: Sentinel-3A's burns raised the semi-major axis by 66 and 75 m, as much as
3B's 41 to 65 m, and the two largest, HY-2D's 95 m and CryoSat-2's 86 m, left the smallest
residuals because their first sets came 59 and 10 hours later. So the two Sentinel-3 spacecraft
differ not in cadence but in when the network issued the first set after each burn: 3A's came 12
and 19 hours after its burns, 3B's 3 to 8 hours after, and the sparser catalogue got its first
post-burn set sooner. What is measured about catalogue production is this: a set issued within
hours of a burn is fitted across it and is wrong along track by kilometres to tens of kilometres
from its epoch, and the next set is not; how long after a burn the first set is issued differs by
object, and the sets do not say why. Why a set issued a few hours after a burn is wrong by 19 to
33 km on Sentinel-3B and SWOT and by 2 to 5 km on Sentinel-1A and CryoSat-2 is not ordered by
cadence, by delay or by burn size, and that part of the 3B question stays open. The radio lane's
per-object output and export now carry the time since the last detected manoeuvre and whether the
set's likely fit arc spanned it, with this measurement as the stated consequence
(`docs/radio-lane.md`).

**The fit each set carries, checked 2026-09-08: the contrast is explained.** Each of the twelve first
post-burn sets was put in the reconstructed orbit's convention (SGP4 over one revolution centred on
its epoch, the osculating semi-major axis averaged as the detector averages the orbit's; the
constant between the two conventions, 70 to 74 m for every mission and most of it the ten-second
finite-difference velocity the orbit reader carries, calibrated on each window's clean sets, whose
scatter is 2 to 6 m) and compared with the orbit at its own epoch rather than the
plateau after the burn, because CryoSat-2 at 717 km decays about 10 m a day and had moved 25 m
below the plateau by the time its sets were issued. The fraction of the burn a set contains is one
plus its error over the burn; the thresholds, a quarter and three quarters, and the rule that a
burn under three scatters is unresolved, were fixed before any set was classified
(`docs/reference-benchmark.md`, "What the first set after each burn contains"). Sentinel-3B's three
first post-burn sets contain 6, 4 and 12 per cent of their burns and SWOT's none (−7 per cent): they
are pre-burn fits with their epochs advanced past the burn, and the drift their error predicts,
three halves of the mean motion times the error times the lead, reproduces the observed residual at
four days to within 20 per cent (−21, −34, −25 and −17 km predicted against −25, −33, −30 and −19
observed) and its growth with lead; the 0.5 to 3 km it falls short by is there already at a day,
the offset the set carries at its epoch. CryoSat-2's three contain 92, 106 and 85 per cent, Sentinel-3A's two 102 and
98, HY-2D's two 86 and 100: fitted after the burn, with errors of −7 to +5 m against the orbit at
their epoch, and residuals at the clear-arc level. Sentinel-1A's is unresolved by the rule, a 9 m
burn against a 15 m threshold, though its error at its epoch, −11 m, predicts its residual (−1.5 km
at a day and −6 at four against −1.5 and −4.2 observed), which is what a pre-burn fit of a small
burn would do. No set is mixed. So the mechanism, on twelve burns of six spacecraft in four windows:
**the first set after a burn is wrong by the part of the burn it does not contain, and whether it
contains the burn or is a pre-burn fit re-epoched past it differs by object, not by delay**:
CryoSat-2's set issued 5.4 hours after its burn already contained it, Sentinel-3B's issued 3 to 8
hours after did not. The delay split above is therefore a description of this sample, in which the
re-epoched sets happened to be the ones issued within ten hours. What stays open is why the network
re-epochs a pre-burn fit for some objects and refits after the burn for others; the sets do not say.

**Coverage of the empirical covariance** (in-track, inside two sigma, 95 per cent claimed). At 460
to 507 km on five spacecraft item 6 repeats: 98 to 100 per cent in the quiet week from one to seven
days, 65 to 84 per cent in the storms, and 33 per cent at seven days in August. Above 600 km the
storms still under-cover at a day (67 to 85 per cent). At 1,338 km the covariance under-covers in
every window, the quiet week included, for a reason of its own: item 9. The sixth-hour
under-coverage of item 6 (the half-day floor) is general: 17 to 57 per cent at six hours in every
band.

**The storm term** on five spacecraft at 460 to 507 km repeats item 6: it hurts in the quiet week
(−56 per cent at a day, −137 at three), hurts inside a day or two of a storm and helps from three
days (May +14 and +35 per cent at three and seven days; October +41 at three; August +14 and +12).
Above 700 km its effect is within about 30 per cent either way with no consistent sign, and at
1,338 km it is nil at a day, because the coefficient it needs is fitted from decay that is not
measurable there.

**How the two references disagree.** Reconstructed orbit against laser ranging, above 20 degrees of
elevation, Marini-Murray troposphere from the station's own meteorology, SLRF2020 stations with the
ILRS site eccentricities, no centre-of-mass correction: the median one-way range residual is
between −0.1 and −0.6 m for every mission but SWOT, and the 95th percentile of the absolute residual
is under 1.0 m for Swarm, GRACE-FO, SARAL, Sentinel-3, Jason-3 and Sentinel-6A, 1.4 to 1.5 m for
HY-2C and 2D, and 2.7 to 2.8 m for SWOT, whose residual is a constant −2.0 m in every window: the
retroreflector's distance from the centre of mass on a large spacecraft, uncorrected. A few outlying
normal points inflate the RMS to between 2 and 38 m in seven of the sixty mission-windows without
moving the median or the 95th percentile. The two references therefore agree at the metre level,
three orders of magnitude below the element-set residuals, and neither validates the other at its
own centimetre level. The station eccentricities were missing from the first run, and the error
they left is recorded with the others of its class in item 2.

**The element set against the laser**, median absolute range residual at a day and at seven days:
0.3 to 0.4 km and 7 to 20 km at 460 to 507 km, 0.2 and 1 to 5 km at 700 km, 0.2 to 0.3 and 0.5 to
2.5 km at 800 km, 0.2 and 0.3 to 3.5 km at 900 to 950 km, 0.1 to 0.2 and 0.3 to 0.6 km at 1,338 km:
the same picture in one dimension. For the laser-only missions, TerraSAR-X and TanDEM-X at 514 km
are at 1.5 and 0.6 km after a day and 44 and 49 km after seven in the quiet week, and ICESat-2 at
496 km at 0.7 km after a day; with three to thirteen sets in a storm window, no storm horizon is
stated for them.

**Population, for every downstream page.** Fifteen spacecraft with a reconstructed orbit in five
bands from 460 to 1,338 km, near-circular, free-flying between manoeuvres, one week of element sets
per window in four windows, with manoeuvre arcs excluded from a published record (Swarm, GRACE-FO:
one GRACE-FO 2 burn on 15 May 2024 took 38 set-lead pairs out) and from detection otherwise, with the
24-hour arc before each epoch on both paths, which took up to three fifths of the pairs out of some
Sentinel-1A and Sentinel-3 windows. Nothing is measured for
debris, for eccentric orbits, for station-kept constellations, for objects the network tracks less
often, or above 1,340 km, and a detection that reads storm drag as a burn removes trials from
exactly the intervals a storm benchmark needs; that failure mode is counted for Swarm in item 6 and
not measured for the detection-only missions.

### 9. At 1,338 km the consistency-derived covariance under-covers in quiet conditions, because the sets agree with one another better than with the truth

The empirical covariance is fitted from how an object's successive element sets disagree
(`docs/methods.md`, uncertainty and probability), and claims 95 per cent of trials inside two
sigma. At 460 to 507 km it holds in the quiet week (98 to 100 per cent from one to seven days,
item 8) and fails in storms. At 1,338 km, on Jason-3 and Sentinel-6A, it fails in the quiet week
as well, in-track, inside two sigma:

| Window | Median in-track residual at a day | Fitted one-day sigma | Inside two sigma at a day | At six hours |
| --- | ---: | ---: | ---: | ---: |
| quiet | 0.27 km | 0.26 km | **51 %** | 32 % |
| May 2024 | 0.45 km | 0.11 km | 6 % | 15 % |
| October 2024 | 0.32 km | 0.43 km | 81 % | 53 % |
| August 2024 | 0.27 km | 0.04 km | 9 % | 0 % |
| 400 to 600 km, quiet, for comparison | 0.37 km | 0.98 km | 98 % | |

The error is small; the sets' agreement with one another is smaller. Drag is negligible at that
altitude, so successive fits by the same network to the same tracking with the same force model
repeat one another closely, and whatever error they share, the fit's own systematic error, is
invisible to any measure of their consistency. The fitted sigma is a statement about the network's
repeatability, and it coincides with its accuracy only where a changing atmosphere makes successive
fits disagree by about as much as they are wrong, which is what happens at 500 km in a quiet week
and nowhere in a storm. Consequence: at 1,338 km the quiet-scenario probability is computed with an
in-track sigma smaller than the error in every window, and the first recorded candidate in
`ROADMAP.md`, a covariance scale validated on the held-out windows per altitude band, is the fix;
nothing on any page applies it yet, and the report's probabilities at that altitude carry this
item beside them.

### 10. ESA's dSGP4 reproduces SGP4 to the metre; its ML-dSGP4 hybrid, trained as published, is worse than SGP4 on both held-out storms

ESA's dsgp4 (Acciarini, Baydin and Izzo 2025, Acta Astronautica 226; version 1.3.0), run on the
reference benchmark's 1,201 usable trial sets (`docs/dsgp4-evaluation.md`): with WGS72 constants
it reproduces the sgp4 library's in-track residual to the metre at every lead in every window, and
with its default WGS-84 constants it differs by up to five per cent of the median, decametres at
seven days. Its ML-dSGP4 hybrid wraps the propagator in two small networks that perturb the mean
elements before the propagation and the state after it, and is trained against a higher-precision
reference by the mean squared error of the normalised state. The published training used an
operator's predictions in a quiet week, SpaceX's Starlink ephemerides, so the storm result is new.
Two hybrids were trained here on the quiet and May windows only, with the corrections starting at
zero so that the untrained model is exactly SGP4 and the epoch of lowest training loss kept: one on
Swarm (111 sets, 18,648 hourly truth states to seven days) and one on every mission with a
reconstructed orbit (625 sets, 105,000). A sweep of the learning rate over 10⁻³, 10⁻⁴ and 10⁻⁵ on
the Swarm set gave losses of 6.66, 6.73 and 6.77 × 10⁻⁶ against 6.80 at the zero start, so the
training does lower the published objective. It raises the residual. On the training windows the
Swarm hybrid's median in-track residual is 7 to 46 km against SGP4's 0.4 to 7 km and the
all-mission hybrid's 1.5 to 7 km; on the held-out storms neither improves one of the ten leads
(October at a day: 15 and 5 km against 0.64; August: 14 and 7 km against 0.45; at seven days in
October 92 and 16 km against 11). **The rule fixed
before the numbers were seen, adopt only if the held-out storms improve, says do not adopt.** The
mechanism is in the numbers: the objective is a mean of squared errors over every hour to seven
days, which the seven-day tail of tens to hundreds of kilometres dominates, so its optimum trades
the short leads for a small change at the tail, and a loss that fell by two per cent moved the
day-one residual by an order of magnitude. This does not say the hybrid cannot be made to help; it
says the published recipe, on public element sets against reconstructed orbits, did not, and the
storm term with the observed ap remains the only correction with demonstrated held-out skill, at
three days and beyond in a storm.

Everything above is indicative, not operational: the covariances come from the consistency of
public element sets, which measures how much successive fits by one network disagree and bounds
their accuracy in neither direction, because successive sets share observations and assumptions;
the calibrations against independent truths (items 6, 8 and 9) cover fifteen spacecraft in five
altitude bands and find that consistency under-covers the error in a storm, and at 1,338 km in the
quiet week as well; the Kelvins reproduction
validates the probability arithmetic on ESA's inputs and calibrates none of this; and the
probabilities are computed by the two-dimensional method, which is a known underestimate for slow
encounters.
`docs/methods.md` lists every approximation, with the precedent this rests on (Flohrer, Krag and
Klinkrad, 2008; Parker and Linares, 2024) and what is done differently.

_Last updated 8 September 2026._
