# Satellite crossings of a dish's beam over the Karoo, with the accuracy attached

A bounded demonstrator, built in three working days from public data, of what the calibration
benchmark's measured element-set error means for a radio telescope: which catalogued objects are
in the sky above the MeerKAT site during an observation, which of them cross the primary beam, how
far the crossing could be from where the public element set puts it, and whether that is inside
the two horizons the benchmark measured: a crossing horizon and a position horizon. Nothing here is a received power, an occupancy fraction or a
sensitivity loss; those need a measurement at the site, and the statistics of satellite
interference into radio telescopes have been modelled elsewhere. No organisation has used this,
asked for it, or agreed to be named in connection with it.

The pieces: the radio horizon table (`docs/radio-horizon.md`), the declared-emission table
(`docs/radio-emissions.md`), two period reports (`docs/radio/quiet-2024-04.md`,
`docs/radio/storm-2024-05.md`) and their machine-readable exports under `data/radio/`. The code
is `src/driftwatch/radio/`; the commands are at the end of this page.

## Four decisions

**Angular error, not kilometres.** The benchmark's horizon was stated as an along-track
distance, because a screening box is a box. A beam is an angle, and the two components of the
residual do different things to a crossing: the cross-track error moves the path sideways and
decides *whether* the object enters the beam; the along-track error moves the object along its
path and decides *when*. So every trial's radial, in-track, cross-track residual is converted
into the angle it subtends from the array centre with the satellite overhead, the largest angle it
can subtend from the site, and the table reports the fraction of trials whose angular error is
under a third of the primary beam's half-power width, per receiver, per lead, per window. The
half-power width is the measured L-band relation, 57.5 arcmin at 1.5 GHz scaling with wavelength
(Mauch et al. 2020, ApJ 888, 61), which is 1.13 λ/D for the 13.5 m dish, applied to the UHF and
S receivers by the wavelength scaling the holography paper reports over most of each band
(de Villiers 2023, AJ 165, 78).

Two horizons come out of it, and they answer different questions; both are computed per altitude
band of the reference benchmark, and an object is scored against its own band's trials
(`docs/radio-horizon.md`, the band table). The **crossing horizon**, governed by the cross-track
error, answers whether an object crossed the beam during an observation: the cross-track residual
stays under 3.4 arcmin at the 95th percentile at every lead in every window in every band, against
thresholds of 8 to 35 arcmin, so the crossing horizon is the benchmark's full seven days in every
band and window at every receiver, with one exception, 5 days at 600 to 750 km in the August 2024
window; the time of the crossing is known to the along-track shift, at 400 to 600 km 0.2 s at the
95th percentile at 6 hours in every window and, at seven days, 8 s in the quiet week, 25 s in May,
72 s in October and 29 s in August. The **position horizon**, governed by the along-track error,
answers where an object is at an instant to within a third of the beam, and it is the number that
moves, with the storm and with altitude: at the L-band centre **24, 12, 6 and 12 hours at 400 to
600 km in the quiet, May, October and August windows**; 24, 24, 12 and 36 hours at 600 to 750 km;
6 days, 2 days, 6 hours and 3 days at 750 to 850 km; 7, 7, 3 and 7 days at 850 to 1,000 km; 7, 3, 7
and 7 days at 1,338 km. **S-band position prediction from public element sets is not possible at
any element-set age at 400 to 600 km**: at the top of the band the position horizon is under
6 hours, the benchmark's shortest lead, in every window. Higher it is possible: at the top of S band
12 hours in the quiet and May windows at 600 to 750 km, 3 days in the quiet week at 750 to 850 km,
the full seven days in the quiet week at 850 to 1,000 km with 12 hours to 4 days in the storms, and
seven days in every window but May at 1,338 km. Whether a crossing predicted days ahead happens
inside a given observation is a position question, of timing, before it is a crossing question, of
geometry.

**Population.** The band table on `docs/radio-horizon.md`: fifteen spacecraft with a public
reconstructed orbit, near-circular and free-flying between manoeuvres, in five altitude bands, 460
to 507 km (Swarm A, B, C; GRACE-FO 1, 2), 696 to 719 km (Sentinel-1A, CryoSat-2), 783 to 803 km
(SARAL, Sentinel-3A, 3B), 893 to 952 km (SWOT, HY-2C, 2D) and 1,338 km (Jason-3, Sentinel-6A), one
week of element sets in each of four windows. The two measured horizons are attached only to
objects whose mean altitude falls in one of the bands, 400 to 1,400 km, with an eccentricity under
0.02 and an element set no older than the benchmark's seven days, each scored against its own
band's trials; every other object, which includes all of GNSS, Globalstar at 1,414 km and Inmarsat,
carries *no measured horizon* for both and the reason. A Starlink satellite at 550 km, an Iridium
at 780 km or a OneWeb at 1,200 km carries the label by altitude; they are station-kept, and nothing
in the benchmark measured a station-kept object's error through a burn, which the reports say.
SpaceX's published ephemerides are not archived, so a retrospective on 2024 has none to use and
every Starlink falls to the catalogue.

**Real observations, and where they come from.** The SARAO archive carries the pointing, start,
duration and band of every released MeerKAT observation, and its documented route for reading
them is an API (below), which needs a logged-in account's token; without one the archive was not
queried. The observation list is therefore a plain CSV, the shape an archive export reduces to,
and every record carries the source it was read from. One public record was found inside the two periods: GCN Circular 36362,
an S-band observation of the field of EP240414a on 23 April 2024, with the pointing taken as the
counterpart's position from GCN Circular 36105 because the circular gives no phase centre. No
published circular or paper read for this work gives a MeerKAT observation between 10 and 12
May 2024. Nothing was invented to fill the gap: the storm-week report runs the product that needs
no pointing, hour by hour, and says that the other has nothing to run on until an observation
list is exported from the archive.

**Two products, no power claims.** For each observation, first, every catalogued object that
belongs to a constellation with a declared emission, counted by constellation, that rises above
ten degrees during the observation, with how many are up at once: the aggregate a sidelobe sees.
Second, every object whose predicted track passes inside the half-power radius, with its closest
approach to the boresight, the time, the element set's age, the cross-track angular uncertainty
and the along-track shift at that age and geometry, the two horizon labels, crossing and
position, and, from the object's own element sets, the time since the last manoeuvre the
set-jump detector finds, as a lower bound, with whether the set's likely fit arc, the benchmark's
24-hour exclusion arc before its epoch, spanned it. The benchmark measured what such a set does
(`docs/reference-benchmark.md`, the first element sets after a burn), and the export states it
beside the flag. Both products are geometry.

## The archive's route

Read from the archive's own help page (archive.sarao.ac.za/help) and terms of use
(archive.sarao.ac.za/terms-of-use) on 7 September 2026, before anything was automated.

- **The permitted route is a documented API.** "You can interact with the MeerKAT Archive
  programmatically using our GraphQL API. Visit /graphql in your browser to explore the schema and
  run queries interactively using the built-in GraphQL Playground." The search interface's own
  metadata download is that API: selecting rows and clicking "DOWNLOAD METADATA" hands out a
  published script, `export_meerkat_archive.py`, which pages the `observations` query 25 records
  at a time and is offered as "a reference implementation to extend for specific use cases".
  There is no CSV export from the search interface, and the katdal endpoint
  (`archive-gw-1.kat.ac.za/<capture block>/..._sdp_l0.full.rdb?token=...`) is for observation
  data, which this lane never reads.
- **Login.** "The API supports script-based authentication through the OAuth2 PKCE flow": a
  browser login through the archive's `login.py` issues an access token and a refresh token, and
  "Refresh tokens are valid for 30 days, and are rotated on successful logins". "Public datasets
  are available to all logged-in users." There is no documented password login for scripts, so
  `driftwatch radio archive` reads one token from `SARAO_ARCHIVE_TOKEN`, holds it in memory, and
  never writes it to disk, a log or the cache.
- **Proprietary periods.** "Open Time proposals typically have a proprietary period of 12 months
  after the last observation has been obtained"; DDT three months; large survey projects vary; the
  telescope and data access guidelines (SSA-0003C-001 rev. 02, 28 May 2024) say "After proprietary
  periods expire, the relevant datasets will be available to anyone." The export keeps a record
  only when the archive itself marks it public and its start is more than twelve months before the
  export, and counts everything it excludes.
- **Terms of use.** The site's terms grant permission "to display, copy, distribute, and download
  the materials on this website for personal, non-commercial use only, provided you do not modify
  the materials and that you retain all copyright and other proprietary notices contained in the
  materials", and forbid mirroring. The export is a metadata table of public observations with the
  archive's own identifiers in every row; no data product is copied; the table stays outside the
  repository (`data/archive/` is ignored), and a period report cites a record by its capture block and
  proposal identifiers and reproduces none of the archive's descriptive text. The archive's acknowledgement
  statement for publications using MeerKAT data is: "The MeerKAT telescope is operated by the
  South African Radio Astronomy Observatory, which is a facility of the National Research
  Foundation, an agency of the Department of Science and Innovation."
- **Pace and scope.** The help page states no rate limit; the export sends at most one request every
  two seconds with a descriptive User-Agent, uses the published script's page size, and asks only
  for observation metadata: capture block, proposal, start, duration, band, frequency range,
  targets, pointings and the public flag. The API is described as "experimental and may be subject
  to change".

## The catalogue as it stood

Each observation is run on the catalogue as it stood at its start: every object's newest public
element set at or before that moment and none later, no older than seven days, rebuilt from
Space-Track's element-set history (the replay mode the storm validation already used). The
history was backfilled for every object SATCAT lists as on orbit in each period, 28,919 objects
for 13 to 27 April 2024 and 28,624 for 3 to 13 May, in 110 requests. The 23 April observation
ran on 24,746 objects; the hourly aggregates on 25,617 and 25,658.

Constellation membership is by catalogue name, and for GLONASS, which the catalogue names
`COSMOS`, by owner and orbit. It includes retired members, because the catalogue does not carry
transmit status, and the reports say so beside every count.

## What the retrospective found

**23 April 2024, S-band, one hour on EP240414a.** Two catalogued objects crossed the 14-arcmin
half-power radius: a Delta 1 fragment 10.8 arcmin from the boresight on an element set an hour
old, and a CZ-4C fragment 0.7 arcmin from it on a set three and a half days old. Both are debris
at 840 to 880 km, so both carry *no measured horizon* and no declared emission. In the sky above
ten degrees during the hour: 25 GPS, 33 GLONASS, 10 Galileo, 16 BeiDou and 5 NavIC satellites at
some point, with 22, 30, 8, 14 and 5 up at once on average; 10 Inmarsat; up to 4 Iridium and 9
Globalstar; 135 Starlink and 25 OneWeb at the peak. In the S4 band the only declared emitter
among them is Starlink's direct-to-cell downlink at 2620 to 2690 MHz, a capability declared in
November 2024, after the observation, and not established per object.

**10 to 12 May 2024, hour by hour.** In the L band, which every GNSS constellation, Iridium and
Inmarsat declare emissions inside, the sky above ten degrees held on average 21 GPS, 40 GLONASS,
8 Galileo, 16 BeiDou, 3 NavIC, 2 Iridium and 10 Inmarsat satellites at once, with peaks of 33,
59, 12, 20, 3, 7 and 10, and 121 Starlink and 21 OneWeb, whose L-band emission is unknown and
out of band respectively. The quiet week's figures are the same to within a satellite or two: a
geomagnetic storm does not move a navigation satellite across the sky. What the storm moves is
the error of a low object's element set, which is why the position horizon for the May window is
half the quiet week's while the crossing horizon is the full seven days in both.

**A declared band inside the L-band receiver.** FCC DA 24-1193, an Order and Authorization of
the Space Bureau adopted and released on 26 November 2024 (ICFS File Nos. SAT-MOD-20230207-00021
and SAT-AMD-20240322-00061, call sign S3069; GN Docket No. 23-135), says at paragraph 39: "In
particular, outside the United States, SpaceX is authorized to transmit in the 1475-1518 MHz,
1805-1880 MHz, 1930-2000 MHz, 2110-2180 MHz, 2180-2200 MHz, 2345-2360 MHz, and 2620-2690 MHz
(space-to-Earth) bands", and in the same paragraph: "We also require that any direct-to-cell
operations outside the United States be duly authorized by the relevant administrations and will
be subject to the laws, regulations, and requirements applicable to such operations in the
territories of the authorizing administrations." Ordering paragraph 89, condition ww, lists the
same sub-bands "(outside the United States only)". The range 1475 to 1518 MHz lies inside
MeerKAT's digitised L band. The table records it as **declared and subject to each
administration**: a capability, not a measured emission, not an operation over the site, and not
established per object. If the downlink were licensed in South Africa, an intentional
space-to-Earth transmission would sit inside the L-band receiver's band from satellites these
reports count at about 120 above ten degrees at once, so the range would join the GNSS, Iridium
and Inmarsat bands the receiver already sees as declared in-band emitters, at a level no public
measurement gives; whether such a licence will be granted is not predicted here. No published
measurement of Starlink's unintended emission inside any MeerKAT band was found, and the table
records that as unknown rather than absent. The order's wording is quoted in full on the emission
page (`docs/radio-emissions.md`).

## The export, and where it could go

Each observation's crossings are written in the shape of the IAU CPS SatChecker field-of-view
response (`GET /fov/satellite-passes/`, synchronous form): `data.satellites` keyed by name and
NORAD id, each with its `positions` carrying altitude, angle from the field centre, azimuth, time,
right ascension, declination, Julian date, element-set epoch and range. Six fields are added to
every position: `cross_track_uncertainty_deg` with `crossing_horizon`, `along_track_shift_s`
with `position_horizon`, and `hours_since_manoeuvre` with `fit_arc_spanned_manoeuvre`. The last
pair comes from the element-set jump detector on the object's own sets at or before its epoch: a
lower bound on the time since the last detected burn, which lies between the two set epochs the
crossing record names, and whether the set's likely fit arc, the benchmark's 24-hour exclusion
arc, reaches it. The consequence of a spanned arc is stated once, under `post_manoeuvre`, as the
benchmark measured it on twelve burns of six spacecraft in four windows, a split re-measured
whenever a window is added: the first set issued within ten hours of a burn was wrong along track
at four days by 2.3 to 33 km, the first set issued twelve hours or later by under 2.5 km, and the
next set after every burn by under 5.3 km; the error is the part of the burn the set does not
contain, and a set issued after a burn can still be a pre-burn fit with its epoch advanced
(`docs/findings.md`, item 8). Those six fields are
the whole of what this lane would offer upstream; everything else driftwatch writes sits beside
`data` under its own keys. Positions through the beam are sampled every tenth of a second, because a low object
crosses a half-degree beam in under a second. SatChecker itself is unchanged; it is a field-of-view
predictor with orbit-source provenance, not a radio tool, and carries no per-object accuracy.

## What this does not show

- No received power, occupancy fraction or sensitivity loss, anywhere.
- Both horizons rest on the reference benchmark's fifteen spacecraft in five altitude bands over
  four weeks of element sets, each object scored against its own band. They are bounds at zenith
  range; a crossing at 30 degrees of elevation sees half the angle.
- The manoeuvre fields rest on the element-set jump detector alone: a burn it misses, and any burn
  after the object's newest set, go unreported, and a station-kept object may carry the flag on
  every set. The consequence quoted is the benchmark's, measured on free-flying spacecraft at 700
  to 950 km, twelve burns on six spacecraft in four windows, and re-measured whenever a window is
  added.
- The beam width is measured at L-band and scaled by wavelength; near the top of each band the
  holography measurements depart from the scaling.
- Constellation counts include retired members. GPS shows 75 catalogued and up to 33 above ten
  degrees at once, against 31 operational satellites, for that reason.
- Where the phase centre is not public, the target position stands in for it; where scan
  boundaries are not public, a crossing during a calibrator scan or a slew is counted with the
  rest.
- One observation in one period, none in the other: a demonstration of the method on real
  records, not a survey.

## Commands

```powershell
uv run driftwatch radio horizon      # docs/radio-horizon.md, data/radio/horizon.json, data/radio/swarm_trials.csv
uv run driftwatch radio emissions    # docs/radio-emissions.md
uv run driftwatch radio archive quiet-2024-04   # needs SARAO_ARCHIVE_TOKEN; writes data/archive/sarao/quiet-2024-04.csv (ignored)
uv run driftwatch radio archive storm-2024-05
uv run driftwatch radio period quiet-2024-04 --observations data/archive/sarao/quiet-2024-04.csv
uv run driftwatch radio period storm-2024-05 --observations data/archive/sarao/storm-2024-05.csv
```

`radio horizon` reads the benchmark's per-trial file where it exists and otherwise the exported
CSV beside the page, so the table recomputes from the repository. `radio archive` reads the
period's observations from the SARAO archive's documented GraphQL API with the token in
`SARAO_ARCHIVE_TOKEN` (read-only, paced, metadata only, public records past the proprietary period
only) into a CSV under `data/archive/sarao/`, which the repository ignores, with the public-record rows
of `data/radio/observations/` kept above the export. `radio period` needs the element-set history
for the period in the local store (`data/history/`), which the Space-Track backfill writes, and an
observation CSV with the columns `observation_id, target, ra, dec, start_utc, duration_s, band,
centre_mhz, source, note`.

_Last updated 7 September 2026._
