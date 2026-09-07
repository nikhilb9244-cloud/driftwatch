import type { GlobeInstance } from "globe.gl";
import { el } from "./ui";

type View = "explore" | "approaches" | "methods";
export const catalogueHomeAltitude = () => Math.max(2.4, Math.min(6, 2.2 * innerHeight / innerWidth));
const headings: Record<View, [string, string]> = {
  explore: ["Explore", "Find an object"],
  approaches: ["Stored screening", "Close approaches"],
  methods: ["Methods & limits", "About the data"],
};

/** Navigation lives outside catalogue mounts, so replay cannot duplicate listeners. */
export function buildCatalogueShell(globe: GlobeInstance) {
  const drawer = el("catalogue-drawer");
  const scroll = drawer.querySelector<HTMLElement>(".drawer-scroll")!;
  const actions = [...document.querySelectorAll<HTMLButtonElement>("[data-view]")];
  let view: View | null = null;
  let opener: HTMLElement | null = null;
  const positions = new Map<View, number>();
  const close = (restore = true) => {
    if (view) positions.set(view, scroll.scrollTop);
    drawer.hidden = true;
    delete document.body.dataset.panel;
    actions.forEach(button => button.setAttribute("aria-expanded", "false"));
    view = null;
    // `opener` is the control the drawer was opened from, and it is only a dock button when the
    // reader pressed one: a drawer opened by selecting an object on the globe has none, and
    // sending focus to whichever dock button they last used — possibly minutes ago — puts them
    // somewhere they never were. Try it, then check the browser accepted it: a button that has
    // been removed, or hidden by the short-viewport rules while a panel is open, silently
    // refuses focus and would otherwise leave the reader on <body>.
    if (restore) {
      opener?.focus({ preventScroll: true });
      if (document.activeElement !== opener) el("globe").focus({ preventScroll: true });
      opener = null;
    }
  };
  const open = (next: View, focus = true) => {
    if (view) positions.set(view, scroll.scrollTop);
    view = next;
    drawer.hidden = false;
    document.body.dataset.panel = next;
    document.querySelectorAll<HTMLElement>("[data-pane]").forEach(pane => { pane.hidden = pane.dataset.pane !== next; });
    actions.forEach(button => button.setAttribute("aria-expanded", String(button.dataset.view === next)));
    const [kicker, title] = headings[next];
    el("drawer-kicker").textContent = kicker;
    el("drawer-title").textContent = title;
    scroll.scrollTop = positions.get(next) ?? 0;
    if (focus) (next === "explore" ? el("find") : el("drawer-title")).focus({ preventScroll: true });
  };
  actions.forEach(button => button.addEventListener("click", () => {
    opener = button;
    if (view === button.dataset.view) close();
    else open(button.dataset.view as View);
  }));
  el("drawer-close").addEventListener("click", () => close());
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && view) { event.preventDefault(); close(); }
  });

  const duration = () => matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 400;
  const zoom = (factor: number) => {
    const current = globe.pointOfView();
    globe.pointOfView({ altitude: Math.max(.12, Math.min(58, current.altitude * factor)) }, duration());
  };
  el("zoom-in").addEventListener("click", () => zoom(.8));
  el("zoom-out").addEventListener("click", () => zoom(1.25));
  el("reset-view").addEventListener("click", () => globe.pointOfView({ lat: -20, lng: 25, altitude: catalogueHomeAltitude() }, duration()));
  el("globe").addEventListener("keydown", event => {
    // Ctrl/Cmd with +/- is browser zoom and Alt/Cmd with an arrow is history: cancelling those
    // would take a shortcut away from the reader and hand them a rotated globe instead. Shift is
    // still allowed, because '+' is Shift and '='.
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const current = globe.pointOfView();
    if (event.key.startsWith("Arrow")) {
      event.preventDefault();
      globe.pointOfView({
        lat: Math.max(-85, Math.min(85, current.lat + (event.key === "ArrowUp" ? 8 : event.key === "ArrowDown" ? -8 : 0))),
        lng: current.lng + (event.key === "ArrowLeft" ? -8 : event.key === "ArrowRight" ? 8 : 0),
      }, duration());
    } else if (event.key === "+" || event.key === "=" || event.key === "-") {
      event.preventDefault(); zoom(event.key === "-" ? 1.25 : .8);
    }
  });

  const quality = el<HTMLSelectElement>("render-detail");
  const renderer = globe.renderer();
  const composer = globe.postProcessingComposer();
  const reportResolution = () => {
    el("render-resolution").textContent = `${renderer.domElement.width.toLocaleString()} × ${renderer.domElement.height.toLocaleString()} rendered pixels. Earth imagery: 4,096 × 2,048. Sharper rendering does not add orbital accuracy.`;
  };
  // The altitude that frames Earth depends on the aspect, and `resize` is the only place that
  // learns the aspect has changed. globe.gl frames the sphere with a fixed 50 degree *vertical*
  // field of view, so on a portrait screen it is the horizontal half-angle, atan(aspect x tan 25
  // degrees), that clips, and an altitude fitted in landscape crops both limbs when the phone is
  // turned: at 844 x 390 the home altitude is the 2.4 floor, and carrying that into 390 x 844
  // draws a 557 px disc across a 390 px viewport. Re-fit by the ratio of the new home altitude to
  // the old, so a reader who had deliberately zoomed in keeps their zoom in proportion instead of
  // being thrown back to the whole Earth.
  let home = catalogueHomeAltitude();
  const refit = () => {
    const next = catalogueHomeAltitude();
    if (Math.abs(next - home) < 1e-6) return;
    const altitude = globe.pointOfView().altitude * (next / home);
    home = next;
    globe.pointOfView({ altitude: Math.max(.12, Math.min(58, altitude)) }, 0);
  };
  const resize = () => {
    const requested = quality.value === "high" ? 2.5 : quality.value === "low" ? 1 : Math.min(window.devicePixelRatio || 1, 2);
    const ratio = Math.min(requested, Math.sqrt(8_000_000 / (innerWidth * innerHeight)));
    renderer.setPixelRatio(ratio);
    composer.setPixelRatio(ratio);
    globe.width(innerWidth).height(innerHeight);
    refit();
    reportResolution();
  };
  new MutationObserver(reportResolution).observe(renderer.domElement, { attributes: true, attributeFilter: ["width", "height"] });
  quality.addEventListener("change", resize);
  window.addEventListener("resize", resize);
  resize();
  new ResizeObserver(() => {
    document.body.style.setProperty("--replay-height", `${el("replay").getBoundingClientRect().height}px`);
  }).observe(el("replay"));
  return {
    revealSelection() {
      // Already showing the selection: leave the drawer alone. Returning early rather than
      // re-opening the same view also keeps `opener`, so a reader who opened this panel with the
      // dock button still gets it back on Escape.
      //
      // "approaches" is deliberately not in that test. An encounter row selects its own primary and
      // must not throw the reader out of the list it was chosen from, but that is now said at the
      // call site, which passes `reveal = false`. A click on Earth while the list is open is a new
      // selection, and its card, its "Centre on object" button and its `role="status"` message all
      // live in the explore pane — leaving that pane hidden showed the reader nothing and announced
      // nothing, while the globe changed under them.
      if (view === "explore") return;
      // Opened by the selection itself, not by a control the reader pressed, so there is nothing
      // to restore focus to when it closes; `close` falls through to the globe.
      opener = null;
      open("explore", false);
    },
  };
}
