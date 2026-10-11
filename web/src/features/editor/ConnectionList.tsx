import { useState } from "react";
import { numberWithMeaning } from "../../format";
import { t } from "../../i18n";
import type { ConnectionKind, ConnectionView } from "../../types";
import { Button, Card, CommitRange, Select } from "../../ui";
import { kindOptions } from "./connections";

/** The region's connections (US-2.2 둘째, US-2.8): the other end, kind, weight and the
 * grounds — the prior's effect, or "unsaved grounds" when the world lacks it. Changing
 * the kind is one call that keeps weight, rationale and prior (BR-U3-11). */
export function ConnectionList({
  connections,
  busy,
  onChangeKind,
  onChangeWeight,
  onDelete,
  onPickRegion,
}: {
  connections: ConnectionView[];
  busy: boolean;
  onPickRegion?: (regionId: string) => void; // the other end's name picks that region (§ 4.4)
  onChangeKind: (c: ConnectionView, kind: ConnectionKind) => void;
  onChangeWeight: (c: ConnectionView, weight: number) => void;
  onDelete: (c: ConnectionView) => void;
}) {
  if (connections.length === 0) {
    return <div className="text-xs text-muted">{t("editor.connection.none")}</div>;
  }
  return (
    <div className="flex flex-col gap-1.5" data-testid="connection-list">
      {connections.map((c) => {
        const id = `${c.key.a_region_id}|${c.key.b_region_id}|${c.key.kind}`;
        return (
          <Card key={id} data-testid={`connection-${id}`} className="flex flex-col gap-1 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <strong className="min-w-0 flex-1 break-words">
                {onPickRegion ? (
                  <button type="button" className="text-left underline decoration-dotted"
                    data-testid={`connection-other-${id}`} onClick={() => onPickRegion(c.other_region_id)}>
                    {c.other_region_name}
                  </button>
                ) : c.other_region_name}
              </strong>
              <Select label={t("editor.connection.kind")} hideLabel value={c.key.kind} disabled={busy}
                data-testid={`connection-kind-${id}`} options={kindOptions()}
                onChange={(v) => onChangeKind(c, v as ConnectionKind)} />
              <Button size="sm" variant="danger" disabled={busy} data-testid={`connection-delete-${id}`}
                aria-label={t("action.deleteConnection", { name: c.other_region_name })}
                onClick={() => onDelete(c)}>
                ✕
              </Button>
            </div>
            <Weight id={id} weight={c.weight} busy={busy} onCommit={(w) => onChangeWeight(c, w)} />
            {c.rationale && <div className="text-xs text-muted">{c.rationale}</div>}
            {c.prior && (
              <div className={`text-xs ${c.prior.broken ? "text-danger" : "text-muted"}`}
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

/** One weight control (UX-20, BR-V8-13): a slider whose label is the number and its meaning;
 * moving it writes nothing, letting go saves once (CommitRange, the GM's slider). */
function Weight({ id, weight, busy, onCommit }: {
  id: string;
  weight: number;
  busy: boolean;
  onCommit(w: number): void;
}) {
  const [draft, setDraft] = useState(weight);
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-muted" data-testid={`connection-weight-label-${id}`}>
        {t("editor.connection.weight")} · {numberWithMeaning("weight", draft)}
      </span>
      <CommitRange min={0} max={1} step={0.05} value={weight} disabled={busy} data-testid={`connection-weight-${id}`}
        className="w-full" onDraft={setDraft} onCommit={onCommit} />
    </label>
  );
}
