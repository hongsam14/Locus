// V4 play parts (FD frontend-components § 3.3, BR-V4-10/11/13/14/23, TP-V4-6/7/13): names
import * as React from "react";
// from the name map with the English behind them, words instead of numbers, a blocked way
// that says why, a map that only points, one result band, a labelled box and named sheets.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ActionBar, TurnStatus } from "../features/play/ActionBar";
import { ActionDock } from "../features/play/ActionDock";
import { DialoguePanel } from "../features/play/DialoguePanel";
import { MovePanel } from "../features/play/MovePanel";
import { namedPayload, type NameOf } from "../features/play/names";
import { NpcList } from "../features/play/NpcList";
import { PlayHeader } from "../features/play/PlayHeader";
import { PlayLog } from "../features/play/PlayLog";
import { PlayMap } from "../features/play/PlayMap";
import { KnownHere, SceneText } from "../features/play/RegionScene";
import { ResultBand } from "../features/play/ResultBand";
import { TalkSheet } from "../features/play/TalkSheet";
import { enumLabel, turnAt, turnLabel } from "../format";
import type { TurnOutcome } from "../hooks";
import { t } from "../i18n";
import { WorldMap } from "../map";
import { Button } from "../ui";
import type { MoveOption, NPC, Region, RegionView, TimelineEntry } from "../types";

vi.mock("../api", () => ({
  api: { startDialogue: vi.fn().mockResolvedValue({ messages: [] }), dialogueHistory: vi.fn(), say: vi.fn() },
}));

const KO: Record<string, Record<string, Record<string, string>>> = {
  regions: {
    top: { name: "올더무어" },
    a: { name: "리버턴", description: "강가의 작은 마을." },
    b: { name: "할로" },
  },
  npcs: { n1: { name: "마라", role: "여관 주인" } },
  event_seeds: { s1: { title: "늑대의 겨울" } },
};
const korean: NameOf = (kind, id, field, fallback) => KO[kind]?.[id]?.[field] ?? fallback;

const MARA: NPC = {
  id: "n1", world_id: "w", name: "Mara", role: "innkeeper", description: "", home_region_id: "a",
  traits: [], provenance: { source: "input" },
};
const MOVES: MoveOption[] = [
  { region_id: "b", region_name: "Hollow", kind: "route", weight: 0.5, cost_turns: 2, passable: true },
  { region_id: "c", region_name: "Crag", kind: "blocked", weight: 0, cost_turns: 0, passable: false, reason: "blocked pass" },
];

function view(over: Partial<RegionView> = {}): RegionView {
  return {
    session_id: "s1", turn: 4, player: { id: "p", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 4 },
    region_id: "a", region_name: "Riverton", level: "town", description: "A river town.",
    level_path: ["Aldermoor", "Riverton"], level_path_ids: ["top", "a"],
    npcs: [MARA], facts: [], hearsay: [], rumors: [], moves: MOVES,
    turn_running: false, llm_available: true, ...over,
  };
}

const inRouter = (ui: React.ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe("TP-V4-6: names from the map, the English behind them", () => {
  it("the header: the path above the title, the title, the level and the turn in words", () => {
    const { unmount } = inRouter(<PlayHeader view={view()} closed={false} nameOf={korean} />);
    expect(screen.getByTestId("region-path")).toHaveTextContent("올더무어");
    expect(screen.getByTestId("region-path")).not.toHaveTextContent("리버턴"); // the title is not in its own path
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("리버턴");
    expect(screen.getByTestId("region-meta")).toHaveTextContent(`${enumLabel("regionLevel", "town")} · ${turnLabel(4)}`);
    unmount();
    inRouter(<PlayHeader view={view()} closed={false} />);
    expect(screen.getByTestId("region-path")).toHaveTextContent("Aldermoor");
    expect(screen.getByTestId("region-title")).toHaveTextContent("Riverton");
  });

  it("the scene text, people, moves and result lines take the map's names", () => {
    render(<SceneText view={view()} nameOf={korean} />);
    expect(screen.getByTestId("region-scene")).toHaveTextContent("강가의 작은 마을.");
    render(<NpcList npcs={[MARA]} nameOf={korean} onTalk={() => {}} />);
    expect(screen.getByTestId("npc-n1")).toHaveTextContent("마라");
    expect(screen.getByTestId("npc-n1")).toHaveTextContent("여관 주인");
    render(<MovePanel moves={MOVES} disabled={false} onMove={() => {}} nameOf={korean} />);
    expect(screen.getByTestId("move-b")).toHaveTextContent("할로");
    expect(screen.getByTestId("move-c")).toHaveTextContent("Crag"); // not in the map: English
    const outcome: TurnOutcome = {
      turn: 5, quiet: false, declaration: null,
      changes: [{ region_id: "b", region_name: "Hollow", promoted: [], demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: ["r1"] }],
    };
    render(<ResultBand outcome={outcome} nameOf={korean} onClose={() => {}} />);
    expect(screen.getByTestId("result-change-b")).toHaveTextContent("할로");
  });

  it("a log line finds its names by the ids in its payload; a name the map lacks stays", () => {
    const entries: TimelineEntry[] = [
      { id: "1", session_id: "s1", turn: 2, kind: "player_moved", summary: "",
        payload: { from_region_id: "a", from_region_name: "Riverton", to_region_id: "b", to_region_name: "Hollow", cost_turns: 1 } },
      { id: "3", session_id: "s1", turn: 4, kind: "player_waited", summary: "",
        payload: { region_id: "z", region_name: "Zed" } },
      { id: "2", session_id: "s1", turn: 3, kind: "npc_talked", summary: "",
        payload: { npc_id: "n1", npc_name: "Mara", region_id: "a", region_name: "Riverton" } },
    ];
    render(<PlayLog entries={entries} nameOf={korean} />);
    expect(screen.getByTestId("log-player_moved")).toHaveTextContent("리버턴");
    expect(screen.getByTestId("log-player_moved")).toHaveTextContent("할로"); // the to-region pair
    expect(screen.getByTestId("log-player_waited")).toHaveTextContent("Zed"); // not in the map: kept
    expect(screen.getByTestId("log-npc_talked")).toHaveTextContent("마라");
    expect(screen.getByTestId("log-npc_talked")).toHaveTextContent("리버턴"); // the region_id pair
    expect(screen.getByTestId("log-npc_talked")).toHaveTextContent(turnAt(3));
    expect(namedPayload({ seed_id: "s1", seed_title: "Wolf Winter" }, korean).seed_title).toBe("늑대의 겨울");
    expect(namedPayload({ region_name: "Old" }, korean)).toEqual({ region_name: "Old" }); // no id: unchanged
  });

  it("the dialogue names the NPC from the map; the talk sheet's title says it", async () => {
    render(
      <TalkSheet npc={MARA} nameOf={korean} onClose={() => {}}>
        <DialoguePanel bare sessionId="s1" npc={MARA} nameOf={korean} llmAvailable busy={false}
          onClose={() => {}} onEndTalk={() => {}} />
      </TalkSheet>,
    );
    expect(screen.getByRole("dialog", { name: t("dialogue.title", { name: "마라" }) })).toBeInTheDocument();
    expect(screen.getByTestId("talk-sheet")).toHaveAttribute("data-variant", "full");
    expect(within(screen.getByTestId("dialogue-panel")).queryByRole("heading")).not.toBeInTheDocument(); // bare
    await waitFor(() => expect(screen.getByTestId("dialogue-panel")).toHaveTextContent("여관 주인"));
  });
});

describe("TP-V4-7: moves and the map", () => {
  it("a blocked way stays as a grey row that says why, with no button; the server's reason is not shown", () => {
    render(<MovePanel moves={MOVES} disabled={false} onMove={() => {}} />);
    const row = screen.getByTestId("move-c");
    expect(screen.getByTestId("move-c-blocked")).toHaveTextContent(t("notice.moveBlocked"));
    expect(row).toHaveTextContent(enumLabel("travelBy", "blocked"));
    expect(row).not.toHaveTextContent("blocked pass");
    expect(screen.queryByTestId("move-c-btn")).not.toBeInTheDocument();
    expect(row.className).toMatch(/text-muted/);
    expect(screen.getByTestId("move-b")).toHaveTextContent(`${enumLabel("travelBy", "route")} · ${t("unit.turns", { n: 2 })}`);
    expect(screen.getByTestId("move-b")).not.toHaveTextContent("route");
  });

  it("the map points at a reachable row and moves no one; an unreachable press does nothing", () => {
    const regions: Region[] = [
      { id: "a", name: "Riverton", level: "town", position: { x: 0.4, y: 0.4 } },
      { id: "b", name: "Hollow", level: "town", position: { x: 0.6, y: 0.4 } },
      { id: "c", name: "Crag", level: "town", position: { x: 0.5, y: 0.6 } },
    ];
    const pick = vi.fn();
    render(<PlayMap view={view()} regions={regions} connections={[]} nameOf={korean} onPickReachable={pick} />);
    expect(screen.getByTestId("region-label-a")).toHaveTextContent("리버턴");
    fireEvent.click(screen.getByTestId("region-marker-c")); // blocked: not reachable
    expect(pick).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("region-marker-b"));
    expect(pick).toHaveBeenCalledWith("b");
  });

  it("the row the map pointed at is marked", () => {
    const { rerender } = render(<MovePanel moves={MOVES} disabled={false} onMove={() => {}} />);
    expect(screen.getByTestId("move-b")).not.toHaveAttribute("data-highlight");
    rerender(<MovePanel moves={MOVES} disabled={false} onMove={() => {}} highlightId="b" />);
    expect(screen.getByTestId("move-b")).toHaveAttribute("data-highlight", "true");
  });

  it("the world map is still a skeleton while the world's map is on its way", () => {
    render(<PlayMap view={view()} regions={null} connections={[]} onPickReachable={() => {}} />);
    expect(within(screen.getByTestId("play-map")).getByRole("status")).toBeInTheDocument();
  });

  it("play draws its picture inside the map so a close-up follows it; edit keeps the picture behind", () => {
    const regions: Region[] = [{ id: "a", name: "A", level: "town", position: { x: 0.5, y: 0.5 } }];
    const { container, unmount } = render(
      <WorldMap regions={regions} connections={[]} mode="play" label="map" background="blob:map" focus={{ id: "a", neighbors: [] }} />,
    );
    const image = screen.getByTestId("map-background");
    expect(image.tagName.toLowerCase()).toBe("image");
    expect(image.closest("svg")).not.toBeNull();
    expect(image).toHaveAttribute("width", "1000");
    expect(image).toHaveAttribute("height", "625");
    expect(container.querySelector("img")).toBeNull();
    unmount();
    const edit = render(<WorldMap regions={regions} connections={[]} mode="edit" label="map" background="blob:map" />);
    expect(edit.container.querySelector("img")).toHaveAttribute("src", "blob:map");
    expect(screen.queryByTestId("map-background")).not.toBeInTheDocument();
  });
});

describe("the result band (BR-V4-04, Q2=A)", () => {
  const change = { region_id: "a", region_name: "Riverton", promoted: [], demoted: [], pruned: [], events_applied: [], events_resolved: [], rumors_added: ["r1", "r2"] };

  it("says the turn, the regions that changed, and the GM's answer; [close] folds it", () => {
    const close = vi.fn();
    const outcome: TurnOutcome = {
      turn: 4, quiet: false, changes: [change],
      declaration: { text: "광장이 술렁인다.", record: "", lang: "ko", llm_calls: 0 },
    };
    render(<ResultBand outcome={outcome} onClose={close} />);
    const band = screen.getByTestId("result-band");
    // code review 01 #26: the live region is always there; the band comes into it
    expect(screen.getByTestId("result-live")).toHaveAttribute("role", "status");
    expect(screen.getByTestId("result-live")).toContainElement(band);
    expect(band).toHaveTextContent(t("story.turnPassed", { n: 4 }));
    expect(screen.getByTestId("result-change-a")).toHaveTextContent(t("notif.rumors_added", { n: 2 }));
    expect(within(band).getByTestId("narration-card")).toHaveTextContent("광장이 술렁인다.");
    expect(within(band).getByTestId("narration-fallback")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("result-band-close"));
    expect(close).toHaveBeenCalled();
  });

  it("a quiet turn says so; no outcome is no band", () => {
    const { rerender } = render(<ResultBand outcome={{ turn: 2, quiet: true, changes: [], declaration: null }} onClose={() => {}} />);
    expect(screen.getByTestId("result-band")).toHaveTextContent(t("story.quietTurn"));
    rerender(<ResultBand outcome={null} onClose={() => {}} />);
    expect(screen.queryByTestId("result-band")).not.toBeInTheDocument();
    expect(screen.getByTestId("result-live")).toBeEmptyDOMElement(); // still there, empty
  });
});

describe("the header's states (BR-V4-18/19)", () => {
  it("a closed session has its line and [home]; the GM notice waits while it is closed", () => {
    inRouter(<PlayHeader view={view({ gm_busy: true })} closed />);
    expect(screen.getByTestId("closed-banner")).toHaveTextContent(t("notice.sessionClosed"));
    expect(screen.getByTestId("play-home-link")).toHaveAttribute("href", "/");
    expect(screen.queryByTestId("gm-busy-notice")).not.toBeInTheDocument();
  });

  it("gm_busy says the GM is at work; absent is false", () => {
    const { unmount } = inRouter(<PlayHeader view={view({ gm_busy: true })} closed={false} />);
    expect(screen.getByTestId("gm-busy-notice")).toHaveTextContent(t("notice.gmBusy"));
    unmount();
    inRouter(<PlayHeader view={view()} closed={false} />);
    expect(screen.queryByTestId("gm-busy-notice")).not.toBeInTheDocument();
  });
});

describe("what is known, in words (BR-V4-10)", () => {
  const facts = Array.from({ length: 5 }, (_, i) => ({
    knowledge_id: `k${i}`, statement: `fact ${i}`, scope_type: "direct", is_hearsay: false, confidence: 0.9,
  }));
  const rumor = (id: string, origin: "deed" | "canonical") => ({
    id, session_id: "s1", region_id: "a", distorted_from_id: "k1", distorted_from_kind: "knowledge",
    statement: `rumor ${id}`, distortion_degree: 0.42, support: 0.73, confidence: 0.6, promoted: false, origin_kind: origin,
  });

  it("no number, no raw scope; distortion, belief and decay are words; your deed is your story", () => {
    const v = view({
      facts,
      hearsay: [{ knowledge_id: "h1", statement: "far tale", scope_type: "hearsay", is_hearsay: true, confidence: 0.4, path_decay: 0.55 }],
      rumors: [rumor("r1", "deed"), rumor("r2", "canonical")],
    });
    render(<KnownHere view={v} />);
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/\b0\.\d+\b/);
    expect(text).not.toMatch(/\bdirect\b|\bhearsay\b/);
    expect(screen.getByTestId("deed-badge-r1")).toHaveTextContent(t("label.yourStory"));
    expect(screen.queryByTestId("deed-badge-r2")).not.toBeInTheDocument();
    expect(screen.getAllByTestId(/^knowledge-item-/)).toHaveLength(5); // wide: all
  });

  it("a phone shows three and [show N more]", () => {
    render(<KnownHere view={view({ facts })} compact />);
    expect(screen.getAllByTestId(/^knowledge-item-/)).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: t("action.showMore", { n: 2 }) }));
    expect(screen.getAllByTestId(/^knowledge-item-/)).toHaveLength(5);
  });

  it("the log shows five lines on a phone, all on a wide screen", () => {
    const entries = Array.from({ length: 8 }, (_, i): TimelineEntry => ({
      id: `e${i}`, session_id: "s1", turn: i, kind: "player_waited", summary: "", payload: { region_name: "Riverton" },
    }));
    const { unmount } = render(<PlayLog entries={entries} compact />);
    expect(screen.getAllByTestId("log-player_waited")).toHaveLength(5);
    expect(screen.getByRole("button", { name: t("action.showMore", { n: 3 }) })).toBeInTheDocument();
    unmount();
    render(<PlayLog entries={entries} />);
    expect(screen.getAllByTestId("log-player_waited")).toHaveLength(8);
  });

  // code review 01 #28 (a): without a key [talk] still opens the past talk (BR-U5-29, BR-V4-18)
  it("without an AI key [talk] stays on and a line says only past talks can be read", () => {
    const onTalk = vi.fn();
    render(<NpcList npcs={[MARA]} onTalk={onTalk} talkNote={t("notice.talkNeedsKey")} />);
    expect(screen.getByTestId("npc-n1-talk-btn")).toBeEnabled();
    fireEvent.click(screen.getByTestId("npc-n1-talk-btn"));
    expect(onTalk).toHaveBeenCalledWith("n1");
    expect(screen.getByTestId("talk-note")).toHaveTextContent(t("notice.talkNeedsKey"));
  });
});

describe("TP-V4-13: labels, the focus ring, named sheets", () => {
  it("the declaration box has a visible label and no outline-none", () => {
    render(<ActionBar running={null} disabled={false} onWait={() => {}} onDeclare={async () => true} />);
    const box = screen.getByLabelText(t("label.declare"));
    expect(box).toBe(screen.getByTestId("declare-input"));
    expect(box.className).not.toMatch(/outline-none/);
    expect(screen.getByTestId("declare-btn")).toHaveTextContent(`${t("action.declare")} · ${t("unit.turns", { n: 1 })}`);
    expect(screen.getByTestId("wait-btn")).toHaveTextContent(`${t("action.wait")} · ${t("unit.turns", { n: 1 })}`);
  });

  it("code review 01 #7: [declare] keeps focus while its request is out, then the box gets it back", async () => {
    let answer: (v: boolean) => void = () => {};
    render(<ActionBar running={null} disabled={false} onWait={() => {}} onDeclare={() => new Promise<boolean>((r) => (answer = r))} />);
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "I sing" } });
    const btn = screen.getByTestId("declare-btn");
    btn.focus();
    fireEvent.click(btn);
    expect(btn).not.toBeDisabled(); // busy (aria-disabled), not native: focus stays
    expect(btn).toHaveFocus();
    expect(screen.getByTestId("declare-input")).toHaveAttribute("readonly");
    await act(async () => answer(true));
    expect(screen.getByTestId("declare-input")).toHaveFocus();
  });

  it("the turn's place: running, slow with [check again], a failed check with [check again]", () => {
    const run = { id: "r", session_id: "s1", action: { type: "wait" as const }, cost_turns: 2, status: "running" as const, started_turn: 1 };
    const recheck = vi.fn();
    const { rerender } = render(<TurnStatus running={run} onRecheck={recheck} />);
    expect(screen.getByTestId("turn-progress")).toHaveTextContent(t("play.running", { n: 2 }));
    rerender(<TurnStatus running={run} slow onRecheck={recheck} />);
    expect(screen.getByTestId("turn-slow")).toHaveTextContent(t("notice.turnSlow"));
    expect(screen.queryByTestId("turn-progress")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("turn-recheck"));
    rerender(<TurnStatus running={null} error={{ title: "서버에 닿지 못했어요." }} onRecheck={recheck} />);
    expect(screen.getByTestId("turn-error")).toHaveTextContent("서버에 닿지 못했어요.");
    fireEvent.click(screen.getByTestId("turn-recheck"));
    expect(recheck).toHaveBeenCalledTimes(2);
  });

  function Dock({ onDeclare, onMove }: { onDeclare: (s: string) => Promise<boolean>; onMove: (id: string) => void }) {
    const [open, setOpen] = React.useState(false);
    return (
      <ActionDock running={null} disabled={false} onWait={() => {}} onDeclare={onDeclare} moves={MOVES}
        onMove={onMove} moveOpen={open} onMoveOpenChange={setOpen} />
    );
  }

  it("the dock's declare sheet is named, closes when taken, stays when refused, and gives focus back", async () => {
    const onDeclare = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<Dock onDeclare={onDeclare} onMove={() => {}} />);
    expect(screen.queryByTestId("declare-input")).not.toBeInTheDocument(); // only while open
    const opener = screen.getByTestId("dock-declare");
    opener.focus();
    fireEvent.click(opener);
    const sheet = screen.getByRole("dialog", { name: t("action.declare") });
    expect(sheet).toHaveAttribute("data-variant", "sheet");
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "I sing" } });
    await act(async () => fireEvent.click(screen.getByTestId("declare-btn")));
    expect(screen.getByTestId("declare-sheet")).toBeInTheDocument(); // refused: open, text back
    expect(screen.getByTestId("declare-input")).toHaveValue("I sing");
    await act(async () => fireEvent.click(screen.getByTestId("declare-btn")));
    await waitFor(() => expect(screen.queryByTestId("declare-sheet")).not.toBeInTheDocument());
    await waitFor(() => expect(opener).toHaveFocus());
  });

  it("the move sheet lists the ways and closes on a choice; Esc closes it too", async () => {
    const onMove = vi.fn();
    render(<Dock onDeclare={async () => true} onMove={onMove} />);
    fireEvent.click(screen.getByTestId("dock-move"));
    const sheet = screen.getByRole("dialog", { name: t("label.whereToGo") });
    expect(within(sheet).getAllByRole("heading", { name: t("label.whereToGo") })).toHaveLength(1); // the list is bare
    fireEvent.click(within(sheet).getByTestId("move-b-btn"));
    expect(onMove).toHaveBeenCalledWith("b");
    await waitFor(() => expect(screen.queryByTestId("move-sheet")).not.toBeInTheDocument());
    fireEvent.click(screen.getByTestId("dock-move"));
    fireEvent.keyDown(screen.getByTestId("move-sheet"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByTestId("move-sheet")).not.toBeInTheDocument());
  });

  it("a closed session turns the dock off", () => {
    render(
      <ActionDock running={null} disabled closed onWait={() => {}} onDeclare={async () => true} moves={MOVES}
        onMove={() => {}} moveOpen={false} onMoveOpenChange={() => {}} />,
    );
    for (const id of ["dock-wait", "dock-declare", "dock-move"]) expect(screen.getByTestId(id)).toBeDisabled();
  });
});

describe("Button: busy and a caller's aria-disabled together (BR-V4-24)", () => {
  it("a caller's aria-disabled={undefined} does not undo busy; a caller's aria-disabled marks it off", () => {
    const onClick = vi.fn();
    const { rerender } = render(<Button busy aria-disabled={undefined} onClick={onClick}>x</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("aria-disabled", "true");
    rerender(<Button aria-disabled onClick={onClick}>x</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("aria-disabled", "true");
    rerender(<Button onClick={onClick}>x</Button>);
    expect(screen.getByRole("button")).not.toHaveAttribute("aria-disabled");
  });

  it("the action box's [wait] keeps focus while a turn runs and ignores the press", () => {
    const onWait = vi.fn();
    render(<ActionBar running={null} disabled={false} locked onWait={onWait} onDeclare={async () => true} />);
    const wait = screen.getByTestId("wait-btn");
    wait.focus();
    fireEvent.click(wait);
    expect(onWait).not.toHaveBeenCalled();
    expect(wait).toHaveFocus();
    expect(wait).not.toBeDisabled();
    expect(wait).toHaveAttribute("aria-disabled", "true");
  });
});

describe("code review 01 #10: locked actions ignore a press", () => {
  it("[declare], [move] and the move sheet's [move] do nothing while a turn runs", async () => {
    const onDeclare = vi.fn().mockResolvedValue(true);
    const onMove = vi.fn();
    const { unmount } = render(<ActionBar running={null} disabled={false} locked onWait={() => {}} onDeclare={onDeclare} />);
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "I sing" } });
    fireEvent.click(screen.getByTestId("declare-btn"));
    fireEvent.submit(screen.getByTestId("declare-input").closest("form") as HTMLFormElement);
    expect(onDeclare).not.toHaveBeenCalled();
    unmount();
    const panel = render(<MovePanel moves={MOVES} disabled={false} locked onMove={onMove} />);
    fireEvent.click(screen.getByTestId("move-b-btn"));
    expect(onMove).not.toHaveBeenCalled();
    panel.unmount();
    render(
      <ActionDock running={null} disabled={false} locked onWait={() => {}} onDeclare={onDeclare} moves={MOVES}
        onMove={onMove} moveOpen onMoveOpenChange={() => {}} />,
    );
    fireEvent.click(within(screen.getByTestId("move-sheet")).getByTestId("move-b-btn"));
    expect(onMove).not.toHaveBeenCalled();
  });
});

describe("code review 01 #14: a refusal belongs to the action it answered", () => {
  it("opening the declare sheet clears a move's refusal, so it is not shown as the declaration's", () => {
    const clear = vi.fn();
    render(
      <ActionDock running={null} disabled={false} onWait={() => {}} onDeclare={async () => true} moves={MOVES}
        onMove={() => {}} moveOpen={false} onMoveOpenChange={() => {}} refusal={{ title: "갈 수 없어요." }}
        onClearRefusal={clear} />,
    );
    expect(screen.getByTestId("action-error")).toHaveTextContent("갈 수 없어요.");
    fireEvent.click(screen.getByTestId("dock-declare"));
    expect(clear).toHaveBeenCalled();
  });
});
