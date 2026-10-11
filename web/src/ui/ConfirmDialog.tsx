import type { ReactNode } from "react";
import type { DescribedError } from "../errors";
import { t } from "../i18n";
import { Button } from "./Button";
import { Dialog } from "./Dialog";
import { InlineError } from "./StatusView";

// V2 (FR-D4, BR-V2-21): "are you sure?" on the shared Dialog. While the confirmed request
// runs (`busy`) the confirm button shows it and cannot be pressed again, and the dialog does
// not close under it; a failure stays in the dialog (`error`) instead of closing it. A
// confirmation that cannot go ahead at all (`confirmDisabled`) turns off the confirm button
// only — cancel, Esc and an outside press still close it (V2 review #1).
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  cancelLabel,
  tone = "default",
  busy = false,
  confirmDisabled = false,
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
  confirmDisabled?: boolean;
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
            disabled={confirmDisabled}
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
