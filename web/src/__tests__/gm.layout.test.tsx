// V6 GM screen as a whole (code plan Step 5, TP-V6-1/2/3/5/6/8/10, BR-V6-02..12/15/16/18/21/
// 32/35) and the GmHub behaviours that moved here (frontend-components § 7.1, TP-V6-17).
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { HttpError } from "../api/http";
import { resetCapabilities } from "../capabilities";
import { numberWithMeaning, turnAt } from "../format";
import { WIDE } from "../hooks";
import { t, timelineText } from "../i18n";
import { GmPage } from "../routes/GmPage";
import type { GameSession, SessionEvent, SessionRumor, TimelineEntry, WorldState } from "../types";
import { clearToasts, useToasts } from "../ui/toast";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn(),
    worldNames: vi.fn(),
    getSession: vi.fn(),
    exportWorld: vi.fn(),
    listSessions: vi.fn(),
    listEvents: vi.fn(),
    getTimeline: vi.fn(),
    getWorldState: vi.fn(),
    listRumors: vi.fn(),
    listSeeds: vi.fn(),
    listDeeds: vi.fn(),
    getPlayer: vi.fn(),
    listTurnRuns: vi.fn(),
    sessionKnowledge: vi.fn(),
    advanceTurn: vi.fn(),
    suggestEvents: vi.fn(),
    approveEvent: vi.fn(),
    discardEvent: vi.fn(),
    resolveEvent: vi.fn(),
    createEvent: vi.fn(),
    startSeed: vi.fn(),
    setDistortion: vi.fn(),
    setSupport: vi.fn(),
    generateRumors: vi.fn(),
    regenRumors: vi.fn(),
    voidDeed: vi.fn(),
    closeSession: vi.fn(),
    startSession: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;
const OPEN: GameSession = { id: "s1", world_id: "w", status: "open", turn: 3, created_at: "2026-10-08T05:05:00Z" };
const WORLD = { world_id: "w", regions: [{ id: "a", name: "Riverton", level: "town" }, { id: "b", name: "Hollow", level: "town" }],
  connections: [], entities: [], knowledge: [], scopes: [] };
const state = (over: Partial<WorldState> = {}): WorldState => ({
  session_id: "s1", turn: 3, player_region_id: "a",
  regions: [
    { region_id: "a", region_name: "Riverton", distortion: 0.6, feedback_share: 0.05, active_rumors: 2, promoted_rumors: 1, deed_rumors: 1, active_events: 1 },
    { region_id: "b", region_name: "Hollow", distortion: 0.1, feedback_share: 0, active_rumors: 0, promoted_rumors: 0, deed_rumors: 0, active_events: 0 },
  ],
  ...over,
});
const rumor = (id: string, over: Partial<SessionRumor> = {}): SessionRumor => ({
  id, session_id: "s1", region_id: "a", distorted_from_id: "k", distorted_from_kind: "knowledge", statement: `rumor ${id}`,
  distortion_degree: 0.42, support: 0.5, confidence: 0.5, promoted: false, ...over,
});
const ev = (id: string, status: SessionEvent["status"], over: Partial<SessionEvent> = {}): SessionEvent => ({
  id, session_id: "s1", region_id: "b", category: "war", description: `event ${id}`, magnitude: 0.5, lifecycle: "persistent",
  status, created_turn: 1, contributions: {}, ...over,
});
const line = (id: string, turn: number, over: Partial<TimelineEntry> = {}): TimelineEntry => ({
  id, session_id: "s1", turn, kind: "promote", summary: id, payload: { region_id: "a", region_name: "Riverton" }, ...over,
});
function deferred<T>() {
  let resolve: (v: T) => void = () => {};
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

function reads() {
  (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
  (api.worldNames as Mock).mockResolvedValue({ world_id: "w", lang: "ko", world: { name: "엠버리프" }, regions: {}, npcs: {}, event_seeds: {} });
  (api.getSession as Mock).mockImplementation(async (sid: string) => ({ ...OPEN, id: sid }));
  (api.exportWorld as Mock).mockResolvedValue(WORLD);
  (api.listSessions as Mock).mockResolvedValue([OPEN]);
  (api.listEvents as Mock).mockResolvedValue([]);
  (api.getTimeline as Mock).mockResolvedValue([]);
  (api.getWorldState as Mock).mockResolvedValue(state());
  (api.listRumors as Mock).mockResolvedValue([]);
  (api.listSeeds as Mock).mockResolvedValue([]);
  (api.listDeeds as Mock).mockResolvedValue([]);
  (api.getPlayer as Mock).mockResolvedValue({ id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 });
  (api.listTurnRuns as Mock).mockResolvedValue([]);
  (api.sessionKnowledge as Mock).mockResolvedValue({ world_id: "w", region_id: "a", items: [], shared_ids: [], unique_ids: [] });
}

let wide = false;
beforeEach(() => {
  vi.clearAllMocks();
  resetCapabilities();
  clearToasts();
  wide = false;
  window.matchMedia = ((q: string) => ({
    matches: wide && q === WIDE, media: q, addEventListener() {}, removeEventListener() {},
  })) as unknown as typeof window.matchMedia;
  reads();
});
afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  resetCapabilities();
});

function Toasts() {
  const toasts = useToasts();
  return <div data-testid="toast-keys">{toasts.map((x) => x.key).join(",")}</div>;
}
function Go({ to }: { to: string }) {
  const navigate = useNavigate();
  return <button data-testid={`go-${to}`} onClick={() => navigate(`/gm/${to}`)}>go</button>;
}
function renderGm(path = "/gm/s1") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Go to="s2" />
      <Toasts />
      <Routes>
        <Route path="/gm/:sessionId" element={<GmPage />} />
      </Routes>
    </MemoryRouter>,
  );
}
async function ready() {
  await waitFor(() => expect(screen.getByTestId("advance-turn-btn")).toBeEnabled());
}
async function chooseRegion(id: string) {
  fireEvent.click(await screen.findByTestId(`region-marker-${id}`));
  await screen.findByTestId("gm-region");
}
function openTab(name: string) {
  const tab = screen.getByTestId(`gm-tab-${name}`).closest('[role="tab"]') as HTMLElement;
  fireEvent.mouseDown(tab, { button: 0 });
}
const selectedTab = () => screen.getByRole("tab", { selected: true });

describe("TP-V6-1: two widths, each part once (BR-V6-02/03)", () => {
  const order = () =>
    ["gm-header", "turn-tools", "turn-band-live", "gm-map", "gm-tabs"].map((id) => screen.getByTestId(id))
      .sort((x, y) => (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1))
      .map((e) => e.getAttribute("data-testid"));

  it("wide: the map beside a panel holding the turn tools, the band and the tabs", async () => {
    wide = true;
    renderGm();
    await ready();
    const aside = screen.getByRole("region", { name: t("label.gmPanel") }); // review 43(c): not an <aside>
    for (const id of ["turn-tools", "turn-band-live", "gm-tabs"]) expect(aside).toContainElement(screen.getByTestId(id));
    expect(aside).not.toContainElement(screen.getByTestId("gm-map"));
    for (const id of ["advance-turn-btn", "gm-tabs", "gm-map", "session-select"]) expect(screen.getAllByTestId(id)).toHaveLength(1);
  });

  it("narrower: one column — head, tools, band, map, tabs", async () => {
    renderGm();
    await ready();
    expect(screen.queryByRole("region", { name: t("label.gmPanel") })).not.toBeInTheDocument();
    expect(order()).toEqual(["gm-header", "turn-tools", "turn-band-live", "gm-map", "gm-tabs"]);
    for (const id of ["advance-turn-btn", "gm-tabs", "gm-map"]) expect(screen.getAllByTestId(id)).toHaveLength(1);
  });
});

describe("TP-V6-2: choosing a region opens its tab; nothing else moves the tab (BR-V6-05)", () => {
  it("the map, the band and an event card choose a region and open [region]", async () => {
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "active")]);
    (api.advanceTurn as Mock).mockResolvedValue({ session_id: "s1", turn: 4, promoted_ids: [], demoted_ids: [], applied_event_ids: [],
      resolved_event_ids: [], region_changes: [{ region_id: "a", region_name: "Riverton", promoted: ["x"], demoted: [], pruned: [],
        events_applied: [], events_resolved: [], rumors_added: [] }] });
    (api.suggestEvents as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    expect(screen.getByTestId("gm-no-region")).toHaveTextContent(t("empty.noRegionChosen"));
    expect(api.listRumors).not.toHaveBeenCalled(); // no region, no rumor read (FR-H6)
    // 1. the map
    await chooseRegion("a");
    expect(screen.getByTestId("region-heading")).toHaveTextContent("Riverton");
    // 2. an event card
    openTab("events");
    fireEvent.click(await screen.findByTestId("event-region-e1"));
    expect(selectedTab()).toHaveTextContent(t("tab.region"));
    expect(screen.getByTestId("region-heading")).toHaveTextContent("Hollow");
    // 3. the band
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    openTab("timeline");
    fireEvent.click(await screen.findByTestId("turn-band-region-a"));
    expect(selectedTab()).toHaveTextContent(t("tab.region"));
    expect(screen.getByTestId("region-heading")).toHaveTextContent("Riverton");
    // a suggestion does not move the tab: the events tab's count says it
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "active"), ev("e2", "suggested"), ev("e3", "suggested")]);
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn")));
    await waitFor(() => expect(screen.getByTestId("events-badge")).toHaveTextContent("2")); // suggestions only (review #20)
    expect(selectedTab()).toHaveTextContent(t("tab.region"));
  });
});

describe("TP-V6-3: one turn per press, one band, the new lines marked (BR-V6-06/07/08)", () => {
  it("two quick presses advance once; the band names the regions; no turn notification", async () => {
    const hold = deferred<unknown>();
    (api.advanceTurn as Mock).mockReturnValue(hold.promise);
    (api.getTimeline as Mock).mockResolvedValue([line("old1", 2), line("old2", 3)]);
    renderGm();
    await ready();
    const btn = screen.getByTestId("advance-turn-btn");
    fireEvent.click(btn);
    fireEvent.click(btn);
    expect(api.advanceTurn).toHaveBeenCalledTimes(1);
    expect(api.advanceTurn).toHaveBeenCalledWith("s1"); // review #46
    expect(btn).toHaveAttribute("aria-disabled", "true");
    (api.getTimeline as Mock).mockResolvedValue([line("old1", 2), line("old2", 3), line("new1", 4)]);
    await act(async () => hold.resolve({ session_id: "s1", turn: 4, promoted_ids: [], demoted_ids: [], applied_event_ids: [],
      resolved_event_ids: [], budget_exhausted: true, region_changes: [{ region_id: "a", region_name: "Riverton", promoted: [],
        demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: ["r9"] }] }));
    const band = await screen.findByTestId("turn-band");
    expect(band).toHaveTextContent(t("notice.turnPassedGm", { n: 4 }));
    expect(band).toHaveTextContent("Riverton");
    expect(band).toHaveTextContent(t("notice.turnBudget"));
    expect(screen.getByTestId("toast-keys").textContent).not.toMatch(/turn:/);
    openTab("timeline");
    await waitFor(() => expect(screen.getByTestId("timeline-new-new1")).toHaveTextContent(t("label.newLine")));
    expect(screen.queryByTestId("timeline-new-old2")).not.toBeInTheDocument();
    // newest first (UX-34): the turn heads read 4, 3, 2
    const items = within(screen.getByTestId("timeline")).getAllByRole("listitem");
    expect(items.map((li) => li.querySelector("b")?.textContent)).toEqual([turnAt(4), turnAt(3), turnAt(2)]);
    expect(items[0]).toHaveTextContent(timelineText("promote", { region_id: "a", region_name: "Riverton" }, 4, "new1"));
    fireEvent.click(screen.getByTestId("turn-band-close"));
    expect(screen.queryByTestId("turn-band")).not.toBeInTheDocument();
  });

  it("the record shows twenty lines and [more] adds twenty (BR-V6-35)", async () => {
    (api.getTimeline as Mock).mockResolvedValue(Array.from({ length: 45 }, (_, i) => line(`l${i}`, i)));
    renderGm();
    await ready();
    openTab("timeline");
    const list = await screen.findByTestId("timeline");
    expect(within(list).getAllByRole("listitem")).toHaveLength(20);
    fireEvent.click(screen.getByTestId("timeline-more"));
    expect(within(screen.getByTestId("timeline")).getAllByRole("listitem")).toHaveLength(40);
    fireEvent.click(screen.getByTestId("timeline-more"));
    expect(within(screen.getByTestId("timeline")).getAllByRole("listitem")).toHaveLength(45);
    expect(screen.queryByTestId("timeline-more")).not.toBeInTheDocument();
  });
});

describe("TP-V6-5: GM writes go once however fast they are pressed (BR-V6-09)", () => {
  it("seed start, approve, create event and end session", async () => {
    const holds = [deferred<unknown>(), deferred<unknown>(), deferred<unknown>(), deferred<unknown>()];
    (api.listSeeds as Mock).mockResolvedValue([{ seed: { id: "sd", world_id: "w", region_id: "a", title: "Blight", description: "",
      category: "plague", magnitude: 0.5 }, region_name: "Riverton", running_event_id: null }]);
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "suggested")]);
    (api.startSeed as Mock).mockReturnValue(holds[0].promise);
    (api.approveEvent as Mock).mockReturnValue(holds[1].promise);
    (api.createEvent as Mock).mockReturnValue(holds[2].promise);
    (api.closeSession as Mock).mockReturnValue(holds[3].promise);
    renderGm();
    await ready();
    openTab("seeds");
    const start = await screen.findByTestId("seed-start-sd");
    fireEvent.click(start);
    fireEvent.click(start);
    openTab("events");
    const approve = await screen.findByTestId("approve-e1");
    fireEvent.click(approve);
    fireEvent.click(approve);
    await chooseRegion("a");
    fireEvent.click(screen.getByRole("button", { name: t("label.createEventHere") }));
    fireEvent.change(screen.getByTestId("event-description"), { target: { value: "Fire" } });
    fireEvent.click(screen.getByTestId("event-create-btn"));
    fireEvent.click(screen.getByTestId("event-create-btn"));
    fireEvent.click(screen.getByTestId("session-close-btn"));
    fireEvent.click(screen.getByTestId("session-close-confirm"));
    fireEvent.click(screen.getByTestId("session-close-confirm"));
    expect([api.startSeed, api.approveEvent, api.createEvent, api.closeSession].map((f) => (f as Mock).mock.calls.length)).toEqual([1, 1, 1, 1]);
    expect(api.createEvent).toHaveBeenCalledWith("s1", { region_id: "a", category: "war", description: "Fire", magnitude: 0.5, lifecycle: null });
    await act(async () => holds.forEach((h) => h.resolve({ id: "x" })));
  });
});

describe("TP-V6-6 (screen): nothing of the last session (BR-V6-15/16, #14, RE-F14)", () => {
  it("while the next session reads, the last one's head, turn and player are gone; the map stays", async () => {
    const next = deferred<GameSession>();
    (api.getSession as Mock).mockImplementation((sid: string) => (sid === "s1" ? Promise.resolve(OPEN) : next.promise));
    const lateEvents = deferred<SessionEvent[]>();
    renderGm();
    await ready();
    expect(screen.getByTestId("gm-player-status")).toHaveTextContent("Ari");
    (api.listEvents as Mock).mockImplementation((sid: string) => (sid === "s1" ? lateEvents.promise : Promise.resolve([])));
    (api.getPlayer as Mock).mockImplementation(async (sid: string) => {
      if (sid === "s1") return { id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 };
      throw new HttpError(404, "Not Found", "");
    });
    fireEvent.click(screen.getByTestId("go-s2"));
    expect(await screen.findByTestId("busy")).toBeInTheDocument();
    expect(screen.queryByTestId("gm-player-status")).not.toBeInTheDocument();
    expect(screen.getByTestId("region-marker-a")).toBeInTheDocument(); // same world: the map stays
    await act(async () => lateEvents.resolve([ev("old", "suggested")]));
    await act(async () => next.resolve({ ...OPEN, id: "s2", turn: 0 }));
    await ready();
    openTab("events"); // a hidden tab says nothing (code review 01 #17)
    await screen.findByTestId("events-suggested");
    expect(screen.queryByTestId("event-old")).not.toBeInTheDocument();
    expect(screen.queryByTestId("events-badge")).not.toBeInTheDocument();
    expect(screen.queryByTestId("gm-player-status")).not.toBeInTheDocument();
    expect(api.exportWorld).toHaveBeenCalledTimes(1);
  });

  it("another session starts afresh: no result band, the region tab open, no error line (code plan § 1.1 R-02)", async () => {
    (api.advanceTurn as Mock).mockResolvedValue({ session_id: "s1", turn: 4, promoted_ids: [], demoted_ids: [], applied_event_ids: [],
      resolved_event_ids: [], region_changes: [] });
    (api.suggestEvents as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"x","code":"gm_busy"}'));
    renderGm();
    await ready();
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn")));
    expect(await screen.findByTestId("turn-band")).toBeInTheDocument();
    expect(await screen.findByTestId("gm-hub-error")).toBeInTheDocument();
    openTab("deeds");
    expect(selectedTab()).toHaveTextContent(t("tab.deeds"));
    fireEvent.click(screen.getByTestId("go-s2"));
    await ready();
    expect(screen.queryByTestId("turn-band")).not.toBeInTheDocument();
    expect(screen.queryByTestId("gm-hub-error")).not.toBeInTheDocument();
    expect(selectedTab()).toHaveTextContent(t("tab.region"));
  });

  it("another region's rumors are gone while the next region reads", async () => {
    const b = deferred<SessionRumor[]>();
    (api.listRumors as Mock).mockImplementation((_s: string, rid: string) => (rid === "a" ? Promise.resolve([rumor("ra")]) : b.promise));
    renderGm();
    await ready();
    await chooseRegion("a");
    expect(await screen.findByTestId("rumor-ra")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("region-marker-b"));
    await waitFor(() => expect(screen.getByTestId("region-heading")).toHaveTextContent("Hollow"));
    expect(screen.queryByTestId("rumor-ra")).not.toBeInTheDocument();
    expect(screen.queryByTestId("support-ra")).not.toBeInTheDocument();
    await act(async () => b.resolve([rumor("rb", { region_id: "b" })]));
    expect(screen.getByTestId("rumor-rb")).toBeInTheDocument();
  });
});

describe("TP-V6-8 and TP-V6-10 (screen): retry, an ended session (BR-V6-12/18)", () => {
  it("a failed first read: [retry] reads the session and the world, and the map is drawn", async () => {
    (api.getSession as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue(OPEN);
    renderGm();
    expect(await screen.findByTestId("gm-error")).toBeInTheDocument();
    expect(api.exportWorld).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("gm-retry-btn"));
    expect(await screen.findByTestId("region-marker-a")).toBeInTheDocument();
  });

  it("ending: asked first; then the banner, every write off, no end button, the record still there", async () => {
    (api.closeSession as Mock).mockResolvedValue({ ...OPEN, status: "closed" });
    (api.getTimeline as Mock).mockResolvedValue([line("l1", 1)]);
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("session-close-btn"));
    expect(api.closeSession).not.toHaveBeenCalled();
    (api.getSession as Mock).mockResolvedValue({ ...OPEN, status: "closed" });
    await act(async () => fireEvent.click(screen.getByTestId("session-close-confirm")));
    expect(await screen.findByTestId("gm-closed-banner")).toHaveTextContent(t("notice.sessionEnded"));
    expect(screen.queryByTestId("session-close-btn")).not.toBeInTheDocument();
    for (const id of ["advance-turn-btn", "suggest-events-btn", "generate-all-btn", "regen-all-btn"]) expect(screen.getByTestId(id)).toBeDisabled();
    await chooseRegion("a");
    expect(screen.getByTestId("distortion-slider")).toBeDisabled();
    openTab("timeline");
    expect(await screen.findByTestId("timeline")).toBeInTheDocument();
  });
});

describe("the region tab, events and refusals (moved from the GmHub tests)", () => {
  it("rumors with their badges in words; generating reads the region again; the original text is a toggle", async () => {
    (api.listRumors as Mock).mockResolvedValue([rumor("ru1", { promoted: true, origin_kind: "deed", statement_ko: "창고가 불탔대" })]);
    (api.generateRumors as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    await chooseRegion("a");
    const card = await screen.findByTestId("rumor-ru1");
    expect(within(card).getByTestId("promoted-ru1")).toHaveTextContent(t("label.settled"));
    expect(within(card).getByTestId("deed-badge-ru1")).toBeInTheDocument();
    expect(card).toHaveTextContent(numberWithMeaning("distortion", 0.42));
    expect(card).toHaveTextContent("창고가 불탔대");
    fireEvent.click(screen.getByTestId("rumor-text-ru1-toggle"));
    expect(card).toHaveTextContent("rumor ru1");
    const before = (api.listRumors as Mock).mock.calls.length;
    await act(async () => fireEvent.click(screen.getByTestId("generate-btn")));
    expect(api.generateRumors).toHaveBeenCalledWith("s1", "a");
    await waitFor(() => expect((api.listRumors as Mock).mock.calls.length).toBeGreaterThan(before));
  });

  it("the region's distortion and share come from the world state, in words; its summary line", async () => {
    renderGm();
    await ready();
    await chooseRegion("a");
    expect(screen.getByTestId("distortion-label")).toHaveTextContent(numberWithMeaning("distortion", 0.6));
    expect(screen.getByTestId("distortion-feedback")).toHaveTextContent(numberWithMeaning("share", 0.05));
    expect(screen.getByTestId("region-summary")).toHaveTextContent(t("label.rumorsGoing", { n: 2 }));
  });

  it("suggest, approve, discard, resolve call the server for this session", async () => {
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "suggested"), ev("e2", "suggested"), ev("e3", "active")]);
    for (const f of [api.suggestEvents, api.approveEvent, api.discardEvent, api.resolveEvent]) (f as Mock).mockResolvedValue({});
    renderGm();
    await ready();
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn")));
    expect(api.suggestEvents).toHaveBeenCalledWith("s1", 1);
    openTab("events");
    await act(async () => fireEvent.click(await screen.findByTestId("approve-e1")));
    await act(async () => fireEvent.click(screen.getByTestId("discard-e2")));
    await act(async () => fireEvent.click(screen.getByTestId("resolve-e3")));
    expect(api.approveEvent).toHaveBeenCalledWith("s1", "e1");
    expect(api.discardEvent).toHaveBeenCalledWith("s1", "e2");
    expect(api.resolveEvent).toHaveBeenCalledWith("s1", "e3");
  });

  it("a belief saved for a rumor that is gone says so and reads the region's rumors again (BR-V6-21)", async () => {
    (api.listRumors as Mock).mockResolvedValueOnce([rumor("ru1")]).mockResolvedValue([]);
    (api.setSupport as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"inactive","code":"rumor_inactive"}'));
    renderGm();
    await ready();
    await chooseRegion("a");
    const slider = await screen.findByTestId("support-ru1");
    fireEvent.change(slider, { target: { value: "0.9" } });
    expect(screen.getByTestId("support-label-ru1")).toHaveTextContent(numberWithMeaning("support", 0.9)); // UX-41
    await act(async () => fireEvent.pointerUp(slider));
    expect(await screen.findByTestId("gm-hub-error")).toHaveTextContent(t("error.rumor_inactive.title"));
    await waitFor(() => expect(screen.queryByTestId("rumor-ru1")).not.toBeInTheDocument());
    expect(screen.getByTestId("rumors-empty")).toBeInTheDocument();
  });

  it("a write refused because a turn runs says so and reads the player again", async () => {
    (api.advanceTurn as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"a turn","code":"turn_running"}'));
    renderGm();
    await ready();
    const before = (api.getPlayer as Mock).mock.calls.length;
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    expect(await screen.findByTestId("gm-hub-error")).toHaveTextContent(t("error.turn_running.title"));
    await waitFor(() => expect((api.getPlayer as Mock).mock.calls.length).toBeGreaterThan(before));
  });

  it("the world state is read with the overlay off too; the switch only paints (BR-V6-32)", async () => {
    renderGm();
    await ready();
    expect(await screen.findByTestId("region-badge-a")).toHaveTextContent("2 ✦1");
    fireEvent.click(screen.getByTestId("gm-state-toggle"));
    expect(screen.queryByTestId("region-badge-a")).not.toBeInTheDocument();
    await chooseRegion("a");
    expect(screen.getByTestId("region-summary")).toBeInTheDocument(); // still read
    expect(api.getWorldState).toHaveBeenCalledTimes(1);
  });
});
