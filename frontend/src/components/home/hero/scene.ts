/**
 * Scene geometry shared by the first (server) render and the animation loop, so both always
 * agree. Everything turns around one vertical axis at x = CX: the podium details and both
 * figures are projected from the same yaw angle.
 */

export const CX = 320;

export interface Tier {
  cy: number;
  rx: number;
  ry: number;
  h: number;
}

// Bottom → top. Each tier's base sits exactly on the surface of the tier below it.
export const BASE: Tier = { cy: 554, rx: 266, ry: 51, h: 30 };
export const MID: Tier = { cy: 532, rx: 226, ry: 43, h: 22 };
export const TOP: Tier = { cy: 506, rx: 186, ry: 35, h: 26 };

export const sidePath = (t: Tier) =>
  `M${CX - t.rx} ${t.cy} A${t.rx} ${t.ry} 0 0 0 ${CX + t.rx} ${t.cy} L${CX + t.rx} ${t.cy + t.h} A${t.rx} ${t.ry} 0 0 1 ${CX - t.rx} ${t.cy + t.h} Z`;

/** Point on a tier's surface ring (fraction `r` of its radius) at angle `phi` (0 = front). */
export function surfacePoint(t: Tier, r: number, phi: number) {
  const c = Math.cos(phi);
  return { x: CX + t.rx * r * Math.sin(phi), y: t.cy + t.ry * r * c, depth: c };
}

/** Vertical flute on a tier's side wall; only the front half is visible. */
export function flute(t: Tier, phi: number) {
  const p = surfacePoint(t, 1, phi);
  return { x: p.x, y1: p.y + 2, y2: p.y + t.h - 2, opacity: p.depth > 0 ? p.depth * 0.45 : 0 };
}

/** Rivet on a tier's side wall (mid-height). */
export function rivet(t: Tier, phi: number) {
  const p = surfacePoint(t, 1, phi);
  return { x: p.x, y: p.y + t.h / 2, opacity: p.depth > 0.05 ? 0.35 + 0.65 * p.depth : 0 };
}

// --- Figures --------------------------------------------------------------------------------

/** Distance of each figure from the podium axis. */
export const ORBIT = 64;

export interface FigurePose {
  transform: string;
  frontOpacity: number;
  backOpacity: number;
  depth: number;
}

const smoothstep = (a: number, b: number, v: number) => {
  const t = Math.max(0, Math.min(1, (v - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/**
 * Pose of a figure standing `ORBIT` from the axis at `base` (−π/2 = left, +π/2 = right) when the
 * display has turned by `yaw`. The figure orbits the axis, its feet stay on the top surface, it
 * narrows as it turns side-on and swaps to its back artwork while facing away.
 */
export function figurePose(base: number, yaw: number): FigurePose {
  const p = surfacePoint(TOP, ORBIT / TOP.rx, yaw + base);
  const facing = Math.cos(yaw);
  const width = 0.42 + 0.58 * Math.abs(facing);
  const scale = 1 + 0.035 * p.depth;
  const front = smoothstep(-0.14, 0.14, facing);
  return {
    transform: `translate(${p.x.toFixed(2)} ${p.y.toFixed(2)}) scale(${(width * scale).toFixed(4)} ${scale.toFixed(4)})`,
    frontOpacity: front,
    backOpacity: 1 - front,
    depth: p.depth,
  };
}

export const GIRL_BASE = -Math.PI / 2;
export const BOY_BASE = Math.PI / 2;
