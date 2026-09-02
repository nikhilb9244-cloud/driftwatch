/**
 * The conjunctions panel: the screening run, as Python computed it.
 *
 * Nothing here is a screening result of the browser's own. The pairs, the events, the
 * probabilities, the covariances and the tracks all come out of `conjunctions.json` and
 * `conjunction-tracks.bin`, written by `driftwatch report`. The viewer's job is to put
 * them somewhere a reader can see them: a list of pairs (repeated encounters collapsed,
 * as the Step 2 review asked), the events of a pair on demand, and, when an event is
 * selected, the clock jumped to the time of closest approach, both objects highlighted,
 * ten minutes of each track drawn either side, and the encounter plane in an inset.
 *
 * The tracks are stored in TEME, the frame SGP4 works in, and are rotated to Earth-fixed
 * here with the same GMST that the propagation worker uses (`gstime`, UTC standing in for
 * UT1, no polar motion). Doing the rotation the same way in both places is what keeps a
 * drawn track sitting on its moving dot.
 */

import * as THREE from "three";
import { gstime } from "satellite.js";
import type { Bundle, ConjunctionEvent, ConjunctionPair } from "./data";
import { formatUtc } from "./geodesy";
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

  /**
   * Draw both tracks for `event`, rotating each TEME sample to Earth-fixed at its own time.
   *
   * GMST advances about five degrees over the twenty minutes of a track, so the rotation
   * has to be per sample; using one angle for the whole track would smear it by kilometres.
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

/**
 * The encounter plane as an SVG: the hard-body disc at the origin, the combined covariance
 * ellipse centred on the miss, and the miss vector between them.
 *
 * This is the picture the probability is an integral over: the plane perpendicular to the
 * relative velocity, the disc of the combined hard-body radius, and the Gaussian whose
 * mass inside that disc is the probability of collision.
 */
export function encounterPlaneSvg(event: ConjunctionEvent, size = 260): string {
  const xx = event.enc_cov_xx_km2 ?? 0;
  const xy = event.enc_cov_xy_km2 ?? 0;
  const yy = event.enc_cov_yy_km2 ?? 0;
  const { a, b, angle } = principalAxes(xx, xy, yy);
  const miss = event.miss_km;
  const hbr = (event.hbr_m ?? 0) / 1000;
  const extent = Math.max(miss + 3 * Math.max(a, b), 3 * Math.max(a, b), hbr * 4, 1e-6) * 1.15;
  const scale = size / 2 / extent;
  const cx = size / 2;
  const cy = size / 2;
  const mx = cx + miss * scale;
  const deg = (-angle * 180) / Math.PI;
  // The uncertainty is routinely thousands of times the hard-body radius, and the covariance
  // is far longer in-track than across. Drawn to scale the disc and the minor axis vanish, so
  // both get a floor of a couple of pixels and the caption says by how much the disc was grown.
  const minPx = 2.5;
  const ring = (k: number, opacity: number) =>
    `<ellipse cx="${mx.toFixed(2)}" cy="${cy}" rx="${Math.max(k * a * scale, minPx).toFixed(2)}" ` +
    `ry="${Math.max(k * b * scale, 1).toFixed(2)}" ` +
    `transform="rotate(${deg.toFixed(2)} ${mx.toFixed(2)} ${cy})" fill="rgba(76,201,240,0.10)" ` +
    `stroke="rgba(76,201,240,${opacity})" stroke-width="1"/>`;
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
  <rect x="0" y="0" width="${size}" height="${size}" fill="rgba(8,12,20,0.55)" rx="6"/>
  <line x1="0" y1="${cy}" x2="${size}" y2="${cy}" stroke="rgba(255,255,255,0.10)"/>
  <line x1="${cx}" y1="0" x2="${cx}" y2="${size}" stroke="rgba(255,255,255,0.10)"/>
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

function flagChip(flag: string, confidence: string, region: string): string {
  if (flag === "none") return "";
  const cls = confidence === "low" ? "flag low" : `flag ${flag}`;
  const title = confidence === "low" ? `${flag}, low confidence (${region} region): not actionable` : `${flag}`;
  const label = confidence === "low" ? `${flag} · low` : flag;
  return `<span class="${cls}" title="${escapeHtml(title)}">${escapeHtml(label)}</span>`;
}

export interface PanelHandles {
  /** Redraw the list, e.g. after the filter changes. */
  refresh(): void;
}

/**
 * Build the conjunctions panel. `onSelect` is called with the pair, the event and the two
 * point-cloud indices (-1 when the object is not in the catalogue bundle).
 */
export function buildConjunctionPanel(
  bundle: Bundle,
  onSelect: (selection: ConjunctionSelection | null) => void,
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

  const red = data.pairs.filter((p) => p.flag === "red").length;
  const yellow = data.pairs.filter((p) => p.flag === "yellow").length;
  const lowConfidence = data.pairs.filter((p) => p.flag !== "none" && p.confidence === "low").length;
  header.innerHTML =
    `<div>${data.n_events_total.toLocaleString()} events over ${data.n_pairs.toLocaleString()} pairs, ` +
    `${escapeHtml(data.window.start.slice(0, 10))} to ${escapeHtml(data.window.end.slice(0, 10))}.</div>` +
    `<div class="muted">${red} red, ${yellow} yellow; ${lowConfidence} of them in the dilution region and ` +
    `not actionable. Scenario <code>${escapeHtml(data.scenario)}</code>.</div>`;

  let expanded: number | null = null;

  const matching = (): ConjunctionPair[] => {
    const q = filter.value.trim().toLowerCase();
    return data.pairs.filter((p) => {
      if (onlyFlagged.checked && p.flag === "none") return false;
      if (!q) return true;
      return (
        p.secondary_name.toLowerCase().includes(q) ||
        p.primary_name.toLowerCase().includes(q) ||
        String(p.secondary_norad_id).includes(q)
      );
    });
  };

  const selectEvent = (pair: ConjunctionPair, event: ConjunctionEvent) => {
    onSelect({
      pair,
      event,
      primaryIndex: indexOfNorad.get(pair.primary_norad_id) ?? -1,
      secondaryIndex: indexOfNorad.get(pair.secondary_norad_id) ?? -1,
    });
    detail.hidden = false;
    detail.innerHTML = eventDetailHtml(pair, event, data.model_version);
    detail.scrollIntoView({ block: "nearest" });
  };

  const render = () => {
    const pairs = matching();
    const shown = pairs.slice(0, LIST_LIMIT);
    list.innerHTML = "";
    for (const pair of shown) {
      const index = data.pairs.indexOf(pair);
      const row = document.createElement("div");
      row.className = "cj-row";
      row.innerHTML =
        `<button class="cj-head" aria-expanded="${expanded === index}">` +
        `<span class="cj-names">${escapeHtml(pair.primary_name)} <span class="muted">vs</span> ` +
        `${escapeHtml(pair.secondary_name)}</span>` +
        // The miss quoted beside the probability is the miss of the event that produced it, which
        // for a pair seen many times is often not the closest pass. The closest is in the subtitle.
        `<span class="cj-nums">${fmtKm(pair.miss_at_max_pc_km ?? pair.closest_km)} km · ${fmtPc(pair.max_pc)} ${flagChip(pair.flag, pair.confidence, pair.region)}</span>` +
        `<span class="muted cj-sub">${pair.n_events} event${pair.n_events === 1 ? "" : "s"} · ` +
        `closest ${fmtKm(pair.closest_km)} km · ` +
        `first ${escapeHtml(pair.first_tca.slice(5, 16).replace("T", " "))} · ${escapeHtml(pair.secondary_category)}` +
        `${pair.n_in_box > 0 ? ` · ${pair.n_in_box} in box` : ""}</span>` +
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
          const event = data.events[eventIndex];
          const button = document.createElement("button");
          button.className = "cj-event";
          button.innerHTML =
            `<span>${escapeHtml(event.tca.slice(5, 19).replace("T", " "))}</span>` +
            `<span>${fmtKm(event.miss_km)} km</span>` +
            `<span>${fmtPc(event.pc)}</span>` +
            `<span class="muted">${escapeHtml(event.region)}</span>`;
          button.addEventListener("click", () => selectEvent(pair, event));
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
  };

  filter.addEventListener("input", render);
  onlyFlagged.addEventListener("change", render);
  root.querySelector<HTMLButtonElement>("#conjunction-clear")?.addEventListener("click", () => {
    detail.hidden = true;
    onSelect(null);
  });
  render();
  return { refresh: render };
}

function eventDetailHtml(pair: ConjunctionPair, event: ConjunctionEvent, modelVersion: string | null): string {
  const rows: Array<[string, string]> = [
    ["Time of closest approach", formatUtc(Date.parse(event.tca))],
    ["Miss distance", `${fmtKm(event.miss_km)} km`],
    ["Relative speed", `${fmtKm(event.rel_speed_kms, 2)} km/s`],
    ["Radial, in-track, cross-track", `${fmtKm(event.miss_r_km, 2)}, ${fmtKm(event.miss_i_km, 2)}, ${fmtKm(event.miss_c_km, 2)} km`],
    ["Combined hard-body radius", `${event.hbr_m?.toFixed(1) ?? "—"} m`],
    ["In-track sigma, primary", `${fmtKm(event.sigma_i_primary_km, 2)} km`],
    ["In-track sigma, secondary", `${fmtKm(event.sigma_i_secondary_km, 2)} km`],
    ["Covariance source", event.cov_source_secondary ?? "—"],
    ["Probability", fmtPc(event.pc)],
    ["Maximum probability", `${fmtPc(event.pc_max)} at ${event.pc_max_scale?.toFixed(2) ?? "—"}× the covariance`],
    ["Region", `${event.region}${event.confidence === "low" ? " (low confidence, not actionable)" : ""}`],
  ];
  const note =
    event.region === "dilution"
      ? `<p class="caveat">The maximum probability lies below the covariance used, so shrinking the uncertainty
         at the same miss would raise it. The number is held up by the size of the covariance rather than by the
         geometry: it says the trajectories are uncertain, not that a collision is likely &mdash; and equally not
         that one is unlikely. The data cannot support a judgement either way. Better tracking would shrink the
         covariance and move the nominal miss together, so nothing here predicts which way this would go.</p>`
      : `<p class="caveat">The probability is limited by the geometry rather than by the uncertainty. It still
         rests on a covariance estimated from how much each object's own element sets disagree, which is a floor
         on the error and not a measurement of it.</p>`;
  return (
    `<h2>${escapeHtml(pair.primary_name)} vs ${escapeHtml(pair.secondary_name)}</h2>` +
    encounterPlaneSvg(event) +
    `<p class="muted">The encounter plane: the disc is the combined hard-body radius at the primary, the
      ellipses are the one and three sigma contours of the combined covariance about the miss, and the line
      between them is the miss vector. The probability is the mass of the ellipse's Gaussian inside the disc.</p>` +
    `<dl>${rows.map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd>`).join("")}</dl>` +
    note +
    `<p class="caveat">Computed by driftwatch${modelVersion ? ` (${escapeHtml(modelVersion)})` : ""}; the
      viewer only draws it.</p>`
  );
}
