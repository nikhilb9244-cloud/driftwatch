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

## Later steps in one paragraph each

**Step 1, space weather.** CelesTrak `SW-All.csv` cached daily as the primary driver;
NOAA SWPC JSON for the real-time planetary K index, the three-day forecast, the 27-day
outlook and the solar wind, each cached with a floor and stamped with its issue time; one
row per three-hour interval with Kp, ap, F10.7, the 81-day average and a provenance column
saying observed, forecast or synthetic; Helioviewer frames for the replay.

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
