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

## Two numbers, always

Every row carries `pc` (shift **and** variance) as the primary number and `pc_variance_only`
(the same widened covariance, both objects left where their element sets put them) beside it.
The ratio says how much of a scenario is the displacement and how much is the spread — a
question the documentation has to answer with a measurement rather than an assertion.

On the demo run's G5 scenario, over the 998 events above a probability of 1e-9: the median
`pc / pc_variance_only` is **0.68**, and the shift **lowers** the probability on 823 of them
against raising it on 175. A relative displacement usually separates two objects that were
going to pass close, so on most events the shift is protective. The screening interest is in
the minority it raises and in the tail — pairs at 1e-80 under quiet that come back at 1e-7
because the shift moved one object onto the other, with ratios reaching 3,265.

The scale of the inputs behind that: a median absolute shift of 278 km per object, but a median
*relative* shift of only 32 km between the two objects of a pair, because a storm moves
neighbouring objects in the same direction by similar amounts. The sigma the term adds is a
median of 6.5 km per object.

Which is why the flag counts **fall** rather than rise:

| Scenario | red | yellow |
| --- | ---: | ---: |
| `quiet` | 1 | 22 |
| `forecast` | 2 | 11 |
| `storm-g5` | 1 | 12 |

A relative displacement of tens of kilometres applied to a population of near misses separates
more pairs than it creates. That is a real result and not a bug, and it is the opposite of the
intuition that a storm must make everything worse. What a storm actually does is make every
prediction *different*, and different is bad news only for the minority of pairs it pushes
together — which is exactly why the tail matters more than the count, and why the report shows
the events that moved most rather than the totals.

Every row also carries `run_id`, `snapshot`, `model_version`, `supplemental_version`,
`scenario`, both objects' in-track shifts and their sigmas, and the `source` label of the
ballistic coefficient behind each — so a surprising number can be traced to the coefficient
that produced it without leaving the output file.

## Limits, stated

- **Near-circular.** Equation (2) is a near-circular linearisation. Eccentric orbits get the
  general drag integral but not a general derivation.
- **The excess is measured against SGP4's own atmosphere**, through a `B*` that Step 2
  documents at length as noisy. An object whose `B*` is nonsense has a nonsense implied
  density and therefore a nonsense excess, which is why the coefficient's `source` label
  travels with every row.
- **The storm-response uncertainty is a prior**, not a measurement, until Step 4.
- **No coefficient means no shift**, which is a statement that we do not know rather than that
  there is none. The label says `storm:none` and the count is in the run record.
- **The shift is zero at the element set's own epoch** by construction. An object screened
  from a fresh element set is displaced less than one screened from a week-old set — which is
  correct, and is also why a run whose objects have very recent epochs will show a smaller
  storm effect than one whose objects do not.
