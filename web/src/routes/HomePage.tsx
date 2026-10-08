import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { describeError, type DescribedError } from "../errors";
import { BuildPanel } from "../features/editor/BuildPanel";
import { DemoCards } from "../features/home/DemoCards";
import { HomeHero } from "../features/home/HomeHero";
import { MyWorlds } from "../features/home/MyWorlds";
import { NewSessionForm } from "../features/play/NewSessionForm";
import { useResource } from "../hooks";
import { useLang, useRequestLang } from "../i18n";
import type { Region } from "../types";
import { InlineError } from "../ui";
import { AppShell } from "../layout";

/** `/` (V4 FR-S1, BLM § 1): the opening lines, a card per manifest demo (the card owns its
 * world, Q1=A) and "my worlds". Both lists follow the display language (BR-V4-12) and are
 * read again after a demo load and after a build, whatever its end (UX-16). */
export function HomePage() {
  useLang();
  const lang = useRequestLang();
  const navigate = useNavigate();
  const demos = useResource(["demos", lang], () => api.listDemos());
  const worlds = useResource(["worlds", lang], () => api.listWorlds());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<DescribedError | null>(null);
  const [start, setStart] = useState<{ worldId: string; regions: Region[] } | null>(null);
  const [building, setBuilding] = useState(false);

  const { reload: reloadDemos } = demos;
  const { reload: reloadWorlds } = worlds;
  const reloadLists = useCallback(() => {
    reloadDemos();
    reloadWorlds();
  }, [reloadDemos, reloadWorlds]);
  const demoNames = useMemo(() => new Set((demos.data ?? []).map((d) => d.name)), [demos.data]);
  const demosSettled = demos.data !== undefined || demos.state === "error";

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(false);
    }
  }

  // the world's regions are read only when the form opens (BLM § 1.1)
  const openStart = (worldId: string) =>
    run(async () => setStart({ worldId, regions: (await api.exportWorld(worldId)).regions }));

  return (
    <AppShell>
      <div data-testid="home" className="mx-auto flex w-full max-w-[1240px] flex-col gap-8 px-4 pb-12">
        <HomeHero />
        {error && <InlineError error={error} />}
        <DemoCards demos={demos} worlds={worlds.data} onLoaded={reloadLists} />
        <MyWorlds worlds={worlds} demoNames={demoNames} settled={demosSettled} busy={busy}
          onBuild={() => setBuilding(true)} onStart={openStart} />
      </div>
      <NewSessionForm open={start != null} worldId={start?.worldId} regions={start?.regions ?? []} busy={busy}
        onCancel={() => setStart(null)}
        onSubmit={(name, startRegionId) =>
          run(async () => {
            const out = await api.startSession(start!.worldId, { name, start_region_id: startRegionId });
            navigate(`/play/${encodeURIComponent(out.session.id)}`);
          })
        } />
      {/* the panel forgets its files when closed idle and keeps a running build (U8 review #2) */}
      <BuildPanel open={building} exists={false}
        onClose={() => {
          setBuilding(false);
          reloadLists(); // a build that threw may still have written the world
        }}
        onBuilt={(worldId, report) => {
          reloadLists();
          // A replace stays on the report (what was replaced, the backup) — U3 review #6
          if (report.ok && !report.replaced) navigate(`/editor/${encodeURIComponent(worldId)}`);
        }} />
    </AppShell>
  );
}
