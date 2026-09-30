import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { ActionBar } from "../features/play/ActionBar";
import { LlmBanner } from "../features/play/LlmBanner";
import { MovePanel } from "../features/play/MovePanel";
import { PlayLog } from "../features/play/PlayLog";
import { RegionScene } from "../features/play/RegionScene";
import { changeSummary, changeTitle } from "../features/play/summary";
import { t } from "../i18n";
import type { GameSession, PlayerAction, RegionView, TimelineEntry, TurnRun } from "../types";
import { NotificationCenter, Panel } from "../ui";
import type { Notif } from "../ui";
import { AppNav } from "./AppNav";

let _notifSeq = 0;

/** Player screen (F3, US-3.2~3.4): the current region, the move options and the
 * wait action. An action answers 202 with a TurnRun; the page refreshes the
 * region at once (the player has arrived, Q4=A) and polls the run until it is
 * done, then shows one notification per changed region + the narration. */
export function PlayPage({ pollMs = 700 }: { pollMs?: number }) {
  const { sessionId = "" } = useParams();
  const [session, setSession] = useState<GameSession | null>(null);
  const [view, setView] = useState<RegionView | null>(null);
  const [log, setLog] = useState<TimelineEntry[]>([]);
  const [run, setRun] = useState<TurnRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notif[]>([]);
  const [narration, setNarration] = useState<string[]>([]);  // last turn's sentences
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

  const refresh = useCallback(async () => {
    const sid = sessionId;
    if (!sid) return;
    try {
      const [s, v, entries] = await Promise.all([
        api.getSession(sid),
        api.getRegion(sid),
        api.getLog(sid),
      ]);
      if (sessionIdRef.current !== sid) return;
      setSession(s);
      setView(v);
      setLog(entries);
      setError(null);
    } catch (e) {
      if (sessionIdRef.current === sid) setError(String(e));
    }
  }, [sessionId]);

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
          setNarration(res.narration);
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
    setNarration([]);
    setError(null);
    if (!sessionId) return;
    (async () => {
      await refresh();
      if (genRef.current !== gen) return;
      // resume polling a run left in flight (e.g. after a reload)
      try {
        const running = await api.listTurnRuns(sessionId, "running");
        if (genRef.current !== gen || sessionIdRef.current !== sessionId) return;
        if (running.length > 0) {
          setRun(running[0]);
          void poll(sessionId, running[0].id, gen);
        } else {
          await refresh(); // nothing is running: make sure turn_running is not stale
        }
      } catch {
        /* the region view already reported any error */
      }
    })();
    return () => {
      genRef.current++; // stop any loop still awaiting a poll
    };
  }, [sessionId, refresh, poll]);

  async function act(action: PlayerAction) {
    const sid = sessionId;
    setError(null);
    try {
      const started = await api.act(sid, action);
      if (sessionIdRef.current !== sid) return;
      setRun(started);
      await refresh(); // the player has already arrived (BR-U4-10)
      void poll(sid, started.id, genRef.current);
    } catch (e) {
      const msg = String(e);
      if (msg.startsWith("Error: 409") || msg.startsWith("409")) {
        addNotif({ region_id: "guard", title: t("play.turnInProgress"), body: "" });
      } else {
        setError(msg);
      }
    }
  }

  const busy = run != null || (view?.turn_running ?? false);

  return (
    <div className="min-h-full">
      <AppNav sessionId={sessionId || null} worldId={session?.world_id} />
      <NotificationCenter items={notifications} onDismiss={dismissNotif} />
      <div className="p-3 flex flex-col gap-3" data-testid="play-page">
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
            <LlmBanner visible={!view.llm_available} />
            <RegionScene view={view} />
            {narration.length > 0 && (
              <ul data-testid="play-narration" className="max-w-2xl space-y-0.5 text-sm">
                {narration.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            )}
            <ActionBar running={run} disabled={busy} onWait={() => act({ type: "wait" })} />
            <MovePanel
              moves={view.moves}
              disabled={busy}
              onMove={(rid) => act({ type: "move", to_region_id: rid })}
            />
            <PlayLog entries={log} />
          </>
        )}
      </div>
    </div>
  );
}
