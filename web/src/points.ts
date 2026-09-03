/**
 * One THREE.Points object for the whole catalogue.
 *
 * The worker delivers Earth-fixed position and velocity on a time grid. Rather than
 * uploading a new position buffer every animation frame, the geometry carries the two
 * bracketing grid frames (p0, v0 at tA; p1, v1 at tB) and the vertex shader evaluates a
 * cubic Hermite polynomial at the current fraction `uT`. For a 90-minute orbit and a
 * one-minute grid the interpolation error is under 10 m; at a 12-minute grid it is
 * still under 10 km, below a pixel at globe scale. Only the fraction changes per frame.
 *
 * Scene coordinates: globe.gl uses x = cos(lat) sin(lon), y = sin(lat), z = cos(lat)
 * cos(lon) on a sphere of radius 100, so an Earth-fixed (X, Y, Z) maps to (Y, Z, X)
 * scaled by 100 / 6371 km. main.ts checks this against globe.gl's own getCoords.
 */

import * as THREE from "three";
import { GLOBE_MEAN_RADIUS_KM, GLOBE_SCENE_RADIUS } from "./geodesy";

export const SCENE_PER_KM = GLOBE_SCENE_RADIUS / GLOBE_MEAN_RADIUS_KM;

/** Category colours, indexed like manifest.categories. */
export const CATEGORY_COLOURS: Record<string, string> = {
  station: "#ffd166",
  starlink: "#4cc9f0",
  oneweb: "#b388ff",
  constellation: "#06d6a0",
  payload: "#e8eef7",
  rocket_body: "#ff9f43",
  debris: "#ef476f",
  unknown: "#8d99ae",
};

const VERTEX = /* glsl */ `
attribute vec3 p0;
attribute vec3 v0;
attribute vec3 p1;
attribute vec3 v1;
attribute float cat;
attribute float vis;
attribute float idx;
uniform float uT;
uniform float uH;
uniform float uScale;
uniform vec3 uPalette[8];
uniform float uPointSize;
uniform float uHighlight;
uniform float uHighlight2;
uniform float uPixelRatio;
varying vec3 vColor;

void main() {
  float t = clamp(uT, 0.0, 1.0);
  float t2 = t * t;
  float t3 = t2 * t;
  float h00 = 2.0 * t3 - 3.0 * t2 + 1.0;
  float h10 = t3 - 2.0 * t2 + t;
  float h01 = -2.0 * t3 + 3.0 * t2;
  float h11 = t3 - t2;
  vec3 p = h00 * p0 + h10 * uH * v0 + h01 * p1 + h11 * uH * v1;
  vec3 scene = vec3(p.y, p.z, p.x) * uScale;
  bool highlighted = abs(idx - uHighlight) < 0.5 || abs(idx - uHighlight2) < 0.5;
  vec4 mv = modelViewMatrix * vec4(scene, 1.0);
  gl_Position = projectionMatrix * mv;
  float size = vis > 0.5 ? (highlighted ? uPointSize * 2.6 : uPointSize) : 0.0;
  gl_PointSize = size * uPixelRatio;
  if (vis < 0.5) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
  }
  vColor = highlighted ? vec3(1.0, 1.0, 1.0) : uPalette[int(cat)];
}
`;

const FRAGMENT = /* glsl */ `
uniform float uOpacity;
varying vec3 vColor;

void main() {
  vec2 c = gl_PointCoord - vec2(0.5);
  float d2 = dot(c, c);
  if (d2 > 0.25) discard;
  float edge = smoothstep(0.25, 0.16, d2);
  gl_FragColor = vec4(vColor, uOpacity * edge);
}
`;

export interface Frame {
  tMs: number;
  /** Earth-fixed position, km, n*3. */
  pos: Float32Array;
  /** Earth-fixed velocity, km/s, n*3. */
  vel: Float32Array;
  /** SGP4 error code per object. */
  err: Int8Array;
}

export class CataloguePoints {
  readonly points: THREE.Points;
  readonly n: number;
  private readonly geometry: THREE.BufferGeometry;
  private readonly material: THREE.ShaderMaterial;
  private readonly p0: THREE.BufferAttribute;
  private readonly v0: THREE.BufferAttribute;
  private readonly p1: THREE.BufferAttribute;
  private readonly v1: THREE.BufferAttribute;
  private readonly vis: THREE.BufferAttribute;
  /** Filter mask (category/band); combined with per-frame SGP4 errors into `vis`. */
  private readonly filterMask: Uint8Array;
  private errMask: Int8Array;
  tA = 0;
  tB = 0;

  constructor(n: number, categoryIndex: Int32Array, categoryNames: string[]) {
    this.n = n;
    this.geometry = new THREE.BufferGeometry();
    this.p0 = new THREE.BufferAttribute(new Float32Array(n * 3), 3);
    this.v0 = new THREE.BufferAttribute(new Float32Array(n * 3), 3);
    this.p1 = new THREE.BufferAttribute(new Float32Array(n * 3), 3);
    this.v1 = new THREE.BufferAttribute(new Float32Array(n * 3), 3);
    this.vis = new THREE.BufferAttribute(new Float32Array(n), 1);
    for (const a of [this.p0, this.v0, this.p1, this.v1, this.vis]) a.setUsage(THREE.DynamicDrawUsage);
    const cat = new Float32Array(n);
    const idx = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      cat[i] = categoryIndex[i];
      idx[i] = i;
    }
    this.geometry.setAttribute("position", this.p0); // three needs a "position" attribute; the shader uses p0..p1
    this.geometry.setAttribute("p0", this.p0);
    this.geometry.setAttribute("v0", this.v0);
    this.geometry.setAttribute("p1", this.p1);
    this.geometry.setAttribute("v1", this.v1);
    this.geometry.setAttribute("cat", new THREE.BufferAttribute(cat, 1));
    this.geometry.setAttribute("idx", new THREE.BufferAttribute(idx, 1));
    this.geometry.setAttribute("vis", this.vis);
    // Bounding sphere large enough for cislunar objects, so nothing is frustum-culled by mistake.
    this.geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 100 * 80);

    const palette: THREE.Vector3[] = [];
    for (let i = 0; i < 8; i++) {
      const name = categoryNames[i] ?? "unknown";
      const c = new THREE.Color(CATEGORY_COLOURS[name] ?? CATEGORY_COLOURS.unknown);
      palette.push(new THREE.Vector3(c.r, c.g, c.b));
    }

    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT,
      uniforms: {
        uT: { value: 0 },
        uH: { value: 1 },
        uScale: { value: SCENE_PER_KM },
        uPalette: { value: palette },
        uPointSize: { value: 2.6 },
        uHighlight: { value: -1 },
        uHighlight2: { value: -1 },
        uPixelRatio: { value: Math.min(window.devicePixelRatio || 1, 2) },
        uOpacity: { value: 0.95 },
      },
      transparent: true,
      depthTest: true,
      depthWrite: false,
    });

    this.points = new THREE.Points(this.geometry, this.material);
    this.points.frustumCulled = false;
    this.points.renderOrder = 5;
    this.filterMask = new Uint8Array(n).fill(1);
    this.errMask = new Int8Array(n);
  }

  /** Install the bracketing pair of grid frames. */
  setFrames(a: Frame, b: Frame): void {
    if (a.tMs === this.tA && b.tMs === this.tB) return;
    (this.p0.array as Float32Array).set(a.pos);
    (this.v0.array as Float32Array).set(a.vel);
    (this.p1.array as Float32Array).set(b.pos);
    (this.v1.array as Float32Array).set(b.vel);
    this.p0.needsUpdate = true;
    this.v0.needsUpdate = true;
    this.p1.needsUpdate = true;
    this.v1.needsUpdate = true;
    this.tA = a.tMs;
    this.tB = b.tMs;
    this.material.uniforms.uH.value = (b.tMs - a.tMs) / 1000;
    let changed = false;
    for (let i = 0; i < this.n; i++) {
      const e = a.err[i] !== 0 || b.err[i] !== 0 ? 1 : 0;
      if (e !== this.errMask[i]) {
        this.errMask[i] = e;
        changed = true;
      }
    }
    if (changed) this.refreshVisibility();
  }

  /** Set the interpolation fraction for time `tMs`. */
  setTime(tMs: number): void {
    const h = this.tB - this.tA;
    this.material.uniforms.uT.value = h > 0 ? (tMs - this.tA) / h : 0;
  }

  get fraction(): number {
    return Math.min(1, Math.max(0, this.material.uniforms.uT.value as number));
  }

  get hasFrames(): boolean {
    return this.tB > this.tA;
  }

  setFilter(mask: Uint8Array): void {
    this.filterMask.set(mask);
    this.refreshVisibility();
  }

  /** Draw up to two objects white and enlarged: a hovered or selected object, and the other half of a pair. */
  setHighlight(index: number, second = -1): void {
    this.material.uniforms.uHighlight.value = index;
    this.material.uniforms.uHighlight2.value = second;
  }

  /** Number of objects currently drawn. */
  visibleCount(): number {
    let c = 0;
    const arr = this.vis.array as Float32Array;
    for (let i = 0; i < this.n; i++) c += arr[i];
    return c;
  }

  isVisible(i: number): boolean {
    return (this.vis.array as Float32Array)[i] > 0.5;
  }

  /** Interpolated Earth-fixed position (km) of object `i` at the current fraction. */
  positionOf(i: number, out: Float64Array = new Float64Array(3)): Float64Array {
    const t = this.fraction;
    const t2 = t * t;
    const t3 = t2 * t;
    const h00 = 2 * t3 - 3 * t2 + 1;
    const h10 = t3 - 2 * t2 + t;
    const h01 = -2 * t3 + 3 * t2;
    const h11 = t3 - t2;
    const h = this.material.uniforms.uH.value as number;
    const p0 = this.p0.array as Float32Array;
    const v0 = this.v0.array as Float32Array;
    const p1 = this.p1.array as Float32Array;
    const v1 = this.v1.array as Float32Array;
    const k = i * 3;
    for (let d = 0; d < 3; d++) {
      out[d] = h00 * p0[k + d] + h10 * h * v0[k + d] + h01 * p1[k + d] + h11 * h * v1[k + d];
    }
    return out;
  }

  /** Interpolated Earth-fixed velocity (km/s) of object `i` (derivative of the Hermite curve). */
  velocityOf(i: number, out: Float64Array = new Float64Array(3)): Float64Array {
    const t = this.fraction;
    const t2 = t * t;
    const d00 = 6 * t2 - 6 * t;
    const d10 = 3 * t2 - 4 * t + 1;
    const d01 = -6 * t2 + 6 * t;
    const d11 = 3 * t2 - 2 * t;
    const h = this.material.uniforms.uH.value as number;
    const p0 = this.p0.array as Float32Array;
    const v0 = this.v0.array as Float32Array;
    const p1 = this.p1.array as Float32Array;
    const v1 = this.v1.array as Float32Array;
    const k = i * 3;
    for (let d = 0; d < 3; d++) {
      out[d] = (d00 * p0[k + d] + d10 * h * v0[k + d] + d01 * p1[k + d] + d11 * h * v1[k + d]) / h;
    }
    return out;
  }

  /**
   * Release the GPU buffers and the shader program.
   *
   * Needed because entering replay swaps one catalogue for another of a different size, and a
   * `THREE.Points` whose geometry is still resident is 13,000 to 32,000 objects' worth of
   * vertex buffers that nothing will ever draw again. The caller removes it from the scene
   * first; three.js does not free the GPU side on its own.
   */
  dispose(): void {
    this.geometry.dispose();
    this.material.dispose();
  }

  private refreshVisibility(): void {
    const arr = this.vis.array as Float32Array;
    for (let i = 0; i < this.n; i++) arr[i] = this.filterMask[i] && !this.errMask[i] ? 1 : 0;
    this.vis.needsUpdate = true;
  }
}
