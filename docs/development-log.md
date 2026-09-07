# Development log

The working record: dated verification runs, test counts, browser and viewport sweeps, and the
checks behind each change. It is kept separate from the public pages, which describe the software,
its measurements and its limits rather than the process that produced them.

Limits of the *software* stay on the public pages. What appears here is the record of what was
checked, when, and what the check could not reach.

## The local workspace — verified 6 September 2026

The complete Python regression suite passed: **577 tests**. TypeScript typechecking, Ruff checks/formatting and the Vite production build passed. Live requests against the rebuilt local workspace exercised orbit comparison and contact prediction against real Space-Track element sets, model evaluation against the measured Swarm benchmark, and input inspection against those same files. CDM reconciliation and contact planning were exercised only on inputs constructed for the check, which are not shipped; neither has been run on real conjunction messages or a real request week. The scheduler was also compared against exhaustive feasible subsets; exchange-format tests verify equivalent trajectories and explicit metre-to-kilometre conversion. The existing large-globe-bundle and satellite.js browser-externalisation build warnings remain.

Browser checks exercised two actual OEM file selections and a local comparison, the synthetic CDM comparison, receiver-log matching, one-antenna planning, evidence answer feedback, model-window selection, trace controls and Earth detail settings. Responsive checks included 390 × 844 and 1024 × 768 viewports with no horizontal page overflow, and a fully visible mobile export dialog. Temporary viewport and rendering preferences were restored after testing. Contact times now display to the nearest second while result exports retain the engine's original precision. Earth captions use a dark backing to remain readable over bright imagery.

The export preview and manual selection were checked with a **72,211-character JSON report**: all characters were selected and the complete text parsed as JSON, beyond the initial preview limit. The embedded browser did not provide a confirmed saved download, and automatic clipboard access was unavailable on a later check; manual selection is verified, not a claim of a completed operating-system save. Final TypeScript typechecking and the production build passed after these interface fixes. A second-PC installation trial, assistive-technology audit and observation by a prospective user remain outstanding.

Resizing also exposed a stale resolution caption: the globe library applies dimensions asynchronously. The caption now observes the canvas width/height changes, and the displayed dimensions were checked against the actual canvas after mobile reflow and restoration to desktop size.

The subsequent schedule-review extension passed **31 targeted Python tests** covering the planner, imports and local API. Tests compare protected-contact optimisation and minimum-change ties against exhaustive feasible subsets, verify decimal priority ties, exact turnaround boundaries, ambiguous flags and infeasible baselines. This is a focused regression after the earlier full-suite run, not a new claim that the full suite was rerun.

Browser verification of that extension imported, through the PC file chooser, a CSV constructed for the check and not shipped: protecting the current plan returned **Keep the current schedule**, and conflicting commitments returned a named error. Changing a file or turnaround clears the previous review and its export controls. The comparison JSON contained the baseline, changes and source/request fingerprints; the selected-contact CSV contained exactly SHORT-B, SHORT-C and FOLLOW-D. Its export contents were checked in the preview; operating-system download completion remains unconfirmed. Desktop and 390 × 844 visual checks passed after containing a wide decision table within its scroll panel. The final TypeScript check and production build passed; existing bundle warnings remain.


## The catalogue viewer — 6 September 2026

The catalogue page shares the workspace's Earth and was finished after it. What follows is what was measured, in headless Chromium against the production build, and what was not.

**Earth in portrait.** globe.gl frames the sphere with a fixed 50° *vertical* field of view, so on a portrait screen the limiting angle is the horizontal one, atan(aspect · tan 25°), and the altitude that fits Earth on a landscape screen crops both limbs on a portrait one. The home altitude scales with height over width for that reason. It was applied once, at load, and never again — so rotating a phone from landscape to portrait carried the landscape altitude into a portrait aspect: at 844 × 390 the altitude is the 2.4 floor, and 2.4 under a 390 × 844 aspect draws a 557 px disc across a 390 px viewport, 84 px off each side. The resize handler now re-fits, scaling the current altitude by the ratio of the new home altitude to the old so that a deliberate zoom moves with the screen instead of being discarded. Three rotations were measured — 844 × 390 → 390 × 844, its reverse, and 1440 × 900 → 390 × 844 — and in each the rendered result is now identical to a fresh load at the destination size.

**Layout.** Forty viewports from 320 × 480 to 2560 × 1440, each in four states — plain, plain with a panel open, replay, replay with a panel open: **160 checks**. Each one tests every pair of the wordmark, the workspace link, the navigation, the headline, the chart, the transport, the zoom buttons and the panel for overlap; hit-tests the centre of every visible control with `elementFromPoint` to catch a control that is placed correctly but painted under something else; checks the document for horizontal overflow; and checks that the headline, the zoom buttons, the navigation and the transport are actually present rather than merely un-overlapped. All 160 are clear.

They were not. At 844 × 390 in replay the navigation sat over the wordmark by about 22,000 px² and the zoom buttons sat behind the chart. A phone held sideways has around 390 px of height and the masthead, navigation, chart and transport want more than that between them, so the chart is now capped from the viewport height — the cap is chosen so the navigation's top edge lands 92 px down whatever the height — and it keeps `overflow: auto`, so the Kp legend and the SDO citation stay reachable by scrolling inside it rather than being dropped.

**The first fix was worse in places, and an overlap test could not see it.** Keying the short-viewport rules on width and height alone caught portrait phones too: at 360 × 640, 320 × 568 and a 600 × 650 window the page lost its only `<h1>` and all three Earth buttons to a rule written for a phone held sideways, on a screen with 240 px of clear space between the masthead and the navigation. Nothing overlapped, so nothing was flagged. The rules are now keyed on shape as well as size — `min-aspect-ratio: 1/1` separates the two cases — and the suite asserts presence and hit-testing, not just non-overlap. The same pass found the zoom row painted under the navigation between 601 and 659 px wide (a click on `+` reached the navigation's third button) and under the open panel up to 683 px, neither of which an overlap-only check on four viewport widths would have reached.

**The floors, and what is lost at each.** Below 660 px wide in landscape the navigation's 466 px and the zoom row's 146 px do not both fit between the margins, so the zoom buttons go; in portrait below about 540 px of height in replay the column cannot fit between the masthead and the navigation once the chart has its band, so they go there too. Drag, pinch, the scroll wheel and the arrow and `+`/`−` keys all still zoom, so what is lost is the visible control, not the capability. Below about 340 px of height the chart's cap is smaller than its own padding — at 568 × 320 the masthead is 69 px, the navigation 69 and the transport 142, which is 292 of the 320 before the chart asks for anything — so the chart and the headline are dropped rather than shown as slivers, and an open panel takes the transport's space instead of covering its controls. Replay still works there: the clock reads replay time and the slider scrubs the storm window. But its weather chart is not on screen and nothing says so. That is a stated limit, not a solved problem.

**Replay preserves the panel.** Entering and leaving replay keeps the open panel (the replay button lives inside *About the data*, and the reader stays there), the selected object where the other catalogue holds it, the position through the window, the speed and the filters. Verified at 1440 × 900 and 390 × 844, in both directions, and through the Back and Forward buttons. Focus did not survive it: the button disables itself while the catalogue loads, which blurs it to `<body>`, and a reader who pressed Enter on *Replay May 2024* was left at the top of the document with the catalogue changed under them. It now takes focus back when focus is still where the disable dropped it, so pressing Enter twice enters and leaves replay; a reader who clicked with a mouse and moved on during the load keeps where they went.

**Keyboard.** With playback paused so that camera motion could be told from the objects' own, the arrow keys and `+`/`−` were confirmed to move Earth while it holds focus, and to do nothing once focus has left it. Space pauses only from the document body or Earth: it types a space in the search box and activates a focused button, as it should. Modified keys are now left to the browser, so Ctrl/Cmd with `+`/`−` still zooms the page and Alt/Cmd with an arrow still navigates history. Escape returns focus to the control that opened the panel, and to Earth when the panel was opened by a selection rather than by a button. *Deselect* hands focus to the search box instead of dropping it with the section it hides. The storm control no longer mirrors its breakpoint into `aria-hidden`: the stylesheet already gives the unused control `display: none`, which removes it from the accessibility tree, and the mirror both disagreed with the stylesheet at exactly 900 px and put `aria-hidden="true"` on a focusable `<select>`.

**Names.** Fleet members are named. The bundle previously carried `payload 55053` for everything but a station, pending an operator's agreement to appear, and the viewer had begun substituting the catalogue's name back in — two rules disagreeing in two languages. It is now decided once, in the exporter: `objects.json` ships all 32,372 catalogue names keyed by NORAD id and every pair carries `primary_norad_id`, so the two join in a line and the rule withheld nothing while costing the reader the one label that says which encounter they are looking at.

**Not done.** Every measurement above is headless Chromium at a set viewport size. No real handset, no real orientation change, no touch, no assistive technology, no browser zoom, no other engine. A device-pixel-ratio of 1 was used throughout, so the rendering-detail selector's behaviour on a real 3× screen is untested. The camera re-fit has one known interaction it does not handle: a resize arriving during the 700 ms flight of *Centre on object*, or the 400 ms of *Reset Earth view*, ends that flight where it had got to rather than at its destination, because the re-fit reads the camera's current position and the setter cancels the tween. Rotating a phone mid-flight therefore stops the globe part-way and the button has to be pressed again. None of this establishes that the page is usable, only that the elements do not overlap, that the controls receive their own clicks, and that nothing the reader needs has been hidden.


## Removal of the constructed demonstration inputs — 7 September 2026

The workspace shipped four constructed examples: an OEM carrying a displacement chosen by the
generator with a candidate at exactly 0.4 times it, two CDMs carrying probabilities chosen by the
generator, a receiver log whose lock times were placed a fixed 35 seconds after the predicted
acquisition, and a five-row contact-request table with invented satellite names. They were removed,
together with the generator that wrote them and every figure quoted from them.

Two examples replaced them, both measured or published data:

* **Orbit comparison, Swarm A (NORAD 39452).** ESA's reduced-dynamic precise science orbit for
  13 May 2024 as the reference, against two Space-Track `gp_history` element sets for the same
  satellite, epochs 2024-05-12T20:57:24Z and 2024-05-06T14:26:27Z. Median position difference
  0.54 km for the three-hour-old set and 32.8 km for the six-day-old one, over 1,440 samples at
  60-second spacing with no missing samples. ESA's thruster record shows no orbit-control thrust in
  the window, so nothing was excluded.
* **Ground contacts, ISS (NORAD 25544).** Two Space-Track element sets, epochs 2024-05-10T20:04:09Z
  and 2024-05-04T05:00:00Z, over IGS station HRAO00ZAF. Three passes on 11 May 2024, peak
  elevations 10.2, 38.6 and 57.0 degrees. The two sets are 9.07 km apart at the first acquisition
  and predict acquisition times about 1.3 seconds apart — a result about this object over this day,
  not a general finding about refresh policy.

The conjunction-message tool and the contact planner were left with no example, because no real
input for either exists in the repository.

The constructed inputs were not deleted outright: they moved to `tests/workspace_fixtures.py`,
where a displacement chosen by the test is what lets a test assert that the engine measures the
displacement it was given. `driftwatch check-bundle` now refuses to publish a bundle containing
their identities or labels, and a test covers that refusal.

Checks: the full Python suite, Ruff, TypeScript typechecking and the Vite production build all
passed; `check-bundle` passed over `web/public`; and the guard was confirmed to fire on each
retired fixture identity.

## Interface checks — 6 September 2026

Browser interaction checks exercised file import and local analysis with real Space-Track element sets and the measured Swarm A/B/C benchmark, plus feedback and visual controls. The conjunction-message tool and the contact planner were exercised only on inputs constructed for the check, and have not been run on real messages or a real request week. At 390 × 844, the page had no horizontal overflow and the export dialog remained within the viewport. Bright Earth imagery exposed a caption contrast problem; captions now have a dark backing. Export controls offer a preview and manual selection of the entire report when automatic clipboard access is unavailable. Contact timestamps display to seconds; exports retain the engine's precision. These checks do not replace observation of a prospective user. Browser zoom, colour-vision simulation, assistive-technology testing and a second-PC installation trial remain outstanding. No usage analytics or tracking has been added.

_Last updated 7 September 2026._
