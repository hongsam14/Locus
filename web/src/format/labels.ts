import { dicts, lang as currentLang } from "../i18n";
import type { Lang } from "../types";
import type { EnumKind } from "./enums";

const isDev = (import.meta as { env?: { DEV?: boolean } }).env?.DEV === true;

/** A server enum value in the display language (FR-D8). An unknown value shows as it is,
 * with a warning in a dev build — the screen never goes blank (BR-V2-11). */
export function enumLabel(kind: EnumKind, value: string, lang: Lang = currentLang()): string {
  const key = `enum.${kind}.${value}`;
  const label = dicts[lang][key] ?? dicts.ko[key];
  if (label == null) {
    if (isDev) console.warn(`no label for ${key}`);
    return value;
  }
  return label;
}
