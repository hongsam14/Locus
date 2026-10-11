import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { useReplaceConfirm } from "../../api/http";
import { describeError, type DescribedError } from "../../errors";
import { t } from "../../i18n";
import type { ImportReport } from "../../types";
import { Button, ConfirmDialog, InlineError } from "../../ui";
import { groupByStage } from "./buildStages";

/** The World File and build actions behind [파일 ▾] (V8 frontend-components § 4.1, BLM § 7.1,
 * BR-V8-34). The hidden file input lives outside the disclosure, always mounted, so a pick
 * still arrives after the row has closed. The row closes on Esc, a press outside it, or the
 * start of one of its actions; focus goes back to [파일 ▾]. Errors show under the head, not
 * in the row, so they stay when it closes. */
export function FileActions({
  worldId,
  onLoaded,
  onBuild,
}: {
  worldId: string;
  onLoaded(report: ImportReport): void;
  onBuild(): void;
}) {
  const [open, setOpen] = useState(false);
  const toggleWrap = useRef<HTMLSpanElement | null>(null); // Button forwards no ref (React 18)
  const row = useRef<HTMLDivElement | null>(null);
  const input = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<object | null>(null);
  const replace = useReplaceConfirm(); // "replace?" then "close N sessions?" (U3 C8)
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<DescribedError | null>(null);

  const focusToggle = () => toggleWrap.current?.querySelector("button")?.focus();
  const close = (refocus = true) => {
    setOpen(false);
    if (refocus) focusToggle();
  };
  // a press outside the toggle and the row closes it (focus stays where the press went)
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (!row.current?.contains(target) && !toggleWrap.current?.contains(target)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  async function save() {
    close();
    setError(null);
    try {
      const data = await api.getWorldFile(worldId);
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${worldId}.world.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(describeError(e));
    }
  }

  async function pick(f: File | undefined) {
    if (!f) return;
    setError(null);
    try {
      setFile(JSON.parse(await readText(f)));
      replace.askReplace();
    } catch (e) {
      setError({ ...describeError(e), title: t("error.validation_failed.title") }); // not a World File
    }
  }

  async function load(confirm: boolean) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const report = await api.importWorldFile(worldId, file, { replace: true, confirm });
      setFile(null);
      if (report.ok) onLoaded(report);
      else {
        // refused before anything was written (duplicate ids, a failed backup): the stage in
        // words, the server's lines folded (BR-V8-15)
        const first = groupByStage(report.warnings)[0];
        setError({ title: first ? first.label : t("label.stage.other"), raw: report.warnings.map((w) => w.message).join("\n") });
      }
    } catch (e) {
      if (!replace.sessionsAsked(e, confirm)) setError(describeError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <span ref={toggleWrap} className="inline-flex">
        <Button size="sm" data-testid="file-menu" aria-expanded={open} aria-controls="editor-file-row"
          onClick={() => setOpen((v) => !v)}
          onKeyDown={(e) => e.key === "Escape" && open && close()}>
          {t("action.fileMenu")} ▾
        </Button>
      </span>
      {open && (
        <div ref={row} id="editor-file-row" data-testid="file-row" className="flex w-full flex-wrap gap-2"
          onKeyDown={(e) => e.key === "Escape" && close()}>
          <Button size="sm" data-testid="file-save" onClick={() => void save()}>{t("file.save")}</Button>
          <Button size="sm" data-testid="file-load" disabled={busy}
            onClick={() => {
              close(false);
              input.current?.click();
            }}>
            {t("file.load")}
          </Button>
          <Button size="sm" data-testid="file-build"
            onClick={() => {
              close(false);
              onBuild();
            }}>
            {t("file.build")}
          </Button>
        </div>
      )}
      <input ref={input} type="file" accept=".json,application/json" className="hidden" data-testid="file-input"
        onChange={(e) => {
          void pick(e.target.files?.[0]);
          e.target.value = ""; // the same file again is a new pick (U3 review S24)
        }} />
      {error && (
        <div className="w-full" data-testid="file-error">
          <InlineError error={error} />
        </div>
      )}
      <ConfirmDialog open={replace.open} tone="danger" busy={busy} title={t("file.load")} confirmLabel={t("action.confirm")}
        onCancel={() => {
          replace.cancel();
          setFile(null);
        }}
        onConfirm={() => void load(replace.answer())}>
        <span data-testid="file-confirm">
          {replace.ask === "replace" ? t("file.replaceConfirm") : t("file.closeSessionsConfirm", { n: replace.sessions })}
        </span>
      </ConfirmDialog>
    </>
  );
}

/** A file's text (``File.text`` where there is one, else ``FileReader``). */
function readText(f: File): Promise<string> {
  if (typeof f.text === "function") return f.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(f);
  });
}
