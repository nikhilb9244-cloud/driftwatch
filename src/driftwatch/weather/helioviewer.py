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

**Each frame is fetched twice, at two sizes.** The full 512 px image is 360 kB, and a seven-day
replay wants 29 of them; loading all of that before a reader has scrubbed anywhere would be ten
megabytes spent on a picture. So a 64 px thumbnail of the same disc is fetched alongside -- the
identical request at a coarser ``imageScale``, needing no image library and no second code path
-- and it is small enough (about 3 kB) to inline into the replay timeline. The viewer draws the
thumbnail immediately at every scrub position and fetches the full frame as the playhead
approaches it.

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
    """One cached frame: what was asked for, what came back, and where it is.

    ``thumb`` is the same disc at :data:`driftwatch.config.HELIOVIEWER_THUMB_PX`, fetched
    alongside the full frame so the viewer has something to draw while the full one is in
    flight. It is ``None`` when Helioviewer served the full frame but not the small one, which
    the caller reports rather than papering over.
    """

    requested: datetime
    actual: datetime | None
    path: Path
    source_id: int | None
    from_cache: bool
    thumb: Path | None = None

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


def image_path(
    t: datetime, cache_dir: Path = config.CACHE_DIR, *, thumb: bool = False, thumb_px: int | None = None
) -> Path:
    """Where a frame is cached. **The thumbnail's size is in its name**, on purpose.

    Without it, changing :data:`driftwatch.config.HELIOVIEWER_THUMB_PX` would go on serving the
    old size from cache for ever and the config would silently mean nothing -- which is how the
    64 px measurement was found still in place after the value had been changed to 32.
    """
    if not thumb:
        return cache_dir / "helioviewer" / f"aia193_{stamp(t)}.png"
    px = config.HELIOVIEWER_THUMB_PX if thumb_px is None else thumb_px
    return cache_dir / "helioviewer" / f"aia193_{stamp(t)}_thumb{px}.png"


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


def _screenshot(
    t: datetime,
    *,
    client: httpx.Client,
    layers: str,
    image_scale: float,
    size_px: int,
) -> bytes | None:
    """The PNG bytes of one screenshot, or None when Helioviewer will not serve it."""
    try:
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
    except httpx.HTTPError as exc:
        log.warning("Helioviewer request for %s at %d px failed (%s)", t.isoformat(), size_px, exc)
        return None
    if response.status_code != 200 or not response.headers.get("content-type", "").startswith("image/"):
        log.warning("Helioviewer returned no %d px image for %s (%s)", size_px, t.isoformat(), response.status_code)
        return None
    return response.content


def _write_png(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(content)
    os.replace(tmp, path)


def fetch_frame(
    t: datetime,
    *,
    cache_dir: Path = config.CACHE_DIR,
    client: httpx.Client | None = None,
    offline: bool = False,
    layers: str = config.HELIOVIEWER_LAYERS,
    image_scale: float = config.HELIOVIEWER_IMAGE_SCALE,
    size_px: int = config.HELIOVIEWER_IMAGE_PX,
    thumb_px: int = config.HELIOVIEWER_THUMB_PX,
) -> SunFrame | None:
    """One PNG of the Sun nearest ``t`` and a thumbnail of it, cached.

    The thumbnail is the identical request at a coarser ``imageScale``, so the field of view is
    the same disc and the only difference is the pixel count. A frame whose full image exists but
    whose thumbnail does not (an older cache, or a failed second request) is still returned, with
    ``thumb`` as None; the viewer then waits for the full image rather than showing nothing.
    """
    path = image_path(t, cache_dir)
    thumb_path = image_path(t, cache_dir, thumb=True, thumb_px=thumb_px)
    if path.exists() and (thumb_path.exists() or offline):
        meta = json.loads(_meta_path(path).read_text(encoding="utf-8")) if _meta_path(path).exists() else {}
        actual = pd.Timestamp(meta["actual"]).to_pydatetime() if meta.get("actual") else None
        return SunFrame(t, actual, path, meta.get("source_id"), True, thumb_path if thumb_path.exists() else None)
    if offline:
        return None

    own = client is None
    client = client or make_client()
    try:
        info = closest_image(t, client=client)
        content = (
            None
            if path.exists()
            else _screenshot(t, client=client, layers=layers, image_scale=image_scale, size_px=size_px)
        )
        if content is None and not path.exists():
            return None
        small = _screenshot(
            t,
            client=client,
            layers=layers,
            image_scale=image_scale * size_px / thumb_px,
            size_px=thumb_px,
        )
    finally:
        if own:
            client.close()

    if content is not None:
        _write_png(path, content)
    if small is not None:
        _write_png(thumb_path, small)
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
                "bytes": len(content) if content is not None else path.stat().st_size,
                "thumb_px": thumb_px,
                "thumb_bytes": len(small) if small is not None else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return SunFrame(t, actual, path, info.get("id") if info else None, False, thumb_path if small else None)


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
        "Helioviewer: %d of %d frames for %s to %s (%d from cache, %d with a thumbnail)",
        len(out),
        len(times),
        start.date(),
        end.date(),
        sum(1 for f in out if f.from_cache),
        sum(1 for f in out if f.thumb is not None),
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
                "thumb_kilobytes": round(f.thumb.stat().st_size / 1024.0, 2) if f.thumb and f.thumb.exists() else None,
            }
            for f in frames
        ]
    )
