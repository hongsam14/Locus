// The world map (V2 FR-D6/D7, BLM § 8): fits its container (no fixed 800 × 500), turns a
// pointer back into 0..1 through the screen matrix, tells region levels apart by shape and
// size, and puts labels on plates where they cover no marker. Three uses: the editor
// (select, add, drag when asked), the GM (state rings and badges), play (a close-up of
// where the player is and where they can go).
import { useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { isDrag } from "../features/editor/drag";
import { t } from "../i18n";
import type { ConnectionEdge, Region } from "../types";
import { autoLayout } from "./autoLayout";
import { edgeStyle, uniqueEdges } from "./edgeStyle";
import { focusBox } from "./focus";
import {
  MAP_EXTENT,
  clampNorm,
  inside,
  invert,
  meetMatrix,
  normalizeFromMatrix,
  type Norm,
  type ViewBox,
} from "./geometry";
import { labelWidth, placeLabels, plateHeight, type Box } from "./labels";

export interface RegionOverlay {
  fill?: string; // a CSS colour (a token mix) for the region's marker
  ring?: "event" | "danger" | "info";
  badge?: string;
}

export interface WorldMapProps {
  regions: Region[];
  connections: ConnectionEdge[];
  mode: "edit" | "gm" | "play";
  label: string; // what the map shows, in words (aria-label)
  selectedId?: string | null;
  playerRegionId?: string | null;
  reachableIds?: string[];
  focus?: { id: string; neighbors: string[] } | null;
  overlay?: Record<string, RegionOverlay>;
  draggable?: boolean;
  selectedConnection?: ConnectionEdge | null;
  background?: string | null;
  onSelect?(id: string): void;
  onSelectConnection?(c: ConnectionEdge): void;
  onMove?(id: string, pos: Norm): void;
  onAddAt?(pos: Norm): void;
}

const LABEL_SIZE = 16;
const PLATE_H = plateHeight(LABEL_SIZE);
const BADGE_H = 16; // a badge line under the plate, kept clear like the plate (review § 2)
const HIT_WIDTH = 14; // an invisible wide stroke under each line to press (review § 2)
const AREA_LEVELS = new Set(["continent", "province"]);
const RING: Record<NonNullable<RegionOverlay["ring"]>, string> = {
  event: "var(--color-event)",
  danger: "var(--color-danger)",
  info: "var(--color-info)",
};

function markerRadius(level: string): number {
  return level === "town" ? 8 : 7;
}

function sameConnection(a: ConnectionEdge | null | undefined, b: ConnectionEdge): boolean {
  if (!a || a.kind !== b.kind) return false;
  return (
    (a.source_region_id === b.source_region_id && a.target_region_id === b.target_region_id) ||
    (a.source_region_id === b.target_region_id && a.target_region_id === b.source_region_id)
  );
}

function Marker({ level, fill }: { level: string; fill: string }) {
  const style = { fill, stroke: "var(--color-bg)", strokeWidth: 1.5 };
  if (level === "district") return <rect x={-6} y={-6} width={12} height={12} rx={2} style={style} />;
  if (level === "terrain") return <path d="M0 -8 L8 6 L-8 6 Z" style={style} />;
  return <circle r={markerRadius(level)} style={style} />;
}

const areaSize = (level: string) => (level === "continent" ? 26 : 18);
const areaSpacing = (level: string) => (level === "continent" ? 8 : 4);

/** The frame around an area name: the accent when selected, the GM state's wash and ring. */
function AreaFrame({ region, selected, overlay }: { region: Region; selected: boolean; overlay?: RegionOverlay }) {
  if (!selected && !overlay?.fill && !overlay?.ring) return null;
  const size = areaSize(region.level);
  const w = labelWidth(region.name, size) + areaSpacing(region.level) * [...region.name].length;
  const h = size * 1.5;
  const stroke = selected ? "var(--color-accent)" : overlay?.ring ? RING[overlay.ring] : "none";
  return (
    <rect
      data-testid={overlay?.fill ? `region-fill-${region.id}` : undefined}
      x={-w / 2}
      y={-h / 2}
      width={w}
      height={h}
      rx={6}
      pointerEvents="none"
      style={{
        fill: overlay?.fill ?? "var(--color-map-plate)",
        fillOpacity: overlay?.fill ? 0.45 : 1,
        stroke,
        strokeWidth: selected ? 2.5 : 3,
      }}
    />
  );
}

export function WorldMap({
  regions,
  connections,
  mode,
  label,
  selectedId,
  playerRegionId,
  reachableIds,
  focus,
  overlay,
  draggable = false,
  selectedConnection,
  background,
  onSelect,
  onSelectConnection,
  onMove,
  onAddAt,
}: WorldMapProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [drag, setDrag] = useState<{
    id: string;
    pos: Norm;
    start: { x: number; y: number };
    moved: boolean;
  } | null>(null);
  const [whole, setWhole] = useState(false);
  const canDrag = mode === "edit" && draggable;

  const pos = useMemo(() => autoLayout(regions), [regions]);
  const viewBox: ViewBox = useMemo(
    () => (mode === "play" && focus && !whole ? focusBox(pos, focus) : MAP_EXTENT),
    [mode, focus, whole, pos],
  );
  const reachable = useMemo(() => new Set(reachableIds ?? []), [reachableIds]);
  const dimOthers = mode === "play" && reachableIds != null;

  const at = (id: string): { x: number; y: number } | undefined => {
    const p = drag && drag.id === id && drag.moved ? drag.pos : pos[id];
    return p ? { x: p.x * MAP_EXTENT.w, y: p.y * MAP_EXTENT.h } : undefined;
  };

  function toNorm(e: { clientX: number; clientY: number }): Norm {
    const svg = svgRef.current;
    const client = { x: e.clientX, y: e.clientY };
    const ctm = svg?.getScreenCTM?.();
    if (ctm) return normalizeFromMatrix(client, ctm.inverse());
    const rect = svg?.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) return { x: 0.5, y: 0.5 };
    return normalizeFromMatrix(client, invert(meetMatrix(rect, viewBox)));
  }

  // labels: towns, districts and terrain go on plates; continents and provinces are area
  // names written where they are
  const points = regions
    .filter((r) => !AREA_LEVELS.has(r.level))
    .map((r) => ({ r, p: at(r.id) }))
    .filter((x): x is { r: Region; p: { x: number; y: number } } => x.p != null);
  // the room a marker takes with its rings: the player's glow, the selected / reachable
  // ring, a GM state ring (each drawn below at markerRadius + 9 / 6 / 4, plus its stroke)
  const room = (r: Region): number => {
    let pad = 2;
    if (overlay?.[r.id]?.ring) pad = 6;
    if (r.id === selectedId || reachable.has(r.id)) pad = 8;
    if (r.id === playerRegionId) pad = 10;
    return markerRadius(r.level) + pad;
  };
  const player = playerRegionId ? at(playerRegionId) : undefined;
  const pin: Box[] = player ? [{ x: player.x - 24, y: player.y - 36, w: 16, h: 24 }] : [];
  const group = (id: string) => (id === playerRegionId ? 0 : id === selectedId ? 1 : reachable.has(id) ? 2 : 3);
  const plates = new Map(
    placeLabels(
      points.map(({ r, p }) => ({ id: r.id, x: p.x, y: p.y, r: room(r), group: group(r.id) })),
      points.map(({ r }) => ({ id: r.id, text: r.name, size: LABEL_SIZE, below: overlay?.[r.id]?.badge ? BADGE_H : 0 })),
      pin,
      MAP_EXTENT,
    ).map((b) => [b.id, b]),
  );

  function onPointerDown(e: ReactPointerEvent<SVGGElement>, id: string) {
    if (!canDrag) return;
    // the marker keeps the pointer: a release outside the map still ends the drag, and a
    // click still lands on the marker (U3 review S23)
    try {
      e.currentTarget.setPointerCapture?.(e.pointerId);
    } catch {
      // no active pointer (a synthetic event): the svg handlers still apply
    }
    setDrag({ id, pos: pos[id], start: { x: e.clientX, y: e.clientY }, moved: false });
  }

  return (
    <div
      data-testid="map-overlay"
      className="relative w-full overflow-hidden rounded-lg border border-line-strong bg-map-land"
      style={{ aspectRatio: `${viewBox.w} / ${viewBox.h}` }}
    >
      {background && mode !== "play" && (
        // the alt text moves into the dictionary with the editor screen (V8)
        <img src={background} alt="world map" className="absolute inset-0 h-full w-full object-cover opacity-70" />
      )}
      <svg
        ref={svgRef}
        role="img"
        aria-label={label}
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 h-full w-full"
        onPointerMove={(e) => {
          if (drag) {
            const moved = drag.moved || isDrag(drag.start, { x: e.clientX, y: e.clientY });
            setDrag({ ...drag, pos: clampNorm(toNorm(e)), moved });
          }
        }}
        onPointerUp={() => {
          if (drag) {
            if (drag.moved) onMove?.(drag.id, drag.pos); // a click saves nothing (B7)
            setDrag(null);
          }
        }}
        // a drag the browser took away (a touch scroll, a lost window) ends unsaved; the
        // capture after a normal release ends nothing, the release already did (U3 S23)
        onPointerCancel={() => setDrag(null)}
        onLostPointerCapture={() => setDrag(null)}
        onClick={(e) => {
          if (mode === "edit" && onAddAt && e.target === e.currentTarget) {
            const n = toNorm(e);
            if (inside(n)) onAddAt(n); // a click on the letterbox beside the map adds nothing
          }
        }}
      >
        {background && mode === "play" && (
          // play zooms to a close-up: the picture is drawn in the map's own space so it
          // follows the view box (V4, V2 carry-over); "slice" covers the extent as the
          // editor's object-cover does, so a region sits on the same spot of the picture
          <image
            data-testid="map-background"
            href={background}
            x={MAP_EXTENT.x}
            y={MAP_EXTENT.y}
            width={MAP_EXTENT.w}
            height={MAP_EXTENT.h}
            preserveAspectRatio="xMidYMid slice"
            opacity={0.7}
            pointerEvents="none"
          />
        )}
        {uniqueEdges(connections).map((c) => {
          const a = at(c.source_region_id);
          const b = at(c.target_region_id);
          if (!a || !b) return null;
          const s = edgeStyle(c.kind, c.weight);
          const picked = sameConnection(selectedConnection, c);
          const faded =
            dimOthers &&
            !(
              (c.source_region_id === playerRegionId && reachable.has(c.target_region_id)) ||
              (c.target_region_id === playerRegionId && reachable.has(c.source_region_id))
            );
          const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
          return (
            <g
              key={`${c.source_region_id}|${c.target_region_id}|${c.kind}`}
              opacity={faded ? 0.35 : 1}
              style={{ cursor: onSelectConnection ? "pointer" : undefined }}
              onClick={onSelectConnection ? () => onSelectConnection(c) : undefined}
            >
              {onSelectConnection && (
                <line
                  data-testid="connection-hit"
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  style={{ stroke: "transparent", strokeWidth: HIT_WIDTH, strokeLinecap: "round" }}
                />
              )}
              <line
                data-testid="connection-line"
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                style={{
                  stroke: picked ? "var(--color-accent)" : s.stroke,
                  strokeWidth: picked ? s.width + 3 : s.width,
                  strokeOpacity: s.opacity,
                  strokeDasharray: s.dash,
                  strokeLinecap: "round",
                }}
              />
              {s.cross && (
                <path
                  d={`M${mid.x - 5} ${mid.y - 5} l10 10 M${mid.x + 5} ${mid.y - 5} l-10 10`}
                  style={{ stroke: s.stroke, strokeWidth: 2 }}
                  aria-hidden="true"
                />
              )}
            </g>
          );
        })}

        {regions.map((r) => {
          const p = at(r.id);
          if (!p) return null;
          const area = AREA_LEVELS.has(r.level);
          const o = overlay?.[r.id];
          const dim = dimOthers && r.id !== playerRegionId && !reachable.has(r.id);
          const rr = markerRadius(r.level);
          return (
            <g
              key={r.id}
              data-testid={`region-marker-${r.id}`}
              transform={`translate(${p.x}, ${p.y})`}
              opacity={dim ? 0.45 : 1}
              style={{ cursor: canDrag ? "grab" : onSelect ? "pointer" : undefined }}
              onPointerDown={(e) => onPointerDown(e, r.id)}
              onClick={() => onSelect?.(r.id)}
            >
              {area ? (
                <>
                  {/* an area name: no marker, a wide-spaced name. Only the small middle takes
                      presses, so a wide name does not swallow adding, dragging or a line
                      under it (review #11); a frame shows selection and the GM state (#10) */}
                  <AreaFrame
                    region={r}
                    selected={r.id === selectedId}
                    overlay={o}
                  />
                  <circle r={14} style={{ fill: "transparent" }} />
                  <text
                    textAnchor="middle"
                    dy="0.35em"
                    fontSize={areaSize(r.level)}
                    letterSpacing={areaSpacing(r.level)}
                    pointerEvents="none"
                    style={{
                      fill: r.id === selectedId || o?.fill ? "var(--color-fg)" : "var(--color-faint)",
                      fontFamily: "var(--font-heading)",
                      fontWeight: 700,
                    }}
                  >
                    {r.name}
                  </text>
                  {o?.badge && (
                    <text
                      data-testid={`region-badge-${r.id}`}
                      textAnchor="middle"
                      y={r.level === "continent" ? 34 : 28}
                      fontSize={13}
                      pointerEvents="none"
                      style={{ fill: "var(--color-muted)" }}
                    >
                      {o.badge}
                    </text>
                  )}
                </>
              ) : (
                <>
                  {r.id === selectedId && (
                    <circle r={rr + 6} style={{ fill: "none", stroke: "var(--color-accent)", strokeWidth: 2.5 }} />
                  )}
                  {reachable.has(r.id) && (
                    <circle
                      r={rr + 6}
                      style={{ fill: "none", stroke: "var(--color-accent)", strokeWidth: 2, strokeDasharray: "4 3" }}
                    />
                  )}
                  {o?.ring && <circle r={rr + 4} style={{ fill: "none", stroke: RING[o.ring], strokeWidth: 3 }} />}
                  {r.id === playerRegionId && (
                    <circle r={rr + 9} style={{ fill: "var(--color-map-glow)" }} aria-hidden="true" />
                  )}
                  <g data-testid={o?.fill ? `region-fill-${r.id}` : undefined}>
                    <Marker
                      level={r.level}
                      fill={o?.fill ?? (r.id === playerRegionId ? "var(--color-map-current)" : "var(--color-map-town)")}
                    />
                  </g>
                </>
              )}
              {r.id === playerRegionId && (
                <path
                  data-testid={`player-marker-${r.id}`}
                  transform="translate(-16 -22)"
                  d="M0 -9 a4.5 4.5 0 1 1 0.01 0 Z M-6 7 C-6 -1 6 -1 6 7 Z"
                  style={{ fill: "var(--color-map-player)", stroke: "var(--color-bg)", strokeWidth: 1 }}
                />
              )}
            </g>
          );
        })}

        {/* plates last, so lines never cross a name */}
        {points.map(({ r, p }) => {
          const b = plates.get(r.id);
          if (!b) return null;
          const strong = r.id === playerRegionId;
          const badge = overlay?.[r.id]?.badge;
          const dim = dimOthers && r.id !== playerRegionId && !reachable.has(r.id);
          // a name takes a press as its marker does (review #4)
          return (
            <g
              key={`label-${r.id}`}
              data-testid={`region-label-${r.id}`}
              opacity={dim ? 0.6 : 1}
              pointerEvents={onSelect ? undefined : "none"}
              style={{ cursor: onSelect ? "pointer" : undefined }}
              onClick={onSelect ? () => onSelect(r.id) : undefined}
            >
              <rect
                x={b.x}
                y={b.y}
                width={b.w}
                height={PLATE_H}
                rx={4}
                style={{ fill: strong ? "var(--color-accent)" : "var(--color-map-plate)" }}
              />
              <text
                x={b.x + b.w / 2}
                y={b.y + PLATE_H / 2}
                dy="0.35em"
                textAnchor="middle"
                fontSize={LABEL_SIZE}
                style={{
                  fill: strong ? "var(--color-on-accent)" : "var(--color-fg)",
                  fontWeight: strong || reachable.has(r.id) ? 700 : 400,
                }}
              >
                {r.name}
              </text>
              {badge && (
                <text
                  data-testid={`region-badge-${r.id}`}
                  x={b.x + b.w / 2}
                  y={b.y + PLATE_H + 12}
                  textAnchor="middle"
                  fontSize={13}
                  style={{ fill: "var(--color-muted)" }}
                >
                  {badge}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {mode === "play" && focus && (
        <button
          type="button"
          className="absolute bottom-2 right-2 min-h-9 rounded-md border border-line-strong bg-surface px-3 text-sm text-fg"
          onClick={() => setWhole((w) => !w)}
        >
          {whole ? t("action.closeUp") : t("action.wholeMap")}
        </button>
      )}
    </div>
  );
}
