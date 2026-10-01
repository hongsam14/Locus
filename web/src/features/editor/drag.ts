// U3 (Q5=A, BR-U3-30): a press only counts as a drag past a few pixels, so clicking a
// region never saves its position (B7). Pure, so the rule is tested without a browser.

export const DRAG_PX = 4;

export interface Point {
  x: number;
  y: number;
}

/** Whether the pointer moved far enough (screen pixels) to be a drag. */
export function isDrag(start: Point, end: Point, threshold = DRAG_PX): boolean {
  return Math.hypot(end.x - start.x, end.y - start.y) > threshold;
}

/** A pointer position as a normalized map coordinate (0..1 on each axis). */
export function toNorm(
  e: { clientX: number; clientY: number },
  rect: { left: number; top: number; width: number; height: number } | undefined,
): Point {
  if (!rect || rect.width <= 0 || rect.height <= 0) return { x: 0.5, y: 0.5 };
  return {
    x: Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)),
    y: Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height)),
  };
}
