import { useState } from "react";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Field } from "../../ui";

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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4"
      role="dialog"
      aria-modal="true"
      data-testid="new-session-form"
    >
      <form
        className="sketch-border sketch-shadow bg-paper-card p-4 max-w-sm w-full flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid && !busy) onSubmit(name.trim(), regionId);
        }}
      >
        <h2 className="font-display text-lg">{t("session.playTitle")}</h2>
        <Field
          label={t("session.name")}
          data-testid="new-session-name"
          value={name}
          maxLength={40}
          onChange={(e) => setName(e.target.value)}
        />
        <label className="inline-flex flex-col gap-0.5 text-sm">
          <span className="text-ink-soft">{t("session.startRegion")}</span>
          <select
            data-testid="new-session-region"
            value={regionId}
            onChange={(e) => setRegionId(e.target.value)}
            className="sketch-border bg-paper-card px-2 py-1 text-sm"
          >
            <option value="">{t("session.pickRegion")}</option>
            {regions.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} · {r.level}
              </option>
            ))}
          </select>
        </label>
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
    </div>
  );
}
