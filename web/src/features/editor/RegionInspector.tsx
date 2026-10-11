import { useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "../../api";
import { openSessionsOf, statusOf } from "../../api/http";
import { describeError, type DescribedError } from "../../errors";
import { enumLabel } from "../../format";
import { useResource } from "../../hooks";
import { t, useRequestLang } from "../../i18n";
import { Section } from "../../layout";
import type {
  ConnectionKind,
  ConnectionView,
  Knowledge,
  NPC,
  Region,
  RegionDeletePlan,
} from "../../types";
import { InlineError, StatusView } from "../../ui";
import { ConfirmDelete } from "./ConfirmDelete";
import { ConnectionList } from "./ConnectionList";
import { KnowledgeList } from "./KnowledgeList";
import { type NpcFields, NpcEditorList } from "./NpcEditorList";
import { RegionForm } from "./RegionForm";
import { DangerZone } from "./RegionTab";
import type { Panel } from "./useEditorWorld";

const PROV = { source: "input", generated_by: "designer" };

export type InspectorSection = "basic" | "connections" | "knowledge" | "npcs";
export type InspectorOpen = Record<InspectorSection, boolean>;
export const INSPECTOR_FIRST: InspectorOpen = { basic: true, connections: false, knowledge: false, npcs: false };

type Pending =
  | { kind: "region"; plan: RegionDeletePlan }
  | { kind: "knowledge"; item: Knowledge }
  | { kind: "npc"; item: NPC }
  | { kind: "connection"; item: ConnectionView };

/** One region in the editor (US-2.2·2.3·2.4·2.5; V8 frontend-components § 4.4): four folding
 * sections — basics, connections N, knowledge here N, people N — whose folds the page holds,
 * then the danger zone. Every write re-reads the region; ``onChanged`` lets the page re-read
 * the world. The page also re-reads it through ``registerReload`` (after a drag save, a World
 * File load or a build), so the form never saves a stale region over newer data (U3 review
 * #1, BR-U3-1). A read never blanks the screen: the loading line shows only before the first
 * answer (BR-V8-21/25). */
export function RegionInspector({
  worldId,
  regionId,
  regions,
  open,
  onOpenChange,
  onChanged,
  onDeleted,
  onSelectRegion,
  registerReload,
}: {
  worldId: string;
  regionId: string;
  regions: Region[];
  open: InspectorOpen;
  onOpenChange(section: InspectorSection, open: boolean): void;
  onChanged(): void;
  /** The region is gone: its name and what the delete did, for the page's notice. */
  onDeleted(name: string, detail: string): void;
  onSelectRegion?(regionId: string): void; // a connection's other end
  registerReload?(panel: Panel, fn: () => void): () => void;
}) {
  const lang = useRequestLang();
  // keyed by the language too: a slow read in the language the screen just left never
  // paints over the new one (U3 review S31)
  const read = useResource(["editor-region", worldId, regionId, lang], () => api.getEditorRegion(worldId, regionId));
  useEffect(() => registerReload?.("inspector", read.reload), [registerReload, read.reload]);
  const view = read.data;
  const [error, setError] = useState<DescribedError | null>(null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [saved, setSaved] = useState(false);
  const savedTimer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => clearTimeout(savedTimer.current), []);

  async function saveRegion(r: Region) {
    // the spot on the map, which a drag may have moved before its save came back: the form's
    // copy is the last read and would write the old spot back (code review 01 #8)
    const spot = regions.find((x) => x.id === r.id)?.position;
    if (!(await write(() => api.updateRegion(worldId, spot ? { ...r, position: spot } : r)))) return;
    setSaved(true);
    clearTimeout(savedTimer.current);
    savedTimer.current = setTimeout(() => setSaved(false), 1000);
  }

  /** Run a write, then re-read this region — and the world, unless only the region's people
   * changed (BLM § 5: NPC writes re-read the inspector only, code review 01 #29); false when
   * it failed (the error is shown). */
  async function write(fn: () => Promise<unknown>, { world = true }: { world?: boolean } = {}): Promise<boolean> {
    if (busy) return false;
    setBusy(true);
    setError(null);
    try {
      await fn();
      read.reload();
      if (world) onChanged();
      return true;
    } catch (e) {
      setError(describeError(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function askDeleteRegion() {
    setError(null);
    try {
      setPending({ kind: "region", plan: await api.getDeletePlan(worldId, regionId) });
    } catch (e) {
      setError(describeError(e));
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
        onDeleted(view?.region.name ?? regionId, t("delete.region.done", { children: r.children.length,
          npcs: r.npcs.length, connections: r.connections.length, unscoped: r.knowledge_to_unscope.length }));
        return;
      }
      if (p.kind === "knowledge") await api.deleteKnowledge(worldId, p.item.id);
      if (p.kind === "npc") await api.deleteNpc(worldId, p.item.id);
      if (p.kind === "connection") {
        const k = p.item.key;
        await api.deleteConnection(worldId, k.a_region_id, k.b_region_id, k.kind);
      }
      setPending(null);
      read.reload();
      if (p.kind !== "npc") onChanged();
    } catch (e) {
      // a player walked in while the dialog was open: the plan's blocked line and a confirm
      // that stays off — not the raw 409 (U3 review S05)
      const ids = statusOf(e) === 409 ? openSessionsOf(e)?.sessionIds ?? [] : [];
      if (p.kind === "region" && ids.length) {
        setPending({ kind: "region", plan: { ...p.plan, blocked_by_sessions: ids } });
      } else setError(describeError(e));
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
    // the title the card and its ✕ show (code review 01 #24)
    pending?.kind === "knowledge" ? t("delete.knowledge", { name: pending.item.title_ko || pending.item.title })
    : pending?.kind === "npc" ? t("delete.npc", { name: pending.item.name })
    : pending?.kind === "connection"
      ? t("delete.connection", { a: view?.region.name ?? "", b: pending.item.other_region_name,
          kind: enumLabel("connectionKind", pending.item.key.kind) })
      : undefined;

  if (!view) {
    return (
      <section data-testid="region-inspector">
        <StatusView state={read.state === "error" ? "error" : "loading"} error={read.error} onRetry={read.reload} />
      </section>
    );
  }
  const section = (key: InspectorSection, title: string, body: ReactNode) => (
    <div data-testid={`inspector-section-${key}`}>
      <Section level={3} collapsible title={title} open={open[key]} onOpenChange={(o) => onOpenChange(key, o)}>
        {body}
      </Section>
    </div>
  );
  return (
    <section data-testid="region-inspector" aria-label={view.region.name} className="flex flex-col gap-3">
      <h2 className="break-words font-heading text-xl">{view.region.name}</h2>
      {error && !pending && (
        <div data-testid="inspector-error"><InlineError error={error} /></div>
      )}
      {section("basic", t("label.sectionBasic"),
        // keyed by what the form shows, not the spot: a drag of this region does not wipe what
        // was typed (code review 01 #28)
        <RegionForm key={JSON.stringify({ ...view.region, position: undefined })} region={view.region} regions={regions}
          busy={busy} saved={saved} onSave={saveRegion} />)}
      {section("connections", t("label.sectionConnections", { n: view.connections.length }),
        <ConnectionList connections={view.connections} busy={busy}
          onChangeKind={(c, kind) => saveConnection(c, { kind })}
          onChangeWeight={(c, weight) => saveConnection(c, { weight })}
          onDelete={(c) => setPending({ kind: "connection", item: c })} onPickRegion={onSelectRegion} />)}
      {section("knowledge", t("label.sectionKnowledge", { n: view.knowledge.length }),
        <KnowledgeList items={view.knowledge} regions={regions} busy={busy}
          onCreate={(title, statement) => write(() => api.createKnowledge(worldId, regionId,
            { world_id: worldId, title, statement, confidence: 1, provenance: PROV }))}
          onUpdate={(k) => write(() => api.updateKnowledge(worldId, k))}
          onSetScopes={(k, ids) => write(() => api.setScopes(worldId, k.id, ids))}
          onDelete={(k) => setPending({ kind: "knowledge", item: k })} />)}
      {section("npcs", t("label.sectionNpcs", { n: view.npcs.length }),
        <NpcEditorList worldId={worldId} regionId={regionId} npcs={view.npcs} busy={busy}
          onCreate={(f: NpcFields) => write(() => api.createNpc(worldId,
            { ...f, world_id: worldId, home_region_id: regionId, provenance: PROV }), { world: false })}
          onUpdate={(n) => write(() => api.updateNpc(worldId, n), { world: false })}
          onDelete={(n) => setPending({ kind: "npc", item: n })} />)}
      <DangerZone disabled={busy} onDelete={askDeleteRegion} />
      <ConfirmDelete open={pending != null} plan={pending?.kind === "region" ? pending.plan : null}
        regions={regions}
        message={message} busy={busy} error={pending ? error : null} onConfirm={confirmDelete}
        onCancel={() => setPending(null)} />
    </section>
  );
}
