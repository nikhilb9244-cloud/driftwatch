# Phase 4 plan: the shipping phase

The working plan for Phase 4, written the way `docs/phase2-plan.md` and `docs/phase3-plan.md`
were: decisions before the code, results after it, a review section per step, and the wrong
turnings left in beside their corrections rather than edited away. That convention has now
caught three errors that a clean history would have buried. The prompt is
`docs/phase4-prompt.md`.

## What Phase 4 delivers

A public, automated, documented product: a site a stranger can open, a pipeline that keeps it
current with nobody remembering to run it, an export somebody can take away, and a write-up
honest enough to send to people who do this for a living and ask what is wrong with it.

## Prompt additions before the build (2026-09-03)

Three, agreed before any code was written, and committed as `2428587`.

1. **The two parked items are ordered**: commandability first, manoeuvre burden second.
   Commandability because nobody else publishes it, because the console specification already
   reserves the column and renders it as a dash, and because a probability with no pass before
   the encounter is a notification rather than a decision. Manoeuvre burden second because it
   is the number an insurer or a regulator asks for, which is a slower audience, and because it
   is a summary over risk tables that already exist and so loses nothing by waiting.
2. **The write-up gains a section on moving from indicative to operational** — better orbits
   with real covariance — and states plainly that two findings stand regardless of that gap:
   the storm-term validity split, and that the storm term has demonstrated skill only for
   objects with a measured ballistic coefficient. Neither depends on how well the orbits are
   known; better orbits do not supply a ballistic coefficient, only an object's own decay
   history does.
3. **A precondition check before the pipeline step**: a GitHub remote with `main` pushed, the
   four Actions secrets by name only, and `.gitignore` excluding the SpaceX ephemerides, the
   Kelvins dataset and every cache directory. It reports what is missing rather than
   proceeding, and it distinguishes "could not verify" from "absent".

### The precondition check, run 2026-09-03

| Check | Result |
| --- | --- |
| GitHub remote, `main` pushed | **Pass.** `origin` is `nikhilb9244-cloud/driftwatch`; local `HEAD` and `origin/main` were both `89f2ea3`. |
| The four Actions secrets | **Could not verify**, which is not the same as absent. The `gh` CLI on this machine is authenticated as an account with `pull` only on the repository (`{"admin": false, "push": false, "pull": true}`), and listing secret names needs admin, so the API returns 403. Git itself pushes through Windows Credential Manager under a different account, which is why the pull succeeded. Taken as set on the operator's statement; Step 2 will need a `gh` session with admin, or verification through the web interface. |
| `.gitignore` exclusions | **Pass**, checked with `git check-ignore` rather than by reading the file: `data/spacex/`, `data/external/kelvins/`, `data/cache/`, `data/ballistic/`, `data/supplemental/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.wrangler/`, `web/node_modules/`. |

The licence was already in `main` — `LICENSE`, MIT, tracked since `5b903f6` on 1 September —
so there was nothing to pull; GitHub was displaying the file the repository already had.

### The precondition check, re-run at the Step 1 review (2026-09-03, later)

Re-run because the prompt requires it immediately before the pipeline is written, and because
the first check passed item 1 on a state that no longer holds.

| Check | Result |
| --- | --- |
| GitHub remote, `main` pushed | **Fail, and it is a new failure.** `origin/main` is still `89f2ea3`; local `main` is `8bd44c3`, **six commits ahead**. Everything Phase 4 Step 1 built is unpushed, and so is `.github/workflows/supplemental.yml`'s companion setup. `git push --dry-run` succeeds, so the credential is not the obstacle — nobody has pushed. |
| The four Actions secrets | **Still could not verify.** Same 403, same cause: `gh` is authenticated as `nikoloooodeon`, which the API reports as `{"admin": false, "push": false, "pull": true}` on this repository. Listing secret names needs admin. This is not evidence that the secrets are absent. |
| `.gitignore` exclusions | **Pass**, re-checked with `git check-ignore` on each path: `data/spacex`, `data/external` (which holds `kelvins/`), `data/cache`, `data/ballistic`, `data/supplemental`, `data/snapshots`, `data/history`, `data/conjunctions`, `data/weather`, `data/validation`, `data/propagated`, `.wrangler`, `web/public/data/*`. |

**A fourth thing the check found that it was not asked to look for.** The `supplemental-store`
orphan branch **does not exist on the remote** — `git ls-remote --heads origin` returns `main`
and nothing else. `.github/workflows/supplemental.yml` is on `origin/main` and is `active`, but
its first step checks out `supplemental-store`, so every scheduled run would fail at the
checkout; and in fact the workflow has never run at all, the only run in the repository's
history being the `ci` job on the Phase 3 close-out push. That matters for Step 2 beyond its own
sake: the prompt names this workflow as the pattern for persisting state between runs, and the
pattern has not yet been shown to work. The one-off setup in the workflow's own header comment
has to be done before either workflow can be trusted.

**Step 2 is therefore blocked on item 1** and proceeds no further than this. The two review
items below need none of it.

## Step 1. Stage C interpolates the SpaceX ephemeris states directly

Built 2026-09-03. This step turned out to be much larger than the prompt supposed, for one
reason: the prompt sized the error being removed at 0.2 km, and it is not 0.2 km.

### The problem as stated, and the problem as measured

The prompt's framing was Phase 2's: for a Starlink secondary inside the 72-hour ephemeris
horizon, the covariance comes from SpaceX's published file and the trajectory comes from
CelesTrak's SGP4 fit to that file, and the two disagree by the fit's own published residual, a
median 0.20 km. Phase 2 added that residual in quadrature on every served covariance and
called it an admitted patch.

The first thing Step 1 did was measure the disagreement rather than take the published number
for it. Nineteen Starlink satellites, on 2026-09-03, with the ephemeris file and the CelesTrak
supplemental element set fetched within a few hours of each other so that the element set is
the fit to that file and not to an earlier one. Distance between the SGP4 states and the
published states, sampled every 30 minutes across the whole 72 hours:

| Lead | Samples | Median | 90th percentile | Worst | Median in-track | Median radial | Median cross-track |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 to 1 h | 57 | 0.515 km | 1.570 km | 6.7 km | 0.440 km | 0.105 km | 0.111 km |
| 1 to 3 h | 76 | 0.327 km | 0.891 km | 2.9 km | 0.224 km | 0.076 km | 0.106 km |
| 3 to 8 h | 190 | 0.296 km | 0.768 km | 3.5 km | 0.213 km | 0.059 km | 0.112 km |
| 8 to 12 h | 152 | 0.337 km | 1.231 km | 5.2 km | 0.269 km | 0.097 km | 0.135 km |
| 12 to 24 h | 456 | **2.765 km** | 8.712 km | 185.8 km | 2.749 km | 0.153 km | 0.146 km |
| 24 to 36 h | 456 | **11.503 km** | 27.975 km | 582.5 km | 11.496 km | 0.173 km | 0.153 km |
| 36 to 48 h | 456 | **28.306 km** | 66.181 km | 1191.9 km | 28.304 km | 0.241 km | 0.180 km |
| 48 to 60 h | 456 | **51.792 km** | 126.985 km | 2034.0 km | 51.791 km | 0.243 km | 0.313 km |
| 60 to 72 h | 456 | **82.940 km** | 210.787 km | 3099.7 km | 82.938 km | 0.291 km | 0.293 km |

CelesTrak's own published per-object fit RMS on the same day was a median 0.201 km, a 99th
percentile of 0.48 km and a maximum of 10.8 km — and it is not wrong. It is the residual **over
the arc the fit was made on**, which is the first several hours. Beyond that the element set is
being propagated, not fitted, and an SGP4 element set cannot represent three days of a
trajectory containing planned manoeuvres. Almost the whole error is in-track, which is what a
timing error looks like. The worst cases, in the hundreds and thousands of kilometres, are
satellites under orbit-raising thrust.

**Three things follow, and the first two are corrections to the project's own record.**

1. **Phase 2's patch was the right shape at a hundredth of the right size.** 0.2 km is a fair
   description of the first eight to twelve hours and a hundredth of the error at the end of
   the horizon.
   `docs/spacex-ephemerides.md` said the term "bites at short lead and nowhere else", which
   was measured and is true *of the term*; what was not measured was whether the term was the
   whole of the error it stood for. It was not.
2. **Layering SpaceX's covariance on an SGP4 trajectory made days two and three worse, not
   better.** Their published in-track sigma at 72 hours is 3.80 km — a stationkeeping control
   box for the trajectory *they* published. driftwatch's own supplemental-consistency model
   gives 22.8 km at the same lead, which is far closer to the 83 km the propagated element set
   is actually out by. Serving the tighter number for a trajectory it does not describe
   understated the uncertainty on exactly the events furthest out in the window. This is
   recorded as an error in the Phase 3 Step 0 arrangement rather than tidied away; Step 1 is
   the fix, and the fix is to make the covariance's trajectory and the served trajectory the
   same object.
3. **The prompt's Stage B question has no answer in the form it was asked.** It said: Stage C
   refines on interpolated states while Stages A and B screen on element sets, the two differ
   by 0.2 km, so either show the existing pad absorbs it or widen the pad. With a median 83 km
   at the far end of the horizon and a 90th percentile of 211 km, there is no pad. Screening on
   one trajectory and refining on another, tens of kilometres apart, would choose pairs by a
   trajectory they are not then scored on. **So Stage B screens on the served trajectory too.**

### What was built

**The frame, read rather than assumed.** The prompt said to read the frame from the file header
and not to infer it from the covariance's UVW axes. The header does not carry it: it has
`created`, `ephemeris_start`, `ephemeris_stop`, `step_size`, `ephemeris_source` and then a bare
line reading `UVW`, which is the covariance's frame. The state frame is in the **file name** —
every file is `MEME_<norad id>_STARLINK-…`, and MEME is mean equator and mean equinox, of
J2000. That was then checked rather than trusted, because the consequence of being wrong is
large: precession and nutation since J2000 amount to about 0.36 degrees by 2026, some 44 km at
low Earth orbit radius. Six satellites, states compared against SGP4 from their supplemental
element sets:

| Interpretation | Median distance to the SGP4 fit at zero lead |
| --- | ---: |
| States read as TEME | 36.2 km |
| States rotated J2000 → TEME | **0.356 km** |

0.356 km at zero lead is the published fit residual, so the rotated interpretation is right and
the unrotated one is wrong by two hundred times the error the whole step exists to remove. The
rotation is `orbit/frames.j2000_to_teme` and only TEME is ever stored, so no second inertial
frame convention enters the project.

It uses **skyfield** rather than astropy, which reverses Phase 1's arrangement, and the reason
is cost rather than preference: a fetch rotates a few hundred thousand states and astropy's
frame machinery takes 1.74 s per 4,321-state file against skyfield's 0.13 s. The comparison
that justified astropy in Phase 1 is kept as a test — they agree to **0.9 mm** in position —
so the independent check still runs, just not in the pipeline. Skyfield rotates velocity with
the position's matrix and so omits the frame's own rotation rate, worth 0.12 mm/s; that is
stated in the docstring and is a part in 10^8 of a relative speed.

**Hermite interpolation, and the grid chosen by measurement.** `ephemeris/hermite.py`. Cubic
Hermite on position and velocity, because the files give both and velocity is the derivative of
the quantity being interpolated; a Lagrange fit through positions alone throws that away. The
error on a smooth arc is `a (omega h)^4 / 384`, and the held-out measurement on ten real files
matches it closely:

| Stored step | States kept per file | Median error | 99th percentile | Worst (before segmentation) |
| ---: | ---: | ---: | ---: | ---: |
| 60 s | 4,321 | exact at nodes | — | — |
| **120 s** | **2,161** | **5.68 m** | **6.03 m** | 1,112 m |
| 180 s | 1,441 | 22.6 m | 27.3 m | 1,647 m |
| 300 s | 865 | 193.7 m | 214.1 m | 1,990 m |
| 600 s | 433 | 2,462 m | 3,531 m | 3,725 m |

120 seconds is the choice: it halves the store against the file's own step and leaves the
interpolation error a thirty-fifth of the 0.2 km term it removes, while 300 seconds would
reintroduce an error the same size as the one being removed. `SPACEX_STATE_STEP_S` holds it and
every fetch re-measures the error, so a change in the published step size cannot pass unnoticed.

**The 48-hour seam, which was not expected.** The "worst" column above is a thousand times the
median, and it is one held-out point per file — always the same one. It sits at exactly 47.983
hours, which is the sample interval ending at **48 hours after `ephemeris_start`**, in all ten
files measured. It is a discontinuity of a few hundred metres in SpaceX's own product: a seam
between two arcs of the `blend` the header names. Interpolating across it costs more than the
whole exercise saves.

It is not detectable in raw second differences of position or velocity — those are dominated by
the 30 km per step² of ordinary orbital curvature — so the detector is a residual test.
`node_consistency_error_km` predicts every interior node from its two neighbours; on a smooth
arc that is the 120-second Hermite error, 5.7 m, and at the seam it is 150 to 1,100 m. Three
orders of magnitude apart, so the threshold is not a tuning knob: it is 50 m or ten times the
file's own median, whichever is larger. A node's test spans the two intervals either side of
it, so a break in interval `j` shows as the tests at nodes `j` and `j+1` both failing while
their neighbours pass, which localises it to one 60-second interval rather than a neighbourhood
of three. A planned manoeuvre would look the same and is handled the same way.

The stored history is then split into segments at every break, and no interpolant spans one.
With that in place the measured error over ten files is a median 5.6 to 6.0 m and a **maximum
of 6.8 m**: the tail is not smoothed over, it is excluded from interpolation and handed to the
base propagator, which is what "we do not know what happened in that minute" should look like.

A break in the very first or very last interval of a file cannot be seen this way, because
those intervals have a node test on one side only. That is stated in the code and here rather
than papered over.

**Stage B and Stage C both screen on the served trajectory.** `ServedTrajectory` in
`screening/stages.py` holds one answer to "which trajectory served this object at this time"
and both stages use it. Stage B substitutes interpolated states into the vectorised SGP4 grid;
Stage C's `PairEvaluator` substitutes them at every trial time of the root finder, by the same
rule, so a pair chosen on one trajectory is refined on it.

**The jump, and the guarantee re-derived.** The served trajectory is discontinuous at a small
number of instants — at most three per object per run: the start of coverage, the 48-hour seam,
the 72-hour horizon. Stage B's no-miss argument rests on `|d'(t)| <= |v_rel|`, which a jump
breaks. So:

- Every sample interval holding a jump for either object of a pair is marked.
- On a marked interval the detection threshold is **doubled**, from `R + v h / 2` to `R + v h`.
  The half-step in the original comes from a minimum being reachable from *either* endpoint; on
  a marked interval only one endpoint is on each side of the jump, and a one-sided bound needs
  the whole step. That is the widening the prompt asked for, and it is 0.2 % of the pairs rather
  than a global change.
- A candidate on a marked interval is refined by **scanning** the interval on a hundred-point
  sub-grid rather than by root finding, because a discontinuous function has neither a bracketed
  root nor a unimodal minimum. That places the time of closest approach to 0.3 s at a 30-second
  step, against the microsecond tolerance the root finder reaches elsewhere. The events carry
  `refine_method="scan"` and are counted in the run summary, so the coarser treatment is visible
  rather than silent.
- A sampled local minimum is bracketed by the two intervals either side of it, so it is only
  used when neither of them holds a jump.

**The fit residual leaves per event, and it is the screening's record that decides.** The
covariance model no longer adds `SPACEX_SGP4_FIT_RMS_KM` to every served covariance. It adds it
only where the geometry still came from the fit, and which events those are is read from the
`primary_trajectory` and `secondary_trajectory` columns the screening wrote, via
`interpolated_times_from_events`, rather than recomputed from the store. The store is refetched
every eight hours, and a rescore weeks later that recomputed coverage would silently give an
event a covariance that did not match the geometry it was scored on. Model version
`spacex-ephemeris/3`; version 2 was the residual on everything, version 1 was as published.

Making that per-event required one change to the covariance protocol: `RicCovariance.source` may
now be one label per requested time as well as one label for the batch, with `relabel` and
`source_array` to compose and read them. Before this, an object with some events inside the
ephemeris horizon and some past it got the single label `spacex-ephemeris+default:leo` on **all**
of them; now each event carries what actually served it. The prompt asked for
`cov_source_secondary` to be extended rather than a parallel flag added, and this is that.

### What it changed: two runs of the same window, by lead

The report the prompt asks for. Both runs screen the same 2026-09-03 16:06 snapshot over the
same seven days with the same fleet; **run A** screens on CelesTrak's SGP4 fits and carries the
fit residual on every served covariance, which is what Phase 3 shipped, and **run B** screens on
SpaceX's published states and carries the residual only where the fit still served. Events are
matched by object pair and nearest time of closest approach, because the time itself moves.

The ISS's docked visiting vehicles — Soyuz, Progress, Cygnus, Crew Dragon, Nauka, Poisk — are
separate catalogue objects sitting at the same position as the station, so they generate 1,519
events at a 0.2 m miss and 416 of the run's red flags. They have nothing to do with Step 1 and
they would swamp any tally, so they are excluded from everything below and counted once here.

> **Corrected at the Step 1 review, 2026-09-03.** Two things in that paragraph are wrong. The
> list of attached objects is incomplete — three ISS *structural* modules (Zvezda, Unity,
> Destiny) sit on the station's element set too, so it is ten objects and 2,170 events, not
> seven and 1,519 — and the "416 red flags" is not the visiting vehicles' count but what was
> *left* after removing them, which is those three modules. The seven visiting vehicles carry
> 1,112 reds and 407 yellows. Everything in this section that compares run A with run B stands,
> because the attached pairs are identical in both runs; the **flag totals table below does
> not**. See the Step 1 review section below for the corrected table and for
> the structural filter that replaces this by-hand exclusion.

**Totals.** 8,404 events in A and 8,394 in B (6,885 and 6,875 without the docked modules). 300
objects had published states stored; 131 of them had events inside the coverage, and **646
events were refined on the published states**. No event needed the scan refinement: 22
candidates fell in a jump interval and none of them survived to be an event.

**Events gained and lost.** 170 events exist only in B and 180 only in A — and they are not
scattered. Every one of the 170 and 173 of the 180 are on an object whose states served, and
they sit where the two trajectories disagree most:

| Lead | Only in B | Only in A |
| --- | ---: | ---: |
| 0–12 h | 1 | 2 |
| 12–24 h | 11 | 15 |
| 24–36 h | 26 | 25 |
| 36–48 h | 40 | 46 |
| 48–60 h | 54 | 51 |
| 60–72 h | 38 | 41 |
| past 72 h | 0 | 0 |

Past 72 hours nothing changes at all, which is the control: there are no published states there
and both runs are doing the same thing.

**How far the miss moved**, over the 476 matched events served by the published states:

| Lead | Events | Median | 90th pct | 99th pct | Worst | Moved > 1 km |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0–12 h | 117 | 0.159 km | 1.006 km | 4.360 km | 5.895 km | 12 |
| 12–24 h | 143 | 1.571 km | 7.087 km | 12.089 km | 12.720 km | 83 |
| 24–36 h | 90 | 3.399 km | 13.169 km | 21.128 km | 26.354 km | 63 |
| 36–48 h | 86 | 6.975 km | 17.051 km | 24.114 km | 25.816 km | 75 |
| 48–60 h | 28 | 9.086 km | 15.881 km | 17.870 km | 18.147 km | 23 |
| 60–72 h | 12 | 3.361 km | 10.729 km | 16.743 km | 17.456 km | 11 |

The growth is the finding, and it is the same growth as the trajectory measurement that opened
this step — 0.16 km in the first half-day rising to 9 km by two and a half days. It is *smaller*
than the raw trajectory disagreement (0.30 km rising to 83 km) and it has to be: an event only
survives in both runs if the miss stays inside the screening radius, so the largest shifts
destroy the event rather than moving it, and turn up in the gained-and-lost table instead. The
60–72 h bin falls back only because 12 events are left in it.

**How far the probability moved.** An average ratio would be meaningless — `pc` goes as
`exp(-(miss/sigma)^2 / 2)`, so a few kilometres against a sub-kilometre sigma moves it by tens of
orders of magnitude — and most of these events have a probability far below anything anyone would
act on in *both* runs. So: how many carry a probability worth reading at all, and what happened
to those.

| Lead | Served | Negligible in both (`pc` < 1e-9) | Live | Median log10 ratio | 10th pct | 90th pct | Fell ≥10× | Rose ≥10× |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0–12 h | 117 | 116 | 1 | −0.58 | — | — | 0 | 0 |
| 12–24 h | 143 | 140 | 3 | −2.02 | −2.04 | +0.59 | 2 | 1 |
| 24–36 h | 90 | 81 | 9 | −4.50 | −12.97 | +15.71 | 5 | 3 |
| 36–48 h | 86 | 75 | 11 | −1.19 | −16.26 | +14.70 | 6 | 4 |
| 48–60 h | 28 | 22 | 6 | −1.93 | −8.14 | +1.82 | 3 | 1 |
| 60–72 h | 12 | 10 | 2 | −13.73 | −32.53 | +5.07 | 1 | 1 |

Two things to take from it. The great majority of served events are negligible in both runs and
stay negligible: this changes nothing for them. For the 32 that carry a readable probability the
change is not a correction of a few per cent but a different answer — 17 fell by a factor of ten
or more, 10 rose by ten or more, and only two stayed within a factor of two.

**And whether any flag moved. Yes — which is the sharpest way to say what this step did.**

Phase 2 measured its 0.2 km quadrature patch and found that it moved no flag anywhere, and
concluded from that how little the whole class of error mattered. Removing the *error the patch
stood for*, rather than the patch, moves flags:

| | Run A | Run B |
| --- | ---: | ---: |
| red | 416 | **417** |
| yellow | 257 | **255** |
| none | 6,212 | 6,203 |

> **Corrected at the Step 1 review, 2026-09-03.** This table counts the three ISS structural
> modules the by-hand exclusion above missed, and they supply every one of run A's 416 reds and
> 235 of its 257 yellows. Corrected: run A is 0 red and 22 yellow, run B is **1 red and 20
> yellow**. The conclusion below is unchanged and gets sharper — the one red flag in run B is
> the new one.

- **10 matched events changed flag, every one of them on an object served by published states**:
  one `none` → **red**, two `none` → yellow, seven yellow → `none`.
- **5 more flagged events exist only in run B** and **4 only in run A** — events that appear or
  disappear entirely once the trajectory changes, all yellow, all on EOS SAT-1 between 49 and 65
  hours out.

The new red is EOS SAT-1 against Starlink 61705 at a 15-hour lead: the miss falls from 5.479 km
to 2.780 km and the probability rises from 6.19e-6 to **1.076e-4**, across the 1e-4 threshold.
Fifteen hours is not the far end of the horizon, where the trajectory disagreement is tens of
kilometres; it is the near end, where the median disagreement is about 1.6 km. That is all it
took.

> **Corrected 2026-09-05, after an external review.** This red is **in the dilution region at low
> confidence**: its maximum probability over covariance scale factors sits at 0.85 times the
> covariance in hand, so shrinking the uncertainty at the same miss would raise the number, and the
> number is held up by the covariance rather than by the geometry. The paragraph above does not say
> so and should have led with it. Every mention of this event — here, in `docs/writeup-notes.md`,
> in the report and in the viewer — now leads with the region and the confidence. What Step 1
> established is unchanged and narrower than "a red flag": that the choice of trajectory moves a
> dilution-region probability across the red threshold at a fifteen-hour lead, which is more than
> the 0.2 km term Phase 2 was carrying could do.

So the answer to the prompt's question — *say plainly whether removing it does* — is that it
does, and the honest gloss is that Phase 2's "it moves no flag" was a true measurement of a term
that was far too small. The number that bounds how much this class of error matters is not zero.

**Cost.** Stage B went from 195 s to 205 s, a 5 per cent overhead for interpolating 2.4 million
states into the sample grid; Stage C from 2.6 s to 4.2 s. The fetch itself is unchanged at about
26 minutes for 300 satellites, which is download time and is Step 2's problem, not this step's.

### Files

```
src/driftwatch/
  ephemeris/
    hermite.py       new: cubic Hermite on position and velocity, NaN outside the table
    spacex.py        states parsed, rotated, break-detected, thinned, stored; EphemerisTrajectory;
                     the fit residual per event
  orbit/
    frames.py        new: j2000_to_teme
  screening/
    stages.py        ServedTrajectory; Stage B substitution and jump handling; Stage C scan;
                     primary_trajectory and secondary_trajectory on every event
  risk/
    covariance.py    RicCovariance.source may be per-time; relabel, source_array
tests/
  test_hermite.py    new
  test_frames.py     j2000_to_teme against astropy, and the 44 km the rotation is worth
  test_spacex.py     states, frame, breaks, segments, per-event residual, the state store,
                     and the fetch-time frame check in both directions
  test_screening.py  the served trajectory, the jump, and the no-miss guarantee by brute force
docs/
  ephemeris-frame.md new: the frame finding on its own, for anyone else using these files
```

### What the fetch actually produced (300 satellites, 2026-09-03)

`driftwatch spacex` on the demo run's 300 closest Starlink secondaries: 300 of 300 fetched,
648,602 stored states out of 1,296,300 published, 33.9 MB of parquet. 26 minutes, which is the
download; the parsing, rotation, break detection and thinning are 0.17 s a file.

**The interpolation error, over 647,698 held-out states.** Median 5.74 m. Per object the median
is 5.29 to 5.87 m — the spread is the spread of orbital radii, since the error goes as
`a (omega h)^4` — and the 99th percentile per object is 5.9 m. The single worst held-out point
over all 300 objects is 49.4 m, and it is on the one object described below. Against the 200 m
fit residual this replaces, the typical figure is a thirty-fifth and the worst is a quarter.

**The frame check on the real store.** Median 0.3664 km against CelesTrak's SGP4 fits, 90th
percentile 0.757 km, worst 2.34 km, on all 300 objects. That is the published fit residual and
not a frame error, which is what the check exists to distinguish.

**The break census, and it is the interesting part.** 303 breaks over 300 objects:

| Break at | Objects |
| --- | ---: |
| 47.98 h after `ephemeris_start` | **299** |
| 49.40 h | 1 |
| 54.25 h | 1 |
| 62.35 h | 1 |
| 65.28 h | 1 |
| none detected | 1 |

299 of 300 files carry the seam at the same instant, which settles that it is a property of how
the files are made rather than anything the satellites did. The four scattered breaks are one
object each at four different times, which is what a planned manoeuvre looks like, and it is the
right behaviour that the same detector catches both: an interpolant must not span a burn either.

The one object with no detected break, **STARLINK-30405 (57851)**, is also the object with the
worst interpolation error, 49.4 m. That is not a coincidence and it is worth stating plainly:
its seam is gentler than the others and its node-consistency error came out at 49 m against a
tolerance of 57 m — ten times its own median of 5.7 m, and just under the bar. So the detector
found 299 of 300 and the one it missed cost 49 m, which is still a quarter of the term being
removed. The threshold is doing what it was set to do rather than being lucky, but this is where
its margin actually is, and a narrower one would start flagging ordinary arcs.

### Stage A: the pad does not quite absorb it, so nothing relies on the pad

The prompt's instruction was not to rely quietly on the pad, and measuring it showed why. Over
the 300 fetched objects, the published trajectory leaves the mean-element shell by:

| | Median | 90th percentile | 99th | Worst |
| --- | ---: | ---: | ---: | ---: |
| Excursion beyond the shell | 7.6 km | 10.6 km | 20.2 km | **32.6 km** |

Most of that is the ordinary difference between mean and osculating elements, which the 50 km pad
was already sized for. But the pad also has to cover the 35.4 km screening radius, so its slack
is 14.6 km — and 54 of 300 objects exceed that, three of them by more than 25 km. Those three are
raising their orbits: 63885 dips 32.6 km below its mean perigee inside the 72 hours.

So Stage A now takes the **union** of the mean-element shell and what the published states reach,
and the same for the speed bound. The speed comes from the largest speed the states actually
show, which is an exact bound over the span they cover; a vis-viva speed inferred from a perigee
the object never reaches is not a bound on anything. Neither test is ever narrowed, because
outside the ephemeris's coverage the element set still serves.

**What it costs and what it buys:** 4 extra pairs out of 47,974, on four objects, none lost. Tiny
— but it is the difference between a bound and a hope, and the four are precisely the
orbit-raisers whose element sets describe them worst.

### The frame check runs on every fetch, not once in a test

Added at the Step 1 review. The frame finding is only half-safe as a test: what it guards
against is a **change at the source**, and the header does not name the state frame at all, so a
change to the filename convention — or to the frame behind it — would arrive silently.
`driftwatch spacex` therefore propagates the matching supplemental element set to the first
three hours of each fetched ephemeris and compares, **before writing anything**. The two
plausible outcomes are hundreds of metres, which is CelesTrak's published fit residual, and tens
of kilometres, which is a frame error; the threshold sits at 5 km, an order of magnitude clear
of both, so it is not a judgement call. A failure logs the residual, refuses to write the store
and exits non-zero. Where there are no stored supplemental sets to check against, it says it
could not check rather than passing by default — the same distinction the Step 2 precondition
check draws about the Actions secrets.

## Step 1 review: three items before the pipeline, and a fourth that turned up (2026-09-03)

Step 1 was approved with three items attached, and a fourth turned up while doing them.

### 1. The hand exclusion was wrong, which is the argument for not doing it by hand

Step 1's report excluded the ISS's docked visiting vehicles from every tally by listing them:
Soyuz, Progress (two of them), Cygnus, Crew Dragon, Nauka, Poisk — seven objects, 1,519 events.
The list was incomplete. **Three more catalogue objects sit on the station's own element set**:
ISS (ZVEZDA) 26400, ISS (UNITY) 25575 and ISS (DESTINY) 26700, the service module, the first
US node and the US laboratory. They are structure, not visitors, and no rule about visiting
vehicles would ever have caught them. Ten objects, 2,170 events, a median miss of 0.267 m.

Leaving them in did not merely add noise. It **produced the headline flag table**:

| Quiet scenario, event flags | Run A as reported | Run A, corrected | Run B as reported | Run B, corrected |
| --- | ---: | ---: | ---: | ---: |
| red | 416 | **0** | 417 | **1** |
| yellow | 257 | **22** | 255 | **20** |
| none | 6,212 | 6,212 | 6,203 | 6,203 |
| events | 6,885 | 6,234 | 6,875 | 6,224 |

Every one of run A's 416 red flags was one of the three ISS modules, and so were 235 of its 257
yellows. The corrected statement of the Step 1 result is **stronger and much cleaner** than the
one first written: screening on CelesTrak's fits, the demo fleet had **no red flag at all**
outside the station's own hardware; screening on SpaceX's published states it has **exactly
one**, and that one is EOS SAT-1 against Starlink 61705 — **a dilution-region red at low
confidence** (maximum at 0.85 times the covariance; corrected 2026-09-05, see the Step 1 note
above), which is to say a statement about the covariance, not an actionable warning. The rest of Step 1's numbers — the
miss-distance movements, the gained-and-lost tables, the probability ratios, the ten matched
flag changes — are unaffected, because the attached pairs are identical in both runs and
contribute nothing to any difference.

One number is re-derived rather than corrected. Recomputing the ten matched flag changes at
this review, with a greedy nearest-time matcher inside a ten-minute tolerance, gives **one
`none` → red, three `none` → yellow and six yellow → `none`** against the "one, two, seven"
first reported. Ten changes either way, on the same ten events; the single event that moves
between the two categories is a matching-tolerance detail and neither breakdown is being
claimed over the other here. The one that matters is the same in both: `none` → **red**, EOS
SAT-1 against Starlink 61705.

### 2. Attached and co-orbiting objects are filtered structurally

**The rule.** A pair whose separation stays at or under `attached_km` (1 km) for at least
`attached_fraction` (99 %) of Stage B's sampled window is one physical cluster, and its
candidates are dropped before Stage C. Stage B already samples every surviving pair's
separation across the window, so the test is five extra array reductions per chunk and no extra
propagation.

**Why sustained separation and not relative speed.** A relative-speed rule would catch these
pairs too — the ISS and its modules close at 0.3 mm/s — and it would be simpler. It would also
catch the **slow encounters between genuinely distinct objects**, which are exactly the events
the two-dimensional probability is known to underestimate and which `docs/methods.md` records as
the largest error in this project that no comparison available to it can size. Deleting the
events the method is worst at, on a criterion that cannot distinguish them from docked hardware,
would be the wrong kind of tidying. A test pins it: a designed encounter at a 3° crossing angle,
with a relative speed a twentieth of an ordinary one, survives the filter.

**Why a rule and not a list.** A known-attached list would have caught the seven visiting
vehicles, because those are the ones anybody thinks of — and it would have missed the three
station modules for exactly the reason the hand exclusion did. The rule catches what it
measures rather than what somebody remembered.

**Where the threshold came from.** Measured over all 47,974 Stage A survivors of this run on a
300-second grid, the furthest apart each pair ever gets over the seven days:

| Pair | Furthest apart over the window |
| --- | ---: |
| Each of the ten ISS-attached objects | **0.857 m** |
| The tightest genuinely distinct pair (EOS SAT-1 / STARLINK-35843) | 745 km |
| Median over all 47,974 pairs | 13,824 km |

Nothing lies between 0.857 m and 745 km. Every threshold across five orders of magnitude gives
the same ten pairs; a maximum-separation rule and a 99th-percentile rule agree exactly. The
fraction is kept rather than the maximum so that one bad sample — a stale element set, a served
trajectory's jump at a file's 48-hour seam — cannot rescue a pair that is otherwise permanently
attached. 1 km sits a thousandfold clear on each side, which is the only defence a threshold
needs.

**Visible and reversible.** The excluded pairs, with their closest, mean and furthest
separations and the fraction of the window they spent below the threshold, go into the run's
`run.json` under `attached_excluded` and into a section of the report that is written whether
the filter fired or not, and whether it was on or off. `driftwatch screen --keep-attached`
restores the events; `--attached-km` and `--attached-fraction` move the thresholds.
`docs/screening.md` has the derivation, `docs/methods.md` the approximation.

**What it removes from a normal run.** The same fleet, snapshot, window and supplemental
version as run B, screened again with the filter on:

| | Filter off (run B) | Filter on | Removed |
| --- | ---: | ---: | ---: |
| Events | 8,394 | **6,224** | 2,170 (25.9 %) |
| Event flags: red | 1,529 | **1** | 1,528 |
| Event flags: yellow | 662 | **20** | 642 |
| Event flags: none | 6,203 | 6,203 | 0 |
| Pairs flagged red (the report's own count) | 11 | **1** | 10 |
| Pairs flagged yellow | 15 | 15 | 0 |
| Report's "closest approach" | 0.000 km | **0.138 km** | |
| Report's "highest probability" | 2.77 × 10⁻¹ | **1.08 × 10⁻⁴** | |

The last two rows are the reason this could not be left to a hand exclusion in the analysis.
The report's headline numbers — the two a reader looks at first — were a miss of zero and a
probability of 0.28, and both were the ISS's own service module.

**Every red flag but one was attached hardware.** That is the finding, and it is the answer to
"how many flags does it remove": 1,528 of 1,529. The one that survives is EOS SAT-1 against
Starlink 61705, the flag Step 1 produced.

The filter is surgical rather than merely large. The two runs' event tables were compared by
event id: **2,170 ids present only in the unfiltered run, none present only in the filtered
one**, and the 6,224 shared events are bit-for-bit identical. Dropping the candidates before
Stage C changes the refinement of nothing else, which is what a test asserts as well as this
run.

The excluded objects, exactly as they appear in the report:

| Excluded object | NORAD | Closest | Mean | Furthest apart | Window below 1 km |
| --- | ---: | ---: | ---: | ---: | ---: |
| ISS (ZVEZDA) | 26400 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| ISS (UNITY) | 25575 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| ISS (DESTINY) | 26700 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| ISS (NAUKA) | 49044 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| POISK | 36086 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| SOYUZ-MS 29 | 100057 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| PROGRESS-MS 33 | 68319 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| PROGRESS-MS 34 | 68837 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| CYGNUS NG-24 | 68689 | 0.198 m | 0.431 m | 0.862 m | 100 % |
| CREW DRAGON 12 | 67796 | 0.198 m | 0.431 m | 0.862 m | 100 % |

All ten give the same three numbers to the millimetre, which is the clearest possible statement
of what they are: ten catalogue entries propagating one element set. (The threshold table above
says 0.857 m rather than 0.862 m because it came from a 300-second diagnostic sweep; the run's
own grid is 30 seconds and catches a slightly higher peak. Nothing turns on the difference.)

> **Why the runner dropped nothing, explained 2026-09-05.** Both runner runs (2026-09-03 19:11
> and 2026-09-04 11:18) reported the same ten pairs excluded and **no candidate dropped**, and
> "never more than 0 m apart"; this run dropped 2,170 candidates at 0.198 to 0.862 m. It is the
> input, not the machine. On the afternoon of 2026-09-03 both Space-Track and CelesTrak carried
> the station's own record at TLE precision — eccentricity 0.0005015, seven decimals — and the
> ten attached objects' records at eight (0.00050146), same epoch: one element set, two copies
> four units apart in the eighth decimal, which propagate 0.27 to 0.58 m apart, once an orbit, so
> Stage B finds a closest approach on every orbit and the filter has 217 candidates a pair to
> drop. By the time the runner fetched, the whole cluster was on one copy to the last digit: the
> separation is exactly zero, the range rate never changes sign, Stage B has no candidate, and
> the filter reports the pair attached with nothing to drop. Both are the filter working, and
> `tests/test_screening.py` now pins both readings (the twin on the same set, the twin four units
> off in the eighth decimal). The remaining question — whether the same snapshot gives the same
> events on both machines — is answered in `docs/pipeline.md`, "Reproducibility".

**Cost.** Stage B went from 205.1 s to 239.8 s, a **17 per cent overhead** for five array
reductions per chunk per primary group over the same separations Stage B already computes. Read
that as an upper bound rather than a measurement: the two runs were not alone on the machine and
this one shared it with the test suite. Even taken at face value it is 35 seconds on a
ten-minute screening, against storm scenarios that cost sixteen minutes each, so it is not worth
optimising before Step 2 has measured the whole run. It is recorded because Step 2's constraint
is runtime and because there is an obvious fix if it ever matters: the reductions are over the
full
`(pairs, samples)` block for all 47,974 pairs at every step, and a pair can be **disqualified
permanently** once `(samples below so far + samples remaining) / total` falls under
`attached_fraction`. The first chunk is 235 of 20,161 samples, so any pair not already below the
threshold throughout it can never reach 99 % and drops out — which leaves ten pairs out of
47,974 to keep accumulating for. Stage C fell from 4.2 s to 3.7 s, having 2,170 fewer candidates
to refine.

### 3. The mixed covariance case, tested rather than waited for

The prompt's Step 1 asked for the SGP4 fit residual to be removed **per event**, and it is:
an event refined on the published states gets SpaceX's covariance as published; one whose
geometry still came from CelesTrak's fit carries the 0.20 km residual in quadrature and is
labelled `spacex-ephemeris+sgp4-fit`. Checking the review's question — has that second label
ever actually been produced? — the answer is **no**:

| `cov_source_secondary`, run B, quiet | Events |
| --- | ---: |
| `empirical` | 3,924 |
| `supplemental:beyond-horizon` | 3,334 |
| `spacex-ephemeris` | 646 |
| `supplemental:consistency-prior-p1.5` | 395 |
| `supplemental:consistency-prior-p1.5+beyond-horizon` | 65 |
| pooled fallbacks | 30 |
| **`spacex-ephemeris+sgp4-fit`** | **0** |

Sixteen objects had events served both ways, so the *trajectory* label is genuinely mixed. But
every unserved event on those sixteen sits at a lead of 65.7 hours or more, past the end of the
object's own ephemeris, so the covariance falls through to the base model and the event is
labelled `supplemental:beyond-horizon` rather than `spacex-ephemeris+sgp4-fit`. The two horizons
— the covariance's and the states' — coincided on every file in this run, so the partial path
had nothing to do.

It is not dead code. A file's covariance covers its full 72 hours while its stored states are
split at every discontinuity, and 299 of the 300 files fetched carry a seam at 47.98 hours; a
time of closest approach inside a seam has SpaceX's covariance and CelesTrak's trajectory. The
same holds if a fetch stores covariance for an object whose states fail to parse. So the path
is real, rare, and until now exercised only by a unit test on the model in isolation.

`tests/test_spacex.py` now runs it end to end. One Starlink secondary meets the primary twice an
orbit for a day; its states are stored for the first twelve hours and its covariance across all
twenty-four. The whole chain runs — the screening writes `secondary_trajectory`,
`interpolated_times_from_events` reads it back, the model decides per event, `run_risk` labels
the row — and it produces **18 events labelled `spacex-ephemeris` and 15 labelled
`spacex-ephemeris+sgp4-fit` on the same object**, with the in-track sigma differing by exactly
the quadrature term. The test asserts the labels follow the trajectory event by event and not
object by object, which is the property Step 1 changed and the one that would break silently.

### 4. A shadowed variable meant no Step 1 run recorded its own snapshot

Found while wiring the exclusion record into `run.json`. `cmd_screen` assigns the catalogue
snapshot to `path`, and the supplemental loop then assigned the *stored supplemental file* to
the same name:

```python
path = Path(args.snapshot) if args.snapshot else snapshot.latest_snapshot(config.SNAPSHOT_DIR)
...
    path, written = supplemental_mod.store_supplemental(records, ...)   # shadows it
...
run_dir.write_run({"snapshot": path.name, ...})                        # the wrong file
```

Both Step 1 runs therefore recorded `snapshot: starlink_20260903T152308Z.parquet`, which is a
supplemental element-set file and not a snapshot at all. The consequence is not cosmetic:
`elements_for_run` looks the recorded name up with `snapshot_file`, which searches the snapshot
directories and raises, so **`driftwatch report` could not rebuild either Step 1 run** —
confirmed by running it and getting `FileNotFoundError: snapshot
'starlink_20260903T152308Z.parquet' is in neither ... nor ...`. And Step 2 is required to fail
loudly on a snapshot older than a set age, which it cannot compute from the name of a different
file.

The shadowing dates from `343660d` (Phase 3 Step 0, 2 September) and the 1 September run
predates it and records `gp_20260901T204841Z.parquet` correctly, which is how it was dated. The
loop variable is now `stored_path`, with a comment saying why it must not be `path`. The two
stored Step 1 runs were repaired in place, with the correction recorded in their own `run.json`
under `corrections`, and `driftwatch report` rebuilds them again.

## Step 2. The daily pipeline (2026-09-03)

`docs/pipeline.md` is the design document the prompt asked for -- the runtime budget, the state
inventory, the retention rule and the failure model -- and `.github/workflows/pipeline.yml` is
the workflow. This section records the decisions and what testing them cost.

### The persistence pattern, proved in isolation before anything was built on it

The prompt names `.github/workflows/supplemental.yml`'s orphan branch as the pattern for
persisting state between runs. It had never worked, and testing it produced four findings.

**The branch did not exist.** `git ls-remote` returned only `main`. The one-off setup lived in a
comment at the head of the workflow, which is the same as not existing, so every scheduled run
would have failed at the store checkout -- and the first cron firing after the workflow reached
`main` did exactly that, at 18:16 UTC, before this work reached it. The job now creates the
branch itself, in a scratch directory with its own `git init` so the first commit is genuinely
parentless and the main working tree is never touched by an orphan checkout.

**Two dispatched runs proved both halves.** Run 1 created the branch and stored one version.
Run 2 read it back: one version in the checkout, the Actions cache restored from run 1's key,
`Using cached 'supplemental/starlink' (age 0h02m)`, nothing refetched, nothing committed.

**The fetch cache was not persisted at all, which quietly defeated CelesTrak's two-hour floor.**
A fresh runner has no cache, so every run refetched, and `store_supplemental` names versions by
fetch time rather than by content -- two runs an hour apart would have stored two near-identical
0.74 MB files. Committing the cache instead would have been worse: the supplemental payload is
**5.1 MB of JSON per fetch**, seven times the parquet it produces. So the state is now split by
character: the store on the branch, the cache in the Actions cache, where eviction costs one
polite refetch and never any data.

**Branch-as-storage cannot stay small, and pruning does not help.** Measured locally: three
supplemental versions committed in sequence cost 2.19 MB of `.git` for 2.22 MB of files -- zstd
parquet deltas against nothing -- and deleting two of them left `.git` at 2.19 MB.
`prune_supplemental` thins the checkout and reclaims **nothing** from the history. At eight runs
a day that is 5.9 MB/day and about 2.2 GB a year. The branch is therefore rebuilt from its own
tip past a commit threshold: same tree, one commit, no history. Nothing that matters is lost,
because every stored version is named by its own fetch time -- the store is its own log.

**And the compaction trigger could never have fired.** `actions/checkout` clones the store at
`fetch-depth: 1`, which is what keeps every run cheap however long the branch gets, so
`git rev-list --count HEAD` reads 1 for ever. Found by running it: the step reported
`1 commits, limit 1` on a branch that had two. The counter is now a file in the store, which is
shallow-clone-proof and needs no API call. A third dispatch with the threshold forced to zero
compacted the branch for real: it is now a single parentless commit holding the `.gitignore`,
the README, the counter and the stored version, confirmed from a local fetch.

A fourth thing the same step nearly did: `git add -A` in the compaction would have swept the
restored Actions cache -- those 5.1 MB of JSON -- into the very history the step exists to
prevent. `--orphan` keeps the index, so the right tree is already staged and no `add -A` is
wanted. The store branch also carries its own `.gitignore` now, so no future step can do it by
accident.

### Why the run archive is not on a branch

The retention rule added at this review is that **every daily run is kept**, so that warning
stability can be measured later. That decides the storage, because a run directory is 4.8 MB and
a snapshot 3.8 MB: **8.6 MB a day, about 3.1 GB a year**. Compaction bounds a branch's history to
its tip, but the tip *is* 3.1 GB after a year, past what GitHub asks a repository to stay under.

Release assets are not stored in git at all -- they do not count against the repository, each may
be 2 GB, and a release may carry any number. One release a month, one compressed run a day, is
145 MB a month in objects that never touch a clone. **Cloudflare R2** would also work and the
project has the account, but it needs a bucket, a token scope this project's Cloudflare token
does not have, and a second place to look for data; the release asset needs `gh release upload`.

The threshold at which that stops being true is worth stating: a fleet ten times larger is about
50 MB a day and 18 GB a year, which is where an object store becomes the answer rather than the
alternative. **The archive as designed is good to about a tenfold growth in fleet size.**

### The schema warning stability needs, and the reason it is a report rather than a build

Reported in `docs/pipeline.md` and deliberately not implemented. The substantive finding is that
**`event_id` cannot join runs**: it is `<snapshot stamp>:<primary>:<secondary>:<tca to the
minute>`, and the snapshot stamp changes daily by construction while the time of closest approach
itself moves as the orbits are refitted. The series has to be assembled on the object pair plus
the time of closest approach within a tolerance -- the same greedy nearest-time match the Step 1
comparison used, and delicate in the same place, a pair with repeated close passes.

Every column such an analysis needs is **already written** by `events.parquet` and
`risk_<scenario>.parquet`, so no schema change is required. What a later phase should add is a
narrow per-run *stability slice* so the analysis need not open 365 run directories to follow one
pair. That file is not being created now.

**Built at the Step 2 review, 2026-09-03 (later).** The slice is no longer a later phase: the read
path is `data/stability/<fleet>/<run_id>.parquet` and `driftwatch stability`. See "The read path
warning stability needed" below. The analysis is still not built.

---

## The read path warning stability needed (Phase 4, after the Step 2 review, 2026-09-03)

Step 2 reported the schema and built nothing, on the grounds that the storage decision could not be
made retrospectively but the analysis could wait. The half that could not wait is the **read path**:
every run is archived as a 4.8 MB release asset, so answering "how did this warning evolve" meant
downloading a month of archives and opening them one at a time. That is not a question anyone asks
twice. `src/driftwatch/stability.py`, `driftwatch stability`, `tests/test_stability.py` and the
schema in `docs/data-schema.md` are the answer; `docs/pipeline.md` carries the design.

### What it is

One narrow file per run, `data/stability/<fleet>/<run_id>.parquet`, on the store branch rather than
in the release archive, holding one row per encounter per run per scenario: the identity, the lead
time, the time of closest approach and how far it moved, the miss distance, the probability and the
flag, with the covariance and trajectory sources beside them. The pipeline writes it after the
deploy and before the archive, so nothing is indexed that was not published and the archived
`run.json` records what the run contributed.

### Identity, measured rather than argued

The Step 2 report's substantive finding stands: `event_id` cannot join runs. A series is assembled
on the object pair plus the time of closest approach within a tolerance, greedily, nearest first,
one event to one series. The tolerance was set at ten minutes from the half-orbit argument -- and it
is now checked against two real runs whose windows start 43 hours apart, indexed one after the other:

| | |
| --- | --- |
| Series continued | **1,756** |
| Time of closest approach moved, median | **0.3 s** |
| 95th percentile | **4.5 s** |
| Largest | **20.8 s** |
| Tolerance | 600 s |
| Gap between successive passes of one pair | ~2,760 s |

Thirty times inside the tolerance and a hundred times clear of the thing the tolerance has to
separate it from. Every row carries its own `dt_tca_s`, so this stays checkable from the files as
the pipeline runs rather than resting on this table.

The read path shows the intended thing immediately. `driftwatch stability --pair 55053,61705` over
those two runs prints EOS SAT-1 against Starlink 61705 as **five distinct series**, one per pass,
47 minutes apart and never confused with one another -- and one of them is a warning that
evaporated:

```
55053-61705-20260904T0844Z  scenario quiet  2 runs
   20260902T065806Z-38c7    2.50 d   20260904T084455Z       -     16.394   1.052e-05  yellow
   20260903T175632Z-9a31    0.69 d   20260904T084451Z      -4     22.981   4.323e-25  none
```

A yellow flag at a two-and-a-half-day lead, gone at seventeen hours, with the time of closest
approach having moved four seconds. **It is not evidence about warning stability**, and the write-up
must not use it as such: those two runs differ by more than a day, because Step 1 changed what the
Starlink secondaries are screened on in between. It is evidence that the read path answers the
question in the form the question is asked.

### Two decisions worth defending

**Every event is indexed, not the flagged ones.** The tempting saving is to keep only what flags,
or only what comes within a few kilometres. Measured over these runs, flagged events have miss
distances from **0.53 km to 28.3 km** -- the whole screening volume, because the flag is decided by
the covariance and not by the miss. There is no cut that admits the warnings. Worse, an event first
indexed on the day it flags has no history behind it on that day, which is exactly the failure the
index exists to prevent, and it cannot be repaired later. What is cut instead is scenarios: `quiet`
and `forecast`, the two that are statements about the actual window.

**One immutable file per run, not one file rewritten.** Git keeps every version of a rewritten file
in full, so a monthly file rewritten daily costs roughly fifteen times its own size in branch
history; a per-run file costs its size once. Measured on the 2026-09-03 run: 231 KB for one
scenario over 6,224 events and **330 KB for two** -- 27 bytes a row, because the second scenario's
rows repeat the first's identity columns and compress against them -- against the 8.6 MB a day the
archive already costs. A test pins the byte budget, because a column added without thinking is a
year of files.

### The step the pipeline was missing, found by timing it

Timing the steps for the runtime report turned up a plain fault: **`.github/workflows/pipeline.yml`
never ran `driftwatch ballistic`**, and every scenario but `quiet` refuses without a ballistic
coefficient per object -- deliberately, since a missing coefficient would otherwise move nothing and
produce quiet numbers under a stormy label. The first scheduled run would have failed at
`risk --scenario forecast`, after publishing, on every run. Nothing caught it because the workflow
had never been run end to end and no test covers the workflow file. The step is now in, before
`Score every scenario`, and deliberately **not** with `--offline`: the historical ap and F10.7
table lives in the fetch cache, which the Actions cache may evict, and an offline fit without it
does not fail -- it returns NaN density and rejects every object, which is the silent degradation
this project keeps refusing. Fetching hits CelesTrak's two-hour floor and costs nothing warm.

---

## Step 2A preparation: the Office of Space Commerce dataset, read before anything is fetched (2026-09-03)

The prompt requires the user's guide to be read and the terms confirmed **before** anything is
downloaded or redistributed. This section is that reading, plus the decomposition question the
20.73 GB tarball forces, and it is written before a byte of the dataset has been fetched.

Source: the download page (`space.commerce.gov/dataset-for-conjunction-assessment-verification/`)
and the user's guide, *Conjunction Assessment Verification Data and Process*, Auman, Murphy and
George (The Aerospace Corporation), March 2026, 10 pages, fetched and read in full.

### The terms, confirmed

**CC0-1.0, stated in the guide itself** and not only on the download page: "These data are
available on a full and open basis, with no restrictions on use or dissemination, under the
Creative Commons Universal Public Domain Dedication (CC0-1.0)." A derived subset may therefore be
redistributed -- unlike the SpaceX ephemerides, which `check-bundle` exists to keep out of the
published site. Access is a Google Drive link behind a Google Form (email address entered by
hand), with `TraCSS.Outreach@noaa.gov` as the route for anyone who cannot use a Google account.

**The caveat, verbatim, for the write-up**: "This data was not evaluated (nor is it intended) for
use in live operations or as a tool for formal system certification or validation." The guide adds
a second one that matters as much: the answer key was generated by Aerospace's own CSieve, "that
is expected to find nearly all the events within the dataset, but we cannot guarantee exhaustive
results", and the test set "should only be used as a diagnostic tool for self-evaluation."

### The structure

| File | Guide | Download page |
| --- | ---: | ---: |
| `AerospaceIVVDataset_20251009a.tar.gz` (ephemerides) | 21.74 GB | 20.73 GB |
| `IVV_Releasable_Dataset_Spherical_DefaultHBR.csv.gz` (answer key 1) | 204 MB | 198.8 MB |
| `IVV_Releasable_Dataset_SFSH_DiscreteHBR.csv.gz` (answer key 2) | 144 MB | **62.4 MB** |
| `AerospaceIVVDataset_20251009a_Size_ScreeningVolumes.csv.gz` (volumes and HBR per object) | 145 KB | 145 KB |
| `Conjunction_Screening_Testset_Users_Guide.pdf` | -- | 363 KB |

The first two disagreements are GB-against-GiB. **The SFSH one is not**: 144 MB against 62.4 MB is
a factor of 2.3, so either the file was reissued after the guide was written or one of the two
numbers is wrong. Check the file's own size on download before quoting either.

**Inside the tarball**: OCM-formatted ephemerides -- Orbit Comprehensive Message, the format
TraCSS will itself publish and accept -- spanning roughly the first week of January 2025, with the
screening window fixed at **2025-01-01T12:00:00Z to 2025-01-08T12:00:00Z**. The guide says the
ephemerides "may be grouped into different directories based on object type", and object type is
readable from the catalogue id alone:

| Ids | What | Count |
| --- | --- | ---: |
| 00005-62461 | TLE-derived, from the public Space-Track catalogue on/around 1 Jan 2025, with COVGEN covariance | the catalogue |
| 90006-90190 | Synthetic manoeuvring ephemerides and the "victims" generated to conjunct with them | 185 ids |
| 95000-95407 | Historical CDMs: the state and covariance at TCA propagated forward and back into an ephemeris | 408 ids |
| 99000-99008 | Fictitious objects and victims, for requirements the others do not cover | 9 ids |
| 99996-99999 | OSIRIS-REx sample return capsule (99999) and victims: a reentering, heliocentric object | 4 ids |

Two structural details that will bite an implementation: some ephemerides **start or end inside
the window** and carry their own usable start/stop times, which a tool must honour; and one object
designator can have several **candidate OCMs** -- a nominal trajectory plus mitigation manoeuvres --
which must be screened against everything else but never against each other.

### Does it decompose? Yes by file, no by test.

**By file, yes.** It is one OCM per object (per candidate), so the members can be selected by name.
But a `.tar.gz` is a single gzip stream with no index, so there is **no random access**: extracting
a whitelist means streaming the whole archive once and discarding what is not wanted. That makes
the 20.73 GB a **transfer cost paid once and a storage cost never paid** -- `curl ... | tar -xz`
with a member list writes only the selected files, and the source sha256 can be computed in the
same pass. It does not make it free, and a Google Drive object of that size is not reliably
`curl`-able (confirmation tokens, per-file quotas), which is an argument for doing the one pass
from a machine that can retry rather than from a runner.

**By test, no, and this is the constraint that actually decides the step.** The guide requires an
**ALL vs ALL** screening: every ephemeris against every other. driftwatch screens a fleet of
primaries against a catalogue, and its cost is set by Stage B, measured at **187 to 240 s for six
primaries against a 22,646-object catalogue over a seven-day window** -- 47,978 pairs surviving
Stage A out of 135,876 offered. All-vs-all over a catalogue of that size is ~3.4 x 10^8 pairs
before Stage A and, at the same survival rate, **about 2,500 times the demo run's Stage B**: of
order a **week** of it on this machine, before a single probability is computed. Even the ~600
synthetic objects screened as primaries against the whole set is of order five hours, which is a
shard across jobs rather than a step in a run. A subset is not a saving here; it is the difference
between a step that exists and one that does not.

### The subset that keeps both directions of the claim honest

The prompt asks for two numbers that fail in different ways: events the key has and driftwatch
misses, and events driftwatch reports that the key does not have. A subset preserves **both**
exactly, provided it is closed:

> Choose a set of objects **S**, screen all-vs-all **within S**, and compare against the answer key
> **restricted to pairs with both objects in S**. Because the key is itself all-vs-all, its
> restriction to S is the exact truth for S. Nothing is missed by construction and nothing is
> falsely called extra. What is lost is coverage of pairs that leave S -- not the meaning of either
> number.

The defensible S, in the order it should be built:

1. **Every synthetic object** -- the 90006-90190, 95000-95407, 99000-99008 and 99996-99999 ranges,
   about 600 ids. These are the stressing edge cases the dataset was built to carry, and they are
   the part driftwatch has never been tested on: manoeuvres, a reentering heliocentric object,
   hyperbolic geometries, ephemerides that start and stop mid-window.
2. **Every TLE-derived object the key pairs with one of those**, so that each edge case keeps its
   real screening background.
3. **A documented random sample of the remaining TLE objects**, to give the extra-event count
   volume without paying for the whole catalogue.

What is deliberately *not* bought: the TLE-against-TLE bulk of the dataset. Those ephemerides were
generated from the public catalogue with COVGEN covariance -- which is SGP4-against-SGP4 ground
that the daily pipeline screens every day and that the Kelvins reproduction already scored. It is
the least novel part of the most expensive file.

### The cheapest path, in three rounds, and the first needs no tarball at all

**Round 0 -- 200 MB, no ephemerides, and it validates the scorer.** The answer key is not a list of
identifiers: each row carries both objects' **J2000 state at TCA**, both **UVW covariances** (upper
triangular), the miss distance, the relative velocity, the Mahalanobis distance, a dilution flag,
and `prob`. The mappings file carries per-object HBR. Feeding driftwatch's encounter-plane
construction and probability those exact inputs tests the whole scoring path against a government
reference **without a byte of the 20.73 GB**, and it is a like-for-like comparison rather than a
loose one: the key's `prob` is **Alfano (2004)** and driftwatch already computes `pc_alfano` beside
its default. Do this first. If it disagrees, nothing downstream is worth downloading yet.

**Round 1 -- one streaming pass, keep the closed subset.** Stream the tarball once, extract only
S's members, convert straight to the project's ephemeris parquet and never keep the OCM text.
Screen S all-vs-all against the **spherical** key. Round 1 is where the screening claim is made.

**Round 2 -- only if Round 1 earns it.** The SFSH key, with per-object volumes, and a wider sample
of the TLE background for the extra-event count.

### Configuration the guide fixes, and what driftwatch would have to change

- **Volumes.** The two keys are a **10 km sphere with a constant 0.5 m HBR**, and the SFSH
  per-object rectangles. Note what the prompt assumed and what is actually true: driftwatch's
  `box_ric_km = (2, 25, 25)` is a **half-width** box, and SFSH volume ID 7 is `U=2, V=25, W=25` as
  half-volumes for `period < 225 min`. **driftwatch's box is exactly the SFSH near-Earth volume.**
  The spherical key is reachable today by setting the watch radius to 10 km and the box to zero,
  since Stage C keeps an event that is in the box **or** inside the watch radius.
- **Rules driftwatch does not implement**: only element sets with `OD_EPOCH` within 14 days of the
  window start; usable start/stop times honoured per ephemeris; candidate OCMs of one designator
  never screened against each other; no Pc pre-filter; TCA strictly inside the window, and only at
  a **local minimum** of miss distance inside the volume; for the spherical key both directions of
  a pair reported.
- **A parser and a frame.** OCM is not the SpaceX ephemeris format, so it needs a reader, and the
  frame in the file has to be rotated into TEME rather than assumed -- the MEME/J2000 lesson of
  Step 1, where getting it wrong was worth 44 km.
- **A truncation that must not be read as a false positive.** CSieve was run with a 68 km spherical
  radius but the key keeps only misses **at or under 10 km**. An event driftwatch finds beyond
  10 km is outside the key by construction.

### The claim this step can actually make

The guide is explicit: the dataset "was devised primarily to evaluate conjunction geometry at the
time of closest approach", with the emphasis on finding all the same events and computing TCA and
the states accurately, and "**while Pc metrics do exist in the answer key, direct comparison of Pc
values requires the same method of Pc computation and is therefore not a key metric of this
dataset**". So the headline claim is about **screening**: which events are found, where the TCA is
placed, what the miss distance is. The probability comparison is legitimate only in the Round 0
form, where the inputs are identical and the method is matched to Alfano (2004) -- and it must be
reported as a check on the scorer, not as agreement on risk.

### Where it lives

`data/external/osc/` locally, which `.gitignore` already covers via `data/external/`. Never in the
repository, never in a run directory, never in the viewer bundle, and never through the daily
pipeline. The reproducible artefact is the **derived subset** -- the parquet ephemerides for S plus
the key restricted to S -- published as a release asset under CC0 with the source tarball's sha256,
recorded during the streaming pass, so a reader can reproduce the selection without the 20.73 GB.
