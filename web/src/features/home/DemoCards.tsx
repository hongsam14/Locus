import type { Resource } from "../../hooks";
import { t } from "../../i18n";
import type { DemoInfo, WorldInfo } from "../../types";
import { InlineError } from "../../ui";
import { DemoCard } from "./DemoCard";

/** A card for each demo the server's manifest lists (U8, BR-U8-19) — no demo name in the
 * screen's code (BR-U8-1). A failed demo list is a line here only; the world list stands.
 * `worlds` undefined = not known yet: a card then reads as not loaded, and a load that
 * finds the world there asks (BLM § 1.1). */
export function DemoCards({
  demos,
  worlds,
  onLoaded,
}: {
  demos: Resource<DemoInfo[]>;
  worlds: WorldInfo[] | undefined;
  onLoaded: () => void;
}) {
  if (demos.data?.length === 0 && demos.state !== "error") return null;
  const byId = new Map((worlds ?? []).map((w) => [w.id, w]));
  return (
    <section className="flex flex-col gap-3" data-testid="demo-cards" aria-labelledby="demo-heading">
      <h2 id="demo-heading" className="font-heading text-xl">{t("demo.heading")}</h2>
      {demos.state === "error" && demos.error && (
        <div data-testid="demo-list-error">
          <InlineError error={demos.error} onRetry={demos.reload} />
        </div>
      )}
      {demos.data ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {demos.data.map((d) => (
            <DemoCard key={d.name} demo={d} held={byId.has(d.name)} regionCount={byId.get(d.name)?.region_count}
              onLoaded={onLoaded} />
          ))}
        </div>
      ) : (
        demos.state === "loading" && (
          <div role="status" aria-label={t("label.loading")} data-testid="demo-loading" className="grid gap-4 lg:grid-cols-2">
            <span className="block h-40 rounded-lg bg-sunken" />
          </div>
        )
      )}
    </section>
  );
}
