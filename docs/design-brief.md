# Design brief: the Phase 4 visual pass on the viewer

A parked design document. Nothing here is built yet and nothing in `web/src` changes on
account of it. It exists so that when Phase 4 opens, the visual decisions have already been
argued and the reading of four other projects has already been done.

What the viewer is today: one `THREE.Points` object for the whole catalogue over a globe.gl
sphere, a category filter, a conjunction list, two ten-minute tracks either side of a
selected event, and an SVG encounter-plane inset with a hard-body disc, one and three sigma
ellipses and the miss vector. It is legible and it is fast. What it is not yet is an
*instrument*: everything is drawn at the same weight all the time, and nothing on the screen
tells you what the atmosphere is doing.

## What was read, and what may be taken from it

| Project | Licence | What it does | What is safe to take |
| --- | --- | --- | --- |
| [KeepTrack.space](https://github.com/thkruz/keeptrack.space) | **AGPL-3.0-or-later**, and `KeepTrack™`/`KeepTrack.space™` are trademarks of Kruczek Labs LLC | WebGL 2 + custom GLSL, 50,000 objects, colour schemes by type/country/velocity, sensor cones, time machine, satellite trail mode | **Ideas only.** No code, no assets, no name. See the note below. |
| [Flowm/satvis](https://github.com/Flowm/satvis) | MIT | CesiumJS + Vue, ~12,000 objects, pass prediction, PWA, a Cloudflare Worker that caches CelesTrak element sets in KV | Architecture lessons, and one hard operational warning (below) |
| [ut-astria/AstriaGraph](https://github.com/ut-astria/AstriaGraph) | GPL-3.0 | Cesium, fuses Space-Track, JSC Vimpel, SeeSat-L and UCS; 7-pixel points coloured by class; orbit polyline drawn **only for the selected object** | The on-demand-orbit idea, and the fused-source provenance idea |
| [cambecc/earth](https://github.com/cambecc/earth) | Learning project, SVG map + two stacked canvases | Wind particles animated over a projected globe; the field is a canvas that is faded rather than cleared | The trail technique, near enough verbatim in spirit |

### The AGPL and the trademark

KeepTrack is licensed AGPL-3.0-or-later, and its README is explicit that **network use counts
as distribution**: a modified version served as a web page has to ship its source. driftwatch
is not AGPL and is not going to be. So nothing may be copied from it — not a shader, not a
colour table, not a layout constant, not a snippet of its orbital library. Its README also
states that *"KeepTrack™ and KeepTrack.space™ are trademarks of Kruczek Labs LLC"*, so the
name does not appear in our UI, our docs beyond this citation, or our commit messages as an
attribution.

What is *not* restricted is the observation that a satellite viewer benefits from a trail
mode, from selection dimming the rest, and from colour schemes the user can switch. Those are
ideas, and ideas about how to arrange a screen are not what a copyright licence covers. Every
concrete number in this brief — every hex value, every alpha, every millisecond — is derived
below from our own palette or from first principles, and none of it is read off theirs.

### satvis's warning, which changes the Phase 4 pipeline

satvis serves CelesTrak element sets through a Cloudflare Worker on a six-hourly cron into
Workers KV. That arrangement has a failure mode worth writing down before we build the same
thing: **CelesTrak firewalls by IP, and Cloudflare Worker egress addresses are shared between
tenants.** A Worker's fetches can therefore start returning HTTP 522 on every source while the
same URLs answer instantly from anywhere else, because some other tenant on the same egress
address earned the block. satvis's way out is a `push-gp` path that runs the worker's own
download logic somewhere else — a CI runner, a VPS, a laptop — and POSTs the payloads to an
ingest endpoint.

**The consequence for us.** The Phase 4 scheduled pipeline must fetch from a machine whose IP
we control: a GitHub Actions runner (as the supplemental fetch already does — see
`scripts/register-supplemental-task.ps1` and the Step 0 close-out) or our own host. A
Cloudflare Worker or Pages Function may *serve* the bundle; it must never be the thing that
fetches from CelesTrak or Space-Track. This also protects the two-hour minimum fetch interval
in `config.MIN_GROUP_FETCH_INTERVAL`, which is a courtesy we can only honour if we know how
many of us there are behind the address.

## The visual pass

### 1. Selection and dimming

Today every point is drawn at full weight, so a selected object is a slightly larger dot in a
field of forty thousand identical dots. The fix is contrast, not brightness: **selection dims
everything else** rather than lighting the selection.

- Unselected points drop to about 25 % opacity and desaturate towards the background over
  roughly 180 ms. The transition is an eased uniform in the existing vertex shader — one
  `uDim` float, no new geometry, no rebuild of the buffers.
- The selected object and, for a conjunction, its partner stay at full opacity and gain a
  thin ring. Two objects, two rings, and the ring colour is the category colour so the pair's
  identity survives the dimming.
- Filtering is the same mechanism at a different setting: a filtered-out category goes to
  zero rather than to 25 %. One uniform serves both, which keeps the point cloud a single
  draw call, which is the whole reason Phase 1 hits its frame budget.
- **Nothing about this touches the propagation path.** The Phase 1 performance rule stands:
  the storm control and the selection state change uniforms and DOM, never the point buffers.

### 2. The terminator and the atmosphere rim

The globe currently shows a Blue Marble texture at uniform illumination and globe.gl's own
atmosphere at `atmosphereAltitude(0.12)`. Two changes, both of which pay for themselves in
comprehension rather than decoration:

- **A day–night terminator.** The subsolar point is a closed-form function of the simulation
  time we already hold, so this is a fragment-shader term over the globe material: full
  texture on the day side, the texture at about 15 % plus a faint city-lights layer on the
  night side, and a soft band a few degrees wide across the terminator. It matters here more
  than in a general tracker because **density is a local-solar-time story**: the diurnal bulge
  is a factor of two to six between day and night at these altitudes (see
  `docs/density-and-drag.md`), so a reader who can see where noon is can see why an object's
  drag is doing what the panel says.
- **An atmosphere rim that means something.** Rather than a decorative glow, the rim is scaled
  to the altitude band the storm term is about: a thin shell from the surface to about 1000 km
  with opacity falling as the density does, roughly exponentially with a 50 km scale height.
  In replay it brightens with the storm — the same quantity the density field shows, seen
  edge-on. This makes the atmosphere the thing that changes when the Kp bar moves, which is
  the single clearest way to say what a geomagnetic storm is.

### 3. Fading trails, not persistent orbit lines

AstriaGraph draws a polyline only for the object you clicked; everything else is a bare point.
That is the right instinct and Phase 4 should go one step further, because a full orbit line
answers "where will it go" while a trail answers "where has it been and how fast", and at
conjunction scale the second question is the one being asked.

The technique is cambecc/earth's, which is worth stating precisely because it is
counter-intuitive: the trail layer is a canvas (here, a render target) that is never cleared.
Each frame it is composited with itself under `globalCompositeOperation = "destination-in"`
and a fill of `rgba(0, 0, 0, 0.95)`, which multiplies the whole buffer's alpha by 0.95 and so
decays every trail exponentially; the new points are then drawn over it. earth uses
`MAX_PARTICLE_AGE = 100` frames at `FRAME_RATE = 40` ms and a line width of 1.

Translated to our scene at 60 fps:

- An alpha multiplier of 0.95 a frame is a 1/e length of about 20 frames — a third of a
  second, too short. **0.985 gives about 66 frames, a little over a second**, which at our
  default time compression is a few minutes of orbit: enough to read direction and speed,
  short enough that forty thousand of them do not turn the globe white.
- Trails are drawn for **selected and filtered-in objects only** at first. A trail for every
  catalogue object is the visual equivalent of the persistent orbit lines we are replacing.
- The trail inherits the category colour and fades to transparent, so speed reads as trail
  length and identity reads as hue, with no extra legend.
- Full orbit lines survive in exactly one place: the two ten-minute conjunction tracks either
  side of a selected event, which are not trails but a geometric claim about where the two
  objects pass. Those stay solid, and gain the 2σ tube described below.

### 4. Labels on demand

No permanent labels. Forty thousand of anything cannot be labelled, and a viewer that labels
the loudest hundred is asserting an importance order it has not earned.

- **Hover** gives the existing tooltip.
- **Selection** gives a small leader-line label anchored to the point: name, NORAD id,
  altitude. Tabular numerals (below), so the altitude does not jitter as the object moves.
- **A conjunction** labels exactly two objects, primary and secondary, and nothing else on
  screen, for as long as the event is selected.
- Labels are DOM elements positioned from the projected point, not textures in the scene:
  they are then real text for accessibility and selection, and they cost nothing in the point
  shader. At most a few dozen exist at any moment, so the projection cost is negligible.

### 5. One category palette, and the G-scale reserved

The viewer already has a category palette in `web/src/points.ts`, and it is a good one. The
rule Phase 4 adds is that **it is the only palette for objects**, and that a second, disjoint
scale is reserved for storm state and used for nothing else.

| Category | Hex | Reading |
| --- | --- | --- |
| `station` | `#ffd166` | Crewed; the one category a reader should find instantly |
| `starlink` | `#4cc9f0` | The dominant constellation, cool so it recedes in bulk |
| `oneweb` | `#b388ff` | |
| `constellation` | `#06d6a0` | Other constellations |
| `payload` | `#e8eef7` | Near-white: the default, uncoloured case |
| `rocket_body` | `#ff9f43` | |
| `debris` | `#ef476f` | |
| `unknown` | `#8d99ae` | Grey, deliberately: no claim is being made |

Storm state uses NOAA's own geomagnetic scale, which is the vocabulary every space weather
reader already has. NOAA publishes the scale as G1 Minor (Kp 5), G2 Moderate (Kp 6), G3
Strong (Kp 7), G4 Severe (Kp 8 including 9−) and G5 Extreme (Kp 9), and shows it as green,
yellow, orange, red and dark red on its conditions dial; it does not publish hex values, so
these are ours, chosen to match that ramp and to stay distinguishable at 3 px on a dark
background:

| Level | Kp | Hex |
| --- | --- | --- |
| quiet (G0) | < 5 | `#3f7d5a` |
| G1 minor | 5 | `#8bc34a` |
| G2 moderate | 6 | `#f2c14e` |
| G3 strong | 7 | `#f08c2e` |
| G4 severe | 8 | `#e04b2a` |
| G5 extreme | 9 | `#a01f1f` |

**The reservation is the point.** No object, no track, no flag and no button uses a colour
from the G ramp. When something on screen goes orange it is because the atmosphere did, never
because a satellite did. This costs us the most natural colours for a risk flag — red for a
red flag — so the conjunction flags keep their existing shape-and-weight treatment and take
their emphasis from position in the list and from typography rather than from hue.

### 6. The encounter plane as an instrument

The inset in `conjunctions.ts` is already the right picture: the hard-body disc at the origin,
the covariance ellipse about the miss, the miss vector between them, and a caption saying the
probability is the mass of the Gaussian inside the disc. The Phase 4 pass makes it read as a
gauge rather than a diagram.

- **One, two and three sigma.** Today it draws 1σ and 3σ. Three contours at 1σ, 2σ and 3σ,
  with the innermost heaviest, let a reader see where the disc sits in the distribution
  instead of interpolating between two rings. Line weights roughly 1.6, 1.1 and 0.7 px, all
  in the same hue at falling opacity.
- **Tabular numerals everywhere.** `font-variant-numeric: tabular-nums` and a monospaced
  fallback for every number in the inset and the panel. Numbers that change as you scrub a
  timeline must not change width, or the eye reads the movement as data.
- **A fixed frame.** A thin rule around the plot, tick marks in kilometres on both axes, and
  the scale stated. The current inset auto-scales silently, so two events look alike when one
  is a hundred times tighter. An instrument states its range.
- **The storm delta in place.** Under a storm scenario the inset shows the quiet ellipse as a
  faint outline and the scenario ellipse solid, with the mean in-track shift drawn as an arrow
  from one miss position to the other. That single picture is the whole of Phase 3 Step 3:
  the ellipse grows (the variance term) and the miss moves (the shift term), and the reader
  can see immediately which of the two did the work.
- **Region and confidence as text, not colour**, because of the G-scale reservation, and
  because the dilution region is a statement about what the data cannot support and deserves
  a sentence rather than a hue.

### 7. One scrubber

Replay is currently four things that would each want their own control. It gets one.

A single horizontal scrubber along the bottom of the screen, spanning the replay window,
carrying the Kp bar as its own background — so the timeline *is* the storm plot, and dragging
along it is dragging along the storm. Moving it moves, in the same frame:

1. **The Sun image**, snapped to the nearest cached Helioviewer frame, in a corner tile with
   its actual timestamp shown (it will not be the scrubber's time, and pretending otherwise
   would be a lie about provenance).
2. **The Kp bar**, whose bars are the G-scale colours, with a marker at the current time and
   the observed/forecast/synthetic provenance shown by fill style — solid for measured,
   hatched for forecast, outlined for designed. The existing `provenance` and `skill` columns
   already carry exactly this distinction.
3. **The density field**: the atmosphere rim brightness, and a small numeric readout of the
   density ratio at 400 and 500 km against the quiet baseline.
4. **The conjunction list**, filtered to events whose TCA is near the scrubber time, with the
   scenario's probabilities.

The four are one control because they are one story, and because a reader who has to
synchronise four widgets by hand will conclude the tool does not know they are related.
Keyboard: left/right by one three-hour interval, shift for a day, space to play. The scrubber
is the only new persistent chrome the storm mode adds.

---

# The operator console: a Phase 4 specification

Design only. Nothing below is built, no file in `web/src` changes on account of it, and every
number here is either derived from measurements of the current bundle (recorded below) or
stated as a budget to be met.

> **Partly built at Phase 3 Step 5 (2026-09-03), on purpose.** Step 5 needed a storm control and
> a replay, and this section had already settled what both should be, so it was built to the
> specification rather than invented twice. What exists in `web/src` now: the scenario control of
> §3.1 (a segmented control of five at desktop width, a dropdown below 900 px, full names, an
> unscored scenario shown and disabled, replay as a mode with its own control), the Δ-against-
> quiet column of §5 on every row, the unscoreable section of §5 below the queue, the encounter
> plane's quiet ellipse and shift arrow from §6.1, and the replay scrubber with the Kp bar as its
> background from §2. What does not: the status strip, the fleet band, the queue as a table, the
> reading order of §1, the layout of §2, the commandability column, and the paint budget of §8 —
> all of which are a rewrite of the viewer's shell rather than an addition to its panel, and all
> of which remain Phase 4. The parts that were built kept this section's decisions so that Phase 4
> inherits them instead of replacing them.

The visual pass above answers "how should the viewer look". This answers a different and more
important question: **what is the screen for, and in what order does a person read it.** The
Phase 1 to 3 viewer is a globe with a list attached. An operator does not open a globe. They
open a screen to find out whether anything needs doing today, and if so, to what, and by when.
The console is that screen, and the globe becomes one of the things on it.

## 1. The reading order, and why it is fixed

Three questions, always in this order, each answerable without the next:

1. **Is my fleet all right?** — the status strip and the fleet band. Answerable in about two
   seconds, without scrolling, without clicking, and without the globe having loaded.
2. **What needs action?** — the event queue. A ranked list where the top row is the most
   urgent thing and the rank means something the reader can defend.
3. **What exactly is this one?** — the detail view. Everything about a single encounter,
   including how much of it is the atmosphere and how much is the geometry.

The globe **supports step 3 and sometimes step 2**. It never leads, and it is never the thing a
reader must interact with to learn something. This is the single biggest departure from the
current viewer and the reason for the whole section: a globe is a wonderful way to show *where*
and a poor way to show *whether*, and the operator's first question is a whether.

The consequence, stated once so it governs every later decision: **the console must be
completely usable with the globe absent.** Not degraded-but-tolerable — completely usable. That
is what makes the phone layout in §7 a restriction rather than a rewrite, and it is what makes
the paint budget in §8 achievable.

## 2. Layout

Desktop, at or above 1280 px:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STATUS STRIP   Kp now 3+ · fcst 6 (G2) 12h · scenario forecast · 14 h old    │ 44 px
├───────────────────────────────────────────┬──────────────────────────────────┤
│ FLEET BAND  6 members, 3 with events      │                                  │ 72 px
│  ISS ·2   S1C ·0   XI-IV ·1   UWE-3 ·0    │                                  │
├───────────────────────────────────────────┤             GLOBE                │
│ EVENT QUEUE                               │          (supporting)            │
│  1  ISS   × STARLINK-31178   2d 04h  ...  │                                  │
│  2  XI-IV × FENGYUN 1C DEB   4d 11h  ...  │   selection-linked, lazily       │
│  3  ...                                   │   loaded, dismissible            │
│                                           │                                  │
├───────────────────────────────────────────┤                                  │
│ DETAIL  (opens under the queue, or as a   │                                  │
│  right-hand third pane above 1600 px)     │                                  │
├───────────────────────────────────────────┴──────────────────────────────────┤
│ REPLAY SCRUBBER (replay mode only) — the Kp bar is its background            │ 64 px
└──────────────────────────────────────────────────────────────────────────────┘
```

The queue is the widest thing on the screen at every width, because it is the thing being read.
The globe gets what is left and never more than 40 %.

## 3. The status strip

One row, always visible, never scrolls away. Four groups, left to right, separated by thin
rules rather than by whitespace alone so the grouping survives a narrow window.

| Group | Contents | Notes |
| --- | --- | --- |
| **Geomagnetic now** | Current Kp with its three-hour interval, and the G level | From the space weather table's newest `observed` row. The Kp digit takes the G-ramp colour; it is one of exactly three places that ramp appears. |
| **Geomagnetic ahead** | The peak forecast Kp over the next 72 hours, the G level, the hours until it, and the issue time of the forecast it came from | SWPC's three-day forecast. The issue time is not decoration: a six-hour-old forecast and a six-minute-old one are different objects and the strip must not conflate them. |
| **Scenario in force** | The named scenario every probability on screen was computed under | See §3.1. This is the single most important label on the console. |
| **Provenance** | Snapshot age, oldest element-set epoch in the run, run id, model version, supplemental version, and when the scoring was computed | Collapsed to `14 h old · run 20260901T2048Z-a3f1` with the rest on click or focus. |

**Snapshot age is two numbers, not one.** The snapshot's own fetch time answers "how old is
this run", and the *oldest element-set epoch in it* answers "how old is the worst element set a
probability rests on". They differ by days, the second is what actually degrades the answer,
and only the second is a fair thing to judge the tool by. Both are shown; the second is the one
in the collapsed strip when it is the worse of the two.

**Staleness is not shown in colour.** The G ramp is reserved (§5 of the visual pass), and a
stale-data warning in amber would read as a storm. Staleness is shown by the word, a heavier
weight on the number, and a hairline rule under the group. If the run is older than the
screening window it describes, the strip says `EXPIRED` in text and the queue is dimmed as a
whole, because at that point every probability on screen is about a week that has passed.

### 3.1 The scenario control

The brief left open whether this is a segmented control or a dropdown, saying Phase 3 Step 3
would settle it. Step 3 delivered five named scenarios plus a parameterised `replay:<date>`, so:

- **Desktop: a segmented control of five** — `quiet · forecast · G3 · G4 · G5`. Five is the
  most a segmented control carries legibly, and it is exactly five. Replay is not a sixth
  segment: it is a *mode*, entered from a separate control, because it changes the meaning of
  the whole screen (the times become historical) rather than only the numbers in it.
- **Below 900 px: a dropdown**, with the current scenario's name always rendered in full. Never
  an abbreviation: `G4` alone on a small screen, next to a probability, is too easy to read as
  a flag.
- The control is the only way probabilities change, and changing it re-renders the queue and
  the detail view in place. It does not touch the point cloud (the Phase 1 rule).
- A scenario the run has not been scored under is shown but disabled, with the reason
  (`not scored for this run`) rather than hidden, so the reader knows the option exists.

## 4. The fleet band: state at a glance

One row per fleet member, horizontally scrollable only if the fleet is larger than the width
allows. Per member, in this order:

`name · altitude · events by flag · highest probability · time to that event · Δ vs quiet`

- **Events by flag** is three counts (red, yellow, none) rendered as counts, not as coloured
  dots. Zero is shown as `–`, not as `0`: the eye should be able to sweep the row and see
  nothing rather than count zeros.
- **Δ vs quiet** is the fleet member's worst event's `pc / pc_quiet`, shown as `×0.7` or `×12`
  with an arrow. This is the number that makes the storm layer worth having on the screen at
  all, and putting it at fleet level means a reader sees "the storm halved my worst event"
  before they have opened anything.
- A member with **no covariance history** (fewer than the fit's minimum element sets) says so
  here rather than silently carrying a category default. So does a member on a **stale element
  set**.
- The band is a filter: clicking a member restricts the queue to it. Clicking again clears.

## 5. The event queue

Sorted by probability under the scenario in force, descending. One row per event. Columns, in
reading order, with the ones that can be dropped at narrow widths marked:

| Column | Content | Drops at |
| --- | --- | --- |
| Rank | Position in the sort | — |
| Primary | Fleet member, short name | — |
| Secondary | Name, category glyph, and NORAD id | id at < 1100 px |
| TCA | Relative first (`in 2 d 04 h`), absolute second, both UTC | absolute at < 900 px |
| Miss | Kilometres, under the scenario in force | — |
| **Probability** | The scenario's `pc`, in scientific notation with tabular numerals | — |
| Flag | `red` / `yellow` / none, as weight and a leading rule, never as hue | — |
| Region | `robust` / `dilution` / `unscoreable` | — |
| Confidence | `standard` / `low` / `none` | merged into Region at < 1100 px |
| **Commandability** | Hours from the last usable ground-station pass to the TCA | < 1100 px |
| **Δ quiet→storm** | `pc / pc_quiet` as a multiplier with a direction arrow | — |
| **Storm validity** | `validated` / `indicative`, from the weaker of the two coefficient sources | merged into Δ at < 1100 px |

Five things about this table matter more than the rest.

**The sort key is the scenario's probability, and the sort is stated in the header.** Not
"risk", not a composite score. A composite would hide the one judgement the tool is making.

**Region and confidence are always both present.** A red flag in the dilution region at low
confidence is not a red flag; it is a statement that the data cannot support a judgement either
way. The queue must never render the flag without the region beside it, at any width — which is
why Region is the one column that never drops, only merges.

**Commandability is a column, not a footnote.** A probability is only actionable if somebody can
act on it, and for a small operator the binding constraint is usually whether there is a pass
between now and the encounter. It is `hours from the last usable pass before TCA`, and it is
rendered `4.2 h` or, when there is no pass at all before the encounter, `none before TCA` in
the row's heaviest weight. It depends on the ground-station work parked in ROADMAP.md at the
Step 2 review, and if that work is not done the column shows `–` with a tooltip saying no
ground stations are defined — never a plausible-looking blank.

**The quiet-to-storm delta is on every row, not only on the interesting ones.** Phase 3's
headline result is that the storm *lowers* the probability on most events, and a reader who sees
`×0.7` on twenty rows and `×340` on one has learned that result from the screen rather than from
the documentation. Under the `quiet` scenario the column reads `—` rather than `×1.0`, because
the comparison is with itself.

> **Corrected at the Phase 3 Step 4 review (2026-09-03).** This paragraph originally attributed
> the headline result to "common-mode cancellation", meaning that a storm displaces both objects
> of a pair alike so that only a small relative shift reaches the miss. The result stands and the
> mechanism does not. Measured, the relative shift is **1.91 times** the mean of the two objects'
> own shifts out of a possible 2: the two displacements are nearly independent, because a
> conjunction is a crossing at a median 120° between the two in-track directions. What lowers
> most probabilities is simply that a displacement of tens of kilometres applied to a miss of a
> few separates more pairs than it creates. See `docs/storm-term.md`, "Attacking the result".

**The delta column says which of the two labels the row carries.** Step 4 measured the storm term
against the May 2024 record and found it predictive only for objects whose ballistic coefficient
was measured from their own decay. A row whose weaker side rests on a B\* inversion or a
population stand-in is `indicative`, and the console must not let the multiplier be read without
it: the delta is rendered in the row's normal weight for a `validated` event and in a muted
weight with an `indicative` marker otherwise. §5's aggregates are reported both ways for the same
reason. See "Storm-term validity" in `docs/methods.md`.

**Unscoreable events are in their own section below the queue**, headed with the count and the
reason, one row each carrying the object, the reason text and everything except a probability.
They cannot be ranked by a number they do not have, and putting them in the sort with a blank
would make them read as "safe". The section is collapsed by default and its header is always
visible: `3 events not scored — the storm term is outside its own derivation for 2 objects`.

### 5.1 Selection and the globe

Selecting a queue row does four things in one frame: opens the detail view, dims the rest of
the queue, highlights the two objects on the globe if it is loaded, and, if it is not, does
nothing about the globe at all and says nothing about it either. **No part of the detail view
waits on the globe.**

## 6. The detail view

Three blocks, in this order. Everything in it is derived from one risk row plus the two objects'
rows; nothing here needs a new computation in the browser.

### 6.1 The encounter plane

As specified in §6 of the visual pass: hard-body disc, 1σ/2σ/3σ contours, the miss vector, a
fixed stated scale, tabular numerals, and under a storm scenario the quiet ellipse as a faint
outline with an arrow from the quiet miss to the scenario miss.

One addition Step 3 makes possible: the arrow is drawn **from the shift alone**. The console
carries `pc`, `pc_shift_only` and `pc_variance_only`, so the picture can be honest about which
half did the work — the arrow is the shift, the change in ellipse size is the variance, and the
caption gives the three numbers in that order.

### 6.2 The covariance, for both objects

A two-column block, primary and secondary, each stating:

- the covariance source label as it appears in the data (`empirical`, `supplemental:<version>`,
  `spacex:<epoch>`, `default:<band>`), spelled out in words underneath;
- σ radial, in-track and cross-track in kilometres at the time of closest approach;
- how many element sets the fit rests on, and the fitted window;
- the manoeuvre level (`none` / `possible` / `observed` / `known`) and the date of the last
  observed jump;
- the hard-body radius and where it came from (`fleet`, `category`, `rcs`, `span`);
- **and, under a storm scenario, the in-track sigma the storm term added and the ballistic
  coefficient source it rests on** (`history`, `bstar`, `typical`), with the thrust marking
  where it applies.

This block exists because the probability is a model output and the reader is entitled to see
the model. It is the block that makes a low-confidence red flag legible as what it is.

### 6.3 The scenario comparison

A small table: one row per scenario the run has been scored under, columns `miss`, `pc`,
`pc shift only`, `pc variance only`, `region`, `confidence`. The scenario in force is marked.
An unscoreable scenario shows its reason across the row rather than blanks.

This is the console's answer to "what would a G4 do to this", and it is a table rather than a
chart because five rows of six numbers is a table.

## 7. Responsive behaviour

Three layouts, and the rules are stated as behaviour rather than as breakpoint arithmetic
because the breakpoints are consequences.

| Width | Layout |
| --- | --- |
| ≥ 1600 px | Status strip; fleet band; queue; globe; detail as a third pane beside the queue. |
| 1280–1599 px | As the diagram in §2: detail opens beneath the queue, globe on the right. |
| 900–1279 px | Two panes. The globe collapses to a button in the status strip; opening it overlays the right half and can be dismissed. Queue drops the columns marked in §5. |
| < 900 px | **Single column. The event list is the page.** |

At the phone layout:

- **The event list is primary and the globe is optional.** The globe is not rendered, not
  fetched, and not loaded until the reader asks for it with an explicit control labelled
  `Show globe (~3.5 MB)` — the size is in the label, because on a metered connection that is
  information the reader needs before they tap, not after. The figure is transfer, not raw: the
  scripts compress about threefold and the two `.bin` float arrays barely compress at all.
- **Hover is replaced by tap, everywhere, with no information lost.** This is a hard rule, not
  a courtesy: nothing may exist only in a hover state. Concretely — the queue row's hover
  tooltip becomes a first-tap expansion of the row in place (a second line under it with the
  dropped columns); a second tap on the same row opens the detail sheet; a tap elsewhere
  collapses it. Every hover affordance on the desktop layout must have a focus equivalent as
  well, which is the same requirement arriving from accessibility rather than from touch.
- **The encounter-plane inset becomes a full-screen sheet**, entered from the detail view,
  dismissed by a swipe down or a close control, with the covariance block scrolling underneath
  it. At phone width the inset is otherwise about 90 mm across, which is not enough for three
  sigma contours, a disc, a vector, tick marks and a scale to be read at once — so it gets the
  screen or it does not get drawn.
- The fleet band becomes a horizontally scrollable strip of chips with the same contents, and
  the scroll is snapped per member so a chip is never half-visible.
- The status strip keeps the Kp values and the scenario name and collapses the provenance to a
  single tappable `ⓘ`. The scenario name is never abbreviated (§3.1).
- The replay scrubber, in replay mode, becomes the bottom 96 px with the Sun tile moving to a
  collapsed thumbnail; the four things it drives still move together, which is the whole point
  of it being one control.

Touch targets are at least 44 × 44 px. The queue row is 56 px tall at phone width against 34 px
on desktop, which is the main reason the phone layout shows fewer rows rather than smaller ones.

## 8. First meaningful paint on a mid-range phone

**The target: first meaningful paint at or under 1.8 s, and largest contentful paint at or
under 2.5 s, on a mid-range Android over Slow 4G** — Lighthouse's mobile profile, 1.6 Mbit/s
down, 150 ms round trip, 4× CPU throttle. "Meaningful" is defined here as *the status strip and
the first ten queue rows, with real numbers in them*. Not a skeleton, not a spinner: the
answer to question 1 and the top of the answer to question 2.

That target is a budget, and the budget is spent as follows.

**What the current bundle costs, measured** (re-measured 2026-09-03 after Phase 3 Step 5 added
storm mode and the replay; `web/dist` and `web/public/data`):

| Asset | Bytes | On the console's critical path? |
| --- | ---: | --- |
| `index-*.js` (three.js, globe.gl, the viewer) | 1 935 374 | **No** |
| `index-*.js` (second chunk) | 308 863 | Partly — the console's own code is carved out of this |
| `base-release-*.js` | 152 136 | No |
| `propagator.worker-*.js` | 30 507 | No |
| `index-*.css` | 9 030 | Yes |
| `objects.json` | 2 064 926 | No |
| `elements.bin` | 2 847 768 | No |
| `conjunctions.json` | 3 531 615 | **No — replaced, see below** |
| `scenarios.json` (storm mode, lazy) | 1 280 532 | **No — fetched after first paint** |
| `reference.bin` | 776 664 | No |
| `conjunction-tracks.bin` | 439 200 | No |
| `replay/` (catalogue, conjunctions, timeline, 29 Sun frames) | 15 166 904 | **No — and only 1.4 MB of it on entry, see below** |
| Blue Marble texture (globe.gl default) | ~1 MB | No |

Roughly 13 MB of transfer for the live viewer today, plus 15 MB more that only a reader who
enters replay ever fetches, of which about 60 KB is on the console's critical path once the split
below is made. That is the whole design: the console is a different, much smaller document that
happens to share a repository with the globe.

**Step 5 cost the critical path nothing**, which was the point of building it the way it was
built. The viewer's own JavaScript grew by 24 KB and its stylesheet by 3.8 KB; `scenarios.json`
is behind an idle callback and the replay directory behind an explicit mode switch, and neither
is fetched by a reader who does not use them. The largest single file is 3.4 MB against
Cloudflare Pages' 25 MiB limit, and the largest Sun frame is 380 KB.

**And entering replay costs 1.4 MB of the 15 MB, not 15 MB.** The 10.4 MiB of Sun imagery is 29
full frames, of which the viewer fetches **three** up front and the rest only as the playhead
approaches them; every frame's 32 px thumbnail travels inline in the 121 KB `storm.json`, so
every scrub position has a picture immediately without any of them being requested. What is
actually fetched on entry is the historical catalogue (2.4 MB of `elements.bin`, `objects.json`
and `reference.bin` for 13,376 objects, against 5.6 MB for the live 32,361), that run's
conjunctions and overlays (1.3 MB), the timeline, and three images. The rest is there for a
reader who scrubs the whole week, which is the only reader who needs it.

**What ships on the critical path:**

1. `console.json` — a new export, written by `driftwatch report`: the status strip's fields, the
   fleet band's rollup, and the **first 50 queue rows fully populated**, with the rest of the
   queue in a second file. Estimated 45–70 KB raw, 12–20 KB gzipped, for a demo-fleet run.
2. The console's own JavaScript: DOM rendering, sorting, the scenario control. No three.js, no
   globe.gl, no satellite.js, no worker. Budget **40 KB gzipped**, and it is a budget rather
   than an estimate because it is the number that must be defended in review.
3. The stylesheet, inlined into the document head at build time while it is under 8 KB.
4. The document itself, with the status strip's *last known* values server-rendered into the
   HTML at export time, so the strip has content before any script runs.

That is about 60 KB gzipped on the critical path against roughly 3 MB today for a first paint
that shows anything at all.

**What is dropped to reach it**, explicitly:

- **The globe and its whole dependency tree** — three.js, globe.gl, the Blue Marble texture,
  `elements.bin`, `reference.bin`, the propagation worker. Loaded on an explicit control at
  phone width, and on an idle callback after first paint at desktop width. About 6.7 MB raw and
  roughly 3.5 MB transferred.
- **The rest of the event queue** beyond the first 50 rows, and `objects.json` entirely: the
  queue's rows carry the few object fields they need, denormalised, rather than joining against
  a catalogue in the browser. About 2 MB.
- **`conjunction-tracks.bin`** — the two ten-minute tracks per event, fetched only when an event
  is opened, and only for that event if the export is split per event.
- **The replay bundle**: Sun imagery, the Kp series and the historical positions load when
  replay mode is entered, never before.
- **Web fonts.** The first paint uses a system font stack with
  `font-variant-numeric: tabular-nums`, which every system UI face in the stack supports; where
  it does not the fallback is the platform monospace. No font file is on the critical path, so
  there is no flash of invisible text and no layout shift from a swap. If a display face is
  wanted later it may only be used for headings, loaded with `font-display: optional`, and it
  must not touch a number.
- **Any client-side propagation.** Nothing on the critical path calls SGP4. The console's
  numbers are computed by the pipeline and exported; the browser renders them.

**What is not dropped:** every number's provenance. The scenario name, the region, the
confidence and the snapshot age are on the critical path and stay there, because a fast screen
that does not say what it is showing is worse than a slow one that does.

**How it is checked.** A Lighthouse run in CI against the built bundle on the mobile profile,
failing the build if FMP exceeds 1.8 s or if the critical-path transfer exceeds 80 KB gzipped.
The existing `driftwatch check-bundle` already enforces a per-file size limit for Cloudflare
Pages; this is the same idea one level up, and the two should report together.

## 9. What this specification still does not decide

- **The ground-station model behind commandability.** The column is specified; the pass
  predictor, the minimum elevation and the fleet-file schema for stations are the parked Phase 4
  item and are not settled here.
- **Whether the console and the existing viewer are one page or two.** The split above makes
  them cleanly separable, and either arrangement satisfies it; the decision belongs with the
  routing and the hosting, not with the layout.
- **Persistence of operator state** — acknowledged events, per-member thresholds, a chosen
  scenario surviving a reload. All of it is desirable and none of it is specified, because it is
  the first thing that turns a published artefact into an application with accounts.
- **Anything about the point cloud's data path.** As before: it is not to change.

## What this brief does not decide

- The replay bundle's size budget, which depends on how many Sun frames a day survive the
  25 MiB Cloudflare Pages file limit that `driftwatch check-bundle` enforces.
- Anything about the point cloud's data path. It is not to change.
- The four items in §9 of the console specification above.

*Settled since this brief was first written:* whether the storm control is a segmented control
or a dropdown. Phase 3 Step 3 delivered five named scenarios plus a parameterised replay, so it
is a segmented control of five on desktop and a dropdown below 900 px, with replay as a separate
mode rather than a sixth segment. See §3.1.

## Sources

- [thkruz/keeptrack.space](https://github.com/thkruz/keeptrack.space) — AGPL-3.0-or-later; KeepTrack™ and KeepTrack.space™ are trademarks of Kruczek Labs LLC. Referenced for ideas only.
- [Flowm/satvis](https://github.com/Flowm/satvis) — MIT; CesiumJS + Vue; the Cloudflare Worker and the CelesTrak egress problem.
- [ut-astria/AstriaGraph](https://github.com/ut-astria/AstriaGraph) — GPL-3.0; `main.js`, the per-class point colours and the select-then-draw-orbit behaviour.
- [cambecc/earth](https://github.com/cambecc/earth) — the `destination-in` fade, `MAX_PARTICLE_AGE`, `FRAME_RATE` and the particle colour ramp in `public/libs/earth/1.0.0/earth.js`.
- [NOAA Space Weather Scales](https://www.spaceweather.gov/noaa-scales-explanation) — the G1 to G5 descriptors and Kp values.
