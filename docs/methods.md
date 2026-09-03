# Methods and approximations

A running list of every approximation in the pipeline, with its size where it has been
measured. Phase 4 turns this into the public methods page. Entries are grouped by where
they enter the chain; each states what is assumed, why, and what it costs.

## Catalogue

- **Coverage.** CelesTrak groups `active`, `stations`, `starlink`, `oneweb`,
  `last-30-days` and the Fengyun-1C, Iridium 33 and Cosmos 2251 debris clouds, merged
  with Space-Track's `gp` class (every object with no decay date and an element set from
  the last 30 days) when credentials are available. Space-Track supplies the older
  rocket bodies and the debris that belongs to no CelesTrak group, which are the dominant
  secondaries in screening. Without credentials the snapshot is CelesTrak only, and the
  fetch log says so. Objects with no element set in 30 days are absent from both sources.
- **Two sources, one element set per object.** The newest epoch wins per NORAD id; at
  equal epoch CelesTrak wins the tie. CelesTrak redistributes Space-Track's element sets,
  so the two sources never disagree about an object at the same epoch; the only effect of
  the merge is more objects and, for a fraction of the CelesTrak ones, a fresher element
  set. The `source` column records which.
- **Redistribution.** Space-Track's user agreement (read 2026-09-01, quoted in
  `docs/data-sources.md`) grants blanket approval to redistribute TLEs and OMMs, SATCAT and
  decay data with citation. The viewer bundle therefore carries Space-Track-sourced
  elements and the manifest and the viewer show the attribution. Conjunction Data
  Messages and the emergency and advanced tiers are not covered and are never fetched.
- **Element-set age.** Whatever CelesTrak holds at fetch time. The age distribution is
  logged for every snapshot and exported to the viewer per object.
- **Object type and category.** SATCAT object type is authoritative for debris and
  rocket bodies. Constellation membership is inferred from group membership and name
  prefixes; these are heuristics.
- **Apogee, perigee, period.** Mean-element values from the sgp4 library's
  initialisation (Brouwer mean semi-major axis). They differ from osculating values by
  up to several kilometres. Used only for filtering and the altitude bands.
- **Category and altitude band are labels, not filters.** Screening candidates are
  chosen from mean-element apogee and perigee alone (Phase 2, Stage A). `unknown`
  (objects with no SATCAT type, mostly analyst objects Space-Track has not yet correlated
  to a launch) and `other` (orbits that straddle the 2,000 km LEO ceiling or sit near or
  above GEO) stay in the pool. The labels colour the viewer, group the report and choose
  the pooled covariance fallback.

## Screening (Phase 2)

- **Hard-body radius.** Each fleet member carries the radius of the sphere that encloses
  its deployed envelope, half the diagonal of the bounding box, rounded up (the
  "circumscribing sphere" of NASA CARA's guidance). Secondaries get a category default
  or a radar-derived sphere (below). The probability of collision scales with the square of the combined radius,
  so this is a first-order choice, and the sphere overstates the cross-section of flat or
  long bodies: the ISS's 70 m sphere is several times its projected area for most
  approach directions, and ZACube-1's 10 m wire antenna sets a radius seventeen times
  that of its bus. Every value and its provenance is in `fleets/demo.yaml`.
- **Manoeuvres.** Not predicted. SGP4 cannot see a burn coming, and an element set
  issued before one is wrong after it by the size of the burn. Every object carries a
  three-valued prior instead: `known` (operated constellations, stations, fleet members
  flagged in the file), `possible` (every other payload in CelesTrak's active group) or
  `none` (debris, rocket bodies, payloads outside the active group), and the history
  check promotes `possible` to `observed` when the element sets show a semi-major-axis
  jump that drag cannot explain. The detector's thresholds (a 100 m floor; a raise
  beyond half the modelled drag change; a lowering beyond twice it, so that storm-driven
  decay is not called a burn; gaps over ten days skipped) are judgement calls recorded
  in `risk/manoeuvre.py`. A `known` object's next burn is as invisible as ever.
- **Miss distances are between propagated trajectories.** Stage C finds the closest approach
  of two trajectories to microseconds and metres, which says nothing about how close the two
  spacecraft come: the trajectories themselves are good to hundreds of metres to kilometres.
  The probability layer below attaches the uncertainty.
- **The published states are in MEME (J2000), and only the filename says so.** The file header
  names the covariance's frame, `UVW`, and never the states'. MEME is 0.36 degrees from TEME by
  2026, about **44 km** at low Earth orbit radius. Measured against CelesTrak's SGP4 fits to the
  same files: read as TEME the states sit 36.2 km away, rotated into TEME they sit 0.356 km
  away, which is CelesTrak's own published fit residual. Reading them wrong would have
  introduced a 44 km error in the course of removing a 0.2 km one, and it would have been
  silent. `driftwatch spacex` re-runs that comparison on every fetch and refuses to write the
  store if it fails, because the risk being guarded against is a change at the source rather
  than a mistake in the code. `docs/ephemeris-frame.md` is the standalone note.
- **Where an operator publishes states, those are the trajectory (Phase 4 Step 1).** For a
  Starlink object inside the 72-hour horizon of SpaceX's published ephemeris, both Stage B and
  Stage C use the published states, interpolated by cubic Hermite on a 120-second grid, rather
  than CelesTrak's SGP4 fit to them. `primary_trajectory` and `secondary_trajectory` say which
  served each event. Three approximations come with it. The interpolation error is a measured
  median 5.7 m and maximum 6.8 m, against the 0.2 km fit residual it removes. The published
  states are in MEME (J2000), which is 44 km from TEME at this radius, so they are rotated on
  the way in; the rotation is skyfield's and agrees with astropy's to 0.9 mm. And the served
  trajectory is discontinuous at up to three instants per object per run — the start of
  coverage, the file's 48-hour seam and its 72-hour horizon — where the position steps by up
  to tens of kilometres; Stage B doubles its detection threshold on those intervals and Stage C
  scans them rather than root-finding, so the time of closest approach there is placed to about
  0.3 s rather than to microseconds. A break in a file's first or last interval cannot be
  detected at all.
- **Stage A uses mean apogee and perigee with a 50 km pad.** Brouwer mean values differ
  from the osculating orbit by several kilometres, and drag lowers an orbit by a few
  kilometres a week (more for an object about to decay, and in a storm); the pad, which
  also has to cover the 35 km screening radius, absorbs both. A secondary whose
  perigee rises or falls by more than the pad's slack inside the window (a manoeuvre, or
  the last days of a decay) can be missed by Stage A. Objects with a mean perigee below
  120 km are dropped outright.
- **Stage B's no-miss guarantee rests on a speed bound and on continuity.** The relative
  speed of a pair is bounded by the sum of the two-body perigee speeds from mean elements,
  times a 2 % margin for SGP4's departures from Keplerian motion. The bound is derived and
  tested in `docs/screening.md`; it fails only if a trajectory moves more than 2 % faster than
  its two-body perigee speed, which does not happen above 120 km. It also assumes the
  separation is continuous, which the served trajectory is not at the handful of instants where
  it switches between published states and SGP4; there the threshold is doubled to `R + v h`,
  because only one endpoint sample lies on each side of the jump and a one-sided reach needs
  the whole step rather than half of it.
- **A maximum and a minimum inside one step** (30 s) would defeat the sign-change
  candidate rule. That needs a relative speed of metres per second (co-orbital objects),
  for which the sampled separation is already within metres of the true minimum; the
  sampled-minimum fallback catches it. Never triggered on the 2026-09-01 catalogue.
- **SpaceX's published files are not smooth all the way through, and the discontinuity is
  structural.** Every 72-hour file measured on 2026-09-03 -- ten of ten, then nineteen of
  nineteen -- steps by a few hundred metres at **exactly 48 hours after `ephemeris_start`**. On
  the file examined in detail the radius moves 160 m between two consecutive 60-second states
  and the published velocity at that instant disagrees with the central difference of the
  positions around it by 16 m/s. This is an observation about how the files are made, not about
  the satellites: it is at the same lead in every file, so it is not a manoeuvre, and the header
  labels the product `ephemeris_source: blend`, which is the likely explanation -- two arcs
  produced differently and joined at a fixed offset from the file's start, with no attempt to
  match derivatives across the join. Consequences: an interpolant must not span it (driftwatch
  splits the stored history into segments and lets the base propagator serve the 60-second gap),
  and any use of these files that assumes a single smooth arc over 72 hours is wrong by a few
  hundred metres for part of it. A planned manoeuvre would look the same to any detector and is
  handled the same way. A break in a file's very first or very last interval cannot be detected
  at all, because the test needs a node on both sides. `docs/spacex-ephemerides.md`.
- **Supplemental Starlink sets are fits to predictions.** CelesTrak fits SGP4 to SpaceX's
  published ephemerides, which include planned manoeuvres. The fit residuals CelesTrak
  publishes with every set (a median of 0.20 km, a 90th percentile of 0.27 km and a worst case of 10.8 km when read on 2026-09-02) are the floor on how well the set represents
  that ephemeris, and the ephemeris itself is a prediction revised as plans change. Used for 10,728 of the 11,094 Starlink objects on the first run;
  `secondary_ephemeris` says which set an event used.
- **Events are geometry; probability is a separate layer.** An event is kept when the
  miss vector lies inside the 2 x 25 x 25 km box or within the 25 km watch radius, and
  its row carries both objects' states at the time of closest approach. Every scenario
  (quiet now; storm and replay in Phase 3) rescored over those rows changes the
  uncertainty and the probability and nothing else.

## Uncertainty and probability (Phase 2, Step 3)

- **The covariance is a consistency floor, not an accuracy.** It is fitted from the
  disagreement between an object's own element sets after propagation (`docs/screening.md`,
  "Uncertainty"). Two fits by the same network with the same force model share whatever
  error they have in common, a storm-biased drag model above all, and the difference
  between them cannot see it. The true error is at least the fitted one; `pc_max` and
  its scale are the honest reading.
- **SGP4 is not invariant under re-initialisation with drag.** A set fitted at a later
  epoch with the same `B*` drifts in-track by about 0.07 km per day at `B* = 1e-4`
  (measured on a 500 km orbit; zero with `B* = 0`). That drift sits inside the
  consistency residuals as part of the floor. Small against real element-set errors.
- **A power law per RIC component, diagonal, floored at half a day.**
  `sigma(dt) = s dt^p` from pairs between 0.5 and 7 days apart, no cross-terms, no
  velocity covariance; below half a day the half-day value is used, beyond seven days
  the law is extrapolated. Two parameters per component keep thin histories stable at
  the cost of any structure the data might have (a diurnal term, a change of tracking
  regime).
- **Thin history falls back to a pool, then to a prior.** Objects with under 5 sets or
  10 pairs take the fit of every object with the same category and altitude band (at
  least 30 pairs); an empty pool takes a per-band prior from published TLE-accuracy
  studies. The label travels with every number (`empirical`, `pooled:<category>/<band>`,
  `default:<band>`), so the reader can tell a measured covariance from a borrowed one.
- **An object screened on an operator ephemeris has its covariance fitted from
  successive supplemental versions, not from its GP history.** Its GP sets disagree by
  about 10 km a day, which measures its station keeping rather than its tracking and has
  nothing to do with the set actually propagated. The supplemental fit has its own
  limits: the versions are hours to days apart, so a power law fitted to them is
  extrapolated to the seven-day end of the window; no object yet has enough versions of
  its own, so the growth is pooled across all of them and only the floor is per object;
  and when the publication gaps span less than a factor of three the exponent is not
  fitted at all but fixed at one. The label on every covariance says which case applied.
- **The floor under a supplemental covariance is CelesTrak's published fit residual**
  (`RMS` in the supplemental file, a median of 0.20 km on 2026-09-02), added in
  quadrature and split across the RIC components in the proportions of the fitted
  growth. It measures the element set against the ephemeris it was fitted to, not the
  ephemeris against reality: an operator's published plan can be revised or abandoned,
  and nothing here sees that until the next version is published. With only one stored
  version the floor is the whole covariance, which is a lower bound and is labelled
  `supplemental:rms` so it can be recognised.
- **Secondary hard-body radii are category defaults or radar-derived spheres.** 30 m
  station, 10 m Starlink, 3 m OneWeb / constellation / payload, 5 m rocket body, 0.5 m
  debris, 1 m untyped; for payloads, rocket bodies, debris and untyped objects a
  published radar cross-section gives `sqrt(RCS / pi)` clipped to 0.1 to 20 m instead.
  The probability scales with the square of the combined radius, so a factor of two
  here is a factor of four in `pc`; the objects table records which rule applied.
- **The encounter is a straight line.** The two-dimensional method assumes constant
  relative velocity through the encounter and no velocity uncertainty, which holds for
  crossings at kilometres per second and fails for co-orbital pairs at metres per second
  (long encounters).
- **A slow encounter's probability is a known underestimate, and is flagged as one.** Below
  0.1 km/s relative the pair takes minutes rather than a second to cross its separation, the
  relative path curves through the passage and the two can re-approach, so more of the
  uncertainty is in play than the one-plane integral sees. `slow_encounter` marks those
  events in every risk table and the report counts them; **nothing rescales the
  probability**, and the fix is a three-dimensional integration, which is not in this phase.
  **The flag rests on the method's straight-line assumption, not on a measured error.** The
  size of the underestimate is unmeasured here, and the flag would stand at this threshold
  whether it turned out to be a factor of two or a factor of ten.
  Ten of the demo run's 5,704 events qualify, the slowest at 23 m/s, none flagged. Note two
  things. A large in-track uncertainty is not this problem — it is mostly a timing error and
  the projection discards it, which is why the method survives hundreds of kilometres of
  in-track sigma. And the Kelvins reproduction cannot measure the size of the underestimate,
  because ESA's own risk column uses the same two-dimensional method: the residual binned by
  relative speed is flat at the slow end, which says the two share the approximation, not
  that there is no error.
- **Three integrators, one value.** Foster's polar grid (the reported `pc`) and Alfano's
  one-dimensional form agree to about 1e-8 over the tested range and must agree within
  one percent; Chan's series is exact for an isotropic covariance and drifts by tens of
  percent when the disc is comparable to the smaller standard deviation. All three are
  exported.
- **The maximum probability is a sweep, not a model.** Covariance scale factors from 0.1
  to 10 on a log grid of 61 steps with a parabolic refinement; the true maximum could
  lie outside the range for a very small or very large miss, in which case the edge
  value is reported with a scale of 0.1 or 10.
- **Flags use NASA's ISS thresholds on `pc`.** Red at 1e-4, yellow at 1e-5, on the Foster
  value under the fitted covariance; a different operator's thresholds, or a rule on
  `pc_max`, can be applied to the same rows.
- **A flag in the dilution region is not actionable.** When the maximum of the
  probability over covariance scale factors lies below the covariance used
  (`pc_max_scale` under one), shrinking the uncertainty *with the miss held fixed* would
  raise the probability: the number is held up by the size of the covariance rather than
  by the geometry. Those events are labelled `region = dilution` and `confidence = low`,
  and the report and the viewer present them as statements about the uncertainty rather
  than about the encounter. The first live run's largest probability, the ISS against
  YAM-3 at 11.5 km seven days out, is one of these: the encounter-plane uncertainty is
  13.9 by 0.50 km against an 11.5 km miss, and shrinking the covariance tenfold at the
  same miss drops the probability from 1.6e-4 to 7.1e-7. **That is not a prediction
  about better data.** A better orbit shrinks the covariance and moves the nominal miss
  at the same time, and the miss can move either way by a distance of the order of the
  uncertainty being removed. The dilution region means the data in hand cannot support a
  judgement either way, not that a judgement is coming. `docs/screening.md` works that
  example through.
- **A pair's cumulative probability is an upper bound.** One minus the product of the
  complements over the pair's events assumes the events are independent. They are
  repeated passes of the same two objects propagated from the same two element sets, so
  an error that puts them close on one pass puts them close on the next; the true
  combined probability is lower. It is labelled as such everywhere it appears.
- **The Kelvins reconstruction makes two approximations.** The chaser's RTN frame is
  built from the target's with the target's velocity taken as circular, and the
  covariances are used as position-only matrices. With those two, and with the combined
  hard-body radius taken as `(t_span + c_span) / 2` — the dataset's own size columns, no
  parameter fitted — the reconstruction reproduces ESA's risk column to a median residual
  of -0.0003 in log10 (0.07 % in the probability), 87 % of the tail within a factor of
  two. What disagreement remains is one-sided: the 5th percentile of the residual is
  -0.66 against a 95th of +0.13, so where it disagrees it reads the encounter as *safer*
  than ESA did, and payloads are over-represented in that tail. Our covariance-scale sweep
  matches ESA's `max_risk_scaling` exactly as a factor on the covariance (median ratio
  0.9999). See `docs/screening.md` and `docs/kelvins-reproduction.md`.
- **A secondary's hard-body radius is a population median, not a measurement.** Nobody
  publishes the size of most catalogue objects. `sqrt(RCS / pi)`, which driftwatch used to
  fall back on, is the radius of the disc that returns the same echo rather than the size of
  the object: it understates anything much larger than the radar wavelength and anything
  with a low-return geometry, and scored on the Kelvins data against ESA's own radii it
  needs a multiplier of nearly five and still does no better than one radius for everything.
  It has been replaced by the median radius of the object's type and cross-section class in
  those same rows (4.55 m for a large-return payload, 1.90 m for a large-return rocket body,
  1.25 m for large-return debris, 1.0 m otherwise), with the previous value kept as a lower
  bound. Two caveats travel with it. Most cells are 1.0 m because ESA defaults an
  unpublished span to 2.0 m, so the radius of an unknown object is a **screening
  convention** — deliberately generous, and the reason these probabilities are comparable
  with ESA's. And a median is not a measurement: any individual fragment may be a tenth of
  it or ten times it, and nothing here knows which.
- **Kp is an index, not a measurement of anything an orbit feels.** It is a three-hourly
  average over thirteen mid-latitude magnetometer stations of a phenomenon whose energy is
  deposited mainly in the auroral ovals, so two storms with the same Kp can heat a given
  orbit differently. The table converts it to ap by the published Bartels table before
  anything averages it, because Kp is quasi-logarithmic and averaging it is meaningless: 4
  and 6 are 27 and 80 nT, whose mean is 53 nT, which is Kp 5+ rather than Kp 5.
- **F10.7 is a proxy for the heating, not the heating.** The thermosphere is warmed by
  extreme ultraviolet, which the 10.7 cm radio flux correlates with over a solar cycle and
  less well day to day. It is what NRLMSIS was built on, so it is what the table carries. The
  **observed** flux is used rather than the value adjusted to 1 AU, because the atmosphere
  feels the flux that arrives; both are in the table so the choice can be reversed.
- **Everything past the last observation is somebody else's forecast**, carried with the time
  it was issued and never smoothed into the observations. SWPC's three-day Kp forecast is
  skilful; CelesTrak's six-week prediction appears to be derived from it and is not an
  independent opinion; the 27-day outlook is a recurrence climatology and should be read as
  one. A three-hour interval with no source at all is left as NaN with provenance `missing`
  rather than filled with a quiet value.
- **A daily A index spread across eight intervals is flat by construction.** Where the 27-day
  outlook is the only source, every interval of the day gets the same ap. A real disturbed day
  is not flat, and the density model will therefore miss the shape of it even when it has the
  level about right.
- **A supplemental-set covariance is a floor plus a growth term, used only over the lead
  times the stored versions resolve.** The floor per component is the larger of the shortest
  resolved lead-time bin's measured disagreement and CelesTrak's published fit residual —
  the larger, not the quadrature sum, because two versions an hour apart already disagree by
  both their fit residuals. The growth is fitted to the excess over that floor, so the model
  reproduces the bin it is anchored at instead of standing above it by the floor again. The
  in-track exponent is a physically bounded prior (`[1, 2]`, at 1.5) rather than a fit,
  because the store spans hours; radial and cross-track are floor-only until the bins
  resolve a trend, and linear when they do. Even so, extrapolating to seven days gives 42 to
  2,500 km in-track depending on the exponent, against about 18 km measured directly from
  the same objects' GP sets, so the fit carries a validity horizon — the top of the longest
  bin holding 30 pairs, not the single longest pair — and the GP model serves beyond it,
  labelled `supplemental:beyond-horizon`. The horizon moves out as the scheduled fetch
  accumulates versions.
- **SpaceX's published covariance is used as published plus the fit residual, and it is not
  the same quantity as ours.** Inside a file's 72-hour validity a Starlink secondary's covariance is SpaceX's own,
  interpolated on a ten-minute grid and labelled `spacex-ephemeris`; outside it the base
  model serves and reports its own label. Three things to hold on to. Past about ten hours
  their numbers are a stated envelope on round figures (100 m radial, 1,000 m in-track, 10 m
  cross-track) rather than a propagated covariance. It is the uncertainty *within* one
  published plan, while the supplemental-consistency fit measures the uncertainty *of the
  plan being revised*, which is roughly eleven times larger at three hours and is the part a
  seven-day screen depends on; the two are reported side by side rather than merged. And the
  geometry driftwatch propagates is CelesTrak's SGP4 fit to that ephemeris, not the
  ephemeris itself, so that fit's own published residual — 0.2 km, split in the base model's
  measured shape to 20 m radial, 199 m in-track and 11 m cross-track — is **added in
  quadrature** — but **only on the events whose geometry still comes from that fit**
  (`spacex-ephemeris+sgp4-fit`); where Stage C refined on the published states the two share a
  source and nothing is added (`spacex-ephemeris`). `SPACEX_SGP4_FIT_RMS_KM`;
  `spacex-ephemeris/3` in the model version says the rule is per event.
- **How big that residual actually is, corrected (Phase 4 Step 1).** Phase 2 sized the gap
  between the propagated element set and the published ephemeris at CelesTrak's published fit
  RMS, a median 0.20 km. Measured directly on nineteen matched files on 2026-09-03, that holds
  only for the first eight to twelve hours: the median distance is 0.30 km inside 12 hours,
  **2.8 km at 12 to 24, 11.5 km at 24 to 36, 28.3 km at 36 to 48, 51.8 km at 48 to 60 and
  82.9 km at 60 to 72**, almost all in-track, with a worst case in the thousands of kilometres
  for satellites under orbit-raising thrust. CelesTrak's number is the residual over the arc
  the fit was made on, not over the file. Two consequences are recorded rather than tidied
  away: the Phase 2 patch was the right shape at a hundredth of the right size at the far end
  of the horizon, and serving SpaceX's 3.80 km control box on top of a trajectory that is 83 km
  out **understated** the uncertainty on the events furthest ahead in the window, where the
  project's own supplemental-consistency model would have said 22.8 km. Interpolating the
  published states removes the gap rather than sizing it, which is why Step 1 exists; for
  events past the horizon, where the fit is still the trajectory, the residual carried is still
  the published 0.20 km and is still too small by this measurement. That is an open
  understatement, not a solved one. **Measured on the demo run of 2026-09-03**, screening on the
  published states instead of the fit moved the miss distance of the 476 affected events by a
  median 0.16 km inside twelve hours rising to 9.1 km at 48 to 60 hours, moved ten flags
  (one of them `none` to red), and added or removed nine more flagged events outright. Phase 2's
  measurement that the 0.2 km patch moved no flag was true of the patch and not of the error.

## Density and drag (Phase 3, Step 2)

- **NRLMSIS 2.1 through pymsis, and its own uncertainty is the dominant term.** Tens of per
  cent in quiet conditions, worse in a storm and worse again in the days after one. Nothing
  here improves on that; the storm scenarios are reported as changes against a quiet baseline
  for exactly this reason. `docs/density-and-drag.md` carries the sanity check: within a
  factor of two of the US Standard Atmosphere 1976 at its own conditions, with the gap growing
  with altitude as that profile's known bias predicts, and well inside the solar-cycle spread.
- **The model is driven with the inputs it was fitted with**, which are not the obvious ones:
  the **previous day's** observed F10.7, the 81-day **centred** average, the **observed** flux
  rather than the flux adjusted to 1 AU, and a **seven-element** ap history per sample (daily
  Ap; now, 3, 6 and 9 hours back; the mean of 12 to 33 hours back; the mean of 36 to 57 hours
  back), read only because `geomagnetic_activity=-1` is passed. With the default switch the
  model would use the daily Ap alone and the storm response would be a smooth daily average.
  A sample whose history the weather table does not cover comes back NaN, never zero.
- **Density is sampled along the orbit, not evaluated once.** The step is one revolution over
  16, tightened for eccentric orbits in proportion to their altitude range in scale heights,
  and clamped to [30 s, 600 s]. Measured against a 10-second reference the rule holds every
  orbit tested to under 0.1 %, where a fixed 600 s step is wrong by 13 % at e = 0.15 and 17 %
  at e = 0.72 — the eccentric tail whose perigee passes through the densest air.
- **The sampling frame is GMST-only.** No polar motion, UTC treated as UT1: measured on the
  ISS, 12 m of latitude and 0.9 m of longitude. Nothing, for a model uncertain by tens of per
  cent, and it avoids an astropy frame transform per sample over millions of samples.
- **The atmosphere co-rotates exactly, and there are no winds.** The relative velocity used in
  the drag integral is the inertial velocity minus solid-body rotation, which is a 6 % effect
  on speed and 17 % on its cube. Real thermospheric winds reach several hundred metres a
  second in the auroral zones during a storm — a few per cent of the relative speed, in the
  places and at the times a storm matters most, and not modelled.
- **B\* is a fit parameter, not a physical ballistic coefficient.** It absorbs whatever the
  SGP4 fit could not otherwise explain and is routinely negative. The textbook conversion
  through a reference density is quoted in the config and **not used**: measured against the
  decay SGP4 itself produces, it is wrong by three orders of magnitude and the implied
  constant varies sevenfold between objects 45 km apart in altitude. The fallback instead
  propagates the element set with its own B\* and inverts the resulting decay through the same
  density model, which is self-consistent and altitude-aware.
- **A ballistic coefficient is fitted from the object's own decay where the decay is
  measurable**, over 45 days, excluding manoeuvre intervals, outlier sets and intervals longer
  than a fortnight. Objects with neither a usable fit nor a usable B\* take the run's own
  median for their category **and drag altitude band**, labelled `typical`. Every row carries
  which of the three it used and an uncertainty: the statistical error of its own decay for a
  fit (floored at 5 %), a 50 % prior for a B\* inversion, the pool's robust spread floored at a
  factor of two for a stand-in.
- **A fit is accepted against the object's own element-set scatter, not a fixed threshold.**
  The scatter is the pooled residual of a quadratic fitted through the mean semi-major axis
  *inside each contiguous run* of surviving element sets — never across the gap a manoeuvre
  exclusion leaves, or the burn itself is counted as noise. The decay must exceed
  `scatter × sqrt(2 × runs)` by a factor of three. So a quiet object earns a fit from a smaller
  decay than a noisy one: NOAA-20's elements scatter by 0.16 m, making its 64 m of decay a
  77-sigma measurement.
- **A jump detector cannot see a continuous thrust**, and a drag fit reads it as atmosphere.
  Deorbiting Starlinks fit at B near 1 m²/kg off 48 km of decay in 45 days, an area-to-mass no
  satellite has. The proxy used is the fraction of intervals excluded as manoeuvres, refused
  above a quarter — set from a measured break in the population, where the median B is flat at
  0.012 to 0.045 below it and jumps to 0.18 to 0.26 above. It is a proxy and it does not catch
  everything: one Starlink with 12 % of its intervals excluded still fits at 0.69 m²/kg.
- **The fit runs on a coarser grid than the scenarios**, four times the step rule, because it
  only ever uses the integral. Measured cost: 0.65 % on a history fit against a 5 % statistical
  uncertainty, 3.9 % on a B\* inversion against a 50 % prior. And under a **wall-clock budget**,
  spent from the top of the probability list down, with a persistent cache keyed by NORAD id
  and the history span it used, so coverage deepens run over run rather than the same objects
  being refitted.
- **Only the product `B rho` is observable from a decay**, so a systematic bias in the density
  model folds into the fitted coefficient and cancels when the same model drives the
  scenarios — for the quiet case. It does **not** cancel for the storm response, which has no
  baseline to divide out against. The fitted B is therefore not a measurement of area over
  mass; it is that divided by the model's bias over the fit window.
- **One coefficient per object, constant over the window.** No attitude changes, no lift, no
  radiation pressure. A Starlink turning its panel edge-on to ride out a storm — a documented
  operational response — changes its coefficient by a factor of several, invisibly.

- **A manoeuvring object fitting above `BALLISTIC_THRUST_M2_KG` is under continuous thrust and
  is refused a coefficient**, taking the run's typical value for its class instead. A
  continuous low thrust is a ramp rather than a jump, so the manoeuvre detector cannot see it
  and a drag fit reads the whole fall as atmosphere. A satellite's area-to-mass is bounded by
  its own geometry — the largest operated low Earth orbit satellites reach A/m near
  0.05 m²/kg broadside, so `B = C_D A/m` tops out near 0.11 — and the cut is scoped to objects
  that *can* thrust, which is what lets the number be physical rather than arbitrary. It
  applies to the B\* route as well as to the decay fit, because B\* is fitted by the
  element-set producer to the same thrust-driven fall. Debris fitting near the 1 m²/kg
  plausibility cap is high area-to-mass, which is real and common for a fragmentation cloud,
  and is kept. (Added at the Step 3 review; `docs/density-and-drag.md` carries the evidence.)

## The storm term (Phase 3, Step 3)

- **The displacement is derived for a near-circular orbit.** Equation (2) of
  `docs/storm-term.md` linearises the relation between the energy loss and the mean motion,
  which is a near-circular statement. The general drag integral `rho |v_rel| (v_rel . v)` is
  carried through it, so the perigee weighting of an eccentric orbit is right, but the
  derivation itself is not. Eccentric orbits get the term with that caveat and no other.
- **The closed form is verified, not asserted.** `s = (3/4) B drho v² t²` against a
  Runge-Kutta integration of the same orbit with a step density change: 0.24 % at worst
  (300 km, seven days, doubled density), better than 0.05 % at 400 km and above. The error is
  the closed form holding `v` fixed while the real orbit decays, and it grows with the decay,
  exactly as it should.
- **The term is applied at the *stored* time of closest approach, and this is exact rather
  than approximate.** The encounter plane is perpendicular to the relative velocity, and the
  component of a shift along that direction is precisely the part that moves the TCA rather
  than the miss at it; the projection removes it. Nothing rescreens.
- **The excess is measured against SGP4's own atmosphere**, through the element set's B\*,
  which the entry above describes as noisy. An object whose B\* is nonsense has a nonsense
  implied density and therefore a nonsense excess. The coefficient's source label travels with
  every risk row for this reason.
- **Past the linear theory an event is unscoreable and carries no probability at all.** The
  derivation holds the semi-major axis fixed, so it is a small-perturbation statement. Every
  object's shift carries the implied decay as a fraction of `a` and the displacement in orbit
  circumferences. Past a quarter of a revolution of displacement the term has stopped being a
  correction to a known position and has become a claim about where in its orbit the object is,
  which nothing here can support — so every event involving such an object is reported
  **unscoreable**: NaN in `pc`, `pc_shift_only`, `pc_variance_only`, `pc_alfano`, `pc_chan` and
  `pc_max`, `unscoreable` as the region and the flag, the reason on the row, and excluded from
  every aggregate. The geometry, the covariance and the shift stay; only the number a reader
  could act on is withheld. The decay-fraction test, one part in a thousand, is the wider one
  and still labels the covariance source `!extrapolated` without withdrawing the event.
  (Changed at the Step 3 review: it was a label on a reported number.)
- **The density model's uncertainty is entered as a *storm-response* error, not an absolute
  one.** The absolute part cancels against a coefficient fitted through the same model, so
  30 % of the scenario density is carried for a fitted coefficient and that in quadrature with
  15 % for a `bstar` or `typical` one, where the cancellation does not apply. Both are priors
  until Step 4 measures them against May 2024. The term is applied **coherently in time**,
  because a model bias is not a fresh random number every three hours.
- **The index uncertainty is evaluated, not differentiated.** There is no closed form for the
  density's response to ap, so the whole track is recomputed with every interval's ap raised by
  its own `ap_sigma` and the difference in the displacement is the term.
- **`quiet` applies no storm term at all.** It is the Phase 2 model untouched, which is what
  the regression baseline requires and what makes every other scenario a readable difference
  from it. The alternative — applying the term under observed conditions — would make the
  baseline move whenever the density model changed.
- **The shift is zero at each object's own element-set epoch**, by construction. A run screened
  on fresh element sets shows a smaller storm effect than one screened on week-old sets, which
  is correct and is worth knowing when comparing two runs.
- **No coefficient means no shift**, labelled `storm:none`. That is a statement that the
  displacement is unknown, not that it is zero, and the two must not be read alike.
- **Three probabilities per row, because the scenario does two things.** `pc` (the objects
  moved and the covariance grew), `pc_shift_only` (moved, scored against the covariance the run
  would otherwise have had) and `pc_variance_only` (covariance grown, objects left where their
  element sets put them). They are not decomposable into each other — the probability is not
  linear in either input — so all three are computed rather than one being inferred.
- **The relative shift, not either absolute shift, is what changes a miss.** Both objects'
  in-track displacements are rotated out of their own RIC frames and differenced in TEME; the
  scalar difference of the two in-track components is *not* a displacement, because the two
  frames are different. `relative_shift_km` on every row is the vector norm of the difference.
- **The two objects' displacements are nearly independent, and no cancellation is claimed
  between them.** The relative shift is a median **1.91 times** the mean of the two objects' own
  shifts, out of a maximum of 2, flat across coefficient-source pairs and flat in the altitude
  difference between the two orbits (rank correlation −0.10), and reproduced at 1.87 on the
  independent May 2024 replay. The two in-track shifts are uncorrelated (r = 0.08) and the median
  angle between the two in-track directions at the encounter is 120°, because a screener finds
  crossing pairs — a low relative speed is what stops two objects closing on each other. That a
  storm *lowers* the probability on most events is measured and stands; the reason is that a
  displacement of tens of kilometres applied to a miss of a few separates more pairs than it
  creates, and the tighter the miss the more surely it does.
  > **Corrected at the Step 4 review (2026-09-03).** Step 3 explained the same result by
  > *common-mode cancellation* — both objects displaced alike, so only a small relative shift
  > reaching the miss. `driftwatch storm-check` was built to test that claim and refuted it. The
  > wording is withdrawn wherever it appeared; the result is not. `docs/storm-term.md` carries
  > the measurement.

- **The weather table must reach behind the oldest element-set epoch in a run**, not merely
  cover the screening window: the shift is integrated from each object's own epoch, and NRLMSIS
  wants 57 hours of ap history behind the first sample. A short table returns part-NaN density
  tracks whose unusable samples are zeroed, which *understates* the shift silently. It is now an
  exception rather than a warning (`storm.scenarios.WeatherTableTooShort`) and a test pins it.

### Storm-term validity

- **The storm term is predictive at r = 0.88 for an object whose ballistic coefficient was
  measured from its own decay, and has no demonstrated skill otherwise.** Over the free-flying
  May 2024 population as a whole the predicted and observed in-track shifts correlate at
  **−0.10**, which is nothing; restricted to objects with a `history` coefficient it is **0.88**,
  with a magnitude between 0.65 and 1.3 times observed depending on the estimator. A `bstar`
  inversion has no predictive power for the shift at all — regression slope −1.39 — and a
  `typical` stand-in is a population median that was never a measurement of the object. So the
  coefficient's source is not a provenance note; it is the difference between a measured quantity
  and an extrapolation.
- **Every event therefore carries `storm_validity`, taken from the weaker of its two objects'
  coefficient sources.** `validated` when **both** objects have a `history` coefficient;
  `indicative` when either rests on a B\* inversion, a `typical` stand-in, or no coefficient at
  all; `none` under a scenario with no storm layer, which is `quiet` and any plain labelled
  rescore. Two measured sides is the only case the validation covers, so it is the only case
  called validated. `storm_source_primary` and `storm_source_secondary` say which side was the
  weaker one.
- **Every aggregate is reported both ways.** The weekly report, `driftwatch storm-check` and the
  viewer's storm panel give each figure over the `validated` events and over the `indicative`
  ones separately as well as combined, and never a combined figure alone. A single median over a
  population that is mostly `indicative` reads as a measurement and is not one: on the demo run
  1,782 of 2,993 objects have a measured coefficient, so a majority of *objects* are validated
  and a minority of *events* are, because an event needs both sides.
- **`indicative` is not a smaller number, it is an unmeasured one.** Nothing is downweighted,
  widened or withheld on the strength of the label — the sigma an `indicative` object carries is
  the one Step 3 derived, unchanged. The label says the validation does not reach it. Whether a
  B\*-only object should instead take a wider storm sigma is a Step 4 review question and is
  deliberately unanswered here.

## Validation against the record (Phase 3, Step 4)

Full account in `docs/storm-validation.md`. What is approximate about the *measurements*:

- **The later element set is not truth.** The in-track error measured is the disagreement
  between two fits, each with its own error of hundreds of metres to kilometres. It is a floor
  on the propagation error, not a measurement of it. Over the storm the disagreement runs to
  tens of kilometres and the floor is far below it; in the quiet control it is not, and the
  control's numbers are an upper bound on what SGP4 alone contributes.
- **The observed density ratio assumes `B` is constant between the two windows.** Over three
  weeks with the manoeuvre intervals excluded that is good. For an object whose attitude mode
  changed it is not, and nothing in public element sets can see an attitude change.
- **The modelled ratio integrates along each object's pre-storm orbit for both windows.** Over
  three days of storm the semi-major axis moves a few kilometres at these altitudes, small
  against a 50 km scale height.
- **The quiet control window was not perfectly quiet.** Kp stayed at or under 4 across 25 to
  28 April 2024, which is a quieter atmosphere than the storm and is not a solar-minimum
  baseline. The measured enhancement is correspondingly conservative.
- **Both samples are survivorship-biased against the objects a storm affects most.** The May
  2024 selection is drawn from today's catalogue, so the 3,891 objects that were in orbit on
  9 May 2024 and have decayed since cannot be in it. The February 2022 case has the same bias
  arriving from the other direction: 32 of the 49 satellites lost were never assigned catalogue
  numbers at all, so the public record holds 17 of them.
- **The control subtraction is matched on lead time in whole days**, taking the median of each
  object's control comparisons at that lead. An object with one control comparison contributes
  a single number as its median.
- **The in-track error is measured in the later element set's RIC frame.** The two frames differ
  by the angle the disagreement subtends, under a milliradian for a shift of tens of kilometres.
- **NRLMSIS 2.1's storm-response bias is now recorded, and is not applied.** Over 10 to 13 May
  2024 it **over-predicts** the storm/quiet density ratio by about **22 per cent** (observed
  median 1.68 against a modelled 2.21), with **no resolvable altitude dependence** — 0.83, 0.74,
  0.76 and 0.73 across 450–550, 550–650, 650–800 and 800–2000 km. The published assessments of
  MSIS-class models at storm time mostly find the opposite **sign**, and the two are **not
  measuring the same quantity**: they compare model density at a point against a spacecraft
  accelerometer and report the error in the storm's *peak*, while this compares model density at
  a fixed altitude against density inferred from the *decay of an orbit* and reports the error in
  a three-day *integral* dominated by the recovery. A model that undershoots the peak and
  overshoots the recovery gives both answers with no contradiction, and this method cannot
  separate them because it has no time resolution inside its window. Two further biases here — a
  control window that was not solar-minimum quiet, and survivorship against the objects that
  decayed — both inflate our figure, so 22 per cent is an upper bound on this quantity's error
  rather than a best estimate. `DENSITY_STORM_RATIO_SIGMA_REL` stays a symmetric 0.30 and a test
  pins it, so the record cannot quietly become a calibration.
  `docs/storm-validation.md` §1 sets the two quantities out side by side, with the citations.
- **The February 2022 case is bounded by the catalogue holding 17 of the 49 satellites**, and the
  decay evidence in it rests on six of the thirty-eight lost. No population statistic is quoted
  from six objects, five of which have under a day of element sets; what they establish is the
  comparison the case was pulled for, 79 to 101 km of altitude lost in under a week at 210 km
  against 8.5 km in six weeks for a control group at 500 km. The model's **16 per cent**
  enhancement at 210 km is not read as a failure: at that altitude the baseline density is three
  orders of magnitude above the 500 km value, so a modest multiplier on an already-marginal
  margin is sufficient, and the satellites were in safe mode and could not answer it. The figure
  sits at the low end of the published post-mortems (Fang et al. 2022: 20–30 %; Lin et al. 2022:
  50–125 % at 200–400 km from a physics-based simulation) and nothing is tuned to close the gap.
- **Nothing in the storm term was tuned to any of it.** The measurements are reported and the
  code is unchanged, because adjusting a model against the data that measured it destroys the
  measurement.

## Propagation

- **SGP4 with WGS72 constants, improved mode.** The only correct way to use TLE/OMM
  data. Verified against the official `tcppver.out` to 1e-6 km through the same
  vectorised path the pipeline uses.
- **Error handling.** SGP4 error codes are kept per object and positions are masked to
  NaN. Nothing is silently dropped or plotted at a bogus location.
- **Time.** UTC everywhere; SGP4 evaluation uses split Julian dates so microsecond
  precision is kept. The element-set epoch from OMM carries microseconds, which is finer
  than the TLE format's 0.86 ms resolution.
- **Accuracy of the result.** Not improved by anything here. Public element sets are
  good to hundreds of metres to kilometres at epoch, growing by kilometres per day, worse
  in storms. See `docs/tle-and-sgp4.md`.

## Frames

- **TEME to ITRS (Python).** Astropy with IERS Earth-orientation data (UT1-UTC and polar
  motion). Matches skyfield's rotation to under a millimetre given the same inputs. Beyond
  the IERS table astropy extrapolates and a warning is logged; the resulting error is at
  the tens-of-metres level.
- **TEME to Earth-fixed (browser).** GMST rotation with UTC as UT1, no polar motion (what
  satellite.js does). Error equals the DUT1 rotation plus polar motion, measured at
  about 90 m in LEO and 1.2 km at geostationary radius for the test epoch; bounded by
  roughly 400 m in LEO and 3 km at GEO for any epoch. Invisible on the globe; not used
  for analysis.
- **Geodetic coordinates.** WGS84 ellipsoid. The globe in the viewer is a sphere of
  mean radius 6371 km, so drawn height differs from WGS84 height by up to about 20 km
  near the poles; the hover panel reports the WGS84 value.

## Viewer

- **The conjunctions panel draws Python's numbers and computes nothing.** The pairs, the
  events, the probabilities, the covariance ellipse and the tracks all come from the
  exported bundle. The tracks are TEME positions sampled every 20 seconds from the same
  element sets the screening used, rotated to Earth-fixed in the browser with the GMST
  of each sample's own time, the same approximation the propagation worker makes (UTC
  standing in for UT1, no polar motion, under a pixel).
- **The encounter-plane inset is not to scale in one respect.** The hard-body disc is
  routinely thousands of times smaller than the covariance, so it is drawn at a minimum
  size and the caption states the magnification; the ellipse's minor axis has the same
  floor. The numbers beside the picture are exact.
- **The panel carries a subset of the events.** Every collapsed pair is listed, but the
  individual events only for the flagged pairs, the pairs with an event inside the
  notification box and the highest-probability pairs, with tracks for at most 300 of
  them. The run directory holds every event.
- **SGP4 in the browser.** satellite.js 7 (a port of the same Vallado code, tested
  against the same verification cases), run through its WebAssembly bulk propagator in a
  Web Worker. The Python reference state at the reference time is shipped with the bundle
  and the viewer reports the disagreement it finds. Measured on the 2026-09-01 snapshot:
  median 3.7 m, maximum 8.4 m over 19,183 objects, with identical error status on every
  object. The difference comes from the OMM epoch being rounded to milliseconds by
  JavaScript `Date` parsing (up to 0.5 ms times orbital speed) and is far below the
  catalogue's own accuracy. Frame compute time with the WebAssembly path is about 11 ms
  for the whole catalogue.
- **Interpolation between worker frames.** The worker computes positions and velocities
  on a time grid; the GPU interpolates with a cubic Hermite polynomial between grid
  points. For a 90-minute orbit and a 60-second grid step the interpolation error is
  under 10 m; the grid step grows with playback speed and the error with it (about 8 km
  at a 12-minute step), still under a pixel at globe scale.
- **Globe radius.** Positions are scaled by 100 / 6371 km into scene units, so the
  globe is a sphere. Objects are drawn as fixed-size points regardless of their real
  size or distance.

### Storm mode and replay (Phase 3, Step 5)

- **The scenario control changes numbers in the panel and nothing else.** The point cloud, the
  propagation worker and the drawn tracks are geometry, and geometry does not depend on the
  scenario. A storm displaces an object *along* the track already drawn, by tens of kilometres
  against a covariance of kilometres, and redrawing the track at the displaced position would
  assert a precision the covariance denies. So the displacement is a number in the panel. This
  is also what keeps Phase 1's frame budget: switching scenario costs one re-render of a list.
- **The miss shown under a scenario is the shifted miss.** `miss_km` is what the two element
  sets predicted and `miss_shifted_km` is where the scenario's term put them, which is what its
  probability was computed from. Everything that summarises a scenario — the queue, the pair
  rollup, the report's tables — reads the shifted one; the detail view and the per-event tables
  show both, and their difference is the storm's whole effect on the geometry.
- **`scenarios.json` is a lazily fetched overlay, not a second bundle.** It carries only the
  columns a scenario changes, in arrays parallel to the base bundle's events and pairs, and is
  requested on an idle callback after first paint. Label columns are dictionary-encoded. On the
  demo run it is 1.2 MB for three scenarios against a 3.4 MB base bundle, and none of it is on
  the critical path. If it fails to load the viewer says so and goes on showing the one scenario
  the bundle carries, which is a complete answer rather than a degraded one.
- **The Δ against quiet is suppressed where both probabilities are below 1e-12.** A storm that
  takes an event from 1e-95 to 1e-24 has multiplied it by 1e71 and changed nothing anybody could
  act on. Below that floor the two numbers are indistinguishable from zero and their ratio is
  numerical noise — the same floor `driftwatch storm-check` bands on. Where one side is below it
  and the other above, the cell reads `↑ from ~0` rather than an exponent, because crossing the
  level at which a probability means anything is the statement worth making.
- **Replay is a mode, not a second page.** The globe, the camera, the clock, the transport
  controls and the animation loop are created once and live for the life of the tab; the
  *catalogue* — the bundle, the point cloud, the worker, the frame store, the conjunctions panel
  and the storm control — is mounted and unmounted around them against
  `web/public/data/replay/` or `web/public/data/`. Nothing of the replay bundle is fetched until
  a reader enters it, and `?replay` still goes into the address bar through `pushState`, so a
  replay is a link somebody can send and the Back button leaves it.
  (Changed at the Step 5 review, 2026-09-03: the first build entered replay by reloading the
  page, which was simpler and cost the reader their camera, selection and scenario every time
  they crossed the boundary.)
- **What carries across a mode switch, and what does not.** Carried: the camera, the *position
  through the window* as a fraction (the two windows are the same length two years apart, so
  "four days in" is the only part of a 2026 instant that still means anything in May 2024), the
  playback speed and whether it was playing, the category and band filters **by name** rather
  than by index, the selected object **by NORAD id**, and the scenario — remembered **per mode**,
  because a replay run is scored under `quiet` and its own observed record while the live run is
  scored under quiet, forecast and the storm levels, so one carried value would drop a reader's
  G5 on the way in and fail to restore it on the way out. Not carried: an absolute time, an
  object the other catalogue does not hold, and a scenario the other run was not scored under.
- **The worker is replaced rather than re-initialised.** The WebAssembly bulk propagator is
  allocated for a fixed object count; re-initialising it for a different catalogue would leave
  the previous allocation resident with nothing to free it. The script is already cached, so the
  cost of a fresh worker is the WASM instantiation alone. Every listener a mounted catalogue
  attaches goes on one `AbortController`, so unmounting cannot leave a handler behind to fire
  against a catalogue no longer on screen.
- **The replay scrubber is the simulation clock.** There is no second timeline. The Kp bar is
  the clock's background, and the density readout, the Sun image and the objects all read the
  same `tMs`, which is what makes them move together by construction rather than by
  synchronisation.
- **Kp is read from the interval the clock is inside, not the nearest one.** Kp is a three-hour
  average; showing the next interval's value before it has happened would be a small forecast.
- **The replay's density ratio is NRLMSIS at a fixed altitude, averaged over 24 local solar
  times, over the same average across the Gannon quiet control window.** The day-night contrast
  at these altitudes is a factor of two, so a single longitude would make the ratio a coin toss.
  The denominator is deliberately the one Step 4's measurement used, so the number on screen and
  the number in `docs/storm-validation.md` mean the same thing. It is a ratio at a *fixed
  height*, not along any orbit, and it is uncorrected for the 22 per cent over-prediction that
  same section records.
- **A Sun frame is the nearest image Helioviewer holds to the time asked for**, which during a
  data gap can be hours away. The lag is carried on every frame and the viewer renders it above
  15 minutes.
- **The Sun loads lazily, over an inline placeholder.** Four frames a day at 512 px is 29 images
  and 10.4 MiB for a seven-day replay, which is not a thing to fetch before a reader has looked
  at anything. Each frame is fetched from Helioviewer **twice**: the full 512 px image, which
  stays a file, and a 64 px — now 32 px — thumbnail of the same disc, which is the identical
  request at a coarser `imageScale` and needs no image library. The thumbnails travel **inline in
  `storm.json` as data URIs** (about 3 kB each, 121 kB for the whole timeline against 360 kB for
  one full frame), so every scrub position has a picture the instant the file parses; the full
  image is requested when the playhead comes within six hours of it, at most one at a time, and
  the three the exporter marks `eager` — the first, the peak and the last — are requested up
  front. The placeholder is blurred **and captioned as a preview**, because a 32 px disc
  presented as the Sun at a stated minute would be a small lie.
  (Measured at the Step 5 review: a 64 px thumbnail came out at 9.8 kB, because Helioviewer
  renders a 24-bit PNG of a noisy image, so 29 of them inline was 280 kB of JSON. The thumbnail's
  size is now part of its cache filename, because without that a change to
  `HELIOVIEWER_THUMB_PX` went on serving the old size for ever.)
- **The replay fleet is not the demo fleet.** Sentinel-1A stands in for Sentinel-1C, which did
  not launch until December 2024. `fleets/demo-2024.yaml` records the substitution.

## Not yet modelled (later phases)

- Manoeuvres, beyond the three-valued flag, the history check and the Starlink
  supplemental sets.
- Thrust as a *modelled* force. An object under continuous low thrust is detected and refused a
  drag coefficient (below), which keeps the wrong number out; it does not put the right one in.
  A satellite raising or lowering itself is not predictable from public element sets at all.
- Thermospheric winds, attitude changes, radiation pressure, and any density model other
  than NRLMSIS.
- Velocity covariance, cross-terms between RIC components, long-encounter corrections.
