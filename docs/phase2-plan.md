# Phase 2 plan: conjunction screening

The plan for the phase described in `docs/phase2-prompt.md`, kept in the repository so
it can be reviewed and revised step by step. Decisions that constrain Phase 3 are marked
**ask** and are put to review before they are built, as the prompt requires.

## What Phase 2 delivers

| Step | Deliverable | Command |
| --- | --- | --- |
| 0 | Space-Track as a second catalogue source, plus element-set history | `driftwatch fetch`, `driftwatch history` |
| 1 | Fleet definitions in YAML with hard-body radii | `fleets/demo.yaml` |
| 2 | Three-stage screening, fleet against catalogue, seven days | `driftwatch screen` |
| 3 | Empirical RIC covariance and probability of collision (Foster + Chan) | same command |
| 4 | Conjunction parquet, JSON, weekly markdown report, viewer panel | same command, viewer |

Everything computes in Python in TEME with split Julian dates. The browser displays
exported numbers and never computes a screening result.

## Module layout (target for the whole phase)

```
src/driftwatch/
  catalogue/
    spacetrack.py         Space-Track client: login, rate limiting, gp catalogue, gp_history   (step 0)
    history.py            element-set history store: history parquet files + snapshots       (step 0)
                          + consolidated index keyed by (NORAD id, epoch); batched backfill  (step 3)
    snapshot.py           build_snapshot() now merges a second source by NORAD id            (step 0)
  fleet.py                fleets/*.yaml loading, validation, join to a snapshot               (step 1)
  screening/
    stages.py             Stage A (geometry), Stage B (coarse stepping), Stage C (refine)    (step 2)
    ric.py                RIC frame from a TEME state; relative vectors                       (step 2)
    supplemental.py       CelesTrak supplemental Starlink ephemerides                         (step 2)
  risk/
    covariance.py         CovarianceModel protocol, empirical fit, pooled fallback            (step 3)
    pc.py                 Foster polar-grid integration, Chan series, Alfano max-Pc scan      (step 3)
    kelvins.py            ESA Kelvins reproduction                                            (step 3)
  export/
    conjunctions.py       parquet + JSON + markdown report + viewer panel data                (step 4)
fleets/                   YAML fleet definitions                                              (step 1)
data/history/             gph_<stamp>.parquet from gp_history (git-ignored)                   (step 0)
data/conjunctions/        screening output (git-ignored)                                     (step 4)
```

## Step 0 decisions

### Space-Track rules, as read on 2026-09-01

From https://www.space-track.org/documentation (API and user agreement pages):

- Fewer than 30 requests per minute and 300 per hour. The client keeps a sliding-window
  limiter set below both (20 per minute, 250 per hour) and sleeps when it would exceed
  them.
- GP catalogue: "once every hour". The prompt asks for the same two-hour floor as
  CelesTrak, and for the full catalogue to be pulled at most a few times a day. The
  cache enforces a two-hour floor and a cap of four catalogue pulls per rolling 24 hours.
- gp_history: "1 / lifetime". Every history request is cached permanently by its
  (NORAD ids, date range) key and never re-requested. The results are also written into
  `data/history/` as parquet so analysis never reads the raw cache.
- Credentials come from `SPACETRACK_USER` and `SPACETRACK_PASS`. They are held in a
  `Credentials` object whose `repr` masks them, are sent only in the login POST body,
  and are never written to cache metadata or logs. A test greps the cache directory and
  the log capture for the password after a full mocked session.

### Redistribution

The user agreement says: "The User agrees not to transfer any data or technical
information received from this website, or other U.S. Government source, including the
analysis of data, to any other entity without prior express approval." It then grants an
exception: "USSPACECOM has provided express blanket approval for transfer/redistribution
of basic SSA data and services accessed via www.Space-Track.org conditioned on
appropriate citation. Publications of analysis based on USSPACECOM data also require
appropriate citations." Basic SSA data is defined as "Two-Line Elements (TLEs) and
Orbital Mean-element Messages (OMMs); SATCAT; and Satellite Decay and Reentry Data".

Element sets are OMMs, so they may be redistributed with citation. Decision: the viewer
bundle includes Space-Track-sourced elements, the manifest carries per-source counts and
an attribution list, and the viewer shows the credit line. Conjunction Data Messages are
not basic SSA data; driftwatch never fetches them. If this reading is rejected at review,
filtering the export on the snapshot's `source` column removes the Space-Track rows.

### Merge policy

- One snapshot per fetch, as before. Records from every CelesTrak group and from the
  Space-Track gp query are concatenated and the row with the newest epoch wins per NORAD
  id. At equal epoch CelesTrak wins the tie (the records are the same element set, since
  CelesTrak redistributes Space-Track's data, so this only decides the `source` label).
- `source` records which record won: `celestrak` or `spacetrack`. `groups` still lists
  CelesTrak groups only, so `groups == []` identifies objects that only Space-Track holds.
  No schema change; the schema version stays at 1.
- The Space-Track query is `class/gp`, `decay_date/null-val`, `epoch/>now-30`, which is
  the form Space-Track's own documentation recommends for "the current catalogue".
- SATCAT (CelesTrak's copy) covers every object, so object type, owner and RCS join the
  same way for both sources.

### History store

`driftwatch history --ids ... --start ... --end ...` fetches gp_history in chunks of 200
NORAD ids per request, caches each chunk, and writes one `data/history/gph_<stamp>.parquet`
with the element columns of the snapshot schema plus `source` and `fetched_at`.
`history.load_history()` concatenates the history files with the snapshots and
de-duplicates on (NORAD id, epoch). Step 3 fits covariance from that table; Phase 3
replays storms from it. The per-fetch-file layout was put to review (the alternative was
one partitioned dataset keyed by NORAD id); the decision is recorded below.

## Step 0 review (2026-09-01)

Approved. The redistribution reading was confirmed, and `docs/data-sources.md` now quotes
the blanket-approval clause, records the date it was checked, states that the approval
covers basic SSA data only (GP element sets, SATCAT and decay data, not conjunction
messages nor the emergency and advanced tiers) and gives the citation format. The first
live pull ran at 2026-09-01 20:48 UTC:

| Count | |
| --- | --- |
| Space-Track `gp` records cached | 32,357 |
| Objects in the merged snapshot | 32,361 |
| Objects in no CelesTrak group (Space-Track only) | 13,178 |
| CelesTrak objects that took a fresher Space-Track element set | 46 |

By category: constellation 1,300; debris 10,232; oneweb 654; payload 6,243; rocket_body
2,200; starlink 11,094; station 20; unknown 618. By band: geo 870; heo 1,765; leo 27,843;
meo 625; other 1,258. Space-Track's additions are mostly debris (7,589), payloads (2,639)
and rocket bodies (2,187), with 9,485 of them in LEO. Element-set age: median 0.43 days,
p90 1.72 days, max 29.9 days.

## Decisions taken at the Step 0 review (these constrain Phase 3)

### Covariance model interface (decided)

The screener asks for one object's covariance at absolute times, not at intervals,
because Phase 3 has to look up Kp and density along the real path. The model gets the
object's identity with its category and band, the epoch of the element set the state
was propagated from, and the UTC times the covariance is wanted at:

```python
@dataclass(frozen=True)
class ObjectRef:
    norad_id: int
    category: str  # snapshot category
    altitude_band: str  # snapshot altitude band


@dataclass(frozen=True)
class RicCovariance:
    cov_km2: np.ndarray  # (n, 3, 3) position covariance in the object's own RIC frame
    source: str  # 'empirical', 'pooled:<category>/<band>', 'default', 'storm:<model>'


class CovarianceModel(Protocol):
    def covariance_ric(self, obj: ObjectRef, epoch: datetime, at: np.ndarray) -> RicCovariance:
        """Covariance of ``obj`` at the absolute UTC times ``at`` (datetime64[us]), given
        that its state was propagated from the element set with epoch ``epoch``."""
```

The model returns a full 3-by-3 matrix per time (the Phase 2 fit is diagonal, Phase 3's is
not) plus the source label. The screener does the rotation into the encounter plane and
the combination of the two objects; a model never sees the other object. Phase 3's
`StormCovariance` wraps a base model, integrates the drag-driven along-track variance
from `epoch` to each `at` along the object's path, adds it to element `[1, 1]`, and
labels the result `storm:<model>`.

### Conjunction export schema (decided)

As proposed, plus a run id, the snapshot the run was built from, and a model version,
with one row per event per scenario so a quiet row and a storm row for the same event
are directly comparable and reproducible. Columns of
`data/conjunctions/<fleet>_<stamp>.parquet` and the JSON:

- run: `run_id` (UTC stamp of the screening run plus a short suffix), `snapshot` (the
  snapshot file name), `model_version` (driftwatch version plus the covariance model's
  version string), `scenario` (`quiet` in Phase 2; Phase 3 adds `storm` and
  `replay:<name>`); (`event_id`, `scenario`) is unique within a run;
- identity: `event_id` (the same across scenarios: primary, secondary, snapshot and TCA
  rounded to the minute), `primary_norad_id`, `secondary_norad_id`, names and categories
  of both;
- geometry: `tca` (UTC, microseconds), `miss_km`, `rel_speed_kms`, `miss_r_km`,
  `miss_i_km`, `miss_c_km`, `in_box`, `within_watch_radius`;
- uncertainty: `sigma_r/i/c_primary_km`, `sigma_r/i/c_secondary_km`, `cov_source_primary`,
  `cov_source_secondary`, `hbr_m`;
- probability: `pc`, `pc_chan` (cross-check), `pc_max`, `pc_max_scale`, `flag` (`red`,
  `yellow`, `none`);
- quality flags: `stale_primary`, `stale_secondary`, `decaying_secondary`,
  `manoeuvrable_primary`, `manoeuvrable_secondary`, `secondary_ephemeris`
  (`gp` or `supplemental`).

### History storage (decided)

One parquet per pull stays. Step 3 adds a consolidated index, `data/history/index.parquet`,
keyed by (`norad_id`, `epoch`) and recording which file holds each element set, so a
lookup by object opens only the files that hold it instead of scanning every file. The
index is derived data: it is updated after every history write and can be rebuilt from
the files at any time.

### History fetching (decided)

Space-Track accepts comma-separated NORAD ids in one request, so the Step 3 backfill
batches the fleet members and the Stage A survivors into a few large requests over a
bounded window of about 45 days ending at the snapshot epoch, rather than one request per
object. The chunk size rises from 200 ids to as many as fit a URL of about 8,000
characters; ids are sorted within a chunk and the window is aligned to whole days so
repeated runs hit the same cached requests.

## Step 1 decisions (fleets)

### `fleets/demo.yaml`

| NORAD | Member | Role | Radius (m) | Manoeuvres | Orbit (2026-09-01) |
| --- | --- | --- | --- | --- | --- |
| 25544 | ISS (Zarya) | station | 70 | yes | 417 x 424 km, 51.6 deg |
| 39634 | Sentinel-1A (ESA) | sentinel | 13 | yes | 690 x 692 km, sun-synchronous |
| 27848 | CubeSat XI-IV (University of Tokyo) | university_cubesat | 0.4 | no | 804 x 817 km, sun-synchronous |
| 39446 | UWE-3 (University of Würzburg) | university_cubesat | 0.25 | no | 537 x 606 km, sun-synchronous |
| 39417 | ZACube-1 / TshepisoSat (CPUT) | safr | 5.1 | no | 530 x 587 km, sun-synchronous |
| 55053 | EOS SAT-1 (Dragonfly Aerospace) | safr | 1.5 | yes | 454 x 466 km, sun-synchronous |

"Active SAFR object" is read as SATCAT operational status `+` plus membership of
CelesTrak's `active` group. On the 2026-09-01 SATCAT that is exactly ZACube-1 and
EOS SAT-1. SUNSAT (25636) is still in orbit but marked `-`; every other SAFR entry has
decayed (ZACube-2, the three MDASat-1s, SumbandilaSat). Sentinel-1A was chosen over 1C
and 1D for its long element-set history (Step 3 fits from it) and because it is still
station-kept at the operational altitude. XI-IV sits in the 800 km band where the
Fengyun-1C and Iridium 33 / Cosmos 2251 fragments are densest; UWE-3 shares ZACube-1's
launch and orbit, so the two make a natural pair in the report.

### Hard-body radius rule

The radius of the sphere that encloses the deployed spacecraft, half the diagonal of its
bounding box, rounded up: the "circumscribing 3D sphere" of NASA's CARA guidance
(Mashiku and Hejduk, AAS 19-702, 2019). Each entry records the dimensions it was built
from; where a deployed dimension is not published (EOS SAT-1's panels, UWE-3's antennas)
the file says what was assumed. Two judgement calls are recorded in the file so a
reviewer can flip them: the ISS's flat 109 x 73 x 20 m envelope gives 66 m, rounded to
70 m, which overstates the cross-section for most approach directions; ZACube-1's 10 m
HF wire antenna sets its radius at 5.1 m, against 0.3 m for the bus and short antennas.

### File format and code

`schema_version`, `name`, `description` and a `members` list; each member has
`norad_id`, `name`, `hard_body_radius_m`, `radius_source` (mandatory, a sentence),
`manoeuvres` (a real boolean) and optional `role` and `notes`. Unknown keys are errors so a
misspelt `manoeuvres` cannot default silently; radii must lie in (0, 1000] m. `fleet.py`
loads and validates, and `resolve_fleet()` joins the members to a snapshot, reporting
`in_catalogue`, `in_active_group`, orbit, source and element-set age. `driftwatch fleet
fleets/demo.yaml` prints that table and exits non-zero when a member is missing from the
snapshot; Step 2 refuses to screen in that case rather than silently dropping a primary.

### What is in `unknown` and `other`, and why neither matters for screening

Asked at the Step 0 review, on the 2026-09-01 snapshot.

`unknown` (618 objects) is everything with no usable SATCAT type. 568 are named
`TBA - TO BE ASSIGNED` with no SATCAT row at all: analyst objects that Space-Track tracks
but has not yet correlated to a launch, 220 in the 80000 series and 348 in the 270000
series, 508 of them in LEO (median perigee 826 km), 37 in `other` and 23 in `heo`, with
element sets a median 1.6 days old. The other 50 have SATCAT rows typed `UNK`: 42 pieces
of launches from 2018 to 2026 still called `OBJECT B` and so on (owner `TBD`, `PRC`,
`CIS`), and 8 objects from CelesTrak's `last-30-days` group known only by their
international designator (`2026-188A` to `G`). Classification is by rule 5 of the
category rules: no debris or rocket-body type, no station or constellation match, no
`PAY` type, so `unknown`.

`other` (1,258 objects) is every orbit outside the four bands. 429 straddle the 2,000 km
LEO ceiling with eccentricity at or below 0.25: perigee below 2,000 km and apogee above
it, 308 of them debris, 47 rocket bodies, 37 payloads, 35 analyst objects. 107 of these
have a perigee under 600 km and 43 dip below the ISS. The other 829 sit near or above
GEO but outside the 200 km ring on at least one side: 514 in graveyard orbits (perigee
above 35,986 km) and 315 old geostationary satellites and Transtage rocket bodies
drifting on slightly eccentric orbits (perigee 25,870 to 35,984 km).

Neither label removes an object from the screening candidate pool. Stage A (Step 2)
selects on `perigee_km` and `apogee_km` alone, with the 120 km decay cut; `category` and
`altitude_band` colour the viewer, group the report and choose the pooled covariance
fallback in Step 3. Step 2 ships a test that permutes both labels across the catalogue
and asserts the same Stage A survivors. An analyst object with no SATCAT type is still a
hazard on an orbit; the only consequences of having no type are that its radar
cross-section is unknown (Step 3 uses the category default hard-body radius) and that the
pooled covariance comes from the `unknown` pool for its band.

## Later steps in one paragraph each

**Step 2.** Stage A on mean-element apogee and perigee with a 50 km pad, dropping
perigee below 120 km (flagged decaying) and flagging element sets older than five days.
Stage B steps relative distance with SatrecArray; the step and threshold are derived
together from a 15 km/s maximum relative speed in `docs/screening.md` and proved by a
brute-force test. Stage C brackets each candidate and root-finds the relative range rate
with SGP4 inside the bracket. Output in the primary's RIC frame; box 2 by 25 by 25 km
and watch radius 25 km. Supplemental Starlink ephemerides where available; manoeuvre flag
on every pair with a manoeuvring member. Timings per stage; target under ten minutes.

**Step 3.** Empirical RIC error growth from consecutive element sets, pooled fallback by
category and band, the interface above, Foster polar-grid integration cross-checked by
Chan's series within one percent, the Alfano scale scan for maximum probability, NASA
ISS thresholds for flags, closed-form tests, and the Kelvins reproduction with a fitted
hard-body radius and a residual report.

**Step 4.** `driftwatch screen --fleet fleets/demo.yaml --days 7`, the parquet, JSON and
markdown outputs, and the viewer's conjunctions panel with the encounter-plane inset fed
from Python's numbers.

## Review points

One commit per step, stopping after each: Step 0 (Space-Track and history, reviewed
2026-09-01), Step 1 (fleets), Step 2 (screening), Step 3 (covariance and probability),
Step 4 (outputs and viewer). The **ask** items were raised at the Step 0 review and are
now recorded as decisions above.
