import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { conflictKind } from "../api/http";
import { ActionBar } from "../features/play/ActionBar";
import { DialoguePanel } from "../features/play/DialoguePanel";
import { NarrationCard } from "../features/play/NarrationCard";
import { MovePanel } from "../features/play/MovePanel";
import { PlayLog } from "../features/play/PlayLog";
import { RegionScene } from "../features/play/RegionScene";
import { changeSummary, changeTitle } from "../features/play/summary";
import { t, useLang, useRequestLang } from "../i18n";
import type {
  GameSession,
  Narration,
  PlayerAction,
  RegionTurnChange,
  RegionView,
  TimelineEntry,
  TurnRun,
} from "../types";
import { Button, LlmNotice, NotificationCenter, Panel } from "../ui";
import type { Notif } from "../ui";

const LOG_LINES = 30; // the log shows the newest 30 lines (U7 review C6)
import { AppNav } from "./AppNav";

let _notifSeq = 0;

/** Player screen (F3, US-3.2~3.4): the current region, the move options and the
 * wait action. An action answers 202 with a TurnRun; the page refreshes the
 * region at once (the player has arrived, Q4=A) and polls the run until it is
 * done, then shows one notification per changed region + the narration.
 * U5: "talk" on an NPC opens `DialoguePanel`; a display-language switch re-reads
 * the region (its translated fields depend on the language). */
export function PlayPage({ pollMs = 700 }: { pollMs?: number }) {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<GameSession | null>(null);
  const [view, setView] = useState<RegionView | null>(null);
  const [log, setLog] = useState<TimelineEntry[]>([]);
  const [run, setRun] = useState<TurnRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notif[]>([]);
  // The last action's changes; drawn with t() so the summary follows the language toggle
  // (the server's `narration` sentences are English only, review U5 #12). null = none yet.
  const [lastChanges, setLastChanges] = useState<RegionTurnChange[] | null>(null);
  const [npcCounts, setNpcCounts] = useState<Record<string, number>>({}); // U5: messages per NPC
  const [activeNpcId, setActiveNpcId] = useState<string | null>(null);
  const [declaration, setDeclaration] = useState<Narration | null>(null); // U6: last answer
  useLang(); // labels follow the display language
  const requestLangKey = useRequestLang(); // translated data follows the requested language
  // Route session readable from async continuations so a late response for a
  // previous session never rebinds the screen (same pattern as GmPage).
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  // Bumped on unmount and on every session switch, so a poll loop that is awaiting a
  // timer stops instead of writing state (or notifications) into a screen that moved on.
  const genRef = useRef(0);

  const addNotif = useCallback(
    (n: Omit<Notif, "id">) => setNotifications((cur) => [...cur, { ...n, id: `p${_notifSeq++}` }]),
    [],
  );
  const dismissNotif = useCallback(
    (id: string) => setNotifications((cur) => cur.filter((n) => n.id !== id)),
    [],
  );

  // Talked-to marks (U5). Best effort: the region screen must not fail with it.
  const loadNpcs = useCallback(async (sid: string) => {
    try {
      const list = await api.listNpcs(sid);
      if (sessionIdRef.current !== sid || !Array.isArray(list)) return;
      setNpcCounts(Object.fromEntries(list.map((n) => [n.npc.id, n.message_count])));
    } catch {
      /* the marks just stay as they were */
    }
  }, []);

  // Only the latest read may paint: a slow answer in the previous language must not
  // overwrite a newer one (review U5 #11).
  const readSeq = useRef(0);
  const refresh = useCallback(async (): Promise<RegionView | null> => {
    const sid = sessionId;
    if (!sid) return null;
    const mine = ++readSeq.current;
    void loadNpcs(sid);
    try {
      const [s, v, entries] = await Promise.all([
        api.getSession(sid),
        api.getRegion(sid),
        api.getLog(sid, LOG_LINES),
      ]);
      if (sessionIdRef.current !== sid || mine !== readSeq.current) return null;
      setSession(s);
      setView(v);
      setLog(entries);
      setError(null);
      return v;
    } catch (e) {
      if (sessionIdRef.current === sid && mine === readSeq.current) setError(String(e));
      return null;
    }
  }, [sessionId, loadNpcs]);

  // A change of the requested language re-reads the region (translated fields differ
  // per language). Compared against the last value seen, so it neither fires on mount
  // nor twice under StrictMode, and it never restarts the session effect below.
  const langSeen = useRef(requestLangKey);
  useEffect(() => {
    if (langSeen.current === requestLangKey) return;
    langSeen.current = requestLangKey;
    void refresh();
  }, [requestLangKey, refresh]);

  // The dialogue panel belongs to the region it was opened in: moving closes it, so
  // coming back does not reopen it without a click (review U5 #8).
  const regionId = view?.region_id ?? null;
  useEffect(() => {
    setActiveNpcId(null);
  }, [regionId]);

  // Poll a run until it settles; then notify + refresh (Q4=A).
  // `gen` invalidates the loop on unmount or a session switch, and every exit path
  // refreshes so `turn_running` cannot latch the action buttons off (U4-2 #15).
  const poll = useCallback(
    async (sid: string, runId: string, gen: number) => {
      const alive = () => sessionIdRef.current === sid && genRef.current === gen;
      for (;;) {
        await new Promise((r) => setTimeout(r, pollMs));
        if (!alive()) return;
        let current: TurnRun;
        try {
          current = await api.getTurnRun(sid, runId);
        } catch (e) {
          if (!alive()) return;
          setError(String(e));
          setRun(null);
          await refresh(); // clears a stale turn_running so the screen is usable again
          return;
        }
        if (!alive()) return;
        if (current.status === "running") continue;
        setRun(null);
        if (current.status === "failed") {
          addNotif({ region_id: "run", title: t("play.runFailed"), body: current.error ?? "" });
        } else if (current.result) {
          const res = current.result;
          setLastChanges(res.changes);
          if (res.declaration) setDeclaration(res.declaration);
          for (const rc of res.changes) {
            const body = changeSummary(rc);
            if (body) addNotif({ region_id: rc.region_id, title: changeTitle(rc), body });
          }
          if (res.changes.length === 0)
            addNotif({
              region_id: "turn",
              title: t("play.turnDone", { n: res.session.turn }),
              body: t("play.quiet"),
            });
          if (res.budget_exhausted)
            addNotif({ region_id: "budget", title: t("play.turnDone", { n: res.session.turn }), body: t("play.budget") });
          if (res.llm_failed)
            addNotif({ region_id: "llm", title: t("play.turnDone", { n: res.session.turn }), body: t("play.llmFailed") });
        }
        await refresh();
        return;
      }
    },
    [addNotif, pollMs, refresh],
  );

  useEffect(() => {
    const gen = ++genRef.current;
    setSession(null);
    setView(null);
    setLog([]);
    setRun(null);
    setLastChanges(null);
    setDeclaration(null);
    setNpcCounts({});
    setActiveNpcId(null);
    setError(null);
    if (!sessionId) return;
    (async () => {
      // the first read and the run check go together; a second read only when the view
      // says a turn runs but none does (a stale flag) — U7 review C7
      const [first, running] = await Promise.all([
        refresh(),
        api.listTurnRuns(sessionId, "running").catch(() => null),
      ]);
      if (genRef.current !== gen || sessionIdRef.current !== sessionId) return;
      if (running && running.length > 0) {
        setRun(running[0]); // resume polling a run left in flight (e.g. after a reload)
        void poll(sessionId, running[0].id, gen);
      } else if (running && first?.turn_running) {
        await refresh();
      }
    })();
    return () => {
      genRef.current++; // stop any loop still awaiting a poll
    };
  }, [sessionId, refresh, poll]);

  /** Start an action; true when the server accepted it (202). U6: the declaration box
   * restores its text on false (400 shown as an error, 409 as a notice). */
  async function act(action: PlayerAction): Promise<boolean> {
    const sid = sessionId;
    // the screen this action belongs to: leaving it (GM mode, another session) before
    // the answer must not start a poller on the unmounted page (U7 review §3)
    const gen = genRef.current;
    const here = () => sessionIdRef.current === sid && genRef.current === gen;
    setError(null);
    setDeclaration(null);
    try {
      const started = await api.act(sid, action);
      if (!here()) return false;
      setRun(started);
      await refresh(); // the player has already arrived (BR-U4-10)
      if (!here()) return false;
      void poll(sid, started.id, gen);
      return true;
    } catch (e) {
      const kind = conflictKind(e);
      if (kind === "closed") {
        // not a turn: the session ended (GM, CLI, world replace) — say so, re-read
        // so the controls lock (U6 review #10)
        addNotif({ region_id: "guard", title: t("play.sessionClosed"), body: "" });
        await refresh();
      } else if (kind === "busy") {
        addNotif({ region_id: "guard", title: t("play.turnInProgress"), body: "" });
      } else {
        setError(String(e));
      }
      return false;
    }
  }

  const closed = session?.status === "closed";
  const busy = run != null || (view?.turn_running ?? false);
  // The panel follows the region: after a move the NPC is no longer here, so it closes.
  const activeNpc = view?.npcs.find((n) => n.id === activeNpcId) ?? null;

  async function endTalk(npcId: string) {
    setActiveNpcId(null);
    await act({ type: "end_talk", npc_id: npcId });
  }

  return (
    <div className="min-h-full">
      <AppNav sessionId={sessionId || null} worldId={session?.world_id} />
      <NotificationCenter items={notifications} onDismiss={dismissNotif} />
      <div className="p-3 flex flex-col gap-3" data-testid="play-page">
        {sessionId && (
          <div className="flex justify-end">
            <Button
              size="sm"
              data-testid="play-gm-btn"
              onClick={() => navigate(`/gm/${encodeURIComponent(sessionId)}`)}
            >
              {t("play.gmMode")}
            </Button>
          </div>
        )}
        {!sessionId && (
          <Panel data-testid="play-empty" title={t("play.title")} className="max-w-xl">
            <p className="text-sm">{t("play.noSession")}</p>
          </Panel>
        )}
        {error && (
          <div className="text-danger text-sm" data-testid="play-error">
            {error}
          </div>
        )}
        {view && (
          <>
            <LlmNotice visible={!view.llm_available} text={t("play.noLlm")} />
            <RegionScene
              view={view}
              npcCounts={npcCounts}
              activeNpcId={activeNpc?.id ?? null}
              onTalk={setActiveNpcId}
            />
            {activeNpc && (
              <DialoguePanel
                key={activeNpc.id}
                sessionId={sessionId}
                npc={activeNpc}
                llmAvailable={view.llm_available}
                busy={busy}
                readOnly={session?.status === "closed"}
                onClose={() => setActiveNpcId(null)}
                onEndTalk={() => endTalk(activeNpc.id)}
                // a line and its answer: two more messages, no list re-read (U5 C1)
                onSpoke={() =>
                  setNpcCounts((c) => ({ ...c, [activeNpc.id]: (c[activeNpc.id] ?? 0) + 2 }))
                }
                onClosed={() => void refresh()}
              />
            )}
            {lastChanges && (
              <ul data-testid="play-narration" className="max-w-2xl space-y-0.5 text-sm">
                {lastChanges.length === 0 && <li>{t("play.quiet")}</li>}
                {lastChanges.map((rc) => (
                  <li key={rc.region_id}>
                    {changeTitle(rc)}: {changeSummary(rc) || t("play.quiet")}
                  </li>
                ))}
              </ul>
            )}
            <NarrationCard narration={declaration} />
            <ActionBar
              running={run}
              disabled={busy || closed}
              closed={closed}
              onWait={() => act({ type: "wait" })}
              onDeclare={(text) => act({ type: "declare", text })}
              maxChars={view.declare_max_chars ?? 300}
            />
            <MovePanel
              moves={view.moves}
              disabled={busy || closed}
              onMove={(rid) => act({ type: "move", to_region_id: rid })}
            />
            <PlayLog entries={log} />
          </>
        )}
      </div>
    </div>
  );
}
