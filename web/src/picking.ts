/**
 * Screen-space picking for the point cloud.
 *
 * Raycasting THREE.Points uses a world-space threshold, which does not suit fixed
 * pixel-size sprites. Instead every visible object's interpolated position is projected
 * to the screen and the nearest one within a pixel radius wins, provided the straight
 * line from the camera to it does not pass through the globe.
 */

import * as THREE from "three";
import { GLOBE_SCENE_RADIUS } from "./geodesy";
import { SCENE_PER_KM, type CataloguePoints } from "./points";

const tmp = new Float64Array(3);
const v = new THREE.Vector3();

export function pick(
  points: CataloguePoints,
  camera: THREE.Camera,
  px: number,
  py: number,
  width: number,
  height: number,
  radiusPx = 9,
): number {
  camera.updateMatrixWorld();
  const cam = camera.position;
  const camR2 = cam.lengthSq();
  const R2 = GLOBE_SCENE_RADIUS * GLOBE_SCENE_RADIUS;
  let best = -1;
  let bestD2 = radiusPx * radiusPx;
  for (let i = 0; i < points.n; i++) {
    if (!points.isVisible(i)) continue;
    points.positionOf(i, tmp);
    v.set(tmp[1] * SCENE_PER_KM, tmp[2] * SCENE_PER_KM, tmp[0] * SCENE_PER_KM);
    // Occlusion: does the camera-to-point segment cross the globe sphere?
    const dx = v.x - cam.x;
    const dy = v.y - cam.y;
    const dz = v.z - cam.z;
    const d2 = dx * dx + dy * dy + dz * dz;
    const tClosest = -(cam.x * dx + cam.y * dy + cam.z * dz) / d2;
    if (tClosest > 0 && tClosest < 1) {
      const cx = cam.x + tClosest * dx;
      const cy = cam.y + tClosest * dy;
      const cz = cam.z + tClosest * dz;
      if (cx * cx + cy * cy + cz * cz < R2 && camR2 > R2) continue;
    }
    v.project(camera);
    if (v.z > 1) continue; // behind the camera
    const sx = (v.x + 1) * 0.5 * width;
    const sy = (1 - v.y) * 0.5 * height;
    const ex = sx - px;
    const ey = sy - py;
    const e2 = ex * ex + ey * ey;
    if (e2 < bestD2) {
      bestD2 = e2;
      best = i;
    }
  }
  return best;
}
