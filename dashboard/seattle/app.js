import * as THREE from 'three';
import { createApp } from './src/render/App.js';
import { ROUTE } from './src/site/route.js';
import { ENV_VOXEL as ENV, BEAM_TOP, BEAM_SEPARATION } from './src/site/layout.js';
import { TRAIN_LEN, VOXEL as HERO } from './src/gen/monorail.js';
import { Train } from './src/sim/Train.js';
import { People } from './src/sim/People.js';
import { Elevators, DeckCamera } from './src/sim/Elevator.js';

const app = await createApp({
  canvas: document.getElementById('c'),
  hud: document.getElementById('hud'),
});
window.seattle = app; // console: seattle.setColor('needle_gold', '#ffb020', { metal: 1 })

const sunSlider = document.getElementById('sun');
const azSlider = document.getElementById('azimuth');
const applySun = () => app.setSun(+sunSlider.value, +azSlider.value);
sunSlider.addEventListener('input', applySun);
azSlider.addEventListener('input', applySun);

await app.ready;

// --- Monorail shuttle: stops at the Seattle Center platform and the Westlake stub ---
const halfTrain = (TRAIN_LEN / 2) * HERO / ENV; // env voxels
const stationS = () => halfTrain + 4; // train centre when its nose is 2 m short of the bumper
const stopsFor = (spline) => [stationS(spline), spline.length - halfTrain - 6];
const red = new Train(app, ROUTE.red, { color: 'monorail_red', name: 'Red', stops: stopsFor(ROUTE.red), direction: 1 });
const blue = new Train(app, ROUTE.blue, { color: 'monorail_blue', name: 'Blue', stops: stopsFor(ROUTE.blue), direction: -1 });
blue.s = blue.stops[1]; blue.state = 'moving'; blue.direction = -1; blue.doorsOpen = false; blue.place(); // Blue starts leaving Westlake
app.trains = { red, blue };

// --- People: platform crowd + plaza wanderers ---
const pc = ROUTE.centre.pointAt(stationS(ROUTE.centre)), pt = ROUTE.centre.tangentAt(stationS(ROUTE.centre));
const platformY = (BEAM_TOP + 2) * ENV + 0.5; // slab top surface
const along = new THREE.Vector3(pt.x, 0, pt.z);
const platformCenter = new THREE.Vector3(pc.x * ENV, platformY, pc.z * ENV);
const stairs = platformCenter.clone().addScaledVector(along, -(stationS() * ENV) - 3); // bumper end, toward the Needle
const people = new People(app, {
  platform: { center: platformCenter, along, halfLen: 24, halfWidth: (BEAM_SEPARATION / 2 - 4) * ENV, y: platformY },
  plaza: { center: new THREE.Vector3(0, 0.5, 0), rMin: 14, rMax: 28 },
  stairs,
});
// Red's platform side: the platform lies between the beams, i.e. on Red's +z local side (east) and Blue's -z side.
red.on('doorsOpen', (t) => { if (t.s === t.stops[0]) people.onDoorsOpen(t, +1); });
blue.on('doorsOpen', (t) => { if (t.s === t.stops[0]) people.onDoorsOpen(t, -1); });

// --- Needle elevators + deck ---
const elevators = new Elevators(app);
const deck = new DeckCamera();

app.onFrame((dt) => {
  red.update(dt); blue.update(dt); people.update(dt); elevators.update(dt); deck.update(dt);
  app.status = `${red.statusText()} · ${blue.statusText()} · ${elevators.statusText()}`;
});

// --- Cameras ---
const modes = {
  orbit: { enter() { app.controls.enabled = true; } },
  red: { update() { follow(red.cameraPose()); } },
  blue: { update() { follow(blue.cameraPose()); } },
  chase: { update() { follow(red.chasePose()); } },
  platform: {
    enter() {
      // inner end of the platform, eye height, looking out along it toward the bumper and the Needle
      app.camera.position.copy(platformCenter).addScaledVector(along, 24).add(new THREE.Vector3(0, 1.7, 0));
      app.controls.target.copy(platformCenter).addScaledVector(along, -12).add(new THREE.Vector3(0, 1.4, 0));
      app.controls.enabled = true;
    },
  },
  elevator: { update() { follow(elevators.cameraPose(), 1); } },
  deck: { update() { follow(deck.cameraPose(), 1); } },
};
let mode = 'orbit';
function follow({ position, lookAt }, alpha = 0.5) {
  app.camera.position.lerp(position, alpha);
  app.camera.lookAt(lookAt);
}
function setMode(m) {
  mode = m;
  app.controls.enabled = false;
  fly = false;
  modes[m].enter?.();
  document.querySelectorAll('[data-cam]').forEach((b) => b.classList.toggle('active', b.dataset.cam === m));
  document.getElementById('mode').textContent = m.toUpperCase();
}
app.onFrame(() => { if (!fly) modes[mode].update?.(); });
document.querySelectorAll('[data-cam]').forEach((b) => b.addEventListener('click', () => setMode(b.dataset.cam)));
window.addEventListener('keydown', (e) => {
  const keys = { Digit1: 'orbit', Digit2: 'red', Digit3: 'blue', Digit4: 'chase', Digit5: 'platform', Digit6: 'elevator', Digit7: 'deck' };
  if (keys[e.code]) setMode(keys[e.code]);
});

// Simple free-fly (F to toggle): WASD move, Q/E down/up, drag to look.
let fly = false;
const keys = new Set();
window.addEventListener('keydown', (e) => {
  if (e.code === 'KeyF') { fly = !fly; app.controls.enabled = !fly && mode === 'orbit'; document.getElementById('mode').textContent = fly ? 'FLY (F)' : mode.toUpperCase(); }
  keys.add(e.code);
});
window.addEventListener('keyup', (e) => keys.delete(e.code));
let dragging = false, yaw = 0, pitch = 0;
window.addEventListener('pointerdown', (e) => { if (fly && e.target.id === 'c') dragging = true; });
window.addEventListener('pointerup', () => (dragging = false));
window.addEventListener('pointermove', (e) => {
  if (!fly || !dragging) return;
  yaw -= e.movementX * 0.003; pitch -= e.movementY * 0.003;
  pitch = Math.max(-1.5, Math.min(1.5, pitch));
});
app.onFrame((dt) => {
  if (!fly) return;
  const cam = app.camera;
  cam.rotation.set(pitch, yaw, 0, 'YXZ');
  const speed = (keys.has('ShiftLeft') ? 120 : 40) * dt;
  const dir = { x: 0, y: 0, z: 0 };
  if (keys.has('KeyW')) dir.z -= 1; if (keys.has('KeyS')) dir.z += 1;
  if (keys.has('KeyA')) dir.x -= 1; if (keys.has('KeyD')) dir.x += 1;
  if (keys.has('KeyE')) dir.y += 1; if (keys.has('KeyQ')) dir.y -= 1;
  cam.translateX(dir.x * speed); cam.translateY(dir.y * speed); cam.translateZ(dir.z * speed);
  app.controls.target.copy(cam.position).add(cam.getWorldDirection(new THREE.Vector3()).multiplyScalar(30));
});
