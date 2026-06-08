import { useEffect, useState } from "react";
import { api } from "./api";
import type { QueryResult } from "./types";

interface Props {
  worldId: string;
  regionId: string;
  onDeleted?: () => void;
}

const SCOPE_COLORS: Record<string, string> = {
  direct: "#27ae60",
  inherited: "#2980b9",
  global: "#8e44ad",
  propagated: "#f39c12",
};

export function RegionPanel({ worldId, regionId, onDeleted }: Props) {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setResult(null);
    setError(null);
    api
      .regionKnowledge(worldId, regionId)
      .then((r) => active && setResult(r))
      .catch((e) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, [worldId, regionId]);

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
    <div data-testid="region-panel" style={{ padding: 12, minWidth: 320 }}>
      <h3>Region knowledge</h3>
      {error && <div style={{ color: "#c0392b" }}>{error}</div>}
      {!result && !error && <div>Loading…</div>}
      {result && (
        <>
          <div style={{ fontSize: 12, color: "#666" }}>
            unique {result.unique_ids.length} · shared {result.shared_ids.length}
          </div>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {result.items.map((it) => (
              <li
                key={it.knowledge_id}
                data-testid={`knowledge-item-${it.knowledge_id}`}
                style={{ borderBottom: "1px solid #eee", padding: "6px 0" }}
              >
                <span
                  style={{
                    background: SCOPE_COLORS[it.scope_type] ?? "#7f8c8d",
                    color: "#fff",
                    borderRadius: 4,
                    padding: "1px 6px",
                    fontSize: 11,
                    marginRight: 6,
                  }}
                >
                  {it.is_rumor ? "rumor" : it.scope_type}
                </span>
                {it.statement}
                <span style={{ color: "#999", fontSize: 11 }}> ({it.confidence.toFixed(2)})</span>
                <button
                  data-testid={`delete-${it.knowledge_id}`}
                  style={{ float: "right" }}
                  onClick={() => remove(it.knowledge_id)}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
