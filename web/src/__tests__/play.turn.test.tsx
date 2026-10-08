// V4 play hooks (FD BLM § 2.1·2.2, BR-V4-04/16/17/19, TP-V4-9/10, RE-F08): a turn run is
// polled with a cap; a finished turn becomes the one outcome; only warnings notify; leaving
// the session stops the loop; another session's data is never returned.
import { act, renderHook, waitFor } from "@testing-library/react";
import { HttpError } from "../api/http";
import { useHeldRereads, usePlaySession, useTurnRun, useWorldNames } from "../hooks";
import { t } from "../i18n";
import type { GameSession, RegionView, TurnRun } from "../types";
import { clearToasts } from "../ui/toast";

vi.mock("../api", () => ({
  api: {
    act: vi.fn(),
    getTurnRun: vi.fn(),
    listTurnRuns: vi.fn(),
    getSession: vi.fn(),
    getRegion: vi.fn(),
    getLog: vi.fn(),
    worldNames: vi.fn(),
  },
}));
import { api } from "../api";
import { useToasts } from "../ui/toast";

type Mock = ReturnType<typeof vi.fn>;
const run = (status: TurnRun["status"], extra: Partial<TurnRun> = {}): TurnRun => ({
  id: "run1", session_id: "s1", action: { type: "wait" }, cost_turns: 1, status, started_turn: 3, ...extra,
});
const done = (changes = 0, flags: { budget?: boolean; llm?: boolean; declaration?: string } = {}) =>
  run("done", {
    result: {
      session: { id: "s1", world_id: "w", status: "open", turn: 4 } as GameSession,
      player: null, turns: [], narration: [], llm_calls: 0, llm_available: false,
      changes: Array.from({ length: changes }, (_, i) => ({
        region_id: `r${i}`, promoted: [], demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: ["x"],
      })),
      budget_exhausted: !!flags.budget,
      llm_failed: !!flags.llm,
      declaration: flags.declaration ? { text: flags.declaration, record: "", lang: "ko", llm_calls: 1 } : null,
    },
  });

beforeEach(() => {
  vi.clearAllMocks();
  (api.listTurnRuns as Mock).mockResolvedValue([]);
});
afterEach(() => clearToasts());

function setup(sessionId = "s1", maxPolls = 120) {
  const reload = vi.fn();
  const hook = renderHook(({ sid }) => ({ turn: useTurnRun(sid, { reload, pollMs: 1, maxPolls }), toasts: useToasts() }), {
    initialProps: { sid: sessionId },
  });
  return { reload, hook };
}

describe("useTurnRun", () => {
  it("polls a run to its end: one outcome, a re-read after the action and after the turn", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValueOnce(run("running")).mockResolvedValue(done(2, { declaration: "광장이 술렁인다." }));
    const { reload, hook } = setup();
    let ok = false;
    await act(async () => {
      ok = await hook.result.current.turn.act({ type: "wait" });
    });
    expect(ok).toBe(true);
    expect(hook.result.current.turn.running?.id).toBe("run1");
    await waitFor(() => expect(hook.result.current.turn.outcome).not.toBeNull());
    expect(hook.result.current.turn.outcome).toMatchObject({ turn: 4, quiet: false, declaration: { text: "광장이 술렁인다." } });
    expect(hook.result.current.turn.running).toBeNull();
    expect(reload).toHaveBeenCalledTimes(2);
    expect(hook.result.current.toasts).toEqual([]); // the result is not a notification (BR-V4-04)
  });

  it("only warnings notify: budget, LLM failure, a failed run", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValue(done(0, { budget: true, llm: true }));
    const { hook } = setup();
    await act(async () => void (await hook.result.current.turn.act({ type: "wait" })));
    await waitFor(() => expect(hook.result.current.turn.outcome?.quiet).toBe(true));
    expect(hook.result.current.toasts.map((x) => x.key).sort()).toEqual(["play:budget", "play:llm"]);
    (api.getTurnRun as Mock).mockResolvedValue(run("failed", { error: "boom" }));
    await act(async () => void (await hook.result.current.turn.act({ type: "wait" })));
    await waitFor(() => expect(hook.result.current.toasts.some((x) => x.key === "play:run" && x.tone === "danger")).toBe(true));
  });

  it("stops at the cap and says the turn is slow; [check again] polls again (RE-F08)", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockResolvedValue(run("running"));
    const { hook } = setup("s1", 3);
    await act(async () => void (await hook.result.current.turn.act({ type: "wait" })));
    await waitFor(() => expect(hook.result.current.turn.slow).toBe(true));
    expect(api.getTurnRun).toHaveBeenCalledTimes(3);
    expect(hook.result.current.turn.running).not.toBeNull(); // the actions stay off
    (api.getTurnRun as Mock).mockResolvedValue(done(1));
    act(() => hook.result.current.turn.recheck());
    expect(hook.result.current.turn.slow).toBe(false);
    await waitFor(() => expect(hook.result.current.turn.outcome).not.toBeNull());
  });

  it("a failed check shows the error, re-reads, and [check again] tries the same run", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    (api.getTurnRun as Mock).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const { reload, hook } = setup();
    await act(async () => void (await hook.result.current.turn.act({ type: "wait" })));
    await waitFor(() => expect(hook.result.current.turn.error?.code).toBe("network"));
    expect(hook.result.current.turn.running).toBeNull();
    expect(reload).toHaveBeenCalledTimes(2);
    (api.getTurnRun as Mock).mockResolvedValue(done(1));
    act(() => hook.result.current.turn.recheck());
    await waitFor(() => expect(hook.result.current.turn.outcome).not.toBeNull());
    expect(hook.result.current.turn.error).toBeUndefined();
  });

  it("409: mid-turn notifies, a closed session re-reads with no notification; 400 is refused (BR-V4-04/18)", async () => {
    const { reload, hook } = setup();
    (api.act as Mock).mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":"a turn is running","code":"turn_running"}'));
    let ok = true;
    await act(async () => {
      ok = await hook.result.current.turn.act({ type: "wait" });
    });
    expect(ok).toBe(false);
    expect(hook.result.current.toasts.map((x) => [x.key, x.title])).toEqual([["play:busy", t("play.turnInProgress")]]);
    clearToasts();
    (api.act as Mock).mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":"session is closed","code":"session_closed"}'));
    await act(async () => void (await hook.result.current.turn.act({ type: "wait" })));
    expect(reload).toHaveBeenCalledTimes(1);
    expect(hook.result.current.toasts).toEqual([]);
    (api.act as Mock).mockRejectedValueOnce(new HttpError(400, "Bad Request", '{"detail":"no such connection"}'));
    await act(async () => {
      ok = await hook.result.current.turn.act({ type: "move", to_region_id: "r9" });
    });
    expect(ok).toBe(false); // a refused action: the caller keeps the sheet open
    expect(hook.result.current.turn.refusal?.status).toBe(400);
    expect(hook.result.current.turn.error).toBeUndefined(); // nothing to check again
  });

  it("leaving the session stops the loop: no outcome lands on the next session", async () => {
    (api.act as Mock).mockResolvedValue(run("running"));
    let finish: (r: TurnRun) => void = () => {};
    (api.getTurnRun as Mock).mockImplementation(() => new Promise<TurnRun>((r) => (finish = r)));
    const { hook } = setup();
    await act(async () => void (await hook.result.current.turn.act({ type: "wait" })));
    await waitFor(() => expect(api.getTurnRun).toHaveBeenCalled());
    hook.rerender({ sid: "s2" });
    await act(async () => finish(done(1)));
    expect(hook.result.current.turn.outcome).toBeNull();
    expect(hook.result.current.turn.running).toBeNull();
  });

  it("a run left in flight is polled again when the screen opens", async () => {
    (api.listTurnRuns as Mock).mockResolvedValue([run("running")]);
    (api.getTurnRun as Mock).mockResolvedValue(done(1));
    const { hook } = setup();
    await waitFor(() => expect(hook.result.current.turn.outcome).not.toBeNull());
  });
});

describe("useHeldRereads (BR-V4-19)", () => {
  it("re-reads every interval while held, at most max times", async () => {
    vi.useFakeTimers();
    try {
      const reload = vi.fn();
      const { rerender } = renderHook(({ held }) => useHeldRereads(held, reload, 1000, 5), { initialProps: { held: true } });
      for (let i = 0; i < 7; i++) await act(async () => vi.advanceTimersByTime(1000));
      expect(reload).toHaveBeenCalledTimes(5);
      rerender({ held: false });
      rerender({ held: true }); // held again: counts afresh
      await act(async () => vi.advanceTimersByTime(1000));
      expect(reload).toHaveBeenCalledTimes(6);
    } finally {
      vi.useRealTimers();
    }
  });
});

const view = (sid: string, name: string) => ({ session_id: sid, region_id: "r1", region_name: name } as unknown as RegionView);

describe("usePlaySession (BR-V4-16, TP-V4-10)", () => {
  it("never returns the previous session's data while the next one reads, nor a late answer", async () => {
    (api.getSession as Mock).mockImplementation(async (sid: string) => ({ id: sid, world_id: "w", status: "open", turn: 0 }));
    (api.getLog as Mock).mockResolvedValue([]);
    let releaseA: (v: RegionView) => void = () => {};
    let releaseB: (v: RegionView) => void = () => {};
    (api.getRegion as Mock).mockImplementation((sid: string) =>
      new Promise<RegionView>((r) => (sid === "a" ? (releaseA = r) : (releaseB = r))),
    );
    const { result, rerender } = renderHook(({ sid }) => usePlaySession(sid), { initialProps: { sid: "a" } });
    await act(async () => releaseA(view("a", "Harbor")));
    await waitFor(() => expect(result.current.view?.region_name).toBe("Harbor"));
    rerender({ sid: "b" });
    expect(result.current.view).toBeNull(); // not A's region under B's address
    expect(result.current.state).toBe("loading");
    await act(async () => releaseB(view("b", "Ironcrag")));
    await waitFor(() => expect(result.current.view?.region_name).toBe("Ironcrag"));
  });

  it("a re-read keeps the screen (no skeleton); a failed re-read keeps the data and adds the error", async () => {
    (api.getSession as Mock).mockResolvedValue({ id: "a", world_id: "w", status: "open", turn: 0 });
    (api.getLog as Mock).mockResolvedValue([]);
    (api.getRegion as Mock).mockResolvedValueOnce(view("a", "Harbor"));
    const { result } = renderHook(() => usePlaySession("a"));
    await waitFor(() => expect(result.current.state).toBe("ready"));
    let fail: (e: unknown) => void = () => {};
    (api.getRegion as Mock).mockImplementation(() => new Promise((_r, rej) => (fail = rej)));
    act(() => result.current.reload());
    expect(result.current.state).toBe("ready");
    expect(result.current.view?.region_name).toBe("Harbor");
    await act(async () => fail(new TypeError("Failed to fetch")));
    await waitFor(() => expect(result.current.error?.code).toBe("network"));
    expect(result.current.state).toBe("ready");
    expect(result.current.view?.region_name).toBe("Harbor");
  });
});

describe("useWorldNames (BR-V4-11)", () => {
  it("finds a name by id, falls back to the English, and ignores another world's map", async () => {
    (api.worldNames as Mock).mockImplementation(async (w: string) => ({
      world_id: w === "w2" ? "elsewhere" : w, lang: "ko", world: {}, npcs: {}, event_seeds: {},
      regions: { r1: { name: "솔트웨이크 항구" } },
    }));
    const { result, rerender } = renderHook(({ w }) => useWorldNames(w), { initialProps: { w: "w1" as string | null } });
    await waitFor(() => expect(result.current.names).not.toBeNull());
    expect(result.current.nameOf("regions", "r1", "name", "Saltwake Harbor")).toBe("솔트웨이크 항구");
    expect(result.current.nameOf("regions", "r9", "name", "Ironcrag")).toBe("Ironcrag");
    rerender({ w: "w2" });
    await waitFor(() => expect(api.worldNames).toHaveBeenCalledWith("w2"));
    expect(result.current.names).toBeNull(); // the answer names another world
    expect(result.current.nameOf("regions", "r1", "name", "Saltwake Harbor")).toBe("Saltwake Harbor");
  });
});
