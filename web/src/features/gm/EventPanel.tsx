import { useState } from "react";
import { t } from "../../i18n";
import type { EventCategory, EventLifecycle, SessionEvent } from "../../types";
import { Badge, Button, Card, Field, LocalizedText, Range } from "../../ui";

const EVENT_TONE: Record<string, "neutral" | "event" | "danger"> = {
  active: "event",
  suggested: "danger",
  resolved: "neutral",
};

const CATEGORIES: EventCategory[] = ["war", "plague", "politics", "disaster", "festival", "discovery"];

export interface NewEvent {
  region_id: string;
  category: EventCategory;
  description: string;
  magnitude: number;
  lifecycle: EventLifecycle | null;
}

/** Session events with their lifecycle buttons, and the create form for the selected
 * region. A suggestion can be approved or discarded, never resolved (BR-U7-7); only an
 * active event can be resolved. Regions read by name (FR-D3). */
export function EventPanel({
  events,
  regionId,
  regionNames,
  closed,
  onApprove,
  onDiscard,
  onResolve,
  onCreate,
}: {
  events: SessionEvent[];
  regionId: string | null;
  regionNames: Record<string, string>;
  closed: boolean;
  onApprove: (eventId: string) => void;
  onDiscard: (eventId: string) => void;
  onResolve: (eventId: string) => void;
  onCreate: (body: NewEvent) => void;
}) {
  const [category, setCategory] = useState<EventCategory>("war");
  const [description, setDescription] = useState("");
  const [magnitude, setMagnitude] = useState(0.5);
  const [lifecycle, setLifecycle] = useState<EventLifecycle | "">("");
  return (
    <>
      <h4 className="font-display text-base mt-3 mb-1">{t("gm.events")}</h4>
      <div data-testid="events" className="flex flex-col gap-1.5 text-sm">
        {events.map((ev) => (
          <Card key={ev.id} data-testid={`event-${ev.id}`} className="flex flex-wrap items-center gap-1.5">
            <Badge data-testid={`event-status-${ev.id}`} tone={EVENT_TONE[ev.status] ?? "neutral"}>
              {ev.status}
            </Badge>
            <span className="text-ink-soft text-xs">
              {regionNames[ev.region_id] ?? ev.region_id} · {ev.category} · m{ev.magnitude.toFixed(2)} ·{" "}
              {ev.lifecycle}
            </span>
            <LocalizedText testId={`event-desc-${ev.id}`} ko={ev.description_ko} original={ev.description} />
            {ev.status === "suggested" && (
              <>
                <Button size="sm" data-testid={`approve-${ev.id}`} onClick={() => onApprove(ev.id)} disabled={closed}>
                  {t("gm.approve")}
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  data-testid={`discard-${ev.id}`}
                  onClick={() => onDiscard(ev.id)}
                  disabled={closed}
                >
                  {t("gm.discard")}
                </Button>
              </>
            )}
            {ev.status === "active" && (
              <Button size="sm" data-testid={`resolve-${ev.id}`} onClick={() => onResolve(ev.id)} disabled={closed}>
                {t("gm.resolve")}
              </Button>
            )}
          </Card>
        ))}
      </div>
      {regionId && (
        <Card data-testid="event-form" className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          <select
            data-testid="event-category"
            value={category}
            disabled={closed}
            onChange={(e) => setCategory(e.target.value as EventCategory)}
            className="sketch-border bg-paper-card px-1.5 py-1"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <Field
            label={t("gm.eventDescription")}
            hideLabel
            data-testid="event-description"
            placeholder={t("gm.eventDescription")}
            value={description}
            disabled={closed}
            onChange={(e) => setDescription(e.target.value)}
          />
          <label className="flex items-center gap-1">
            m{magnitude.toFixed(2)}
            <Range
              data-testid="event-magnitude"
              min={0}
              max={1}
              step={0.05}
              value={magnitude}
              disabled={closed}
              onChange={(e) => setMagnitude(Number(e.target.value))}
            />
          </label>
          <select
            data-testid="event-lifecycle"
            value={lifecycle}
            disabled={closed}
            onChange={(e) => setLifecycle(e.target.value as EventLifecycle | "")}
            className="sketch-border bg-paper-card px-1.5 py-1"
          >
            <option value="">{t("gm.lifecycleDefault")}</option>
            <option value="one_shot">one_shot</option>
            <option value="persistent">persistent</option>
          </select>
          <Button
            size="sm"
            variant="primary"
            data-testid="event-create-btn"
            disabled={closed}
            onClick={() =>
              onCreate({ region_id: regionId, category, description, magnitude, lifecycle: lifecycle || null })
            }
          >
            {t("gm.createEvent")}
          </Button>
        </Card>
      )}
    </>
  );
}
