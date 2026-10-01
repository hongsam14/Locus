import { useState } from "react";
import { api } from "../../api";
import { needsLlm, statusOf } from "../../api/http";
import { llmOff, useCapabilities } from "../../capabilities";
import { t } from "../../i18n";
import type { BuildReport } from "../../types";
import { Button, Field, InProgressBadge, Modal } from "../../ui";
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
  const [ask, setAsk] = useState<"replace" | { sessions: number } | null>(null);
  const noLlm = llmOff(useCapabilities()); // U8 (BR-U8-25): building calls the LLM
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<BuildReport | null>(null);
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
      const m = /"open_sessions":\s*(\d+)/.exec(String(e));
      if (statusOf(e) === 409 && m && !confirm) setAsk({ sessions: Number(m[1]) });
      else if (statusOf(e) === 409 && !replace && !m) setAsk("replace"); // the id exists
      else setError(needsLlm(e) ? t("llm.required") : String(e)); // BR-U8-27
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/30 p-4" role="dialog"
      aria-modal="true" data-testid="build-panel">
      <div className="sketch-border sketch-shadow bg-paper-card p-4 max-w-lg w-full flex flex-col gap-2">
        <h2 className="font-display text-lg">{t("build.title")}</h2>
        {fixedId == null && (
          <Field label={t("build.worldId")} data-testid="build-world-id" value={worldId}
            onChange={(e) => setWorldId(e.target.value)} />
        )}
        <Field label={t("build.name")} value={name} onChange={(e) => setName(e.target.value)} />
        <Field label={t("build.description")} value={description}
          onChange={(e) => setDescription(e.target.value)} />
        <label className="inline-flex flex-col gap-0.5 text-sm">
          <span className="text-ink-soft">{t("build.memoText")}</span>
          <textarea data-testid="build-memo" rows={3} value={memo} onChange={(e) => setMemo(e.target.value)}
            className="sketch-border bg-paper-card px-2 py-1 text-sm" />
        </label>
        {FIELDS.map((f) => (
          <label key={f.name} className="inline-flex flex-col gap-0.5 text-sm">
            <span className="text-ink-soft">
              {t(f.label)}
              {f.name === "concept_arts" && <> <InProgressBadge note={t("build.conceptArtsWip")} /></>}
            </span>
            <input type="file" multiple accept={f.accept} data-testid={`build-${f.name}`}
              onChange={(e) => setFiles({ ...files, [f.name]: Array.from(e.target.files ?? []) })} />
          </label>
        ))}
        {busy && <div className="text-ink-soft text-sm" data-testid="build-working">{t("build.working")}</div>}
        {error && <div className="text-danger text-sm" data-testid="build-error">{error}</div>}
        {report && <BuildReportPanel report={report} />}
        <div className="flex items-center justify-end gap-2">
          {noLlm && <span className="text-xs text-ink-soft" data-testid="llm-required">{t("llm.required")}</span>}
          <Button size="sm" onClick={onClose}>{t("action.close")}</Button>
          <Button size="sm" variant="primary" data-testid="build-submit"
            disabled={busy || !id || !hasInput || noLlm} title={noLlm ? t("llm.required") : undefined}
            onClick={() => (exists ? setAsk("replace") : send(false, false))}>
            {t("build.submit")}
          </Button>
        </div>
      </div>
      <Modal open={ask != null} confirmTone="danger" title={t("build.title")}
        onCancel={() => setAsk(null)}
        onConfirm={() => {
          const a = ask;
          setAsk(null);
          send(true, a !== "replace"); // the second question is the session one
        }}>
        <span data-testid="build-confirm">
          {ask === "replace" ? t("build.replaceConfirm")
            : t("build.closeSessions", { n: typeof ask === "object" && ask ? ask.sessions : 0 })}
        </span>
      </Modal>
    </div>
  );
}
