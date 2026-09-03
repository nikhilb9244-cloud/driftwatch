# Notes for the write-up (Phase 4 Step 7)

Findings that came out of the build and that the write-up has to name, with the numbers
attached, so that Step 7 is not reconstructed from memory months later. Each entry says what
the claim is, what it rests on, and why it belongs in a paper rather than only in a plan.

This file is additive. Nothing is deleted from it; an entry that turns out to be wrong is
corrected in place with the date, in the same style as the phase plans.

---

## The flag that moved: EOS SAT-1 against Starlink 61705 (Phase 4 Step 1, 2026-09-03)

**Name this event in the write-up.** It is the demonstration Step 1 existed to produce.

A South African satellite in the demo fleet — **EOS SAT-1 (55053)**, built by Dragonfly Aerospace in
Stellenbosch for EOS Data Analytics and owned by SAFR — gains a **red flag at a fifteen-hour
lead** purely
from screening on the operator's own published states rather than on a third party's fit to
them. Nothing else changed: same catalogue snapshot, same window, same fleet, same covariance
model, same thresholds.

| | Screening on CelesTrak's SGP4 fit | Screening on SpaceX's published states |
| --- | ---: | ---: |
| Miss distance | 5.479 km | **2.780 km** |
| Probability of collision | 6.19 × 10⁻⁶ | **1.076 × 10⁻⁴** |
| Flag | none | **red** |

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
