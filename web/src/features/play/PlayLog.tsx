import { t, timelineText } from "../../i18n";
import type { TimelineEntry } from "../../types";
import { Panel } from "../../ui";

/** The session timeline (U4 basic; the player-perspective filter is U7). */
export function PlayLog({ entries }: { entries: TimelineEntry[] }) {
  const recent = entries.slice(-30).reverse();
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
