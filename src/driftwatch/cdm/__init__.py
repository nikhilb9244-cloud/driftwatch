"""CCSDS Conjunction Data Messages: parse them, match them to driftwatch events, report the difference.

A CDM is what an operator actually receives when somebody else's screening finds a close
approach to their spacecraft -- from the 18th/19th Space Defense Squadron, from ESA's Space
Debris Office, from a commercial provider. It names the two objects, the time of closest
approach, the miss distance and its components, both covariances and usually a probability. It
is therefore the only ground truth a public-data screening can be measured against **for the
events an operator was warned about**: match each CDM to the driftwatch event of the same pair
within a time tolerance, and read off which warnings public data found, at what miss and what
probability, and which public-data flags the operator never received.

The parser (:mod:`driftwatch.cdm.parse`) reads the standard's two forms, KVN and XML (CCSDS
508.0-B-1). The matcher (:mod:`driftwatch.cdm.match`) joins on the unordered object pair and the
time of closest approach, many messages to one event, because an operator receives several
messages about one conjunction as its time approaches. The Kelvins adapter
(:mod:`driftwatch.cdm.kelvins`) turns ESA's anonymised challenge rows -- which are CDMs with
the identities removed -- back into messages, so the whole path is exercised against real
operational numbers before a real message from a real operator has arrived.

The submodules are imported by name (``from driftwatch.cdm import parse as cdm_parse``); the
function that reads either form is re-exported here as :func:`parse_cdm` so that the module
``parse`` is not shadowed by a function of the same name.
"""

from driftwatch.cdm.match import MatchResult, match_cdms
from driftwatch.cdm.parse import CdmObject, ConjunctionDataMessage, load_cdms
from driftwatch.cdm.parse import parse as parse_cdm

__all__ = [
    "CdmObject",
    "ConjunctionDataMessage",
    "MatchResult",
    "load_cdms",
    "match_cdms",
    "parse_cdm",
]
