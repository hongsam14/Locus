import { t } from "../../i18n";
import type { TurnRun } from "../../types";
import { Button } from "../../ui";

/** Wait button + progress while a turn run is in flight (Q4=A). */
export function ActionBar({
  running,
  disabled,
  onWait,
}: {
  running: TurnRun | null;
  disabled: boolean;
  onWait: () => void;
}) {
  return (
    <div data-testid="action-bar" className="flex flex-wrap items-center gap-3">
      <Button size="sm" data-testid="wait-btn" disabled={disabled} onClick={onWait}>
        {t("play.wait")}
      </Button>
      {running && (
        <span data-testid="turn-progress" className="text-sm text-ink-soft animate-pulse">
          {t("play.running", { n: running.cost_turns })}
        </span>
      )}
    </div>
  );
}
