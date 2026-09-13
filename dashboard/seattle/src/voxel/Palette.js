// 256-entry palette. Each vertex carries a palette index; the renderer looks
// up color + material class from a texture, so retuning never needs a rebake.
// Entry: { name, r, g, b (0-255), metal, rough, emissive (0-1), flags }

export const FLAG_GLASS = 1;        // transparent pass
export const FLAG_FRESNEL_BLUE = 2; // pearlescent hue shift at grazing angles (MoPOP blue)
export const FLAG_NO_JITTER = 4;    // skip per-voxel color variation (signs, screens)
export const FLAG_PANELS = 8;       // panel-scale shade variation (MoPOP's 21,000 shingles)

export const BYTES_PER_ENTRY = 8;

export class Palette {
  constructor() {
    this.entries = new Array(256).fill(null).map(() => ({
      name: '', r: 0, g: 0, b: 0, metal: 0, rough: 1, emissive: 0, flags: 0,
    }));
    this.byName = new Map();
    this.next = 1; // 0 is air
  }

  add(name, hex, { metal = 0, rough = 0.85, emissive = 0, flags = 0 } = {}) {
    if (this.byName.has(name)) return this.byName.get(name);
    if (this.next > 255) throw new Error('palette full');
    const idx = this.next++;
    const n = parseInt(hex.replace('#', ''), 16);
    Object.assign(this.entries[idx], {
      name, r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, metal, rough, emissive, flags,
    });
    this.byName.set(name, idx);
    return idx;
  }

  index(name) {
    const i = this.byName.get(name);
    if (i === undefined) throw new Error(`unknown palette entry ${name}`);
    return i;
  }

  isGlass(idx) {
    return (this.entries[idx].flags & FLAG_GLASS) !== 0;
  }

  // Uint8Array(256) of flags, handed to the mesher / worker.
  flagsArray() {
    const f = new Uint8Array(256);
    for (let i = 0; i < 256; i++) f[i] = this.entries[i].flags;
    return f;
  }

  toBytes() {
    const out = new Uint8Array(256 * BYTES_PER_ENTRY);
    this.entries.forEach((e, i) => {
      const o = i * BYTES_PER_ENTRY;
      out[o] = e.r; out[o + 1] = e.g; out[o + 2] = e.b;
      out[o + 3] = Math.round(e.metal * 255);
      out[o + 4] = Math.round(e.rough * 255);
      out[o + 5] = Math.round(e.emissive * 255);
      out[o + 6] = e.flags;
      out[o + 7] = 0;
    });
    return out;
  }

  // Restore names (and the name → index map) after fromBytes.
  setNames(names) {
    this.byName.clear();
    names.forEach((n, i) => {
      this.entries[i].name = n || '';
      if (n) { this.byName.set(n, i); this.next = Math.max(this.next, i + 1); }
    });
  }

  static fromBytes(bytes) {
    const p = new Palette();
    for (let i = 0; i < 256; i++) {
      const o = i * BYTES_PER_ENTRY;
      Object.assign(p.entries[i], {
        r: bytes[o], g: bytes[o + 1], b: bytes[o + 2],
        metal: bytes[o + 3] / 255, rough: bytes[o + 4] / 255, emissive: bytes[o + 5] / 255,
        flags: bytes[o + 6],
      });
    }
    return p;
  }
}

// The starter palette. Names are what generators reference.
export function defaultPalette() {
  const p = new Palette();
  // site basics
  p.add('grass', '#6b9c4a', { rough: 1 });
  p.add('grass_dark', '#5c8a3f', { rough: 1 });
  p.add('asphalt', '#3a3a3e', { rough: 0.95 });
  p.add('concrete', '#c9c6bd', { rough: 0.9 });
  p.add('concrete_dark', '#8d8a82', { rough: 0.9 });
  p.add('pavement', '#b5b0a5', { rough: 0.9 });
  p.add('dirt', '#6e5a3e', { rough: 1 });
  // Space Needle
  p.add('needle_white', '#ebe9e2', { rough: 0.6 });
  p.add('needle_core', '#c4c2bb', { rough: 0.8 });
  p.add('needle_gold', '#e0a534', { metal: 0.9, rough: 0.35 });
  p.add('needle_steel', '#4a4d52', { metal: 0.7, rough: 0.45 });
  p.add('needle_glass', '#9fc6e6', { metal: 0.1, rough: 0.05, flags: FLAG_GLASS });
  p.add('deck_floor', '#2a2a2e', { rough: 0.7 });
  p.add('beacon_red', '#ff2a2a', { emissive: 1, flags: FLAG_NO_JITTER });
  // MoPOP finishes (from the reference photos): bead-blasted gold stainless,
  // brushed silver stainless, mirrored purple stainless, painted pale-blue and
  // red aluminium, plus the silver-white billow and the Sky Church's dark roof.
  p.add('mopop_gold', '#c3923c', { metal: 0.95, rough: 0.4, flags: FLAG_PANELS });
  p.add('mopop_blue', '#7fa8cf', { metal: 0.75, rough: 0.32, flags: FLAG_PANELS | FLAG_FRESNEL_BLUE });
  p.add('mopop_silver', '#a9aeb7', { metal: 0.92, rough: 0.5, flags: FLAG_PANELS });
  p.add('mopop_red', '#a8262a', { metal: 0.45, rough: 0.5, flags: FLAG_PANELS });
  p.add('mopop_purple', '#472468', { metal: 1.0, rough: 0.12, flags: FLAG_PANELS | FLAG_FRESNEL_BLUE });
  p.add('mopop_white', '#c9ced5', { metal: 0.85, rough: 0.45, flags: FLAG_PANELS });
  p.add('mopop_dark', '#2b2d31', { rough: 0.9 });
  // generic building / vehicle colors
  p.add('brick', '#8b4a3a', { rough: 0.95 });
  p.add('window_dark', '#1c2230', { metal: 0.2, rough: 0.2 });
  p.add('window_lit', '#ffd98a', { emissive: 0.8, flags: FLAG_NO_JITTER });
  p.add('glass_clear', '#cfe6f5', { metal: 0.1, rough: 0.05, flags: FLAG_GLASS });
  p.add('white', '#e6e6e4', { rough: 0.5 });
  p.add('black', '#141414', { rough: 0.6 });
  p.add('monorail_blue', '#1f5fb8', { metal: 0.3, rough: 0.35 });
  p.add('monorail_red', '#c8202f', { metal: 0.3, rough: 0.35 });
  p.add('monorail_skirt', '#3d3d40', { rough: 0.8 });
  p.add('monorail_roof', '#d6d6d2', { rough: 0.5 });
  p.add('monorail_frame', '#4a4d55', { metal: 0.5, rough: 0.4 });
  p.add('chrome', '#e2e2e0', { metal: 0.95, rough: 0.12 });
  p.add('vent_dark', '#2a2a2c', { rough: 0.9 });
  p.add('headlight', '#fff6d5', { emissive: 1, flags: FLAG_NO_JITTER });
  p.add('taillight', '#ff2020', { emissive: 0.9, flags: FLAG_NO_JITTER });
  p.add('beam_concrete', '#b9b6ad', { rough: 0.9 });
  p.add('water', '#3f7fa8', { metal: 0.2, rough: 0.1, flags: FLAG_GLASS });
  p.add('tree_trunk', '#5b4128', { rough: 1 });
  p.add('tree_leaf', '#3f7a2f', { rough: 1 });
  p.add('tree_leaf_light', '#5b9a3c', { rough: 1 });
  // people
  p.add('person_skin_1', '#e8b894', { rough: 0.9 });
  p.add('person_skin_2', '#c68a5b', { rough: 0.9 });
  p.add('person_skin_3', '#8a5a3c', { rough: 0.9 });
  p.add('person_hair_dark', '#2b2118', { rough: 0.9 });
  p.add('person_hair_light', '#c9a86a', { rough: 0.9 });
  p.add('person_hair_red', '#8f4a2a', { rough: 0.9 });
  p.add('person_shirt_red', '#c23a3a', { rough: 0.9 });
  p.add('person_shirt_blue', '#2f62b8', { rough: 0.9 });
  p.add('person_shirt_yellow', '#e0b33a', { rough: 0.9 });
  p.add('person_shirt_green', '#3f8f4f', { rough: 0.9 });
  p.add('person_shirt_white', '#eeeeea', { rough: 0.9 });
  p.add('person_shirt_purple', '#6d3f9a', { rough: 0.9 });
  p.add('person_pants_dark', '#2c2c34', { rough: 0.9 });
  p.add('person_pants_blue', '#3b4d78', { rough: 0.9 });
  p.add('person_pants_khaki', '#a8905c', { rough: 0.9 });
  return p;
}
