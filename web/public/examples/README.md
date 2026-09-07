# Workspace examples

Every file here is measured or published data. Nothing in this directory is constructed, and
`scripts/export_workspace_examples.py` has no synthetic branch. Rebuild them with:

```
uv run --offline python scripts/export_workspace_examples.py
```

## The Swarm benchmark

`benchmark.json` is the measured comparison of public element sets for Swarm A, B and C against
ESA's reduced-dynamic precise science orbits, over a quiet window, the May 2024 storm and a
held-out October window. It carries its own `sources` block. `benchmark-tracks.json` holds 100
minutes of ESA's reconstructed orbit for each satellite on one day of each window, for drawing.

## Orbit comparison — Swarm A (NORAD 39452, 2013-067B)

| File | What it is |
| --- | --- |
| `swarm-a-esa-orbit.oem` | ESA reduced-dynamic precise science orbit, SW_OPER_SP3ACOM_2_, 2024-05-13T00:00:00Z to 2024-05-14T00:00:00Z, ITRF, UTC. The reference. |
| `swarm-a-elements-2024-05-12.json` | Space-Track gp_history element set, epoch 2024-05-12T20:57:24.865344Z |
| `swarm-a-elements-2024-05-06.json` | Space-Track gp_history element set, epoch 2024-05-06T14:26:27.721536Z |
| `swarm-a-esa-manoeuvres.csv` | ESA SW_OPER_SC_xDYN_1B thruster record; 0 orbit-control interval(s) in this window |

The two element sets are for the same satellite and were issued six days apart. Compared against
the same measured ESA orbit, the difference between them is the real growth of along-track error
with element-set age, through the May 2024 storm — the quantity the horizon result reports.
ESA recorded no orbit-control thrust in this window, so nothing is excluded and the residual is the drift of the element set, not the trace of a burn.

## Ground contacts — ISS (NORAD 25544, 1998-067A)

| File | What it is |
| --- | --- |
| `iss-elements-2024-05-10.json` | Space-Track gp_history element set, epoch 2024-05-10T20:04:09.655968Z |
| `iss-elements-2024-05-04.json` | Space-Track gp_history element set, epoch 2024-05-04T05:00:00.714240Z |

Station: **HRAO00ZAF**, Hartebeesthoek Radio Astronomy Observatory, South Africa, latitude -25.89°, longitude
27.687°, height 1414.744 m. Source: IGS station list, https://files.igs.org/pub/station/general/IGSNetwork.csv. That is the
surveyed GNSS marker at the site; it is not a statement about which antenna is used for spacecraft
contacts, or that the site is available to anyone.

The window is 2024-05-11T00:00:00Z for 24 h. The second element set is six days older than the first, so the
comparison shows whether refreshing the orbit moves the predicted acquisition times.

**No receiver log is shipped.** The tool accepts one — a CSV with a `lock_time` column — but no
real receiver log exists in this repository, and the previous example's lock times were placed a
fixed 35 seconds after the predicted acquisition, which made the matcher look right by
construction.

## What has no example

The conjunction-message (CDM) tool and the contact planner ship no example, because no real input
for either exists here. Each says on screen what file it needs and that it has not been exercised
on real data. An invented CDM probability or an invented request week would demonstrate the
software running, not the software working.

_Last updated 7 September 2026._
