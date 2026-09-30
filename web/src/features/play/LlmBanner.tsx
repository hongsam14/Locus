import { t } from "../../i18n";

/** Shown when the backend has no LLM provider (US-1.4): moving still works. */
export function LlmBanner({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div data-testid="llm-banner" className="sketch-border bg-highlight px-3 py-2 text-sm">
      {t("play.noLlm")}
    </div>
  );
}
