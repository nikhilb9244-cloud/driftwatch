# Scheduled-workflow audit — 2026-09-08

The daily pipeline ran on every audited day, but it did not start at its stated time. Supplemental collection also ran successfully, but its observed starts did not meet the three-hour cadence. Neither workflow had a 36-hour gap at the audit cutoff, 20:15:45 UTC on 8 September. The [retained run metadata](assets/maintenance-2026-09-08.json) records every scheduled and manual run returned since 5 September, the workflow hashes and the interval accounting.

The historical state-of-play snapshot was read from its archived copy. It predates these successful scheduled runs; its statement that no pipeline run had completed is no longer current.

## Daily pipeline

The configured daily start is 06:20 UTC. All four scheduled events were delivered; three succeeded and one failed. Manual dispatches are listed separately in the evidence and do not count as scheduled starts.

| Date | Actual scheduled start UTC | Delay | Outcome | Run |
| --- | --- | --- | --- | --- |
| 2026-09-05 | 10:35:35 | 4 h 15 m 35 s | Failed during screening | 33961078980 |
| 2026-09-06 | 10:56:34 | 4 h 36 m 34 s | Succeeded | 34028810113 |
| 2026-09-07 | 12:33:03 | 6 h 13 m 03 s | Succeeded | 34122470546 |
| 2026-09-08 | 11:19:05 | 4 h 59 m 05 s | Succeeded | 34220049794 |

The 5 September failure occurred in “Screen, fit the covariance and score quiet”. Two fetched copies of the same SpaceX provider version tied on creation time, so duplicate epochs reached the interpolator, which rejected the time grid as not strictly increasing. The retained logs identify that failure; commit `8c216fb` repaired version selection and grid handling that day. The later three scheduled runs succeeded. This is an execution failure, distinct from the delayed scheduling.

## Supplemental collection

The configured cadence is every three hours at minute zero. There are 21 successful scheduled starts across 31 expected intervals from 5 September 00:00 UTC through the audit cutoff. Every interval without a recorded start is listed below. The last interval is partially elapsed, but already contains a successful start.

| Date | Interval without a recorded start, UTC | Cause established by available records |
| --- | --- | --- |
| 2026-09-05 | 03:00–06:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-05 | 09:00–12:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-06 | 03:00–06:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-06 | 09:00–12:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-07 | 03:00–06:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-07 | 09:00–12:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-07 | 15:00–18:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-08 | 03:00–06:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-08 | 09:00–12:00 | No execution record; delayed versus dropped trigger is unknown |
| 2026-09-08 | 15:00–18:00 | No execution record; delayed versus dropped trigger is unknown |

These are ten cadence gaps, not ten individually identified lost cron instances. GitHub's run API provides the run creation and start times but does not bind each delayed event to its originally intended occurrence. Both workflows are active and their schedule definitions were present throughout the audited period. Scheduler delay or dropping is consistent with the observations and with [GitHub's documented scheduling limits](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows), but the service-side cause of each gap is not exposed by these records.

## Installed watchdog

[Scheduled workflow health](../.github/workflows/workflow-health.yml) runs every six hours at minute 17, after either monitored workflow completes, and on manual dispatch. It fails with an Actions error annotation and a retained report when either workflow is inactive, has no scheduled start within 36 hours, has no successful scheduled start within 36 hours, or its latest completed scheduled run failed. A queued event or manual dispatch cannot satisfy the schedule check. Unknown, naive or future start times fail explicitly. API errors also fail the job.

The health check uses read-only Actions permissions and does not fetch orbital data or deploy anything. Tests exercise stale schedules masked by manual runs, queued events, failures, an active run with a stale predecessor, the exact age boundary and invalid timestamps. Because the watchdog itself runs on Actions, it cannot independently detect an outage that prevents all Actions jobs from starting; its next execution will report the stale state.
