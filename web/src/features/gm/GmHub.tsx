import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { conflictKind, needsLlm } from "../../api/http";
import { llmOff, useCapabilities } from "../../capabilities";
import { t, useRequestLang } from "../../i18n";
import type { GameSession, SessionEvent, SessionRumor, TimelineEntry, TurnResult } from "../../types";
import { LlmNotice, Modal, NotificationCenter, Panel } from "../../ui";
import type { Notif } from "../../ui";
import { changeSummary, changeTitle } from "../play/summary";
import { DistortionPanel } from "./DistortionPanel";
import { EventPanel } from "./EventPanel";
import type { NewEvent } from "./EventPanel";
import { ManualTurnPanel } from "./ManualTurnPanel";
import { RumorPanel } from "./RumorPanel";
import { SeedPanel } from "./SeedPanel";
import { TimelinePanel } from "./TimelinePanel";
import { useBulkRumors } from "./useBulkRumors";

let _notifSeq = 0;

interface Props {
  session: GameSession;
  regionId: string | null; // GameMaster target = map-selected region
  regionNames?: Record<string, string>; // FR-D3: regions read by name
  onChanged?: () => void; // notify parent (e.g. refresh RegionPanel/session)
  reloadKey?: number; // bumped when a change elsewhere on the page touched rumors
}

/** The GameMaster hub (U7 split of the old SessionPanel, NFR-7): it owns the session
 * reads (one parallel round, latest answer wins), the write wrapper and turn
 * notifications; bulk runs live in `useBulkRumors` (U8); the panels only draw and call back. Every `data-testid` of the
 * old panel is kept on the same element (BR-U7-25). */
export function GmHub({ session, regionId, regionNames = {}, onChanged, reloadKey = 0 }: Props) {
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [rumors, setRumors] = useState<SessionRumor[]>([]);
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [distortions, setDistortions] = useState<Record<string, { degree: number; share: number }>>({});
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notif[]>([]);
  const [suggestN, setSuggestN] = useState(1);
  const [confirm, setConfirm] = useState<{ message: string; onConfirm: () => void } | null>(null);
  const closed = session.status === "closed";
  const noLlm = llmOff(useCapabilities()); // U8 (BR-U8-25): LLM buttons off, told why
  const [seedKey, setSeedKey] = useState(0);
  const displayLang = useRequestLang(); // rumors / events carry translated fields: re-read

  const addNotif = useCallback(
    (n: Omit<Notif, "id">) => setNotifications((cur) => [...cur, { ...n, id: `n${_notifSeq++}` }]),
    [],
  );
  const dismissNotif = useCallback(
    (id: string) => setNotifications((cur) => cur.filter((n) => n.id !== id)),
    [],
  );

  // Only the latest read may paint (review U5 #11).
  const readSeq = useRef(0);
  const refresh = useCallback(async () => {
    const mine = ++readSeq.current;
    setError(null);
    try {
      const [tl, ev, dist, rm] = await Promise.all([
        api.getTimeline(session.id),
        api.listEvents(session.id),
        api.listDistortions(session.id),
        regionId ? api.listRumors(session.id, regionId) : Promise.resolve([]),
      ]);
      if (mine !== readSeq.current) return;
      setTimeline(tl);
      setEvents(ev);
      const map: Record<string, { degree: number; share: number }> = {};
      for (const d of dist) map[d.region_id] = { degree: d.distortion_degree, share: d.feedback_share ?? 0 };
      setDistortions(map);
      setRumors(rm);
    } catch (e) {
      if (mine === readSeq.current) setError(String(e));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- displayLang / reloadKey re-read
  }, [session.id, regionId, displayLang, reloadKey]);

  useEffect(() => {
    refresh();
  }, [refresh]);
  // A write awaits the *current* refresh: the one captured when the button was pressed
  // is bound to the region selected then, and painted that region's rumors under a new
  // region's heading (U7 review #6).
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  // The server's cap on suggestions (EVENT_SUGGEST_MAX), not a fixed 1..5 (U7 review #15).
  const [maxSuggest, setMaxSuggest] = useState(5);
  useEffect(() => {
    Promise.resolve()
      .then(() => api.getWorldState(session.id))
      .then((s) => s?.max_event_suggestions && setMaxSuggest(s.max_event_suggestions))
      .catch(() => {});
  }, [session.id]);

  const { progress, generateAll, regenAll } = useBulkRumors(session.id, {
    notify: addNotif,
    fail: setError,
    after: async () => {
      await refreshRef.current();
      onChanged?.();
    },
    onCap: setMaxSuggest,
  });

  /** A GM write, then a re-read; true when it was saved. A 409 for a closed session
   * tells the page, which re-reads the session and locks the controls (U7 review #11). */
  async function run(fn: () => Promise<unknown>): Promise<boolean> {
    setError(null);
    try {
      await fn();
      await refreshRef.current();
      onChanged?.();
      return true;
    } catch (e) {
      setError(needsLlm(e) ? t("llm.required") : String(e)); // BR-U8-27
      if (conflictKind(e) === "closed") onChanged?.();
      return false;
    }
  }

  // Advance a turn and surface per-region change notifications (FR-UX2.6).
  async function advance() {
    setError(null);
    try {
      const result = (await api.advanceTurn(session.id)) as TurnResult;
      for (const rc of result.region_changes ?? []) {
        const body = changeSummary(rc);
        if (body) addNotif({ region_id: rc.region_id, title: changeTitle(rc), body });
      }
      await refreshRef.current();
      onChanged?.();
    } catch (e) {
      setError(String(e));
      if (conflictKind(e) === "closed") onChanged?.();
    }
  }

  const ask = (message: string, onConfirm: () => void) => setConfirm({ message, onConfirm });
  const here = regionId ? distortions[regionId] : undefined;

  return (
    <Panel data-testid="session-panel" title={t("gm.title", { turn: session.turn })} className="min-w-80">
      <LlmNotice visible={noLlm} />
      {error && <div className="text-danger mb-2" data-testid="gm-hub-error">{error}</div>}
      <ManualTurnPanel
        closed={closed}
        llmOff={noLlm}
        progress={progress}
        suggestN={Math.min(suggestN, maxSuggest)}
        maxSuggest={maxSuggest}
        onSuggestN={setSuggestN}
        onAdvance={advance}
        onSuggest={() => run(() => api.suggestEvents(session.id, Math.min(suggestN, maxSuggest)))}
        onGenerateAll={generateAll}
        onRegenAll={() =>
          ask(t("confirm.regenAll"), () => regenAll(Object.keys(distortions)))
        }
      />
      <EventPanel
        events={events}
        regionId={regionId}
        regionNames={regionNames}
        closed={closed}
        onApprove={(id) => run(() => api.approveEvent(session.id, id))}
        onDiscard={(id) => run(() => api.discardEvent(session.id, id))}
        onResolve={(id) => run(() => api.resolveEvent(session.id, id))}
        onCreate={(body: NewEvent) => run(() => api.createEvent(session.id, body))}
      />
      <SeedPanel
        sessionId={session.id}
        closed={closed}
        busy={progress != null}
        reloadKey={seedKey + reloadKey + timeline.length}
        onStart={async (id) => {
          const ok = await run(() => api.startSeed(session.id, id));
          setSeedKey((k) => k + 1);
          return ok;
        }}
      />
      {!regionId && (
        <div data-testid="gm-no-region" className="text-ink-soft text-xs mt-2">
          {t("gm.noRegion")}
        </div>
      )}
      {regionId && (
        <div data-testid="gm-region" className="mt-3 flex flex-col gap-2">
          <DistortionPanel
            key={regionId} // a region's slider state never carries over (U7 review #4)
            regionName={regionNames[regionId] ?? regionId}
            value={here?.degree ?? 0.3}
            share={here?.share ?? 0}
            closed={closed}
            onCommit={(v) => run(() => api.setDistortion(session.id, regionId, v))}
          />
          <RumorPanel
            rumors={rumors}
            closed={closed}
            llmOff={noLlm}
            busy={progress != null}
            onGenerate={() => run(() => api.generateRumors(session.id, regionId))}
            onRegen={() => ask(t("confirm.regen"), () => run(() => api.regenRumors(session.id, regionId)))}
            onSupport={(id, v) => run(() => api.setSupport(session.id, id, v))}
          />
        </div>
      )}
      <TimelinePanel timeline={timeline} />
      <Modal
        open={confirm != null}
        title={t("gm.regen")}
        confirmTone="danger"
        confirmLabel={t("action.confirm")}
        cancelLabel={t("action.cancel")}
        onConfirm={() => {
          confirm?.onConfirm();
          setConfirm(null);
        }}
        onCancel={() => setConfirm(null)}
      >
        {confirm?.message}
      </Modal>
      <NotificationCenter items={notifications} onDismiss={dismissNotif} />
    </Panel>
  );
}
