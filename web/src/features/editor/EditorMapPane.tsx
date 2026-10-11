import { useEffect, useRef, useState } from "react";
import type { DescribedError } from "../../errors";
import { t } from "../../i18n";
import { WorldMap } from "../../map";
import type { Norm } from "../../map/geometry";
import type { ConnectionEdge, ConnectionKind, Region } from "../../types";
import { FileInput, InlineError } from "../../ui";
import { type MapTool, type NewRegion, sameConnection } from "./connections";
import { MapLegend } from "./MapLegend";
import { MapTools } from "./MapTools";
import { NewConnectionDialog } from "./NewConnectionDialog";
import { NewRegionDialog } from "./NewRegionDialog";

/** The editor's map pane (V8 frontend-components § 4.2): the tools, the legend and the map
 * picture on the map's head, then `WorldMap` in edit mode (the old adapter is gone). Select
 * picks and drags (a press alone saves nothing, BR-U3-30); add region opens a form at the
 * pressed spot; connect takes two regions in turn. `disabled` (no world to edit, U3 review
 * S21) turns the tools and dragging off. `world == null` shows a loading plate. */
export function EditorMapPane({
  loading,
  regions,
  connections,
  selectedId,
  selectedConnection,
  busy,
  disabled,
  mapUrl,
  mapName,
  error,
  onSelect,
  onSelectConnection,
  onMove,
  onCreateRegion,
  onCreateConnection,
  onMapFile,
}: {
  loading: boolean;
  regions: Region[];
  connections: ConnectionEdge[];
  selectedId: string | null;
  selectedConnection: ConnectionEdge | null;
  busy: boolean;
  disabled: boolean;
  mapUrl: string | null;
  mapName: string | null;
  error?: DescribedError; // a failed drag save or map write, shown under the map's head
  onSelect(id: string): void;
  onSelectConnection(c: ConnectionEdge): void;
  onMove(id: string, pos: Norm): void;
  onCreateRegion(r: NewRegion): void;
  onCreateConnection(a: string, b: string, kind: ConnectionKind, weight: number): void;
  onMapFile(file: File): void;
}) {
  const [tool, setTool] = useState<MapTool>("select");
  const [at, setAt] = useState<Norm | null>(null); // new region spot
  const [first, setFirst] = useState<string | null>(null); // connect: first region
  const [pair, setPair] = useState<[string, string] | null>(null); // connect: form open
  // a closed form gives the focus back to the tool that opened it (BR-V8-33), not to whatever
  // held it before — a tab trigger there would take the tab back on focus
  const tools = useRef<HTMLDivElement>(null);
  const formOpen = useRef(false);
  useEffect(() => {
    const open = at != null || pair != null;
    if (formOpen.current && !open) tools.current?.querySelector<HTMLElement>('[aria-pressed="true"]')?.focus();
    formOpen.current = open;
  }, [at, pair]);

  const name = (id: string) => regions.find((r) => r.id === id)?.name ?? id;
  function pick(id: string) {
    if (tool === "connect") {
      if (first == null) setFirst(id);
      else if (first === id) setFirst(null); // the same region twice cancels
      else {
        setPair([first, id]);
        setFirst(null);
      }
      return;
    }
    onSelect(id);
  }
  const hint = tool === "connect" && first ? t("map.hint.connectSecond", { name: name(first) }) : t(`map.hint.${tool}`);

  return (
    <section data-testid="map-canvas" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div ref={tools} className="min-w-0">
          <MapTools tool={tool} disabled={disabled} hint={hint} onTool={(next) => { setTool(next); setFirst(null); }} />
        </div>
        <FileInput label={t("label.mapPicture")} hint={t("hint.mapPictureLocal")} accept="image/*" data-testid="map-file-input"
          chosen={mapName ? [mapName] : undefined} onFiles={([f]) => f && onMapFile(f)} />
      </div>
      <MapLegend />
      {error && (
        <div data-testid="editor-error"><InlineError error={error} /></div>
      )}
      {loading ? (
        <div role="status" aria-label={t("label.loading")} className="aspect-[16/10] w-full rounded-lg bg-sunken" />
      ) : (
        <WorldMap
          mode="edit"
          label={t("label.map")}
          regions={regions}
          connections={connections}
          selectedId={tool === "connect" ? first : selectedId}
          selectedConnection={selectedConnection}
          draggable={tool === "select" && !disabled}
          background={mapUrl}
          onSelect={pick}
          onMove={onMove}
          onAddAt={tool === "addRegion" && !disabled ? (p) => setAt(p) : undefined}
          onSelectConnection={tool === "select" ? onSelectConnection : undefined}
        />
      )}
      {at && (
        <NewRegionDialog regions={regions} busy={busy} onCancel={() => setAt(null)}
          onSubmit={(r) => {
            onCreateRegion({ ...r, position: at });
            setAt(null);
          }} />
      )}
      {pair && (
        <NewConnectionDialog
          title={`${name(pair[0])} – ${name(pair[1])}`}
          busy={busy}
          existing={(kind) => sameConnection(connections, pair[0], pair[1], kind)}
          onCancel={() => setPair(null)}
          onSubmit={(kind, weight) => {
            onCreateConnection(pair[0], pair[1], kind, weight);
            setPair(null);
          }}
        />
      )}
    </section>
  );
}
