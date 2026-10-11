import { useState } from "react";
import { enumLabel, numberWithMeaning } from "../../format";
import { t } from "../../i18n";
import type { ConnectionEdge, ConnectionKind } from "../../types";
import { Button, CommitRange, Dialog, Select } from "../../ui";
import { DEFAULT_WEIGHT, kindOptions } from "./connections";

/** The connect tool's form (U3 #15; V8 BLM § 4, BR-V8-13): a kind in words and one weight
 * slider whose label is the number and its meaning. The slider only sets the value — [save]
 * writes. It starts at the stored weight of this pair and kind, or 0.6; another kind starts
 * from that kind's stored weight. On a pair that already has the kind the form edits it. */
export function NewConnectionDialog({
  title,
  busy,
  existing,
  onSubmit,
  onCancel,
}: {
  title: string;
  busy: boolean;
  /** The stored connection of the pair for a kind: the form then edits it. */
  existing(kind: ConnectionKind): ConnectionEdge | undefined;
  onSubmit(kind: ConnectionKind, weight: number): void;
  onCancel(): void;
}) {
  const [kind, setKind] = useState<ConnectionKind>("route");
  const [weight, setWeight] = useState(existing("route")?.weight ?? DEFAULT_WEIGHT);
  const old = existing(kind);
  return (
    <Dialog open size="sm" testId="connection-form" onOpenChange={(open) => !open && onCancel()}
      title={`${t(old ? "editor.connection.edit" : "editor.connection.add")}: ${title}`}>
      <div className="flex flex-col gap-3">
        {old && (
          <p className="text-xs text-muted" data-testid="connection-exists">
            {t("editor.connection.exists", { kind: enumLabel("connectionKind", kind), weight: numberWithMeaning("weight", old.weight) })}
          </p>
        )}
        <Select label={t("editor.connection.kind")} data-testid="connection-kind" value={kind} options={kindOptions()}
          onChange={(next) => {
            setKind(next as ConnectionKind);
            setWeight(existing(next as ConnectionKind)?.weight ?? DEFAULT_WEIGHT); // start from what is saved
          }} />
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-bold" data-testid="connection-weight-label">
            {t("editor.connection.weight")} · {numberWithMeaning("weight", weight)}
          </span>
          <CommitRange min={0} max={1} step={0.05} value={weight} data-testid="connection-weight" className="w-full"
            onDraft={setWeight} onCommit={setWeight} />
        </label>
        <div className="flex justify-end gap-2">
          <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
          <Button size="sm" variant="primary" data-testid="connection-save" disabled={busy} onClick={() => onSubmit(kind, weight)}>
            {t("editor.connection.save")}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
