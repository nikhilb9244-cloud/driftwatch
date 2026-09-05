# SpaceX Starlink ephemerides: may we use them, and how?

A Phase 3 Step 0 question. Everything below was checked on 2026-09-02; the endpoints and the
terms both move, so re-check before relying on this.

## What they are

SpaceX publishes a predicted trajectory for every Starlink satellite, with covariance. These
are the operator's own product, not a tracking fit: they contain the manoeuvres the satellite
is *planned* to make, which no element set fitted to past observations can know about. They
are also the upstream source of the CelesTrak supplemental element sets driftwatch already
uses — CelesTrak fits an SGP4 element set to each of these files.

One file per satellite, in the "Modified ITC" format described in the *Spaceflight Safety
Handbook for Operators*. Measured on `MEME_53152_STARLINK-4045_2450325_Operational_...`,
fetched 2026-09-02:

| | |
| --- | --- |
| Size | 2.0 MB per satellite per version |
| Header | `created`, `ephemeris_start`, `ephemeris_stop`, `step_size`, `ephemeris_source`, frame |
| Span | 72 hours from creation, at a 60-second step (4,321 states) |
| Frame | `UVW`, which is the RTN/RIC frame |
| Per state | position and velocity in km and km/s, then the lower triangle of the 6×6 covariance (21 numbers) |
| Source label | `blend` on this file: a blend of the fitted past and the planned future |

## Where they come from now, and what that means for the terms

**They are no longer on Space-Track.** Space-Track announced that from 28 July 2025 it would
stop hosting SpaceX ephemerides on its Public Files page and through the `/publicfiles/` API,
and directed users to SpaceX. Checked directly on 2026-09-02 with our own account: the
directory listing at `/publicfiles/query/class/dirs` still names
`public-data-files-552-spacex-prod`, but `loadpublicdata` returns the NASA-JSC ISS ephemeris
entries whatever directory is asked for, and no Starlink ephemeris is retrievable there.

**They come from SpaceX, without an account.** `https://api.starlink.com/public-files/ephemerides/`
serves a `MANIFEST.txt` listing one file per satellite — 11,092 of them on 2026-09-02, the same
count as the CelesTrak supplemental file — and each named file at that path. Both returned
HTTP 200 with no authentication and no credentials of any kind. The `README.md` at the same
path documents the format, the 8-hour update cadence and the 72-hour horizon, and directs
conjunction correspondence to `starlink.com/satellite-operators`.

**So Space-Track's user agreement does not govern them.** That matters, because it would not
have helped if it did. USSPACECOM's blanket approval to redistribute covers *basic* space
surveillance data — element sets and OMMs, the SATCAT, decay and reentry data — and the
agreement otherwise has the user agree "not to transfer any data or technical information
received from this website … to any other entity without prior express approval". An
owner/operator ephemeris is not basic space surveillance data, so had we taken these files
from Space-Track, redistributing them or products built from them would have needed express
approval. Taken from SpaceX directly, none of that applies.

**SpaceX attaches no published licence.** Neither the README nor the space-safety
documentation states terms of use, a licence, redistribution rights or an attribution
requirement. The files are published, unauthenticated, for the stated purpose of letting other
operators screen against Starlink.

## The finding

**We may use them.** They are published without restriction for exactly this purpose, and no
agreement we are party to limits it. The rule we adopt is the one already applied to CelesTrak's
supplemental data:

- Read them, compute with them, and publish the results, crediting SpaceX for the source.
- Do not republish the raw files or a repackaged copy of them. Nothing grants that, and
  nothing is gained by it: the files are one HTTP request away for anyone.
- Cache politely. One request per satellite per version, only for the satellites a run
  actually needs, and never a sweep of the whole constellation.

## What their covariance actually is

Worth knowing before planning to use it. The published sigmas from the file above:

| Lead | Radial (U) | In-track (V) | Cross-track (W) |
| ---: | ---: | ---: | ---: |
| 0 h | 1.0 m | 1.4 m | 1.7 m |
| 1 h | 2.7 m | 11 m | 2.7 m |
| 3 h | 7.3 m | 62 m | 2.2 m |
| 8 h | 26 m | 576 m | 3.0 m |
| 12 to 48 h | 100 m | 1,000 m | 10 m |
| 60 to 72 h | 350 m | 2,000 m | 550 m |

It grows smoothly for about ten hours, which is a propagated covariance, and then sits on
round numbers — exactly 100 m, 1,000 m, 10 m — until it steps to another set of round numbers
for the last twelve hours. Past ten hours this is a stated envelope, not a fitted uncertainty:
plausibly the satellite's stationkeeping control box, which is a real and meaningful bound but
is not the same quantity as a covariance. Any use of it has to say so.

It is also far tighter than our own measurement of the same thing. The consistency of two
successive CelesTrak supplemental versions gives an in-track disagreement of about 710 m at a
lead of 2.9 hours (`docs/screening.md`); SpaceX's published sigma at 3 hours is 62 m, eleven
times smaller. The two are not measuring the same thing — ours includes the revision of the
plan between versions, theirs is the uncertainty within one plan — and the difference is
roughly the size of that revision. For screening, the revision is the part that matters.

## As built (Step 0 revision, 2026-09-02)

`ephemeris/spacex.py` and `driftwatch spacex`.

1. **The fetch is bounded.** One request per satellite, only for the Starlink secondaries a
   run's events involve, ranked by closest approach and capped by `--limit` (300 by
   default). At 2.0 MB a file this is the binding constraint: the 1,744
   supplemental-screened secondaries of the first live run would be 3.5 GB a version, and
   the whole constellation 22 GB. Only the position covariance is kept, thinned to a
   ten-minute grid, which turns each 2 MB file into tens of kilobytes; the raw file is not
   stored at all.
2. **Their covariance is used as published**, for the Starlink object, inside the file's
   72-hour validity, labelled `spacex-ephemeris`. The 21 published numbers are the lower
   triangle of the 6x6, row-major, in their UVW frame, which is our RIC, so no rotation is
   needed; the position block is interpolated linearly between the stored samples.
   Nothing inflates it. In particular the version-to-version revision measured from our
   stored supplemental versions is **not** added: the supplemental-consistency fit is kept
   as a cross-check instead (`spacex.cross_check`), because the two are different quantities
   and merging them would hide that.
   The fetch is a **separate command rather than part of `screen`**, deliberately: 120
   satellites took eight minutes and 240 MB, and a screening run should not carry that
   silently. `driftwatch risk` picks up whatever the store holds unless `--no-spacex` is
   given, so the layer is automatic once the data are there.
3. **Days four to seven.** The file stops at 72 hours and a seven-day screening window does
   not. Past a file's `ephemeris_stop`, and for any Starlink object with no stored file, the
   base model serves and reports **its own** source label rather than a SpaceX one, so
   `cov_source_secondary` says which of the three models covered each event. A request
   spanning the horizon comes back labelled `spacex-ephemeris+<what the base said>`.

### The cross-check, measured

`driftwatch spacex` prints their sigma beside ours at matched leads. Measured on 120
satellites of the demo run on 2026-09-02:

| Lead | SpaceX in-track | driftwatch in-track | Ratio | Which model of ours |
| ---: | ---: | ---: | ---: | --- |
| 1 h | 6.7 m | 489 m | 73 | supplemental consistency |
| 3 h | 24 m | 700 m | 29 | supplemental consistency |
| 8 h | 257 m | 4.54 km | 18 | GP (past the supplemental horizon) |
| 24 h | 2.81 km | 8.47 km | 3.0 | GP |
| 48 h | 2.51 km | 15.8 km | 6.3 | GP |
| 72 h | 3.80 km | 22.8 km | 6.0 | GP |

Ours is three to seventy times larger, and the sign is the expected one throughout: theirs
is the uncertainty *within* one published plan, ours is the uncertainty *of the plan being
revised*. The gap is widest at the short leads, where a published plan is nearly exact and a
revision is the whole error. Past eight hours ours is not even the supplemental fit any more
but the GP element sets, which measure the manoeuvring itself, and the ratio settles around
six. The number to watch is that ratio: if it ever fell to one, either the plans had stopped
being revised or our fit had stopped measuring the revision.

Two things the table shows about their own numbers. The in-track sigma is **not monotonic**
across the constellation — the median is 2.81 km at 24 hours and 2.51 km at 48 — which is
what an envelope on round figures looks like when different satellites sit on different
steps, and is another reminder that past about ten hours this is a control box rather than a
propagated covariance. And the envelope is not the same for every satellite: the file
measured for the terms question sat at 1,000 m in-track from 12 to 48 hours, well below the
constellation median here.

### The residual of the fit we actually propagate, added in quadrature

The geometry driftwatch propagates is CelesTrak's SGP4 **fit** to this ephemeris, not the
ephemeris itself, and CelesTrak publishes that fit's residual as a median of about 0.2 km.
SpaceX's own in-track sigma is 62 m at three hours and 576 m at eight. So for roughly the
first eight hours their covariance, used as published, is tighter than the disagreement
between the trajectory we are propagating and the trajectory the covariance describes.

Those are two different errors and they are independent: theirs is how well SpaceX knows
where the satellite will be, the residual is how far the element set we propagate sits from
the ephemeris they published. So the residual is added in quadrature rather than used as a
floor, on the diagonal only, which keeps the matrix positive definite and dilutes the
published correlations the way an added error should:

    sigma_k(t)^2  =  sigma_k^spacex(t)^2  +  (share_k * 0.20 km)^2

CelesTrak publishes the residual as one scalar, so it is split across R, I and C in the
shape of the base model's own measured floor — the version-to-version disagreement of those
same fits at essentially no lead, which is what shape those fits miss in. On the store in
hand that comes out as (0.099, 0.994, 0.054), giving 20 m radial, **199 m in-track** and 11 m
cross-track. `SPACEX_SGP4_FIT_RMS_KM` and `SPACEX_FIT_RMS_SHARE` hold the numbers;
`fit_rms_km=0.0` restores the as-published behaviour, and `spacex-ephemeris/2` in the model
version says the residual is in there.

**What it changed, on the demo run's 499 served events.** Nothing in the tally: 1 red, 22
yellow, highest probability 1.58e-4, all three identical to the as-published run, and not a
single event changed flag or region. It bites at short lead and nowhere else, which is
exactly where the argument said it would:

| Lead | Events | In-track sigma before | after | Median probability ratio |
| ---: | ---: | ---: | ---: | ---: |
| 8 to 24 h | 17 | 72 m | **211 m** | **3.63** |
| 24 to 48 h | 92 | 2.50 km | 2.51 km | 1.10 |
| 48 to 72 h | 109 | 2.50 km | 2.51 km | 1.08 |
| past 72 h | 27 | 3.80 km | 3.81 km | 1.05 |

Past a day their published number is a kilometre-scale control box and 199 m in quadrature is
a third of a percent of it. Inside a day it triples the probability, because there the
covariance was smaller than the gap between the two trajectories. A fifth of the served
events move by more than 10 per cent and 3.5 per cent of them by more than a factor of two.
That the probabilities go **up** rather than down is the geometry: at these misses the
covariance is small against the miss distance, so widening it moves probability mass onto the
hard-body disc rather than away from it.

**This term is a patch on a mismatch, not a fix for it.** The fix is to propagate the
ephemeris instead of the fit, which removes the residual from the chain entirely and improves
the nominal miss as well as the covariance. That is the first Phase 4 item in `ROADMAP.md`:
Stage C should interpolate the SpaceX ephemeris states directly for served events, so the
trajectory and the covariance share a source. When it lands, `SPACEX_SGP4_FIT_RMS_KM` goes to
zero for those events.

## Phase 4 Step 1: the states, and what the fit residual really was (2026-09-03)

The section above ends by saying the fit residual is "a patch on a mismatch, not a fix for
it", and that the fix is to propagate the ephemeris. Step 1 did that. It also measured the
mismatch properly for the first time, and the measurement changes the story.

### The disagreement is not 0.2 km except at short lead

CelesTrak publishes a per-object RMS with each supplemental element set: a median 0.201 km on
2026-09-03, 99th percentile 0.48 km. Phase 2 took that as the size of the gap between the
trajectory driftwatch propagates and the trajectory SpaceX's covariance describes. It is the
residual **over the arc the fit was made on**, which is the first several hours; past that the
element set is being propagated rather than fitted.

Measured directly: nineteen satellites, ephemeris files and supplemental element sets fetched
within a few hours of each other on 2026-09-03 so that the element set is the fit to *that*
file, states compared every 30 minutes across the whole 72 hours.

| Lead | Median | 90th percentile | Worst | Median in-track | Median radial | Median cross-track |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 to 1 h | 0.515 km | 1.570 km | 6.7 km | 0.440 km | 0.105 km | 0.111 km |
| 1 to 3 h | 0.327 km | 0.891 km | 2.9 km | 0.224 km | 0.076 km | 0.106 km |
| 3 to 8 h | 0.296 km | 0.768 km | 3.5 km | 0.213 km | 0.059 km | 0.112 km |
| 8 to 12 h | 0.337 km | 1.231 km | 5.2 km | 0.269 km | 0.097 km | 0.135 km |
| 12 to 24 h | **2.765 km** | 8.712 km | 185.8 km | 2.749 km | 0.153 km | 0.146 km |
| 24 to 36 h | **11.503 km** | 27.975 km | 582.5 km | 11.496 km | 0.173 km | 0.153 km |
| 36 to 48 h | **28.306 km** | 66.181 km | 1191.9 km | 28.304 km | 0.241 km | 0.180 km |
| 48 to 60 h | **51.792 km** | 126.985 km | 2034.0 km | 51.791 km | 0.243 km | 0.313 km |
| 60 to 72 h | **82.940 km** | 210.787 km | 3099.7 km | 82.938 km | 0.291 km | 0.293 km |

Almost all of it in-track, which is what a timing error looks like. The worst cases are
satellites under orbit-raising thrust, which an SGP4 element set cannot represent at all.

### Lineage, checked (2026-09-05)

A second external review asked for the table above to be qualified, and for the lineage of each
pair to be verified before the difference is attributed to the fit's extrapolation. The
qualification first: it is **one fetch on one date**, nineteen satellites, and the comparison is
against SpaceX's *published prediction* — a 72-hour file that carries planned burns and the
operator's drag model — not against the realised orbit. Whether the fit or the file is nearer to
where the satellite actually went cannot be told from this measurement.

The lineage next. A supplemental set fitted to one file and compared with another would measure
the revision of the plan between the two files as well as the fit's own drift. CelesTrak places
the epoch of each fit at the `ephemeris_start` of the file it fitted, to the second — every
epoch in the store ends in :42 (or :41.99999, the same number rounded), as does every file start
— so a set whose epoch equals the stored file's start was fitted to that file and no other. On the
300 pairs of the 2026-09-03 16:19 fetch (the states store and the 15:23 supplemental version),
classified that way and measured every 30 minutes, in TEME:

| Lineage | objects | under 12 h | 12 to 24 h | 24 to 36 h | 36 to 48 h | 48 to 60 h | 60 to 72 h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Set fitted to **this** file (epoch = start) | **17** | 0.293 km | 2.841 km | 11.789 km | 27.556 km | 51.832 km | 82.214 km |
| Set fitted to an **earlier** file (0.2 to 3.4 h before) | 105 | 0.296 km | 3.106 km | 12.799 km | 28.752 km | 52.046 km | 80.359 km |
| Set fitted to a **later** file (0.2 to 3.3 h after) | 178 | 0.318 km | 1.806 km | 9.506 km | 24.291 km | 45.456 km | 72.687 km |
| All 300 | 300 | 0.310 km | 2.305 km | 10.828 km | 26.038 km | 48.179 km | 75.654 km |

Medians of the distance, almost all of it in-track in every row. **What this establishes:** the
drift is the same on the seventeen pairs whose lineage is verified as on the 283 that were fitted
to a neighbouring file, so it is not the plan's revision between files, and the nineteen-file table
above stands as a description of a fit against the file it was fitted to — on one date. **What it
does not establish:** why. Past 24 hours the fit runs ahead of the file on nine of the seventeen
verified objects and behind on eight. Planned manoeuvres inside the file, which SGP4 cannot carry,
would do that; so would fit noise in the mean motion. Separating the two needs the *next* file's
first states, which are the nearest thing to a realised trajectory SpaceX publishes, and that
comparison has not been made. That a set fitted to a *later* file sits marginally closer to the
stored file than one fitted to the same file is consistent with the later fit having seen a
revised plan, and is within the scatter.

So the finding, stated to its evidence: a propagated supplemental set and the published file it
was fitted to disagree by kilometres within a day and tens of kilometres by three, on one date,
for the Starlink shell driftwatch screens against; the disagreement is not the revision of the
plan; and whether it is the fit's extrapolation or the file's own plan being wrong about the
satellite is open. The script that made the table is not in the repository; it propagates each
stored set with `satrec_from_elements` at the stored state times and bins the distance by lead
from `ephemeris_start`.

**Two corrections to what this file said before.**

1. The 0.2 km term was the right shape and the wrong size. The measurement recorded above —
   "it bites at short lead and nowhere else" — was true of *the term*. Whether the term was the
   whole of the error it stood for was never checked. It was not.
2. Serving SpaceX's covariance on top of the SGP4 trajectory made days two and three **worse**.
   Their in-track sigma at 72 hours is 3.80 km, a control box for the trajectory they published;
   ours from the supplemental-consistency fit is 22.8 km, far closer to the 83 km the propagated
   element set is actually out by. The tighter number was being served for a trajectory it did
   not describe, on exactly the events furthest out in the window.

Both are fixed by the same change, which is to make the served trajectory and the covariance's
trajectory the same object.

### The frame: MEME, not TEME, and worth 44 km

The header does not name the state frame. It carries `created`, `ephemeris_start`,
`ephemeris_stop`, `step_size`, `ephemeris_source` and a bare `UVW` line, which is the
*covariance's* frame. The state frame is in the file name: every file is
`MEME_<norad id>_STARLINK-…`, and MEME is mean equator and mean equinox of J2000.

Checked rather than assumed, because being wrong here is expensive — precession and nutation
since J2000 amount to about 0.36 degrees by 2026, some 44 km at low Earth orbit radius. Six
satellites, states against SGP4 from their own supplemental element sets:

| Interpretation | Median distance to the SGP4 fit at zero lead |
| --- | ---: |
| States read as TEME | 36.2 km |
| States rotated J2000 → TEME | **0.356 km** |

0.356 km at zero lead is the published fit residual, so the rotated reading is right. The
rotation is `orbit/frames.j2000_to_teme`, and only TEME is stored, so no second inertial frame
convention enters the project. It uses skyfield rather than astropy for speed — 0.13 s against
1.74 s per file — and `tests/test_frames.py` pins the two against each other at 0.9 mm.

### The stored grid, measured

Cubic Hermite on position and velocity, thinned from the file's 60-second grid. Held-out error
against the file's own states, ten files:

| Stored step | Kept per file | Median error | 99th percentile |
| ---: | ---: | ---: | ---: |
| **120 s (chosen)** | **2,161** | **5.68 m** | **6.03 m** |
| 180 s | 1,441 | 22.6 m | 27.3 m |
| 300 s | 865 | 193.7 m | 214.1 m |
| 600 s | 433 | 2,462 m | 3,531 m |

120 seconds halves the store against the file's own step and leaves the interpolation error a
thirty-fifth of the 0.2 km it removes. 300 seconds would reintroduce an error the same size as
the one being removed, which is the line this must stay well clear of. Every fetch re-measures
it and `driftwatch spacex` prints it.

### The 48-hour seam

**Every file measured carries a discontinuity of a few hundred metres at exactly 48 hours after
`ephemeris_start`.** Not a manoeuvre — it is at the same instant in all of them — but a seam
between two arcs of the `blend` the header names. On the file measured for this section the
radius steps by about 160 m between two consecutive 60-second states, and the published velocity
at the seam disagrees with the central difference of the positions around it by 16 m/s.

It is invisible in raw second differences, which are dominated by 30 km per step² of ordinary
orbital curvature. The detector is a residual test: predict each interior node from its two
neighbours by Hermite, which on a smooth arc gives 5.7 m and at the seam gives 150 to 1,100 m.
Three orders of magnitude, so the threshold — 50 m, or ten times the file's own median — is not
a tuning knob.

The stored history is split into segments at each break and no interpolant spans one; the
60-second gap between segments is served by the base propagator, exactly as the region past the
72-hour horizon is. With that in place the measured interpolation error over ten files has a
**maximum of 6.8 m**, the tail having been excluded rather than smoothed over.

A planned manoeuvre would look the same to this detector and is handled the same way, which is
the right answer: an interpolant should not span a burn either. A break in the very first or
very last interval of a file cannot be detected, because the test needs a node on both sides.

### The store holds one copy of one version per satellite

A fetch writes one file, the store is the set of them, and a satellite is read from its newest
version only: newest by the file's own `created` header, and a tie on `created` goes to the fetch
that stored it later. The tie is not hypothetical. SpaceX refreshes a satellite's file roughly
every eight hours and the pipeline fetches whenever it runs, so two runs inside one window hold the
same version. Pipeline run 6 on 2026-09-05 fetched at 10:48 UTC exactly what run 5 had fetched at
09:33, the same 300 files all created at about 01:25, into a state store the Actions cache had
carried between the two runs. The newest-version rule kept both copies, every epoch of every
segment appeared twice, and the Hermite interpolant refused the grid with `the time grid must be
strictly increasing`. It had never happened locally because the local store holds one fetch.

The loader is also made to refuse to fall over. Each segment's grid is sorted and de-duplicated
before an interpolant is built; a row repeating its neighbour's epoch and state, to a millimetre,
is dropped; and an epoch that carries two *different* states splits the segment there, with the
object, segment and epoch in the log, so that no interpolant spans the disagreement. The store fix
is meant to make that a no-op, and when it was not the screening log says how many objects were
repaired (`repairs` in the trajectory summary).

### What the fit residual now is

It applies **per event, not per object**. An event whose geometry came from the interpolated
states has no SGP4 fit in its chain and gets the covariance exactly as SpaceX published it; one
past the horizon, inside a break, or on an object whose states were not stored still has a fit
in its chain and still carries the residual. Which is which is read from the trajectory columns
the screening wrote, not recomputed from a store that is refetched every eight hours. Model
version `spacex-ephemeris/3`.

## Sources

- Starlink ephemerides README, https://api.starlink.com/public-files/ephemerides/README.md, and
  the manifest and a sample file at the same path, read 2026-09-02.
- Starlink Space Safety documentation, https://space-safety.starlink.com/docs/tutorial-basics/trajectories/,
  read 2026-09-02: the operator-facing portal, hourly upload with a seven-day horizon,
  covariance frames ITRF, EME2000 and RTN.
- Space-Track's announcement that it would stop hosting the files from 28 July 2025
  (@SpaceTrackOrg, https://x.com/SpaceTrackOrg/status/1938326343193698325), corroborated here
  by direct query of the `/publicfiles/` API on 2026-09-02.
- Space-Track user agreement and API documentation, https://www.space-track.org/documentation,
  read 2026-09-02, for the blanket approval and its limits.
