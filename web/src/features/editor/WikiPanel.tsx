import { useEffect, useState } from "react";
import { api } from "../../api";
import { t } from "../../i18n";
import type { ConnectionKey, NameRef, PriorRefsOut, Region, WikiPrior } from "../../types";
import { Badge, Button, Card, Panel } from "../../ui";
import { ConfirmDelete } from "./ConfirmDelete";

/** The world's common-sense grounds (US-2.8, BR-U3-31): each prior's condition → effect,
 * domains and confidence, what cites it, and the cited ids the world does not hold
 * ("unsaved grounds"). Deleting a prior is confirmed; what cited it becomes broken. */
export function WikiPanel({
  worldId,
  regions,
  reloadKey = 0,
}: {
  worldId: string;
  regions: Region[];
  reloadKey?: number;
}) {
  const [refs, setRefs] = useState<PriorRefsOut | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [doomed, setDoomed] = useState<WikiPrior | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setRefs(await api.priorRefs(worldId));
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [worldId, reloadKey]);

  const name = (id: string) => regions.find((r) => r.id === id)?.name ?? id;
  const conn = (k: ConnectionKey) => `${name(k.a_region_id)}–${name(k.b_region_id)} ${k.kind}`;
  const cites = (connections: ConnectionKey[], knowledge: NameRef[]) => (
    <ul className="list-disc pl-4 text-xs">
      {connections.map((k) => <li key={`${k.a_region_id}|${k.b_region_id}|${k.kind}`}>{conn(k)}</li>)}
      {knowledge.map((k) => <li key={k.id}>{k.name}</li>)}
    </ul>
  );

  return (
    <Panel title={t("wiki.title")} data-testid="wiki-panel" className="min-w-80">
      {error && <div className="text-danger text-sm">{error}</div>}
      {refs?.usages.length === 0 && <div className="text-xs text-muted">{t("wiki.none")}</div>}
      <div className="flex flex-col gap-1.5">
        {refs?.usages.map(({ prior, connections, knowledge }) => (
          <Card key={prior.id} data-testid={`prior-${prior.id}`} className="text-sm flex flex-col gap-1">
            <div>
              {prior.condition} → <strong>{prior.effect}</strong>
            </div>
            <div className="flex flex-wrap items-center gap-1 text-xs">
              {prior.domains.map((d) => <Badge key={d}>{d}</Badge>)}
              <span className="text-muted">
                {t("wiki.confidence")} {prior.confidence.toFixed(2)}
              </span>
              <button type="button" className="underline" data-testid={`prior-refs-${prior.id}`}
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
      {(refs?.broken.length ?? 0) > 0 && (
        <div className="mt-2" data-testid="wiki-broken">
          <h3 className="font-heading text-danger">{t("wiki.broken")}</h3>
          {refs?.broken.map((b) => (
            <div key={b.ref_id} className="text-xs">
              <code>{b.ref_id}</code>
              {cites(b.connections, b.knowledge)}
            </div>
          ))}
        </div>
      )}
      <ConfirmDelete open={doomed != null} busy={busy}
        message={doomed ? t("delete.prior", { name: doomed.effect }) : undefined}
        onCancel={() => setDoomed(null)}
        onConfirm={async () => {
          const p = doomed;
          setDoomed(null);
          if (!p) return;
          setBusy(true);
          try {
            await api.deletePrior(worldId, p.id);
            await load();
          } catch (e) {
            setError(String(e));
          } finally {
            setBusy(false);
          }
        }} />
    </Panel>
  );
}
