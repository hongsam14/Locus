// U3 world editor (frontend-components §6, EX-11, BR-U3-24..32).
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import { AugmentPanel } from "../features/editor/AugmentPanel";
import { BuildPanel } from "../features/editor/BuildPanel";
import { ConfirmDelete } from "../features/editor/ConfirmDelete";
import { isDrag } from "../features/editor/drag";
import { MapCanvas } from "../features/editor/MapCanvas";
import { RegionInspector } from "../features/editor/RegionInspector";
import { UnscopedPanel } from "../features/editor/UnscopedPanel";
import { WikiPanel } from "../features/editor/WikiPanel";
import { t } from "../i18n";
import type { AugRun, EditorRegionView, Region, RegionDeletePlan } from "../types";

vi.mock("../api", () => ({
  api: {
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
    render(<UnscopedPanel worldId="w" regions={regions} onChanged={() => {}} />);
    await waitFor(() => screen.getByTestId("unscoped-k9"));
    fireEvent.change(screen.getByTestId("unscoped-region-k9"), { target: { value: "r2" } });
    fireEvent.click(screen.getByTestId("unscoped-assign-k9"));
    await waitFor(() => expect(api.setScopes).toHaveBeenCalledWith("w", "k9", ["r2"]));
    await waitFor(() => expect(screen.queryByTestId("unscoped-k9")).not.toBeInTheDocument());
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
