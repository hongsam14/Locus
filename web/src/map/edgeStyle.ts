// How a connection is drawn (V2 FR-D7, BLM § 8.4): the kind sets the line, the weight its
// strength. Colours are token variables (FR-D2), resolved through `style`, not attributes.
import type { ConnectionEdge } from "../types";

export interface EdgeStyle {
  width: number;
  opacity: number;
  stroke: string;
  dash?: string;
  dashed: boolean;
  cross: boolean; // a blocked way gets an × at its middle
}

export function edgeStyle(kind: string, weight: number): EdgeStyle {
  const w = Math.min(1, Math.max(0, Number.isFinite(weight) ? weight : 0));
  const width = 1.5 + w * 3;
  const opacity = 0.45 + w * 0.55;
  switch (kind) {
    case "river":
      return { width: width + 0.5, opacity, stroke: "var(--color-map-river)", dashed: false, cross: false };
    case "route":
      return { width, opacity, stroke: "var(--color-map-path)", dash: "7 5", dashed: true, cross: false };
    case "blocked":
      return { width: 2, opacity: 0.85, stroke: "var(--color-map-blocked)", dash: "1 5", dashed: true, cross: true };
    default: // adjacent and anything new: a thin plain line
      return { width: 1 + w * 1.5, opacity, stroke: "var(--color-map-path)", dashed: false, cross: false };
  }
}

/** One line per pair of regions and kind: the two directions of a connection are drawn
 * once, with the stronger weight. */
export function uniqueEdges(connections: ConnectionEdge[]): ConnectionEdge[] {
  const best = new Map<string, ConnectionEdge>();
  for (const c of connections) {
    const [a, b] = [c.source_region_id, c.target_region_id].sort();
    const key = `${a}|${b}|${c.kind}`;
    const seen = best.get(key);
    if (!seen || c.weight > seen.weight) best.set(key, c);
  }
  return [...best.values()];
}
