// V6 new GM parts (code plan Step 4): the head with a confirmed end, the map pane in words,
// turn tools, the result band, the event card and form, the tabs and the layout
// (BR-V6-02/03/04/06/07/13/14/26/27/31/34, TP-V6-10/11/14/15).
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { ENUM_VALUES, enumLabel, numberWithMeaning } from "../format";
import { HttpError } from "../api/http";
import { EventCard } from "../features/gm/EventCard";
import { EMPTY_DRAFT, EventForm, type EventDraft } from "../features/gm/EventForm";
import { ClosedBanner, GmHeader } from "../features/gm/GmHeader";
import { GmLayout } from "../features/gm/GmLayout";
import { GmTabs, type GmTab } from "../features/gm/GmTabs";
import { MapPane, badgeOf } from "../features/gm/MapPane";
import { TurnBand, outcomeOf } from "../features/gm/TurnBand";
import { TurnTools } from "../features/gm/TurnTools";
import { t } from "../i18n";
import { WorldMap } from "../map";
import type { GameSession, Region, SessionEvent, TurnResult, WorldState } from "../types";
import { useState } from "react";

const OPEN: GameSession = { id: "s1", world_id: "w", status: "open", turn: 3, created_at: "2026-10-08T05:05:00Z" };
const regions: Region[] = [
  { id: "a", name: "Harbor", level: "town", x: 0.2, y: 0.3 } as Region,
  { id: "b", name: "Moor", level: "town", x: 0.6, y: 0.6 } as Region,
];
const STATE: WorldState = {
  session_id: "s1",
  turn: 3,
  player_region_id: "a",
  regions: [
    { region_id: "a", region_name: "Harbor", distortion: 0.6, feedback_share: 0, active_rumors: 3, promoted_rumors: 1, deed_rumors: 1, active_events: 0 },
    { region_id: "b", region_name: "Moor", distortion: 0.1, feedback_share: 0, active_rumors: 0, promoted_rumors: 0, deed_rumors: 0, active_events: 0 },
  ],
};

function deferred<T>() {
  let resolve: (v: T) => void = () => {};
  let reject: (e: unknown) => void = () => {};
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("GmHeader (BR-V6-13/26, TP-V6-10)", () => {
  const props = () => ({
    session: OPEN,
    worldName: "엠버리프 섬",
    options: [
      { value: "s1", label: "3턴째 · 진행 중 · …" },
      { value: "s0", label: "9턴째 · 닫힘 · …", group: "끝난 세션" },
    ],
    onRetrySessions: vi.fn(),
    onPick: vi.fn(),
    onNew: vi.fn().mockResolvedValue(undefined),
    onEnd: vi.fn().mockResolvedValue(undefined),
  });

  it("ends a session only after asking; a refused end stays in the dialog with the sentence", async () => {
    const p = props();
    p.onEnd.mockRejectedValueOnce(new HttpError(409, "Conflict", '{"detail":"a turn","code":"turn_running"}'));
    render(<GmHeader {...p} />);
    expect(screen.getByRole("heading", { name: "GM · 엠버리프 섬" })).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("session-close-btn"));
    expect(p.onEnd).not.toHaveBeenCalled();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent(t("confirm.endSession"));
    await act(async () => fireEvent.click(screen.getByTestId("session-close-confirm")));
    expect(p.onEnd).toHaveBeenCalledTimes(1);
    expect(within(screen.getByRole("dialog")).getByRole("alert")).toHaveTextContent(t("error.turn_running.title"));
    await act(async () => fireEvent.click(screen.getByTestId("session-close-confirm")));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(p.onEnd).toHaveBeenCalledTimes(2);
  });

  it("an ended session has no end button; the picker groups ended sessions; a list failure offers a retry", () => {
    const p = props();
    render(<GmHeader {...p} session={{ ...OPEN, status: "closed" }}
      sessionsError={{ title: "x", code: "network" }} />);
    expect(screen.queryByTestId("session-close-btn")).not.toBeInTheDocument();
    const select = screen.getByTestId("session-select");
    expect(within(select).getByRole("group", { name: "끝난 세션" })).toBeInTheDocument();
    fireEvent.change(select, { target: { value: "s0" } });
    expect(p.onPick).not.toHaveBeenCalled(); // choosing moves nowhere (review #9)
    fireEvent.click(screen.getByTestId("session-open-btn"));
    expect(p.onPick).toHaveBeenCalledWith("s0");
    fireEvent.click(within(screen.getByTestId("sessions-error")).getByRole("button"));
    expect(p.onRetrySessions).toHaveBeenCalled();
  });

  it("a new session goes once however fast it is pressed; both buttons wait while a bulk run goes", async () => {
    const p = props();
    const hold = deferred<void>();
    p.onNew.mockReturnValue(hold.promise);
    const { rerender } = render(<GmHeader {...p} />);
    const btn = screen.getByTestId("session-new-btn");
    fireEvent.click(btn);
    fireEvent.click(btn);
    expect(p.onNew).toHaveBeenCalledTimes(1);
    expect(btn).toHaveAttribute("aria-disabled", "true");
    await act(async () => hold.resolve());
    rerender(<GmHeader {...p} locked />);
    expect(screen.getByTestId("session-new-btn")).toBeDisabled();
    expect(screen.getByTestId("session-close-btn")).toBeDisabled();
  });

  it("the ended-session line says the record stays", () => {
    render(<ClosedBanner />);
    expect(screen.getByTestId("gm-closed-banner")).toHaveTextContent(t("notice.sessionEnded"));
  });
});

describe("MapPane (BR-V6-27/31/32, TP-V6-15)", () => {
  const base = {
    world: { world_id: "w", regions, connections: [] } as never,
    selectedId: null,
    playerRegionId: "a",
    mapUrl: null,
    mapName: null,
    onToggle: vi.fn(),
    onSelect: vi.fn(),
    onMapFile: vi.fn(),
  };

  it("badges count the rumors going round, with ✦ for the player's story; none for a quiet region", () => {
    expect(badgeOf(STATE)).toEqual({ a: "3 ✦1" });
    render(<MapPane {...base} state={STATE} overlayOn />);
    expect(screen.getByTestId("region-badge-a")).toHaveTextContent("3 ✦1");
    expect(screen.queryByTestId("region-badge-b")).not.toBeInTheDocument();
    const legend = screen.getByTestId("gm-state-legend");
    for (const key of ["label.legendColor", "label.legendCount", "label.legendDeed"]) expect(legend).toHaveTextContent(t(key));
    expect(legend.textContent).not.toMatch(/\d\/\d/); // the old "2/0" reading is gone
  });

  it("with the overlay off the map has no colour or badge", () => {
    render(<MapPane {...base} state={STATE} overlayOn={false} />);
    expect(screen.getByTestId("gm-state-toggle")).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByTestId("region-badge-a")).not.toBeInTheDocument();
    expect(screen.queryByTestId("gm-state-legend")).not.toBeInTheDocument();
  });

  it("names come from the map of names; pressing a region chooses it", () => {
    const nameOf = (_k: string, id: string, _f: string, fb: string) => (id === "a" ? "솔트웨이크 항구" : fb);
    const onSelect = vi.fn();
    render(<MapPane {...base} nameOf={nameOf} onSelect={onSelect} overlayOn={false} />);
    expect(screen.getByTestId("region-label-a")).toHaveTextContent("솔트웨이크 항구");
    fireEvent.click(screen.getByTestId("region-marker-b"));
    expect(onSelect).toHaveBeenCalledWith("b");
  });

  it("the GM map does not drag (RE-F05)", () => {
    const onMove = vi.fn();
    render(<WorldMap mode="gm" label="map" regions={regions} connections={[]} onSelect={vi.fn()} onMove={onMove} />);
    const marker = screen.getByTestId("region-marker-a");
    const svg = marker.closest("svg") as SVGSVGElement;
    fireEvent.pointerDown(marker, { clientX: 100, clientY: 100 });
    fireEvent.pointerMove(svg, { clientX: 160, clientY: 120 });
    fireEvent.pointerUp(svg, { clientX: 160, clientY: 120 });
    expect(onMove).not.toHaveBeenCalled();
  });
});

describe("TurnTools (BR-V6-06/23)", () => {
  const props = () => ({
    closed: false,
    advancing: false,
    suggesting: false,
    bulk: null,
    suggestN: 2,
    maxSuggest: 3,
    onSuggestN: vi.fn(),
    onAdvance: vi.fn(),
    onSuggest: vi.fn(),
    onGenerateAll: vi.fn(),
    onRegenAll: vi.fn(),
  });

  it("without an LLM the LLM buttons are off and say why in their title; no second notice", () => {
    render(<TurnTools {...props()} llmOff />);
    for (const id of ["suggest-events-btn", "generate-all-btn", "regen-all-btn"]) {
      expect(screen.getByTestId(id)).toBeDisabled();
      expect(screen.getByTestId(id)).toHaveAttribute("title", t("llm.required"));
    }
    expect(screen.getByTestId("advance-turn-btn")).not.toBeDisabled();
    expect(screen.queryByText(t("llm.required"))).not.toBeInTheDocument();
  });

  it("every region's rumors again only after asking; a bulk run holds the turn and the bulk buttons", () => {
    const p = props();
    const { rerender } = render(<TurnTools {...p} />);
    fireEvent.click(screen.getByTestId("regen-all-btn"));
    expect(p.onRegenAll).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("regen-all-confirm"));
    expect(p.onRegenAll).toHaveBeenCalledTimes(1);
    rerender(<TurnTools {...p} bulk={{ done: 2, total: 5, failed: 1 }} />);
    expect(screen.getByTestId("advance-turn-btn")).toBeDisabled();
    expect(screen.getByTestId("generate-all-btn")).toBeDisabled();
    expect(screen.getByTestId("generate-progress")).toHaveTextContent(t("progress.done", { done: 2, total: 5 }));
  });

  it("the turn button waits while its turn runs, and is off on an ended session", () => {
    const { rerender } = render(<TurnTools {...props()} advancing />);
    expect(screen.getByTestId("advance-turn-btn")).toHaveAttribute("aria-disabled", "true");
    rerender(<TurnTools {...props()} closed />);
    expect(screen.getByTestId("advance-turn-btn")).toBeDisabled();
  });
});

describe("TurnBand (Q2=A, BR-V6-07)", () => {
  const change = (region_id: string, rumors_added: string[] = []) => ({
    region_id, region_name: region_id.toUpperCase(), promoted: [], demoted: [], pruned: [],
    events_applied: [], events_resolved: [], rumors_added,
  });
  const result = (over: Partial<TurnResult> = {}) =>
    ({ session_id: "s1", turn: 5, promoted_ids: [], demoted_ids: [], applied_event_ids: [], resolved_event_ids: [], ...over }) as TurnResult;

  it("names the turn and the regions that changed; a name chooses that region; close folds it", () => {
    const onPick = vi.fn();
    const onClose = vi.fn();
    const outcome = outcomeOf(result({ region_changes: [change("a", ["r1"]), change("b")], budget_exhausted: true }));
    render(<TurnBand outcome={outcome} onPickRegion={onPick} onClose={onClose} />);
    const band = screen.getByTestId("turn-band");
    expect(band).toHaveTextContent(t("notice.turnPassedGm", { n: 5 }));
    expect(band).toHaveTextContent(t("notice.turnBudget"));
    expect(screen.queryByTestId("turn-band-region-b")).not.toBeInTheDocument(); // nothing changed there
    fireEvent.click(screen.getByTestId("turn-band-region-a"));
    expect(onPick).toHaveBeenCalledWith("a");
    fireEvent.click(screen.getByTestId("turn-band-close"));
    expect(onClose).toHaveBeenCalled();
    expect(screen.getByTestId("turn-band-live")).toHaveAttribute("role", "status");
  });

  it("a turn that changed nothing reads as quiet", () => {
    render(<TurnBand outcome={outcomeOf(result({ region_changes: [change("a")] }))} onPickRegion={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByTestId("turn-band")).toHaveTextContent(t("notice.quietTurnGm", { n: 5 }));
  });
});

describe("EventCard (BR-V6-09/24/25/27)", () => {
  const ev = (over: Partial<SessionEvent> = {}): SessionEvent => ({
    id: "e1", session_id: "s1", region_id: "a", category: "plague", description: "Fever", magnitude: 0.5,
    lifecycle: "one_shot", status: "suggested", created_turn: 1, contributions: {}, ...over,
  });

  it("reads in words, never raw values or bare numbers", () => {
    render(<EventCard event={ev()} regionName="항구" closed={false} onApprove={vi.fn()} onDiscard={vi.fn()}
      onResolve={vi.fn()} onPickRegion={vi.fn()} />);
    const card = screen.getByTestId("event-e1");
    expect(card).toHaveTextContent(enumLabel("eventStatus", "suggested"));
    expect(card).toHaveTextContent(enumLabel("eventCategory", "plague"));
    expect(card).toHaveTextContent(enumLabel("eventLifecycle", "one_shot"));
    expect(card).toHaveTextContent(numberWithMeaning("magnitude", 0.5));
    expect(card.textContent).not.toMatch(/\bone_shot\b|\bsuggested\b|\bm0\.\d/);
    expect(screen.getByTestId("event-status-e1").className).not.toMatch(/danger/);
  });

  it("one write per card at a time; the region name chooses the region", async () => {
    const hold = deferred<void>();
    const onApprove = vi.fn().mockReturnValue(hold.promise);
    const onPick = vi.fn();
    render(<EventCard event={ev()} regionName="항구" closed={false} onApprove={onApprove} onDiscard={vi.fn()}
      onResolve={vi.fn()} onPickRegion={onPick} />);
    fireEvent.click(screen.getByTestId("approve-e1"));
    fireEvent.click(screen.getByTestId("approve-e1"));
    expect(onApprove).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("discard-e1")).toHaveAttribute("aria-disabled", "true");
    await act(async () => hold.resolve());
    fireEvent.click(screen.getByTestId("event-region-e1"));
    expect(onPick).toHaveBeenCalled();
  });

  it("an active event is resolved, a suggestion never (BR-U7-7)", () => {
    render(<EventCard event={ev({ status: "active" })} regionName="항구" closed={false} onApprove={vi.fn()}
      onDiscard={vi.fn()} onResolve={vi.fn()} onPickRegion={vi.fn()} />);
    expect(screen.getByTestId("resolve-e1")).toBeInTheDocument();
    expect(screen.queryByTestId("approve-e1")).not.toBeInTheDocument();
  });
});

describe("EventForm (UX-38, BR-V6-14, TP-V6-11)", () => {
  function Harness({ onCreate }: { onCreate: (b: unknown) => Promise<boolean> }) {
    const [draft, setDraft] = useState<EventDraft>(EMPTY_DRAFT);
    return <EventForm regionId="a" closed={false} draft={draft} onDraft={setDraft} onCreate={onCreate} />;
  }

  it("labels every field; an empty or blank description keeps [create] off", () => {
    render(<Harness onCreate={vi.fn()} />);
    for (const key of ["label.eventCategory", "label.eventWhat", "label.eventLifecycle"]) expect(screen.getByLabelText(t(key))).toBeInTheDocument();
    expect(screen.getByTestId("event-create-btn")).toBeDisabled();
    fireEvent.change(screen.getByTestId("event-description"), { target: { value: "   " } });
    expect(screen.getByTestId("event-create-btn")).toBeDisabled();
    const options = [...(screen.getByTestId("event-lifecycle") as HTMLSelectElement).options].map((o) => o.textContent);
    expect(options).toEqual([t("label.lifecycleDefault"), ...ENUM_VALUES.eventLifecycle.map((l) => enumLabel("eventLifecycle", l))]);
  });

  it("a saved event empties the description only; a refused one keeps it; the size label follows the thumb", async () => {
    const onCreate = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<Harness onCreate={onCreate} />);
    fireEvent.change(screen.getByTestId("event-category"), { target: { value: "festival" } });
    fireEvent.change(screen.getByTestId("event-magnitude"), { target: { value: "0.8" } });
    expect(screen.getByTestId("event-magnitude-label")).toHaveTextContent(numberWithMeaning("magnitude", 0.8));
    fireEvent.change(screen.getByTestId("event-description"), { target: { value: "  Lantern night " } });
    await act(async () => fireEvent.click(screen.getByTestId("event-create-btn")));
    expect(onCreate).toHaveBeenLastCalledWith({ region_id: "a", category: "festival", description: "Lantern night", magnitude: 0.8, lifecycle: null });
    expect(screen.getByTestId("event-description")).toHaveValue("  Lantern night ");
    await act(async () => fireEvent.click(screen.getByTestId("event-create-btn")));
    expect(screen.getByTestId("event-description")).toHaveValue("");
    expect(screen.getByTestId("event-category")).toHaveValue("festival");
  });
});

describe("GmTabs and GmLayout (BR-V6-02/03/04/34, TP-V6-14)", () => {
  function Tabbed() {
    const [tab, setTab] = useState<GmTab>("region");
    return (
      <GmTabs tab={tab} onTab={setTab} suggested={2} region={<p>R</p>} events={<p>E</p>} seeds={<p>S</p>}
        timeline={<p>T</p>} deeds={<p>D</p>} />
    );
  }

  it("five tabs in a tablist, arrow keys move, suggestions waiting on the events tab", async () => {
    render(<Tabbed />);
    const list = screen.getByRole("tablist", { name: t("label.gmTabs") });
    const tabs = within(list).getAllByRole("tab");
    expect(tabs.map((x) => x.querySelector("[data-testid^='gm-tab-']")?.textContent)).toEqual(["region", "events", "seeds", "timeline", "deeds"].map((k) => t(`tab.${k}`)));
    expect(screen.getByTestId("events-badge")).toHaveTextContent("2");
    expect(screen.getByTestId("events-badge").textContent).toBe(`${t("label.waitingSuggestions")} 2`); // the number says what (43(f))
    expect(screen.getByRole("tabpanel")).toHaveTextContent("R");
    tabs[0].focus();
    fireEvent.keyDown(tabs[0], { key: "ArrowRight" });
    await waitFor(() => expect(tabs[1]).toHaveFocus());
  });

  const s = {
    header: <div data-testid="L-header" />, banner: null, player: <div data-testid="L-player" />,
    map: <div data-testid="L-map" />, tools: <div data-testid="L-tools" />, error: <div data-testid="L-error" />,
    band: <div data-testid="L-band" />, tabs: <div data-testid="L-tabs" />,
  };
  const order = () => [...document.querySelectorAll("[data-testid^='L-']")].map((e) => e.getAttribute("data-testid"));

  it("wide: the map beside a panel of tools, error, band and tabs", () => {
    render(<GmLayout wide s={s} />);
    const aside = screen.getByRole("region", { name: t("label.gmPanel") });
    for (const id of ["L-tools", "L-error", "L-band", "L-tabs"]) expect(aside).toContainElement(screen.getByTestId(id));
    expect(aside).not.toContainElement(screen.getByTestId("L-map"));
    expect(order()).toEqual(["L-header", "L-player", "L-map", "L-tools", "L-error", "L-band", "L-tabs"]);
  });

  it("narrow: one column — head, player, tools, band, map, tabs", () => {
    render(<GmLayout wide={false} s={s} />);
    expect(screen.queryByRole("region", { name: t("label.gmPanel") })).not.toBeInTheDocument();
    expect(order()).toEqual(["L-header", "L-player", "L-tools", "L-error", "L-band", "L-map", "L-tabs"]);
  });
});
