// MoPOP (Experience Music Project), Frank Gehry, 2000 — as SDF lobes at hero
// scale (0.25 m). Arrangement traced from David's reference aerials
// (~/Desktop/Swayne Film Studio/emp/emp1.jpg from the north, emp3.jpg from
// the Needle) and street shots. North up, east right; the monorail runs along
// the building's east edge and pierces the gold "fist" at the NE.
//
// The table is in METRES relative to the building centre; x east, z south.
// Edit a line here to move a lobe. Lobes are rasterized in order, later ones
// win where they overlap, so colour boundaries follow the surface intersections.
import {
  ellipsoid, roundedBox, smoothUnion, rotateY, translate, clipY, capsule, ripple,
  rasterize, aabb,
} from '../voxel/Shapes.js';

export const HERO = 0.25;

// Each lobe: parts (ellipsoids [cx, cy, cz, rx, ry, rz]), blend radius, yaw (deg), colour.
export const LOBES = [
  { id: 'skyChurch', color: 'mopop_purple', roofColor: 'mopop_dark', box: [2, 12.5, -2, 18, 12.5, 20, 5], yaw: 10 },
  { id: 'red',    color: 'mopop_red',    yaw: -12, k: 6, fold: [0.7, 16], parts: [[-4, 8.5, -38, 26, 9, 14], [12, 7, -30, 12, 7, 10], [-20, 6, -30, 10, 6, 8]] },
  { id: 'silver', color: 'mopop_silver', yaw: 20,  k: 6, fold: [1.4, 13], parts: [[-32, 10, -14, 15, 11, 20], [-38, 7, 6, 10, 7.5, 10], [-22, 13, -26, 9, 8, 9]] },
  { id: 'white',  color: 'mopop_white',  yaw: -8,  k: 7, fold: [1.3, 15], parts: [[-26, 7.5, 22, 18, 8, 19], [-8, 6, 30, 12, 6, 10], [-34, 5, 30, 8, 5, 8]] },
  { id: 'blue',   color: 'mopop_blue',   yaw: 4,   k: 7, fold: [1.2, 18], parts: [[20, 8.5, 12, 14, 9.5, 28], [27, 6.5, 34, 9, 7, 13], [13, 9.5, -6, 11, 9, 11]] },
  { id: 'gold',   color: 'mopop_gold',   yaw: -18, k: 5, fold: [0.8, 11], parts: [[22, 10, -28, 18, 12, 17], [33, 8, -18, 10, 9, 10], [12, 14, -36, 9, 7, 9]] },
];

// Roof "fret" trusses across the red lobe (metres, relative to centre): [x0,y0,z0, x1,y1,z1]
const FRETS = [
  [-26, 15.5, -44, 12, 16.5, -30],
  [-22, 16.0, -49, 16, 17.0, -36],
  [-18, 15.0, -38, 6, 15.5, -22],
];

/**
 * Build MoPOP into a hero-scale grid. centre = [x, z] of the building centre in
 * hero voxels. Returns { voxels per lobe }.
 */
export function buildMoPOP(grid, pal, centre) {
  const P = (n) => pal.index(n);
  const M = 1 / HERO; // metres → hero voxels
  const [cx, cz] = centre;
  const stats = {};

  for (const lobe of LOBES) {
    let sdf, bounds;
    if (lobe.box) {
      const [bx, by, bz, hx, hy, hz, r] = lobe.box.map((v) => v * M);
      sdf = roundedBox(bx, by, bz, hx, hy, hz, r);
      bounds = { min: [bx - hx, 0, bz - hz], max: [bx + hx, by + hy, bz + hz] };
    } else {
      const parts = lobe.parts.map(([x, y, z, rx, ry, rz]) => ellipsoid(x * M, y * M, z * M, rx * M, ry * M, rz * M));
      sdf = parts.length > 1 ? smoothUnion(lobe.k * M, ...parts) : parts[0];
      if (lobe.fold) {
        const i = LOBES.indexOf(lobe);
        sdf = ripple(sdf, lobe.fold[0] * M, lobe.fold[1] * M, i);            // broad billows
        sdf = ripple(sdf, lobe.fold[0] * 0.45 * M, lobe.fold[1] * 0.43 * M, i * 2.1 + 1); // finer creases
      }
      let min = [Infinity, 0, Infinity], max = [-Infinity, -Infinity, -Infinity];
      for (const [x, y, z, rx, ry, rz] of lobe.parts) {
        min = [Math.min(min[0], (x - rx) * M), 0, Math.min(min[2], (z - rz) * M)];
        max = [Math.max(max[0], (x + rx) * M), Math.max(max[1], (y + ry) * M), Math.max(max[2], (z + rz) * M)];
      }
      bounds = { min, max };
    }
    // yaw about the lobe's own centre, then place at the building centre; keep above ground
    const placed = translate(clipY(rotateY(sdf, lobe.yaw || 0), 0, 1e9), cx, 0, cz);
    const pad = Math.hypot(bounds.max[0] - bounds.min[0], bounds.max[2] - bounds.min[2]) * 0.5;
    const mid = [(bounds.min[0] + bounds.max[0]) / 2, (bounds.min[2] + bounds.max[2]) / 2];
    const box = aabb(cx + mid[0] - pad, 0, cz + mid[1] - pad, cx + mid[0] + pad, bounds.max[1] + 2, cz + mid[1] + pad);
    stats[lobe.id] = rasterize(grid, placed, box, P(lobe.color));
    if (lobe.roofColor) {
      // recolour the top slab of the box (the Sky Church's dark flat roof)
      const topY = Math.round(bounds.max[1]);
      const roofSdf = translate(clipY(rotateY(sdf, lobe.yaw || 0), topY - 6, topY + 2), cx, 0, cz);
      stats[lobe.id + '_roof'] = rasterize(grid, roofSdf, { min: [box.min[0], topY - 6, box.min[2]], max: [box.max[0], topY + 2, box.max[2]] }, P(lobe.roofColor));
    }
  }

  // Frets: thin trusses spanning the red lobe's roof
  let n = 0;
  for (const [x0, y0, z0, x1, y1, z1] of FRETS) {
    const c = translate(capsule(x0 * M, y0 * M, z0 * M, x1 * M, y1 * M, z1 * M, 0.7 * M), cx, 0, cz);
    n += rasterize(grid, c, aabb(cx + Math.min(x0, x1) * M - 4, Math.min(y0, y1) * M - 4, cz + Math.min(z0, z1) * M - 4, cx + Math.max(x0, x1) * M + 4, Math.max(y0, y1) * M + 4, cz + Math.max(z0, z1) * M + 4), P('chrome'));
  }
  stats.frets = n;
  return stats;
}

/**
 * Line the monorail tunnel with gold where it passes through the building:
 * for every cross-section, cells just inside the carved boundary that have
 * solid building beyond them become gold "collar" skin.
 */
export function goldCollar(grid, pal, spline, { scale = 2, halfWidth = 34, floor = -4, ceiling = 30, zRange = null } = {}) {
  const gold = pal.index('mopop_gold');
  let n = 0;
  for (let s = 0; s <= spline.length; s += 0.5) {
    const p = spline.pointAt(s), t = spline.tangentAt(s);
    if (zRange && (p.z < zRange[0] || p.z > zRange[1])) continue;
    const nx = t.z, nz = -t.x;
    const px = p.x * scale, pz = p.z * scale, py = spline.y * scale;
    // side walls
    for (const sign of [-1, 1]) {
      for (let y = py + floor; y <= py + ceiling; y++) {
        const ox = px + nx * sign * (halfWidth + 1), oz = pz + nz * sign * (halfWidth + 1);
        if (!grid.get(Math.round(ox), y, Math.round(oz))) continue;
        for (let d = 0; d <= 1; d++) {
          const ix = px + nx * sign * (halfWidth - d), iz = pz + nz * sign * (halfWidth - d);
          grid.set(Math.round(ix), y, Math.round(iz), gold); n++;
        }
      }
    }
    // ceiling
    for (let o = -halfWidth; o <= halfWidth; o += 0.5) {
      const x = Math.round(px + nx * o), z = Math.round(pz + nz * o);
      if (!grid.get(x, py + ceiling + 1, z)) continue;
      for (let d = 0; d <= 1; d++) { grid.set(x, py + ceiling - d, z, gold); n++; }
    }
  }
  return n;
}
