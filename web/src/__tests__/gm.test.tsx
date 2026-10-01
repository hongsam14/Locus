// U7 GM mode & hardening (frontend-components §6): CommitRange, the play <-> GM switch,
// the world state overlay, the event panel's lifecycle buttons, names on the timeline,
// and the U6 review items carried into U7 (#5, #10-#13, #15, C1).
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import { conflictKind } from "../api/http";
import { MapOverlay } from "../MapOverlay";
import { ActionBar, declaredLength } from "../features/play/ActionBar";
import { DeedPanel } from "../features/gm/DeedPanel";
import { EventPanel } from "../features/gm/EventPanel";
import { GmHub } from "../features/gm/GmHub";
import { PlayerStrip } from "../features/gm/PlayerStrip";
import { WorldStateOverlay, overlayOf, useWorldState } from "../features/gm/WorldStateOverlay";
import { t, timelineText } from "../i18n";
import { GmPage } from "../routes/GmPage";
import { PlayPage } from "../routes/PlayPage";
import type { GameSession, Region, SessionEvent, WorldState } from "../types";
import { CommitRange } from "../ui";

vi.mock("../api", () => ({
  api: {
    getSession: vi.fn(),
    getRegion: vi.fn(),
    getLog: vi.fn(),
    act: vi.fn(),
    getTurnRun: vi.fn(),
    listTurnRuns: vi.fn(),
    listNpcs: vi.fn(),
    getPlayer: vi.fn(),
    getWorldState: vi.fn(),
    getTimeline: vi.fn(),
    listEvents: vi.fn(),
    listDistortions: vi.fn(),
    listRumors: vi.fn(),
    generateRumors: vi.fn(),
    listDeeds: vi.fn(),
    voidDeed: vi.fn(),
    startDialogue: vi.fn(),
    setDistortion: vi.fn(),
    advanceTurn: vi.fn(),
    exportWorld: vi.fn(),
    listSessions: vi.fn(),
    dialogueHistory: vi.fn(),
    say: vi.fn(),
  },
}));

import { api } from "../api";

const OPEN: GameSession = { id: "s1", world_id: "w", status: "open", turn: 3 };

beforeEach(() => {
  vi.clearAllMocks();
});

// --- CommitRange (BR-U7-24, FR-D5) ------------------------------------------------ //
describe("CommitRange", () => {
  it("saves on an arrow key once, never twice for the same value, and on blur", () => {
    const onCommit = vi.fn();
    render(<CommitRange data-testid="r" min={0} max={1} step={0.1} value={0.3} onCommit={onCommit} />);
    const r = screen.getByTestId("r");
    fireEvent.change(r, { target: { value: "0.4" } });
    fireEvent.keyUp(r, { key: "ArrowRight" });
    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(onCommit).toHaveBeenLastCalledWith(0.4);
    fireEvent.keyUp(r, { key: "ArrowRight" }); // same value: not sent again
    fireEvent.keyUp(r, { key: "a" }); // not a slider key
    expect(onCommit).toHaveBeenCalledTimes(1);
    fireEvent.change(r, { target: { value: "0.6" } });
    fireEvent.blur(r);
    expect(onCommit).toHaveBeenCalledTimes(2);
  });

  it("saves on pointer and touch release", () => {
    const onCommit = vi.fn();
    render(<CommitRange data-testid="r" min={0} max={1} step={0.1} value={0.3} onCommit={onCommit} />);
    const r = screen.getByTestId("r");
    fireEvent.change(r, { target: { value: "0.5" } });
    fireEvent.pointerUp(r);
    fireEvent.change(r, { target: { value: "0.7" } });
    fireEvent.touchEnd(r);
    expect(onCommit.mock.calls.map((c) => c[0])).toEqual([0.5, 0.7]);
  });
});

// --- play <-> GM (Q1=B, BR-U7-21/22) ------------------------------------------------ //
describe("GM mode switch", () => {
  it("the play screen's GM button goes to /gm/:sid", async () => {
    (api.getSession as Mock).mockResolvedValue(OPEN);
    (api.getRegion as Mock).mockRejectedValue(new Error("not needed"));
    (api.getLog as Mock).mockResolvedValue([]);
    (api.listTurnRuns as Mock).mockResolvedValue([]);
    (api.listNpcs as Mock).mockResolvedValue([]);
    render(
      <MemoryRouter initialEntries={["/play/s1"]}>
        <Routes>
          <Route path="/play/:sessionId?" element={<PlayPage pollMs={5} />} />
          <Route path="/gm/:sessionId" element={<div data-testid="gm-route">gm</div>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByTestId("play-gm-btn"));
    expect(await screen.findByTestId("gm-route")).toBeInTheDocument();
  });

  function strip() {
    return render(
      <MemoryRouter initialEntries={["/gm/s1"]}>
        <Routes>
          <Route
            path="/gm/:sessionId"
            element={<PlayerStrip sessionId="s1" turn={3} regionNames={{ a: "Riverton" }} rev={0} />}
          />
          <Route path="/play/:sessionId" element={<div data-testid="play-route">play</div>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("the GM screen shows where the player is and leads back to play", async () => {
    (api.getPlayer as Mock).mockResolvedValue({ id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 });
    (api.listTurnRuns as Mock).mockResolvedValue([{ id: "run1" }]);
    strip();
    const status = await screen.findByTestId("gm-player-status");
    expect(status).toHaveTextContent(t("gm.playerStatus", { name: "Ari", region: "Riverton", turn: 3 }));
    expect(status).toHaveTextContent(t("gm.running"));
    expect(api.listTurnRuns).toHaveBeenCalledWith("s1", "running"); // FD review R-08
    fireEvent.click(screen.getByTestId("gm-back-to-play"));
    expect(await screen.findByTestId("play-route")).toBeInTheDocument();
  });

  it("a GM session without a player shows no strip and no way back", async () => {
    (api.getPlayer as Mock).mockRejectedValue(new Error("404 Not Found"));
    (api.listTurnRuns as Mock).mockResolvedValue([]);
    strip();
    await waitFor(() => expect(api.getPlayer).toHaveBeenCalled());
    expect(screen.queryByTestId("gm-player-status")).not.toBeInTheDocument();
    expect(screen.queryByTestId("gm-back-to-play")).not.toBeInTheDocument();
  });
});

// --- world state overlay (US-5.5, BR-U7-23) ------------------------------------------ //
const STATE: WorldState = {
  session_id: "s1",
  turn: 3,
  player_region_id: "a",
  regions: [
    { region_id: "a", region_name: "Riverton", distortion: 0.7, feedback_share: 0.1, active_rumors: 3, promoted_rumors: 1, deed_rumors: 0, active_events: 1 },
    { region_id: "b", region_name: "Hollow", distortion: 0.1, feedback_share: 0, active_rumors: 2, promoted_rumors: 0, deed_rumors: 1, active_events: 0 },
  ],
};

function Harness({ regions }: { regions: Region[] }) {
  const [on, setOn] = useState(false);
  const world = useWorldState("s1", on, 0);
  const o = overlayOf(world.state);
  return (
    <>
      <WorldStateOverlay on={on} onToggle={() => setOn((v) => !v)} error={world.error} />
      <MapOverlay
        regions={regions}
        connections={[]}
        onSelect={() => {}}
        onMove={() => {}}
        markerId="a"
        regionFill={on ? o.fill : undefined}
        regionBadge={on ? o.badge : undefined}
      />
    </>
  );
}
describe("WorldStateOverlay", () => {
  const regions = ["a", "b"].map(
    (id) => ({ id, world_id: "w", name: id === "a" ? "Riverton" : "Hollow", level: "town" }) as unknown as Region,
  );

  it("reads the state when turned on, badges active/promoted and clears when off", async () => {
    (api.getWorldState as Mock).mockResolvedValue(STATE);
    render(<Harness regions={regions} />);
    expect(screen.getByTestId("player-marker-a")).toBeInTheDocument(); // BR-U7-22
    expect(api.getWorldState).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("gm-state-toggle"));
    expect(await screen.findByTestId("region-badge-a")).toHaveTextContent("3/1");
    expect(screen.getByTestId("region-badge-b")).toHaveTextContent("2/0 ✦1");
    expect(screen.getByTestId("gm-state-legend")).toBeInTheDocument();
    expect(api.getWorldState).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("gm-state-toggle"));
    await waitFor(() => expect(screen.queryByTestId("region-badge-a")).not.toBeInTheDocument());
  });

  it("colors by five distortion bands", () => {
    const { fill } = overlayOf(STATE);
    expect(fill.a).toContain("75%");
    expect(fill.b).toContain(" 0%");
  });
});

// --- events (BR-U7-7/8) and names (FR-D3) ------------------------------------------- //
describe("EventPanel and the timeline", () => {
  const ev = (id: string, status: SessionEvent["status"]): SessionEvent =>
    ({ id, session_id: "s1", region_id: "a", category: "war", description: "", magnitude: 0.5, lifecycle: "persistent", status, created_turn: 0, contributions: {} }) as unknown as SessionEvent;

  it("a suggestion has approve and discard but never resolve; an active one only resolve", () => {
    render(
      <EventPanel
        events={[ev("e1", "suggested"), ev("e2", "active")]}
        regionId={null}
        regionNames={{ a: "Riverton" }}
        closed={false}
        onApprove={() => {}}
        onDiscard={() => {}}
        onResolve={() => {}}
        onCreate={() => {}}
      />,
    );
    expect(screen.getByTestId("approve-e1")).toBeInTheDocument();
    expect(screen.getByTestId("discard-e1")).toBeInTheDocument();
    expect(screen.queryByTestId("resolve-e1")).not.toBeInTheDocument();
    expect(screen.getByTestId("resolve-e2")).toBeInTheDocument();
    expect(screen.queryByTestId("approve-e2")).not.toBeInTheDocument();
    expect(screen.getByTestId("event-e1")).toHaveTextContent("Riverton");
  });

  it("lines read by name; an older line without one falls back to the id", () => {
    expect(timelineText("event_suggested", { region_name: "Riverton", category: "war" }, 1)).toBe(
      t("timeline.event_suggested", { region: "Riverton", category: "war" }),
    );
    expect(timelineText("promote", { rumor_id: "r", region_id: "a" }, 1)).toBe(
      t("timeline.promote", { region: "a" }),
    );
    // a pre-U7 approval line (event_created + approved) reads as an approval
    expect(timelineText("event_created", { approved: true, region_id: "a", category: "war" }, 1)).toBe(
      t("timeline.event_approved", { region: "a", category: "war" }),
    );
    expect(timelineText("session_started", { player: null }, 0)).toBe(t("timeline.gm_session_started"));
  });
});

// --- U6 review items carried into U7 ------------------------------------------------ //
describe("U6 review carry-overs", () => {
  it("#5: generate-all counts canonical rumors only, so a deed-only region is filled", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listEvents as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([
      { session_id: "s1", region_id: "a", distortion_degree: 0.3 },
      { session_id: "s1", region_id: "b", distortion_degree: 0.3 },
    ]);
    (api.listRumors as Mock).mockImplementation(async (_s: string, rid: string) =>
      rid === "a" ? [{ id: "d1", origin_kind: "deed" }] : [{ id: "c1", origin_kind: "canonical" }],
    );
    (api.generateRumors as Mock).mockResolvedValue([]);
    render(<GmHub session={OPEN} regionId={null} />);
    await waitFor(() => expect(api.listDistortions).toHaveBeenCalled());
    await act(async () => fireEvent.click(await screen.findByTestId("generate-all-btn")));
    await waitFor(() => expect(api.generateRumors).toHaveBeenCalledTimes(1));
    expect(api.generateRumors).toHaveBeenCalledWith("s1", "a");
  });

  it("#11: a 409 is told apart — closed for good or a turn running", () => {
    expect(conflictKind(new Error("409 Conflict: session is closed: s1"))).toBe("closed");
    expect(conflictKind(new Error("409 Conflict: turn in progress"))).toBe("busy");
    expect(conflictKind(new Error("400 Bad Request: nope"))).toBeNull();
  });

  it("#12: the declaration box is locked while its request is out", async () => {
    let answer: (v: boolean) => void = () => {};
    const onDeclare = vi.fn(() => new Promise<boolean>((r) => (answer = r)));
    render(<ActionBar running={null} disabled={false} onWait={() => {}} onDeclare={onDeclare} />);
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "I sing" } });
    fireEvent.click(screen.getByTestId("declare-btn"));
    await waitFor(() => expect(screen.getByTestId("declare-input")).toBeDisabled());
    expect(screen.getByTestId("declare-btn")).toBeDisabled();
    await act(async () => answer(false));
    expect(screen.getByTestId("declare-input")).toBeEnabled();
    expect(screen.getByTestId("declare-input")).toHaveValue("I sing");
  });

  it("#15: the declaration counts code points and the server's spaces", () => {
    expect(declaredLength("😀😀a")).toBe(3); // UTF-16 length would be 5
    render(<ActionBar running={null} disabled={false} onWait={() => {}} onDeclare={async () => true} maxChars={3} />);
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: " \u0085 " } });
    expect(screen.getByTestId("declare-btn")).toBeDisabled(); // nothing left after strip
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "😀😀😀" } });
    expect(screen.getByTestId("declare-btn")).toBeEnabled(); // 3 code points, not 6 units
  });

  it("#13 and C1: one void per confirmation, one deed read per void", async () => {
    const view = {
      deed: { id: "d1", session_id: "s1", player_id: "p", region_id: "a", turn: 0, kind: "arrival", text: "Ari came.", witnessed_npc_ids: [], voided: false, region_name: "A", witness_names: [] },
      appraisals: [],
      rumors: [],
      reached_region_ids: [],
      reached_region_names: [],
    };
    (api.listDeeds as Mock).mockResolvedValue([view]);
    let done: () => void = () => {};
    (api.voidDeed as Mock).mockImplementation(() => new Promise<void>((r) => (done = r)));
    render(<DeedPanel sessionId="s1" closed={false} />);
    fireEvent.click(await screen.findByTestId("void-d1"));
    const dialog = within(screen.getByRole("dialog"));
    const confirm = dialog.getByRole("button", { name: t("deed.voidConfirmBtn") });
    fireEvent.click(confirm);
    await waitFor(() => expect(confirm).toBeDisabled());
    fireEvent.click(confirm); // a double click sends nothing more
    const before = (api.listDeeds as Mock).mock.calls.length;
    await act(async () => done());
    expect(api.voidDeed).toHaveBeenCalledTimes(1);
    expect((api.listDeeds as Mock).mock.calls.length - before).toBe(1);
  });
});


// --- the play screen: a closed session (#10) and the talked-to count (U5 C1) --------- //
describe("PlayPage after U7", () => {
  const VIEW = {
    session_id: "s1",
    turn: 3,
    player: { id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 },
    region_id: "a",
    region_name: "Riverton",
    level: "town",
    description: "",
    level_path: ["Riverton"],
    npcs: [
      { id: "n1", world_id: "w", name: "Mara", role: "innkeeper", description: "", home_region_id: "a", traits: [], provenance: { source: "input" } },
    ],
    facts: [],
    hearsay: [],
    rumors: [],
    moves: [],
    turn_running: false,
    llm_available: true,
  };

  function play() {
    return render(
      <MemoryRouter initialEntries={["/play/s1"]}>
        <Routes>
          <Route path="/play/:sessionId?" element={<PlayPage pollMs={5} />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  beforeEach(() => {
    (api.getRegion as Mock).mockResolvedValue(VIEW);
    (api.getLog as Mock).mockResolvedValue([]);
    (api.listTurnRuns as Mock).mockResolvedValue([]);
    (api.listNpcs as Mock).mockResolvedValue([{ npc: VIEW.npcs[0], has_conversation: false, message_count: 0 }]);
  });

  it("#10: a closed session locks the actions", async () => {
    (api.getSession as Mock).mockResolvedValue({ ...OPEN, status: "closed" });
    play();
    await waitFor(() => expect(screen.getByTestId("wait-btn")).toBeDisabled());
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "I sing" } });
    expect(screen.getByTestId("declare-btn")).toBeDisabled();
  });

  it("U5 C1: a spoken line adds two to the count without re-reading the people here", async () => {
    (api.getSession as Mock).mockResolvedValue(OPEN);
    (api.startDialogue as Mock).mockResolvedValue({ id: "c1", session_id: "s1", npc_id: "n1", started_turn: 3, messages: [] });
    (api.dialogueHistory as Mock).mockResolvedValue({ id: "c1", session_id: "s1", npc_id: "n1", started_turn: 3, messages: [] });
    (api.say as Mock).mockResolvedValue({
      message: { id: "m2", conversation_id: "c1", role: "npc", text: "Hm.", lang: "ko", turn: 3 },
      lang: "ko",
      llm_calls: 1,
      context_ids: [],
    });
    play();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await waitFor(() => expect(screen.getByTestId("dialogue-input")).toBeEnabled());
    const reads = (api.listNpcs as Mock).mock.calls.length;
    fireEvent.change(screen.getByTestId("dialogue-input"), { target: { value: "hello" } });
    await act(async () => fireEvent.click(screen.getByTestId("dialogue-send-btn")));
    await waitFor(() => expect(api.say).toHaveBeenCalled());
    expect((api.listNpcs as Mock).mock.calls.length).toBe(reads);
    await waitFor(() =>
      expect(screen.getByTestId("npc-n1-talked")).toHaveTextContent(t("dialogue.has", { n: 2 })),
    );
  });
});


// --- U7 code review follow-ups (#1, #4, #11) ------------------------------------------ //
describe("U7 review follow-ups", () => {
  it("#1: tabbing past or clicking a slider never saves the browser's snapped value", () => {
    const onCommit = vi.fn();
    render(<CommitRange data-testid="r" min={0} max={1} step={0.05} value={0.375} onCommit={onCommit} />);
    const r = screen.getByTestId("r");
    // a real browser shows 0.375 as 0.4 (step); no change event was ever fired
    fireEvent.blur(r, { target: { value: "0.4" } });
    fireEvent.pointerUp(r, { target: { value: "0.4" } });
    fireEvent.keyUp(r, { key: "Tab", target: { value: "0.4" } });
    expect(onCommit).not.toHaveBeenCalled();
  });

  it("#4: a refused save puts the thumb back and the same value can be sent again", async () => {
    const onCommit = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<CommitRange data-testid="r" min={0} max={1} step={0.05} value={0.3} onCommit={onCommit} />);
    const r = screen.getByTestId("r") as HTMLInputElement;
    fireEvent.change(r, { target: { value: "0.5" } });
    await act(async () => fireEvent.pointerUp(r));
    expect(r.value).toBe("0.3"); // refused: back to the server's value
    fireEvent.change(r, { target: { value: "0.5" } });
    await act(async () => fireEvent.pointerUp(r));
    expect(onCommit.mock.calls.map((c) => c[0])).toEqual([0.5, 0.5]);
  });

  it("#11: a GM write refused because the session closed tells the page", async () => {
    (api.getTimeline as Mock).mockResolvedValue([]);
    (api.listEvents as Mock).mockResolvedValue([]);
    (api.listDistortions as Mock).mockResolvedValue([{ session_id: "s1", region_id: "a", distortion_degree: 0.3 }]);
    (api.listRumors as Mock).mockResolvedValue([]);
    (api.advanceTurn as Mock).mockRejectedValue(new Error("409 Conflict: session is closed: s1"));
    const onChanged = vi.fn();
    render(<GmHub session={OPEN} regionId={null} onChanged={onChanged} />);
    await act(async () => fireEvent.click(await screen.findByTestId("advance-turn-btn")));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });
});


it("#11 (page): a void refused because the session closed re-reads the session", async () => {
  (api.getSession as Mock).mockResolvedValue(OPEN);
  (api.exportWorld as Mock).mockResolvedValue({ world_id: "w", regions: [], connections: [], entities: [], knowledge: [] });
  (api.listSessions as Mock).mockResolvedValue([OPEN]);
  (api.getPlayer as Mock).mockRejectedValue(new Error("404"));
  (api.listTurnRuns as Mock).mockResolvedValue([]);
  (api.getTimeline as Mock).mockResolvedValue([]);
  (api.listEvents as Mock).mockResolvedValue([]);
  (api.listDistortions as Mock).mockResolvedValue([]);
  (api.listRumors as Mock).mockResolvedValue([]);
  (api.listDeeds as Mock).mockResolvedValue([
    {
      deed: { id: "d1", session_id: "s1", player_id: "p", region_id: "a", turn: 0, kind: "arrival", text: "Ari came.", witnessed_npc_ids: [], voided: false, region_name: "A", witness_names: [] },
      appraisals: [], rumors: [], reached_region_ids: [], reached_region_names: [],
    },
  ]);
  (api.voidDeed as Mock).mockRejectedValue(new Error("409 Conflict: session is closed: s1"));
  render(
    <MemoryRouter initialEntries={["/gm/s1"]}>
      <Routes>
        <Route path="/gm/:sessionId" element={<GmPage />} />
      </Routes>
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByTestId("void-d1"));
  const before = (api.getSession as Mock).mock.calls.length;
  await act(async () =>
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("deed.voidConfirmBtn") })),
  );
  await waitFor(() => expect((api.getSession as Mock).mock.calls.length).toBeGreaterThan(before));
  expect(screen.getByTestId("deed-notice")).toHaveTextContent(t("play.sessionClosed"));
});
