// A player action and the turn it runs (V4 FD BLM § 2.2, BR-V4-04/17/19, RE-F08).
// An action answers 202 with a run; the screen re-reads at once (the player has arrived)
// and polls the run alongside — the poll needs no arrived screen. The poll has a cap: past
// it the screen says the turn is slow and offers [check again]. A finished turn becomes
// the `outcome` for the one result band; only warnings go to notifications (failed run,
// budget, LLM failure, 409 mid-turn). Leaving the session stops every loop.
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { conflictKind } from "../api/http";
import { describeError, type DescribedError } from "../errors";
import { t } from "../i18n";
import type { Narration, PlayerAction, RegionTurnChange, TurnRun } from "../types";
import { toast } from "../ui/toast";

export interface TurnOutcome {
  turn: number;
  changes: RegionTurnChange[];
  declaration: Narration | null;
  quiet: boolean; // nothing changed anywhere
}

export interface TurnRunControl {
  running: TurnRun | null;
  slow: boolean;
  error?: DescribedError;
  outcome: TurnOutcome | null;
  act(action: PlayerAction): Promise<boolean>;
  recheck(): void;
  clearOutcome(): void;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function useTurnRun(
  sessionId: string,
  { reload, pollMs = 700, maxPolls = 120 }: { reload(): void; pollMs?: number; maxPolls?: number },
): TurnRunControl {
  const [running, setRunning] = useState<TurnRun | null>(null);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState<DescribedError>();
  const [outcome, setOutcome] = useState<TurnOutcome | null>(null);
  const sidRef = useRef(sessionId);
  sidRef.current = sessionId;
  const genRef = useRef(0); // bumped on a session switch and unmount: a loop that sees a new gen stops
  const lastRunRef = useRef<string | null>(null); // the run [check again] polls after an error
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  const poll = useCallback(
    async (sid: string, runId: string, gen: number) => {
      const alive = () => sidRef.current === sid && genRef.current === gen;
      lastRunRef.current = runId;
      for (let n = 0; n < maxPolls; n++) {
        await sleep(pollMs);
        if (!alive()) return;
        let current: TurnRun;
        try {
          current = await api.getTurnRun(sid, runId);
        } catch (e) {
          if (!alive()) return;
          setError(describeError(e));
          setRunning(null);
          reloadRef.current(); // a stale turn_running clears, the screen is usable again
          return;
        }
        if (!alive()) return;
        if (current.status === "running") continue;
        setRunning(null);
        if (current.status === "failed") {
          toast({ key: "play:run", tone: "danger", title: t("play.runFailed"), body: current.error ?? undefined });
        } else if (current.result) {
          const res = current.result;
          setOutcome({
            turn: res.session.turn,
            changes: res.changes,
            declaration: res.declaration ?? null,
            quiet: res.changes.length === 0,
          });
          const title = t("play.turnDone", { n: res.session.turn });
          if (res.budget_exhausted) toast({ key: "play:budget", tone: "event", title, body: t("play.budget") });
          if (res.llm_failed) toast({ key: "play:llm", tone: "event", title, body: t("play.llmFailed") });
        }
        reloadRef.current();
        return;
      }
      if (alive()) setSlow(true); // the cap: still running after maxPolls checks (RE-F08)
    },
    [pollMs, maxPolls],
  );

  // A new session starts clean; a run left in flight (a reload of the page) is polled again.
  useEffect(() => {
    const gen = ++genRef.current;
    setRunning(null);
    setSlow(false);
    setError(undefined);
    setOutcome(null);
    lastRunRef.current = null;
    if (!sessionId) return;
    Promise.resolve()
      .then(() => api.listTurnRuns(sessionId, "running"))
      .then((runs) => {
        if (genRef.current !== gen || !runs || runs.length === 0) return;
        setRunning(runs[0]);
        void poll(sessionId, runs[0].id, gen);
      })
      .catch(() => {
        /* no resume: the region view's turn_running still locks the buttons */
      });
    return () => {
      genRef.current++;
    };
  }, [sessionId, poll]);

  const act = useCallback(
    async (action: PlayerAction): Promise<boolean> => {
      const sid = sessionId;
      const gen = genRef.current;
      const here = () => sidRef.current === sid && genRef.current === gen;
      setError(undefined);
      setOutcome(null); // the result band empties when the next action starts (Q2)
      setSlow(false);
      try {
        const started = await api.act(sid, action);
        if (!here()) return false;
        setRunning(started);
        reloadRef.current(); // the player has already arrived (BR-U4-10)
        void poll(sid, started.id, gen); // alongside the re-read, not after it
        return true;
      } catch (e) {
        if (!here()) return false;
        const kind = conflictKind(e);
        if (kind === "closed") reloadRef.current(); // the closed banner says it (BR-V4-18)
        else if (kind === "busy") toast({ key: "play:busy", tone: "event", title: t("play.turnInProgress") });
        else setError(describeError(e));
        return false;
      }
    },
    [sessionId, poll],
  );

  const recheck = useCallback(() => {
    const runId = running?.id ?? lastRunRef.current;
    if (!runId) return;
    setSlow(false);
    setError(undefined);
    void poll(sessionId, runId, genRef.current);
  }, [running, sessionId, poll]);

  const clearOutcome = useCallback(() => setOutcome(null), []);
  return { running, slow, error, outcome, act, recheck, clearOutcome };
}

/** Re-read while the session is held with no run of ours in flight — a GM write, an
 * editor lease, or `gm_busy` (V5) — every `ms`, at most `max` times (U3 S02, BR-V4-19). */
export function useHeldRereads(held: boolean, reload: () => void, ms = 1000, max = 5): void {
  const [count, setCount] = useState(0);
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  useEffect(() => {
    if (!held) {
      setCount(0);
      return;
    }
    if (count >= max) return;
    const timer = setTimeout(() => {
      setCount((n) => n + 1);
      reloadRef.current();
    }, ms);
    return () => clearTimeout(timer);
  }, [held, count, ms, max]);
}
