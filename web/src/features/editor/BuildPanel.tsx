import { useRef, useState } from "react";
import { api } from "../../api";
import { needsLlm, openSessionsOf, statusOf, useReplaceConfirm } from "../../api/http";
import { llmOff, useCapabilities } from "../../capabilities";
import { t } from "../../i18n";
import type { BuildReport } from "../../types";
import { Button, ConfirmDialog, Dialog, Field, FileInput, InProgressBadge } from "../../ui";
import { BuildReportPanel } from "./BuildReportPanel";

const FIELDS = [
  { name: "memos", label: "build.memos", accept: ".txt,.md,text/plain" },
  { name: "maps", label: "build.maps", accept: ".json,application/json" },
  { name: "images", label: "build.images", accept: "image/png,image/jpeg,image/webp" },
  { name: "concept_arts", label: "build.conceptArts", accept: "image/png,image/jpeg,image/webp" },
] as const;

/** Build a world from sources (US-2.1, BR-U3-35): notes, structured maps, map images and
 * concept art as multipart. An existing world is replaced only after a yes; open sessions
 * are closed only after a second yes (BR-U2-25). Where the screen does not know whether
 * the typed id exists (``/``), the first send does not replace and the server's 409 asks
 * the question (U3 review #6). Over-limit files answer 413/422 and the server's text is
 * shown (nfr §1.1). */
export function BuildPanel({
  open,
  worldId: fixedId,
  exists,
  onClose,
  onBuilt,
}: {
  open: boolean;
  worldId?: string; // fixed when building the open world
  exists: boolean;
  onClose: () => void;
  onBuilt: (worldId: string, report: BuildReport) => void;
}) {
  const [worldId, setWorldId] = useState(fixedId ?? "");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [memo, setMemo] = useState("");
  const [files, setFiles] = useState<Record<string, File[]>>({});
  const replaceQ = useReplaceConfirm(); // "replace?" then "close N sessions?" (U3 C8)
  const noLlm = llmOff(useCapabilities()); // U8 (BR-U8-25): building calls the LLM
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<BuildReport | null>(null);
  const closedMidBuild = useRef(false);
  if (!open) return null;
  const id = (fixedId ?? worldId).trim();
  const hasInput = memo.trim() || Object.values(files).some((f) => f.length);

  async function send(replace: boolean, confirm: boolean) {
    const form = new FormData();
    for (const { name: field } of FIELDS) for (const f of files[field] ?? []) form.append(field, f);
    if (memo.trim()) form.append("memos", new File([memo], "typed.txt", { type: "text/plain" }));
    if (name.trim()) form.append("name", name.trim());
    if (description.trim()) form.append("description", description.trim());
    form.append("replace", String(replace));
    form.append("confirm", String(confirm));
    setBusy(true);
    setError(null);
    try {
      const r = await api.uploadBuild(id, form);
      setReport(r);
      onBuilt(id, r);
    } catch (e) {
      if (replaceQ.sessionsAsked(e, confirm)) return;
      if (statusOf(e) === 409 && !replace && !openSessionsOf(e)) replaceQ.askReplace(); // the id exists
      else setError(needsLlm(e) ? t("llm.required") : String(e)); // BR-U8-27
    } finally {
      setBusy(false);
      // the file boxes were unmounted while it ran: their files are not shown any more,
      // so they must not ride along on a next [build] (U3 #14)
      if (closedMidBuild.current) setFiles({});
      closedMidBuild.current = false;
    }
  }

  /** Closing an idle panel forgets its input and report, so the next opening starts clean
   * (U3 #14). Closing it while a build runs keeps everything: reopening shows the build
   * still running, then its report, and no second build can start (U8 review #2). */
  function close() {
    if (busy) closedMidBuild.current = true;
    else {
      if (fixedId == null) setWorldId("");
      setName("");
      setDescription("");
      setMemo("");
      setFiles({});
      setReport(null);
      setError(null);
    }
    onClose();
  }

  return (
    // V2 (requirements review R-01): the shared Dialog; Esc or a click outside is [close]
    <Dialog open title={t("build.title")} size="lg" testId="build-panel" onOpenChange={(o) => !o && close()}>
      <div className="flex flex-col gap-3">
        {fixedId == null && (
          <Field label={t("build.worldId")} data-testid="build-world-id" value={worldId}
            onChange={(e) => setWorldId(e.target.value)} />
        )}
        <Field label={t("build.name")} value={name} onChange={(e) => setName(e.target.value)} />
        <Field label={t("build.description")} value={description}
          onChange={(e) => setDescription(e.target.value)} />
        <label className="inline-flex flex-col gap-0.5 text-sm">
          <span className="text-muted">{t("build.memoText")}</span>
          <textarea data-testid="build-memo" rows={3} value={memo} onChange={(e) => setMemo(e.target.value)}
            className="border border-line-strong rounded-md bg-surface px-2 py-1 text-sm" />
        </label>
        {FIELDS.map((f) => (
          <FileInput key={f.name} multiple accept={f.accept} data-testid={`build-${f.name}`}
            label={<>
              {t(f.label)}
              {f.name === "concept_arts" && <> <InProgressBadge note={t("build.conceptArtsWip")} /></>}
            </>}
            chosen={(files[f.name] ?? []).map((x) => x.name)}
            onFiles={(picked) => setFiles({ ...files, [f.name]: picked })} />
        ))}
        {busy && <div className="text-muted text-sm" data-testid="build-working">{t("build.working")}</div>}
        {error && <div className="text-danger text-sm" data-testid="build-error">{error}</div>}
        {report && <BuildReportPanel report={report} />}
        <div className="flex items-center justify-end gap-2">
          {noLlm && <span className="text-xs text-muted" data-testid="llm-required">{t("llm.required")}</span>}
          <Button size="sm" onClick={close}>{t("action.close")}</Button>
          <Button size="sm" variant="primary" data-testid="build-submit"
            disabled={busy || !id || !hasInput || noLlm} title={noLlm ? t("llm.required") : undefined}
            onClick={() => (exists ? replaceQ.askReplace() : send(false, false))}>
            {t("build.submit")}
          </Button>
        </div>
      </div>
      <ConfirmDialog open={replaceQ.open} tone="danger" title={t("build.title")} confirmLabel={t("action.confirm")}
        onCancel={replaceQ.cancel}
        onConfirm={() => void send(true, replaceQ.answer())}>
        <span data-testid="build-confirm">
          {replaceQ.ask === "replace" ? t("build.replaceConfirm")
            : t("build.closeSessions", { n: replaceQ.sessions })}
        </span>
      </ConfirmDialog>
    </Dialog>
  );
}
