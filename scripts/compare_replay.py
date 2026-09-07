"""Compare an archived screening with its replay, object by object, without fetching."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from driftwatch.export.conjunctions import RunDirectory


def compare(archive: Path, replay: Path) -> dict:
    a, b = RunDirectory(archive), RunDirectory(replay)
    keys = ["primary_norad_id", "secondary_norad_id", "tca"]
    left = a.read_events().sort_values(keys).reset_index(drop=True)
    right = b.read_events().sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(left[keys], right[keys])
    maxima = {}
    for column in left.columns:
        if pd.api.types.is_float_dtype(left[column]):
            np.testing.assert_allclose(left[column], right[column], rtol=0, atol=1e-7, equal_nan=True, err_msg=column)
            maxima[column] = float((left[column] - right[column]).abs().max())
        else:
            pd.testing.assert_series_equal(left[column], right[column])
    risk_keys = ["event_id", "region", "confidence", "flag"]
    ar, br = a.read_risk("quiet"), b.read_risk("quiet")
    pd.testing.assert_frame_equal(
        ar[risk_keys].sort_values("event_id").reset_index(drop=True),
        br[risk_keys].sort_values("event_id").reset_index(drop=True),
    )
    counts = ["region", "confidence", "flag"]
    pd.testing.assert_series_equal(ar.groupby(counts).size(), br.groupby(counts).size())
    for name in ("supplemental", "config", "attached_excluded"):
        assert a.read_run()[name] == b.read_run()[name], name
    flagged = br[br.flag.isin(["red", "yellow"])]
    return {
        "archive": a.name,
        "replay": str(b.path),
        "events": len(left),
        "matched": True,
        "events_per_primary": left.groupby("primary_norad_id").size().to_dict(),
        "max_abs_difference_by_column": maxima,
        "quiet_flags": br.groupby(counts).size().rename("count").reset_index().to_dict("records"),
        "dilution_flags": int((flagged.region == "dilution").sum()),
        "flags": len(flagged),
        "attached_pairs_excluded": b.read_run()["attached_excluded"]["n_pairs"],
        "attached_candidates_dropped": b.read_run()["attached_excluded"]["n_candidates_dropped"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("replay", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(compare(args.archive, args.replay), indent=2)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
