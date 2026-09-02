"""Sun imagery from the Helioviewer Project, for the Step 5 replay.

A storm has a cause, and the cause is visible. The replay timeline needs a picture of the Sun
beside the Kp bar so that the coronal hole or the active region that produced the disturbance
is on screen with its consequence. This module fetches a few frames a day, not a movie: the
point is to see the source rotate across the disc over the storm, and four frames a day does
that in a few megabytes.

The channel is SDO/AIA 193 A, which shows the million-degree corona: coronal holes appear as
dark regions and active regions as bright ones, so both storm drivers read at a glance.
Helioviewer's ``takeScreenshot`` renders it to a PNG at a requested scale, which is what a
browser wants; the alternative, the raw JPEG 2000 science data, would need a decoder in the
viewer for no gain.

Every frame is cached by its **requested** time and the frame's own time is recorded beside
it, because Helioviewer returns the nearest image it has and that can be minutes or, during a
data gap, hours away. A replay that silently showed a picture from the day before would be
worse than showing none.

Terms: the API is public and needs no account. The Helioviewer documentation asks for credit
rather than imposing a licence; ``config.HELIOVIEWER_CITATION`` carries it, and the images are
NASA/SDO products, which are not subject to copyright.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from driftwatch import config
from driftwatch.catalogue.celestrak import make_client
from driftwatch.orbit.time import stamp

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SunFrame:
    """One cached frame: what was asked for, what came back, and where it is."""

    requested: datetime
    actual: datetime | None
    path: Path
    source_id: int | None
    from_cache: bool

    @property
    def lag(self) -> timedelta | None:
        """How far the returned image is from the time asked for."""
        return None if self.actual is None else abs(self.actual - self.requested)


def frame_times(start: datetime, end: datetime, *, per_day: int = config.HELIOVIEWER_FRAMES_PER_DAY) -> list[datetime]:
    """Evenly spaced times over ``[start, end]``, ``per_day`` of them a day.

    Spaced from the window's start rather than snapped to the hour, so a replay of a
    half-day window still gets its frames.
    """
    if per_day <= 0 or end <= start:
        return []
    step = timedelta(days=1) / per_day
    out, t = [], start
    while t <= end:
        out.append(t)
        t = t + step
    return out


def image_path(t: datetime, cache_dir: Path = config.CACHE_DIR) -> Path:
    return cache_dir / "helioviewer" / f"aia193_{stamp(t)}.png"


def _meta_path(path: Path) -> Path:
    return path.with_suffix(".meta.json")


def closest_image(
    t: datetime, *, source_id: int = 14, client: httpx.Client | None = None, timeout: float = 60.0
) -> dict[str, Any] | None:
    """Helioviewer's metadata for the image nearest ``t``: its actual time, id and scale.

    ``source_id`` 14 is SDO/AIA 193. Returns None when Helioviewer has nothing, which happens
    for times before an instrument existed and during long data gaps.
    """
    own = client is None
    client = client or make_client()
    try:
        response = client.get(
            f"{config.HELIOVIEWER_BASE_URL}/getClosestImage/",
            params={"date": t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "sourceId": source_id},
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        return response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None
    finally:
        if own:
            client.close()


def fetch_frame(
    t: datetime,
    *,
    cache_dir: Path = config.CACHE_DIR,
    client: httpx.Client | None = None,
    offline: bool = False,
    layers: str = config.HELIOVIEWER_LAYERS,
    image_scale: float = config.HELIOVIEWER_IMAGE_SCALE,
    size_px: int = config.HELIOVIEWER_IMAGE_PX,
) -> SunFrame | None:
    """One PNG of the Sun nearest ``t``, cached. None when Helioviewer has no image there."""
    path = image_path(t, cache_dir)
    if path.exists():
        meta = json.loads(_meta_path(path).read_text(encoding="utf-8")) if _meta_path(path).exists() else {}
        actual = pd.Timestamp(meta["actual"]).to_pydatetime() if meta.get("actual") else None
        return SunFrame(t, actual, path, meta.get("source_id"), True)
    if offline:
        return None

    own = client is None
    client = client or make_client()
    try:
        info = closest_image(t, client=client)
        response = client.get(
            f"{config.HELIOVIEWER_BASE_URL}/takeScreenshot/",
            params={
                "date": t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "imageScale": image_scale,
                "layers": layers,
                "x0": 0,
                "y0": 0,
                "width": size_px,
                "height": size_px,
                "display": "true",
                "watermark": "false",
            },
            timeout=120.0,
        )
        if response.status_code != 200 or not response.headers.get("content-type", "").startswith("image/"):
            log.warning("Helioviewer returned no image for %s (%s)", t.isoformat(), response.status_code)
            return None
        content = response.content
    except httpx.HTTPError as exc:
        log.warning("Helioviewer request for %s failed (%s)", t.isoformat(), exc)
        return None
    finally:
        if own:
            client.close()

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(content)
    os.replace(tmp, path)
    actual = None
    if info and info.get("date"):
        actual = pd.Timestamp(str(info["date"]), tz="UTC").to_pydatetime()
    _meta_path(path).write_text(
        json.dumps(
            {
                "requested": t.astimezone(UTC).isoformat(),
                "actual": actual.isoformat() if actual else None,
                "source_id": info.get("id") if info else None,
                "layers": layers,
                "image_scale": image_scale,
                "size_px": size_px,
                "bytes": len(content),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return SunFrame(t, actual, path, info.get("id") if info else None, False)


def fetch_frames(
    start: datetime,
    end: datetime,
    *,
    per_day: int = config.HELIOVIEWER_FRAMES_PER_DAY,
    cache_dir: Path = config.CACHE_DIR,
    offline: bool = False,
    client: httpx.Client | None = None,
) -> list[SunFrame]:
    """Every frame over the window, cached; frames Helioviewer cannot supply are simply absent."""
    times = frame_times(start, end, per_day=per_day)
    own = client is None
    client = client or make_client()
    out: list[SunFrame] = []
    try:
        for t in times:
            frame = fetch_frame(t, cache_dir=cache_dir, client=client, offline=offline)
            if frame is not None:
                out.append(frame)
    finally:
        if own:
            client.close()
    log.info(
        "Helioviewer: %d of %d frames for %s to %s (%d from cache)",
        len(out),
        len(times),
        start.date(),
        end.date(),
        sum(1 for f in out if f.from_cache),
    )
    return out


def frames_table(frames: list[SunFrame]) -> pd.DataFrame:
    """The frames as a table, for the viewer bundle and the log: what was asked, what came back, how far off."""
    return pd.DataFrame(
        [
            {
                "requested": pd.Timestamp(f.requested),
                "actual": pd.Timestamp(f.actual) if f.actual else pd.NaT,
                "lag_minutes": round(f.lag.total_seconds() / 60.0, 2) if f.lag is not None else None,
                "file": f.path.name,
                "kilobytes": round(f.path.stat().st_size / 1024.0, 1) if f.path.exists() else None,
            }
            for f in frames
        ]
    )
