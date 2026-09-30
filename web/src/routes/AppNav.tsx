import { NavLink } from "react-router-dom";

interface Props {
  worldId?: string | null;
  sessionId?: string | null;
}

const link = ({ isActive }: { isActive: boolean }) =>
  `px-1.5 py-0.5 ${isActive ? "font-bold underline" : "text-ink-soft hover:text-ink"}`;

// Top-level navigation between the three screens (F1 / AD-R8): editor, GM, player.
export function AppNav({ worldId, sessionId }: Props) {
  const editorTo = `/editor/${encodeURIComponent(worldId || "aldermoor")}`;
  return (
    <nav
      data-testid="app-nav"
      className="flex flex-wrap items-center gap-2 border-b border-ink px-3 py-1.5 bg-paper-card text-sm"
    >
      <strong className="font-display text-2xl mr-2">Locus</strong>
      <NavLink data-testid="nav-editor" to={editorTo} className={link}>
        에디터
      </NavLink>
      {sessionId ? (
        <NavLink data-testid="nav-gm" to={`/gm/${encodeURIComponent(sessionId)}`} className={link}>
          GM
        </NavLink>
      ) : (
        <span className="px-1.5 py-0.5 text-ink-soft" title="세션을 선택하면 열립니다">
          GM
        </span>
      )}
      <NavLink
        data-testid="nav-play"
        to={sessionId ? `/play/${encodeURIComponent(sessionId)}` : "/play"}
        className={link}
      >
        플레이
      </NavLink>
    </nav>
  );
}
