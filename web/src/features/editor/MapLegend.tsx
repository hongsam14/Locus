import { ENUM_VALUES, enumLabel } from "../../format";
import { t } from "../../i18n";
import { edgeStyle } from "../../map";

const SHAPE = { stroke: "var(--color-ink)", strokeWidth: 1.5, fill: "var(--color-surface)" };

/** What the editor map's shapes and lines mean, in words (UX-18, BR-V8-09): towns are
 * circles, districts squares, terrain triangles, continents and provinces large type; each
 * connection kind's line as the map draws it. */
export function MapLegend() {
  return (
    <div data-testid="map-legend" aria-label={t("label.legend")} role="group"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
      <span className="font-bold">{t("label.legend")}</span>
      <span className="inline-flex items-center gap-1">
        <svg width="14" height="14" viewBox="-8 -8 16 16" aria-hidden="true"><circle r={5} style={SHAPE} /></svg>
        {enumLabel("regionLevel", "town")}
      </span>
      <span className="inline-flex items-center gap-1">
        <svg width="14" height="14" viewBox="-8 -8 16 16" aria-hidden="true"><rect x={-5} y={-5} width={10} height={10} rx={2} style={SHAPE} /></svg>
        {enumLabel("regionLevel", "district")}
      </span>
      <span className="inline-flex items-center gap-1">
        <svg width="14" height="14" viewBox="-8 -8 16 16" aria-hidden="true"><path d="M0 -6 L6 5 L-6 5 Z" style={SHAPE} /></svg>
        {enumLabel("regionLevel", "terrain")}
      </span>
      <span>{t("label.legendAreas")}</span>
      {ENUM_VALUES.connectionKind.map((kind) => {
        const s = edgeStyle(kind, 0.6);
        return (
          <span key={kind} className="inline-flex items-center gap-1">
            <svg width="22" height="8" viewBox="0 0 22 8" aria-hidden="true">
              <line x1={1} y1={4} x2={21} y2={4}
                style={{ stroke: s.stroke, strokeWidth: Math.min(s.width, 3), strokeOpacity: s.opacity, strokeDasharray: s.dash }} />
            </svg>
            {enumLabel("connectionKind", kind)}
          </span>
        );
      })}
    </div>
  );
}
