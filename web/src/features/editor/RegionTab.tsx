import type { ReactNode } from "react";
import { t } from "../../i18n";
import type { Region } from "../../types";
import { Button, Select } from "../../ui";
import { regionOptions } from "./connections";

/** The keyboard way to any region (BR-V8-08, FR-S6): the regions grouped by level, the same
 * selection the map shows. The map itself is not reached by keyboard (§9). */
export function RegionPicker({ regions, selected, onSelect }: {
  regions: Region[];
  selected: string | null;
  onSelect(id: string): void;
}) {
  if (regions.length === 0) return null;
  return (
    <Select label={t("label.regionPicker")} data-testid="region-picker" value={selected ?? ""}
      placeholder={t("session.pickRegion")} options={regionOptions(regions)} onChange={onSelect} />
  );
}

/** The [지역] tab (V8 frontend-components § 4.4): the picker on top, then the inspector of the
 * chosen region, or a line saying how to choose one. */
export function RegionTab({ regions, selected, onSelect, children }: {
  regions: Region[];
  selected: string | null;
  onSelect(id: string): void;
  children?: ReactNode; // the inspector, when a region is chosen
}) {
  return (
    <div className="flex flex-col gap-3" data-testid="region-tab">
      <RegionPicker regions={regions} selected={selected} onSelect={onSelect} />
      {selected ? children : <p className="text-sm text-muted">{t("hint.pickRegionEditor")}</p>}
    </div>
  );
}

/** Deleting the region sits apart from [save], under a rule, in its own place (UX-19,
 * BR-V8-12); the delete plan still asks first. */
export function DangerZone({ disabled, onDelete }: { disabled?: boolean; onDelete(): void }) {
  return (
    <section data-testid="danger-zone" aria-label={t("label.dangerZone")} className="mt-2 flex flex-col gap-2 border-t border-dashed border-line-strong pt-3">
      <h3 className="text-sm font-bold text-danger">{t("label.dangerZone")}</h3>
      <div>
        <Button size="sm" variant="danger" data-testid="region-delete" disabled={disabled} onClick={onDelete}>
          {t("action.deleteRegion")}
        </Button>
      </div>
    </section>
  );
}
