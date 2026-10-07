import { renderWithShell } from "../test/render";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import { MapOverlay } from "../MapOverlay";
// U3 intended change (C-8): the GM's read-only knowledge panel (was RegionPanel);
// the augmentation panel moved to features/editor with the kept-run API (C-3)
import { RegionKnowledgePanel } from "../features/gm/RegionKnowledgePanel";
import { AugmentPanel } from "../features/editor/AugmentPanel";
import { SessionBar } from "../SessionBar";
import { GmHub } from "../features/gm/GmHub";
import { App } from "../App";
import { resetCapabilities } from "../capabilities";
import { t } from "../i18n";
import type { ConnectionEdge, GameSession, Region } from "../types";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn().mockResolvedValue({ llm: true, vlm: true, embedding: true }),
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

describe("MapOverlay", () => {
  it("renders a marker per region and a line per connection", () => {
    render(
      <MapOverlay regions={regions} connections={connections} onSelect={() => {}} onMove={() => {}} />,
    );
    expect(screen.getByTestId("region-marker-r1")).toBeInTheDocument();
    expect(screen.getByTestId("region-marker-r2")).toBeInTheDocument();
    expect(screen.getAllByTestId("connection-line")).toHaveLength(1);
  });

  it("calls onSelect when a marker is clicked", () => {
    const onSelect = vi.fn();
    render(
      <MapOverlay regions={regions} connections={[]} onSelect={onSelect} onMove={() => {}} />,
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
    expect(screen.getByTestId("knowledge-item-d1")).toHaveTextContent("direct");
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
    render(<AugmentPanel worldId="w" regions={regions} entities={[]} onChanged={() => {}} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    await waitFor(() => expect(screen.getByText(/What is known here/)).toBeInTheDocument());
    expect(screen.getByTestId("augment-action-add")).toBeInTheDocument();
    expect(screen.getByTestId("augment-action-ignore")).toBeInTheDocument();
  });
});

const OPEN_SESSION: GameSession = { id: "s1", world_id: "w", status: "open", turn: 2 };

describe("SessionBar", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists sessions and starts a new one", async () => {
    (api.listSessions as Mock).mockResolvedValue([]);
    (api.startSession as Mock).mockResolvedValue(OPEN_SESSION);
    const onSelect = vi.fn();
    render(<SessionBar worldId="w" sessionId={null} onSelect={onSelect} />);
    await waitFor(() => expect(api.listSessions).toHaveBeenCalledWith("w"));
    fireEvent.click(screen.getByTestId("session-new-btn"));
    await waitFor(() => expect(api.startSession).toHaveBeenCalledWith("w"));
    await waitFor(() =>
      expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "s1" })),
    );
  });
});

describe("GmHub (GameMaster hub, was SessionPanel)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // safe defaults for the Phase 2 reads SessionPanel issues on refresh
    (api.listEvents as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([]);
  });

  it("renders rumors with promoted badge and generates", async () => {
    (api.getTimeline as Mock).mockResolvedValue([
      { id: "t1", session_id: "s1", turn: 0, kind: "generate", summary: "made rumors", payload: {} },
    ]);
    (api.listRumors as Mock).mockResolvedValue([
      {
        id: "ru1", session_id: "s1", region_id: "r1", distorted_from_id: "k",
        distorted_from_kind: "knowledge", statement: "twisted tale", distortion_degree: 0.3,
        support: 0.7, confidence: 0.5, promoted: true,
      },
    ]);
    (api.generateRumors as Mock).mockResolvedValue([]);
    render(<GmHub session={OPEN_SESSION} regionId="r1" />);
    await waitFor(() => expect(screen.getByTestId("rumor-ru1")).toBeInTheDocument());
    expect(screen.getByTestId("promoted-ru1")).toBeInTheDocument();
    expect(screen.getByText(/twisted tale/)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("generate-btn"));
    await waitFor(() => expect(api.generateRumors).toHaveBeenCalledWith("s1", "r1"));
  });

  it("advances the turn", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.advanceTurn as Mock).mockResolvedValue({
      session_id: "s1", turn: 3, promoted_ids: [], demoted_ids: [],
    });
    render(<GmHub session={OPEN_SESSION} regionId={null} />);
    expect(screen.getByTestId("gm-no-region")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("advance-turn-btn"));
    await waitFor(() => expect(api.advanceTurn).toHaveBeenCalledWith("s1"));
  });

  it("refresh loads independent reads in parallel (FR-H6)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    render(<GmHub session={OPEN_SESSION} regionId="r1" />);
    // all three region-independent reads + the region rumor read are issued
    await waitFor(() => expect(api.getTimeline).toHaveBeenCalledWith("s1"));
    expect(api.listEvents).toHaveBeenCalledWith("s1");
    expect(api.listDistortions).toHaveBeenCalledWith("s1");
    expect(api.listRumors).toHaveBeenCalledWith("s1", "r1");
  });

  it("refresh skips the rumor read when no region is selected (FR-H6)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    render(<GmHub session={OPEN_SESSION} regionId={null} />);
    await waitFor(() => expect(api.getTimeline).toHaveBeenCalledWith("s1"));
    expect(api.listRumors).not.toHaveBeenCalled();
  });

  it("disables write controls on a closed session", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    render(
      <GmHub session={{ ...OPEN_SESSION, status: "closed" }} regionId="r1" />,
    );
    await waitFor(() => expect(screen.getByTestId("generate-btn")).toBeDisabled());
    expect(screen.getByTestId("advance-turn-btn")).toBeDisabled();
    expect(screen.getByTestId("event-create-btn")).toBeDisabled();
    expect(screen.getByTestId("suggest-events-btn")).toBeDisabled();
  });

  it("creates an event for the selected region", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.createEvent as Mock).mockResolvedValue({});
    render(<GmHub session={OPEN_SESSION} regionId="r1" />);
    await waitFor(() => expect(screen.getByTestId("event-form")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("event-create-btn"));
    await waitFor(() =>
      expect(api.createEvent).toHaveBeenCalledWith(
        "s1",
        expect.objectContaining({ region_id: "r1", category: "war" }),
      ),
    );
  });

  it("suggests, then approves/discards/resolves events", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.listEvents as Mock).mockResolvedValue([
      {
        id: "e1", session_id: "s1", region_id: "r1", category: "war", description: "siege",
        magnitude: 0.7, lifecycle: "persistent", status: "suggested", created_turn: 0, contributions: {},
      },
      {
        id: "e2", session_id: "s1", region_id: "r2", category: "festival", description: "fair",
        magnitude: 0.3, lifecycle: "one_shot", status: "active", created_turn: 1, contributions: {},
      },
    ]);
    (api.suggestEvents as Mock).mockResolvedValue([]);
    (api.approveEvent as Mock).mockResolvedValue({});
    (api.resolveEvent as Mock).mockResolvedValue({});
    render(<GmHub session={OPEN_SESSION} regionId={null} />);
    await waitFor(() => expect(screen.getByTestId("event-e1")).toBeInTheDocument());
    expect(screen.getByTestId("event-status-e1")).toHaveTextContent("suggested");

    fireEvent.click(screen.getByTestId("suggest-events-btn"));
    await waitFor(() => expect(api.suggestEvents).toHaveBeenCalledWith("s1", 1));

    fireEvent.click(screen.getByTestId("approve-e1"));
    await waitFor(() => expect(api.approveEvent).toHaveBeenCalledWith("s1", "e1"));

    fireEvent.click(screen.getByTestId("resolve-e2"));
    await waitFor(() => expect(api.resolveEvent).toHaveBeenCalledWith("s1", "e2"));
  });

  it("reflects real per-region distortion from listDistortions", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([
      { session_id: "s1", region_id: "r1", distortion_degree: 0.75 },
    ]);
    render(<GmHub session={OPEN_SESSION} regionId="r1" />);
    await waitFor(() => expect(screen.getByText(new RegExp(`${t("gm.distortion")} 0\\.75`))).toBeInTheDocument());
  });

  it("generate-all fills only empty regions (X3)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([
      { session_id: "s1", region_id: "r1", distortion_degree: 0.3 },
      { session_id: "s1", region_id: "r2", distortion_degree: 0.3 },
    ]);
    // U3 intended change (U7 review C1): one state read gives the counts
    (api.getWorldState as Mock).mockResolvedValue({ session_id: "s1", turn: 0, player_region_id: null,
      regions: [{ region_id: "r1", region_name: "r1", distortion: 0.3, feedback_share: 0, active_rumors: 0, promoted_rumors: 0, deed_rumors: 0, active_events: 0 }, { region_id: "r2", region_name: "r2", distortion: 0.3, feedback_share: 0, active_rumors: 1, promoted_rumors: 0, deed_rumors: 0, active_events: 0 }] });
    (api.generateRumors as Mock).mockResolvedValue([]);
    render(<GmHub session={OPEN_SESSION} regionId={null} />);
    fireEvent.click(await screen.findByTestId("generate-all-btn"));
    await waitFor(() => expect(api.generateRumors).toHaveBeenCalledWith("s1", "r1"));
    expect(api.generateRumors).not.toHaveBeenCalledWith("s1", "r2");
  });

  it("regen-all confirms before regenerating all regions (X3)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([
      { session_id: "s1", region_id: "r1", distortion_degree: 0.3 },
    ]);
    (api.regenRumors as Mock).mockResolvedValue([]);
    render(<GmHub session={OPEN_SESSION} regionId={null} />);
    fireEvent.click(await screen.findByTestId("regen-all-btn"));
    expect(api.regenRumors).not.toHaveBeenCalled(); // confirmation pending
    fireEvent.click(screen.getByText(t("action.confirm")));
    await waitFor(() => expect(api.regenRumors).toHaveBeenCalledWith("s1", "r1"));
  });

  it("shows a per-region notification after advancing a turn (X3 / FR-UX2.6)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.advanceTurn as Mock).mockResolvedValue({
      session_id: "s1",
      turn: 3,
      promoted_ids: ["ra"],
      demoted_ids: [],
      region_changes: [
        {
          region_id: "r1",
          promoted: ["ra"],
          demoted: [],
          pruned: [],
          events_applied: [],
          events_resolved: [],
          rumors_added: [],
        },
      ],
    });
    renderWithShell(<GmHub session={OPEN_SESSION} regionId={null} />); // V2: toasts live in the shell
    fireEvent.click(await screen.findByTestId("advance-turn-btn"));
    // V2: the notification area is always there (a live region), so wait for the card itself
    expect(await screen.findByText(t("notif.title", { region_id: "r1" }))).toBeInTheDocument(); // notif title
    expect(screen.getByText(t("notif.promoted", { n: 1 }))).toBeInTheDocument();
  });

  it("localizes rumor text with an original toggle (X3 / FR-UX3.4)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([
      {
        id: "ru1", session_id: "s1", region_id: "r1", distorted_from_id: "k",
        distorted_from_kind: "knowledge", statement: "twisted tale", distortion_degree: 0.3,
        support: 0.5, confidence: 0.5, promoted: false, statement_ko: "뒤틀린 이야기",
      },
    ]);
    render(<GmHub session={OPEN_SESSION} regionId="r1" />);
    await waitFor(() => expect(screen.getByText("뒤틀린 이야기")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("rumor-text-ru1-toggle"));
    expect(screen.getByText("twisted tale")).toBeInTheDocument();
  });

  it("localizes timeline entries via kind+payload (X3 / F2a)", async () => {
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.getTimeline as Mock).mockResolvedValue([
      { id: "t1", session_id: "s1", turn: 2, kind: "promote", summary: "promoted ra",
        payload: { rumor_id: "ra", region_id: "r1", region_name: "Riverton" } },
    ]);
    render(<GmHub session={OPEN_SESSION} regionId={null} />);
    // U7 intended change: FR-D3 — the line names the region
    await waitFor(() =>
      expect(screen.getByText(new RegExp(t("timeline.promote", { region: "Riverton" })))).toBeInTheDocument(),
    );
  });
});

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
    (api.listSessions as Mock).mockResolvedValue([]);
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listEvents as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([]);
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
    await waitFor(() => expect(screen.getByTestId("session-panel")).toBeInTheDocument());
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
    await waitFor(() => expect(screen.getByTestId("session-panel")).toBeInTheDocument());
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
    expect(screen.getByAltText("world map")).toHaveAttribute("src", "blob:map");
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
