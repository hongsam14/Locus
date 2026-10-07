import { t } from "../../i18n";
import { Button, Select } from "../../ui";

export interface BulkProgress {
  done: number;
  total: number;
  failed: number;
}

/** Turn and whole-world buttons: a manual turn, event suggestions (1..5, BR-U7-10),
 * generate / regenerate for every region, and the bulk progress bar. */
export function ManualTurnPanel({
  closed,
  llmOff = false,
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
  llmOff?: boolean; // U8 (BR-U8-25): no LLM on the server — suggest and bulk generate off
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
        <Button data-testid="suggest-events-btn" onClick={onSuggest} disabled={closed || llmOff}
          title={llmOff ? t("llm.required") : undefined}>
          {t("gm.suggestEvents")}
        </Button>
        <Select
          label={t("gm.suggestN")}
          data-testid="suggest-n"
          value={String(suggestN)}
          disabled={closed}
          options={Array.from({ length: maxSuggest }, (_, i) => ({ value: String(i + 1), label: String(i + 1) }))}
          onChange={(v) => onSuggestN(Number(v))}
        />
        <Button data-testid="generate-all-btn" onClick={onGenerateAll} disabled={closed || bulk || llmOff}
          title={llmOff ? t("llm.required") : undefined}>
          {t("gm.generateAll")}
        </Button>
        <Button variant="danger" data-testid="regen-all-btn" onClick={onRegenAll}
          disabled={closed || bulk || llmOff} title={llmOff ? t("llm.required") : undefined}>
          {t("gm.regenAll")}
        </Button>
        {llmOff && <span className="text-xs text-muted" data-testid="llm-required">{t("llm.required")}</span>}
      </div>
      {progress && (
        <div data-testid="generate-progress" className="mt-2">
          <div className="h-1.5 border border-line-strong rounded-md overflow-hidden">
            <div
              className="h-full bg-accent"
              style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }}
            />
          </div>
          <div className="text-xs text-muted mt-0.5">
            {t("progress.done", { done: progress.done, total: progress.total })}
            {progress.failed ? ` · ${t("progress.failed", { failed: progress.failed })}` : ""}
          </div>
        </div>
      )}
    </>
  );
}
