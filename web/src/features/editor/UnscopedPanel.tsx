import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { api } from "../../api";
import { describeError, type DescribedError } from "../../errors";
import { useResource } from "../../hooks";
import { t, useRequestLang } from "../../i18n";
import type { Knowledge, Region } from "../../types";
import { Button, Card, InlineError, LocalizedText, Panel, Select, StatusView } from "../../ui";
import { ConfirmDelete } from "./ConfirmDelete";
import { regionOptions } from "./connections";
import type { Panel as PanelName } from "./useEditorWorld";

/** Knowledge known nowhere (BR-U3-14): what the build could not place and what region
 * deletes left behind. Assign a region (one DIRECT scope) or delete. The region picked for
 * each item is held by the page (`picks`), so it outlives a hidden tab (V8 UX-24); the list
 * is read again through `registerReload` after a replace or the build report's link (R-02). */
export function UnscopedPanel({
  worldId,
  regions,
  picks,
  onPicks,
  onChanged,
  registerReload,
}: {
  worldId: string;
  regions: Region[];
  picks: Record<string, string>;
  onPicks: Dispatch<SetStateAction<Record<string, string>>>;
  onChanged(): void;
  registerReload?(panel: PanelName, fn: () => void): () => void;
}) {
  const lang = useRequestLang();
  const read = useResource(["editor-unscoped", worldId, lang], () => api.listUnscoped(worldId)); // S31: newest only
  useEffect(() => registerReload?.("unscoped", read.reload), [registerReload, read.reload]);
  const [doomed, setDoomed] = useState<Knowledge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<DescribedError | null>(null);

  async function run(fn: () => Promise<unknown>, done?: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
      // from the picks as they are now, not as they were at the press: a region picked for
      // another item meanwhile, or a replace's clearing, stays (code review 01 #26)
      if (done) onPicks(({ [done]: _gone, ...rest }) => rest);
      read.reload();
      onChanged();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(false);
    }
  }

  const items = read.data;
  return (
    <Panel title={t("editor.unscoped.title")} data-testid="unscoped-panel">
      {error && <InlineError error={error} />}
      {!items ? (
        <StatusView state={read.state === "error" ? "error" : "loading"} error={read.error} onRetry={read.reload} />
      ) : items.length === 0 ? (
        <div className="text-xs text-muted">{t("editor.unscoped.none")}</div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {items.map((k) => (
            <Card key={k.id} data-testid={`unscoped-${k.id}`} className="flex flex-col gap-1 text-sm">
              <strong className="break-words">{k.title_ko || k.title}</strong>
              <LocalizedText ko={k.statement_ko} original={k.statement} />
              <div className="flex flex-wrap items-center gap-1">
                <Select label={t("editor.unscoped.pick")} hideLabel value={picks[k.id] ?? ""}
                  data-testid={`unscoped-region-${k.id}`}
                  options={[{ value: "", label: t("editor.unscoped.pick") }, ...regionOptions(regions)]}
                  onChange={(v) => onPicks({ ...picks, [k.id]: v })} />
                <Button size="sm" variant="primary" data-testid={`unscoped-assign-${k.id}`}
                  disabled={busy || !picks[k.id]}
                  onClick={() => run(() => api.setScopes(worldId, k.id, [picks[k.id]]), k.id)}>
                  {t("editor.unscoped.assign")}
                </Button>
                <Button size="sm" variant="danger" disabled={busy} data-testid={`unscoped-delete-${k.id}`}
                  aria-label={t("action.deleteKnowledge", { name: k.title_ko || k.title })}
                  onClick={() => setDoomed(k)}>✕</Button>
              </div>
            </Card>
          ))}
        </div>
      )}
      <ConfirmDelete open={doomed != null} busy={busy}
        message={doomed ? t("delete.knowledge", { name: doomed.title_ko || doomed.title }) : undefined}
        onCancel={() => setDoomed(null)}
        onConfirm={() => {
          const k = doomed;
          setDoomed(null);
          if (k) void run(() => api.deleteKnowledge(worldId, k.id), k.id);
        }} />
    </Panel>
  );
}
