# The storm term

What an unmodelled density excess does to where an object is, why it is an *along-track*
problem rather than an altitude one, and how the five scenarios are built. Phase 3 Step 3.
The code is `src/driftwatch/storm/`; the density and the ballistic coefficient it multiplies
are `docs/density-and-drag.md`.

## The physics, in one sentence

Drag removes energy, the orbit sinks, and a lower orbit is a **faster** one — so a satellite
that has flown through more air than its element set assumed is not mostly lower than
predicted, it is **ahead**, and it keeps getting further ahead for as long as the error goes
uncorrected.

## The derivation

For a near-circular orbit of semi-major axis `a` under density `rho`, with `B = C_D A / m`:

```
da/dt = -B rho sqrt(mu a)                                              (1)
```

The mean motion is `n = sqrt(mu / a^3)`, so `dn/da = -(3/2) n/a` and

```
dn/dt = -(3/2)(n/a) da/dt = (3/2) n B rho v,      v = sqrt(mu/a)        (2)
```

An excess `drho` over what the element set already knows about adds a mean-motion drift, and
the along-track angle is the *twice*-integrated drift — once to get from a rate of change of
angular rate to an angular rate, again to get an angle:

```
dtheta(t) = integral_0^t (t - tau) (dn/dt)(tau) dtau                    (3)
```

Multiplying by `a` to turn an angle into a distance, and using `a n = v`:

```
s(t) = (3/2) B v^2 integral_0^t (t - tau) drho(tau) dtau                (4)
```

and for a **constant** excess this collapses to the closed form:

```
s(t) = (3/4) B drho v^2 t^2                                            (5)
```

Quadratic in time, linear in the ballistic coefficient, linear in the excess, quadratic in
the orbital speed — which is what the prompt predicted before any of it was written.

### The sign

A positive excess means more drag than the element set assumed, so the object is **ahead** of
where the element set puts it: the in-track displacement is positive in the +I direction of
the RIC frame. This is the one sign in the phase that reads backwards at first glance — "more
drag" sounds like "slower" — and it is pinned by two tests, one on the closed form and one on
the numerical integration, which reports a perturbed orbit that is simultaneously *lower* and
*further along*.

### The general form actually used

An eccentric orbit does its drag at perigee, and every integral in `drag/` carries
`P(t) = |v_rel| (v_rel . v)` rather than assuming `rho v^3`. Carrying that through (2):

```
s(t) = (3/2) (n a^2 B / mu) integral_0^t (t - tau) drho(tau) P(tau) dtau  (6)
```

which reduces to (4) exactly when `P = v^3`. This is what `shift_from_profile` evaluates, and
it is what the scenarios use. The near-circular assumption has **not** gone away: equation (2)
linearises the relation between energy loss and mean motion, which is a near-circular
statement. The term is therefore reported as it stands for near-circular orbits and is an
approximation for eccentric ones; it is in the approximations list.

## Verified against a numerical integration

`term.integrate_test_orbit` integrates (1) together with `dtheta/dt = n(a)` by fourth-order
Runge–Kutta, twice — once at `rho` and once at `rho + drho` — and differences the along-track
angles. No appeal to the closed form anywhere in it. A **step** density change, as the prompt
asked, with `drho = rho` (a doubling) and `B = 0.01`:

| Altitude | Days | Numerical | Closed form (5) | Error |
| ---: | ---: | ---: | ---: | ---: |
| 300 km | 1 | 86.915 km | 86.885 km | −0.035 % |
| 300 km | 3 | 782.779 km | 781.965 km | −0.104 % |
| 300 km | 7 | 4267.725 km | 4257.362 km | −0.243 % |
| 400 km | 1 | 14.158 km | 14.157 km | −0.006 % |
| 400 km | 3 | 127.439 km | 127.417 km | −0.017 % |
| 400 km | 7 | 693.991 km | 693.714 km | −0.040 % |
| 550 km | 1 | 1.288 km | 1.288 km | −0.001 % |
| 550 km | 3 | 11.596 km | 11.596 km | −0.002 % |
| 550 km | 7 | 63.137 km | 63.134 km | −0.004 % |

Better than a quarter of a per cent in the worst case, against the "few per cent" the prompt
asked for. The error is always the same sign and grows with the decay, which is the
approximation being measured: the closed form holds `v` fixed, and by day seven at 300 km the
orbit has genuinely dropped far enough that it is not.

**Read the magnitudes.** A doubled density at 300 km puts an object 4,000 km along its own
track in a week. That is not a rounding error on a conjunction screening; it is the difference
between a conjunction and no conjunction at all. At 550 km the same doubling is 63 km, and at
800 km it would be a few kilometres. This is why the storm layer matters most exactly where
the catalogue is densest.

## Where the excess is measured from

`drho` is **not** the density. It is the scenario's density minus the density the object's own
element set is already flying through.

Every element set carries a `B*`, and SGP4 turns that into a decay. Given the object's
physical `B` from Step 2, `ballistic.density_from_decay` inverts that decay into the effective
density SGP4's own atmosphere is supplying over the span — one constant number, because SGP4's
atmosphere is a static exponential model and does not vary along the orbit the way NRLMSIS
does. The scenario's excess is measured from that. An element set fitted during a storm
already knows about the storm; one fitted the week before does not, and the difference is
exactly what displaces it.

## Why `quiet` applies nothing at all

The prompt calls for a `quiet` scenario "using observed conditions" and also for the Phase 2
quiet scenario to be **bit-for-bit unchanged as the regression baseline**. These are the same
requirement, not two:

- The Phase 2 empirical covariance was fitted on real element sets that flew through whatever
  weather actually happened. It is already an observed-conditions model.
- Every other scenario is read as a *difference* from quiet, so quiet has to be the thing that
  does not move.

So `quiet` carries no weather table and applies no storm layer, and the protocol makes that
free: `RicCovariance.mean_shift_ric_km` defaults to `None`, every Phase 2 model returns
`None`, and `run_risk` adds zero. The Step 2 tests that pin the Phase 2 numbers still pass
untouched.

This is a decision and it is flagged for the review. The alternative reading — that `quiet`
should apply the storm term under observed conditions, and would then be non-zero wherever an
object's own `B*` disagrees with NRLMSIS — would make the baseline move whenever the density
model changed, which is precisely what a regression baseline must not do.

## The five scenarios

| Name | Weather | Storm term |
| --- | --- | --- |
| `quiet` | none | none — the Phase 2 model untouched |
| `forecast` | observed where the record reaches, SWPC's three-day Kp forecast, then the 27-day outlook | yes |
| `storm-g3` | the May 2024 sequence scaled to peak Kp 7 | yes |
| `storm-g4` | scaled to peak Kp 8 | yes |
| `storm-g5` | scaled to peak Kp 9 (the sequence very nearly unscaled) | yes |
| `replay:<date>` | the observed record for a historical window | yes |

### Why a real storm and not a square wave

A flat Kp for three days is not what a storm looks like, and the difference is not cosmetic:
the displacement weights the excess by the time **remaining** in the window, so when the storm
arrives matters as much as how big it is. A test measures this directly — the same total
excess delivered on day one displaces an object more than ten times as far as the same excess
delivered on day seven.

The May 2024 sequence carries a sudden commencement, a main phase of about a day and a
recovery of two. Scaling is on the **Kp** axis, because Kp is quasi-logarithmic and scaling ap
instead would produce a "G4" with no counterpart in the record. Where the storm starts in the
window is `--storm-offset-days`, one day by default and stated on every run, because a
scenario that hid it would be hiding half its own answer.

### Only the storm's own intervals become synthetic

`apply_synthetic` takes a mask. A storm occupies a few days of a window that is otherwise
observation or forecast, and relabelling the whole table `synthetic` would be a false
statement about every row the storm never touched — their provenance, skill, issue time and
`ap_sigma` are still what the feed said. The rows the storm does replace get
`provenance = synthetic`, `skill = designed` and a `synthetic:<level>` source.

## The variance

Three terms, in quadrature, each one a *displacement* passed through the same weighted
integral (6) rather than a fraction scaled off the total.

**The coefficient.** `sigma_B` from Step 2, on every row with its source label. A fitted
coefficient carries the statistical error of its own decay measurement, floored at 5 %; a `B*`
inversion carries a 50 % prior; a `typical` stand-in carries the spread of the pool it came
from, floored at a factor of two. Contributes `(sigma_B / B) * s`.

**The density model.** NRLMSIS's own uncertainty is tens of per cent, but most of it
**cancels** — and understanding why is what decides the number used. Only the product
`B rho` is observable from a decay, so a model that is low by 20 % returns a coefficient that
is high by 20 % and a product that is right. What has no baseline to cancel against is the
model's error in the **storm response** — the ratio of stormy to quiet — so that is the term
carried: `DENSITY_STORM_RATIO_SIGMA_REL`, 30 %, a prior that Step 4 will measure against
May 2024 and should replace. For an object whose coefficient did *not* come from a fit through
this same model — `bstar` or `typical` — the cancellation argument does not apply and the
absolute uncertainty (`DENSITY_ABSOLUTE_SIGMA_REL`, 15 %) goes in with it in quadrature.

It is applied **coherently in time**. A model bias is not a fresh random number every three
hours, so it passes through the weighted integral rather than being summed in quadrature
across samples — which would understate it by roughly the square root of the number of
samples, that is, by a factor of fifty over a week.

**The index.** `ap_sigma` from Step 1: small where the index was measured, the unskilled part
of the climatological spread where it was forecast beyond three days, and the scenario's own
stated spread for a designed storm. There is no closed form for the density's response to ap,
so it is evaluated: the whole track is recomputed with every interval's ap raised by its own
sigma, and the difference in the resulting displacement is the term. That is one extra density
evaluation per object, which is why the term is computed once per object rather than once per
event.

The total is added to the **in-track element** of that object's RIC covariance, which is where
the uncertainty of an along-track displacement belongs.

## What the protocol change is

Exactly one field. `RicCovariance` grows `mean_shift_ric_km`, an `(n, 3)` array or `None`:

```python
@dataclass(frozen=True)
class RicCovariance:
    cov_km2: np.ndarray                       # (n, 3, 3)
    source: str
    mean_shift_ric_km: np.ndarray | None = None
```

`None` means "the element set is right about where this object is", which is what every
Phase 2 model says and why they needed no change. Step 3 only ever fills the in-track
component, but the field is a full RIC vector so that a later scenario wanting to move an
object radially does not have to change the protocol again.

`run_risk` rotates both objects' shifts out of their own RIC frames into TEME, differences
them, and adds the result to the stored relative position before projecting onto the encounter
plane.

### Why applying the shift at the stored time of closest approach is exact

It looks like an approximation — a real in-track displacement moves the time of closest
approach as well as the position at it — and it is not. The encounter plane is perpendicular
to the relative velocity. The component of a shift **along** the relative velocity is
precisely the part that moves the TCA rather than the miss at it, and the projection onto the
plane removes it. What survives the projection is what changes the probability. Nothing
rescreens, and nothing needs to.

## Three numbers, always

A scenario does two things at once, and they pull in opposite directions often enough that one
number hides both. So every row carries all three:

| Column | The objects | The covariance |
| --- | --- | --- |
| `pc` | moved by the scenario's mean shift | the scenario's, with the shift's uncertainty in it |
| `pc_shift_only` | moved | the one the run would have had without the storm layer |
| `pc_variance_only` | left where their element sets put them | the scenario's |

They are not decomposable into one another — the probability is not linear in either input — so
all three are computed rather than one being inferred from the other two. Under a model with no
storm layer the three are the same array, which is what keeps the Phase 2 `quiet` scenario
unchanged.

(`pc_shift_only` was added at the Step 3 review. The step shipped with `pc` and
`pc_variance_only`, which separates the two effects only if one is willing to read the shift's
contribution as a residual.)

On the demo run's G5 scenario, over the 1,104 events above a probability of 1e-9 under `quiet`:
the median `pc / pc_quiet` is **0.27**, and the storm **lowers** the probability on 972 of them
against raising it on 132. Split by band on the variance-only probability, the shift alone is
what does it:

| `pc_variance_only` band | n | median `pc` | median `pc_shift_only` | median `pc_variance_only` | `pc`/variance-only | lowered by the shift | raised |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1e-12 to 1e-9 | 482 | 3.4e-11 | 1.2e-11 | 6.8e-11 | 0.88 | 403 | 79 |
| 1e-9 to 1e-7 | 521 | 6.2e-9 | 1.5e-9 | 1.7e-8 | 0.66 | 450 | 71 |
| 1e-7 to 1e-5 | 605 | 1.6e-7 | 3.3e-8 | 4.4e-7 | 0.52 | 512 | 93 |
| 1e-5 to 1 | 11 | 1.5e-5 | 4.3e-6 | 3.2e-5 | 0.49 | 10 | 1 |

The larger the event, the more the shift lowers it. The screening interest is in the minority it
raises and in the tail — pairs at 1e-80 under quiet that come back at 1e-7 because the shift
moved one object onto the other, with `pc / pc_variance_only` reaching 3,270.

So the flag counts **fall** rather than rise:

| Scenario | red | yellow | unscoreable |
| --- | ---: | ---: | ---: |
| `quiet` | 1 | 22 | 0 |
| `forecast` | 2 | 10 | 113 |
| `storm-g5` | 1 | 11 | 113 |

A displacement of tens of kilometres applied to a population whose misses are a few kilometres
separates more pairs than it creates. That is a real result and not a bug, and it is the
opposite of the intuition that a storm must make everything worse. What a storm actually does is
make every prediction *different*, and different is bad news only for the minority of pairs it
pushes together — which is why the tail matters more than the count, and why the report shows
the events that moved most rather than the totals.

> **Withdrawn 2026-09-05.** The table and the paragraph above describe displacements the term
> should never have applied. The tens of kilometres were almost all on Starlinks whose supplemental
> B\* described a thrusting plan, and on station-kept primaries; on the population whose shifts
> were legitimate — both objects free-flying — the median relative displacement is 2 to 7 km and
> the probability is lowered and raised in nearly equal numbers. The section "Corrected 2026-09-05"
> below has the measurement. The 113 unscoreable events were the same error seen from the other
> side.

Every row also carries `run_id`, `snapshot`, `model_version`, `supplemental_version`,
`scenario`, both objects' in-track shifts and their sigmas, the **relative** shift that actually
entered the miss, and the `source` label of the ballistic coefficient behind each — so a
surprising number can be traced to the coefficient that produced it without leaving the output
file.

`relative_shift_km` is computed as a vector: both objects' in-track displacements are rotated
out of their own RIC frames and differenced in TEME. The scalar difference of the two in-track
components, which is the obvious thing to write, is **not** a displacement, because the two
frames are different — for a crossing geometry they can be nearly perpendicular.

## Attacking the result: is the relative shift what we think it is?

> **Correction, propagated 2026-09-03 (Phase 3 Step 4 review).** Until the Step 3 review this
> page, the plan, the design brief and two docstrings all explained the headline result by
> **common-mode cancellation**. That explanation is withdrawn. The result — a storm lowers the
> probability on most events — stands unchanged and is measured three ways below; the mechanism
> is **two nearly independent displacements separating more pairs than they create**, not two
> alike displacements cancelling. Everywhere the old wording appeared now carries a dated note
> beside it rather than a silent rewrite, as with the Phase 2 dilution wording. The rest of this
> section is the working that produced the correction and is left standing.

The result above is the project's headline and it is counter-intuitive, so before it is
published it has to survive being attacked. It was attacked at the Step 3 review, and it
survived — while the *explanation* attached to it did not. This section is that in full,
because a result whose stated mechanism turned out to be wrong is exactly the kind of thing a
reader is entitled to see worked through rather than quietly corrected.

**What was believed.** That a storm displaces both objects of a pair in the same direction by
similar amounts, so that only a small *relative* shift reaches the miss — a common-mode
cancellation — and that a relative displacement of that modest size, spread over a population of
near misses, separates more pairs than it creates.

**The obvious failure mode.** Two objects can also come out with similar shifts because they
were handed the same coefficient by the same rule: both standing in with the run's `typical`
median for their category and altitude band, say. If the cancellation were an artefact of shared
inputs it would be strongest where the inputs are shared and weakest where they are not, and it
would say nothing about the atmosphere.

`driftwatch storm-check <run>` splits the **relative-to-absolute shift ratio** — the relative
displacement that enters the miss, over the mean of the two objects' own displacements — two
ways and lets the split answer. The ratio runs from 0 (the two shifts identical: perfect
cancellation) to 2 (one shift zero, or the two exactly opposed: none at all).

**By ballistic coefficient source.** A pair whose two coefficients were measured independently
— `history` against `history`, each fitted from its own object's decay — shares no input beyond
the density model. If the ratio there is as small as it is for a pair sharing a `typical`
stand-in, shared values are not what is producing it.

**By the altitude difference between the two objects.** This is the physical prediction and the
sharper test. The shift goes as `B drho v² t²`, and the density falls by an order of magnitude
every 50 km or so, so two objects in the same shell see nearly the same excess and two objects
100 km apart do not. **If the cancellation is physical the ratio must rise with the altitude
difference. If it is an artefact of shared coefficients it has no reason to depend on altitude
at all.**

Which altitude matters here, and it is not the obvious one. A conjunction *is* a near-coincidence
in position, so the two objects are at nearly the same altitude at the moment they pass — a
median of 8 km apart on the demo run, with no range to show a trend across. The displacement is
accumulated over the whole window along each object's own orbit, so the axis is the **mean
altitude of the two orbits**, which does have a range.

### What the splits actually say

Run on the demo run's G5 scenario (5,591 scoreable events) and on the May 2024 replay
(`docs/storm-validation.md`, 1,721 events of a historical catalogue under the observed record).

**By ballistic coefficient source pair**, demo run under G5:

| Pair | events | median relative | median absolute | median ratio |
| --- | ---: | ---: | ---: | ---: |
| `history`+`history` | 2,942 | 30.2 km | 18.0 km | **1.89** |
| `history`+`typical` | 2,060 | 85.9 km | 44.8 km | **1.93** |
| `bstar`+`history` | 581 | 8.0 km | 4.2 km | **1.86** |
| same source | 2,948 | 30.2 km | 18.0 km | 1.89 |
| different sources | 2,643 | 53.5 km | 29.3 km | 1.92 |

**By the difference in the two objects' orbital altitudes**, same run:

| Difference | events | median ratio |
| --- | ---: | ---: |
| 0–2 km | 296 | 1.91 |
| 2–10 km | 2,252 | 1.92 |
| 10–30 km | 2,382 | 1.90 |
| 30–100 km | 513 | 1.89 |
| 100–300 km | 103 | 1.92 |
| over 300 km | 45 | 1.86 |

Rank correlation of the ratio with the altitude difference: **−0.10**. Overall ratio **1.91**,
p90 1.996.

The May 2024 replay, independently — a different catalogue, a different fleet, a different year,
and observed weather rather than a designed profile — gives **1.87** overall, 1.76 to 1.97
across source pairs, and across altitude bins:

| Difference | events | median ratio |
| --- | ---: | ---: |
| 0–2 km | 39 | 1.35 |
| 2–10 km | 230 | 1.88 |
| 10–30 km | 516 | 1.88 |
| 30–100 km | 805 | 1.87 |
| 100–300 km | 100 | 1.88 |
| over 300 km | 31 | 1.85 |

**The one place the physical prediction shows at all** is that first bin: pairs whose orbits are
within 2 km of each other in mean altitude come out at 1.35 rather than 1.87. That is the right
direction — genuinely co-altitude objects do see more of the same excess and do cancel more —
and it is worth reporting rather than smoothing away. But it rests on 39 events, the demo run's
much larger sample puts the same bin at 1.91 with no trend at all, and 1.35 is still nowhere near
the small ratio a common mode would need. Whatever cancellation exists is a second-order effect
in the narrowest bin, not the mechanism behind the headline.

### And the answer is not the one the result was explained by

**There is no common-mode cancellation.** The relative shift is not smaller than the two
absolute shifts; it is close to **twice** their mean, which is what a ratio of 1.91 out of a
possible 2 means — the two displacements are nearly independent, not a common mode.

Three measurements say why, and they are consistent with each other:

* The two objects' in-track directions are **not** the same direction. The median angle between
  them at the encounter is **120°** (p10 46°, p90 160°), with a median relative speed of
  13.2 km/s. A conjunction between two objects genuinely moving together is rare, because a low
  relative speed is precisely what stops two objects from closing on each other. The pairs a
  screener finds are crossing pairs.
* The two shifts are **uncorrelated**: r = 0.08 across the 5,591 events, with the two in-track
  components agreeing in sign only 59 per cent of the time. Even at the same altitude, two
  objects differ in ballistic coefficient by orders of magnitude — a Starlink and a Fengyun 1C
  fragment at 500 km are a factor of thirty apart.
* The ratio is **flat** in both splits. That is the real content of the two tables above: a
  quantity that does not move when the coefficient source changes and does not move when the
  altitude separation changes by two orders of magnitude is not being set by either. It is being
  set by the encounter geometry, and 1.91 is what near-independent displacements give.

The earlier reading — that a storm moves neighbouring objects together and only the small
residual reaches the miss — came from comparing a *per-event relative* shift at the time of
closest approach against a *per-object absolute* shift at the end of the window, which are not
comparable quantities. Compared like with like, the mechanism disappears.

**The result survives the loss of its explanation, and needs a simpler one.** The storm still
lowers the probability on most events, and the reason is that it displaces the objects by tens
of kilometres while their misses are a few: almost any large displacement applied to a near miss
separates the pair. Nothing about that requires the two shifts to be alike. It also explains the
band structure above — the bigger the event, the tighter the miss, the more surely a large
displacement moves the pair apart.

So the two splits the review asked for did their job twice over. They excluded the artefact:
independently measured pairs behave exactly like pairs sharing a stand-in, so the ratio is not
coming from shared inputs. And they falsified the mechanism the result had been attributed to,
which the aggregate number alone would have gone on hiding.

> **Corrected again 2026-09-05.** The paragraph "the result survives the loss of its explanation"
> above is itself withdrawn. The lowering lived entirely in events with an operator-controlled side,
> which the storm term should never have displaced; over the events with both objects free-flying
> the probability is lowered and raised in nearly equal numbers, before and after the correction
> alike. The independence of the two displacements stands, at 1.85 of 2 on the free-flying pairs.
> The full account is in "Corrected 2026-09-05: operator-controlled objects are not displaced"
> below. These splits could not have found the error: they cut along the axes a physical
> cancellation would show on, and not along whether the objects were under control.

### A third split, added at the Step 4 review: how far the validation reaches

Step 4 measured the storm term against the May 2024 record and found it skilful — the right sign
on about nine comparisons in ten at three to four days of lead, none inside two — for objects
whose ballistic coefficient was fitted from their own decay, and of no demonstrated skill for
objects carrying a B\* inversion or a population stand-in (the r = 0.88 once quoted here moved to
0.64 on a redrawn sample and is withdrawn, 2026-09-05; `docs/storm-validation.md`). An event needs **both** its
objects measured before that measurement reaches it, so every row now carries `storm_validity`
and every aggregate here is reported over the validated events, over the indicative ones, and
over both — never over both alone.

**The ratio, both ways.** The finding survives the split on both runs, which is the first thing
to check:

| Population | demo G5, n | ratio | May 2024 replay, n | ratio |
| --- | ---: | ---: | ---: | ---: |
| `validated` — both coefficients measured | 2,942 | **1.89** | 1,062 | **1.79** |
| `indicative` — at least one not | 2,649 | **1.92** | 659 | **1.96** |
| combined | 5,591 | 1.91 | 1,721 | 1.87 |

Four numbers between 1.79 and 1.96, on two different catalogues in two different years under a
designed profile and an observed record. There is no cancellation in the population the
validation covers either.

**And the split found something the combined number was hiding.** The effect split — which of
the two effects moves the probability — is *not* the same in the two populations, and the
difference is large:

| Band on `pc_variance_only` | validated: median `pc / pc_variance_only` | indicative | combined |
| --- | ---: | ---: | ---: |
| 1e-12 to 1e-9 | **0.36** | 0.98 | 0.88 |
| 1e-9 to 1e-7 | **0.17** | 0.84 | 0.66 |
| 1e-7 to 1e-5 | **0.12** | 0.80 | 0.52 |
| 1e-5 to 1 | **0.24** | 0.85 | 0.49 |

Read down the first column: **where the storm term is validated, the displacement lowers the
probability by roughly an order of magnitude**, and it lowers it on 718 of the 835 comparable
events. Where it is indicative the ratio sits near 0.85 and the shift barely moves the number at
all — which is what would be expected of a displacement built on a coefficient that has no
demonstrated relationship to the object.

That is a stronger statement of the headline result than the combined figure makes, and it is
also a warning. The combined median of 0.52 in the 1e-7 band is not a measurement of anything:
it is an average of a large validated effect and a near-absent indicative one, weighted by how
many objects happened to have a usable decay history. **A reader given only the combined number
would be reading the coverage of the coefficient fit as though it were physics.** That is the
argument for the split, and it is why the combined column is never printed on its own.

## Extrapolated events are unscoreable

The derivation holds the semi-major axis fixed and integrates a constant-`v` drift twice. Both
are small-perturbation statements, and the same arithmetic that gives the ISS a few hundred
kilometres under a G5 gives a high area-to-mass fragment at 300 km a hundred thousand — a
faithful evaluation of a formula outside its domain.

Step 3 shipped with that flagged: the number was reported with an `!extrapolated` marker on the
covariance source. **At the Step 3 review that was changed to a refusal.** Past
`STORM_MAX_SHIFT_REVOLUTIONS` — a quarter of the orbit's circumference — the term has stopped
being a correction to a known position and has become a claim about *where in its orbit* the
object is, and a probability computed from such a position is arithmetic with nothing behind it.
A marked number is still a number, and a number in a probability column will be read, sorted and
thresholded.

So every event involving such an object is reported unscoreable:

- `pc`, `pc_shift_only`, `pc_variance_only`, `pc_alfano`, `pc_chan`, `pc_max` and `pc_max_scale`
  are **NaN**;
- `region` and `flag` are `unscoreable`, `confidence` is `none`;
- `scoreable` is false and `unscoreable_reason` names the object and the size of the violation;
- and the event is excluded from every aggregate — the flag counts, the maxima, the
  Foster/Alfano comparison, the cancellation split and the effect split alike.

Nothing is dropped. The event keeps its geometry, its covariance, both shifts and their sigmas.
What is withheld is only the number a reader could act on.

The **cut is the displacement test alone**, which is what the review specified. The decay
fraction — one part in a thousand of `a` over the window — is the wider test, and it still marks
the covariance source `!extrapolated` without withdrawing the event, because "this object's
implied decay was large" is a caveat a reader can weigh while "we do not know where in its orbit
it is" is not.

### What the 42 objects are

> **Corrected 2026-09-05.** The explanation below is wrong. These objects were Starlinks on
> supplemental element sets whose B\* described a thrusting plan, not drag; the storm term should
> never have been applied to them, and under the corrected rule (next section) no event is
> unscoreable. The paragraphs are left as written because the reasoning that went wrong is worth
> seeing: a faithful evaluation of a formula outside its domain was the right diagnosis of the
> symptom and the wrong diagnosis of the cause.

On the demo run's G5 scenario, **42 objects over 113 of the 5,704 events**. (Step 3 reported 53
under the wider test and the coefficients it had then; the thrust ceiling removed some of them
by taking a thrusting satellite's implausible coefficient away, and the cut is now the
displacement test alone.)

They are one population, which is the thing worth knowing:

| | |
| --- | --- |
| Category | 40 Starlink, 2 other constellation. No debris, no rocket bodies, no payloads. |
| Altitude band | 40 at 450–550 km, 2 at 550–650 km. None higher. |
| Coefficient source | 36 `typical`, 4 `history`, 2 `bstar`. |
| Displacement | 0.25 to 1.27 revolutions of the orbit. |

So they are **operated satellites in the densest, lowest shell of the constellation**, mostly
carrying a stand-in coefficient because their own decay history is contaminated by
station-keeping. Under a G5 the arithmetic puts them a quarter to more than a full revolution
ahead of their element sets, which is not a position statement — and it is a faithful evaluation
of the formula, because an object at 450 km under a sustained Kp 9 really is being displaced by
an amount the linear theory cannot express. The right answer for them is a re-entry-style
integration, not a bigger number: `ROADMAP.md` carries that as the lifetime-loss item.

On the May 2024 replay, run against the observed record rather than a synthetic G5, **one**
object crosses the line: STARLINK-30105, 0.67 of a revolution. The count is a property of the
scenario's severity, not of the code.

## Corrected 2026-09-05: operator-controlled objects are not displaced

> An external review found the correctness error this section records. Everything above it is
> left as written, with this section as the correction, in the same manner as the cancellation
> withdrawal above.

**The error.** The excess density is measured against SGP4's own atmosphere through the element
set's B\*, and the term was applied to every object with a coefficient. Two classes of object
should never have had it. A **trajectory that is the operator's** — SpaceX's published states,
served by Stage C since Phase 4 Step 1, or CelesTrak's supplemental fit to those same states —
already carries the operator's drag model and planned burns, so there is no excess over SGP4's
atmosphere to measure: the B\* of a fit to a thrusting plan is not a drag term and the "implied
density" inverted from it is a number with no meaning. And a **station-kept or observed-manoeuvring
satellite** on a tracking-derived element set will burn rather than drift, so the direction of its
displacement under a storm is the operator's, not the atmosphere's.

**The rule now.** For a trajectory reason nothing is added at all — no mean, no variance — and the
label says `storm:operator-controlled/served` or `/operator-ephemeris`. For an object reason the
mean is zero and the in-track variance is kept, because the size of the storm's push is still a
legitimate uncertainty when the response to it is unknown: `/known`, `/observed`. `storm_validity`
gains a fourth value, `operator-controlled`, for an event whose two objects were both given no
shift; an event with one such side is judged on its free-flying side alone. The model version says
`storm/<scenario>/2`. Objects on an operator's trajectory get no density track either, which on the
3 September run is 1,681 of the 2,944 objects and more than halves the scenario step.

**The 42 objects, explained.** The "extrapolated events are unscoreable" section above lists 42
objects on the 1 September run — 40 Starlink, 2 other constellation, 36 of them on a `typical`
coefficient — and explains them as *operated satellites in the densest shell, faithfully
evaluated outside the linear theory*. That explanation was wrong. They were Starlinks whose
supplemental B\* described a thrusting plan; inverting it gave an implied density that was
negative or absurd, an excess of the same size, and a displacement of up to 31,000 km. On the
3 September run the same error produced 36 unscoreable objects over 70 or 71 events per scenario,
every one a Starlink on a supplemental element set. **They were this category error seen from the
other side**: the refusal to score them was the right instinct applied to the wrong cause. Under
the corrected rule no event on either run is unscoreable.

**What the correction moved on the 3 September run**, every scenario rescored from the stored
events (`data/conjunctions/step2-attached`, run `20260903T175632Z-9a31`, the weather tables
rebuilt from the cached feeds):

| Scenario | red, before → after | yellow, before → after | unscoreable, before → after | EOS SAT-1 vs 61705 |
| --- | ---: | ---: | ---: | --- |
| `quiet` | 1 → 1 | 20 → 20 | 0 → 0 | red, dilution, low confidence, 1.076 × 10⁻⁴ |
| `forecast` | 0 → **1** | 16 → 19 | 71 → **0** | yellow 4.98 × 10⁻⁵ → **red, dilution, low**, 1.09 × 10⁻⁴ |
| `storm-g4` | 0 → **1** | 15 → 17 | 71 → **0** | as above |
| `storm-g5` | 0 → **1** | 13 → 17 | 70 → **0** | as above |

Every red and every yellow, before and after, is on a pair with a Starlink secondary; the one red
is the EOS SAT-1 dilution-region flag, which the uncorrected scenarios had turned yellow by
displacing the Starlink with a stand-in coefficient. Of the 6,224 events, **5,243 have an
operator-controlled side** (EOS SAT-1 station-keeps and its 4,222 events are mostly against
Starlinks) and **4,088 have both sides controlled**; 1,735 are `validated` on a free-flying
measured side and 401 `indicative`.

**The headline ratio.** Over the 981 events with both objects free-flying — the only population on
which a relative-to-absolute ratio means anything, since one displacement zeroed by rule makes it
2 by construction — the ratio is **1.85** under `forecast`, `storm-g4` and `storm-g5` alike
(validated 1.85, indicative 1.84), flat in the altitude difference (rank correlation 0.05 to 0.10).
The no-cancellation finding survives on the population it can be measured on; the 1.91 quoted
above was over every event, including the ones whose Starlink side was displaced by a nonsense
excess, and the two figures should not be read as the same measurement.

**And the result the cancellation claim was explaining does not survive.** "A storm lowers the
probability on most events" was measured on this run as a median `pc / pc_variance_only` of 0.31 to
0.40 over the validated events and 0.66 over the events with a controlled side. Split by whether
both objects are free-flying, before the correction:

| Population, `storm-g5` before the correction | n with `pc_variance_only` > 10⁻¹² | median `pc / pc_variance_only` | lowered | raised |
| --- | ---: | ---: | ---: | ---: |
| both objects free-flying | 98 | **0.98** | 55 | 43 |
| at least one operator-controlled | 2,291 | **0.67** | 2,045 | 246 |

The lowering lived entirely in the events with a controlled side — a Starlink displaced by tens of
kilometres on a coefficient that described its thrust, or a station-kept primary displaced against
its operator's intent — and the free-flying population, whose shifts the correction did not touch,
was never lowered: the median relative displacement there is 2 km under `forecast`, 4 km under
`storm-g4` and 7 km under `storm-g5`, against covariances of kilometres to tens of kilometres, and it
lowers and raises in nearly equal numbers. After the correction the controlled-side population sits
at 1.00 (its only storm effect is the kept variance on the known primaries: 143 lowered, 41 raised
of 2,295 under `storm-g5`). **So the headline result of Phase 3 is withdrawn as a finding of these
runs**: it was arithmetic on displacements the term should never have applied. What remains
measured is narrower — on this fleet the storm term moves free-flying events' probabilities little
either way, and the two displacements of a free-flying pair are nearly independent — and whether a
storm lowers or raises the probability of a free-flying event is decided by the size of its
displacement against the miss and the covariance, which on this fleet is small, because the
free-flying primaries are the three cubesats at 540 to 815 km and the lowest, most displaced
objects in the run are all under operator control.

## Limits, stated

- **Near-circular.** Equation (2) is a near-circular linearisation. Eccentric orbits get the
  general drag integral but not a general derivation.
- **The excess is measured against SGP4's own atmosphere**, through a `B*` that Step 2
  documents at length as noisy. An object whose `B*` is nonsense has a nonsense implied
  density and therefore a nonsense excess, which is why the coefficient's `source` label
  travels with every row.
- **The storm-response uncertainty was a prior** until Step 4 measured it. Over May 2024 the
  model **over-predicts** the enhancement by about 22 per cent, consistently across altitude;
  the 30 per cent carried here is the right magnitude and symmetric where the truth is biased.
  Nothing is tuned to that — see `docs/storm-validation.md`.
- **No coefficient means no shift**, which is a statement that we do not know rather than that
  there is none. The label says `storm:none` and the count is in the run record.
- **The shift is zero at the element set's own epoch** by construction. An object screened
  from a fresh element set is displaced less than one screened from a week-old set — which is
  correct, and is also why a run whose objects have very recent epochs will show a smaller
  storm effect than one whose objects do not.
