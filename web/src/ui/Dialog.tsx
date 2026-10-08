import * as RadixDialog from "@radix-ui/react-dialog";
import { useRef, type ReactNode } from "react";

// V2 (FR-D4, BR-V2-21): one dialog. Radix moves focus in, keeps it there, brings it back
// to the opener, closes on Esc and names the dialog by its title. role="dialog". The
// screens open it from their own buttons, not a Radix Trigger, so the element that had
// focus is remembered here and given focus back on close (Radix alone would focus nothing);
// if that element is gone (the confirmed action removed its row) focus goes to the screen's
// <main>. A press in the notification area is not an outside press: closing a toast must
// not close the dialog under it (V2 review #3).
const SIZES = { sm: "max-w-sm", md: "max-w-md", lg: "max-w-2xl" } as const;
// V4 (BR-V4-26): where the dialog sits. "center" is the V2 dialog; "sheet" rises from the
// bottom edge at full width (a phone's declare / move sheet); "full" covers the screen (a
// phone's talk). Only the frame differs — naming, focus, Esc and focus return are the same.
const FRAME = {
  center:
    "left-1/2 top-1/2 max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 rounded-xl border p-6",
  sheet:
    "inset-x-0 bottom-0 max-h-[85vh] w-full rounded-t-xl border-x border-t p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]",
  full: "inset-0 h-full w-full p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]",
} as const;

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = "md",
  variant = "center",
  testId,
}: {
  open: boolean;
  onOpenChange(open: boolean): void;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: keyof typeof SIZES;
  variant?: keyof typeof FRAME;
  testId?: string; // on the dialog element itself (its title and body inside)
}) {
  const opener = useRef<HTMLElement | null>(null);
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-50 bg-scrim" />
        <RadixDialog.Content
          data-testid={testId}
          data-variant={variant}
          className={
            `fixed z-50 flex flex-col gap-3 overflow-y-auto border-line-strong bg-surface text-fg shadow-pop ` +
            `${FRAME[variant]} ${variant === "center" ? SIZES[size] : ""}`
          }
          onOpenAutoFocus={() => {
            opener.current = document.activeElement as HTMLElement | null;
          }}
          onCloseAutoFocus={(e) => {
            e.preventDefault();
            const back = opener.current;
            if (back?.isConnected) back.focus();
            else document.getElementById("main")?.focus();
          }}
          onInteractOutside={(e) => {
            if (e.target instanceof Element && e.target.closest("[data-toaster]")) e.preventDefault();
          }}
          // no description: say so, or Radix warns about a missing one
          {...(description == null ? { "aria-describedby": undefined } : {})}
        >
          <RadixDialog.Title className="font-heading text-xl">{title}</RadixDialog.Title>
          {description != null && (
            <RadixDialog.Description className="text-[15px] text-muted">{description}</RadixDialog.Description>
          )}
          {children}
          {footer != null && <div className="mt-2 flex flex-wrap justify-end gap-2">{footer}</div>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
