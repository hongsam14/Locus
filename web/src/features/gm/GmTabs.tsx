import type { ReactNode, Ref } from "react";
import { t } from "../../i18n";
import { Badge } from "../../ui";
import { Tabs } from "../../ui/Tabs";

export type GmTab = "region" | "events" | "seeds" | "timeline" | "deeds";

/** The GM's five tabs (V6 Q1=A, BR-V6-04/34): region, events, seeds, record, deeds — a
 * tablist with arrow keys (V2 Tabs). The events tab carries the count of suggestions waiting
 * for the GM; it does not open by itself (BR-V6-05). A hidden tab's content is unmounted, so
 * what it reads and holds lives outside (code plan § 1.1 R-08). */
export function GmTabs({
  tab,
  onTab,
  suggested,
  region,
  events,
  seeds,
  timeline,
  deeds,
  rootRef,
}: {
  tab: GmTab;
  onTab(tab: GmTab): void;
  suggested: number;
  region: ReactNode;
  events: ReactNode;
  seeds: ReactNode;
  timeline: ReactNode;
  deeds: ReactNode;
  rootRef?: Ref<HTMLDivElement>;
}) {
  const item = (value: GmTab, content: ReactNode, badge?: ReactNode) => ({
    value,
    label: <span data-testid={`gm-tab-${value}`}>{t(`tab.${value}`)}</span>,
    content,
    badge,
  });
  return (
    <div data-testid="gm-tabs" ref={rootRef} className="scroll-mt-4">
      <Tabs
        value={tab}
        onValueChange={(v) => onTab(v as GmTab)}
        label={t("label.gmTabs")}
        tabs={[
          item("region", region),
          item("events", events, suggested > 0 ? (
            <Badge data-testid="events-badge">
              <span className="sr-only">{t("label.waitingSuggestions")} </span>
              {suggested}
            </Badge>
          ) : undefined),
          item("seeds", seeds),
          item("timeline", timeline),
          item("deeds", deeds),
        ]}
      />
    </div>
  );
}
