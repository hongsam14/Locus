import { t } from "../../i18n";
import type { RegionView } from "../../types";
import { Badge, LocalizedText, Panel } from "../../ui";

/** The current region in one panel (FR-C5 / BR-U4-22): name + hierarchy path,
 * description, the people here, and what is known / heard / rumoured. */
export function RegionScene({ view }: { view: RegionView }) {
  return (
    <Panel data-testid="region-scene" className="max-w-2xl">
      <h2 className="font-display text-2xl" data-testid="region-title">
        {view.region_name}
      </h2>
      <p className="text-xs text-ink-soft" data-testid="region-path">
        {view.level_path.join(" › ")} · {view.level} · turn {view.turn}
      </p>
      {view.description && <p className="mt-2 text-sm">{view.description}</p>}

      <h3 className="font-display text-lg mt-3">{t("play.npcs")}</h3>
      {view.npcs.length === 0 ? (
        <p className="text-xs text-ink-soft">—</p>
      ) : (
        <ul className="flex flex-wrap gap-2" data-testid="npc-list">
          {view.npcs.map((n) => (
            <li key={n.id} data-testid={`npc-${n.id}`} className="sketch-border bg-paper px-2 py-1 text-sm">
              <b>{n.name}</b> <span className="text-ink-soft">· {n.role}</span>
            </li>
          ))}
        </ul>
      )}

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
          <ul className="space-y-1 text-sm">
            {view.hearsay.map((h) => (
              <li key={h.knowledge_id} data-testid={`hearsay-item-${h.knowledge_id}`}>
                <Badge tone="event">hearsay</Badge>{" "}
                {h.path_decay != null && <Badge>decay {h.path_decay.toFixed(2)}</Badge>}{" "}
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
              {r.promoted ? t("gm.promoted") : "rumor"}
            </Badge>{" "}
            <Badge>d{r.distortion_degree.toFixed(2)}</Badge>{" "}
            <LocalizedText ko={r.statement_ko} original={r.statement} />
          </li>
        ))}
        {view.rumors.length === 0 && <li className="text-xs text-ink-soft">—</li>}
      </ul>
    </Panel>
  );
}
