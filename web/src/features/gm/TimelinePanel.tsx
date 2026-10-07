import { t, timelineText } from "../../i18n";
import type { TimelineEntry } from "../../types";

/** The GM timeline: every line, by name (FR-D3), newest last. */
export function TimelinePanel({ timeline }: { timeline: TimelineEntry[] }) {
  return (
    <>
      <h4 className="font-heading text-base mt-3 mb-1">{t("gm.timeline")}</h4>
      <ul data-testid="timeline" className="list-none p-0 m-0 text-xs flex flex-col">
        {timeline.map((entry) => (
          <li key={entry.id} className="border-b border-line py-1">
            <b>t{entry.turn}</b>
            {" · "}
            {timelineText(entry.kind, entry.payload, entry.turn, entry.summary)}
          </li>
        ))}
      </ul>
    </>
  );
}
