/**
 * SGP4 in a Web Worker.
 *
 * Initialised with the flat element table from `elements.bin`, this worker answers
 * "where is everything at time t" with Earth-fixed position and velocity arrays. It uses
 * satellite.js, a port of the same Vallado reference code as the Python sgp4 library,
 * through its WebAssembly bulk propagator when that loads and a per-object JavaScript
 * loop otherwise. Both paths give identical numbers; only speed differs.
 *
 * Earth-fixed here means the GMST rotation with UTC standing in for UT1 and no polar
 * motion, which is what satellite.js provides. The cost of that shortcut is measured in
 * the Python tests (docs/frames-and-time.md) and is far below a pixel.
 */

import {
  BulkPropagator,
  EciBaseCalculator,
  createSingleThreadRuntime,
  gstime,
  json2satrec,
  sgp4,
} from "satellite.js";

type SatRec = ReturnType<typeof json2satrec>;

const EARTH_ROTATION_RATE = 7.292115e-5; // rad/s

interface InitMessage {
  type: "init";
  elements: Float64Array;
  fields: string[];
  perObject: number;
}

interface FrameMessage {
  type: "frame";
  tMs: number;
}

interface EciMessage {
  type: "eci";
  tMs: number;
}

type InMessage = InitMessage | FrameMessage | EciMessage;

const ctx = self as unknown as {
  postMessage(msg: unknown, transfer?: Transferable[]): void;
  onmessage: ((ev: MessageEvent<InMessage>) => void) | null;
};

let n = 0;
let satrecs: SatRec[] = [];
let epochMs: Float64Array = new Float64Array(0);
let bulk: { propagator: any; eci: EciBaseCalculator } | null = null;
let engine = "satellite.js (JS)";

// Scratch buffers reused between frames.
let eciPos = new Float64Array(0);
let eciVel = new Float64Array(0);
let eciErr = new Int8Array(0);

function buildSatrecs(msg: InitMessage): void {
  const f = (name: string) => {
    const i = msg.fields.indexOf(name);
    if (i < 0) throw new Error(`elements.bin lacks field ${name}`);
    return i;
  };
  const iId = f("norad_id");
  const iEpoch = f("epoch_unix_ms");
  const iN = f("mean_motion");
  const iE = f("eccentricity");
  const iInc = f("inclination_deg");
  const iRaan = f("raan_deg");
  const iArgp = f("arg_perigee_deg");
  const iM = f("mean_anomaly_deg");
  const iB = f("bstar");
  const iNd = f("mean_motion_dot");
  const iNdd = f("mean_motion_ddot");
  const per = msg.perObject;
  n = msg.elements.length / per;
  satrecs = new Array(n);
  epochMs = new Float64Array(n);
  for (let k = 0; k < n; k++) {
    const row = msg.elements.subarray(k * per, (k + 1) * per);
    epochMs[k] = row[iEpoch];
    // json2satrec parses EPOCH with the JavaScript Date, so the epoch is rounded to a
    // millisecond here; that is at most 0.5 ms times orbital speed, under 4 m in LEO.
    const omm = {
      OBJECT_NAME: "",
      OBJECT_ID: "",
      EPOCH: new Date(row[iEpoch]).toISOString(),
      MEAN_MOTION: row[iN],
      ECCENTRICITY: row[iE],
      INCLINATION: row[iInc],
      RA_OF_ASC_NODE: row[iRaan],
      ARG_OF_PERICENTER: row[iArgp],
      MEAN_ANOMALY: row[iM],
      EPHEMERIS_TYPE: 0,
      CLASSIFICATION_TYPE: "U",
      NORAD_CAT_ID: row[iId],
      ELEMENT_SET_NO: 999,
      REV_AT_EPOCH: 0,
      BSTAR: row[iB],
      MEAN_MOTION_DOT: row[iNd],
      MEAN_MOTION_DDOT: row[iNdd],
    };
    satrecs[k] = json2satrec(omm as any);
  }
  eciPos = new Float64Array(n * 3);
  eciVel = new Float64Array(n * 3);
  eciErr = new Int8Array(n);
}

async function tryWasm(): Promise<void> {
  try {
    const runtime = await createSingleThreadRuntime();
    const eci = new EciBaseCalculator();
    const propagator = new BulkPropagator({
      runtime,
      calculators: [eci],
      satRecsCount: n,
      datesCount: 1,
    } as any);
    propagator.setSatRecs(satrecs);
    bulk = { propagator, eci };
    engine = "satellite.js (WebAssembly bulk)";
  } catch (err) {
    console.warn("driftwatch worker: WebAssembly propagator unavailable, using JS loop", err);
    bulk = null;
  }
}

/** Fill eciPos/eciVel/eciErr (TEME, km and km/s) for all objects at `tMs`. */
function computeEci(tMs: number): void {
  const date = new Date(tMs);
  if (bulk) {
    bulk.propagator.setDates([date]);
    bulk.propagator.run();
    const raw = bulk.propagator.getRawOutput() as { eci: { position: Float64Array; velocity: Float64Array; error: Int8Array } };
    eciPos.set(raw.eci.position.subarray(0, n * 3));
    eciVel.set(raw.eci.velocity.subarray(0, n * 3));
    eciErr.set(raw.eci.error.subarray(0, n));
    return;
  }
  for (let k = 0; k < n; k++) {
    const minutes = (tMs - epochMs[k]) / 60000;
    const res = sgp4(satrecs[k], minutes) as { position: { x: number; y: number; z: number }; velocity: { x: number; y: number; z: number } } | null;
    const err = (satrecs[k] as any).error as number;
    eciErr[k] = err;
    if (!res || err !== 0) {
      eciPos[k * 3] = eciPos[k * 3 + 1] = eciPos[k * 3 + 2] = NaN;
      eciVel[k * 3] = eciVel[k * 3 + 1] = eciVel[k * 3 + 2] = NaN;
      continue;
    }
    eciPos[k * 3] = res.position.x;
    eciPos[k * 3 + 1] = res.position.y;
    eciPos[k * 3 + 2] = res.position.z;
    eciVel[k * 3] = res.velocity.x;
    eciVel[k * 3 + 1] = res.velocity.y;
    eciVel[k * 3 + 2] = res.velocity.z;
  }
}

/** Rotate TEME into the Earth-fixed frame by GMST; velocity gets the -omega x r term. */
function toEarthFixed(tMs: number, pos: Float32Array, vel: Float32Array): void {
  const theta = gstime(new Date(tMs));
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  for (let k = 0; k < n; k++) {
    const i = k * 3;
    const x = eciPos[i];
    const y = eciPos[i + 1];
    const z = eciPos[i + 2];
    const xe = c * x + s * y;
    const ye = -s * x + c * y;
    pos[i] = xe;
    pos[i + 1] = ye;
    pos[i + 2] = z;
    const vx = eciVel[i];
    const vy = eciVel[i + 1];
    const vxe = c * vx + s * vy;
    const vye = -s * vx + c * vy;
    // v_fixed = R v_inertial - omega x r_fixed, with omega along +z.
    vel[i] = vxe + EARTH_ROTATION_RATE * ye;
    vel[i + 1] = vye - EARTH_ROTATION_RATE * xe;
    vel[i + 2] = eciVel[i + 2];
  }
}

ctx.onmessage = async (ev: MessageEvent<InMessage>) => {
  const msg = ev.data;
  if (msg.type === "init") {
    buildSatrecs(msg);
    await tryWasm();
    ctx.postMessage({ type: "ready", engine, n });
    return;
  }
  if (msg.type === "frame") {
    const t0 = performance.now();
    computeEci(msg.tMs);
    const pos = new Float32Array(n * 3);
    const vel = new Float32Array(n * 3);
    toEarthFixed(msg.tMs, pos, vel);
    const err = new Int8Array(eciErr);
    const computeMs = performance.now() - t0;
    ctx.postMessage({ type: "frame", tMs: msg.tMs, pos, vel, err, computeMs }, [pos.buffer, vel.buffer, err.buffer]);
    return;
  }
  if (msg.type === "eci") {
    computeEci(msg.tMs);
    const pos = new Float64Array(eciPos);
    const vel = new Float64Array(eciVel);
    const err = new Int8Array(eciErr);
    ctx.postMessage({ type: "eci", tMs: msg.tMs, pos, vel, err }, [pos.buffer, vel.buffer, err.buffer]);
  }
};
