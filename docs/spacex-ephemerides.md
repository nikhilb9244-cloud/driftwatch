# SpaceX Starlink ephemerides: may we use them, and how?

A Phase 3 Step 0 question. Everything below was checked on 2026-09-02; the endpoints and the
terms both move, so re-check before relying on this.

## What they are

SpaceX publishes a predicted trajectory for every Starlink satellite, with covariance. These
are the operator's own product, not a tracking fit: they contain the manoeuvres the satellite
is *planned* to make, which no element set fitted to past observations can know about. They
are also the upstream source of the CelesTrak supplemental element sets driftwatch already
uses — CelesTrak fits an SGP4 element set to each of these files.

One file per satellite, in the "Modified ITC" format described in the *Spaceflight Safety
Handbook for Operators*. Measured on `MEME_53152_STARLINK-4045_2450325_Operational_...`,
fetched 2026-09-02:

| | |
| --- | --- |
| Size | 2.0 MB per satellite per version |
| Header | `created`, `ephemeris_start`, `ephemeris_stop`, `step_size`, `ephemeris_source`, frame |
| Span | 72 hours from creation, at a 60-second step (4,321 states) |
| Frame | `UVW`, which is the RTN/RIC frame |
| Per state | position and velocity in km and km/s, then the lower triangle of the 6×6 covariance (21 numbers) |
| Source label | `blend` on this file: a blend of the fitted past and the planned future |

## Where they come from now, and what that means for the terms

**They are no longer on Space-Track.** Space-Track announced that from 28 July 2025 it would
stop hosting SpaceX ephemerides on its Public Files page and through the `/publicfiles/` API,
and directed users to SpaceX. Checked directly on 2026-09-02 with our own account: the
directory listing at `/publicfiles/query/class/dirs` still names
`public-data-files-552-spacex-prod`, but `loadpublicdata` returns the NASA-JSC ISS ephemeris
entries whatever directory is asked for, and no Starlink ephemeris is retrievable there.

**They come from SpaceX, without an account.** `https://api.starlink.com/public-files/ephemerides/`
serves a `MANIFEST.txt` listing one file per satellite — 11,092 of them on 2026-09-02, the same
count as the CelesTrak supplemental file — and each named file at that path. Both returned
HTTP 200 with no authentication and no credentials of any kind. The `README.md` at the same
path documents the format, the 8-hour update cadence and the 72-hour horizon, and directs
conjunction correspondence to `starlink.com/satellite-operators`.

**So Space-Track's user agreement does not govern them.** That matters, because it would not
have helped if it did. USSPACECOM's blanket approval to redistribute covers *basic* space
surveillance data — element sets and OMMs, the SATCAT, decay and reentry data — and the
agreement otherwise has the user agree "not to transfer any data or technical information
received from this website … to any other entity without prior express approval". An
owner/operator ephemeris is not basic space surveillance data, so had we taken these files
from Space-Track, redistributing them or products built from them would have needed express
approval. Taken from SpaceX directly, none of that applies.

**SpaceX attaches no published licence.** Neither the README nor the space-safety
documentation states terms of use, a licence, redistribution rights or an attribution
requirement. The files are published, unauthenticated, for the stated purpose of letting other
operators screen against Starlink.

## The finding

**We may use them.** They are published without restriction for exactly this purpose, and no
agreement we are party to limits it. The rule we adopt is the one already applied to CelesTrak's
supplemental data:

- Read them, compute with them, and publish the results, crediting SpaceX for the source.
- Do not republish the raw files or a repackaged copy of them. Nothing grants that, and
  nothing is gained by it: the files are one HTTP request away for anyone.
- Cache politely. One request per satellite per version, only for the satellites a run
  actually needs, and never a sweep of the whole constellation.

## What their covariance actually is

Worth knowing before planning to use it. The published sigmas from the file above:

| Lead | Radial (U) | In-track (V) | Cross-track (W) |
| ---: | ---: | ---: | ---: |
| 0 h | 1.0 m | 1.4 m | 1.7 m |
| 1 h | 2.7 m | 11 m | 2.7 m |
| 3 h | 7.3 m | 62 m | 2.2 m |
| 8 h | 26 m | 576 m | 3.0 m |
| 12 to 48 h | 100 m | 1,000 m | 10 m |
| 60 to 72 h | 350 m | 2,000 m | 550 m |

It grows smoothly for about ten hours, which is a propagated covariance, and then sits on
round numbers — exactly 100 m, 1,000 m, 10 m — until it steps to another set of round numbers
for the last twelve hours. Past ten hours this is a stated envelope, not a fitted uncertainty:
plausibly the satellite's stationkeeping control box, which is a real and meaningful bound but
is not the same quantity as a covariance. Any use of it has to say so.

It is also far tighter than our own measurement of the same thing. The consistency of two
successive CelesTrak supplemental versions gives an in-track disagreement of about 710 m at a
lead of 2.9 hours (`docs/screening.md`); SpaceX's published sigma at 3 hours is 62 m, eleven
times smaller. The two are not measuring the same thing — ours includes the revision of the
plan between versions, theirs is the uncertainty within one plan — and the difference is
roughly the size of that revision. For screening, the revision is the part that matters.

## Plan for the later step

Not built now. When it is built:

1. Fetch the ephemeris only for Starlink secondaries that appear in a run's events, from the
   manifest, and cache by the file's `created` stamp. At 2.0 MB each this is the binding
   constraint: the 1,744 supplemental-screened secondaries of the first live run would be
   3.5 GB per version. Restrict it to the events that could plausibly be flagged, a few
   hundred objects at most, and store only the states near each time of closest approach.
2. Inside the 72-hour horizon, use their covariance directly for the Starlink object,
   rotated from UVW into the object's RIC frame (they are the same frame), and label the
   source `spacex:ephemeris`. Add the version-to-version revision measured from our stored
   supplemental versions, because their covariance does not contain it.
3. **The horizon problem for days four to seven.** The file stops at 72 hours and a
   seven-day screening window does not. There is no version of their covariance for days
   four to seven, and extrapolating a saturated envelope is meaningless. Those days keep the
   supplemental-consistency model, and past its own validity horizon the GP model, exactly as
   now. The report and the viewer must show which of the three served each event, because the
   covariance source changes discontinuously partway through the window.

## Sources

- Starlink ephemerides README, https://api.starlink.com/public-files/ephemerides/README.md, and
  the manifest and a sample file at the same path, read 2026-09-02.
- Starlink Space Safety documentation, https://space-safety.starlink.com/docs/tutorial-basics/trajectories/,
  read 2026-09-02: the operator-facing portal, hourly upload with a seven-day horizon,
  covariance frames ITRF, EME2000 and RTN.
- Space-Track's announcement that it would stop hosting the files from 28 July 2025
  (@SpaceTrackOrg, https://x.com/SpaceTrackOrg/status/1938326343193698325), corroborated here
  by direct query of the `/publicfiles/` API on 2026-09-02.
- Space-Track user agreement and API documentation, https://www.space-track.org/documentation,
  read 2026-09-02, for the blanket approval and its limits.
