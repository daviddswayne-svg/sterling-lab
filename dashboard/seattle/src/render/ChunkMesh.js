import * as THREE from 'three';

// Turn one mesher output (opaque or glass buffers) into a BufferGeometry.
export function buildGeometry(buf) {
  if (!buf.indices.length) return null;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(buf.positions, 3));
  geo.setAttribute('normal', new THREE.BufferAttribute(buf.normals, 3, true));
  geo.setAttribute('palette', new THREE.BufferAttribute(buf.palette, 1, false));
  geo.setAttribute('ao', new THREE.BufferAttribute(buf.ao, 1, false));
  geo.setIndex(new THREE.BufferAttribute(buf.indices, 1));
  geo.computeBoundingSphere();
  geo.computeBoundingBox();
  return geo;
}

// Concatenate several mesher buffer sets into one (same layout).
export function mergeBuffers(list) {
  const parts = list.filter((b) => b.indices.length);
  if (!parts.length) return { positions: new Float32Array(0), normals: new Int8Array(0), palette: new Uint8Array(0), ao: new Uint8Array(0), indices: new Uint32Array(0) };
  const sum = (k) => parts.reduce((n, b) => n + b[k].length, 0);
  const out = {
    positions: new Float32Array(sum('positions')), normals: new Int8Array(sum('normals')),
    palette: new Uint8Array(sum('palette')), ao: new Uint8Array(sum('ao')), indices: new Uint32Array(sum('indices')),
  };
  let v = 0, o = { positions: 0, normals: 0, palette: 0, ao: 0, indices: 0 };
  for (const b of parts) {
    for (const k of ['positions', 'normals', 'palette', 'ao']) { out[k].set(b[k], o[k]); o[k] += b[k].length; }
    for (let i = 0; i < b.indices.length; i++) out.indices[o.indices + i] = b.indices[i] + v;
    o.indices += b.indices.length;
    v += b.positions.length / 3;
  }
  return out;
}

// A chunk's renderable pair. Either mesh may be null.
export function buildChunkMeshes(result, materials) {
  const out = { opaque: null, glass: null, triangles: 0 };
  const og = buildGeometry(result.opaque);
  if (og) {
    out.opaque = new THREE.Mesh(og, materials.opaque);
    out.opaque.castShadow = true;
    out.opaque.receiveShadow = true;
    out.triangles += og.index.count / 3;
  }
  const gg = buildGeometry(result.glass);
  if (gg) {
    out.glass = new THREE.Mesh(gg, materials.glass);
    out.glass.receiveShadow = true;
    out.glass.renderOrder = 10;
    out.triangles += gg.index.count / 3;
  }
  return out;
}
