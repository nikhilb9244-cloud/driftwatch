"""Export the workspace's examples. Every one of them is measured or published data.

There is no synthetic branch in this file and there must not be one. The workspace previously
shipped constructed inputs -- an OEM with a designed displacement, CDMs carrying illustrative
probabilities, receiver lock times placed 35 seconds after the predicted acquisition, and a set of
invented contact requests. They were removed on 2026-09-07 because a demonstration built from
numbers we chose cannot show a reader whether the tool works, and a reader cannot tell by looking
which parts of a screen came from a measurement and which from a fixture.

What is exported here, and where each piece comes from:

* **The Swarm benchmark** (``benchmark.json``) -- the measured result of comparing public element
  sets for Swarm A, B and C against ESA's reduced-dynamic precise science orbits, with the sources
  it records inside it. Copied verbatim from ``data/validation/swarm_benchmark.json``.
* **ESA reference tracks** (``benchmark-tracks.json``) -- 100 minutes of ESA's reconstructed orbit
  for each satellite on one day of each benchmark window, for drawing on the globe.
* **The orbit comparison** -- ESA's reconstructed orbit for **Swarm A** (NORAD 39452) as the
  reference, against two genuine Space-Track element sets for the same satellite issued six days
  apart. The difference between them is the real drift with element-set age that the horizon
  result measures, through the May 2024 storm. ESA's own thruster record supplies the manoeuvre
  intervals, so a burn is excluded because ESA recorded it and not because the residual looked
  wrong.
* **The ground-contact experiment** -- two genuine Space-Track element sets for the **ISS**
  (NORAD 25544) over the published coordinates of **IGS station HRAO00ZAF** at Hartebeesthoek,
  South Africa.

Two tools get no example, because no real input for them exists in this repository: the
conjunction-message (CDM) tool and the contact planner. They say so on screen.

Run from the repository root, after ``uv sync``, with the offline caches present:

    uv run --offline python scripts/export_workspace_examples.py
"""

from __future__ import annotations

import glob
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch.local import no_network
from driftwatch.orbit.frames import itrs_to_geodetic
from driftwatch.storm.precise import load_precise_orbit, load_thruster_record
from driftwatch.workbench import analyse

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "web" / "public" / "examples"

# The IGS station list gives the surveyed position of every station in the network. HRAO00ZAF is
# the GNSS marker at the Hartebeesthoek Radio Astronomy Observatory. It is a real surveyed point
# with a published position, which is what the contact geometry needs; it is not a claim about
# which antenna at the site is used for spacecraft contacts, or that it is available to anyone.
STATION = {
    "id": "HRAO00ZAF",
    "site": "Hartebeesthoek Radio Astronomy Observatory, South Africa",
    "latitude": -25.890,
    "longitude": 27.687,
    "height_m": 1414.744,
    "source": "IGS station list, https://files.igs.org/pub/station/general/IGSNetwork.csv",
}

# Both examples sit in the benchmark's storm window, which is the case the project exists to
# measure: element sets issued before and during the May 2024 Gannon storm.
SWARM_A = 39452
SWARM_A_WINDOW = ("2024-05-13T00:00:00Z", "2024-05-14T00:00:00Z")
SWARM_A_RECENT = "2024-05-12T20:57:24.865344Z"
SWARM_A_OLDER = "2024-05-06T14:26:27.721536Z"

ISS = 25544
ISS_WINDOW_START = "2024-05-11T00:00:00Z"
ISS_WINDOW_HOURS = 24
ISS_RECENT = "2024-05-10T20:04:09.655968Z"
ISS_OLDER = "2024-05-04T05:00:00.714240Z"

GP_COLUMNS = [
    "norad_id",
    "name",
    "object_id",
    "epoch",
    "mean_motion",
    "eccentricity",
    "inclination_deg",
    "raan_deg",
    "arg_perigee_deg",
    "mean_anomaly_deg",
    "bstar",
    "mean_motion_dot",
    "mean_motion_ddot",
    "ephemeris_type",
    "classification",
    "element_set_no",
    "rev_at_epoch",
]


def history() -> pd.DataFrame:
    """Every element set in the local history store, which is Space-Track's ``gp_history``."""
    files = sorted(glob.glob(str(ROOT / "data" / "history" / "gph_*.parquet")))
    if not files:
        raise SystemExit("No history store. Run `driftwatch history` first; nothing is synthesised here.")
    frames = [pd.read_parquet(f, columns=GP_COLUMNS) for f in files]
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["norad_id", "epoch"])


def one_element_set(rows: pd.DataFrame, norad: int, epoch: str) -> dict[str, Any]:
    """The single real element set with exactly this epoch, as an OMM/GP JSON record.

    Selected by exact epoch rather than "nearest", so the file this writes is reproducible and a
    reader can find the same row in Space-Track's ``gp_history`` for themselves.
    """
    want = pd.Timestamp(epoch)
    match = rows[(rows.norad_id == norad) & (rows.epoch == want)]
    if len(match) != 1:
        raise SystemExit(f"Expected exactly one element set for {norad} at {epoch}; found {len(match)}.")
    r = match.iloc[0]
    return {
        "NORAD_CAT_ID": int(r.norad_id),
        "OBJECT_NAME": str(r["name"]),
        "OBJECT_ID": str(r.object_id),
        "EPOCH": pd.Timestamp(r.epoch).tz_convert("UTC").isoformat().replace("+00:00", ""),
        "MEAN_MOTION": float(r.mean_motion),
        "ECCENTRICITY": float(r.eccentricity),
        "INCLINATION": float(r.inclination_deg),
        "RA_OF_ASC_NODE": float(r.raan_deg),
        "ARG_OF_PERICENTER": float(r.arg_perigee_deg),
        "MEAN_ANOMALY": float(r.mean_anomaly_deg),
        "BSTAR": float(r.bstar),
        "MEAN_MOTION_DOT": float(r.mean_motion_dot),
        "MEAN_MOTION_DDOT": float(r.mean_motion_ddot),
        "EPHEMERIS_TYPE": int(r.ephemeris_type),
        "CLASSIFICATION_TYPE": str(r.classification),
        "ELEMENT_SET_NO": int(r.element_set_no),
        "REV_AT_EPOCH": int(r.rev_at_epoch),
    }


def esa_reference_oem(letter: str, norad: int, object_id: str, start: str, end: str) -> str:
    """ESA's reduced-dynamic precise orbit for one Swarm satellite, as a CCSDS OEM.

    Every state in the file is ESA's, interpolated onto a one-minute grid by the same reader the
    benchmark uses. The frame is ITRF because that is what ESA publishes; the loader has already
    converted the product's GPS epochs to UTC, which is the 18-second correction that would put
    the satellite 137 km along track if it were skipped.
    """
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    orbit = load_precise_orbit(
        letter, (lo - pd.Timedelta(days=1)).date(), (hi + pd.Timedelta(days=1)).date(), offline=True
    )
    times = pd.date_range(lo, hi, freq="60s")
    r, v, ok = orbit.states_itrs(times.to_numpy(dtype="datetime64[us]"))
    if not ok.all():
        raise SystemExit(f"ESA's cached orbit for Swarm {letter} has gaps over {start}..{end}; nothing is substituted.")
    lines = [
        "CCSDS_OEM_VERS = 2.0",
        f"COMMENT ESA Swarm {letter} reduced-dynamic precise science orbit (SW_OPER_SP3{letter}COM_2_).",
        "COMMENT Measured reconstructed orbit, not a prediction and not a fixture.",
        f"COMMENT Source files: {', '.join(orbit.files)}",
        "COMMENT GPS epochs in the source product converted to UTC by driftwatch.storm.precise.",
        f"CREATION_DATE = {pd.Timestamp.utcnow().isoformat(timespec='seconds').replace('+00:00', '')}",
        "ORIGINATOR = ESA (orbit); driftwatch (OEM packaging)",
        "META_START",
        f"OBJECT_NAME = SWARM {letter}",
        f"OBJECT_ID = {object_id}",
        "CENTER_NAME = EARTH",
        "REF_FRAME = ITRF",
        "TIME_SYSTEM = UTC",
        f"START_TIME = {lo.tz_localize(None).isoformat()}",
        f"STOP_TIME = {hi.tz_localize(None).isoformat()}",
        "META_STOP",
    ]
    for t, a, b in zip(times, r, v, strict=True):
        stamp = t.tz_localize(None).isoformat()
        lines.append(f"{stamp} " + " ".join(f"{x:.9f}" for x in [*a, *b]))
    _ = norad
    return "\n".join(lines) + "\n"


def esa_manoeuvres(letter: str, start: str, end: str) -> tuple[str, int]:
    """ESA's own record of when the orbit-control thrusters fired, as a start,end CSV."""
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    record = load_thruster_record(
        letter, (lo - pd.Timedelta(days=1)).date(), (hi + pd.Timedelta(days=1)).date(), offline=True
    )
    rows = [(a, b) for a, b in record.intervals if b >= lo and a <= hi]
    lines = ["start,end"] + [f"{a.isoformat()},{b.isoformat()}" for a, b in rows]
    return "\n".join(lines) + "\n", len(rows)


def write(name: str, text: str) -> dict[str, str]:
    (DEST / name).write_text(text, encoding="utf-8")
    return {"name": name, "text": text}


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    with no_network():
        # ---- the measured benchmark and ESA's tracks -------------------------------------
        tracks: dict[str, Any] = {
            "source": "ESA Swarm reduced-dynamic reconstructed orbits; GPS epochs converted to UTC",
            "windows": {},
        }
        for window, day in (
            ("quiet", date(2024, 4, 22)),
            ("storm", date(2024, 5, 10)),
            ("held-out", date(2024, 10, 10)),
        ):
            drawn = []
            for letter, colour in (("A", "#d4ef8d"), ("B", "#86bfff"), ("C", "#edb45e")):
                orbit = load_precise_orbit(letter, day, day, offline=True)
                times = pd.date_range(f"{day}T12:00:00", periods=101, freq="60s").to_numpy(dtype="datetime64[us]")
                r, _, ok = orbit.states_itrs(times)
                if not ok.all():
                    raise SystemExit(f"The cached {letter}/{day} track has missing states; no substitute generated.")
                lat, lon, height = itrs_to_geodetic(r)
                drawn.append(
                    {
                        "label": f"Swarm {letter}",
                        "colour": colour,
                        "points": np.column_stack((lat, lon, height)).tolist(),
                        "files": orbit.files,
                    }
                )
            tracks["windows"][window] = {"start": f"{day}T12:00:00Z", "end": f"{day}T13:40:00Z", "tracks": drawn}
        measured = ROOT / "data" / "validation" / "swarm_benchmark.json"
        tracks["benchmark_sha256"] = hashlib.sha256(measured.read_bytes()).hexdigest()
        (DEST / "benchmark.json").write_bytes(measured.read_bytes())
        (DEST / "benchmark-tracks.json").write_text(json.dumps(tracks, indent=2) + "\n", encoding="utf-8")

        rows = history()

        # ---- orbit comparison: ESA truth against two real element sets --------------------
        recent = one_element_set(rows, SWARM_A, SWARM_A_RECENT)
        older = one_element_set(rows, SWARM_A, SWARM_A_OLDER)
        object_id = recent["OBJECT_ID"]
        reference = write("swarm-a-esa-orbit.oem", esa_reference_oem("A", SWARM_A, object_id, *SWARM_A_WINDOW))
        prediction = write("swarm-a-elements-2024-05-12.json", json.dumps([recent], indent=2) + "\n")
        candidate = write("swarm-a-elements-2024-05-06.json", json.dumps([older], indent=2) + "\n")
        burns_text, n_burns = esa_manoeuvres("A", *SWARM_A_WINDOW)
        manoeuvres = write("swarm-a-esa-manoeuvres.csv", burns_text)
        orbit_request = {
            "reference": reference,
            "prediction": prediction,
            "candidate": candidate,
            "manoeuvres": manoeuvres,
            "reference_kind": "reconstructed",
            "norad": SWARM_A,
            "tolerance_km": 1,
        }

        # ---- ground contacts: a real object over a published station ----------------------
        iss_recent = one_element_set(rows, ISS, ISS_RECENT)
        iss_older = one_element_set(rows, ISS, ISS_OLDER)
        contacts_request = {
            "prediction": write("iss-elements-2024-05-10.json", json.dumps([iss_recent], indent=2) + "\n"),
            "candidate": write("iss-elements-2024-05-04.json", json.dumps([iss_older], indent=2) + "\n"),
            "latitude": STATION["latitude"],
            "longitude": STATION["longitude"],
            "height_m": STATION["height_m"],
            "mask_deg": 10,
            "start": ISS_WINDOW_START,
            "hours": ISS_WINDOW_HOURS,
            "norad": ISS,
        }

        provenance = {
            "orbit": {
                "object": f"Swarm A (NORAD {SWARM_A}, {object_id})",
                "reference": "ESA reduced-dynamic precise science orbit, SW_OPER_SP3ACOM_2_",
                "prediction": f"Space-Track gp_history element set, epoch {SWARM_A_RECENT}",
                "candidate": f"Space-Track gp_history element set, epoch {SWARM_A_OLDER}",
                "manoeuvres": (
                    f"ESA SW_OPER_SC_xDYN_1B thruster record; {n_burns} orbit-control interval(s) in this window"
                ),
                "window": f"{SWARM_A_WINDOW[0]} to {SWARM_A_WINDOW[1]}",
            },
            "contacts": {
                "object": f"ISS (NORAD {ISS}, {iss_recent['OBJECT_ID']})",
                "prediction": f"Space-Track gp_history element set, epoch {ISS_RECENT}",
                "candidate": f"Space-Track gp_history element set, epoch {ISS_OLDER}",
                "station": STATION,
                "window": f"{ISS_WINDOW_START} for {ISS_WINDOW_HOURS} h",
            },
        }

        for name, kind, request in (("orbit", "compare", orbit_request), ("contacts", "contacts", contacts_request)):
            result = analyse(kind, request)
            result["provenance"] = provenance[name]
            for suffix, body in (("request", request), ("result", result)):
                (DEST / f"{name}-{suffix}.json").write_text(
                    json.dumps(body, indent=2, allow_nan=False) + "\n", encoding="utf-8"
                )
            print(f"Exported the {name} example", flush=True)

        (DEST / "README.md").write_text(readme(provenance), encoding="utf-8")
    print("Exported the measured benchmark, ESA tracks and the two real-data examples.")


def readme(provenance: dict[str, Any]) -> str:
    orbit, contacts = provenance["orbit"], provenance["contacts"]
    station = contacts["station"]
    burns = (
        "ESA recorded no orbit-control thrust in this window, so nothing is excluded and the "
        "residual is the drift of the element set, not the trace of a burn."
        if orbit["manoeuvres"].split(";")[-1].strip().startswith("0 ")
        else "A manoeuvre is excluded because ESA's thruster record says one happened, not because "
        "a residual looked large."
    )
    return f"""# Workspace examples

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

## Orbit comparison — {orbit["object"]}

| File | What it is |
| --- | --- |
| `swarm-a-esa-orbit.oem` | {orbit["reference"]}, {orbit["window"]}, ITRF, UTC. The reference. |
| `swarm-a-elements-2024-05-12.json` | {orbit["prediction"]} |
| `swarm-a-elements-2024-05-06.json` | {orbit["candidate"]} |
| `swarm-a-esa-manoeuvres.csv` | {orbit["manoeuvres"]} |

The two element sets are for the same satellite and were issued six days apart. Compared against
the same measured ESA orbit, the difference between them is the real growth of along-track error
with element-set age, through the May 2024 storm — the quantity the horizon result reports.
{burns}

## Ground contacts — {contacts["object"]}

| File | What it is |
| --- | --- |
| `iss-elements-2024-05-10.json` | {contacts["prediction"]} |
| `iss-elements-2024-05-04.json` | {contacts["candidate"]} |

Station: **{station["id"]}**, {station["site"]}, latitude {station["latitude"]}°, longitude
{station["longitude"]}°, height {station["height_m"]} m. Source: {station["source"]}. That is the
surveyed GNSS marker at the site; it is not a statement about which antenna is used for spacecraft
contacts, or that the site is available to anyone.

The window is {contacts["window"]}. The second element set is six days older than the first, so the
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
"""


if __name__ == "__main__":
    main()
