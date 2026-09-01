# Reference frames and time scales in driftwatch

## The frames

**TEME** (True Equator, Mean Equinox). The frame SGP4 produces. Its z-axis is the true
celestial pole of date (nutation included) and its x-axis points to the mean equinox of
date (nutation excluded), a hybrid that only exists because the original US Air Force
code worked that way. It does not rotate with the Earth. Relative distances and
velocities between two objects are frame-independent, so Phase 2 conjunction screening
can stay in TEME.

**ITRS** (International Terrestrial Reference System). The Earth-fixed frame in which
ground stations have constant coordinates. WGS84, the GPS datum, agrees with ITRS at the
centimetre level, so for this project they are the same thing. Geodetic latitude,
longitude and height are computed on the WGS84 ellipsoid.

**Not used.** GCRS or J2000, the modern inertial frames. Astropy can take TEME to them,
but nothing in Phase 1 needs an inertial frame other than TEME itself.

## TEME to ITRS

Two rotations, in this order:

1. **Earth rotation.** Rotate about z by the Greenwich Mean Sidereal Time (GMST), the
   angle between the mean equinox and the Greenwich meridian. GMST is a polynomial in
   UT1, the time scale tied to the actual, slightly irregular rotation of the Earth. The
   IAU 1982 expression is used, because that is the one paired with TEME in the SGP4
   literature and in satellite.js.
2. **Polar motion.** Two small rotations (a few tenths of an arcsecond) for the wander of
   the rotation axis relative to the crust. Values come from the IERS.

Astropy implements exactly this as its `TEME` to `ITRS` transformation, using IERS
tables it downloads automatically (`finals2000A.all`) and caches. Where a requested time
lies beyond the table, astropy extrapolates and driftwatch logs a warning. The velocity
it returns is relative to the rotating Earth, i.e. it includes the omega-cross-r term.

`tests/test_frames.py` compares this against skyfield, an independent implementation:

- Feeding skyfield's rotation the same Earth-orientation values reproduces astropy's
  output to under a millimetre, so the matrices and sign conventions agree.
- Skyfield's default timescale has no polar-motion table; the residual against its full
  pipeline is then entirely accounted for by polar motion (up to 8 m in LEO, 55 m at
  geostationary radius).

## Time scales

| Scale | Used for | Notes |
| --- | --- | --- |
| UTC | Everything the user sees, element-set epochs, SGP4 evaluation | TLE epochs are UTC by convention (AIAA 2006-6753). |
| UT1 | GMST | UT1 minus UTC (DUT1) is published by the IERS, within plus or minus 0.9 s. |
| TT, TDB | Not needed in Phase 1 | Astropy handles them internally where a transformation needs them. |

Julian dates are handled in the split form `(jd, fr)` the sgp4 library expects: a
whole part ending in .5 (a midnight) and a fraction of a day, because a single float64
Julian date only resolves to about 10 microseconds. Times are stored as `datetime64[us]`
in UTC.

## The browser's shortcut, and what it costs

The viewer converts TEME to Earth-fixed using satellite.js, which applies the GMST
rotation only, with UTC in place of UT1 and no polar motion. The error is not a guess;
it is measured in `tests/test_frames.py` against the full conversion and shown to be
exactly the sum of two terms:

- **DUT1.** Skipping UT1 rotates every position about the pole by up to 0.9 s of Earth
  rotation. The displacement scales with distance from the axis: about 400 m at the
  surface or in LEO, about 3 km at geostationary radius. In the test epoch (2006, DUT1
  around 0.2 to 0.4 s) the measured errors were 90 m in LEO and 1.2 km at GEO.
- **Polar motion.** About 10 m in LEO, 60 m at GEO.

Both are far below one pixel at globe scale and are irrelevant to relative geometry
between objects, which is why the shortcut is acceptable for the viewer and only there.
The Python state files used for analysis carry the full ITRS conversion.

## Coordinates on the globe

globe.gl places a point at latitude, longitude and altitude on a unit sphere of radius
100 scene units, with the axis convention x = cos(lat) sin(lon), y = sin(lat),
z = cos(lat) cos(lon). An ITRS position `(X, Y, Z)` in kilometres therefore maps to the
scene as `(Y, Z, X) * 100 / 6371`, which the viewer verifies against globe.gl's own
`getCoords` at start-up. The 6371 km mean radius means an object's drawn height above
the sphere differs from its WGS84 height by up to about 20 km near the poles, because
the real Earth is flattened; the hover panel shows the WGS84 value.
