// Greedy mesher with baked ambient occlusion for one 32³ chunk.
// Input is the chunk plus a 1-voxel apron (see Grid.extractWithApron) so
// faces on chunk borders are culled against neighbors and AO is seamless.
//
// Output: { opaque: MeshBuffers, glass: MeshBuffers, stats }
//   MeshBuffers = { positions: Float32Array (world units), normals: Int8Array,
//                   palette: Uint8Array, ao: Uint8Array (0..3), indices: Uint32Array }
//
// Faces merge only when palette index AND the 4 corner AO values match, so a
// merged rectangle is lit exactly like its individual voxels would be.

import { CHUNK, APRON } from './Grid.js';
import { FLAG_GLASS } from './Palette.js';

const A2 = APRON * APRON;

class Builder {
  constructor() {
    this.pos = []; this.nrm = []; this.pal = []; this.ao = []; this.idx = [];
    this.quads = 0;
  }
  quad(corners, normal, palIdx, aoCorners, flip) {
    const base = this.pos.length / 3;
    for (let i = 0; i < 4; i++) {
      const c = corners[i];
      this.pos.push(c[0], c[1], c[2]);
      this.nrm.push(normal[0], normal[1], normal[2]);
      this.pal.push(palIdx);
      this.ao.push(aoCorners[i]);
    }
    // Two triangles; choose the diagonal that keeps AO gradients smooth.
    const useAlt = aoCorners[0] + aoCorners[2] > aoCorners[1] + aoCorners[3];
    if (flip) {
      if (useAlt) this.idx.push(base + 1, base, base + 3, base + 1, base + 3, base + 2);
      else this.idx.push(base, base + 3, base + 2, base, base + 2, base + 1);
    } else {
      if (useAlt) this.idx.push(base + 1, base + 2, base + 3, base + 1, base + 3, base);
      else this.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
    this.quads++;
  }
  finish() {
    return {
      positions: new Float32Array(this.pos),
      normals: new Int8Array(this.nrm),
      palette: new Uint8Array(this.pal),
      ao: new Uint8Array(this.ao),
      indices: new Uint32Array(this.idx),
    };
  }
}

/**
 * @param {Uint8Array} apron  APRON³ palette indices
 * @param {Uint8Array} flags  256 palette flags
 * @param {number[]} origin   world voxel coords of the chunk's (0,0,0)
 * @param {number} voxelSize  world units per voxel
 */
export function meshChunk(apron, flags, origin, voxelSize) {
  const opaque = new Builder();
  const glass = new Builder();

  const at = (x, y, z) => apron[(x + 1) + (y + 1) * APRON + (z + 1) * A2];
  const isGlass = (v) => (flags[v] & FLAG_GLASS) !== 0;
  const isOpaque = (v) => v !== 0 && !isGlass(v);

  const mask = new Int32Array(CHUNK * CHUNK);
  const x = [0, 0, 0];
  const q = [0, 0, 0];

  for (let d = 0; d < 3; d++) {
    const u = (d + 1) % 3, v = (d + 2) % 3;
    q[0] = q[1] = q[2] = 0; q[d] = 1;
    const normalPos = [0, 0, 0]; normalPos[d] = 1;
    const normalNeg = [0, 0, 0]; normalNeg[d] = -1;

    // Slice between x[d] and x[d]+1, for x[d] in [-1, CHUNK-1]
    for (x[d] = -1; x[d] < CHUNK; x[d]++) {
      let n = 0;
      for (x[v] = 0; x[v] < CHUNK; x[v]++) {
        for (x[u] = 0; x[u] < CHUNK; x[u]++, n++) {
          const a = at(x[0], x[1], x[2]);
          const b = at(x[0] + q[0], x[1] + q[1], x[2] + q[2]);
          let val = 0;
          // Front face of a (normal +d): a visible against b
          if (x[d] >= 0 && a !== 0) {
            if (isOpaque(a) ? !isOpaque(b) : b === 0) {
              val = encode(a, aoFor(x[0], x[1], x[2], d, 1, u, v), 0, isGlass(a));
            }
          }
          // Back face of b (normal -d): b visible against a
          if (val === 0 && x[d] + 1 < CHUNK && b !== 0) {
            if (isOpaque(b) ? !isOpaque(a) : a === 0) {
              const bx = x[0] + q[0], by = x[1] + q[1], bz = x[2] + q[2];
              val = encode(b, aoFor(bx, by, bz, d, -1, u, v), 1, isGlass(b));
            }
          }
          mask[n] = val;
        }
      }

      // Greedy merge over the mask
      n = 0;
      for (let j = 0; j < CHUNK; j++) {
        for (let i = 0; i < CHUNK;) {
          const c = mask[n];
          if (c === 0) { i++; n++; continue; }
          let w = 1;
          while (i + w < CHUNK && mask[n + w] === c) w++;
          let h = 1;
          outer: for (; j + h < CHUNK; h++) {
            for (let k = 0; k < w; k++) if (mask[n + k + h * CHUNK] !== c) break outer;
          }

          const back = (c >> 1) & 1;
          const gl = c & 1;
          const palIdx = (c >>> 12) & 255;
          const aoPacked = (c >>> 4) & 255;
          const aoC = [aoPacked & 3, (aoPacked >> 2) & 3, (aoPacked >> 4) & 3, (aoPacked >> 6) & 3];

          x[u] = i; x[v] = j;
          const p = [x[0], x[1], x[2]];
          p[d] += 1; // the face plane sits at x[d]+1 for both front-of-a and back-of-b
          const du = [0, 0, 0]; du[u] = w;
          const dv = [0, 0, 0]; dv[v] = h;
          const s = voxelSize;
          const c0 = [(origin[0] + p[0]) * s, (origin[1] + p[1]) * s, (origin[2] + p[2]) * s];
          const c1 = [c0[0] + du[0] * s, c0[1] + du[1] * s, c0[2] + du[2] * s];
          const c2 = [c1[0] + dv[0] * s, c1[1] + dv[1] * s, c1[2] + dv[2] * s];
          const c3 = [c0[0] + dv[0] * s, c0[1] + dv[1] * s, c0[2] + dv[2] * s];

          (gl ? glass : opaque).quad([c0, c1, c2, c3], back ? normalNeg : normalPos, palIdx, aoC, back === 1);

          for (let l = 0; l < h; l++) for (let k = 0; k < w; k++) mask[n + k + l * CHUNK] = 0;
          i += w; n += w;
        }
      }
    }
  }

  // AO for the 4 corners of the face of voxel (vx,vy,vz) with normal sign `sgn` on axis d.
  // Corner order matches quad corners: (0,0) (u+,0) (u+,v+) (0,v+) in (u,v) space.
  function aoFor(vx, vy, vz, d, sgn, u, v) {
    const p = [vx, vy, vz]; p[d] += sgn; // the cell in front of the face
    const solid = (du, dv) => {
      const c = [p[0], p[1], p[2]]; c[u] += du; c[v] += dv;
      return isOpaque(at(c[0], c[1], c[2])) ? 1 : 0;
    };
    const corner = (su, sv) => {
      const s1 = solid(su, 0), s2 = solid(0, sv);
      if (s1 && s2) return 0;
      return 3 - (s1 + s2 + solid(su, sv));
    };
    return corner(-1, -1) | (corner(1, -1) << 2) | (corner(1, 1) << 4) | (corner(-1, 1) << 6);
  }

  const o = opaque.finish(), g = glass.finish();
  return {
    opaque: o,
    glass: g,
    stats: { quads: opaque.quads + glass.quads, vertices: o.positions.length / 3 + g.positions.length / 3 },
  };
}

function encode(palIdx, aoPacked, back, glass) {
  return (palIdx << 12) | (aoPacked << 4) | (back << 1) | (glass ? 1 : 0);
}
