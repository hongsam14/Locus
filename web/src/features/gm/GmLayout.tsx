import type { ReactNode } from "react";
import { t } from "../../i18n";

export interface GmSections {
  header: ReactNode;
  banner: ReactNode; // the ended-session line, or nothing
  player: ReactNode;
  map: ReactNode;
  tools: ReactNode;
  error: ReactNode; // the write error line, between the tools and the band
  band: ReactNode;
  tabs: ReactNode;
}

/** Where each part of the GM screen goes, by width (V6 frontend-components § 1, BR-V6-02/03).
 * Wide (≥1024): the head across, then the map beside a 400 px panel — turn tools, error line,
 * result band, tabs — that sticks to the top and scrolls on its own (code plan § 1.1 R-08:
 * no measured head height; the column fits the viewport once the page scrolls). Narrower:
 * one column — head, player, turn tools, band, map, tabs. Each part is placed once. */
export function GmLayout({ wide, s }: { wide: boolean; s: GmSections }) {
  const head = (
    <>
      {s.header}
      {s.banner}
      {s.player}
    </>
  );
  if (wide) {
    return (
      <div data-testid="gm-layout" data-wide="true" className="mx-auto flex w-full max-w-[1240px] flex-col gap-4 px-6 py-6">
        {head}
        <div className="grid grid-cols-[minmax(0,1fr)_400px] items-start gap-6">
          <div className="min-w-0">{s.map}</div>
          {/* the GM's main controls: a named region, not a side note (<aside>, review 43(c)); the
              tools, the error line and the band stay at its top while the tabs scroll (#42) */}
          <section aria-label={t("label.gmPanel")}
            className="sticky top-4 flex max-h-[calc(100vh-2rem)] min-w-0 flex-col overflow-y-auto pr-1">
            <div data-testid="gm-panel-top" className="sticky top-0 z-10 flex flex-col gap-4 bg-bg pb-4">
              {s.tools}
              {s.error}
              {s.band}
            </div>
            {s.tabs}
          </section>
        </div>
      </div>
    );
  }
  return (
    <div data-testid="gm-layout" className="mx-auto flex w-full max-w-[1240px] flex-col gap-4 px-4 py-4 sm:px-6">
      {head}
      {s.tools}
      {s.error}
      {s.band}
      {s.map}
      {s.tabs}
    </div>
  );
}
