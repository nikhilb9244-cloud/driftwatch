import numpy as np

from driftwatch.catalogue.classify import altitude_band, altitude_bands, categorise


def test_categorise_rules():
    assert categorise("ISS (ZARYA)", "PAY", ["active", "stations"]) == "station"
    assert categorise("STARLINK-1234", "PAY", ["active", "starlink"]) == "starlink"
    assert categorise("STARLINK-9999", "PAY", ["active"]) == "starlink"  # name alone is enough
    assert categorise("ONEWEB-0123", "PAY", ["active"]) == "oneweb"
    assert categorise("KUIPER-00010", "PAY", ["active"]) == "constellation"
    assert categorise("FLOCK 4X-12", "PAY", ["active"]) == "constellation"
    assert categorise("SENTINEL-2A", "PAY", ["active"]) == "payload"
    assert categorise("IRIDIUM 33 DEB", "DEB", ["iridium-33-debris"]) == "debris"
    assert categorise("STARLINK-30 DEB", "DEB", ["starlink"]) == "debris"  # debris beats the name
    assert categorise("FALCON 9 R/B", "R/B", ["last-30-days"]) == "rocket_body"
    assert categorise("OBJECT A", "UNK", ["last-30-days"]) == "unknown"
    assert categorise("OBJECT B", None, []) == "unknown"


def test_altitude_band_rules():
    assert altitude_band(400, 420, 0.001) == "leo"
    assert altitude_band(1950, 1999, 0.003) == "leo"
    assert altitude_band(20000, 20200, 0.005) == "meo"
    assert altitude_band(35700, 35800, 0.0001) == "geo"
    assert altitude_band(500, 39000, 0.7) == "heo"
    assert altitude_band(600, 3000, 0.15) == "other"  # crosses LEO ceiling without being HEO
    assert altitude_band(36500, 36600, 0.0) == "other"  # graveyard
    assert altitude_band(float("nan"), 400, 0.0) == "other"


def test_vectorised_bands_agree_with_scalar():
    perigee = np.array([400, 1950, 20000, 35700, 500, 600, 36500, np.nan])
    apogee = np.array([420, 1999, 20200, 35800, 39000, 3000, 36600, 400])
    ecc = np.array([0.001, 0.003, 0.005, 0.0001, 0.7, 0.15, 0.0, 0.0])
    vec = altitude_bands(perigee, apogee, ecc)
    for k in range(len(perigee)):
        assert vec[k] == altitude_band(perigee[k], apogee[k], ecc[k])
