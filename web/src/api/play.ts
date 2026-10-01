// `/api/play` — game sessions, the player screen and player actions (U4).
import type {
  Conversation,
  GameSession,
  NpcReply,
  NpcSummary,
  PlayerAction,
  PlayerCreate,
  Player,
  QueryResult,
  RegionView,
  SessionStartOut,
  TimelineEntry,
  TurnRun,
} from "../types";
import { enc, http, withLang } from "./http";

const s = (sid: string) => `/api/play/sessions/${enc(sid)}`;

function startSession(worldId: string): Promise<GameSession>;
function startSession(worldId: string, body: PlayerCreate): Promise<SessionStartOut>;
function startSession(worldId: string, body?: PlayerCreate) {
  // No body = GM session (200 GameSession, pre-U4 contract); body = player-mode
  // session (201 {session, player}).
  return http<GameSession | SessionStartOut>(`/api/play/worlds/${enc(worldId)}/sessions`, {
    method: "POST",
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
}

export const playApi = {
  listSessions: (worldId: string) =>
    http<GameSession[]>(`/api/play/worlds/${enc(worldId)}/sessions`),
  startSession,
  getSession: (sid: string) => http<GameSession>(s(sid)),
  closeSession: (sid: string) => http<GameSession>(`${s(sid)}/close`, { method: "POST" }),
  sessionKnowledge: (sid: string, regionId: string) =>
    http<QueryResult>(withLang(`${s(sid)}/regions/${enc(regionId)}/knowledge`)),
  // U4 player mode
  getPlayer: (sid: string) => http<Player>(`${s(sid)}/player`),
  getRegion: (sid: string) => http<RegionView>(withLang(`${s(sid)}/region`)),
  // U6: the display language travels with the action (a declaration is narrated in it)
  act: (sid: string, action: PlayerAction) =>
    http<TurnRun>(withLang(`${s(sid)}/act`), { method: "POST", body: JSON.stringify(action) }),
  getTurnRun: (sid: string, runId: string) => http<TurnRun>(`${s(sid)}/turn-runs/${enc(runId)}`),
  listTurnRuns: (sid: string, status?: string) =>
    http<TurnRun[]>(`${s(sid)}/turn-runs${status ? `?status=${enc(status)}` : ""}`),
  // `limit` keeps the newest lines (the screen shows 30, U7 review C6)
  getLog: (sid: string, limit?: number) =>
    http<TimelineEntry[]>(`${s(sid)}/log${limit ? `?limit=${limit}` : ""}`),
  // U5 NPC dialogue: only `say` calls the LLM (one call) and takes the language
  listNpcs: (sid: string) => http<NpcSummary[]>(`${s(sid)}/npcs`),
  startDialogue: (sid: string, npcId: string) =>
    http<Conversation>(`${s(sid)}/npcs/${enc(npcId)}/start`, { method: "POST" }),
  say: (sid: string, npcId: string, text: string) =>
    http<NpcReply>(withLang(`${s(sid)}/npcs/${enc(npcId)}/say`), {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  dialogueHistory: (sid: string, npcId: string) =>
    http<Conversation>(`${s(sid)}/npcs/${enc(npcId)}/history`),
};
