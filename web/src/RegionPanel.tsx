import { useEffect, useState } from "react";
import { api } from "./api";
import type { QueryResult } from "./types";
import { Badge, Button, Card, LocalizedText, Panel } from "./ui";

interface Props {
  worldId: string;
  regionId: string;
  sessionId?: string | null; // when set, show the session NPC view (FR-R5.1)
  onDeleted?: () => void;
}

export function RegionPanel({ worldId, regionId, sessionId, onDeleted }: Props) {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

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
  }, [worldId, regionId, sessionId]);

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
    <Panel data-testid="region-panel" title="Region knowledge" className="min-w-80">
      {error && <div className="text-danger">{error}</div>}
      {!result && !error && <div className="text-ink-soft">Loading…</div>}
      {result && (
        <>
          <div className="text-xs text-ink-soft mb-2">
            unique {result.unique_ids.length} · shared {result.shared_ids.length}
          </div>
          <div className="flex flex-col gap-1.5">
            {result.items.map((it) => (
              <Card
                key={it.knowledge_id}
                data-testid={`knowledge-item-${it.knowledge_id}`}
                className="flex items-start gap-2 text-sm"
              >
                <Badge
                  tone={
                    it.is_rumor
                      ? "event"
                      : it.scope_type === "direct"
                        ? "promoted" // emphasize locally-authored knowledge (mono-safe)
                        : "neutral"
                  }
                >
                  {it.is_rumor ? "rumor" : it.scope_type}
                </Badge>
                <span className="flex-1">
                  <LocalizedText
                    testId={`knowledge-text-${it.knowledge_id}`}
                    ko={it.statement_ko}
                    original={it.statement}
                  />
                  <span className="text-ink-soft text-xs"> ({it.confidence.toFixed(2)})</span>
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
