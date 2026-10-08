import { useState } from "react";
import { t } from "../../i18n";
import type { SessionEvent } from "../../types";
import { Button, StatusView } from "../../ui";
import { Section } from "../../layout";
import { EventCard } from "./EventCard";
import type { GmRes } from "./useGmData";

const STEP = 10;

/** The session's events in three groups — suggested, running, ended (V6 frontend-components
 * § 4.2, BR-V6-33): an empty group says so in a line; the ended ones are folded and come ten
 * at a time, newest first. Each card holds its own write (BR-V6-09). */
export function EventPanel({
  events,
  regionName,
  closed,
  onApprove,
  onDiscard,
  onResolve,
  onPickRegion,
}: {
  events: GmRes<SessionEvent[]>;
  regionName(regionId: string): string;
  closed: boolean;
  onApprove(eventId: string): Promise<boolean>;
  onDiscard(eventId: string): Promise<boolean>;
  onResolve(eventId: string): Promise<boolean>;
  onPickRegion(regionId: string): void;
}) {
  const [ended, setEnded] = useState(STEP);
  if (!events.data) {
    return <StatusView state={events.state === "error" ? "error" : "loading"} error={events.error} onRetry={events.reload} skeleton="cards" />;
  }
  const all = events.data;
  const of = (status: string) => all.filter((e) => e.status === status);
  const resolved = of("resolved").sort((a, b) => (b.resolved_turn ?? b.created_turn) - (a.resolved_turn ?? a.created_turn));
  const cards = (list: SessionEvent[]) =>
    list.map((ev) => (
      <EventCard
        key={ev.id}
        event={ev}
        regionName={regionName(ev.region_id)}
        closed={closed}
        onApprove={() => onApprove(ev.id)}
        onDiscard={() => onDiscard(ev.id)}
        onResolve={() => onResolve(ev.id)}
        onPickRegion={() => onPickRegion(ev.region_id)}
      />
    ));
  const group = (id: string, title: string, list: SessionEvent[], empty: string) => (
    <section data-testid={`events-${id}`} className="flex flex-col gap-1.5">
      <h3 className="font-heading text-lg">
        {title} <span className="text-sm text-muted">{list.length}</span>
      </h3>
      {list.length === 0 ? (
        <p data-testid={`events-empty-${id}`} className="text-sm text-muted">{empty}</p>
      ) : (
        cards(list)
      )}
    </section>
  );
  return (
    <div data-testid="events" className="flex flex-col gap-4">
      {group("suggested", t("label.eventsSuggested"), of("suggested"), t("empty.eventsSuggested"))}
      {group("active", t("label.eventsActive"), of("active"), t("empty.eventsActive"))}
      <div data-testid="events-resolved">
        <Section level={3} collapsible defaultOpen={false}
          title={<>{t("label.eventsResolved")} <span className="text-sm text-muted">{resolved.length}</span></>}>
          {resolved.length === 0 ? (
            <p data-testid="events-empty-resolved" className="text-sm text-muted">{t("empty.eventsResolved")}</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {cards(resolved.slice(0, ended))}
              {resolved.length > ended && (
                <Button size="sm" className="self-start" data-testid="events-more" onClick={() => setEnded((n) => n + STEP)}>
                  {t("action.showMore", { n: Math.min(STEP, resolved.length - ended) })}
                </Button>
              )}
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}
