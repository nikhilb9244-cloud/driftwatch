"""The manoeuvre flag: what we know, what we suspect, and what the history shows.

SGP4 cannot predict a burn. An element set fitted before a manoeuvre is wrong after it
by the size of the burn, and nothing in a screening against public element sets can see
the burn coming. What the pipeline can do is say, for each object, how likely a burn is
and whether its recent history shows one. The flag has three prior values, decided at
the Step 2 review, and one value the history can promote to:

``known``
    Operated constellations and crewed stations (the ``starlink``, ``oneweb``,
    ``constellation`` and ``station`` categories), and fleet members whose file says
    ``manoeuvres: true``.
``possible``
    Every other payload in CelesTrak's ``active`` group (the ``payload`` category, or
    ``unknown`` when SATCAT has no type for it yet): an operational satellite that may or
    may not have propulsion.
``none``
    Debris and rocket bodies whatever group they sit in, payloads outside the active
    group (dead, or never operational), and fleet members whose file says
    ``manoeuvres: false``.
``observed``
    A ``possible`` object whose element-set history shows a jump in semi-major axis
    that drag cannot explain. The dates are recorded.

The detector. Between consecutive element sets ``k`` and ``k + 1`` the osculating
semi-major axis should change only by drag, and SGP4 has its own model of that (the
B* term). Propagating set ``k`` to the epoch of set ``k + 1`` twice, once with its B*
and once with B* zeroed, gives the drag-driven change ``da_drag`` SGP4 expects; the
osculating semi-major axis of set ``k + 1`` at its own epoch, minus that of set ``k``
propagated with drag to the same instant, is the change the model did not predict,
``da_unexplained``. Because both states are evaluated at the same time and within a few
kilometres of each other, the short-period J2 terms in the osculating semi-major axis
(about 8 km peak to peak in LEO) cancel to metres. A raise beyond a floor of 100 m and
half the modelled drag change is a manoeuvre: drag cannot raise an orbit. A lowering is
flagged only when it exceeds the floor and twice the modelled drag change: an
underestimated B*, or a geomagnetic storm, can double or treble the decay, and Phase 3
needs exactly those intervals kept, so the lowering test is deliberately lenient. A
jump that the next interval reverses (a raise followed by an equal fall) is not a
manoeuvre but a bad element set; that set is dropped from the covariance fit and
neither interval is counted.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

MANOEUVRE_LEVELS: tuple[str, ...] = ("none", "possible", "observed", "known")
# Categories whose members are operated and manoeuvre as a matter of course.
KNOWN_MANOEUVRING_CATEGORIES: frozenset[str] = frozenset({"starlink", "oneweb", "constellation", "station"})
# Categories that can be "possible" when the object is in the active group: payloads, and objects
# SATCAT has not typed yet. Debris and rocket bodies never manoeuvre, whatever group they are in.
POSSIBLY_MANOEUVRING_CATEGORIES: frozenset[str] = frozenset({"payload", "unknown"})

# Below this an unexplained change in semi-major axis is fit noise, not a burn: the
# short-period residual of the same-time comparison plus the scatter of the mean motion
# between fits is a few tens of metres in LEO.
JUMP_FLOOR_KM = 0.1
# A raise must also exceed this fraction of the drag change SGP4 modelled over the interval
# (the B* fit can be off by tens of percent), and a lowering this multiple of it.
RAISE_DRAG_FRACTION = 0.5
LOWER_DRAG_MULTIPLE = 2.0
# Consecutive element sets further apart than this are not compared: the drag model's error
# over long gaps is no longer small against a burn.
MAX_INTERVAL_DAYS = 10.0


def manoeuvre_prior(category: str, in_active_group: bool, fleet_flag: bool | None = None) -> str:
    """The prior flag for one object: the fleet file's word if it has one, else the category and group rules."""
    if fleet_flag is not None:
        return "known" if fleet_flag else "none"
    if str(category) in KNOWN_MANOEUVRING_CATEGORIES:
        return "known"
    if in_active_group and str(category) in POSSIBLY_MANOEUVRING_CATEGORIES:
        return "possible"
    return "none"


def promote(level: str, n_jumps: int) -> str:
    """Promote ``possible`` to ``observed`` when the history shows jumps; other levels are unchanged."""
    if level == "possible" and n_jumps > 0:
        return "observed"
    return level


@dataclass
class JumpDetection:
    """What the detector found in one object's history.

    ``jump_epochs`` are the epochs of the first element set after each detected burn (the
    burn happened in the interval ending there), ``jump_delta_a_km`` the unexplained
    change in semi-major axis (positive for a raise), ``bad_set_epochs`` the epochs of
    element sets judged to be outliers rather than evidence of a burn.
    """

    jump_epochs: list[datetime] = field(default_factory=list)
    jump_delta_a_km: list[float] = field(default_factory=list)
    bad_set_epochs: list[datetime] = field(default_factory=list)
    n_intervals: int = 0

    @property
    def n_jumps(self) -> int:
        return len(self.jump_epochs)


def detect_jumps(
    a_next_fitted_km: np.ndarray,
    a_next_propagated_km: np.ndarray,
    a_next_no_drag_km: np.ndarray,
    dt_days: np.ndarray,
    *,
    floor_km: float = JUMP_FLOOR_KM,
    raise_fraction: float = RAISE_DRAG_FRACTION,
    lower_multiple: float = LOWER_DRAG_MULTIPLE,
    max_interval_days: float = MAX_INTERVAL_DAYS,
) -> tuple[np.ndarray, np.ndarray]:
    """Flag the consecutive intervals that show a burn, and the element sets that are outliers.

    The three semi-major-axis arrays are indexed by interval ``k`` (between sets ``k`` and
    ``k + 1``) and are all evaluated at the epoch of set ``k + 1``: the osculating value
    of set ``k + 1`` itself, of set ``k`` propagated with its B*, and of set ``k``
    propagated with B* zeroed. Returns ``(jump, bad_set)``: ``jump[k]`` is True when
    interval ``k`` holds a manoeuvre; ``bad_set[m]`` (length one more than ``jump``) is
    True when set ``m`` is an outlier, in which case the intervals either side of it are
    not flagged. Non-finite inputs and intervals longer than ``max_interval_days`` are
    never flagged.
    """
    a_fit = np.asarray(a_next_fitted_km, dtype=float)
    a_prop = np.asarray(a_next_propagated_km, dtype=float)
    a_free = np.asarray(a_next_no_drag_km, dtype=float)
    dt = np.asarray(dt_days, dtype=float)
    n_int = len(a_fit)
    bad_set = np.zeros(n_int + 1, dtype=bool)
    if n_int == 0:
        return np.zeros(0, dtype=bool), bad_set
    with np.errstate(invalid="ignore"):
        da_drag = a_prop - a_free  # what SGP4's drag model removed over the interval (negative)
        da_unexplained = a_fit - a_prop
        raise_threshold = np.maximum(floor_km, raise_fraction * np.abs(da_drag))
        lower_threshold = np.maximum(floor_km, lower_multiple * np.abs(da_drag))
        comparable = np.isfinite(da_drag) & np.isfinite(da_unexplained) & (dt <= max_interval_days) & (dt > 0)
        raised = comparable & (da_unexplained > raise_threshold)
        lowered = comparable & (da_unexplained < -lower_threshold)
    jump = raised | lowered
    # A jump that the next interval reverses is one bad element set, not two burns.
    for k in np.nonzero(jump[:-1])[0]:
        if not jump[k + 1] or bad_set[k + 1]:
            continue
        opposite = np.sign(da_unexplained[k]) != np.sign(da_unexplained[k + 1])
        if opposite and abs(da_unexplained[k + 1]) >= 0.5 * abs(da_unexplained[k]):
            bad_set[k + 1] = True
            jump[k] = False
            jump[k + 1] = False
    return jump, bad_set


def summarise(detection: JumpDetection, epochs: Iterable[datetime] | None = None) -> dict[str, object]:
    """A JSON-friendly summary of a detection for logs and the objects table."""
    return {
        "n_jumps": detection.n_jumps,
        "jump_epochs": [t.isoformat() for t in detection.jump_epochs],
        "jump_delta_a_km": [round(x, 4) for x in detection.jump_delta_a_km],
        "n_bad_sets": len(detection.bad_set_epochs),
    }
