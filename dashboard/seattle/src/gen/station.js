// Seattle Center Monorail station: a centre platform between the two beams
// over the first STATION.s1 voxels of the route (s = 0 at the bumper on the
// Needle side), with a canopy, columns, a kiosk at the inner end and stairs
// down at the Needle end. Plus the short Westlake stub at the far end.
// Environment layer (0.5 m).
import { STATION, BEAM_TOP, BEAM_SEPARATION } from '../site/layout.js';

export function buildStation(grid, pal, route) {
  const pave = pal.index('pavement'), conc = pal.index('concrete'), dark = pal.index('concrete_dark');
  const white = pal.index('white'), glass = pal.index('glass_clear'), steel = pal.index('needle_steel'), red = pal.index('monorail_red');
  let n = 0;
  const set = (x, y, z, v) => { grid.set(Math.round(x), y, Math.round(z), v); n++; };
  const half = BEAM_SEPARATION / 2 - 3; // platform half-width: stops 1 voxel short of each beam
  const platTop = BEAM_TOP + 2;         // platform surface = train floor level

  for (let s = STATION.s0; s <= STATION.s1; s += 0.5) {
    const p = route.pointAt(s), t = route.tangentAt(s);
    const nx = t.z, nz = -t.x;
    for (let o = -half; o <= half; o += 0.5)
      for (let y = platTop - 1; y <= platTop; y++) set(p.x + nx * o, y, p.z + nz * o, o === -half || o === half ? white : pave);
    for (let o = -half - 2; o <= half + 2; o += 0.5) set(p.x + nx * o, platTop + 12, p.z + nz * o, white); // canopy
    if (Math.round(s * 2) % 40 === 0) {
      for (let y = platTop + 1; y < platTop + 12; y++) set(p.x, y, p.z, steel);
      for (let y = 0; y < platTop - 1; y++) for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) set(p.x + dx, y, p.z + dz, dark);
    }
  }
  // kiosk at the inner (east) end
  const inner = route.pointAt(STATION.s1 - 8);
  for (let dx = -6; dx <= 6; dx++) for (let dz = -3; dz <= 3; dz++) for (let y = platTop + 1; y <= platTop + 6; y++)
    set(inner.x + dx, y, inner.z + dz, (Math.abs(dx) === 6 || Math.abs(dz) === 3) && y > platTop + 2 && y < platTop + 6 ? glass : conc);
  // stairs at the bumper end, descending west toward the Needle, 4 wide
  const end = route.pointAt(STATION.s0), t0 = route.tangentAt(STATION.s0);
  for (let i = 0; i <= platTop; i++) {
    const y = platTop - i;
    for (let w = -2; w <= 1; w++) for (let k = 0; k < 2; k++)
      set(end.x - t0.x * (2 + i * 2 + k) + t0.z * w, y, end.z - t0.z * (2 + i * 2 + k) - t0.x * w, conc);
  }
  // buffer stops on both beams at the bumper
  for (const off of [-BEAM_SEPARATION / 2, BEAM_SEPARATION / 2])
    for (let y = BEAM_TOP + 1; y <= BEAM_TOP + 3; y++) for (let o = -1; o <= 1; o++) set(end.x + t0.z * (off + o), y, end.z - t0.x * (off + o), red);
  return n;
}

/** Westlake stub: a short platform and buffers at the far end of the route. */
export function buildWestlakeStub(grid, pal, route, trainHalfLen) {
  const pave = pal.index('pavement'), white = pal.index('white'), red = pal.index('monorail_red'), dark = pal.index('concrete_dark');
  let n = 0;
  const set = (x, y, z, v) => { grid.set(Math.round(x), y, Math.round(z), v); n++; };
  const half = BEAM_SEPARATION / 2 - 3, platTop = BEAM_TOP + 2;
  const sEnd = route.length - 4, sStart = sEnd - trainHalfLen * 2 - 8;
  for (let s = sStart; s <= sEnd; s += 0.5) {
    const p = route.pointAt(s), t = route.tangentAt(s);
    const nx = t.z, nz = -t.x;
    for (let o = -half; o <= half; o += 0.5)
      for (let y = platTop - 1; y <= platTop; y++) set(p.x + nx * o, y, p.z + nz * o, o === -half || o === half ? white : pave);
    if (Math.round(s * 2) % 40 === 0) for (let y = 0; y < platTop - 1; y++) set(p.x, y, p.z, dark);
  }
  for (const off of [-BEAM_SEPARATION / 2, BEAM_SEPARATION / 2]) {
    const p = route.pointAt(route.length - 1), t = route.tangentAt(route.length - 1);
    for (let y = BEAM_TOP + 1; y <= BEAM_TOP + 3; y++) for (let o = -1; o <= 1; o++) set(p.x + t.z * (off + o), y, p.z - t.x * (off + o), red);
  }
  return n;
}
