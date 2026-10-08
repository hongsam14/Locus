import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../api";
import { HttpError, conflictKind, statusOf } from "../../api/http";
import { llmOff, useCapabilities } from "../../capabilities";
import { describeError, type DescribedError } from "../../errors";
import { useAction, useMounted } from "../../hooks";
import { lang } from "../../i18n";
import { InlineError, toast } from "../../ui";
import { DeedPanel } from "./DeedPanel";
import { EMPTY_DRAFT, type EventDraft, type NewEvent } from "./EventForm";
import { EventPanel } from "./EventPanel";
import { ClosedBanner, GmHeader } from "./GmHeader";
import { GmLayout } from "./GmLayout";
import { GmTabs, type GmTab } from "./GmTabs";
import { MapPane } from "./MapPane";
import { newLineIds, snapshotIds } from "./newLines";
import { PlayerStrip } from "./PlayerStrip";
import { RegionTab } from "./RegionTab";
import { SeedPanel } from "./SeedPanel";
import { sessionOptions } from "./sessionLabel";
import { TimelinePanel } from "./TimelinePanel";
import { TurnBand, outcomeOf, type GmTurnOutcome } from "./TurnBand";
import { TurnTools } from "./TurnTools";
import { useBulkRumors } from "./useBulkRumors";
import { useGmData, type GmWrite } from "./useGmData";
import type { GmSessionRead } from "./useGmSession";
import type { TimelineEntry } from "../../types";

/** One session's GM screen, inside the page's `key={sessionId}` (V6 BLM § 1.3, code plan
 * § 1.1 R-02): another session starts it afresh — the open tab, the result band, the "new"
 * marks, the error line, the folds and the event draft — and nothing the last session
 * asked for lands here. The page keeps the world, its names, the chosen region and the map
 * picture outside.
 *
 * Every GM write goes through `gmWrite`: the error line is cleared, the write runs, and on
 * success only what it changed is read again (AFTER); a refusal is told by kind (BLM § 6) —
 * a closed session re-reads the session, a running turn the player strip, a rumor gone the
 * region's rumors. A write asked for in a dialog (end, void) tells its refusal there. */
export function GmSessionView({
  sessionId,
  gm,
  wide,
  selected,
  onSelect,
  overlayOn,
  onToggleOverlay,
  mapUrl,
  mapName,
  onMapFile,
}: {
  sessionId: string;
  gm: GmSessionRead;
  wide: boolean;
  selected: string | null;
  onSelect(regionId: string | null): void;
  overlayOn: boolean;
  onToggleOverlay(): void;
  mapUrl: string | null;
  mapName: string | null;
  onMapFile(file: File): void;
}) {
  const navigate = useNavigate();
  const mounted = useMounted();
  const noLlm = llmOff(useCapabilities());
  const session = gm.session;
  const closed = !session || session.status === "closed";
  const nameOf = gm.names.nameOf;
  // a region of the last world is not read for this session while it loads (review #25)
  const data = useGmData(sessionId, session ? selected : null, { session: gm.reloadSession, sessions: gm.reloadSessions });

  const [tab, setTab] = useState<GmTab>("region");
  const [outcome, setOutcome] = useState<GmTurnOutcome | null>(null);
  // the "new" marks: the record as it was when the turn was pressed, then the lines the first
  // answer after the turn brought — fixed, so later GM writes are not marked (review #6, #23)
  const [before, setBefore] = useState<{ ids: Set<string> | null; seen: TimelineEntry[] | undefined } | null>(null);
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const [writeError, setWriteError] = useState<DescribedError>();
  const [draft, setDraft] = useState<EventDraft>(EMPTY_DRAFT);
  const [formOpen, setFormOpen] = useState(false);
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [suggestN, setSuggestN] = useState(1);
  const [cap, setCap] = useState<number | null>(null);
  const tabsRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  // Where the focus goes after a write took away the control that had it (code review 01 #1,
  // #8, #9): a test id, focused once the element is there and no dialog is open (re-reads
  // and the dialog's own close come later, on no render of ours), tried for three seconds so
  // it never jumps away from what the GM did next.
  const [focusTo, setFocusTo] = useState<string | null>(
    (location.state as { focus?: string } | null)?.focus ?? null,
  );
  useEffect(() => {
    if (!focusTo) return;
    const tryFocus = () => {
      if (document.querySelector('[role="dialog"]')) return false;
      const el = document.querySelector<HTMLElement>(`[data-testid="${focusTo}"]`);
      if (!el || (el instanceof HTMLButtonElement && el.disabled)) return false;
      el.focus();
      return true;
    };
    if (tryFocus()) {
      setFocusTo(null);
      return;
    }
    const started = Date.now();
    const timer = setInterval(() => {
      if (tryFocus() || Date.now() - started > 3000) {
        clearInterval(timer);
        setFocusTo(null);
      }
    }, 50);
    return () => clearInterval(timer);
  }, [focusTo]);
  const go = (id: string) => navigate(`/gm/${encodeURIComponent(id)}`, { state: { focus: "session-select" } });
  const maxSuggest = cap ?? data.worldState.data?.max_event_suggestions ?? 5;

  useEffect(() => {
    if (!before || !data.timeline.data || data.timeline.data === before.seen) return;
    setNewIds(newLineIds(before.ids, data.timeline.data));
    setBefore(null);
  }, [before, data.timeline.data]);

  function told(e: unknown, write: GmWrite) {
    const kind = conflictKind(e);
    if (kind === "closed") gm.reloadSession();
    else if (kind === "turn_running") data.player.reload();
    else if (kind === "rumor_inactive") data.rumors.reload();
    // a thing already gone, or a seed already running: read again what this write touches,
    // so the card that offered it shows the truth (code review 01 #30)
    else if (statusOf(e) === 404 || (e instanceof HttpError && e.code === "seed_running")) data.after(write);
  }

  async function gmWrite<R>(kind: GmWrite, fn: () => Promise<R>, opts: { inDialog?: boolean } = {}): Promise<R | undefined> {
    if (!opts.inDialog) setWriteError(undefined);
    try {
      const result = await fn();
      if (mounted.current) {
        data.after(kind);
        if (opts.inDialog) setWriteError(undefined); // an older line does not outlive it (review #31)
      }
      return result;
    } catch (e) {
      if (!mounted.current) return undefined;
      told(e, kind);
      if (opts.inDialog) throw e;
      setWriteError(describeError(e));
      return undefined;
    }
  }

  /** A card's write: true when it was saved (a 204 answers nothing, so the answer is no sign). */
  async function saved(kind: GmWrite, fn: () => Promise<unknown>): Promise<boolean> {
    let ok = false;
    await gmWrite(kind, async () => {
      await fn();
      ok = true;
    });
    return ok;
  }

  const advance = useAction(async () => {
    // a record still being read again is no snapshot: nothing is marked then (R-07, review #23)
    const timeline = data.timeline;
    const ids = snapshotIds(timeline.data, timeline.state === "ready" && !timeline.pending);
    const seen = timeline.data;
    const result = await gmWrite("turn", () => api.advanceTurn(sessionId));
    if (result && mounted.current) {
      setNewIds(new Set());
      setBefore({ ids, seen });
      setOutcome(outcomeOf(result));
    }
  });
  // the region's own writes, one at a time; the bulk runs wait for them (review #7)
  const regionWrite = useAction((fn: () => Promise<unknown>) => fn());
  const suggest = useAction(() => gmWrite("suggest", () => api.suggestEvents(sessionId, Math.min(suggestN, maxSuggest))));
  const bulk = useBulkRumors(sessionId, {
    notify: (n) => toast({ key: "gm:bulk", region: n.region_id, title: n.title, body: n.body || undefined, tone: "event" }),
    fail: () => {},
    onError: (e) => setWriteError(e ?? undefined),
    after: async () => data.after("bulk"),
    onCap: setCap,
    onClosed: gm.reloadSession,
    onTurnRunning: data.player.reload,
  });

  const bulkBusy = bulk.progress != null;
  // the GM's own turn holds the session: other writes would be refused as "another turn"
  // (review #35); a bulk run holds the region writes, seeds and the head
  const holding = advance.busy;
  const writesOff = closed || holding;

  function pickRegion(regionId: string, from: "map" | "band" | "card" | "select") {
    onSelect(regionId);
    setTab("region");
    // the event card that was pressed goes with its tab: the region's name takes the focus
    if (from === "card") setFocusTo("region-heading");
    if (from === "band" && !wide) {
      // one column: the tabs are below the map — bring them into view and say where (R-08)
      const root = tabsRef.current;
      root?.scrollIntoView?.({ block: "start" });
      root?.querySelector<HTMLElement>('[data-testid="gm-tab-region"]')?.closest<HTMLElement>('[role="tab"]')?.focus();
    }
  }

  const regionName = (id: string) => {
    const region = gm.world?.regions.find((r) => r.id === id);
    return nameOf("regions", id, "name", region?.name ?? id);
  };
  const region = session && selected ? gm.world?.regions.find((r) => r.id === selected) : undefined;
  const row = selected ? data.worldState.data?.regions.find((r) => r.region_id === selected) : undefined;
  // the names map is empty in the source language: the world file's own name before its id (#12)
  const worldName = gm.names.names?.world?.name ?? gm.world?.world?.name ?? gm.worldId ?? "";
  const suggested = data.events.data?.filter((e) => e.status === "suggested").length ?? 0;

  return (
    <GmLayout
      wide={wide}
      s={{
        header: (
          <GmHeader
            session={session}
            worldName={worldName}
            options={sessionOptions(gm.sessions, session, lang())}
            sessionsError={gm.sessionsError}
            locked={bulkBusy || holding}
            onRetrySessions={gm.reloadSessions}
            onPick={(id) => {
              if (id && id !== sessionId) go(id);
            }}
            onNew={async () => {
              if (!gm.worldId) return;
              const created = await api.startSession(gm.worldId);
              gm.reloadSessions(); // the list knows the new session (R-04, review #4)
              if (mounted.current) go(created.id);
            }}
            onEnd={async () => {
              await gmWrite("close", () => api.closeSession(sessionId), { inDialog: true });
              setFocusTo("gm-closed-banner");
            }}
          />
        ),
        banner: session?.status === "closed" ? <ClosedBanner /> : null,
        player: session ? <PlayerStrip sessionId={sessionId} turn={session.turn} player={data.player} regionName={regionName} /> : null,
        map: (
          <MapPane
            world={gm.world}
            state={data.worldState.data}
            stateError={data.worldState.error}
            nameOf={nameOf}
            selectedId={selected}
            playerRegionId={data.player.data?.player?.region_id ?? null}
            overlayOn={overlayOn}
            mapUrl={mapUrl}
            mapName={mapName}
            onToggle={onToggleOverlay}
            onSelect={(id) => pickRegion(id, "map")}
            onMapFile={onMapFile}
          />
        ),
        tools: (
          <TurnTools
            closed={closed}
            llmOff={noLlm}
            advancing={advance.busy}
            regionBusy={regionWrite.busy}
            suggesting={suggest.busy}
            bulk={bulk.progress}
            suggestN={suggestN}
            maxSuggest={maxSuggest}
            onSuggestN={setSuggestN}
            onAdvance={() => void advance.run()}
            onSuggest={() => void suggest.run()}
            onGenerateAll={() => {
              setFocusTo("generate-progress"); // the pressed button turns off while it runs
              void bulk.generateAll();
            }}
            onRegenAll={() => {
              setFocusTo("generate-progress");
              void bulk.regenAll();
            }}
          />
        ),
        error: writeError ? (
          <div data-testid="gm-hub-error">
            <InlineError error={writeError} />
          </div>
        ) : null,
        band: (
          <TurnBand
            outcome={outcome}
            nameOf={nameOf}
            onPickRegion={(id) => pickRegion(id, "band")}
            onClose={() => {
              setOutcome(null);
              setFocusTo(closed || bulkBusy ? "turn-tools" : "advance-turn-btn");
            }}
          />
        ),
        tabs: (
          <GmTabs
            rootRef={tabsRef}
            tab={tab}
            onTab={setTab}
            suggested={suggested}
            region={
              <RegionTab
                sessionId={sessionId}
                worldId={gm.worldId}
                region={region}
                regionId={selected}
                row={row}
                distortion={selected ? data.regionState(selected) : undefined}
                rumors={data.rumors}
                rumorList={data.rumorList}
                nameOf={nameOf}
                closed={writesOff}
                llmOff={noLlm}
                bulkBusy={bulkBusy}
                regionWriting={regionWrite.busy}
                regions={gm.world?.regions ?? []}
                onPickRegion={(id) => pickRegion(id, "select")}
                knowledgeRev={data.knowledgeRev}
                draft={draft}
                onDraft={setDraft}
                formOpen={formOpen}
                onFormOpen={setFormOpen}
                knowledgeOpen={knowledgeOpen}
                onKnowledgeOpen={setKnowledgeOpen}
                onDistortion={async (v) => {
                  if (!selected) return false;
                  const answer = await gmWrite("distortion", () => api.setDistortion(sessionId, selected, v));
                  if (!answer) return false;
                  data.patchDistortion(answer);
                  return true;
                }}
                onSupport={async (rumorId, v) => {
                  const answer = await gmWrite("support", () => api.setSupport(sessionId, rumorId, v));
                  if (!answer) return false;
                  data.patchSupport(rumorId, answer.support);
                  return true;
                }}
                onGenerate={() => regionWrite.run(() => gmWrite("generate", () => api.generateRumors(sessionId, selected as string)))}
                onRegen={() => regionWrite.run(() => gmWrite("regen", () => api.regenRumors(sessionId, selected as string)))}
                onCreateEvent={async (body: NewEvent) =>
                  (await gmWrite("create", () => api.createEvent(sessionId, body))) !== undefined}
              />
            }
            events={
              <EventPanel
                events={data.events}
                regionName={regionName}
                closed={writesOff}
                onApprove={async (id) => {
                  const ok = await saved("approve", () => api.approveEvent(sessionId, id));
                  // the card moves to the running group once read again: that group stays put
                  if (ok) setFocusTo("events-active");
                  return ok;
                }}
                onDiscard={async (id) => {
                  const ok = await saved("discard", () => api.discardEvent(sessionId, id));
                  if (ok) setFocusTo("events-suggested");
                  return ok;
                }}
                onResolve={async (id) => {
                  const ok = await saved("resolve", () => api.resolveEvent(sessionId, id));
                  if (ok) setFocusTo("events-resolved"); // ended cards are folded
                  return ok;
                }}
                onPickRegion={(id) => pickRegion(id, "card")}
              />
            }
            seeds={
              <SeedPanel
                seeds={data.seeds}
                nameOf={nameOf}
                closed={writesOff}
                busy={bulkBusy}
                onStart={async (id) => {
                  const ok = await saved("seed", () => api.startSeed(sessionId, id));
                  if (ok) setFocusTo(`seed-row-${id}`); // its button becomes "running"
                  return ok;
                }}
              />
            }
            timeline={<TimelinePanel timeline={data.timeline} newIds={newIds} nameOf={nameOf} />}
            deeds={
              <DeedPanel
                deeds={data.deeds}
                closed={writesOff}
                nameOf={nameOf}
                onVoid={async (id) => {
                  await gmWrite("void", () => api.voidDeed(sessionId, id), { inDialog: true });
                  setFocusTo(`deed-${id}`);
                }}
              />
            }
          />
        ),
      }}
    />
  );
}
