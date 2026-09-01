"""Rule-based classification of catalogue objects.

Two labels are attached to every object:

``category``
    What kind of thing it is, for colouring and filtering. Derived from the SATCAT
    object type, overridden by group membership and by well-known name prefixes. The
    name rules are a heuristic: operators name their satellites consistently, but there
    is no guarantee, so treat the constellation labels as "probably".

``altitude_band``
    Where it lives, from mean-element apogee and perigee. Mean elements are not
    osculating ones, so the boundaries are soft by a few kilometres.

Both labels describe; neither selects. Conjunction screening chooses its candidates from
apogee and perigee alone, so an object labelled ``unknown`` (no SATCAT type, typically an
analyst object not yet correlated to a launch) or ``other`` (an orbit outside the four
bands) is screened like any other. The labels colour the viewer, group the report and
pick the pooled covariance fallback.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

CATEGORIES: tuple[str, ...] = (
    "station",
    "starlink",
    "oneweb",
    "constellation",
    "payload",
    "rocket_body",
    "debris",
    "unknown",
)

ALTITUDE_BANDS: tuple[str, ...] = ("leo", "meo", "geo", "heo", "other")

# Name prefixes for other large constellations. Checked after Starlink and OneWeb.
CONSTELLATION_PREFIXES: tuple[str, ...] = (
    "KUIPER",
    "AMAZON LEO",
    "QIANFAN",
    "HULIANWANG",
    "GUOWANG",
    "IRIDIUM",
    "GLOBALSTAR",
    "ORBCOMM",
    "FLOCK",
    "LEMUR",
    "SPACEBEE",
    "LIGHTSPEED",
)

GEO_ALTITUDE_KM = 35_786.0
GEO_TOLERANCE_KM = 200.0
LEO_CEILING_KM = 2_000.0
HEO_ECCENTRICITY = 0.25


def categorise(name: str, object_type: str | None, groups: Iterable[str]) -> str:
    """Return the category for one object.

    Order matters: debris and rocket bodies are identified first from SATCAT because
    fragments inherit their parent's name (``IRIDIUM 33 DEB``); then the space stations
    group; then constellation name prefixes; then anything SATCAT calls a payload.
    """
    upper = (name or "").upper().strip()
    otype = (object_type or "UNK").upper()
    group_set = set(groups)
    if otype == "DEB":
        return "debris"
    if otype == "R/B":
        return "rocket_body"
    if "stations" in group_set:
        return "station"
    if upper.startswith("STARLINK") or "starlink" in group_set:
        return "starlink"
    if upper.startswith("ONEWEB") or "oneweb" in group_set:
        return "oneweb"
    if upper.startswith(CONSTELLATION_PREFIXES):
        return "constellation"
    if otype == "PAY":
        return "payload"
    return "unknown"


def altitude_band(perigee_km: float, apogee_km: float, eccentricity: float) -> str:
    """Return the altitude band for one object from mean-element apogee and perigee."""
    if np.isnan(perigee_km) or np.isnan(apogee_km):
        return "other"
    if abs(perigee_km - GEO_ALTITUDE_KM) <= GEO_TOLERANCE_KM and abs(apogee_km - GEO_ALTITUDE_KM) <= GEO_TOLERANCE_KM:
        return "geo"
    if eccentricity > HEO_ECCENTRICITY:
        return "heo"
    if apogee_km < LEO_CEILING_KM:
        return "leo"
    if perigee_km >= LEO_CEILING_KM and apogee_km < GEO_ALTITUDE_KM - GEO_TOLERANCE_KM:
        return "meo"
    return "other"


def categorise_frame(df: pd.DataFrame) -> pd.Series:
    """Vectorised :func:`categorise` over a frame with ``name``, ``object_type``, ``groups``."""
    return pd.Series(
        [categorise(n, t, g) for n, t, g in zip(df["name"], df["object_type"], df["groups"], strict=True)],
        index=df.index,
        dtype="string",
    )


def altitude_bands(perigee_km: np.ndarray, apogee_km: np.ndarray, eccentricity: np.ndarray) -> np.ndarray:
    """Vectorised :func:`altitude_band`."""
    perigee_km = np.asarray(perigee_km, dtype=float)
    apogee_km = np.asarray(apogee_km, dtype=float)
    eccentricity = np.asarray(eccentricity, dtype=float)
    out = np.full(perigee_km.shape, "other", dtype=object)
    valid = ~(np.isnan(perigee_km) | np.isnan(apogee_km))
    geo = (
        valid
        & (np.abs(perigee_km - GEO_ALTITUDE_KM) <= GEO_TOLERANCE_KM)
        & (np.abs(apogee_km - GEO_ALTITUDE_KM) <= GEO_TOLERANCE_KM)
    )
    heo = valid & ~geo & (eccentricity > HEO_ECCENTRICITY)
    leo = valid & ~geo & ~heo & (apogee_km < LEO_CEILING_KM)
    meo = valid & ~geo & ~heo & ~leo & (perigee_km >= LEO_CEILING_KM) & (apogee_km < GEO_ALTITUDE_KM - GEO_TOLERANCE_KM)
    out[geo] = "geo"
    out[heo] = "heo"
    out[leo] = "leo"
    out[meo] = "meo"
    return out
