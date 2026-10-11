// What the player screen reads for one session: the session, its region view and its
// journey log (V4 FD BLM § 2.1, BR-V4-16). Late answers are dropped (useResource), and
// the data of another session — the previous one while the next reads — is never shown:
// the screen gets data only when `session.id` is the session it asked for. A re-read after
// an action keeps the data on screen (same key, `reload`); an error then rides above it.
import { api } from "../api";
import type { DescribedError } from "../errors";
import { useRequestLang } from "../i18n";
import type { GameSession, RegionView, TimelineEntry } from "../types";
import { useResource } from "./useResource";

export interface PlaySession {
  session: GameSession | null;
  view: RegionView | null;
  log: TimelineEntry[];
  /** "loading" only without data; with data a failed re-read keeps "ready" and sets `error`. */
  state: "loading" | "ready" | "error";
  error?: DescribedError;
  /** A read is out (the held re-reads wait for it rather than cut it short). */
  pending: boolean;
  reload(): void;
}

export function usePlaySession(sessionId: string, logLines = 30): PlaySession {
  const lang = useRequestLang();
  const r = useResource(sessionId ? ["play", sessionId, lang] : null, async () => {
    const [session, view, log] = await Promise.all([
      api.getSession(sessionId),
      api.getRegion(sessionId),
      api.getLog(sessionId, logLines),
    ]);
    return { session, view, log };
  });
  const data = r.data && r.data.session.id === sessionId ? r.data : null;
  const state = data ? "ready" : r.state === "error" ? "error" : "loading";
  return {
    session: data?.session ?? null,
    view: data?.view ?? null,
    log: data?.log ?? [],
    state,
    error: r.state === "error" ? r.error : undefined,
    pending: r.pending,
    reload: r.reload,
  };
}
