"""Density and drag: NRLMSIS along an orbit, and a ballistic coefficient per object.

Phase 3 Step 2. :mod:`driftwatch.drag.density` turns the space weather table into the exact
inputs NRLMSIS 2.1 wants and evaluates it along a propagated orbit;
:mod:`driftwatch.drag.ballistic` turns an object's own decay into the coefficient that
converts a density into an acceleration, cached across runs by :mod:`driftwatch.drag.store`.
Step 3 multiplies the two into an in-track displacement.
"""

__all__ = ["ballistic", "density", "store"]
