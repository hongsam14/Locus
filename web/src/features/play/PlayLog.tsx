import { t, timelineText } from "../../i18n";
import type { TimelineEntry } from "../../types";
import { Panel } from "../../ui";

/** GM-only lines, hidden from the player (U6 frontend §2.5): who judged a deed and where
 * its rumors went are for the player to find out by travelling. Display-only — the
 * server's /log still returns everything; its player filter (C6) is U7. */
export const GM_ONLY_KINDS = ["deed_appraised", "deed_seeded", "rumor_spread"];

/** The session timeline (U4 basic; the player-perspective filter is U7). */
export function PlayLog({ entries }: { entries: TimelineEntry[] }) {
  const recent = entries
    .filter((e) => !GM_ONLY_KINDS.includes(e.kind))
    .slice(-30)
    .reverse();
  return (
    <Panel title={t("play.log")} data-testid="play-log" className="max-w-2xl">
      {recent.length === 0 && <p className="text-xs text-ink-soft">—</p>}
      <ul className="space-y-0.5 text-sm">
        {recent.map((e) => (
          <li key={e.id} data-testid={`log-${e.kind}`}>
            <span className="text-ink-soft">t{e.turn}</span>{" "}
            {timelineText(e.kind, e.payload, e.turn, e.summary)}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
