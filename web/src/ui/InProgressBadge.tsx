import { t } from "../i18n";

/** "In progress": a feature that is kept but not finished (U8, US-7.3, BR-U8-31). */
export function InProgressBadge({ note }: { note: string }) {
  return (
    <span
      data-testid="wip-badge"
      title={note}
      className="ml-1 inline-block rounded-full border border-line px-2 text-xs text-muted"
    >
      {t("wip.badge")}
    </span>
  );
}
