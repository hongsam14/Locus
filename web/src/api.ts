import type {
  AugAnswer,
  AugSession,
  GameSession,
  QueryResult,
  Region,
  RegionDistortion,
  SessionRumor,
  TimelineEntry,
  TurnResult,
  WorldExport,
} from "./types";

const BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // serving
  regionKnowledge: (worldId: string, regionId: string, includeRumors = true) =>
    http<QueryResult>(
      `/api/query/regions/${encodeURIComponent(regionId)}/knowledge?world_id=${encodeURIComponent(
        worldId,
      )}&include_rumors=${includeRumors}`,
    ),

  // authoring
  exportWorld: (worldId: string) =>
    http<WorldExport>(`/api/authoring/worlds/${encodeURIComponent(worldId)}/export`),
  // Builds the bundled demo world server-side. with_map=false keeps it fast
  // (structured map + memo, no VLM); pass with_map=true to also run the VLM.
  buildWorldDemo: (worldId: string, withMap = false) =>
    http(
      `/api/authoring/worlds/${encodeURIComponent(worldId)}/build/demo?with_map=${withMap}`,
      { method: "POST" },
    ),
  upsertRegion: (worldId: string, region: Region) =>
    http<Region>(
      `/api/authoring/worlds/${encodeURIComponent(worldId)}/regions/${encodeURIComponent(region.id)}`,
      { method: "PUT", body: JSON.stringify(region) },
    ),
  deleteNode: (worldId: string, nodeId: string) =>
    http(
      `/api/authoring/worlds/${encodeURIComponent(worldId)}/nodes/${encodeURIComponent(nodeId)}`,
      { method: "DELETE" },
    ),

  // augmentation
  startAugment: (worldId: string) =>
    http<AugSession>(`/api/authoring/worlds/${encodeURIComponent(worldId)}/augment/session`, {
      method: "POST",
    }),
  submitAnswer: (sessionId: string, answer: AugAnswer) =>
    http(`/api/authoring/augment/${encodeURIComponent(sessionId)}/answer`, {
      method: "POST",
      body: JSON.stringify(answer),
    }),
  revertAugment: (sessionId: string, changeId: string) =>
    http(
      `/api/authoring/augment/${encodeURIComponent(sessionId)}/revert?change_id=${encodeURIComponent(
        changeId,
      )}`,
      { method: "POST" },
    ),

  // --- session layer (S3) ---
  listSessions: (worldId: string) =>
    http<GameSession[]>(
      `/api/session/worlds/${encodeURIComponent(worldId)}/sessions`,
    ),
  startSession: (worldId: string) =>
    http<GameSession>(`/api/session/worlds/${encodeURIComponent(worldId)}/sessions`, {
      method: "POST",
    }),
  closeSession: (sid: string) =>
    http<GameSession>(`/api/session/sessions/${encodeURIComponent(sid)}/close`, {
      method: "POST",
    }),
  getTimeline: (sid: string) =>
    http<TimelineEntry[]>(`/api/session/sessions/${encodeURIComponent(sid)}/timeline`),
  listRumors: (sid: string, regionId: string) =>
    http<SessionRumor[]>(
      `/api/session/sessions/${encodeURIComponent(sid)}/regions/${encodeURIComponent(
        regionId,
      )}/rumors`,
    ),
  generateRumors: (sid: string, regionId: string) =>
    http<SessionRumor[]>(
      `/api/session/sessions/${encodeURIComponent(sid)}/regions/${encodeURIComponent(
        regionId,
      )}/rumors`,
      { method: "POST" },
    ),
  regenRumors: (sid: string, regionId: string) =>
    http<SessionRumor[]>(
      `/api/session/sessions/${encodeURIComponent(sid)}/regions/${encodeURIComponent(
        regionId,
      )}/rumors/regen`,
      { method: "POST" },
    ),
  setSupport: (sid: string, rumorId: string, support: number) =>
    http<SessionRumor>(
      `/api/session/sessions/${encodeURIComponent(sid)}/rumors/${encodeURIComponent(
        rumorId,
      )}/support`,
      { method: "PUT", body: JSON.stringify({ support }) },
    ),
  setDistortion: (sid: string, regionId: string, degree: number) =>
    http<RegionDistortion>(
      `/api/session/sessions/${encodeURIComponent(sid)}/regions/${encodeURIComponent(
        regionId,
      )}/distortion`,
      { method: "PUT", body: JSON.stringify({ degree }) },
    ),
  advanceTurn: (sid: string) =>
    http<TurnResult>(`/api/session/sessions/${encodeURIComponent(sid)}/advance-turn`, {
      method: "POST",
    }),
  sessionKnowledge: (sid: string, regionId: string) =>
    http<QueryResult>(
      `/api/session/sessions/${encodeURIComponent(sid)}/regions/${encodeURIComponent(
        regionId,
      )}/knowledge`,
    ),
};
