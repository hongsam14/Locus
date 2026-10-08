import type { GameSession } from "../../types";

/** Open sessions, latest first (BLM § 1.1): the server lists every session, oldest first.
 * ISO times of one server compare as text. */
export function openLatestFirst(sessions: readonly GameSession[]): GameSession[] {
  return sessions
    .filter((s) => s.status === "open")
    .sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
}
