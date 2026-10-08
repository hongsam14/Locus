// U7 GM mode & hardening (frontend-components §6): CommitRange, the play <-> GM switch,
// the world state overlay, the event panel's lifecycle buttons, names on the timeline,
// and the U6 review items carried into U7 (#5, #10-#13, #15, C1).
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import type { Mock } from "vitest";
import { conflictKind } from "../api/http";
import { mapLimit } from "../features/gm/bulk";
import { resetCapabilities } from "../capabilities";
import { MapOverlay } from "../MapOverlay";
import { ActionBar, declaredLength } from "../features/play/ActionBar";
import { DeedPanel } from "../features/gm/DeedPanel";
import { EventPanel } from "../features/gm/EventPanel";
import { PlayerStrip } from "../features/gm/PlayerStrip";
import { distortionColor } from "../features/gm/WorldStateOverlay";
import { enumLabel, numberWithMeaning, turnLabel } from "../format";
import { t, timelineText } from "../i18n";
import { GmPage } from "../routes/GmPage";
import { PlayPage } from "../routes/PlayPage";
import type { GameSession, Region, SeedView, SessionEvent, WorldState } from "../types";
import { CommitRange } from "../ui";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn().mockResolvedValue({ llm: true, vlm: true, embedding: true }),
    listSeeds: vi.fn().mockResolvedValue([]),
    startSeed: vi.fn(),
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
    // V6: the GM screen's other reads and writes
    worldNames: vi.fn(),
    regenRumors: vi.fn(),
    setSupport: vi.fn(),
    createEvent: vi.fn(),
    suggestEvents: vi.fn(),
    approveEvent: vi.fn(),
    discardEvent: vi.fn(),
    resolveEvent: vi.fn(),
    closeSession: vi.fn(),
    startSession: vi.fn(),
    sessionKnowledge: vi.fn(),
  },
}));

import { api } from "../api";

const OPEN: GameSession = { id: "s1", world_id: "w", status: "open", turn: 3 };

beforeEach(() => {
  vi.clearAllMocks();
  // no test inherits another's "LLM off" answer (code review 01 #21)
  resetCapabilities();
  (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
});

// V6: the GM tests drive the real screen (GmPage) over these reads; a test changes what it needs.
const WORLD = { world_id: "w", regions: [{ id: "a", name: "Riverton", level: "town" }, { id: "b", name: "Hollow", level: "town" }],
  connections: [], entities: [], knowledge: [], scopes: [] };
const gmState = (over: Partial<WorldState> = {}): WorldState => ({
  session_id: "s1", turn: 3, player_region_id: null,
  regions: ["a", "b"].map((id) => ({ region_id: id, region_name: id, distortion: 0.3, feedback_share: 0, active_rumors: 1,
    promoted_rumors: 0, deed_rumors: 0, active_events: 0 })),
  ...over,
});
function gmReads() {
  (api.getSession as Mock).mockImplementation(async (sid: string) => ({ ...OPEN, id: sid }));
  (api.exportWorld as Mock).mockResolvedValue(WORLD);
  (api.listSessions as Mock).mockResolvedValue([OPEN]);
  (api.worldNames as Mock).mockRejectedValue(new Error("names are not needed here"));
  (api.getTimeline as Mock).mockResolvedValue([]);
  (api.listEvents as Mock).mockResolvedValue([]);
  (api.getWorldState as Mock).mockResolvedValue(gmState());
  (api.listRumors as Mock).mockResolvedValue([]);
  (api.listSeeds as Mock).mockResolvedValue([]);
  (api.listDeeds as Mock).mockResolvedValue([]);
  (api.getPlayer as Mock).mockRejectedValue(new HttpError(404, "Not Found", "no player"));
  (api.listTurnRuns as Mock).mockResolvedValue([]);
}
function renderGm(path = "/gm/s1") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/gm/:sessionId" element={<GmPage />} />
        <Route path="/play/:sessionId" element={<div data-testid="play-route">play</div>} />
      </Routes>
    </MemoryRouter>,
  );
}
async function chooseRegion(id: string) {
  fireEvent.click(await screen.findByTestId(`region-marker-${id}`));
  await screen.findByTestId("gm-region");
}
async function openTab(name: "events" | "seeds" | "timeline" | "deeds" | "region") {
  const tab = (await screen.findByTestId(`gm-tab-${name}`)).closest('[role="tab"]') as HTMLElement;
  fireEvent.mouseDown(tab, { button: 0 });
  fireEvent.click(tab);
}

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
  // V4 intended change (BR-V4-20, R-11): the play screen has no GM button; the menu's GM
  // item goes to this session's GM screen
  it("the menu's GM item on the play screen goes to /gm/:sid", async () => {
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
    await screen.findByTestId("play-page");
    expect(screen.queryByTestId("play-gm-btn")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("nav-gm"));
    expect(await screen.findByTestId("gm-route")).toBeInTheDocument();
  });

  it("the GM screen shows where the player is and leads back to play", async () => {
    gmReads();
    (api.getPlayer as Mock).mockResolvedValue({ id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 });
    (api.listTurnRuns as Mock).mockResolvedValue([{ id: "run1" }]);
    renderGm();
    const status = await screen.findByTestId("gm-player-status");
    // V6: in words — name · region · turn, and that a turn is running (with [check again])
    expect(status).toHaveTextContent(`Ari · Riverton · ${turnLabel(3)}`);
    expect(status).toHaveTextContent(t("label.turnRunning"));
    expect(screen.getByTestId("gm-player-recheck")).toBeInTheDocument();
    expect(api.listTurnRuns).toHaveBeenCalledWith("s1", "running"); // FD review R-08
    fireEvent.click(screen.getByTestId("gm-back-to-play"));
    expect(await screen.findByTestId("play-route")).toBeInTheDocument();
  });

  it("a GM session without a player shows no strip and no way back", async () => {
    gmReads();
    renderGm();
    await screen.findByTestId("turn-tools");
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

describe("world state colours", () => {
  // V6: the switch, legend and badge moved to MapPane (gm.parts.test.tsx); the state is read
  // with the session's other reads (gm.layout.test.tsx, BR-V6-32)
  it("colors by five distortion bands", () => {
    expect(distortionColor(STATE.regions[0].distortion)).toContain("75%");
    expect(distortionColor(STATE.regions[1].distortion)).toContain(" 0%");
  });
});

// --- events (BR-U7-7/8) and names (FR-D3) ------------------------------------------- //
describe("EventPanel and the timeline", () => {
  const ev = (id: string, status: SessionEvent["status"]): SessionEvent =>
    ({ id, session_id: "s1", region_id: "a", category: "war", description: "", magnitude: 0.5, lifecycle: "persistent", status, created_turn: 0, contributions: {} }) as unknown as SessionEvent;

  it("a suggestion has approve and discard but never resolve; an active one only resolve", () => {
    const done = () => Promise.resolve(true);
    render(
      <EventPanel
        events={{ data: [ev("e1", "suggested"), ev("e2", "active")], state: "ready", reload: vi.fn() }}
        regionName={(id) => (id === "a" ? "Riverton" : id)}
        closed={false}
        onApprove={done}
        onDiscard={done}
        onResolve={done}
        onPickRegion={vi.fn()}
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
    gmReads();
    // U3 intended change (U7 review C1): one state read gives the counts
    (api.getWorldState as Mock).mockResolvedValue(gmState({ turn: 0, regions: [
      { region_id: "a", region_name: "a", distortion: 0.3, feedback_share: 0, active_rumors: 1, promoted_rumors: 0, deed_rumors: 1, active_events: 0 },
      { region_id: "b", region_name: "b", distortion: 0.3, feedback_share: 0, active_rumors: 1, promoted_rumors: 0, deed_rumors: 0, active_events: 0 },
    ] }));
    (api.generateRumors as Mock).mockResolvedValue([]);
    renderGm();
    await waitFor(async () => expect(await screen.findByTestId("generate-all-btn")).toBeEnabled()); // the session is here
    await act(async () => fireEvent.click(screen.getByTestId("generate-all-btn")));
    await waitFor(() => expect(api.generateRumors).toHaveBeenCalledTimes(1));
    expect(api.generateRumors).toHaveBeenCalledWith("s1", "a");
  });

  it("#11: a 409 is told apart — closed for good or a turn running", () => {
    expect(conflictKind(new Error("409 Conflict: session is closed: s1"))).toBe("closed");
    expect(conflictKind(new Error("409 Conflict: turn in progress"))).toBe("turn_running");
    expect(conflictKind(new Error("400 Bad Request: nope"))).toBeNull();
    // U3 (C16): the typed error answers the same
    expect(conflictKind(new HttpError(409, "Conflict", "session is closed: s1"))).toBe("closed");
    expect(conflictKind(new HttpError(409, "Conflict", "turn in progress"))).toBe("turn_running");
    expect(String(new HttpError(409, "Conflict", "x"))).toBe("Error: 409 Conflict: x");
  });

  it("#12: the declaration box is locked while its request is out", async () => {
    let answer: (v: boolean) => void = () => {};
    const onDeclare = vi.fn(() => new Promise<boolean>((r) => (answer = r)));
    render(<ActionBar running={null} disabled={false} onWait={() => {}} onDeclare={onDeclare} />);
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "I sing" } });
    fireEvent.click(screen.getByTestId("declare-btn"));
    // V4 intended change (code review 01 #7, BR-V4-24): read-only and busy, not disabled,
    // so focus stays; a second press while it is out sends nothing
    await waitFor(() => expect(screen.getByTestId("declare-input")).toHaveAttribute("readonly"));
    expect(screen.getByTestId("declare-btn")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByTestId("declare-btn")).not.toBeDisabled();
    fireEvent.click(screen.getByTestId("declare-btn"));
    expect(onDeclare).toHaveBeenCalledTimes(1);
    await act(async () => answer(false));
    expect(screen.getByTestId("declare-input")).not.toHaveAttribute("readonly");
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
    gmReads();
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
    renderGm();
    await openTab("deeds");
    fireEvent.click(await screen.findByTestId("void-d1"));
    const dialog = within(screen.getByRole("dialog"));
    const confirm = dialog.getByRole("button", { name: t("deed.voidConfirmBtn") });
    fireEvent.click(confirm);
    // V4 (BR-V4-24): a busy button is aria-disabled and ignores presses (not native disabled)
    await waitFor(() => expect(confirm).toHaveAttribute("aria-disabled", "true"));
    fireEvent.click(confirm); // a double click sends nothing more
    const before = (api.listDeeds as Mock).mock.calls.length;
    await act(async () => done());
    expect(api.voidDeed).toHaveBeenCalledTimes(1);
    expect(api.voidDeed).toHaveBeenCalledWith("s1", "d1"); // review #46
    await waitFor(() => expect((api.listDeeds as Mock).mock.calls.length - before).toBe(1));
  });
});


// restored by V6 code review 01 #22 (dropped by mistake in the V6 switch-over)
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
    gmReads();
    (api.advanceTurn as Mock).mockRejectedValue(new HttpError(409, "Conflict", "session is closed: s1"));
    renderGm();
    await waitFor(async () => expect(await screen.findByTestId("advance-turn-btn")).toBeEnabled()); // the session is here
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    await waitFor(() => expect(screen.getByTestId("gm-hub-error")).toBeInTheDocument());
    // the page reads the session again (V6: the closed banner and the locked controls follow)
    await waitFor(() => expect(api.getSession).toHaveBeenCalledTimes(2));
  });
});


it("#11 (page): a void refused because the session closed re-reads the session", async () => {
  gmReads();
  (api.listDeeds as Mock).mockResolvedValue([
    {
      deed: { id: "d1", session_id: "s1", player_id: "p", region_id: "a", turn: 0, kind: "arrival", text: "Ari came.", witnessed_npc_ids: [], voided: false, region_name: "A", witness_names: [] },
      appraisals: [], rumors: [], reached_region_ids: [], reached_region_names: [],
    },
  ]);
  (api.voidDeed as Mock).mockRejectedValue(new HttpError(409, "Conflict", "session is closed: s1"));
  renderGm();
  await openTab("deeds");
  fireEvent.click(await screen.findByTestId("void-d1"));
  const before = (api.getSession as Mock).mock.calls.length;
  await act(async () =>
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("deed.voidConfirmBtn") })),
  );
  await waitFor(() => expect((api.getSession as Mock).mock.calls.length).toBeGreaterThan(before));
  // V6 (BLM § 6): a refused void is told in its dialog
  expect(within(screen.getByRole("dialog")).getByRole("alert")).toBeInTheDocument();
});

// --- U3: the rest of U7 code review (#6 #8 #10 #12 #15, C15 C19, §3 PlayerStrip, A3-14) -- //
describe("U7 review carry in U3", () => {
  it("#6: a write that ends after the region changed paints the new region's rumors", async () => {
    gmReads();
    (api.listRumors as Mock).mockImplementation(async (_s: string, rid: string) => [
      { id: `r-${rid}`, session_id: "s1", region_id: rid, distorted_from_id: "k", statement: `rumor of ${rid}`,
        distortion_degree: 0.3, support: 0.5, confidence: 0.5, promoted: false },
    ]);
    let finish: (v: unknown) => void = () => {};
    (api.setDistortion as Mock).mockReturnValue(new Promise((r) => (finish = r)));
    renderGm();
    await chooseRegion("a");
    await waitFor(() => expect(screen.getByText("rumor of a")).toBeInTheDocument());
    const slider = screen.getByTestId("distortion-slider");
    fireEvent.change(slider, { target: { value: "0.5" } });
    fireEvent.pointerUp(slider);
    fireEvent.click(screen.getByTestId("region-marker-b"));
    await waitFor(() => expect(screen.getByText("rumor of b")).toBeInTheDocument());
    const timelineReads = (api.getTimeline as Mock).mock.calls.length;
    await act(async () => finish({ session_id: "s1", region_id: "a", distortion_degree: 0.5, feedback_share: 0 }));
    await waitFor(() => expect((api.getTimeline as Mock).mock.calls.length).toBeGreaterThan(timelineReads)); // the write's re-read
    expect(screen.queryByText("rumor of a")).not.toBeInTheDocument();
    expect(screen.getByText("rumor of b")).toBeInTheDocument();
  });

  it("#8: the distortion label follows the thumb before the save", async () => {
    gmReads();
    renderGm();
    await chooseRegion("a");
    fireEvent.change(await screen.findByTestId("distortion-slider"), { target: { value: "0.7" } });
    expect(screen.getByTestId("distortion-label")).toHaveTextContent(numberWithMeaning("distortion", 0.7));
  });

  it("#15: the suggestion count goes up to the server's cap", async () => {
    gmReads();
    (api.getWorldState as Mock).mockResolvedValue(gmState({ max_event_suggestions: 8 }));
    renderGm();
    await waitFor(() => expect(screen.getByRole("option", { name: "8" })).toBeInTheDocument());
  });

  it("C15/C19: a mouse release alone does not save; a caller's handler still runs", async () => {
    const onCommit = vi.fn().mockResolvedValue(true);
    const onBlur = vi.fn();
    render(<CommitRange data-testid="r" min={0} max={1} step={0.1} value={0.2} onCommit={onCommit} onBlur={onBlur} />);
    const r = screen.getByTestId("r");
    fireEvent.change(r, { target: { value: "0.6" } });
    fireEvent.mouseUp(r);
    expect(onCommit).not.toHaveBeenCalled();
    fireEvent.blur(r);
    expect(onBlur).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(onCommit).toHaveBeenCalledWith(0.6));
  });

  it("§3: only a 404 means no player; another failure keeps the player and says so", async () => {
    gmReads();
    (api.getPlayer as Mock)
      .mockResolvedValueOnce({ id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 })
      .mockRejectedValueOnce(new HttpError(500, "Internal Server Error", "boom"));
    (api.listTurnRuns as Mock).mockResolvedValue([{ id: "run1" }]);
    renderGm();
    await waitFor(() => expect(screen.getByTestId("gm-player-status")).toHaveTextContent("Ari"));
    fireEvent.click(screen.getByTestId("gm-player-recheck")); // V6: the strip reads again on [check again]
    await waitFor(() => expect(screen.getByTestId("gm-player-error")).toBeInTheDocument());
    expect(screen.getByTestId("gm-player-status")).toHaveTextContent("Ari");
  });

  it("#10: an old flagged event line without a category reads its summary", () => {
    // the shapes written before U7: no category, and approval without a region
    expect(timelineText("event_created", { event_id: "e1", region_id: "r1", suggested: true }, 2,
      "suggested war event in r1")).toBe("suggested war event in r1");
    expect(timelineText("event_created", { event_id: "e1", approved: true }, 2, "approved event e1"))
      .toBe("approved event e1");
    expect(timelineText("event_created", { event_id: "e1", region_id: "r1", category: "war", suggested: true }, 2, "x"))
      .not.toBe("x"); // with a category the newer wording is used
  });

  it("A3-14: a region line written before regions were recorded reads its summary", () => {
    expect(timelineText("promote", { rumor_id: "rm1" }, 4, "promoted rm1")).toBe("promoted rm1");
    expect(timelineText("promote", { rumor_id: "rm1", region_name: "Riverton" }, 4, "x")).toContain("Riverton");
  });
});


// --------------------------------------------------------------------------- //
// U8 event seeds and the LLM-off hub (frontend-components §2.4–2.5, §5)
// --------------------------------------------------------------------------- //
describe("U8 seeds and LLM-off buttons", () => {
  const seed = (id: string, running?: string): SeedView => ({
    seed: { id, world_id: "w", region_id: "a", title: `Title ${id}`, description: "d", category: "plague", magnitude: 0.5 },
    region_name: "Ambermeadow",
    running_event_id: running ?? null,
  });
  beforeEach(() => {
    resetCapabilities();
    (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
    gmReads();
  });
  afterEach(() => resetCapabilities());

  it("lists the seeds; a running one says so, the other starts and the list is read again", async () => {
    (api.listSeeds as Mock).mockResolvedValue([seed("seed-a"), seed("seed-b", "ev-1")]);
    (api.startSeed as Mock).mockResolvedValue({ id: "ev-2" });
    renderGm();
    await openTab("seeds");
    const row = await screen.findByTestId("seed-row-seed-a");
    expect(row).toHaveTextContent("Title seed-a");
    expect(row).toHaveTextContent("Ambermeadow");
    expect(row).toHaveTextContent(enumLabel("eventCategory", "plague")); // V6: in words (FR-D8)
    expect(row).toHaveTextContent(numberWithMeaning("magnitude", 0.5));
    expect(screen.getByTestId("seed-running-seed-b")).toHaveTextContent(t("seed.running"));
    expect(screen.queryByTestId("seed-start-seed-b")).not.toBeInTheDocument();
    const reads = (api.listSeeds as Mock).mock.calls.length;
    await act(async () => fireEvent.click(screen.getByTestId("seed-start-seed-a")));
    expect(api.startSeed).toHaveBeenCalledWith("s1", "seed-a");
    await waitFor(() => expect((api.listSeeds as Mock).mock.calls.length).toBeGreaterThan(reads));
  });

  it("a refused start (409) is the screen's error line, in words with the detail folded", async () => {
    (api.listSeeds as Mock).mockResolvedValue([seed("seed-a")]);
    (api.startSeed as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"seed seed-a is already running","code":"seed_running"}'));
    renderGm();
    await openTab("seeds");
    await act(async () => fireEvent.click(await screen.findByTestId("seed-start-seed-a")));
    const line = await screen.findByTestId("gm-hub-error");
    expect(line).toHaveTextContent(t("error.seed_running.title"));
    expect(line.querySelector("details")).toHaveTextContent("already running");
  });

  it("a closed session cannot start a seed; no seeds is one line", async () => {
    (api.listSeeds as Mock).mockResolvedValue([seed("seed-a")]);
    (api.getSession as Mock).mockResolvedValue({ ...OPEN, status: "closed" });
    const { unmount } = renderGm();
    await openTab("seeds");
    expect(await screen.findByTestId("seed-start-seed-a")).toBeDisabled();
    unmount();
    gmReads();
    renderGm();
    await openTab("seeds");
    expect(await screen.findByTestId("seed-panel")).toHaveTextContent(t("empty.seeds"));
  });

  it("with no LLM the LLM buttons are off and say why; one notice on the screen; manual events stay on", async () => {
    (api.capabilities as Mock).mockResolvedValue({ llm: false, vlm: false, embedding: false });
    renderGm();
    await chooseRegion("a");
    await waitFor(() => expect(screen.getByTestId("suggest-events-btn")).toBeDisabled());
    for (const id of ["suggest-events-btn", "generate-all-btn", "regen-all-btn", "generate-btn", "regen-btn"]) {
      expect(screen.getByTestId(id)).toBeDisabled();
      expect(screen.getByTestId(id)).toHaveAttribute("title", t("llm.required"));
    }
    // V6 (BR-V6-23): the one notice is the app's band; no second line beside the buttons
    expect(screen.getAllByTestId("llm-notice")).toHaveLength(1);
    expect(screen.queryByTestId("llm-required")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: t("label.createEventHere") }));
    fireEvent.change(screen.getByTestId("event-description"), { target: { value: "Fire at the docks" } });
    expect(screen.getByTestId("event-create-btn")).toBeEnabled();
    expect(screen.getByTestId("advance-turn-btn")).toBeEnabled();
  });

  it("with an LLM (or an unknown answer) nothing is switched off", async () => {
    (api.capabilities as Mock).mockRejectedValue(new Error("down"));
    renderGm();
    await chooseRegion("a");
    await waitFor(() => expect(api.capabilities).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId("generate-btn")).toBeEnabled());
    expect(screen.getByTestId("suggest-events-btn")).toBeEnabled();
    expect(screen.queryByTestId("llm-notice")).not.toBeInTheDocument();
  });

  it("a 503 for a missing provider reads 'no AI key' (BR-U8-27, V6 describeError)", async () => {
    (api.generateRumors as Mock).mockRejectedValue(new HttpError(503, "Service Unavailable",
      '{"detail":"rumor generation needs an LLM provider (set OPENAI_API_KEY)","code":"llm_unavailable"}'));
    renderGm();
    await chooseRegion("a");
    await waitFor(() => expect(screen.getByTestId("generate-btn")).toBeEnabled());
    await act(async () => fireEvent.click(screen.getByTestId("generate-btn")));
    await waitFor(() => expect(screen.getByTestId("gm-hub-error")).toHaveTextContent(t("error.llm_unavailable.title")));
  });
});


// --------------------------------------------------------------------------- //
// U3 code-review-01, GM screen (U8 Step 11c): S13 S14
// --------------------------------------------------------------------------- //
describe("U3 review carry: the GM screen", () => {
  beforeEach(() => {
    resetCapabilities();
    (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
    gmReads();
  });
  afterEach(() => resetCapabilities());

  it("S13: a failed cap read on mount is corrected by the next state read", async () => {
    (api.getWorldState as Mock)
      .mockRejectedValueOnce(new Error("state down"))
      .mockResolvedValue({ session_id: "s1", turn: 3, player_region_id: null, max_event_suggestions: 8,
        regions: [{ region_id: "a", region_name: "a", distortion: 0.3, feedback_share: 0, active_rumors: 1,
          promoted_rumors: 0, deed_rumors: 0, active_events: 0 }] });
    renderGm();
    await waitFor(() => expect(api.getWorldState).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("option", { name: "8" })).not.toBeInTheDocument();
    await act(async () => fireEvent.click(screen.getByTestId("generate-all-btn")));
    await waitFor(() => expect(screen.getByRole("option", { name: "8" })).toBeInTheDocument());
  });

  it("S14: another session never shows the last session's player", async () => {
    (api.getSession as Mock).mockImplementation(async (sid: string) => ({ ...OPEN, id: sid }));
    (api.exportWorld as Mock).mockResolvedValue({ world_id: "w", regions: [{ id: "a", name: "Riverton", level: "town" }],
      connections: [], entities: [], knowledge: [], scopes: [] });
    (api.listSessions as Mock).mockResolvedValue([]);
    (api.listDeeds as Mock).mockResolvedValue([]);
    (api.listTurnRuns as Mock).mockResolvedValue([]);
    (api.getWorldState as Mock).mockResolvedValue({ session_id: "s1", turn: 3, player_region_id: null, regions: [] });
    (api.getPlayer as Mock).mockImplementation(async (sid: string) => {
      if (sid === "s1") return { id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 };
      throw new HttpError(500, "Server Error", "player read failed");
    });
    function Go() {
      const navigate = useNavigate();
      return <button data-testid="go-s2" onClick={() => navigate("/gm/s2")}>s2</button>;
    }
    render(
      <MemoryRouter initialEntries={["/gm/s1"]}>
        <Go />
        <Routes><Route path="/gm/:sessionId" element={<GmPage />} /></Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId("gm-player-status")).toHaveTextContent("Ari");
    expect(await screen.findByTestId("player-marker-a")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("go-s2"));
    await waitFor(() => expect(api.getPlayer).toHaveBeenCalledWith("s2"));
    await waitFor(() => expect(screen.queryByTestId("gm-player-status")).not.toBeInTheDocument());
    expect(screen.queryByTestId("player-marker-a")).not.toBeInTheDocument();
  });
});

describe("V6 shared base", () => {
  it("a bulk run that is told to stop sends no more regions (code plan § 1.1 R-06)", async () => {
    const sent: number[] = [];
    let stop = false;
    await mapLimit([1, 2, 3, 4, 5, 6, 7], 2, async (n) => {
      sent.push(n);
      if (n === 3) stop = true;
      return n;
    }, () => stop);
    // two workers: 1 and 2 start, then 3 and 4; after 3 asks to stop nothing new is taken
    expect(sent.length).toBeLessThanOrEqual(4);
    expect(sent).not.toContain(5);
    expect(await mapLimit([1, 2, 3], 5, async (n) => n * 2)).toEqual([2, 4, 6]);
  });

  it("an event whose region left the world reads so, with no region id (V5 → V6, BR-V6-29)", () => {
    const line = timelineText("event_resolved", { event_id: "e1", region_id: "r-gone", reason: "region_removed", restored: {} }, 4, "x");
    expect(line).toBe(t("timeline.event_resolved_removed"));
    expect(line).not.toContain("r-gone");
    expect(timelineText("event_resolved", { event_id: "e1", region_id: "r1", region_name: "Harbor" }, 4)).toContain("Harbor");
  });
});
