import type { HTMLAttributes } from "react";

// V2: every tone is a token pair from the allowed table (domain-entities § 1.6).
type Tone = "neutral" | "event" | "danger" | "success" | "info" | "promoted" | "deed" | "pruned";

const tones: Record<Tone, string> = {
  neutral: "border-line bg-sunken text-fg",
  event: "border-tint-event-line bg-tint-event text-event",
  danger: "border-tint-danger-line bg-tint-danger text-danger",
  success: "border-tint-success-line bg-tint-success text-success",
  info: "border-tint-info-line bg-tint-info text-info",
  promoted: "border-accent bg-accent text-on-accent",
  deed: "border-danger bg-transparent text-danger",
  pruned: "border-line bg-sunken text-muted line-through",
};

export function Badge({
  tone = "neutral",
  className = "",
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={
        `inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ` +
        `${tones[tone]} ${className}`.trim()
      }
      {...rest}
    />
  );
}
