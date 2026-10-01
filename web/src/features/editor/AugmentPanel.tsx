import { useEffect, useState } from "react";
import { api } from "../../api";
import { statusOf } from "../../api/http";
import { t } from "../../i18n";
import type { AugAction, AugQuestion, AugRun, NameRef, QuestionTarget, Region, WikiPrior } from "../../types";
import { Badge, Button, Card, Field, Panel } from "../../ui";

const kindOf = (q: AugQuestion) => q.issue_key.split(":")[0];

/** The augmentation Q&A (US-2.6, BR-U3-24..28): one run kept by the screen; each
 * question names its target and offers only the server's actions; an answer returns
 * the run with its next questions; changes undo latest first; an ignored question can
 * be asked again. A restart loses runs (BR-U3-42): the panel then offers a new search. */
export function AugmentPanel({
  worldId,
  regions,
  entities,
  onChanged,
}: {
  worldId: string;
  regions: Region[];
  entities: NameRef[];
  onChanged: () => void;
}) {
  const [run, setRun] = useState<AugRun | null>(null);
  const [lost, setLost] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changed, setChanged] = useState<Record<string, QuestionTarget[]>>({});
  const [priors, setPriors] = useState<WikiPrior[] | null>(null);
  const [input, setInput] = useState<Record<string, { statement?: string; region?: string; ref?: string }>>({});

  useEffect(() => {
    setRun(null);
    setLost(false);
  }, [worldId]);

  const needsPriors = run?.open_questions.some((q) =>
    ["wiki_prior_ref", "derived_from_prior_ids"].includes(q.target?.field ?? ""),
  );
  useEffect(() => {
    if (needsPriors && priors == null) api.listPriors(worldId).then(setPriors).catch(() => setPriors([]));
  }, [needsPriors, priors, worldId]);

  async function call(fn: () => Promise<AugRun | void>) {
    setBusy(true);
    setError(null);
    try {
      const next = await fn();
      if (next) setRun(next);
    } catch (e) {
      if (statusOf(e) === 404 && run) setLost(true);
      else if (statusOf(e) === 409) setError(t("augment.conflict", { reason: String(e) }));
      else setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const find = () =>
    call(async () => {
      setLost(false);
      setChanged({});
      return api.startRun(worldId);
    });

  const answer = (q: AugQuestion, action: AugAction) =>
    call(async () => {
      const i = input[q.id] ?? {};
      const res = await api.answer(run!.id, {
        question_id: q.id,
        action,
        statement: i.statement?.trim() || undefined,
        region_id: i.region || undefined,
        ref_id: i.ref || undefined,
      });
      if (res.change) setChanged((c) => ({ ...c, [res.change!.id]: res.changed }));
      if (action !== "ignore") onChanged();
      return res.run;
    });

  const latest = run ? [...run.history].reverse().find((c) => !c.reverted) : undefined;
  const refOptions = (q: AugQuestion): NameRef[] => {
    const field = q.target?.field ?? "";
    if (field === "parent_id" || field === "located_in") return regions;
    if (field === "about_entity_ids") return entities;
    return (priors ?? []).map((p) => ({ id: p.id, name: p.effect }));
  };
  const set = (id: string, patch: object) => setInput((s) => ({ ...s, [id]: { ...s[id], ...patch } }));

  return (
    <Panel title={t("augment.title")} data-testid="augment-panel" className="min-w-80">
      <Button size="sm" variant="primary" data-testid="augment-find" disabled={busy} onClick={find}>
        {t("augment.find")}
      </Button>
      {error && <div className="text-danger text-sm" data-testid="augment-error">{error}</div>}
      {lost && <div className="text-danger text-sm" data-testid="augment-lost">{t("augment.lost")}</div>}
      {run && !lost && (
        <div className="flex flex-col gap-2 mt-2">
          <div className="text-xs text-ink-soft" data-testid="augment-status">
            {t("augment.status", { status: run.status, answers: run.answers })}
          </div>
          {run.llm_budget_exhausted && <div className="text-xs text-danger">{t("augment.budget")}</div>}
          {run.status === "converged" && <div className="text-sm">{t("augment.converged")}</div>}
          {run.status === "stopped" && <div className="text-sm">{t("augment.stopped")}</div>}
          {run.open_questions.map((q) => (
            <Card key={q.id} data-testid="augment-question" className="text-sm flex flex-col gap-1">
              {q.target && (
                <div className="flex flex-wrap items-center gap-1" data-testid="augment-target">
                  <Badge>{t(`augment.target.${q.target.kind}`)}</Badge>
                  <strong>{q.target.name}</strong>
                  {q.target.region_name && <span className="text-xs text-ink-soft">@ {q.target.region_name}</span>}
                  {q.target.field && <code className="text-xs">{q.target.field}</code>}
                </div>
              )}
              <div>{q.text}</div>
              {(q.actions.includes("add") || (q.actions.includes("edit") && ["low_confidence", "wiki_conflict"].includes(kindOf(q)))) && (
                <Field label={t("augment.statement")} data-testid="augment-statement"
                  value={input[q.id]?.statement ?? ""} onChange={(e) => set(q.id, { statement: e.target.value })} />
              )}
              {["orphan", "unscoped"].includes(kindOf(q)) && (
                <Select testId="augment-region" label={t("augment.region")} value={input[q.id]?.region}
                  options={regions} onChange={(v) => set(q.id, { region: v })} />
              )}
              {kindOf(q) === "dangling" && (
                <Select testId="augment-ref" label={t("augment.ref")} value={input[q.id]?.ref}
                  options={refOptions(q)} onChange={(v) => set(q.id, { ref: v })} />
              )}
              <div className="flex flex-wrap gap-1">
                {q.actions.map((a) => (
                  <Button key={a} size="sm" disabled={busy} data-testid={`augment-action-${a}`}
                    variant={a === "remove" ? "danger" : "ghost"} onClick={() => answer(q, a)}>
                    {t(`augment.action.${a}`)}
                  </Button>
                ))}
              </div>
            </Card>
          ))}
          {run.history.length > 0 && <h3 className="font-display">{t("augment.changed")}</h3>}
          {[...run.history].reverse().map((c) => (
            <div key={c.id} className="text-xs flex items-center gap-2" data-testid="augment-change">
              <span className="flex-1">
                {c.description} {(changed[c.id] ?? []).map((x) => x.name).join(", ")}
              </span>
              {c.reverted ? (
                <span className="text-ink-soft">{t("augment.reverted")}</span>
              ) : (
                <Button size="sm" data-testid="augment-revert" disabled={busy || latest?.id !== c.id}
                  onClick={() => call(async () => {
                    const next = await api.revert(run.id, c.id);
                    onChanged();
                    return next;
                  })}>
                  {t("augment.revert")}
                </Button>
              )}
            </div>
          ))}
          {run.ignored_keys.length > 0 && <h3 className="font-display">{t("augment.ignored")}</h3>}
          {run.ignored_keys.map((key) => (
            <div key={key} className="text-xs flex items-center gap-2">
              <code className="flex-1 truncate">{key}</code>
              <Button size="sm" data-testid="augment-unignore" disabled={busy || run.status === "stopped"}
                onClick={() => call(() => api.unignore(run.id, key))}>
                {t("augment.unignore")}
              </Button>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function Select({ testId, label, value, options, onChange }: {
  testId: string;
  label: string;
  value?: string;
  options: NameRef[];
  onChange: (v: string) => void;
}) {
  return (
    <select data-testid={testId} aria-label={label} value={value ?? ""}
      onChange={(e) => onChange(e.target.value)} className="sketch-border bg-paper-card px-1 text-xs">
      <option value="">{label}</option>
      {options.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
    </select>
  );
}
