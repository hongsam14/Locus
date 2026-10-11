import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { AugmentPanel } from "../features/editor/AugmentPanel";
import { BuildPanel } from "../features/editor/BuildPanel";
import { type NewRegion, sameConnection } from "../features/editor/connections";
import { EditorHeader } from "../features/editor/EditorHeader";
import { EditorMapPane } from "../features/editor/EditorMapPane";
import { INSPECTOR_FIRST, type InspectorOpen, RegionInspector } from "../features/editor/RegionInspector";
import { RegionTab } from "../features/editor/RegionTab";
import { UnscopedPanel } from "../features/editor/UnscopedPanel";
import { useAugmentation } from "../features/editor/useAugmentation";
import { useEditorWorld } from "../features/editor/useEditorWorld";
import { WikiPanel } from "../features/editor/WikiPanel";
import { useAction, useMedia, WIDE } from "../hooks";
import { t, useLang } from "../i18n";
import { AppShell, MapPanelLayout } from "../layout";
import type { BuildReport, ConnectionEdge, ConnectionKind, ImportReport, NameRef } from "../types";
import { Button, InlineError, StatusView, toast } from "../ui";
import { Tabs } from "../ui/Tabs";

const PROV = { source: "input", generated_by: "designer" };
type Tab = "region" | "unscoped" | "augment" | "wiki";
const TABS: Tab[] = ["region", "unscoped", "augment", "wiki"];

/** `/editor/:worldId` — the world editor (V8 FR-S4, frontend-components § 1–5). The GM's frame:
 * one head, the map with its tools beside a 400 px panel of four tabs on a wide screen, one
 * column on a narrow one. The page holds what must outlive a hidden tab or a pressed map —
 * the world and selection (`useEditorWorld`), the augmentation run and its typed answers
 * (`useAugmentation`), the inspector's folds and the regions picked for unscoped knowledge
 * (UX-24) — and clears them by the rules of BLM § 1 item 4 when the world changes. */
export function EditorPage() {
  useLang();
  const { worldId = "" } = useParams();
  const wide = useMedia(WIDE);
  const [tab, setTab] = useState<Tab>("region");
  const [inspectorOpen, setInspectorOpen] = useState<InspectorOpen>(INSPECTOR_FIRST);
  const [unscopedPick, setUnscopedPick] = useState<Record<string, string>>({});
  const [picture, setPicture] = useState<{ url: string; name: string } | null>(null);
  const [building, setBuilding] = useState(false);
  const built = useRef<BuildReport | null>(null); // the last build of this opening, for the notice on close
  const panelRef = useRef<HTMLDivElement>(null);

  const w = useEditorWorld(worldId, {
    // a load or a build replaced the world: the run, its answers and the picks go (BLM § 1.4)
    onReplaced: () => {
      aug.reset();
      setUnscopedPick({});
    },
  });
  const aug = useAugmentation(worldId, {
    onChanged: () => {
      w.reloadWorld();
      w.reloadPanels("inspector");
    },
  });

  // another world: its picks and this browser's map picture do not carry over (BLM § 1.4)
  useEffect(() => {
    setUnscopedPick({});
    setPicture(null);
  }, [worldId]);

  // the map's writes: one at a time, the error under the map's head
  const mapWrite = useAction(async (fn: () => Promise<void>) => fn());
  const createRegion = (r: NewRegion) =>
    void mapWrite.run(async () => {
      const made = await api.createRegion(worldId, { ...r, world_id: worldId, provenance: PROV });
      setTab("region");
      w.created(made.id); // picked once a read that started after it brings it (UX-25)
    });
  // the connect tool on a pair that already has this kind edits that connection: its
  // grounds, prior and source are kept and only the weight is the form's (U3 #15)
  const createConnection = (a: string, b: string, kind: ConnectionKind, weight: number) =>
    void mapWrite.run(async () => {
      const old = sameConnection(w.world?.connections ?? [], a, b, kind);
      await api.saveConnection(worldId, old
        ? { ...old, source_region_id: a, target_region_id: b, weight }
        : { world_id: worldId, source_region_id: a, target_region_id: b, kind, weight, provenance: PROV });
      w.reloadWorld();
      w.reloadPanels("inspector");
    });

  /** A region chosen on the map opens the region tab; on a narrow screen the panel is below
   * the map, so it is scrolled to (BLM § 3; jsdom has no scrollIntoView, R-14). */
  function showRegionTab() {
    setTab("region");
    if (!wide) panelRef.current?.scrollIntoView?.({ block: "start" });
  }
  const pickOnMap = (id: string) => {
    w.select(id);
    showRegionTab();
  };
  const pickConnection = (c: ConnectionEdge) => {
    w.selectConnection(c);
    setInspectorOpen((o) => ({ ...o, connections: true }));
    showRegionTab();
  };

  function loaded(report: ImportReport) {
    w.replaced();
    const n = report.closed_session_ids.length;
    toast({ title: n ? t("notice.loadedClosed", { n }) : t("notice.loaded") });
  }
  function onBuilt(_id: string, report: BuildReport) {
    built.current = report;
    if (report.replaced) w.replaced();
    else {
      w.reloadWorld();
      w.reloadInfo();
    }
  }
  function closeBuild() {
    setBuilding(false);
    if (built.current?.ok) toast({ title: t("notice.buildDone") });
    built.current = null;
  }

  const world = w.world;
  const unscoped = world?.unscoped_knowledge_ids?.length ?? 0; // the server's rule (U3 C5)
  const entities = (world?.entities ?? []) as NameRef[];
  const name = w.info?.name_ko || world?.world?.name || w.info?.name;

  const label = (x: Tab) => <span data-testid={`editor-tab-${x}`}>{t(`tab.${x}`, { n: unscoped })}</span>;
  const content: Record<Tab, () => JSX.Element | null> = {
    region: () => (
      <RegionTab regions={w.regions} selected={w.selected} onSelect={w.select}>
        {world && w.selected && (
          <RegionInspector key={w.selected} worldId={worldId} regionId={w.selected} regions={w.regions}
            open={inspectorOpen} onOpenChange={(s, o) => setInspectorOpen((cur) => ({ ...cur, [s]: o }))}
            onChanged={w.reloadWorld} onSelectRegion={w.select} registerReload={w.registerReload}
            onDeleted={(region, detail) => {
              w.select(null);
              toast({ title: t("notice.regionDeleted", { name: region }), body: detail });
              w.reloadWorld();
            }} />
        )}
      </RegionTab>
    ),
    unscoped: () => (
      <UnscopedPanel worldId={worldId} regions={w.regions} picks={unscopedPick} onPicks={setUnscopedPick}
        onChanged={w.reloadWorld} registerReload={w.registerReload} />
    ),
    augment: () => (
      <AugmentPanel aug={aug} regions={w.regions} entities={entities} knowledge={world?.knowledge ?? []}
        connections={world?.connections ?? []} />
    ),
    wiki: () => (
      <WikiPanel worldId={worldId} regions={w.regions} onChanged={w.reloadWorld} registerReload={w.registerReload} />
    ),
  };

  const head = (
    <div className="flex flex-col gap-2">
      <EditorHeader worldId={worldId} world={world} name={name} openSessions={w.info?.open_sessions}
        onLoaded={loaded} onBuild={() => setBuilding(true)} />
      {w.error && (
        <div data-testid="world-error"><InlineError error={w.error} onRetry={w.retry} /></div>
      )}
    </div>
  );
  const map = (
    <div className="flex flex-col gap-2">
      <EditorMapPane loading={!world && w.state === "loading"} regions={w.regions}
        connections={world?.connections ?? []} selectedId={w.selected} selectedConnection={w.connection}
        busy={mapWrite.busy} disabled={!world} mapUrl={picture?.url ?? null} mapName={picture?.name ?? null}
        error={mapWrite.error ?? w.dragError} onSelect={pickOnMap} onSelectConnection={pickConnection}
        onMove={w.move} onCreateRegion={createRegion} onCreateConnection={createConnection}
        onMapFile={(file) => setPicture({ url: URL.createObjectURL(file), name: file.name })} /* this browser only */ />
      {w.notFound && <p className="text-sm text-danger" data-testid="region-not-found">{t("notice.regionNotFound")}</p>}
    </div>
  );
  const panel = (
    <div ref={panelRef} className="scroll-mt-4" data-testid="editor-panel">
      {w.missing ? (
        <div className="flex flex-col items-start gap-2" data-testid="empty-hint">
          <p className="text-sm text-muted">{t("empty.worldMissing")}</p>
          <Button size="sm" variant="primary" onClick={() => setBuilding(true)}>{t("file.build")}</Button>
        </div>
      ) : !world ? (
        w.state === "loading" ? <StatusView state="loading" /> : null
      ) : (
        <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)} label={t("label.editorTabs")}
          tabs={TABS.map((x) => ({ value: x, label: label(x), content: content[x]() }))} />
      )}
    </div>
  );

  return (
    <AppShell worldId={worldId}>
      <MapPanelLayout wide={wide} testId="editor-layout" panelLabel={t("label.editorPanel")}
        narrowOrder={["head", "map", "panel"]} head={head} map={map} panel={panel} />
      <BuildPanel open={building} worldId={worldId} exists={world != null} onClose={closeBuild} onBuilt={onBuilt}
        onShowUnscoped={() => {
          setTab("unscoped");
          w.reloadPanels("unscoped");
        }} />
    </AppShell>
  );
}
