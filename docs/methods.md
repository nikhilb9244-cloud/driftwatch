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
  publishes were 0.1 to 5 km per satellite on 2026-09-02, and the ephemeris is revised
  as plans change. Used for 10,728 of the 11,094 Starlink objects on the first run;
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
- **A Starlink secondary's covariance comes from its GP history, its geometry from the
  supplemental set.** The GP sets of a manoeuvring satellite disagree by about 10 km
  after a day (the first run's median for Starlink), which measures the manoeuvring
  rather than the tracking and overstates the supplemental set's error (CelesTrak's
  published residuals are 0.1 to 5 km). Until a supplemental-set covariance exists,
  Starlink probabilities are diluted by that sigma; the `cov_source` column and the
  ephemeris flag say which set fed which number.
- **Secondary hard-body radii are category defaults or radar-derived spheres.** 30 m
  station, 10 m Starlink, 3 m OneWeb / constellation / payload, 5 m rocket body, 0.5 m
  debris, 1 m untyped; for payloads, rocket bodies, debris and untyped objects a
  published radar cross-section gives `sqrt(RCS / pi)` clipped to 0.1 to 20 m instead.
  The probability scales with the square of the combined radius, so a factor of two
  here is a factor of four in `pc`; the objects table records which rule applied.
- **The encounter is a straight line.** The two-dimensional method assumes constant
  relative velocity through the encounter and no velocity uncertainty, which holds for
  crossings at kilometres per second and fails for co-orbital pairs at metres per second
  (long encounters). Those pairs are visible by their `rel_speed_kms`; no long-encounter
  correction is applied.
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
- **The Kelvins reconstruction makes two approximations.** The chaser's RTN frame is
  built from the target's with the target's velocity taken as circular, and the
  covariances are used as position-only matrices. The hard-body radius ESA used is
  fitted, not known. The dataset had not been downloaded when this was written; the
  reproduction test is skipped until it is.

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
