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
HISTORY_DIR = DATA_DIR / "history"
SUPPLEMENTAL_DIR = DATA_DIR / "supplemental"
CONJUNCTION_DIR = DATA_DIR / "conjunctions"
EXTERNAL_DIR = DATA_DIR / "external"
# ESA's Kelvins Collision Avoidance Challenge data, if downloaded (see risk/kelvins.py).
KELVINS_DIR = EXTERNAL_DIR / "kelvins"
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
# Supplemental GP data: element sets CelesTrak fits to operator-supplied ephemerides. The
# Starlink file comes from SpaceX's published ephemerides, which include planned manoeuvres
# that the standard element sets cannot know about. Same politeness rules as gp.php.
CELESTRAK_SUPPLEMENTAL_URL = "https://celestrak.org/NORAD/elements/supplemental/sup-gp.php"
SUPPLEMENTAL_FILES: tuple[str, ...] = ("starlink",)
# A supplemental set older than the GP set by more than this is treated as abandoned and
# the GP set is used instead.
SUPPLEMENTAL_MAX_LAG_DAYS = 1.0
# The scheduled fetch (see `.github/workflows/supplemental.yml` and
# `scripts/register-supplemental-task.ps1`) stores a version every few hours so that the
# supplemental covariance fit eventually sees consistency pairs days apart rather than
# hours apart. Three hours is inside CelesTrak's two-hour floor per group with room to
# spare, and gives eight versions a day.
SUPPLEMENTAL_FETCH_INTERVAL_HOURS = 3
# Every stored version is kept for this long; beyond it only the first of each UTC day
# survives `driftwatch supplemental --prune`, which bounds the store at a few hundred
# megabytes while keeping the long lead times the fit needs.
SUPPLEMENTAL_KEEP_ALL_DAYS = 14

# Space-Track.org: the full public catalogue and element-set history. Needs a free account;
# credentials are read from the environment only (see catalogue/spacetrack.py).
SPACETRACK_BASE_URL = "https://www.space-track.org"
SPACETRACK_LOGIN_URL = f"{SPACETRACK_BASE_URL}/ajaxauth/login"
SPACETRACK_LOGOUT_URL = f"{SPACETRACK_BASE_URL}/ajaxauth/logout"
SPACETRACK_QUERY_URL = f"{SPACETRACK_BASE_URL}/basicspacedata/query"
SPACETRACK_USER_ENV = "SPACETRACK_USER"
SPACETRACK_PASS_ENV = "SPACETRACK_PASS"
# Space-Track's published limits (documentation, read 2026-09-01) are "less than 30 requests per
# 1 minute and 300 requests per 1 hour". The limiter stays below both to leave room for anything
# else using the same account.
SPACETRACK_MAX_PER_MINUTE = 20
SPACETRACK_MAX_PER_HOUR = 250
# Space-Track allows the GP catalogue once an hour; the prompt asks for the CelesTrak floor of two
# hours and "a few times a day" at most. Both are enforced by the cache.
MIN_SPACETRACK_GP_INTERVAL = timedelta(hours=2)
MAX_SPACETRACK_GP_PULLS_PER_DAY = 4
# "Current catalogue" per Space-Track's own recipe: no decay date and an epoch in the last 30 days.
SPACETRACK_GP_MAX_EPOCH_AGE_DAYS = 30
# NORAD ids per gp_history request for the ``history`` command; keeps the URL short and each
# response a few thousand rows.
SPACETRACK_HISTORY_CHUNK = 200
# The Step 3 backfill batches ids into as many as fit a request URL of this many characters
# (about 450 six-digit ids), so the fleet and the Stage A survivors take about fifty requests
# rather than a few hundred. The Step 0 review's figure was 8,000 characters; measured on
# 2026-09-02, Space-Track serves a 3,602-character gp_history URL and answers a generic
# 403 Forbidden to one of 5,365, so the limit sits near 4 KB and 3,500 keeps clear of it. A
# 403, 413 or 414 on a long URL splits the chunk and retries anyway.
SPACETRACK_HISTORY_URL_BUDGET = 3500
# Only the element-set fields are requested from gp_history (Space-Track's ``predicates``
# operator), which cuts each response to about a third of the full record. If Space-Track
# rejects the operator the request is retried for the full records.
SPACETRACK_HISTORY_PREDICATES: tuple[str, ...] = (
    "NORAD_CAT_ID",
    "OBJECT_NAME",
    "OBJECT_ID",
    "EPOCH",
    "MEAN_MOTION",
    "ECCENTRICITY",
    "INCLINATION",
    "RA_OF_ASC_NODE",
    "ARG_OF_PERICENTER",
    "MEAN_ANOMALY",
    "BSTAR",
    "MEAN_MOTION_DOT",
    "MEAN_MOTION_DDOT",
    "EPHEMERIS_TYPE",
    "CLASSIFICATION_TYPE",
    "ELEMENT_SET_NO",
    "REV_AT_EPOCH",
)
# A history response for a thousand objects over 45 days is tens of megabytes; give it time.
SPACETRACK_HISTORY_TIMEOUT_S = 900.0
# Default backfill window for the covariance fit: element sets from this many days before the
# snapshot. Seven days of propagation error needs pairs up to seven days apart; 45 gives
# several such pairs per object without pulling a season of history.
HISTORY_BACKFILL_DAYS = 45

# Attribution required by the data providers. Space-Track's user agreement grants blanket approval
# to redistribute basic SSA data (TLEs/OMMs, SATCAT, decay data) "conditioned on appropriate
# citation"; CelesTrak asks to be credited.
CELESTRAK_CITATION = "Element sets and SATCAT from CelesTrak (celestrak.org), T.S. Kelso."
SPACETRACK_CITATION = (
    "Element sets from Space-Track.org (USSPACECOM / 18th Space Defense Squadron), "
    "redistributed with citation under the Space-Track user agreement."
)

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
