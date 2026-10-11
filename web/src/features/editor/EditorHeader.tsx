import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { describeError, type DescribedError } from "../../errors";
import { useMounted } from "../../hooks";
import { t } from "../../i18n";
import type { ImportReport, Region, WorldExport } from "../../types";
import { Button } from "../../ui";
import { NewSessionForm } from "../play/NewSessionForm";
import { connectionCount } from "./connections";
import { FileActions } from "./FileActions";

/** The editor's one head line (V8 frontend-components § 4.1, UX-17, Q2 = A): the world's name
 * as the page title — its id only when it has no name — the counts, [파일 ▾], the open-session
 * count, and [이 월드로 플레이]. On a narrow screen the line wraps. */
export function EditorHeader({
  worldId,
  world,
  name,
  openSessions,
  onLoaded,
  onBuild,
}: {
  worldId: string;
  world: WorldExport | undefined;
  name: string | null | undefined;
  openSessions: number | null | undefined;
  onLoaded(report: ImportReport): void;
  onBuild(): void;
}) {
  return (
    <header data-testid="editor-header" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h1 className="min-w-0 break-words font-heading text-2xl" data-testid="world-name">
          {name || worldId}
        </h1>
        {world && (
          <span className="text-sm text-muted" data-testid="graph-status">
            {t("label.worldCounts", { regions: world.regions.length, connections: connectionCount(world.connections), knowledge: world.knowledge.length })}
          </span>
        )}
        {/* `contents`: the buttons sit on the head line, and the file row opened by [파일 ▾]
            wraps under the whole line instead of between the two buttons (V8 captures) */}
        <div className="contents">
          <FileActions worldId={worldId} onLoaded={onLoaded} onBuild={onBuild} />
          <PlayThisWorld worldId={worldId} regions={world?.regions ?? []} />
        </div>
      </div>
      {(openSessions ?? 0) > 0 && (
        <p className="text-sm text-muted" data-testid="open-sessions">{t("notice.openSessions", { n: openSessions ?? 0 })}</p>
      )}
    </header>
  );
}

/** [이 월드로 플레이] (Q2 = A, BR-V8-27): the home's player form — a name and a start region —
 * then the play screen. No session without a player is made here. Off without a region. */
export function PlayThisWorld({ worldId, regions }: { worldId: string; regions: Region[] }) {
  const navigate = useNavigate();
  const mounted = useMounted();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<DescribedError | null>(null);
  const none = regions.length === 0;
  return (
    <>
      <Button size="sm" variant="primary" data-testid="play-this-world" disabled={none}
        aria-describedby={none ? "play-this-world-hint" : undefined} onClick={() => setOpen(true)}>
        {t("action.playThisWorld")}
      </Button>
      {/* said on the page, not in a tooltip: a turned-off button takes no focus and a touch
          screen shows no title (BLM § 8.4, code review 01 #20) */}
      {none && (
        <span id="play-this-world-hint" className="text-xs text-muted" data-testid="play-hint">
          {t("hint.playNeedsRegion")}
        </span>
      )}
      <NewSessionForm open={open} worldId={worldId} regions={regions} busy={busy} error={error}
        onCancel={() => {
          setOpen(false);
          setError(null);
        }}
        onSubmit={async (name, startRegionId) => {
          setError(null);
          setBusy(true);
          try {
            const out = await api.startSession(worldId, { name, start_region_id: startRegionId });
            if (mounted.current) navigate(`/play/${encodeURIComponent(out.session.id)}`);
          } catch (e) {
            if (mounted.current) setError(describeError(e)); // said in the form (V4 review 01 #22)
          } finally {
            if (mounted.current) setBusy(false);
          }
        }} />
    </>
  );
}
