import { lang as currentLang, tFor } from "../i18n";
import type { Lang } from "../types";

const LOCALES: Record<Lang, string> = { ko: "ko-KR", en: "en-US" };
// "2026년 10월 2일" / "Oct 2, 2026"
const DAY: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" };

/** A date in the display language's locale, in the viewer's time zone (UX-07, BR-V2-14).
 * Tests pass `timeZone: "UTC"` to fix the result. An unreadable string is shown as it is. */
export function formatDate(iso: string, lang: Lang = currentLang(), timeZone?: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(LOCALES[lang], { ...DAY, timeZone }).format(d);
}

/** Date and time, same rules as `formatDate`. */
export function formatDateTime(iso: string, lang: Lang = currentLang(), timeZone?: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(LOCALES[lang], {
    ...DAY,
    hour: "numeric",
    minute: "2-digit",
    timeZone,
  }).format(d);
}

/** The current turn: "4턴째" / "Turn 4"; a session not yet past its first turn is "시작"
 * as in the log (V4 code review 01 #15). */
export function turnLabel(n: number, lang: Lang = currentLang()): string {
  if (n === 0) return tFor(lang, "unit.turnStart");
  return tFor(lang, "unit.turnNow", { n });
}

/** A log line's turn: "4턴" / "T4", and 0 is "시작" / "Start". */
export function turnAt(n: number, lang: Lang = currentLang()): string {
  return n === 0 ? tFor(lang, "unit.turnStart") : tFor(lang, "unit.turnAt", { n });
}
