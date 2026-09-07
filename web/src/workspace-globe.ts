import { createEarth } from './earth';
import type { GlobeInstance } from 'globe.gl';

export interface Trace { label: string; colour: string; points: number[][] }
let globe: GlobeInstance | null = null;
const canvas = document.createElement('div');
canvas.className = 'earth-canvas';
let observer: ResizeObserver | null = null;
let resolutionObserver: MutationObserver | null = null;
let quality = 'auto';
try { quality = localStorage.getItem('driftwatch-render-quality') || 'auto'; } catch { /* Device preferences are optional. */ }
const safe = (s: string) => s.replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]!));
export const scene = (caption = 'Drag to rotate · scroll to zoom · use the controls with a keyboard') => `<section class="earth-card card"><div class="earth-heading"><span class="eyebrow">EARTH / ORBIT VIEW</span><div class="earth-controls"><button id="earth-left" aria-label="Rotate Earth west">←</button><button id="earth-right" aria-label="Rotate Earth east">→</button><button id="earth-reset" aria-label="Centre Earth on Southern Africa">Centre</button><select id="earth-quality" aria-label="Earth rendering quality"><option value="auto">Auto detail</option><option value="high">High detail</option><option value="eco">Low power</option></select><a href="./catalogue.html" aria-label="Open the full moving satellite catalogue">Catalogue ↗</a></div></div><div id="scene-mount" aria-label="Interactive Earth with orbit tracks"></div><div class="earth-caption" id="earth-caption">${safe(caption)}</div><div class="earth-key" id="earth-key"></div><p class="scene-resolution" id="scene-resolution"></p><p class="earth-fallback" id="earth-fallback" hidden>The interactive Earth is unavailable on this device. The measurements and tables remain usable.</p></section>`;
export function mountScene(traces: Trace[] = [], station?: {lat: number; lon: number}): void {
  const mount = document.getElementById('scene-mount');
  if (!mount) return;
  mount.append(canvas);
  try {
    if (!globe) {
      globe = createEarth(canvas);
      globe.pointOfView({lat: -27, lng: 25, altitude: 1.9}, 0);
      globe.controls().enablePan = false;
      globe.controls().minDistance = 130;
      globe.controls().maxDistance = 650;
      globe.pathTransitionDuration(0).pathPoints('points')
        .pathPointLat((p: unknown) => (p as number[])[0])
        .pathPointLng((p: unknown) => (p as number[])[1])
        .pathPointAlt((p: unknown) => (p as number[])[2] / 6371)
        .pathColor('colour').pathStroke(1.8).pathResolution(.5);
      globe.labelLat('lat').labelLng('lon').labelText('name').labelColor(() => '#c4f563')
        .labelSize(1.2).labelDotRadius(.45).labelAltitude(.01);
    }
    const updateResolution = () => {
      if (!mount.isConnected) return;
      const output = document.getElementById('scene-resolution');
      if (output) output.textContent = `${globe!.renderer().domElement.width.toLocaleString('en-GB')} × ${globe!.renderer().domElement.height.toLocaleString('en-GB')} rendered pixels · true-scale tracks`;
    };
    // Globe applies dimensions asynchronously; report the resulting canvas, not its previous size.
    resolutionObserver?.disconnect();
    resolutionObserver = new MutationObserver(updateResolution);
    resolutionObserver.observe(globe.renderer().domElement, {attributes: true, attributeFilter: ['width', 'height']});
    const resize = () => {
      const w = mount.clientWidth, h = mount.clientHeight;
      if (!w || !h) return;
      const requested = quality === 'eco' ? 1 : quality === 'high' ? 2.5 : Math.min(devicePixelRatio || 1, 2);
      // Bound GPU memory; a sharp canvas does not add detail to the source texture.
      const ratio = Math.min(requested, Math.sqrt(8_000_000 / (w * h)));
      globe!.renderer().setPixelRatio(ratio);
      globe!.postProcessingComposer().setPixelRatio(ratio);
      globe!.width(w).height(h);
      updateResolution();
    };
    observer?.disconnect();
    observer = new ResizeObserver(resize); observer.observe(mount); resize();
    globe.pathsData(traces).labelsData(station ? [{...station, name: 'Selected ground station'}] : []);
    const duration = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 600;
    const reset = () => globe!.pointOfView({lat: station?.lat ?? -27, lng: station?.lon ?? 25, altitude: 1.9}, duration);
    document.getElementById('earth-reset')!.onclick = reset;
    for (const [id, delta] of [['earth-left', -25], ['earth-right', 25]] as const) {
      document.getElementById(id)!.onclick = () => { const p = globe!.pointOfView(); globe!.pointOfView({...p, lng: p.lng + delta}, duration); };
    }
    const select = document.getElementById('earth-quality') as HTMLSelectElement;
    select.value = quality;
    select.onchange = () => { quality = select.value; try { localStorage.setItem('driftwatch-render-quality', quality); } catch { /* No persistence required. */ } resize(); };
    const key = document.getElementById('earth-key')!;
    key.replaceChildren();
    const visible = new Set(traces);
    for (const t of traces) {
      const button = document.createElement('button'), dot = document.createElement('i');
      dot.style.background = t.colour;
      button.append(dot, document.createTextNode(t.label));
      button.setAttribute('aria-pressed', 'true');
      button.title = `Show or hide ${t.label}`;
      button.onclick = () => { if (visible.has(t)) visible.delete(t); else visible.add(t); button.setAttribute('aria-pressed', String(visible.has(t))); globe!.pathsData(traces.filter(x => visible.has(x))); };
      key.append(button);
    }
    if (!traces.length) { const label = document.createElement('span'); label.textContent = 'Context only · no measured track loaded'; key.append(label); }
    if (station) reset();
  } catch { document.getElementById('earth-fallback')!.hidden = false; }
}
