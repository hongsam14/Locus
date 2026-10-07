// The old map props on the new WorldMap (V2 Step 8). The screens still pass these; V4, V6
// and V8 move to WorldMap directly and the adapter goes with V8.
import { t } from "./i18n";
import { WorldMap } from "./map";
import type { RegionOverlay } from "./map";
import type { ConnectionEdge, Region } from "./types";

interface Props {
  regions: Region[];
  connections: ConnectionEdge[];
  selectedId?: string | null;
  mapImageUrl?: string | null;
  onSelect: (id: string) => void;
  onMove: (id: string, x: number, y: number) => void;
  // U3 editor (Q5=A): a press-and-release without moving never moves (BR-U3-30);
  // ``draggable=false`` turns dragging off (the add/connect tools)
  draggable?: boolean;
  onBackground?: (x: number, y: number) => void; // a click on empty map, normalized
  onSelectConnection?: (c: ConnectionEdge) => void;
  selectedConnection?: ConnectionEdge | null;
  // U7 GM screen: the player's region is ringed (BR-U7-22); the world state overlay
  // colors regions and puts a count badge on them (BR-U7-23)
  markerId?: string | null;
  regionFill?: Record<string, string>;
  regionBadge?: Record<string, string>;
}

export function MapOverlay({
  regions,
  connections,
  selectedId,
  mapImageUrl,
  onSelect,
  onMove,
  markerId,
  regionFill,
  regionBadge,
  draggable = true,
  onBackground,
  onSelectConnection,
  selectedConnection,
}: Props) {
  let overlay: Record<string, RegionOverlay> | undefined;
  if (regionFill || regionBadge) {
    overlay = {};
    for (const id of new Set([...Object.keys(regionFill ?? {}), ...Object.keys(regionBadge ?? {})])) {
      overlay[id] = { fill: regionFill?.[id], badge: regionBadge?.[id] };
    }
  }
  return (
    <WorldMap
      // "edit" keeps every current use as it was (the GM map's own mode, with no drag,
      // comes with V6 — RE-F05)
      mode="edit"
      label={t("label.map")}
      regions={regions}
      connections={connections}
      selectedId={selectedId}
      playerRegionId={markerId}
      overlay={overlay}
      draggable={draggable}
      selectedConnection={selectedConnection}
      background={mapImageUrl}
      onSelect={onSelect}
      onMove={(id, p) => onMove(id, p.x, p.y)}
      onAddAt={onBackground ? (p) => onBackground(p.x, p.y) : undefined}
      onSelectConnection={onSelectConnection}
    />
  );
}
