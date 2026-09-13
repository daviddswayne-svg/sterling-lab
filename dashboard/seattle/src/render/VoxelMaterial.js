// One material for the whole world. Vertices carry a palette index + AO;
// color and metal/rough/emissive come from two 256×1 palette textures, so
// tuning a color or a shine is a texture update, never a rebake.
import * as THREE from 'three';
import { FLAG_FRESNEL_BLUE, FLAG_NO_JITTER, FLAG_GLASS } from '../voxel/Palette.js';

export class PaletteTextures {
  constructor(palette) {
    this.palette = palette;
    this.colorData = new Uint8Array(256 * 4);
    this.matData = new Uint8Array(256 * 4);
    this.color = new THREE.DataTexture(this.colorData, 256, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
    this.color.colorSpace = THREE.SRGBColorSpace;
    this.mat = new THREE.DataTexture(this.matData, 256, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
    for (const t of [this.color, this.mat]) {
      t.magFilter = t.minFilter = THREE.NearestFilter;
      t.generateMipmaps = false;
    }
    this.refresh();
  }

  refresh() {
    this.palette.entries.forEach((e, i) => {
      this.colorData.set([e.r, e.g, e.b, 255], i * 4);
      this.matData.set([Math.round(e.metal * 255), Math.round(e.rough * 255), Math.round(e.emissive * 255), e.flags], i * 4);
    });
    this.color.needsUpdate = true;
    this.mat.needsUpdate = true;
  }

  // Live edit: seattle.setColor('mopop_blue', '#3344ff', { metal: 0.9 })
  set(name, hex, props = {}) {
    const idx = this.palette.index(name);
    const e = this.palette.entries[idx];
    if (hex) {
      const n = parseInt(hex.replace('#', ''), 16);
      e.r = (n >> 16) & 255; e.g = (n >> 8) & 255; e.b = n & 255;
    }
    Object.assign(e, props);
    this.refresh();
  }
}

const vertexHead = /* glsl */ `
  attribute float palette;
  attribute float ao;
  varying float vPal;
  varying float vAo;
  varying vec3 vWorldPos;
  varying vec3 vWorldNormal;
`;
const vertexBody = /* glsl */ `
  vPal = palette;
  vAo = ao;
  vWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
  vWorldNormal = normalize(mat3(modelMatrix) * objectNormal);
`;
const fragHead = /* glsl */ `
  uniform sampler2D paletteTex;
  uniform sampler2D matTex;
  uniform float voxelSize;
  uniform float jitterAmount;
  uniform float aoStrength;
  varying float vPal;
  varying float vAo;
  varying vec3 vWorldPos;
  varying vec3 vWorldNormal;
  vec4 palMat;
  float hash13(vec3 p) {
    p = fract(p * 0.1031);
    p += dot(p, p.zyx + 31.32);
    return fract((p.x + p.y) * p.z);
  }
`;
const fragColor = /* glsl */ `
  {
    vec2 uv = vec2((vPal + 0.5) / 256.0, 0.5);
    vec4 pc = texture2D(paletteTex, uv);
    palMat = texture2D(matTex, uv);
    diffuseColor.rgb = pc.rgb;
    int flags = int(palMat.a * 255.0 + 0.5);
    // per-voxel grain: hash the cell this face belongs to (step back off the face plane)
    if ((flags & ${FLAG_NO_JITTER}) == 0) {
      vec3 cell = floor((vWorldPos - vWorldNormal * voxelSize * 0.5) / voxelSize);
      float h = hash13(cell) - 0.5;
      diffuseColor.rgb *= 1.0 + h * jitterAmount;
    }
    // baked ambient occlusion (0..3)
    float aoT = vAo / 3.0;
    diffuseColor.rgb *= mix(1.0 - aoStrength, 1.0, aoT * aoT * (3.0 - 2.0 * aoT));
  }
`;
const fragRough = /* glsl */ `roughnessFactor = palMat.g;`;
const fragMetal = /* glsl */ `metalnessFactor = palMat.r;`;
const fragEmissive = /* glsl */ `
  {
    int flags = int(palMat.a * 255.0 + 0.5);
    if ((flags & ${FLAG_FRESNEL_BLUE}) != 0) {
      vec3 viewDir = normalize(cameraPosition - vWorldPos);
      float fr = pow(1.0 - max(dot(normalize(vWorldNormal), viewDir), 0.0), 2.5);
      vec3 shifted = diffuseColor.rgb * vec3(1.35, 0.65, 1.25); // toward violet
      diffuseColor.rgb = mix(diffuseColor.rgb, shifted, fr * 0.8);
    }
    totalEmissiveRadiance = diffuseColor.rgb * palMat.b * 3.0;
  }
`;

function patch(material, textures, voxelSize) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.paletteTex = { value: textures.color };
    shader.uniforms.matTex = { value: textures.mat };
    shader.uniforms.voxelSize = { value: voxelSize };
    shader.uniforms.jitterAmount = { value: 0.08 };
    shader.uniforms.aoStrength = { value: 0.55 };
    material.userData.shader = shader;

    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\n' + vertexHead)
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\n' + vertexBody);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\n' + fragHead)
      .replace('#include <color_fragment>', '#include <color_fragment>\n' + fragColor)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n' + fragRough)
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\n' + fragMetal)
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + fragEmissive);
  };
  // Distinct cache key so the patched program is not shared with plain materials.
  material.customProgramCacheKey = () => 'voxel-' + (material.transparent ? 'glass' : 'opaque');
  return material;
}

export function createVoxelMaterials(textures, voxelSize) {
  const opaque = patch(new THREE.MeshStandardMaterial({ roughness: 1, metalness: 0, envMapIntensity: 0.6 }), textures, voxelSize);
  const glass = patch(new THREE.MeshPhysicalMaterial({
    roughness: 0.1, metalness: 0.1, transparent: true, opacity: 0.45, depthWrite: false,
    side: THREE.DoubleSide, envMapIntensity: 1.4,
  }), textures, voxelSize);
  return { opaque, glass };
}

export const isGlassFlag = (flags) => (flags & FLAG_GLASS) !== 0;
