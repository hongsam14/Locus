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
  /** Options with the same `group` next to each other are drawn under one `<optgroup>`. */
  options: { value: T; label: string; disabled?: boolean; group?: string }[];
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
          {runs(options).map((run, i) =>
            run.group == null ? (
              run.items.map((o) => (
                <option key={o.value} value={o.value} disabled={o.disabled}>
                  {o.label}
                </option>
              ))
            ) : (
              <optgroup key={`g${i}`} label={run.group}>
                {run.items.map((o) => (
                  <option key={o.value} value={o.value} disabled={o.disabled}>
                    {o.label}
                  </option>
                ))}
              </optgroup>
            ),
          )}
        </select>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </span>
    </label>
  );
}

/** The options cut into runs of the same group, in order (V6: the GM's ended sessions). */
function runs<O extends { group?: string }>(options: O[]): { group?: string; items: O[] }[] {
  const out: { group?: string; items: O[] }[] = [];
  for (const o of options) {
    const last = out[out.length - 1];
    if (last && last.group === o.group) last.items.push(o);
    else out.push({ group: o.group, items: [o] });
  }
  return out;
}
