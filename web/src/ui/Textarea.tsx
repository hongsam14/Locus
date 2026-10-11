import { useId, type ReactNode, type TextareaHTMLAttributes } from "react";
import { t } from "../i18n";

export function Textarea({
  label,
  hint,
  hideLabel = false,
  className = "",
  maxLength,
  value,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: ReactNode; hint?: ReactNode; hideLabel?: boolean }) {
  const id = useId();
  const length = typeof value === "string" ? [...value].length : 0;
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className={hideLabel ? "sr-only" : "font-bold text-fg"}>{label}</span>
      <textarea
        className={
          `rounded-md border border-line-strong bg-bg px-3 py-2 text-[15px] leading-relaxed text-fg ` +
          `placeholder:text-faint disabled:bg-disabled disabled:text-disabled-fg ${className}`.trim()
        }
        aria-describedby={hint != null ? `${id}-hint` : undefined}
        maxLength={maxLength}
        value={value}
        {...rest}
      />
      <span className="flex gap-2 text-muted">
        {hint != null && <span id={`${id}-hint`} className="flex-1">{hint}</span>}
        {maxLength != null && <span className="ml-auto">{t("unit.chars", { n: length, max: maxLength })}</span>}
      </span>
    </label>
  );
}
