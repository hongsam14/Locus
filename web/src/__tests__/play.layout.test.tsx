// V4 play screen (FD frontend-components § 1 and § 3, BLM § 2, R-11): one place per part at
// each width, the talk in the column (wide) or a sheet that the router's history holds,
// one result band, the closed / empty / GM-at-work states, no other session's data.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import type { Mock } from "vitest";
import { resetCapabilities } from "../capabilities";
import { configureLangs, setLang, t } from "../i18n";
import { HttpError } from "../api/http";
import { PlayPage } from "../routes/PlayPage";
import type { GameSession, NPC, RegionView, TurnRun } from "../types";
import { clearToasts } from "../ui";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn(),
    getSession: vi.fn(),
    getRegion: vi.fn(),
    getLog: vi.fn(),
    act: vi.fn(),
    getTurnRun: vi.fn(),
    listTurnRuns: vi.fn(),
    listNpcs: vi.fn(),
    startDialogue: vi.fn(),
    dialogueHistory: vi.fn(),
    say: vi.fn(),
    worldNames: vi.fn(),
    exportWorld: vi.fn(),
  },
}));
import { api } from "../api";

// ---- widths: a matchMedia stand-in the screen subscribes to ----------------------------- //
let width = 800;
const lists: { list: { matches: boolean }; fns: Set<(e: { matches: boolean }) => void> }[] = [];
function matchMedia(q: string) {
  const min = /min-width:\s*(\d+)px/.exec(q);
  const max = /max-width:\s*(\d+)px/.exec(q);
  const fns = new Set<(e: { matches: boolean }) => void>();
  const list = {
    media: q,
    get matches() {
      return (!min || width >= Number(min[1])) && (!max || width <= Number(max[1]));
    },
    addEventListener: (_: string, f: (e: { matches: boolean }) => void) => fns.add(f),
    removeEventListener: (_: string, f: (e: { matches: boolean }) => void) => fns.delete(f),
  };
  lists.push({ list, fns });
  return list;
}
function resize(w: number) {
  width = w;
  act(() => {
    for (const { list, fns } of lists) for (const f of fns) f({ matches: list.matches });
  });
}

// ---- data ------------------------------------------------------------------------------ //
const MARA: NPC = {
  id: "n1", world_id: "w", name: "Mara", role: "innkeeper", description: "", home_region_id: "a",
  traits: [], provenance: { source: "input" },
};
const session = (id: string, status: GameSession["status"] = "open"): GameSession => ({ id, world_id: "w", status, turn: 3 });
function view(over: Partial<RegionView> = {}): RegionView {
  return {
    session_id: "s1", turn: 3, player: { id: "p", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 3 },
    region_id: "a", region_name: "Riverton", level: "town", description: "A river town.",
    level_path: ["Aldermoor", "Riverton"], level_path_ids: ["top", "a"], npcs: [MARA],
    facts: [{ knowledge_id: "k1", statement: "The mill burned.", scope_type: "direct", is_hearsay: false, confidence: 0.9 }],
    hearsay: [], rumors: [],
    moves: [
      { region_id: "b", region_name: "Hollow", kind: "route", weight: 0.5, cost_turns: 1, passable: true },
      { region_id: "c", region_name: "Crag", kind: "blocked", weight: 0, cost_turns: 0, passable: false },
    ],
    turn_running: false, llm_available: true, ...over,
  };
}
const AWAY = view({ region_id: "b", region_name: "Hollow", npcs: [], level_path: ["Aldermoor", "Hollow"], level_path_ids: ["top", "b"] });
const run = (status: TurnRun["status"], result?: TurnRun["result"]): TurnRun =>
  ({ id: "run1", session_id: "s1", action: { type: "wait" }, cost_turns: 1, status, started_turn: 3, result });
const done = (over: Partial<NonNullable<TurnRun["result"]>> = {}) =>
  run("done", {
    session: session("s1"), player: null, turns: [], narration: [], llm_calls: 0, llm_available: true,
    budget_exhausted: false, llm_failed: false, changes: [], ...over,
  } as TurnRun["result"]);

// ---- page and a probe of the router ---------------------------------------------------- //
function Probe() {
  const loc = useLocation();
  const nav = useNavigate();
  return (
    <div>
      <span data-testid="probe-path">{loc.pathname}</span>
      <span data-testid="probe-state">{JSON.stringify(loc.state ?? null)}</span>
      <button data-testid="probe-back" onClick={() => nav(-1)}>back</button>
      <button data-testid="probe-s2" onClick={() => nav("/play/s2")}>s2</button>
    </div>
  );
}
type Entry = string | { pathname: string; state?: unknown };
function renderPlay(entries: Entry[] = ["/", "/play/s1"]) {
  return render(
    <MemoryRouter initialEntries={entries} initialIndex={entries.length - 1}>
      <Routes>
        <Route path="/play/:sessionId?" element={<PlayPage pollMs={1} heldRetryMs={5} />} />
        <Route path="*" element={<div data-testid="elsewhere" />} />
      </Routes>
      <Probe />
    </MemoryRouter>,
  );
}
const path = () => screen.getByTestId("probe-path").textContent;
const routerState = () => JSON.parse(screen.getByTestId("probe-state").textContent ?? "null");

beforeEach(() => {
  for (const m of Object.values(api)) (m as Mock).mockReset();
  resetCapabilities();
  (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
  (api.getSession as Mock).mockImplementation(async (sid: string) => session(sid));
  (api.getRegion as Mock).mockResolvedValue(view());
  (api.getLog as Mock).mockResolvedValue([]);
  (api.listTurnRuns as Mock).mockResolvedValue([]);
  (api.listNpcs as Mock).mockResolvedValue([{ npc: MARA, has_conversation: false, message_count: 0 }]);
  (api.startDialogue as Mock).mockResolvedValue({ id: "c1", session_id: "s1", npc_id: "n1", started_turn: 3, messages: [] });
  (api.worldNames as Mock).mockResolvedValue({ world_id: "w", lang: "ko", world: {}, regions: {}, npcs: {}, event_seeds: {} });
  (api.exportWorld as Mock).mockResolvedValue({
    world_id: "w", entities: [], knowledge: [], scopes: [], connections: [],
    regions: [
      { id: "a", name: "Riverton", level: "town", position: { x: 0.4, y: 0.4 } },
      { id: "b", name: "Hollow", level: "town", position: { x: 0.6, y: 0.4 } },
      { id: "c", name: "Crag", level: "town", position: { x: 0.5, y: 0.6 } },
    ],
  });
  width = 800; // the middle layout unless a test says otherwise
  lists.length = 0;
  vi.stubGlobal("matchMedia", matchMedia);
});
afterEach(() => {
  vi.unstubAllGlobals();
  clearToasts();
});

const ONCE = ["declare-input", "move-b-btn", "dialogue-panel", "region-title", "play-map", "action-bar", "action-dock"];
function atMostOnce() {
  for (const id of ONCE) expect(screen.queryAllByTestId(id).length, id).toBeLessThanOrEqual(1);
}

describe("TP-V4-8: three widths", () => {
  it("wide: two columns; the talk takes the people's place and adds no history", async () => {
    width = 1280;
    renderPlay();
    await screen.findByTestId("region-title");
    expect(screen.getByTestId("action-bar")).toBeInTheDocument();
    expect(screen.queryByTestId("action-dock")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-map").closest("aside")).not.toBeNull();
    expect(screen.getByTestId("move-panel").closest("aside")).not.toBeNull();
    fireEvent.click(screen.getByTestId("npc-n1-talk-btn"));
    const panel = await screen.findByTestId("dialogue-panel");
    expect(panel.closest("[role=dialog]")).toBeNull(); // in the column, not a sheet
    expect(screen.queryByTestId("people-here")).not.toBeInTheDocument();
    expect(routerState()).toBeNull();
    atMostOnce();
    fireEvent.click(screen.getByTestId("probe-back")); // no entry was pushed: back leaves
    expect(path()).toBe("/");
  });

  it("middle: the action box in the page, the talk in a full sheet", async () => {
    width = 800;
    renderPlay();
    await screen.findByTestId("region-title");
    expect(screen.getByTestId("action-bar")).toBeInTheDocument();
    expect(screen.queryByTestId("action-dock")).not.toBeInTheDocument();
    expect(screen.getByTestId("move-panel").closest("aside")).toBeNull();
    fireEvent.click(screen.getByTestId("npc-n1-talk-btn"));
    expect(await screen.findByTestId("talk-sheet")).toHaveAttribute("data-variant", "full");
    expect(within(screen.getByTestId("talk-sheet")).getByTestId("dialogue-panel")).toBeInTheDocument();
    atMostOnce();
  });

  it("narrow: the dock, its sheets, and back closes the talk sheet without leaving", async () => {
    width = 390;
    renderPlay();
    await screen.findByTestId("region-title");
    expect(screen.getByTestId("action-dock")).toBeInTheDocument();
    expect(screen.queryByTestId("action-bar")).not.toBeInTheDocument();
    expect(screen.queryByTestId("move-panel")).not.toBeInTheDocument(); // only in its sheet
    expect(screen.queryByTestId("declare-input")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("dock-move"));
    expect(within(screen.getByTestId("move-sheet")).getByTestId("move-b-btn")).toBeInTheDocument();
    fireEvent.keyDown(screen.getByTestId("move-sheet"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByTestId("move-sheet")).not.toBeInTheDocument());
    fireEvent.click(screen.getByTestId("dock-declare"));
    expect(within(screen.getByTestId("declare-sheet")).getByTestId("declare-input")).toBeInTheDocument();
    atMostOnce();
    fireEvent.keyDown(screen.getByTestId("declare-sheet"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByTestId("declare-sheet")).not.toBeInTheDocument());
    fireEvent.click(screen.getByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    expect(routerState()).toEqual({ talk: { sessionId: "s1", regionId: "a", npcId: "n1" } });
    atMostOnce();
    fireEvent.click(screen.getByTestId("probe-back"));
    await waitFor(() => expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument());
    expect(path()).toBe("/play/s1"); // back closed the sheet and stayed
  });

  it("narrow: a press on the small map opens the move sheet at that row, moving no one", async () => {
    width = 390;
    renderPlay();
    await screen.findByTestId("play-map");
    fireEvent.click(await screen.findByTestId("region-marker-b"));
    expect(within(screen.getByTestId("move-sheet")).getByTestId("move-b")).toHaveAttribute("data-highlight", "true");
    expect(api.act).not.toHaveBeenCalled();
  });

  it("[close] and Esc close the talk sheet; the history entry goes with it", async () => {
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    fireEvent.click(screen.getByTestId("dialogue-close-btn"));
    await waitFor(() => expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument());
    expect(routerState()).toBeNull();
    fireEvent.click(screen.getByTestId("probe-back")); // the talk's entry was popped: back leaves
    expect(path()).toBe("/");
  });
});

describe("R-11: the talk's history entry", () => {
  it("moving away clears the entry in place and the sheet does not come back", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValue(done());
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    (api.getRegion as Mock).mockResolvedValue(AWAY);
    fireEvent.click(screen.getByTestId("move-b-btn"));
    await waitFor(() => expect(screen.getByTestId("region-title")).toHaveTextContent("Hollow"));
    await waitFor(() => expect(routerState()).toBeNull());
    expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument();
  });

  it("a state naming another session or place opens nothing", async () => {
    renderPlay(["/", { pathname: "/play/s1", state: { talk: { sessionId: "s9", regionId: "a", npcId: "n1" } } }]);
    await screen.findByTestId("region-title");
    expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument();
  });

  it("a restored entry of ours opens the sheet; closing it stays on the page", async () => {
    renderPlay(["/", { pathname: "/play/s1", state: { talk: { sessionId: "s1", regionId: "a", npcId: "n1" } } }]);
    await screen.findByTestId("talk-sheet");
    fireEvent.click(screen.getByTestId("dialogue-close-btn"));
    await waitFor(() => expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument());
    expect(path()).toBe("/play/s1"); // not popped to "/": this screen did not push it
  });

  it("leaving with the sheet open goes where it was sent; nothing pulls it back", async () => {
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    fireEvent.click(screen.getByTestId("nav-home"));
    await screen.findByTestId("elsewhere");
    await new Promise((r) => setTimeout(r, 20));
    expect(path()).toBe("/");
  });

  it("another session closes the sheet and starts clean", async () => {
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    fireEvent.click(screen.getByTestId("probe-s2"));
    await waitFor(() => expect(api.getSession).toHaveBeenCalledWith("s2"));
    expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument();
  });

  it("a width change carries the talk across: sheet → column → sheet", async () => {
    width = 800;
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    resize(1280);
    await waitFor(() => expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument());
    expect(screen.getByTestId("dialogue-panel").closest("[role=dialog]")).toBeNull();
    expect(routerState()).toBeNull();
    resize(390);
    expect(await screen.findByTestId("talk-sheet")).toBeInTheDocument();
    expect(routerState()).toEqual({ talk: { sessionId: "s1", regionId: "a", npcId: "n1" } });
    atMostOnce();
  });
});

describe("TP-V4-5 and BR-V4-22: one result band", () => {
  // code review 01 #16: the band empties when the next turn starts (its 202), so a refused
  // action keeps the last result
  it("the result is in the band only; the next turn empties it, a refusal keeps it; [close] folds it", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValue(done({
      session: { ...session("s1"), turn: 4 },
      changes: [{ region_id: "a", region_name: "Riverton", promoted: [], demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: ["r"] }],
    }));
    renderPlay();
    await screen.findByTestId("region-title");
    fireEvent.click(screen.getByTestId("wait-btn"));
    const band = await screen.findByTestId("result-band");
    expect(band).toHaveTextContent(t("story.turnPassed", { n: 4 }));
    expect(screen.getByTestId("notification-center")).not.toHaveTextContent(t("notif.rumors_added", { n: 1 }));
    await waitFor(() => expect(screen.getByTestId("wait-btn")).not.toHaveAttribute("aria-disabled"));
    (api.act as Mock).mockRejectedValueOnce(new HttpError(400, "Bad Request", '{"detail":"no"}'));
    fireEvent.click(screen.getByTestId("wait-btn"));
    expect(await screen.findByTestId("action-error")).toBeInTheDocument();
    expect(screen.getByTestId("result-band")).toBeInTheDocument(); // a refusal keeps the last result
    let answer: (r: TurnRun) => void = () => {};
    let finish: (r: TurnRun) => void = () => {};
    (api.act as Mock).mockReturnValueOnce(new Promise<TurnRun>((r) => (answer = r)));
    (api.getTurnRun as Mock).mockReturnValueOnce(new Promise<TurnRun>((r) => (finish = r)));
    fireEvent.click(screen.getByTestId("wait-btn"));
    expect(screen.getByTestId("result-band")).toBeInTheDocument(); // still there before the 202
    await act(async () => answer(run("running")));
    expect(screen.queryByTestId("result-band")).not.toBeInTheDocument(); // the next turn empties it
    await act(async () => finish(done()));
    await screen.findByTestId("result-band");
    fireEvent.click(screen.getByTestId("result-band-close"));
    expect(screen.queryByTestId("result-band")).not.toBeInTheDocument();
  });

  it("[end talk] closes the talk and its judgment lands in the band", async () => {
    width = 1280;
    (api.act as Mock).mockResolvedValue({ ...run("running"), action: { type: "end_talk", npc_id: "n1" } });
    (api.getTurnRun as Mock).mockResolvedValue(done({
      changes: [{ region_id: "a", region_name: "Riverton", promoted: [], demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: ["deed"] }],
    }));
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("dialogue-panel");
    fireEvent.click(screen.getByTestId("dialogue-end-btn"));
    await waitFor(() => expect(api.act).toHaveBeenCalledWith("s1", { type: "end_talk", npc_id: "n1" }));
    expect(screen.queryByTestId("dialogue-panel")).not.toBeInTheDocument();
    expect(await screen.findByTestId("result-change-a")).toHaveTextContent(t("notif.rumors_added", { n: 1 }));
  });
});

describe("TP-V4-11: closed, empty, the GM at work", () => {
  it("a closed session: the line, [home], and the actions off; the history still reads", async () => {
    (api.getSession as Mock).mockResolvedValue(session("s1", "closed"));
    (api.dialogueHistory as Mock).mockResolvedValue({ id: "c1", session_id: "s1", npc_id: "n1", started_turn: 3, messages: [] });
    renderPlay();
    expect(await screen.findByTestId("closed-banner")).toHaveTextContent(t("notice.sessionClosed"));
    expect(screen.getByTestId("play-home-link")).toHaveAttribute("href", "/");
    expect(screen.getByTestId("wait-btn")).toBeDisabled();
    expect(screen.getByTestId("declare-input")).toBeDisabled();
    expect(screen.getByTestId("move-b-btn")).toBeDisabled();
    fireEvent.click(screen.getByTestId("npc-n1-talk-btn"));
    await waitFor(() => expect(api.dialogueHistory).toHaveBeenCalled());
    expect(screen.getByTestId("dialogue-input")).toBeDisabled();
  });

  it("/play without a session says so and points home, reading nothing", async () => {
    renderPlay(["/play"]);
    expect(screen.getByTestId("play-empty")).toHaveTextContent(t("empty.noSession"));
    expect(screen.getByTestId("play-home-link")).toHaveAttribute("href", "/");
    expect(api.getSession).not.toHaveBeenCalled();
  });

  it("the GM at work: the notice, the actions held, read again 1 s × 5 at most", async () => {
    (api.getRegion as Mock).mockResolvedValue(view({ gm_busy: true }));
    renderPlay();
    expect(await screen.findByTestId("gm-busy-notice")).toHaveTextContent(t("notice.gmBusy"));
    expect(screen.getByTestId("wait-btn")).toHaveAttribute("aria-disabled", "true");
    await waitFor(() => expect(api.getRegion).toHaveBeenCalledTimes(6));
    await new Promise((r) => setTimeout(r, 40));
    expect(api.getRegion).toHaveBeenCalledTimes(6);
  });

  it("code review 01 #1: a hold with no run of ours says so, and past the cap offers [check again]", async () => {
    (api.getRegion as Mock).mockResolvedValue(view({ turn_running: true }));
    renderPlay();
    expect(await screen.findByTestId("turn-held")).toHaveTextContent(t("notice.sessionHeld"));
    expect(screen.getByTestId("wait-btn")).toHaveAttribute("aria-disabled", "true");
    await waitFor(() => expect(api.getRegion).toHaveBeenCalledTimes(6)); // mount + 5
    const again = await screen.findByTestId("held-recheck");
    (api.getRegion as Mock).mockResolvedValue(view());
    fireEvent.click(again);
    await waitFor(() => expect(screen.getByTestId("wait-btn")).not.toHaveAttribute("aria-disabled"));
    expect(screen.queryByTestId("turn-held")).not.toBeInTheDocument();
  });

  it("code review 01 #3: a double press on [wait] sends one action", async () => {
    let answer: (r: TurnRun) => void = () => {};
    (api.act as Mock).mockReturnValue(new Promise<TurnRun>((r) => (answer = r)));
    (api.getTurnRun as Mock).mockResolvedValue(done());
    renderPlay();
    await screen.findByTestId("region-title");
    fireEvent.click(screen.getByTestId("wait-btn"));
    fireEvent.click(screen.getByTestId("wait-btn"));
    expect(screen.getByTestId("wait-btn")).toHaveAttribute("aria-disabled", "true");
    await act(async () => answer(run("running")));
    expect(api.act).toHaveBeenCalledTimes(1);
  });

  // code review 01 #28 (a): the past talk opens without a key; only a new line needs one
  it("without an AI key [talk] opens the past talk with the input locked", async () => {
    (api.getRegion as Mock).mockResolvedValue(view({ llm_available: false }));
    renderPlay();
    expect(await screen.findByTestId("talk-note")).toHaveTextContent(t("notice.talkNeedsKey"));
    fireEvent.click(screen.getByTestId("npc-n1-talk-btn"));
    expect(await screen.findByTestId("dialogue-no-llm")).toBeInTheDocument();
    expect(screen.getByTestId("dialogue-input")).toBeDisabled();
  });
});

describe("TP-V4-10: no other session's data", () => {
  it("while the next session reads, the last one's place is not shown", async () => {
    renderPlay();
    await waitFor(() => expect(screen.getByTestId("region-title")).toHaveTextContent("Riverton"));
    let answer: (v: RegionView) => void = () => {};
    (api.getRegion as Mock).mockImplementation(() => new Promise<RegionView>((r) => (answer = r)));
    fireEvent.click(screen.getByTestId("probe-s2"));
    await waitFor(() => expect(api.getSession).toHaveBeenCalledWith("s2"));
    expect(screen.queryByTestId("region-title")).not.toBeInTheDocument();
    expect(screen.getByTestId("status-loading")).toBeInTheDocument();
    await act(async () => answer({ ...AWAY, session_id: "s2" }));
    expect(await screen.findByTestId("region-title")).toHaveTextContent("Hollow");
  });
});

describe("code review 01: the talk and focus", () => {
  it("#6: the talk sheet opens on [close], never on [end talk], then moves to the input", async () => {
    let start: (c: unknown) => void = () => {};
    (api.startDialogue as Mock).mockReturnValue(new Promise((r) => (start = r)));
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    await waitFor(() => expect(screen.getByTestId("dialogue-close-btn")).toHaveFocus());
    expect(screen.getByTestId("dialogue-end-btn")).not.toHaveFocus();
    await act(async () => start({ id: "c1", session_id: "s1", npc_id: "n1", started_turn: 3, messages: [] }));
    await waitFor(() => expect(screen.getByTestId("dialogue-input")).toHaveFocus());
  });

  it("#6: the move sheet takes focus itself, not its first [move]", async () => {
    width = 390;
    renderPlay();
    fireEvent.click(await screen.findByTestId("dock-move"));
    const sheet = await screen.findByTestId("move-sheet");
    await waitFor(() => expect(sheet).toHaveFocus());
  });

  it("#7: a column talk takes focus and gives it back to [talk] when it closes", async () => {
    width = 1280;
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await waitFor(() => expect(screen.getByTestId("dialogue-input")).toHaveFocus());
    fireEvent.click(screen.getByTestId("dialogue-close-btn"));
    await waitFor(() => expect(screen.getByTestId("npc-n1-talk-btn")).toHaveFocus());
  });

  it("#11: the NPC leaving the region closes the talk (wide and narrower)", async () => {
    width = 1280;
    const { unmount } = renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("dialogue-panel");
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValue(done());
    (api.getRegion as Mock).mockResolvedValue(view({ npcs: [] }));
    fireEvent.click(screen.getByTestId("wait-btn")); // any re-read; the place is the same
    await waitFor(() => expect(screen.queryByTestId("dialogue-panel")).not.toBeInTheDocument());
    unmount();
  });

  it("#11: a restored entry naming an NPC who is not here is cleared, staying on the page", async () => {
    renderPlay(["/", { pathname: "/play/s1", state: { talk: { sessionId: "s1", regionId: "a", npcId: "gone" } } }]);
    await screen.findByTestId("region-title");
    await waitFor(() => expect(routerState()).toBeNull());
    expect(path()).toBe("/play/s1");
  });

  it("#12: moving with the sheet open pops the talk's entry: one back leaves", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValue(done());
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    (api.getRegion as Mock).mockResolvedValue(AWAY);
    fireEvent.click(screen.getByTestId("move-b-btn"));
    await waitFor(() => expect(screen.getByTestId("region-title")).toHaveTextContent("Hollow"));
    await waitFor(() => expect(routerState()).toBeNull());
    fireEvent.click(screen.getByTestId("probe-back"));
    expect(path()).toBe("/");
  });

  it("#12: width round trips with a talk open leave no extra entries", async () => {
    width = 800;
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("talk-sheet");
    for (let i = 0; i < 3; i++) {
      resize(1280);
      await waitFor(() => expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument());
      resize(800);
      await screen.findByTestId("talk-sheet");
    }
    fireEvent.click(screen.getByTestId("dialogue-close-btn"));
    await waitFor(() => expect(screen.queryByTestId("talk-sheet")).not.toBeInTheDocument());
    fireEvent.click(screen.getByTestId("probe-back"));
    expect(path()).toBe("/");
  });

  it("#13: a refused [end talk] keeps the talk open", async () => {
    width = 1280;
    (api.act as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"a turn is running","code":"turn_running"}'));
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await screen.findByTestId("dialogue-panel");
    fireEvent.click(screen.getByTestId("dialogue-end-btn"));
    await waitFor(() => expect(api.act).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId("notification-center")).toHaveTextContent(t("play.turnInProgress")));
    expect(screen.getByTestId("dialogue-panel")).toBeInTheDocument();
  });

  it("#19: the people's counts are read again after a turn, and a line that lands after closing counts", async () => {
    width = 1280;
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValue(done());
    let reply: (v: unknown) => void = () => {};
    (api.say as Mock).mockReturnValue(new Promise((r) => (reply = r)));
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    await waitFor(() => expect(screen.getByTestId("dialogue-input")).toBeEnabled());
    fireEvent.change(screen.getByTestId("dialogue-input"), { target: { value: "hello" } });
    fireEvent.click(screen.getByTestId("dialogue-send-btn"));
    fireEvent.click(screen.getByTestId("dialogue-close-btn")); // closed while the line is out
    await act(async () => reply({ message: { id: "m2", conversation_id: "c1", role: "npc", text: "Hm.", lang: "ko", turn: 3 }, lang: "ko", llm_calls: 1, context_ids: [] }));
    expect(await screen.findByTestId("npc-n1-talked")).toHaveTextContent(t("dialogue.has", { n: 2 }));
    const reads = (api.listNpcs as Mock).mock.calls.length;
    fireEvent.click(screen.getByTestId("wait-btn"));
    await screen.findByTestId("result-live");
    await waitFor(() => expect((api.listNpcs as Mock).mock.calls.length).toBe(reads + 1));
  });

  it("#20: a failed read after a language switch is not a move: the column talk comes back with the data", async () => {
    width = 1280;
    act(() => configureLangs("ko", ["ko", "en"]));
    try {
      renderPlay();
      fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
      await screen.findByTestId("dialogue-panel");
      (api.getRegion as Mock).mockRejectedValueOnce(new HttpError(502, "Bad Gateway", "proxy"));
      fireEvent.click(screen.getByTestId("lang-en"));
      expect(await screen.findByTestId("play-error")).toBeInTheDocument();
      fireEvent.click(within(screen.getByTestId("play-error")).getByRole("button"));
      expect(await screen.findByTestId("dialogue-panel")).toBeInTheDocument();
    } finally {
      act(() => setLang("ko"));
    }
  });
});

describe("code review 01 #17: the phone's bar keeps room under the page", () => {
  it("measures itself into --dock-h while it is there", async () => {
    let fire: () => void = () => {};
    vi.stubGlobal("ResizeObserver", class {
      constructor(cb: () => void) { fire = cb; }
      observe() {}
      disconnect() {}
    });
    width = 390;
    const { unmount } = renderPlay();
    const dock = await screen.findByTestId("action-dock");
    Object.defineProperty(dock, "offsetHeight", { value: 180 });
    act(() => fire());
    expect(document.documentElement.style.getPropertyValue("--dock-h")).toBe("180px");
    unmount();
    expect(document.documentElement.style.getPropertyValue("--dock-h")).toBe("");
  });
});
