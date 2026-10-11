import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { GmSessionView } from "../features/gm/GmSessionView";
import { useGmSession } from "../features/gm/useGmSession";
import { useMedia, WIDE } from "../hooks";
import { t, useLang } from "../i18n";
import { AppShell } from "../layout";
import { Button, InlineError } from "../ui";

// The GameMaster screen (V6 FR-S3, Q1=A): the map beside the turn tools and five tabs, one
// result band (Q2=A). The page holds what outlives a session of the same world — the world,
// its names and sessions, the chosen region, the map picture and the overlay switch — and
// draws one session's view inside `key={sessionId}`, so nothing of the last session shows
// (#14, RE-F14). A failed read offers [retry], which reads again the session and the world
// (RE-F01). Reached from the menu's GM; left with [back to play] (U7 Q1=B).
export function GmPage() {
  useLang(); // labels follow the display language
  const { sessionId = "" } = useParams();
  const gm = useGmSession(sessionId);
  const wide = useMedia(WIDE);
  const [selected, setSelected] = useState<string | null>(null);
  const [overlayOn, setOverlayOn] = useState(true);
  const [picture, setPicture] = useState<{ url: string; name: string } | null>(null);

  // another world drops the chosen region; a region the world no longer has is dropped too
  useEffect(() => setSelected(null), [gm.worldId]);
  useEffect(() => {
    if (selected && gm.world && !gm.world.regions.some((r) => r.id === selected)) setSelected(null);
  }, [gm.world, selected]);

  return (
    <AppShell worldId={gm.worldId} sessionId={sessionId}>
      {gm.state === "error" && gm.error ? (
        <div data-testid="gm-error" className="mx-auto flex w-full max-w-[1240px] flex-col items-start gap-3 px-4 py-6 sm:px-6">
          <InlineError error={gm.error} />
          <Button data-testid="gm-retry-btn" onClick={gm.retry}>
            {t("action.retry")}
          </Button>
          {gm.error.status === 404 && (
            <p className="text-sm text-muted">
              {t("hint.startFromDemo")} <Link to="/" className="text-accent underline">{t("action.goHome")}</Link>
            </p>
          )}
        </div>
      ) : (
        <>
          {!gm.session && (
            <div data-testid="busy" role="status" className="mx-auto w-full max-w-[1240px] px-4 pt-4 text-sm text-muted sm:px-6">
              {t("gm.loading")}
            </div>
          )}
          <GmSessionView
            key={sessionId}
            sessionId={sessionId}
            gm={gm}
            wide={wide}
            selected={selected}
            onSelect={setSelected}
            overlayOn={overlayOn}
            onToggleOverlay={() => setOverlayOn((v) => !v)}
            mapUrl={picture?.url ?? null}
            mapName={picture?.name ?? null}
            onMapFile={(file) => setPicture({ url: URL.createObjectURL(file), name: file.name })}
          />
        </>
      )}
    </AppShell>
  );
}
