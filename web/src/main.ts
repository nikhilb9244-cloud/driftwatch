/**
 * driftwatch viewer entry point.
 *
 * Load a bundle, put a globe on screen, hand the elements to the propagation worker, and drive
 * a simulation clock. The point cloud interpolates between worker frames on the GPU (see
 * points.ts); the main thread only touches per-object data on hover.
 *
 * **One application, two catalogues.** Replay is a mode, not a second page: the globe, the
 * camera, the clock, the transport controls and the animation loop are created once and live
 * for the life of the tab, while the *catalogue* — the bundle, the point cloud, the worker, the
 * frame store, the conjunctions panel and the storm control — is mounted and unmounted around
 * them. `mountCatalogue` builds that set and returns the state worth carrying to the next one;
 * `Carried` is the list of what survives a switch and, just as importantly, what does not.
 *
 * What survives: the camera (it is never touched by a switch), the time *position through the
 * window* (the two windows are the same length, two years apart, so "four days in" carries and
 * the instant does not), the playback speed and whether it was playing, the category and band
 * filters by name, the selected object by NORAD id, and the scenario by name. What does not: an
 * absolute time, an object the other catalogue does not hold, and a scenario the other run was
 * not scored under. Each of those is reported rather than silently dropped.
 */

import Globe, { type GlobeInstance } from "globe.gl";
import * as THREE from "three";
import { SimClock } from "./clock";
import { buildConjunctionPanel, ConjunctionTracks, type ConjunctionSelection } from "./conjunctions";
import { loadBundle, type Bundle } from "./data";
import { FrameStore } from "./frames";
import { pick } from "./picking";
import { CataloguePoints, SCENE_PER_KM } from "./points";
import {
  bindReplayControl,
  buildReplay,
  dataBaseFor,
  loadTimeline,
  replayInUrl,
  setReplayInUrl,
  type ReplayHandle,
} from "./replay";
import { ScenarioState } from "./scenarios";
import { buildStormControl } from "./storm";
import {
  bindClock,
  buildFilterControls,
  describe,
  el,
  filterMask,
  filterNames,
  findObject,
  showSelected,
  showTooltip,
  type FilterNames,
} from "./ui";

/** What is worth carrying from one catalogue to the next. See the module docstring. */
interface Carried {
  noradId: number | null;
  scenario: string | null;
  fraction: number;
  filters: FilterNames | null;
  speed: number;
  playing: boolean;
}

interface Mounted {
  bundle: Bundle;
  points: CataloguePoints;
  frames: FrameStore;
  tracks: ConjunctionTracks;
  replay: ReplayHandle | null;
  /** Per-frame work owned by this catalogue. */
  tick(nowMs: number): void;
  /** Called when the pointer moves or the loop wants a hover test. */
  hover(x: number, y: number, rect: DOMRect): void;
  clearHover(): void;
  click(): void;
  unmount(): Carried;
}

async function main(): Promise<void> {
  const loading = el<HTMLDivElement>("loading");

  // ---- Built once, for the life of the page -------------------------------------------
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

  // The clock outlives every catalogue; `setRange` moves its window when the mode changes, so
  // the slider, the play button and the speed selector stay bound to one object throughout.
  const clock = new SimClock(Date.now(), 48);
  bindClock(clock);

  let pointer = { x: -1, y: -1, inside: false };
  container.addEventListener("pointermove", (ev) => {
    pointer = { x: ev.clientX, y: ev.clientY, inside: true };
  });
  container.addEventListener("pointerleave", () => {
    pointer.inside = false;
    current?.clearHover();
  });
  container.addEventListener("click", () => current?.click());

  let current: Mounted | null = null;
  let switching = false;
  // The scenario is remembered *per mode*, not carried across as one value. A replay run is
  // scored under `quiet` and its own observed record; the live run under quiet, forecast and the
  // storm levels. Carrying one value across would drop a reader's G5 on the way in (it does not
  // exist in replay) and then fail to restore it on the way out, leaving them on the live run's
  // default having chosen nothing.
  const lastScenario: Record<"live" | "replay", string | null> = { live: null, replay: null };
  const modeKey = (replay: boolean) => (replay ? "replay" : "live") as "live" | "replay";

  /**
   * Load `replay ? data/replay/ : data/` and put it on screen, carrying what still applies.
   *
   * The whole of the mode switch is here, and it is deliberately one function: every listener
   * it attaches goes on one `AbortController`, so unmounting cannot leave a handler behind to
   * fire against a catalogue that is no longer on screen.
   */
  async function mountCatalogue(replay: boolean, carried: Carried | null): Promise<Mounted> {
    const base = dataBaseFor(replay);
    const bundle = await loadBundle(base);
    const aborter = new AbortController();
    const { signal } = aborter;

    loading.hidden = false;
    loading.textContent = `Propagating ${bundle.n.toLocaleString()} objects…`;

    // ---- Points and worker ------------------------------------------------------------
    const categoryIndex = Int32Array.from(bundle.objects.category);
    const points = new CataloguePoints(bundle.n, categoryIndex, bundle.manifest.categories);
    globe.scene().add(points.points);

    // A fresh worker rather than a second `init` on the old one: the WebAssembly bulk
    // propagator is allocated for a fixed object count, and re-initialising it for a different
    // catalogue would leave the previous allocation resident with nothing to free it. The
    // script is already in the browser cache, so the cost is the WASM instantiation alone.
    const worker = new Worker(new URL("./propagator.worker.ts", import.meta.url), { type: "module" });
    const screening = bundle.conjunctions?.window;
    clock.setRange(
      bundle.t0Ms,
      bundle.manifest.window_hours,
      screening ? { minMs: Date.parse(screening.start), maxMs: Date.parse(screening.end) } : undefined,
      { keepFraction: carried !== null },
    );
    if (carried) {
      clock.speed = carried.speed;
      clock.playing = carried.playing;
    }

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
      {
        type: "init",
        elements: elementsCopy,
        fields: bundle.elementFields,
        perObject: bundle.manifest.files.elements.per_object,
      },
      [elementsCopy.buffer],
    );
    await ready;
    loading.hidden = true;

    checkAgainstReference(worker, bundle);

    // ---- Panel state ------------------------------------------------------------------
    const filters = buildFilterControls(
      bundle,
      (f) => {
        points.setFilter(filterMask(bundle, f));
        updateVisible();
      },
      { signal, carried: carried?.filters ?? null },
    );
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
    const visibleTimer = window.setInterval(updateVisible, 1000);
    updateVisible();

    const select = (index: number) => {
      selected = index;
      points.setHighlight(index, pairSecondary);
      showSelected(index >= 0 ? describe(bundle, points, index) : null);
    };

    const find = el<HTMLInputElement>("find");
    find.addEventListener(
      "keydown",
      (ev) => {
        if (ev.key !== "Enter") return;
        const i = findObject(bundle, find.value);
        select(i);
        find.setCustomValidity(i < 0 ? "No match" : "");
        find.reportValidity();
      },
      { signal },
    );
    el("clear").addEventListener(
      "click",
      () => {
        pairSecondary = -1;
        select(-1);
      },
      { signal },
    );

    // A selection is an object, not an index: the two catalogues number their objects
    // differently and 13,376 of them are not the same 13,376.
    if (carried?.noradId != null) {
      const i = bundle.objects.norad_id.indexOf(carried.noradId);
      if (i >= 0) select(i);
    }

    // ---- Conjunctions, storm mode and replay -------------------------------------------
    const tracks = new ConjunctionTracks(bundle.conjunctions?.tracks.samples ?? 0);
    globe.scene().add(tracks.object3d);
    const scenarios = new ScenarioState(bundle, bundle.conjunctions?.scenario ?? "quiet");
    const panel = buildConjunctionPanel(
      bundle,
      scenarios,
      (selection: ConjunctionSelection | null) => {
        if (!selection) {
          pairSecondary = -1;
          tracks.hide();
          points.setHighlight(selected, -1);
          return;
        }
        clock.playing = false;
        clock.set(Date.parse(selection.event.tca));
        pairSecondary = selection.secondaryIndex;
        select(selection.primaryIndex);
        tracks.show(bundle, selection.event);
      },
      signal,
    );
    buildStormControl(bundle, scenarios, () => panel.refresh(), signal);

    // Fetched after the first paint, never before it: the critical path is the size it was
    // before storm mode existed, and a reader who never touches the control never pays for it.
    // A carried scenario is applied when the overlays land, because until then only the one in
    // the bundle can be rendered.
    // Quiet is the default (2026-09-05): a storm scenario is chosen explicitly, never met first. A
    // bundle written under another scenario is switched to quiet once the overlays carry it. A
    // replay keeps the bundle's own, because entering replay is itself the explicit choice.
    const wantedScenario = carried?.scenario ?? (replay ? null : "quiet");
    const applyCarriedScenario = () => {
      if (wantedScenario && wantedScenario !== scenarios.current) scenarios.select(wantedScenario);
    };
    scenarios.onChange(() => void 0);
    const idle = (window as unknown as { requestIdleCallback?: (fn: () => void) => void }).requestIdleCallback;
    const fetchOverlays = () => void scenarios.load(base).then(applyCarriedScenario);
    if (idle) idle(fetchOverlays);
    else window.setTimeout(fetchOverlays, 500);
    applyCarriedScenario();

    let replayHandle: ReplayHandle | null = null;
    if (replay) {
      const timeline = await loadTimeline(base);
      if (timeline) replayHandle = buildReplay(timeline, clock, base, signal);
      else console.warn("Replay mode without a timeline; run `driftwatch replay-bundle <run>`");
    }

    return {
      bundle,
      points,
      frames,
      tracks,
      replay: replayHandle,
      tick: (nowMs: number) => {
        if (selected >= 0 && (nowMs | 0) % 8 === 0) showSelected(describe(bundle, points, selected));
        replayHandle?.tick();
      },
      hover: (px, py, rect) => {
        const i = pick(points, camera, px - rect.left, py - rect.top, rect.width, rect.height);
        hovered = i;
        showTooltip(i >= 0 ? describe(bundle, points, i) : null, px, py);
        points.setHighlight(i >= 0 ? i : selected, pairSecondary);
      },
      clearHover: () => {
        hovered = -1;
        showTooltip(null, 0, 0);
        if (selected < 0) points.setHighlight(-1, pairSecondary);
      },
      click: () => {
        if (hovered >= 0) select(hovered);
      },
      unmount: () => {
        aborter.abort();
        window.clearInterval(visibleTimer);
        replayHandle?.destroy();
        worker.terminate();
        globe.scene().remove(points.points);
        globe.scene().remove(tracks.object3d);
        points.dispose();
        tracks.dispose();
        showTooltip(null, 0, 0);
        showSelected(null);
        return {
          noradId: selected >= 0 ? bundle.objects.norad_id[selected] : null,
          scenario: scenarios.current,
          fraction: clock.fraction,
          filters: filterNames(bundle, filters),
          speed: clock.speed,
          playing: clock.playing,
        };
      },
    };
  }

  const setReplayLabel = bindReplayControl((wanted) => void switchMode(wanted));

  async function switchMode(replay: boolean): Promise<void> {
    if (switching) return;
    switching = true;
    setReplayLabel(replay, true);
    const leaving = current;
    const wasReplay = document.body.dataset.replay === "1";
    const carried = leaving?.unmount() ?? null;
    if (carried) lastScenario[modeKey(wasReplay)] = carried.scenario;
    try {
      current = await mountCatalogue(replay, carried ? { ...carried, scenario: lastScenario[modeKey(replay)] } : null);
      setReplayInUrl(replay);
    } catch (err) {
      console.error(err);
      loading.hidden = false;
      loading.textContent = failureText(replay, err);
      current = null;
    } finally {
      setReplayLabel(replay);
      switching = false;
    }
  }

  current = await mountCatalogue(replayInUrl(), null);
  setReplayLabel(replayInUrl());

  // ---- Animation loop, one for the life of the page ------------------------------------
  let last = performance.now();
  let lastT = clock.tMs;
  let lastPick = 0;
  const loop = (now: number) => {
    const dt = Math.min(now - last, 250);
    last = now;
    clock.tick(dt);
    const direction: 1 | -1 = clock.tMs >= lastT ? 1 : -1;
    lastT = clock.tMs;
    const mounted = current;
    if (mounted) {
      mounted.frames.ensure(clock.tMs, clock.speed, direction);
      if (pointer.inside && now - lastPick > 40 && mounted.points.hasFrames) {
        lastPick = now;
        mounted.hover(pointer.x, pointer.y, container.getBoundingClientRect());
      }
      mounted.tick(now);
    }
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

function failureText(replay: boolean, err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  const how = replay
    ? 'Run "uv run driftwatch propagate --snapshot <as-of file> --at 2024-05-09T00:00:00Z --export-dir web/public/data/replay", then "driftwatch report <replay run> --out-dir web/public/data/replay" and "driftwatch replay-bundle <replay run>".'
    : 'Run "uv run driftwatch propagate --at <time>" first.';
  return `Failed to load: ${message}. ${how}`;
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
    out.textContent =
      `median ${median.toFixed(1)} m, max ${max.toFixed(1)} m over ${diffs.length.toLocaleString()} objects` +
      (mismatchedErrors ? `; ${mismatchedErrors} error-status mismatches` : "");
    console.info("driftwatch: satellite.js vs Python sgp4 at t0", {
      medianM: median,
      maxM: max,
      n: diffs.length,
      mismatchedErrors,
    });
  };
  worker.addEventListener("message", onMessage);
  worker.postMessage({ type: "eci", tMs: bundle.t0Ms });
}

main().catch((err) => {
  console.error(err);
  const loading = el<HTMLDivElement>("loading");
  loading.hidden = false;
  loading.textContent = failureText(replayInUrl(), err);
});
