import { useEffect, useState } from "react";
import { api } from "./api";
import type { GameSession } from "./types";

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
      style={{ display: "flex", gap: 8, alignItems: "center", padding: 8, borderBottom: "1px solid #eee" }}
    >
      <strong style={{ fontSize: 13 }}>Session</strong>
      <select
        data-testid="session-select"
        value={sessionId ?? ""}
        onChange={(e) => onSelect(sessions.find((s) => s.id === e.target.value) ?? null)}
      >
        <option value="">— none —</option>
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {s.id.slice(0, 8)} · turn {s.turn} · {s.status}
          </option>
        ))}
      </select>
      <button data-testid="session-new-btn" onClick={start}>
        New Session
      </button>
      <button
        data-testid="session-close-btn"
        onClick={close}
        disabled={!current || current.status === "closed"}
      >
        Close
      </button>
      {current && (
        <span data-testid="session-status" style={{ fontSize: 12, color: "#666" }}>
          turn {current.turn} · {current.status}
        </span>
      )}
      {error && <span style={{ color: "#c0392b", fontSize: 12 }}>{error}</span>}
    </div>
  );
}
