import { turnAt } from "../../format";
import { logText, t } from "../../i18n";
import type { TimelineEntry } from "../../types";
import { MoreList } from "./MoreList";
import { english, namedPayload, type NameOf } from "./names";

const LOG_SHORT = 5; // a phone shows five lines and [show more] (V4 § 1.2)

/** The player's log (FR-C6), newest first. The server already keeps only the player's own
 * doings and what happened where the player was (U7 BR-U7-12), so nothing is filtered here;
 * lines a player reads differently from the GM have their own wording (`log.*`). V4: names
 * by the ids in each line's payload (BLM § 2.7), the turn in words, five lines on a phone. */
export function PlayLog({
  entries,
  nameOf = english,
  compact = false,
}: {
  entries: TimelineEntry[];
  nameOf?: NameOf;
  compact?: boolean;
}) {
  const recent = entries.slice(-30).reverse();
  return (
    <section className="flex flex-col gap-2" aria-labelledby="journey" data-testid="play-log">
      <h2 id="journey" className="font-heading text-xl">{t("label.journey")}</h2>
      {recent.length === 0 ? (
        <p className="text-sm text-muted">—</p>
      ) : (
        <MoreList items={recent} limit={compact ? LOG_SHORT : undefined} className="flex flex-col gap-1 text-sm"
          render={(e) => (
            <li key={e.id} data-testid={`log-${e.kind}`} className="flex gap-2">
              <span className="shrink-0 text-muted tabular-nums">{turnAt(e.turn)}</span>
              <span className="min-w-0">{logText(e.kind, namedPayload(e.payload, nameOf), e.turn, e.summary)}</span>
            </li>
          )} />
      )}
    </section>
  );
}
