// Lightweight i18n (X3 / C10, extended by U5; split into ko.ts / en.ts in V2): two
// dictionaries and the display language as module state, remembered in localStorage.
// No library (FD-U5 frontend §2.2): a few hundred flat keys do not justify i18next.
// Korean is the default (Q2=A). A key's first segment says its register (V2 BLM § 4):
// action/nav/tab = control names, notice/error/confirm/empty/hint = 해요체 notices,
// story/log/timeline = 해라체 narration, enum/word/label/unit = value names.
import { useSyncExternalStore } from "react";
import type { Lang } from "../types";
import { en } from "./en";
import { ko } from "./ko";

type Params = Record<string, unknown>;

export const LANGS: readonly Lang[] = ["ko", "en"];
const STORAGE_KEY = "locus.lang";

/** Both dictionaries, exported for the key-set test (same keys in ko and en). */
export const dicts: Record<Lang, Record<string, string>> = { ko, en };

function isLang(v: unknown): v is Lang {
  return v === "ko" || v === "en";
}

// Storage can throw (private window, blocked site data) — the language then just
// is not remembered.
function readStoredLang(): Lang | null {
  try {
    const v = globalThis.localStorage?.getItem(STORAGE_KEY);
    return isLang(v) ? v : null;
  } catch {
    return null;
  }
}

let current: Lang = readStoredLang() ?? "ko";
if (typeof document !== "undefined") document.documentElement.lang = current;
const listeners = new Set<() => void>();

// The server's display languages (`GET /api/langs`, review U5 #2). Until they are
// known the client sends no `?lang=` and the server's default applies: a server
// configured for English only must never receive `?lang=ko` and answer 400.
let serverDefault: string | null = null;
let serverLangs: readonly string[] | null = null;

function notify(): void {
  if (typeof document !== "undefined") document.documentElement.lang = current;
  for (const fn of listeners) fn();
}

/** The display language: labels come from its dictionary. Read requests carry it as
 * `?lang=` when the server needs to be told (`requestLang`, `api/http.ts::withLang`). */
export function lang(): Lang {
  return current;
}

/** Switch the display language, remember it, and re-render every `useLang()` user. */
export function setLang(next: Lang): void {
  if (!isLang(next) || next === current) return;
  current = next;
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, next);
  } catch {
    /* not remembered; the switch still applies to this page */
  }
  notify();
}

/** Adopt the server's languages. A remembered language the server does not take falls
 * back to the server default (for this page; the stored choice is kept). */
export function configureLangs(defaultLang: string, supported: readonly string[]): void {
  serverDefault = defaultLang.trim().toLowerCase();
  serverLangs = supported.map((l) => l.trim().toLowerCase());
  const known = serverLangs;
  if (!known.includes(current)) {
    const fallback = isLang(serverDefault) ? serverDefault : LANGS.find((l) => known.includes(l));
    if (fallback) current = fallback;
  }
  notify();
}

/** The `?lang=` value to send, or `null` to let the server default apply: unknown
 * server languages, a language the server does not take, or the default itself. */
export function requestLang(): Lang | null {
  if (serverLangs === null || !serverLangs.includes(current)) return null;
  return current === serverDefault ? null : current;
}

/** Languages the toggle offers: the dictionaries the server also takes. */
export function availableLangs(): Lang[] {
  const known = serverLangs;
  return known === null ? [...LANGS] : LANGS.filter((l) => known.includes(l));
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Subscribe a component to the display language (re-renders on `setLang`). */
export function useLang(): Lang {
  return useSyncExternalStore(subscribe, lang, lang);
}

const requestKey = () => requestLang() ?? "";

/** The language the server is asked for (`""` = its default). Screens that show
 * translated data re-read when this changes — not merely when the labels change. */
export function useRequestLang(): string {
  return useSyncExternalStore(subscribe, requestKey, requestKey);
}

const availableKey = () => availableLangs().join(",");

/** Re-render when the offered languages change (after `configureLangs`). */
export function useAvailableLangs(): Lang[] {
  const key = useSyncExternalStore(subscribe, availableKey, availableKey);
  return key ? (key.split(",") as Lang[]) : [];
}

function lookup(key: string): string | undefined {
  return dicts[current][key] ?? dicts.ko[key];
}

/** Translate a key with {param} interpolation: the current language's dictionary,
 * then Korean, then the key itself (a missing key never blanks the screen). */
export function t(key: string, params?: Params): string {
  const tpl = lookup(key);
  if (tpl == null) return key;
  return tpl.replace(/\{(\w+)\}/g, (_, k) => {
    const v = params?.[k];
    return v == null ? `{${k}}` : String(v);
  });
}

/** Localize a timeline entry from its kind + payload (F2a). When no template
 * exists for the kind (e.g. event_created, reused for create/suggest/approve),
 * falls back to the entry's own summary so distinct actions stay legible. */
export function timelineText(
  kind: string,
  payload: Params,
  turn: number,
  summary?: string,
): string {
  let k = kind;
  // U8 (BR-U8-18): a seed's start is an event_created line that names its seed
  if (k === "event_created" && payload.seed_title != null) {
    return t("timeline.seedStarted", { title: payload.seed_title });
  }
  // older lines: one kind for create/suggest/approve, told apart by a flag (pre-U7) —
  // only when the line has what the newer wording needs (U7 review #10)
  if (k === "event_created" && payload.suggested && payload.category != null) k = "event_suggested";
  else if (k === "event_created" && payload.approved && payload.category != null) k = "event_approved";
  else if (k === "event_created" && (payload.suggested || payload.approved)) return summary || kind;
  else if (k === "session_started" && payload.player_name == null) k = "gm_session_started";
  const key = `timeline.${k}`;
  const template = lookup(key);
  if (template == null) return summary || kind;
  // a region line written before regions were recorded on it: its summary, not "—"
  // (U3 A3-14, BR-U3-39)
  if (template.includes("{region}") && payload.region_name == null && payload.region_id == null) {
    return summary || t(key, { ...payload, turn, region: "—" });
  }
  const params: Params = { ...payload, turn, region: regionOf(payload) };
  // a field the line does not carry would show as "{name}": the summary reads better —
  // judged on the template's own fields, so a name with braces in it stays (U3 S08)
  const missing = [...template.matchAll(/\{(\w+)\}/g)].some(([, k]) => params[k] == null);
  return missing && summary ? summary : t(key, params);
}

/** A line as the player reads it: its own wording when it has one (`log.*`), else the
 * timeline's (U7, FR-C6). */
export function logText(kind: string, payload: Params, turn: number, summary?: string): string {
  const key = `log.${kind}`;
  if (lookup(key) != null) return t(key, { ...payload, turn, region: regionOf(payload) });
  return timelineText(kind, payload, turn, summary);
}

// FR-D3: the region by name; its id for a line written before names, "—" for none.
function regionOf(payload: Params): string {
  const name = payload.region_name ?? payload.region_id;
  return name == null ? "—" : String(name);
}
