"""Viewer bundle: what the browser needs to draw the catalogue and move it in time.

The viewer runs SGP4 itself (satellite.js, a port of the same reference code the Python
side uses) because a trajectory table for 30,000 objects over 48 hours would be about a
gigabyte. So the bundle carries the mean elements, not positions, plus the Python
reference state at one instant so the two implementations can be checked against each
other at run time.

Files written into ``web/public/data/``:

``manifest.json``
    Reference time, counts, file list, legend for category and band codes.
``objects.json``
    Columnar metadata (name, category code, band code, apogee, perigee, period, SGP4
    error at the reference time). Column-oriented JSON compresses far better than an
    array of objects.
``elements.bin``
    Little-endian float64, ``ELEMENTS_PER_OBJECT`` values per object in the order of
    :data:`ELEMENT_FIELDS`. Enough to initialise SGP4 in the browser.
``reference.bin``
    Little-endian float32, six values per object: TEME position (km) and velocity
    (km/s) at the reference time as computed by the Python sgp4 library. NaN where SGP4
    reported an error.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from driftwatch import __version__, config
from driftwatch.catalogue.classify import ALTITUDE_BANDS, CATEGORIES
from driftwatch.orbit.propagator import PropagatedState
from driftwatch.orbit.time import datetime64_to_datetime, unix_microseconds

log = logging.getLogger(__name__)

ELEMENT_FIELDS: tuple[str, ...] = (
    "norad_id",
    "epoch_unix_ms",
    "mean_motion",
    "eccentricity",
    "inclination_deg",
    "raan_deg",
    "arg_perigee_deg",
    "mean_anomaly_deg",
    "bstar",
    "mean_motion_dot",
    "mean_motion_ddot",
)
ELEMENTS_PER_OBJECT = len(ELEMENT_FIELDS)
REFERENCE_PER_OBJECT = 6
BUNDLE_VERSION = 1


def _epoch_unix_ms(epochs: pd.Series) -> np.ndarray:
    utc = pd.to_datetime(epochs, utc=True)
    return np.array([unix_microseconds(t) for t in utc.dt.to_pydatetime()], dtype=np.float64) / 1000.0


def elements_array(snapshot: pd.DataFrame) -> np.ndarray:
    """``(n, ELEMENTS_PER_OBJECT)`` float64 array in :data:`ELEMENT_FIELDS` order."""
    columns = [
        snapshot["norad_id"].to_numpy(dtype=np.float64),
        _epoch_unix_ms(snapshot["epoch"]),
        snapshot["mean_motion"].to_numpy(dtype=np.float64),
        snapshot["eccentricity"].to_numpy(dtype=np.float64),
        snapshot["inclination_deg"].to_numpy(dtype=np.float64),
        snapshot["raan_deg"].to_numpy(dtype=np.float64),
        snapshot["arg_perigee_deg"].to_numpy(dtype=np.float64),
        snapshot["mean_anomaly_deg"].to_numpy(dtype=np.float64),
        snapshot["bstar"].to_numpy(dtype=np.float64),
        snapshot["mean_motion_dot"].to_numpy(dtype=np.float64),
        snapshot["mean_motion_ddot"].to_numpy(dtype=np.float64),
    ]
    return np.column_stack(columns)


def _codes(values: pd.Series, legend: tuple[str, ...]) -> list[int]:
    lookup = {name: i for i, name in enumerate(legend)}
    return [lookup.get(v, len(legend) - 1) for v in values.astype(str)]


def _round_list(values: np.ndarray, ndigits: int) -> list[float | None]:
    out: list[float | None] = []
    for v in np.asarray(values, dtype=float):
        out.append(None if not np.isfinite(v) else round(float(v), ndigits))
    return out


def export_viewer_bundle(
    snapshot: pd.DataFrame,
    state: PropagatedState,
    *,
    out_dir: Path = config.VIEWER_DATA_DIR,
    snapshot_name: str = "",
    window_hours: float = 48.0,
) -> dict[str, Any]:
    """Write the viewer bundle for ``snapshot`` with ``state`` as the reference instant.

    ``state`` must hold exactly one time and be row-aligned with ``snapshot``.
    Returns the manifest dictionary.
    """
    if not state.single:
        raise ValueError("export expects a state propagated to a single time")
    if len(snapshot) != state.r_teme.shape[0]:
        raise ValueError("snapshot and state have different lengths")
    if not np.array_equal(snapshot["norad_id"].to_numpy(), state.norad_id):
        raise ValueError("snapshot and state are not row-aligned")

    out_dir.mkdir(parents=True, exist_ok=True)
    reference_time = datetime64_to_datetime(state.times[0])
    r, v, error = state.at_index(0)
    n = len(snapshot)

    elements = elements_array(snapshot).astype("<f8")
    (out_dir / "elements.bin").write_bytes(elements.tobytes(order="C"))

    reference = np.hstack([r, v]).astype("<f4")
    (out_dir / "reference.bin").write_bytes(reference.tobytes(order="C"))

    epoch_age_days = (
        pd.Timestamp(reference_time) - pd.to_datetime(snapshot["epoch"], utc=True)
    ).dt.total_seconds().to_numpy() / 86400.0

    objects = {
        "norad_id": [int(x) for x in snapshot["norad_id"]],
        "name": [str(x) for x in snapshot["name"]],
        "category": _codes(snapshot["category"], CATEGORIES),
        "band": _codes(snapshot["altitude_band"], ALTITUDE_BANDS),
        "object_type": [str(x) for x in snapshot["object_type"].fillna("UNK")],
        "perigee_km": _round_list(snapshot["perigee_km"].to_numpy(), 1),
        "apogee_km": _round_list(snapshot["apogee_km"].to_numpy(), 1),
        "period_min": _round_list(snapshot["period_min"].to_numpy(), 2),
        "inclination_deg": _round_list(snapshot["inclination_deg"].to_numpy(), 2),
        "epoch_age_days": _round_list(epoch_age_days, 2),
        "sgp4_error": [int(x) for x in error],
    }
    (out_dir / "objects.json").write_text(json.dumps(objects, separators=(",", ":")), encoding="utf-8")

    manifest = {
        "bundle_version": BUNDLE_VERSION,
        "generator": f"driftwatch {__version__}",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "snapshot": snapshot_name,
        "reference_time": reference_time.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "window_hours": window_hours,
        "n_objects": n,
        "n_sgp4_errors": int((error != 0).sum()),
        "categories": list(CATEGORIES),
        "bands": list(ALTITUDE_BANDS),
        "files": {
            "objects": "objects.json",
            "elements": {
                "path": "elements.bin",
                "dtype": "float64le",
                "fields": list(ELEMENT_FIELDS),
                "per_object": ELEMENTS_PER_OBJECT,
            },
            "reference": {
                "path": "reference.bin",
                "dtype": "float32le",
                "fields": ["x_teme_km", "y_teme_km", "z_teme_km", "vx_teme_kms", "vy_teme_kms", "vz_teme_kms"],
                "per_object": REFERENCE_PER_OBJECT,
            },
        },
        "notes": [
            "Elements are mean elements (SGP4/OMM); positions are only meaningful through SGP4.",
            "Reference state is the Python sgp4 library output in TEME at reference_time.",
            "Public catalogue accuracy is of order hundreds of metres to kilometres; see docs.",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    sizes = {
        p.name: p.stat().st_size
        for p in (out_dir / "elements.bin", out_dir / "reference.bin", out_dir / "objects.json")
    }
    log.info("Viewer bundle written to %s (%s)", out_dir, ", ".join(f"{k} {v / 1e6:.1f} MB" for k, v in sizes.items()))
    return manifest
