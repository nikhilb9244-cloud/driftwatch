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

Two horizons come out of it, and they answer different questions. The **crossing horizon**,
governed by the cross-track error, answers whether an object crossed the beam during an
observation: for the population it was measured on, the cross-track residual stays under
3.6 arcmin at the 95th percentile at every lead in every window, against thresholds of 8 to
35 arcmin, so the crossing horizon holds for the full seven days in every window at every
receiver, and the time of the crossing is known to the along-track shift: 0.2 s at the 95th
percentile at 6 hours in every window and, at seven days, 8 s in the quiet week, 26 s in May and
85 s in October. The **position horizon**, governed by the along-track error, answers where an
object is at an instant to within a third of the beam, and it is the number that moves: at the
L-band centre **24 hours in the quiet week, 12 hours in the May 2024 storm and 6 hours in the
October 2024 storm**; at the UHF centre 36, 24 and 6 hours. **S-band position prediction from
public element sets is not possible at any element-set age**: at the top of the band the position
horizon is under 6 hours, the benchmark's shortest lead, in every window, and at the S0 band
centre it is 24 hours, 12 hours and under 6 hours in the three windows. Whether a crossing
predicted days ahead happens inside a given observation is a position question, of timing, before
it is a crossing question, of geometry.

**Population.** The benchmark covers three near-circular satellites at 460 to 506 km that did not
manoeuvre inside the trials kept. The two measured horizons are attached only to objects between
400 and 600 km with an eccentricity under 0.02 and an element set no older than the benchmark's
seven days; every other object, which includes all of GNSS, Iridium, Globalstar, Inmarsat and
OneWeb, carries *no measured horizon* for both and the reason. A Starlink satellite at 550 km carries the label by
altitude; it is station-kept, and nothing in the benchmark measured a station-kept object's error
through a burn, which the reports say. SpaceX's published ephemerides are not archived, so a
retrospective on 2024 has none to use and every Starlink falls to the catalogue.

**Real observations, and where they come from.** The SARAO archive carries the pointing, start,
duration and band of every released MeerKAT observation, but its search tool needs a SARAO
account (the archive's own guidance says so), so it was not queried. The observation list is
therefore a plain CSV, the shape an archive export reduces to, and every record carries the
source it was read from. One public record was found inside the two periods: GCN Circular 36362,
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
and the along-track shift at that age and geometry, and the two horizon labels, crossing and
position. Both products are geometry.

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
right ascension, declination, Julian date, element-set epoch and range. Four fields are added to
every position, `cross_track_uncertainty_deg` with `crossing_horizon` and `along_track_shift_s`
with `position_horizon`, and those four are the whole of what this lane would offer upstream;
everything else driftwatch writes sits beside `data` under its own keys. Positions through the beam are sampled every tenth of a second, because a low object
crosses a half-degree beam in under a second. SatChecker itself is unchanged; it is a field-of-view
predictor with orbit-source provenance, not a radio tool, and carries no per-object accuracy.

## What this does not show

- No received power, occupancy fraction or sensitivity loss, anywhere.
- Both horizons rest on three satellites in one orbit class over three weeks of element sets. They
  are bounds at zenith range; a crossing at 30 degrees of elevation sees half the angle.
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
uv run driftwatch radio period quiet-2024-04 --observations data/radio/observations/quiet-2024-04.csv
uv run driftwatch radio period storm-2024-05 --observations data/radio/observations/storm-2024-05.csv
```

`radio horizon` reads the benchmark's per-trial file where it exists and otherwise the exported
CSV beside the page, so the table recomputes from the repository. `radio period` needs the
element-set history for the period in the local store (`data/history/`), which the Space-Track
backfill writes, and an observation CSV with the columns `observation_id, target, ra, dec,
start_utc, duration_s, band, centre_mhz, source, note`.

_Last updated 7 September 2026._
