// Scene bootstrap shared by index.html and me.html: renderer, sky, sun with a
// camera-following shadow frustum, controls, and streaming world load via a
// worker pool (nearest chunks first). Loads any number of world files — the
// 0.5 m environment layer and the 0.25 m hero layer — each with its own
// material pair (same palette, different voxelSize).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Sky } from 'three/addons/objects/Sky.js';
import Stats from 'three/addons/libs/stats.module.js';
import { decodeWorld } from '../voxel/WorldFormat.js';
import { CHUNK, unpackKey } from '../voxel/Grid.js';
import { PaletteTextures, createVoxelMaterials } from './VoxelMaterial.js';
import { buildChunkMeshes, mergeBuffers } from './ChunkMesh.js';

// Static chunks are merged into REGION³-chunk regions so the world is a few
// dozen draw calls instead of one per 32³ chunk.
const REGION = 12; // 384 voxels = 192 m at 0.5 m; keeps the site under ~30 regions

export async function createApp({ canvas, hud, worldUrls = ['./world.bin', './detail.bin'] }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.55;

  const scene = new THREE.Scene();
  // The Preetham sky is very bright as an environment map; without this the
  // ambient term drowns the sun and every face reads the same brightness.
  scene.environmentIntensity = 0.15;
  scene.fog = new THREE.Fog(0xc9daea, 700, 2600);

  const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.5, 6000);
  camera.position.set(190, 110, 230);

  const controls = new OrbitControls(camera, canvas);
  controls.target.set(0, 70, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 2;
  controls.maxDistance = 1800;
  controls.maxPolarAngle = Math.PI / 2 + 0.05;
  controls.update();

  // --- Sky + sun ---
  const sky = new Sky();
  sky.scale.setScalar(50000);
  scene.add(sky);
  const su = sky.material.uniforms;
  su.turbidity.value = 6;
  su.rayleigh.value = 2.4;
  su.mieCoefficient.value = 0.006;
  su.mieDirectionalG.value = 0.85;

  const sun = new THREE.DirectionalLight(0xfff2dc, 3.2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096);
  sun.shadow.bias = -0.0003;
  sun.shadow.normalBias = 0.6;
  sun.shadow.radius = 2;
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 2500;
  scene.add(sun);
  scene.add(sun.target);

  const hemi = new THREE.HemisphereLight(0xbfd8f5, 0x6f6a5c, 0.55);
  scene.add(hemi);

  const sunDir = new THREE.Vector3();
  const pmrem = new THREE.PMREMGenerator(renderer);
  let envTarget = null;
  function setSun(elevationDeg, azimuthDeg) {
    const phi = THREE.MathUtils.degToRad(90 - elevationDeg);
    const theta = THREE.MathUtils.degToRad(azimuthDeg);
    sunDir.setFromSphericalCoords(1, phi, theta);
    su.sunPosition.value.copy(sunDir);
    const warm = THREE.MathUtils.clamp(elevationDeg / 35, 0, 1);
    sun.color.setRGB(1, 0.78 + 0.17 * warm, 0.55 + 0.35 * warm);
    sun.intensity = 1.0 + 1.6 * Math.min(1, elevationDeg / 25);
    hemi.intensity = 0.12 + 0.13 * warm;
    if (envTarget) envTarget.dispose();
    envTarget = pmrem.fromScene(sky, 0.02);
    scene.environment = envTarget.texture;
    app.sun = { elevation: elevationDeg, azimuth: azimuthDeg };
  }

  // Keep the shadow frustum tight around whatever the camera is looking at.
  const tmp = new THREE.Vector3();
  function updateShadowFrustum() {
    // POV modes keep the orbit target under the camera so the shadow frustum follows.
    if (!controls.enabled) controls.target.copy(camera.position).add(camera.getWorldDirection(tmp).multiplyScalar(40));
    const dist = camera.position.distanceTo(controls.target);
    const size = THREE.MathUtils.clamp(dist * 1.1, 40, 700);
    const cam = sun.shadow.camera;
    cam.left = -size; cam.right = size; cam.top = size; cam.bottom = -size;
    cam.updateProjectionMatrix();
    sun.target.position.copy(controls.target);
    tmp.copy(sunDir).multiplyScalar(900).add(controls.target);
    sun.position.copy(tmp);
  }

  // --- HUD ---
  const stats = new Stats();
  stats.dom.style.cssText = 'position:absolute;top:8px;left:8px;';
  if (hud) hud.appendChild(stats.dom);
  const info = document.createElement('div');
  info.className = 'hud-info';
  if (hud) hud.appendChild(info);
  const progress = document.createElement('div');
  progress.className = 'hud-progress';
  progress.innerHTML = '<div class="bar"></div><span></span>';
  if (hud) hud.appendChild(progress);

  const app = {
    renderer, scene, camera, controls, sun: null, sunLight: sun,
    palette: null, textures: null, materialsBySize: new Map(), worlds: [],
    chunks: new Map(), triangles: 0, worldBytes: 0,
    frameCallbacks: [],
    setSun,
    onFrame(cb) { this.frameCallbacks.push(cb); },
    setColor(name, hex, props) { this.textures.set(name, hex, props); },
    // Materials for a voxel size — dynamic objects ask for theirs here.
    materialsFor(voxelSize) {
      let m = this.materialsBySize.get(voxelSize);
      if (!m) { m = createVoxelMaterials(this.textures, voxelSize); this.materialsBySize.set(voxelSize, m); }
      return m;
    },
    ready: null,
  };

  // --- World load + streaming mesh ---
  app.ready = (async () => {
    const t0 = performance.now();
    const jobs = []; // { fileIdx, key, grid, flags, voxelSize, center }
    for (const url of worldUrls) {
      const res = await fetch(url, { cache: 'no-cache' });
      if (!res.ok) { console.warn('world file missing', url); continue; }
      const bytes = new Uint8Array(await res.arrayBuffer());
      app.worldBytes += bytes.length;
      const { grid, palette, voxelSize } = await decodeWorld(bytes);
      if (!app.palette) {
        app.palette = palette;
        app.textures = new PaletteTextures(palette);
      }
      const fileIdx = app.worlds.length;
      app.worlds.push({ url, grid, voxelSize, flags: palette.flagsArray() });
      for (const key of grid.chunks.keys()) {
        const [cx, cy, cz] = unpackKey(key);
        jobs.push({
          fileIdx, key, voxelSize,
          center: new THREE.Vector3((cx + 0.5) * CHUNK * voxelSize, (cy + 0.5) * CHUNK * voxelSize, (cz + 0.5) * CHUNK * voxelSize),
        });
      }
    }
    app.grid = app.worlds[0]?.grid;
    app.voxelSize = app.worlds[0]?.voxelSize ?? 0.5;
    const total = jobs.length;
    jobs.sort((a, b) => a.center.distanceTo(controls.target) - b.center.distanceTo(controls.target));

    // region bookkeeping: how many chunks each region expects, and what has arrived
    const regionOf = (job) => {
      const [cx, cy, cz] = unpackKey(job.key);
      // +1 on y so the ground slab (chunk row -1) shares a region with what stands on it
      return `${job.fileIdx}:${Math.floor(cx / REGION)},${Math.floor((cy + 1) / REGION)},${Math.floor(cz / REGION)}`;
    };
    const expected = new Map();
    for (const j of jobs) expected.set(regionOf(j), (expected.get(regionOf(j)) || 0) + 1);
    const arrived = new Map();
    const flushRegion = (rk, voxelSize) => {
      const parts = arrived.get(rk);
      const merged = { opaque: mergeBuffers(parts.map((p) => p.opaque)), glass: mergeBuffers(parts.map((p) => p.glass)) };
      const meshes = buildChunkMeshes(merged, app.materialsFor(voxelSize));
      if (meshes.opaque) scene.add(meshes.opaque);
      if (meshes.glass) scene.add(meshes.glass);
      app.chunks.set(rk, meshes);
      app.triangles += meshes.triangles;
      arrived.delete(rk);
    };

    const nWorkers = Math.max(1, Math.min(8, (navigator.hardwareConcurrency || 4) - 1));
    const workers = Array.from({ length: nWorkers }, () => new Worker(new URL('../voxel/mesh.worker.js', import.meta.url), { type: 'module' }));
    let done = 0, next = 0;
    const meshedAt = performance.now();
    const inflight = new Map(); // worker → job

    await new Promise((resolve) => {
      if (!total) return resolve();
      const dispatch = (w) => {
        if (next >= total) return;
        const job = jobs[next++];
        const world = app.worlds[job.fileIdx];
        const [cx, cy, cz] = unpackKey(job.key);
        const apron = world.grid.extractWithApron(cx, cy, cz);
        inflight.set(w, job);
        w.postMessage({ id: job.key, apron, flags: world.flags, origin: [cx * CHUNK, cy * CHUNK, cz * CHUNK], voxelSize: world.voxelSize }, [apron.buffer]);
      };
      workers.forEach((w) => {
        w.onmessage = (e) => {
          const job = inflight.get(w);
          const rk = regionOf(job);
          if (!arrived.has(rk)) arrived.set(rk, []);
          arrived.get(rk).push(e.data);
          if (arrived.get(rk).length === expected.get(rk)) flushRegion(rk, job.voxelSize);
          done++;
          progress.querySelector('.bar').style.width = `${(100 * done) / total}%`;
          progress.querySelector('span').textContent = `meshing ${done}/${total}`;
          if (done === total) {
            progress.classList.add('done');
            workers.forEach((x) => x.terminate());
            app.loadMs = performance.now() - t0;
            app.meshMs = performance.now() - meshedAt;
            resolve();
          } else dispatch(w);
        };
        dispatch(w);
      });
    });
    return app;
  })();

  // --- Frame loop ---
  const timer = new THREE.Timer();
  let frames = 0;
  function frame(ts) {
    requestAnimationFrame(frame);
    timer.update(ts);
    const dt = Math.min(timer.getDelta(), 0.1);
    // OrbitControls.update() moves the camera even when input is disabled, so
    // only run it in orbit-style modes; POV cameras own the camera outright.
    if (controls.enabled) controls.update();
    updateShadowFrustum();
    for (const cb of app.frameCallbacks) cb(dt);
    renderer.render(scene, camera);
    stats.update();
    if (++frames % 20 === 0) {
      const r = renderer.info.render;
      info.textContent =
        `${r.calls} draw calls · ${(r.triangles / 1000).toFixed(0)}k tris · ${app.chunks.size} regions` +
        (app.loadMs ? ` · world ${(app.worldBytes / 1024).toFixed(0)} KB · load ${app.loadMs.toFixed(0)} ms (mesh ${app.meshMs.toFixed(0)} ms)` : '') +
        (app.status ? ` · ${app.status}` : '');
    }
  }

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  setSun(38, 155);
  frame();
  return app;
}
