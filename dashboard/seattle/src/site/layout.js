// The site in one table. Every landmark is placed from lat/lon so a wrong
// position is a one-number fix. Frame: Space Needle base = origin, +x east,
// -z north, environment voxel = 0.5 m. Footprints are metres; rot is degrees
// clockwise from north for the footprint's long (d) axis.

export const ORIGIN = { lat: 47.62050, lon: -122.34930 }; // Space Needle
export const ENV_VOXEL = 0.5;
const M_PER_LAT = 111320;
const M_PER_LON = 111320 * Math.cos((ORIGIN.lat * Math.PI) / 180); // ≈ 75,000

/** lat/lon → metres east/north of the origin */
export function toMetres(lat, lon) {
  return { x: (lon - ORIGIN.lon) * M_PER_LON, z: -(lat - ORIGIN.lat) * M_PER_LAT };
}
/** lat/lon → environment voxel coords (0.5 m) */
export function toVoxel(lat, lon) {
  const m = toMetres(lat, lon);
  return { x: Math.round(m.x / ENV_VOXEL), z: Math.round(m.z / ENV_VOXEL) };
}

// World extents in environment voxels (x east, z south)
export const WORLD = { x0: -900, x1: 520, z0: -760, z1: 640 };

// kind: 'box' (gray block), 'ring' (fountain bowl), 'hero' (built elsewhere), 'stub'
export const LANDMARKS = [
  { id: 'needle',     name: 'Space Needle',              lat: 47.62050, lon: -122.34930, kind: 'hero' },
  { id: 'mopop',      name: 'MoPOP',                     lat: 47.62152, lon: -122.34810, kind: 'box', w: 65,  d: 110, h: 25, rot: 8,   corridor: true },
  { id: 'station',    name: 'Seattle Center Station',    lat: 47.62215, lon: -122.34815, kind: 'stationSlot', w: 20, d: 70 },
  { id: 'psc',        name: 'Pacific Science Center',    lat: 47.61930, lon: -122.35120, kind: 'box', w: 150, d: 120, h: 10, rot: 0 },
  { id: 'arena',      name: 'Climate Pledge Arena',      lat: 47.62210, lon: -122.35400, kind: 'box', w: 150, d: 130, h: 26, rot: 0 },
  { id: 'fountain',   name: 'International Fountain',    lat: 47.62225, lon: -122.35130, kind: 'ring', r: 30 },
  { id: 'armory',     name: 'Armory',                    lat: 47.62215, lon: -122.34960, kind: 'box', w: 120, d: 60,  h: 15, rot: 0 },
  { id: 'chihuly',    name: 'Chihuly Garden and Glass',  lat: 47.62060, lon: -122.34860, kind: 'box', w: 40,  d: 22,  h: 12, rot: 0 },
  { id: 'mccaw',      name: 'McCaw Hall',                lat: 47.62360, lon: -122.35000, kind: 'box', w: 110, d: 80,  h: 30, rot: 0 },
  { id: 'rep',        name: 'Seattle Repertory Theatre', lat: 47.62390, lon: -122.35150, kind: 'box', w: 80,  d: 60,  h: 15, rot: 0 },
  { id: 'fisher',     name: 'Fisher Pavilion',           lat: 47.62130, lon: -122.35060, kind: 'box', w: 60,  d: 40,  h: 6,  rot: 0 },
  { id: 'mural',      name: 'Mural Amphitheatre',        lat: 47.62100, lon: -122.35010, kind: 'box', w: 30,  d: 10,  h: 8,  rot: 0 },
  { id: 'westlake',   name: 'Westlake stub',             lat: 47.61790, lon: -122.34620, kind: 'stub' },
];

export const byId = Object.fromEntries(LANDMARKS.map((l) => [l.id, { ...l, ...toVoxel(l.lat, l.lon) }]));

// Monorail route waypoints (env voxels), Seattle Center station → south to the
// Westlake stub, following 5th Ave N (x ≈ 225) then drifting SE downtown.
export const ROUTE_POINTS = [
  [172, -470], // north bumper, just past the station
  [172, -400], // platform (station centre ≈ z -400, clear of MoPOP's north face at -336)
  [176, -270], // entering MoPOP's corridor
  [186, -200], // leaving MoPOP
  [212, -100], // curve onto 5th Ave N
  [225, 0],
  [228, 200],
  [236, 400],
  [252, 560],
  [262, 630], // Westlake stub / world edge
];
export const BEAM_TOP = 18;        // 9 m above ground, env voxels
export const BEAM_SEPARATION = 16; // centre-to-centre, env voxels (8 m)
export const STATION = { zStart: -445, zEnd: -355 }; // platform extent along the route (env voxels)
