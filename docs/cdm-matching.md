# Conjunction Data Messages: parsing them and matching them to a run

Built 2026-09-05, as one of the two items that replaced Steps 3 to 7 of Phase 4 (`ROADMAP.md`).
The code is `src/driftwatch/cdm/`; the command is `driftwatch cdm`.

## Why this exists

A public-data screening has no ground truth of its own. The Kelvins reproduction
(`docs/kelvins-reproduction.md`) checks the probability arithmetic against ESA's; the May 2024
validation (`docs/storm-validation.md`) checks the storm term against what the atmosphere did.
Neither says whether the **events** driftwatch reports are the events an operator was actually
warned about, at the misses and probabilities the operator was given. The only thing that can say
that is the operator's own warnings, and those arrive as Conjunction Data Messages (CCSDS
508.0-B-1): one message per warning, naming both objects, the time of closest approach, the miss
and its RTN components, both covariances and, usually, a probability.

So the tool that has to exist before the first operator conversation is one that takes a folder
of their messages and a stored run and says three things:

1. which of the operator's conjunctions public data found, and at what miss and probability
   against the message's;
2. which of them public data did **not** find;
3. which of driftwatch's red and yellow flags on the operator's own objects no message mentions.

That is what `driftwatch cdm match` prints and writes.

## The parser

`driftwatch.cdm.parse` reads both forms of the standard into one structure.

- **KVN** — `KEY = value [unit]` lines. The header and the relative metadata and data (TCA, miss,
  relative state, screening period, probability and its method) come first; `OBJECT = OBJECT1`
  and `OBJECT = OBJECT2` introduce each object's metadata, orbit-determination fields, state vector
  and covariance. `COMMENT` lines are kept per section.
- **XML** — the same keys as element names inside `header`, `relativeMetadataData` and two
  `segment` blocks, with units as attributes. Namespaces are ignored; the two segments are the two
  objects, in document order, each confirmed by its `OBJECT` element.

Every key read is kept verbatim in `raw`, with its unit in `units`, so nothing the standard allows
is lost by the fields this project happens to type. The typed fields are the ones the matcher and
the report need: both designators (normalised so `00025544` and `25544` compare equal), the TCA
(calendar or day-of-year form, read as UTC), the miss and relative state, the probability and its
method, and each object's 3 × 3 RTN position covariance from the six lower-triangle terms. Units
stay as the standard has them — metres for the relative quantities, kilometres for the state
vectors, square metres for the covariance — and are converted at the point of use, so a message
written back out with `to_kvn` reads back equal. `load_cdms` reads a file or a whole directory
(`*.cdm`, `*.kvn`, `*.txt`, `*.xml`), and a file without a TCA is refused by name rather than
skipped.

## The matcher

`driftwatch.cdm.match.match_cdms` joins messages to a run's joined conjunction rows on exactly two
things: the **unordered object pair** and the **time of closest approach within a tolerance**,
ten minutes by default. Those are the same two things the warning-stability index uses to say two
runs saw one encounter (`docs/pipeline.md`), and they are the only things that may take part in
deciding what is compared: the miss, the probability and the covariance are what the comparison
measures.

**Many messages to one event.** An operator receives several messages about one conjunction as
its time approaches — the Kelvins rows carry a median of a dozen per event — while a run has one
event per pass. Each message is therefore matched to the nearest driftwatch event of its pair
inside the tolerance, several messages may share an event, and the report counts both messages
and *distinct operator conjunctions* (one pair, one TCA to the minute).

The three outputs:

| Output | What it is |
| --- | --- |
| `matches` | One row per message public data found: both TCAs and their offset, the message's miss and probability beside driftwatch's shifted miss and probability, and driftwatch's region, confidence and flag for the event. `miss_ratio` and `log10_pc_ratio` are driftwatch over the message. |
| `unmatched_cdms` | Messages whose pair is not in the run, or whose nearest event of the pair is past the tolerance. These are the operator warnings public data did not find. |
| `unwarned_flags` | Driftwatch's red and yellow events on the operator's own objects (every designator that appears as `OBJECT1`), inside the span the messages cover (their stated screening period, or the span of their TCAs), that no message matched. |

The summary counts all three, with the median and maximum TCA offset of the matches, the median
and 16th to 84th percentile of the miss ratio and of the log10 probability ratio, the matched
events by flag, and the unmatched messages by reason.

**What the third output cannot say.** An unwarned flag is either a real conjunction the
operator's provider did not flag, or a public-data flag that was not real — a dilution-region
number held up by the covariance, for instance. The matcher cannot tell which, and the report
prints the region and confidence first on every such row for that reason.

## The Kelvins rows as test input

Nobody had sent a message when this was built, so the parser and the matcher were built against
the nearest real thing: ESA's Kelvins challenge rows, which are operational CDMs with the
identities removed. `driftwatch.cdm.kelvins` turns a row back into a message. Every field the row
has goes in under its CDM name — the miss, the RTN relative position and velocity, the relative
speed, both covariances from the sigmas and correlations, the object type, the orbit-determination
fields (`ACTUAL_OD_SPAN`, `OBS_USED`, `WEIGHTED_RMS`, `CD_AREA_OVER_MASS` and the rest) and the
operator's probability from `risk` — and the two fields the anonymisation removed are given
deterministic synthetic values that no real object carries: `OBJECT1 = 900000 + mission_id`,
`OBJECT2 = 800000 + event_id`, a TCA at a fixed reference epoch (9 May 2024) plus an offset keyed
on the event id, and a creation date `time_to_tca` days before it. Every message says so in a
COMMENT.

`kelvins_events` builds the matching driftwatch-shaped events table from the same rows — one row
per conjunction, the last message's numbers — so the matcher can be tested against an answer known
by construction. The tests (`tests/test_cdm.py`) perturb it: one event moved 90 s (inside the
tolerance, matched with its offset recorded), one moved 40 minutes (past it, reported), one dropped
(reported as a pair not in the run), one flagged event added that no message mentions (reported as
an unwarned flag). The real challenge file, when it is under `data/external/kelvins/`, is run
through the same path on its first 400 rows.

**This is a test of the plumbing, not a validation of anything.** Matching messages to events built
from the same rows agrees by construction; the numbers it produces mean nothing about screening
quality. The first real measurement is the first real folder of messages.

## The commands

```bash
driftwatch cdm parse <files or directories>          # one summary line per message
driftwatch cdm match <run> --cdm <dir> [--scenario quiet] [--tolerance-s 600] [--out matches.json]
driftwatch cdm from-kelvins --out-dir <dir> [--limit 200]   # Kelvins rows as KVN test messages
```

`match` prints the summary, the first rows of each table (region and confidence first on the
unwarned flags) and, with `--out`, writes the three tables and the summary as one JSON file.

## What a real message will test that the Kelvins rows cannot

- **Identity.** Real designators are NORAD ids, and the run's `primary_norad_id` and
  `secondary_norad_id` are the same ids, so the join is exact. A message naming an object by
  international designator alone would not match; the standard makes `OBJECT_DESIGNATOR`
  obligatory, so this should not arise.
- **Time.** A real TCA is absolute. The tolerance is ten minutes; the stability index measured a
  run-to-run TCA movement of 0.3 s median and 20.8 s at most between two driftwatch runs, but
  a provider's orbit determination and CelesTrak's fit will disagree by more than two driftwatch
  runs do, and the first real folder is where the tolerance gets measured rather than argued.
- **Coverage.** A provider screens against its own catalogue, which is larger than the public one
  and includes analyst objects the public catalogue has not yet correlated. Unmatched messages
  whose `OBJECT2` is not in the run are the measurement of that gap.
