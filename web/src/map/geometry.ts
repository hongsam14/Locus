// Map coordinates (V2 FR-D6, BLM § 8.1, BR-V2-18). Regions are stored normalized (0..1);
// the map draws them in map units (1000 × 625, 8:5) and the SVG fits its container with
// `xMidYMid meet`. A pointer is turned back into 0..1 through the inverse of the screen
// matrix, so the map can shrink without the clicks and drags going off.

export type Norm = { x: number; y: number };
export type Point = { x: number; y: number };
export type ViewBox = { x: number; y: number; w: number; h: number };
/** A 2D affine matrix in DOMMatrix form: x' = a·x + c·y + e, y' = b·x + d·y + f. */
export type Matrix = { a: number; b: number; c: number; d: number; e: number; f: number };

export const MAP_EXTENT: ViewBox = { x: 0, y: 0, w: 1000, h: 625 };

export function applyMatrix(m: Matrix, p: Point): Point {
  return { x: m.a * p.x + m.c * p.y + m.e, y: m.b * p.x + m.d * p.y + m.f };
}

export function invert(m: Matrix): Matrix {
  const det = m.a * m.d - m.b * m.c;
  return {
    a: m.d / det,
    b: -m.b / det,
    c: -m.c / det,
    d: m.a / det,
    e: (m.c * m.f - m.d * m.e) / det,
    f: (m.b * m.e - m.a * m.f) / det,
  };
}

/** A screen point as a normalized map coordinate. `inverse` maps screen → map units. */
export function normalizeFromMatrix(client: Point, inverse: Matrix, extent: ViewBox = MAP_EXTENT): Norm {
  const p = applyMatrix(inverse, client);
  return { x: (p.x - extent.x) / extent.w, y: (p.y - extent.y) / extent.h };
}

/** The inverse of `normalizeFromMatrix`: a normalized coordinate on screen. */
export function toClient(p: Norm, matrix: Matrix, extent: ViewBox = MAP_EXTENT): Point {
  return applyMatrix(matrix, { x: extent.x + p.x * extent.w, y: extent.y + p.y * extent.h });
}

/** The screen matrix of a `viewBox` drawn into `rect` with `xMidYMid meet` — used where the
 * browser gives no `getScreenCTM` (jsdom, not yet laid out). */
export function meetMatrix(
  rect: { left: number; top: number; width: number; height: number },
  viewBox: ViewBox,
): Matrix {
  const s = Math.min(rect.width / viewBox.w, rect.height / viewBox.h);
  const e = rect.left + (rect.width - viewBox.w * s) / 2 - viewBox.x * s;
  const f = rect.top + (rect.height - viewBox.h * s) / 2 - viewBox.y * s;
  return { a: s, b: 0, c: 0, d: s, e, f };
}

export function inside(p: Norm): boolean {
  return p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1;
}

export function clampNorm(p: Norm): Norm {
  return { x: Math.min(1, Math.max(0, p.x)), y: Math.min(1, Math.max(0, p.y)) };
}

/** A normalized coordinate in pixels of a canvas. Pure. */
export function toPixels(c: Norm, width: number, height: number) {
  return { px: c.x * width, py: c.y * height };
}
