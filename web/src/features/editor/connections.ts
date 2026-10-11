import { ENUM_VALUES, enumLabel } from "../../format";
import type { ConnectionEdge, ConnectionKind, Region } from "../../types";

// What the editor's map and inspector share (V8 code plan § 1.4 R-06: moved here from the old
// map canvas).

export type MapTool = "select" | "addRegion" | "connect";

export const DEFAULT_WEIGHT = 0.6; // a new connection's starting weight (as before V8)

export interface NewRegion {
  name: string;
  level: string;
  parent_id: string | null;
  description: string | null;
  position: { x: number; y: number };
}

/** The stored connection of this pair and kind, either way round (a pair is one
 * connection, BR-U3-10), or undefined. */
export function sameConnection(
  connections: ConnectionEdge[],
  a: string,
  b: string,
  kind: ConnectionKind,
): ConnectionEdge | undefined {
  return connections.find(
    (c) =>
      c.kind === kind &&
      ((c.source_region_id === a && c.target_region_id === b) ||
        (c.source_region_id === b && c.target_region_id === a)),
  );
}

/** Regions as select options, one group per level, by level then name (the GM picker's
 * order, V6), so any region is reachable without the map (FR-S6, BR-V8-08). */
export function regionOptions(regions: Region[]): { value: string; label: string; group: string }[] {
  const levels: readonly string[] = ENUM_VALUES.regionLevel;
  return [...regions]
    .sort((a, b) => levels.indexOf(a.level) - levels.indexOf(b.level) || a.name.localeCompare(b.name))
    .map((r) => ({ value: r.id, label: r.name, group: enumLabel("regionLevel", r.level) }));
}

export const levelOptions = () => ENUM_VALUES.regionLevel.map((l) => ({ value: l, label: enumLabel("regionLevel", l) }));
export const kindOptions = () =>
  (ENUM_VALUES.connectionKind as readonly ConnectionKind[]).map((k) => ({ value: k, label: enumLabel("connectionKind", k) }));
