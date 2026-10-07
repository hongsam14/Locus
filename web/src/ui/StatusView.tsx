import type { ReactNode } from "react";
import type { DescribedError } from "../errors";
import { t } from "../i18n";
import { Button } from "./Button";

// V2 (FR-S5, UX-10): loading, empty, error and ready look different. A first read shows a
// skeleton, never the empty sentence.
export function InlineError({ error, onRetry }: { error: DescribedError; onRetry?(): void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-1 rounded-lg border border-tint-danger-line bg-tint-danger p-3 text-sm">
      <strong className="text-danger">{error.title}</strong>
      {error.action && <span className="text-muted">{error.action}</span>}
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          {t("action.retry")}
        </Button>
      )}
      {error.raw && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer">{t("action.details")}</summary>
          {error.raw}
        </details>
      )}
    </div>
  );
}

export function StatusView({
  state,
  error,
  emptyText,
  emptyHint,
  onRetry,
  skeleton = "lines",
  children,
}: {
  state: "loading" | "empty" | "error" | "ready";
  error?: DescribedError;
  emptyText?: string;
  emptyHint?: string;
  onRetry?(): void;
  skeleton?: "lines" | "cards";
  children?: ReactNode;
}) {
  if (state === "loading") {
    return (
      <div role="status" className="flex flex-col gap-2 p-1" data-testid="status-loading">
        {(skeleton === "cards" ? [0, 1] : [70, 90, 55]).map((w, i) =>
          skeleton === "cards" ? (
            <span key={i} className="block h-16 rounded-lg bg-sunken" />
          ) : (
            <span key={i} className="block h-3 rounded bg-sunken" style={{ width: `${w}%` }} />
          ),
        )}
        <span className="text-sm text-muted">{t("label.loading")}</span>
      </div>
    );
  }
  if (state === "error" && error) return <InlineError error={error} onRetry={onRetry} />;
  if (state === "empty") {
    return (
      <div className="flex flex-col items-start gap-1 p-1 text-sm" data-testid="status-empty">
        {emptyText && <strong className="text-fg">{emptyText}</strong>}
        {emptyHint && <span className="text-muted">{emptyHint}</span>}
      </div>
    );
  }
  return <>{children}</>;
}
