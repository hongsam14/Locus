import { useState } from "react";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Field, Select, Textarea } from "../../ui";
import { levelOptions, regionOptions } from "./connections";

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
 * replace write — a cleared description is gone (BR-U3-1). Deleting the region is not here:
 * it sits in the inspector's danger zone, apart from [save] (V8 UX-19, BR-V8-12). */
export function RegionForm({
  region,
  regions,
  busy,
  saved = false,
  onSave,
}: {
  region: Region;
  regions: Region[];
  busy: boolean;
  saved?: boolean; // the inspector says "saved" on the button for a second (BLM § 5)
  onSave: (r: Region) => void;
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
      <Select label={t("editor.region.level")} data-testid="region-level" value={level}
        options={levelOptions()} onChange={setLevel} />
      <Select label={t("editor.region.parent")} data-testid="region-parent" value={parent}
        options={[{ value: "", label: t("editor.region.noParent") }, ...regionOptions(parents)]}
        onChange={setParent} />
      <Textarea label={t("editor.region.description")} data-testid="region-description" value={desc} rows={3}
        onChange={(e) => setDesc(e.target.value)} />
      <div className="flex gap-2">
        <Button size="sm" variant="primary" data-testid="region-save" disabled={busy || !name.trim()}
          onClick={() => onSave({ ...region, name: name.trim(), level, parent_id: parent || null,
            description: desc.trim() || null })}>
          {saved ? t("notice.saved") : t("editor.region.save")}
        </Button>
      </div>
    </div>
  );
}
