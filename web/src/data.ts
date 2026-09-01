/**
 * Loading the bundle written by `driftwatch propagate` (see docs/data-schema.md).
 *
 * Everything is column-oriented: `objects.json` holds parallel arrays, `elements.bin` is
 * a flat float64 table and `reference.bin` a flat float32 table. That keeps the payload
 * small and lets the propagator work on typed arrays without building 19,000 objects.
 */

export interface BinaryFileSpec {
  path: string;
  dtype: "float64le" | "float32le";
  fields: string[];
  per_object: number;
}

export interface Manifest {
  bundle_version: number;
  generator: string;
  generated_at: string;
  snapshot: string;
  reference_time: string;
  window_hours: number;
  n_objects: number;
  n_sgp4_errors: number;
  categories: string[];
  bands: string[];
  files: { objects: string; elements: BinaryFileSpec; reference: BinaryFileSpec };
  notes: string[];
}

export interface Objects {
  norad_id: number[];
  name: string[];
  category: number[];
  band: number[];
  object_type: string[];
  perigee_km: (number | null)[];
  apogee_km: (number | null)[];
  period_min: (number | null)[];
  inclination_deg: (number | null)[];
  epoch_age_days: (number | null)[];
  sgp4_error: number[];
}

export interface Bundle {
  manifest: Manifest;
  objects: Objects;
  /** Flat float64 table, `manifest.files.elements.per_object` values per object. */
  elements: Float64Array;
  elementFields: string[];
  /** Flat float32 table: TEME x, y, z (km), vx, vy, vz (km/s) at the reference time. */
  reference: Float32Array;
  /** Reference time as a Unix timestamp in milliseconds. */
  t0Ms: number;
  n: number;
}

async function fetchOk(url: string): Promise<Response> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status} ${res.statusText}`);
  return res;
}

export async function loadBundle(base = "data/"): Promise<Bundle> {
  const manifest = (await (await fetchOk(base + "manifest.json")).json()) as Manifest;
  if (manifest.bundle_version !== 1) {
    throw new Error(`Unsupported bundle version ${manifest.bundle_version}`);
  }
  const [objects, elementsBuf, referenceBuf] = await Promise.all([
    (await fetchOk(base + manifest.files.objects)).json() as Promise<Objects>,
    (await fetchOk(base + manifest.files.elements.path)).arrayBuffer(),
    (await fetchOk(base + manifest.files.reference.path)).arrayBuffer(),
  ]);
  const n = manifest.n_objects;
  const elements = new Float64Array(elementsBuf);
  const reference = new Float32Array(referenceBuf);
  const perElem = manifest.files.elements.per_object;
  if (elements.length !== n * perElem) {
    throw new Error(`elements.bin has ${elements.length} values, expected ${n * perElem}`);
  }
  if (reference.length !== n * manifest.files.reference.per_object) {
    throw new Error(`reference.bin has ${reference.length} values, expected ${n * 6}`);
  }
  if (objects.name.length !== n) {
    throw new Error(`objects.json has ${objects.name.length} rows, expected ${n}`);
  }
  return {
    manifest,
    objects,
    elements,
    elementFields: manifest.files.elements.fields,
    reference,
    t0Ms: Date.parse(manifest.reference_time),
    n,
  };
}
