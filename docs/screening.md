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

### What the bound rests on, and where it does not hold

Every line of the argument above rests on one thing: `d(t)` is continuous, with a bounded
derivative. Phase 4 Step 1 introduced a trajectory for which that is not true everywhere,
so the guarantee has to be re-derived rather than assumed to carry over.

**Why the trajectory changed.** Where SpaceX has published states for a Starlink object,
Stage B and Stage C both use those states rather than CelesTrak's SGP4 fit to them
(`ephemeris/spacex.py`, `docs/spacex-ephemerides.md`). The first design considered was the
one the Phase 4 prompt proposed — screen on element sets, refine on the published states,
and widen the Stage A pad to cover the difference. Measured on nineteen matched files on
2026-09-03, that difference is a median 0.30 km inside 12 hours but **28 km at 36 to 48
hours and 83 km at 60 to 72**, with a 90th percentile of 211 km. There is no pad for that,
and screening on a trajectory tens of kilometres from the one the pair is then scored on is
not a defensible arrangement whatever the pad. So both stages moved to the same trajectory.

**Where it jumps.** An object's published states cover part of the window and not the rest,
and the stored history is split at every discontinuity in the published file — every file
measured has one at exactly 48 hours after `ephemeris_start`. So the served trajectory has
at most three jump instants per object per run: the start of coverage, the 48-hour seam and
the 72-hour horizon. Between two segments, and past the horizon, the SGP4 states serve, and
the change from one to the other is a step of up to tens of kilometres.

**The re-derivation.** Let interval `[t_k, t_(k+1)]` contain a jump for one of the pair's
objects. Inside it the trajectory is continuous on each side of the jump separately, so the
bound `|d'| <= v_bound` still holds on each side — but a minimum on one side can only be
reached from the endpoint on that side, not from the nearer of the two. The reach needed is
therefore the whole step rather than half of it:

```
d(t_k) <= d(t*) + v_bound h    for a minimum t* on t_k's side of the jump,
```

so on such an interval the threshold becomes `T_jump = R + v_bound h`, twice the ordinary
one less `R`. Stage B marks every interval holding a jump for either object and applies
`T_jump` there. For a typical LEO pair at the default step that is 503 km rather than
269 km, on a handful of intervals per ephemeris object per run.

**And how those candidates are refined.** Not by root finding: `f = dr . dv` has no
trustworthy sign change across a step in position, and a golden-section search needs a
unimodal function. The interval is scanned instead, on a hundred-point sub-grid, and the
smallest sampled separation is taken. At a 30-second step that places the time of closest
approach to 0.3 s, against the microsecond tolerance the root finder reaches elsewhere.
Those events carry `refine_method = "scan"` and are counted in the run summary, so the
coarser treatment can be seen rather than assumed away. A sampled local minimum is bracketed
by the two intervals either side of it and is used only when neither holds a jump.

**What is still not guaranteed.** The scan places a jump-interval event's time of closest
approach to about `h / 100`, not to the root finder's tolerance, so its miss distance is the
smallest on that sub-grid rather than the true minimum. And a break in the very first or very
last interval of a published file cannot be detected at all, because the detector needs a node
test on both sides. Both are stated here and in `ephemeris/spacex.py` rather than left to be
discovered.

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
  object.
- **The pairs are binned by lead time and each bin that holds enough pairs is weighted
  equally.** A store covering a week holds tens of thousands of pairs a few hours apart and
  a few hundred six days apart; fitted over the raw pairs the law is set almost entirely by
  the short leads and then extrapolated over the part of the range that decides a seven-day
  screen. A bin with fewer than 30 pairs is not used at all: its root-mean-square is noise,
  and three separate things hang off the bins (the floor, the growth and the horizon).
- **The exponent is a prior, not a fit** (see below).

### A floor plus a growth term, per component

Every RIC component of a supplemental covariance is a floor with a growth term over it:

```
sigma_k(dt)^2  =  floor_k^2  +  (s_k * dt^p_k)^2
```

**The floor** is what the disagreement already is at essentially no lead. Two measurements
give it. CelesTrak publishes the RMS of each fit to the operator's ephemeris in the
supplemental file itself (a median of 0.20 km, a 90th percentile of 0.27 km and a worst
case of 10.8 km when read on 2026-09-02): the disagreement between the element set and the
trajectory it was fitted to, invisible to any comparison between versions. And the shortest
lead-time bin that resolves gives the version-to-version disagreement at a lead of an hour
or two, which on the store in hand is 0.047 km radial, 0.471 km in-track and 0.026 km
cross-track — larger than the published residual, so it is the floor that binds.

The floor is the **larger** of the two per component, not their sum in quadrature, because
they are not independent: the disagreement between two versions published an hour apart
already contains both versions' fit residuals. The published RMS is a scalar, and it is
split across the components in the shape the shortest bin has, which is in-track dominated
— which is what an SGP4 fit to an ephemeris should look like.

**The growth** is fitted to what is left over the floor, `sqrt(rms_k^2 - floor_k^2)` in
each bin, not to the raw residual. Fitting the raw residual and then adding the floor in
quadrature counts the floor twice and puts the model above every bin it was fitted to; with
the excess, the model lands on the bin it is anchored at. On the store in hand the in-track
sigma at the anchor bin's lead of 0.119 days is 0.678 km against a measured 0.673 km.

**In-track always carries a growth term; radial and cross-track have to earn one.**
In-track growth is the mechanism — a semi-major-axis error becomes an along-track error
through the mean motion — so its absence from a few hours of pairs is a limit of the
measurement, not a statement about the physics. Radial and cross-track have no such
amplifier, so they are floor-only unless the longest resolved bin stands at least 1.5 times
its floor, and when they do earn a growth term it is capped at linear, which is how a
semi-major-axis or node error grows. Nothing makes it accelerate.

The sources are labelled `supplemental:consistency` when the exponent was fitted,
`supplemental:consistency-prior-p<p>` when it was the prior, `supplemental:rms` when there
is only one stored version and the floor is all there is, and `supplemental:beyond-horizon`
past the fit's validity.

The floor alone is a lower bound and is treated as one: an event scored on it lands in
the robust region below, where the maximum-probability sweep shows what a larger
uncertainty would give.

### The operator's own covariance, where it reaches

SpaceX publishes the ephemerides CelesTrak fits those supplemental sets to, with a
covariance at every state, 72 hours ahead. `driftwatch spacex` fetches them for the Starlink
secondaries of a run — one request per satellite, ranked by closest approach and capped, at
2 MB a file — keeps only the position covariance thinned to a ten-minute grid, and
`driftwatch risk` serves those objects from it inside each file's validity, labelled
`spacex-ephemeris`. Past the file, and for a Starlink object with no stored file, the base
model serves and reports **its own** label, so `cov_source_secondary` says which of the three
models covered each event; an event straddling the horizon reads
`spacex-ephemeris+<what the base said>`.

It is used **as published, plus one term**: the published residual of CelesTrak's SGP4 fit to
the same ephemeris, 0.2 km, added in quadrature because that fit is the trajectory driftwatch
actually propagates while their covariance describes the ephemeris. Split in the shape of the
base model's own floor it is 20 m radial, 199 m in-track and 11 m cross-track — a third of a
per cent of their kilometre-scale envelope past a day, and a tripling of the probability
inside one, where the covariance would otherwise be tighter than the gap between the two
trajectories. The version-to-version revision the supplemental fit measures is a different
matter and is deliberately **not** added: it is a different quantity, and `driftwatch spacex`
prints the two side by side instead:

| Lead | SpaceX in-track | driftwatch in-track | Ratio |
| ---: | ---: | ---: | ---: |
| 1 h | 6.7 m | 489 m | 73 |
| 3 h | 24 m | 700 m | 29 |
| 8 h | 257 m | 4.54 km | 18 |
| 24 h | 2.81 km | 8.47 km | 3.0 |
| 72 h | 3.80 km | 22.8 km | 6.0 |

Theirs is the uncertainty *within* one published plan; ours is the uncertainty *of the plan
being revised*, and past eight hours it is the GP element sets, which measure the manoeuvring
itself. Both numbers are real and they answer different questions. One caveat still travels
with theirs: past about ten hours it is a stated envelope on round figures rather than a
propagated covariance. `docs/spacex-ephemerides.md` has the terms, the format, the fit
residual and the full argument.

**What it did to the demo run.** 499 of 5,704 events served, the median secondary in-track
sigma on them falling from 24.8 km to 2.5 km. Of those events 111 were in the dilution region
and 37 now are — which is the point of a better covariance. Yellow pairs rise from 10 to 18,
because at a miss of one to three kilometres a tighter covariance concentrates the
probability on the disc instead of spreading it thin, and ZACube-1 against STARLINK-6053
drops from red to yellow while moving *out* of the dilution region.

### The exponent is a prior, and the fit has a horizon

Taken at the Phase 3 Step 0 review, and the most consequential correction in it.

The first two stored versions were two hours apart. Their consistency pairs span lead
times of 0.02 to 0.24 days, and a free power-law fit over them returned an in-track
exponent of 0.55. Evaluated at seven days that is an extrapolation by a factor of forty in
time, from a baseline of hours, at an exponent below anything the physics allows. What the
physics allows: an unmodelled along-track acceleration — a drag error, or a revised burn
plan — changes the semi-major axis linearly in time, which moves the object radially as
`t` and, through the mean motion, in-track as `t^2`; an along-track velocity or epoch
error moves it in-track as `t`. So the in-track exponent is constrained to `[1, 2]` with
the prior at 1.5, and the radial and cross-track exponents are held at one. Only the
amplitudes are fitted. The exponent is fitted, and then clipped into the range, only once
the store gives pairs across four or more lead-time bins reaching at least a day.

Constraining it does not rescue the extrapolation, and this is the part worth stating
plainly. With the amplitude anchored on those pairs, the in-track sigma at seven days
comes out at **42 km at `p = 1`, 321 km at `p = 1.5` and 2,500 km at `p = 2`** — against
about **18 km measured directly** from the same objects' GP element sets seven days apart.
There is no exponent in the physical range that makes the extrapolation safe, and choosing
the one that lands nearest the GP number would be fitting the answer.

So the fit carries a **validity horizon**, and past it the GP model serves, labelled
`supplemental:beyond-horizon`. The horizon sits at the top of the longest lead-time bin
that holds enough pairs to resolve a trend, capped at the longest pair actually seen — not
at the single longest pair, which can be one lonely late pair in an otherwise empty bin
carrying the model across the whole window. With the two versions in hand the horizon is
0.16 days, so almost the whole seven-day window falls back to the GP fit for Starlink
secondaries. That is the honest position: two versions two hours apart say
nothing about a week ahead, and the GP element sets, whose disagreement at seven days is
dominated by exactly the manoeuvring we cannot predict, are the better estimate at that
range even though they are the wrong instrument at short range.

The horizon moves out on its own. `driftwatch supplemental` fetches and stores a version
every three hours, under GitHub Actions (`.github/workflows/supplemental.yml`) or a
Windows scheduled task (`scripts/register-supplemental-task.ps1`), and thins versions
older than a fortnight to one a day so the store stays bounded while keeping the long
leads. Once it spans the screening window the fallback disappears and the exponent becomes
a measurement. `driftwatch supplemental --fit` refits across the whole store and prints
the lead-time bins.

Where the amplitude is anchored matters once the exponent is a prior. A law steeper than
the data can touch the bins at one point only: it is anchored at the **longest** occupied
bin that resolves, which is the bin nearest the lead times being asked about and the one
where the growing term is least swamped by the floor. Anchoring at the mean of the bins
would put the law a factor of two above its own longest bin. The shortest bin never
contributes an amplitude: the floor is its own residual, so its excess over the floor is
zero by construction.

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
secondary's. Nobody publishes the size of most secondaries, so the rules for one are all
lower bounds and the **largest of them wins**; the objects table records which.

- **The category default.** 30 m for a station, 10 m for a Starlink (V1.5 spans about
  11 m, V2 Mini about 30 m with both arrays), 3 m for OneWeb, the other constellations
  and payloads, 5 m for a rocket body, 0.5 m for debris, 1 m for an untyped object.
- **The span lookup** (`span`), for payloads, rocket bodies, debris and untyped objects,
  the four categories with no known envelope. The median radius of the object's type and
  radar cross-section class, derived from ESA's Kelvins data: 4.55 m for a large-return
  payload, 1.90 m for a large-return rocket body, 1.25 m for large-return debris, 1.0 m
  for everything else. See below and `docs/kelvins-reproduction.md`.
- **The radar cross-section** (`rcs`), `sqrt(RCS / pi)` clipped to 0.1 to 20 m, for the
  same four categories. It survives only where a cross-section is large enough to beat
  the lookup, which is the regime where it is least misleading.

The radius is a model parameter rather than a property of the run, so `driftwatch risk`
rebaselines it from the current rules before rescoring a stored run; a radius that came
from the fleet file is left alone.

### Slow encounters, where the straight line fails

The projection onto one plane holds because the pair passes in a straight line at constant
velocity: at 13 km/s a 10 km separation is crossed in under a second, in which a low Earth
orbit turns through a twentieth of a degree. Two objects in nearly the same orbit — two
members of one constellation, a satellite and its own upper stage — pass at metres per
second instead, and then the passage takes minutes, the relative path curves through it,
and the two can re-approach. More of the uncertainty is in play than one plane sees, so the
probability comes out **too low**.

Every event below 0.1 km/s relative carries `slow_encounter` in the risk table, and the
report says how many there are and whether any is flagged. It is a flag and not a
correction: nothing rescales the probability, and the fix is a three-dimensional
integration over the encounter, which is not in this phase. The demo run has 10 such events
out of 5,704, the slowest at 23 m/s, none of them flagged.

A large in-track uncertainty is *not* the same problem, and is deliberately not flagged. A
seven-day-old element set can be hundreds of kilometres uncertain along track, but that is
mostly a timing error — the object is on the same track, early or late — and projecting onto
the plane perpendicular to the relative velocity discards exactly that component. The
method survives a large in-track sigma and fails on a low relative speed.

The reproduction of ESA's risk column cannot measure the size of the underestimate, and it
is worth being clear about why: ESA's own column is computed the same way, so the residual
binned by relative speed shows nothing at the slow end (`docs/kelvins-reproduction.md`).
The two share the approximation exactly. The flag therefore comes from the method rather
than from the comparison.

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
the uncertainty already dilutes the probability, so that shrinking the covariance at the
same miss would raise it. This is Alfano's dilution, and it is what the Phase 3 storm
term will move.

The sweep scales the covariance and holds the miss fixed, which is an arithmetic
operation on the numbers in hand and not a forecast of what a better orbit would give.
A better orbit changes both: the covariance shrinks and the nominal miss moves, by a
distance of the order of the uncertainty that was removed, in a direction nothing here
can predict. Every statement about dilution below is a statement about the sweep.

## The two regions, and what a flag is worth in each

That scale classifies every event, and the classification is the difference between a
number worth acting on and a number that only describes the uncertainty:

- **Robust** (`pc_max_scale` at or above one). The probability is limited by the
  geometry. Shrinking the covariance would lower it, so the value in hand is not being
  propped up by the size of the uncertainty.
- **Dilution** (`pc_max_scale` below one). Shrinking the covariance at the same miss
  would *raise* the probability: the event sits on the falling side of Alfano's curve,
  where the uncertainty is already large enough to spread the distribution thin. The
  number says the trajectories are uncertain, not that the objects are likely to meet,
  and equally not that they are unlikely to: the data cannot support a judgement either
  way.

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

`pc_max_scale` is 0.88, so the covariance is already a little past the peak. Scaling it
down, with the miss held at 11.47 km, shows how much of the number the covariance is
carrying:

| Covariance scale | `pc` |
| --- | ---: |
| 1 (as fitted) | 1.6e-4 |
| 0.5 | 1.3e-4 |
| 0.1 | 7.1e-7 |
| 0.01 | 3.6e-36 |

Almost all of it. At a tenth of the covariance the probability is down by a factor of
two hundred, and at a hundredth it is gone: the flag is produced by an uncertainty of the
order of the miss, not by the trajectories passing close.

**This is not a forecast of what better tracking would give.** The rows above move the
covariance and leave the miss where it is, which no real improvement does. A better
orbit for either object would shrink the covariance *and* move the nominal miss, by a
distance of the order of the tens of kilometres of in-track uncertainty being removed,
and the miss can move either way: an 11.5 km miss can become 40 km or 0.5 km, and this
tool cannot say which. The honest reading is that the public catalogue, seven days
ahead, cannot tell whether these two objects come close or not. That is why the report
puts it under a heading that says so and never counts it as actionable, and it is why
the ISS programme screens its own conjunctions against an operational ephemeris and
covariance rather than against element sets.

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
from those inputs with the code above and reports the distribution of residuals by risk
bin. Two approximations are stated in `risk/kelvins.py`: the chaser's frame is built from
the target's with the target's velocity taken as circular, and the covariances are used as
position-only matrices.

The dataset is not redistributed with driftwatch and has to be downloaded from the
Kelvins site (registration required) into `data/external/kelvins/`; without it the
reproduction test is skipped with a message saying where to put the file.

### What it gives

Run on `train_data.csv` (162,634 conjunction messages, 10,183 of them in the tail),
`driftwatch kelvins` writes `docs/kelvins-reproduction.md` and its residual plot.

**The hard-body radius ESA used is in the data.** Phase 2 fitted a single radius, got 9 m
and agreement within a factor of two on 43 % of the tail, and put the spread down to ESA
having used a radius per object that the dataset did not publish. It does publish it. Each
object carries a `span` in metres, and the combined radius `(t_span + c_span) / 2`
reproduces the risk column with **no fitted parameter at all**:

| | Per-object span | One fitted radius |
| --- | --- | --- |
| Combined radius | `(t_span + c_span) / 2`, median 7.0 m | 9.0 m, fitted |
| Median residual over the tail | **-0.0003** (0.07 % in probability) | +0.22 (a factor of 1.7 high) |
| Median over risk above 1e-5 | **+0.0005** | +0.21 |
| Within a factor of two | **87 %** | 43 % |
| Within a factor of ten | **96 %** | 80 % |

Which settles the Phase 2 question: the probability integration agrees with ESA's to a
fraction of a percent, and the earlier spread was entirely the radius.

**The direction of the residual still matters.** The median is zero but the distribution
is not symmetric. Over the tail that matters the 5th percentile is -0.66 and the 95th is
+0.13: where the reconstruction disagrees it reads the encounter as *safer* than ESA did,
by up to a factor of ten, which is the dangerous direction. The rows in that tail are
disproportionately payloads (13 % of them against 4 % of the tail), which is where the
chaser-frame approximation is worst. Five of the eight rows above a risk of 1e-2 come out
two orders of magnitude low: at that risk the miss is comparable to the hard-body radius
and the two-dimensional method is at the edge of its assumptions.

### The radar cross-section is a poor size proxy, and we rely on it

The dataset's other size column is the radar cross-section, and scoring it the same way —
one free multiplier, fitted like the single radius — it needs a multiplier of nearly five
and still does no better than one radius for everything (median absolute residual 0.30
against 0.45, 50 % within a factor of two against 40 %). The radar cross-section is the
area of the echo rather than of the object: it understates anything much larger than the
radar wavelength, it depends on aspect and material, and it is missing on a third of the
chaser rows.

**That was a finding about driftwatch, not just about the dataset, and it has been acted
on.** `risk/scenario.py` used to take a secondary's hard-body radius from `sqrt(RCS / pi)`
for payloads, rocket bodies and debris, exactly the proxy that fails here, so those
probabilities were biased low. The formula is gone, replaced by the median chaser radius of
each object type and cross-section class in these same rows — half the median `c_span`,
since `(t_span + c_span) / 2` is what reproduces ESA's column with nothing fitted. The
cross-section survives as a *class* (small below 0.1 m2, medium to 1 m2, large above),
which is the part of it that carries size information.

| Object type | Small | Medium | Large | Unknown |
| --- | ---: | ---: | ---: | ---: |
| Payload | 1.00 m | 1.00 m | **4.55 m** | 1.50 m |
| Rocket body | 1.50 m | 1.50 m | **1.90 m** | 1.50 m |
| Debris | 1.00 m | 1.00 m | **1.25 m** | 1.00 m |
| Untyped | 1.00 m | 1.00 m | 1.00 m | 1.00 m |

Most cells are exactly 1.0 m because ESA defaults an unpublished span to 2.0 m. That
default is a screening convention, deliberately generous for an object whose size nobody
knows, and adopting it is what makes these probabilities comparable with ESA's. It moves in
the conservative direction: a fragment that `sqrt(RCS / pi)` clipped to a 0.1 m radius now
carries 1 m, and a hundred times the probability. The previous value is kept as a lower
bound, so a known envelope — a Starlink's 10 m, the station's 30 m — is never reduced to a
population median, and a cross-section large enough to beat the lookup still wins.

**What it did to the week in hand.** Rescoring the demo run's 5,704 stored events moved 756
of the 2,993 objects' radii, by a median factor of ten. 391 events gained more than a factor
of two of probability and 122 more than a factor of ten, with debris secondaries up by a
median factor of 2.4 and rocket bodies by 1.3. **No flag moved**: red stayed at 2 pairs,
yellow at 12, and the flagged pairs are all Starlink secondaries, whose 10 m envelope the
change does not touch. The events it did move were three or more orders of magnitude below
the yellow threshold. So the correction is real and it is in the safe direction, and this
week's headline numbers do not depend on it.

One more result comes out exactly. Comparing our covariance-scale sweep with ESA's own
`max_risk_scaling` column, the ratio of the two has a median of 0.9999 when ESA's is
read as a factor on the covariance, and 0.82 when read as a factor on the standard
deviation. ESA's scaling is a factor on the covariance, as ours is, and the maximum
probabilities agree to a median of +0.22 in log10 — the same offset as the probabilities
themselves, because that comparison is still computed at the single fitted radius.

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
