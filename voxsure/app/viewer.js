import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

let scene, camera, renderer, controls;
let meshBaseline, meshDamage;
const VOXEL_SIZE = 0.8;

export function initViewer() {
    const canvas = document.querySelector('#vox-canvas');
    const container = canvas.parentElement;

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(50, 50, 50);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));

    const p1 = new THREE.PointLight(0x00f2ff, 1.5, 200);
    p1.position.set(100, 100, 100);
    scene.add(p1);

    const grid = new THREE.GridHelper(200, 40, 0x444444, 0x222222);
    scene.add(grid);

    window.addEventListener('resize', onWindowResize);
    animate();
}

function onWindowResize() {
    const container = document.querySelector('#viewer-container');
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

export function displayVoxels(voxelData) {
    // Clear everything for a fresh scan
    if (meshBaseline) scene.remove(meshBaseline);
    if (meshDamage) scene.remove(meshDamage);

    meshBaseline = createInstancedMesh(voxelData.voxels, 1.0);
    if (meshBaseline) {
        scene.add(meshBaseline);
        focusCamera(meshBaseline);
    }
}

export function displayComparison(compData) {
    if (meshBaseline) scene.remove(meshBaseline);
    if (meshDamage) scene.remove(meshDamage);

    const baselineVoxels = compData.voxels.filter(v => v.status !== 'added');
    const damageVoxels = compData.voxels.filter(v => v.status !== 'match');

    // Baseline is the "ghost" (muted or lost)
    meshBaseline = createInstancedMesh(baselineVoxels, 0.2); // Faint ghost

    // Damage is the "active" forensic layer (added territory)
    meshDamage = createInstancedMesh(damageVoxels, 1.0);

    if (meshBaseline) scene.add(meshBaseline);
    if (meshDamage) {
        // High-contrast highlighting for forensic damage
        meshDamage.material.emissive = new THREE.Color(0xff3333);
        meshDamage.material.emissiveIntensity = 0.4;
        scene.add(meshDamage);
    }

    // Focus on whichever is available, preferably baseline
    if (meshBaseline) focusCamera(meshBaseline);
    else if (meshDamage) focusCamera(meshDamage);
}

export function setLayerVisibility(type, visible) {
    if (type === 'baseline' && meshBaseline) meshBaseline.visible = visible;
    if (type === 'damage' && meshDamage) meshDamage.visible = visible;
}

function createInstancedMesh(voxels, opacity) {
    if (!voxels || voxels.length === 0) return null;

    const geometry = new THREE.BoxGeometry(VOXEL_SIZE, VOXEL_SIZE, VOXEL_SIZE);
    const material = new THREE.MeshPhongMaterial({
        transparent: opacity < 1,
        opacity: opacity
    });

    const mesh = new THREE.InstancedMesh(geometry, material, voxels.length);
    const dummy = new THREE.Object3D();
    const color = new THREE.Color();

    voxels.forEach((v, i) => {
        dummy.position.set(v.pos[0], v.pos[2] + VOXEL_SIZE / 2, v.pos[1]);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);

        color.set(v.color);
        mesh.setColorAt(i, color);
    });

    if (mesh.instanceMatrix) mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    return mesh;
}

function focusCamera(mesh) {
    if (!mesh) return;
    const box = new THREE.Box3().setFromObject(mesh);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    controls.target.copy(center);
    camera.position.set(center.x + size.x * 2, center.y + size.y * 2, center.z + size.z * 2);
}
