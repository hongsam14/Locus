import type { ReactNode } from "react";
import { t } from "../../i18n";
import { MapPanelLayout } from "../../layout/MapPanelLayout";

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
 * one column — head, player, turn tools, band, map, tabs. Each part is placed once.
 * V8: the frame is the shared `MapPanelLayout`; this keeps the GM's order and names. */
export function GmLayout({ wide, s }: { wide: boolean; s: GmSections }) {
  return (
    <MapPanelLayout
      wide={wide}
      testId="gm-layout"
      panelLabel={t("label.gmPanel")}
      narrowOrder={["head", "panelTop", "map", "panel"]}
      head={
        <>
          {s.header}
          {s.banner}
          {s.player}
        </>
      }
      map={s.map}
      panelTop={
        <>
          {s.tools}
          {s.error}
          {s.band}
        </>
      }
      panel={s.tabs}
    />
  );
}
