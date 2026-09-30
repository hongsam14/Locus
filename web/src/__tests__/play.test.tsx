// U4 player screen tests (Step 9.5): EX-13 load, EX-7 move -> 202 -> poll -> toast,
// 409 toast, EX-16 banner, TP-U4-2 blocked option, NewSessionForm (US-3.1).
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import { SessionBar } from "../SessionBar";
import { t } from "../i18n";
import { PlayPage } from "../routes/PlayPage";
import type { GameSession, RegionView, TurnRun } from "../types";

vi.mock("../api", () => ({
  api: {
    getSession: vi.fn(),
    getRegion: vi.fn(),
    getLog: vi.fn(),
    act: vi.fn(),
    getTurnRun: vi.fn(),
    listTurnRuns: vi.fn(),
    listSessions: vi.fn(),
    startSession: vi.fn(),
    closeSession: vi.fn(),
  },
}));

import { api } from "../api";

const SESSION: GameSession = { id: "s1", world_id: "w", status: "open", turn: 0 };

function view(over: Partial<RegionView> = {}): RegionView {
  return {
    session_id: "s1",
    turn: 0,
    player: { id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 },
    region_id: "a",
    region_name: "Riverton",
    level: "town",
    description: "A quiet river town.",
    level_path: ["Aldermoor", "Riverton"],
    npcs: [
      {
        id: "n1", world_id: "w", name: "Mara", role: "innkeeper", description: "", home_region_id: "a",
        traits: [], provenance: { source: "input" },
      },
    ],
    facts: [
      { knowledge_id: "k1", statement: "The mill burned.", scope_type: "direct", is_hearsay: false, confidence: 0.9 },
    ],
    hearsay: [
      { knowledge_id: "k9", statement: "Wolves in the pass.", scope_type: "hearsay", is_hearsay: true, confidence: 0.4, path_decay: 0.6 },
    ],
    rumors: [
      {
        id: "ru1", session_id: "s1", region_id: "a", distorted_from_id: "k1", distorted_from_kind: "knowledge",
        statement: "The mill was cursed.", distortion_degree: 0.3, support: 0.5, confidence: 0.6, promoted: true,
      },
    ],
    moves: [
      { region_id: "b", region_name: "Hollow", kind: "route", weight: 0.5, cost_turns: 2, passable: true },
      { region_id: "c", region_name: "Crag", kind: "blocked", weight: 0, cost_turns: 0, passable: false, reason: "blocked pass" },
    ],
    turn_running: false,
    llm_available: true,
    ...over,
  };
}

function renderPlay(path = "/play/s1") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/play/:sessionId?" element={<PlayPage pollMs={5} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PlayPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getSession as Mock).mockResolvedValue(SESSION);
    (api.getRegion as Mock).mockResolvedValue(view());
    (api.getLog as Mock).mockResolvedValue([
      { id: "t1", session_id: "s1", turn: 0, kind: "session_started", summary: "", payload: { player_name: "Ari", region_name: "Riverton" } },
    ]);
    (api.listTurnRuns as Mock).mockResolvedValue([]);
  });

  it("EX-13: shows the region, its people, what is known/heard/rumoured and the moves", async () => {
    renderPlay();
    await waitFor(() => expect(screen.getByTestId("region-scene")).toBeInTheDocument());
    expect(screen.getByTestId("region-title")).toHaveTextContent("Riverton");
    expect(screen.getByTestId("region-path")).toHaveTextContent("Aldermoor › Riverton");
    expect(screen.getByTestId("npc-n1")).toHaveTextContent("Mara");
    expect(screen.getByTestId("knowledge-item-k1")).toHaveTextContent("The mill burned.");
    expect(screen.getByTestId("hearsay-item-k9")).toHaveTextContent("Wolves in the pass.");
    expect(screen.getByTestId("rumor-ru1")).toHaveTextContent(t("gm.promoted"));
    expect(screen.getByTestId("move-b")).toHaveTextContent(t("play.turns", { n: 2 }));
    expect(screen.getByTestId("move-c-blocked")).toHaveTextContent(t("play.blocked"));
    expect(screen.getByTestId("move-c-btn")).toBeDisabled(); // TP-U4-2 (UI)
    expect(screen.getByTestId("move-b-btn")).toBeEnabled();
    expect(screen.queryByTestId("llm-banner")).not.toBeInTheDocument();
    expect(screen.getByTestId("log-session_started")).toHaveTextContent(
      t("timeline.session_started", { player_name: "Ari", region_name: "Riverton" }),
    );
  });

  it("EX-7: a move answers 202, refreshes the region at once, polls to done and notifies", async () => {
    const running: TurnRun = {
      id: "run1", session_id: "s1", action: { type: "move", to_region_id: "b" }, cost_turns: 2,
      status: "running", started_turn: 0,
    };
    const done: TurnRun = {
      ...running,
      status: "done",
      result: {
        session: { ...SESSION, turn: 2 },
        player: { id: "p1", session_id: "s1", name: "Ari", region_id: "b", turns_spent: 2 },
        turns: [],
        changes: [{ region_id: "b", region_name: "Hollow", promoted: ["x"], demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: ["y", "z"] }],
        narration: ["Hollow: 2 new rumors, 1 promoted"],
        llm_calls: 2, budget_exhausted: true, llm_failed: false, llm_available: true,
      },
    };
    (api.act as Mock).mockResolvedValue(running);
    (api.getTurnRun as Mock).mockResolvedValueOnce(running).mockResolvedValue(done);
    (api.getRegion as Mock)
      .mockResolvedValueOnce(view())
      .mockResolvedValue(view({ region_id: "b", region_name: "Hollow", turn: 2, level_path: ["Aldermoor", "Hollow"] }));
    renderPlay();
    await waitFor(() => expect(screen.getByTestId("move-b-btn")).toBeEnabled());
    fireEvent.click(screen.getByTestId("move-b-btn"));
    await waitFor(() => expect(api.act).toHaveBeenCalledWith("s1", { type: "move", to_region_id: "b" }));
    await waitFor(() => expect(screen.getByTestId("region-title")).toHaveTextContent("Hollow")); // arrived at once
    expect(screen.getByTestId("turn-progress")).toHaveTextContent(t("play.running", { n: 2 }));
    await waitFor(() => expect(screen.getByTestId("notification-center")).toBeInTheDocument());
    expect(screen.getByTestId("notification-center")).toHaveTextContent("Hollow");
    expect(screen.getByTestId("notification-center")).toHaveTextContent(t("notif.rumors_added", { n: 2 }));
    expect(screen.getByTestId("notification-center")).toHaveTextContent(t("play.budget"));
    await waitFor(() => expect(screen.queryByTestId("turn-progress")).not.toBeInTheDocument());
    expect((api.getLog as Mock).mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  it("409 while a turn is in progress shows the in-progress toast, not an error", async () => {
    (api.act as Mock).mockRejectedValue(new Error('409 Conflict: {"detail":"turn in progress"}'));
    renderPlay();
    await waitFor(() => expect(screen.getByTestId("wait-btn")).toBeEnabled());
    fireEvent.click(screen.getByTestId("wait-btn"));
    await waitFor(() => expect(screen.getByTestId("notification-center")).toHaveTextContent(t("play.turnInProgress")));
    expect(screen.queryByTestId("play-error")).not.toBeInTheDocument();
  });

  it("EX-16: shows the LLM banner and still offers moves without a provider", async () => {
    (api.getRegion as Mock).mockResolvedValue(view({ llm_available: false }));
    renderPlay();
    await waitFor(() => expect(screen.getByTestId("llm-banner")).toBeInTheDocument());
    expect(screen.getByTestId("move-b-btn")).toBeEnabled();
  });

  it("U4-2 #15: a failed poll re-enables the actions instead of latching them off", async () => {
    const running: TurnRun = {
      id: "r1", session_id: "s1", action: { type: "wait" }, cost_turns: 1,
      status: "running", started_turn: 0,
    };
    (api.act as Mock).mockResolvedValue(running);
    (api.getTurnRun as Mock).mockRejectedValue(new Error("502 Bad Gateway"));
    // two refreshes on mount, then the one right after the 202 sees the guard held
    (api.getRegion as Mock)
      .mockResolvedValueOnce(view())
      .mockResolvedValueOnce(view())
      .mockResolvedValueOnce(view({ turn_running: true }))
      .mockResolvedValue(view({ turn_running: false }));
    renderPlay();
    await waitFor(() => expect(screen.getByTestId("wait-btn")).toBeEnabled());
    fireEvent.click(screen.getByTestId("wait-btn"));
    await waitFor(() => expect(screen.getByTestId("play-error")).toBeInTheDocument());
    // the poll's failure path refreshes, so turn_running clears and the button returns
    await waitFor(() => expect(screen.getByTestId("wait-btn")).toBeEnabled());
    expect(screen.getByTestId("move-b-btn")).toBeEnabled();
  });

  it("resumes polling a run that is still in flight after a reload", async () => {
    const running: TurnRun = { id: "r9", session_id: "s1", action: { type: "wait" }, cost_turns: 1, status: "running", started_turn: 0 };
    (api.listTurnRuns as Mock).mockResolvedValue([running]);
    (api.getTurnRun as Mock).mockResolvedValue({ ...running, status: "failed", error: "turn processing failed" });
    renderPlay();
    await waitFor(() => expect(screen.getByTestId("notification-center")).toHaveTextContent(t("play.runFailed")));
  });
});

describe("SessionBar player start (US-3.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.listSessions as Mock).mockResolvedValue([]);
  });

  it("opens the form, requires a name and a region, and hands the session to onPlay", async () => {
    (api.startSession as Mock).mockResolvedValue({
      session: { ...SESSION, id: "s2" },
      player: { id: "p2", session_id: "s2", name: "Ari", region_id: "a", turns_spent: 0 },
    });
    const onPlay = vi.fn();
    const onSelect = vi.fn();
    render(
      <SessionBar
        worldId="w"
        sessionId={null}
        onSelect={onSelect}
        variant="picker"
        regions={[{ id: "a", name: "Riverton", level: "town" }]}
        onPlay={onPlay}
      />,
    );
    expect(screen.getByTestId("session-new-btn")).toBeInTheDocument(); // GM button untouched
    fireEvent.click(screen.getByTestId("session-play-btn"));
    expect(screen.getByTestId("new-session-submit")).toBeDisabled();
    fireEvent.change(screen.getByTestId("new-session-name"), { target: { value: "Ari" } });
    expect(screen.getByTestId("new-session-submit")).toBeDisabled(); // region still missing
    fireEvent.change(screen.getByTestId("new-session-region"), { target: { value: "a" } });
    expect(screen.getByTestId("new-session-submit")).toBeEnabled();
    fireEvent.click(screen.getByTestId("new-session-submit"));
    await waitFor(() =>
      expect(api.startSession).toHaveBeenCalledWith("w", { name: "Ari", start_region_id: "a" }),
    );
    await waitFor(() => expect(onPlay).toHaveBeenCalledWith(expect.objectContaining({ session: expect.objectContaining({ id: "s2" }) })));
    expect(onSelect).not.toHaveBeenCalledWith(expect.objectContaining({ id: "s2" }));
  });

  it("hides the play button when no onPlay handler is given (GM screen)", () => {
    render(<SessionBar worldId="w" sessionId={null} onSelect={vi.fn()} />);
    expect(screen.queryByTestId("session-play-btn")).not.toBeInTheDocument();
  });
});
