import type { ReactNode } from "react";
import type { DescribedError } from "../errors";
import { t } from "../i18n";
import { Button } from "./Button";
import { Dialog } from "./Dialog";
import { InlineError } from "./StatusView";

// V2 (FR-D4, BR-V2-21): "are you sure?" on the shared Dialog. While the confirmed request
// runs (`busy`) the confirm button shows it and cannot be pressed again; a failure stays in
// the dialog (`error`) instead of closing it.
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  cancelLabel,
  tone = "default",
  busy = false,
  error,
  onConfirm,
  onCancel,
  confirmTestId,
  cancelTestId,
  children,
}: {
  open: boolean;
  title: ReactNode;
  body?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
  busy?: boolean;
  error?: DescribedError;
  onConfirm(): void | Promise<void>;
  onCancel(): void;
  confirmTestId?: string;
  cancelTestId?: string;
  children?: ReactNode;
}) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !busy) onCancel();
      }}
      title={title}
      size="sm"
      footer={
        <>
          <Button data-testid={cancelTestId} onClick={onCancel} disabled={busy}>
            {cancelLabel ?? t("action.cancel")}
          </Button>
          <Button
            data-testid={confirmTestId}
            variant={tone === "danger" ? "danger" : "primary"}
            busy={busy}
            onClick={() => void onConfirm()}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {body != null && <div className="text-[15px]">{body}</div>}
      {children}
      {error && <InlineError error={error} />}
    </Dialog>
  );
}
