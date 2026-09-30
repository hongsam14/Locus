import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AugmentPanel } from "../AugmentPanel";
import { MapOverlay } from "../MapOverlay";
import { RegionPanel } from "../RegionPanel";
import { SessionBar } from "../SessionBar";
import { Toolbar } from "../Toolbar";
import { api } from "../api";
import { t, useLang } from "../i18n";
import type { GameSession, Region, SessionStartOut, WorldExport } from "../types";
import { Modal } from "../ui";
import { AppNav } from "./AppNav";

export const DEFAULT_WORLD = "aldermoor";

// World editor screen (F1): build/load a world, move regions, inspect canonical
// knowledge, run augmentation Q&A. Selecting a session hands off to /gm/:sessionId.
export function EditorPage() {
  useLang(); // labels follow the display language
  const { worldId: paramWorldId = DEFAULT_WORLD } = useParams();
  const navigate = useNavigate();
  const [worldId, setWorldId] = useState(paramWorldId);
  const [data, setData] = useState<WorldExport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The URL names the world: seed the input and load it (deep link, refresh, Back
  // from /gm). An unbuilt world shows the empty hint, not an error (review U1 #8).
  useEffect(() => {
    setWorldId(paramWorldId);
    let active = true;
    setBusy(true);
    setError(null);
    api
      .exportWorld(paramWorldId)
      .then((world) => active && world && setData(world))
      .catch(() => active && setData(null))
      .finally(() => active && setBusy(false));
    return () => {
      active = false;
    };
  }, [paramWorldId]);

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

  // Keep the URL in step with the world the editor is showing.
  function syncUrl() {
    if (worldId !== paramWorldId) {
      navigate(`/editor/${encodeURIComponent(worldId)}`, { replace: true });
    }
  }

  // An empty id would navigate to "/editor/" and fall through to the "*" redirect,
  // silently dropping the loaded world (review U1 #12).
  function requireWorldId(): boolean {
    if (worldId.trim()) return true;
    setError(t("editor.enterWorldId"));
    return false;
  }

  const load = () => {
    if (!requireWorldId()) return;
    syncUrl();
    return run(async () => setData(await api.exportWorld(worldId)));
  };
  // Load the packaged demo World File (LLM-free, US-1.3). Replacing a world that has
  // open sessions answers 409 (BR-U2-25): ask before retrying with confirm=true.
  const [confirmReplace, setConfirmReplace] = useState<{ open: number } | null>(null);
  const loadDemo = (confirm: boolean) =>
    run(async () => {
      try {
        await api.loadDemo(worldId, "aldermoor", { replace: true, confirm });
      } catch (e) {
        const msg = String(e);
        const m = /"open_sessions":\s*(\d+)/.exec(msg);
        if (!confirm && msg.startsWith("Error: 409") && m) {
          setConfirmReplace({ open: Number(m[1]) });
          return;
        }
        throw e;
      }
      setData(await api.exportWorld(worldId));
    });
  const buildDemo = () => {
    if (!requireWorldId()) return;
    syncUrl();
    return loadDemo(false);
  };

  async function move(id: string, x: number, y: number) {
    if (!data) return;
    const region = data.regions.find((r) => r.id === id);
    if (!region) return;
    const updated: Region = { ...region, position: { x, y } };
    setData({ ...data, regions: data.regions.map((r) => (r.id === id ? updated : r)) });
    run(() => api.upsertRegion(worldId, updated));
  }

  // Picking (or starting) a session moves to the GameMaster screen.
  function onSelectSession(s: GameSession | null) {
    if (s) navigate(`/gm/${encodeURIComponent(s.id)}`);
  }

  // U4: a player-mode session goes straight to the player screen.
  function onPlay(out: SessionStartOut) {
    navigate(`/play/${encodeURIComponent(out.session.id)}`);
  }

  return (
    <div className="min-h-full">
      <AppNav worldId={worldId} />
      <Toolbar
        worldId={worldId}
        onWorldIdChange={setWorldId}
        onLoad={load}
        onBuildDemo={buildDemo}
        onPickMap={setMapUrl}
        busy={busy}
      />
      <SessionBar
        worldId={worldId}
        sessionId={null}
        onSelect={onSelectSession}
        variant="picker"
        regions={data?.regions ?? []}
        onPlay={onPlay}
      />
      {error && <div className="p-2 text-danger">{error}</div>}
      {busy && (
        <div className="p-2 text-ink-soft" data-testid="busy">
          {t("editor.working")}
        </div>
      )}
      {!busy && data && data.regions.length === 0 && (
        <div data-testid="empty-hint" className="p-2 text-danger">
          {t("editor.emptyWorld", { world: worldId })}{" "}
          <code>locus world demo --name aldermoor --world {worldId}</code>
        </div>
      )}
      {!busy && !data && (
        <div data-testid="empty-hint" className="p-2 text-ink-soft">
          {t("editor.noWorld", { loadDemo: t("toolbar.loadDemo"), load: t("toolbar.load") })}
        </div>
      )}
      <Modal
        open={confirmReplace != null}
        title={t("editor.replaceTitle")}
        confirmTone="danger"
        confirmLabel={t("editor.replaceConfirm")}
        cancelLabel={t("action.cancel")}
        onConfirm={() => {
          setConfirmReplace(null);
          loadDemo(true);
        }}
        onCancel={() => setConfirmReplace(null)}
      >
        <span data-testid="replace-confirm">
          {t("editor.replaceBody", { n: confirmReplace?.open ?? 0 })}
        </span>
      </Modal>
      {data && (
        <div data-testid="graph-status" className="px-2 pb-2 text-xs text-ink-soft">
          {t("editor.status", {
            world: data.world_id,
            regions: data.regions.length,
            connections: data.connections.length,
            entities: data.entities?.length ?? 0,
            knowledge: data.knowledge.length,
          })}
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
              key={selected}
              worldId={worldId}
              regionId={selected}
              sessionId={null}
              onDeleted={load}
            />
          )}
          <AugmentPanel worldId={worldId} />
        </div>
      </div>
    </div>
  );
}
