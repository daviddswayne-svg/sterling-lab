// Space Needle, built from the spec sheet at 0.5 m per voxel.
//   total 605 ft / 184 m → 368 voxels; observation deck 520 ft → 320; Loupe 500 ft → 305
//   base spread Ø102 ft → r≈31; top house Ø138 ft → r≈42; legs pinch at 373 ft → 227
// Everything is an SDF in voxel units, rasterized into the grid around (cx, cz).

import {
  revolveY, annulusY, cylinderY, box, union, radial, clipY, translate, rotateY,
  rasterize, aabbAround, aabb,
} from '../voxel/Shapes.js';

// Leg radius (distance of the leg pair centerline from the axis) by height.
function legRadius(y) {
  const WAIST_Y = 227, TOP_Y = 293;
  if (y < WAIST_Y) {
    const t = y / WAIST_Y;
    return 12 + 19 * Math.pow(1 - t, 1.6);      // 31 at ground → 12 at the waist
  }
  const t = (y - WAIST_Y) / (TOP_Y - WAIST_Y);
  return 12 + 16 * Math.pow(t, 1.4);            // flares back out to ~28 under the top house
}

// One leg column: follows legRadius(y) at angle `deg`, offset sideways by `off`.
function legColumn(deg, off, thick, y0, y1) {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return (x, y, z) => {
    const yc = Math.min(Math.max(y, y0), y1);
    const r = legRadius(yc);
    const cxr = r * c - off * s, czr = r * s + off * c;
    const d = Math.sqrt((x - cxr) ** 2 + (z - czr) ** 2) - thick;
    return Math.max(d, Math.max(y0 - y, y - y1));
  };
}

// Horizontal tie between the two columns of a pair at height y.
function legTie(deg, off, y, thick) {
  const inner = (x, yy, z) => {
    const r = legRadius(y);
    return box(r, y, 0, thick, thick, off + thick)(x, yy, z);
  };
  return rotateY(inner, deg);
}

export function buildNeedle(grid, pal, cx = 0, cz = 0, baseY = 0) {
  const P = (n) => pal.index(n);
  const T = (f) => translate(f, cx, baseY, cz);
  const stats = {};
  const put = (name, sdf, box, idx) => { stats[name] = (stats[name] || 0) + rasterize(grid, T(sdf), box, idx); };
  const around = (r, y0, y1) => aabbAround(cx, cz, r, baseY + y0, baseY + y1);

  const LEG_TOP = 293, LOUPE = 305, DECK = 316, BRIM = 328, DOME_TOP = 350, SPIRE_TOP = 368;
  const PAIR_OFF = 3.5, LEG_THICK = 1.6;

  // Ground pavilion (the round base building) + plaza
  put('plaza', cylinderY(0, 0, 60, -1, 0), around(61, -1, 0), P('pavement'));
  put('pavilion', annulusY(0, 0, 0, 12, () => 30, () => 40), around(41, 0, 12), P('needle_glass'));
  put('pavilion_roof', cylinderY(0, 0, 41, 12, 14), around(42, 12, 14), P('needle_white'));
  put('pavilion_floor', cylinderY(0, 0, 40, 0, 1), around(41, 0, 1), P('deck_floor'));

  // Core (elevator core runs to the top house)
  put('core', cylinderY(0, 0, 6, 0, LOUPE), around(7, 0, LOUPE), P('needle_core'));

  // Three leg pairs, 120° apart, plus ties every 20 voxels
  const pair = union(
    legColumn(0, PAIR_OFF, LEG_THICK, 0, LEG_TOP),
    legColumn(0, -PAIR_OFF, LEG_THICK, 0, LEG_TOP),
  );
  const ties = [];
  for (let y = 12; y < LEG_TOP - 5; y += 20) ties.push(legTie(0, PAIR_OFF, y, 1.2));
  put('legs', radial(union(pair, ...ties), 3, 90), around(34, 0, LEG_TOP), P('needle_white'));

  // Skyline level (100 ft → 61) — disc hung between the legs
  put('skyline_floor', annulusY(0, 0, 60, 62, () => 7, () => 26), around(27, 60, 62), P('needle_white'));
  put('skyline_glass', annulusY(0, 0, 62, 68, () => 25, () => 26), around(27, 62, 68), P('needle_glass'));
  put('skyline_roof', annulusY(0, 0, 68, 70, () => 7, () => 27), around(28, 68, 70), P('needle_white'));

  // Top house: soffit cone → Loupe (restaurant) → deck → gold brim → dome
  put('soffit', revolveY(0, 0, LEG_TOP, LOUPE, y => 28 + (42 - 28) * Math.pow((y - LEG_TOP) / (LOUPE - LEG_TOP), 0.7)),
    around(43, LEG_TOP, LOUPE), P('needle_white'));
  put('loupe_floor', cylinderY(0, 0, 42, LOUPE, LOUPE + 1), around(43, LOUPE, LOUPE + 1), P('deck_floor'));
  put('loupe_glass', annulusY(0, 0, LOUPE + 1, DECK, () => 41, () => 42.5), around(44, LOUPE + 1, DECK), P('needle_glass'));
  put('loupe_mullions', radial(box(41.5, (LOUPE + DECK) / 2, 0, 1.2, (DECK - LOUPE) / 2, 0.6), 24), around(44, LOUPE + 1, DECK), P('needle_steel'));
  put('deck_floor', cylinderY(0, 0, 46, DECK, DECK + 1), around(47, DECK, DECK + 1), P('deck_floor'));
  put('deck_glass', annulusY(0, 0, DECK + 1, DECK + 8, y => 45 + (y - DECK) * 0.3, y => 46.5 + (y - DECK) * 0.3), around(50, DECK + 1, DECK + 8), P('needle_glass'));
  put('deck_rail', annulusY(0, 0, DECK + 8, DECK + 9, () => 47, () => 49), around(50, DECK + 8, DECK + 9), P('needle_steel'));
  put('brim', annulusY(0, 0, BRIM, BRIM + 4, () => 14, () => 50), around(51, BRIM, BRIM + 4), P('needle_gold'));
  put('dome', revolveY(0, 0, BRIM + 4, DOME_TOP, y => 46 * Math.sqrt(Math.max(0, 1 - Math.pow((y - BRIM - 4) / (DOME_TOP - BRIM - 4), 2)))),
    around(47, BRIM + 4, DOME_TOP), P('needle_white'));

  // Spire + beacon
  put('spire', revolveY(0, 0, DOME_TOP - 2, SPIRE_TOP - 2, y => 3 - 2 * (y - DOME_TOP) / (SPIRE_TOP - DOME_TOP)), around(4, DOME_TOP - 2, SPIRE_TOP - 2), P('needle_steel'));
  put('beacon', cylinderY(0, 0, 1.2, SPIRE_TOP - 2, SPIRE_TOP), around(2, SPIRE_TOP - 2, SPIRE_TOP), P('beacon_red'));

  return stats;
}
