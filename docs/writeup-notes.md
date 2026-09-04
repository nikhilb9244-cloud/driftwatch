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
not publish one. The Office of Space Commerce's **Dataset for Conjunction Assessment Verification**
is a **government-issued test set with a published answer key**, developed for TraCSS — the US
civil space traffic coordination system — and issued expressly so that space situational awareness
providers can check their conjunction assessment algorithms against a common reference. Agreeing
with it is a claim about matching the reference the American civil regulator publishes, not about
scoring well on a contest.

Three things that have to travel with the claim, or it is overstated:

- **The Office of Space Commerce's own caveat, quoted rather than paraphrased**: the dataset is not
  comprehensive, and it is "not evaluated (nor is it intended) for use in live operations or as a
  tool for formal system certification or validation". Passing it is evidence, not accreditation,
  and the write-up must not let a reader take it for the latter.
- **Which screening volume was compared against** — the key is published for a spherical volume and
  for an SFSH rectangular one, and driftwatch's own 2 x 25 x 25 km box is neither.
- **Nothing was tuned to it**, on the same terms as the 22 % NRLMSIS bias and the 0.88 correlation:
  a record, not a calibration.

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
