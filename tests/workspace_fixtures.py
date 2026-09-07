"""Constructed inputs for the workspace tests, built here and never shipped.

Until 2026-09-07 these files were generated into ``web/public/examples/`` and offered to readers
as demonstrations: an OEM carrying a displacement we chose, CDMs carrying probabilities we chose,
receiver lock times placed a fixed 35 seconds after the predicted acquisition, and a week of
invented contact requests. A reader could not tell by looking which numbers on the screen were
measured and which were designed, so they were removed from the product. The shipped examples are
now measured or published data only; see ``scripts/export_workspace_examples.py``.

They belong *here*, though, and could not be replaced by real data without weakening the tests.
A designed displacement is what lets a test assert that the engine measures it: the candidate is
built at exactly 0.4 times the prediction's offset, so
``candidate_median_km == 0.4 * median_km`` is a statement about the arithmetic rather than about
the weather. Real element sets cannot do that, because nobody knows their true error to nine
significant figures.

Everything is built in memory. Nothing here writes to ``web/public/examples/``.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from driftwatch.orbit.propagator import propagate_satrecs, satrec_from_elements
from driftwatch.workbench import analyse

NORAD = 90001
OBJECT_ID = "2024-001A"
EPOCH = datetime(2024, 5, 10)

RECORD: dict[str, Any] = {
    "NORAD_CAT_ID": NORAD,
    "OBJECT_NAME": "SYNTHETIC-1",
    "OBJECT_ID": OBJECT_ID,
    "EPOCH": EPOCH.isoformat(),
    "MEAN_MOTION": 15.2,
    "ECCENTRICITY": 0.001,
    "INCLINATION": 87.4,
    "RA_OF_ASC_NODE": 25.0,
    "ARG_OF_PERICENTER": 6.0,
    "MEAN_ANOMALY": 12.0,
    "BSTAR": 1e-5,
    "MEAN_MOTION_DOT": 0.0,
    "MEAN_MOTION_DDOT": 0.0,
    "EPHEMERIS_TYPE": 0,
    "CLASSIFICATION_TYPE": "U",
    "ELEMENT_SET_NO": 1,
    "REV_AT_EPOCH": 1,
}


@lru_cache(maxsize=1)
def _built() -> tuple[dict[str, str], dict[str, dict]]:
    """The file texts and the four tool requests, built once per session."""
    sat = satrec_from_elements(NORAD, EPOCH, 15.2, 0.001, 87.4, 25.0, 6.0, 12.0, 1e-5)
    times = pd.date_range(EPOCH, periods=1561, freq="60s").to_numpy(dtype="datetime64[us]")
    states = propagate_satrecs([sat], np.array([NORAD]), times)
    r, v = states.r_teme[0], states.v_teme[0]
    along = v / np.linalg.norm(v, axis=1)[:, None]
    displacement = along * (0.3 + np.arange(len(times)) / 60 * 0.15)[:, None]

    texts: dict[str, str] = {"sets.json": json.dumps([RECORD], indent=2) + "\n"}

    trial_lines = ["trial_id,satellite,window,lead_h,baseline_km,candidate_km,sigma_km"]
    for window in ("quiet", "storm", "held-out"):
        for trial in range(1, 5):
            for lead in (24, 48, 72):
                baseline = trial * lead / 24 * (2 if window != "quiet" else 1)
                trial_lines.append(
                    f"{window}-{trial},SYNTHETIC-1,{window},{lead},{baseline},"
                    f"{baseline * (0.6 if window != 'quiet' else 1.2)},{baseline / 3}"
                )
    texts["model-trials.csv"] = "\n".join(trial_lines) + "\n"

    for name, factor in (("reference.oem", 0), ("prediction.oem", 1), ("candidate.oem", 0.4)):
        positions = r + displacement * factor
        velocities = v + np.gradient(displacement * factor, 60, axis=0)
        lines = [
            "CCSDS_OEM_VERS = 2.0",
            "COMMENT TEST FIXTURE. SGP4 with a displacement chosen by the test, not an observation.",
            "CREATION_DATE = 2024-05-10T00:00:00",
            "ORIGINATOR = DRIFTWATCH TEST FIXTURE",
            "META_START",
            "OBJECT_NAME = SYNTHETIC-1",
            f"OBJECT_ID = {OBJECT_ID}",
            "CENTER_NAME = EARTH",
            "REF_FRAME = TEME",
            "TIME_SYSTEM = UTC",
            "START_TIME = 2024-05-10T00:00:00",
            "STOP_TIME = 2024-05-11T02:00:00",
            "META_STOP",
        ]
        for t, a, b in zip(times, positions, velocities, strict=True):
            lines.append(f"{str(t)} " + " ".join(f"{x:.9f}" for x in [*a, *b]))
        texts[name] = "\n".join(lines) + "\n"

    for name, time, miss, pc in (
        ("first.cdm", "2024-05-10T15:00:00", 715, 4.8e-5),
        ("second.cdm", "2024-05-10T15:00:30", 850, 2.1e-5),
    ):
        lines = [
            "CCSDS_CDM_VERS = 1.0",
            "COMMENT TEST FIXTURE. The probabilities are values the test supplies, not a computed risk.",
            "CREATION_DATE = 2024-05-10T00:00:00",
            "ORIGINATOR = DRIFTWATCH TEST FIXTURE",
            f"MESSAGE_ID = {name}",
            f"TCA = {time}",
            f"MISS_DISTANCE = {miss} [m]",
            "RELATIVE_SPEED = 14000 [m/s]",
            f"COLLISION_PROBABILITY = {pc}",
            "COLLISION_PROBABILITY_METHOD = FIXTURE",
        ]
        for i in (1, 2):
            lines += [
                f"OBJECT = OBJECT{i}",
                f"OBJECT_DESIGNATOR = {90000 + i}",
                f"OBJECT_NAME = SYNTHETIC-{i}",
                "REF_FRAME = TEME",
                "CR_R = 100 [m**2]",
                "CT_R = 0 [m**2]",
                "CT_T = 10000 [m**2]",
                "CN_R = 0 [m**2]",
                "CN_T = 0 [m**2]",
                "CN_N = 100 [m**2]",
            ]
        texts[name] = "\n".join(lines) + "\n"

    texts["contact-requests.csv"] = (
        "contact_id,satellite,start,end,priority,resource,baseline,locked\n"
        "LONG-A,Fixture satellite A,2024-05-10T08:59:00Z,2024-05-10T09:20:00Z,10,Fixture antenna,true,false\n"
        "SHORT-B,Fixture satellite B,2024-05-10T09:00:00Z,2024-05-10T09:08:00Z,6,Fixture antenna,false,false\n"
        "SHORT-C,Fixture satellite C,2024-05-10T09:09:00Z,2024-05-10T09:18:00Z,6,Fixture antenna,false,false\n"
        "FOLLOW-D,Fixture satellite D,2024-05-10T09:21:00Z,2024-05-10T09:30:00Z,4,Fixture antenna,true,true\n"
        "OVERLAP-E,Fixture satellite E,2024-05-10T09:17:00Z,2024-05-10T09:27:00Z,3,Fixture antenna,false,false\n"
    )

    def file(name: str) -> dict[str, str]:
        return {"name": name, "text": texts[name]}

    orbit = {
        "reference": file("reference.oem"),
        "prediction": file("prediction.oem"),
        "candidate": file("candidate.oem"),
        "reference_kind": "prediction",
        "norad": NORAD,
        "tolerance_km": 1,
    }
    contacts = {
        "prediction": file("sets.json"),
        "candidate": file("prediction.oem"),
        "latitude": -33.93,
        "longitude": 18.64,
        "height_m": 80,
        "mask_deg": 10,
        "start": "2024-05-10T00:00:00Z",
        "hours": 24,
        "norad": NORAD,
    }
    # The lock times are placed a fixed 35 s after the predicted acquisition so the matcher has
    # something with a known answer to match. That is exactly why this is a fixture and not a
    # demonstration: it cannot show anyone that receiver reconciliation works in the field.
    first = analyse("contacts", contacts)
    locks = [(pd.Timestamp(p["aos"]) + pd.Timedelta(seconds=35)).isoformat() for p in first["passes"][:2]]
    texts["acquisitions.csv"] = "lock_time\n" + "\n".join(locks) + "\n"
    contacts = {**contacts, "log": file("acquisitions.csv")}

    requests = {
        "orbit": orbit,
        "contacts": contacts,
        "cdms": {"first": file("first.cdm"), "second": file("second.cdm"), "tolerance_s": 600},
        "plan": {"contacts": file("contact-requests.csv"), "turnaround_s": 60},
    }
    return texts, requests


def request(name: str) -> dict:
    """A fresh, deeply-copied request body for one tool: ``orbit``, ``contacts``, ``cdms``, ``plan``."""
    return json.loads(json.dumps(_built()[1][name]))


def text(name: str) -> str:
    """The text of one constructed input file, e.g. ``reference.oem``."""
    return _built()[0][name]
