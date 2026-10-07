// 0..1 measures as words (V2 FD domain-entities § 3, BR-V2-12/13). Each band holds values
// from the previous band's `upTo` (included) to its own `upTo` (excluded); the last
// band also holds 1. Out-of-range values are clamped; NaN and null are "—".
import { dicts, lang as currentLang } from "../i18n";
import type { Lang } from "../types";

export type MeasureKind =
  | "distortion"
  | "decay"
  | "support"
  | "magnitude"
  | "confidence"
  | "salience"
  | "weight"
  | "share";

export type Band = { upTo: number; key: string };

export const BANDS: Record<MeasureKind, readonly Band[]> = {
  distortion: [
    { upTo: 0.15, key: "nearlyTrue" },
    { upTo: 0.4, key: "stretched" },
    { upTo: 0.7, key: "twisted" },
    { upTo: 1, key: "otherStory" },
  ],
  decay: [
    { upTo: 0.3, key: "secondHand" },
    { upTo: 0.6, key: "faint" },
    { upTo: 1, key: "veryFaint" },
  ],
  support: [
    { upTo: 0.2, key: "hardly" },
    { upTo: 0.4, key: "few" },
    { upTo: 0.6, key: "fairly" },
    { upTo: 1, key: "widely" },
  ],
  magnitude: [
    { upTo: 0.25, key: "minor" },
    { upTo: 0.5, key: "moderate" },
    { upTo: 0.75, key: "major" },
    { upTo: 1, key: "severe" },
  ],
  confidence: [
    { upTo: 0.4, key: "low" },
    { upTo: 0.75, key: "medium" },
    { upTo: 1, key: "high" },
  ],
  salience: [
    { upTo: 0.34, key: "barely" },
    { upTo: 0.67, key: "noticed" },
    { upTo: 1, key: "stoodOut" },
  ],
  weight: [
    { upTo: 0.3, key: "rarely" },
    { upTo: 0.6, key: "sometimes" },
    { upTo: 1, key: "often" },
  ],
  share: [
    { upTo: 0.34, key: "little" },
    { upTo: 0.67, key: "half" },
    { upTo: 1, key: "most" },
  ],
};

const NONE = "word.none";
const isDev = (import.meta as { env?: { DEV?: boolean } }).env?.DEV === true;

/** The band index of a value, or -1 for NaN / null. Pure. */
export function bandIndex(kind: MeasureKind, value: number | null | undefined): number {
  if (value == null || Number.isNaN(value)) return -1;
  if ((value < 0 || value > 1) && isDev) console.warn(`${kind} ${value} is outside 0..1`);
  const v = Math.min(1, Math.max(0, value));
  const bands = BANDS[kind];
  for (let i = 0; i < bands.length - 1; i++) if (v < bands[i].upTo) return i;
  return bands.length - 1;
}

/** The dictionary key of a value's band (`word.<kind>.<band>`), or "word.none". */
export function bandOf(kind: MeasureKind, value: number | null | undefined): string {
  const i = bandIndex(kind, value);
  return i < 0 ? NONE : `word.${kind}.${BANDS[kind][i].key}`;
}

function word(key: string, lang: Lang): string {
  return dicts[lang][key] ?? dicts.ko[key] ?? key;
}

/** How twisted a rumor is, in words — the player screen shows no number (FR-D8). */
export function degreeWord(distortion: number | null | undefined, lang: Lang = currentLang()) {
  return word(bandOf("distortion", distortion), lang);
}

/** How faint a second-hand story is, in words (path decay). */
export function decayWord(pathDecay: number | null | undefined, lang: Lang = currentLang()) {
  return word(bandOf("decay", pathDecay), lang);
}

/** "0.42 · 많이 비틀림": the number with its meaning, for the GM and the editor. */
export function numberWithMeaning(
  kind: MeasureKind,
  value: number | null | undefined,
  lang: Lang = currentLang(),
): string {
  if (value == null || Number.isNaN(value)) return word(NONE, lang);
  return `${value.toFixed(2)} · ${word(bandOf(kind, value), lang)}`;
}
