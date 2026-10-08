// What the GM screen reads around one session (V6 BLM § 1.1–1.2, code plan § 1.1 R-02,
// R-04, R-10): the session, its world, the world's names and its sessions. It lives outside
// the screen's `key={sessionId}` boundary, so the world, the names and the list stay when
// the GM moves to another session of the same world.
//
// - The session is used only when its id is the route's: `useResource` keeps the last key's
//   data while the next key reads (RE-F14).
// - While the next session reads, the last world stays: a session of another world drops it
//   when it comes.
// - A failed name read falls back to English quietly; a failed list read says so beside the
//   picker. `retry` reads again whatever failed (RE-F01).
import { useRef } from "react";
import { api } from "../../api";
import type { DescribedError } from "../../errors";
import { useResource, useWorldNames } from "../../hooks";
import type { GameSession, WorldExport } from "../../types";

export interface GmSessionRead {
  session: GameSession | null;
  world: WorldExport | null;
  worldId: string | null;
  sessions: GameSession[] | null;
  names: ReturnType<typeof useWorldNames>;
  /** "ready" once the session and its world are here; "error" when either read failed. */
  state: "loading" | "ready" | "error";
  error?: DescribedError;
  sessionsError?: DescribedError;
  retry(): void;
  reloadSession(): void;
  reloadSessions(): void;
}

export function useGmSession(sessionId: string): GmSessionRead {
  const sessionR = useResource(sessionId ? ["gm-session", sessionId] : null, () => api.getSession(sessionId));
  const session = sessionR.data && sessionR.data.id === sessionId ? sessionR.data : null;

  // the world to show: the session's, or the last one while the next session reads
  const lastWorld = useRef<string | null>(null);
  if (session) lastWorld.current = session.world_id;
  const worldId = session?.world_id ?? lastWorld.current;

  const worldR = useResource(worldId ? ["gm-world", worldId] : null, () => api.exportWorld(worldId as string));
  const world = worldR.data && worldR.data.world_id === worldId ? worldR.data : null;
  const names = useWorldNames(worldId);
  const listR = useResource(worldId ? ["gm-sessions", worldId] : null, async () => ({
    worldId,
    list: await api.listSessions(worldId as string),
  }));
  const sessions = listR.data && listR.data.worldId === worldId ? listR.data.list : null;

  const sessionFailed = sessionR.state === "error" && !session;
  const worldFailed = worldR.state === "error" && !world;
  const state = sessionFailed || worldFailed ? "error" : session && world ? "ready" : "loading";
  return {
    session,
    world,
    worldId,
    sessions,
    names,
    state,
    error: sessionFailed ? sessionR.error : worldFailed ? worldR.error : undefined,
    sessionsError: listR.state === "error" ? listR.error : undefined,
    retry: () => {
      if (sessionR.state === "error") sessionR.reload();
      if (worldR.state === "error") worldR.reload();
      if (names.failed) names.reload();
    },
    reloadSession: sessionR.reload,
    reloadSessions: listR.reload,
  };
}
