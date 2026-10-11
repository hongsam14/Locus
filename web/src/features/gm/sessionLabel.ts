// The GM's session picker in words (V6 BR-V6-26, code plan § 1.2 and § 1.1 R-04): "4턴째 ·
// 진행 중 · 2026년 10월 8일 오후 2:05"; the id only when there is no date, or a short tail
// when two labels would read the same. Ended sessions sit in their own group, after the
// open ones. The current session's line is built from the session read, not the list, so
// a stale list never shows the wrong turn; a session the list does not have yet is added.
import { enumLabel, formatDateTime, turnLabel } from "../../format";
import { tFor } from "../../i18n";
import type { GameSession, Lang } from "../../types";

export interface SessionOption {
  value: string;
  label: string;
  group?: string;
}

export function sessionLabel(s: GameSession, lang: Lang): string {
  const when = s.created_at ? formatDateTime(s.created_at, lang) : s.id.slice(0, 8);
  return `${turnLabel(s.turn, lang)} · ${enumLabel("sessionStatus", s.status, lang)} · ${when}`;
}

export function sessionOptions(list: GameSession[] | null, current: GameSession | null, lang: Lang): SessionOption[] {
  const byId = new Map<string, GameSession>();
  for (const s of list ?? []) byId.set(s.id, s);
  if (current) byId.set(current.id, current); // fresh from the session read (R-04)
  const all = [...byId.values()];
  const ordered = [...all.filter((s) => s.status !== "closed"), ...all.filter((s) => s.status === "closed")];
  const labels = ordered.map((s) => sessionLabel(s, lang));
  const count = new Map<string, number>();
  for (const l of labels) count.set(l, (count.get(l) ?? 0) + 1);
  const ended = tFor(lang, "label.endedSessions");
  return ordered.map((s, i) => ({
    value: s.id,
    label: (count.get(labels[i]) ?? 0) > 1 ? `${labels[i]} · ${s.id.slice(0, 4)}` : labels[i],
    group: s.status === "closed" ? ended : undefined,
  }));
}
