// Sweep the monorail beam cross-section (3 wide × 4 tall, env voxels) along a
// Spline, with piers every ~70 ft (42 voxels) down to the ground.
export function buildBeam(grid, pal, spline, { pierEvery = 42, pierSkip = () => false } = {}) {
  const beam = pal.index('beam_concrete'), pier = pal.index('concrete_dark');
  const top = spline.y;
  let n = 0;
  const seen = new Set();
  for (let s = 0; s <= spline.length; s += 0.5) {
    const p = spline.pointAt(s), t = spline.tangentAt(s);
    const nx = t.z, nz = -t.x; // lateral
    for (let o = -1; o <= 1; o += 0.5)
      for (let y = top - 3; y <= top; y++) {
        const x = Math.round(p.x + nx * o), z = Math.round(p.z + nz * o);
        const key = `${x},${y},${z}`;
        if (seen.has(key)) continue;
        seen.add(key);
        grid.set(x, y, z, beam);
        n++;
      }
  }
  for (let s = pierEvery / 2; s < spline.length; s += pierEvery) {
    const p = spline.pointAt(s);
    if (pierSkip(p)) continue;
    const cx = Math.round(p.x), cz = Math.round(p.z);
    for (let y = 0; y <= top - 4; y++)
      for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) { grid.set(cx + dx, y, cz + dz, pier); n++; }
    for (let dz = -2; dz <= 2; dz++) for (let dx = -2; dx <= 2; dx++) grid.set(cx + dx, top - 4, cz + dz, pier);
  }
  return n;
}

/** Carve a corridor for the trains along a spline through whatever is there. */
export function carveCorridor(grid, spline, { halfWidth = 18, floor = -2, ceiling = 34 } = {}) {
  let n = 0;
  for (let s = 0; s <= spline.length; s += 0.5) {
    const p = spline.pointAt(s), t = spline.tangentAt(s);
    const nx = t.z, nz = -t.x;
    for (let o = -halfWidth; o <= halfWidth; o += 0.5)
      for (let y = spline.y + floor; y <= spline.y + ceiling; y++) {
        const x = Math.round(p.x + nx * o), z = Math.round(p.z + nz * o);
        if (grid.get(x, y, z)) { grid.set(x, y, z, 0); n++; }
      }
  }
  return n;
}
