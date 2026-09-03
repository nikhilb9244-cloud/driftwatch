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
(CelesTrak's rule) or SATCAT younger than a day. The supplemental cache holds one version
and overwrites it, which is why every fetch is also stored under `data/supplemental/`
(below): a run is only reproducible if the element sets it used are still on disk.

## Supplemental versions: `data/supplemental/<name>_<YYYYMMDDTHHMMSSZ>.parquet`

One file per fetched version of a supplemental file, named by the fetch time, which is
the version stamp a run records. Columns are the element-set columns of the snapshot
(`norad_id` through `rev_at_epoch`) plus:

| Column | Type | Meaning |
| --- | --- | --- |
| `rms_km` | float64 | CelesTrak's published RMS of the fit of this element set to the operator's ephemeris, in km. The floor under the supplemental covariance. |
| `fetched_at` | timestamp[us, UTC] | When this version was downloaded; the version stamp comes from it. |

`load_supplemental_history()` concatenates the versions and keeps one row per
(`norad_id`, `epoch`), so a satellite CelesTrak has not refitted between two fetches
contributes one row, not two. Step 3 fits the covariance of supplemental-screened objects
from that table; `driftwatch report` and `driftwatch risk` rebuild a run's element sets
from its snapshot plus the versions it recorded.

## SpaceX ephemeris covariance: `data/spacex/ephemerides_<YYYYMMDDTHHMMSSZ>.parquet`

One row per satellite per stored sample of SpaceX's own published covariance, written by
`driftwatch spacex`. **Derived data, not the files**: only the position covariance is kept,
and only every ten minutes of it, and neither this nor the raw files are ever redistributed
(`docs/data-sources.md`).

| Column | Type | Meaning |
| --- | --- | --- |
| `norad_id`, `name` | int64, string | From the manifest file name. |
| `created` | timestamp[us, UTC] | When SpaceX generated this version. Identifies the version; the newest per satellite is the one used. |
| `ephemeris_start`, `ephemeris_stop` | timestamp[us, UTC] | The file's validity, 72 hours apart. Outside it the base covariance model serves. |
| `ephemeris_source` | string | SpaceX's own label, e.g. `blend`: a blend of the fitted past and the planned future. |
| `t` | timestamp[us, UTC] | The sample time. |
| `cov_rr_km2`, `cov_ri_km2`, `cov_ii_km2`, `cov_rc_km2`, `cov_ic_km2`, `cov_cc_km2` | float64 | The six independent entries of the RIC (their UVW) position covariance in km^2, used as published. |

## Space weather: `data/weather/`

`data/cache/weather/SW-All.csv` is CelesTrak's file as downloaded, with a `.meta.json`
recording the fetch. `data/weather/swpc/<product>_<issued stamp>.<ext>` holds one file per
**issue** of each SWPC product, never overwritten, each with a sidecar:

| Sidecar field | Meaning |
| --- | --- |
| `product` | `kp-forecast`, `kp-realtime`, `outlook-27day` or `solar-wind`. |
| `url`, `bytes`, `fetched_at` | Where it came from, how big, and when it was fetched. |
| `issued_at` | When SWPC issued it. This names the file, so a stored run can be rescored against the forecast it actually used. |
| `issued_from` | How the issue time was determined: `product` (its own `:Issued:` line), `companion` (the three-day forecast text fetched beside the JSON, which carries no issue time of its own), `last-observation` (an observation stream, stamped by its newest sample) or `fetch-time` (the fallback). |

### The three-hourly table

Built on demand by `driftwatch.weather.table.weather_table`, and written by
`driftwatch weather --out`. One row per three-hour interval.

| Column | Type | Meaning |
| --- | --- | --- |
| `t` | timestamp[us, UTC] | Start of the interval (00, 03, ... 21 UTC). |
| `kp` | float64 | Planetary K index, snapped to thirds. |
| `ap` | float64 | The interval's ap in nT; from the Bartels table where only Kp was published. |
| `ap_sigma` | float64 | Standard deviation of that ap in nT, which is what Step 3's variance term consumes. Half a Bartels step on a measurement, a full step on SWPC's provisional estimate, and on a forecast the part of the climatological spread its skill does not remove -- widening to the whole spread past three days, and floored at half the forecast value so a forecast storm is not treated as precisely known. NaN where `ap` is. |
| `ap_daily` | float64 | The day's average ap, what NRLMSIS calls the daily Ap. |
| `f107`, `f107_81` | float64 | Observed 10.7 cm solar flux for the day and its centred 81-day average, in solar flux units. |
| `f107_adj`, `f107_adj_81` | float64 | The same adjusted to 1 AU. The observed pair is the one an atmosphere model wants; see `docs/space-weather.md`. |
| `provenance` | string | `observed`, `forecast`, `synthetic` or `missing`. A `missing` row has NaN indices and is left that way deliberately. |
| `skill` | string | What the row's numbers are worth: `measured`, `provisional` (measured, not yet definitive), `forecast` (skilful over climatology), `recurrence` (a 27-day recurrence guess, blind to coronal mass ejections), `designed` (a synthetic scenario) or `none` (a gap). Provenance cannot make this distinction -- SWPC's three-day Kp and CelesTrak's six-week prediction are both `forecast`. |
| `source` | string | `celestrak:observed`, `swpc:kp-observed`, `swpc:kp-estimated`, `swpc:kp-forecast`, `celestrak:predicted`, `swpc:outlook-27day` or `synthetic:<name>`. |
| `issued_at` | timestamp[us, UTC] | The forecast's issue time; empty on an observed row. |

### The rolled solar wind: `data/weather/swpc/solar-wind-hourly.parquet`

The minute-cadence feed serves a week and every fetch repeats it, so versions issued more
than `SOLAR_WIND_MINUTE_DAYS` (7) days ago are summarised into one hourly archive and their
JSON deleted -- the only place in the store where raw data does not survive, and deliberately
not done to the forecast products. `<archive>.meta.json` lists every file that was rolled
into it.

| Column | Type | Meaning |
| --- | --- | --- |
| `t` | timestamp[us, UTC] | Start of the hour. |
| `n` | int64 | Minutes that went into the row, so a gap stays visible. |
| `speed_kms`, `speed_kms_max` | float64 | Mean and peak solar wind speed. |
| `density_cm3`, `temperature_k` | float64 | Hourly means. |
| `bx_nt`, `by_nt`, `bz_nt`, `bt_nt` | float64 | Hourly means of the interplanetary magnetic field. |
| `bz_nt_min`, `bz_nt_max` | float64 | The extremes of Bz in the hour. A mean is the wrong summary for it: an hour swinging from -15 to +15 nT averages to zero while being the most geoeffective hour of the storm. |

### Sun imagery

`data/cache/helioviewer/aia193_<YYYYMMDDTHHMMSSZ>.png`, named for the time **requested**,
with a `.meta.json` giving the time Helioviewer actually returned, the image id, the layers,
the scale and the size. The two times differ because Helioviewer serves the nearest image it
has.

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
  re-fetched; the metadata (ids, days) is also how the Step 3 backfill knows which ids
  and days are already covered. Backfill requests ask only for the element-set fields
  (Space-Track's `predicates` operator), so a record holds the OMM fields and nothing
  else.

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
| `manoeuvres` | bool | Whether the object performs orbit manoeuvres: sets the member's manoeuvre level to `known` or `none`, overriding the category rules. |
| `role` | string | Optional tag: `station`, `sentinel`, `university_cubesat`, `safr`, or anything else. |
| `notes` | string | Optional. |

Unknown keys are errors, so a misspelt `manoeuvres` cannot silently default.
`driftwatch fleet fleets/demo.yaml` validates the file and shows each member as the
latest snapshot knows it (`resolve_fleet()` in `driftwatch.fleet`), flagging members the
snapshot does not hold.

## History: `data/history/gph_<YYYYMMDDTHHMMSSZ>[_n].parquet` and `index.parquet`

One file per pull, whether a `driftwatch history` run or a backfill by `driftwatch
screen` (the parquet metadata says which: `kind = backfill` with the window's `start`
and `end`, or the ids and range of a `history` command). A second pull in the same
second gets a `_2`, `_3` suffix rather than overwriting the first. Each file holds
every element set Space-Track's `gp_history` returned. Columns are the element-set
columns of the snapshot (`norad_id` through `rev_at_epoch`) plus `source`
(`spacetrack`) and `fetched_at`, one row per (`norad_id`, `epoch`), sorted by object
and epoch and written in row groups of 50,000 rows so that a read filtered on
`norad_id` skips most of a large file. A re-issued element set with the same epoch
replaces the earlier one.

`index.parquet` is the consolidated index decided at the Step 0 review: one row per
element set in every history file, `norad_id` (int64), `epoch` (timestamp[us, UTC])
and `file` (the history file's name). It is derived data: updated after every history
write, rebuilt from the files whenever it is missing or does not list every file
(`driftwatch history --rebuild-index` forces it).

`driftwatch.catalogue.history.load_history(norad_ids=...)` reads the index, opens only
the history files that hold those objects (with the row-group filter), adds the rows
for those objects from every snapshot (which carry the same columns), and keeps one
row per (`norad_id`, `epoch`), so the snapshots taken by the daily fetch and the
backfilled history form one table. Without `norad_ids` every file is read. Step 3 fits
the covariance from that table; Phase 3 replays storms from it.

## Conjunction runs: `data/conjunctions/<fleet>_<YYYYMMDDTHHMMSSZ>/`

One directory per `driftwatch screen` run, named by the fleet and the window start.
Geometry and probability live in separate files, the Phase 3 design rule: Stages A to
C write the events once, and every scenario writes its own risk file over the same
events. `driftwatch risk <run> --scenario <name>` adds a scenario without rescreening.

| File | Content |
| --- | --- |
| `run.json` | The run id, snapshot, fleet file, window, screening configuration, per-stage summary and timings, the history backfill result, the covariance fit summary, the supplemental versions used and their covariance fit, the scenarios present and one record per scoring (scenario, time, model version, flag counts). |
| `events.parquet` | Stages A to C: one row per event, the geometry and both TEME states at the time of closest approach (below). Metadata: the snapshot, the run id, the fleet, the configuration and the summary. |
| `objects.parquet` | One row per object that takes part in any event, plus every fleet member (below). |
| `covariance.parquet` | The fitted covariance model: one row per object analysed (every Stage A survivor), per (category, band) pool and per default band (below). Rebuilding the model from this table gives the same covariances. |
| `risk_<scenario>.parquet` | One row per event for that scenario: the sigmas, their sources, the hard-body radius, the encounter-plane covariance, the probabilities, the flag (below). A `replay:may2024` scenario is `risk_replay-may2024.parquet`; the metadata carries the exact name. |
| `conjunctions.parquet` | The export decided at the Step 0 review: `events` joined with the manoeuvre levels and every risk file, one row per event per scenario (below). Rebuilt whenever a risk file is written. |
| `report.md` | The weekly report for one scenario: the flagged pairs split by region, the top twenty by probability and by closest approach, a table per fleet member, and how to read the numbers. Repeated encounters of a pair are collapsed to one row with the events underneath. |

An event is kept when its miss vector lies inside the RIC box or its miss distance is
inside the watch radius.

### `events.parquet`

| Column | Type | Meaning |
| --- | --- | --- |
| `event_id` | string | `<snapshot stamp>:<primary>:<secondary>:<TCA to the minute>`, e.g. `20260901T204841Z:55053:53000:20260903T0857Z`. The same in every scenario and across reruns of the same snapshot; two distinct minima of one pair inside one minute get `#2`, `#3`. |
| `primary_norad_id`, `primary_name`, `primary_category` | int64, string, string | The fleet member; the name is the fleet file's. |
| `secondary_norad_id`, `secondary_name`, `secondary_category` | int64, string, string | The catalogue object, as the snapshot names and classifies it. |
| `tca` | timestamp[us, UTC] | Time of closest approach between the two SGP4 trajectories. |
| `miss_km` | float64 | Separation at `tca`. |
| `rel_speed_kms` | float64 | Relative speed at `tca`. |
| `miss_r_km`, `miss_i_km`, `miss_c_km` | float64 | The miss vector (secondary minus primary) in the primary's radial, in-track, cross-track frame at `tca`. |
| `in_box` | bool | Inside the box: radial within 2 km, in-track and cross-track within 25 km, by default. |
| `within_watch_radius` | bool | `miss_km` at or under the watch radius (25 km by default). |
| `stale_primary`, `stale_secondary` | bool | Element set older than five days at the window start. |
| `manoeuvre_primary`, `manoeuvre_secondary` | string | The prior manoeuvre level, `known`, `possible` or `none` (see `docs/screening.md`, "Manoeuvres"). The objects table and the export carry the level after the history check, which can be `observed`. |
| `secondary_ephemeris` | string | `gp` or `supplemental`: which element set the secondary was propagated from. |
| `refine_method` | string | `root` (range-rate root inside a sign-change bracket) or `minimum` (golden-section fallback). |
| `p_x_km`, `p_y_km`, `p_z_km`, `p_vx_kms`, `p_vy_kms`, `p_vz_kms` | float64 | The primary's TEME position (km) and velocity (km/s) at `tca`. |
| `s_x_km`, ..., `s_vz_kms` | float64 | The same for the secondary. The risk step rotates covariances and builds the encounter plane from these and never propagates. |

### `objects.parquet`

| Column | Type | Meaning |
| --- | --- | --- |
| `norad_id`, `name`, `category`, `altitude_band` | int64, string, string, string | As the snapshot (the fleet file's name for members). |
| `is_primary` | bool | A fleet member. |
| `epoch` | timestamp[us, UTC] | Epoch of the element set the object was propagated from (the supplemental set's for a Starlink that used one). |
| `ephemeris`, `source` | string | `gp` or `supplemental`; `celestrak` or `spacetrack`. |
| `in_active_group` | bool | In CelesTrak's `active` group (the manoeuvre prior's second rule). |
| `rcs_m2` | float64 | SATCAT radar cross-section, NaN if unpublished. |
| `hbr_m`, `hbr_source` | float64, string | The hard-body radius used and the rule that gave the largest value, every rule being a lower bound on an unpublished size: `fleet` (the fleet file, which wins outright), `span` (the median radius of the object's type and radar cross-section class, derived from ESA's Kelvins data — see `docs/kelvins-reproduction.md`), `rcs` (`sqrt(RCS / pi)`, clipped to 0.1 to 20 m) or `category` (the default for the category). A rescore rebaselines these from the current rules, so a stored run scores with the radii the code holds now. |
| `manoeuvre_prior`, `manoeuvre_level` | string | The prior (`known`, `possible`, `none`) and the level after the history check (`possible` becomes `observed` when the history shows a burn). |
| `n_history_sets`, `n_jumps` | int64 | Element sets the fit saw; burns the detector found. |
| `jump_epochs`, `last_jump` | list<timestamp>, timestamp | Epochs of the first element set after each detected burn, and the latest of them. |
| `cov_source` | string | Which covariance the model uses for the object: `empirical`, `pooled:<category>/<band>`, `default:<band>`, or, for an object screened on an operator ephemeris, `supplemental:consistency` (exponent fitted), `supplemental:consistency-prior-p<p>` (exponent a prior), `supplemental:rms` (one stored version, the published fit residual alone) or `supplemental:beyond-horizon` (past the supplemental fit's validity; the base model served). A row can carry `<label>+beyond-horizon` when an object's events straddle the horizon. This column names the *growth law* an object gets; SpaceX's published covariance is a time series rather than a law, so `spacex-ephemeris` appears only in the risk table's per-event `cov_source_secondary`. |

### `covariance.parquet`

| Column | Type | Meaning |
| --- | --- | --- |
| `kind` | string | `object`, `pool`, `default`, or `supplemental` for an object screened on an operator ephemeris. |
| `norad_id`, `category`, `altitude_band` | int64, string, string | The object (with its labels), the pool's labels, or the default's band. |
| `source` | string | For an object row, the label the model uses for it (empirical, pooled or default); for a pool or default row, its own label; empty for a pool with too few pairs. |
| `n_objects`, `n_fitted`, `n_sets`, `n_pairs`, `dt_min_days`, `dt_max_days` | int64, float64 | What the fit saw: objects in the pool and how many of them have their own fit, element sets, residual pairs and their propagation-time range. On a supplemental row `dt_max_days` is the fit's **validity horizon** rather than its longest pair: past it the base model serves (see `docs/screening.md`), and it is empty when the fit covers the whole window. |
| `sigma_r_1d_km`, `p_r`, `sigma_i_1d_km`, `p_i`, `sigma_c_1d_km`, `p_c` | float64 | The power law per RIC component, `sigma(dt) = sigma_1d * dt^p` with `dt` in days; empty where there is no fit. On a supplemental row this is the **growth term only**, which sits over the floor: `sigma_k(dt)^2 = floor_k^2 + (sigma_1d_k * dt^p_k)^2`. An amplitude of zero means that component is floor-only, which is the default for radial and cross-track until the bins resolve a trend. |
| `n_jumps`, `n_bad_sets` | int64 | Burns detected and outlier sets dropped for the object. |
| `rms_km` | float64 | Supplemental rows only: CelesTrak's published residual of the fit of this element set to the operator's ephemeris. Kept for the record; it is one of the two things the floor is taken from. |
| `floor_r_km`, `floor_i_km`, `floor_c_km` | float64 | Supplemental rows only: the floor per RIC component, the larger of the shortest resolved lead-time bin's measured disagreement and `rms_km` split across the components in the shape that bin has. The two are not independent — the disagreement between two versions an hour apart already contains both versions' fit residuals — so the floor is the larger of them, not their sum in quadrature. |

The parquet metadata records the model version (`driftwatch_model_version`) and the
run id.

### `ballistic.parquet`

One row per object, written by `driftwatch ballistic` (Phase 3 Step 2). Fitted once per run
and reused by every scenario; see `docs/density-and-drag.md`.

| Column | Type | Meaning |
| --- | --- | --- |
| `norad_id`, `category` | int64, string | The object. |
| `b_m2_kg` | float64 | The ballistic coefficient `C_D A / m`. What turns a density into a deceleration. |
| `source` | string | `history` (fitted from the object's own decay), `bstar` (from the decay its own SGP4 drag term produces, inverted through the same density model) or `typical` (the run's median for its category, where neither worked). |
| `n_sets`, `span_days` | int64, float64 | Element sets the fit saw and the span they cover. Both are 1 and the B\* baseline for a `bstar` row. |
| `decay_m` | float64 | The drop in mean semi-major axis the coefficient was fitted to, in metres. Negative means the orbit rose, which for a `bstar` row means B\* is not physical. |
| `rho_mean_kg_m3` | float64 | Mean density over the fit window, for reading; the fit uses the full `rho \|v_rel\| (v_rel . v)` integral. |
| `n_intervals`, `n_manoeuvre_excluded` | int64 | Intervals used, and intervals dropped because the manoeuvre detector found a burn in them. |
| `note` | string | Why a route was refused, and what stood in. |

The parquet metadata records the run id and the NRLMSIS version.

### `risk_<scenario>.parquet`

| Column | Type | Meaning |
| --- | --- | --- |
| `run_id`, `snapshot`, `model_version`, `scenario` | string | The Step 0 review's run identity: the UTC stamp of the screening run plus a suffix; the snapshot file; `<driftwatch version>+<covariance model version>`; the scenario name (`quiet` in Phase 2). |
| `event_id` | string | Joins to `events.parquet`. |
| `sigma_r_primary_km`, `sigma_i_primary_km`, `sigma_c_primary_km` | float64 | The primary's RIC standard deviations at `tca` under this scenario's model. |
| `sigma_r_secondary_km`, `sigma_i_secondary_km`, `sigma_c_secondary_km` | float64 | The same for the secondary. |
| `cov_source_primary`, `cov_source_secondary` | string | The model's source label for each, per event (a scenario wrapper prefixes its own, e.g. `scaled:4:default:leo`). `spacex-ephemeris` where SpaceX's own published covariance served, and `spacex-ephemeris+<base label>` where an event straddled the 72-hour horizon of their file; past it the base model serves and reports its own label, so this column says which of the three models covered each event. A `spacex-ephemeris` sigma is their published number with the 0.2 km residual of CelesTrak's SGP4 fit added in quadrature, because that fit is the trajectory being propagated; `model_version` carries `spacex-ephemeris/2` when it is in there. |
| `hbr_m` | float64 | The combined hard-body radius, primary plus secondary. |
| `enc_cov_xx_km2`, `enc_cov_xy_km2`, `enc_cov_yy_km2` | float64 | The combined covariance projected onto the encounter plane, x along the miss vector. Enough to draw the ellipse. |
| `pc` | float64 | Probability of collision, Foster's integration. The primary number: the objects moved by the scenario's mean shift **and** the covariance carrying that shift's uncertainty. |
| `pc_shift_only` | float64 | The objects moved, scored against the covariance the run would have had with no storm layer. What the displacement alone does to the geometry. |
| `pc_variance_only` | float64 | The scenario's covariance with the objects left where their element sets put them. What the added uncertainty alone does. The three are not decomposable into one another — the probability is not linear in either input — so all three are computed. Equal to `pc` under a scenario with no storm layer. |
| `pc_alfano`, `pc_chan` | float64 | The same integral by Alfano's one-dimensional form (the cross-check) and Chan's series. |
| `pc_max`, `pc_max_scale` | float64 | The maximum probability over covariance scale factors 0.1 to 10, and the factor at which it occurs. NaN when the sweep was skipped. |
| `region` | string | `dilution` when `pc_max_scale` is below one (shrinking the covariance would raise the probability), `robust` at or above one, `unknown` when the sweep did not run. |
| `flag` | string | `red` (`pc >= 1e-4`), `yellow` (`>= 1e-5`) or `none`. |
| `confidence` | string | `standard` in the robust region, `low` elsewhere. A red or yellow flag with `low` confidence is not actionable; see `docs/screening.md`. |
| `miss_shifted_km` | float64 | The miss distance after the scenario's shifts, in the encounter plane. Equal to the event's own `miss_km` under a scenario with no storm layer. |
| `shift_i_primary_km`, `shift_i_secondary_km` | float64 | Each object's in-track displacement at `tca`, positive meaning **ahead** of where its element set puts it (more drag lowers the orbit and a lower orbit is faster). Zero where no coefficient was available — which is a statement that the displacement is unknown, not that it is zero; `storm_source_*` is what tells the two apart. |
| `relative_shift_km` | float64 | The displacement that actually enters the miss: both in-track shifts rotated **out of their own RIC frames** and differenced in TEME, as a vector norm. The scalar difference of the two `shift_i_*` columns is not a displacement — for a crossing geometry the two frames are nearly perpendicular — so do not compute it that way. |
| `sigma_shift_i_primary_km`, `sigma_shift_i_secondary_km` | float64 | The standard deviation the storm term added to each object's in-track sigma, over and above what the run's base model gave. |
| `storm_source_primary`, `storm_source_secondary` | string | Where each object's ballistic coefficient came from: `history` (fitted from its own decay), `bstar`, `typical`, or `none` (no coefficient, so no shift). A `!extrapolated` suffix means the scenario's implied decay for that object passed `STORM_MAX_DECAY_FRACTION`; that is a statement about the size of the decay, not about the coefficient. |
| `storm_validity` | string | How far Step 4's validation reaches this event, from the **weaker** of the two sources above: `validated` (both `history`), `indicative` (anything resting on a B\* inversion, a stand-in, or no coefficient), `none` (no storm layer at all — `quiet`, and any plain labelled rescore). The storm term is predictive at r = 0.88 for objects with a measured coefficient and has no demonstrated skill otherwise, so **every aggregate over these rows is reported both ways**. Nothing is weighted or withheld by the label; the numbers are identical either way. Added at the Step 4 review (2026-09-03) and filled on read for runs scored before it. See `docs/methods.md`, "Storm-term validity". |
| `scoreable`, `unscoreable_reason` | bool, string | False, with the reason, when either object's in-track displacement passed `STORM_MAX_SHIFT_REVOLUTIONS` of its orbit's circumference. Such an event carries **NaN in every probability column**, `unscoreable` as region and flag, `none` as confidence, and is excluded from every aggregate. The geometry, the covariance and the shift all stay. |
| `slow_encounter` | bool | True below 0.1 km/s relative, where the two-dimensional method's straight-line assumption no longer holds and the probability is a **known underestimate**. The flag rests on that assumption, not on any measured error: no comparison driftwatch has run can size the bias, because ESA's own risk column shares the approximation. Not a correction either: nothing rescales `pc`. See `driftwatch.risk.pc.slow_encounters`. |
| `computed_at` | timestamp[us, UTC] | When this scenario was scored. |

### `conjunctions.parquet`

The columns of `risk_*` (without `computed_at`) merged with those of `events`
(without the states), plus `manoeuvre_primary` and `manoeuvre_secondary` taken from
the objects table (so they can read `observed`), in the order fixed by
`EXPORT_COLUMNS` in `driftwatch.export.conjunctions`: run identity, event identity,
geometry, uncertainty, the three probabilities, the storm term's shifts and labels,
flags, `secondary_ephemeris`, `refine_method` and the encounter-plane covariance. One
row per event per scenario; (`event_id`, `scenario`) is unique. With no risk file
present the geometry rows are exported with the risk columns empty.

The storm columns were added to this join at the Step 4 review (2026-09-03). Before
that the join carried `pc` alone out of the scenario's five probability-and-shift
columns, so the report and the viewer — which both read this file rather than the risk
parquets — could show a storm probability with nothing beside it to say what had moved
it. Rebuild an older run's join with `RunDirectory.rebuild_conjunctions()`; no rescore
is needed, because every column comes from the stored risk tables.

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

### The conjunctions bundle

Written by `driftwatch report` (and by `driftwatch screen` at the end of a run) into the
same directory. Both files are optional: the globe works without them, and the viewer
ignores a bundle whose `bundle_version` it does not know.

| File | Content |
| --- | --- |
| `conjunctions.json` | The run's identity (run id, snapshot, fleet, model version, scenario, window, supplemental versions), the flag thresholds, every collapsed pair, the events of the pairs a reader can act on, a track index per event and the caveats the panel shows. |
| `conjunction-tracks.bin` | Little-endian float32 TEME positions in km, ordered event, object (primary then secondary), sample, xyz. `conjunctions.json`'s `tracks` block gives the counts, the 20 s step and the 600 s half-window. |

A pair row carries the event count, the number inside the box, the first time of closest
approach, the closest miss, the highest probability with the miss of the event that
produced it (`miss_at_max_pc_km`, which is not always the closest pass), the cumulative
probability (an upper bound; the events are not independent), the maximum probability,
the region, the flag,
the confidence, the manoeuvre level, the ephemeris source and the covariance source. An
event row carries the geometry, the encounter-plane covariance (`enc_cov_*`), the
probabilities, the region, the flag and the confidence, plus the index of its track or
null. Every pair is listed; events are carried for the flagged pairs, the pairs with an
event inside the notification box and the highest-probability pairs, and the run
directory holds the rest.

Positions are TEME because that is what SGP4 produces and what the viewer's own
propagator returns; the browser rotates each sample to the Earth-fixed frame with the
GMST of that sample's own time, the same way the propagation worker does.
