import { useEffect, useState } from "react";
import type { DescribedError } from "../../errors";
import { enumLabel } from "../../format";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Dialog, Field, InlineError, Select } from "../../ui";
import { english, type NameOf } from "./names";

/** Player-mode session start (US-3.1): a name and a start region, both required. The form
 * stays mounted while closed: when it opens for another world the region choice empties and
 * the name stays (RE-F03, BR-V4-08). `worldId` is optional — a caller without it is as before.
 * V4 code review 01: regions by the world's name map and the level in words (#8, BR-V4-10);
 * a failed start is said inside the form, where the person is looking (#22). */
export function NewSessionForm({
  open,
  worldId,
  regions,
  nameOf = english,
  error = null,
  busy = false,
  onSubmit,
  onCancel,
}: {
  open: boolean;
  worldId?: string;
  regions: Region[];
  nameOf?: NameOf;
  error?: DescribedError | null;
  busy?: boolean;
  onSubmit: (name: string, startRegionId: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [regionId, setRegionId] = useState("");
  useEffect(() => setRegionId(""), [worldId]);
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
            ...regions.map((r) => ({
              value: r.id,
              label: `${nameOf("regions", r.id, "name", r.name)} · ${enumLabel("regionLevel", r.level)}`,
            })),
          ]}
          onChange={setRegionId}
        />
        {error && (
          <div data-testid="new-session-error">
            <InlineError error={error} />
          </div>
        )}
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
