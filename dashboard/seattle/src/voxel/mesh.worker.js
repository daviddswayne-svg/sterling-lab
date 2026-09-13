// Module worker: meshes one chunk per message and transfers the buffers back.
import { meshChunk } from './Mesher.js';

self.onmessage = (e) => {
  const { id, apron, flags, origin, voxelSize } = e.data;
  const result = meshChunk(apron, flags, origin, voxelSize);
  const transfer = [];
  for (const part of [result.opaque, result.glass])
    for (const k of Object.keys(part)) transfer.push(part[k].buffer);
  self.postMessage({ id, ...result }, transfer);
};
