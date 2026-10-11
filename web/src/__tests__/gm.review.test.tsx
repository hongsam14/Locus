// V6 code review 01: the findings the four review angles reproduced, now asserting the fixed
// behaviour (record construction/V6-gm-screen/code/reviews/code-review-01.md, # in each name).
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { StrictMode } from "react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { HttpError } from "../api/http";
import { resetCapabilities } from "../capabilities";
import { numberWithMeaning } from "../format";
import { t } from "../i18n";
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
const line = (id: string, turn: number, over: Partial<TimelineEntry> = {}): TimelineEntry => ({
  id, session_id: "s1", turn, kind: "promote", summary: id, payload: { region_id: "a", region_name: "Riverton" }, ...over,
});
const ev = (id: string, status: SessionEvent["status"], over: Partial<SessionEvent> = {}): SessionEvent => ({
  id, session_id: "s1", region_id: "b", category: "war", description: `event ${id}`, magnitude: 0.5, lifecycle: "persistent",
  status, created_turn: 1, contributions: {}, ...over,
});
const SEED = { seed: { id: "sd", world_id: "w", region_id: "a", title: "Blight", description: "", category: "plague" as const, magnitude: 0.5 },
  region_name: "Riverton", running_event_id: null as string | null };
const TURN = { session_id: "s1", turn: 4, promoted_ids: [], demoted_ids: [], applied_event_ids: [], resolved_event_ids: [], region_changes: [] };
function deferred<T>() {
  let resolve: (v: T) => void = () => {};
  let reject: (e: unknown) => void = () => {};
  const promise = new Promise<T>((r, j) => {
    resolve = r;
    reject = j;
  });
  return { promise, resolve, reject };
}

function reads() {
  (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
  (api.worldNames as Mock).mockImplementation(async (w: string) => ({ world_id: w, lang: "ko", world: { name: "W" }, regions: {}, npcs: {}, event_seeds: {} }));
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

beforeEach(() => {
  vi.clearAllMocks();
  resetCapabilities();
  clearToasts();
  window.matchMedia = ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia;
  reads();
});
afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  resetCapabilities();
});

function Toasts() {
  const toasts = useToasts();
  return <div data-testid="toast-text">{toasts.map((x) => `${x.key}|${x.title}|${x.body ?? ""}`).join("\n")}</div>;
}
function Go({ to }: { to: string }) {
  const navigate = useNavigate();
  return <button data-testid={`go-${to}`} onClick={() => navigate(`/gm/${to}`)}>go</button>;
}
function renderGm(path = "/gm/s1", strict = false) {
  const tree = (
    <MemoryRouter initialEntries={[path]}>
      <Go to="s1" />
      <Go to="s3" />
      <Toasts />
      <Routes>
        <Route path="/gm/:sessionId" element={<GmPage />} />
      </Routes>
    </MemoryRouter>
  );
  return render(strict ? <StrictMode>{tree}</StrictMode> : tree);
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
const rumorCalls = (sid: string, rid: string) => (api.listRumors as Mock).mock.calls.filter((c) => c[0] === sid && c[1] === rid).length;

describe("F1: the session list after [new session] (R-04)", () => {
  it("a new session stays in the picker after going back to the last one", async () => {
    (api.startSession as Mock).mockResolvedValue({ ...OPEN, id: "s9", turn: 0 });
    renderGm();
    await ready();
    const before = (api.listSessions as Mock).mock.calls.length;
    (api.listSessions as Mock).mockResolvedValue([OPEN, { ...OPEN, id: "s9", turn: 0 }]); // the server now has it
    await act(async () => fireEvent.click(screen.getByTestId("session-new-btn")));
    await waitFor(() => expect(screen.getByTestId("session-select")).toHaveValue("s9"));
    await ready();
    fireEvent.click(screen.getByTestId("go-s1"));
    await waitFor(() => expect(screen.getByTestId("session-select")).toHaveValue("s1"));
    await ready();
    expect((api.listSessions as Mock).mock.calls.length - before).toBeGreaterThanOrEqual(1);
    await waitFor(() =>
      expect(within(screen.getByTestId("session-select")).getAllByRole("option").map((o) => (o as HTMLOptionElement).value))
        .toEqual(expect.arrayContaining(["s1", "s9"])),
    );
  });
});

describe("F2: after(kind) uses the click-time region", () => {
  it("turn: a region chosen while the turn runs is read again after it", async () => {
    const hold = deferred<unknown>();
    (api.advanceTurn as Mock).mockReturnValue(hold.promise);
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("advance-turn-btn")); // no region chosen yet
    await chooseRegion("a");
    await waitFor(() => expect(rumorCalls("s1", "a")).toBe(1));
    await act(async () => hold.resolve(TURN));
    await screen.findByTestId("turn-band");
    await waitFor(() => expect(api.getTimeline).toHaveBeenCalledTimes(2)); // the turn's re-reads ran
    expect(rumorCalls("s1", "a")).toBe(2);
  });

  it("bulk: a region chosen while [generate all] runs is read again at the end", async () => {
    const hold = deferred<unknown>();
    (api.generateRumors as Mock).mockReturnValue(hold.promise); // target: region b (no canonical rumor)
    renderGm();
    await ready();
    await act(async () => fireEvent.click(screen.getByTestId("generate-all-btn")));
    await waitFor(() => expect(api.generateRumors).toHaveBeenCalledWith("s1", "b"));
    await chooseRegion("b");
    await waitFor(() => expect(rumorCalls("s1", "b")).toBe(1));
    await act(async () => hold.resolve([]));
    await waitFor(() => expect(screen.queryByTestId("generate-progress")).not.toBeInTheDocument());
    await waitFor(() => expect(api.getTimeline).toHaveBeenCalledTimes(2)); // the bulk's re-reads ran
    expect(rumorCalls("s1", "b")).toBe(2);
  });
});

describe("F3: the 'new' marks", () => {
  it("a line a GM write adds after the turn is not marked new", async () => {
    (api.getTimeline as Mock).mockResolvedValue([line("old1", 3)]);
    (api.advanceTurn as Mock).mockResolvedValue(TURN);
    (api.suggestEvents as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    openTab("timeline");
    await screen.findByTestId("timeline");
    (api.getTimeline as Mock).mockResolvedValue([line("old1", 3), line("new1", 4)]);
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    await screen.findByTestId("timeline-new-new1");
    (api.getTimeline as Mock).mockResolvedValue([line("old1", 3), line("new1", 4), line("gm1", 4, { kind: "event_suggested" })]);
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn")));
    await waitFor(() => expect(within(screen.getByTestId("timeline")).getAllByRole("listitem")).toHaveLength(3));
    expect(screen.queryByTestId("timeline-new-gm1")).not.toBeInTheDocument();
  });

  it("#23: a record still being read at the press is no snapshot — nothing is marked (R-07)", async () => {
    (api.getTimeline as Mock).mockResolvedValue([line("old1", 3)]);
    (api.advanceTurn as Mock).mockResolvedValue(TURN);
    (api.suggestEvents as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    openTab("timeline");
    await screen.findByTestId("timeline");
    const held = deferred<TimelineEntry[]>();
    (api.getTimeline as Mock).mockReturnValueOnce(held.promise);
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn"))); // before the turn
    (api.getTimeline as Mock).mockResolvedValue([line("old1", 3), line("gm0", 3, { kind: "event_suggested" }), line("new1", 4)]);
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn"))); // the suggest re-read is still out
    await screen.findByTestId("turn-band");
    await act(async () => held.resolve([line("old1", 3), line("gm0", 3, { kind: "event_suggested" })]));
    await waitFor(() => expect(within(screen.getByTestId("timeline")).getAllByRole("listitem")).toHaveLength(3));
    expect(screen.queryByTestId("timeline-new-gm0")).not.toBeInTheDocument();
    expect(screen.queryByTestId("timeline-new-new1")).not.toBeInTheDocument();
  });
});

describe("F4: a support patch cleared by an older rumors answer", () => {
  it("the saved belief stays after a rumors read that was sent before the save answers", async () => {
    (api.listRumors as Mock).mockResolvedValueOnce([rumor("ra")]);
    renderGm();
    await ready();
    await chooseRegion("a");
    const slider = await screen.findByTestId("support-ra");
    const held = deferred<SessionRumor[]>();
    (api.listRumors as Mock).mockReturnValueOnce(held.promise).mockResolvedValue([rumor("ra", { support: 0.8 })]);
    (api.generateRumors as Mock).mockResolvedValue([]);
    await act(async () => fireEvent.click(screen.getByTestId("generate-btn"))); // after("generate") reads the rumors again (held)
    await waitFor(() => expect(rumorCalls("s1", "a")).toBe(2));
    (api.setSupport as Mock).mockResolvedValue(rumor("ra", { support: 0.8 }));
    fireEvent.change(slider, { target: { value: "0.8" } });
    await act(async () => fireEvent.pointerUp(slider));
    await waitFor(() => expect(screen.getByTestId("support-label-ra")).toHaveTextContent(numberWithMeaning("support", 0.8)));
    await act(async () => held.resolve([rumor("ra", { support: 0.5 })])); // answered by the server before the save
    expect(screen.getByTestId("support-label-ra")).toHaveTextContent(numberWithMeaning("support", 0.8));
  });
});

describe("F5: another world's session — reads with the last world's region", () => {
  it("no rumors or knowledge read pairs the next session with a region of the last world", async () => {
    const next = deferred<GameSession>();
    (api.getSession as Mock).mockImplementation((sid: string) => (sid === "s1" ? Promise.resolve(OPEN) : next.promise));
    renderGm();
    await ready();
    await chooseRegion("a");
    fireEvent.click(screen.getByRole("button", { name: t("label.knows") }));
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalledWith("s1", "a"));
    fireEvent.click(screen.getByTestId("go-s3")); // s3 lives in world w2
    await screen.findByTestId("busy");
    await act(async () => {});
    expect({
      rumors: rumorCalls("s3", "a"),
      knowledge: (api.sessionKnowledge as Mock).mock.calls.filter((c) => c[0] === "s3").length,
    }).toEqual({ rumors: 0, knowledge: 0 });
    await act(async () => next.resolve({ ...OPEN, id: "s3", world_id: "w2" }));
  });
});

describe("F6: [regenerate all] with no world state", () => {
  it("#26: a failed state read is told on the error line, and nothing is sent", async () => {
    (api.getWorldState as Mock).mockRejectedValue(new TypeError("Failed to fetch"));
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("regen-all-btn"));
    await act(async () => fireEvent.click(screen.getByTestId("regen-all-confirm")));
    expect(await screen.findByTestId("gm-hub-error")).toHaveTextContent(t("error.network.title"));
    expect(api.regenRumors).not.toHaveBeenCalled();
    expect(screen.getByTestId("toast-text").textContent).not.toMatch(/gm:bulk/);
  });
});

describe("F7: StrictMode — the knowledge fold reads once more than it needs", () => {
  it("opening the fold sends how many knowledge reads", async () => {
    renderGm("/gm/s1", true);
    await ready();
    await chooseRegion("a");
    fireEvent.click(screen.getByRole("button", { name: t("label.knows") }));
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalled());
    await act(async () => {});
    expect((api.sessionKnowledge as Mock).mock.calls.length).toBe(2); // StrictMode's own double effect
  });
});

describe("F8: [check again] when the runs read fails", () => {
  it("keeps 'a turn runs' or says the check failed", async () => {
    (api.listTurnRuns as Mock).mockResolvedValue([{ id: "run1", session_id: "s1", status: "running" }]);
    renderGm();
    await ready();
    expect(await screen.findByTestId("gm-player-recheck")).toBeInTheDocument();
    (api.listTurnRuns as Mock).mockRejectedValue(new TypeError("Failed to fetch"));
    await act(async () => fireEvent.click(screen.getByTestId("gm-player-recheck")));
    await waitFor(() => expect(api.listTurnRuns).toHaveBeenCalledTimes(2));
    await act(async () => {});
    const status = screen.getByTestId("gm-player-status").textContent ?? "";
    const said = status.includes(t("label.turnRunning")) || screen.queryByTestId("gm-player-error") != null;
    expect({ status, said }).toEqual({ status, said: true });
  });
});

describe("writes (code review 01)", () => {
  it("#3: resolving a seed's event frees the seed", async () => {
    (api.listSeeds as Mock).mockResolvedValue([{ ...SEED, running_event_id: "e1" }]);
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "active", { region_id: "a" })]);
    (api.resolveEvent as Mock).mockResolvedValue(ev("e1", "resolved"));
    renderGm();
    await ready();
    openTab("events");
    (api.listSeeds as Mock).mockResolvedValue([{ ...SEED, running_event_id: null }]);
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "resolved", { region_id: "a", resolved_turn: 3 })]);
    await act(async () => fireEvent.click(await screen.findByTestId("resolve-e1")));
    openTab("seeds");
    expect(await screen.findByTestId("seed-start-sd")).toBeEnabled();
    expect(screen.queryByTestId("seed-running-sd")).not.toBeInTheDocument();
  });

  it("#7: [make rumors for empty regions] waits while the region's own write runs", async () => {
    const hold = deferred<unknown>();
    (api.generateRumors as Mock).mockReturnValueOnce(hold.promise).mockResolvedValue([]);
    renderGm();
    await ready();
    await chooseRegion("b");
    await waitFor(() => expect(screen.getByTestId("generate-btn")).toBeEnabled());
    fireEvent.click(screen.getByTestId("generate-btn"));
    await waitFor(() => expect(screen.getByTestId("generate-all-btn")).toBeDisabled());
    expect(screen.getByTestId("regen-all-btn")).toBeDisabled();
    await act(async () => hold.resolve([]));
    await waitFor(() => expect(screen.getByTestId("generate-all-btn")).toBeEnabled());
    expect((api.generateRumors as Mock).mock.calls.filter((c) => c[1] === "b")).toHaveLength(1);
  });

  it("#29: after a saved approve the card stays off until the events are read again", async () => {
    const reread = deferred<SessionEvent[]>();
    (api.listEvents as Mock).mockResolvedValueOnce([ev("e1", "suggested")]).mockReturnValue(reread.promise);
    (api.approveEvent as Mock).mockResolvedValue(ev("e1", "active"));
    renderGm();
    await ready();
    openTab("events");
    await act(async () => fireEvent.click(await screen.findByTestId("approve-e1")));
    expect(screen.getByTestId("discard-e1")).toBeDisabled();
    fireEvent.click(screen.getByTestId("discard-e1"));
    expect(api.discardEvent).not.toHaveBeenCalled();
    await act(async () => reread.resolve([ev("e1", "active")]));
    expect(await screen.findByTestId("resolve-e1")).toBeEnabled();
  });

  it("#30: a 404 reads the events again, so the gone card goes", async () => {
    (api.listEvents as Mock).mockResolvedValueOnce([ev("e1", "suggested")]).mockResolvedValue([]);
    (api.approveEvent as Mock).mockRejectedValue(new HttpError(404, "Not Found", '{"detail":"event not found: e1","code":"not_found"}'));
    renderGm();
    await ready();
    openTab("events");
    await act(async () => fireEvent.click(await screen.findByTestId("approve-e1")));
    expect(await screen.findByTestId("gm-hub-error")).toHaveTextContent(t("error.not_found.title"));
    await waitFor(() => expect(screen.queryByTestId("event-e1")).not.toBeInTheDocument());
  });

  it("#31: a dialog write that succeeds clears the last write's error line", async () => {
    (api.advanceTurn as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"a turn","code":"turn_running"}'));
    (api.closeSession as Mock).mockResolvedValue({ ...OPEN, status: "closed" });
    renderGm();
    await ready();
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    expect(await screen.findByTestId("gm-hub-error")).toHaveTextContent(t("error.turn_running.title"));
    (api.getSession as Mock).mockImplementation(async (sid: string) => ({ ...OPEN, id: sid, status: "closed" }));
    fireEvent.click(screen.getByTestId("session-close-btn"));
    await act(async () => fireEvent.click(screen.getByTestId("session-close-confirm")));
    await screen.findByTestId("gm-closed-banner");
    expect(screen.queryByTestId("gm-hub-error")).not.toBeInTheDocument();
  });

  it("#32: [make rumors for empty regions] with no target clears the error line and says so", async () => {
    (api.advanceTurn as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"busy","code":"gm_busy"}'));
    (api.getWorldState as Mock).mockResolvedValue(state({ regions: [
      { region_id: "a", region_name: "Riverton", distortion: 0.6, feedback_share: 0, active_rumors: 2, promoted_rumors: 0, deed_rumors: 0, active_events: 0 },
    ] }));
    renderGm();
    await ready();
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    expect(await screen.findByTestId("gm-hub-error")).toBeInTheDocument();
    await act(async () => fireEvent.click(screen.getByTestId("generate-all-btn")));
    await waitFor(() => expect(screen.getByTestId("toast-text").textContent).toContain(t("notif.noTargets")));
    expect(screen.queryByTestId("gm-hub-error")).not.toBeInTheDocument();
  });

  it("#34: two presses in one tick run [make rumors for empty regions] once", async () => {
    (api.generateRumors as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    const gen = screen.getByTestId("generate-all-btn");
    const before = (api.getWorldState as Mock).mock.calls.length;
    await act(async () => {
      gen.click();
      gen.click();
    });
    await waitFor(() => expect((api.generateRumors as Mock).mock.calls.filter((c) => c[1] === "b")).toHaveLength(1));
    expect((api.getWorldState as Mock).mock.calls.length - before).toBeLessThanOrEqual(2); // one pre-scan (+ the re-read)
  });

  it("#34: two presses of the regenerate-all confirm run it once", async () => {
    (api.regenRumors as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("regen-all-btn"));
    const confirm = screen.getByTestId("regen-all-confirm");
    await act(async () => {
      confirm.click();
      confirm.click();
    });
    await waitFor(() => expect(api.regenRumors).toHaveBeenCalledTimes(2)); // 2 regions, one run
    await new Promise((r) => setTimeout(r, 30));
    expect(api.regenRumors).toHaveBeenCalledTimes(2);
  });

  it("#35: while the GM's own turn runs, the other writes wait", async () => {
    const hold = deferred<unknown>();
    (api.advanceTurn as Mock).mockReturnValue(hold.promise);
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "suggested")]);
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("advance-turn-btn"));
    for (const id of ["suggest-events-btn", "generate-all-btn", "regen-all-btn", "session-new-btn", "session-close-btn"])
      expect(screen.getByTestId(id), id).toBeDisabled();
    openTab("events");
    expect(await screen.findByTestId("approve-e1")).toBeDisabled();
    await act(async () => hold.resolve(TURN));
    await waitFor(() => expect(screen.getByTestId("suggest-events-btn")).toBeEnabled());
  });

  it("#2: a saved belief keeps the rumor's Korean line", async () => {
    (api.listRumors as Mock).mockResolvedValue([{ ...rumor("ru1"), statement_ko: "강에 괴물이 산다" } as SessionRumor]);
    (api.setSupport as Mock).mockResolvedValue({ ...rumor("ru1", { support: 0.8 }), statement_ko: null });
    renderGm();
    await ready();
    await chooseRegion("a");
    expect(await screen.findByTestId("rumor-text-ru1")).toHaveTextContent("강에 괴물이 산다");
    const slider = screen.getByTestId("support-ru1");
    fireEvent.change(slider, { target: { value: "0.8" } });
    await act(async () => fireEvent.pointerUp(slider));
    await waitFor(() => expect(api.setSupport).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("rumor-text-ru1")).toHaveTextContent("강에 괴물이 산다");
  });

  it("#33: an open 'what the NPCs know' is read again after a bulk run too", async () => {
    (api.generateRumors as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    await chooseRegion("b");
    fireEvent.click(screen.getByRole("button", { name: t("label.knows") }));
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalledTimes(1));
    await act(async () => fireEvent.click(screen.getByTestId("generate-all-btn")));
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalledTimes(2));
  });
});

describe("focus and keyboard (code review 01)", () => {
  const focused = () => document.activeElement?.getAttribute("data-testid");

  it("#1: ending a session leaves the focus on the ended-session line, not <body>", async () => {
    (api.closeSession as Mock).mockResolvedValue({ ...OPEN, status: "closed" });
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("session-close-btn"));
    (api.getSession as Mock).mockImplementation(async (sid: string) => ({ ...OPEN, id: sid, status: "closed" }));
    await act(async () => fireEvent.click(screen.getByTestId("session-close-confirm")));
    await waitFor(() => expect(focused()).toBe("gm-closed-banner"));
  });

  it("#1: voiding a deed leaves the focus on its card", async () => {
    const deed = { id: "d1", session_id: "s1", player_id: "p", region_id: "a", turn: 0, kind: "arrival", text: "Ari came.",
      witnessed_npc_ids: [], voided: false, region_name: "A", witness_names: [] };
    (api.listDeeds as Mock).mockResolvedValueOnce([{ deed, appraisals: [], rumors: [], reached_region_ids: [], reached_region_names: [] }])
      .mockResolvedValue([{ deed: { ...deed, voided: true }, appraisals: [], rumors: [], reached_region_ids: [], reached_region_names: [] }]);
    (api.voidDeed as Mock).mockResolvedValue({ deed_id: "d1", deactivated_rumor_ids: [] });
    renderGm();
    await ready();
    openTab("deeds");
    fireEvent.click(await screen.findByTestId("void-d1"));
    await act(async () => fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("deed.voidConfirmBtn") })));
    await waitFor(() => expect(focused()).toBe("deed-d1"));
  });

  it("#1: confirming [remake every region's rumors] leaves the focus on the progress line", async () => {
    const hold = deferred<unknown>();
    (api.regenRumors as Mock).mockReturnValue(hold.promise);
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("regen-all-btn"));
    await act(async () => fireEvent.click(screen.getByTestId("regen-all-confirm")));
    await waitFor(() => expect(focused()).toBe("generate-progress"));
    await act(async () => hold.resolve([]));
  });

  it("#8: an approved card leaves the focus on the group it moved to; a closed band hands it to [advance]", async () => {
    (api.listEvents as Mock).mockResolvedValueOnce([{ id: "e1", session_id: "s1", region_id: "b", category: "war", description: "x",
      magnitude: 0.5, lifecycle: "persistent", status: "suggested", created_turn: 1, contributions: {} }])
      .mockResolvedValue([{ id: "e1", session_id: "s1", region_id: "b", category: "war", description: "x",
        magnitude: 0.5, lifecycle: "persistent", status: "active", created_turn: 1, contributions: {} }]);
    (api.approveEvent as Mock).mockResolvedValue({});
    (api.advanceTurn as Mock).mockResolvedValue(TURN);
    renderGm();
    await ready();
    openTab("events");
    await act(async () => fireEvent.click(await screen.findByTestId("approve-e1")));
    await waitFor(() => expect(screen.getByTestId("events-active")).toContainElement(screen.getByTestId("event-e1")));
    expect(focused()).toBe("events-active");
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    fireEvent.click(await screen.findByTestId("turn-band-close"));
    await waitFor(() => expect(focused()).toBe("advance-turn-btn"));
  });

  it("#8: an event card's region name hands the focus to the region's heading", async () => {
    (api.listEvents as Mock).mockResolvedValue([{ id: "e1", session_id: "s1", region_id: "b", category: "war", description: "x",
      magnitude: 0.5, lifecycle: "persistent", status: "active", created_turn: 1, contributions: {} }]);
    renderGm();
    await ready();
    openTab("events");
    fireEvent.click(await screen.findByTestId("event-region-e1"));
    await waitFor(() => expect(focused()).toBe("region-heading"));
  });

  it("#9: the picker moves nowhere until [open]; the next session's picker has the focus", async () => {
    (api.listSessions as Mock).mockResolvedValue([OPEN, { ...OPEN, id: "s2", turn: 1 }]);
    renderGm();
    await ready();
    const select = screen.getByTestId("session-select");
    await waitFor(() => expect(within(select).getAllByRole("option").length).toBe(2));
    fireEvent.change(select, { target: { value: "s2" } });
    expect(api.getSession).not.toHaveBeenCalledWith("s2");
    fireEvent.click(screen.getByTestId("session-open-btn"));
    await waitFor(() => expect(api.getSession).toHaveBeenCalledWith("s2"));
    await ready();
    await waitFor(() => expect(focused()).toBe("session-select"));
  });

  it("#10: any region can be chosen without the map", async () => {
    renderGm();
    await ready();
    const picker = await screen.findByTestId("region-select");
    fireEvent.change(picker, { target: { value: "b" } });
    expect(await screen.findByTestId("region-heading")).toHaveTextContent("Hollow");
    expect(screen.getByTestId("region-select")).toHaveValue("b");
  });

  it("#44: the knowledge fold says how much is known once read; the map picture says it stays here", async () => {
    (api.sessionKnowledge as Mock).mockResolvedValue({ world_id: "w", region_id: "a", shared_ids: [], unique_ids: [],
      items: [{ knowledge_id: "k1", statement: "x", scope_type: "direct", is_hearsay: false, confidence: 0.6 }] });
    renderGm();
    await ready();
    expect(screen.getByText(t("hint.mapPictureLocal"))).toBeInTheDocument();
    await chooseRegion("a");
    fireEvent.click(screen.getByRole("button", { name: t("label.knows") }));
    expect(await screen.findByRole("button", { name: t("label.knowsCount", { n: 1 }) })).toBeInTheDocument();
  });
});

describe("test gaps (code review 01 #14–#20, #47)", () => {
  const evs = (n: number, status: SessionEvent["status"]) =>
    Array.from({ length: n }, (_, i) => ev(`r${i}`, status, { resolved_turn: i, description: `old ${i}` }));

  it("#14: [remake every region's rumors] remakes every region of the state, after asking", async () => {
    (api.regenRumors as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    fireEvent.click(screen.getByTestId("regen-all-btn"));
    expect(api.regenRumors).not.toHaveBeenCalled();
    await act(async () => fireEvent.click(screen.getByTestId("regen-all-confirm")));
    await waitFor(() => expect(api.regenRumors).toHaveBeenCalledTimes(2));
    expect((api.regenRumors as Mock).mock.calls).toEqual(expect.arrayContaining([["s1", "a"], ["s1", "b"]]));
  });

  it("#15: a tab whose first read fails says so with [retry], and retry shows it", async () => {
    (api.listEvents as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue([ev("e1", "active")]);
    (api.getTimeline as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue([line("l1", 1)]);
    renderGm();
    await ready();
    openTab("events");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(t("error.network.title"));
    fireEvent.click(within(alert).getByRole("button", { name: t("action.retry") }));
    expect(await screen.findByTestId("event-e1")).toBeInTheDocument();
    openTab("timeline");
    fireEvent.click(within(await screen.findByRole("alert")).getByRole("button", { name: t("action.retry") }));
    expect(await screen.findByTestId("timeline")).toBeInTheDocument();
  });

  it("#18: while a bulk run goes, the head, the seeds and the region's writes wait", async () => {
    const hold = deferred<unknown>();
    (api.generateRumors as Mock).mockReturnValue(hold.promise);
    (api.listSeeds as Mock).mockResolvedValue([SEED]);
    renderGm();
    await ready();
    await chooseRegion("b");
    await act(async () => fireEvent.click(screen.getByTestId("generate-all-btn")));
    await waitFor(() => expect(api.generateRumors).toHaveBeenCalled());
    for (const id of ["session-new-btn", "session-close-btn", "generate-btn", "regen-btn", "regen-all-btn", "advance-turn-btn"])
      expect(screen.getByTestId(id), id).toBeDisabled();
    openTab("seeds");
    expect(await screen.findByTestId("seed-start-sd")).toBeDisabled();
    await act(async () => hold.resolve([]));
  });

  it("#19: an ended session turns every write off — events, deeds, beliefs, rumors", async () => {
    (api.getSession as Mock).mockImplementation(async (sid: string) => ({ ...OPEN, id: sid, status: "closed" }));
    (api.listEvents as Mock).mockResolvedValue([ev("e1", "suggested"), ev("e2", "active")]);
    (api.listRumors as Mock).mockResolvedValue([rumor("ra")]);
    const deed = { id: "d1", session_id: "s1", player_id: "p", region_id: "a", turn: 0, kind: "arrival", text: "x",
      witnessed_npc_ids: [], voided: false, region_name: "A", witness_names: [] };
    (api.listDeeds as Mock).mockResolvedValue([{ deed, appraisals: [], rumors: [], reached_region_ids: [], reached_region_names: [] }]);
    renderGm();
    await screen.findByTestId("gm-closed-banner");
    await chooseRegion("a");
    for (const id of ["generate-btn", "regen-btn", "support-ra", "distortion-slider"]) expect(await screen.findByTestId(id), id).toBeDisabled();
    openTab("events");
    for (const id of ["approve-e1", "discard-e1", "resolve-e2"]) expect(await screen.findByTestId(id), id).toBeDisabled();
    openTab("deeds");
    expect(await screen.findByTestId("void-d1")).toBeDisabled();
  });

  it("#20: the next write clears the error line; a saved belief shows the saved value, not the dragged one", async () => {
    (api.suggestEvents as Mock).mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":"x","code":"gm_busy"}')).mockResolvedValue([]);
    (api.listRumors as Mock).mockResolvedValueOnce([rumor("ra")]).mockResolvedValue([rumor("ra", { support: 0.85 })]);
    (api.setSupport as Mock).mockResolvedValue(rumor("ra", { support: 0.85 }));
    renderGm();
    await ready();
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn")));
    expect(await screen.findByTestId("gm-hub-error")).toBeInTheDocument();
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn")));
    await waitFor(() => expect(screen.queryByTestId("gm-hub-error")).not.toBeInTheDocument());
    await chooseRegion("a");
    const slider = await screen.findByTestId("support-ra");
    fireEvent.change(slider, { target: { value: "0.9" } });
    await act(async () => fireEvent.pointerUp(slider));
    await waitFor(() => expect(screen.getByTestId("support-label-ra")).toHaveTextContent(numberWithMeaning("support", 0.85)));
  });

  it("#47 P1: a session of another world drops the chosen region", async () => {
    (api.getSession as Mock).mockImplementation(async (sid: string) => ({ ...OPEN, id: sid, world_id: sid === "s3" ? "w2" : "w" }));
    (api.exportWorld as Mock).mockImplementation(async (w: string) => (w === "w2" ? { ...WORLD, world_id: "w2",
      regions: [{ id: "z", name: "Zeal", level: "town" }] } : WORLD));
    renderGm();
    await ready();
    await chooseRegion("a");
    fireEvent.click(screen.getByTestId("go-s3"));
    await ready();
    await screen.findByTestId("region-marker-z");
    expect(screen.queryByTestId("region-heading")).not.toBeInTheDocument();
    expect(screen.getByTestId("gm-no-region")).toBeInTheDocument();
  });

  it("#47 RK1/RT2: what the NPCs know is read again in place after a write, not remounted", async () => {
    (api.generateRumors as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    await chooseRegion("a");
    fireEvent.click(screen.getByRole("button", { name: t("label.knows") }));
    const panel = await screen.findByTestId("region-panel");
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalledTimes(1));
    await act(async () => fireEvent.click(screen.getByTestId("generate-btn")));
    await waitFor(() => expect(api.sessionKnowledge).toHaveBeenCalledTimes(2));
    expect(screen.getByTestId("region-panel")).toBe(panel);
  });

  it("#47 V10: in one column a region named in the band brings its tab into focus", async () => {
    (api.advanceTurn as Mock).mockResolvedValue({ ...TURN, region_changes: [{ region_id: "a", region_name: "Riverton", promoted: ["x"],
      demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: [] }] });
    renderGm();
    await ready();
    await act(async () => fireEvent.click(screen.getByTestId("advance-turn-btn")));
    fireEvent.click(await screen.findByTestId("turn-band-region-a"));
    await waitFor(() => expect(document.activeElement?.querySelector('[data-testid="gm-tab-region"]')).not.toBeNull());
  });

  it("#47 EP1/EP2/TL1: ended events newest first, ten at a time; [more] says how many", async () => {
    (api.listEvents as Mock).mockResolvedValue(evs(12, "resolved"));
    (api.getTimeline as Mock).mockResolvedValue(Array.from({ length: 25 }, (_, i) => line(`l${i}`, i)));
    renderGm();
    await ready();
    openTab("events");
    fireEvent.click(await screen.findByRole("button", { name: new RegExp(t("label.eventsResolved")) }));
    const cards = () => within(screen.getByTestId("events-resolved")).getAllByTestId(/^event-r\d+$/);
    await waitFor(() => expect(cards()).toHaveLength(10));
    expect(cards()[0]).toHaveTextContent("old 11");
    fireEvent.click(screen.getByTestId("events-more"));
    expect(cards()).toHaveLength(12);
    openTab("timeline");
    expect(await screen.findByTestId("timeline-more")).toHaveTextContent(t("action.showMore", { n: 5 }));
  });

  it("#47 DS2/RT1/V12: no share line at 0; a region's slider draft does not carry over; the suggestion count stays under the cap", async () => {
    (api.getWorldState as Mock).mockResolvedValue(state({ max_event_suggestions: 2, regions: [
      { region_id: "a", region_name: "Riverton", distortion: 0.3, feedback_share: 0, active_rumors: 1, promoted_rumors: 0, deed_rumors: 0, active_events: 0 },
      { region_id: "b", region_name: "Hollow", distortion: 0.7, feedback_share: 0, active_rumors: 0, promoted_rumors: 0, deed_rumors: 0, active_events: 0 },
    ] }));
    (api.suggestEvents as Mock).mockResolvedValue([]);
    renderGm();
    await ready();
    await chooseRegion("a");
    expect(screen.queryByTestId("distortion-feedback")).not.toBeInTheDocument();
    fireEvent.change(screen.getByTestId("distortion-slider"), { target: { value: "0.9" } }); // dragged, not saved
    fireEvent.click(screen.getByTestId("region-marker-b"));
    await waitFor(() => expect(screen.getByTestId("distortion-label")).toHaveTextContent(numberWithMeaning("distortion", 0.7)));
    expect(within(screen.getByTestId("suggest-n")).getAllByRole("option")).toHaveLength(2);
    await act(async () => fireEvent.click(screen.getByTestId("suggest-events-btn")));
    expect(api.suggestEvents).toHaveBeenCalledWith("s1", 1);
  });

  it("#47 DP2: a witness with no name in the map keeps the name the deed carries", async () => {
    const deed = { id: "d1", session_id: "s1", player_id: "p", region_id: "a", turn: 0, kind: "arrival", text: "x",
      witnessed_npc_ids: ["n1"], voided: false, region_name: "A", witness_names: ["Mara"] };
    (api.listDeeds as Mock).mockResolvedValue([{ deed, appraisals: [], rumors: [], reached_region_ids: [], reached_region_names: [] }]);
    renderGm();
    await ready();
    openTab("deeds");
    expect(await screen.findByTestId("deed-witnesses-d1")).toHaveTextContent("Mara");
  });
});

describe("missed mutants of the fixes", () => {
  it("#12: with no names in the map, the title is the world file's name, not its id", async () => {
    (api.worldNames as Mock).mockResolvedValue({ world_id: "w", lang: "en", world: {}, regions: {}, npcs: {}, event_seeds: {} });
    (api.exportWorld as Mock).mockResolvedValue({ ...WORLD, world: { id: "w", name: "Emberleaf Isle" } });
    renderGm();
    await ready();
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Emberleaf Isle");
  });

  it("#29: a started seed stays off until the seeds are read again", async () => {
    const reread = deferred<unknown>();
    (api.listSeeds as Mock).mockResolvedValueOnce([SEED]).mockReturnValue(reread.promise);
    (api.startSeed as Mock).mockResolvedValue(ev("e9", "active"));
    renderGm();
    await ready();
    openTab("seeds");
    await act(async () => fireEvent.click(await screen.findByTestId("seed-start-sd")));
    expect(screen.getByTestId("seed-start-sd")).toBeDisabled();
    await act(async () => reread.resolve([{ ...SEED, running_event_id: "e9" }]));
    expect(await screen.findByTestId("seed-running-sd")).toBeInTheDocument();
  });
});
