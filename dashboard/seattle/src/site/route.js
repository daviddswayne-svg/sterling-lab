// Monorail route as an arc-length-parameterised Catmull-Rom spline.
// Dependency-free so the Node bake and the browser share it exactly.
import { ROUTE_POINTS, BEAM_TOP, BEAM_SEPARATION } from './layout.js';

export class Spline {
  /** pts: [[x, z], …] in the horizontal plane (y is constant per route) */
  constructor(pts, y = 0, samplesPerSeg = 32) {
    this.pts = pts;
    this.y = y;
    // Build a dense polyline + cumulative arc length
    const poly = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      for (let s = 0; s < samplesPerSeg; s++) {
        const t = s / samplesPerSeg;
        poly.push([cr(p0[0], p1[0], p2[0], p3[0], t), cr(p0[1], p1[1], p2[1], p3[1], t)]);
      }
    }
    poly.push(pts[pts.length - 1]);
    this.poly = poly;
    this.cum = [0];
    for (let i = 1; i < poly.length; i++) this.cum.push(this.cum[i - 1] + Math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1]));
    this.length = this.cum[this.cum.length - 1];
  }

  /** point at arc length s (clamped) → { x, y, z } */
  pointAt(s) {
    s = Math.min(Math.max(s, 0), this.length);
    let lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (this.cum[mid] <= s) lo = mid; else hi = mid; }
    const seg = this.cum[hi] - this.cum[lo] || 1;
    const t = (s - this.cum[lo]) / seg;
    const a = this.poly[lo], b = this.poly[hi];
    return { x: a[0] + (b[0] - a[0]) * t, y: this.y, z: a[1] + (b[1] - a[1]) * t };
  }

  /** unit tangent at arc length s → { x, z } */
  tangentAt(s) {
    const d = 0.5;
    const a = this.pointAt(Math.max(0, s - d)), b = this.pointAt(Math.min(this.length, s + d));
    const len = Math.hypot(b.x - a.x, b.z - a.z) || 1;
    return { x: (b.x - a.x) / len, z: (b.z - a.z) / len };
  }

  /** arc length of the closest polyline vertex to (x, z) — good enough for station stops */
  nearest(x, z) {
    let best = 0, bd = Infinity;
    for (let i = 0; i < this.poly.length; i++) {
      const d = (this.poly[i][0] - x) ** 2 + (this.poly[i][1] - z) ** 2;
      if (d < bd) { bd = d; best = i; }
    }
    return this.cum[best];
  }

  /** a parallel copy offset laterally by `off` (positive = right of travel direction) */
  offset(off) {
    const pts = [];
    for (let i = 0; i < this.pts.length; i++) {
      const s = this.cum[Math.min(i * 32, this.cum.length - 1)];
      const t = this.tangentAt(s);
      pts.push([this.pts[i][0] - t.z * off, this.pts[i][1] + t.x * off]);
    }
    return new Spline(pts, this.y);
  }
}

function cr(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t;
  return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
}

// The two beams, in environment voxels (0.5 m). Red = west beam, Blue = east.
const centre = new Spline(ROUTE_POINTS, BEAM_TOP);
export const ROUTE = {
  centre,
  red: centre.offset(-BEAM_SEPARATION / 2),
  blue: centre.offset(BEAM_SEPARATION / 2),
};
