import { Link, NavLink } from "react-router-dom";
import { LangSwitch as LangToggle } from "../layout/LangSwitch";
import { t, useLang } from "../i18n";

interface Props {
  worldId?: string | null;
  sessionId?: string | null;
}

const link = ({ isActive }: { isActive: boolean }) =>
  `px-1.5 py-0.5 ${isActive ? "font-bold underline" : "text-ink-soft hover:text-ink"}`;

// Top-level navigation between the three screens (F1 / AD-R8): editor, GM, player,
// and the display-language toggle on the right (U5, shown on every screen).
export function AppNav({ worldId, sessionId }: Props) {
  useLang(); // labels follow the display language
  // no world chosen yet: the world list is where one is picked (U8, BR-U8-1; U3 S01)
  const editorTo = worldId ? `/editor/${encodeURIComponent(worldId)}` : "/";
  return (
    <nav
      data-testid="app-nav"
      className="flex flex-wrap items-center gap-2 border-b border-ink px-3 py-1.5 bg-paper-card text-sm"
    >
      <Link to="/" data-testid="nav-home" className="font-display text-2xl mr-2 font-bold">
        Locus
      </Link>
      <NavLink data-testid="nav-editor" to={editorTo} className={link}>
        {t("nav.editor")}
      </NavLink>
      {sessionId ? (
        <NavLink data-testid="nav-gm" to={`/gm/${encodeURIComponent(sessionId)}`} className={link}>
          {t("nav.gm")}
        </NavLink>
      ) : (
        <span className="px-1.5 py-0.5 text-ink-soft" title={t("nav.gmLocked")}>
          {t("nav.gm")}
        </span>
      )}
      <NavLink
        data-testid="nav-play"
        to={sessionId ? `/play/${encodeURIComponent(sessionId)}` : "/play"}
        className={link}
      >
        {t("nav.play")}
      </NavLink>
      <span className="ml-auto">
        <LangToggle />
      </span>
    </nav>
  );
}
