import { ENUM_VALUES, enumLabel, numberWithMeaning } from "../../format";
import { useAction } from "../../hooks";
import { t } from "../../i18n";
import type { EventCategory, EventLifecycle } from "../../types";
import { Button, Field, Range, Select } from "../../ui";

export interface EventDraft {
  category: EventCategory;
  description: string;
  magnitude: number;
  lifecycle: EventLifecycle | "";
}

export const EMPTY_DRAFT: EventDraft = { category: "war", description: "", magnitude: 0.5, lifecycle: "" };

export interface NewEvent {
  region_id: string;
  category: EventCategory;
  description: string;
  magnitude: number;
  lifecycle: EventLifecycle | null;
}

/** An event for the chosen region (V6 frontend-components § 4.3, UX-38, BR-V6-14): every
 * field labelled; [create] is off while the description is empty (spaces too); a saved event
 * empties the description only, a refused one keeps it. The draft is the caller's, so a
 * hidden tab does not lose it (code plan § 1.1 R-08). */
export function EventForm({
  regionId,
  closed,
  draft,
  onDraft,
  onCreate,
}: {
  regionId: string;
  closed: boolean;
  draft: EventDraft;
  onDraft(next: EventDraft): void;
  /** true when it was saved. */
  onCreate(body: NewEvent): Promise<boolean>;
}) {
  const create = useAction(onCreate, {
    onDone: (saved) => {
      if (saved) onDraft({ ...draft, description: "" });
    },
  });
  const text = draft.description.trim();
  return (
    <form data-testid="event-form" className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (!text || closed) return;
        void create.run({
          region_id: regionId,
          category: draft.category,
          description: text,
          magnitude: draft.magnitude,
          lifecycle: draft.lifecycle || null,
        });
      }}>
      <Select
        label={t("label.eventCategory")}
        data-testid="event-category"
        value={draft.category}
        disabled={closed}
        options={ENUM_VALUES.eventCategory.map((c) => ({ value: c, label: enumLabel("eventCategory", c) }))}
        onChange={(v) => onDraft({ ...draft, category: v as EventCategory })}
      />
      <Field
        label={t("label.eventWhat")}
        data-testid="event-description"
        value={draft.description}
        disabled={closed}
        onChange={(e) => onDraft({ ...draft, description: e.target.value })}
      />
      <label className="flex flex-col gap-1 text-sm">
        <span data-testid="event-magnitude-label" className="font-bold">
          {t("label.magnitude")} {numberWithMeaning("magnitude", draft.magnitude)}
        </span>
        <Range
          data-testid="event-magnitude"
          min={0}
          max={1}
          step={0.05}
          value={draft.magnitude}
          disabled={closed}
          onChange={(e) => onDraft({ ...draft, magnitude: Number(e.target.value) })}
        />
      </label>
      <Select
        label={t("label.eventLifecycle")}
        data-testid="event-lifecycle"
        value={draft.lifecycle}
        disabled={closed}
        options={[
          { value: "", label: t("label.lifecycleDefault") },
          ...ENUM_VALUES.eventLifecycle.map((l) => ({ value: l, label: enumLabel("eventLifecycle", l) })),
        ]}
        onChange={(v) => onDraft({ ...draft, lifecycle: v as EventLifecycle | "" })}
      />
      <Button type="submit" variant="primary" className="self-start" data-testid="event-create-btn"
        busy={create.busy} disabled={closed || !text}>
        {t("action.createEvent")}
      </Button>
    </form>
  );
}
