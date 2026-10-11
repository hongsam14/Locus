import type { GameSession } from "../../types";

/** Open sessions, latest first (BLM § 1.1): the server lists every session, oldest first.
 * Compared as times, not text — "…45Z" and "…45.500000Z" sort wrong as text (code review 01
 * #23); a session without a time goes last. */
export function openLatestFirst(sessions: readonly GameSession[]): GameSession[] {
  const at = (s: GameSession) => {
    const ms = s.created_at ? Date.parse(s.created_at) : NaN;
    return Number.isNaN(ms) ? -Infinity : ms;
  };
  return sessions.filter((s) => s.status === "open").sort((a, b) => at(b) - at(a));
}
