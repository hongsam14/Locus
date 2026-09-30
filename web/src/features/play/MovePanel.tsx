import { t } from "../../i18n";
import type { MoveOption } from "../../types";
import { Button, Panel } from "../../ui";

/** Move options from the current region (FR-C2): cost in turns, blocked ones greyed. */
export function MovePanel({
  moves,
  disabled,
  onMove,
}: {
  moves: MoveOption[];
  disabled: boolean;
  onMove: (regionId: string) => void;
}) {
  return (
    <Panel title={t("play.moves")} data-testid="move-panel" className="max-w-2xl">
      {moves.length === 0 && <p className="text-xs text-ink-soft">—</p>}
      <ul className="space-y-1">
        {moves.map((m) => (
          <li
            key={m.region_id}
            data-testid={`move-${m.region_id}`}
            className={`flex items-center gap-2 text-sm ${m.passable ? "" : "opacity-50"}`}
          >
            <span className="flex-1">
              <b>{m.region_name}</b> <span className="text-ink-soft">· {m.kind}</span>{" "}
              {m.passable ? (
                <span>· {t("play.turns", { n: m.cost_turns })}</span>
              ) : (
                <span data-testid={`move-${m.region_id}-blocked`}>· {t("play.blocked")}</span>
              )}
            </span>
            <Button
              size="sm"
              variant="primary"
              data-testid={`move-${m.region_id}-btn`}
              disabled={disabled || !m.passable}
              onClick={() => onMove(m.region_id)}
            >
              {t("play.move")}
            </Button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
