"""Matching operator CDMs to driftwatch events, and saying what each side had that the other did not.

The join is on the **unordered object pair** and the **time of closest approach within a
tolerance**, the same two things the warning-stability index uses to say two runs saw the same
encounter (`docs/pipeline.md`). Nothing else is comparable across the two sources: the miss,
the probability and the covariance are exactly what the comparison is meant to measure, so none
of them may take part in deciding what is being compared.

**Many messages to one event.** An operator receives several CDMs about one conjunction as its
time approaches -- the Kelvins rows carry a median of a dozen per event -- while a driftwatch
run has one event per pass. So every message is matched to the nearest driftwatch event of its
pair inside the tolerance, several messages may share one event, and the report counts both
messages and *distinct operator conjunctions* (one pair, one time of closest approach to the
minute).

Three outputs, and the last two are the point:

* ``matches`` -- one row per CDM that public data found, with both misses and both probabilities;
* ``unmatched_cdms`` -- conjunctions the operator was warned about that public data did not find
  within the tolerance, which is the miss rate of a public-data screening against the real thing;
* ``unwarned_flags`` -- driftwatch's red and yellow events on the operator's own objects, inside
  the span the messages cover, that no CDM mentions. Either the operator's provider did not flag
  them, or public data raised a flag that was not real; the report cannot tell which, and says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from driftwatch.cdm.parse import ConjunctionDataMessage, normalise_designator

#: Two encounters of the same pair inside this are the same encounter. Ten minutes: the
#: warning-stability index measured a run-to-run TCA movement of 0.3 s median and 20.8 s at
#: most, against a ~46-minute gap between successive passes of one pair.
DEFAULT_TOLERANCE_S = 600.0
#: The flags a public-data screening would have wanted the operator to see.
ACTIONABLE_FLAGS: tuple[str, ...] = ("red", "yellow")


@dataclass
class MatchResult:
    matches: pd.DataFrame
    unmatched_cdms: pd.DataFrame
    unwarned_flags: pd.DataFrame
    summary: dict[str, Any] = field(default_factory=dict)


def cdm_table(cdms: list[ConjunctionDataMessage]) -> pd.DataFrame:
    """One row per message with the fields the matcher and the report use."""
    rows = []
    for k, cdm in enumerate(cdms):
        rows.append(
            {
                "cdm_index": k,
                "message_id": cdm.message_id,
                "originator": cdm.originator,
                "creation_date": cdm.creation_date,
                "object1": cdm.object1.designator,
                "object2": cdm.object2.designator,
                "cdm_tca": cdm.tca,
                "cdm_miss_km": cdm.miss_distance_m / 1000.0,
                "cdm_relative_speed_kms": cdm.relative_speed_ms / 1000.0,
                "cdm_pc": cdm.collision_probability,
                "cdm_pc_method": cdm.collision_probability_method,
                "source": cdm.source,
            }
        )
    out = pd.DataFrame(rows)
    if len(out):
        out["cdm_tca"] = pd.to_datetime(out["cdm_tca"], utc=True)
        out["creation_date"] = pd.to_datetime(out["creation_date"], utc=True)
        out["conjunction_key"] = [
            f"{'|'.join(sorted((a, b)))}@{t.floor('min').isoformat()}"
            for a, b, t in zip(out["object1"], out["object2"], out["cdm_tca"], strict=True)
        ]
    return out


def _pair_key(a: Any, b: Any) -> frozenset[str]:
    return frozenset({normalise_designator(a), normalise_designator(b)})


def match_cdms(
    cdms: list[ConjunctionDataMessage],
    events: pd.DataFrame,
    *,
    tolerance_s: float = DEFAULT_TOLERANCE_S,
    scenario: str | None = None,
) -> MatchResult:
    """Match every message to the nearest driftwatch event of its pair within ``tolerance_s``.

    ``events`` is a joined-conjunctions frame (``conjunctions.parquet`` rows, or the events table
    joined with one scenario's risk rows): it needs ``primary_norad_id``, ``secondary_norad_id``
    and ``tca``, and uses ``event_id``, ``miss_km``, ``miss_shifted_km``, ``pc``, ``flag``,
    ``region``, ``confidence`` and ``scenario`` where they are present. With several scenarios in
    the frame, ``scenario`` picks one; the default is ``quiet``.
    """
    table = cdm_table(cdms)
    ev = events.copy()
    if "scenario" in ev.columns and ev["scenario"].notna().any():
        wanted = scenario or ("quiet" if (ev["scenario"] == "quiet").any() else str(ev["scenario"].dropna().iloc[0]))
        ev = ev[ev["scenario"].astype(str) == wanted]
        scenario = wanted
    ev = ev.reset_index(drop=True)
    ev["tca"] = pd.to_datetime(ev["tca"], utc=True)
    ev["_key"] = [_pair_key(a, b) for a, b in zip(ev["primary_norad_id"], ev["secondary_norad_id"], strict=True)]
    by_pair: dict[frozenset[str], pd.DataFrame] = {k: g for k, g in ev.groupby("_key")} if len(ev) else {}

    matched_rows: list[dict[str, Any]] = []
    unmatched_rows: list[dict[str, Any]] = []
    matched_event_ids: set[Any] = set()
    for row in table.itertuples(index=False):
        candidates = by_pair.get(_pair_key(row.object1, row.object2))
        record = row._asdict()
        if candidates is None or not len(candidates):
            record["reason"] = "pair not in the run"
            unmatched_rows.append(record)
            continue
        dt = (candidates["tca"] - row.cdm_tca).dt.total_seconds().to_numpy(dtype=float)
        nearest = int(np.argmin(np.abs(dt)))
        if abs(dt[nearest]) > tolerance_s:
            record["reason"] = f"nearest event of the pair is {abs(dt[nearest]):.0f} s away, past the tolerance"
            record["nearest_dt_s"] = float(dt[nearest])
            unmatched_rows.append(record)
            continue
        event = candidates.iloc[nearest]
        matched_event_ids.add(event.get("event_id", event.name))
        record.update(
            {
                "event_id": event.get("event_id", event.name),
                "event_tca": event["tca"],
                "dt_tca_s": float(dt[nearest]),
                "event_miss_km": float(event.get("miss_km", np.nan)),
                "event_miss_shifted_km": float(event.get("miss_shifted_km", event.get("miss_km", np.nan))),
                "event_pc": float(event.get("pc", np.nan)),
                "event_flag": str(event.get("flag", "")),
                "event_region": str(event.get("region", "")),
                "event_confidence": str(event.get("confidence", "")),
                "event_storm_validity": str(event.get("storm_validity", "")),
                "scenario": scenario,
            }
        )
        matched_rows.append(record)

    matches = pd.DataFrame(matched_rows)
    unmatched = pd.DataFrame(unmatched_rows)
    if len(matches):
        with np.errstate(invalid="ignore", divide="ignore"):
            matches["miss_ratio"] = matches["event_miss_km"] / matches["cdm_miss_km"]
            matches["log10_pc_ratio"] = np.log10(matches["event_pc"] / matches["cdm_pc"])

    # Flags the operator never received: red or yellow driftwatch events on the operator's own
    # objects (every designator that appears as OBJECT1), inside the span the messages cover,
    # that no message matched.
    unwarned = ev.iloc[0:0]
    if len(ev) and len(table):
        operators = {normalise_designator(o) for o in table["object1"]}
        own = ev["primary_norad_id"].map(normalise_designator).isin(operators) | ev["secondary_norad_id"].map(
            normalise_designator
        ).isin(operators)
        span_lo, span_hi = _covered_span(cdms, table)
        inside = (ev["tca"] >= span_lo) & (ev["tca"] <= span_hi)
        flagged = (
            ev["flag"].astype(str).isin(ACTIONABLE_FLAGS) if "flag" in ev.columns else pd.Series(True, index=ev.index)
        )
        not_matched = ~ev.get("event_id", pd.Series(ev.index, index=ev.index)).isin(matched_event_ids)
        unwarned = ev[own & inside & flagged & not_matched]
    unwarned = unwarned.drop(columns=["_key"], errors="ignore").reset_index(drop=True)

    summary = _summary(table, matches, unmatched, unwarned, tolerance_s, scenario)
    return MatchResult(matches, unmatched, unwarned, summary)


def _covered_span(cdms: list[ConjunctionDataMessage], table: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """The screening period the messages state, or the span of their TCAs when they state none."""
    periods = [c.screen_period for c in cdms if c.screen_period is not None]
    if periods:
        return min(p[0] for p in periods), max(p[1] for p in periods)
    return table["cdm_tca"].min(), table["cdm_tca"].max()


def _summary(
    table: pd.DataFrame,
    matches: pd.DataFrame,
    unmatched: pd.DataFrame,
    unwarned: pd.DataFrame,
    tolerance_s: float,
    scenario: str | None,
) -> dict[str, Any]:
    distinct = table["conjunction_key"].nunique() if len(table) else 0
    found = matches["conjunction_key"].nunique() if len(matches) else 0
    out: dict[str, Any] = {
        "scenario": scenario,
        "tolerance_s": tolerance_s,
        "n_cdms": int(len(table)),
        "n_operator_conjunctions": int(distinct),
        "n_conjunctions_found_by_public_data": int(found),
        "n_conjunctions_public_data_missed": int(distinct - found),
        "n_cdms_matched": int(len(matches)),
        "n_cdms_unmatched": int(len(unmatched)),
        "n_public_flags_operator_never_received": int(len(unwarned)),
    }
    if len(matches):
        dt = matches["dt_tca_s"].abs()
        out["dt_tca_s"] = {"median_abs": round(float(dt.median()), 1), "max_abs": round(float(dt.max()), 1)}
        ratio = matches["miss_ratio"].replace([np.inf, -np.inf], np.nan).dropna()
        if len(ratio):
            out["miss_ratio_event_over_cdm"] = {
                "median": round(float(ratio.median()), 3),
                "p16": round(float(ratio.quantile(0.16)), 3),
                "p84": round(float(ratio.quantile(0.84)), 3),
            }
        pc = matches["log10_pc_ratio"].replace([np.inf, -np.inf], np.nan).dropna()
        if len(pc):
            out["log10_pc_ratio_event_over_cdm"] = {
                "median": round(float(pc.median()), 3),
                "p16": round(float(pc.quantile(0.16)), 3),
                "p84": round(float(pc.quantile(0.84)), 3),
                "n": int(len(pc)),
            }
        if "event_flag" in matches.columns:
            out["matched_by_event_flag"] = {str(k): int(v) for k, v in matches["event_flag"].value_counts().items()}
    if len(unmatched) and "reason" in unmatched.columns:
        out["unmatched_by_reason"] = {
            str(k): int(v) for k, v in unmatched["reason"].str.split(" is ").str[0].value_counts().items()
        }
    return out


def report_lines(result: MatchResult) -> list[str]:
    """The comparison as plain text, for the command and for a run's notes."""
    s = result.summary
    lines = [
        f"{s['n_cdms']} CDM(s) describing {s['n_operator_conjunctions']} distinct operator conjunction(s), "
        f"matched on the object pair and a TCA tolerance of {s['tolerance_s']:g} s"
        + (f" against scenario {s['scenario']}" if s.get("scenario") else ""),
        f"  public data found {s['n_conjunctions_found_by_public_data']} of them "
        f"({s['n_cdms_matched']} messages) and missed {s['n_conjunctions_public_data_missed']} "
        f"({s['n_cdms_unmatched']} messages)",
        f"  public-data flags the operator never received: {s['n_public_flags_operator_never_received']}",
    ]
    if "dt_tca_s" in s:
        lines.append(f"  matched TCA offset: median {s['dt_tca_s']['median_abs']} s, max {s['dt_tca_s']['max_abs']} s")
    if "miss_ratio_event_over_cdm" in s:
        r = s["miss_ratio_event_over_cdm"]
        lines.append(f"  miss, driftwatch over CDM: median {r['median']} (p16 {r['p16']}, p84 {r['p84']})")
    if "log10_pc_ratio_event_over_cdm" in s:
        r = s["log10_pc_ratio_event_over_cdm"]
        lines.append(
            f"  log10 probability, driftwatch over CDM: median {r['median']} (p16 {r['p16']}, p84 {r['p84']}) "
            f"over {r['n']} messages with both numbers"
        )
    if "unmatched_by_reason" in s:
        lines.append(f"  why messages went unmatched: {s['unmatched_by_reason']}")
    lines.append(
        "  An unmatched message is a conjunction the operator was warned about that this run did not find "
        "within the tolerance; an unwarned flag is a public-data flag no message mentions, and the report "
        "cannot tell whether the provider did not raise it or public data raised one that was not real."
    )
    return lines


__all__ = ["ACTIONABLE_FLAGS", "DEFAULT_TOLERANCE_S", "MatchResult", "cdm_table", "match_cdms", "report_lines"]
