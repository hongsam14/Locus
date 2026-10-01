import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { statusOf } from "../api/http";
import { AugmentPanel } from "../features/editor/AugmentPanel";
import { BuildPanel } from "../features/editor/BuildPanel";
import { MapCanvas, type NewRegion } from "../features/editor/MapCanvas";
import { RegionInspector } from "../features/editor/RegionInspector";
import { UnscopedPanel } from "../features/editor/UnscopedPanel";
import { WikiPanel } from "../features/editor/WikiPanel";
import { WorldFileBar } from "../features/editor/WorldFileBar";
import { t, useLang } from "../i18n";
import type { ConnectionEdge, ConnectionKind, NameRef, WorldExport, WorldInfo } from "../types";
import { Button, Toast } from "../ui";
import { AppNav } from "./AppNav";

const PROV = { source: "input", generated_by: "designer" };
type Tab = "region" | "unscoped" | "augment" | "wiki";

/** `/editor/:worldId` — the world editor (US-2.x, frontend-components §1). The page only
 * composes: the bar, the map with its tools, the inspector and the side tabs; each part
 * reads and writes on its own and asks the page to re-read the world after a change. */
export function EditorPage() {
  useLang();
  const { worldId = "" } = useParams();
  const [data, setData] = useState<WorldExport | null>(null);
  const [info, setInfo] = useState<WorldInfo | null>(null);
  const [missing, setMissing] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [conn, setConn] = useState<ConnectionEdge | null>(null);
  const [tab, setTab] = useState<Tab>("region");
  const [rev, setRev] = useState(0);
  const [building, setBuilding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function reload() {
    try {
      setData(await api.exportWorld(worldId));
      setMissing(false);
    } catch (e) {
      if (statusOf(e) === 404) setMissing(true);
      else setError(String(e));
    }
    api.listWorlds().then((ws) => setInfo(ws.find((w) => w.id === worldId) ?? null)).catch(() => {});
    setRev((r) => r + 1);
  }
  useEffect(() => {
    setData(null);
    setSelected(null);
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [worldId]);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function move(id: string, x: number, y: number) {
    const region = data?.regions.find((r) => r.id === id);
    if (!data || !region) return;
    const updated = { ...region, position: { x, y } };
    setData({ ...data, regions: data.regions.map((r) => (r.id === id ? updated : r)) });
    run(() => api.updateRegion(worldId, updated));
  }
  const createRegion = (r: NewRegion) =>
    run(async () => {
      const made = await api.createRegion(worldId, { ...r, world_id: worldId, provenance: PROV });
      setSelected(made.id);
      setTab("region");
    });
  const createConnection = (a: string, b: string, kind: ConnectionKind, weight: number) =>
    run(() => api.saveConnection(worldId, { world_id: worldId, source_region_id: a,
      target_region_id: b, kind, weight, provenance: PROV }));

  const regions = data?.regions ?? [];
  const scoped = new Set((data?.scopes ?? []).map((s) => s.knowledge_id));
  const unscoped = (data?.knowledge ?? []).filter((k) => !k.is_global && !scoped.has(k.id)).length;
  const entities = (data?.entities ?? []) as NameRef[];

  return (
    <div className="min-h-full">
      <AppNav worldId={worldId} />
      <WorldFileBar worldId={worldId} name={data?.world?.name ?? info?.name ?? worldId}
        openSessions={info?.open_sessions ?? null} regions={regions} onLoaded={reload}
        onBuild={() => setBuilding(true)} />
      {error && <div className="p-2 text-danger" data-testid="editor-error">{error}</div>}
      {toast && <Toast onClose={() => setToast(null)}>{toast}</Toast>}
      {missing && (
        <div className="p-3 flex items-center gap-2" data-testid="empty-hint">
          <span className="text-ink-soft">{t("home.empty")}</span>
          <Button size="sm" variant="primary" onClick={() => setBuilding(true)}>
            {t("home.buildFromSources")}
          </Button>
        </div>
      )}
      {data && (
        <div data-testid="graph-status" className="px-3 pt-2 text-xs text-ink-soft">
          {t("editor.status", { world: data.world_id, regions: regions.length,
            connections: data.connections.length, entities: data.entities?.length ?? 0,
            knowledge: data.knowledge.length })}
        </div>
      )}
      <div className="flex flex-wrap gap-4 p-3">
        <MapCanvas regions={regions} connections={data?.connections ?? []} selectedId={selected}
          selectedConnection={conn} busy={busy}
          onSelect={(id) => { setSelected(id); setConn(null); setTab("region"); }}
          onSelectConnection={(c) => { setConn(c); setSelected(c.source_region_id); setTab("region"); }}
          onMove={move} onCreateRegion={createRegion} onCreateConnection={createConnection} />
        <div className="flex min-w-80 flex-col gap-2">
          <div className="flex gap-1" role="tablist">
            {(["region", "unscoped", "augment", "wiki"] as Tab[]).map((x) => (
              <Button key={x} size="sm" role="tab" aria-selected={tab === x} data-testid={`editor-tab-${x}`}
                variant={tab === x ? "primary" : "ghost"} onClick={() => setTab(x)}>
                {t(`editor.tab.${x}`, { n: unscoped })}
              </Button>
            ))}
          </div>
          {tab === "region" &&
            (selected ? (
              <RegionInspector key={selected} worldId={worldId} regionId={selected} regions={regions}
                onChanged={reload}
                onDeleted={(message) => { setSelected(null); setToast(message); reload(); }} />
            ) : (
              <div className="text-ink-soft text-sm">{t("editor.pickRegion")}</div>
            ))}
          {tab === "unscoped" && (
            <UnscopedPanel worldId={worldId} regions={regions} reloadKey={rev} onChanged={reload} />
          )}
          {tab === "augment" && (
            <AugmentPanel worldId={worldId} regions={regions} entities={entities} onChanged={reload} />
          )}
          {tab === "wiki" && <WikiPanel worldId={worldId} regions={regions} reloadKey={rev} />}
        </div>
      </div>
      <BuildPanel open={building} worldId={worldId} exists={data != null}
        onClose={() => setBuilding(false)} onBuilt={() => reload()} />
    </div>
  );
}
