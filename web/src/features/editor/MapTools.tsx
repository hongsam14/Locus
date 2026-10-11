import { useRef, type KeyboardEvent } from "react";
import { t } from "../../i18n";
import { Button } from "../../ui";
import type { MapTool } from "./connections";

const TOOLS: MapTool[] = ["select", "addRegion", "connect"];

/** The map's three tools (US-2.2, Q5=A), always visible so it is clear what a press does.
 * A toolbar with one tab stop: the arrow keys move between the tools, Home/End jump, the
 * chosen tool is pressed (FR-S6, BR-V8-32). */
export function MapTools({
  tool,
  disabled,
  hint,
  onTool,
}: {
  tool: MapTool;
  disabled: boolean;
  hint: string;
  onTool(next: MapTool): void;
}) {
  const bar = useRef<HTMLDivElement | null>(null); // Button forwards no ref (React 18)
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const buttons = [...(bar.current?.querySelectorAll("button") ?? [])];
    const at = buttons.findIndex((b) => b === document.activeElement);
    if (at < 0) return;
    const to =
      e.key === "ArrowRight" ? (at + 1) % TOOLS.length
        : e.key === "ArrowLeft" ? (at - 1 + TOOLS.length) % TOOLS.length
          : e.key === "Home" ? 0
            : e.key === "End" ? TOOLS.length - 1
              : -1;
    if (to < 0) return;
    e.preventDefault();
    buttons[to]?.focus();
  };
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <div ref={bar} role="toolbar" aria-label={t("label.mapTools")} className="flex flex-wrap gap-1" onKeyDown={onKeyDown}>
        {TOOLS.map((m) => (
          <Button
            key={m}
            size="sm"
            variant={tool === m ? "primary" : "ghost"}
            aria-pressed={tool === m}
            tabIndex={tool === m ? 0 : -1}
            data-testid={`map-tool-${m === "addRegion" ? "add-region" : m}`}
            disabled={disabled}
            onClick={() => onTool(m)}
          >
            {t(`map.tool.${m}`)}
          </Button>
        ))}
      </div>
      <span className="min-w-0 text-xs text-muted" data-testid="map-hint">
        {hint}
      </span>
    </div>
  );
}
