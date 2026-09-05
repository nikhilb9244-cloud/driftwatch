# Notes for the write-up (Phase 4 Step 7)

Findings that came out of the build and that the write-up has to name, with the numbers
attached, so that Step 7 is not reconstructed from memory months later. Each entry says what
the claim is, what it rests on, and why it belongs in a paper rather than only in a plan.

This file is additive. Nothing is deleted from it; an entry that turns out to be wrong is
corrected in place with the date, in the same style as the phase plans.

---

## The flag that moved: EOS SAT-1 against Starlink 61705 (Phase 4 Step 1, 2026-09-03)

> **Corrected 2026-09-05, after an external review.** This entry quoted a red flag without its
> region. **The flag is in the dilution region at low confidence**: the maximum of its probability
> over covariance scale factors sits at **0.85 times the covariance in hand**, so shrinking the
> uncertainty at the same miss would raise the number, and the number is held up by the size of the
> covariance rather than by the geometry. It is not an actionable warning, and the write-up must
> lead with that wherever the event is named — as this entry, the report and the viewer now do.
> What survives is narrower and still worth a paragraph: the choice of trajectory moved a
> dilution-region probability across the red threshold at a fifteen-hour lead, which the 0.2 km
> term Phase 2 carried for that choice could not have done. Under the corrected storm term
> (`docs/storm-term.md`, 2026-09-05) both objects of this pair are operator-controlled — EOS SAT-1
> station-keeps, Starlink 61705 is on SpaceX's published states — so no scenario displaces either;
> the storm scenarios widen EOS SAT-1's in-track covariance and, in the dilution region, that
> *raises* the number slightly (1.09 × 10⁻⁴ under `forecast` against 1.076 × 10⁻⁴ under `quiet`).
> Before the correction the scenarios displaced the Starlink by a stand-in coefficient and the
> event read yellow at 4.98 × 10⁻⁵ under every storm scenario, which was arithmetic on an undefined
> excess. On the public page the primary appears as `payload 55053` until its operator has agreed
> to be named.

**Name this event in the write-up, region first.** It is the demonstration Step 1 existed to
produce.

A South African satellite in the demo fleet — **EOS SAT-1 (55053)**, built by Dragonfly Aerospace in
Stellenbosch for EOS Data Analytics and owned by SAFR — gains a **dilution-region, low-confidence
red flag at a fifteen-hour lead** purely from screening on the operator's own published states
rather than on a third party's fit to them. Nothing else changed: same catalogue snapshot, same
window, same fleet, same covariance model, same thresholds.

| | Screening on CelesTrak's SGP4 fit | Screening on SpaceX's published states |
| --- | ---: | ---: |
| Region, confidence | dilution, low | **dilution, low** |
| Miss distance | 5.479 km | **2.780 km** |
| Probability of collision | 6.19 × 10⁻⁶ | **1.076 × 10⁻⁴** |
| Maximum over covariance scales | | at **0.85×** the covariance |
| Flag | none | **red** (not actionable) |

The red threshold is 10⁻⁴, the one NASA applies to the ISS.

**Why it is worth a paragraph and not a footnote.**

- **It is at the near end of the horizon, not the far end.** Fifteen hours out, the two
  trajectories disagree by a median of about 1.6 km — the disagreement grows to tens of
  kilometres by two and a half days. This flag needed only the near-end disagreement. The
  effect does not depend on going out to where the two trajectories are obviously different.
- **It falsifies the measurement Phase 2 published about itself.** Phase 2 added CelesTrak's
  0.20 km fit residual in quadrature to every served covariance, measured the result, and found
  it **moved no flag anywhere**. The conclusion drawn at the time was that this whole class of
  error was small. Removing the *error the patch stood for*, rather than the patch, moves flags:
  ten matched events change flag, one of them into red, and nine more flagged events appear or
  disappear entirely. Phase 2's "it moves no flag" was a true measurement of a term that was far
  too small to stand for the thing it was patching. That is a better story than a clean result.
- **It is the tool's own audience.** The write-up goes to SANSA, the SKA Observatory and a
  university satellite group, and the worked example is a South African satellite whose answer
  changes. It is also the honest form of the claim the landing page makes: this is indicative,
  not operational — and here is a case where the indicative answer is different depending on
  whose orbit you screen against.

**The corrected form of the claim, which is the one to publish.** The Step 1 write-up's flag
table counted ten catalogue objects that sit on the ISS's own element set — three structural
modules and seven docked visiting vehicles — as though they were conjunctions, and a by-hand
exclusion caught only seven of the ten. With all ten excluded structurally, the result is
sharper than it first appeared:

| Quiet scenario, event flags | Run A (SGP4 fits) | Run B (published states) |
| --- | ---: | ---: |
| red | **0** | **1** |
| yellow | 22 | 20 |
| none | 6,212 | 6,203 |

**Screening on CelesTrak's fits, the demo fleet has no red flag at all outside the station's own
attached hardware. Screening on SpaceX's published states it has exactly one, and it is EOS
SAT-1 against Starlink 61705.** That is the sentence for the write-up. Do not quote the earlier
"416 red / 417 red" table: every one of those flags was the ISS's own Zvezda, Unity and Destiny
modules being screened against the ISS.

**Where the numbers are.** `docs/phase4-plan.md`, Step 1, "What it changed: two runs of the
same window, by lead", with the corrections marked in place, and the Step 1 review section for
the corrected table. Run A (`data/conjunctions/step1-baseline/`) and run B
(`data/conjunctions/step1-served/`) over the 2026-09-03 16:06 UTC snapshot.

**The caveat that has to travel with it.** Both numbers are indicative. The covariance on the
EOS SAT-1 side still comes from element-set consistency, not from an orbit determination, and
the encounter is scored with the two-dimensional method. What the comparison establishes is
that the choice of *trajectory* changes the answer by more than the term the project was
carrying to account for that choice — not that either probability is operationally correct.

---

## The partial residual path that production has not produced (Phase 4 Step 2 review, 2026-09-03)

Worth a sentence in the limitations, because it is a case of a code path that is correct,
tested and so far unexercised by real data. An event can have SpaceX's published covariance and
still have CelesTrak's SGP4 fit as its trajectory — inside a file's 47.98-hour seam, or past
the end of the stored states but inside the covariance's 72-hour validity. On the 2026-09-03
demo run **no event took it**: 646 events were served by the published states, 16 objects had
events both ways, and every unserved event on those 16 fell past the covariance's horizon too,
so it went to the base model. The path is now covered by an end-to-end test
(`tests/test_spacex.py`) rather than waiting for a run to produce it.

---

## Attached and co-orbiting objects (Phase 4 Step 2 review, 2026-09-03)

A short methods note, because it is the kind of thing a reviewer will ask about and the answer
is more interesting than "we filtered them out". Ten catalogue objects sit on the ISS's own
element set — three station modules and seven visiting vehicles — and the screening finds a
closest approach of 0.267 m between each of them and the station, roughly once an orbit, for
the whole window. Before the filter they were 2,170 of the run's 8,394 events and **1,528 of
its 1,529 red flags** — all but one. The single red flag left standing once they are gone is
the EOS SAT-1 event above, which is a tidy way to say what the exclusion is worth.

They are excluded on a rule about **sustained separation**, not about relative speed, and the
reason is the one that matters for the paper: a relative-speed rule would also remove the slow
encounters between genuinely distinct objects, and those are exactly the events the
two-dimensional probability is known to underestimate — the largest error in `docs/methods.md`
that this project cannot size. Tidying the table by deleting the events you are worst at would
be the wrong kind of tidy.

---

## The Office of Space Commerce dataset is a stronger claim than Kelvins (Step 2A, 2026-09-03)

When Step 2A is done, **say clearly that this validation is of a different kind from the Kelvins
one**, and why, because the difference is the whole reason it is worth doing.

The ESA Kelvins reproduction (`docs/kelvins-reproduction.md`) is a check against **a competition
dataset**: valuable, public, and widely used, but assembled for a machine-learning challenge, with
a hard-body radius this project had to infer from the span of the data because the organisers did
not publish one — an inference made on the evaluation rows, and since confirmed on held-out splits
(2026-09-05; `docs/kelvins-reproduction.md`). It validates the probability arithmetic on ESA's
inputs and calibrates nothing about this project's covariance. The Office of Space Commerce's
**Dataset for Conjunction Assessment Verification** is a **government-issued test set with a
published answer key**, developed for TraCSS — the US civil space traffic coordination system,
which as of June 2026 was in **pilot evaluation with 52 users in 21 countries**, not in production
(corrected 2026-09-05; the earlier text read as though it were operational) — and issued
expressly so that space situational awareness providers can check their conjunction assessment
algorithms against a common reference. Agreeing with it is a claim about matching the reference
the Office of Space Commerce publishes for a system still in pilot, not about scoring well on a
contest.

Three things that have to travel with the claim, or it is overstated:

- **The Office of Space Commerce's own caveat, quoted rather than paraphrased**: the dataset is not
  comprehensive, and it is "not evaluated (nor is it intended) for use in live operations or as a
  tool for formal system certification or validation". Passing it is evidence, not accreditation,
  and the write-up must not let a reader take it for the latter.
- **Which screening volume was compared against** — the key is published for a spherical volume and
  for an SFSH rectangular one, and driftwatch's own 2 x 25 x 25 km box is neither.
- **Nothing was tuned to it**, on the same terms as the 22 % NRLMSIS bias and the sign agreement
  by lead (the 0.88 correlation was withdrawn on 2026-09-05): a record, not a calibration.

Note also what it tests that Kelvins could not: the dataset is **ephemerides**, so it exercises the
Phase 4 Step 1 served-trajectory path rather than the SGP4 one. The two validations do not overlap.

---

## The page was showing 2.77 × 10⁻¹ against the ISS, and every internal check was green (Phase 4 Step 2 review, 2026-09-03)

**The clearest example this project has of an error that is invisible from inside the pipeline and
obvious from the front page.** Worth its own paragraph in the write-up, because the lesson is not
about conjunctions at all.

Before the attached-object filter, the published page's top row — the highest probability in the
demo fleet, the first number a stranger read — was:

| | |
| --- | --- |
| Primary | ISS (Zarya), 25544 |
| Secondary | **PROGRESS-MS 33**, 68319 — a Progress cargo ship docked to it |
| Miss distance | **0.272 m** (0.267 m is the median over all ten attached objects) |
| Relative speed | 0.3 mm/s |
| Probability of collision | **2.77 × 10⁻¹** |

Behind it, in order: Poisk 2.74 × 10⁻¹, Crew Dragon 12 2.73 × 10⁻¹, Cygnus NG-24 2.73 × 10⁻¹,
Soyuz MS-29 2.73 × 10⁻¹, Nauka 2.73 × 10⁻¹, Progress MS-34 2.70 × 10⁻¹, then the three structural
modules — Destiny 1.75 × 10⁻¹, Zvezda 1.71 × 10⁻¹, Unity 1.68 × 10⁻¹. Ten objects, 217 events
each, 2,170 of the run's 8,394 events and **1,528 of its 1,529 red flags**.

**Nothing inside the pipeline was wrong, which is the point.** The catalogue really does carry ten
objects on the station's own element set. Stages A to C really did find a repeated 0.267 m
approach between each of them and the station. The two-dimensional probability of a 0.267 m
approach between two objects with a combined hard-body radius of 100 m really is of order one. Every test passed, the provenance check passed, the frame check passed, the flag counts were
internally consistent, and a run's own report could not have told anyone the number was
meaningless — because from inside the run it was correct arithmetic on correct inputs. It took
**looking at the site** to see that the tool's headline was a docked spacecraft.

Three things to say with it:

- **The by-hand fix was wrong too.** Step 1 excluded the visiting vehicles by listing them and
  missed Zvezda, Unity and Destiny — station structure that no rule about visitors would catch.
  See the entry above and `docs/phase4-plan.md` Step 1 review, item 1.
- **What replaced it is a measurement, not a list**: a pair whose separation stays under 1 km for
  99 % of the sampled window is one physical cluster. The threshold sits three orders of magnitude
  clear on both sides — the ten attached pairs never exceed 0.857 m apart over seven days, and the
  tightest genuinely distinct pair reaches 745 km.
- **It is the argument for the public page being on the critical path** rather than the last step
  of the phase. A viewer is not decoration on a pipeline; on this occasion it was the only
  instrument that could see the fault.

The corrected top row, with the filter on, is the EOS SAT-1 event: 2.780 km, 1.076 × 10⁻⁴, one red
flag in the whole fleet — **in the dilution region at low confidence** (corrected 2026-09-05; see the
first entry), which the page's chip now says before it says red.

---

## The storm term was displacing operator-controlled objects, and the headline it produced goes with it (2026-09-05)

**Name this in the write-up as the second thing the project had to take back**, after the
cancellation explanation. An external review found it; the project's own diagnostic had been
looking straight at it for two days and had called it physics.

**The error.** The storm term measures a density excess against SGP4's own atmosphere through the
element set's B\*, and it was applied to every object with a ballistic coefficient. For a
trajectory that is the operator's — SpaceX's published states, or CelesTrak's supplemental fit to
them — the trajectory already carries the operator's drag model and planned burns, so there is no
excess to measure, and the B\* of a fit to a thrusting plan is not a drag term. For a station-kept
primary the excess is defined but the satellite will burn rather than drift, so the direction of
its displacement is the operator's. The term now gives such objects no mean shift (no term at all
on an operator's trajectory; the in-track variance kept for a manoeuvring object on a tracking
set), labels them `operator-controlled/<reason>`, and judges an event with one such side on its
free-flying side alone. `docs/storm-term.md`, "Corrected 2026-09-05".

**The 42 unscoreable Starlinks were this error seen from the other side.** Step 3 reported 42
objects (40 Starlink) whose displacement ran past a quarter of an orbit and explained them as
operated satellites in the densest shell, faithfully evaluated outside the linear theory. They
were Starlinks whose supplemental B\* described thrust; the inverted "implied density" was
nonsense and so was the 31,000 km shift. Refusing to score them was the right instinct with the
wrong cause attached. No event on the rescored run is unscoreable.

**What moved on the 3 September run**, every scenario rescored:

| | before | after |
| --- | --- | --- |
| `forecast` flags | 0 red, 16 yellow, 71 unscoreable | **1 red, 19 yellow, 0 unscoreable** |
| `storm-g4` flags | 0 red, 15 yellow, 71 unscoreable | **1 red, 17 yellow, 0** |
| `storm-g5` flags | 0 red, 13 yellow, 70 unscoreable | **1 red, 17 yellow, 0** |
| EOS SAT-1 vs 61705 under the storm scenarios | yellow, 4.98 × 10⁻⁵ | **red, dilution, low confidence**, 1.09 × 10⁻⁴ |
| relative-to-absolute ratio, both objects free-flying (981 events) | 1.85 | 1.85 (unchanged: those shifts were legitimate) |
| median `pc / pc_variance_only`, events with a controlled side (`storm-g5`) | **0.67**, 2,045 lowered against 246 raised | 1.00 |
| median `pc / pc_variance_only`, both objects free-flying (`storm-g5`) | 0.98, 55 lowered against 43 raised | 0.98, unchanged |

**And so the Phase 3 headline is withdrawn as a finding of these runs.** "A storm lowers the
probability on most events" — a median `pc / pc_variance_only` of 0.16 to 0.40 on the validated
events — lived entirely in the events with an operator-controlled side. On the population whose
displacements were legitimate the probability is lowered and raised in nearly equal numbers, and
it was so before the correction too; the correction changed nothing about those events and
everything about which events were being averaged. This is the second time the same result has
lost something: on 2026-09-03 it lost its explanation (common-mode cancellation, refuted at a ratio
of 1.91 of 2), and on 2026-09-05 it lost itself. What is measured now is narrower: on this fleet
the storm term moves a free-flying event's probability little either way, because the free-flying
primaries are cubesats at 540 to 815 km and the low, heavily displaced objects in the run are all
under operator control; and the two displacements of a free-flying pair are nearly independent
(1.85 of 2). Whether a storm lowers or raises a free-flying event's probability is decided by the
size of its displacement against the miss and the covariance, and nothing general should be
claimed about the direction until a fleet with low free-flying primaries has been screened through
a real storm.

**The lesson for the paper is about instruments, not atmospheres.** `driftwatch storm-check` was
built to attack the result and did refute its explanation — but it split the ratio by coefficient
source and by altitude, which are the axes along which a *physical* cancellation would show, and
not by whether the objects were under control, which is the axis along which a *category error*
shows. A diagnostic can only falsify along the axes somebody thought to give it. The review found
the error by asking what a served trajectory means, which no split in the tool could have asked.

---

## The second review, and the correlation the project's own rerun took back (2026-09-05)

**Name this as the third thing the project had to take back**, after the cancellation explanation
and the storm-lowers-probability headline — and note that this time no reviewer found it. A second
external review corrected five claims (below); the third withdrawal came from rerunning
`driftwatch validate gannon` so that `gannon.json` would carry the lead-time table, which the
reviewers had asked for and the stored file predated.

**The withdrawn claim.** "The storm term is predictive at r = 0.88 where the ballistic coefficient
is measured." The rerun draws its sample from the latest snapshot, and the redraw shared **four**
measured-coefficient objects with the 2 September draw: 101 objects and 498 comparisons against 81
and 422, and a correlation of **0.64 against 0.88**. On the four shared objects the two runs agree
to the third decimal, so the code did not move. The statistic did, because a Pearson correlation on
this population is carried by its largest events — dropping the largest two per cent of predictions
takes 0.88 to 0.68 on the first draw and 0.64 to 0.55 on the second — and the two draws had
different large events. Per lead the second draw's correlations are 0.13 and 0.08 inside two days
and 0.33 and 0.64 beyond, low even where the sign agreement is 88 and 97 per cent. What reproduced
across the draws: the robust slope (0.65, then 0.68), the sign agreement at three and four days
(91 and 96 per cent, then 88 and 97), the absence of skill inside two days (39 and 41 per cent,
then 38 and 33, chance being 50), the density over-prediction (22 per cent, then 23) and the
absence of skill without a measured coefficient. `docs/storm-validation.md`, "Redrawn 2026-09-05".

**The bounded statement, which is the one to publish.** On one storm, May 2024, for free-flying
objects whose ballistic coefficient was measured from their own decay, the storm term's predicted
in-track shift agrees in sign with the observed one on about nine comparisons in ten at three and
four days of lead, with a robust slope of 0.63 to 0.75; inside two days the sign agreement is below
chance and the robust slope is zero or negative; without a measured coefficient there is no
demonstrated skill at any lead. NRLMSIS 2.1 over-predicts the storm's three-day density enhancement
by 22 to 23 per cent, and nothing is tuned to it. No correlation is quoted. What none of this
measures: a second storm; a calibration against an independent truth (the later element sets are
fits by the same network, so the comparison bounds the error in neither direction); the direction
in which a storm moves a free-flying event's probability; or the covariance driftwatch puts around
any event, which the Kelvins reproduction does not calibrate either. The sample is drawn from
today's catalogue, so the 3,891 objects that decayed since May 2024 are absent from it.

**The lesson for the paper.** A correlation on a heavy-tailed population is not a finding; it is a
statement about whichever events happened to be largest in the draw. Report a statistic a tail
cannot carry (the sign agreement) beside one that says the magnitude (the robust slope), by lead,
and redraw the sample before quoting either. The project's own "storm-check" habit — attack the
result before reporting it — was applied to the storm term's *effect* and not to the *validation*
of the term, which is where this one lived.

**The five corrections from the second review**, each applied where the claim stood, with the
date:

1. **Language.** Element-set disagreement is no longer called a floor on the prediction error,
   anywhere. Successive sets are fits by the same network to overlapping observations with the same
   assumptions, so their consistency is blind to any shared error (the true error can be far
   larger) and can equally exceed the true error (a set fitted across a manoeuvre, a change of
   tracking geometry, SGP4's own re-initialisation drift): it bounds the accuracy in neither
   direction. Independent calibration would need a truth that does not come from the same fits —
   laser-ranging normal points, GNSS precise orbits, or a special-perturbations orbit determination
   from raw observations — over the same leads and orbit classes, in enough objects to give the
   ratio of actual error to consistency per class and its dependence on geomagnetic conditions, with
   a storm inside the calibration period. Nothing here has made that comparison. `docs/methods.md`,
   "Uncertainty and probability"; `docs/screening.md`; the report and the viewer.
2. **The Starlink drift finding, qualified.** One lead bin of a six-bin table, nineteen satellites,
   one date, against the operator's published prediction and not the realised orbit. The lineage of
   each pair was then checked: a supplemental set's epoch is the start of the file it was fitted
   to, and on the 300 stored pairs of that day 17 share their file with the states they are compared
   against, 105 were fitted to an earlier file and 178 to a later one, with the same drift in all
   three (the verified 17: 0.29, 2.8, 11.8, 27.6, 51.8 and 82.2 km by 12-hour bin). So the
   disagreement is not the plan's revision between files. Why the fit drifts stays open: past 24
   hours it leads the file on nine of the verified objects and lags on eight, which planned
   manoeuvres in the file and fit noise in the mean motion would both do, and only the next file's
   first states could separate them. `docs/spacex-ephemerides.md`, "Lineage, checked".
3. **Kelvins.** The `(t_span + c_span) / 2` convention was recovered from the evaluation rows, so
   it was a fitted choice however few parameters it carried, and it is now confirmed the way a
   fitted parameter is: the multiplier is chosen on one half of the training events and scored on
   the other, both ways, and chosen on the training file and scored on the challenge's test file.
   Every split chooses a multiplier of one and reproduces the rows it never saw; only on that basis
   does any page say nothing was fitted. And the reproduction validates the probability *arithmetic*
   on ESA's inputs — their geometry and covariances through our integral — and calibrates nothing
   about driftwatch's own covariance, which never enters it. `docs/kelvins-reproduction.md`,
   "Confirmed on a held-out split".
4. **TraCSS** is in pilot evaluation, with 52 users in 21 countries as of June 2026, not in
   production. The Office of Space Commerce dataset entry above now says so.
5. **Africa.** The statement that the continent has no independent tracking capability is
   replaced, wherever it stood, with the absence of a comprehensive sovereign catalogue; SANSA and
   DLR operate a debris-tracking telescope at Sutherland. `ROADMAP.md`, twice.

---

## Reproducibility: the attached filter, the runner, and the ISS's own element set (2026-09-05)

**A discrepancy that was two days old and turned out to be the catalogue's, not the code's.** The
attached-object filter dropped 2,170 candidates on the local 3 September run and none on two runner
runs, while all three reported the same ten pairs excluded. The runner's logs said the ten objects
were "never more than 0 m apart"; the local run had them 0.198 to 0.862 m apart. The cause is in
the snapshot: on the afternoon of 2026-09-03 both Space-Track and CelesTrak published the ISS's own
record at TLE precision — eccentricity 0.0005015, seven decimals, B\* 8.2215e-5 — and the ten
attached objects' records at eight decimals (0.00050146, 8.2214763e-5), all at the same epoch. One
element set, two copies, four units apart in the eighth decimal of the eccentricity, which is 0.27 m
of radial separation and twice that along track, once an orbit; Stage B finds a closest approach on
every orbit, 217 candidates a pair, and the filter drops them. By the time the runner fetched, the
whole cluster was on one copy to the last digit: zero separation, a range rate that never changes
sign, no candidate, nothing to drop, and the filter still reporting the pair attached. Both are the
filter working. The number of candidates it drops is a property of the input.

**What was done with it.** A test pins both readings (a twin on the same set produces no candidate
and is reported attached; a twin four units off in the eighth decimal produces one an orbit and
every one is dropped). The pipeline gained a reproducibility mode — `spacex: no` on a dispatch,
which screens and scores without the operator's files so that every input of the run is on the
store branch afterwards — and a gate: a production deploy is downgraded to a preview until
`REPRODUCED_RUN` names an archived run whose events were reproduced on another machine from the
same stored inputs. The comparison itself is in `docs/pipeline.md`, "Reproducibility".

**For the paper.** The lesson is the same as the front-page one above, from the other side: a
sub-metre "conjunction" between two copies of one record is arithmetic on correct inputs, and only
the filter's *report* — which names the pairs whether or not it dropped anything — made the two
runs comparable at all. A filter that only logged what it removed would have looked broken on the
runner and fine locally, and the search would have gone to the wrong place.

---

## A small upstream fix for satchecker, and what TABASCAL does not need from us (2026-09-05)

**What TABASCAL does.** TABASCAL (Finlay et al. 2025, A&A 701, A286; TABASCAL II, arXiv:2502.00106;
code at `epfl-radio-astro/tabascal`) subtracts satellite interference from radio-interferometer
visibilities by using each satellite's trajectory as a prior, propagated with SGP4 from a two-line
element or an OMM. Its orbits come from the IAU CPS SatChecker service through its own
`satchecker-client` package: one `get-nearest-tle` or `get-nearest-omm` request per NORAD id at
the observation epoch, a client-side age ceiling (`remote_max_age_days`) that re-derives a TLE's
epoch from line 1 rather than trusting a provider field, a per-satellite cache, and a rule that it
will not run with an incomplete satellite model. Its author opened satchecker issue 246
(2026-08-11): `tles-at-epoch` returns partially ingested catalogues that are indistinguishable from
complete ones — 1 to 7 records against about 17,800 for epochs 12 to 16 days old, with
`total_results` matching the partial count — and `get-nearest-tle` returns records up to 30 days
old with no staleness indicator; a 30-day-old ISS TLE puts the station 9,700 km from where a
contemporaneous one does. The issue asks for a `catalogue_complete` flag or an `expected_results`
beside `total_results`, a staleness field or a `max_age_days` parameter on the nearest-record
endpoints, and documentation of the ingest lag.

**What of ours applies, and what does not.** Three things in driftwatch do the same job on the
client side: `snapshot_as_of` takes each object's newest set at or before a date and refuses
anything later, with `max_age_days` dropping objects whose newest set is too old; `check-run` reads
a snapshot's age from its own `fetched_at` column rather than its file name and refuses to publish
past a limit; and the supplemental path abandons a set more than a day older than the catalogue's.
None of that fixes satchecker, whose problem is on the server side, and TABASCAL already does the
client-side part better than a borrowed function would — its age ceiling and its coverage rule are
exactly the two checks the issue asks the server to make possible. Nor does TABASCAL use
`tles-at-epoch` at all: its documentation says so, and says why (it wants the record nearest on
either side of the epoch, not the newest before it). So there is nothing of ours to supply to
TABASCAL, and nothing to build.

**The fix that is small, and where it would go.** In satchecker's `_get_all_orbital_data_at_epoch`
(`src/api/adapters/repositories/tle_repository.py`) the first of two SQL queries already computes
the set of satellites in orbit at the requested epoch — launched before it, not decayed, named — and
the second takes each one's newest TLE from the fortnight before the epoch; `total_results` is the
count of the second. Returning the count of the first beside it as `expected_results`, and
`catalogue_complete` as their ratio against a threshold (or just the two counts, and let the client
choose), is a change of a few lines in the repository, the service (`tools_service.py`) and the
route (`tools_routes.py`, whose response schema is documented inline), plus a test in their pytest
suite and a paragraph of documentation. The staleness field on the nearest-record endpoints is
smaller still: the record's epoch is already in the response, so a signed `epoch_offset_days` is one
subtraction, and `max_age_days` as an optional query parameter is a filter on the same number.
**Estimated cost:** a day for the completeness fields with tests and documentation, half a day for
the staleness field and parameter, for someone who has not touched the repository before (Flask,
SQLAlchemy over PostgreSQL, pytest, a contributing guide, BSD-3), plus whatever review the
maintainers need. The ingest lag itself — why recent epochs are empty and fill in a month later — is
in their data pipeline (`retrieve_tle.py` daily, `retrieve_archival_tle_data.py` backfilling
Space-Track in two-day chunks) and is theirs to explain; nothing of ours bears on it.

**What this project should not do:** build a catalogue-completeness service, mirror satchecker, or
wire the snapshot builder into TABASCAL. The overlap is one idea — say how complete the catalogue
you are returning is, and say how old the record is — and it is worth a pull request of a few
lines, not a platform.

---

## The calibration against precise orbits: what an independent truth showed (2026-09-05)

**Name this as the first comparison of a public element set with something that is not another
fit by the same network.** Every earlier statement about accuracy in this project rested on the
consistency of successive fits, and the second review's first correction was that consistency
bounds accuracy in neither direction. ESA's Swarm A, B and C carry GPS receivers and ESA publishes a
reduced-dynamic precise science orbit for each, so the comparison could be made from public sources
in a week: every public element set issued in three windows (a quiet control, the May 2024 storm,
the October 2024 storm held out from every tuning) propagated with SGP4 to leads from six hours to
seven days and measured against the precise orbit in the satellite's own RIC frame, **one trial per
element set**. `docs/calibration-benchmark.md` is the page the command writes; findings page item 6
is the statement.

**What it showed, in the order it matters for the paper.**

1. **The covariance under-covers in a storm and over-covers in quiet.** Two sigma held 65 to 80 per
   cent of the May residuals and 62 to 75 per cent of the October ones against the 95 it claims; in
   the quiet week one sigma held 82 to 96 per cent from one to five days against the 68 claimed, and
   37 to 49 inside twelve hours where the model sits on its half-day floor. A covariance fitted from
   quiet history cannot grow with a storm, and this is the number that says by how much it fails to.
2. **The horizon.** Inside 25 km in-track at the 95th percentile: five days quiet, two days in May,
   one day in October. This is the sentence an engineer can use.
3. **The storm term's lead-time split, against a truth.** In May it helps only from four days
   (+20 to +48 per cent on the median) and hurts from twelve hours to three days; in October it
   helps from six hours to five days and hurts at six and seven; in the quiet week it hurts from one
   to six days, because the density the set's `B*` implies is not the model's quiet density and the
   excess it integrates is not zero without a storm. Its magnitude at seven days in May is about 1.5
   times the actual shift, which is the direction the 22 per cent density over-prediction predicts
   and larger than it. So the bounded statement of the second review stands and gains a caveat: the
   term is a correction at three to four days and beyond in a storm, an uncertainty inside two, and
   a bias in quiet conditions that must not be applied as a mean shift when there is no storm.
4. **Manoeuvres from the published record, not from detection.** ESA's `SC_xDYN_1B` product carries
   per-second thruster on-times and the combined force of the orbit-control thrusters; two orbit
   manoeuvres in 150 satellite-days (Swarm A on 15 October, Swarm B on 17 October), which the step
   detector on the precise orbit found independently and nothing else. The element-set jump
   detector, left to decide, would have read the 11 October storm as a burn on A and C and excluded
   175 set-lead pairs — the storm-time trials themselves. A detector that reads storm drag as a burn
   is a detector that removes the storm from a storm benchmark; the published record decides.
5. **The construction error only a truth reveals.** The first run showed a constant 137 km in-track
   offset at every lead: the SP3 files' GPS time read as UTC, 18 s at 7.6 km/s. Nothing in the
   element-set comparisons could have shown it, because they never touch an absolute clock. The
   reader converts through astropy's leap-second table and a test pins the 18 s.

**What it does not show.** Three well-tracked satellites at two altitudes in one orbit class, 54
to 61 sets a window; whether the ratio of actual error to consistency generalises to debris, to
higher orbits, or to objects tracked less often is not measured. The October window contains two
storms (7 to 8 October, then 10 to 11), and the sets issued between them over-predict the decay for
the quiet days that followed — the satellite is behind the prediction by 4 to 23 km at two to three
days — consistent with a `B*` fitted across the first storm; that is an inference, not a
measurement. Swarm's TU Delft density products could later separate the atmosphere's error from the
object's response and are not part of this week.

**For the paper.** Report the coverage table and the horizon before the residual distribution: the
distribution says how wrong the catalogue is, the coverage says how wrong the tool is about how
wrong the catalogue is, and the second is the finding.
