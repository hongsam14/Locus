import { useEffect, useState } from "react";
import { api } from "../../api";
import { detailOf, statusOf } from "../../api/http";
import { t } from "../../i18n";
import type { AugAction, AugQuestion, AugRun, NameRef, QuestionTarget, Region, WikiPrior } from "../../types";
import { Button, Panel } from "../../ui";
import { AugmentQuestion, type Inputs, confidenceOf } from "./AugmentQuestion";

/** The augmentation Q&A (US-2.6, BR-U3-24..28): one run kept by the screen; each
 * question names its target, offers only the server's actions and shows the inputs the
 * server says they take (statement, title, confidence, region, reference — U3 review
 * C2/S06); an answer returns
 * the run with its next questions; changes undo latest first; an ignored question can
 * be asked again. A restart loses runs (BR-U3-42): the panel then offers a new search.
 * The page keeps the run id (``runId``/``onRunId``) so leaving the tab — a click on the
 * map switches to the region tab — does not drop the run: back on the tab the panel
 * reads it again (U3 review #2, BR-U3-26). */
export function AugmentPanel({
  worldId,
  regions,
  entities,
  onChanged,
  runId = null,
  onRunId,
}: {
  worldId: string;
  regions: Region[];
  entities: NameRef[];
  onChanged: () => void;
  runId?: string | null;
  onRunId?: (id: string | null) => void;
}) {
  const [run, setRun] = useState<AugRun | null>(null);
  const [lost, setLost] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changed, setChanged] = useState<Record<string, QuestionTarget[]>>({});
  const [priors, setPriors] = useState<WikiPrior[] | null>(null);
  // keyed by the issue, not the question: a re-detection gives every question a new id
  // and must not wipe what was typed on the other cards (U3 review S28)
  const [input, setInput] = useState<Record<string, Inputs>>({});

  useEffect(() => {
    setRun(null);
    setLost(false);
    if (!runId) return;
    let alive = true;
    api
      .getRun(runId)
      .then((r) => alive && setRun(r))
      .catch((e) => alive && (statusOf(e) === 404 ? setLost(true) : setError(String(e))));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [worldId]);
  useEffect(() => {
    if (run) onRunId?.(run.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.id]);

  const needsPriors = run?.open_questions.some((q) => q.ref_kind === "prior");
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
      if (statusOf(e) === 404 && run) await checkRun(run.id, e);
      else if (statusOf(e) === 409) setError(t("augment.conflict", { reason: String(e) }));
      else setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  /** A 404 is a lost run only when the run itself is gone (a restart): a target removed
   * meanwhile also answers 404, and then the run stays with the server's reason shown
   * (U3 review #12). */
  async function checkRun(id: string, err: unknown) {
    try {
      setRun(await api.getRun(id));
      setError(detailOf(err));
    } catch (again) {
      if (statusOf(again) === 404) setLost(true);
      else setError(String(again));
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
      const i = input[q.issue_key] ?? {};
      const takes = new Set(q.needs?.[action] ?? []); // only what this action takes
      const res = await api.answer(run!.id, {
        question_id: q.id,
        action,
        statement: takes.has("statement") ? i.statement?.trim() || undefined : undefined,
        title: takes.has("title") ? i.title?.trim() || undefined : undefined,
        confidence: takes.has("confidence") ? confidenceOf(i.confidence) : undefined,
        region_id: takes.has("region") ? i.region || undefined : undefined,
        ref_id: takes.has("ref") ? i.ref || undefined : undefined,
      });
      if (res.change) setChanged((c) => ({ ...c, [res.change!.id]: res.changed }));
      if (action !== "ignore") onChanged();
      return res.run;
    });

  const latest = run ? [...run.history].reverse().find((c) => !c.reverted) : undefined;
  const refOptions = (q: AugQuestion): NameRef[] => {
    if (q.ref_kind === "region") return regions;
    if (q.ref_kind === "entity") return entities;
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
          <div className="text-xs text-muted" data-testid="augment-status">
            {t("augment.status", { status: run.status, answers: run.answers })}
          </div>
          {run.llm_budget_exhausted && <div className="text-xs text-danger">{t("augment.budget")}</div>}
          {run.status === "converged" && <div className="text-sm">{t("augment.converged")}</div>}
          {run.status === "stopped" && <div className="text-sm">{t("augment.stopped")}</div>}
          {run.open_questions.map((q) => (
            <AugmentQuestion key={q.id} question={q} inputs={input[q.issue_key] ?? {}} regions={regions}
              refOptions={refOptions(q)} busy={busy} onInput={(patch) => set(q.issue_key, patch)}
              onAnswer={(a) => answer(q, a)} />
          ))}
          {run.history.length > 0 && <h3 className="font-heading">{t("augment.changed")}</h3>}
          {[...run.history].reverse().map((c) => (
            <div key={c.id} className="text-xs flex items-center gap-2" data-testid="augment-change">
              <span className="flex-1">
                {c.description} {(changed[c.id] ?? []).map((x) => x.name).join(", ")}
              </span>
              {c.reverted ? (
                <span className="text-muted">{t("augment.reverted")}</span>
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
          {run.ignored_keys.length > 0 && <h3 className="font-heading">{t("augment.ignored")}</h3>}
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
