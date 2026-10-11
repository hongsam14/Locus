import { enumLabel } from "../../format";
import { t } from "../../i18n";
import type { AugQuestion, ConnectionEdge, Knowledge, NameRef, Region, WikiPrior } from "../../types";
import { Button, InlineError, Panel } from "../../ui";
import { AugmentQuestion } from "./AugmentQuestion";
import { changeLabel, issueKeyLine, type NameSource, targetLabel } from "./augmentNames";
import type { Augmentation } from "./useAugmentation";

/** The augmentation Q&A (US-2.6, BR-U3-24..28), shown only: the run, its writes and the typed
 * answers live on the page (`useAugmentation`, V8 R-15), so leaving the tab — a press on the
 * map opens the region tab — keeps all of it. Each question names its target, offers only the
 * server's actions and shows the inputs the server says they take (U3 review C2/S06). The
 * state reads in words: no hard-coded answer limit, changes as labels, ignored and kept
 * questions by name (UX-23, BR-V8-17/18). */
export function AugmentPanel({
  aug,
  regions,
  entities,
  knowledge,
  connections,
  priors,
}: {
  aug: Augmentation;
  regions: Region[];
  entities: NameRef[];
  knowledge: Knowledge[];
  connections: ConnectionEdge[];
  priors: WikiPrior[]; // the world's, read again after a prior is deleted (code review 01 #9)
}) {
  const { run, busy, lost, error } = aug;
  const names: NameSource = { regions, knowledge, entities, connections };
  const latest = run ? [...run.history].reverse().find((c) => !c.reverted) : undefined;
  const refOptions = (q: AugQuestion): NameRef[] => {
    if (q.ref_kind === "region") return regions;
    if (q.ref_kind === "entity") return entities;
    return priors.map((p) => ({ id: p.id, name: p.effect }));
  };
  const kept = run?.kept_keys ?? [];
  return (
    <Panel title={t("augment.title")} data-testid="augment-panel">
      <Button size="sm" variant="primary" data-testid="augment-find" busy={busy} onClick={aug.start}>
        {t("augment.find")}
      </Button>
      {error && (
        <div data-testid="augment-error" className="flex flex-col items-start gap-2">
          <InlineError error={error} />
          {aug.stale && (
            <Button size="sm" data-testid="augment-restart" disabled={busy} onClick={aug.start}>
              {t("action.restartAugment")}
            </Button>
          )}
        </div>
      )}
      {lost && (
        <div className="text-sm text-danger" data-testid="augment-lost">{t("augment.lost")}</div>
      )}
      {run && !lost && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="text-xs text-muted" data-testid="augment-status">
            {enumLabel("augmentationStatus", run.status)} · {t("label.augmentAnswered", { n: run.answers })}
          </div>
          {run.llm_budget_exhausted && <div className="text-xs text-danger">{t("augment.budget")}</div>}
          {run.status === "converged" && <div className="text-sm">{t("notice.augmentConverged")}</div>}
          {run.status === "stopped" && <div className="text-sm">{t("notice.augmentStopped")}</div>}
          {run.open_questions.map((q) => (
            <AugmentQuestion key={q.id} question={q} inputs={aug.drafts[q.issue_key] ?? {}} regions={regions} names={names}
              refOptions={refOptions(q)} busy={busy} onInput={(patch) => aug.setDraft(q.issue_key, patch)}
              onAnswer={(a) => aug.answer(q, a)} />
          ))}
          {run.history.length > 0 && <h3 className="font-heading">{t("augment.changed")}</h3>}
          {[...run.history].reverse().map((c) => (
            <div key={c.id} className="flex flex-wrap items-center gap-2 text-xs" data-testid="augment-change">
              <span className="min-w-0 flex-1 break-words">
                {changeLabel(c.description)} {(aug.changed[c.id] ?? []).map((x) => targetLabel(x, names)).join(", ")}
              </span>
              {c.reverted ? (
                <span className="text-muted">{t("augment.reverted")}</span>
              ) : (
                <Button size="sm" data-testid="augment-revert" disabled={busy || latest?.id !== c.id}
                  onClick={() => aug.revert(c.id)}>
                  {t("augment.revert")}
                </Button>
              )}
            </div>
          ))}
          {run.ignored_keys.length > 0 && <h3 className="font-heading">{t("augment.ignored")}</h3>}
          {run.ignored_keys.map((key) => (
            <div key={key} className="flex flex-wrap items-center gap-2 text-xs" data-testid="augment-ignored">
              <span className="min-w-0 flex-1 break-words">{issueKeyLine(key, names)}</span>
              <Button size="sm" data-testid="augment-unignore" disabled={busy || run.status === "stopped"}
                onClick={() => aug.unignore(key)}>
                {t("augment.unignore")}
              </Button>
            </div>
          ))}
          {kept.length > 0 && (
            <details data-testid="augment-kept" className="text-xs">
              <summary className="cursor-pointer">{t("label.augmentKept", { n: kept.length })}</summary>
              <ul className="list-disc pl-4">
                {kept.map((key) => <li key={key} className="break-words">{issueKeyLine(key, names)}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}
    </Panel>
  );
}
