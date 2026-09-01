"""Paths, endpoints and politeness settings shared across driftwatch.

Everything here can be overridden with environment variables where it makes sense to
run the pipeline somewhere other than a checkout (a GitHub Actions runner, for example).
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from driftwatch import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("DRIFTWATCH_DATA_DIR", PROJECT_ROOT / "data"))
CACHE_DIR = DATA_DIR / "cache"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
PROPAGATED_DIR = DATA_DIR / "propagated"
VIEWER_DATA_DIR = Path(os.environ.get("DRIFTWATCH_VIEWER_DATA_DIR", PROJECT_ROOT / "web" / "public" / "data"))

# CelesTrak asks for a descriptive User-Agent so they can tell polite tools from
# runaway scripts. Set DRIFTWATCH_CONTACT to add a contact address.
_contact = os.environ.get("DRIFTWATCH_CONTACT", "")
USER_AGENT = (
    f"driftwatch/{__version__} (open-source LEO conjunction screening; cached fetches"
    + (f"; contact {_contact}" if _contact else "")
    + ")"
)

CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
CELESTRAK_SATCAT_URL = "https://celestrak.org/pub/satcat.csv"

# CelesTrak's stated limit is one fetch per group every two hours. This is a floor, not a
# suggestion, so the CLI does not expose a way to go below it.
MIN_GROUP_FETCH_INTERVAL = timedelta(hours=2)
# SATCAT changes slowly (new launches, decays); once a day is plenty.
SATCAT_MAX_AGE = timedelta(hours=24)
HTTP_TIMEOUT_S = 120.0

# Groups fetched by default. `active` holds every operational payload, so the constellation
# groups mostly overlap it; they are fetched anyway because membership is a cheap and
# reliable classification signal. `last-30-days` catches rocket bodies and fresh debris
# that are not in `active`. The four debris groups are the large fragmentation clouds.
# CelesTrak has no whole-catalogue query; the rest of the ~30,000 tracked objects come from
# Space-Track in a later phase.
DEFAULT_GROUPS: tuple[str, ...] = (
    "active",
    "stations",
    "starlink",
    "oneweb",
    "last-30-days",
    "fengyun-1c-debris",
    "iridium-33-debris",
    "cosmos-2251-debris",
)
