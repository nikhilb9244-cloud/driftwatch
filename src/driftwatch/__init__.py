"""driftwatch: conjunction screening for low Earth orbit under geomagnetic storms.

Phase 1 provides the catalogue pipeline: fetch CelesTrak element sets, snapshot them to
parquet, propagate with SGP4, convert frames, and export a bundle for the web viewer.
"""

__version__ = "0.1.0"
