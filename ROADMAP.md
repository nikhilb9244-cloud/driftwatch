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

The radio lane ([docs/radio-lane.md](docs/radio-lane.md)) turns the benchmark's residuals into
angles on the sky for one 13.5 m dish and runs two geometric products on the catalogue as it
stood. It computes no received power, occupancy or sensitivity loss, ingests no schedule beyond
an observation CSV, and ran on one public observation record. Validating a crossing list needs
the observatory's own monitoring data, and the archive's observation list needs an account;
neither exists in this repository. No organisation has asked for this or agreed to be named.

The reference expansion ([docs/reference-benchmark.md](docs/reference-benchmark.md)) extends the
calibration benchmark from Swarm to every public reconstructed orbit an anonymous server hands out
for spacecraft between 460 and 1,340 km, adds laser ranging as a second truth and a fourth,
disturbed window in August 2024, and states which missions asked for are not obtainable without an
account. The dSGP4 evaluation ([docs/dsgp4-evaluation.md](docs/dsgp4-evaluation.md)) runs ESA's
differentiable SGP4 and its ML-dSGP4 hybrid on the same trials, trained on the tuning-visible
windows only, with adoption decided by the held-out storms.

## Next candidates, recorded and not begun

None of these begins until the expanded reference benchmark exists and the outreach replies are in.
Each carries the label it would wear on every page, and the validation rule it must pass before
anything downstream may cite it.

1. **Covariance realism modelling.** Label: *storm-conditional covariance scale*. A scale on the
   empirical covariance as a function of the observed ap over the propagation, fitted so that the
   68 and 95 per cent contours contain what they claim. Validation rule: fitted on the May 2024
   window only; scored on October and August 2024, held out, per altitude band, by the coverage
   table of the reference benchmark; adopted only if the held-out two-sigma coverage moves toward
   95 per cent in every band without the quiet week's falling.
2. **Density correction from catalogue decay.** Label: *catalogue-decay density ratio*. The ratio
   of the density the free-flying population's own decay implies to NRLMSIS 2.1's, per three-hour
   interval, as a correction to the storm term's density. Validation rule: measured on the May 2024
   storm; validated on October and August, held out, by the storm term's improvement table of the
   reference benchmark; the untuned NRLMSIS prior stays the default until the held-out improvement
   is positive at three days and beyond and not negative inside two.
3. **Manoeuvre classifier.** Label: *burn or drag, by record*. A classifier that separates a
   manoeuvre from storm drag in an element-set jump, trained on the published thruster records
   (Swarm, GRACE-FO) and the precise-orbit steps. Validation rule: trained on quiet and May; scored
   on October and August against the published records (recall and false alarms per
   satellite-day) and against the count of storm-time trials it would exclude, which is the
   detector's known failure; adopted only if it excludes no storm-time interval the record keeps.
4. **Coefficient regression.** Label: *ballistic coefficient from the fit, not the decay*. A
   regression from the catalogue's fit parameters (B\*, the mean-motion derivatives, altitude,
   object class) to the coefficient measured from decay, for objects whose decay is not measurable.
   Validation rule: fitted on objects with a measured coefficient in the quiet window; scored by the
   storm term's improvement in the held-out windows of the reference benchmark, per altitude band;
   adopted only if the term with the regressed coefficient improves the held-out storms where the
   measured one did.

Current limitations and corrections are in [methods.md](docs/methods.md) and
[findings.md](docs/findings.md).

_Last updated 7 September 2026._
