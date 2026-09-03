/**
 * Storm mode: the same events under every scenario, switched in the panel and nowhere else.
 *
 * Phase 3 Step 5. The rule that governs this whole file is the Phase 1 one: **the scenario
 * control changes numbers in the panel, not the point cloud.** Nothing here touches the
 * propagation worker, the globe, the element sets or the frame budget. A scenario is a
 * different covariance and a different set of positions at the stored times of closest
 * approach; it is not a different catalogue, and re-propagating 32,000 objects because a
 * reader clicked `G4` would be both slow and wrong.
 *
 * `scenarios.json` carries only what a scenario changes, in columns parallel to the base
 * bundle's `events` and `pairs` arrays (see `driftwatch/export/storm.py`). It is fetched
 * **after** first paint, so the critical path is the size it was before storm mode existed;
 * until it arrives the control is disabled and says so rather than silently doing nothing.
 *
 * Two things about the numbers, both of which the panel has to say out loud.
 *
 * **The miss under a scenario is the shifted miss.** The geometry's `miss_km` is what the two
 * element sets predicted; a storm scenario moved both objects, and its probability was computed
 * from where they ended up. Showing one beside the other would put two answers to different
 * questions on the same row.
 *
 * **`storm_validity` is not a confidence score.** It says whether Step 4's May 2024 validation
 * reaches the event: `validated` when both objects have a ballistic coefficient fitted from
 * their own decay, `indicative` otherwise. The storm term is predictive at r = 0.88 for the
 * first group and has no demonstrated skill for the second. Nothing here weights, dims or
 * withholds a number because of it — the numbers are identical either way — but every aggregate
 * is shown both ways, because on the demo run the two populations disagree by a factor of five
 * on the one quantity this phase is about.
 */

import type { Bundle, ConjunctionEvent, ConjunctionPair } from "./data";

/** A label column, dictionary-encoded by the exporter: distinct values plus per-row codes. */
export interface Encoded {
  v: string[];
  i: number[];
}

export interface EventOverlay {
  pc: (number | null)[];
  pc_shift_only: (number | null)[];
  pc_variance_only: (number | null)[];
  pc_max: (number | null)[];
  pc_max_scale: (number | null)[];
  miss_shifted_km: (number | null)[];
  relative_shift_km: (number | null)[];
  shift_i_primary_km: (number | null)[];
  shift_i_secondary_km: (number | null)[];
  sigma_i_primary_km: (number | null)[];
  sigma_i_secondary_km: (number | null)[];
  enc_cov_xx_km2: (number | null)[];
  enc_cov_xy_km2: (number | null)[];
  enc_cov_yy_km2: (number | null)[];
  region: Encoded;
  flag: Encoded;
  confidence: Encoded;
  storm_validity: Encoded;
  storm_source_primary: Encoded;
  storm_source_secondary: Encoded;
  unscoreable_reason: Encoded;
  scoreable: boolean[];
}

export interface PairOverlay {
  max_pc: (number | null)[];
  closest_km: (number | null)[];
  miss_at_max_pc_km: (number | null)[];
  pc_cumulative: (number | null)[];
  max_pc_max: (number | null)[];
  region: Encoded;
  flag: Encoded;
  confidence: Encoded;
  storm_validity: Encoded;
  n_scoreable: number[];
}

/** One population's figures. `null` where the population has none of that kind of event. */
export interface ScenarioFigures {
  n_events: number;
  n_moved: number;
  median_relative_shift_km: number | null;
  p90_relative_shift_km: number | null;
  median_pc_over_variance_only: number | null;
  n_lowered_by_shift: number;
  n_raised_by_shift: number;
  n_red: number;
  n_yellow: number;
  n_unscoreable: number;
}

export interface UnscoreableRow {
  event_id: string;
  primary_name: string;
  secondary_name: string;
  secondary_norad_id: number;
  tca: string;
  miss_km: number | null;
  reason: string;
}

export interface ScenarioOverlay {
  events: EventOverlay;
  pairs: PairOverlay;
  /** Keyed `validated` / `indicative` / `combined`; `combined` is always present and always last. */
  summary: Record<string, ScenarioFigures>;
  unscoreable: UnscoreableRow[];
  n_events_total: number;
}

export interface Overlays {
  overlay_version: number;
  run_id: string;
  n_events: number;
  n_pairs: number;
  scenarios: Record<string, ScenarioOverlay>;
  descriptions: Record<string, string>;
  notes: string[];
}

/** Every scenario the live viewer offers, in the order the segmented control shows them. */
export const SCENARIO_ORDER = ["quiet", "forecast", "storm-g3", "storm-g4", "storm-g5"] as const;

export const isReplayScenario = (name: string): boolean => name === "replay" || name.startsWith("replay:");

/** `replay:2024-05-09` reads as `observed record, 9 May 2024`. Never as `replay`. */
export function replayLabel(name: string): string {
  const date = name.includes(":") ? name.split(":")[1] : "";
  if (!date) return "observed record";
  const when = new Date(`${date}T00:00:00Z`);
  const text = Number.isNaN(when.valueOf())
    ? date
    : when.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  return `observed record, ${text}`;
}

/** The name to show for any scenario, live or replay. */
export function labelOf(name: string): string {
  return isReplayScenario(name) ? replayLabel(name) : (SCENARIO_LABELS[name] ?? name);
}

/** Full names. Never abbreviated in the UI: `G4` alone beside a probability reads as a flag. */
export const SCENARIO_LABELS: Record<string, string> = {
  quiet: "quiet",
  forecast: "forecast",
  "storm-g3": "G3 storm",
  "storm-g4": "G4 storm",
  "storm-g5": "G5 storm",
};

export const SCENARIO_HELP: Record<string, string> = {
  quiet:
    "The Phase 2 model untouched: no storm layer, no displacement. The baseline every other scenario is read against.",
  forecast:
    "NOAA SWPC's three-day Kp forecast, the 27-day outlook beyond it, and the observed record where it reaches.",
  "storm-g3": "The May 2024 sequence scaled to a peak Kp of 7, starting one day into the window.",
  "storm-g4": "The May 2024 sequence scaled to a peak Kp of 8, starting one day into the window.",
  "storm-g5": "The May 2024 sequence very nearly unscaled — a peak Kp of 9, as May 2024 itself reached.",
};

export function decode(column: Encoded | undefined, i: number): string {
  if (!column || !column.i) return "";
  const code = column.i[i];
  return code == null ? "" : (column.v[code] ?? "");
}

/**
 * The numbers of one event under one scenario, or the bundle's own values when no overlay
 * is loaded. The shape is the base event's, so every caller reads one type.
 */
export function eventUnder(
  event: ConjunctionEvent,
  index: number,
  overlay: ScenarioOverlay | null,
): ConjunctionEvent {
  if (!overlay) return event;
  const e = overlay.events;
  const at = <T>(a: T[] | undefined): T | undefined => (a ? a[index] : undefined);
  return {
    ...event,
    pc: at(e.pc) ?? null,
    pc_shift_only: at(e.pc_shift_only) ?? null,
    pc_variance_only: at(e.pc_variance_only) ?? null,
    pc_max: at(e.pc_max) ?? null,
    pc_max_scale: at(e.pc_max_scale) ?? null,
    // The scenario's miss, which is the one its probability was computed from.
    miss_shifted_km: at(e.miss_shifted_km) ?? null,
    relative_shift_km: at(e.relative_shift_km) ?? null,
    sigma_i_primary_km: at(e.sigma_i_primary_km) ?? null,
    sigma_i_secondary_km: at(e.sigma_i_secondary_km) ?? null,
    enc_cov_xx_km2: at(e.enc_cov_xx_km2) ?? null,
    enc_cov_xy_km2: at(e.enc_cov_xy_km2) ?? null,
    enc_cov_yy_km2: at(e.enc_cov_yy_km2) ?? null,
    region: decode(e.region, index) || event.region,
    flag: decode(e.flag, index) || event.flag,
    confidence: decode(e.confidence, index) || event.confidence,
    storm_validity: decode(e.storm_validity, index) || "none",
    storm_source_primary: decode(e.storm_source_primary, index) || "none",
    storm_source_secondary: decode(e.storm_source_secondary, index) || "none",
    unscoreable_reason: decode(e.unscoreable_reason, index),
    scoreable: at(e.scoreable) ?? true,
  };
}

export function pairUnder(pair: ConjunctionPair, index: number, overlay: ScenarioOverlay | null): ConjunctionPair {
  if (!overlay) return pair;
  const p = overlay.pairs;
  const at = <T>(a: T[] | undefined): T | undefined => (a ? a[index] : undefined);
  return {
    ...pair,
    max_pc: at(p.max_pc) ?? null,
    closest_km: at(p.closest_km) ?? pair.closest_km,
    miss_at_max_pc_km: at(p.miss_at_max_pc_km) ?? null,
    pc_cumulative: at(p.pc_cumulative) ?? null,
    max_pc_max: at(p.max_pc_max) ?? null,
    region: decode(p.region, index) || pair.region,
    flag: decode(p.flag, index) || pair.flag,
    confidence: decode(p.confidence, index) || pair.confidence,
    storm_validity: decode(p.storm_validity, index) || "none",
    n_scoreable: at(p.n_scoreable) ?? pair.n_events,
  };
}

/**
 * Holds the loaded overlays and the scenario in force, and tells its subscribers when either
 * changes. Deliberately tiny: the panel owns the rendering, this owns the state.
 */
export class ScenarioState {
  private overlays: Overlays | null = null;
  private listeners: Array<() => void> = [];
  private loading = false;
  /** Set when the fetch failed, so the control can say why rather than staying inert. */
  error: string | null = null;
  current: string;

  constructor(
    private readonly bundle: Bundle,
    private readonly base: string,
  ) {
    this.current = base;
  }

  /** Scenarios this run was actually scored under, in the control's fixed order. */
  get scored(): string[] {
    const stored = this.bundle.conjunctions?.scenarios ?? [];
    const set = new Set(stored);
    return [...SCENARIO_ORDER.filter((s) => set.has(s)), ...stored.filter(isReplayScenario)];
  }

  /**
   * Every scenario the control shows. Scored or not in the live view, because a reader should
   * know a G4 exists even where this run has not been scored under one; **only the scored ones
   * in a replay**, because a synthetic G5 dropped into May 2024 would be a different object
   * from the storm that actually happened, and offering it beside the observed record — even
   * greyed — would invite exactly that reading. A replay run is scored under `quiet` and its
   * own observed record, and those are the two the comparison is between.
   */
  get offered(): string[] {
    const scored = this.scored;
    if (scored.some(isReplayScenario)) return scored;
    return [...SCENARIO_ORDER];
  }

  get ready(): boolean {
    return this.overlays !== null;
  }

  get pending(): boolean {
    return this.loading;
  }

  /** The overlay in force, or null when the current scenario is the one already in the bundle. */
  get overlay(): ScenarioOverlay | null {
    if (!this.overlays) return null;
    return this.overlays.scenarios[this.current] ?? null;
  }

  overlayFor(name: string): ScenarioOverlay | null {
    return this.overlays?.scenarios[name] ?? null;
  }

  /** The quiet baseline, for the Δ column. Null when quiet was not scored for this run. */
  get baseline(): ScenarioOverlay | null {
    return this.overlayFor("quiet");
  }

  onChange(fn: () => void): void {
    this.listeners.push(fn);
  }

  private emit(): void {
    for (const fn of this.listeners) fn();
  }

  /**
   * Fetch the overlays. Called once, after first paint. A failure is not fatal: the viewer
   * carries on showing the bundle's own scenario, which is a complete and honest answer.
   */
  async load(base = "data/"): Promise<void> {
    if (this.overlays || this.loading) return;
    this.loading = true;
    this.emit();
    try {
      const res = await fetch(base + "scenarios.json");
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = (await res.json()) as Overlays;
      if (data.overlay_version !== 1) throw new Error(`unsupported overlay version ${data.overlay_version}`);
      const n = this.bundle.conjunctions?.events.length ?? 0;
      if (data.n_events !== n) {
        throw new Error(`overlay has ${data.n_events} events, bundle has ${n}; they are not the same run`);
      }
      this.overlays = data;
      this.error = null;
    } catch (err) {
      this.error = err instanceof Error ? err.message : String(err);
      console.warn("Scenario overlays unavailable:", err);
    } finally {
      this.loading = false;
      this.emit();
    }
  }

  select(name: string): void {
    if (name === this.current) return;
    if (name !== this.base && !this.overlayFor(name)) return;
    this.current = name;
    this.emit();
  }

  /** The figures for the scenario in force, both ways. Falls back to the bundle's own block. */
  summary(): Record<string, ScenarioFigures> | null {
    const fromOverlay = this.overlay?.summary;
    if (fromOverlay) return fromOverlay;
    if (this.current === this.base) return this.bundle.conjunctions?.storm?.summary ?? null;
    return null;
  }

  unscoreable(): UnscoreableRow[] {
    const fromOverlay = this.overlay?.unscoreable;
    if (fromOverlay) return fromOverlay;
    if (this.current === this.base) return this.bundle.conjunctions?.storm?.unscoreable ?? [];
    return [];
  }
}
