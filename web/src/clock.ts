/** The simulation clock: a UTC instant that advances at `speed` simulated seconds per wall second. */

export class SimClock {
  tMs: number;
  playing = true;
  speed = 60;
  readonly minMs: number;
  readonly maxMs: number;
  private listeners: Array<(clock: SimClock) => void> = [];

  constructor(t0Ms: number, windowHours: number) {
    this.tMs = t0Ms;
    const half = (windowHours / 2) * 3.6e6;
    this.minMs = t0Ms - half;
    this.maxMs = t0Ms + half;
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
