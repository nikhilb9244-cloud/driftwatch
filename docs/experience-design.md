# Experience design — 6 September 2026

The direction is an orbital analysis instrument: deep ink, electric lime, cyan measurement traces, restrained amber for unresolved conditions and the existing Earth. This is a design judgement aimed at distinctiveness and legibility, not proof that colour will make someone buy the product.

## Research translated into behaviour

- **Colour is contextual.** Elliot's review describes interactions between colour, meaning and context; it does not justify universal claims such as “blue creates trust”. An operator sees labelled series and explicit warnings. Lime identifies the main action and selected items; cyan provides a second measurement channel. Outcomes also have words and numbers. [Colour and psychological functioning, Frontiers in Psychology](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00368/full).
- **Hierarchy directs attention.** Scale, contrast, grouping and spacing distinguish the work surface from supporting detail. Earth and the comparison dominate; tolerance stays beside the period selector, with statistics immediately below. Navigation uses functional vector symbols rather than arbitrary numbered tiles. [NN/g visual hierarchy](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/).
- **Reveal detail when needed.** A flight-dynamics engineer can inspect measurements, provenance and column mapping without those controls competing with the first comparison. Scientific explanations remain expandable. Unsupported conventions fail with an actionable message. [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/).
- **Measure successful use separately from appearance.** Attractive interfaces can mask usability failures. Observe whether a prospect imports their data, explains the reference correctly, changes a decision and exports evidence without coaching. Compliments alone do not pass the commercial gate. [NN/g aesthetic-usability effect](https://www.nngroup.com/articles/aesthetic-usability-effect/).
- **Accessibility constrains the palette.** Keyboard focus is explicit, controls have text alternatives, trace switches expose pressed state, tables retain exact chart values and motion respects device preference. Main buttons are at least 42 CSS pixels high; scene controls at least 32. [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Palette and resolution

Calculated solid-colour contrast ratios: body text/background 17.48:1; muted text/panel 8.07:1; primary button text/lime 13.36:1; cyan/panel 11.50:1; amber/panel 11.27:1; input border/background 3.21:1. These are token checks, not a full accessibility audit. Rendered combinations still require user testing.

Earth source imagery remains **4096 × 2048**. Antialiasing, vector charts/icons, higher device-pixel rendering and a detail selector are the levers on rendered sharpness; the resulting sharpness has not been measured, and the selector was exercised only in headless Chromium at a device-pixel ratio of 1, so its behaviour on a real 2× or 3× screen is untested. Auto uses the device ratio capped at 2×, High requests 2.5× and Low power uses 1×, all bounded to about eight million canvas pixels. The app reports actual rendered dimensions. Higher rendering resolution cannot recover surface detail absent from the image; this is not an 8K texture claim. Local analysis loads no external images or fonts.

Traces can be individually hidden, and keyboard-operable controls rotate Earth. Nothing auto-spins or invents a live satellite state. Historical tracks retain dates; scenes without coordinates identify themselves as context only.

## Adoption tasks

| Person | Task to observe | Evidence of improvement |
| --- | --- | --- |
| A flight-dynamics or ground-software engineer comparing two orbit products | Import reference and prediction, inspect conventions, identify a discrepancy and save evidence | Correct interpretation without the frame, or whether the reference is truth, being explained alongside |
| A station engineer testing an orbit-refresh policy | Import feasible requests, set priorities and turnaround, explain an excluded contact | A changed accepted contact set, or a demonstrated reason the fixed-turnaround model is insufficient |
| A researcher evaluating a drag or storm correction | Compare paired baseline/candidate trials and identify where a correction stops helping | A restricted or rejected model claim, with observed weather distinguished from forecasts |
| An instructor teaching evidence quality | Ask a trainee to distinguish clock and frame errors from unsupported attribution | The trainee records missing evidence and revises the claim |

Keyboard focus is explicit, controls carry text alternatives, trace switches expose their pressed
state, tables retain the exact values behind every chart, and motion respects the device's
reduced-motion preference. Browser zoom, colour-vision simulation and assistive-technology testing
have not been done. No usage analytics or tracking has been added.

_Last updated 7 September 2026._
