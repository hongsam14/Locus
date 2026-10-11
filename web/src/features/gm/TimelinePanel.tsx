import { useState } from "react";
import { ENUM_VALUES, enumLabel, numberWithMeaning, turnAt } from "../../format";
import { t, timelineText } from "../../i18n";
import type { TimelineEntry } from "../../types";
import { Badge, Button, StatusView } from "../../ui";
import { english, namedPayload, type NameOf } from "../play/names";
import type { GmRes } from "./useGmData";

const STEP = 20;
const CATEGORIES: readonly string[] = ENUM_VALUES.eventCategory;

/** A line's payload as the screen reads it: names by id, an event's category in words (an
 * event line carries the server's raw `category`, FR-D8), a distortion with its meaning. */
function readable(payload: Record<string, unknown>, nameOf: NameOf): Record<string, unknown> {
  const out = namedPayload(payload, nameOf);
  const category = out.category;
  if (typeof category === "string" && CATEGORIES.includes(category)) out.category = enumLabel("eventCategory", category);
  // a distortion setting carries its number: with its meaning, like everywhere else (review #11)
  if (typeof out.degree === "number") out.degree = numberWithMeaning("distortion", out.degree);
  return out;
}

/** The GM's record (V6 BR-V6-08/35, UX-34): newest first, twenty lines and [more] for twenty
 * more; each line's turn in words and regions by name; the lines the last turn brought are
 * marked "new". */
export function TimelinePanel({
  timeline,
  newIds,
  nameOf = english,
}: {
  timeline: GmRes<TimelineEntry[]>;
  newIds: Set<string>;
  nameOf?: NameOf;
}) {
  const [shown, setShown] = useState(STEP);
  if (!timeline.data) {
    return <StatusView state={timeline.state === "error" ? "error" : "loading"} error={timeline.error} onRetry={timeline.reload} />;
  }
  if (timeline.data.length === 0) {
    return <p data-testid="timeline-empty" className="text-sm text-muted">{t("empty.timeline")}</p>;
  }
  const newest = [...timeline.data].reverse(); // the server sends turn order, oldest first
  return (
    <div className="flex flex-col gap-2">
      <h2 className="sr-only">{t("tab.timeline")}</h2>
      <ul data-testid="timeline" className="m-0 flex list-none flex-col p-0 text-sm">
        {newest.slice(0, shown).map((entry) => (
          <li key={entry.id} className="flex flex-wrap items-baseline gap-x-2 border-b border-line py-1.5">
            <b className="text-xs text-muted">{turnAt(entry.turn)}</b>
            <span className="min-w-0 flex-1 [overflow-wrap:anywhere]">{timelineText(entry.kind, readable(entry.payload, nameOf), entry.turn, entry.summary)}</span>
            {newIds.has(entry.id) && (
              <Badge tone="event" data-testid={`timeline-new-${entry.id}`}>{t("label.newLine")}</Badge>
            )}
          </li>
        ))}
      </ul>
      {newest.length > shown && (
        <Button size="sm" className="self-start" data-testid="timeline-more" onClick={() => setShown((n) => n + STEP)}>
          {t("action.showMore", { n: Math.min(STEP, newest.length - shown) })}
        </Button>
      )}
    </div>
  );
}
