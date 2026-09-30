// `/api/play` — game sessions, the player screen and player actions (U4).
import type {
  GameSession,
  PlayerAction,
  PlayerCreate,
  Player,
  QueryResult,
  RegionView,
  SessionStartOut,
  TimelineEntry,
  TurnRun,
} from "../types";
import { enc, http } from "./http";

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
    http<QueryResult>(`${s(sid)}/regions/${enc(regionId)}/knowledge`),
  // U4 player mode
  getPlayer: (sid: string) => http<Player>(`${s(sid)}/player`),
  getRegion: (sid: string) => http<RegionView>(`${s(sid)}/region`),
  act: (sid: string, action: PlayerAction) =>
    http<TurnRun>(`${s(sid)}/act`, { method: "POST", body: JSON.stringify(action) }),
  getTurnRun: (sid: string, runId: string) => http<TurnRun>(`${s(sid)}/turn-runs/${enc(runId)}`),
  listTurnRuns: (sid: string, status?: string) =>
    http<TurnRun[]>(`${s(sid)}/turn-runs${status ? `?status=${enc(status)}` : ""}`),
  getLog: (sid: string) => http<TimelineEntry[]>(`${s(sid)}/log`),
};
