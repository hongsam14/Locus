import type { TurnOutcome } from "../../hooks";
import { t } from "../../i18n";
import { Button } from "../../ui";
import { english, type NameOf } from "./names";
import { changeSummary, changeTitle } from "./summary";

/** The last turn's result in one place under the region name (V4 Q2=A, BR-V4-04): the turn,
 * the regions that changed (names from the map), the GM's line for a declaration, a talk's
 * judgment. It is not a notification: only warnings are. [close] folds it; the next action
 * empties it and the next result opens it again. */
export function ResultBand({
  outcome,
  nameOf = english,
  onClose,
}: {
  outcome: TurnOutcome | null;
  nameOf?: NameOf;
  onClose: () => void;
}) {
  // the live region is always there and only its content changes, so a screen reader hears
  // the result when it lands (code review 01 #26); empty, it takes back the layout's gap
  return (
    <div role="status" data-testid="result-live" className="empty:-mt-6">
      {outcome && <Band outcome={outcome} nameOf={nameOf} onClose={onClose} />}
    </div>
  );
}

function Band({ outcome, nameOf, onClose }: { outcome: TurnOutcome; nameOf: NameOf; onClose: () => void }) {
  const { declaration } = outcome;
  return (
    <section data-testid="result-band"
      className="flex flex-col gap-2 rounded-lg border border-accent/60 bg-sunken p-3 shadow-panel">
      <div className="flex items-start gap-2">
        <h2 className="flex-1 font-heading text-lg">
          {outcome.quiet ? t("story.quietTurn") : t("story.turnPassed", { n: outcome.turn })}
        </h2>
        <Button size="sm" variant="ghost" data-testid="result-band-close" onClick={onClose}>
          {t("action.close")}
        </Button>
      </div>
      {outcome.changes.length > 0 && (
        <ul className="flex flex-col gap-1 text-sm">
          {outcome.changes.map((rc) => (
            <li key={rc.region_id} data-testid={`result-change-${rc.region_id}`}>
              <b>{nameOf("regions", rc.region_id, "name", changeTitle(rc))}</b>: {changeSummary(rc) || t("play.quiet")}
            </li>
          ))}
        </ul>
      )}
      {declaration && (
        // the world's answer to a declaration, written in the display language (FD-U6 Q3=A)
        <div data-testid="narration-card" className="border-l-2 border-accent pl-3">
          <p className="whitespace-pre-line font-story">{declaration.text}</p>
          {declaration.llm_calls === 0 && (
            <p data-testid="narration-fallback" className="mt-1 text-xs text-muted">{t("play.narrationFallback")}</p>
          )}
        </div>
      )}
    </section>
  );
}
