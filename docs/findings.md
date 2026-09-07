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

The radio lane (`docs/radio-lane.md`) converts item 6's residuals into angles at the MeerKAT array
centre and tests them against a third of the primary beam's half-power width. Two horizons result,
and they answer different questions. The **crossing horizon**, governed by the cross-track error,
answers whether an object crossed the beam during an observation: the cross-track residual stays
under 3.6 arcmin at the 95th percentile at every lead in every window, so for the measured
population it holds for the benchmark's full seven days in every window at every receiver, with the
crossing's time known to the along-track shift (0.2 s at the 95th percentile at six hours; 8, 26 and
85 s at seven days in the quiet, May and October windows). The **position horizon**, governed by the
along-track error, answers where an object is at an instant to within a third of the beam, and it is
the one a storm moves: at the L-band centre **24 hours in the quiet week, 12 hours in the May 2024
storm and 6 hours in the October 2024 storm**; at the UHF centre 36, 24 and 6 hours. **S-band
position prediction from public element sets is not possible at any element-set age**: at the top
of the band the position horizon is under six hours, the benchmark's shortest lead, in every window.
Both rest on three Swarm-class satellites at 460 to 506 km, not manoeuvring in the trials kept; every
other object carries *no measured horizon* for both (`docs/radio-horizon.md`).

Everything above is indicative, not operational: the covariances come from the consistency of
public element sets, which measures how much successive fits by one network disagree and bounds
their accuracy in neither direction, because successive sets share observations and assumptions;
the one calibration against an independent truth (item 6) covers three satellites in one orbit
class and finds that consistency under-covers the error in a storm; the Kelvins reproduction
validates the probability arithmetic on ESA's inputs and calibrates none of this; and the
probabilities are computed by the two-dimensional method, which is a known underestimate for slow
encounters.
`docs/methods.md` lists every approximation, with the precedent this rests on (Flohrer, Krag and
Klinkrad, 2008; Parker and Linares, 2024) and what is done differently.

_Last updated 7 September 2026._
