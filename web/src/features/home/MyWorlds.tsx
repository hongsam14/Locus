import type { Resource } from "../../hooks";
import { t } from "../../i18n";
import type { WorldInfo } from "../../types";
import { Button, InlineError, StatusView } from "../../ui";
import { WorldRow } from "./WorldRow";

/** "My worlds" (V4 Q1=A, BR-V4-05/07): the world list without the demo worlds — a demo card
 * owns those — and the one [build a world from sources] in its head (UX-15). `settled` false
 * = the demo list is still on its way: the rows wait, so a demo world does not flash here. */
export function MyWorlds({
  worlds,
  demoNames,
  settled,
  busy,
  onBuild,
  onStart,
}: {
  worlds: Resource<WorldInfo[]>;
  demoNames: ReadonlySet<string>;
  settled: boolean;
  busy: boolean;
  onBuild: () => void;
  onStart: (worldId: string) => void;
}) {
  const mine = (worlds.data ?? []).filter((w) => !demoNames.has(w.id));
  const ready = worlds.data !== undefined && settled;
  return (
    <section className="flex flex-col gap-3" data-testid="my-worlds" aria-labelledby="my-worlds-heading">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="my-worlds-heading" className="flex-1 font-heading text-xl">{t("label.myWorlds")}</h2>
        <Button data-testid="home-build" onClick={onBuild}>{t("home.buildFromSources")}</Button>
      </div>
      {worlds.state === "error" && worlds.error && <InlineError error={worlds.error} onRetry={worlds.reload} />}
      {ready ? (
        mine.length === 0 ? (
          <div data-testid="home-empty">
            <StatusView state="empty" emptyText={t("empty.noWorlds")} />
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {mine.map((w) => (
              <li key={w.id}>
                <WorldRow world={w} busy={busy} onStart={onStart} onStale={worlds.reload} />
              </li>
            ))}
          </ul>
        )
      ) : (
        worlds.state !== "error" && <StatusView state="loading" skeleton="cards" />
      )}
    </section>
  );
}
