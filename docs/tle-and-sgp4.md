# Element sets, SGP4 and what the public catalogue can and cannot tell you

This page is the background a developer needs before trusting a number that comes out
of driftwatch. It is deliberately short; the references at the end go deeper.

## What a two-line element set is

The public catalogue is maintained by the US Space Force's 18th Space Defense Squadron
from radar and optical tracking. For each object it publishes a *two-line element set*
(TLE), or the same content as an *Orbit Mean-elements Message* (OMM), which is what
driftwatch downloads from CelesTrak as JSON. A TLE looks like this:

```
ISS (ZARYA)
1 25544U 98067A   26243.51782528  .00016717  00000-0  10270-3 0  9993
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537
```

Line 1 carries the catalogue number (25544), international designator (1998-067A, the
first object from the 67th launch of 1998), the epoch (day 243.5178 of 2026, in UTC),
two drag-related derivatives that SGP4 ignores, and the `B*` drag term (`10270-3`
means 0.10270e-3, in units of inverse Earth radii). Line 2 carries the six classical
orbital elements at that epoch: inclination (51.64 degrees), right ascension of the
ascending node (247.46 degrees), eccentricity (0.0006703, decimal point implied), argument
of perigee (130.54 degrees), mean anomaly (325.03 degrees) and mean motion (15.72
revolutions per day), followed by the revolution number.

Six elements plus a drag term and an epoch are enough to define an orbit. What they are
not is a measurement of where the satellite is.

## Mean elements are not osculating elements

An *osculating* orbit is the Keplerian ellipse a satellite would follow if every
perturbation switched off at this instant. It changes continuously: Earth's equatorial
bulge (the J2 term of the gravity field) makes the orbital plane precess and the
perigee rotate, and it adds short-period wobbles of a few kilometres to the radius
every revolution. Drag shrinks the orbit. The Sun and Moon tug on high orbits.

A TLE holds *mean* elements: the orbit with those periodic wobbles averaged out
according to one specific analytical theory, SGP4. The elements are fitted to tracking
data by running SGP4 backwards, so they only reproduce the observations when they are
fed through SGP4 again. Put the same numbers into a plain Keplerian propagator, or a
numerical integrator with a better gravity model, and you get a *worse* orbit, typically
off by kilometres, because the periodic terms SGP4 would have restored are missing.

This is also why two element sets for the same object a day apart disagree by hundreds
of metres when propagated to the same time. Each is a least-squares fit to a different
span of tracking data with a simplified force model; neither is "the truth", and the
difference between them is a rough measure of how uncertain either one is. driftwatch
keeps every daily snapshot precisely so that this disagreement can be measured per
object in Phase 2 and used as an empirical covariance.

## What SGP4 does

SGP4 (Simplified General Perturbations 4) is an analytical propagator published in
Spacetrack Report Number 3 (1980) and refined by Vallado and others in 2006. Given mean
elements at an epoch and a time offset, it returns position and velocity in kilometres
and kilometres per second. It models:

- Secular and long-period effects of J2, J3 and J4 (Earth's oblateness and pear shape).
- Atmospheric drag through a simple power-law density and the `B*` coefficient.
- For orbits with periods over 225 minutes, resonance with Earth's rotation and the
  gravitational pull of the Sun and Moon (the "deep space" branch, historically called
  SDP4; the modern combined code handles both).

It is fast (microseconds per evaluation) and it is the *only* correct way to use a TLE.
driftwatch uses the `sgp4` Python package, which wraps Vallado's reference C++ code,
with WGS72 gravitational constants because that is what the catalogue is fitted with.
The package ships the official verification cases (`SGP4-VER.TLE` and `tcppver.out`),
and `tests/test_sgp4_verification.py` reproduces every line of that file through the
same vectorised code path the pipeline uses, to a millionth of a kilometre.

## The output frame

SGP4 positions come out in TEME, "True Equator, Mean Equinox" of date. It is an
inertial-ish frame that is neither the modern GCRS nor Earth-fixed. To draw an object
over a map, or to compare it with a ground station, it has to be rotated into an
Earth-fixed frame. See `docs/frames-and-time.md`.

## Known accuracy limits of the public catalogue

Treat these as the honest error budget behind every number driftwatch shows.

| Source of error | Typical size | Notes |
| --- | --- | --- |
| Element-set fit and SGP4 force model, at epoch | 0.1 to 1 km in LEO | Along-track (direction of travel) is the worst axis; radial is best. |
| Growth with time since epoch | 1 to 3 km per day in LEO, worse in low orbits | Mostly along-track, driven by drag mis-modelling. |
| Geomagnetic storms | Several km per day and more | Density rises far above the SGP4 drag model's assumptions; this is the whole point of driftwatch. |
| Manoeuvres | Unbounded until the next element set | Active satellites (Starlink especially) manoeuvre often; the catalogue lags by hours to days. |
| Objects with high `B*` or very low perigee | Can fail to propagate | SGP4 reports error codes 1 to 6; driftwatch keeps the code and masks the position to NaN rather than plotting rubbish. |
| Truncated precision of the TLE format | Metres | Angles to 4 decimals, mean motion to 8; the OMM JSON carries a few more digits. |
| Element-set age | Hours to weeks | Every snapshot records the age distribution; anything older than a few days should be treated as a guess. |

Consequences for later phases:

- Absolute probabilities of collision built on public elements are indicative only.
  Rankings and the *change* between quiet and storm assumptions are the robust product.
- Per-object uncertainty must be estimated, not read from the catalogue, which carries
  no covariance at all.
- For the ISS and Starlink, better ephemerides exist (NASA's public ISS trajectory and
  CelesTrak's supplemental Starlink data); Phase 2 uses them where available.

## References

- Hoots, F. R. and Roehrich, R. L., *Spacetrack Report No. 3: Models for Propagation of
  NORAD Element Sets*, 1980.
- Vallado, D. A., Crawford, P., Hujsak, R. and Kelso, T. S., *Revisiting Spacetrack
  Report #3*, AIAA 2006-6753. The paper behind the reference code and its test cases.
- Vallado, D. A., *Fundamentals of Astrodynamics and Applications*, 4th edition,
  chapters 3 (coordinate and time systems) and 9 (special perturbations).
- Kelso, T. S., CelesTrak documentation on GP data formats,
  https://celestrak.org/NORAD/documentation/gp-data-formats.php.
- Rhodes, B., the `sgp4` package documentation, https://pypi.org/project/sgp4/.
