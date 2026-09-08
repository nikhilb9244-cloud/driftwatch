# Write-up notes: identities and bounded findings

The public account leads with the Swarm horizon and uncertainty coverage. The population is
three related spacecraft, the trial is one element set at each lead, and the evidence comprises
the quiet, May and held-out October windows. No general spacecraft horizon, operational
collision probability, forecast skill or adoption claim follows from those measurements.

## Object names and flag interpretation

Anonymisation was applied and then withdrawn. The original rationale was that an indicative
warning beside a named operator's satellite could imply a level of knowledge or consent the
project did not have. A category and catalogue number were intended to reduce that reputational
risk; stations were treated as already public infrastructure.

That policy withheld no identity: every NORAD number is public and resolves directly to the
catalogue name, and the same public bundle already joined those identifiers to names. Replacing
`EOS SAT-1` with `payload 55053` therefore reduced readability while implying protection that
did not exist. The public export again uses real object names. Naming a public spacecraft does
not imply its operator's participation, endorsement or agreement with the analysis.

Every flag retains **region, confidence, then colour**. In particular, **dilution region, low
confidence, red** describes sensitivity to the covariance rather than an actionable encounter.
Robust-region flags remain indicative and do not establish accurate positions. Headline flag
counts carry the dilution numerator, denominator and proportion.

## Corrections that remain part of the findings

- The 0.20 km supplemental fit residual did not describe extrapolation across a 72-hour file.
  The nineteen-file comparison reached a median 82.9 km at 60–72 hours against operator predictions,
  not realised orbits. The lineage-qualified sample contains seventeen files. Neither is a
  constellation-wide accuracy result.
- MEME/J2000 states were misread as TEME; GPS epochs in ESA SP3 files were misread as UTC.
  The first produced tens of kilometres of error; the second produced an approximately 137 km
  along-track offset. Internally consistent computations did not expose those source errors.
- The ISS's attached hardware was counted as independent conjunctions. Excluding co-orbiting
  pairs corrects that population; it does not remove unresolved slow encounters, for which the
  two-dimensional probability approximation has unmeasured error direction and magnitude in slow encounters.
- Storm displacement was applied to operator-controlled objects. Their means now remain fixed
  under that term; only appropriate uncertainty widening remains. The resulting large mean-shift
  headline and the common-mode-cancellation explanation were withdrawn.
- A covariance fit read outside its stated history window. Correct bounding changed quiet flags
  from 21 to 12 in the 3 September sample. The benchmark's own bounded fits were unaffected.
- A pooled correlation concealed lead-time dependence. The revised findings retain the sample
  counts and period/lead partitions in [storm-validation.md](storm-validation.md). Unmeasured
  ballistic coefficients have no demonstrated storm-correction skill.
- The claim that correction always hurts inside three days was too broad: October improves at
  6–120 hours, while May worsens at 12–72 hours and quiet worsens at 1–6 days.
- Swarm's 0.544 km and 32.845 km medians over 1,440 samples were incorrectly attributed to the
  ISS contact example in a report. The generated examples are distinct; the ISS has three
  predicted passes, no independent orbit reference and no measured receiver log.
- Cache-based offline screening did not reproduce the recorded supplemental input. Explicit
  archive replay now reads the versioned parquet, retains the attached filter and matches all
  5,766 events and quiet flags in the 5 September archive.

The [full findings](findings.md), [methods](methods.md) and [claims audit](claims-audit.md) retain
the numerical populations and limits.

_Last updated 7 September 2026._
