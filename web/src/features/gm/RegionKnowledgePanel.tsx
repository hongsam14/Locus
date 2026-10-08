import { useEffect, useRef } from "react";
import { api } from "../../api";
import { enumLabel, numberWithMeaning } from "../../format";
import { useResource } from "../../hooks";
import { t, useRequestLang } from "../../i18n";
import type { KnowledgeView } from "../../types";
import { Badge, Card, LocalizedText, StatusView } from "../../ui";

interface Props {
  worldId: string;
  regionId: string;
  sessionId?: string | null; // when set, show the session NPC view (FR-R5.1)
  /** Bumped when what the NPCs know may have changed: read again, keeping what is shown. */
  rev?: number;
  /** How many things are known here, once read (the fold's title says it, FE § 4.1). */
  onCount?(n: number): void;
}

// Badge text (U1 §11.4): canonical hearsay vs. session rumor vs. scope — in words (V6 FR-D8).
export function badgeLabel(it: KnowledgeView): string {
  if (it.is_hearsay) return t("badge.hearsay");
  if (it.source?.startsWith("rumor")) return t("badge.rumor");
  return enumLabel("scopeType", it.scope_type);
}

function badgeTone(it: KnowledgeView): "neutral" | "event" | "promoted" {
  if (it.is_hearsay) return "neutral";
  if (it.source?.startsWith("rumor")) return "event";
  return it.scope_type === "direct" ? "promoted" : "neutral"; // emphasize local knowledge
}

/** What a region knows, as the GM sees it (was ``RegionPanel``). Read-only: canonical
 * knowledge is edited in the world editor only (U3 BR-U3-33). V6: it sits in a fold of the
 * region tab and reads when opened; a new `rev` reads again without unmounting, so the list
 * stays on screen until the answer comes (UX-42). Numbers carry their meaning (FR-D8). */
export function RegionKnowledgePanel({ worldId, regionId, sessionId, rev = 0, onCount }: Props) {
  const lang = useRequestLang(); // translated fields differ per language: re-read
  // Q3=A: in a session, use the session NPC view; otherwise the canonical query.
  const key = ["knowledge", worldId, regionId, sessionId ?? null, lang];
  const keyText = JSON.stringify(key);
  const r = useResource(key, async () => ({
    k: keyText,
    v: await (sessionId ? api.sessionKnowledge(sessionId, regionId) : api.regionKnowledge(worldId, regionId)),
  }));
  const result = r.data && r.data.k === keyText ? r.data.v : null; // another region's answer never shows
  const reload = r.reload;
  const count = result?.items.length;
  useEffect(() => {
    if (count != null) onCount?.(count);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onCount is a notifier
  }, [count]);
  // read again when `rev` moves — compared with the last one seen, so StrictMode's second
  // effect run does not read twice (code review 01 #28)
  const seen = useRef(rev);
  useEffect(() => {
    if (seen.current === rev) return;
    seen.current = rev;
    reload();
  }, [rev, reload]);

  return (
    <div data-testid="region-panel" className="flex flex-col gap-2">
      {!result ? (
        <StatusView state={r.state === "error" ? "error" : "loading"} error={r.error} onRetry={reload} />
      ) : (
        <>
          <div className="text-xs text-muted">
            {t("region.unique", { n: result.unique_ids.length })} · {t("region.shared", { n: result.shared_ids.length })}
          </div>
          {result.items.length === 0 && (
            <div data-testid="region-empty" className="text-sm text-muted">
              {t("empty.knowledge")}
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            {result.items.map((it) => (
              <Card key={it.knowledge_id} data-testid={`knowledge-item-${it.knowledge_id}`} className="flex items-start gap-2 text-sm">
                <Badge tone={badgeTone(it)}>{badgeLabel(it)}</Badge>
                <span className="flex flex-1 flex-col gap-0.5">
                  <LocalizedText testId={`knowledge-text-${it.knowledge_id}`} ko={it.statement_ko} original={it.statement} />
                  <span className="text-xs text-muted">
                    {t("label.confidence")} {numberWithMeaning("confidence", it.confidence)}
                    {it.path_decay != null ? ` · ${t("label.decay")} ${numberWithMeaning("decay", it.path_decay)}` : ""}
                    {it.distortion != null ? ` · ${t("label.distortion")} ${numberWithMeaning("distortion", it.distortion)}` : ""}
                  </span>
                </span>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
