import { useState } from "react";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Field } from "../../ui";
import { LEVELS } from "./MapCanvas";

/** Regions under ``id`` (its children, theirs, …): a parent must not be one (BR-U3-7). */
export function descendantsOf(id: string, regions: Region[]): Set<string> {
  const out = new Set<string>();
  const stack = [id];
  while (stack.length) {
    const cur = stack.pop() as string;
    for (const r of regions) {
      if (r.parent_id === cur && !out.has(r.id)) {
        out.add(r.id);
        stack.push(r.id);
      }
    }
  }
  return out;
}

/** The region's own fields (US-2.2 첫째): name, level, parent, description. Saving is a
 * replace write — a cleared description is gone (BR-U3-1). */
export function RegionForm({
  region,
  regions,
  busy,
  onSave,
  onDelete,
}: {
  region: Region;
  regions: Region[];
  busy: boolean;
  onSave: (r: Region) => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(region.name);
  const [level, setLevel] = useState(region.level);
  const [parent, setParent] = useState(region.parent_id ?? "");
  const [desc, setDesc] = useState(region.description ?? "");
  const blocked = descendantsOf(region.id, regions);
  const parents = regions.filter((r) => r.id !== region.id && !blocked.has(r.id));
  return (
    <div className="flex flex-col gap-1.5" data-testid="region-form">
      <Field label={t("editor.region.name")} data-testid="region-name" value={name}
        onChange={(e) => setName(e.target.value)} />
      <label className="inline-flex flex-col gap-0.5 text-sm">
        <span className="text-ink-soft">{t("editor.region.level")}</span>
        <select data-testid="region-level" value={level} onChange={(e) => setLevel(e.target.value)}
          className="sketch-border bg-paper-card px-2 py-1 text-sm">
          {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </label>
      <label className="inline-flex flex-col gap-0.5 text-sm">
        <span className="text-ink-soft">{t("editor.region.parent")}</span>
        <select data-testid="region-parent" value={parent} onChange={(e) => setParent(e.target.value)}
          className="sketch-border bg-paper-card px-2 py-1 text-sm">
          <option value="">{t("editor.region.noParent")}</option>
          {parents.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
      </label>
      <label className="inline-flex flex-col gap-0.5 text-sm">
        <span className="text-ink-soft">{t("editor.region.description")}</span>
        <textarea data-testid="region-description" value={desc} rows={3}
          onChange={(e) => setDesc(e.target.value)}
          className="sketch-border bg-paper-card px-2 py-1 text-sm" />
      </label>
      <div className="flex gap-2">
        <Button size="sm" variant="primary" data-testid="region-save" disabled={busy || !name.trim()}
          onClick={() => onSave({ ...region, name: name.trim(), level, parent_id: parent || null,
            description: desc.trim() || null })}>
          {t("editor.region.save")}
        </Button>
        <Button size="sm" variant="danger" data-testid="region-delete" disabled={busy}
          onClick={onDelete}>
          {t("editor.region.delete")}
        </Button>
      </div>
    </div>
  );
}
