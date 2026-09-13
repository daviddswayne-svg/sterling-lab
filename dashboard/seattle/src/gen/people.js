// Voxel people at hero scale (0.25 m, ~1.5× true): 4 wide × 11 tall × 2 deep.
// Six variants (shirt / trousers / hair / skin combos) built as tiny grids;
// the sim instances them.
import { Grid } from '../voxel/Grid.js';

export const PERSON_H = 11;

const VARIANTS = [
  { shirt: 'person_shirt_red', pants: 'person_pants_dark', hair: 'person_hair_dark', skin: 'person_skin_1' },
  { shirt: 'person_shirt_blue', pants: 'person_pants_blue', hair: 'person_hair_light', skin: 'person_skin_2' },
  { shirt: 'person_shirt_yellow', pants: 'person_pants_dark', hair: 'person_hair_dark', skin: 'person_skin_3' },
  { shirt: 'person_shirt_green', pants: 'person_pants_khaki', hair: 'person_hair_red', skin: 'person_skin_1' },
  { shirt: 'person_shirt_white', pants: 'person_pants_blue', hair: 'person_hair_dark', skin: 'person_skin_2' },
  { shirt: 'person_shirt_purple', pants: 'person_pants_dark', hair: 'person_hair_light', skin: 'person_skin_3' },
];

/** Returns [{ grid }] — one grid per variant, feet at y=0, centred on x/z, facing +z. */
export function buildPeople(pal) {
  return VARIANTS.map((v) => {
    const g = new Grid();
    const P = (n) => pal.index(n);
    const fill = (x0, x1, y0, y1, z0, z1, idx) => {
      for (let z = z0; z <= z1; z++) for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) g.set(x, y, z, idx);
    };
    fill(-1, 0, 0, 4, 0, 0, P(v.pants));       // legs (two 1-wide columns: x=-1 and x=0)
    fill(-2, 1, 5, 8, 0, 0, P(v.shirt));       // torso
    fill(-2, -2, 5, 7, 0, 0, P(v.skin));       // arms (skin at the sides)
    fill(1, 1, 5, 7, 0, 0, P(v.skin));
    fill(-1, 0, 9, 10, 0, 0, P(v.skin));       // head
    fill(-1, 0, 10, 10, -1, -1, P(v.hair));    // hair (back)
    fill(-1, 0, 10, 10, 0, 0, P(v.hair));      // hair (top)
    return { grid: g };
  });
}
