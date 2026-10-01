import { type ReactNode, useState } from "react";
import { MapOverlay } from "../../MapOverlay";
import { t } from "../../i18n";
import type { ConnectionEdge, ConnectionKind, Region } from "../../types";
import { Button, Field } from "../../ui";

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
        <span className="text-xs text-ink-soft ml-2" data-testid="map-hint">
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

function Dialog({ testId, children }: { testId: string; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4" role="dialog"
      aria-modal="true" data-testid={testId}>
      <div className="sketch-border sketch-shadow bg-paper-card p-4 max-w-sm w-full flex flex-col gap-2">
        {children}
      </div>
    </div>
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
    <Dialog testId="new-region-form">
      <h2 className="font-display text-lg">{t("editor.region.add")}</h2>
      <Field label={t("editor.region.name")} data-testid="new-region-name" value={nm}
        onChange={(e) => setName(e.target.value)} />
      <select data-testid="new-region-level" value={level} onChange={(e) => setLevel(e.target.value)}
        className="sketch-border bg-paper-card px-2 py-1 text-sm" aria-label={t("editor.region.level")}>
        {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
      </select>
      <select data-testid="new-region-parent" value={parent} onChange={(e) => setParent(e.target.value)}
        className="sketch-border bg-paper-card px-2 py-1 text-sm" aria-label={t("editor.region.parent")}>
        <option value="">{t("editor.region.noParent")}</option>
        {regions.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
      </select>
      <Field label={t("editor.region.description")} value={desc} onChange={(e) => setDesc(e.target.value)} />
      <div className="flex justify-end gap-2">
        <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
        <Button size="sm" variant="primary" data-testid="new-region-save" disabled={busy || !nm.trim()}
          onClick={() => onSubmit({ name: nm.trim(), level, parent_id: parent || null,
            description: desc.trim() || null })}>
          {t("editor.region.save")}
        </Button>
      </div>
    </Dialog>
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
    <Dialog testId="connection-form">
      <h2 className="font-display text-lg">
        {t(old ? "editor.connection.edit" : "editor.connection.add")}: {title}
      </h2>
      {old && (
        <p className="text-xs text-ink-soft" data-testid="connection-exists">
          {t("editor.connection.exists", { kind, weight: old.weight.toFixed(2) })}
        </p>
      )}
      <select data-testid="connection-kind" value={kind}
        onChange={(e) => {
          const next = e.target.value as ConnectionKind;
          setKind(next);
          const stored = existing(next);
          if (stored) setWeight(stored.weight); // start from what is saved
        }}
        className="sketch-border bg-paper-card px-2 py-1 text-sm" aria-label={t("editor.connection.kind")}>
        {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
      </select>
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
    </Dialog>
  );
}
