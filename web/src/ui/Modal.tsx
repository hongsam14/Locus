import type { ReactNode } from "react";
import { Button } from "./Button";

/** Confirm dialog (X2 presentational). Used by X3 for destructive actions. */
export function Modal({
  open,
  title,
  children,
  confirmLabel = "확인",
  cancelLabel = "취소",
  confirmTone = "primary",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title?: ReactNode;
  children?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmTone?: "primary" | "danger";
  onConfirm?: () => void;
  onCancel?: () => void;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="sketch-border sketch-shadow bg-paper-card p-4 max-w-sm w-full">
        {title != null && <h2 className="font-display text-lg mb-2">{title}</h2>}
        {children != null && <div className="text-sm mb-4">{children}</div>}
        <div className="flex justify-end gap-2">
          <Button size="sm" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button size="sm" variant={confirmTone} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
