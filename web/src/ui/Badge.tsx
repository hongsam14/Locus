import type { HTMLAttributes } from "react";

type Tone = "neutral" | "promoted" | "pruned" | "event" | "danger";

const tones: Record<Tone, string> = {
  neutral: "bg-paper text-ink-soft",
  promoted: "bg-ink text-paper",
  pruned: "bg-paper text-ink-soft line-through opacity-70",
  event: "bg-highlight text-ink",
  danger: "bg-danger text-paper",
};

export function Badge({
  tone = "neutral",
  className = "",
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={
        `sketch-border inline-flex items-center px-1.5 py-0.5 text-xs font-display ` +
        `${tones[tone]} ${className}`.trim()
      }
      {...rest}
    />
  );
}
