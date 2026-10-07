import { useState } from "react";
import { t } from "../../i18n";
import type { NPC, NpcDraft } from "../../types";
import { Button, Card, Field } from "../../ui";
import { NpcDraftCards } from "./NpcDraftCards";

export interface NpcFields {
  name: string;
  role: string;
  description: string;
  traits: string[];
}

/** The region's inhabitants (US-2.4), shown as written — NPC text is not translated
 * (BR-U3-37) — with add, edit, delete (confirmed) and suggestions (US-2.5). */
export function NpcEditorList({
  worldId,
  regionId,
  npcs,
  busy,
  onCreate,
  onUpdate,
  onDelete,
}: {
  worldId: string;
  regionId: string;
  npcs: NPC[];
  busy: boolean;
  onCreate: (f: NpcFields) => Promise<boolean>;
  onUpdate: (npc: NPC) => void;
  onDelete: (npc: NPC) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  return (
    <div className="flex flex-col gap-1.5" data-testid="npc-list">
      {npcs.length === 0 && <div className="text-xs text-muted">{t("editor.npc.none")}</div>}
      {npcs.map((n) =>
        editing === n.id ? (
          <NpcForm key={n.id} initial={n} busy={busy} onCancel={() => setEditing(null)}
            onSubmit={(f) => {
              onUpdate({ ...n, ...f });
              setEditing(null);
            }} />
        ) : (
          <Card key={n.id} data-testid={`editor-npc-${n.id}`} className="text-sm flex flex-col gap-0.5">
            <strong>{n.name}</strong>
            <span className="text-xs text-muted">{n.role} · {n.traits.join(", ")}</span>
            <span className="text-xs">{n.description}</span>
            <div className="flex gap-1">
              <Button size="sm" disabled={busy} data-testid={`npc-edit-${n.id}`}
                onClick={() => setEditing(n.id)}>{t("editor.knowledge.edit")}</Button>
              <Button size="sm" variant="danger" disabled={busy} data-testid={`npc-delete-${n.id}`}
                onClick={() => onDelete(n)}>✕</Button>
            </div>
          </Card>
        ),
      )}
      {adding ? (
        <NpcForm busy={busy} onCancel={() => setAdding(false)}
          onSubmit={async (f) => {
            if (await onCreate(f)) setAdding(false);
          }} />
      ) : (
        <Button size="sm" data-testid="npc-add" disabled={busy} onClick={() => setAdding(true)}>
          {t("editor.npc.add")}
        </Button>
      )}
      <NpcDraftCards worldId={worldId} regionId={regionId} busy={busy}
        onAccept={(d: NpcDraft) => onCreate(d)} />
    </div>
  );
}

function NpcForm({ initial, busy, onSubmit, onCancel }: {
  initial?: NpcFields;
  busy: boolean;
  onSubmit: (f: NpcFields) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [role, setRole] = useState(initial?.role ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [traits, setTraits] = useState((initial?.traits ?? []).join(", "));
  const valid = name.trim() && role.trim() && description.trim();
  return (
    <div className="flex flex-col gap-1" data-testid="npc-form">
      <Field label={t("editor.npc.name")} data-testid="npc-name" value={name}
        onChange={(e) => setName(e.target.value)} />
      <Field label={t("editor.npc.role")} data-testid="npc-role" value={role}
        onChange={(e) => setRole(e.target.value)} />
      <Field label={t("editor.npc.description")} data-testid="npc-description" value={description}
        onChange={(e) => setDescription(e.target.value)} />
      <Field label={t("editor.npc.traits")} value={traits} onChange={(e) => setTraits(e.target.value)} />
      <div className="flex gap-1">
        <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
        <Button size="sm" variant="primary" data-testid="npc-save" disabled={busy || !valid}
          onClick={() => onSubmit({ name: name.trim(), role: role.trim(),
            description: description.trim(),
            traits: traits.split(",").map((x) => x.trim()).filter(Boolean) })}>
          {t("editor.npc.save")}
        </Button>
      </div>
    </div>
  );
}
