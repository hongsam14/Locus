import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { statusOf } from "../../api/http";
import { describeError, type DescribedError } from "../../errors";
import { t } from "../../i18n";
import type { AugAction, AugQuestion, AugRun, QuestionTarget } from "../../types";
import { confidenceOf, type Inputs } from "./AugmentQuestion";

export interface Augmentation {
  run: AugRun | null;
  busy: boolean;
  error?: DescribedError;
  lost: boolean; // the run itself is gone (a server restart): start again
  changed: Record<string, QuestionTarget[]>; // change id -> the targets it changed
  drafts: Record<string, Inputs>; // by issue key (U3 review S28)
  setDraft(issueKey: string, patch: Partial<Inputs>): void;
  /** The last write met a target the world no longer has: offer to start again (BLM § 1.4). */
  stale: boolean;
  start(): void;
  answer(q: AugQuestion, action: AugAction): void;
  revert(changeId: string): void;
  unignore(issueKey: string): void;
  reset(): void;
}

/** The augmentation Q&A's reads and writes, held by the editor page (V8 code plan § 1.1 R-15,
 * § 1.4 R-05). The panel only shows: leaving the tab — a press on the map opens the region
 * tab — keeps the run, the typed answers and a write that is still out, so an answer that
 * ends while the panel is away still clears its card's draft, and the same answer is not
 * sent twice from a remounted panel. The four writes share one guard. */
export function useAugmentation(worldId: string, opts: { onChanged(): void }): Augmentation {
  const [run, setRun] = useState<AugRun | null>(null);
  const [lost, setLost] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<DescribedError>();
  const [changed, setChanged] = useState<Record<string, QuestionTarget[]>>({});
  const [drafts, setDrafts] = useState<Record<string, Inputs>>({});
  const [stale, setStale] = useState(false);
  const running = useRef(false);
  const epoch = useRef(0); // a reset or another world: answers of older calls are dropped
  const optsRef = useRef(opts);
  optsRef.current = opts;
  const runRef = useRef(run);
  runRef.current = run;

  const reset = useCallback(() => {
    epoch.current += 1;
    running.current = false;
    setRun(null);
    setLost(false);
    setBusy(false);
    setError(undefined);
    setChanged({});
    setDrafts({});
    setStale(false);
  }, []);
  useEffect(() => reset, [worldId, reset]); // another world starts clean

  // the reference choices of a broken prior link come from the world the page reads, which is
  // read again after a prior is deleted — not from a list read once (code review 01 #9)

  /** One write at a time. A 404 is a lost run only when the run itself is gone: a target
   * removed meanwhile (an edit, another tab's replace) also answers 404, and then the run
   * stays with a sentence and the server's reason folded (U3 review #12). */
  const write = useCallback(async (fn: () => Promise<AugRun | null>) => {
    if (running.current) return;
    running.current = true;
    const mine = epoch.current;
    setBusy(true);
    setError(undefined);
    setStale(false);
    try {
      const next = await fn();
      if (mine === epoch.current && next) setRun(next);
    } catch (err) {
      if (mine !== epoch.current) return;
      const status = statusOf(err);
      const held = runRef.current;
      if (status === 404 && held) {
        try {
          const again = await api.getRun(held.id);
          if (mine !== epoch.current) return;
          setRun(again);
          // the sentence is the whole advice: describeError's own line ("reload the list")
          // would contradict it (code review 01 #19); [start again] sits beside it
          setError({ ...describeError(err), title: t("notice.augmentWorldChanged"), action: undefined });
          setStale(true);
        } catch (gone) {
          if (mine !== epoch.current) return;
          if (statusOf(gone) === 404) setLost(true);
          else setError(describeError(gone));
        }
      } else if (status === 400) {
        // several causes share the code (no change, empty statement, a missing reference …):
        // one sentence, the server's reason folded (FD review 01 R-06)
        setError({ ...describeError(err), title: t("notice.augmentCantSave"), action: undefined });
      } else {
        setError(describeError(err));
      }
    } finally {
      if (mine === epoch.current) {
        running.current = false;
        setBusy(false);
      }
    }
  }, []);

  const start = useCallback(
    () =>
      void write(async () => {
        setLost(false);
        setChanged({});
        return api.startRun(worldId);
      }),
    [write, worldId],
  );

  const answer = useCallback(
    (q: AugQuestion, action: AugAction) =>
      void write(async () => {
        const held = runRef.current;
        if (!held) return null;
        const mine = epoch.current;
        const i = drafts[q.issue_key] ?? {};
        const takes = new Set(q.needs?.[action] ?? []); // only what this action takes
        const res = await api.answer(held.id, {
          question_id: q.id,
          action,
          statement: takes.has("statement") ? i.statement?.trim() || undefined : undefined,
          title: takes.has("title") ? i.title?.trim() || undefined : undefined,
          confidence: takes.has("confidence") ? confidenceOf(i.confidence) : undefined,
          region_id: takes.has("region") ? i.region || undefined : undefined,
          ref_id: takes.has("ref") ? i.ref || undefined : undefined,
        });
        // a reset or another world meanwhile: the answer belongs to a run that is gone (#27)
        if (mine !== epoch.current) return null;
        // this card's draft goes; the others stay (S28) — here, not in the panel, so it
        // goes even when the panel left meanwhile
        setDrafts((d) => {
          const { [q.issue_key]: _done, ...rest } = d;
          return rest;
        });
        if (res.change) setChanged((c) => ({ ...c, [res.change!.id]: res.changed }));
        if (action !== "ignore") optsRef.current.onChanged();
        return res.run;
      }),
    [write, drafts],
  );

  const revert = useCallback(
    (changeId: string) =>
      void write(async () => {
        const held = runRef.current;
        if (!held) return null;
        const mine = epoch.current;
        const next = await api.revert(held.id, changeId);
        if (mine !== epoch.current) return null; // #27
        optsRef.current.onChanged();
        return next;
      }),
    [write],
  );

  const unignore = useCallback(
    (issueKey: string) =>
      void write(async () => {
        const held = runRef.current;
        return held ? api.unignore(held.id, issueKey) : null;
      }),
    [write],
  );

  const setDraft = useCallback(
    (issueKey: string, patch: Partial<Inputs>) => setDrafts((d) => ({ ...d, [issueKey]: { ...d[issueKey], ...patch } })),
    [],
  );

  return { run, busy, error, lost, stale, changed, drafts, setDraft, start, answer, revert, unignore, reset };
}
