import { t } from "../../i18n";
import type { SessionRumor } from "../../types";
import { Badge, Button, Card, CommitRange, LocalizedText } from "../../ui";

/** The selected region's rumors: generate / regenerate, and each rumor's support slider
 * (saved however it is moved, BR-U7-24). Deed rumors carry a badge (U6). */
export function RumorPanel({
  rumors,
  closed,
  llmOff = false,
  busy,
  onGenerate,
  onRegen,
  onSupport,
}: {
  rumors: SessionRumor[];
  closed: boolean;
  llmOff?: boolean; // U8 (BR-U8-25): generate and regenerate need the LLM
  busy: boolean;
  onGenerate: () => void;
  onRegen: () => void;
  onSupport: (rumorId: string, v: number) => Promise<boolean> | boolean | void;
}) {
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button variant="primary" data-testid="generate-btn" onClick={onGenerate}
          disabled={closed || busy || llmOff} title={llmOff ? t("llm.required") : undefined}>
          {t("gm.generate")}
        </Button>
        <Button data-testid="regen-btn" onClick={onRegen}
          disabled={closed || busy || llmOff} title={llmOff ? t("llm.required") : undefined}>
          {t("gm.regen")}
        </Button>
      </div>
      <div className="flex flex-col gap-1.5">
        {rumors.map((r) => (
          <Card key={r.id} data-testid={`rumor-${r.id}`} className="text-sm">
            <div className="flex items-center gap-1.5">
              {r.promoted && (
                <Badge data-testid={`promoted-${r.id}`} tone="promoted">
                  {t("gm.promoted")}
                </Badge>
              )}
              {r.origin_kind === "deed" && (
                <Badge data-testid={`deed-badge-${r.id}`} tone="event">
                  {t("badge.deed")}
                </Badge>
              )}
              <span className="text-ink-soft text-xs">d{r.distortion_degree.toFixed(2)}</span>
              <LocalizedText testId={`rumor-text-${r.id}`} ko={r.statement_ko} original={r.statement} />
            </div>
            <label className="text-xs text-ink-soft flex items-center gap-2 mt-1">
              {t("gm.support")} {r.support.toFixed(2)}
              <CommitRange
                data-testid={`support-${r.id}`}
                min={0}
                max={1}
                step={0.05}
                value={r.support}
                disabled={closed}
                onCommit={(v) => onSupport(r.id, v)}
              />
            </label>
          </Card>
        ))}
      </div>
    </>
  );
}
