import { ENUM_VALUES, enumLabel, type EnumKind } from "../../format";
import { t } from "../../i18n";
import type { ConnectionEdge, Knowledge, Region } from "../../types";

/** What the augmentation panel shows instead of the server's internal text (V8 BLM § 6.4,
 * BR-V8-18, FD review 01 R-07): the issue key `type:target_kind:ids:field:broken` as the
 * target's name, a change description `type:action` as two labels, a broken property as its
 * label. Nothing here ever returns the key or a raw enum value. */

export interface NameSource {
  regions: Region[];
  knowledge: Knowledge[];
  entities: { id: string; name?: string }[];
  connections: ConnectionEdge[];
}

const FIELDS = new Set(["parent_id", "located_in", "wiki_prior_ref", "derived_from_prior_ids", "about_entity_ids"]);

export function fieldLabel(field: string | null | undefined): string {
  return t(`label.field.${field && FIELDS.has(field) ? field : "other"}`);
}

function known(kind: EnumKind, value: string): boolean {
  return (ENUM_VALUES[kind] as readonly string[]).includes(value);
}

/** "낮은 확신 · 맞음" for `low_confidence:confirm`; "변경" for anything else. */
export function changeLabel(description: string): string {
  const [type, action, ...rest] = description.split(":");
  if (rest.length || !known("augmentationIssue", type ?? "") || !known("augmentationAction", action ?? ""))
    return t("label.change");
  return `${enumLabel("augmentationIssue", type)} · ${enumLabel("augmentationAction", action)}`;
}

function connectionName(ids: string, src: NameSource): string | undefined {
  for (const c of src.connections) {
    const [a, b] = [c.source_region_id, c.target_region_id].sort();
    if (`${a}|${b}|${c.kind}` !== ids) continue;
    const name = (id: string) => src.regions.find((r) => r.id === id)?.name;
    const na = name(a);
    const nb = name(b);
    if (!na || !nb) return undefined;
    return `${na} – ${nb} · ${enumLabel("connectionKind", c.kind)}`;
  }
  return undefined;
}

function nameOfId(kind: string, id: string, src: NameSource): string | undefined {
  if (kind === "region") return src.regions.find((r) => r.id === id)?.name;
  if (kind === "knowledge") {
    const k = src.knowledge.find((x) => x.id === id);
    return k ? k.title || k.statement : undefined;
  }
  if (kind === "entity") return src.entities.find((e) => e.id === id)?.name;
  return undefined;
}

/** The name of an issue key's target, with the broken property's label when there is one. */
export function issueKeyName(key: string, src: NameSource): string {
  const parts = key.split(":");
  if (parts.length < 5) return t("label.unnamed");
  const kind = parts[1];
  const field = parts[parts.length - 2];
  const ids = parts.slice(2, -2).join(":"); // an id may hold ":" itself
  let name: string | undefined;
  if (kind === "connection") name = connectionName(ids, src);
  else {
    name = nameOfId(kind, ids, src);
    // several targets are joined by "|"; a region id may hold "|" too, so the whole is tried first
    if (name == null && ids.includes("|")) {
      for (const one of ids.split("|")) {
        name = nameOfId(kind, one, src);
        if (name) break;
      }
    }
  }
  if (!name) return t("label.unnamed");
  return field ? `${name} · ${fieldLabel(field)}` : name;
}
