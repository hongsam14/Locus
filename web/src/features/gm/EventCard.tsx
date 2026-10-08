import { enumLabel, numberWithMeaning } from "../../format";
import { useAction } from "../../hooks";
import { t } from "../../i18n";
import type { SessionEvent } from "../../types";
import { Badge, Button, Card, LocalizedText } from "../../ui";

const TONE: Record<string, "neutral" | "event"> = { suggested: "neutral", active: "event", resolved: "neutral" };

/** One session event (V6 frontend-components § 4.2, BR-V6-09/24/25/27): its status, region
 * (a button that chooses the region), category, size with its meaning and lifecycle, all in
 * words. A suggestion is approved or discarded, an active event resolved (BR-U7-7). The card
 * runs one of its writes at a time; other cards are not held. A write's failure is the
 * screen's error line, so the card only waits. */
export function EventCard({
  event,
  regionName,
  closed,
  onApprove,
  onDiscard,
  onResolve,
  onPickRegion,
}: {
  event: SessionEvent;
  regionName: string;
  closed: boolean;
  onApprove(): Promise<unknown>;
  onDiscard(): Promise<unknown>;
  onResolve(): Promise<unknown>;
  onPickRegion(): void;
}) {
  const write = useAction((fn: () => Promise<unknown>) => fn());
  const id = event.id;
  return (
    <Card data-testid={`event-${id}`} className="flex flex-col gap-1.5 text-sm">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
        <Badge data-testid={`event-status-${id}`} tone={TONE[event.status] ?? "neutral"}>
          {enumLabel("eventStatus", event.status)}
        </Badge>
        <button type="button" data-testid={`event-region-${id}`} className="font-bold text-accent hover:underline"
          onClick={onPickRegion}>
          {regionName}
        </button>
        <span>{enumLabel("eventCategory", event.category)}</span>
        <span>
          {t("label.magnitude")} {numberWithMeaning("magnitude", event.magnitude)}
        </span>
        <span>{enumLabel("eventLifecycle", event.lifecycle)}</span>
      </div>
      <LocalizedText testId={`event-desc-${id}`} ko={event.description_ko} original={event.description} />
      {event.status === "suggested" && (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" data-testid={`approve-${id}`} busy={write.busy} disabled={closed}
            onClick={() => void write.run(onApprove)}>
            {t("action.approve")}
          </Button>
          <Button size="sm" variant="danger" data-testid={`discard-${id}`} busy={write.busy} disabled={closed}
            onClick={() => void write.run(onDiscard)}>
            {t("action.discard")}
          </Button>
        </div>
      )}
      {event.status === "active" && (
        <Button size="sm" className="self-start" data-testid={`resolve-${id}`} busy={write.busy} disabled={closed}
          onClick={() => void write.run(onResolve)}>
          {t("action.resolve")}
        </Button>
      )}
    </Card>
  );
}
