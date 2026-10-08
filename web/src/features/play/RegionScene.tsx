import { bandOf, decayWord, degreeWord } from "../../format";
import { t } from "../../i18n";
import type { RegionView } from "../../types";
import { Badge, LocalizedText } from "../../ui";
import { MoreList } from "./MoreList";
import { english, type NameOf } from "./names";
import { NpcList } from "./NpcList";

// The current region's parts (FR-C5 / BR-U4-22; V4 frontend-components § 1 and § 3.3),
// placed by PlayLayout — the scene text above the action box, the people and what is known
// below it. Names from the map, words instead of numbers (FR-D8). "Heard" stays a player-
// only view: NPCs do not know hearsay (BR-U5-7). `compact` = a phone: three and [show more].
const KNOWLEDGE_SHORT = 3;

export function SceneText({ view, nameOf = english }: { view: RegionView; nameOf?: NameOf }) {
  const text = nameOf("regions", view.region_id, "description", view.description);
  return (
    <div data-testid="region-scene" className="max-w-prose font-story text-[17px] leading-relaxed">
      {text && <p className="whitespace-pre-line">{text}</p>}
    </div>
  );
}

export function PeopleHere({
  view,
  nameOf = english,
  counts,
  activeNpcId = null,
  talkOff = null,
  onTalk,
}: {
  view: RegionView;
  nameOf?: NameOf;
  counts?: Record<string, number>;
  activeNpcId?: string | null;
  talkOff?: string | null;
  onTalk?: (npcId: string) => void;
}) {
  return (
    <section className="flex flex-col gap-2" aria-labelledby="people-here" data-testid="people-here">
      <h2 id="people-here" className="font-heading text-xl">{t("label.peopleHere")}</h2>
      <NpcList npcs={view.npcs} counts={counts} activeNpcId={activeNpcId} onTalk={onTalk} nameOf={nameOf}
        talkOff={talkOff} />
    </section>
  );
}

export function KnownHere({ view, compact = false }: { view: RegionView; compact?: boolean }) {
  const limit = compact ? KNOWLEDGE_SHORT : undefined;
  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-2" aria-labelledby="known-here" data-testid="known-here">
        <h2 id="known-here" className="font-heading text-xl">{t("label.knownHere")}</h2>
        {view.facts.length === 0 ? (
          <p className="text-sm text-muted">—</p>
        ) : (
          <MoreList items={view.facts} limit={limit} className="flex flex-col gap-1.5 text-sm"
            render={(f) => (
              <li key={f.knowledge_id} data-testid={`knowledge-item-${f.knowledge_id}`}>
                <LocalizedText ko={f.statement_ko} original={f.statement} />
              </li>
            )} />
        )}
      </section>
      {view.hearsay.length > 0 && (
        <section className="flex flex-col gap-2" aria-labelledby="heard-far" data-testid="heard-far">
          <h2 id="heard-far" className="font-heading text-xl">{t("label.heardFar")}</h2>
          {/* NPCs do not know hearsay (BR-U5-7): the line under the heading says so */}
          <p data-testid="hearsay-hint" className="text-xs text-muted">{t("play.hearsayHint")}</p>
          <MoreList items={view.hearsay} limit={limit} className="flex flex-col gap-1.5 text-sm"
            render={(h) => (
              <li key={h.knowledge_id} data-testid={`hearsay-item-${h.knowledge_id}`} className="flex flex-wrap items-baseline gap-1.5">
                <Badge tone="event">{decayWord(h.path_decay)}</Badge>
                <LocalizedText ko={h.statement_ko} original={h.statement} />
              </li>
            )} />
        </section>
      )}
      <section className="flex flex-col gap-2" aria-labelledby="rumors-here" data-testid="rumors-here">
        <h2 id="rumors-here" className="font-heading text-xl">{t("label.rumorsHere")}</h2>
        {view.rumors.length === 0 ? (
          <p className="text-sm text-muted">—</p>
        ) : (
          <MoreList items={view.rumors} limit={limit} className="flex flex-col gap-1.5 text-sm"
            render={(r) => (
              <li key={r.id} data-testid={`rumor-${r.id}`} className="flex flex-wrap items-baseline gap-1.5">
                {r.origin_kind === "deed" && (
                  <Badge tone="deed" data-testid={`deed-badge-${r.id}`}>{t("label.yourStory")}</Badge>
                )}
                <Badge>{degreeWord(r.distortion_degree)}</Badge>
                <Badge tone="info">{t(bandOf("support", r.support))}</Badge>
                <LocalizedText ko={r.statement_ko} original={r.statement} />
              </li>
            )} />
        )}
      </section>
    </div>
  );
}
