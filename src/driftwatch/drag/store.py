"""The persistent store of fitted ballistic coefficients.

A coefficient fitted from an object's decay history costs about a hundred NRLMSIS
evaluations, and it is the same answer next week: ``B = C_D A / m`` changes when the object's
attitude or configuration changes, which for most of the catalogue is never. What does change
is the history available to fit it from. So the fit is cached by NORAD id, **with the span of
history it used**, and redone only when

* that history has grown by more than :data:`driftwatch.config.BALLISTIC_REFIT_SPAN_GROWTH_DAYS`
  -- a week of new element sets is worth refitting for; a day is not;
* or the fit is older than :data:`driftwatch.config.BALLISTIC_REFIT_AFTER_DAYS`, so that a
  coefficient cannot drift arbitrarily far from the object it describes;
* or it was fitted under a different NRLMSIS version, because only the product ``B rho`` is
  observable from a decay and a fit made against one model is not a fit against another;
* or it was fitted under different acceptance rules
  (:data:`driftwatch.config.BALLISTIC_RULES_VERSION`). A change to what counts as a good
  enough decay has to reach the objects already in the store, or the store ends up holding
  rows decided by two different rules and saying so nowhere.

**Rejections are cached too.** An object whose decay is inside its own element-set scatter
costs the same hundred evaluations to find that out, and the answer is just as stable. It is
stored with ``source = 'none'`` and its reason, and retried on the same rules -- which is
exactly right, because the thing that would change the answer is more history.

Nothing here caches a ``bstar`` or a ``typical`` coefficient. The first is a property of one
element set and a new set arrives daily; the second is a property of the run it stood in for.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from driftwatch import config

log = logging.getLogger(__name__)

STORE_NAME = "coefficients.parquet"

# What a cached row carries beyond the coefficient itself: the span of history the fit saw,
# when it was made and against which model.
# How far a cached fit's history may end *after* the run asking for it before it is refused.
# A day, not zero: element sets arrive through the day and a run's newest epoch is a few hours
# behind the store's without either being wrong.
FUTURE_TOLERANCE_DAYS = 1.0

PROVENANCE_COLUMNS: tuple[str, ...] = (
    "history_start",
    "history_end",
    "fitted_at",
    "msis_version",
    "rules_version",
)


class CoefficientStore:
    """Fitted coefficients by NORAD id, kept across runs. See the module docstring."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or config.BALLISTIC_CACHE_DIR) / STORE_NAME
        self.rows: dict[int, dict[str, Any]] = {}
        self._loaded_from: pd.DataFrame | None = None
        self.dirty = False

    def load(self) -> CoefficientStore:
        """Read the store, or start an empty one. A corrupt file is a warning, not a failure."""
        if not self.path.exists():
            return self
        try:
            frame = pq.read_table(self.path).to_pandas()
        except (OSError, pa.ArrowInvalid) as exc:  # pragma: no cover - corrupt cache
            log.warning("Cannot read the ballistic cache at %s (%s); refitting from scratch", self.path, exc)
            return self
        self._loaded_from = frame
        for row in frame.to_dict("records"):
            self.rows[int(row["norad_id"])] = row
        log.info("Ballistic cache: %d coefficients from %s", len(self.rows), self.path)
        return self

    def usable(self, norad_id: int, *, history_end: datetime | None, now: datetime) -> dict[str, Any] | None:
        """The cached row for ``norad_id`` if it is still good, else ``None``.

        ``history_end`` is the epoch of the newest element set now available for the object;
        a cached fit whose own history stopped materially earlier than that is stale.
        """
        row = self.rows.get(int(norad_id))
        if row is None:
            return None
        if str(row.get("msis_version", "")) != str(config.MSIS_VERSION):
            return None
        if str(row.get("rules_version", "")) != str(config.BALLISTIC_RULES_VERSION):
            return None
        fitted_at = pd.to_datetime(row.get("fitted_at"), utc=True, errors="coerce")
        if pd.isna(fitted_at):
            return None
        age_days = (pd.Timestamp(now).tz_convert("UTC") - fitted_at).total_seconds() / 86400.0
        if age_days > config.BALLISTIC_REFIT_AFTER_DAYS:
            return None
        cached_end = pd.to_datetime(row.get("history_end"), utc=True, errors="coerce")
        if history_end is not None and not pd.isna(cached_end):
            grown_days = (pd.Timestamp(history_end).tz_convert("UTC") - cached_end).total_seconds() / 86400.0
            if grown_days > config.BALLISTIC_REFIT_SPAN_GROWTH_DAYS:
                return None
            # And the other direction, which a live-only pipeline never sees and a historical run
            # hits immediately: a fit made from element sets *later* than the ones this run is
            # allowed to know about. Rescoring 9 May 2024 must not be handed a coefficient fitted
            # in 2026 -- it would be a measurement of a different atmosphere, and for a satellite
            # that has since changed shell, of a different orbit. See Phase 3 Step 4's replay.
            if grown_days < -FUTURE_TOLERANCE_DAYS:
                return None
        return dict(row)

    def put(self, row: dict[str, Any], *, history_start: Any, history_end: Any, now: datetime) -> None:
        """Store one fit outcome. Only history fits and history rejections belong here.

        A ``thrust`` refusal is a rejection like any other -- an outcome of the fit rules over
        this object's own element sets -- so it is cached and reread rather than recomputed.
        """
        if str(row.get("source")) not in ("history", "none", "thrust"):
            return
        self.rows[int(row["norad_id"])] = {
            **row,
            "history_start": pd.Timestamp(history_start) if history_start is not None else pd.NaT,
            "history_end": pd.Timestamp(history_end) if history_end is not None else pd.NaT,
            "fitted_at": pd.Timestamp(now).tz_convert("UTC"),
            "msis_version": str(config.MSIS_VERSION),
            "rules_version": str(config.BALLISTIC_RULES_VERSION),
        }
        self.dirty = True

    def save(self) -> Path | None:
        """Write the store back if anything changed."""
        if not self.dirty or not self.rows:
            return None
        frame = pd.DataFrame(list(self.rows.values()))
        for column in ("history_start", "history_end", "fitted_at"):
            frame[column] = pd.to_datetime(frame.get(column), utc=True, errors="coerce").astype("datetime64[us, UTC]")
        frame["norad_id"] = frame["norad_id"].astype("int64")
        frame = frame.sort_values("norad_id").reset_index(drop=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), self.path, compression="zstd")
        log.info("Ballistic cache: wrote %d coefficients to %s", len(frame), self.path)
        self.dirty = False
        return self.path

    def summary(self, *, now: datetime | None = None) -> dict[str, Any]:
        """What the store holds, for the run record."""
        now = now or datetime.now(UTC)
        if not self.rows:
            return {"n": 0, "path": str(self.path)}
        ages = []
        for row in self.rows.values():
            fitted_at = pd.to_datetime(row.get("fitted_at"), utc=True, errors="coerce")
            if not pd.isna(fitted_at):
                ages.append((pd.Timestamp(now).tz_convert("UTC") - fitted_at).total_seconds() / 86400.0)
        sources = pd.Series([str(r.get("source")) for r in self.rows.values()]).value_counts()
        return {
            "n": len(self.rows),
            "path": str(self.path),
            "by_source": {str(k): int(v) for k, v in sources.items()},
            "age_days": {"median": round(float(np.median(ages)), 2), "max": round(float(np.max(ages)), 2)}
            if ages
            else None,
        }
