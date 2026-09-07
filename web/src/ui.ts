/** DOM wiring for the side panel and tooltip. No framework; the page is one screen. */

import type { Bundle } from "./data";
import { ecefToGeodetic, formatOffset, formatUtc, inertialSpeed } from "./geodesy";
import { CATEGORY_COLOURS, type CataloguePoints } from "./points";
import type { SimClock } from "./clock";

const BAND_LABELS: Record<string, string> = {
  leo: "Low Earth (LEO)",
  meo: "Medium Earth (MEO)",
  geo: "Geostationary band (GEO)",
  heo: "Highly elliptical (HEO)",
  other: "Other orbits",
};

const BAND_TITLES: Record<string, string> = {
  leo: "Apogee below 2000 km",
  meo: "Between LEO and GEO",
  geo: "Within 200 km of 35,786 km",
  heo: "Eccentricity above 0.25",
  other: "Graveyard, transfer and cislunar orbits",
};

export function el<T extends HTMLElement>(id: string): T {
  const e = document.getElementById(id);
  if (!e) throw new Error(`Missing element #${id}`);
  return e as T;
}

export interface Filters {
  categories: Set<number>;
  bands: Set<number>;
}

/**
 * What a filter selection means independently of a catalogue: names, not indices.
 *
 * The replay catalogue and the live one share a legend today, but nothing guarantees they always
 * will, and an index carried across a mode switch would silently filter the wrong class. Names
 * carry; an index does not.
 */
export interface FilterNames {
  categories: Set<string>;
  bands: Set<string>;
}

export function filterNames(bundle: Bundle, filters: Filters): FilterNames {
  return {
    categories: new Set([...filters.categories].map((i) => bundle.manifest.categories[i])),
    bands: new Set([...filters.bands].map((i) => bundle.manifest.bands[i])),
  };
}

/**
 * Build the category and altitude-band checkboxes for `bundle`.
 *
 * `signal` aborts every listener when the catalogue is unmounted, and `carried` restores a
 * selection made against the previous one. Both containers are emptied first, so this is safe to
 * call again on the same DOM.
 */
export function buildFilterControls(
  bundle: Bundle,
  onChange: (f: Filters) => void,
  opts: { signal?: AbortSignal; carried?: FilterNames | null } = {},
): Filters {
  const { signal, carried } = opts;
  const wanted = (kind: "categories" | "bands", name: string) => !carried || carried[kind].has(name);
  const filters: Filters = {
    categories: new Set(
      bundle.manifest.categories.map((name, i) => (wanted("categories", name) ? i : -1)).filter((i) => i >= 0),
    ),
    bands: new Set(bundle.manifest.bands.map((name, i) => (wanted("bands", name) ? i : -1)).filter((i) => i >= 0)),
  };
  const catCounts = new Array(bundle.manifest.categories.length).fill(0);
  const bandCounts = new Array(bundle.manifest.bands.length).fill(0);
  for (let i = 0; i < bundle.n; i++) {
    catCounts[bundle.objects.category[i]]++;
    bandCounts[bundle.objects.band[i]]++;
  }

  const cats = el<HTMLDivElement>("categories");
  cats.replaceChildren();
  bundle.manifest.categories.forEach((name, i) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = filters.categories.has(i);
    input.addEventListener(
      "change",
      () => {
        if (input.checked) filters.categories.add(i);
        else filters.categories.delete(i);
        onChange(filters);
      },
      { signal },
    );
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.style.background = CATEGORY_COLOURS[name] ?? CATEGORY_COLOURS.unknown;
    const text = document.createElement("span");
    text.className = "name";
    text.textContent = name.replace("_", " ");
    const count = document.createElement("span");
    count.className = "count";
    count.textContent = catCounts[i].toLocaleString();
    label.append(input, chip, text, count);
    cats.append(label);
  });

  const bands = el<HTMLDivElement>("bands");
  bands.replaceChildren();
  bundle.manifest.bands.forEach((name, i) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = filters.bands.has(i);
    input.addEventListener(
      "change",
      () => {
        if (input.checked) filters.bands.add(i);
        else filters.bands.delete(i);
        onChange(filters);
      },
      { signal },
    );
    const text = document.createElement("span");
    text.className = "name";
    text.textContent = BAND_LABELS[name] ?? name;
    label.title = BAND_TITLES[name] ?? "";
    const count = document.createElement("span");
    count.className = "count";
    count.textContent = bandCounts[i].toLocaleString();
    label.append(input, text, count);
    bands.append(label);
  });
  return filters;
}

export function filterMask(bundle: Bundle, filters: Filters): Uint8Array {
  const mask = new Uint8Array(bundle.n);
  for (let i = 0; i < bundle.n; i++) {
    mask[i] = filters.categories.has(bundle.objects.category[i]) && filters.bands.has(bundle.objects.band[i]) ? 1 : 0;
  }
  return mask;
}

export function bindClock(clock: SimClock): void {
  const slider = el<HTMLInputElement>("slider");
  const play = el<HTMLButtonElement>("play");
  const speed = el<HTMLSelectElement>("speed");
  const utc = el<HTMLSpanElement>("clock-utc");
  const offset = el<HTMLSpanElement>("clock-offset");
  const steps = Number(slider.max);
  let dragging = false;

  // Bound once for the life of the page, and `clock.t0Ms` is read at render time rather than
  // captured, so entering replay moves the window under the same controls instead of leaving
  // the offset measured against a reference time two years away.
  const render = () => {
    utc.textContent = formatUtc(clock.tMs);
    offset.textContent = formatOffset(clock.tMs, clock.t0Ms).replace("t₀", "Reference");
    play.textContent = clock.playing ? "⏸" : "▶";
    play.setAttribute("aria-label", clock.playing ? "Pause playback" : "Play time");
    speed.value = String(clock.speed);
    slider.setAttribute("aria-valuetext", formatUtc(clock.tMs));
    const live = el<HTMLButtonElement>("live");
    const currentMs = Date.now();
    live.disabled = currentMs < clock.minMs || currentMs > clock.maxMs;
    live.title = live.disabled ? "Current UTC is outside this snapshot's available time window. Use Reference time instead." : "Jump to current UTC using this snapshot's elements";
    el("window-start").textContent = formatUtc(clock.minMs).slice(5, 16);
    el("window-end").textContent = formatUtc(clock.maxMs).slice(5, 16);
    if (!dragging) slider.value = String(Math.round(clock.fraction * steps));
  };
  clock.onChange(render);
  render();

  slider.addEventListener("pointerdown", () => (dragging = true));
  slider.addEventListener("pointerup", () => (dragging = false));
  slider.addEventListener("pointercancel", () => (dragging = false));
  slider.addEventListener("input", () => {
    const f = Number(slider.value) / steps;
    clock.set(clock.minMs + f * (clock.maxMs - clock.minMs));
  });
  play.addEventListener("click", () => {
    clock.playing = !clock.playing;
    render();
  });
  speed.value = String(clock.speed);
  speed.addEventListener("change", () => (clock.speed = Number(speed.value)));
  el<HTMLButtonElement>("now").addEventListener("click", () => clock.set(clock.t0Ms));
  el<HTMLButtonElement>("live").addEventListener("click", () => clock.set(Date.now()));
  window.addEventListener("keydown", (ev) => {
    if (ev.code === "Space" && (ev.target === document.body || ev.target === el("globe"))) {
      ev.preventDefault();
      clock.playing = !clock.playing;
      render();
    }
  });
}

function fmt(v: number | null | undefined, digits = 1, unit = ""): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return v.toFixed(digits) + unit;
}

export interface ObjectDetails {
  name: string;
  norad: number;
  category: string;
  band: string;
  objectType: string;
  latDeg: number;
  lonDeg: number;
  heightKm: number;
  speedKms: number;
  periodMin: number | null;
  inclinationDeg: number | null;
  perigeeKm: number | null;
  apogeeKm: number | null;
  epochAgeDays: number | null;
}

export function describe(bundle: Bundle, points: CataloguePoints, i: number): ObjectDetails {
  const p = points.positionOf(i);
  const v = points.velocityOf(i);
  const geo = ecefToGeodetic(p[0], p[1], p[2]);
  const o = bundle.objects;
  return {
    name: o.name[i],
    norad: o.norad_id[i],
    category: bundle.manifest.categories[o.category[i]],
    band: bundle.manifest.bands[o.band[i]],
    objectType: o.object_type[i],
    latDeg: geo.latDeg,
    lonDeg: geo.lonDeg,
    heightKm: geo.heightKm,
    speedKms: inertialSpeed(p[0], p[1], p[2], v[0], v[1], v[2]),
    periodMin: o.period_min[i],
    inclinationDeg: o.inclination_deg[i],
    perigeeKm: o.perigee_km[i],
    apogeeKm: o.apogee_km[i],
    epochAgeDays: o.epoch_age_days[i],
  };
}

export function showTooltip(d: ObjectDetails | null, x: number, y: number): void {
  const tip = el<HTMLDivElement>("tooltip");
  if (!d) {
    tip.hidden = true;
    return;
  }
  tip.hidden = false;
  tip.innerHTML =
    `<b>${escapeHtml(d.name)}</b>` +
    `<span class="muted">${d.norad} · ${d.category.replace("_", " ")} · ${d.band.toUpperCase()}</span><br>` +
    `alt ${fmt(d.heightKm, 0, " km")} · ${fmt(d.latDeg, 2, "°")}, ${fmt(d.lonDeg, 2, "°")} · ${fmt(d.speedKms, 2, " km/s")}`;
  const w = tip.offsetWidth;
  const h = tip.offsetHeight;
  const left = x + 14 + w > window.innerWidth ? x - w - 14 : x + 14;
  const top = y + 14 + h > window.innerHeight ? y - h - 14 : y + 14;
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

export function showSelected(d: ObjectDetails | null): void {
  const section = el<HTMLElement>("selected");
  const body = el<HTMLDListElement>("selected-body");
  if (!d) {
    section.hidden = true;
    body.innerHTML = "";
    el("selected-orbit").innerHTML = "";
    return;
  }
  section.hidden = false;
  el("selected-name").textContent = d.name;
  const rows: Array<[string, string]> = [
    ["Catalogue number", `NORAD ${d.norad}`],
    ["Object type", `${d.category.replace("_", " ")} (${d.objectType})`],
    ["Orbit group", BAND_LABELS[d.band] ?? d.band],
    ["Height above Earth", fmt(d.heightKm, 1, " km")],
    ["Latitude / longitude", `${fmt(d.latDeg, 3, "°")}, ${fmt(d.lonDeg, 3, "°")}`],
    ["Orbital speed", fmt(d.speedKms, 3, " km/s")],
  ];
  const orbitRows: Array<[string, string]> = [
    ["Time for one orbit", fmt(d.periodMin, 1, " min")],
    ["Tilt to the equator", fmt(d.inclinationDeg, 2, "°")],
    ["Lowest / highest altitude", `${fmt(d.perigeeKm, 0)} / ${fmt(d.apogeeKm, 0)} km`],
    ["Element age at reference", fmt(d.epochAgeDays, 2, " days")],
  ];
  body.innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join("");
  el("selected-orbit").innerHTML = orbitRows.map(([k, v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join("");
}

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** Catalogue punctuation varies; exact identifiers and names rank ahead of partial names. */
export function findObjects(bundle: Bundle, query: string): number[] {
  const normalise = (value: string) => value.toUpperCase().replace(/[^A-Z0-9]/g, "");
  const q = normalise(query.trim());
  if (!q) return [];
  const id = Number(q.replace(/^NORAD/, ""));
  const index = Number.isInteger(id) ? bundle.objects.norad_id.indexOf(id) : -1;
  if (index >= 0) return [index];
  const exact: number[] = [], prefix: number[] = [], partial: number[] = [];
  bundle.objects.name.forEach((value, i) => {
    const name = normalise(value);
    if (name === q) exact.push(i);
    else if (name.startsWith(q)) prefix.push(i);
    else if (name.includes(q)) partial.push(i);
  });
  return [...exact, ...prefix, ...partial];
}

export function findObject(bundle: Bundle, query: string): number {
  return findObjects(bundle, query)[0] ?? -1;
}
