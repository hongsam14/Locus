// V4 FR-D8 (BR-V4-10, TP-V4-14): the home and play screens show no raw server value and no
// 0..1 number. Every value of the enums these screens meet is put on a screen at once, and
// the visible text is searched for the raw word and for a decimal like 0.42.
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { Mock } from "vitest";
import { resetCapabilities } from "../capabilities";
import { ENUM_VALUES } from "../format";
import { HomePage } from "../routes/HomePage";
import { PlayPage } from "../routes/PlayPage";
import type { GameSession, MoveOption, RegionView, SessionRumor, TurnRun } from "../types";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn(),
    getSession: vi.fn(),
    getRegion: vi.fn(),
    getLog: vi.fn(),
    listTurnRuns: vi.fn(),
    listNpcs: vi.fn(),
    worldNames: vi.fn(),
    exportWorld: vi.fn(),
    listDemos: vi.fn(),
    listWorlds: vi.fn(),
    listSessions: vi.fn(),
    act: vi.fn(),
    getTurnRun: vi.fn(),
  },
}));
import { api } from "../api";

// a 0..1 number anywhere, also glued to a letter ("d0.42", the old rumor badge): FD's
// /\b0\.\d+\b/ misses that one, so the left side only refuses a digit or a dot (10.5, 1.05)
const DECIMAL = /(?<![\d.])0\.\d+/;
const RAW = [...ENUM_VALUES.regionLevel, ...ENUM_VALUES.travelBy, ...ENUM_VALUES.sessionStatus, ...ENUM_VALUES.rumorOrigin];
const rawIn = (text: string) => RAW.filter((v) => new RegExp(`\\b${v}\\b`).test(text));

/** The page's text, one text node at a time with a space between: `textContent` glues
 * siblings ("Saltwake" + "town · 2턴째" → "Saltwaketown"), which hides a raw word from the
 * search (code review 01 #10). The whole body, so sheets in portals count too. */
function visibleText(): string {
  const parts: string[] = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) parts.push(n.textContent ?? "");
  return parts.join(" ");
}

const moves: MoveOption[] = ENUM_VALUES.travelBy.map((kind, i) => ({
  region_id: `m${i}`, region_name: `Place ${i}`, kind, weight: 0.37, cost_turns: i + 1,
  passable: kind !== "blocked", reason: kind === "blocked" ? "blocked pass" : null,
}));
const rumors: SessionRumor[] = ENUM_VALUES.rumorOrigin.map((origin, i) => ({
  id: `r${i}`, session_id: "s1", region_id: "a", distorted_from_id: "k1", distorted_from_kind: "knowledge",
  statement: `Tale ${i}`, distortion_degree: 0.42, support: 0.73, confidence: 0.61, promoted: i === 0, origin_kind: origin,
}));
function view(level: string): RegionView {
  return {
    session_id: "s1", turn: 2, player: { id: "p", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 2 },
    region_id: "a", region_name: "Saltwake", level, description: "Salt on the wind.",
    level_path: ["Emberleaf", "Saltwake"], level_path_ids: ["top", "a"], npcs: [],
    facts: [{ knowledge_id: "k1", statement: "Ships come at dawn.", scope_type: "direct", is_hearsay: false, confidence: 0.88 }],
    hearsay: [{ knowledge_id: "h1", statement: "A storm far away.", scope_type: "hearsay", is_hearsay: true, confidence: 0.4, path_decay: 0.55 }],
    rumors, moves, turn_running: false, llm_available: true,
  };
}

beforeEach(() => {
  for (const m of Object.values(api)) (m as Mock).mockReset();
  resetCapabilities();
  (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
  (api.getLog as Mock).mockResolvedValue([
    { id: "e1", session_id: "s1", turn: 1, kind: "player_moved", summary: "",
      payload: { from_region_name: "Saltwake", to_region_name: "Place 1", cost_turns: 1 } },
  ]);
  (api.listTurnRuns as Mock).mockResolvedValue([]);
  (api.listNpcs as Mock).mockResolvedValue([]);
  (api.worldNames as Mock).mockResolvedValue({ world_id: "w", lang: "ko", world: {}, regions: {}, npcs: {}, event_seeds: {} });
  (api.exportWorld as Mock).mockResolvedValue({ world_id: "w", regions: [], connections: [], entities: [], knowledge: [], scopes: [] });
});

describe("TP-V4-14: no raw value, no 0..1 number", () => {
  const cases = ENUM_VALUES.regionLevel.flatMap((level) =>
    ENUM_VALUES.sessionStatus.map((status) => [level, status] as const),
  );

  it.each(cases)("the play screen at a %s, session %s, with a turn's result and the log", async (level, status) => {
    const session: GameSession = { id: "s1", world_id: "w", status, turn: 2 };
    (api.getSession as Mock).mockResolvedValue(session);
    (api.getRegion as Mock).mockResolvedValue(view(level));
    render(
      <MemoryRouter initialEntries={["/play/s1"]}>
        <Routes><Route path="/play/:sessionId" element={<PlayPage pollMs={1} />} /></Routes>
      </MemoryRouter>,
    );
    await screen.findByTestId("region-title");
    await waitFor(() => expect(screen.getByTestId("move-m0")).toBeInTheDocument());
    if (status === "open") {
      // a turn with region changes and a GM line: the result band is searched too
      const running: TurnRun = { id: "r1", session_id: "s1", action: { type: "wait" }, cost_turns: 1, status: "running", started_turn: 2 };
      (api.act as Mock).mockResolvedValue(running);
      (api.getTurnRun as Mock).mockResolvedValue({
        ...running, status: "done",
        result: { session: { ...session, turn: 3 }, player: null, turns: [], narration: [], llm_calls: 1, llm_available: true,
          budget_exhausted: false, llm_failed: false, declaration: { text: "바람이 분다.", record: "", lang: "ko", llm_calls: 1 },
          changes: [{ region_id: "m1", region_name: "Place 1", promoted: ["x"], demoted: ["y"], pruned: ["z"],
            events_applied: ["e"], events_resolved: ["f"], rumors_added: ["g"] }] },
      });
      await act(async () => fireEvent.click(screen.getByTestId("wait-btn")));
      await screen.findByTestId("result-band");
    }
    const text = visibleText();
    expect(rawIn(text)).toEqual([]);
    expect(text).not.toMatch(DECIMAL);
    expect(text).not.toContain("blocked pass");
  });

  it("the new-session form lists every region level in words", async () => {
    (api.listDemos as Mock).mockResolvedValue([]);
    (api.listWorlds as Mock).mockResolvedValue([{ id: "harrow", name: "Harrow", region_count: 5, open_sessions: 0 }]);
    (api.exportWorld as Mock).mockResolvedValue({ world_id: "harrow", connections: [], entities: [], knowledge: [], scopes: [],
      regions: ENUM_VALUES.regionLevel.map((level, i) => ({ id: `r${i}`, name: `Spot ${i}`, level })) });
    render(<MemoryRouter><HomePage /></MemoryRouter>);
    fireEvent.click(await screen.findByTestId("world-start-harrow"));
    await screen.findByTestId("new-session-form");
    expect(rawIn(visibleText())).toEqual([]);
  });

  it("the home cards and rows", async () => {
    (api.listDemos as Mock).mockResolvedValue([
      { name: "emberleaf", title: "Emberleaf Isle", start_region_id: "a", has_sources: true, description: "Three provinces." },
    ]);
    (api.listWorlds as Mock).mockResolvedValue([
      { id: "emberleaf", name: "Emberleaf Isle", region_count: 12, open_sessions: 1 },
      { id: "harrow", name: "Harrow", region_count: 4, open_sessions: 2, updated_at: "2026-10-02T09:30:00Z" },
    ]);
    (api.listSessions as Mock).mockResolvedValue([{ id: "s1", world_id: "emberleaf", status: "open", turn: 3, created_at: "2026-10-01T00:00:00Z" }]);
    render(<MemoryRouter><HomePage /></MemoryRouter>);
    await screen.findByTestId("world-row-harrow");
    await screen.findByTestId("demo-continue-emberleaf");
    const text = visibleText();
    expect(rawIn(text)).toEqual([]);
    expect(text).not.toMatch(DECIMAL);
  });

  it("the search finds what it looks for, also beside a name in the next node", () => {
    document.body.innerHTML = "<h1>Saltwake</h1><span>town · 2턴째</span>";
    expect(rawIn(visibleText())).toEqual(["town"]);
    document.body.innerHTML = "";
    expect(rawIn("마을 · river")).toEqual(["river"]);
    expect(rawIn("Riverton · Opening")).toEqual([]); // a name is not the word
    for (const bad of ["d0.42", "· 0.42 ·", "(0.5)"]) expect(bad).toMatch(DECIMAL);
    for (const ok of ["10.5", "1.05", "2026. 10. 2.", "4턴"]) expect(ok).not.toMatch(DECIMAL);
  });
});
