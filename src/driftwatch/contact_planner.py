"""Exact weighted interval scheduling for one antenna and declared feasible contacts."""

from bisect import bisect_right
from decimal import Decimal

import pandas as pd

from driftwatch.imports import scalar, tabular

REQUIRED = ("contact_id", "satellite", "start", "end", "priority")
FLAGS = ("baseline", "locked")


def flag(value: str, name: str, identity: str) -> bool:
    value = value.strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no", ""}:
        return False
    raise ValueError(f"Contact {identity}: {name} needs true/false, yes/no, 1/0 or a blank false value.")


def conflicts(a: dict, b: dict, gap: float) -> bool:
    return not (a["end_s"] + gap <= b["start_s"] or b["end_s"] + gap <= a["start_s"])


def priority_sum(contacts: list[dict]) -> float:
    return float(sum((Decimal(str(c["priority"])) for c in contacts), Decimal(0)))


def schedule_contacts(text: str, *, turnaround_s=60, mapping=None, delimiter=",") -> dict:
    columns, rows = tabular(text, delimiter)
    if len(rows) > 5000:
        raise ValueError("Plan at most 5,000 candidate contacts for one antenna.")
    if mapping is not None and not isinstance(mapping, dict):
        raise ValueError("Column mapping must name the source column for each field.")
    mapping = mapping if mapping is not None else {key: key for key in REQUIRED}
    mapping = {**mapping, **{key: mapping.get(key, key if key in columns else "") for key in FLAGS}}
    names = [mapping.get(key) for key in REQUIRED]
    if any(name not in columns for name in names) or len(set(names)) != 5:
        raise ValueError("Map distinct contact ID, satellite, start, end and priority columns.")
    optional_names = [mapping[key] for key in FLAGS if mapping[key]]
    if any(name not in columns for name in optional_names) or len(set(names + optional_names)) != len(
        names + optional_names
    ):
        raise ValueError("Map current-schedule and protected-contact flags to distinct existing columns.")
    baseline_provided = bool(mapping["baseline"])
    gap = scalar(turnaround_s, "Antenna turnaround")
    if not 0 <= gap <= 3600:
        raise ValueError("Antenna turnaround must be between 0 and 3,600 seconds.")
    contacts, seen = [], set()
    resources = {row["resource"] for row in rows} if "resource" in columns else set()
    if len(resources) > 1:
        raise ValueError("This planner serves one antenna. Split different resource values into separate files.")
    for row in rows:
        contact = {key: row[name] for key, name in mapping.items() if key in REQUIRED}
        identity = contact["contact_id"].strip()
        if not identity or identity in seen or len(identity) > 160 or not contact["satellite"].strip():
            raise ValueError("Every contact needs a unique, non-empty ID and a satellite name.")
        seen.add(identity)
        start, end = pd.Timestamp(contact["start"]), pd.Timestamp(contact["end"])
        if pd.isna(start) or pd.isna(end) or start.tzinfo is None or end.tzinfo is None:
            raise ValueError("Contact times need ISO 8601 timestamps with Z or an explicit UTC offset.")
        start, end = start.tz_convert("UTC"), end.tz_convert("UTC")
        if not 0 < (end - start).total_seconds() <= 86400:
            raise ValueError("Each contact must have positive duration of at most 24 hours.")
        priority = scalar(contact["priority"], "Priority")
        if not 0 < priority <= 1_000_000:
            raise ValueError("Priorities must be greater than zero and no larger than 1,000,000.")
        contacts.append(
            {
                "contact_id": identity,
                "satellite": contact["satellite"],
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z"),
                "priority": priority,
                "start_s": start.timestamp(),
                "end_s": end.timestamp(),
                "baseline": flag(row[mapping["baseline"]], "Current schedule", identity)
                if baseline_provided
                else False,
                "locked": flag(row[mapping["locked"]], "Protected contact", identity) if mapping["locked"] else False,
            }
        )
    if max(c["end_s"] for c in contacts) - min(c["start_s"] for c in contacts) > 31 * 86400:
        raise ValueError("Use a planning window of at most 31 days.")
    contacts.sort(key=lambda c: (c["end_s"], c["start_s"], c["contact_id"]))
    locked = sorted([c for c in contacts if c["locked"]], key=lambda c: c["start_s"])
    for a, b in zip(locked, locked[1:], strict=False):
        if conflicts(a, b, gap):
            raise ValueError(
                f"Protected contacts {a['contact_id']} and {b['contact_id']} conflict, including turnaround. "
                "Resolve the commitment or timing before planning. No protected contact was dropped."
            )
    eligible = [c for c in contacts if not c["locked"] and not any(conflicts(c, s, gap) for s in locked)]
    ends = [c["end_s"] for c in eligible]
    previous = [bisect_right(ends, c["start_s"] - gap, 0, i) for i, c in enumerate(eligible)]
    # Equal priority is broken by the smallest change to the supplied schedule.
    # |baseline XOR selected| = |baseline| - retained + added, so maximise retained - added.
    best = [(Decimal(0), 0)]
    take = []
    for i, contact in enumerate(eligible):
        prior = best[previous[i]]
        stability = (1 if contact["baseline"] else -1) if baseline_provided else 0
        include = (Decimal(str(contact["priority"])) + prior[0], stability + prior[1])
        take.append(include > best[i])
        best.append(max(include, best[i]))
    selected_ids = {c["contact_id"] for c in locked}
    i = len(eligible)
    while i:
        if take[i - 1]:
            selected_ids.add(eligible[i - 1]["contact_id"])
            i = previous[i - 1]
        else:
            i -= 1
    selected = [c for c in contacts if c["contact_id"] in selected_ids]
    first_come, last_end = list(locked), float("-inf")
    for contact in sorted(eligible, key=lambda c: (c["start_s"], c["end_s"], c["contact_id"])):
        if contact["start_s"] >= last_end + gap:
            first_come.append(contact)
            last_end = contact["end_s"]
    for contact in contacts:
        contact["selected"] = contact["contact_id"] in selected_ids
        contact["conflicts_with"] = (
            [] if contact["selected"] else [s["contact_id"] for s in selected if conflicts(contact, s, gap)]
        )
        contact["decision"] = (
            "Selected: protected commitment"
            if contact["locked"]
            else ("Selected" if contact["selected"] else "Excluded: overlaps a selected contact or its turnaround")
        )
        contact["change"] = (
            (
                ("retained" if contact["selected"] else "removed")
                if contact["baseline"]
                else ("added" if contact["selected"] else "not_selected")
            )
            if baseline_provided
            else ("selected" if contact["selected"] else "not_selected")
        )
    baseline = sorted([c for c in contacts if c["baseline"]], key=lambda c: c["start_s"])
    issues = []
    if baseline_provided:
        for a, b in zip(baseline, baseline[1:], strict=False):
            if conflicts(a, b, gap):
                issues.append(
                    f"Current contacts {a['contact_id']} and {b['contact_id']} conflict, including turnaround."
                )
        issues.extend(
            f"Protected contact {c['contact_id']} is absent from the current schedule."
            for c in locked
            if not c["baseline"]
        )
    total = priority_sum(selected)
    delta = (
        float(
            sum((Decimal(str(c["priority"])) for c in selected), Decimal(0))
            - sum((Decimal(str(c["priority"])) for c in baseline), Decimal(0))
        )
        if baseline_provided and not issues
        else None
    )
    comparison = {
        "provided": baseline_provided,
        "feasible": not issues if baseline_provided else None,
        "issues": issues,
        "status": "baseline_required"
        if not baseline_provided
        else ("repair_required" if issues else ("improved" if delta > 0 else "unchanged")),
        "baseline_count": len(baseline) if baseline_provided else None,
        "baseline_priority": priority_sum(baseline) if baseline_provided else None,
        "priority_delta": delta,
        "baseline_minutes": sum((c["end_s"] - c["start_s"]) / 60 for c in baseline) if baseline_provided else None,
        "proposed_minutes": sum((c["end_s"] - c["start_s"]) / 60 for c in selected),
        "added_ids": [c["contact_id"] for c in contacts if c["change"] == "added"],
        "removed_ids": [c["contact_id"] for c in contacts if c["change"] == "removed"],
        "retained_ids": [c["contact_id"] for c in contacts if c["change"] == "retained"],
    }
    return {
        "kind": "plan",
        "contacts": contacts,
        "selected_count": len(selected),
        "priority_total": total,
        "first_come_priority": priority_sum(first_come),
        "protected_count": len(locked),
        "comparison": comparison,
        "turnaround_s": gap,
        "resource": next(iter(resources), "One declared antenna"),
        "limitations": [
            "Candidate contacts are assumed feasible. This planner does not establish visibility, "
            "radio-link availability or spacecraft readiness.",
            "Maximises the sum of user-assigned priority across whole contacts for one antenna, "
            "with a fixed turnaround. "
            "It cannot divide passes or represent angle-dependent slews, multi-antenna networks, deadlines, "
            "power or data-volume constraints.",
            "Priority is a user-defined preference, not a calibrated risk or financial value. "
            "Equal-priority solutions minimise additions and removals from the supplied current schedule; "
            "remaining ties retain the deterministic earlier-finishing solution. No commands are sent.",
            "Protected contacts must be retained. A current schedule is compared only within the supplied "
            "candidate set, priorities and fixed turnaround. Its flags are the user's declaration, not a "
            "verified booking. An infeasible current schedule receives no improvement claim. "
            "Contact minutes do not establish data delivered, revenue or link success.",
        ],
    }
