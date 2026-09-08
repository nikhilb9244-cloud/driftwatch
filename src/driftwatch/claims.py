"""Current public wording and identities, generated from the claims manifest."""

import json
from pathlib import Path

MANIFEST = json.loads(Path(__file__).with_name("public_claims.json").read_text(encoding="utf-8"))
CLAIMS = {row["id"]: row for row in MANIFEST["claims"]}


def wording(claim_id: str) -> str:
    return CLAIMS[claim_id]["permitted_wording"]


def identity(claim_id: str) -> dict:
    return {
        key: CLAIMS[claim_id][key]
        for key in (
            "id",
            "result_hash",
            "method_version",
            "population",
            "denominator",
            "reference_type",
            "censoring_state",
        )
    }


HORIZON_HEADLINE = wording("horizon_overview")
STORM_CALIBRATION_NOTE = wording("consistency")
STORM_CALIBRATION_SHORT = STORM_CALIBRATION_NOTE
