import { t } from "../../i18n";
import type { ConnectionKind, ConnectionView } from "../../types";
import { Button, Card } from "../../ui";
import { KINDS } from "./MapCanvas";

/** The region's connections (US-2.2 둘째, US-2.8): the other end, kind, weight and the
 * grounds — the prior's effect, or "unsaved grounds" when the world lacks it. Changing
 * the kind is one call that keeps weight, rationale and prior (BR-U3-11). */
export function ConnectionList({
  connections,
  busy,
  onChangeKind,
  onChangeWeight,
  onDelete,
}: {
  connections: ConnectionView[];
  busy: boolean;
  onChangeKind: (c: ConnectionView, kind: ConnectionKind) => void;
  onChangeWeight: (c: ConnectionView, weight: number) => void;
  onDelete: (c: ConnectionView) => void;
}) {
  if (connections.length === 0) {
    return <div className="text-xs text-ink-soft">{t("editor.connection.none")}</div>;
  }
  return (
    <div className="flex flex-col gap-1.5" data-testid="connection-list">
      {connections.map((c) => {
        const id = `${c.key.a_region_id}|${c.key.b_region_id}|${c.key.kind}`;
        return (
          <Card key={id} data-testid={`connection-${id}`} className="flex flex-col gap-1 text-sm">
            <div className="flex items-center gap-2">
              <strong className="flex-1">{c.other_region_name}</strong>
              <select value={c.key.kind} disabled={busy} data-testid={`connection-kind-${id}`}
                aria-label={t("editor.connection.kind")}
                onChange={(e) => onChangeKind(c, e.target.value as ConnectionKind)}
                className="sketch-border bg-paper-card px-1 text-xs">
                {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
              <input type="number" min={0} max={1} step={0.05} defaultValue={c.weight}
                aria-label={t("editor.connection.weight")} disabled={busy}
                data-testid={`connection-weight-${id}`} className="sketch-border w-16 px-1 text-xs"
                onBlur={(e) => {
                  const w = Number(e.target.value);
                  if (w !== c.weight && w >= 0 && w <= 1) onChangeWeight(c, w);
                }} />
              <Button size="sm" variant="danger" disabled={busy} data-testid={`connection-delete-${id}`}
                onClick={() => onDelete(c)}>
                ✕
              </Button>
            </div>
            {c.rationale && <div className="text-xs text-ink-soft">{c.rationale}</div>}
            {c.prior && (
              <div className={`text-xs ${c.prior.broken ? "text-danger" : "text-ink-soft"}`}
                data-testid={`connection-prior-${id}`}>
                {c.prior.broken
                  ? t("editor.connection.brokenPrior", { id: c.prior.prior_id })
                  : t("editor.connection.prior", { effect: c.prior.effect ?? "" })}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
