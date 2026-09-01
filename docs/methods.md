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
  `docs/phase2-plan.md`) grants blanket approval to redistribute TLEs and OMMs, SATCAT and
  decay data with citation. The viewer bundle therefore carries Space-Track-sourced
  elements and the manifest and the viewer show the attribution. Conjunction Data
  Messages are not covered and are never fetched.
- **Element-set age.** Whatever CelesTrak holds at fetch time. The age distribution is
  logged for every snapshot and exported to the viewer per object.
- **Object type and category.** SATCAT object type is authoritative for debris and
  rocket bodies. Constellation membership is inferred from group membership and name
  prefixes; these are heuristics.
- **Apogee, perigee, period.** Mean-element values from the sgp4 library's
  initialisation (Brouwer mean semi-major axis). They differ from osculating values by
  up to several kilometres. Used only for filtering and the altitude bands.

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

- Covariance or any per-object uncertainty (Phase 2, from consecutive element sets).
- Manoeuvres.
- Atmospheric density beyond SGP4's built-in power law; storms (Phase 3).
- The Starlink supplemental ephemerides, which are more accurate than the GP data.
