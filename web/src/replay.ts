/**
 * Replay mode: May 2024, scrubbed, without leaving the application.
 *
 * Phase 3 Step 5, revised at the Step 5 review. The Kp bar, the density ratio at 400 and 500 km,
 * the Sun image nearest the selected time and the conjunction list all move together, because
 * they are all driven by the one simulation clock the viewer already has. There is no second
 * timeline: the replay scrubber *is* the clock, drawn with the Kp bar as its background.
 *
 * **Replay is a mode, not a reload.** The first build entered it by navigating to `?replay`,
 * which was simple and cost the reader their camera, their selection and their scenario every
 * time they crossed the boundary. It is now a swap of the data source inside one live
 * application: `main.ts` unmounts the catalogue, mounts the other one, and carries over
 * everything that still means something (see `Carried` there). The URL still carries `?replay`
 * through `history.pushState`, so a replay is still a link somebody can send and the browser's
 * Back button still works — it is the reload that has gone, not the address.
 *
 * **The Sun is loaded lazily.** A seven-day replay is 29 frames at 360 kB, and fetching all of
 * them so that a reader can look at three is ten megabytes spent on a picture. Every frame
 * carries a 64 px thumbnail inline in `storm.json` (about 3 kB, so all of them together are a
 * fraction of one full image), which is drawn immediately at any scrub position; the full image
 * is fetched when the playhead comes near it, and the three marked `eager` by the exporter — the
 * first, the peak and the last — are requested up front. The caption says which of the two is on
 * screen, because a blurred 64 px disc presented as the Sun at a stated minute would be a small
 * lie.
 *
 * Everything drawn here comes from `storm.json`, written by `driftwatch replay-bundle`. The
 * browser computes no density and no Kp; it draws two series and picks the nearest image.
 */

import type { SimClock } from "./clock";
import { el, escapeHtml } from "./ui";

/** The query parameter that marks replay mode, and the directory it reads. */
export const REPLAY_PARAM = "replay";
export const REPLAY_BASE = "data/replay/";
export const LIVE_BASE = "data/";

/** How near the playhead has to come, in milliseconds, before a full frame is fetched. */
const PREFETCH_MS = 6 * 3600 * 1000;

export interface SunFrame {
  requested: string;
  actual: string | null;
  lag_minutes: number | null;
  path: string;
  bytes: number;
  /** A 64 px data URI, drawn while the full image is in flight. Null if the export had none. */
  thumb: string | null;
  /** Whether the exporter marked this one worth fetching before the reader scrubs. */
  eager: boolean;
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
  sun: {
    layers: string;
    citation: string;
    frames: SunFrame[];
    total_bytes: number;
    thumb_px?: number;
    n_eager?: number;
    n_with_thumb?: number;
  };
  notes: string[];
}

/** Whether the address bar says replay. Read once at startup; after that the mode is state. */
export function replayInUrl(): boolean {
  return new URLSearchParams(window.location.search).has(REPLAY_PARAM);
}

export function dataBaseFor(replay: boolean): string {
  return replay ? REPLAY_BASE : LIVE_BASE;
}

/**
 * Put `?replay` in the address bar, or take it out, without reloading.
 *
 * `pushState` rather than `replaceState` so the Back button leaves replay, which is what a
 * reader who arrived by clicking a button will expect it to do.
 */
export function setReplayInUrl(on: boolean): void {
  const url = new URL(window.location.href);
  if (on) url.searchParams.set(REPLAY_PARAM, "1");
  else url.searchParams.delete(REPLAY_PARAM);
  if (url.toString() !== window.location.href) window.history.pushState({ replay: on }, "", url);
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

const nearestIndex = <T>(items: T[], at: number, time: (item: T) => number): number => {
  let best = -1;
  let bestGap = Infinity;
  items.forEach((item, i) => {
    const gap = Math.abs(time(item) - at);
    if (gap < bestGap) {
      bestGap = gap;
      best = i;
    }
  });
  return best;
};

/**
 * Fetches full-resolution Sun frames on demand and remembers which have arrived.
 *
 * A frame is requested when the playhead comes within `PREFETCH_MS` of it, and at most one
 * request is in flight at a time so that dragging the scrubber across a week does not open
 * twenty-nine connections. A frame that fails is marked failed and not retried in a loop; its
 * thumbnail goes on being shown, which is a worse picture rather than no picture.
 */
class SunLoader {
  private readonly state = new Map<number, "pending" | "ready" | "failed">();
  private inflight = 0;

  constructor(
    private readonly frames: SunFrame[],
    private readonly base: string,
    private readonly onLoaded: (index: number) => void,
  ) {
    frames.forEach((frame, i) => {
      if (frame.eager) this.request(i);
    });
  }

  ready(index: number): boolean {
    return this.state.get(index) === "ready";
  }

  url(index: number): string {
    return this.base + this.frames[index].path;
  }

  /** Ask for `index` and anything else the playhead is about to reach. */
  ensure(index: number, nowMs: number): void {
    this.request(index);
    this.frames.forEach((frame, i) => {
      const at = Date.parse(frame.actual ?? frame.requested);
      if (Math.abs(at - nowMs) <= PREFETCH_MS) this.request(i);
    });
  }

  private request(index: number): void {
    if (index < 0 || index >= this.frames.length) return;
    if (this.state.has(index)) return;
    if (this.inflight >= 1 && !this.frames[index].eager) return;
    this.state.set(index, "pending");
    this.inflight++;
    const image = new Image();
    image.decoding = "async";
    image.onload = () => {
      this.state.set(index, "ready");
      this.inflight--;
      this.onLoaded(index);
    };
    image.onerror = () => {
      this.state.set(index, "failed");
      this.inflight--;
      console.warn("Sun frame failed to load:", this.frames[index].path);
    };
    image.src = this.url(index);
  }
}

export interface ReplayHandle {
  /** Called once per animation frame. Cheap: only the playhead and three text nodes move. */
  tick(): void;
  /** Hide the scrubber and release its listeners. */
  destroy(): void;
}

/**
 * Draw the scrubber and keep it, the Sun image and the readouts in step with the clock.
 *
 * The SVG is built once and only the playhead's `x` and a few text nodes change, so scrubbing
 * does not re-render the bar. Nothing here touches the point cloud.
 */
export function buildReplay(
  timeline: StormTimeline,
  clock: SimClock,
  base = REPLAY_BASE,
  signal?: AbortSignal,
): ReplayHandle {
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
  bar.addEventListener(
    "click",
    (ev) => {
      const rect = bar.getBoundingClientRect();
      const fraction = Math.min(Math.max((ev.clientX - rect.left) / rect.width, 0), 1);
      clock.playing = false;
      clock.set(startMs + fraction * span);
    },
    { signal },
  );

  let shown = -1;
  let shownFull = false;
  let lastKpIndex = -1;

  const paint = (index: number, full: boolean) => {
    const frame = timeline.sun.frames[index];
    if (!frame) return;
    shown = index;
    shownFull = full;
    image.src = full ? base + frame.path : (frame.thumb ?? base + frame.path);
    image.classList.toggle("placeholder", !full);
    image.hidden = false;
    const at = frame.actual ?? frame.requested;
    const lag = frame.lag_minutes;
    caption.innerHTML =
      `SDO/AIA 193 Å at ${escapeHtml(at.slice(0, 16).replace("T", " "))} UTC` +
      (lag != null && lag > 15 ? ` <span class="warn">· ${lag.toFixed(0)} min from the time asked for</span>` : "") +
      // A blurred 64 px disc presented as "the Sun at 11 May 12:00" would be a small lie, so it
      // is labelled until the real one arrives.
      (full ? "" : ` <span class="muted">· ${timeline.sun.thumb_px ?? 64} px preview, loading…</span>`) +
      ` <span class="muted">${escapeHtml(timeline.sun.citation)}</span>`;
  };

  const loader = new SunLoader(timeline.sun.frames, base, (index) => {
    if (index === shown && !shownFull) paint(index, true);
  });

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

    if (timeline.sun.frames.length) {
      const nearest = nearestIndex(timeline.sun.frames, now, (f) => Date.parse(f.actual ?? f.requested));
      loader.ensure(nearest, now);
      const full = loader.ready(nearest);
      if (nearest !== shown || (full && !shownFull)) paint(nearest, full);
    } else {
      image.hidden = true;
      caption.innerHTML =
        `<span class="muted">No Sun imagery in this bundle. Run <code>driftwatch replay-bundle &lt;run&gt;</code> ` +
        `without <code>--offline</code> to fetch a few frames a day from Helioviewer.</span>`;
    }
  };

  update();
  return {
    tick: update,
    destroy: () => {
      root.hidden = true;
      image.hidden = true;
      image.removeAttribute("src");
      image.classList.remove("placeholder");
      delete document.body.dataset.replay;
    },
  };
}

/**
 * The control that enters and leaves replay mode.
 *
 * Bound once for the life of the page, because the mode switch no longer reloads it. Returns a
 * setter the application calls after a switch so the label always describes what the button will
 * do next rather than what it did last.
 */
export function bindReplayControl(onToggle: (replay: boolean) => void): (replay: boolean, busy?: boolean) => void {
  const button = document.getElementById("replay-toggle");
  if (!(button instanceof HTMLButtonElement)) return () => void 0;
  let current = replayInUrl();

  const apply = (replay: boolean, busy = false) => {
    current = replay;
    button.disabled = busy;
    button.textContent = busy ? "loading…" : replay ? "leave replay" : "replay May 2024";
    button.title = replay
      ? "Return to the live catalogue and the current screening window"
      : "Load the historical catalogue for 9 May 2024 and scrub through the Gannon storm. " +
        "The Sun imagery and the historical positions are fetched only when you do this.";
  };

  button.addEventListener("click", () => onToggle(!current));
  // The Back button leaves replay, because a reader who arrived by clicking expects it to.
  window.addEventListener("popstate", () => {
    const wanted = replayInUrl();
    if (wanted !== current) onToggle(wanted);
  });
  apply(current);
  return apply;
}
