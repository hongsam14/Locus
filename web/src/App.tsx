import { useState } from "react";
import { AugmentPanel } from "./AugmentPanel";
import { MapOverlay } from "./MapOverlay";
import { RegionPanel } from "./RegionPanel";
import { SessionBar } from "./SessionBar";
import { SessionPanel } from "./SessionPanel";
import { Toolbar } from "./Toolbar";
import { api } from "./api";
import type { GameSession, Region, WorldExport } from "./types";

export function App() {
  const [worldId, setWorldId] = useState("aldermoor");
  const [data, setData] = useState<WorldExport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<GameSession | null>(null);
  const [sessionRev, setSessionRev] = useState(0);

  // After a SessionPanel write (advance turn / generate / support / distortion),
  // refresh the parent session (turn may have changed) and force RegionPanel to
  // reload the session NPC view.
  async function onSessionChanged() {
    setSessionRev((n) => n + 1);
    if (!session) return;
    try {
      const sessions = await api.listSessions(worldId);
      const fresh = sessions.find((s) => s.id === session.id);
      if (fresh) setSession(fresh);
    } catch {
      // non-fatal: the panel surfaces its own errors
    }
  }

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

  async function move(id: string, x: number, y: number) {
    if (!data) return;
    const region = data.regions.find((r) => r.id === id);
    if (!region) return;
    const updated: Region = { ...region, position: { x, y } };
    setData({ ...data, regions: data.regions.map((r) => (r.id === id ? updated : r)) });
    run(() => api.upsertRegion(worldId, updated));
  }

  return (
    <div className="min-h-full">
      <Toolbar
        worldId={worldId}
        onWorldIdChange={setWorldId}
        onLoad={load}
        onBuildDemo={buildDemo}
        onPickMap={setMapUrl}
        busy={busy}
      />
      <SessionBar worldId={worldId} sessionId={session?.id ?? null} onSelect={setSession} />
      {error && <div className="p-2 text-danger">{error}</div>}
      {busy && (
        <div className="p-2 text-ink-soft" data-testid="busy">
          working…
        </div>
      )}
      {!busy && data && data.regions.length === 0 && (
        <div data-testid="empty-hint" className="p-2 text-danger">
          World <b>{worldId}</b> has <b>0 regions</b> — build it first (button above or
          <code> locus build-world --world {worldId} --demo</code>), then Load. Check the world id matches.
        </div>
      )}
      {!busy && !data && (
        <div data-testid="empty-hint" className="p-2 text-ink-soft">
          No world loaded. Click <b>Build World (demo)</b> or <b>Load</b>.
        </div>
      )}
      {data && (
        <div data-testid="graph-status" className="px-2 pb-2 text-xs text-ink-soft">
          world <b>{data.world_id}</b> · regions {data.regions.length} · connections{" "}
          {data.connections.length} · knowledge {data.knowledge.length}
        </div>
      )}
      <div className="flex flex-wrap gap-4 p-3">
        <MapOverlay
          regions={data?.regions ?? []}
          connections={data?.connections ?? []}
          selectedId={selected}
          mapImageUrl={mapUrl}
          onSelect={setSelected}
          onMove={move}
        />
        <div className="flex min-w-72 flex-col gap-4">
          {selected && (
            <RegionPanel
              key={`${selected}-${session?.id ?? "none"}-${sessionRev}`}
              worldId={worldId}
              regionId={selected}
              sessionId={session?.id ?? null}
              onDeleted={load}
            />
          )}
          {session && (
            <SessionPanel session={session} regionId={selected} onChanged={onSessionChanged} />
          )}
          <AugmentPanel worldId={worldId} />
        </div>
      </div>
    </div>
  );
}
