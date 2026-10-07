import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { openSessionsOf, statusOf } from "../../api/http";
import { t, useRequestLang } from "../../i18n";
import type {
  ConnectionKind,
  ConnectionView,
  EditorRegionView,
  Knowledge,
  NPC,
  Region,
  RegionDeletePlan,
} from "../../types";
import { Panel } from "../../ui";
import { ConfirmDelete } from "./ConfirmDelete";
import { ConnectionList } from "./ConnectionList";
import { KnowledgeList } from "./KnowledgeList";
import { type NpcFields, NpcEditorList } from "./NpcEditorList";
import { RegionForm } from "./RegionForm";

const PROV = { source: "input", generated_by: "designer" };

type Pending =
  | { kind: "region"; plan: RegionDeletePlan }
  | { kind: "knowledge"; item: Knowledge }
  | { kind: "npc"; item: NPC }
  | { kind: "connection"; item: ConnectionView };

/** One region in the editor (US-2.2·2.3·2.4·2.5): its fields, connections, knowledge
 * and inhabitants. Every write re-reads the region; ``onChanged`` lets the page re-read
 * the world (the map and the unscoped count). ``reloadKey`` changes whenever the page
 * re-read the world (a map drag, a World File load, a build): the view is read again so
 * the form never saves a stale region over newer data (U3 review #1, BR-U3-1). */
export function RegionInspector({
  worldId,
  regionId,
  regions,
  onChanged,
  onDeleted,
  reloadKey = 0,
}: {
  worldId: string;
  regionId: string;
  regions: Region[];
  onChanged: () => void;
  onDeleted: (message: string) => void;
  reloadKey?: number;
}) {
  const [view, setView] = useState<EditorRegionView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const lang = useRequestLang();
  const readSeq = useRef(0);

  /** Read the region; only the newest read is drawn, so a slow read in the language the
   * screen just left cannot paint over the new one (U3 review S31). */
  async function load() {
    const seq = ++readSeq.current;
    try {
      const v = await api.getEditorRegion(worldId, regionId);
      if (seq === readSeq.current) setView(v);
    } catch (e) {
      if (seq === readSeq.current) setError(String(e));
    }
  }
  useEffect(() => {
    setView(null);
    setError(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [worldId, regionId, lang]);
  const seenKey = useRef(reloadKey);
  useEffect(() => {
    if (seenKey.current === reloadKey) return; // the mount read above covers the first key
    seenKey.current = reloadKey;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);

  /** Run a write, then re-read; false when it failed (the error is shown). */
  async function write(fn: () => Promise<unknown>): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
      onChanged();
      return true;
    } catch (e) {
      setError(String(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function askDeleteRegion() {
    try {
      setPending({ kind: "region", plan: await api.getDeletePlan(worldId, regionId) });
    } catch (e) {
      setError(String(e));
    }
  }

  async function confirmDelete() {
    const p = pending;
    if (!p) return;
    setBusy(true);
    setError(null);
    try {
      if (p.kind === "region") {
        const r = await api.deleteRegion(worldId, regionId);
        setPending(null);
        onDeleted(t("delete.region.done", { children: r.children.length, npcs: r.npcs.length,
          connections: r.connections.length, unscoped: r.knowledge_to_unscope.length }));
        return;
      }
      if (p.kind === "knowledge") await api.deleteKnowledge(worldId, p.item.id);
      if (p.kind === "npc") await api.deleteNpc(worldId, p.item.id);
      if (p.kind === "connection") {
        const k = p.item.key;
        await api.deleteConnection(worldId, k.a_region_id, k.b_region_id, k.kind);
      }
      setPending(null);
      await load();
      onChanged();
    } catch (e) {
      // a player walked in while the dialog was open: the plan's blocked line, its
      // sessions and a confirm that stays off — not the raw 409 (U3 review S05)
      const ids = statusOf(e) === 409 ? openSessionsOf(e)?.sessionIds ?? [] : [];
      if (p.kind === "region" && ids.length) {
        setPending({ kind: "region", plan: { ...p.plan, blocked_by_sessions: ids } });
      } else setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function saveConnection(c: ConnectionView, patch: { kind?: ConnectionKind; weight?: number }) {
    return write(() =>
      api.saveConnection(worldId, {
        world_id: worldId,
        source_region_id: regionId,
        target_region_id: c.other_region_id,
        kind: patch.kind ?? c.key.kind,
        weight: patch.weight ?? c.weight,
        rationale: c.rationale ?? null,
        wiki_prior_ref: c.prior?.prior_id ?? null,
        provenance: PROV,
        ...(patch.kind && patch.kind !== c.key.kind ? { previous_kind: c.key.kind } : {}),
      }),
    );
  }

  const message =
    pending?.kind === "knowledge" ? t("delete.knowledge", { name: pending.item.title })
    : pending?.kind === "npc" ? t("delete.npc", { name: pending.item.name })
    : pending?.kind === "connection"
      ? t("delete.connection", { a: view?.region.name ?? "", b: pending.item.other_region_name,
          kind: pending.item.key.kind })
      : undefined;

  return (
    <Panel data-testid="region-inspector" title={view?.region.name ?? t("editor.region.title")}
      className="min-w-80">
      {error && <div className="text-danger text-sm" data-testid="inspector-error">{error}</div>}
      {!view && !error && <div className="text-muted">{t("common.loading")}</div>}
      {view && (
        <div className="flex flex-col gap-3">
          <RegionForm key={JSON.stringify(view.region)} region={view.region} regions={regions}
            busy={busy} onSave={(r) => write(() => api.updateRegion(worldId, r))}
            onDelete={askDeleteRegion} />
          <h3 className="font-heading">{t("editor.connection.title")}</h3>
          <ConnectionList connections={view.connections} busy={busy}
            onChangeKind={(c, kind) => saveConnection(c, { kind })}
            onChangeWeight={(c, weight) => saveConnection(c, { weight })}
            onDelete={(c) => setPending({ kind: "connection", item: c })} />
          <h3 className="font-heading">{t("editor.knowledge.title")}</h3>
          <KnowledgeList items={view.knowledge} regions={regions} busy={busy}
            onCreate={(title, statement) => write(() => api.createKnowledge(worldId, regionId,
              { world_id: worldId, title, statement, confidence: 1, provenance: PROV }))}
            onUpdate={(k) => write(() => api.updateKnowledge(worldId, k))}
            onSetScopes={(k, ids) => write(() => api.setScopes(worldId, k.id, ids))}
            onDelete={(k) => setPending({ kind: "knowledge", item: k })} />
          <h3 className="font-heading">{t("editor.npc.title")}</h3>
          <NpcEditorList worldId={worldId} regionId={regionId} npcs={view.npcs} busy={busy}
            onCreate={(f: NpcFields) => write(() => api.createNpc(worldId,
              { ...f, world_id: worldId, home_region_id: regionId, provenance: PROV }))}
            onUpdate={(n) => write(() => api.updateNpc(worldId, n))}
            onDelete={(n) => setPending({ kind: "npc", item: n })} />
        </div>
      )}
      <ConfirmDelete open={pending != null} plan={pending?.kind === "region" ? pending.plan : null}
        regions={regions}
        message={message} busy={busy} error={pending ? error : null} onConfirm={confirmDelete}
        onCancel={() => setPending(null)} />
    </Panel>
  );
}
