import { t } from "../../i18n";
import type { RegionView } from "../../types";
import { Badge, LocalizedText, Panel } from "../../ui";
import { NpcList } from "./NpcList";

/** The current region in one panel (FR-C5 / BR-U4-22): name + hierarchy path,
 * description, the people here (`NpcList`, U5), and what is known / heard / rumoured.
 * "Heard" stays a player-only view: NPCs do not know hearsay (BR-U5-7), and the hint
 * under its heading says so (FD-U5 frontend §2.3a). */
export function RegionScene({
  view,
  npcCounts,
  activeNpcId = null,
  onTalk,
}: {
  view: RegionView;
  npcCounts?: Record<string, number>;
  activeNpcId?: string | null;
  onTalk?: (npcId: string) => void;
}) {
  return (
    <Panel data-testid="region-scene" className="max-w-2xl">
      <h2 className="font-display text-2xl" data-testid="region-title">
        {view.region_name}
      </h2>
      <p className="text-xs text-ink-soft" data-testid="region-path">
        {view.level_path.join(" › ")} · {view.level} · {t("common.turn", { n: view.turn })}
      </p>
      {view.description && <p className="mt-2 text-sm">{view.description}</p>}

      <h3 className="font-display text-lg mt-3">{t("play.npcs")}</h3>
      <NpcList npcs={view.npcs} counts={npcCounts} activeNpcId={activeNpcId} onTalk={onTalk} />

      <h3 className="font-display text-lg mt-3">{t("play.facts")}</h3>
      <ul className="space-y-1 text-sm">
        {view.facts.map((f) => (
          <li key={f.knowledge_id} data-testid={`knowledge-item-${f.knowledge_id}`}>
            <Badge>{f.scope_type}</Badge>{" "}
            <LocalizedText ko={f.statement_ko} original={f.statement} />
          </li>
        ))}
        {view.facts.length === 0 && <li className="text-xs text-ink-soft">—</li>}
      </ul>

      {view.hearsay.length > 0 && (
        <>
          <h3 className="font-display text-lg mt-3">{t("play.hearsay")}</h3>
          <p data-testid="hearsay-hint" className="text-xs text-ink-soft mb-1">
            {t("play.hearsayHint")}
          </p>
          <ul className="space-y-1 text-sm">
            {view.hearsay.map((h) => (
              <li key={h.knowledge_id} data-testid={`hearsay-item-${h.knowledge_id}`}>
                <Badge tone="event">{t("badge.hearsay")}</Badge>{" "}
                {h.path_decay != null && (
                  <Badge>
                    {t("label.decay")} {h.path_decay.toFixed(2)}
                  </Badge>
                )}{" "}
                <LocalizedText ko={h.statement_ko} original={h.statement} />
              </li>
            ))}
          </ul>
        </>
      )}

      <h3 className="font-display text-lg mt-3">{t("play.rumors")}</h3>
      <ul className="space-y-1 text-sm">
        {view.rumors.map((r) => (
          <li key={r.id} data-testid={`rumor-${r.id}`}>
            <Badge tone={r.promoted ? "promoted" : "neutral"}>
              {r.promoted ? t("gm.promoted") : t("badge.rumor")}
            </Badge>{" "}
            {r.origin_kind === "deed" && (
              <>
                <Badge tone="event" data-testid={`deed-badge-${r.id}`}>
                  {t("badge.deed")}
                </Badge>{" "}
              </>
            )}
            <Badge>d{r.distortion_degree.toFixed(2)}</Badge>{" "}
            <LocalizedText ko={r.statement_ko} original={r.statement} />
          </li>
        ))}
        {view.rumors.length === 0 && <li className="text-xs text-ink-soft">—</li>}
      </ul>
    </Panel>
  );
}
