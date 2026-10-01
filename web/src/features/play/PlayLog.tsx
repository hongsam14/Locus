import { logText, t } from "../../i18n";
import type { TimelineEntry } from "../../types";
import { Panel } from "../../ui";

/** The player's log (FR-C6). The server already keeps only the player's own doings and
 * what happened where the player was (U7 BR-U7-12), so nothing is filtered here; lines
 * a player reads differently from the GM have their own wording (`log.*`). */
export function PlayLog({ entries }: { entries: TimelineEntry[] }) {
  const recent = entries.slice(-30).reverse();
  return (
    <Panel title={t("play.log")} data-testid="play-log" className="max-w-2xl">
      {recent.length === 0 && <p className="text-xs text-ink-soft">—</p>}
      <ul className="space-y-0.5 text-sm">
        {recent.map((e) => (
          <li key={e.id} data-testid={`log-${e.kind}`}>
            <span className="text-ink-soft">t{e.turn}</span>{" "}
            {logText(e.kind, e.payload, e.turn, e.summary)}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
