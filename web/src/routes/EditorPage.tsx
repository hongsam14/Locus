import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { statusOf } from "../api/http";
import { llmOff, useCapabilities } from "../capabilities";
import { AugmentPanel } from "../features/editor/AugmentPanel";
import { BuildPanel } from "../features/editor/BuildPanel";
import { MapCanvas, type NewRegion, sameConnection } from "../features/editor/MapCanvas";
import { RegionInspector } from "../features/editor/RegionInspector";
import { UnscopedPanel } from "../features/editor/UnscopedPanel";
import { WikiPanel } from "../features/editor/WikiPanel";
import { WorldFileBar } from "../features/editor/WorldFileBar";
import { t, useLang } from "../i18n";
import type { ConnectionEdge, ConnectionKind, NameRef, WorldExport, WorldInfo } from "../types";
import { Button, FileInput, toast } from "../ui";
import { AppShell } from "../layout";

const PROV = { source: "input", generated_by: "designer" };
type Tab = "region" | "unscoped" | "augment" | "wiki";

/** `/editor/:worldId` — the world editor (US-2.x, frontend-components §1). The page only
 * composes: the bar, the map with its tools, the inspector and the side tabs; each part
 * reads and writes on its own and asks the page to re-read the world after a change. */
export function EditorPage() {
  useLang();
  const { worldId = "" } = useParams();
  const caps = useCapabilities(); // U8 (BR-U8-25): the notice at the head of the editor
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
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [augRunId, setAugRunId] = useState<string | null>(null);

  async function reload() {
    try {
      setData(await api.exportWorld(worldId));
      setMissing(false);
    } catch (e) {
      if (statusOf(e) === 404) setMissing(true);
      else setError(String(e));
    }
    setRev((r) => r + 1);
  }
  // The world list is read for its open-session count only: on mount and after a load or
  // a build, the writes that can change it — not after every edit (U3 review C1).
  const loadInfo = () =>
    api.listWorlds().then((ws) => setInfo(ws.find((w) => w.id === worldId) ?? null)).catch(() => {});
  const reloadAll = () => {
    loadInfo();
    return reload();
  };
  useEffect(() => {
    setData(null);
    setSelected(null);
    setAugRunId(null);
    reloadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [worldId]);

  // A World File load or a rebuild can remove the selected region: drop the selection
  // instead of keeping an inspector that would save a region the world no longer has.
  useEffect(() => {
    if (data && selected && !data.regions.some((r) => r.id === selected)) setSelected(null);
  }, [data, selected]);

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

  // A drag is one PUT: the map already shows the new spot, so the world is not read
  // again; the inspector re-reads its region (rev) so it never saves the old spot back
  // (U3 #1). A failed save reads the world again to put the marker back (U3 review C1).
  async function move(id: string, x: number, y: number) {
    const region = data?.regions.find((r) => r.id === id);
    if (!data || !region) return;
    const updated = { ...region, position: { x, y } };
    setData({ ...data, regions: data.regions.map((r) => (r.id === id ? updated : r)) });
    setBusy(true);
    setError(null);
    try {
      await api.updateRegion(worldId, updated);
      setRev((r) => r + 1);
    } catch (e) {
      setError(String(e));
      await reload();
    } finally {
      setBusy(false);
    }
  }
  const createRegion = (r: NewRegion) =>
    run(async () => {
      const made = await api.createRegion(worldId, { ...r, world_id: worldId, provenance: PROV });
      setSelected(made.id);
      setTab("region");
    });
  // The connect tool on a pair that already has this kind edits that connection: its
  // grounds, prior and source are kept and only the weight is the form's (U3 #15).
  const createConnection = (a: string, b: string, kind: ConnectionKind, weight: number) => {
    const old = sameConnection(data?.connections ?? [], a, b, kind);
    return run(() => api.saveConnection(worldId, old
      ? { ...old, source_region_id: a, target_region_id: b, weight }
      : { world_id: worldId, source_region_id: a, target_region_id: b, kind, weight, provenance: PROV }));
  };

  // the panel forgets its files when closed idle and keeps a running build (U8 review #2)
  const openBuild = () => setBuilding(true);

  const noLlm = llmOff(caps);
  const regions = data?.regions ?? [];
  const unscoped = data?.unscoped_knowledge_ids?.length ?? 0; // the server's rule (C5)
  const entities = (data?.entities ?? []) as NameRef[];

  return (
    <AppShell worldId={worldId}>
      <WorldFileBar worldId={worldId} name={data?.world?.name ?? info?.name ?? worldId}
        openSessions={info?.open_sessions ?? null} regions={regions} onLoaded={reloadAll}
        onBuild={openBuild} />
      {error && <div className="p-2 text-danger" data-testid="editor-error">{error}</div>}
      {missing && (
        <div className="p-3 flex items-center gap-2" data-testid="empty-hint">
          <span className="text-muted">{t("home.empty")}</span>
          <Button size="sm" variant="primary" onClick={openBuild}>
            {t("home.buildFromSources")}
          </Button>
        </div>
      )}
      {data && (
        <div data-testid="graph-status" className="px-3 pt-2 text-xs text-muted">
          {t("editor.status", { world: data.world_id, regions: regions.length,
            connections: data.connections.length, entities: data.entities?.length ?? 0,
            knowledge: data.knowledge.length })}
          <span className="ml-3 inline-flex">
            <FileInput label={t("toolbar.pickMap")} accept="image/*" data-testid="map-file-input"
              onFiles={([f]) => setMapUrl(URL.createObjectURL(f))} /* this browser only, as on the GM page */ />
          </span>
        </div>
      )}
      <div className="flex flex-wrap gap-4 p-3">
        <MapCanvas regions={regions} connections={data?.connections ?? []} selectedId={selected}
          selectedConnection={conn} busy={busy} mapImageUrl={mapUrl} disabled={missing}
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
                reloadKey={rev} onChanged={reload}
                onDeleted={(message) => { setSelected(null); toast({ title: message }); reload(); }} />
            ) : (
              <div className="text-muted text-sm">{t("editor.pickRegion")}</div>
            ))}
          {tab === "unscoped" && (
            <UnscopedPanel worldId={worldId} regions={regions} reloadKey={rev} onChanged={reload} />
          )}
          {tab === "augment" && (
            <AugmentPanel worldId={worldId} regions={regions} entities={entities} onChanged={reload}
              runId={augRunId} onRunId={setAugRunId} />
          )}
          {tab === "wiki" && <WikiPanel worldId={worldId} regions={regions} reloadKey={rev} />}
        </div>
      </div>
      <BuildPanel open={building} worldId={worldId} exists={data != null}
        onClose={() => setBuilding(false)} onBuilt={() => reloadAll()} />
    </AppShell>
  );
}
