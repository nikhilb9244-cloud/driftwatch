# Density and drag

Phase 3 Step 2. How driftwatch gets a density along an orbit, and how it turns that density
into a force on a particular object. Step 3 turns the pair into an in-track displacement;
this page is everything up to that point.

Code: `src/driftwatch/drag/density.py`, `src/driftwatch/drag/ballistic.py`. Commands:
`driftwatch density` for the sanity checks, `driftwatch ballistic <run>` for the
coefficients.

## The model

**NRLMSIS 2.1, through `pymsis`.** The US Naval Research Laboratory's empirical thermosphere
model: a fit to decades of satellite drag, mass spectrometer and incoherent-scatter radar
data, parameterised by date, position, solar flux and geomagnetic activity. It is the
standard baseline for this kind of work and the version is recorded in every run
(`MSIS_VERSION`).

**Its own uncertainty is tens of per cent even in quiet conditions**, worse in a storm and
worse again in the days after one, when the thermosphere is still recovering and the model's
memory of the storm is a fixed functional form. That number is not a caveat to be waved at;
it is the dominant term in everything Step 3 produces, and it is why the storm scenarios are
reported as *changes* against a quiet baseline rather than as absolute probabilities.

### Driving it correctly is most of the work

The inputs are not the obvious ones, and each of these was a decision:

| Input | What NRLMSIS wants | Why it matters |
| --- | --- | --- |
| `f107` | The **previous day's** observed 10.7 cm flux | The thermosphere responds to the extreme ultraviolet that arrived yesterday, and the model was fitted that way. Using today's value is a quiet few-per-cent error. |
| `f107a` | The **81-day centred** average, centred on the day in question | For a forecast this needs the predicted flux of the following forty days. CelesTrak publishes it, which is why the table carries it. |
| both | The **observed** flux, not the flux adjusted to 1 AU | The atmosphere feels what arrives. The Earth's distance from the Sun varies by 3.4 per cent over a year, so the adjustment is a real 7 per cent swing in the wrong direction. |
| `ap` | A **seven-element vector per sample time** | Daily Ap; the three-hourly ap now and at 3, 6 and 9 hours ago; the average of the eight intervals from 12 to 33 hours ago; the average of the eight from 36 to 57 hours ago. The thermosphere at a given moment remembers two and a half days of heating. |

The ap vector is only read when the model is asked for it — `geomagnetic_activity=-1`, which
`density()` always passes. With the default switch NRLMSIS uses the daily Ap alone and the
storm response is a smooth daily average, which is exactly the wrong thing for an event whose
timing matters to the hour. Building this wrong produces a storm response that looks entirely
plausible and is not, so `ap_vector` is tested against a hand-built case where every element
of the answer is a different number.

A sample whose 57 hours of history the table does not cover comes back **NaN**, not zero. A
quiet zero would turn a missing record into a calm day. Every caller counts them.

## The sanity check the prompt asks for

`driftwatch density`. Quiet-condition density at four altitudes, averaged over 24 local solar
times because the day-night contrast at these heights is a factor of two to six and a single
longitude would be a coin toss.

Against the US Standard Atmosphere 1976, which is a fixed "moderate activity" profile (about
F10.7 = 150), at the same conditions:

| Altitude | driftwatch (F10.7 = 150) | US Std 1976 | ratio | day/night |
| ---: | ---: | ---: | ---: | ---: |
| 300 km | 2.59e-11 | 1.92e-11 | 1.35 | 1.8 |
| 400 km | 4.27e-12 | 2.80e-12 | 1.52 | 2.6 |
| 500 km | 8.74e-13 | 5.22e-13 | 1.68 | 4.2 |
| 600 km | 2.07e-13 | 1.14e-13 | 1.82 | 6.1 |

Within a factor of two everywhere, with the gap growing with altitude, which is the known
behaviour of the 1976 standard atmosphere: it was built on sparse high-altitude data and runs
low above 500 km. The solar-cycle spread is much larger than the disagreement — the same model
gives 7.7e-13 at 400 km at F10.7 = 70 and 9.8e-12 at F10.7 = 220, a factor of thirteen — so
the published value sits comfortably inside the range at every altitude.

On the live conditions of 2 September 2026 (F10.7 = 100.5, 81-day 110.8, Ap 5) the same
command gives 1.30e-11, 1.59e-12, 2.52e-13 and 4.95e-14, which is the low-moderate part of
that range, as it should be at this point in the cycle.

### Against published NRLMSIS values, which is the stronger check

The 1976 comparison above measures the 1976 profile's known bias about as much as it measures
anything of ours. The check that tests **our own plumbing** is against NRLMSIS output somebody
else published at stated drivers, because everything between the space weather table and the
number — the previous day's flux, the 81-day centred average, the seven-element ap vector, the
units, the pymsis call — has to be right to reproduce it, and anything wrong shows up as tens
of per cent rather than as a subtlety.

The reference is NRL's own test output for NRLMSIS 2.1, distributed with the model and shipped
inside pymsis as `tests/msis2.1_test_ref_dp.txt`. Four of its rows in the altitude range this
project cares about, driven end to end through `driftwatch.drag.density` from a space weather
table built to carry those drivers (the file publishes g/cm³; these are ×1000 for kg/m³):

| Row (yyddd) | Altitude | F10.7 prev. day | 81-day | Ap | NRL published | driftwatch | error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 76138 | 349.9 km | 77.4 | 72.4 | 4 | 1.5860e-12 | 1.5859e-12 | −0.005 % |
| 78279 | 379.2 km | 138.7 | 156.5 | 4 | 6.2060e-12 | 6.2063e-12 | +0.005 % |
| 88156 | 434.6 km | 145.2 | 129.9 | 3 | 2.2890e-12 | 2.2847e-12 | −0.187 % |
| 6257 | 500.0 km | 82.9 | 77.6 | 4 | 1.8790e-13 | 1.8793e-13 | +0.015 % |

Better than 0.2 per cent, which is the printing precision of NRL's own file. This is pinned by
a test with the four rows written out in it, so the numbers cannot drift silently.

**Why those four rows and not others.** NRLMSIS has two geomagnetic modes and they are not the
same model. NRL's reference file was produced in the **daily-Ap** mode; `density()` always asks
for the **seven-element storm-time** mode, because that is the one that responds to a storm at
all. The two agree exactly at Ap = 4 — the model's quiet baseline — and diverge as the index
rises, so the rows at Ap ≈ 4 are the ones on which the plumbing can be compared without the
model's own two answers confounding it. Measured at 379 km with a flat ap vector:

| Ap | daily-Ap mode | seven-element mode | difference |
| ---: | ---: | ---: | ---: |
| 4 | 3.7361e-12 | 3.7361e-12 | +0.00 % |
| 15 | 4.2985e-12 | 4.4067e-12 | +2.52 % |
| 40 | 4.9210e-12 | 5.1755e-12 | +5.17 % |
| 80 | 5.5296e-12 | 5.9126e-12 | +6.93 % |
| 150 | 6.6039e-12 | 7.1894e-12 | +8.87 % |

That divergence, growing with the index, is the reason the seven-element vector is built at
all — and this is with a *flat* history. A real storm's history is not flat, and the gap
between "the daily average said 80" and "it was 4 yesterday and 200 three hours ago" is larger
still.

### The storm-to-quiet ratio

A flat Kp applied for the 24 hours before the evaluation as well as at it — a storm switched
on at the instant of evaluation would show almost nothing, because the model's response is
built from that 57-hour history:

| Altitude | G3 (Kp 7, ap 132) | G5 (Kp 9, ap 400) |
| ---: | ---: | ---: |
| 300 km | 1.60 | 2.67 |
| 400 km | 1.84 | 3.69 |
| 500 km | 2.05 | 4.78 |
| 600 km | 2.16 | 5.67 |

The ratio grows with altitude, which is the physics: a storm heats the lower thermosphere,
the atmosphere expands, and the density at a fixed height rises by more the further that
height is above the heating. The G5 numbers are in the range reported for the May 2024 Gannon
storm, where 400 to 500 km densities rose by factors of two to eight. Step 4 tests that
against the storm itself rather than against a recollection of it.

## Along an orbit

`density_along_orbit` propagates one object's element set from a start time to an end time —
normally its own epoch to a time of closest approach — samples the sub-satellite position,
and evaluates the model at each sample.

**The frame.** A GMST-only rotation from TEME to Earth-fixed, not the full IERS transform.
Measured against `teme_to_itrs` on the ISS, ignoring UT1-UTC and polar motion misplaces the
sub-satellite point by 12 m in latitude and 0.9 m in longitude. For a model whose own
uncertainty is tens of per cent that is nothing, and it is the difference between one
vectorised rotation and an astropy frame transform per sample time, of which a run has
millions.

### The step, and why it is what it is

The step trades cost against the two things that make density vary along an orbit: **where**
the satellite is — latitude, and above all local solar time, which swings the density by a
factor of two to six over one revolution — and **how high** it is, which for an eccentric
orbit swings it by orders of magnitude.

The rule (`sample_step_s`):

- one revolution divided by `DENSITY_SAMPLES_PER_ORBIT` = 16, which is 5.6 minutes at low
  Earth orbit and resolves the local-time swing;
- for eccentricity above 0.005, tightened in proportion to the orbit's altitude range
  measured in scale heights (`2ae / 50 km`), because there the drag is concentrated in the
  perigee passage and a step that flies over it integrates the wrong thing;
- clamped into [30 s, 600 s].

**Measured, not asserted.** Mean density over one day against a 10-second reference, for the
median object of each eccentricity band in the catalogue (`driftwatch density --convergence`):

| Object | e | perigee | step | rule error | a fixed 600 s step |
| --- | ---: | ---: | ---: | ---: | ---: |
| STARLINK-3520 | 0.0001 | 470 km | 353 s | −0.03 % | −0.05 % |
| CZ-6A DEB | 0.0070 | 613 km | 187 s | −0.09 % | −0.36 % |
| FENGYUN 1C DEB | 0.0374 | 605 km | 35 s | +0.02 % | +0.65 % |
| DELTA 1 DEB | 0.0811 | 537 km | 30 s | −0.02 % | −0.82 % |
| FREGAT DEB | 0.1521 | 470 km | 30 s | −0.02 % | **−13.5 %** |
| IUS R/B(1) | 0.7215 | 388 km | 30 s | −0.02 % | **−17.0 %** |

The rule holds every case to under a tenth of a per cent. A fixed step would be fine for the
near-circular majority and wrong by more than a tenth for the eccentric tail — which is
exactly the population whose perigee passes through the densest air, so it is the population
where being wrong matters most.

## The ballistic coefficient

`B = C_D A / m`, in m²/kg: the one number that turns a density into a deceleration. The decay
it produces, in general and then for a circular orbit:

```
da/dt = -(B a² / mu) rho |v_rel| (v_rel . v)          ->      da/dt = -B rho sqrt(mu a)
```

`v_rel` is the velocity relative to a **co-rotating** atmosphere. The atmosphere carries a
satellite's ground track along at up to 465 m/s, six per cent of an orbital speed and about
seventeen per cent of its cube, so ignoring it would overestimate the drag on every prograde
orbit and underestimate it on every retrograde one. The general form is what is fitted,
because an eccentric orbit does its drag at perigee where both the density and the speed are
highest and a mean density times `sqrt(mu a)` understates the integral badly.

### Three sources, labelled

**`history`** — fitted from the object's own decay. Read the mean semi-major axis off each
element set of the last 45 days and ask what B makes NRLMSIS reproduce the drop that actually
happened, summed over intervals:

```
B = mu * sum(da_i) / sum(a_i² * integral_i(rho |v_rel| (v_rel . v) dt))
```

A total-decay estimator, so element-set noise averages out over the window instead of being
fitted interval by interval. Three things are excluded rather than fitted around:
**manoeuvre intervals**, found by the same detector the covariance fit uses, because a
station-keeping burn would come back as negative drag; **outlier element sets**, likewise;
and **intervals longer than a fortnight**, where a burn could hide inside a net decay. The
windows carry the **observed** ap of those days, so a storm inside the fit window is modelled
as a storm rather than averaged into a quiet mean.

#### When a fit is accepted

Not on a fixed number of metres, which cannot know whether fifty metres is a measurement or a
wobble. The threshold is the **object's own element-set scatter**.

Excluding the manoeuvre intervals leaves contiguous *runs* of element sets. A quadratic is
fitted through the mean semi-major axis **inside each run** and the pooled root-mean-square
residual is the scatter — what one element set of this object disagrees with its neighbours
by, over this window. A quadratic because a decaying orbit's semi-major axis is curved over
six weeks and a line's residual would count the curvature as noise; inside each run and never
across the gap between two, because a run ends where a burn was excluded and a curve fitted
across the exclusion reads the 2 km burn itself as noise. That last point is not hypothetical:
the first version of this fitted one curve across the whole window, and the burn-exclusion test
caught it refusing a designed fit it had just made possible.

The total-decay estimator telescopes to endpoint differences within a run, so its own
uncertainty is `scatter × sqrt(2 × runs)`, and a fit is accepted only when the measured decay
exceeds that by a factor of three. Quiet elements therefore earn a fit from a smaller decay
than noisy ones. NOAA-20 is the case that shows why: its element sets scatter by 0.16 m, so its
64 m of decay is a 77-sigma measurement, where a fixed 50 m floor would have called it marginal.

Also refused, with the reason recorded: a clean span under 10 days, fewer than six element sets,
a decay under an absolute 20 m floor (below which the difference of two mean semi-major axes is
systematics rather than noise), an answer outside 1e-4 to 1 m²/kg, and — see below — more than a
quarter of the intervals excluded as manoeuvres.

#### An object under continuous control is not measuring drag

Excluding a burn assumes the intervals *around* it are free flight. That fails for an object
that is manoeuvring most of the time, and it fails in a specific way: a **continuous** low
thrust is a ramp rather than a jump, the jump detector cannot see it, and the fit reads it as
atmosphere.

The Starlinks being deorbited are the case. On the demo run several fit at B near 1 m²/kg off
48 km of decay in 45 days at 400 km, which is not an atmosphere and is not an area-to-mass any
satellite has. Grouping the run's 384 history fits by the fraction of intervals excluded as
manoeuvres:

| Excluded fraction | n | median B | max B |
| --- | ---: | ---: | ---: |
| 0–5 % | 103 | 0.045 | 0.798 |
| 5–10 % | 29 | 0.018 | 0.260 |
| 10–15 % | 74 | 0.012 | 0.692 |
| 15–20 % | 89 | 0.013 | 0.321 |
| 20–25 % | 48 | 0.014 | 0.175 |
| 25–35 % | 11 | 0.023 | 0.994 |
| 35–50 % | 15 | 0.260 | 0.883 |
| over 50 % | 15 | 0.183 | 0.759 |

Flat to a quarter, then an order of magnitude. So a fit is refused above a quarter, and the run
comes back with 362 history fits instead of 384.

**The rule is on the exclusions and not on the coefficient**, deliberately: every *debris*
object fitted above 0.5 m²/kg has **no** exclusions at all, and that tail is real (below). A cap
on B would throw the fragments away to catch the satellites.

It is a proxy and it does not catch everything. STARLINK-65196 has 12 per cent of its intervals
excluded and still fits at 0.69 m²/kg off 43 km of decay; it survives the rule and it is
certainly a deorbit. It is left in and named here rather than chased with a tighter threshold
that would start refusing the fragments, and it is a question for the review.

#### Every coefficient carries an uncertainty

So the Step 3 variance term has something to propagate. `b_sigma_m2_kg` on every row:

- **`history`**: the statistical uncertainty of its own decay measurement, `sigma_B/B = 1/snr`,
  floored at 5 %. It is deliberately *not* the density model's uncertainty — that is a separate
  Step 3 term where it partly cancels, and adding it here would double-count it.
- **`bstar`**: a 50 % prior. There is no repeat measurement to take a scatter from, and 50 % is
  the size of the disagreements the table below shows against independent estimates.
- **`typical`**: the robust spread of the pool the median came from (`1.4826 × MAD`), floored at
  a factor of two, because a population median is not a measurement of this object however
  tight the population is.

**`bstar`** — from the element set's own drag term. **B\* is not a physical ballistic
coefficient.** It is a fit parameter for SGP4's own atmosphere model and it absorbs whatever
the fit could not otherwise explain; it is routinely negative (STARLINK-6053 carried −2.98e-5
on 2 September 2026, which as a physical coefficient would mean an object that accelerates as
it flies through air). The textbook conversion `B = 2 B*/rho0` with `rho0 = 2.461e-5`
kg/m²/ER is quoted in `config.SGP4_BSTAR_RHO0` and **deliberately not used**: measured against
the decay SGP4 itself produces, it is wrong by three orders of magnitude, and the implied
reference density is not even constant — the ISS and YAM-3 at 415 to 420 km imply 0.043, and
STARLINK-32515 at 463 km implies 0.0064, a factor of seven apart.

So the fallback asks a self-consistent question instead: **propagate the element set with its
own B\* for ten days, read the drop off SGP4's own mean elements, and invert it through
NRLMSIS**. No conversion constant, altitude-aware, and it inherits exactly as much noise as
B\* has — which is the point of the label. (SGP4's mean semi-major axis, `satrec.am`, not an
osculating one: an osculating value carries a short-period oscillation of kilometres and a
long-period one that over ten days looks exactly like a trend, either of which swamps the
tens or hundreds of metres a week of drag removes.)

**`typical`** — the run's own median. Where neither route works, the object takes the median
of the coefficients this run actually fitted, for its own **category and drag altitude band**,
falling back to the category alone and then to everything fitted, with the label saying which.
The bands are `config.BALLISTIC_ALTITUDE_BAND_EDGES_KM` — 350, 450, 550, 650, 800, 1200 km —
and they are drag bands, not the screener's: what one object's coefficient has in common with
another's is the density regime its decay was measured in, and the screener's `leo` spans three
orders of magnitude of density. `leo` is one band there and six here. Sentinel-1A forced this: at 693 km its decay over 45 days is 25 m, inside the
element-set scatter, so there is nothing to fit; before the B\* route was made altitude-aware
its B\* implied 3.3 m²/kg, which is not a satellite. The alternative was B = 0, which asserts
that a storm does nothing to it — nearly true at 800 km, plainly false at 500, and the wrong
kind of wrong for a risk model.

### What it gives on real objects

| Object | Altitude | source | B (m²/kg) | Independent estimate |
| --- | ---: | --- | ---: | --- |
| ISS | 420 km | history, 136 sets, 1 burn excluded | 0.0087 | ~0.0075 from a published ballistic coefficient of 125 to 150 kg/m² |
| YAM-3 | 415 km | history, 123 sets | 0.0121 | ~0.02 for a 100 kg microsatellite |
| STARLINK-32515 | 463 km | history, 105 sets, 7 burns excluded | 0.0059 | ~0.0055 for an 800 kg v2 mini |
| Sentinel-1A | 691 km | bstar | 0.0235 | ~0.029 for 2,300 kg and ~30 m² |
| NOAA-20 | 824 km | bstar | 0.0293 | ~0.017 for 2,540 kg and ~20 m² |
| STARLINK-6053 | 570 km | typical | 0.0100 | its B\* is negative, so nothing physical can be read from it |

Every one within a factor of two of an independent estimate, and the three fitted from
history within about fifteen per cent. That is better than this method has any right to be
and should not be read as a general accuracy claim: these are large, well-tracked objects
with dense element-set histories.

### What it gives on a population

150 objects of the demo run (the fleet, then by catalogue number, so the sample is
old low-perigee debris and the fleet rather than a random draw): **125 fitted from history,
22 from B\*, 3 typical**, in seven minutes.

| Category | n | median B | interquartile range |
| --- | ---: | ---: | --- |
| station | 1 | 0.0087 | — |
| rocket_body | 22 | 0.0142 | 0.0078 to 0.0268 |
| payload | 38 | 0.0248 | 0.0188 to 0.0363 |
| debris | 89 | 0.110 | 0.091 to 0.261 |

The ordering is the physical one and nothing enforced it: a space station is dense, a spent
stage is a heavy empty tube, a payload is somewhere between, and debris is light. The
separation is a factor of thirteen from the station to the debris median.

**The debris tail is high and it is probably real.** The largest coefficients, 0.44 to 0.61
m²/kg, are Cosmos 1275, Cosmos 249 and Cosmos 252 fragments at 750 to 850 km with radar cross
sections of 0.01 to 0.08 m². Taking `C_D` = 2.2 that is an area-to-mass of about 0.27 m²/kg,
which for a 25 cm object means a mass near 150 g — a thin plate or a sheet of multi-layer
insulation, which is what those clouds are known to consist of. The decay is not marginal
either: 750 m over 45 days at 800 km, where the model gives 6.6e-15 kg/m³, needs a
coefficient near 0.6 and cannot be produced by a small one. The caveat is that these are also
the objects where the model is least certain (helium and hydrogen dominate the atmosphere
there) and where solar radiation pressure is a comparable force, so read the tail as "light
fragments, coefficient uncertain by a factor rather than a per cent".

## What it costs, and what is done about it

A history fit is one density evaluation per element-set interval, about a hundred an object.
The demo run has 2,993 objects appearing in events. Fitting them all at the full sampling step
would take hours, so the Step 2 review set four rules and they are all measured rather than
asserted.

### Profiled first

Eight objects, 949 element sets, 814 fitted intervals: 20.3 s unprofiled, 2.53 s an object.
Under cProfile (26.0 s total, so read the shares rather than the absolutes):

| | tottime | share |
| --- | ---: | ---: |
| `pymsis.calculate` (the Fortran model itself) | 12.76 s | 49 % |
| rebuilding the weather grid, once per interval | 3.97 s | 15 % |
| propagating the orbit track | 3.92 s | 15 % |
| everything else | ~5 s | 20 % |

So density evaluation does dominate, and it is dominated in turn by the number of samples. The
second line is not density evaluation at all: it was pandas re-parsing the same unchanged
weather table a hundred times an object. That is now `density.WeatherGrid`, built once per run
and passed down — no approximation, just not doing the same work repeatedly.

### A coarser grid, for the fit alone

The fit only ever uses the *integral* of the density over an interval, so the local-time
structure the scenario step resolves is being averaged away immediately. Multiplying the
per-object step rule by a factor, on the same eight objects:

| Step | Time per object | Worst |ΔB| against the rule step |
| --- | ---: | ---: |
| ×1 (the rule) | 2.53 s | — |
| ×2 | 1.75 s | 0.02 % |
| **×4** | **1.18 s** | **0.65 %** |
| ×8 | 0.97 s | 1.44 % |

And the same factor applied to the B\* inversion, which is a single ten-day track rather than a
sum over a hundred intervals and is correspondingly more sensitive (40 objects):

| Step | Time per object | Median |ΔB| | Worst |ΔB| |
| --- | ---: | ---: | ---: |
| ×1 | 142 ms | — | — |
| ×2 | 75 ms | 0.04 % | 0.20 % |
| **×4** | **41 ms** | **0.67 %** | **3.88 %** |
| ×8 | 21 ms | 2.85 % | 24.1 % |

×4 is the default for both. It costs the history fit 0.65 % against a coefficient whose own
statistical uncertainty is 5 %, and the B\* inversion 3.9 % against one carrying a 50 % prior.
×8 is where the B\* inversion falls apart, which is why the choice is measured and not guessed.

### Only the objects that appear in events, worst first

`driftwatch ballistic` fits the objects that take part in a stored event — nothing else needs a
coefficient, because nothing else has a conjunction to score — ordered by the highest
probability they appear in under the run's first scored scenario, falling back to closest
approach when nothing has been scored yet. `--all` covers every object of the run.

### A wall-clock budget

`--budget-s`, four minutes by default, bounds the **history fits**. What it does not reach
falls through to the B\* inversion and then to the typical value, labelled exactly as any other
fallback, so nothing downstream has to know a budget existed. The ordering is what makes this
sound: the allowance is spent from the top of the probability list down.

### And a persistent cache, which is what makes it converge

`data/ballistic/coefficients.parquet`, keyed by NORAD id, holding each fit **with the span of
history it used**. A cached fit is reused unless the object's history has grown by more than a
week, the fit is over 30 days old, or it was made under a different NRLMSIS version or a
different set of acceptance rules (`config.BALLISTIC_RULES_VERSION` — without it, a change to
what counts as a good enough decay would reach new objects and silently leave the cached ones
alone). Rejections are cached too: finding out that an object's decay is inside its own scatter
costs the same hundred evaluations, and the answer is just as stable.

The effect is that **coverage deepens run over run** rather than the same objects being refitted:

| Run | From cache | Newly fitted | Over budget | Objects with a fitted coefficient |
| --- | ---: | ---: | ---: | ---: |
| first | 0 | 608 | 2,367 | 362 |
| second | 608 | 453 | 1,914 | 670 |

Both took under seven minutes wall clock for 2,993 objects.

## What it gives on the full run

2,993 objects of the demo run, after two passes: **670 fitted from history, 1,620 from B\*, 703
typical**. Median B by source and category (m²/kg):

| Category | history | bstar | typical |
| --- | ---: | ---: | ---: |
| station | 0.0088 | — | — |
| starlink | 0.0129 | 0.164 | 0.0127 |
| rocket_body | 0.0204 | 0.0228 | 0.0204 |
| payload | 0.0264 | 0.0312 | 0.0264 |
| unknown | 0.0382 | 0.148 | 0.0382 |
| constellation | 0.0599 | 0.0524 | 0.0685 |
| debris | 0.327 | 0.197 | 0.442 |

The `history` column is the one to read; the ordering across it is the physical one, station to
debris, and nothing enforces it. The `bstar` column runs consistently higher for the
constellations, which is what B\* being a fit parameter that absorbs unmodelled thrust looks
like on a population that manoeuvres.

## The bias that folds in, and the part of it that cancels

Only the **product** `B rho` is observable from a decay. If NRLMSIS is systematically low by
twenty per cent over the fit window, the fit returns a B twenty per cent high, and when the
same model then drives the scenarios the product comes back right. **The quiet-case bias
cancels.**

What does not cancel is the storm *response*. A model that gets the quiet density wrong by a
constant factor but the storm ratio right gives the right answer here; a model whose ratio is
wrong is not corrected by anything in this chain, because there is no quiet baseline to
divide it out against. This is the reason the fitted coefficient is preferred over B\*, and
the reason the same model must drive both the fit and the scenarios — mixing them would break
the cancellation and add a bias nobody could see.

It also means the fitted B is **not** a measurement of the object's area over its mass. It is
a measurement of that divided by whatever NRLMSIS's bias is over the fit window, and it should
be read as one.

## What this does not do

- **No thermospheric winds.** The atmosphere is taken to co-rotate exactly. Real winds reach
  several hundred metres a second in the auroral zones during a storm, which is a few per cent
  of the relative speed and more in the places a storm matters most.
- **No lift, no attitude.** `C_D A` is one number per object, constant in time. A satellite
  that changes attitude — a Starlink turning its panel edge-on to ride out a storm, which is a
  documented operational response — changes its ballistic coefficient by a factor of several
  and nothing here sees it.
- **No radiation pressure.** For a light object on a high, eccentric orbit, solar radiation
  pressure is comparable to drag near apogee, and the fit will read some of it as drag.
- **NRLMSIS's own limits.** It is an empirical climatology: it has no knowledge of a
  particular storm's geometry, and its ap parameterisation cannot distinguish two storms with
  the same index and different energy deposition. It is also fitted to a period that did not
  include the May 2024 event.
- **The coefficient is fitted once per run** and held constant across the screening window. A
  seven-day window is short enough that this is the least of the approximations above.
