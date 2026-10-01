import { t } from "../i18n";

/** "In progress": a feature that is kept but not finished (U8, US-7.3, BR-U8-31). */
export function InProgressBadge({ note }: { note: string }) {
  return (
    <span
      data-testid="wip-badge"
      title={note}
      className="ml-1 inline-block sketch-border px-1 text-[10px] uppercase tracking-wide text-ink-soft"
    >
      {t("wip.badge")}
    </span>
  );
}
