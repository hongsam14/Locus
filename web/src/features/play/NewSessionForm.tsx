import { useState } from "react";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Dialog, Field, Select } from "../../ui";

/** Player-mode session start (US-3.1): a name and a start region, both required. */
export function NewSessionForm({
  open,
  regions,
  busy = false,
  onSubmit,
  onCancel,
}: {
  open: boolean;
  regions: Region[];
  busy?: boolean;
  onSubmit: (name: string, startRegionId: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [regionId, setRegionId] = useState("");
  if (!open) return null;
  const valid = name.trim().length >= 1 && name.trim().length <= 40 && regionId !== "";
  return (
    <Dialog open title={t("session.playTitle")} size="sm" testId="new-session-form"
      onOpenChange={(o) => !o && onCancel()}>
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid && !busy) onSubmit(name.trim(), regionId);
        }}
      >
        <Field
          label={t("session.name")}
          data-testid="new-session-name"
          value={name}
          maxLength={40}
          onChange={(e) => setName(e.target.value)}
        />
        <Select
          label={t("session.startRegion")}
          data-testid="new-session-region"
          value={regionId}
          options={[
            { value: "", label: t("session.pickRegion") },
            ...regions.map((r) => ({ value: r.id, label: `${r.name} · ${r.level}` })),
          ]}
          onChange={setRegionId}
        />
        <div className="flex justify-end gap-2">
          <Button size="sm" type="button" data-testid="new-session-cancel" onClick={onCancel}>
            {t("action.cancel")}
          </Button>
          <Button
            size="sm"
            type="submit"
            variant="primary"
            data-testid="new-session-submit"
            disabled={!valid || busy}
          >
            {t("session.play")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
