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
SPACEX_DIR = DATA_DIR / "spacex"
WEATHER_DIR = DATA_DIR / "weather"
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

# SpaceX's own Starlink ephemerides, with covariance, 72 hours ahead at a 60-second step,
# refreshed every eight hours. Served without an account and without a stated licence, for
# the express purpose of letting other operators screen against Starlink; Space-Track stopped
# hosting them on 28 July 2025, so its user agreement does not govern them. The rule adopted
# is analysis only: compute with them and publish the results crediting SpaceX, never
# republish the raw files. See docs/spacex-ephemerides.md and ephemeris/spacex.py.
SPACEX_EPHEMERIS_URL = "https://api.starlink.com/public-files/ephemerides/"
SPACEX_CITATION = (
    "Starlink ephemerides published by SpaceX (api.starlink.com/public-files/ephemerides/), "
    "used for analysis; the raw files are not redistributed."
)
# The manifest names one file per satellite and the names do not change between versions, so
# a few hours old is fine; the contents behind them are what refresh.
SPACEX_MANIFEST_MAX_AGE = timedelta(hours=4)
# Only the position covariance is kept, and only every this many seconds of it. The published
# covariance is smooth for the first ten hours and piecewise constant afterwards, so a
# ten-minute grid holds it to a fraction of a percent and turns a 2 MB file into tens of
# kilobytes. Each file is one request; the whole constellation would be 22 GB a version, so a
# fetch is bounded to the objects a run's events actually involve.
SPACEX_COVARIANCE_STEP_S = 600.0
SPACEX_MAX_OBJECTS = 300
# The trajectory driftwatch propagates for a Starlink secondary is CelesTrak's SGP4 fit to
# the ephemeris, not the ephemeris itself, and that fit's own published residual (the median
# `RMS` field of the supplemental records, 0.20 km on 2026-09-02) is larger than SpaceX's
# published sigma for the first several hours. It is an independent error source from theirs
# -- theirs describes the ephemeris, this is the distance from the ephemeris to what we
# propagate -- so it is added in quadrature rather than used as a floor. Set to 0.0 once
# Stage C interpolates the ephemeris states directly, at which point the fit is out of the
# chain; that is the first Phase 4 item in ROADMAP.md.
SPACEX_SGP4_FIT_RMS_KM = 0.20
# CelesTrak publishes that residual as one scalar. An SGP4 fit to an ephemeris misses mostly
# along track, so the scalar is split in the shape of the base model's own measured floor
# where there is one, and in this shape -- the shortest supplemental bin's measured
# disagreement, unit-normed -- where there is not.
SPACEX_FIT_RMS_SHARE = (0.099, 0.994, 0.055)

# ---------------------------------------------------------------------------------------
# Space weather (Phase 3 Step 1). See docs/space-weather.md and driftwatch/weather/.

# CelesTrak's SW-All.csv: three-hourly Kp and ap and daily F10.7 back to 1957, then
# predicted F10.7 forward to 2041. The primary driver for the density model. Same politeness
# rules as the element sets; it changes once a day.
CELESTRAK_SW_URL = "https://celestrak.org/SpaceData/SW-All.csv"
CELESTRAK_SW_MAX_AGE = timedelta(hours=12)

# NOAA SWPC. Public, no account, no stated rate limit; the cache floors below keep the
# fetches to roughly the rate at which each product is actually reissued.
SWPC_BASE_URL = "https://services.swpc.noaa.gov"
# Three-hourly Kp: the last week observed and estimated, then three days predicted, in one
# feed. This is the three-day Kp forecast the prompt asks for; the JSON carries no issue
# time of its own, so the HTTP Last-Modified header is used (see weather/swpc.py).
SWPC_KP_FORECAST_URL = f"{SWPC_BASE_URL}/products/noaa-planetary-k-index-forecast.json"
# The real-time planetary K index, estimated once a minute from the ground magnetometers.
SWPC_KP_REALTIME_URL = f"{SWPC_BASE_URL}/json/planetary_k_index_1m.json"
# The 27-day outlook: daily F10.7, planetary A index and largest Kp. Text only -- SWPC
# publishes no JSON for it -- and it carries its own ``:Issued:`` line.
SWPC_27DAY_URL = f"{SWPC_BASE_URL}/text/27-day-outlook.txt"
# The three-day forecast text, fetched only for its ``:Issued:`` line and its discussion; the
# numbers come from the JSON above.
SWPC_3DAY_URL = f"{SWPC_BASE_URL}/text/3-day-forecast.txt"
# Solar wind at L1, propagated to the bow shock: speed, density, temperature and the
# interplanetary magnetic field in one series. The one-hour file is the live view, the full
# file the last week.
SWPC_SOLAR_WIND_URL = f"{SWPC_BASE_URL}/products/geospace/propagated-solar-wind.json"
SWPC_SOLAR_WIND_1H_URL = f"{SWPC_BASE_URL}/products/geospace/propagated-solar-wind-1-hour.json"
# How often each product is worth refetching. Kp is reissued every three hours, the 27-day
# outlook once a day, the solar wind once a minute (but a screening run does not need it that
# fresh).
SWPC_KP_MIN_INTERVAL = timedelta(minutes=30)
SWPC_27DAY_MIN_INTERVAL = timedelta(hours=6)
SWPC_SOLAR_WIND_MIN_INTERVAL = timedelta(minutes=15)

# Helioviewer: Sun imagery for the Step 5 replay. Public API, no account. Credit is asked
# for in the API documentation rather than required by a licence.
HELIOVIEWER_BASE_URL = "https://api.helioviewer.org/v2"
# SDO/AIA 193 A shows the corona and the coronal holes that drive recurrent storms; it is the
# channel a reader recognises. 512 px at 4.8 arcsec/px is the full disc with a margin.
HELIOVIEWER_LAYERS = "[SDO,AIA,193,1,100]"
HELIOVIEWER_IMAGE_SCALE = 4.8
HELIOVIEWER_IMAGE_PX = 512
# A few frames a day, not a movie: enough to see the active region turn.
HELIOVIEWER_FRAMES_PER_DAY = 4
HELIOVIEWER_CITATION = "Sun imagery courtesy of the Helioviewer Project (helioviewer.org), NASA/SDO and the AIA team."

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
