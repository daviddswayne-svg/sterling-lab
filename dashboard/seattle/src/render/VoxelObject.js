// Dynamic voxel objects: a small Grid meshed once (all chunks merged) into a
// Group of opaque + glass meshes using the shared palette materials, then moved
// as a rigid body. Same mesher and materials as the static world.
import * as THREE from 'three';
import { meshChunk } from '../voxel/Mesher.js';
import { CHUNK, unpackKey } from '../voxel/Grid.js';
import { mergeBuffers, buildChunkMeshes } from './ChunkMesh.js';

/**
 * @param {Grid} grid   voxels in object-local coords; local (0,0,0) becomes the pivot
 * @param {Uint8Array} flags   palette flags
 * @param {number} voxelSize   world units per voxel
 * @param {{opaque, glass}} materials  from app.materialsFor(voxelSize)
 */
export function meshGrid(grid, flags, voxelSize, materials) {
  const parts = [];
  for (const key of grid.chunks.keys()) {
    const [cx, cy, cz] = unpackKey(key);
    parts.push(meshChunk(grid.extractWithApron(cx, cy, cz), flags, [cx * CHUNK, cy * CHUNK, cz * CHUNK], voxelSize));
  }
  const merged = { opaque: mergeBuffers(parts.map((p) => p.opaque)), glass: mergeBuffers(parts.map((p) => p.glass)) };
  const meshes = buildChunkMeshes(merged, materials);
  const group = new THREE.Group();
  if (meshes.opaque) { meshes.opaque.castShadow = true; group.add(meshes.opaque); }
  if (meshes.glass) group.add(meshes.glass);
  group.userData.triangles = meshes.triangles;
  return group;
}
