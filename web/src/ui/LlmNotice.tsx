import { t } from "../i18n";

/** One line telling the visitor what an LLM key would switch on (U8, US-1.4, BR-U8-25).
 * The play screen uses it with its own text (the session view says what is off there). */
export function LlmNotice({ visible, text }: { visible: boolean; text?: string }) {
  if (!visible) return null;
  return (
    <div data-testid="llm-notice" className="sketch-border bg-highlight px-3 py-2 text-sm">
      {text ?? t("llm.offNotice")}
    </div>
  );
}
