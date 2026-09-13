// 1962 Alweg monorail train in voxels, from the V4 recipe: deep dark skirt
// straddling the beam, chrome belt line, painted hull, a continuous glass
// strip with framed windows, sliding doors, light roof with vents, and on the
// end cars a rounded nose with angled windshield, chrome bumper and twin
// lights (white ahead, red behind). Four cars: TAIL BODY BODY HEAD along +x.
//
// Authored at the HERO voxel size (0.25 m) at ~1.5× true scale so detail reads:
//   car 56 long × 19 wide × 27 tall (incl. 6 of skirt below beam top).
// Car-local frame: x ∈ [0, CAR_LEN-1] (+ NOSE beyond the end for end cars),
// y = 0 at beam top, z ∈ [-HW, HW].

export const VOXEL = 0.25;
export const CAR_LEN = 56, CAR_W = 19, HW = 9, NOSE = 12, GAP = 2;
export const SKIRT_DEPTH = 6;          // how far the skirt wraps down over the beam
export const BEAM_W = 6, BEAM_H = 8;   // beam cross-section at hero size (3 × 4 at 0.5 m)
export const DOOR_X = [12, 40];        // door left edges per car (2 doors per side)
export const DOOR_W = 7, DOOR_Y0 = 4, DOOR_Y1 = 15;
export const TRAIN_LEN = 4 * CAR_LEN + 3 * GAP + 2 * NOSE;

/**
 * Build one car into `grid` at `origin` (grid coords of car-local (0,0,0)).
 * kind: 'head' (nose at +x), 'tail' (nose at -x), 'body'.
 * Returns voxel count. Doors are left as painted panels (the dynamic sliding
 * door meshes are built separately by buildDoor).
 */
export function buildCar(grid, pal, origin, kind, { color = 'monorail_red', doors = true } = {}) {
  const P = (n) => pal.index(n);
  const [ox, oy, oz] = origin;
  let n = 0;
  const set = (x, y, z, idx) => { grid.set(ox + x, oy + y, oz + z, idx); n++; };
  const fill = (x0, x1, y0, y1, z0, z1, idx) => {
    for (let z = z0; z <= z1; z++) for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) set(x, y, z, idx);
  };
  const paint = P(color), skirt = P('monorail_skirt'), chrome = P('chrome'), glass = P('glass_clear');
  const roof = P('monorail_roof'), vent = P('vent_dark'), dark = P('black'), frame = P('monorail_frame');
  const x0 = 0, x1 = CAR_LEN - 1;

  // --- body ---
  fill(x0, x1, -SKIRT_DEPTH, 3, -HW, HW, skirt);            // skirt
  fill(x0, x1, -SKIRT_DEPTH, 1, -BEAM_W / 2, BEAM_W / 2, 0); // beam channel (air)
  fill(x0, x1, 4, 5, -HW, HW, chrome);                        // belt line
  fill(x0, x1, 6, 9, -HW, HW, paint);                         // painted hull
  fill(x0, x1, 10, 15, -HW, HW, glass);                       // glass strip
  fill(x0, x1, 10, 15, -HW + 1, HW - 1, dark);                // interior
  fill(x0, x1, 10, 10, -HW, HW, frame);                       // window sill line
  fill(x0, x1, 15, 15, -HW, HW, frame);                       // window head line
  for (let x = x0 + 5; x <= x1; x += 10) fill(x, x, 10, 15, -HW, HW, frame); // window mullions
  fill(x0, x1, 16, 17, -HW, HW, roof);                        // roof edge
  fill(x0, x1, 18, 19, -HW + 1, HW - 1, roof);                // rounded roof
  fill(x0, x1, 20, 20, -HW + 3, HW - 3, roof);                // crown
  fill(x0 + 8, x0 + 22, 21, 22, -4, 4, vent);                 // vent housings
  fill(x1 - 22, x1 - 8, 21, 22, -4, 4, vent);
  fill(x0 + 1, x1 - 1, -SKIRT_DEPTH + 1, -SKIRT_DEPTH + 1, -HW, -HW, chrome); // skirt trim
  fill(x0 + 1, x1 - 1, -SKIRT_DEPTH + 1, -SKIRT_DEPTH + 1, HW, HW, chrome);

  // --- doors (both sides): painted panels with a window, outlined by a frame ---
  if (doors) for (const dx of DOOR_X) for (const side of [-HW, HW]) {
    fill(dx - 1, dx + DOOR_W, DOOR_Y0 - 1, DOOR_Y1 + 1, side, side, frame);   // outline
    fill(dx, dx + DOOR_W - 1, DOOR_Y0, 9, side, side, paint);                 // lower panel
    fill(dx, dx + DOOR_W - 1, 10, DOOR_Y1, side, side, glass);                // door window
    const mid = dx + Math.floor(DOOR_W / 2);
    fill(mid, mid, DOOR_Y0, DOOR_Y1, side, side, frame);                      // centre split
  }

  // --- nose ---
  if (kind === 'head' || kind === 'tail') {
    const dir = kind === 'head' ? 1 : -1;
    const base = kind === 'head' ? x1 : x0;
    for (let i = 1; i <= NOSE; i++) {
      const x = base + dir * i;
      const t = i / NOSE;
      const w = Math.max(2, Math.round(HW * Math.sqrt(1 - t * t * 0.9)));   // plan taper
      const top = 19 - Math.round(t * t * 9);                                 // profile droop
      fill(x, x, -SKIRT_DEPTH, 3, -w, w, skirt);
      if (i <= 4) fill(x, x, -SKIRT_DEPTH, 1, -BEAM_W / 2, BEAM_W / 2, 0);
      fill(x, x, 4, 5, -w, w, chrome);
      fill(x, x, 6, 9, -w, w, paint);
      if (top >= 10) {
        const glassy = i >= 5;                                                 // windshield starts a third in
        fill(x, x, 10, Math.min(top, 15), -w, w, glassy ? glass : paint);
        if (glassy) fill(x, x, 10, Math.min(top, 15), -Math.max(0, w - 1), Math.max(0, w - 1), dark);
        if (glassy && i === 5) fill(x, x, 10, Math.min(top, 15), -w, w, frame); // windshield frame
      }
      if (top >= 16) fill(x, x, 16, top, -Math.max(0, w - 1), Math.max(0, w - 1), roof);
    }
    const tip = base + dir * NOSE;
    fill(tip, tip, 2, 4, -6, 6, chrome);                        // bumper
    const light = P(kind === 'head' ? 'headlight' : 'taillight');
    for (const z of [-5, 4]) { fill(tip, tip, 6, 8, z - 1, z + 2, chrome); fill(tip, tip, 7, 7, z, z + 1, light); } // lamp housings
    fill(tip, tip, 8, 8, -1, 1, chrome);                       // nose emblem
  }
  return n;
}

/** A whole static train (preview / bake). origin = car-local origin of the tail car. */
export function buildTrain(grid, pal, origin, opts = {}) {
  const kinds = ['tail', 'body', 'body', 'head'];
  let n = 0;
  for (let c = 0; c < 4; c++) {
    const ox = origin[0] + c * (CAR_LEN + GAP);
    n += buildCar(grid, pal, [ox, origin[1], origin[2]], kinds[c], opts);
    if (c < 3) {
      const g = pal.index('black');
      for (let x = ox + CAR_LEN; x < ox + CAR_LEN + GAP; x++)
        for (let y = 0; y <= 17; y++) for (let z = -HW + 2; z <= HW - 2; z++) { grid.set(x, origin[1] + y, origin[2] + z, g); n++; }
    }
  }
  return n;
}

/** Car x-offsets along the train (tail car first), for placing dynamic cars along a curve. */
export const CAR_OFFSETS = [0, 1, 2, 3].map((c) => c * (CAR_LEN + GAP) + CAR_LEN / 2);
export const CAR_KINDS = ['tail', 'body', 'body', 'head'];
