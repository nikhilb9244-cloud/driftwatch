/**
 * Replay mode: May 2024, scrubbed.
 *
 * Phase 3 Step 5. The Kp bar, the density ratio at 400 and 500 km, the Sun image nearest the
 * selected time and the conjunction list all move together, because they are all driven by the
 * one simulation clock the viewer already has. There is no second timeline: the replay scrubber
 * *is* the clock, drawn with the Kp bar as its background.
 *
 * **Replay is a mode, not a sixth scenario** (`docs/design-brief.md` §3.1). It changes what the
 * whole screen means — the times become historical, the catalogue becomes the one that existed
 * on 9 May 2024, and the fleet has Sentinel-1A standing in for Sentinel-1C, which did not launch
 * until December of that year. So it is entered from its own control, not from the segmented
 * scenario control beside it.
 *
 * **Entering it navigates to `?replay`, which reloads the viewer against `data/replay/`.**
 * That looks blunt and is the deliberate choice. The alternative — holding two catalogues in
 * memory and swapping the point cloud's buffers — would put a second code path through the one
 * part of this project Phase 1 asked not to be touched, for a mode a reader enters once. A
 * reload keeps exactly one catalogue alive, keeps the propagation worker's initialisation
 * unchanged, and has the side benefit of making a replay a link somebody can send. The replay
 * bundle is never fetched until that navigation happens, which is what §8 of the brief asks for.
 *
 * Everything drawn here comes from `storm.json`, written by `driftwatch replay-bundle`. The
 * browser computes no density and no Kp; it draws two series and picks the nearest image.
 */

import type { SimClock } from "./clock";
import { el, escapeHtml } from "./ui";

/** The query parameter that puts the viewer in replay mode, and the directory it then reads. */
export const REPLAY_PARAM = "replay";
export const REPLAY_BASE = "data/replay/";

export interface SunFrame {
  requested: string;
  actual: string | null;
  lag_minutes: number | null;
  path: string;
  bytes: number;
}

export interface StormTimeline {
  storm_version: number;
  scenario: string;
  run_id: string | null;
  snapshot: string | null;
  window: { start: string; end: string };
  kp: { t: string[]; kp: (number | null)[]; ap: (number | null)[]; provenance: string[] };
  density: {
    altitudes_km: number[];
    t: string[];
    quiet_baseline_kg_m3: Record<string, string>;
    quiet_window: string[];
    [key: string]: unknown;
  };
  sun: { layers: string; citation: string; frames: SunFrame[]; total_bytes: number };
  notes: string[];
}

export function isReplay(): boolean {
  return new URLSearchParams(window.location.search).has(REPLAY_PARAM);
}

/** The data directory the viewer should read: the replay bundle in replay mode, else the live one. */
export function dataBase(): string {
  return isReplay() ? REPLAY_BASE : "data/";
}

export async function loadTimeline(base = REPLAY_BASE): Promise<StormTimeline | null> {
  try {
    const res = await fetch(base + "storm.json");
    if (!res.ok) return null;
    const data = (await res.json()) as StormTimeline;
    return data.storm_version === 1 ? data : null;
  } catch (err) {
    console.warn("No replay timeline:", err);
    return null;
  }
}

/** NOAA's G scale from Kp, for the label beside the bar. Kp 5 is G1, 9 is G5. */
function gLevel(kp: number | null): string {
  if (kp == null || !Number.isFinite(kp)) return "";
  if (kp >= 9) return "G5";
  if (kp >= 8) return "G4";
  if (kp >= 7) return "G3";
  if (kp >= 6) return "G2";
  if (kp >= 5) return "G1";
  return "";
}

/**
 * The one place in the viewer the G ramp appears, as `docs/design-brief.md` §5 reserves it.
 * Below Kp 5 the bar is the neutral panel colour: a quiet interval is not a small storm.
 */
function kpColour(kp: number | null): string {
  if (kp == null || !Number.isFinite(kp)) return "rgba(255,255,255,0.10)";
  if (kp < 5) return "rgba(141,153,174,0.45)";
  const ramp = ["#f6c744", "#f4a261", "#ee8959", "#e2554f", "#c1121f"];
  return ramp[Math.min(4, Math.floor(kp - 5))];
}

const nearest = <T>(items: T[], at: number, time: (item: T) => number): T | null => {
  let best: T | null = null;
  let bestGap = Infinity;
  for (const item of items) {
    const gap = Math.abs(time(item) - at);
    if (gap < bestGap) {
      bestGap = gap;
      best = item;
    }
  }
  return best;
};

/**
 * Draw the scrubber and keep it, the Sun image and the readouts in step with the clock.
 *
 * Returns a function the animation loop calls each frame. It is cheap: the SVG is built once
 * and only the playhead's `x` and three text nodes change, so scrubbing does not re-render the
 * bar. Nothing here touches the point cloud.
 */
export function buildReplay(timeline: StormTimeline, clock: SimClock, base = REPLAY_BASE): () => void {
  const root = el<HTMLDivElement>("replay");
  root.hidden = false;
  // The scrubber is fixed to the bottom, so the two side panels have to stop above it rather
  // than run under it. One attribute, and the stylesheet does the rest.
  document.body.dataset.replay = "1";
  const bar = el<HTMLDivElement>("replay-bar");
  const readout = el<HTMLDivElement>("replay-readout");
  const image = el<HTMLImageElement>("replay-sun");
  const caption = el<HTMLDivElement>("replay-sun-caption");

  const times = timeline.kp.t.map((t) => Date.parse(t));
  const startMs = Date.parse(timeline.window.start);
  const endMs = Date.parse(timeline.window.end);
  const span = Math.max(endMs - startMs, 1);
  const width = 1000;
  const height = 64;
  const x = (ms: number) => ((ms - startMs) / span) * width;

  // The Kp bar. One rectangle per three-hour interval, full height, coloured by the G ramp.
  const barWidth = width / Math.max(times.length, 1);
  const bars = times
    .map((t, i) => {
      const kp = timeline.kp.kp[i];
      const h = kp == null ? 0 : Math.max(2, (Math.min(kp, 9) / 9) * height);
      const forecast = timeline.kp.provenance[i] !== "observed";
      return (
        `<rect x="${x(t).toFixed(2)}" y="${(height - h).toFixed(2)}" width="${Math.max(barWidth - 0.5, 0.5).toFixed(2)}" ` +
        `height="${h.toFixed(2)}" fill="${kpColour(kp)}" ${forecast ? 'opacity="0.55"' : ""}/>`
      );
    })
    .join("");

  // The two density ratios, as polylines over the bar. Scaled to the largest ratio in the
  // window so the shape is legible; the axis label says what the top of the box is.
  const altitudes = timeline.density.altitudes_km;
  const densityTimes = timeline.density.t.map((t) => Date.parse(t));
  const series = altitudes.map((a) => (timeline.density[`ratio_${Math.round(a)}km`] as (number | null)[]) ?? []);
  const peak = Math.max(1.2, ...series.flat().filter((v): v is number => v != null && Number.isFinite(v)));
  const colours = ["#4cc9f0", "#a0e8b7"];
  const lines = series
    .map((values, k) => {
      const points = values
        .map((v, i) => (v == null ? null : `${x(densityTimes[i]).toFixed(1)},${(height - (v / peak) * height).toFixed(1)}`))
        .filter((p): p is string => p !== null)
        .join(" ");
      return `<polyline points="${points}" fill="none" stroke="${colours[k % colours.length]}" stroke-width="1.5" opacity="0.9"/>`;
    })
    .join("");

  bar.innerHTML =
    `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" ` +
    `aria-label="Kp through the replay window with the density ratio at 400 and 500 km over it">` +
    bars +
    lines +
    `<line id="replay-playhead" x1="0" y1="0" x2="0" y2="${height}" stroke="#ffd166" stroke-width="2"/>` +
    `</svg>`;
  const playhead = bar.querySelector<SVGLineElement>("#replay-playhead")!;

  el<HTMLDivElement>("replay-legend").innerHTML =
    `<span><i class="swatch kp"></i>Kp, three-hourly (paler where forecast rather than observed)</span>` +
    altitudes
      .map(
        (a, k) =>
          `<span><i class="swatch" style="background:${colours[k % colours.length]}"></i>` +
          `density ratio at ${Math.round(a)} km</span>`,
      )
      .join("") +
    `<span class="muted">top of the box is ×${peak.toFixed(1)}; the ratio's denominator is the quiet window ` +
    `${escapeHtml(timeline.density.quiet_window[0].slice(0, 10))} to ` +
    `${escapeHtml(timeline.density.quiet_window[1].slice(0, 10))}, the same one Step 4 measured against</span>`;

  // Clicking the bar scrubs, which is what a reader will try first.
  bar.addEventListener("click", (ev) => {
    const rect = bar.getBoundingClientRect();
    const fraction = Math.min(Math.max((ev.clientX - rect.left) / rect.width, 0), 1);
    clock.playing = false;
    clock.set(startMs + fraction * span);
  });

  let shownFrame: SunFrame | null = null;
  let lastKpIndex = -1;

  const update = () => {
    const now = clock.tMs;
    playhead.setAttribute("x1", String(x(now)));
    playhead.setAttribute("x2", String(x(now)));

    // The interval the clock is inside, not the nearest one: Kp is a three-hour average and
    // reporting the next interval's value before it has happened would be a small forecast.
    let index = -1;
    for (let i = 0; i < times.length; i++) if (times[i] <= now) index = i;
    if (index !== lastKpIndex) {
      lastKpIndex = index;
      const kp = index >= 0 ? timeline.kp.kp[index] : null;
      const ap = index >= 0 ? timeline.kp.ap[index] : null;
      const g = gLevel(kp);
      const ratios = altitudes
        .map((a, k) => {
          const values = series[k];
          let j = -1;
          for (let i = 0; i < densityTimes.length; i++) if (densityTimes[i] <= now) j = i;
          const v = j >= 0 ? values[j] : null;
          return `<span><b>×${v == null ? "—" : v.toFixed(2)}</b> at ${Math.round(a)} km</span>`;
        })
        .join("");
      readout.innerHTML =
        `<span>Kp <b>${kp == null ? "—" : kp.toFixed(2)}</b>${g ? ` <span class="g">${g}</span>` : ""}</span>` +
        `<span class="muted">ap ${ap == null ? "—" : ap.toFixed(0)}</span>` +
        ratios;
    }

    const frame = nearest(timeline.sun.frames, now, (f) => Date.parse(f.actual ?? f.requested));
    if (frame && frame !== shownFrame) {
      shownFrame = frame;
      image.src = base + frame.path;
      image.hidden = false;
      const at = frame.actual ?? frame.requested;
      const lag = frame.lag_minutes;
      caption.innerHTML =
        `SDO/AIA 193 Å at ${escapeHtml(at.slice(0, 16).replace("T", " "))} UTC` +
        (lag != null && lag > 15
          ? ` <span class="warn">· ${lag.toFixed(0)} min from the time asked for</span>`
          : "") +
        ` <span class="muted">${escapeHtml(timeline.sun.citation)}</span>`;
    }
    if (!timeline.sun.frames.length) {
      image.hidden = true;
      caption.innerHTML =
        `<span class="muted">No Sun imagery in this bundle. Run <code>driftwatch replay-bundle &lt;run&gt;</code> ` +
        `without <code>--offline</code> to fetch a few frames a day from Helioviewer.</span>`;
    }
  };

  update();
  return update;
}

/**
 * The control that enters and leaves replay mode. Present on both, because a reader who has
 * scrubbed through May 2024 needs a way back that is not the browser's history.
 */
export function bindReplayControl(): void {
  const button = document.getElementById("replay-toggle");
  if (!(button instanceof HTMLButtonElement)) return;
  const on = isReplay();
  button.textContent = on ? "leave replay" : "replay May 2024";
  button.title = on
    ? "Return to the live catalogue and the current screening window"
    : "Load the historical catalogue for 9 May 2024 and scrub through the Gannon storm. " +
      "The Sun imagery and the historical positions are fetched only when you do this.";
  button.addEventListener("click", () => {
    const url = new URL(window.location.href);
    if (on) url.searchParams.delete(REPLAY_PARAM);
    else url.searchParams.set(REPLAY_PARAM, "1");
    window.location.href = url.toString();
  });
}
