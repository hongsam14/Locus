import { useEffect, useState } from "react";
import { ENUM_VALUES, enumLabel } from "../../format";
import { t } from "../../i18n";
import { Section } from "../../layout";
import type { Region, RegionState, SessionRumor } from "../../types";
import { Select, StatusView } from "../../ui";
import { english, type NameOf } from "../play/names";
import { DistortionPanel } from "./DistortionPanel";
import { EventForm, type EventDraft, type NewEvent } from "./EventForm";
import { RegionKnowledgePanel } from "./RegionKnowledgePanel";
import { RumorPanel } from "./RumorPanel";
import type { GmRes } from "./useGmData";

/** The [region] tab (V6 frontend-components § 4.1): the chosen region's name and level, one
 * line of what goes on there, its distortion, its rumors, a fold to create an event there and
 * a fold with what its NPCs know. With no region chosen it says how to choose one. The folds'
 * state and the event draft are the session view's, so a hidden tab keeps them (R-08). */
export function RegionTab({
  sessionId,
  worldId,
  region,
  regionId,
  row,
  distortion,
  rumors,
  rumorList,
  nameOf = english,
  closed,
  llmOff,
  bulkBusy,
  regionWriting = false,
  regions = [],
  onPickRegion,
  knowledgeRev,
  draft,
  onDraft,
  formOpen,
  onFormOpen,
  knowledgeOpen,
  onKnowledgeOpen,
  onDistortion,
  onSupport,
  onGenerate,
  onRegen,
  onCreateEvent,
}: {
  sessionId: string;
  worldId: string | null;
  region: Region | undefined;
  regionId: string | null;
  row: RegionState | undefined;
  distortion: { distortion: number; feedback_share: number } | undefined;
  rumors: GmRes<SessionRumor[]>;
  rumorList: SessionRumor[] | undefined;
  nameOf?: NameOf;
  closed: boolean;
  llmOff: boolean;
  bulkBusy: boolean;
  regionWriting?: boolean;
  /** The world's regions: a picker reaches any of them without the map (review #10). */
  regions?: Region[];
  onPickRegion?(regionId: string): void;
  knowledgeRev: number;
  draft: EventDraft;
  onDraft(d: EventDraft): void;
  formOpen: boolean;
  onFormOpen(open: boolean): void;
  knowledgeOpen: boolean;
  onKnowledgeOpen(open: boolean): void;
  onDistortion(v: number): Promise<boolean>;
  onSupport(rumorId: string, v: number): Promise<boolean>;
  onGenerate(): Promise<unknown>;
  onRegen(): Promise<unknown>;
  onCreateEvent(body: NewEvent): Promise<boolean>;
}) {
  const [known, setKnown] = useState<number | null>(null);
  useEffect(() => setKnown(null), [regionId]);
  // by level, then by name: one group per level (the map is not reached by keyboard, FR-S6)
  const levels: readonly string[] = ENUM_VALUES.regionLevel;
  const options = [...regions]
    .map((r) => ({ r, name: nameOf("regions", r.id, "name", r.name) }))
    .sort((a, b) => levels.indexOf(a.r.level) - levels.indexOf(b.r.level) || a.name.localeCompare(b.name))
    .map(({ r, name }) => ({ value: r.id, label: name, group: enumLabel("regionLevel", r.level) }));
  const picker = onPickRegion && options.length > 0 && (
    <Select
      label={t("label.regionPicker")}
      data-testid="region-select"
      value={regionId && region ? regionId : ""}
      placeholder={t("session.pickRegion")}
      options={options}
      onChange={(id) => onPickRegion(id)}
    />
  );
  if (!regionId || !region) {
    return (
      <div className="flex flex-col gap-3">
        {picker}
        <p data-testid="gm-no-region" className="text-sm text-muted">
          {t("empty.noRegionChosen")}
        </p>
      </div>
    );
  }
  return (
    <div data-testid="gm-region" className="flex flex-col gap-4">
      {picker}
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 data-testid="region-heading" tabIndex={-1} className="font-heading text-xl">
          {nameOf("regions", region.id, "name", region.name)}
        </h2>
        <span className="text-sm text-muted">{enumLabel("regionLevel", region.level)}</span>
      </div>
      {row && (
        <p data-testid="region-summary" className="text-sm text-muted">
          {[
            t("label.rumorsGoing", { n: row.active_rumors }),
            t("label.rumorsSettled", { n: row.promoted_rumors }),
            t("label.rumorsDeed", { n: row.deed_rumors }),
            t("label.eventsHere", { n: row.active_events }),
          ].join(" · ")}
        </p>
      )}
      {distortion ? (
        <DistortionPanel
          key={regionId} // a region's slider state never carries over (U7 review #4)
          value={distortion.distortion}
          share={distortion.feedback_share}
          closed={closed}
          onCommit={onDistortion}
        />
      ) : (
        <StatusView state="loading" />
      )}
      <RumorPanel
        rumors={rumors}
        list={rumorList}
        closed={closed}
        llmOff={llmOff}
        busy={bulkBusy}
        writing={regionWriting}
        onGenerate={onGenerate}
        onRegen={onRegen}
        onSupport={onSupport}
      />
      <div data-testid="event-form-toggle">
        <Section level={3} collapsible title={t("label.createEventHere")} open={formOpen} onOpenChange={onFormOpen}>
          <EventForm regionId={regionId} closed={closed} draft={draft} onDraft={onDraft} onCreate={onCreateEvent} />
        </Section>
      </div>
      <div data-testid="knowledge-toggle">
        <Section level={3} collapsible open={knowledgeOpen} onOpenChange={onKnowledgeOpen}
          title={known == null ? t("label.knows") : t("label.knowsCount", { n: known })}>
          {worldId && (
            <RegionKnowledgePanel worldId={worldId} regionId={regionId} sessionId={sessionId} rev={knowledgeRev} onCount={setKnown} />
          )}
        </Section>
      </div>
    </div>
  );
}
