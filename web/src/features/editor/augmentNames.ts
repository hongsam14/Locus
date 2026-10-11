import { ENUM_VALUES, enumLabel, type EnumKind } from "../../format";
import { t } from "../../i18n";
import type { ConnectionEdge, Knowledge, QuestionTarget, Region } from "../../types";

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
    // the title the cards show: the display language's when there is one (code review 01 #24)
    return k ? k.title_ko || k.title || k.statement_ko || k.statement : undefined;
  }
  if (kind === "entity") return src.entities.find((e) => e.id === id)?.name;
  return undefined;
}

/** The target's name from its kind and ids, or undefined. */
function targetName(kind: string, ids: string, src: NameSource): string | undefined {
  if (kind === "connection") return connectionName(ids, src);
  // several targets are joined by "|"; a region id may hold "|" too, so the whole is tried first
  const whole = nameOfId(kind, ids, src);
  if (whole != null || !ids.includes("|")) return whole;
  for (const one of ids.split("|")) {
    const name = nameOfId(kind, one, src);
    if (name) return name;
  }
  return undefined;
}

export interface IssueKey {
  type: string;
  kind: string;
  ids: string;
  field: string; // "" when none
}

/** `type:target_kind:ids:field:broken`. Ids and the broken id may both hold ":", so the field
 * is found by its name (a known property) rather than by its place from the end (code
 * review 01 #21); a key without a field ends with "::". */
export function parseIssueKey(key: string): IssueKey | null {
  const parts = key.split(":");
  if (parts.length < 5) return null;
  const [type, kind] = parts;
  const rest = parts.slice(2);
  for (let j = 1; j < rest.length - 1; j++) {
    if (FIELDS.has(rest[j])) return { type, kind, ids: rest.slice(0, j).join(":"), field: rest[j] };
  }
  return { type, kind, ids: rest.slice(0, -2).join(":"), field: rest[rest.length - 2] };
}

/** The name of an issue key's target, with the broken property's label when there is one. */
export function issueKeyName(key: string, src: NameSource): string {
  const p = parseIssueKey(key);
  const name = p && targetName(p.kind, p.ids, src);
  if (!p || !name) return t("label.unnamed");
  return p.field ? `${name} · ${fieldLabel(p.field)}` : name;
}

/** An ignored or kept question's line: its issue's label and its target, so two issues of
 * one target read apart (code review 01 #23). */
export function issueKeyLine(key: string, src: NameSource): string {
  const type = parseIssueKey(key)?.type ?? "";
  const name = issueKeyName(key, src);
  return known("augmentationIssue", type) ? `${enumLabel("augmentationIssue", type)} · ${name}` : name;
}

/** A question's or a change's target by name: the world's name for it, so a connection reads
 * as its two regions and the kind in words — the server's own name carries the raw kind
 * (code review 01 #3); the server's name only for a target the world does not hold. */
export function targetLabel(target: QuestionTarget, src: NameSource): string {
  if (target.kind === "connection") {
    const key = target.connection
      ? `${[target.connection.a_region_id, target.connection.b_region_id].sort().join("|")}|${target.connection.kind}`
      : target.id;
    return connectionName(key, src) ?? t("label.unnamed");
  }
  return nameOfId(target.kind, target.id, src) ?? (target.name || t("label.unnamed"));
}
