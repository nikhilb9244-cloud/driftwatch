# Phase 4 prompt

How to use this. Save it as `docs/phase4-prompt.md` in the repository, then paste everything below
the line into the coding agent in the repository folder. It assumes Phase 3 as delivered: the five
scenarios on `driftwatch risk`, the storm term validated against May 2024 and February 2022, the
`storm_validity` label, the viewer's storm mode and the May 2024 replay.

---

We are starting Phase 4 of driftwatch, the shipping phase. Read `ROADMAP.md` (Phase 4 and its
parked items), `docs/phase3-plan.md` (every review decision of the storm layer), `docs/methods.md`,
`docs/design-brief.md` (both halves: the visual pass and the operator console specification) and
`docs/data-sources.md` before doing anything else.

The goal is a **public, automated, documented product**: a site a stranger can open, a pipeline
that keeps it current without anybody remembering to run it, an export somebody can take away, and
a write-up honest enough to send to people who do this for a living and ask them what is wrong
with it.

Two rules carry over from every previous phase and are not negotiable in this one.

**Nothing is tuned to a validation.** The 22 per cent NRLMSIS over-prediction and the 0.88
correlation are records, not calibrations. `DENSITY_STORM_RATIO_SIGMA_REL` stays at 0.30 and a test
pins it. If Phase 4 finds a reason to change a model, it changes the model on the strength of an
argument and says so in the plan, not quietly on the strength of a number already in the docs.

**The point cloud's data path does not change.** Phase 1's frame budget is the reason the viewer is
worth looking at. The visual pass in Step 5 is uniforms, shaders and DOM; it is not new geometry
per object and it is not per-frame work on the main thread.

## Step 1. Stage C interpolates the SpaceX ephemeris states directly

This is first because it is the only item that changes a number the whole pipeline rests on, and
because it removes a term the project currently carries as an admitted patch.

**The problem.** For a Starlink secondary inside the 72-hour horizon of SpaceX's published
ephemeris, the *covariance* comes from that ephemeris and the *trajectory* comes from CelesTrak's
SGP4 fit to it. Those are two different objects, and they disagree by the fit's own published
residual — a median 0.20 km, which is larger than SpaceX's own sigma for the first several hours.
Phase 2 added that residual in quadrature on every served covariance
(`config.SPACEX_SGP4_FIT_RMS_KM`, split by `SPACEX_FIT_RMS_SHARE`, model version
`spacex-ephemeris/2`). That is the honest patch. The fix is to propagate the ephemeris.

**Build.**

- **Keep the position blocks at fetch.** `ephemeris/spacex.py` currently stores only the covariance
  and throws the states away. Store the states too, on a grid coarse enough to be small and fine
  enough to interpolate — the files are 60-second, 72 hours, so a full state history is about
  4,300 rows per object. Decide and document whether every fetched object keeps its states or only
  those a run's events involve.
- **Read the frame from the file header rather than assuming it.** Do not infer it from the
  covariance's UVW axes. Record what the header says in `docs/spacex-ephemerides.md` and convert to
  TEME through the same path Phase 1 verified, so the interpolated states and the SGP4 states are
  comparable without a second frame convention entering the project.
- **Interpolate with Hermite on position and velocity**, not Lagrange on position alone: the files
  give both, and a Hermite interpolant on a 60-second grid is accurate to metres for a low Earth
  orbit while a position-only Lagrange fit of the same order is not. Measure the interpolation
  error by holding out every other grid point and report it; if it is not well under the 0.2 km
  residual being removed, the exercise has not paid for itself.
- **Decide what Stage B screens on, and prove the no-miss guarantee still holds.** Stage B's
  guarantee rests on a relative-speed bound derived from mean elements (`docs/screening.md`). If
  Stage C refines on interpolated states while Stages A and B still use element sets, the pair that
  reaches Stage C is chosen by one trajectory and refined on another, and the two differ by 0.2 km.
  Either show that the existing pad absorbs it, or widen the pad and say by how much. **Do not
  quietly rely on the pad.**
- **Set the fit residual to zero per event, not globally.** An event served by interpolation has no
  fit in its chain and its `SPACEX_SGP4_FIT_RMS_KM` term goes to zero; an event past the horizon,
  or on an object whose ephemeris was not fetched, still has one. `cov_source_secondary` already
  distinguishes these; extend it rather than adding a parallel flag, and bump the model version.

**Report.** How many events changed, the distribution of the change in miss distance, the change in
`pc`, and **whether any flag moved**. Phase 2's measurement was that the residual moved no flag;
say plainly whether removing it does. If the answer is that nothing moves, that is a result worth
publishing too — it bounds how much this whole class of error matters.

## Step 2. The daily pipeline, as a GitHub Actions workflow

**Build** a scheduled workflow that fetches, screens, scores every scenario, rebuilds the bundle and
deploys, with no human in the loop.

- **All fetching happens in Actions.** Never in a Cloudflare Worker or a Pages Function. This is not
  a preference: CelesTrak firewalls by IP and Cloudflare Worker egress addresses are **shared
  between tenants**, so a Worker's fetches can start returning HTTP 522 on every source while the
  same URLs answer instantly from anywhere else, because another tenant on the same egress address
  earned the block. `docs/design-brief.md` records where this was read (satvis) and how that project
  works around it. A Worker or a Pages deployment may *serve* the bundle; it must never fetch.
- **Space-Track credentials are Actions secrets** (`SPACETRACK_USER`, `SPACETRACK_PASS`), read from
  the environment only, as `catalogue/spacetrack.py` already requires. Cloudflare needs
  `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. `driftwatch check-bundle` already refuses to
  publish a file containing the literal value of any of them; keep that in the workflow as the last
  step before deploy, not as an afterthought.
- **The order.** `fetch` → `screen` → `risk` once per scenario → `storm-check` → `report` →
  `check-bundle` → deploy. The replay bundle is rebuilt only when its inputs change, which is
  rarely: a historical snapshot does not move and the Sun imagery is already fetched.
- **Runtime is the hard constraint and it needs a plan before it needs code.** On a laptop the demo
  fleet's week is about four minutes of screening plus four of covariance fitting, and **each storm
  scenario is about sixteen minutes** — two density tracks per object from its own epoch to the
  window end. Five scenarios is over an hour, against a six-hour job limit and against the courtesy
  owed to CelesTrak and Space-Track. Three things already exist to spend before writing anything
  new: the persistent ballistic-coefficient cache (`drag/store.py`, keyed by NORAD id and history
  span), `--storm-step-s` coarsening with its measured cost (0.65 % on a history fit against a 5 %
  statistical uncertainty), and the fact that the *geometry* is computed once per snapshot while
  only the scoring is per scenario. Measure the run before optimising it, and record the numbers.
- **State has to persist between runs**, or the cache is useless and CelesTrak's two-hour floor
  cannot be honoured. The supplemental store already solves this with an orphan branch
  (`supplemental-store`, see `.github/workflows/supplemental.yml`); use the same pattern, or the
  Actions cache, and say which and why. Do not commit run directories to `main`.
- **Concurrency and failure.** One run at a time (`concurrency:` with no cancellation mid-deploy).
  A failed fetch must **not** publish a stale bundle silently: either the deploy is skipped and the
  previous site stands, or the bundle carries its true age and the status strip shows it. The
  console specification already requires snapshot age to be two numbers and to say `EXPIRED` when
  the run is older than the window it describes; wire the pipeline to that rather than inventing a
  second staleness mechanism.
- **Retention.** Decide how many run directories survive and where, and make `driftwatch report`
  able to rebuild any of them.

## Step 3. The public landing page

A stranger arrives knowing nothing. The page has to answer, in plain language and in this order:
what a conjunction is, what a geomagnetic storm does to the atmosphere and therefore to where
things are, why a screening tool built on the public catalogue gets worse exactly when it matters,
and what this tool does about it.

- **Plain language means plain language.** No "in-track" before it is defined, no `pc`, no Kp
  without saying what a 9 means. The physics that earns its place: drag lowers an orbit, a lower
  orbit is *faster*, so a storm mostly makes a satellite **early** rather than low — and being
  early by tens of kilometres is what moves a conjunction.
- **State the limits on the page itself, not only in the methods.** Absolute probabilities from
  public element sets are indicative, not operational. This is not a collision-avoidance service and
  must not be used as one. The storm term is validated for objects with a measured ballistic
  coefficient and has no demonstrated skill for the rest, and the site labels which is which.
- Link the methods page, the repository, the write-up and the export. Carry the attribution
  `docs/data-sources.md` requires for CelesTrak, Space-Track, SpaceX, NOAA SWPC and Helioviewer.
- It is the first document on the critical path, so it obeys the paint budget in Step 5: it must be
  readable before any JavaScript runs.

## Step 4. CSV and JSON export per fleet

Somebody who cannot run the tool must be able to take the numbers away.

- **One export per fleet, per run, per scenario**, reachable from the viewer and at a stable URL.
- **CSV for the events**, one row each, with a documented and stable column order and units in the
  header names. The JSON companion carries what a CSV cannot: the run identity, the snapshot, the
  model and supplemental versions, the scenario definition, the thresholds and the caveats — the
  same provenance every risk row already carries, hoisted once instead of repeated 5,704 times.
- **An unscoreable event exports with empty probability fields and its reason**, never as zero and
  never dropped. Anything else turns "we refuse to give a number" into "the number is small" the
  moment it reaches a spreadsheet, which is the single most likely way this project's care gets
  undone by somebody else's `SUM`.
- Carry `storm_validity` and both coefficient sources on every row, and the licence and citation
  lines in the JSON.
- Version the schema and document it in `docs/data-schema.md` beside the others.

## Step 5. The visual pass, the mobile layout and the paint budget

`docs/design-brief.md` is the specification and it has already been argued; this step builds it.
**Read the note at the head of the console section first** — Phase 3 Step 5 built the scenario
control, the Δ-against-quiet column, the unscoreable section, the encounter plane's shift arrow and
the replay scrubber to that spec, and those are not to be rebuilt.

- **The visual pass** (§1–§7 of the brief): selection dimming rather than highlighting, the
  day–night terminator and an atmosphere rim scaled to the density profile, fading trails rather
  than persistent orbit lines, labels on demand, one category palette with **the G ramp reserved**
  for geomagnetic level and used in exactly three places, the encounter plane as an instrument, and
  one scrubber rather than two.
- **The console** (§1–§6): the fixed reading order — *is my fleet all right, what needs action, what
  exactly is this one* — the status strip, the fleet band, the event queue as a ranked table, and
  the detail view. The governing constraint is that **the console must be completely usable with
  the globe absent**, not degraded-but-tolerable.
- **The mobile layout** (§7) is a restriction of that arrangement, not a rewrite, which is only true
  if the globe is genuinely optional. Build it that way round: the console first, the globe added.
- **The paint budget** (§8) is a number to be met and defended: first meaningful paint at or under
  1.8 s and largest contentful paint at or under 2.5 s on Lighthouse's mobile profile, with the
  critical-path transfer at or under 80 KB gzipped. "Meaningful" is the status strip and the first
  ten queue rows *with real numbers in them* — not a skeleton. That means `console.json` as a small
  first-paint export, the console's own JavaScript with no three.js and no worker, the stylesheet
  inlined while it is under 8 KB, and the status strip's values server-rendered into the HTML at
  export time. **A Lighthouse run in CI fails the build if either threshold is missed.**
- The brief's measured bundle table was re-measured at Phase 3 Step 5; re-measure it again and keep
  the table honest.

## Step 6. The six parked research items, and which two to build

All six are in `ROADMAP.md` with their reasoning. Restated with what each needs:

1. **Manoeuvre burden.** The count of events crossing an operator's action threshold under each
   scenario, against quiet, per fleet member. Needs no new data and no new physics — it is a
   summary over risk tables Phase 3 already writes.
2. **Commandability.** Hours from the fleet member's last usable ground-station pass to the time of
   closest approach. Needs ground stations in the fleet YAML (latitude, longitude, altitude,
   minimum elevation), a pass predictor over the screening window, and the honest note that a pass
   is an opportunity to command, not a guarantee.
3. **Lifetime loss per storm.** The same coefficient and density track integrated to re-entry rather
   than to a time of closest approach: days of remaining life a G3, G4 or G5 costs an object at
   300, 400 and 500 km. Needs a real integration, because the linear storm term does not survive a
   decay that large — the same limit Step 3 hit.
4. **A live NOAA impacts panel.** Current and forecast R, S and G scale levels beside the
   conjunction list, from the SWPC feeds Phase 3 already pulls.
5. **Illuminated satellites over southern African sites.** Satellites sunlit above Sutherland during
   astronomical twilight, and above the SKA core site, with the growth curve over years of
   historical snapshots. Shadow geometry on the propagated catalogue and nothing more.
6. **A Hermanus dB/dt panel** from INTERMAGNET, against a stated threshold — the same storm seen
   from the ground. Check INTERMAGNET's attribution and licensing conditions before redistributing
   anything.

(The RIPE Atlas Starlink latency overlay is already resolved: the Phase 3 Step 2 review moved it out
of the pipeline and into the write-up as context. It is Step 7's business, not this step's.)

**Recommendation: build 1 and 2, manoeuvre burden and commandability.** The reasoning, so it can be
argued with:

- They are the two that make a probability **actionable**, which is the premise the whole console is
  built on. Everything else on the list is context around a number; these two turn the number into a
  decision — *how many burns would you have had to plan, and is there a pass before the encounter?*
- Neither needs new physics. Manoeuvre burden is arithmetic over tables that already exist.
  Commandability is a topocentric elevation calculation on a propagator that is already verified
  against the official SGP4 cases and against skyfield.
- The console specification **already depends on commandability** and currently specifies a column
  that renders `–` with a tooltip saying no ground stations are defined. Shipping the console with a
  designed hole in it, when the hole is a fortnight of work, is the wrong order.
- They are what a small operator would ask for first, which is exactly the audience Phase 5 goes
  looking for. Lifetime loss is the best *third* — it is the most legible consequence of a storm for
  a general reader and a natural figure for the write-up — but it needs a re-entry integration, so
  it is real work rather than a summary, and it informs nobody's Tuesday.
- Items 4, 5 and 6 are each interesting and none is this product. The impacts panel restates what
  NOAA already says; the illumination counts answer a different community's question well enough to
  deserve their own tool rather than a corner of this one; the Hermanus panel is a ground
  measurement that never touches an orbit. Park them again, with that written down.

Build the two, and leave the other four in `ROADMAP.md` with this reasoning attached so the next
review can disagree with it on the record.

## Step 7. The write-up

A short paper or a long blog post. It has to cover, and be honest about, four things.

- **The method.** What is computed and in what order: the catalogue, the three screening stages and
  why each exists, the covariance from element-set consistency, the probability on the encounter
  plane, the density model, the ballistic coefficient, the in-track storm term and its derivation,
  and the five scenarios.
- **The two validated storms.** May 2024 on both tests — the density enhancement, which needs no
  ballistic coefficient, and the in-track error of pre-storm element sets, which is the one that
  matters for screening. February 2022 with its coverage limitation stated: the catalogue holds 17
  of the 49 satellites and the decay evidence rests on six of the 38 lost, so no population
  statistic is quoted from it.
- **The validity split.** The storm term is predictive at r = 0.88 for objects whose ballistic
  coefficient was measured from their own decay and has **no demonstrated skill** without one, and
  every aggregate in the tool is reported both ways for that reason. Include the finding that
  motivated it: the median `pc / pc_variance_only` is 0.16 over validated events and 0.89 over
  indicative ones, so the combined figure was averaging a large real effect with a near-absent
  unmeasured one, weighted by the coverage of the coefficient fit rather than by physics.
- **Every known limitation**, from `docs/methods.md`, not a selection of the comfortable ones. The
  dilution region and what it does and does not say. The slow-encounter underestimate that no
  comparison this project can run is able to size. The survivorship bias in both validation samples.
  The NRLMSIS storm-response bias — with the two quantities set out side by side, because our sign
  disagrees with the published assessments and most of that disagreement is a category difference
  (model density at a fixed altitude against density inferred from a decaying orbit's own decay,
  integrated over three days) rather than a discrepancy.

**Two things belong in the write-up that belong nowhere else.**

The **withdrawn common-mode cancellation claim**, worked through. Phase 3 Step 3 found that a storm
lowers the probability on most events and explained it by the two objects being displaced alike. The
diagnostic built to attack that claim confirmed the result and **falsified the explanation** — the
relative shift is 1.91 times the mean of the two absolute shifts out of a possible 2, because a
conjunction is a crossing at a median 120°. That is the most methodologically interesting thing this
project has done and it should be told as what it is: a result that survived losing its reason.

The **RIPE Atlas Starlink latency overlay** as context, plotted against the Kp bar, with the probe
ids cited. Pulled once for the paper, never wired into the pipeline.

Then publish it, and send it to people at SANSA, the SKA Observatory, a university satellite group
and two space situational awareness companies — **asking for criticism rather than praise**, and
recording what comes back.

## Docs and hygiene

- A `docs/phase4-plan.md` in the same style as Phase 2 and Phase 3: every decision, every review, and
  every run's numbers, with the wrong turnings left in beside their corrections rather than edited
  away. That convention has now caught two errors that a clean history would have buried.
- Keep the approximations list in `docs/methods.md` current. It is long and it should be.
- A licence and a `CITATION.cff`, both of which Phase 4 owes and neither of which exists yet.
- Tests for the Hermite interpolator against a held-out grid, the export's refusal to write a zero
  where a probability is absent, the pipeline's staleness handling, the pass predictor against a
  known pass, and the manoeuvre-burden count against a hand-checked table.
- Same discipline as before. One step at a time, stopping for review after each, asking before
  anything that constrains Phase 5.

## Acceptance criteria

1. Stage C interpolates SpaceX's published states for events inside the ephemeris horizon, with the
   interpolation error measured against held-out grid points, the fit residual removed **per event**
   rather than globally, Stage B's no-miss guarantee re-derived or its pad widened, and a report of
   how many events moved and whether any flag did.
2. A scheduled GitHub Actions workflow fetches, screens, scores every scenario, rebuilds the bundle
   and deploys to Cloudflare Pages, with Space-Track and Cloudflare credentials as Actions secrets,
   **every fetch inside Actions**, persistent state between runs, one run at a time, and a stale
   bundle either not published or visibly labelled as stale.
3. A landing page explains conjunctions, storms and the tool's limits in plain language, states that
   this is not a collision-avoidance service, and is readable before any JavaScript runs.
4. CSV and JSON export per fleet, per run, per scenario, with a documented and versioned schema,
   full provenance in the JSON, and unscoreable events exported with empty probabilities and their
   reason.
5. The visual pass and the console are built to `docs/design-brief.md`, the mobile layout is a
   restriction of the same arrangement, the console is usable with the globe absent, and a
   Lighthouse run in CI fails the build if first meaningful paint exceeds 1.8 s or the critical-path
   transfer exceeds 80 KB gzipped.
6. Manoeuvre burden and commandability are built; the other four parked items are re-parked in
   `ROADMAP.md` with the reasoning for the choice recorded so it can be argued with.
7. The write-up is published, covering the method, both validation storms, the validity split and
   every known limitation, including the withdrawn cancellation claim worked through and the
   NRLMSIS comparison with both quantities set out; and it has been sent to at least five people
   with a request for criticism.
8. Docs, the approximations list, the licence, the citation file, tests and CI all updated and green.
