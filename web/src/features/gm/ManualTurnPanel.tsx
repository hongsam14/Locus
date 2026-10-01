import { t } from "../../i18n";
import { Button } from "../../ui";

export interface BulkProgress {
  done: number;
  total: number;
  failed: number;
}

/** Turn and whole-world buttons: a manual turn, event suggestions (1..5, BR-U7-10),
 * generate / regenerate for every region, and the bulk progress bar. */
export function ManualTurnPanel({
  closed,
  progress,
  suggestN,
  maxSuggest = 5,
  onSuggestN,
  onAdvance,
  onSuggest,
  onGenerateAll,
  onRegenAll,
}: {
  closed: boolean;
  progress: BulkProgress | null;
  suggestN: number;
  maxSuggest?: number;
  onSuggestN: (n: number) => void;
  onAdvance: () => void;
  onSuggest: () => void;
  onGenerateAll: () => void;
  onRegenAll: () => void;
}) {
  const bulk = progress != null;
  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="primary" data-testid="advance-turn-btn" onClick={onAdvance} disabled={closed}>
          {t("gm.advanceTurn")}
        </Button>
        <Button data-testid="suggest-events-btn" onClick={onSuggest} disabled={closed}>
          {t("gm.suggestEvents")}
        </Button>
        <label className="inline-flex items-center gap-1 text-xs">
          {t("gm.suggestN")}
          <select
            data-testid="suggest-n"
            value={suggestN}
            disabled={closed}
            onChange={(e) => onSuggestN(Number(e.target.value))}
            className="sketch-border bg-paper-card px-1 py-0.5"
          >
            {Array.from({ length: maxSuggest }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <Button data-testid="generate-all-btn" onClick={onGenerateAll} disabled={closed || bulk}>
          {t("gm.generateAll")}
        </Button>
        <Button variant="danger" data-testid="regen-all-btn" onClick={onRegenAll} disabled={closed || bulk}>
          {t("gm.regenAll")}
        </Button>
      </div>
      {progress && (
        <div data-testid="generate-progress" className="mt-2">
          <div className="h-1.5 sketch-border overflow-hidden">
            <div
              className="h-full bg-ink"
              style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }}
            />
          </div>
          <div className="text-xs text-ink-soft mt-0.5">
            {t("progress.done", { done: progress.done, total: progress.total })}
            {progress.failed ? ` · ${t("progress.failed", { failed: progress.failed })}` : ""}
          </div>
        </div>
      )}
    </>
  );
}
