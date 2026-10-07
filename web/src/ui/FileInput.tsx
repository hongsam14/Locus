import { useId, useRef, type ReactNode } from "react";
import { t } from "../i18n";
import { Button } from "./Button";

// V2 (UX-09): no browser "Choose File / No file chosen" text. The real input stays (hidden)
// and carries the test id, so a test can still hand it files; it is emptied after each pick
// so the same file can be picked again.
export function FileInput({
  label,
  accept,
  multiple,
  onFiles,
  hint,
  chosen,
  disabled,
  "data-testid": testId,
}: {
  label: ReactNode;
  accept?: string;
  multiple?: boolean;
  onFiles(files: File[]): void;
  hint?: ReactNode;
  chosen?: string[];
  disabled?: boolean;
  "data-testid"?: string;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement | null>(null);
  return (
    <div className="flex flex-col gap-1 text-sm">
      <span id={`${id}-label`} className="font-bold text-fg">{label}</span>
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-line-strong bg-bg p-2">
        <input
          ref={input}
          id={id}
          type="file"
          className="sr-only"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          aria-labelledby={`${id}-label`}
          data-testid={testId}
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            e.target.value = "";
            if (files.length) onFiles(files);
          }}
        />
        <Button size="sm" disabled={disabled} aria-describedby={`${id}-label`} onClick={() => input.current?.click()}>
          {t("action.chooseFile")}
        </Button>
        <span className="text-muted">{chosen && chosen.length ? chosen.join(", ") : t("empty.noFile")}</span>
      </div>
      {hint != null && <span className="text-muted">{hint}</span>}
    </div>
  );
}
