"""The radio lane: satellite crossings of a dish's beam over the Karoo, with the accuracy attached.

Four modules. ``site`` is the place and the beam: the MeerKAT array centre, its receivers and
the half-power width of a 13.5 m dish at each frequency, plus the geometry that turns an
orbit into an elevation, an azimuth and an angle from the boresight. ``emissions`` is the table
of declared satellite emissions by band, from public regulatory filings, and the rule that says
which catalogued object belongs to which constellation. ``horizon`` converts the calibration
benchmark's radial, in-track, cross-track residuals into angles on the sky and computes the
radio horizon table. ``crossings`` runs the two products for an observation on the catalogue as
it stood at the observation's start, and ``report`` writes the period reports and the
machine-readable export in the shape of the IAU SatChecker field-of-view response.

Everything here is computed from public data and reported with its population and its limits.
No received power, occupancy fraction or sensitivity loss is stated anywhere: those need a
measurement, and the statistics have been modelled elsewhere.
"""
