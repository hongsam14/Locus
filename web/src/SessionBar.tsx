import { useEffect, useState } from "react";
import { api } from "./api";
import { NewSessionForm } from "./features/play/NewSessionForm";
import { t } from "./i18n";
import type { GameSession, Region, SessionStartOut } from "./types";
import { Button, Select } from "./ui";

interface Props {
  worldId: string;
  sessionId: string | null;
  onSelect: (session: GameSession | null) => void;
  /** "picker": choose/start only (editor screen); "full": also close + status (GM screen). */
  variant?: "full" | "picker";
  /** Offer the "— none —" entry. The GM screen always has a session, so it hides it. */
  allowNone?: boolean;
  /** U4: regions of the loaded world for the player-mode start form. */
  regions?: Region[];
  /** U4: when given, a "플레이 시작" button opens the player-mode form; the
   * created session is handed here (the editor navigates to /play/:id). */
  onPlay?: (out: SessionStartOut) => void;
}

export function SessionBar({
  worldId,
  sessionId,
  onSelect,
  variant = "full",
  allowNone = true,
  regions = [],
  onPlay,
}: Props) {
  const [sessions, setSessions] = useState<GameSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [playOpen, setPlayOpen] = useState(false);
  const [playBusy, setPlayBusy] = useState(false);

  async function refresh() {
    setError(null);
    try {
      setSessions(await api.listSessions(worldId));
    } catch (e) {
      setError(String(e));
    }
  }

  // reload the session list when the world changes; drop any current selection
  useEffect(() => {
    onSelect(null);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [worldId]);

  const current = sessions.find((s) => s.id === sessionId) ?? null;

  async function start() {
    setError(null);
    try {
      const s = await api.startSession(worldId);
      await refresh();
      onSelect(s);
    } catch (e) {
      setError(String(e));
    }
  }

  async function startPlay(name: string, startRegionId: string) {
    setError(null);
    setPlayBusy(true);
    try {
      const out = await api.startSession(worldId, { name, start_region_id: startRegionId });
      setPlayOpen(false);
      await refresh();
      onPlay?.(out);
    } catch (e) {
      setError(String(e));
    } finally {
      setPlayBusy(false);
    }
  }

  async function close() {
    if (!sessionId) return;
    setError(null);
    try {
      const s = await api.closeSession(sessionId);
      await refresh();
      onSelect(s);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div
      data-testid="session-bar"
      className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2"
    >
      <strong className="font-heading text-lg">{t("session.title")}</strong>
      <Select
        label={t("session.title")}
        hideLabel
        data-testid="session-select"
        value={sessionId ?? ""}
        options={[
          ...(allowNone ? [{ value: "", label: t("session.none") }] : []),
          ...sessions.map((s) => ({
            value: s.id,
            label: `${s.id.slice(0, 8)} · ${t("common.turn", { n: s.turn })} · ${s.status}`,
          })),
        ]}
        onChange={(v) => onSelect(sessions.find((s) => s.id === v) ?? null)}
      />
      <Button size="sm" variant="primary" data-testid="session-new-btn" onClick={start}>
        {t("session.new")}
      </Button>
      {onPlay && (
        <Button size="sm" data-testid="session-play-btn" onClick={() => setPlayOpen(true)}>
          {t("session.play")}
        </Button>
      )}
      {onPlay && (
        <NewSessionForm
          open={playOpen}
          regions={regions}
          busy={playBusy}
          onSubmit={startPlay}
          onCancel={() => setPlayOpen(false)}
        />
      )}
      {variant === "full" && (
        <Button
          size="sm"
          data-testid="session-close-btn"
          onClick={close}
          disabled={!current || current.status === "closed"}
        >
          {t("session.close")}
        </Button>
      )}
      {variant === "full" && current && (
        <span data-testid="session-status" className="text-xs text-muted">
          {t("common.turn", { n: current.turn })} · {current.status}
        </span>
      )}
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  );
}
