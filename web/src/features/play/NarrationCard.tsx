import { t } from "../../i18n";
import type { Narration } from "../../types";
import { Panel } from "../../ui";

/** The world's answer to the last declaration (US-4.5). Written in the display language
 * when it was made, so there is no original/translation toggle (FD-U6 Q3=A). */
export function NarrationCard({ narration }: { narration: Narration | null }) {
  if (!narration) return null;
  return (
    <Panel data-testid="narration-card" title={t("play.narrationTitle")} className="max-w-2xl">
      <p className="text-sm whitespace-pre-line">{narration.text}</p>
      {narration.llm_calls === 0 && (
        <p data-testid="narration-fallback" className="mt-1 text-xs text-ink-soft">
          {t("play.narrationFallback")}
        </p>
      )}
    </Panel>
  );
}
