import type { AugAnswer, AugSession, QueryResult, Region, WorldExport } from "./types";

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
  buildWorldDemo: (worldId: string) =>
    http(`/api/authoring/worlds/${encodeURIComponent(worldId)}/build`, {
      method: "POST",
      body: JSON.stringify({ memos: [], structured_maps: [] }),
    }),
  buildWiki: () => http(`/api/authoring/wiki/build`, { method: "POST", body: "null" }),
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
};
