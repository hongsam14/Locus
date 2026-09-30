// `/api/world` — world editor: build, export, edit nodes, augmentation runs.
import type {
  AugAnswer,
  AugRun,
  BuildReport,
  DemoInfo,
  ImportReport,
  Region,
  WorldExport,
  WorldFile,
  WorldInfo,
} from "../types";
import { BASE, enc, http } from "./http";

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
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
      return (await res.json()) as BuildReport;
    }),
  getWorldFile: (worldId: string) => http<WorldFile>(`/api/world/worlds/${enc(worldId)}/file`),
  importWorldFile: (worldId: string, file: WorldFile | object, options?: ReplaceOptions & { remap?: boolean }) =>
    http<ImportReport>(
      `/api/world/worlds/${enc(worldId)}/file?${replaceQuery(options, { remap: String(options?.remap ?? false) })}`,
      { method: "POST", body: JSON.stringify(file) },
    ),
  listWorlds: () => http<WorldInfo[]>(`/api/world/worlds`),
  listDemos: () => http<DemoInfo[]>(`/api/world/demos`),
  // Loads the packaged demo World File — no LLM call (FR-B3, US-1.3).
  loadDemo: (worldId: string, name = "aldermoor", options?: ReplaceOptions) =>
    http<ImportReport>(
      `/api/world/worlds/${enc(worldId)}/demo/${enc(name)}?${replaceQuery(options)}`,
      { method: "POST" },
    ),
  // Development path: build the demo from its raw sources through the LLM pipeline.
  buildWorldDemo: (worldId: string, options?: ReplaceOptions) =>
    http<BuildReport>(
      `/api/world/worlds/${enc(worldId)}/demo/aldermoor/build?${replaceQuery(options)}`,
      { method: "POST" },
    ),
  upsertRegion: (worldId: string, region: Region) =>
    http<Region>(`/api/world/worlds/${enc(worldId)}/regions/${enc(region.id)}`, {
      method: "PUT",
      body: JSON.stringify(region),
    }),
  deleteNode: (worldId: string, nodeId: string) =>
    http(`/api/world/worlds/${enc(worldId)}/nodes/${enc(nodeId)}`, { method: "DELETE" }),

  // augmentation runs (AugmentationRun; was "augment session")
  startAugment: (worldId: string) =>
    http<AugRun>(`/api/world/worlds/${enc(worldId)}/augmentation/runs`, { method: "POST" }),
  submitAnswer: (runId: string, answer: AugAnswer) =>
    http(`/api/world/augmentation/runs/${enc(runId)}/answer`, {
      method: "POST",
      body: JSON.stringify(answer),
    }),
  revertAugment: (runId: string, changeId: string) =>
    http(`/api/world/augmentation/runs/${enc(runId)}/revert?change_id=${enc(changeId)}`, {
      method: "POST",
    }),
};
