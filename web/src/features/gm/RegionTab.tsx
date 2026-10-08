import { enumLabel } from "../../format";
import { t } from "../../i18n";
import { Section } from "../../layout";
import type { Region, RegionState, SessionRumor } from "../../types";
import { StatusView } from "../../ui";
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
  if (!regionId || !region) {
    return (
      <p data-testid="gm-no-region" className="text-sm text-muted">
        {t("empty.noRegionChosen")}
      </p>
    );
  }
  return (
    <div data-testid="gm-region" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 data-testid="region-heading" className="font-heading text-xl">
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
        <Section level={3} collapsible title={t("label.knows")} open={knowledgeOpen} onOpenChange={onKnowledgeOpen}>
          {worldId && <RegionKnowledgePanel worldId={worldId} regionId={regionId} sessionId={sessionId} rev={knowledgeRev} />}
        </Section>
      </div>
    </div>
  );
}
