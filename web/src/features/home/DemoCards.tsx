import { useEffect, useState } from "react";
import { api } from "../../api";
import { t } from "../../i18n";
import type { DemoInfo, WorldInfo } from "../../types";
import { DemoCard } from "./DemoCard";

/** A card for each demo the server's manifest lists (U8, BR-U8-19) — no demo name in the
 * screen's code (BR-U8-1). Shown whether or not worlds exist. */
export function DemoCards({ worlds, onLoaded }: { worlds: WorldInfo[] | null; onLoaded: () => void }) {
  const [demos, setDemos] = useState<DemoInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.listDemos().then(setDemos).catch((e) => setError(String(e)));
  }, []);
  if (error) return <div className="text-sm text-danger" data-testid="demo-list-error">{error}</div>;
  if (!demos || demos.length === 0) return null;
  const held = new Set((worlds ?? []).map((w) => w.id));
  return (
    <section className="flex flex-col gap-2" data-testid="demo-cards">
      <h2 className="font-heading text-lg">{t("demo.heading")}</h2>
      {demos.map((d) => (
        <DemoCard key={d.name} demo={d} exists={held.has(d.name)} onLoaded={onLoaded} />
      ))}
    </section>
  );
}
