# Phase 3 prompt

How to use this. Save it as `docs/phase3-prompt.md` in the repository, then paste everything below the line into the coding agent in the repository folder. It assumes Phase 2 as delivered, including the run directory, the `risk` command that rescores stored events by scenario, the covariance protocol and the supplemental-set snapshots.

---

We are starting Phase 3 of driftwatch, the storm layer. Read ROADMAP.md, docs/phase2-plan.md, docs/phase2-prompt.md and the methods and approximations pages first. The goal is to show, live and in replay, what a geomagnetic storm does to low Earth orbit drag, to the in-track uncertainty of every object, and therefore to the conjunction list. Nothing in this phase rescreens. Every scenario rescores the stored events through the covariance protocol and the `risk` command, exactly as designed in Phase 2.

## Step 0. Close out Phase 2

- Dilution wording. In the methods page, the report and the panel, the dilution region means the data cannot support a judgement either way. Remove any statement that better data would clear a flag. Better data usually shrinks the probability, but it can also move the nominal miss, and the tool must not predict which.
- Starlink extrapolation. Do not fit the growth exponent for supplemental-set covariance from a baseline of hours. Constrain it to a physically plausible range, at least linear and at most quadratic in time, fit only the amplitude, and record in the docs that the exponent is a prior until versions accumulate. Add a scheduled task, a GitHub Actions cron or a local scheduler, that fetches and stores supplemental sets every few hours from now on, and a `--refit` path that uses every stored version with consistency pairs binned by lead time.
- SpaceX ephemerides. Space-Track publishes SpaceX's own Starlink ephemerides as public files, with covariance, for about three days ahead. Read their terms, which may not fall under the basic-data blanket approval, and report whether we may use them and how. If we may, plan to use their covariance directly for Starlink secondaries inside the three-day horizon in a later step, and note the horizon problem for days four to seven.
- State plainly in the report whether the remaining ISS versus YAM-3 red is robust or dilution.
- Kelvins. Add the agreement restricted to the high-risk tail, meaning rows with risk above 1e-5, the direction of the bias, and a residual-against-risk plot. If the chaser's radar cross-section category is in the data, test it as a size proxy for the per-object radius.

## Step 1. Space weather ingestion

- CelesTrak SW-All.csv, cached daily, for observed and predicted Kp, ap and F10.7 back to 1957. This is the primary driver for the density model.
- NOAA SWPC JSON feeds at services.swpc.noaa.gov for the real-time planetary K index, the three-day Kp forecast, the 27-day outlook, and the solar wind magnetic field and plasma. Cache with a floor and record the issue time of every forecast.
- A space weather table with one row per three-hour interval, columns for Kp, ap, F10.7, the 81-day F10.7 average, a provenance column that says observed, forecast or synthetic, and the forecast issue time where relevant.
- Helioviewer API for Sun imagery at chosen times, cached, for the replay in Step 5. Fetch a few frames per storm day, not a movie.

## Step 2. Density and drag

- Use pymsis with NRLMSIS 2.x. Learn its ap input format, which takes the daily value and a short three-hourly history, and build it correctly from the table.
- For each stored event, compute density along both objects' orbits from the element-set epoch to the time of closest approach, under a given scenario, at a step coarse enough to be fast and fine enough to follow altitude changes on eccentric orbits. Document the step choice.
- A ballistic coefficient per object. Fit it from the object's own decay history in the element sets where the history is long enough, and fall back to the B-star term converted to physical units where it is not, labelling which was used. Treat B-star as noisy and say so in the docs.
- Report quiet-condition density at 300, 400, 500 and 600 km as a sanity check against published values, and the storm-to-quiet density ratio for a G3 and a G5 profile.

## Step 3. The storm term and scenarios

- Derive and document the in-track displacement caused by an unmodelled density excess on a near-circular orbit. Starting from the semi-major axis decay rate under drag and the resulting mean motion drift, the displacement grows with the square of time and is proportional to the ballistic coefficient, the density excess and the square of the orbital speed. Verify the closed form against a numerical integration of a test orbit with a step density change, to a few percent.
- Apply it in two parts. First a mean shift of each object's in-track position at the time of closest approach relative to what its element set predicted, computed from the scenario density minus the density implied by the element set's own fit. Second a variance term from the uncertainty in that shift, driven by the stated uncertainty of the density model, tens of percent even in quiet conditions, and by the forecast uncertainty in ap. The relative shift between the two objects changes the miss vector in the primary's frame, and the variance adds to the in-track element of each covariance.
- Extend the covariance protocol minimally so a scenario can return an in-track mean shift alongside the covariance. Keep the Phase 2 quiet scenario bit-for-bit unchanged as the regression baseline.
- Scenarios for the `risk` command. quiet, using observed conditions. forecast, using the NOAA three-day forecast and the 27-day outlook beyond it. storm-g3, storm-g4 and storm-g5, synthetic ap profiles built from the May 2024 sequence scaled to the target level, starting at a chosen offset into the window. replay, using the observed record for a historical window. Every output row carries the scenario, run id, snapshot id, supplemental version and model version.
- Report the probability under shift plus variance as the primary number and under variance only as a comparison, so the docs can show which of the two effects matters.

## Step 4. Validation against the two storms

- Historical snapshots. Add a command that builds a catalogue snapshot as of a given date from gp_history, taking the latest element set per object before that date, restricted to a chosen altitude range to keep the history pull bounded. Cache permanently.
- The May 2024 Gannon storm. Pull element sets for a few hundred low Earth orbit objects across a range of altitudes and ballistic coefficients from 20 April to 25 May 2024. Measure the change in mean motion across the storm and infer the density enhancement, and compare it with the NRLMSIS ratio for the same days and altitudes. Then the test that matters for screening. Take each object's last pre-storm element set, propagate it through 10 to 13 May, and measure the in-track error against the element sets issued during those days. Do the same for a quiet control window with the same lead times. The storm term, driven by the observed ap, should predict the storm-window offset. Report the residual distribution and any dependence on altitude.
- The February 2022 Starlink loss. Pull the element sets for the 49 satellites launched on 3 February 2022 and a control group at 500 km. Show the decay at insertion altitude, and whether the model predicts elevated drag for a G1 storm at 210 km. If it does not, say so and discuss why in the docs rather than adjusting anything.
- A replay run for the demo fleet on the historical snapshot for 9 May 2024, with Sentinel-1A standing in for Sentinel-1C since 1C did not exist yet, scored under quiet and replay scenarios, showing which events moved and by how much.

## Step 5. Viewer storm mode and replay

- A storm control in the viewer that switches the conjunction panel between quiet, forecast and the synthetic storm levels, showing for each event the change in miss distance and probability between scenarios, and the region and confidence under each.
- A replay mode for May 2024 with a timeline. The Kp bar, the density ratio at 400 and 500 km, the Sun image nearest the selected time, and the conjunction list for the replay run all move together as the user scrubs. Positions come from the historical snapshot's export.
- Keep the Phase 1 performance. The storm control changes numbers in the panel, not the point cloud.

## Docs and hygiene

- A methods page for the storm term with the full derivation, the density model's known limits, the ballistic coefficient sources and the scenario definitions.
- Extend the approximations list. It should now be long.
- Tests for the ap input construction, the density sanity values, the closed form against numerical integration, the shift sign convention, scenario reproducibility, and the historical snapshot builder.
- Same discipline as before. One step at a time, stopping for review after each, asking before anything that constrains Phase 4.

## Acceptance criteria

1. Phase 2 close-out items done, including the constrained exponent, the scheduled supplemental fetch, the SpaceX ephemeris terms report, the robust-or-dilution statement and the Kelvins tail figures.
2. Space weather ingested with provenance, and density computed along orbits from pymsis with a correctly built ap history.
3. The storm term derived, verified numerically, and applied as a mean shift plus a variance through the extended protocol, with the quiet scenario unchanged from Phase 2.
4. Five scenarios rescoring stored events through the `risk` command with full provenance on every row.
5. May 2024 validated on both the density enhancement and the in-track error of pre-storm element sets, with residuals reported. February 2022 examined and discussed. The replay run reported.
6. Viewer storm mode and replay working with the Sun imagery and the Kp bar.
7. Docs, approximations list, tests and CI all updated and green.
