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
    covariance.py         CovarianceModel protocol, empirical power-law fit, pooled fallback,
                          default priors, the ScaledCovariance stand-in                       (step 3)
    manoeuvre.py          three-valued manoeuvre flag and the semi-major-axis jump detector   (step 3)
    pc.py                 Foster polar-grid integration, Alfano 1-D form, Chan series,
                          the covariance-scale sweep for the maximum Pc, the flags            (step 3)
    scenario.py           covariance + probability over stored events, once per scenario     (step 3)
    kelvins.py            ESA Kelvins reproduction                                            (step 3)
  export/
    conjunctions.py       the run directory: events, objects, covariance, one risk file per
                          scenario, the joined export                                        (step 3)
                          + JSON + markdown report + viewer panel data                        (step 4)
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
| 62261 | Sentinel-1C (ESA) | sentinel | 13 | yes | 692 x 694 km, sun-synchronous |
| 27848 | CubeSat XI-IV (University of Tokyo) | university_cubesat | 0.4 | no | 804 x 817 km, sun-synchronous |
| 39446 | UWE-3 (University of Würzburg) | university_cubesat | 0.25 | no | 537 x 606 km, sun-synchronous |
| 39417 | ZACube-1 / TshepisoSat (CPUT) | safr | 5.1 | no | 530 x 587 km, sun-synchronous |
| 55053 | EOS SAT-1 (Dragonfly Aerospace) | safr | 1.5 | yes | 454 x 466 km, sun-synchronous |

"Active SAFR object" is read as SATCAT operational status `+` plus membership of
CelesTrak's `active` group. On the 2026-09-01 SATCAT that is exactly ZACube-1 and
EOS SAT-1. SUNSAT (25636) is still in orbit but marked `-`; every other SAFR entry has
decayed (ZACube-2, the three MDASat-1s, SumbandilaSat). Sentinel-1A was the first choice,
for its long element-set history and because its element set was still at the operational
altitude; the Step 1 review asked for its status to be confirmed, and ESA had ended its
operations on 29 June 2026 (see the Step 1 review below), so the fleet carries Sentinel-1C
instead. XI-IV sits in the 800 km band where the Fengyun-1C and Iridium 33 / Cosmos 2251
fragments are densest; UWE-3 shares ZACube-1's launch and orbit, so the two make a
natural pair in the report.

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

## Step 1 review (2026-09-02)

Approved: the fleet, the radii and the handling of the `unknown` and `other` objects.
Two follow-ups:

- **Sentinel-1A is retired.** ESA's "Time to say goodbye to Sentinel-1A" (30 June 2026)
  records that its operational duties ended on 29 June 2026 after Sentinel-1C and 1D took
  over, and that its orbit will be lowered over the coming months for re-entry within a
  few years. Its 2026-09-01 element set still shows 690 x 692 km, but a retired satellite
  does not manoeuvre to avoid anything, so `manoeuvres: true` would have been wrong.
  Swapped for Sentinel-1C (62261, 2024-235A, launched 5 December 2024, SATCAT `+`, in the
  `active` group, 692 x 694 km): the same bus and radar, so the 13 m radius carries over,
  and its element-set history runs from December 2024, which covers the Step 3 fit window.
- **Two items parked for Phase 4**, recorded in `ROADMAP.md` under Phase 4 and not to be
  built before then: a live impacts panel in the viewer driven by NOAA's R, S and G scales
  from the SWPC feeds Phase 3 already pulls, and a May 2024 replay overlay of Starlink
  round-trip times from public RIPE Atlas probes against the Kp bar.

## Step 2 decisions (screening, built 2026-09-02)

The method, the derivation of the step and the threshold, and the tests are in
`docs/screening.md`; the output columns are in `docs/data-schema.md`. What was decided:

- **Screening radius 35.4 km, not 25.** The box's corner at (2, 25, 25) km lies 35.4 km
  from the primary, outside the 25 km watch sphere, so the sphere Stage B must not miss
  is the box's circumscribing sphere. Both flags are recorded on every event and an
  event is kept if either holds; on the first run 133 events were in the box but outside
  the sphere and 4,872 inside the sphere but outside the box.
- **Speed bound per pair, not a flat 15 km/s.** The relative speed of a pair is bounded
  by the sum of the two objects' two-body perigee speeds from their mean elements, times
  a 2 % margin for SGP4's departure from Keplerian motion. For LEO pairs that is 15.5 to
  15.7 km/s, which is where the prompt's "about 15 km/s" comes from; for an eccentric
  secondary dipping through LEO (a transfer-orbit rocket body at 10 km/s at perigee) it
  is 18 km/s, and a flat 15 km/s would not have been a bound. The bound is attached to
  each pair by Stage A and Stage B derives its threshold from it.
- **Step 30 s.** The threshold is then 35.4 + v_bound x 15 s, about 270 km for LEO
  pairs. At 0.22 microseconds per propagation the week costs about three minutes; 60 s
  would halve that and double the candidates for Stage C, which is cheap either way. The
  step is `--step` on the command line and the threshold follows.
- **Candidate rule.** A sign change of the range rate (approaching to receding) between
  consecutive samples with either sample under the threshold, bracket one step wide;
  plus a sampled local minimum under the threshold with no sign change beside it,
  bracket two steps wide, minimised rather than root-found. The fallback never fired on
  the real catalogue.
- **Stage C without scipy.** A vectorised regula falsi with the Illinois modification and
  Dekker's bisection safeguard, converging in eight to twelve evaluations per candidate
  to 10 microseconds, and a vectorised golden section for the fallback. About 80 lines;
  scipy joins in Step 3 if Foster's integration wants it.
- **Window and staleness.** The window starts at the snapshot's fetch time floored to
  the minute (`--start` overrides) and stale is measured from there.
- **Supplemental Starlink sets** are substituted into the snapshot before Stage A, with
  apogee and perigee recomputed. Placeholder ids (100000 and above, satellites not yet
  catalogued) are skipped; a supplemental set more than a day older than the GP set is
  treated as abandoned. Every event records which set its secondary used.
- **Manoeuvre flag.** The fleet's own flag for members; for other secondaries the
  `starlink`, `oneweb`, `constellation` and `station` categories. Active payloads outside
  those categories are not flagged (see the questions below).
- **Fleet members screen against each other.** A member is a catalogue object too, so
  ZACube-1 and UWE-3 are each other's secondaries; a member's fleet flag is used when it
  appears as a secondary.
- **Output.** One parquet per run, `data/conjunctions/<fleet>_<start>.parquet`, with the
  Step 2 columns and the configuration and summary in the metadata. The Step 0 review's
  schema (run id, scenario, uncertainty, probability) is completed by Steps 3 and 4.
- **Test scaffolding.** `tests/synthetic.py` builds conjunctions with a designed time
  and miss by choosing the secondary's osculating state at the encounter and converting
  it to SGP4 mean elements by fixed-point iteration (sub-millimetre). Step 3's tests can
  reuse it for encounters with a designed geometry.

### First run (2026-09-02; snapshot of 2026-09-01 20:48 UTC; 7 days from 20:48 UTC)

| Stage | Count | Time |
| --- | --- | --- |
| Supplemental Starlink | 11,093 records; 10,728 applied (365 placeholder ids; median epoch lag +0.40 days) | |
| A | 47,908 pairs over 6 primaries; 22,628 distinct objects propagated; 5 dropped as decaying; 1,178 element sets stale | 0.02 s |
| B | 20,163 samples x 22,628 objects = 4.6 x 10^8 propagations; 169,899 candidates, all sign changes | 184 s |
| C | 169,899 refined, none unconverged; 6,016 events (1,144 in the box, 5,883 inside the watch radius) | 2.4 s |
| Total | | 187 s (with the test suite running for part of it) |

| Primary | Stage A pairs | Events | In box | Distinct in-box secondaries | Closest |
| --- | --- | --- | --- | --- | --- |
| ISS | 7,315 | 104 | 11 | 7 | 1.82 km, a rocket body (OBJECT A), 2026-09-02 23:01 UTC |
| Sentinel-1C | 5,065 | 276 | 30 | 22 | 0.53 km, Fengyun-1C fragment, 2026-09-04 05:01 UTC |
| XI-IV | 7,540 | 461 | 60 | 40 | 1.05 km |
| UWE-3 | 6,683 | 605 | 43 | 40 | 0.77 km, SL-14 rocket body at 15.1 km/s, 2026-09-06 01:08 UTC |
| ZACube-1 | 9,580 | 543 | 80 | 61 | 1.61 km |
| EOS SAT-1 | 11,725 | 4,027 | 920 | 332 | 0.049 km, STARLINK-4722 at 13.1 km/s, 2026-09-03 08:57 UTC |

By secondary category: Starlink 4,273; debris 797; payload 649; other constellations
133; rocket bodies 122; unknown 42. 4,249 events used a supplemental set, 64 involve a
stale secondary, 73 % a manoeuvrable one. Relative speed: median 13.3 km/s, 95th
percentile 15.0, maximum 15.8. Miss distance: median 16.7 km.

What the first run says:

- **EOS SAT-1 dominates**, with two thirds of the events (575 a day). Its 454 x 466 km
  orbit sits just below the Starlink shells at 462 to 486 km (the median Starlink
  secondary has a mean perigee of 484 km), and 1,485 of its 1,616 distinct secondaries
  are Starlink satellites. Several are near-co-planar pairs that return every orbit:
  STARLINK-35774 130 times in the week, STARLINK-31598 every 94 minutes at 0.4 to
  1.7 km. These are the pairs where the supplemental sets matter most, and where Step
  3's probability will decide what is worth reporting.
- **The closest approach of the week is 49 m**, EOS SAT-1 and STARLINK-4722 at 13.1 km/s
  on the supplemental set. A 49 m miss between two trajectories each uncertain by
  hundreds of metres or more is not a 49 m miss between two spacecraft; until Step 3 it
  is the same kind of event as a 500 m miss.
- **The ISS is quiet** at 420 km: 104 events, 7 distinct objects in the box, nothing
  under 1.8 km.
- **The performance target is met** with a factor of three to spare, and Stage B is the
  whole cost. Nothing has been parallelised; the SatrecArray loop is single-threaded.

### Questions for the Step 2 review

1. The manoeuvre rule for secondaries: categories only (as built), or also flag every
   payload in CelesTrak's `active` group as "may manoeuvre"? The wider rule flags
   cubesats that cannot manoeuvre; the narrower one misses operational satellites that
   can.
2. The default step: 30 s (three minutes, 170,000 candidates) or 60 s (about half the
   time, twice the candidates). Both satisfy the guarantee.
3. Repeated encounters of one co-orbital pair (STARLINK-35774 130 times): keep every
   event as a row, as now, or collapse repeats of the same pair in the Step 4 report to
   the closest one with a count?

## Step 2 review (2026-09-02)

Approved, including the Sentinel swap. The three questions were answered:

1. **Manoeuvre flag: three-valued.** `known` for constellations and stations as built
   (and fleet members flagged in the file); `possible` for every payload in the active
   group; `none` for debris, rocket bodies and dead payloads. Step 3 adds an empirical
   detector on the history backfill that promotes `possible` to `observed` when the
   semi-major axis jumps between consecutive element sets by more than drag can
   explain, recording the date, and excludes those intervals from the covariance fit.
2. **Step: 30 s stays the default**, exposed as `--step`.
3. **Repeated encounters: keep every row** in the parquet and the JSON. Collapse only in
   the report and the viewer (Step 4), where a pair appears once with the event count,
   the closest miss, the highest probability and the first TCA, and expands on demand.

One design requirement for Step 3: **geometry and probability must be separate.**
Stages A to C run once per snapshot and write the events. Each scenario (quiet, storm,
replay) reruns only the covariance and the probability over the stored events and
writes rows with the scenario, run id, snapshot id and model version from the schema
decision. Nothing in Phase 3 should need to rescreen.

## Step 3 decisions (uncertainty and probability, built 2026-09-02)

The method and its caveats are in the second half of `docs/screening.md`; the files and
columns in `docs/data-schema.md`; the approximations in `docs/methods.md`. What was
decided:

- **The run directory replaces the single parquet.** `data/conjunctions/<fleet>_<start>/`
  holds `events.parquet` (Stages A to C, with both objects' TEME states at TCA and a
  stable `event_id`), `objects.parquet` (hard-body radius, manoeuvre level, covariance
  source per object), `covariance.parquet` (the fitted model), one `risk_<scenario>.parquet`
  per scenario and `conjunctions.parquet`, the joined export of the Step 0 schema with
  one row per event per scenario. `driftwatch risk <run> --scenario <name>` rescores the
  stored events with another covariance model and never propagates an orbit; `--refit`
  redoes the history and the fit; `--scale` wraps the fitted model in a factor as a
  stand-in scenario until Phase 3's storm model exists. The run id is the screening
  run's and is shared by every scenario scored in the directory.
- **History backfill.** 45 days before the window start for the fleet and every Stage A
  survivor (22,628 objects on the demo run), only the element-set fields
  (`predicates`), ids sorted and batched by URL length, every id and day a cached
  request already covers skipped (coverage intervals chained, so a daily rerun asks for
  one new day per id). Space-Track's front end answers a bare 403 to a URL over about
  4 KB (a 3,602-character request was served, a 5,365-character one refused, 2026-09-02),
  so the Step 0 review's 8,000-character budget became 3,500 (about 450 ids; 44
  requests for the demo fleet), and a 403, 413 or 414 on a long URL splits the
  chunk. Two pulls in the same second get distinct file names. The consolidated
  `index.parquet` is built and used as decided at the Step 0 review.
- **The fit.** Per object and RIC component, `sigma(dt) = s dt^p` by profile maximum
  likelihood on an exponent grid (0 to 2.5 by 0.05) over pairs 0.5 to 7 days apart,
  differenced in the newer set's RIC frame, at most 600 pairs per object. Own fit with
  at least 5 sets, 10 pairs and a factor-3 span of propagation times (`empirical`);
  otherwise the (category, band) pool with at least 30 pairs (`pooled:<category>/<band>`),
  else a per-band prior from Flohrer et al. 2008 and Vallado and Cefola 2012
  (`default:<band>`). Diagonal in RIC, floored at half a day. Every object row of the
  covariance table carries the label the model actually uses for it.
- **The detector.** Consecutive sets: the unexplained change in osculating semi-major
  axis is the newer set's value minus the older set propagated with drag; the modelled
  drag change is the difference between propagating with and without `B*`. Raise beyond
  max(100 m, half the drag change); lowering beyond max(100 m, twice the drag change),
  deliberately lenient so that storm-driven decay is not called a burn; a jump the next
  interval reverses is one bad element set, dropped from the fit; gaps over 10 days
  skipped. Pairs spanning a burn are excluded from the fit.
- **SGP4 is not invariant under re-initialisation with drag.** Found while testing the
  fit: a set fitted at a later epoch with the same `B*` drifts in-track by about
  0.07 km per day at `B* = 1e-4` (exactly zero with `B* = 0`). Recorded in the docs as a
  known contribution to the consistency floor; the drag-free test case is kept
  drag-free for that reason.
- **Hard-body radii for secondaries.** Category defaults (station 30 m, Starlink 10 m,
  OneWeb / constellation / payload 3 m, rocket body 5 m, debris 0.5 m, untyped 1 m); a
  published radar cross-section replaces the default with `sqrt(RCS / pi)`, clipped to
  0.1 to 20 m, for payloads, rocket bodies, debris and untyped objects. The objects
  table records which rule applied.
- **Probability.** Foster's polar grid is the reported `pc` (adaptive: at least 24 x 72
  nodes, more when the disc is large against the smaller sigma); Alfano's 1-D form is
  the cross-check that must agree within one percent (it agrees to about 1e-8 over
  aspect ratios to 100 and discs to two sigma); Chan's series is exported as a third
  value and its drift where the disc is comparable to the smaller sigma is recorded, not
  hidden. Closed-form tests: `1 - exp(-R^2 / 2 sigma^2)` at zero miss, the non-central
  chi-square at an offset, and brute-force quadrature for anisotropic cases.
- **The sweep.** `pc_max` over covariance scale factors 0.1 to 10 (61 log steps, parabolic
  refinement), `pc_max_scale` the factor at the maximum; the test recovers the analytic
  `k* = d^2 / 2 sigma_0^2`. Flags on `pc`: red at 1e-4, yellow at 1e-5.
- **Kelvins.** `driftwatch kelvins` and `risk/kelvins.py` are built (frame reconstruction,
  the hard-body radius as a fit parameter over the `risk >= -6` tail, residuals by risk
  bin, the maximum-risk comparison that reads the scaling convention). The dataset was
  not under `data/external/kelvins/` when Step 3 was built, so the reproduction test is
  skipped with a message saying where to put it, and the numbers are still to come.
- **Tests.** 312 pass and 1 is skipped (Kelvins): the closed forms and cross-checks
  above; the fit recovering designed exponents (a period error gives `p = 1`, a timing
  error `p = 0`) through SGP4; the detector finding a planted 1 km burn and a planted
  outlier; the pooled and default labels and the table round trip; the closed form
  reproduced through the whole chain (Stage C geometry, RIC rotation, encounter plane,
  Foster) on a designed conjunction; a rescoring changing the probabilities and not the
  events; the run directory and the joined export; the index and the backfill against
  the fake Space-Track server (batching, coverage, 403/414 splitting, timeouts); the
  `screen` and `risk` commands end to end.

### First run (2026-09-02; snapshot of 2026-09-01 20:48 UTC; 7 days from 20:48 UTC)

The whole command, screening included, took 619 s: Stage B 187 s, history and fit
425 s (backfill 3.5 min, fit 3.5 min), risk 3.6 s. The screening reproduced the Step 2
run to within the day's supplemental update (47,925 pairs, 169,649 candidates, 5,704
events, 1,017 in the box).

| History backfill | |
| --- | --- |
| Window | 2026-07-19 to 2026-09-01 (45 days) |
| Objects | 22,628 (the fleet and every Stage A survivor); all 22,628 had element sets in the window |
| Requests | 44, of 136 to 654 ids each (about 3,500 characters); 3.5 minutes at nine a minute |
| Element sets | 2,129,877; 134 MB of parquet plus a 13 MB index; 1.1 GB of raw JSON in the cache |

The first attempt, with the Step 0 review's 8,000-character URL budget, was refused with
a bare 403 on its first request (1,427 ids); the probes that found the limit are in the
decisions above. A failed backfill now leaves a complete run directory scored with the
stored history, and `driftwatch risk <run> --refit --history on` finishes the job
without rescreening, which is how the numbers below were produced after the pooling
was changed to the median.

| Covariance fit | |
| --- | --- |
| Own fit (`empirical`) | 22,035 objects |
| Pooled | 593 objects (436 LEO debris, 60 untyped LEO objects, 46 HEO debris, 20 Starlink, 9 payloads, the rest in ones and sevens); 16 pools |
| Default | none: every survivor had history |
| Median element sets per object | 72 (debris) to 126 (payloads); 100 for Starlink |
| Pairs per object | capped at 600 for almost every object |

Median own fits by category, in-track sigma at one day and exponent (radial and
cross-track are 50 to 300 m with exponents near 1):

| Category | Objects | sigma_I at 1 d (km) | p_I | sigma_R at 1 d (km) | sigma_C at 1 d (km) |
| --- | --- | --- | --- | --- | --- |
| debris | 6,849 | 0.37 | 1.35 | 0.06 | 0.05 |
| rocket body | 1,081 | 0.41 | 1.30 | 0.08 | 0.07 |
| payload | 3,067 | 0.55 | 1.50 | 0.07 | 0.03 |
| station | 15 | 1.21 | 1.75 | 0.05 | 0.20 |
| constellation | 792 | 3.70 | 1.40 | 0.09 | 0.15 |
| starlink | 9,944 | 10.4 | 1.35 | 0.30 | 0.21 |

Across all own fits the in-track sigma at one day runs from 0.15 km (10th percentile)
through 2.3 km (median) to 13 km (90th), and the in-track exponent from 0.8 to 1.85
with a median of 1.35: drag errors grow faster than linearly, as expected, and the
prompt's "half a day to seven days" window is where the power law holds. Debris and
rocket bodies at a few hundred metres a day agree with the published TLE assessments
that set the default priors. Starlink is the outlier: its GP element sets disagree by
10 km after a day because the satellites manoeuvre between fits, so the GP history
measures the manoeuvring, not the tracking. The events use the supplemental set for a
Starlink's geometry but the GP history for its covariance, which overstates the
supplemental set's error (CelesTrak's published residuals have a median of 0.20 km); a
covariance for the supplemental sets is the obvious next refinement, and the Step 3
review took it.

The pools, after the change to the median of the members' fits (the summed residuals
had given 48 km for Starlink and 37 km for LEO rocket bodies, both set by a handful of
objects); in-track sigma at one day and exponent:

| Pool | Members (fitted) | sigma_I at 1 d (km) | p_I | Uses it |
| --- | --- | --- | --- | --- |
| debris / leo | 6,595 (6,249) | 0.34 | 1.35 | 436 objects |
| debris / heo | 514 (475) | 0.99 | 1.20 | 46 |
| rocket body / leo | 589 (589) | 0.12 | 1.25 | 0 |
| rocket body / heo | 466 (459) | 0.90 | 1.55 | 7 |
| payload / leo | 2,985 (2,979) | 0.55 | 1.50 | 9 |
| constellation / leo | 792 (792) | 3.70 | 1.40 | 0 |
| starlink / leo | 9,964 (9,944) | 10.4 | 1.35 | 20 |
| unknown / leo | 314 (262) | 0.44 | 1.40 | 60 |
| unknown / other | 5 (3) | 139 | 1.95 | 4 (too few fitted members: the summed fit, and a poor one) |

Only 63 events in the run took a pooled covariance on the secondary side.

The fleet's own fits (RIC sigma in km at 1, 3 and 7 days of propagation):

| Member | sigma_R | sigma_I | sigma_C | at 7 days: sigma_I |
| --- | --- | --- | --- | --- |
| ISS | 0.05 | 1.08 | 0.20 | 32.6 |
| Sentinel-1C | 0.06 | 0.31 | 0.05 | 4.3 |
| XI-IV | 0.05 | 0.05 | 0.05 | 0.6 |
| UWE-3 | 0.07 | 0.55 | 0.04 | 8.3 |
| ZACube-1 | 0.06 | 0.58 | 0.04 | 13.0 |
| EOS SAT-1 | 0.07 | 0.46 | 0.01 | 10.3 |

The ISS's in-track sigma of 33 km at seven days (exponent 1.75) is the drag at 420 km
on a body whose attitude and drag area change, plus one reboost in the window that the
detector found and excluded; the ISS's public element sets are known to be poor a week
out. XI-IV at 810 km barely feels drag and stays at half a kilometre after a week.

| Manoeuvre check | |
| --- | --- |
| Objects with at least one jump | 9,893 of 22,628; 132,455 jumps and 8,704 outlier sets |
| By category | debris 1.8 %, rocket bodies 4.8 %, untyped 4.6 %, payloads 14 %, other constellations 43 %, Starlink 89 % (13 jumps each in 45 days) |
| In the objects table (2,993 objects in events plus the fleet) | `known` 1,848, `none` 797, `possible` 305, `observed` 43 |
| Promoted to `observed` | 43 active payloads, among them EARTHCARE, ICEYE-X49, TELEOS-2, YAOGAN-30 05C and GEESAT satellites; 106 events involve one |

| Probability (scenario `quiet`) | |
| --- | --- |
| Events | 5,704; 2,034 in the box |
| Flags | 2 red, 12 yellow, 5,690 none; all 14 flagged events are in the box |
| `pc` above 1e-6 / 1e-8 | 221 / 1,096; 1,210 events underflow to zero (misses of many sigma) |
| `pc_max_scale` | at the 10 edge for 3,872 events (the covariance is smaller than the miss: a larger uncertainty would raise the probability), below 1 for 1,066, at the 0.1 edge for 663 (dilution) |
| Foster against Alfano | largest relative disagreement 6e-12 over the 1,782 events with `pc` above 1e-12 |
| Chan against Foster | median 0, 90th percentile 0.04 %, 99th 0.7 %, worst 55 % (a disc comparable to the smaller sigma) |
| Secondary sigma_I at TCA | median 18 km (Starlink dominated), 10th percentile 1.5 km, 90th 157 km; sigma_R median 0.44 km |

The two reds:

| Primary | Secondary | TCA | Miss (km) | `pc` | `pc_max` (scale) | sigma_I primary / secondary (km) | HBR (m) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISS | YAM-3 (payload, `possible`) | 2026-09-08 19:04 | 11.5 | 1.6e-4 | 1.6e-4 (0.88) | 35 / 30 | 73 |
| ZACube-1 | STARLINK-6053 (`known`, supplemental set) | 2026-09-05 08:36 | 1.9 | 1.0e-4 | 1.0e-4 (0.88) | 5.1 / 4.6 | 15 |

What the first run says:

- **The ISS red is the fit being honest, not a close call.** Seven days out, the ISS
  and YAM-3 are each uncertain by 30 km in-track, the 11.5 km miss is well inside that
  tube, and a 73 m disc inside a 35 x 30 km Gaussian gives 1.6e-4 wherever the miss
  vector sits; `pc_max_scale` of 0.88 says the probability is already near the most it
  could be. This is the known result that public element sets cannot screen the ISS a
  week ahead: the ISS programme uses its own ephemeris and the yellow-red rule on
  numbers three orders of magnitude tighter. The same pair two hours earlier is the
  first yellow.
- **The ZACube-1 red is a real screening candidate**: a 1.9 km miss at 14.8 km/s three
  and a half days out, both objects with 5 km in-track sigma, and a 15 m combined
  radius. It is the only red under 5 km.
- **Two thirds of events sit in the retreat regime** (`pc_max_scale` at the upper edge):
  the fitted uncertainty is smaller than the miss, so the probability is tiny and would
  grow if the covariance were larger. That is where a storm term in Phase 3 will act,
  and it is why `pc_max` is exported beside `pc`: for those events `pc_max` at ten times
  the covariance is the number to watch when the fits are more consistent than they are
  accurate.
- **Starlink covariances need their own treatment.** Every Starlink secondary carries a
  10 km-a-day in-track sigma from its GP history, which is the history of its
  manoeuvres, while its geometry comes from the supplemental set. The Step 4 report
  should say so beside every Starlink event, and a supplemental-set covariance (from
  CelesTrak's published residuals, or from the supplemental sets' own consistency) is
  the obvious next refinement.
- **The cross-checks hold at scale**: Foster and Alfano agree to 6e-12 across the run,
  and Chan drifts only where the docs say it will.


## Step 3 review (2026-09-02)

Approved, with four corrections taken before the viewer work.

### 1. Dilution labelling

The scale at which the maximum probability occurs now classifies every event. Below one,
the event is in the **dilution region**: shrinking the covariance would raise the
probability, so the number is held up by the size of the uncertainty rather than by the
geometry and cannot support a judgement. At or above one it is **robust**. Every risk row
carries `region` and a `confidence` (`low` outside the robust region, `standard` inside),
the report splits the flagged pairs into two sections with the dilution ones marked not
actionable, and the viewer's chips read `red · low`.

The ISS red at 11.5 km is worked through in `docs/screening.md` and summarised in
`docs/methods.md`: seven days out the encounter-plane uncertainty is 13.9 by 0.50 km
against an 11.5 km miss and a 73 m disc, `pc_max_scale` is 0.88, and shrinking the
covariance tenfold drops the probability from 1.6e-4 to 7.1e-7 while a hundredfold
extinguishes it. Better data clears that flag rather than confirming it.

### 2. Supplemental covariance

An object whose geometry comes from a supplemental set is now fitted from the consistency
of successive stored supplemental versions, never from its GP history, with CelesTrak's
published fit residual (`RMS` in the file, median 0.20 km) as a floor in quadrature and
the source labelled `supplemental:consistency`, `supplemental:consistency-p1` (exponent
fixed because the publication gaps span less than a factor of three) or
`supplemental:rms` (only one stored version, so the floor is all there is). Pairs that
span a detected burn are kept for this fit: a supplemental set already contains the
planned manoeuvres, so the difference between two versions is the revision of the plan,
which is the error being measured.

**The rescore.** Two versions were stored (the 06:48 UTC fetch the first run used and an
08:49 UTC one, taken after CelesTrak's two-hour floor had passed), and every one of the
11,092 satellites had been refitted between them. Of the 1,744 supplemental-screened
objects in the run's events, 1,742 had a usable pair. The published epochs were 0.02 to
0.16 days apart, a span of 7.1, enough for the exponent to be fitted rather than fixed:

| | R | I | C |
| --- | ---: | ---: | ---: |
| sigma at one day (km) | 0.51 | 2.18 | 0.28 |
| exponent | 0.85 | 0.55 | 0.85 |

with a median RMS floor of 0.197 km under it. Rescoring the same 5,704 stored events with
`driftwatch risk --refit` (no rescreening, and no Space-Track requests, since the
incremental history found everything already held):

| | GP history | Successive supplemental versions |
| --- | ---: | ---: |
| Median in-track sigma of a secondary at TCA | 18.4 km | 3.9 km |
| Red | 2 | 1 |
| Yellow | 12 | 36 |
| Flagged pairs in the dilution region | 7 of 14 | 31 of 37 |

**ZACube-1 versus STARLINK-6053 does not survive.** Its probability falls from 1.02e-4 to
2.46e-5, out of red and into yellow, and its scale of 0.76 puts it in the dilution region,
so it is now reported at low confidence and is not actionable. The one remaining red is
the ISS against YAM-3, which is an active payload on GP element sets, not a supplemental
object, and is unchanged at 1.58e-4 in the dilution region.

The yellows tripled, which is the expected direction and not a regression: a Starlink
covariance an order of magnitude tighter stops diluting sub-kilometre approaches into
insignificance, so EOS SAT-1's close passes through the Starlink shell now produce
probabilities near 1e-5 where before they were smeared away. Most of them are still in the
dilution region.

Two things to keep in view. The two versions are hours apart, so a power law fitted to
them and evaluated at seven days is a forty-fold extrapolation, and the in-track exponent
of 0.55 is measured over that short baseline alone; it should be refitted as versions
accumulate. And the floor measures the element set against the ephemeris it was fitted to,
never the ephemeris against reality: an operator's published plan can be revised or
abandoned, and nothing here sees that until the next version is published.

### 3. Reproducibility

**Why the Step 2 run had 6,016 events and the Step 3 run 5,704, on the same snapshot.**
The supplemental Starlink sets changed between the two days: the Step 2 run applied
10,728 of them at a median epoch lag of +0.40 days, the Step 3 run 10,727 at +0.70 days.
CelesTrak's cache holds one version and overwrites it, so the older sets were gone and
the difference could not be demonstrated directly. It can now be demonstrated by
elimination: running the Step 2 commit (`6bab1ee`) and the current code over the same
snapshot with `--no-supplemental` gives **5,923 events from both, with every time of
closest approach identical to the microsecond and every miss distance identical to the
bit**. The geometry code did not change; the operator ephemerides did.

So that a run is reproducible from what it records, every supplemental fetch is now
stored as `data/supplemental/<name>_<stamp>.parquet` with the published RMS, `run.json`
and the events parquet record the version used, and `driftwatch report` and
`driftwatch risk` rebuild a run's element sets from its snapshot plus those stored
versions rather than from whatever CelesTrak is serving now.

### 4. History

The backfill is a one-off. `history.backfill()` now reads the newest stored epoch per
object out of the index and asks only for the days after it, batching the ids that share
a start day; an object already held past the window end is not requested at all, and an
object new to the fleet still gets the whole window. A daily rerun of the demo fleet
costs one day of history rather than forty-five.

**Manoeuvre intervals were already excluded from the covariance fit**, as designed: every
pair of element sets whose propagation window contains a detected jump is dropped, along
with every pair involving an outlier set. Measured on four heavily manoeuvring Starlink
satellites from the first run, 19 % to 75 % of the pairs inside the fit window were
discarded for that reason. No fix was needed; the check is now stated in
`docs/screening.md` and covered by a test.

## Step 4 decisions (outputs and viewer, built 2026-09-02)

- **Repeated encounters collapse in the report and the viewer, never in the data.** One
  row per pair with the event count, the closest miss, the highest probability and the
  first TCA, the individual events underneath on demand (a `<details>` block in the
  markdown, an expanding row in the panel). The parquet and the JSON keep every event.
- **A pair's cumulative probability** is one minus the product of the complements over
  its events, reported beside the highest single probability and labelled an upper bound
  wherever it appears: the events are repeated passes of the same two objects from the
  same two element sets, so they are not independent.
- **The report** (`report.md` in the run directory) leads with the flagged pairs split by
  region, then the top twenty by probability and by closest approach, a table per fleet
  member, and a "how to read this" section naming the covariance sources and the
  supplemental version the run used.
- **The viewer bundle** is `conjunctions.json` plus `conjunction-tracks.bin` in the
  viewer's data directory. Every pair is listed; individual events are carried for the
  flagged pairs, the pairs with an event in the box and the highest-probability pairs
  (2.6 MB and 0.4 MB for the demo run). Tracks are TEME positions every 20 s over ten
  minutes either side of the TCA for up to 300 events, rotated to Earth-fixed in the
  browser with the same GMST the propagation worker uses.
- **The panel** jumps the clock to the TCA (the clock's window was widened to cover the
  screening window, which is longer than the propagated one), highlights both objects,
  draws both tracks and opens the encounter-plane inset with the covariance ellipse, the
  hard-body disc, the miss vector, the probability, the maximum probability and its
  scale. The disc is drawn at a minimum size with the magnification stated, because it
  is routinely thousands of times smaller than the covariance.
- **The Kelvins reproduction** ran on the full training set: best single hard-body radius
  9.0 m, median residual +0.22 in log10, 43 % of rows within a factor of two, best in the
  bins an operator acts on. The spread is explained, not tuned away: the residual
  correlates with the target's radar cross-section at -0.63, and fitting a radius per
  quintile of that gives 2, 4, 7, 11 and 13 m with 54 to 66 % within a factor of two
  inside each. ESA used a radius per object; the dataset gives no size for the chaser.
  Our covariance-scale sweep matches ESA's `max_risk_scaling` as a factor on the
  covariance to a median ratio of 0.9999.

## Later steps in one paragraph each

**Step 2.** Built and reviewed 2026-09-02; see "Step 2 decisions" and `docs/screening.md`.

**Step 3.** Built and reviewed 2026-09-02; see "Step 3 decisions", the Step 3 review
above and the second half of `docs/screening.md`.

**Step 4.** Built 2026-09-02; see "Step 4 decisions" above. Phase 2 is complete.

## Review points

One commit per step, stopping after each: Step 0 (Space-Track and history, reviewed
2026-09-01), Step 1 (fleets, reviewed 2026-09-02), Step 2 (screening, reviewed
2026-09-02), Step 3 (covariance and probability, reviewed 2026-09-02), Step 4 (outputs
and viewer, built 2026-09-02, awaiting review). The **ask** items were raised at the
Step 0 review and are recorded as decisions above.
