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

> Corrected 2026-09-05: "a floor on the error" overstates it. The consistency of successive fits
> bounds their accuracy in neither direction, because the fits share observations and assumptions
> (`docs/methods.md`, "Uncertainty and probability"). The rule above stands as a rule about the
> *model* — no growth law may undercut a measured disagreement — and not as a claim about the
> truth.

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
   *Answered by the review: keep it as proposed, both F10.7 pairs included. Two columns were
   added on top — `skill` and `ap_sigma` — see "The four instructions" below.*
2. **Layer 4 is CelesTrak's predicted Kp, and that is what covers days four to seven of a
   screening window.** It appears to be derived from SWPC's own forecasts, so it is not an
   independent opinion — it is a smoothed, longer-range version of layer 3. Should days four
   to seven instead be treated as having *no usable geomagnetic forecast*, with the scenario
   machinery (quiet, storm-g3 and so on) carrying that part of the window? That would be the
   more honest position and it is a bigger change than it looks.
   *Answered by the review: do not blank them. They are labelled `recurrence` in the new
   `skill` column instead, and their `ap_sigma` widens to the full climatological spread,
   which says the same thing without putting a hole in the density computation.*
3. **The solar wind is stored but not yet used.** A week of one-minute L1 data is most of the
   store's bulk. It is context for the replay rather than a driver; if it stays unused past
   Step 5 it should be dropped to the one-hour feed.
   *Answered by the review: keep the minute cadence for the last seven days and roll older
   data to hourly means. Done, with the Bz and speed extremes kept beside the means.*

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

### 3. The space weather table: schema kept, four changes

The schema stands as proposed, both F10.7 pairs included. Four changes on top of it.

**`skill` on every layer.** `provenance` says measurement or forecast, which is not enough:
SWPC's three-day Kp and CelesTrak's six-week prediction are both `forecast` and they are not
the same kind of object. The six values are `measured`, `provisional` (SWPC's estimated index,
revised by about a step when it is made definitive), `forecast` (skilful over climatology),
`recurrence` (a coronal hole coming round again, blind to a coronal mass ejection),
`designed` (a scenario) and `none` (a gap). On the live window of 2 September that is 3
provisional, 17 forecast and 37 recurrence — which says plainly that most of a seven-day
screening window rests on a recurrence guess.

**Days four to seven keep their forecast.** Not blanked. A recurrence guess is weak
information but it is not none, and blanking would put a hole in the middle of the density
computation for Step 2 to fill with something. Labelling it and widening its uncertainty says
the same thing honestly, which is what `skill` and `ap_sigma` now do together.

**`ap_sigma`, for Step 3's variance term.** The standard deviation of each interval's ap:

- A measurement is uncertain by the resolution of the index, half a Bartels step — 0.5 nT at
  ap 4, 50 nT at ap 300, because the table is quasi-logarithmic. A provisional estimate
  carries a full step.
- A forecast is uncertain by the part of the climatological spread its skill does not remove,
  `sigma_clim * sqrt(1 - r^2)`, with `r` = 0.85, 0.70, 0.50, 0.40 at leads of 0 to 3 days and
  **zero past three days**, so it widens to the climatological spread exactly as the review
  asked. The lead is measured from the forecast's own issue time where it has one.
- The spread is **measured, not assumed**: the standard deviation of observed three-hourly ap
  over the year before the window. On 2 September 2026 it is 20.0 nT, against a median
  interval of 7 nT. The distribution is strongly skewed and the variance is carried by a few
  storm days, so Step 3 must consume this as a variance on the density and not as an interval
  on the index — one standard deviation below a quiet forecast is a negative ap.
- Floored at half the forecast value, because an ap of 200 nT three days out is not known to
  20 nT. A prior, labelled as one.

The correlation numbers are priors of the right order for SWPC's three-day forecast, not
measured skill scores, and May 2024 was much worse than them. Step 4 is where that gets
tested.

**The solar wind is rolled.** One minute for the last seven days, hourly means before that,
into one archive with the file list that fed it. The archive keeps `bz_nt_min`, `bz_nt_max`
and `speed_kms_max` beside the means, because an hourly mean of Bz averages away exactly the
southward excursions that drive a storm. It is the only place in the store where raw data is
deleted, and it is deliberately not done to the forecast products, whose whole point is that
a stored run can be rescored against the forecast it actually used.

**Deferred to Step 2, as instructed.** The density code reads the **observed** F10.7 of the
**previous day** with the 81-day centred average, which is what NRLMSIS expects, pinned by a
test. That belongs with `drag/density.py` and is done there.

### 4. Housekeeping

Any dev server or shell started during a step is closed at the end of it.

## Step 2 decisions (density and drag, built 2026-09-02)

`src/driftwatch/drag/`, `driftwatch density`, `driftwatch ballistic`,
`docs/density-and-drag.md`, `tests/test_drag.py`. pymsis 0.12 added as a dependency;
NRLMSIS 2.1 is the version and it is recorded in every run.

### The model inputs, which are not the obvious ones

Four things NRLMSIS wants that a careless caller gets wrong, each now pinned by a test:

- **The previous day's** observed F10.7, not today's — the instruction from the review, and
  the model was fitted that way.
- The 81-day **centred** average, which for a forecast needs the predicted flux of the next
  forty days. CelesTrak publishes it; that is why the table carries it.
- The **observed** flux, not the value adjusted to 1 AU. Both are in the table and only one is
  fed to the model.
- A **seven-element ap vector** per sample, read only when `geomagnetic_activity=-1` is
  passed. With the default switch the model uses the daily Ap alone and the storm response
  becomes a smooth daily average — plausible-looking and wrong. The test builds a table whose
  ap is the interval index, so every element of the expected answer is a different number and
  a transposition cannot pass by luck.

A sample whose 57 hours of history the table does not cover comes back NaN. This is what made
the first ballistic run warn: the B\* fallback propagates ten days past an element set's
epoch, past the end of the table the run had built, and the model said so instead of
inventing a quiet day.

### The sampling step, measured rather than asserted

One revolution over 16, tightened for eccentric orbits by their altitude range in scale
heights, clamped to [30, 600] s. Against a 10-second reference over one day:

| Object | e | step | rule error | a fixed 600 s step |
| --- | ---: | ---: | ---: | ---: |
| STARLINK-3520 | 0.0001 | 353 s | -0.03 % | -0.05 % |
| CZ-6A DEB | 0.0070 | 187 s | -0.09 % | -0.36 % |
| FENGYUN 1C DEB | 0.0374 | 35 s | +0.02 % | +0.65 % |
| DELTA 1 DEB | 0.0811 | 30 s | -0.02 % | -0.82 % |
| FREGAT DEB | 0.1521 | 30 s | -0.02 % | **-13.5 %** |
| IUS R/B(1) | 0.7215 | 30 s | -0.02 % | **-17.0 %** |

The eccentricity refinement earns its place exactly where predicted and nowhere else. The
convergence table is reproducible with `driftwatch density --convergence`.

### The density sanity check

Against the US Standard Atmosphere 1976 at its own conditions (F10.7 = 150): 1.35, 1.52, 1.68
and 1.82 times it at 300, 400, 500 and 600 km. Within a factor of two, with the gap growing
with altitude, which is that profile's known bias. The solar-cycle spread the same model gives
is a factor of thirteen at 400 km, so the published value sits comfortably inside the range.
Storm ratios: G3 gives 1.6 to 2.2 and G5 gives 2.7 to 5.7 from 300 to 600 km, growing with
altitude as the physics requires and in the range reported for May 2024.

### Three sources for the ballistic coefficient, not two

The prompt asked for two: fitted from decay, or from B\* converted to physical units. Both are
built. The conversion is the part worth reading.

**B\* cannot be converted by a constant.** It is a fit parameter for SGP4's own atmosphere and
absorbs whatever the fit could not explain; STARLINK-6053's was negative on 2 September, which
as a physical coefficient means an object that accelerates as it flies through air. The
textbook `B = 2 B*/rho0` with `rho0 = 2.461e-5` kg/m^2/ER is quoted in the config and **not
used**: measured against the decay SGP4 itself produces it is wrong by three orders of
magnitude, and the implied constant is not constant — the ISS and YAM-3 at 415 to 420 km imply
0.043 and STARLINK-32515 at 463 km implies 0.0064, a factor of seven apart. So the fallback
propagates the element set with its own B\*, reads the drop off SGP4's **mean** semi-major axis
(`satrec.am`, because an osculating one carries kilometres of short-period wobble and a
long-period drift that over ten days looks exactly like a trend), and inverts that through the
same density model. No constant, altitude-aware, and it inherits exactly as much noise as B\*
has.

**And a third, `typical`.** Sentinel-1A forced it: at 693 km its decay over 45 days is 25 m,
inside the element-set scatter, so there is nothing to fit, and an object whose B\* implies no
decay would otherwise carry B = 0 — which asserts that a storm does nothing to it. Nearly true
at 800 km, plainly false at 500, and the wrong kind of wrong for a risk model. Such objects
take the median of the coefficients **this run actually fitted**, for their own category, and
the label says so.

### What it gives, and why the general form matters

| Object | Altitude | source | B (m^2/kg) | Independent estimate |
| --- | ---: | --- | ---: | --- |
| ISS | 420 km | history, 136 sets, 1 burn excluded | 0.0087 | ~0.0075 |
| YAM-3 | 415 km | history, 123 sets | 0.0121 | ~0.02 |
| STARLINK-32515 | 463 km | history, 105 sets, 7 burns excluded | 0.0059 | ~0.0055 |
| Sentinel-1A | 691 km | bstar | 0.0235 | ~0.029 |
| NOAA-20 | 824 km | bstar | 0.0293 | ~0.017 |
| STARLINK-6053 | 570 km | typical | 0.0100 | its B\* is negative |

Every one within a factor of two, the fitted ones within about fifteen per cent. Two things
had to be right for that. The decay is inverted through the **general** form
`da/dt = -(B a^2/mu) rho |v_rel| (v_rel . v)`, not the circular `-B rho sqrt(mu a)`: an
eccentric orbit does its drag at perigee, and using a mean density with the circular formula
made Vanguard 2 come out 2.3 times too heavy on drag before the change. And ``v_rel`` is
relative to a **co-rotating** atmosphere, which is six per cent of orbital speed and
seventeen per cent of its cube.

### On a population: the categories separate themselves

150 objects of the demo run, 125 fitted from history, 22 from B\*, 3 typical, in seven
minutes. Median B by category: station 0.0087, rocket_body 0.0142, payload 0.0248, debris
0.110. The ordering is the physical one and nothing enforced it — dense station, heavy empty
tube, mixed payloads, light fragments — which is the closest thing to an external check this
step has. The debris tail (0.44 to 0.61 for Cosmos 1275 and Cosmos 249 fragments at 750 to
850 km, radar cross sections of 0.01 to 0.08 m²) implies an area-to-mass near 0.27, a 25 cm
object weighing 150 g: thin plate or multi-layer insulation, which is what those clouds are.
Their decay of 750 m over 45 days cannot be produced by a small coefficient. It is also where
the density model is least certain and where radiation pressure is comparable to drag, so the
tail is good to a factor rather than a per cent.

### The bias that folds in, and the half of it that cancels

Only the product `B rho` is observable from a decay, so a systematic bias in NRLMSIS folds
into the fitted coefficient and **cancels when the same model drives the scenarios** — for the
quiet case. It does not cancel for the storm response, which has no baseline to divide out
against. Two consequences, both now in the docs: the fitted coefficient is preferred over B\*,
and the same model must drive the fit and the scenarios or the cancellation breaks invisibly.
The fitted B is therefore not a measurement of area over mass; it is that divided by the
model's bias over the fit window.

### Questions for the Step 2 review

1. **A third source, `typical`, was added beyond the two the prompt asked for.** The
   alternative for an object with no measurable decay and an unusable B\* was B = 0, which
   says a storm cannot move it. Is the labelled median the right call, or should those objects
   be excluded from the storm term entirely and reported as such?
2. **The fit is slow at catalogue scale.** One density sampling per element-set interval means
   about 100 intervals an object; 150 objects take about eight minutes, so the run's ~3,000
   objects would take hours. Step 3 needs a coefficient for both objects of every event.
   Options: fit only the objects in flagged or near-threshold events; batch the model calls
   across intervals; or cache coefficients across runs by NORAD id, since B changes slowly.
   Which?
3. **45 days of history, 10-day minimum clean span, 50 m minimum decay.** These thresholds
   decide who gets a fitted coefficient and who falls back. They are set from the element-set
   scatter seen on the demo run's objects, not from a formal noise model.
4. **`ballistic.parquet` is a new file in the run directory** and `category` is a new column
   beside the coefficient. Additive; nothing reads it yet but Step 3 will.

## The Step 2 review's four instructions (2026-09-02)

### 1. A typical value by category *and* altitude band

Done, and the bands are new. `config.BALLISTIC_ALTITUDE_BAND_EDGES_KM` cuts at 350, 450, 550,
650, 800 and 1200 km, derived from the element set rather than read off a column. They are
**drag** bands, not the screener's: what one object's coefficient has in common with another's
is the density regime its decay was measured in, and `leo` spans three orders of magnitude of
density. The median narrows as far as the population allows — category and band, then category,
then everything fitted — and the label says which won, e.g. *median of 23 fitted starlink
objects at 450-550 km*. The order of resort is as instructed: history fit, then the B\*
inversion, then this.

### 2. The fit cost, measured before it was changed

Profiled first, on eight objects and 814 fitted intervals (20.3 s unprofiled):

| | tottime | share |
| --- | ---: | ---: |
| `pymsis.calculate` | 12.76 s | 49 % |
| rebuilding the weather grid, per interval | 3.97 s | 15 % |
| propagating the orbit track | 3.92 s | 15 % |

So density evaluation dominates, as the review supposed. But the second line is not density
evaluation at all — it was pandas re-parsing the same unchanged weather table a hundred times
an object, which is now `density.WeatherGrid`, built once and passed down. No approximation,
just not doing the same work repeatedly.

The coarser grid for the fit alone is measured rather than assumed. ×4 costs a history fit
0.65 % at worst and the B\* inversion 3.9 %, against coefficients whose own uncertainties are
5 % and 50 %; ×8 is where the B\* inversion falls apart at 24 %. The B\* route needed the same
treatment because once the budget stops the history fits, every remaining object of a run comes
through it, and at the full step that was the slowest thing in the command.

Only the objects appearing in events are fitted, ordered by the highest probability they appear
in. A four-minute budget bounds the history fits; the rest fall through to B\* and then
`typical`, labelled as always. And the cache is what makes it converge — keyed by NORAD id with
the history span each fit used, invalidated by a week of new history, thirty days of age, a
different NRLMSIS version or a different `BALLISTIC_RULES_VERSION`:

| Run | From cache | Newly fitted | Over budget | Objects with a fitted coefficient |
| --- | ---: | ---: | ---: | ---: |
| first | 0 | 608 | 2,367 | 362 |
| second | 608 | 453 | 1,914 | 670 |

Both under seven minutes for 2,993 objects. Rejections are cached too: finding out that an
object's decay is inside its own scatter costs the same hundred evaluations.

### 3. The thresholds, and what they found

The acceptance rule is now the object's own scatter, as instructed. Excluding the manoeuvre
intervals leaves contiguous *runs* of element sets; a quadratic is fitted **inside each run**
and the pooled residual is the scatter; the decay estimator telescopes to endpoint differences,
so its uncertainty is `scatter × sqrt(2 × runs)` and the decay must exceed it by three.

Inside each run and never across the gap between two, and that distinction was not anticipated:
the first version fitted one curve across the whole window, and the existing burn-exclusion test
caught it reading a 2 km station-keeping burn as element-set noise and refusing a designed fit
the exclusion had just made possible.

**The threshold then surfaced something the old fixed 50 m had hidden.** Deorbiting Starlinks
fit at B near 1 m²/kg off 48 km of decay in 45 days — an area-to-mass no satellite has. The
cause is structural: a continuous low thrust is a *ramp* rather than a jump, so the manoeuvre
detector cannot see it and the fit reads it as atmosphere. Grouping the run's 384 history fits
by the fraction of intervals excluded as manoeuvres, the median B is flat (0.045, 0.018, 0.012,
0.013, 0.014) up to a quarter and then jumps (0.023, 0.260, 0.183). A fit is now refused above a
quarter, which is set from that break.

The rule is on the **exclusions** and not on the coefficient, deliberately: every *debris*
object fitted above 0.5 m²/kg has no exclusions at all, and that light-fragment tail is real.
A cap on B would throw the fragments away to catch the satellites. It is a proxy and it does not
catch everything — STARLINK-65196 has 12 % of its intervals excluded and still fits at 0.69
m²/kg — and that case is named in the docs rather than chased with a tighter number.

Every coefficient now carries `b_sigma_m2_kg`: the statistical error of its own decay for a fit
(floored at 5 %), a 50 % prior for a B\* inversion, the pool's robust spread floored at a factor
of two for a stand-in. Step 3 propagates it.

### 4. Docs and hygiene

- **Published NRLMSIS values added.** The 1976 comparison measures the 1976 profile's bias as
  much as anything of ours. The new one drives our whole chain at the stated drivers of NRL's
  own reference rows for NRLMSIS 2.1 — the file shipped with the model and with pymsis — and
  agrees to better than 0.2 %, which is that file's printing precision. Pinned by a test with
  the rows written out. The rows used are the Ap ≈ 4 ones, because NRL produced the file in the
  daily-Ap mode and `density()` always asks for the seven-element storm-time mode; the two
  coincide at the model's quiet baseline and diverge to +8.9 % by Ap 150, which is measured and
  tabulated beside it and is the reason the vector is built at all.
- **Source maps excluded from the deployed bundle.** `sourcemap: false` in `web/vite.config.ts`.
  They were 9.5 MB of a 12 MB `dist` and they publish the unminified sources with their
  comments. `npm run build -- --sourcemap` turns them back on locally.
- **The two remaining shells were mine and are closed.** Two `npm run dev --prefix web` Vite
  dev servers for this project's viewer (PIDs 38644/52348 and 34840/44456), started at 13:40 and
  13:41 during the Step 1 and Step 2 viewer checks and never stopped. Both killed. The other
  node processes on the machine are a `next start` for an unrelated project and an OpenAI Codex
  runtime, neither of them ours.

## Step 3 decisions (the storm term, built 2026-09-02)

`src/driftwatch/storm/`, `docs/storm-term.md`, `tests/test_storm.py`. The derivation, its
numerical check and the scenario definitions are in the docs page; what follows is what had to
be decided.

### The closed form, and the one that is actually used

`s = (3/4) B drho v² t²` falls out of the mean-motion drift integrated twice, and it matches an
independent Runge-Kutta integration of the same orbit with a step density change to **0.24 % at
worst** (300 km, seven days, doubled density) and better than 0.05 % at 400 km and above. The
error is always the same sign and grows with the decay, which is the approximation being
measured: the closed form holds `v` fixed and the real orbit does not.

But the scenarios use the *weighted* form, `s(t) = (3/2)(n a² B/mu) ∫(t-τ) drho(τ) P(τ) dτ`,
because a storm is not a constant. The `(t-τ)` weight means the same total excess delivered on
day one displaces an object **more than ten times as far** as the same excess on day seven, and
the closed form applied to a window mean cannot express that. This is also why the synthetic
storms use the real May 2024 shape scaled on the Kp axis rather than a square wave, and why the
offset into the window is a stated scenario parameter.

### `quiet` applies nothing, and that is the point

The prompt asks for `quiet` "using observed conditions" and for the Phase 2 quiet scenario to be
bit-for-bit unchanged. These are the same requirement: the Phase 2 empirical covariance was
fitted on real element sets that flew through whatever weather actually happened, so it *is* an
observed-conditions model, and every other scenario is read as a difference from it. So `quiet`
carries no weather table and adds no layer. The protocol makes that free — `mean_shift_ric_km`
defaults to `None` and every Phase 2 model returns it — and the Phase 2 tests pass untouched.

**This is a decision for the review.** The alternative reading, applying the term under observed
conditions, would make the baseline move whenever the density model changed, which is what a
regression baseline must not do.

### The protocol extension is one field

`RicCovariance.mean_shift_ric_km`, `(n, 3)` or `None`. Step 3 only ever fills the in-track
component, but the field is a full RIC vector so a later scenario wanting to move an object
radially does not have to change the protocol again. `run_risk` rotates both objects' shifts into
TEME, differences them, and adds the result to the stored relative position.

**Applying the shift at the stored time of closest approach is exact, not an approximation.** The
encounter plane is perpendicular to the relative velocity, and the component of a shift along
that direction is precisely the part that moves the TCA rather than the miss at it; the
projection removes it. Nothing rescreens and nothing needs to.

### The variance, and the half of it that cancels

Three terms in quadrature, each a displacement passed through the same weighted integral rather
than a fraction scaled off the total. The coefficient's own sigma from Step 2. The density
model's **storm-response** error — 30 %, a prior — rather than its absolute error, because the
absolute part cancels against a coefficient fitted through the same model and only the ratio has
no baseline to divide out against; a `bstar` or `typical` coefficient gets the absolute 15 % in
quadrature with it, because for those the cancellation argument does not apply. And the index,
evaluated rather than differentiated: the whole track is recomputed with every interval's ap
raised by its own `ap_sigma`. The model term is applied **coherently in time**, since a model
bias is not a fresh random number every three hours; summing it in quadrature across samples
would understate it by about fifty over a week.

### Two things the first real run found

**The weather table was not reaching back far enough.** It was built over the *screening window*
plus NRLMSIS's 57 hours, but every shift is integrated from its own object's element-set epoch,
and a run screens on sets up to five days stale. Objects whose epoch predated the table came back
with part of their track NaN and their shifts silently understated — one showed 2,620 of 4,499
samples with no driver. The table is now built back to the earliest epoch in the run; the rerun
has zero.

**The linear theory runs out, and now says so.** The G5 scenario gives a median absolute shift of
278 km, a p90 of 971 km — and a maximum of **106,726 km**, which is two and a half Earth
circumferences. That is a faithful evaluation of the formula for a high area-to-mass fragment at
300 km under a G5, and it is meaningless as a position: such an object is re-entering, not
conjuncting. Every shift now carries the implied decay as a fraction of `a` and the displacement
in orbit circumferences, and is labelled `!extrapolated` past one part in a thousand or a quarter
of a revolution. 53 of 2,993 objects fail it on the G5 run. Nothing is dropped — the number and
the flag travel together.

### What the G5 scenario does to the demo run

2,993 objects, 5,704 events. Median absolute shift 278 km, p90 971 km, 2,675 objects pushed
*ahead* and 318 behind (the behind ones are objects whose own B\* already assumed more drag than
the scenario gives). Median sigma on the shift 199 km. The relative shift moves every one of the
5,704 events, by a median 44 km.

The flag counts **fall**, which was not what I expected to be writing:

| Scenario | red | yellow | median relative shift | p90 | events on an extrapolated shift |
| --- | ---: | ---: | ---: | ---: | ---: |
| `quiet` | 1 | 22 | — | — | — |
| `forecast` | 2 | 11 | 9.8 km | 468 km | 143 |
| `storm-g5` | 1 | 12 | 32.0 km | 505 km | 180 |

**The explanation written here at the time was wrong, and the Step 3 review's own instruction is
what found it. It is left standing with its correction beside it rather than edited away.**

What was written: the storm displaces both objects of most pairs in the same direction by
similar amounts, because they are at similar altitudes with similar coefficients, so only a
small *relative* shift enters the miss — a median 32 km under G5 against a median absolute shift
of 278 km — and a relative displacement of that size separates more pairs than it creates.

Those two numbers are not comparable. The 32 km is a *per-event relative* shift at the time of
closest approach; the 278 km is a *per-object absolute* shift at the end of the seven-day window.
Compared like with like, the relative shift is **1.91 times** the mean of the two objects' own
shifts, out of a maximum of 2 — the opposite of cancellation. See the correction below and
`docs/storm-term.md`. The yellow count does halve, for a simpler reason that needs nothing about
the two shifts being alike.

**Which of the two effects matters, measured rather than asserted.** Over the events above a
probability of 1e-9, the median `pc / pc_variance_only` is well below one and the shift *lowers*
the probability on the large majority of them. On most events the shift is protective and the
variance is what is left. The screening interest is in the minority it raises, and in the tail —
events at 1e-80 under quiet that come back at 1e-7 because the shift moved one object onto the
other. So the honest summary is: **the shift moves more events than the variance does, and in
the safe direction for most of them; the variance is what carries the ones the shift does not
touch.** Both numbers are on every row so a reader never has to take that on trust, and the
review added a third. The figures below are the ones from the rescore after the review's
corrections; the pre-correction numbers were 0.68, 823 and 175 over 998 events.

### The regression assertion, checked rather than claimed

The stored `risk_quiet.parquet` was written before any of this existed. Rescoring it with the
code as it stands and comparing column by column: **every shared column is identical, NaN for
NaN**, over all 5,704 events. The nine columns Step 3 adds are all zero or `none` under quiet.
That is what "bit-for-bit unchanged" was supposed to mean and it is now measured; a test pins
the same property at the `run_risk` level so it cannot quietly stop being true.

### Questions for the Step 3 review

1. **`quiet` applies no storm term at all**, for the regression-baseline reason above. Is that
   the right reading of "quiet, using observed conditions", or should there be a sixth scenario
   that applies the term under the observed record so the two can be compared directly?
2. **The extrapolation flag is a label, not a refusal.** 53 objects on the G5 run have shifts
   outside the linear theory by orders of magnitude, and they keep their probabilities with a
   `!extrapolated` marker. Should those events instead be reported as unscoreable — a dilution-
   like statement — rather than carrying a number nobody should use?
3. **The storm-response uncertainty is a 30 % prior** and it is the largest single term in the
   variance. Step 4 measures it against May 2024. Nothing downstream should be tuned against it
   until then.
4. **A scenario rescore takes about sixteen minutes** for 2,993 objects: two density tracks per
   object from its own epoch to the window end. `--storm-step-s` coarsens it and the same
   argument that justified ×4 for the fit applies, but the default is left at the full step so
   the first reported numbers are not sampling-limited. Should the default coarsen?
5. **`replay:<date>` is built and reachable but not yet meaningful**, because it would pair
   today's element sets with 2024's weather. Step 4's historical snapshots are what make it a
   real scenario.

## The Step 3 review's four corrections (2026-09-02)

The review approved Step 3 and named the finding that a storm *lowers* the probability on most
events, through common-mode cancellation, as the project's headline result. Four corrections
before Phase 4, and all four are hardening rather than new physics.

> **Corrected at the Step 4 review (2026-09-03).** The clause "through common-mode cancellation"
> in the paragraph above is the review's own wording at the time and is left as it was said. It
> did not survive the first of the four corrections it asked for: correction 1 below falsified
> the mechanism while confirming the result. The mechanism is two nearly independent
> displacements separating more pairs than they create. See `docs/storm-term.md`.

### 1. Verify the cancellation, split two ways

The claim is physical: a storm displaces both objects of a pair in the same direction by
similar amounts, so what reaches the miss is the small *relative* shift. The failure mode is
that two objects can also come out alike because they were **handed the same coefficient by the
same rule**. `driftwatch storm-check <run>` splits the relative-to-absolute shift ratio by
coefficient source pair and by the altitude difference between the two objects, and reports the
three probabilities side by side.

**The splits, on the demo run's G5 scenario (5,591 scoreable events) and independently on the
May 2024 replay (1,721 events, observed record, historical catalogue).**

| Split | ratio |
| --- | ---: |
| Overall, demo G5 | **1.91** (p90 1.996) |
| `history`+`history` — two independently measured coefficients | 1.89 (n = 2,942) |
| `history`+`typical` — one measured, one stand-in | 1.93 (n = 2,060) |
| `bstar`+`history` | 1.86 (n = 581) |
| Orbital altitude difference 0–2 km | 1.91 (n = 296) |
| … 10–30 km | 1.90 (n = 2,382) |
| … 30–100 km | 1.89 (n = 513) |
| … over 300 km | 1.86 (n = 45) |
| Rank correlation of the ratio with the altitude difference | **−0.10** |
| Overall, May 2024 replay | **1.87** |

**The splits did their job twice over. They excluded the artefact — independently measured pairs
behave exactly like pairs sharing a stand-in — and they falsified the mechanism.** A ratio of
1.91 out of a possible 2 is not cancellation of any kind: it is two nearly independent
displacements. Three measurements say why, and they agree: the median angle between the two
objects' in-track directions at the encounter is **120°** with a median relative speed of
13.2 km/s (a conjunction between two objects genuinely moving together is rare, because a low
relative speed is what stops two objects closing on each other); the two in-track shifts are
**uncorrelated**, r = 0.08, agreeing in sign 59 per cent of the time; and the ratio is **flat**
in both splits, which is what a quantity set by geometry rather than by coefficients or by the
atmosphere looks like.

The result survives without its explanation. A storm displaces the objects by tens of kilometres
while their misses are a few, and almost any large displacement applied to a near miss separates
the pair. That needs nothing about the two shifts being alike, and it explains the band structure
the effect split shows: the tighter the miss, the more surely a large displacement moves the pair
apart. The median `pc / pc_variance_only` runs 0.88, 0.66, 0.52, 0.49 across bands from 1e-12 to
1, with 403, 450, 512 and 10 events lowered against 79, 71, 93 and 1 raised.

**And the altitude split had to be moved to make it a test at all.** The first version split on
each object's altitude at the time of closest approach, which cannot work: a conjunction *is* a
near-coincidence in position, so the two objects are a median 8 km apart in altitude when they
pass, and the axis has no range. The displacement is accumulated over the window along each
object's own orbit, so the split is on the two orbits' mean altitudes.

The two splits answer different halves of the question, which is why both were asked for. The
source split says whether the *inputs* are shared. The altitude split is the physical
prediction: the density falls by an order of magnitude every 50 km or so, so a pair separated in
altitude sees different excesses and must cancel less. A ratio flat in altitude difference would
have been the artefact.

### 2. Shift-only, variance-only and combined, side by side

Step 3 shipped `pc` and `pc_variance_only`, which separates the two effects only if a reader is
willing to take the shift's contribution as a residual. `pc_shift_only` — the objects moved,
scored against the covariance the run would otherwise have had — is now a column of its own.
The three are not decomposable into one another, because the probability is not linear in
either input, so all three are computed.

`relative_shift_km` is also now a column, and it is a **vector** norm: both objects' in-track
displacements rotated out of their own RIC frames and differenced in TEME. The scalar
difference of the two in-track components, which is the obvious thing to write, is not a
displacement at all — for a crossing geometry the two frames are nearly perpendicular.

### 3. Extrapolated events are unscoreable

Step 3 labelled them `!extrapolated` and reported the number anyway. The review's instruction is
that a number nobody should use should not be printed in a probability column, and it is right:
a marked number is still a number, and a number in that column will be sorted and thresholded.

The cut is the one the review named — the displacement past a fraction of the orbital
circumference, `STORM_MAX_SHIFT_REVOLUTIONS = 0.25`. Such events now carry NaN in every
probability column, `unscoreable` as region and flag, `none` as confidence, the reason on the
row, and are excluded from every aggregate. The decay-fraction test stays as the wider
diagnostic and still marks the covariance source without withdrawing the event.

On the demo run's G5 scenario the cut withdraws **113 of 5,704 events, on 42 objects** — Step 3
reported 53 under the wider test and the coefficients it had then. The 42 are one population:
40 Starlink and 2 other constellation members, 40 of them at 450–550 km, 36 carrying a `typical`
stand-in coefficient because their own decay history is contaminated by station-keeping, with
displacements of 0.25 to 1.27 revolutions. They are operated satellites in the densest, lowest
shell of the constellation, and under a sustained Kp 9 they really are displaced by an amount the
linear theory cannot express — the right answer for them is a re-entry-style integration, which
`ROADMAP.md` already carries as the lifetime-loss item. Under the May 2024 replay, scored against
the observed record rather than a synthetic G5, exactly **one** object crosses the line.

### 4. Continuous thrust

The review's instruction: an object fitting near 1 m²/kg is under thrust, not drag; mark it as
manoeuvring under continuous thrust and use the typical coefficient.

**Implemented with one deviation, and the deviation is what the instruction's own words ask
for.** "Mark those as manoeuvring" cannot be said about debris, and on the demo run the objects
fitting *near the 1 m²/kg cap* are almost all debris: Fengyun 1C, NOAA 16, DMSP 5D-2 F13 and
Meteor 2 fragments with radar cross-sections of 0.002 to 0.03 m² and B\* values a hundred times
a satellite's. For a fragmentation-cloud fragment a high area-to-mass ratio is exactly what is
expected, three independent things say so, and replacing those fits with a population median
thirty times smaller would understate the storm's effect on precisely the objects it moves most.

So the ceiling is **scoped to objects that can thrust** — the manoeuvre prior's own
category-and-group test — and that scoping is what lets the threshold be physical rather than
arbitrary: a satellite's area-to-mass is bounded by its geometry at about 0.05 m²/kg broadside,
so `B = C_D A/m` tops out near 0.11, and `BALLISTIC_THRUST_M2_KG = 0.1` is that ceiling.

The first refit then found the rule was in the wrong half of the code. With the ceiling on the
decay fit alone it caught 66 objects, and Starlinks whose **B\*** inverted to 0.9 m²/kg came
through the fallback untested — B\* is fitted by the element-set producer to the same
thrust-driven fall, so it is not a second opinion. With both routes covered the count is 452,
and the largest coefficient held by any object that can manoeuvre is 0.0995 m²/kg.

After the refit: **1,782 `history`, 1,014 `typical`, 197 `bstar`** of the demo run's 2,993
objects, with **437 marked as manoeuvring under continuous thrust** — 416 Starlink, 18 other
constellation members, 3 payloads, and 391 of them in the 450–550 km band. The unlimited fit
budget is part of that change: the run went from 670 measured coefficients to 1,782 by refitting
everything rather than what fitted in four minutes, which matters because Step 4 then found the
term has no predictive power at all without a measured coefficient.

### And a test that fails loudly on a short weather table

The reach-back bug Step 3 found by accident is now an exception rather than a comment.
`storm.scenarios.check_table_reaches` raises `WeatherTableTooShort` when the table starts after
the oldest element-set epoch needs it to, once NRLMSIS's own 57 hours of ap history are allowed
for, and `shifts_for_objects` calls it before integrating anything. A silently understated storm
term on the stalest element sets in a run is the one error here that looks like a result.

## Step 4 decisions (validation, built 2026-09-02)

Full account in `docs/storm-validation.md`; what belongs here is what was decided and why.

### The order of the two tests is the design

The density enhancement first, because it needs **no ballistic coefficient**: the ratio of an
object's storm decay rate to its quiet one has `B` cancelled out of it, and NRLMSIS predicts the
same ratio independently. If that fails nothing downstream can be believed; if it passes, a
failure downstream is in the coefficients or the linearisation rather than in the weather. The
in-track test second, because it is the one that matters for screening and it depends on both.

### Three disciplines that make the second test a test

**Nothing after the pivot reaches the prediction** — not the element set, not the coefficient.
An element set issued on 12 May already contains the storm. **A quiet control at matched lead
times**, because SGP4 drifts along track quadratically with no storm at all; the control turns
out to be a median 10.2 km over 2.9 days, which is comparable with the storm signal at short
leads and is the difference between a measurement and an artefact. **The later element set is
not truth** — it is another fit, so what is measured is the disagreement between two fits by the
same network, which bounds the propagation error in neither direction (corrected 2026-09-05; this
sentence called it a floor).

### The population is narrowed twice, and both narrowings are stated

Manoeuvring objects out (the term is a claim about drag), then objects whose coefficient was
*measured* rather than inverted from B\* or stood in from a median (the term is the product of a
coefficient and a density excess, so an object with no measured coefficient has nothing in it to
test). Nothing is trimmed inside either population.

That narrowing is not a convenience: over the free-flying population as a whole the predicted
and observed shifts correlate at **−0.10**, which is nothing; restricted to measured
coefficients it is **0.88**. The term is right where it has a coefficient and silent where it
does not, and the label saying which was already on every row.

### What was measured, and what was not changed

- NRLMSIS **over-predicts** the Gannon density enhancement by about 22 per cent, consistently
  across the altitude range: observed median 1.68 against a modelled 2.21.
- The in-track shift is predicted with a correlation of 0.88 and a magnitude between 0.65 and
  1.3 times the observed, depending on the estimator. Both estimators are reported.
- A `B*`-derived coefficient has no predictive power for the shift at all — slope −1.39, which
  is a sharper statement than Step 2's "treat B\* as noisy".
- Below 450 km the term does not apply: that band is nearly all actively controlled Starlink and
  the residual is a hundred sigma. Reported, not fixed.
- February 2022: the public catalogue holds **17 of the 49** satellites lost. The model shows
  the G1's enhancement at 210 km as **16 per cent**, growing to 69 per cent at 500 km.

**Nothing in the storm term was tuned to any of it.** Adjusting a model against the data that
measured it destroys the measurement, and one storm is not a population.

### Questions for the Step 4 review

1. **The storm-response prior.** It is now measured once: a 22 per cent over-prediction with a
   comparable spread. Should `DENSITY_STORM_RATIO_SIGMA_REL` become a bias plus a spread, or
   stay a symmetric prior until a second storm agrees?
2. **The `bstar` population.** Its shifts have no predictive power. Should an object whose only
   coefficient is a B\* inversion be given a *wider* storm sigma, or should its shift be
   withheld the way an extrapolated one now is?
3. **The low-altitude band.** Below 450 km the population is dominated by objects under
   continuous control and the term is not applicable. Should there be an altitude floor on the
   storm term, or is the thrust marking enough?
4. **Survivorship.** Both validation samples are biased against the objects a storm affects
   most. A selection built from SATCAT's decayed objects would reach them; it needs their
   element sets, which Space-Track holds. Worth a pull?

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

**Step 4, validation.** Built; see the section above and `docs/storm-validation.md`.

**Step 5, viewer.** A storm control switching the panel between scenarios and showing the
change per event; a replay mode with the Kp bar, the density ratio, the Sun image and the
conjunction list moving together; the point cloud untouched, so Phase 1 performance holds.

## Review points

After each step, as in Phase 2. Anything that constrains Phase 4 — the space weather table
schema, the scenario names on `risk`, the export columns the viewer reads — is asked about
before it is built.

## The Step 4 review's four corrections (2026-09-03)

The review approved Step 4 and confirmed the correction of the cancellation claim. Four things
before Step 5. None of them changes a number the pipeline computes; three change what is said
about the numbers and one changes what is carried beside them.

### 1. The correction is propagated, not rewritten

Every place that explained the headline result by common-mode cancellation now carries a dated
note beside the old wording rather than a silent edit, following the Phase 2 dilution
precedent. The sites: `docs/design-brief.md` §5 (the operator console's Δ column), the Step 3
review section above, `driftwatch.storm.diagnostics`'s module docstring, `cmd_storm_check`'s
one-line summary, `README.md`'s `storm-check` entry, and `docs/methods.md`, which gains the
corrected mechanism as an entry of its own. `docs/storm-term.md` gains a banner at the head of
the section that did the falsifying. `docs/density-and-drag.md` gains a disambiguating note,
because it describes a *different* cancellation — a density-model bias folding into a
coefficient fitted through the same model — which is unaffected and still stands; the two share
a word and nothing else.

The report and the viewer carried no such string to correct: the report had no storm section at
all until this step, and the viewer's storm mode is Step 5. Both now state the corrected
mechanism where the number appears.

### 2. Storm-term validity on every event

Step 4's sharpest finding was that the term is predictive at r = 0.88 for objects with a
measured ballistic coefficient and has **no demonstrated skill** without one — over the whole
free-flying population the correlation is −0.10. That was reported once, in a validation
document, while every aggregate downstream went on pooling the two populations.

`storm_validity` is now a column on every risk row, taken from the **weaker** of the two
objects' coefficient sources: `validated` when both are `history`, `indicative` when either
rests on a B\* inversion, a stand-in or no coefficient, `none` under a scenario with no storm
layer. The weaker side decides because a relative shift is the difference of two displacements.

Every aggregate is reported over both populations and the combined figure is never printed
alone: `driftwatch storm-check`, the weekly report's new storm section, `run.json`'s per-scenario
record, and Step 5's viewer panel. A test pins that the label changes no probability, no sigma
and no flag — it is a statement about the evidence, and a label that quietly reweighted the
numbers would be a calibration wearing a provenance badge.

**The split immediately found something the combined number was hiding**, which is the
justification for the whole exercise. On the demo run's G5 scenario the median
`pc / pc_variance_only` is **0.16** over the validated events and **0.89** over the indicative
ones. Where the term is validated the displacement lowers the probability by close to an order
of magnitude; where it is not, it barely moves the number. The combined 0.66 is an average of a
large real effect and a near-absent unmeasured one, weighted by how many objects happened to
have a usable decay history — that is, by the coverage of the coefficient fit rather than by
physics. `docs/storm-term.md` carries the table.

Two smaller things fell out of it. The joined `conjunctions.parquet` was carrying `pc` alone out
of Step 3's five probability-and-shift columns, so the report and the viewer — which read that
file, not the risk parquets — could show a storm probability with nothing beside it to say what
had moved it; the storm columns are now in `EXPORT_COLUMNS`. And `RunDirectory.read_risk` fills
`storm_validity` for a run scored before the column existed, because it is a pure function of two
columns every stored table already has. No rescore was needed for either.

### 3. The NRLMSIS bias is recorded and nothing is tuned to it

`docs/storm-validation.md` §1 gains the bias as a record with its sign, size, spread, altitude
dependence and — the part the review asked for — a comparison against the published analyses.

The comparison disagrees, and the disagreement is the reason to write it down. Published
assessments of MSIS-class models at storm time mostly find **under**-estimation; this measurement
finds a 22 per cent **over**-prediction. Four things separate them, and only one favours us: the
published work measures an instantaneous peak against an accelerometer while this measures a
three-day window-integrated decay ratio dominated by the recovery; their satellites sit at 450 to
510 km while half this sample is above 650 km; and the two known biases in this measurement — a
control window that was not solar-minimum quiet, and survivorship against the objects that
decayed — both push the observed ratio down and the apparent over-prediction up. So the honest
statement is that the figure is real for this quantity at these altitudes and that at least three
things inflate it.

`DENSITY_STORM_RATIO_SIGMA_REL` stays a symmetric 0.30 and a test now pins it, so that no later
change can quietly turn the record into a calibration. The config comment that predicted the
prior "is likely to move up" is corrected in place: it moved the other way.

### 4. February 2022, bounded and explained

The coverage limitation is now stated as what it bounds rather than as a fact about the SATCAT.
The public catalogue holds 17 of the 49 satellites and the decay evidence rests on **six of the
thirty-eight lost**, five of which have under a day of element sets. No population statistic is
quoted from them anywhere. What the six do establish needs no population: 79 to 101 km of
altitude lost in under a week at 210 km, against a control group at 500 km losing 8.5 km in six
weeks.

And the 16 per cent enhancement is discussed as the right answer rather than a shortfall. At
210 km the baseline density is three orders of magnitude above the 500 km value, so a modest
multiplier on an already-marginal margin is sufficient; the satellites were in safe mode, flying
broadside with no thrust, while the survivors in the same launch climbed 138 to 149 km over the
following 39 days. The figure sits at the low end of the published post-mortems — Fang et al.
(2022) put the enhancement at 20–30 per cent above the nine days before launch, Lin et al. (2022)
at 50–125 per cent from a physics-based simulation — and nothing is tuned to close the gap. Two
storms measured in opposite directions is two data points and a reason to want a third, not a
calibration.

What the case establishes is narrower and more useful than a model correction: **at insertion
altitude the enhancement is not the warning, the baseline is.**

## Step 5 decisions (viewer storm mode and replay, built 2026-09-03)

The prompt asks for three things: a storm control that switches the panel between scenarios and
shows the change per event, a May 2024 replay with the Kp bar, the density ratio, the Sun image
and the conjunction list all moving together, and Phase 1's performance untouched. The console
specification in `docs/design-brief.md` had already settled how the first should look, so it was
built to that rather than invented a second time — and the brief now records which of its parts
exist and which remain Phase 4.

### The one rule, and what it decided

**The scenario control changes numbers in the panel, not the point cloud.** That is the Phase 1
rule restated, and it settled more than performance. A storm displaces an object *along* the
track already drawn, by tens of kilometres against a covariance of kilometres. Redrawing the
track at the displaced position would assert a precision the covariance denies — the displacement
is smaller than the uncertainty on it for most objects — so the displacement is a number in the
panel and the track is geometry. The point cloud, the propagation worker and the tracks never
learn that a scenario exists.

### `scenarios.json`: an overlay, not a second bundle

The conjunctions bundle is 3.4 MB and carries one scenario. Five of them is 17 MB, and four
fifths of that would be geometry, names and tracks that no scenario changes. So a scenario ships
as **only what it changes**, in columns parallel to the base bundle's `events` and `pairs`
arrays: the browser indexes into them and joins nothing. Label columns are dictionary-encoded
(`{v: [...], i: [...]}`), which took the file from 1.9 MB to 1.25 MB for three scenarios, because
a third of it was `robust`/`history`/`validated` written out thousands of times. Wide numeric
columns went from eight decimals to four significant figures for the same reason.

It is fetched on an idle callback **after first paint** and never on the critical path, so the
base bundle is the size it was before storm mode existed. Until it lands the control is disabled
and says so; if it fails to load the panel says which one scenario is available and goes on
showing it, which is a complete answer rather than a degraded one.

### Two bugs the build found, both about which miss is shown

**The first was silent.** The base bundle's pair rollup summarised by the *geometry's* miss while
the overlay summarised by the *shifted* one, so the miss on a row changed when the overlay landed
even though the scenario had not. ISS versus YAM-3 read 11.466 km and then 3.402 km with no
interaction in between. `normalise()` now derives one `miss_scenario_km` that everything
summarising a scenario reads — the queue, the pair rollup, the report's tables — while everything
describing the geometry goes on reading `miss_km`, and the per-event tables carry both so the
difference is visible rather than chosen between. Under `quiet` they are the same number.

**The second was loud once it was looked at.** The joined `conjunctions.parquet` was carrying
`pc` alone out of Step 3's five probability-and-shift columns, because `EXPORT_COLUMNS` predates
them. The report and the viewer both read that file rather than the risk parquets, so a storm
probability could be shown with nothing beside it to say what had moved it. Fixed by adding the
columns; no rescore was needed, because the join is rebuilt from the stored risk tables.

### Replay is a navigation, and that is the deliberate choice

Replay changes the catalogue: 13,376 objects as they stood on 9 May 2024, against 32,361 today.
Holding two catalogues in memory and swapping the point cloud's buffers would put a second code
path through the one part of this project Phase 1 asked not to be touched, for a mode a reader
enters once. So `?replay` reloads the viewer against `web/public/data/replay/` — one catalogue
alive at a time, the propagation worker's initialisation unchanged, nothing of the replay bundle
fetched until the navigation happens, and a replay becomes a link somebody can send.

The replay bundle is four ordinary exports pointed at another directory plus one new file. That
was a decision too: `driftwatch replay-bundle` writes the timeline and **not** the catalogue or
the conjunctions, because those are `propagate --export-dir` and `report --out-dir` over the
historical snapshot, and a second path for them could drift from the first.

### The scrubber is the clock

There is no second timeline. The Kp bar is drawn as the background of the simulation clock's own
scrubber, and the density readout, the Sun image and the objects all read the same `tMs`. They
move together by construction rather than by synchronisation, which is the only version of this
that cannot fall out of step.

Three smaller decisions inside it. **Kp is read from the interval the clock is inside**, not the
nearest one, because Kp is a three-hour average and the next interval's value is a forecast until
it has happened. **The density ratio's denominator is the Gannon quiet control window**, the same
one Step 4 measured the enhancement against, so the number on screen and the number in
`docs/storm-validation.md` mean the same thing; getting that wrong is how the first build
produced a timeline of NaN, and a baseline table that does not reach the quiet window is now an
exception rather than a silent all-null column. **A Sun frame carries its lag** — Helioviewer
returns the nearest image it holds, which during a data gap is hours away — and the viewer shows
it above fifteen minutes, because a stale Sun with no label would be worse than none.

### The delta column, and where it is suppressed

`docs/design-brief.md` §5 puts `pc / pc_quiet` on every row rather than only the interesting ones,
so that a reader who sees `×0.7` twenty times and `×340` once has learnt the phase's result from
the screen. Built as specified, with one addition the first screenshot forced: a column of
`↑×3.8e+70` is arithmetically true and operationally meaningless. Below **1e-12** — the same floor
`storm-check` bands on, and for the same reason — two probabilities are indistinguishable from
zero and their ratio is noise, so the cell reads an em dash with the reason in its tooltip. Where
one side is below the floor and the other above, it reads `↑ from ~0`, because crossing the level
at which a probability means anything is the statement worth making and an exponent is not.

### What the replay run shows

The control in replay mode offers `quiet` and `observed record, 9 May 2024` and **not** the
synthetic storm levels, even greyed out. A G5 profile dropped into May 2024 would be a different
object from the storm that actually happened, and offering the two side by side would invite
exactly that reading. The numbers: 1,722 events over 1,413 pairs, a median relative shift of
27.4 km, a median `pc / pc_variance_only` of 0.65 over the validated events and 0.78 over the
indicative ones, and exactly **one** event the storm term could not score. Scrubbing to 11 May
gives Kp 9.00 (G5), ap 400, and a density ratio of ×2.33 at 400 km and ×2.84 at 500 km against
the quiet window — which is the same enhancement `docs/storm-validation.md` §1 measures the model
over-predicting by 22 per cent, and it is not corrected for that here either.

### Questions for the Step 5 review

1. **The replay is a page reload.** It is honest and it keeps the point cloud untouched, but it
   loses the scenario selection and the camera. Should it instead be a route with the catalogue
   swapped in place, accepting a second initialisation path through the worker?
2. **`scenarios.json` is 1.25 MB for three scenarios** and would be about 2 MB for five. It is off
   the critical path, but a reader on a phone who touches the control pays for all five at once.
   Should it be one file per scenario, fetched on first use of each?
3. **The storm summary's two populations are shown as columns of a table.** At 360 px that table
   is tight, and Phase 4's console has more room. Is the table the right form, or should the
   validated figure lead with the indicative one as a subordinate note?
4. **The Sun imagery is 10.4 MiB for 29 frames** at four a day over a seven-day window. One frame
   loads at a time, so the cost is per-frame rather than up front, but the bundle is the bundle.
   Fewer frames a day, or smaller images, or is a 360 kB image per twelve hours of replay right?

## The Step 5 review's three answers, and Phase 3 closing (2026-09-03)

The review approved Step 5 and answered the three questions it was asked, closing the phase.

### 1. Replay is a mode, not a reload

**Answered: one application, one live catalogue, the data source swapped in place, preserving
camera, selection and scenario where they still apply.**

Step 5 shipped the switch as a navigation to `?replay`, which was defensible and cost the reader
their camera, their selection and their scenario every time they crossed the boundary. It is now a
mount and unmount inside one live page. `main.ts` creates the globe, the camera, the clock, the
transport bindings and the animation loop once, for the life of the tab; `mountCatalogue` builds
the *catalogue* — bundle, point cloud, worker, frame store, conjunctions panel, storm control,
replay scrubber — and returns a handle whose `unmount` gives back what is worth carrying.

**What carries, and the reason for each.** The camera, because nothing touches it. The position
through the window as a **fraction**: the live and replay windows are the same length two years
apart, so "four days in" is the only part of a 2026 instant that still means anything in May 2024.
The playback speed and whether it was playing. The filters **by name**, not by index — the two
catalogues share a legend today and nothing guarantees they always will, and a carried index would
silently filter the wrong class. The selection **by NORAD id**, because 13,376 objects are not the
same 13,376. And the scenario **per mode**: the first attempt carried one value and lost a reader's
G5 on the way in (replay has no G5) and then could not restore it on the way out, leaving them on
the live run's default having chosen nothing.

**Three things the swap needed that a reload had hidden.** `SimClock` gained a mutable range, so
one clock and one set of transport controls survive the move rather than being rebuilt.
`CataloguePoints` and `ConjunctionTracks` gained `dispose`, because three.js does not free GPU
buffers on its own and a discarded catalogue is 13,000 to 32,000 objects' worth of vertex data.
Every listener a mounted catalogue attaches now goes on one `AbortController`, so unmounting
cannot leave a handler behind to fire against a catalogue that is no longer on screen.

**The worker is replaced rather than re-initialised.** The WebAssembly bulk propagator is allocated
for a fixed object count; a second `init` for a different catalogue would leave the first
allocation resident with nothing to free it. Terminating and recreating costs one WASM
instantiation against a script already in cache, and it guarantees no stale state.

`?replay` still reaches the address bar, through `pushState` rather than a navigation, so a replay
is still a link somebody can send and the Back button still leaves it. Measured in a real browser:
`performance.getEntriesByType('navigation').length` stays at **1** across three switches, the
object count moves 32,361 → 13,376 → 32,361, and the selection, speed, filters and scenario all
come back.

### 2. The Sun ships two or three frames and fetches the rest lazily

**Answered: three eager frames, an inline low-resolution placeholder for every position, the rest
on approach.**

Each frame is now fetched from Helioviewer **twice**: the full 512 px image and a thumbnail of the
same disc. The thumbnail is the identical request at a coarser `imageScale` — no image library, no
second code path, and Helioviewer caches it like any other screenshot. The thumbnails travel
**inline in `storm.json` as data URIs**; the full images stay files.

The size took two measurements to get right, and both are worth keeping. At 64 px a thumbnail came
out at **9.8 kB**, because Helioviewer renders a 24-bit PNG of a noisy image and 64 × 64 × 3 barely
compresses; 29 of those inline is 280 kB of JSON, which is not lean. At 32 px it is **2.9 kB**, and
behind `filter: blur(3px)` at 96 px on screen it is indistinguishable from the larger one. The
second measurement was nearly missed: changing the config appeared to do nothing, because the
thumbnail's cache filename did not include its size and the old files were being served. The size
is now part of the name.

The result: `storm.json` is **121 kB** with all 29 thumbnails in it, against 360 kB for a single
full frame. The exporter marks three frames `eager` — the first, the one nearest peak Kp, and the
last — chosen rather than taken in order, because those are where a reader opens, where they land
when they scrub to "the storm", and the far end of the bar that would otherwise always wait.
Everything else is requested when the playhead comes within six hours, at most one at a time.

**The placeholder is labelled.** A blurred 32 px disc presented as "the Sun at 11 May 12:00" would
be a small lie, so the caption reads `32 px preview, loading…` until the real frame lands. Verified
over a throttled 60 kB/s link: scrubbing to an unfetched frame shows the thumbnail and that
caption immediately, and the full image replaces both about ten seconds later. Entering replay
fetched four full frames, not twenty-nine; a scrub fetched two more.

### 3. The NRLMSIS comparison states which quantity each side measures

**Answered: set the two out side by side so a reader can judge discrepancy against category
difference, and tune nothing either way.**

`docs/storm-validation.md` §1 now carries a seven-row table comparing what is measured, the
observed quantity, where in space, where in time, what is reported, the baseline and the
population — for the published assessments and for this measurement. The short version: they
compare **model density at a point against a spacecraft accelerometer** and report the error in the
storm's **peak**; we compare **model density at a fixed altitude against density inferred from the
decay of an orbit** and report the error in a **three-day integral** dominated by the recovery.

Three things follow, in order of how much they explain. A model that undershoots the main-phase
spike and overshoots the two-day recovery — which is exactly the shape the NRLMSIS 2.1 assessments
describe — produces both results with no contradiction, and **this method cannot test that**,
because it has no time resolution inside its window. Their `rho` is at a place; ours is what an
object flew through, weighted by the drag integral and therefore by perigee, along an orbit that
was itself falling. And their 450–510 km sits at the bottom of our range.

So it is mostly a category difference with a possible discrepancy inside it that this measurement
cannot isolate — and the two known biases here, a control window that was not solar-minimum quiet
and survivorship against the objects that decayed, both make the model look worse than it is. **22
per cent is an upper bound on this quantity's error, not a best estimate.** Nothing is tuned:
`DENSITY_STORM_RATIO_SIGMA_REL` stays a symmetric 0.30 and the test that pins it stays, so a future
reader who resolves the time-resolution problem with better data finds the prior where they left it
rather than half-corrected against a comparison that never justified a correction.

### Phase 3 closes

Six steps, every one reviewed. What it delivered: space weather with per-row provenance and a
stated skill; NRLMSIS density along every orbit with the ap history built the way the model was
fitted; a ballistic coefficient per object from its own decay where the decay is measurable, with
the source on every row; the in-track storm term derived, verified against an independent numerical
integration to a quarter of a per cent, and applied as a mean shift plus a variance through a
minimally extended covariance protocol; five scenarios rescoring stored events with the quiet one
bit-for-bit unchanged; validation against two storms with nothing tuned to either; and a viewer
that switches scenarios and replays May 2024.

Two of those are worth naming as the phase's real content. **A result survived losing its
explanation** — the storm lowers most probabilities, and the common-mode cancellation that was
supposed to be why does not exist. And **a label was added that says how far a measurement
reaches**: `storm_validity`, which turned out to matter by a factor of five on the one number the
phase is about.

`docs/phase4-prompt.md` is written and awaiting review. Nothing in it is built.
