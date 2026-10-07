import { setLang, t, useAvailableLangs, useLang } from "../../i18n";

/** Display language ko | en (FD-U5 Q1=A, US-9.4). No state of its own: the language
 * lives in `i18n` and localStorage; screens that read translated data re-fetch when
 * it changes (their `useLang()` value is an effect dependency). */
export function LangToggle() {
  const current = useLang();
  const offered = useAvailableLangs(); // only languages the server takes (review U5 #2)
  if (offered.length < 2) return null;
  return (
    <span
      role="group"
      aria-label={t("lang.label")}
      data-testid="lang-toggle"
      className="inline-flex sketch-border overflow-hidden text-xs font-display"
    >
      {offered.map((l) => (
        <button
          key={l}
          type="button"
          data-testid={`lang-${l}`}
          aria-pressed={l === current}
          onClick={() => setLang(l)}
          className={`px-1.5 py-0.5 ${l === current ? "bg-ink text-paper" : "bg-paper-card text-ink-soft hover:text-ink"}`}
        >
          {l}
        </button>
      ))}
    </span>
  );
}
