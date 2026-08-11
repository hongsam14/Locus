import { useEffect, useState } from "react";
import { api } from "./api";
import type { GameSession } from "./types";
import { Button } from "./ui";

interface Props {
  worldId: string;
  sessionId: string | null;
  onSelect: (session: GameSession | null) => void;
}

export function SessionBar({ worldId, sessionId, onSelect }: Props) {
  const [sessions, setSessions] = useState<GameSession[]>([]);
  const [error, setError] = useState<string | null>(null);

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
      <strong className="font-display text-lg">Session</strong>
      <select
        data-testid="session-select"
        value={sessionId ?? ""}
        onChange={(e) => onSelect(sessions.find((s) => s.id === e.target.value) ?? null)}
        className="sketch-border bg-paper-card px-2 py-1 text-sm"
      >
        <option value="">— none —</option>
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {s.id.slice(0, 8)} · turn {s.turn} · {s.status}
          </option>
        ))}
      </select>
      <Button size="sm" variant="primary" data-testid="session-new-btn" onClick={start}>
        New Session
      </Button>
      <Button
        size="sm"
        data-testid="session-close-btn"
        onClick={close}
        disabled={!current || current.status === "closed"}
      >
        Close
      </Button>
      {current && (
        <span data-testid="session-status" className="text-xs text-ink-soft">
          turn {current.turn} · {current.status}
        </span>
      )}
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  );
}
