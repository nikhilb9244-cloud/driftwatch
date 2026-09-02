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
- **Miss distances are between SGP4 trajectories.** Stage C finds the closest approach
  of two propagated element sets to microseconds and metres, which says nothing about
  how close the two spacecraft come: the element sets themselves are good to hundreds of
  metres to kilometres. The probability layer below attaches the uncertainty.
- **Stage A uses mean apogee and perigee with a 50 km pad.** Brouwer mean values differ
  from the osculating orbit by several kilometres, and drag lowers an orbit by a few
  kilometres a week (more for an object about to decay, and in a storm); the pad, which
  also has to cover the 35 km screening radius, absorbs both. A secondary whose
  perigee rises or falls by more than the pad's slack inside the window (a manoeuvre, or
  the last days of a decay) can be missed by Stage A. Objects with a mean perigee below
  120 km are dropped outright.
- **Stage B's no-miss guarantee rests on a speed bound.** The relative speed of a pair
  is bounded by the sum of the two-body perigee speeds from mean elements, times a 2 %
  margin for SGP4's departures from Keplerian motion. The bound is derived and tested in
  `docs/screening.md`; it fails only if an SGP4 trajectory moves more than 2 % faster
  than its two-body perigee speed, which does not happen above 120 km.
- **A maximum and a minimum inside one step** (30 s) would defeat the sign-change
  candidate rule. That needs a relative speed of metres per second (co-orbital objects),
  for which the sampled separation is already within metres of the true minimum; the
  sampled-minimum fallback catches it. Never triggered on the 2026-09-01 catalogue.
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
- **SpaceX's published covariance is used as published, and it is not the same quantity as
  ours.** Inside a file's 72-hour validity a Starlink secondary's covariance is SpaceX's own,
  interpolated on a ten-minute grid and labelled `spacex-ephemeris`; outside it the base
  model serves and reports its own label. Three things to hold on to. Past about ten hours
  their numbers are a stated envelope on round figures (100 m radial, 1,000 m in-track, 10 m
  cross-track) rather than a propagated covariance. It is the uncertainty *within* one
  published plan, while the supplemental-consistency fit measures the uncertainty *of the
  plan being revised*, which is roughly eleven times larger at three hours and is the part a
  seven-day screen depends on; the two are reported side by side rather than merged. And the
  geometry driftwatch propagates is CelesTrak's SGP4 fit to that ephemeris, not the
  ephemeris itself, and that fit's own published residual of about 0.2 km is larger than
  SpaceX's sigma for the first several hours — so inside that range the covariance is
  tighter than the trajectory it is attached to. Applying the fit residual as a floor is
  implemented (`add_fit_rms_floor`) and off by default; it is a Step 0 review question.

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

## Not yet modelled (later phases)

- Manoeuvres, beyond the three-valued flag, the history check and the Starlink
  supplemental sets.
- Atmospheric density beyond SGP4's built-in power law; storms, and the storm term in
  the in-track covariance (Phase 3).
- Velocity covariance, cross-terms between RIC components, long-encounter corrections.
