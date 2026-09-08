# TLE-to-OMM audit of driftwatch's own paths

Audit time: 2026-09-08T20:54:50.033293+00:00

One public history-store case and declared format/identity variants. Customer adapters remain unverified.

| Axis | Status | Check | Evidence |
| --- | --- | --- | --- |
| Object identity (untested) | passed | json identifier 39452: import, history and inspection API | {"identifiers": [39452, 39452, 39452], "construction": "stored identity"} |
| Object identity (untested) | passed | tle identifier 100001: import, history and inspection API | {"identifiers": [100001, 100001, 100001], "construction": "identifier-only variant of the public case; not another observed spacecraft"} |
| Object identity (untested) | passed | json identifier 999999999: import, history and inspection API | {"identifiers": [999999999, 999999999, 999999999], "construction": "identifier-only variant of the public case; not another observed spacecraft"} |
| Object identity (untested) | untested | Browser display and exported identity joins | Inspection API was exercised; browser display and export were not automated. |
| Time and availability (passed) | passed | State epoch and provider creation stay distinct | {"state_epoch": "2024-04-01T12:17:27.273408+00:00", "provider_created_at": "2024-04-02T00:00:00+00:00"} |
| Time and availability (passed) | passed | Actual supplied retrieval time survives history storage | 2026-09-08T00:00:00+00:00 |
| Time and availability (passed) | passed | Unknown publication and acquisition remain unknown | Neither epoch nor local import time establishes publication or retrieval |
| Frame, centre and units (passed) | passed | Unsupported REF_FRAME fails explicitly | ITRF |
| Frame, centre and units (passed) | passed | Unsupported CENTER_NAME fails explicitly | MARS |
| Frame, centre and units (passed) | passed | Unsupported TIME_SYSTEM fails explicitly | TAI |
| Frame, centre and units (passed) | passed | Unsupported declared mean-motion units fail explicitly | rad/s refused |
| Mean-element theory (passed) | passed | Same public elements through TLE and OMM preserve the declared SGP4 output | {"accepted": true, "max_position_difference_km": 7.697422427244107e-06, "max_velocity_difference_km_s": 8.576288718861792e-09, "criterion_sha256": "4a93840b3738a86b6ba370500aa5a5c25f552c5a8ab3483012f5586c4de10a9d", "limitations": ["Public adapter demonstration; no customer has agreed or accepted this criterion.", "The baseline is a TLE encoding of the same stored mean elements; it is not independent truth.", "Agreement measures encoding and adapter behaviour, not orbit accuracy or operational suitability.", "Single mission and element epoch; no transfer to other adapters or unsupported conventions.", "No short-window dynamical validation or timing application is claimed.", "Unknown provider creation and publication times remain unknown."]} |
| Mean-element theory (passed) | passed | Unsupported mean-element theory is refused | DSST |
| Optional and missing data (failed) | failed | Missing optional values remain unknown | {"CLASSIFICATION_TYPE": "U", "ELEMENT_SET_NO": 0, "REV_AT_EPOCH": 0} |
| Optional and missing data (failed) | failed | Supplied covariance metadata and matrix survive the history adapter | {"decoded": true, "retained_in_history": false, "explicit_rejection": false} |
| Full adapter path (untested) | passed | Legacy and OMM identity joins agree | Same public spacecraft and international designator |
| Full adapter path (untested) | untested | Full browser, save/open and export round trip | CLI bundle reopening was independently verified; an end-to-end browser case workflow was not exercised. |

The optional-field and covariance failures are recorded defects, not repaired by this audit. The full browser round trip remains untested. No standards certification, product-accuracy result or customer acceptance follows from the passing rows.

[Machine-readable record](assets/cases/migration-audit-2026-09-08.json); [second-machine bundle reproduction](assets/cases/second-machine-2026-09-08.json).
