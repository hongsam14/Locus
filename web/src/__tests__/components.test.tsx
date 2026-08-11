import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MapOverlay } from "../MapOverlay";
import { RegionPanel } from "../RegionPanel";
import { AugmentPanel } from "../AugmentPanel";
import { SessionBar } from "../SessionBar";
import { SessionPanel } from "../SessionPanel";
import type { ConnectionEdge, GameSession, Region } from "../types";

vi.mock("../api", () => ({
  api: {
    regionKnowledge: vi.fn(),
    sessionKnowledge: vi.fn(),
    startAugment: vi.fn(),
    submitAnswer: vi.fn(),
    revertAugment: vi.fn(),
    deleteNode: vi.fn(),
    listSessions: vi.fn(),
    startSession: vi.fn(),
    closeSession: vi.fn(),
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
        { knowledge_id: "k1", statement: "Sunday market", scope_type: "direct", is_rumor: false, confidence: 0.9 },
      ],
      shared_ids: [],
      unique_ids: ["k1"],
    });
    render(<RegionPanel worldId="w" regionId="r1" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-item-k1")).toBeInTheDocument());
    expect(screen.getByText(/Sunday market/)).toBeInTheDocument();
  });
});

describe("AugmentPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("starts a session and shows questions", async () => {
    (api.startAugment as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "s1",
      world_id: "w",
      round: 0,
      status: "open",
      open_questions: [{ id: "q1", issue_id: "i1", text: "What is known here?", options: ["add", "ignore"], kind: "confirm" }],
      history: [],
    });
    render(<AugmentPanel worldId="w" />);
    fireEvent.click(screen.getByTestId("augment-start-btn"));
    await waitFor(() => expect(screen.getByText(/What is known here/)).toBeInTheDocument());
    expect(screen.getAllByTestId("augment-answer-btn").length).toBe(2);
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

describe("SessionPanel (GameMaster hub)", () => {
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
    render(<SessionPanel session={OPEN_SESSION} regionId="r1" />);
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
    render(<SessionPanel session={OPEN_SESSION} regionId={null} />);
    expect(screen.getByTestId("gm-no-region")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("advance-turn-btn"));
    await waitFor(() => expect(api.advanceTurn).toHaveBeenCalledWith("s1"));
  });

  it("refresh loads independent reads in parallel (FR-H6)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    render(<SessionPanel session={OPEN_SESSION} regionId="r1" />);
    // all three region-independent reads + the region rumor read are issued
    await waitFor(() => expect(api.getTimeline).toHaveBeenCalledWith("s1"));
    expect(api.listEvents).toHaveBeenCalledWith("s1");
    expect(api.listDistortions).toHaveBeenCalledWith("s1");
    expect(api.listRumors).toHaveBeenCalledWith("s1", "r1");
  });

  it("refresh skips the rumor read when no region is selected (FR-H6)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    render(<SessionPanel session={OPEN_SESSION} regionId={null} />);
    await waitFor(() => expect(api.getTimeline).toHaveBeenCalledWith("s1"));
    expect(api.listRumors).not.toHaveBeenCalled();
  });

  it("disables write controls on a closed session", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValue([]);
    render(
      <SessionPanel session={{ ...OPEN_SESSION, status: "closed" }} regionId="r1" />,
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
    render(<SessionPanel session={OPEN_SESSION} regionId="r1" />);
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
    render(<SessionPanel session={OPEN_SESSION} regionId={null} />);
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
    render(<SessionPanel session={OPEN_SESSION} regionId="r1" />);
    await waitFor(() => expect(screen.getByText(/distortion 0\.75/)).toBeInTheDocument());
  });
});

describe("RegionPanel session view", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses sessionKnowledge when a session is active", async () => {
    (api.sessionKnowledge as Mock).mockResolvedValue({
      world_id: "w", region_id: "r1", items: [], shared_ids: [], unique_ids: [],
    });
    render(<RegionPanel worldId="w" regionId="r1" sessionId="s1" />);
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalledWith("s1", "r1"));
    expect(api.regionKnowledge).not.toHaveBeenCalled();
  });
});
