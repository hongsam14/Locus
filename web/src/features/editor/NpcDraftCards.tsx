import { useState } from "react";
import { api } from "../../api";
import { needsLlm } from "../../api/http";
import { llmOff, useCapabilities } from "../../capabilities";
import { t } from "../../i18n";
import type { NpcDraft } from "../../types";
import { Button, Card } from "../../ui";

/** NPC suggestions for a region (US-2.5): one LLM call, 0–3 cards, nothing saved until
 * one is accepted; a failed call is a notice, not an error (BR-U3-20/21). */
export function NpcDraftCards({
  worldId,
  regionId,
  busy,
  onAccept,
}: {
  worldId: string;
  regionId: string;
  busy: boolean;
  onAccept: (d: NpcDraft) => Promise<boolean>;
}) {
  const [drafts, setDrafts] = useState<NpcDraft[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const noLlm = llmOff(useCapabilities()); // U8 (BR-U8-25)
  async function suggest() {
    setAsking(true);
    setError(null);
    setFailed(false);
    try {
      const r = await api.draftNpcs(worldId, regionId);
      setDrafts(r.drafts);
      setFailed(r.failed);
    } catch (e) {
      setError(needsLlm(e) ? t("llm.required") : String(e)); // BR-U8-27
    } finally {
      setAsking(false);
    }
  }
  return (
    <div className="flex flex-col gap-1" data-testid="npc-drafts">
      <span className="flex items-center gap-2">
        <Button size="sm" data-testid="npc-suggest" disabled={busy || asking || noLlm} onClick={suggest}
          title={noLlm ? t("llm.required") : undefined}>
          {t("editor.npcDraft.suggest")}
        </Button>
        {noLlm && <span className="text-xs text-ink-soft" data-testid="llm-required">{t("llm.required")}</span>}
      </span>
      {failed && <div className="text-xs text-danger" data-testid="npc-draft-failed">{t("editor.npcDraft.failed")}</div>}
      {error && <div className="text-xs text-danger">{error}</div>}
      {drafts && drafts.length === 0 && !failed && (
        <div className="text-xs text-ink-soft">{t("editor.npcDraft.none")}</div>
      )}
      {drafts?.map((d, i) => (
        <Card key={`${d.name}-${i}`} data-testid="npc-draft-card" className="text-sm flex flex-col gap-0.5">
          <strong>{d.name}</strong>
          <span className="text-xs text-ink-soft">{d.role} · {d.traits.join(", ")}</span>
          <span className="text-xs">{d.description}</span>
          <Button size="sm" variant="primary" disabled={busy} data-testid="npc-draft-accept"
            onClick={async () => {
              if (await onAccept(d)) setDrafts((ds) => (ds ?? []).filter((x) => x !== d));
            }}>
            {t("editor.npcDraft.accept")}
          </Button>
        </Card>
      ))}
    </div>
  );
}
