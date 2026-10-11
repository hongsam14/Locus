import { useId, type InputHTMLAttributes, type ReactNode } from "react";

// V2 (FR-S6): every input has a label — `hideLabel` keeps it for screen readers only.
export function Field({
  label,
  hint,
  error,
  hideLabel = false,
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  hideLabel?: boolean;
}) {
  const id = useId();
  const described = [hint != null ? `${id}-hint` : null, error != null ? `${id}-error` : null].filter(Boolean).join(" ");
  return (
    <label className="inline-flex flex-col gap-1 text-sm">
      <span className={hideLabel ? "sr-only" : "font-bold text-fg"}>{label}</span>
      <input
        className={
          `min-h-11 rounded-md border border-line-strong bg-bg px-3 text-[15px] text-fg ` +
          `placeholder:text-faint disabled:bg-disabled disabled:text-disabled-fg ${className}`.trim()
        }
        aria-describedby={described || undefined}
        aria-invalid={error != null || undefined}
        {...rest}
      />
      {hint != null && <span id={`${id}-hint`} className="text-muted">{hint}</span>}
      {error != null && <span id={`${id}-error`} className="text-danger">{error}</span>}
    </label>
  );
}
