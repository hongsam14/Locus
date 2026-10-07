import * as RadixDialog from "@radix-ui/react-dialog";
import { useRef, type ReactNode } from "react";

// V2 (FR-D4, BR-V2-21): one dialog. Radix moves focus in, keeps it there, brings it back
// to the opener, closes on Esc and names the dialog by its title. role="dialog". The
// screens open it from their own buttons, not a Radix Trigger, so the element that had
// focus is remembered here and given focus back on close (Radix alone would focus nothing).
const SIZES = { sm: "max-w-sm", md: "max-w-md", lg: "max-w-2xl" } as const;

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = "md",
}: {
  open: boolean;
  onOpenChange(open: boolean): void;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: keyof typeof SIZES;
}) {
  const opener = useRef<HTMLElement | null>(null);
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-50 bg-scrim" />
        <RadixDialog.Content
          className={
            `fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 ` +
            `flex-col gap-3 overflow-y-auto rounded-xl border border-line-strong bg-surface p-6 text-fg shadow-pop ${SIZES[size]}`
          }
          onOpenAutoFocus={() => {
            opener.current = document.activeElement as HTMLElement | null;
          }}
          onCloseAutoFocus={(e) => {
            e.preventDefault();
            opener.current?.focus?.();
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
