import * as THREE from 'three';
import { createApp } from './src/render/App.js';

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

// Simple free-fly (F to toggle): WASD move, Q/E down/up, drag to look.
let fly = false;
const keys = new Set();
window.addEventListener('keydown', (e) => {
  if (e.code === 'KeyF') { fly = !fly; app.controls.enabled = !fly; document.getElementById('mode').textContent = fly ? 'FLY (F)' : 'ORBIT (F)'; }
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
