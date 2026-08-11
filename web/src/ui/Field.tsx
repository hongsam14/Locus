import type { InputHTMLAttributes, ReactNode } from "react";

/** Labelled text input with ink styling. Forwards all input props (incl. data-testid). */
export function Field({
  label,
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label?: ReactNode }) {
  return (
    <label className="inline-flex flex-col gap-0.5 text-sm">
      {label != null && <span className="text-ink-soft">{label}</span>}
      <input
        className={
          `sketch-border bg-paper-card px-2 py-1 text-ink outline-none ` +
          `focus:bg-highlight ${className}`.trim()
        }
        {...rest}
      />
    </label>
  );
}
