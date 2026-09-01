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
  in Step 3. The probability of collision scales with the square of the combined radius,
  so this is a first-order choice, and the sphere overstates the cross-section of flat or
  long bodies: the ISS's 70 m sphere is several times its projected area for most
  approach directions, and ZACube-1's 10 m wire antenna sets a radius seventeen times
  that of its bus. Every value and its provenance is in `fleets/demo.yaml`.
- **Manoeuvres.** Not modelled. SGP4 cannot predict a burn; the fleet file flags objects
  that manoeuvre and every event carries a flag for each side. For secondaries "known to
  manoeuvre" is a category rule (Starlink, OneWeb, the other constellations, stations);
  an active payload outside those categories may manoeuvre too and is not flagged. An
  element set issued before a burn is wrong after it by the size of the burn, and the
  error grows with time.
- **Miss distances are between SGP4 trajectories.** Stage C finds the closest approach
  of two propagated element sets to microseconds and metres, which says nothing about
  how close the two spacecraft come: the element sets themselves are good to hundreds of
  metres to kilometres. Step 3 attaches the uncertainty; until then a 50 m miss and a
  500 m miss are the same event.
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
- **Events are geometry only.** Kept when the miss vector lies inside the 2 x 25 x 25 km
  box or within the 25 km watch radius. No probability, no ranking by risk, until Step 3.

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

- Covariance or any per-object uncertainty (Phase 2 Step 3, from consecutive element
  sets), and therefore probability of collision.
- Manoeuvres, beyond the flags and the Starlink supplemental sets.
- Atmospheric density beyond SGP4's built-in power law; storms (Phase 3).
