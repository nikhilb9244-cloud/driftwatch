/** The simulation clock: a UTC instant that advances at `speed` simulated seconds per wall second. */

export class SimClock {
  tMs: number;
  playing = true;
  speed = 60;
  minMs: number;
  maxMs: number;
  /**
   * The middle of the window, which is the bundle's reference time and what the `t₀` button
   * jumps to. It moves with the range, so entering replay does not leave the button pointing at
   * a moment two years away.
   */
  t0Ms: number;
  private listeners: Array<(clock: SimClock) => void> = [];

  /**
   * `range` widens the window beyond the bundle's own, so that a screening window longer
   * than the propagated window is still reachable: selecting a conjunction seven days out
   * must move the clock there rather than stop at the edge.
   */
  constructor(t0Ms: number, windowHours: number, range?: { minMs: number; maxMs: number }) {
    this.tMs = t0Ms;
    this.t0Ms = t0Ms;
    const half = (windowHours / 2) * 3.6e6;
    this.minMs = Math.min(t0Ms - half, range?.minMs ?? Infinity);
    this.maxMs = Math.max(t0Ms + half, range?.maxMs ?? -Infinity);
  }

  /**
   * Move the clock to a different window without replacing it.
   *
   * Entering replay changes *when* the viewer is, by two years, but not *what* it is: one
   * application, one clock, one set of transport controls, and the bindings in `ui.ts` stay
   * attached across the switch. `keepFraction` carries the reader's position through the window
   * over, which is the only part of a 2026 instant that still means anything in May 2024 — the
   * two windows are the same length, so "four days in" survives the move and the instant does
   * not.
   */
  setRange(
    t0Ms: number,
    windowHours: number,
    range?: { minMs: number; maxMs: number },
    opts: { keepFraction?: boolean } = {},
  ): void {
    const fraction = opts.keepFraction ? this.fraction : 0;
    const half = (windowHours / 2) * 3.6e6;
    this.t0Ms = t0Ms;
    this.minMs = Math.min(t0Ms - half, range?.minMs ?? Infinity);
    this.maxMs = Math.max(t0Ms + half, range?.maxMs ?? -Infinity);
    this.tMs = opts.keepFraction ? this.minMs + fraction * (this.maxMs - this.minMs) : t0Ms;
    this.emit();
  }

  /** Advance by a wall-clock interval in milliseconds. Pauses at the window edges. */
  tick(dtWallMs: number): void {
    if (!this.playing) return;
    const next = this.tMs + dtWallMs * this.speed;
    if (next >= this.maxMs) {
      this.tMs = this.maxMs;
      this.playing = false;
    } else if (next <= this.minMs) {
      this.tMs = this.minMs;
      this.playing = false;
    } else {
      this.tMs = next;
    }
    this.emit();
  }

  set(tMs: number): void {
    this.tMs = Math.min(this.maxMs, Math.max(this.minMs, tMs));
    this.emit();
  }

  /** Position within the window in [0, 1]. */
  get fraction(): number {
    return (this.tMs - this.minMs) / (this.maxMs - this.minMs);
  }

  onChange(fn: (clock: SimClock) => void): void {
    this.listeners.push(fn);
  }

  private emit(): void {
    for (const fn of this.listeners) fn(this);
  }
}
