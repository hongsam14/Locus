// A player action and the turn it runs (V4 FD BLM § 2.2, BR-V4-04/17/19, RE-F08).
// An action answers 202 with a run; the screen re-reads at once (the player has arrived)
// and polls the run alongside — the poll needs no arrived screen. The poll has a cap: past
// it the screen says the turn is slow and offers [check again]. A finished turn becomes
// the `outcome` for the one result band; only warnings go to notifications (failed run,
// budget, LLM failure, 409 mid-turn). Leaving the session stops every loop.
// Code review 01: one poll loop at a time (a token), the run being checked is `running`
// (the actions lock while [check again] checks), and an action's request in flight is
// `acting` (a second press sends nothing).
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
  quiet: boolean; // nothing changed anywhere and nothing was declared
}

export interface TurnRunControl {
  running: TurnRun | null;
  /** The action's request is out (before its 202): the actions are off. */
  acting: boolean;
  slow: boolean;
  /** The run's check failed: [check again] polls the same run. */
  error?: DescribedError;
  /** The server refused the action (400 and the like): no run, nothing to check again. */
  refusal?: DescribedError;
  outcome: TurnOutcome | null;
  act(action: PlayerAction): Promise<boolean>;
  recheck(): void;
  clearOutcome(): void;
  clearRefusal(): void;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function useTurnRun(
  sessionId: string,
  { reload, pollMs = 700, maxPolls = 120 }: { reload(): void; pollMs?: number; maxPolls?: number },
): TurnRunControl {
  const [running, setRunning] = useState<TurnRun | null>(null);
  const [acting, setActing] = useState(false);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState<DescribedError>();
  const [refusal, setRefusal] = useState<DescribedError>();
  const [outcome, setOutcome] = useState<TurnOutcome | null>(null);
  const sidRef = useRef(sessionId);
  sidRef.current = sessionId;
  const genRef = useRef(0); // bumped on a session switch and unmount: a loop that sees a new gen stops
  const loopRef = useRef(0); // one poll loop at a time: a loop that sees a newer token stops
  const lastRunRef = useRef<TurnRun | null>(null); // the run [check again] polls
  const actingRef = useRef(false);
  const actedRef = useRef(false); // an action started: the entry's resume must not take over
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  const poll = useCallback(
    async (sid: string, run: TurnRun, gen: number) => {
      const token = ++loopRef.current;
      const alive = () => sidRef.current === sid && genRef.current === gen && loopRef.current === token;
      lastRunRef.current = run;
      setRunning(run); // the actions stay off and the progress shows while it is checked
      for (let n = 0; n < maxPolls; n++) {
        await sleep(pollMs);
        if (!alive()) return;
        let current: TurnRun;
        try {
          current = await api.getTurnRun(sid, run.id);
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
          // the server's reason is an English line for operators: the title says it (FR-D8)
          toast({ key: "play:run", tone: "danger", title: t("play.runFailed") });
        } else if (current.result) {
          const res = current.result;
          const declaration = res.declaration ?? null;
          setOutcome({
            turn: res.session.turn,
            changes: res.changes,
            declaration,
            quiet: res.changes.length === 0 && !declaration,
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

  /** Take up a run already in flight (a page reload, or a 409 that says one runs). */
  const resume = useCallback(
    (sid: string, gen: number, after: { acted: boolean }) => {
      Promise.resolve()
        .then(() => api.listTurnRuns(sid, "running"))
        .then((runs) => {
          if (genRef.current !== gen || actedRef.current !== after.acted || !runs || runs.length === 0) return;
          void poll(sid, runs[0], gen); // a loop already on it gives way (one token)
        })
        .catch(() => {
          /* no resume: the region view's turn_running still locks the buttons */
        });
    },
    [poll],
  );

  // A new session starts clean; a run left in flight (a reload of the page) is polled again.
  useEffect(() => {
    const gen = ++genRef.current;
    setRunning(null);
    setActing(false);
    setSlow(false);
    setError(undefined);
    setRefusal(undefined);
    setOutcome(null);
    lastRunRef.current = null;
    actingRef.current = false;
    actedRef.current = false;
    if (!sessionId) return;
    resume(sessionId, gen, { acted: false }); // skipped once the player has acted meanwhile
    return () => {
      genRef.current++;
    };
  }, [sessionId, resume]);

  const act = useCallback(
    async (action: PlayerAction): Promise<boolean> => {
      if (actingRef.current) return false; // a second press before the answer sends nothing
      const sid = sessionId;
      const gen = genRef.current;
      const here = () => sidRef.current === sid && genRef.current === gen;
      actingRef.current = true;
      actedRef.current = true;
      setActing(true);
      setError(undefined);
      setRefusal(undefined);
      try {
        const started = await api.act(sid, action);
        if (!here()) return false;
        setSlow(false);
        setOutcome(null); // the result band empties when the next turn starts (Q2)
        reloadRef.current(); // the player has already arrived (BR-U4-10)
        void poll(sid, started, gen); // alongside the re-read, not after it
        return true;
      } catch (e) {
        if (!here()) return false;
        const kind = conflictKind(e);
        if (kind === "closed") reloadRef.current(); // the closed banner says it (BR-V4-18)
        else if (kind === "busy") {
          toast({ key: "play:busy", tone: "event", title: t("play.turnInProgress") });
          reloadRef.current(); // the hold shows, and a run of this session is taken up
          resume(sid, gen, { acted: true });
        } else setRefusal(describeError(e));
        return false;
      } finally {
        if (here()) {
          actingRef.current = false;
          setActing(false);
        }
      }
    },
    [sessionId, poll, resume],
  );

  const recheck = useCallback(() => {
    const run = lastRunRef.current;
    if (!run) return;
    setSlow(false);
    setError(undefined);
    void poll(sessionId, run, genRef.current);
  }, [sessionId, poll]);

  const clearOutcome = useCallback(() => setOutcome(null), []);
  const clearRefusal = useCallback(() => setRefusal(undefined), []);
  return { running, acting, slow, error, refusal, outcome, act, recheck, clearOutcome, clearRefusal };
}

/** Re-read while the session is held with no run of ours in flight — a GM write, an
 * editor lease, or `gm_busy` (V5) — every `ms`, at most `max` times (U3 S02, BR-V4-19).
 * A read still out is waited for, not cut short (code review 01 #21). Past the cap the hold
 * is `stuck`: the screen offers [check again], which reads again and counts afresh. */
export function useHeldRereads(
  held: boolean,
  reload: () => void,
  ms = 1000,
  max = 5,
  pending = false,
): { stuck: boolean; retry(): void } {
  const [count, setCount] = useState(0);
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  useEffect(() => {
    if (!held) {
      setCount(0);
      return;
    }
    if (pending || count >= max) return;
    const timer = setTimeout(() => {
      setCount((n) => n + 1);
      reloadRef.current();
    }, ms);
    return () => clearTimeout(timer);
  }, [held, count, ms, max, pending]);
  const retry = useCallback(() => {
    setCount(0);
    reloadRef.current();
  }, []);
  return { stuck: held && count >= max, retry };
}
