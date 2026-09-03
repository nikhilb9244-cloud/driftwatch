# The frame of SpaceX's Starlink ephemerides is MEME, and only the filename says so

Found 2026-09-03, building Phase 4 Step 1. Written up on its own because it is a trap anybody
using these files can fall into, the failure is silent, and the error it introduces is two
hundred times larger than the one the work was undertaken to remove.

## The finding, in one paragraph

SpaceX's public Starlink ephemerides give position and velocity in **MEME — mean equator, mean
equinox, of J2000**. That is not TEME, the frame SGP4 produces and the frame most conjunction
tooling is written around. Nothing in the file header says which frame the states are in: the
header names the *covariance's* frame, `UVW`, and nothing else. The state frame is declared
**only in the filename**, as the `MEME_` prefix. Read the states as TEME and every position is
wrong by about 44 km at low Earth orbit radius, because precession and nutation have separated
the two frames by roughly 0.36 degrees since J2000.

## What the file actually contains

Fetched from `https://api.starlink.com/public-files/ephemerides/`, 2026-09-03. The first lines
of `MEME_69228_STARLINK-37618_2450923_Operational_1472635440_UNCLASSIFIED.txt`:

```
created:2026-09-02 09:38:06 UTC
ephemeris_start:2026-09-02 09:23:42 UTC ephemeris_stop:2026-09-05 09:23:42 UTC step_size:60
ephemeris_source:blend
UVW
2026245092342.000 774.9155802260 6585.0492066958 1696.6793273830 1.1924944021 1.7600470244 -7.3320882616
4.2423923916e-07 -3.4297392031e-07 7.1550446672e-07 1.7920980827e-10 6.0564076957e-10 1.1172923909e-06 ...
```

Four header lines, then one state every four lines: an epoch, position in km and velocity in
km/s, then the 21 numbers of the lower triangle of the 6×6 covariance. The bare `UVW` line is
the covariance's frame — the radial/in-track/cross-track frame of the satellite itself. It says
nothing about the frame the position and velocity above it are expressed in.

The format is the "Modified ITC" of SpaceX's *Spaceflight Safety Handbook for Operators*, and
the handbook's filename convention is where the state frame lives: `<frame>_<NORAD
id>_<name>_…`. Every file in the manifest on 2026-09-03 began `MEME_`.

## The measurement that settles it

Guessing was not acceptable, so the two readings were tested against an independent trajectory:
CelesTrak's supplemental element sets, which are SGP4 fits to these same files and whose
residual CelesTrak publishes (a median 0.201 km on 2026-09-03). Six satellites, states compared
with SGP4 at the ephemeris start:

| Interpretation | Median distance to the SGP4 fit of the same satellite |
| --- | ---: |
| Read the states as TEME | **36.2 km** |
| Rotate the states J2000 → TEME | **0.356 km** |

0.356 km is CelesTrak's own published fit residual. That is the signature of a correct reading:
the remaining disagreement is exactly the disagreement that ought to be there and nothing more.
36.2 km is the signature of a frame error — a rotation about the pole, not a growing propagation
error.

**So this would have been a 44 km error introduced in the course of fixing a 0.2 km one.** The
whole point of Phase 4 Step 1 was to remove the 0.20 km gap between the trajectory driftwatch
propagates and the trajectory SpaceX's covariance describes. Reading the states in the wrong
frame would have replaced that gap with one two hundred times larger, and it would not have
looked like a bug: the states would still have been smooth, still have interpolated cleanly,
still have produced plausible conjunctions. They would simply all have been in the wrong place.

## What driftwatch does about it

- `orbit/frames.j2000_to_teme` rotates the states on the way in, and **only TEME is stored**, so
  no second inertial frame convention enters the project. The rotation is skyfield's, checked
  against astropy's frame machinery to 0.9 mm in `tests/test_frames.py`.
- `driftwatch spacex` **re-runs the measurement on every fetch** and refuses to write the store
  if it fails (`spacex.check_state_frame`, `config.SPACEX_FRAME_CHECK_MAX_KM`). If SpaceX ever
  changes the published frame without changing the filename convention, or changes the
  convention without anyone here noticing, the fetch stops with an error naming the residual
  rather than quietly poisoning every Starlink event in the run. A one-off check in a test
  would not do that, because the thing being guarded against is a change at the source.
- The frame the file declared is stored beside the states (`state_frame`), so a stored run
  records what it believed rather than what the code assumes today.

## If you are using these files yourself

Three things, in order of how much they will cost you:

1. **The states are MEME/J2000. The header does not tell you.** Read the filename prefix, and
   check it — do not trust either it or this note. Propagate any published element set for the
   same satellite to the ephemeris start and compare. Sub-kilometre means you have it right;
   tens of kilometres means you have a frame error, whatever the arithmetic says.
2. **MEME J2000 and the ICRF differ by the frame bias**, about 23 milliarcseconds, which is
   0.8 m at this radius. Below every other error in the chain and safely ignored — but it is
   the reason a very careful check will not close to exactly zero.
3. **The covariance is in a different frame from the states.** `UVW` is the satellite's own
   radial/in-track/cross-track frame and it moves with the satellite; the states are inertial.
   Rotating one with the other's matrix is a second, quieter way to get this wrong.

## Sources

- Starlink ephemerides and manifest, `https://api.starlink.com/public-files/ephemerides/`, read
  2026-09-03, and the `README.md` at the same path.
- *Spaceflight Safety Handbook for Operators* v1.7,
  `https://www.space-track.org/documents/SFS_Handbook_For_Operators_V1.7.pdf`, for the Modified
  ITC format and the filename convention that carries the frame.
- CelesTrak supplemental Starlink element sets and their published per-object fit `RMS`, read
  2026-09-03, used as the independent trajectory in the measurement above.
- `docs/spacex-ephemerides.md` for the terms these files are used under and what their
  covariance is; `docs/phase4-plan.md` for the step this came out of.
