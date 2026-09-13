// The Seattle Center Monorail shuttle: four car meshes following a beam
// spline, run → arrive → doors → dwell → return. Ported from V4's Train
// (reverse at the ends, stop timer) with distance-based ease in/out.
import * as THREE from 'three';
import { Grid } from '../voxel/Grid.js';
import { meshGrid } from '../render/VoxelObject.js';
import { buildCar, CAR_LEN, CAR_OFFSETS, CAR_KINDS, TRAIN_LEN, NOSE, DOOR_X, DOOR_W, HW, VOXEL as HERO } from '../gen/monorail.js';
import { ENV_VOXEL as ENV } from '../site/layout.js';

const HERO_TO_ENV = HERO / ENV; // 0.5

export class Train {
  /**
   * @param app        from createApp (needs palette, materialsFor, scene)
   * @param spline     beam centreline in env voxels (y = beam top)
   * @param opts       { color, stops: [sA, sB] (env voxels), dwell, vmax, accel, startAt, direction }
   */
  constructor(app, spline, { color, stops, dwell = 18, vmax = 24, accel = 4, startAt = null, direction = 1, name = color } = {}) {
    this.app = app;
    this.spline = spline;
    this.name = name;
    this.stops = stops;          // [north, south] arc lengths of the train centre when stopped
    this.dwell = dwell;
    this.vmax = vmax;            // env voxels / s  (24 ≈ 12 m/s)
    this.accel = accel;
    // `direction` = the NEXT departure direction (+1 toward stops[1] / south).
    // While dwelling, this.direction holds the previous travel direction and is
    // flipped on departure, so seed it inverted.
    this.direction = -direction;
    this.s = startAt ?? stops[0];
    this.v = 0;
    this.state = 'dwell';
    this.timer = dwell * 0.5;
    this.doorsOpen = true;
    this.listeners = [];

    // Build the four cars, pivot at each car's centre on the beam top.
    const flags = app.palette.flagsArray();
    const materials = app.materialsFor(HERO);
    this.cars = CAR_KINDS.map((kind) => {
      const g = new Grid();
      buildCar(g, app.palette, [-CAR_LEN / 2, 0, 0], kind, { color });
      const group = meshGrid(g, flags, HERO, materials);
      app.scene.add(group);
      return group;
    });
    this.place();
  }

  on(event, fn) { this.listeners.push({ event, fn }); }
  emit(event) { for (const l of this.listeners) if (l.event === event) l.fn(this); }

  get target() { return this.direction > 0 ? this.stops[1] : this.stops[0]; }
  get progress() { const [a, b] = this.stops; return (this.s - a) / (b - a); }

  update(dt) {
    if (this.state === 'dwell') {
      this.timer -= dt;
      if (this.timer <= 0) {
        this.doorsOpen = false;
        this.emit('doorsClose');
        this.state = 'moving';
        this.direction *= -1;
      }
      return;
    }
    // ease: never faster than what lets us stop exactly at the target
    const remaining = Math.abs(this.target - this.s);
    const vAllowed = Math.min(this.vmax, Math.sqrt(2 * this.accel * remaining));
    this.v = Math.min(this.v + this.accel * dt, vAllowed);
    this.s += this.direction * this.v * dt;
    if (remaining <= this.v * dt + 0.05) {
      this.s = this.target;
      this.v = 0;
      this.state = 'dwell';
      this.timer = this.dwell;
      this.doorsOpen = true;
      this.emit('arrive');
      this.emit('doorsOpen');
    }
    this.place();
  }

  place() {
    for (let i = 0; i < 4; i++) {
      const sCar = this.s + (CAR_OFFSETS[i] - TRAIN_LEN / 2) * HERO_TO_ENV;
      const p = this.spline.pointAt(sCar), t = this.spline.tangentAt(sCar);
      const car = this.cars[i];
      car.position.set(p.x * ENV, p.y * ENV, p.z * ENV);
      car.rotation.y = Math.atan2(-t.z, t.x); // local +x (car length) along the tangent
    }
  }

  /** Camera in the leading cab, looking down the beam. */
  cameraPose() {
    const lead = this.direction > 0 ? this.cars[3] : this.cars[0];
    const forward = this.direction > 0 ? 1 : -1;
    // just ahead of the nose tip, at windshield height, so the cab doesn't crowd the frame
    const local = new THREE.Vector3(forward * (CAR_LEN / 2 + NOSE + 2) * HERO, 12 * HERO, 0);
    const pos = lead.localToWorld(local.clone());
    const ahead = lead.localToWorld(local.clone().add(new THREE.Vector3(forward * 80, -3, 0)));
    return { position: pos, lookAt: ahead };
  }

  /** World positions (metres) of the door centres on one side (+1 = local +z side, -1 = -z). */
  doorPositions(side = 1) {
    const out = [];
    for (const car of this.cars)
      for (const dx of DOOR_X)
        out.push(car.localToWorld(new THREE.Vector3((dx + DOOR_W / 2 - CAR_LEN / 2) * HERO, 0, side * (HW + 1) * HERO)));
    return out;
  }

  /** A point just behind the trailing car for a chase camera. */
  chasePose() {
    const trail = this.direction > 0 ? this.cars[0] : this.cars[3];
    const back = this.direction > 0 ? -1 : 1;
    const pos = trail.localToWorld(new THREE.Vector3(back * 40 * HERO, 40 * HERO, 30 * HERO));
    const lookAt = trail.localToWorld(new THREE.Vector3(-back * 60 * HERO, 8 * HERO, 0));
    return { position: pos, lookAt };
  }

  statusText() {
    return this.state === 'dwell'
      ? `${this.name}: doors open ${this.timer.toFixed(0)}s`
      : `${this.name}: ${this.direction > 0 ? 'south' : 'north'} ${(this.v * ENV).toFixed(0)} m/s`;
  }
}
