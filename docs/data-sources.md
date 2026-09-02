# Data sources and their terms

What driftwatch downloads, where from, under which rules, and what it may republish.
Terms are quoted as read on the date given. Check the source page before relying on them
and update the date here when you do.

## CelesTrak (celestrak.org)

**Used for.** GP element sets (OMM JSON) by group, the SATCAT metadata table and, from
Step 2 of Phase 2, the supplemental Starlink element sets (`sup-gp.php?FILE=starlink`,
SGP4 fits CelesTrak makes to SpaceX's published ephemerides; the fit residuals are
published alongside as `starlink.rms.txt`). Phase 3 adds the `SW-All.csv` space-weather
file.

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

## Sources used in later steps and phases

- **ESA Kelvins Collision Avoidance Challenge dataset** (Step 3). Anonymised real
  conjunction messages released by ESA for the 2019 challenge, used to check the
  probability-of-collision code (`driftwatch kelvins`). The download needs an account
  on https://kelvins.esa.int/ and goes into `data/external/kelvins/` (git-ignored); the
  data are never redistributed by driftwatch, only the fitted hard-body radius and the
  residual statistics are reported. The terms are recorded here when it is first
  fetched; at the time of writing it had not been.
- **CelesTrak `SW-All.csv`, NOAA SWPC JSON feeds, NASA OMNIweb** (Phase 3). Public,
  no account, no redistribution restriction beyond credit. Terms recorded when first used.
