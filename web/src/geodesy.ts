/** Small geodesy helpers for the hover panel. WGS84 throughout. */

export const WGS84_A_KM = 6378.137;
export const WGS84_F = 1 / 298.257223563;
export const WGS84_E2 = WGS84_F * (2 - WGS84_F);
/** Earth rotation rate, rad/s (IERS 2010). Used to recover inertial speed from Earth-fixed velocity. */
export const EARTH_ROTATION_RATE = 7.292115e-5;
/** Mean Earth radius used by globe.gl's unit sphere. Drawn height uses this; the panel shows WGS84 height. */
export const GLOBE_MEAN_RADIUS_KM = 6371.0;
export const GLOBE_SCENE_RADIUS = 100.0;

export interface Geodetic {
  latDeg: number;
  lonDeg: number;
  heightKm: number;
}

/**
 * Earth-fixed Cartesian (km) to WGS84 geodetic coordinates.
 * Iterative method (Bowring's start, then Newton on latitude); converges to
 * sub-millimetre in a few steps for anything from the surface to cislunar range.
 */
export function ecefToGeodetic(x: number, y: number, z: number): Geodetic {
  const p = Math.hypot(x, y);
  const lon = Math.atan2(y, x);
  // Bowring's initial guess for latitude.
  const b = WGS84_A_KM * (1 - WGS84_F);
  const ep2 = (WGS84_A_KM * WGS84_A_KM - b * b) / (b * b);
  const theta = Math.atan2(z * WGS84_A_KM, p * b);
  let lat = Math.atan2(
    z + ep2 * b * Math.sin(theta) ** 3,
    p - WGS84_E2 * WGS84_A_KM * Math.cos(theta) ** 3,
  );
  let n = WGS84_A_KM;
  let h = 0;
  for (let i = 0; i < 5; i++) {
    const s = Math.sin(lat);
    n = WGS84_A_KM / Math.sqrt(1 - WGS84_E2 * s * s);
    if (p > 1e-9) {
      h = p / Math.cos(lat) - n;
      lat = Math.atan2(z, p * (1 - (WGS84_E2 * n) / (n + h)));
    } else {
      h = Math.abs(z) - b;
    }
  }
  return { latDeg: (lat * 180) / Math.PI, lonDeg: (lon * 180) / Math.PI, heightKm: h };
}

/** Inertial speed (km/s) from Earth-fixed position and velocity: |v_ecef + omega x r|. */
export function inertialSpeed(x: number, y: number, z: number, vx: number, vy: number, vz: number): number {
  const wx = -EARTH_ROTATION_RATE * y;
  const wy = EARTH_ROTATION_RATE * x;
  void z;
  return Math.hypot(vx + wx, vy + wy, vz);
}

export function formatUtc(ms: number): string {
  const d = new Date(ms);
  const pad = (v: number) => String(v).padStart(2, "0");
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} UTC`
  );
}

export function formatOffset(ms: number, t0Ms: number): string {
  const dh = (ms - t0Ms) / 3.6e6;
  const sign = dh >= 0 ? "+" : "−";
  return `t₀ ${sign}${Math.abs(dh).toFixed(2)} h`;
}
