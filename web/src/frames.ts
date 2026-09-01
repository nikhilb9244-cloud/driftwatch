/**
 * Frame store: asks the worker for Earth-fixed states on a time grid and keeps the
 * bracketing pair installed in the point cloud.
 *
 * The grid is anchored at the reference time. Its step grows with playback speed so
 * the worker is asked for a new frame roughly every 200 ms of wall time; at 60x that
 * is a one-minute step, at 1000x a 200-second step.
 */

import type { CataloguePoints, Frame } from "./points";

export interface WorkerStats {
  engine: string;
  lastComputeMs: number;
}

type FrameMessage = {
  type: "frame";
  tMs: number;
  pos: Float32Array;
  vel: Float32Array;
  err: Int8Array;
  computeMs: number;
};

export class FrameStore {
  private readonly cache = new Map<number, Frame>();
  private readonly inflight = new Set<number>();
  private queue: number[] = [];
  private busy = false;
  stats: WorkerStats = { engine: "starting", lastComputeMs: 0 };
  onStats: ((s: WorkerStats) => void) | null = null;

  constructor(
    private readonly worker: Worker,
    private readonly points: CataloguePoints,
    private readonly anchorMs: number,
  ) {
    worker.addEventListener("message", (ev: MessageEvent) => this.onMessage(ev.data));
  }

  /** Grid step in ms for a given playback speed (simulated seconds per wall second). */
  static stepMs(speed: number): number {
    const s = Math.max(60, Math.min(900, speed * 0.2));
    return Math.round(s) * 1000;
  }

  /**
   * Make sure the frames bracketing `tMs` are installed, requesting them if needed and
   * prefetching the next frame in the direction of travel.
   */
  ensure(tMs: number, speed: number, direction: 1 | -1 = 1): void {
    const step = FrameStore.stepMs(speed);
    const ta = this.anchorMs + Math.floor((tMs - this.anchorMs) / step) * step;
    const tb = ta + step;
    const a = this.cache.get(ta);
    const b = this.cache.get(tb);
    if (a && b) {
      this.points.setFrames(a, b);
      this.points.setTime(tMs);
      const ahead = direction > 0 ? tb + step : ta - step;
      this.request(ahead);
    } else {
      // Keep showing the last pair while the new one is computed.
      if (this.points.hasFrames) this.points.setTime(tMs);
      if (!a) this.request(ta);
      if (!b) this.request(tb);
    }
    this.evict(tMs, step);
  }

  private request(tMs: number): void {
    if (this.cache.has(tMs) || this.inflight.has(tMs) || this.queue.includes(tMs)) return;
    this.queue.push(tMs);
    this.pump();
  }

  private pump(): void {
    if (this.busy || this.queue.length === 0) return;
    const tMs = this.queue.shift()!;
    this.busy = true;
    this.inflight.add(tMs);
    this.worker.postMessage({ type: "frame", tMs });
  }

  private onMessage(msg: FrameMessage | { type: string; [k: string]: unknown }): void {
    if (msg.type === "frame") {
      const m = msg as FrameMessage;
      this.inflight.delete(m.tMs);
      this.cache.set(m.tMs, { tMs: m.tMs, pos: m.pos, vel: m.vel, err: m.err });
      this.stats.lastComputeMs = m.computeMs;
      this.onStats?.(this.stats);
      this.busy = false;
      this.pump();
    } else if (msg.type === "ready") {
      this.stats.engine = String(msg.engine);
      this.onStats?.(this.stats);
    }
  }

  private evict(tMs: number, step: number): void {
    if (this.cache.size <= 12) return;
    const keys = [...this.cache.keys()].sort((x, y) => Math.abs(x - tMs) - Math.abs(y - tMs));
    for (const k of keys.slice(8)) {
      if (Math.abs(k - tMs) > 3 * step) this.cache.delete(k);
    }
  }
}
