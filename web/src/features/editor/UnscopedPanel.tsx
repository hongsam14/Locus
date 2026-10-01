import { useEffect, useState } from "react";
import { api } from "../../api";
import { t, useRequestLang } from "../../i18n";
import type { Knowledge, Region } from "../../types";
import { Button, Card, LocalizedText, Panel } from "../../ui";
import { ConfirmDelete } from "./ConfirmDelete";

/** Knowledge known nowhere (BR-U3-14): what the build could not place and what region
 * deletes left behind. Assign a region (one DIRECT scope) or delete. */
export function UnscopedPanel({
  worldId,
  regions,
  reloadKey = 0,
  onChanged,
}: {
  worldId: string;
  regions: Region[];
  reloadKey?: number;
  onChanged: () => void;
}) {
  const [items, setItems] = useState<Knowledge[] | null>(null);
  const [pick, setPick] = useState<Record<string, string>>({});
  const [doomed, setDoomed] = useState<Knowledge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lang = useRequestLang();

  async function load() {
    try {
      setItems(await api.listUnscoped(worldId));
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [worldId, reloadKey, lang]);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
      onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title={t("editor.unscoped.title")} data-testid="unscoped-panel" className="min-w-80">
      {error && <div className="text-danger text-sm">{error}</div>}
      {items?.length === 0 && (
        <div className="text-xs text-ink-soft">{t("editor.unscoped.none")}</div>
      )}
      <div className="flex flex-col gap-1.5">
        {items?.map((k) => (
          <Card key={k.id} data-testid={`unscoped-${k.id}`} className="text-sm flex flex-col gap-1">
            <strong>{k.title_ko || k.title}</strong>
            <LocalizedText ko={k.statement_ko} original={k.statement} />
            <div className="flex gap-1">
              <select value={pick[k.id] ?? ""} data-testid={`unscoped-region-${k.id}`}
                aria-label={t("editor.unscoped.pick")}
                onChange={(e) => setPick({ ...pick, [k.id]: e.target.value })}
                className="sketch-border bg-paper-card px-1 text-xs">
                <option value="">{t("editor.unscoped.pick")}</option>
                {regions.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
              <Button size="sm" variant="primary" data-testid={`unscoped-assign-${k.id}`}
                disabled={busy || !pick[k.id]}
                onClick={() => run(() => api.setScopes(worldId, k.id, [pick[k.id]]))}>
                {t("editor.unscoped.assign")}
              </Button>
              <Button size="sm" variant="danger" disabled={busy} onClick={() => setDoomed(k)}>✕</Button>
            </div>
          </Card>
        ))}
      </div>
      <ConfirmDelete open={doomed != null} busy={busy}
        message={doomed ? t("delete.knowledge", { name: doomed.title }) : undefined}
        onCancel={() => setDoomed(null)}
        onConfirm={() => {
          const k = doomed;
          setDoomed(null);
          if (k) run(() => api.deleteKnowledge(worldId, k.id));
        }} />
    </Panel>
  );
}
