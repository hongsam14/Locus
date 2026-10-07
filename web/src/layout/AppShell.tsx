import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { llmOff, useCapabilities } from "../capabilities";
import { t, useLang } from "../i18n";
import { Toaster } from "../ui";
import { LangSwitch } from "./LangSwitch";

// The frame of every screen (V2 FR-D5, BLM § 9): the top bar with the logo, the menu and the
// display language; one LLM-off band under it (BR-V2-20 — screens no longer draw their own);
// the one notification area. Which menu items open is as before (AppNav, U8 BR-U8-1): GM
// waits for a session, the editor link without a world is the world list.
const item = ({ isActive }: { isActive: boolean }) =>
  `inline-flex min-h-11 items-center rounded-md px-3 ${isActive ? "bg-sunken font-bold text-fg" : "text-muted hover:text-fg"}`;

export function AppShell({
  worldId,
  sessionId,
  children,
}: {
  worldId?: string | null;
  sessionId?: string | null;
  children: ReactNode;
}) {
  useLang(); // labels follow the display language
  const caps = useCapabilities();
  const [menuOpen, setMenuOpen] = useState(false);
  const editorTo = worldId ? `/editor/${encodeURIComponent(worldId)}` : "/";
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-line bg-chrome">
        <div className="mx-auto flex min-h-14 max-w-[1240px] flex-wrap items-center gap-x-6 gap-y-1 px-4 sm:px-6">
          <Link to="/" data-testid="nav-home" className="font-display text-2xl tracking-wide text-accent">
            Locus
          </Link>
          <button
            type="button"
            className="ml-auto inline-flex min-h-11 min-w-11 items-center justify-center rounded-md text-fg hover:bg-sunken sm:hidden"
            aria-expanded={menuOpen}
            aria-controls="app-menu"
            aria-label={t("action.menu")}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <nav
            id="app-menu"
            data-testid="app-nav"
            aria-label={t("action.menu")}
            className={`${menuOpen ? "flex" : "hidden"} w-full flex-col gap-1 pb-2 sm:flex sm:w-auto sm:flex-1 sm:flex-row sm:pb-0`}
          >
            <NavLink to="/" end className={item}>
              {t("nav.worlds")}
            </NavLink>
            <NavLink data-testid="nav-play" to={sessionId ? `/play/${encodeURIComponent(sessionId)}` : "/play"} className={item}>
              {t("nav.play")}
            </NavLink>
            {sessionId ? (
              <NavLink data-testid="nav-gm" to={`/gm/${encodeURIComponent(sessionId)}`} className={item}>
                {t("nav.gm")}
              </NavLink>
            ) : (
              <span className="inline-flex min-h-11 items-center px-3 text-faint" title={t("nav.gmLocked")}>
                {t("nav.gm")}
              </span>
            )}
            <NavLink data-testid="nav-editor" to={editorTo} className={item}>
              {t("nav.editor")}
            </NavLink>
          </nav>
          <LangSwitch />
        </div>
      </header>
      {llmOff(caps) && (
        <div role="status" data-testid="llm-notice" className="border-b border-tint-info-line bg-tint-info">
          <div className="mx-auto flex max-w-[1240px] items-start gap-2 px-4 py-2 text-sm text-info-fg sm:px-6">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true" className="mt-0.5 flex-none text-info">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v.01M11 12h1v5h1" />
            </svg>
            <span>{t("notice.llmOff")}</span>
          </div>
        </div>
      )}
      <div className="flex-1">{children}</div>
      <Toaster />
    </div>
  );
}
