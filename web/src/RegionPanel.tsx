import { useEffect, useState } from "react";
import { api } from "./api";
import { t, useLang } from "./i18n";
import type { KnowledgeView, QueryResult } from "./types";
import { Badge, Button, Card, LocalizedText, Panel } from "./ui";

interface Props {
  worldId: string;
  regionId: string;
  sessionId?: string | null; // when set, show the session NPC view (FR-R5.1)
  onDeleted?: () => void;
}

// Badge text (U1 §11.4): canonical hearsay vs. session rumor vs. scope. Scope
// types stay codes (direct / inherited / global), like the other enum values.
export function badgeLabel(it: KnowledgeView): string {
  if (it.is_hearsay) return t("badge.hearsay");
  if (it.source?.startsWith("rumor")) return t("badge.rumor");
  return it.scope_type;
}

function badgeTone(it: KnowledgeView): "neutral" | "event" | "promoted" {
  if (it.is_hearsay) return "neutral";
  if (it.source?.startsWith("rumor")) return "event";
  return it.scope_type === "direct" ? "promoted" : "neutral"; // emphasize local knowledge
}

export function RegionPanel({ worldId, regionId, sessionId, onDeleted }: Props) {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const displayLang = useLang(); // translated fields differ per language: re-read on switch

  useEffect(() => {
    let active = true;
    setResult(null);
    setError(null);
    // Q3=A: in a session, use the session NPC view; otherwise the canonical query.
    const query = sessionId
      ? api.sessionKnowledge(sessionId, regionId)
      : api.regionKnowledge(worldId, regionId);
    query
      .then((r) => active && setResult(r))
      .catch((e) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, [worldId, regionId, sessionId, displayLang]);

  async function remove(id: string) {
    try {
      await api.deleteNode(worldId, id);
      setResult((r) => (r ? { ...r, items: r.items.filter((i) => i.knowledge_id !== id) } : r));
      onDeleted?.();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <Panel data-testid="region-panel" title={t("region.title")} className="min-w-80">
      {error && <div className="text-danger">{error}</div>}
      {!result && !error && <div className="text-ink-soft">{t("common.loading")}</div>}
      {result && (
        <>
          <div className="text-xs text-ink-soft mb-2">
            {t("region.unique", { n: result.unique_ids.length })} ·{" "}
            {t("region.shared", { n: result.shared_ids.length })}
          </div>
          {result.items.length === 0 && (
            <div data-testid="region-empty" className="text-xs text-ink-soft">
              {t("region.empty")}
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            {result.items.map((it) => (
              <Card
                key={it.knowledge_id}
                data-testid={`knowledge-item-${it.knowledge_id}`}
                className="flex items-start gap-2 text-sm"
              >
                <Badge tone={badgeTone(it)}>{badgeLabel(it)}</Badge>
                <span className="flex-1">
                  <LocalizedText
                    testId={`knowledge-text-${it.knowledge_id}`}
                    ko={it.statement_ko}
                    original={it.statement}
                  />
                  <span className="text-ink-soft text-xs">
                    {" "}({it.confidence.toFixed(2)}
                    {it.path_decay != null ? ` · ${t("label.decay")} ${it.path_decay.toFixed(2)}` : ""}
                    {it.distortion != null ? ` · d${it.distortion.toFixed(2)}` : ""})
                  </span>
                </span>
                <Button
                  size="sm"
                  variant="danger"
                  data-testid={`delete-${it.knowledge_id}`}
                  onClick={() => remove(it.knowledge_id)}
                >
                  ✕
                </Button>
              </Card>
            ))}
          </div>
        </>
      )}
    </Panel>
  );
}
