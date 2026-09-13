// world.bin: voxels, not meshes. Tiny on disk, meshed in workers on load.
//
//   'SVX1'  u16 version  f32 voxelSize  u32 bodyLength  [palette 2048 bytes]
//   deflate-raw( per chunk: i32 key, u32 runCount, runCount × (u8 idx, u16 run) )
//
// Uses the web CompressionStream API, available in browsers and Node 18+.

import { Grid, CHUNK_VOLUME } from './Grid.js';
import { Palette, BYTES_PER_ENTRY } from './Palette.js';

const MAGIC = 0x31585653; // 'SVX1' little-endian
const VERSION = 1;
const HEADER = 4 + 2 + 4 + 4;
const PALETTE_BYTES = 256 * BYTES_PER_ENTRY;

async function pipe(bytes, stream) {
  const res = new Response(new Blob([bytes]).stream().pipeThrough(stream));
  return new Uint8Array(await res.arrayBuffer());
}

export async function encodeWorld(grid, palette, voxelSize) {
  grid.prune();
  // RLE every chunk
  const parts = [];
  let total = 0;
  grid.forEachChunk((data, cx, cy, cz, key) => {
    const runs = [];
    let cur = data[0], run = 0;
    for (let i = 0; i < CHUNK_VOLUME; i++) {
      if (data[i] === cur && run < 65535) run++;
      else { runs.push(cur, run); cur = data[i]; run = 1; }
    }
    runs.push(cur, run);
    const buf = new Uint8Array(8 + (runs.length / 2) * 3);
    const dv = new DataView(buf.buffer);
    dv.setInt32(0, key, true);
    dv.setUint32(4, runs.length / 2, true);
    for (let i = 0, o = 8; i < runs.length; i += 2, o += 3) {
      buf[o] = runs[i];
      dv.setUint16(o + 1, runs[i + 1], true);
    }
    parts.push(buf);
    total += buf.length;
  });
  const body = new Uint8Array(total);
  let o = 0;
  for (const p of parts) { body.set(p, o); o += p.length; }
  const packed = await pipe(body, new CompressionStream('deflate-raw'));

  const out = new Uint8Array(HEADER + PALETTE_BYTES + packed.length);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, MAGIC, true);
  dv.setUint16(4, VERSION, true);
  dv.setFloat32(6, voxelSize, true);
  dv.setUint32(10, packed.length, true);
  out.set(palette.toBytes(), HEADER);
  out.set(packed, HEADER + PALETTE_BYTES);
  return out;
}

export async function decodeWorld(bytes) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (dv.getUint32(0, true) !== MAGIC) throw new Error('not a SVX1 world file');
  const version = dv.getUint16(4, true);
  if (version !== VERSION) throw new Error(`unsupported world version ${version}`);
  const voxelSize = dv.getFloat32(6, true);
  const packedLen = dv.getUint32(10, true);
  const palette = Palette.fromBytes(bytes.subarray(HEADER, HEADER + PALETTE_BYTES));
  const packed = bytes.subarray(HEADER + PALETTE_BYTES, HEADER + PALETTE_BYTES + packedLen);
  const body = await pipe(packed, new DecompressionStream('deflate-raw'));
  const bdv = new DataView(body.buffer, body.byteOffset, body.byteLength);

  const grid = new Grid();
  let o = 0;
  while (o < body.length) {
    const key = bdv.getInt32(o, true);
    const runCount = bdv.getUint32(o + 4, true);
    o += 8;
    const data = new Uint8Array(CHUNK_VOLUME);
    let i = 0;
    for (let r = 0; r < runCount; r++, o += 3) {
      const idx = body[o];
      const run = bdv.getUint16(o + 1, true);
      if (idx !== 0) data.fill(idx, i, i + run);
      i += run;
    }
    grid.chunks.set(key, data);
  }
  return { grid, palette, voxelSize };
}
