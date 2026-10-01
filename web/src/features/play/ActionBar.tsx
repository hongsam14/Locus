import { useState } from "react";
import { t } from "../../i18n";
import type { TurnRun } from "../../types";
import { Button } from "../../ui";

/** Wait button + progress while a turn run is in flight (Q4=A), and — U6 — the
 * declaration box (US-4.5): free text, the server's length limit, one turn. The box is
 * cleared on send and restored when the server refuses (400 / 409, review R-14). */
export function ActionBar({
  running,
  disabled,
  onWait,
  onDeclare,
  maxChars = 300,
}: {
  running: TurnRun | null;
  disabled: boolean;
  onWait: () => void;
  onDeclare?: (text: string) => Promise<boolean>;
  maxChars?: number;
}) {
  const [draft, setDraft] = useState("");
  const text = draft.trim();
  const tooLong = text.length > maxChars;

  async function declare() {
    if (!onDeclare || disabled || !text || tooLong) return;
    const kept = draft;
    setDraft("");
    const accepted = await onDeclare(text);
    if (!accepted) setDraft(kept);
  }

  return (
    <div data-testid="action-bar" className="flex max-w-2xl flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" data-testid="wait-btn" disabled={disabled} onClick={onWait}>
          {t("play.wait")}
        </Button>
        {running && (
          <span data-testid="turn-progress" className="text-sm text-ink-soft animate-pulse">
            {t("play.running", { n: running.cost_turns })}
          </span>
        )}
      </div>
      {onDeclare && (
        <form
          className="flex flex-col gap-1"
          onSubmit={(e) => {
            e.preventDefault();
            void declare();
          }}
        >
          <textarea
            data-testid="declare-input"
            value={draft}
            rows={2}
            placeholder={t("play.declarePlaceholder")}
            onChange={(e) => setDraft(e.target.value)}
            className="sketch-border bg-paper-card px-2 py-1 text-sm text-ink outline-none focus:bg-highlight"
          />
          <div className="flex items-center gap-2">
            <span
              data-testid="declare-count"
              className={`text-xs ${tooLong ? "text-danger" : "text-ink-soft"}`}
            >
              {t("play.chars", { n: text.length, max: maxChars })}
            </span>
            <Button
              type="submit"
              size="sm"
              variant="primary"
              data-testid="declare-btn"
              disabled={disabled || !text || tooLong}
            >
              {t("play.declare")}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
