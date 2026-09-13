// 1962 Alweg monorail train, rebuilt in voxels from the V4 recipe:
// deep dark skirt straddling the beam, chrome belt line, painted hull, a
// continuous glass strip with painted mullions, light roof with a vent, and
// on the end cars a rounded nose with angled windshield, chrome bumper and
// twin lights (white ahead, red behind). Four cars: HEAD BODY BODY TAIL.
//
// Units are voxels at "hero" scale (~1.5× true size so the detail reads):
//   car 28 long × 9 wide × 12 tall, 1-voxel articulation gaps.
// Train runs along +x; origin = centre of the train at beam-top level.

export const CAR_LEN = 28, CAR_W = 9, CAR_H = 12, GAP = 1, NOSE = 6;
export const TRAIN_LEN = 4 * CAR_LEN + 3 * GAP + 2 * NOSE;
export const BEAM_W = 3, BEAM_H = 4;

/**
 * Write the train into `grid`. color = palette name for the livery.
 * Returns voxel count. `cars` lets callers build a single car for dynamic use.
 */
export function buildTrain(grid, pal, origin, { color = 'monorail_red' } = {}) {
  const P = (n) => pal.index(n);
  const [ox, oy, oz] = origin;
  let n = 0;
  const set = (x, y, z, idx) => { grid.set(ox + x, oy + y, oz + z, idx); n++; };
  const fill = (x0, x1, y0, y1, z0, z1, idx) => {
    for (let z = z0; z <= z1; z++) for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) set(x, y, z, idx);
  };
  const hw = (CAR_W - 1) / 2; // 4 → z in [-4, 4]
  const paint = P(color), skirt = P('monorail_skirt'), chrome = P('chrome'), glass = P('glass_clear');
  const roof = P('monorail_roof'), vent = P('vent_dark'), dark = P('black');

  // One car body from x0 to x1 (inclusive)
  const body = (x0, x1) => {
    fill(x0, x1, -3, 1, -hw, hw, skirt);            // skirt: wraps 3 voxels down over the beam
    fill(x0, x1, -3, 0, -1, 1, 0);                  // channel for the beam (air)
    fill(x0, x1, 2, 2, -hw, hw, chrome);            // belt line
    fill(x0, x1, 3, 4, -hw, hw, paint);             // painted hull
    fill(x0, x1, 5, 7, -hw, hw, glass);             // glass strip (full height windows)
    for (let x = x0 + 2; x <= x1; x += 5) fill(x, x, 5, 7, -hw, hw, paint); // mullions
    fill(x0, x1, 5, 7, -hw + 1, hw - 1, dark);      // dark interior behind the glass
    fill(x0, x1, 8, 8, -hw, hw, roof);              // roof edge
    fill(x0, x1, 9, 9, -hw + 1, hw - 1, roof);      // rounded roof
    fill(x0 + 4, x1 - 4, 10, 10, -2, 2, vent);      // vent box
  };

  // Nose: dir = +1 at the front (x beyond x1), -1 at the back (x before x0)
  const nose = (xBase, dir, isHead) => {
    for (let i = 1; i <= NOSE; i++) {
      const x = xBase + dir * i;
      const t = i / NOSE;                             // 0 → 1 toward the tip
      const w = Math.max(1, Math.round(hw * Math.sqrt(1 - t * t * 0.85))); // plan-view taper
      const top = 9 - Math.round(t * t * 4);          // profile droops toward the tip
      fill(x, x, -3, 1, -w, w, skirt);
      if (i <= 2) fill(x, x, -3, 0, -1, 1, 0);        // beam channel continues
      fill(x, x, 2, 2, -w, w, chrome);
      fill(x, x, 3, 4, -w, w, paint);
      // windshield: glass on the upper front, painted below the belt
      if (top >= 5) fill(x, x, 5, Math.min(top, 7), -w, w, i >= 3 ? glass : paint);
      if (i >= 3) fill(x, x, 5, Math.min(top, 7), -Math.max(0, w - 1), Math.max(0, w - 1), dark);
      if (top >= 8) fill(x, x, 8, top, -Math.max(0, w - 1), Math.max(0, w - 1), roof);
    }
    const tip = xBase + dir * NOSE;
    fill(tip, tip, 1, 1, -3, 3, chrome);              // bumper
    const light = P(isHead ? 'headlight' : 'taillight');
    set(tip, 3, -2, light); set(tip, 3, 2, light);
    if (isHead) set(tip, 4, 0, chrome);              // headlamp trim / logo
  };

  const start = -Math.floor(TRAIN_LEN / 2) + NOSE;
  for (let c = 0; c < 4; c++) {
    const x0 = start + c * (CAR_LEN + GAP);
    const x1 = x0 + CAR_LEN - 1;
    body(x0, x1);
    if (c < 3) fill(x1 + 1, x1 + 1, -1, 8, -hw + 1, hw - 1, dark); // articulation gaiter
    if (c === 0) nose(x0, -1, false);   // tail lights at the back
    if (c === 3) nose(x1, +1, true);    // head lights at the front
  }
  return n;
}

/** Straight elevated beam along x with piers. beamTop = y of the beam's top surface. */
export function buildBeam(grid, pal, x0, x1, beamTop, z, { pierEvery = 42 } = {}) {
  const beam = pal.index('beam_concrete'), pier = pal.index('concrete_dark');
  let n = 0;
  for (let x = x0; x <= x1; x++)
    for (let y = beamTop - BEAM_H + 1; y <= beamTop; y++)
      for (let dz = -1; dz <= 1; dz++) { grid.set(x, y, z + dz, beam); n++; }
  for (let x = x0 + pierEvery / 2; x <= x1; x += pierEvery) {
    for (let y = 0; y <= beamTop - BEAM_H; y++) for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) { grid.set(Math.round(x) + dx, y, z + dz, pier); n++; }
    // pier cap
    for (let dz = -2; dz <= 2; dz++) for (let dx = -2; dx <= 2; dx++) grid.set(Math.round(x) + dx, beamTop - BEAM_H, z + dz, pier);
  }
  return n;
}
