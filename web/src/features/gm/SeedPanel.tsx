import { useEffect, useState } from "react";
import { api } from "../../api";
import { t } from "../../i18n";
import type { SeedView } from "../../types";
import { Badge, Button, Card } from "../../ui";

/** The world's event seeds (U8, BLM §3, BR-U8-15..18): each with its region, category
 * and size; [start] makes it an ACTIVE event with no LLM call; a seed whose event is
 * still running shows "running" instead. Errors go to the hub's error line. */
export function SeedPanel({
  sessionId,
  closed,
  busy,
  reloadKey = 0,
  onStart,
}: {
  sessionId: string;
  closed: boolean;
  busy: boolean;
  reloadKey?: number;
  onStart: (seedId: string) => Promise<boolean>;
}) {
  const [seeds, setSeeds] = useState<SeedView[] | null>(null);
  useEffect(() => {
    let alive = true;
    api
      .listSeeds(sessionId)
      .then((s) => alive && setSeeds(s))
      .catch(() => alive && setSeeds([]));
    return () => {
      alive = false;
    };
  }, [sessionId, reloadKey]);

  if (seeds == null) return null;
  return (
    <section data-testid="seed-panel" className="mt-2 flex flex-col gap-1">
      <h3 className="font-display">{t("seed.title")}</h3>
      {seeds.length === 0 && <div className="text-xs text-ink-soft">{t("seed.none")}</div>}
      {seeds.map(({ seed, region_name, running_event_id }) => (
        <Card key={seed.id} data-testid={`seed-row-${seed.id}`} className="flex flex-wrap items-center gap-2 text-sm">
          <strong>{seed.title}</strong>
          <span className="text-xs text-ink-soft">{region_name}</span>
          <Badge>{t("seed.category", { category: seed.category })}</Badge>
          <span className="text-xs">{t("seed.magnitude", { n: seed.magnitude.toFixed(2) })}</span>
          <span className="ml-auto">
            {running_event_id ? (
              <span className="text-xs text-ink-soft" data-testid={`seed-running-${seed.id}`}>
                {t("seed.running")}
              </span>
            ) : (
              <Button size="sm" data-testid={`seed-start-${seed.id}`} disabled={closed || busy}
                onClick={() => void onStart(seed.id)}>
                {t("seed.start")}
              </Button>
            )}
          </span>
        </Card>
      ))}
    </section>
  );
}
