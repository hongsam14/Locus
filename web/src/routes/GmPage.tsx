import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MapOverlay } from "../MapOverlay";
import { RegionPanel } from "../RegionPanel";
import { SessionBar } from "../SessionBar";
import { SessionPanel } from "../SessionPanel";
import { api } from "../api";
import type { GameSession, WorldExport } from "../types";
import { Button } from "../ui";
import { AppNav } from "./AppNav";

// GameMaster screen (F1): one session, its world map, the session NPC view of the
// selected region, and the GameMaster hub (rumors / distortion / turns / events).
export function GmPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<GameSession | null>(null);
  const [data, setData] = useState<WorldExport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionRev, setSessionRev] = useState(0);
  // Current route session + loaded world, readable from async continuations so a
  // late response for a previous session never rebinds the screen (review U1 #3).
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const dataRef = useRef<WorldExport | null>(null);
  dataRef.current = data;

  const loadSession = useCallback(async (): Promise<GameSession | null> => {
    const sid = sessionId;
    try {
      const s = await api.getSession(sid);
      if (sessionIdRef.current !== sid) return null; // stale: route moved on
      setSession(s);
      setError(null);
      return s;
    } catch (e) {
      if (sessionIdRef.current === sid) setError(String(e));
      return null;
    }
  }, [sessionId]);

  useEffect(() => {
    let active = true;
    setError(null);
    (async () => {
      const s = await loadSession();
      if (!s || !active) return;
      // Same world as before: keep the map, entities and the selected region
      // (review U1 #7). Only a world change reloads the export.
      if (dataRef.current?.world_id === s.world_id) return;
      setData(null);
      setSelected(null);
      try {
        const world = await api.exportWorld(s.world_id);
        if (active && sessionIdRef.current === sessionId) setData(world);
      } catch (e) {
        if (active) setError(String(e));
      }
    })();
    return () => {
      active = false;
    };
  }, [loadSession, sessionId]);

  // After a SessionPanel write (advance turn / generate / support / distortion),
  // refresh the session (turn may have changed) and force RegionPanel to reload.
  function onSessionChanged() {
    setSessionRev((n) => n + 1);
    loadSession();
  }

  // Switching sessions in the bar changes the route (same-session events, e.g.
  // Close, just refresh the object). The bar hides "none" on this screen.
  function onSelectSession(s: GameSession | null) {
    if (!s) return;
    if (s.id !== sessionId) navigate(`/gm/${encodeURIComponent(s.id)}`);
    else setSession(s);
  }

  return (
    <div className="min-h-full">
      <AppNav worldId={session?.world_id ?? data?.world_id} sessionId={sessionId} />
      {session && (
        <SessionBar
          worldId={session.world_id}
          sessionId={session.id}
          onSelect={onSelectSession}
          allowNone={false}
        />
      )}
      {error && (
        <div className="p-2 text-danger flex flex-wrap items-center gap-2" data-testid="gm-error">
          <span>{error}</span>
          <Button size="sm" data-testid="gm-retry-btn" onClick={() => loadSession()}>
            다시 시도
          </Button>
          {!session && (
            <span className="text-xs text-ink-soft">
              세션이 없으면 에디터에서 새 세션을 시작하세요.
            </span>
          )}
        </div>
      )}
      {!session && !error && (
        <div className="p-2 text-ink-soft" data-testid="busy">
          loading session…
        </div>
      )}
      {session && (
        <div className="flex flex-wrap items-center gap-3 px-3 py-1 text-xs text-ink-soft">
          <span data-testid="gm-world">
            world <b>{session.world_id}</b>
            {data && (
              <>
                {" "}
                · regions {data.regions.length} · connections {data.connections.length}
              </>
            )}
          </span>
          <label className="inline-flex items-center gap-1">
            Map:
            <input
              data-testid="map-file-input"
              type="file"
              accept="image/*"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setMapUrl(URL.createObjectURL(f));
              }}
            />
          </label>
        </div>
      )}
      {session && (
        <div className="flex flex-wrap gap-4 p-3">
          <MapOverlay
            regions={data?.regions ?? []}
            connections={data?.connections ?? []}
            selectedId={selected}
            mapImageUrl={mapUrl}
            onSelect={setSelected}
            onMove={() => {}}
          />
          <div className="flex min-w-72 flex-col gap-4">
            {selected && (
              <RegionPanel
                key={`${selected}-${session.id}-${sessionRev}`}
                worldId={session.world_id}
                regionId={selected}
                sessionId={session.id}
              />
            )}
            <SessionPanel session={session} regionId={selected} onChanged={onSessionChanged} />
          </div>
        </div>
      )}
    </div>
  );
}
