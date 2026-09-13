// Signed-distance authoring toolkit. Every procedural object is an SDF in
// voxel units that gets rasterized into the Grid at cell centers. Distances
// only need to be correct in sign near the surface, so approximations are fine.

const len2 = (x, z) => Math.sqrt(x * x + z * z);
const len3 = (x, y, z) => Math.sqrt(x * x + y * y + z * z);

export const sphere = (cx, cy, cz, r) => (x, y, z) => len3(x - cx, y - cy, z - cz) - r;

// Axis-aligned box from center and half extents.
export const box = (cx, cy, cz, hx, hy, hz) => (x, y, z) => {
  const dx = Math.abs(x - cx) - hx, dy = Math.abs(y - cy) - hy, dz = Math.abs(z - cz) - hz;
  const outside = len3(Math.max(dx, 0), Math.max(dy, 0), Math.max(dz, 0));
  return outside + Math.min(Math.max(dx, Math.max(dy, dz)), 0);
};

// Vertical cylinder between y0 and y1.
export const cylinderY = (cx, cz, r, y0, y1) => (x, y, z) => {
  const dr = len2(x - cx, z - cz) - r;
  const dy = Math.max(y0 - y, y - y1);
  return Math.max(dr, dy);
};

// Solid of revolution around a vertical axis: radius is a function of y.
export const revolveY = (cx, cz, y0, y1, radiusAt) => (x, y, z) => {
  const dy = Math.max(y0 - y, y - y1);
  const yc = Math.min(Math.max(y, y0), y1);
  return Math.max(len2(x - cx, z - cz) - radiusAt(yc), dy);
};

// Annular solid of revolution (a ring / tube wall) with inner and outer radii as functions of y.
export const annulusY = (cx, cz, y0, y1, innerAt, outerAt) => (x, y, z) => {
  const dy = Math.max(y0 - y, y - y1);
  const yc = Math.min(Math.max(y, y0), y1);
  const r = len2(x - cx, z - cz);
  return Math.max(Math.max(r - outerAt(yc), innerAt(yc) - r), dy);
};

// Torus lying flat (major radius R in xz, tube radius r), centered at (cx,cy,cz).
export const torusY = (cx, cy, cz, R, r) => (x, y, z) =>
  len2(len2(x - cx, z - cz) - R, y - cy) - r;

// Capsule / rounded line segment.
export const capsule = (ax, ay, az, bx, by, bz, r) => (x, y, z) => {
  const pax = x - ax, pay = y - ay, paz = z - az;
  const bax = bx - ax, bay = by - ay, baz = bz - az;
  const h = Math.min(Math.max((pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz), 0), 1);
  return len3(pax - bax * h, pay - bay * h, paz - baz * h) - r;
};

// Combinators
export const union = (...fs) => (x, y, z) => {
  let d = Infinity;
  for (const f of fs) { const v = f(x, y, z); if (v < d) d = v; }
  return d;
};
export const intersect = (a, b) => (x, y, z) => Math.max(a(x, y, z), b(x, y, z));
export const subtract = (a, b) => (x, y, z) => Math.max(a(x, y, z), -b(x, y, z));
export const smoothUnion = (k, ...fs) => (x, y, z) => {
  let d = fs[0](x, y, z);
  for (let i = 1; i < fs.length; i++) {
    const b = fs[i](x, y, z);
    const h = Math.min(Math.max(0.5 + 0.5 * (b - d) / k, 0), 1);
    d = b + (d - b) * h - k * h * (1 - h);
  }
  return d;
};
export const shell = (f, t) => (x, y, z) => Math.abs(f(x, y, z)) - t;
export const translate = (f, tx, ty, tz) => (x, y, z) => f(x - tx, y - ty, z - tz);
export const rotateY = (f, deg) => {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return (x, y, z) => f(x * c + z * s, y, -x * s + z * c);
};
// N-fold rotational copies of a shape around the y axis at the origin.
export const radial = (f, n, offsetDeg = 0) => union(...Array.from({ length: n }, (_, i) => rotateY(f, offsetDeg + (i * 360) / n)));

// Only keep the part of `f` inside a vertical y range (cheap clip).
export const clipY = (f, y0, y1) => (x, y, z) => Math.max(f(x, y, z), Math.max(y0 - y, y - y1));

/**
 * Rasterize an SDF into the grid. Samples cell centers inside the AABB.
 * aabb: { min: [x,y,z], max: [x,y,z] } in voxel coords (max exclusive).
 * Only writes where the SDF is inside; existing voxels outside are untouched.
 * Returns number of voxels written.
 */
export function rasterize(grid, sdf, aabb, palIdx, { onlyAir = false } = {}) {
  let n = 0;
  const [x0, y0, z0] = aabb.min.map(Math.floor);
  const [x1, y1, z1] = aabb.max.map(Math.ceil);
  for (let z = z0; z < z1; z++)
    for (let y = y0; y < y1; y++)
      for (let x = x0; x < x1; x++) {
        if (sdf(x + 0.5, y + 0.5, z + 0.5) <= 0) {
          if (onlyAir && grid.get(x, y, z) !== 0) continue;
          grid.set(x, y, z, palIdx);
          n++;
        }
      }
  return n;
}

// Carve: set voxels to air where the SDF is inside.
export function carve(grid, sdf, aabb) {
  return rasterize(grid, sdf, aabb, 0);
}

export const aabb = (x0, y0, z0, x1, y1, z1) => ({ min: [x0, y0, z0], max: [x1, y1, z1] });
export const aabbAround = (cx, cz, r, y0, y1) => aabb(cx - r - 1, y0 - 1, cz - r - 1, cx + r + 1, y1 + 1, cz + r + 1);
