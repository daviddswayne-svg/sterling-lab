// Instanced crowd: platform waiters who board when doors open, arrivals who
// spill out and head for the stairs, and plaza wanderers under the Needle.
import * as THREE from 'three';
import { meshGrid } from '../render/VoxelObject.js';
import { buildPeople, PERSON_H } from '../gen/people.js';
import { VOXEL as HERO } from '../gen/monorail.js';

const CAP = 24; // instances per variant

export class People {
  constructor(app, { platform, plaza, stairs }) {
    this.app = app;
    this.platform = platform; // { center: Vector3, along: Vector3 (unit), halfLen, halfWidth, y }
    this.plaza = plaza;       // { center: Vector3, rMin, rMax }
    this.stairs = stairs;     // Vector3 where arrivals exit
    const flags = app.palette.flagsArray();
    const materials = app.materialsFor(HERO);
    this.meshes = buildPeople(app.palette).map(({ grid }) => {
      const group = meshGrid(grid, flags, HERO, materials);
      const src = group.children.find((m) => m.material === materials.opaque);
      const im = new THREE.InstancedMesh(src.geometry, materials.opaque, CAP);
      im.castShadow = true;
      im.count = 0;
      app.scene.add(im);
      return im;
    });
    this.people = [];
    this.dummy = new THREE.Object3D();

    // populate
    for (let i = 0; i < 18; i++) this.spawn('wait', this.randomOnPlatform());
    for (let i = 0; i < 16; i++) this.spawn('wander', this.randomOnPlaza());
  }

  spawn(state, pos) {
    const variant = Math.floor(Math.random() * this.meshes.length);
    const p = { variant, pos: pos.clone(), target: pos.clone(), state, speed: 1.1 + Math.random() * 0.6, wait: Math.random() * 3, yaw: Math.random() * Math.PI * 2 };
    this.people.push(p);
    return p;
  }

  randomOnPlatform() {
    const a = (Math.random() * 2 - 1) * this.platform.halfLen, b = (Math.random() * 2 - 1) * this.platform.halfWidth;
    const side = new THREE.Vector3(-this.platform.along.z, 0, this.platform.along.x);
    return this.platform.center.clone().addScaledVector(this.platform.along, a).addScaledVector(side, b);
  }
  randomOnPlaza() {
    const r = this.plaza.rMin + Math.random() * (this.plaza.rMax - this.plaza.rMin), a = Math.random() * Math.PI * 2;
    return this.plaza.center.clone().add(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
  }

  /** Train doors opened at the platform: waiters board, arrivals step out. */
  onDoorsOpen(train, platformSide) {
    const doors = train.doorPositions(platformSide).map((d) => d.setY(this.platform.y));
    for (const p of this.people) {
      if (p.state !== 'wait') continue;
      let best = doors[0], bd = Infinity;
      for (const d of doors) { const dd = d.distanceToSquared(p.pos); if (dd < bd) { bd = dd; best = d; } }
      p.target.copy(best); p.state = 'board';
    }
    const arriving = 6 + Math.floor(Math.random() * 6);
    for (let i = 0; i < arriving; i++) {
      const d = doors[Math.floor(Math.random() * doors.length)];
      const p = this.spawn('alight', d);
      p.target.copy(this.stairs);
    }
  }

  update(dt) {
    for (let i = this.people.length - 1; i >= 0; i--) {
      const p = this.people[i];
      if (p.state === 'wait' || p.state === 'wander') {
        p.wait -= dt;
        if (p.wait <= 0) {
          p.target.copy(p.state === 'wait' ? this.randomOnPlatform() : this.randomOnPlaza());
          p.wait = 2 + Math.random() * 6;
        }
      }
      const to = p.target.clone().sub(p.pos); to.y = 0;
      const dist = to.length();
      if (dist > 0.15) {
        to.normalize();
        p.pos.addScaledVector(to, Math.min(dist, p.speed * dt));
        p.yaw = Math.atan2(to.x, to.z);
      } else if (p.state === 'board') {
        this.people.splice(i, 1); // stepped into the train
        continue;
      } else if (p.state === 'alight') {
        this.people.splice(i, 1); // down the stairs and gone
        if (this.people.filter((q) => q.state === 'wait').length < 18) this.spawn('wait', this.randomOnPlatform()).wait = 6;
        continue;
      }
    }
    // write instance matrices
    const counts = new Array(this.meshes.length).fill(0);
    for (const p of this.people) {
      const im = this.meshes[p.variant];
      const idx = counts[p.variant]++;
      if (idx >= CAP) continue;
      this.dummy.position.copy(p.pos);
      this.dummy.rotation.set(0, p.yaw, 0);
      this.dummy.updateMatrix();
      im.setMatrixAt(idx, this.dummy.matrix);
    }
    this.meshes.forEach((im, v) => { im.count = Math.min(counts[v], CAP); im.instanceMatrix.needsUpdate = true; });
  }
}

export const PERSON_HEIGHT_M = PERSON_H * HERO;
