"""The storm term: what an unmodelled density excess does to where an object is.

Phase 3 Step 3. :mod:`driftwatch.storm.term` derives and applies the in-track displacement a
density excess produces and the uncertainty on it; :mod:`driftwatch.storm.scenarios` builds
the space weather each named scenario runs under and turns it into a covariance model the
``risk`` command can be handed.

Nothing here rescreens. A scenario changes where the two objects are at the stored time of
closest approach and how uncertain that is, and the probability is recomputed from the
geometry Phase 2 already stored.
"""

__all__ = ["scenarios", "term"]
