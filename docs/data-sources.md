# Data sources and their terms

What driftwatch downloads, where from, under which rules, and what it may republish.
Terms are quoted as read on the date given. Check the source page before relying on them
and update the date here when you do.

## CelesTrak (celestrak.org)

**Used for.** GP element sets (OMM JSON) by group, the SATCAT metadata table and, from
Step 2 of Phase 2, the supplemental Starlink element sets (`sup-gp.php?FILE=starlink`,
SGP4 fits CelesTrak makes to SpaceX's published ephemerides; the fit residuals are
published alongside as `starlink.rms.txt`). From Phase 3 Step 1, `SW-All.csv`: three-hourly
Kp and ap back to 1957, daily F10.7, and predictions forward. Cached for twelve hours; a
stale copy is kept and used if a download fails, because a day-old space weather record is
far better than none.

**Rules (read 2026-09-01).** No account. At most one request per group every two hours,
a descriptive `User-Agent`, and the JSON endpoints rather than scraping. The fetcher
enforces the two-hour floor in its cache and cannot be told to go below it. Set
`DRIFTWATCH_CONTACT` to put a contact address in the `User-Agent`.

**Credit line** (`config.CELESTRAK_CITATION`):

```
Element sets and SATCAT from CelesTrak (celestrak.org), T.S. Kelso.
```

## Space-Track.org

**Used for.** The `gp` class (the current catalogue: no decay date, epoch within 30 days)
and `gp_history` (every element set for named objects over a date range). Nothing else.
driftwatch never requests conjunction data messages (`cdm_public`, `cdm`) or anything
from the emergency or advanced tiers.

**Rules (documentation read 2026-09-01).** Free registration. Credentials live in
`SPACETRACK_USER` and `SPACETRACK_PASS` only and are never written to disk or logs.
Fewer than 30 requests a minute and 300 an hour by their rule; the client stays at 20 and
250. The catalogue at most once an hour by their rule, and at most every two hours and
four times a day by ours. `gp_history` "once per lifetime": every history request is
cached for ever and never repeated.

### Redistribution: the blanket-approval clause (checked 2026-09-01)

The user agreement, at https://www.space-track.org/documentation under "User Agreement",
first restricts transfer:

> The User agrees not to transfer any data or technical information received from this
> website, or other U.S. Government source, including the analysis of data, to any other
> entity without prior express approval.

and then grants the exception driftwatch relies on:

> USSPACECOM has provided express blanket approval for transfer/redistribution of basic
> SSA data and services accessed via www.Space-Track.org conditioned on appropriate
> citation. Publications of analysis based on USSPACECOM data also require appropriate
> citations.

Basic SSA data is defined on the same page as "Two-Line Elements (TLEs) and Orbital
Mean-element Messages (OMMs); SATCAT; and Satellite Decay and Reentry Data".

**What the approval covers.** Basic SSA data only: GP element sets (TLEs and OMMs),
SATCAT, and decay and re-entry data.

**What it does not cover.** Conjunction data messages, and the emergency and advanced
SSA tiers, which sit under separate agreements with USSPACECOM. driftwatch fetches only
`gp` and `gp_history`, both OMM element sets, so everything it holds from Space-Track is
inside the approval. If the project ever needs conjunction messages for validation it
uses a dataset released for that purpose (ESA's Kelvins challenge data, below), never
Space-Track's CDM classes.

**What driftwatch republishes.** The viewer bundle in `web/public/data/` carries every
element set in the snapshot, the Space-Track-sourced ones included, with the citation
below in `manifest.json` and on screen. Snapshots and history parquet files hold element
sets plus SATCAT fields and are covered the same way. Screening outputs (Phase 2) and
storm analyses (Phase 3) are "analysis based on USSPACECOM data" and carry the same
citation in their report headers.

### Citation format

Machine-readable, in `manifest.json` and in report headers (`config.SPACETRACK_CITATION`):

```
Element sets from Space-Track.org (USSPACECOM / 18th Space Defense Squadron),
redistributed with citation under the Space-Track user agreement.
```

In prose, for a paper, a talk or a README:

> Orbital element sets and satellite catalogue data courtesy of Space-Track.org
> (U.S. Space Command, 18th Space Defense Squadron), www.space-track.org, and of
> CelesTrak (T.S. Kelso), celestrak.org, retrieved on <date>.

The unit name is the one Space-Track uses on its own pages; update both strings if it
changes.

## SpaceX Starlink ephemerides (api.starlink.com)

**Used for.** The covariance of Starlink secondaries inside the operator's own 72-hour
horizon (`driftwatch spacex`, `ephemeris/spacex.py`). SpaceX publishes a predicted
trajectory with covariance for every Starlink satellite, refreshed every eight hours, at
`https://api.starlink.com/public-files/ephemerides/`. These are the same files CelesTrak
fits its supplemental element sets to, so driftwatch is taking the uncertainty of the
trajectory it is already propagating rather than inferring one from how much successive
fits to it disagree. `docs/spacex-ephemerides.md` carries the full finding.

**Rules (read 2026-09-02).** No account, no authentication, no stated licence and no
stated attribution requirement. Published for the express purpose of letting other
operators screen against Starlink. Space-Track stopped hosting them on 28 July 2025 and
directed users to SpaceX, so **the Space-Track user agreement does not govern them** — and
would not have helped if it did, since an owner/operator ephemeris is not "basic SSA data"
and the blanket approval would not have covered it.

**What driftwatch does with them, and the rule adopted.** Because no licence is stated,
they are used **for analysis only**:

- Read them, compute with them, and publish the results, crediting SpaceX.
- **Never redistribute the raw files**, or a repackaged copy of them. Nothing grants that
  right, and nothing is gained by it: the files are one unauthenticated HTTP request away
  for anyone. `data/spacex/` is git-ignored, holds only a thinned covariance series (a
  derived product, not the file), and is not published in the viewer bundle either.
- Fetch politely: one request per satellite per version, only for the satellites a run's
  events actually involve, never a sweep of the constellation. At 2 MB a file the whole
  11,000 would be 22 GB a version. `driftwatch spacex --limit` caps it, at 300 by default.

**Credit line** (`config.SPACEX_CITATION`):

```
Starlink ephemerides published by SpaceX (api.starlink.com/public-files/ephemerides/),
used for analysis; the raw files are not redistributed.
```

## Sources used in later steps and phases

- **ESA Kelvins Collision Avoidance Challenge dataset** (Step 3). Anonymised real
  conjunction messages released by ESA for the 2019 challenge, used to check the
  probability-of-collision code (`driftwatch kelvins`). The download needs an account
  on https://kelvins.esa.int/ and goes into `data/external/kelvins/` (git-ignored); the
  data are never redistributed by driftwatch, only the fitted hard-body radius and the
  residual statistics are reported. The terms are recorded here when it is first
  fetched; at the time of writing it had not been.
## NOAA Space Weather Prediction Center (services.swpc.noaa.gov)

**Used for.** Everything CelesTrak does not observe or predict: the three-day Kp forecast
(`noaa-planetary-k-index-forecast.json`), the real-time planetary K index
(`planetary_k_index_1m.json`), the 27-day outlook (`27-day-outlook.txt`) and the propagated
L1 solar wind (`propagated-solar-wind.json`). See `docs/space-weather.md`.

**Rules (read 2026-09-02).** Public, no account, no authentication, no stated rate limit.
US government work, so not subject to copyright. driftwatch caches each product with a floor
matched to how often it is actually reissued — thirty minutes for Kp, six hours for the
27-day outlook, fifteen minutes for the solar wind — and stores one file per issue rather
than one per fetch.

**What driftwatch republishes.** The derived space weather table and the analyses built on
it, which is what a public-domain product is for. The raw feeds are small and public; they
are stored locally for reproducibility (`data/weather/`, git-ignored) rather than
redistributed.

## Helioviewer (api.helioviewer.org)

**Used for.** A PNG of the Sun nearest a chosen time (SDO/AIA 193 A), a few frames a day, for
the Phase 3 Step 5 storm replay.

**Rules (read 2026-09-02).** Public API, no account. The documentation asks for credit rather
than imposing a licence, and the underlying images are NASA/SDO products, which are not
subject to copyright. `config.HELIOVIEWER_CITATION` carries the credit line:

```
Sun imagery courtesy of the Helioviewer Project (helioviewer.org), NASA/SDO and the AIA team.
```

## Sources used in later steps

- **NASA OMNIweb** (Phase 3, if the solar wind record is needed further back than SWPC's
  week). Public, no account. Terms recorded when first used.
