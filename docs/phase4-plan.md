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
