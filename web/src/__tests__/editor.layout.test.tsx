// V8 editor screen (FR-S4, frontend-components § 1–5, code plan Step 5.5): TP-V8-1, 3 (the
// inspector opens), 4, 6, 8, 10 (the screen side), 11, 12, 14, 15, 18 and BR-V8-17/19/26/28/33.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import { resetCapabilities } from "../capabilities";
import { stageLabel } from "../features/editor/buildStages";
import { enumLabel } from "../format";
import { WIDE } from "../hooks";
import { t } from "../i18n";
import { EditorPage } from "../routes/EditorPage";
import { openFileMenu } from "../test/editor";
import type {
  AugQuestion,
  AugRun,
  BuildReport,
  ConnectionEdge,
  EditorRegionView,
  Knowledge,
  Region,
  WorldExport,
} from "../types";
import { clearToasts } from "../ui";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn(),
    exportWorld: vi.fn(),
    listWorlds: vi.fn(),
    getEditorRegion: vi.fn(),
    updateRegion: vi.fn(),
    createRegion: vi.fn(),
    saveConnection: vi.fn(),
    deleteConnection: vi.fn(),
    getDeletePlan: vi.fn(),
    deleteRegion: vi.fn(),
    createKnowledge: vi.fn(),
    updateKnowledge: vi.fn(),
    deleteKnowledge: vi.fn(),
    setScopes: vi.fn(),
    listUnscoped: vi.fn(),
    createNpc: vi.fn(),
    updateNpc: vi.fn(),
    deleteNpc: vi.fn(),
    draftNpcs: vi.fn(),
    listPriors: vi.fn(),
    priorRefs: vi.fn(),
    deletePrior: vi.fn(),
    startRun: vi.fn(),
    getRun: vi.fn(),
    answer: vi.fn(),
    revert: vi.fn(),
    unignore: vi.fn(),
    uploadBuild: vi.fn(),
    importWorldFile: vi.fn(),
    getWorldFile: vi.fn(),
    startSession: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;

const REGIONS: Region[] = [
  { id: "r1", name: "Riverton", level: "town", position: { x: 0.2, y: 0.3 } },
  { id: "r2", name: "Hollow", level: "town", position: { x: 0.7, y: 0.6 } },
];
const ROAD: ConnectionEdge = { world_id: "w", source_region_id: "r1", target_region_id: "r2", kind: "route", weight: 0.6 };
const MILL: Knowledge = { id: "k1", world_id: "w", title: "mill", statement: "the mill turns", confidence: 1,
  provenance: { source: "input" } };
const LOST: Knowledge = { id: "k7", world_id: "w", title: "lost bell", statement: "a bell rang once", confidence: 1,
  provenance: { source: "input" } };
const WORLD: WorldExport = { world_id: "w", world: { id: "w", name: "Emberleaf" }, regions: REGIONS, connections: [ROAD],
  entities: [{ id: "e1", name: "Old Bell" }], knowledge: [MILL], scopes: [], unscoped_knowledge_ids: ["k7"] };

function view(id: string): EditorRegionView {
  const region = WORLD.regions.find((r) => r.id === id) ?? { id, name: "Mill", level: "town" };
  const r1 = id === "r1";
  return {
    region: { ...region, world_id: "w" },
    children: [],
    connections: r1 ? [{ key: { world_id: "w", a_region_id: "r1", b_region_id: "r2", kind: "route" },
      other_region_id: "r2", other_region_name: "Hollow", weight: 0.6 }] : [],
    knowledge: r1 ? [{ knowledge: MILL, scope_region_ids: ["r1"] }] : [],
    npcs: r1 ? [{ id: "n1", world_id: "w", name: "Ada", role: "miller", description: "", home_region_id: "r1",
      traits: [], provenance: { source: "input" } }] : [],
  };
}

const lowQ = (over: Partial<AugQuestion> = {}): AugQuestion => ({
  id: "q1", issue_id: "i1", issue_key: "low_confidence:knowledge:k1::", type: "low_confidence",
  text: "Is this right?", actions: ["confirm", "edit", "ignore"], needs: { edit: ["statement"] },
  target: { kind: "knowledge", id: "k1", name: "mill" }, ...over,
});
const gapQ = (over: Partial<AugQuestion> = {}): AugQuestion => ({
  id: "q2", issue_id: "i2", issue_key: "gap:region:r2::", type: "gap", text: "What is known in Hollow?",
  actions: ["add", "ignore"], needs: { add: ["statement", "title"] },
  target: { kind: "region", id: "r2", name: "Hollow" }, ...over,
});
function runOf(over: Partial<AugRun> = {}): AugRun {
  return { id: "run1", world_id: "w", status: "open", answers: 0, ignored_keys: [], history: [], llm_calls: 0,
    llm_budget_exhausted: false, open_questions: [gapQ()], ...over };
}
function report(over: Partial<BuildReport> = {}): BuildReport {
  return { world_id: "w", regions_created: 2, connections_created: 1, entities_created: 1, knowledge_created: 2,
    corroborations_created: 0, warnings: [], unscoped_knowledge_ids: [], llm_calls: 3, embedding_calls: 1,
    replaced: true, closed_session_ids: [], priors_created: 0, ok: true, ...over };
}
function deferred<T>() {
  let resolve: (v: T) => void = () => {};
  let reject: (e: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

let wide = false;
beforeEach(() => {
  vi.clearAllMocks();
  resetCapabilities();
  clearToasts();
  wide = false;
  window.matchMedia = ((q: string) => ({
    matches: wide && q === WIDE, media: q, addEventListener() {}, removeEventListener() {},
  })) as unknown as typeof window.matchMedia;
  (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
  (api.exportWorld as Mock).mockResolvedValue(WORLD);
  (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "Emberleaf", region_count: 2, open_sessions: 0 }]);
  (api.getEditorRegion as Mock).mockImplementation(async (_w: string, id: string) => view(id));
  (api.listUnscoped as Mock).mockResolvedValue([LOST]);
  (api.priorRefs as Mock).mockResolvedValue({ usages: [], broken: [] });
  (api.listPriors as Mock).mockResolvedValue([]);
});
afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  resetCapabilities();
});

function renderEditor() {
  return render(
    <MemoryRouter initialEntries={["/editor/w"]}>
      <Routes>
        <Route path="/editor/:worldId" element={<EditorPage />} />
      </Routes>
    </MemoryRouter>,
  );
}
async function ready() {
  await screen.findByTestId("region-marker-r1");
  await screen.findByTestId("editor-tab-region");
}
function openTab(name: string) {
  const tab = screen.getByTestId(`editor-tab-${name}`).closest('[role="tab"]') as HTMLElement;
  fireEvent.mouseDown(tab, { button: 0 });
}
const selectedTab = () => screen.getByRole("tab", { selected: true });
const fold = (key: string) =>
  screen.getByTestId(`inspector-section-${key}`).querySelector("[aria-expanded]") as HTMLElement;
async function pickOnMap(id: string) {
  fireEvent.click(screen.getByTestId(`region-marker-${id}`));
  await waitFor(() => expect(screen.getByTestId("region-inspector")).toHaveAttribute("aria-label",
    REGIONS.find((r) => r.id === id)?.name));
}
const notices = () => screen.getByTestId("notification-center");

describe("TP-V8-1: the GM's frame — two columns wide, one column narrow, each part once", () => {
  it("wide: the map beside the named panel; the head across", async () => {
    wide = true;
    renderEditor();
    await ready();
    const panel = screen.getByRole("region", { name: t("label.editorPanel") });
    expect(panel).toContainElement(screen.getByTestId("editor-panel"));
    expect(panel).not.toContainElement(screen.getByTestId("map-canvas"));
    expect(panel).not.toContainElement(screen.getByTestId("editor-header"));
    expect(screen.getByTestId("editor-layout")).toHaveAttribute("data-wide", "true");
    for (const id of ["editor-header", "map-canvas", "editor-panel", "world-name"]) expect(screen.getAllByTestId(id)).toHaveLength(1);
  });

  it("narrower: one column — head, map, panel", async () => {
    renderEditor();
    await ready();
    expect(screen.queryByRole("region", { name: t("label.editorPanel") })).not.toBeInTheDocument();
    const order = ["editor-panel", "map-canvas", "editor-header"].map((id) => screen.getByTestId(id))
      .sort((x, y) => (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1))
      .map((e) => e.getAttribute("data-testid"));
    expect(order).toEqual(["editor-header", "map-canvas", "editor-panel"]);
    expect(screen.getByTestId("world-name")).toHaveTextContent("Emberleaf");
  });
});

describe("TP-V8-3 (UX-25): a region made on the map is picked and its inspector opens", () => {
  it("the re-read that brings it picks it, with the region tab open", async () => {
    const MADE: Region = { id: "r9", name: "Mill", level: "town", position: { x: 0.5, y: 0.5 } };
    (api.createRegion as Mock).mockResolvedValue({ ...MADE, world_id: "w" });
    renderEditor();
    await ready();
    openTab("wiki");
    (api.exportWorld as Mock).mockResolvedValue({ ...WORLD, regions: [...REGIONS, MADE] });
    fireEvent.click(screen.getByTestId("map-tool-add-region"));
    fireEvent.click(screen.getByTestId("region-marker-r1").closest("svg") as SVGSVGElement);
    fireEvent.change(screen.getByTestId("new-region-name"), { target: { value: "Mill" } });
    fireEvent.click(screen.getByTestId("new-region-save"));
    await waitFor(() => expect(api.getEditorRegion).toHaveBeenCalledWith("w", "r9"));
    expect(selectedTab()).toHaveTextContent(t("tab.region"));
    await waitFor(() => expect(screen.getByTestId("region-inspector")).toHaveAttribute("aria-label", "Mill"));
    expect(screen.getByTestId("region-picker")).toHaveValue("r9");
    expect(screen.queryByTestId("region-not-found")).not.toBeInTheDocument();
  });
});

describe("TP-V8-4 (UX-24): what was typed in a tab outlives the tab", () => {
  it("an augmentation answer survives a press on the map and the way back", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf());
    renderEditor();
    await ready();
    openTab("augment");
    fireEvent.click(screen.getByTestId("augment-find"));
    fireEvent.change(await screen.findByTestId("augment-statement"), { target: { value: "Wells run dry" } });
    await pickOnMap("r1");
    expect(selectedTab()).toHaveTextContent(t("tab.region"));
    expect(screen.queryByTestId("augment-panel")).not.toBeInTheDocument();
    openTab("augment");
    expect(screen.getByTestId("augment-statement")).toHaveValue("Wells run dry");
    expect(api.startRun).toHaveBeenCalledTimes(1);
  });

  it("an answer that ends while the tab is away clears only that card's draft", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf({ open_questions: [lowQ(), gapQ()] }));
    const answer = deferred<unknown>();
    (api.answer as Mock).mockReturnValue(answer.promise);
    renderEditor();
    await ready();
    openTab("augment");
    fireEvent.click(screen.getByTestId("augment-find"));
    await waitFor(() => expect(screen.getAllByTestId("augment-statement")).toHaveLength(2));
    const [low, gap] = screen.getAllByTestId("augment-statement");
    fireEvent.change(low, { target: { value: "kept" } });
    fireEvent.change(gap, { target: { value: "sent" } });
    fireEvent.click(screen.getAllByTestId("augment-action-add")[0]);
    await waitFor(() => expect(api.answer).toHaveBeenCalledTimes(1));
    await pickOnMap("r2");
    const exports = (api.exportWorld as Mock).mock.calls.length;
    // new question ids, as a re-detection makes them (S28)
    await act(async () => answer.resolve({ change: null, changed: [],
      run: runOf({ answers: 1, open_questions: [lowQ({ id: "q8" }), gapQ({ id: "q9" })] }) }));
    // an answer changed the world: it is read again (BLM § 5)
    await waitFor(() => expect((api.exportWorld as Mock).mock.calls.length).toBe(exports + 1));
    openTab("augment");
    const [low2, gap2] = screen.getAllByTestId("augment-statement");
    expect(low2).toHaveValue("kept");
    expect(gap2).toHaveValue("");
  });

  it("the region picked for knowledge known nowhere survives a press on the map", async () => {
    renderEditor();
    await ready();
    openTab("unscoped");
    fireEvent.change(await screen.findByTestId("unscoped-region-k7"), { target: { value: "r2" } });
    await pickOnMap("r1");
    openTab("unscoped");
    expect(await screen.findByTestId("unscoped-region-k7")).toHaveValue("r2");
  });
});

describe("TP-V8-6 (UX-19): four folding sections, the danger zone apart", () => {
  it("first only the basics open; heads count; folds stay across regions; delete only in the danger zone", async () => {
    renderEditor();
    await ready();
    await pickOnMap("r1");
    expect(fold("basic")).toHaveAttribute("aria-expanded", "true");
    for (const k of ["connections", "knowledge", "npcs"]) expect(fold(k)).toHaveAttribute("aria-expanded", "false");
    expect(fold("connections")).toHaveTextContent(t("label.sectionConnections", { n: 1 }));
    expect(fold("knowledge")).toHaveTextContent(t("label.sectionKnowledge", { n: 1 }));
    expect(fold("npcs")).toHaveTextContent(t("label.sectionNpcs", { n: 1 }));
    fireEvent.click(fold("knowledge"));
    fireEvent.click(fold("basic"));
    fireEvent.change(screen.getByTestId("region-picker"), { target: { value: "r2" } });
    await waitFor(() => expect(screen.getByTestId("region-inspector")).toHaveAttribute("aria-label", "Hollow"));
    expect(fold("knowledge")).toHaveAttribute("aria-expanded", "true");
    expect(fold("basic")).toHaveAttribute("aria-expanded", "false");
    expect(fold("knowledge")).toHaveTextContent(t("label.sectionKnowledge", { n: 0 }));
    const danger = screen.getByTestId("danger-zone");
    expect(danger).toContainElement(screen.getByTestId("region-delete"));
    expect(screen.getAllByTestId("region-delete")).toHaveLength(1);
    fireEvent.click(fold("basic"));
    expect(screen.getByTestId("inspector-section-basic")).not.toContainElement(screen.getByTestId("region-delete"));
    expect(screen.getByTestId("inspector-section-basic")).toContainElement(screen.getByTestId("region-save"));
  });

  it("a line on the map picks its first region and opens the connections section (BLM § 3)", async () => {
    renderEditor();
    await ready();
    fireEvent.click(screen.getByTestId("connection-hit"));
    await waitFor(() => expect(screen.getByTestId("region-inspector")).toHaveAttribute("aria-label", "Riverton"));
    expect(fold("connections")).toHaveAttribute("aria-expanded", "true");
    // the other end's name picks that region
    fireEvent.click(screen.getByTestId("connection-other-r1|r2|route"));
    await waitFor(() => expect(screen.getByTestId("region-inspector")).toHaveAttribute("aria-label", "Hollow"));
  });
});

describe("TP-V8-8 (UX-21): icon buttons say what they do", () => {
  it("each ✕ has a name, and the NPC edit button its own words", async () => {
    renderEditor();
    await ready();
    await pickOnMap("r1");
    for (const k of ["connections", "knowledge", "npcs"]) fireEvent.click(fold(k));
    // code review 01 #32: the far region and the kind, so two kinds of one pair differ
    expect(screen.getByRole("button", { name: t("action.deleteConnection", { name: `Hollow · ${enumLabel("connectionKind", "route")}` }) })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: t("action.deleteKnowledge", { name: "mill" }) })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: t("action.deleteNpc", { name: "Ada" }) })).toBeInTheDocument();
    expect(screen.getByTestId("npc-edit-n1")).toHaveTextContent(t("action.editNpc"));
    openTab("unscoped");
    expect(await screen.findByRole("button", { name: t("action.deleteKnowledge", { name: "lost bell" }) })).toBeInTheDocument();
  });
});

describe("TP-V8-10 (UX-23, BR-V8-17/18): the augmentation state in words", () => {
  it("no fixed answer limit; ignored and kept questions by name; no key text", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf({ answers: 3, ignored_keys: ["gap:region:r2::"],
      kept_keys: ["low_confidence:knowledge:k1::", "orphan:connection:r1|r2|route::"],
      open_questions: [lowQ({ id: "q5", issue_key: "dangling:knowledge:k1:about_entity_ids:gone", type: "dangling",
        actions: ["edit", "ignore"], needs: { edit: ["ref"] }, ref_kind: "entity",
        target: { kind: "knowledge", id: "k1", name: "mill", field: "about_entity_ids" } })] }));
    renderEditor();
    await ready();
    openTab("augment");
    fireEvent.click(screen.getByTestId("augment-find"));
    const status = await screen.findByTestId("augment-status");
    expect(status).toHaveTextContent(enumLabel("augmentationStatus", "open"));
    expect(status).toHaveTextContent(t("label.augmentAnswered", { n: 3 }));
    expect(status.textContent).not.toMatch(/\/\s*\d/);
    expect(screen.getByTestId("augment-ignored")).toHaveTextContent("Hollow");
    const kept = screen.getByTestId("augment-kept");
    expect(kept).toHaveTextContent("mill");
    expect(kept).toHaveTextContent("Riverton");
    expect(screen.getByTestId("augment-field")).toHaveTextContent(t("label.field.about_entity_ids"));
    const panel = screen.getByTestId("augment-panel").textContent ?? "";
    for (const raw of ["gap:region", "low_confidence:", "about_entity_ids", "r1|r2", "/30"]) expect(panel).not.toContain(raw);
  });

  it("a 400 says the answer cannot be saved, the server's reason folded", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf());
    (api.answer as Mock).mockRejectedValue(new HttpError(400, "Bad Request", '{"detail":"no change"}'));
    renderEditor();
    await ready();
    openTab("augment");
    fireEvent.click(screen.getByTestId("augment-find"));
    const add = await screen.findByTestId("augment-action-add");
    await act(async () => fireEvent.click(add));
    await waitFor(() => expect(screen.getByTestId("augment-error")).toHaveTextContent(t("notice.augmentCantSave")));
    expect(screen.getByTestId("augment-error").querySelector("details")).toHaveTextContent("no change");
  });
});

describe("TP-V8-11 (BR-V8-21): loading, missing and failed reads", () => {
  it("the first read shows loading and no empty sentence", async () => {
    const read = deferred<WorldExport>();
    const list = deferred<unknown>();
    (api.exportWorld as Mock).mockReturnValue(read.promise);
    (api.listWorlds as Mock).mockReturnValue(list.promise);
    renderEditor();
    await waitFor(() => expect(api.exportWorld).toHaveBeenCalled());
    expect(within(screen.getByTestId("editor-panel")).getByRole("status")).toBeInTheDocument();
    expect(within(screen.getByTestId("map-canvas")).getByRole("status", { name: t("label.loading") })).toBeInTheDocument();
    expect(screen.queryByTestId("empty-hint")).not.toBeInTheDocument();
    expect(screen.getByTestId("world-name")).toHaveTextContent("w");
    await act(async () => read.resolve(WORLD));
    await act(async () => list.resolve([{ id: "w", name: "Emberleaf", region_count: 2, open_sessions: 0 }]));
    await ready();
    expect(screen.getByTestId("world-name")).toHaveTextContent("Emberleaf");
  });

  it("a world not there yet: its own sentence and [build]; the map tools and play are off", async () => {
    (api.exportWorld as Mock).mockRejectedValue(new HttpError(404, "Not Found", "world not found"));
    renderEditor();
    const empty = await screen.findByTestId("empty-hint");
    expect(empty).toHaveTextContent(t("empty.worldMissing"));
    expect(empty).not.toHaveTextContent(t("empty.noWorlds"));
    expect(screen.getByTestId("map-tool-add-region")).toBeDisabled();
    expect(screen.getByTestId("play-this-world")).toBeDisabled();
    fireEvent.click(within(empty).getByRole("button", { name: t("file.build") }));
    expect(await screen.findByTestId("build-panel")).toBeInTheDocument();
  });

  it("a failed read says why and [retry] reads the world and its sessions again", async () => {
    (api.exportWorld as Mock).mockRejectedValueOnce(new HttpError(500, "Server Error", "graph down"));
    renderEditor();
    const error = await screen.findByTestId("world-error");
    expect(error.querySelector("details")).toHaveTextContent("graph down");
    const lists = (api.listWorlds as Mock).mock.calls.length;
    fireEvent.click(within(error).getByRole("button", { name: t("action.retry") }));
    await ready();
    expect(screen.queryByTestId("world-error")).not.toBeInTheDocument();
    expect((api.listWorlds as Mock).mock.calls.length).toBe(lists + 1);
  });
});

describe("TP-V8-12 (BR-V8-23/25): writes go once and re-read only what they change", () => {
  it("a region save: one request for two presses, the world read once, the sessions not, the inspector kept", async () => {
    const save = deferred<unknown>();
    (api.updateRegion as Mock).mockReturnValue(save.promise);
    renderEditor();
    await ready();
    await pickOnMap("r1");
    const exports = (api.exportWorld as Mock).mock.calls.length;
    const lists = (api.listWorlds as Mock).mock.calls.length;
    fireEvent.click(screen.getByTestId("region-save"));
    fireEvent.click(screen.getByTestId("region-save"));
    const reread = deferred<EditorRegionView>();
    (api.getEditorRegion as Mock).mockReturnValueOnce(reread.promise);
    const regionReads = (api.getEditorRegion as Mock).mock.calls.length;
    await act(async () => save.resolve({}));
    expect(api.updateRegion).toHaveBeenCalledTimes(1);
    expect((api.getEditorRegion as Mock).mock.calls.length).toBe(regionReads + 1); // the inspector re-reads itself
    await waitFor(() => expect((api.exportWorld as Mock).mock.calls.length).toBe(exports + 1));
    expect((api.listWorlds as Mock).mock.calls.length).toBe(lists);
    // the region is read again; until it answers the inspector shows what it had
    expect(screen.getByTestId("region-inspector")).toHaveAttribute("aria-label", "Riverton");
    expect(screen.getByTestId("region-save")).toHaveTextContent(t("notice.saved"));
    await act(async () => reread.resolve(view("r1")));
    expect(screen.getByTestId("region-form")).toBeInTheDocument();
  });
});

describe("TP-V8-12 (BR-V8-10, C1): a drag on the screen", () => {
  it("a drag save reads the open inspector again, and not the world or the sessions", async () => {
    (api.updateRegion as Mock).mockResolvedValue({});
    renderEditor();
    await ready();
    await pickOnMap("r1");
    const regionReads = (api.getEditorRegion as Mock).mock.calls.length;
    const exports = (api.exportWorld as Mock).mock.calls.length;
    const lists = (api.listWorlds as Mock).mock.calls.length;
    const marker = screen.getByTestId("region-marker-r1");
    const svg = marker.closest("svg") as SVGSVGElement;
    fireEvent.pointerDown(marker, { clientX: 100, clientY: 100 });
    fireEvent.pointerMove(svg, { clientX: 130, clientY: 100 });
    fireEvent.pointerUp(svg, { clientX: 130, clientY: 100 });
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledTimes(1));
    await waitFor(() => expect((api.getEditorRegion as Mock).mock.calls.length).toBe(regionReads + 1));
    expect((api.exportWorld as Mock).mock.calls.length).toBe(exports);
    expect((api.listWorlds as Mock).mock.calls.length).toBe(lists);
  });
});

describe("TP-V8-14 (UX-22, BR-V8-29/30): the build report", () => {
  async function build(r: BuildReport) {
    (api.uploadBuild as Mock).mockResolvedValue(r);
    renderEditor();
    await ready();
    openFileMenu();
    fireEvent.click(screen.getByTestId("file-build"));
    fireEvent.change(await screen.findByTestId("build-memo"), { target: { value: "a river town" } });
    await waitFor(() => expect(screen.getByTestId("build-submit")).toBeEnabled());
    fireEvent.click(screen.getByTestId("build-submit"));
    await screen.findByTestId("build-confirm"); // this world exists: replace?
    fireEvent.click(screen.getByText(t("action.confirm")));
    await screen.findByTestId("build-report");
  }

  it("carried counts, warnings by stage folded, the sessions line; the unscoped link opens that tab", async () => {
    await build(report({ carried_npcs: 2, carried_seeds: 1, unscoped_knowledge_ids: ["k7", "k8"], warnings: [
      { stage: "carry-over", severity: "warning", message: "npc n3 had no region to go to" },
      { stage: "carry-over", severity: "warning", message: "seed s2 had no region to go to" },
      { stage: "sessions", severity: "warning", message: "session s9 was mid-turn and could not be closed" },
    ] }));
    expect(screen.getByTestId("build-report-carried")).toHaveTextContent(t("notice.buildCarried", { npcs: 2, seeds: 1 }));
    const carry = screen.getByTestId("build-report-stage-carry-over");
    expect(carry.querySelector("summary")).toHaveTextContent(t("label.stageCount", { stage: stageLabel("carry-over"), n: 2 }));
    expect(carry).not.toHaveAttribute("open");
    expect(carry).toHaveTextContent("npc n3 had no region to go to");
    expect(screen.queryByTestId("build-report-stage-sessions")).not.toBeInTheDocument();
    expect(screen.getByTestId("build-report-sessions")).toHaveTextContent(t("notice.sessionsNotClosed", { n: 1 }));
    fireEvent.click(screen.getByTestId("build-report-unscoped"));
    await waitFor(() => expect(screen.queryByTestId("build-panel")).not.toBeInTheDocument());
    expect(selectedTab()).toHaveTextContent(t("tab.unscoped", { n: 1 }));
    expect(await screen.findByTestId("unscoped-k7")).toBeInTheDocument();
    expect(notices()).toHaveTextContent(t("notice.buildDone")); // BR-V8-26
  });

  it("with nothing carried and nothing unscoped neither line shows", async () => {
    await build(report());
    expect(screen.queryByTestId("build-report-carried")).not.toBeInTheDocument();
    expect(screen.queryByTestId("build-report-unscoped")).not.toBeInTheDocument();
    expect(screen.queryByTestId("build-report-sessions")).not.toBeInTheDocument();
  });
});

describe("TP-V8-15, BR-V8-19/31: the tabs", () => {
  it("named in words, a named tablist, arrow keys move between them", async () => {
    renderEditor();
    await ready();
    const list = screen.getByRole("tablist", { name: t("label.editorTabs") });
    const tabs = within(list).getAllByRole("tab");
    expect(tabs.map((x) => x.textContent)).toEqual([
      t("tab.region"), t("tab.unscoped", { n: 1 }), t("tab.augment"), t("tab.wiki")]);
    expect(list.textContent).not.toMatch(/wiki|스코프/);
    tabs[0].focus();
    fireEvent.keyDown(tabs[0], { key: "ArrowRight" });
    await waitFor(() => expect(document.activeElement).toBe(tabs[1]));
  });
});

describe("TP-V8-18 (BLM § 1.4, R-02): a world replaced clears what belonged to the old one", () => {
  it("a build that replaces: the run, its drafts and the picks go; the inspector and the open list read again", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf());
    (api.uploadBuild as Mock).mockResolvedValue(report());
    renderEditor();
    await ready();
    await pickOnMap("r1");
    openTab("augment");
    fireEvent.click(screen.getByTestId("augment-find"));
    fireEvent.change(await screen.findByTestId("augment-statement"), { target: { value: "draft" } });
    openTab("unscoped");
    fireEvent.change(await screen.findByTestId("unscoped-region-k7"), { target: { value: "r2" } });
    const regionReads = (api.getEditorRegion as Mock).mock.calls.length;
    const unscopedReads = (api.listUnscoped as Mock).mock.calls.length;
    openFileMenu();
    fireEvent.click(screen.getByTestId("file-build"));
    fireEvent.change(await screen.findByTestId("build-memo"), { target: { value: "again" } });
    await waitFor(() => expect(screen.getByTestId("build-submit")).toBeEnabled());
    fireEvent.click(screen.getByTestId("build-submit"));
    await screen.findByTestId("build-confirm");
    fireEvent.click(screen.getByText(t("action.confirm")));
    await screen.findByTestId("build-report");
    await waitFor(() => expect((api.listUnscoped as Mock).mock.calls.length).toBe(unscopedReads + 1));
    fireEvent.click(screen.getByText(t("action.close")));
    expect(await screen.findByTestId("unscoped-region-k7")).toHaveValue("");
    openTab("augment");
    expect(screen.queryByTestId("augment-status")).not.toBeInTheDocument();
    expect(screen.queryByTestId("augment-statement")).not.toBeInTheDocument();
    openTab("region");
    // r1 is still in the world: it stays chosen and reads its new content
    await waitFor(() => expect((api.getEditorRegion as Mock).mock.calls.length).toBeGreaterThan(regionReads));
    expect(screen.getByTestId("region-picker")).toHaveValue("r1");
  });

  it("a World File load says so and clears the same way (BR-V8-26)", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf());
    (api.importWorldFile as Mock).mockResolvedValue({ world_id: "w", format_version: 1, source_world_id: "w",
      remapped: false, forced: false, replaced: true, closed_session_ids: ["s1", "s2"], counts: {}, warnings: [], ok: true });
    renderEditor();
    await ready();
    openTab("augment");
    fireEvent.click(screen.getByTestId("augment-find"));
    await screen.findByTestId("augment-status");
    const file = new File(['{"format_version": 1}'], "w.world.json", { type: "application/json" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [file] } });
    await waitFor(() => screen.getByTestId("file-confirm"));
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() => expect(notices()).toHaveTextContent(t("notice.loadedClosed", { n: 2 })));
    expect(screen.queryByTestId("augment-status")).not.toBeInTheDocument();
  });
});

describe("BR-V8-26/28: notices and the open-session line", () => {
  it("a region delete says which region went and drops the selection", async () => {
    (api.getDeletePlan as Mock).mockResolvedValue({ region_id: "r1", region_name: "Riverton", children: [],
      connections: [], npcs: [], knowledge_to_unscope: [], knowledge_scope_removed: [], entities_unlocated: [],
      blocked_by_sessions: [] });
    (api.deleteRegion as Mock).mockResolvedValue({ region_id: "r1", region_name: "Riverton", children: [],
      connections: [], npcs: [], knowledge_to_unscope: [], knowledge_scope_removed: [], entities_unlocated: [],
      blocked_by_sessions: [], deleted_ids: ["r1"] });
    renderEditor();
    await ready();
    await pickOnMap("r1");
    fireEvent.click(screen.getByTestId("region-delete"));
    fireEvent.click(await screen.findByText(t("delete.confirm")));
    await waitFor(() => expect(notices()).toHaveTextContent(t("notice.regionDeleted", { name: "Riverton" })));
    expect(screen.queryByTestId("region-inspector")).not.toBeInTheDocument();
    expect(screen.getByTestId("region-tab")).toHaveTextContent(t("hint.pickRegionEditor"));
  });

  it("open sessions are counted in the head, and not shown at zero", async () => {
    (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "Emberleaf", region_count: 2, open_sessions: 2 }]);
    const { unmount } = renderEditor();
    expect(await screen.findByTestId("open-sessions")).toHaveTextContent(t("notice.openSessions", { n: 2 }));
    unmount();
    (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "Emberleaf", region_count: 2, open_sessions: 0 }]);
    renderEditor();
    await ready();
    expect(screen.queryByTestId("open-sessions")).not.toBeInTheDocument();
  });
});

describe("BR-V8-33: every control has a label; a dialog closes on Esc", () => {
  it("the inspector's and the new-region dialog's controls are all named", async () => {
    renderEditor();
    await ready();
    await pickOnMap("r1");
    for (const k of ["connections", "knowledge", "npcs"]) fireEvent.click(fold(k));
    fireEvent.click(screen.getByTestId("knowledge-add"));
    fireEvent.click(screen.getByTestId("npc-add"));
    const unnamed = (root: HTMLElement) =>
      [...root.querySelectorAll<HTMLElement>("input:not([type=hidden]):not([type=file]), select, textarea")].filter(
        (el) => !(el as HTMLInputElement).labels?.length && !el.getAttribute("aria-label") && !el.getAttribute("aria-labelledby"),
      ).map((el) => el.getAttribute("data-testid"));
    expect(unnamed(screen.getByTestId("editor-panel"))).toEqual([]);
    fireEvent.click(screen.getByTestId("map-tool-add-region"));
    fireEvent.click(screen.getByTestId("region-marker-r1").closest("svg") as SVGSVGElement);
    const dialog = await screen.findByRole("dialog");
    expect(unnamed(dialog)).toEqual([]);
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(document.activeElement).toBe(screen.getByTestId("map-tool-add-region"))); // its opener
  });
});

describe("code review 01 #12: each write re-reads what it changed (BLM § 5)", () => {
  it("the connect tool re-reads the world and the open inspector", async () => {
    (api.saveConnection as Mock).mockResolvedValue([]);
    renderEditor();
    await ready();
    await pickOnMap("r1");
    const regionReads = (api.getEditorRegion as Mock).mock.calls.length;
    const exports = (api.exportWorld as Mock).mock.calls.length;
    fireEvent.click(screen.getByTestId("map-tool-connect"));
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    fireEvent.click(screen.getByTestId("region-marker-r2"));
    fireEvent.change(await screen.findByTestId("connection-kind"), { target: { value: "river" } });
    fireEvent.click(screen.getByTestId("connection-save"));
    await waitFor(() => expect(api.saveConnection).toHaveBeenCalledTimes(1));
    await waitFor(() => expect((api.getEditorRegion as Mock).mock.calls.length).toBe(regionReads + 1));
    expect((api.exportWorld as Mock).mock.calls.length).toBe(exports + 1);
  });

  it("assigning a region to knowledge known nowhere re-reads the world (its count)", async () => {
    (api.setScopes as Mock).mockResolvedValue({ region_ids: ["r2"] });
    renderEditor();
    await ready();
    openTab("unscoped");
    fireEvent.change(await screen.findByTestId("unscoped-region-k7"), { target: { value: "r2" } });
    const exports = (api.exportWorld as Mock).mock.calls.length;
    fireEvent.click(screen.getByTestId("unscoped-assign-k7"));
    await waitFor(() => expect((api.exportWorld as Mock).mock.calls.length).toBe(exports + 1));
  });

  it("deleting a prior re-reads the world; a replace re-reads the grounds tab", async () => {
    (api.priorRefs as Mock).mockResolvedValue({ usages: [{ prior: { id: "p1", world_id: "w", prior_type: "fact",
      condition: "river", effect: "trade", domains: ["geography"], confidence: 0.8 }, connections: [], knowledge: [] }], broken: [] });
    (api.deletePrior as Mock).mockResolvedValue({});
    (api.importWorldFile as Mock).mockResolvedValue({ world_id: "w", format_version: 1, source_world_id: "w",
      remapped: false, forced: false, replaced: true, closed_session_ids: [], counts: {}, warnings: [], ok: true });
    renderEditor();
    await ready();
    openTab("wiki");
    const card = await screen.findByTestId("prior-p1");
    const exports = (api.exportWorld as Mock).mock.calls.length;
    fireEvent.click(within(card).getByRole("button", { name: t("wiki.delete") }));
    await screen.findByTestId("confirm-delete");
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("delete.confirm") }));
    await waitFor(() => expect((api.exportWorld as Mock).mock.calls.length).toBe(exports + 1));
    const refs = (api.priorRefs as Mock).mock.calls.length;
    const file = new File(['{"format_version": 1}'], "w.world.json", { type: "application/json" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [file] } });
    await waitFor(() => screen.getByTestId("file-confirm"));
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() => expect((api.priorRefs as Mock).mock.calls.length).toBeGreaterThan(refs));
  });
});

describe("code review 01 #14: on a narrow screen a press on the map scrolls to the panel", () => {
  const proto = Element.prototype as unknown as { scrollIntoView?: (arg?: unknown) => void };
  let had: typeof proto.scrollIntoView;
  beforeEach(() => {
    had = proto.scrollIntoView;
  });
  afterEach(() => {
    proto.scrollIntoView = had;
  });

  it("narrow: the panel is scrolled to once; wide: not at all", async () => {
    const calls: Element[] = [];
    proto.scrollIntoView = function (this: Element) {
      calls.push(this);
    };
    const { unmount } = renderEditor();
    await ready();
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    expect(calls).toEqual([screen.getByTestId("editor-panel")]);
    unmount();
    calls.length = 0;
    wide = true;
    renderEditor();
    await ready();
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    expect(calls).toEqual([]);
  });
});

describe("code review 01 #5, #6: the keyboard focus stays where the work is", () => {
  it("[자료로 만들기] from the file row: closing the dialog gives the focus back to [파일 ▾]", async () => {
    renderEditor();
    await ready();
    openFileMenu();
    const build = screen.getByTestId("file-build");
    build.focus(); // a browser focuses a pressed button
    fireEvent.click(build);
    const dialog = await screen.findByTestId("build-panel");
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByTestId("build-panel")).not.toBeInTheDocument());
    await waitFor(() => expect(document.activeElement).toBe(screen.getByTestId("file-menu")));
  });

  it("[불러오기] from the file row: the focus is on [파일 ▾] while the file picker is up", async () => {
    renderEditor();
    await ready();
    openFileMenu();
    const loadBtn = screen.getByTestId("file-load");
    loadBtn.focus();
    fireEvent.click(loadBtn);
    expect(document.activeElement).toBe(screen.getByTestId("file-menu"));
  });

  it("a weight step keeps the slider on and focused while its save is out", async () => {
    const save = deferred<unknown>();
    (api.saveConnection as Mock).mockReturnValue(save.promise);
    renderEditor();
    await ready();
    await pickOnMap("r1");
    fireEvent.click(fold("connections"));
    const range = screen.getByTestId("connection-weight-r1|r2|route") as HTMLInputElement;
    range.focus();
    fireEvent.change(range, { target: { value: "0.65" } });
    fireEvent.keyUp(range, { key: "ArrowRight" });
    await waitFor(() => expect(api.saveConnection).toHaveBeenCalledTimes(1));
    expect(range).toBeEnabled();
    expect(document.activeElement).toBe(range);
    // a second step while the first is out is refused: the thumb goes back to the stored
    // weight until the first save's re-read brings the new one
    fireEvent.change(range, { target: { value: "0.7" } });
    fireEvent.keyUp(range, { key: "ArrowRight" });
    await waitFor(() => expect(range.value).toBe("0.6"));
    expect(api.saveConnection).toHaveBeenCalledTimes(1);
    expect(document.activeElement).toBe(range);
    await act(async () => save.resolve([]));
  });

  it("[저장] keeps the focus after the region is saved and drawn again", async () => {
    (api.updateRegion as Mock).mockResolvedValue({});
    renderEditor();
    await ready();
    await pickOnMap("r1");
    (api.getEditorRegion as Mock).mockImplementation(async (_w: string, id: string) =>
      id === "r1" ? { ...view("r1"), region: { ...view("r1").region, name: "Riverton Port" } } : view(id));
    const saveBtn = screen.getByTestId("region-save");
    saveBtn.focus();
    fireEvent.change(screen.getByTestId("region-name"), { target: { value: "Riverton Port" } });
    fireEvent.click(saveBtn);
    await waitFor(() => expect(screen.getByTestId("region-save")).toHaveTextContent(t("notice.saved")));
    await waitFor(() => expect(document.activeElement).toBe(screen.getByTestId("region-save")));
  });
});

describe("code review 01 #7, #31: long words wrap; the narrow panel is a screen tall", () => {
  it("a connection's grounds, a person's lines and a scope badge wrap anywhere", async () => {
    (api.getEditorRegion as Mock).mockImplementation(async (_w: string, id: string) => {
      const v = view(id);
      return id === "r1" ? { ...v, connections: v.connections.map((c) => ({ ...c, rationale: "https://example.org/a-very-long-unbroken-reference" })) } : v;
    });
    renderEditor();
    await ready();
    await pickOnMap("r1");
    for (const k of ["connections", "knowledge", "npcs"]) fireEvent.click(fold(k));
    const card = screen.getByTestId("connection-r1|r2|route");
    expect(within(card).getByText(/a-very-long-unbroken-reference/)).toHaveClass("[overflow-wrap:anywhere]");
    expect(within(screen.getByTestId("editor-npc-n1")).getByText(/miller/)).toHaveClass("[overflow-wrap:anywhere]");
  });

  it("narrow: the panel is at least a screen tall; wide: as tall as its content", async () => {
    const { unmount } = renderEditor();
    await ready();
    expect(screen.getByTestId("editor-panel")).toHaveClass("min-h-screen");
    unmount();
    wide = true;
    renderEditor();
    await ready();
    expect(screen.getByTestId("editor-panel")).not.toHaveClass("min-h-screen");
  });
});
