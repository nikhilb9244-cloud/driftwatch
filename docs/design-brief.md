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

## What this brief does not decide

- Whether the storm control is a segmented control or a dropdown. That depends on how many
  scenarios there are in the end, which Phase 3 Step 3 settles.
- The replay bundle's size budget, which depends on how many Sun frames a day survive the
  25 MiB Cloudflare Pages file limit that `driftwatch check-bundle` enforces.
- Anything about the point cloud's data path. It is not to change.

## Sources

- [thkruz/keeptrack.space](https://github.com/thkruz/keeptrack.space) — AGPL-3.0-or-later; KeepTrack™ and KeepTrack.space™ are trademarks of Kruczek Labs LLC. Referenced for ideas only.
- [Flowm/satvis](https://github.com/Flowm/satvis) — MIT; CesiumJS + Vue; the Cloudflare Worker and the CelesTrak egress problem.
- [ut-astria/AstriaGraph](https://github.com/ut-astria/AstriaGraph) — GPL-3.0; `main.js`, the per-class point colours and the select-then-draw-orbit behaviour.
- [cambecc/earth](https://github.com/cambecc/earth) — the `destination-in` fade, `MAX_PARTICLE_AGE`, `FRAME_RATE` and the particle colour ramp in `public/libs/earth/1.0.0/earth.js`.
- [NOAA Space Weather Scales](https://www.spaceweather.gov/noaa-scales-explanation) — the G1 to G5 descriptors and Kp values.
