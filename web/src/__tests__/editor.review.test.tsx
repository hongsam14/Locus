// V8 code review 01 — the data flow fixes and the test gaps the review found
// (code-review-01.md #2, #8, #9, #11–#13, #19, #25–#27, #29, #37).
import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { HttpError } from "../api/http";
import { fieldLabel } from "../features/editor/augmentNames";
import { BuildReportPanel } from "../features/editor/BuildReportPanel";
import { UnscopedPanel } from "../features/editor/UnscopedPanel";
import { useAugmentation } from "../features/editor/useAugmentation";
import { useEditorWorld } from "../features/editor/useEditorWorld";
import { enumLabel } from "../format";
import { t } from "../i18n";
import { AugHost } from "../test/editor";
import { InlineError } from "../ui";
import type { AugQuestion, AugRun, BuildReport, ConnectionEdge, Region, WorldExport } from "../types";

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
    listUnscoped: vi.fn(),
    setScopes: vi.fn(),
    deleteKnowledge: vi.fn(),
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
const region = (id: string, x = 0.1, y = 0.1, name = id.toUpperCase()): Region => ({ id, name, level: "town", position: { x, y } });
const world = (...regions: Region[]): WorldExport =>
  ({ world_id: "w", regions, connections: [], entities: [], knowledge: [], scopes: [] }) as WorldExport;
const run = (over: Partial<AugRun> = {}): AugRun => ({
  id: "run1", world_id: "w", status: "open", answers: 0, open_questions: [], ignored_keys: [], history: [],
  llm_calls: 0, llm_budget_exhausted: false, ...over,
});
const question = (key: string, over: Partial<AugQuestion> = {}): AugQuestion => ({
  id: `q-${key}`, issue_id: `i-${key}`, issue_key: key, text: "?", actions: ["edit", "ignore"],
  needs: { edit: ["statement"] }, ...over,
});

beforeEach(() => {
  vi.resetAllMocks();
  (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "W", region_count: 1, open_sessions: 0 }]);
});

async function editorWorld(...regions: Region[]) {
  (api.exportWorld as Mock).mockResolvedValueOnce(world(...regions));
  const hook = renderHook(() => useEditorWorld("w"));
  await waitFor(() => expect(hook.result.current.world).toBeDefined());
  return hook;
}
async function augmentation(questions: AugQuestion[], onChanged = vi.fn()) {
  (api.startRun as Mock).mockResolvedValueOnce(run({ open_questions: questions }));
  const hook = renderHook(() => useAugmentation("w", { onChanged }));
  act(() => hook.result.current.start());
  await waitFor(() => expect(hook.result.current.run).not.toBeNull());
  return { ...hook, onChanged };
}

describe("#2: a drag is saved from the world as the last write left it", () => {
  it("a drag right after a rename waits for the world read and sends the new name", async () => {
    const { result } = await editorWorld(region("a", 0.1, 0.1, "Old"));
    const slow = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(slow.promise);
    act(() => result.current.reloadWorld()); // the inspector saved "New" and asked for a re-read
    (api.updateRegion as Mock).mockResolvedValue({});
    act(() => result.current.move("a", { x: 0.5, y: 0.5 }));
    expect(api.updateRegion).not.toHaveBeenCalled(); // waits for the read
    await act(async () => slow.resolve(world(region("a", 0.1, 0.1, "New"))));
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledTimes(1));
    expect((api.updateRegion as Mock).mock.calls[0][1]).toMatchObject({ name: "New", position: { x: 0.5, y: 0.5 } });
  });

  it("after a replace the map is off until the new world answers", async () => {
    const { result } = await editorWorld(region("gone"));
    const after = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(after.promise);
    act(() => result.current.replaced());
    expect(result.current.settling).toBe(true);
    await act(async () => after.resolve(world(region("new"))));
    await waitFor(() => expect(result.current.settling).toBe(false));
    expect(result.current.regions.map((r) => r.id)).toEqual(["new"]);
  });

  it("a drag waiting for a read when a replace comes is never sent into the new world", async () => {
    const { result } = await editorWorld(region("a"));
    const first = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(first.promise);
    act(() => result.current.reloadWorld());
    (api.updateRegion as Mock).mockResolvedValue({});
    act(() => result.current.move("a", { x: 0.4, y: 0.4 })); // waits for that read
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a", 0.9, 0.9, "Loaded")));
    act(() => result.current.replaced());
    await waitFor(() => expect(result.current.world?.regions[0].name).toBe("Loaded"));
    await new Promise((r) => setTimeout(r, 20));
    expect(api.updateRegion).not.toHaveBeenCalled();
  });
});

describe("#8 / T2: the drag overlay shows the server's spot once the world is read after the save", () => {
  it("a read asked after the save settled drops the overlay even when the spots differ", async () => {
    const { result } = await editorWorld(region("a"));
    (api.updateRegion as Mock).mockResolvedValue({});
    act(() => result.current.move("a", { x: 0.6, y: 0.6 }));
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledTimes(1));
    await act(async () => {});
    expect(result.current.regions[0].position).toEqual({ x: 0.6, y: 0.6 });
    // something else wrote the region after the drag (another tab): the world says 0.9
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a", 0.9, 0.9)));
    act(() => result.current.reloadWorld());
    await waitFor(() => expect(result.current.regions[0].position).toEqual({ x: 0.9, y: 0.9 }));
  });

  it("a read while the save is out keeps the dragged spot", async () => {
    const { result } = await editorWorld(region("a"));
    (api.updateRegion as Mock).mockReturnValue(new Promise(() => {}));
    act(() => result.current.move("a", { x: 0.6, y: 0.6 }));
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a", 0.9, 0.9)));
    act(() => result.current.reloadWorld());
    await waitFor(() => expect(result.current.world?.regions[0].position).toEqual({ x: 0.9, y: 0.9 }));
    expect(result.current.regions[0].position).toEqual({ x: 0.6, y: 0.6 });
  });
});

describe("#11 / T1: a replace clears what belonged to the old world (TP-V8-18, BLM § 1.4)", () => {
  it("the line, the overlay, the queue and the awaited region all go, and a late save answer does nothing", async () => {
    const { result } = await editorWorld(region("a"), region("b"));
    const line: ConnectionEdge = { world_id: "w", source_region_id: "a", target_region_id: "b", kind: "route", weight: 0.5 };
    act(() => result.current.selectConnection(line));
    const held = deferred<unknown>();
    (api.updateRegion as Mock).mockReturnValueOnce(held.promise).mockResolvedValue({});
    act(() => result.current.move("a", { x: 0.6, y: 0.6 }));
    act(() => result.current.move("a", { x: 0.7, y: 0.7 })); // waits behind the held save
    (api.exportWorld as Mock).mockReturnValueOnce(new Promise(() => {})); // the create's read never answers
    act(() => result.current.created("c"));
    // the new world holds "c" too: had the wait survived the replace, "c" would be picked
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a", 0.3, 0.3), region("b"), region("c")));
    act(() => result.current.replaced());
    expect(result.current.connection).toBeNull();
    await waitFor(() => expect(result.current.regions[0].position).toEqual({ x: 0.3, y: 0.3 }));
    await act(async () => held.resolve({})); // the old save comes back after the replace
    await new Promise((r) => setTimeout(r, 20));
    expect(api.updateRegion).toHaveBeenCalledTimes(1); // the waiting 0.7 is never sent
    expect(result.current.regions[0].position).toEqual({ x: 0.3, y: 0.3 });
    expect(result.current.selected).toBe("a"); // kept: in the new world; "c" is no longer awaited
  });

  it("a failed save forgets the spot that waited (G-M24)", async () => {
    const { result } = await editorWorld(region("a"));
    (api.exportWorld as Mock).mockResolvedValue(world(region("a")));
    const first = deferred<unknown>();
    (api.updateRegion as Mock).mockReturnValueOnce(first.promise).mockResolvedValue({});
    act(() => result.current.move("a", { x: 0.2, y: 0.2 }));
    act(() => result.current.move("a", { x: 0.3, y: 0.3 }));
    await act(async () => first.reject(new HttpError(503, "x", "down")));
    await waitFor(() => expect(result.current.dragError).toBeDefined());
    act(() => result.current.move("a", { x: 0.9, y: 0.9 }));
    await waitFor(() => expect(api.updateRegion).toHaveBeenCalledTimes(2));
    expect((api.updateRegion as Mock).mock.calls.map((c) => c[1].position)).toEqual([{ x: 0.2, y: 0.2 }, { x: 0.9, y: 0.9 }]);
  });

  it("a replace clears the drag error; picking a line clears the not-found line (#29)", async () => {
    const { result } = await editorWorld(region("a"), region("b"));
    (api.updateRegion as Mock).mockRejectedValueOnce(new HttpError(503, "x", "down"));
    (api.exportWorld as Mock).mockResolvedValue(world(region("a"), region("b")));
    act(() => result.current.move("a", { x: 0.2, y: 0.2 }));
    await waitFor(() => expect(result.current.dragError).toBeDefined());
    act(() => result.current.created("zzz")); // the read after it does not hold it
    await waitFor(() => expect(result.current.notFound).toBe(true));
    act(() => result.current.selectConnection({ world_id: "w", source_region_id: "a", target_region_id: "b", kind: "route", weight: 0.5 }));
    expect(result.current.notFound).toBe(false);
    act(() => result.current.replaced());
    expect(result.current.dragError).toBeUndefined();
  });
});

describe("#25: a region made while the world shows a read error is still picked", () => {
  it("the old error does not release the new wait; the read after the create decides", async () => {
    const { result } = await editorWorld(region("a"));
    (api.exportWorld as Mock).mockRejectedValueOnce(new HttpError(500, "Error", "blip"));
    act(() => result.current.reloadWorld());
    await waitFor(() => expect(result.current.error).toBeDefined());
    const after = deferred<WorldExport>();
    (api.exportWorld as Mock).mockReturnValueOnce(after.promise);
    act(() => result.current.created("b"));
    await act(async () => after.resolve(world(region("a"), region("b"))));
    await waitFor(() => expect(result.current.selected).toBe("b"));
  });

  it("the read after the create failing does release it", async () => {
    const { result } = await editorWorld(region("a"));
    (api.exportWorld as Mock).mockRejectedValueOnce(new HttpError(500, "Error", "blip"));
    act(() => result.current.created("b"));
    await waitFor(() => expect(result.current.error).toBeDefined());
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a"), region("b")));
    act(() => result.current.reloadWorld());
    await waitFor(() => expect(result.current.world?.regions).toHaveLength(2));
    expect(result.current.selected).toBeNull();
  });
});

describe("#37: another world clears the last one's selection, run and drafts (BR-V8-24)", () => {
  it("the world hook starts clean and does not drag the old world into the new one", async () => {
    (api.exportWorld as Mock).mockResolvedValueOnce(world(region("a", 0.1, 0.1, "FromW")));
    const { result, rerender } = renderHook(({ id }) => useEditorWorld(id), { initialProps: { id: "w" } });
    await waitFor(() => expect(result.current.world).toBeDefined());
    act(() => result.current.select("a"));
    (api.exportWorld as Mock).mockReturnValueOnce(new Promise(() => {}));
    rerender({ id: "v" });
    expect(result.current.selected).toBeNull();
    await waitFor(() => expect(result.current.settling).toBe(true));
    (api.updateRegion as Mock).mockResolvedValue({});
    act(() => result.current.move("a", { x: 0.7, y: 0.7 }));
    await new Promise((r) => setTimeout(r, 20));
    expect(api.updateRegion).not.toHaveBeenCalled();
  });

  it("the augmentation hook forgets the run and the drafts", async () => {
    (api.startRun as Mock).mockResolvedValueOnce(run({ open_questions: [question("k1")] }));
    const { result, rerender } = renderHook(({ id }) => useAugmentation(id, { onChanged: () => {} }), { initialProps: { id: "w" } });
    act(() => result.current.start());
    await waitFor(() => expect(result.current.run).not.toBeNull());
    act(() => result.current.setDraft("k1", { statement: "typed" }));
    rerender({ id: "v" });
    expect(result.current.run).toBeNull();
    expect(result.current.drafts).toEqual({});
  });
});

describe("#19, #27, #12, #13: the augmentation hook", () => {
  it("a 404 with the run alive: one sentence, no contradicting line, and [start again]", async () => {
    const { result } = await augmentation([question("k1")]);
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", "region not found: gone"));
    (api.getRun as Mock).mockResolvedValueOnce(run({ open_questions: [question("k1")] }));
    act(() => result.current.answer(question("k1"), "edit"));
    await waitFor(() => expect(result.current.error?.title).toBe(t("notice.augmentWorldChanged")));
    expect(result.current.error?.action).toBeUndefined();
    expect(result.current.stale).toBe(true);
  });

  it("a 400: one sentence, no repeated line", async () => {
    const { result } = await augmentation([question("k1")]);
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(400, "Bad Request", "nothing changes"));
    act(() => result.current.answer(question("k1"), "edit"));
    await waitFor(() => expect(result.current.error?.title).toBe(t("notice.augmentCantSave")));
    expect(result.current.error?.action).toBeUndefined();
    expect(result.current.stale).toBe(false);
  });

  it("[start again] in the panel starts a new run (#19)", async () => {
    const q = question("k1", { target: { kind: "region", id: "a", name: "A" } });
    (api.startRun as Mock).mockResolvedValueOnce(run({ open_questions: [q] }))
      .mockResolvedValueOnce(run({ id: "run2", open_questions: [] }));
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", "region not found: gone"));
    (api.getRun as Mock).mockResolvedValueOnce(run({ open_questions: [q] }));
    render(<AugHost regions={[region("a")]} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    const edit = await screen.findByTestId("augment-action-edit");
    await act(async () => fireEvent.click(edit));
    fireEvent.click(await screen.findByTestId("augment-restart"));
    await waitFor(() => expect(api.startRun).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByTestId("augment-error")).not.toBeInTheDocument());
  });

  it("an answer back after a reset changes nothing and asks for no re-read (#27)", async () => {
    const { result, onChanged } = await augmentation([question("k1")]);
    const out = deferred<unknown>();
    (api.answer as Mock).mockReturnValueOnce(out.promise);
    act(() => result.current.answer(question("k1"), "edit"));
    act(() => result.current.reset());
    await act(async () => out.resolve({ change: { id: "c-old", description: "gap:add", added_ids: [], reverted: false }, run: run(), changed: [] }));
    expect(result.current.run).toBeNull();
    expect(onChanged).not.toHaveBeenCalled();
    expect(result.current.changed).toEqual({});
  });

  it("an undo back after a reset asks for no re-read (#27)", async () => {
    (api.startRun as Mock).mockResolvedValueOnce(run({ history: [{ id: "c1", description: "gap:add", added_ids: [], reverted: false }] }));
    const onChanged = vi.fn();
    const { result } = renderHook(() => useAugmentation("w", { onChanged }));
    act(() => result.current.start());
    await waitFor(() => expect(result.current.run).not.toBeNull());
    const out = deferred<AugRun>();
    (api.revert as Mock).mockReturnValueOnce(out.promise);
    act(() => result.current.revert("c1"));
    act(() => result.current.reset());
    await act(async () => out.resolve(run()));
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("a reset while a write is out leaves the guard open (G-M7)", async () => {
    const { result } = await augmentation([question("k1")]);
    const out = deferred<unknown>();
    (api.answer as Mock).mockReturnValueOnce(out.promise);
    act(() => result.current.answer(question("k1"), "edit"));
    act(() => result.current.reset());
    (api.startRun as Mock).mockResolvedValueOnce(run({ id: "run2" }));
    act(() => result.current.start());
    expect(api.startRun).toHaveBeenCalledTimes(2);
    await act(async () => out.resolve({ change: null, run: run(), changed: [] }));
    await waitFor(() => expect(result.current.run?.id).toBe("run2"));
    expect(result.current.busy).toBe(false);
  });

  it("a refused answer keeps what was typed (#13, G-M15)", async () => {
    const { result } = await augmentation([question("k1")]);
    act(() => result.current.setDraft("k1", { statement: "typed" }));
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(400, "Bad Request", "nothing changes"));
    act(() => result.current.answer(question("k1"), "edit"));
    await waitFor(() => expect(result.current.error).toBeDefined());
    expect(result.current.drafts.k1).toEqual({ statement: "typed" });
  });

  it("an undo re-reads the world and the inspector (#12, G-M26, BLM § 5)", async () => {
    (api.startRun as Mock).mockResolvedValueOnce(run({ history: [{ id: "c1", description: "gap:add", added_ids: [], reverted: false }] }));
    const onChanged = vi.fn();
    const { result } = renderHook(() => useAugmentation("w", { onChanged }));
    act(() => result.current.start());
    await waitFor(() => expect(result.current.run).not.toBeNull());
    (api.revert as Mock).mockResolvedValueOnce(run());
    act(() => result.current.revert("c1"));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  });

  it("an ignore asks for no re-read; an answer that changes the world does", async () => {
    const { result, onChanged } = await augmentation([question("k1"), question("k2")]);
    (api.answer as Mock).mockResolvedValue({ change: null, changed: [], run: run({ open_questions: [question("k2")] }) });
    act(() => result.current.answer(question("k1"), "ignore"));
    await waitFor(() => expect(result.current.busy).toBe(false));
    expect(onChanged).not.toHaveBeenCalled();
    act(() => result.current.answer(question("k2"), "edit"));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  });
});

describe("#26: the regions picked for knowledge known nowhere", () => {
  it("a region picked for another item while an assign is out stays", async () => {
    const items = [
      { id: "k1", world_id: "w", statement: "one", title: "one", confidence: 1, provenance: { source: "input" } },
      { id: "k2", world_id: "w", statement: "two", title: "two", confidence: 1, provenance: { source: "input" } },
    ];
    (api.listUnscoped as Mock).mockResolvedValue(items);
    const out = deferred<unknown>();
    (api.setScopes as Mock).mockReturnValueOnce(out.promise);
    const regions = [region("r1"), region("r2")];
    let latest: Record<string, string> = {};
    function Page() {
      const [picks, setPicks] = useState<Record<string, string>>({});
      latest = picks;
      return <UnscopedPanel worldId="w" regions={regions} picks={picks} onPicks={setPicks} onChanged={() => {}} />;
    }
    render(<Page />);
    await waitFor(() => screen.getByTestId("unscoped-k1"));
    fireEvent.change(screen.getByTestId("unscoped-region-k1"), { target: { value: "r1" } });
    fireEvent.click(screen.getByTestId("unscoped-assign-k1"));
    fireEvent.change(screen.getByTestId("unscoped-region-k2"), { target: { value: "r2" } });
    await act(async () => out.resolve({ region_ids: ["r1"] }));
    await waitFor(() => expect(api.listUnscoped).toHaveBeenCalledTimes(2));
    expect(latest).toEqual({ k2: "r2" });
  });
});

describe("#3: the question card in the screen's words, from what the server really sends", () => {
  const regions = [region("r1", 0.1, 0.1, "Saltwake"), region("r2", 0.5, 0.5, "Ironcrag")];
  const connections: ConnectionEdge[] = [{ world_id: "w", source_region_id: "r2", target_region_id: "r1", kind: "route", weight: 0.5 }];
  // as questions.py builds them with no LLM: the English template, the raw kind in the name
  const conn: AugQuestion = {
    id: "q1", issue_id: "i1", issue_key: "orphan:connection:r1|r2|route::", type: "orphan",
    text: "Saltwake – Ironcrag (route) is tied to no place. Where does it belong?", actions: ["edit", "ignore"], needs: {},
    target: { kind: "connection", id: "r1|r2|route", name: "Saltwake – Ironcrag (route)",
      connection: { world_id: "w", a_region_id: "r1", b_region_id: "r2", kind: "route" } },
  };
  const dangling: AugQuestion = {
    id: "q2", issue_id: "i2", issue_key: "dangling:connection:r1|r2|route:wiki_prior_ref:p-gone", type: "dangling",
    text: "Saltwake – Ironcrag (route) points at something that is gone (wiki_prior_ref). Re-point or clear?",
    actions: ["edit", "remove", "ignore"], needs: { edit: ["ref"] }, ref_kind: "prior",
    target: { kind: "connection", id: "r1|r2|route", name: "Saltwake – Ironcrag (route)", field: "wiki_prior_ref",
      connection: { world_id: "w", a_region_id: "r1", b_region_id: "r2", kind: "route" } },
  };

  it("the head is the issue, the kind and the world's name; the question is this screen's; no server text", async () => {
    (api.startRun as Mock).mockResolvedValueOnce(run({ open_questions: [conn, dangling] }));
    render(<AugHost regions={regions} connections={connections} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    const cards = await screen.findAllByTestId("augment-question");
    const route = enumLabel("connectionKind", "route");
    expect(cards[0]).toHaveTextContent(enumLabel("augmentationIssue", "orphan"));
    expect(cards[0]).toHaveTextContent(t("augment.target.connection"));
    expect(cards[0]).toHaveTextContent(`Saltwake – Ironcrag · ${route}`);
    expect(cards[0]).toHaveTextContent(t("augment.ask.orphan"));
    expect(cards[1]).toHaveTextContent(t("augment.ask.dangling", { kind: t("augment.refKind.prior") }));
    expect(cards[1]).toHaveTextContent(fieldLabel("wiki_prior_ref"));
    const text = screen.getByTestId("augment-panel").textContent ?? "";
    for (const raw of ["(route)", "wiki_prior_ref", "Re-point", "tied to no place"]) expect(text).not.toContain(raw);
  });

  it("a change names what it changed from the world too", async () => {
    (api.startRun as Mock).mockResolvedValueOnce(run({ open_questions: [conn] }));
    const change = { id: "c1", description: "orphan:edit", added_ids: [], reverted: false };
    (api.answer as Mock).mockResolvedValueOnce({ change, changed: [conn.target], run: run({ answers: 1, history: [change] }) });
    render(<AugHost regions={regions} connections={connections} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    const edit = await screen.findByTestId("augment-action-edit");
    await act(async () => fireEvent.click(edit));
    const line = await screen.findByTestId("augment-change");
    expect(line).toHaveTextContent(`Saltwake – Ironcrag · ${enumLabel("connectionKind", "route")}`);
    expect(line).not.toHaveTextContent("(route)");
  });

  it("ignored and kept lines say which issue; the kept count is the kept, not the ignored", async () => {
    (api.startRun as Mock).mockResolvedValueOnce(run({
      ignored_keys: ["low_confidence:region:r1::", "unscoped:region:r1::"],
      kept_keys: ["gap:region:r2::"],
    }));
    render(<AugHost regions={regions} connections={connections} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    const ignored = await screen.findAllByTestId("augment-ignored");
    expect(ignored.map((x) => x.querySelector("span")?.textContent)).toEqual([
      `${enumLabel("augmentationIssue", "low_confidence")} · Saltwake`,
      `${enumLabel("augmentationIssue", "unscoped")} · Saltwake`,
    ]);
    expect(screen.getByTestId("augment-kept").querySelector("summary")).toHaveTextContent(t("label.augmentKept", { n: 1 }));
  });
});

describe("#17, #35: the build report's counts", () => {
  const report = (over: Partial<BuildReport>): BuildReport => ({ world_id: "w", regions_created: 1, connections_created: 0,
    entities_created: 0, knowledge_created: 0, corroborations_created: 0, warnings: [], unscoped_knowledge_ids: [],
    llm_calls: 0, embedding_calls: 0, replaced: false, closed_session_ids: [], ok: true, ...over });

  it("nothing carried — the server's zeros — shows no carried line; seeds alone do", () => {
    const { unmount } = render(<BuildReportPanel report={report({ carried_npcs: 0, carried_seeds: 0 })} />);
    expect(screen.queryByTestId("build-report-carried")).not.toBeInTheDocument();
    unmount();
    render(<BuildReportPanel report={report({ carried_npcs: 0, carried_seeds: 2 })} />);
    expect(screen.getByTestId("build-report-carried")).toHaveTextContent(t("notice.buildCarried", { npcs: 0, seeds: 2 }));
  });

  it("where there is no tab to open (the home) the unscoped count is said", () => {
    const { unmount } = render(<BuildReportPanel report={report({ unscoped_knowledge_ids: ["k1", "k2"] })} />);
    expect(screen.getByTestId("build-report-unscoped-count")).toHaveTextContent(t("build.report.unscoped", { n: 2 }));
    expect(screen.queryByTestId("build-report-unscoped")).not.toBeInTheDocument();
    unmount();
    render(<BuildReportPanel report={report({ unscoped_knowledge_ids: ["k1"] })} onShowUnscoped={() => {}} />);
    expect(screen.getByTestId("build-report-unscoped")).toBeInTheDocument();
    expect(screen.queryByTestId("build-report-unscoped-count")).not.toBeInTheDocument();
  });
});

describe("#38: smaller behaviours of the augmentation tab", () => {
  it("a stopped run and a converged run say so in a sentence (I3, BR-V8-17)", async () => {
    (api.startRun as Mock).mockResolvedValueOnce(run({ status: "stopped" })).mockResolvedValueOnce(run({ status: "converged" }));
    render(<AugHost regions={[region("a")]} />);
    fireEvent.click(screen.getByTestId("augment-find"));
    expect(await screen.findByText(t("notice.augmentStopped"))).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("augment-find"));
    expect(await screen.findByText(t("notice.augmentConverged"))).toBeInTheDocument();
    expect(screen.queryByText(t("notice.augmentStopped"))).not.toBeInTheDocument();
  });

  it("[다시 묻기] waits for a write that is out (A4: one shared guard)", async () => {
    const { result } = await augmentation([question("k1")]);
    const out = deferred<unknown>();
    (api.answer as Mock).mockReturnValueOnce(out.promise);
    act(() => result.current.answer(question("k1"), "edit"));
    act(() => result.current.unignore("gap:region:a::"));
    expect(api.unignore).not.toHaveBeenCalled();
    await act(async () => out.resolve({ change: null, changed: [], run: run() }));
  });

  it("a 404 with the run alive shows the run as the server has it now (A6)", async () => {
    const { result } = await augmentation([question("k1")]);
    (api.answer as Mock).mockRejectedValueOnce(new HttpError(404, "Not Found", "gone"));
    (api.getRun as Mock).mockResolvedValueOnce(run({ answers: 3, open_questions: [question("k2")] }));
    act(() => result.current.answer(question("k1"), "edit"));
    await waitFor(() => expect(result.current.run?.open_questions.map((q) => q.issue_key)).toEqual(["k2"]));
    expect(result.current.run?.answers).toBe(3);
  });
});

describe("#30: a folded server line wraps", () => {
  it("the error's original text breaks anywhere, so a long id does not push the page sideways", () => {
    render(<InlineError error={{ title: "x", raw: "region-with-a-very-long-unbroken-identifier-0123456789" }} />);
    expect(screen.getByText(/very-long-unbroken/).closest("details")).toHaveClass("[overflow-wrap:anywhere]");
  });
});
