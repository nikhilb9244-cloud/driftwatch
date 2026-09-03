/**
 * driftwatch viewer entry point.
 *
 * Load the bundle, put a globe on screen, hand the elements to the propagation worker,
 * and drive a simulation clock. The point cloud interpolates between worker frames on
 * the GPU (see points.ts); the main thread only touches per-object data on hover.
 */

import Globe, { type GlobeInstance } from "globe.gl";
import * as THREE from "three";
import { SimClock } from "./clock";
import { buildConjunctionPanel, ConjunctionTracks, type ConjunctionSelection } from "./conjunctions";
import { loadBundle, type Bundle } from "./data";
import { FrameStore } from "./frames";
import { pick } from "./picking";
import { CataloguePoints, SCENE_PER_KM } from "./points";
import { bindReplayControl, buildReplay, dataBase, isReplay, loadTimeline } from "./replay";
import { ScenarioState } from "./scenarios";
import { buildStormControl } from "./storm";
import { bindClock, buildFilterControls, describe, el, filterMask, findObject, showSelected, showTooltip } from "./ui";

async function main(): Promise<void> {
  const loading = el<HTMLDivElement>("loading");
  // Replay mode reads a different directory: the historical catalogue for 9 May 2024, that
  // run's own conjunctions, and the storm timeline. Nothing of it is fetched otherwise. See
  // replay.ts for why entering the mode is a navigation rather than a swap in place.
  const base = dataBase();
  const bundle = await loadBundle(base);
  loading.textContent = `Propagating ${bundle.n.toLocaleString()} objects…`;

  // Globe ----------------------------------------------------------------------
  const container = el<HTMLDivElement>("globe");
  const globe = new Globe(container)
    .globeImageUrl("textures/earth-blue-marble.jpg")
    .bumpImageUrl("textures/earth-topology.png")
    .backgroundImageUrl("textures/night-sky.png")
    .showAtmosphere(true)
    .atmosphereAltitude(0.12)
    .showGraticules(false);
  const camera = globe.camera() as THREE.PerspectiveCamera;
  camera.far = 100 * 400; // cislunar objects sit at a few thousand globe radii; keep them in view
  camera.updateProjectionMatrix();
  globe.controls().maxDistance = 100 * 60;
  globe.pointOfView({ lat: -20, lng: 25, altitude: 2.4 }, 0);
  verifyGlobeConvention(globe);

  // Points ----------------------------------------------------------------------
  const categoryIndex = Int32Array.from(bundle.objects.category);
  const points = new CataloguePoints(bundle.n, categoryIndex, bundle.manifest.categories);
  globe.scene().add(points.points);

  // Worker ----------------------------------------------------------------------
  const worker = new Worker(new URL("./propagator.worker.ts", import.meta.url), { type: "module" });
  // A screening window can be longer than the propagated window; the clock has to reach the whole of it.
  const screening = bundle.conjunctions?.window;
  const clock = new SimClock(
    bundle.t0Ms,
    bundle.manifest.window_hours,
    screening ? { minMs: Date.parse(screening.start), maxMs: Date.parse(screening.end) } : undefined,
  );
  const frames = new FrameStore(worker, points, bundle.t0Ms);
  frames.onStats = (s) => {
    el("stat-engine").textContent = s.engine;
    el("stat-frame").textContent = `${s.lastComputeMs.toFixed(0)} ms for ${bundle.n.toLocaleString()} objects`;
  };
  const ready = new Promise<void>((resolve) => {
    const onReady = (ev: MessageEvent) => {
      if (ev.data?.type === "ready") {
        worker.removeEventListener("message", onReady);
        resolve();
      }
    };
    worker.addEventListener("message", onReady);
  });
  const elementsCopy = bundle.elements.slice();
  worker.postMessage(
    { type: "init", elements: elementsCopy, fields: bundle.elementFields, perObject: bundle.manifest.files.elements.per_object },
    [elementsCopy.buffer],
  );
  await ready;
  loading.hidden = true;

  // Cross-check satellite.js against the Python reference state at t0.
  checkAgainstReference(worker, bundle);

  // UI ---------------------------------------------------------------------------
  bindClock(clock);
  const filters = buildFilterControls(bundle, (f) => {
    points.setFilter(filterMask(bundle, f));
    updateVisible();
  });
  points.setFilter(filterMask(bundle, filters));
  el("stat-snapshot").textContent = bundle.manifest.snapshot.replace(/^gp_/, "").replace(/\.parquet$/, "");
  el("stat-t0").textContent = bundle.manifest.reference_time.replace("T", " ").replace(/\.\d+Z$/, "Z");
  el("stat-age").textContent = describeAges(bundle);
  el("credit").textContent = (bundle.manifest.attribution ?? []).join(" ");

  let selected = -1;
  let hovered = -1;
  let pairSecondary = -1;
  const updateVisible = () => {
    el("stat-visible").textContent = `${points.visibleCount().toLocaleString()} of ${bundle.n.toLocaleString()}`;
  };

  const find = el<HTMLInputElement>("find");
  find.addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter") return;
    const i = findObject(bundle, find.value);
    selected = i;
    points.setHighlight(i);
    showSelected(i >= 0 ? describe(bundle, points, i) : null);
    if (i < 0) find.setCustomValidity("No match");
    else find.setCustomValidity("");
    find.reportValidity();
  });
  el("clear").addEventListener("click", () => {
    selected = -1;
    pairSecondary = -1;
    points.setHighlight(-1);
    showSelected(null);
  });

  // Conjunctions panel: Python's events, drawn here. Selecting one jumps the clock to the
  // time of closest approach, highlights both objects and draws ten minutes of each track.
  //
  // Storm mode sits on top of it: the scenario control re-renders this panel and nothing else.
  // The point cloud, the worker and the tracks are geometry and do not depend on the scenario,
  // which is the Phase 1 rule and the reason a storm costs no frames.
  const tracks = new ConjunctionTracks(bundle.conjunctions?.tracks.samples ?? 0);
  globe.scene().add(tracks.object3d);
  const scenarios = new ScenarioState(bundle, bundle.conjunctions?.scenario ?? "quiet");
  const panel = buildConjunctionPanel(bundle, scenarios, (selection: ConjunctionSelection | null) => {
    if (!selection) {
      pairSecondary = -1;
      tracks.hide();
      points.setHighlight(selected, -1);
      return;
    }
    clock.playing = false;
    clock.set(Date.parse(selection.event.tca));
    selected = selection.primaryIndex;
    pairSecondary = selection.secondaryIndex;
    points.setHighlight(selected, pairSecondary);
    showSelected(selected >= 0 ? describe(bundle, points, selected) : null);
    tracks.show(bundle, selection.event);
  });
  buildStormControl(bundle, scenarios, () => panel.refresh());
  bindReplayControl();
  // Fetched after the first paint, never before it: the critical path is the size it was
  // before storm mode existed, and a reader who never touches the control never pays for it.
  const idle = (window as unknown as { requestIdleCallback?: (fn: () => void) => void }).requestIdleCallback;
  const fetchOverlays = () => void scenarios.load(base);
  if (idle) idle(fetchOverlays);
  else setTimeout(fetchOverlays, 500);

  // Replay: the Kp bar, the density ratios and the Sun, all driven by the same clock as the
  // objects, so scrubbing moves everything together.
  let tickReplay: (() => void) | null = null;
  if (isReplay()) {
    const timeline = await loadTimeline(base);
    if (timeline) tickReplay = buildReplay(timeline, clock, base);
    else console.warn("Replay mode without a timeline; run `driftwatch replay-bundle <run>`");
  }

  // Hover picking, throttled.
  let lastPick = 0;
  let pointer = { x: -1, y: -1, inside: false };
  container.addEventListener("pointermove", (ev) => {
    pointer = { x: ev.clientX, y: ev.clientY, inside: true };
  });
  container.addEventListener("pointerleave", () => {
    pointer.inside = false;
    hovered = -1;
    showTooltip(null, 0, 0);
    if (selected < 0) points.setHighlight(-1, pairSecondary);
  });
  container.addEventListener("click", () => {
    if (hovered >= 0) {
      selected = hovered;
      points.setHighlight(selected, pairSecondary);
      showSelected(describe(bundle, points, selected));
    }
  });

  // Animation loop ---------------------------------------------------------------
  let last = performance.now();
  let lastT = clock.tMs;
  const loop = (now: number) => {
    const dt = Math.min(now - last, 250);
    last = now;
    clock.tick(dt);
    const direction: 1 | -1 = clock.tMs >= lastT ? 1 : -1;
    lastT = clock.tMs;
    frames.ensure(clock.tMs, clock.speed, direction);

    if (pointer.inside && now - lastPick > 40 && points.hasFrames) {
      lastPick = now;
      const rect = container.getBoundingClientRect();
      const i = pick(points, camera, pointer.x - rect.left, pointer.y - rect.top, rect.width, rect.height);
      hovered = i;
      showTooltip(i >= 0 ? describe(bundle, points, i) : null, pointer.x, pointer.y);
      points.setHighlight(i >= 0 ? i : selected, pairSecondary);
    }
    if (selected >= 0 && (now | 0) % 8 === 0) showSelected(describe(bundle, points, selected));
    if (tickReplay) tickReplay();
    requestAnimationFrame(loop);
  };
  clock.onChange(() => void 0);
  requestAnimationFrame(loop);
  setInterval(updateVisible, 1000);
  updateVisible();
}

/** Assert our Earth-fixed -> scene mapping matches globe.gl's lat/lon convention. */
function verifyGlobeConvention(globe: GlobeInstance): void {
  const R = 6371;
  const cases: Array<[number, number]> = [
    [0, 0],
    [45, 90],
    [-30, 31],
    [60, -120],
  ];
  for (const [lat, lon] of cases) {
    const la = (lat * Math.PI) / 180;
    const lo = (lon * Math.PI) / 180;
    const x = R * Math.cos(la) * Math.cos(lo);
    const y = R * Math.cos(la) * Math.sin(lo);
    const z = R * Math.sin(la);
    const ours = new THREE.Vector3(y, z, x).multiplyScalar(SCENE_PER_KM);
    const ref = globe.getCoords(lat, lon, 0);
    const d = ours.distanceTo(new THREE.Vector3(ref.x, ref.y, ref.z));
    if (d > 1e-6 * 100) {
      console.error("Globe coordinate convention mismatch", { lat, lon, ours, ref, d });
      throw new Error("Globe coordinate convention mismatch; see console");
    }
  }
}

function describeAges(bundle: Bundle): string {
  const ages = bundle.objects.epoch_age_days.filter((a): a is number => a !== null).sort((a, b) => a - b);
  if (!ages.length) return "—";
  const q = (p: number) => ages[Math.min(ages.length - 1, Math.floor(p * ages.length))];
  return `median ${q(0.5).toFixed(2)} d, p90 ${q(0.9).toFixed(2)} d, max ${ages[ages.length - 1].toFixed(1)} d`;
}

/**
 * Ask the worker for TEME states at the reference time and compare with the Python
 * sgp4 output shipped in reference.bin. Reported in the status panel so the reader can
 * see that the two implementations agree, and by how much.
 */
function checkAgainstReference(worker: Worker, bundle: Bundle): void {
  const out = el("stat-check");
  const onMessage = (ev: MessageEvent) => {
    if (ev.data?.type !== "eci") return;
    worker.removeEventListener("message", onMessage);
    const pos = ev.data.pos as Float64Array;
    const err = ev.data.err as Int8Array;
    const ref = bundle.reference;
    const diffs: number[] = [];
    let mismatchedErrors = 0;
    for (let i = 0; i < bundle.n; i++) {
      const refOk = Number.isFinite(ref[i * 6]);
      const jsOk = err[i] === 0 && Number.isFinite(pos[i * 3]);
      if (refOk !== jsOk) {
        mismatchedErrors++;
        continue;
      }
      if (!refOk) continue;
      const dx = pos[i * 3] - ref[i * 6];
      const dy = pos[i * 3 + 1] - ref[i * 6 + 1];
      const dz = pos[i * 3 + 2] - ref[i * 6 + 2];
      diffs.push(Math.hypot(dx, dy, dz) * 1000); // metres
    }
    diffs.sort((a, b) => a - b);
    const median = diffs.length ? diffs[Math.floor(diffs.length / 2)] : NaN;
    const max = diffs.length ? diffs[diffs.length - 1] : NaN;
    out.textContent = `median ${median.toFixed(1)} m, max ${max.toFixed(1)} m over ${diffs.length.toLocaleString()} objects` +
      (mismatchedErrors ? `; ${mismatchedErrors} error-status mismatches` : "");
    console.info("driftwatch: satellite.js vs Python sgp4 at t0", { medianM: median, maxM: max, n: diffs.length, mismatchedErrors });
  };
  worker.addEventListener("message", onMessage);
  worker.postMessage({ type: "eci", tMs: bundle.t0Ms });
}

main().catch((err) => {
  console.error(err);
  const loading = el<HTMLDivElement>("loading");
  loading.hidden = false;
  const how = isReplay()
    ? 'Run "uv run driftwatch propagate --snapshot <as-of file> --at 2024-05-09T00:00:00Z --export-dir web/public/data/replay", then "driftwatch report <replay run> --out-dir web/public/data/replay" and "driftwatch replay-bundle <replay run>".'
    : 'Run "uv run driftwatch propagate --at <time>" first.';
  loading.textContent = `Failed to start: ${err instanceof Error ? err.message : String(err)}. ${how}`;
});
