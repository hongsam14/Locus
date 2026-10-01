import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { llmOff, useCapabilities } from "../capabilities";
import { BuildPanel } from "../features/editor/BuildPanel";
import { DemoCards } from "../features/home/DemoCards";
import { NewSessionForm } from "../features/play/NewSessionForm";
import { t, useLang } from "../i18n";
import type { Region, WorldInfo } from "../types";
import { Button, Card, LlmNotice, Panel } from "../ui";
import { AppNav } from "./AppNav";

/** `/` — the demo cards (U8, BR-U8-19: from the server's manifest, shown always) and the
 * world list (US-6.4, BR-U3-34): name, regions, last edit and open sessions, with [edit]
 * and [start session]; building from sources. Without an LLM key a line says so first. */
export function HomePage() {
  useLang();
  const navigate = useNavigate();
  const [worlds, setWorlds] = useState<WorldInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [start, setStart] = useState<{ worldId: string; regions: Region[] } | null>(null);
  const [building, setBuilding] = useState(false);
  const caps = useCapabilities();

  const loadWorlds = () => api.listWorlds().then(setWorlds).catch((e) => setError(String(e)));
  useEffect(() => {
    loadWorlds();
  }, []);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const openStart = (worldId: string) =>
    run(async () => setStart({ worldId, regions: (await api.exportWorld(worldId)).regions }));
  // the panel forgets its files when closed idle and keeps a running build (U8 review #2)
  const openBuild = () => setBuilding(true);

  return (
    <div className="min-h-full">
      <AppNav />
      <LlmNotice visible={llmOff(caps)} />
      <Panel title={t("home.title")} className="m-3" data-testid="home">
        {error && <div className="text-danger text-sm">{error}</div>}
        <DemoCards worlds={worlds} onLoaded={loadWorlds} />
        {worlds?.length === 0 && (
          <div className="flex flex-col gap-2" data-testid="home-empty">
            <span className="text-ink-soft">{t("home.empty")}</span>
            <div className="flex gap-2">
              <Button data-testid="home-build" disabled={busy} onClick={openBuild}>
                {t("home.buildFromSources")}
              </Button>
            </div>
          </div>
        )}
        <div className="flex flex-col gap-1.5">
          {worlds?.map((w) => (
            <Card key={w.id} data-testid={`world-row-${w.id}`} className="flex flex-wrap items-center gap-2">
              <strong className="font-display">{w.name}</strong>
              <code className="text-xs text-ink-soft">{w.id}</code>
              <span className="text-xs">{t("home.regions", { n: w.region_count })}</span>
              {w.updated_at && (
                <span className="text-xs text-ink-soft">
                  {t("home.updated", { when: new Date(w.updated_at).toLocaleString() })}
                </span>
              )}
              {(w.open_sessions ?? 0) > 0 && (
                <span className="text-xs text-danger">{t("home.openSessions", { n: w.open_sessions ?? 0 })}</span>
              )}
              <span className="ml-auto flex gap-1">
                <Button size="sm" data-testid={`world-edit-${w.id}`}
                  onClick={() => navigate(`/editor/${encodeURIComponent(w.id)}`)}>
                  {t("home.edit")}
                </Button>
                <Button size="sm" variant="primary" data-testid={`world-start-${w.id}`} disabled={busy}
                  onClick={() => openStart(w.id)}>
                  {t("home.startSession")}
                </Button>
              </span>
            </Card>
          ))}
        </div>
        {worlds && worlds.length > 0 && (
          <Button size="sm" className="mt-2" data-testid="home-build" onClick={openBuild}>
            {t("home.buildFromSources")}
          </Button>
        )}
      </Panel>
      <NewSessionForm open={start != null} regions={start?.regions ?? []} busy={busy}
        onCancel={() => setStart(null)}
        onSubmit={(name, startRegionId) =>
          run(async () => {
            const out = await api.startSession(start!.worldId, { name, start_region_id: startRegionId });
            navigate(`/play/${encodeURIComponent(out.session.id)}`);
          })
        } />
      <BuildPanel open={building} exists={false} onClose={() => setBuilding(false)}
        onBuilt={(worldId, report) =>
          // A replace stays on the report (what was replaced, the backup) — U3 review #6
          report.ok && !report.replaced && navigate(`/editor/${encodeURIComponent(worldId)}`)
        } />
    </div>
  );
}
