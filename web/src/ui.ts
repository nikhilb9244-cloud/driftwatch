/** DOM wiring for the side panel and tooltip. No framework; the page is one screen. */

import type { Bundle } from "./data";
import { ecefToGeodetic, formatOffset, formatUtc, inertialSpeed } from "./geodesy";
import { CATEGORY_COLOURS, type CataloguePoints } from "./points";
import type { SimClock } from "./clock";

const BAND_LABELS: Record<string, string> = {
  leo: "LEO",
  meo: "MEO",
  geo: "GEO",
  heo: "HEO",
  other: "other",
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

export function buildFilterControls(bundle: Bundle, onChange: (f: Filters) => void): Filters {
  const filters: Filters = {
    categories: new Set(bundle.manifest.categories.map((_, i) => i)),
    bands: new Set(bundle.manifest.bands.map((_, i) => i)),
  };
  const catCounts = new Array(bundle.manifest.categories.length).fill(0);
  const bandCounts = new Array(bundle.manifest.bands.length).fill(0);
  for (let i = 0; i < bundle.n; i++) {
    catCounts[bundle.objects.category[i]]++;
    bandCounts[bundle.objects.band[i]]++;
  }

  const cats = el<HTMLDivElement>("categories");
  bundle.manifest.categories.forEach((name, i) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = true;
    input.addEventListener("change", () => {
      if (input.checked) filters.categories.add(i);
      else filters.categories.delete(i);
      onChange(filters);
    });
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
  bundle.manifest.bands.forEach((name, i) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = true;
    input.addEventListener("change", () => {
      if (input.checked) filters.bands.add(i);
      else filters.bands.delete(i);
      onChange(filters);
    });
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
  const t0Ms = (clock.minMs + clock.maxMs) / 2;
  const steps = Number(slider.max);
  let dragging = false;

  const render = () => {
    utc.textContent = formatUtc(clock.tMs);
    offset.textContent = formatOffset(clock.tMs, t0Ms);
    play.textContent = clock.playing ? "⏸" : "▶";
    if (!dragging) slider.value = String(Math.round(clock.fraction * steps));
  };
  clock.onChange(render);
  render();

  slider.addEventListener("pointerdown", () => (dragging = true));
  slider.addEventListener("pointerup", () => (dragging = false));
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
  el<HTMLButtonElement>("now").addEventListener("click", () => clock.set(t0Ms));
  el<HTMLButtonElement>("live").addEventListener("click", () => clock.set(Date.now()));
  window.addEventListener("keydown", (ev) => {
    if (ev.code === "Space" && !(ev.target instanceof HTMLInputElement)) {
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
    return;
  }
  section.hidden = false;
  const rows: Array<[string, string]> = [
    ["Name", d.name],
    ["NORAD", String(d.norad)],
    ["Category", `${d.category.replace("_", " ")} (${d.objectType})`],
    ["Band", d.band.toUpperCase()],
    ["Height", fmt(d.heightKm, 1, " km (WGS84)")],
    ["Lat, lon", `${fmt(d.latDeg, 3, "°")}, ${fmt(d.lonDeg, 3, "°")}`],
    ["Speed", fmt(d.speedKms, 3, " km/s (inertial)")],
    ["Period", fmt(d.periodMin, 1, " min")],
    ["Inclination", fmt(d.inclinationDeg, 2, "°")],
    ["Perigee / apogee", `${fmt(d.perigeeKm, 0)} / ${fmt(d.apogeeKm, 0)} km (mean)`],
    ["Element-set age", fmt(d.epochAgeDays, 2, " days at t₀")],
  ];
  body.innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join("");
}

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** Find the first object whose name contains the query or whose NORAD id equals it. */
export function findObject(bundle: Bundle, query: string): number {
  const q = query.trim().toUpperCase();
  if (!q) return -1;
  const asNumber = Number(q);
  if (Number.isInteger(asNumber)) {
    const i = bundle.objects.norad_id.indexOf(asNumber);
    if (i >= 0) return i;
  }
  for (let i = 0; i < bundle.n; i++) {
    if (bundle.objects.name[i].toUpperCase().includes(q)) return i;
  }
  return -1;
}
