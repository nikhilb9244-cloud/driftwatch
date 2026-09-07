# Remaining validation and scope

The software screens public orbital products and supports local comparison of supplied files.
It performs no independent orbit determination and has no operational adoption evidence.

The measured calibration covers Swarm A/B/C, one orbit class at approximately 460 and 506 km,
three windows and two storm periods. The covariance measures consistency, not accuracy.
The October window contains two disturbed intervals; it is not a single isolated storm.
The 25 km horizon results establish no operating horizon for another spacecraft.

Remaining evidence includes calibration on debris, higher orbits and less frequently tracked
objects; independent validation of warning completeness; real CDM comparisons; receiver logs;
and a real contact-request week with an accepted baseline. The CDM reconciler and planner ship
no real example because those inputs are absent. No organisation has adopted the software or
agreed to be named as a prospective customer.

A flight-dynamics workflow compares two orbit products with the same declared reference and
manoeuvre exclusions. A station-engineering workflow compares refresh policies using measured
acquisition records and explicit feasibility constraints. Neither workflow has produced
operational validation or willingness-to-pay evidence in this repository.

The Office of Space Commerce conjunction dataset comparison remains unperformed. Kelvins checks
probability arithmetic on supplied encounter inputs; it does not validate catalogue screening,
driftwatch's covariance or real warning recall. A fitted hard-body-radius lookup is an approximation.

Quiet applies no storm displacement. Any future adjustment of storm magnitude requires a
separate fitting population and held-out evaluation. The current term hurts the quiet 1–6 day
sample and May 12–72 hour sample, while helping October 6–120 hours. A universal short-lead
improvement or failure claim is unsupported. Forecast skill requires archived forecast issue
times; a hindcast with observed weather cannot establish it.

Local application network guards do not establish security certification or operating-system
isolation. Second-computer installation, real-handset, other-browser-engine, browser-zoom and
assistive-technology evaluation remain incomplete. Synthetic tests establish specified software
behaviour, not operational utility. Export previews and download requests do not prove that an
operating-system save completed. No hardware command path, service guarantee, payment system or
multi-user deployment is provided.

Current limitations and corrections are in [methods.md](docs/methods.md) and
[findings.md](docs/findings.md).

_Last updated 7 September 2026._
