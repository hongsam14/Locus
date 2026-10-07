// Per-region turn-change summary text (FR-UX2.6), shared by the GM hub and the
// player screen (U4). Moved here from SessionPanel so both use one template set.
import { t } from "../../i18n";
import type { RegionTurnChange } from "../../types";

export function changeSummary(rc: RegionTurnChange): string {
  const segs: string[] = [];
  if (rc.promoted.length) segs.push(t("notif.promoted", { n: rc.promoted.length }));
  if (rc.demoted.length) segs.push(t("notif.demoted", { n: rc.demoted.length }));
  if (rc.pruned.length) segs.push(t("notif.pruned", { n: rc.pruned.length }));
  if (rc.rumors_added.length) segs.push(t("notif.rumors_added", { n: rc.rumors_added.length }));
  if (rc.events_applied.length) segs.push(t("notif.events_applied", { n: rc.events_applied.length }));
  if (rc.events_resolved.length)
    segs.push(t("notif.events_resolved", { n: rc.events_resolved.length }));
  return segs.join(", ");
}

/** Region label for a change: the backend's name, or the id when unnamed. */
export function changeTitle(rc: RegionTurnChange): string {
  return rc.region_name || t("notif.title", { region_id: rc.region_id });
}
