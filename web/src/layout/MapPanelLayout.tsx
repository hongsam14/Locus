import { Fragment, type ReactNode } from "react";

type Part = "head" | "panelTop" | "map" | "panel";

const NARROW_DEFAULT: Part[] = ["head", "map", "panelTop", "panel"];

/** A map beside a side panel, shared by the GM screen and the editor (V8 frontend-components
 * § 1, BR-V8-01/02). Wide (≥1024): the head across, then the map beside a 400 px panel that
 * sticks to the top and scrolls on its own; `panelTop` stays at the panel's top while the rest
 * scrolls (V6 #42). Narrower: one column in `narrowOrder`. Each part is placed once. */
export function MapPanelLayout({
  wide,
  testId,
  panelLabel,
  head,
  map,
  panel,
  panelTop,
  narrowOrder = NARROW_DEFAULT,
}: {
  wide: boolean;
  testId: string;
  panelLabel: string; // the panel is a named region, not a side note (V6 review 43(c))
  head: ReactNode;
  map: ReactNode;
  panel: ReactNode;
  panelTop?: ReactNode;
  narrowOrder?: Part[];
}) {
  if (wide) {
    return (
      <div data-testid={testId} data-wide="true" className="mx-auto flex w-full max-w-[1240px] flex-col gap-4 px-6 py-6">
        {head}
        <div className="grid grid-cols-[minmax(0,1fr)_400px] items-start gap-6">
          <div className="min-w-0">{map}</div>
          <section aria-label={panelLabel}
            className="sticky top-4 flex max-h-[calc(100vh-2rem)] min-w-0 flex-col overflow-y-auto pr-1">
            {panelTop != null && (
              <div data-testid={`${testId.replace(/-layout$/, "")}-panel-top`}
                className="sticky top-0 z-10 flex flex-col gap-4 bg-bg pb-4">
                {panelTop}
              </div>
            )}
            {panel}
          </section>
        </div>
      </div>
    );
  }
  const parts: Record<Part, ReactNode> = { head, panelTop, map, panel };
  return (
    <div data-testid={testId} className="mx-auto flex w-full max-w-[1240px] flex-col gap-4 px-4 py-4 sm:px-6">
      {/* fragments: the parts stay direct children of the column, as before the extraction */}
      {narrowOrder.map((p) => (parts[p] == null ? null : <Fragment key={p}>{parts[p]}</Fragment>))}
    </div>
  );
}

