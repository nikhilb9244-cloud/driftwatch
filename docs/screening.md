# Conjunction screening: the three stages

How `driftwatch screen` finds close approaches between a fleet and the catalogue, why
the coarse time step cannot miss one, and what the output means. Step 3 of Phase 2 adds
uncertainty and probability on top of the geometry described here; the covariance
method, the probability definitions and the flag thresholds will join this page then.

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
trajectories, not of two spacecraft. Step 3 puts numbers on that.

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
(`starlink.rms.txt`, 0.1 to 5 km per satellite on 2026-09-02) are the floor on their
error, and the ephemerides are predictions that SpaceX revises. Manoeuvres by anything
else are not modelled at all; the `manoeuvrable_*` flags say which pairs involve an
object known to manoeuvre (the fleet's own flag for members; the `starlink`, `oneweb`,
`constellation` and `station` categories for secondaries) so a reader knows which
predictions can be overtaken by events.

## Output

`data/conjunctions/<fleet>_<start stamp>.parquet`, one row per event, with the columns
listed in `docs/data-schema.md`: identity of both objects, the time of closest approach
to the microsecond, the miss distance, the relative speed, the RIC components of the miss
vector, the two volume flags, the stale and manoeuvre flags, the secondary's ephemeris
source and the refinement method. Step 3 adds the uncertainty and probability columns
and Step 4 the run identity and the report.

## References

- F. R. Hoots, L. L. Crawford and R. L. Roehrich, "An analytic method to determine
  future close approaches between satellites", Celestial Mechanics 33, 143-158 (1984).
  The apogee/perigee, orbit-path and time filters; Stage A here is the first of them.
- D. A. Vallado, Fundamentals of Astrodynamics and Applications, section 11.7, for the
  RSW (RIC) frame and close-approach geometry.
- T. S. Kelso, CelesTrak supplemental GP data, https://celestrak.org/NORAD/elements/supplemental/.
