import { ENUM_VALUES, enumLabel } from "../../format";
import { t } from "../../i18n";
import { fieldLabel, type NameSource, parseIssueKey, targetLabel } from "./augmentNames";
import type { AugAction, AugInput, AugQuestion, NameRef, Region } from "../../types";
import { Badge, Button, Card, Field, Select as UiSelect } from "../../ui";

/** What a designer typed on one question's card (kept per issue key, U3 review S28). */
export type Inputs = { statement?: string; title?: string; confidence?: string; region?: string; ref?: string };

/** Every input any of the question's actions takes — the server says which (U3 C2). */
const inputsOf = (q: AugQuestion): Set<AugInput> =>
  new Set(Object.values(q.needs ?? {}).flat() as AugInput[]);

/** A confidence box's value when it is a number in [0, 1]; otherwise nothing is sent. */
export function confidenceOf(text?: string): number | undefined {
  if (text == null || text.trim() === "") return undefined;
  const v = Number(text);
  return Number.isFinite(v) && v >= 0 && v <= 1 ? v : undefined;
}

const ISSUES = ENUM_VALUES.augmentationIssue as readonly string[];

/** One augmentation question (US-2.6), out of `AugmentPanel` (U8, NFR-7): the issue's label,
 * the target's kind and name, the question in this screen's words, the inputs the server says
 * its actions take (statement, title, confidence, region, reference — U3 review C2/S06) and
 * only the server's actions. The server's own sentence is not shown: without an LLM it is an
 * English template with the raw property in it, and its connection names carry the raw kind
 * (code review 01 #3, the human's choice A; FC § 4.5, BLM § 6.4). */
export function AugmentQuestion({
  question: q,
  inputs,
  regions,
  names,
  refOptions,
  busy,
  onInput,
  onAnswer,
}: {
  question: AugQuestion;
  inputs: Inputs;
  regions: Region[];
  names: NameSource;
  refOptions: NameRef[];
  busy: boolean;
  onInput: (patch: Inputs) => void;
  onAnswer: (action: AugAction) => void;
}) {
  const takes = inputsOf(q);
  const key = parseIssueKey(q.issue_key);
  const type = q.type ?? key?.type ?? "";
  const issue = ISSUES.includes(type) ? type : null;
  const kind = q.target?.kind ?? key?.kind;
  const field = q.target?.field ?? (key?.field || null);
  const refKind = q.ref_kind === "prior" ? t("augment.refKind.prior")
    : q.ref_kind ? t(`augment.target.${q.ref_kind}`) : t("label.unnamed");
  return (
    <Card data-testid="augment-question" className="flex flex-col gap-1 break-words text-sm">
      <div className="flex flex-wrap items-center gap-1" data-testid="augment-target">
        {issue && <Badge tone="info" data-testid="augment-issue">{enumLabel("augmentationIssue", issue)}</Badge>}
        {kind && <Badge>{t(`augment.target.${kind}`)}</Badge>}
        <strong className="min-w-0 [overflow-wrap:anywhere]">
          {q.target ? targetLabel(q.target, names) : t("label.unnamed")}
        </strong>
        {q.target?.region_name && <span className="text-xs text-muted">@ {q.target.region_name}</span>}
        {field && <span className="text-xs text-muted" data-testid="augment-field">{fieldLabel(field)}</span>}
      </div>
      <p data-testid="augment-ask">{t(`augment.ask.${issue ?? "other"}`, { kind: refKind })}</p>
      {takes.has("statement") && (
        <Field label={t("augment.statement")} data-testid="augment-statement"
          value={inputs.statement ?? ""} onChange={(e) => onInput({ statement: e.target.value })} />
      )}
      {takes.has("title") && (
        <Field label={t("augment.titleLabel")} data-testid="augment-title"
          value={inputs.title ?? ""} onChange={(e) => onInput({ title: e.target.value })} />
      )}
      {takes.has("confidence") && (
        <Field label={t("augment.confidence")} data-testid="augment-confidence" type="number"
          min={0} max={1} step={0.05} value={inputs.confidence ?? ""}
          onChange={(e) => onInput({ confidence: e.target.value })} />
      )}
      {takes.has("region") && (
        <Select testId="augment-region" label={t("augment.region")} value={inputs.region}
          options={regions} onChange={(v) => onInput({ region: v })} />
      )}
      {takes.has("ref") && (
        <Select testId="augment-ref" label={t("augment.ref")} value={inputs.ref}
          options={refOptions} onChange={(v) => onInput({ ref: v })} />
      )}
      <div className="flex flex-wrap gap-1">
        {q.actions.map((a) => (
          <Button key={a} size="sm" disabled={busy} data-testid={`augment-action-${a}`}
            variant={a === "remove" ? "danger" : "ghost"} onClick={() => onAnswer(a)}>
            {t(`augment.action.${a}`)}
          </Button>
        ))}
      </div>
    </Card>
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
    <UiSelect label={label} hideLabel data-testid={testId} value={value ?? ""}
      options={[{ value: "", label }, ...options.map((o) => ({ value: o.id, label: o.name }))]}
      onChange={onChange} />
  );
}
