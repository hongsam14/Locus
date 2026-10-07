import { type ReactNode, useState } from "react";
import { MapOverlay } from "../../MapOverlay";
import { t } from "../../i18n";
import type { ConnectionEdge, ConnectionKind, Region } from "../../types";
import { Button, Dialog, Field, Select } from "../../ui";

export type MapTool = "select" | "addRegion" | "connect";
export const LEVELS = ["continent", "province", "town", "district", "terrain"];
export const KINDS: ConnectionKind[] = ["adjacent", "route", "river", "blocked"];

export interface NewRegion {
  name: string;
  level: string;
  parent_id: string | null;
  description: string | null;
  position: { x: number; y: number };
}

/** The stored connection of this pair and kind, either way round (a pair is one
 * connection, BR-U3-10), or undefined. */
export function sameConnection(
  connections: ConnectionEdge[],
  a: string,
  b: string,
  kind: ConnectionKind,
): ConnectionEdge | undefined {
  return connections.find(
    (c) =>
      c.kind === kind &&
      ((c.source_region_id === a && c.target_region_id === b) ||
        (c.source_region_id === b && c.target_region_id === a)),
  );
}

/** The editor's map (US-2.2, Q5=A): three tools, always visible, so it is clear what a
 * click does. Select picks and drags (a click alone saves nothing, BR-U3-30); add
 * region opens a form at the clicked spot; connect takes two regions in turn — on a
 * pair that already has the chosen kind the form edits that connection (U3 #15).
 * ``disabled`` (no world to edit, U3 review S21) turns every tool off. */
export function MapCanvas({
  regions,
  connections,
  selectedId,
  selectedConnection,
  mapImageUrl,
  busy = false,
  disabled = false,
  onSelect,
  onSelectConnection,
  onMove,
  onCreateRegion,
  onCreateConnection,
}: {
  regions: Region[];
  connections: ConnectionEdge[];
  selectedId: string | null;
  selectedConnection: ConnectionEdge | null;
  mapImageUrl?: string | null;
  busy?: boolean;
  disabled?: boolean;
  onSelect: (id: string) => void;
  onSelectConnection: (c: ConnectionEdge) => void;
  onMove: (id: string, x: number, y: number) => void;
  onCreateRegion: (r: NewRegion) => void;
  onCreateConnection: (a: string, b: string, kind: ConnectionKind, weight: number) => void;
}) {
  const [tool, setTool] = useState<MapTool>("select");
  const [at, setAt] = useState<{ x: number; y: number } | null>(null); // new region spot
  const [first, setFirst] = useState<string | null>(null); // connect: first region
  const [pair, setPair] = useState<[string, string] | null>(null); // connect: form open

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
  function choose(next: MapTool) {
    setTool(next);
    setFirst(null);
  }
  const hint =
    tool === "connect" && first
      ? t("map.hint.connectSecond", { name: name(first) })
      : t(`map.hint.${tool}`);

  return (
    <div className="flex flex-col gap-2" data-testid="map-canvas">
      <div className="flex flex-wrap items-center gap-1" role="toolbar">
        {(["select", "addRegion", "connect"] as MapTool[]).map((m) => (
          <Button
            key={m}
            size="sm"
            variant={tool === m ? "primary" : "ghost"}
            aria-pressed={tool === m}
            data-testid={`map-tool-${m === "addRegion" ? "add-region" : m}`}
            disabled={disabled}
            onClick={() => choose(m)}
          >
            {t(`map.tool.${m}`)}
          </Button>
        ))}
        <span className="text-xs text-muted ml-2" data-testid="map-hint">
          {hint}
        </span>
      </div>
      <MapOverlay
        regions={regions}
        connections={connections}
        selectedId={tool === "connect" ? first : selectedId}
        selectedConnection={selectedConnection}
        mapImageUrl={mapImageUrl}
        draggable={tool === "select" && !disabled}
        onSelect={pick}
        onMove={onMove}
        onBackground={tool === "addRegion" && !disabled ? (x, y) => setAt({ x, y }) : undefined}
        onSelectConnection={tool === "select" ? onSelectConnection : undefined}
      />
      {at && (
        <NewRegionForm
          regions={regions}
          busy={busy}
          onCancel={() => setAt(null)}
          onSubmit={(r) => {
            onCreateRegion({ ...r, position: at });
            setAt(null);
          }}
        />
      )}
      {pair && (
        <ConnectionForm
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
    </div>
  );
}

/** The map's forms on the shared Dialog (V2 BLM § 10): Esc or a click outside cancels. */
function MapDialog({ testId, title, onCancel, children }: {
  testId: string;
  title: ReactNode;
  onCancel: () => void;
  children: ReactNode;
}) {
  return (
    <Dialog open title={title} size="sm" testId={testId} onOpenChange={(open) => !open && onCancel()}>
      <div className="flex flex-col gap-3">{children}</div>
    </Dialog>
  );
}

/** The map's new-region form (U3 review C8: not the inspector's ``RegionForm``). */
function NewRegionForm({ regions, busy, onSubmit, onCancel }: {
  regions: Region[];
  busy: boolean;
  onSubmit: (r: Omit<NewRegion, "position">) => void;
  onCancel: () => void;
}) {
  const [nm, setName] = useState("");
  const [level, setLevel] = useState("town");
  const [parent, setParent] = useState("");
  const [desc, setDesc] = useState("");
  return (
    <MapDialog testId="new-region-form" title={t("editor.region.add")} onCancel={onCancel}>
      <Field label={t("editor.region.name")} data-testid="new-region-name" value={nm}
        onChange={(e) => setName(e.target.value)} />
      <Select label={t("editor.region.level")} data-testid="new-region-level" value={level}
        options={LEVELS.map((l) => ({ value: l, label: l }))} onChange={setLevel} />
      <Select label={t("editor.region.parent")} data-testid="new-region-parent" value={parent}
        options={[{ value: "", label: t("editor.region.noParent") }, ...regions.map((r) => ({ value: r.id, label: r.name }))]}
        onChange={setParent} />
      <Field label={t("editor.region.description")} value={desc} onChange={(e) => setDesc(e.target.value)} />
      <div className="flex justify-end gap-2">
        <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
        <Button size="sm" variant="primary" data-testid="new-region-save" disabled={busy || !nm.trim()}
          onClick={() => onSubmit({ name: nm.trim(), level, parent_id: parent || null,
            description: desc.trim() || null })}>
          {t("editor.region.save")}
        </Button>
      </div>
    </MapDialog>
  );
}

export function ConnectionForm({ title, busy, initialKind = "route", initialWeight = 0.6,
  existing = () => undefined, onSubmit, onCancel }: {
  title: string;
  busy: boolean;
  initialKind?: ConnectionKind;
  initialWeight?: number;
  /** The stored connection of the pair for a kind: the form then edits it. */
  existing?: (kind: ConnectionKind) => ConnectionEdge | undefined;
  onSubmit: (kind: ConnectionKind, weight: number) => void;
  onCancel: () => void;
}) {
  const [kind, setKind] = useState<ConnectionKind>(initialKind);
  const [weight, setWeight] = useState(existing(initialKind)?.weight ?? initialWeight);
  const old = existing(kind);
  return (
    <MapDialog testId="connection-form" onCancel={onCancel}
      title={`${t(old ? "editor.connection.edit" : "editor.connection.add")}: ${title}`}>
      {old && (
        <p className="text-xs text-muted" data-testid="connection-exists">
          {t("editor.connection.exists", { kind, weight: old.weight.toFixed(2) })}
        </p>
      )}
      <Select label={t("editor.connection.kind")} data-testid="connection-kind" value={kind}
        options={KINDS.map((k) => ({ value: k, label: k }))}
        onChange={(next) => {
          setKind(next);
          const stored = existing(next);
          if (stored) setWeight(stored.weight); // start from what is saved
        }} />
      <label className="text-sm">
        {t("editor.connection.weight")} {weight.toFixed(2)}
        <input type="range" min={0} max={1} step={0.05} value={weight} data-testid="connection-weight"
          onChange={(e) => setWeight(Number(e.target.value))} className="w-full" />
      </label>
      <div className="flex justify-end gap-2">
        <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
        <Button size="sm" variant="primary" data-testid="connection-save" disabled={busy}
          onClick={() => onSubmit(kind, weight)}>
          {t("editor.connection.save")}
        </Button>
      </div>
    </MapDialog>
  );
}
