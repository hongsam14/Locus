import { useState } from "react";
import { t } from "../i18n";

/** Show the Korean translation by default with a per-item toggle to the original
 * (FR-UX3.4 / Q11=B / Q5=A). When no translation is available, shows the original
 * with no toggle. */
export function LocalizedText({
  ko,
  original,
  testId,
}: {
  ko?: string | null;
  original: string;
  testId?: string;
}) {
  const [showOriginal, setShowOriginal] = useState(false);
  const hasKo = ko != null && ko !== "" && ko !== original;
  const text = hasKo && !showOriginal ? (ko as string) : original;
  return (
    <span data-testid={testId}>
      {text}
      {hasKo && (
        <button
          type="button"
          data-testid={testId ? `${testId}-toggle` : undefined}
          onClick={() => setShowOriginal((v) => !v)}
          className="ml-1 text-xs text-ink-soft underline hover:opacity-70"
        >
          {showOriginal ? t("action.translated") : t("action.original")}
        </button>
      )}
    </span>
  );
}
