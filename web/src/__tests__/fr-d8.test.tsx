// V4 FR-D8 (BR-V4-10, TP-V4-14): the home and play screens show no raw server value and no
// 0..1 number. Every value of the enums these screens meet is put on a screen at once, and
// the visible text is searched for the raw word and for a decimal like 0.42.
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { Mock } from "vitest";
import { resetCapabilities } from "../capabilities";
import { ENUM_VALUES, enumLabel, numberWithMeaning } from "../format";
import { setLang, t } from "../i18n";
import { BUILD_STAGES } from "../features/editor/buildStages";
import { EditorPage } from "../routes/EditorPage";
import { GmPage } from "../routes/GmPage";
import { HomePage } from "../routes/HomePage";
import { PlayPage } from "../routes/PlayPage";
import type { AugQuestion, AugRun, GameSession, MoveOption, RegionView, SessionRumor, TurnRun } from "../types";

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
    // V6: the GM screen
    getWorldState: vi.fn(),
    getTimeline: vi.fn(),
    listEvents: vi.fn(),
    listRumors: vi.fn(),
    listSeeds: vi.fn(),
    listDeeds: vi.fn(),
    getPlayer: vi.fn(),
    sessionKnowledge: vi.fn(),
    // V8: the editor
    getEditorRegion: vi.fn(),
    listUnscoped: vi.fn(),
    priorRefs: vi.fn(),
    listPriors: vi.fn(),
    startRun: vi.fn(),
    getDeletePlan: vi.fn(),
    uploadBuild: vi.fn(),
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

// V6 (BR-V6-24/25, TP-V6-12): the GM screen shows numbers — but each with its meaning — and
// no raw value of the enums it meets. The slant of a judgment is the NPC's own words, not an
// enum (code plan § 1.1 R-01), so it is not searched.
describe("TP-V6-12: the GM screen in words", () => {
  const GM_RAW = [
    ...ENUM_VALUES.eventStatus, ...ENUM_VALUES.eventCategory, ...ENUM_VALUES.eventLifecycle,
    ...ENUM_VALUES.sessionStatus, ...ENUM_VALUES.scopeType, ...ENUM_VALUES.regionLevel,
  ];
  const gmRaw = (text: string) => GM_RAW.filter((v) => new RegExp(`\\b${v}\\b`).test(text));
  // a 0..1 number must carry its meaning right after it ("0.42 · 많이 비틀림")
  // one decimal is a number too ("→ 0.4", code review 01 #11); T4 is the en abbreviation (#40)
  const BARE = /(?<![\d.])[01]\.\d+(?!\d)(?! · )/;
  const ABBREV = /(?<![\p{L}\d])[mdtMDT]\d/u; // m0.40, d0.42, t4, T4

  const regions = ENUM_VALUES.regionLevel.map((level, i) => ({ id: `g${i}`, name: `Place ${i}`, level }));
  const events = ENUM_VALUES.eventCategory.map((category, i) => ({
    id: `e${i}`, session_id: "s1", region_id: "g0", category, description: `Thing ${i}`, magnitude: 0.37 + i / 100,
    lifecycle: ENUM_VALUES.eventLifecycle[i % 2], status: ENUM_VALUES.eventStatus[i % 3], created_turn: i, resolved_turn: i % 3 === 2 ? i : null,
    contributions: {},
  }));

  beforeEach(() => {
    (api.getSession as Mock).mockResolvedValue({ id: "s1", world_id: "w", status: "open", turn: 4, created_at: "2026-10-08T05:05:00Z" });
    (api.listSessions as Mock).mockResolvedValue(ENUM_VALUES.sessionStatus.map((status, i) => ({
      id: `s${i + 1}`, world_id: "w", status, turn: i + 1, created_at: "2026-10-0" + (i + 1) + "T05:05:00Z" })));
    (api.exportWorld as Mock).mockResolvedValue({ world_id: "w", regions, connections: [], entities: [], knowledge: [], scopes: [] });
    (api.getWorldState as Mock).mockResolvedValue({ session_id: "s1", turn: 4, player_region_id: "g0", max_event_suggestions: 3,
      regions: regions.map((r, i) => ({ region_id: r.id, region_name: r.name, distortion: 0.42, feedback_share: i ? 0 : 0.07,
        active_rumors: 2, promoted_rumors: 1, deed_rumors: 1, active_events: 1 })) });
    (api.getTimeline as Mock).mockResolvedValue([
      ...events.map((e, i) => ({ id: `t${i}`, session_id: "s1", turn: i, kind: "event_created",
        summary: "", payload: { region_id: "g0", region_name: "Place 0", category: e.category } })),
      // a distortion setting carries its degree (code review 01 #11)
      { id: "td", session_id: "s1", turn: 1, kind: "set_distortion", summary: "", payload: { region_id: "g0", region_name: "Place 0", degree: 0.4 } },
    ]);
    (api.listEvents as Mock).mockResolvedValue(events);
    (api.listRumors as Mock).mockResolvedValue(rumors);
    (api.listSeeds as Mock).mockResolvedValue(events.map((e) => ({ seed: { id: `sd-${e.id}`, world_id: "w", region_id: "g0",
      title: `Seed ${e.id}`, description: "", category: e.category, magnitude: 0.55 }, region_name: "Place 0", running_event_id: null })));
    (api.listDeeds as Mock).mockResolvedValue([{
      deed: { id: "d1", session_id: "s1", player_id: "p", region_id: "g0", turn: 2, kind: "arrival", text: "Ari came.",
        witnessed_npc_ids: [], voided: false, region_name: "Place 0", witness_names: [] },
      appraisals: [{ id: "ap", deed_id: "d1", npc_id: "n1", noteworthy: true, salience: 0.83, slant: "admiring", retelling: "", turn: 2, npc_name: "Mara" }],
      rumors: [], reached_region_ids: [], reached_region_names: [],
    }]);
    (api.getPlayer as Mock).mockResolvedValue({ id: "p", session_id: "s1", name: "Ari", region_id: "g0", turns_spent: 2 });
    (api.sessionKnowledge as Mock).mockResolvedValue({ world_id: "w", region_id: "g0", shared_ids: [], unique_ids: [],
      items: ENUM_VALUES.scopeType.map((scope, i) => ({ knowledge_id: `k${i}`, statement: `Known ${i}`, scope_type: scope,
        is_hearsay: false, confidence: 0.66, path_decay: i === 0 ? 0.31 : null, distortion: i === 1 ? 0.27 : null })) });
  });

  afterEach(() => setLang("ko"));

  it.each(["ko", "en"] as const)("%s: every tab, the head and each region level: no raw value, no bare or abbreviated number", async (lang) => {
    setLang(lang);
    render(
      <MemoryRouter initialEntries={["/gm/s1"]}>
        <Routes><Route path="/gm/:sessionId" element={<GmPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("advance-turn-btn")).toBeEnabled());
    const seen: string[] = [];
    const tab = (name: string) => {
      fireEvent.mouseDown(screen.getByTestId(`gm-tab-${name}`).closest('[role="tab"]') as HTMLElement, { button: 0 });
    };
    for (const r of regions) {
      // the world comes after the session: wait for its map (code review 01 #21)
      fireEvent.click(await screen.findByTestId(`region-marker-${r.id}`));
      await screen.findByTestId("region-heading");
      seen.push(visibleText());
    }
    fireEvent.click(screen.getByTestId(`region-marker-g0`));
    await screen.findByTestId("rumor-r0");
    fireEvent.click(screen.getByRole("button", { name: /NPC/ }));
    await screen.findByTestId("knowledge-item-k0");
    seen.push(visibleText());
    tab("events");
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t("label.eventsResolved")) }));
    await screen.findByTestId("event-e2");
    seen.push(visibleText());
    tab("seeds");
    await screen.findByTestId("seed-row-sd-e0");
    seen.push(visibleText());
    tab("timeline");
    await screen.findByTestId("timeline");
    seen.push(visibleText());
    tab("deeds");
    await screen.findByTestId("deed-d1");
    seen.push(visibleText());
    const all = seen.join("\n");
    expect(gmRaw(all)).toEqual([]);
    const bare = all.match(BARE);
    expect(bare && all.slice(Math.max(0, (bare.index ?? 0) - 60), (bare.index ?? 0) + 20)).toBeNull();
    expect(all.match(ABBREV)).toBeNull();
    expect(all).toContain(numberWithMeaning("distortion", 0.42)); // numbers are there, with meanings
  }, 30_000); // one long scenario: under a loaded test run it outlasts 5 s (V8 code review 01 #15)
});

// V8 (BR-V8-15/16/18, TP-V8-9): the editor in words. Every region level, connection kind,
// augmentation status, target, issue and action, wiki domain and build stage is put on a
// screen — the head, the legend, both map forms, the inspector with its four sections, the
// delete plan, the augmentation tab, the grounds tab and a build report — and the shown text
// is searched for the raw value, a "type:action" or key text, and a bare 0..1 number. The
// server's own sentences sit folded in <details> by design (BR-V8-22/30); only the summary
// of a closed one counts as shown.
describe("TP-V8-9: the editor in words", () => {
  const ALL_RAW = [
    ...ENUM_VALUES.regionLevel, ...ENUM_VALUES.connectionKind, ...ENUM_VALUES.augmentationStatus,
    ...ENUM_VALUES.augmentationTarget, ...ENUM_VALUES.augmentationAction, ...ENUM_VALUES.augmentationIssue,
    ...ENUM_VALUES.wikiDomain, ...BUILD_STAGES,
  ];
  // in English most values are plain words a sentence may use ("pick a region"); there the
  // values no sentence would write are searched
  const RAW: Record<"ko" | "en", readonly string[]> = { ko: ALL_RAW, en: ALL_RAW.filter((v) => /[_-]/.test(v)) };
  const rawOf = (lang: "ko" | "en", text: string) =>
    RAW[lang].filter((v) => new RegExp(`(?<![\\w-])${v}(?![\\w-])`).test(text));
  const KEYISH = /[a-z_]+:[a-z_]+|\w\|\w/; // "low_confidence:confirm", "gap:region:…", "r1|r2"
  const BARE = /(?<![\d.])[01]\.\d+(?!\d)(?! · )/;

  function shownText(): string {
    const parts: string[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const closed = n.parentElement?.closest("details:not([open])");
      if (closed && !n.parentElement?.closest("summary")) continue;
      parts.push(n.textContent ?? "");
    }
    return parts.join(" ");
  }

  const regions = ENUM_VALUES.regionLevel.map((level, i) => ({ id: `v${i}`, name: `곳${i}`, level,
    position: { x: 0.1 + i * 0.2, y: 0.2 + (i % 2) * 0.5 } }));
  const kinds = ENUM_VALUES.connectionKind;
  const connections = kinds.map((kind, i) => ({ world_id: "w", source_region_id: "v0", target_region_id: `v${i + 1}`,
    kind, weight: 0.37 }));
  const keys = kinds.map((kind, i) => ({ world_id: "w", a_region_id: "v0", b_region_id: `v${i + 1}`, kind }));
  const mill = { id: "k1", world_id: "w", title: "물레방아", statement: "물레방아가 돈다", confidence: 0.73,
    provenance: { source: "input" } };
  const targetOf = (kind: string) =>
    kind === "region" ? { kind, id: "v1", name: "곳1" }
    : kind === "knowledge" ? { kind, id: "k1", name: "물레방아" }
    : kind === "entity" ? { kind, id: "e1", name: "옛 종" }
    // as the server names a connection: the raw kind in brackets (code review 01 #3)
    : { kind, id: "v0|v1|adjacent", name: "곳0 – 곳1 (adjacent)",
        connection: { world_id: "w", a_region_id: "v0", b_region_id: "v1", kind: "adjacent" } };
  const keyOf = (issue: string, kind: string) => `${issue}:${kind}:${targetOf(kind).id}::`;
  const questions: AugQuestion[] = ENUM_VALUES.augmentationIssue.map((issue, i) => {
    const kind = ENUM_VALUES.augmentationTarget[i % 4];
    // the server's no-LLM template, raw property and all: the screen must not show it
    return { id: `q${i}`, issue_id: `i${i}`, issue_key: keyOf(issue, kind), type: issue,
      text: `item ${i} points at something that is gone (about_entity_ids). Re-point or clear?`,
      actions: [...ENUM_VALUES.augmentationAction], needs: {},
      target: { ...targetOf(kind), ...(issue === "dangling" ? { field: "about_entity_ids" } : {}) } } as AugQuestion;
  });
  const runOf = (status: AugRun["status"]): AugRun => ({
    id: `run-${status}`, world_id: "w", status, answers: 4, llm_calls: 1, llm_budget_exhausted: status === "stopped",
    open_questions: status === "open" ? questions : [],
    history: ENUM_VALUES.augmentationIssue.flatMap((issue) => ENUM_VALUES.augmentationAction.map((action) =>
      ({ id: `c-${issue}-${action}`, description: `${issue}:${action}`, added_ids: [], reverted: action === "add" }))),
    ignored_keys: ENUM_VALUES.augmentationTarget.map((kind) => keyOf("gap", kind)),
    kept_keys: ENUM_VALUES.augmentationTarget.map((kind) => keyOf("low_confidence", kind)),
  });

  beforeEach(() => {
    (api.exportWorld as Mock).mockResolvedValue({ world_id: "w", world: { id: "w", name: "엠버리프" }, regions, connections,
      entities: [{ id: "e1", name: "옛 종" }], knowledge: [mill], scopes: [], unscoped_knowledge_ids: ["k7"] });
    (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "엠버리프", region_count: 5, open_sessions: 2 }]);
    (api.getEditorRegion as Mock).mockResolvedValue({
      region: { ...regions[0], world_id: "w" }, children: [],
      connections: keys.map((key, i) => ({ key, other_region_id: key.b_region_id, other_region_name: `곳${i + 1}`,
        weight: 0.37, prior: i === 0 ? { prior_id: "p1", effect: "길이 난다", broken: false } : i === 1 ? { prior_id: "gone", broken: true } : null })),
      knowledge: [{ knowledge: mill, scope_region_ids: ["v0"] }],
      npcs: [{ id: "n1", world_id: "w", name: "에이다", role: "방앗간지기", description: "", home_region_id: "v0", traits: [],
        provenance: { source: "input" } }],
    });
    (api.getDeletePlan as Mock).mockResolvedValue({ region_id: "v0", region_name: "곳0", children: [{ id: "v9", name: "곳9" }],
      connections: keys, npcs: [{ id: "n1", name: "에이다" }], knowledge_to_unscope: [{ id: "k1", name: "물레방아" }],
      knowledge_scope_removed: [], entities_unlocated: [{ id: "e1", name: "옛 종" }], blocked_by_sessions: ["s7"], seed_ids: ["sd1"] });
    (api.listUnscoped as Mock).mockResolvedValue([{ ...mill, id: "k7", title: "잃은 종" }]);
    (api.listPriors as Mock).mockResolvedValue([]);
    (api.priorRefs as Mock).mockResolvedValue({
      usages: [{ prior: { id: "p1", world_id: "w", prior_type: "fact", condition: "강이 흐르면", effect: "길이 난다",
        domains: [...ENUM_VALUES.wikiDomain], confidence: 0.64 }, connections: keys, knowledge: [{ id: "k1", name: "물레방아" }] }],
      broken: [{ ref_id: "gone", connections: keys.slice(0, 2), knowledge: [] }],
    });
    (api.startRun as Mock)
      .mockResolvedValueOnce(runOf("open"))
      .mockResolvedValueOnce(runOf("converged"))
      .mockResolvedValueOnce(runOf("stopped"));
    (api.uploadBuild as Mock).mockResolvedValue({ world_id: "w", regions_created: 5, connections_created: 4,
      entities_created: 1, knowledge_created: 2, corroborations_created: 1, unscoped_knowledge_ids: ["k7"], llm_calls: 3,
      embedding_calls: 1, replaced: true, closed_session_ids: ["s1"], priors_created: 1, ok: true, carried_npcs: 2,
      carried_seeds: 1, backup_path: "/backups/w.json",
      warnings: [...BUILD_STAGES, "mystery"].map((stage, i) => ({ stage, message: `server line ${i}`,
        severity: i % 3 === 0 ? "error" : "warning" })) });
  });

  afterEach(() => setLang("ko"));

  it.each(["ko", "en"] as const)("%s: head, legend, forms, inspector, delete plan, augmentation, grounds, build report", async (lang) => {
    setLang(lang);
    render(
      <MemoryRouter initialEntries={["/editor/w"]}>
        <Routes><Route path="/editor/:worldId" element={<EditorPage />} /></Routes>
      </MemoryRouter>,
    );
    const seen: string[] = [];
    const tab = (name: string) =>
      fireEvent.mouseDown(screen.getByTestId(`editor-tab-${name}`).closest('[role="tab"]') as HTMLElement, { button: 0 });
    const escape = async () => {
      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
      await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    };
    // the head, the legend, the inspector with all four sections
    fireEvent.click(await screen.findByTestId("region-marker-v0"));
    await screen.findByTestId("inspector-section-npcs");
    for (const k of ["connections", "knowledge", "npcs"]) {
      fireEvent.click(screen.getByTestId(`inspector-section-${k}`).querySelector("[aria-expanded]") as HTMLElement);
    }
    await screen.findByTestId("editor-npc-n1");
    seen.push(shownText());
    // the delete plan
    fireEvent.click(screen.getByTestId("region-delete"));
    await screen.findByTestId("delete-plan");
    seen.push(shownText());
    await escape();
    // both map forms
    fireEvent.click(screen.getByTestId("map-tool-add-region"));
    fireEvent.click(screen.getByTestId("region-marker-v0").closest("svg") as SVGSVGElement);
    await screen.findByTestId("new-region-form");
    seen.push(shownText());
    await escape();
    fireEvent.click(screen.getByTestId("map-tool-connect"));
    fireEvent.click(screen.getByTestId("region-marker-v0"));
    fireEvent.click(screen.getByTestId("region-marker-v1"));
    fireEvent.change(await screen.findByTestId("connection-kind"), { target: { value: "adjacent" } });
    await screen.findByTestId("connection-exists");
    seen.push(shownText());
    await escape();
    fireEvent.click(screen.getByTestId("map-tool-select"));
    // the augmentation tab in each status
    tab("augment");
    for (const status of ENUM_VALUES.augmentationStatus) {
      fireEvent.click(screen.getByTestId("augment-find"));
      await waitFor(() => expect(screen.getByTestId("augment-status")).toHaveTextContent(enumLabel("augmentationStatus", status)));
      fireEvent.click(screen.getByTestId("augment-kept").querySelector("summary") as HTMLElement);
      seen.push(shownText());
    }
    // the grounds tab with its references open
    tab("wiki");
    fireEvent.click(await screen.findByTestId("prior-refs-p1"));
    seen.push(shownText());
    // a build report with every stage, and one the screen does not know
    fireEvent.click(screen.getByTestId("file-menu"));
    fireEvent.click(screen.getByTestId("file-build"));
    fireEvent.change(await screen.findByTestId("build-memo"), { target: { value: "강 마을" } });
    await waitFor(() => expect(screen.getByTestId("build-submit")).toBeEnabled());
    fireEvent.click(screen.getByTestId("build-submit"));
    await screen.findByTestId("build-confirm");
    fireEvent.click(screen.getByText(t("action.confirm")));
    await screen.findByTestId("build-report");
    seen.push(shownText());

    const all = seen.join("\n");
    expect(rawOf(lang, all)).toEqual([]);
    const key = all.match(KEYISH);
    expect(key && all.slice(Math.max(0, (key.index ?? 0) - 60), (key.index ?? 0) + 30)).toBeNull();
    const bare = all.match(BARE);
    expect(bare && all.slice(Math.max(0, (bare.index ?? 0) - 60), (bare.index ?? 0) + 20)).toBeNull();
    // the values are there, in words
    expect(all).toContain(enumLabel("connectionKind", "river"));
    expect(all).toContain(numberWithMeaning("weight", 0.37));
    expect(all).toContain(t("label.stage.other"));
    expect(all).toContain(t("label.field.about_entity_ids"));
  }, 30_000); // one long scenario: under a loaded test run it outlasts 5 s (V8 code review 01 #15)
});
