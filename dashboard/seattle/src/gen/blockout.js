// Gray-box every landmark from the layout table at its real relative position.
// These are placeholders: later milestones replace each box with the real
// building, but its slot on the site is fixed here.
import { LANDMARKS, byId, ENV_VOXEL } from '../site/layout.js';
import { box, rotateY, translate, rasterize, aabb, annulusY } from '../voxel/Shapes.js';

export function buildBlockout(grid, pal) {
  const gray = pal.index('concrete_dark'), pave = pal.index('pavement'), water = pal.index('water');
  const stats = {};
  for (const l of LANDMARKS) {
    const L = byId[l.id];
    if (l.kind === 'box') {
      const hw = l.w / ENV_VOXEL / 2, hd = l.d / ENV_VOXEL / 2, h = l.h / ENV_VOXEL;
      const shape = translate(rotateY(box(0, h / 2, 0, hw, h / 2, hd), l.rot || 0), L.x, 0, L.z);
      const r = Math.hypot(hw, hd) + 2;
      stats[l.id] = rasterize(grid, shape, aabb(L.x - r, 0, L.z - r, L.x + r, h + 1, L.z + r), gray);
    } else if (l.kind === 'ring') {
      const R = l.r / ENV_VOXEL;
      stats[l.id] = rasterize(grid, annulusY(L.x, L.z, -1, 1, () => R - 3, () => R), aabb(L.x - R - 2, -1, L.z - R - 2, L.x + R + 2, 2, L.z + R + 2), pave)
        + rasterize(grid, annulusY(L.x, L.z, -1, 0, () => 0, () => R - 3), aabb(L.x - R, -1, L.z - R, L.x + R, 0, L.z + R), water);
    }
  }
  return stats;
}
