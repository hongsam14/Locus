export interface EdgeStyle {
  width: number;
  opacity: number;
  color: string;
  dashed: boolean;
}

/** Connection visual style from kind + weight (BR-U10-2). Pure. */
export function edgeStyle(kind: string, weight: number): EdgeStyle {
  const blocked = kind === "blocked";
  return {
    width: 1 + weight * 4,
    opacity: 0.3 + weight * 0.7,
    color: blocked ? "#c0392b" : "#34495e",
    dashed: blocked,
  };
}

/** Map a normalized coord to pixel space given a canvas size. Pure. */
export function toPixels(c: { x: number; y: number }, width: number, height: number) {
  return { px: c.x * width, py: c.y * height };
}
