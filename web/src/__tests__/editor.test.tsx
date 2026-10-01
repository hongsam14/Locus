// U3 world editor (frontend-components §6, EX-11, BR-U3-24..32).
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import { resetCapabilities } from "../capabilities";
import { AugmentPanel } from "../features/editor/AugmentPanel";
import { BuildPanel } from "../features/editor/BuildPanel";
import { ConfirmDelete } from "../features/editor/ConfirmDelete";
import { NpcDraftCards } from "../features/editor/NpcDraftCards";
import { isDrag } from "../features/editor/drag";
import { MapCanvas } from "../features/editor/MapCanvas";
import { KnowledgeList } from "../features/editor/KnowledgeList";
import { WorldFileBar } from "../features/editor/WorldFileBar";
import { MapOverlay } from "../MapOverlay";
import { EditorPage } from "../routes/EditorPage";
import { RegionInspector } from "../features/editor/RegionInspector";
import { UnscopedPanel } from "../features/editor/UnscopedPanel";
import { WikiPanel } from "../features/editor/WikiPanel";
import { t } from "../i18n";
import type {
  AugQuestion,
  AugRun,
  ConnectionEdge,
  EditorRegionView,
  Region,
  RegionDeletePlan,
  WorldExport,
} from "../types";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn().mockResolvedValue({ llm: true, vlm: true, embedding: true }),
    getEditorRegion: vi.fn(),
    updateRegion: vi.fn(),
    getDeletePlan: vi.fn(),
    deleteRegion: vi.fn(),
    saveConnection: vi.fn(),
    deleteConnection: vi.fn(),
    createKnowledge: vi.fn(),
    updateKnowledge: vi.fn(),
    setScopes: vi.fn(),
    deleteKnowledge: vi.fn(),
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
    exportWorld: vi.fn(),
    listWorlds: vi.fn(),
    createRegion: vi.fn(),
    importWorldFile: vi.fn(),
    getWorldFile: vi.fn(),
    listSessions: vi.fn().mockResolvedValue([]),
    startSession: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;
const regions: Region[] = [
  { id: "r1", name: "Riverton", level: "town", position: { x: 0.2, y: 0.3 } },
  { id: "r2", name: "Hollow", level: "town", position: { x: 0.7, y: 0.6 } },
];

beforeEach(() => vi.clearAllMocks());

describe("drag threshold (BR-U3-30)", () => {
  it("only counts past 4px", () => {
    expect(isDrag({ x: 0, y: 0 }, { x: 3, y: 2 })).toBe(false);
    expect(isDrag({ x: 0, y: 0 }, { x: 10, y: 0 })).toBe(true);
  });
});

describe("MapCanvas tools (Q5=A)", () => {
  function setup() {
    const props = {
      onSelect: vi.fn(), onSelectConnection: vi.fn(), onMove: vi.fn(),
      onCreateRegion: vi.fn(), onCreateConnection: vi.fn(),
    };
    render(<MapCanvas regions={regions} connections={[]} selectedId={null} selectedConnection={null} {...props} />);
    return props;
  }

  it("EX-11: a click saves nothing, a 10px drag saves once", () => {
    const p = setup();
    const marker = screen.getByTestId("region-marker-r1");
    const svg = marker.closest("svg") as SVGSVGElement;
    fireEvent.pointerDown(marker, { clientX: 100, clientY: 100 });
    fireEvent.pointerUp(svg, { clientX: 100, clientY: 100 });
    fireEvent.click(marker);
    expect(p.onMove).not.toHaveBeenCalled();
    expect(p.onSelect).toHaveBeenCalledWith("r1");
    fireEvent.pointerDown(marker, { clientX: 100, clientY: 100 });
    fireEvent.pointerMove(svg, { clientX: 110, clientY: 100 });
    fireEvent.pointerUp(svg, { clientX: 110, clientY: 100 });
    expect(p.onMove).toHaveBeenCalledTimes(1);
  });

  it("add region: a click on empty map opens the form at that spot", () => {
    const p = setup();
    fireEvent.click(screen.getByTestId("map-tool-add-region"));
    const svg = screen.getByTestId("region-marker-r1").closest("svg") as SVGSVGElement;
    fireEvent.click(svg);
    fireEvent.change(screen.getByTestId("new-region-name"), { target: { value: "Mill" } });
    fireEvent.click(screen.getByTestId("new-region-save"));
    expect(p.onCreateRegion).toHaveBeenCalledWith(expect.objectContaining({ name: "Mill", level: "town" }));
  });

  it("connect: two regions in turn open the connection form", () => {
    const p = setup();
    fireEvent.click(screen.getByTestId("map-tool-connect"));
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    expect(screen.getByTestId("map-hint")).toHaveTextContent("Riverton");
    fireEvent.click(screen.getByTestId("region-marker-r2"));
    fireEvent.change(screen.getByTestId("connection-kind"), { target: { value: "river" } });
    fireEvent.click(screen.getByTestId("connection-save"));
    expect(p.onCreateConnection).toHaveBeenCalledWith("r1", "r2", "river", 0.6);
    expect(p.onSelect).not.toHaveBeenCalled();
  });
});

const VIEW: EditorRegionView = {
  region: { id: "r1", world_id: "w", name: "Riverton", level: "town" },
  children: [],
  connections: [{ key: { world_id: "w", a_region_id: "r1", b_region_id: "r2", kind: "route" },
    other_region_id: "r2", other_region_name: "Hollow", weight: 0.6,
    prior: { prior_id: "p9", broken: true } }],
  knowledge: [{ knowledge: { id: "k1", world_id: "w", statement: "the mill turns", title: "mill",
    confidence: 1, provenance: { source: "input" }, statement_ko: "물레방아가 돈다" },
    scope_region_ids: ["r1"] }],
  npcs: [],
};

describe("RegionInspector (US-2.2·2.3·2.4·2.5)", () => {
  beforeEach(() => (api.getEditorRegion as Mock).mockResolvedValue(VIEW));
  const open = () =>
    render(<RegionInspector worldId="w" regionId="r1" regions={regions} onChanged={() => {}} onDeleted={() => {}} />);

  it("shows translated knowledge, broken grounds, and adds knowledge to this region", async () => {
    (api.createKnowledge as Mock).mockResolvedValue({});
    open();
    await waitFor(() => expect(screen.getByTestId("editor-knowledge-text-k1")).toHaveTextContent("물레방아"));
    expect(screen.getByTestId("connection-prior-r1|r2|route")).toHaveTextContent("p9");
    fireEvent.click(screen.getByTestId("knowledge-add"));
    fireEvent.change(screen.getByTestId("knowledge-statement"), { target: { value: "a dry well" } });
    fireEvent.click(screen.getByTestId("knowledge-save"));
    await waitFor(() => expect(api.createKnowledge).toHaveBeenCalledWith("w", "r1",
      expect.objectContaining({ statement: "a dry well", world_id: "w" })));
  });

  it("reads the region again when the page re-read the world, so a save keeps a drag", async () => {
    // U3 review #1 (BR-U3-1): the form saves the whole region; a stale view undid a drag
    (api.updateRegion as Mock).mockResolvedValue({});
    const props = { worldId: "w", regionId: "r1", regions, onChanged: () => {}, onDeleted: () => {} };
    const { rerender } = render(<RegionInspector {...props} reloadKey={0} />);
    await waitFor(() => screen.getByTestId("region-form"));
    (api.getEditorRegion as Mock).mockResolvedValue({
      ...VIEW, region: { ...VIEW.region, position: { x: 0.5, y: 0.5 } },
    });
    rerender(<RegionInspector {...props} reloadKey={1} />); // the page moved the marker
    await waitFor(() => expect(api.getEditorRegion).toHaveBeenCalledTimes(2));
    fireEvent.change(screen.getByTestId("region-description"), { target: { value: "by the river" } });
    fireEvent.click(screen.getByTestId("region-save"));
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledWith("w",
      expect.objectContaining({ position: { x: 0.5, y: 0.5 }, description: "by the river" })));
  });

  it("an empty or unreadable weight box saves nothing and shows the saved weight again", async () => {
    // U3 review #5: Number("") is 0, which blocked the path
    open();
    const box = (await screen.findByTestId("connection-weight-r1|r2|route")) as HTMLInputElement;
    for (const typed of ["", "abc", "1.5"]) {
      fireEvent.change(box, { target: { value: typed } });
      fireEvent.blur(box);
      expect(box.value).toBe("0.6");
    }
    expect(api.saveConnection).not.toHaveBeenCalled();
  });

  it("sets scopes to the picked regions", async () => {
    (api.setScopes as Mock).mockResolvedValue({ region_ids: ["r1", "r2"] });
    open();
    await waitFor(() => screen.getByTestId("knowledge-scopes-k1"));
    fireEvent.click(screen.getByTestId("knowledge-scopes-k1"));
    fireEvent.click(screen.getByTestId("scope-r2"));
    fireEvent.click(screen.getByTestId("scope-save"));
    await waitFor(() => expect(api.setScopes).toHaveBeenCalledWith("w", "k1", ["r1", "r2"]));
  });

  it("suggests NPCs and saves only the accepted one; a failed call is a notice", async () => {
    (api.draftNpcs as Mock).mockResolvedValueOnce({ region_id: "r1", llm_calls: 1, failed: false,
      drafts: [1, 2, 3].map((i) => ({ name: `N${i}`, role: "r", description: "d", traits: [] })) });
    (api.createNpc as Mock).mockResolvedValue({});
    open();
    await waitFor(() => screen.getByTestId("npc-suggest"));
    fireEvent.click(screen.getByTestId("npc-suggest"));
    await waitFor(() => expect(screen.getAllByTestId("npc-draft-card")).toHaveLength(3));
    fireEvent.click(screen.getAllByTestId("npc-draft-accept")[1]);
    await waitFor(() => expect(api.createNpc).toHaveBeenCalledTimes(1));
    expect(api.createNpc).toHaveBeenCalledWith("w", expect.objectContaining({ name: "N2", home_region_id: "r1" }));
    (api.draftNpcs as Mock).mockResolvedValueOnce({ region_id: "r1", drafts: [], llm_calls: 1, failed: true });
    fireEvent.click(screen.getByTestId("npc-suggest"));
    await waitFor(() => expect(screen.getByTestId("npc-draft-failed")).toBeInTheDocument());
  });

  it("deletes a region through its plan", async () => {
    const plan: RegionDeletePlan = { region_id: "r1", region_name: "Riverton", children: [],
      connections: [VIEW.connections[0].key], npcs: [{ id: "n1", name: "Ada" }],
      knowledge_to_unscope: [{ id: "k1", name: "mill" }], knowledge_scope_removed: [],
      entities_unlocated: [], blocked_by_sessions: [] };
    (api.getDeletePlan as Mock).mockResolvedValue(plan);
    (api.deleteRegion as Mock).mockResolvedValue({ ...plan, deleted_ids: ["r1", "n1"] });
    const onDeleted = vi.fn();
    render(<RegionInspector worldId="w" regionId="r1" regions={regions} onChanged={() => {}} onDeleted={onDeleted} />);
    await waitFor(() => screen.getByTestId("region-delete"));
    fireEvent.click(screen.getByTestId("region-delete"));
    await waitFor(() => expect(screen.getByTestId("delete-plan")).toHaveTextContent("Ada"));
    fireEvent.click(screen.getByText(t("delete.confirm")));
    await waitFor(() => expect(api.deleteRegion).toHaveBeenCalledWith("w", "r1"));
    expect(onDeleted).toHaveBeenCalled();
  });
});

describe("ConfirmDelete (BR-U3-9/16)", () => {
  it("cannot be confirmed while a player stands there", () => {
    const onConfirm = vi.fn();
    render(<ConfirmDelete open plan={{ region_id: "r1", region_name: "Riverton", children: [],
      connections: [], npcs: [], knowledge_to_unscope: [], knowledge_scope_removed: [],
      entities_unlocated: [], blocked_by_sessions: ["s1"] }} onConfirm={onConfirm} onCancel={() => {}} />);
    expect(screen.getByTestId("delete-blocked")).toHaveTextContent("s1");
    expect(screen.getByText(t("delete.confirm"))).toBeDisabled();
  });
});

describe("UnscopedPanel (BR-U3-14)", () => {
  it("assigns a region and the item leaves the list", async () => {
    (api.listUnscoped as Mock)
      .mockResolvedValueOnce([{ id: "k9", world_id: "w", statement: "lost", title: "lost", confidence: 1, provenance: { source: "input" } }])
      .mockResolvedValueOnce([]);
    (api.setScopes as Mock).mockResolvedValue({ region_ids: ["r2"] });
    // U8 intended change: U3 review C12 — the panel no longer reads again on its own; the
    // page re-reads the world and bumps reloadKey, as EditorPage does
    function Page() {
      const [rev, setRev] = useState(0);
      return <UnscopedPanel worldId="w" regions={regions} reloadKey={rev} onChanged={() => setRev((r) => r + 1)} />;
    }
    render(<Page />);
    await waitFor(() => screen.getByTestId("unscoped-k9"));
    fireEvent.change(screen.getByTestId("unscoped-region-k9"), { target: { value: "r2" } });
    fireEvent.click(screen.getByTestId("unscoped-assign-k9"));
    await waitFor(() => expect(api.setScopes).toHaveBeenCalledWith("w", "k9", ["r2"]));
    await waitFor(() => expect(screen.queryByTestId("unscoped-k9")).not.toBeInTheDocument());
    expect(api.listUnscoped).toHaveBeenCalledTimes(2); // the mount read and one after the write
  });
});

function runOf(over: Partial<AugRun> = {}): AugRun {
  return { id: "run1", world_id: "w", status: "open", answers: 0, ignored_keys: [], history: [],
    llm_calls: 0, llm_budget_exhausted: false,
    open_questions: [{ id: "q1", issue_id: "i1", issue_key: "low_confidence:knowledge:k1::",
      text: "Is this right?", actions: ["confirm", "edit", "remove", "ignore"],
      target: { kind: "knowledge", id: "k1", name: "mill", region_name: "Riverton" } }], ...over };
}

describe("AugmentPanel (BR-U3-24..28)", () => {
  it("keeps one run, shows the target, offers only the server's actions and undoes latest first", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf());
    const first = { id: "c1", description: "low_confidence:confirm", added_ids: [], reverted: false };
    const second = { id: "c2", description: "low_confidence:confirm", added_ids: [], reverted: false };
    (api.answer as Mock)
      .mockResolvedValueOnce({ change: first, changed: [{ kind: "knowledge", id: "k1", name: "mill" }],
        run: runOf({ answers: 1, history: [first] }) })
      .mockResolvedValueOnce({ change: second, changed: [],
        run: runOf({ answers: 2, history: [first, second] }) });
    (api.revert as Mock).mockResolvedValue(runOf({ answers: 2, history: [first, { ...second, reverted: true }] }));
    render(<AugmentPanel worldId="w" regions={regions} entities={[]} onChanged={() => {}} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    await waitFor(() => expect(screen.getByTestId("augment-target")).toHaveTextContent("mill"));
    expect(screen.queryByTestId("augment-action-add")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("augment-action-confirm"));
    await waitFor(() => expect(screen.getAllByTestId("augment-change")).toHaveLength(1));
    fireEvent.click(screen.getByTestId("augment-action-confirm"));
    await waitFor(() => expect(screen.getAllByTestId("augment-change")).toHaveLength(2));
    expect(api.startRun).toHaveBeenCalledTimes(1); // the run is kept (B2)
    const reverts = screen.getAllByTestId("augment-revert");
    expect(reverts[0]).not.toBeDisabled(); // the latest (listed first)
    expect(reverts[1]).toBeDisabled();
    fireEvent.click(reverts[0]);
    await waitFor(() => expect(api.revert).toHaveBeenCalledWith("run1", "c2"));
    await waitFor(() => expect(screen.getByText(t("augment.reverted"))).toBeInTheDocument());
  });

  it("hands its run id to the page and reads the run again when it comes back", async () => {
    // U3 review #2 (BR-U3-26): a click on the map unmounts the tab; the run must survive
    const change = { id: "c1", description: "low_confidence:confirm", added_ids: [], reverted: false };
    (api.startRun as Mock).mockResolvedValue(runOf());
    (api.getRun as Mock).mockResolvedValue(runOf({ answers: 1, history: [change] }));
    const onRunId = vi.fn();
    const { unmount } = render(
      <AugmentPanel worldId="w" regions={regions} entities={[]} onChanged={() => {}} onRunId={onRunId} />,
    );
    fireEvent.click(screen.getByTestId("augment-find"));
    await waitFor(() => expect(onRunId).toHaveBeenCalledWith("run1"));
    unmount();
    render(<AugmentPanel worldId="w" regions={regions} entities={[]} onChanged={() => {}} runId="run1" />);
    await waitFor(() => expect(api.getRun).toHaveBeenCalledWith("run1"));
    await waitFor(() => expect(screen.getAllByTestId("augment-revert")[0]).not.toBeDisabled());
    expect(api.startRun).toHaveBeenCalledTimes(1);
  });

  it("a run the server no longer has is reported lost when the panel comes back", async () => {
    (api.getRun as Mock).mockRejectedValue(new HttpError(404, "Not Found", "run not found"));
    render(<AugmentPanel worldId="w" regions={regions} entities={[]} onChanged={() => {}} runId="gone" />);
    await waitFor(() => expect(screen.getByTestId("augment-lost")).toBeInTheDocument());
  });

  it("a lost run (404 after a restart) offers a new search", async () => {
    (api.startRun as Mock).mockResolvedValue(runOf());
    (api.answer as Mock).mockRejectedValue(new HttpError(404, "Not Found", "run not found"));
    // U8 intended change: U3 review #12 — a 404 is "lost" only when the run is gone too
    (api.getRun as Mock).mockRejectedValue(new HttpError(404, "Not Found", "run not found"));
    render(<AugmentPanel worldId="w" regions={regions} entities={[]} onChanged={() => {}} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    await waitFor(() => screen.getByTestId("augment-action-ignore"));
    await act(async () => fireEvent.click(screen.getByTestId("augment-action-ignore")));
    await waitFor(() => expect(screen.getByTestId("augment-lost")).toBeInTheDocument());
  });
});

describe("WikiPanel (BR-U3-31)", () => {
  it("lists priors with their references and the unsaved grounds", async () => {
    (api.priorRefs as Mock).mockResolvedValue({
      usages: [{ prior: { id: "p1", world_id: "w", prior_type: "fact", condition: "river",
        effect: "trade", domains: ["geography"], confidence: 0.8 },
        connections: [{ world_id: "w", a_region_id: "r1", b_region_id: "r2", kind: "route" }],
        knowledge: [] }],
      broken: [{ ref_id: "gone", connections: [], knowledge: [{ id: "k1", name: "mill" }] }],
    });
    render(<WikiPanel worldId="w" regions={regions} />);
    await waitFor(() => screen.getByTestId("prior-p1"));
    fireEvent.click(screen.getByTestId("prior-refs-p1"));
    expect(screen.getByTestId("prior-p1")).toHaveTextContent("Riverton–Hollow route");
    expect(screen.getByTestId("wiki-broken")).toHaveTextContent("mill");
  });
});

describe("BuildPanel (BR-U3-35)", () => {
  it("sends the sources, asks before closing sessions, and shows the report", async () => {
    (api.uploadBuild as Mock)
      .mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":{"open_sessions":1}}'))
      .mockResolvedValueOnce({ world_id: "w", regions_created: 3, connections_created: 2,
        entities_created: 1, knowledge_created: 4, corroborations_created: 0, warnings: [],
        unscoped_knowledge_ids: [], llm_calls: 5, embedding_calls: 2, replaced: true,
        closed_session_ids: ["s1"], priors_created: 2, ok: true });
    const onBuilt = vi.fn();
    render(<MemoryRouter><BuildPanel open worldId="w" exists={false} onClose={() => {}} onBuilt={onBuilt} /></MemoryRouter>);
    fireEvent.change(screen.getByTestId("build-memo"), { target: { value: "a river town" } });
    const art = new File(["x"], "art.png", { type: "image/png" });
    fireEvent.change(screen.getByTestId("build-concept_arts"), { target: { files: [art] } });
    fireEvent.click(screen.getByTestId("build-submit"));
    await waitFor(() => expect(screen.getByTestId("build-confirm")).toHaveTextContent("1"));
    const form = (api.uploadBuild as Mock).mock.calls[0][1] as FormData;
    expect(form.getAll("concept_arts")).toHaveLength(1);
    expect(form.get("confirm")).toBe("false");
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() => expect(screen.getByTestId("build-report")).toBeInTheDocument());
    expect(((api.uploadBuild as Mock).mock.calls[1][1] as FormData).get("confirm")).toBe("true");
    expect(onBuilt).toHaveBeenCalledWith("w", expect.objectContaining({ ok: true }));
  });

  it("where the screen cannot tell, a world that exists is replaced only after a yes", async () => {
    // U3 review #6 (BR-U3-35): `/` opens the panel without knowing the typed id
    (api.uploadBuild as Mock)
      .mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":"world already exists: mine"}'))
      .mockResolvedValueOnce({ world_id: "mine", regions_created: 1, connections_created: 0,
        entities_created: 0, knowledge_created: 1, corroborations_created: 0, warnings: [],
        unscoped_knowledge_ids: [], llm_calls: 1, embedding_calls: 0, replaced: true,
        closed_session_ids: [], priors_created: 0, ok: true });
    render(<MemoryRouter><BuildPanel open exists={false} onClose={() => {}} onBuilt={() => {}} /></MemoryRouter>);
    fireEvent.change(screen.getByTestId("build-world-id"), { target: { value: "mine" } });
    fireEvent.change(screen.getByTestId("build-memo"), { target: { value: "a note" } });
    fireEvent.click(screen.getByTestId("build-submit"));
    await waitFor(() => expect(screen.getByTestId("build-confirm")).toBeInTheDocument());
    expect(((api.uploadBuild as Mock).mock.calls[0][1] as FormData).get("replace")).toBe("false");
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() => expect(api.uploadBuild).toHaveBeenCalledTimes(2));
    const second = (api.uploadBuild as Mock).mock.calls[1][1] as FormData;
    expect(second.get("replace")).toBe("true");
    expect(second.get("confirm")).toBe("false");
  });
});


// --------------------------------------------------------------------------- //
// U8: LLM buttons off without a key, the concept-art badge, seeds in the delete plan
// (frontend-components §2.5–2.6, BR-U8-14/25/27, EX-7/8)
// --------------------------------------------------------------------------- //
describe("U8 editor", () => {
  const noLlm = () => (api.capabilities as Mock).mockResolvedValue({ llm: false, vlm: false, embedding: false });
  beforeEach(() => {
    resetCapabilities();
    (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
  });
  afterEach(() => resetCapabilities());
  const build = () =>
    render(<MemoryRouter><BuildPanel open worldId="w" exists={false} onClose={() => {}} onBuilt={() => {}} /></MemoryRouter>);

  it("EX-8: [build] is off and says why when the server has no LLM", async () => {
    noLlm();
    build();
    fireEvent.change(screen.getByTestId("build-memo"), { target: { value: "a river town" } });
    await waitFor(() => expect(screen.getByTestId("build-submit")).toBeDisabled());
    expect(screen.getByTestId("build-submit")).toHaveAttribute("title", t("llm.required"));
    expect(screen.getByTestId("llm-required")).toHaveTextContent(t("llm.required"));
  });

  it("with an LLM [build] is on once there is input", async () => {
    build();
    fireEvent.change(screen.getByTestId("build-memo"), { target: { value: "a river town" } });
    await waitFor(() => expect(api.capabilities).toHaveBeenCalled());
    expect(screen.getByTestId("build-submit")).toBeEnabled();
    expect(screen.queryByTestId("llm-required")).not.toBeInTheDocument();
  });

  it("the concept-art field carries the in-progress badge with its note", () => {
    build();
    const badge = screen.getByTestId("wip-badge");
    expect(badge).toHaveTextContent(t("wip.badge"));
    expect(badge).toHaveAttribute("title", t("build.conceptArtsWip"));
    expect(screen.getAllByTestId("wip-badge")).toHaveLength(1); // only that field
  });

  it("a build 503 for a missing provider reads 'LLM key required'", async () => {
    (api.uploadBuild as Mock).mockRejectedValue(new HttpError(503, "Service Unavailable",
      '{"detail":"world build (LLM provider) unavailable"}'));
    build();
    fireEvent.change(screen.getByTestId("build-memo"), { target: { value: "a river town" } });
    fireEvent.click(screen.getByTestId("build-submit"));
    await waitFor(() => expect(screen.getByTestId("build-error")).toHaveTextContent(t("llm.required")));
  });

  it("EX-8: [draft NPCs] is off without an LLM; a 503 reads 'LLM key required'", async () => {
    noLlm();
    const { unmount } = render(<NpcDraftCards worldId="w" regionId="r1" busy={false} onAccept={async () => true} />);
    await waitFor(() => expect(screen.getByTestId("npc-suggest")).toBeDisabled());
    expect(screen.getByTestId("npc-suggest")).toHaveAttribute("title", t("llm.required"));
    unmount();
    resetCapabilities();
    (api.capabilities as Mock).mockRejectedValue(new Error("down")); // unknown: left on
    (api.draftNpcs as Mock).mockRejectedValue(new HttpError(503, "Service Unavailable",
      '{"detail":"NPC drafts need an LLM provider"}'));
    render(<NpcDraftCards worldId="w" regionId="r1" busy={false} onAccept={async () => true} />);
    await waitFor(() => expect(api.capabilities).toHaveBeenCalled());
    expect(screen.getByTestId("npc-suggest")).toBeEnabled();
    fireEvent.click(screen.getByTestId("npc-suggest"));
    await waitFor(() => expect(screen.getByText(t("llm.required"))).toBeInTheDocument());
  });

  it("EX-7: the delete plan counts the region's event seeds", () => {
    const plan: RegionDeletePlan = { region_id: "r1", region_name: "Ambermeadow", children: [],
      connections: [], npcs: [], knowledge_to_unscope: [], knowledge_scope_removed: [],
      entities_unlocated: [], blocked_by_sessions: [], seed_ids: ["seed-mushroom-blight"] };
    const { unmount } = render(<ConfirmDelete open plan={plan} onConfirm={() => {}} onCancel={() => {}} />);
    expect(screen.getByTestId("delete-plan-seeds")).toHaveTextContent(t("delete.region.seeds", { n: 1 }));
    unmount();
    render(<ConfirmDelete open plan={{ ...plan, seed_ids: [] }} onConfirm={() => {}} onCancel={() => {}} />);
    expect(screen.queryByTestId("delete-plan-seeds")).not.toBeInTheDocument();
  });
});


// --------------------------------------------------------------------------- //
// U3 code-review-01, editor screen (U8 Step 11a): #14 #15 S01 S05 S21 S23 S24 S25 S31,
// C1 C5 C8 C12 C17
// --------------------------------------------------------------------------- //
describe("U3 review carry: the editor screen", () => {
  const ROAD: ConnectionEdge = { world_id: "w", source_region_id: "r1", target_region_id: "r2",
    kind: "route", weight: 0.35, rationale: "old road", wiki_prior_ref: "p1",
    provenance: { source: "inferred", generated_by: "demo-author" } };
  const WORLD: WorldExport = { world_id: "w", regions, connections: [ROAD, { ...ROAD,
    source_region_id: "r2", target_region_id: "r1" }], entities: [], knowledge: [], scopes: [],
    unscoped_knowledge_ids: ["k7", "k8"] };
  function editor() {
    render(
      <MemoryRouter initialEntries={["/editor/w"]}>
        <Routes><Route path="/editor/:worldId" element={<EditorPage />} /></Routes>
      </MemoryRouter>,
    );
  }
  beforeEach(() => {
    resetCapabilities();
    (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
    (api.exportWorld as Mock).mockResolvedValue(WORLD);
    (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "W", region_count: 2, open_sessions: 0 }]);
    (api.listSessions as Mock).mockResolvedValue([]);
  });
  afterEach(() => resetCapabilities());

  it("C1: a drag is one PUT — no world or world-list read after it", async () => {
    (api.updateRegion as Mock).mockResolvedValue({});
    editor();
    await waitFor(() => screen.getByTestId("region-marker-r1"));
    const exports = (api.exportWorld as Mock).mock.calls.length;
    const lists = (api.listWorlds as Mock).mock.calls.length;
    const marker = screen.getByTestId("region-marker-r1");
    const svg = marker.closest("svg") as SVGSVGElement;
    fireEvent.pointerDown(marker, { clientX: 100, clientY: 100 });
    fireEvent.pointerMove(svg, { clientX: 120, clientY: 100 });
    fireEvent.pointerUp(svg, { clientX: 120, clientY: 100 });
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledTimes(1));
    await new Promise((r) => setTimeout(r, 20));
    expect((api.exportWorld as Mock).mock.calls.length).toBe(exports);
    expect((api.listWorlds as Mock).mock.calls.length).toBe(lists);
  });

  it("C1: a failed drag save reads the world again and says why", async () => {
    (api.updateRegion as Mock).mockRejectedValue(new HttpError(500, "Server Error", "graph down"));
    editor();
    await waitFor(() => screen.getByTestId("region-marker-r1"));
    const exports = (api.exportWorld as Mock).mock.calls.length;
    const marker = screen.getByTestId("region-marker-r1");
    const svg = marker.closest("svg") as SVGSVGElement;
    fireEvent.pointerDown(marker, { clientX: 100, clientY: 100 });
    fireEvent.pointerMove(svg, { clientX: 120, clientY: 100 });
    fireEvent.pointerUp(svg, { clientX: 120, clientY: 100 });
    await waitFor(() => expect(screen.getByTestId("editor-error")).toHaveTextContent("graph down"));
    expect((api.exportWorld as Mock).mock.calls.length).toBe(exports + 1);
  });

  it("C5: the unscoped tab counts the server's list", async () => {
    editor();
    await waitFor(() => expect(screen.getByTestId("editor-tab-unscoped")).toHaveTextContent("2"));
  });

  it("#14: a closed build panel keeps no files — reopened, [build] needs new input", async () => {
    editor();
    await waitFor(() => screen.getByTestId("file-build"));
    fireEvent.click(screen.getByTestId("file-build"));
    const art = new File(["x"], "old-map.png", { type: "image/png" });
    fireEvent.change(screen.getByTestId("build-images"), { target: { files: [art] } });
    await waitFor(() => expect(screen.getByTestId("build-submit")).toBeEnabled());
    fireEvent.click(screen.getByText(t("action.close")));
    fireEvent.click(screen.getByTestId("file-build"));
    await waitFor(() => expect(api.capabilities).toHaveBeenCalled());
    expect(screen.getByTestId("build-submit")).toBeDisabled();
  });

  it("#15: the connect tool on a stored pair edits it and keeps its grounds and prior", async () => {
    (api.saveConnection as Mock).mockResolvedValue([]);
    editor();
    await waitFor(() => screen.getByTestId("region-marker-r1"));
    fireEvent.click(screen.getByTestId("map-tool-connect"));
    fireEvent.click(screen.getByTestId("region-marker-r2"));
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    expect(screen.getByTestId("connection-form")).toHaveTextContent(t("editor.connection.edit"));
    expect(screen.getByTestId("connection-exists")).toHaveTextContent("0.35");
    expect(screen.getByTestId("connection-weight")).toHaveValue("0.35");
    fireEvent.change(screen.getByTestId("connection-weight"), { target: { value: "0.5" } });
    fireEvent.click(screen.getByTestId("connection-save"));
    await waitFor(() => expect(api.saveConnection).toHaveBeenCalledTimes(1));
    expect((api.saveConnection as Mock).mock.calls[0][1]).toMatchObject({
      source_region_id: "r2", target_region_id: "r1", kind: "route", weight: 0.5,
      rationale: "old road", wiki_prior_ref: "p1",
      provenance: { source: "inferred", generated_by: "demo-author" },
    });
  });

  it("#15: another kind on that pair is a new connection", async () => {
    (api.saveConnection as Mock).mockResolvedValue([]);
    editor();
    await waitFor(() => screen.getByTestId("region-marker-r1"));
    fireEvent.click(screen.getByTestId("map-tool-connect"));
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    fireEvent.click(screen.getByTestId("region-marker-r2"));
    fireEvent.change(screen.getByTestId("connection-kind"), { target: { value: "river" } });
    expect(screen.queryByTestId("connection-exists")).not.toBeInTheDocument();
    expect(screen.getByTestId("connection-form")).toHaveTextContent(t("editor.connection.add"));
    fireEvent.click(screen.getByTestId("connection-save"));
    await waitFor(() => expect(api.saveConnection).toHaveBeenCalledTimes(1));
    const body = (api.saveConnection as Mock).mock.calls[0][1];
    expect(body).toMatchObject({ kind: "river", provenance: { source: "input", generated_by: "designer" } });
    expect(body.wiki_prior_ref).toBeUndefined();
  });

  it("S21: with no world to edit the map tools are off", async () => {
    (api.exportWorld as Mock).mockRejectedValue(new HttpError(404, "Not Found", "world not found"));
    editor();
    await waitFor(() => screen.getByTestId("empty-hint"));
    expect(screen.getByTestId("map-tool-add-region")).toBeDisabled();
    expect(screen.getByTestId("map-tool-connect")).toBeDisabled();
  });

  it("S01: with no open session the bar offers a session start", async () => {
    editor();
    fireEvent.click(await screen.findByTestId("start-session-band"));
    expect(await screen.findByTestId("session-new-btn")).toBeInTheDocument();
    expect(screen.queryByTestId("open-sessions-band")).not.toBeInTheDocument();
  });

  it("S05: a delete refused because a player walked in shows who, and stays off", async () => {
    const plan: RegionDeletePlan = { region_id: "r1", region_name: "Riverton", children: [],
      connections: [], npcs: [], knowledge_to_unscope: [], knowledge_scope_removed: [],
      entities_unlocated: [], blocked_by_sessions: [] };
    (api.getEditorRegion as Mock).mockResolvedValue(VIEW);
    (api.getDeletePlan as Mock).mockResolvedValue(plan);
    (api.deleteRegion as Mock).mockRejectedValue(new HttpError(409, "Conflict", JSON.stringify(
      { detail: { message: "a player of an open session stands in this region", session_ids: ["s7"] } })));
    render(<RegionInspector worldId="w" regionId="r1" regions={regions} onChanged={() => {}} onDeleted={() => {}} />);
    fireEvent.click(await screen.findByTestId("region-delete"));
    fireEvent.click(await screen.findByText(t("delete.confirm")));
    await waitFor(() => expect(screen.getByTestId("delete-blocked")).toHaveTextContent("s7"));
    expect(screen.getByText(t("delete.confirm"))).toBeDisabled();
    expect(screen.getByTestId("confirm-delete")).not.toHaveTextContent("409");
  });

  it("S25: the delete plan names what goes, by the region at the far end for connections", () => {
    const plan: RegionDeletePlan = { region_id: "r1", region_name: "Riverton", children: [],
      connections: [{ world_id: "w", a_region_id: "r1", b_region_id: "r2", kind: "route" }],
      npcs: [], knowledge_to_unscope: [], knowledge_scope_removed: [{ id: "k1", name: "mill" }],
      entities_unlocated: [{ id: "e1", name: "Old Bell" }], blocked_by_sessions: [] };
    render(<ConfirmDelete open plan={plan} regions={regions} onConfirm={() => {}} onCancel={() => {}} />);
    const list = screen.getByTestId("delete-plan");
    expect(list).toHaveTextContent("Hollow (route)");
    expect(list).toHaveTextContent("mill");
    expect(list).toHaveTextContent("Old Bell");
  });

  it("S31: a slow read in the language just left does not paint over the newer one", async () => {
    let first: (v: EditorRegionView) => void = () => {};
    (api.getEditorRegion as Mock)
      .mockImplementationOnce(() => new Promise((r) => (first = r)))
      .mockResolvedValueOnce({ ...VIEW, region: { ...VIEW.region, name: "Riverton (new)" } });
    const props = { worldId: "w", regionId: "r1", regions, onChanged: () => {}, onDeleted: () => {} };
    const { rerender } = render(<RegionInspector {...props} reloadKey={0} />);
    rerender(<RegionInspector {...props} reloadKey={1} />);
    await waitFor(() => expect(screen.getByTestId("region-inspector")).toHaveTextContent("Riverton (new)"));
    await act(async () => first({ ...VIEW, region: { ...VIEW.region, name: "Riverton (old)" } }));
    expect(screen.getByTestId("region-inspector")).not.toHaveTextContent("Riverton (old)");
  });

  it("S31: the unscoped list draws only its newest read", async () => {
    let first: (v: unknown[]) => void = () => {};
    (api.listUnscoped as Mock)
      .mockImplementationOnce(() => new Promise((r) => (first = r)))
      .mockResolvedValueOnce([]);
    const { rerender } = render(<UnscopedPanel worldId="w" regions={regions} reloadKey={0} onChanged={() => {}} />);
    rerender(<UnscopedPanel worldId="w" regions={regions} reloadKey={1} onChanged={() => {}} />);
    await waitFor(() => screen.getByText(t("editor.unscoped.none")));
    await act(async () => first([{ id: "k9", world_id: "w", statement: "lost", title: "lost", confidence: 1, provenance: { source: "input" } }]));
    expect(screen.queryByTestId("unscoped-k9")).not.toBeInTheDocument();
  });

  it("C17: a fact added without a title sends no title of the client's making", () => {
    const onSubmit = vi.fn();
    render(<KnowledgeList items={[]} regions={regions} busy={false} onCreate={onSubmit}
      onUpdate={() => {}} onSetScopes={() => {}} onDelete={() => {}} />);
    fireEvent.click(screen.getByTestId("knowledge-add"));
    fireEvent.change(screen.getByTestId("knowledge-statement"), { target: { value: "  The mill wheel turns at dawn and dusk  " } });
    fireEvent.click(screen.getByTestId("knowledge-save"));
    expect(onSubmit).toHaveBeenCalledWith("", "The mill wheel turns at dawn and dusk");
  });

  it("S23: a drag the browser cancels or takes away ends without a save", () => {
    const onMove = vi.fn();
    const captured: number[] = [];
    const proto = Element.prototype as unknown as { setPointerCapture?: (id: number) => void };
    const had = proto.setPointerCapture;
    proto.setPointerCapture = (id: number) => void captured.push(id);
    try {
      render(<MapOverlay regions={regions} connections={[]} selectedId={null} draggable onSelect={() => {}} onMove={onMove} />);
      const marker = screen.getByTestId("region-marker-r1");
      const svg = marker.closest("svg") as SVGSVGElement;
      for (const end of ["pointerCancel", "lostPointerCapture"] as const) {
        fireEvent.pointerDown(marker, { clientX: 100, clientY: 100, pointerId: 7 });
        fireEvent.pointerMove(svg, { clientX: 130, clientY: 100 });
        fireEvent[end](svg);
        fireEvent.pointerUp(svg, { clientX: 130, clientY: 100 });
      }
      expect(onMove).not.toHaveBeenCalled();
      expect(captured.length).toBe(2); // the marker took the pointer each time
    } finally {
      proto.setPointerCapture = had;
    }
  });

  it("S24: the file box is emptied after a pick, so the same file can be picked again", async () => {
    render(<MemoryRouter><WorldFileBar worldId="w" name="W" openSessions={0} regions={regions}
      onLoaded={() => {}} onBuild={() => {}} /></MemoryRouter>);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const set = vi.fn();
    Object.defineProperty(input, "value", { configurable: true, get: () => "", set });
    const file = new File(['{"format_version": 1}'], "w.world.json", { type: "application/json" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(set).toHaveBeenCalledWith("");
    await waitFor(() => expect(screen.getByTestId("file-confirm")).toHaveTextContent(t("file.replaceConfirm")));
  });

  it("C8: the World File bar asks replace, then the session question, then loads with confirm", async () => {
    (api.importWorldFile as Mock)
      .mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":{"open_sessions":3,"session_ids":["a","b","c"]}}'))
      .mockResolvedValueOnce({ ok: true });
    const onLoaded = vi.fn();
    render(<MemoryRouter><WorldFileBar worldId="w" name="W" openSessions={3} regions={regions}
      onLoaded={onLoaded} onBuild={() => {}} /></MemoryRouter>);
    const file = new File(['{"format_version": 1}'], "w.world.json", { type: "application/json" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [file] } });
    await waitFor(() => screen.getByTestId("file-confirm"));
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() => expect(screen.getByTestId("file-confirm")).toHaveTextContent(t("file.closeSessionsConfirm", { n: 3 })));
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() => expect(onLoaded).toHaveBeenCalled());
    expect((api.importWorldFile as Mock).mock.calls.map((c) => c[2])).toEqual([
      { replace: true, confirm: false }, { replace: true, confirm: true }]);
  });
});


// --------------------------------------------------------------------------- //
// U3 code-review-01, augmentation screen (U8 Step 11b): #12 S06 S28 C2
// --------------------------------------------------------------------------- //
describe("U3 review carry: the augmentation screen", () => {
  const low = (over: Partial<AugQuestion> = {}): AugQuestion => ({
    id: "q1", issue_id: "i1", issue_key: "low_confidence:knowledge:k1::", type: "low_confidence",
    text: "Is this right?", actions: ["confirm", "edit", "remove", "ignore"],
    needs: { edit: ["statement", "title", "confidence"] },
    target: { kind: "knowledge", id: "k1", name: "mill" }, ...over,
  });
  const gap = (id: string): AugQuestion => ({
    id, issue_id: "i2", issue_key: "gap:region:r2::", type: "gap", text: "What is known in Hollow?",
    actions: ["add", "ignore"], needs: { add: ["statement", "title"] },
    target: { kind: "region", id: "r2", name: "Hollow" },
  });
  const answered = (run: AugRun) => ({ change: null, changed: [], run });
  async function open(run: AugRun) {
    (api.startRun as Mock).mockResolvedValue(run);
    render(<AugmentPanel worldId="w" regions={regions} entities={[{ id: "e1", name: "Old Bell" }]} onChanged={() => {}} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    await waitFor(() => screen.getAllByTestId("augment-question"));
  }

  it("#12: a 404 for a target gone meanwhile keeps the run and shows the server's reason", async () => {
    (api.answer as Mock).mockRejectedValue(new HttpError(404, "Not Found", '{"detail":"region not found: gone"}'));
    (api.getRun as Mock).mockResolvedValue(runOf({ open_questions: [low()] }));
    await open(runOf({ open_questions: [low()] }));
    await act(async () => fireEvent.click(screen.getByTestId("augment-action-confirm")));
    await waitFor(() => expect(screen.getByTestId("augment-error").textContent).toBe("region not found: gone"));
    expect(api.getRun).toHaveBeenCalledWith("run1");
    expect(screen.queryByTestId("augment-lost")).not.toBeInTheDocument();
    expect(screen.getAllByTestId("augment-question")).toHaveLength(1);
  });

  it("C2/S06: the inputs are the server's — statement, title and confidence go with edit only", async () => {
    (api.answer as Mock).mockResolvedValue(answered(runOf({ open_questions: [] })));
    await open(runOf({ open_questions: [low()] }));
    expect(screen.queryByTestId("augment-region")).not.toBeInTheDocument();
    fireEvent.change(screen.getByTestId("augment-statement"), { target: { value: "The mill burned" } });
    fireEvent.change(screen.getByTestId("augment-title"), { target: { value: "Burned mill" } });
    fireEvent.change(screen.getByTestId("augment-confidence"), { target: { value: "0.9" } });
    await act(async () => fireEvent.click(screen.getByTestId("augment-action-edit")));
    expect((api.answer as Mock).mock.calls[0][1]).toEqual({ question_id: "q1", action: "edit",
      statement: "The mill burned", title: "Burned mill", confidence: 0.9,
      region_id: undefined, ref_id: undefined });
  });

  it("S06: a confirm carries none of the typed inputs; a confidence out of range is not sent", async () => {
    (api.answer as Mock).mockResolvedValue(answered(runOf({ open_questions: [low()] })));
    await open(runOf({ open_questions: [low()] }));
    fireEvent.change(screen.getByTestId("augment-statement"), { target: { value: "typed" } });
    fireEvent.change(screen.getByTestId("augment-confidence"), { target: { value: "1.5" } });
    await act(async () => fireEvent.click(screen.getByTestId("augment-action-confirm")));
    expect((api.answer as Mock).mock.calls[0][1]).toMatchObject({ action: "confirm", statement: undefined, confidence: undefined });
    await act(async () => fireEvent.click(screen.getByTestId("augment-action-edit")));
    expect((api.answer as Mock).mock.calls[1][1]).toMatchObject({ action: "edit", statement: "typed", confidence: undefined });
  });

  it("C2: a dangling reference lists the kind the server names", async () => {
    const dangling = low({ id: "q3", issue_key: "dangling:knowledge:k1:about_entity_ids:gone", type: "dangling",
      actions: ["edit", "remove", "ignore"], needs: { edit: ["ref"] }, ref_kind: "entity",
      target: { kind: "knowledge", id: "k1", name: "mill", field: "about_entity_ids" } });
    await open(runOf({ open_questions: [dangling] }));
    expect(screen.getByTestId("augment-ref")).toHaveTextContent("Old Bell");
    expect(screen.queryByTestId("augment-statement")).not.toBeInTheDocument();
    expect(api.listPriors).not.toHaveBeenCalled();
  });

  it("S28: what is typed on one card survives an answer on another (new question ids)", async () => {
    (api.answer as Mock).mockResolvedValue(answered(runOf({ open_questions: [low({ id: "q9" }), gap("q8")] })));
    await open(runOf({ open_questions: [low(), gap("q2")] }));
    const statements = screen.getAllByTestId("augment-statement");
    fireEvent.change(statements[1], { target: { value: "Wells run dry" } });
    await act(async () => fireEvent.click(screen.getAllByTestId("augment-action-confirm")[0]));
    await waitFor(() => expect(api.answer).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getAllByTestId("augment-statement")[1]).toHaveValue("Wells run dry"));
  });
});
