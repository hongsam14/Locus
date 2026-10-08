// Whether a media query matches now, following changes (V4, FD frontend-components § 5).
// Used only where the screen renders a different component per width (the action dock,
// the sheets, the talk place); layout spacing stays in CSS. Without `matchMedia` (jsdom,
// old browsers) it is false, so tests get the middle layout unless they stub it.
import { useEffect, useState } from "react";

function query(q: string): MediaQueryList | null {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" ? window.matchMedia(q) : null;
}

export function useMedia(q: string): boolean {
  const [matches, setMatches] = useState(() => query(q)?.matches ?? false);
  useEffect(() => {
    const list = query(q);
    if (!list) return;
    setMatches(list.matches);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    list.addEventListener?.("change", onChange);
    return () => list.removeEventListener?.("change", onChange);
  }, [q]);
  return matches;
}

/** The two widths the screens tell apart (FD § 1): wide ≥ 1024 px, narrow < 640 px. */
export const WIDE = "(min-width: 1024px)";
export const NARROW = "(max-width: 639px)";
