import { useState } from "react";
import { api } from "../../api";
import { t } from "../../i18n";
import type { BulkProgress } from "./ManualTurnPanel";
import { BULK_LIMIT, mapLimit } from "./bulk";

/** The GM hub's runs over many regions (FR-UX2.3 / SEC-E), out of `GmHub` (U8, NFR-7):
 * [generate all] fills the regions with no canonical rumor, [regenerate all] redoes the
 * given ones; one progress line, one notification at the end, then `after` (the hub's
 * re-read). `onCap` takes the suggestion cap the state read carries (U3 review S13). */
export function useBulkRumors(
  sessionId: string,
  {
    notify,
    fail,
    after,
    onCap,
  }: {
    notify: (n: { region_id: string; title: string; body: string }) => void;
    fail: (message: string | null) => void;
    after: () => Promise<void>;
    onCap: (cap: number) => void;
  },
) {
  const [progress, setProgress] = useState<BulkProgress | null>(null);

  async function runBulk(ids: string[], op: (rid: string) => Promise<unknown>, label: string) {
    fail(null);
    let done = 0;
    let failed = 0;
    setProgress({ done, total: ids.length, failed });
    // a worker pool: one slow region does not hold back the next ones (U7 review C8)
    await mapLimit(ids, BULK_LIMIT, (rid) =>
      op(rid)
        .catch(() => {
          failed += 1;
        })
        .finally(() => {
          done += 1;
          setProgress({ done, total: ids.length, failed });
        }),
    );
    setProgress(null);
    const ok = ids.length - failed;
    notify({
      region_id: "bulk",
      title: label,
      body: `${t("progress.done", { done: ok, total: ids.length })}${failed ? ` · ${t("progress.failed", { failed })}` : ""}`,
    });
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
      setProgress(null);
      fail(String(e));
    }
  }

  const regenAll = (ids: string[]) =>
    runBulk(ids, (rid) => api.regenRumors(sessionId, rid), t("gm.regenAll"));

  return { progress, generateAll, regenAll };
}
