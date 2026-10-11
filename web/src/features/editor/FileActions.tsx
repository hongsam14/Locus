import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { useReplaceConfirm } from "../../api/http";
import { describeError, type DescribedError } from "../../errors";
import { t } from "../../i18n";
import type { ImportReport } from "../../types";
import { Button, ConfirmDialog, InlineError } from "../../ui";

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
      setError({ ...describeError(e), title: t("error.bad_world_file.title") }); // not a World File (review #22)
    }
  }

  async function load(confirm: boolean) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const report = await api.importWorldFile(worldId, file, { replace: true, confirm });
      setFile(null);
      const outcome = loadOutcome(report);
      // written, even with problems: the world on screen is the old one, so the page reads
      // the new one and clears what belonged to the old (code review 01 #1)
      if (outcome.kind !== "refused") onLoaded(report);
      if (outcome.error) setError(outcome.error);
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
          {t("action.fileMenu")} <span aria-hidden="true">▾</span>
        </Button>
      </span>
      {open && (
        // its own line under the head line, after [이 월드로 플레이] on screen (FC § 2); in the
        // DOM it follows its toggle, so the tab order goes into what the toggle opened
        <div ref={row} id="editor-file-row" data-testid="file-row" className="order-last flex basis-full flex-wrap gap-2"
          onKeyDown={(e) => e.key === "Escape" && close()}>
          <Button size="sm" data-testid="file-save" onClick={() => void save()}>{t("file.save")}</Button>
          <Button size="sm" data-testid="file-load" disabled={busy}
            onClick={() => {
              // the toggle takes the focus first: the pressed button goes with the row, and a
              // dialog opened next returns the focus to whatever held it (code review 01 #5)
              close();
              input.current?.click();
            }}>
            {t("file.load")}
          </Button>
          <Button size="sm" data-testid="file-build"
            onClick={() => {
              close();
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
        <div className="order-last basis-full" data-testid="file-error">
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

/** What a World File load did, from its report (code review 01 #1). The server answers
 * `ok=false` both when it stopped before writing anything — duplicate ids, a backup it could
 * not make (V7) — and when it wrote the world but dropped items whose references point
 * nowhere, or failed part way after deleting the old world. Only the first is a refusal. */
export function loadOutcome(report: ImportReport): { kind: "loaded" | "refused" | "partial"; error?: DescribedError } {
  const warnings = report.warnings ?? [];
  const raw = warnings.map((w) => w.message).join("\n") || undefined;
  const errors = warnings.filter((w) => w.severity === "error");
  const stop = errors.find((w) => w.stage === "duplicate-ids" || w.stage === "backup");
  if (stop) {
    return { kind: "refused", error: { title: t("notice.loadRefused"),
      action: t(stop.stage === "backup" ? "notice.loadRefusedBackup" : "notice.loadRefusedDuplicate"), raw } };
  }
  if (report.ok) return { kind: "loaded" };
  if (errors.some((w) => w.stage === "commit")) return { kind: "partial", error: { title: t("notice.loadIncomplete"), raw } };
  return { kind: "partial", error: { title: t("notice.loadedDropped", { n: errors.length }), raw } };
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
