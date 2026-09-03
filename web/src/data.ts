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
  /** Object count per element-set source (`celestrak`, `spacetrack`). Absent in bundles older than Phase 2. */
  sources?: Record<string, number>;
  /** Credit lines the data providers require; shown in the panel. */
  attribution?: string[];
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

/** One close approach, as Python computed it. Probabilities and covariances are never recomputed here. */
export interface ConjunctionEvent {
  event_id: string;
  primary_norad_id: number;
  secondary_norad_id: number;
  tca: string;
  miss_km: number;
  rel_speed_kms: number;
  miss_r_km: number;
  miss_i_km: number;
  miss_c_km: number;
  in_box: boolean;
  hbr_m: number;
  sigma_i_primary_km: number | null;
  sigma_i_secondary_km: number | null;
  cov_source_secondary: string | null;
  /** The combined covariance projected onto the encounter plane, x along the miss vector. */
  enc_cov_xx_km2: number | null;
  enc_cov_xy_km2: number | null;
  enc_cov_yy_km2: number | null;
  pc: number | null;
  /** Phase 3: the objects moved, scored against the covariance the run would have had. */
  pc_shift_only?: number | null;
  /** Phase 3: the covariance widened, the objects left where their element sets put them. */
  pc_variance_only?: number | null;
  /**
   * The miss under the scenario in force, after the storm term moved both objects. Under
   * `quiet` it equals `miss_km`; under a storm scenario the two answer different questions
   * and this is the one the probability was computed from.
   */
  miss_shifted_km?: number | null;
  /** The displacement that actually entered the miss: a vector norm, not a difference of the two. */
  relative_shift_km?: number | null;
  storm_source_primary?: string;
  storm_source_secondary?: string;
  /**
   * How far Step 4's May 2024 validation reaches this event: `validated` when both objects have
   * a ballistic coefficient measured from their own decay, `indicative` otherwise, `none` under
   * a scenario with no storm layer. Not a confidence and not a weighting.
   */
  storm_validity?: string;
  /** False when the storm term left the linear theory it was derived under; then every pc is null. */
  scoreable?: boolean;
  unscoreable_reason?: string;
  pc_max: number | null;
  pc_max_scale: number | null;
  region: string;
  flag: string;
  confidence: string;
  /** Index into the track table, or null when this event has no stored track. */
  track: number | null;
}

/** Repeated encounters of one pair, collapsed. `events` indexes into `Conjunctions.events`. */
export interface ConjunctionPair {
  primary_norad_id: number;
  primary_name: string;
  secondary_norad_id: number;
  secondary_name: string;
  secondary_category: string;
  n_events: number;
  n_in_box: number;
  first_tca: string;
  closest_km: number;
  max_pc: number | null;
  // The miss of the event that produced max_pc, which is not always the closest pass.
  miss_at_max_pc_km?: number | null;
  pc_cumulative: number | null;
  max_pc_max: number | null;
  region: string;
  flag: string;
  confidence: string;
  /** The validity of the event this pair is judged on. See `ConjunctionEvent.storm_validity`. */
  storm_validity?: string;
  /** Events of this pair that carry a probability under the scenario in force. */
  n_scoreable?: number;
  manoeuvre_secondary: string;
  secondary_ephemeris: string;
  cov_source_secondary: string | null;
  hbr_m: number;
  events: number[];
}

export interface TracksSpec {
  path: string;
  dtype: "float32le";
  frame: "teme";
  units: "km";
  n_events: number;
  objects_per_event: number;
  samples: number;
  step_s: number;
  half_window_s: number;
  order: string;
}

export interface Conjunctions {
  bundle_version: number;
  run_id: string;
  snapshot: string;
  fleet: string;
  model_version: string | null;
  scenario: string;
  scenarios: string[];
  window: { start: string; end: string };
  thresholds: { red: number; yellow: number };
  n_events: number;
  n_events_total: number;
  n_pairs: number;
  n_pairs_detailed: number;
  pairs: ConjunctionPair[];
  events: ConjunctionEvent[];
  tracks: TracksSpec;
  /** Storm mode's entry point: where the overlays are, and the figures for the scenario in force. */
  storm?: {
    overlays: string;
    baseline: string;
    scored: string[];
    summary: Record<string, import("./scenarios").ScenarioFigures>;
    unscoreable: import("./scenarios").UnscoreableRow[];
  };
  caveats: string[];
  supplemental?: Array<{ name: string; version: string; n_applied: number }> | null;
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
  /** The screening run's conjunctions, when `driftwatch report` has written them. */
  conjunctions?: Conjunctions;
  /** Flat float32 TEME positions (km): event, object, sample, xyz. */
  tracks?: Float32Array;
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
  const bundle: Bundle = {
    manifest,
    objects,
    elements,
    elementFields: manifest.files.elements.fields,
    reference,
    t0Ms: Date.parse(manifest.reference_time),
    n,
  };
  Object.assign(bundle, await loadConjunctions(base));
  return bundle;
}

/**
 * The conjunctions bundle, if a screening run has been exported beside the catalogue.
 *
 * Optional on purpose: the globe works without it, and a bundle written before Step 4
 * has no such file. A failure here is logged and dropped rather than fatal.
 */
async function loadConjunctions(base: string): Promise<Partial<Bundle>> {
  let conjunctions: Conjunctions;
  try {
    const res = await fetch(base + "conjunctions.json");
    if (!res.ok) return {};
    conjunctions = (await res.json()) as Conjunctions;
  } catch (err) {
    console.warn("No conjunctions bundle:", err);
    return {};
  }
  if (conjunctions.bundle_version !== 1) {
    console.warn(`Ignoring conjunctions bundle version ${conjunctions.bundle_version}`);
    return {};
  }
  let tracks: Float32Array | undefined;
  const spec = conjunctions.tracks;
  if (spec && spec.n_events > 0) {
    try {
      const buf = await (await fetchOk(base + spec.path)).arrayBuffer();
      tracks = new Float32Array(buf);
      const expected = spec.n_events * spec.objects_per_event * spec.samples * 3;
      if (tracks.length !== expected) {
        console.warn(`${spec.path} has ${tracks.length} values, expected ${expected}; tracks disabled`);
        tracks = undefined;
      }
    } catch (err) {
      console.warn("No conjunction tracks:", err);
    }
  }
  return { conjunctions, tracks };
}
