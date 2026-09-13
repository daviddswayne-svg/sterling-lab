// Assembles the world: STL landmarks + procedural pieces + any models/*.vox
// listed in site.json → ../dashboard/seattle/world.bin
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { Grid } from '../dashboard/seattle/src/voxel/Grid.js';
import { defaultPalette } from '../dashboard/seattle/src/voxel/Palette.js';
import { encodeWorld } from '../dashboard/seattle/src/voxel/WorldFormat.js';
import { readVox, stampVox } from '../dashboard/seattle/src/voxel/Vox.js';
import { parseStl, voxelizeStl, stampVoxels } from '../dashboard/seattle/src/voxel/Stl.js';
import { buildNeedle } from '../dashboard/seattle/src/gen/needle.js';
import { buildTrain, buildBeam } from '../dashboard/seattle/src/gen/monorail.js';
import { cylinderY, rasterize, aabbAround } from '../dashboard/seattle/src/voxel/Shapes.js';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = join(here, '../dashboard/seattle/world.bin');
const STL_DIR = process.env.STL_DIR || join(process.env.HOME, 'voxel_archive/voxel_project');
const VOXEL_SIZE = 0.5; // metres
const NEEDLE_SOURCE = process.env.NEEDLE || 'stl'; // 'stl' | 'procedural'

const t0 = performance.now();
const grid = new Grid();
const pal = defaultPalette();
const P = (n) => pal.index(n);
const timed = (label, fn) => {
  const t = performance.now();
  const r = fn();
  console.log(`${label.padEnd(14)} ${(performance.now() - t).toFixed(0).padStart(6)} ms`, typeof r === 'string' ? r : '');
  return r;
};

// Ground: 512×512 voxel grass slab (256 m square) centred on the origin.
timed('ground', () => {
  const g = P('grass'), gd = P('grass_dark');
  for (let z = -256; z < 256; z++)
    for (let x = -256; x < 256; x++)
      grid.set(x, -1, z, ((x * 7 + z * 13) % 11 === 0) ? gd : g);
  return `${grid.voxelCount()} voxels`;
});

// Plaza under the Needle
timed('plaza', () => rasterize(grid, cylinderY(0, 0, 60, -1, 0), aabbAround(0, 0, 61, -1, 0), P('pavement')) + ' voxels');

// --- Space Needle ---
const NEEDLE_H = 368; // 184 m at 0.5 m/voxel
if (NEEDLE_SOURCE === 'stl') {
  const model = timed('needle stl', () => voxelizeStl(parseStl(readFileSync(join(STL_DIR, 'SpaceNeedle.stl'))), { height: NEEDLE_H }));
  console.log(`               size ${model.size.join('×')}  solid ${model.count}`);
  // Height bands from the real Needle (fractions of 605 ft):
  //   Loupe glass 500–520 ft, deck 520–540, gold brim ~540–550, dome to ~575, spire above.
  timed('needle', () => stampVoxels(grid, model, [0, 0, 0], (x, y, z, { h, r }) => {
    if (h > 0.985) return P('beacon_red');
    if (h > 0.95) return P('needle_steel');            // spire
    if (h > 0.905) return P('needle_white');           // dome
    if (h > 0.885) return P('needle_gold');            // brim / halo
    if (h > 0.86) return r > 40 ? P('needle_glass') : P('needle_white');   // deck barrier
    if (h > 0.83) return r > 36 ? P('needle_glass') : P('needle_white');   // Loupe windows
    if (h > 0.78) return P('needle_white');            // soffit
    if (r < 7) return P('needle_core');
    if (h < 0.035 && r > 20) return P('needle_glass'); // ground pavilion
    return P('needle_white');
  }) + ' voxels');
} else {
  timed('needle', () => Object.values(buildNeedle(grid, pal, 0, 0, 0)).reduce((a, b) => a + b, 0) + ' voxels');
}

// --- Monorail: two beams east of the plaza, Red and Blue trains (static style
// preview; they become moving objects with stations in Milestone B) ---
{
  const beamTop = 18; // ~30 ft up
  timed('beams', () => buildBeam(grid, pal, -20, 230, beamTop, 84) + buildBeam(grid, pal, -20, 230, beamTop, 96) + ' voxels');
  timed('red train', () => buildTrain(grid, pal, [80, beamTop, 84], { color: 'monorail_red' }) + ' voxels');
  timed('blue train', () => buildTrain(grid, pal, [160, beamTop, 96], { color: 'monorail_blue' }) + ' voxels');
}

// Optional hand-made models: site.json = [{ "file": "foo.vox", "at": [x, y, z] }]
const siteFile = join(here, 'site.json');
if (existsSync(siteFile)) {
  const site = JSON.parse(readFileSync(siteFile, 'utf8'));
  for (const item of site) {
    timed(item.file, () => {
      const vox = readVox(readFileSync(join(here, 'models', item.file)));
      const nearest = (rgba) => {
        let best = 0, bd = Infinity;
        pal.entries.forEach((e, i) => {
          if (i === 0 || !e.name) return;
          const d = (e.r - rgba[0]) ** 2 + (e.g - rgba[1]) ** 2 + (e.b - rgba[2]) ** 2;
          if (d < bd) { bd = d; best = i; }
        });
        return best;
      };
      return stampVox(vox, grid, item.at, nearest) + ' voxels';
    });
  }
}

grid.prune();
const bytes = await encodeWorld(grid, pal, VOXEL_SIZE);
writeFileSync(OUT, bytes);
console.log(`\nchunks ${grid.chunkCount}  voxels ${grid.voxelCount()}  world.bin ${(bytes.length / 1024).toFixed(1)} KB  total ${(performance.now() - t0).toFixed(0)} ms`);
