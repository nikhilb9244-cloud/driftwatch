# Space weather: the indices, the feeds and the table

What drives the density model in Phase 3, where each number comes from, and what it does
and does not mean. Written at Step 1; the density model itself is Step 2.

## The two indices, and why the table carries both

**Kp** is the planetary K index: a three-hourly measure of geomagnetic disturbance from
thirteen ground magnetometer stations, on a quasi-logarithmic scale from 0 to 9 in thirds
(0, 0+, 1−, 1, 1+, … 9). It is the number people quote, and the NOAA G scale is defined on
it: G1 at Kp 5, G3 at 7, G5 at 9.

**ap** is the same disturbance expressed as an amplitude in nanotesla, by a fixed table.
It is what an atmosphere model wants, for one reason: **Kp must not be averaged and ap
may be.** Kp 4 and Kp 6 do not average to Kp 5 in any physical sense — their amplitudes are
27 and 80 nT and the mean of those is 53, which is Kp 5+, not Kp 5. The relationship is
steep: two units of Kp between 5 and 7 is a factor of 2.75 in ap, and between 7 and 9 another
factor of 3.

The conversion is the published Bartels table, reproduced in `weather/table.py` so it can be
read rather than trusted:

| Kp | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ap | 0 | 4 | 7 | 15 | 27 | 48 | 80 | 132 | 207 | 400 |

**F10.7** is the solar radio flux at 10.7 cm in solar flux units, a daily number that stands
in for the extreme ultraviolet output that actually heats the thermosphere. NRLMSIS wants two
of them: the day's value and an 81-day average (three solar rotations) centred on the day.

The table carries F10.7 twice more, observed and adjusted. **Observed** is the flux measured
at Earth; **adjusted** is that value scaled to a fixed Sun–Earth distance of 1 AU, which
removes the ±3.5 % annual swing from the eccentricity of Earth's orbit. For studying the Sun
the adjusted value is right. For driving an atmosphere the observed one is, because the
atmosphere feels the flux that arrives. Step 2 uses the observed pair; both are in the table
so the choice is visible and reversible.

## The feeds

| Source | Gives | Cached | Terms |
| --- | --- | --- | --- |
| CelesTrak `SW-All.csv` | Three-hourly Kp and ap 1957 to now, daily F10.7, predicted Kp and ap about six weeks out, predicted F10.7 to 2041 | 12 hours | Same as the element sets |
| SWPC `noaa-planetary-k-index-forecast.json` | Three-hourly Kp: a week observed and estimated, three days predicted | 30 minutes | Public, no account |
| SWPC `planetary_k_index_1m.json` | The estimated planetary K index once a minute | 30 minutes | Public |
| SWPC `27-day-outlook.txt` | Daily F10.7, planetary A index and largest Kp, 27 days out | 6 hours | Public |
| SWPC `propagated-solar-wind.json` | Speed, density, temperature and the interplanetary magnetic field at L1, a week at one-minute cadence | 15 minutes | Public |
| Helioviewer `takeScreenshot` | A PNG of the Sun (SDO/AIA 193 Å) nearest a requested time | Permanently | Public; credit asked |

`driftwatch weather` fetches them all, builds the table for a window and prints it with its
provenance. `--images` adds the Sun frames.

### Every forecast is stored with the time it was issued

A forecast is only reproducible if you know **which** forecast it was, and SWPC reissues
these several times a day. Each fetch is written to `data/weather/swpc/` under the product
name and the issue time and is never overwritten, with a sidecar recording the URL, the fetch
time, the issue time and where the issue time came from. `swpc.stored_before(product, when)`
then returns the version that existed at a past moment, so a run made last Tuesday rescores
against last Tuesday's forecast.

Where the issue time comes from, in order of preference:

- **`product`** — the text products carry their own `:Issued:` line, and it is authoritative.
- **`companion`** — the Kp forecast JSON carries no issue time, and its HTTP `Last-Modified`
  is the time the file was last regenerated rather than the time the forecast was made
  (measured 2026-09-02: 36 seconds before the request). So the three-day forecast **text**
  product is fetched alongside the JSON purely for its `:Issued:` line. Two small requests
  every half hour at most, in exchange for knowing which forecast a run used.
- **`last-observation`** — for the observation streams (the real-time index, the solar wind)
  the issue time is the last observation in the series, which is what "current as of" means
  for a stream.
- **`fetch-time`** — the fallback, recorded as such so it is never mistaken for the others.

## The table

One row per three-hour interval, from `weather/table.py`. This is what the density model
reads.

| Column | Meaning |
| --- | --- |
| `t` | Start of the three-hour interval, UTC (00, 03, … 21). |
| `kp` | Planetary K index for the interval, snapped to thirds. |
| `ap` | The interval's ap in nT, from the Bartels table where only Kp was published. |
| `ap_daily` | The day's average ap — what NRLMSIS calls the daily Ap. |
| `f107`, `f107_81` | Observed 10.7 cm flux for the day, and its centred 81-day average. |
| `f107_adj`, `f107_adj_81` | The same adjusted to 1 AU. |
| `provenance` | `observed`, `forecast`, `synthetic` or `missing`. |
| `source` | Which feed: `celestrak:observed`, `swpc:kp-observed`, `swpc:kp-estimated`, `swpc:kp-forecast`, `celestrak:predicted`, `swpc:outlook-27day` or `synthetic:<name>`. |
| `issued_at` | The forecast's issue time; empty for an observation. |

### How the sources are layered

Best first, each filling only what the one above leaves:

1. **CelesTrak observed.** The definitive record. Nothing beats a measurement.
2. **SWPC observed and estimated.** CelesTrak rebuilds its file once a day, so the last day
   or two before now sits in a gap where CelesTrak has only a prediction and SWPC already
   has the real index — definitive for the older hours, estimated from the live magnetometer
   network for the most recent. Both are measurements; both are marked `observed` with a
   source that says which.
3. **SWPC's three-day Kp forecast.** The finest and freshest thing available for the next
   three days.
4. **CelesTrak's predicted Kp and ap**, about six weeks out. This is what covers the rest of
   a seven-day screening window.
5. **SWPC's 27-day outlook.** A last resort, rarely reached, kept because CelesTrak's
   predicted Kp is itself derived from SWPC's forecasts and it is worth being able to see
   both when they disagree.

On the live window of 2026-09-02, that comes out as 4 intervals from SWPC's estimated index,
17 from its three-day forecast, and 36 from CelesTrak's prediction.

### Three decisions worth stating

**The 27-day outlook's A index is used, not its largest Kp.** The outlook publishes a daily
planetary A index and the largest Kp expected that day. Repeating a daily maximum across
eight intervals would say the whole day was as disturbed as its worst three hours, which for
a density model driven by the average is wrong in the dangerous direction. The A index is
already a daily average, so spreading it flat is the honest reading of a daily number, and
`kp` on those rows is the inverse of the ap table rather than the outlook's own Kp.

**A gap stays a gap.** An interval with no source in any layer comes back with NaN and
provenance `missing`. Substituting a quiet zero would be a silent invention, and the density
model has to decide what to do about a hole rather than be handed one disguised as a calm
day.

**A synthetic profile changes the geomagnetic columns only.** Step 3's storm scenarios
replace `kp`, `ap` and `ap_daily` and mark the rows `synthetic`; F10.7 is left alone, because
a geomagnetic storm does not change the Sun's radio output and putting two unrelated changes
behind one scenario name would make the result unreadable.

## Sun imagery

`weather/helioviewer.py`, for the Step 5 replay. SDO/AIA 193 Å at 512 px and 4.8 arcsec per
pixel — the full disc with a margin — through Helioviewer's `takeScreenshot`, which renders
to PNG. The 193 Å channel shows the million-degree corona, so coronal holes read as dark
regions and active regions as bright ones: both storm drivers are visible at a glance.

Four frames a day by default, which is enough to watch a source rotate across the disc over a
storm without becoming a movie. Each frame is cached permanently by the time **requested**,
and the time actually returned is recorded beside it, because Helioviewer serves the nearest
image it has: on the Gannon storm days that lag is a fraction of a minute, but during a data
gap it can be hours, and a replay that silently showed yesterday's Sun would be worse than
showing none.

## What this does not do

- **No storm is predicted here.** Everything past the last observation is somebody else's
  forecast, carried with its issue time. The three-day Kp forecast is skilful; the 27-day
  outlook is a recurrence climatology and should be read as one.
- **No index is invented.** See "a gap stays a gap" above.
- **F10.7 is a proxy.** The thermosphere is heated by extreme ultraviolet, which F10.7
  correlates with rather than measures; the correlation is good over a solar cycle and worse
  day to day. It is what NRLMSIS was built on, so it is what the table carries.
- **Kp is a global average of a local phenomenon.** A storm's energy deposition is
  concentrated in the auroral ovals, and two storms with the same Kp can heat a given orbit
  differently. Step 2 inherits that limitation from the model.

## Sources

- CelesTrak space weather data, https://celestrak.org/SpaceData/, and T. S. Kelso's notes on
  the file format and on the observed-versus-adjusted F10.7 question.
- NOAA Space Weather Prediction Center products, https://services.swpc.noaa.gov/, read
  2026-09-02.
- J. Bartels, "The technique of scaling indices K and Q of geomagnetic activity", *Annals of
  the International Geophysical Year* 4, 215–226 (1957), for the K-to-a conversion.
- GFZ Potsdam, the Kp index definition and its history, https://www.gfz-potsdam.de/kp-index/.
- Helioviewer Project API, https://api.helioviewer.org/docs/v2/, read 2026-09-02.
