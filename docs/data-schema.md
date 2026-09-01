# Data schema

All on-disk products live under `data/` (git-ignored) except the viewer bundle, which is
written into `web/public/data/` so Vite serves it. Times are UTC throughout.

## Cache: `data/cache/celestrak/`

Raw downloads, kept verbatim so a snapshot can be rebuilt offline.

- `gp/<group>.json`: the OMM record list exactly as CelesTrak returned it.
- `gp/<group>.meta.json`: `fetched_at`, `n_objects`, URL and the User-Agent used.
- `satcat.csv` and `satcat.meta.json`: CelesTrak's satellite catalogue metadata.
- `supplemental/<file>.json` and its `.meta.json`: CelesTrak's supplemental GP data
  (`sup-gp.php?FILE=starlink`), element sets fitted to operator ephemerides, in the same
  OMM shape. Records for satellites not yet catalogued carry placeholder ids of 100000
  and above.

The fetcher refuses to re-download a group or a supplemental file younger than two hours
(CelesTrak's rule) or SATCAT younger than a day.

## Cache: `data/cache/spacetrack/`

Raw Space-Track downloads. Nothing here ever contains the credentials; the metadata
records the query URL, the fetch time and the count only.

- `gp.json` and `gp.meta.json`: the current catalogue from the `gp` class (no decay
  date, epoch within 30 days), as Space-Track returned it (every value is a string). The
  metadata keeps the times of the last day's pulls so the fetcher can enforce a two-hour
  floor and at most four pulls per rolling 24 hours.
- `gp_history/<start>_<end>_<n>ids_<digest>.json` and its `.meta.json`: one file per
  `gp_history` request, keyed by the date range and a digest of the sorted NORAD ids.
  Space-Track asks for history to be requested once and kept, so these are never
  re-fetched.

## Snapshot: `data/snapshots/gp_<YYYYMMDDTHHMMSSZ>.parquet`

One row per object, one file per fetch, zstd-compressed, schema version recorded in the
parquet metadata as `driftwatch_schema_version`. Column order is fixed by
`SNAPSHOT_SCHEMA` in `driftwatch.catalogue.snapshot`.

| Column | Type | Meaning |
| --- | --- | --- |
| `norad_id` | int32 | Catalogue number. Unique within a snapshot. |
| `name` | string | Object name as published. |
| `object_id` | string | International designator, e.g. `1998-067A`. |
| `epoch` | timestamp[us, UTC] | Element-set epoch. |
| `mean_motion` | float64 | Revolutions per day (Kozai mean motion, as in the TLE). |
| `eccentricity` | float64 | Mean eccentricity. |
| `inclination_deg`, `raan_deg`, `arg_perigee_deg`, `mean_anomaly_deg` | float64 | Mean angles in degrees. |
| `bstar` | float64 | SGP4 drag term, inverse Earth radii. |
| `mean_motion_dot`, `mean_motion_ddot` | float64 | TLE-convention derivatives (already divided by 2 and 6), rev/day^2 and rev/day^3. Ignored by SGP4. |
| `ephemeris_type` | int8 | Always 0 for public data. |
| `classification` | string | `U` for unclassified. |
| `element_set_no`, `rev_at_epoch` | int32 | Bookkeeping from the TLE. |
| `period_min` | float64 | 1440 / mean_motion. |
| `semi_major_axis_km`, `apogee_km`, `perigee_km` | float64 | **Mean-element** values recovered by the sgp4 library at initialisation. Not osculating; good to a few km. Altitudes are above the WGS72 equatorial radius (6378.135 km). |
| `object_type` | string | SATCAT: `PAY`, `R/B`, `DEB` or `UNK`. |
| `category` | string | See below. |
| `altitude_band` | string | See below. |
| `rcs_m2` | float64 | SATCAT radar cross-section in square metres, NaN if unpublished. |
| `owner` | string | SATCAT owner code, e.g. `US`, `PRC`, `ESA`. |
| `launch_date` | date32 | From SATCAT, null if unknown. |
| `groups` | list<string> | Every CelesTrak group the object appeared in. Empty for objects that only Space-Track holds. |
| `source` | string | Where the winning element set came from: `celestrak` or `spacetrack`. |
| `fetched_at` | timestamp[us, UTC] | When the snapshot was built. |

An object present in several groups or sources is kept once, with the newest epoch. At
equal epoch the CelesTrak record wins the tie; CelesTrak redistributes Space-Track's
element sets, so equal epochs are the same element set and the tie only decides the
`source` label. The parquet metadata records the CelesTrak `groups` fetched.

### Category rules (in order)

1. SATCAT `DEB` -> `debris`; `R/B` -> `rocket_body`.
2. In the `stations` group -> `station` (ISS, Tiangong and visiting vehicles).
3. Name starts with `STARLINK` or in the `starlink` group -> `starlink`; likewise `oneweb`.
4. Name starts with one of a short list of constellation prefixes (Kuiper / Amazon Leo,
   Qianfan, Hulianwang / Guowang, Iridium, Globalstar, Orbcomm, Flock, Lemur, SpaceBEE,
   Lightspeed) -> `constellation`.
5. SATCAT `PAY` -> `payload`; otherwise `unknown`.

The name rules are heuristics and are marked as such in the code.

### Altitude bands

From mean-element apogee and perigee:

- `geo`: perigee and apogee both within 200 km of 35,786 km.
- `heo`: eccentricity above 0.25 (Molniya, transfer orbits).
- `leo`: apogee below 2,000 km.
- `meo`: perigee at or above 2,000 km and apogee below 35,586 km.
- `other`: everything else (graveyard orbits, LEO-to-MEO ellipses, cislunar).

Both labels describe; neither selects. Screening (Phase 2) picks candidates from
`perigee_km` and `apogee_km` alone, so an object in `unknown` or `other` is screened like
any other. On the 2026-09-01 snapshot `unknown` (618) was 568 uncatalogued
`TBA - TO BE ASSIGNED` analyst objects with no SATCAT row and 50 recently launched pieces
that SATCAT still types `UNK`; `other` (1,258) was 429 orbits straddling the 2,000 km LEO
ceiling (mostly debris) and 829 orbits near or above GEO but outside the 200 km ring (514
of them graveyard orbits). The breakdown is in `docs/phase2-plan.md`.

## Fleet definitions: `fleets/<name>.yaml`

The primaries for screening. These are committed to the repository, not generated. One
YAML document per fleet:

| Key | Type | Meaning |
| --- | --- | --- |
| `schema_version` | int | 1. |
| `name` | string | Short fleet name, used in output file names. |
| `description` | string | Optional. |
| `members` | list | One entry per primary, keys below. |

| Member key | Type | Meaning |
| --- | --- | --- |
| `norad_id` | int | Catalogue number, unique within the fleet. |
| `name` | string | Display name. |
| `hard_body_radius_m` | number | Radius of the sphere that encloses the deployed spacecraft, in metres, in (0, 1000]. |
| `radius_source` | string | Required. The dimensions the radius came from and what was assumed. |
| `manoeuvres` | bool | Whether the object performs orbit manoeuvres. Step 2 flags every pair that involves one. |
| `role` | string | Optional tag: `station`, `sentinel`, `university_cubesat`, `safr`, or anything else. |
| `notes` | string | Optional. |

Unknown keys are errors, so a misspelt `manoeuvres` cannot silently default.
`driftwatch fleet fleets/demo.yaml` validates the file and shows each member as the
latest snapshot knows it (`resolve_fleet()` in `driftwatch.fleet`), flagging members the
snapshot does not hold.

## History: `data/history/gph_<YYYYMMDDTHHMMSSZ>.parquet`

One file per `driftwatch history` run, holding every element set Space-Track's
`gp_history` returned for the requested NORAD ids and date range. Columns are the
element-set columns of the snapshot (`norad_id` through `rev_at_epoch`) plus `source`
(`spacetrack`) and `fetched_at`; the parquet metadata records the ids and the range.
One row per (`norad_id`, `epoch`); a re-issued element set with the same epoch replaces
the earlier one.

`driftwatch.catalogue.history.load_history()` concatenates these files with the
snapshots (which carry the same columns) and keeps one row per (`norad_id`, `epoch`), so
the snapshots taken by the daily fetch and the backfilled history form one table. Step 3
fits per-object covariance from that table; Phase 3 replays storms from it.

## Conjunctions: `data/conjunctions/<fleet>_<YYYYMMDDTHHMMSSZ>.parquet`

One file per `driftwatch screen` run, named by the fleet and the window start, one row
per close-approach event between a fleet member (the primary) and a catalogue object
(the secondary). An event is kept when its miss vector lies inside the RIC box or its
miss distance is inside the watch radius. The parquet metadata records the snapshot
(`driftwatch_snapshot`), the fleet file, the screening configuration as JSON
(`driftwatch_screening_config`, including the step, pad, box, watch radius and the
derived screening radius) and the run summary with per-stage timings. These are the
Step 2 columns; Step 3 adds the uncertainty and probability columns and Step 4 the run
identity, as decided at the Step 0 review (see `docs/phase2-plan.md`).

| Column | Type | Meaning |
| --- | --- | --- |
| `primary_norad_id`, `primary_name`, `primary_category` | int64, string, string | The fleet member; the name is the fleet file's. |
| `secondary_norad_id`, `secondary_name`, `secondary_category` | int64, string, string | The catalogue object, as the snapshot names and classifies it. |
| `tca` | timestamp[us, UTC] | Time of closest approach between the two SGP4 trajectories. |
| `miss_km` | float64 | Separation at `tca`. |
| `rel_speed_kms` | float64 | Relative speed at `tca`. |
| `miss_r_km`, `miss_i_km`, `miss_c_km` | float64 | The miss vector (secondary minus primary) in the primary's radial, in-track, cross-track frame at `tca`. |
| `in_box` | bool | Inside the box: radial within 2 km, in-track and cross-track within 25 km, by default. |
| `within_watch_radius` | bool | `miss_km` at or under the watch radius (25 km by default). |
| `stale_primary`, `stale_secondary` | bool | Element set older than five days at the window start. |
| `manoeuvrable_primary`, `manoeuvrable_secondary` | bool | Known to manoeuvre: the fleet file's flag for members; the `starlink`, `oneweb`, `constellation` and `station` categories for other secondaries. A warning, not a model. |
| `secondary_ephemeris` | string | `gp` or `supplemental`: which element set the secondary was propagated from. |
| `refine_method` | string | `root` (range-rate root inside a sign-change bracket) or `minimum` (golden-section fallback). |

## Propagated state: `data/propagated/state_<YYYYMMDDTHHMMSSZ>.parquet`

One row per object of the snapshot named in the parquet metadata
(`driftwatch_snapshot`), at one instant `t`.

| Column | Meaning |
| --- | --- |
| `norad_id`, `name`, `category` | Copied from the snapshot for convenience. |
| `t` | The requested UTC time. |
| `x_teme_km`, `y_teme_km`, `z_teme_km`, `vx_teme_kms`, ... | SGP4 output in TEME. |
| `x_itrs_km`, ..., `vx_itrs_kms`, ... | Earth-fixed position and Earth-relative velocity via astropy with IERS data. |
| `lat_deg`, `lon_deg`, `height_km` | WGS84 geodetic coordinates. |
| `sgp4_error` | 0 if fine; 1 to 6 per the SGP4 error table. Positions are NaN when non-zero. |

## Viewer bundle: `web/public/data/`

| File | Content |
| --- | --- |
| `manifest.json` | Reference time, counts (total and per `source`), category and band legends, file descriptions, caveats, and the `attribution` lines the data providers require. |
| `objects.json` | Column-oriented arrays: `norad_id`, `name`, `category` (index into legend), `band`, `object_type`, `perigee_km`, `apogee_km`, `period_min`, `inclination_deg`, `epoch_age_days`, `sgp4_error`. |
| `elements.bin` | Little-endian float64, 11 values per object: `norad_id`, `epoch_unix_ms`, `mean_motion`, `eccentricity`, `inclination_deg`, `raan_deg`, `arg_perigee_deg`, `mean_anomaly_deg`, `bstar`, `mean_motion_dot`, `mean_motion_ddot`. |
| `reference.bin` | Little-endian float32, 6 values per object: TEME position (km) and velocity (km/s) at the reference time from the Python sgp4 library, NaN where SGP4 reported an error. |

The viewer rebuilds OMM records from `elements.bin`, initialises satellite.js with them,
and reports the largest disagreement with `reference.bin` at the reference time.
