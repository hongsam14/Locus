import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { t } from "../../i18n";
import type { WorldState } from "../../types";
import { Button } from "../../ui";

const STEPS = [0, 25, 50, 75, 100]; // ink strength per distortion band (BR-U7-23)

/** Five distortion bands, design tokens only: paper for [0, .2), red ink above. */
export function distortionColor(d: number): string {
  const band = Math.min(4, Math.max(0, Math.floor(d * 5)));
  return `color-mix(in srgb, var(--color-danger) ${STEPS[band]}%, var(--color-paper-card))`;
}

/** What the map draws for a state: a fill per region and an "active/promoted" badge
 * (with ✦ and the deed rumor count when there are any). */
export function overlayOf(state: WorldState | null): {
  fill: Record<string, string>;
  badge: Record<string, string>;
} {
  const fill: Record<string, string> = {};
  const badge: Record<string, string> = {};
  for (const r of state?.regions ?? []) {
    fill[r.region_id] = distortionColor(r.distortion);
    badge[r.region_id] =
      `${r.active_rumors}/${r.promoted_rumors}` + (r.deed_rumors ? ` ✦${r.deed_rumors}` : "");
  }
  return { fill, badge };
}

/** Reads the world state while the overlay is on, again whenever `rev` changes (a turn
 * or a GM write). Only the latest answer paints. */
export function useWorldState(sessionId: string, on: boolean, rev: number) {
  const [state, setState] = useState<WorldState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);
  useEffect(() => {
    if (!on) {
      setState(null);
      setError(null);
      return;
    }
    const mine = ++seq.current;
    Promise.resolve()
      .then(() => api.getWorldState(sessionId))
      .then((s) => {
        if (mine === seq.current) {
          setState(s ?? null);
          setError(null);
        }
      })
      .catch((e) => {
        if (mine === seq.current) setError(String(e));
      });
  }, [sessionId, on, rev]);
  return { state, error };
}

/** The overlay's switch and legend (US-5.5). The map itself is MapOverlay. */
export function WorldStateOverlay({
  on,
  onToggle,
  error,
}: {
  on: boolean;
  onToggle: () => void;
  error: string | null;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <Button size="sm" data-testid="gm-state-toggle" onClick={onToggle} aria-pressed={on}>
        {t("gm.stateToggle")}
      </Button>
      {on && (
        <span data-testid="gm-state-legend" className="inline-flex items-center gap-1">
          {STEPS.map((s, i) => (
            <span
              key={s}
              className="inline-block h-3 w-4 sketch-border"
              style={{ background: distortionColor(i / 5 + 0.01) }}
            />
          ))}
          <span className="text-ink-soft">{t("gm.stateLegend")}</span>
        </span>
      )}
      {on && error && (
        <span data-testid="gm-state-error" className="text-danger">
          {error}
        </span>
      )}
    </div>
  );
}
