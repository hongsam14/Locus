import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MapOverlay } from "../MapOverlay";
import { RegionKnowledgePanel } from "../features/gm/RegionKnowledgePanel";
import { SessionBar } from "../SessionBar";
import { DeedPanel } from "../features/gm/DeedPanel";
import { GmHub } from "../features/gm/GmHub";
import { PlayerStrip } from "../features/gm/PlayerStrip";
import { WorldStateOverlay, overlayOf, useWorldState } from "../features/gm/WorldStateOverlay";
import { api } from "../api";
import { t, useLang } from "../i18n";
import type { GameSession, Player, WorldExport } from "../types";
import { Button } from "../ui";
import { AppNav } from "./AppNav";

// GameMaster screen (F1): one session, its world map, the session NPC view of the
// selected region, and the GameMaster hub (rumors / distortion / turns / events).
// U7 (Q1=B): reached from the play screen's "GM mode" and left with "back to play";
// the player's place and turn stay in view, and the map can show the world state.
export function GmPage() {
  useLang(); // labels follow the display language
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<GameSession | null>(null);
  const [data, setData] = useState<WorldExport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionRev, setSessionRev] = useState(0);
  const [deedRev, setDeedRev] = useState(0); // U6: a void changed rumors on this page
  const [player, setPlayer] = useState<Player | null>(null);
  const [stateOn, setStateOn] = useState(false);
  const world = useWorldState(sessionId, stateOn, sessionRev + deedRev);
  const overlay = useMemo(() => overlayOf(world.state), [world.state]);
  const regionNames = useMemo(
    () => Object.fromEntries((data?.regions ?? []).map((r) => [r.id, r.name])),
    [data],
  );
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
    setPlayer(null); // the map marker is the new session's or none (U3 review S14)
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

  // A deed void turned rumors off: re-read the GM hub and the region panel (the deed
  // panel already re-read itself, so it is not keyed on this: U6 review C1).
  function onDeedChanged() {
    setDeedRev((n) => n + 1);
    void loadSession(); // a 409 "session is closed" from a void must lock the page (#11)
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
            {t("gm.retry")}
          </Button>
          {!session && (
            <span className="text-xs text-ink-soft">
              {t("gm.noSessionHint")}
            </span>
          )}
        </div>
      )}
      {!session && !error && (
        <div className="p-2 text-ink-soft" data-testid="busy">
          {t("gm.loading")}
        </div>
      )}
      {session && (
        <PlayerStrip
          key={session.id} // another session starts with no player of the last (U3 S14)
          sessionId={session.id}
          turn={session.turn}
          regionNames={regionNames}
          rev={sessionRev}
          onPlayer={setPlayer}
        />
      )}
      {session && (
        <div className="flex flex-wrap items-center gap-3 px-3 py-1 text-xs text-ink-soft">
          <span data-testid="gm-world">
            {t("gm.world", { world: session.world_id })}
            {data && (
              <>
                {" · "}
                {t("gm.worldCounts", {
                  regions: data.regions.length,
                  connections: data.connections.length,
                })}
              </>
            )}
          </span>
          <label className="inline-flex items-center gap-1">
            {t("toolbar.pickMap")}
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
          <div className="flex flex-col gap-2">
            <WorldStateOverlay
              on={stateOn}
              onToggle={() => setStateOn((v) => !v)}
              error={world.error}
            />
            <MapOverlay
              regions={data?.regions ?? []}
              connections={data?.connections ?? []}
              selectedId={selected}
              mapImageUrl={mapUrl}
              onSelect={setSelected}
              onMove={() => {}}
              markerId={player?.region_id ?? null}
              regionFill={stateOn ? overlay.fill : undefined}
              regionBadge={stateOn ? overlay.badge : undefined}
            />
          </div>
          <div className="flex min-w-72 flex-col gap-4">
            {selected && (
              <RegionKnowledgePanel
                key={`${selected}-${session.id}-${sessionRev}-${deedRev}`}
                worldId={session.world_id}
                regionId={selected}
                sessionId={session.id}
              />
            )}
            <GmHub
              session={session}
              regionId={selected}
              regionNames={regionNames}
              onChanged={onSessionChanged}
              reloadKey={deedRev}
            />
            <DeedPanel
              key={`deeds-${session.id}`}
              sessionId={session.id}
              closed={session.status === "closed"}
              onChanged={onDeedChanged}
              reloadKey={sessionRev}
            />
          </div>
        </div>
      )}
    </div>
  );
}
