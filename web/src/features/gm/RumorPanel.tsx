import { useEffect, useState } from "react";
import { numberWithMeaning } from "../../format";
import { t } from "../../i18n";
import type { SessionRumor } from "../../types";
import { Badge, Button, Card, CommitRange, ConfirmDialog, LocalizedText, StatusView } from "../../ui";
import type { GmRes } from "./useGmData";

/** The chosen region's rumors (V6 frontend-components § 4.1, BR-V6-11/25/33): make them, make
 * them again after asking, and each rumor's belief — the number with its meaning, following
 * the thumb (UX-41). The first read shows loading; another region's rumors never show here
 * while this one reads (code plan § 1.1 R-02). */
export function RumorPanel({
  rumors,
  list,
  closed,
  llmOff = false,
  busy,
  writing = false,
  onGenerate,
  onRegen,
  onSupport,
}: {
  rumors: GmRes<SessionRumor[]>;
  /** The list with a write's own answer laid over it. */
  list: SessionRumor[] | undefined;
  closed: boolean;
  llmOff?: boolean;
  busy: boolean; // a bulk run goes
  /** This region's generate / regenerate runs (the screen holds it, code review 01 #7). */
  writing?: boolean;
  onGenerate(): Promise<unknown>;
  onRegen(): Promise<unknown>;
  onSupport: (rumorId: string, v: number) => Promise<boolean> | boolean | void;
}) {
  const [asking, setAsking] = useState(false);
  const why = llmOff ? t("llm.required") : undefined;
  const off = closed || busy || llmOff;
  return (
    <section className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="flex-1 font-heading text-lg">{t("label.rumors")}</h3>
        <Button size="sm" variant="primary" data-testid="generate-btn" busy={writing} disabled={off} title={why}
          onClick={() => void onGenerate()}>
          {t("action.generateHere")}
        </Button>
        <Button size="sm" data-testid="regen-btn" busy={writing} disabled={off} title={why}
          onClick={() => setAsking(true)}>
          {t("action.regenerate")}
        </Button>
      </div>
      {list === undefined ? (
        <StatusView state={rumors.state === "error" ? "error" : "loading"} error={rumors.error} onRetry={rumors.reload} />
      ) : list.length === 0 ? (
        <p data-testid="rumors-empty" className="text-sm text-muted">{t("empty.rumorsHere")}</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {list.map((r) => (
            <RumorCard key={r.id} rumor={r} closed={closed} onSupport={onSupport} />
          ))}
        </div>
      )}
      <ConfirmDialog
        open={asking}
        title={t("action.regenerate")}
        confirmLabel={t("action.regenerate")}
        cancelLabel={t("action.cancel")}
        confirmTestId="regen-confirm"
        onConfirm={() => {
          setAsking(false);
          void onRegen();
        }}
        onCancel={() => setAsking(false)}
      >
        {t("confirm.regenRegion")}
      </ConfirmDialog>
    </section>
  );
}

function RumorCard({
  rumor: r,
  closed,
  onSupport,
}: {
  rumor: SessionRumor;
  closed: boolean;
  onSupport: (rumorId: string, v: number) => Promise<boolean> | boolean | void;
}) {
  const [shown, setShown] = useState(r.support);
  useEffect(() => setShown(r.support), [r.support]);
  return (
    <Card data-testid={`rumor-${r.id}`} className="flex flex-col gap-1 text-sm">
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
        {r.promoted && (
          <Badge data-testid={`promoted-${r.id}`} tone="promoted">
            {t("label.settled")}
          </Badge>
        )}
        {r.origin_kind === "deed" && (
          <Badge data-testid={`deed-badge-${r.id}`} tone="event">
            {t("badge.deed")}
          </Badge>
        )}
        <span>
          {t("label.distortion")} {numberWithMeaning("distortion", r.distortion_degree)}
        </span>
      </div>
      <span id={`rumor-say-${r.id}`}>
        <LocalizedText testId={`rumor-text-${r.id}`} ko={r.statement_ko} original={r.statement} />
      </span>
      <label className="flex flex-col gap-1 text-xs">
        <span data-testid={`support-label-${r.id}`} className="text-muted">
          {t("label.support")} {numberWithMeaning("support", shown)}
        </span>
        <CommitRange
          aria-describedby={`rumor-say-${r.id}`} // which rumor this belief is (review 43(d))
          data-testid={`support-${r.id}`}
          min={0}
          max={1}
          step={0.05}
          value={r.support}
          disabled={closed}
          onCommit={(v) => onSupport(r.id, v)}
          onDraft={setShown}
        />
      </label>
    </Card>
  );
}
