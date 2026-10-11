import { renderWithShell } from "../test/render";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import { WorldMap } from "../map";
// U3 intended change (C-8): the GM's read-only knowledge panel (was RegionPanel);
// the augmentation panel moved to features/editor with the kept-run API (C-3)
import { RegionKnowledgePanel } from "../features/gm/RegionKnowledgePanel";
import { AugHost } from "../test/editor";
import { App } from "../App";
import { resetCapabilities } from "../capabilities";
import { t } from "../i18n";
import type { ConnectionEdge, GameSession, Region } from "../types";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn().mockResolvedValue({ llm: true, vlm: true, embedding: true }),
    worldNames: vi.fn().mockRejectedValue(new Error("no names in this test")),
    listSeeds: vi.fn().mockResolvedValue([]),
    startSeed: vi.fn(),
    listDemos: vi.fn().mockResolvedValue([]),
    regionKnowledge: vi.fn(),
    sessionKnowledge: vi.fn(),
    exportWorld: vi.fn(),
    loadDemo: vi.fn(),
    updateRegion: vi.fn(),
    getSession: vi.fn(),
    startRun: vi.fn(),
    answer: vi.fn(),
    revert: vi.fn(),
    unignore: vi.fn(),
    listPriors: vi.fn(),
    listWorlds: vi.fn(),
    importWorldFile: vi.fn(),
    getWorldFile: vi.fn(),
    listSessions: vi.fn(),
    startSession: vi.fn(),
    closeSession: vi.fn(),
    getPlayer: vi.fn(),
    getRegion: vi.fn(),
    act: vi.fn(),
    getTurnRun: vi.fn(),
    listTurnRuns: vi.fn(),
    getLog: vi.fn(),
    getTimeline: vi.fn(),
    listRumors: vi.fn(),
    generateRumors: vi.fn(),
    regenRumors: vi.fn(),
    setSupport: vi.fn(),
    setDistortion: vi.fn(),
    advanceTurn: vi.fn(),
    listEvents: vi.fn(),
    createEvent: vi.fn(),
    suggestEvents: vi.fn(),
    approveEvent: vi.fn(),
    resolveEvent: vi.fn(),
    discardEvent: vi.fn(),
    listDistortions: vi.fn(),
    getWorldState: vi.fn(),
    listDeeds: vi.fn(),
    voidDeed: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;

const regions: Region[] = [
  { id: "r1", name: "Riverton", level: "town", position: { x: 0.2, y: 0.3 } },
  { id: "r2", name: "Highcrag", level: "town", position: { x: 0.8, y: 0.7 } },
];
const connections: ConnectionEdge[] = [
  { source_region_id: "r1", target_region_id: "r2", kind: "blocked", weight: 0.2 },
];

// V8 intended change (§ 7.1): the editor draws `WorldMap` in edit mode directly
describe("WorldMap in edit mode", () => {
  it("renders a marker per region and a line per connection", () => {
    render(
      <WorldMap mode="edit" label="map" regions={regions} connections={connections} onSelect={() => {}} onMove={() => {}} />,
    );
    expect(screen.getByTestId("region-marker-r1")).toBeInTheDocument();
    expect(screen.getByTestId("region-marker-r2")).toBeInTheDocument();
    expect(screen.getAllByTestId("connection-line")).toHaveLength(1);
  });

  it("calls onSelect when a marker is clicked", () => {
    const onSelect = vi.fn();
    render(
      <WorldMap mode="edit" label="map" regions={regions} connections={[]} onSelect={onSelect} onMove={() => {}} />,
    );
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    expect(onSelect).toHaveBeenCalledWith("r1");
  });
});

describe("RegionPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows region knowledge from the API", async () => {
    (api.regionKnowledge as ReturnType<typeof vi.fn>).mockResolvedValue({
      world_id: "w",
      region_id: "r1",
      items: [
        { knowledge_id: "k1", statement: "Sunday market", scope_type: "direct", is_hearsay: false, confidence: 0.9 },
      ],
      shared_ids: [],
      unique_ids: ["k1"],
    });
    render(<RegionKnowledgePanel worldId="w" regionId="r1" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-item-k1")).toBeInTheDocument());
    expect(screen.getByText(/Sunday market/)).toBeInTheDocument();
    expect(screen.queryByTestId("delete-k1")).not.toBeInTheDocument(); // BR-U3-33: no ✕
  });
});

describe("RegionPanel badges (U1 §11.4)", () => {
  beforeEach(() => vi.clearAllMocks());

  it("labels canonical hearsay, session rumors and scope distinctly", async () => {
    (api.regionKnowledge as Mock).mockResolvedValue({
      world_id: "w",
      region_id: "r1",
      items: [
        { knowledge_id: "h1", statement: "far tale", scope_type: "hearsay", is_hearsay: true, confidence: 0.4, path_decay: 0.5 },
        { knowledge_id: "s1", statement: "session tale", scope_type: "direct", is_hearsay: false, confidence: 0.5, source: "rumor:promoted", distortion: 0.3 },
        { knowledge_id: "d1", statement: "local fact", scope_type: "direct", is_hearsay: false, confidence: 0.9 },
      ],
      shared_ids: [],
      unique_ids: [],
    });
    render(<RegionKnowledgePanel worldId="w" regionId="r1" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-item-h1")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-item-h1")).toHaveTextContent(t("badge.hearsay"));
    expect(screen.getByTestId("knowledge-item-s1")).toHaveTextContent(t("badge.rumor"));
    // V6 (FR-D8): the scope reads in words, never the raw value
    expect(screen.getByTestId("knowledge-item-d1")).toHaveTextContent(t("enum.scopeType.direct"));
    expect(screen.getByTestId("knowledge-item-d1").textContent).not.toMatch(/\bdirect\b/);
  });
});

describe("AugmentPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("starts a session and shows questions", async () => {
    // U3 intended change (C-3): a run with targets and fixed actions
    (api.startRun as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "s1", world_id: "w", answers: 0, status: "open", ignored_keys: [], history: [],
      llm_calls: 0, llm_budget_exhausted: false,
      open_questions: [{ id: "q1", issue_id: "i1", issue_key: "gap:region:r1::",
        text: "What is known here?", actions: ["add", "ignore"],
        target: { kind: "region", id: "r1", name: "Riverton" } }],
    });
    render(<AugHost regions={regions} />); // V8: the page's hook around the panel
    fireEvent.click(screen.getByTestId("augment-find"));
    await waitFor(() => expect(screen.getByText(/What is known here/)).toBeInTheDocument());
    expect(screen.getByTestId("augment-action-add")).toBeInTheDocument();
    expect(screen.getByTestId("augment-action-ignore")).toBeInTheDocument();
  });
});

// V8 intended change (Q2 = A): the session bar and its [new session] are gone
const OPEN_SESSION: GameSession = { id: "s1", world_id: "w", status: "open", turn: 2 };

// V6: the GmHub tests moved to gm.layout.test.tsx (the screen) and gm.parts.test.tsx (the
// parts) — frontend-components § 7.1, TP-V6-17; each behaviour they asserted is kept there.

describe("RegionPanel session view", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses sessionKnowledge when a session is active", async () => {
    (api.sessionKnowledge as Mock).mockResolvedValue({
      world_id: "w", region_id: "r1", items: [], shared_ids: [], unique_ids: [],
    });
    render(<RegionKnowledgePanel worldId="w" regionId="r1" sessionId="s1" />);
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalledWith("s1", "r1"));
    expect(api.regionKnowledge).not.toHaveBeenCalled();
  });
});

describe("App routing (F1 / AD-R8)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // no test inherits another's "LLM off" answer (code review 01 #50)
    resetCapabilities();
    (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
    (api.listSessions as Mock).mockResolvedValue([]);
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listEvents as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([]);
    // V6: the GM screen reads its session's state, rumors, seeds, deeds and player itself
    (api.getWorldState as Mock).mockResolvedValue({ session_id: "s1", turn: 0, player_region_id: null, regions: [] });
    (api.listSeeds as Mock).mockResolvedValue([]);
    (api.listDeeds as Mock).mockResolvedValue([]);
    (api.getPlayer as Mock).mockRejectedValue(new HttpError(404, "Not Found", "no player"));
    (api.listTurnRuns as Mock).mockResolvedValue([]);
  });

  it("redirects / to the default world editor and loads that world", async () => {
    // U3 intended change (C-7, BR-U3-34): `/` is the world list; the editor loads
    // the world its URL names
    (api.listWorlds as Mock).mockResolvedValue([
      { id: "aldermoor", name: "Aldermoor", region_count: 1, open_sessions: 0 },
    ]);
    (api.exportWorld as Mock).mockResolvedValue({
      world_id: "aldermoor", regions: [{ id: "r1", name: "Riverton", level: "town" }],
      connections: [], entities: [], knowledge: [], scopes: [],
    });
    const { unmount } = render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("world-row-aldermoor")).toBeInTheDocument());
    unmount();
    render(
      <MemoryRouter initialEntries={["/editor/aldermoor"]}>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => expect(api.exportWorld).toHaveBeenCalledWith("aldermoor"));
    await waitFor(() => expect(screen.getByTestId("graph-status")).toBeInTheDocument());
    // V8 (Q2 = A): the editor's one session action is the player start
    expect(screen.getByTestId("play-this-world")).toBeInTheDocument();
    expect(screen.queryByTestId("session-close-btn")).not.toBeInTheDocument();
  });

  it("refuses to load an empty world id instead of navigating to /editor/", async () => {
    // U3 intended change (C-7): the id is asked where a world is made — building from
    // sources needs one before it can be sent
    (api.listWorlds as Mock).mockResolvedValue([]);
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("home-empty")).toBeInTheDocument());
    fireEvent.click(screen.getAllByTestId("home-build")[0]);
    fireEvent.change(screen.getByTestId("build-memo"), { target: { value: "a note" } });
    expect(screen.getByTestId("build-submit")).toBeDisabled();
    fireEvent.change(screen.getByTestId("build-world-id"), { target: { value: "mine" } });
    expect(screen.getByTestId("build-submit")).not.toBeDisabled();
  });

  it("renders the GameMaster screen for /gm/:sessionId", async () => {
    (api.getSession as Mock).mockResolvedValue(OPEN_SESSION);
    (api.exportWorld as Mock).mockResolvedValue({
      world_id: "w", regions: [], connections: [], entities: [], knowledge: [], scopes: [],
    });
    render(
      <MemoryRouter initialEntries={["/gm/s1"]}>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("turn-tools")).toBeInTheDocument()); // V6: was the hub panel
    expect(screen.getByTestId("gm-tabs")).toBeInTheDocument();
    expect(api.getSession).toHaveBeenCalledWith("s1");
    expect(api.exportWorld).toHaveBeenCalledWith("w");
    expect(screen.getByTestId("nav-gm")).toHaveAttribute("href", "/gm/s1");
  });

  it("keeps the GM screen recoverable when the session cannot be loaded", async () => {
    (api.getSession as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", "no session"));
    (api.getSession as Mock).mockResolvedValueOnce(OPEN_SESSION);
    (api.exportWorld as Mock).mockResolvedValue({
      world_id: "w", regions: [], connections: [], entities: [], knowledge: [], scopes: [],
    });
    render(
      <MemoryRouter initialEntries={["/gm/s1"]}>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("gm-error")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("gm-retry-btn"));
    await waitFor(() => expect(screen.getByTestId("turn-tools")).toBeInTheDocument()); // V6: was the hub panel
    expect(screen.queryByText(t("session.none"))).not.toBeInTheDocument(); // no dead entry on GM
  });

  it("shows the player screen hint for /play without a session (U4)", () => {
    render(
      <MemoryRouter initialEntries={["/play"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("play-empty")).toBeInTheDocument();
  });
});

describe("EditorPage demo load (BR-U2-25)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.listSessions as Mock).mockResolvedValue([]);
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.exportWorld as Mock).mockResolvedValue({
      world_id: "aldermoor", regions: [], connections: [], entities: [], knowledge: [], scopes: [],
    });
  });

  it("asks before closing open sessions and retries with confirm", async () => {
    // U3 intended change (BR-U3-36): replacing a world is the World File bar's load —
    // a yes to replace, then a yes to close the open sessions
    (api.importWorldFile as Mock)
      .mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":{"open_sessions":2}}'))
      .mockResolvedValueOnce({ ok: true, closed_session_ids: ["s1", "s2"] });
    render(
      <MemoryRouter initialEntries={["/editor/aldermoor"]}>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => expect(api.exportWorld).toHaveBeenCalled());
    const file = new File(['{"format_version": 1}'], "w.world.json", { type: "application/json" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [file] } });
    await waitFor(() => expect(screen.getByTestId("file-confirm")).toHaveTextContent(t("file.replaceConfirm")));
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() =>
      expect(api.importWorldFile).toHaveBeenCalledWith("aldermoor", { format_version: 1 }, { replace: true, confirm: false }),
    );
    await waitFor(() => expect(screen.getByTestId("file-confirm")).toHaveTextContent("2"));
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() =>
      expect(api.importWorldFile).toHaveBeenLastCalledWith("aldermoor", { format_version: 1 }, { replace: true, confirm: true }),
    );
  });

  it("lays a background map picked in this browser under the editor's map", async () => {
    // U3 Step 11: the picker the old Toolbar had, kept when the Toolbar went (Step 9.8)
    const made = vi.fn(() => "blob:map");
    Object.assign(URL, { createObjectURL: made });
    (api.exportWorld as Mock).mockResolvedValue({
      world_id: "aldermoor", regions: [{ id: "r1", name: "Riverton", level: "town" }],
      connections: [], entities: [], knowledge: [], scopes: [],
    });
    render(
      <MemoryRouter initialEntries={["/editor/aldermoor"]}>
        <App />
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId("map-file-input"));
    const image = new File(["png"], "map.png", { type: "image/png" });
    expect(screen.getByText(t("empty.noFile"))).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("map-file-input"), { target: { files: [image] } });
    expect(made).toHaveBeenCalledWith(image);
    // V6 (code review 01 43(e)): the backdrop is decorative — the map beside it has the name
    expect(screen.getByTestId("map-overlay").querySelector("img")).toHaveAttribute("src", "blob:map");
    expect(screen.getByText("map.png")).toBeInTheDocument(); // the picker says what it holds (V2 review #7)
  });
});


// --------------------------------------------------------------------------- //
// U8: the nav with no world named, and the editor's LLM-off notice
// --------------------------------------------------------------------------- //
describe("EditorPage after U8", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetCapabilities();
    (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
    (api.listSessions as Mock).mockResolvedValue([]);
    (api.listWorlds as Mock).mockResolvedValue([]);
  });
  afterEach(() => resetCapabilities());

  // V2: the menu rules moved to layout.test.tsx with AppShell (AppNav is gone)
  it("the editor shows the LLM-off notice and keeps the World File bar", async () => {
    (api.capabilities as Mock).mockResolvedValue({ llm: false, vlm: false, embedding: false });
    (api.exportWorld as Mock).mockResolvedValue({
      world_id: "emberleaf", regions: [{ id: "r1", name: "Saltwake", level: "town" }],
      connections: [], entities: [], knowledge: [], scopes: [],
    });
    render(
      <MemoryRouter initialEntries={["/editor/emberleaf"]}>
        <App />
      </MemoryRouter>,
    );
    // V2 intended change: the one band of the AppShell, one sentence for every screen (BR-V2-20)
    expect(await screen.findByTestId("llm-notice")).toHaveTextContent(t("notice.llmOff"));
    expect(screen.getByTestId("file-input")).toBeEnabled();
  });
});
