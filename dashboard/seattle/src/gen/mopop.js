// MoPOP (Experience Music Project), Frank Gehry, 2000 — as SDF lobes at hero
// scale (0.25 m). Arrangement from David's aerial reference (2026-09-12, with
// Memorial Stadium and the Armory as anchors) plus the emp/ photo set:
//   gold faces 5th Ave (EAST) and the monorail curves through it; red sits
//   behind the gold to the north-east; the purple Sky Church box is central;
//   the pale-BLUE billow on the SOUTH is the monorail station canopy — the
//   platform faces the Needle from the south-west; the big brushed-SILVER
//   billow is the west side; a small silver-white form at the north-west.
//
// The table is in METRES relative to the building centre; x east, z south.
// Edit a line here to move a lobe. Lobes are rasterized in order, later ones
// win where they overlap, so colour boundaries follow the surface intersections.
// NOTE: yaw rotates about the BUILDING centre, so a yawed lobe lands away from
// its nominal centre — check the top-down bake after moving one.
import {
  ellipsoid, roundedBox, smoothUnion, rotateY, translate, clipY, capsule, ripple,
  rasterize, aabb,
} from '../voxel/Shapes.js';

export const HERO = 0.25;

// Each lobe: parts (ellipsoids [cx, cy, cz, rx, ry, rz]), blend radius, yaw (deg), colour.
export const LOBES = [
  { id: 'skyChurch', color: 'mopop_purple', roofColor: 'mopop_dark', box: [-2, 12.5, -8, 17, 12.5, 17, 5], yaw: 6 },
  { id: 'red',    color: 'mopop_red',    yaw: 0,   k: 6, fold: [0.7, 16], parts: [[18, 8.5, -22, 15, 9, 15], [6, 6.5, -34, 12, 6.5, 9], [26, 7, -36, 9, 7, 8]] },
  { id: 'silver', color: 'mopop_silver', yaw: 0,   k: 6, fold: [1.4, 13], parts: [[-30, 11, -6, 17, 12, 24], [-38, 8, 14, 10, 8, 10], [-20, 14, -26, 11, 8, 10]] },
  { id: 'white',  color: 'mopop_white',  yaw: 0,   k: 7, fold: [1.3, 15], parts: [[-12, 8, -32, 14, 8, 11], [-26, 6, -40, 9, 6, 8]] },
  { id: 'blue',   color: 'mopop_blue',   yaw: 0,   k: 7, fold: [1.2, 18], parts: [[4, 8, 24, 34, 8.5, 13], [-24, 6, 28, 12, 6.5, 9], [30, 7, 26, 10, 7, 9]] },
  { id: 'gold',   color: 'mopop_gold',   yaw: 0,   k: 5, fold: [0.8, 11], parts: [[30, 10, 4, 14, 12, 20], [38, 7, -12, 9, 8, 10], [26, 13, 18, 9, 7, 9]] },
];

// Roof "fret" trusses across the red lobe (metres, relative to centre): [x0,y0,z0, x1,y1,z1]
const FRETS = [
  [2, 15.5, -36, 32, 16.5, -20],
  [6, 16.0, -42, 34, 17.0, -28],
  [0, 15.0, -30, 26, 15.5, -14],
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
 * Line the monorail tunnel where it passes through the building: for every
 * cross-section, cells just inside the carved boundary that have solid
 * building beyond them get the skin colour of that building material, so the
 * gold form wraps the track in gold and the blue canopy in blue.
 */
export function lineTunnel(grid, spline, { scale = 2, halfWidth = 34, floor = -4, ceiling = 30, sRange = null } = {}) {
  let n = 0;
  const [sA, sB] = sRange || [0, spline.length];
  for (let s = sA; s <= sB; s += 0.5) {
    const p = spline.pointAt(s), t = spline.tangentAt(s);
    const nx = t.z, nz = -t.x;
    const px = p.x * scale, pz = p.z * scale, py = spline.y * scale;
    for (const sign of [-1, 1]) {
      for (let y = py + floor; y <= py + ceiling; y++) {
        const outside = grid.get(Math.round(px + nx * sign * (halfWidth + 1)), y, Math.round(pz + nz * sign * (halfWidth + 1)));
        if (!outside) continue;
        for (let d = 0; d <= 1; d++) {
          grid.set(Math.round(px + nx * sign * (halfWidth - d)), y, Math.round(pz + nz * sign * (halfWidth - d)), outside); n++;
        }
      }
    }
    for (let o = -halfWidth; o <= halfWidth; o += 0.5) {
      const x = Math.round(px + nx * o), z = Math.round(pz + nz * o);
      const above = grid.get(x, py + ceiling + 1, z);
      if (!above) continue;
      for (let d = 0; d <= 1; d++) { grid.set(x, py + ceiling - d, z, above); n++; }
    }
  }
  return n;
}
