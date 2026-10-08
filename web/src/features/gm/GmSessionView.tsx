import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { conflictKind } from "../../api/http";
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
  const data = useGmData(sessionId, selected, { session: gm.reloadSession, sessions: gm.reloadSessions });

  const [tab, setTab] = useState<GmTab>("region");
  const [outcome, setOutcome] = useState<GmTurnOutcome | null>(null);
  const [before, setBefore] = useState<Set<string> | null>(null);
  const [writeError, setWriteError] = useState<DescribedError>();
  const [draft, setDraft] = useState<EventDraft>(EMPTY_DRAFT);
  const [formOpen, setFormOpen] = useState(false);
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [suggestN, setSuggestN] = useState(1);
  const [cap, setCap] = useState<number | null>(null);
  const tabsRef = useRef<HTMLDivElement>(null);
  const maxSuggest = cap ?? data.worldState.data?.max_event_suggestions ?? 5;

  function told(e: unknown) {
    const kind = conflictKind(e);
    if (kind === "closed") gm.reloadSession();
    else if (kind === "turn_running") data.player.reload();
    else if (kind === "rumor_inactive") data.rumors.reload();
  }

  async function gmWrite<R>(kind: GmWrite, fn: () => Promise<R>, opts: { inDialog?: boolean } = {}): Promise<R | undefined> {
    if (!opts.inDialog) setWriteError(undefined);
    try {
      const result = await fn();
      if (mounted.current) data.after(kind);
      return result;
    } catch (e) {
      if (!mounted.current) return undefined;
      told(e);
      if (opts.inDialog) throw e;
      setWriteError(describeError(e));
      return undefined;
    }
  }

  const advance = useAction(async () => {
    const snap = snapshotIds(data.timeline.data, data.timeline.state === "ready");
    const result = await gmWrite("turn", () => api.advanceTurn(sessionId));
    if (result && mounted.current) {
      setBefore(snap);
      setOutcome(outcomeOf(result));
    }
  });
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

  function pickRegion(regionId: string, from: "map" | "band" | "card") {
    onSelect(regionId);
    setTab("region");
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
  const region = selected ? gm.world?.regions.find((r) => r.id === selected) : undefined;
  const row = selected ? data.worldState.data?.regions.find((r) => r.region_id === selected) : undefined;
  const worldName = gm.names.names?.world?.name ?? gm.worldId ?? "";
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
            locked={bulk.progress != null}
            onRetrySessions={gm.reloadSessions}
            onPick={(id) => {
              if (id && id !== sessionId) navigate(`/gm/${encodeURIComponent(id)}`);
            }}
            onNew={async () => {
              if (!gm.worldId) return;
              const created = await api.startSession(gm.worldId);
              if (mounted.current) navigate(`/gm/${encodeURIComponent(created.id)}`);
            }}
            onEnd={() => gmWrite("close", () => api.closeSession(sessionId), { inDialog: true })}
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
            suggesting={suggest.busy}
            bulk={bulk.progress}
            suggestN={suggestN}
            maxSuggest={maxSuggest}
            onSuggestN={setSuggestN}
            onAdvance={() => void advance.run()}
            onSuggest={() => void suggest.run()}
            onGenerateAll={() => void bulk.generateAll()}
            onRegenAll={() => void bulk.regenAll(data.worldState.data?.regions.map((r) => r.region_id) ?? [])}
          />
        ),
        error: writeError ? (
          <div data-testid="gm-hub-error">
            <InlineError error={writeError} />
          </div>
        ) : null,
        band: <TurnBand outcome={outcome} nameOf={nameOf} onPickRegion={(id) => pickRegion(id, "band")} onClose={() => setOutcome(null)} />,
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
                closed={closed}
                llmOff={noLlm}
                bulkBusy={bulk.progress != null}
                knowledgeRev={data.knowledgeRev}
                draft={draft}
                onDraft={setDraft}
                formOpen={formOpen}
                onFormOpen={setFormOpen}
                knowledgeOpen={knowledgeOpen}
                onKnowledgeOpen={setKnowledgeOpen}
                onDistortion={async (v) => {
                  if (!selected) return false;
                  const saved = await gmWrite("distortion", () => api.setDistortion(sessionId, selected, v));
                  if (!saved) return false;
                  data.patchDistortion(saved);
                  return true;
                }}
                onSupport={async (rumorId, v) => {
                  const saved = await gmWrite("support", () => api.setSupport(sessionId, rumorId, v));
                  if (!saved) return false;
                  data.patchRumor(saved);
                  return true;
                }}
                onGenerate={() => gmWrite("generate", () => api.generateRumors(sessionId, selected as string))}
                onRegen={() => gmWrite("regen", () => api.regenRumors(sessionId, selected as string))}
                onCreateEvent={async (body: NewEvent) =>
                  (await gmWrite("create", () => api.createEvent(sessionId, body))) !== undefined}
              />
            }
            events={
              <EventPanel
                events={data.events}
                regionName={regionName}
                closed={closed}
                onApprove={(id) => gmWrite("approve", () => api.approveEvent(sessionId, id))}
                onDiscard={(id) => gmWrite("discard", () => api.discardEvent(sessionId, id))}
                onResolve={(id) => gmWrite("resolve", () => api.resolveEvent(sessionId, id))}
                onPickRegion={(id) => pickRegion(id, "card")}
              />
            }
            seeds={
              <SeedPanel
                seeds={data.seeds}
                nameOf={nameOf}
                closed={closed}
                busy={bulk.progress != null}
                onStart={(id) => gmWrite("seed", () => api.startSeed(sessionId, id))}
              />
            }
            timeline={<TimelinePanel timeline={data.timeline} newIds={newLineIds(before, data.timeline.data)} nameOf={nameOf} />}
            deeds={
              <DeedPanel
                deeds={data.deeds}
                closed={closed}
                nameOf={nameOf}
                onVoid={(id) => gmWrite("void", () => api.voidDeed(sessionId, id), { inDialog: true })}
              />
            }
          />
        ),
      }}
    />
  );
}
