// The world's name map in the display language (V3 Q5=A; V4 BR-V4-11): region, NPC,
// event-seed and world text by id. Read once per world and language; a map of another
// world (a late answer, or the previous world while the next one reads) is never used.
import { useCallback } from "react";
import { api } from "../api";
import { useRequestLang } from "../i18n";
import type { WorldNames } from "../types";
import { useResource } from "./useResource";

export type NameKind = "regions" | "npcs" | "event_seeds";

export function useWorldNames(worldId: string | null): {
  names: WorldNames | null;
  nameOf(kind: NameKind, id: string, field: string, fallback: string): string;
} {
  const lang = useRequestLang();
  const r = useResource(worldId ? ["names", worldId, lang] : null, () => api.worldNames(worldId as string));
  const names = r.data && r.data.world_id === worldId ? r.data : null;
  const nameOf = useCallback(
    (kind: NameKind, id: string, field: string, fallback: string) => names?.[kind]?.[id]?.[field] ?? fallback,
    [names],
  );
  return { names, nameOf };
}
