// Three Space Needle elevator cabs climbing the outside of the core, with V4's
// wait → accelerate → decelerate → wait cycle. Each cab is a small hero-scale
// voxel object; the camera can ride inside looking outward.
import * as THREE from 'three';
import { Grid } from '../voxel/Grid.js';
import { meshGrid } from '../render/VoxelObject.js';
import { VOXEL as HERO } from '../gen/monorail.js';

const CAB = { w: 8, h: 11, d: 8 }; // hero voxels
const RADIUS_M = 5.2;               // cab centre from the Needle axis
const BOTTOM_M = 1.5, TOP_M = 152;  // Loupe level
const MAX_SPEED = 7, ACCEL = 2.5;   // m/s, m/s² (real: ~4 m/s — sped up for feel)

export class Elevators {
  constructor(app, { colors = ['monorail_blue', 'needle_gold', 'monorail_red'], angles = [60, 180, 300] } = {}) {
    this.app = app;
    const flags = app.palette.flagsArray();
    const materials = app.materialsFor(HERO);
    this.cabs = angles.map((deg, i) => {
      const g = new Grid();
      const P = (n) => app.palette.index(n);
      const body = P(colors[i]), glass = P('glass_clear'), floor = P('deck_floor'), steel = P('needle_steel');
      for (let z = 0; z < CAB.d; z++) for (let y = 0; y < CAB.h; y++) for (let x = 0; x < CAB.w; x++) {
        const edge = x === 0 || x === CAB.w - 1 || z === 0 || z === CAB.d - 1;
        if (!edge && y > 0 && y < CAB.h - 1) continue;             // hollow
        let idx = body;
        if (y === 0) idx = floor;
        else if (y === CAB.h - 1) idx = steel;
        else if (x === CAB.w - 1 && y > 1 && y < CAB.h - 2) idx = glass; // outward-facing glass wall (+x)
        g.set(x - CAB.w / 2, y, z - CAB.d / 2, idx);
      }
      const group = meshGrid(g, flags, HERO, materials);
      app.scene.add(group);
      const rad = (deg * Math.PI) / 180;
      return {
        group, deg, rad,
        radial: new THREE.Vector3(Math.cos(rad), 0, Math.sin(rad)),
        y: BOTTOM_M + (i * 50) % 150, v: 0, mode: 'wait', wait: 2 + i * 3, target: TOP_M,
      };
    });
    for (const c of this.cabs) this.place(c);
  }

  place(c) {
    c.group.position.set(c.radial.x * RADIUS_M, c.y, c.radial.z * RADIUS_M);
    c.group.rotation.y = -c.rad; // local +x (glass wall) points away from the axis
  }

  update(dt) {
    for (const c of this.cabs) {
      if (c.mode === 'wait') {
        c.wait -= dt;
        if (c.wait <= 0) { c.mode = 'move'; c.target = c.y < (TOP_M + BOTTOM_M) / 2 ? TOP_M : BOTTOM_M; }
        continue;
      }
      const remaining = Math.abs(c.target - c.y);
      const dir = Math.sign(c.target - c.y);
      const vAllowed = Math.min(MAX_SPEED, Math.sqrt(2 * ACCEL * remaining));
      c.v = Math.min(c.v + ACCEL * dt, vAllowed);
      c.y += dir * c.v * dt;
      if (remaining <= c.v * dt + 0.02) { c.y = c.target; c.v = 0; c.mode = 'wait'; c.wait = 4 + Math.random() * 4; }
      this.place(c);
    }
  }

  /** Camera inside cab 0 looking outward through the glass. */
  cameraPose() {
    const c = this.cabs[0];
    const pos = c.group.localToWorld(new THREE.Vector3(0.6, 1.6, 0));
    const lookAt = c.group.localToWorld(new THREE.Vector3(40, -12, 0)); // tilted down toward the grounds
    return { position: pos, lookAt };
  }

  statusText() { const c = this.cabs[0]; return `Elevator ${c.mode === 'wait' ? 'doors' : (c.target > c.y ? 'up' : 'down')} ${c.y.toFixed(0)} m`; }
}

/** Slow orbit at deck height — the Loupe's rotation, sped up. */
export class DeckCamera {
  // Observation deck floor is ~158.5 m; the deck radius is ~21 m.
  constructor({ radius = 18, height = 160.2, period = 120 } = {}) {
    Object.assign(this, { radius, height, period, t: 0 });
  }
  update(dt) { this.t += dt; }
  cameraPose() {
    const a = (this.t / this.period) * Math.PI * 2;
    const pos = new THREE.Vector3(Math.cos(a) * this.radius, this.height, Math.sin(a) * this.radius);
    const lookAt = new THREE.Vector3(Math.cos(a) * 300, this.height - 175, Math.sin(a) * 300); // ~30° down: deck rail in frame, grounds beyond
    return { position: pos, lookAt };
  }
}
