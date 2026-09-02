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

Refused, with the reason recorded, when the clean span is under 10 days, when fewer than six
element sets survive, when the total drop is under 50 m (inside the element-set scatter), or
when the answer lands outside 1e-4 to 1 m²/kg.

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
of the coefficients this run actually fitted, for its own category where there are at least
five of them. Sentinel-1A forced this: at 693 km its decay over 45 days is 25 m, inside the
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
