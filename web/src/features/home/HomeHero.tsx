import { t } from "../../i18n";

/** The home's opening lines (V4 FR-S1, frontend-components § 2.3): what this game is, in
 * the story register. Static: no read, no button. */
export function HomeHero() {
  return (
    <header data-testid="home-hero" className="flex flex-col gap-2 pt-4">
      <span className="font-heading text-sm uppercase tracking-widest text-accent">{t("label.homeKicker")}</span>
      <h1 className="font-heading text-2xl text-balance sm:text-3xl">{t("story.homeTagline")}</h1>
      <p className="max-w-prose font-story text-muted">{t("story.homeLead")}</p>
    </header>
  );
}
