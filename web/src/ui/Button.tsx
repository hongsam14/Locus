import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "danger";
type Size = "sm" | "md";

const base =
  "sketch-border inline-flex items-center gap-1 font-display leading-none " +
  "transition active:translate-y-px disabled:opacity-40 disabled:cursor-not-allowed";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-paper sketch-shadow hover:bg-ink-soft",
  ghost: "bg-paper-card text-ink sketch-shadow hover:bg-highlight",
  danger: "bg-danger text-paper sketch-shadow hover:opacity-90",
};

const sizes: Record<Size, string> = {
  sm: "px-2 py-0.5 text-sm",
  md: "px-3 py-1.5",
};

export function Button({
  variant = "ghost",
  size = "md",
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`.trim()}
      {...rest}
    />
  );
}
