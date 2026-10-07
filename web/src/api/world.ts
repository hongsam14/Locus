// `/api/world` — world editor: build, export, World File, edits, wiki, augmentation runs.
import type {
  AnswerResult,
  AugAnswer,
  AugRun,
  BuildReport,
  ConnectionEdge,
  DemoInfo,
  EditorRegionView,
  ImportReport,
  Knowledge,
  NPC,
  NpcDraftResult,
  PriorRefsOut,
  Region,
  RegionDeletePlan,
  RegionDeleteReport,
  WikiPrior,
  WorldExport,
  WorldFile,
  WorldInfo,
  WorldNames,
  DemoLoadReport,
} from "../types";
import { BASE, enc, http, HttpError, withLang } from "./http";

const w = (worldId: string) => `/api/world/worlds/${enc(worldId)}`;

/** A knowledge item as the server takes it: the response-only translations removed. */
function stripKo(k: Knowledge): Knowledge {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { statement_ko, title_ko, ...rest } = k;
  return rest as Knowledge;
}

// Replace-confirmation flags shared by build / import / demo (BR-U2-25). A 409 means
// the world has open sessions; retry with confirm=true to close them.
export interface ReplaceOptions {
  replace?: boolean;
  confirm?: boolean;
}

const replaceQuery = (o: ReplaceOptions = {}, extra: Record<string, string> = {}) =>
  new URLSearchParams({
    replace: String(o.replace ?? true),
    confirm: String(o.confirm ?? false),
    ...extra,
  }).toString();

export const worldApi = {
  exportWorld: (worldId: string) =>
    http<WorldExport>(`/api/world/worlds/${enc(worldId)}/export`),

  // --- U2: build / World File / demo / list ---
  buildWorld: (
    worldId: string,
    inputs: {
      memos?: string[];
      structured_maps?: object[];
      map_images?: string[]; // base64
      concept_arts?: string[];
      name?: string | null;
      description?: string | null;
    },
    options?: ReplaceOptions,
  ) =>
    http<BuildReport>(`/api/world/worlds/${enc(worldId)}/build?${replaceQuery(options)}`, {
      method: "POST",
      body: JSON.stringify(inputs),
    }),
  uploadBuild: (worldId: string, form: FormData) =>
    fetch(`${BASE}/api/world/worlds/${enc(worldId)}/build/upload`, {
      method: "POST",
      body: form,
    }).then(async (res) => {
      if (!res.ok) throw new HttpError(res.status, res.statusText, await res.text());
      return (await res.json()) as BuildReport;
    }),
  getWorldFile: (worldId: string) => http<WorldFile>(`/api/world/worlds/${enc(worldId)}/file`),
  importWorldFile: (worldId: string, file: WorldFile | object, options?: ReplaceOptions & { remap?: boolean }) =>
    http<ImportReport>(
      `/api/world/worlds/${enc(worldId)}/file?${replaceQuery(options, { remap: String(options?.remap ?? false) })}`,
      { method: "POST", body: JSON.stringify(file) },
    ),
  listWorlds: () => http<WorldInfo[]>(withLang(`/api/world/worlds`)),
  listDemos: () => http<DemoInfo[]>(withLang(`/api/world/demos`)),
  // V3 (Q5=A): the world's names in the display language; find by id, else the English
  worldNames: (worldId: string) => http<WorldNames>(withLang(`${w(worldId)}/names`)),
  // Loads a manifest demo's World File — no LLM call (FR-B3, US-1.3). No default name:
  // the home screen reads the demos from the manifest (U8, BR-U8-1).
  loadDemo: (worldId: string, name: string, options?: ReplaceOptions) =>
    http<DemoLoadReport>(
      `/api/world/worlds/${enc(worldId)}/demo/${enc(name)}?${replaceQuery(options)}`,
      { method: "POST" },
    ),
  // --- U3 world editor (BLM §7) ---
  getEditorRegion: (worldId: string, regionId: string) =>
    http<EditorRegionView>(withLang(`${w(worldId)}/regions/${enc(regionId)}/editor`)),
  createRegion: (worldId: string, region: Partial<Region>) =>
    http<Region>(`${w(worldId)}/regions`, { method: "POST", body: JSON.stringify(region) }),
  updateRegion: (worldId: string, region: Region) =>
    http<Region>(`${w(worldId)}/regions/${enc(region.id)}`, {
      method: "PUT",
      body: JSON.stringify(region),
    }),
  getDeletePlan: (worldId: string, regionId: string) =>
    http<RegionDeletePlan>(`${w(worldId)}/regions/${enc(regionId)}/delete-plan`),
  deleteRegion: (worldId: string, regionId: string) =>
    http<RegionDeleteReport>(`${w(worldId)}/regions/${enc(regionId)}`, { method: "DELETE" }),
  saveConnection: (worldId: string, edge: ConnectionEdge & { previous_kind?: string }) =>
    http<ConnectionEdge[]>(`${w(worldId)}/connections`, {
      method: "PUT",
      body: JSON.stringify(edge),
    }),
  deleteConnection: (worldId: string, a: string, b: string, kind: string) =>
    http<{ deleted: number }>(
      `${w(worldId)}/connections?${new URLSearchParams({ a, b, kind }).toString()}`,
      { method: "DELETE" },
    ),
  createKnowledge: (worldId: string, regionId: string, k: Partial<Knowledge>) =>
    http<Knowledge>(`${w(worldId)}/regions/${enc(regionId)}/knowledge`, {
      method: "POST",
      body: JSON.stringify(k),
    }),
  updateKnowledge: (worldId: string, k: Knowledge) =>
    http<Knowledge>(`${w(worldId)}/knowledge/${enc(k.id)}`, {
      method: "PUT",
      body: JSON.stringify(stripKo(k)),
    }),
  setScopes: (worldId: string, knowledgeId: string, regionIds: string[]) =>
    http<{ region_ids: string[] }>(`${w(worldId)}/knowledge/${enc(knowledgeId)}/scopes`, {
      method: "PUT",
      body: JSON.stringify({ region_ids: regionIds }),
    }),
  deleteKnowledge: (worldId: string, knowledgeId: string) =>
    http(`${w(worldId)}/knowledge/${enc(knowledgeId)}`, { method: "DELETE" }),
  listUnscoped: (worldId: string) =>
    http<Knowledge[]>(withLang(`${w(worldId)}/knowledge/unscoped`)),
  createNpc: (worldId: string, npc: Partial<NPC>) =>
    http<NPC>(`${w(worldId)}/npcs`, { method: "POST", body: JSON.stringify(npc) }),
  updateNpc: (worldId: string, npc: NPC) =>
    http<NPC>(`${w(worldId)}/npcs/${enc(npc.id)}`, { method: "PUT", body: JSON.stringify(npc) }),
  deleteNpc: (worldId: string, npcId: string) =>
    http(`${w(worldId)}/npcs/${enc(npcId)}`, { method: "DELETE" }),
  draftNpcs: (worldId: string, regionId: string) =>
    http<NpcDraftResult>(`${w(worldId)}/regions/${enc(regionId)}/npc-drafts`, {
      method: "POST",
    }),
  listPriors: (worldId: string) => http<WikiPrior[]>(`${w(worldId)}/priors`),
  priorRefs: (worldId: string) => http<PriorRefsOut>(`${w(worldId)}/prior-refs`),
  deletePrior: (worldId: string, priorId: string) =>
    http(`${w(worldId)}/priors/${enc(priorId)}`, { method: "DELETE" }),

  // augmentation runs — the screen keeps one run (B2)
  startRun: (worldId: string) =>
    http<AugRun>(`${w(worldId)}/augmentation/runs`, { method: "POST" }),
  getRun: (runId: string) => http<AugRun>(`/api/world/augmentation/runs/${enc(runId)}`),
  answer: (runId: string, answer: AugAnswer) =>
    http<AnswerResult>(`/api/world/augmentation/runs/${enc(runId)}/answer`, {
      method: "POST",
      body: JSON.stringify(answer),
    }),
  revert: (runId: string, changeId: string) =>
    http<AugRun>(
      `/api/world/augmentation/runs/${enc(runId)}/revert?change_id=${enc(changeId)}`,
      { method: "POST" },
    ),
  unignore: (runId: string, issueKey: string) =>
    http<AugRun>(`/api/world/augmentation/runs/${enc(runId)}/unignore`, {
      method: "POST",
      body: JSON.stringify({ issue_key: issueKey }),
    }),
};
