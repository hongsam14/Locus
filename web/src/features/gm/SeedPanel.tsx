import { enumLabel, numberWithMeaning } from "../../format";
import { useAction } from "../../hooks";
import { t } from "../../i18n";
import type { SeedView } from "../../types";
import { Badge, Button, Card, StatusView } from "../../ui";
import { english, type NameOf } from "../play/names";
import type { GmRes } from "./useGmData";

/** The world's event seeds (U8, BR-U8-15..18; V6 BR-V6-09/24/25): title and region by name,
 * the category and size in words; [start] makes it an active event with no LLM call, one
 * press per row at a time; a seed whose event is running says so. Errors go to the screen's
 * error line. */
export function SeedPanel({
  seeds,
  nameOf = english,
  closed,
  busy,
  onStart,
}: {
  seeds: GmRes<SeedView[]>;
  nameOf?: NameOf;
  closed: boolean;
  busy: boolean; // a bulk run goes
  onStart(seedId: string): Promise<unknown>;
}) {
  if (!seeds.data) {
    return <StatusView state={seeds.state === "error" ? "error" : "loading"} error={seeds.error} onRetry={seeds.reload} />;
  }
  return (
    <section data-testid="seed-panel" className="flex flex-col gap-1.5">
      {seeds.data.length === 0 && <p className="text-sm text-muted">{t("empty.seeds")}</p>}
      {seeds.data.map((view) => (
        <SeedRow key={view.seed.id} view={view} nameOf={nameOf} off={closed || busy} onStart={onStart} />
      ))}
    </section>
  );
}

function SeedRow({ view, nameOf, off, onStart }: { view: SeedView; nameOf: NameOf; off: boolean; onStart(id: string): Promise<unknown> }) {
  const start = useAction(() => onStart(view.seed.id));
  const { seed, region_name, running_event_id } = view;
  return (
    <Card data-testid={`seed-row-${seed.id}`} className="flex flex-wrap items-center gap-2 text-sm">
      <strong>{nameOf("event_seeds", seed.id, "title", seed.title)}</strong>
      <span className="text-xs text-muted">{nameOf("regions", seed.region_id, "name", region_name)}</span>
      <Badge>{enumLabel("eventCategory", seed.category)}</Badge>
      <span className="text-xs">
        {t("label.magnitude")} {numberWithMeaning("magnitude", seed.magnitude)}
      </span>
      <span className="ml-auto">
        {running_event_id ? (
          <span className="text-xs text-muted" data-testid={`seed-running-${seed.id}`}>
            {t("seed.running")}
          </span>
        ) : (
          <Button size="sm" data-testid={`seed-start-${seed.id}`} busy={start.busy} disabled={off}
            onClick={() => void start.run()}>
            {t("seed.start")}
          </Button>
        )}
      </span>
    </Card>
  );
}
