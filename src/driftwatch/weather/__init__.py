"""Space weather: what drives the density, and where each number came from.

Three sources, one table. CelesTrak's ``SW-All.csv`` is the record: three-hourly Kp and ap
back to 1957, daily F10.7, and predicted F10.7 forward to 2041. NOAA SWPC supplies what
CelesTrak does not predict — Kp for the next three days and the 27-day outlook — and the
solar wind and real-time K index for context. :func:`~driftwatch.weather.table.weather_table`
merges them into one row per three-hour interval, and **every row says where it came from**:
``observed``, ``forecast`` or ``synthetic``, with the forecast's issue time beside it.

The provenance column is the point. A density model driven by observed ap for a past window
and by a three-day forecast for a future one is doing two different things, and a storm
scenario built from a scaled May 2024 profile is doing a third. The table refuses to let
them be confused.
"""
