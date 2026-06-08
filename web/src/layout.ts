import type { Coord, Region } from "./types";

/**
 * Returns a normalized {x,y} in [0,1] per region: uses region.position when set,
 * otherwise places regions on a circle (deterministic). Pure.
 */
export function autoLayout(regions: Region[]): Record<string, Coord> {
  const out: Record<string, Coord> = {};
  const missing: Region[] = [];
  for (const r of regions) {
    if (r.position && typeof r.position.x === "number" && typeof r.position.y === "number") {
      out[r.id] = { x: r.position.x, y: r.position.y };
    } else {
      missing.push(r);
    }
  }
  const n = missing.length;
  missing.forEach((r, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, n);
    out[r.id] = { x: 0.5 + 0.4 * Math.cos(angle), y: 0.5 + 0.4 * Math.sin(angle) };
  });
  return out;
}
