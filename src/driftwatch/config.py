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
# Historical snapshots (Phase 3 Step 4) live in a subdirectory of their own rather than beside
# the live ones. `list_snapshots` globs `gp_*.parquet`, and a file named for 2022 sorts *after*
# every 2026 file because "a" beats a digit -- so a reconstruction of an old day would become
# "the latest snapshot" for the whole pipeline. It is also simply a different kind of object:
# a live snapshot is what the catalogue said at a fetch, a historical one is what it said on a
# date we chose, rebuilt from gp_history afterwards.
AS_OF_SNAPSHOT_DIR = SNAPSHOT_DIR / "as-of"
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
# The minute-cadence solar wind is most of the store's bulk: about a megabyte a fetch, and
# every fetch repeats the whole week. It is kept at one minute for this long and then rolled
# into one hourly archive (weather/swpc.py, roll_solar_wind), which keeps the means and the
# extremes -- an hourly *mean* of Bz would average away exactly the southward excursions that
# drive a storm, so the archive carries the minimum and the maximum beside the mean.
SOLAR_WIND_MINUTE_DAYS = 7

# The uncertainty of the ap the table carries, which is what Step 3's variance term consumes.
# Two regimes. A measurement is uncertain only by the resolution of the index itself, which is
# one Bartels step; SWPC's estimated Kp is provisional and is revised by about a step. A
# forecast is uncertain by the part of the climatological spread its skill does not remove:
# with a correlation r against what happens, the residual spread is sigma_clim * sqrt(1 - r^2),
# so as skill goes to zero the uncertainty widens to the climatological spread itself. These
# correlations are a prior of the right order for SWPC's three-day Kp forecast, not a measured
# skill score, and May 2024 was very much worse than this; the lead-day breakpoints are
# 0, 1, 2 and 3 days and everything past three days takes r = 0.
AP_FORECAST_CORRELATION_BY_LEAD_DAY = ((0.0, 0.85), (1.0, 0.70), (2.0, 0.50), (3.0, 0.40))
# The climatological spread is measured from the observed record itself, over this many days
# before the window. The distribution is strongly skewed -- most intervals are quiet and the
# variance is carried by a few storm days -- so this standard deviation is much larger than a
# typical interval's ap, which is the honest statement of what "no forecast skill" means.
AP_CLIMATOLOGY_DAYS = 365
# Used only when no observed record is available to measure it from. Of the right order for a
# solar maximum year; the log says when the fallback was used.
AP_CLIMATOLOGY_FALLBACK_NT = 20.0
# A forecast of a storm carries an uncertainty proportional to the storm it forecasts: an ap
# of 100 nT is not known to the same absolute precision as an ap of 5 nT. The forecast
# uncertainty is floored at this fraction of the forecast value, which matters above about
# 50 nT where the climatological term alone would understate it. A prior, not a measurement.
AP_FORECAST_RELATIVE_FLOOR = 0.5

# ---------------------------------------------------------------------------------------
# Density and drag (Phase 3 Step 2). See docs/density-and-drag.md and driftwatch/drag/.

# NRLMSIS through pymsis. 2.1 is the current version; 0 is the 2000 model, kept available
# because a good deal of published drag work still uses it. Recorded in every run so a
# result can be reproduced against the model that made it.
MSIS_VERSION = 2.1
# The sampling step along an orbit, as samples per revolution. Sixteen puts a sample every
# 5.6 minutes at low Earth orbit, which resolves the local-time swing -- the factor of about
# two between the day and night sides -- that dominates a near-circular orbit's density.
# docs/density-and-drag.md carries the convergence measurement.
DENSITY_SAMPLES_PER_ORBIT = 16
# Above this eccentricity the altitude range, not the local time, is what the step has to
# resolve: the drag of an eccentric orbit is concentrated in its perigee passage.
DENSITY_ECCENTRICITY_THRESHOLD = 0.005
# A representative thermospheric scale height. Density falls by a factor of e over this
# height, so it is the natural unit for "how much altitude may a step cross".
DENSITY_SCALE_HEIGHT_KM = 50.0
DENSITY_SCALE_HEIGHTS_PER_STEP = 1.0
# Whatever the rule gives, the step stays inside these. The floor is cost; the ceiling keeps
# a slow, high orbit from being sampled so coarsely that the diurnal bulge is aliased.
DENSITY_MIN_STEP_S = 30.0
DENSITY_MAX_STEP_S = 600.0

# The ballistic coefficient B = C_D A / m, in m^2/kg. Fitting it from an object's own decay
# needs the decay to be larger than the scatter of the element sets it is measured from.
# A window this long, with at least this many element sets, or the fit is refused.
BALLISTIC_MIN_SPAN_DAYS = 10.0
BALLISTIC_MIN_SETS = 6
# And the decay has to be *measurably* larger than that scatter, which is the Step 2 review's
# threshold: the drop in mean semi-major axis over the clean intervals must exceed the
# uncertainty the element-set scatter puts on it by this factor. The scatter is measured on
# the object's own series -- the root-mean-square residual of a quadratic through its mean
# semi-major axis over the kept sets -- rather than assumed, so an object with quiet elements
# gets a fit from a smaller decay than one whose elements bounce.
BALLISTIC_MIN_DECAY_SNR = 3.0
# An absolute floor under that, because below a few tens of metres the difference between two
# mean semi-major axes is systematics rather than noise and the scatter estimate no longer
# describes it.
BALLISTIC_MIN_DECAY_M = 20.0
# And a fit is refused outright when more than this fraction of the object's intervals had to
# be excluded as manoeuvres. Excluding a burn assumes the intervals around it are free flight;
# an object manoeuvring in a quarter of them is under continuous control, and a *continuous*
# low thrust is a ramp rather than a jump, so the detector cannot see it and the fit reads it
# as drag.
#
# This is a proxy, and it is set from a measurement rather than chosen. On the demo run of
# 2026-09-02, of the 384 objects fitted from history, the median B by band of excluded
# fraction is 0.045, 0.018, 0.012, 0.013 and 0.014 for the bands up to a quarter and then
# 0.023, 0.260 and 0.183 above it: flat, then a jump of an order of magnitude. Every Starlink
# fitted above 0.5 m^2/kg is above a quarter -- 48 km of decay in 45 days at 400 km, which is
# a deorbit and not an atmosphere, and inverts to an area-to-mass a satellite does not have.
#
# The rule is on the *exclusions* and not on the coefficient because the high coefficients are
# not all wrong: every debris object above 0.5 has no exclusions at all, and that tail -- thin
# plate and multi-layer insulation from the big fragmentation clouds -- is real and has to
# survive. Being a proxy it does not catch everything: STARLINK-65196 has 12 per cent of its
# intervals excluded and still fits at 0.69 m^2/kg off 43 km of decay. It is reported in
# docs/density-and-drag.md rather than chased with a tighter number that would start refusing
# the fragments.
BALLISTIC_MAX_MANOEUVRE_FRACTION = 0.25
# The window the fit looks back over. Long enough to average out the element-set scatter and
# to include a range of geomagnetic conditions; short enough that the object's attitude and
# area have not changed much.
BALLISTIC_FIT_DAYS = 45.0
# Physically plausible bounds for B. A dense compact body sits near 0.002 m^2/kg; a light
# panel or a deployed sail reaches a few tenths. Anything outside this came from a bad fit,
# not from a satellite, and is refused with its label.
BALLISTIC_MIN_M2_KG = 1e-4
BALLISTIC_MAX_M2_KG = 1.0
# Continuous thrust, added at the Step 3 review. An object that can fire an engine and whose
# decay history fits a coefficient above this is not being fitted for drag: a satellite's
# area-to-mass is bounded by its own geometry, and the largest operated low Earth orbit
# satellites reach A/m of about 0.05 m^2/kg even broadside, so B = C_D A/m tops out near
# 0.11. A manoeuvring object fitting above this is under thrust, its measured fall is not
# atmospheric, and the fit is refused in favour of the run's typical value for its class.
#
# The cut is scoped to objects that *can* thrust, and that scoping is what lets the number be
# physical rather than arbitrary. Applied to the whole catalogue the same rule would have to
# sit near the 1 m^2/kg plausibility cap to avoid discarding high area-to-mass debris, and it
# would then catch almost none of the real cases: on the demo run the objects fitting near
# the cap are Fengyun 1C, NOAA 16, DMSP and Meteor fragments with radar cross-sections of a
# few hundredths of a square metre and B* a hundred times a satellite's, where a high
# area-to-mass ratio is exactly what is expected, while the thrusting objects sit between 0.2
# and 0.7 with B* *ten times smaller* than a normal member of their own constellation and
# negative for two of them. See docs/density-and-drag.md.
BALLISTIC_THRUST_M2_KG = 0.1
# Where neither the object's own decay nor its B* gives a usable coefficient, the run's own
# median stands in, labelled `typical`. A category median needs at least this many fitted
# objects to be worth more than the overall one.
BALLISTIC_TYPICAL_MIN_OBJECTS = 5
# And when a run has fitted almost nothing, this stands in: the middle of the range a mixed
# catalogue actually shows, which is where the fitted values in docs/density-and-drag.md sit.
BALLISTIC_TYPICAL_M2_KG = 0.01
# The median is taken by category *and* altitude band (the Step 2 review's instruction). The
# bands are drag bands, not the screening bands: what a coefficient has in common with
# another object's is the regime its decay was measured in, and between 400 and 800 km the
# density falls by three orders of magnitude. `leo` is one band to the screener and six here.
BALLISTIC_ALTITUDE_BAND_EDGES_KM: tuple[float, ...] = (0.0, 350.0, 450.0, 550.0, 650.0, 800.0, 1200.0)

# Every coefficient carries an uncertainty, so Step 3 can propagate it into the variance of
# the storm term. A fitted one gets the statistical uncertainty of its own decay measurement,
# floored here: no decay measurement over six weeks of element sets pins a coefficient better
# than a few per cent, whatever its formal error says.
BALLISTIC_SIGMA_REL_FLOOR = 0.05
# A B* inversion gets a prior instead, because there is no repeat measurement to take a
# scatter from. Fifty per cent is the size of the disagreements the Step 2 table showed
# against independent estimates (Sentinel-1A -19 per cent, NOAA-20 +72 per cent).
BALLISTIC_SIGMA_REL_BSTAR = 0.5
# A `typical` stand-in gets the spread of the pool its median came from, floored at a factor
# of two: it is not a measurement of that object at all.
BALLISTIC_SIGMA_REL_TYPICAL = 1.0
# The SGP4 reference density that defines B*: B* = rho0 C_D A / (2 m), with rho0 as a column
# density in kg/m^2 per Earth radius. Quoted here for the record and deliberately NOT used to
# convert -- see docs/density-and-drag.md, where the conversion it implies is measured
# against the decay SGP4 itself produces and found to be wrong by three orders of magnitude,
# because B* is a fit parameter for SGP4's own atmosphere rather than a physical quantity.
SGP4_BSTAR_RHO0 = 2.461e-5
# The fallback measures what decay the element set's own B* produces over this many days and
# inverts it through NRLMSIS, which is self-consistent and altitude-aware where a constant is
# neither. Ten days rather than three because the orbit-averaged semi-major axis carries tens
# of metres of residual, which over three days is comparable to the decay of anything above
# about 600 km; the trend is fitted across the span, not differenced across its ends.
BSTAR_DECAY_DAYS = 10.0

# Fitting is not free: one density evaluation per element-set interval is about a hundred
# NRLMSIS calls an object. A run therefore fits only the objects that appear in events, in
# descending order of probability, under a wall-clock budget; whatever the budget does not
# reach falls back to the B* inversion and the typical value, labelled as always. Four
# minutes fits about 120 objects on this machine.
BALLISTIC_FIT_BUDGET_S = 240.0
# The fit runs on a coarser grid than the scenarios do. Profiling put 96 per cent of the fit
# in NRLMSIS itself, in proportion to the number of samples, and the fit only ever uses the
# *integral* of the density over an interval -- so the local-time structure the scenario step
# resolves is being averaged away immediately. See docs/density-and-drag.md for the measured
# cost of this against the step rule.
BALLISTIC_FIT_STEP_SCALE = 4.0

# Fitted coefficients are cached across runs by NORAD id, with the history span each was
# fitted from. B changes only when an object's attitude or configuration does, so refitting
# it every run is waste; what does change is the history available, so a cached fit is redone
# when the object's history has grown by this much or when it is this old.
BALLISTIC_CACHE_DIR = DATA_DIR / "ballistic"
# Bumped whenever the acceptance rules above change, which invalidates every cached fit made
# under the old ones. Without it a rule change would reach new objects and silently leave the
# cached ones as they were, which is the worst of both: a store whose rows were decided by
# different rules and whose rows do not say which.
BALLISTIC_RULES_VERSION = "5"
BALLISTIC_REFIT_AFTER_DAYS = 30.0
BALLISTIC_REFIT_SPAN_GROWTH_DAYS = 7.0

# ---------------------------------------------------------------------------------------
# The storm term (Phase 3 Step 3). See docs/storm-term.md and driftwatch/storm/.

# How wrong the density model's *storm response* can be. This is the part of NRLMSIS's
# uncertainty that does NOT cancel against the fitted ballistic coefficient: only the product
# B*rho is observable from a decay, so a model biased by a constant factor gives a coefficient
# biased the other way and a product that is right, but nothing corrects an error in the ratio
# between stormy and quiet. Thirty per cent is a prior.
#
# Step 4 measured it against May 2024 (2026-09-03) and it is deliberately NOT changed. The
# measurement: NRLMSIS 2.1 *over*-predicts the storm/quiet ratio by about 22 per cent, with a
# spread of a similar size and no resolvable altitude dependence from 450 to 2,000 km. So the
# magnitude of this prior is right and its centre is not -- and the sign is the opposite of what
# the sentence here used to predict, which was that the published comparisons had the empirical
# models low on the enhancement and that this would therefore move up.
#
# It stays a symmetric 0.30 for two reasons. One storm is not a population, and a model adjusted
# against the data that measured it can no longer be measured by it. `tests/test_storm_validity`
# pins this value so that the record in `docs/storm-validation.md` cannot quietly become a
# calibration; changing it is a decision somebody has to make on purpose.
DENSITY_STORM_RATIO_SIGMA_REL = 0.30
# And how wrong the absolute density can be, which matters only for an object whose coefficient
# did NOT come from a fit through this same model -- a `bstar` or `typical` one -- where the
# cancellation argument does not apply. NRLMSIS's own quoted uncertainty, tens of per cent.
DENSITY_ABSOLUTE_SIGMA_REL = 0.15

# The synthetic storm scenarios are built from the May 2024 sequence scaled to a target level.
# 10 May 2024 carries the Gannon storm's sudden commencement and its whole G5 period, which is
# the shape a scenario wants: a fast rise, a long main phase and a slow recovery.
STORM_TEMPLATE_START = "2024-05-10T00:00:00Z"
STORM_TEMPLATE_DAYS = 3.0
# Where in the screening window a synthetic storm begins, in days from the window start. A
# storm on the first day displaces an object for the whole of the rest of the window; the same
# storm on the last day displaces almost nothing, because the displacement grows with the
# square of the time left. That sensitivity is the point of the term, so the offset is a stated
# scenario parameter rather than something buried.
STORM_OFFSET_DAYS = 1.0
# Target peak Kp for each named level, from NOAA's G scale (G3 strong, G4 severe, G5 extreme).
STORM_LEVEL_KP: dict[str, float] = {"storm-g3": 7.0, "storm-g4": 8.0, "storm-g5": 9.0}
# The scenario names `driftwatch risk` accepts beyond these. `quiet` is the Phase 2 model
# untouched and is the regression baseline; `forecast` is NOAA's three-day forecast with the
# 27-day outlook beyond it; `replay:<date>` reruns the observed record of a historical window.
SCENARIO_QUIET = "quiet"
SCENARIO_FORECAST = "forecast"
SCENARIO_REPLAY_PREFIX = "replay"

# Where the linear theory stops meaning anything. The derivation holds the semi-major axis
# fixed while it integrates the mean-motion drift, so it is valid while the orbit has barely
# moved. Two limits, and a shift that breaks either is reported with its number and a flag
# rather than quietly trusted:
#
#  - the decay the scenario implies over the window, as a fraction of the semi-major axis.
#    One part in a thousand of 6,800 km is 6.8 km of altitude, which is already a large
#    unmodelled decay for a week and near where the numerical check's error starts growing.
#  - the displacement itself, as a fraction of the orbit's circumference. Past a quarter of a
#    revolution "the object is ahead by s" has stopped being a small perturbation of a known
#    position, and past a full one it is not a position statement at all.
#
# The demo run's G5 scenario puts high area-to-mass debris at 300 km past both by orders of
# magnitude -- those objects would be re-entering, not conjuncting -- so the flag is what keeps
# a faithful extrapolation from being read as a prediction.
STORM_MAX_DECAY_FRACTION = 1e-3
STORM_MAX_SHIFT_REVOLUTIONS = 0.25

# ---------------------------------------------------------------------------------------
# Phase 3 Step 4: the two validation storms. See docs/storm-validation.md.

# The May 2024 Gannon storm. The main phase ran from the sudden commencement late on 10 May
# through 11 May with a long recovery; Kp reached 9- for the first time since November 2003.
# The storm window is the three days over which the drag enhancement is unambiguous.
GANNON_STORM_WINDOW = ("2024-05-10T00:00:00Z", "2024-05-13T00:00:00Z")
# The quiet control. Late April 2024 was not perfectly quiet -- nothing in solar cycle 25's
# maximum is -- but Kp stayed at or under 4 across it, and it is close enough in time that the
# solar flux and the objects' altitudes are nearly the same, which is what the control needs.
GANNON_QUIET_WINDOW = ("2024-04-25T00:00:00Z", "2024-04-28T00:00:00Z")
# The pivots: the last instant an element set may have been issued and still count as "before".
# 9 May is before the sudden commencement and after the first flares, which is exactly the
# position an operator was in.
GANNON_PIVOT = "2024-05-09T00:00:00Z"
GANNON_QUIET_PIVOT = "2024-04-24T00:00:00Z"
# The history pull that covers both windows and leaves room for a pre-storm coefficient fit.
GANNON_HISTORY_DAYS = 36
GANNON_HISTORY_END = "2024-05-25T00:00:00Z"

# The February 2022 Starlink loss. The launch's international designator; SATCAT resolves it
# to NORAD ids, including the ones that have since decayed, which is the point.
STARLINK_2022_LAUNCH = "2022-010"
STARLINK_2022_HISTORY_END = "2022-03-20T00:00:00Z"
STARLINK_2022_HISTORY_DAYS = 45
# The storm was a G1: a minor one, which is what makes it the harder test. The insertion
# altitude SpaceX flew, and the shell the survivors were raised to.
STARLINK_2022_INSERTION_KM = 210.0
STARLINK_2022_CONTROL_KM = 500.0
STARLINK_2022_STORM_DAY = "2022-02-04T00:00:00Z"
STARLINK_2022_QUIET_DAY = "2022-01-25T00:00:00Z"

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
