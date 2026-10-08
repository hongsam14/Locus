import { useState } from "react";
import { t } from "../../i18n";
import { Button, ConfirmDialog, Select } from "../../ui";
import type { BulkProgress } from "./bulk";

/** The turn and whole-world buttons, always at the top of the GM panel (V6 Q1=A, BR-V6-06):
 * [advance turn] — off while it runs, while a bulk run goes and on an ended session; event
 * suggestions (1..the server's cap); rumors for the empty regions; every region's rumors
 * again, after asking. Without an LLM those buttons are off and their title says why; the
 * one notice is the app's band (BR-V6-23). */
export function TurnTools({
  closed,
  llmOff = false,
  advancing,
  regionBusy = false,
  suggesting,
  bulk,
  suggestN,
  maxSuggest,
  onSuggestN,
  onAdvance,
  onSuggest,
  onGenerateAll,
  onRegenAll,
}: {
  closed: boolean;
  llmOff?: boolean;
  advancing: boolean;
  /** A region's own rumor write runs: the bulk runs wait for it (code review 01 #7). */
  regionBusy?: boolean;
  suggesting: boolean;
  bulk: BulkProgress | null;
  suggestN: number;
  maxSuggest: number;
  onSuggestN(n: number): void;
  onAdvance(): void;
  onSuggest(): void;
  onGenerateAll(): void;
  onRegenAll(): void;
}) {
  const [asking, setAsking] = useState(false);
  const running = bulk != null;
  // while the GM's own turn runs, the other writes would be refused (code review 01 #35)
  const bulkOff = closed || running || llmOff || advancing || regionBusy;
  const why = llmOff ? t("llm.required") : undefined;
  return (
    <section data-testid="turn-tools" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-2">
        <Button variant="primary" data-testid="advance-turn-btn" busy={advancing} disabled={closed || running}
          onClick={onAdvance}>
          {t("gm.advanceTurn")}
        </Button>
        <Select
          label={t("label.suggestCount")}
          data-testid="suggest-n"
          value={String(Math.min(suggestN, maxSuggest))}
          disabled={closed}
          options={Array.from({ length: maxSuggest }, (_, i) => ({ value: String(i + 1), label: String(i + 1) }))}
          onChange={(v) => onSuggestN(Number(v))}
        />
        <Button data-testid="suggest-events-btn" busy={suggesting} disabled={closed || llmOff || advancing} title={why}
          onClick={onSuggest}>
          {t("action.suggestEvents")}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button data-testid="generate-all-btn" disabled={bulkOff} title={why} onClick={onGenerateAll}>
          {t("action.generateEmpty")}
        </Button>
        <Button variant="danger" data-testid="regen-all-btn" disabled={bulkOff} title={why}
          onClick={() => setAsking(true)}>
          {t("action.regenAllRumors")}
        </Button>
      </div>
      {bulk && (
        <div data-testid="generate-progress">
          <div className="h-1.5 overflow-hidden rounded-md border border-line-strong">
            <div className="h-full bg-accent" style={{ width: `${bulk.total ? (bulk.done / bulk.total) * 100 : 0}%` }} />
          </div>
          <div className="mt-0.5 text-xs text-muted">
            {t("progress.done", { done: bulk.done, total: bulk.total })}
            {bulk.failed ? ` · ${t("progress.failed", { failed: bulk.failed })}` : ""}
          </div>
        </div>
      )}
      <ConfirmDialog
        open={asking}
        tone="danger"
        title={t("action.regenAllRumors")}
        confirmLabel={t("action.regenerate")}
        cancelLabel={t("action.cancel")}
        confirmTestId="regen-all-confirm"
        onConfirm={() => {
          setAsking(false);
          onRegenAll();
        }}
        onCancel={() => setAsking(false)}
      >
        {t("confirm.regenAllRumors")}
      </ConfirmDialog>
    </section>
  );
}
