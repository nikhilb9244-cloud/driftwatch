# Conjunction screening and collision probability

How `driftwatch screen` finds close approaches between a fleet and the catalogue, why
the coarse time step cannot miss one, and what the output means (the first half of this
page, Step 2 of Phase 2); then how an uncertainty is put on every position, how the
probability of collision is computed on the encounter plane, what the maximum
probability and the flags mean, and how the probability layer is kept separate from
the geometry so that a scenario can be rescored without rescreening (the second half,
Step 3); then what the weekly report and the viewer's conjunctions panel show, and why
they collapse repeated encounters (Step 4).

## The problem

A fleet of `P` primaries against a catalogue of `N` objects is `P x N` pairs over a
seven-day window. For the demo fleet that is 6 x 32,361 pairs. Checking every pair at
every second would be 6 x 32,361 x 604,800 = 1.2 x 10^11 propagations, weeks of
computing. The three-stage scheme of Hoots, Crawford and Roehrich (1984) throws pairs
away as cheaply as possible, in the order geometry, then coarse time, then fine time,
and gets the demo fleet done in a few minutes.

Everything is computed in TEME from the snapshot's mean elements with SGP4. The
positions are only as good as the element sets (hundreds of metres to kilometres; see
`docs/tle-and-sgp4.md`), so a miss distance here is the miss distance of two SGP4
trajectories, not of two spacecraft. The second half of this page puts numbers on that.

## Stage A: apogee and perigee overlap

Two orbits cannot come within `D` km of each other unless their altitude shells overlap
to within `D`. With perigee `q` and apogee `Q` for each object, the test is

```
max(q_primary, q_secondary) - min(Q_primary, Q_secondary) <= D
```

The pad `D` (default 50 km) covers three things: the mean-element apogee and perigee
from the sgp4 library are Brouwer mean values that differ from the osculating orbit by
several kilometres; drag lowers an orbit by up to a few kilometres over a week (much
more for an object about to decay, and more in a storm); and the screening volume
itself extends 35 km from the primary (below). Objects with a mean perigee below 120 km
are dropped and listed as decaying: SGP4 is unreliable that low and the object will be
gone within days. Element sets older than five days at the window start are kept but
flagged stale on every event they take part in. A fleet member that is missing from the
snapshot or below the decay cut stops the run with an error; silently screening five
primaries when six were asked for would be worse.

Stage A reads `perigee_km`, `apogee_km`, `semi_major_axis_km` and `epoch` and nothing
else. The `category` and `altitude_band` labels are not consulted: an `unknown` analyst
object or an `other` orbit that dips through LEO is screened like everything else. A
test permutes both labels across the catalogue, and relabels everything `unknown` /
`other`, and asserts the same survivors.

On the 2026-09-01 snapshot Stage A keeps 47,922 pairs (from 194,166) over a union of
22,627 distinct secondaries, because the demo fleet's altitudes (420 to 820 km) span the
most crowded part of LEO.

## Stage B: coarse time stepping, and why it cannot miss

Every surviving pair's separation is sampled on a common time grid: all objects are
propagated together with `SatrecArray`, and for each primary the distance to each of its
secondaries is taken at every sample. A pair becomes a candidate when it is closer than
a threshold `T`. The step `h` and the threshold `T` have to be chosen together.

### The bound

Let `d(t) = |r_s(t) - r_p(t)|` be the separation. Its rate of change is

```
d'(t) = (dr . dv) / |dr|,     so     |d'(t)| <= |dv| = |v_s - v_p| <= |v_s| + |v_p|.
```

The separation cannot change faster than the relative speed, and the relative speed
cannot exceed the sum of the two speeds. Each object is fastest at perigee, where the
two-body (vis-viva) speed from its mean elements is

```
v_perigee = sqrt(mu (2 / r_perigee - 1 / a)).
```

So for a pair, `v_bound = m (v_perigee,p + v_perigee,s)` bounds `|d'(t)|` at every
instant, with a margin `m = 1.02` because SGP4 trajectories are not exactly Keplerian
and the osculating speed can exceed the two-body value by a fraction of a percent.

Now suppose the separation has a minimum `d(t*) <= R` inside the window, where `R` is the
screening radius. The nearest sample `t_k` is at most `h / 2` away, and

```
d(t_k) <= d(t*) + v_bound h / 2 <= R + v_bound h / 2 = T.
```

So with `T = R + v_bound h / 2`, every minimum inside `R` has at least one sample under
the threshold, whatever the step. The step only decides how many false candidates Stage
C has to refine, not whether a true one can be lost. The bound holds for any function
with a bounded derivative; it does not assume the encounter is short, straight, or fast.

### The numbers

For two circular orbits at 400 km, `v_perigee` is 7.67 km/s each, so `v_bound` is
15.6 km/s with the margin; the prompt's "about 15 km/s" is this figure. The bound is
larger for eccentric secondaries that dip through LEO: a transfer-orbit rocket body with
a 200 km perigee and a 36,000 km apogee moves at 10.2 km/s at perigee, so its pairs
get a bound near 18.3 km/s and a correspondingly larger threshold. That is why the
threshold is per pair rather than one number.

The screening radius `R` is the sphere that encloses the whole screening volume: the
larger of the 25 km watch radius and the half-diagonal of the 2 x 25 x 25 km box, which is
`sqrt(2^2 + 25^2 + 25^2) = 35.4` km. A miss can sit in a corner of the box and outside
the watch sphere, so the box's corner sets `R`.

| Step `h` | Threshold `T` for a typical LEO pair | Samples in 7 days | Propagations (22,629 objects) |
| --- | --- | --- | --- |
| 20 s | 35.4 + 15.6 x 10 = 191 km | 30,242 | 6.8 x 10^8 |
| 30 s (default) | 35.4 + 15.6 x 15 = 269 km | 20,162 | 4.6 x 10^8 |
| 60 s | 35.4 + 15.6 x 30 = 503 km | 10,082 | 2.3 x 10^8 |
| 120 s | 35.4 + 15.6 x 60 = 971 km | 5,042 | 1.1 x 10^8 |

The vectorised SGP4 path runs at about 0.22 microseconds per propagation on the
development laptop, so Stage B's propagation cost at 30 s is under two minutes and the
default sits where the Stage B cost and the Stage C candidate count are both comfortable.
The step is a command-line option; the threshold follows from it automatically. The
sample grid is padded by one step on either side of the window so that a minimum right
at the window's edge still has neighbours on both sides.

### From samples to brackets

A candidate is handed to Stage C as a bracket in time. The range rate
`f(t) = dr . dv` is negative while the objects approach and positive while they
recede, so a minimum of `d` is a zero of `f` crossing from negative to non-negative. The
primary bracket rule is: consecutive samples `t_k, t_(k+1)` with `f(t_k) < 0 <= f(t_(k+1))`
and at least one of `d(t_k), d(t_(k+1))` under the threshold. The bound above says the
nearest sample to `t*` is under the threshold, and it is one of these two, so the rule
is complete whenever the sign of `f` at the two samples straddles the minimum.

That can fail only if `f` changes sign twice inside one step, which means a local
maximum and a local minimum of `d` within `h` of each other: the relative velocity would
have to reverse along the line of sight twice in 30 s. Near a close approach the
separation is convex (`d'' ~ |dv|^2 / d`), so this needs a very small relative speed,
metres per second, the co-orbital case. For those pairs the sampled distance is within
`|dv| h / 2`, metres, of the true minimum anyway. The fallback rule covers it: a sampled
local minimum under the threshold with no sign change on either side is also a
candidate, with the two-step bracket `[t_(k-1), t_(k+1)]`, and Stage C minimises the
separation directly rather than root-finding.

### The proof by brute force

`tests/test_screening.py` builds a synthetic catalogue: an ISS-like primary, eight
secondaries constructed to pass it at random times and distances (0.1 to 30 km, crossing
angles 5 to 175 degrees) and forty random LEO orbits. Brute force samples every Stage A
survivor at one-second intervals over a day and refines every local minimum of the
separation with a scalar golden section. The test asserts that every brute-force
minimum inside `R` falls inside a Stage B bracket, at the default 30 s step and at 120 s,
and that Stage C reproduces each one inside the watch radius to 10 ms and 1 m. The
negative control sets the threshold to `R` alone, without the `v_bound h / 2` term, at a
120 s step, and shows that fast crossings are then lost.

## Stage C: refinement

For each bracket the time of closest approach is the root of `f(t) = dr . dv` with SGP4
evaluated at every trial time (each primary with `sgp4_array` over all its candidates,
each secondary with a scalar call). The root finder is regula falsi with the Illinois
modification and Dekker's bisection safeguard, vectorised over all candidates, stopping
when the bracket is narrower than 10 microseconds or when `|f| <= tol |dv|^2`, which is
the same thing expressed through the local slope. It takes about eight to twelve
evaluations per candidate against the twenty-two that bisection would need. Fallback
candidates are minimised by golden section to a millisecond.

At the root the geometry is read off: the miss distance `|dr|`, the relative speed
`|dv|`, and the miss vector in the primary's RIC frame (see `driftwatch.screening.ric`;
radial along the primary's position, cross-track along its angular momentum, in-track
completing the right-handed set). An event is kept when the miss vector lies in the box
(`|R| <= 2`, `|I| <= 25`, `|C| <= 25` km) or the miss distance is inside the 25 km watch
radius; both flags are recorded because either can hold without the other. Two
candidates that converge on the same minimum (a sign change beside a sampled minimum, or
two sign changes around a shallow root) are merged when their times agree to the second.

The precision test constructs two orbits that pass at a chosen time and distance. The
secondary's osculating state at the encounter is set by hand (the primary's position
plus the miss vector, the primary's velocity rotated about the radial axis by the
crossing angle), then converted to SGP4 mean elements by fixed-point iteration, which
converges to under a millimetre. Stage C recovers the designed time to about a
millisecond and the designed miss and its RIC components to under a metre, across
crossing angles from 10 to 170 degrees and misses from 0.5 to 24 km.

## Starlink secondaries: supplemental element sets

A standard element set is fitted to past tracking, so it cannot know about a manoeuvre
planned for tomorrow. Starlink satellites manoeuvre constantly, and SpaceX publishes its
own ephemerides, which include planned burns; CelesTrak fits SGP4 element sets to those
(its supplemental GP data) so ordinary tooling can use them. `driftwatch screen` fetches
the Starlink file under the same two-hour cache rule as the GP groups, matches it to the
snapshot by NORAD id, and substitutes the elements before Stage A, recomputing apogee and
perigee from the new set. Records for satellites not yet in the public catalogue carry
placeholder ids above 100,000 and are skipped; a supplemental set more than a day older
than the GP set is treated as abandoned and the GP set is kept. Every event records
which set the secondary carried (`secondary_ephemeris`).

The supplemental sets are better, not true. CelesTrak's published fit residuals
(the ``RMS`` field of every supplemental record: a median of 0.20 km, a 90th percentile of 0.27 km and a worst case of 10.8 km when read on 2026-09-02) are the floor on their
error, and the ephemerides are predictions that SpaceX revises. Manoeuvres by anything
else are not modelled at all; the `manoeuvre_*` columns say, for each side of a pair,
whether the object is known to manoeuvre, might, or has been seen to (the three-valued
flag described under "Manoeuvres" below), so a reader knows which predictions can be
overtaken by events.

## Output of the geometry: the events table

Stages A to C write `events.parquet` in the run directory
`data/conjunctions/<fleet>_<start stamp>/`, one row per event, with the columns listed
in `docs/data-schema.md`: a stable event id, the identity of both objects, the time of
closest approach to the microsecond, the miss distance, the relative speed, the RIC
components of the miss vector, the two volume flags, the stale and manoeuvre flags, the
secondary's ephemeris source, the refinement method, and both objects' TEME position
and velocity at the time of closest approach. The states are what lets everything
below run without touching SGP4 again.

## Uncertainty: what the catalogue does not say

A public element set comes with no covariance. The only handle on its accuracy that
needs nothing but the catalogue is consistency: an object with several element sets
can have an older set propagated to a newer set's epoch and the two compared. The
difference, taken in the newer set's radial, in-track, cross-track frame, is how much
two fits of the same orbit disagree after a given propagation time. Do that for every
pair of sets between half a day and seven days apart and the scatter, as a function of
the propagation time, is a model of how fast the position error grows.

**Why that is a floor, not a measure.** Both sets are fits by the same tracking
network with the same force model, so they share whatever error the network and the
model have in common: a biased drag model during a geomagnetic storm, a sparse tracking
geometry, a systematic in the sensors. The difference between two such fits cannot see
any of it. Consistency measures the part of the error that changes from fit to fit;
the true error is at least that large and, in a storm, much larger. Every probability
on this page is therefore indicative, not operational, and the maximum-probability
sweep below is the honest way to read it.

**One contribution to the floor is SGP4 itself.** A set fitted at a later epoch with the
same `B*` does not propagate drag exactly as the original set did: the theory's drag
terms are polynomials in time from the epoch, so re-basing the epoch changes them.
Measured on a 500 km orbit with `B* = 1e-4`, the re-initialised set drifts in-track by
about 0.07 km per day; with `B* = 0` the inversion is exact to the metre. That is well
below the kilometre-a-day errors of real element sets, but it is in the residuals, and
a test keeps its drag-free case drag-free for that reason.

## The empirical fit

For each object with history, `risk/covariance.py` propagates every element set to
every other set's epoch in one vectorised call, keeps the pairs `(older, newer)` whose
propagation time `dt` lies in `[0.5, 7]` days, and takes the difference of the older
set's propagated position from the newer set's own position in the newer set's RIC
frame. Pairs that span a detected manoeuvre, or involve an element set judged to be an
outlier (next section), are dropped. An object with many sets a day is subsampled to
600 pairs so it does not dominate its pool.

The model for each RIC component is a power law in the propagation time,

```
sigma_k(dt) = s_k dt^p_k,     dt in days,  s_k in km at one day,  k in {R, I, C}.
```

Two parameters per component keep the fit stable on thin history and cover the shapes
that matter: a period error (a wrong mean motion) puts an in-track error that grows
linearly, `p = 1`; a timing error (a wrong mean anomaly) is a constant offset, `p = 0`;
drag errors accumulate faster than linearly. The parameters come from maximum
likelihood for zero-mean Gaussian residuals: at fixed `p` the best `s` is
`s^2 = sum(d^2 / dt^(2p)) / N`, and the profile likelihood over `p` is evaluated on a
grid from 0 to 2.5 in steps of 0.05. The sufficient statistics (`sum d^2 / dt^(2p)` on
the grid, `sum log dt`, `N`) add across objects, which is how the pools are formed. A
test feeds designed residuals through this and recovers the exponents to 0.1 and the
scales to 15 %; another builds element-set histories through SGP4 with a period error
and a timing error and recovers `p = 1` and `p = 0`.

An object gets its own fit when it has at least 5 element sets and 10 usable pairs
whose propagation times span at least a factor of 3 (`empirical`). Otherwise it takes
the pool for its (category, altitude band): the component-wise median of the fits of
the pool's fitted members when there are at least 5 of them, so that a typical member
is represented and one satellite whose residuals are enormous (a manoeuvring object the
detector did not catch) cannot dominate; with fewer fitted members, a fit of the same
form to the pool's residuals added together, when they hold at least 30 pairs
(`pooled:<category>/<band>`). The first run showed why the median is needed: the summed
residuals of the Starlink pool gave 48 km at one day, the rocket-body pool 37 km, both
set by a handful of objects. An object whose pool is empty too falls to a default per
band (`default:<band>`), taken
from published assessments of TLE accuracy (Flohrer, Krag and Klinkrad 2008; Vallado
and Cefola 2012): in LEO a few hundred metres at epoch, in-track dominant, growing by
about a kilometre a day. Every covariance the pipeline uses carries its label, and the
objects table and the export record it per object and per event.

The covariance is diagonal in the object's own RIC frame, with the standard deviations
floored at half a day of propagation time (the fit does not extrapolate below the
shortest pairs). It is a full 3 x 3 matrix in the interface, because Phase 3's storm
model will add an in-track term and the interface should not change when it does.

### Objects screened on an operator ephemeris

A Starlink secondary is screened on CelesTrak's supplemental set, a fit to SpaceX's
published ephemeris, not on its GP element sets. Its GP history is then the wrong thing
to measure: it records how far the satellite moved from where the tracking-based fits
said it would go, which is mostly its own station keeping. On the first live run that
came out at about 10 km a day in-track for the median Starlink satellite, against a few
hundred metres a day for debris, and it was the manoeuvring being measured, not the
tracking.

So an object whose geometry comes from a supplemental set gets its covariance from the
consistency of *successive supplemental versions* instead. Every fetch is stored under
`data/supplemental/<name>_<stamp>.parquet`, and the fit takes the same form as before:
propagate an older published set to a newer one's epoch, difference in RIC, and fit a
power law to the scatter. Two differences from the GP fit:

- **Pairs that span a detected burn are kept.** A supplemental set is fitted to an
  ephemeris that already contains the planned manoeuvres, so the difference between two
  versions is a revision of the plan, which is exactly the error being measured.
- **The window starts much lower.** CelesTrak republishes several times a day, so the
  pairs are hours to days apart rather than half a day to seven days. No object has
  enough versions of its own yet, so the residuals are pooled across every supplemental
  object; because their publication gaps differ, the pool still spans a range of
  propagation times and the exponent can be fitted. When it does not span a factor of
  three the exponent is fixed at one and only the scale is fitted, and the label says so.

Under the fitted growth sits a floor: CelesTrak publishes the RMS of each fit to the
operator's ephemeris in the supplemental file itself (a median of 0.20 km, a 90th
percentile of 0.27 km and a worst case of 10.8 km when read on 2026-09-02). That
disagreement between the element set and the trajectory it was fitted to is invisible to
any comparison between versions, so it is added in quadrature, split across the RIC
components in the proportions of the fitted growth. The sources are labelled
`supplemental:consistency` (or `supplemental:consistency-p1` when the exponent was
fixed) and `supplemental:rms` when there is only one stored version and the floor is all
there is.

The floor alone is a lower bound and is treated as one: an event scored on it lands in
the robust region below, where the maximum-probability sweep shows what a larger
uncertainty would give.

**History for the fit.** `driftwatch screen` backfills 45 days of `gp_history` before
the window start for every fleet member and every Stage A survivor, batched into as
many NORAD ids as fit a 3,500-character request URL (about 450; Space-Track's front end
refuses URLs much beyond 4 KB with a bare 403, measured 2026-09-02, and the Step 0
review's 8,000 was cut to fit), asking only for the element-set fields, and skipping
every id and day a cached request already covers. A
consolidated index, `data/history/index.parquet`, records which history file holds each
(NORAD id, epoch) so that a lookup opens only the files it needs. The fit takes every
element set in the history store for those objects, the snapshots included.

The backfill is a one-off. Every later run asks only for the days after each object's
newest stored element set: the index gives that date per object, ids that share one are
batched into the same request, and an object whose newest set is already past the window
end is not requested at all. A daily run of the same fleet therefore costs one day of
history rather than forty-five, and an object that joins the fleet later still gets the
whole window. The day of the newest set is asked for again rather than skipped, because
more sets can be published later on the same day; the cached-request chain drops it when
a previous request already covered it.

## Manoeuvres: known, possible, observed, none

SGP4 cannot predict a burn, and an element set fitted before one is wrong afterwards by
the size of the burn. What the pipeline can say is, for every object, how likely a burn
is and whether the history shows one. Decided at the Step 2 review, the flag has three
prior values and one the history can promote to:

- `known`: operated constellations and crewed stations (the `starlink`, `oneweb`,
  `constellation` and `station` categories) and fleet members whose file says so;
- `possible`: every other payload in CelesTrak's `active` group (an operational
  satellite that may or may not carry propulsion);
- `none`: debris and rocket bodies, payloads outside the active group, and fleet
  members whose file says `manoeuvres: false`;
- `observed`: a `possible` object whose element-set history shows a jump in
  semi-major axis that drag cannot explain; the dates are recorded in the objects
  table.

**The detector.** Between consecutive element sets `k` and `k + 1` the osculating
semi-major axis should change only by drag, and SGP4 has its own model of that. Set `k`
is propagated to the epoch of set `k + 1` twice, once with its `B*` and once with `B*`
zeroed; the difference is the drag-driven change SGP4 expects. The osculating
semi-major axis of set `k + 1` at its own epoch, minus that of set `k` propagated with
drag to the same instant, is the change the model did not predict. Because both are
evaluated at the same time within kilometres of each other, the short-period J2 terms
(about 8 km peak to peak in LEO) cancel to metres. A raise beyond a floor of 100 m and
half the modelled drag change is a burn: drag cannot raise an orbit. A lowering counts
only beyond the floor and twice the modelled drag change, because an underestimated
`B*` or a storm can double or treble the decay and Phase 3 needs exactly those
intervals kept. A jump that the next interval reverses is one bad element set, not two
burns; that set is dropped from the fit and neither interval counts. Gaps longer than
ten days are not compared. A test raises a synthetic orbit by 1 km mid-history and
recovers the burn's epoch and size; another plants a single outlier set and gets no
burn and one bad set.

Calibrated on the demo run's 45 days of history (2026-07-19 to 2026-09-01): the
unexplained change in semi-major axis between consecutive sets scatters by about 1 m
(median absolute deviation) for debris, rocket bodies and payloads, so the 100 m floor
sits far above the fit noise. 1.8 % of debris and 4.8 % of rocket bodies still show at
least one jump (the heavier tails, and objects whose drag model is poorest), against
14 % of payloads, 43 % of the other constellations and 89 % of Starlink satellites,
which average 13 jumps in 45 days, one every three and a half days of station keeping.
A robust rule (five median absolute deviations about the median) was tried on the same
sample and changed the debris rate by a fraction of a percent while halving the Starlink
count; the simpler rule stays.

**The intervals a burn spans do not reach the covariance fit.** Every pair of element
sets whose propagation window contains a detected jump is dropped before the residuals
are formed, along with every pair involving an element set the detector judged an
outlier. Measured on four heavily manoeuvring Starlink satellites from the first live
run, between 19 % and 75 % of the pairs inside the fit window were discarded for that
reason. The check is in `analyse_object`, and `exclude_jumps=False` exists only for the
supplemental fit above, where a jump is the quantity being measured rather than a
contaminant.

## The encounter plane

Near the time of closest approach the relative motion of two objects in LEO is a
straight line at constant velocity: the encounter lasts a fraction of a second and
gravity bends the relative path by micrometres. The combined position uncertainty,
each object's RIC covariance rotated into TEME with the object's own frame at the time
of closest approach and the two added, is projected onto the plane perpendicular to the
relative velocity. In that plane the miss vector is a point and the two objects touch
when the relative position falls inside a disc of the combined hard-body radius. The
probability of collision is the mass of the projected two-dimensional Gaussian inside
that disc.

The combined hard-body radius is the primary's radius from the fleet file plus the
secondary's. Secondaries carry a category default: 30 m for a station, 10 m for a
Starlink (V1.5 spans about 11 m, V2 Mini about 30 m with both arrays), 3 m for OneWeb,
the other constellations and payloads, 5 m for a rocket body, 0.5 m for debris, 1 m for
an untyped object. For payloads, rocket bodies, debris and untyped objects a published
radar cross-section replaces the default with the equivalent sphere, `sqrt(RCS / pi)`,
clipped to 0.1 to 20 m; the constellations and stations keep their envelope because a
radar return understates a body much larger than the wavelength. The objects table
records which rule produced each radius.

## Probability of collision, three ways

The same integral is evaluated by three methods in `risk/pc.py`; the export carries all
three so the reader can see where they agree.

- **Foster (`pc`).** Foster and Estes' numerical integration on a polar grid over the
  disc: Gauss-Legendre in radius, a uniform grid in angle (spectrally accurate for a
  periodic integrand). At least 24 radial and 72 angular nodes, more when the disc is
  large against the smaller standard deviation. This is the value the flags use.
- **Alfano (`pc_alfano`).** The disc integral reduced to one dimension along a
  principal axis of the covariance, the other dimension in closed form with error
  functions; with the substitution `x = R sin(phi)` the integrand is smooth and a few
  dozen nodes give ten digits. The prompt's cross-check: it must agree with Foster
  within one percent, and a test asserts that over aspect ratios up to 100, misses up
  to six sigma and discs up to twice the smaller sigma (they agree to about 1e-8).
- **Chan (`pc_chan`).** Chan's analytical series after replacing the ellipse of equal
  probability by a circle of equal area. Exact for an isotropic covariance and within
  one percent when the disc is under a tenth of the smaller standard deviation; it
  drifts by tens of percent when the disc is comparable to it, which a test records
  rather than hides. It is a third value, not a check that has to pass.

Two closed forms anchor all three. Zero miss with an isotropic sigma gives
`1 - exp(-R^2 / 2 sigma^2)`; a miss `d` with an isotropic sigma gives the non-central
chi-square with two degrees of freedom, `P(chi^2_2(d^2 / sigma^2) <= R^2 / sigma^2)`.
Anisotropic cases are checked against brute-force two-dimensional quadrature.

## The maximum probability and dilution

For a fixed miss the probability is not monotonic in the uncertainty. Shrink the
covariance and the Gaussian pulls away from the disc; inflate it and the mass spreads
thin; the maximum lies where the standard deviation is of the order of the miss
distance. For a small disc and an isotropic sigma_0 the probability at a scale factor
`k` on the covariance is about `(R^2 / 2 k sigma_0^2) exp(-d^2 / 2 k sigma_0^2)`, with
its maximum at `k* = d^2 / (2 sigma_0^2)`, and a test recovers that.

`pc_max` is the largest probability over scale factors from 0.1 to 10 on the combined
covariance (61 log-spaced steps, the maximum refined by a parabola through its
neighbours), and `pc_max_scale` the factor at which it occurs. Because the empirical
covariance is a floor on the true error, `pc_max` is the honest upper bound: a
`pc_max_scale` above one says the real risk could be higher than `pc` if the fits are
more consistent than they are accurate, which is the usual case; a scale below one says
the uncertainty already dilutes the probability and a better orbit would raise it.
This is Alfano's dilution, and it is what the Phase 3 storm term will move.

## The two regions, and what a flag is worth in each

That scale classifies every event, and the classification is the difference between a
number worth acting on and a number that only describes the uncertainty:

- **Robust** (`pc_max_scale` at or above one). The probability is limited by the
  geometry. Shrinking the covariance would lower it, so the value in hand is not being
  propped up by the size of the uncertainty.
- **Dilution** (`pc_max_scale` below one). Shrinking the covariance would *raise* the
  probability: the event sits on the falling side of Alfano's curve, where the
  uncertainty is already large enough to spread the distribution thin. The number says
  the trajectories are uncertain, not that the objects are likely to meet.

Every event carries `region`, and the flag carries a `confidence`: `standard` in the
robust region, `low` everywhere else. **A red or yellow flag with low confidence is
never actionable**, and the report and the viewer say so wherever it appears. This is
not a way of dismissing awkward results; it is the honest reading of a probability whose
maximum lies below the covariance that produced it.

### Why the ISS red at 11.5 km is a dilution-region flag

The first live run's largest probability was the ISS against YAM-3, an active payload,
at a miss of 11.47 km seven days into the window, `pc` 1.6e-4. Seven days out the ISS's
own element sets disagree by 35 km in-track and YAM-3's by 30 km. Most of that lies
along the relative velocity and projects out of the encounter plane, leaving a combined
uncertainty of 13.9 km by 0.50 km in the plane, against a miss of 11.5 km and a combined
hard-body radius of 73 m. The miss is inside one sigma of the larger axis: the two
trajectories are, as far as the catalogue can tell, in the same place.

`pc_max_scale` is 0.88, so the covariance is already a little past the peak. Shrinking
it shows what the flag is worth:

| Covariance scale | `pc` |
| --- | ---: |
| 1 (as fitted) | 1.6e-4 |
| 0.5 | 1.3e-4 |
| 0.1 | 7.1e-7 |
| 0.01 | 3.6e-36 |

A tenfold better orbit for either object takes the probability down by a factor of two
hundred; a hundredfold better one, which is what an operational ephemeris would give for
the ISS, extinguishes it. The flag is a statement about the public catalogue seven days
ahead, not about the encounter, and better data would almost certainly clear it rather
than confirm it. That is why the report puts it under a heading that says so and never
counts it as actionable. The ISS programme screens its own conjunctions against an
operational ephemeris and covariance for exactly this reason.

## Flags

Red at a probability of `1e-4` or above, yellow at `1e-5`, the thresholds the ISS
programme uses (a yellow starts the planning of an avoidance manoeuvre, a red calls for
one unless the risk is refined away). The flag is set on `pc`, not on `pc_max`, and
every row carries both so the reader can apply either rule, together with the region and
the confidence above.

## Scenarios: geometry once, probability per scenario

The design rule for Phase 3, taken at the Step 2 review: Stages A to C run once per
snapshot and write the events; each scenario reruns only the covariance and the
probability over those stored events. `driftwatch screen` writes the run directory
(`events.parquet`, `objects.parquet`, `covariance.parquet`, `risk_quiet.parquet`,
`conjunctions.parquet`, `run.json`), and `driftwatch risk <run> --scenario <name>`
scores the same events again with another covariance model and adds a
`risk_<name>.parquet`, rebuilding the joined export with one row per event per
scenario. Every risk row carries the scenario, the run id, the snapshot and the model
version, and the event id is the same across scenarios, so a quiet row and a storm row
for one event are directly comparable. A covariance model is anything with a `version`
and a `covariance_ric(obj, epoch, at)` method (the protocol decided at the Step 0
review); `--scale` wraps the fitted model in a factor as a stand-in until Phase 3's
storm model exists.

## The Kelvins check

ESA's Kelvins Collision Avoidance Challenge dataset holds anonymised real conjunction
messages with the relative position and velocity in the target's RTN frame, both
objects' covariances and ESA's computed risk (log10 of the probability), and for many
rows a maximum risk and its scaling. `driftwatch kelvins` reconstructs the probability
from those inputs with the code above, treats the hard-body radius ESA used (not
given) as a fit parameter, and reports the radius that best reproduces the risk column
over the high-risk tail (`risk >= -6`) together with the distribution of residuals by
risk bin. Two approximations are stated in `risk/kelvins.py`: the chaser's frame is
built from the target's with the target's velocity taken as circular, and the
covariances are used as position-only matrices.

The dataset is not redistributed with driftwatch and has to be downloaded from the
Kelvins site (registration required) into `data/external/kelvins/`; without it the
reproduction test is skipped with a message saying where to put the file.

### What it gives

Run on `train_data.csv` (162,634 conjunction messages, 10,183 of them in the tail),
`driftwatch kelvins` writes `docs/kelvins-reproduction.md`. The headline:

| | |
| --- | --- |
| Best single hard-body radius | **9.0 m** |
| Median residual, log10 of ours over ESA's | **+0.22** (a factor of 1.7 high) |
| Within a factor of two | 43 % |
| Within a factor of ten | 80 % |
| Best-reproduced bin | risk -4 to -3: median -0.17, 58 % within a factor of two |
| Worst-reproduced bin | risk -6 to -5: median +0.39, 37 % within a factor of two |

The median meets the target of a factor of two across the tail, and the agreement is
best in the bins where an operator would act. The spread of individual rows does not
meet it, and the reason is worth stating rather than tuning away.

### Where the disagreement comes from

The residual's strongest correlation in the whole dataset is with the target's radar
cross-section (Spearman -0.63), far ahead of the time to closest approach (-0.02, so the
reconstruction is not drifting with propagation), the miss distance (-0.41) or the
covariance shape (-0.26). A negative correlation with size is what a single fitted
radius would produce if ESA had used a radius per object: our 9 m is too small for big
targets, making us under-report, and too large for small ones, making us over-report.

Fitting a radius separately in each quintile of the target's radar cross-section says so
directly:

| Radar cross-section (m^2) | Rows | Best radius | Median residual | Within x2 |
| --- | ---: | ---: | ---: | ---: |
| 0.01 to 2.35 | 2,020 | 2 m | +0.25 | 59 % |
| 2.35 to 3.23 | 1,981 | 4 m | -0.28 | 54 % |
| 3.23 to 4.32 | 1,985 | 7 m | 0.00 | 59 % |
| 4.32 to 4.98 | 2,001 | 11 m | -0.02 | 66 % |
| 4.98 to 28.0 | 1,975 | 13 m | +0.11 | 60 % |

The fitted radius rises monotonically with object size, from 2 m to 13 m, and the
agreement inside each quintile is markedly better than the 43 % over the pooled tail.
ESA used a hard-body radius that scaled with the objects; the dataset publishes the
target's radar cross-section but nothing at all about the chaser's size, so a
reproduction from its own columns cannot do better than a population compromise. The
9 m headline stays as the single-radius answer to the question the prompt asked; the
table above is the explanation of its spread, not a replacement for it.

One result comes out exactly. Comparing our covariance-scale sweep with ESA's own
`max_risk_scaling` column, the ratio of the two has a median of 0.9999 when ESA's is
read as a factor on the covariance, and 0.82 when read as a factor on the standard
deviation. ESA's scaling is a factor on the covariance, as ours is, and the maximum
probabilities agree to a median of +0.22 in log10, the same offset as the probabilities
themselves.

## The report and the viewer

`driftwatch screen` finishes by writing `report.md` in the run directory and the
viewer's `conjunctions.json` and `conjunction-tracks.bin`; `driftwatch report <run>`
rewrites both without rescreening.

**Repeated encounters are collapsed.** Two objects in nearby orbits meet every time
their planes cross, which for a co-orbital pair is every orbit: on the first live run one
Starlink satellite came back 130 times in a week. Listing all 130 buries the pairs a
reader should look at, so the report and the panel show one row per pair with the number
of events, the closest miss, the highest probability and the first time of closest
approach, and the individual events underneath on demand. The parquet and the JSON keep
every event, as decided at the Step 2 review.

**A pair also gets a cumulative probability**, one minus the product of the complements
over its events. It is an upper bound, not a probability: the events of one pair are
repeated passes of the same two objects propagated from the same two element sets, so a
position error that puts them close on one pass puts them close on the next. Their
errors are strongly correlated and the true combined probability is lower than the
product formula gives. It is reported because a reader comparing a pair seen 130 times
with a pair seen once needs some measure of the difference, and it is labelled as not
independent wherever it appears.

**The report** leads with the flagged pairs, split by region: the robust ones first, as
the pairs worth a second look, then the dilution-region ones under a heading that says
they are not actionable and why. Then the top twenty pairs by probability, the top twenty
by closest approach, a table per fleet member, and a section on how to read the numbers
that names the covariance sources actually used and the supplemental version each run
screened on.

**The viewer's conjunctions panel** lists the same collapsed pairs with a filter and a
flagged-only switch. Expanding a pair lists its events; selecting one pauses the clock,
jumps it to the time of closest approach, highlights both objects in the point cloud,
draws ten minutes of each object's track either side of the encounter, and opens an inset
of the encounter plane showing the hard-body disc, the one and three sigma contours of
the combined covariance and the miss vector, with the probability, the maximum
probability, its scale, the region and the confidence beside it.

Every number in the panel is Python's. The tracks are exported as TEME positions sampled
every 20 seconds and rotated to the Earth-fixed frame in the browser with the same GMST
the propagation worker uses, so a drawn track sits on its moving dot; the browser
computes no screening result of its own. The bundle carries every pair but the individual
events only for the flagged pairs, the pairs with an event inside the notification box
and the highest-probability pairs, which keeps it to a couple of megabytes; the run
directory holds the rest.

## References

- F. R. Hoots, L. L. Crawford and R. L. Roehrich, "An analytic method to determine
  future close approaches between satellites", Celestial Mechanics 33, 143-158 (1984).
  The apogee/perigee, orbit-path and time filters; Stage A here is the first of them.
- D. A. Vallado, Fundamentals of Astrodynamics and Applications, section 11.7, for the
  RSW (RIC) frame and close-approach geometry.
- T. S. Kelso, CelesTrak supplemental GP data, https://celestrak.org/NORAD/elements/supplemental/.
- J. L. Foster and H. S. Estes, "A parametric analysis of orbital debris collision
  probability and maneuver rate for space vehicles", NASA JSC-25898 (1992). The
  polar-grid integration.
- S. Alfano, "A numerical implementation of spherical object collision probability",
  Journal of the Astronautical Sciences 53(1), 103-109 (2005). The one-dimensional
  form used as the cross-check.
- S. Alfano, "Relating position uncertainty to maximum conjunction probability",
  Journal of the Astronautical Sciences 53(2), 193-205 (2005). The scale sweep and
  dilution.
- F. K. Chan, Spacecraft Collision Probability, The Aerospace Press (2008). The
  equal-area series.
- T. Flohrer, H. Krag and H. Klinkrad, "Assessment and categorisation of TLE orbit
  errors for the US SSN catalogue", AMOS Conference (2008); D. A. Vallado and P. J.
  Cefola, "Two-line element sets: practice and use", IAC-12 (2012). The default
  priors.
- L. K. Newman, "The NASA robotic conjunction assessment process: overview and
  operational experiences", Acta Astronautica 66, 1253-1261 (2010). The `1e-4` and
  `1e-5` thresholds.
- T. Uriot et al., "Spacecraft collision avoidance challenge: design and results of a
  machine learning competition", Astrodynamics 6, 121-140 (2022); data at
  https://kelvins.esa.int/collision-avoidance-challenge/.
