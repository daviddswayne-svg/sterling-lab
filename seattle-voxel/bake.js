// Assembles two world layers:
//   world.bin  — environment at 0.5 m (lawn, plazas, beams, blockouts)
//   detail.bin — hero objects at 0.25 m (Space Needle, trains, …)
// plus any models/*.vox listed in site.json → ../dashboard/seattle/
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { Grid } from '../dashboard/seattle/src/voxel/Grid.js';
import { defaultPalette } from '../dashboard/seattle/src/voxel/Palette.js';
import { encodeWorld } from '../dashboard/seattle/src/voxel/WorldFormat.js';
import { readVox, stampVox } from '../dashboard/seattle/src/voxel/Vox.js';
import { parseStl, voxelizeStl, stampVoxels } from '../dashboard/seattle/src/voxel/Stl.js';
import { buildNeedle } from '../dashboard/seattle/src/gen/needle.js';
import { buildTrain } from '../dashboard/seattle/src/gen/monorail.js';
import { buildBeam, carveCorridor } from '../dashboard/seattle/src/gen/beam.js';
import { buildBlockout } from '../dashboard/seattle/src/gen/blockout.js';
import { buildStation, buildWestlakeStub } from '../dashboard/seattle/src/gen/station.js';
import { TRAIN_LEN, VOXEL as HERO_V } from '../dashboard/seattle/src/gen/monorail.js';
import { WORLD, byId, STATION, BEAM_TOP } from '../dashboard/seattle/src/site/layout.js';
import { ROUTE } from '../dashboard/seattle/src/site/route.js';
import { cylinderY, rasterize, aabbAround } from '../dashboard/seattle/src/voxel/Shapes.js';

const here = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(here, '../dashboard/seattle');
const STL_DIR = process.env.STL_DIR || join(process.env.HOME, 'voxel_archive/voxel_project');
const ENV = 0.5, HERO = 0.25;              // metres per voxel, per layer
const NEEDLE_SOURCE = process.env.NEEDLE || 'stl';

const t0 = performance.now();
const world = new Grid();   // 0.5 m
const detail = new Grid();  // 0.25 m
const pal = defaultPalette();
const P = (n) => pal.index(n);
const timed = (label, fn) => {
  const t = performance.now();
  const r = fn();
  console.log(`${label.padEnd(14)} ${(performance.now() - t).toFixed(0).padStart(6)} ms`, typeof r === 'string' ? r : '');
  return r;
};
const H = (m) => Math.round(m / HERO); // metres → hero voxels

// ---------------- environment layer (0.5 m) ----------------
timed('ground', () => {
  // One flat colour: the shader's per-voxel grain gives the texture, and a
  // speckle pattern here would shatter greedy meshing into millions of quads.
  const g = P('grass');
  for (let z = WORLD.z0; z < WORLD.z1; z++)
    for (let x = WORLD.x0; x < WORLD.x1; x++) world.set(x, -1, z, g);
  return `${world.voxelCount()} voxels`;
});
timed('plaza', () => rasterize(world, cylinderY(0, 0, 60, -1, 0), aabbAround(0, 0, 61, -1, 0), P('pavement')) + ' voxels');

timed('blockout', () => {
  const s = buildBlockout(world, pal);
  return Object.entries(s).map(([k, v]) => `${k}:${v}`).join(' ');
});

// Monorail: carve the corridor through MoPOP's block, then sweep both beams.
timed('corridor', () => carveCorridor(world, ROUTE.centre, { halfWidth: 16, floor: -2, ceiling: 20 }) + ' voxels carved');
timed('beams', () => {
  const skip = (p) => p.z > STATION.zStart && p.z < STATION.zEnd; // station has its own structure
  return buildBeam(world, pal, ROUTE.red, { pierSkip: skip }) + buildBeam(world, pal, ROUTE.blue, { pierSkip: skip }) + ' voxels';
});
timed('station', () => buildStation(world, pal, ROUTE.centre) + buildWestlakeStub(world, pal, ROUTE.centre, (TRAIN_LEN / 2) * HERO_V / ENV) + ' voxels');

// ---------------- hero layer (0.25 m) ----------------
const NEEDLE_H = H(184); // 184 m → 736 voxels
if (NEEDLE_SOURCE === 'stl') {
  const model = timed('needle stl', () => voxelizeStl(parseStl(readFileSync(join(STL_DIR, 'SpaceNeedle.stl'))), { height: NEEDLE_H }));
  console.log(`               size ${model.size.join('×')}  solid ${model.count}`);
  timed('needle', () => stampVoxels(detail, model, [0, 0, 0], (x, y, z, { h, r }) => {
    if (h > 0.985) return P('beacon_red');
    if (h > 0.95) return P('needle_steel');
    if (h > 0.905) return P('needle_white');
    if (h > 0.885) return P('needle_gold');
    if (h > 0.86) return r > 80 ? P('needle_glass') : P('needle_white');
    if (h > 0.83) return r > 72 ? P('needle_glass') : P('needle_white');
    if (h > 0.78) return P('needle_white');
    if (r < 14) return P('needle_core');
    if (h < 0.035 && r > 40) return P('needle_glass');
    return P('needle_white');
  }) + ' voxels');
} else {
  timed('needle', () => Object.values(buildNeedle(world, pal, 0, 0, 0)).reduce((a, b) => a + b, 0) + ' voxels');
}

// Trains are dynamic objects built at runtime (src/sim/Train.js) — nothing static here.

// Optional hand-made models: site.json = [{ "file": "foo.vox", "at": [x, y, z], "layer": "detail" }]
const siteFile = join(here, 'site.json');
if (existsSync(siteFile)) {
  for (const item of JSON.parse(readFileSync(siteFile, 'utf8'))) {
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
      return stampVox(vox, item.layer === 'detail' ? detail : world, item.at, nearest) + ' voxels';
    });
  }
}

for (const [name, grid, size] of [['world.bin', world, ENV], ['detail.bin', detail, HERO]]) {
  grid.prune();
  const bytes = await encodeWorld(grid, pal, size);
  writeFileSync(join(OUT_DIR, name), bytes);
  console.log(`${name.padEnd(11)} chunks ${String(grid.chunkCount).padStart(4)}  voxels ${String(grid.voxelCount()).padStart(8)}  ${(bytes.length / 1024).toFixed(1)} KB`);
}
console.log(`total ${(performance.now() - t0).toFixed(0)} ms`);
