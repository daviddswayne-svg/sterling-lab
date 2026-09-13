// "2D me": webcam → MediaPipe person mask → unlit billboard in the voxel
// world that still casts a real shadow. Attach to any app from App.js.
import * as THREE from 'three';

const MP_VERSION = '0.10.21';
const MP_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}`;
const MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite';

export function createMeLayer(app, { seats, onStatus = () => {} }) {
  const video = document.createElement('video');
  video.playsInline = true; video.muted = true;
  let w = 1280, h = 720;

  const maskCanvas = document.createElement('canvas');
  const outCanvas = document.createElement('canvas');
  const mctx = maskCanvas.getContext('2d', { willReadFrequently: true });
  const octx = outCanvas.getContext('2d');
  let maskImage = null;

  const texture = new THREE.CanvasTexture(outCanvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;

  const material = new THREE.MeshBasicMaterial({ map: texture, transparent: true, alphaTest: 0.5, side: THREE.DoubleSide, toneMapped: false });
  const geo = new THREE.PlaneGeometry(1, 1);
  geo.translate(0, 0.5, 0); // anchor at the feet
  const mesh = new THREE.Mesh(geo, material);
  mesh.castShadow = true;
  mesh.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: texture, alphaTest: 0.5 });
  mesh.visible = false;
  app.scene.add(mesh);

  const state = { frameHeight: 2.6, mirror: true, warmth: 0.25, brightness: 1.0, seat: null, segmenter: null, running: false };

  function applyLook() {
    const warm = new THREE.Color(1.0, 0.86, 0.68);
    material.color.copy(new THREE.Color(1, 1, 1).lerp(warm, state.warmth)).multiplyScalar(state.brightness);
    mesh.scale.set(state.frameHeight * (w / h), state.frameHeight, 1);
  }

  async function start() {
    onStatus('asking for the camera…');
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }, audio: false });
    video.srcObject = stream;
    await video.play();
    w = video.videoWidth; h = video.videoHeight;
    maskCanvas.width = outCanvas.width = w;
    maskCanvas.height = outCanvas.height = h;
    maskImage = mctx.createImageData(w, h);
    maskImage.data.fill(255);

    onStatus('loading segmenter…');
    const { ImageSegmenter, FilesetResolver } = await import(`${MP_URL}/vision_bundle.mjs`);
    const fileset = await FilesetResolver.forVisionTasks(`${MP_URL}/wasm`);
    state.segmenter = await ImageSegmenter.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: MODEL_URL, delegate: 'GPU' },
      runningMode: 'VIDEO',
      outputCategoryMask: false,
      outputConfidenceMasks: true,
    });
    state.running = true;
    mesh.visible = true;
    applyLook();
    onStatus('live');
    segmentLoop();
  }

  let lastTs = -1;
  function segmentLoop() {
    if (!state.running) return;
    const ts = performance.now();
    if (video.readyState >= 2 && ts !== lastTs) {
      lastTs = ts;
      state.segmenter.segmentForVideo(video, ts, (result) => {
        const mask = result.confidenceMasks?.[0];
        if (!mask) return;
        const conf = mask.getAsFloat32Array();
        const data = maskImage.data;
        for (let i = 0, j = 3; i < conf.length; i++, j += 4) data[j] = conf[i] * 255;
        mctx.putImageData(maskImage, 0, 0);
        mask.close?.();

        octx.save();
        octx.clearRect(0, 0, w, h);
        if (state.mirror) { octx.translate(w, 0); octx.scale(-1, 1); }
        octx.drawImage(video, 0, 0, w, h);
        octx.globalCompositeOperation = 'destination-in';
        octx.filter = 'blur(2px)';
        octx.drawImage(maskCanvas, 0, 0);
        octx.restore();
        texture.needsUpdate = true;
      });
    }
    requestAnimationFrame(segmentLoop);
  }

  function setSeat(name) {
    const seat = seats.find((s) => s.name === name);
    if (!seat) return;
    state.seat = seat;
    mesh.position.copy(seat.position);
    // reframe the orbit camera on the seat
    app.controls.target.copy(seat.position).add(new THREE.Vector3(0, 1.0, 0));
    app.camera.position.copy(seat.position).add(seat.cameraOffset);
    app.controls.update();
  }

  // yaw-only billboard so he stays upright
  app.onFrame(() => {
    if (!mesh.visible) return;
    const c = app.camera.position;
    mesh.rotation.y = Math.atan2(c.x - mesh.position.x, c.z - mesh.position.z);
  });

  return {
    mesh, state, start, setSeat,
    set(props) { Object.assign(state, props); applyLook(); },
  };
}
