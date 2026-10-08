// What the GM screen reads for one session, and what each write reads again (V6 BLM § 2–3,
// code plan § 1.1 R-02, R-03, § 1.2). It lives inside the screen's `key={sessionId}`
// boundary: another session starts it afresh, and an answer for the last session is dropped.
//
// - Each read answers with its key, and only an answer for the current key is used. So a
//   region's rumors never show under another region's name while the next region reads.
// - A re-read of the same key keeps the screen as it is until the answer comes (no flicker,
//   BR-V6-10). After a failed re-read the last answer stays and the error rides beside it.
// - A write's own answer is laid over the list at once (a rumor's support, a region's
//   distortion); the next answer of that read clears the layer, since it carries the save.
// - `after(kind)` reads again only what that write changed (the AFTER table = BLM § 3).
import { useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { statusOf } from "../../api/http";
import type { DescribedError } from "../../errors";
import { useResource } from "../../hooks";
import { useRequestLang } from "../../i18n";
import type {
  DeedViewOut,
  Player,
  RegionDistortion,
  SeedView,
  SessionEvent,
  SessionRumor,
  TimelineEntry,
  TurnRun,
  WorldState,
} from "../../types";

/** The GM writes (code plan § 1.2): 14 kinds over the 13 rows of BLM § 3. */
export type GmWrite =
  | "turn"
  | "suggest"
  | "approve"
  | "discard"
  | "resolve"
  | "create"
  | "seed"
  | "distortion"
  | "support"
  | "generate"
  | "regen"
  | "bulk"
  | "void"
  | "close";

export type GmRead =
  | "session"
  | "sessions"
  | "worldState"
  | "events"
  | "timeline"
  | "rumors"
  | "seeds"
  | "deeds"
  | "player"
  | "knowledge";

/** What each write reads again (BLM § 3; § 1.1 R-04 adds the session list to a turn). */
export const AFTER: Record<GmWrite, readonly GmRead[]> = {
  turn: ["session", "sessions", "worldState", "events", "timeline", "rumors", "seeds", "deeds", "player", "knowledge"],
  suggest: ["events", "timeline"],
  approve: ["events", "timeline", "worldState"],
  discard: ["events", "timeline"],
  resolve: ["events", "timeline", "worldState", "rumors"],
  create: ["events", "timeline", "worldState"],
  seed: ["seeds", "events", "timeline", "worldState"],
  distortion: ["worldState", "timeline"],
  support: ["timeline"],
  generate: ["rumors", "worldState", "timeline", "knowledge"],
  regen: ["rumors", "worldState", "timeline", "knowledge"],
  bulk: ["worldState", "rumors", "timeline"],
  void: ["deeds", "rumors", "worldState", "timeline", "knowledge"],
  close: ["session", "sessions"],
};

export interface GmRes<T> {
  /** The answer for the current key only. */
  data?: T;
  /** "ready" with data (a failed re-read keeps it and sets `error`), else loading / error. */
  state: "loading" | "ready" | "error";
  error?: DescribedError;
  reload(): void;
}

/** A read whose answer carries its key, so another key's data is never shown (R-02). */
function useOwn<T>(key: readonly unknown[] | null, load: () => Promise<T>): GmRes<T> {
  const keyText = key === null ? null : JSON.stringify(key);
  const r = useResource(key, async () => ({ k: keyText, v: await load() }));
  const data = r.data && r.data.k === keyText ? r.data.v : undefined;
  const state = data !== undefined ? "ready" : r.state === "error" ? "error" : "loading";
  return { data, state, error: r.state === "error" ? r.error : undefined, reload: r.reload };
}

export interface PlayerRead {
  player: Player | null;
  running: TurnRun[];
}

export interface GmData {
  events: GmRes<SessionEvent[]>;
  timeline: GmRes<TimelineEntry[]>;
  worldState: GmRes<WorldState>;
  rumors: GmRes<SessionRumor[]>;
  seeds: GmRes<SeedView[]>;
  deeds: GmRes<DeedViewOut[]>;
  player: GmRes<PlayerRead>;
  /** Bumped when what a region's NPCs know may have changed (the knowledge panel re-reads). */
  knowledgeRev: number;
  /** The rumors with a write's own answer laid over them. */
  rumorList: SessionRumor[] | undefined;
  /** A region's distortion and feedback share, a write's own answer first. */
  regionState(regionId: string): { distortion: number; feedback_share: number } | undefined;
  after(kind: GmWrite): void;
  patchRumor(r: SessionRumor): void;
  patchDistortion(row: RegionDistortion): void;
}

export function useGmData(
  sessionId: string,
  regionId: string | null,
  outside: { session?(): void; sessions?(): void } = {},
): GmData {
  const lang = useRequestLang();
  const events = useOwn(["gm-events", sessionId, lang], () => api.listEvents(sessionId));
  const timeline = useOwn(["gm-timeline", sessionId], () => api.getTimeline(sessionId));
  const worldState = useOwn(["gm-state", sessionId], () => api.getWorldState(sessionId));
  const rumors = useOwn(regionId ? ["gm-rumors", sessionId, regionId, lang] : null, () =>
    api.listRumors(sessionId, regionId as string),
  );
  const seeds = useOwn(["gm-seeds", sessionId], () => api.listSeeds(sessionId));
  const deeds = useOwn(["gm-deeds", sessionId, lang], () => api.listDeeds(sessionId));
  const player = useOwn(["gm-player", sessionId], async (): Promise<PlayerRead> => {
    const [p, runs] = await Promise.all([
      // only a 404 means "no player"; another failure is an error (U7 review § 3)
      api.getPlayer(sessionId).catch((e) => {
        if (statusOf(e) === 404) return null;
        throw e;
      }),
      api.listTurnRuns(sessionId, "running").catch(() => [] as TurnRun[]),
    ]);
    return { player: p, running: Array.isArray(runs) ? runs : [] };
  });
  const [knowledgeRev, setKnowledgeRev] = useState(0);

  // the write's own answers, cleared by the next answer of the same read (R-03)
  const [rumorPatch, setRumorPatch] = useState<Record<string, SessionRumor>>({});
  const [distPatch, setDistPatch] = useState<Record<string, { distortion: number; feedback_share: number }>>({});
  useEffect(() => setRumorPatch({}), [rumors.data]);
  useEffect(() => setDistPatch({}), [worldState.data]);

  const reloads: Record<GmRead, (() => void) | undefined> = {
    session: outside.session,
    sessions: outside.sessions,
    worldState: worldState.reload,
    events: events.reload,
    timeline: timeline.reload,
    rumors: regionId ? rumors.reload : undefined,
    seeds: seeds.reload,
    deeds: deeds.reload,
    player: player.reload,
    knowledge: () => setKnowledgeRev((n) => n + 1),
  };
  const after = (kind: GmWrite) => {
    for (const read of AFTER[kind]) reloads[read]?.();
  };

  const rumorList = rumors.data?.map((r) => rumorPatch[r.id] ?? r);
  const regionState = useCallback(
    (id: string) => {
      if (distPatch[id]) return distPatch[id];
      const row = worldState.data?.regions.find((r) => r.region_id === id);
      return row ? { distortion: row.distortion, feedback_share: row.feedback_share } : undefined;
    },
    [distPatch, worldState.data],
  );

  return {
    events,
    timeline,
    worldState,
    rumors,
    seeds,
    deeds,
    player,
    knowledgeRev,
    rumorList,
    regionState,
    after,
    patchRumor: (r) => setRumorPatch((p) => ({ ...p, [r.id]: r })),
    patchDistortion: (row) =>
      setDistPatch((p) => ({
        ...p,
        [row.region_id]: { distortion: row.distortion_degree, feedback_share: row.feedback_share ?? 0 },
      })),
  };
}
