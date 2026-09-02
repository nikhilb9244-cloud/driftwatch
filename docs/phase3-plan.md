# Phase 3 plan: the storm layer

The working plan for Phase 3, written the way `docs/phase2-plan.md` was: decisions before
the code, results after it, and a review section per step. The prompt is
`docs/phase3-prompt.md`.

## What Phase 3 delivers

A storm term on top of the Phase 2 machinery. Nothing rescreens: Stages A to C stay as
they are, and every scenario rescores the stored events of a run through the covariance
protocol and `driftwatch risk`. What is new is where the covariance and the nominal
position come from — a density model driven by observed or forecast space weather, a
ballistic coefficient per object, and an in-track displacement that grows with the square
of time.

## Module layout (target for the whole phase)

```
src/driftwatch/
  weather/           # Step 1
    celestrak_sw.py  # SW-All.csv: Kp, ap, F10.7 back to 1957, cached daily
    swpc.py          # NOAA SWPC JSON: real-time Kp, three-day forecast, 27-day outlook, solar wind
    table.py         # the three-hourly space weather table with provenance and issue times
    helioviewer.py   # Sun imagery for the replay, cached, a few frames per storm day
  drag/              # Step 2
    density.py       # pymsis / NRLMSIS 2.x, the ap input vector, density along an orbit
    ballistic.py     # B per object: fitted from decay history, or from B* with a label
  storm/             # Step 3
    term.py          # the in-track displacement and its variance
    scenarios.py     # quiet, forecast, storm-g3/g4/g5, replay
  risk/
    covariance.py    # extended so a scenario returns an in-track mean shift beside the covariance
  catalogue/
    historical.py    # Step 4: a snapshot as of a date from gp_history, cached permanently
```

## Step 0 decisions (Phase 2 close-out, built 2026-09-02)

Five items from the prompt. Four were straightforward; the second turned into the most
consequential correction of the phase so far and is written up at length.

### 1. Dilution wording

The dilution region means **the data cannot support a judgement either way**. Removed from
the methods page, `docs/screening.md`, the report and the viewer panel every statement
that better data would clear a flag, and replaced them with the distinction that was being
elided:

- The covariance-scale sweep is *arithmetic on the numbers in hand*. It scales the
  covariance and holds the miss fixed, which is what makes `pc_max_scale` meaningful.
- A better orbit does not do that. It shrinks the covariance **and moves the nominal
  miss**, by a distance of the order of the uncertainty being removed, in a direction
  nothing here can predict. An 11.5 km miss with 13.9 km of in-track uncertainty can
  become 40 km or 0.5 km.

So the sensitivity table for the ISS versus YAM-3 stays — it shows how much of the
probability the covariance is carrying — but the sentences that read it as a forecast are
gone. The Step 3 review section of `docs/phase2-plan.md` carries a dated correction rather
than being quietly rewritten.

### 2. The supplemental exponent, and the horizon it forced

The prompt asked for the growth exponent to be constrained to a physically plausible
range, at least linear and at most quadratic, with only the amplitude fitted. Done, and
then the constraint showed that the extrapolation itself was the problem.

**The constraint.** An unmodelled along-track acceleration — a drag error, or a revised
burn plan — changes the semi-major axis linearly in time, which moves the object radially
as `t` and, through the mean motion, in-track as `t^2`; an along-track velocity or epoch
error moves it in-track as `t`. So the in-track exponent is constrained to `[1, 2]` with
the prior at 1.5, and the radial and cross-track exponents are held at one, their own
mechanism being linear. Only the amplitudes are fitted. The in-track exponent is fitted,
then clipped into the range, only once the store gives pairs across four or more lead-time
bins reaching at least a day. `SUPPLEMENTAL_PRIOR_P` and its neighbours in
`risk/covariance.py` carry the reasoning.

**Binning by lead time.** Consistency pairs are binned on fixed edges (0.02, 0.05, 0.1,
0.25, 0.5, 1, 2, 4, 7 days) and each occupied bin is weighted equally, so that the
thousands of pairs a few hours apart do not outweigh the few days apart. With a fitted
exponent the amplitude is the log-mean of the bins; with a prior exponent it is anchored
at the **longest** occupied bin, because a law steeper than the data can touch them at one
point only and that point decides the extrapolation.

**What the constraint revealed.** The two stored versions give pairs from 0.02 to 0.24
days. Anchored there, the in-track sigma at seven days is:

| Exponent | sigma_i at 7 days |
| --- | ---: |
| `p = 1` (linear) | 42 km |
| `p = 1.5` (the prior) | 321 km |
| `p = 2` (quadratic) | 2,500 km |

against about **18 km measured directly** from the same objects' GP element sets seven
days apart. No exponent in the physical range makes that extrapolation safe, and choosing
the one that lands nearest 18 km would be fitting the answer.

**So the fit carries a validity horizon**, at its longest observed pair, and past it the
base (GP) model serves with the source labelled `supplemental:beyond-horizon`. Today the
horizon is 0.24 days, so almost the whole seven-day window falls back to GP for Starlink
secondaries. That is the honest position: two versions two hours apart say nothing about a
week ahead, and at that range the GP disagreement — which is dominated by exactly the
manoeuvring we cannot predict — is the better estimate, even though it is the wrong
instrument at short range. `SupplementalCovariance` applies the horizon per requested
time, so one object's events can be served by both models, and the label says when they
were.

**A floor, kept a floor.** A prior exponent anchored at the longest bin passes *under* the
shorter bins. The covariance is meant to be a floor on the error, so the measured
consistency in the shortest bin joins CelesTrak's published fit RMS as the floor, and no
growth law can undercut a disagreement that was actually measured.

**The horizon moves out on its own.** `driftwatch supplemental` fetches a version, stores
it, thins versions older than a fortnight to one a day, and with `--fit` refits across the
whole store and prints the bins. It runs every three hours from
`.github/workflows/supplemental.yml` (which commits to a `supplemental-store` branch,
inert until the repository has a remote) or from a Windows scheduled task registered by
`scripts/register-supplemental-task.ps1`, which is what will actually run today. Once the
store spans the screening window the fallback disappears and the exponent becomes a
measurement rather than a prior.

**The rescore.** `driftwatch risk latest --refit --offline` over the same 5,704 stored
events:

| | Step 3 fit (free exponent, no horizon) | Step 0 fit (prior exponent, horizon) |
| --- | ---: | ---: |
| Red pairs | 1 | 2 |
| Yellow pairs | 26 | 10 |
| Flagged pairs in the dilution region | 22 | 7 |
| Highest probability | 1.58e-4 | 1.58e-4 |

ZACube-1 versus STARLINK-6053 comes back to red at 1.02e-4, where the GP-history fit had
it before the supplemental layer existed, because it is now served by the GP model past
the horizon. The yellows fall from 26 to 10 for the same reason: the tight supplemental
covariance that produced them was an extrapolation, and it has been withdrawn rather than
defended.

### 3. SpaceX ephemerides: may we use them?

`docs/spacex-ephemerides.md`. In short: **yes**, and the terms question turned out to be
about the wrong party. Space-Track stopped hosting them on 28 July 2025 — confirmed here
by direct query, its `/publicfiles/` API now returns only the NASA-JSC ISS files — and
SpaceX serves them itself at `api.starlink.com/public-files/ephemerides/`, unauthenticated,
with no licence or restriction stated. Space-Track's blanket approval would not have
covered them (it covers basic space surveillance data, and an operator ephemeris is not
that), but Space-Track's agreement no longer applies at all.

The rule adopted is the one already used for CelesTrak's supplemental data: use them,
credit SpaceX, publish derived results, do not republish the raw files.

Two things worth knowing before the later step builds on them. Their covariance is a real
propagated one for about ten hours and then a **stated envelope** — exactly 100 m radial,
1,000 m in-track, 10 m cross-track from 12 to 48 hours, stepping to 350/2,000/550 m for
the last twelve. And it is eleven times tighter than our own measurement of the
version-to-version revision at the same lead, because it is the uncertainty *within* one
plan and not of the plan being revised. The plan for days four to seven, where the file
stops, is in that document.

### 4. The ISS versus YAM-3 red, stated plainly

The report gained a **"The flags, plainly"** section after the summary: one line per
flagged pair naming the region of the event that raised the flag, with the explanation
given once at the top rather than repeated. The answer for the week in hand: the ISS
versus YAM-3 red at `pc` 1.58e-4, at a miss of 11.5 km, is **dilution, not robust**, with
the maximum at 0.88 times the covariance. So is the second red, ZACube-1 versus
STARLINK-6053. Five of the twelve flagged pairs are robust, all yellow.

The pair table gained `miss_at_max_pc_km` so the sentence quotes the miss of the event
that raised the flag rather than the pair's closest approach, which can be a different
pass.

### 5. Kelvins: the tail, the bias, the plot, and the radius

The tail restricted to risk above 1e-5, the direction of the bias and a residual-against-
risk plot were all asked for. Testing the radar cross-section as a size proxy, which was
the fifth item, produced something better than expected.

**ESA's hard-body radius is in the data.** Phase 2 fitted a single radius (9.0 m, 43 % of
the tail within a factor of two) and attributed the spread to ESA having used a per-object
radius the dataset did not publish. It does publish it: each object carries a `span` in
metres, and the combined radius `(t_span + c_span) / 2` reproduces the risk column with
**no fitted parameter** to a median residual of -0.0003 in log10 — 0.07 % in the
probability — with 87 % of the tail within a factor of two and 96 % within ten. Over the
tail that matters, 92 % within a factor of two. The multiplier that comes out of the fit
is exactly one, which is what identifies it as ESA's convention rather than a good fit.

That closes the Phase 2 question: the probability integration agrees with ESA's to a
fraction of a percent, and the earlier spread was the radius, not the method.

**The direction of the bias.** In the median there is none. The distribution is one-sided,
though: over the tail that matters the 5th percentile of the residual is -0.66 and the
95th is +0.13, so where the reconstruction disagrees it reads the encounter as *safer*
than ESA did, by up to a factor of ten. That is the dangerous direction, and the rows in
that tail are disproportionately payloads (13 % of them against 4 % of the tail), which is
where the chaser-frame approximation is worst. Five of the eight rows above a risk of 1e-2
come out two orders of magnitude low, at the edge of the two-dimensional method's
assumptions.

**The radar cross-section fails as a size proxy, and we use it.** Given the same free
multiplier, `rcs` needs nearly five times and still does no better than one radius for
everything. It is the area of the echo, not of the object. `risk/scenario.py` takes a
secondary's radius from `sqrt(RCS / pi)` for payloads, rocket bodies and debris, so those
probabilities are biased low — recorded in the approximations list, and a Phase 4 item to
prefer a published dimension wherever one exists.

**The plot** is `docs/kelvins-reproduction.svg`, written beside the markdown by
`driftwatch kelvins --out`: a density map of the residual against ESA's risk with the
median and 5th/95th percentiles per decade, and the old single-radius median in grey for
contrast. Drawn as hand-written SVG so the repository keeps no plotting dependency and the
file diffs.

## Step 0 revision (the review's four changes, 2026-09-02)

Step 0 was approved with four changes before Step 1. All four are built. Each is written
up with what it did to the numbers, because three of the four move probabilities and one
of them moves them by two orders of magnitude.

### 1. Every covariance component is a floor plus a growth term

The supplemental fit had a scalar floor split across the components in the shape of the
fitted growth, and the growth was fitted to the raw residual and then had the floor added
in quadrature on top — which counts the floor twice and puts the model above every bin it
was fitted to. Now:

- **The floor is per component**, and it is the larger of two measurements: the shortest
  lead-time bin that resolves, and CelesTrak's published RMS of the fit to the operator
  ephemeris split in the shape that bin has. The larger, not the quadrature sum, because
  they are not independent — two versions published an hour apart already disagree by both
  their fit residuals. On the store in hand the floor is `(0.047, 0.471, 0.026)` km and the
  published RMS (median 0.197 km) does not bind anywhere.
- **The growth is fitted to the excess over the floor**, `sqrt(rms^2 - floor^2)` per bin.
  The model now lands on its anchor bin: in-track 0.678 km against a measured 0.673 km at a
  lead of 0.119 days, where before it stood above it.
- **In-track always carries a growth term**, exponent prior 1.5 constrained to `[1, 2]`,
  because in-track growth is the mechanism and its absence from a few hours of pairs is a
  measurement limit rather than a physical statement. **Radial and cross-track are
  floor-only** until the longest resolved bin stands at least 1.5 times its floor, and then
  the growth is capped at linear — a semi-major-axis or node error grows linearly and
  nothing accelerates it. On the store in hand all three resolve.
- **A bin is used only when it holds 30 pairs.** The shortest bin of the current store has
  13 and is dropped, which is right: its root-mean-square is noise, and the floor, the
  growth and the horizon all hang off the bins.
- **The horizon is the top of the longest resolved bin**, capped at the longest pair
  actually seen, rather than the single longest pair. On the current store both give 0.157
  days (the 0.24 quoted in Step 0 above was measured on a slightly different set of pairs
  from the same two versions, before the 30-pair minimum dropped the thin first bin); the difference matters when one lonely late pair would otherwise carry the model
  across the whole window. A regression test builds exactly that case (200 objects six
  hours apart, two objects five days apart) and checks the horizon stays under a day.

**Effect on the run: none.** Rescoring the 5,704 stored events leaves red at 2 pairs and
yellow at 12, because almost every Starlink secondary is past the horizon and served by the
GP model either way. The change is about the model being honest at the leads it does serve.

### 2. The secondary radius: the radar-cross-section formula is gone

`sqrt(RCS / pi)` is the radius of the disc that returns the same echo, not the size of the
object. It is replaced by a lookup derived from the Kelvins data —
`kelvins.chaser_radius_table`, the median chaser span halved, by object type and radar
cross-section class — with the previous value kept as a lower bound so that a known
envelope or a large cross-section is never reduced to a population median.

| Object type | Small | Medium | Large | Unknown |
| --- | ---: | ---: | ---: | ---: |
| Payload | 1.00 m | 1.00 m | **4.55 m** | 1.50 m |
| Rocket body | 1.50 m | 1.50 m | **1.90 m** | 1.50 m |
| Debris | 1.00 m | 1.00 m | **1.25 m** | 1.00 m |
| Untyped | 1.00 m | 1.00 m | 1.00 m | 1.00 m |

The lookup is baked into `risk/scenario.py` so that screening does not depend on a dataset
behind a registration wall, and `driftwatch kelvins` re-derives it and warns if the code
has drifted from the data. A test asserts they agree.

**The rebaseline.** `driftwatch risk latest --refit --offline` over the same 5,704 events.
The hard-body radius is a model parameter rather than a property of the run, so a rescore
now recomputes it from the current rules (leaving fleet-file radii alone) and logs what
moved.

| | Before | After |
| --- | ---: | ---: |
| Object radii changed | — | 756 of 2,993, median factor 10 |
| Events whose probability rose by more than 2x | — | 391 |
| ... by more than 10x | — | 122 |
| Median factor, debris secondaries | — | 2.44 |
| Median factor, rocket-body secondaries | — | 1.28 |
| Red pairs | 2 | 2 |
| Yellow pairs | 12 | 12 |
| Flagged pairs in the dilution region | 8 | 8 |
| Highest probability | 1.58e-4 | 1.58e-4 |

**No flag moved**, and the reason is worth stating: every flagged pair this week has a
Starlink secondary, whose 10 m envelope the change does not touch, and the events that did
move were three or more orders of magnitude below the yellow threshold. So the correction is
real, it is in the safe direction, and this week's headline numbers do not rest on it.

The caveat travels with the number. Most cells are exactly 1.0 m because ESA defaults an
unpublished span to 2.0 m; the radius of an unknown object is a **screening convention**,
deliberately generous, and adopting it is what makes these probabilities comparable with
ESA's. A median is not a measurement — any individual fragment may be a tenth of it.

### 3. The Kelvins residual against relative speed: a null result, and why it is not a clearance

Asked: does the one-sided residual correlate with relative speed, since the two-dimensional
method assumes straight-line relative motion and fails for slow encounters?

| Relative speed | n | median | p05 | within x2 | more than 3x low |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 to 1 km/s | 238 | +0.0014 | -0.85 | 85 % | 7.1 % |
| 1 to 4 km/s | 1,071 | +0.0002 | -0.85 | 84 % | 9.5 % |
| 4 to 10 km/s | 2,603 | -0.0006 | -1.20 | 83 % | 10.8 % |
| 10 to 14 km/s | 3,282 | -0.0005 | -0.83 | 85 % | 8.4 % |
| 14 to 20 km/s | 2,989 | -0.0002 | -0.29 | 93 % | 4.3 % |

**The slow bin is not where the disagreement lives.** It is unremarkable, and slightly
better than the 4 to 10 km/s band. Agreement improves monotonically towards head-on
encounters instead.

That null result does **not** clear the method, and the reason is the interesting part. The
comparison is against ESA's own operational risk column, which this reconstruction
reproduces to a fraction of a percent *including on the slow rows*. That agreement is
itself the evidence: if ESA had integrated the slow encounters in three dimensions and
driftwatch had not, the slow bin would stand out. It does not, so both are computing the
same two-dimensional integral and a bias they share is invisible here whatever its size.

**So the flag was added anyway, on the method rather than on the measurement.** This goes
one step beyond the conditional instruction, and deliberately: the failure of the
rectilinear assumption at low relative speed is a documented property of the integral, not
a hypothesis the Kelvins rows were able to test. `slow_encounter` marks every event below
0.1 km/s relative — at that speed a pair takes 100 s to cross 10 km, in which a low orbit
turns through about 6 degrees, against a twentieth of a degree at 13 km/s — and the report
says how many there are and whether any is flagged. It is a flag and not a correction:
nothing rescales the probability, and the fix is a three-dimensional integration, which is
not in this phase. **The demo run has 10 such events out of 5,704, the slowest at 23 m/s
(CubeSat XI-IV against CZ-6A debris), none of them flagged.**

One thing the flag deliberately does not catch: a large in-track uncertainty. A seven-day-old
element set can be hundreds of kilometres uncertain along track, but that is mostly a timing
error — the object is on the same track, early or late — and projecting onto the plane
perpendicular to the relative velocity discards exactly that component. An earlier version of
this flag used the encounter duration from the along-velocity sigma, the textbook Coppola
criterion, and it flagged 225 events at 14 km/s while missing the 23 m/s pass. Relative speed
is the right discriminator.

### 4. SpaceX ephemerides, integrated

`ephemeris/spacex.py` and `driftwatch spacex`. Their covariance is used **as published** for
Starlink secondaries inside each file's 72-hour validity, labelled `spacex-ephemeris`;
outside it the base model serves and reports its own label, so the report shows exactly where
the covariance changed hands. The supplemental-consistency fit stays as a cross-check rather
than being merged in, since the two measure different things: theirs is the uncertainty
*within* one published plan, ours is the uncertainty *of the plan being revised*.

What the module does and does not do:

- One request per satellite, only for the satellites a run's events involve, ranked by
  closest approach and capped (`--limit`, 300 by default). At 2 MB a file the whole
  constellation would be 22 GB a version.
- Only the position covariance is kept, thinned to a ten-minute grid: 2 MB becomes tens of
  kilobytes. The 21 published numbers are the lower triangle of the 6x6, row-major, in their
  UVW frame, which is our RIC.
- **Analysis only.** No licence is stated, so the raw files are never redistributed and
  neither is the derived store; `data/spacex/` is git-ignored and out of the viewer bundle.
  `docs/data-sources.md` carries the standing rule and the credit line.

**The cross-check, measured on 120 satellites of the demo run.** `driftwatch spacex` prints
their sigma beside ours at matched leads:

| Lead | SpaceX in-track | driftwatch in-track | Ratio | Which model of ours |
| ---: | ---: | ---: | ---: | --- |
| 1 h | 6.7 m | 489 m | 73 | supplemental consistency |
| 3 h | 24 m | 700 m | 29 | supplemental consistency |
| 8 h | 257 m | 4.54 km | 18 | GP (past the supplemental horizon) |
| 24 h | 2.81 km | 8.47 km | 3.0 | GP |
| 48 h | 2.51 km | 15.8 km | 6.3 | GP |
| 72 h | 3.80 km | 22.8 km | 6.0 | GP |

The sign is right everywhere and the gap is widest at short lead, which is what the two
quantities predict: a published plan is nearly exact an hour ahead and the revision is then
the whole error. Their in-track sigma is not monotonic across the constellation (2.81 km at
24 hours against 2.51 at 48), which is what a control box on round figures looks like when
different satellites sit on different steps.

**This is the change that moves the numbers.** `driftwatch risk latest` with and without
`--no-spacex`, same events, same radii:

| | Without SpaceX | With SpaceX |
| --- | ---: | ---: |
| Events served by their covariance | 0 | 499 of 5,704 (245 fully, 254 straddling the horizon) |
| Median secondary in-track sigma on those events | 24.8 km | **2.5 km** |
| Of those events, in the robust region | 388 | **462** |
| ... in the dilution region | 111 | **37** |
| Red pairs | 2 | **1** |
| Yellow pairs | 10 | **18** |
| Flagged pairs in the dilution region | 7 | 8 |
| Highest probability | 1.58e-4 | 1.58e-4 |

Both directions are visible and both are right. **Fewer events sit in the dilution region**,
because a covariance three to ten times smaller stops being the thing holding the
probability up — that is the point of using it. **More pairs are flagged yellow**, because at
a miss of a kilometre or two a tighter covariance concentrates the probability mass on the
disc instead of spreading it thin: eleven events go from unflagged to yellow, every one of
them EOS SAT-1 against a Starlink, ten of the eleven at a miss under three kilometres, with
the probability rising by factors of three to three thousand. Two events go the other way,
where the miss is large enough that the narrower Gaussian pulls away from the disc. And
ZACube-1 against STARLINK-6053, the Phase 2 red, drops to yellow at 8.4e-5 *and moves from
the dilution region to the robust one* (scale 0.88 to 1.05), which is a better outcome than
the number falling: it is now a statement about the geometry rather than about the
uncertainty.

EOS SAT-1 dominating the new flags is not an accident of the fetch. It is a 177 kg
microsatellite in a 454 by 466 km sun-synchronous orbit, right where the Starlink shells sit,
so it has more events with Starlink secondaries than any other fleet member and its numbers
were dominated by the secondary's uncertainty. Replacing that uncertainty with the
operator's own is exactly the case this layer was built for.

The remaining red is the ISS against YAM-3 at 1.58e-4, untouched — YAM-3 is not a Starlink,
so nothing here reaches it, and it stays a dilution flag.

**One thing not done, and it is a review question.** The geometry driftwatch propagates is
CelesTrak's SGP4 fit to this ephemeris, not the ephemeris itself, and that fit's own
published residual is about 0.2 km — larger than SpaceX's own sigma for the first several
hours (24 m in-track at 3 hours, measured across the constellation). Used as published, the
covariance inside that range is tighter than the trajectory it is attached to. Applying the
fit residual as a floor is implemented and off by default (`add_fit_rms_floor`), because
"use their covariance as published" was the instruction. Given how much the layer moves the
flags, this one matters more than it looked before the numbers were in.
*Answered by the review: turn it on, in quadrature. Done — see "The four instructions"
below, and the first Phase 4 item in `ROADMAP.md` for the fix it stands in for.*

### Questions for the Step 0 review

1. **The horizon is the big one.** It withdraws the tight Starlink covariance that Step 3
   of Phase 2 introduced, and puts most of the seven-day window back on GP element sets
   until the store accumulates. The alternative was to keep extrapolating a law that the
   objects' own element sets contradict by a factor of twenty. Is withdrawing it the call
   you want?
2. **The prior exponent is 1.5 in-track, 1.0 radial and cross-track.** The prompt said "at
   least linear and at most quadratic"; applying that to all three components would give a
   radial sigma of 9 km at seven days, which is not credible for an operator ephemeris, so
   the constraint is applied to the in-track component and the other two are held at their
   own linear mechanism. Reasonable?
3. **The scheduled fetch has not run yet.** CelesTrak's two-hour floor had not elapsed
   when Step 0 finished, so the store still holds the two versions from this morning. The
   Windows task needs registering (`scripts/register-supplemental-task.ps1`) for the
   horizon to start moving.
4. **Should the span finding change driftwatch's own radii now, or in Phase 4?** The
   Kelvins result says a published dimension beats a radar cross-section. Changing
   `SECONDARY_HBR_M` would move every probability in the catalogue, which is a Phase 4
   decision rather than a Phase 3 one, so nothing was changed.
   *Answered by the review: change it now. Done, above; no flag moved.*

### Questions for the Step 0 revision

1. **Should SpaceX's covariance carry the SGP4 fit residual as a floor?** As published it
   is tighter than CelesTrak's fit to the same ephemeris, which is the trajectory we
   actually propagate. The switch exists and is off. Turning it on would raise every
   Starlink secondary's covariance inside about the first eight hours to 0.2 km, roughly
   eight times their published in-track sigma at three hours. This is now the biggest open
   question of the four, because the SpaceX layer is what moves the flag counts.
   *Answered by the review: yes, and in quadrature rather than as a floor. Done; the tally
   did not move. See "The four instructions" below.*
2. **Only 120 satellites were fetched, of 1,751 Starlink objects in the run.** The cap is
   politeness and disk: 2 MB a file, 8 minutes for 120. The 120 were chosen by closest
   approach, which is the ranking available before scoring. Is that the right selection
   rule, and is 300 the right default cap?
3. **The slow-encounter flag was added on a null result.** The Kelvins rows could not
   confirm the underestimate, because ESA's reference shares the approximation. The flag
   rests on the method instead. Is that the call you want, or should it wait for a
   three-dimensional integration that can measure it?
4. **`slow_encounter` is a new column in every risk table and in `conjunctions.parquet`,**
   and `floor_r_km`, `floor_i_km` and `floor_c_km` are new in `covariance.parquet`. Both
   are additive. The viewer does not read either yet.

## Step 1 decisions (space weather, built 2026-09-02)

`src/driftwatch/weather/`, `driftwatch weather`, `docs/space-weather.md`,
`tests/test_weather.py`. Everything the prompt asked for is in, and the decisions worth a
review are below.

### The table, and the layering that fills it

One row per three-hour interval, built on demand from the caches by
`weather.table.weather_table`. Columns: `t`, `kp`, `ap`, `ap_daily`, `f107`, `f107_81`,
`f107_adj`, `f107_adj_81`, `provenance`, `source`, `issued_at`. The schema is in
`docs/data-schema.md`; it is the thing the prompt said to ask about, and it is the prompt's
own list plus three additions, each with a reason:

- **`ap_daily`** as well as the interval's `ap`, because NRLMSIS wants both the daily Ap and
  the three-hourly history and computing one from the other in the density module would hide
  which day a boundary interval belongs to.
- **`f107_adj` and `f107_adj_81`** beside the observed pair. CelesTrak publishes both;
  observed is the one an atmosphere model wants, because the atmosphere feels the flux that
  arrives rather than the flux scaled to 1 AU. Carrying both makes the choice visible and
  reversible instead of buried in a loader.
- **`source`** as well as `provenance`. "Forecast" does not distinguish SWPC's three-day Kp
  from CelesTrak's six-week prediction from a 27-day recurrence climatology, and those are
  very different objects.

The sources are layered best-first, each filling only what the one above leaves:

| Layer | Source | On the live window of 2026-09-02 |
| --- | --- | ---: |
| 1 | CelesTrak observed | 0 intervals |
| 2 | SWPC observed, then estimated | 4 |
| 3 | SWPC three-day Kp forecast | 17 |
| 4 | CelesTrak predicted (about six weeks out) | 36 |
| 5 | SWPC 27-day outlook | 0 |

Layer 2 was added after the first build showed the hole it fills: CelesTrak rebuilds its file
once a day, so the last day or two before now has only a CelesTrak *prediction* while SWPC
already has the real index. Falling through to a forecast when a measurement exists would
have been wrong every single day.

### Four decisions worth the review's attention

1. **A gap stays a gap.** An interval with no source in any layer comes back NaN with
   provenance `missing`. Substituting a quiet zero would be a silent invention, and Step 2
   has to decide what to do about a hole rather than be handed one dressed as a calm day.
   `driftwatch weather` prints a warning when the count is not zero.
2. **The 27-day outlook's A index is used, not its largest Kp.** The outlook is a daily
   product giving both. Repeating a daily *maximum* across eight intervals would say the whole
   day was as bad as its worst three hours, which for a density model driven by the average
   overstates in the dangerous direction. The A index is already a daily average, so spreading
   it flat is the honest reading, and `kp` on those rows is the inverse of the ap table.
3. **The forecast issue time is fetched, not inferred.** SWPC's JSON products carry no issue
   time, and their `Last-Modified` is a file-regeneration time — measured at 36 seconds before
   the request, which is meaningless as a forecast stamp. So the three-day forecast **text**
   product is fetched alongside the Kp JSON purely for its `:Issued:` line. Two small requests
   every half hour, in exchange for a stored run knowing which forecast it used.
   `issued_from` records which of four routes gave each stamp.
4. **ap, not Kp, is what the table is really for.** Kp must not be averaged: 4 and 6 are 27
   and 80 nT, whose mean is 53 nT, which is Kp 5+ and not Kp 5. The Bartels table is
   reproduced in the code rather than pulled from a dependency, and a test walks it in both
   directions.

### What the store looks like

Every SWPC fetch is written under its product and **issue** time and never overwritten
(`data/weather/swpc/`), with a sidecar carrying the URL, the fetch time, the issue time and
how the issue time was determined. `swpc.stored_before(product, when)` returns the version
that existed at a past moment, which is what will let a stored run rescore against the
forecast it actually used. The four products together are about 1.2 MB a fetch, almost all of
it the week of one-minute solar wind.

Sun imagery is `weather/helioviewer.py`: SDO/AIA 193 A through `takeScreenshot`, four frames
a day, 512 px, cached permanently by the time **requested** with the time actually returned
recorded beside it. On the Gannon storm days the two differ by 13 seconds; during a data gap
they could differ by hours, and a replay showing yesterday's Sun without saying so would be
worse than showing none.

### Questions for the Step 1 review

1. **Is the table schema right?** It is the prompt's list plus `ap_daily`, the adjusted F10.7
   pair and `source`, reasoned above. This is the thing that constrains Phase 4, so it is the
   one to push back on now.
2. **Layer 4 is CelesTrak's predicted Kp, and that is what covers days four to seven of a
   screening window.** It appears to be derived from SWPC's own forecasts, so it is not an
   independent opinion — it is a smoothed, longer-range version of layer 3. Should days four
   to seven instead be treated as having *no usable geomagnetic forecast*, with the scenario
   machinery (quiet, storm-g3 and so on) carrying that part of the window? That would be the
   more honest position and it is a bigger change than it looks.
3. **The solar wind is stored but not yet used.** A week of one-minute L1 data is most of the
   store's bulk. It is context for the replay rather than a driver; if it stays unused past
   Step 5 it should be dropped to the one-hour feed.

## The four instructions (Step 1 review, 2026-09-02)

Four instructions came back with the Step 1 review, before Step 2. What was done, and what
each one turned out to cost.

### 1. SpaceX covariance: the fit residual, in quadrature

`SPACEX_SGP4_FIT_RMS_KM = 0.20`, on by default, added in quadrature on the diagonal of every
covariance SpaceX's ephemerides serve. The scalar CelesTrak publishes is split across R, I
and C in the shape of the base model's own measured floor — (0.099, 0.994, 0.054) on the
store in hand, so 20 m radial, 199 m in-track, 11 m cross-track. `fit_rms_km=0.0` restores
the as-published behaviour and the model version says which was used
(`spacex-ephemeris/2+sgp4-fit-0.2km`).

Quadrature rather than a floor because the two are independent: SpaceX's covariance is how
well they know where the satellite will be, the residual is how far the element set
driftwatch propagates sits from the ephemeris they published. A floor would treat them as
the same error and keep only the larger.

**The flag tally did not move.** Same 5,704 events, 499 of them served by SpaceX:

| | As published | With the fit residual |
| --- | ---: | ---: |
| Red pairs | 1 | **1** |
| Yellow pairs | 22 | **22** |
| Highest probability | 1.58e-4 | **1.58e-4** |
| Events in the dilution region (all) | 1,021 | **1,021** |
| ... of the 499 served | 37 | **37** |
| Events changing flag | — | **0** |
| Events changing region | — | **0** |

It moves the numbers only at short lead, which is where the argument said it would:

| Lead | Events | In-track sigma before | after | Median probability ratio |
| ---: | ---: | ---: | ---: | ---: |
| 8 to 24 h | 17 | 72 m | **211 m** | **3.63** |
| 24 to 48 h | 92 | 2.50 km | 2.51 km | 1.10 |
| 48 to 72 h | 109 | 2.50 km | 2.51 km | 1.08 |
| past 72 h | 27 | 3.80 km | 3.81 km | 1.05 |

Past a day their published number is a kilometre-scale control box and 199 m in quadrature
is a third of a per cent of it; inside a day it triples the probability. A fifth of the
served events move by more than 10 per cent, 3.5 per cent of them by more than a factor of
two, and the probabilities go **up** rather than down because at these misses the covariance
is small against the miss distance, so widening it moves mass onto the disc.

**The demo run has no short-lead Starlink event near a threshold, so nothing moved.** That is
a property of this run rather than of the term: a run whose window opened on a Starlink
conjunction eight hours out would show it.

Recorded as the **first Phase 4 item** in `ROADMAP.md`: Stage C should interpolate the
SpaceX ephemeris states directly for served events, so the trajectory and the covariance
share a source. This term is the patch for the mismatch, not the fix; when the states are
interpolated the residual leaves the chain and `SPACEX_SGP4_FIT_RMS_KM` goes to zero for
those events.

### 2. The slow-encounter flag: what it rests on

Approved as built, with the basis stated wherever the flag appears — `risk/pc.py`,
`docs/methods.md`, `docs/screening.md`, `docs/data-schema.md` and the report:

- It rests on the **method's straight-line assumption**, not on a measured error. The
  threshold comes from the geometry (at 0.1 km/s a pair takes 100 s to cross 10 km, in which
  a low orbit turns through about six degrees, against a twentieth of a degree at 13 km/s),
  not from a residual.
- **Agreement with ESA on the slow rows cannot detect a bias the two tools share.** The
  Kelvins reproduction matches ESA's operational risk column as closely on slow rows as on
  fast ones, and that is exactly what would be seen whether the shared two-dimensional
  integral is right or wrong there. The size of the underestimate is unmeasured, and the
  flag would stand whether it is a factor of two or of ten.

## Later steps in one paragraph each

**Step 2, density and drag.** pymsis with NRLMSIS 2.x, the ap input vector built correctly
from the table (the daily value plus the three-hourly history it expects); density along
both objects' orbits from element-set epoch to time of closest approach at a documented
step; a ballistic coefficient per object fitted from its own decay history where the
history allows and from B* where it does not, labelled either way; quiet-condition density
at 300, 400, 500 and 600 km reported against published values.

**Step 3, the storm term.** The in-track displacement from a density excess derived and
checked against a numerical integration to a few percent; applied as a mean shift plus a
variance; the covariance protocol extended minimally so a scenario returns the shift beside
the covariance; the quiet scenario bit-for-bit unchanged as the regression baseline; five
scenarios on `driftwatch risk` with full provenance per row.

**Step 4, validation.** Historical snapshots from `gp_history`; May 2024 on both the
density enhancement and the in-track error of pre-storm element sets, with residuals and
any altitude dependence; February 2022 examined and discussed rather than tuned; a replay
run for the demo fleet on the 9 May 2024 snapshot.

**Step 5, viewer.** A storm control switching the panel between scenarios and showing the
change per event; a replay mode with the Kp bar, the density ratio, the Sun image and the
conjunction list moving together; the point cloud untouched, so Phase 1 performance holds.

## Review points

After each step, as in Phase 2. Anything that constrains Phase 4 — the space weather table
schema, the scenario names on `risk`, the export columns the viewer reads — is asked about
before it is built.
