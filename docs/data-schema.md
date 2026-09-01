# Data schema

All on-disk products live under `data/` (git-ignored) except the viewer bundle, which is
written into `web/public/data/` so Vite serves it. Times are UTC throughout.

## Cache: `data/cache/celestrak/`

Raw downloads, kept verbatim so a snapshot can be rebuilt offline.

- `gp/<group>.json`: the OMM record list exactly as CelesTrak returned it.
- `gp/<group>.meta.json`: `fetched_at`, `n_objects`, URL and the User-Agent used.
- `satcat.csv` and `satcat.meta.json`: CelesTrak's satellite catalogue metadata.

The fetcher refuses to re-download a group younger than two hours (CelesTrak's rule) or
SATCAT younger than a day.

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
| `groups` | list<string> | Every CelesTrak group the object appeared in. |
| `source` | string | `celestrak`. Reserved for `spacetrack` later. |
| `fetched_at` | timestamp[us, UTC] | When the snapshot was built. |

An object present in several groups is kept once, with the newest epoch.

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
| `manifest.json` | Reference time, counts, category and band legends, file descriptions, caveats. |
| `objects.json` | Column-oriented arrays: `norad_id`, `name`, `category` (index into legend), `band`, `object_type`, `perigee_km`, `apogee_km`, `period_min`, `inclination_deg`, `epoch_age_days`, `sgp4_error`. |
| `elements.bin` | Little-endian float64, 11 values per object: `norad_id`, `epoch_unix_ms`, `mean_motion`, `eccentricity`, `inclination_deg`, `raan_deg`, `arg_perigee_deg`, `mean_anomaly_deg`, `bstar`, `mean_motion_dot`, `mean_motion_ddot`. |
| `reference.bin` | Little-endian float32, 6 values per object: TEME position (km) and velocity (km/s) at the reference time from the Python sgp4 library, NaN where SGP4 reported an error. |

The viewer rebuilds OMM records from `elements.bin`, initialises satellite.js with them,
and reports the largest disagreement with `reference.bin` at the reference time.
