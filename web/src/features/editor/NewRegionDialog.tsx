import { useState } from "react";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Dialog, Field, Select, Textarea } from "../../ui";
import { levelOptions, type NewRegion, regionOptions } from "./connections";

/** The add tool's new-region form (U3 review C8; V8 frontend-components § 4.2): name, level
 * in words, a parent picked from the regions grouped by level, a description box. Esc or a
 * press outside cancels. */
export function NewRegionDialog({
  regions,
  busy,
  onSubmit,
  onCancel,
}: {
  regions: Region[];
  busy: boolean;
  onSubmit(r: Omit<NewRegion, "position">): void;
  onCancel(): void;
}) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState("town");
  const [parent, setParent] = useState("");
  const [desc, setDesc] = useState("");
  return (
    <Dialog open title={t("editor.region.add")} size="sm" testId="new-region-form" onOpenChange={(open) => !open && onCancel()}>
      <div className="flex flex-col gap-3">
        <Field label={t("editor.region.name")} data-testid="new-region-name" value={name} onChange={(e) => setName(e.target.value)} />
        <Select label={t("editor.region.level")} data-testid="new-region-level" value={level} options={levelOptions()} onChange={setLevel} />
        <Select label={t("editor.region.parent")} data-testid="new-region-parent" value={parent}
          options={[{ value: "", label: t("editor.region.noParent") }, ...regionOptions(regions)]} onChange={setParent} />
        <Textarea label={t("editor.region.description")} data-testid="new-region-description" value={desc}
          onChange={(e) => setDesc(e.target.value)} rows={3} />
        <div className="flex justify-end gap-2">
          <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
          <Button size="sm" variant="primary" data-testid="new-region-save" disabled={busy || !name.trim()}
            onClick={() => onSubmit({ name: name.trim(), level, parent_id: parent || null, description: desc.trim() || null })}>
            {t("editor.region.save")}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
