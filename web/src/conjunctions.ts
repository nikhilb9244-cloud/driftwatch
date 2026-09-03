/**
 * The conjunctions panel: the screening run, as Python computed it.
 *
 * Nothing here is a screening result of the browser's own. The pairs, the events, the
 * probabilities, the covariances and the tracks all come out of `conjunctions.json`,
 * `scenarios.json` and `conjunction-tracks.bin`, written by `driftwatch report`. The viewer's
 * job is to put them somewhere a reader can see them: a list of pairs (repeated encounters
 * collapsed, as the Step 2 review asked), the events of a pair on demand, and, when an event is
 * selected, the clock jumped to the time of closest approach, both objects highlighted, ten
 * minutes of each track drawn either side, and the encounter plane in an inset.
 *
 * The tracks are stored in TEME, the frame SGP4 works in, and are rotated to Earth-fixed
 * here with the same GMST that the propagation worker uses (`gstime`, UTC standing in for
 * UT1, no polar motion). Doing the rotation the same way in both places is what keeps a
 * drawn track sitting on its moving dot.
 *
 * **Step 5 adds the scenario in force.** Every number in the list and the detail view is read
 * through `ScenarioState`, so switching from `quiet` to `G5` re-renders the panel and touches
 * nothing else — not the point cloud, not the worker, not the tracks, which are geometry and do
 * not depend on the scenario. Two consequences are visible in the markup and both are
 * deliberate:
 *
 * - The **miss** shown under a storm scenario is the *shifted* miss, which is what that
 *   scenario's probability was computed from. The quiet miss is still shown, beside it, in the
 *   detail view — they answer different questions and the difference is the storm's whole effect
 *   on the geometry.
 * - The **Δ against quiet** is on every row rather than only the interesting ones
 *   (`docs/design-brief.md` §5), because a reader who sees `×0.7` twenty times and `×340` once
 *   has learnt the phase's headline result from the screen rather than from the documentation.
 */

import * as THREE from "three";
import { gstime } from "satellite.js";
import type { Bundle, ConjunctionEvent, ConjunctionPair } from "./data";
import { formatUtc } from "./geodesy";
import { eventUnder, labelOf, pairUnder, type ScenarioState } from "./scenarios";
import { SCENE_PER_KM } from "./points";
import { escapeHtml } from "./ui";

const TRACK_COLOURS = { primary: 0xffd166, secondary: 0x4cc9f0 };
/** Pairs shown at once; the rest are reachable by the filter box. */
const LIST_LIMIT = 120;

export interface ConjunctionSelection {
  pair: ConjunctionPair;
  event: ConjunctionEvent;
  primaryIndex: number;
  secondaryIndex: number;
}

/** Two polylines in the scene, one per object, redrawn whenever an event is selected. */
export class ConjunctionTracks {
  private readonly group = new THREE.Group();
  private readonly lines: THREE.Line[] = [];
  private readonly marks: THREE.Points[] = [];

  constructor(samples: number) {
    for (const colour of [TRACK_COLOURS.primary, TRACK_COLOURS.secondary]) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(samples * 3), 3));
      geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 100 * 80);
      const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: colour, transparent: true, opacity: 0.9 }));
      line.frustumCulled = false;
      line.renderOrder = 6;
      this.lines.push(line);
      this.group.add(line);

      const dot = new THREE.BufferGeometry();
      dot.setAttribute("position", new THREE.BufferAttribute(new Float32Array(3), 3));
      dot.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 100 * 80);
      const mark = new THREE.Points(dot, new THREE.PointsMaterial({ color: colour, size: 6, sizeAttenuation: false }));
      mark.frustumCulled = false;
      mark.renderOrder = 7;
      this.marks.push(mark);
      this.group.add(mark);
    }
    this.group.visible = false;
  }

  get object3d(): THREE.Object3D {
    return this.group;
  }

  hide(): void {
    this.group.visible = false;
  }

  /** Release the two polylines and their markers, for a catalogue swap. */
  dispose(): void {
    for (const line of this.lines) {
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    }
    for (const mark of this.marks) {
      mark.geometry.dispose();
      (mark.material as THREE.Material).dispose();
    }
  }

  /**
   * Draw both tracks for `event`, rotating each TEME sample to Earth-fixed at its own time.
   *
   * GMST advances about five degrees over the twenty minutes of a track, so the rotation
   * has to be per sample; using one angle for the whole track would smear it by kilometres.
   *
   * The tracks are the **geometry**, so they do not move when the scenario changes: a storm
   * scenario displaces an object along that track, and the displacement is a number in the
   * panel rather than a redrawn line. Drawing a shifted track would be drawing a position the
   * covariance says we do not know to within many times the shift.
   */
  show(bundle: Bundle, event: ConjunctionEvent): boolean {
    const spec = bundle.conjunctions?.tracks;
    if (!bundle.tracks || !spec || event.track == null) {
      this.hide();
      return false;
    }
    const tcaMs = Date.parse(event.tca);
    const stride = spec.samples * 3;
    for (let side = 0; side < 2; side++) {
      const base = (event.track * spec.objects_per_event + side) * stride;
      const positions = this.lines[side].geometry.getAttribute("position") as THREE.BufferAttribute;
      const array = positions.array as Float32Array;
      for (let k = 0; k < spec.samples; k++) {
        const tMs = tcaMs + (k - (spec.samples - 1) / 2) * spec.step_s * 1000;
        const theta = gstime(new Date(tMs));
        const c = Math.cos(theta);
        const s = Math.sin(theta);
        const x = bundle.tracks[base + k * 3];
        const y = bundle.tracks[base + k * 3 + 1];
        const z = bundle.tracks[base + k * 3 + 2];
        const xe = c * x + s * y;
        const ye = -s * x + c * y;
        // Scene axes are (Y, Z, X) of the Earth-fixed frame, as in points.ts and picking.ts.
        array[k * 3] = ye * SCENE_PER_KM;
        array[k * 3 + 1] = z * SCENE_PER_KM;
        array[k * 3 + 2] = xe * SCENE_PER_KM;
      }
      positions.needsUpdate = true;
      const mid = Math.floor((spec.samples - 1) / 2) * 3;
      const dot = this.marks[side].geometry.getAttribute("position") as THREE.BufferAttribute;
      (dot.array as Float32Array).set(array.slice(mid, mid + 3));
      dot.needsUpdate = true;
    }
    this.group.visible = true;
    return true;
  }
}

// --------------------------------------------------------------------------------------
// The encounter-plane inset

/** Principal axes of a 2x2 covariance: half-axes in km and the rotation of the first. */
function principalAxes(xx: number, xy: number, yy: number): { a: number; b: number; angle: number } {
  const theta = 0.5 * Math.atan2(2 * xy, xx - yy);
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  const v1 = xx * c * c + 2 * xy * c * s + yy * s * s;
  const v2 = xx * s * s - 2 * xy * c * s + yy * c * c;
  return { a: Math.sqrt(Math.max(v1, 0)), b: Math.sqrt(Math.max(v2, 0)), angle: theta };
}

const missOf = (event: ConjunctionEvent): number =>
  event.miss_shifted_km != null && Number.isFinite(event.miss_shifted_km) ? event.miss_shifted_km : event.miss_km;

/**
 * The encounter plane as an SVG: the hard-body disc at the origin, the combined covariance
 * ellipse centred on the miss, and the miss vector between them.
 *
 * This is the picture the probability is an integral over: the plane perpendicular to the
 * relative velocity, the disc of the combined hard-body radius, and the Gaussian whose
 * mass inside that disc is the probability of collision.
 *
 * Under a storm scenario, `quiet` is drawn behind it as a faint outline with an arrow from the
 * quiet miss to the scenario's — `docs/design-brief.md` §6.1. The arrow is the storm's effect on
 * the geometry, drawn to the same scale as everything else, so a reader can see at a glance
 * whether the displacement was large against the uncertainty or lost inside it.
 */
export function encounterPlaneSvg(event: ConjunctionEvent, quiet: ConjunctionEvent | null = null, size = 260): string {
  const xx = event.enc_cov_xx_km2 ?? 0;
  const xy = event.enc_cov_xy_km2 ?? 0;
  const yy = event.enc_cov_yy_km2 ?? 0;
  const { a, b, angle } = principalAxes(xx, xy, yy);
  const miss = missOf(event);
  const quietMiss = quiet ? missOf(quiet) : null;
  const hbr = (event.hbr_m ?? 0) / 1000;
  const far = Math.max(miss, quietMiss ?? 0);
  const extent = Math.max(far + 3 * Math.max(a, b), 3 * Math.max(a, b), hbr * 4, 1e-6) * 1.15;
  const scale = size / 2 / extent;
  const cx = size / 2;
  const cy = size / 2;
  const mx = cx + miss * scale;
  const deg = (-angle * 180) / Math.PI;
  // The uncertainty is routinely thousands of times the hard-body radius, and the covariance
  // is far longer in-track than across. Drawn to scale the disc and the minor axis vanish, so
  // both get a floor of a couple of pixels and the caption says by how much the disc was grown.
  const minPx = 2.5;
  const ellipse = (x: number, k: number, opacity: number, av: number, bv: number, degv: number, fill: string) =>
    `<ellipse cx="${x.toFixed(2)}" cy="${cy}" rx="${Math.max(k * av * scale, minPx).toFixed(2)}" ` +
    `ry="${Math.max(k * bv * scale, 1).toFixed(2)}" ` +
    `transform="rotate(${degv.toFixed(2)} ${x.toFixed(2)} ${cy})" fill="${fill}" ` +
    `stroke="rgba(76,201,240,${opacity})" stroke-width="1"/>`;
  const ring = (k: number, opacity: number) => ellipse(mx, k, opacity, a, b, deg, "rgba(76,201,240,0.10)");

  let quietLayer = "";
  if (quiet && quietMiss != null && Math.abs(quietMiss - miss) * scale > 1) {
    const q = principalAxes(quiet.enc_cov_xx_km2 ?? 0, quiet.enc_cov_xy_km2 ?? 0, quiet.enc_cov_yy_km2 ?? 0);
    const qx = cx + quietMiss * scale;
    quietLayer =
      ellipse(qx, 1, 0.25, q.a, q.b, (-q.angle * 180) / Math.PI, "none") +
      `<line x1="${qx.toFixed(2)}" y1="${cy}" x2="${mx.toFixed(2)}" y2="${cy}" stroke="#f4a261" ` +
      `stroke-width="1.5" stroke-dasharray="3 2" marker-end="url(#shift-arrow)"/>`;
  }
  const trueDiscPx = hbr * scale;
  const discR = Math.max(trueDiscPx, minPx);
  const magnified = trueDiscPx > 0 && discR / trueDiscPx > 1.5;
  const caption = magnified
    ? `half-width ${extent.toPrecision(3)} km · disc drawn ${Math.round(discR / trueDiscPx)}× true size`
    : `half-width ${extent.toPrecision(3)} km`;
  const sigmas = `1σ ${a.toPrecision(2)} × ${b.toPrecision(2)} km`;
  return `
<svg viewBox="0 0 ${size} ${size}" width="100%" role="img"
     aria-label="Encounter plane: hard-body disc, covariance ellipse and miss vector">
  <defs>
    <marker id="shift-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0 0 L8 4 L0 8 z" fill="#f4a261"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="${size}" height="${size}" fill="rgba(8,12,20,0.55)" rx="6"/>
  <line x1="0" y1="${cy}" x2="${size}" y2="${cy}" stroke="rgba(255,255,255,0.10)"/>
  <line x1="${cx}" y1="0" x2="${cx}" y2="${size}" stroke="rgba(255,255,255,0.10)"/>
  ${quietLayer}
  ${ring(3, 0.35)}
  ${ring(1, 0.75)}
  <line x1="${cx}" y1="${cy}" x2="${mx.toFixed(2)}" y2="${cy}" stroke="#ffd166" stroke-width="1.5"/>
  <circle cx="${cx}" cy="${cy}" r="${discR.toFixed(2)}" fill="rgba(239,71,111,0.35)" stroke="#ef476f" stroke-width="1.5"/>
  <circle cx="${mx.toFixed(2)}" cy="${cy}" r="2.5" fill="#4cc9f0"/>
  <text x="6" y="14" fill="rgba(230,237,243,0.75)" font-size="10">${escapeHtml(sigmas)}</text>
  <text x="6" y="${size - 8}" fill="rgba(230,237,243,0.75)" font-size="10">${escapeHtml(caption)}</text>
</svg>`;
}

// --------------------------------------------------------------------------------------
// The panel

const fmtPc = (v: number | null | undefined): string =>
  v == null || !Number.isFinite(v) ? "—" : v === 0 ? "0" : v.toExponential(2).replace("e", "e");

const fmtKm = (v: number | null | undefined, digits = 3): string =>
  v == null || !Number.isFinite(v) ? "—" : v.toFixed(digits);

/**
 * Below this, a probability is indistinguishable from zero and a ratio of two of them is
 * numerical noise. The same floor `driftwatch storm-check` bands on, for the same reason: a
 * storm that takes an event from 1e-95 to 1e-24 has multiplied it by 1e71 and changed nothing
 * anybody could act on, and a column of such numbers buries the handful that matter.
 */
const PC_FLOOR = 1e-12;

/**
 * `pc / pc_quiet` as a multiplier with a direction arrow, or an em dash when the comparison is
 * with itself, one of the two numbers is missing, or both are below the floor. Zero-to-zero is
 * not a ratio and says so.
 */
function deltaAgainstQuiet(pc: number | null | undefined, quietPc: number | null | undefined): string {
  if (pc == null || quietPc == null || !Number.isFinite(pc) || !Number.isFinite(quietPc)) return "—";
  if (Math.max(pc, quietPc) < PC_FLOOR) return "—";
  // One side below the floor and the other above: the ratio is a number like 1e47, which says
  // "it came from nothing" in the least readable way available. Say that instead.
  if (quietPc < PC_FLOOR) return "↑ from ~0";
  if (pc < PC_FLOOR) return "↓ to ~0";
  const ratio = pc / quietPc;
  if (!Number.isFinite(ratio)) return "—";
  const arrow = ratio > 1 ? "↑" : ratio < 1 ? "↓" : "=";
  const text = ratio >= 100 || ratio < 0.01 ? ratio.toExponential(1) : ratio.toFixed(2);
  return `${arrow}×${text}`;
}

/** Why a Δ is an em dash, for the cell's tooltip. */
function deltaTitle(pc: number | null | undefined, quietPc: number | null | undefined): string {
  if (pc != null && quietPc != null && Number.isFinite(pc) && Number.isFinite(quietPc)) {
    if (Math.max(pc, quietPc) < PC_FLOOR) {
      return `Both this scenario and quiet are below ${PC_FLOOR.toExponential(0)}, where the two are indistinguishable from zero and their ratio is numerical noise. The storm did move this event; it moved it from one unactionable number to another.`;
    }
    if (quietPc < PC_FLOOR || pc < PC_FLOOR) {
      return `One side is below ${PC_FLOOR.toExponential(0)}, so the ratio would be a number like 1e47. The event crossed the level at which a probability means anything, which is the statement worth making.`;
    }
  }
  return "This scenario's probability over the quiet one";
}

function flagChip(flag: string, confidence: string, region: string): string {
  if (flag === "unscoreable") {
    return `<span class="flag none" title="The storm term left the linear theory it was derived under; this event carries no probability at all">not scored</span>`;
  }
  if (flag === "none") return "";
  const cls = confidence === "low" ? "flag low" : `flag ${flag}`;
  const title = confidence === "low" ? `${flag}, low confidence (${region} region): not actionable` : `${flag}`;
  const label = confidence === "low" ? `${flag} · low` : flag;
  return `<span class="${cls}" title="${escapeHtml(title)}">${escapeHtml(label)}</span>`;
}

/** `indicative` gets a marker; `validated` and `none` do not need one on every row. */
function validityChip(validity: string | undefined): string {
  if (validity !== "indicative") return "";
  return `<span class="chip-validity" title="At least one of the two objects has no ballistic coefficient measured from its own decay. Step 4 found the storm term predictive at r = 0.88 with a measured coefficient and of no demonstrated skill without one. The number is not adjusted for this; the label says the validation does not reach it.">indicative</span>`;
}

export interface PanelHandles {
  /** Redraw the list, e.g. after the filter or the scenario changes. */
  refresh(): void;
}

/**
 * Build the conjunctions panel. `onSelect` is called with the pair, the event and the two
 * point-cloud indices (-1 when the object is not in the catalogue bundle).
 *
 * `signal` aborts every listener this attaches, so the panel can be rebuilt against a different
 * bundle when the viewer switches to replay without the previous one's handlers surviving. The
 * lists themselves are rebuilt by `innerHTML`, so only the four persistent controls need it.
 */
export function buildConjunctionPanel(
  bundle: Bundle,
  state: ScenarioState,
  onSelect: (selection: ConjunctionSelection | null) => void,
  signal?: AbortSignal,
): PanelHandles {
  const root = document.getElementById("conjunctions");
  const data = bundle.conjunctions;
  if (!root || !data) {
    if (root) root.hidden = true;
    return { refresh: () => void 0 };
  }
  root.hidden = false;

  const indexOfNorad = new Map<number, number>();
  bundle.objects.norad_id.forEach((id, i) => indexOfNorad.set(id, i));

  const header = root.querySelector<HTMLElement>("#conjunctions-summary");
  const list = root.querySelector<HTMLElement>("#conjunction-list");
  const detail = root.querySelector<HTMLElement>("#conjunction-detail");
  const filter = root.querySelector<HTMLInputElement>("#conjunction-filter");
  const onlyFlagged = root.querySelector<HTMLInputElement>("#conjunction-flagged");
  if (!header || !list || !detail || !filter || !onlyFlagged) return { refresh: () => void 0 };

  /** The pairs under the scenario in force, ranked by its probability, with their base index. */
  const rankedPairs = (): Array<{ pair: ConjunctionPair; index: number }> => {
    const overlay = state.overlay;
    const rows = data.pairs.map((pair, index) => ({ pair: pairUnder(pair, index, overlay), index }));
    if (!overlay) return rows;
    // Re-sorted here rather than by the exporter because the order depends on the scenario, and
    // shipping five orderings of the same 3,000 pairs would cost more than the sort does.
    return rows.sort((x, y) => (y.pair.max_pc ?? -1) - (x.pair.max_pc ?? -1));
  };

  const eventAt = (index: number): ConjunctionEvent => eventUnder(data.events[index], index, state.overlay);
  const quietEventAt = (index: number): ConjunctionEvent | null => {
    const baseline = state.baseline;
    if (!baseline || state.current === "quiet") return null;
    return eventUnder(data.events[index], index, baseline);
  };
  const quietPairAt = (index: number): ConjunctionPair | null => {
    const baseline = state.baseline;
    if (!baseline || state.current === "quiet") return null;
    return pairUnder(data.pairs[index], index, baseline);
  };

  let expanded: number | null = null;

  const renderHeader = () => {
    const rows = rankedPairs().map((r) => r.pair);
    const red = rows.filter((p) => p.flag === "red").length;
    const yellow = rows.filter((p) => p.flag === "yellow").length;
    const lowConfidence = rows.filter((p) => p.flag !== "none" && p.confidence === "low").length;
    const label = labelOf(state.current);
    header.innerHTML =
      `<div>${data.n_events_total.toLocaleString()} events over ${data.n_pairs.toLocaleString()} pairs, ` +
      `${escapeHtml(data.window.start.slice(0, 10))} to ${escapeHtml(data.window.end.slice(0, 10))}.</div>` +
      `<div class="muted">${red} red, ${yellow} yellow; ${lowConfidence} of them in the dilution region and ` +
      `not actionable. Scenario <code>${escapeHtml(label)}</code>, sorted by its probability.</div>`;
  };

  const matching = (): Array<{ pair: ConjunctionPair; index: number }> => {
    const q = filter.value.trim().toLowerCase();
    return rankedPairs().filter(({ pair }) => {
      if (onlyFlagged.checked && (pair.flag === "none" || pair.flag === "unscoreable")) return false;
      if (!q) return true;
      return (
        pair.secondary_name.toLowerCase().includes(q) ||
        pair.primary_name.toLowerCase().includes(q) ||
        String(pair.secondary_norad_id).includes(q)
      );
    });
  };

  const selectEvent = (pair: ConjunctionPair, event: ConjunctionEvent, eventIndex: number) => {
    onSelect({
      pair,
      event,
      primaryIndex: indexOfNorad.get(pair.primary_norad_id) ?? -1,
      secondaryIndex: indexOfNorad.get(pair.secondary_norad_id) ?? -1,
    });
    detail.hidden = false;
    detail.dataset.eventIndex = String(eventIndex);
    detail.innerHTML = eventDetailHtml(pair, event, quietEventAt(eventIndex), data.model_version, state.current);
    detail.scrollIntoView({ block: "nearest" });
  };

  const render = () => {
    renderHeader();
    const pairs = matching();
    const shown = pairs.slice(0, LIST_LIMIT);
    list.innerHTML = "";
    for (const { pair, index } of shown) {
      const quiet = quietPairAt(index);
      const row = document.createElement("div");
      row.className = "cj-row";
      const delta = quiet ? deltaAgainstQuiet(pair.max_pc, quiet.max_pc) : "";
      row.innerHTML =
        `<button class="cj-head" aria-expanded="${expanded === index}">` +
        `<span class="cj-names">${escapeHtml(pair.primary_name)} <span class="muted">vs</span> ` +
        `${escapeHtml(pair.secondary_name)}</span>` +
        // The miss quoted beside the probability is the miss of the event that produced it, which
        // for a pair seen many times is often not the closest pass. The closest is in the subtitle.
        `<span class="cj-nums">${fmtKm(pair.miss_at_max_pc_km ?? pair.closest_km)} km · ${fmtPc(pair.max_pc)} ` +
        `${flagChip(pair.flag, pair.confidence, pair.region)}${validityChip(pair.storm_validity)}</span>` +
        `<span class="muted cj-sub">${pair.n_events} event${pair.n_events === 1 ? "" : "s"} · ` +
        `closest ${fmtKm(pair.closest_km)} km · ` +
        `first ${escapeHtml(pair.first_tca.slice(5, 16).replace("T", " "))} · ${escapeHtml(pair.secondary_category)}` +
        `${pair.n_in_box > 0 ? ` · ${pair.n_in_box} in box` : ""}` +
        // The Δ is on every row, not only the interesting ones: seeing it small twenty times and
        // large once is how the phase's result is learnt from the screen.
        `${
          delta
            ? ` · <span class="cj-delta" title="${escapeHtml(deltaTitle(pair.max_pc, quiet!.max_pc))}">` +
              `${escapeHtml(delta)} vs quiet</span>`
            : ""
        }` +
        `</span>` +
        `</button>`;
      const head = row.querySelector<HTMLButtonElement>(".cj-head")!;
      head.addEventListener("click", () => {
        expanded = expanded === index ? null : index;
        render();
      });
      if (expanded === index) {
        const events = document.createElement("div");
        events.className = "cj-events";
        if (!pair.events.length) {
          events.innerHTML = `<p class="muted">Individual events for this pair are in the run's parquet; the
            viewer carries them for the flagged pairs, the pairs with an event in the box and the highest
            probabilities.</p>`;
        }
        for (const eventIndex of pair.events) {
          const event = eventAt(eventIndex);
          const quietEvent = quietEventAt(eventIndex);
          const button = document.createElement("button");
          button.className = "cj-event";
          button.innerHTML =
            `<span>${escapeHtml(event.tca.slice(5, 19).replace("T", " "))}</span>` +
            `<span>${fmtKm(missOf(event))} km</span>` +
            `<span>${fmtPc(event.pc)}</span>` +
            `<span class="muted">${escapeHtml(
              quietEvent ? deltaAgainstQuiet(event.pc, quietEvent.pc) : event.region,
            )}</span>`;
          button.addEventListener("click", () => selectEvent(pair, event, eventIndex));
          events.appendChild(button);
        }
        row.appendChild(events);
      }
      list.appendChild(row);
    }
    if (pairs.length > shown.length) {
      const more = document.createElement("p");
      more.className = "muted";
      more.textContent = `${pairs.length - shown.length} more pairs; narrow the filter to see them.`;
      list.appendChild(more);
    }
    if (!pairs.length) {
      list.innerHTML = `<p class="muted">No pair matches.</p>`;
    }
    // A detail view left open must follow the scenario, or it is showing the previous one's
    // numbers under the new one's name.
    const openIndex = detail.hidden ? null : Number(detail.dataset.eventIndex);
    if (openIndex != null && Number.isInteger(openIndex)) {
      const event = eventAt(openIndex);
      const pair = data.pairs.find((p) => p.events.includes(openIndex));
      if (pair) {
        const index = data.pairs.indexOf(pair);
        detail.innerHTML = eventDetailHtml(
          pairUnder(pair, index, state.overlay),
          event,
          quietEventAt(openIndex),
          data.model_version,
          state.current,
        );
      }
    }
  };

  filter.addEventListener("input", render, { signal });
  onlyFlagged.addEventListener("change", render, { signal });
  root.querySelector<HTMLButtonElement>("#conjunction-clear")?.addEventListener(
    "click",
    () => {
      detail.hidden = true;
      delete detail.dataset.eventIndex;
      onSelect(null);
    },
    { signal },
  );
  detail.hidden = true;
  delete detail.dataset.eventIndex;
  render();
  return { refresh: render };
}

const VALIDITY_TEXT: Record<string, string> = {
  validated:
    "validated — both objects have a ballistic coefficient fitted from their own decay, which is the " +
    "population Step 4 measured the storm term against (r = 0.88)",
  indicative:
    "indicative — at least one object's coefficient is a B* inversion, a population stand-in, or absent. " +
    "The storm term has no demonstrated skill there. The number is not adjusted for this.",
  none: "no storm term applied under this scenario",
};

function eventDetailHtml(
  pair: ConjunctionPair,
  event: ConjunctionEvent,
  quiet: ConjunctionEvent | null,
  modelVersion: string | null,
  scenario: string,
): string {
  const shifted = missOf(event);
  const stormy = event.relative_shift_km != null && event.relative_shift_km > 0;
  const rows: Array<[string, string]> = [
    ["Scenario", labelOf(scenario)],
    ["Time of closest approach", formatUtc(Date.parse(event.tca))],
    ["Miss distance", `${fmtKm(shifted)} km${stormy ? " (after the storm term moved both objects)" : ""}`],
  ];
  if (stormy) {
    rows.push(["Miss without the storm term", `${fmtKm(event.miss_km)} km`]);
    rows.push(["Relative displacement", `${fmtKm(event.relative_shift_km)} km`]);
  }
  rows.push(
    ["Relative speed", `${fmtKm(event.rel_speed_kms, 2)} km/s`],
    ["Combined hard-body radius", `${event.hbr_m?.toFixed(1) ?? "—"} m`],
    ["In-track sigma, primary", `${fmtKm(event.sigma_i_primary_km, 2)} km`],
    ["In-track sigma, secondary", `${fmtKm(event.sigma_i_secondary_km, 2)} km`],
    ["Covariance source", event.cov_source_secondary ?? "—"],
    ["Probability", fmtPc(event.pc)],
  );
  if (stormy) {
    rows.push(
      ["… objects moved only", fmtPc(event.pc_shift_only)],
      ["… covariance widened only", fmtPc(event.pc_variance_only)],
    );
  }
  if (quiet) {
    rows.push(["Probability under quiet", `${fmtPc(quiet.pc)} (${deltaAgainstQuiet(event.pc, quiet.pc)})`]);
    rows.push(["Region under quiet", `${quiet.region} · ${quiet.confidence}`]);
  }
  rows.push(
    ["Maximum probability", `${fmtPc(event.pc_max)} at ${event.pc_max_scale?.toFixed(2) ?? "—"}× the covariance`],
    ["Region", `${event.region}${event.confidence === "low" ? " (low confidence, not actionable)" : ""}`],
  );
  if (event.storm_validity && event.storm_validity !== "none") {
    rows.push(["Storm-term validity", VALIDITY_TEXT[event.storm_validity] ?? event.storm_validity]);
    rows.push([
      "Coefficient sources",
      `${event.storm_source_primary ?? "—"} / ${event.storm_source_secondary ?? "—"}`,
    ]);
  }

  const note =
    event.scoreable === false
      ? `<p class="caveat">This event carries <b>no probability at all</b> under this scenario, not a small one.
         ${escapeHtml(event.unscoreable_reason ?? "")} Past that the storm term has stopped being a small
         correction to a known position and has become a claim about where in its orbit the object is, which
         nothing here can support. The geometry, the covariance and the displacement all stand; only the
         number a reader could act on is withheld.</p>`
      : event.region === "dilution"
        ? `<p class="caveat">The maximum probability lies below the covariance used, so shrinking the uncertainty
           at the same miss would raise it. The number is held up by the size of the covariance rather than by the
           geometry: it says the trajectories are uncertain, not that a collision is likely &mdash; and equally not
           that one is unlikely. The data cannot support a judgement either way. Better tracking would shrink the
           covariance and move the nominal miss together, so nothing here predicts which way this would go.</p>`
        : `<p class="caveat">The probability is limited by the geometry rather than by the uncertainty. It still
           rests on a covariance estimated from how much each object's own element sets disagree, which is a floor
           on the error and not a measurement of it.</p>`;

  const stormNote = stormy
    ? `<p class="caveat">The dashed arrow is the storm's whole effect on the geometry: it runs from the quiet
       miss to this scenario's, drawn to the same scale as the ellipse, so a displacement lost inside the
       uncertainty looks lost. The two objects are displaced <i>nearly independently</i> &mdash; a conjunction
       is a crossing, at a median 120° between their two in-track directions &mdash; and it is the relative
       displacement above, not either object's own, that moves the miss.</p>`
    : "";

  return (
    `<h2>${escapeHtml(pair.primary_name)} vs ${escapeHtml(pair.secondary_name)}</h2>` +
    encounterPlaneSvg(event, quiet) +
    `<p class="muted">The encounter plane: the disc is the combined hard-body radius at the primary, the
      ellipses are the one and three sigma contours of the combined covariance about the miss, and the line
      between them is the miss vector. The probability is the mass of the ellipse's Gaussian inside the disc.</p>` +
    `<dl>${rows.map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd>`).join("")}</dl>` +
    note +
    stormNote +
    `<p class="caveat">Computed by driftwatch${modelVersion ? ` (${escapeHtml(modelVersion)})` : ""}; the
      viewer only draws it.</p>`
  );
}
