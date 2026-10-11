import { useEffect, useState } from "react";
import { api } from "../../api";
import { describeError, type DescribedError } from "../../errors";
import { enumLabel, numberWithMeaning } from "../../format";
import { useResource } from "../../hooks";
import { t } from "../../i18n";
import type { ConnectionKey, NameRef, Region, WikiPrior } from "../../types";
import { Badge, Button, Card, InlineError, Panel, StatusView } from "../../ui";
import { ConfirmDelete } from "./ConfirmDelete";
import type { Panel as PanelName } from "./useEditorWorld";

/** The world's common-sense grounds (US-2.8, BR-U3-31): each prior's condition → effect,
 * domains and confidence in words, what cites it, and the cited ids the world does not hold
 * ("unsaved grounds"). Deleting a prior is confirmed; what cited it becomes broken. Read again
 * through `registerReload` after a replace (V8 R-02). */
export function WikiPanel({
  worldId,
  regions,
  onChanged,
  registerReload,
}: {
  worldId: string;
  regions: Region[];
  onChanged?(): void; // a deleted prior: the world is read again too (BLM § 5)
  registerReload?(panel: PanelName, fn: () => void): () => void;
}) {
  const read = useResource(["editor-priors", worldId], () => api.priorRefs(worldId));
  useEffect(() => registerReload?.("wiki", read.reload), [registerReload, read.reload]);
  const [open, setOpen] = useState<string | null>(null);
  const [doomed, setDoomed] = useState<WikiPrior | null>(null);
  const [error, setError] = useState<DescribedError | null>(null);
  const [busy, setBusy] = useState(false);

  const name = (id: string) => regions.find((r) => r.id === id)?.name ?? id;
  const conn = (k: ConnectionKey) => `${name(k.a_region_id)}–${name(k.b_region_id)} ${enumLabel("connectionKind", k.kind)}`;
  const cites = (connections: ConnectionKey[], knowledge: NameRef[]) => (
    <ul className="list-disc pl-4 text-xs">
      {connections.map((k) => <li key={`${k.a_region_id}|${k.b_region_id}|${k.kind}`}>{conn(k)}</li>)}
      {knowledge.map((k) => <li key={k.id}>{k.name}</li>)}
    </ul>
  );
  const refs = read.data;
  return (
    <Panel title={t("wiki.title")} data-testid="wiki-panel">
      {error && <InlineError error={error} />}
      {!refs ? (
        <StatusView state={read.state === "error" ? "error" : "loading"} error={read.error} onRetry={read.reload} />
      ) : (
        <>
          {refs.usages.length === 0 && <div className="text-xs text-muted">{t("wiki.none")}</div>}
          <div className="flex flex-col gap-1.5">
            {refs.usages.map(({ prior, connections, knowledge }) => (
              <Card key={prior.id} data-testid={`prior-${prior.id}`} className="flex flex-col gap-1 text-sm">
                <div className="break-words">
                  {prior.condition} → <strong>{prior.effect}</strong>
                </div>
                <div className="flex flex-wrap items-center gap-1 text-xs">
                  {prior.domains.map((d) => <Badge key={d}>{enumLabel("wikiDomain", d)}</Badge>)}
                  <span className="text-muted">
                    {t("wiki.confidence")} {numberWithMeaning("confidence", prior.confidence)}
                  </span>
                  <button type="button" className="underline" data-testid={`prior-refs-${prior.id}`}
                    aria-expanded={open === prior.id}
                    onClick={() => setOpen(open === prior.id ? null : prior.id)}>
                    {t("wiki.refs", { n: connections.length + knowledge.length })}
                  </button>
                  <Button size="sm" variant="danger" disabled={busy} onClick={() => setDoomed(prior)}>
                    {t("wiki.delete")}
                  </Button>
                </div>
                {open === prior.id && cites(connections, knowledge)}
              </Card>
            ))}
          </div>
          {refs.broken.length > 0 && (
            <div className="mt-2" data-testid="wiki-broken">
              <h3 className="font-heading text-danger">{t("wiki.broken")}</h3>
              {refs.broken.map((b) => (
                <div key={b.ref_id} className="text-xs">
                  <code className="break-all">{b.ref_id}</code>
                  {cites(b.connections, b.knowledge)}
                </div>
              ))}
            </div>
          )}
        </>
      )}
      <ConfirmDelete open={doomed != null} busy={busy}
        message={doomed ? t("delete.prior", { name: doomed.effect }) : undefined}
        onCancel={() => setDoomed(null)}
        onConfirm={async () => {
          const p = doomed;
          setDoomed(null);
          if (!p) return;
          setBusy(true);
          setError(null);
          try {
            await api.deletePrior(worldId, p.id);
            read.reload();
            onChanged?.();
          } catch (e) {
            setError(describeError(e));
          } finally {
            setBusy(false);
          }
        }} />
    </Panel>
  );
}
