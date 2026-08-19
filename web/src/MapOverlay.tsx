import { useRef, useState } from "react";
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
}

export function MapOverlay({
  regions,
  connections,
  selectedId,
  mapImageUrl,
  onSelect,
  onMove,
}: Props) {
  const pos = autoLayout(regions);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [drag, setDrag] = useState<{ id: string; x: number; y: number } | null>(null);

  const coordOf = (id: string) => (drag && drag.id === id ? { x: drag.x, y: drag.y } : pos[id]);

  function clientToNorm(e: { clientX: number; clientY: number }) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0.5, y: 0.5 };
    return {
      x: Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height)),
    };
  }

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
            setDrag({ id: drag.id, x: n.x, y: n.y });
          }
        }}
        onPointerUp={() => {
          if (drag) {
            onMove(drag.id, drag.x, drag.y);
            setDrag(null);
          }
        }}
      >
        {connections.map((c, i) => {
          const a = coordOf(c.source_region_id);
          const b = coordOf(c.target_region_id);
          if (!a || !b) return null;
          const s = edgeStyle(c.kind, c.weight);
          return (
            <line
              key={i}
              data-testid="connection-line"
              x1={a.x * W}
              y1={a.y * H}
              x2={b.x * W}
              y2={b.y * H}
              stroke={s.color}
              strokeWidth={s.width}
              strokeOpacity={s.opacity}
              strokeDasharray={s.dashed ? "6 4" : undefined}
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
              style={{ cursor: "grab" }}
              onPointerDown={() => setDrag({ id: r.id, x: c.x, y: c.y })}
              onClick={() => onSelect(r.id)}
            >
              <circle
                r={10}
                // var() resolves in CSS (style), not in SVG presentation attributes
                style={{
                  fill: selectedId === r.id ? "var(--color-ink)" : "var(--color-paper-card)",
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
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
