import type { ReactNode } from "react";

// V2 (BLM § 10 correction): the browser's own <select> with token looks — the phone's
// picker, a dark list through `color-scheme`, no added JS. The test id goes on the
// <select> itself, so a test can still change it.
export function Select<T extends string>({
  label,
  value,
  options,
  onChange,
  placeholder,
  disabled,
  hideLabel = false,
  className = "",
  "data-testid": testId,
}: {
  label: ReactNode;
  value: T | "";
  options: { value: T; label: string; disabled?: boolean }[];
  onChange(v: T): void;
  placeholder?: string;
  disabled?: boolean;
  hideLabel?: boolean;
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <label className={`inline-flex flex-col gap-1 text-sm ${className}`.trim()}>
      <span className={hideLabel ? "sr-only" : "font-bold text-fg"}>{label}</span>
      <span className="relative inline-flex">
        <select
          data-testid={testId}
          className="min-h-11 w-full appearance-none rounded-md border border-line-strong bg-bg py-0 pl-3 pr-9 text-[15px] text-fg disabled:bg-disabled disabled:text-disabled-fg"
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value as T)}
        >
          {placeholder != null && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value} disabled={o.disabled}>
              {o.label}
            </option>
          ))}
        </select>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </span>
    </label>
  );
}
