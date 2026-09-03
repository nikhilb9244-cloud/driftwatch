/**
 * The storm control, the storm summary and the unscoreable section.
 *
 * Built to the console specification in `docs/design-brief.md` §3.1 and §5, so that the Phase 4
 * console inherits this rather than replacing it:
 *
 * - **A segmented control of five on desktop** — `quiet · forecast · G3 · G4 · G5` — and a
 *   dropdown below 900 px. Replay is not a sixth segment; it is a mode, with its own control,
 *   because it changes the meaning of the whole screen rather than only the numbers in it.
 * - **Names in full, never abbreviated.** `G4` alone next to a probability is too easy to read
 *   as a flag.
 * - **A scenario the run was not scored under is shown and disabled**, with the reason, rather
 *   than hidden: the reader should know the option exists.
 * - **Changing it re-renders the panel in place and does not touch the point cloud.**
 *
 * The summary block is the one place the storm's effect is stated as a number rather than
 * implied by a list, and it is given **both ways** — over the events whose two objects both
 * have a ballistic coefficient measured from their own decay, and over the rest. Step 4 found
 * the storm term predictive at r = 0.88 for the first group and of no demonstrated skill for
 * the second, and the split is not decoration: on the demo run's G5 the median
 * `pc / pc_variance_only` is 0.16 over the validated events and 0.89 over the indicative ones.
 * The combined figure is shown last and never alone, because it averages a large real effect
 * with a near-absent unmeasured one, weighted by the coverage of the coefficient fit rather
 * than by physics.
 */

import type { Bundle } from "./data";
import {
  SCENARIO_HELP,
  isReplayScenario,
  labelOf,
  type ScenarioFigures,
  type ScenarioState,
} from "./scenarios";
import { el, escapeHtml } from "./ui";

const NARROW_PX = 900;

const REPLAY_HELP =
  "The weather that actually happened over this window, driving the storm term on a catalogue "  +
  "rebuilt as it stood before the storm. Nothing here is synthetic and nothing is forecast.";

const fmtRatio = (v: number | null | undefined): string =>
  v == null || !Number.isFinite(v) ? "—" : v >= 100 ? `×${v.toFixed(0)}` : `×${v.toFixed(2)}`;

const fmtKm = (v: number | null | undefined, digits = 1): string =>
  v == null || !Number.isFinite(v) ? "—" : v.toFixed(digits);

/** `validated`, `indicative`, `combined` — in that order, and only those actually present. */
function orderedPopulations(summary: Record<string, ScenarioFigures>): string[] {
  return ["validated", "indicative", "combined"].filter((k) => summary[k]);
}

/**
 * Wire the scenario control and the summary. Returns a redraw function the panel calls when
 * the scenario changes; it never re-renders the list itself, which the panel owns.
 */
export function buildStormControl(
  bundle: Bundle,
  state: ScenarioState,
  onChange: () => void,
  signal?: AbortSignal,
): () => void {
  const root = document.getElementById("storm");
  if (!root || !bundle.conjunctions) {
    if (root) root.hidden = true;
    return () => void 0;
  }
  root.hidden = false;
  const segments = el<HTMLDivElement>("storm-segments");
  const select = el<HTMLSelectElement>("storm-select");
  const note = el<HTMLDivElement>("storm-note");
  const summary = el<HTMLDivElement>("storm-summary");
  const unscoreable = el<HTMLDetailsElement>("storm-unscoreable");
  // Emptied first: the two controls are rebuilt whenever the catalogue changes, and a replay
  // offers a different set of scenarios from the live view.
  segments.replaceChildren();
  select.replaceChildren();

  const scored = new Set(state.scored);
  const isScored = (name: string) => scored.has(name);

  // Both controls are built once and CSS decides which is visible, so a resize past 900 px
  // does not lose the selection or need a rebuild.
  for (const name of state.offered) {
    const button = document.createElement("button");
    button.className = "storm-seg";
    button.type = "button";
    button.dataset.scenario = name;
    button.textContent = labelOf(name);
    button.disabled = !isScored(name);
    button.title = isScored(name)
      ? (SCENARIO_HELP[name] ?? (isReplayScenario(name) ? REPLAY_HELP : ""))
      : `not scored for this run — run \`driftwatch risk <run> --scenario ${name}\``;
    button.addEventListener(
      "click",
      () => {
        state.select(name);
      },
      { signal },
    );
    segments.appendChild(button);

    const option = document.createElement("option");
    option.value = name;
    option.textContent = labelOf(name);
    option.disabled = !isScored(name);
    select.appendChild(option);
  }
  select.addEventListener("change", () => state.select(select.value), { signal });

  const renderNote = () => {
    if (state.pending) {
      note.textContent = "Loading the other scenarios…";
      return;
    }
    if (state.error) {
      note.innerHTML =
        `<span class="warn">Only <code>${escapeHtml(bundle.conjunctions!.scenario)}</code> is available: ` +
        `the scenario overlays could not be loaded (${escapeHtml(state.error)}). Every number on screen is ` +
        `still that scenario's own.</span>`;
      return;
    }
    note.textContent =
      SCENARIO_HELP[state.current] ?? (isReplayScenario(state.current) ? REPLAY_HELP : "");
  };

  const renderSummary = () => {
    const figures = state.summary();
    if (!figures) {
      summary.innerHTML = "";
      summary.hidden = true;
      return;
    }
    const populations = orderedPopulations(figures);
    const moved = figures.combined?.n_moved ?? 0;
    if (state.current === "quiet" || moved === 0) {
      summary.hidden = false;
      summary.innerHTML =
        `<p class="muted">No storm term under <code>${escapeHtml(state.current)}</code>: this is the Phase 2 ` +
        `model untouched, and it is the baseline every other scenario is read against. Pick another scenario ` +
        `to see what a storm does to these events.</p>`;
      return;
    }
    summary.hidden = false;
    const head = populations.map((p) => `<th>${escapeHtml(p)}<span class="muted"> (${figures[p].n_events})</span></th>`);
    const row = (label: string, get: (f: ScenarioFigures) => string) =>
      `<tr><th scope="row">${escapeHtml(label)}</th>${populations.map((p) => `<td>${get(figures[p])}</td>`).join("")}</tr>`;
    summary.innerHTML =
      `<table class="storm-table"><thead><tr><th></th>${head.join("")}</tr></thead><tbody>` +
      row("Events moved", (f) => f.n_moved.toLocaleString()) +
      row("Median relative shift", (f) => `${fmtKm(f.median_relative_shift_km)} km`) +
      row("Median pc / variance only", (f) => fmtRatio(f.median_pc_over_variance_only).replace("×", "")) +
      row("Lowered by the shift", (f) => f.n_lowered_by_shift.toLocaleString()) +
      row("Raised by the shift", (f) => f.n_raised_by_shift.toLocaleString()) +
      row("Red / yellow", (f) => `${f.n_red} / ${f.n_yellow}`) +
      row("Not scored", (f) => String(f.n_unscoreable)) +
      `</tbody></table>` +
      // Folded away rather than dropped: it is needed once, and the queue is what is being read.
      `<details class="storm-explainer"><summary>What these columns mean, and why a storm lowers most
        probabilities</summary>` +
      `<p class="caveat"><b>Both columns, always.</b> <code>validated</code> means both objects of the event
        have a ballistic coefficient fitted from their own decay history; <code>indicative</code> means at
        least one rests on a B* inversion, a population stand-in, or no coefficient at all. Step 4 measured
        the storm term against the May 2024 record and found it predictive at a correlation of 0.88 for the
        first group and of <b>no demonstrated skill</b> for the second. Nothing is weighted or withheld by
        the label — the numbers are identical either way — but a median taken across both populations
        together is an average of a measured effect and an unmeasured one.</p>` +
      `<p class="caveat"><b>Why a storm usually lowers the probability.</b> It displaces the two objects by
        tens of kilometres while their misses are a few, and a displacement that large applied to a near
        miss separates more pairs than it creates. The two displacements are <i>not</i> alike: the relative
        shift that reaches the miss is a median 1.91 times the mean of the two absolute shifts, out of a
        possible 2, because a conjunction is a crossing at a median 120°. (An earlier version of this tool
        explained the same result by common-mode cancellation between the two objects; that explanation was
        measured and withdrawn on 2026-09-03. The result stands.)</p>` +
      `</details>`;
  };

  const renderUnscoreable = () => {
    const rows = state.unscoreable();
    if (!rows.length) {
      unscoreable.hidden = true;
      return;
    }
    unscoreable.hidden = false;
    const objects = new Set(rows.map((r) => r.reason.split(":")[0]));
    unscoreable.innerHTML =
      `<summary>${rows.length} event${rows.length === 1 ? "" : "s"} not scored — the storm term is outside ` +
      `its own derivation for ${objects.size} object${objects.size === 1 ? "" : "s"}</summary>` +
      `<p class="caveat">These carry <b>no probability at all</b>, not a small one. The in-track displacement
        the scenario gives one of the two objects has run past a quarter of its orbit's circumference, past
        the small-perturbation linearisation the term was derived under; a number computed from such a
        position would be arithmetic with no claim behind it. They are listed here rather than in the queue
        because they cannot be ranked by a number they do not have, and a blank in a probability column would
        read as "safe".</p>` +
      `<ul class="storm-unscoreable">` +
      rows
        .slice(0, 40)
        .map(
          (r) =>
            `<li><span>${escapeHtml(r.primary_name)} <span class="muted">vs</span> ` +
            `${escapeHtml(r.secondary_name)}</span>` +
            `<span class="muted">${escapeHtml(r.tca.slice(5, 16).replace("T", " "))} · ` +
            `${fmtKm(r.miss_km, 2)} km quiet miss</span>` +
            `<span class="muted">${escapeHtml(r.reason)}</span></li>`,
        )
        .join("") +
      (rows.length > 40 ? `<li class="muted">…and ${rows.length - 40} more; the run's parquet has them all.</li>` : "") +
      `</ul>`;
  };

  const render = () => {
    for (const button of segments.querySelectorAll<HTMLButtonElement>(".storm-seg")) {
      button.setAttribute("aria-pressed", String(button.dataset.scenario === state.current));
    }
    select.value = state.current;
    // Until the overlays land, only the scenario already in the bundle can be shown.
    const usable = (name: string) => name === bundle.conjunctions!.scenario || state.overlayFor(name) !== null;
    for (const button of segments.querySelectorAll<HTMLButtonElement>(".storm-seg")) {
      const name = button.dataset.scenario!;
      button.disabled = !isScored(name) || !usable(name);
    }
    for (const option of select.querySelectorAll<HTMLOptionElement>("option")) {
      option.disabled = !isScored(option.value) || !usable(option.value);
    }
    renderNote();
    renderSummary();
    renderUnscoreable();
  };

  state.onChange(() => {
    render();
    onChange();
  });
  render();
  // A mode switch rebuilds this block, and the browser keeps the old scroll offset -- which
  // left the heading above the fold and the section looking truncated rather than compact.
  root.scrollTop = 0;

  // Narrow layouts get the dropdown; the media query in the stylesheet does the switching, and
  // this only mirrors it into `aria-hidden` so a screen reader is not offered both.
  const applyWidth = () => {
    const narrow = window.innerWidth < NARROW_PX;
    segments.setAttribute("aria-hidden", String(narrow));
    select.setAttribute("aria-hidden", String(!narrow));
  };
  window.addEventListener("resize", applyWidth, { signal });
  applyWidth();
  return render;
}
