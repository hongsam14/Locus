// `/api/knowledge` — canonical region knowledge (consensus + hearsay).
import type { QueryResult, RegionBrief } from "../types";
import { enc, http } from "./http";

export const knowledgeApi = {
  regionBriefs: (worldId: string, topK = 3) =>
    http<RegionBrief[]>(`/api/knowledge/worlds/${enc(worldId)}/briefs?top_k=${topK}`),
  regionKnowledge: (worldId: string, regionId: string, includeHearsay = true) =>
    http<QueryResult>(
      `/api/knowledge/worlds/${enc(worldId)}/regions/${enc(regionId)}?include_hearsay=${includeHearsay}`,
    ),
};
