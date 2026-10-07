import type { ButtonHTMLAttributes, ReactNode } from "react";

// V2 (FR-D4, BR-V2-06/08): token colours, the body font, 44 px targets on a phone.
// "secondary" is the bordered default; "ghost" has no border (V2 FD correction).
type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const base =
  "inline-flex items-center justify-center gap-2 rounded-md border font-body font-bold leading-none " +
  "transition-colors disabled:cursor-not-allowed disabled:border-line disabled:bg-disabled disabled:text-disabled-fg";

const variants: Record<Variant, string> = {
  primary: "border-accent bg-accent text-on-accent hover:border-accent-hover hover:bg-accent-hover",
  secondary: "border-line-strong bg-surface text-fg hover:bg-sunken",
  ghost: "border-transparent bg-transparent text-accent hover:bg-sunken",
  danger: "border-danger bg-danger text-on-danger hover:opacity-90",
};

const sizes: Record<Size, string> = {
  sm: "min-h-11 px-3 text-sm sm:min-h-9",
  md: "min-h-11 px-4 text-[15px]",
};

function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true" className="animate-spin">
      <path d="M12 3 a9 9 0 1 1 -9 9" />
    </svg>
  );
}

export function Button({
  variant = "secondary",
  size = "md",
  busy = false,
  icon,
  className = "",
  disabled,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; busy?: boolean; icon?: ReactNode }) {
  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`.trim()}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <Spinner /> : icon}
      {children}
    </button>
  );
}
