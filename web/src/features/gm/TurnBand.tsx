import { t } from "../../i18n";
import type { RegionTurnChange, TurnResult } from "../../types";
import { Button } from "../../ui";
import { english, type NameOf } from "../play/names";
import { changeSummary, changeTitle } from "../play/summary";

export interface GmTurnOutcome {
  turn: number;
  changes: RegionTurnChange[];
  quiet: boolean;
  budgetExhausted: boolean;
  llmFailed: boolean;
}

/** A manual turn's answer as the band shows it (BLM § 5.2). */
export function outcomeOf(result: TurnResult): GmTurnOutcome {
  const changes = result.region_changes ?? [];
  return {
    turn: result.turn,
    changes,
    quiet: changes.every((rc) => !changeSummary(rc)),
    budgetExhausted: !!result.budget_exhausted,
    llmFailed: !!result.llm_failed,
  };
}

/** The last turn's result in one place, under the turn tools (V6 Q2=A, BR-V6-07): the turn,
 * the regions that changed — a name chooses that region — and the budget or LLM line. It is
 * not a notification. [close] folds it; the next turn replaces it. The live region is always
 * there, so a screen reader hears the result when it lands. */
export function TurnBand({
  outcome,
  nameOf = english,
  onPickRegion,
  onClose,
}: {
  outcome: GmTurnOutcome | null;
  nameOf?: NameOf;
  onPickRegion(regionId: string): void;
  onClose(): void;
}) {
  return (
    <div role="status" data-testid="turn-band-live">
      {outcome && (
        <section data-testid="turn-band"
          className="flex flex-col gap-2 rounded-lg border border-accent/60 bg-sunken p-3 shadow-panel">
          <div className="flex items-start gap-2">
            <h2 className="flex-1 font-heading text-lg">
              {outcome.quiet ? t("notice.quietTurnGm") : t("notice.turnPassedGm", { n: outcome.turn })}
            </h2>
            <Button size="sm" variant="ghost" data-testid="turn-band-close" onClick={onClose}>
              {t("action.close")}
            </Button>
          </div>
          {!outcome.quiet && (
            <ul className="flex flex-col gap-1 text-sm">
              {outcome.changes.filter((rc) => changeSummary(rc)).map((rc) => (
                <li key={rc.region_id}>
                  <button type="button" data-testid={`turn-band-region-${rc.region_id}`}
                    className="font-bold text-accent underline-offset-2 hover:underline"
                    onClick={() => onPickRegion(rc.region_id)}>
                    {nameOf("regions", rc.region_id, "name", changeTitle(rc))}
                  </button>
                  : {changeSummary(rc)}
                </li>
              ))}
            </ul>
          )}
          {outcome.budgetExhausted && <p className="text-sm text-muted">{t("notice.turnBudget")}</p>}
          {outcome.llmFailed && <p className="text-sm text-muted">{t("notice.turnLlmFailed")}</p>}
        </section>
      )}
    </div>
  );
}
