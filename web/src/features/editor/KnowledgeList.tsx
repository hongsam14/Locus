import { useState } from "react";
import { t } from "../../i18n";
import type { Knowledge, Region, ScopedKnowledge } from "../../types";
import { Badge, Button, Card, Field, LocalizedText } from "../../ui";

/** Knowledge held here (US-2.3): translated text with an original toggle (BR-U3-37),
 * the regions each item is scoped to, edit (scopes stay), scope edit (DIRECT scopes
 * become exactly the picked regions, BR-U3-13), delete, and add (one DIRECT scope). */
export function KnowledgeList({
  items,
  regions,
  busy,
  onCreate,
  onUpdate,
  onSetScopes,
  onDelete,
}: {
  items: ScopedKnowledge[];
  regions: Region[];
  busy: boolean;
  onCreate: (title: string, statement: string) => void;
  onUpdate: (k: Knowledge) => void;
  onSetScopes: (k: Knowledge, regionIds: string[]) => void;
  onDelete: (k: Knowledge) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [scoping, setScoping] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const name = (id: string) => regions.find((r) => r.id === id)?.name ?? id;
  return (
    <div className="flex flex-col gap-1.5" data-testid="knowledge-list">
      {items.length === 0 && (
        <div className="text-xs text-ink-soft">{t("editor.knowledge.none")}</div>
      )}
      {items.map(({ knowledge: k, scope_region_ids: scopes }) => (
        <Card key={k.id} data-testid={`editor-knowledge-${k.id}`} className="flex flex-col gap-1 text-sm">
          {editing === k.id ? (
            <TextForm initialTitle={k.title} initialStatement={k.statement} busy={busy}
              onCancel={() => setEditing(null)}
              onSubmit={(title, statement) => {
                onUpdate({ ...k, title, statement });
                setEditing(null);
              }} />
          ) : (
            <>
              <strong>{k.title_ko || k.title}</strong>
              <LocalizedText testId={`editor-knowledge-text-${k.id}`} ko={k.statement_ko}
                original={k.statement} />
            </>
          )}
          <div className="flex flex-wrap gap-1">
            {scopes.map((rid) => <Badge key={rid}>{name(rid)}</Badge>)}
          </div>
          {scoping === k.id ? (
            <ScopePicker regions={regions} initial={scopes} busy={busy}
              onCancel={() => setScoping(null)}
              onSave={(ids) => {
                onSetScopes(k, ids);
                setScoping(null);
              }} />
          ) : (
            <div className="flex gap-1">
              <Button size="sm" data-testid={`knowledge-edit-${k.id}`} disabled={busy}
                onClick={() => setEditing(k.id)}>{t("editor.knowledge.edit")}</Button>
              <Button size="sm" data-testid={`knowledge-scopes-${k.id}`} disabled={busy}
                onClick={() => setScoping(k.id)}>{t("editor.scopes")}</Button>
              <Button size="sm" variant="danger" data-testid={`knowledge-delete-${k.id}`}
                disabled={busy} onClick={() => onDelete(k)}>✕</Button>
            </div>
          )}
        </Card>
      ))}
      {adding ? (
        <TextForm initialTitle="" initialStatement="" busy={busy} onCancel={() => setAdding(false)}
          onSubmit={(title, statement) => {
            onCreate(title, statement);
            setAdding(false);
          }} />
      ) : (
        <Button size="sm" data-testid="knowledge-add" disabled={busy} onClick={() => setAdding(true)}>
          {t("editor.knowledge.add")}
        </Button>
      )}
    </div>
  );
}

function TextForm({ initialTitle, initialStatement, busy, onSubmit, onCancel }: {
  initialTitle: string;
  initialStatement: string;
  busy: boolean;
  onSubmit: (title: string, statement: string) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initialTitle);
  const [statement, setStatement] = useState(initialStatement);
  const valid = statement.trim().length > 0;
  return (
    <div className="flex flex-col gap-1" data-testid="knowledge-form">
      <Field label={t("editor.knowledge.titleLabel")} data-testid="knowledge-title" value={title}
        onChange={(e) => setTitle(e.target.value)} />
      <label className="inline-flex flex-col gap-0.5 text-sm">
        <span className="text-ink-soft">{t("editor.knowledge.statement")}</span>
        <textarea data-testid="knowledge-statement" rows={2} value={statement}
          onChange={(e) => setStatement(e.target.value)}
          className="sketch-border bg-paper-card px-2 py-1 text-sm" />
      </label>
      <div className="flex gap-1">
        <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
        <Button size="sm" variant="primary" data-testid="knowledge-save" disabled={busy || !valid}
          onClick={() => onSubmit(title.trim() || statement.trim().slice(0, 60), statement.trim())}>
          {t("editor.knowledge.save")}
        </Button>
      </div>
    </div>
  );
}

export function ScopePicker({ regions, initial, busy, onSave, onCancel }: {
  regions: Region[];
  initial: string[];
  busy: boolean;
  onSave: (ids: string[]) => void;
  onCancel: () => void;
}) {
  const [picked, setPicked] = useState<string[]>(initial);
  const toggle = (id: string) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  return (
    <div className="flex flex-col gap-1" data-testid="scope-picker">
      <div className="flex flex-wrap gap-2">
        {regions.map((r) => (
          <label key={r.id} className="text-xs inline-flex items-center gap-1">
            <input type="checkbox" checked={picked.includes(r.id)} data-testid={`scope-${r.id}`}
              onChange={() => toggle(r.id)} />
            {r.name}
          </label>
        ))}
      </div>
      <div className="flex gap-1">
        <Button size="sm" onClick={onCancel}>{t("action.cancel")}</Button>
        <Button size="sm" variant="primary" data-testid="scope-save" disabled={busy}
          onClick={() => onSave(picked)}>{t("editor.scopes.save")}</Button>
      </div>
    </div>
  );
}
