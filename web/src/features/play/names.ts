// Names in the display language for the play parts (V4 BR-V4-11, BLM § 2.7): a part takes
// `nameOf` from `useWorldNames` and falls back to the English it holds. Without one a part
// shows the English, as before V4.
import type { NameKind } from "../../hooks";

export type NameOf = (kind: NameKind, id: string, field: string, fallback: string) => string;

export const english: NameOf = (_kind, _id, _field, fallback) => fallback;

// a log payload's names and the ids they belong to (BLM § 2.7, the log row)
const PAYLOAD_NAMES: [idKey: string, nameKey: string, kind: NameKind, field: string][] = [
  ["region_id", "region_name", "regions", "name"],
  ["from_region_id", "from_region_name", "regions", "name"],
  ["to_region_id", "to_region_name", "regions", "name"],
  ["npc_id", "npc_name", "npcs", "name"],
  ["seed_id", "seed_title", "event_seeds", "title"],
];

/** A timeline payload with its names looked up by id. A name the map lacks keeps the
 * payload's own (fixed when the line was written); a line without ids is unchanged. */
export function namedPayload(payload: Record<string, unknown>, nameOf: NameOf): Record<string, unknown> {
  const out = { ...payload };
  for (const [idKey, nameKey, kind, field] of PAYLOAD_NAMES) {
    const id = payload[idKey];
    if (typeof id !== "string" || !id) continue;
    const named = nameOf(kind, id, field, "");
    if (named) out[nameKey] = named;
  }
  return out;
}
