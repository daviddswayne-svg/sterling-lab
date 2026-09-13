// Seattle Center Monorail station: a centre platform between the two beams,
// canopy, columns, a terminal kiosk and stairs down to the plaza. Plus the
// short Westlake stub platform at the south end. Environment layer (0.5 m).
import { STATION, BEAM_TOP, BEAM_SEPARATION } from '../site/layout.js';

export function buildStation(grid, pal, route) {
  const pave = pal.index('pavement'), conc = pal.index('concrete'), dark = pal.index('concrete_dark');
  const white = pal.index('white'), glass = pal.index('glass_clear'), steel = pal.index('needle_steel');
  let n = 0;
  const set = (x, y, z, v) => { grid.set(Math.round(x), y, Math.round(z), v); n++; };
  const half = BEAM_SEPARATION / 2 - 3; // platform half-width: stops 1 voxel short of each beam
  const platTop = BEAM_TOP + 2;         // platform surface = train floor level

  const sStart = route.nearest(0, STATION.zStart), sEnd = route.nearest(0, STATION.zEnd);
  for (let s = Math.min(sStart, sEnd); s <= Math.max(sStart, sEnd); s += 0.5) {
    const p = route.pointAt(s), t = route.tangentAt(s);
    const nx = t.z, nz = -t.x;
    // slab
    for (let o = -half; o <= half; o += 0.5)
      for (let y = platTop - 1; y <= platTop; y++) set(p.x + nx * o, y, p.z + nz * o, o === -half || o === half ? white : pave);
    // canopy: thin roof 6 m above the platform with a centre-line column every 10 m
    for (let o = -half - 2; o <= half + 2; o += 0.5) set(p.x + nx * o, platTop + 12, p.z + nz * o, white);
    if (Math.round(s * 2) % 40 === 0) {
      for (let y = platTop + 1; y < platTop + 12; y++) set(p.x, y, p.z, steel);
      for (let y = 0; y < platTop - 1; y++) for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) set(p.x + dx, y, p.z + dz, dark);
    }
  }
  // terminal kiosk at the north end, stairs at the south end
  const north = route.pointAt(Math.min(sStart, sEnd) + 6), south = route.pointAt(Math.max(sStart, sEnd) - 4);
  for (let dx = -3; dx <= 3; dx++) for (let dz = -6; dz <= 6; dz++) for (let y = platTop + 1; y <= platTop + 6; y++)
    set(north.x + dx, y, north.z + dz, (Math.abs(dx) === 3 || Math.abs(dz) === 6) && y > platTop + 2 && y < platTop + 6 ? glass : conc);
  // stairs: descend westward from the platform edge to the ground, 4 wide
  for (let i = 0; i <= platTop; i++) {
    const y = platTop - i;
    for (let dz = -2; dz <= 1; dz++) for (let k = 0; k < 2; k++) set(south.x - half - 1 - i * 2 - k, y, south.z + dz, conc);
  }
  return n;
}

/** Westlake stub: a short platform and buffer at the south end of the route. */
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
  // buffer stops on both beams
  for (const off of [-BEAM_SEPARATION / 2, BEAM_SEPARATION / 2]) {
    const p = route.pointAt(route.length - 1), t = route.tangentAt(route.length - 1);
    for (let y = BEAM_TOP + 1; y <= BEAM_TOP + 3; y++) for (let o = -1; o <= 1; o++) set(p.x + t.z * (off + o), y, p.z - t.x * (off + o), red);
  }
  return n;
}
