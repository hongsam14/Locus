// V6 GM data hooks (code plan Step 3, TP-V6-4/6/7/8, § 1.1 R-02/R-03/R-04/R-07/R-10): what
// each write reads again, answers of another key never shown, a bulk run that stops, and
// the session read with its world, names and list.
import { act, renderHook, waitFor } from "@testing-library/react";
import { HttpError } from "../api/http";
import { snapshotIds, newLineIds } from "../features/gm/newLines";
import { sessionLabel, sessionOptions } from "../features/gm/sessionLabel";
import { useBulkRumors } from "../features/gm/useBulkRumors";
import { AFTER, useGmData, type GmWrite } from "../features/gm/useGmData";
import { useGmSession } from "../features/gm/useGmSession";
import { dicts, t } from "../i18n";
import type { GameSession, SessionRumor, TimelineEntry, WorldState } from "../types";

vi.mock("../api", () => ({
  api: {
    getSession: vi.fn(),
    exportWorld: vi.fn(),
    listSessions: vi.fn(),
    worldNames: vi.fn(),
    listEvents: vi.fn(),
    getTimeline: vi.fn(),
    getWorldState: vi.fn(),
    listRumors: vi.fn(),
    listSeeds: vi.fn(),
    listDeeds: vi.fn(),
    getPlayer: vi.fn(),
    listTurnRuns: vi.fn(),
    generateRumors: vi.fn(),
    regenRumors: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;
const READS = ["listEvents", "getTimeline", "getWorldState", "listRumors", "listSeeds", "listDeeds", "getPlayer", "listTurnRuns"] as const;

const state = (regions: Partial<WorldState["regions"][number]>[] = []): WorldState => ({
  session_id: "s1",
  turn: 3,
  player_region_id: null,
  regions: regions.map((r, i) => ({
    region_id: `r${i}`, region_name: `R${i}`, distortion: 0.3, feedback_share: 0, active_rumors: 0,
    promoted_rumors: 0, deed_rumors: 0, active_events: 0, ...r,
  })),
});
const rumor = (id: string, support = 0.5): SessionRumor =>
  ({ id, session_id: "s1", region_id: "a", statement: id, support, distortion_degree: 0.2 }) as SessionRumor;
const line = (id: string, turn = 1): TimelineEntry => ({ id, session_id: "s1", turn, kind: "x", summary: id, payload: {} });

function deferred<T>() {
  let resolve: (v: T) => void = () => {};
  let reject: (e: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.listEvents as Mock).mockResolvedValue([]);
  (api.getTimeline as Mock).mockResolvedValue([]);
  (api.getWorldState as Mock).mockResolvedValue(state([{}]));
  (api.listRumors as Mock).mockResolvedValue([]);
  (api.listSeeds as Mock).mockResolvedValue([]);
  (api.listDeeds as Mock).mockResolvedValue([]);
  (api.getPlayer as Mock).mockResolvedValue({ id: "p", session_id: "s1", name: "Arin", region_id: "a", turns_spent: 0 });
  (api.listTurnRuns as Mock).mockResolvedValue([]);
});

// BLM § 3 written out apart from AFTER, so the test does not read the code's own table
const EXPECTED: Record<GmWrite, string[]> = {
  turn: ["session", "sessions", "getWorldState", "listEvents", "getTimeline", "listRumors", "listSeeds", "listDeeds", "getPlayer", "knowledge"],
  suggest: ["listEvents", "getTimeline"],
  approve: ["listEvents", "getTimeline", "getWorldState"],
  discard: ["listEvents", "getTimeline"],
  resolve: ["listEvents", "getTimeline", "getWorldState", "listRumors"],
  create: ["listEvents", "getTimeline", "getWorldState"],
  seed: ["listSeeds", "listEvents", "getTimeline", "getWorldState"],
  distortion: ["getWorldState", "getTimeline"],
  support: ["getTimeline"],
  generate: ["listRumors", "getWorldState", "getTimeline", "knowledge"],
  regen: ["listRumors", "getWorldState", "getTimeline", "knowledge"],
  bulk: ["getWorldState", "listRumors", "getTimeline"],
  void: ["listDeeds", "listRumors", "getWorldState", "getTimeline", "knowledge"],
  close: ["session", "sessions"],
};

describe("TP-V6-4: a write reads again only what it changed", () => {
  it("the table has the 14 writes of the code plan", () => {
    expect(Object.keys(AFTER).sort()).toEqual(Object.keys(EXPECTED).sort());
    expect(Object.keys(AFTER)).toHaveLength(14);
  });

  it.each(Object.keys(EXPECTED) as GmWrite[])("%s", async (kind) => {
    const session = vi.fn();
    const sessions = vi.fn();
    const { result } = renderHook(() => useGmData("s1", "a", { session, sessions }));
    await waitFor(() => expect(result.current.deeds.state).toBe("ready"));
    await waitFor(() => expect(result.current.rumors.state).toBe("ready"));
    for (const name of READS) (api[name] as Mock).mockClear();
    const rev = result.current.knowledgeRev;
    act(() => result.current.after(kind));
    // the screen keeps what it shows while it reads again (BR-V6-10)
    for (const name of ["events", "timeline", "worldState", "rumors", "seeds", "deeds", "player"] as const)
      expect(result.current[name].state, name).toBe("ready");
    await waitFor(() => {
      const called = READS.filter((name) => (api[name] as Mock).mock.calls.length > 0 && name !== "listTurnRuns");
      if (session.mock.calls.length) called.push("session" as never);
      if (sessions.mock.calls.length) called.push("sessions" as never);
      if (result.current.knowledgeRev !== rev) called.push("knowledge" as never);
      expect(called.sort()).toEqual([...EXPECTED[kind]].sort());
    });
  });
});

describe("TP-V6-6 (hooks): an answer for another key is never shown (§ 1.1 R-02)", () => {
  it("the last session's late answer does not land on the next session", async () => {
    const late = deferred<unknown[]>();
    (api.listEvents as Mock).mockImplementation((sid: string) => (sid === "s1" ? late.promise : new Promise(() => {})));
    const { result, rerender } = renderHook(({ sid }) => useGmData(sid, null), { initialProps: { sid: "s1" } });
    rerender({ sid: "s2" });
    await act(async () => late.resolve([{ id: "e-old" }]));
    expect(result.current.events.data).toBeUndefined();
    expect(result.current.events.state).toBe("loading");
  });

  it("another region's rumors are gone while the next region reads", async () => {
    const b = deferred<SessionRumor[]>();
    (api.listRumors as Mock).mockImplementation((_s: string, region: string) =>
      region === "a" ? Promise.resolve([rumor("ra")]) : b.promise,
    );
    const { result, rerender } = renderHook(({ region }) => useGmData("s1", region), { initialProps: { region: "a" } });
    await waitFor(() => expect(result.current.rumorList?.map((r) => r.id)).toEqual(["ra"]));
    rerender({ region: "b" });
    expect(result.current.rumorList).toBeUndefined();
    expect(result.current.rumors.state).toBe("loading");
    await act(async () => b.resolve([rumor("rb")]));
    expect(result.current.rumorList?.map((r) => r.id)).toEqual(["rb"]);
  });
});

describe("§ 1.1 R-03: a write's own answer at once, then the next read", () => {
  it("a saved support shows before the re-read and the re-read clears the layer", async () => {
    (api.listRumors as Mock).mockResolvedValueOnce([rumor("r1", 0.5)]);
    const { result } = renderHook(() => useGmData("s1", "a"));
    await waitFor(() => expect(result.current.rumorList?.[0].support).toBe(0.5));
    act(() => result.current.patchRumor(rumor("r1", 0.9)));
    expect(result.current.rumorList?.[0].support).toBe(0.9);
    (api.listRumors as Mock).mockResolvedValueOnce([rumor("r1", 0.8)]);
    act(() => result.current.after("support")); // support reads the timeline only
    act(() => result.current.rumors.reload());
    await waitFor(() => expect(result.current.rumorList?.[0].support).toBe(0.8));
  });

  it("a saved distortion shows at once for that region", async () => {
    (api.getWorldState as Mock).mockResolvedValue(state([{ distortion: 0.3 }]));
    const { result } = renderHook(() => useGmData("s1", "r0"));
    await waitFor(() => expect(result.current.regionState("r0")?.distortion).toBe(0.3));
    act(() => result.current.patchDistortion({ session_id: "s1", region_id: "r0", distortion_degree: 0.7, feedback_share: 0.05 }));
    expect(result.current.regionState("r0")).toEqual({ distortion: 0.7, feedback_share: 0.05 });
  });

  it("a failed re-read of the player keeps the last one and says so", async () => {
    const { result } = renderHook(() => useGmData("s1", null));
    await waitFor(() => expect(result.current.player.data?.player?.name).toBe("Arin"));
    (api.getPlayer as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    act(() => result.current.player.reload());
    await waitFor(() => expect(result.current.player.error?.code).toBe("network"));
    expect(result.current.player.data?.player?.name).toBe("Arin");
    expect(result.current.player.state).toBe("ready");
  });

  it("only a 404 means no player", async () => {
    (api.getPlayer as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", "no player"));
    const { result } = renderHook(() => useGmData("s1", null));
    await waitFor(() => expect(result.current.player.state).toBe("ready"));
    expect(result.current.player.data?.player).toBeNull();
  });
});

describe("TP-V6-7: a bulk run counts why it failed and stops (§ 1.1 R-06)", () => {
  const llm = () => new HttpError(503, "Service Unavailable", '{"detail":"no key","code":"llm_unavailable"}');
  const closed = () => new HttpError(409, "Conflict", '{"detail":"closed","code":"session_closed"}');
  const busy = () => new HttpError(409, "Conflict", '{"detail":"held","code":"gm_busy"}');
  const setup = () => {
    const notify = vi.fn();
    const onError = vi.fn();
    const onClosed = vi.fn();
    const after = vi.fn().mockResolvedValue(undefined);
    const hook = renderHook(() =>
      useBulkRumors("s1", { notify, fail: vi.fn(), after, onCap: vi.fn(), onError, onClosed }),
    );
    return { hook, notify, onError, onClosed, after };
  };

  it("no LLM and busy are counted apart; a run that needed the LLM every time says so", async () => {
    (api.regenRumors as Mock).mockRejectedValueOnce(llm()).mockRejectedValueOnce(busy()).mockResolvedValue([]);
    const { hook, notify, onError } = setup();
    await act(async () => hook.result.current.regenAll(["a", "b", "c", "d"]));
    const body = notify.mock.calls[0][0].body as string;
    expect(body).toContain(t("progress.done", { done: 2, total: 4 }));
    expect(body).toContain(t("progress.noLlm", { n: 1 }));
    expect(body).toContain(t("progress.busy", { n: 1 }));
    expect(onError).toHaveBeenLastCalledWith(null);
    (api.regenRumors as Mock).mockReset().mockRejectedValue(llm());
    await act(async () => hook.result.current.regenAll(["a", "b"]));
    expect(onError).toHaveBeenLastCalledWith(expect.objectContaining({ title: dicts.ko["error.llm_unavailable.title"] }));
  });

  it("the first 'session closed' stops the run and tells the page", async () => {
    let calls = 0;
    (api.regenRumors as Mock).mockImplementation(async () => {
      calls += 1;
      if (calls === 1) throw closed();
      return [];
    });
    const { hook, onClosed, onError } = setup();
    await act(async () => hook.result.current.regenAll(Array.from({ length: 12 }, (_, i) => `r${i}`)));
    expect(calls).toBeLessThanOrEqual(5); // the first five were already out; none after
    expect(onClosed).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenLastCalledWith(expect.objectContaining({ title: dicts.ko["error.session_closed.title"] }));
  });

  it("another session: five out, none more, nothing shown or read (RE-F11)", async () => {
    const holds = Array.from({ length: 10 }, () => deferred<unknown>());
    let i = 0;
    (api.regenRumors as Mock).mockImplementation(() => holds[i++].promise);
    const { hook, notify, after } = setup();
    let run: Promise<unknown> = Promise.resolve();
    act(() => {
      run = hook.result.current.regenAll(Array.from({ length: 10 }, (_, k) => `r${k}`));
    });
    expect(api.regenRumors).toHaveBeenCalledTimes(5);
    hook.unmount();
    await act(async () => {
      for (const h of holds.slice(0, 5)) h.resolve([]);
      await run;
    });
    expect(api.regenRumors).toHaveBeenCalledTimes(5);
    expect(notify).not.toHaveBeenCalled();
    expect(after).not.toHaveBeenCalled();
  });
});

describe("TP-V6-8 (hooks): the session read and [retry] (RE-F01, § 1.1 R-10)", () => {
  const S1: GameSession = { id: "s1", world_id: "w", status: "open", turn: 3, created_at: "2026-10-08T05:05:00Z" };
  const world = { world_id: "w", regions: [], connections: [] };

  it("a failed first session read: retry reads the session, then the world comes", async () => {
    (api.getSession as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue(S1);
    (api.exportWorld as Mock).mockResolvedValue(world);
    (api.listSessions as Mock).mockResolvedValue([S1]);
    (api.worldNames as Mock).mockResolvedValue({ world_id: "w", lang: "ko", world: {}, regions: {}, npcs: {}, event_seeds: {} });
    const { result } = renderHook(() => useGmSession("s1"));
    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(api.exportWorld).not.toHaveBeenCalled();
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(result.current.world).toEqual(world);
  });

  it("a failed world read: retry reads the world again", async () => {
    (api.getSession as Mock).mockResolvedValue(S1);
    (api.exportWorld as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue(world);
    (api.listSessions as Mock).mockResolvedValue([S1]);
    (api.worldNames as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue({
      world_id: "w", lang: "ko", world: {}, regions: { a: { name: "항구" } }, npcs: {}, event_seeds: {},
    });
    const { result } = renderHook(() => useGmSession("s1"));
    await waitFor(() => expect(result.current.state).toBe("error"));
    expect(result.current.names.nameOf("regions", "a", "name", "Harbor")).toBe("Harbor"); // English, quietly
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.state).toBe("ready"));
    await waitFor(() => expect(result.current.names.nameOf("regions", "a", "name", "Harbor")).toBe("항구"));
  });

  it("a failed list read is told apart and the session still shows", async () => {
    (api.getSession as Mock).mockResolvedValue(S1);
    (api.exportWorld as Mock).mockResolvedValue(world);
    (api.listSessions as Mock).mockRejectedValue(new TypeError("Failed to fetch"));
    (api.worldNames as Mock).mockResolvedValue({ world_id: "w", lang: "ko", world: {}, regions: {}, npcs: {}, event_seeds: {} });
    const { result } = renderHook(() => useGmSession("s1"));
    await waitFor(() => expect(result.current.sessionsError?.code).toBe("network"));
    expect(result.current.state).toBe("ready");
    expect(sessionOptions(result.current.sessions, result.current.session, "ko").map((o) => o.value)).toEqual(["s1"]);
  });

  it("while the next session reads, the last one is not shown but its world stays", async () => {
    const next = deferred<GameSession>();
    (api.getSession as Mock).mockImplementation((sid: string) => (sid === "s1" ? Promise.resolve(S1) : next.promise));
    (api.exportWorld as Mock).mockResolvedValue(world);
    (api.listSessions as Mock).mockResolvedValue([S1]);
    (api.worldNames as Mock).mockResolvedValue({ world_id: "w", lang: "ko", world: {}, regions: {}, npcs: {}, event_seeds: {} });
    const { result, rerender } = renderHook(({ sid }) => useGmSession(sid), { initialProps: { sid: "s1" } });
    await waitFor(() => expect(result.current.state).toBe("ready"));
    rerender({ sid: "s2" });
    expect(result.current.session).toBeNull();
    expect(result.current.world).toEqual(world);
    await act(async () => next.resolve({ ...S1, id: "s2" }));
    expect(result.current.session?.id).toBe("s2");
    expect(api.exportWorld).toHaveBeenCalledTimes(1); // same world: not read again
  });
});

describe("§ 1.1 R-04 and BR-V6-26: the session picker in words", () => {
  const base: GameSession = { id: "abcdef1234", world_id: "w", status: "open", turn: 4, created_at: "2026-10-08T05:05:00Z" };

  it("turn, status and start date; the id only without a date", () => {
    expect(sessionLabel(base, "ko")).toMatch(/^4턴째 · 진행 중 · 2026/);
    expect(sessionLabel({ ...base, created_at: null }, "ko")).toBe("4턴째 · 진행 중 · abcdef12");
  });

  it("ended sessions in their own group; same labels told apart; the current session from its own read", () => {
    const ended: GameSession = { ...base, id: "zz99", status: "closed" };
    const twin: GameSession = { ...base, id: "qq11" };
    const opts = sessionOptions([ended, base, twin], null, "ko");
    expect(opts.map((o) => o.value)).toEqual(["abcdef1234", "qq11", "zz99"]);
    expect(opts[2].group).toBe(dicts.ko["label.endedSessions"]);
    expect(opts[0].label).toMatch(/· abcd$/);
    expect(opts[1].label).toMatch(/· qq11$/);
    // a new session not in the list yet, and a turn the list has not seen
    const fresh: GameSession = { ...base, id: "new1", turn: 0, created_at: "2026-10-09T01:00:00Z" };
    expect(sessionOptions([base], fresh, "ko").map((o) => o.value)).toEqual(["abcdef1234", "new1"]);
    expect(sessionOptions([base], { ...base, turn: 5 }, "ko")[0].label).toMatch(/^5턴째/);
  });
});

describe("§ 1.1 R-07: the 'new' marks", () => {
  it("lines not there before the turn; nothing when the timeline was not read", () => {
    const before = snapshotIds([line("a"), line("b")], true);
    expect([...newLineIds(before, [line("a"), line("b"), line("c")])]).toEqual(["c"]);
    expect(snapshotIds([line("a")], false)).toBeNull();
    expect(newLineIds(null, [line("a")]).size).toBe(0);
  });
});
