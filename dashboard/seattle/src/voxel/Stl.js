// Binary STL → solid voxels. Surface is sampled densely enough to be
// 26-connected, then exterior air is flood-filled (6-connected) so everything
// else becomes interior. Z-up STL is converted to Y-up.

export function parseStl(buf) {
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const n = dv.getUint32(80, true);
  const tris = new Float32Array(n * 9);
  for (let i = 0; i < n; i++) {
    const o = 84 + i * 50 + 12;
    for (let k = 0; k < 9; k++) tris[i * 9 + k] = dv.getFloat32(o + k * 4, true);
  }
  return tris;
}

/**
 * Voxelize triangles.
 * opts: { height: target height in voxels (Y-up), zUp: true, step: sample spacing (voxels) }
 * Returns { size:[w,h,d], solid: Uint8Array(w*h*d) (1 = solid), surface: Uint8Array, scale }
 */
export function voxelizeStl(tris, { height, zUp = true, step = 0.35 } = {}) {
  // Convert to Y-up and find bounds
  const n = tris.length / 3;
  const pts = new Float32Array(tris.length);
  for (let i = 0; i < n; i++) {
    const x = tris[i * 3], y = tris[i * 3 + 1], z = tris[i * 3 + 2];
    if (zUp) { pts[i * 3] = x; pts[i * 3 + 1] = z; pts[i * 3 + 2] = -y; }
    else { pts[i * 3] = x; pts[i * 3 + 1] = y; pts[i * 3 + 2] = z; }
  }
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < n; i++) for (let k = 0; k < 3; k++) {
    const v = pts[i * 3 + k];
    if (v < min[k]) min[k] = v; if (v > max[k]) max[k] = v;
  }
  const scale = height / (max[1] - min[1]);
  const size = [0, 1, 2].map((k) => Math.ceil((max[k] - min[k]) * scale) + 2);
  const [W, H, D] = size;
  const surface = new Uint8Array(W * H * D);
  const idx = (x, y, z) => x + y * W + z * W * H;
  // model → voxel space: centre x/z, base at y=1 (1-voxel padding all round)
  const tx = (v, k) => (v - min[k]) * scale + 1;

  // Sample every triangle
  const tri = pts;
  for (let t = 0; t < n / 3; t++) {
    const o = t * 9;
    const a = [tx(tri[o], 0), tx(tri[o + 1], 1), tx(tri[o + 2], 2)];
    const b = [tx(tri[o + 3], 0), tx(tri[o + 4], 1), tx(tri[o + 5], 2)];
    const c = [tx(tri[o + 6], 0), tx(tri[o + 7], 1), tx(tri[o + 8], 2)];
    const e1 = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const e2 = Math.hypot(c[0] - a[0], c[1] - a[1], c[2] - a[2]);
    const e3 = Math.hypot(c[0] - b[0], c[1] - b[1], c[2] - b[2]);
    const steps = Math.max(1, Math.ceil(Math.max(e1, e2, e3) / step));
    for (let i = 0; i <= steps; i++) {
      for (let j = 0; j <= steps - i; j++) {
        const u = i / steps, v = j / steps, w = 1 - u - v;
        const x = Math.floor(a[0] * w + b[0] * u + c[0] * v);
        const y = Math.floor(a[1] * w + b[1] * u + c[1] * v);
        const z = Math.floor(a[2] * w + b[2] * u + c[2] * v);
        if (x >= 0 && y >= 0 && z >= 0 && x < W && y < H && z < D) surface[idx(x, y, z)] = 1;
      }
    }
  }

  // Flood exterior from the padded corner
  const solid = new Uint8Array(W * H * D).fill(1);
  const stack = [idx(0, 0, 0)];
  solid[stack[0]] = 0;
  while (stack.length) {
    const i = stack.pop();
    const x = i % W, y = ((i / W) | 0) % H, z = (i / (W * H)) | 0;
    const tryPush = (nx, ny, nz) => {
      if (nx < 0 || ny < 0 || nz < 0 || nx >= W || ny >= H || nz >= D) return;
      const j = idx(nx, ny, nz);
      if (solid[j] && !surface[j]) { solid[j] = 0; stack.push(j); }
    };
    tryPush(x + 1, y, z); tryPush(x - 1, y, z);
    tryPush(x, y + 1, z); tryPush(x, y - 1, z);
    tryPush(x, y, z + 1); tryPush(x, y, z - 1);
  }
  let count = 0;
  for (let i = 0; i < solid.length; i++) count += solid[i];
  return { size, solid, surface, scale, count };
}

/**
 * Stamp a voxelized model into the grid. origin = world voxel position of the
 * model's base centre. colorize(x, y, z, info) → palette index (0 skips);
 * x/z are centred model coords, y from 0, info = { h: 0..1 height fraction, r: xz radius, size }.
 */
export function stampVoxels(grid, model, origin, colorize) {
  const [W, H, D] = model.size;
  const cx = W / 2, cz = D / 2;
  let n = 0;
  for (let z = 0; z < D; z++)
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++) {
        if (!model.solid[x + y * W + z * W * H]) continue;
        const lx = x - cx, ly = y - 1, lz = z - cz;
        const idx = colorize(lx, ly, lz, { h: ly / (H - 2), r: Math.hypot(lx, lz), size: model.size });
        if (!idx) continue;
        grid.set(origin[0] + Math.round(lx), origin[1] + ly, origin[2] + Math.round(lz), idx);
        n++;
      }
  return n;
}
