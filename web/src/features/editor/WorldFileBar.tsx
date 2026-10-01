import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { useReplaceConfirm } from "../../api/http";
import { SessionBar } from "../../SessionBar";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Modal } from "../../ui";

/** The world's bar (US-6.2·6.3, BR-U3-15/36): its name, save as a World File, load one
 * (replacing the world after a yes, closing open sessions after a second), build from
 * sources, and the sessions band: the open ones, or a session start when there are none
 * (U3 review S01 — the editor's way into play). */
export function WorldFileBar({
  worldId,
  name,
  openSessions,
  regions,
  onLoaded,
  onBuild,
}: {
  worldId: string;
  name: string;
  openSessions: number | null;
  regions: Region[];
  onLoaded: () => void;
  onBuild: () => void;
}) {
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<object | null>(null);
  const replace = useReplaceConfirm(); // "replace?" then "close N sessions?" (U3 C8)
  const [showSessions, setShowSessions] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
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
      setError(String(e));
    }
  }

  async function pick(f: File | undefined) {
    if (!f) return;
    setError(null);
    try {
      setFile(JSON.parse(await readText(f)));
      replace.askReplace();
    } catch {
      setError(t("file.load") + ": JSON?");
    }
  }

  async function load(confirm: boolean) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await api.importWorldFile(worldId, file, { replace: true, confirm });
      setFile(null);
      onLoaded();
    } catch (e) {
      if (!replace.sessionsAsked(e, confirm)) setError(String(e)); // 422: the server's words
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-ink px-3 py-1.5" data-testid="world-file-bar">
      <strong className="font-display text-lg" data-testid="world-name">{name}</strong>
      <code className="text-xs text-ink-soft">{worldId}</code>
      <Button size="sm" data-testid="file-save" onClick={save}>{t("file.save")}</Button>
      <Button size="sm" data-testid="file-load" disabled={busy} onClick={() => input.current?.click()}>
        {t("file.load")}
      </Button>
      <input ref={input} type="file" accept=".json,application/json" className="hidden"
        data-testid="file-input" onChange={(e) => {
          void pick(e.target.files?.[0]);
          e.target.value = ""; // the same file again is a new pick (U3 review S24)
        }} />
      <Button size="sm" data-testid="file-build" onClick={onBuild}>{t("file.build")}</Button>
      {(openSessions ?? 0) > 0 ? (
        <button type="button" className="text-xs underline text-danger" data-testid="open-sessions-band"
          onClick={() => setShowSessions((v) => !v)}>
          {t("file.openSessions", { n: openSessions ?? 0 })}
        </button>
      ) : openSessions === 0 && (
        <button type="button" className="text-xs underline" data-testid="start-session-band"
          onClick={() => setShowSessions((v) => !v)}>
          {t("home.startSession")}
        </button>
      )}
      {error && <span className="text-danger text-sm" data-testid="file-error">{error}</span>}
      {showSessions && (
        <div className="w-full">
          <SessionBar worldId={worldId} sessionId={null} variant="picker" regions={regions}
            onSelect={(s) => s && navigate(`/gm/${encodeURIComponent(s.id)}`)}
            onPlay={(out) => navigate(`/play/${encodeURIComponent(out.session.id)}`)} />
        </div>
      )}
      <Modal open={replace.open} confirmTone="danger" busy={busy} title={t("file.load")}
        onCancel={() => {
          replace.cancel();
          setFile(null);
        }}
        onConfirm={() => void load(replace.answer())}>
        <span data-testid="file-confirm">
          {replace.ask === "replace" ? t("file.replaceConfirm")
            : t("file.closeSessionsConfirm", { n: replace.sessions })}
        </span>
      </Modal>
    </div>
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
