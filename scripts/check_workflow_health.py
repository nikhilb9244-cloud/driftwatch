"""Fail when either scheduled collection workflow has gone stale."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

WORKFLOWS = ("pipeline.yml", "supplemental.yml")


def utc_time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp is unknown")
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("timestamp has no time zone")
    return instant.astimezone(UTC)


def assess(workflow, runs, *, now, max_age_hours=36):
    """Manual runs and queued events cannot conceal a stopped schedule."""
    cutoff = now - timedelta(hours=max_age_hours)
    problems = []
    if workflow.get("state") != "active":
        problems.append("workflow is not active")
    started = []
    for run in runs:
        if run.get("event") != "schedule" or run.get("status") not in {"in_progress", "completed"}:
            continue
        try:
            instant = utc_time(run["run_started_at"])
        except (KeyError, TypeError, ValueError):
            problems.append(f"scheduled run {run.get('id', 'unknown')} has no valid start time")
            continue
        if instant > now:
            problems.append(f"scheduled run {run.get('id', 'unknown')} starts in the future")
            continue
        started.append((instant, run))
    started.sort(key=lambda item: item[0], reverse=True)
    recent = [(instant, run) for instant, run in started if instant >= cutoff]
    if not recent:
        problems.append(f"no scheduled run started in the last {max_age_hours:g} hours")
    successful = [(instant, run) for instant, run in started if run.get("conclusion") == "success"]
    if not successful or successful[0][0] < cutoff:
        problems.append(f"no successful scheduled run started in the last {max_age_hours:g} hours")
    completed = [run for _, run in started if run.get("status") == "completed"]
    if completed and completed[0].get("conclusion") != "success":
        problems.append(
            f"latest completed scheduled run {completed[0]['id']} concluded {completed[0].get('conclusion')}"
        )
    latest = started[0] if started else None
    return {
        "workflow": workflow["path"].rsplit("/", 1)[-1],
        "healthy": not problems,
        "last_scheduled_run_id": latest[1]["id"] if latest else None,
        "last_scheduled_start": latest[0].isoformat() if latest else None,
        "last_successful_scheduled_run_id": successful[0][1]["id"] if successful else None,
        "problems": problems,
    }


def api(relative, *, repository, token):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{relative}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "driftwatch-workflow-health",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def annotation(text):
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--max-age-hours", type=float, default=36)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not args.repository or not token or args.max_age_hours <= 0:
        parser.error("repository, GITHUB_TOKEN (or GH_TOKEN), and a positive maximum age are required")
    now = datetime.now(UTC)
    results = []
    for name in WORKFLOWS:
        try:
            workflow = api(f"actions/workflows/{name}", repository=args.repository, token=token)
            runs = api(
                f"actions/workflows/{name}/runs?event=schedule&per_page=100", repository=args.repository, token=token
            )
            result = assess(workflow, runs["workflow_runs"], now=now, max_age_hours=args.max_age_hours)
        except Exception as error:
            # Do not print response bodies or credentials while reporting an API failure.
            result = {"workflow": name, "healthy": False, "problems": [f"health query failed: {type(error).__name__}"]}
        results.append(result)
        for problem in result["problems"]:
            print(f"::error title=Scheduled workflow health::{annotation(name + ': ' + problem)}")
    record = {"checked_at": now.isoformat(), "maximum_age_hours": args.max_age_hours, "workflows": results}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    summary = [
        "## Scheduled workflow health",
        "",
        f"Checked at {now.isoformat()}; maximum age {args.max_age_hours:g} h.",
        "",
    ]
    for result in results:
        summary.append(f"- {result['workflow']}: {'PASS' if result['healthy'] else 'FAIL'}")
        summary.extend(f"  - {problem}" for problem in result["problems"])
        if result.get("last_scheduled_start"):
            summary.append(f"  - Last scheduled start: {result['last_scheduled_start']}")
    text = "\n".join(summary) + "\n"
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(text)
    return int(any(not result["healthy"] for result in results))


if __name__ == "__main__":
    sys.exit(main())
