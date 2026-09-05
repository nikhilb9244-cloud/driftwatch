# driftwatch

Conjunction screening for low Earth orbit that shows how geomagnetic storms change
collision risk. A storm heats the upper atmosphere, drag rises, predicted positions
drift along-track, and screening built on the public catalogue quietly gets worse at
the moment it matters most. driftwatch screens a chosen fleet against the whole
catalogue every day and shows how miss distances and probabilities move under quiet and
stormy conditions, live and in replay of past storms.

## Findings and corrections

What this project has found, and what it has had to take back, in the order a reviewer should
read them. Every number here is reproduced from a stored run or a stored measurement named in
the linked page, and every correction carries its date. Written 2026-09-05, after an external
review found two correctness errors and a set of framing problems; the plan changed as a result
(`ROADMAP.md`, "Plan change").

**The horizon comes first (2026-09-05).** Against ESA's precise orbits for Swarm A, B and C, a public
element set keeps the satellite inside the 25 km in-track half-width of the screening box, at the
95th percentile of trials, for **five days** in a quiet week, **two days** in the May 2024 storm and
**one day** in the October 2024 storm (item 6; `docs/calibration-benchmark.md`). Every probability
on this page, in the report and in the viewer is read after that number, not before it: a
probability computed from a set propagated past its horizon is arithmetic on a position the set no
longer predicts. The quiet scenario is the default everywhere. A storm scenario is chosen
explicitly, and every storm number carries the benchmark's calibration beside it: the covariance
under-covers in a storm, the storm term hurts inside three days and in a quiet week (its excess is
not zero without a storm), and at seven days of lead its shift over-corrects, about 1.5 times the
actual in May.

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

**Qualified 2026-09-05, after a second external review.** The headline is one lead bin of a six-bin
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
states'. MEME is 0.36 degrees from TEME by 2026, about **44 km** at low Earth orbit radius: read as
TEME the states sit 36.2 km from CelesTrak's fit to the same file, rotated into TEME they sit
0.356 km away, which is the published residual. Getting this wrong would have introduced a 44 km
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

### 5. Three headlines were withdrawn, and every correction is dated

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
flag exists — EOS SAT-1 (shown on the public page as `payload 55053`) against Starlink 61705,
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

### 6. Against an independent truth, the public element set is worse than its own consistency says in a storm, and the storm term helps only beyond three days (2026-09-05)

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
in `docs/state-of-play.md`, open items.

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

**Status: Phases 1 to 3 built; Phase 4 stops at the pipeline** (a daily GitHub Actions run that
fetches, screens, scores every scenario, publishes to Vercel and keeps every run). The landing
page, the export, the visual pass, the parked research items, the write-up and the Office of
Space Commerce validation are deferred indefinitely, because they change nobody's decision while
no operator uses the output; they are replaced by this page and by a Conjunction Data Message
parser and matcher (`docs/cdm-matching.md`), which is what turns the first operator conversation
into a measurement. `docs/state-of-play.md` is where a fresh session starts; `ROADMAP.md` has the
plan and the change to it.

What works today:

- `driftwatch fetch` downloads the CelesTrak catalogue groups politely (cached, at most
  one request per group every two hours), joins SATCAT object types, classifies every
  object and writes a dated parquet snapshot.
- `driftwatch propagate --at <time>` runs SGP4 over the whole snapshot, converts TEME to
  the Earth-fixed ITRS frame and to WGS84 latitude, longitude and height, writes a
  parquet state file, and exports a compact bundle for the viewer.
- The viewer renders every object on a globe as one GPU point cloud, runs SGP4 in a Web
  Worker (satellite.js, WebAssembly) so a 48-hour window can be scrubbed and played, filters
  by category and altitude band, and shows details on hover. It reports the disagreement
  between its own SGP4 and the Python reference state at the reference time.
- `driftwatch fleet fleets/demo.yaml` validates a fleet definition (NORAD ids, hard-body
  radii with their provenance, manoeuvre flags) and shows each member as the latest
  snapshot knows it. The demo fleet is the ISS, Sentinel-1C, two university cubesats and
  the two active South African objects.
- `driftwatch screen --fleet fleets/demo.yaml --days 7` screens the fleet against the
  whole catalogue in three stages (apogee/perigee overlap, coarse time stepping with a
  step and threshold chosen so nothing inside the screening volume can be missed, and
  root-finding on the range rate), using CelesTrak's supplemental Starlink sets for
  Starlink secondaries; then backfills 45 days of Space-Track element-set history for
  the fleet and every surviving secondary, fits each object's position uncertainty from
  the disagreement between its own element sets (with a pooled fallback per category and
  altitude band, and a labelled prior below that), checks the history for unexplained
  orbit raises, and computes the probability of collision on the encounter plane by
  Foster's integration with Alfano's form as a cross-check, the maximum probability over
  covariance scale factors, and red/yellow flags at the ISS thresholds. Everything goes
  into a run directory under `data/conjunctions/`: the geometry, the objects, the
  covariance model, one risk file per scenario and the joined export. The demo fleet's
  week takes about four minutes plus the history backfill on a laptop.
  Every event is labelled `robust` or `dilution` by where the maximum probability sits:
  a flag in the dilution region is reported at low confidence and never as actionable,
  because shrinking the covariance would raise it.
- `driftwatch risk <run> --scenario <name>` rescores a stored run's events with another
  covariance model without rescreening (today a scale factor; Phase 3's storm model
  uses the same interface), so a quiet row and a storm row for the same event sit side
  by side in the export.
- `driftwatch storm-check <run>` attacks the storm result rather than reporting it. It splits
  the relative-to-absolute shift ratio by ballistic coefficient source and by the altitude
  difference between their two orbits — the first says whether the pair's shifts are alike only
  because their coefficients came from the same rule, the second is the physical prediction,
  since the density falls by an order of magnitude every 50 km and two objects far apart in
  altitude cannot see the same excess — puts the combined, shift-only and variance-only
  probabilities side by side over probability
  bands, and names the objects whose storm term ran outside the linear theory. Those events carry
  no probability at all: `unscoreable`, with the reason on the row and excluded from every
  aggregate. It did its job twice: it excluded the artefact, and then it **falsified the
  explanation** the headline result had been given — the relative-to-absolute ratio is 1.85 out
  of a possible 2 over the free-flying pairs, so the two displacements are nearly independent.
  What it could not find was that the result itself rested on displacing operator-controlled
  objects; an external review did (2026-09-05), and the ratio is now taken over free-flying
  pairs only. See `docs/storm-term.md`.
- Every aggregate the tool prints is reported **twice**: over the events whose two objects both
  have a ballistic coefficient measured from their own decay (`validated`), and over the rest
  (`indicative`). Step 4 measured the storm term against May 2024 and found its sign right on
  about nine comparisons in ten at three to four days of lead with a measured coefficient, no
  skill inside two days, and no demonstrated skill without a measured coefficient, so the split
  is the difference between a measurement and an extrapolation. `storm_validity` is on every row.
- `driftwatch snapshot-as-of --date <when>` rebuilds the catalogue as it stood on a past date
  from `gp_history`, taking each object's newest element set **at or before** that date and
  nothing later, bounded by an altitude range or a launch's international designator to keep the
  pull proportionate. Cached permanently under `data/snapshots/as-of/`.
- `driftwatch validate gannon` and `driftwatch validate starlink-2022` measure the storm term
  against the record. See below.
- `driftwatch stability <run>` adds a scored run to the warning-stability index -- one narrow
  file per run on the pipeline's store branch, holding each encounter's identity, miss distance
  and probability. `driftwatch stability --pair 55053,61705` reads one encounter's history back:
  how a warning moved run to run, without opening a month of run archives. The index is written;
  no analysis of it is.
- `driftwatch report <run>` writes the weekly markdown report and the viewer's
  conjunction bundle. Repeated encounters of one pair are collapsed to a single row with
  the event count, the closest miss, the highest probability and the first time of
  closest approach, expanding to the individual events on demand, with a cumulative
  probability per pair labelled as the upper bound it is.
- The viewer's conjunctions panel lists those pairs. Selecting an event jumps the clock
  to the time of closest approach, highlights both objects, draws ten minutes of each
  track either side and opens an inset of the encounter plane with the covariance
  ellipse, the hard-body disc, the miss vector and the probabilities. Every number is
  Python's; the browser computes no screening result.
- **Storm mode** switches the panel between `quiet`, `forecast` and the three synthetic storm
  levels. Every row then carries the miss and probability *under that scenario*, its region and
  confidence, whether the storm term is validated or indicative for it, and `Δ vs quiet` as a
  multiplier — on every row, not only the interesting ones, so the phase's result is learnt from
  the screen. The detail view adds the pre-storm miss, the relative displacement, the shift-only
  and variance-only probabilities, and the quiet ellipse behind the scenario's with an arrow
  between the two misses. Events the storm term cannot score sit in their own section below the
  queue with the reason, never in the queue with a blank. **The control changes numbers in the
  panel and nothing else** — the point cloud, the worker and the tracks are geometry and do not
  depend on the scenario, which is what keeps Phase 1's frame budget.
- **Replay mode** swaps the catalogue for the one that existed on 9 May 2024, that run's own
  screening under the observed record, and a timeline — **without leaving the page**. The Kp bar is
  the background of the scrubber, the density ratio at 400 and 500 km is drawn over it, the Sun in
  SDO/AIA 193 Å sits beside it, and all of them plus the objects read the one simulation clock, so
  scrubbing moves everything together by construction. The camera, the selected object, the
  filters, the playback speed and the position through the window all carry across; the scenario
  is remembered per mode, so leaving replay puts a G5 back. `?replay` still goes in the address
  bar, so a replay is a link and the Back button leaves it, and nothing of the replay bundle is
  fetched until somebody asks for it.
- `driftwatch replay-bundle <run>` writes that timeline: the observed Kp and ap with their
  provenance, the density ratios against the same quiet control window Step 4 measured the
  enhancement against, and a few Sun frames a day from Helioviewer with the lag between the time
  asked for and the image actually returned on each. Each frame is fetched at two sizes — the full
  512 px image as a file and a 32 px thumbnail inlined in the timeline — so the viewer has a
  placeholder everywhere on the scrubber and fetches the 360 kB frames only as the playhead
  reaches them.
- `driftwatch supplemental` fetches CelesTrak's operator-ephemeris element sets, stores
  the version, thins versions older than a fortnight to one a day, and with `--fit`
  refits the supplemental covariance across the whole store. It runs every three hours
  from a scheduled task, because that covariance is measured from the consistency of
  successive versions and CelesTrak keeps only the latest one.
- `driftwatch kelvins` reproduces the risk column of ESA's Kelvins Collision Avoidance
  Challenge data from its own inputs. The hard-body radius ESA used turns out to be in
  the data: with the combined radius taken as `(t_span + c_span) / 2`, the 162,634-row
  training set is reproduced to a median residual of 0.07 % with 87 % of the high-risk tail
  within a factor of two. The convention was recovered from those rows, so it is confirmed on
  held-out splits (each half of the events against the other, and the training file against
  the challenge's test file) before being called unfitted. It validates the probability
  arithmetic on ESA's inputs and does not calibrate driftwatch's covariance
  (`docs/kelvins-reproduction.md`).
- `driftwatch cdm match <run> --cdm <dir>` reads an operator's Conjunction Data Messages
  (CCSDS 508.0-B-1, KVN or XML), matches them to a stored run's events on the object pair and
  a ten-minute TCA tolerance, and reports which operator-warned conjunctions public data found
  and at what miss and probability, which it missed, and which public-data flags the operator
  never received. Built against the Kelvins rows as test input, which `driftwatch cdm
  from-kelvins` writes out as messages with synthetic identities (`docs/cdm-matching.md`).
- `driftwatch validate swarm` is the calibration benchmark against precise orbits: every public
  element set issued for Swarm A, B and C in three windows (a quiet control, the May 2024 storm,
  and an October 2024 storm held out from every tuning) propagated with SGP4 to leads from six
  hours to seven days and measured against ESA's precise science orbit in the satellite's own RIC
  frame, one trial per element set. It reports the residual distribution, the coverage of the
  empirical covariance against the 68 and 95 per cent it claims, the storm term's effect with
  the observed ap, and the horizon for the screening box, and reads ESA's thruster record for the
  manoeuvre exclusion (`docs/calibration-benchmark.md`, item 6 above).
- `driftwatch local` runs an operator's own files through the provenance check, the CDM matcher
  and the same benchmark with the operator's ephemeris as the truth, with every outbound request
  refused for the duration, so nothing leaves their machine and the public demonstration stays
  reproducible from public sources alone (`docs/local-analysis.md`).
- Tests cover the official SGP4 verification cases, frame conversions against skyfield,
  a real ISS pass over Durban, the cache rules, the snapshot schema, the export, the
  Space-Track client, the fleet files, the screening (synthetic conjunctions with a
  designed time and miss distance recovered to a millisecond and a metre, and the coarse
  step checked against one-second brute force), the probability of collision (closed
  forms, brute-force quadrature, the three integrators against each other, the dilution
  maximum), the covariance fit and the manoeuvre detector on synthetic element-set
  histories, the history index and batched backfill, the scenario mechanism end to end, the
  storm term's closed form against an independent Runge-Kutta integration and its sign against a
  case where the answer is obvious, the refusal to score an event whose displacement has left
  the linear theory, the thrust ceiling on a satellite fitting above what its own geometry
  allows, the loud failure of a weather table that does not reach the oldest element-set epoch
  in a run, the historical snapshot builder's refusal to use an element set from after the date
  it reconstructs, Step 4's own measurements, the storm-term validity label and the promise that
  it changes no number, the storm-response prior's value (so the measured 22 per cent
  over-prediction cannot quietly become a calibration), and Step 5's exports: the scenario
  overlay's columns staying parallel to the bundle's own order, an unscoreable event carrying
  null rather than a small number, every aggregate present both ways, and the refusal to build a
  replay timeline whose density baseline does not reach the quiet control window.

## Quick start

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
uv sync                                   # Python environment
export SPACETRACK_USER=you@example.org    # optional: Space-Track login for the full catalogue
export SPACETRACK_PASS=...                #   (PowerShell: $env:SPACETRACK_USER = "..."). Never put these in a file.
uv run driftwatch fetch                   # ~30 s; CelesTrak groups + Space-Track gp, writes data/snapshots/gp_<stamp>.parquet
uv run driftwatch propagate --at 2026-09-01T12:00:00Z
                                          # ~3 s; writes data/propagated/state_<stamp>.parquet
                                          # and web/public/data/{manifest.json,objects.json,elements.bin,reference.bin}
uv run driftwatch fleet fleets/demo.yaml  # check the demo fleet against the snapshot
uv run driftwatch screen --fleet fleets/demo.yaml --days 7
                                          # ~4 min + the history backfill; writes data/conjunctions/demo_<stamp>/
uv run driftwatch risk latest --scenario test --scale 3
                                          # rescore the same events with every covariance tripled
uv run driftwatch spacex latest           # optional: SpaceX's own covariance for the run's Starlink
                                          #   secondaries, inside their 72-hour horizon
uv run driftwatch weather --days 7        # space weather for the window, with its provenance
uv run driftwatch density                 # NRLMSIS sanity check: quiet density and the storm ratios
uv run driftwatch ballistic latest        # a ballistic coefficient per object, from decay or B*
uv run driftwatch risk latest --scenario storm-g5
                                          # rescore under a synthetic G5 built from May 2024
uv run driftwatch storm-check latest      # attack the storm result; name what cannot be scored
uv run driftwatch stability latest        # index the run for warning stability (the pipeline does this daily)
uv run driftwatch stability --pair 55053,61705
                                          # read one encounter's history back across runs
uv run driftwatch validate gannon         # measure the term against the May 2024 storm

# The May 2024 replay the viewer's `?replay` mode reads.
uv run driftwatch propagate --snapshot data/snapshots/as-of/gp_asof_20240509T000000Z.parquet \
    --at 2024-05-09T00:00:00Z --export-dir web/public/data/replay
uv run driftwatch report demo-2024_20240509T000000Z --scenario replay:2024-05-09 \
    --out-dir web/public/data/replay
uv run driftwatch replay-bundle demo-2024_20240509T000000Z
uv run driftwatch report latest           # weekly report + the viewer's conjunctions bundle
cd web && npm install && npm run dev      # open the printed URL
```

To publish it, see [Deploying the viewer](#deploying-the-viewer).

`uv run driftwatch snapshots` lists what has been fetched. `--offline` on `fetch`
rebuilds the snapshot from cache without touching the network; `--spacetrack off` skips
Space-Track and `--spacetrack on` fails without it (the default uses it when the
credentials or a cache are present). `uv run driftwatch history --ids 25544,39634
--start 2024-05-01 --end 2024-05-20` pulls every element set for those objects from
Space-Track's `gp_history` into `data/history/`; `screen` does the same for the fleet
and its surviving secondaries by itself (`--history off` skips it, `--history on` insists
on it). Run `uv run pytest` for the tests (the first run downloads IERS Earth-orientation
data for astropy, about 3 MB).

## Deploying the viewer

Vercel, from 2026-09-05: team `nikolodeon-s-projects`, project `driftwatch`, root directory
`web`, framework Vite, with the GitHub repository **disconnected**, so nothing builds on a push.
Two things deploy and nothing else does: the daily pipeline (`.github/workflows/pipeline.yml`,
production) and the hand-run script below (a preview by default). Both build the same way and
check the same bytes. Every deployment sits behind Vercel Authentication until a custom domain is
attached or the protection is changed (`docs/pipeline.md`, "Hosting").

```powershell
pwsh -File scripts/deploy-vercel.ps1 -DryRun                    # export, build, check; stop before uploading
pwsh -File scripts/deploy-vercel.ps1 -Run <run> -Scenario quiet  # a preview deploy with its own URL
pwsh -File scripts/deploy-vercel.ps1 -Production -Run <run> -Scenario quiet
```

1. **Export a fresh bundle.** `driftwatch propagate --at <now>` writes the catalogue side
   (`manifest.json`, `objects.json`, `elements.bin`, `reference.bin`) and `driftwatch report`
   the conjunctions side (`conjunctions.json`, `scenarios.json`, `conjunction-tracks.bin`).
   Neither rescreens. `-SkipExport` deploys what is already in `web/public/data`; `-Run` and
   `-Scenario` choose which stored run and scenario to show. On the public page, fleet members
   other than stations appear by category and NORAD id, not by name, until their operator has
   agreed to appear.
2. **Build with the Vercel CLI.** `vercel pull` fetches the project settings and `vercel build`
   runs the Vite build locally into `.vercel/output/`. Building here and deploying prebuilt is
   what lets the next step check exactly the files that will be served.
3. **Check what is about to be published**, over the prebuilt output:

   ```bash
   uv run driftwatch check-bundle --dir .vercel/output
   ```

   It refuses to continue if any file is a raw SpaceX ephemeris or a copy of the derived
   covariance store (analysis only, never redistributed — `docs/spacex-ephemerides.md`), if
   anything matches a credential pattern or the literal value of `SPACETRACK_USER`,
   `SPACETRACK_PASS` or `VERCEL_TOKEN` in the environment, or if any file is over the 25 MiB
   per-file ceiling (Cloudflare Pages' upload limit, kept as the project's own). The rules are in
   `src/driftwatch/export/audit.py` and the tests in `tests/test_audit.py`.
4. **Upload.** `vercel deploy --prebuilt`, with `--prod` for production. Vercel builds nothing.

Authentication is the Vercel CLI's: `npx vercel login` once on a machine, or `VERCEL_TOKEN` with
`VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` in the environment, which is how the pipeline runs it.
The pipeline names a missing secret before it builds anything.

**Retired: Cloudflare Pages.** The project `driftwatch` and <https://driftwatch-2wg.pages.dev>
are retired; they last served the 2026-09-03 run under the uncorrected storm term.
`scripts/deploy-pages.ps1` stays, marked retired, until the first Vercel production deploy has
succeeded. `docs/pipeline.md` has the deploy design and why the host changed.

**Current sizes** (5 September 2026): the prebuilt output is 31 MiB in all, the largest files
`elements.bin` at 2.7 MiB and `conjunctions.json` at about 3 MiB, well inside the 25 MiB per-file
ceiling. Source maps are not published (`web/vite.config.ts`).

## What you are looking at

Each point is one catalogued object at the time on the clock, coloured by category:
space stations, Starlink, OneWeb, other constellations, other payloads, rocket bodies,
debris, unknown. The slider spans 24 hours either side of the reference time. Hover for
name, altitude and position; click or search to pin an object.

Positions come from public two-line element sets propagated with SGP4. They are good to
hundreds of metres to a few kilometres near the element-set epoch and drift by kilometres
per day, more in a storm. The viewer's Earth-fixed frame ignores UT1 and polar motion,
which costs under a pixel. Everything approximate is listed in `docs/methods.md`.

Coverage is the CelesTrak groups (operational payloads, stations, the Starlink and
OneWeb constellations, recent launches and the three largest debris clouds), roughly
19,000 objects, merged with Space-Track's full `gp` catalogue when a login is available,
which adds the older rocket bodies and the rest of the tracked debris. Each object keeps
its freshest element set and records which source it came from.

## Layout

```
src/driftwatch/         Python package (CLI: driftwatch)
  catalogue/            CelesTrak and Space-Track fetch, SATCAT, classification, parquet snapshots, history
  orbit/                time, SGP4 propagation, frame conversions
  screening/            three-stage conjunction screening, RIC frame, supplemental Starlink sets
  ephemeris/            operator-published ephemerides (SpaceX's Starlink covariance)
  weather/              space weather: CelesTrak SW-All, NOAA SWPC, the three-hourly table, Sun imagery
  drag/                 NRLMSIS density along an orbit, and the ballistic coefficient per object
  risk/                 covariance model and fit, manoeuvre flag, probability of collision, scenarios, Kelvins
  export/               viewer bundle, conjunction run directory, weekly report, pre-deploy audit
  cdm/                  CCSDS Conjunction Data Messages: parser, matcher, the Kelvins test adapter
scripts/                deploy to Vercel (deploy-vercel.ps1; deploy-pages.ps1 is retired), register the supplemental fetch task
fleets/                 YAML fleet definitions (the primaries to screen)
tests/                  pytest
docs/                   physics background, frames and time, data schema, methods, data sources, plans
web/                    Vite + TypeScript + globe.gl + satellite.js viewer
data/                   cache, snapshots, history, supplemental and SpaceX ephemeris versions,
                        conjunction runs (git-ignored)
```

## Docs

- `docs/state-of-play.md`: **start here to resume the work.** Where Phase 4 stands step by
  step, what is committed and what has never run, the open items, and the ceilings.
- `docs/tle-and-sgp4.md`: what a TLE is, mean versus osculating elements, what SGP4
  does, and the accuracy limits of the public catalogue.
- `docs/frames-and-time.md`: TEME, ITRS, GMST, UT1 and polar motion, and the measured
  cost of the browser's shortcut.
- `docs/data-schema.md`: every column in the snapshot, state, conjunction and viewer files.
- `docs/screening.md`: the three screening stages, the step-and-threshold derivation
  with its brute-force proof, what an event's numbers mean; then the covariance from
  element-set consistency and why it is a consistency measure and not a bound on accuracy,
  the manoeuvre flag, the encounter plane, the three probability integrators, the dilution
  maximum and the flags.
- `docs/methods.md`: the running list of approximations.
- `docs/kelvins-reproduction.md`: the ESA Kelvins reproduction as the command writes it,
  with `docs/kelvins-reproduction.svg`, the residual against ESA's risk.
- `docs/cdm-matching.md`: the Conjunction Data Message parser and matcher, what the three
  outputs mean, and why the Kelvins rows are its test input and not a validation.
- `docs/calibration-benchmark.md`: the calibration against ESA's precise orbits for Swarm A, B
  and C, as the command writes it: three windows, four things by lead bin, every source with its
  origin and derivation.
- `docs/local-analysis.md`: the optional local path, for an operator's own ephemerides, messages
  and records, and the guard that keeps them on the operator's machine.
- `docs/data-sources.md`: each data provider's terms, the Space-Track redistribution
  clause as checked, and the citation format.
- `docs/spacex-ephemerides.md`: whether SpaceX's published Starlink ephemerides may be
  used and how, what their covariance actually is, and the plan for them.
- `docs/space-weather.md`: Kp and ap and why the table carries both, the feeds and their
  terms, how the sources are layered, and what is deliberately not filled in.
- `docs/density-and-drag.md`: NRLMSIS and how it is driven, the sampling step and its
  convergence, the ballistic coefficient and why B* is not one.
- `docs/pipeline.md`: the daily run — the runtime budget, where each piece of state lives
  and why, the retention rule and the failure model.
- `docs/phase2-plan.md`: the Phase 2 plan, the review decisions and the demo fleet.
- `docs/phase3-plan.md`: the Phase 3 plan and its review decisions.
- `docs/phase4-plan.md`: the Phase 4 plan and its review decisions, with
  `docs/writeup-notes.md` accumulating the findings the write-up has to name.

## Data sources and their rules

- [CelesTrak](https://celestrak.org) GP element sets and SATCAT. No account. Their rule
  is one fetch per group per two hours with a descriptive User-Agent; the fetcher
  enforces both and caches everything. Set `DRIFTWATCH_CONTACT` to add a contact
  address to the User-Agent.
- [Space-Track](https://www.space-track.org) `gp` catalogue and `gp_history`. Free
  registration. Credentials are read from `SPACETRACK_USER` and `SPACETRACK_PASS` and
  never written to disk or logs. The client stays under Space-Track's limits (fewer than
  30 requests a minute and 300 an hour), pulls the catalogue at most every two hours and
  four times a day, and never repeats a history request. Their user agreement grants
  blanket approval to redistribute basic SSA data (element sets, SATCAT and decay data)
  with citation, which the viewer bundle carries; conjunction messages and the emergency
  and advanced tiers are not covered and are never fetched. See `docs/data-sources.md`
  for the quoted text, the date it was checked and the citation format.

- [SpaceX Starlink ephemerides](https://api.starlink.com/public-files/ephemerides/). No
  account, no stated licence, published so that other operators can screen against
  Starlink. driftwatch uses their covariance for Starlink secondaries inside the 72-hour
  horizon of each file. Because no licence is stated the rule is **analysis only**: the
  raw files are never redistributed, only one satellite's file is fetched per satellite a
  run actually needs, and the store holds a thinned covariance series rather than the
  file. See `docs/spacex-ephemerides.md` and `docs/data-sources.md`.

- [NOAA SWPC](https://services.swpc.noaa.gov) space weather forecasts and the L1 solar
  wind, and [CelesTrak's `SW-All.csv`](https://celestrak.org/SpaceData/) for the observed
  record. Both public and free of account. Every forecast is stored under the time it was
  **issued**, so a stored run can be rescored against the forecast it actually used.
- [Helioviewer](https://helioviewer.org) for Sun imagery in the storm replay. Public API,
  credit given in `config.HELIOVIEWER_CITATION`; the images are NASA/SDO products.

## Licence

MIT. See `LICENSE`.
