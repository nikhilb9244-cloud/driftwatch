"""Uncertainty and probability of collision (Phase 2, Step 3).

``covariance``  the injectable covariance model: the protocol, the empirical power-law fit
                from element-set consistency, the pooled fallback and the default prior;
``manoeuvre``   the three-valued manoeuvre flag and the semi-major-axis jump detector;
``pc``          probability of collision on the encounter plane: Foster's polar-grid
                integration, Alfano's one-dimensional form, Chan's series, the
                covariance-scale sweep for the maximum probability, and the flags;
``scenario``    runs a covariance model and the probability over stored events, once per
                scenario, without touching the geometry;
``kelvins``     the reproduction of ESA's Kelvins Collision Avoidance Challenge risk column.

Nothing is imported here on purpose: ``screening.stages`` uses ``manoeuvre`` and
``covariance`` uses ``screening.ric``, and an eager import in this package would turn
that into a cycle.
"""
