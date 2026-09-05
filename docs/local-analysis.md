# Local analysis: an operator's own files, on the operator's own machine

Built 2026-09-05, beside the calibration benchmark (`docs/calibration-benchmark.md`). The code is
`src/driftwatch/local.py`; the command is `driftwatch local`.

## Why this exists

The public demonstration is reproducible from public sources, and it stays that way: the daily
pipeline, the two validation storms, the Kelvins reproduction and the Swarm calibration read
nothing that is not public, and nothing here changes that. But the reader who can change what this
project does is an operator with real warnings, and an operator will not upload a Conjunction
Data Message, an ephemeris or a manoeuvre log to anybody. So the three instruments the project has
for that conversation run on the operator's machine, over the operator's files, with the network
refused for the duration:

1. **The provenance check** on a stored run (the logic of `driftwatch check-run`): is the run's
   recorded snapshot a real snapshot, how old is it, are the supplemental versions it used still
   stored, has it been scored.
2. **The CDM matcher** (`driftwatch cdm match`, `docs/cdm-matching.md`): which of the operator's
   conjunctions public data found, at what miss and probability against theirs, which it did not
   find, and which public-data flags on the operator's objects no message mentions.
3. **The calibration against the operator's ephemeris** — the Swarm benchmark's machinery with the
   operator's orbit as the truth. For every public element set issued while the ephemeris runs,
   the residual by lead in the satellite's radial, in-track, cross-track frame; the fraction of
   residuals inside the covariance the screening would have carried, against the 68 and 95 per
   cent it claims; the storm term's effect with the cached observed ap, if the weather is cached;
   and the lead beyond which the in-track residual exceeds the screening box's half-width. One
   element set is one trial, never one timestamp.

## Nothing leaves the machine

`driftwatch local` runs inside `driftwatch.local.no_network`, which replaces `httpx.Client.send`
and `httpx.AsyncClient.send` (every fetch this project makes goes through httpx), replaces
`urllib.request.urlopen` (astropy fetches IERS tables and leap seconds through it) and switches
astropy's auto-download off, then restores all four on exit. Any outbound request inside the block
raises `NetworkRefused` naming the URL, and the command exits with code 3. A test attempts a request
inside the guard and checks that the originals are restored afterwards.

What the command reads: the operator's files named on the command line; the local run store
(`data/conjunctions`); the local element-set history (`data/history`, `data/snapshots`) or a file
of OMM records the operator supplies; the cached CelesTrak space-weather file, if `--storm-term`
is given and it exists. What it writes: `local_analysis.json`, `local_analysis.md` and
`ephemeris_trials.parquet` under `--out`, and nothing else anywhere.

The element-set history is the one input that has to have been fetched beforehand, with the
network, by `driftwatch history` (Space-Track credentials) or by the operator handing the command
a JSON file of the object's OMM records in CelesTrak or Space-Track form (`--sets`). The command
does not fetch it and says so when it is missing.

## The inputs

- `--ephemeris`: a CCSDS Orbit Ephemeris Message (502.0-B-2) in KVN, or a directory of them. One or
  more segments, each `META_START` to `META_STOP` naming the object, the centre, `REF_FRAME` and
  `TIME_SYSTEM`, followed by state lines `epoch x y z vx vy vz` in km and km/s (a trailing
  acceleration is dropped; covariance blocks are skipped). Frames accepted: any ITRF realisation,
  TEME, and J2000/EME2000 (ICRF and GCRF are taken as J2000, a difference of tens of
  milliarcseconds). Time systems: UTC, TAI and GPS, converted through astropy's leap-second table.
  Anything else is refused by name rather than guessed, because a wrong frame is 44 km and a wrong
  time system is 137 km, both along track, both silent. A gap between samples wider than three
  times the file's own step (or 30 s, whichever is larger) stays a gap: nothing is interpolated
  across it, and a lead that lands in one is excluded and counted.
- `--norad`: the public catalogue id the ephemeris describes, so the right element sets are taken
  from the history.
- `--manoeuvres`: the operator's own record, a CSV with `start` and `end` columns of UTC times. It
  decides the exclusion: a trial is excluded when a manoeuvre falls between 24 hours before its
  element set's epoch (the tracking arc the set was fitted from) and the lead's time. The project's
  own detection (a step in the orbit-mean semi-major axis of the ephemeris; the jump detector on the
  element sets) is computed either way and reported beside the record as a cross-check; without a
  record it is what excludes, and every row says which.
- `--run` and `--cdm`: a stored run and the operator's messages, matched on the object pair and a
  TCA tolerance exactly as `driftwatch cdm match` does.
- `--storm-term`: apply the storm term with the cached observed ap. Skipped, and said so in the
  report, when the cached space-weather file is absent.

## The output

`local_analysis.md` has one section per instrument that ran: the provenance result with its
warnings and problems; the CDM match summary; and, for the ephemeris, the trial counts and
exclusions, the manoeuvre sentence (record or detection, and how the two compared), the table by
lead (in-track median and 95th percentile, coverage at one and two sigma, radial and cross-track
medians, the storm term's improvement where it ran) and the horizon for the named task. Every
source is listed at the end with where it came from. `local_analysis.json` carries the same with
every number, and `ephemeris_trials.parquet` is the per-trial file the numbers are computed from
(the same columns as the Swarm benchmark's `swarm_benchmark.parquet`).

## What this is not

It is not a way to get an operator's data into the public demonstration; the public site reads
nothing an operator supplies. It is not a validation of driftwatch: the first real folder of
messages and the first real ephemeris are measurements the operator makes of the tool, and what
they show is theirs to share or not. And it is not a substitute for the operator's own screening:
the horizon it reports is the lead beyond which the *public* element set cannot be trusted to
place the operator's satellite inside the screening box, which is a statement about the public
catalogue and not about the operator's orbit determination.

## Commands

```bash
driftwatch local --out <dir> --run latest                                   # provenance only
driftwatch local --out <dir> --run latest --cdm <messages>                  # plus the matcher
driftwatch local --out <dir> --ephemeris <oem> --norad <id> [--manoeuvres <csv>] [--storm-term]
driftwatch local --out <dir> --ephemeris <oem> --norad <id> --sets <omm.json>   # without a history store
```

Tests: `tests/test_local.py` — the guard refuses and restores; the OEM reader (segments, a gap, a
GPS-time segment moved 18 s, an unsupported frame refused by name); the manoeuvre record; and the
command end to end on a designed element set whose own SGP4 path is written out as the operator's
ephemeris, so the residual is the interpolation error alone, with a manoeuvre record outside the
tracking arc that excludes nothing and one inside it that excludes every lead.
