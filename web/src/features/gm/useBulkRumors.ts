import { useState } from "react";
import { api } from "../../api";
import { conflictKind, isBusy, needsLlm } from "../../api/http";
import { describeError, type DescribedError } from "../../errors";
import { useMounted } from "../../hooks";
import { t } from "../../i18n";
import { BULK_LIMIT, mapLimit, type BulkProgress } from "./bulk";

type FailKind = "llm" | "closed" | "busy" | "other";

function failKind(e: unknown): FailKind {
  if (needsLlm(e)) return "llm";
  const kind = conflictKind(e);
  if (kind === "closed") return "closed";
  if (isBusy(kind)) return "busy";
  return "other";
}

/** The GM screen's runs over many regions (FR-UX2.3 / SEC-E; out of the old hub in U8, NFR-7):
 * [generate all] fills the regions with no canonical rumor, [regenerate all] redoes the
 * given ones; one progress line, one notification at the end, then `after` (the hub's
 * re-read). `onCap` takes the suggestion cap the state read carries (U3 review S13).
 *
 * V6 (code plan § 1.1 R-06, BR-V6-17/22): failures are counted by why — no LLM, the session
 * closed, the session busy, other. The first "closed" or "turn running" stops the run (no
 * more regions are sent) and is told through `onClosed` / `onTurnRunning` and the error.
 * A run whose every request lacked the LLM says so on the error line too. When the screen
 * goes away (another session) the run sends no more, and nothing more is shown or read. */
export function useBulkRumors(
  sessionId: string,
  {
    notify,
    fail,
    after,
    onCap,
    onError,
    onClosed,
    onTurnRunning,
  }: {
    notify: (n: { region_id: string; title: string; body: string }) => void;
    fail: (message: string | null) => void;
    after: () => Promise<void>;
    onCap: (cap: number) => void;
    /** The error as a described sentence; without it `fail` gets its title. */
    onError?: (error: DescribedError | null) => void;
    onClosed?: () => void;
    onTurnRunning?: () => void;
  },
) {
  const [progress, setProgress] = useState<BulkProgress | null>(null);
  const mounted = useMounted();

  const report = (error: DescribedError | null) => {
    if (onError) onError(error);
    else fail(error ? error.title : null);
  };

  async function runBulk(ids: string[], op: (rid: string) => Promise<unknown>, label: string) {
    report(null);
    let done = 0;
    const counts: Record<FailKind, number> = { llm: 0, closed: 0, busy: 0, other: 0 };
    let stopped: { kind: "closed" | "turn_running"; error: unknown } | null = null;
    let noLlm: unknown = null; // the first "no LLM" answer, for the error line (#15)
    const failedCount = () => counts.llm + counts.closed + counts.busy + counts.other;
    setProgress({ done, total: ids.length, failed: 0 });
    // a worker pool: one slow region does not hold back the next ones (U7 review C8)
    await mapLimit(
      ids,
      BULK_LIMIT,
      (rid) =>
        op(rid)
          .catch((e) => {
            const kind = failKind(e);
            counts[kind] += 1;
            if (kind === "llm" && noLlm == null) noLlm = e;
            const conflict = conflictKind(e);
            if (!stopped && (conflict === "closed" || conflict === "turn_running")) stopped = { kind: conflict, error: e };
          })
          .finally(() => {
            done += 1;
            if (mounted.current) setProgress({ done, total: ids.length, failed: failedCount() });
          }),
      () => !mounted.current || stopped != null,
    );
    if (!mounted.current) return; // another session: nothing more for this one (RE-F11)
    setProgress(null);
    const ok = done - failedCount();
    const parts = [t("progress.done", { done: ok, total: ids.length })];
    if (counts.llm) parts.push(t("progress.noLlm", { n: counts.llm }));
    if (counts.busy) parts.push(t("progress.busy", { n: counts.busy }));
    const rest = counts.other + counts.closed;
    if (rest) parts.push(t("progress.failed", { failed: rest }));
    notify({ region_id: "bulk", title: label, body: parts.join(" · ") });
    const halted = stopped as { kind: "closed" | "turn_running"; error: unknown } | null;
    if (halted) {
      report(describeError(halted.error));
      if (halted.kind === "closed") onClosed?.();
      else onTurnRunning?.();
    } else if (counts.llm > 0 && counts.llm === ids.length) {
      report(describeError(noLlm)); // #15: the run needed the LLM, every time
    }
    await after();
  }

  // "Generate all" — regions with no canonical rumor (Q5=C / Q6=B). A deed rumor does not
  // make a region "full" of the world's rumors (U6 review #5). One state read gives the
  // counts — no per-region rumor read, so no translation warm per region (U7 review C1).
  async function generateAll() {
    if (progress != null) return; // in-flight guard (review #2)
    setProgress({ done: 0, total: 0, failed: 0 }); // gate the button during the pre-scan
    try {
      const state = await api.getWorldState(sessionId);
      if (!mounted.current) return;
      // the cap read on mount may have failed: this read corrects it (U3 review S13)
      if (state.max_event_suggestions) onCap(state.max_event_suggestions);
      const empty = state.regions
        .filter((r) => r.active_rumors - r.deed_rumors === 0)
        .map((r) => r.region_id);
      if (empty.length === 0) {
        setProgress(null);
        notify({ region_id: "bulk", title: t("gm.generateAll"), body: t("notif.noTargets") });
        return;
      }
      await runBulk(empty, (rid) => api.generateRumors(sessionId, rid), t("gm.generateAll"));
    } catch (e) {
      if (!mounted.current) return;
      setProgress(null);
      report(describeError(e));
    }
  }

  const regenAll = (ids: string[]) =>
    runBulk(ids, (rid) => api.regenRumors(sessionId, rid), t("gm.regenAll"));

  return { progress, generateAll, regenAll };
}
