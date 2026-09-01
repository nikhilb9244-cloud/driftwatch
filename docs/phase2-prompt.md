# Phase 2 prompt

How to use this. Save it as `docs/phase2-prompt.md` in the repository, then paste everything below the line into the coding agent in the repository folder. It assumes Phase 1 as delivered, including the snapshot history under `data/snapshots/` and the approximations list in `docs/`.

---

We are starting Phase 2 of driftwatch, conjunction screening. Read ROADMAP.md, docs/phase1-plan.md, docs/data-schema.md and the approximations list first. Everything in this phase runs in Python in the TEME frame with full-precision epochs. The browser never computes a screening result. It only displays what Python exported.

## Step 0. Space-Track as a second source

Screening against 19,000 objects misses most of the debris and rocket bodies, which are the dominant secondary population, so this comes first.

- Read credentials from SPACETRACK_USER and SPACETRACK_PASS. Never write them to disk or logs.
- Pull the current catalogue from the gp class, meaning objects with no decay date and an epoch inside the last thirty days. Respect Space-Track's published request limits, cache with the same two-hour floor as CelesTrak, and pull the full catalogue at most a few times a day.
- Merge into the snapshot by NORAD ID, keeping the freshest epoch per object and recording the source. Keep the raw Space-Track elements out of the public viewer bundle unless you have read the user agreement and it allows redistribution. Derived results are ours to publish.
- Add a gp_history fetch for a named list of NORAD IDs over a date range. Phase 2 needs it for covariance and Phase 3 needs it for the storm replays.
- Report the new object count and the change in the category and band mix.

## Step 1. Fleets

- Fleet definitions live in `fleets/` as YAML. Each entry has a NORAD ID, a display name, a hard-body radius in metres with a note on where it came from, and a flag for whether the object manoeuvres.
- Build `fleets/demo.yaml` with the ISS, one Sentinel satellite, two university cubesats, and any active object whose SATCAT owner code is SAFR. Choose radii from public dimensions and justify each in the file.

## Step 2. Screening, fleet against catalogue

Fleet against the catalogue, never all against all. A seven-day window from the snapshot epoch. Three stages, in the tradition of Hoots, Crawford and Roehrich (1984).

- Stage A. Apogee and perigee overlap from mean elements with a configurable pad, default 50 km. Drop objects with a perigee below 120 km and flag them as decaying. Flag objects whose element set is older than five days as stale.
- Stage B. Coarse time stepping of relative distance for surviving pairs, vectorised with SatrecArray. Choose the step and the candidate threshold together so that no approach within the screening radius can be missed, given a maximum relative speed of about 15 km per second. Write the derivation in the docs and prove it with a test that compares against brute-force fine stepping on a random subset.
- Stage C. Refine each candidate minimum by root-finding on the relative range rate, the dot product of relative position and relative velocity, with SGP4 evaluated inside the bracket. Output the time of closest approach, the miss distance, the relative speed, and the miss vector in the primary's radial, in-track and cross-track frame.
- Screening volume. A configurable box in the primary's RIC frame, defaulting to 2 km radial and 25 km in-track and cross-track, the familiar ISS notification box, plus a spherical watch radius, default 25 km, for context.
- Use the CelesTrak supplemental Starlink ephemerides for Starlink secondaries when available, since standard elements cannot predict their manoeuvres. Flag any pair where either object is known to manoeuvre.
- Performance target. The full weekly screen for the demo fleet in under ten minutes on a laptop, with timings printed per stage.

## Step 3. Uncertainty and probability of collision

- The catalogue carries no covariance, so estimate it. For each object with enough history, take pairs of element sets, propagate the older to the newer epoch, and difference in RIC. Fit the growth of the radial, in-track and cross-track errors against propagation time from half a day to seven days. Where history is thin, fall back to a pooled model by category and altitude band, and record which was used. Backfill history from gp_history for every fleet member and every secondary that survives Stage A. Document that consistency between element sets is a floor on the error, not a measure of accuracy.
- Design the covariance as an injectable model. Phase 3 will add a storm term to the in-track component, so the screening function must accept a covariance model as an argument rather than computing one internally.
- Probability of collision by the two-dimensional method. Project the combined covariance onto the encounter plane perpendicular to the relative velocity, and integrate the Gaussian over a disc of the combined hard-body radius centred on the miss vector. Implement Foster's numerical integration on a polar grid, and either Alfano's series or Chan's analytical form as a cross-check that must agree within one percent.
- Also compute the maximum probability over covariance scale factors from 0.1 to 10, after Alfano, and report the scale at which it occurs. This is what makes the dilution effect visible, where probability falls as uncertainty grows.
- Flags. Red at a probability of 1e-4 or above, yellow at 1e-5, the thresholds NASA uses for the ISS.
- Tests. Closed-form checks first, for example zero miss distance with an isotropic covariance gives one minus exp of minus R squared over two sigma squared. Then reproduce the risk column of ESA's Kelvins Collision Avoidance Challenge dataset from its own inputs, registering on the Kelvins site if the download requires it. That dataset gives relative position and velocity in RTN, both covariance matrices and a computed risk, and if present, columns for maximum risk and its scaling that correspond to the Alfano calculation. The hard-body radius ESA used is not given, so treat it as a fit parameter and report the value that best reproduces the risk column. Agreement within a factor of two across the high-risk tail is the target. Report the distribution of residuals, and if any region disagrees badly, say so rather than tuning it away.

## Step 4. Output and viewer

- `uv run driftwatch screen --fleet fleets/demo.yaml --days 7` writes a conjunctions parquet and JSON with every field above, the covariance source per object and the flags, plus a weekly report in markdown with the top twenty by probability and the top twenty by miss distance.
- Viewer. A conjunctions panel listing the report. Selecting an event jumps the clock to the time of closest approach, highlights both objects, draws their tracks for ten minutes either side, and opens an inset showing the encounter plane with the combined covariance ellipse, the hard-body disc and the miss vector. Positions and times for the highlighted pair come from Python's export, not from satellite.js, and the inset states the probability, the maximum probability and its scale.

## Docs and hygiene

- A methods page covering the filters, the step-and-threshold derivation, the covariance method with its caveats, the probability definitions and the thresholds. Extend the approximations list.
- Tests for synthetic conjunctions with known geometry, meaning two orbits constructed to pass at a chosen time and distance, with the time of closest approach recovered to a second and the miss distance to a metre.
- Same commit discipline as Phase 1, one step at a time, stopping for review after each step. Ask before choosing anything that constrains Phase 3, particularly the covariance model interface and the export schema.

## Acceptance criteria

1. Space-Track merged in, the object count reported, credentials only in the environment, and no raw redistributed data in the public bundle.
2. The demo fleet screens over seven days in under ten minutes, with TCA, miss distance, relative speed, RIC components, probability, maximum probability, covariance source and flags for every event.
3. The no-miss guarantee for Stage B is derived in the docs and demonstrated by the brute-force comparison test.
4. The probability code passes the closed-form tests, the two implementations agree within one percent, and the Kelvins reproduction is documented with its fitted hard-body radius and residuals.
5. The viewer's conjunctions panel works as described, using Python's numbers.
6. Docs updated, approximations list extended, all tests and CI green.
