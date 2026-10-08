import { useMemo } from "react";
import { t } from "../../i18n";
import { WorldMap } from "../../map";
import type { RegionOverlay } from "../../map";
import type { DescribedError } from "../../errors";
import type { WorldExport, WorldState } from "../../types";
import { Button, FileInput, InlineError } from "../../ui";
import { english, type NameOf } from "../play/names";
import { distortionColor } from "./WorldStateOverlay";

const LEGEND_STEPS = [0, 1, 2, 3, 4];

/** The map badge (V6 BR-V6-27, code plan § 1.2): the rumors going round, and ✦ with the
 * count of the player's story among them. A region with none has no badge. */
export function badgeOf(state: WorldState | null | undefined): Record<string, string> {
  const badge: Record<string, string> = {};
  for (const r of state?.regions ?? []) {
    if (r.active_rumors <= 0) continue;
    badge[r.region_id] = `${r.active_rumors}` + (r.deed_rumors ? ` ✦${r.deed_rumors}` : "");
  }
  return badge;
}

/** The GM's map (V6 frontend-components § 4, BR-V6-27/31/32): no dragging (`mode="gm"`,
 * RE-F05), the player ringed, the chosen region, and — while the overlay is on — the
 * distortion colour and the badge, with a legend in words. Pressing a region chooses it.
 * A background picture stays in this browser. */
export function MapPane({
  world,
  state,
  stateError,
  nameOf = english,
  selectedId,
  playerRegionId,
  overlayOn,
  mapUrl,
  mapName,
  onToggle,
  onSelect,
  onMapFile,
}: {
  world: WorldExport | null;
  state?: WorldState;
  stateError?: DescribedError;
  nameOf?: NameOf;
  selectedId: string | null;
  playerRegionId: string | null;
  overlayOn: boolean;
  mapUrl: string | null;
  mapName: string | null;
  onToggle(): void;
  onSelect(regionId: string): void;
  onMapFile(file: File): void;
}) {
  const regions = useMemo(
    () => (world?.regions ?? []).map((r) => ({ ...r, name: nameOf("regions", r.id, "name", r.name) })),
    [world, nameOf],
  );
  const overlay = useMemo(() => {
    if (!overlayOn || !state) return undefined;
    const badge = badgeOf(state);
    const out: Record<string, RegionOverlay> = {};
    for (const r of state.regions) out[r.region_id] = { fill: distortionColor(r.distortion), badge: badge[r.region_id] };
    return out;
  }, [overlayOn, state]);
  return (
    <section data-testid="gm-map" aria-label={t("label.map")} className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
        <Button size="sm" data-testid="gm-state-toggle" aria-pressed={overlayOn} onClick={onToggle}>
          {t("gm.stateToggle")}
        </Button>
        {overlayOn && (
          <span data-testid="gm-state-legend" className="flex flex-wrap items-center gap-x-3 gap-y-1 text-muted">
            <span className="inline-flex items-center gap-1">
              {LEGEND_STEPS.map((i) => (
                <span key={i} aria-hidden="true" className="inline-block h-3 w-4 rounded-sm border border-line-strong"
                  style={{ background: distortionColor(i / 5 + 0.01) }} />
              ))}
              <span>{t("label.legendColor")}</span>
            </span>
            <span>{t("label.legendCount")}</span>
            <span>{t("label.legendDeed")}</span>
          </span>
        )}
        <span className="ml-auto">
          <FileInput label={t("toolbar.pickMap")} accept="image/*" data-testid="map-file-input"
            chosen={mapName ? [mapName] : undefined} onFiles={([f]) => f && onMapFile(f)} />
        </span>
      </div>
      {overlayOn && stateError && (
        <div data-testid="gm-state-error"><InlineError error={stateError} /></div>
      )}
      {world === null ? (
        <div role="status" aria-label={t("label.loading")} className="aspect-[16/10] w-full rounded-lg bg-sunken" />
      ) : (
        <WorldMap
          mode="gm"
          label={t("label.map")}
          regions={regions}
          connections={world.connections}
          selectedId={selectedId}
          playerRegionId={playerRegionId}
          overlay={overlay}
          background={mapUrl}
          onSelect={onSelect}
        />
      )}
    </section>
  );
}
