import { useRef, useState } from "react";
import { isDrag, toNorm } from "./features/editor/drag";
import { autoLayout } from "./layout";
import type { ConnectionEdge, Region } from "./types";
import { edgeStyle } from "./viz";

const W = 800;
const H = 500;

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
  const pos = autoLayout(regions);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [drag, setDrag] = useState<{
    id: string;
    x: number;
    y: number;
    start: { x: number; y: number }; // screen pixels at the press
    moved: boolean;
  } | null>(null);

  const coordOf = (id: string) =>
    drag && drag.id === id && drag.moved ? { x: drag.x, y: drag.y } : pos[id];

  function clientToNorm(e: { clientX: number; clientY: number }) {
    return toNorm(e, svgRef.current?.getBoundingClientRect());
  }
  const isSelectedConnection = (c: ConnectionEdge) =>
    selectedConnection != null &&
    selectedConnection.kind === c.kind &&
    ((selectedConnection.source_region_id === c.source_region_id &&
      selectedConnection.target_region_id === c.target_region_id) ||
      (selectedConnection.source_region_id === c.target_region_id &&
        selectedConnection.target_region_id === c.source_region_id));

  return (
    <div
      data-testid="map-overlay"
      className="relative sketch-border sketch-shadow overflow-hidden bg-paper-card"
      style={{ width: W, height: H, maxWidth: "100%" }}
    >
      {mapImageUrl && (
        <img
          src={mapImageUrl}
          alt="world map"
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="absolute inset-0 h-full w-full"
        onPointerMove={(e) => {
          if (drag) {
            const n = clientToNorm(e);
            const moved = drag.moved || isDrag(drag.start, { x: e.clientX, y: e.clientY });
            setDrag({ ...drag, x: n.x, y: n.y, moved });
          }
        }}
        onPointerUp={() => {
          if (drag) {
            if (drag.moved) onMove(drag.id, drag.x, drag.y); // a click saves nothing (B7)
            setDrag(null);
          }
        }}
        onClick={(e) => {
          if (onBackground && e.target === e.currentTarget) {
            const n = clientToNorm(e);
            onBackground(n.x, n.y);
          }
        }}
      >
        {connections.map((c, i) => {
          const a = coordOf(c.source_region_id);
          const b = coordOf(c.target_region_id);
          if (!a || !b) return null;
          const s = edgeStyle(c.kind, c.weight);
          const picked = isSelectedConnection(c);
          return (
            <line
              key={i}
              data-testid="connection-line"
              x1={a.x * W}
              y1={a.y * H}
              x2={b.x * W}
              y2={b.y * H}
              stroke={s.color}
              strokeWidth={picked ? s.width + 3 : s.width}
              strokeOpacity={s.opacity}
              strokeDasharray={s.dashed ? "6 4" : undefined}
              style={onSelectConnection ? { cursor: "pointer" } : undefined}
              onClick={onSelectConnection ? () => onSelectConnection(c) : undefined}
            />
          );
        })}
        {regions.map((r) => {
          const c = coordOf(r.id);
          if (!c) return null;
          return (
            <g
              key={r.id}
              data-testid={`region-marker-${r.id}`}
              transform={`translate(${c.x * W}, ${c.y * H})`}
              style={{ cursor: draggable ? "grab" : "pointer" }}
              onPointerDown={(e) => {
                if (draggable) {
                  const start = { x: e.clientX, y: e.clientY };
                  setDrag({ id: r.id, x: c.x, y: c.y, start, moved: false });
                }
              }}
              onClick={() => onSelect(r.id)}
            >
              {markerId === r.id && (
                <circle
                  data-testid={`player-marker-${r.id}`}
                  r={15}
                  style={{ fill: "none", stroke: "var(--color-danger)" }}
                  strokeWidth={3}
                />
              )}
              <circle
                r={10}
                data-testid={regionFill?.[r.id] ? `region-fill-${r.id}` : undefined}
                // var() resolves in CSS (style), not in SVG presentation attributes
                style={{
                  fill:
                    selectedId === r.id
                      ? "var(--color-ink)"
                      : (regionFill?.[r.id] ?? "var(--color-paper-card)"),
                  stroke: "var(--color-ink)",
                }}
                strokeWidth={2}
              />
              <text
                x={12}
                y={4}
                fontSize={13}
                style={{ fill: "var(--color-ink)", fontFamily: "var(--font-display)" }}
              >
                {r.name}
                {markerId === r.id ? " ●" : ""}
              </text>
              {regionBadge?.[r.id] && (
                <text
                  data-testid={`region-badge-${r.id}`}
                  x={12}
                  y={20}
                  fontSize={11}
                  style={{ fill: "var(--color-ink-soft)" }}
                >
                  {regionBadge[r.id]}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
