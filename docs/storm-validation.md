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
metres to kilometres. What is measured is the disagreement between two fits, which is a *floor*
on the propagation error rather than a measurement of it.

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

By lead time, on that population:

| Lead | n | observed (km) | predicted (km) | slope |
| --- | ---: | ---: | ---: | ---: |
| 1 day | 28 | −0.35 | 2.02 | 1.06 |
| 2 days | 150 | −0.31 | 5.01 | 0.81 |
| 3 days | 124 | 10.9 | 18.9 | 1.62 |
| 4 days | 115 | 26.5 | 34.5 | 1.17 |

The quadratic growth is there in both columns — a median observed shift going 0, 0, 11, 27 km
against a predicted 2, 5, 19, 34 km — which is the shape the derivation predicts and the
strongest single piece of evidence here, because a term with the wrong physics could match a
magnitude at one lead by accident and cannot match a growth curve at four.

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

**Sign agreement is 71 per cent, not 100.** Three comparisons in ten have the observed shift
on the opposite side of zero from the predicted one. At one and two days' lead the predicted
shift is a few kilometres and the quiet-time propagation error is ten, so the sign is decided by
noise; by three and four days, where the shift is tens of kilometres, it is not.

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

**Why 16 per cent was enough to lose 38 satellites, and why nothing here is adjusted for it.**
The loss was not a failure of the density model. At 210 km the *baseline* drag is already close
to what a Starlink can overcome: 1.5e-10 kg/m³ is three orders of magnitude above the 500 km
value, and the satellites had been put into safe mode by the storm, where they fly broadside
with the largest possible area and no thrust. A 16 per cent increase on an already-marginal
margin, applied to satellites that could not raise themselves, is sufficient. The published
post-mortems say the same thing.

The temptation this case creates is to conclude the geomagnetic response is under-modelled at
low altitude and to raise it. That would be fitting one event through the wrong parameter. What
the case actually establishes is narrower and more useful: **the model's enhancement at 200 km
is small, so an operator at insertion altitude cannot rely on the enhancement being the warning
— the warning is the baseline.** The May 2024 test is where the enhancement itself is measured,
and there it comes out 22 per cent *too large* rather than too small.

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
