# Reopenable adapter cases

The case bundle records the supplied files, their hashes and individual redistribution rights; state, creation, publication and retrieval times; conventions; the selected adapter; the exact source and dependency lock; baseline and candidate outputs; signed Cartesian position and velocity differences; the recorded criterion, decision and limitations. Unknown dates remain null. Packing requires an explicit rights basis and a criterion recorded before evaluation. A customer case must name the customer's agreed criterion and decision owner. The public demonstration records that no customer has agreed its criterion.

The initial bounded profile compares one TLE or OMM element set per input using Earth-centred TEME, UTC, km, km/s, SGP4, WGS72 and improved operation mode. It requires matching catalogue and international identifiers, and records the difference as candidate minus baseline. Unsupported conventions, invalid propagation, changed inputs or incomplete rights records fail explicitly. This is an adapter acceptance review; the agreed numerical comparison does not establish product accuracy or general OMM conformance.

To create a case, first write its `case.json` and supplied files using the public case as the schema example, then run:

```sh
uv run python -m driftwatch.case_bundle pack case/case.json case.zip
uv run python -m driftwatch.case_bundle unpack case.zip reopened-case
cd reopened-case
uv sync --frozen --no-dev --python 3.12.14
uv run --frozen --no-dev python -m driftwatch.case_bundle verify .
```

The Python version is recorded in each bundle's `environment.json`; use that version when reopening another case. Installing the recorded dependencies may access package indexes. Evaluation itself blocks outbound HTTP and uses only the supplied files. Reopening checks every member hash, the installed numerical versions and bundled source before reproducing the decision. Reproduction tolerances are recorded separately from the customer's acceptance tolerance. Archive paths, duplicate entries, symbolic links and excessive uncompressed size are checked before extraction.

The [public Swarm A bundle](assets/cases/public-swarm-a.zip) was built from an April element set in the local history store. Its baseline is a TLE re-encoding and its candidate is OMM-keyword JSON from the same GP fields. The criterion was recorded before residual evaluation: at six hours, one, two, three and seven days, the maximum position difference must be at most 0.01 km and the velocity difference at most 0.00001 km/s. This is a format-preservation check, with no independent reference orbit or short-window dynamical claim. Both source formats carry attribution under [Space-Track's basic SSA redistribution permission](https://www.space-track.org/documentation#odr).

The [asset record](assets/cases/public-swarm-a.json) contains its hash and the Windows reproduction result. The `Public case reproduction` Actions workflow starts with a fresh Linux clone without local data, checks the public ZIP hash, unpacks it outside the clone, installs the source and lock inside the bundle, and reproduces its decision with data networking disabled. This is an automated second-machine test. An independent person reopening a rights-cleared customer case remains a separate acceptance condition.

The [second-machine run completed successfully on 8 September](assets/cases/second-machine-2026-09-08.json), reproducing the acceptance decision within the recorded numerical tolerances. The subsequent [migration matrix](migration-audit-2026-09-08.md) records three passed axes, one failed axis and two untested axes. Missing optional fields acquire defaults, and covariance metadata is lost by the history adapter; these defects remain recorded. Browser display/export and the complete browser round trip remain untested. Passing the CLI bundle check does not resolve them.
