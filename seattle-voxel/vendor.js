// Copies the pinned Three.js build + the few addons the page uses into
// ../dashboard/seattle/vendor/three/ so the site serves them itself (no CDN).
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, 'node_modules/three');
const dst = join(here, '../dashboard/seattle/vendor/three');

const files = [
  ['build/three.module.js', 'three.module.js'],
  ['build/three.core.js', 'three.core.js'], // three.module.js imports this sibling since r170
  ['examples/jsm/controls/OrbitControls.js', 'addons/controls/OrbitControls.js'],
  ['examples/jsm/objects/Sky.js', 'addons/objects/Sky.js'],
  ['examples/jsm/libs/stats.module.js', 'addons/libs/stats.module.js'],
];

for (const [from, to] of files) {
  mkdirSync(dirname(join(dst, to)), { recursive: true });
  copyFileSync(join(src, from), join(dst, to));
  console.log('vendored', to);
}
