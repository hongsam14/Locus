import { setLang, t, useAvailableLangs, useLang } from "../i18n";
import type { Lang } from "../types";

// Display language ko | en (FD-U5 Q1=A, US-9.4). No state of its own: the language lives
// in `i18n` and localStorage; screens that read translated data re-fetch when it changes.
// Each language is named in itself; below 640 px the buttons show the short form (V2 BLM § 9).
const NAMES: Record<Lang, { full: string; short: string }> = {
  ko: { full: "한국어", short: "한" },
  en: { full: "English", short: "EN" },
};

export function LangSwitch() {
  const current = useLang();
  const offered = useAvailableLangs(); // only languages the server takes (review U5 #2)
  if (offered.length < 2) return null;
  return (
    <span
      role="group"
      aria-label={t("lang.label")}
      data-testid="lang-toggle"
      className="inline-flex overflow-hidden rounded-md border border-line-strong text-[13px]"
    >
      {offered.map((l) => (
        <button
          key={l}
          type="button"
          lang={l}
          aria-label={NAMES[l].full}
          data-testid={`lang-${l}`}
          aria-pressed={l === current}
          onClick={() => setLang(l)}
          className={`min-h-9 px-3 ${l === current ? "bg-accent font-bold text-on-accent" : "bg-surface text-fg hover:bg-sunken"}`}
        >
          <span className="hidden sm:inline">{NAMES[l].full}</span>
          <span className="sm:hidden" aria-hidden="true">
            {NAMES[l].short}
          </span>
        </button>
      ))}
    </span>
  );
}
