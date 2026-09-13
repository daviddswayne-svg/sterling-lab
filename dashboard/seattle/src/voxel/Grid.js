// Sparse voxel grid: world split into 32³ chunks, each a Uint8Array of palette
// indices (0 = air). Shared by the Node bake and the browser.

export const CHUNK = 32;
export const CHUNK_BITS = 5;
export const CHUNK_MASK = CHUNK - 1;
export const CHUNK_VOLUME = CHUNK * CHUNK * CHUNK;
export const APRON = CHUNK + 2; // chunk + 1-voxel border on every side, for meshing

const KEY_OFFSET = 512; // chunk coords live in [-512, 511]

export function chunkKey(cx, cy, cz) {
  return ((cx + KEY_OFFSET) << 20) | ((cy + KEY_OFFSET) << 10) | (cz + KEY_OFFSET);
}

export function unpackKey(key) {
  return [
    (key >>> 20) - KEY_OFFSET,
    ((key >>> 10) & 1023) - KEY_OFFSET,
    (key & 1023) - KEY_OFFSET,
  ];
}

export function voxelIndex(lx, ly, lz) {
  return lx + (ly << CHUNK_BITS) + (lz << (CHUNK_BITS * 2));
}

export class Grid {
  constructor() {
    this.chunks = new Map(); // key -> Uint8Array(CHUNK_VOLUME)
  }

  getChunk(cx, cy, cz, create = false) {
    const key = chunkKey(cx, cy, cz);
    let c = this.chunks.get(key);
    if (!c && create) {
      c = new Uint8Array(CHUNK_VOLUME);
      this.chunks.set(key, c);
    }
    return c;
  }

  get(x, y, z) {
    const c = this.chunks.get(chunkKey(x >> CHUNK_BITS, y >> CHUNK_BITS, z >> CHUNK_BITS));
    if (!c) return 0;
    return c[voxelIndex(x & CHUNK_MASK, y & CHUNK_MASK, z & CHUNK_MASK)];
  }

  set(x, y, z, v) {
    const c = this.getChunk(x >> CHUNK_BITS, y >> CHUNK_BITS, z >> CHUNK_BITS, v !== 0);
    if (!c) return;
    c[voxelIndex(x & CHUNK_MASK, y & CHUNK_MASK, z & CHUNK_MASK)] = v;
  }

  // Fill an inclusive box (world voxel coords).
  fillBox(x0, y0, z0, x1, y1, z1, v) {
    for (let z = z0; z <= z1; z++)
      for (let y = y0; y <= y1; y++)
        for (let x = x0; x <= x1; x++) this.set(x, y, z, v);
  }

  forEachChunk(cb) {
    for (const [key, data] of this.chunks) {
      const [cx, cy, cz] = unpackKey(key);
      cb(data, cx, cy, cz, key);
    }
  }

  get chunkCount() {
    return this.chunks.size;
  }

  voxelCount() {
    let n = 0;
    for (const c of this.chunks.values()) for (let i = 0; i < c.length; i++) if (c[i]) n++;
    return n;
  }

  // Drop chunks that are entirely air.
  prune() {
    for (const [key, c] of this.chunks) {
      let empty = true;
      for (let i = 0; i < c.length; i++) if (c[i]) { empty = false; break; }
      if (empty) this.chunks.delete(key);
    }
  }

  // World-voxel bounds of all non-empty chunks (inclusive min, exclusive max).
  bounds() {
    if (!this.chunks.size) return null;
    let min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    this.forEachChunk((_, cx, cy, cz) => {
      min = [Math.min(min[0], cx), Math.min(min[1], cy), Math.min(min[2], cz)];
      max = [Math.max(max[0], cx + 1), Math.max(max[1], cy + 1), Math.max(max[2], cz + 1)];
    });
    return { min: min.map(v => v * CHUNK), max: max.map(v => v * CHUNK) };
  }

  // Chunk data plus a 1-voxel apron from neighbors, laid out APRON³ with
  // index (lx+1) + (ly+1)*APRON + (lz+1)*APRON². What the mesher consumes.
  extractWithApron(cx, cy, cz) {
    const out = new Uint8Array(APRON * APRON * APRON);
    const bx = cx << CHUNK_BITS, by = cy << CHUNK_BITS, bz = cz << CHUNK_BITS;
    // Fast path for the interior from the chunk itself, then borders via get().
    const c = this.getChunk(cx, cy, cz);
    if (c) {
      for (let lz = 0; lz < CHUNK; lz++)
        for (let ly = 0; ly < CHUNK; ly++) {
          const src = voxelIndex(0, ly, lz);
          const dst = 1 + (ly + 1) * APRON + (lz + 1) * APRON * APRON;
          out.set(c.subarray(src, src + CHUNK), dst);
        }
    }
    for (let lz = -1; lz <= CHUNK; lz++)
      for (let ly = -1; ly <= CHUNK; ly++)
        for (let lx = -1; lx <= CHUNK; lx++) {
          const border = lx < 0 || ly < 0 || lz < 0 || lx >= CHUNK || ly >= CHUNK || lz >= CHUNK;
          if (!border) continue;
          out[(lx + 1) + (ly + 1) * APRON + (lz + 1) * APRON * APRON] = this.get(bx + lx, by + ly, bz + lz);
        }
    return out;
  }
}
