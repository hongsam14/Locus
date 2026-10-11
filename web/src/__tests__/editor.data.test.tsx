// V8 editor data hooks (code plan Step 3, TP-V8-3/4/12/18, § 1.1 R-15/R-16/R-17, § 1.4 R-02/
// R-04/R-05): a made region is picked by the read after it, drags of one region wait their turn,
// a replace clears and re-reads, and the augmentation writes live on the page.
import { act, renderHook, waitFor } from "@testing-library/react";
import { HttpError } from "../api/http";
import { useAugmentation } from "../features/editor/useAugmentation";
import { useEditorWorld } from "../features/editor/useEditorWorld";
import { t } from "../i18n";
import type { AugQuestion, AugRun, Region, WorldExport } from "../types";

vi.mock("../api", () => ({
  api: {
    exportWorld: vi.fn(),
    listWorlds: vi.fn(),
    updateRegion: vi.fn(),
    startRun: vi.fn(),
    getRun: vi.fn(),
    answer: vi.fn(),
    revert: vi.fn(),
    unignore: vi.fn(),
    listPriors: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;

function deferred<T>() {
  let resolve: (v: T) => void = () => {};
  let reject: (e: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const region = (id: string, x = 0.1, y = 0.1): Region => ({ id, name: id.toUpperCase(), level: "town", position: { x, y } });
const world = (...regions: Region[]): WorldExport =>
  ({ world_id: "w", regions, connections: [], entities: [], knowledge: [], scopes: [] }) as WorldExport;

beforeEach(() => {
  vi.resetAllMocks();
  (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "W", region_count: 1, open_sessions: 0 }]);
});

describe("useEditorWorld — a made region (TP-V8-3, UX-25, R-04)", () => {
  it("is picked by the read after it, even when that read comes late", async () => {
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a")));
    const { result } = renderHook(() => useEditorWorld("w"));
    await waitFor(() => expect(result.current.world).toBeDefined());
    const late = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(late.promise);
    act(() => result.current.created("b"));
    expect(result.current.selected).toBeNull(); // not before the read
    await act(async () => late.resolve(world(region("a"), region("b"))));
    await waitFor(() => expect(result.current.selected).toBe("b"));
    expect(result.current.notFound).toBe(false);
  });

  it("stops waiting when the read fails, and the stale-selection rule runs again", async () => {
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a")));
    const { result } = renderHook(() => useEditorWorld("w"));
    await waitFor(() => expect(result.current.world).toBeDefined());
    act(() => result.current.select("a"));
    (api.exportWorld as Mock).mockRejectedValueOnce(new HttpError(500, "Error", "boom"));
    act(() => result.current.created("b"));
    await waitFor(() => expect(result.current.error).toBeDefined());
    expect(result.current.selected).toBe("a"); // nothing was decided; "a" stays
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("c")));
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.world?.regions[0].id).toBe("c"));
    await waitFor(() => expect(result.current.selected).toBeNull()); // "a" is gone: cleared
  });

  it("the read that brings the new region and drops the old selection picks the new one", async () => {
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a")));
    const { result } = renderHook(() => useEditorWorld("w"));
    await waitFor(() => expect(result.current.world).toBeDefined());
    act(() => result.current.select("a"));
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("b"))); // "a" went meanwhile
    act(() => result.current.created("b"));
    await waitFor(() => expect(result.current.world?.regions[0].id).toBe("b"));
    await waitFor(() => expect(result.current.selected).toBe("b"));
  });

  it("gives way to a region the designer picks meanwhile", async () => {
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a")));
    const { result } = renderHook(() => useEditorWorld("w"));
    await waitFor(() => expect(result.current.world).toBeDefined());
    const late = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(late.promise);
    act(() => result.current.created("b"));
    act(() => result.current.select("a"));
    await act(async () => late.resolve(world(region("a"), region("b"))));
    await waitFor(() => expect(result.current.world?.regions).toHaveLength(2));
    expect(result.current.selected).toBe("a");
  });

  it("an older read landing after the create never decides; a read without the region says so", async () => {
    const first = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(first.promise);
    const { result } = renderHook(() => useEditorWorld("w"));
    const after = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(after.promise);
    act(() => result.current.created("b"));
    await act(async () => first.resolve(world(region("a")))); // started before the create
    expect(result.current.notFound).toBe(false);
    await act(async () => after.resolve(world(region("a")))); // started after it: "b" is not there
    await waitFor(() => expect(result.current.notFound).toBe(true));
    expect(result.current.selected).toBeNull();
  });
});

describe("useEditorWorld — drags (TP-V8-12, R-16)", () => {
  async function ready(...regions: Region[]) {
    (api.exportWorld as Mock).mockResolvedValueOnce(world(...regions));
    const hook = renderHook(() => useEditorWorld("w"));
    await waitFor(() => expect(hook.result.current.world).toBeDefined());
    return hook;
  }

  it("one region: a save at a time, then only the last spot waiting", async () => {
    const { result } = await ready(region("a"));
    const first = deferred<Region>();
    (api.updateRegion as Mock).mockReturnValueOnce(first.promise).mockResolvedValue(region("a"));
    act(() => result.current.move("a", { x: 0.2, y: 0.2 }));
    act(() => result.current.move("a", { x: 0.3, y: 0.3 }));
    act(() => result.current.move("a", { x: 0.4, y: 0.4 }));
    expect(api.updateRegion).toHaveBeenCalledTimes(1);
    expect(result.current.regions[0].position).toEqual({ x: 0.4, y: 0.4 }); // the map shows the last
    await act(async () => first.resolve(region("a")));
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledTimes(2));
    expect((api.updateRegion as Mock).mock.calls[1][1].position).toEqual({ x: 0.4, y: 0.4 });
  });

  it("different regions do not wait for each other", async () => {
    const { result } = await ready(region("a"), region("b"));
    (api.updateRegion as Mock).mockReturnValue(new Promise(() => {}));
    act(() => result.current.move("a", { x: 0.2, y: 0.2 }));
    act(() => result.current.move("b", { x: 0.3, y: 0.3 }));
    expect(api.updateRegion).toHaveBeenCalledTimes(2);
  });

  it("a failed save drops the spot, says so and reads the world again", async () => {
    const { result } = await ready(region("a"));
    (api.updateRegion as Mock).mockRejectedValueOnce(new HttpError(503, "Unavailable", "graph down"));
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a")));
    act(() => result.current.move("a", { x: 0.5, y: 0.5 }));
    await waitFor(() => expect(result.current.dragError).toBeDefined());
    expect(result.current.dragError?.raw).toContain("graph down");
    expect(result.current.regions[0].position).toEqual({ x: 0.1, y: 0.1 });
    expect(api.exportWorld).toHaveBeenCalledTimes(2);
  });

  it("the laid-over spot goes once the stored world holds it", async () => {
    const { result } = await ready(region("a"));
    (api.updateRegion as Mock).mockResolvedValue(region("a"));
    act(() => result.current.move("a", { x: 0.6, y: 0.6 }));
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledTimes(1));
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a", 0.6, 0.6)));
    act(() => result.current.reloadWorld());
    await waitFor(() => expect(result.current.world?.regions[0].position).toEqual({ x: 0.6, y: 0.6 }));
    expect(result.current.regions[0].position).toEqual({ x: 0.6, y: 0.6 });
  });
});

describe("useEditorWorld — a replace (TP-V8-18, R-02)", () => {
  it("clears the connection and the drags, re-reads the world, the count and every panel", async () => {
    (api.exportWorld as Mock).mockResolvedValue(world(region("a")));
    const onReplaced = vi.fn();
    const { result } = renderHook(() => useEditorWorld("w", { onReplaced }));
    await waitFor(() => expect(result.current.world).toBeDefined());
    const inspector = vi.fn();
    const unscoped = vi.fn();
    act(() => {
      result.current.registerReload("inspector", inspector);
      result.current.registerReload("unscoped", unscoped);
      result.current.select("a");
    });
    act(() => result.current.replaced());
    expect(onReplaced).toHaveBeenCalledTimes(1);
    expect(inspector).toHaveBeenCalledTimes(1); // "a" stays: it reads its new content
    expect(unscoped).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(api.exportWorld).toHaveBeenCalledTimes(2));
    expect(api.listWorlds).toHaveBeenCalledTimes(2);
    expect(result.current.selected).toBe("a");
  });

  it("a drag save re-reads the inspector only", async () => {
    (api.exportWorld as Mock).mockResolvedValue(world(region("a")));
    (api.updateRegion as Mock).mockResolvedValue(region("a"));
    const { result } = renderHook(() => useEditorWorld("w"));
    await waitFor(() => expect(result.current.world).toBeDefined());
    const inspector = vi.fn();
    const wiki = vi.fn();
    act(() => {
      result.current.registerReload("inspector", inspector);
      result.current.registerReload("wiki", wiki);
    });
    act(() => result.current.move("a", { x: 0.3, y: 0.3 }));
    await waitFor(() => expect(inspector).toHaveBeenCalledTimes(1));
    expect(wiki).not.toHaveBeenCalled();
    expect(api.exportWorld).toHaveBeenCalledTimes(1); // a drag reads no world (C1)
  });
});

// --------------------------------------------------------------------------- //
const run = (over: Partial<AugRun> = {}): AugRun => ({
  id: "run1", world_id: "w", status: "open", answers: 0, open_questions: [], ignored_keys: [], history: [],
  llm_calls: 0, llm_budget_exhausted: false, ...over,
});
const question = (key: string, over: Partial<AugQuestion> = {}): AugQuestion => ({
  id: `q-${key}`, issue_id: `i-${key}`, issue_key: key, text: "?", actions: ["edit", "ignore"],
  needs: { edit: ["statement"] }, ...over,
});

describe("useAugmentation (R-15, § 1.4 R-05, TP-V8-4)", () => {
  async function started(q: AugQuestion[]) {
    (api.startRun as Mock).mockResolvedValueOnce(run({ open_questions: q }));
    const onChanged = vi.fn();
    const hook = renderHook(() => useAugmentation("w", { onChanged }));
    act(() => hook.result.current.start());
    await waitFor(() => expect(hook.result.current.run).not.toBeNull());
    return { ...hook, onChanged };
  }

  it("one write at a time: a second answer while one is out is not sent", async () => {
    const q = question("k1");
    const { result } = await started([q]);
    const out = deferred<unknown>();
    (api.answer as Mock).mockReturnValueOnce(out.promise);
    act(() => result.current.setDraft("k1", { statement: "s" }));
    act(() => result.current.answer(q, "edit"));
    act(() => result.current.answer(q, "edit"));
    act(() => result.current.revert("c1"));
    expect(api.answer).toHaveBeenCalledTimes(1);
    expect(api.revert).not.toHaveBeenCalled();
    expect(result.current.busy).toBe(true);
    await act(async () => out.resolve({ change: null, run: run(), changed: [] }));
    await waitFor(() => expect(result.current.busy).toBe(false));
  });

  it("an answer clears its own card's draft only, by issue key", async () => {
    const q1 = question("k1");
    const q2 = question("k2");
    const { result, onChanged } = await started([q1, q2]);
    act(() => {
      result.current.setDraft("k1", { statement: "one" });
      result.current.setDraft("k2", { statement: "two" });
    });
    (api.answer as Mock).mockResolvedValueOnce({
      change: { id: "c1", description: "gap:add", added_ids: [], reverted: false },
      run: run({ open_questions: [{ ...q2, id: "q-new" }] }), // a re-detection: new question ids
      changed: [{ kind: "knowledge", id: "k1", name: "Fish" }],
    });
    act(() => result.current.answer(q1, "edit"));
    await waitFor(() => expect(result.current.drafts.k1).toBeUndefined());
    expect(result.current.drafts.k2).toEqual({ statement: "two" });
    expect(result.current.changed.c1[0].name).toBe("Fish");
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect((api.answer as Mock).mock.calls[0][1]).toMatchObject({ statement: "one", action: "edit" });
  });

  it("a 404 with the run alive keeps the run and says the subject is gone (#12)", async () => {
    const q = question("k1");
    const { result } = await started([q]);
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", '{"detail":"region not found: gone"}'));
    (api.getRun as Mock).mockResolvedValueOnce(run({ open_questions: [q] }));
    act(() => result.current.answer(q, "edit"));
    await waitFor(() => expect(result.current.error).toBeDefined());
    expect(result.current.error?.title).toBe(t("notice.augmentWorldChanged"));
    expect(result.current.error?.raw).toContain("region not found: gone");
    expect(result.current.lost).toBe(false);
    expect(result.current.run).not.toBeNull();
  });

  it("a 404 with the run gone is a lost run", async () => {
    const q = question("k1");
    const { result } = await started([q]);
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", "run not found"));
    (api.getRun as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", "run not found"));
    act(() => result.current.answer(q, "edit"));
    await waitFor(() => expect(result.current.lost).toBe(true));
  });

  it("a 400 reads as one sentence with the server's reason folded (R-06)", async () => {
    const q = question("k1");
    const { result } = await started([q]);
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(400, "Bad Request", '{"detail":"the answer changes nothing","code":"invalid_request"}'));
    act(() => result.current.answer(q, "edit"));
    await waitFor(() => expect(result.current.error?.title).toBe(t("notice.augmentCantSave")));
    expect(result.current.error?.raw).toContain("the answer changes nothing");
  });

  it("reads the prior choices when a question needs them, and a reset forgets everything", async () => {
    (api.listPriors as Mock).mockResolvedValue([{ id: "p1", effect: "rivers flow downhill" }]);
    const { result } = await started([question("k1", { ref_kind: "prior" })]);
    await waitFor(() => expect(result.current.priors).toHaveLength(1));
    act(() => result.current.setDraft("k1", { ref: "p1" }));
    act(() => result.current.reset());
    expect(result.current.run).toBeNull();
    expect(result.current.drafts).toEqual({});
    expect(result.current.priors).toBeNull();
  });
});
