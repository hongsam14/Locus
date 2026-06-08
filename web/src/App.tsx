import { useState } from "react";
import { AugmentPanel } from "./AugmentPanel";
import { MapOverlay } from "./MapOverlay";
import { RegionPanel } from "./RegionPanel";
import { Toolbar } from "./Toolbar";
import { api } from "./api";
import type { Region, WorldExport } from "./types";

export function App() {
  const [worldId, setWorldId] = useState("aldermoor");
  const [data, setData] = useState<WorldExport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run<T>(fn: () => Promise<T>) {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const load = () => run(async () => setData(await api.exportWorld(worldId)));
  const buildDemo = () => run(async () => { await api.buildWorldDemo(worldId); setData(await api.exportWorld(worldId)); });
  const buildWiki = () => run(() => api.buildWiki());

  async function move(id: string, x: number, y: number) {
    if (!data) return;
    const region = data.regions.find((r) => r.id === id);
    if (!region) return;
    const updated: Region = { ...region, position: { x, y } };
    setData({ ...data, regions: data.regions.map((r) => (r.id === id ? updated : r)) });
    run(() => api.upsertRegion(worldId, updated));
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif" }}>
      <Toolbar
        worldId={worldId}
        onWorldIdChange={setWorldId}
        onLoad={load}
        onBuildDemo={buildDemo}
        onBuildWiki={buildWiki}
        onPickMap={setMapUrl}
        busy={busy}
      />
      {error && <div style={{ color: "#c0392b", padding: 8 }}>{error}</div>}
      {busy && <div style={{ padding: 8, color: "#888" }} data-testid="busy">working…</div>}
      {!busy && (!data || data.regions.length === 0) && (
        <div data-testid="empty-hint" style={{ padding: 8, color: "#888" }}>
          No world loaded. Click <b>Build World (demo)</b> to generate one, or{" "}
          <b>Load</b> if it already exists (CLI: <code>locus build-world --world {worldId} --demo</code>).
        </div>
      )}
      <div style={{ display: "flex", gap: 16, padding: 12 }}>
        <MapOverlay
          regions={data?.regions ?? []}
          connections={data?.connections ?? []}
          selectedId={selected}
          mapImageUrl={mapUrl}
          onSelect={setSelected}
          onMove={move}
        />
        <div>
          {selected && <RegionPanel worldId={worldId} regionId={selected} onDeleted={load} />}
          <AugmentPanel worldId={worldId} />
        </div>
      </div>
    </div>
  );
}
