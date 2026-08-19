import type { ReactNode } from "react";

type Tone = "neutral" | "event" | "danger";

const accents: Record<Tone, string> = {
  neutral: "bg-paper-card",
  event: "bg-highlight",
  danger: "bg-danger text-paper",
};

/** Presentational toast card (X2). Wiring (turn-change notifications) is X3. */
export function Toast({
  tone = "neutral",
  title,
  children,
  onClose,
  ...rest
}: {
  tone?: Tone;
  title?: ReactNode;
  children?: ReactNode;
  onClose?: () => void;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`sketch-border sketch-shadow p-2 ${accents[tone]}`.trim()} {...rest}>
      <div className="flex items-start gap-2">
        <div className="flex-1">
          {title != null && <div className="font-display text-sm mb-0.5">{title}</div>}
          {children != null && <div className="text-sm">{children}</div>}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            aria-label="close"
            className="font-display text-sm leading-none px-1 hover:opacity-70"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}
