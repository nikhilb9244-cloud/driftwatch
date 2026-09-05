# Validating the storm term against the record

Phase 3 Step 4. Everything before this step is internally consistent and unvalidated: the
closed form was checked against a numerical integration of *itself*, the density model against
published quiet-time tables, the ballistic coefficients against the objects' own decay. A chain
of individually correct steps can still add up to a wrong answer, and there is one term in it
carried as a prior rather than a measurement — how wrong NRLMSIS's *storm response* can be,
`config.DENSITY_STORM_RATIO_SIGMA_REL`, set at 30 per cent with nothing behind it.

So the chain goes against the record twice, in the order that makes a failure interpretable.

```
driftwatch validate gannon          # May 2024: the atmosphere, then the objects
driftwatch validate starlink-2022   # February 2022: what the catalogue could even see
```

Both write parquet and a JSON summary under `data/validation/`.

---

## 1. May 2024: did the atmosphere do what the model says?

The cleanest measurement available from public element sets, and it needs **no ballistic
coefficient at all**. For one object under drag,

    da/dt = -B rho sqrt(mu a)

Take that over a quiet window and over the storm and divide. `B` cancels — the object's size,
mass and drag coefficient all go — and `sqrt(mu a)` cancels to the fraction of a per cent the
semi-major axis moved. What is left is the ratio of the densities that object actually flew
through. NRLMSIS, driven by the observed ap for the same days along the same orbit, predicts
that ratio independently.

**The windows.** Storm: 10 to 13 May 2024. Quiet control: 25 to 28 April 2024, close enough in
time that the solar flux and the altitudes are nearly the same. `da/dt` is a straight line
through the mean semi-major axis of every element set in the window rather than an endpoint
difference — with six to ten sets available, the endpoints are the two noisiest numbers there
are — and intervals the manoeuvre detector flags are dropped.

**The selection.** 300 objects with perigee between 250 and 750 km, spread over the range
rather than sampled at random so the altitudes are covered. 163 of them had element sets in the
window. 56 had a decay in the quiet window significant against their own element-set scatter
(the `--min-snr 3` cut) — the ratio of two noisy small numbers is the classic way to manufacture
a spectacular and meaningless enhancement, so objects whose quiet decay is inside their own
noise are dropped rather than divided by.

### The result

| | median | p10 | p90 |
| --- | ---: | ---: | ---: |
| **Observed** storm/quiet, from the objects | **1.68** | 1.06 | 2.38 |
| **NRLMSIS** for the same days and orbits | **2.21** | 1.75 | 2.96 |
| observed / modelled | **0.78** | | |

> **Redrawn 2026-09-05.** `driftwatch validate gannon` draws its sample from the latest snapshot,
> and the rerun that wrote the lead-time table into `gannon.json` drew a different population
> from the 3 September catalogue: 68 objects with two usable decay rates, observed median
> **1.73** against a modelled **2.32**, observed over modelled **0.77** — a 23 per cent
> over-prediction against the 22 above, with the same sign at every altitude band (0.84, 0.82,
> 0.74 and 0.75 from 350 to 800 km). The size and the direction reproduce; the sample does not,
> which is the point of recording both.

By altitude, and this is the part that matters, because a model right on average and wrong at
500 km is not right:

| Altitude | n | observed | modelled | observed/modelled |
| --- | ---: | ---: | ---: | ---: |
| 450–550 km | 15 | 1.65 | 2.03 | 0.83 |
| 550–650 km | 11 | 1.68 | 2.12 | 0.74 |
| 650–800 km | 19 | 2.00 | 2.64 | 0.76 |
| 800–2000 km | 8 | 1.42 | 2.33 | 0.73 |

**NRLMSIS over-predicts the Gannon enhancement by about a quarter, consistently across the
altitude range.** The enhancement is real and large — the atmosphere at these altitudes was
denser by 40 to 100 per cent over those three days — and the model gets its size right to
within about 30 per cent, in the same direction at every altitude.

That is the first measurement of a quantity Step 3 had to assume. The prior
`DENSITY_STORM_RATIO_SIGMA_REL = 0.30` turns out to be **the right magnitude and centred in the
wrong place**: the model's storm-response error over this storm is not a symmetric 30 per cent,
it is a systematic over-prediction of about 22 per cent with a spread of a similar size around
it. Nothing in the code is tuned to this. Changing the term from a symmetric prior to a
bias-plus-spread on the strength of a single storm would be fitting one event; what it earns is
a sentence in the docs, a number to check the next storm against, and the note that the sign of
the bias is now known.

### What this measurement cannot see

**Survivorship.** The 300 objects are chosen from *today's* catalogue, so every object that has
decayed since May 2024 is absent — and a storm's most affected objects are precisely the ones
that came down. SATCAT records **3,891 objects that were in orbit on 9 May 2024 and have
decayed since**, none of which can be in this sample. The measured enhancement is therefore a
lower bound in a specific way: the objects that felt the storm hardest are missing from it.

**The quiet window was not perfectly quiet.** Nothing in solar cycle 25's maximum is. Kp stayed
at or under 4 across 25 to 28 April, so the denominator is a genuinely quieter atmosphere than
the numerator, but it is not a solar-minimum baseline and the ratio is correspondingly
conservative.


### The bias, recorded: sign, size, altitude dependence, and what the literature says

Recorded here so the next storm has something to disagree with. **Nothing is tuned to it**, and
the rest of this section is the reasons not to be.

| | |
| --- | ---: |
| Sign | **Over-prediction.** NRLMSIS 2.1's storm/quiet ratio exceeds the objects' own |
| Size | observed/modelled **0.78**, a **22 per cent** over-prediction of the enhancement |
| Spread | p10 to p90 of the observed ratio 1.06 to 2.38 against a modelled 1.75 to 2.96 |
| Altitude dependence | **None resolvable.** 0.83, 0.74, 0.76, 0.73 across 450–550, 550–650, 650–800 and 800–2000 km — a spread of 0.10 across 53 objects in four bins, with no monotone trend |
| Sample | 56 objects with a quiet decay significant against their own element-set scatter |
| Quantity | the ratio of two **three-day window-integrated** decay rates, not an instantaneous density |

The altitude row is the one worth dwelling on, because "no dependence" is a stronger statement
than it looks. The four bins span 1,550 km and a factor of some hundreds in density, and the
ratio moves by a tenth. A model whose *geomagnetic* term were wrong would be expected to fail
differently at 500 km and at 800 km, where the storm response and the quiet baseline are set by
different mixtures of species. That it does not points at a bias in the storm response as a
whole rather than at the altitude profile — which is the term the code carries as a prior, and
the one thing the measurement was designed to constrain.

**Against the published record, this disagrees in sign.** The published assessments of
MSIS-class models at storm time mostly find **under**-estimation:

- Bruinsma et al. (2021), *Thermosphere modeling capabilities assessment: geomagnetic storms*,
  J. Space Weather Space Clim. — comparing modelled against accelerometer-derived densities over
  many storms, NRLMSISE-00 **underestimates** storm amplitudes on average, by a margin the paper
  puts at tens of per cent, while DTM2013 and CTIPe overestimate.
- Zhang et al. (2025), Front. Astron. Space Sci. — NRLMSIS 2.0 "systematically underestimated
  thermospheric density" through the November 2003 storm with recovery-phase errors above 50 %,
  and underestimated the March 2015 main phase by over 20 %, at GRACE-A and Swarm-A altitudes.
- Assessments of NRLMSIS 2.1 report the same shape: under-estimation of the main-phase peak,
  over-estimation in the initial phase, and a recovery-phase error over 40 % for some events.

### The two sides are not measuring the same quantity, and here is each one written out

Before the disagreement can be called a discrepancy, it has to survive being stated precisely.
A "density error" is not one number: it depends on where, when, over how long, and against what.
Set side by side:

| | **The published assessments** | **This measurement** |
| --- | --- | --- |
| **What is compared** | Model density at a **point** against density derived from a **spacecraft accelerometer** at that point | Model density at a **fixed altitude** against density inferred from the **decay of an orbit** through it |
| **The observed quantity** | Non-gravitational acceleration on a drag-free-controlled satellite, inverted to `rho` with a modelled drag coefficient and a known area | `da/dt` of the mean semi-major axis, from a straight line through the element sets in each window, with `B` divided out by taking a **ratio of two windows** |
| **Where in space** | One point on one orbit, sampled continuously: GRACE-FO ~500 km, Swarm-A/C ~450 km | Wherever each of 53 objects flew, weighted along the orbit by `rho \|v_rel\| (v_rel · v)`; 450–2,000 km, 27 of them above 650 km |
| **Where in time** | Instantaneous, at whatever cadence the accelerometer gives (seconds to minutes) | A **three-day integral**, 10–13 May, with no time resolution inside it whatever |
| **What is reported** | The error in the **peak amplitude** of the storm response, and separately per storm phase | The error in the **window-integrated storm/quiet ratio**, one number per object |
| **The baseline** | The model's own quiet value at the same point and time | A different **three-day window three weeks earlier** (25–28 April), through which the same objects flew |
| **The population** | Two to four dedicated science satellites in near-circular orbits, with measured areas and attitudes | Every catalogued object that had a decay significant against its own element-set scatter — sizes, shapes and attitudes unknown |

**So the honest reading is that this is mostly a category difference, with a possible discrepancy
inside it that this measurement cannot isolate.** Three things follow from the table, in order of
how much they explain:

1. **Peak against integral.** A storm's density response is a sharp main-phase spike on a
   two-day recovery shoulder. The published error is in the spike; ours is in the area under the
   whole thing, where the shoulder dominates simply because it is longer. A model that
   undershoots the spike and overshoots the recovery — which is exactly the shape the NRLMSIS 2.1
   assessments describe, "under-estimation of the main-phase peak, over-estimation in the initial
   phase, recovery error over 40 %" — produces both results at once with no contradiction. **This
   measurement cannot test that**, by construction: the decay method integrates the window and
   has no time resolution inside it. Resolving it needs a shorter window, which needs element
   sets more often than the catalogue issues them.
2. **Point against path, and fixed height against a decaying orbit.** Their `rho` is at a place;
   ours is what an object *flew through*, weighted by the drag integral and therefore by
   perigee, over an orbit that was itself falling as the storm acted. The two are the same number
   only for a circular orbit at a constant altitude, which is the case their satellites nearly
   are and ours are not.
3. **Different altitudes.** Their 450–510 km sits at the bottom of our range; half our binned
   objects are above 650 km, where the storm response is set by a different mixture of species.
   Our own altitude split resolves no trend across 1,550 km, which argues this is the smallest
   of the three, but it is not nothing.

**And two known biases in our measurement push in one direction — the direction that would shrink
the disagreement.** The quiet control window had Kp at or below 4 rather than being a
solar-minimum baseline, so the *observed* ratio is conservative and the true enhancement was
larger than 1.68; and the 3,891 objects in orbit on 9 May 2024 that have since decayed are
precisely the ones that felt the storm hardest and cannot be in the sample. Both make the model
look worse than it is. Together with (1) they mean **22 per cent is an upper bound on this
quantity's error, not a best estimate of it**.

**What is documented, and what is not done.** Over this window, at these altitudes, by this
method, NRLMSIS 2.1 over-predicts the enhancement by about 22 per cent; the published work
measures a different quantity and finds the opposite sign; the difference is mostly explained by
which quantity, and what remains is not separable here. Nothing is tuned either way.
`DENSITY_STORM_RATIO_SIGMA_REL` stays at a symmetric 0.30 and a test pins it there, so that no
later change can quietly turn this record into a calibration — and so that a future reader who
resolves (1) with better data finds the prior where they left it rather than half-corrected
against a comparison that never justified a correction.

---

## 2. May 2024: did it move the objects where we say it did?

The test that matters for screening, and it is a **forecast** test, run the way an operator
would have run it on the day.

For each object: take its last element set issued **before** 9 May 2024, propagate it with SGP4
through 10 to 13 May, and compare with the element sets issued during those days. The
along-track component of that disagreement is the error a screening run made — the thing
driftwatch exists to predict. The storm term's prediction, computed from the same pre-storm
element set, that object's **pre-storm** ballistic coefficient and the observed ap, is what it
is compared with.

Three disciplines make it a test rather than a demonstration.

**Nothing after the pivot reaches the prediction.** An element set issued on 12 May already
contains the storm's effect; using one would be "predicting" the drag it was fitted to. The
coefficient fit is given history cut at the pivot and nothing else.

**A quiet control at the same lead times.** SGP4 accumulates along-track error with no storm at
all, from fit noise and ordinary mismodelled drag, and it does so quadratically too. Without
the control that error is read as the storm's. Pivot 24 April, window 25 to 28 April, matched to
the storm comparisons by lead time in whole days.

**The later element set is not truth.** It is another fit with its own error of hundreds of
metres to kilometres. What is measured is the disagreement between two fits by the same network,
which bounds the propagation error in neither direction (reworded 2026-09-05; the earlier text
called it a floor): the two share observations and assumptions, so an error common to them is
invisible here, and a shared assumption can equally make them disagree by more than either is
wrong. Only a comparison against an independent truth would calibrate it. One has since been made,
on three satellites (`docs/calibration-benchmark.md`, 2026-09-05): against ESA's precise orbits for
Swarm A, B and C the storm term with the observed ap reduces the in-track residual in the May 2024
storm only from four days of lead (+20 to +48 per cent on the median at four to seven days) and
increases it from twelve hours to three days; in the October 2024 storm, held out from every tuning,
it helps from six hours to five days and hurts at six and seven; and in a quiet week it makes the
residual worse from one to six days, because the excess it integrates is not zero without a storm.
Its magnitude runs about 1.5 times the actual shift at seven days in May. That is the lead-time
structure below, seen against a truth, plus a quiet-time bias this comparison could not see.

### The control, first, because it sets the scale

Over the quiet window, SGP4 propagating a pre-window element set drifts a median **10.2 km**
along track in 2.9 days, with a p90 of **85 km**.

That number deserves to be read before any storm number. It says the quiet-time propagation
error at three days is already tens of kilometres — comparable with the storm signal itself at
short leads — which is why the control subtraction is not a refinement but the difference
between a measurement and an artefact.

### The result

962 comparisons over 152 objects. The population narrows twice, and both narrowings are stated
rather than applied silently:

| Population | comparisons | objects | slope | robust slope | correlation |
| --- | ---: | ---: | ---: | ---: | ---: |
| Everything scoreable | 954 | 151 | −0.03 | | |
| Free-flying (no burn between pivot and comparison) | 646 | 133 | −0.05 | 0.62 | **−0.10** |
| **Free-flying with a measured coefficient** | **422** | **81** | **1.30** | **0.65** | **0.88** |

The correlation column is the one to read first. Over the free-flying population as a whole the
predicted and observed shifts are **uncorrelated** — −0.10, which is nothing. Restricting to the
objects whose ballistic coefficient was measured from their own decay takes it to **0.88**. The
storm term is not a little bit right everywhere; it is right where it has a coefficient and
silent where it does not, and the label that says which is already on every row.

The last row is the one the term is a claim about. The storm term is the product of a ballistic
coefficient and a density excess: an object standing in with the run's population median has no
coefficient in it to test, and a `B*` inversion carries a number that Step 2 documents at length
as not being a coefficient. Restricting to objects whose `B` was **measured from their own decay
history** is a narrowing of the population, not of the residual — nothing is trimmed inside it.

**On that population the predicted and observed in-track shifts correlate at 0.88, and the
observed shift is between 0.65 and 1.3 times the predicted** depending on the estimator. The
term has the right sign, tracks the event-to-event variation, and is right in magnitude to
within about a factor of two.

> **Redrawn 2026-09-05, and the correlation withdrawn.** The rerun made to write the lead-time
> table into `gannon.json` drew its sample from the 3 September snapshot and shared **four**
> measured-coefficient objects with the 2 September draw above. Its table:
>
> | Population | comparisons | objects | slope | robust slope | correlation |
> | --- | ---: | ---: | ---: | ---: | ---: |
> | Everything scoreable | 974 | 154 | 0.42 | 0.65 | 0.05 |
> | Free-flying | 664 | 137 | 0.73 | 0.61 | 0.36 |
> | **Free-flying with a measured coefficient** | **498** | **101** | **0.74** | **0.68** | **0.64** |
>
> On the four shared objects the two runs agree to the third decimal, so the code did not move.
> The correlation did, from 0.88 to 0.64, because a Pearson correlation on this population is
> carried by its largest events — dropping the largest two per cent of predictions takes 0.88 to
> 0.68 on the first draw and 0.64 to 0.55 on the second — and the two draws had different large
> events. **The r = 0.88 is therefore withdrawn as a headline and no correlation is quoted.**
> What reproduced: the robust slope (0.65, then 0.68), the sign agreement by lead (below), the
> absence of skill inside two days and the absence of skill without a measured coefficient. The
> quiet control drifted a median 7.8 km along track on the second draw against 10.2 km on the
> first, over the same 2.9 days. The sentence that survives is the bounded one on the findings
> page: the right sign on about nine comparisons in ten at three to four days of lead, a robust
> slope of 0.63 to 0.75, no skill inside two days, one storm.

The two slopes disagree because they are answering slightly different questions and the tail is
doing work. `slope` is least squares through the origin and is pulled by the largest events;
`slope_robust` is the median of observed over predicted across the half of the events with the
largest predictions. A gap between them is a fact about the data — the large shifts came out
*larger* than predicted while the typical ones came out smaller — and both are reported rather
than one being chosen.

**The robust slope of 0.65 and the density measurement's 0.78 point the same way.** If NRLMSIS
over-predicts the density excess by about a quarter, the shift it drives is over-predicted by
about a quarter, and the observed-over-predicted slope should sit below one. It does, by rather
more than the density measurement alone accounts for, which leaves the remainder to the
coefficients and to the linearisation.

### By lead time: the skill is at three to four days and near zero inside two

> **Recomputed 2026-09-05**, after an external review asked where in the window the r = 0.88
> comes from. On the free-flying measured-coefficient population (422 comparisons, 81 objects),
> by whole day of lead, with the sign agreement and the typical residual beside the slope pair
> and the correlation. `driftwatch validate gannon` now writes this table as
> `free_flying_measured_coefficient.by_lead_day`; the numbers below were computed by the same
> function over the stored per-comparison file of the 2026-09-02 run, and the second table is
> the rerun of 2026-09-05 that wrote it into `gannon.json`, on a redrawn sample (498 comparisons,
> 101 objects, four of them shared with the first draw).

| Lead | n | objects | observed (km) | predicted (km) | slope | robust slope | correlation | sign agreement | median \|residual\| (km) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 day | 28 | 26 | −0.35 | 2.02 | 1.06 | **−0.15** | 0.96 | **39 %** | 2.2 |
| 2 days | 150 | 74 | −0.31 | 5.01 | 0.81 | **−0.04** | 0.62 | **41 %** | 6.3 |
| 3 days | 124 | 59 | 10.9 | 18.8 | 1.62 | **0.63** | 0.94 | **91 %** | 8.5 |
| 4 days | 115 | 53 | 26.5 | 34.4 | 1.17 | **0.71** | 0.87 | **96 %** | 10.0 |

The redrawn sample of 2026-09-05, same columns:

| Lead | n | objects | observed (km) | predicted (km) | slope | robust slope | correlation | sign agreement | median \|residual\| (km) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 day | 40 | 36 | −0.44 | 2.10 | 0.10 | **−0.12** | 0.13 | **38 %** | 3.3 |
| 2 days | 186 | 82 | −0.56 | 3.77 | 0.25 | **−0.09** | 0.08 | **33 %** | 6.6 |
| 3 days | 142 | 70 | 8.3 | 10.2 | 0.67 | **0.63** | 0.33 | **88 %** | 6.9 |
| 4 days | 115 | 57 | 21.2 | 27.4 | 0.83 | **0.75** | 0.64 | **97 %** | 10.1 |
| 5 days | 11 | 9 | 36.5 | 76.1 | 0.58 | 0.54 | 0.67 | 91 % | 34.5 |

The two draws agree on everything but the correlation column, which on the second draw is 0.13
and 0.08 inside two days and 0.33 and 0.64 beyond — low even where the sign agreement is 88 and
97 per cent, which is the clearest statement in this document that a correlation is the wrong
statistic for this population and the sign agreement and the robust slope are the right ones.

**The plain statement: the storm term's skill is concentrated at three to four days of lead and
is near zero inside two.** Inside two days the median observed shift is within a kilometre of
zero against a predicted 2 to 5 km, the observed sign agrees with the predicted one on 39 and 41
per cent of comparisons — chance is 50 — and the robust slope is zero or negative. The
least-squares slope and the Pearson correlation in those two rows (1.06 and 0.96 at one day, on 28
comparisons) are carried by a handful of large events and are not evidence of per-event skill;
the sign agreement is the statistic that cannot be carried by a tail, and it says there is none.
At three and four days the sign agrees on 91 and 96 per cent, the robust slope is 0.63 and 0.71,
the correlation 0.94 and 0.87, and the typical residual is 8 to 10 km against a predicted 19 to
34. Split at two and a half days: 178 comparisons inside with a sign agreement of 40 per cent and
a robust slope of −0.03; 244 beyond with 93 per cent and 0.71.

Why it is so is not mysterious and is not a defect in the term. The quiet control drifts a median
10 km along track in three days by itself (above), so a predicted storm shift of 2 to 5 km at one
or two days is inside the noise of the comparison, whatever the term's physics; the storm's
displacement grows with the square of the elapsed time and only clears that noise on the third
day. What it does mean for a screening is that **a storm forecast one or two days out does not
move an individual event's probability in a direction this validation can support**, and the
`forecast` scenario's day-one and day-two shifts should be read as an uncertainty, not a
correction. The headline r = 0.88 does not stand: it was 0.64 on the redrawn sample (above, and
"Redrawn 2026-09-05") and is not quoted; where in the window the skill lives is this table, on
both draws.

The quadratic growth is still there in the observed column — a median observed shift going 0, 0,
11, 27 km against a predicted 2, 5, 19, 34 km — which is the shape the derivation predicts, and a
term with the wrong physics could match a magnitude at one lead by accident and cannot match a
growth curve at four. But that is a statement about the population's growth curve, and the two
rows inside two days show that a right growth curve is not the same thing as per-event skill.

### Where it fails, and why that is reported rather than fixed

**Below 450 km the term does not apply and the numbers say so loudly.** In the 350–450 km band
the median observed shift is −263 km against a predicted −1.7 km, a residual of −160 sigma. That
is not a mis-tuned coefficient; it is a population that is almost entirely actively controlled
Starlink, where the along-track disagreement between two element sets is the operator's doing
and not the atmosphere's. The manoeuvre detector removes the burns it can see, and a continuous
low thrust is a ramp it cannot. This is the same failure mode the ballistic fit's thrust ceiling
was added for at this review (`docs/density-and-drag.md`), seen from the other end.

**A `B*`-derived coefficient does not predict the storm shift.** Split by coefficient source,
the least-squares slope is 1.30 for `history`, −1.39 for `bstar` and −0.06 for `typical`. The
`bstar` population has no predictive power at all and the wrong sign on the median. That is a
sharper statement than Step 2's "treat `B*` as noisy": for this purpose it is not usable, and
the honest reading of a storm term computed on a `bstar` coefficient is that its magnitude is
a guess with a label on it. The label is already on every row.

**Sign agreement is 71 per cent, not 100, and the lead-time table above says where the other 29
are.** They are almost all inside two days: 39 and 41 per cent agreement at one and two days
against 91 and 96 at three and four. At one and two days' lead the predicted shift is a few
kilometres and the quiet-time propagation error is ten, so the sign is decided by noise; by
three and four days, where the shift is tens of kilometres, it is not.

---

## 3. February 2022: the Starlink loss

A narrower question and a harder one. On 3 February 2022 SpaceX launched 49 Starlink satellites
into a 210 km insertion orbit; a G1 geomagnetic storm — the *smallest* named level — raised the
drag and 38 of them re-entered. Does the model show elevated drag there?

### First finding: the public catalogue never saw most of it

**Of the 49 satellites, CelesTrak's SATCAT carries 17.** The launch, international designator
`2022-010`, has 21 catalogued objects: 17 payloads (A through S) and 4 pieces of Falcon 9
debris. The other 32 satellites re-entered before the 18th Space Defense Squadron assigned them
catalogue numbers, and they are not in the public record at all.

That is not a limitation of driftwatch; it is a property of the data driftwatch is built on, and
it is worth stating plainly because it bounds what any tool of this kind can say about a fast
loss at low altitude. **The objects that come down fastest are the ones the catalogue is least
likely to hold.** It is the same bias that the May 2024 selection has, arriving from a different
direction.

Of the 17 catalogued payloads, six have decay dates within nine days of launch (6, 6, 7, 8, 9
and 12 February), two decayed later (October 2023 and December 2024), and nine are still in
orbit.

**What holding 17 of 49 bounds, stated plainly.** The decay evidence in this section rests on
**six of the thirty-eight satellites that were lost**, plus four pieces of Falcon 9 debris on
the same trajectory. So:

- Nothing here is a measurement over the *population* of losses. Six objects with between 0.8
  and 6.7 days of element sets cannot carry a distribution, and no percentile, median or spread
  is quoted from them anywhere in this section.
- The six are not a random six. They are the ones that survived long enough to be catalogued,
  which is a bias *towards* the slower losses — the fastest are exactly the ones the 18th Space
  Defense Squadron never assigned a number to.
- Five of the six have under a day of element sets, so their decay *rates* are element-set
  scatter rather than measurements. The command prints them and says so. Only two objects in the
  table have a span long enough for the rate to mean anything, and both are debris.
- What the six do establish is the thing the case was pulled for: that the decay at insertion
  altitude is unambiguous and enormous — 79 to 101 km of altitude lost in under a week — against
  a control group at 500 km losing 8.5 km in six weeks. That comparison needs no population.

This is a property of the public catalogue rather than of driftwatch, and it is the general
version of the survivorship problem the May 2024 sample has: **the objects that come down fastest
are the ones the catalogue is least likely to hold**, so any tool built on the public record
systematically under-observes the events a storm causes. It is the single strongest argument in
this document for the parked SATCAT-decayed-object pull.

### Second finding: the decay is unambiguous in the element sets

| Object | sets | span (d) | first alt (km) | last alt (km) | change (km) | rate (km/d) | decayed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| STARLINK A (51456) | 8 | 0.8 | 233 | 154 | −79 | −98 | 2022-02-06 |
| STARLINK L (51466) | 3 | 0.9 | 252 | 216 | −36 | −41 | 2022-02-09 |
| FALCON 9 DEB (51473) | 18 | 6.7 | 249 | 158 | −91 | −13.5 | 2022-02-16 |
| FALCON 9 DEB (51475) | 15 | 5.9 | 245 | 144 | −101 | −17.1 | 2022-02-14 |
| STARLINK-3181 (51461) | 99 | 39.2 | 284 | 424 | **+139** | +3.6 | — |
| STARLINK-3178 (51467) | 106 | 39.2 | 280 | 429 | **+149** | +3.8 | — |

Five of the lost objects have under a day of element sets before they were gone, so their rate
column is element-set scatter rather than a decay rate and two of them come out nominally
rising. The altitudes are real; those rates are not, and the command says so in its output.

The survivors are the other half of the picture: over the same 39 days they **climbed** 138 to
149 km, from the 280 km they had reached to their 420 km operational shell. The same days, the
same atmosphere, and the difference between the two groups is entirely whether the satellite
was raising itself or sitting broadside in safe mode.

**The control group at 500 km**, six Starlinks from earlier shells flying within 40 km of that
altitude through the same window, fell a median **8.5 km over 43.6 days — 0.20 km per day**.
Against tens of kilometres a day at 210 km, that is the altitude dependence of the whole
problem in one number.

### Third finding: the model shows the enhancement, and it is small

NRLMSIS, driven by the observed ap, for 4 February 2022 against a quiet 25 January:

| Altitude | storm (kg/m³) | quiet (kg/m³) | ratio |
| --- | ---: | ---: | ---: |
| 210 km | 1.71e-10 | 1.48e-10 | **1.16** |
| 300 km | 1.85e-11 | 1.39e-11 | 1.33 |
| 400 km | 2.64e-12 | 1.74e-12 | 1.52 |
| 500 km | 4.77e-13 | 2.82e-13 | 1.69 |

Observed Kp peaked at 5.33 (ap 56) over those days — a G1, exactly as recorded.

**So the answer is yes, but by 16 per cent.** The model does show elevated drag at the insertion
altitude and it does not show anything dramatic there, because at 210 km the density is set
mostly by the solar cycle and the diurnal bulge, and the geomagnetic term is a small correction
to a very large number. The ratio *grows* with altitude — 1.16 at 210 km, 1.69 at 500 km —
which is the physics: a storm heats the lower thermosphere, the atmosphere expands, and the
density at a fixed height rises by more the further that height is above the heating.

### Why 16 per cent is not a model failure, and why nothing here is adjusted for it

The loss was not a failure of the density model, and the temptation this case creates — to
conclude the geomagnetic response is under-modelled at low altitude and raise it — would be
fitting one event through the wrong parameter. Three things say the modest number is the right
one.

**The insertion altitude is the whole explanation.** At 210 km the *baseline* is
1.5e-10 kg/m³, three orders of magnitude above the 500 km value. Drag scales with that baseline,
so the satellites were already flying in air a thousand times thicker than their operational
shell before the storm added anything. A margin that thin does not need a large multiplier to be
consumed: 16 per cent of a very large number is a large number. The comparison that makes this
concrete is in the decay table above — tens of kilometres a day at 210 km against the control
group's **0.20 km per day at 500 km**, in the same days and the same atmosphere.

**And the satellites could not answer it.** They had been put into safe mode by the storm, where
they fly broadside with the largest possible area and no thrust, precisely while the drag rose.
The survivors in the same launch, which were raising themselves, climbed 138 to 149 km over the
following 39 days. The difference between the two groups is not the atmosphere; it is whether the
satellite was pushing.

**The number is in family with the published post-mortems**, which matters because it is the only
external check available on the model at this altitude:

| Source | Enhancement at ~210 km | Baseline compared against |
| --- | --- | --- |
| driftwatch, NRLMSIS 2.1, observed ap | **1.16** (16 %) | quiet 25 January 2022 |
| Fang et al. (2022), *Space Weather* — the post-mortem written with the Starlink team | 20–30 % | the 9 days before launch |
| Lin et al. (2022), *Space Weather* — physics-based whole-geospace simulation | 50–125 % at 200–400 km | pre-storm |

The three are not the same measurement: they use different baselines, different models and, in
Lin's case, a first-principles simulation rather than an empirical model. But 16 per cent sits at
the low end of a published range whose own spread is a factor of several, and the direction of
the difference is the one the May 2024 test predicts — an empirical model reading the *smallest*
enhancement of the three. Nothing here is tuned to close that gap. Two storms, measured in
opposite directions (22 per cent too large at 450–2000 km in May 2024, at the low end of the
published range at 210 km in February 2022), is not a calibration; it is two data points and a
reason to want a third.

What the case establishes is narrower and more useful than a model correction: **the model's
enhancement at 200 km is small, so an operator at insertion altitude cannot rely on the
enhancement being the warning — the warning is the baseline.** A tool that screened this launch
would have shown a 16 per cent density rise and lost the satellites anyway. That is a statement
about where to look, not about what to fix.

---

## 4. The replay run

A historical snapshot for 9 May 2024, built from `gp_history` by `driftwatch snapshot-as-of`,
screened against `fleets/demo-2024.yaml` — the demo fleet with **Sentinel-1A standing in for
Sentinel-1C**, which did not launch until December 2024 — and scored under both `quiet` and
`replay:2024-05-09`.

```
driftwatch snapshot-as-of --date 2024-05-09T00:00:00Z --fleet fleets/demo-2024.yaml \
    --min-perigee-km 380 --max-perigee-km 880 --sample 30000 --days 6 --max-age-days 5
driftwatch screen --fleet fleets/demo-2024.yaml \
    --snapshot data/snapshots/as-of/gp_asof_20240509T000000Z.parquet \
    --start 2024-05-09T00:00:00Z --days 7 --no-supplemental --history-days 20
driftwatch ballistic data/conjunctions/demo-2024_20240509T000000Z --budget-s 0 --fit-days 20
driftwatch risk data/conjunctions/demo-2024_20240509T000000Z --scenario replay:2024-05-09
```

**The snapshot.** 14,174 objects were in orbit on the day and inside the altitude band;
**13,376** had an element set within five days of it, at a median age of 0.23 days. 27 requests
to Space-Track, 153,829 element sets. By category: 6,110 debris, 4,486 Starlink, 1,739 payloads,
646 rocket bodies, 187 other constellation, 5 station.

**The run.** 1,722 events over 1,350 objects. 994 of those objects earned a measured ballistic
coefficient from their own pre-storm decay, 271 fell back to B\*, 85 to a stand-in, and one was
refused as thrusting.

| | events | red | yellow | unscoreable | max `pc` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `quiet` | 1,722 | 1 | 3 | 0 | 2.4e-4 |
| `replay:2024-05-09` | 1,722 | 1 | 2 | 1 | 1.7e-4 |

**What moved.** Over the 152 events above 1e-9 under `quiet`, the median `pc / pc_quiet` is
**0.43**: the real storm, driven by the observed record rather than a synthetic profile, lowers
the probability on most events exactly as the synthetic scenarios do. The median absolute
in-track shift is 95.8 km per object and the median relative shift between the two objects of a
pair is 27.5 km; 1,276 of the 1,350 objects are displaced *ahead* of their element sets and 74
behind, which is the sign the derivation predicts for an unmodelled density excess.

The largest movers are ZACube-1 against MACSAT 2, a pair whose quiet probability of 2.0e-12 comes
back at 6.4e-7 under the storm, and UWE-3 against STARLINK-5290 at 6.0e-16 against 9.7e-9. Both
are events the quiet screening would have discarded without a second look.

**And the cancellation split, independently.** `driftwatch storm-check` on this run gives a
relative-to-absolute ratio of **1.87**, flat across coefficient source pairs (1.76 to 1.97) and
across altitude bins — the same answer the demo run's synthetic G5 gives, on a different
catalogue, a different fleet, a different year and observed rather than designed weather. See
`docs/storm-term.md`: this is what falsified the common-mode explanation of the headline result
while leaving the result itself standing.

### The historical snapshot, and the one trap in it

`snapshot_as_of` takes each object's **newest element set at or before the date and nothing
later**. Using a set from after the date is the failure mode this exists to prevent, and it is
the one that would quietly make a storm validation come out right: an element set issued on
12 May already contains the storm's effect.

Historical snapshots live in `data/snapshots/as-of/`, deliberately not beside the live ones.
`list_snapshots` globs one directory for `gp_*.parquet` and takes the last by name, and
`gp_asof_2022…` sorts *after* `gp_20260901…` because a letter beats a digit — so a
reconstruction of an old day would silently become "the latest snapshot" for the screener, the
coefficient fit and the history loader alike. That happened once during this step, which is why
the directory exists and why this paragraph does.

They are cached permanently: `gp_history` does not change, so the file is a pure function of the
date and the object list.

---

## What Step 4 changed in the code

Nothing in the storm term. That is deliberate: the point of a validation is to find out whether
the thing is right, and adjusting it against the same data that measured it destroys the
measurement. What changed:

- `driftwatch snapshot-as-of` and `driftwatch validate`, new commands.
- `catalogue.history.backfill(..., use_stored=False)`. The backfill's shortcut — "this object is
  already held through its newest stored set" — is a true statement about an object with a 2026
  element set that says nothing at all about 2024, and with it on, a historical window came back
  empty. Every historical pull now turns it off; the cached-request check still applies, so
  nothing is fetched twice.
- `config.AS_OF_SNAPSHOT_DIR`, for the sorting trap above.

## The approximations this step adds to the list

- The observed density ratio assumes `B` is constant between the two windows. Over three weeks
  and with the manoeuvre intervals excluded that is good; for an object whose attitude mode
  changed it is not, and nothing here can see an attitude change.
- The modelled ratio uses each object's **pre-storm** element set for both windows, so the
  orbit it integrates along is the pre-storm one. Over three days of storm the semi-major axis
  moves by a few kilometres at these altitudes, which is small against a 50 km scale height.
- The control subtraction is matched on lead time in whole days and takes the median over each
  object's comparisons at that lead. An object with one control comparison contributes a
  single number as its median.
- The in-track error is measured in the *later* element set's RIC frame. The two frames differ
  by the angle the disagreement subtends, which is under a milliradian for a shift of tens of
  kilometres.

## Published work this section is measured against

Read 2026-09-03. None of it is used as an input; it is here so the two measurements above have
something external to disagree with, and so a reader can see where they do.

- Parker, W. E. and Linares, R. (2024), *Satellite Drag Analysis During the May 2024 Gannon
  Geomagnetic Storm*, J. Spacecraft and Rockets 61(6), 1412.
  <https://arxiv.org/abs/2406.08617> — the template for §1 and §2: TLE-derived density
  enhancement over the whole LEO catalogue. Reports up to a sixfold density increase at 400 km
  at the peak against a baseline twelve hours earlier, and a fourfold rise in decay rate on a
  single object (38 to 180 m/day). A peak against a short baseline is a different quantity from
  our three-day window ratio and the two are not directly comparable. What §2 adds to their
  method is set out in `docs/methods.md`, "Precedent, and what this adds".
- Flohrer, T., Krag, H. and Klinkrad, H. (2008), *Assessment and Categorisation of TLE Orbit
  Errors for the US SSN Catalogue*, Proceedings of the Advanced Maui Optical and Space
  Surveillance Technologies Conference (AMOS), Maui — ESA's Space Debris Office's derivation of
  TLE position uncertainty **from the consistency of successive element sets**, tabulated by
  orbit class. The per-band prior at the bottom of driftwatch's covariance fallback chain is a
  table of that kind, and the consistency method the whole chain rests on is theirs; see
  `docs/methods.md`, "Precedent, and what this adds", for what is done differently here.
- Bruinsma, S. et al. (2021), *Thermosphere modeling capabilities assessment: geomagnetic
  storms*, J. Space Weather Space Clim. 11, 12.
  <https://www.swsc-journal.org/articles/swsc/full_html/2021/01/swsc200061/swsc200061.html>
  — the standard multi-model, multi-storm assessment against accelerometer densities.
  NRLMSISE-00 under-estimates storm amplitudes on average; DTM2013 and CTIPe over-estimate.
- Zhang et al. (2025), *Thermospheric density variations during extreme geomagnetic storms and
  their potential impact on the orbit of the China space station*, Front. Astron. Space Sci.
  <https://doi.org/10.3389/fspas.2025.1644152> — NRLMSIS 2.0 systematically under-estimates
  through the November 2003 and March 2015 storms at GRACE-A and Swarm-A altitudes, with
  recovery-phase errors above 50 %.
- Fang, T.-W. et al. (2022), *Space Weather Environment During the SpaceX Starlink Satellite
  Loss in February 2022*, Space Weather 20, e2022SW003193.
  <https://doi.org/10.1029/2022SW003193> — the post-mortem written with the Starlink team;
  density 20–30 % above the nine days before launch at 210 km.
- Lin, C. Y. et al. (2022), *Thermospheric Neutral Density Variation During the "SpaceX" Storm*,
  Space Weather 20, e2022SW003254. <https://doi.org/10.1029/2022SW003254> — a physics-based
  whole-geospace simulation giving 50–125 % enhancement between 200 and 400 km.

**A note on how these were read.** The abstracts and the openly accessible full texts were read
directly; three of the five sit behind publisher access controls and their quantitative claims
here come from the abstract, the open preprint or a secondary summary rather than from the
figures. Every number attributed above is one stated in prose, not read off a plot, and none of
them is used in any computation. Where the exact figure matters to a conclusion — it does not,
in either section — the paper should be read in full first.
