// MagicaVoxel .vox reader/writer.
// Reader handles SIZE/XYZI/RGBA plus the nTRN/nGRP/nSHP scene graph so
// multi-part models land where MagicaVoxel placed them. Z-up → Y-up on read.
// Writer emits a single-model file (used to hand David a first pass to edit).

const td = new TextDecoder();

function readString(dv, o) {
  const n = dv.getInt32(o, true);
  return { s: td.decode(new Uint8Array(dv.buffer, dv.byteOffset + o + 4, n)), next: o + 4 + n };
}
function readDict(dv, o) {
  const n = dv.getInt32(o, true);
  o += 4;
  const d = {};
  for (let i = 0; i < n; i++) {
    const k = readString(dv, o); o = k.next;
    const v = readString(dv, o); o = v.next;
    d[k.s] = v.s;
  }
  return { d, next: o };
}

// MagicaVoxel packs a rotation matrix into one byte.
function rotationFromByte(b) {
  const r0 = b & 3, r1 = (b >> 2) & 3;
  const r2 = 3 - r0 - r1;
  const s0 = (b >> 4) & 1 ? -1 : 1, s1 = (b >> 5) & 1 ? -1 : 1, s2 = (b >> 6) & 1 ? -1 : 1;
  const m = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  m[0][r0] = s0; m[1][r1] = s1; m[2][r2] = s2;
  return m;
}
const IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];

/** @returns {{ models: {size:number[], voxels:Uint8Array}[], palette: number[][], placements: {modelId:number, t:number[], r:number[][]}[] }} */
export function readVox(buffer) {
  const dv = new DataView(buffer.buffer ?? buffer, buffer.byteOffset ?? 0, buffer.byteLength);
  if (td.decode(new Uint8Array(dv.buffer, dv.byteOffset, 4)) !== 'VOX ') throw new Error('not a .vox file');
  const models = [];
  let palette = defaultVoxPalette();
  const nodes = new Map();
  let size = null;
  let o = 8;
  // MAIN chunk
  o += 12 + dv.getInt32(o + 4, true);
  while (o < dv.byteLength) {
    const id = td.decode(new Uint8Array(dv.buffer, dv.byteOffset + o, 4));
    const len = dv.getInt32(o + 4, true);
    const body = o + 12;
    if (id === 'SIZE') {
      size = [dv.getInt32(body, true), dv.getInt32(body + 4, true), dv.getInt32(body + 8, true)];
    } else if (id === 'XYZI') {
      const n = dv.getInt32(body, true);
      const vox = new Uint8Array(n * 4);
      vox.set(new Uint8Array(dv.buffer, dv.byteOffset + body + 4, n * 4));
      models.push({ size, voxels: vox });
    } else if (id === 'RGBA') {
      palette = [[0, 0, 0, 0]];
      for (let i = 0; i < 255; i++) {
        const p = body + i * 4;
        palette.push([dv.getUint8(p), dv.getUint8(p + 1), dv.getUint8(p + 2), dv.getUint8(p + 3)]);
      }
    } else if (id === 'nTRN') {
      const nodeId = dv.getInt32(body, true);
      let p = readDict(dv, body + 4).next;
      const child = dv.getInt32(p, true);
      p += 4 + 4 + 4; // child, reserved, layer
      const frames = dv.getInt32(p, true); p += 4;
      let t = [0, 0, 0], r = IDENTITY;
      for (let f = 0; f < frames; f++) {
        const fr = readDict(dv, p); p = fr.next;
        if (f === 0) {
          if (fr.d._t) t = fr.d._t.split(' ').map(Number);
          if (fr.d._r) r = rotationFromByte(parseInt(fr.d._r));
        }
      }
      nodes.set(nodeId, { type: 'trn', child, t, r });
    } else if (id === 'nGRP') {
      const nodeId = dv.getInt32(body, true);
      let p = readDict(dv, body + 4).next;
      const n = dv.getInt32(p, true); p += 4;
      const children = [];
      for (let i = 0; i < n; i++, p += 4) children.push(dv.getInt32(p, true));
      nodes.set(nodeId, { type: 'grp', children });
    } else if (id === 'nSHP') {
      const nodeId = dv.getInt32(body, true);
      let p = readDict(dv, body + 4).next;
      const n = dv.getInt32(p, true); p += 4;
      const modelIds = [];
      for (let i = 0; i < n; i++) {
        modelIds.push(dv.getInt32(p, true)); p += 4;
        p = readDict(dv, p).next;
      }
      nodes.set(nodeId, { type: 'shp', modelIds });
    }
    o = body + len; // children chunks of non-MAIN nodes are not used by the format
  }

  // Walk the scene graph accumulating transforms; fall back to one model at origin.
  const placements = [];
  if (nodes.size) {
    const mul = (a, b) => a.map((row, i) => [0, 1, 2].map(j => row[0] * b[0][j] + row[1] * b[1][j] + row[2] * b[2][j]));
    const apply = (m, v) => m.map(row => row[0] * v[0] + row[1] * v[1] + row[2] * v[2]);
    const walk = (id, t, r) => {
      const n = nodes.get(id);
      if (!n) return;
      if (n.type === 'trn') {
        const rt = apply(r, n.t);
        walk(n.child, [t[0] + rt[0], t[1] + rt[1], t[2] + rt[2]], mul(r, n.r));
      } else if (n.type === 'grp') n.children.forEach(c => walk(c, t, r));
      else n.modelIds.forEach(modelId => placements.push({ modelId, t, r }));
    };
    walk(0, [0, 0, 0], IDENTITY);
  }
  if (!placements.length) models.forEach((_, i) => placements.push({ modelId: i, t: [0, 0, 0], r: IDENTITY }));
  return { models, palette, placements };
}

/**
 * Stamp a parsed .vox into the grid at `origin` (world voxel coords, Y-up).
 * mapColor(rgba, voxIndex) → world palette index. Model center sits at origin.
 */
export function stampVox(vox, grid, origin, mapColor) {
  let n = 0;
  for (const pl of vox.placements) {
    const m = vox.models[pl.modelId];
    if (!m) continue;
    const half = m.size.map(s => Math.floor(s / 2));
    for (let i = 0; i < m.voxels.length; i += 4) {
      const ci = m.voxels[i + 3];
      const idx = mapColor(vox.palette[ci], ci);
      if (!idx) continue;
      // model-local, centered, rotated, translated (all Z-up)
      const lx = m.voxels[i] - half[0], ly = m.voxels[i + 1] - half[1], lz = m.voxels[i + 2] - half[2];
      const r = pl.r;
      const wx = r[0][0] * lx + r[0][1] * ly + r[0][2] * lz + pl.t[0];
      const wy = r[1][0] * lx + r[1][1] * ly + r[1][2] * lz + pl.t[1];
      const wz = r[2][0] * lx + r[2][1] * ly + r[2][2] * lz + pl.t[2];
      // Z-up → Y-up: (x, y_depth, z_up) → (x, z_up, -y_depth)
      grid.set(origin[0] + wx, origin[1] + wz, origin[2] - wy, idx);
      n++;
    }
  }
  return n;
}

/**
 * Write a single-model .vox. voxels: array of [x, y, z, colorIndex(1..255)] in
 * Y-up coordinates (converted to Z-up on write). palette: 256 × [r,g,b,a].
 */
export function writeVox(size, voxels, palette) {
  const te = new TextEncoder();
  const chunk = (id, body, children = new Uint8Array(0)) => {
    const out = new Uint8Array(12 + body.length + children.length);
    const dv = new DataView(out.buffer);
    out.set(te.encode(id), 0);
    dv.setInt32(4, body.length, true);
    dv.setInt32(8, children.length, true);
    out.set(body, 12);
    out.set(children, 12 + body.length);
    return out;
  };
  const sizeBody = new Uint8Array(12);
  const sdv = new DataView(sizeBody.buffer);
  // Y-up (x, y, z) → Z-up (x, -z, y): size maps (sx, sy, sz) → (sx, sz, sy)
  sdv.setInt32(0, size[0], true); sdv.setInt32(4, size[2], true); sdv.setInt32(8, size[1], true);
  const xyzi = new Uint8Array(4 + voxels.length * 4);
  new DataView(xyzi.buffer).setInt32(0, voxels.length, true);
  voxels.forEach(([x, y, z, c], i) => {
    const o = 4 + i * 4;
    xyzi[o] = x; xyzi[o + 1] = size[2] - 1 - z; xyzi[o + 2] = y; xyzi[o + 3] = c;
  });
  const rgba = new Uint8Array(256 * 4);
  for (let i = 1; i < 256; i++) {
    const c = palette[i] || [0, 0, 0, 255];
    rgba.set([c[0], c[1], c[2], c[3] ?? 255], (i - 1) * 4);
  }
  const children = concat(chunk('SIZE', sizeBody), chunk('XYZI', xyzi), chunk('RGBA', rgba));
  const main = chunk('MAIN', new Uint8Array(0), children);
  const header = new Uint8Array(8);
  header.set(te.encode('VOX '), 0);
  new DataView(header.buffer).setInt32(4, 150, true);
  return concat(header, main);
}

function concat(...arrs) {
  const out = new Uint8Array(arrs.reduce((n, a) => n + a.length, 0));
  let o = 0;
  for (const a of arrs) { out.set(a, o); o += a.length; }
  return out;
}

function defaultVoxPalette() {
  // MagicaVoxel's default palette is a fixed table; a neutral grey ramp is
  // enough here because every model we ship carries its own RGBA chunk.
  const p = [[0, 0, 0, 0]];
  for (let i = 1; i < 256; i++) p.push([i, i, i, 255]);
  return p;
}
