"""Explicit event/state times and publication-aware selection, without invented dates."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

EPOCH_RECONSTRUCTION = "epoch-based reconstruction"
CAUSAL_REPLAY = "causal replay"
TIME_FIELDS = ("provider_created_at", "published_at", "retrieved_at")


def utc(value):
    if value is None or pd.isna(value):
        return pd.NaT
    result = pd.Timestamp(value)
    return result.tz_localize("UTC") if result.tzinfo is None else result.tz_convert("UTC")


def normalise(frame, *, epoch_column="epoch"):
    frame = frame.copy()
    if epoch_column in frame:
        frame[epoch_column] = pd.to_datetime(frame[epoch_column], utc=True, format="mixed")
    for field in TIME_FIELDS:
        if field not in frame:
            frame[field] = frame.get("fetched_at", pd.NaT) if field == "retrieved_at" else pd.NaT
        frame[field] = pd.to_datetime(frame[field], utc=True, format="mixed")
        if field == "retrieved_at" and "fetched_at" in frame:
            frame[field] = frame[field].fillna(pd.to_datetime(frame.fetched_at, utc=True, format="mixed"))
    return frame


def available(frame, as_of):
    """Known publication wins; otherwise actual retrieval proves availability by that time.

    Creation, state/event epoch, file mtime and local import time are never substitutes.
    A known later publication excludes the record even if other dates precede the cutoff.
    """
    frame = normalise(frame)
    cutoff = utc(as_of)
    if pd.isna(cutoff):
        raise ValueError("Causal replay requires a decision time")
    publication = frame.published_at
    return (publication.notna() & (publication <= cutoff)) | (
        publication.isna() & frame.retrieved_at.notna() & (frame.retrieved_at <= cutoff)
    )


def select(frame, *, as_of, selection_kind=EPOCH_RECONSTRUCTION, epoch_column="epoch", restrict_epoch=True):
    if selection_kind not in {EPOCH_RECONSTRUCTION, CAUSAL_REPLAY}:
        raise ValueError("Unknown availability selection kind")
    result = normalise(frame, epoch_column=epoch_column)
    cutoff = utc(as_of)
    if restrict_epoch:
        if pd.isna(cutoff):
            raise ValueError("Epoch selection requires a decision time")
        result = result[result[epoch_column] <= cutoff]
    if selection_kind == CAUSAL_REPLAY:
        result = result[available(result, cutoff)]
    result = result.copy()
    result["selection_kind"] = selection_kind
    return result


def membership_at(records, *, as_of, selection_kind):
    """Latest effective catalogue membership known under the declared selection rule."""
    if not {"norad_id", "effective_at", "present"} <= set(records):
        raise ValueError("Membership requires norad_id, effective_at and present")
    records = select(records, as_of=as_of, selection_kind=selection_kind, epoch_column="effective_at")
    if not pd.api.types.is_bool_dtype(records.present) or records.present.isna().any():
        raise ValueError("Membership present must be a boolean")
    latest = records.sort_values(
        ["effective_at", "provider_created_at", "retrieved_at"], na_position="first", kind="stable"
    )
    latest = latest.drop_duplicates("norad_id", keep="last")
    return latest[latest.present].copy()


def metadata(frame, *, epoch_column="epoch"):
    frame = normalise(frame, epoch_column=epoch_column)
    keys = [
        k
        for k in (
            "norad_id",
            "present",
            "end",
            epoch_column,
            *TIME_FIELDS,
            "source_identifier",
            "source_sha256",
            "selection_kind",
        )
        if k in frame
    ]
    result = []
    for values in frame[keys].to_dict("records"):
        result.append(
            {k: None if pd.isna(v) else v.isoformat() if isinstance(v, pd.Timestamp) else v for k, v in values.items()}
        )
    return result


def write_records(frame, path, *, epoch_column="epoch"):
    """Reopenable provenance table; no date is inferred from the destination or save time."""
    record = {"epoch_column": epoch_column, "rows": []}
    frame = normalise(frame, epoch_column=epoch_column)
    for row in frame.to_dict("records"):
        record["rows"].append(
            {k: None if pd.isna(v) else v.isoformat() if isinstance(v, pd.Timestamp) else v for k, v in row.items()}
        )
    Path(path).write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def read_records(path):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalise(pd.DataFrame(record["rows"]), epoch_column=record["epoch_column"])
